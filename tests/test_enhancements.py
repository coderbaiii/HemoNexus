import datetime
import pytest
from backend.database import query_db, execute_db

def test_family_member_crud_and_isolation(client, app, db_conn):
    """Test full CRUD operations and cross-user isolation for family members."""
    # Register and login User 1
    r1 = client.post("/api/register", json={
        "full_name": "Family Head One",
        "email": "family1@example.com",
        "password": "Password123",
        "role": "patient"
    })
    assert r1.status_code == 201

    # 1. Add Family Member
    res = client.post("/api/family-members", json={
        "full_name": "Ananya Sharma",
        "relationship": "Sister",
        "blood_group": "A+",
        "age": 28,
        "contact_number": "+91 98765 00001",
        "medical_notes": "Mild asthma"
    })
    assert res.status_code == 201
    member = res.get_json()["family_member"]
    member_id = member["id"]
    assert member["full_name"] == "Ananya Sharma"
    assert member["relationship"] == "Sister"
    assert member["blood_group"] == "A+"

    # 2. List Family Members
    list_res = client.get("/api/family-members")
    assert list_res.status_code == 200
    members = list_res.get_json()["family_members"]
    assert len(members) == 1
    assert members[0]["id"] == member_id

    # 3. Update Family Member
    up_res = client.put(f"/api/family-members/{member_id}", json={
        "full_name": "Ananya Sharma Sen",
        "relationship": "Sister",
        "blood_group": "A+",
        "age": 29
    })
    assert up_res.status_code == 200
    assert up_res.get_json()["family_member"]["full_name"] == "Ananya Sharma Sen"
    assert up_res.get_json()["family_member"]["age"] == 29

    # 4. Cross-User Isolation: User 2 cannot access or delete User 1's family member
    client.post("/api/register", json={
        "full_name": "Family Head Two",
        "email": "family2@example.com",
        "password": "Password123",
        "role": "patient"
    })

    # User 2 list should be empty
    list_u2 = client.get("/api/family-members").get_json()["family_members"]
    assert len(list_u2) == 0

    # User 2 cannot delete User 1's family member
    del_forbidden = client.delete(f"/api/family-members/{member_id}")
    assert del_forbidden.status_code == 404

    # Sign back in as User 1 and delete
    client.post("/api/login", json={"email": "family1@example.com", "password": "Password123"})
    del_ok = client.delete(f"/api/family-members/{member_id}")
    assert del_ok.status_code == 200

    list_after = client.get("/api/family-members").get_json()["family_members"]
    assert len(list_after) == 0

def test_ngo_portal_verification_and_privacy_gating(client, admin_client, donor_client, db_conn):
    """Test NGO registration, admin verification requirement, and donor contact privacy safeguards."""
    # 1. Register NGO user
    reg = client.post("/api/register", json={
        "full_name": "Kolkata Blood Care Foundation",
        "email": "contact@kolkatabloodcare.org",
        "password": "Password123",
        "role": "ngo",
        "ngo_name": "Kolkata Blood Care Foundation",
        "registration_number": "NGO-WB-2026-9988",
        "contact_person": "Subrata Sen",
        "phone": "+91 98300 99999",
        "city": "Kolkata"
    })
    assert reg.status_code == 201

    # Fetch registered NGO profile
    prof_res = client.get("/api/ngo/profile")
    assert prof_res.status_code == 200
    ngo_prof = prof_res.get_json()["profile"]
    ngo_prof_id = ngo_prof["id"]
    assert ngo_prof["verification_status"] == "PENDING"
    assert prof_res.get_json()["is_verified"] is False

    # 2. Unverified NGO cannot send contact requests (Forbidden)
    donor_user = query_db("SELECT id FROM users WHERE email = 'amitav.donor@example.com'", one=True, db=db_conn)
    assert donor_user is not None
    donor_id = donor_user["id"]

    outreach_blocked = client.post("/api/ngo/contact-requests", json={
        "donor_id": donor_id,
        "required_blood_group": "O+",
        "message": "Urgent drive request."
    })
    assert outreach_blocked.status_code == 403
    assert "verification required" in outreach_blocked.get_json()["error"].lower()

    # 3. Privacy Safeguard: Donor search must mask contact info
    donors_res = client.get("/api/ngo/donors?blood_group=O+")
    assert donors_res.status_code == 200
    donors = donors_res.get_json()["donors"]
    assert len(donors) > 0
    donor_entry = next(d for d in donors if d["user_id"] == donor_id)
    assert donor_entry["is_contact_revealed"] is False
    assert "••••" in donor_entry["phone"]

    # 4. Admin verifies the NGO
    admin_verify = admin_client.post(f"/api/admin/ngos/{ngo_prof_id}/verify", json={"status": "VERIFIED"})
    assert admin_verify.status_code == 200

    # 5. Now verified NGO sends contact request
    outreach_ok = client.post("/api/ngo/contact-requests", json={
        "donor_id": donor_id,
        "required_blood_group": "O+",
        "message": "Urgent drive request from verified NGO."
    })
    assert outreach_ok.status_code == 201
    contact_req_id = outreach_ok.get_json()["request_id"]

    # 6. Donor views incoming NGO request and accepts it
    donor_inbox = donor_client.get("/api/donor/ngo-requests")
    assert donor_inbox.status_code == 200
    assert len(donor_inbox.get_json()["requests"]) > 0

    donor_accept = donor_client.post(f"/api/donor/ngo-requests/{contact_req_id}/accept")
    assert donor_accept.status_code == 200

    # 7. Privacy unmasked: NGO now sees verified donor phone and email
    tracked_requests = client.get("/api/ngo/contact-requests")
    assert tracked_requests.status_code == 200
    req_item = next(r for r in tracked_requests.get_json()["contact_requests"] if r["id"] == contact_req_id)
    assert req_item["status"] == "ACCEPTED"
    assert req_item["is_contact_revealed"] is True
    assert "+91 98300 11223" in req_item["phone"]

def test_user_profile_management_and_session_sync(client):
    """Test updating user profile and verifying changes persist and sync to session."""
    client.post("/api/register", json={
        "full_name": "Original Name",
        "email": "update.test@example.com",
        "password": "Password123",
        "role": "donor",
        "blood_group": "B+",
        "city": "Kolkata"
    })

    # Retrieve profile
    prof1 = client.get("/api/profile").get_json()
    assert prof1["success"] is True
    assert prof1["user"]["full_name"] == "Original Name"
    assert prof1["blood_group"] == "B+"

    # Update profile
    update_res = client.post("/api/profile", json={
        "full_name": "Updated Real Name",
        "email": "new.email@example.com",
        "phone": "+91 98300 88888",
        "address": "42 Salt Lake Sector 1",
        "city": "Salt Lake",
        "blood_group": "AB+",
        "availability": "NIGHTTIME"
    })
    assert update_res.status_code == 200

    # Verify updated profile
    prof2 = client.get("/api/profile").get_json()
    assert prof2["user"]["full_name"] == "Updated Real Name"
    assert prof2["user"]["email"] == "new.email@example.com"
    assert prof2["user"]["city"] == "Salt Lake"
    assert prof2["blood_group"] == "AB+"
    assert prof2["availability"] == "NIGHTTIME"

def test_user_blocking_and_recommendation_exclusion(client, patient_client, donor_client, db_conn):
    """Test bidirectional blocking, admin block protection, and exclusion from recommendation pipeline."""
    # 1. Fetch user IDs
    donor_user = query_db("SELECT id FROM users WHERE email = 'amitav.donor@example.com'", one=True, db=db_conn)
    patient_user = query_db("SELECT id FROM users WHERE email = 'patient.raj@example.com'", one=True, db=db_conn)
    admin_user = query_db("SELECT id FROM users WHERE email = 'admin@hemonexus.org'", one=True, db=db_conn)

    donor_id = donor_user["id"]
    patient_id = patient_user["id"]
    admin_id = admin_user["id"]

    # 2. Patient cannot block admin (Forbidden)
    block_admin = patient_client.post("/api/blocked-users", json={"blocked_id": admin_id})
    assert block_admin.status_code == 403

    # 3. Patient cannot block self
    block_self = patient_client.post("/api/blocked-users", json={"blocked_id": patient_id})
    assert block_self.status_code == 400

    # 4. Patient blocks Donor
    block_donor = patient_client.post("/api/blocked-users", json={
        "blocked_id": donor_id,
        "reason": "Harassment prevention test"
    })
    assert block_donor.status_code == 201

    # Check blocked list
    blocked_list = patient_client.get("/api/blocked-users").get_json()["blocked_users"]
    assert any(b["blocked_id"] == donor_id for b in blocked_list)

    # 5. Matching Engine Exclusion: Amitav (donor_id) must NOT appear in patient's matches
    req = query_db("SELECT id FROM blood_requests WHERE patient_id = ?", (patient_id,), one=True, db=db_conn)
    req_id = req["id"]
    matches_res = patient_client.get(f"/api/patient/blood-requests/{req_id}/matches")
    assert matches_res.status_code == 200
    matched_donor_ids = [m["user_id"] for m in matches_res.get_json()["matches"]]
    assert donor_id not in matched_donor_ids, "Blocked donor must never appear in patient's recommendations!"

    # 6. Patient cannot dispatch to blocked donor
    dispatch_blocked = patient_client.post(f"/api/patient/blood-requests/{req_id}/send-request", json={
        "donor_id": donor_id
    })
    # Cannot send request or donor excluded
    assert dispatch_blocked.status_code in (400, 403, 404, 409)

    # 7. Unblock donor restores matching
    unblock = patient_client.delete(f"/api/blocked-users/{donor_id}")
    assert unblock.status_code == 200

    matches_after = patient_client.get(f"/api/patient/blood-requests/{req_id}/matches").get_json()["matches"]
    matched_after_ids = [m["user_id"] for m in matches_after]
    assert donor_id in matched_after_ids, "Unblocked donor should reappear in eligible recommendations."

def test_smart_donor_sorting_and_multi_criteria_scoring(client, patient_client, db_conn):
    """Test smart recommendation scoring and sorting preferences."""
    req = query_db("SELECT id FROM blood_requests WHERE required_blood_group = 'O+'", one=True, db=db_conn)
    req_id = req["id"]

    # Best match ranking
    res_best = patient_client.get(f"/api/patient/blood-requests/{req_id}/matches")
    assert res_best.status_code == 200
    matches = res_best.get_json()["matches"]
    assert len(matches) > 0

    # Every match must have match_score and transparent recommendation reasons
    for m in matches:
        assert m["match_score"] > 0
        assert "score_breakdown" in m
        assert "recommendation_reasons" in m
        assert len(m["recommendation_reasons"]) > 0
        assert "medical_disclaimer" in m

    # Scores must be sorted descending
    scores = [m["match_score"] for m in matches]
    assert scores == sorted(scores, reverse=True)
