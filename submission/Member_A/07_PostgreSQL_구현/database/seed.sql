-- =============================================================================
-- Cinema Reservation System - canonical seed data (PostgreSQL 14+)
-- Run AFTER database/schema.sql, ONCE, in the same NEW database.
--   psql -X -v ON_ERROR_STOP=1 -d <db> -f database/seed.sql
--
-- ALL VALUES BELOW ARE DEMO DATA, not business rules:
--   * movie genre / rating / release_date / synopsis values are placeholders;
--     BR-DL-001 sec. 6 approves no genre or rating vocabulary.
--   * ticket_price 12000.00 is a demo price (D6 #6: no numeric price approved).
--   * the 3 accounts keep Member A's demo password HASHES. The plaintext
--     passwords were never documented by A and have not been verified, so none
--     are documented anywhere. Replace the hashes (Werkzeug
--     generate_password_hash) before demoing a login.
--
-- Screening window: 7 consecutive Asia/Seoul calendar days starting on the day
-- the seed is executed. Slots that have already started today cannot be booked.
-- =============================================================================
BEGIN;

INSERT INTO users(username, password_hash, role) VALUES
 ('admin_demo',     'pbkdf2:sha256:600000$a54ec6ae2aeb6373$1f412da1184bfec47331b445d020c6d3a0cf95cdd50443bf7be7c3067aa69d10', 'ADMIN'),
 ('customer_demo',  'pbkdf2:sha256:600000$e5714680b2a12625$e0615cb2938c2dceae1fa1f7422c3c45db16eca464978e2c755fe32d8d10fe12', 'CUSTOMER'),
 ('customer_demo2', 'pbkdf2:sha256:600000$79a1d0adbb18490b$68288afaddc1fa4208923dd8c0d99edf65a4d794724b28a0a7215a664908d551', 'CUSTOMER');

INSERT INTO movies(title, genre, duration_minutes, rating, synopsis, release_date) VALUES
 ('Phim 1', 'Action',    120, 'ALL', 'Demo movie 1', DATE '2026-09-01'),
 ('Phim 2', 'Drama',     135, '12',  'Demo movie 2', DATE '2026-09-15'),
 ('Phim 3', 'Comedy',    140, '15',  'Demo movie 3', DATE '2026-10-01'),
 ('Phim 4', 'Thriller',  125, '15',  'Demo movie 4', DATE '2026-10-15'),
 ('Phim 5', 'Animation', 145, 'ALL', 'Demo movie 5', DATE '2026-11-01');

INSERT INTO theater_rooms(room_name)
SELECT 'Phòng ' || n FROM generate_series(1, 5) AS n;

INSERT INTO seats(room_id, seat_row, seat_number)
SELECT r.room_id, chr(65 + row_idx)::char(1), seat_num
FROM theater_rooms r
CROSS JOIN generate_series(0, 4) AS row_idx
CROSS JOIN generate_series(1, 10) AS seat_num;

-- Schedule rotation: for room 1..5 and slot 0..3,
--   movie index = ((room_number - 1 + slot) % 5) + 1.
-- Each movie appears 4 times/day; each room has 4 screenings/day (20/day, 140 total).
-- ends_at = starts_at + movie duration (stored; later duration edits never move it).
-- Longest movie is 145 min, so the 3-hour slot spacing never overlaps.
WITH demo_days AS (
 SELECT (timezone('Asia/Seoul', now())::date + day_offset) AS local_day
 FROM generate_series(0, 6) AS day_offset
), slots AS (
 SELECT slot_idx, (ARRAY['10:00','13:00','16:00','19:00'])[slot_idx + 1]::time AS local_time
 FROM generate_series(0, 3) AS slot_idx
), planned AS (
 SELECT m.movie_id, r.room_id, m.duration_minutes,
        (d.local_day + s.local_time) AT TIME ZONE 'Asia/Seoul' AS starts_at,
        d.local_day, s.slot_idx
 FROM demo_days d
 CROSS JOIN theater_rooms r
 CROSS JOIN slots s
 JOIN movies m ON m.title = 'Phim ' || (((substring(r.room_name from '[0-9]+')::int - 1 + s.slot_idx) % 5) + 1)
)
INSERT INTO showtimes(movie_id, room_id, starts_at, ends_at, ticket_price)
SELECT movie_id, room_id, starts_at, starts_at + duration_minutes * interval '1 minute', 12000.00
FROM planned
ORDER BY local_day, room_id, slot_idx;

COMMIT;

-- Verify after seeding:
SELECT 'users' AS entity, count(*) AS actual, 3 AS expected FROM users
UNION ALL SELECT 'movies', count(*), 5 FROM movies
UNION ALL SELECT 'theater_rooms', count(*), 5 FROM theater_rooms
UNION ALL SELECT 'seats', count(*), 250 FROM seats
UNION ALL SELECT 'showtimes', count(*), 140 FROM showtimes;

-- 20 screenings per day:
SELECT (starts_at AT TIME ZONE 'Asia/Seoul')::date AS day, count(*) AS screenings
FROM showtimes GROUP BY 1 ORDER BY 1;
