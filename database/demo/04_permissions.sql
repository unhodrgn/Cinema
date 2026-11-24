\ir 00_context.sql
SELECT c.showtime_id, u.user_id, (SELECT min(seat_id) FROM seats WHERE room_id=c.room_id) AS seat_id
FROM demo_cases c CROSS JOIN demo_customers u WHERE c.case_no=3 AND u.customer_no=1 \gset
BEGIN;
SET LOCAL ROLE cinema_demo_app;
SELECT current_user AS application_role,
       has_function_privilege('public.create_booking(bigint,bigint,bigint[])', 'EXECUTE') AS can_book,
       has_table_privilege('public.bookings', 'DELETE') AS can_delete_history,
       has_table_privilege('public.bookings', 'TRUNCATE') AS can_truncate_history;
SELECT public.create_booking(:user_id,:showtime_id,ARRAY[:seat_id]::bigint[]) AS booking_id \gset
SELECT public.cancel_booking(:booking_id,:user_id) AS permitted_cancel;
DO $demo$
BEGIN
  BEGIN
    DELETE FROM public.bookings WHERE false;
    RAISE EXCEPTION 'Application role has direct DELETE';
  EXCEPTION WHEN insufficient_privilege THEN
    RAISE NOTICE 'PASS 앱 역할의 직접 DELETE 거부: SQLSTATE %', SQLSTATE;
  END;
END
$demo$;
ROLLBACK;
