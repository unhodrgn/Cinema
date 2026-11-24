\ir 00_context.sql
SELECT (SELECT count(*) FROM bookings WHERE showtime_id=c.showtime_id) AS parent_bookings,
       (SELECT count(*) FROM booking_seats WHERE showtime_id=c.showtime_id) AS seat_allocations
FROM demo_cases c WHERE c.case_no=4;
DO $demo$
DECLARE s bigint := (SELECT showtime_id FROM demo_cases WHERE case_no=4);
BEGIN
  IF (SELECT count(*) FROM bookings WHERE showtime_id=s) <> 1
     OR (SELECT count(*) FROM booking_seats WHERE showtime_id=s) <> 1 THEN
    RAISE EXCEPTION 'Expected exactly one booking and one allocation after both sessions';
  END IF;
  RAISE NOTICE 'PASS 동시 예매 후 예매 1건, 좌석 배정 1건';
END
$demo$;
