"""
HEMONEXAS Database Seeding Script
Populates the database with realistic synthetic test data:
- Administrator account
- Patient accounts & blood requests
- 24+ diverse synthetic donors (covering all blood groups, active/due/inactive,
  day/night/24h/8h schedules, travel limits, and temporary availability)
- In-app notifications & donation records
"""
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import datetime
from werkzeug.security import generate_password_hash

def seed_database(conn):
    """Seed synthetic entities into the database."""
    cur = conn.cursor()
    now = datetime.datetime.now(datetime.timezone.utc)
    now_iso = now.isoformat()
    
    # Verification interval dates
    plus_6mo = (now + datetime.timedelta(days=180)).isoformat()
    plus_3mo = (now + datetime.timedelta(days=90)).isoformat()
    past_5days = (now - datetime.timedelta(days=5)).isoformat()    # Due (within 30-day grace)
    past_15days = (now - datetime.timedelta(days=15)).isoformat()  # Due (within 30-day grace)
    past_7mo = (now - datetime.timedelta(days=210)).isoformat()    # Overdue/inactive
    past_10mo = (now - datetime.timedelta(days=300)).isoformat()   # Inactive
    past_1yr = (now - datetime.timedelta(days=365)).isoformat()

    # 1. Admin Account
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
            (admin_id, "INIT_ADMIN", "Initialized default system administrator")
        )

    # 2. Patients & Demo Blood Requests
    patients_data = [
        {
            "name": "Rajesh Kumar",
            "email": "patient.raj@example.com",
            "phone": "+91 98765 43210",
            "location": "Apollo Multispecialty Hospital, Kolkata",
            "lat": 22.5697,
            "lon": 88.4046,
            "requests": [
                {
                    "blood": "O+",
                    "units": 2,
                    "hospital": "Apollo Multispecialty Hospital",
                    "location": "Canal Circular Rd, EM Bypass, Kolkata",
                    "lat": 22.5697,
                    "lon": 88.4046,
                    "urgency": "URGENT",
                    "preferred_dist": 20.0,
                    "sort_pref": "BEST_MATCH",
                    "avail_pref": "ANY"
                },
                {
                    "blood": "B+",
                    "units": 1,
                    "hospital": "AMRI Hospital, Salt Lake",
                    "location": "JC Block, Salt Lake, Kolkata",
                    "lat": 22.5735,
                    "lon": 88.4110,
                    "urgency": "CRITICAL",
                    "preferred_dist": 15.0,
                    "sort_pref": "FASTEST",
                    "avail_pref": "24_HOURS"
                }
            ]
        },
        {
            "name": "Anita Roy Chowdhury",
            "email": "patient.anita@example.com",
            "phone": "+91 98765 88990",
            "location": "Fortis Hospital, Anandapur, Kolkata",
            "lat": 22.5186,
            "lon": 88.4011,
            "requests": [
                {
                    "blood": "A-",
                    "units": 1,
                    "hospital": "Fortis Hospital",
                    "location": "730 Anandapur, EM Bypass, Kolkata",
                    "lat": 22.5186,
                    "lon": 88.4011,
                    "urgency": "NORMAL",
                    "preferred_dist": 30.0,
                    "sort_pref": "NEAREST",
                    "avail_pref": "DAY"
                }
            ]
        }
    ]

    for p in patients_data:
        cur.execute("SELECT id FROM users WHERE email = ?", (p["email"],))
        p_row = cur.fetchone()
        if not p_row:
            p_pass = generate_password_hash("Patient@1234")
            cur.execute(
                "INSERT INTO users (full_name, email, password_hash, role, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (p["name"], p["email"], p_pass, "patient", now_iso, now_iso)
            )
            p_user_id = cur.lastrowid
            cur.execute(
                "INSERT INTO patient_profiles (user_id, phone, location, latitude, longitude, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (p_user_id, p["phone"], p["location"], p["lat"], p["lon"], now_iso, now_iso)
            )
            for req in p["requests"]:
                cur.execute(
                    """INSERT INTO blood_requests 
                       (patient_id, required_blood_group, required_units, hospital_name, location, latitude, longitude, preferred_max_distance, required_date_time, urgency, sorting_preference, availability_preference, request_status, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?)""",
                    (p_user_id, req["blood"], req["units"], req["hospital"], req["location"], req["lat"], req["lon"], req["preferred_dist"], now_iso, req["urgency"], req["sort_pref"], req["avail_pref"], now_iso, now_iso)
                )

    # 3. Comprehensive Synthetic Donors (24 Diverse Donors)
    # Centers around Kolkata metropolitan region (approx lat 22.5 to 22.7, lon 88.3 to 88.5)
    synthetic_donors = [
        # O+ Donors (Various statuses and distances from Apollo Hospital at 22.5697, 88.4046)
        {
            "name": "Amitav Sengupta",
            "email": "amitav.donor@example.com",
            "blood": "O+",
            "phone": "+91 98300 11201",
            "loc": "Sector 5, Salt Lake, Kolkata",
            "lat": 22.5805, "lon": 88.4344, # ~3.3 km
            "avail": "24_HOURS", "from": "00:00", "to": "23:59", "is_avail": 1,
            "dist": 25.0, "status": "ACTIVE", "last_v": now_iso, "next_v": plus_6mo
        },
        {
            "name": "Priyanka Roy",
            "email": "priyanka.donor@example.com",
            "blood": "O+",
            "phone": "+91 98300 11202",
            "loc": "Park Circus, Kolkata",
            "lat": 22.5414, "lon": 88.3686, # ~4.9 km
            "avail": "DAY", "from": "08:00", "to": "18:00", "is_avail": 1,
            "dist": 15.0, "status": "ACTIVE", "last_v": now_iso, "next_v": plus_6mo
        },
        {
            "name": "Siddharth Banerjee",
            "email": "siddharth.donor@example.com",
            "blood": "O+",
            "phone": "+91 98300 11203",
            "loc": "Ballygunge Circular Road, Kolkata",
            "lat": 22.5320, "lon": 88.3630, # ~5.9 km
            "avail": "NIGHT", "from": "18:00", "to": "06:00", "is_avail": 1,
            "dist": 20.0, "status": "ACTIVE", "last_v": now_iso, "next_v": plus_6mo
        },
        {
            "name": "Arjun Mukherjee",
            "email": "arjun.donor@example.com",
            "blood": "O+",
            "phone": "+91 98300 11204",
            "loc": "Kankurgachi, Kolkata",
            "lat": 22.5760, "lon": 88.3880, # ~2.0 km (Very close)
            "avail": "8_HOURS", "from": "09:00", "to": "17:00", "is_avail": 1,
            "dist": 10.0, "status": "ACTIVE", "last_v": (now - datetime.timedelta(days=20)).isoformat(), "next_v": plus_3mo
        },
        {
            "name": "Devratna Mitra",
            "email": "devratna.donor@example.com",
            "blood": "O+",
            "phone": "+91 98300 11205",
            "loc": "Howrah Station Road",
            "lat": 22.5857, "lon": 88.3426, # ~6.5 km
            "avail": "24_HOURS", "from": "00:00", "to": "23:59", "is_avail": 1,
            "dist": 15.0, "status": "VERIFICATION_DUE", "last_v": past_7mo, "next_v": past_5days
        },
        {
            "name": "Rohan Ganguly",
            "email": "rohan.donor@example.com",
            "blood": "O+",
            "phone": "+91 98300 11206",
            "loc": "Barasat, North 24 Parganas",
            "lat": 22.7230, "lon": 88.4817, # ~18.5 km
            "avail": "24_HOURS", "from": "00:00", "to": "23:59", "is_avail": 1,
            "dist": 25.0, "status": "INACTIVE", "last_v": past_1yr, "next_v": past_7mo
        },
        {
            "name": "Kunal Bhattacharya",
            "email": "kunal.donor@example.com",
            "blood": "O+",
            "phone": "+91 98300 11207",
            "loc": "New Town Action Area 1",
            "lat": 22.5840, "lon": 88.4610, # ~6.0 km
            "avail": "24_HOURS", "from": "00:00", "to": "23:59", "is_avail": 0, # Temporarily unavailable!
            "dist": 20.0, "status": "ACTIVE", "last_v": now_iso, "next_v": plus_6mo
        },
        {
            "name": "Vikram Das",
            "email": "vikram.donor@example.com",
            "blood": "O+",
            "phone": "+91 98300 11208",
            "loc": "Garia, Kolkata",
            "lat": 22.4640, "lon": 88.3830, # ~12.0 km
            "avail": "DAY", "from": "08:00", "to": "18:00", "is_avail": 1,
            "dist": 5.0, # Small donor travel limit! Will fail travel limit if distance > 5km
            "status": "ACTIVE", "last_v": now_iso, "next_v": plus_6mo
        },

        # A+ Donors
        {
            "name": "Subhashish Bose",
            "email": "subhashish.donor@example.com",
            "blood": "A+",
            "phone": "+91 98300 11209",
            "loc": "New Town Action Area 2",
            "lat": 22.5937, "lon": 88.4798,
            "avail": "24_HOURS", "from": "00:00", "to": "23:59", "is_avail": 1,
            "dist": 30.0, "status": "ACTIVE", "last_v": now_iso, "next_v": plus_6mo
        },
        {
            "name": "Ananya Chatterjee",
            "email": "ananya.donor@example.com",
            "blood": "A+",
            "phone": "+91 98300 11210",
            "loc": "Behala Chowrasta, Kolkata",
            "lat": 22.4988, "lon": 88.3180,
            "avail": "DAY", "from": "08:00", "to": "18:00", "is_avail": 1,
            "dist": 20.0, "status": "ACTIVE", "last_v": now_iso, "next_v": plus_6mo
        },
        {
            "name": "Debabrata Majumdar",
            "email": "debabrata.donor@example.com",
            "blood": "A+",
            "phone": "+91 98300 11211",
            "loc": "Ultadanga, Kolkata",
            "lat": 22.5940, "lon": 88.3870,
            "avail": "NIGHT", "from": "18:00", "to": "06:00", "is_avail": 1,
            "dist": 15.0, "status": "VERIFICATION_DUE", "last_v": past_7mo, "next_v": past_15days
        },

        # A- Donors
        {
            "name": "Mousumi Sarkar",
            "email": "mousumi.donor@example.com",
            "blood": "A-",
            "phone": "+91 98300 11212",
            "loc": "Kasba, Kolkata",
            "lat": 22.5180, "lon": 88.3880,
            "avail": "24_HOURS", "from": "00:00", "to": "23:59", "is_avail": 1,
            "dist": 25.0, "status": "ACTIVE", "last_v": now_iso, "next_v": plus_6mo
        },
        {
            "name": "Tanmoy Ghoshal",
            "email": "tanmoy.donor@example.com",
            "blood": "A-",
            "phone": "+91 98300 11213",
            "loc": "Jadavpur Central Road",
            "lat": 22.4990, "lon": 88.3710,
            "avail": "DAY", "from": "08:00", "to": "18:00", "is_avail": 1,
            "dist": 15.0, "status": "ACTIVE", "last_v": (now - datetime.timedelta(days=45)).isoformat(), "next_v": plus_3mo
        },

        # B+ Donors
        {
            "name": "Saurav Dasgupta",
            "email": "saurav.donor@example.com",
            "blood": "B+",
            "phone": "+91 98300 11214",
            "loc": "Salt Lake Sector 1, Kolkata",
            "lat": 22.5910, "lon": 88.4090,
            "avail": "24_HOURS", "from": "00:00", "to": "23:59", "is_avail": 1,
            "dist": 25.0, "status": "ACTIVE", "last_v": now_iso, "next_v": plus_6mo
        },
        {
            "name": "Madhurima Sen",
            "email": "madhurima.donor@example.com",
            "blood": "B+",
            "phone": "+91 98300 11215",
            "loc": "Shyambazar Five Point",
            "lat": 22.6020, "lon": 88.3720,
            "avail": "8_HOURS", "from": "09:00", "to": "17:00", "is_avail": 1,
            "dist": 20.0, "status": "ACTIVE", "last_v": now_iso, "next_v": plus_6mo
        },
        {
            "name": "Joydeep Nandi",
            "email": "joydeep.donor@example.com",
            "blood": "B+",
            "phone": "+91 98300 11216",
            "loc": "Dum Dum Cantonment",
            "lat": 22.6450, "lon": 88.4200,
            "avail": "NIGHT", "from": "18:00", "to": "06:00", "is_avail": 1,
            "dist": 20.0, "status": "ACTIVE", "last_v": now_iso, "next_v": plus_6mo
        },
        {
            "name": "Pradip Halder",
            "email": "pradip.donor@example.com",
            "blood": "B+",
            "phone": "+91 98300 11217",
            "loc": "Kalyani Highway",
            "lat": 22.8000, "lon": 88.4500, # Far away
            "avail": "24_HOURS", "from": "00:00", "to": "23:59", "is_avail": 1,
            "dist": 35.0, "status": "INACTIVE", "last_v": past_10mo, "next_v": past_7mo
        },

        # B- Donors
        {
            "name": "Rina Karmakar",
            "email": "rina.donor@example.com",
            "blood": "B-",
            "phone": "+91 98300 11218",
            "loc": "Lake Town, Kolkata",
            "lat": 22.6010, "lon": 88.4020,
            "avail": "24_HOURS", "from": "00:00", "to": "23:59", "is_avail": 1,
            "dist": 25.0, "status": "ACTIVE", "last_v": now_iso, "next_v": plus_6mo
        },
        {
            "name": "Dipankar Paul",
            "email": "dipankar.donor@example.com",
            "blood": "B-",
            "phone": "+91 98300 11219",
            "loc": "Baguiati VIP Road",
            "lat": 22.6180, "lon": 88.4280,
            "avail": "DAY", "from": "08:00", "to": "18:00", "is_avail": 1,
            "dist": 15.0, "status": "ACTIVE", "last_v": now_iso, "next_v": plus_6mo
        },

        # AB+ Donors
        {
            "name": "Rituparna Dutta",
            "email": "rituparna.donor@example.com",
            "blood": "AB+",
            "phone": "+91 98300 11220",
            "loc": "Alipore, Kolkata",
            "lat": 22.5310, "lon": 88.3300,
            "avail": "24_HOURS", "from": "00:00", "to": "23:59", "is_avail": 1,
            "dist": 20.0, "status": "ACTIVE", "last_v": now_iso, "next_v": plus_6mo
        },
        {
            "name": "Indranil Guha",
            "email": "indranil.donor@example.com",
            "blood": "AB+",
            "phone": "+91 98300 11221",
            "loc": "Santoshpur, Kolkata",
            "lat": 22.4910, "lon": 88.3890,
            "avail": "NIGHT", "from": "18:00", "to": "06:00", "is_avail": 1,
            "dist": 15.0, "status": "ACTIVE", "last_v": now_iso, "next_v": plus_6mo
        },

        # AB- Donors (Rare blood group)
        {
            "name": "Sandip Kundu",
            "email": "sandip.donor@example.com",
            "blood": "AB-",
            "phone": "+91 98300 11222",
            "loc": "Maniktala, Kolkata",
            "lat": 22.5850, "lon": 88.3790,
            "avail": "24_HOURS", "from": "00:00", "to": "23:59", "is_avail": 1,
            "dist": 25.0, "status": "ACTIVE", "last_v": now_iso, "next_v": plus_6mo
        },
        {
            "name": "Soma Bhowmick",
            "email": "soma.donor@example.com",
            "blood": "AB-",
            "phone": "+91 98300 11223",
            "loc": "Gariahat, Kolkata",
            "lat": 22.5180, "lon": 88.3650,
            "avail": "DAY", "from": "08:00", "to": "18:00", "is_avail": 1,
            "dist": 20.0, "status": "ACTIVE", "last_v": (now - datetime.timedelta(days=90)).isoformat(), "next_v": (now + datetime.timedelta(days=90)).isoformat()
        },

        # O- Donor (Universal Red Cell Donor)
        {
            "name": "Abhishek Chakraborty",
            "email": "abhishek.donor@example.com",
            "blood": "O-",
            "phone": "+91 98300 11224",
            "loc": "Chinar Park, Rajarhat",
            "lat": 22.6280, "lon": 88.4420,
            "avail": "24_HOURS", "from": "00:00", "to": "23:59", "is_avail": 1,
            "dist": 30.0, "status": "ACTIVE", "last_v": now_iso, "next_v": plus_6mo
        }
    ]

    donor_pass = generate_password_hash("Donor@1234")
    for d in synthetic_donors:
        cur.execute("SELECT id FROM users WHERE email = ?", (d["email"],))
        user_row = cur.fetchone()
        if not user_row:
            cur.execute(
                "INSERT INTO users (full_name, email, password_hash, role, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (d["name"], d["email"], donor_pass, "donor", now_iso, now_iso)
            )
            d_uid = cur.lastrowid
            cur.execute(
                """INSERT INTO donor_profiles 
                   (user_id, blood_group, phone, location, latitude, longitude, availability, available_from, available_to, maximum_travel_distance, is_available, profile_status, last_verified_date, next_verification_date, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (d_uid, d["blood"], d["phone"], d["loc"], d["lat"], d["lon"], d["avail"], d["from"], d["to"], d["dist"], d["is_avail"], d["status"], d["last_v"], d["next_v"], now_iso, now_iso)
            )

    # 4. Sample Donation Records & In-App Notifications
    cur.execute("SELECT id FROM users WHERE email = ?", ("amitav.donor@example.com",))
    amitav = cur.fetchone()
    cur.execute("SELECT id FROM users WHERE email = ?", ("patient.raj@example.com",))
    raj = cur.fetchone()
    
    if amitav and raj:
        cur.execute("SELECT COUNT(*) AS count FROM donation_records")
        if cur.fetchone()["count"] == 0:
            past_donation_date = (now - datetime.timedelta(days=40)).isoformat()
            cur.execute(
                """INSERT INTO donation_records 
                   (donor_id, patient_id, donation_date, blood_center_name, units_donated, verification_notes, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (amitav["id"], raj["id"], past_donation_date, "Apollo Blood Bank & Transfusion Centre", 1, "Successful voluntary donation. All clinical screenings authorized by medical staff.", past_donation_date)
            )
            
            # Sample notifications
            cur.execute(
                """INSERT INTO notifications (user_id, title, message, type, is_read, link, created_at)
                   VALUES (?, ?, ?, ?, 0, ?, ?)""",
                (amitav["id"], "Verification Reminder", "Your 6-month profile verification is active and current.", "VERIFICATION", "/donor/dashboard", now_iso)
            )
            cur.execute(
                """INSERT INTO notifications (user_id, title, message, type, is_read, link, created_at)
                   VALUES (?, ?, ?, ?, 0, ?, ?)""",
                (raj["id"], "System Ready", "Smart requirement-based donor matching is active for your blood requests.", "INFO", "/patient/dashboard", now_iso)
            )

    conn.commit()
    print("Database seeding completed successfully: 24 synthetic donors, demo patients, and admin initialized.")

if __name__ == "__main__":
    from database.db import get_db, init_db
    init_db(seed=True)
