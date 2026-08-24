# src/features/local_features.py
import pandas as pd
from typing import Dict, List
from datetime import datetime

class LocalFeatureExtractor:
    """
    Simulates a real-time production feature store.
    Calculates features using ONLY data isolated to a single merchant, 
    strictly relying on past events to guarantee zero temporal leakage.
    """
    def __init__(self):
        # State dictionaries tracking historical timestamps per merchant
        # Structure: { merchant_id: { account_id: [datetime, datetime, ...] } }
        self.merchant_account_history: Dict[str, Dict[str, List[datetime]]] = {}
        self.merchant_device_history: Dict[str, Dict[str, List[datetime]]] = {}

    def _clean_old_events(self, timestamps: List[datetime], current_time: datetime, window_hours: int = 24) -> List[datetime]:
        """Keeps only timestamps within the rolling window."""
        cutoff = current_time - pd.Timedelta(hours=window_hours)
        return [ts for ts in timestamps if ts >= cutoff]

    def extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Iterates chronologically to compute point-in-time features."""
        
        # Feature lists to append as new columns
        f_account_txns_1h = []
        f_account_txns_24h = []
        f_device_txns_1h = []
        f_device_txns_24h = []

        print("Extracting Merchant-Local Features (Streaming Simulation)...")
        
        for _, row in df.iterrows():
            merchant_id = row['merchant_id']
            account_id = row['account_id']
            device_id = row['device_id']
            current_time = row['timestamp']

            # Initialize merchant isolation state if new
            if merchant_id not in self.merchant_account_history:
                self.merchant_account_history[merchant_id] = {}
                self.merchant_device_history[merchant_id] = {}

            # 1. Look up historical events (BEFORE adding current transaction)
            acc_history = self.merchant_account_history[merchant_id].get(account_id, [])
            dev_history = self.merchant_device_history[merchant_id].get(device_id, [])

            # 2. Compute features based on strict historical state
            acc_history_1h = [ts for ts in acc_history if ts >= current_time - pd.Timedelta(hours=1)]
            acc_history_24h = [ts for ts in acc_history if ts >= current_time - pd.Timedelta(hours=24)]
            
            dev_history_1h = [ts for ts in dev_history if ts >= current_time - pd.Timedelta(hours=1)]
            dev_history_24h = [ts for ts in dev_history if ts >= current_time - pd.Timedelta(hours=24)]

            f_account_txns_1h.append(len(acc_history_1h))
            f_account_txns_24h.append(len(acc_history_24h))
            f_device_txns_1h.append(len(dev_history_1h))
            f_device_txns_24h.append(len(dev_history_24h))

            # 3. Update the state with the current transaction
            if account_id not in self.merchant_account_history[merchant_id]:
                self.merchant_account_history[merchant_id][account_id] = []
            self.merchant_account_history[merchant_id][account_id].append(current_time)

            if device_id not in self.merchant_device_history[merchant_id]:
                self.merchant_device_history[merchant_id][device_id] = []
            self.merchant_device_history[merchant_id][device_id].append(current_time)

            # Prune memory to keep it fast (optional optimization for massive datasets)
            # self.merchant_account_history[merchant_id][account_id] = self._clean_old_events(...)

        # Attach features to a copy of the dataframe
        result_df = df.copy()
        result_df['local_account_txns_1h'] = f_account_txns_1h
        result_df['local_account_txns_24h'] = f_account_txns_24h
        result_df['local_device_txns_1h'] = f_device_txns_1h
        result_df['local_device_txns_24h'] = f_device_txns_24h

        return result_df

if __name__ == "__main__":
    # Quick test to ensure it works
    df = pd.read_csv("data/generated/train.csv")
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    extractor = LocalFeatureExtractor()
    enhanced_df = extractor.extract_features(df)
    
    print("\nFeature extraction complete. Sample output:")
    cols_to_show = ['merchant_id', 'account_id', 'local_account_txns_1h', 'local_device_txns_1h', 'is_fraud']
    print(enhanced_df[cols_to_show].head(10))