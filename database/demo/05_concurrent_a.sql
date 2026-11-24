\ir 00_context.sql
BEGIN ISOLATION LEVEL READ COMMITTED;
SELECT create_booking(u.user_id, c.showtime_id,
       ARRAY[(SELECT min(seat_id) FROM seats WHERE room_id=c.room_id)]) AS winner_booking_id
FROM demo_cases c CROSS JOIN demo_customers u WHERE c.case_no=4 AND u.customer_no=1;
\echo '세션 A: 잠금 유지 중. 세션 B가 대기한 뒤 이 세션에서 COMMIT;을 실행한다.'
