# PostgreSQL ↔ Flask Integration Contract

**Project:** 영화관 예매 및 좌석 관리 시스템 (Cinema Reservation System)
**Applies to:** `backend/migrations/0001_baseline.sql` and `backend/seeds/demo.sql` (canonical) · verified on PostgreSQL 18.6
**Authority:** B01–B05 and BR-DL-001 (D1–D6). This contract implements them; it changes none of them.
**Supersedes:** `CinemaDB_FINAL_PostgreSQL_Handover/docs/05_Integration_Contract_KO.md` (kept unchanged as history; outdated — it still describes `CONFIRMED`, `paid_at` auto-payment and no expiry).

Every statement below was checked against the executed schema and tests (`docs/database/database_test_documentation.md`). Flask code must follow this contract; it must not add columns, tables or triggers (request database changes from Member A).

---

## 1. Physical tables and columns

Logical names in B01–B05 map to physical tables as follows. **Use the physical names in all SQL.**

| Logical | Physical | Primary key |
|---|---|---|
| USERS | `users` | `user_id` |
| MOVIES | `movies` | `movie_id` |
| ROOMS | `theater_rooms` | `room_id` |
| SEATS | `seats` | `seat_id` |
| SCREENINGS | `showtimes` | `showtime_id` |
| BOOKINGS | `bookings` | `booking_id` |
| BOOKING_SEATS | `booking_seats` | `booking_seat_id` |

All keys are `bigint GENERATED ALWAYS AS IDENTITY` (never supply an id on INSERT).

| Table | Columns (all `NOT NULL` unless marked *null*) |
|---|---|
| `users` | `user_id`, `username varchar(60) UNIQUE` (= account ID), `password_hash text`, `role` ∈ {`CUSTOMER`,`ADMIN`} default `CUSTOMER`, `created_at timestamptz` |
| `movies` | `movie_id`, `title varchar(200)`, `genre varchar(100)` *null*, `duration_minutes integer` (1–300), `rating varchar(50)` *null*, `synopsis text` *null*, `release_date date` *null* |
| `theater_rooms` | `room_id`, `room_name varchar(60) UNIQUE` |
| `seats` | `seat_id`, `room_id` → `theater_rooms`, `seat_row char(1)` A–E, `seat_number smallint` 1–10, `UNIQUE(room_id, seat_row, seat_number)` |
| `showtimes` | `showtime_id`, `movie_id` → `movies`, `room_id` → `theater_rooms`, `starts_at timestamptz`, `ends_at timestamptz` (> `starts_at`), `ticket_price numeric(10,2)` ≥ 0 |
| `bookings` | `booking_id`, `user_id` → `users`, `showtime_id` → `showtimes`, `status`, `payment_status`, `booked_at timestamptz`, `expires_at timestamptz`, `total_amount numeric(10,2)` ≥ 0, `paid_at` *null*, `cancelled_at` *null* |
| `booking_seats` | `booking_seat_id`, `booking_id` → `bookings`, `seat_id` → `seats`, `price_at_booking numeric(10,2)` ≥ 0, `UNIQUE(booking_id, seat_id)` |

Relationships: `theater_rooms 1─N seats`, `theater_rooms 1─N showtimes`, `movies 1─N showtimes`, `users 1─N bookings`, `showtimes 1─N bookings`, `bookings 1─N booking_seats` (≥ 1 while `BOOKED`, 0 otherwise), `seats 1─N booking_seats`. There is **no** seat-status column: availability is per screening (§8). No table stores a GUEST; an unauthenticated visitor has no row (D4).

Genre and rating are **free text** (no vocabulary is approved); `release_date` is a `date`. Flask must not invent a list.

## 2. Status values

| Column | Values | Meaning |
|---|---|---|
| `bookings.status` | `BOOKED` | confirmed; holds seats (an unpaid one only until `expires_at`) |
| | `CANCELLED` | whole booking cancelled; seat rows deleted; terminal |
| | `EXPIRED` | unpaid at/after `expires_at`; seat rows deleted; terminal |
| `bookings.payment_status` | `UNPAID` | simulated payment not completed (initial) |
| | `PAID` | simulated payment completed; the booking never expires |

The two are independent: a paid booking that is cancelled stays `CANCELLED` + `PAID` (no refund state exists); an expired booking stays `EXPIRED` + `UNPAID`. `paid_at` is set by the database exactly when `payment_status = 'PAID'`; `cancelled_at` exactly when `status = 'CANCELLED'`. Neither is writable by Flask.

Allowed transitions (enforced by trigger `trg_bookings_validate`; anything else raises `UC007`/`UC006`):
`BOOKED+UNPAID → BOOKED+PAID` (strictly before `expires_at`) · `BOOKED+UNPAID → EXPIRED+UNPAID` (at/after `expires_at`, works after the screening started) · `BOOKED+* → CANCELLED+(same payment)` (before screening start; an overdue unpaid booking must expire instead). `booked_at`, `expires_at`, `total_amount`, `user_id`, `showtime_id` never change.

## 3. Operations Flask must use

Four database functions are the supported way to change bookings. Each is one atomic unit; call it inside the request's transaction. **Never** pass the optional `p_as_of` argument (it exists only so tests can probe the exact deadline).

| Function | Returns | Purpose |
|---|---|---|
| `create_booking(user_id, showtime_id, seat_ids bigint[])` | `booking_id` | C-06 booking confirmation |
| `pay_booking(booking_id, user_id)` | `'PAID'` or `'EXPIRED'` | C-07 simulated payment |
| `cancel_booking(booking_id, user_id)` | `'CANCELLED'` or `'EXPIRED'` | C-09 cancellation |
| `expire_overdue_bookings()` | integer (count expired) | D3 expiry step |

### 3.1 Booking creation (C-06)
Flask first checks the session: user is logged in and `role = 'CUSTOMER'` (D4). Then:
```python
with conn:                                   # BEGIN ... COMMIT; rolls back on any exception
    with conn.cursor() as cur:
        cur.execute("SELECT create_booking(%s, %s, %s)", (user_id, showtime_id, seat_ids))   # seat_ids: Python list of ints
        booking_id = cur.fetchone()[0]
        cur.execute("SELECT status, payment_status, booked_at, expires_at, total_amount FROM bookings WHERE booking_id=%s", (booking_id,))
```
The database does, atomically: runs the expiry step first (D3 #10); locks the screening row; computes `total_amount = ticket_price × number of seats`; inserts the `BOOKED`/`UNPAID` booking with `booked_at = now` and `expires_at = booked_at + 10 minutes`; inserts one `booking_seats` row per seat with `price_at_booking = ticket_price`. If any seat fails (other room, already reserved, nonexistent, started screening…) **nothing** is created. Flask must not send `total_amount`, prices or timestamps. Direct `INSERT`s are still guarded (consistency is checked at COMMIT) but are not the supported path.

### 3.2 Payment (C-07)
```python
with conn:
    with conn.cursor() as cur:
        cur.execute("SELECT pay_booking(%s, %s)", (booking_id, user_id))
        outcome = cur.fetchone()[0]
# 'PAID'    -> success.
# 'EXPIRED' -> payment REJECTED because current_time >= expires_at; the booking was expired
#              in this same transaction. The transaction MUST be committed (leave the 'with'
#              normally) so the expiry persists; only then show "payment window elapsed".
```
Payment is valid only for the caller's own `BOOKED`+`UNPAID` booking strictly before `expires_at`. The row is locked, so payment and expiry can never interleave. Raises `UC011` (not found / not yours), `UC006` (already `CANCELLED`/`EXPIRED`/`PAID`).

### 3.3 Expiration (D3) and how to invoke it
`expire_overdue_bookings()` sets `EXPIRED` on every `BOOKED`+`UNPAID` booking whose `expires_at <= now` and deletes **all** its `booking_seats` rows, in one transaction. It is idempotent (a second call returns 0), never touches `PAID`/`CANCELLED`/`EXPIRED` rows, keeps the parent row, and is not blocked by the screening having started or by the screening-protection rule. Rows locked by a concurrent payment/cancel are skipped (that transaction decides them itself).

**Invocation requirement (team decision: request-time expiry; nothing runs by itself — no pg_cron, worker or scheduler exists):**

| Request | Required |
|---|---|
| C-04 seat availability | call `SELECT expire_overdue_bookings()` **first**, in the same request |
| C-06 booking | built into `create_booking` (no extra call needed) |
| C-07 payment | built into `pay_booking` (it expires that booking itself) |
| C-09 cancel | built into `cancel_booking` |
| C-08 history, A-03 all bookings | call it first so no overdue booking is displayed as `BOOKED` (recommended) |

If Flask forgets the call, the database is still safe (an overdue booking can neither be paid nor cancelled; `create_booking` will not double-book), but availability screens would show stale holds — so make the call part of the shared request helper.

### 3.4 Cancellation (C-09)
```python
with conn:
    with conn.cursor() as cur:
        cur.execute("SELECT cancel_booking(%s, %s)", (booking_id, user_id))
        outcome = cur.fetchone()[0]       # 'CANCELLED' or 'EXPIRED'
```
`'CANCELLED'`: status → `CANCELLED`, **all** seat rows deleted, parent kept, `payment_status` unchanged, `total_amount` retained. `'EXPIRED'`: the booking was an unpaid one past its deadline, so it was expired instead (D3: expired bookings cannot be cancelled) — commit, then tell the user it had expired. Raises `UC011` (not yours), `UC006` (already `CANCELLED`/`EXPIRED`), `UC005` (screening already started). Partial-seat cancellation does not exist.

## 4. Transaction boundaries

* One user action = one database transaction (`with conn:` in psycopg2, or `conn.commit()`/`conn.rollback()` explicitly). Default `READ COMMITTED` is correct; the triggers take their own locks.
* `create_booking` / `pay_booking` / `cancel_booking` / `expire_overdue_bookings` are all-or-nothing: on any exception roll back and nothing changed.
* For `pay_booking` and `cancel_booking`, a returned `'EXPIRED'` is a **committed** outcome, not an error: do not raise before committing.
* Never run `SET CONSTRAINTS … IMMEDIATE` around `create_booking` (booking and seats are validated together at COMMIT).
* Do not check availability in Python and then insert separately (check-then-write race): always call `create_booking` and handle `UC002`.
* Do not issue direct `UPDATE bookings`, `INSERT/DELETE booking_seats` or `UPDATE showtimes` for booked data except as stated in §7 (admin editing of unbooked screenings).

## 5. Seat availability (C-04) — query behaviour

Run in the same transaction as `SELECT expire_overdue_bookings();`. A seat is unavailable only if a seat row exists for a `BOOKED` booking of that screening that is either `PAID` or still inside its payment window; cancelled/expired bookings have no seat rows. Verified: the query shows an overdue-but-unprocessed booking's seats as available even before expiry runs.
```sql
SELECT se.seat_id, se.seat_row, se.seat_number,
       NOT EXISTS (
         SELECT 1 FROM booking_seats bs JOIN bookings b ON b.booking_id = bs.booking_id
         WHERE b.showtime_id = %(showtime)s AND bs.seat_id = se.seat_id AND b.status = 'BOOKED'
           AND (b.payment_status = 'PAID' OR b.expires_at > clock_timestamp())
       ) AS is_available
FROM showtimes s JOIN seats se ON se.room_id = s.room_id
WHERE s.showtime_id = %(showtime)s
ORDER BY se.seat_row, se.seat_number;
```
Seat selection (C-05) holds nothing; seats are held only by a successful `create_booking`. Browsing (C-02…C-05) needs no login (D4).

Other read queries Flask needs:
```sql
-- C-08 / A-03: booking summary (seat details exist only for BOOKED)
SELECT b.booking_id, m.title, s.starts_at, s.ends_at, r.room_name, b.booked_at, b.expires_at,
       b.total_amount, b.status, b.payment_status
FROM bookings b JOIN showtimes s ON s.showtime_id=b.showtime_id JOIN movies m ON m.movie_id=s.movie_id
JOIN theater_rooms r ON r.room_id=s.room_id
WHERE b.user_id = %s ORDER BY b.booked_at DESC;                         -- A-03: drop the WHERE (ADMIN only)
SELECT se.seat_row, se.seat_number, bs.price_at_booking
FROM booking_seats bs JOIN seats se ON se.seat_id=bs.seat_id WHERE bs.booking_id=%s;   -- empty for CANCELLED/EXPIRED: never promise seats
```
Display `expires_at` for `BOOKED`+`UNPAID` rows as the payment deadline.

## 6. Errors and constraints Flask must handle

Read `e.pgcode` (psycopg2). The custom `UC…` codes are stable; do not match on message text.

| SQLSTATE | Raised when | Suggested response |
|---|---|---|
| `UC001` | admin edits a screening that has any booking record (any status; any attribute incl. price/end time) — D2 | "has bookings; cannot be modified" |
| `UC002` | seat already reserved for this screening (incl. lost race) | ask user to re-select seats |
| `UC003` | seat belongs to another room | internal/tampering error |
| `UC004` | screening already started (booking) | block |
| `UC005` | cancellation after screening start | block |
| `UC006` | payment/cancel not allowed: booking already `CANCELLED`/`EXPIRED`/`PAID`, or payment window elapsed (direct SQL) | explain state |
| `UC007` | illegal change (immutable column, illegal transition, direct delete of seat rows, …) | internal error: Flask must not issue such statements |
| `UC008` | booking owner is not a `CUSTOMER` (e.g. ADMIN) | block |
| `UC009` | price snapshot ≠ screening price, or `total_amount` ≠ sum of snapshots | internal error (use `create_booking`) |
| `UC010` | empty/duplicate seat list, or `BOOKED` booking without seats at COMMIT | "select at least one seat" |
| `UC011` | booking/screening not found **for this user** | 404 |
| `23505` | duplicate `username` (registration), duplicate seat position | "account ID taken" |
| `23503` | unknown user / seat / screening / movie / room id | 400 |
| `23514` | CHECK violation (invalid role, duration, row/number, price < 0, `ends_at <= starts_at`) | validation message |
| `23P01` | screening overlaps another in the same room (BR-04; real `[start,end)` intervals, **no buffer**) | show conflict, ask for another time |
| `23001` | unexpected attempt to remove a referenced row | internal error |

Enforced by the database (do not duplicate as the only guard, but still validate for UX): role/status domains, seat ↔ room ownership, one active booking per seat per screening (race-safe: the screening row is locked), no overlap, no booking/cancel after start, atomic booking + seats, price snapshot = screening price, `total_amount` = sum of snapshots (immutable, kept after cancel/expiry), D1/D2/D3 transitions.

## 7. Application (Flask) responsibilities — not enforced by the database

| Area | Flask must |
|---|---|
| Authentication (D4, BR-05) | session login; browsing/availability public; require login for confirm/pay/cancel; **no GUEST account**; check `role` |
| Registration (D5) | only account ID + password. `INSERT INTO users(username, password_hash)` — **never pass `role`** (default `CUSTOMER`; the DB would accept `ADMIN`, so public registration must not allow it). Hash with a one-way password hash (e.g. Werkzeug `generate_password_hash`), never plaintext |
| Ownership (BR-09) | pass `session user_id` to `pay_booking`/`cancel_booking` and filter history by it |
| Authorisation (BR-13) | movies and screenings add/edit/delete and A-03 only for `ADMIN` |
| Expiry invocation | per §3.3 |
| Admin screening add | `INSERT INTO showtimes(movie_id, room_id, starts_at, ends_at, ticket_price)`; `ends_at` may be omitted (defaults to start + movie duration, stored) |
| Admin screening edit | `UPDATE showtimes SET …` only; the database rejects with `UC001` if any booking row exists, any status. Catch it; optionally pre-check `NOT EXISTS (SELECT 1 FROM bookings WHERE showtime_id=…)` for UX |
| Admin movie edit | `UPDATE movies`; changing `duration_minutes` is allowed and never moves existing screenings (their `ends_at` is stored) |
| Admin movie deletion | Lock the movie and its screenings, then remove the movie and its upcoming unbooked screenings in one transaction. Preserve all rows if any screening has started or has any booking history. |
| Admin screening deletion | Lock the screening row against concurrent reservations. Remove the screening only if its start time is in the future and no booking references it. |
| Time | convert Seoul-local input to `timestamptz` explicitly; never compare with the Flask host clock — the database decides every deadline; show times in `Asia/Seoul` |
| SQL safety | parameter binding only |
| Demo accounts | The demo seed creates `admin`, `customer1` and `customer2`. Demo login details and password rotation instructions are in the root README. |

## 8. PostgreSQL connection requirements

* PostgreSQL **14+** (verified on 18.6 only). Extension `btree_gist` is required by `schema.sql` (shipped with PostgreSQL; creating it needs a role allowed to — the database owner can since PG 13).
* Driver: Flask uses psycopg2 and parameterized SQL. Dependencies are pinned in `backend/requirements.txt`.
* Configuration through environment variables (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`); `.env` is git-ignored; never commit credentials.
* The functions and triggers run with the caller's privileges. The Flask runtime role needs `EXECUTE`, `SELECT` on all application tables, `INSERT` on `users`, `INSERT/UPDATE` on `bookings`, `INSERT/DELETE` on `booking_seats` and `INSERT/UPDATE/DELETE` on `movies` and `showtimes`. The baseline creates no roles. Fresh Compose volumes apply `backend/migrations/compose-role.sql` and `backend/migrations/0002_movie_delete_permissions.sql`. Use a non-owner, non-superuser application role for an externally managed database. Use the owner role for setup and tests.
* Create the database empty, then: `psql -X -v ON_ERROR_STOP=1 -d <db> -f backend/migrations/0001_baseline.sql` and `… -f backend/seeds/demo.sql` (once). Tests: `bash database/tests/run_all.sh` on a **disposable** database only.
* Timestamps are `timestamptz`; the seed uses 14 consecutive `Asia/Seoul` days starting on the day it is run.
