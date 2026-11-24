\ir 00_context.sql
BEGIN;
DO $demo$
DECLARE
  c demo_cases%ROWTYPE;
  customer bigint := (SELECT user_id FROM demo_customers WHERE customer_no=1);
  other_seat bigint;
BEGIN
  SELECT * INTO STRICT c FROM demo_cases WHERE case_no=2;
  SELECT seat_id INTO STRICT other_seat FROM seats WHERE room_id<>c.room_id ORDER BY seat_id LIMIT 1;
  BEGIN
    PERFORM create_booking(customer, c.showtime_id, ARRAY[other_seat]);
    RAISE EXCEPTION 'Wrong-room seat accepted';
  EXCEPTION WHEN SQLSTATE 'UC003' THEN
    RAISE NOTICE 'PASS 다른 상영관 좌석 거부: SQLSTATE %', SQLSTATE;
  END;
  BEGIN
    INSERT INTO showtimes(movie_id,room_id,starts_at,ends_at,ticket_price)
    VALUES(c.movie_id,c.room_id,c.starts_at,c.ends_at,c.ticket_price);
    RAISE EXCEPTION 'Overlapping screening accepted';
  EXCEPTION WHEN exclusion_violation THEN
    RAISE NOTICE 'PASS 같은 상영관의 중첩 일정 거부: SQLSTATE %', SQLSTATE;
  END;
  IF EXISTS (SELECT FROM bookings WHERE showtime_id=c.showtime_id) THEN
    RAISE EXCEPTION 'Invalid seat request left a parent booking';
  END IF;
  RAISE NOTICE 'PASS 잘못된 좌석 요청 후 부분 예매 0건';
END
$demo$;
ROLLBACK;
