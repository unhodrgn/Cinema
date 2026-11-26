-- 권한 시연: cinema_api 역할의 권한 확인, GRANT/REVOKE 즉시 시연, 권한 부족 거부.
-- 격리된 cinema_test_* DB에서 소유자로 실행한다. 마지막에 ROLLBACK하므로 권한 변경은 남지 않는다.
\ir guard.sql
BEGIN;

-- 1. 역할 속성: 일반 로그인 역할이며 슈퍼유저/DB·역할 생성 권한이 없어야 한다.
SELECT rolname, rolcanlogin, rolsuper, rolcreatedb, rolcreaterole
FROM pg_roles WHERE rolname = 'cinema_api';

-- 2. 테이블별 권한 표 (has_table_privilege)
SELECT t.table_name,
       has_table_privilege('cinema_api', t.table_name, 'SELECT')   AS "SELECT",
       has_table_privilege('cinema_api', t.table_name, 'INSERT')   AS "INSERT",
       has_table_privilege('cinema_api', t.table_name, 'UPDATE')   AS "UPDATE",
       has_table_privilege('cinema_api', t.table_name, 'DELETE')   AS "DELETE",
       has_table_privilege('cinema_api', t.table_name, 'TRUNCATE') AS "TRUNCATE"
FROM (VALUES ('users'),('movies'),('theater_rooms'),('seats'),
             ('showtimes'),('bookings'),('booking_seats')) AS t(table_name)
ORDER BY t.table_name;

-- 3. 부여된 권한 목록 (information_schema)
SELECT table_name, string_agg(privilege_type, ', ' ORDER BY privilege_type) AS privileges
FROM information_schema.role_table_grants
WHERE grantee = 'cinema_api' AND table_schema = 'public'
GROUP BY table_name ORDER BY table_name;

-- 4. REVOKE / GRANT 즉시 시연 (소유자 권한, 트랜잭션 안이므로 ROLLBACK으로 복원)
SELECT has_table_privilege('cinema_api', 'showtimes', 'INSERT') AS before_revoke;
REVOKE INSERT ON showtimes FROM cinema_api;
SELECT has_table_privilege('cinema_api', 'showtimes', 'INSERT') AS after_revoke;
DO $$
BEGIN
 IF has_table_privilege('cinema_api', 'showtimes', 'INSERT') THEN
  RAISE EXCEPTION 'REVOKE had no effect (grants may have been issued by another role)';
 END IF;
END $$;
GRANT INSERT ON showtimes TO cinema_api;
SELECT has_table_privilege('cinema_api', 'showtimes', 'INSERT') AS after_grant;

-- 5. 런타임 역할로 전환하여 허용/거부 확인
SET LOCAL ROLE cinema_api;
SELECT current_user, (SELECT count(*) FROM movies) AS readable_movies;
DO $$
BEGIN
 BEGIN
  DELETE FROM bookings WHERE false;
  RAISE EXCEPTION 'cinema_api unexpectedly has DELETE on bookings';
 EXCEPTION WHEN insufficient_privilege THEN
  RAISE NOTICE '예상된 거부 (%): bookings DELETE (이력 삭제 불가)', SQLSTATE;
 END;
 BEGIN
  UPDATE seats SET seat_number = seat_number WHERE false;
  RAISE EXCEPTION 'cinema_api unexpectedly has UPDATE on seats';
 EXCEPTION WHEN insufficient_privilege THEN
  RAISE NOTICE '예상된 거부 (%): seats UPDATE (좌석 마스터 수정 불가)', SQLSTATE;
 END;
 BEGIN
  UPDATE users SET role = 'ADMIN' WHERE false;
  RAISE EXCEPTION 'cinema_api unexpectedly has UPDATE on users';
 EXCEPTION WHEN insufficient_privilege THEN
  RAISE NOTICE '예상된 거부 (%): users UPDATE (권한 상승 불가)', SQLSTATE;
 END;
END $$;
ROLLBACK;
