import sys
from pathlib import Path

# Add project root to sys.path for direct script execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3
import datetime
from werkzeug.security import generate_password_hash
from backend.config import Config
from backend.database import get_db

SCHEMA_SQL = """
-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('donor', 'patient', 'admin')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Donor profiles table
CREATE TABLE IF NOT EXISTS donor_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    blood_group TEXT NOT NULL CHECK(blood_group IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')),
    phone TEXT NOT NULL,
    location TEXT NOT NULL,
    latitude REAL,
    longitude REAL,
    availability TEXT NOT NULL DEFAULT '24_HOURS' CHECK(availability IN ('24_HOURS', '8_HOURS', 'DAYTIME', 'NIGHTTIME')),
    maximum_travel_distance REAL NOT NULL DEFAULT 15.0,
    profile_status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(profile_status IN ('ACTIVE', 'VERIFICATION_DUE', 'INACTIVE')),
    last_verified_date TEXT NOT NULL DEFAULT (datetime('now')),
    next_verification_date TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Patient profiles table
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

-- Blood requests table
CREATE TABLE IF NOT EXISTS blood_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    required_blood_group TEXT NOT NULL CHECK(required_blood_group IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')),
    required_units INTEGER NOT NULL DEFAULT 1,
    hospital_name TEXT NOT NULL,
    location TEXT NOT NULL,
    latitude REAL,
    longitude REAL,
    preferred_max_distance REAL NOT NULL DEFAULT 25.0,
    required_date_time TEXT NOT NULL DEFAULT (datetime('now')),
    urgency TEXT NOT NULL DEFAULT 'NORMAL' CHECK(urgency IN ('LOW', 'NORMAL', 'URGENT', 'CRITICAL')),
    request_status TEXT NOT NULL DEFAULT 'OPEN' CHECK(request_status IN ('OPEN', 'MATCHING', 'FULFILLED', 'CANCELLED')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Donor request responses table
CREATE TABLE IF NOT EXISTS donor_request_responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    blood_request_id INTEGER NOT NULL REFERENCES blood_requests(id) ON DELETE CASCADE,
    donor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'ACCEPTED', 'REJECTED', 'CANCELLED')),
    response_time TEXT,
    message TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(blood_request_id, donor_id)
);

-- Audit logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    details TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_donor_user ON donor_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_donor_blood_status ON donor_profiles(blood_group, profile_status);
CREATE INDEX IF NOT EXISTS idx_patient_user ON patient_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_blood_requests_patient ON blood_requests(patient_id);
CREATE INDEX IF NOT EXISTS idx_blood_requests_status ON blood_requests(request_status);
CREATE INDEX IF NOT EXISTS idx_responses_req_donor ON donor_request_responses(blood_request_id, donor_id);
"""

def init_database(db_path=None, seed_demo=True):
    """
    Initializes the database schema and seeds initial admin & demo accounts.
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
    """Seed administrator and demo donors/patients if not already present."""
    cur = conn.cursor()
    now = datetime.datetime.now(datetime.timezone.utc)
    now_iso = now.isoformat()
    future_6mo = (now + datetime.timedelta(days=180)).isoformat()
    past_7mo = (now - datetime.timedelta(days=210)).isoformat()
    past_10mo = (now - datetime.timedelta(days=300)).isoformat()

    # 1. Admin account
    cur.execute("SELECT id FROM users WHERE email = ?", ("admin@hemonexus.org",))
    if not cur.fetchone():
        admin_pass = generate_password_hash("Admin@123456")
        cur.execute(
            "INSERT INTO users (full_name, email, password_hash, role, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("System Administrator", "admin@hemonexus.org", admin_pass, "admin", now_iso, now_iso)
        )
        admin_id = cur.lastrowid
        cur.execute(
            "INSERT INTO audit_logs (user_id, action, details) VALUES (?, ?, ?)",
            (admin_id, "INIT_ADMIN", "Created default admin account")
        )

    # 2. Demo Patient
    cur.execute("SELECT id FROM users WHERE email = ?", ("patient.raj@example.com",))
    patient_row = cur.fetchone()
    if not patient_row:
        p_pass = generate_password_hash("Patient@1234")
        cur.execute(
            "INSERT INTO users (full_name, email, password_hash, role, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("Rajesh Kumar", "patient.raj@example.com", p_pass, "patient", now_iso, now_iso)
        )
        patient_id = cur.lastrowid
        cur.execute(
            "INSERT INTO patient_profiles (user_id, phone, location, latitude, longitude, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (patient_id, "+91 98765 43210", "Apollo Multispecialty Hospital, Kolkata", 22.5697, 88.4046, now_iso, now_iso)
        )
        
        # Sample blood request
        cur.execute(
            """INSERT INTO blood_requests 
               (patient_id, required_blood_group, required_units, hospital_name, location, latitude, longitude, preferred_max_distance, required_date_time, urgency, request_status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (patient_id, "O+", 2, "Apollo Hospital", "Canal Circular Rd, EM Bypass, Kolkata", 22.5697, 88.4046, 20.0, now_iso, "URGENT", "OPEN", now_iso, now_iso)
        )

    # 3. Demo Donors (Covering ACTIVE, VERIFICATION_DUE, and INACTIVE lifecycle)
    demo_donors = [
        # Active Donor 1: O+ nearby (Salt Lake Sector 5, 2.5 km away)
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
        # Active Donor 2: O+ moderately near (Park Circus, 5 km away)
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
        # Donor 3: A+ donor (different blood group)
        {
            "name": "Subhashish Bose",
            "email": "subhashish.donor@example.com",
            "phone": "+91 98322 33445",
            "blood": "A+",
            "loc": "New Town, Kolkata",
            "lat": 22.5937,
            "lon": 88.4798,
            "avail": "24_HOURS",
            "dist": 20.0,
            "status": "ACTIVE",
            "last_v": now_iso,
            "next_v": future_6mo
        },
        # Donor 4: O+ donor due for verification (next verification was 10 days ago)
        {
            "name": "Devratna Mitra",
            "email": "devratna.donor@example.com",
            "phone": "+91 98333 44556",
            "blood": "O+",
            "loc": "Howrah Station Road",
            "lat": 22.5857,
            "lon": 88.3426,
            "avail": "8_HOURS",
            "dist": 15.0,
            "status": "VERIFICATION_DUE",
            "last_v": past_7mo,
            "next_v": (now - datetime.timedelta(days=10)).isoformat()
        },
        # Donor 5: Inactive donor (grace period expired, unverified for 10 months)
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

    for d in demo_donors:
        cur.execute("SELECT id FROM users WHERE email = ?", (d["email"],))
        if not cur.fetchone():
            d_pass = generate_password_hash("Donor@1234")
            cur.execute(
                "INSERT INTO users (full_name, email, password_hash, role, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (d["name"], d["email"], d_pass, "donor", now_iso, now_iso)
            )
            d_user_id = cur.lastrowid
            cur.execute(
                """INSERT INTO donor_profiles 
                   (user_id, blood_group, phone, location, latitude, longitude, availability, maximum_travel_distance, profile_status, last_verified_date, next_verification_date, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (d_user_id, d["blood"], d["phone"], d["loc"], d["lat"], d["lon"], d["avail"], d["dist"], d["status"], d["last_v"], d["next_v"], now_iso, now_iso)
            )

    conn.commit()

if __name__ == "__main__":
    init_database()
