\ir guard.sql
BEGIN ISOLATION LEVEL READ COMMITTED;
SET LOCAL lock_timeout='30s';
SELECT set_config('cinema.demo_showtime', :'demo_showtime', true);
DO $$
BEGIN
 BEGIN
  PERFORM create_booking(3,current_setting('cinema.demo_showtime')::bigint,ARRAY[1]::bigint[]);
  RAISE EXCEPTION 'Expected UC002';
 EXCEPTION WHEN SQLSTATE 'UC002' THEN
  RAISE NOTICE '예상된 동시 예매 거부: %', SQLSTATE;
 END;
END $$;
SELECT count(*) AS active_allocations FROM booking_seats WHERE showtime_id=:demo_showtime AND seat_id=1;
ROLLBACK;
