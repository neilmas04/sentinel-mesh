import pandas as pd
from typing import Dict, List, Tuple
from datetime import datetime

class TemporalFeatureExtractor:
    """
    Simulates Sentinel Mesh's Temporal and Emerging-Risk Detection layer.
    Extracts rolling window activity, cluster growth rates, and synchronization
    metrics, strictly enforcing causal as-of timestamps.
    """
    def __init__(self):
        # Tracking transaction timestamps.
        # { entity_id: [timestamp] }
        self.device_tx_history: Dict[str, List[datetime]] = {}
        self.network_tx_history: Dict[str, List[datetime]] = {}
        self.account_tx_history: Dict[str, List[datetime]] = {}
        
        # Tracking first-seen linking times.
        # { entity_id: { linked_entity_id: first_seen_timestamp } }
        self.account_devices: Dict[str, Dict[str, datetime]] = {}
        self.device_accounts: Dict[str, Dict[str, datetime]] = {}

    def extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # Rolling activity (5 min)
        f_device_txns_5m = []
        f_account_txns_5m = []
        
        # Synchronization (network-level burst)
        f_network_sync_5m = []
        f_network_sync_15m = []
        
        # Growth Rate (newly linked entities in last 1h)
        f_account_new_devices_1h = []
        f_device_new_accounts_1h = []
        
        print("Extracting Temporal/Emerging-Risk Features...")
        
        for _, row in df.iterrows():
            current_time = row['timestamp']
            device_id = row['device_id']
            network_id = row['network_group_id']
            account_id = row['account_id']
            
            cutoff_5m = current_time - pd.Timedelta(minutes=5)
            cutoff_15m = current_time - pd.Timedelta(minutes=15)
            cutoff_1h = current_time - pd.Timedelta(hours=1)
            
            # --- 1. ROLLING ACTIVITY (Global across all merchants) ---
            dev_txs = [t for t in self.device_tx_history.get(device_id, []) if t < current_time]
            acc_txs = [t for t in self.account_tx_history.get(account_id, []) if t < current_time]
            net_txs = [t for t in self.network_tx_history.get(network_id, []) if t < current_time]
            
            f_device_txns_5m.append(sum(1 for t in dev_txs if t >= cutoff_5m))
            f_account_txns_5m.append(sum(1 for t in acc_txs if t >= cutoff_5m))
            
            # --- 2. SYNCHRONIZATION ---
            f_network_sync_5m.append(sum(1 for t in net_txs if t >= cutoff_5m))
            f_network_sync_15m.append(sum(1 for t in net_txs if t >= cutoff_15m))
            
            # --- 3. CLUSTER GROWTH (Newly Linked Entities) ---
            # Account's new devices in last 1h
            acc_devs = self.account_devices.get(account_id, {})
            # Only count devices where first_seen < current_time (strictly past) 
            # AND first_seen >= cutoff_1h (newly seen within 1h)
            new_devs_1h = sum(1 for d, first_ts in acc_devs.items() if cutoff_1h <= first_ts < current_time)
            f_account_new_devices_1h.append(new_devs_1h)
            
            # Device's new accounts in last 1h
            dev_accs = self.device_accounts.get(device_id, {})
            new_accs_1h = sum(1 for a, first_ts in dev_accs.items() if cutoff_1h <= first_ts < current_time)
            f_device_new_accounts_1h.append(new_accs_1h)
            
            # --- UPDATE STATE ---
            if device_id not in self.device_tx_history:
                self.device_tx_history[device_id] = []
            self.device_tx_history[device_id].append(current_time)
            
            if account_id not in self.account_tx_history:
                self.account_tx_history[account_id] = []
            self.account_tx_history[account_id].append(current_time)
            
            if network_id not in self.network_tx_history:
                self.network_tx_history[network_id] = []
            self.network_tx_history[network_id].append(current_time)
            
            if account_id not in self.account_devices:
                self.account_devices[account_id] = {}
            if device_id not in self.account_devices[account_id]:
                self.account_devices[account_id][device_id] = current_time
                
            if device_id not in self.device_accounts:
                self.device_accounts[device_id] = {}
            if account_id not in self.device_accounts[device_id]:
                self.device_accounts[device_id][account_id] = current_time

        result_df = df.copy()
        result_df['temporal_device_txns_5m'] = f_device_txns_5m
        result_df['temporal_account_txns_5m'] = f_account_txns_5m
        result_df['temporal_network_sync_5m'] = f_network_sync_5m
        result_df['temporal_network_sync_15m'] = f_network_sync_15m
        result_df['temporal_account_new_devices_1h'] = f_account_new_devices_1h
        result_df['temporal_device_new_accounts_1h'] = f_device_new_accounts_1h

        return result_df
