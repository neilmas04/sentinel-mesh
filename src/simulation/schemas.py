# src/simulation/schemas.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class Merchant(BaseModel):
    merchant_id: str
    category: str
    base_velocity_mean: float  # Expected txns per hour
    avg_txn_amount: float
    std_txn_amount: float

class Account(BaseModel):
    account_id: str
    creation_time: datetime
    is_compromised: bool = False # Internal ground truth ONLY, never exposed to features

class Device(BaseModel):
    device_id: str
    device_type: str
    is_compromised: bool = False

class Transaction(BaseModel):
    transaction_id: str
    timestamp: datetime
    merchant_id: str
    account_id: str
    device_id: str
    network_id: str
    amount: float
    
    # --- GROUND TRUTH (STRIPPED BEFORE ML) ---
    scenario_name: str       # e.g., "distributed_card_testing"
    is_fraud: int            # 1 or 0
    campaign_id: Optional[str] = None # To calculate TTD for specific clusters