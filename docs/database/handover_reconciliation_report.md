# Handover Reconciliation Report — Member A PostgreSQL Handover vs. B01–B05 / D1–D6

The paths quoted in this report refer to the November 20 handover. The current SQL baseline, demo seed and verification commands are listed in the [PostgreSQL guide](../../database/README.md).

**Project:** 영화관 예매 및 좌석 관리 시스템 (Cinema Reservation System)
**Prepared by:** Member B (Application Lead)
**Date:** 2026-11-20 (KST)
**Authority:** B01–B05 and `business_rules_decision_log.md` (BR-DL-001, D1–D6) are authoritative. Nothing here changes them.
**Subject:** `CinemaDB_FINAL_PostgreSQL_Handover/` (preserved unmodified)

> **Audit verdict on the ORIGINAL handover (2026-11-20, sections 1–3): not ready for Flask.** It was a clean, internally consistent schema built to an earlier model; it lacked what D2 (price), D3, D5 and D6 require.
>
> **Resolution (section 10): the corrections were implemented in the canonical files `database/schema.sql`, `database/seed.sql` and `database/tests/`, and verified by execution (177 integrity checks, 31 probes, 16 concurrency checks, all passing on PostgreSQL 18.6).** The original handover folder is unchanged. Sections 1–3 are kept as the historical audit evidence; sections 4 and 6–8 describe the current state.

---

## 1. What was inspected

Handover folder: `CinemaDB_FINAL_PostgreSQL_Handover/` (untracked in git; not modified).

| Area | Files |
|---|---|
| DDL / seed / verify | `database/schema.sql` (200 lines, 7 tables, 8 triggers), `database/seed.sql`, `database/verify.sql` |
| Tests | `tests/integrity_tests.sql`, `tests/test_concurrency_fixed.py` |
| ERDs | `erd/Cinema_Conceptual_ERD.{drawio,png}`, `erd/Cinema_Logical_ERD_3NF.{drawio,svg}`, `erd/Final_Logical_ERD_Actual_PostgreSQL.mmd` |
| Docs | `docs/00_READ_FIRST_KO.md` … `07_Final_Checklist_KO.md` (glossary, domain definition, table description, normalization, integration contract, test report, checklist), `README_DB_Setup.md`, `evidence/README.txt` |

The actual SQL, constraints and triggers were read line by line and executed; documentation summaries were not relied on. Also read: all six files under `docs/business/` and `docs/database/database_design_handoff_A.md`.

## 2. Verification performed (actually executed)

**Environment:** a throwaway PostgreSQL **18.6** cluster created with `initdb` in a temporary directory, listening on `127.0.0.1:54329` only. The machine's existing PostgreSQL 18 service was **not touched**. Fresh databases `a_orig` and `a_probe` were created for the runs; they were never shared. Only PostgreSQL 18.6 was tested (A targets 14+; 14–17 were not run).

| # | Check | Command / artifact | Actual result |
|---|---|---|---|
| T1 | `schema.sql` on empty DB | `psql -v ON_ERROR_STOP=1 -f schema.sql` | Success, no errors |
| T2 | `seed.sql` | same | Success: 3 users, 5 movies, 5 rooms, 250 seats, 140 showtimes (20/day × 7 days) |
| T3 | `verify.sql` | `psql -f verify.sql` | Counts as expected; 50 seats/room; 8 triggers; 0 double allocations |
| T4 | `integrity_tests.sql` (A's) | `psql -v ON_ERROR_STOP=1` | PASS 1–7 (test "8" is a comment placeholder, not a test); rolled back |
| T5 | `test_concurrency_fixed.py` (A's) | `PGDATABASE=a_orig python …` | `RESULT: PASS - concurrent duplicate booking prevented` (B blocked on lock, then rejected: "Seat already reserved") |
| T6 | Reconciliation probes (B's, audit-time version) | `database/tests/reconciliation_probes.sql` *(that version has since been replaced by the corrected-model probes, section 10)* | See section 3; 13 MISMATCH, 9 MATCH, 4 INFO (+ P16 expected error). All rolled back |
| T7 | Booking without seats at COMMIT | probe P16 | `ERROR: Confirmed booking must contain at least one seat`; 0 rows persisted |

**What T4/T5 do and do not prove.** They prove A's *own* rules (CONFIRMED/CANCELLED model) work, including race-safe duplicate-seat prevention. They do **not** test any D1–D6 requirement, and A's `06_Test_Report_KO.md` PASS claims rest on A's local logs (2026-11-13). B has now independently re-executed both A tests on PG 18.6 and got the same PASS results.

**Side effect found in T5:** the concurrency test leaves one `CANCELLED` booking behind (cleanup cancels, it cannot delete). Under D2 that permanently locks the test screening. Run it only on a disposable database.

## 3. Reconciliation against D1–D6 and approved rules

Legend: ✅ satisfied (verified by execution) · ❌ not satisfied · ⚠️ partly / application-level / needs decision.

### D1 — Cancellation
| Requirement | Result | Evidence |
|---|---|---|
| Status becomes `CANCELLED` | ✅ | P07: status=`CANCELLED` |
| Parent booking remains | ✅ | P07 |
| All booking-seat rows deleted | ✅ | P07: 0 rows (trigger `trg_release_cancelled_seats`) |
| Cancelled booking cannot be reactivated | ✅ | P08 |
| Retained parent includes total amount and payment status | ❌ | Columns do not exist (P01, DB-04) |
| Released seats rebookable | ✅ | A's test 6 |

### D2 — Screening modification
| Requirement | Result | Evidence |
|---|---|---|
| movie / room / start time locked once any booking references the screening | ✅ | P06a, P06b |
| Applies regardless of status (CANCELLED/EXPIRED too) | ✅ for CANCELLED (P06c); EXPIRED does not exist yet | trigger checks `EXISTS (bookings WHERE showtime_id=…)` with no status filter |
| **Ticket price locked** | ❌ | **P05: `UPDATE showtimes SET ticket_price=…` was ACCEPTED** on a screening with a booking. `trg_booked_showtime` fires only `UPDATE OF movie_id,room_id,starts_at` |
| End time locked | ⚠️ | No end-time column exists (DB-02). Currently derived from movie duration, and `trg_movie_duration` blocks duration edits (see "extra rules") |

### D3 — Expiration and payment
| Requirement | Result | Evidence |
|---|---|---|
| Booking statuses `BOOKED/CANCELLED/EXPIRED` | ❌ | P02: domain is `CONFIRMED/CANCELLED` |
| Payment statuses `UNPAID/PAID` | ❌ | No `payment_status` column (P01) |
| `expires_at = booked_at + 10 min` | ❌ | No `expires_at` column (P01) |
| New booking starts UNPAID | ❌ | P03: `paid_at DEFAULT now()` marks every booking "paid" at insert |
| Payment recordable later (UNPAID→PAID) | ❌ | P03b: `validate_booking` forbids changing `paid_at` |
| Expiry deletes seats, keeps parent, atomic, idempotent | ❌ | No expiry logic anywhere (P02b: 0 objects). Cancellation pattern exists and can be mirrored |
| Paid bookings never expire; payment valid only before `expires_at` | ❌ | Not representable |

**Per instructions, no automatic-expiration mechanism was invented.** D3 #10 leaves the invocation mechanism (scheduled / request-triggered / both) open. What A must supply is the *data model and an atomic, idempotent transition*; how it is invoked is an open team decision (section 7, Q1).

### D4 — Guest browsing
| Requirement | Result | Evidence |
|---|---|---|
| No GUEST role | ✅ | P13: `CHECK (role IN ('CUSTOMER','ADMIN'))` rejects `GUEST` |
| Browsing without login; login before confirmation | ⚠️ application | DB cannot know sessions; only CUSTOMERs may own bookings (A's test 1 ✅) |

### D5 — Data attributes
| Requirement | Result | Evidence |
|---|---|---|
| Account ID + password hash; unique ID | ✅ | `users.username UNIQUE`, `password_hash` (demo hashes are Werkzeug `pbkdf2:sha256`) |
| Role defaults to CUSTOMER | ✅ | `DEFAULT 'CUSTOMER'` |
| Public registration never creates ADMIN | ⚠️ application | P14: DB accepts `role='ADMIN'` inserts; Flask must never pass a role |
| Movie: title, duration, synopsis | ✅ | `title`, `duration_minutes`, `synopsis` |
| Movie: **genre, rating, release_date** | ❌ | P01: all three ABSENT |

### D6 — Price
| Requirement | Result | Evidence |
|---|---|---|
| Per-screening price | ✅ | `showtimes.ticket_price numeric(10,2) ≥ 0` |
| Per-seat price snapshot | ⚠️ | `booking_seats.price_at_booking` exists; P04: DB accepts a value ≠ screening price (app-supplied) |
| `BOOKINGS.total_amount` | ❌ | Column absent (P01) |
| Price immutable once booked (D2 #5) | ❌ | P05 |
| Demo price documented as demo | ⚠️ | Seed uses 12000.00 for all; seed comment does not say "demo, not a rule" |

### Other approved rules
| Rule | Result | Evidence |
|---|---|---|
| Seat belongs to booking's screening room (BR-07) | ✅ | P09, A's test 4 |
| No overlap in same room (BR-04) | ✅ for true overlap | P11a |
| ↳ back-to-back allowed | ❌ | P11b: rejected because of an **unapproved 15-minute buffer** |
| One active booking per seat per screening (BR-08) | ✅ | P10, A's test 3, concurrency T5 (trigger locks the showtime row; no partial-unique index is possible without denormalizing, and BR-DL-001 §5.2 #10 explicitly accepts a trigger) |
| Atomic booking + seats | ✅ | Deferred constraint trigger: P16 |
| No booking after showtime start (BR-12); no cancel after start (BR-10) | ✅ by code review; not re-executed (needs a started screening) | `validate_booking`, `validate_booking_seat` |
| No global seat-status in `SEATS` | ✅ | `seats` has only position columns |
| Timestamps: one convention | ✅ | `timestamptz` everywhere; seed built with `AT TIME ZONE 'Asia/Seoul'` |
| Seed: 5 rooms / 250 seats / 5 movies / 140 screenings / 1 admin / 2 customers | ✅ | T2 (but movies lack D5 attributes; screenings use relative dates, 5 of today's already started at run time, P15) |

### Unapproved additional rules found in A's schema (not in B01–B05 or D1–D6)
| ID | Rule | Effect on the application | Required action |
|---|---|---|---|
| X1 | 15-minute cleaning buffer between screenings (`validate_showtime`) | Admin cannot schedule a screening that starts when the previous ends (A-02, BR-04) | Team decision; if not approved, A removes the buffer |
| X2 | Movie duration cannot be edited once any screening exists (`trg_movie_duration`, P12) | A-01 "영화 정보 수정" fails for duration on any scheduled movie | Team decision; if kept, B documents it as a UI-visible restriction (it does incidentally protect a derived end time) |
| X3 | `cancelled_at` column; booking-identity immutability | Harmless supporting detail | Keep; document as technical column |
| X4 | `movies.duration_minutes BETWEEN 1 AND 300`; `seat_row` A–E, `seat_number` 1–10 | Reasonable, consistent with 50 seats/room; B uses as-is | Document as technical domain limits |

## 4. Main-repository incorporation status (current)

| Path | State | Notes |
|---|---|---|
| `CinemaDB_FINAL_PostgreSQL_Handover/` | untracked, **unchanged** | Historical reference of Member A's delivery. Not edited, not deleted, not used as a second schema. |
| `database/schema.sql` | **canonical, populated** | Derived from A's DDL and corrected (section 10). Verified. |
| `database/seed.sql` | **canonical, populated** | 3 / 5 / 5 / 250 / 140 rows; new movie attributes and stored end times. Verified. |
| `database/tests/integrity_tests.sql` | canonical | Replaces the placeholder-based original tests for the new model (177 checks). A's original test file stays in the handover folder. |
| `database/tests/reconciliation_probes.sql` | canonical | Probes updated to the corrected model (31 MATCH, 0 MISMATCH). |
| `database/tests/test_concurrency.py`, `run_all.sh` | canonical | Real multi-session race tests (16 checks) and the disposable-database runner. |
| `database/README.md` | updated | Status verified; setup and safety notes. |
| `docs/database/postgresql_flask_integration_contract.md` | updated | Matches the implemented schema (10 required topics). |
| `docs/database/{table_description,glossary,domain_definition,normalization,conceptual_data_model,logical_data_model,physical_data_model}.md` | **filled** (were 0-byte placeholders) | Derived from the canonical schema. |
| `docs/database/database_test_documentation.md` | new | Commands and actual results. |
| ERDs | Mermaid ERDs in the three model documents | A's `.drawio/.svg/.png/.mmd` ERDs describe the old model and are left untouched in the handover folder; they must not be used for the presentation (A may regenerate drawio/PNG from the new Mermaid ERDs). |
| `requirements.txt` | unchanged (empty) | Driver choice still open (B01 §7.1). |

## 5. Logical vs. physical names (resolved, no rename requested)

| Logical (B01–B05, BR-DL-001) | Physical (A's PostgreSQL) |
|---|---|
| `USERS` | `users` |
| `MOVIES` | `movies` |
| `ROOMS` | **`theater_rooms`** |
| `SEATS` | `seats` |
| `SCREENINGS` | **`showtimes`** |
| `BOOKINGS` | `bookings` |
| `BOOKING_SEATS` | `booking_seats` |

Column mapping (logical → physical): account ID → `users.username`; duration → `movies.duration_minutes`; screening start → `showtimes.starts_at`; per-seat price → `showtimes.ticket_price`; price snapshot → `booking_seats.price_at_booking`. Application code uses the physical names; documents keep the logical names. A should **not** rename tables to match the logical names (churn without benefit); the mapping above is part of the contract.

## 6. Corrections that were assigned to Member A — status

The audit assigned DB-01…DB-11 to Member A as database owner. By instruction, the corrections were then implemented directly in the canonical files (A's original files untouched). Member A should review the canonical `database/schema.sql` and accept it as the team's database. Details and evidence: section 10.

| ID | Item | Status |
|---|---|---|
| DB-01 | Movie attributes (`genre`, `rating`, `release_date`) | ✅ done, tested |
| DB-02 | Stored screening end time (`ends_at`) | ✅ done, tested |
| DB-03 | Remove 15-min buffer and duration lock | ✅ done, tested |
| DB-04 | Booking statuses, `payment_status`, `expires_at`, `total_amount`, no auto-payment | ✅ done, tested |
| DB-05 | Trigger rework (BOOKED, payment, expiry, cancel) + expiry operation | ✅ done, tested |
| DB-06 | D2 protection incl. `ticket_price` | ✅ done, tested |
| DB-07 | Price snapshot and total consistency | ✅ done (database-enforced), tested |
| DB-08 | Tests for the new model | ✅ done (177 + 31 + 16 checks) |
| DB-09 | Seed update and demo-credential documentation | ✅ seed updated; ⚠️ demo password plaintexts remain unknown/unverified (not documented, not invented) |
| DB-10 | ERDs and database documents | ✅ new Mermaid ERDs and documents; A's old drawio/PNG/SVG are stale |
| DB-11 | Expiry-scan index | ✅ partial index `idx_bookings_pending_expiry` |

## 7. Open items and decisions

| Item | State |
|---|---|
| Expiry invocation (was Q1) | **Decided by the team: request-time expiry.** Implemented as `expire_overdue_bookings()` (+ built into `create_booking`/`pay_booking`/`cancel_booking`). No pg_cron, worker or scheduler. Flask must call it before availability, history and admin booking lists (contract §3.3). |
| 15-min buffer / duration lock (was Q2) | **Removed** as instructed (not approved business rules). |
| Database driver (Q3) | Open. `psycopg2-binary` recommended; `requirements.txt` unchanged. |
| `expires_at` after screening start (Q4) | Not specified by B01–B05; no rule invented. Current behaviour: a booking is allowed until the screening starts; if its deadline falls after the start, expiry still works after the start (tested). Needs the project owner's confirmation only if a different rule is wanted. |
| Genre / rating vocabularies (Q5) | Not imposed: free text, columns nullable. Confirm nullability if the owner wants them mandatory. |
| Demo credentials | A's three password hashes kept; plaintext undocumented/unverified. A or B must set known passwords before a login demo. |
| Application role privileges | Functions run with the caller's privileges; a function-only application role would need `SECURITY DEFINER` — not implemented, deployment decision for A. |
| PostgreSQL 14–17 | Not tested (18.6 only). |
| `p_as_of` argument | Present on `expire_overdue_bookings`, `pay_booking`, `cancel_booking` for deterministic deadline tests only; Flask must not pass it. A may remove it if tests are re-designed. |

## 8. Readiness (current)

**READY FOR FLASK INTEGRATION** against the canonical database, with the open items above (none is a failing requirement): all critical approved requirements D1–D6 and the retained rules passed execution-based verification (section 10 and `database_test_documentation.md`). Flask work must follow the integration contract and must not start a login demo until demo passwords are set.

## 9. Reproducing the results

```bash
# disposable server/database only - never a shared one
export PGHOST=127.0.0.1 PGPORT=54329 PGUSER=<owner role>
python -m pip install psycopg2-binary
bash database/tests/run_all.sh
```
To reproduce the ORIGINAL audit (13 mismatches) apply `CinemaDB_FINAL_PostgreSQL_Handover/database/{schema,seed}.sql` to an empty database; the audit-time probe script is described in section 2/3 (the file itself was replaced by the corrected-model probes).

## 10. Resolution — how each item was fixed and verified

### 10.1 D1–D6 (final)

| Decision | Implemented as | Verified by |
|---|---|---|
| **D1** | `trg_bookings_validate` allows `BOOKED → CANCELLED` (before start, payment status unchanged); `trg_bookings_release_seats` deletes all seat rows in the same transaction; parent and `total_amount` stay; `cancel_booking()` | integrity: 18 D1 checks, probes P07/P08 |
| **D2** | `trg_showtimes_protect_booked` now fires on every UPDATE and compares movie, room, start, end **and `ticket_price`**; rejects (`UC001`) if any booking row exists, any status | integrity: 22 D2 checks — 5 attributes + combined change × BOOKED/CANCELLED/EXPIRED, plus editable/no-op/delete; probes P05, P06a–f; mutation check |
| **D3** | `status` BOOKED/CANCELLED/EXPIRED, `payment_status` UNPAID/PAID, `expires_at = booked_at + 10 min` (CHECK + trigger), no automatic payment, transition rules in the trigger, `expire_overdue_bookings()` (atomic, idempotent, works after screening start, not blocked by D2), `pay_booking()`, `cancel_booking()` | integrity: 45 D3 checks incl. 1 µs-before / exact-deadline / after-start / idempotence / paid-never-expires; concurrency C4–C6; probes P02–P03b, P17–P19 |
| **D4** | unchanged: `role` CHECK rejects GUEST; only CUSTOMER may own bookings | integrity: 2 D4 checks; probe P13 |
| **D5** | `movies.genre`, `rating`, `release_date` added (free text/date, nullable, no ENUM); account ID + hash + default `CUSTOMER` unchanged | integrity: 6 D5 checks; probe P01 |
| **D6** | `showtimes.ticket_price` per screening; `price_at_booking` must equal it (NULL is filled from it); `bookings.total_amount` = Σ snapshots (deferred check at COMMIT, immutable, retained after cancel/expiry); `create_booking()` computes both | integrity: 14 D6 checks; probes P04 |

### 10.2 DB-01 … DB-11

| ID | Fix in canonical schema/seed |
|---|---|
| DB-01 | three movie columns; seed gives demo genre/rating/release_date (demo data, not a vocabulary) |
| DB-02 | `showtimes.ends_at NOT NULL`, CHECK `> starts_at`; defaulted from the movie duration only when omitted, then **stored**; seed stores `starts_at + duration`; checked for all 140 seeded rows; later duration edits do not move existing screenings; D2 protects `ends_at` |
| DB-03 | 15-minute buffer and duration-lock trigger **removed**; overlap is now an `EXCLUDE USING gist` on `[starts_at, ends_at)` per room (declarative, race-free); back-to-back and 1-minute gaps accepted, true overlaps (`23P01`) rejected |
| DB-04 | new `bookings` columns/domains/CHECKs (see table description); `paid_at` is now nullable and set only on payment |
| DB-05 | all `CONFIRMED` logic rewritten for the new model; trigger names listed in `physical_data_model.md`; consistency trigger named so it fires after seat release (found and fixed by verification: cancel/expire failed under `SET CONSTRAINTS ALL IMMEDIATE`; now a regression test) |
| DB-06 | see D2 |
| DB-07 | database-enforced (chosen over application responsibility): Flask supplies nothing — `create_booking()` computes; direct inserts are still validated |
| DB-08 | `integrity_tests.sql` (177), `reconciliation_probes.sql` (31), `test_concurrency.py` (16), `run_all.sh`; 5 mutation checks prove sensitivity |
| DB-09 | seed updated; demo password plaintexts **still unknown/unverified** — not documented |
| DB-10 | `docs/database/*.md` filled with Mermaid ERDs; contract rewritten; A's old ERDs stale |
| DB-11 | `idx_bookings_pending_expiry` partial index |

### 10.3 Defects found in B's own work during verification (disclosed)

* The first concurrency run showed `PAID=0` in the pay-vs-expire race: the test was not racing (connections opened late). Fixed; the race now produces both outcomes.
* A published seat-availability query was exercised; it exposed that `expire_overdue_bookings()` failed in IMMEDIATE-constraint mode because of alphabetical trigger firing order. Fixed in the schema and covered by a regression test.
* Two probe/test expectations were wrong (same-statement snapshot visibility; `RESTRICT` raises 23001, not 23503) and were corrected — the database was behaving correctly.

### 10.4 Test results (final `run_all.sh`)

`schema.sql` OK · `seed.sql` OK (3/5/5/250/140) · integrity **177/177** · probes **31 MATCH, 0 MISMATCH** · concurrency **16/16** · `ALL DATABASE TESTS PASSED` (PostgreSQL 18.6, disposable database, dropped afterwards).
