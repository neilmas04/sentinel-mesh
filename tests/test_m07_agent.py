import pytest
from unittest.mock import patch
from src.agent.investigator import RiskInvestigator, DossierSchema, Claim

def test_grounding_exact_integer_count():
    investigator = RiskInvestigator(None)
    evidence_bundle = [{
        "evidence_id": "E1",
        "observation": {"historical_account_count": 17}
    }]
    dossier = DossierSchema(
        facts=[Claim(claim="The device was linked to 17 accounts.", type="FACT", evidence_ids=["E1"])],
        inferences=[], unknowns=[], risk_assessment=".", recommended_next_step="."
    )
    result = investigator._grounding_validator(dossier, evidence_bundle)
    assert result["facts"][0]["grounding_status"] == "SUPPORTED"

def test_grounding_correct_decimal_amount():
    investigator = RiskInvestigator(None)
    evidence_bundle = [{
        "evidence_id": "E1",
        "observation": {"amount": 844.29}
    }]
    dossier = DossierSchema(
        facts=[Claim(claim="The transaction amount was 844.29.", type="FACT", evidence_ids=["E1"])],
        inferences=[], unknowns=[], risk_assessment=".", recommended_next_step="."
    )
    result = investigator._grounding_validator(dossier, evidence_bundle)
    assert result["facts"][0]["grounding_status"] == "SUPPORTED"

def test_grounding_incorrect_decimal_amount():
    investigator = RiskInvestigator(None)
    evidence_bundle = [{
        "evidence_id": "E1",
        "observation": {"amount": 844.29}
    }]
    dossier = DossierSchema(
        facts=[Claim(claim="The transaction amount was 844.39.", type="FACT", evidence_ids=["E1"])],
        inferences=[], unknowns=[], risk_assessment=".", recommended_next_step="."
    )
    result = investigator._grounding_validator(dossier, evidence_bundle)
    assert result["facts"][0]["grounding_status"] == "UNSUPPORTED"
    assert "Float 844.39 not matched" in result["facts"][0]["grounding_reason"]

def test_grounding_correct_entity_id():
    investigator = RiskInvestigator(None)
    evidence_bundle = [{
        "evidence_id": "E1",
        "observation": {"device_id": "id_abc123"}
    }]
    dossier = DossierSchema(
        facts=[Claim(claim="Device id_abc123 was used.", type="FACT", evidence_ids=["E1"])],
        inferences=[], unknowns=[], risk_assessment=".", recommended_next_step="."
    )
    result = investigator._grounding_validator(dossier, evidence_bundle)
    assert result["facts"][0]["grounding_status"] == "SUPPORTED"

def test_grounding_wrong_entity_id():
    investigator = RiskInvestigator(None)
    evidence_bundle = [{
        "evidence_id": "E1",
        "observation": {"device_id": "id_abc123"}
    }]
    dossier = DossierSchema(
        facts=[Claim(claim="Device id_def456 was used.", type="FACT", evidence_ids=["E1"])],
        inferences=[], unknowns=[], risk_assessment=".", recommended_next_step="."
    )
    result = investigator._grounding_validator(dossier, evidence_bundle)
    assert result["facts"][0]["grounding_status"] == "UNSUPPORTED"

def test_grounding_correct_timestamp():
    investigator = RiskInvestigator(None)
    evidence_bundle = [{
        "evidence_id": "E1",
        "observation": {"timestamp": "2026-08-24 10:00:00"}
    }]
    dossier = DossierSchema(
        facts=[Claim(claim="The event occurred on 2026-08-24.", type="FACT", evidence_ids=["E1"])],
        inferences=[], unknowns=[], risk_assessment=".", recommended_next_step="."
    )
    result = investigator._grounding_validator(dossier, evidence_bundle)
    assert result["facts"][0]["grounding_status"] == "SUPPORTED"

def test_grounding_wrong_timestamp():
    investigator = RiskInvestigator(None)
    evidence_bundle = [{
        "evidence_id": "E1",
        "observation": {"timestamp": "2026-08-24 10:00:00"}
    }]
    dossier = DossierSchema(
        facts=[Claim(claim="The event occurred on 2027-01-01.", type="FACT", evidence_ids=["E1"])],
        inferences=[], unknowns=[], risk_assessment=".", recommended_next_step="."
    )
    result = investigator._grounding_validator(dossier, evidence_bundle)
    assert result["facts"][0]["grounding_status"] == "UNSUPPORTED"

def test_grounding_incorrect_field_reference():
    investigator = RiskInvestigator(None)
    evidence_bundle = [{
        "evidence_id": "E1",
        "observation": {"historical_account_count": 17, "historical_merchant_count": 5}
    }]
    dossier = DossierSchema(
        facts=[Claim(claim="The device was linked to 17 merchants.", type="FACT", evidence_ids=["E1"])],
        inferences=[], unknowns=[], risk_assessment=".", recommended_next_step="."
    )
    result = investigator._grounding_validator(dossier, evidence_bundle)
    assert result["facts"][0]["grounding_status"] == "UNSUPPORTED"

def test_grounding_unverifiable_semantic_inference():
    investigator = RiskInvestigator(None)
    evidence_bundle = [{
        "evidence_id": "E1",
        "observation": {"historical_account_count": 17}
    }]
    dossier = DossierSchema(
        facts=[Claim(claim="The device appears highly suspicious.", type="FACT", evidence_ids=["E1"])],
        inferences=[], unknowns=[], risk_assessment=".", recommended_next_step="."
    )
    result = investigator._grounding_validator(dossier, evidence_bundle)
    assert result["facts"][0]["grounding_status"] == "UNVERIFIABLE"

def test_grounding_transaction_amount_valid():
    investigator = RiskInvestigator(None)
    evidence_bundle = [{"evidence_id": "E1", "observation": {"amount": 223.93}}]
    dossier = DossierSchema(
        facts=[Claim(claim="A transaction for 223.93 occurred.", type="FACT", evidence_ids=["E1"])],
        inferences=[], unknowns=[], risk_assessment=".", recommended_next_step="."
    )
    result = investigator._grounding_validator(dossier, evidence_bundle)
    assert result["facts"][0]["grounding_status"] == "SUPPORTED"

def test_grounding_transaction_amount_invalid():
    investigator = RiskInvestigator(None)
    evidence_bundle = [{"evidence_id": "E1", "observation": {"amount": 223.93}}]
    dossier = DossierSchema(
        facts=[Claim(claim="A transaction for 999.99 occurred.", type="FACT", evidence_ids=["E1"])],
        inferences=[], unknowns=[], risk_assessment=".", recommended_next_step="."
    )
    result = investigator._grounding_validator(dossier, evidence_bundle)
    assert result["facts"][0]["grounding_status"] == "UNSUPPORTED"

def test_grounding_merchant_id_valid():
    investigator = RiskInvestigator(None)
    evidence_bundle = [{"evidence_id": "E1", "observation": {"merchant_id": "id_abc123", "device_id": "id_wrong"}}]
    dossier = DossierSchema(
        facts=[Claim(claim="Merchant id_abc123 was used.", type="FACT", evidence_ids=["E1"])],
        inferences=[], unknowns=[], risk_assessment=".", recommended_next_step="."
    )
    result = investigator._grounding_validator(dossier, evidence_bundle)
    assert result["facts"][0]["grounding_status"] == "SUPPORTED"

def test_grounding_merchant_id_invalid():
    investigator = RiskInvestigator(None)
    evidence_bundle = [{"evidence_id": "E1", "observation": {"merchant_id": "id_abc123", "device_id": "id_wrong"}}]
    dossier = DossierSchema(
        facts=[Claim(claim="Merchant id_wrong was used.", type="FACT", evidence_ids=["E1"])],
        inferences=[], unknowns=[], risk_assessment=".", recommended_next_step="."
    )
    result = investigator._grounding_validator(dossier, evidence_bundle)
    assert result["facts"][0]["grounding_status"] == "UNSUPPORTED"

def test_grounding_timestamp_many_numeric_components():
    investigator = RiskInvestigator(None)
    evidence_bundle = [{"evidence_id": "E1", "observation": {"timestamp": "2026-01-28 11:15:26.449136+00:00"}}]
    dossier = DossierSchema(
        facts=[Claim(claim="Transaction occurred on 2026-01-28 11:15:26.449136+00:00.", type="FACT", evidence_ids=["E1"])],
        inferences=[], unknowns=[], risk_assessment=".", recommended_next_step="."
    )
    result = investigator._grounding_validator(dossier, evidence_bundle)
    assert result["facts"][0]["grounding_status"] == "SUPPORTED"

def test_grounding_composite_transaction_claim():
    investigator = RiskInvestigator(None)
    evidence_bundle = [{"evidence_id": "E1", "observation": {
        "amount": 223.93,
        "timestamp": "2026-01-28 11:15:26",
        "merchant_id": "id_abc123",
        "account_id": "id_def456"
    }}]
    dossier = DossierSchema(
        facts=[Claim(claim="A transaction for 223.93 occurred on 2026-01-28 with merchant id_abc123.", type="FACT", evidence_ids=["E1"])],
        inferences=[], unknowns=[], risk_assessment=".", recommended_next_step="."
    )
    result = investigator._grounding_validator(dossier, evidence_bundle)
    assert result["facts"][0]["grounding_status"] == "SUPPORTED"

def test_grounding_timestamp_natural_language_at():
    investigator = RiskInvestigator(None)
    evidence_bundle = [{"evidence_id": "E1", "observation": {"timestamp": "2026-01-28T06:18:56.762775"}}]
    dossier = DossierSchema(
        facts=[Claim(claim="occurring on 2026-01-28 at 06:18:56.762775", type="FACT", evidence_ids=["E1"])],
        inferences=[], unknowns=[], risk_assessment=".", recommended_next_step="."
    )
    result = investigator._grounding_validator(dossier, evidence_bundle)
    assert result["facts"][0]["grounding_status"] == "SUPPORTED"

def test_grounding_timestamp_t_format():
    investigator = RiskInvestigator(None)
    evidence_bundle = [{"evidence_id": "E1", "observation": {"timestamp": "2026-01-28T06:18:56.762775"}}]
    dossier = DossierSchema(
        facts=[Claim(claim="timestamp 2026-01-28T06:18:56.762775", type="FACT", evidence_ids=["E1"])],
        inferences=[], unknowns=[], risk_assessment=".", recommended_next_step="."
    )
    result = investigator._grounding_validator(dossier, evidence_bundle)
    assert result["facts"][0]["grounding_status"] == "SUPPORTED"

def test_grounding_timestamp_space_format():
    investigator = RiskInvestigator(None)
    evidence_bundle = [{"evidence_id": "E1", "observation": {"timestamp": "2026-01-28T06:18:56.762775"}}]
    dossier = DossierSchema(
        facts=[Claim(claim="timestamp 2026-01-28 06:18:56.762775", type="FACT", evidence_ids=["E1"])],
        inferences=[], unknowns=[], risk_assessment=".", recommended_next_step="."
    )
    result = investigator._grounding_validator(dossier, evidence_bundle)
    assert result["facts"][0]["grounding_status"] == "SUPPORTED"

def test_grounding_mismatched_numeric_fact():
    investigator = RiskInvestigator(None)
    evidence_bundle = [{"evidence_id": "E1", "observation": {"timestamp": "2026-01-28T06:18:56.762775", "amount": 100.0}}]
    dossier = DossierSchema(
        facts=[Claim(claim="occurring on 2026-01-28 at 06:18:56.762775 with amount 56.76", type="FACT", evidence_ids=["E1"])],
        inferences=[], unknowns=[], risk_assessment=".", recommended_next_step="."
    )
    result = investigator._grounding_validator(dossier, evidence_bundle)
    assert result["facts"][0]["grounding_status"] == "UNSUPPORTED"

def test_grounding_inference_claim_unverifiable():
    investigator = RiskInvestigator(None)
    evidence_bundle = [{"evidence_id": "E1", "observation": {"timestamp": "2026-01-28T06:18:56.762775"}}]
    dossier = DossierSchema(
        facts=[],
        inferences=[Claim(claim="occurring on 2026-01-28 at 06:18:56.762775", type="INFERENCE", evidence_ids=["E1"])],
        unknowns=[], risk_assessment=".", recommended_next_step="."
    )
    result = investigator._grounding_validator(dossier, evidence_bundle)
    assert result["inferences"][0]["grounding_status"] == "UNVERIFIABLE"
