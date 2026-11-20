# Cinema Reservation System — Project Progress Tracker

> **Mục đích:** Theo dõi các giai đoạn, công việc, tiến độ và trạng thái hoàn thành của dự án Cinema Reservation System.  
> **Deadline:** 29/11/2026 — 23:59 KST  
> **Presentation:** 01/12 hoặc 03/12/2026  
> **Tech Stack:** Python, Flask, PostgreSQL, HTML, CSS, JavaScript

---

## 1. Project Overview

| Thông tin | Nội dung |
|---|---|
| Project | Cinema Reservation System |
| Database | PostgreSQL |
| Backend | Python + Flask |
| Database Lead | Member A |
| Application Lead | Member B |
| Database scope | Schema, constraints, triggers, seed data, integrity tests |
| Application scope | Flask backend, frontend, business logic, integration |
| Final deliverables | Source code, database, documentation, presentation |

### Overall Progress

- [x] Requirements and business analysis
- [x] Business documentation
- [x] Database design and implementation
- [ ] Database validation and handover *(verified by tests 20/11; waiting for Member A's review — see 3.3)*
- [ ] Flask application foundation
- [ ] Backend implementation
- [ ] Frontend implementation
- [ ] Database–application integration
- [ ] System testing and bug fixing
- [ ] Final documentation
- [ ] Presentation preparation
- [ ] Final submission

---

## 2. Phase 1 — Requirements & Business Analysis

**Mục tiêu:** Xác định phạm vi, chức năng và các quy tắc nghiệp vụ của hệ thống.

- [x] Define project overview — B01
- [x] Define business functions — B02
- [x] Write unit business descriptions — B03
- [x] Create business flowcharts — B04
- [x] Create business document list — B05
- [x] Define business rules BR-01 to BR-15
- [x] Create business decision log BR-DL-001
- [x] Finalize decisions D1–D6
- [x] Confirm PostgreSQL as the official DBMS
- [x] Confirm Flask as the application framework

**Deliverable:** `docs/business/`

**Status:** Completed

---

## 3. Phase 2 — Database Design & Implementation

**Owner:** Member A — Database Lead

**Mục tiêu:** Xây dựng PostgreSQL database đáp ứng toàn bộ business requirements và D1–D6.

### 3.1 Initial Database Handover

- [x] Receive Member A's PostgreSQL handover
- [x] Inspect schema.sql
- [x] Inspect seed.sql
- [x] Inspect verify.sql
- [x] Inspect database integrity tests
- [x] Inspect concurrency tests
- [x] Inspect ERD files and database documentation
- [x] Execute initial database validation
- [x] Compare database implementation against D1–D6
- [x] Identify mismatches and additional unapproved rules

### 3.2 Database Reconciliation

- [x] Create database reconciliation report
- [x] Create Flask integration contract
- [x] Create reconciliation probes
- [x] Add missing movie attributes: genre, rating, release_date *(free text / date, nullable, no ENUM)*
- [x] Add screening end time *(`showtimes.ends_at`, stored)*
- [x] Implement booking statuses: BOOKED, CANCELLED, EXPIRED
- [x] Implement payment statuses: UNPAID, PAID
- [x] Implement booking expiration using expires_at *(= booked_at + 10 min)*
- [x] Implement atomic and idempotent expiration operation *(`expire_overdue_bookings()`, request-time, no scheduler)*
- [x] Preserve booking history after cancellation and expiration
- [x] Implement total_amount in BOOKINGS
- [x] Implement per-seat price snapshot in BOOKING_SEATS
- [x] Enforce screening modification restrictions under D2 *(incl. ticket_price and end time)*
- [x] Remove unapproved 15-minute cleaning buffer
- [x] Remove unapproved movie-duration editing restriction
- [x] Update seed data *(3 / 5 / 5 / 250 / 140; demo values)*
- [x] Update database integrity tests *(`integrity_tests.sql`, 177 checks)*
- [x] Add D1–D6 reconciliation tests *(`reconciliation_probes.sql`, 31 MATCH / 0 MISMATCH)*
- [x] Add concurrency tests for payment and expiration *(`test_concurrency.py`, 16 checks)*
- [x] Regenerate ERDs *(Mermaid ERDs in `docs/database/`; Member A's old drawio/PNG/SVG are stale and not regenerated)*
- [x] Update database documentation

### 3.3 Database Validation & Handover

- [x] Apply schema.sql to a clean PostgreSQL database
- [x] Apply seed.sql successfully
- [x] Verify all expected records
- [x] Verify all PK/FK/CHECK/UNIQUE constraints
- [x] Verify all triggers and database functions
- [x] Verify D1–D6
- [x] Verify concurrent booking behavior
- [x] Verify payment and expiration behavior
- [x] Verify cancellation and seat release behavior
- [x] Confirm no unexpected business rules remain *(buffer and duration lock removed; remaining technical limits — duration 1–300, seat rows A–E / numbers 1–10 — are documented in `domain_definition.md`)*
- [ ] Obtain Member A's database review *(Member A has not yet reviewed the canonical `database/schema.sql`)*
- [x] Confirm database is ready for Flask integration *(by verification; subject to Member A's review)*

**Verification (20/11/2026, PostgreSQL 18.6, disposable database, `bash database/tests/run_all.sh`):**
schema OK · seed OK · integrity **177/177** · probes **31 MATCH, 0 MISMATCH** · concurrency **16/16** · `ALL DATABASE TESTS PASSED`. PostgreSQL 14–17 not tested.

**Deliverables:**
- `database/schema.sql`
- `database/seed.sql`
- `database/tests/` (`integrity_tests.sql`, `reconciliation_probes.sql`, `test_concurrency.py`, `run_all.sh`)
- `docs/database/` (contract, reconciliation report, test documentation, data-model documents)
- `CinemaDB_FINAL_PostgreSQL_Handover/` — Member A's original delivery, kept unchanged as history

**Status:** Implemented and verified — waiting for Member A's review.

---

## 4. Phase 3 — Flask Application Foundation

**Owner:** Member B — Application Lead

**Mục tiêu:** Chuẩn bị cấu trúc Flask và kết nối PostgreSQL sau khi database đạt điều kiện tích hợp.

- [ ] Review final PostgreSQL schema
- [ ] Review PostgreSQL–Flask integration contract
- [ ] Select and confirm PostgreSQL Python driver
- [ ] Configure Python virtual environment
- [ ] Configure requirements.txt
- [ ] Configure Flask application entry point
- [ ] Configure environment variables
- [ ] Configure PostgreSQL connection
- [ ] Implement database connection management
- [ ] Implement transaction management
- [ ] Implement application configuration
- [ ] Verify Flask can connect to PostgreSQL
- [ ] Verify basic database queries through Flask

**Deliverables:**
- `app/__init__.py`
- `app/config.py`
- `app/db.py`
- `requirements.txt`
- `.env.example`

**Status:** Not Started — **unblocked** (database reconciliation completed 20/11/2026). Follow `docs/database/postgresql_flask_integration_contract.md`; confirm the driver (`psycopg2-binary` recommended) before editing `requirements.txt`.

---

## 5. Phase 4 — Backend Implementation

**Owner:** Member B — Application Lead

**Mục tiêu:** Triển khai các chức năng nghiệp vụ bằng Flask.

### 5.1 Authentication & Account

- [ ] Customer registration
- [ ] Customer login
- [ ] Logout
- [ ] Password hashing and verification
- [ ] Session management
- [ ] Admin authentication and authorization

### 5.2 Movie & Screening

- [ ] Retrieve movie list
- [ ] Retrieve movie details
- [ ] Retrieve screening schedules
- [ ] Retrieve screening details
- [ ] Retrieve available seats
- [ ] Admin: Add movie
- [ ] Admin: Update movie
- [ ] Admin: Add screening
- [ ] Admin: Update screening

### 5.3 Booking & Payment

- [ ] Select multiple seats
- [ ] Validate selected seats
- [ ] Require login before booking confirmation
- [ ] Create booking
- [ ] Calculate total amount
- [ ] Save per-seat price snapshots
- [ ] Implement simulated payment
- [ ] Prevent payment after expiration
- [ ] Implement request-time booking expiration
- [ ] Release seats after expiration
- [ ] Retrieve customer booking history
- [ ] Cancel customer booking
- [ ] Release seats after cancellation
- [ ] Preserve cancelled and expired booking history

### 5.4 Admin Functions

- [ ] View all bookings
- [ ] Restrict admin-only functions
- [ ] Prevent customer access to admin functions

**Status:** Not Started

---

## 6. Phase 5 — Frontend Implementation

**Owner:** Member B — Application Lead

**Mục tiêu:** Xây dựng giao diện người dùng cho Customer và Admin.

### 6.1 Customer Interface

- [ ] Home page
- [ ] Movie list page
- [ ] Movie detail page
- [ ] Screening selection page
- [ ] Seat selection interface
- [ ] Booking confirmation page
- [ ] Simulated payment page
- [ ] Booking history page
- [ ] Booking cancellation interface
- [ ] Login page
- [ ] Registration page

### 6.2 Admin Interface

- [ ] Admin dashboard
- [ ] Movie management page
- [ ] Screening management page
- [ ] Booking management page

### 6.3 UI Validation

- [ ] Validate navigation between pages
- [ ] Validate forms and user input
- [ ] Display success and error messages
- [ ] Display booking and payment statuses
- [ ] Validate responsive layout
- [ ] Verify customer/admin access restrictions

**Status:** Not Started

---

## 7. Phase 6 — Database & Application Integration

**Mục tiêu:** Đảm bảo Flask hoạt động chính xác với PostgreSQL và toàn bộ business rules.

- [ ] Connect Flask to the final PostgreSQL database
- [ ] Verify all database queries
- [ ] Verify transaction boundaries
- [ ] Verify concurrent seat booking
- [ ] Verify duplicate seat prevention
- [ ] Verify screening overlap prevention
- [ ] Verify booking confirmation
- [ ] Verify payment processing
- [ ] Verify booking expiration
- [ ] Verify cancellation and seat release
- [ ] Verify booking history retention
- [ ] Verify screening modification restrictions
- [ ] Verify customer/admin permissions
- [ ] Verify all D1–D6 through application workflows

**Status:** Not Started

---

## 8. Phase 7 — System Testing & Bug Fixing

**Mục tiêu:** Kiểm tra toàn bộ hệ thống trước khi nộp.

### 8.1 Functional Testing

- [ ] Registration
- [ ] Login/logout
- [ ] Movie browsing
- [ ] Screening lookup
- [ ] Seat availability
- [ ] Multi-seat selection
- [ ] Booking confirmation
- [ ] Simulated payment
- [ ] Booking history
- [ ] Booking cancellation
- [ ] Booking expiration
- [ ] Admin movie management
- [ ] Admin screening management
- [ ] Admin booking management

### 8.2 Business Rule Testing

- [ ] D1 — Cancellation and history retention
- [ ] D2 — Screening modification restrictions
- [ ] D3 — Booking expiration and payment rules
- [ ] D4 — Public browsing and login requirement
- [ ] D5 — Account and movie attributes
- [ ] D6 — Ticket price and price snapshots

### 8.3 Final Validation

- [ ] Run all automated tests
- [ ] Test complete customer workflow
- [ ] Test complete admin workflow
- [ ] Fix critical bugs
- [ ] Fix UI and validation bugs
- [ ] Re-run regression tests
- [ ] Confirm application starts from a clean setup

**Status:** Not Started

---

## 9. Phase 8 — Documentation & Presentation

**Mục tiêu:** Hoàn thiện tài liệu và chuẩn bị demo.

### 9.1 Documentation

- [ ] Finalize database schema documentation
- [ ] Finalize ERD
- [ ] Finalize database setup instructions
- [ ] Finalize application setup instructions
- [ ] Document environment variables
- [ ] Document demo accounts and credentials securely
- [ ] Document system architecture
- [ ] Document major business workflows
- [ ] Prepare test results

### 9.2 Presentation

- [ ] Prepare project introduction
- [ ] Explain system architecture
- [ ] Present ERD and database design
- [ ] Explain important database constraints and triggers
- [ ] Demonstrate customer workflow
- [ ] Demonstrate admin workflow
- [ ] Demonstrate booking, payment, cancellation and expiration
- [ ] Prepare screenshots
- [ ] Prepare presentation slides
- [ ] Rehearse the presentation
- [ ] Prepare backup demo data

**Status:** Not Started

---

## 10. Phase 9 — Final Submission

**Deadline:** 29/11/2026 — 23:59 KST

- [ ] Verify complete source code
- [ ] Verify database scripts
- [ ] Verify documentation
- [ ] Verify requirements.txt
- [ ] Verify setup instructions
- [ ] Remove unnecessary files
- [ ] Check for exposed passwords or secrets
- [ ] Test project setup from a clean environment
- [ ] Verify submission structure
- [ ] Submit before deadline
- [ ] Prepare for presentation on 01/12 or 03/12

**Status:** Not Started

---

## 11. Current Project Status

| Phase | Status | Owner |
|---|---|---|
| 1. Requirements & Business Analysis | Completed | Member A + B |
| 2. Database Design & Implementation | Implemented & verified — awaiting Member A's review | Member A (+ B for reconciliation) |
| 3. Flask Application Foundation | Ready to start (unblocked) | Member B |
| 4. Backend Implementation | Not Started | Member B |
| 5. Frontend Implementation | Not Started | Member B |
| 6. Database–Application Integration | Not Started | Member B |
| 7. System Testing | Not Started | Member A + B |
| 8. Documentation & Presentation | Not Started | Member A + B |
| 9. Final Submission | Not Started | Member A + B |

### Current Blocking Issue

**None for Flask development.** The database now satisfies D1–D6 and passed all executed tests (see 3.3). The original handover in `CinemaDB_FINAL_PostgreSQL_Handover/` is outdated — do not code against it; use `database/schema.sql` and the integration contract.

**Next priority:** start Phase 3 (Flask foundation), and get Member A's review of the canonical database.

### Open Items and Decisions

| Item | Owner | Note |
|---|---|---|
| Member A's review of canonical `database/schema.sql` | Member A | Only remaining step of Phase 2 |
| Demo account passwords | A or B | The three seeded accounts keep A's hashes; plaintext is unknown/unverified and is documented nowhere. Set known passwords before any login demo |
| PostgreSQL driver / `requirements.txt` | A + B | `psycopg2-binary` recommended; `requirements.txt` still empty |
| Application DB role privileges (`SECURITY DEFINER` or not) | Member A | Functions run with caller privileges; not implemented |
| Is `expires_at` allowed after screening start? | Project owner | Not specified in B01–B05; no rule invented (booking allowed until start; expiry still works after start) |
| Genre / rating / release_date mandatory? | Project owner | Currently nullable free text; no vocabulary approved |
| Regenerate drawio/PNG ERDs for the presentation | Member A | Mermaid ERDs exist in `docs/database/`; A's old ERDs show the outdated model |
| PostgreSQL 14–17 compatibility | Member A / B | Tested on 18.6 only |

**Reminder for Phase 4:** Flask must call `expire_overdue_bookings()` (request-time expiry) before seat availability, booking history and admin booking lists; `create_booking`, `pay_booking` and `cancel_booking` already expire what they need. Nothing expires by itself.

---

## 12. Progress Update Log

Use this section to record significant project changes.

| Date | Update | Status |
|---|---|---|
| 17/11/2026 | Approved BR-DL-001 and decisions D1–D6 | Completed |
| 20/11/2026 | Officially switched DBMS from SQLite to PostgreSQL | Completed |
| 20/11/2026 | Audited Member A's PostgreSQL handover | Completed |
| 20/11/2026 | Created reconciliation report and Flask integration contract | Completed |
| 20/11/2026 | Implemented database corrections in canonical `database/schema.sql` and `database/seed.sql` (D2 price protection, booking/payment statuses, expiry, totals and price snapshots, stored end time, movie attributes; removed unapproved 15-minute buffer and duration lock) | Completed |
| 20/11/2026 | Added `integrity_tests.sql` (177), updated `reconciliation_probes.sql` (31 MATCH, 0 MISMATCH), added `test_concurrency.py` (16) and `run_all.sh`; all passed on PostgreSQL 18.6 disposable database | Completed |
| 20/11/2026 | Filled `docs/database/` model documents (with Mermaid ERDs), rewrote Flask integration contract, updated reconciliation report and `database/README.md`, added database test documentation | Completed |
| 20/11/2026 | Database declared ready for Flask integration; waiting for Member A's review | Pending (A's review) |

Add a new row whenever a major milestone is completed.

---

## 13. Rules for Maintaining This Checklist

1. Mark a task `[x]` only after its implementation or deliverable has been verified.
2. Use `[ ]` for tasks that have not started or are not completed.
3. Do not mark a whole phase as Completed while critical tasks remain.
4. Update the progress log after major changes.
5. Keep the checklist consistent with the actual repository state.
6. Do not treat a successful test as proof that untested business requirements are satisfied.
7. Do not begin a dependent phase while its blocking requirements remain unresolved.
8. Preserve approved business requirements and decisions unless the team formally changes them.
