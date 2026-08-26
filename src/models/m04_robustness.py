import pandas as pd
import numpy as np
from src.features.local_features import LocalFeatureExtractor
from src.features.network_features import NetworkFeatureExtractor
from src.features.temporal_features import TemporalFeatureExtractor
from src.models.m04_temporal import prepare_data, select_threshold, calculate_metrics, evaluate_ttd
from src.data.perturbation import generate_robustness_variants
from sklearn.ensemble import RandomForestClassifier

def extract_all_features(df: pd.DataFrame) -> pd.DataFrame:
    """Runs all three extractors sequentially."""
    print("  Extracting local features...")
    df = LocalFeatureExtractor().extract_features(df)
    print("  Extracting network features...")
    df = NetworkFeatureExtractor().extract_features(df)
    print("  Extracting temporal features...")
    df = TemporalFeatureExtractor().extract_features(df)
    return df

def evaluate_variant(model, threshold, features, df_features, test_campaigns, target_col='is_abuse'):
    X = df_features[features]
    y_true = df_features[target_col]
    
    y_prob = model.predict_proba(X)[:, 1]
    y_pred = (y_prob >= threshold).astype(int)
    
    df_eval = df_features.copy()
    df_eval['predicted_fraud'] = y_pred
    df_eval['predicted_prob'] = y_prob
    
    metrics = calculate_metrics(y_true, y_pred, y_prob)
    ttd_metrics = evaluate_ttd(df_eval, test_campaigns)
    
    return {**metrics, **ttd_metrics}

def run_robustness():
    print("Loading datasets...")
    labels_df = pd.read_csv("data/generated/m01-world-v1/ground_truth/event_labels.csv")
    campaigns_df = pd.read_csv("data/generated/m01-world-v1/ground_truth/campaigns.csv")
    campaigns_df['start_timestamp'] = pd.to_datetime(campaigns_df['start_timestamp'])
    
    train_df = prepare_data("train", labels_df)
    val_df = prepare_data("validation", labels_df)
    
    # Raw test set before feature extraction
    tx_path = f"data/generated/m01-world-v1/cohorts/test/transactions.csv"
    raw_test_df = pd.read_csv(tx_path)
    raw_test_df['timestamp'] = pd.to_datetime(raw_test_df['timestamp'])
    test_campaigns = campaigns_df[campaigns_df['cohort'] == 'test'].copy()
    
    print("Generating Robustness Variants...")
    variants = generate_robustness_variants(raw_test_df, labels_df, test_campaigns)
    variants['baseline'] = (raw_test_df, test_campaigns) # Original
    
    extracted_variants = {}
    for v_name, (v_df, v_camp) in variants.items():
        print(f"\nProcessing Variant: {v_name}")
        ext_df = extract_all_features(v_df)
        ext_df = ext_df.merge(labels_df[['transaction_id', 'is_abuse', 'campaign_id']], on='transaction_id', how='left')
        extracted_variants[v_name] = (ext_df, v_camp)
        
    # --- Feature Sets ---
    LOCAL_FEATURES = [
        'amount', 'local_account_txns_1h', 'local_account_txns_24h', 
        'local_device_txns_1h', 'local_device_txns_24h',
        'local_account_amt_1h', 'local_account_amt_24h'
    ]
    DEVICE_FEATURES = ['network_device_accounts_24h', 'network_device_merchants_24h']
    NETWORK_GROUP_FEATURES = ['network_group_accounts_24h', 'network_group_merchants_24h']
    ACCOUNT_RELATIONSHIP_FEATURES = [
        'network_account_devices_24h', 'network_account_merchants_24h',
        'network_account_devices_7d', 'network_account_merchants_7d'
    ]
    ALL_NETWORK_FEATURES = DEVICE_FEATURES + NETWORK_GROUP_FEATURES + ACCOUNT_RELATIONSHIP_FEATURES
    B_STAR_FEATURES = DEVICE_FEATURES + ACCOUNT_RELATIONSHIP_FEATURES
    ROLLING_FEATURES = ['temporal_device_txns_5m', 'temporal_account_txns_5m']
    GROWTH_FEATURES = ['temporal_account_new_devices_1h', 'temporal_device_new_accounts_1h']
    SYNC_FEATURES = ['temporal_network_sync_5m', 'temporal_network_sync_15m']
    ALL_TEMPORAL_FEATURES = ROLLING_FEATURES + GROWTH_FEATURES + SYNC_FEATURES
    
    candidates = {
        'A (All Network + All Temporal)': LOCAL_FEATURES + ALL_NETWORK_FEATURES + ALL_TEMPORAL_FEATURES,
        'B (B* + Synchronization)': LOCAL_FEATURES + B_STAR_FEATURES + SYNC_FEATURES,
        'C (B* + Growth)': LOCAL_FEATURES + B_STAR_FEATURES + GROWTH_FEATURES,
        'D (B* + Synchronization + Growth)': LOCAL_FEATURES + B_STAR_FEATURES + SYNC_FEATURES + GROWTH_FEATURES
    }
    
    models = {}
    thresholds = {}
    
    print("\n--- Training Candidates ---")
    for name, features in candidates.items():
        print(f"Training {name}...")
        X_train = train_df[features]
        y_train = train_df['is_abuse']
        
        X_val = val_df[features]
        y_val = val_df['is_abuse']
        
        model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42, class_weight='balanced')
        model.fit(X_train, y_train)
        
        thresh = select_threshold(model, X_val, y_val)
        models[name] = model
        thresholds[name] = thresh
        
    print("\n--- Evaluating Candidates on Robustness Variants ---")
    
    for c_name, features in candidates.items():
        print(f"\n======================================")
        print(f"Candidate: {c_name}")
        model = models[c_name]
        thresh = thresholds[c_name]
        
        baseline_metrics = evaluate_variant(model, thresh, features, extracted_variants['baseline'][0], extracted_variants['baseline'][1])
        print(f"\n[BASELINE]")
        print(f"F1: {baseline_metrics['f1']:.4f} | FPR: {baseline_metrics['fpr']:.4f} | Cov: {baseline_metrics['coverage']:.2f} | TTD: {baseline_metrics['median_ttd_mins']}m")
        
        for v_name in ['jitter', 'low_and_slow', 'amount']:
            if v_name not in extracted_variants: continue
            
            ext_df, v_camp = extracted_variants[v_name]
            metrics = evaluate_variant(model, thresh, features, ext_df, v_camp)
            
            f1_diff = metrics['f1'] - baseline_metrics['f1']
            ttd_diff = (metrics['median_ttd_mins'] or 0) - (baseline_metrics['median_ttd_mins'] or 0)
            cov_diff = metrics['coverage'] - baseline_metrics['coverage']
            
            print(f"\n[{v_name.upper()}]")
            print(f"F1: {metrics['f1']:.4f} ({f1_diff:+.4f}) | Cov: {metrics['coverage']:.2f} ({cov_diff:+.2f}) | TTD: {metrics['median_ttd_mins']}m ({ttd_diff:+.1f}m)")

if __name__ == "__main__":
    run_robustness()
