-- Runs only while creating a fresh Compose development volume.
\getenv runtime_password CINEMA_APP_PASSWORD
BEGIN;
CREATE ROLE cinema_api LOGIN PASSWORD :'runtime_password';
GRANT USAGE ON SCHEMA public TO cinema_api;
GRANT SELECT ON users, movies, theater_rooms, seats, showtimes, bookings, booking_seats TO cinema_api;
GRANT INSERT ON users TO cinema_api;
GRANT INSERT, UPDATE ON movies, showtimes, bookings TO cinema_api;
GRANT INSERT, DELETE ON booking_seats TO cinema_api;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO cinema_api;
COMMIT;
