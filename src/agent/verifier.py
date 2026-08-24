# src/agent/verifier.py
import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

from src.agent.schemas import EvidenceDossier
from src.agent.tools import InvestigationTools

# Load environment variables (API Key)
load_dotenv()

class RiskInvestigator:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing from the .env file.")
        
        # Initialize the modern client
        self.client = genai.Client(api_key=api_key)
        self.tools = InvestigationTools()

    def investigate_cluster(self, device_id: str) -> EvidenceDossier:
        print(f"\n[Agent] Initiating bounded investigation for Device: {device_id}")
        
        # 1. GATHER EVIDENCE
        print("[Agent] Extracting network graph metrics...")
        cluster_summary = self.tools.get_device_cluster_summary(device_id)
        
        print("[Agent] Extracting financial exposure...")
        exposure = self.tools.get_merchant_exposure(device_id)
        
        raw_evidence = {
            "cluster_metrics": cluster_summary,
            "merchant_exposure": exposure
        }
        
        # 2. PROMPT ENGINEERING
        prompt = f"""
        You are an expert Payment Risk Investigator at Razorpay.
        Analyze the following deterministic evidence extracted from the Sentinel Mesh graph.
        
        EVIDENCE:
        {json.dumps(raw_evidence, indent=2)}
        
        RULES:
        1. You must output strictly valid JSON matching the provided schema.
        2. Do NOT hallucinate. Only make claims supported by the numbers in the EVIDENCE.
        3. If the device is shared among many accounts AND spans many merchants, classify as 'coordinated_abuse_ring' and recommend 'step_up_auth' or 'block'.
        4. If the device has multiple accounts but only targets 1 or 2 merchants (e.g., a family using one tablet), classify as 'benign_shared_device' and recommend 'monitor'.
        
        Provide your final structured risk dossier.
        """
        
        print("[Agent] Requesting grounded verification from Gemini...")
        
        # 3. STRUCTURED AI GENERATION (Modern SDK Syntax)
        response = self.client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=EvidenceDossier,
                temperature=0.1
            )
        )
        
        dossier_data = json.loads(response.text)
        dossier = EvidenceDossier(**dossier_data)
        
        return dossier

if __name__ == "__main__":
    test_device = "dev_user_83dec039" 
    
    try:
        investigator = RiskInvestigator()
        dossier = investigator.investigate_cluster(test_device)
        
        print("\n" + "="*50)
        print(" 🛡️ SENTINEL MESH AI DOSSIER (Modern SDK)")
        print("="*50)
        print(json.dumps(dossier.model_dump(), indent=2))
        print("="*50)
        
    except Exception as e:
        print(f"Integration Error: {e}")