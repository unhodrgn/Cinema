-- 격리된 시연용 서버와 데이터베이스인지 검사한다.
DO $guard$
BEGIN
  IF current_database() <> 'cinema_live_demo'
     OR current_user <> 'cinema_demo_owner'
     OR current_setting('cinema_demo.isolated', true) IS DISTINCT FROM 'on'
     OR current_setting('server_encoding') <> 'UTF8'
     OR inet_server_addr() IS NOT NULL THEN
    RAISE EXCEPTION 'Refusing to run outside the disposable UTF-8 demo database';
  END IF;
END
$guard$;
