-- Run as the schema/function owner in the target database.
-- Supply an existing dedicated login or group role with no owner/admin rights:
--   psql -X -v ON_ERROR_STOP=1 -v app_role=cinema_app -d <new_db> -f database/grant_application_role.sql
-- Manage login and credentials separately. Do not grant this role membership
-- in any owner role or grant it CREATE on public.
\set ON_ERROR_STOP on
BEGIN;

GRANT USAGE ON SCHEMA public TO :"app_role";
GRANT SELECT ON public.users, public.movies, public.theater_rooms, public.seats,
 public.showtimes, public.bookings, public.booking_seats TO :"app_role";
GRANT INSERT (username, password_hash) ON public.users TO :"app_role";
GRANT INSERT (title, genre, duration_minutes, rating, synopsis, release_date),
 UPDATE (title, genre, duration_minutes, rating, synopsis, release_date)
 ON public.movies TO :"app_role";
GRANT INSERT (movie_id, room_id, starts_at, ends_at, ticket_price),
 UPDATE (movie_id, room_id, starts_at, ends_at, ticket_price)
 ON public.showtimes TO :"app_role";

GRANT EXECUTE ON FUNCTION public.expire_overdue_bookings(timestamptz),
 public.screening_seat_availability(bigint), public.create_booking(bigint,bigint,bigint[]),
 public.pay_booking(bigint,bigint), public.cancel_booking(bigint,bigint)
 TO :"app_role";

COMMIT;
