-- Cinema on Neon (cloud PostgreSQL 18): runtime role and grants.
-- Run AFTER migrations 0001, 0003..0006 (0002 is applied below) as the Neon project owner:
--   psql -X -v ON_ERROR_STOP=1 -v runtime_password='<DB_PASSWORD>' "$OWNER_URL" -f database/cloud/setup_neon.sql
-- Same grants as backend/migrations/compose-role.sql + 0002_movie_delete_permissions.sql.
BEGIN;
CREATE ROLE cinema_api LOGIN PASSWORD :'runtime_password';
GRANT USAGE ON SCHEMA public TO cinema_api;
GRANT SELECT ON users, movies, theater_rooms, seats, showtimes, bookings, booking_seats TO cinema_api;
GRANT INSERT ON users TO cinema_api;
GRANT INSERT, UPDATE ON movies, showtimes, bookings TO cinema_api;
GRANT INSERT, DELETE ON booking_seats TO cinema_api;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO cinema_api;
GRANT DELETE ON movies, showtimes TO cinema_api;
-- PG16+: lets the owner run "SET ROLE cinema_api" (needed by database/demo/permissions_grants.sql).
GRANT cinema_api TO CURRENT_USER WITH INHERIT FALSE, SET TRUE;
COMMIT;
