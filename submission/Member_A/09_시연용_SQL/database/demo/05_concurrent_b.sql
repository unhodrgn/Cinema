\ir 00_context.sql
BEGIN ISOLATION LEVEL READ COMMITTED;
DO $demo$
DECLARE
  screening bigint := (SELECT showtime_id FROM demo_cases WHERE case_no=4);
  customer bigint := (SELECT user_id FROM demo_customers WHERE customer_no=2);
  seat bigint := (SELECT min(seat_id) FROM seats WHERE room_id=(SELECT room_id FROM demo_cases WHERE case_no=4));
BEGIN
  BEGIN
    PERFORM create_booking(customer,screening,ARRAY[seat]);
    RAISE EXCEPTION 'The second session acquired the same seat';
  EXCEPTION WHEN SQLSTATE 'UC002' THEN
    RAISE NOTICE 'PASS 세션 B: SQLSTATE %', SQLSTATE;
  END;
END
$demo$;
ROLLBACK;
