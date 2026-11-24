-- =============================================================================
-- Cinema Reservation System - canonical seed data (PostgreSQL 14+)
-- Run AFTER database/schema.sql, ONCE, in the same NEW database.
--   psql -X -v ON_ERROR_STOP=1 -d <db> -f database/seed.sql
--
-- ALL VALUES BELOW ARE DEMO DATA, not business rules:
--   * the 6 movies are real films: English title, genre, running time (Korean listings),
--     Korean release date and poster file are real. Synopses are short own-words summaries.
--     Korean age ratings are NOT verified, except 20th Century Girl (12): TO CONFIRM the
--     three Jujutsu Kaisen films (15), Exhuma (15) and Godzilla x Kong (12).
--     Poster files live in frontend/images/posters/ (source: TMDB). BR-DL-001 sec. 6
--     approves no genre or rating vocabulary. Screenings, prices, rooms, seats, accounts
--     and bookings are demo data.
--   * ticket_price 12000.00 is a demo price (D6 #6: no numeric price approved).
--   * the 3 demo accounts (admin, customer1, customer2) store salted Werkzeug
--     pbkdf2:sha256:600000 hashes for normal alphanumeric demo passwords
--     (admin: admin1234, customer1/customer2: customer1234). Use
--     scripts/set_demo_passwords.py to change them anytime.
--
-- Screening window: 14 consecutive Asia/Seoul calendar days (today .. today + 13) counted
-- from the day the seed is executed, so the demo always has bookable screenings. There are no
-- hard-coded calendar dates. "Today" is the cinema's calendar day (Asia/Seoul), which is what
-- the API uses too; it equals CURRENT_DATE when the session time zone is Asia/Seoul.
-- Slots that have already started today cannot be booked.
-- =============================================================================
BEGIN;

INSERT INTO users(username, password_hash, role) VALUES
 ('admin',     'pbkdf2:sha256:600000$173528b654ee4462$d480b4f9fe069011000fc1e121ceed936139e5a23df83f25ecb24f5052ee2b7a', 'ADMIN'),
 ('customer1', 'pbkdf2:sha256:600000$c2dcfc0b5cb72d2c$ba2bffe6f6ce01dc3fefcbe1a3e9c868666df4caf1bdb2ca94a7e91262cd1b02', 'CUSTOMER'),
 ('customer2', 'pbkdf2:sha256:600000$f545d159cd8e6ced$349d9a1c35a07a870158bb5460acd39d37eb39610f0a42b04e87636d87568a55', 'CUSTOMER');

INSERT INTO movies(title, genre, duration_minutes, rating, synopsis, release_date, poster_url) VALUES
 ('Jujutsu Kaisen 0', 'Animation', 105, '15',
    'Yuta Okkotsu, haunted by the cursed spirit of his childhood friend, is taken in by Tokyo Jujutsu High.',
    DATE '2022-02-17', '/images/posters/jjk-0.jpg'),
 ('Jujutsu Kaisen: Hidden Inventory / Premature Death', 'Animation', 110, '15',
    'Gojo and Geto take on a mission to guard the Star Plasma Vessel, a job that will change both of them.',
    DATE '2025-10-16', '/images/posters/jjk-hidden-inventory.jpg'),
 ('Jujutsu Kaisen: Execution', 'Animation', 87, '15',
    'The Shibuya Incident is retold and followed by a first look at the Culling Game.',
    DATE '2025-12-03', '/images/posters/jjk-execution.jpg'),
 ('20th Century Girl', 'Romance', 119, '12',
    'In 1999, a teenager promises to collect every detail of her best friend''s first crush.',
    DATE '2022-10-06', '/images/posters/20th-century-girl.jpg'),
 ('Exhuma', 'Horror', 134, '15',
    'Shamans, a feng shui master and an undertaker move a wealthy family''s cursed ancestral grave.',
    DATE '2024-02-22', '/images/posters/exhuma.jpg'),
 ('Godzilla x Kong: The New Empire', 'Action', 115, '12',
    'Godzilla and Kong must join forces against a hidden threat buried deep in the Hollow Earth.',
    DATE '2024-03-27', '/images/posters/godzilla-x-kong.jpg');

INSERT INTO theater_rooms(room_name)
SELECT 'Hall ' || n FROM generate_series(1, 5) AS n;

INSERT INTO seats(room_id, seat_row, seat_number)
SELECT r.room_id, chr(65 + row_idx)::char(1), seat_num
FROM theater_rooms r
CROSS JOIN generate_series(0, 4) AS row_idx
CROSS JOIN generate_series(1, 10) AS seat_num;

-- Schedule rotation: for room 1..5 and slot 0..3 (rooms and movies numbered by id order),
--   movie index = ((room_number - 1 + slot) % 6) + 1.
-- Each movie appears 4 times/day; each room has 4 screenings/day (20/day, 280 in 14 days).
-- ends_at = starts_at + movie duration (stored; later duration edits never move it).
-- Longest movie is 134 min, so the 3-hour slot spacing never overlaps.
WITH demo_days AS (
 SELECT (timezone('Asia/Seoul', now())::date + day_offset) AS local_day
 FROM generate_series(0, 13) AS day_offset
), slots AS (
 SELECT slot_idx, (ARRAY['10:00','13:00','16:00','19:00'])[slot_idx + 1]::time AS local_time
 FROM generate_series(0, 3) AS slot_idx
), numbered_rooms AS (
 SELECT room_id, row_number() OVER (ORDER BY room_id) AS room_no FROM theater_rooms
), numbered_movies AS (
 SELECT movie_id, duration_minutes, row_number() OVER (ORDER BY movie_id) AS movie_no FROM movies
), planned AS (
 SELECT m.movie_id, r.room_id, m.duration_minutes,
        (d.local_day + s.local_time) AT TIME ZONE 'Asia/Seoul' AS starts_at,
        d.local_day, s.slot_idx
 FROM demo_days d
 CROSS JOIN numbered_rooms r
 CROSS JOIN slots s
 JOIN numbered_movies m ON m.movie_no = ((r.room_no - 1 + s.slot_idx) % 6) + 1
)
INSERT INTO showtimes(movie_id, room_id, starts_at, ends_at, ticket_price)
SELECT movie_id, room_id, starts_at, starts_at + duration_minutes * interval '1 minute', 12000.00
FROM planned
ORDER BY local_day, room_id, slot_idx;

COMMIT;

-- Verify after seeding:
SELECT 'users' AS entity, count(*) AS actual, 3 AS expected FROM users
UNION ALL SELECT 'movies', count(*), 6 FROM movies
UNION ALL SELECT 'theater_rooms', count(*), 5 FROM theater_rooms
UNION ALL SELECT 'seats', count(*), 250 FROM seats
UNION ALL SELECT 'showtimes', count(*), 280 FROM showtimes;

-- 20 screenings per day:
SELECT (starts_at AT TIME ZONE 'Asia/Seoul')::date AS day, count(*) AS screenings
FROM showtimes GROUP BY 1 ORDER BY 1;
