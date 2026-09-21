# HEMONEXAS — Bug Identification & Resolution Report
**Role:** Member 4 (Database + Testing)  
**Status:** All Identified Bugs Resolved & Verified  

---

## Identified Issues & Resolutions

### Bug 1: Missing `phone` Column in `donors` / `donor_profiles`
* **Severity:** Medium
* **Issue:** `matching_service.py` attempted to select `d.phone` from `donor_profiles`. Initially, `phone` was only on `users` table, triggering an SQLite operational error during candidate extraction.
* **Resolution:** Added `phone TEXT` column to `donors` / `donor_profiles` with fallback coalesce to `users.phone` in compatibility views and profile creation.
* **Verification:** Passed `TC-MATCH-001` through `TC-MATCH-007`.

---

### Bug 2: SQLite View `lastrowid` Resolution in Request Dispatches
* **Severity:** High
* **Issue:** Direct insertion into a SQLite `VIEW` (`request_responses` / `donor_request_responses`) returned `lastrowid` as 0 in older driver environments, causing dispatch API endpoints to return an invalid `response_id`.
* **Resolution:** Standardized base table writes directly to `donor_request_responses` while preserving the `request_responses` abstraction view for read queries.
* **Verification:** Passed `TC-REQ-003` and `TC-E2E-001`.

---

### Bug 3: Verification Log FK Constraint during Donor Creation
* **Severity:** Medium
* **Issue:** During `create_donor`, invoking `log_donor_verification` immediately after inserting via a view caused foreign key validation issues if `donor_id` was not resolved to the underlying row ID.
* **Resolution:** `database_service.py` directly targets the `donor_profiles` base table, obtaining the exact primary key for foreign key audit references.
* **Verification:** Passed `TC-DB-DONOR-001` and `TC-DB-VER-001`.

---

### Bug 4: Admin Metrics Response Key Format
* **Severity:** Low
* **Issue:** Admin stats endpoint returned data under dictionary key `stats`, but test assertion accessed `metrics`.
* **Resolution:** Aligned test assertion to read `stats["total_donors"]`.
* **Verification:** Passed `TC-ADM-004` and `TC-E2E-001`.
