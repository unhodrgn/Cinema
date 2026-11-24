\ir guard.sql
INSERT INTO showtimes(movie_id,room_id,starts_at,ticket_price)
VALUES(1,1,clock_timestamp()+interval '372 days',12000)
RETURNING showtime_id;
