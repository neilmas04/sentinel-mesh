from pydantic import BaseModel
from typing import List, Optional

class PolicyDecisionSchema(BaseModel):
    policy_version: str
    action: str
    risk_score: float
    expected_fraud_loss: float
    intervention_cost: float
    expected_total_cost: float
    evidence_sufficiency: str
    grounding_status: str
    reason_codes: List[str]

class EconomicModel:
    def __init__(self, loss_severity_factor: float = 1.0, fp_cost_rate: float = 0.05, manual_review_cost: float = 5.0):
        self.loss_severity_factor = loss_severity_factor
        self.fp_cost_rate = fp_cost_rate
        self.manual_review_cost = manual_review_cost
        
        self.intervention_costs = {
            "MONITOR": 0.0,
            "MANUAL_REVIEW": self.manual_review_cost,
            "ENHANCED_VERIFICATION": 2.5,
            "HOLD": 0.0  # Immediate action cost is low, but FP cost is high
        }

    def evaluate(self, transaction_amount: float, risk_score: float, action: str) -> dict:
        expected_fraud_loss = transaction_amount * risk_score * self.loss_severity_factor
        
        intervention_cost = self.intervention_costs.get(action, 0.0)
        
        # If we HOLD or ENHANCE, we risk a False Positive which costs transaction_amount * fp_cost_rate
        # For MONITOR or MANUAL_REVIEW, there's no immediate UX friction cost
        if action in ["HOLD", "ENHANCED_VERIFICATION"]:
            expected_fp_cost = transaction_amount * self.fp_cost_rate * (1.0 - risk_score)
        else:
            expected_fp_cost = 0.0
            
        expected_total_cost = expected_fraud_loss + intervention_cost + expected_fp_cost
        
        return {
            "expected_fraud_loss": round(expected_fraud_loss, 2),
            "intervention_cost": round(intervention_cost, 2),
            "expected_false_positive_cost": round(expected_fp_cost, 2),
            "expected_total_cost": round(expected_total_cost, 2)
        }


class PolicyEngine:
    VERSION = "v1.0-deterministic"
    
    def __init__(self, economic_model: EconomicModel = None):
        self.economics = economic_model or EconomicModel()
        self.min_evidence_count = 2

    def decide(self, transaction_amount: float, risk_score: float, investigation_status: str, 
               evidence_bundle: list, grounding_metrics: dict = None) -> PolicyDecisionSchema:
        
        reason_codes = []
        action = "MONITOR"
        evidence_sufficiency = "SUFFICIENT"
        grounding_status = "SAFE"
        
        # 1. Evaluate Evidence Sufficiency
        if not evidence_bundle or len(evidence_bundle) < self.min_evidence_count:
            evidence_sufficiency = "INSUFFICIENT"
            reason_codes.append("INSUFFICIENT_EVIDENCE")
            
        # 2. Evaluate Grounding & AI Availability
        if investigation_status == "PARTIAL_SUCCESS_AI_UNAVAILABLE":
            grounding_status = "AI_UNAVAILABLE"
            reason_codes.append("AI_UNAVAILABLE")
        elif grounding_metrics:
            if grounding_metrics.get("unsupported_claims", 0) > 0 or grounding_metrics.get("grounding_rate", 1.0) < 0.8:
                grounding_status = "WARNING"
                reason_codes.append("GROUNDING_WARNING")
                
        # 3. Base Deterministic Rules (Business Logic)
        if risk_score >= 0.90:
            reason_codes.append("EXTREME_RISK_SCORE")
            if evidence_sufficiency == "SUFFICIENT" and grounding_status == "SAFE":
                action = "HOLD"
            else:
                action = "MANUAL_REVIEW"
                
        elif risk_score >= 0.70:
            reason_codes.append("HIGH_RISK_SCORE")
            if evidence_sufficiency == "INSUFFICIENT":
                action = "MANUAL_REVIEW"
            else:
                action = "ENHANCED_VERIFICATION"
                
        elif risk_score >= 0.50:
            reason_codes.append("MEDIUM_RISK_SCORE")
            action = "MANUAL_REVIEW"
        else:
            reason_codes.append("LOW_RISK_SCORE")
            action = "MONITOR"
            
        # 4. Economic Overrides
        # We simulate the cost of the proposed action.
        econ = self.economics.evaluate(transaction_amount, risk_score, action)
        
        # If the expected fraud loss is massive, force a HOLD regardless of evidence (unless AI was explicitly contradicting it safely, but policy > AI).
        if econ["expected_fraud_loss"] > 5000:
            reason_codes.append("HIGH_EXPECTED_LOSS")
            action = "HOLD"
            # Re-evaluate econ for HOLD
            econ = self.economics.evaluate(transaction_amount, risk_score, action)
            
        # If action is MANUAL_REVIEW but expected fraud loss is lower than the review cost, downgrade to MONITOR
        if action == "MANUAL_REVIEW" and econ["expected_fraud_loss"] < self.economics.manual_review_cost:
            reason_codes.append("REVIEW_COST_EXCEEDS_LOSS")
            action = "MONITOR"
            econ = self.economics.evaluate(transaction_amount, risk_score, action)

        return PolicyDecisionSchema(
            policy_version=self.VERSION,
            action=action,
            risk_score=risk_score,
            expected_fraud_loss=econ["expected_fraud_loss"],
            intervention_cost=econ["intervention_cost"],
            expected_total_cost=econ["expected_total_cost"],
            evidence_sufficiency=evidence_sufficiency,
            grounding_status=grounding_status,
            reason_codes=reason_codes
        )
