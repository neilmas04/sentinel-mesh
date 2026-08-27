import os
import json
import joblib
from datetime import datetime, UTC
from sklearn.ensemble import RandomForestClassifier
from src.models.external_benchmark_utils import load_and_split_external_data

def train_model():
    print("Training External Benchmark Model...")
    data_path = "data/external/creditcard.csv"
    
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"External dataset not found at {data_path}. Please download it.")
        
    train_df, val_df, test_df, features, target = load_and_split_external_data(data_path)
    
    X_train = train_df[features]
    y_train = train_df[target]
    
    # Use a reproducible random seed
    model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42, class_weight='balanced')
    model.fit(X_train, y_train)
    
    artifact_dir = "artifacts/models/external_benchmark"
    os.makedirs(artifact_dir, exist_ok=True)
    
    model_path = os.path.join(artifact_dir, "model.pkl")
    joblib.dump(model, model_path)
    
    metadata = {
        "model_version": "external_benchmark_v1",
        "dataset_name": "Kaggle Credit Card Fraud Detection",
        "exported_at": datetime.now(UTC).isoformat(),
        "features": features,
        "split_strategy": "temporal_64_16_20",
        "random_seed": 42,
        "model_configuration": {
            "type": "RandomForestClassifier",
            "n_estimators": 100,
            "max_depth": 5,
            "class_weight": "balanced"
        }
    }
    
    with open(os.path.join(artifact_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)
        
    print(f"Model exported to {artifact_dir}")

if __name__ == "__main__":
    train_model()
