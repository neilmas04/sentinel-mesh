import pytest
import pandas as pd
import numpy as np
from datetime import datetime
import os
import joblib

from src.features.local_features import LocalFeatureExtractor
from src.models.m02_baseline import prepare_data, calculate_metrics

@pytest.fixture
def dummy_transactions():
    data = {
        'transaction_id': ['tx1', 'tx2', 'tx3', 'tx4'],
        'timestamp': [
            pd.to_datetime('2026-01-01 10:00:00'),
            pd.to_datetime('2026-01-01 10:30:00'),
            pd.to_datetime('2026-01-01 11:30:00'),
            pd.to_datetime('2026-01-01 09:00:00') # out of order
        ],
        'merchant_id': ['m1', 'm1', 'm1', 'm1'],
        'account_id': ['a1', 'a1', 'a1', 'a1'],
        'device_id': ['d1', 'd1', 'd1', 'd1'],
        'amount': [100.0, 50.0, 200.0, 10.0]
    }
    return pd.DataFrame(data)

def test_no_ground_truth_fields_in_features(dummy_transactions):
    """Test 1: feature extractor does not expect or use ground truth fields."""
    extractor = LocalFeatureExtractor()
    df_features = extractor.extract_features(dummy_transactions)
    
    forbidden_fields = ['is_fraud', 'is_abuse', 'scenario', 'campaign_id']
    for field in forbidden_fields:
        assert field not in df_features.columns, f"Ground truth field {field} leaked into features!"
        
def test_no_future_events_in_features(dummy_transactions):
    """Test 2: Ensure strictly past events are used, and order does not cause future leakage."""
    extractor = LocalFeatureExtractor()
    df_features = extractor.extract_features(dummy_transactions)
    
    # Sorting order should be: tx4 (09:00), tx1 (10:00), tx2 (10:30), tx3 (11:30)
    assert df_features.iloc[0]['transaction_id'] == 'tx4'
    assert df_features.iloc[0]['local_account_txns_1h'] == 0
    
    assert df_features.iloc[1]['transaction_id'] == 'tx1'
    assert df_features.iloc[1]['local_account_txns_1h'] == 1 # tx4
    assert df_features.iloc[1]['local_account_amt_1h'] == 10.0
    
    assert df_features.iloc[2]['transaction_id'] == 'tx2'
    assert df_features.iloc[2]['local_account_txns_1h'] == 1 # tx1 (tx4 is >1h old)
    assert df_features.iloc[2]['local_account_amt_1h'] == 100.0 # tx1 only
    
    assert df_features.iloc[3]['transaction_id'] == 'tx3'
    # tx4 is at 09:00, tx3 is at 11:30. 09:00 is > 1 hour ago (11:30 - 1h = 10:30)
    # wait, strict inequality: 09:00 is not >= 10:30, so tx4 drops out of 1h window!
    # history for tx3 at 11:30: tx1 (10:00, outside 1h?), 11:30 - 1h = 10:30. 10:00 is outside.
    # So tx2 (10:30) is the only one inside the 1h window. Wait, 10:30 >= 10:30 is TRUE.
    # So tx2 is in, tx1 is out, tx4 is out.
    assert df_features.iloc[3]['local_account_txns_1h'] == 1

def test_metrics_calculated_correctly():
    """Test 8: Ensure metrics are calculated accurately."""
    y_true = np.array([0, 0, 1, 1, 1])
    y_pred = np.array([0, 1, 1, 1, 0])
    y_prob = np.array([0.1, 0.6, 0.8, 0.9, 0.4])
    
    metrics = calculate_metrics(y_true, y_pred, y_prob)
    
    assert metrics['confusion_matrix']['tn'] == 1
    assert metrics['confusion_matrix']['fp'] == 1
    assert metrics['confusion_matrix']['fn'] == 1
    assert metrics['confusion_matrix']['tp'] == 2
    
    assert metrics['precision'] == 2/3
    assert metrics['recall'] == 2/3
    assert metrics['f1'] == 2/3
    assert metrics['fpr'] == 0.5

def test_deterministic_inference_and_reload(tmpdir):
    """Tests 6, 7: Model can be persisted, reloaded, and produces deterministic results."""
    from sklearn.linear_model import LogisticRegression
    X = np.array([[1, 2], [3, 4], [5, 6]])
    y = np.array([0, 1, 1])
    
    model = LogisticRegression(random_state=42).fit(X, y)
    preds1 = model.predict_proba(X)
    
    model_path = os.path.join(tmpdir, "model.pkl")
    joblib.dump(model, model_path)
    
    loaded_model = joblib.load(model_path)
    preds2 = loaded_model.predict_proba(X)
    
    np.testing.assert_array_equal(preds1, preds2)
