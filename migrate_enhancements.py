"""
Database Migration for HemoNexus Major Feature Integration:
- family_members table
- ngo_profiles table
- ngo_contact_requests table
- blocked_users table
- users table extensions: profile_photo, address, city, support 'ngo' role
- performance indexes
"""
import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "hemonexus.db"

def run_migration(db_path=DB_PATH):
    print(f"Connecting to database at {db_path}...")
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON;")
    cur = conn.cursor()

    # 1. Update users table columns if missing
    cur.execute("PRAGMA table_info(users);")
    user_cols = [r[1] for r in cur.fetchall()]
    
    if "profile_photo" not in user_cols:
        print("Adding profile_photo to users...")
        cur.execute("ALTER TABLE users ADD COLUMN profile_photo TEXT DEFAULT NULL;")
    if "address" not in user_cols:
        print("Adding address to users...")
        cur.execute("ALTER TABLE users ADD COLUMN address TEXT DEFAULT NULL;")
    if "city" not in user_cols:
        print("Adding city to users...")
        cur.execute("ALTER TABLE users ADD COLUMN city TEXT DEFAULT 'Kolkata';")

    # Update role CHECK constraint on users table if needed
    # In SQLite, to alter CHECK constraints safely, we can recreate the table if 'ngo' isn't supported,
    # or ensure our insert/updates succeed. Let's check table sql.
    cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='users';")
    users_sql = cur.fetchone()[0]
    if "'ngo'" not in users_sql and "'NGO'" not in users_sql:
        print("Updating users table role constraint to support 'ngo'...")
        cur.execute("""
            CREATE TABLE users_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER GENERATED ALWAYS AS (id) VIRTUAL,
                full_name TEXT NOT NULL,
                name TEXT GENERATED ALWAYS AS (full_name) VIRTUAL,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                phone TEXT,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('donor', 'patient', 'admin', 'ngo', 'DONOR', 'PATIENT', 'ADMIN', 'NGO')),
                profile_photo TEXT DEFAULT NULL,
                address TEXT DEFAULT NULL,
                city TEXT DEFAULT 'Kolkata',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)
        cur.execute("""
            INSERT INTO users_new (id, full_name, email, phone, password_hash, role, profile_photo, address, city, created_at, updated_at)
            SELECT id, full_name, email, phone, password_hash, role, profile_photo, address, city, created_at, updated_at
            FROM users;
        """)
        cur.execute("DROP TABLE users;")
        cur.execute("ALTER TABLE users_new RENAME TO users;")

    # 2. Family Members Table
    print("Creating family_members table...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS family_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            full_name TEXT NOT NULL,
            relationship TEXT NOT NULL CHECK(relationship IN ('Father', 'Mother', 'Brother', 'Sister', 'Spouse', 'Child', 'Other')),
            blood_group TEXT NOT NULL CHECK(blood_group IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')),
            age INTEGER CHECK(age > 0 AND age < 130),
            contact_number TEXT,
            medical_notes TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)

    # 3. NGO Profiles Table
    print("Creating ngo_profiles table...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ngo_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
            ngo_name TEXT NOT NULL,
            registration_number TEXT NOT NULL UNIQUE,
            contact_person TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            address TEXT,
            city TEXT DEFAULT 'Kolkata',
            service_areas TEXT DEFAULT 'Kolkata Metropolitan Area',
            verification_status TEXT NOT NULL DEFAULT 'PENDING' CHECK(verification_status IN ('PENDING', 'VERIFIED', 'REJECTED')),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)

    # 4. NGO Contact Requests Table
    print("Creating ngo_contact_requests table...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ngo_contact_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ngo_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            donor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            required_blood_group TEXT NOT NULL CHECK(required_blood_group IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')),
            message TEXT,
            status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'ACCEPTED', 'DECLINED', 'COMPLETED')),
            response_time TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(ngo_id, donor_id, required_blood_group)
        );
    """)

    # 5. Blocked Users Table
    print("Creating blocked_users table...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS blocked_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            blocker_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            blocked_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            reason TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(blocker_id, blocked_id),
            CHECK(blocker_id != blocked_id)
        );
    """)

    # 6. Performance Indexes
    print("Creating performance indexes...")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_family_members_user ON family_members(user_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_family_members_blood ON family_members(blood_group);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ngo_profiles_user ON ngo_profiles(user_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ngo_profiles_status ON ngo_profiles(verification_status);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ngo_contact_ngo ON ngo_contact_requests(ngo_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ngo_contact_donor ON ngo_contact_requests(donor_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ngo_contact_status ON ngo_contact_requests(status);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_blocked_users_pair ON blocked_users(blocker_id, blocked_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_users_role_city ON users(role, city);")

    conn.commit()
    print("Migration completed successfully!")
    conn.close()

if __name__ == "__main__":
    run_migration()
