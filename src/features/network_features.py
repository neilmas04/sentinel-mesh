# src/features/network_features.py
import pandas as pd
from typing import Dict, List, Tuple
from datetime import datetime

class NetworkFeatureExtractor:
    """
    Simulates Sentinel Mesh's cross-merchant intelligence layer.
    Tracks entity relationships across the ENTIRE network chronologically,
    strictly respecting causal ordering (as-of timestamp).
    """
    def __init__(self):
        # Format: { entity_id: [(timestamp, linked_entity_1, linked_entity_2)] }
        self.device_history: Dict[str, List[Tuple[datetime, str, str]]] = {}
        self.network_history: Dict[str, List[Tuple[datetime, str, str]]] = {}
        self.account_history: Dict[str, List[Tuple[datetime, str, str]]] = {}

    def extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Iterates chronologically to compute point-in-time network features."""
        
        # Sort by timestamp to ensure causal processing
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        f_device_accounts_24h = []
        f_device_merchants_24h = []
        
        f_network_accounts_24h = []
        f_network_merchants_24h = []
        
        f_account_devices_24h = []
        f_account_merchants_24h = []
        f_account_devices_7d = []
        f_account_merchants_7d = []

        print("Extracting Network-Global Features (Sentinel Mesh)...")
        
        for _, row in df.iterrows():
            current_time = row['timestamp']
            device_id = row['device_id']
            network_id = row['network_group_id']
            account_id = row['account_id']
            merchant_id = row['merchant_id']
            
            # --- 1. DEVICE RELATIONSHIPS ---
            if device_id not in self.device_history:
                self.device_history[device_id] = []
                
            cutoff_24h = current_time - pd.Timedelta(hours=24)
            cutoff_7d = current_time - pd.Timedelta(days=7)
            
            # Strictly past events
            past_device_events = [e for e in self.device_history[device_id] if e[0] < current_time]
            dev_events_24h = [e for e in past_device_events if e[0] >= cutoff_24h]
            
            f_device_accounts_24h.append(len(set([e[1] for e in dev_events_24h])))
            f_device_merchants_24h.append(len(set([e[2] for e in dev_events_24h])))
            
            # --- 2. NETWORK GROUP RELATIONSHIPS ---
            if network_id not in self.network_history:
                self.network_history[network_id] = []
                
            past_network_events = [e for e in self.network_history[network_id] if e[0] < current_time]
            net_events_24h = [e for e in past_network_events if e[0] >= cutoff_24h]
            
            f_network_accounts_24h.append(len(set([e[1] for e in net_events_24h])))
            f_network_merchants_24h.append(len(set([e[2] for e in net_events_24h])))
            
            # --- 3. ACCOUNT RELATIONSHIPS ---
            if account_id not in self.account_history:
                self.account_history[account_id] = []
                
            past_account_events = [e for e in self.account_history[account_id] if e[0] < current_time]
            acc_events_24h = [e for e in past_account_events if e[0] >= cutoff_24h]
            acc_events_7d = [e for e in past_account_events if e[0] >= cutoff_7d]
            
            f_account_devices_24h.append(len(set([e[1] for e in acc_events_24h])))
            f_account_merchants_24h.append(len(set([e[2] for e in acc_events_24h])))
            
            f_account_devices_7d.append(len(set([e[1] for e in acc_events_7d])))
            f_account_merchants_7d.append(len(set([e[2] for e in acc_events_7d])))
            
            # --- 4. UPDATE STATE WITH CURRENT EVENT ---
            # Append to history so future transactions can see this one
            self.device_history[device_id].append((current_time, account_id, merchant_id))
            self.network_history[network_id].append((current_time, account_id, merchant_id))
            self.account_history[account_id].append((current_time, device_id, merchant_id))

        # Attach features to a copy of the dataframe
        result_df = df.copy()
        result_df['network_device_accounts_24h'] = f_device_accounts_24h
        result_df['network_device_merchants_24h'] = f_device_merchants_24h
        
        result_df['network_group_accounts_24h'] = f_network_accounts_24h
        result_df['network_group_merchants_24h'] = f_network_merchants_24h
        
        result_df['network_account_devices_24h'] = f_account_devices_24h
        result_df['network_account_merchants_24h'] = f_account_merchants_24h
        result_df['network_account_devices_7d'] = f_account_devices_7d
        result_df['network_account_merchants_7d'] = f_account_merchants_7d

        return result_df