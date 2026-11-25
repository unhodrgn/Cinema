\ir guard.sql
BEGIN;
CREATE FUNCTION pg_temp.demo_rejection(statement text, expected text) RETURNS void
LANGUAGE plpgsql AS $$
BEGIN
 BEGIN
  EXECUTE statement;
 EXCEPTION WHEN OTHERS THEN
  IF SQLSTATE = expected THEN
   RAISE NOTICE '예상된 오류: %', SQLSTATE;
   RETURN;
  END IF;
  RAISE;
 END;
 RAISE EXCEPTION 'Expected SQLSTATE %', expected;
END $$;

INSERT INTO showtimes(movie_id,room_id,starts_at,ticket_price)
VALUES(1,1,clock_timestamp()+interval '371 days',12000)
RETURNING showtime_id,starts_at \gset
SELECT create_booking(2,:showtime_id,ARRAY[1]::bigint[]);
SELECT pg_temp.demo_rejection(format('SELECT create_booking(3,%s,ARRAY[1]::bigint[])',:showtime_id),'UC002');
SELECT pg_temp.demo_rejection(format('SELECT create_booking(3,%s,ARRAY[51]::bigint[])',:showtime_id),'UC003');
SELECT pg_temp.demo_rejection(format('INSERT INTO showtimes(movie_id,room_id,starts_at,ticket_price) VALUES(1,1,%L,12000)', :'starts_at'),'23P01');
SELECT pg_temp.demo_rejection('INSERT INTO showtimes(movie_id,room_id,starts_at,ticket_price) VALUES(1,1,now()+interval ''380 days'',''NaN''::numeric)','23514');
SELECT pg_temp.demo_rejection('INSERT INTO showtimes(movie_id,room_id,starts_at,ticket_price) VALUES(1,1,now()+interval ''380 days'',-1)','23514');
SELECT count(*) AS committed_candidate FROM bookings WHERE showtime_id=:showtime_id;
SET CONSTRAINTS ALL IMMEDIATE;
ROLLBACK;
