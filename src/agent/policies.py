# src/agent/policies.py
from pydantic import BaseModel
from typing import Dict, Any

class FinalDecision(BaseModel):
    action: str           # "APPROVE", "MONITOR", "STEP_UP_AUTH", "BLOCK", "MANUAL_REVIEW"
    reason: str
    overrode_ai: bool     # A great audit metric to track how often the policy engine catches AI mistakes

class PolicyEngine:
    """
    The deterministic gatekeeper.
    Evaluates the ML Risk Score and the AI Dossier together.
    The AI NEVER makes the final decision; it only provides a recommendation.
    """
    def __init__(self, high_risk_threshold: float = 0.85):
        self.high_risk_threshold = high_risk_threshold

    def evaluate(self, ml_risk_score: float, ai_dossier: Dict[str, Any]) -> FinalDecision:
        ai_action = ai_dossier.get("recommended_action", "").lower()
        classification = ai_dossier.get("classification", "").lower()
        
        # Rule 1: ML says safe, but AI says block (AI is likely hallucinating or overreacting)
        if ml_risk_score < 0.5 and ai_action == "block":
            return FinalDecision(
                action="MANUAL_REVIEW",
                reason="Policy Engine override: AI recommended block, but ML risk is low.",
                overrode_ai=True
            )
            
        # Rule 2: Benign Shared Device (Family iPad constraint)
        if classification == "benign_shared_device":
            return FinalDecision(
                action="MONITOR",
                reason="Graph indicates shared device, but AI verified benign household/corporate usage.",
                overrode_ai=False
            )
            
        # Rule 3: Confirmed Coordinated Abuse
        if ml_risk_score >= self.high_risk_threshold and classification == "coordinated_abuse_ring":
            return FinalDecision(
                action="BLOCK",
                reason="ML triggered high risk; AI verified coordinated cross-merchant abuse ring.",
                overrode_ai=False
            )
            
        # Rule 4: Ambiguous Risk
        if ml_risk_score >= 0.6:
            return FinalDecision(
                action="STEP_UP_AUTH",
                reason="Moderate ML risk. Friction added (e.g., 3DS / OTP) to verify identity.",
                overrode_ai=False
            )
            
        # Default fallback
        return FinalDecision(
            action="APPROVE",
            reason="Standard baseline activity.",
            overrode_ai=False
        )

if __name__ == "__main__":
    engine = PolicyEngine()
    
    # Test Case 1: The AI perfectly catches the ring we just found
    dossier_from_gemini = {
        "classification": "coordinated_abuse_ring",
        "confidence_score": 1.0,
        "recommended_action": "block"
    }
    decision = engine.evaluate(ml_risk_score=0.92, ai_dossier=dossier_from_gemini)
    
    print("\n" + "="*50)
    print(" ⚖️ POLICY ENGINE DECISION")
    print("="*50)
    print(f"Action:      {decision.action}")
    print(f"Reason:      {decision.reason}")
    print(f"AI Override: {decision.overrode_ai}")
    print("="*50)