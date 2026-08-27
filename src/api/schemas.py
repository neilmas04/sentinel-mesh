from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, UTC
from src.api.policy import PolicyDecisionSchema

class ScoreRequest(BaseModel):
    transaction_id: str = Field(..., description="The unique identifier of the transaction to score.")

class ScoreResponse(BaseModel):
    transaction_id: str
    risk_score: float
    risk_level: str
    model_version: str
    case_id: Optional[str] = None
    created_at: datetime
    merchant_id: Optional[str] = None
    as_of_timestamp: Optional[datetime] = None
    is_flagged: Optional[bool] = None

class HealthResponse(BaseModel):
    status: str
    version: str

class RiskCaseSchema(BaseModel):
    case_id: str
    transaction_id: str
    as_of_timestamp: datetime
    risk_score: float
    risk_level: str
    triggered_signals: List[str]
    model_version: str
    feature_version: str
    status: str
    created_at: datetime
    investigation_status: str = 'UNINVESTIGATED'
    tools_used: Optional[List[dict]] = None
    evidence_bundle: Optional[List[dict]] = None
    ai_dossier: Optional[dict] = None
    grounding_result: Optional[dict] = None
    policy_decision: Optional[dict] = None
    failure_reason: Optional[str] = None

class InvestigationResponse(BaseModel):
    case_id: str
    investigation_status: str
    evidence: List[dict]
    ai_dossier: Optional[dict]
    grounding_result: Optional[dict]
    policy_decision: Optional[dict]
    tool_trace: List[dict]
    recommended_next_step: Optional[str]
    failure_reason: Optional[str]

class TimelineBucket(BaseModel):
    bucket_idx: int
    start_time: str
    end_time: str
    total_transactions: int
    flagged_transactions: int
    flagged_rate: float
    is_live: bool
    is_baseline: bool

class MerchantSpikeResponse(BaseModel):
    merchant_id: str
    timestamp: str
    total_transactions: int
    flagged_transactions: int
    flagged_rate: float
    baseline_mean: Optional[float]
    baseline_std: Optional[float]
    rate_multiplier: Optional[float]
    spike_score: Optional[float]
    severity: str
    baseline_insufficient: bool
    timeline: Optional[List[TimelineBucket]] = None
