# src/api/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

from src.agent.verifier import RiskInvestigator
from src.agent.policies import PolicyEngine

app = FastAPI(
    title="Sentinel Mesh API",
    description="Cross-Merchant Coordinated Abuse Intelligence"
)

# Initialize our components once when the server starts
investigator = RiskInvestigator()
policy_engine = PolicyEngine()

# Define the request schema
class ClusterRequest(BaseModel):
    device_id: str
    ml_risk_score: float

@app.post("/api/v1/investigate")
async def run_investigation(request: ClusterRequest):
    print(f"\n[API] Received investigation request for device: {request.device_id}")
    try:
        # 1. The LLM Agent gathers data and creates the dossier
        dossier = investigator.investigate_cluster(request.device_id)
        
        # 2. The Policy Engine makes the final deterministic decision
        decision = policy_engine.evaluate(
            ml_risk_score=request.ml_risk_score, 
            ai_dossier=dossier.model_dump()
        )
        
        # 3. Return the complete audit payload
        return {
            "status": "success",
            "device_id": request.device_id,
            "ml_risk_score": request.ml_risk_score,
            "ai_dossier": dossier.model_dump(),
            "final_decision": decision.model_dump()
        }
    except Exception as e:
        print(f"[API] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "Sentinel Mesh Core is online."}

if __name__ == "__main__":
    # Runs the server locally on port 8000
    uvicorn.run(app, host="127.0.0.1", port=8000)