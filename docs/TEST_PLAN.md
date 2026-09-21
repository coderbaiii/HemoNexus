# HEMONEXAS — Automated Test Plan
**Role:** Member 4 (Database + Testing)  
**Framework:** Pytest 9.x / Python 3.14  
**Coverage Scope:** Database CRUD, Constraints, Validation, 6-Month Verification Lifecycle, Matching DB Interaction, Security, API Routing, and End-to-End System Flows.

---

## 1. Test Strategy & Objectives

1. **Isolation:** Every test session and fixture spins up an independent, temporary SQLite database with freshly seeded demo data.
2. **Foreign Key Verification:** Ensure SQLite `PRAGMA foreign_keys = ON;` is enforced on every connection to prevent invalid states.
3. **No Medical Diagnostics:** Ensure all tests adhere to platform guidelines (operational search ranking only, no diagnostic logic).
4. **100% Automated Execution:** Execute all test suites via `pytest -v` across 74 automated test cases.

---

## 2. Test Modules

| Module | Test File | Target Scope |
| :--- | :--- | :--- |
| **Auth & Users** | `tests/test_auth.py` | Registration, login, password hashing, roles, duplicate emails |
| **Database CRUD** | `tests/test_database_crud.py` | Insert, Read, Update, Delete, Foreign Key cascades, Uniqueness |
| **Data Validation** | `tests/test_database_validation.py` | ABO/Rh validation, distance limits, units, email formats |
| **Lifecycle Verification** | `tests/test_lifecycle_verification.py` | 180-day cycle, grace period, due status, non-destructive sweep |
| **Matching DB Integration**| `tests/test_matching_db_integration.py`| Compatibility with Member 3's algorithm: group match, distance, radius |
| **Donation Records** | `tests/test_donation_records.py` | Blood bank donation logging, components (RBC, Platelets, Plasma) |
| **Donor Portal & Routes** | `tests/test_donor.py` | Profile updates, availability patterns, incoming invitations |
| **Patient Blood Requests**| `tests/test_requests.py` | Request creation, duplicate dispatches prevention, fulfillment |
| **Security & Isolation** | `tests/test_security.py` | SQL injection resistance, password privacy, cross-tenant protection |
| **Admin Oversight** | `tests/test_admin.py` | Role-based authorization, verification sweep triggers, metrics |
| **End-to-End System Flow** | `tests/test_end_to_end_integration.py`| Full scenario: Patient Request -> Algorithm -> Donor Accept -> Fulfill |
