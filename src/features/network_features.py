# src/features/network_features.py
import pandas as pd
from typing import Dict, List, Tuple
from datetime import datetime

class NetworkFeatureExtractor:
    """
    Simulates Sentinel Mesh's cross-merchant intelligence layer.
    Tracks entity relationships across the ENTIRE network chronologically.
    """
    def __init__(self):
        # Track history within a rolling time window. 
        # Format: { entity_id: [(timestamp, linked_account_id, linked_merchant_id)] }
        self.device_history: Dict[str, List[Tuple[datetime, str, str]]] = {}
        self.network_history: Dict[str, List[Tuple[datetime, str, str]]] = {}

    def extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        f_device_accounts_24h = []
        f_device_merchants_24h = []
        f_network_accounts_24h = []

        print("Extracting Network-Global Features (Sentinel Mesh)...")
        
        for _, row in df.iterrows():
            current_time = row['timestamp']
            device_id = row['device_id']
            network_id = row['network_id']
            account_id = row['account_id']
            merchant_id = row['merchant_id']
            
            # --- DEVICE NETWORK GRAPH ---
            if device_id not in self.device_history:
                self.device_history[device_id] = []
                
            # Filter to last 24 hours to simulate a rolling graph
            cutoff_24h = current_time - pd.Timedelta(hours=24)
            valid_device_events = [e for e in self.device_history[device_id] if e[0] >= cutoff_24h]
            
            # Calculate unique graph relationships (The Core Differentiator)
            unique_accounts_on_device = len(set([e[1] for e in valid_device_events]))
            unique_merchants_on_device = len(set([e[2] for e in valid_device_events]))
            
            f_device_accounts_24h.append(unique_accounts_on_device)
            f_device_merchants_24h.append(unique_merchants_on_device)
            
            # Update State with the current transaction
            self.device_history[device_id] = valid_device_events + [(current_time, account_id, merchant_id)]
            
            # --- IP/NETWORK GRAPH ---
            if network_id not in self.network_history:
                self.network_history[network_id] = []
                
            valid_network_events = [e for e in self.network_history[network_id] if e[0] >= cutoff_24h]
            unique_accounts_on_network = len(set([e[1] for e in valid_network_events]))
            
            f_network_accounts_24h.append(unique_accounts_on_network)
            
            self.network_history[network_id] = valid_network_events + [(current_time, account_id, merchant_id)]

        # Attach features to a copy of the dataframe
        result_df = df.copy()
        result_df['global_device_accounts_24h'] = f_device_accounts_24h
        result_df['global_device_merchants_24h'] = f_device_merchants_24h
        result_df['global_network_accounts_24h'] = f_network_accounts_24h

        return result_df

if __name__ == "__main__":
    df = pd.read_csv("data/generated/train.csv")
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    extractor = NetworkFeatureExtractor()
    enhanced_df = extractor.extract_features(df)
    
    print("\nNetwork extraction complete.")
    print("Checking for shared devices (where Sentinel Mesh finds its evidence):")
    
    # Filter to prove the graph actually detects linked accounts
    suspicious_rows = enhanced_df[enhanced_df['global_device_accounts_24h'] > 1]
    
    cols_to_show = ['device_id', 'global_device_accounts_24h', 'global_device_merchants_24h', 'is_fraud']
    if not suspicious_rows.empty:
        print(suspicious_rows[cols_to_show].head(10))
    else:
        print(enhanced_df[cols_to_show].head(10))