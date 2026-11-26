# 통합 DB 덤프 (응용 프로그램 + 데이터베이스 통합 파일용)

PostgreSQL 18에서 만든 **전체 데이터베이스 덤프**다. 스키마(마이그레이션 `0001`~`0005`: 테이블 7개, 트리거 9개, 인덱스, 함수 4개, `btree_gist` 확장)와 데모 데이터를 함께 담는다. 응용 프로그램(`backend/`, `frontend/`)과 `docker-compose.yml`은 저장소에 있다.

| 파일 | 형식 | 복원 방법 |
|---|---|---|
| `cinema_full.sql` | 일반 SQL (`pg_dump --format=plain`) | `psql -f` |
| `cinema_full.dump` | 사용자 지정 형식 (`pg_dump --format=custom`) | `pg_restore` |
| `cinema_schema.sql` | **DDL만** 담은 일반 SQL (`--schema-only`, 마이그레이션 `0001`~`0005`를 하나로 합친 결과, 데이터 없음) | `psql -f` (psql 버전 제한 없음) |

## 내용

- 계정 3개(`admin`, `customer1`, `customer2`), 영화 6편, 상영관 5개, 좌석 250석, 상영 일정 280회, 예매 0건. 데모 데이터는 `backend/seeds/demo.sql`과 같다.
- **상영 일정은 덤프를 만든 날(2026-11-26)부터 14일치**(2026-11-26 ~ 2026-12-09)다. 시드가 날짜를 상대적으로 만들기 때문이다. 이후 날짜에 쓰려면 아래 "다시 만들기"로 새로 덤프하거나, 상영 관리 화면에서 상영 일정을 추가한다.
- `--no-owner --no-acl`로 만들었다. 소유자와 권한(GRANT)은 들어 있지 않으므로 복원한 DB를 응용 프로그램이 쓰려면 런타임 역할 권한을 따로 준다 (`backend/migrations/compose-role.sql`, `0002_movie_delete_permissions.sql`). Compose로 새 볼륨을 만들면 이 과정은 자동으로 실행된다.
- 일반 SQL 파일에는 PostgreSQL 18의 `\restrict` 메타 명령이 들어 있어 **psql 18 이상**으로 복원해야 한다 (Compose의 `db` 컨테이너가 18이다).

## 복원 (Compose, 운영체제 무관)

저장소 루트에서 실행한다. 기존 `cinema` DB는 건드리지 않고 `cinema_restore`를 새로 만든다.

```sh
docker compose up -d --wait db
docker compose cp database/dump db:/tmp/dump
docker compose exec db psql -X -v ON_ERROR_STOP=1 -U cinema_owner -d postgres -c "CREATE DATABASE cinema_restore"
docker compose exec db psql -X -v ON_ERROR_STOP=1 -U cinema_owner -d cinema_restore -f /tmp/dump/cinema_full.sql
```

사용자 지정 형식을 쓰려면 마지막 줄 대신 아래를 실행한다.

```sh
docker compose exec db pg_restore -U cinema_owner -d cinema_restore --exit-on-error /tmp/dump/cinema_full.dump
```

## 다시 만들기 (제출 직전 날짜를 새로 맞출 때)

격리된 서버(예: Compose의 `test-db`)에 빈 DB를 만들고 마이그레이션과 시드를 적용한 뒤 덤프한다. 운영 DB(`cinema`)에서 덤프하지 않는다.

```sh
docker compose --profile test up -d --wait test-db
docker compose exec test-db psql -X -U cinema_test_owner -d postgres -c "CREATE DATABASE cinema_pkg"
# 0001, 0003, 0004, 0005, seeds/demo.sql 을 이 순서로 적용 (각각: -v ON_ERROR_STOP=1 -d cinema_pkg < 파일)
docker compose exec -T test-db pg_dump -U cinema_test_owner --no-owner --no-acl --format=plain --encoding=UTF8 cinema_pkg > database/dump/cinema_full.sql
docker compose exec -T test-db pg_dump -U cinema_test_owner --no-owner --no-acl --format=custom cinema_pkg > database/dump/cinema_full.dump
docker compose exec test-db psql -X -U cinema_test_owner -d postgres -c "DROP DATABASE cinema_pkg"
```

바이너리 덤프는 PowerShell의 `>` 리디렉션으로 만들면 깨지므로 Git Bash나 cmd에서 실행한다.

## 검증 (2026-11-26)

두 형식을 각각 새 DB에 복원해 원본과 비교했다. 사용자 3 / 영화 6 / 좌석 250 / 상영 280, 트리거 9, 인덱스 21(기본키·고유 제약 포함), 핵심 함수 4개, 상영·사용자 행 전체의 md5가 모두 같았다. 복원한 DB에서 `create_booking()`이 정상 동작했다.
