import sqlite3
import json
from contextlib import contextmanager
import uuid
from datetime import datetime, UTC

DB_PATH = "sentinel.db"

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS risk_cases")
        cursor.execute("""
            CREATE TABLE risk_cases (
                case_id TEXT PRIMARY KEY,
                transaction_id TEXT NOT NULL,
                as_of_timestamp TEXT NOT NULL,
                risk_score REAL NOT NULL,
                risk_level TEXT NOT NULL,
                triggered_signals TEXT NOT NULL,
                model_version TEXT NOT NULL,
                feature_version TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                investigation_status TEXT DEFAULT 'UNINVESTIGATED',
                tools_used TEXT,
                evidence_bundle TEXT,
                ai_dossier TEXT,
                grounding_result TEXT,
                policy_decision TEXT,
                failure_reason TEXT
            )
        """)
        conn.commit()

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def create_risk_case(transaction_id: str, as_of_timestamp: str, risk_score: float, 
                     risk_level: str, triggered_signals: list, model_version: str, 
                     feature_version: str) -> str:
    case_id = f"CASE-{uuid.uuid4().hex[:8].upper()}"
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO risk_cases (
                case_id, transaction_id, as_of_timestamp, risk_score, risk_level, 
                triggered_signals, model_version, feature_version, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            case_id, transaction_id, as_of_timestamp, risk_score, risk_level,
            json.dumps(triggered_signals), model_version, feature_version, "OPEN", datetime.now(UTC).isoformat()
        ))
        conn.commit()
    return case_id

def get_risk_case(case_id: str) -> dict:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM risk_cases WHERE case_id = ?", (case_id,))
        row = cursor.fetchone()
        if not row:
            return None
        
        result = dict(row)
        result['triggered_signals'] = json.loads(result['triggered_signals'])
        if result.get('tools_used'):
            result['tools_used'] = json.loads(result['tools_used'])
        if result.get('evidence_bundle'):
            result['evidence_bundle'] = json.loads(result['evidence_bundle'])
        if result.get('ai_dossier'):
            result['ai_dossier'] = json.loads(result['ai_dossier'])
        if result.get('grounding_result'):
            result['grounding_result'] = json.loads(result['grounding_result'])
        if result.get('policy_decision'):
            result['policy_decision'] = json.loads(result['policy_decision'])
        return result

def update_investigation(case_id: str, status: str, tools_used: list = None, 
                         evidence_bundle: list = None, ai_dossier: dict = None, 
                         grounding_result: dict = None, policy_decision: dict = None,
                         failure_reason: str = None):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE risk_cases SET 
                investigation_status = ?,
                tools_used = ?,
                evidence_bundle = ?,
                ai_dossier = ?,
                grounding_result = ?,
                policy_decision = ?,
                failure_reason = ?
            WHERE case_id = ?
        """, (
            status,
            json.dumps(tools_used) if tools_used else None,
            json.dumps(evidence_bundle) if evidence_bundle else None,
            json.dumps(ai_dossier) if ai_dossier else None,
            json.dumps(grounding_result) if grounding_result else None,
            json.dumps(policy_decision) if policy_decision else None,
            failure_reason,
            case_id
        ))
        conn.commit()

def get_all_cases(limit: int = 50) -> list[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM risk_cases ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        
        cases = []
        for row in rows:
            result = dict(row)
            result['triggered_signals'] = json.loads(result['triggered_signals'])
            if result.get('tools_used'):
                result['tools_used'] = json.loads(result['tools_used'])
            if result.get('evidence_bundle'):
                result['evidence_bundle'] = json.loads(result['evidence_bundle'])
            if result.get('ai_dossier'):
                result['ai_dossier'] = json.loads(result['ai_dossier'])
            if result.get('grounding_result'):
                result['grounding_result'] = json.loads(result['grounding_result'])
            if result.get('policy_decision'):
                result['policy_decision'] = json.loads(result['policy_decision'])
            cases.append(result)
        return cases

def get_dashboard_summary() -> dict:
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as total FROM risk_cases")
        total_cases = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as high_risk FROM risk_cases WHERE risk_level = 'HIGH'")
        high_risk_cases = cursor.fetchone()['high_risk']
        
        cursor.execute("SELECT COUNT(*) as investigated FROM risk_cases WHERE investigation_status != 'UNINVESTIGATED'")
        investigated_cases = cursor.fetchone()['investigated']
        
        # Estimate total exposure (this is just sum of amounts if we had it, but we can only approximate from policy decisions where available)
        cursor.execute("SELECT policy_decision FROM risk_cases WHERE policy_decision IS NOT NULL")
        decisions = cursor.fetchall()
        total_exposure = 0.0
        for d in decisions:
            try:
                pol = json.loads(d['policy_decision'])
                if 'expected_fraud_loss' in pol:
                    total_exposure += pol['expected_fraud_loss']
            except:
                pass
                
        return {
            "total_active_cases": total_cases,
            "high_risk_cases": high_risk_cases,
            "investigated_cases": investigated_cases,
            "estimated_exposure": total_exposure
        }
