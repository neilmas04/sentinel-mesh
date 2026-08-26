# src/features/local_features.py
import pandas as pd
from typing import Dict, List, Tuple
from datetime import datetime

class LocalFeatureExtractor:
    """
    Simulates a real-time production feature store.
    Calculates features using ONLY data isolated to a single merchant, 
    strictly relying on past events to guarantee zero temporal leakage.
    """
    def __init__(self):
        # State dictionaries tracking historical events per merchant
        # Structure: { merchant_id: { account_id: [(datetime, amount), ...] } }
        self.merchant_account_history: Dict[str, Dict[str, List[Tuple[datetime, float]]]] = {}
        self.merchant_device_history: Dict[str, Dict[str, List[Tuple[datetime, float]]]] = {}

    def extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Iterates chronologically to compute point-in-time features."""
        
        # Sort by timestamp to ensure causal processing
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # Feature lists to append as new columns
        f_account_txns_1h = []
        f_account_txns_24h = []
        f_device_txns_1h = []
        f_device_txns_24h = []
        
        f_account_amt_1h = []
        f_account_amt_24h = []

        print("Extracting Merchant-Local Features (Streaming Simulation)...")
        
        for _, row in df.iterrows():
            merchant_id = row['merchant_id']
            account_id = row['account_id']
            device_id = row['device_id']
            current_time = row['timestamp']
            amount = row['amount']

            # Initialize merchant isolation state if new
            if merchant_id not in self.merchant_account_history:
                self.merchant_account_history[merchant_id] = {}
                self.merchant_device_history[merchant_id] = {}

            # 1. Look up historical events (BEFORE adding current transaction)
            acc_history = self.merchant_account_history[merchant_id].get(account_id, [])
            dev_history = self.merchant_device_history[merchant_id].get(device_id, [])

            # 2. Compute features based on strict historical state
            # Strict inequality `ts < current_time` to absolutely prevent temporal leakage
            acc_history_1h = [x for x in acc_history if current_time - pd.Timedelta(hours=1) <= x[0] < current_time]
            acc_history_24h = [x for x in acc_history if current_time - pd.Timedelta(hours=24) <= x[0] < current_time]
            
            dev_history_1h = [x for x in dev_history if current_time - pd.Timedelta(hours=1) <= x[0] < current_time]
            dev_history_24h = [x for x in dev_history if current_time - pd.Timedelta(hours=24) <= x[0] < current_time]

            f_account_txns_1h.append(len(acc_history_1h))
            f_account_txns_24h.append(len(acc_history_24h))
            f_device_txns_1h.append(len(dev_history_1h))
            f_device_txns_24h.append(len(dev_history_24h))
            
            f_account_amt_1h.append(sum(x[1] for x in acc_history_1h))
            f_account_amt_24h.append(sum(x[1] for x in acc_history_24h))

            # 3. Update the state with the current transaction
            if account_id not in self.merchant_account_history[merchant_id]:
                self.merchant_account_history[merchant_id][account_id] = []
            self.merchant_account_history[merchant_id][account_id].append((current_time, amount))

            if device_id not in self.merchant_device_history[merchant_id]:
                self.merchant_device_history[merchant_id][device_id] = []
            self.merchant_device_history[merchant_id][device_id].append((current_time, amount))

        # Attach features to a copy of the dataframe
        result_df = df.copy()
        result_df['local_account_txns_1h'] = f_account_txns_1h
        result_df['local_account_txns_24h'] = f_account_txns_24h
        result_df['local_device_txns_1h'] = f_device_txns_1h
        result_df['local_device_txns_24h'] = f_device_txns_24h
        result_df['local_account_amt_1h'] = f_account_amt_1h
        result_df['local_account_amt_24h'] = f_account_amt_24h

        return result_df