"""
HEMONEXAS — Database Validation & Check Constraint Tests
Member 4 Responsibility: Unit tests verifying that invalid input, invalid blood types,
negative distances, invalid statuses, and missing required fields are properly rejected.
"""
import pytest
import sqlite3
from backend.database_service import (
    create_user, create_donor, create_blood_request, create_donation_record,
    validate_blood_group, validate_role, validate_donor_status,
    validate_availability_type, validate_positive_distance, validate_positive_units,
    validate_email
)
from backend.database import execute_db

# ============================================================================
# BLOOD GROUP VALIDATION TESTS
# ============================================================================

def test_blood_group_validation_valid():
    """TC-VAL-BG-001: Test all 8 valid ABO/Rh blood groups."""
    valid_groups = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
    for bg in valid_groups:
        ok, res = validate_blood_group(bg)
        assert ok is True
        assert res == bg

def test_blood_group_validation_invalid():
    """TC-VAL-BG-002: Test invalid blood groups rejected."""
    invalid_groups = ["C+", "O*", "XYZ", "A", "B", "", None, "123"]
    for bg in invalid_groups:
        ok, res = validate_blood_group(bg)
        assert ok is False

def test_database_check_constraint_blood_group(app, db_conn):
    """TC-VAL-BG-003: SQLite check constraint enforces valid blood group."""
    with app.app_context():
        user = create_user("Check User", "check.user@example.com", "Password@123", "donor", db=db_conn)
        with pytest.raises(sqlite3.IntegrityError):
            execute_db(
                "INSERT INTO donors (user_id, blood_group, location, next_verification_date) VALUES (?, 'INVALID', 'Kolkata', '2026-12-31')",
                (user["id"],),
                db=db_conn
            )

# ============================================================================
# ROLE & STATUS VALIDATION TESTS
# ============================================================================

def test_role_validation():
    """TC-VAL-ROLE-001: Test role validation."""
    assert validate_role("donor")[0] is True
    assert validate_role("patient")[0] is True
    assert validate_role("admin")[0] is True
    assert validate_role("superadmin")[0] is False
    assert validate_role("")[0] is False

def test_donor_status_validation():
    """TC-VAL-STAT-001: Test donor lifecycle status validation."""
    valid_statuses = ["ACTIVE", "VERIFICATION_DUE", "INACTIVE", "TEMPORARILY_UNAVAILABLE"]
    for s in valid_statuses:
        assert validate_donor_status(s)[0] is True
        
    assert validate_donor_status("DELETED")[0] is False
    assert validate_donor_status("EXPIRED")[0] is False

# ============================================================================
# DISTANCE & NUMERIC VALIDATION TESTS
# ============================================================================

def test_positive_distance_validation():
    """TC-VAL-DIST-001: Test travel distance validation."""
    assert validate_positive_distance(15.0)[0] is True
    assert validate_positive_distance(0.5)[0] is True
    assert validate_positive_distance("25.5")[0] is True
    
    # Invalid distances
    assert validate_positive_distance(0)[0] is False
    assert validate_positive_distance(-10)[0] is False
    assert validate_positive_distance("abc")[0] is False
    assert validate_positive_distance(1000)[0] is False  # Above reasonable threshold

def test_positive_units_validation():
    """TC-VAL-UNIT-001: Test required units validation."""
    assert validate_positive_units(1)[0] is True
    assert validate_positive_units(4)[0] is True
    assert validate_positive_units(0)[0] is False
    assert validate_positive_units(-2)[0] is False
    assert validate_positive_units("invalid")[0] is False

def test_email_validation():
    """TC-VAL-EMAIL-001: Test email formatting."""
    assert validate_email("donor@example.com")[0] is True
    assert validate_email("invalid-email")[0] is False
    assert validate_email("")[0] is False
    assert validate_email(None)[0] is False

# ============================================================================
# MISSING REQUIRED FIELDS & FOREIGN KEY CHECKS
# ============================================================================

def test_create_user_missing_fields(app, db_conn):
    """TC-VAL-REQ-001: Missing required fields in user creation."""
    with app.app_context():
        with pytest.raises(ValueError, match="Full name is required"):
            create_user("", "test@example.com", "Password@123", db=db_conn)
            
        with pytest.raises(ValueError, match="Password must be at least 6 characters"):
            create_user("Test User", "test@example.com", "123", db=db_conn)

def test_donor_nonexistent_user_foreign_key(app, db_conn):
    """TC-VAL-FK-001: Attempting to create donor with non-existent user_id."""
    with app.app_context():
        with pytest.raises(ValueError, match="does not exist"):
            create_donor(user_id=99999, blood_group="O+", location="Kolkata", db=db_conn)

def test_donation_record_nonexistent_donor(app, db_conn):
    """TC-VAL-FK-002: Attempting to create donation record for non-existent donor."""
    with app.app_context():
        with pytest.raises(ValueError, match="not found"):
            create_donation_record(donor_id=99999, blood_centre="Kolkata Central Blood Bank", db=db_conn)
