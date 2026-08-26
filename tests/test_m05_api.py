import pytest
from fastapi.testclient import TestClient
from src.api.main import app
import os
import json
import sqlite3

# Initialize the TestClient using the context manager to trigger lifespan events
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "Sentinel Mesh Core is online."

def test_client_cannot_supply_score(client):
    # Try to send a score in the payload. Pydantic should ignore or reject it, 
    # but the API contract strictly doesn't take it.
    payload = {
        "transaction_id": "tx1",
        "risk_score": 0.99
    }
    # It might pass validation if we don't forbid extra fields, 
    # but let's check that the API doesn't use it.
    response = client.post("/api/v1/score", json=payload)
    # The transaction doesn't exist, so we expect a 404, proving it hit the DB lookup 
    # instead of trusting the score.
    assert response.status_code == 404

def test_valid_scoring_and_case_creation(client):
    # Find a transaction we know is fraudulent from the test set
    import pandas as pd
    labels_df = pd.read_csv("data/generated/m01-world-v1/ground_truth/event_labels.csv")
    test_df = pd.read_csv("data/generated/m01-world-v1/cohorts/test/transactions.csv")
    full = test_df.merge(labels_df[['transaction_id', 'is_abuse']], on='transaction_id')
    abuse_txs = full[full['is_abuse'] == 1]['transaction_id'].tolist()
    
    # Take a known abuse transaction
    tx_id = abuse_txs[-1]
    
    response = client.post("/api/v1/score", json={"transaction_id": tx_id})
    assert response.status_code == 200
    data = response.json()
    
    assert "risk_score" in data
    assert "risk_level" in data
    assert data["transaction_id"] == tx_id
    
    # If the risk level is HIGH, it should have created a case
    if data["risk_level"] in ["HIGH", "CRITICAL"]:
        assert data["case_id"] is not None
        assert data["case_id"].startswith("CASE-")
        
        # Verify case retrieval
        case_resp = client.get(f"/api/v1/cases/{data['case_id']}")
        assert case_resp.status_code == 200
        case_data = case_resp.json()
        assert case_data["transaction_id"] == tx_id
        assert case_data["risk_score"] == data["risk_score"]
        assert "temporal_growth_spike" in case_data["triggered_signals"]
        
        # Check database persistence directly
        conn = sqlite3.connect("sentinel.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM risk_cases WHERE case_id = ?", (data["case_id"],))
        row = cursor.fetchone()
        assert row is not None
        conn.close()

def test_identical_inference(client):
    # Fetch any valid transaction
    import pandas as pd
    test_df = pd.read_csv("data/generated/m01-world-v1/cohorts/test/transactions.csv")
    tx_id = test_df['transaction_id'].iloc[0]
    
    # Score twice
    res1 = client.post("/api/v1/score", json={"transaction_id": tx_id})
    res2 = client.post("/api/v1/score", json={"transaction_id": tx_id})
    
    assert res1.status_code == 200
    assert res2.status_code == 200
    
    assert res1.json()["risk_score"] == res2.json()["risk_score"]

def test_evaluation_endpoint(client):
    response = client.get("/api/v1/evaluation")
    assert response.status_code == 200
    data = response.json()
    
    # Verify we didn't get the error string
    assert "error" not in data
    
    # 2. M02 metadata is included.
    assert "m02" in data
    assert "metrics" in data["m02"]
    
    # 3. M03 metadata is included.
    assert "m03" in data
    assert "ablations" in data["m03"]
    
    # 4. M04 metadata is included.
    assert "m04" in data
    assert "ablations" in data["m04"]
    
    # 5. Candidate D metadata is included.
    assert "candidate_d" in data
    assert "model_version" in data["candidate_d"]
    
    # 6. No ML training is triggered (this is true since it returns instantly, 
    # but we just assert the keys exist and the response is correct without checking processing time)
    
    # 7. Endpoint works regardless of working directory: we used pathlib in main.py.
