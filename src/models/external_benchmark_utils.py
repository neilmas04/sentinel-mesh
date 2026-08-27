import pandas as pd
import numpy as np

def load_and_split_external_data(filepath: str, train_size: float = 0.64, val_size: float = 0.16, test_size: float = 0.20):
    """
    Loads the external dataset, validates columns, and performs a temporal split into train/val/test.
    """
    df = pd.read_csv(filepath)
    
    expected_cols = ['Time', 'Amount', 'Class'] + [f'V{i}' for i in range(1, 29)]
    missing_cols = [c for c in expected_cols if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
        
    # Reject M01 specific columns
    m01_cols = ['merchant_id', 'account_id', 'device_id', 'is_abuse']
    for c in m01_cols:
        if c in df.columns:
            raise ValueError(f"Dataset contains M01-specific column: {c}")
            
    # Sort by Time for temporal split
    df = df.sort_values('Time').reset_index(drop=True)
    
    total_len = len(df)
    train_idx = int(total_len * train_size)
    val_idx = train_idx + int(total_len * val_size)
    
    train_df = df.iloc[:train_idx].copy()
    val_df = df.iloc[train_idx:val_idx].copy()
    test_df = df.iloc[val_idx:].copy()
    
    features = ['Time', 'Amount'] + [f'V{i}' for i in range(1, 29)]
    target = 'Class'
    
    return train_df, val_df, test_df, features, target
