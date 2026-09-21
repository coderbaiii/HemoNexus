"""
HEMONEXAS — Six-Month Verification Lifecycle Unit Tests
Member 4 Responsibility: Tests for the 180-day freshness verification workflow,
status transitions (ACTIVE -> VERIFICATION_DUE -> INACTIVE -> Reactivation),
and audit logging without deleting accounts.
"""
import pytest
import datetime
from backend.config import Config
from backend.services.verification_service import (
    compute_lifecycle_status,
    refresh_donor_verification,
    sweep_and_update_donor_statuses,
    get_donor_verification_details
)
from backend.database_service import create_user, create_donor, get_donor_by_user_id
from backend.database import query_db, execute_db

def test_lifecycle_status_computation():
    """TC-VER-001: Verification within 180 days remains ACTIVE."""
    now = datetime.datetime.now(datetime.timezone.utc)
    future_date = now + datetime.timedelta(days=90)
    status = compute_lifecycle_status(future_date, current_dt=now)
    assert status == "ACTIVE"

def test_lifecycle_status_verification_due():
    """TC-VER-002: Reaching next_verification_date enters VERIFICATION_DUE (grace period)."""
    now = datetime.datetime.now(datetime.timezone.utc)
    due_date = now - datetime.timedelta(days=5)  # 5 days overdue (within 30-day grace)
    status = compute_lifecycle_status(due_date, current_dt=now, grace_days=30)
    assert status == "VERIFICATION_DUE"

def test_lifecycle_status_grace_period_expired_inactive():
    """TC-VER-003: Grace period exceeded without confirmation transitions to INACTIVE."""
    now = datetime.datetime.now(datetime.timezone.utc)
    expired_date = now - datetime.timedelta(days=45)  # 45 days overdue (beyond 30-day grace)
    status = compute_lifecycle_status(expired_date, current_dt=now, grace_days=30)
    assert status == "INACTIVE"

def test_donor_verification_refresh_flow(app, db_conn):
    """TC-VER-004: Donor confirms profile freshness -> resets status to ACTIVE and logs audit."""
    with app.app_context():
        user = create_user("Freshened Donor", "fresh.donor@example.com", "Password@123", "donor", db=db_conn)
        
        # Create initially with past date
        now = datetime.datetime.now(datetime.timezone.utc)
        past_next = (now - datetime.timedelta(days=10)).isoformat()
        donor = create_donor(user["id"], "O+", "Salt Lake", status="VERIFICATION_DUE", next_verification_date=past_next, db=db_conn)
        
        # Donor confirms profile
        res = refresh_donor_verification(user["id"], db=db_conn)
        assert res["status"] == "ACTIVE"
        
        # Check database
        updated = get_donor_by_user_id(user["id"], db=db_conn)
        assert updated["status"] == "ACTIVE"
        
        # Check donor_verifications table has logged the confirmation
        ver_history = query_db("SELECT * FROM donor_verifications WHERE donor_id = ?", (donor["id"],), db=db_conn)
        assert len(ver_history) >= 2

def test_inactive_donor_reactivation(app, db_conn):
    """TC-VER-005: Inactive donor can be reactivated back to ACTIVE after updating/confirming profile."""
    with app.app_context():
        user = create_user("Inactive Donor", "inactive.donor@example.com", "Password@123", "donor", db=db_conn)
        
        now = datetime.datetime.now(datetime.timezone.utc)
        expired_date = (now - datetime.timedelta(days=100)).isoformat()
        donor = create_donor(user["id"], "B+", "Howrah", status="INACTIVE", next_verification_date=expired_date, db=db_conn)
        
        # Inactive donor confirms profile
        refresh_donor_verification(user["id"], db=db_conn)
        
        # Check donor is ACTIVE again
        updated = get_donor_by_user_id(user["id"], db=db_conn)
        assert updated["status"] == "ACTIVE"

def test_sweep_updates_statuses_without_deleting(app, db_conn):
    """TC-VER-006: Verification sweep updates status but preserves account records."""
    with app.app_context():
        # Count donors before sweep
        count_before = query_db("SELECT COUNT(*) AS c FROM donors", db=db_conn, one=True)["c"]
        
        stats = sweep_and_update_donor_statuses(db=db_conn)
        assert stats["evaluated"] == count_before
        
        # Count donors after sweep
        count_after = query_db("SELECT COUNT(*) AS c FROM donors", db=db_conn, one=True)["c"]
        assert count_before == count_after  # No records deleted!
