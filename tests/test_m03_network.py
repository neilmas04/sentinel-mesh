import pytest
import pandas as pd
from src.features.network_features import NetworkFeatureExtractor

@pytest.fixture
def dummy_network_transactions():
    data = {
        'transaction_id': ['tx1', 'tx2', 'tx3', 'tx4'],
        'timestamp': [
            pd.to_datetime('2026-01-01 10:00:00'),
            pd.to_datetime('2026-01-01 10:30:00'),
            pd.to_datetime('2026-01-01 11:30:00'),
            pd.to_datetime('2026-01-01 09:00:00') # out of order
        ],
        'merchant_id': ['m1', 'm2', 'm3', 'm1'],
        'account_id': ['a1', 'a2', 'a1', 'a3'],
        'device_id': ['d1', 'd1', 'd2', 'd1'],
        'network_group_id': ['n1', 'n1', 'n2', 'n1'],
        'amount': [100.0, 50.0, 200.0, 10.0]
    }
    return pd.DataFrame(data)

def test_no_future_leakage_in_network_features(dummy_network_transactions):
    """Ensure strictly past events are used, and order does not cause future leakage."""
    extractor = NetworkFeatureExtractor()
    df_features = extractor.extract_features(dummy_network_transactions)
    
    # Sorting order should be: tx4 (09:00), tx1 (10:00), tx2 (10:30), tx3 (11:30)
    
    # tx4 (09:00): account a3, device d1, merchant m1, network n1
    assert df_features.iloc[0]['transaction_id'] == 'tx4'
    assert df_features.iloc[0]['network_device_accounts_24h'] == 0
    assert df_features.iloc[0]['network_group_accounts_24h'] == 0
    assert df_features.iloc[0]['network_account_merchants_24h'] == 0
    
    # tx1 (10:00): account a1, device d1, merchant m1, network n1
    assert df_features.iloc[1]['transaction_id'] == 'tx1'
    # d1 saw a3 in tx4
    assert df_features.iloc[1]['network_device_accounts_24h'] == 1 
    # n1 saw a3 in tx4
    assert df_features.iloc[1]['network_group_accounts_24h'] == 1 
    # a1 has no prior history
    assert df_features.iloc[1]['network_account_merchants_24h'] == 0
    
    # tx2 (10:30): account a2, device d1, merchant m2, network n1
    assert df_features.iloc[2]['transaction_id'] == 'tx2'
    # d1 saw a3 (tx4) and a1 (tx1)
    assert df_features.iloc[2]['network_device_accounts_24h'] == 2
    # d1 saw m1 (tx4) and m1 (tx1), so unique merchants = 1
    assert df_features.iloc[2]['network_device_merchants_24h'] == 1
    # n1 saw a3, a1
    assert df_features.iloc[2]['network_group_accounts_24h'] == 2
    
    # tx3 (11:30): account a1, device d2, merchant m3, network n2
    assert df_features.iloc[3]['transaction_id'] == 'tx3'
    # d2 is new
    assert df_features.iloc[3]['network_device_accounts_24h'] == 0
    # a1 was seen in tx1 (m1, d1)
    assert df_features.iloc[3]['network_account_merchants_24h'] == 1
    assert df_features.iloc[3]['network_account_devices_24h'] == 1

def test_cutoff_window(dummy_network_transactions):
    """Test that events outside the 24h window are dropped."""
    data = {
        'transaction_id': ['tx1', 'tx2'],
        'timestamp': [
            pd.to_datetime('2026-01-01 10:00:00'),
            pd.to_datetime('2026-01-02 11:00:00') # > 24 hours later
        ],
        'merchant_id': ['m1', 'm2'],
        'account_id': ['a1', 'a2'],
        'device_id': ['d1', 'd1'],
        'network_group_id': ['n1', 'n1'],
        'amount': [100.0, 50.0]
    }
    df = pd.DataFrame(data)
    extractor = NetworkFeatureExtractor()
    df_features = extractor.extract_features(df)
    
    # tx2 is at 2026-01-02 11:00, > 24 hours after tx1 (2026-01-01 10:00)
    # The 24h window for tx2 starts at 2026-01-01 11:00, so tx1 should be dropped.
    assert df_features.iloc[1]['transaction_id'] == 'tx2'
    assert df_features.iloc[1]['network_device_accounts_24h'] == 0
