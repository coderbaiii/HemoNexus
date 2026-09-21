"""
HEMONEXAS — Matching Algorithm & Database Integration Tests
Member 4 Responsibility: Comprehensive integration tests verifying the database query
and filtering interaction with Member 3's 7-step matching algorithm.
"""
import pytest
import datetime
from backend.services.matching_service import find_matching_donors, haversine_distance_km
from backend.database_service import create_user, create_donor, create_blood_request
from backend.database import query_db, execute_db

def test_match_correct_blood_group(app, db_conn):
    """TC-MATCH-001: Correct blood group donor is included as candidate."""
    with app.app_context():
        p_user = create_user("Patient Match 1", "pat.m1@example.com", "Password@123", "patient", db=db_conn)
        req = create_blood_request(p_user["id"], "O+", "Apollo Hospital", latitude=22.5697, longitude=88.4046, preferred_max_distance=25.0, db=db_conn)
        
        d_user = create_user("Donor Match 1", "don.m1@example.com", "Password@123", "donor", db=db_conn)
        create_donor(d_user["id"], "O+", "Salt Lake", latitude=22.5805, longitude=88.4344, availability_type="24_HOURS", max_distance_km=25.0, status="ACTIVE", db=db_conn)
        
        matches = find_matching_donors(req["id"], db=db_conn)
        matched_emails = [m["email"] for m in matches]
        assert "don.m1@example.com" in matched_emails

def test_match_wrong_blood_group_excluded(app, db_conn):
    """TC-MATCH-002: Incompatible blood group donor is strictly excluded."""
    with app.app_context():
        p_user = create_user("Patient Match 2", "pat.m2@example.com", "Password@123", "patient", db=db_conn)
        req = create_blood_request(p_user["id"], "B+", "AMRI Hospital", latitude=22.5852, longitude=88.4124, db=db_conn)
        
        d_user = create_user("Donor Match 2 (A+)", "don.m2@example.com", "Password@123", "donor", db=db_conn)
        create_donor(d_user["id"], "A+", "Salt Lake", latitude=22.5852, longitude=88.4124, status="ACTIVE", db=db_conn)
        
        matches = find_matching_donors(req["id"], db=db_conn)
        matched_emails = [m["email"] for m in matches]
        assert "don.m2@example.com" not in matched_emails

def test_match_inactive_donor_excluded(app, db_conn):
    """TC-MATCH-003: Inactive donor is excluded from matching results."""
    with app.app_context():
        p_user = create_user("Patient Match 3", "pat.m3@example.com", "Password@123", "patient", db=db_conn)
        req = create_blood_request(p_user["id"], "O+", "Apollo Hospital", latitude=22.5697, longitude=88.4046, db=db_conn)
        
        d_user = create_user("Donor Match 3 (Inactive)", "don.m3@example.com", "Password@123", "donor", db=db_conn)
        create_donor(d_user["id"], "O+", "Salt Lake", latitude=22.5697, longitude=88.4046, status="INACTIVE", db=db_conn)
        
        matches = find_matching_donors(req["id"], db=db_conn)
        matched_emails = [m["email"] for m in matches]
        assert "don.m3@example.com" not in matched_emails

def test_match_unavailable_schedule_excluded(app, db_conn):
    """TC-MATCH-004: Donor whose availability schedule does not fit request time is excluded."""
    with app.app_context():
        p_user = create_user("Patient Match 4", "pat.m4@example.com", "Password@123", "patient", db=db_conn)
        # Night emergency request at 02:00 AM UTC
        night_req_time = "2026-10-15T02:00:00+00:00"
        req = create_blood_request(p_user["id"], "O+", "Apollo Hospital", required_time=night_req_time, latitude=22.5697, longitude=88.4046, db=db_conn)
        
        # Daytime only donor (08:00 to 18:00)
        d_user = create_user("Daytime Donor", "day.donor@example.com", "Password@123", "donor", db=db_conn)
        create_donor(d_user["id"], "O+", "Salt Lake", latitude=22.5697, longitude=88.4046, availability_type="DAYTIME", status="ACTIVE", db=db_conn)
        
        matches = find_matching_donors(req["id"], db=db_conn)
        matched_emails = [m["email"] for m in matches]
        assert "day.donor@example.com" not in matched_emails

def test_match_outside_patient_search_radius_excluded(app, db_conn):
    """TC-MATCH-005: Donor beyond patient's preferred radius is excluded."""
    with app.app_context():
        p_user = create_user("Patient Match 5", "pat.m5@example.com", "Password@123", "patient", db=db_conn)
        # Patient radius 5 km
        req = create_blood_request(p_user["id"], "O+", "Apollo Hospital", latitude=22.5697, longitude=88.4046, preferred_max_distance=5.0, db=db_conn)
        
        # Faraway donor (Barasat, ~20 km away)
        d_user = create_user("Far Donor", "far.donor@example.com", "Password@123", "donor", db=db_conn)
        create_donor(d_user["id"], "O+", "Barasat", latitude=22.7230, longitude=88.4817, max_distance_km=50.0, status="ACTIVE", db=db_conn)
        
        matches = find_matching_donors(req["id"], db=db_conn)
        matched_emails = [m["email"] for m in matches]
        assert "far.donor@example.com" not in matched_emails

def test_match_beyond_donor_max_travel_excluded(app, db_conn):
    """TC-MATCH-006: Patient is beyond donor's max travel distance -> excluded."""
    with app.app_context():
        p_user = create_user("Patient Match 6", "pat.m6@example.com", "Password@123", "patient", db=db_conn)
        # Patient radius 50 km
        req = create_blood_request(p_user["id"], "O+", "Apollo Hospital", latitude=22.5697, longitude=88.4046, preferred_max_distance=50.0, db=db_conn)
        
        # Donor max travel is only 2 km
        d_user = create_user("Short Travel Donor", "short.donor@example.com", "Password@123", "donor", db=db_conn)
        create_donor(d_user["id"], "O+", "Howrah", latitude=22.5857, longitude=88.3426, max_distance_km=2.0, status="ACTIVE", db=db_conn)
        
        matches = find_matching_donors(req["id"], db=db_conn)
        matched_emails = [m["email"] for m in matches]
        assert "short.donor@example.com" not in matched_emails

def test_match_all_conditions_satisfied_and_ranked(app, db_conn):
    """TC-MATCH-007: Multiple eligible donors are correctly ranked by composite score."""
    with app.app_context():
        p_user = create_user("Patient Rank", "pat.rank@example.com", "Password@123", "patient", db=db_conn)
        req = create_blood_request(p_user["id"], "O+", "Apollo Hospital", latitude=22.5697, longitude=88.4046, preferred_max_distance=30.0, db=db_conn)
        
        matches = find_matching_donors(req["id"], db=db_conn)
        assert len(matches) >= 2
        # Check descending sort order
        scores = [m["match_score"] for m in matches]
        assert scores == sorted(scores, reverse=True)
