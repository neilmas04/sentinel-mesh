import os
import json
import pandas as pd
import numpy as np
from src.features.local_features import LocalFeatureExtractor
from src.features.network_features import NetworkFeatureExtractor
from src.features.temporal_features import TemporalFeatureExtractor

def extract_all_features(df: pd.DataFrame) -> pd.DataFrame:
    df = LocalFeatureExtractor().extract_features(df)
    df = NetworkFeatureExtractor().extract_features(df)
    df = TemporalFeatureExtractor().extract_features(df)
    return df

def extract_thresholds():
    print("Loading datasets...")
    labels_df = pd.read_csv("data/generated/m01-world-v1/ground_truth/event_labels.csv")
    
    # Load Validation data
    val_tx_path = "data/generated/m01-world-v1/cohorts/validation/transactions.csv"
    raw_val_df = pd.read_csv(val_tx_path)
    raw_val_df['timestamp'] = pd.to_datetime(raw_val_df['timestamp'])
    val_ext_df = extract_all_features(raw_val_df)
    val_ext_df = val_ext_df.merge(labels_df[['transaction_id', 'is_abuse']], on='transaction_id', how='left')
    
    val_benign = val_ext_df[val_ext_df['is_abuse'] == 0]
    
    # We want the OR rule at FPR <= 0.5%
    # From Phase 5H, the percentiles were (99.5, 98) for network_device_accounts_24h and temporal_device_new_accounts_1h
    
    t1 = np.percentile(val_benign['network_device_accounts_24h'], 99.5)
    t2 = np.percentile(val_benign['temporal_device_new_accounts_1h'], 98)
    
    print(f"network_device_accounts_24h 99.5th percentile: {t1}")
    print(f"temporal_device_new_accounts_1h 98th percentile: {t2}")
    
    config = {
        "detector_version": "early_warning_v1",
        "rule_type": "OR",
        "fpr_target": 0.005,
        "validation_split": "validation",
        "threshold_source": "m01-world-v1",
        "signals": [
            {
                "feature": "network_device_accounts_24h",
                "operator": ">",
                "threshold": float(t1),
                "percentile": 99.5
            },
            {
                "feature": "temporal_device_new_accounts_1h",
                "operator": ">",
                "threshold": float(t2),
                "percentile": 98.0
            }
        ]
    }
    
    output_dir = "artifacts/models/early_warning"
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "config.json"), "w") as f:
        json.dump(config, f, indent=2)
        
    print("Saved config to artifacts/models/early_warning/config.json")

if __name__ == "__main__":
    extract_thresholds()
