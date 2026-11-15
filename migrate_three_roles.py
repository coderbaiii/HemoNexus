import sqlite3
import datetime

DB_PATH = "hemonexus.db"

def run_migration():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # 1. users table: add account_status if not exists
    cur.execute("PRAGMA table_info(users)")
    user_cols = [c[1] for c in cur.fetchall()]
    if "account_status" not in user_cols:
        cur.execute("ALTER TABLE users ADD COLUMN account_status TEXT DEFAULT 'ACTIVE'")
        print("Added account_status to users.")
        
    # 2. donor_profiles: add kyc_status, kyc_updated_at, total_donations, privacy_preference
    cur.execute("PRAGMA table_info(donor_profiles)")
    donor_cols = [c[1] for c in cur.fetchall()]
    if "kyc_status" not in donor_cols:
        cur.execute("ALTER TABLE donor_profiles ADD COLUMN kyc_status TEXT DEFAULT 'VERIFIED'")
        print("Added kyc_status to donor_profiles.")
    if "kyc_updated_at" not in donor_cols:
        cur.execute("ALTER TABLE donor_profiles ADD COLUMN kyc_updated_at TEXT")
        print("Added kyc_updated_at to donor_profiles.")
    if "total_donations" not in donor_cols:
        cur.execute("ALTER TABLE donor_profiles ADD COLUMN total_donations INTEGER DEFAULT 0")
        print("Added total_donations to donor_profiles.")
    if "privacy_preference" not in donor_cols:
        cur.execute("ALTER TABLE donor_profiles ADD COLUMN privacy_preference TEXT DEFAULT 'MASKED'")
        print("Added privacy_preference to donor_profiles.")
        
    # 3. ngo_profiles: add govt_license_number, govt_verified, fraud_status, fraud_reason
    cur.execute("PRAGMA table_info(ngo_profiles)")
    ngo_cols = [c[1] for c in cur.fetchall()]
    if "govt_license_number" not in ngo_cols:
        cur.execute("ALTER TABLE ngo_profiles ADD COLUMN govt_license_number TEXT")
        print("Added govt_license_number to ngo_profiles.")
    if "govt_verified" not in ngo_cols:
        cur.execute("ALTER TABLE ngo_profiles ADD COLUMN govt_verified INTEGER DEFAULT 0")
        print("Added govt_verified to ngo_profiles.")
    if "fraud_status" not in ngo_cols:
        cur.execute("ALTER TABLE ngo_profiles ADD COLUMN fraud_status TEXT DEFAULT 'CLEAN'")
        print("Added fraud_status to ngo_profiles.")
    if "fraud_reason" not in ngo_cols:
        cur.execute("ALTER TABLE ngo_profiles ADD COLUMN fraud_reason TEXT")
        print("Added fraud_reason to ngo_profiles.")
        
    # 4. patient_ngo_requests table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS patient_ngo_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        ngo_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        patient_name TEXT NOT NULL,
        patient_phone TEXT,
        blood_group TEXT NOT NULL CHECK(blood_group IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')),
        units_required INTEGER NOT NULL DEFAULT 1 CHECK(units_required > 0),
        hospital_name TEXT NOT NULL,
        hospital_location TEXT,
        urgency TEXT NOT NULL DEFAULT 'URGENT' CHECK(urgency IN ('NORMAL', 'URGENT', 'CRITICAL')),
        patient_notes TEXT,
        status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'ACCEPTED', 'DECLINED', 'FULFILLED')),
        ngo_response_message TEXT,
        responded_at TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pnr_patient ON patient_ngo_requests(patient_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pnr_ngo ON patient_ngo_requests(ngo_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pnr_status ON patient_ngo_requests(status);")
    print("Created patient_ngo_requests table and indexes.")
    
    # Backfill verified state for demo NGOs
    cur.execute("UPDATE ngo_profiles SET govt_verified = 1 WHERE verification_status = 'VERIFIED'")
    cur.execute("UPDATE donor_profiles SET kyc_status = 'VERIFIED' WHERE kyc_status IS NULL")
    
    conn.commit()
    conn.close()
    print("Migration finished successfully.")

if __name__ == "__main__":
    run_migration()
