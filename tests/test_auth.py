import pytest

def test_register_donor_success(client):
    """Test successful registration of a new donor."""
    res = client.post("/api/register", json={
        "full_name": "Dr. Ananya Roy",
        "email": "ananya.roy@example.com",
        "password": "SecurePassword123",
        "role": "donor",
        "blood_group": "B+",
        "phone": "+91 98301 99999",
        "location": "Ballygunge, Kolkata",
        "availability": "DAYTIME",
        "maximum_travel_distance": 20.0
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    assert data["user"]["email"] == "ananya.roy@example.com"
    assert data["user"]["role"] == "donor"
    assert "password_hash" not in data["user"]

def test_register_patient_success(client):
    """Test successful registration of a new patient."""
    res = client.post("/api/register", json={
        "full_name": "Siddharth Sen",
        "email": "siddharth.sen@example.com",
        "password": "PatientPassword123",
        "role": "patient"
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    assert data["user"]["role"] == "patient"

def test_register_duplicate_email_rejected(client):
    """Test that registering with an already existing email returns 409 Conflict."""
    res = client.post("/api/register", json={
        "full_name": "Duplicate User",
        "email": "amitav.donor@example.com",  # Already in seed data
        "password": "Password123",
        "role": "donor"
    })
    assert res.status_code == 409
    data = res.get_json()
    assert data["success"] is False
    assert "already exists" in data["error"].lower()

def test_register_admin_self_registration_forbidden(client):
    """Test that self-registering as admin is strictly blocked."""
    res = client.post("/api/register", json={
        "full_name": "Fake Admin",
        "email": "fake.admin@example.com",
        "password": "AdminPassword123",
        "role": "admin"
    })
    assert res.status_code == 400
    data = res.get_json()
    assert data["success"] is False
    assert "invalid role" in data["error"].lower()

def test_register_validation_missing_fields(client):
    """Test that missing required fields return 400 Bad Request."""
    res = client.post("/api/register", json={
        "full_name": "",
        "email": "no.name@example.com",
        "password": "Password123",
        "role": "donor"
    })
    assert res.status_code == 400
    data = res.get_json()
    assert data["success"] is False

def test_register_invalid_email(client):
    """Test that malformed email returns 400."""
    res = client.post("/api/register", json={
        "full_name": "Bad Email User",
        "email": "not-an-email",
        "password": "Password123",
        "role": "donor"
    })
    assert res.status_code == 400
    data = res.get_json()
    assert "invalid email" in data["error"].lower()

def test_login_success(client):
    """Test login with correct email and password."""
    res = client.post("/api/login", json={
        "email": "amitav.donor@example.com",
        "password": "Donor@1234"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["user"]["email"] == "amitav.donor@example.com"
    assert "password_hash" not in data["user"]
    assert "profile" in data
    assert data["profile"]["blood_group"] == "O+"

def test_login_wrong_password(client):
    """Test login with incorrect password returns 401."""
    res = client.post("/api/login", json={
        "email": "amitav.donor@example.com",
        "password": "WrongPassword123"
    })
    assert res.status_code == 401
    data = res.get_json()
    assert data["success"] is False

def test_login_nonexistent_user(client):
    """Test login with unregistered email returns 401."""
    res = client.post("/api/login", json={
        "email": "doesnotexist@example.com",
        "password": "SomePassword"
    })
    assert res.status_code == 401
    data = res.get_json()
    assert data["success"] is False

def test_session_current_user_me(donor_client):
    """Test /api/me returns authenticated donor and profile details without secrets."""
    res = donor_client.get("/api/me")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["user"]["email"] == "amitav.donor@example.com"
    assert "password_hash" not in data["user"]
    assert data["profile"]["blood_group"] == "O+"

def test_logout_flow(donor_client):
    """Test logout clears session and subsequent /api/me returns no user."""
    res = donor_client.post("/api/logout")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True

    me_res = donor_client.get("/api/me")
    assert me_res.status_code == 200
    me_data = me_res.get_json()
    assert me_data["user"] is None
