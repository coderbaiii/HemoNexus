# HEMONEXAS — Test Case Specification & Matrix
**Project:** HEMONEXAS  
**Responsible Team Member:** Member 4 (Database + Testing)  
**Total Test Cases:** 74  
**Passing Rate:** 100% (74 Passed, 0 Failed)  

---

## Complete Test Case Matrix

| Test Case ID | Module | Description | Precondition | Input | Expected Result | Actual Result | Status | Remarks |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-AUTH-001** | Auth | Register valid donor | DB initialized | Valid donor JSON | User & donor profile created (201) | User created | **PASS** | Auto-login verified |
| **TC-AUTH-002** | Auth | Register valid patient | DB initialized | Valid patient JSON | User & patient profile created (201) | User created | **PASS** | Profile created |
| **TC-AUTH-003** | Auth | Reject duplicate email | Email exists | Duplicate email | 409 Conflict | Rejected with 409 | **PASS** | Unique constraint enforced |
| **TC-AUTH-004** | Auth | Prevent admin self-registration | Any user | `role: admin` | 403 Forbidden | 403 Returned | **PASS** | Admin privilege protected |
| **TC-AUTH-005** | Auth | Reject missing required fields | Any user | Missing email/name | 400 Bad Request | 400 Returned | **PASS** | Form validation passed |
| **TC-AUTH-006** | Auth | Reject invalid email format | Any user | `email: invalid-mail` | 400 Bad Request | 400 Returned | **PASS** | Regex validation passed |
| **TC-AUTH-007** | Auth | Login with valid credentials | User registered | Correct email & password | 200 OK + session created | 200 OK | **PASS** | Session active |
| **TC-AUTH-008** | Auth | Login with invalid password | User registered | Incorrect password | 401 Unauthorized | 401 Returned | **PASS** | Safe error response |
| **TC-AUTH-009** | Auth | Login with non-existent user | No account | Unregistered email | 401 Unauthorized | 401 Returned | **PASS** | Generic error returned |
| **TC-AUTH-010** | Auth | Retrieve current user `/api/me` | Authenticated | GET request | 200 OK with role & name | 200 OK | **PASS** | User payload correct |
| **TC-AUTH-011** | Auth | Logout session flow | Authenticated | POST `/api/logout` | Session cleared (200 OK) | Session cleared | **PASS** | Complete session destruction |
| **TC-AUTH-012** | Auth | Security helper functions | None | Module import | PBKDF2 hashing active | Hashes verified | **PASS** | Safe cryptographic hashing |
| **TC-DB-USER-001** | DB CRUD | User CRUD operations | DB initialized | Sourav Ganguly user data | Create, Read, Update, Delete work | All operations succeed | **PASS** | Full CRUD verified |
| **TC-DB-USER-002** | DB CRUD | Unique email constraint | User exists | Same email | Value Error / IntegrityError | Rejected | **PASS** | Constraint verified |
| **TC-DB-USER-003** | DB CRUD | Case-insensitive email uniqueness | User exists | Uppercase version of email | Value Error / IntegrityError | Rejected | **PASS** | NOCASE verified |
| **TC-DB-DONOR-001** | DB CRUD | Donor profile CRUD & FK cascade | User created | B+ Donor details | Profile created & cascade deleted | CASCADE verified | **PASS** | Zero orphaned rows |
| **TC-DB-REQ-001** | DB CRUD | Blood request CRUD & state | Patient exists | AB+ request for Ruby Hospital | Status transitions: OPEN -> MATCHING -> FULFILLED | Valid status cycle | **PASS** | Transition validated |
| **TC-DB-VER-001** | DB CRUD | Donor verification checkpoint log | Donor exists | Checkpoint flags (1, 1, 1, 1) | Verification row inserted & audited | Log verified | **PASS** | Audit trail active |
| **TC-DB-RESP-001**| DB CRUD | Request responses CRUD & unique | Req & Donor exist| PENDING invitation | Unique dispatch enforced; status update to ACCEPTED | Unique verified | **PASS** | Duplicate dispatch blocked |
| **TC-DB-DONREC-001**| DB CRUD | Donation record creation & query | Donor exists | Whole blood donation entry | Inserted with timestamp & blood centre | Record queryable | **PASS** | Query verified |
| **TC-VAL-BG-001** | Validation | Validate all 8 ABO/Rh blood types | Function call | A+, A-, B+, B-, AB+, AB-, O+, O- | All return True | All valid | **PASS** | 8 standard groups |
| **TC-VAL-BG-002** | Validation | Reject invalid blood types | Function call | C+, O*, XYZ, 123 | All return False | All rejected | **PASS** | Strict filtering |
| **TC-VAL-BG-003** | Validation | SQLite check constraint for blood | DB connection | Direct SQL insert `blood_group='INVALID'` | SQLite IntegrityError | IntegrityError | **PASS** | DB constraint enforced |
| **TC-VAL-ROLE-001**| Validation | Validate user roles | Function call | donor, patient, admin vs superadmin | Valid roles pass, others fail | Validated | **PASS** | Role boundary checked |
| **TC-VAL-STAT-001**| Validation | Validate donor lifecycle statuses | Function call | ACTIVE, VERIFICATION_DUE, INACTIVE | Valid pass, others fail | Validated | **PASS** | 4 valid states |
| **TC-VAL-DIST-001**| Validation | Validate positive travel distance | Function call | 15.0 vs -10 vs 0 | Positive passes, negative/0 fails | Validated | **PASS** | Numeric range valid |
| **TC-VAL-UNIT-001**| Validation | Validate blood units | Function call | 2 units vs 0 vs -1 | Positive int passes, non-positive fails | Validated | **PASS** | Safe quantity bounds |
| **TC-VAL-EMAIL-001**| Validation | Validate email address syntax | Function call | valid@test.com vs invalid | Regex match | Regex valid | **PASS** | RFC compliant syntax |
| **TC-VAL-REQ-001** | Validation | Missing required user fields | Function call | Empty full_name or short password | ValueError | ValueError | **PASS** | Field presence verified |
| **TC-VAL-FK-001** | Validation | Donor with non-existent user_id | DB connection | `user_id = 99999` | ValueError | ValueError | **PASS** | FK parent check |
| **TC-VAL-FK-002** | Validation | Donation record invalid donor | DB connection | `donor_id = 99999` | ValueError | ValueError | **PASS** | FK parent check |
| **TC-DONREC-001** | Donation | Create valid whole blood donation | Donor exists | SSKM Hospital donation | Record created (COMPLETED) | Created | **PASS** | Component logged |
| **TC-DONREC-002** | Donation | Validate donation components | Donor exists | WHOLE_BLOOD, RBC, PLATELETS, PLASMA | Valid components pass | Validated | **PASS** | Component enum valid |
| **TC-DONREC-003** | Donation | Link donation to blood request | Req & Donor exist| Link to fulfilled request | Foreign key queryable | Linked | **PASS** | Traceability ensured |
| **TC-DONOR-001** | Donor | View donor profile & verification | Donor logged in | GET `/api/donor/profile` | 200 OK + profile telemetry | 200 OK | **PASS** | Telemetry payload |
| **TC-DONOR-002** | Donor | Update donor profile | Donor logged in | Updated location & radius | 200 OK + updated record | 200 OK | **PASS** | Persistence verified |
| **TC-DONOR-003** | Donor | Reject invalid blood update | Donor logged in | `blood_group: Z+` | 400 Bad Request | 400 Returned | **PASS** | API validation passed |
| **TC-DONOR-004** | Donor | Re-verify profile freshness | Donor logged in | POST `/api/donor/profile/verify` | Reset status to ACTIVE for 180 days | ACTIVE status set | **PASS** | Date updated |
| **TC-DONOR-005** | Donor | Compute lifecycle status | Helper call | 60 days ahead vs expired | Correct enum status | Status correct | **PASS** | Time calculation valid |
| **TC-DONOR-006** | Donor | Sweep preserves inactive accounts | DB initialized | Trigger verification sweep | Zero accounts deleted | Accounts kept | **PASS** | Retention confirmed |
| **TC-DONOR-007** | Donor | Schema preserves existing users | Existing legacy DB | Run `init_database(seed=False)` | Existing user row untouched | User preserved | **PASS** | Migration safety |
| **TC-VER-001** | Verification | Status within 180 days | Within cycle | `next_verification_date` > now | Status remains ACTIVE | ACTIVE | **PASS** | Lifecycle baseline |
| **TC-VER-002** | Verification | Verification due in grace window | 185 days old | Overdue within 30-day grace | Status becomes VERIFICATION_DUE | VERIFICATION_DUE | **PASS** | Grace window entered |
| **TC-VER-003** | Verification | Expiration beyond grace period | 220 days old | Overdue beyond grace window | Status becomes INACTIVE | INACTIVE | **PASS** | Excluded from search |
| **TC-VER-004** | Verification | Profile confirmation workflow | Status DUE | Call `refresh_donor_verification` | Status resets to ACTIVE | ACTIVE | **PASS** | 180-day cycle reset |
| **TC-VER-005** | Verification | Inactive donor reactivation | Status INACTIVE | Inactive donor updates profile | Status restored to ACTIVE | ACTIVE | **PASS** | Non-destructive reactivate |
| **TC-VER-006** | Verification | Sweep updates without deleting | DB initialized | Run sweep across registry | Record count identical before/after | Record count kept | **PASS** | Deletion prevention |
| **TC-MATCH-001** | Matching | Correct blood group included | Request O+ | Donor is O+ | Donor returned in candidates | Included | **PASS** | Group matching rule |
| **TC-MATCH-002** | Matching | Wrong blood group excluded | Request B+ | Donor is A+ | Donor excluded from candidates | Excluded | **PASS** | Group rejection rule |
| **TC-MATCH-003** | Matching | Inactive donor excluded | Request O+ | Donor is INACTIVE | Donor excluded from candidates | Excluded | **PASS** | Freshness enforcement |
| **TC-MATCH-004** | Matching | Unavailable timing excluded | Night request | Donor is DAYTIME only | Donor excluded from candidates | Excluded | **PASS** | Schedule compatibility |
| **TC-MATCH-005** | Matching | Beyond patient radius excluded | Radius 5 km | Donor 20 km away | Donor excluded from candidates | Excluded | **PASS** | Search radius rule |
| **TC-MATCH-006** | Matching | Beyond donor travel excluded | Radius 50 km | Donor max travel 2 km | Donor excluded from candidates | Excluded | **PASS** | Mutual travel limit |
| **TC-MATCH-007** | Matching | Rank multiple eligible donors | Multiple O+ | Different distances & freshness | Sorted descending by match_score | Correctly ranked | **PASS** | Multi-factor ranker |
| **TC-MATH-001** | Matching | Haversine formula calculation | GPS coordinates| Salt Lake to Park Circus | Distance ~5.0 km | 5.0 km computed | **PASS** | Formula precision |
| **TC-MATH-002** | Matching | Availability pattern time check | Time slots | Daytime vs Nighttime hours | Correct boolean & score | Match score computed | **PASS** | Timing evaluation |
| **TC-MATH-003** | Matching | Verification recency score | Last verified date| Today vs 90 days ago | Score decays from 1.0 to 0.1 | Decay score valid | **PASS** | Freshness weight |
| **TC-MATH-004** | Matching | Matching engine filter pipeline | Request O+ | 5 candidate donor profiles | Filtered list with score breakdown | Breakdown computed | **PASS** | 7-step pipeline |
| **TC-REQ-001** | Requests | Patient create blood request | Patient logged in | O+ request for Apollo Hospital | 201 Created | 201 Created | **PASS** | Request open |
| **TC-REQ-002** | Requests | Prevent duplicate donor dispatch | Request created | Dispatch to same donor twice | 409 Conflict on 2nd attempt | 409 Returned | **PASS** | Duplicate prevented |
| **TC-REQ-003** | Requests | Donor accept dispatch invitation | Donor logged in | POST `/api/donor/requests/<id>/accept`| Request status -> MATCHING (200 OK)| Status MATCHING | **PASS** | Hospital notified |
| **TC-REQ-004** | Requests | Patient cancel blood request | Patient logged in | POST `/api/patient/blood-requests/<id>/cancel`| Status CANCELLED | Status CANCELLED | **PASS** | Dispatches cancelled |
| **TC-SEC-001** | Security | SQL Injection prevention in login | Unauthenticated | `' OR '1'='1` in email | 401 Unauthorized | 401 Returned | **PASS** | Parameterized queries |
| **TC-SEC-002** | Security | Passwords never plaintext in DB | DB inspection | Query user record | Hash string (pbkdf2/scrypt) | Hash verified | **PASS** | Zero plaintext leaks |
| **TC-SEC-003** | Security | Password hashes never in API JSON | API calls | Fetch user & donor profiles | JSON lacks password/hash keys | No hash keys | **PASS** | Field exclusion verified |
| **TC-SEC-004** | Security | Patient cross-tenant isolation | 2 Patients | Patient A attempts access to Patient B | 403 Forbidden | 403 Returned | **PASS** | Ownership enforced |
| **TC-ADM-001** | Admin | Unauthorized donor access blocked| Donor logged in | Access `/api/admin/stats` | 403 Forbidden | 403 Returned | **PASS** | RBAC enforced |
| **TC-ADM-002** | Admin | Unauthorized patient access blocked| Patient logged in | Access `/api/admin/donors` | 403 Forbidden | 403 Returned | **PASS** | RBAC enforced |
| **TC-ADM-003** | Admin | Unauthenticated admin access | Anonymous | Access `/api/admin/stats` | 401 Unauthorized | 401 Returned | **PASS** | Auth check enforced |
| **TC-ADM-004** | Admin | Fetch system-wide admin metrics | Admin logged in | GET `/api/admin/stats` | 200 OK with registry counters | 200 OK | **PASS** | Counters accurate |
| **TC-ADM-005** | Admin | List & filter donors by status | Admin logged in | GET `/api/admin/donors?status=ACTIVE` | Filtered donor registry list | Filtered list | **PASS** | Query filter verified |
| **TC-ADM-006** | Admin | Trigger 6-month verification sweep| Admin logged in | POST `/api/admin/donors/verify-check` | 200 OK + sweep summary stats | Sweep executed | **PASS** | Audit log recorded |
| **TC-ADM-007** | Admin | Admin override donor status | Admin logged in | PATCH `/api/admin/donors/<id>/status` | Status updated & audited | Status updated | **PASS** | Manual override works |
| **TC-E2E-001** | E2E System | Complete emergency dispatch flow | Full System | End-to-end user journey | Request -> Match -> Dispatch -> Accept -> Fulfill -> Record | 100% complete flow | **PASS** | Full system integrated |
