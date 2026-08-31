import pytest
import pandas as pd
import json
import os
from src.features.early_warning import EarlyWarningDetector

@pytest.fixture
def sample_config():
    return {
        "detector_version": "test_v1",
        "rule_type": "OR",
        "fpr_target": 0.005,
        "signals": [
            {"feature": "f1", "operator": ">", "threshold": 5.0},
            {"feature": "f2", "operator": ">", "threshold": 1.0}
        ]
    }

@pytest.fixture
def config_file(tmp_path, sample_config):
    config_path = tmp_path / "config.json"
    with open(config_path, "w") as f:
        json.dump(sample_config, f)
    return str(config_path)

def test_early_warning_detector_initialization(config_file):
    detector = EarlyWarningDetector(config_path=config_file)
    assert detector.version == "test_v1"
    assert detector.rule_type == "OR"
    assert len(detector.signals) == 2

def test_early_warning_detector_evaluate_or(config_file):
    detector = EarlyWarningDetector(config_path=config_file)
    
    # Neither triggers
    tx1 = pd.Series({"f1": 4.0, "f2": 0.5, "f3": 10.0})
    res1 = detector.evaluate(tx1)
    assert not res1["triggered"]
    
    # First triggers
    tx2 = pd.Series({"f1": 6.0, "f2": 0.5})
    res2 = detector.evaluate(tx2)
    assert res2["triggered"]
    assert len(res2["signals"]) == 1
    assert res2["signals"][0]["feature"] == "f1"
    
    # Both trigger
    tx3 = pd.Series({"f1": 6.0, "f2": 2.0})
    res3 = detector.evaluate(tx3)
    assert res3["triggered"]
    assert len(res3["signals"]) == 2

def test_early_warning_detector_evaluate_and(tmp_path, sample_config):
    sample_config["rule_type"] = "AND"
    config_path = tmp_path / "config.json"
    with open(config_path, "w") as f:
        json.dump(sample_config, f)
        
    detector = EarlyWarningDetector(config_path=str(config_path))
    
    # One triggers
    tx1 = pd.Series({"f1": 6.0, "f2": 0.5})
    assert not detector.evaluate(tx1)["triggered"]
    
    # Both trigger
    tx2 = pd.Series({"f1": 6.0, "f2": 2.0})
    assert detector.evaluate(tx2)["triggered"]

def test_early_warning_detector_batch(config_file):
    detector = EarlyWarningDetector(config_path=config_file)
    df = pd.DataFrame([
        {"f1": 4.0, "f2": 0.5},
        {"f1": 6.0, "f2": 0.5},
        {"f1": 4.0, "f2": 2.0}
    ])
    preds = detector.evaluate_batch(df)
    assert len(preds) == 3
    assert not preds.iloc[0]
    assert preds.iloc[1]
    assert preds.iloc[2]

def test_actual_config_exists():
    # Verify the actual production config exists and has the right structure
    config_path = "artifacts/models/early_warning/config.json"
    assert os.path.exists(config_path)
    with open(config_path, "r") as f:
        config = json.load(f)
    assert "detector_version" in config
    assert "rule_type" in config
    assert "signals" in config
    assert len(config["signals"]) == 2
    
def test_no_ground_truth_usage(config_file):
    detector = EarlyWarningDetector(config_path=config_file)
    tx = pd.Series({"f1": 6.0, "f2": 2.0, "is_abuse": 0})
    res = detector.evaluate(tx)
    # Ensure is_abuse is not in the triggered signals
    for sig in res["signals"]:
        assert sig["feature"] != "is_abuse"
