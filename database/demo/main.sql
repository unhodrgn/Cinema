\ir guard.sql
BEGIN;
SELECT current_database(), current_user;
SELECT (SELECT count(*) FROM movies) AS movies, (SELECT count(*) FROM seats) AS seats,
       (SELECT count(*) FROM showtimes) AS showtimes;
INSERT INTO showtimes(movie_id,room_id,starts_at,ticket_price)
VALUES(1,1,clock_timestamp()+interval '370 days',12000)
RETURNING showtime_id \gset
SELECT create_booking(2,:showtime_id,ARRAY[1,2]::bigint[]) AS original \gset
SELECT booking_id,status,payment_status,total_amount FROM bookings WHERE booking_id=:original;
SELECT pay_booking(:original,2);
SELECT cancel_booking(:original,2);
SELECT b.status,b.payment_status,b.total_amount,count(a.seat_id) AS active_seats
FROM bookings b LEFT JOIN booking_seats a USING(booking_id)
WHERE b.booking_id=:original GROUP BY b.booking_id;
SELECT create_booking(3,:showtime_id,ARRAY[1]::bigint[]) AS rebooked \gset
SELECT * FROM booking_seats WHERE booking_id=:rebooked;
SET CONSTRAINTS ALL IMMEDIATE;
ROLLBACK;
