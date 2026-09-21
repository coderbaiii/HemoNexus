# HEMONEXAS — Integration Test Report
**Author:** Member 4 (Database + Testing)  
**Scope:** Integration between Frontend APIs (Member 1), Flask Backend (Member 2), Matching Algorithm (Member 3), and Database Architecture (Member 4).

---

## 1. End-to-End Integration Architecture

The HEMONEXAS workflow operates seamlessly across all architectural layers:

```
[ Frontend Client (UI / JSON API) ]
                |
                v
[ Flask Backend (Blueprints & Auth Sessions) ]
                |
                +---> [ Database Validation & Service Layer ]
                |                    |
                |                    v
                |         [ SQLite Database (PRAGMA foreign_keys = ON) ]
                |
                +---> [ 7-Step Requirement Matching Engine ]
                                     |
                                     v
                        [ Haversine Distance + Availability + 180d Freshness ]
```

---

## 2. Tested Integration Scenarios

1. **Patient Emergency Requirement Workflow:**
   - Patient posts requirement (`POST /api/patient/blood-requests`).
   - Flask validates ABO/Rh blood group and stores request in `blood_requests`.
   - Backend queries `donor_profiles` filtered by `profile_status = 'ACTIVE'` and blood compatibility.
   - Matching algorithm evaluates availability schedules, GPS Haversine distance within search radius, and 180-day verification recency score.
   - Ranked donor candidates are returned to the frontend.

2. **Dispatch & Acceptance Workflow:**
   - Patient sends targeted dispatch to matching donor (`POST /api/patient/blood-requests/<id>/send-request`).
   - SQLite enforces `UNIQUE(blood_request_id, donor_id)` to block duplicate invitations.
   - Donor authenticates, inspects incoming invitations (`GET /api/donor/requests`), and accepts (`POST /api/donor/requests/<id>/accept`).
   - Blood request state transitions from `OPEN` to `MATCHING`.

3. **Blood Release & Donation Recording:**
   - Upon completion, blood center logs the unit into `donation_records` (specifying whole blood, RBC, platelets, or plasma).
   - Linked request is marked as `FULFILLED`.

4. **Continuous 6-Month Verification Sweep:**
   - Admin triggers automated sweep (`POST /api/admin/donors/verify-check`).
   - Profiles approaching 180 days transition to `VERIFICATION_DUE`.
   - Profiles beyond 30-day grace period transition to `INACTIVE` (automatically excluded from matching queries without account deletion).
   - Inactive donor re-confirming profile restores status to `ACTIVE`.

---

## 3. Integration Verdict

* **All 74 Automated Tests Passed.**
* **Zero Cross-Member Regressions.**
* **Database performance verified with full index coverage.**
