# 데이터베이스 SQL 시연

## 테스트 준비

PostgreSQL 18의 **새 격리 서버/Compose 테스트 프로젝트**에 `cinema_test_demo`를 만들고, 소유자로 0001·0003·0004와 데모 seed를 순서대로 적용한다. `permissions.sql`까지 실행하려면 그 격리 서버에서 `compose-role.sql`과 0002로 `cinema_api`를 준비한다. 서버·포트·DB를 명시적으로 확인한다. 기존 데모와 로컬 운영 DB에는 실행하지 않는다.

아래 예시는 테스트 서버 연결을 확인한 후 저장소 루트에서 실행한다. 각 스크립트는 DB 이름과 0004 제약을 먼저 확인한다.

```sh
psql -X -v ON_ERROR_STOP=1 -d cinema_test_demo -f database/demo/main.sql
psql -X -v ON_ERROR_STOP=1 -d cinema_test_demo -f database/demo/exceptions.sql
psql -X -v ON_ERROR_STOP=1 -d cinema_test_demo -f database/demo/permissions.sql
```

## 주 시나리오 3–4분

| 시간 | 실행과 확인 |
|---|---|
| 0:00–0:35 | `main.sql` 시작 출력에서 격리 DB와 역할, 영화·좌석·상영 건수를 확인한다. |
| 0:35–1:25 | 미래 상영의 두 좌석 예매, BOOKED/UNPAID와 24,000.00을 설명한다. |
| 1:25–2:25 | 결제 후 취소를 보여 준다. CANCELLED/PAID 및 24,000.00은 남고 활성 좌석은 0이다. 다른 고객이 같은 좌석을 다시 잡는다. |
| 2:25–3:45 | `exceptions.sql`에서 중복 UC002, 다른 관 UC003, 시간 중복 23P01, NaN/음수 23514를 설명한다. 시간이 남으면 `permissions.sql`의 42501을 보여 준다. |

## 예비 시연과 복원

- 권한 스크립트는 owner 연결에서 `SET LOCAL ROLE cinema_api`를 사용한다. 상영 INSERT는 가능하고 bookings DELETE/TRUNCATE 및 seats UPDATE는 불가하다.
- 두 터미널을 사용할 때 `concurrency_prepare.sql`을 한 번 실행하고 출력된 상영 ID를 기록한다. 터미널 A에서 `psql -X -d cinema_test_demo -v demo_showtime=<ID> -f database/demo/concurrency_a.sql`을 실행한다. A가 대기 프롬프트에 도달하면 B에서 같은 명령의 파일을 `concurrency_b.sql`로 바꾸어 실행한다. 30초 안에 A에서 Enter를 눌러 커밋한다. B에서 UC002와 활성 배정 1건을 확인한다. 예시에 있는 `<ID>` 전체를 실제 숫자로 바꾼다.
- `main.sql`, `exceptions.sql`, `permissions.sql`은 ROLLBACK한다. Identity sequence 값은 일반적으로 되돌아가지 않는다. 동시성 A의 커밋은 관찰을 위해 보존된다. 처음 상태로 시연하려면 **다른 새 격리 DB**에서 같은 체인과 seed를 실행한다.
