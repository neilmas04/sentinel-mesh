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

# Ensure reproducibility
np.random.seed(42)

def prepare_data(cohort_name: str, labels_df: pd.DataFrame) -> pd.DataFrame:
    """Loads transactions for a cohort, extracts local features, and joins labels."""
    print(f"Loading data for cohort: {cohort_name}")
    tx_path = f"data/generated/m01-world-v1/cohorts/{cohort_name}/transactions.csv"
    df = pd.read_csv(tx_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Extract merchant-local features only
    extractor = LocalFeatureExtractor()
    df = extractor.extract_features(df)
    
    # Join with ground truth for training/evaluation purposes ONLY
    # TARGET VS FEATURES: 'is_abuse' must NEVER appear in model features, preprocessing, or inference inputs.
    df = df.merge(labels_df[['transaction_id', 'is_abuse']], on='transaction_id', how='left')
    return df

def calculate_metrics(y_true, y_pred, y_prob):
    """Calculates standard classification metrics."""
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    
    precision, recall, _ = precision_recall_curve(y_true, y_prob)
    pr_auc = auc(recall, precision)
    
    return {
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "fpr": float(fpr),
        "pr_auc": float(pr_auc),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)}
    }

def evaluate_ttd(test_eval_df: pd.DataFrame, test_campaigns: pd.DataFrame, alert_criterion: callable) -> dict:
    """
    Calculates Time-To-Detection metrics using a modular alert criterion.
    
    alert_criterion: A function that takes a DataFrame of transactions for a campaign
                     and returns the timestamp of detection, or None if missed.
    """
    if len(test_campaigns) == 0:
        return None
        
    detected_times = []
    
    for _, campaign in test_campaigns.iterrows():
        camp_id = campaign['campaign_id']
        start_ts = campaign['start_timestamp']
        
        # All transactions belonging to this campaign in the test set
        camp_txs = test_eval_df[test_eval_df['campaign_id'] == camp_id]
        
        # Apply the modular alert criterion
        detection_time = alert_criterion(camp_txs)
        
        if detection_time is not None:
            ttd_mins = (detection_time - start_ts).total_seconds() / 60.0
            detected_times.append(ttd_mins)
            
    detected_count = len(detected_times)
    total_campaigns = len(test_campaigns)
    
    return {
        'total_campaigns': total_campaigns,
        'detected_count': detected_count,
        'missed_count': total_campaigns - detected_count,
        'coverage': float(detected_count / total_campaigns) if total_campaigns > 0 else 0.0,
        'median_ttd_mins': float(np.median(detected_times)) if detected_count > 0 else None,
        'p95_ttd_mins': float(np.percentile(detected_times, 95)) if detected_count > 0 else None
    }

def m02_alert_criterion(camp_txs: pd.DataFrame):
    """
    M02 Rule: The campaign is considered detected when the first test transaction 
    belonging to that campaign is flagged by the frozen System A threshold.
    """
    flagged = camp_txs[camp_txs['predicted_fraud'] == 1]
    if len(flagged) > 0:
        return flagged['timestamp'].min()
    return None

def run_pipeline():
    print("Loading event labels...")
    labels_df = pd.read_csv("data/generated/m01-world-v1/ground_truth/event_labels.csv")
    campaigns_df = pd.read_csv("data/generated/m01-world-v1/ground_truth/campaigns.csv")
    campaigns_df['start_timestamp'] = pd.to_datetime(campaigns_df['start_timestamp'])
    
    # 1. Train Cohort
    train_df = prepare_data("train", labels_df)
    
    FEATURES = [
        'amount', 
        'local_account_txns_1h', 'local_account_txns_24h', 
        'local_device_txns_1h', 'local_device_txns_24h',
        'local_account_amt_1h', 'local_account_amt_24h'
    ]
    TARGET = 'is_abuse'
    
    X_train = train_df[FEATURES]
    y_train = train_df[TARGET]
    
    print("\nTraining Baseline Models...")
    lr_model = LogisticRegression(random_state=42, class_weight='balanced', max_iter=1000)
    lr_model.fit(X_train, y_train)
    
    rf_model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42, class_weight='balanced')
    rf_model.fit(X_train, y_train)
    
    # 2. Validation Cohort - Threshold Selection
    val_df = prepare_data("validation", labels_df)
    X_val = val_df[FEATURES]
    y_val = val_df[TARGET]
    
    print("\nEvaluating on Validation Cohort...")
    models = {'LogisticRegression': lr_model, 'RandomForest': rf_model}
    
    # Cost Assumptions
    COST_FP = 10.0  # Ops cost of a false positive
    COST_FN = 100.0 # Financial loss of a missed fraud
    MAX_FPR = 0.05  # Maximum 5% FPR allowed
    
    best_model_name = None
    best_cost = float('inf')
    best_threshold = None
    
    model_thresholds = {}
    
    for name, model in models.items():
        y_val_prob = model.predict_proba(X_val)[:, 1]
        
        precisions, recalls, thresholds = precision_recall_curve(y_val, y_val_prob)
        f1_scores = np.divide(2 * (precisions * recalls), (precisions + recalls), out=np.zeros_like(precisions), where=(precisions + recalls) != 0)
        
        # 2a. F1-Optimal Threshold
        f1_opt_idx = np.argmax(f1_scores)
        f1_threshold = thresholds[f1_opt_idx] if f1_opt_idx < len(thresholds) else 1.0
        
        # 2b. Cost-Aware Threshold
        model_best_cost = float('inf')
        cost_threshold = 1.0
        
        for thresh in thresholds:
            y_pred_t = (y_val_prob >= thresh).astype(int)
            tn, fp, fn, tp = confusion_matrix(y_val, y_pred_t).ravel()
            fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
            
            if fpr <= MAX_FPR:
                cost = (fp * COST_FP) + (fn * COST_FN)
                if cost < model_best_cost:
                    model_best_cost = cost
                    cost_threshold = thresh
                    
        print(f"[{name}] F1-Optimal Threshold: {f1_threshold:.4f} (F1: {f1_scores[f1_opt_idx]:.4f})")
        print(f"[{name}] Cost-Aware Threshold: {cost_threshold:.4f} (Cost: {model_best_cost:.2f})")
        
        model_thresholds[name] = {
            'f1_thresh': f1_threshold,
            'cost_thresh': cost_threshold,
            'best_cost': model_best_cost
        }
        
        if model_best_cost < best_cost:
            best_cost = model_best_cost
            best_threshold = cost_threshold
            best_model_name = name

    print(f"\nSelected {best_model_name} as System A baseline.")
    print(f"We selected the Cost-Aware threshold ({best_threshold:.4f}) over the F1-optimal threshold.")
    print("Why: Maximizing F1 assumes FP and FN have roughly symmetrical importance or is unaware of business impact. " 
          "The cost-aware threshold explicitly minimizes financial loss while respecting our maximum FPR constraint (5%).")
    
    final_model = models[best_model_name]
    
    # 3. Test Cohort - Final Evaluation
    test_df = prepare_data("test", labels_df)
    X_test = test_df[FEATURES]
    y_test = test_df[TARGET]
    
    y_test_prob = final_model.predict_proba(X_test)[:, 1]
    y_test_pred = (y_test_prob >= best_threshold).astype(int)
    
    test_df['predicted_fraud'] = y_test_pred
    test_df['predicted_prob'] = y_test_prob
    
    metrics = calculate_metrics(y_test, y_test_pred, y_test_prob)
    
    # TTD Evaluation
    print("\nCalculating TTD...")
    test_eval_df = test_df.merge(labels_df[['transaction_id', 'campaign_id']], on='transaction_id', how='left')
    test_campaigns = campaigns_df[campaigns_df['cohort'] == 'test'].copy()
    
    metrics['ttd'] = evaluate_ttd(test_eval_df, test_campaigns, m02_alert_criterion)

    print("\n--- FINAL TEST METRICS ---")
    print(json.dumps(metrics, indent=2))
    
    # 4. Persistence
    artifact_dir = "artifacts/experiments/m02_baseline"
    os.makedirs(artifact_dir, exist_ok=True)
    
    model_path = os.path.join(artifact_dir, "system_a_model.pkl")
    joblib.dump(final_model, model_path)
    
    metadata = {
        "timestamp": datetime.utcnow().isoformat(),
        "dataset_version": "m01-world-v1",
        "random_seed": 42,
        "feature_version": "v1.0.local",
        "features": FEATURES,
        "model_type": best_model_name,
        "threshold_strategy": "cost-aware",
        "threshold": float(best_threshold),
        "metrics": metrics
    }
    
    with open(os.path.join(artifact_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)
        
    print(f"\nArtifacts saved to {artifact_dir}")

if __name__ == "__main__":
    run_pipeline()
