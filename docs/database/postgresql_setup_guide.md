# PostgreSQL 신규 설치 및 검증 안내서

## 설치 전 확인

저장소 루트에서 실행한다. 대상은 전용 신규 UTF-8 데이터베이스다. PostgreSQL 14 이상을 대상으로 작성되었으며 18.7에서 검증했다. 서버에 btree_gist 확장이 제공되어야 한다. 신규 인스턴스 주소·포트를 지정하고 운영 DB와 분리한다. 기존 데이터베이스에 스키마와 시드를 재적용하는 절차는 제공하지 않는다.

## 신규 DB 및 계정

관리자가 전용 객체 소유자 cinema_owner, 앱 로그인 cinema_app_login, 권한 그룹 cinema_app을 미리 준비한다. 일반적인 앱 연결이 그룹 권한을 상속하도록 설정한다. 앱 로그인에 소유자 멤버십, CREATE ROLE 또는 슈퍼유저 권한을 부여하지 않는다. SQL 도구는 명시적으로 신규 인스턴스에 연결하며 인증 정보는 환경의 비밀 관리 도구 또는 libpq 설정으로 공급한다. 예시 역할 이름이 사용 중인 경우 다른 이름을 선택한다.

```sql
CREATE ROLE cinema_owner LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE ROLE cinema_app NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE ROLE cinema_app_login LOGIN INHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE;
GRANT cinema_app TO cinema_app_login;
```

인증 정책에 따라 객체 소유자와 앱 로그인의 인증 수단을 별도로 설정한다.

```bash
createdb --template=template0 --encoding=UTF8 --owner=cinema_owner cinema_integration
PGOPTIONS='-c search_path=public,pg_catalog' psql -X -v ON_ERROR_STOP=1 -U cinema_owner -d cinema_integration -f database/schema.sql
psql -X -v ON_ERROR_STOP=1 -U cinema_owner -d cinema_integration -f database/seed.sql
psql -X -v ON_ERROR_STOP=1 -U cinema_owner -d cinema_integration -v app_role=cinema_app -f database/grant_application_role.sql
```

첫 명령은 DB 생성 권한을 가진 계정으로 실행한다. 이후 명령은 전용 객체 소유자로 실행한다. schema.sql, seed.sql은 한 번씩 적용한다. 정식 운영 환경에서 시연용 계정과 영화 데이터를 사용할지는 별도로 결정한다.

앱은 DB_HOST, DB_PORT, DB_NAME, DB_USER를 지정하고 DB_PASSWORD 또는 별도 libpq 인증을 사용한다. 다음 조회로 함수의 소유자, 실행 권한과 설정을 확인할 수 있다.

```sql
SELECT p.oid::regprocedure AS function_name,
       pg_get_userbyid(p.proowner) AS owner,
       p.prosecdef AS security_definer, p.proconfig, p.proacl
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'public' AND p.prosecdef
ORDER BY p.oid::regprocedure::text;

SELECT has_schema_privilege('cinema_app_login', 'public', 'CREATE') AS app_can_create,
       has_table_privilege('cinema_app_login', 'public.bookings', 'DELETE') AS app_can_delete,
       has_table_privilege('cinema_app_login', 'public.bookings', 'TRUNCATE') AS app_can_truncate;
```

세 플래그는 모두 false여야 한다. 다섯 업무 함수 소유자는 cinema_owner와 같은 전용 소유자여야 한다. 시드에는 관리자 1명과 고객 2명의 데모 해시가 있다. 평문 비밀번호는 확인되지 않았으므로 로그인 시연 전 별도로 승인된 방식으로 신규 DB의 데모 자격 증명을 마련한다.

## 폐기용 검증 실행

별도 테스트 서버가 없다면 저장소 루트에서 다음 명령으로 임시 서버를 기동하고 종료할 수 있다. trust 인증은 이 임시 경로의 Unix 소켓에만 적용한다. 명령은 하나의 Bash 하위 셸에서 실행한다.

```bash
(
  set -euo pipefail
  umask 077
  qa_dir="$(mktemp -d /tmp/cinema-submission.XXXXXX)"
  unset PGSERVICE PGSERVICEFILE PGHOSTADDR PGDATABASE PGOPTIONS PGPASSWORD
  export PGHOST="$qa_dir" PGPORT=59485 PGUSER=cinema_qa_owner
  initdb -D "$qa_dir/pg" -U "$PGUSER" --encoding=UTF8 --no-locale -A trust
  pg_ctl -D "$qa_dir/pg" -l "$qa_dir/server.log" \
    -o "-k $PGHOST -p $PGPORT -c listen_addresses='' -c timezone=Asia/Seoul" start
  trap 'pg_ctl -D "$qa_dir/pg" stop -m fast' EXIT
  psql -X -d postgres -c "SELECT version(), current_setting('server_encoding'), inet_server_addr() IS NULL AS unix_socket;"
  PYTHON="$(command -v python3)" bash database/tests/run_all.sh
)
```

위 절차는 사용 중인 서버에 연결하지 않는다. PostgreSQL 클라이언트·서버 도구와 psycopg2를 설치한 Python 환경을 사용한다. 기존에 격리된 테스트 인스턴스가 있다면 아래의 일반 절차를 사용한다.

별도의 UTF-8 테스트 인스턴스에서 접속 대상과 현재 역할을 확인한다. 실행 역할에는 테스트 DB와 임시 역할의 생성 권한이 필요하다. 저장소 requirements.txt의 psycopg2-binary 등을 설치한 환경을 사용한다.

```bash
psql -X -d postgres -c 'SELECT current_user, current_database(), version();'
bash database/tests/run_all.sh
```

런너는 고유 DB를 새로 만들고 검증 후 해당 DB를 제거한다. PYTHON 환경 변수로 테스트용 인터프리터를 지정할 수 있다. 기존 DB에서 무결성·동시성 테스트를 직접 실행하지 않는다. 확인 결과는 [검증 결과 보고서](database_test_documentation.md), 실제 로그와 발표용 명령은 [검증 증빙](evidence/README.md)을 참조한다.
