from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
import joblib
import json
import pandas as pd
from datetime import datetime, UTC
import os
from dotenv import load_dotenv

load_dotenv()
print("MAIN LOADED KEY:", os.environ.get("GOOGLE_API_KEY")[:10] if os.environ.get("GOOGLE_API_KEY") else "MISSING")

from src.api.schemas import ScoreRequest, ScoreResponse, RiskCaseSchema, InvestigationResponse, MerchantSpikeResponse
from src.api.database import init_db, update_investigation, get_all_cases, get_dashboard_summary
from src.api.cases import generate_case_if_needed, retrieve_case
from src.features.local_features import LocalFeatureExtractor
from src.features.network_features import NetworkFeatureExtractor
from src.features.temporal_features import TemporalFeatureExtractor
from src.agent.tools import AgentTools
from src.agent.investigator import RiskInvestigator
from src.api.policy import PolicyEngine
from src.features.merchant_spike import MerchantSpikeDetector

# Global state
app_state = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database
    init_db()
    
    # Load Model Artifact
    artifact_dir = "artifacts/models/candidate_d"
    model_path = os.path.join(artifact_dir, "model.pkl")
    meta_path = os.path.join(artifact_dir, "metadata.json")
    
    if not os.path.exists(model_path) or not os.path.exists(meta_path):
        raise RuntimeError("Model artifact not found. Please run M05 model export first.")
        
    app_state["model"] = joblib.load(model_path)
    with open(meta_path, "r") as f:
        app_state["metadata"] = json.load(f)
        
    # Load Simulation Data (Simulating the backend database of transactions)
    print("Loading simulation transaction database...")
    tx_path = "data/generated/m01-world-v1/cohorts/test/transactions.csv"
    if not os.path.exists(tx_path):
        raise RuntimeError(f"Transaction data not found at {tx_path}")
        
    df = pd.read_csv(tx_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    app_state["transactions"] = df.sort_values('timestamp')
    
    print("Sentinel Mesh API started successfully.")
    yield
    app_state.clear()

app = FastAPI(
    title="Sentinel Mesh API",
    description="Cross-Merchant Coordinated Abuse Intelligence",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def classify_risk(score: float, threshold: float) -> str:
    if score >= threshold:
        return "HIGH"
    elif score >= threshold * 0.5:
        return "MEDIUM"
    return "LOW"

@app.post("/api/v1/score", response_model=ScoreResponse)
async def score_transaction(request: ScoreRequest):
    tx_id = request.transaction_id
    df_all = app_state["transactions"]
    
    # Simulating DB lookup
    tx_row = df_all[df_all['transaction_id'] == tx_id]
    if tx_row.empty:
        raise HTTPException(status_code=404, detail="Transaction not found in database.")
        
    current_tx = tx_row.iloc[0]
    current_ts = current_tx['timestamp']
    
    # Strictly enforce causal extraction for historical aggregates: ts < current_transaction
    historical_df = df_all[df_all['timestamp'] < current_ts].copy()
    
    # Append the current transaction itself so its features can be evaluated.
    # This guarantees no other simultaneous transactions are in the history.
    historical_df = pd.concat([historical_df, tx_row])
    historical_df = historical_df.sort_values('timestamp').reset_index(drop=True)
    
    # Extract features
    try:
        ext_df = LocalFeatureExtractor().extract_features(historical_df)
        ext_df = NetworkFeatureExtractor().extract_features(ext_df)
        ext_df = TemporalFeatureExtractor().extract_features(ext_df)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Feature extraction failed: {str(e)}")
        
    # Get the feature row for the current transaction
    feature_row = ext_df[ext_df['transaction_id'] == tx_id]
    if feature_row.empty:
        raise HTTPException(status_code=500, detail="Failed to locate transaction post-extraction.")
        
    # Prepare features for the model
    features = app_state["metadata"]["features"]
    X = feature_row[features]
    
    # Inference
    model = app_state["model"]
    risk_score = float(model.predict_proba(X)[:, 1][0])
    
    threshold = app_state["metadata"]["threshold"]
    risk_level = classify_risk(risk_score, threshold)
    
    # Case Creation (Policy)
    case_id = generate_case_if_needed(
        transaction_id=tx_id,
        as_of_timestamp=current_ts.isoformat(),
        risk_score=risk_score,
        risk_level=risk_level,
        model_version=app_state["metadata"]["model_version"],
        feature_version="v1"
    )
    
    return ScoreResponse(
        transaction_id=tx_id,
        risk_score=risk_score,
        risk_level=risk_level,
        model_version=app_state["metadata"]["model_version"],
        case_id=case_id,
        created_at=datetime.now(UTC),
        merchant_id=current_tx['merchant_id'],
        as_of_timestamp=current_ts,
        is_flagged=(risk_level in ["HIGH", "CRITICAL"])
    )

@app.get("/api/v1/cases", response_model=List[RiskCaseSchema])
async def list_cases(limit: int = 50):
    cases = get_all_cases(limit)
    return cases

@app.get("/api/v1/cases/{case_id}", response_model=RiskCaseSchema)
async def get_case(case_id: str):
    case = retrieve_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    return case

@app.post("/api/v1/cases/{case_id}/investigate", response_model=InvestigationResponse)
async def investigate_case(case_id: str, simulate_ai_failure: bool = False):
    case = retrieve_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
        
    # Initialize Investigator
    tools = AgentTools(app_state["transactions"])
    investigator = RiskInvestigator(tools)
    
    # If simulating AI failure, temporarily remove the API key from environment
    original_api_key = os.environ.get("GOOGLE_API_KEY")
    if simulate_ai_failure:
        os.environ["GOOGLE_API_KEY"] = ""
        
    try:
        # Run investigation
        result = investigator.investigate(case_id, case.model_dump(mode='json'))
    finally:
        # Restore API key
        if simulate_ai_failure and original_api_key is not None:
            os.environ["GOOGLE_API_KEY"] = original_api_key
    
    # M08: Compute Deterministic Policy Decision
    policy_engine = PolicyEngine()
    
    # We need transaction amount to compute economics. We get it from the case evidence.
    transaction_amount = 0.0
    for e in result.get("evidence", []):
        if e.get("source_tool") == "get_transaction_context":
            transaction_amount = float(e.get("observation", {}).get("amount", 0.0))
            
    policy_decision = policy_engine.decide(
        transaction_amount=transaction_amount,
        risk_score=case.risk_score,
        investigation_status=result["status"],
        evidence_bundle=result.get("evidence", []),
        grounding_metrics=result.get("grounding_result")
    )
    
    policy_decision_dict = policy_decision.model_dump()
    
    # Persist results
    update_investigation(
        case_id=case_id,
        status=result["status"],
        tools_used=result["tool_trace"],
        evidence_bundle=result["evidence"],
        ai_dossier=result["ai_dossier"],
        grounding_result=result.get("grounding_result"),
        policy_decision=policy_decision_dict,
        failure_reason=result.get("failure_reason")
    )
    
    return InvestigationResponse(
        case_id=case_id,
        investigation_status=result["status"],
        evidence=result["evidence"],
        ai_dossier=result["ai_dossier"],
        grounding_result=result.get("grounding_result"),
        policy_decision=policy_decision_dict,
        tool_trace=result["tool_trace"],
        recommended_next_step=result["ai_dossier"].get("recommended_next_step") if result.get("ai_dossier") else None,
        failure_reason=result.get("failure_reason")
    )

@app.get("/health")
async def health_check():
    return {"status": "Sentinel Mesh Core is online."}

@app.get("/api/v1/dashboard/summary")
async def dashboard_summary():
    return get_dashboard_summary()

@app.get("/api/v1/evaluation")
async def get_evaluation():
    try:
        from pathlib import Path
        repo_root = Path(__file__).resolve().parent.parent.parent
        
        metrics = {}
        missing = []
        paths = {
            "m02": repo_root / "artifacts/experiments/m02_baseline/metadata.json",
            "m03": repo_root / "artifacts/experiments/m03_system_b/metadata.json",
            "m04": repo_root / "artifacts/experiments/m04_system_c/metadata.json",
            "candidate_d": repo_root / "artifacts/models/candidate_d/metadata.json"
        }
        
        for key, p in paths.items():
            if p.exists():
                with open(p, "r") as f:
                    metrics[key] = json.load(f)
            else:
                missing.append(key)
                
        if not metrics:
            return {"error": "Evaluation artifacts not found. Run evaluations first."}
            
        if missing:
            metrics["missing_artifacts"] = missing
            
        return metrics
    except Exception as e:
        return {"error": f"Evaluation artifacts not found. {str(e)}"}

def get_flagged_transactions() -> set:
    if "flagged_tx_ids" in app_state:
        return app_state["flagged_tx_ids"]
        
    print("Computing Candidate D predictions for all transactions to initialize spike detector...")
    df_all = app_state["transactions"]
    
    # Extract features
    ext_df = LocalFeatureExtractor().extract_features(df_all)
    ext_df = NetworkFeatureExtractor().extract_features(ext_df)
    ext_df = TemporalFeatureExtractor().extract_features(ext_df)
    
    features = app_state["metadata"]["features"]
    X = ext_df[features]
    
    model = app_state["model"]
    risk_scores = model.predict_proba(X)[:, 1]
    
    threshold = app_state["metadata"]["threshold"]
    flagged_mask = risk_scores >= threshold
    
    flagged_tx_ids = set(ext_df[flagged_mask]['transaction_id'].tolist())
    app_state["flagged_tx_ids"] = flagged_tx_ids
    return flagged_tx_ids

@app.get("/api/v1/merchant-spikes", response_model=List[MerchantSpikeResponse])
async def get_merchant_spikes(
    merchant_id: Optional[str] = None, 
    current_time: Optional[str] = None,
    live_tx_id: Optional[str] = None,
    live_is_flagged: Optional[bool] = None
):
    df_all = app_state["transactions"]
    
    if current_time:
        try:
            eval_time = pd.to_datetime(current_time)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid current_time format: {str(e)}")
    else:
        eval_time = df_all['timestamp'].max()
        
    flagged_tx_ids = get_flagged_transactions()
    detector = MerchantSpikeDetector(bucket_size='1h', lookback_window=6)
    
    live_observation = None
    if live_tx_id and live_is_flagged is not None:
        live_observation = {
            "live_tx_id": live_tx_id,
            "is_flagged": live_is_flagged
        }
    
    results = []
    merchants_to_eval = [merchant_id] if merchant_id else df_all['merchant_id'].unique()
    
    for m_id in merchants_to_eval:
        res = detector.compute_spike(m_id, eval_time, df_all, flagged_tx_ids, live_observation)
        results.append(MerchantSpikeResponse(**res))
        
    return results

class SimulationStepRequest(BaseModel):
    scenario: str

@app.post("/api/v1/simulation/step")
async def simulation_step(req: SimulationStepRequest):
    df_all = app_state["transactions"]
    scenario = req.scenario.upper()
    
    # Simple simulation logic based on ground truth labels in a real scenario.
    # Here we pick transactions based on some simplistic logic representing the scenario.
    if scenario == "NORMAL":
        tx = df_all.sample(n=1).iloc[0]
    elif scenario == "COORDINATED_ACTIVITY":
        # Find a transaction that belongs to a known cluster (e.g. from generated data)
        # We know we have a test cohort, let's just pick a high-risk one
        labels = pd.read_csv("data/generated/m01-world-v1/ground_truth/event_labels.csv")
        abuse_txs = labels[labels['is_abuse'] == 1]['transaction_id'].tolist()
        tx = df_all[df_all['transaction_id'].isin(abuse_txs)].sample(n=1).iloc[0]
    elif scenario == "AI_FAILURE":
        # We can just pick any transaction but temporarily unset the API key to force a failure on investigate
        # Not easily done safely in global state without a lock, but for demo we can mock it by passing a flag.
        labels = pd.read_csv("data/generated/m01-world-v1/ground_truth/event_labels.csv")
        abuse_txs = labels[labels['is_abuse'] == 1]['transaction_id'].tolist()
        tx = df_all[df_all['transaction_id'].isin(abuse_txs)].sample(n=1).iloc[0]
    else:
        tx = df_all.sample(n=1).iloc[0]
        
    # We trigger the score endpoint internally
    score_req = ScoreRequest(transaction_id=tx['transaction_id'])
    return await score_transaction(score_req)