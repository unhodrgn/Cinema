\ir guard.sql
BEGIN ISOLATION LEVEL READ COMMITTED;
SELECT create_booking(2,:demo_showtime,ARRAY[1]::bigint[]);
\prompt 'B가 기다리는 상태를 확인한 후 Enter를 누르세요. ' ready
COMMIT;
