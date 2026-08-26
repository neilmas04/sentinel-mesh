from src.api.database import create_risk_case, get_risk_case
from src.api.schemas import RiskCaseSchema
from typing import Optional

def generate_case_if_needed(transaction_id: str, as_of_timestamp: str, risk_score: float, 
                            risk_level: str, model_version: str, feature_version: str) -> Optional[str]:
    """Generates a case if the risk score crosses the high-risk threshold."""
    if risk_level in ["HIGH", "CRITICAL"]:
        # In a real system, we'd determine the triggered signals dynamically from feature attributions.
        triggered_signals = ["temporal_growth_spike", "network_sync_anomaly"]
        
        case_id = create_risk_case(
            transaction_id=transaction_id,
            as_of_timestamp=as_of_timestamp,
            risk_score=risk_score,
            risk_level=risk_level,
            triggered_signals=triggered_signals,
            model_version=model_version,
            feature_version=feature_version
        )
        return case_id
    return None

def retrieve_case(case_id: str) -> Optional[RiskCaseSchema]:
    """Retrieves a case and formats it using the Pydantic schema."""
    case_data = get_risk_case(case_id)
    if case_data:
        return RiskCaseSchema(**case_data)
    return None
