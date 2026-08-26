import pytest
import pandas as pd
from src.features.temporal_features import TemporalFeatureExtractor

@pytest.fixture
def dummy_temporal_transactions():
    data = {
        'transaction_id': ['tx1', 'tx2', 'tx3', 'tx4'],
        'timestamp': [
            pd.to_datetime('2026-01-01 10:00:00'),
            pd.to_datetime('2026-01-01 10:04:00'),
            pd.to_datetime('2026-01-01 11:30:00'),
            pd.to_datetime('2026-01-01 09:59:00') # out of order
        ],
        'merchant_id': ['m1', 'm2', 'm3', 'm1'],
        'account_id': ['a1', 'a1', 'a1', 'a2'],
        'device_id': ['d1', 'd2', 'd1', 'd1'],
        'network_group_id': ['n1', 'n1', 'n1', 'n1'],
        'amount': [100.0, 50.0, 200.0, 10.0]
    }
    return pd.DataFrame(data)

def test_rolling_and_synchronization_features(dummy_temporal_transactions):
    extractor = TemporalFeatureExtractor()
    df_features = extractor.extract_features(dummy_temporal_transactions)
    
    # Sorting order: tx4 (09:59), tx1 (10:00), tx2 (10:04), tx3 (11:30)
    
    # tx4 (09:59)
    assert df_features.iloc[0]['transaction_id'] == 'tx4'
    assert df_features.iloc[0]['temporal_device_txns_5m'] == 0
    assert df_features.iloc[0]['temporal_network_sync_5m'] == 0
    
    # tx1 (10:00)
    assert df_features.iloc[1]['transaction_id'] == 'tx1'
    assert df_features.iloc[1]['temporal_device_txns_5m'] == 1 # tx4 was at 09:59 on d1
    assert df_features.iloc[1]['temporal_network_sync_5m'] == 1 # tx4 was at 09:59 on n1
    
    # tx2 (10:04)
    assert df_features.iloc[2]['transaction_id'] == 'tx2'
    assert df_features.iloc[2]['temporal_account_txns_5m'] == 1 # tx1 was at 10:00 on a1
    assert df_features.iloc[2]['temporal_network_sync_5m'] == 2 # tx4 (09:59), tx1 (10:00)
    
    # tx3 (11:30)
    assert df_features.iloc[3]['transaction_id'] == 'tx3'
    # > 1 hour gap, so 5m counts should be 0
    assert df_features.iloc[3]['temporal_device_txns_5m'] == 0
    assert df_features.iloc[3]['temporal_account_txns_5m'] == 0
    assert df_features.iloc[3]['temporal_network_sync_5m'] == 0

def test_cluster_growth_newly_linked_features():
    # tx1 at 10:00: a1 uses d1 for first time.
    # tx2 at 10:30: a1 uses d2 for first time.
    # tx3 at 11:15: a1 uses d1 again.
    # tx4 at 12:00: a1 uses d3 for first time.
    data = {
        'transaction_id': ['tx1', 'tx2', 'tx3', 'tx4'],
        'timestamp': [
            pd.to_datetime('2026-01-01 10:00:00'),
            pd.to_datetime('2026-01-01 10:30:00'),
            pd.to_datetime('2026-01-01 11:15:00'),
            pd.to_datetime('2026-01-01 12:00:00')
        ],
        'merchant_id': ['m1', 'm1', 'm1', 'm1'],
        'account_id': ['a1', 'a1', 'a1', 'a1'],
        'device_id': ['d1', 'd2', 'd1', 'd3'],
        'network_group_id': ['n1', 'n1', 'n1', 'n1'],
        'amount': [10.0, 10.0, 10.0, 10.0]
    }
    df = pd.DataFrame(data)
    extractor = TemporalFeatureExtractor()
    df_features = extractor.extract_features(df)
    
    # tx1 (10:00)
    assert df_features.iloc[0]['temporal_account_new_devices_1h'] == 0 # no history
    
    # tx2 (10:30)
    # At 10:30, a1's known devices is d1 (seen at 10:00).
    # 10:00 is within 1h (cutoff 09:30). So d1 is a "new device in last 1h".
    assert df_features.iloc[1]['temporal_account_new_devices_1h'] == 1
    
    # tx3 (11:15)
    # Known devices before 11:15: d1(10:00), d2(10:30).
    # 1h cutoff is 10:15.
    # d1 was seen at 10:00, which is < 10:15, so it is NOT "newly linked in last 1h".
    # d2 was seen at 10:30, which is >= 10:15, so it IS "newly linked in last 1h".
    assert df_features.iloc[2]['temporal_account_new_devices_1h'] == 1
    
    # tx4 (12:00)
    # Known: d1(10:00), d2(10:30).
    # 1h cutoff is 11:00.
    # d1(10:00) < 11:00 -> old.
    # d2(10:30) < 11:00 -> old.
    assert df_features.iloc[3]['temporal_account_new_devices_1h'] == 0
