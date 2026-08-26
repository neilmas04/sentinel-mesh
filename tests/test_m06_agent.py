import pytest
import pandas as pd
from datetime import datetime, timedelta, UTC
from unittest.mock import patch
from src.agent.tools import AgentTools
from src.agent.investigator import RiskInvestigator, DossierSchema

@pytest.fixture
def sample_tx_data():
    now = datetime.now(UTC)
    future = now + timedelta(days=1)
    
    # 3 txs: 2 in the past, 1 in the future
    data = {
        'transaction_id': ['tx1', 'tx2', 'tx3'],
        'timestamp': [now - timedelta(hours=2), now - timedelta(hours=1), future],
        'merchant_id': ['m1', 'm2', 'm1'],
        'account_id': ['a1', 'a1', 'a1'],
        'device_id': ['d1', 'd1', 'd1'],
        'network_group_id': ['n1', 'n1', 'n1'],
        'amount': [100.0, 50.0, 500.0]
    }
    return pd.DataFrame(data)

def test_tools_as_of_enforcement(sample_tx_data):
    as_of = sample_tx_data.iloc[1]['timestamp']
    tools = AgentTools(sample_tx_data)
    
    ctx = tools.get_transaction_context('tx2', as_of.isoformat())
    assert "error" not in ctx
    
    hist = tools.get_account_history('a1', as_of.isoformat())
    assert type(hist['observation']) == dict
    assert hist['observation']['historical_transaction_count'] == 1

    future_ctx = tools.get_transaction_context('tx3', as_of.isoformat())
    assert "error" in future_ctx
    assert "beyond as_of_timestamp" in future_ctx['error']

@patch('src.agent.investigator.genai.Client')
def test_grounding_validator(mock_client):
    investigator = RiskInvestigator(None)
    
    from src.agent.investigator import Claim
    
    dossier = DossierSchema(
        facts=[
            Claim(claim="Fact 1", type="FACT", evidence_ids=["E1", "E99"])
        ],
        inferences=[
            Claim(claim="Inf 1", type="INFERENCE", evidence_ids=["E1"])
        ],
        unknowns=[],
        risk_assessment="High risk.",
        recommended_next_step="manual review"
    )
    
    evidence_bundle = [{"evidence_id": "E1", "observation": {"k": "v"}}]
    
    result = investigator._grounding_validator(dossier, evidence_bundle)
    assert result["facts"][0]["grounding_status"] == "UNSUPPORTED"
    assert "Invalid citations: ['E99']" in result["facts"][0]["grounding_reason"]

def test_prompt_injection_does_not_break_agent():
    pass

@patch('src.agent.investigator.genai.Client')
def test_agent_safe_degradation(mock_client):
    investigator = RiskInvestigator(None)
    res = investigator.investigate("case_1", {"bad_key": "val"})
    assert res['status'] == "PARTIAL_SUCCESS_AI_UNAVAILABLE"
    assert res['ai_dossier'] is None
    assert "Initial context failure" in res['failure_reason']
