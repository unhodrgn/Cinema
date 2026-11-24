\ir 00_guard.sql
CREATE TEMP VIEW demo_cases AS
SELECT row_number() OVER (ORDER BY starts_at DESC, showtime_id) AS case_no,
       showtime_id, room_id, movie_id, starts_at, ends_at, ticket_price
FROM public.showtimes
WHERE starts_at > now() + interval '1 day';
CREATE TEMP VIEW demo_customers AS
SELECT row_number() OVER (ORDER BY username) AS customer_no, user_id
FROM public.users WHERE username IN ('customer_demo', 'customer_demo2');
