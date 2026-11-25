# Database Test Documentation

The original sections cover baseline `0001_baseline.sql` and `backend/seeds/demo.sql`. Their historical results were recorded on 2026-11-20 against **PostgreSQL 18.6** (Windows). Other PostgreSQL versions (14–17) were **not** tested.

## 1. Safety rules

* Run only on a **new, disposable** database. `integrity_tests.sql` and `reconciliation_probes.sql` roll back; `test_concurrency.py` commits (its bookings are permanent history and cannot be deleted) and therefore **refuses to run unless the database is freshly seeded with zero bookings**.
* The test role must own the tables (the role that created the schema does). Tests simulate elapsed time only by temporarily disabling USER triggers inside the rolled-back transaction (or, for concurrency, on the disposable database); no application path does that.
* The runner creates its own uniquely named database (`cinema_test_<timestamp>_<pid>`) and drops **only that one**. It never touches any other database or the PostgreSQL service.

## 2. Files

| File | Kind | Content |
|---|---|---|
| `database/tests/run_all.sh` | legacy wrapper | forwards to `backend/tests/run_database.py` |
| `backend/tests/run_database.py` | runner | migrations `0001`+`0003`+`0004` → seed → `money_domain.sql` → `integrity_tests.sql` → `reconciliation_probes.sql` → `test_booking_concurrency.py` on a disposable DB |
| `backend/tests/sql/money_domain.sql` | SQL, rolled back | catalog checks and finite-money domain checks (`0004`) |
| `backend/tests/sql/integrity_tests.sql` | SQL, one rolled-back transaction | checks for seed, D1–D6, DB-02/03, seats, rollback, constraints, trigger-order regression |
| `backend/tests/sql/reconciliation_probes.sql` | SQL, rolled back | 31 probes with the audit's P-numbers; fails on any MISMATCH |
| `backend/tests/test_booking_concurrency.py` | Python (psycopg2), real sessions | 16 checks, scenarios C1–C6 |

## 3. How to run

From the repository root, run `docker compose --profile test run --build --rm verify` for the full application, frontend and database suites. With a disposable native PostgreSQL server and an explicit `TEST_DB_PORT`, run `python backend/tests/run_database.py` for SQL and concurrency only. The runner applies the canonical baseline and seed, checks the integrity summary and reconciliation P16, and then runs concurrency on that database. Supply `--keep-db` to inspect it afterwards. The legacy Bash entry point forwards to this runner.

Current seed counts are 3 users, 6 movies, 5 rooms, 250 seats and 280 screenings across 14 days. Results in section 4 describe the historical November 20 seed.

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

* These historical results used PostgreSQL 18.6; the baseline uses features available in 14 (identity columns, EXCLUDE with `btree_gist`, constraint triggers, `FOR UPDATE SKIP LOCKED`).
* The exact-deadline checks use the functions' optional `p_as_of` argument (tests only); real-clock behaviour is covered by the 1.5-second pre-deadline payment, the post-deadline payments and the timed race C4.
* Flask-level behaviour (sessions, authorisation, registration role, request-time expiry calls, demo account login) is covered by the pytest suite under `backend/tests/` and Playwright E2E tests under `frontend/e2e/`, not by the SQL-only suite above. Demo account credentials are documented in the root `README.md` and `backend/seeds/demo.sql`.

## 0003–0004 회귀 및 시연

- PostgreSQL 18.7에서 0001 → 0003 → 0004 스키마를 사용한다. 별도 Compose 검증 프로필의 기존 실행기는 DB 스키마 작성 후 시드한다.
- 두 고객이 같은 상영의 같은 좌석을 예매하면 즉시 고유 제약 또는 SQLSTATE 40001로 한 건만 확정된다. 같은 물리 좌석은 다른 상영에서 다시 예매할 수 있다. 취소·만료가 커밋되면 같은 상영에서도 다시 배정할 수 있다.
- 격리된 DB에서 단가 99,999,999.99의 미래 상영을 만들고 50석을 예매한다. 예매 총액은 4,999,999,999.50이다. 결제 후 취소하면 총액과 CANCELLED/PAID 이력이 남고 활성 배정은 0건이다.
- 40001 또는 40P01 뒤에는 실패한 트랜잭션을 롤백하고, 재시도가 허용되는 업무라면 새 트랜잭션에서 전체 작업을 다시 수행한다. UC002는 좌석 선택을 다시 받아야 하는 충돌이다.
- 운영 환경이 아닌 격리 환경에서만 시연한다. 테스트 절차, 3개 격리 수준 및 부하별 증거는 별도로 전달하는 Phase 3 감사 보고서를 참조한다.

- `backend/tests/sql/money_domain.sql`은 세 CHECK의 카탈로그 정의와 직접 쓰기 오류를 검증한다. 전체 시연 순서와 두 세션 명령은 [SQL 시연](../../database/demo/README.md)에 있다.

### 격리된 시드 DB에서 실행하는 총액·이력 시연 SQL

아래 psql 예제는 0004까지의 마이그레이션과 데모 시드를 적용한 전용 테스트 DB에서 고객 ID 2와 1관을 사용한다. 마지막 ROLLBACK으로 시연용 데이터를 되돌린다.

```sql
BEGIN;
INSERT INTO showtimes(movie_id, room_id, starts_at, ticket_price)
VALUES (1, 1, clock_timestamp() + interval '365 days', 99999999.99)
RETURNING showtime_id \gset

SELECT create_booking(2, :showtime_id, ARRAY(
    SELECT seat_id FROM seats WHERE room_id = 1 ORDER BY seat_id
)) AS demo_booking_id \gset

SET CONSTRAINTS ALL IMMEDIATE;
SELECT b.total_amount, count(bs.seat_id) AS seats, sum(bs.price_at_booking) AS snapshots
FROM bookings b JOIN booking_seats bs USING (booking_id)
WHERE b.booking_id = :demo_booking_id GROUP BY b.booking_id;

SELECT pay_booking(:demo_booking_id, 2);
SELECT cancel_booking(:demo_booking_id, 2);
SELECT status, payment_status, total_amount,
       (SELECT count(*) FROM booking_seats WHERE booking_id = :demo_booking_id) AS seats
FROM bookings WHERE booking_id = :demo_booking_id;
ROLLBACK;
```
