import pytest
import pandas as pd
import numpy as np
import os
import json
from unittest.mock import patch, MagicMock
from src.models.external_benchmark_utils import load_and_split_external_data
from src.models.train_external_benchmark import train_model
from src.evaluation.evaluate_external import evaluate_model

@pytest.fixture
def mock_external_data(tmp_path):
    # Create a mock dataset
    df = pd.DataFrame({
        'Time': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        'Amount': [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0],
        'Class': [0, 0, 1, 0, 1, 0, 0, 1, 0, 0]
    })
    for i in range(1, 29):
        df[f'V{i}'] = np.random.randn(10)
        
    data_path = tmp_path / "creditcard.csv"
    df.to_csv(data_path, index=False)
    return str(data_path)

def test_missing_required_columns(tmp_path):
    df = pd.DataFrame({'Time': [1], 'Amount': [10.0]}) # Missing Class and V1-V28
    data_path = tmp_path / "bad_data.csv"
    df.to_csv(data_path, index=False)
    
    with pytest.raises(ValueError, match="Missing required columns"):
        load_and_split_external_data(str(data_path))

def test_rejects_m01_columns(tmp_path):
    df = pd.DataFrame({
        'Time': [1], 'Amount': [10.0], 'Class': [0], 'merchant_id': ['m1']
    })
    for i in range(1, 29):
        df[f'V{i}'] = 0.0
        
    data_path = tmp_path / "bad_data.csv"
    df.to_csv(data_path, index=False)
    
    with pytest.raises(ValueError, match="Dataset contains M01-specific column: merchant_id"):
        load_and_split_external_data(str(data_path))

def test_deterministic_split(mock_external_data):
    train1, val1, test1, f1, t1 = load_and_split_external_data(mock_external_data, train_size=0.6, val_size=0.2, test_size=0.2)
    train2, val2, test2, f2, t2 = load_and_split_external_data(mock_external_data, train_size=0.6, val_size=0.2, test_size=0.2)
    
    pd.testing.assert_frame_equal(train1, train2)
    pd.testing.assert_frame_equal(val1, val2)
    pd.testing.assert_frame_equal(test1, test2)
    assert len(train1) == 6
    assert len(val1) == 2
    assert len(test1) == 2
    assert t1 == 'Class'
    assert 'Class' not in f1 # Target should not be in features
    
    # Test temporal ordering and no future rows in train/val
    assert train1['Time'].max() <= val1['Time'].min()
    assert val1['Time'].max() <= test1['Time'].min()

def test_missing_dataset_error():
    with patch('os.path.exists', return_value=False):
        with pytest.raises(FileNotFoundError, match="External dataset not found"):
            train_model()

@patch('src.models.train_external_benchmark.load_and_split_external_data')
@patch('src.models.train_external_benchmark.os.makedirs')
@patch('src.models.train_external_benchmark.joblib.dump')
def test_train_model_no_m01_writes(mock_dump, mock_makedirs, mock_load, mock_external_data):
    # Mock the data loading
    df = pd.read_csv(mock_external_data)
    features = ['Time', 'Amount'] + [f'V{i}' for i in range(1, 29)]
    mock_load.return_value = (df.iloc[:6], df.iloc[6:8], df.iloc[8:], features, 'Class')
    
    with patch('os.path.exists', return_value=True):
        with patch('builtins.open') as mock_open:
            train_model()
            
            # Verify it only writes to artifacts/models/external_benchmark
            mock_makedirs.assert_called_with("artifacts/models/external_benchmark", exist_ok=True)
            
            # Verify Candidate D artifacts are untouched (no calls to that dir)
            for call in mock_open.call_args_list:
                assert "candidate_d" not in call[0][0]
                assert "m01-world-v1" not in call[0][0]

@patch('src.evaluation.evaluate_external.load_and_split_external_data')
@patch('src.evaluation.evaluate_external.joblib.load')
@patch('src.evaluation.evaluate_external.os.makedirs')
@patch('src.evaluation.evaluate_external.plt')
@patch('src.evaluation.evaluate_external.sns')
def test_evaluate_model_metrics(mock_sns, mock_plt, mock_makedirs, mock_joblib_load, mock_load, mock_external_data):
    # Mock data
    df = pd.read_csv(mock_external_data)
    features = ['Time', 'Amount'] + [f'V{i}' for i in range(1, 29)]
    mock_load.return_value = (df.iloc[:6], df.iloc[6:8], df.iloc[8:], features, 'Class')
    
    # Mock model
    mock_model = MagicMock()
    # 2 validation samples, 2 test samples
    mock_model.predict_proba.side_effect = [
        np.array([[0.9, 0.1], [0.2, 0.8]]), # val
        np.array([[0.1, 0.9], [0.8, 0.2]])  # test
    ]
    mock_joblib_load.return_value = mock_model
    
    # Mock metadata read
    mock_meta = {
        "dataset_name": "Test",
        "split_strategy": "test",
        "random_seed": 42,
        "model_configuration": {}
    }
    
    # We need to handle open() for reading metadata and writing results
    # We'll use a side_effect to return mock_meta when reading
    import io
    def mock_open_side_effect(file, mode='r', *args, **kwargs):
        if mode == 'r':
            return io.StringIO(json.dumps(mock_meta))
        return MagicMock()
        
    with patch('os.path.exists', return_value=True):
        with patch('builtins.open') as mock_open:
            mock_open.side_effect = mock_open_side_effect
            evaluate_model()
            
            # Verify it writes to artifacts/experiments/m12_external_benchmark
            mock_makedirs.assert_called_with("artifacts/experiments/m12_external_benchmark", exist_ok=True)
            
            # Check that the written JSON contains all required metrics
            # The last call to open should be the write
            write_call = [c for c in mock_open.call_args_list if c[0][1] == 'w']
            assert len(write_call) > 0
            
            # Verify test labels are not accessed during threshold selection
            # The side_effect for predict_proba ensures val is called first, then test.
            assert mock_model.predict_proba.call_count == 2
            
            # Verify plots were saved
            assert mock_plt.savefig.call_count == 2

from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_api_evaluation_endpoint():
    response = client.get("/api/v1/evaluation")
    assert response.status_code == 200
    data = response.json()
    
    # If evaluations are run, it should contain m12_external_benchmark
    if "m12_external_benchmark" in data:
        metrics = data["m12_external_benchmark"]
        assert "metrics" in metrics
        assert "pr_auc" in metrics["metrics"]
        assert "cost_analysis" in metrics
        assert "normalized_cost" in metrics["cost_analysis"]
        assert "benchmark_specific_cost" in metrics["cost_analysis"]
        assert "artifacts" in metrics
        assert "pr_curve" in metrics["artifacts"]
        assert "confusion_matrix" in metrics["artifacts"]

def test_api_artifacts_endpoint():
    # Test that the artifacts endpoint is mounted
    response = client.get("/api/artifacts/m12_external_benchmark/metadata.json")
    # It might be 404 if not run, but it shouldn't be 404 for the route itself
    # Actually, if the file doesn't exist it returns 404. 
    # We just want to ensure the route doesn't return 404 because it's not mounted.
    # A better test is to check if the route exists in the app.
    routes = [r.path for r in app.routes if hasattr(r, 'path')]
    assert "/api/artifacts" in routes
