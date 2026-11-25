-- Run on a disposable seeded database, as owner or with PGOPTIONS='-c role=cinema_api'.
\set ON_ERROR_STOP on
BEGIN;

CREATE FUNCTION pg_temp.money_rejected(statement text, allowed text[]) RETURNS void
LANGUAGE plpgsql AS $$
BEGIN
 BEGIN
  EXECUTE statement;
 EXCEPTION WHEN OTHERS THEN
  IF SQLSTATE = ANY(allowed) THEN
   RAISE NOTICE 'MONEY rejected with %', SQLSTATE;
   RETURN;
  END IF;
  RAISE;
 END;
 RAISE EXCEPTION 'Expected money-domain rejection: %', statement;
END $$;

-- Independently exercise each deployed CHECK using its catalog definition on an
-- unconstrained numeric fixture. Real writes are also tested below. This separates
-- a CHECK rejection from a typed column's earlier Infinity coercion or trigger.
DO $$
DECLARE
 target record;
 definition text;
 amount text;
BEGIN
 FOR target IN SELECT * FROM (VALUES
  ('showtimes_ticket_price_finite', 'public.showtimes', 'ticket_price'),
  ('bookings_total_amount_finite', 'public.bookings', 'total_amount'),
  ('booking_seats_price_at_booking_finite', 'public.booking_seats', 'price_at_booking')
 ) AS t(constraint_name, relation_name, column_name)
 LOOP
  SELECT pg_get_constraintdef(c.oid) INTO STRICT definition FROM pg_constraint c
   WHERE c.conname=target.constraint_name AND c.conrelid=target.relation_name::regclass
     AND c.convalidated AND c.contype='c';
  EXECUTE format('CREATE TEMP TABLE finite_probe(%I numeric, %s)',target.column_name,definition);
  FOREACH amount IN ARRAY ARRAY['NaN','Infinity','-Infinity'] LOOP
   PERFORM pg_temp.money_rejected(format('INSERT INTO finite_probe VALUES (%L::numeric)',amount),
                                  ARRAY['23514']);
  END LOOP;
  INSERT INTO finite_probe VALUES (0), (12000.37), (99999999.99);
  DROP TABLE finite_probe;
 END LOOP;
END $$;

DO $$
DECLARE
 show_id bigint;
 zero_show bigint;
 regular_show bigint;
 bad_booking bigint;
 original bigint;
 zero_id bigint;
 test_seats bigint[];
 amount text;
BEGIN
 SELECT ARRAY(SELECT seat_id FROM seats WHERE room_id=1 ORDER BY seat_id) INTO test_seats;
 IF cardinality(test_seats)<>50 THEN RAISE EXCEPTION 'Expected the seeded 50-seat room'; END IF;

 INSERT INTO showtimes(movie_id,room_id,starts_at,ticket_price)
 VALUES(1,1,now()+interval '400 days',99999999.99) RETURNING showtime_id INTO show_id;
 INSERT INTO showtimes(movie_id,room_id,starts_at,ticket_price)
 VALUES(1,1,now()+interval '401 days',0) RETURNING showtime_id INTO zero_show;
 INSERT INTO showtimes(movie_id,room_id,starts_at,ticket_price)
 VALUES(1,1,now()+interval '402 days',12000.37) RETURNING showtime_id INTO regular_show;
 zero_id := create_booking(2,zero_show,ARRAY[test_seats[1]]);

 FOREACH amount IN ARRAY ARRAY['NaN','Infinity','-Infinity','-0.01'] LOOP
  PERFORM pg_temp.money_rejected(format('UPDATE showtimes SET ticket_price=%L::numeric WHERE showtime_id=%s',
                                 amount,regular_show), ARRAY['23514','22003']);
  PERFORM pg_temp.money_rejected(format('INSERT INTO bookings(user_id,showtime_id,total_amount) VALUES (2,%s,%L::numeric)',
                                 regular_show,amount), ARRAY['23514','22003']);
  PERFORM pg_temp.money_rejected(format('INSERT INTO booking_seats(booking_id,seat_id,price_at_booking) VALUES (%s,%s,%L::numeric)',
                                 zero_id,test_seats[2],amount), ARRAY['UC009','23514','22003']);
 END LOOP;

 original := create_booking(2,show_id,test_seats);
 IF (SELECT total_amount FROM bookings WHERE booking_id=original) <> 4999999999.50
 OR (SELECT count(*) FROM booking_seats WHERE booking_id=original
     AND price_at_booking=99999999.99) <> 50
 OR (SELECT total_amount FROM bookings WHERE booking_id=zero_id) <> 0 THEN
  RAISE EXCEPTION 'Money positive controls failed';
 END IF;

 BEGIN
  INSERT INTO bookings(user_id,showtime_id,total_amount) VALUES(2,regular_show,1)
   RETURNING booking_id INTO bad_booking;
  INSERT INTO booking_seats(booking_id,seat_id,price_at_booking) VALUES(bad_booking,test_seats[1],12000.37);
  SET CONSTRAINTS ALL IMMEDIATE;
  RAISE EXCEPTION 'Deferred total mismatch was not rejected';
 EXCEPTION WHEN SQLSTATE 'UC009' THEN
  IF EXISTS (SELECT 1 FROM bookings WHERE booking_id=bad_booking)
     OR EXISTS (SELECT 1 FROM booking_seats WHERE booking_id=bad_booking) THEN
   RAISE EXCEPTION 'Failed nested transaction left rows';
  END IF;
 END;

 IF pay_booking(original,2) <> 'PAID' THEN RAISE EXCEPTION 'Payment failed'; END IF;
 IF cancel_booking(original,2) <> 'CANCELLED' THEN RAISE EXCEPTION 'Cancellation failed'; END IF;
 IF NOT EXISTS (SELECT 1 FROM bookings WHERE booking_id=original AND status='CANCELLED'
                AND payment_status='PAID' AND total_amount=4999999999.50)
    OR EXISTS (SELECT 1 FROM booking_seats WHERE booking_id=original) THEN
  RAISE EXCEPTION 'Cancellation did not preserve history or release seats';
 END IF;
 PERFORM create_booking(3,show_id,ARRAY[test_seats[1]]);
END $$;

SET CONSTRAINTS ALL IMMEDIATE;
\echo 'MONEY DOMAIN CHECKS PASSED'
ROLLBACK;
