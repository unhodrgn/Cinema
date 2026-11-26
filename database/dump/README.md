# PostgreSQL 18 · 마이그레이션 0006

| 파일 | 내용 |
|---|---|
| `cinema_schema.sql` | 스키마만 포함. psql 18 이상으로 복원 |
| `cinema_full.sql` | 스키마 + 데모 카탈로그. psql 18 이상으로 복원 |
| `cinema_full.dump` | 같은 스키마 + 데모 카탈로그의 custom 형식. pg_restore 18 이상으로 복원 |

데모에는 영화 6편, 상영관 5개, 좌석 250석, 상영 일정 280회(2026-11-27~2026-12-10)가 있다. 계정, 비밀번호 해시, 예매, 운영 데이터는 포함하지 않는다. 소유자와 ACL은 제외했다. 빈 테스트 DB에서 복원하며, 앱 연결에 필요한 런타임 권한은 `backend/migrations/compose-role.sql`과 `0002_movie_delete_permissions.sql`을 참조한다.

## 다시 만들기

1. 새 격리 PostgreSQL 18 인스턴스의 빈 DB에 0001~0006과 필요한 런타임 역할을 순서대로 적용한다. Compose 신규 프로젝트가 같은 순서로 초기화한다.
2. 같은 빈 DB에 `backend/seeds/demo.sql`을 실행한다. 데모 전용 DB임을 확인한 뒤 `TRUNCATE public.users RESTART IDENTITY CASCADE`로 계정과 관련 예매 데이터를 제거한다.
3. 해당 데모 DB에 `pg_dump --no-owner --no-acl --encoding=UTF8`을 사용한다. `--schema-only`, `--format=plain`, `--format=custom`으로 세 파일을 만든다.
4. 별개의 빈 DB에서 plain SQL은 `psql -X -v ON_ERROR_STOP=1`로, custom 파일은 `pg_restore --single-transaction --exit-on-error`로 복원한다. 카탈로그 수와 `users_username_format_check` 검증 여부를 비교한다.

[복원 결과](../verification/0006/demo-dump-restore.txt) · [0005 보존본](../history/0005/README.md)
