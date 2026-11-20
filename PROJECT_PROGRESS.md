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
- [ ] Flask application foundation *(core implemented and verified 20/11; app database role pending Member A, documentation sync pending — see section 4)*
- [x] Phase 4 T1 — independent frontend + REST API foundation and test harness *(verified 20/11 — see section 4A)*
- [x] Phase 4 T2 — authentication API and frontend login/registration *(verified 20/11 — see section 4A)*
- [x] Phase 4 T3 — public catalog API (movies, schedules) and pages *(verified 20/11 — see section 4A)*
- [x] Phase 4 T4 — seat availability API and frontend seat picker *(verified 20/11 — see section 4A)*
- [x] Phase 4 T5 — booking creation and simulated payment API and pages *(verified 20/11 — see section 4A)*
- [x] Phase 4 T6 — customer booking history, details and cancellation API and pages *(verified 20/11 — see section 4A)*
- [ ] Phase 4 T7 — admin movie and screening API and pages *(implemented and covered by automated tests 20/11; **not ticked until the real-browser check in T9** — see section 4A)*
- [ ] Phase 4 T8 — admin booking list (view only) API and page *(implemented and covered by automated tests 20/11; **not ticked until the real-browser check in T9** — see section 4A)*
- [ ] Phase 4 T9–T11 — frontend validation pass, integration/E2E/security suite, deployment and separation demo *(not started)*
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

- [x] Review final PostgreSQL schema *(`schema.sql` and `seed.sql` applied to a clean PostgreSQL 18.6 database by the test fixture)*
- [x] Review PostgreSQL–Flask integration contract *(error mapping is checked automatically against contract section 6)*
- [ ] Select and confirm PostgreSQL Python driver *(project owner selected `psycopg2-binary` + direct parameterized SQL, no SQLAlchemy/ORM, 20/11; **Member A's agreement still pending**, see Open Items)*
- [x] Configure Python virtual environment *(`.venv/`, rebuilt from `requirements.txt` alone and checked with `pip check`)*
- [x] Configure requirements.txt *(Flask 3.1.3, psycopg2-binary 2.9.13, python-dotenv 1.2.4, tzdata 2026.6, pytest 9.2.0; `tzdata` is needed because Windows has no time zone database)*
- [x] Configure Flask application entry point *(`create_app()` factory; `flask --app app run`)*
- [x] Configure environment variables *(`DB_*`, `SECRET_KEY`, `APP_TIMEZONE` default `Asia/Seoul`, `FLASK_DEBUG`; documented in `.env.example`)*
- [x] Configure PostgreSQL connection
- [x] Implement database connection management *(`app/database.py`: one connection per request, always rolled back and closed)*
- [x] Implement transaction management *(`transaction()` context manager; `expire_overdue_bookings(cur)` helper)*
- [x] Implement application configuration *(`app/config.py`: development and testing configs, fail-fast validation)*
- [x] Verify Flask can connect to PostgreSQL *(real Flask server against a disposable PostgreSQL 18.6 instance: `/health/db` 200, then 503 with the database stopped, then 200 after restart)*
- [x] Verify basic database queries through Flask *(`SELECT 1`, seed record counts and real database errors through `get_db()` / `transaction()`)*
- [x] Error handling and health check *(`app/errors.py`, `app/health.py`: SQLSTATE mapping, safe responses, `/health`, `/health/db`)*
- [x] Automated tests *(352 tests: 293 need no server, 59 need a disposable PostgreSQL via explicit `TEST_DB_PORT`; all passed)*
- [ ] Application database role and privileges *(plan Task 7: **needs Member A's approval**; not started, no database permission was changed)*
- [ ] Documentation sync *(plan Task 8: hygiene tests, README setup instructions, driver decision record)*

**Deliverables:**
- `app/__init__.py`, `app/config.py`, `app/database.py` *(the connection module is `database.py`, not `db.py`)*, `app/errors.py`, `app/health.py`
- `requirements.txt`, `.env.example`, `pytest.ini`
- `tests/` (`conftest.py`, `disposable_db.py`, `fake_driver.py`, and tests for config, app factory, database fixture, connections, transactions, errors and health)

**How the tests run:** unit tests need no server. PostgreSQL tests require an explicit `TEST_DB_PORT` (plus optional `TEST_DB_HOST`, `TEST_DB_ADMIN_USER`, `TEST_DB_ADMIN_PASSWORD`); without it they are skipped and no connection is attempted. There is no fallback to `DB_PORT`, `PGPORT` or port 5432. The fixture creates and drops only databases named `cinema_test_*` that it created itself, and never connects to `DB_NAME`.

**Status:** In progress — **core implemented and verified (20/11/2026)**; Phase 3 is not marked completed until the application database role (needs Member A's approval) and the documentation sync are done, and Member A has confirmed the driver. Verified on PostgreSQL 18.6 only, using a disposable instance; the normal development database was never contacted.

---

## 4A. Phase 4 — Application Features (REST API + independent frontend)

**Owner:** Member B — Application Lead

**Plan:** the revised Phase 4 plan, tasks **T1–T11**. This section is the live checklist for it; sections 5–8 below keep the original feature checklists, which are ticked only when the matching task has been verified. (Do not confuse it with "Phase 4 — Integration & Testing, 28/11" in `chia_viec.md`.)

**Architecture (approved 20/11/2026).** Course requirement: *데이터베이스(백엔드 서버)와 클라이언트(웹/앱 프론트엔드)는 반드시 논리적, 물리적으로 분리된 아키텍처로 구현할 것.*

```
Browser ── static files ──► Frontend server :8080   frontend/server.py  (HTML, CSS, vanilla JS; no Flask, no DB)
   └────── JSON over HTTP ─► Flask REST API :5000   app/                (JSON only; no templates, no static files)
                                  └── PostgreSQL protocol ─► PostgreSQL :5432 (reachable by the API only)
```

Authentication is a **signed Bearer token** (no cookies, no CSRF, no cross-origin cookie problems); CORS allows **exact origins only** (no wildcard). The interface between the layers is [`docs/api/api_contract.md`](docs/api/api_contract.md). D1–D6 and the PostgreSQL integration contract are unchanged.

- [x] **T1 — Architecture split, REST foundation and test harness** *(verified 20/11/2026)*
  - [x] Spike A: per-test database clones from a session template (`CREATE DATABASE … TEMPLATE`): about 0.35 s to create and 0.08 s to drop; the ownership marker is *not* copied and is written again for every clone; a clone is refused while anything is connected to the template; only databases created by the current process can be a template or be dropped
  - [x] Spike A: owner-only time helpers `age_booking()` and `start_screening_in_past()` (+ `create_spare_room_screening()`): one transaction each, refuse any database that is not `cinema_test_*`, guarded triggers are verified enabled again even when the helper fails
  - [x] Spike B: Flask 404/405 (and every other HTTP error) now return the JSON error envelope; CORS preflight and denied origins verified; error responses carry the CORS headers
  - [x] Backend foundation: JSON provider (ISO 8601 with offset, money as string), `app/cors.py`, `app/security.py` (route-policy registry that stops startup if a route is unclassified, signed-token primitives, fail-closed role guard), `app/api.py` (`/api` skeleton, JSON body helper), new settings `CORS_ALLOWED_ORIGINS`, `AUTH_TOKEN_MAX_AGE_SECONDS` (default 8 h), 64 KiB request limit; static files and templates disabled
  - [x] Frontend foundation: `frontend/server.py` (standard library only; GET/HEAD only, allow-listed extensions, traversal-safe, CSP and security headers, `/config.js` generated from `API_BASE_URL`), `index.html`, `css/style.css`, `js/api.js`, `js/ui.js`, `js/pages/index.js`, dependency-free `package.json`
  - [x] `docs/api/api_contract.md` (checked against the code by `tests/test_api_contract.py`)
  - [x] Existing Phase 3 infrastructure reused unchanged (`database.py`, `health.py`, transactions, expiration helper, SQLSTATE map); the 352 earlier tests still pass
- [x] **T2 — Authentication API + login/register pages** *(verified 20/11/2026)*
  - [x] `POST /api/auth/register` (account ID `username` + password only; role always `CUSTOMER`, any role in the request ignored; duplicate → 409 through the existing SQLSTATE mapping), `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/logout`; contract updated (`docs/api/api_contract.md` sections 5–7, 11)
  - [x] Passwords: Werkzeug `pbkdf2:sha256:600000` (the method of the seeded hashes; seed-format and scrypt hashes verified); one identical `401 invalid_credentials` for an unknown account and a wrong password, with one dummy hash verification for every failure; only technical limits (account ID 1–60 characters = `users.username`, no control characters; password 1–256 characters); hashes, passwords and tokens never returned or logged
  - [x] Bearer token: `URLSafeTimedSerializer`, user id only, lifetime `AUTH_TOKEN_MAX_AGE_SECONDS` (default 8 h); signature and age checked, and the account (role included) **re-read from PostgreSQL on every authenticated request**: a deleted account answers 401 and a role change applies on the next request; 401 + `WWW-Authenticate: Bearer` / 403 as specified; new policy `authenticated`; route-policy registry kept
  - [x] Frontend: `login.html`, `register.html`, `js/auth.js` (token in `sessionStorage` via `api.js`, logout clears it first, 401 → login page, `?next=` accepted only for an allow-list of known pages), `js/nav.js`, `js/forms.js`; text-only rendering (no `innerHTML`)
  - [x] `scripts/set_demo_passwords.py`: setup-only tool for the seeded accounts, explicit `SETUP_DB_*` settings (no `DB_*` fallback, no defaults), prompt or `SETUP_NEW_PASSWORD`, one transaction, never prints a password or hash; creates no roles and changes no permissions
  - [x] Corrections to the T1 draft of the contract: logout is **public** (B03 CM-02: logging out while not logged in is not an error), policy `authenticated` for `/me`, error code `invalid_credentials` (B03 CM-01)
- [x] **T3 — Catalog API (movies, schedules) + pages** *(verified 20/11/2026; real-browser check of the pages is part of T9)*
  - [x] Public, no login (D4): `GET /api/movies`, `/api/movies/{id}`, `/api/screenings?movie_id&date`, `/api/screenings/{id}`; the six approved movie attributes (B03 "duration" = `duration_minutes`); schedule = screenings that **start** on one calendar day of the cinema's time zone (half-open `[00:00, next 00:00)`, default day = today decided by the database); strict `YYYY-MM-DD`; unknown movie 404, bad parameters 400 with `fields`; `has_started` from the database clock (display only; BR-12 stays enforced by the database)
  - [x] New `app/params.py` (id guard + query readers). A huge path id is harmless in a comparison but makes a bigint *function* call (`pay_booking`, `cancel_booking`) fail, so every id above the bigint range is a 404 up front (checked against the real database)
  - [x] Pages: `movies.html`, `movie.html?id=`, `screenings.html?date=`, `js/format.js` (money as an exact decimal string, times shown exactly as the API wrote them: no `Date`/`Intl`, so the display cannot depend on the browser's time zone), `js/catalog.js` (text-only builders, links only from validated ids); nav links; home-page links; next-page allow-list extended
  - [x] `tests/test_access_matrix.py`: every route x {anonymous, customer, admin} derived from the route-policy registry, so every later route is checked automatically; contract tests now compare normalised path placeholders in both directions
- [x] **T4 — Seat availability API + seat picker** *(verified 20/11/2026)*
  - [x] `GET /api/screenings/{id}/seats` (public, policy `public`), runs `expire_overdue_bookings(cur)` in same transaction
  - [x] Contract query: room's 50 seats with exact availability based on active `BOOKED` bookings (paid or within payment window)
  - [x] Frontend: `seats.html`, `js/seats.js`, `js/pages/seats.js`, CSS grid with available/selected/occupied states, estimated total
  - [x] Provisional seat selection without reserving seats; preserved across login redirect via `loginUrl` / query parameters
- [x] **T5 — Booking and simulated payment API + pages** *(verified 20/11/2026)*
  - [x] `POST /api/bookings` (policy `customer`), calls `create_booking()`, returns 201 with booking and per-seat price snapshots
  - [x] `POST /api/bookings/{id}/pay` (policy `customer`), calls `pay_booking()`, returns 200 with outcome `PAID` or `EXPIRED`
  - [x] Trust PostgreSQL for pricing, totals, deadlines and concurrency (handles `UC002` seat conflict, `UC004` started screening)
  - [x] Frontend: `booking.html`, `js/pages/booking.js`, live 10-minute countdown timer, simulated payment button, expiration handling
- [x] **T6 — Booking history and cancellation API + pages** *(verified 20/11/2026)*
  - [x] `GET /api/bookings` (policy `customer`), runs expiry first, returns all customer bookings ordered by `booked_at DESC`
  - [x] `GET /api/bookings/{id}` (policy `customer`), returns booking detail, runs expiry first, enforces ownership (404 for others)
  - [x] `POST /api/bookings/{id}/cancel` (policy `customer`), calls `cancel_booking()`, preserves parent record and `PAID` payment_status (D1), deletes seat rows (seats released!)
  - [x] Frontend: `bookings.html`, `js/pages/bookings.js`, status badges, details view, cancellation button
- [ ] **T7 — Admin movie and screening API + pages** *(implemented and automatically tested 20/11/2026; the top-level box stays open until the real-browser check, which is part of T9)*
  - [x] `app/admin.py`: `GET/POST /api/admin/movies`, `GET/PUT /api/admin/movies/{id}`, `GET/POST /api/admin/screenings`, `GET/PUT /api/admin/screenings/{id}` (all `Policy.ADMIN`, registered in `app/api.py`); movie input follows the schema limits (title ≤ 200, genre ≤ 100, rating ≤ 50, duration 1–300); `release_date` must be exactly `YYYY-MM-DD` (shared `strict_iso_date` in `app/params.py`, also used by the catalog's date query)
  - [x] Screening input: price is a finite number from 0 to 99999999.99 with at most two decimals (`Infinity`, `NaN`, `1e999`, too large or over-precise values are `400`, never `500`); timestamps in the years 1900–2200 (technical limits, not business rules); a time without an offset is the cinema's local time; `ends_at` defaults to start + movie duration; D2 relies on the database trigger (`UC001` → `409 screening_has_bookings`, also for CANCELLED and EXPIRED bookings; an identical save of a booked screening is not a modification); overlap on the `EXCLUDE` constraint (`23P01` → `409 screening_overlap`, back-to-back screenings allowed); `PUT` is a full replace (documented)
  - [x] `tests/test_admin_api.py` — **136 tests** against PostgreSQL: CRUD, boundaries, validation, `401`/`403`, `404` (including huge ids), D2 for BOOKED / CANCELLED / EXPIRED, overlap on create and update, atomicity (a failed save changes nothing), price snapshot after a price change
  - [x] Frontend: `admin-movies.html` + `js/pages/admin_movies.js`, `admin-screenings.html` + `js/pages/admin_screenings.js` (movie filter, add, edit; the Edit button is disabled for a screening that has bookings), shared helpers in `js/admin.js` (`requireAdmin`, `dataTable`, `badge`, `toInputDateTime`); no inline styles (classes in `css/style.css`), text-only rendering; static CSP tests pass
  - [x] Contract sections 11.5–11.6 updated; `tests/test_frontend_node.py` now runs every `tests/*.test.js` (it had skipped `seats.test.js`)
  - [ ] Real-browser check of the two admin pages (T9)
- [ ] **T8 — Admin booking list (view only) API + page** *(implemented and automatically tested 20/11/2026; the top-level box stays open until the real-browser check, which is part of T9)*
  - [x] `GET /api/admin/bookings` in `app/admin.py` (filters `status` — case-insensitive —, `screening_id`, `user_id`; runs `expire_overdue_bookings(cur)` first and the expiry is committed; seats listed only for `BOOKED` bookings); contract section 11.7
  - [x] `tests/test_admin_bookings_api.py` — **34 tests** against PostgreSQL: bookings of all customers, fields, no password data, PAID / CANCELLED / EXPIRED states (cancelled and expired list no seats, D1/D3), a PAID booking never expires, ordering, every filter and their combinations, bad filters `400`, expiry on read (committed, seats released), view-only (`405` for writes), listing changes nothing. Mutation check: three deliberate bugs in `admin_list_bookings` were all caught (6 failing tests)
  - [x] Frontend: `admin-bookings.html`, `js/pages/admin_bookings.js`, pure helpers in `js/admin_bookings.js`; `frontend/tests/admin.test.js` (16 Node tests for `admin.js` and `admin_bookings.js`, including hostile text rendered as text)
  - [x] The weakened contract test was restored to a meaningful check (`test_endpoints_still_planned_in_section_12_do_not_exist_yet`)
  - [ ] Real-browser check of the page (T9)
- [ ] T9 — Frontend integration and validation pass
- [ ] T10 — Integration, end-to-end and security suite
- [ ] T11 — Deployment, separation demo and release readiness

**Verification of T1 (20/11/2026, PostgreSQL 18.6, disposable server on `127.0.0.1:54329`, explicit `TEST_DB_PORT`):**
all tests **639 passed, 2 skipped** (the 2 skips need permission to create symbolic links, which this account lacks; the same traversal protection was verified with a directory junction) · without `TEST_DB_PORT`: 563 passed, 78 skipped, no connection attempted · frontend JavaScript (Node test runner): 26/26 · `pip check`: no broken requirements · `requirements.txt` unchanged. Real-process checks: frontend and API as two OS processes on ports 8080 and 5000, each stopped and restarted alone; API stays up and answers `503` on `/health/db` when its database is unreachable; frontend calls `/health` across origins; allowed and denied CORS origins; JSON 404/405. No connection was made to the development database (tests used port 54329; the process tests used a closed port).

**Verification of T2 (20/11/2026, PostgreSQL 18.6, disposable server on `127.0.0.1:54329`, explicit `TEST_DB_PORT`):**
all tests **793 passed, 2 skipped** (same two symbolic-link skips as T1) · without `TEST_DB_PORT`: 611 passed, 184 skipped, PostgreSQL tests skip and no connection is attempted · frontend JavaScript (Node test runner): 46/46 · `pip check`: clean · `requirements.txt` unchanged. Authorization matrix (anonymous / customer / admin × `/me`, a customer-only route, an admin-only route) and the role-change, deleted-account, expired-token, foreign-secret, tampered and malformed-header cases are tested through real Flask requests against PostgreSQL; the real `api.js` / `auth.js` were run under Node against the live API; registration, login and role authorization were also checked by hand over real HTTP with the API (5000) and frontend (8080) as separate processes, each stopped alone. Mutation checks (seven backend and eight frontend deliberate bugs in a scratch copy) were all caught. The development database was not touched (tests used port 54329).

**Known limits of T2.** Tokens are stateless: logout only discards the token in the browser and a stolen token works until it expires (tested and documented). There is no login rate limiting or lockout (out of scope; a production gap). `customer` / `admin` guards are verified with test-only routes: the first real customer and admin endpoints arrive in T5–T8. The seeded accounts still have unknown passwords until someone with a setup role runs `scripts/set_demo_passwords.py`.

**Verification of T3 (20/11/2026, PostgreSQL 18.6, disposable server on `127.0.0.1:54329`, explicit `TEST_DB_PORT`):**
all tests **938 passed, 2 skipped** (same two symbolic-link skips) · without `TEST_DB_PORT`: 673 passed, 267 skipped, PostgreSQL tests skip and nothing connects · frontend JavaScript (Node): 64/64 · `pip check`: clean · `requirements.txt` unchanged. Midnight boundaries (00:00 in, 23:59 in, neighbours out), ordering, started flag, null optional fields, markup in text returned as data, invalid dates and ids, CORS and a database outage are tested through real Flask requests against PostgreSQL; the real `api.js` / `format.js` read the live catalog under Node; checked by hand over real HTTP with the API (5000) and frontend (8080) as separate processes. Mutation checks (13 deliberate bugs, one of which exposed a wrong comment about the id guard, now corrected and covered) all caught. The development database was not touched.

**State of the working tree at the project review (20/11/2026, PostgreSQL 18.6, disposable server on `127.0.0.1:54329`, explicit `TEST_DB_PORT`; T4–T9 files are still uncommitted):**
Python tests **999 passed, 6 failed, 2 skipped** · without `TEST_DB_PORT`: 712 passed, 3 failed, 292 skipped · frontend JavaScript (Node): **69/69** · `tests/test_booking_flow.py` (T4–T6) passes, so T4–T6 stay verified. The 6 failures:
- 3 × `tests/test_frontend_static.py` — real defects of the unfinished T7 frontend (inline `style=` attributes; `admin-screenings.html` references the missing `admin_screenings.js`)
- 2 × tampered-token tests (`test_security.py::test_a_tampered_token_is_rejected`, `test_auth_api.py::test_a_tampered_token_is_401_invalid_token`) — flaky: the test changes only the last base64 character of the signature, which can leave the decoded signature unchanged; they passed on 3 re-runs. To fix in T9
- 1 × `test_setup_script.py::test_a_role_without_update_permission_cannot_change_anything` — caused by the throw-away server used for the review (a password-less role under SCRAM authentication gives no SQLSTATE); not a project defect, expected to pass on the original test server
The disposable server was stopped afterwards; the development database (port 5432) was not touched.

**Verification of T7 and T8 (20/11/2026, same disposable PostgreSQL 18.6 on `127.0.0.1:54329`, explicit `TEST_DB_PORT`, development database not touched):**
all Python tests **1196 passed, 1 failed, 2 skipped** · the one failure is the `test_setup_script` case described above (caused by the throw-away server, not by the project) · frontend JavaScript (Node, now all `tests/*.test.js`): **85/85** · the two earlier `test_frontend_static` failures and the two flaky-token failures did not recur in this run, but the token tests are still flaky by construction (see below). The real-browser check of the admin pages has **not** been done.

**Other findings of the review.**
- *(Fixed 20/11 in T8)* `tests/test_api_contract.py::test_planned_endpoints_are_not_implemented_yet` had been weakened (`if not planned: return`); it is now `test_endpoints_still_planned_in_section_12_do_not_exist_yet` and asserts that section 12 states "all Phase 4 endpoints implemented" when it lists none
- *(Fixed 20/11 in T7)* `release_date` accepted the compact form `20261120` (found by the new tests); now exactly `YYYY-MM-DD`
- *(Decision)* no `22003` / `22P02` entries were added to `app/errors.py`: that map is checked against the database contract of Member A, so numeric limits are validated in the application instead
- `README.md` still says "Flask application and web frontend: Not started" and the features are marked "Planned"; the empty placeholders `app/app.py`, `app/templates/`, `app/static/` are still tracked
- Nothing of T4–T8 is committed yet (12 modified and 12 new files)

**Network separation status.** Tier 1 (separate processes, one machine) is built and verified. Tier 2 (browser on a second device) is prepared by configuration only (`FRONTEND_HOST`, `API_BASE_URL`, `CORS_ALLOWED_ORIGINS`, `flask run --host`; see the API contract, section 13) and has **not yet been rehearsed on a second device**. Tier 3 (database on another machine) is not prepared and needs the Phase 3 Task 7 role. No PostgreSQL or firewall setting was changed; the development PostgreSQL was observed listening on all interfaces (`0.0.0.0:5432`): check it before using a shared network.

**How to run the tests now.** `TEST_DB_PORT` is still mandatory for the PostgreSQL tests (no fallback). Node is optional (those tests are skipped without it; no npm packages). `psql` is not on `PATH` on this machine; a disposable server can be created with `initdb` / `pg_ctl` from the PostgreSQL `bin` directory. Tests that commit bookings use the opt-in `fresh_db` / `fresh_app` fixtures (one private clone per test).

**Not done in T1, on purpose:** no authentication endpoints, no customer or admin endpoints, no demo-password command, no database role or permission change, `schema.sql` / `seed.sql` untouched, the empty placeholders `app/app.py`, `app/templates/`, `app/static/` remain (deferred Task 8), `README.md` not yet synchronized (deferred Task 8).

---

## 5. Phase 4 — Backend Implementation

> **Architecture change (20/11/2026):** this backend work is now delivered as a **REST API (JSON only)** consumed by an independent frontend, executed through tasks T2–T11 in section 4A. The checklist below is kept unchanged: an item is ticked only when its task has been verified. Sessions and cookies are **not** used; authentication is a signed Bearer token.

**Owner:** Member B — Application Lead

**Mục tiêu:** Triển khai các chức năng nghiệp vụ bằng Flask.

### 5.1 Authentication & Account

- [x] Customer registration *(T2)*
- [x] Customer login *(T2)*
- [x] Logout *(T2; stateless: the browser discards the token)*
- [x] Password hashing and verification *(T2)*
- [x] Session management *(T2: signed Bearer token, account re-read from PostgreSQL on every request; no cookie session)*
- [x] Admin authentication and authorization *(login for ADMIN and the role guard were verified with test routes in T2; the real admin endpoints (T7–T8) are tested for anonymous `401` and customer `403`)*

### 5.2 Movie & Screening

- [x] Retrieve movie list *(T3)*
- [x] Retrieve movie details *(T3)*
- [x] Retrieve screening schedules *(T3)*
- [x] Retrieve screening details *(T3)*
- [x] Retrieve available seats *(T4)*
- [x] Admin: Add movie *(T7 API, automated tests; page check in T9)*
- [x] Admin: Update movie *(T7 API, automated tests; page check in T9)*
- [x] Admin: Add screening *(T7 API, automated tests; page check in T9)*
- [x] Admin: Update screening *(T7 API, automated tests incl. D2 and overlap; page check in T9)*

### 5.3 Booking & Payment

- [x] Select multiple seats *(T4, T5)*
- [x] Validate selected seats *(T4, T5)*
- [x] Require login before booking confirmation *(T4, T5)*
- [x] Create booking *(T5)*
- [x] Calculate total amount *(T5)*
- [x] Save per-seat price snapshots *(T5)*
- [x] Implement simulated payment *(T5)*
- [x] Prevent payment after expiration *(T5)*
- [x] Implement request-time booking expiration *(T4, T5, T6)*
- [x] Release seats after expiration *(T5, T6)*
- [x] Retrieve customer booking history *(T6)*
- [x] Cancel customer booking *(T6)*
- [x] Release seats after cancellation *(T6)*
- [x] Preserve cancelled and expired booking history *(T6)*

### 5.4 Admin Functions

- [x] View all bookings *(T8 API, automated tests; page check in T9)*
- [x] Restrict admin-only functions *(every admin route is `Policy.ADMIN`; anonymous `401` tested on all nine routes; the access matrix derives the check from the route-policy registry)*
- [x] Prevent customer access to admin functions *(customer `403` tested on all nine admin routes, and a denied write changes nothing)*

**Status:** API complete and automatically tested (customer booking, payment, history and cancellation; admin movies, screenings and booking list); the phase is not marked completed until the integration, end-to-end and security work (T9–T10) is done

---

## 6. Phase 5 — Frontend Implementation

> **Architecture change (20/11/2026):** the frontend is an **independent program** in `frontend/` (HTML, CSS, vanilla JavaScript, its own static server) that talks to the API over HTTP. It does not use Flask templates. Pages are built per feature in tasks T2–T9 of section 4A; items below stay unticked until verified.

**Owner:** Member B — Application Lead

**Mục tiêu:** Xây dựng giao diện người dùng cho Customer và Admin.

### 6.1 Customer Interface

- [x] Home page *(T1)*
- [x] Movie list page *(T3)*
- [x] Movie detail page *(T3)*
- [x] Screening selection page *(T3)*
- [x] Seat selection interface *(T4)*
- [x] Booking confirmation page *(T5)*
- [x] Simulated payment page *(T5)*
- [x] Booking history page *(T6)*
- [x] Booking cancellation interface *(T6)*
- [x] Login page *(T2)*
- [x] Registration page *(T2)*

### 6.2 Admin Interface

- [ ] Admin dashboard *(not planned as a separate page: the navigation links to the three admin pages)*
- [ ] Movie management page *(`admin-movies.html` built and tested with Node and the static rules; ticked after the real-browser check, T9)*
- [ ] Screening management page *(`admin-screenings.html`, same status)*
- [ ] Booking management page *(`admin-bookings.html`, same status)*

### 6.3 UI Validation

- [ ] Validate navigation between pages
- [ ] Validate forms and user input
- [ ] Display success and error messages
- [ ] Display booking and payment statuses
- [ ] Validate responsive layout
- [ ] Verify customer/admin access restrictions

**Status:** In progress — all customer pages done and verified; the three admin pages are built and tested with Node and the static rules (real-browser check pending, T9); section 6.3 (UI validation) not started

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
| 3. Flask Application Foundation | In progress — core implemented and verified; app DB role (needs A) and documentation sync pending | Member B |
| 4A. Application Features (REST API + independent frontend, T1–T11) | In progress — **T1 through T6 done and verified (20/11)**; **T7–T8 implemented and automatically tested (20/11), real-browser check pending (T9)**; T9–T11 not started | Member B |
| 4. Backend Implementation | API complete and automatically tested (delivered through 4A); integration and security suite (T10) pending | Member B |
| 5. Frontend Implementation | In progress — customer pages done; admin pages built, browser check and UI validation (T9) pending | Member B |
| 6. Database–Application Integration | Not Started | Member B |
| 7. System Testing | Not Started | Member A + B |
| 8. Documentation & Presentation | Not Started | Member A + B |
| 9. Final Submission | Not Started | Member A + B |

### Current Blocking Issue

**None for Flask development.** The database now satisfies D1–D6 and passed all executed tests (see 3.3). The original handover in `CinemaDB_FINAL_PostgreSQL_Handover/` is outdated — do not code against it; use `database/schema.sql` and the integration contract.

**Next priority:** finish Phase 4 T7–T8 (see the plan below), and in parallel get Member A's review of the canonical database, confirmation of the driver and approval of the application database role (Phase 3 Task 7), then the Phase 3 documentation sync.

**Update 20/11/2026:** Phase 4 **T1** (architecture split, REST foundation, test harness), **T2** (auth API + login/register pages), **T3** (public catalog API + pages), **T4** (seat availability API + seat picker), **T5** (booking creation + simulated payment), and **T6** (booking history + cancellation) are all completed and verified. **T7 and T8 (admin) are implemented and covered by automated tests** (136 + 34 API tests, 16 Node tests); they are ticked at task level only after the real-browser check in T9 — see section 4A.

**Next steps (plan agreed after the 20/11 review, deadline 29/11):**
1. ~~Finish T7~~ and ~~Finish T8~~ — done 20/11 (automated verification; browser check moves to T9)
2. Phase 3 Task 8 / hygiene (next): remove the empty placeholders (`app/app.py`, `app/templates/`, `app/static/`), rewrite `README.md`, add the driver decision record and hygiene tests; fix the two flaky token tests (change the whole signature instead of one character)
3. T9: real-browser validation pass of every page (navigation, forms, messages, responsive layout, access restrictions, no CSP errors in the console); then tick T7, T8 and section 6.2
4. T10: end-to-end and security suite (TC01–TC15 of `chia_viec.md`, D1–D6 through the application, concurrent booking)
5. T11 and documentation: demo passwords, rehearsal on a second device, SQL scripts for the demo, README sync, remove empty placeholders; in parallel get Member A's review, driver confirmation and the application database role
6. Slides (including the required "why a team project in the age of AI" page), rehearsal, clean-environment check, packaging, submission

### Open Items and Decisions

| Item | Owner | Note |
|---|---|---|
| Member A's review of canonical `database/schema.sql` | Member A | Only remaining step of Phase 2 |
| Demo account passwords | A or B | The three seeded accounts keep A's hashes; plaintext is unknown/unverified and is documented nowhere. Set known passwords before any login demo with `scripts/set_demo_passwords.py` (T2): it needs explicit `SETUP_DB_*` credentials of a role that may UPDATE `users`; the API's runtime role must not be given that permission. Until Task 7 exists, the owner role is the only such role |
| PostgreSQL driver | A + B | Project owner approved `psycopg2-binary` with direct SQL (no ORM) on 20/11; `requirements.txt` pinned (2.9.13). **Member A's agreement still pending**; low reversal cost because all database access is in `app/database.py` |
| Application DB role privileges (`SECURITY DEFINER` or not) | Member A | Functions run with caller privileges; not implemented. Phase 3 Task 7 (role script and permission probe) waits for A's approval. Until then the app must only be run with the owner role locally, never in the demo |
| Is `expires_at` allowed after screening start? | Project owner | Not specified in B01–B05; no rule invented (booking allowed until start; expiry still works after start) |
| Genre / rating / release_date mandatory? | Project owner | Currently nullable free text; no vocabulary approved |
| Regenerate drawio/PNG ERDs for the presentation | Member A | Mermaid ERDs exist in `docs/database/`; A's old ERDs show the outdated model |
| PostgreSQL 14–17 compatibility | Member A / B | Tested on 18.6 only |
| Does the instructor accept process-level separation on one machine, or must the browser device / database be separate hardware? | Project owner (ask the instructor) | Frontend, API and PostgreSQL are separate processes on separate ports and network-connected; separate containers or processes on one machine do **not** by themselves mean separate hardware. A browser on a second device is a configuration change (API contract, section 13); a database on another machine needs the Task 7 role and is not prepared |
| Password / account-ID policy for registration | Project owner | None approved (BR-DL-001 section 6). T2 applies only technical bounds: account ID 1–60 characters (matching `users.username`) with no control characters, password 1–256 characters (limits the hashing work). Change only if the owner approves a policy |
| Language of the user interface (T2 onwards) | Project owner | Not specified; API messages and the T2 pages are English |
| Bearer-token limits (accepted 20/11) | Project owner | Tokens last 8 h by default (configurable) and cannot be revoked on the server; logout only discards the token in the browser (API contract, section 6) |

**Reminder for Phase 4:** Flask must call `expire_overdue_bookings()` (request-time expiry) before seat availability, booking history and admin booking lists; `create_booking`, `pay_booking` and `cancel_booking` already expire what they need. Nothing expires by itself.

**How to do it with the Phase 3 foundation:** run all SQL inside `with transaction() as cur:` (one user action = one transaction; reads too), and call `expire_overdue_bookings(cur)` from `app/database.py` first in the same block so the expiry is committed with the request. It is not re-entrant. A returned `'EXPIRED'` from `pay_booking` / `cancel_booking` is a committed outcome, not an error: leave the block normally. Never pass `p_as_of`. Translate database errors with `app/errors.py` (`translate_database_error`); responses never expose SQL or driver text.

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
| 20/11/2026 | Phase 3 decisions confirmed by the project owner: `psycopg2-binary`, direct parameterized SQL (no SQLAlchemy/ORM), `DB_*` variables, `app/database.py`, default timezone `Asia/Seoul` | Completed (driver: Member A's agreement pending) |
| 20/11/2026 | Phase 3 Tasks 1–3: fresh `.venv` and pinned `requirements.txt`, `.env.example`, `pytest.ini`; configuration and `create_app()` factory; disposable-database test fixture (`cinema_test_*` only, explicit `TEST_DB_PORT` required, ownership marker before any drop) | Completed |
| 20/11/2026 | Phase 3 Tasks 4–6: connection lifecycle, `transaction()` and `expire_overdue_bookings(cur)`, SQLSTATE error mapping per contract section 6, `/health` and `/health/db`. 352 tests passed against a disposable PostgreSQL 18.6; live Flask run verified 200 / 503 / 200 as the database was stopped and restarted | Completed |
| 20/11/2026 | Phase 3 remaining: Task 7 application database role (needs Member A's approval) and Task 8 documentation sync | Pending |
| 20/11/2026 | Phase 4 architecture revised to meet the course's separation requirement: independent frontend (`frontend/`, HTML/CSS/vanilla JS), Flask REST API returning JSON only, PostgreSQL; signed Bearer-token authentication; exact-origin CORS | Approved |
| 20/11/2026 | Phase 4 T1 spikes: per-test database clones from a session template (about 0.35 s each, marker re-applied, safety rules kept) and owner-only time-simulation helpers; JSON HTTP errors and CORS verified before implementation | Completed |
| 20/11/2026 | Phase 4 T1: REST foundation (`app/cors.py`, `app/security.py`, `app/api.py`, JSON provider, route-policy registry), independent frontend (`frontend/server.py`, `api.js`, `ui.js`, index page), `docs/api/api_contract.md`, per-test database fixtures. 639 tests passed + 2 skipped on a disposable PostgreSQL 18.6; 26 frontend JavaScript tests; frontend and API verified as independent processes on ports 8080 and 5000. T2–T11 not started | Completed |
| 20/11/2026 | Phase 4 T2: authentication API (`/api/auth/register`, `login`, `me`, `logout`), Bearer tokens with the account re-read from PostgreSQL on every request, `authenticated` policy, frontend login and registration pages (`auth.js`, `nav.js`, `forms.js`), setup-only `scripts/set_demo_passwords.py` (explicit `SETUP_DB_*`, no fallback), API contract updated (logout public per B03 CM-02, `invalid_credentials`). 793 tests passed + 2 skipped on a disposable PostgreSQL 18.6; 46 frontend JavaScript tests; checked by hand over real HTTP with API and frontend as separate processes. T3–T11 not started | Completed |
| 20/11/2026 | Phase 4 T3: public catalog API (`/api/movies`, `/api/movies/{id}`, `/api/screenings?movie_id&date`, `/api/screenings/{id}`), `app/params.py`, pages `movies.html` / `movie.html` / `screenings.html` with `js/format.js` and `js/catalog.js`, route-policy access matrix test for every route. 938 tests passed + 2 skipped on a disposable PostgreSQL 18.6; 64 frontend JavaScript tests; checked by hand over real HTTP with API and frontend as separate processes. T4–T11 not started | Completed |
| 20/11/2026 | Phase 4 T4–T6: Seat availability API (`/api/screenings/{id}/seats`), booking creation (`POST /api/bookings`), simulated payment (`POST /api/bookings/{id}/pay`), customer history (`GET /api/bookings`, `GET /api/bookings/{id}`), and cancellation (`POST /api/bookings/{id}/cancel`). Frontend pages `seats.html`, `booking.html`, `bookings.html` with interactive seat grid, live 10-min countdown timer, simulated payment, and cancellation. Contract updated, unit and frontend tests passing. T7–T11 not started | Completed |

| 20/11/2026 | Project review: full test run on a disposable PostgreSQL 18.6 (999 passed, 6 failed, 2 skipped; Node 69/69). T4–T6 confirmed verified. T7/T8 found partially implemented (admin API in `app/admin.py` and `admin-movies` page written, but no admin API tests, `admin_screenings.js` and the admin bookings page missing, admin pages violate the CSP) — recorded as in progress, not ticked. Continuation plan added to section 11 | Completed |

| 20/11/2026 | Phase 4 T7 and T8 implemented and automatically tested: admin movie / screening / booking-list API hardened (price and timestamp limits, strict `release_date`), `tests/test_admin_api.py` (136) and `tests/test_admin_bookings_api.py` (34), pages `admin-movies`, `admin-screenings`, `admin-bookings` with shared `js/admin.js` and `js/admin_bookings.js`, 16 new Node tests, contract sections 11.5–11.7 updated, weakened contract test restored, Node test runner now picks up every `tests/*.test.js`. Python 1196 passed / 1 environment-related failure / 2 skipped; Node 85/85. Real-browser check outstanding (T9) | Completed (browser check pending) |

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
