-- =============================================================================
-- Database integrity tests for D1-D6 (+ DB-02/DB-03 and the retained A rules).
--
-- Target : a NEW, DISPOSABLE database with database/schema.sql and
--          database/seed.sql applied. NEVER a shared / demo database.
-- Run    : psql -X -v ON_ERROR_STOP=1 -d <disposable_db> -f database/tests/integrity_tests.sql
-- Effect : everything runs in ONE transaction that is ROLLED BACK; nothing persists.
-- Result : prints "PASS <label>" per check; the first failure raises
--          "FAIL: <label>" and psql exits non-zero (ON_ERROR_STOP).
-- Needs  : the connecting role must OWN the tables (true for the creating role).
--          Time is simulated only inside this rolled-back transaction by
--          temporarily disabling USER triggers (helpers backdate / set_deadline /
--          move_show_start); no application path does that.
-- =============================================================================
\set ON_ERROR_STOP on
\pset pager off
SET client_min_messages = notice;

BEGIN;
CREATE TEMP TABLE test_log(label text);

-- ------------------------------------------------------------------ helpers ---
CREATE FUNCTION pg_temp.ok(p_cond boolean, p_label text) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
 IF p_cond IS NOT TRUE THEN RAISE EXCEPTION 'FAIL: %', p_label; END IF;
 INSERT INTO test_log VALUES (p_label);
 RAISE NOTICE 'PASS %', p_label;
END $$;

-- p_sql must be ONE statement; it must raise SQLSTATE p_state.
CREATE FUNCTION pg_temp.expect_err(p_sql text, p_state text, p_label text) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
 BEGIN
   EXECUTE p_sql;
 EXCEPTION WHEN OTHERS THEN
   DECLARE v_state text := SQLSTATE; v_msg text := SQLERRM; BEGIN
   SET CONSTRAINTS ALL DEFERRED;
   IF v_state = p_state THEN
     INSERT INTO test_log VALUES (p_label);
     RAISE NOTICE 'PASS % [%: %]', p_label, v_state, v_msg;
     RETURN;
   END IF;
   RAISE EXCEPTION 'FAIL: % - expected SQLSTATE % but got % (%)', p_label, p_state, v_state, v_msg;
   END;
 END;
 RAISE EXCEPTION 'FAIL: % - statement was ACCEPTED, expected SQLSTATE %', p_label, p_state;
END $$;

-- screening fixture: room 1, movie 1 (default end), unique far-future day per n
CREATE FUNCTION pg_temp.mk_show(n integer, p_price numeric DEFAULT 12000, p_room integer DEFAULT 1)
RETURNS bigint LANGUAGE plpgsql AS $$
DECLARE v bigint;
BEGIN
 INSERT INTO showtimes(movie_id, room_id, starts_at, ticket_price)
 SELECT (SELECT min(movie_id) FROM movies), (SELECT room_id FROM theater_rooms ORDER BY room_id OFFSET p_room-1 LIMIT 1),
        date_trunc('hour', now()) + (100 + n) * interval '1 day', p_price
 RETURNING showtime_id INTO v;
 RETURN v;
END $$;

CREATE FUNCTION pg_temp.seat(p_show bigint, p_row char, p_num integer) RETURNS bigint LANGUAGE sql AS $$
 SELECT se.seat_id FROM showtimes s JOIN seats se ON se.room_id = s.room_id
 WHERE s.showtime_id = p_show AND se.seat_row = p_row AND se.seat_number = p_num $$;

CREATE FUNCTION pg_temp.cust(p_name text DEFAULT 'customer_demo') RETURNS bigint LANGUAGE sql AS $$
 SELECT user_id FROM users WHERE username = p_name $$;

-- simulate elapsed time for a booking: shift booked_at and expires_at together
CREATE FUNCTION pg_temp.backdate(p_booking bigint, p_by interval) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
 SET CONSTRAINTS ALL IMMEDIATE;
 ALTER TABLE bookings DISABLE TRIGGER USER;
 UPDATE bookings SET booked_at = booked_at - p_by, expires_at = expires_at - p_by WHERE booking_id = p_booking;
 ALTER TABLE bookings ENABLE TRIGGER USER;
 SET CONSTRAINTS ALL DEFERRED;
END $$;

-- force an exact deadline: expires_at = p_expires, booked_at = p_expires - 10 min
CREATE FUNCTION pg_temp.set_deadline(p_booking bigint, p_expires timestamptz) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
 SET CONSTRAINTS ALL IMMEDIATE;
 ALTER TABLE bookings DISABLE TRIGGER USER;
 UPDATE bookings SET booked_at = p_expires - interval '10 minutes', expires_at = p_expires WHERE booking_id = p_booking;
 ALTER TABLE bookings ENABLE TRIGGER USER;
 SET CONSTRAINTS ALL DEFERRED;
END $$;

-- make a screening "already started" (bypasses D2 trigger; tests only)
CREATE FUNCTION pg_temp.move_show_start(p_show bigint, p_start timestamptz, p_end timestamptz) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
 SET CONSTRAINTS ALL IMMEDIATE;
 ALTER TABLE showtimes DISABLE TRIGGER USER;
 UPDATE showtimes SET starts_at = p_start, ends_at = p_end WHERE showtime_id = p_show;
 ALTER TABLE showtimes ENABLE TRIGGER USER;
 SET CONSTRAINTS ALL DEFERRED;
END $$;

-- ================================================================ SEED / SCHEMA
DO $t$
DECLARE r record;
BEGIN
 PERFORM pg_temp.ok((SELECT count(*) FROM users) = 3, 'SEED 3 accounts');
 PERFORM pg_temp.ok((SELECT count(*) FROM users WHERE role='ADMIN') = 1 AND (SELECT count(*) FROM users WHERE role='CUSTOMER') = 2, 'SEED 1 ADMIN + 2 CUSTOMER');
 PERFORM pg_temp.ok((SELECT count(*) FROM movies) = 5, 'SEED 5 movies');
 PERFORM pg_temp.ok((SELECT count(*) FROM theater_rooms) = 5, 'SEED 5 rooms');
 PERFORM pg_temp.ok((SELECT count(*) FROM seats) = 250, 'SEED 250 seats');
 PERFORM pg_temp.ok((SELECT bool_and(c = 50) AND count(*) = 5 FROM (SELECT count(*) c FROM seats GROUP BY room_id) x), 'SEED 50 seats per room');
 PERFORM pg_temp.ok((SELECT count(*) FROM showtimes) = 280, 'SEED 280 screenings');
 PERFORM pg_temp.ok((SELECT count(DISTINCT (starts_at AT TIME ZONE 'Asia/Seoul')::date) FROM showtimes) = 14, 'SEED 14 consecutive days');
 PERFORM pg_temp.ok((SELECT bool_and(c = 20) FROM (SELECT count(*) c FROM showtimes GROUP BY (starts_at AT TIME ZONE 'Asia/Seoul')::date) x), 'SEED 20 screenings per day');
 PERFORM pg_temp.ok((SELECT count(*) FROM showtimes s JOIN movies m USING (movie_id)
                      WHERE s.ends_at <> s.starts_at + m.duration_minutes * interval '1 minute') = 0, 'SEED every ends_at = starts_at + movie duration (DB-02)');
 PERFORM pg_temp.ok((SELECT count(*) FROM movies WHERE genre IS NULL OR rating IS NULL OR release_date IS NULL OR synopsis IS NULL) = 0, 'SEED movies carry all six D5 attributes');
 PERFORM pg_temp.ok((SELECT count(*) FROM bookings) = 0 AND (SELECT count(*) FROM booking_seats) = 0, 'SEED starts without bookings');
 PERFORM pg_temp.ok((SELECT count(*) FROM pg_extension WHERE extname = 'pg_cron') = 0, 'NO pg_cron / scheduler extension installed');
 FOR r IN SELECT unnest(ARRAY['trg_showtimes_default_end_time','trg_showtimes_protect_booked','trg_bookings_validate','trg_bookings_release_seats',
                              'trg_booking_seats_validate','trg_booking_seats_protect_delete','trg_bookings_z_consistency','trg_booking_seats_consistency']) AS n LOOP
   PERFORM pg_temp.ok((SELECT count(*) FROM pg_trigger WHERE tgname = r.n AND NOT tgisinternal) = 1, 'TRIGGER exists: ' || r.n);
 END LOOP;
 PERFORM pg_temp.ok((SELECT count(*) FROM pg_proc WHERE proname IN ('expire_overdue_bookings','create_booking','pay_booking','cancel_booking')) = 4, 'FUNCTIONS exist: expire/create/pay/cancel');
END $t$;

-- ================================================================ D5 attributes, D4 role
DO $t$
DECLARE m bigint; u bigint; s1 bigint := pg_temp.mk_show(1);
BEGIN
 INSERT INTO movies(title, genre, duration_minutes, rating, synopsis, release_date)
 VALUES ('Probe Movie', 'Any genre text', 99, 'Any rating text', 'Probe synopsis', DATE '2026-12-25') RETURNING movie_id INTO m;
 PERFORM pg_temp.ok((SELECT title='Probe Movie' AND genre='Any genre text' AND duration_minutes=99 AND rating='Any rating text'
                             AND synopsis='Probe synopsis' AND release_date=DATE '2026-12-25' FROM movies WHERE movie_id=m), 'D5 all six movie attributes can be stored and read back');
 PERFORM pg_temp.ok((SELECT data_type FROM information_schema.columns WHERE table_name='movies' AND column_name='release_date') = 'date', 'D5 release_date is a DATE');
 PERFORM pg_temp.ok((SELECT count(*) FROM information_schema.columns WHERE table_name='movies' AND column_name IN ('title','genre','duration_minutes','rating','synopsis','release_date')) = 6, 'D5 six movie columns present');
 PERFORM pg_temp.ok((SELECT count(*) FROM pg_constraint WHERE conrelid='movies'::regclass AND contype='c'
                     AND (pg_get_constraintdef(oid) ILIKE '%genre%' OR pg_get_constraintdef(oid) ILIKE '%rating%')) = 0, 'D5 no invented genre/rating restriction');
 INSERT INTO users(username, password_hash) VALUES ('probe_new_user', 'hash') RETURNING user_id INTO u;
 PERFORM pg_temp.ok((SELECT role FROM users WHERE user_id=u) = 'CUSTOMER', 'D5 role defaults to CUSTOMER (account ID + password only)');
 PERFORM pg_temp.expect_err($$INSERT INTO users(username,password_hash) VALUES ('probe_new_user','h2')$$, '23505', 'D5 account ID is unique');
 PERFORM pg_temp.expect_err($$INSERT INTO users(username,password_hash,role) VALUES ('probe_guest','h','GUEST')$$, '23514', 'D4 GUEST role rejected');
 PERFORM pg_temp.expect_err(format($$SELECT create_booking(%s, %s, ARRAY[%s]::bigint[])$$,
     (SELECT user_id FROM users WHERE role='ADMIN'), s1, pg_temp.seat(s1, 'A', 1)), 'UC008', 'D4/BR-13 ADMIN account cannot own a booking');
END $t$;

-- ================================================================ D1 cancellation
DO $t$
DECLARE c1 bigint := pg_temp.cust(); c2 bigint := pg_temp.cust('customer_demo2');
        s bigint := pg_temp.mk_show(2, 10000); b bigint; b2 bigint; b3 bigint; res text;
BEGIN
 b := create_booking(c1, s, ARRAY[pg_temp.seat(s,'A',1), pg_temp.seat(s,'A',2)]);
 PERFORM pg_temp.ok((SELECT count(*) FROM booking_seats WHERE booking_id=b) = 2, 'D1 setup: booking holds 2 seat rows');
 PERFORM pg_temp.expect_err(format($$SELECT cancel_booking(%s, %s)$$, b, c2), 'UC011', 'BR-09 another customer cannot cancel (not found for them)');
 PERFORM pg_temp.ok((SELECT count(*) FROM booking_seats WHERE booking_id=b) = 2, 'D1 failed cancel leaves seats untouched');
 res := cancel_booking(b, c1);
 PERFORM pg_temp.ok(res = 'CANCELLED', 'D1 cancel_booking returns CANCELLED');
 PERFORM pg_temp.ok((SELECT status = 'CANCELLED' FROM bookings WHERE booking_id=b), 'D1 status becomes CANCELLED');
 PERFORM pg_temp.ok((SELECT count(*) FROM bookings WHERE booking_id=b) = 1, 'D1 parent booking remains');
 PERFORM pg_temp.ok((SELECT count(*) FROM booking_seats WHERE booking_id=b) = 0, 'D1 all booking_seats rows deleted');
 PERFORM pg_temp.ok((SELECT payment_status = 'UNPAID' AND paid_at IS NULL FROM bookings WHERE booking_id=b), 'D1 payment_status preserved (UNPAID) on cancel');
 PERFORM pg_temp.ok((SELECT total_amount = 20000 AND cancelled_at IS NOT NULL FROM bookings WHERE booking_id=b), 'D1/D6 total_amount retained, cancelled_at set');
 PERFORM pg_temp.ok((SELECT count(*) FROM bookings WHERE user_id=c1 AND showtime_id=s AND status='CANCELLED') = 1, 'D1 cancelled history is queryable without seat details');
 PERFORM pg_temp.expect_err(format($$SELECT cancel_booking(%s, %s)$$, b, c1), 'UC006', 'D1 cancelling twice is rejected');
 PERFORM pg_temp.expect_err(format($$UPDATE bookings SET status='BOOKED' WHERE booking_id=%s$$, b), 'UC007', 'D1 cancelled booking cannot be reactivated');
 PERFORM pg_temp.expect_err(format($$SELECT pay_booking(%s, %s)$$, b, c1), 'UC006', 'D1 cancelled booking cannot be paid');
 -- released seats are rebookable; paid booking keeps PAID after cancel
 b2 := create_booking(c1, s, ARRAY[pg_temp.seat(s,'A',1)]);
 PERFORM pg_temp.ok(b2 IS NOT NULL, 'D1 released seat can be booked again');
 PERFORM pg_temp.ok(pay_booking(b2, c1) = 'PAID', 'D1 setup: pay before cancel');
 PERFORM pg_temp.ok(cancel_booking(b2, c1) = 'CANCELLED', 'D1 paid booking can be cancelled before start');
 PERFORM pg_temp.ok((SELECT status='CANCELLED' AND payment_status='PAID' AND paid_at IS NOT NULL FROM bookings WHERE booking_id=b2), 'D1 payment_status stays PAID after cancel (no refund state)');
 PERFORM pg_temp.ok((SELECT count(*) FROM booking_seats WHERE booking_id=b2) = 0, 'D1 paid-then-cancelled seats deleted');
 -- direct UPDATE (the path A used) behaves identically
 b3 := create_booking(c1, s, ARRAY[pg_temp.seat(s,'B',1), pg_temp.seat(s,'B',2)]);
 UPDATE bookings SET status='CANCELLED' WHERE booking_id=b3;
 PERFORM pg_temp.ok((SELECT count(*) FROM booking_seats WHERE booking_id=b3) = 0 AND (SELECT status FROM bookings WHERE booking_id=b3)='CANCELLED', 'D1 direct UPDATE cancel also deletes every seat row atomically');
 PERFORM pg_temp.expect_err(format($$DELETE FROM booking_seats WHERE booking_id=%s$$, create_booking(c1, s, ARRAY[pg_temp.seat(s,'C',1)])), 'UC007', 'D1 seat rows of a BOOKED booking cannot be deleted directly');
END $t$;

-- ================================================================ D1/BR-10 cancel after start (D3: expiry still works)
DO $t$
DECLARE c1 bigint := pg_temp.cust(); s bigint := pg_temp.mk_show(3); b bigint; b_paid bigint; b_unpaid bigint;
BEGIN
 b_paid   := create_booking(c1, s, ARRAY[pg_temp.seat(s,'A',1)]);
 PERFORM pg_temp.ok(pay_booking(b_paid, c1) = 'PAID', 'setup: paid booking');
 b_unpaid := create_booking(c1, s, ARRAY[pg_temp.seat(s,'A',2)]);
 PERFORM pg_temp.move_show_start(s, now() - interval '10 days', now() - interval '10 days' + interval '2 hours');
 PERFORM pg_temp.expect_err(format($$SELECT cancel_booking(%s, %s)$$, b_paid, c1), 'UC005', 'BR-10 cancel after screening start rejected');
 PERFORM pg_temp.ok((SELECT count(*) FROM booking_seats WHERE booking_id=b_paid) = 1 AND (SELECT status FROM bookings WHERE booking_id=b_paid)='BOOKED', 'BR-10 rejected cancel is atomic (seats + status untouched)');
 PERFORM pg_temp.expect_err(format($$SELECT create_booking(%s, %s, ARRAY[%s]::bigint[])$$, c1, s, pg_temp.seat(s,'B',1)), 'UC004', 'BR-12 booking a started screening rejected');
 -- D3: expiry after screening start
 PERFORM pg_temp.backdate(b_unpaid, interval '11 minutes');
 PERFORM pg_temp.ok(expire_overdue_bookings() >= 1, 'D3 expiry runs AFTER the screening has started');
 PERFORM pg_temp.ok((SELECT status='EXPIRED' AND payment_status='UNPAID' FROM bookings WHERE booking_id=b_unpaid), 'D3 expired booking after screening start: EXPIRED + UNPAID');
 PERFORM pg_temp.ok((SELECT count(*) FROM booking_seats WHERE booking_id=b_unpaid) = 0, 'D3 expiry after screening start deleted seat rows');
 PERFORM pg_temp.ok((SELECT status='BOOKED' AND payment_status='PAID' FROM bookings WHERE booking_id=b_paid), 'D3 paid booking on a started screening untouched by expiry');
END $t$;

-- ================================================================ D2 screening protection
DO $t$
DECLARE c1 bigint := pg_temp.cust(); s bigint := pg_temp.mk_show(4, 12000); s2 bigint := pg_temp.mk_show(5, 12000);
        s3 bigint := pg_temp.mk_show(6, 12000); b bigint; b2 bigint; b3 bigint; col text; stmt text; sh bigint; lbl text; i int;
BEGIN
 -- free screening is editable (price, movie, room, times)
 UPDATE showtimes SET ticket_price = 13000 WHERE showtime_id = s;
 PERFORM pg_temp.ok((SELECT ticket_price FROM showtimes WHERE showtime_id=s) = 13000, 'D2 screening without bookings is editable');
 UPDATE showtimes SET ticket_price = 12000 WHERE showtime_id = s;
 -- BOOKED
 b := create_booking(c1, s, ARRAY[pg_temp.seat(s,'A',1)]);
 -- CANCELLED
 b2 := create_booking(c1, s2, ARRAY[pg_temp.seat(s2,'A',1)]); PERFORM cancel_booking(b2, c1);
 -- EXPIRED
 b3 := create_booking(c1, s3, ARRAY[pg_temp.seat(s3,'A',1)]); PERFORM pg_temp.backdate(b3, interval '11 minutes'); PERFORM expire_overdue_bookings();
 PERFORM pg_temp.ok((SELECT status FROM bookings WHERE booking_id=b)='BOOKED' AND (SELECT status FROM bookings WHERE booking_id=b2)='CANCELLED'
                    AND (SELECT status FROM bookings WHERE booking_id=b3)='EXPIRED', 'D2 setup: one BOOKED, one CANCELLED, one EXPIRED booking');
 FOREACH sh IN ARRAY ARRAY[s, s2, s3] LOOP
   lbl := (SELECT status FROM bookings WHERE showtime_id = sh);
   PERFORM pg_temp.expect_err(format($$UPDATE showtimes SET movie_id = (SELECT max(movie_id) FROM movies) WHERE showtime_id=%s$$, sh), 'UC001', 'D2 movie change rejected (' || lbl || ')');
   PERFORM pg_temp.expect_err(format($$UPDATE showtimes SET room_id = (SELECT room_id FROM theater_rooms ORDER BY room_id DESC LIMIT 1) WHERE showtime_id=%s$$, sh), 'UC001', 'D2 room change rejected (' || lbl || ')');
   PERFORM pg_temp.expect_err(format($$UPDATE showtimes SET starts_at = starts_at + interval '1 minute' WHERE showtime_id=%s$$, sh), 'UC001', 'D2 start-time change rejected (' || lbl || ')');
   PERFORM pg_temp.expect_err(format($$UPDATE showtimes SET ends_at = ends_at + interval '1 minute' WHERE showtime_id=%s$$, sh), 'UC001', 'D2 end-time change rejected (' || lbl || ')');
   PERFORM pg_temp.expect_err(format($$UPDATE showtimes SET ticket_price = ticket_price + 1 WHERE showtime_id=%s$$, sh), 'UC001', 'D2 ticket_price change rejected (' || lbl || ')');
   PERFORM pg_temp.expect_err(format($$UPDATE showtimes SET ticket_price = 1, starts_at = starts_at + interval '5 minutes', ends_at = ends_at + interval '5 minutes' WHERE showtime_id=%s$$, sh), 'UC001', 'D2 combined change rejected (' || lbl || ')');
   UPDATE showtimes SET ticket_price = ticket_price WHERE showtime_id = sh;   -- no-op UPDATE is not a modification
 END LOOP;
 PERFORM pg_temp.ok(true, 'D2 no-op UPDATE of a booked screening is not treated as a modification');
 PERFORM pg_temp.expect_err(format($$DELETE FROM showtimes WHERE showtime_id=%s$$, s), '23001', 'D2 a booked screening cannot be deleted (FK RESTRICT)');
END $t$;

-- ================================================================ D3 data model + payment
DO $t$
DECLARE c1 bigint := pg_temp.cust(); s bigint := pg_temp.mk_show(7); b bigint; b2 bigint; b3 bigint; T timestamptz := now(); res text;
BEGIN
 b := create_booking(c1, s, ARRAY[pg_temp.seat(s,'A',1), pg_temp.seat(s,'A',2)]);
 PERFORM pg_temp.ok((SELECT status='BOOKED' AND payment_status='UNPAID' FROM bookings WHERE booking_id=b), 'D3 new booking is BOOKED and UNPAID');
 PERFORM pg_temp.ok((SELECT paid_at IS NULL AND cancelled_at IS NULL FROM bookings WHERE booking_id=b), 'D3 payment is NOT recorded automatically at creation');
 PERFORM pg_temp.ok((SELECT expires_at = booked_at + interval '10 minutes' FROM bookings WHERE booking_id=b), 'D3 expires_at is exactly booked_at + 10 minutes');
 PERFORM pg_temp.ok((SELECT booked_at BETWEEN clock_timestamp() - interval '5 seconds' AND clock_timestamp() FROM bookings WHERE booking_id=b), 'D3 booked_at is the confirmation time');
 PERFORM pg_temp.expect_err(format($$INSERT INTO bookings(user_id,showtime_id,total_amount,status) VALUES (%s,%s,0,'EXPIRED')$$, c1, s), 'UC007', 'D3 a booking cannot be created in a non-BOOKED state');
 PERFORM pg_temp.expect_err(format($$INSERT INTO bookings(user_id,showtime_id,total_amount,payment_status) VALUES (%s,%s,0,'PAID')$$, c1, s), 'UC007', 'D3 a booking cannot be created already PAID');
 PERFORM pg_temp.ok((SELECT count(*) FROM pg_constraint WHERE conrelid='bookings'::regclass AND contype='c'
                      AND pg_get_constraintdef(oid) LIKE '%BOOKED%' AND pg_get_constraintdef(oid) LIKE '%CANCELLED%' AND pg_get_constraintdef(oid) LIKE '%EXPIRED%'
                      AND pg_get_constraintdef(oid) NOT LIKE '%CONFIRMED%') = 1, 'D3 booking status domain is exactly BOOKED / CANCELLED / EXPIRED');
 PERFORM pg_temp.ok((SELECT count(*) FROM pg_constraint WHERE conrelid='bookings'::regclass AND contype='c'
                      AND pg_get_constraintdef(oid) LIKE '%UNPAID%' AND pg_get_constraintdef(oid) LIKE '%''PAID''%') >= 1, 'D3 payment status domain is UNPAID / PAID');
 -- pay before expiry
 res := pay_booking(b, c1);
 PERFORM pg_temp.ok(res = 'PAID', 'D3 payment before expiration succeeds');
 PERFORM pg_temp.ok((SELECT status='BOOKED' AND payment_status='PAID' AND paid_at IS NOT NULL FROM bookings WHERE booking_id=b), 'D3 after payment: BOOKED + PAID + paid_at set');
 PERFORM pg_temp.ok((SELECT count(*) FROM booking_seats WHERE booking_id=b) = 2, 'D3 paid booking keeps its seats');
 PERFORM pg_temp.expect_err(format($$SELECT pay_booking(%s, %s)$$, b, c1), 'UC006', 'D3 paying twice rejected');
 PERFORM pg_temp.expect_err(format($$UPDATE bookings SET payment_status='UNPAID' WHERE booking_id=%s$$, b), 'UC007', 'D3 PAID cannot revert to UNPAID');
 PERFORM pg_temp.expect_err(format($$SELECT pay_booking(%s, %s)$$, b, pg_temp.cust('customer_demo2')), 'UC011', 'BR-09 only the owner can pay');
 -- payment 1.5 seconds before the deadline (real clock) still succeeds
 b2 := create_booking(c1, s, ARRAY[pg_temp.seat(s,'B',1)]);
 PERFORM pg_temp.set_deadline(b2, clock_timestamp() + interval '1500 milliseconds');
 PERFORM pg_temp.ok(pay_booking(b2, c1) = 'PAID', 'D3 payment just before the deadline succeeds');
 -- payment exactly at the deadline: rejected and the booking expires
 b3 := create_booking(c1, s, ARRAY[pg_temp.seat(s,'C',1)]);
 PERFORM pg_temp.set_deadline(b3, T);
 PERFORM pg_temp.ok(pay_booking(b3, c1, T) = 'EXPIRED', 'D3 payment AT expires_at is rejected (booking expires)');
 PERFORM pg_temp.ok((SELECT status='EXPIRED' AND payment_status='UNPAID' FROM bookings WHERE booking_id=b3), 'D3 rejected late payment leaves EXPIRED + UNPAID');
 PERFORM pg_temp.ok((SELECT count(*) FROM booking_seats WHERE booking_id=b3) = 0, 'D3 rejected late payment released the seats');
 PERFORM pg_temp.expect_err(format($$SELECT pay_booking(%s, %s)$$, b3, c1), 'UC006', 'D3 expired booking cannot be paid');
 PERFORM pg_temp.expect_err(format($$SELECT cancel_booking(%s, %s)$$, b3, c1), 'UC006', 'D3 expired booking cannot be cancelled');
 PERFORM pg_temp.expect_err(format($$UPDATE bookings SET status='BOOKED' WHERE booking_id=%s$$, b3), 'UC007', 'D3 expired booking cannot be reactivated');
 -- payment after the deadline (real clock), bypassing the function (DB backstop)
 b := create_booking(c1, s, ARRAY[pg_temp.seat(s,'D',1)]);
 PERFORM pg_temp.backdate(b, interval '10 minutes 1 second');
 PERFORM pg_temp.expect_err(format($$UPDATE bookings SET payment_status='PAID' WHERE booking_id=%s$$, b), 'UC006', 'D3 DB trigger rejects direct payment at/after expires_at');
 PERFORM pg_temp.ok(pay_booking(b, c1) = 'EXPIRED', 'D3 payment after the deadline via pay_booking: rejected, booking expires');
END $t$;

-- ================================================================ D3 expiration: exact boundary, idempotence
DO $t$
DECLARE c1 bigint := pg_temp.cust(); s bigint := pg_temp.mk_show(8); T timestamptz := now();
        b_live bigint; b_edge bigint; b_paid bigint;
BEGIN
 b_live := create_booking(c1, s, ARRAY[pg_temp.seat(s,'A',1)]);
 b_edge := create_booking(c1, s, ARRAY[pg_temp.seat(s,'A',2), pg_temp.seat(s,'A',3)]);
 b_paid := create_booking(c1, s, ARRAY[pg_temp.seat(s,'A',5)]);
 PERFORM pay_booking(b_paid, c1);
 PERFORM pg_temp.set_deadline(b_edge, T);
 PERFORM pg_temp.backdate(b_paid, interval '11 minutes');           -- PAID, deadline long past
 PERFORM expire_overdue_bookings(T - interval '1 microsecond');
 PERFORM pg_temp.ok((SELECT status FROM bookings WHERE booking_id=b_edge) = 'BOOKED', 'D3 1 microsecond before expires_at: NOT expired');
 PERFORM expire_overdue_bookings(T);
 PERFORM pg_temp.ok((SELECT status='EXPIRED' AND payment_status='UNPAID' FROM bookings WHERE booking_id=b_edge), 'D3 unpaid booking expires at the EXACT deadline (current_time >= expires_at)');
 PERFORM pg_temp.ok((SELECT count(*) FROM booking_seats WHERE booking_id=b_edge) = 0, 'D3 expiration deletes every seat row (2 of 2)');
 PERFORM pg_temp.ok((SELECT count(*) FROM bookings WHERE booking_id=b_edge) = 1 AND (SELECT total_amount FROM bookings WHERE booking_id=b_edge) = 24000, 'D3/D6 parent retained with total_amount after expiration');
 PERFORM pg_temp.ok((SELECT status='BOOKED' AND payment_status='PAID' FROM bookings WHERE booking_id=b_paid) AND (SELECT count(*) FROM booking_seats WHERE booking_id=b_paid) = 1, 'D3 PAID booking past its deadline does not expire and keeps its seat');
 PERFORM pg_temp.expect_err(format($$UPDATE bookings SET status='EXPIRED' WHERE booking_id=%s$$, b_paid), 'UC007', 'D3 PAID booking cannot be expired even directly');
 PERFORM pg_temp.ok((SELECT status='BOOKED' FROM bookings WHERE booking_id=b_live), 'D3 live unpaid booking within its window is not expired');
 PERFORM pg_temp.expect_err(format($$UPDATE bookings SET status='EXPIRED' WHERE booking_id=%s$$, b_live), 'UC006', 'D3 DB trigger rejects expiring before expires_at');
 PERFORM pg_temp.ok(expire_overdue_bookings() = 0, 'D3 repeated expiration call is a no-op (returns 0)');
 PERFORM pg_temp.ok(expire_overdue_bookings() = 0 AND expire_overdue_bookings(T) = 0, 'D3 further repeated calls stay no-ops');
 PERFORM pg_temp.ok((SELECT status FROM bookings WHERE booking_id=b_edge)='EXPIRED' AND (SELECT status FROM bookings WHERE booking_id=b_paid)='BOOKED' AND (SELECT status FROM bookings WHERE booking_id=b_live)='BOOKED', 'D3 repeated calls changed nothing');
 PERFORM pg_temp.ok((SELECT count(*) FROM bookings WHERE booking_id IN (b_live,b_edge,b_paid)) = 3, 'D3 no booking row was ever removed');
 PERFORM pg_temp.ok(create_booking(pg_temp.cust('customer_demo2'), s, ARRAY[pg_temp.seat(s,'A',2), pg_temp.seat(s,'A',3)]) IS NOT NULL, 'D3 seats of an expired booking can be booked again');
END $t$;

-- ================================================================ D3 expiration is on demand only
DO $t$
DECLARE c1 bigint := pg_temp.cust(); c2 bigint := pg_temp.cust('customer_demo2'); s bigint := pg_temp.mk_show(11); b_late bigint; b2 bigint; n int;
BEGIN
 b_late := create_booking(c1, s, ARRAY[pg_temp.seat(s,'A',4)]);
 PERFORM pg_temp.backdate(b_late, interval '11 minutes');
 PERFORM pg_temp.ok((SELECT status FROM bookings WHERE booking_id=b_late) = 'BOOKED', 'D3 nothing expires by itself: an overdue booking stays BOOKED until the operation is called');
 n := expire_overdue_bookings();
 PERFORM pg_temp.ok(n >= 1 AND (SELECT status FROM bookings WHERE booking_id=b_late) = 'EXPIRED', 'D3 expire_overdue_bookings() expires overdue unpaid bookings');
 PERFORM pg_temp.ok((SELECT count(*) FROM booking_seats WHERE booking_id=b_late) = 0, 'D3 overdue booking seat rows deleted');
 b2 := create_booking(c1, s, ARRAY[pg_temp.seat(s,'B',1)]);
 PERFORM pg_temp.backdate(b2, interval '11 minutes');
 PERFORM pg_temp.expect_err(format($$UPDATE bookings SET status='CANCELLED' WHERE booking_id=%s$$, b2), 'UC006', 'D3 DB rejects direct cancel of an overdue unpaid booking');
 PERFORM pg_temp.ok(cancel_booking(b2, c1) = 'EXPIRED', 'D3 cancel_booking on an overdue unpaid booking expires it instead');
 b_late := create_booking(c1, s, ARRAY[pg_temp.seat(s,'B',2)]);
 PERFORM pg_temp.backdate(b_late, interval '11 minutes');
 PERFORM pg_temp.ok(create_booking(c2, s, ARRAY[pg_temp.seat(s,'B',2)]) IS NOT NULL, 'D3 create_booking runs the expiry step first, so an overdue holder does not block the seat (D3 #10)');
 PERFORM pg_temp.ok((SELECT status FROM bookings WHERE booking_id=b_late) = 'EXPIRED', 'D3 that overdue holder is EXPIRED afterwards');
END $t$;

-- ================================================================ D6 price + total
DO $t$
DECLARE c1 bigint := pg_temp.cust(); sa bigint := pg_temp.mk_show(9, 9500); sb bigint := pg_temp.mk_show(10, 14000);
        b1 bigint; b2 bigint; b3 bigint; b4 bigint;
BEGIN
 PERFORM pg_temp.ok((SELECT ticket_price FROM showtimes WHERE showtime_id=sa) = 9500 AND (SELECT ticket_price FROM showtimes WHERE showtime_id=sb) = 14000, 'D6 ticket price is stored per screening');
 b1 := create_booking(c1, sa, ARRAY[pg_temp.seat(sa,'A',1), pg_temp.seat(sa,'A',2), pg_temp.seat(sa,'A',3)]);
 b2 := create_booking(c1, sb, ARRAY[pg_temp.seat(sb,'A',1), pg_temp.seat(sb,'A',2)]);
 PERFORM pg_temp.ok((SELECT count(*) = 3 AND bool_and(price_at_booking = 9500) FROM booking_seats WHERE booking_id=b1), 'D6 every seat row snapshots its screening price (9500)');
 PERFORM pg_temp.ok((SELECT count(*) = 2 AND bool_and(price_at_booking = 14000) FROM booking_seats WHERE booking_id=b2), 'D6 a different screening snapshots its own price (14000)');
 PERFORM pg_temp.ok((SELECT total_amount FROM bookings WHERE booking_id=b1) = 28500, 'D6 total = price x seats (3 x 9500 = 28500)');
 PERFORM pg_temp.ok((SELECT total_amount FROM bookings WHERE booking_id=b2) = 28000, 'D6 total = price x seats (2 x 14000 = 28000)');
 PERFORM pg_temp.ok((SELECT b.total_amount = sum(bs.price_at_booking) FROM bookings b JOIN booking_seats bs USING (booking_id) WHERE b.booking_id=b1 GROUP BY b.total_amount), 'D6 total equals the sum of seat snapshots');
 -- DB-level guards for direct inserts (the Flask-bypass paths)
 PERFORM pg_temp.expect_err(format($$INSERT INTO booking_seats(booking_id,seat_id,price_at_booking) VALUES (%s,%s,1)$$, b1, pg_temp.seat(sa,'B',1)), 'UC009', 'D6 snapshot different from the screening price rejected');
 PERFORM pg_temp.expect_err(format($q$DO $x$ DECLARE b bigint; BEGIN
     INSERT INTO bookings(user_id,showtime_id,total_amount) VALUES (%s,%s,1) RETURNING booking_id INTO b;
     INSERT INTO booking_seats(booking_id,seat_id,price_at_booking) VALUES (b,%s,9500);
     SET CONSTRAINTS ALL IMMEDIATE; END $x$$q$, c1, sa, pg_temp.seat(sa,'C',1)), 'UC009', 'D6 total_amount different from the sum of snapshots rejected at commit');
 PERFORM pg_temp.expect_err(format($q$DO $x$ DECLARE b bigint; BEGIN
     INSERT INTO bookings(user_id,showtime_id,total_amount) VALUES (%s,%s,9500) RETURNING booking_id INTO b;
     SET CONSTRAINTS ALL IMMEDIATE; END $x$$q$, c1, sa), 'UC010', 'D3/D6 a BOOKED booking without any seat rejected at commit (atomic creation)');
 PERFORM pg_temp.expect_err(format($q$DO $x$ DECLARE b bigint; BEGIN
     INSERT INTO bookings(user_id,showtime_id,total_amount) VALUES (%s,%s,9500) RETURNING booking_id INTO b;
     INSERT INTO booking_seats(booking_id,seat_id,price_at_booking) VALUES (b,%s,9500);
     INSERT INTO booking_seats(booking_id,seat_id,price_at_booking) VALUES (b,%s,9500);
     SET CONSTRAINTS ALL IMMEDIATE; END $x$$q$, c1, sa, pg_temp.seat(sa,'D',1), pg_temp.seat(sa,'D',2)), 'UC009', 'D6 adding a seat without updating total_amount rejected');
 -- NULL snapshot is filled from the screening; a correct direct insert passes
  INSERT INTO bookings(user_id,showtime_id,total_amount) VALUES (c1, sa, 9500) RETURNING booking_id INTO b3;
 INSERT INTO booking_seats(booking_id,seat_id,price_at_booking) VALUES (b3, pg_temp.seat(sa,'E',1), NULL);
 SET CONSTRAINTS ALL IMMEDIATE; SET CONSTRAINTS ALL DEFERRED;
 PERFORM pg_temp.ok((SELECT price_at_booking FROM booking_seats WHERE booking_id=b3) = 9500, 'D6 omitted snapshot defaults to the screening price; direct insert path consistent');
 -- total immutable and retained after cancel / expiry
 PERFORM pg_temp.expect_err(format($$UPDATE bookings SET total_amount = 1 WHERE booking_id=%s$$, b1), 'UC007', 'D6 total_amount is immutable');
 PERFORM cancel_booking(b1, c1);
 PERFORM pg_temp.ok((SELECT total_amount = 28500 AND status='CANCELLED' FROM bookings WHERE booking_id=b1) AND (SELECT count(*) FROM booking_seats WHERE booking_id=b1) = 0, 'D6 total_amount still available after cancellation (seat rows gone)');
 PERFORM pg_temp.backdate(b2, interval '11 minutes');
 PERFORM expire_overdue_bookings();
 PERFORM pg_temp.ok((SELECT total_amount = 28000 AND status='EXPIRED' FROM bookings WHERE booking_id=b2) AND (SELECT count(*) FROM booking_seats WHERE booking_id=b2) = 0, 'D6 total_amount still available after expiration (seat rows gone)');
 b4 := create_booking(c1, sb, ARRAY[pg_temp.seat(sb,'C',1)]);
 PERFORM pg_temp.ok((SELECT total_amount FROM bookings WHERE booking_id=b4) = 14000, 'D6 single-seat total = unit price');
END $t$;

-- ================================================================ DB-02 / DB-03 end time, overlap, duration
DO $t$
DECLARE base timestamptz := date_trunc('hour', now()) + interval '140 days'; r1 bigint; r2 bigint; m1 bigint := (SELECT min(movie_id) FROM movies);
        dur int; sh bigint; sh_end timestamptz; before_end timestamptz; new_show bigint;
BEGIN
 SELECT room_id INTO r1 FROM theater_rooms ORDER BY room_id LIMIT 1;
 SELECT room_id INTO r2 FROM theater_rooms ORDER BY room_id OFFSET 1 LIMIT 1;
 SELECT duration_minutes INTO dur FROM movies WHERE movie_id = m1;
 -- default end time + explicit end time
 INSERT INTO showtimes(movie_id,room_id,starts_at,ticket_price) VALUES (m1, r1, base, 12000) RETURNING showtime_id, ends_at INTO sh, sh_end;
 PERFORM pg_temp.ok(sh_end = base + dur * interval '1 minute', 'DB-02 omitted ends_at defaults to start + movie duration');
 PERFORM pg_temp.expect_err(format($$INSERT INTO showtimes(movie_id,room_id,starts_at,ends_at,ticket_price) VALUES (%s,%s,'%s','%s',1)$$, m1, r2, base, base), '23514', 'DB-02 ends_at must be later than starts_at');
 -- DB-03: duration edits are allowed and never move an existing screening
 before_end := sh_end;
 UPDATE movies SET duration_minutes = dur + 30 WHERE movie_id = m1;
 PERFORM pg_temp.ok((SELECT duration_minutes FROM movies WHERE movie_id=m1) = dur + 30, 'DB-03 movie duration can be edited although the movie has screenings');
 PERFORM pg_temp.ok((SELECT ends_at FROM showtimes WHERE showtime_id=sh) = before_end, 'DB-03 stored ends_at of existing screenings does not change when duration changes');
 PERFORM pg_temp.ok((SELECT count(*) FROM showtimes s JOIN movies m USING (movie_id) WHERE s.movie_id = m1 AND s.ends_at <> s.starts_at + dur * interval '1 minute') = 0, 'DB-03 all existing screenings of the edited movie keep their original end times');
 INSERT INTO showtimes(movie_id,room_id,starts_at,ticket_price) VALUES (m1, r2, base, 12000) RETURNING showtime_id INTO new_show;
 PERFORM pg_temp.ok((SELECT ends_at FROM showtimes WHERE showtime_id=new_show) = base + (dur + 30) * interval '1 minute', 'DB-03 a NEW screening defaults to the NEW duration');
 UPDATE movies SET duration_minutes = dur WHERE movie_id = m1;
 -- DB-03: overlap uses real [start,end) only; no 15-minute buffer
 INSERT INTO showtimes(movie_id,room_id,starts_at,ends_at,ticket_price) VALUES (m1, r1, sh_end, sh_end + interval '2 hours', 12000);
 PERFORM pg_temp.ok(true, 'DB-03 back-to-back screening (start = previous end) is allowed: no cleaning buffer');
 INSERT INTO showtimes(movie_id,room_id,starts_at,ends_at,ticket_price) VALUES (m1, r1, sh_end + interval '2 hours' + interval '1 minute', sh_end + interval '4 hours', 12000);
 PERFORM pg_temp.ok(true, 'DB-03 a 1-minute gap is allowed');
 PERFORM pg_temp.expect_err(format($$INSERT INTO showtimes(movie_id,room_id,starts_at,ends_at,ticket_price) VALUES (%s,%s,'%s','%s',1)$$, m1, r1, base + interval '10 minutes', base + interval '70 minutes'), '23P01', 'BR-04 overlapping screening in the same room rejected');
 PERFORM pg_temp.expect_err(format($$INSERT INTO showtimes(movie_id,room_id,starts_at,ends_at,ticket_price) VALUES (%s,%s,'%s','%s',1)$$, m1, r1, base - interval '30 minutes', base + interval '1 minute'), '23P01', 'BR-04 overlap by 1 minute at the start rejected');
 PERFORM pg_temp.expect_err(format($$INSERT INTO showtimes(movie_id,room_id,starts_at,ends_at,ticket_price) VALUES (%s,%s,'%s','%s',1)$$, m1, r1, base - interval '1 hour', sh_end + interval '1 hour'), '23P01', 'BR-04 screening enclosing another rejected');
 PERFORM pg_temp.ok((SELECT count(*) FROM showtimes WHERE room_id=r2 AND starts_at=base) = 1, 'BR-04 same time in a DIFFERENT room is allowed');
 PERFORM pg_temp.expect_err(format($$UPDATE showtimes SET room_id = %s WHERE showtime_id=%s$$, r1, new_show), '23P01', 'BR-04 moving a screening into an occupied room slot rejected');
END $t$;

-- ================================================================ trigger-order robustness (regression)
-- cancel / expire must also work if a session has switched constraints to IMMEDIATE
-- (the consistency check must run AFTER the seat rows are released).
DO $t$
DECLARE c1 bigint := pg_temp.cust(); s bigint := pg_temp.mk_show(19); b bigint; b2 bigint; n int;
BEGIN
 b  := create_booking(c1, s, ARRAY[pg_temp.seat(s,'A',1), pg_temp.seat(s,'A',2)]);
 b2 := create_booking(c1, s, ARRAY[pg_temp.seat(s,'A',3)]);
 PERFORM pg_temp.backdate(b2, interval '11 minutes');
 SET CONSTRAINTS ALL IMMEDIATE;
 PERFORM pg_temp.ok(cancel_booking(b, c1) = 'CANCELLED', 'ORDER cancel works with constraints IMMEDIATE');
 n := expire_overdue_bookings();                       -- separate statement so the check sees its effect
 PERFORM pg_temp.ok(n >= 1 AND (SELECT status FROM bookings WHERE booking_id=b2) = 'EXPIRED', 'ORDER expiry works with constraints IMMEDIATE');
 PERFORM pg_temp.ok((SELECT count(*) FROM booking_seats WHERE booking_id IN (b, b2)) = 0, 'ORDER seat rows deleted in both cases');
 SET CONSTRAINTS ALL DEFERRED;
END $t$;

-- ================================================================ retained rules: seats, duplicates, rollback, constraints
DO $t$
DECLARE c1 bigint := pg_temp.cust(); c2 bigint := pg_temp.cust('customer_demo2');
        s bigint := pg_temp.mk_show(12); s_other bigint := pg_temp.mk_show(13, 12000, 2);
        other_room_seat bigint; b bigint; n_before int; a_seat bigint;
BEGIN
 other_room_seat := pg_temp.seat(s_other, 'A', 1);
 PERFORM pg_temp.expect_err(format($$SELECT create_booking(%s, %s, ARRAY[%s]::bigint[])$$, c1, s, other_room_seat), 'UC003', 'BR-07 seat of another room rejected');
 n_before := (SELECT count(*) FROM bookings);
 PERFORM pg_temp.expect_err(format($$SELECT create_booking(%s, %s, ARRAY[%s,%s]::bigint[])$$, c1, s, pg_temp.seat(s,'A',1), other_room_seat), 'UC003', 'TX create_booking with one invalid seat fails as a whole');
 PERFORM pg_temp.ok((SELECT count(*) FROM bookings) = n_before, 'TX no partial booking row remains after the failure');
 PERFORM pg_temp.ok((SELECT count(*) FROM booking_seats bs JOIN bookings bk USING (booking_id) WHERE bk.showtime_id=s) = 0, 'TX no partial seat row remains after the failure');
 b := create_booking(c1, s, ARRAY[pg_temp.seat(s,'A',1)]);
 PERFORM pg_temp.expect_err(format($$SELECT create_booking(%s, %s, ARRAY[%s]::bigint[])$$, c2, s, pg_temp.seat(s,'A',1)), 'UC002', 'BR-08 same seat, same screening, other customer rejected');
 PERFORM pg_temp.expect_err(format($$SELECT create_booking(%s, %s, ARRAY[%s,%s]::bigint[])$$, c2, s, pg_temp.seat(s,'A',2), pg_temp.seat(s,'A',1)), 'UC002', 'BR-08 one taken seat rejects the whole multi-seat booking');
 PERFORM pg_temp.ok((SELECT count(*) FROM bookings WHERE user_id=c2 AND showtime_id=s) = 0, 'BR-08 rejected multi-seat booking left nothing behind');
 PERFORM pg_temp.ok(create_booking(c2, s, ARRAY[pg_temp.seat(s,'A',2)]) IS NOT NULL, 'BR-08 the untouched seat A2 is still bookable');
 -- the same physical seat is independent per screening (availability is per screening)
 a_seat := pg_temp.seat(s, 'A', 1);
 s_other := pg_temp.mk_show(16);
 PERFORM pg_temp.ok(create_booking(c2, s_other, ARRAY[pg_temp.seat(s_other, 'A', 1)]) IS NOT NULL, 'BR-08 the same seat position on ANOTHER screening is bookable');
 PERFORM pg_temp.ok(a_seat IS NOT NULL, 'seat lookup sanity');
 -- foreign keys / unique / check constraints
 PERFORM pg_temp.expect_err(format($$SELECT create_booking(%s, %s, ARRAY[0]::bigint[])$$, c1, s), '23503', 'FK booking_seats.seat_id must reference an existing seat');
 PERFORM pg_temp.expect_err(format($$INSERT INTO bookings(user_id,showtime_id,total_amount) VALUES (%s, 0, 0)$$, c1), '23503', 'FK bookings.showtime_id must reference an existing screening');
 PERFORM pg_temp.expect_err($$INSERT INTO bookings(user_id,showtime_id,total_amount) VALUES (0, 0, 0)$$, '23503', 'FK bookings.user_id must reference an existing user');
 PERFORM pg_temp.expect_err(format($$SELECT create_booking(%s, 0, ARRAY[%s]::bigint[])$$, c1, a_seat), 'UC011', 'create_booking: unknown screening');
 PERFORM pg_temp.expect_err(format($$SELECT create_booking(%s, %s, ARRAY[]::bigint[])$$, c1, s), 'UC010', 'create_booking: empty seat list rejected');
 PERFORM pg_temp.expect_err(format($$SELECT create_booking(%s, %s, ARRAY[%s,%s]::bigint[])$$, c1, s, a_seat, a_seat), 'UC010', 'create_booking: duplicate seat ids rejected');
 PERFORM pg_temp.expect_err(format($$INSERT INTO movies(title,duration_minutes) VALUES ('x', 0)$$), '23514', 'CHECK duration_minutes >= 1');
 PERFORM pg_temp.expect_err(format($$INSERT INTO seats(room_id,seat_row,seat_number) VALUES ((SELECT min(room_id) FROM theater_rooms),'F',1)$$), '23514', 'CHECK seat_row in A..E');
 PERFORM pg_temp.expect_err(format($$INSERT INTO seats(room_id,seat_row,seat_number) VALUES ((SELECT min(room_id) FROM theater_rooms),'A',1)$$), '23505', 'UNIQUE (room_id, seat_row, seat_number)');
 PERFORM pg_temp.expect_err(format($$INSERT INTO theater_rooms(room_name) VALUES ('Hall 1')$$), '23505', 'UNIQUE room_name');
 PERFORM pg_temp.expect_err(format($$UPDATE showtimes SET ticket_price = -1 WHERE showtime_id = %s$$, pg_temp.mk_show(18)), '23514', 'CHECK ticket_price >= 0');
 PERFORM pg_temp.expect_err(format($$DELETE FROM users WHERE user_id = %s$$, c1), '23001', 'FK users referenced by bookings cannot be deleted (RESTRICT)');
 PERFORM pg_temp.expect_err($q$DO $x$ BEGIN
     SET CONSTRAINTS ALL IMMEDIATE;
     ALTER TABLE bookings DISABLE TRIGGER USER;
     INSERT INTO bookings(user_id,showtime_id,total_amount,booked_at,expires_at)
       SELECT user_id, (SELECT min(showtime_id) FROM showtimes), 0, now(), now() + interval '9 minutes' FROM users WHERE username='customer_demo';
   END $x$$q$, '23514', 'CHECK expires_at = booked_at + 10 minutes (even if the trigger were bypassed)');
END $t$;

-- ================================================================ summary
SELECT count(*) AS checks_passed FROM test_log;
SELECT 'ALL ' || count(*) || ' CHECKS PASSED (transaction will be rolled back)' AS result FROM test_log;
ROLLBACK;
