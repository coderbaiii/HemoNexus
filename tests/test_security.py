import pytest
from backend.database import query_db

def test_sql_injection_attempt_in_login(client):
    """Test SQL injection attack in login input is safely handled via parameterized SQL."""
    injection_email = "' OR '1'='1' --"
    res = client.post("/api/login", json={
        "email": injection_email,
        "password": "random_password"
    })
    assert res.status_code == 401
    data = res.get_json()
    assert data["success"] is False

def test_passwords_never_stored_in_plaintext(db_conn):
    """Test that all passwords in users table are securely hashed and never plain text."""
    users = query_db("SELECT email, password_hash FROM users", db=db_conn)
    assert len(users) > 0
    for u in users:
        h = u["password_hash"]
        assert not h.startswith("Admin@")
        assert not h.startswith("Donor@")
        assert not h.startswith("Patient@")
        assert h.startswith("scrypt:") or h.startswith("pbkdf2:")

def test_password_hash_never_exposed_via_apis(admin_client, donor_client, patient_client):
    """Verify that password_hash is never included in JSON responses across all user/auth endpoints."""
    # 1. /api/me
    for c in (admin_client, donor_client, patient_client):
        res = c.get("/api/me")
        data = res.get_json()
        assert "password_hash" not in data.get("user", {})

    # 2. /api/admin/users
    res_users = admin_client.get("/api/admin/users")
    for u in res_users.get_json().get("users", []):
        assert "password_hash" not in u
        assert "password" not in u

def test_patient_cross_user_isolation(client, db_conn):
    """Test that a patient cannot access or modify another patient's private request."""
    # Register patient 2
    client.post("/api/register", json={
        "full_name": "Patient Two",
        "email": "patient2@example.com",
        "password": "Password123",
        "role": "patient"
    })

    # Find request belonging to patient 1 (Rajesh Kumar)
    req1 = query_db("SELECT id FROM blood_requests WHERE patient_id = (SELECT id FROM users WHERE email = 'patient.raj@example.com')", one=True, db=db_conn)
    assert req1 is not None

    # Patient 2 tries to access Patient 1's request
    res = client.get(f"/api/patient/blood-requests/{req1['id']}")
    assert res.status_code == 403
    data = res.get_json()
    assert data["success"] is False
