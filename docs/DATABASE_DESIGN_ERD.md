# HEMONEXAS — Database Design & ER Information
**Project:** HEMONEXAS – Smart Blood Donor Management & Requirement-Based Matching System  
**Author:** Member 4 (Database + Testing)  

---

## 1. Architectural Principles

1. **Relational Integrity & Normalization:**
   - 3rd Normal Form (3NF) relational design.
   - Separation of user authentication (`users`) from operational domains (`donor_profiles`, `patient_profiles`).
   - Strict `FOREIGN KEY` cascades (`ON DELETE CASCADE`) to eliminate orphaned rows.
2. **Deterministic Lifecycle Modeling:**
   - Donors cycle through `ACTIVE` -> `VERIFICATION_DUE` -> `INACTIVE` states every 180 days.
   - Records are **never permanently deleted** upon inactivity, allowing profile re-confirmation.
3. **Data Security & Privacy:**
   - Passwords stored as one-way PBKDF2/scrypt cryptographic hashes.
   - Exact coordinates filtered during general candidate searches; parameterized queries prevent SQL Injection.
   - Absolute exclusion of synthetic patient disease diagnostics / medical screening from the software layer.

---

## 2. Cardinality & Relationships

```
USERS (1) <---------- (1) DONOR_PROFILES
USERS (1) <---------- (1) PATIENT_PROFILES
USERS (1) <---------- (N) BLOOD_REQUESTS
DONOR_PROFILES (1) <-- (N) DONOR_VERIFICATIONS
BLOOD_REQUESTS (1) <-- (N) DONOR_REQUEST_RESPONSES
USERS (1) <---------- (N) DONOR_REQUEST_RESPONSES
DONOR_PROFILES (1) <-- (N) DONATION_RECORDS
BLOOD_REQUESTS (1) <-- (N) DONATION_RECORDS (Optional 0..1)
```

| Relationship | Type | Parent | Child | Cascade Rule |
| :--- | :--- | :--- | :--- | :--- |
| User Profile | 1 : 1 | `users` | `donor_profiles` | `CASCADE` |
| Patient Profile | 1 : 1 | `users` | `patient_profiles` | `CASCADE` |
| Blood Requests | 1 : N | `users` | `blood_requests` | `CASCADE` |
| Verification Logs | 1 : N | `donor_profiles` | `donor_verifications` | `CASCADE` |
| Dispatch Invitation | 1 : N | `blood_requests` | `donor_request_responses` | `CASCADE` |
| Donor Contact | 1 : N | `users` | `donor_request_responses` | `CASCADE` |
| Donation Records | 1 : N | `donor_profiles` | `donation_records` | `CASCADE` |
| Fulfillment Link | 1 : N | `blood_requests` | `donation_records` | `SET NULL` |
