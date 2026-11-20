-- =============================================================================
-- Reconciliation probes: canonical schema vs. approved rules D1-D6 (+ DB-01..DB-10).
--
-- These are the SAME probe IDs (P01 ... P16) that produced 13 MISMATCH against Member
-- A's original handover (see docs/database/handover_reconciliation_report.md). Against
-- the corrected canonical schema every probe must report MATCH (INFO lines are
-- documented application responsibilities, not defects). The script raises an
-- error - and psql exits non-zero under ON_ERROR_STOP - if any probe MISMATCHes.
--
-- Target : NEW, DISPOSABLE database with database/schema.sql + database/seed.sql.
-- Run    : psql -X -v ON_ERROR_STOP=1 -d <disposable_db> -f database/tests/reconciliation_probes.sql
-- Effect : single transaction, ROLLED BACK. Needs table ownership (time simulation
--          temporarily disables USER triggers inside the rolled-back transaction).
--
-- Running this against the ORIGINAL handover schema is expected to fail (it uses the
-- corrected column and function names); the audit results for that schema are
-- recorded in the reconciliation report.
-- =============================================================================
\set ON_ERROR_STOP on
\pset pager off
SET client_min_messages = notice;

BEGIN;
CREATE TEMP TABLE probe_log(id text, verdict text);

CREATE FUNCTION pg_temp.probe(p_id text, p_ok boolean, p_msg text) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
 INSERT INTO probe_log VALUES (p_id, CASE WHEN p_ok THEN 'MATCH' ELSE 'MISMATCH' END);
 RAISE NOTICE '[%] % %', p_id, CASE WHEN p_ok THEN 'MATCH   ' ELSE 'MISMATCH' END, p_msg;
END $$;
CREATE FUNCTION pg_temp.info(p_id text, p_msg text) RETURNS void LANGUAGE plpgsql AS $$
BEGIN RAISE NOTICE '[%] INFO     %', p_id, p_msg; END $$;

-- runs ONE statement and reports its SQLSTATE ('OK' when it succeeds)
CREATE FUNCTION pg_temp.try(p_sql text) RETURNS text LANGUAGE plpgsql AS $$
BEGIN
 BEGIN EXECUTE p_sql; RETURN 'OK';
 EXCEPTION WHEN OTHERS THEN SET CONSTRAINTS ALL DEFERRED; RETURN SQLSTATE; END;
END $$;

CREATE FUNCTION pg_temp.backdate(p_booking bigint, p_by interval) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
 SET CONSTRAINTS ALL IMMEDIATE;
 ALTER TABLE bookings DISABLE TRIGGER USER;
 UPDATE bookings SET booked_at = booked_at - p_by, expires_at = expires_at - p_by WHERE booking_id = p_booking;
 ALTER TABLE bookings ENABLE TRIGGER USER;
 SET CONSTRAINTS ALL DEFERRED;
END $$;

DO $probe$
DECLARE
 v_cust bigint; v_cust2 bigint; v_admin bigint;
 v_show bigint; v_room bigint; v_room2 bigint; v_movie1 bigint; v_movie2 bigint;
 v_seat1 bigint; v_seat2 bigint; v_other_seat bigint;
 v_bk bigint; v_bk2 bigint; v_bk3 bigint; v_cnt int; v_txt text; v_def text; v_ts timestamptz; v_dur int; v_end timestamptz;
 v_base timestamptz := date_trunc('hour', now()) + interval '60 days';
 col text;
BEGIN
 SELECT user_id INTO v_cust  FROM users WHERE username='customer_demo';
 SELECT user_id INTO v_cust2 FROM users WHERE username='customer_demo2';
 SELECT user_id INTO v_admin FROM users WHERE role='ADMIN' LIMIT 1;
 SELECT movie_id, duration_minutes INTO v_movie1, v_dur FROM movies ORDER BY movie_id LIMIT 1;
 SELECT movie_id INTO v_movie2 FROM movies ORDER BY movie_id OFFSET 1 LIMIT 1;
 SELECT room_id INTO v_room  FROM theater_rooms ORDER BY room_id LIMIT 1;
 SELECT room_id INTO v_room2 FROM theater_rooms ORDER BY room_id OFFSET 1 LIMIT 1;
 INSERT INTO showtimes(movie_id,room_id,starts_at,ticket_price) VALUES (v_movie1, v_room, v_base + interval '5 days', 12000) RETURNING showtime_id INTO v_show;
 SELECT seat_id INTO v_seat1 FROM seats WHERE room_id=v_room AND seat_row='A' AND seat_number=1;
 SELECT seat_id INTO v_seat2 FROM seats WHERE room_id=v_room AND seat_row='A' AND seat_number=2;
 SELECT seat_id INTO v_other_seat FROM seats WHERE room_id<>v_room ORDER BY seat_id LIMIT 1;

 -- ------------------------------------------------------------ P01 required columns (D3/D5/D6, DB-01/02/04)
 FOREACH col IN ARRAY ARRAY['movies.genre','movies.rating','movies.release_date','showtimes.ends_at',
                            'bookings.expires_at','bookings.payment_status','bookings.total_amount'] LOOP
   SELECT count(*) INTO v_cnt FROM information_schema.columns
    WHERE table_schema='public' AND table_name=split_part(col,'.',1) AND column_name=split_part(col,'.',2);
   PERFORM pg_temp.probe('P01', v_cnt = 1, 'column ' || col || CASE WHEN v_cnt=1 THEN ' present' ELSE ' ABSENT' END);
 END LOOP;

 -- ------------------------------------------------------------ P02 status domains (D3)
 SELECT string_agg(pg_get_constraintdef(oid), ' | ') INTO v_def FROM pg_constraint
  WHERE conrelid='bookings'::regclass AND contype='c';
 PERFORM pg_temp.probe('P02', v_def LIKE '%BOOKED%' AND v_def LIKE '%CANCELLED%' AND v_def LIKE '%EXPIRED%' AND v_def LIKE '%UNPAID%' AND v_def LIKE '%''PAID''%' AND v_def NOT LIKE '%CONFIRMED%',
                       'booking status = BOOKED/CANCELLED/EXPIRED, payment status = UNPAID/PAID');
 SELECT count(*) INTO v_cnt FROM pg_proc WHERE proname IN ('expire_overdue_bookings','create_booking','pay_booking','cancel_booking');
 PERFORM pg_temp.probe('P02b', v_cnt = 4, 'expiry/create/pay/cancel operations exist (' || v_cnt || ' of 4)');
 PERFORM pg_temp.probe('P02c', (SELECT count(*) FROM pg_extension WHERE extname='pg_cron') = 0, 'no scheduler extension (pg_cron) - expiry is request-time only');

 -- ------------------------------------------------------------ P03 booking starts BOOKED + UNPAID, no automatic payment (D3)
 v_bk := create_booking(v_cust, v_show, ARRAY[v_seat1]);
 PERFORM pg_temp.probe('P03', (SELECT status='BOOKED' AND payment_status='UNPAID' AND paid_at IS NULL AND expires_at = booked_at + interval '10 minutes' FROM bookings WHERE booking_id=v_bk),
                       'new booking is BOOKED + UNPAID, paid_at NULL, expires_at = booked_at + 10 min');
 v_txt := pay_booking(v_bk, v_cust);                      -- separate statement: the check must see the payment
 PERFORM pg_temp.probe('P03b', v_txt = 'PAID' AND (SELECT payment_status='PAID' AND paid_at IS NOT NULL FROM bookings WHERE booking_id=v_bk),
                       'payment can be recorded later (UNPAID -> PAID before expires_at)');

 -- ------------------------------------------------------------ P04 snapshot + total (D6)
 v_txt := pg_temp.try(format('INSERT INTO booking_seats(booking_id,seat_id,price_at_booking) VALUES (%s,%s,1)', v_bk, v_seat2));
 PERFORM pg_temp.probe('P04', v_txt = 'UC009' AND (SELECT total_amount = 12000 AND total_amount = (SELECT sum(price_at_booking) FROM booking_seats WHERE booking_id=v_bk) FROM bookings WHERE booking_id=v_bk),
                       'snapshot must equal screening price (' || v_txt || '); total_amount = sum of snapshots');

 -- ------------------------------------------------------------ P05 / P06 D2
 v_bk2 := create_booking(v_cust2, v_show, ARRAY[v_seat2]);
 PERFORM pg_temp.probe('P05', pg_temp.try(format('UPDATE showtimes SET ticket_price = ticket_price + 1000 WHERE showtime_id=%s', v_show)) = 'UC001', 'ticket_price UPDATE rejected when a booking exists');
 PERFORM pg_temp.probe('P06a', pg_temp.try(format($$UPDATE showtimes SET starts_at = starts_at + interval '1 minute' WHERE showtime_id=%s$$, v_show)) = 'UC001', 'starts_at UPDATE rejected');
 PERFORM pg_temp.probe('P06b', pg_temp.try(format('UPDATE showtimes SET movie_id=%s WHERE showtime_id=%s', v_movie2, v_show)) = 'UC001', 'movie_id UPDATE rejected');
 PERFORM pg_temp.probe('P06d', pg_temp.try(format($$UPDATE showtimes SET ends_at = ends_at + interval '1 minute' WHERE showtime_id=%s$$, v_show)) = 'UC001', 'ends_at UPDATE rejected');
 PERFORM pg_temp.probe('P06e', pg_temp.try(format('UPDATE showtimes SET room_id=%s WHERE showtime_id=%s', v_room2, v_show)) = 'UC001', 'room_id UPDATE rejected');
 PERFORM cancel_booking(v_bk, v_cust);                    -- paid booking becomes CANCELLED
 PERFORM cancel_booking(v_bk2, v_cust2);
 PERFORM pg_temp.probe('P06c', pg_temp.try(format($$UPDATE showtimes SET starts_at = starts_at + interval '1 minute' WHERE showtime_id=%s$$, v_show)) = 'UC001', 'starts_at UPDATE rejected with only CANCELLED bookings');
 v_bk3 := create_booking(v_cust, v_show, ARRAY[v_seat1]);
 PERFORM pg_temp.backdate(v_bk3, interval '11 minutes');
 PERFORM expire_overdue_bookings();
 PERFORM pg_temp.probe('P06f', (SELECT status FROM bookings WHERE booking_id=v_bk3)='EXPIRED' AND pg_temp.try(format('UPDATE showtimes SET ticket_price = ticket_price + 1 WHERE showtime_id=%s', v_show)) = 'UC001', 'ticket_price UPDATE rejected with an EXPIRED booking too');

 -- ------------------------------------------------------------ P07 / P08 D1
 PERFORM pg_temp.probe('P07', (SELECT status='CANCELLED' AND payment_status='PAID' AND total_amount=12000 FROM bookings WHERE booking_id=v_bk)
                              AND (SELECT count(*) FROM booking_seats WHERE booking_id=v_bk) = 0,
                       'cancel: parent kept, status CANCELLED, payment_status PAID preserved, total kept, seat rows 0');
 PERFORM pg_temp.probe('P08', pg_temp.try(format($$UPDATE bookings SET status='BOOKED' WHERE booking_id=%s$$, v_bk)) = 'UC007', 'cancelled booking cannot be reactivated');

 -- ------------------------------------------------------------ P09 / P10 seats
 v_bk := create_booking(v_cust, v_show, ARRAY[v_seat1]);
 PERFORM pg_temp.probe('P09', pg_temp.try(format('SELECT create_booking(%s,%s,ARRAY[%s]::bigint[])', v_cust2, v_show, v_other_seat)) = 'UC003', 'seat of another room rejected');
 PERFORM pg_temp.probe('P10', pg_temp.try(format('SELECT create_booking(%s,%s,ARRAY[%s]::bigint[])', v_cust2, v_show, v_seat1)) = 'UC002', 'duplicate active seat rejected');

 -- ------------------------------------------------------------ P11 overlap / no buffer (DB-03)
 INSERT INTO showtimes(movie_id,room_id,starts_at,ticket_price) VALUES (v_movie1, v_room, v_base, 12000) RETURNING ends_at INTO v_end;
 PERFORM pg_temp.probe('P11a', pg_temp.try(format($$INSERT INTO showtimes(movie_id,room_id,starts_at,ticket_price) VALUES (%s,%s,'%s',1)$$, v_movie1, v_room, v_base + interval '60 minutes')) = '23P01', 'genuinely overlapping screening rejected');
 PERFORM pg_temp.probe('P11b', pg_temp.try(format($$INSERT INTO showtimes(movie_id,room_id,starts_at,ends_at,ticket_price) VALUES (%s,%s,'%s','%s',1)$$, v_movie1, v_room, v_end, v_end + interval '1 hour')) = 'OK', 'back-to-back screening accepted (no 15-minute buffer)');

 -- ------------------------------------------------------------ P12 duration edit (DB-03)
 SELECT ends_at INTO v_ts FROM showtimes WHERE showtime_id=v_show;
 v_txt := pg_temp.try(format('UPDATE movies SET duration_minutes = duration_minutes + 1 WHERE movie_id=%s', v_movie1));
 PERFORM pg_temp.probe('P12', v_txt = 'OK' AND (SELECT ends_at FROM showtimes WHERE showtime_id=v_show) = v_ts, 'movie duration editable; stored screening end time unchanged');

 -- ------------------------------------------------------------ P13 / P14 roles (D4, D5)
 PERFORM pg_temp.probe('P13', pg_temp.try($$INSERT INTO users(username,password_hash,role) VALUES ('probe_guest','x','GUEST')$$) = '23514', 'GUEST role rejected');
 PERFORM pg_temp.info('P14', 'DB accepts role=ADMIN inserts; Flask registration MUST NOT pass a role (default CUSTOMER) - application responsibility');
 SELECT count(*) INTO v_cnt FROM showtimes WHERE starts_at <= clock_timestamp() AND (starts_at AT TIME ZONE 'Asia/Seoul')::date = timezone('Asia/Seoul', now())::date;
 PERFORM pg_temp.info('P15', 'seeded screenings already started today at run time: ' || v_cnt || ' (seed is relative to the execution day)');

 -- ------------------------------------------------------------ P17..P20 D3 behaviours
 v_bk := create_booking(v_cust2, v_show, ARRAY[v_seat2]);
 PERFORM pg_temp.backdate(v_bk, interval '10 minutes 1 second');
 PERFORM pg_temp.probe('P17', pg_temp.try(format($$UPDATE bookings SET payment_status='PAID' WHERE booking_id=%s$$, v_bk)) = 'UC006' AND pay_booking(v_bk, v_cust2) = 'EXPIRED',
                       'payment at/after expires_at rejected; booking expires; seats released');
 PERFORM pg_temp.probe('P18', expire_overdue_bookings() = 0 AND expire_overdue_bookings() = 0, 'repeated expiration calls are no-ops (idempotent)');
 PERFORM pg_temp.probe('P19', (SELECT status='EXPIRED' AND payment_status='UNPAID' FROM bookings WHERE booking_id=v_bk) AND (SELECT count(*) FROM booking_seats WHERE booking_id=v_bk)=0,
                       'expired booking keeps parent + UNPAID, seat rows deleted');
END $probe$;

DO $s$
DECLARE v_match int; v_mis int;
BEGIN
 SELECT count(*) FILTER (WHERE verdict='MATCH'), count(*) FILTER (WHERE verdict='MISMATCH') INTO v_match, v_mis FROM probe_log;
 RAISE NOTICE 'SUMMARY: % MATCH, % MISMATCH', v_match, v_mis;
 IF v_mis > 0 THEN RAISE EXCEPTION 'reconciliation probes: % MISMATCH', v_mis; END IF;
END $s$;
ROLLBACK;

-- ------------------------------------------------------------ P16 booking without seats at COMMIT (atomic creation)
\echo [P16] expecting an ERROR below (BOOKED booking without seats must fail at COMMIT):
\set ON_ERROR_STOP off
BEGIN;
INSERT INTO bookings(user_id,showtime_id,total_amount)
  SELECT (SELECT user_id FROM users WHERE username='customer_demo'),
         (SELECT showtime_id FROM showtimes WHERE starts_at > now()+interval '2 days' ORDER BY starts_at DESC LIMIT 1), 12000;
COMMIT;
\set ON_ERROR_STOP on
SELECT '[P16] ' || CASE WHEN count(*) = 0 THEN 'MATCH    failed commit left 0 booking rows' ELSE 'MISMATCH rows persisted: ' || count(*) END AS result FROM bookings;
