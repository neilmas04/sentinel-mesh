import pytest
import sqlite3
import os
from src.api.database import init_db, get_db, DB_PATH

@pytest.fixture(autouse=True)
def setup_teardown():
    # Setup: ensure clean state
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    yield
    # Teardown: cleanup
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

def test_init_db_creates_table():
    assert not os.path.exists(DB_PATH)
    init_db()
    assert os.path.exists(DB_PATH)
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='risk_cases'")
        assert cursor.fetchone() is not None

def test_init_db_preserves_existing_data():
    init_db()
    
    # Insert a dummy record
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO risk_cases (
                case_id, transaction_id, as_of_timestamp, risk_score, risk_level, 
                triggered_signals, model_version, feature_version, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "CASE-TEST1", "tx1", "2026-01-01T00:00:00Z", 0.9, "HIGH",
            "[]", "v1", "v1", "OPEN", "2026-01-01T00:00:00Z"
        ))
        conn.commit()
        
    # Run init_db again
    init_db()
    
    # Verify data is preserved
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM risk_cases WHERE case_id = 'CASE-TEST1'")
        assert cursor.fetchone() is not None

def test_init_db_is_idempotent():
    init_db()
    init_db()
    init_db()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='risk_cases'")
        assert cursor.fetchone() is not None
