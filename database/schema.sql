-- =============================================================================
-- Cinema Reservation System - canonical PostgreSQL schema (PostgreSQL 14+)
--
-- Source of truth: docs/business/business_rules_decision_log.md (BR-DL-001, D1-D6)
-- Derived from Member A's handover (CinemaDB_FINAL_PostgreSQL_Handover/, kept
-- unmodified as the historical reference) and corrected per
-- docs/database/handover_reconciliation_report.md (DB-01 ... DB-10).
--
-- Apply ONCE to a NEW, EMPTY database:
--   psql -X -v ON_ERROR_STOP=1 -d <db> -f database/schema.sql
-- Requires the btree_gist extension (shipped with PostgreSQL; trusted since 13).
--
-- Time convention: every instant is timestamptz. Business-local time is
-- Asia/Seoul; convert at the application edge. All time rules use
-- clock_timestamp() (real time), never the application host clock.
--
-- SQLSTATEs raised by this schema (class 'UC' = user-defined, Cinema):
--   UC001 screening is locked by booking records (D2)
--   UC002 seat already reserved for this screening (BR-08)
--   UC003 seat does not belong to the screening's room (BR-07)
--   UC004 screening already started (BR-12)
--   UC005 cancellation after screening start (BR-10)
--   UC006 payment / cancellation not allowed: window elapsed or wrong state (D3)
--   UC007 illegal change (immutable column or illegal status transition)
--   UC008 only CUSTOMER accounts may own bookings
--   UC009 price snapshot / total_amount inconsistency (D6)
--   UC010 booking has no seat / bad seat list
--   UC011 booking or screening not found for this caller
-- Standard SQLSTATEs also occur: 23505 unique, 23503 FK, 23514 check,
-- 23P01 exclusion (overlapping screenings in one room, BR-04).
-- =============================================================================
BEGIN;

CREATE EXTENSION IF NOT EXISTS btree_gist;

-- ----------------------------------------------------------------- tables ---
CREATE TABLE users (
 user_id       bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 username      varchar(60)  NOT NULL UNIQUE,              -- the "account ID" (D5)
 password_hash text         NOT NULL,                     -- one-way hash only (D5)
 role          varchar(10)  NOT NULL DEFAULT 'CUSTOMER'
               CHECK (role IN ('CUSTOMER','ADMIN')),      -- no GUEST role (D4)
 created_at    timestamptz  NOT NULL DEFAULT now()
);

-- D5: the six approved movie attributes. genre/rating are free text: BR-DL-001
-- sec. 6 states no vocabulary has been approved, so no ENUM / list is imposed.
CREATE TABLE movies (
 movie_id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 title            varchar(200) NOT NULL,
 genre            varchar(100),
 duration_minutes integer      NOT NULL CHECK (duration_minutes BETWEEN 1 AND 300),
 rating           varchar(50),
 synopsis         text,
 release_date     date,
 -- Site-relative path of a poster file served by the frontend (no host, no '..').
 poster_url       varchar(255) CHECK (poster_url ~ '^/images/posters/[A-Za-z0-9][A-Za-z0-9._-]*\.(jpg|png)$')
);

CREATE TABLE theater_rooms (
 room_id   bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 room_name varchar(60) NOT NULL UNIQUE
);

CREATE TABLE seats (
 seat_id     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 room_id     bigint   NOT NULL REFERENCES theater_rooms(room_id) ON DELETE RESTRICT,
 seat_row    char(1)  NOT NULL CHECK (seat_row IN ('A','B','C','D','E')),
 seat_number smallint NOT NULL CHECK (seat_number BETWEEN 1 AND 10),
 UNIQUE (room_id, seat_row, seat_number)
);                                                        -- no global seat status (BR-DL-001 5.2 #9)

-- DB-02: stored end time. DB-03: overlap uses the real [start, end) interval
-- only; there is NO cleaning buffer. The EXCLUDE constraint is declarative and
-- race-free (no trigger, no explicit lock needed).
CREATE TABLE showtimes (
 showtime_id  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 movie_id     bigint        NOT NULL REFERENCES movies(movie_id) ON DELETE RESTRICT,
 room_id      bigint        NOT NULL REFERENCES theater_rooms(room_id) ON DELETE RESTRICT,
 starts_at    timestamptz   NOT NULL,
 ends_at      timestamptz   NOT NULL,                    -- defaulted from movie duration if omitted
 ticket_price numeric(10,2) NOT NULL CHECK (ticket_price >= 0),   -- per screening (D6)
 CONSTRAINT showtimes_end_after_start CHECK (ends_at > starts_at),
 CONSTRAINT showtimes_no_room_overlap
   EXCLUDE USING gist (room_id WITH =, tstzrange(starts_at, ends_at, '[)') WITH &&)
);

CREATE TABLE bookings (
 booking_id     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 user_id        bigint        NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
 showtime_id    bigint        NOT NULL REFERENCES showtimes(showtime_id) ON DELETE RESTRICT,
 status         varchar(10)   NOT NULL DEFAULT 'BOOKED'
                CHECK (status IN ('BOOKED','CANCELLED','EXPIRED')),
 payment_status varchar(10)   NOT NULL DEFAULT 'UNPAID'
                CHECK (payment_status IN ('UNPAID','PAID')),
 booked_at      timestamptz   NOT NULL DEFAULT now(),    -- forced to clock_timestamp() by trigger
 expires_at     timestamptz   NOT NULL,                  -- set by trigger = booked_at + 10 min
 total_amount   numeric(10,2) NOT NULL CHECK (total_amount >= 0),
 paid_at        timestamptz,                             -- technical: set only when PAID
 cancelled_at   timestamptz,                             -- technical: set only when CANCELLED
 CONSTRAINT bookings_expiry_is_10_minutes CHECK (expires_at = booked_at + interval '10 minutes'),
 CONSTRAINT bookings_paid_at_matches CHECK ((payment_status = 'PAID') = (paid_at IS NOT NULL)),
 CONSTRAINT bookings_cancelled_at_matches CHECK ((status = 'CANCELLED') = (cancelled_at IS NOT NULL)),
 CONSTRAINT bookings_paid_never_expired CHECK (NOT (status = 'EXPIRED' AND payment_status = 'PAID'))
);

CREATE TABLE booking_seats (
 booking_seat_id  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 booking_id       bigint        NOT NULL REFERENCES bookings(booking_id) ON DELETE CASCADE,
 seat_id          bigint        NOT NULL REFERENCES seats(seat_id) ON DELETE RESTRICT,
 price_at_booking numeric(10,2) NOT NULL CHECK (price_at_booking >= 0),  -- unit-price snapshot (D6)
 UNIQUE (booking_id, seat_id)
);

CREATE INDEX idx_showtimes_movie_start        ON showtimes(movie_id, starts_at);
CREATE INDEX idx_showtimes_room_start         ON showtimes(room_id, starts_at);
CREATE INDEX idx_bookings_user                ON bookings(user_id, booked_at DESC);
CREATE INDEX idx_bookings_showtime_status     ON bookings(showtime_id, status);
CREATE INDEX idx_booking_seats_seat           ON booking_seats(seat_id);
-- supports the expiry scan (a technical index, not a business rule)
CREATE INDEX idx_bookings_pending_expiry      ON bookings(expires_at)
       WHERE status = 'BOOKED' AND payment_status = 'UNPAID';

-- ------------------------------------------------------- showtimes triggers ---
-- Default the stored end time from the movie duration ONLY when it is omitted.
-- The value is stored, so a later change of movies.duration_minutes never moves
-- an existing screening (DB-02/DB-03). An explicit end time is always honoured.
CREATE FUNCTION showtimes_default_end_time() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE v_minutes integer;
BEGIN
 IF NEW.ends_at IS NULL THEN
   SELECT duration_minutes INTO v_minutes FROM movies WHERE movie_id = NEW.movie_id;
   IF v_minutes IS NOT NULL THEN
     NEW.ends_at := NEW.starts_at + v_minutes * interval '1 minute';
   END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER trg_showtimes_default_end_time BEFORE INSERT OR UPDATE ON showtimes
FOR EACH ROW EXECUTE FUNCTION showtimes_default_end_time();

-- D2: once ANY booking row (BOOKED, CANCELLED or EXPIRED) references a screening,
-- none of its attributes may change. Fires on every UPDATE and compares all five
-- business attributes, so ticket_price and ends_at are protected too.
CREATE FUNCTION showtimes_protect_booked() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF (NEW.movie_id, NEW.room_id, NEW.starts_at, NEW.ends_at, NEW.ticket_price)
    IS DISTINCT FROM
    (OLD.movie_id, OLD.room_id, OLD.starts_at, OLD.ends_at, OLD.ticket_price)
    AND EXISTS (SELECT 1 FROM bookings WHERE showtime_id = OLD.showtime_id) THEN
   RAISE EXCEPTION 'Cannot modify a screening that has booking records' USING ERRCODE = 'UC001';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER trg_showtimes_protect_booked BEFORE UPDATE ON showtimes
FOR EACH ROW EXECUTE FUNCTION showtimes_protect_booked();

-- -------------------------------------------------------- bookings triggers ---
-- Booking lifecycle (D1, D3). Allowed transitions only:
--   BOOKED/UNPAID -> BOOKED/PAID        strictly before expires_at
--   BOOKED/UNPAID -> EXPIRED/UNPAID     at or after expires_at (works after screening start)
--   BOOKED/*      -> CANCELLED/(same)   before screening start; an UNPAID booking whose
--                                       window has elapsed must expire instead
-- CANCELLED and EXPIRED are terminal. PAID never expires. Payment status never
-- changes on cancellation or expiry. Identity, timestamps and total are immutable.
CREATE FUNCTION bookings_validate() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
 v_now   timestamptz := clock_timestamp();
 v_role  text;
 v_start timestamptz;
BEGIN
 IF TG_OP = 'INSERT' THEN
   SELECT role INTO v_role FROM users WHERE user_id = NEW.user_id;
   IF v_role IS NULL THEN
     RAISE EXCEPTION 'User does not exist' USING ERRCODE = '23503';
   END IF;
   IF v_role IS DISTINCT FROM 'CUSTOMER' THEN
     RAISE EXCEPTION 'Only customers can book' USING ERRCODE = 'UC008';
   END IF;
   SELECT starts_at INTO v_start FROM showtimes WHERE showtime_id = NEW.showtime_id;
   IF v_start <= v_now THEN
     RAISE EXCEPTION 'Showtime has already started' USING ERRCODE = 'UC004';
   END IF;
   IF NEW.status <> 'BOOKED' OR NEW.payment_status <> 'UNPAID'
      OR NEW.paid_at IS NOT NULL OR NEW.cancelled_at IS NOT NULL THEN
     RAISE EXCEPTION 'A new booking must be BOOKED and UNPAID' USING ERRCODE = 'UC007';
   END IF;
   NEW.booked_at  := v_now;
   NEW.expires_at := v_now + interval '10 minutes';        -- D3
   RETURN NEW;
 END IF;

 -- UPDATE
 IF NEW.booking_id <> OLD.booking_id OR NEW.user_id <> OLD.user_id
    OR NEW.showtime_id <> OLD.showtime_id OR NEW.booked_at <> OLD.booked_at
    OR NEW.expires_at <> OLD.expires_at OR NEW.total_amount <> OLD.total_amount THEN
   RAISE EXCEPTION 'Booking identity, timestamps and total_amount cannot be changed' USING ERRCODE = 'UC007';
 END IF;

 IF NEW.status = OLD.status AND NEW.payment_status = OLD.payment_status THEN
   IF NEW.paid_at IS DISTINCT FROM OLD.paid_at OR NEW.cancelled_at IS DISTINCT FROM OLD.cancelled_at THEN
     RAISE EXCEPTION 'paid_at / cancelled_at cannot be edited directly' USING ERRCODE = 'UC007';
   END IF;
   RETURN NEW;                                             -- no state change
 END IF;

 IF OLD.status <> 'BOOKED' THEN
   RAISE EXCEPTION 'Booking is % and can no longer change', OLD.status USING ERRCODE = 'UC007';
 END IF;

 IF NEW.status = 'BOOKED' THEN                             -- payment
   IF OLD.payment_status = 'UNPAID' AND NEW.payment_status = 'PAID' THEN
     IF v_now >= OLD.expires_at THEN
       RAISE EXCEPTION 'Payment window has elapsed' USING ERRCODE = 'UC006';
     END IF;
     NEW.paid_at := v_now;
     NEW.cancelled_at := NULL;
     RETURN NEW;
   END IF;
   RAISE EXCEPTION 'Illegal payment status transition % -> %', OLD.payment_status, NEW.payment_status
     USING ERRCODE = 'UC007';

 ELSIF NEW.status = 'CANCELLED' THEN                       -- D1
   IF NEW.payment_status <> OLD.payment_status THEN
     RAISE EXCEPTION 'Payment status cannot change while cancelling' USING ERRCODE = 'UC007';
   END IF;
   IF OLD.payment_status = 'UNPAID' AND v_now >= OLD.expires_at THEN
     RAISE EXCEPTION 'Payment window has elapsed; the booking must expire, not be cancelled'
       USING ERRCODE = 'UC006';
   END IF;
   SELECT starts_at INTO v_start FROM showtimes WHERE showtime_id = OLD.showtime_id;
   IF v_start <= v_now THEN
     RAISE EXCEPTION 'Cannot cancel after showtime starts' USING ERRCODE = 'UC005';
   END IF;
   NEW.cancelled_at := v_now;
   NEW.paid_at := OLD.paid_at;
   RETURN NEW;

 ELSIF NEW.status = 'EXPIRED' THEN                         -- D3: deliberately NOT blocked by screening start
   IF OLD.payment_status <> 'UNPAID' OR NEW.payment_status <> 'UNPAID' THEN
     RAISE EXCEPTION 'Only unpaid bookings can expire' USING ERRCODE = 'UC007';
   END IF;
   IF v_now < OLD.expires_at THEN
     RAISE EXCEPTION 'Payment window has not elapsed' USING ERRCODE = 'UC006';
   END IF;
   NEW.cancelled_at := NULL;
   NEW.paid_at := NULL;
   RETURN NEW;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER trg_bookings_validate BEFORE INSERT OR UPDATE ON bookings
FOR EACH ROW EXECUTE FUNCTION bookings_validate();

-- D1/D3: leaving BOOKED releases ALL seat rows in the same statement/transaction.
CREATE FUNCTION bookings_release_seats() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF OLD.status = 'BOOKED' AND NEW.status IN ('CANCELLED','EXPIRED') THEN
   DELETE FROM booking_seats WHERE booking_id = NEW.booking_id;
 END IF;
 RETURN NULL;
END $$;
CREATE TRIGGER trg_bookings_release_seats AFTER UPDATE OF status ON bookings
FOR EACH ROW EXECUTE FUNCTION bookings_release_seats();

-- ---------------------------------------------------- booking_seats triggers ---
-- Locks the screening row first: this serializes concurrent reservations of one
-- screening, so the EXISTS check below is race-safe (verified by concurrency tests).
CREATE FUNCTION booking_seats_validate() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
 v_showtime bigint; v_status text; v_room bigint; v_start timestamptz;
 v_price numeric(10,2); v_seat_room bigint;
BEGIN
 IF TG_OP = 'UPDATE' THEN
   RAISE EXCEPTION 'Seat allocations are immutable' USING ERRCODE = 'UC007';
 END IF;
 SELECT showtime_id, status INTO v_showtime, v_status FROM bookings WHERE booking_id = NEW.booking_id;
 IF v_status IS DISTINCT FROM 'BOOKED' THEN
   RAISE EXCEPTION 'Booking is not BOOKED' USING ERRCODE = 'UC007';
 END IF;
 SELECT room_id, starts_at, ticket_price INTO v_room, v_start, v_price
   FROM showtimes WHERE showtime_id = v_showtime FOR UPDATE;
 IF v_start <= clock_timestamp() THEN
   RAISE EXCEPTION 'Showtime has already started' USING ERRCODE = 'UC004';
 END IF;
 SELECT room_id INTO v_seat_room FROM seats WHERE seat_id = NEW.seat_id;
 IF v_seat_room IS NULL THEN
   RAISE EXCEPTION 'Seat does not exist' USING ERRCODE = '23503';
 END IF;
 IF v_room IS DISTINCT FROM v_seat_room THEN
   RAISE EXCEPTION 'Seat belongs to another room' USING ERRCODE = 'UC003';
 END IF;
 IF NEW.price_at_booking IS NULL THEN
   NEW.price_at_booking := v_price;                         -- snapshot defaults to the screening price
 ELSIF NEW.price_at_booking <> v_price THEN
   RAISE EXCEPTION 'Price snapshot must equal the screening ticket price' USING ERRCODE = 'UC009';
 END IF;
 IF EXISTS (
   SELECT 1 FROM booking_seats bs JOIN bookings b ON b.booking_id = bs.booking_id
   WHERE b.showtime_id = v_showtime AND b.status = 'BOOKED' AND bs.seat_id = NEW.seat_id
 ) THEN
   RAISE EXCEPTION 'Seat already reserved for this showtime' USING ERRCODE = 'UC002';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER trg_booking_seats_validate BEFORE INSERT OR UPDATE ON booking_seats
FOR EACH ROW EXECUTE FUNCTION booking_seats_validate();

-- Seat rows of a BOOKED booking can only be released by cancelling/expiring it.
CREATE FUNCTION booking_seats_protect_delete() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF EXISTS (SELECT 1 FROM bookings WHERE booking_id = OLD.booking_id AND status = 'BOOKED') THEN
   RAISE EXCEPTION 'Cancel or expire the booking before releasing its seats' USING ERRCODE = 'UC007';
 END IF;
 RETURN OLD;
END $$;
CREATE TRIGGER trg_booking_seats_protect_delete BEFORE DELETE ON booking_seats
FOR EACH ROW EXECUTE FUNCTION booking_seats_protect_delete();

-- D6 + atomic creation, checked at COMMIT (deferred) so a booking and its seats
-- may be inserted in any order inside one transaction:
--   BOOKED      -> >= 1 seat row AND total_amount = SUM(price_at_booking)
--   CANCELLED / EXPIRED -> no seat rows remain (D1, D3)
-- total_amount is immutable, so it stays available after cancellation/expiry.
CREATE FUNCTION booking_check_consistency() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE v_status text; v_total numeric(10,2); v_cnt integer; v_sum numeric(10,2);
BEGIN
 SELECT status, total_amount INTO v_status, v_total FROM bookings WHERE booking_id = NEW.booking_id;
 IF v_status IS NULL THEN RETURN NULL; END IF;
 SELECT count(*), COALESCE(sum(price_at_booking), 0) INTO v_cnt, v_sum
   FROM booking_seats WHERE booking_id = NEW.booking_id;
 IF v_status = 'BOOKED' THEN
   IF v_cnt = 0 THEN
     RAISE EXCEPTION 'A BOOKED booking must contain at least one seat' USING ERRCODE = 'UC010';
   END IF;
   IF v_sum <> v_total THEN
     RAISE EXCEPTION 'total_amount (%) must equal the sum of seat price snapshots (%)', v_total, v_sum
       USING ERRCODE = 'UC009';
   END IF;
 ELSIF v_cnt <> 0 THEN
   RAISE EXCEPTION 'A % booking must not keep seat rows', v_status USING ERRCODE = 'UC007';
 END IF;
 RETURN NULL;
END $$;
-- NOTE: PostgreSQL fires same-event AFTER triggers in alphabetical order. This trigger
-- is named so that it sorts AFTER trg_bookings_release_seats; otherwise, if a session
-- ever switched constraints to IMMEDIATE, the check would run before the seat rows of a
-- cancelled/expired booking were deleted. (create_booking itself requires the default
-- DEFERRED mode: do not run SET CONSTRAINTS ... IMMEDIATE around it.)
CREATE CONSTRAINT TRIGGER trg_bookings_z_consistency AFTER INSERT OR UPDATE OF status ON bookings
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION booking_check_consistency();
CREATE CONSTRAINT TRIGGER trg_booking_seats_consistency AFTER INSERT ON booking_seats
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION booking_check_consistency();

-- ------------------------------------------------- operations for Flask ---
-- Each function is ONE atomic unit of work: it either completes entirely or the
-- caller's transaction rolls back. Flask calls them inside its own transaction
-- (BEGIN ... COMMIT). Nothing here schedules anything: expiry runs only when
-- called (request-time expiry, decided by the team).
--
-- p_as_of exists ONLY so tests can probe the exact deadline. Flask must NOT pass it.

-- D3: expire every overdue unpaid booking. Idempotent: only BOOKED+UNPAID rows with
-- expires_at <= p_as_of are touched, so repeated calls expire nothing new and a
-- PAID/CANCELLED/EXPIRED row is never altered. Rows currently locked by a
-- concurrent payment/cancel are skipped (that transaction decides them itself).
-- Seat rows are deleted by trg_bookings_release_seats in the same transaction.
-- Not blocked by screening start (bookings_validate has no such check for EXPIRED).
CREATE FUNCTION expire_overdue_bookings(p_as_of timestamptz DEFAULT clock_timestamp())
RETURNS integer LANGUAGE plpgsql AS $$
DECLARE v_count integer;
BEGIN
 UPDATE bookings SET status = 'EXPIRED'
 WHERE booking_id IN (
   SELECT booking_id FROM bookings
   WHERE status = 'BOOKED' AND payment_status = 'UNPAID' AND expires_at <= p_as_of
   ORDER BY booking_id
   FOR UPDATE SKIP LOCKED
 );
 GET DIAGNOSTICS v_count = ROW_COUNT;
 RETURN v_count;
END $$;

-- C-06: create a BOOKED + UNPAID booking and all its seat rows atomically.
-- total_amount = screening ticket_price x seat count; every seat row snapshots
-- that price (D6). Runs the expiry step first (D3 #10). Raises on any invalid
-- seat (nothing is created). Returns the new booking_id.
CREATE FUNCTION create_booking(p_user_id bigint, p_showtime_id bigint, p_seat_ids bigint[])
RETURNS bigint LANGUAGE plpgsql AS $$
DECLARE v_price numeric(10,2); v_id bigint; v_n integer;
BEGIN
 v_n := COALESCE(cardinality(p_seat_ids), 0);
 IF v_n = 0 THEN
   RAISE EXCEPTION 'At least one seat is required' USING ERRCODE = 'UC010';
 END IF;
 IF (SELECT count(DISTINCT s) FROM unnest(p_seat_ids) AS s) <> v_n THEN
   RAISE EXCEPTION 'Seat list contains duplicates or NULL' USING ERRCODE = 'UC010';
 END IF;
 SELECT ticket_price INTO v_price FROM showtimes WHERE showtime_id = p_showtime_id FOR UPDATE;
 IF NOT FOUND THEN
   RAISE EXCEPTION 'Screening not found' USING ERRCODE = 'UC011';
 END IF;
 PERFORM expire_overdue_bookings();
 INSERT INTO bookings(user_id, showtime_id, total_amount)
 VALUES (p_user_id, p_showtime_id, v_price * v_n)
 RETURNING booking_id INTO v_id;
 INSERT INTO booking_seats(booking_id, seat_id, price_at_booking)
 SELECT v_id, s, v_price FROM unnest(p_seat_ids) AS s ORDER BY s;
 RETURN v_id;
END $$;

-- C-07: simulated payment. Returns the resulting state:
--   'PAID'    paid strictly before expires_at
--   'EXPIRED' deadline reached (p_as_of >= expires_at): payment REJECTED and the
--             booking is expired in the same transaction (D3); caller must COMMIT
--             so the expiry persists.
-- Raises UC011 (not found / not the caller's booking) or UC006 (CANCELLED, EXPIRED,
-- already PAID). The row is locked, so payment and expiry cannot interleave.
CREATE FUNCTION pay_booking(p_booking_id bigint, p_user_id bigint,
                            p_as_of timestamptz DEFAULT clock_timestamp())
RETURNS text LANGUAGE plpgsql AS $$
DECLARE b bookings%ROWTYPE;
BEGIN
 SELECT * INTO b FROM bookings WHERE booking_id = p_booking_id AND user_id = p_user_id FOR UPDATE;
 IF NOT FOUND THEN
   RAISE EXCEPTION 'Booking not found' USING ERRCODE = 'UC011';
 END IF;
 IF b.status <> 'BOOKED' THEN
   RAISE EXCEPTION 'Booking is % and cannot be paid', b.status USING ERRCODE = 'UC006';
 END IF;
 IF b.payment_status = 'PAID' THEN
   RAISE EXCEPTION 'Booking is already paid' USING ERRCODE = 'UC006';
 END IF;
 IF p_as_of >= b.expires_at THEN
   UPDATE bookings SET status = 'EXPIRED' WHERE booking_id = b.booking_id;
   RETURN 'EXPIRED';
 END IF;
 UPDATE bookings SET payment_status = 'PAID' WHERE booking_id = b.booking_id;
 RETURN 'PAID';
END $$;

-- C-09: cancel the whole booking (D1). Returns the resulting state:
--   'CANCELLED' status changed, all seat rows deleted, payment_status unchanged
--   'EXPIRED'   the booking was an UNPAID one whose deadline had passed: it is
--               expired instead (D3: expired bookings cannot be cancelled)
-- Raises UC011 (not found / not the caller's), UC006 (already CANCELLED/EXPIRED),
-- UC005 (screening already started).
CREATE FUNCTION cancel_booking(p_booking_id bigint, p_user_id bigint,
                               p_as_of timestamptz DEFAULT clock_timestamp())
RETURNS text LANGUAGE plpgsql AS $$
DECLARE b bookings%ROWTYPE;
BEGIN
 SELECT * INTO b FROM bookings WHERE booking_id = p_booking_id AND user_id = p_user_id FOR UPDATE;
 IF NOT FOUND THEN
   RAISE EXCEPTION 'Booking not found' USING ERRCODE = 'UC011';
 END IF;
 IF b.status <> 'BOOKED' THEN
   RAISE EXCEPTION 'Booking is % and cannot be cancelled', b.status USING ERRCODE = 'UC006';
 END IF;
 IF b.payment_status = 'UNPAID' AND p_as_of >= b.expires_at THEN
   UPDATE bookings SET status = 'EXPIRED' WHERE booking_id = b.booking_id;
   RETURN 'EXPIRED';
 END IF;
 UPDATE bookings SET status = 'CANCELLED' WHERE booking_id = b.booking_id;
 RETURN 'CANCELLED';
END $$;

COMMIT;
