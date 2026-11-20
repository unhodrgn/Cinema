# Database Test Documentation

Covers the canonical database (`database/schema.sql`, `database/seed.sql`). Everything below was executed; the results are copied from real runs on 2026-11-20 against **PostgreSQL 18.6** (Windows). Other PostgreSQL versions (14–17) were **not** tested.

## 1. Safety rules

* Run only on a **new, disposable** database. `integrity_tests.sql` and `reconciliation_probes.sql` roll back; `test_concurrency.py` commits (its bookings are permanent history and cannot be deleted) and therefore **refuses to run unless the database is freshly seeded with zero bookings**.
* The test role must own the tables (the role that created the schema does). Tests simulate elapsed time only by temporarily disabling USER triggers inside the rolled-back transaction (or, for concurrency, on the disposable database); no application path does that.
* The runner creates its own uniquely named database (`cinema_test_<timestamp>_<pid>`) and drops **only that one**. It never touches any other database or the PostgreSQL service.

## 2. Files

| File | Kind | Content |
|---|---|---|
| `database/tests/run_all.sh` | runner | schema → seed → integrity → probes → concurrency on a disposable DB |
| `database/tests/integrity_tests.sql` | SQL, one rolled-back transaction | 177 checks: seed, D1–D6, DB-02/03, seats, rollback, constraints, trigger-order regression |
| `database/tests/reconciliation_probes.sql` | SQL, rolled back | 31 probes with the audit's P-numbers; fails on any MISMATCH |
| `database/tests/test_concurrency.py` | Python (psycopg2), real sessions | 16 checks, scenarios C1–C6 |

## 3. How to run

```bash
# connection through the libpq environment, e.g. a throwaway server on port 54329
export PGHOST=127.0.0.1 PGPORT=54329 PGUSER=<owner role>        # PGPASSWORD if needed
python -m pip install psycopg2-binary                           # for test_concurrency.py
bash database/tests/run_all.sh                                  # KEEP_DB=1 keeps the database

# or step by step on an empty database:
createdb cinema_verify
psql -X -v ON_ERROR_STOP=1 -d cinema_verify -f database/schema.sql
psql -X -v ON_ERROR_STOP=1 -d cinema_verify -f database/seed.sql
psql -X -v ON_ERROR_STOP=1 -d cinema_verify -f database/tests/integrity_tests.sql
psql -X -v ON_ERROR_STOP=1 -d cinema_verify -f database/tests/reconciliation_probes.sql
PGDATABASE=cinema_verify python database/tests/test_concurrency.py
```

## 4. Results (final run of `run_all.sh`)

| Step | Result |
|---|---|
| 1 `schema.sql` | OK (no errors) |
| 2 `seed.sql` | OK — 3 users, 5 movies, 5 rooms, 250 seats, 140 screenings, 20 per day over 7 days |
| 3 `integrity_tests.sql` | **ALL 177 CHECKS PASSED**, exit 0, nothing persisted |
| 4 `reconciliation_probes.sql` | **SUMMARY: 31 MATCH, 0 MISMATCH**, exit 0; P16 expected error raised and 0 rows persisted; 2 INFO items (application responsibilities) |
| 5 `test_concurrency.py` | **16/16 checks passed**, exit 0 (race outcome in the final run: 24 payments won, 16 expiries won; repeated runs: 22/18, 23/17, 29/11 — always valid) |
| overall | `ALL DATABASE TESTS PASSED`, disposable database dropped |

The earlier audit of Member A's original handover (7/7 original integrity tests and the original concurrency test passed, but 13 probes mismatched D1–D6) is recorded in `handover_reconciliation_report.md`.

## 5. What each decision is checked by

| Req. | Verified by (examples; each is a named PASS line) |
|---|---|
| D1 | cancel → `CANCELLED`, parent stays, 0 seat rows, `payment_status` preserved (UNPAID and PAID), total kept, history queryable, no re-activation, other user cannot cancel, cancel after start rejected and atomic |
| D2 | movie / room / start / end / ticket_price / combined changes each rejected with `UC001` for BOOKED, CANCELLED and EXPIRED bookings; free screening editable; no-op update allowed |
| D3 | new booking BOOKED+UNPAID, `paid_at` NULL, `expires_at` = `booked_at` + exactly 10 min; payment before expiry; payment 1.5 s before deadline; payment **at** the deadline rejected (booking expires); payment after the deadline rejected by function and by DB trigger; expiry **1 µs before** does nothing, **at** the exact deadline expires; seats deleted, parent kept; PAID never expires (even directly); repeated calls return 0; expiry works after the screening started; expired booking cannot be paid/cancelled/reactivated; nothing expires without a call |
| D4 | `GUEST` role rejected (23514); ADMIN cannot own a booking (`UC008`); no scheduler extension installed |
| D5 | six movie attributes stored and read back, no genre/rating restriction, role defaults to CUSTOMER, `username` unique |
| D6 | per-screening price (9500 and 14000 screenings), per-seat snapshot, total = price × seats and = Σ snapshots, wrong snapshot / wrong total / missing seats rejected, total immutable, total kept after cancel and after expiry |
| DB-02/03 | `ends_at` default and CHECK, duration edit allowed, existing end times unchanged, new screening uses new duration, back-to-back and 1-minute-gap screenings allowed, true overlaps rejected (`23P01`), other room allowed |
| Retained | seat ownership (`UC003`), duplicate active seat (`UC002`) incl. multi-seat, atomic rollback of `create_booking`, FK/UNIQUE/CHECK/RESTRICT violations, `expires_at` CHECK even if the trigger were bypassed, trigger-order robustness under `SET CONSTRAINTS ALL IMMEDIATE` |
| Concurrency | C1 8 sessions one seat → exactly 1 win; C2 B blocked until A commits then `UC002`; C3 overlapping multi-seat → one wins, loser leaves nothing; C4 40 payments vs 2 expirers at the deadline → every row valid, both outcomes occurred; C5 20 pay-vs-cancel races valid; C6 5 parallel expirers → each booking expired exactly once |

## 6. Test sensitivity (mutation checks)

To make sure the tests can fail, five deliberate defects were applied to scratch copies of the schema and `integrity_tests.sql` was run; each was caught by the expected check:

| Defect | Caught by |
|---|---|
| `ticket_price` removed from the D2 trigger | `D2 ticket_price change rejected (BOOKED)` |
| expiry allowed before `expires_at` | `D3 DB trigger rejects expiring before expires_at` |
| duplicate-seat check disabled | `BR-08 same seat, same screening, other customer rejected` |
| cancel of an overdue unpaid booking allowed | `D3 DB rejects direct cancel of an overdue unpaid booking` |
| consistency trigger renamed so it fires before seat release | `ORDER cancel works with constraints IMMEDIATE` (found by verification, fixed, now a regression test) |

The new integrity suite also fails against Member A's original schema (`column s.ends_at does not exist`), as expected.

## 7. Limits

* Tested on PostgreSQL 18.6 only; the schema uses only features available in 14 (identity columns, EXCLUDE with `btree_gist`, constraint triggers, `FOR UPDATE SKIP LOCKED`).
* The exact-deadline checks use the functions' optional `p_as_of` argument (tests only); real-clock behaviour is covered by the 1.5-second pre-deadline payment, the post-deadline payments and the timed race C4.
* Flask-level behaviour (sessions, authorisation, registration role, request-time expiry calls) is application scope and is **not** tested here.
* Demo account passwords are unverified (see the contract §7); no login was tested.
