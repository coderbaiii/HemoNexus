# HEMONEXAS &mdash; Backend REST API & Smart Matching Engine

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1%2B-red.svg)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/SQLite-3-lightgrey.svg)](https://www.sqlite.org/)
[![Branch](https://img.shields.io/badge/Branch-backend--only-green.svg)]()

> **Project Team (Team Egnima):**  
> Arunima Ghosh &bull; Debriddhi Ghosh &bull; Baivabi Chakraborty &bull; Udipta Dhara

---

## 1. Overview (Backend Branch)

This branch (`backend`) contains the dedicated **backend services, SQLite relational schema, 7-step requirement-based matching engine, 6-month verification lifecycle, REST APIs, and automated test suite** for the HEMONEXAS platform.

> [!NOTE]
> For the complete integrated application with frontend UI templates and static assets, switch to the **`main`** branch:  
> `git checkout main`

---

## 2. Backend Modules & Architecture

- **Core Application**: [`backend/app.py`](file:///C:/Users/udipt/.gemini/antigravity/scratch/HemoNexus/backend/app.py) &mdash; Factory pattern, error handlers, and Blueprint registration.
- **Database Connection & DDL**: [`backend/database.py`](file:///C:/Users/udipt/.gemini/antigravity/scratch/HemoNexus/backend/database.py) and [`backend/init_db.py`](file:///C:/Users/udipt/.gemini/antigravity/scratch/HemoNexus/backend/init_db.py) &mdash; Parameterized queries, `PRAGMA foreign_keys = ON;`, schema DDL, and demo accounts.
- **7-Step Smart Matching Engine**: [`backend/services/matching_service.py`](file:///C:/Users/udipt/.gemini/antigravity/scratch/HemoNexus/backend/services/matching_service.py) &mdash; Exact blood group matching, active status verification, availability time window matching, mutual distance checks via the Haversine formula, and composite weighted ranking.
- **6-Month Verification Lifecycle**: [`backend/services/verification_service.py`](file:///C:/Users/udipt/.gemini/antigravity/scratch/HemoNexus/backend/services/verification_service.py) &mdash; `ACTIVE` &rarr; `VERIFICATION_DUE` &rarr; `INACTIVE` state management, grace periods, and verification confirmation.
- **API Blueprints**:
  - `backend/routes/auth.py` &mdash; Authentication, password hashing, and session management.
  - `backend/routes/donor.py` &mdash; Donor profiles, availability, verification, and incoming requests.
  - `backend/routes/patient.py` &mdash; Blood requests, matching engine invocation, and donor dispatch.
  - `backend/routes/admin.py` &mdash; Platform metrics, donor directory oversight, and batch verification sweeps.
- **Automated Tests**: [`tests/`](file:///C:/Users/udipt/.gemini/antigravity/scratch/HemoNexus/tests/) &mdash; 36 automated pytest tests with 100% pass rate.

---

## 3. Quick Start

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Initialize Database
```bash
python backend/init_db.py
```

### Step 3: Run the Backend API Service
```bash
python backend/app.py
```
API Root: **`http://127.0.0.1:5000/`**

### Step 4: Run the Test Suite
```bash
python -m pytest tests/ -v
```

---

## 4. REST API Endpoint Reference

| Service | Method | Route | Description |
|---|---|---|---|
| **Auth** | `POST` | `/api/register` | User registration (`donor` / `patient`) |
| | `POST` | `/api/login` | Session login with email & password |
| | `POST` | `/api/logout` | Clears user session |
| | `GET` | `/api/me` | Current authenticated user |
| **Donor** | `GET` | `/api/donor/profile` | Donor profile & verification details |
| | `POST` | `/api/donor/profile` | Update availability, location, radius |
| | `POST` | `/api/donor/profile/verify` | 6-month verification confirmation |
| | `GET` | `/api/donor/requests` | Incoming blood donation invitations |
| | `POST` | `/api/donor/requests/<id>/accept` | Accept donation invitation |
| | `POST` | `/api/donor/requests/<id>/reject` | Decline donation invitation |
| **Patient** | `POST` | `/api/patient/blood-requests` | Create requirement blood request |
| | `GET` | `/api/patient/blood-requests` | List patient's requests |
| | `GET` | `/api/patient/blood-requests/<id>/matches` | Execute 7-step matching algorithm |
| | `POST` | `/api/patient/blood-requests/<id>/send-request` | Dispatch request to donor (duplicates blocked) |
| **Admin** | `GET` | `/api/admin/stats` | Platform statistics & lifecycle metrics |
| | `GET` | `/api/admin/donors` | List donors with status filter |
| | `POST` | `/api/admin/verify-check` | Execute 6-month verification sweep |
| | `PATCH` | `/api/admin/donors/<id>/status` | Administrative status override |
