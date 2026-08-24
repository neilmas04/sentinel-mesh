# src/models/experiment.py
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_score, recall_score, f1_score

from src.features.local_features import LocalFeatureExtractor
from src.features.network_features import NetworkFeatureExtractor

def prepare_data():
    print("1. Loading full chronological dataset...")
    df = pd.read_csv("data/generated/transactions_full.csv")
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # We process the FULL dataset chronologically to maintain streaming state, 
    # exactly like a real production feature store.
    local_ext = LocalFeatureExtractor()
    network_ext = NetworkFeatureExtractor()
    
    df = local_ext.extract_features(df)
    df = network_ext.extract_features(df)
    
    # Split back into Train (Days 1-4) and Test (Days 6-7)
    train_end = datetime(2026, 1, 5)
    test_start = datetime(2026, 1, 6)
    
    train_df = df[df["timestamp"] < train_end].copy()
    test_df = df[df["timestamp"] >= test_start].copy()
    
    return train_df, test_df

def calculate_business_metrics(df: pd.DataFrame, predictions: np.ndarray, model_name: str):
    """Calculates False Positive Rate and Median Time-To-Detection (TTD)."""
    df_eval = df.copy()
    df_eval['predicted_fraud'] = predictions
    
    # FPR Calculation
    fp = len(df_eval[(df_eval['is_fraud'] == 0) & (df_eval['predicted_fraud'] == 1)])
    tn = len(df_eval[(df_eval['is_fraud'] == 0) & (df_eval['predicted_fraud'] == 0)])
    fpr = (fp / (fp + tn)) * 100 if (fp + tn) > 0 else 0.0
    
    # TTD Calculation
    campaigns = df_eval[(df_eval['is_fraud'] == 1) & (df_eval['campaign_id'].notnull())]
    ttd_list = []
    
    for camp_id, group in campaigns.groupby('campaign_id'):
        start_time = group['timestamp'].min()
        alerts = group[group['predicted_fraud'] == 1]
        if not alerts.empty:
            first_alert_time = alerts['timestamp'].min()
            ttd_minutes = (first_alert_time - start_time).total_seconds() / 60.0
            ttd_list.append(ttd_minutes)
            
    median_ttd = np.median(ttd_list) if ttd_list else float('inf')
    return fpr, median_ttd

def run_experiment():
    train_df, test_df = prepare_data()
    
    # Define Feature Sets
    FEATURES_LOCAL = [
        'amount', 
        'local_account_txns_1h', 'local_account_txns_24h', 
        'local_device_txns_1h', 'local_device_txns_24h'
    ]
    
    FEATURES_NETWORK = FEATURES_LOCAL + [
        'global_device_accounts_24h', 
        'global_device_merchants_24h', 
        'global_network_accounts_24h'
    ]
    
    TARGET = 'is_fraud'
    
    print("\n2. Training System A (Merchant-Local Baseline)...")
    model_a = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42, class_weight='balanced')
    model_a.fit(train_df[FEATURES_LOCAL], train_df[TARGET])
    
    print("3. Training System B (Sentinel Mesh Network Enhanced)...")
    model_b = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42, class_weight='balanced')
    model_b.fit(train_df[FEATURES_NETWORK], train_df[TARGET])
    
    print("\n4. Evaluating on Held-Out Test Set (Future Data)...")
    # Predictions
    preds_a = model_a.predict(test_df[FEATURES_LOCAL])
    preds_b = model_b.predict(test_df[FEATURES_NETWORK])
    
    # Standard ML Metrics
    res_a = {
        "Precision": precision_score(test_df[TARGET], preds_a),
        "Recall": recall_score(test_df[TARGET], preds_a),
        "F1": f1_score(test_df[TARGET], preds_a)
    }
    res_b = {
        "Precision": precision_score(test_df[TARGET], preds_b),
        "Recall": recall_score(test_df[TARGET], preds_b),
        "F1": f1_score(test_df[TARGET], preds_b)
    }
    
    # Business/Hypothesis Metrics
    fpr_a, ttd_a = calculate_business_metrics(test_df, preds_a, "System A")
    fpr_b, ttd_b = calculate_business_metrics(test_df, preds_b, "System B")
    
    print("\n" + "="*50)
    print(" EXPERIMENT RESULTS: LOCAL vs NETWORK INTELLIGENCE")
    print("="*50)
    print(f"{'Metric':<20} | {'System A (Local)':<15} | {'System B (Network)':<15}")
    print("-" * 50)
    print(f"{'Precision':<20} | {res_a['Precision']:.3f}           | {res_b['Precision']:.3f}")
    print(f"{'Recall':<20} | {res_a['Recall']:.3f}           | {res_b['Recall']:.3f}")
    print(f"{'F1 Score':<20} | {res_a['F1']:.3f}           | {res_b['F1']:.3f}")
    print(f"{'False Positive Rate':<20} | {fpr_a:.2f}%            | {fpr_b:.2f}%")
    print(f"{'Median TTD (mins)':<20} | {ttd_a:<15.1f} | {ttd_b:<15.1f}")
    print("="*50)
    
    if ttd_b < ttd_a:
        improvement = ((ttd_a - ttd_b) / ttd_a) * 100
        print(f"\n[HYPOTHESIS PROVED] Sentinel Mesh detected coordinated abuse {improvement:.1f}% faster than the local baseline.")

if __name__ == "__main__":
    run_experiment()