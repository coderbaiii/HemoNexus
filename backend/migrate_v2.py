"""
HEMONEXAS Database Migration V2
Adds tables for Family Management, NGO Portal, User Blocking, and Profile Enhancement.
Safe and idempotent.
"""
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import Config

def run_migration(db_path=None):
    target_path = db_path or Config.DATABASE_PATH
    if target_path == ":memory:":
        return
    
    conn = sqlite3.connect(str(target_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("PRAGMA foreign_keys = OFF;")
        
        # 1. Check if users table needs 'ngo' role support
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='users';")
        row = cursor.fetchone()
        if row and "'ngo'" not in row[0].lower():
            # Needs migration to allow 'ngo' role
            cursor.execute("ALTER TABLE users RENAME TO _users_old_v2;")
            cursor.execute("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER GENERATED ALWAYS AS (id) VIRTUAL,
                    full_name TEXT NOT NULL,
                    name TEXT GENERATED ALWAYS AS (full_name) VIRTUAL,
                    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    phone TEXT,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('donor', 'patient', 'admin', 'ngo', 'DONOR', 'PATIENT', 'ADMIN', 'NGO')),
                    profile_photo TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                );
            """)
            cursor.execute("""
                INSERT INTO users (id, full_name, email, phone, password_hash, role, created_at, updated_at)
                SELECT id, full_name, email, phone, password_hash, role, created_at, updated_at
                FROM _users_old_v2;
            """)
            cursor.execute("DROP TABLE _users_old_v2;")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);")
            print("Migrated users table to support 'ngo' role.")
        else:
            # Check if profile_photo column exists
            cursor.execute("PRAGMA table_info(users);")
            cols = [c[1] for c in cursor.fetchall()]
            if "profile_photo" not in cols:
                try:
                    cursor.execute("ALTER TABLE users ADD COLUMN profile_photo TEXT;")
                    print("Added profile_photo column to users table.")
                except Exception:
                    pass

        # 2. Family Members Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS family_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                full_name TEXT NOT NULL,
                relationship TEXT NOT NULL CHECK(relationship IN ('Father', 'Mother', 'Brother', 'Sister', 'Spouse', 'Child', 'Other')),
                blood_group TEXT NOT NULL CHECK(blood_group IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')),
                age INTEGER NOT NULL CHECK(age >= 0 AND age <= 130),
                phone TEXT,
                medical_notes TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_family_members_user ON family_members(user_id);")

        # 3. NGO Profiles Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ngo_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
                ngo_name TEXT NOT NULL,
                registration_number TEXT,
                contact_person TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT NOT NULL,
                address TEXT NOT NULL,
                operating_locations TEXT NOT NULL,
                service_areas TEXT,
                verification_status TEXT NOT NULL DEFAULT 'PENDING' CHECK(verification_status IN ('PENDING', 'VERIFIED', 'REJECTED')),
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ngo_profiles_user ON ngo_profiles(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ngo_verification ON ngo_profiles(verification_status);")

        # 4. NGO Contact Requests Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ngo_contact_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ngo_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                donor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                blood_group TEXT NOT NULL CHECK(blood_group IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')),
                units_needed INTEGER NOT NULL DEFAULT 1 CHECK(units_needed > 0),
                reason TEXT NOT NULL,
                message TEXT,
                status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'ACCEPTED', 'DECLINED', 'COMPLETED')),
                donor_consent INTEGER NOT NULL DEFAULT 0 CHECK(donor_consent IN (0, 1)),
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ngo_requests_ngo ON ngo_contact_requests(ngo_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ngo_requests_donor ON ngo_contact_requests(donor_id);")

        # 5. Blocked Users Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS blocked_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                blocker_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                blocked_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                reason TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(blocker_id, blocked_id)
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_blocked_users_blocker ON blocked_users(blocker_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_blocked_users_blocked ON blocked_users(blocked_id);")

        # 6. Check if blood_requests has family_member_id
        cursor.execute("PRAGMA table_info(blood_requests);")
        br_cols = [c[1] for c in cursor.fetchall()]
        if "family_member_id" not in br_cols:
            try:
                cursor.execute("ALTER TABLE blood_requests ADD COLUMN family_member_id INTEGER REFERENCES family_members(id) ON DELETE SET NULL;")
                print("Added family_member_id column to blood_requests.")
            except Exception:
                pass

        conn.commit()
        cursor.execute("PRAGMA foreign_keys = ON;")
        print("Database migration V2 completed successfully.")
    except Exception as e:
        conn.rollback()
        print(f"Migration error: {e}")
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
