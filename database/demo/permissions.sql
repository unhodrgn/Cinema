\ir guard.sql
BEGIN;
SET LOCAL ROLE cinema_api;
SELECT current_user,
 has_table_privilege(current_user,'showtimes','INSERT') AS can_insert_showtimes,
 has_table_privilege(current_user,'bookings','DELETE') AS can_delete_history,
 has_table_privilege(current_user,'bookings','TRUNCATE') AS can_truncate_history,
 has_table_privilege(current_user,'seats','UPDATE') AS can_edit_seats;
DO $$
BEGIN
 BEGIN
  DELETE FROM bookings WHERE false;
  RAISE EXCEPTION 'Runtime role unexpectedly has DELETE permission';
 EXCEPTION WHEN insufficient_privilege THEN
  RAISE NOTICE '예상된 이력 삭제 거부: %', SQLSTATE;
 END;
END $$;
ROLLBACK;
