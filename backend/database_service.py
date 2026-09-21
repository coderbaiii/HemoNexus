"""
HEMONEXAS — Database Service & Validation Layer
Member 4 Responsibility: CRUD Operations, Data Validation, Foreign Key Integrity, and Query Abstractions.
"""
import re
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from backend.config import Config
from backend.database import get_db, query_db, execute_db

# Constants & Enums
VALID_BLOOD_GROUPS = ("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-")
VALID_ROLES = ("donor", "patient", "admin", "DONOR", "PATIENT", "ADMIN")
VALID_DONOR_STATUSES = ("ACTIVE", "VERIFICATION_DUE", "INACTIVE", "TEMPORARILY_UNAVAILABLE")
VALID_AVAILABILITIES = ("24_HOURS", "8_HOURS", "DAY", "NIGHT", "DAYTIME", "NIGHTTIME")
VALID_URGENCIES = ("LOW", "NORMAL", "URGENT", "CRITICAL")
VALID_REQUEST_STATUSES = ("OPEN", "MATCHING", "FULFILLED", "CANCELLED")
VALID_RESPONSE_STATUSES = ("PENDING", "ACCEPTED", "REJECTED", "CANCELLED")
VALID_COMPONENTS = ("WHOLE_BLOOD", "RBC", "PLATELETS", "PLASMA")
VALID_DONATION_STATUSES = ("COMPLETED", "DISCARDED", "TESTING_PENDING")

EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")

# ============================================================================
# VALIDATION HELPERS
# ============================================================================

def validate_email(email):
    """Validates email format."""
    if not email or not isinstance(email, str):
        return False, "Email address is required."
    email = email.strip()
    if not EMAIL_REGEX.match(email):
        return False, "Invalid email format."
    return True, email.lower()

def validate_blood_group(blood_group):
    """Validates blood group against ABO/Rh standard."""
    if not blood_group or not isinstance(blood_group, str):
        return False, "Blood group is required."
    bg = blood_group.strip().upper()
    if bg not in VALID_BLOOD_GROUPS:
        return False, f"Invalid blood group '{bg}'. Must be one of: {', '.join(VALID_BLOOD_GROUPS)}."
    return True, bg

def validate_role(role):
    """Validates user authorization role."""
    if not role or not isinstance(role, str):
        return False, "Role is required."
    r = role.strip().lower()
    if r not in ("donor", "patient", "admin"):
        return False, f"Invalid role '{role}'. Must be donor, patient, or admin."
    return True, r

def validate_donor_status(status):
    """Validates donor 6-month lifecycle status."""
    if not status or not isinstance(status, str):
        return False, "Status is required."
    s = status.strip().upper()
    if s not in VALID_DONOR_STATUSES:
        return False, f"Invalid status '{s}'. Must be one of: {', '.join(VALID_DONOR_STATUSES)}."
    return True, s

def validate_availability_type(avail):
    """Validates availability pattern."""
    if not avail or not isinstance(avail, str):
        return True, "24_HOURS"
    a = avail.strip().upper()
    if a not in VALID_AVAILABILITIES:
        return False, f"Invalid availability pattern '{a}'."
    return True, a

def validate_positive_distance(distance):
    """Validates maximum travel distance / search radius."""
    try:
        d = float(distance)
        if d <= 0 or d > 500:
            return False, "Distance must be a positive number between 0.1 and 500 km."
        return True, round(d, 2)
    except (ValueError, TypeError):
        return False, "Distance must be a valid numeric value."

def validate_positive_units(units):
    """Validates required units of blood."""
    try:
        u = int(units)
        if u <= 0 or u > 50:
            return False, "Units must be an integer between 1 and 50."
        return True, u
    except (ValueError, TypeError):
        return False, "Units must be a valid integer."

# ============================================================================
# USERS CRUD & AUTHENTICATION
# ============================================================================

def create_user(full_name, email, password, role="donor", phone=None, db=None):
    """Creates a new user record with password hashing and validation."""
    conn = db or get_db()
    if not full_name or not full_name.strip():
        raise ValueError("Full name is required.")
        
    ok, email_clean = validate_email(email)
    if not ok:
        raise ValueError(email_clean)
        
    ok, role_clean = validate_role(role)
    if not ok:
        raise ValueError(role_clean)
        
    if not password or len(password) < 6:
        raise ValueError("Password must be at least 6 characters long.")
        
    # Check duplicate email
    existing = query_db("SELECT id FROM users WHERE email = ?", (email_clean,), one=True, db=conn)
    if existing:
        raise ValueError(f"Email '{email_clean}' is already registered.")
        
    password_hash = generate_password_hash(password)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    user_id, _ = execute_db(
        """INSERT INTO users (full_name, email, phone, password_hash, role, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (full_name.strip(), email_clean, (phone or "").strip(), password_hash, role_clean, now, now),
        db=conn
    )
    return get_user_by_id(user_id, db=conn)

def get_user_by_id(user_id, db=None):
    """Fetches user by primary key ID."""
    conn = db or get_db()
    return query_db(
        "SELECT id, user_id, full_name, name, email, phone, password_hash, role, created_at, updated_at FROM users WHERE id = ?",
        (user_id,),
        one=True,
        db=conn
    )

def get_user_by_email(email, db=None):
    """Fetches user by unique email."""
    conn = db or get_db()
    if not email:
        return None
    return query_db(
        "SELECT id, user_id, full_name, name, email, phone, password_hash, role, created_at, updated_at FROM users WHERE email = ?",
        (email.strip().lower(),),
        one=True,
        db=conn
    )

def authenticate_user(email, password, db=None):
    """Verifies user credentials and returns user record if valid."""
    user = get_user_by_email(email, db=db)
    if not user:
        return None
    if check_password_hash(user["password_hash"], password):
        return user
    return None

def update_user(user_id, full_name=None, phone=None, password=None, role=None, db=None):
    """Updates user information."""
    conn = db or get_db()
    user = get_user_by_id(user_id, db=conn)
    if not user:
        raise ValueError(f"User #{user_id} not found.")
        
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    pw_hash = generate_password_hash(password) if password else None
    
    execute_db(
        """UPDATE users 
           SET full_name = COALESCE(NULLIF(?, ''), full_name),
               phone = COALESCE(?, phone),
               password_hash = COALESCE(?, password_hash),
               role = COALESCE(NULLIF(?, ''), role),
               updated_at = ?
           WHERE id = ?""",
        (full_name, phone, pw_hash, role, now, user_id),
        db=conn
    )
    return get_user_by_id(user_id, db=conn)

def delete_user(user_id, db=None):
    """Deletes user (cascades to donor/patient profiles)."""
    conn = db or get_db()
    _, count = execute_db("DELETE FROM users WHERE id = ?", (user_id,), db=conn)
    return count > 0

# ============================================================================
# DONORS CRUD
# ============================================================================

def create_donor(user_id, blood_group, location, phone=None, latitude=None, longitude=None,
                 availability_type="24_HOURS", max_distance_km=15.0, status="ACTIVE",
                 last_verified_date=None, next_verification_date=None, db=None):
    """Creates a new donor profile."""
    conn = db or get_db()
    
    # Verify user exists
    user = get_user_by_id(user_id, db=conn)
    if not user:
        raise ValueError(f"User #{user_id} does not exist.")
        
    ok, bg_clean = validate_blood_group(blood_group)
    if not ok:
        raise ValueError(bg_clean)
        
    ok, dist_clean = validate_positive_distance(max_distance_km)
    if not ok:
        raise ValueError(dist_clean)
        
    ok, avail_clean = validate_availability_type(availability_type)
    if not ok:
        raise ValueError(avail_clean)
        
    ok, status_clean = validate_donor_status(status)
    if not ok:
        raise ValueError(status_clean)
        
    now = datetime.datetime.now(datetime.timezone.utc)
    now_iso = now.isoformat()
    last_v = last_verified_date or now_iso
    next_v = next_verification_date or (now + datetime.timedelta(days=Config.VERIFICATION_INTERVAL_DAYS)).isoformat()
    donor_phone = phone if phone is not None else (user.get("phone") or "")
    
    donor_id, _ = execute_db(
        """INSERT INTO donor_profiles 
           (user_id, blood_group, phone, location, latitude, longitude, availability, maximum_travel_distance, profile_status, last_verified_date, next_verification_date, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, bg_clean, donor_phone, location or "", latitude, longitude, avail_clean, dist_clean, status_clean, last_v, next_v, now_iso, now_iso),
        db=conn
    )
    
    # Log initial verification entry
    log_donor_verification(donor_id, last_v, status=status_clean, db=conn)
    return get_donor_by_id(donor_id, db=conn)

def get_donor_by_id(donor_id, db=None):
    """Fetches donor by primary key."""
    conn = db or get_db()
    return query_db("SELECT * FROM donor_profiles WHERE id = ?", (donor_id,), one=True, db=conn)

def get_donor_by_user_id(user_id, db=None):
    """Fetches donor by associated user_id."""
    conn = db or get_db()
    return query_db("SELECT * FROM donor_profiles WHERE user_id = ?", (user_id,), one=True, db=conn)

def update_donor(donor_id, blood_group=None, phone=None, location=None, latitude=None, longitude=None,
                 availability_type=None, max_distance_km=None, status=None,
                 last_verified_date=None, next_verification_date=None, db=None):
    """Updates donor profile."""
    conn = db or get_db()
    if blood_group:
        ok, bg = validate_blood_group(blood_group)
        if not ok:
            raise ValueError(bg)
        blood_group = bg
        
    if max_distance_km is not None:
        ok, d = validate_positive_distance(max_distance_km)
        if not ok:
            raise ValueError(d)
        max_distance_km = d
        
    if availability_type:
        ok, a = validate_availability_type(availability_type)
        if not ok:
            raise ValueError(a)
        availability_type = a
        
    if status:
        ok, s = validate_donor_status(status)
        if not ok:
            raise ValueError(s)
        status = s
        
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    execute_db(
        """UPDATE donor_profiles 
           SET blood_group = COALESCE(NULLIF(?, ''), blood_group),
               phone = COALESCE(?, phone),
               location = COALESCE(NULLIF(?, ''), location),
               latitude = COALESCE(?, latitude),
               longitude = COALESCE(?, longitude),
               availability = COALESCE(NULLIF(?, ''), availability),
               maximum_travel_distance = COALESCE(?, maximum_travel_distance),
               profile_status = COALESCE(NULLIF(?, ''), profile_status),
               last_verified_date = COALESCE(NULLIF(?, ''), last_verified_date),
               next_verification_date = COALESCE(NULLIF(?, ''), next_verification_date),
               updated_at = ?
           WHERE id = ?""",
        (blood_group, phone, location, latitude, longitude, availability_type, max_distance_km, status, last_verified_date, next_verification_date, now, donor_id),
        db=conn
    )
    return get_donor_by_id(donor_id, db=conn)

# ============================================================================
# BLOOD REQUESTS CRUD
# ============================================================================

def create_blood_request(patient_id, blood_group, hospital_name, location=None,
                         units_required=1, latitude=None, longitude=None,
                         preferred_max_distance=25.0, urgency="NORMAL",
                         required_time=None, availability_preference="ANY",
                         sort_preference="DISTANCE", db=None):
    """Creates a new patient requirement blood request."""
    conn = db or get_db()
    
    # Check patient exists
    patient = get_user_by_id(patient_id, db=conn)
    if not patient:
        raise ValueError(f"Patient user #{patient_id} does not exist.")
        
    ok, bg_clean = validate_blood_group(blood_group)
    if not ok:
        raise ValueError(bg_clean)
        
    if not hospital_name or not hospital_name.strip():
        raise ValueError("Hospital name is required.")
        
    ok, units_clean = validate_positive_units(units_required)
    if not ok:
        raise ValueError(units_clean)
        
    ok, dist_clean = validate_positive_distance(preferred_max_distance)
    if not ok:
        raise ValueError(dist_clean)
        
    urg = (urgency or "NORMAL").strip().upper()
    if urg not in VALID_URGENCIES:
        urg = "NORMAL"
        
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    req_time = required_time or now
    
    req_id, _ = execute_db(
        """INSERT INTO blood_requests 
           (patient_id, required_blood_group, required_units, hospital_name, location, latitude, longitude, preferred_max_distance, required_date_time, urgency, availability_preference, sort_preference, request_status, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?)""",
        (patient_id, bg_clean, units_clean, hospital_name.strip(), location or hospital_name.strip(), latitude, longitude, dist_clean, req_time, urg, availability_preference, sort_preference, now, now),
        db=conn
    )
    return get_blood_request_by_id(req_id, db=conn)

def get_blood_request_by_id(request_id, db=None):
    """Fetches blood request by primary key ID."""
    conn = db or get_db()
    return query_db("SELECT * FROM blood_requests WHERE id = ?", (request_id,), one=True, db=conn)

def update_blood_request_status(request_id, status, db=None):
    """Updates blood request lifecycle status (OPEN, MATCHING, FULFILLED, CANCELLED)."""
    conn = db or get_db()
    s = (status or "").strip().upper()
    if s not in VALID_REQUEST_STATUSES:
        raise ValueError(f"Invalid request status '{status}'.")
        
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    execute_db(
        "UPDATE blood_requests SET request_status = ?, updated_at = ? WHERE id = ?",
        (s, now, request_id),
        db=conn
    )
    return get_blood_request_by_id(request_id, db=conn)

# ============================================================================
# DONOR VERIFICATIONS CRUD
# ============================================================================

def log_donor_verification(donor_id, verification_date=None, phone_confirmed=1,
                           address_confirmed=1, availability_confirmed=1,
                           travel_distance_confirmed=1, status="ACTIVE", db=None):
    """Logs a 6-month verification audit checkpoint entry."""
    conn = db or get_db()
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    v_date = verification_date or now_iso
    
    vid, _ = execute_db(
        """INSERT INTO donor_verifications 
           (donor_id, verification_date, phone_confirmed, address_confirmed, availability_confirmed, travel_distance_confirmed, status, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (donor_id, v_date, 1 if phone_confirmed else 0, 1 if address_confirmed else 0,
         1 if availability_confirmed else 0, 1 if travel_distance_confirmed else 0, status, now_iso),
        db=conn
    )
    return query_db("SELECT * FROM donor_verifications WHERE id = ?", (vid,), one=True, db=conn)

def get_donor_verification_history(donor_id, db=None):
    """Retrieves all verification audit logs for a donor."""
    conn = db or get_db()
    return query_db("SELECT * FROM donor_verifications WHERE donor_id = ? ORDER BY verification_date DESC", (donor_id,), db=conn)

# ============================================================================
# REQUEST RESPONSES CRUD
# ============================================================================

def create_request_response(request_id, donor_id, response="PENDING", message=None, db=None):
    """Creates a dispatch response invitation record."""
    conn = db or get_db()
    resp_clean = (response or "PENDING").strip().upper()
    if resp_clean not in VALID_RESPONSE_STATUSES:
        raise ValueError(f"Invalid response status '{response}'.")
        
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    resp_id, _ = execute_db(
        """INSERT INTO donor_request_responses (blood_request_id, donor_id, status, message, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (request_id, donor_id, resp_clean, message, now, now),
        db=conn
    )
    return query_db("SELECT * FROM donor_request_responses WHERE id = ?", (resp_id,), one=True, db=conn)

def update_request_response(response_id, response, message=None, db=None):
    """Updates donor response status (ACCEPTED, REJECTED, CANCELLED)."""
    conn = db or get_db()
    resp_clean = (response or "").strip().upper()
    if resp_clean not in VALID_RESPONSE_STATUSES:
        raise ValueError(f"Invalid response status '{response}'.")
        
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    execute_db(
        """UPDATE donor_request_responses 
           SET status = ?, message = COALESCE(?, message), response_time = ?, updated_at = ?
           WHERE id = ?""",
        (resp_clean, message, now, now, response_id),
        db=conn
    )
    return query_db("SELECT * FROM donor_request_responses WHERE id = ?", (response_id,), one=True, db=conn)

# ============================================================================
# DONATION RECORDS CRUD
# ============================================================================

def create_donation_record(donor_id, blood_centre, request_id=None,
                           donation_date=None, component="WHOLE_BLOOD",
                           status="COMPLETED", db=None):
    """Creates a verified completed donation record."""
    conn = db or get_db()
    
    donor = get_donor_by_id(donor_id, db=conn)
    if not donor:
        raise ValueError(f"Donor #{donor_id} not found.")
        
    if not blood_centre or not blood_centre.strip():
        raise ValueError("Blood centre name is required.")
        
    comp = (component or "WHOLE_BLOOD").strip().upper()
    if comp not in VALID_COMPONENTS:
        raise ValueError(f"Invalid component '{component}'. Must be one of: {', '.join(VALID_COMPONENTS)}.")
        
    stat = (status or "COMPLETED").strip().upper()
    if stat not in VALID_DONATION_STATUSES:
        raise ValueError(f"Invalid donation status '{status}'. Must be one of: {', '.join(VALID_DONATION_STATUSES)}.")
        
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    d_date = donation_date or now
    
    don_id, _ = execute_db(
        """INSERT INTO donation_records 
           (donor_id, request_id, blood_centre, donation_date, component, status, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (donor_id, request_id, blood_centre.strip(), d_date, comp, stat, now, now),
        db=conn
    )
    return query_db("SELECT * FROM donation_records WHERE id = ?", (don_id,), one=True, db=conn)

def get_donation_records_by_donor(donor_id, db=None):
    """Retrieves all donation records for a specific donor."""
    conn = db or get_db()
    return query_db("SELECT * FROM donation_records WHERE donor_id = ? ORDER BY donation_date DESC", (donor_id,), db=conn)

def get_donation_records_by_request(request_id, db=None):
    """Retrieves donation records linked to a blood request."""
    conn = db or get_db()
    return query_db("SELECT * FROM donation_records WHERE request_id = ? ORDER BY donation_date DESC", (request_id,), db=conn)
