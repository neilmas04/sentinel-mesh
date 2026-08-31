import pytest
import pandas as pd
import numpy as np
import os
from src.data.perturbation_v2 import apply_perturbation

@pytest.fixture
def sample_data():
    labels_df = pd.read_csv("data/generated/m01-world-v1/ground_truth/event_labels.csv")
    campaigns_df = pd.read_csv("data/generated/m01-world-v1/ground_truth/campaigns.csv")
    campaigns_df['start_timestamp'] = pd.to_datetime(campaigns_df['start_timestamp'])
    
    tx_path = "data/generated/m01-world-v1/cohorts/test/transactions.csv"
    raw_test_df = pd.read_csv(tx_path)
    raw_test_df['timestamp'] = pd.to_datetime(raw_test_df['timestamp'])
    test_campaigns = campaigns_df[campaigns_df['cohort'] == 'test'].copy()
    
    return raw_test_df, labels_df, test_campaigns

def test_clean_baseline_determinism(sample_data):
    raw_test_df, labels_df, test_campaigns = sample_data
    
    df1, camp1, map1, status1 = apply_perturbation(raw_test_df, labels_df, test_campaigns, "clean", None, 42)
    df2, camp2, map2, status2 = apply_perturbation(raw_test_df, labels_df, test_campaigns, "clean", None, 42)
    
    assert df1.equals(df2)
    assert camp1.equals(camp2)
    assert status1["label_status"] == "PRESERVED"

def test_perturbation_determinism(sample_data):
    raw_test_df, labels_df, test_campaigns = sample_data
    
    df1, camp1, map1, status1 = apply_perturbation(raw_test_df, labels_df, test_campaigns, "timing_jitter", 30, 42)
    df2, camp2, map2, status2 = apply_perturbation(raw_test_df, labels_df, test_campaigns, "timing_jitter", 30, 42)
    
    assert df1.equals(df2)
    assert camp1.equals(camp2)
    assert map1.equals(map2)

def test_traceability_mapping(sample_data):
    raw_test_df, labels_df, test_campaigns = sample_data
    
    df, camp, mapping, status = apply_perturbation(raw_test_df, labels_df, test_campaigns, "timing_jitter", 30, 42)
    
    assert not mapping.empty
    assert "original_transaction_id" in mapping.columns
    assert "transformed_transaction_id" in mapping.columns
    assert mapping["transformed_transaction_id"].str.endswith("_timing_jitter").all()

def test_synthetic_identities(sample_data):
    raw_test_df, labels_df, test_campaigns = sample_data
    
    df, camp, mapping, status = apply_perturbation(raw_test_df, labels_df, test_campaigns, "device_rotation", 1.0, 42)
    
    # Check that synthetic devices were created
    synth_devices = df[df['device_id'].str.startswith('synth_device_')]
    assert not synth_devices.empty

def test_temporal_ordering(sample_data):
    raw_test_df, labels_df, test_campaigns = sample_data
    
    df, camp, mapping, status = apply_perturbation(raw_test_df, labels_df, test_campaigns, "timing_jitter", 30, 42)
    
    # Check if timestamps are monotonically increasing
    assert df['timestamp'].is_monotonic_increasing

def test_no_mutation_of_m01():
    # Check if the files in data/generated/m01-world-v1/ are modified
    # We can just check if the function apply_perturbation modifies the input dataframes in place
    labels_df = pd.DataFrame({'transaction_id': ['1', '2'], 'is_abuse': [1, 0], 'campaign_id': ['c1', '']})
    campaigns_df = pd.DataFrame({'campaign_id': ['c1'], 'start_timestamp': [pd.Timestamp('2026-01-01')], 'end_timestamp': [pd.Timestamp('2026-01-02')]})
    raw_test_df = pd.DataFrame({'transaction_id': ['1', '2'], 'timestamp': [pd.Timestamp('2026-01-01'), pd.Timestamp('2026-01-02')], 'merchant_id': ['m1', 'm2']})
    
    orig_raw = raw_test_df.copy()
    
    apply_perturbation(raw_test_df, labels_df, campaigns_df, "timing_jitter", 30, 42)
    
    assert raw_test_df.equals(orig_raw)
