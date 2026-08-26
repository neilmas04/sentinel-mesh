import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.features.merchant_spike import MerchantSpikeDetector

def create_mock_transactions(merchant_id, start_time, bucket_size_hours, num_buckets, tx_per_bucket, flagged_indices=None):
    if flagged_indices is None:
        flagged_indices = set()
        
    records = []
    tx_id_counter = 0
    flagged_tx_ids = set()
    
    for b in range(num_buckets):
        # Time within the bucket
        bucket_start = start_time + timedelta(hours=b * bucket_size_hours)
        for i in range(tx_per_bucket):
            tx_id = f"tx_{tx_id_counter}"
            # Spread transactions evenly within the bucket
            tx_time = bucket_start + timedelta(minutes=(60 * bucket_size_hours / tx_per_bucket) * i)
            records.append({
                "transaction_id": tx_id,
                "timestamp": tx_time,
                "merchant_id": merchant_id,
                "amount": 100.0
            })
            if tx_id_counter in flagged_indices:
                flagged_tx_ids.add(tx_id)
            tx_id_counter += 1
            
    df = pd.DataFrame(records)
    return df, flagged_tx_ids

def test_temporal_leakage_and_calculations():
    # 6 baseline buckets + 1 current bucket = 7 buckets total
    # bucket_size = 1h, lookback = 6
    start_time = datetime(2026, 1, 1, 0, 0)
    
    # Let's flag exactly 1 transaction in bucket 1, 2 in bucket 2, etc.
    # tx_per_bucket = 10
    # Bucket 0 (oldest): 0 flagged
    # Bucket 1: 1 flagged (tx 10)
    # Bucket 2: 2 flagged (tx 20, 21)
    # Bucket 3: 3 flagged (tx 30, 31, 32)
    # Bucket 4: 4 flagged (tx 40, 41, 42, 43)
    # Bucket 5: 5 flagged (tx 50, 51, 52, 53, 54)
    # Bucket 6 (current): 8 flagged (tx 60..67)
    
    flagged = {10, 20, 21, 30, 31, 32, 40, 41, 42, 43, 50, 51, 52, 53, 54, 60, 61, 62, 63, 64, 65, 66, 67}
    df, flagged_ids = create_mock_transactions("M1", start_time, 1, 7, 10, flagged)
    
    # Current time is exactly at the end of bucket 6
    current_time = start_time + timedelta(hours=7)
    
    detector = MerchantSpikeDetector(bucket_size='1h', lookback_window=6)
    res = detector.compute_spike("M1", pd.Timestamp(current_time), df, flagged_ids)
    
    assert res["merchant_id"] == "M1"
    assert res["baseline_insufficient"] is False
    assert res["total_transactions"] == 10
    assert res["flagged_transactions"] == 8
    assert res["flagged_rate"] == 0.8
    
    # Baseline rates: 0.0, 0.1, 0.2, 0.3, 0.4, 0.5
    # Mean = 0.15 / 6 = 0.25
    assert np.isclose(res["baseline_mean"], 0.25)
    
    # Std dev (population): values = [0, 0.1, 0.2, 0.3, 0.4, 0.5]
    # Variance = sum((x - 0.25)^2) / 6 = (0.0625 + 0.0225 + 0.0025 + 0.0025 + 0.0225 + 0.0625) / 6 = 0.175 / 6 = 0.0291666
    # Std = sqrt(0.0291666) = 0.17078
    expected_std = np.std([0.0, 0.1, 0.2, 0.3, 0.4, 0.5])
    assert np.isclose(res["baseline_std"], expected_std)
    
    # Rate multiplier = 0.8 / 0.25 = 3.2
    assert np.isclose(res["rate_multiplier"], 3.2)
    
    # Spike score = (0.8 - 0.25) / 0.17078 = 3.22
    expected_score = (0.8 - 0.25) / expected_std
    assert np.isclose(res["spike_score"], expected_score)
    
    # Severity: score >= 3 -> HIGH
    assert res["severity"] == "HIGH"

def test_future_buckets_exclusion():
    start_time = datetime(2026, 1, 1, 0, 0)
    # 8 buckets total, but we query at end of bucket 6
    df, flagged_ids = create_mock_transactions("M1", start_time, 1, 8, 10, {60, 70, 71})
    
    current_time = start_time + timedelta(hours=7) # End of bucket 6
    detector = MerchantSpikeDetector(bucket_size='1h', lookback_window=6)
    res = detector.compute_spike("M1", pd.Timestamp(current_time), df, flagged_ids)
    
    # Bucket 7 (future) has 2 flagged, but should be excluded
    # Bucket 6 (current) has 1 flagged
    # Baseline has 0 flagged
    assert res["total_transactions"] == 10
    assert res["flagged_transactions"] == 1
    assert res["baseline_mean"] == 0.0
    assert res["severity"] == "CRITICAL" # Zero-baseline emergence

def test_zero_baseline_emergence():
    start_time = datetime(2026, 1, 1, 0, 0)
    df, flagged_ids = create_mock_transactions("M1", start_time, 1, 7, 10, {60}) # Only current bucket has flagged
    current_time = start_time + timedelta(hours=7)
    
    detector = MerchantSpikeDetector(bucket_size='1h', lookback_window=6)
    res = detector.compute_spike("M1", pd.Timestamp(current_time), df, flagged_ids)
    
    assert res["baseline_mean"] == 0.0
    assert res["rate_multiplier"] is None
    assert res["spike_score"] is None
    assert res["severity"] == "CRITICAL"

def test_zero_baseline_normal():
    start_time = datetime(2026, 1, 1, 0, 0)
    df, flagged_ids = create_mock_transactions("M1", start_time, 1, 7, 10, set()) # No flagged at all
    current_time = start_time + timedelta(hours=7)
    
    detector = MerchantSpikeDetector(bucket_size='1h', lookback_window=6)
    res = detector.compute_spike("M1", pd.Timestamp(current_time), df, flagged_ids)
    
    assert res["baseline_mean"] == 0.0
    assert res["rate_multiplier"] == 1.0
    assert res["spike_score"] == 0.0
    assert res["severity"] == "NORMAL"

def test_insufficient_baseline():
    start_time = datetime(2026, 1, 1, 0, 0)
    # Only 4 buckets total
    df, flagged_ids = create_mock_transactions("M1", start_time, 1, 4, 10, set())
    current_time = start_time + timedelta(hours=4)
    
    detector = MerchantSpikeDetector(bucket_size='1h', lookback_window=6)
    res = detector.compute_spike("M1", pd.Timestamp(current_time), df, flagged_ids)
    
    assert res["baseline_insufficient"] is True
    assert res["baseline_mean"] is None
    assert res["severity"] == "NORMAL"

def test_deterministic_execution():
    start_time = datetime(2026, 1, 1, 0, 0)
    df, flagged_ids = create_mock_transactions("M1", start_time, 1, 7, 10, {10, 20, 60})
    current_time = start_time + timedelta(hours=7)
    
    detector = MerchantSpikeDetector(bucket_size='1h', lookback_window=6)
    res1 = detector.compute_spike("M1", pd.Timestamp(current_time), df, flagged_ids)
    res2 = detector.compute_spike("M1", pd.Timestamp(current_time), df, flagged_ids)
    
    assert res1 == res2

def test_live_observation_flagged():
    start_time = datetime(2026, 1, 1, 0, 0)
    # 6 baseline buckets, 0 current bucket transactions
    df, flagged_ids = create_mock_transactions("M1", start_time, 1, 6, 10, set())
    current_time = start_time + timedelta(hours=7)
    
    detector = MerchantSpikeDetector(bucket_size='1h', lookback_window=6)
    live_obs = {"live_tx_id": "tx_live", "is_flagged": True}
    res = detector.compute_spike("M1", pd.Timestamp(current_time), df, flagged_ids, live_observation=live_obs)
    
    assert res["total_transactions"] == 1
    assert res["flagged_transactions"] == 1
    assert res["flagged_rate"] == 1.0
    assert res["baseline_mean"] == 0.0
    assert res["severity"] == "CRITICAL"

def test_live_observation_unflagged():
    start_time = datetime(2026, 1, 1, 0, 0)
    df, flagged_ids = create_mock_transactions("M1", start_time, 1, 6, 10, set())
    current_time = start_time + timedelta(hours=7)
    
    detector = MerchantSpikeDetector(bucket_size='1h', lookback_window=6)
    live_obs = {"live_tx_id": "tx_live", "is_flagged": False}
    res = detector.compute_spike("M1", pd.Timestamp(current_time), df, flagged_ids, live_observation=live_obs)
    
    assert res["total_transactions"] == 1
    assert res["flagged_transactions"] == 0
    assert res["flagged_rate"] == 0.0
    assert res["baseline_mean"] == 0.0
    assert res["severity"] == "NORMAL"

def test_live_observation_prevents_double_counting():
    start_time = datetime(2026, 1, 1, 0, 0)
    # 7 buckets, current bucket has 1 transaction (tx_60)
    df, flagged_ids = create_mock_transactions("M1", start_time, 1, 7, 10, {60})
    current_time = start_time + timedelta(hours=7)
    
    detector = MerchantSpikeDetector(bucket_size='1h', lookback_window=6)
    # Pass tx_60 as live observation
    live_obs = {"live_tx_id": "tx_60", "is_flagged": True}
    res = detector.compute_spike("M1", pd.Timestamp(current_time), df, flagged_ids, live_observation=live_obs)
    
    # It should filter out tx_60 from df, leaving 9 transactions in current bucket
    # Then it adds 1 for the live observation, so total = 10
    # Flagged = 0 (from df) + 1 (from live) = 1
    assert res["total_transactions"] == 10
    assert res["flagged_transactions"] == 1
    assert res["flagged_rate"] == 0.1
