import pytest
from src.api.policy import PolicyEngine, EconomicModel

def test_low_risk_monitor():
    engine = PolicyEngine()
    decision = engine.decide(
        transaction_amount=50.0,
        risk_score=0.1,
        investigation_status="COMPLETED",
        evidence_bundle=[{}, {}], # 2 items = sufficient
        grounding_metrics={"grounding_rate": 1.0, "unsupported_claims": 0}
    )
    
    assert decision.action == "MONITOR"
    assert "LOW_RISK_SCORE" in decision.reason_codes

def test_high_risk_insufficient_evidence():
    engine = PolicyEngine()
    decision = engine.decide(
        transaction_amount=50.0,
        risk_score=0.85,
        investigation_status="COMPLETED",
        evidence_bundle=[{}], # 1 item = insufficient
        grounding_metrics={"grounding_rate": 1.0, "unsupported_claims": 0}
    )
    
    assert decision.action == "MANUAL_REVIEW"
    assert decision.evidence_sufficiency == "INSUFFICIENT"
    assert "INSUFFICIENT_EVIDENCE" in decision.reason_codes
    assert "HIGH_RISK_SCORE" in decision.reason_codes

def test_high_expected_loss_forces_hold():
    engine = PolicyEngine()
    decision = engine.decide(
        transaction_amount=10000.0,
        risk_score=0.95,
        investigation_status="COMPLETED",
        evidence_bundle=[{}, {}],
        grounding_metrics={"grounding_rate": 1.0, "unsupported_claims": 0}
    )
    
    # expected loss = 10000 * 0.95 = 9500 > 5000 -> HOLD
    assert decision.action == "HOLD"
    assert "EXTREME_RISK_SCORE" in decision.reason_codes
    assert "HIGH_EXPECTED_LOSS" in decision.reason_codes
    assert decision.expected_fraud_loss == 9500.0
    
def test_ai_unavailable_deterministic_fallback():
    engine = PolicyEngine()
    decision = engine.decide(
        transaction_amount=500.0,
        risk_score=0.75,
        investigation_status="PARTIAL_SUCCESS_AI_UNAVAILABLE",
        evidence_bundle=[{}, {}],
        grounding_metrics=None
    )
    
    # High risk score + sufficient evidence -> would normally be ENHANCED_VERIFICATION
    # However AI unavailable means grounding warning.
    # The rule is: risk > 0.70 with sufficient evidence + SAFE grounding = ENHANCED_VERIFICATION.
    # Since grounding is not SAFE (it's AI_UNAVAILABLE), the logic in our engine right now doesn't explicitly 
    # downgrade ENHANCED_VERIFICATION to MANUAL_REVIEW unless evidence is insufficient.
    # Let's see: if risk_score >= 0.70: if evidence == INSUFFICIENT action = MANUAL_REVIEW else action = ENHANCED_VERIFICATION.
    # We should ensure AI unavailability doesn't block operations but flags reasons.
    assert decision.action == "ENHANCED_VERIFICATION"
    assert "AI_UNAVAILABLE" in decision.reason_codes
    assert decision.grounding_status == "AI_UNAVAILABLE"

def test_false_positive_cost_tradeoff():
    # Test review cost exceeds loss
    engine = PolicyEngine()
    decision = engine.decide(
        transaction_amount=2.0,  # Expected loss will be 2.0 * 0.5 = 1.0
        risk_score=0.5,
        investigation_status="COMPLETED",
        evidence_bundle=[{}, {}],
        grounding_metrics={"grounding_rate": 1.0, "unsupported_claims": 0}
    )
    
    # Normally 0.5 -> MANUAL_REVIEW, but expected fraud loss is 1.0. 
    # Manual review cost is 5.0. It should downgrade to MONITOR.
    assert decision.action == "MONITOR"
    assert "REVIEW_COST_EXCEEDS_LOSS" in decision.reason_codes
