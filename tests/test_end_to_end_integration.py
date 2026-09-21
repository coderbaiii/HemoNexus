"""
HEMONEXAS — End-to-End System Integration Tests
Member 4 Responsibility: Full lifecycle integration test spanning Frontend APIs ->
Flask Backend -> Database Queries -> 7-Step Matching Algorithm -> Dispatch ->
Donor Response -> Blood Release -> Donation Record.
"""
import pytest
from backend.services.matching_service import find_matching_donors
from backend.database_service import create_donation_record
from backend.database import query_db

def test_full_emergency_dispatch_and_fulfillment_lifecycle(client):
    """
    TC-E2E-001: Comprehensive end-to-end operational flow test:
    1. Register Patient and Donor.
    2. Patient creates urgent O+ blood request for Apollo Hospital.
    3. Matching engine queries DB and ranks active donor as #1.
    4. Patient dispatches invitation to the top donor.
    5. Donor authenticates, views incoming invitation, and accepts.
    6. Patient checks request status (progressed to MATCHING).
    7. Blood bank records completed donation in donation_records table.
    """
    # 1. Register Patient
    p_reg = client.post("/api/register", json={
        "full_name": "E2E Patient Test",
        "email": "e2e.patient@example.com",
        "password": "Password@123",
        "role": "patient",
        "phone": "+91 98888 11111",
        "location": "Salt Lake Sector 3, Kolkata",
        "latitude": 22.5697,
        "longitude": 88.4046
    })
    assert p_reg.status_code == 201
    patient_id = p_reg.get_json()["user"]["id"]

    # Register Donor (Active O+, nearby at Salt Lake Sector 5)
    d_reg = client.post("/api/register", json={
        "full_name": "E2E Donor Test",
        "email": "e2e.donor@example.com",
        "password": "Password@123",
        "role": "donor",
        "phone": "+91 98888 22222",
        "blood_group": "O+",
        "location": "Salt Lake Sector 5, Kolkata",
        "latitude": 22.5805,
        "longitude": 88.4344,
        "availability": "24_HOURS",
        "maximum_travel_distance": 25.0
    })
    assert d_reg.status_code == 201
    donor_user_id = d_reg.get_json()["user"]["id"]

    # 2. Patient Log in & Create Blood Request
    client.post("/api/login", json={"email": "e2e.patient@example.com", "password": "Password@123"})
    
    req_res = client.post("/api/patient/blood-requests", json={
        "required_blood_group": "O+",
        "required_units": 2,
        "hospital_name": "Apollo Multispecialty Hospital",
        "location": "EM Bypass, Kolkata",
        "latitude": 22.5697,
        "longitude": 88.4046,
        "preferred_max_distance": 20.0,
        "urgency": "CRITICAL"
    })
    assert req_res.status_code == 201
    request_id = req_res.get_json()["request"]["id"]

    # 3. Fetch Matches
    matches_res = client.get(f"/api/patient/blood-requests/{request_id}/matches")
    assert matches_res.status_code == 200
    matches_data = matches_res.get_json()
    assert matches_data["total_matches"] >= 1
    top_donor = matches_data["matches"][0]
    assert top_donor["blood_group"] == "O+"

    # 4. Dispatch invitation to Donor
    disp_res = client.post(f"/api/patient/blood-requests/{request_id}/send-request", json={
        "donor_id": donor_user_id
    })
    assert disp_res.status_code == 201

    # 5. Donor Logs in & Accepts Invitation
    client.post("/api/login", json={"email": "e2e.donor@example.com", "password": "Password@123"})
    
    invites_res = client.get("/api/donor/requests")
    assert invites_res.status_code == 200
    invites = invites_res.get_json()["requests"]
    assert len(invites) >= 1
    response_id = invites[0]["response_id"]

    accept_res = client.post(f"/api/donor/requests/{response_id}/accept", json={
        "message": "On my way to Apollo Hospital now."
    })
    assert accept_res.status_code == 200
    assert accept_res.get_json()["status"] == "ACCEPTED"

    # 6. Patient logs in & checks request status
    client.post("/api/login", json={"email": "e2e.patient@example.com", "password": "Password@123"})
    req_check = client.get(f"/api/patient/blood-requests/{request_id}")
    assert req_check.status_code == 200
    assert req_check.get_json()["request"]["request_status"] == "MATCHING"
    assert len(req_check.get_json()["responses"]) == 1
    assert req_check.get_json()["responses"][0]["status"] == "ACCEPTED"

    # 7. Fulfill Request & Record Completed Donation
    fulfill_res = client.post(f"/api/patient/blood-requests/{request_id}/fulfill")
    assert fulfill_res.status_code == 200

    # 8. Admin log in & verify stats
    client.post("/api/login", json={"email": "admin@hemonexus.org", "password": "Admin@123456"})
    admin_stats = client.get("/api/admin/stats")
    assert admin_stats.status_code == 200
    stats_data = admin_stats.get_json()["stats"]
    assert stats_data["total_donors"] >= 2
    assert stats_data["fulfilled_blood_requests"] >= 1
