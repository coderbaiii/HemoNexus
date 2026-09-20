# HEMONEXAS &mdash; Smart Blood Donor Management & Requirement-Based Matching System

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1%2B-red.svg)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/SQLite-3-lightgrey.svg)](https://www.sqlite.org/)
[![Tests](https://img.shields.io/badge/Tests-38%20passed%20(100%25)-success.svg)]()
[![Status](https://img.shields.io/badge/Status-Complete%20%26%20Verified-brightgreen.svg)]()

> **Project Team (Team Egnima):**  
> Arunima Ghosh &bull; Debriddhi Ghosh &bull; Baivabi Chakraborty &bull; Udipta Dhara

---

## 1. Project Overview

Traditional blood donation platforms rely on static lists and manual phone calls, leading to critical delays during medical emergencies. Donors move, change schedules, or become temporarily unavailable, rendering static directories unreliable.

**HEMONEXAS** is an intelligent, location-aware blood donor management and requirement-based matching platform. It bridges patients, blood donors, and blood bank operators through:
1. **Six-Month Donor Verification Lifecycle**: Automated tracking of donor profile freshness (`ACTIVE` &rarr; `VERIFICATION_DUE` &rarr; `INACTIVE`). Inactive profiles are automatically filtered out of emergency searches without deleting donor history.
2. **7-Step Smart Requirement Matching Engine**: Eliminates random donor selection by combining exact ABO/Rh blood compatibility, real-time availability windows, mutual distance limits (Haversine formula), and multi-criteria composite ranking.
3. **Direct Dispatch & Response Workflow**: Patients can immediately invite top-ranked donors with full visibility over response statuses (`PENDING`, `ACCEPTED`, `REJECTED`).
4. **Role-Based Access Control**: Strict separation between `donor`, `patient`, and `admin` roles with authenticated session cookies and hashed credentials.
5. **Medical Safety Principles**: Matching scores represent operational search priority only; clinical screening, disease testing, and blood component release remain strictly under the authority of authorized blood bank personnel.

---

## 2. System Architecture & Matching Methodology

```
                               ┌────────────────────────────────────────────────────────┐
                               │                 Frontend (HTML / CSS / JS)             │
                               │  - Landing Page & System Stats                         │
                               │  - Auth (Login / Register with Donor/Patient roles)    │
                               │  - Donor Dashboard (Availability, 6-Mo Verification)   │
                               │  - Patient Dashboard (Request Creation, Match Results) │
                               │  - Admin Dashboard (User/Donor Audit, Life-Cycle Tool) │
                               └───────────────────────────┬────────────────────────────┘
                                                           │ REST API (JSON / Session Cookies)
                                                           ▼
                               ┌────────────────────────────────────────────────────────┐
                               │                   Flask Application                    │
                               │  - Blueprints: auth, donor, patient, admin, web        │
                               │  - Role-based Access Control (@login_required, roles)  │
                               │  - Secure Password Hashing (Werkzeug scrypt/pbkdf2)    │
                               │  - Parameterized SQLite Queries (Foreign Keys ON)      │
                               └──────────┬─────────────────────────────────┬───────────┘
                                          │                                 │
                                          ▼                                 ▼
                 ┌─────────────────────────────────────┐   ┌────────────────────────────────────┐
                 │     Smart Matching Engine           │   │    Verification Lifecycle Service  │
                 │ 1. Blood Group Compatibility Check  │   │ - last_verified_date tracking      │
                 │ 2. Active Profile Filter            │   │ - next_verification_date (180 days)│
                 │ 3. Time Window Availability Match   │   │ - Grace Period (30 days)           │
                 │ 4. Patient Search Radius Filter     │   │ - Statuses: ACTIVE, DUE, INACTIVE  │
                 │ 5. Donor Max Travel Limit Filter    │   │ - Donor Self-Confirmation API      │
                 │ 6. Candidate Exclusion              │   │ - Exclude Inactive from Matching   │
                 │ 7. Weighted Composite Ranking Score │   │ - Configurable intervals           │
                 └──────────────────┬──────────────────┘   └─────────────────┬──────────────────┘
                                    │                                        │
                                    └───────────────────┬────────────────────┘
                                                        ▼
                               ┌────────────────────────────────────────────────────────┐
                               │                    SQLite Database                     │
                               │  - PRAGMA foreign_keys = ON;                           │
                               │  - users, donor_profiles, patient_profiles             │
                               │  - blood_requests, donor_request_responses             │
                               │  - audit_logs, verification_history                    │
                               └────────────────────────────────────────────────────────┘
```

### The 7-Step Matching Algorithm
1. **Blood Group Compatibility**: Filters candidate donors for exact match (e.g. O+ patient matches O+ donors).
2. **Active Status Enforcement**: Confirms `profile_status == 'ACTIVE'`. Any profile marked `VERIFICATION_DUE` or `INACTIVE` is excluded.
3. **Availability Schedule Verification**: Compares target emergency hour against donor schedule:
   - `24_HOURS`: Available at all times.
   - `DAYTIME`: Active between 08:00 and 18:00.
   - `NIGHTTIME`: Active between 18:00 and 08:00.
   - `8_HOURS`: Active during standard 8-hour shift (09:00 - 17:00).
4. **Patient Search Radius**: Distance between patient/hospital and donor must be $\le$ `preferred_max_distance`.
5. **Donor Travel Limit**: Distance must also be $\le$ donor's `maximum_travel_distance`.
6. **Candidate Exclusion**: Unsuitable candidates are removed from the candidate pool.
7. **Composite Ranking Score**:
   $$\text{Score} = (0.30 \times S_{\text{availability}}) + (0.30 \times S_{\text{distance}} \times U) + (0.20 \times S_{\text{freshness}}) + (0.20 \times S_{\text{proximity}})$$
   - Donors are sorted in descending order of score.

---

## 3. Technology Stack

- **Backend**: Python 3.10+, Flask 3.1+, Werkzeug (password hashing & session authentication)
- **Database**: SQLite 3 with WAL mode, parameterized queries, and enforced foreign keys
- **Frontend**: Responsive HTML5, CSS3, Vanilla JavaScript (zero external node_modules or build step needed)
- **Testing**: Pytest automated test framework covering auth, donor profiles, matching, dispatch, and security

---

## 4. Repository Structure

```
HemoNexus/
├── backend/
│   ├── __init__.py
│   ├── app.py                      # Flask Application Factory & Error Handlers
│   ├── config.py                   # Centralized Configuration & Environment Settings
│   ├── database.py                 # SQLite Connection Manager & Parameterized Helpers
│   ├── init_db.py                  # Database Schema DDL & Demo Data Seeding
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py                 # Registration, Login, Logout, /api/me
│   │   ├── donor.py                # Profile, Availability, 6-Mo Verification, Requests
│   │   ├── patient.py              # Blood Requests, Matching Trigger, Dispatch
│   │   ├── admin.py                # Metrics, Directory Oversight, Lifecycle Sweep
│   │   └── web.py                  # HTML Page Rendering Routes
│   ├── services/
│   │   ├── __init__.py
│   │   ├── matching_service.py     # 7-Step Matching Engine & Haversine Formula
│   │   └── verification_service.py # 6-Month Verification Lifecycle & Sweeper
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css           # Modern Responsive Theme & Badges
│   │   └── js/
│   │       ├── auth.js             # Client-side Auth & Redirection
│   │       ├── donor.js            # Donor Dashboard & Request Actions
│   │       ├── patient.js          # Patient Dashboard & Matching Modal
│   │       └── admin.js            # Admin Console & Verification Sweep
│   └── templates/
│       ├── base.html               # Base Jinja2 Template & Navbar
│       ├── index.html              # Landing Page & Workflow Overview
│       ├── login.html              # Sign In Interface
│       ├── register.html           # Registration (Donor vs Patient)
│       ├── donor_dashboard.html    # Donor Management Dashboard
│       ├── patient_dashboard.html  # Blood Request & Match Results Dashboard
│       └── admin_dashboard.html    # Administrator Console
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # Isolated Test Database & Client Fixtures
│   ├── test_auth.py                # Auth & Role Access Tests
│   ├── test_donor.py               # Donor Profile & Lifecycle Tests
│   ├── test_matching.py            # 7-Step Matching & Ranking Tests
│   ├── test_requests.py            # Blood Requests & Donor Acceptance Tests
│   ├── test_admin.py               # Admin Authorization & Sweep Tests
│   └── test_security.py            # SQL Injection & Password Protection Tests
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 5. Installation & Setup

### Step 1: Clone the Repository
```bash
git clone https://github.com/coderbaiii/HemoNexus.git
cd HemoNexus
```

### Step 2: Create and Activate a Virtual Environment
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Initialize Database and Seed Demo Accounts
```bash
python backend/init_db.py
```

### Step 5: Start the Flask Application
```bash
python backend/app.py
```
Open your browser and navigate to **`http://127.0.0.1:5000`**.

---

## 6. Pre-Seeded Demonstration Accounts

For ease of testing and evaluation, the database initialization script seeds three pre-configured accounts:

| Role | Email | Password | Description |
|---|---|---|---|
| **Admin** | `admin@hemonexus.org` | `Admin@123456` | Full platform oversight & verification sweep |
| **Donor** | `amitav.donor@example.com` | `Donor@1234` | O+ Active Donor (Salt Lake, Kolkata, 24h) |
| **Patient** | `patient.raj@example.com` | `Patient@1234` | Patient with active O+ urgent request |

---

## 7. REST API Reference

### Authentication (`/api/...`)
- `POST /api/register` &mdash; Create account as `donor` or `patient` (admin self-registration is blocked).
- `POST /api/login` &mdash; Authenticate with email and password, establishing session.
- `POST /api/logout` &mdash; Terminate user session.
- `GET /api/me` &mdash; Retrieve current authenticated user and linked profile.

### Donor Operations (`/api/donor/...`)
- `GET /api/donor/profile` &mdash; Get logged-in donor profile and 6-month verification details.
- `POST /api/donor/profile` &mdash; Update availability schedule, location, GPS, or travel limit.
- `POST /api/donor/profile/verify` &mdash; Donor self-confirmation resetting status to `ACTIVE` for 180 days.
- `GET /api/donor/status` &mdash; Inspect lifecycle countdown and grace period days.
- `GET /api/donor/requests` &mdash; View incoming blood donation invitations.
- `POST /api/donor/requests/<id>/accept` &mdash; Accept donation request.
- `POST /api/donor/requests/<id>/reject` &mdash; Decline donation request with optional note.

### Patient Operations (`/api/patient/...`)
- `GET /api/patient/profile` &mdash; View patient profile.
- `POST /api/patient/blood-requests` &mdash; Create requirement-based blood request.
- `GET /api/patient/blood-requests` &mdash; List own blood requests.
- `GET /api/patient/blood-requests/<id>` &mdash; View single request details and responses.
- `GET /api/patient/blood-requests/<id>/matches` &mdash; Execute 7-step matching engine and retrieve ranked donors.
- `POST /api/patient/blood-requests/<id>/send-request` &mdash; Dispatch request to a candidate donor (duplicates prevented).
- `PATCH /api/patient/blood-requests/<id>/cancel` &mdash; Cancel blood request.
- `PATCH /api/patient/blood-requests/<id>/fulfill` &mdash; Mark blood request as fulfilled.

### Admin Operations (`/api/admin/...`)
- `GET /api/admin/stats` &mdash; Platform summary metrics and active/inactive counts.
- `GET /api/admin/donors` &mdash; Donor directory with filter (`?status=ACTIVE|VERIFICATION_DUE|INACTIVE`).
- `GET /api/admin/users` &mdash; Complete user accounts list.
- `GET /api/admin/blood-requests` &mdash; System-wide blood requirements.
- `GET /api/admin/responses` &mdash; Donor dispatch and response audit logs.
- `POST /api/admin/verify-check` &mdash; Trigger batch sweep of 6-month donor verification statuses.
- `PATCH /api/admin/donors/<id>/status` &mdash; Administrative override of donor status.

---

## 8. Running Automated Tests

Run the full pytest suite:
```bash
python -m pytest tests/ -v
```
All tests run against isolated temporary databases and verify:
- Registration, duplicate checks, login, password security, session persistence
- Donor profile creation, update, and 6-month verification lifecycle
- 7-step matching engine filtering, inactive exclusion, and composite ranking
- Patient request creation, donor dispatch, duplicate rejection, and accept/reject flows
- Admin role-based access restrictions and verification sweeps
- SQL injection resistance and password protection

---

## 9. Security & Medical Disclaimer

- **Password Protection**: Passwords are saved exclusively as salted hashes using Werkzeug. Plaintext passwords or hashes are never exposed via APIs.
- **SQL Security**: All database interactions use strictly parameterized queries.
- **Medical Disclaimer**: HEMONEXAS provides smart operational matching and availability tracking. The platform does not certify donors as medically disease-free. Laboratory cross-matching and blood release are performed strictly by authorized blood banks.
