import datetime
import pytest
from backend.services.verification_service import compute_lifecycle_status, sweep_and_update_donor_statuses
from backend.database import query_db, execute_db

def test_get_donor_profile(donor_client):
    """Test getting own profile as a donor."""
    res = donor_client.get("/api/donor/profile")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["profile"]["blood_group"] == "O+"
    assert data["verification"]["profile_status"] == "ACTIVE"
    assert data["verification"]["verification_interval_days"] == 180

def test_update_donor_profile(donor_client):
    """Test updating donor availability and location parameters."""
    res = donor_client.post("/api/donor/profile", json={
        "blood_group": "O+",
        "phone": "+91 98300 55555",
        "location": "New Town Action Area 1",
        "availability": "NIGHTTIME",
        "maximum_travel_distance": 30.0,
        "latitude": 22.5850,
        "longitude": 88.4700
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["profile"]["availability"] == "NIGHTTIME"
    assert data["profile"]["maximum_travel_distance"] == 30.0
    assert data["profile"]["phone"] == "+91 98300 55555"

def test_update_donor_invalid_blood_group(donor_client):
    """Test updating with an invalid blood group returns 400."""
    res = donor_client.post("/api/donor/profile", json={
        "blood_group": "X_POSITIVE",
        "availability": "24_HOURS"
    })
    assert res.status_code == 400
    data = res.get_json()
    assert data["success"] is False

def test_donor_verification_cycle_refresh(donor_client):
    """Test that calling verify resets status to ACTIVE and recalculates 6-month due date."""
    res = donor_client.post("/api/donor/profile/verify")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["verification"]["status"] == "ACTIVE"
    assert data["verification"]["verification_interval_days"] == 180

def test_verification_lifecycle_status_computation():
    """Unit test for 6-month status lifecycle transitions."""
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # 1. Within 6 months -> ACTIVE
    future_date = now + datetime.timedelta(days=90)
    assert compute_lifecycle_status(future_date, current_dt=now, grace_days=30) == "ACTIVE"
    
    # 2. Due date passed but within 30-day grace period -> VERIFICATION_DUE
    due_date = now - datetime.timedelta(days=15)
    assert compute_lifecycle_status(due_date, current_dt=now, grace_days=30) == "VERIFICATION_DUE"
    
    # 3. Due date passed beyond 30-day grace period -> INACTIVE
    expired_date = now - datetime.timedelta(days=45)
    assert compute_lifecycle_status(expired_date, current_dt=now, grace_days=30) == "INACTIVE"

def test_sweep_does_not_delete_inactive_donors(app, db_conn):
    """Verify that six-month sweep transitions expired profiles to INACTIVE without deleting rows."""
    with app.app_context():
        count_before = query_db("SELECT COUNT(*) AS count FROM donor_profiles", one=True, db=db_conn)["count"]
        
        # Execute system sweep
        stats = sweep_and_update_donor_statuses(db=db_conn)
        
        count_after = query_db("SELECT COUNT(*) AS count FROM donor_profiles", one=True, db=db_conn)["count"]
        assert count_before == count_after, "Inactive donor records must never be deleted!"
        
        # Verify inactive donor seeded earlier is preserved
        rohan = query_db("SELECT * FROM donor_profiles WHERE profile_status = 'INACTIVE'", db=db_conn)
        assert len(rohan) >= 1
