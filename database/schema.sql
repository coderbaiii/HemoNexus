-- ====================================================================
-- HEMONEXAS: Smart Blood Donor Management and Matching System
-- SQLite Relational Database DDL Schema
-- ====================================================================

-- 1. Users Table (Core authentication entity)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('donor', 'patient', 'admin')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 2. Donor Profiles Table (Donor management, location & availability)
CREATE TABLE IF NOT EXISTS donor_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    blood_group TEXT NOT NULL CHECK(blood_group IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')),
    phone TEXT NOT NULL,
    location TEXT NOT NULL,
    latitude REAL,
    longitude REAL,
    availability TEXT NOT NULL DEFAULT '24_HOURS',
    available_from TEXT DEFAULT '00:00',
    available_to TEXT DEFAULT '23:59',
    maximum_travel_distance REAL NOT NULL DEFAULT 15.0,
    is_available INTEGER NOT NULL DEFAULT 1, -- 1 = Available, 0 = Temporarily Unavailable
    profile_status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(profile_status IN ('ACTIVE', 'VERIFICATION_DUE', 'INACTIVE')),
    last_verified_date TEXT NOT NULL DEFAULT (datetime('now')),
    next_verification_date TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 3. Patient Profiles Table
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

-- 4. Blood Requests Table
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
    sorting_preference TEXT NOT NULL DEFAULT 'BEST_MATCH' CHECK(sorting_preference IN ('NEAREST', 'FASTEST', 'RECENTLY_VERIFIED', 'BEST_MATCH')),
    availability_preference TEXT NOT NULL DEFAULT 'ANY',
    request_status TEXT NOT NULL DEFAULT 'OPEN' CHECK(request_status IN ('OPEN', 'MATCHING', 'FULFILLED', 'CANCELLED')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 5. Donor Request Responses Table (Patient -> Donor workflow)
CREATE TABLE IF NOT EXISTS donor_request_responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    blood_request_id INTEGER NOT NULL REFERENCES blood_requests(id) ON DELETE CASCADE,
    donor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'ACCEPTED', 'REJECTED', 'CANCELLED', 'COMPLETED')),
    response_time TEXT,
    message TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(blood_request_id, donor_id)
);

-- 6. Donor Verification History Table (Tracks 6-month cycle renewals)
CREATE TABLE IF NOT EXISTS donor_verifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    donor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    verification_date TEXT NOT NULL DEFAULT (datetime('now')),
    status_before TEXT NOT NULL,
    status_after TEXT NOT NULL,
    remarks TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 7. Donation Records Table (Official blood centre completion records)
CREATE TABLE IF NOT EXISTS donation_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    blood_request_id INTEGER REFERENCES blood_requests(id) ON DELETE SET NULL,
    donor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    patient_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    donation_date TEXT NOT NULL DEFAULT (datetime('now')),
    blood_center_name TEXT NOT NULL,
    units_donated INTEGER NOT NULL DEFAULT 1,
    verification_notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 8. Notifications Table (In-app alerts)
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'INFO', -- 'INFO', 'REQUEST', 'VERIFICATION', 'SUCCESS', 'WARNING'
    is_read INTEGER NOT NULL DEFAULT 0,
    link TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 9. Audit Logs Table (Admin traceability)
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    details TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_donor_user ON donor_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_donor_blood_status ON donor_profiles(blood_group, profile_status);
CREATE INDEX IF NOT EXISTS idx_donor_available ON donor_profiles(is_available);
CREATE INDEX IF NOT EXISTS idx_patient_user ON patient_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_blood_requests_patient ON blood_requests(patient_id);
CREATE INDEX IF NOT EXISTS idx_blood_requests_status ON blood_requests(request_status);
CREATE INDEX IF NOT EXISTS idx_responses_req_donor ON donor_request_responses(blood_request_id, donor_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user_unread ON notifications(user_id, is_read);
