"""
HEMONEXAS — Database CRUD & Constraint Unit Tests
Member 4 Responsibility: Tests for Create, Read, Update, Delete, Foreign Key Cascades,
Unique Constraints, and Check Constraints across all 6 core entities.
"""
import pytest
import sqlite3
from backend.database_service import (
    create_user, get_user_by_id, get_user_by_email, update_user, delete_user,
    create_donor, get_donor_by_id, get_donor_by_user_id, update_donor,
    create_blood_request, get_blood_request_by_id, update_blood_request_status,
    log_donor_verification, get_donor_verification_history,
    create_request_response, update_request_response,
    create_donation_record, get_donation_records_by_donor
)
from backend.database import query_db, execute_db

# ============================================================================
# USERS CRUD TESTS
# ============================================================================

def test_user_crud_operations(app, db_conn):
    """TC-DB-USER-001: Test user creation, retrieval, update, and deletion."""
    with app.app_context():
        # Create
        user = create_user(
            full_name="Dr. Sourav Ganguly",
            email="sourav.test@example.com",
            password="Password@123",
            role="donor",
            phone="+91 99999 88888",
            db=db_conn
        )
        assert user is not None
        assert user["email"] == "sourav.test@example.com"
        assert user["role"] == "donor"
        assert user["password_hash"] != "Password@123"  # Hashed
        
        # Read by ID
        fetched_id = get_user_by_id(user["id"], db=db_conn)
        assert fetched_id["full_name"] == "Dr. Sourav Ganguly"
        
        # Read by Email
        fetched_email = get_user_by_email("sourav.test@example.com", db=db_conn)
        assert fetched_email["id"] == user["id"]
        
        # Update
        updated = update_user(user["id"], full_name="Sourav Ganguly (Updated)", phone="+91 91111 22222", db=db_conn)
        assert updated["full_name"] == "Sourav Ganguly (Updated)"
        assert updated["phone"] == "+91 91111 22222"
        
        # Delete
        success = delete_user(user["id"], db=db_conn)
        assert success is True
        assert get_user_by_id(user["id"], db=db_conn) is None

def test_user_unique_email_constraint(app, db_conn):
    """TC-DB-USER-002: Ensure duplicate emails are strictly rejected."""
    with app.app_context():
        create_user("User One", "duplicate@example.com", "Password@123", "patient", db=db_conn)
        with pytest.raises(ValueError, match="already registered"):
            create_user("User Two", "duplicate@example.com", "Password@123", "patient", db=db_conn)

def test_user_case_insensitive_email_unique(app, db_conn):
    """TC-DB-USER-003: Case-insensitive unique check on email."""
    with app.app_context():
        create_user("Case Test", "case.test@example.com", "Password@123", "donor", db=db_conn)
        with pytest.raises(ValueError, match="already registered"):
            create_user("Case Test 2", "CASE.TEST@EXAMPLE.COM", "Password@123", "donor", db=db_conn)

# ============================================================================
# DONORS CRUD TESTS
# ============================================================================

def test_donor_crud_and_foreign_key(app, db_conn):
    """TC-DB-DONOR-001: Test donor creation, foreign key to user, and cascade deletion."""
    with app.app_context():
        user = create_user("Donor Candidate", "donor.cand@example.com", "Password@123", "donor", db=db_conn)
        
        donor = create_donor(
            user_id=user["id"],
            blood_group="B+",
            location="Kolkata",
            latitude=22.5726,
            longitude=88.3639,
            availability_type="DAY",
            max_distance_km=20.0,
            db=db_conn
        )
        assert donor is not None
        assert donor["blood_group"] == "B+"
        assert donor["status"] == "ACTIVE"
        assert donor["max_distance_km"] == 20.0
        
        # Update donor
        updated_donor = update_donor(donor["id"], blood_group="B+", max_distance_km=35.0, status="TEMPORARILY_UNAVAILABLE", db=db_conn)
        assert updated_donor["max_distance_km"] == 35.0
        assert updated_donor["status"] == "TEMPORARILY_UNAVAILABLE"
        
        # Verify CASCADE delete when user is deleted
        delete_user(user["id"], db=db_conn)
        assert get_donor_by_id(donor["id"], db=db_conn) is None

# ============================================================================
# BLOOD REQUESTS CRUD TESTS
# ============================================================================

def test_blood_request_crud(app, db_conn):
    """TC-DB-REQ-001: Test blood requirement creation, retrieval, and status transitions."""
    with app.app_context():
        patient = create_user("Patient Test", "patient.reqtest@example.com", "Password@123", "patient", db=db_conn)
        
        req = create_blood_request(
            patient_id=patient["id"],
            blood_group="AB+",
            hospital_name="Ruby General Hospital",
            location="Kasba, Kolkata",
            units_required=3,
            preferred_max_distance=30.0,
            urgency="CRITICAL",
            db=db_conn
        )
        assert req is not None
        assert req["required_blood_group"] == "AB+"
        assert req["required_units"] == 3
        assert req["urgency"] == "CRITICAL"
        assert req["request_status"] == "OPEN"
        
        # Update status
        updated_req = update_blood_request_status(req["id"], "MATCHING", db=db_conn)
        assert updated_req["request_status"] == "MATCHING"
        
        updated_req2 = update_blood_request_status(req["id"], "FULFILLED", db=db_conn)
        assert updated_req2["request_status"] == "FULFILLED"

# ============================================================================
# DONOR VERIFICATIONS CRUD TESTS
# ============================================================================

def test_donor_verification_logging(app, db_conn):
    """TC-DB-VER-001: Test 6-month verification audit checkpoint logging."""
    with app.app_context():
        user = create_user("Ver Donor", "ver.donor@example.com", "Password@123", "donor", db=db_conn)
        donor = create_donor(user["id"], "A+", "Salt Lake", db=db_conn)
        
        # Log another verification checkpoint
        log_donor_verification(donor["id"], phone_confirmed=1, address_confirmed=1, availability_confirmed=1, travel_distance_confirmed=1, status="ACTIVE", db=db_conn)
        
        history = get_donor_verification_history(donor["id"], db=db_conn)
        assert len(history) >= 2  # Initial on creation + 1 manual
        assert history[0]["status"] == "ACTIVE"

# ============================================================================
# REQUEST RESPONSES CRUD TESTS
# ============================================================================

def test_request_responses_crud_and_uniqueness(app, db_conn):
    """TC-DB-RESP-001: Test request response creation, updates, and unique dispatch constraint."""
    with app.app_context():
        p_user = create_user("Req Patient", "req.patient@example.com", "Password@123", "patient", db=db_conn)
        d_user = create_user("Req Donor", "req.donor@example.com", "Password@123", "donor", db=db_conn)
        
        req = create_blood_request(p_user["id"], "O-", "Woodlands Hospital", db=db_conn)
        
        # Create response dispatch
        resp = create_request_response(req["id"], d_user["id"], response="PENDING", message="Urgent request", db=db_conn)
        assert resp["response"] == "PENDING"
        
        # Test Duplicate Dispatch Rejected by SQLite UNIQUE constraint
        with pytest.raises(sqlite3.IntegrityError):
            execute_db(
                "INSERT INTO request_responses (request_id, donor_id, response) VALUES (?, ?, 'PENDING')",
                (req["id"], d_user["id"]),
                db=db_conn
            )
            
        # Update response to ACCEPTED
        updated = update_request_response(resp["id"], "ACCEPTED", message="I will arrive in 30 minutes", db=db_conn)
        assert updated["response"] == "ACCEPTED"
        assert updated["message"] == "I will arrive in 30 minutes"
        assert updated["responded_at"] is not None

# ============================================================================
# DONATION RECORDS CRUD TESTS
# ============================================================================

def test_donation_records_crud(app, db_conn):
    """TC-DB-DONREC-001: Test donation record creation, component tracking, and query."""
    with app.app_context():
        user = create_user("Donating Donor", "donating.donor@example.com", "Password@123", "donor", db=db_conn)
        donor = create_donor(user["id"], "O+", "Garia", db=db_conn)
        
        rec = create_donation_record(
            donor_id=donor["id"],
            blood_centre="Medical College Blood Bank Kolkata",
            component="WHOLE_BLOOD",
            status="COMPLETED",
            db=db_conn
        )
        assert rec is not None
        assert rec["blood_centre"] == "Medical College Blood Bank Kolkata"
        assert rec["component"] == "WHOLE_BLOOD"
        assert rec["status"] == "COMPLETED"
        
        records = get_donation_records_by_donor(donor["id"], db=db_conn)
        assert len(records) == 1
        assert records[0]["id"] == rec["id"]
