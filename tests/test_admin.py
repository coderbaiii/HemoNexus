import pytest

def test_admin_access_unauthorized_for_donor(donor_client):
    """Test that a regular donor is blocked from admin endpoints with 403."""
    res = donor_client.get("/api/admin/users")
    assert res.status_code == 403
    data = res.get_json()
    assert data["success"] is False
    assert "insufficient privileges" in data["error"].lower()

def test_admin_access_unauthorized_for_patient(patient_client):
    """Test that a regular patient is blocked from admin endpoints with 403."""
    res = patient_client.get("/api/admin/stats")
    assert res.status_code == 403
    data = res.get_json()
    assert data["success"] is False

def test_admin_access_unauthenticated(client):
    """Test unauthenticated request to admin route returns 401."""
    res = client.get("/api/admin/users")
    assert res.status_code == 401
    data = res.get_json()
    assert data["success"] is False

def test_admin_stats(admin_client):
    """Test admin stats overview endpoint."""
    res = admin_client.get("/api/admin/stats")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    stats = data["stats"]
    assert stats["total_users"] >= 3
    assert stats["total_donors"] >= 2
    assert "active_donors" in stats
    assert "verification_due_donors" in stats

def test_admin_donors_list_and_filter(admin_client):
    """Test admin donors directory and status filtering."""
    # All donors
    res_all = admin_client.get("/api/admin/donors")
    assert res_all.status_code == 200
    donors_all = res_all.get_json()["donors"]
    assert len(donors_all) >= 3

    # Filter by ACTIVE
    res_active = admin_client.get("/api/admin/donors?status=ACTIVE")
    assert res_active.status_code == 200
    donors_active = res_active.get_json()["donors"]
    for d in donors_active:
        assert d["profile_status"] == "ACTIVE"

def test_admin_verify_check_sweep(admin_client):
    """Test admin triggering a 6-month verification sweep."""
    res = admin_client.post("/api/admin/verify-check")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "evaluated" in data["details"]

def test_admin_override_donor_status(admin_client, db_conn):
    """Test admin manually overriding a donor's profile status."""
    from backend.database import query_db
    donor = query_db("SELECT id, profile_status FROM donor_profiles LIMIT 1", one=True, db=db_conn)
    donor_id = donor["id"]

    res = admin_client.patch(f"/api/admin/donors/{donor_id}/status", json={
        "status": "INACTIVE"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["new_status"] == "INACTIVE"

    # Verify status changed in DB
    updated = query_db("SELECT profile_status FROM donor_profiles WHERE id = ?", (donor_id,), one=True, db=db_conn)
    assert updated["profile_status"] == "INACTIVE"
