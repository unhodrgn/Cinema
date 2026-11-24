# PostgreSQL 실시간 SQL 시연 안내

신규 PostgreSQL UTF-8 임시 클러스터에서만 실행한다. 각 접속은 전용 Unix 소켓, 시연 DB 이름, DB 역할 및 서버 표식을 확인한다. 임시 서버는 TCP로 수신하지 않는다. 아래 명령은 저장소 루트에서 실행한다. 설치된 PostgreSQL의 initdb, pg_ctl, createdb, dropdb, psql과 btree_gist가 필요하다.

## 준비 및 단일 세션 시연

```bash
DEMO_DIR="$(bash database/demo/demo.sh setup)"
printf '%s\n' "$DEMO_DIR"
bash database/demo/demo.sh run "$DEMO_DIR" 01_inspect.sql
bash database/demo/demo.sh run "$DEMO_DIR" 02_booking_lifecycle.sql
bash database/demo/demo.sh run "$DEMO_DIR" 03_exceptions.sql
bash database/demo/demo.sh run "$DEMO_DIR" 04_permissions.sql
```

| 파일 | 설명 | 확인할 출력 |
|---|---|---|
| 01_inspect.sql | 버전, UTF-8, 일곱 테이블, 시드 및 제약 정의 조회 | 계정 3, 영화 5, 상영관 5, 좌석 250, 회차 140, 예매·상세 각 0 |
| 02_booking_lifecycle.sql | 한 좌석 확정, 중복 거부, 취소·좌석 재사용, 결제 시 만료 | BOOKED/UNPAID와 10분 기한, UC002, CANCELLED 및 좌석 해제, 같은 좌석 재예매, EXPIRED/UNPAID 및 해제 |
| 03_exceptions.sql | 타 상영관 좌석과 같은 상영관의 중첩 일정 거부 | UC003, 23P01, 잘못된 요청의 부분 예매 0건 |
| 04_permissions.sql | 실제 권한 스크립트를 적용한 앱 그룹 역할로 실행 | can_book=t, can_delete_history=f, can_truncate_history=f, CANCELLED, 직접 DELETE에 42501 |

만료 장면은 약 10분의 대기를 피하기 위해 폐기용 DB에서 기존 검증 트리거 하나를 잠시 중지하고 기한을 11분 과거로 이동한다. 트리거를 복구한 뒤 운영과 동일한 pay_booking을 호출한다. 라이프사이클, 예외 및 권한 스크립트의 데이터 변경은 모두 롤백한다.

## 두 터미널에서 좌석 경합 재현

A와 B를 같은 저장소 루트에서 연다. A에서 아래 명령으로 psql을 시작한다.

```bash
bash database/demo/demo.sh session "$DEMO_DIR"
```

A의 psql에서 다음을 입력한다. 예매 ID가 출력되어도 아직 커밋하지 않는다.

```sql
\i database/demo/05_concurrent_a.sql
```

B에서 A의 준비 단계가 출력한 동일한 경로를 사용한다. 명령을 시작하면 A의 잠금을 대기한다.

```bash
# A 터미널에서 출력한 실제 경로로 지정한다.
DEMO_DIR=/tmp/cinema-live.복사한경로
bash database/demo/demo.sh run "$DEMO_DIR" 05_concurrent_b.sql
```

**B가 대기하면 5초 이내**에 A의 psql에서 COMMIT;을 입력한다. 대기 시간이 초과되면 55P03이 발생할 수 있으므로, 발표 중에는 미리 두 창을 나란히 배치한다. 정상 시 B는 UC002를 출력한다. A에서 이어서 아래 명령을 실행하여 부모 1건과 좌석 배정 1건을 확인한다.

```sql
COMMIT;
\i database/demo/05_concurrent_verify.sql
\q
```

A의 커밋은 폐기용 DB에 남는다. 이 장면을 반복할 때는 새 시연 DB를 생성한다.

## 정리 및 자동 검증

두 세션을 종료한 뒤 다음 명령을 실행한다. 시연 스크립트가 생성한 DB만 제거하고 해당 클러스터만 중지한다. 중지된 클러스터 파일은 출력된 임시 경로에 남는다.

```bash
bash database/demo/demo.sh cleanup "$DEMO_DIR"
bash database/demo/verify.sh
```

verify.sh는 별도의 임시 클러스터를 만들어 전체 흐름을 검증한다. 동시성 단계에서 pg_blocking_pids로 B가 실제로 A의 잠금을 기다리는지 관측한 뒤, UC002와 최종 1건을 검사한다. [저장소 실행 증빙](verification.log)과 [분리 패키지 실행 증빙](standalone_verification.log)은 각각의 실제 검증 출력이다. 공유본에는 로컬 사용자명 및 임시·저장소 절대 경로를 가렸다.

## 발표 진행 순서 — 약 3분

1. 25초: 일곱 테이블과 시드 수량, 회차·좌석 UNIQUE를 확인한다.
2. 45초: 정상 예매, 중복 거부, 취소 후 재예매와 만료를 설명한다.
3. 25초: 잘못된 상영관과 겹치는 회차의 거부 코드를 표시한다.
4. 50초: 두 창에서 잠금 대기 → A 커밋 → B의 UC002 → 최종 한 건을 시연한다.
5. 35초: 앱 역할의 함수 실행과 직접 삭제 거부를 대조한다.
