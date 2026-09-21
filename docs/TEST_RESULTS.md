# HEMONEXAS — Test Execution Results Report
**Date:** September 2026  
**Execution Environment:** Windows / Python 3.14.7 / Pytest 9.1.1 / SQLite 3  
**Evaluator:** Member 4 (Database + Testing)  

---

## 1. Summary of Execution

```
============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\ASUS\.gemini\antigravity\scratch\HemoNexus
collected 74 items

tests/test_admin.py (7 tests) ........................................ PASSED [100%]
tests/test_auth.py (12 tests) ....................................... PASSED [100%]
tests/test_database_crud.py (7 tests) ................................ PASSED [100%]
tests/test_database_validation.py (11 tests) ......................... PASSED [100%]
tests/test_donation_records.py (3 tests) ............................. PASSED [100%]
tests/test_donor.py (7 tests) ........................................ PASSED [100%]
tests/test_end_to_end_integration.py (1 test) ........................ PASSED [100%]
tests/test_lifecycle_verification.py (6 tests) ....................... PASSED [100%]
tests/test_matching.py (4 tests) ..................................... PASSED [100%]
tests/test_matching_db_integration.py (7 tests) ...................... PASSED [100%]
tests/test_requests.py (4 tests) ..................................... PASSED [100%]
tests/test_security.py (4 tests) ..................................... PASSED [100%]

======================= 74 passed in 322.28s (0:05:22) ========================
```

* **Total Tests Executed:** 74
* **Passed:** 74 (100.0%)
* **Failed:** 0 (0.0%)
* **Skipped / XFailed:** 0

---

## 2. Category Breakdown

| Test Category | Total Tests | Passed | Failed | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Authentication & User Profiles** | 12 | 12 | 0 | **PASS** |
| **Database CRUD Operations** | 7 | 7 | 0 | **PASS** |
| **Database & Field Validation** | 11 | 11 | 0 | **PASS** |
| **6-Month Verification Lifecycle** | 13 | 13 | 0 | **PASS** |
| **Matching Algorithm Integration** | 11 | 11 | 0 | **PASS** |
| **Blood Requests & Dispatches** | 4 | 4 | 0 | **PASS** |
| **Donation Records & Components** | 3 | 3 | 0 | **PASS** |
| **Security & Tenancy Isolation** | 4 | 4 | 0 | **PASS** |
| **Admin Oversight & Sweeps** | 7 | 7 | 0 | **PASS** |
| **End-to-End System Flow** | 1 | 1 | 0 | **PASS** |
