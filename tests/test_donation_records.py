"""
HEMONEXAS — Donation Records Unit & Integration Tests
Member 4 Responsibility: Tests for the donation_records entity, component types,
blood center verification, and query relationships.
"""
import pytest
import sqlite3
from backend.database_service import (
    create_user, create_donor, create_blood_request,
    create_donation_record, get_donation_records_by_donor,
    get_donation_records_by_request
)
from backend.database import query_db, execute_db

def test_create_valid_donation_record(app, db_conn):
    """TC-DONREC-001: Create valid donation record for whole blood."""
    with app.app_context():
        user = create_user("Hero Donor", "hero.donor@example.com", "Password@123", "donor", db=db_conn)
        donor = create_donor(user["id"], "O+", "Salt Lake", db=db_conn)
        
        rec = create_donation_record(
            donor_id=donor["id"],
            blood_centre="SSKM Hospital Transfusion Unit",
            component="WHOLE_BLOOD",
            status="COMPLETED",
            db=db_conn
        )
        assert rec is not None
        assert rec["donor_id"] == donor["id"]
        assert rec["blood_centre"] == "SSKM Hospital Transfusion Unit"
        assert rec["component"] == "WHOLE_BLOOD"
        assert rec["status"] == "COMPLETED"

def test_donation_components_validation(app, db_conn):
    """TC-DONREC-002: Test all valid components (WHOLE_BLOOD, RBC, PLATELETS, PLASMA)."""
    with app.app_context():
        user = create_user("Comp Donor", "comp.donor@example.com", "Password@123", "donor", db=db_conn)
        donor = create_donor(user["id"], "AB-", "Park Circus", db=db_conn)
        
        for comp in ["WHOLE_BLOOD", "RBC", "PLATELETS", "PLASMA"]:
            rec = create_donation_record(donor["id"], "Central Blood Bank", component=comp, db=db_conn)
            assert rec["component"] == comp
            
        with pytest.raises(ValueError, match="Invalid component"):
            create_donation_record(donor["id"], "Central Blood Bank", component="INVALID_COMP", db=db_conn)

def test_donation_linked_to_blood_request(app, db_conn):
    """TC-DONREC-003: Donation record linked to a fulfilled blood request."""
    with app.app_context():
        p_user = create_user("Req Patient Rec", "pat.rec@example.com", "Password@123", "patient", db=db_conn)
        d_user = create_user("Req Donor Rec", "don.rec@example.com", "Password@123", "donor", db=db_conn)
        
        donor = create_donor(d_user["id"], "B+", "New Town", db=db_conn)
        req = create_blood_request(p_user["id"], "B+", "AMRI Salt Lake", db=db_conn)
        
        rec = create_donation_record(
            donor_id=donor["id"],
            request_id=req["id"],
            blood_centre="AMRI Hospital Blood Centre",
            component="RBC",
            status="COMPLETED",
            db=db_conn
        )
        assert rec["request_id"] == req["id"]
        
        req_records = get_donation_records_by_request(req["id"], db=db_conn)
        assert len(req_records) == 1
        assert req_records[0]["id"] == rec["id"]
