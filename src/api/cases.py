from src.api.database import create_risk_case, get_risk_case, find_open_case_for_entity, add_case_signal
from src.api.schemas import RiskCaseSchema
from typing import Optional

def process_risk_signals(transaction_id: str, as_of_timestamp: str, signals: list,
                         account_id: str = None, device_id: str = None, merchant_id: str = None,
                         model_version: str = "v1", feature_version: str = "v1", is_ai_failure: bool = False) -> Optional[str]:
    """Processes a list of signals and aggregates them into a case if necessary."""
    if not signals:
        return None
        
    # Determine entity for grouping (prefer merchant_id if it's a merchant spike, else account/device)
    # If any signal is MERCHANT_SPIKE, group by merchant.
    has_merchant_spike = any(s['signal_type'] == 'MERCHANT_SPIKE' for s in signals)
    
    if has_merchant_spike and merchant_id:
        entity_type = "MERCHANT"
        entity_id = merchant_id
    elif account_id:
        entity_type = "ACCOUNT"
        entity_id = account_id
    elif device_id:
        entity_type = "DEVICE"
        entity_id = device_id
    elif merchant_id:
        entity_type = "MERCHANT"
        entity_id = merchant_id
    else:
        entity_type = "TRANSACTION"
        entity_id = transaction_id
        
    # Check for existing open case
    existing_case_id = find_open_case_for_entity(entity_type, entity_id, as_of_timestamp)
    
    if existing_case_id:
        case_id = existing_case_id
    else:
        # Create new case
        max_risk_score = max([s.get('risk_score', 0.0) for s in signals if s.get('risk_score') is not None] or [0.0])
        
        risk_level = "HIGH"
        for s in signals:
            if s.get('details', {}).get('risk_level') == "CRITICAL" or s.get('details', {}).get('severity') == "CRITICAL":
                risk_level = "CRITICAL"
                break
                
        triggered_signals = [s['signal_type'] for s in signals]
        
        case_id = create_risk_case(
            entity_type=entity_type,
            entity_id=entity_id,
            as_of_timestamp=as_of_timestamp,
            risk_score=max_risk_score,
            risk_level=risk_level,
            triggered_signals=triggered_signals,
            model_version=model_version,
            feature_version=feature_version,
            transaction_id=transaction_id,
            is_ai_failure=is_ai_failure
        )
        
    # Add all signals to the case
    for s in signals:
        add_case_signal(
            case_id=case_id,
            transaction_id=s.get('transaction_id', transaction_id),
            signal_type=s['signal_type'],
            timestamp=s.get('timestamp', as_of_timestamp),
            risk_score=s.get('risk_score'),
            details=s.get('details')
        )
        
    return case_id

def retrieve_case(case_id: str) -> Optional[RiskCaseSchema]:
    """Retrieves a case and formats it using the Pydantic schema."""
    case_data = get_risk_case(case_id)
    if case_data:
        return RiskCaseSchema(**case_data)
    return None
