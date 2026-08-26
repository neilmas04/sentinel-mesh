import os
import json
import joblib
import pandas as pd
from datetime import datetime, UTC
from sklearn.ensemble import RandomForestClassifier
from src.models.m04_temporal import prepare_data, select_threshold

def export_model():
    print("Exporting M05 Candidate D Model...")
    labels_df = pd.read_csv("data/generated/m01-world-v1/ground_truth/event_labels.csv")
    
    train_df = prepare_data("train", labels_df)
    val_df = prepare_data("validation", labels_df)
    
    LOCAL_FEATURES = [
        'amount', 'local_account_txns_1h', 'local_account_txns_24h', 
        'local_device_txns_1h', 'local_device_txns_24h',
        'local_account_amt_1h', 'local_account_amt_24h'
    ]
    B_STAR_FEATURES = [
        'network_device_accounts_24h', 'network_device_merchants_24h',
        'network_account_devices_24h', 'network_account_merchants_24h',
        'network_account_devices_7d', 'network_account_merchants_7d'
    ]
    SYNC_FEATURES = ['temporal_network_sync_5m', 'temporal_network_sync_15m']
    GROWTH_FEATURES = ['temporal_account_new_devices_1h', 'temporal_device_new_accounts_1h']
    
    # Candidate D
    features = LOCAL_FEATURES + B_STAR_FEATURES + SYNC_FEATURES + GROWTH_FEATURES
    
    X_train = train_df[features]
    y_train = train_df['is_abuse']
    
    X_val = val_df[features]
    y_val = val_df['is_abuse']
    
    model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42, class_weight='balanced')
    model.fit(X_train, y_train)
    
    threshold = select_threshold(model, X_val, y_val)
    print(f"Selected Threshold: {threshold:.4f}")
    
    artifact_dir = "artifacts/models/candidate_d"
    os.makedirs(artifact_dir, exist_ok=True)
    
    model_path = os.path.join(artifact_dir, "model.pkl")
    joblib.dump(model, model_path)
    
    metadata = {
        "model_version": "candidate_d_v1",
        "dataset_version": "m01-world-v1",
        "exported_at": datetime.now(UTC).isoformat(),
        "threshold": threshold,
        "features": features
    }
    
    with open(os.path.join(artifact_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)
        
    print(f"Model exported to {artifact_dir}")

if __name__ == "__main__":
    export_model()
