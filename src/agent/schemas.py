# src/agent/schemas.py
from pydantic import BaseModel
from typing import List

class EvidenceDossier(BaseModel):
    classification: str             # e.g., "coordinated_abuse_ring", "benign_shared_device"
    confidence_score: float         # 0.0 to 1.0
    supporting_evidence: List[str]  # Grounded claims only
    missing_evidence: List[str]     # What else would help confirm?
    recommended_action: str         # "monitor", "enhanced_review", "step_up_auth"