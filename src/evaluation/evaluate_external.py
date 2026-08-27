import os
import json
import joblib
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, UTC
from sklearn.metrics import precision_recall_curve, auc, precision_score, recall_score, f1_score, confusion_matrix
from src.models.external_benchmark_utils import load_and_split_external_data

def evaluate_model():
    print("Evaluating External Benchmark Model...")
    
    model_dir = "artifacts/models/external_benchmark"
    model_path = os.path.join(model_dir, "model.pkl")
    meta_path = os.path.join(model_dir, "metadata.json")
    
    if not os.path.exists(model_path) or not os.path.exists(meta_path):
        raise FileNotFoundError("External benchmark model not found. Run training first.")
        
    model = joblib.load(model_path)
    with open(meta_path, "r") as f:
        model_meta = json.load(f)
        
    data_path = "data/external/creditcard.csv"
    train_df, val_df, test_df, features, target = load_and_split_external_data(data_path)
    
    # 1. Select threshold on VALIDATION ONLY
    X_val = val_df[features]
    y_val = val_df[target]
    y_val_probs = model.predict_proba(X_val)[:, 1]
    
    precision_curve_val, recall_curve_val, thresholds_val = precision_recall_curve(y_val, y_val_probs)
    f1_scores_val = 2 * (precision_curve_val * recall_curve_val) / (precision_curve_val + recall_curve_val + 1e-9)
    best_idx = np.argmax(f1_scores_val)
    best_threshold = float(thresholds_val[best_idx]) if best_idx < len(thresholds_val) else 0.5
    
    val_pr_auc = auc(recall_curve_val, precision_curve_val)
    
    # 2. Evaluate on TEST ONLY
    X_test = test_df[features]
    y_test = test_df[target]
    y_test_probs = model.predict_proba(X_test)[:, 1]
    
    precision_curve_test, recall_curve_test, _ = precision_recall_curve(y_test, y_test_probs)
    test_pr_auc = auc(recall_curve_test, precision_curve_test)
    
    y_pred = (y_test_probs >= best_threshold).astype(int)
    
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    
    tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
    
    # Cost assumptions (same as Sentinel Mesh)
    intervention_cost = 100.0 * fp
    fn_mask = (y_test == 1) & (y_pred == 0)
    fraud_loss = test_df.loc[fn_mask, 'Amount'].sum()
    expected_cost = intervention_cost + fraud_loss
    
    # Normalized cost (Sentinel Mesh convention)
    normalized_fraud_loss = 500.0 * fn
    normalized_expected_cost = intervention_cost + normalized_fraud_loss
    
    exp_dir = "artifacts/experiments/m12_external_benchmark"
    os.makedirs(exp_dir, exist_ok=True)
    
    # Generate PR Curve Plot
    plt.figure(figsize=(8, 6))
    plt.plot(recall_curve_test, precision_curve_test, color='blue', lw=2, label=f'PR Curve (AUC = {test_pr_auc:.4f})')
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.title('Precision-Recall Curve (Test Set)')
    plt.legend(loc='lower left')
    plt.grid(True, alpha=0.3)
    pr_curve_path = os.path.join(exp_dir, "pr_curve.png")
    plt.savefig(pr_curve_path, bbox_inches='tight')
    plt.close()
    
    # Generate Confusion Matrix Plot
    plt.figure(figsize=(6, 5))
    cm = np.array([[tn, fp], [fn, tp]])
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', cbar=False,
                xticklabels=['Predicted 0', 'Predicted 1'],
                yticklabels=['Actual 0', 'Actual 1'])
    plt.title(f'Confusion Matrix (Threshold = {best_threshold:.4f})')
    cm_path = os.path.join(exp_dir, "confusion_matrix.png")
    plt.savefig(cm_path, bbox_inches='tight')
    plt.close()
    
    results = {
        "dataset_name": model_meta["dataset_name"],
        "dataset_source": "https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud",
        "features": features,
        "split_strategy": model_meta["split_strategy"],
        "random_seed": model_meta["random_seed"],
        "model_configuration": model_meta["model_configuration"],
        "validation_metrics": {
            "threshold_selected": best_threshold,
            "pr_auc": float(val_pr_auc),
            "best_f1": float(f1_scores_val[best_idx])
        },
        "metrics": {
            "pr_auc": float(test_pr_auc),
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_positives": int(tp),
            "true_negatives": int(tn)
        },
        "cost_analysis": {
            "benchmark_specific_cost": {
                "assumptions": {
                    "intervention_cost_per_fp": 100.0,
                    "fraud_loss_per_fn": "Actual Transaction Amount"
                },
                "intervention_cost": float(intervention_cost),
                "fraud_loss": float(fraud_loss),
                "expected_total_cost": float(expected_cost)
            },
            "normalized_cost": {
                "assumptions": {
                    "intervention_cost_per_fp": 100.0,
                    "fraud_loss_per_fn": 500.0
                },
                "intervention_cost": float(intervention_cost),
                "fraud_loss": float(normalized_fraud_loss),
                "expected_total_cost": float(normalized_expected_cost)
            }
        },
        "artifacts": {
            "pr_curve": pr_curve_path,
            "confusion_matrix": cm_path
        },
        "evaluated_at": datetime.now(UTC).isoformat()
    }
    
    with open(os.path.join(exp_dir, "metadata.json"), "w") as f:
        json.dump(results, f, indent=2)
        
    print(f"Evaluation complete. Results and plots saved to {exp_dir}")

if __name__ == "__main__":
    evaluate_model()
