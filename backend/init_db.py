"""
HEMONEXAS — Database Initialization & Schema Definition
Member 4 Responsibility: Database Design, Schema Implementation & Synthetic Test Data Seeding.
"""
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3
import datetime
from werkzeug.security import generate_password_hash
from backend.config import Config
from backend.database import get_db

SCHEMA_SQL = """
-- ============================================================================
-- 1. USERS TABLE
-- Authentication, identity, and role-based access control.
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER GENERATED ALWAYS AS (id) VIRTUAL,
    full_name TEXT NOT NULL,
    name TEXT GENERATED ALWAYS AS (full_name) VIRTUAL,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    phone TEXT,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('donor', 'patient', 'admin', 'DONOR', 'PATIENT', 'ADMIN')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================================
-- 2. DONOR PROFILES / DONORS TABLE
-- Stores blood group, GPS coordinates, availability schedule, and 6-month verification state.
-- ============================================================================
CREATE TABLE IF NOT EXISTS donor_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    donor_id INTEGER GENERATED ALWAYS AS (id) VIRTUAL,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    blood_group TEXT NOT NULL CHECK(blood_group IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')),
    phone TEXT,
    location TEXT NOT NULL,
    address TEXT GENERATED ALWAYS AS (location) VIRTUAL,
    latitude REAL,
    longitude REAL,
    availability TEXT NOT NULL DEFAULT '24_HOURS' CHECK(availability IN ('24_HOURS', '8_HOURS', 'DAY', 'NIGHT', 'DAYTIME', 'NIGHTTIME')),
    availability_type TEXT GENERATED ALWAYS AS (availability) VIRTUAL,
    available_from TEXT DEFAULT '00:00',
    available_to TEXT DEFAULT '23:59',
    maximum_travel_distance REAL NOT NULL DEFAULT 15.0 CHECK(maximum_travel_distance > 0),
    max_distance_km REAL GENERATED ALWAYS AS (maximum_travel_distance) VIRTUAL,
    profile_status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(profile_status IN ('ACTIVE', 'VERIFICATION_DUE', 'INACTIVE', 'TEMPORARILY_UNAVAILABLE')),
    status TEXT GENERATED ALWAYS AS (profile_status) VIRTUAL,
    last_verified_date TEXT NOT NULL DEFAULT (datetime('now')),
    next_verification_date TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================================
-- 3. PATIENT PROFILES TABLE
-- Stores patient contact & default hospital location.
-- ============================================================================
CREATE TABLE IF NOT EXISTS patient_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    phone TEXT,
    location TEXT,
    latitude REAL,
    longitude REAL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================================
-- 4. BLOOD REQUESTS TABLE
-- Patient/hospital emergency requirements, location, search radius & preferences.
-- ============================================================================
CREATE TABLE IF NOT EXISTS blood_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id INTEGER GENERATED ALWAYS AS (id) VIRTUAL,
    patient_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    required_blood_group TEXT NOT NULL CHECK(required_blood_group IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')),
    blood_group TEXT GENERATED ALWAYS AS (required_blood_group) VIRTUAL,
    required_units INTEGER NOT NULL DEFAULT 1 CHECK(required_units > 0),
    units_required INTEGER GENERATED ALWAYS AS (required_units) VIRTUAL,
    hospital_name TEXT NOT NULL,
    location TEXT NOT NULL,
    latitude REAL,
    longitude REAL,
    preferred_max_distance REAL NOT NULL DEFAULT 25.0 CHECK(preferred_max_distance > 0),
    max_distance_km REAL GENERATED ALWAYS AS (preferred_max_distance) VIRTUAL,
    required_date_time TEXT NOT NULL DEFAULT (datetime('now')),
    required_time TEXT GENERATED ALWAYS AS (required_date_time) VIRTUAL,
    urgency TEXT NOT NULL DEFAULT 'NORMAL' CHECK(urgency IN ('LOW', 'NORMAL', 'URGENT', 'CRITICAL')),
    availability_preference TEXT NOT NULL DEFAULT 'ANY' CHECK(availability_preference IN ('ANY', '24_HOURS', '8_HOURS', 'DAY', 'NIGHT', 'DAYTIME', 'NIGHTTIME')),
    sort_preference TEXT NOT NULL DEFAULT 'DISTANCE' CHECK(sort_preference IN ('DISTANCE', 'VERIFICATION_SCORE', 'COMBINED')),
    request_status TEXT NOT NULL DEFAULT 'OPEN' CHECK(request_status IN ('OPEN', 'MATCHING', 'FULFILLED', 'CANCELLED')),
    status TEXT GENERATED ALWAYS AS (request_status) VIRTUAL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================================
-- 5. DONOR VERIFICATIONS TABLE
-- Audit history of 6-month verification cycles and confirmation checkpoints.
-- ============================================================================
CREATE TABLE IF NOT EXISTS donor_verifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    verification_id INTEGER GENERATED ALWAYS AS (id) VIRTUAL,
    donor_id INTEGER NOT NULL REFERENCES donor_profiles(id) ON DELETE CASCADE,
    verification_date TEXT NOT NULL DEFAULT (datetime('now')),
    phone_confirmed INTEGER NOT NULL DEFAULT 1 CHECK(phone_confirmed IN (0, 1)),
    address_confirmed INTEGER NOT NULL DEFAULT 1 CHECK(address_confirmed IN (0, 1)),
    availability_confirmed INTEGER NOT NULL DEFAULT 1 CHECK(availability_confirmed IN (0, 1)),
    travel_distance_confirmed INTEGER NOT NULL DEFAULT 1 CHECK(travel_distance_confirmed IN (0, 1)),
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE', 'VERIFICATION_DUE', 'INACTIVE', 'TEMPORARILY_UNAVAILABLE')),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================================
-- 6. DONOR REQUEST RESPONSES TABLE
-- Tracks donor responses to blood request dispatch invitations.
-- ============================================================================
CREATE TABLE IF NOT EXISTS donor_request_responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    response_id INTEGER GENERATED ALWAYS AS (id) VIRTUAL,
    blood_request_id INTEGER NOT NULL REFERENCES blood_requests(id) ON DELETE CASCADE,
    request_id INTEGER GENERATED ALWAYS AS (blood_request_id) VIRTUAL,
    donor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'ACCEPTED', 'REJECTED', 'CANCELLED')),
    response TEXT GENERATED ALWAYS AS (status) VIRTUAL,
    message TEXT,
    response_time TEXT,
    responded_at TEXT GENERATED ALWAYS AS (response_time) VIRTUAL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(blood_request_id, donor_id)
);

-- ============================================================================
-- 7. DONATION RECORDS TABLE
-- Tracks completed blood donations verified by authorized blood bank staff.
-- ============================================================================
CREATE TABLE IF NOT EXISTS donation_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    donation_id INTEGER GENERATED ALWAYS AS (id) VIRTUAL,
    donor_id INTEGER NOT NULL REFERENCES donor_profiles(id) ON DELETE CASCADE,
    request_id INTEGER REFERENCES blood_requests(id) ON DELETE SET NULL,
    blood_centre TEXT NOT NULL,
    donation_date TEXT NOT NULL DEFAULT (datetime('now')),
    component TEXT NOT NULL DEFAULT 'WHOLE_BLOOD' CHECK(component IN ('WHOLE_BLOOD', 'RBC', 'PLATELETS', 'PLASMA')),
    status TEXT NOT NULL DEFAULT 'COMPLETED' CHECK(status IN ('COMPLETED', 'DISCARDED', 'TESTING_PENDING')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================================
-- 8. AUDIT LOGS TABLE
-- System activity and lifecycle transition audit trails.
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    details TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================================
-- COMPATIBILITY VIEWS & TRIGGERS
-- ============================================================================
CREATE VIEW IF NOT EXISTS donors AS
SELECT 
    id,
    id AS donor_id,
    user_id,
    blood_group,
    phone,
    location,
    location AS address,
    latitude,
    longitude,
    availability,
    availability AS availability_type,
    available_from,
    available_to,
    maximum_travel_distance,
    maximum_travel_distance AS max_distance_km,
    profile_status,
    profile_status AS status,
    last_verified_date,
    next_verification_date,
    created_at,
    updated_at
FROM donor_profiles;

CREATE VIEW IF NOT EXISTS request_responses AS
SELECT 
    id,
    id AS response_id,
    blood_request_id,
    blood_request_id AS request_id,
    donor_id,
    status,
    status AS response,
    message,
    response_time,
    response_time AS responded_at,
    created_at,
    updated_at
FROM donor_request_responses;

CREATE TRIGGER IF NOT EXISTS trg_donors_insert
INSTEAD OF INSERT ON donors
BEGIN
    INSERT INTO donor_profiles (
        user_id, blood_group, phone, location, latitude, longitude,
        availability, maximum_travel_distance, profile_status,
        last_verified_date, next_verification_date, created_at, updated_at
    ) VALUES (
        NEW.user_id, NEW.blood_group, COALESCE(NEW.phone, ''), NEW.location, NEW.latitude, NEW.longitude,
        COALESCE(NEW.availability_type, NEW.availability, '24_HOURS'),
        COALESCE(NEW.max_distance_km, NEW.maximum_travel_distance, 15.0),
        COALESCE(NEW.status, NEW.profile_status, 'ACTIVE'),
        NEW.last_verified_date, NEW.next_verification_date,
        COALESCE(NEW.created_at, datetime('now')), COALESCE(NEW.updated_at, datetime('now'))
    );
END;

CREATE TRIGGER IF NOT EXISTS trg_donors_update
INSTEAD OF UPDATE ON donors
BEGIN
    UPDATE donor_profiles SET
        blood_group = COALESCE(NEW.blood_group, blood_group),
        phone = COALESCE(NEW.phone, phone),
        location = COALESCE(NEW.location, location),
        latitude = COALESCE(NEW.latitude, latitude),
        longitude = COALESCE(NEW.longitude, longitude),
        availability = COALESCE(NEW.availability_type, NEW.availability, availability),
        maximum_travel_distance = COALESCE(NEW.max_distance_km, NEW.maximum_travel_distance, maximum_travel_distance),
        profile_status = COALESCE(NEW.status, NEW.profile_status, profile_status),
        last_verified_date = COALESCE(NEW.last_verified_date, last_verified_date),
        next_verification_date = COALESCE(NEW.next_verification_date, next_verification_date),
        updated_at = COALESCE(NEW.updated_at, datetime('now'))
    WHERE id = OLD.id OR user_id = OLD.user_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_request_responses_insert
INSTEAD OF INSERT ON request_responses
BEGIN
    INSERT INTO donor_request_responses (
        blood_request_id, donor_id, status, message, response_time, created_at, updated_at
    ) VALUES (
        COALESCE(NEW.request_id, NEW.blood_request_id), NEW.donor_id,
        COALESCE(NEW.response, NEW.status, 'PENDING'),
        NEW.message, COALESCE(NEW.responded_at, NEW.response_time),
        COALESCE(NEW.created_at, datetime('now')), COALESCE(NEW.updated_at, datetime('now'))
    );
END;

CREATE TRIGGER IF NOT EXISTS trg_request_responses_update
INSTEAD OF UPDATE ON request_responses
BEGIN
    UPDATE donor_request_responses SET
        status = COALESCE(NEW.response, NEW.status, status),
        message = COALESCE(NEW.message, message),
        response_time = COALESCE(NEW.responded_at, NEW.response_time, response_time),
        updated_at = COALESCE(NEW.updated_at, datetime('now'))
    WHERE id = OLD.id OR (blood_request_id = COALESCE(OLD.request_id, OLD.blood_request_id) AND donor_id = OLD.donor_id);
END;

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_donors_user ON donor_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_donors_blood_status ON donor_profiles(blood_group, profile_status);
CREATE INDEX IF NOT EXISTS idx_donors_status_dates ON donor_profiles(profile_status, next_verification_date);
CREATE INDEX IF NOT EXISTS idx_donors_location_coords ON donor_profiles(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_patient_user ON patient_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_blood_requests_patient ON blood_requests(patient_id);
CREATE INDEX IF NOT EXISTS idx_blood_requests_status ON blood_requests(request_status);
CREATE INDEX IF NOT EXISTS idx_blood_requests_blood ON blood_requests(required_blood_group, request_status);
CREATE INDEX IF NOT EXISTS idx_donor_verifications_donor ON donor_verifications(donor_id, verification_date);
CREATE INDEX IF NOT EXISTS idx_request_responses_req_donor ON donor_request_responses(blood_request_id, donor_id);
CREATE INDEX IF NOT EXISTS idx_donation_records_donor ON donation_records(donor_id, donation_date);
CREATE INDEX IF NOT EXISTS idx_donation_records_request ON donation_records(request_id);
"""

def init_database(db_path=None, seed_demo=True):
    """
    Initializes the SQLite database schema and seeds initial demo/test data.
    """
    conn = get_db(db_path)
    cur = conn.cursor()
    cur.executescript(SCHEMA_SQL)
    conn.commit()

    if seed_demo:
        seed_data(conn)

    cur.close()
    if db_path:
        conn.close()
    print("Database schema initialized successfully.")

def seed_data(conn):
    """
    Seed safe synthetic test data covering:
    - All 8 ABO/Rh blood groups (A+, A-, B+, B-, AB+, AB-, O+, O-)
    - Active donors, Verification Due donors, Inactive donors
    - Different availability patterns (24_HOURS, 8_HOURS, DAY, NIGHT)
    - Multiple locations & travel radii in Kolkata metropolitan area
    - Multiple patient requests with different urgencies
    - 6-Month verification logs
    - Request responses & donation records
    """
    cur = conn.cursor()
    now = datetime.datetime.now(datetime.timezone.utc)
    now_iso = now.isoformat()
    future_6mo = (now + datetime.timedelta(days=180)).isoformat()
    past_7mo = (now - datetime.timedelta(days=210)).isoformat()
    past_10mo = (now - datetime.timedelta(days=300)).isoformat()

    # 1. Admin Account
    cur.execute("SELECT id FROM users WHERE email = ?", ("admin@hemonexus.org",))
    if not cur.fetchone():
        admin_pass = generate_password_hash("Admin@123456")
        cur.execute(
            "INSERT INTO users (full_name, email, phone, password_hash, role, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("System Administrator", "admin@hemonexus.org", "+91 90000 00000", admin_pass, "admin", now_iso, now_iso)
        )
        admin_id = cur.lastrowid
        cur.execute(
            "INSERT INTO audit_logs (user_id, action, details) VALUES (?, ?, ?)",
            (admin_id, "INIT_ADMIN", "Created default admin account")
        )

    # 2. Synthetic Patients
    demo_patients = [
        {
            "name": "Rajesh Kumar",
            "email": "patient.raj@example.com",
            "phone": "+91 98765 43210",
            "loc": "Apollo Multispecialty Hospital, Kolkata",
            "lat": 22.5697,
            "lon": 88.4046,
            "req_blood": "O+",
            "units": 2,
            "urgency": "URGENT",
            "hospital": "Apollo Multispecialty Hospital",
            "max_dist": 25.0
        },
        {
            "name": "Sunita Mukherjee",
            "email": "sunita.patient@example.com",
            "phone": "+91 98765 11223",
            "loc": "AMRI Hospital, Salt Lake",
            "lat": 22.5852,
            "lon": 88.4124,
            "req_blood": "B+",
            "units": 1,
            "urgency": "CRITICAL",
            "hospital": "AMRI Hospital Salt Lake",
            "max_dist": 20.0
        },
        {
            "name": "Ananya Roy",
            "email": "ananya.patient@example.com",
            "phone": "+91 98765 99887",
            "loc": "Fortis Hospital, Anandapur",
            "lat": 22.5186,
            "lon": 88.4011,
            "req_blood": "AB-",
            "units": 1,
            "urgency": "NORMAL",
            "hospital": "Fortis Hospital Kolkata",
            "max_dist": 30.0
        }
    ]

    patient_ids = {}
    for p in demo_patients:
        cur.execute("SELECT id FROM users WHERE email = ?", (p["email"],))
        p_row = cur.fetchone()
        if not p_row:
            p_pass = generate_password_hash("Patient@1234")
            cur.execute(
                "INSERT INTO users (full_name, email, phone, password_hash, role, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (p["name"], p["email"], p["phone"], p_pass, "patient", now_iso, now_iso)
            )
            pid = cur.lastrowid
            cur.execute(
                "INSERT INTO patient_profiles (user_id, phone, location, latitude, longitude, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (pid, p["phone"], p["loc"], p["lat"], p["lon"], now_iso, now_iso)
            )
            cur.execute(
                """INSERT INTO blood_requests 
                   (patient_id, required_blood_group, required_units, hospital_name, location, latitude, longitude, preferred_max_distance, required_date_time, urgency, request_status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?)""",
                (pid, p["req_blood"], p["units"], p["hospital"], p["loc"], p["lat"], p["lon"], p["max_dist"], now_iso, p["urgency"], now_iso, now_iso)
            )
            patient_ids[p["email"]] = pid
        else:
            patient_ids[p["email"]] = p_row[0]

    # 3. Comprehensive Synthetic Donors across all blood groups & verification states
    demo_donors = [
        # Active O+ (Salt Lake Sector 5, 2.5 km from Apollo)
        {
            "name": "Amitav Sengupta",
            "email": "amitav.donor@example.com",
            "phone": "+91 98300 11223",
            "blood": "O+",
            "loc": "Sector 5, Salt Lake, Kolkata",
            "lat": 22.5805,
            "lon": 88.4344,
            "avail": "24_HOURS",
            "dist": 25.0,
            "status": "ACTIVE",
            "last_v": now_iso,
            "next_v": future_6mo
        },
        # Active O+ (Park Circus, 5 km away)
        {
            "name": "Priyanka Roy",
            "email": "priyanka.donor@example.com",
            "phone": "+91 98311 22334",
            "blood": "O+",
            "loc": "Park Circus, Kolkata",
            "lat": 22.5414,
            "lon": 88.3686,
            "avail": "DAYTIME",
            "dist": 15.0,
            "status": "ACTIVE",
            "last_v": now_iso,
            "next_v": future_6mo
        },
        # Active A+ (New Town, 6 km away)
        {
            "name": "Subhashish Bose",
            "email": "subhashish.donor@example.com",
            "phone": "+91 98322 33445",
            "blood": "A+",
            "loc": "New Town Action Area 1, Kolkata",
            "lat": 22.5937,
            "lon": 88.4798,
            "avail": "24_HOURS",
            "dist": 20.0,
            "status": "ACTIVE",
            "last_v": now_iso,
            "next_v": future_6mo
        },
        # Active B+ (Salt Lake Sector 1, 3 km from AMRI)
        {
            "name": "Debolina Banerjee",
            "email": "debolina.donor@example.com",
            "phone": "+91 98355 66778",
            "blood": "B+",
            "loc": "Sector 1, Salt Lake, Kolkata",
            "lat": 22.5910,
            "lon": 88.4110,
            "avail": "24_HOURS",
            "dist": 20.0,
            "status": "ACTIVE",
            "last_v": now_iso,
            "next_v": future_6mo
        },
        # Active AB- (Rare group donor, Anandapur)
        {
            "name": "Tanmay Dutta",
            "email": "tanmay.donor@example.com",
            "phone": "+91 98366 77889",
            "blood": "AB-",
            "loc": "Anandapur, Kolkata",
            "lat": 22.5200,
            "lon": 88.4050,
            "avail": "24_HOURS",
            "dist": 30.0,
            "status": "ACTIVE",
            "last_v": now_iso,
            "next_v": future_6mo
        },
        # Active A- donor
        {
            "name": "Rituparna Sen",
            "email": "rituparna.donor@example.com",
            "phone": "+91 98377 88990",
            "blood": "A-",
            "loc": "Gariahat, Kolkata",
            "lat": 22.5190,
            "lon": 88.3650,
            "avail": "DAYTIME",
            "dist": 15.0,
            "status": "ACTIVE",
            "last_v": now_iso,
            "next_v": future_6mo
        },
        # Active B- donor
        {
            "name": "Souvik Ghosh",
            "email": "souvik.donor@example.com",
            "phone": "+91 98388 99001",
            "blood": "B-",
            "loc": "Shyambazar, Kolkata",
            "lat": 22.6020,
            "lon": 88.3710,
            "avail": "8_HOURS",
            "dist": 15.0,
            "status": "ACTIVE",
            "last_v": now_iso,
            "next_v": future_6mo
        },
        # Active AB+ donor
        {
            "name": "Meghna Das",
            "email": "meghna.donor@example.com",
            "phone": "+91 98399 00112",
            "blood": "AB+",
            "loc": "Dum Dum, Kolkata",
            "lat": 22.6220,
            "lon": 88.4180,
            "avail": "24_HOURS",
            "dist": 20.0,
            "status": "ACTIVE",
            "last_v": now_iso,
            "next_v": future_6mo
        },
        # Active O- (Universal donor)
        {
            "name": "Kallol Chatterjee",
            "email": "kallol.donor@example.com",
            "phone": "+91 98400 11223",
            "blood": "O-",
            "loc": "Behala, Kolkata",
            "lat": 22.4980,
            "lon": 88.3180,
            "avail": "24_HOURS",
            "dist": 25.0,
            "status": "ACTIVE",
            "last_v": now_iso,
            "next_v": future_6mo
        },
        # Donor due for verification (10 days past 180d cycle, within grace window)
        {
            "name": "Devratna Mitra",
            "email": "devratna.donor@example.com",
            "phone": "+91 98333 44556",
            "blood": "O+",
            "loc": "Howrah Station Road, Howrah",
            "lat": 22.5857,
            "lon": 88.3426,
            "avail": "8_HOURS",
            "dist": 15.0,
            "status": "VERIFICATION_DUE",
            "last_v": past_7mo,
            "next_v": (now - datetime.timedelta(days=10)).isoformat()
        },
        # Inactive donor (grace period expired, unverified for 10 months -> excluded from matching)
        {
            "name": "Rohan Ganguly",
            "email": "rohan.donor@example.com",
            "phone": "+91 98344 55667",
            "blood": "O+",
            "loc": "Barasat, Kolkata",
            "lat": 22.7230,
            "lon": 88.4817,
            "avail": "24_HOURS",
            "dist": 10.0,
            "status": "INACTIVE",
            "last_v": past_10mo,
            "next_v": (now - datetime.timedelta(days=120)).isoformat()
        }
    ]

    donor_db_ids = {}
    donor_user_ids = {}
    for d in demo_donors:
        cur.execute("SELECT id FROM users WHERE email = ?", (d["email"],))
        u_row = cur.fetchone()
        if not u_row:
            d_pass = generate_password_hash("Donor@1234")
            cur.execute(
                "INSERT INTO users (full_name, email, phone, password_hash, role, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (d["name"], d["email"], d["phone"], d_pass, "donor", now_iso, now_iso)
            )
            d_user_id = cur.lastrowid
            cur.execute(
                """INSERT INTO donor_profiles 
                   (user_id, blood_group, phone, location, latitude, longitude, availability, maximum_travel_distance, profile_status, last_verified_date, next_verification_date, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (d_user_id, d["blood"], d["phone"], d["loc"], d["lat"], d["lon"], d["avail"], d["dist"], d["status"], d["last_v"], d["next_v"], now_iso, now_iso)
            )
            donor_id = cur.lastrowid
            donor_db_ids[d["email"]] = donor_id
            donor_user_ids[d["email"]] = d_user_id

            # Log initial verification history
            cur.execute(
                """INSERT INTO donor_verifications 
                   (donor_id, verification_date, phone_confirmed, address_confirmed, availability_confirmed, travel_distance_confirmed, status, created_at)
                   VALUES (?, ?, 1, 1, 1, 1, ?, ?)""",
                (donor_id, d["last_v"], d["status"], now_iso)
            )
        else:
            donor_user_ids[d["email"]] = u_row[0]
            cur.execute("SELECT id FROM donor_profiles WHERE user_id = ?", (u_row[0],))
            did_row = cur.fetchone()
            if did_row:
                donor_db_ids[d["email"]] = did_row[0]

    # 4. Seed a completed donation record for Amitav Sengupta
    if "amitav.donor@example.com" in donor_db_ids:
        amitav_donor_id = donor_db_ids["amitav.donor@example.com"]
        cur.execute("SELECT id FROM donation_records WHERE donor_id = ?", (amitav_donor_id,))
        if not cur.fetchone():
            cur.execute(
                """INSERT INTO donation_records 
                   (donor_id, request_id, blood_centre, donation_date, component, status, created_at, updated_at)
                   VALUES (?, NULL, ?, ?, 'WHOLE_BLOOD', 'COMPLETED', ?, ?)""",
                (amitav_donor_id, "Kolkata Central Blood Bank & Transfusion Center", (now - datetime.timedelta(days=95)).isoformat(), now_iso, now_iso)
            )

    conn.commit()

if __name__ == "__main__":
    init_database()
