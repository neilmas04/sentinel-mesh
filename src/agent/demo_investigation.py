import pandas as pd
import json
import joblib
import os
from datetime import datetime, UTC
from dotenv import load_dotenv
load_dotenv()

from src.api.database import init_db
from src.api.cases import generate_case_if_needed, retrieve_case
from src.features.local_features import LocalFeatureExtractor
from src.features.network_features import NetworkFeatureExtractor
from src.features.temporal_features import TemporalFeatureExtractor
from src.agent.tools import AgentTools
from src.agent.investigator import RiskInvestigator
import asyncio

async def run_demo():
    print("=== M06 Deterministic Demo ===")
    
    # 1. Initialize System
    init_db()
    
    # Load Model
    model = joblib.load("artifacts/models/candidate_d/model.pkl")
    with open("artifacts/models/candidate_d/metadata.json", "r") as f:
        metadata = json.load(f)
        
    # Load Data
    tx_df = pd.read_csv("data/generated/m01-world-v1/cohorts/test/transactions.csv")
    tx_df['timestamp'] = pd.to_datetime(tx_df['timestamp'])
    tx_df = tx_df.sort_values('timestamp')
    
    # Pick a known high-risk transaction from ground truth
    labels_df = pd.read_csv("data/generated/m01-world-v1/ground_truth/event_labels.csv")
    full = tx_df.merge(labels_df[['transaction_id', 'is_abuse']], on='transaction_id')
    abuse_txs = full[full['is_abuse'] == 1]['transaction_id'].tolist()
    tx_id = abuse_txs[-1] # Pick the last abuse transaction
    
    # 2. Extract Features to get Risk Score
    tx_row = tx_df[tx_df['transaction_id'] == tx_id]
    current_tx = tx_row.iloc[0]
    current_ts = current_tx['timestamp']
    
    historical_df = tx_df[tx_df['timestamp'] < current_ts].copy()
    historical_df = pd.concat([historical_df, tx_row])
    historical_df = historical_df.sort_values('timestamp').reset_index(drop=True)
    
    ext_df = LocalFeatureExtractor().extract_features(historical_df)
    ext_df = NetworkFeatureExtractor().extract_features(ext_df)
    ext_df = TemporalFeatureExtractor().extract_features(ext_df)
    
    feature_row = ext_df[ext_df['transaction_id'] == tx_id]
    X = feature_row[metadata["features"]]
    risk_score = float(model.predict_proba(X)[:, 1][0])
    
    # 3. Create Case
    case_id = generate_case_if_needed(
        transaction_id=tx_id,
        as_of_timestamp=current_ts.isoformat(),
        risk_score=risk_score,
        risk_level="HIGH",
        model_version=metadata["model_version"],
        feature_version="v1"
    )
    
    print(f"\n[Case Generated] ID: {case_id} | Risk Score: {risk_score:.4f} | TxID: {tx_id}")
    
    # 4. Investigate Case
    case = retrieve_case(case_id)
    tools = AgentTools(tx_df)
    investigator = RiskInvestigator(tools)
    
    print("\n[Agent] Starting Investigation Loop...")
    result = investigator.investigate(case_id, case.model_dump())
    
    print("\n[Tool Trace]")
    for step in result['tool_trace']:
        print(f"  -> {step}")
        
    print("\n[Evidence Bundle]")
    for e in result['evidence']:
        print(f"  {e['evidence_id']} [{e['source_tool']}]: {e['observation']}")
        
    print("\n[AI Dossier]")
    if result.get('ai_dossier'):
        dossier = result['ai_dossier']
        print(json.dumps(dossier, indent=2))
    else:
        print(f"  FAILED: {result.get('failure_reason')}")
        
    print("\n[Economic Analysis & Deterministic Policy]")
    from src.api.policy import PolicyEngine
    policy_engine = PolicyEngine()
    
    tx_amount = float(result["evidence"][0]["observation"]["amount"]) if result["evidence"] else 0.0
    
    policy_decision = policy_engine.decide(
        transaction_amount=tx_amount,
        risk_score=risk_score,
        investigation_status=result["status"],
        evidence_bundle=result["evidence"],
        grounding_metrics=result.get("grounding_result")
    )
    
    print(json.dumps(policy_decision.model_dump(), indent=2))
    
    print(f"\n>> FINAL BOUNDED ACTION: {policy_decision.action}")

if __name__ == "__main__":
    asyncio.run(run_demo())
