import pytest
import pandas as pd
from datetime import datetime, UTC
from src.features.local_features import LocalFeatureExtractor
from src.features.network_features import NetworkFeatureExtractor
from src.features.temporal_features import TemporalFeatureExtractor

def test_no_self_inclusion():
    """
    Test that the extractors do not include the current transaction in its own historical aggregates.
    """
    current_ts = datetime.now(UTC)
    
    # Create two transactions at the exact same timestamp
    # If self-inclusion or same-timestamp inclusion happens, the features will be non-zero.
    data = {
        'transaction_id': ['tx1', 'tx2'],
        'timestamp': [current_ts, current_ts],
        'merchant_id': ['m1', 'm1'],
        'account_id': ['a1', 'a1'],
        'device_id': ['d1', 'd1'],
        'network_group_id': ['n1', 'n1'],
        'amount': [100.0, 500.0]
    }
    df = pd.DataFrame(data)
    
    # 1. Local Features
    local_df = LocalFeatureExtractor().extract_features(df)
    
    # For tx1, historical sum should be 0
    assert local_df.iloc[0]['local_account_amt_1h'] == 0.0
    
    # For tx2, historical sum should ALSO be 0, because tx1 has the EXACT SAME timestamp,
    # and the filter is strictly `ts < current_time`.
    assert local_df.iloc[1]['local_account_amt_1h'] == 0.0
    
    # 2. Network Features
    net_df = NetworkFeatureExtractor().extract_features(local_df)
    
    # For tx1, network accounts should be 0
    assert net_df.iloc[0]['network_device_accounts_24h'] == 0
    
    # For tx2, network accounts should be 0
    assert net_df.iloc[1]['network_device_accounts_24h'] == 0

    # 3. Temporal Features
    temp_df = TemporalFeatureExtractor().extract_features(net_df)
    
    assert temp_df.iloc[0]['temporal_account_new_devices_1h'] == 0
    assert temp_df.iloc[1]['temporal_account_new_devices_1h'] == 0
