import sqlite3
import json
from contextlib import contextmanager
import uuid
from datetime import datetime, UTC

DB_PATH = "sentinel.db"

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS risk_cases (
                case_id TEXT PRIMARY KEY,
                entity_type TEXT DEFAULT 'TRANSACTION',
                entity_id TEXT NOT NULL,
                transaction_id TEXT, -- Legacy field, kept for backward compatibility
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
                failure_reason TEXT,
                disposition TEXT,
                analyst_notes TEXT,
                disposition_timestamp TEXT,
                analyst_id TEXT
            )
        """)
        
        # Add new columns to existing table if they don't exist (SQLite doesn't support IF NOT EXISTS for ADD COLUMN, so we catch the error)
        try:
            cursor.execute("ALTER TABLE risk_cases ADD COLUMN entity_type TEXT DEFAULT 'TRANSACTION'")
            cursor.execute("ALTER TABLE risk_cases ADD COLUMN entity_id TEXT")
            cursor.execute("ALTER TABLE risk_cases ADD COLUMN disposition TEXT")
            cursor.execute("ALTER TABLE risk_cases ADD COLUMN analyst_notes TEXT")
            cursor.execute("ALTER TABLE risk_cases ADD COLUMN disposition_timestamp TEXT")
            cursor.execute("ALTER TABLE risk_cases ADD COLUMN analyst_id TEXT")
            # For existing rows, set entity_id to transaction_id
            cursor.execute("UPDATE risk_cases SET entity_id = transaction_id WHERE entity_id IS NULL")
        except sqlite3.OperationalError:
            pass # Columns already exist
            
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS case_signals (
                signal_id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                transaction_id TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                risk_score REAL,
                details TEXT,
                FOREIGN KEY(case_id) REFERENCES risk_cases(case_id),
                UNIQUE(case_id, transaction_id, signal_type)
            )
        """)
        
        # We can't easily ALTER TABLE to add UNIQUE in SQLite, so we rely on INSERT OR IGNORE
        # If the table was already created without UNIQUE, we might have duplicates, but for new inserts we'll handle it in code.
        # Actually, let's try to create a unique index to enforce it retroactively if possible.
        try:
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_case_signal ON case_signals(case_id, transaction_id, signal_type)")
        except sqlite3.OperationalError:
            pass
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS case_audit_log (
                log_id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                actor TEXT NOT NULL,
                event_type TEXT NOT NULL,
                previous_state TEXT,
                new_state TEXT,
                reason TEXT,
                FOREIGN KEY(case_id) REFERENCES risk_cases(case_id)
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

def create_risk_case(entity_type: str, entity_id: str, as_of_timestamp: str, risk_score: float, 
                     risk_level: str, triggered_signals: list, model_version: str, 
                     feature_version: str, transaction_id: str = None) -> str:
    case_id = f"CASE-{uuid.uuid4().hex[:8].upper()}"
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO risk_cases (
                case_id, entity_type, entity_id, transaction_id, as_of_timestamp, risk_score, risk_level, 
                triggered_signals, model_version, feature_version, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            case_id, entity_type, entity_id, transaction_id, as_of_timestamp, risk_score, risk_level,
            json.dumps(triggered_signals), model_version, feature_version, "OPEN", datetime.now(UTC).isoformat()
        ))
        
        # Add audit log for creation
        log_id = f"LOG-{uuid.uuid4().hex[:8].upper()}"
        cursor.execute("""
            INSERT INTO case_audit_log (
                log_id, case_id, timestamp, actor, event_type, new_state, reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            log_id, case_id, datetime.now(UTC).isoformat(), "SYSTEM", "CASE_CREATED", "OPEN", "Initial case creation"
        ))
        
        conn.commit()
    return case_id

def add_case_signal(case_id: str, transaction_id: str, signal_type: str, timestamp: str, risk_score: float = None, details: dict = None) -> str:
    signal_id = f"SIG-{uuid.uuid4().hex[:8].upper()}"
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO case_signals (
                    signal_id, case_id, transaction_id, signal_type, timestamp, risk_score, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                signal_id, case_id, transaction_id, signal_type, timestamp, risk_score, 
                json.dumps(details) if details else None
            ))
            
            # Add audit log for signal enrichment
            log_id = f"LOG-{uuid.uuid4().hex[:8].upper()}"
            cursor.execute("""
                INSERT INTO case_audit_log (
                    log_id, case_id, timestamp, actor, event_type, new_state, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                log_id, case_id, datetime.now(UTC).isoformat(), "SYSTEM", "SIGNAL_ADDED", "OPEN", 
                f"Added {signal_type} signal for transaction {transaction_id}"
            ))
            
            conn.commit()
            return signal_id
        except sqlite3.IntegrityError:
            # Duplicate signal (case_id, transaction_id, signal_type)
            return None

def get_case_signals(case_id: str) -> list[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM case_signals WHERE case_id = ? ORDER BY timestamp DESC", (case_id,))
        rows = cursor.fetchall()
        signals = []
        for row in rows:
            result = dict(row)
            if result.get('details'):
                result['details'] = json.loads(result['details'])
            signals.append(result)
        return signals

def get_case_audit_log(case_id: str) -> list[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM case_audit_log WHERE case_id = ? ORDER BY timestamp DESC", (case_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def update_case_disposition(case_id: str, disposition: str, analyst_notes: str, analyst_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get current state for audit
        cursor.execute("SELECT status, disposition FROM risk_cases WHERE case_id = ?", (case_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError("Case not found")
            
        previous_state = row['status']
        new_state = "CLOSED"
        
        cursor.execute("""
            UPDATE risk_cases SET 
                disposition = ?,
                analyst_notes = ?,
                disposition_timestamp = ?,
                analyst_id = ?,
                status = ?
            WHERE case_id = ?
        """, (
            disposition, analyst_notes, datetime.now(UTC).isoformat(), analyst_id, new_state, case_id
        ))
        
        # Add audit log
        log_id = f"LOG-{uuid.uuid4().hex[:8].upper()}"
        cursor.execute("""
            INSERT INTO case_audit_log (
                log_id, case_id, timestamp, actor, event_type, previous_state, new_state, reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            log_id, case_id, datetime.now(UTC).isoformat(), analyst_id, "DISPOSITION_UPDATED", 
            previous_state, new_state, f"Disposition set to {disposition}"
        ))
        
        conn.commit()

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

def find_open_case_for_entity(entity_type: str, entity_id: str, current_timestamp: str, window_hours: int = 24) -> str:
    with get_db() as conn:
        cursor = conn.cursor()
        # Find the most recent open case for this entity
        cursor.execute("""
            SELECT case_id, as_of_timestamp FROM risk_cases 
            WHERE entity_type = ? AND entity_id = ? AND status = 'OPEN'
            ORDER BY as_of_timestamp DESC LIMIT 1
        """, (entity_type, entity_id))
        row = cursor.fetchone()
        if not row:
            return None
            
        case_ts = datetime.fromisoformat(row['as_of_timestamp'])
        curr_ts = datetime.fromisoformat(current_timestamp)
        
        # Check if it's within the window
        diff_hours = (curr_ts - case_ts).total_seconds() / 3600.0
        if diff_hours <= window_hours:
            return row['case_id']
            
        return None

def update_investigation(case_id: str, status: str, tools_used: list = None, 
                         evidence_bundle: list = None, ai_dossier: dict = None, 
                         grounding_result: dict = None, policy_decision: dict = None,
                         failure_reason: str = None):
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get current state for audit
        cursor.execute("SELECT investigation_status FROM risk_cases WHERE case_id = ?", (case_id,))
        row = cursor.fetchone()
        if not row:
            return
        previous_state = row['investigation_status']
        
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
        
        if previous_state != status:
            log_id = f"LOG-{uuid.uuid4().hex[:8].upper()}"
            cursor.execute("""
                INSERT INTO case_audit_log (
                    log_id, case_id, timestamp, actor, event_type, previous_state, new_state, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log_id, case_id, datetime.now(UTC).isoformat(), "SYSTEM", "INVESTIGATION_STATUS_CHANGED", 
                previous_state, status, "Agentic investigation update"
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
