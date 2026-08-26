import pytest
import pandas as pd
import numpy as np
from src.data.perturbation import generate_robustness_variants

@pytest.fixture
def dummy_test_data():
    df = pd.DataFrame({
        'transaction_id': ['tx1', 'tx2', 'tx3', 'tx4'],
        'timestamp': [
            pd.to_datetime('2026-01-01 10:00:00'),
            pd.to_datetime('2026-01-01 10:15:00'),
            pd.to_datetime('2026-01-01 10:30:00'),
            pd.to_datetime('2026-01-01 10:45:00')
        ],
        'amount': [100.0, 100.0, 100.0, 100.0]
    })
    
    labels_df = pd.DataFrame({
        'transaction_id': ['tx1', 'tx2', 'tx3', 'tx4'],
        'is_abuse': [0, 1, 1, 0],
        'campaign_id': [np.nan, 'c1', 'c1', np.nan]
    })
    
    campaigns_df = pd.DataFrame({
        'campaign_id': ['c1'],
        'start_timestamp': [pd.to_datetime('2026-01-01 10:15:00')]
    })
    
    return df, labels_df, campaigns_df

def test_perturbation_low_and_slow(dummy_test_data):
    df, labels, campaigns = dummy_test_data
    variants = generate_robustness_variants(df, labels, campaigns)
    
    df_slow, camp_slow = variants['low_and_slow']
    
    # tx1 (normal) stays at 10:00
    # tx2 (abuse) starts at 10:15.
    # tx3 (abuse) was at 10:30 (15m after tx2). Expanded 5x -> 10:15 + (15m * 5) = 11:30.
    # tx4 (normal) stays at 10:45.
    
    # Check new sorting and timestamps
    # Expected order: tx1(10:00), tx2(10:15), tx4(10:45), tx3(11:30)
    assert df_slow.iloc[0]['transaction_id'] == 'tx1'
    assert df_slow.iloc[1]['transaction_id'] == 'tx2'
    assert df_slow.iloc[2]['transaction_id'] == 'tx4'
    assert df_slow.iloc[3]['transaction_id'] == 'tx3'
    
    assert df_slow.iloc[3]['timestamp'] == pd.to_datetime('2026-01-01 11:30:00')
    
    # Check campaign start time
    assert camp_slow.iloc[0]['start_timestamp'] == pd.to_datetime('2026-01-01 10:15:00')

def test_perturbation_amount(dummy_test_data):
    df, labels, campaigns = dummy_test_data
    variants = generate_robustness_variants(df, labels, campaigns)
    
    df_amount, _ = variants['amount']
    
    # Normal amount unchanged
    assert df_amount[df_amount['transaction_id'] == 'tx1']['amount'].iloc[0] == 100.0
    # Abuse amount changed
    assert df_amount[df_amount['transaction_id'] == 'tx2']['amount'].iloc[0] != 100.0
    assert 50.0 <= df_amount[df_amount['transaction_id'] == 'tx2']['amount'].iloc[0] <= 200.0
