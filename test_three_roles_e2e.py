import sys
import os
import json

from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app import create_app
from backend.database import get_db, query_db, execute_db

app = create_app()
client = app.test_client()

print("=" * 60)
print("TESTING 3-ROLE WORKFLOW END-TO-END")
print("=" * 60)

# -------------------------------------------------------------
# 1. NGO FRAUD DETECTION & VERIFIED REGISTRATION TEST
# -------------------------------------------------------------
print("\n[TEST 1] NGO Fraud Detection:")
# Attempt fraudulent NGO registration with disposable domain and fake keyword
fraud_payload = {
    "full_name": "Fake Blood Syndicate",
    "email": "scam_org@mailinator.com",
    "password": "Password123!",
    "role": "ngo",
    "ngo_name": "Fake Blood Syndicate",
    "registration_number": "0000",
    "phone": "+91 99999 00000",
    "city": "Kolkata"
}
res = client.post("/api/register", json=fraud_payload)
print(f"Fraud registration HTTP status: {res.status_code}")
res_json = res.get_json() or {}
print(f"Fraud response message: {res_json.get('error')}")
assert res.status_code == 403, f"Expected 403, got {res.status_code}"

# Attempt login with the blocked fraudulent account
login_res = client.post("/api/login", json={"email": "scam_org@mailinator.com", "password": "Password123!"})
print(f"Blocked account login HTTP status: {login_res.status_code}")
assert login_res.status_code == 403, f"Expected 403 for blocked login, got {login_res.status_code}"
print("-> FRAUD TEST PASSED: Blocked fraudulent registration & prevented login.")

# Legitimate NGO registration
print("\n[TEST 2] Legitimate NGO Registration (e-RaktKosh Dataset):")
legit_ngo_email = "calcutta_redcross@hemonexus.org"
legit_payload = {
    "full_name": "Calcutta National Medical College Blood Bank",
    "email": legit_ngo_email,
    "password": "Password123!",
    "role": "ngo",
    "ngo_name": "Calcutta National Medical College Blood Centre",
    "registration_number": "WB-CNMC-2026",
    "phone": "+91 33 2284 3582",
    "city": "Kolkata"
}

with app.app_context():
    db = get_db()
    existing_u = query_db("SELECT id FROM users WHERE email = ?", (legit_ngo_email,), one=True, db=db)
    if existing_u:
        existing_p = query_db("SELECT id FROM ngo_profiles WHERE user_id = ?", (existing_u["id"],), one=True, db=db)
        if not existing_p:
            execute_db("DELETE FROM users WHERE id = ?", (existing_u["id"],), db=db)

# Register or login if exists
res = client.post("/api/register", json=legit_payload)
if res.status_code == 409: # Already registered
    client.post("/api/login", json={"email": legit_ngo_email, "password": "Password123!"})
    print("-> Logged into existing legitimate NGO.")
else:
    print(f"Legit NGO registration status: {res.status_code}")
    assert res.status_code == 201

# Verify NGO profile
with app.app_context():
    db = get_db()
    ngo_user = query_db("SELECT * FROM users WHERE email = ?", (legit_ngo_email,), one=True, db=db)
    ngo_prof = query_db("SELECT * FROM ngo_profiles WHERE user_id = ?", (ngo_user["id"],), one=True, db=db)
    print(f"NGO Verification Status: {ngo_prof['verification_status']}, Govt Verified: {ngo_prof['govt_verified']}")
    assert ngo_prof["govt_verified"] == 1 or ngo_prof["verification_status"] in ("VERIFIED", "PENDING")

# -------------------------------------------------------------
# 2. PATIENT FLOW: DUAL SOURCING (DONOR VS NGO)
# -------------------------------------------------------------
print("\n[TEST 3] Patient Registration & Dual Sourcing:")
patient_email = "rohan.patient@hemonexus.org"
patient_payload = {
    "full_name": "Rohan Gupta (Patient)",
    "email": patient_email,
    "password": "Password123!",
    "role": "patient",
    "phone": "+91 98310 99881",
    "city": "Kolkata"
}
client.post("/api/register", json=patient_payload)
client.post("/api/login", json={"email": patient_email, "password": "Password123!"})

# Patient searches accredited NGOs
ngo_list_res = client.get("/api/patient/ngos")
print(f"Patient fetch NGOs status: {ngo_list_res.status_code}")
ngo_data = ngo_list_res.get_json()
print(f"Accredited NGOs found: {len(ngo_data.get('ngos', []))}")
assert len(ngo_data.get("ngos", [])) > 0

# Set target NGO to our newly registered verified NGO
with app.app_context():
    db = get_db()
    target_ngo_user = query_db("SELECT id, email FROM users WHERE email = ?", (legit_ngo_email,), one=True, db=db)
    target_ngo_id = target_ngo_user["id"]
    ngo_email = target_ngo_user["email"]

# Patient submits direct blood requisition to NGO
ngo_req_payload = {
    "ngo_id": target_ngo_id,
    "blood_group": "O+",
    "units": 2,
    "hospital_name": "Kolkata Medical College",
    "hospital_location": "College Street, Kolkata",
    "urgency": "CRITICAL",
    "notes": "Emergency ICU admission - urgent 2 units needed."
}
submit_res = client.post("/api/patient/ngo-requests", json=ngo_req_payload)
print(f"Requisition submitted to NGO: {submit_res.status_code}, {submit_res.get_json().get('message')}")
assert submit_res.status_code == 201

# Patient checks their submitted NGO requisitions
my_ngo_reqs_res = client.get("/api/patient/my-ngo-requests")
my_ngo_data = my_ngo_reqs_res.get_json()
print(f"Patient's open NGO requisitions: {len(my_ngo_data.get('requests', []))}")
assert len(my_ngo_data.get("requests", [])) > 0
patient_ngo_req_id = my_ngo_data["requests"][0]["id"]

# -------------------------------------------------------------
# 3. NGO ACCEPTS & DISPATCHES RESPONSE TO PATIENT
# -------------------------------------------------------------
print("\n[TEST 4] NGO Accepts & Dispatches Message to Patient:")
# Login as the target NGO
with app.app_context():
    db = get_db()
    ngo_owner = query_db("SELECT email FROM users WHERE id = ?", (target_ngo_id,), one=True, db=db)
    ngo_email = ngo_owner["email"]

client.post("/api/login", json={"email": ngo_email, "password": "Password123!"})

# NGO views incoming patient requests
incoming_p_res = client.get("/api/ngo/patient-requests")
incoming_p_data = incoming_p_res.get_json()
print(f"NGO incoming patient requests: {len(incoming_p_data.get('requests', []))}")
assert len(incoming_p_data.get("requests", [])) > 0

# NGO accepts and dispatches custom response message
accept_msg = "2 units of O+ blood reserved at Counter 2. Please show Doctor requisition slip."
disp_res = client.post(f"/api/ngo/patient-requests/{patient_ngo_req_id}/accept", json={"custom_message": accept_msg})
print(f"NGO accepted patient request: {disp_res.status_code}, {disp_res.get_json().get('message')}")
assert disp_res.status_code == 200

# -------------------------------------------------------------
# 4. DONOR LIFECYCLE: INCOMING REQUESTS & KYC COMPLETION
# -------------------------------------------------------------
print("\n[TEST 5] Donor Flow: Receive Requests, Accept & Complete Donation (KYC Update):")
donor_email = "sourav.donor@hemonexus.org"
donor_payload = {
    "full_name": "Sourav Mukherjee",
    "email": donor_email,
    "password": "Password123!",
    "role": "donor",
    "blood_group": "O+",
    "phone": "+91 98301 22334",
    "city": "Kolkata",
    "availability": "24_HOURS"
}
client.post("/api/register", json=donor_payload)
client.post("/api/login", json={"email": donor_email, "password": "Password123!"})

# NGO dispatches outreach request to this donor
with app.app_context():
    db = get_db()
    donor_user = query_db("SELECT id FROM users WHERE email = ?", (donor_email,), one=True, db=db)
    donor_uid = donor_user["id"]

# Log in as NGO to outreach to donor
client.post("/api/login", json={"email": ngo_email, "password": "Password123!"})
outreach_res = client.post("/api/ngo/contact-request", json={
    "donor_id": donor_uid,
    "required_blood_group": "O+",
    "message": "Urgent drive at Salt Lake Stadium on Saturday."
})
print(f"NGO outreach to donor: {outreach_res.status_code}")

# Patient also dispatches a request to this donor
client.post("/api/login", json={"email": patient_email, "password": "Password123!"})
# Create blood request and dispatch to donor
with app.app_context():
    db = get_db()
    patient_user = query_db("SELECT id FROM users WHERE email = ?", (patient_email,), one=True, db=db)
    from backend.database import execute_db
    import datetime
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    br_id, _ = execute_db(
        """INSERT INTO blood_requests (patient_id, required_blood_group, required_units, hospital_name, location, urgency, request_status, created_at, updated_at)
           VALUES (?, 'O+', 1, 'AMRI Hospital', 'Salt Lake, Kolkata', 'CRITICAL', 'OPEN', ?, ?)""",
        (patient_user["id"], now_iso, now_iso),
        db=db
    )
    resp_id, _ = execute_db(
        """INSERT INTO donor_request_responses (blood_request_id, donor_id, status, created_at, updated_at)
           VALUES (?, ?, 'PENDING', ?, ?)""",
        (br_id, donor_uid, now_iso, now_iso),
        db=db
    )

# Log in as Donor and inspect all incoming requests (from BOTH Patient and NGO)
client.post("/api/login", json={"email": donor_email, "password": "Password123!"})
all_incoming_res = client.get("/api/donor/all-incoming-requests")
all_incoming = all_incoming_res.get_json()
print(f"Donor incoming from Patients: {len(all_incoming.get('patient_requests', []))}")
print(f"Donor incoming from NGOs: {len(all_incoming.get('ngo_requests', []))}")
assert len(all_incoming.get("patient_requests", [])) > 0
assert len(all_incoming.get("ngo_requests", [])) > 0

# Donor accepts patient request
acc_p_res = client.post(f"/api/donor/requests/{resp_id}/accept", json={"message": "I am on my way to AMRI Hospital."})
print(f"Donor accepted patient request: {acc_p_res.status_code}")
assert acc_p_res.status_code == 200

# Donor completes donation -> KYC update check
complete_res = client.post(f"/api/donor/requests/{resp_id}/complete", json={"blood_centre": "AMRI Blood Bank"})
print(f"Donation completed: {complete_res.status_code}, {complete_res.get_json().get('message')}")
assert complete_res.status_code == 200
comp_data = complete_res.get_json()
print(f"Renewed KYC Status: {comp_data.get('kyc_status')}, Next Verification: {comp_data.get('next_verification_date')}")

# Verify in DB
with app.app_context():
    db = get_db()
    dp = query_db("SELECT * FROM donor_profiles WHERE user_id = ?", (donor_uid,), one=True, db=db)
    print(f"DB donor KYC status: {dp['kyc_status']}, Total donations: {dp['total_donations']}")
    assert dp["kyc_status"] == "VERIFIED"
    assert dp["total_donations"] >= 1

# Donor updates privacy preference
priv_res = client.post("/api/donor/privacy-preference", json={"privacy_preference": "ALWAYS_VISIBLE"})
print(f"Privacy preference update: {priv_res.status_code}, {priv_res.get_json().get('privacy_preference')}")
assert priv_res.status_code == 200

print("\n" + "=" * 60)
print("ALL 5 END-TO-END WORKFLOW TESTS COMPLETED SUCCESSFULLY!")
print("=" * 60)
