import pytest
from backend.database import query_db

def test_patient_create_blood_request(patient_client):
    """Test patient creating a blood request."""
    res = patient_client.post("/api/patient/blood-requests", json={
        "required_blood_group": "A+",
        "required_units": 2,
        "hospital_name": "AMRI Hospital",
        "location": "Dhakuria, Kolkata",
        "latitude": 22.5110,
        "longitude": 88.3690,
        "urgency": "URGENT",
        "preferred_max_distance": 20.0
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    assert data["request"]["required_blood_group"] == "A+"
    assert data["request"]["request_status"] == "OPEN"

def test_send_donor_request_and_prevent_duplicate(patient_client, db_conn):
    """Test sending donation invitation and preventing duplicate active requests."""
    # Find existing request
    req = query_db("SELECT id FROM blood_requests WHERE patient_id = (SELECT id FROM users WHERE email = 'patient.raj@example.com')", one=True, db=db_conn)
    req_id = req["id"]
    
    # Get active donor Amitav Sengupta
    donor = query_db("SELECT id FROM users WHERE email = 'amitav.donor@example.com'", one=True, db=db_conn)
    donor_user_id = donor["id"]
    
    # 1. Send first request
    res1 = patient_client.post(f"/api/patient/blood-requests/{req_id}/send-request", json={
        "donor_id": donor_user_id
    })
    assert res1.status_code == 201
    data1 = res1.get_json()
    assert data1["success"] is True
    assert data1["status"] == "PENDING"
    resp_id = data1["response_id"]

    # 2. Duplicate send attempt must return 409 Conflict
    res2 = patient_client.post(f"/api/patient/blood-requests/{req_id}/send-request", json={
        "donor_id": donor_user_id
    })
    assert res2.status_code == 409
    data2 = res2.get_json()
    assert data2["success"] is False
    assert "already been sent" in data2["error"].lower()

def test_donor_accept_workflow(donor_client, patient_client, db_conn):
    """Test donor receiving and accepting blood donation invitation."""
    req = query_db("SELECT id FROM blood_requests WHERE required_blood_group = 'O+'", one=True, db=db_conn)
    req_id = req["id"]
    donor = query_db("SELECT id FROM users WHERE email = 'amitav.donor@example.com'", one=True, db=db_conn)
    donor_id = donor["id"]
    
    # Send request from patient
    send_res = patient_client.post(f"/api/patient/blood-requests/{req_id}/send-request", json={"donor_id": donor_id})
    if send_res.status_code == 201:
        resp_id = send_res.get_json()["response_id"]
    else:
        resp_row = query_db("SELECT id FROM donor_request_responses WHERE blood_request_id = ? AND donor_id = ?", (req_id, donor_id), one=True, db=db_conn)
        resp_id = resp_row["id"]
        
    # Donor checks incoming requests
    list_res = donor_client.get("/api/donor/requests")
    assert list_res.status_code == 200
    incoming = list_res.get_json()["requests"]
    assert len(incoming) >= 1

    # Donor accepts
    accept_res = donor_client.post(f"/api/donor/requests/{resp_id}/accept", json={
        "message": "I will arrive at the blood center by noon."
    })
    assert accept_res.status_code == 200
    data = accept_res.get_json()
    assert data["success"] is True
    assert data["status"] == "ACCEPTED"

    # Verify response status in database
    row = query_db("SELECT status, message FROM donor_request_responses WHERE id = ?", (resp_id,), one=True, db=db_conn)
    assert row["status"] == "ACCEPTED"
    assert "noon" in row["message"]

def test_cancel_blood_request(patient_client, db_conn):
    """Test patient cancelling a blood request."""
    req = query_db("SELECT id FROM blood_requests WHERE patient_id = (SELECT id FROM users WHERE email = 'patient.raj@example.com')", one=True, db=db_conn)
    req_id = req["id"]
    
    res = patient_client.patch(f"/api/patient/blood-requests/{req_id}/cancel")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    
    row = query_db("SELECT request_status FROM blood_requests WHERE id = ?", (req_id,), one=True, db=db_conn)
    assert row["request_status"] == "CANCELLED"
