\ir 00_guard.sql
SELECT version(), current_setting('server_encoding') AS encoding, current_setting('TimeZone') AS timezone;
SELECT table_name FROM information_schema.tables
WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY table_name;
SELECT 'users' AS table_name, count(*) AS rows FROM users
UNION ALL SELECT 'movies',count(*) FROM movies
UNION ALL SELECT 'theater_rooms',count(*) FROM theater_rooms
UNION ALL SELECT 'seats',count(*) FROM seats
UNION ALL SELECT 'showtimes',count(*) FROM showtimes
UNION ALL SELECT 'bookings',count(*) FROM bookings
UNION ALL SELECT 'booking_seats',count(*) FROM booking_seats;
SELECT conname, pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE conname IN ('booking_seats_booking_showtime_fk','booking_seats_showtime_seat_key','showtimes_no_room_overlap')
ORDER BY conname;
