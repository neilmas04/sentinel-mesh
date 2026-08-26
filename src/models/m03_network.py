import pandas as pd
import numpy as np
from datetime import datetime
import os
import json
import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix, precision_recall_curve, auc

from src.features.local_features import LocalFeatureExtractor
from src.features.network_features import NetworkFeatureExtractor

# Ensure reproducibility
np.random.seed(42)

COST_FP = 10.0  # Ops cost of a false positive
COST_FN = 100.0 # Financial loss of a missed fraud
MAX_FPR = 0.05  # Maximum 5% FPR allowed

def prepare_data(cohort_name: str, labels_df: pd.DataFrame) -> pd.DataFrame:
    """Loads transactions for a cohort, extracts local & network features, and joins labels."""
    print(f"Loading data for cohort: {cohort_name}")
    tx_path = f"data/generated/m01-world-v1/cohorts/{cohort_name}/transactions.csv"
    df = pd.read_csv(tx_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Extract merchant-local features
    local_extractor = LocalFeatureExtractor()
    df = local_extractor.extract_features(df)
    
    # Extract network features
    network_extractor = NetworkFeatureExtractor()
    df = network_extractor.extract_features(df)
    
    # Join with ground truth for training/evaluation
    df = df.merge(labels_df[['transaction_id', 'is_abuse']], on='transaction_id', how='left')
    return df

def calculate_metrics(y_true, y_pred, y_prob):
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    
    precision, recall, _ = precision_recall_curve(y_true, y_prob)
    pr_auc = auc(recall, precision)
    
    expected_cost = float((fp * COST_FP) + (fn * COST_FN))
    
    return {
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "fpr": float(fpr),
        "pr_auc": float(pr_auc),
        "expected_cost": expected_cost,
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)}
    }

def alert_criterion(camp_txs: pd.DataFrame):
    flagged = camp_txs[camp_txs['predicted_fraud'] == 1]
    if len(flagged) > 0:
        return flagged['timestamp'].min()
    return None

def evaluate_ttd(test_eval_df: pd.DataFrame, test_campaigns: pd.DataFrame) -> dict:
    if len(test_campaigns) == 0:
        return None
        
    detected_times = []
    loss_before_detection_list = []
    
    for _, campaign in test_campaigns.iterrows():
        camp_id = campaign['campaign_id']
        start_ts = campaign['start_timestamp']
        
        # All test transactions for this campaign
        camp_txs = test_eval_df[test_eval_df['campaign_id'] == camp_id]
        
        detection_time = alert_criterion(camp_txs)
        
        # Calculate Loss Before Detection (only sum true fraud amounts)
        fraud_txs = camp_txs[camp_txs['is_abuse'] == 1]
        
        if detection_time is not None:
            ttd_mins = (detection_time - start_ts).total_seconds() / 60.0
            detected_times.append(ttd_mins)
            loss = fraud_txs[fraud_txs['timestamp'] < detection_time]['amount'].sum()
        else:
            loss = fraud_txs['amount'].sum()
            
        loss_before_detection_list.append(loss)
            
    detected_count = len(detected_times)
    total_campaigns = len(test_campaigns)
    
    return {
        'total_campaigns': total_campaigns,
        'detected_count': detected_count,
        'missed_count': total_campaigns - detected_count,
        'coverage': float(detected_count / total_campaigns) if total_campaigns > 0 else 0.0,
        'median_ttd_mins': float(np.median(detected_times)) if detected_count > 0 else None,
        'p95_ttd_mins': float(np.percentile(detected_times, 95)) if detected_count > 0 else None,
        'mean_loss_before_detection': float(np.mean(loss_before_detection_list)) if len(loss_before_detection_list) > 0 else 0.0
    }

def select_threshold(model, X_val, y_val):
    y_val_prob = model.predict_proba(X_val)[:, 1]
    precisions, recalls, thresholds = precision_recall_curve(y_val, y_val_prob)
    
    best_cost = float('inf')
    best_thresh = 1.0
    
    for thresh in thresholds:
        y_pred_t = (y_val_prob >= thresh).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_val, y_pred_t).ravel()
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        
        if fpr <= MAX_FPR:
            cost = (fp * COST_FP) + (fn * COST_FN)
            if cost < best_cost:
                best_cost = cost
                best_thresh = thresh
                
    return float(best_thresh)

def run_experiment():
    print("Loading event labels...")
    labels_df = pd.read_csv("data/generated/m01-world-v1/ground_truth/event_labels.csv")
    campaigns_df = pd.read_csv("data/generated/m01-world-v1/ground_truth/campaigns.csv")
    campaigns_df['start_timestamp'] = pd.to_datetime(campaigns_df['start_timestamp'])
    
    # 1. Prepare Data
    train_df = prepare_data("train", labels_df)
    val_df = prepare_data("validation", labels_df)
    test_df = prepare_data("test", labels_df)
    
    test_eval_df_base = test_df.merge(labels_df[['transaction_id', 'campaign_id']], on='transaction_id', how='left')
    test_campaigns = campaigns_df[campaigns_df['cohort'] == 'test'].copy()
    
    # Feature Groups
    LOCAL_FEATURES = [
        'amount', 
        'local_account_txns_1h', 'local_account_txns_24h', 
        'local_device_txns_1h', 'local_device_txns_24h',
        'local_account_amt_1h', 'local_account_amt_24h'
    ]
    
    DEVICE_FEATURES = [
        'network_device_accounts_24h', 'network_device_merchants_24h'
    ]
    
    NETWORK_GROUP_FEATURES = [
        'network_group_accounts_24h', 'network_group_merchants_24h'
    ]
    
    ACCOUNT_RELATIONSHIP_FEATURES = [
        'network_account_devices_24h', 'network_account_merchants_24h',
        'network_account_devices_7d', 'network_account_merchants_7d'
    ]
    
    ALL_NETWORK_FEATURES = DEVICE_FEATURES + NETWORK_GROUP_FEATURES + ACCOUNT_RELATIONSHIP_FEATURES
    
    TARGET = 'is_abuse'
    
    ablations = {
        'System A (Local Only)': LOCAL_FEATURES,
        'System B (Local + Device)': LOCAL_FEATURES + DEVICE_FEATURES,
        'System B (Local + Network Group)': LOCAL_FEATURES + NETWORK_GROUP_FEATURES,
        'System B (Local + Account)': LOCAL_FEATURES + ACCOUNT_RELATIONSHIP_FEATURES,
        'System B (Local + All Network)': LOCAL_FEATURES + ALL_NETWORK_FEATURES
    }
    
    results = {}
    best_system_b_f1 = 0
    
    print("\nStarting Ablation Training & Evaluation...")
    for name, features in ablations.items():
        print(f"\n--- {name} ---")
        X_train = train_df[features]
        y_train = train_df[TARGET]
        
        X_val = val_df[features]
        y_val = val_df[TARGET]
        
        X_test = test_df[features]
        y_test = test_df[TARGET]
        
        # We use RandomForestClassifier as it was typically selected in System A for better non-linear feature handling
        # or we could evaluate both. For simplicity and consistency with M02 (if RF was chosen), we'll use RF.
        # Actually, let's just train RandomForestClassifier as our primary evaluator for Network Features.
        model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42, class_weight='balanced')
        model.fit(X_train, y_train)
        
        threshold = select_threshold(model, X_val, y_val)
        print(f"Selected Threshold: {threshold:.4f}")
        
        y_test_prob = model.predict_proba(X_test)[:, 1]
        y_test_pred = (y_test_prob >= threshold).astype(int)
        
        test_df_eval = test_eval_df_base.copy()
        test_df_eval['predicted_fraud'] = y_test_pred
        test_df_eval['predicted_prob'] = y_test_prob
        
        metrics = calculate_metrics(y_test, y_test_pred, y_test_prob)
        ttd_metrics = evaluate_ttd(test_df_eval, test_campaigns)
        
        # Merge metrics
        full_metrics = {**metrics, **ttd_metrics}
        results[name] = {
            'features': features,
            'threshold': threshold,
            'metrics': full_metrics
        }
        
        print(f"F1: {full_metrics['f1']:.4f}, FPR: {full_metrics['fpr']:.4f}")
        print(f"Coverage: {full_metrics['coverage']:.2f}, Median TTD (mins): {full_metrics['median_ttd_mins']}")
        print(f"Expected Cost: ${full_metrics['expected_cost']:.2f}")
        
        # Save model if it's the best System B (All Network)
        if name == 'System B (Local + All Network)':
            artifact_dir = "artifacts/experiments/m03_system_b"
            os.makedirs(artifact_dir, exist_ok=True)
            model_path = os.path.join(artifact_dir, "system_b_model.pkl")
            joblib.dump(model, model_path)
            
            # Save results
            metadata = {
                "timestamp": datetime.utcnow().isoformat(),
                "ablations": results
            }
            with open(os.path.join(artifact_dir, "metadata.json"), "w") as f:
                json.dump(metadata, f, indent=2)

    print("\n--- ABLATION RESULTS SAVED ---")

if __name__ == "__main__":
    run_experiment()
