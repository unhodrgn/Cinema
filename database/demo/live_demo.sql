\set ON_ERROR_STOP on
\pset pager off
SET TIME ZONE 'Asia/Seoul';
\echo '=== 1. 데이터 현황 / Database counts ==='
SELECT 'users' AS entity,count(*) FROM users UNION ALL SELECT 'movies',count(*) FROM movies UNION ALL SELECT 'rooms',count(*) FROM theater_rooms UNION ALL SELECT 'seats',count(*) FROM seats UNION ALL SELECT 'showtimes',count(*) FROM showtimes;
CREATE TEMP TABLE demo_context AS
SELECT s.showtime_id, s.room_id,
 (SELECT user_id FROM users WHERE role='CUSTOMER' ORDER BY user_id LIMIT 1) AS customer_a,
 (SELECT user_id FROM users WHERE role='CUSTOMER' ORDER BY user_id OFFSET 1 LIMIT 1) AS customer_b,
 (SELECT user_id FROM users WHERE role='ADMIN' ORDER BY user_id LIMIT 1) AS admin_id,
 (SELECT seat_id FROM seats WHERE room_id=s.room_id ORDER BY seat_id LIMIT 1) AS seat_a,
 (SELECT seat_id FROM seats WHERE room_id=s.room_id ORDER BY seat_id OFFSET 1 LIMIT 1) AS seat_b,
 (SELECT seat_id FROM seats WHERE room_id<>s.room_id ORDER BY seat_id LIMIT 1) AS wrong_seat
FROM showtimes s WHERE starts_at > clock_timestamp()+interval '30 minutes' ORDER BY starts_at,showtime_id LIMIT 1;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM demo_context WHERE customer_a IS NOT NULL AND customer_b IS NOT NULL AND admin_id IS NOT NULL AND seat_a IS NOT NULL AND seat_b IS NOT NULL AND wrong_seat IS NOT NULL) THEN RAISE EXCEPTION 'Demo prerequisites missing'; END IF; END $$;
SELECT * FROM demo_context \gset
\echo '=== 2. 예매 전 좌석 조회 / Availability before booking ==='
SELECT * FROM screening_seat_availability(:showtime_id) WHERE seat_id IN (:seat_a,:seat_b);
\echo '=== 3. 두 좌석 예매 / Reserve two seats ==='
SELECT create_booking(:customer_a,:showtime_id,ARRAY[:seat_a,:seat_b]::bigint[]) AS booking_id \gset
SELECT booking_id,status,payment_status,total_amount,expires_at-booked_at AS payment_window FROM bookings WHERE booking_id=:booking_id;
SELECT * FROM screening_seat_availability(:showtime_id) WHERE seat_id IN (:seat_a,:seat_b);
\echo '=== 4. 예외 검증 / Expected errors ==='
DO $$ DECLARE c record; BEGIN SELECT * INTO c FROM demo_context;
 BEGIN PERFORM create_booking(c.customer_b,c.showtime_id,ARRAY[c.seat_a]); RAISE EXCEPTION 'FAIL: duplicate accepted'; EXCEPTION WHEN SQLSTATE 'UC002' THEN RAISE NOTICE 'PASS UC002: duplicate seat rejected'; END;
 BEGIN PERFORM create_booking(c.customer_b,c.showtime_id,ARRAY[c.wrong_seat]); RAISE EXCEPTION 'FAIL: wrong room accepted'; EXCEPTION WHEN SQLSTATE 'UC003' THEN RAISE NOTICE 'PASS UC003: wrong room rejected'; END;
 BEGIN PERFORM create_booking(c.admin_id,c.showtime_id,ARRAY[c.seat_a]); RAISE EXCEPTION 'FAIL: admin booking accepted'; EXCEPTION WHEN SQLSTATE 'UC008' THEN RAISE NOTICE 'PASS UC008: admin booking rejected'; END;
END $$;
\echo '=== 5. 모의 결제 / Simulated payment ==='
SELECT pay_booking(:booking_id,:customer_a) AS payment_result;
SELECT booking_id,status,payment_status,paid_at FROM bookings WHERE booking_id=:booking_id;
\echo '=== 6. 취소 및 좌석 반환 / Cancellation and release ==='
SELECT cancel_booking(:booking_id,:customer_a) AS cancellation_result;
SELECT booking_id,status,payment_status,total_amount FROM bookings WHERE booking_id=:booking_id;
SELECT count(*) AS remaining_allocations FROM booking_seats WHERE booking_id=:booking_id;
SELECT * FROM screening_seat_availability(:showtime_id) WHERE seat_id IN (:seat_a,:seat_b);
\echo '=== 7. 재예매 / Rebooking ==='
SELECT create_booking(:customer_b,:showtime_id,ARRAY[:seat_a]::bigint[]) AS rebooking_id \gset
SELECT booking_id,status,payment_status FROM bookings WHERE booking_id=:rebooking_id;
SELECT cancel_booking(:rebooking_id,:customer_b) AS cleanup_result;
\echo '=== LIVE DEMO COMPLETED ==='
