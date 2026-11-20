# PostgreSQL 개선 사항 인수인계 — Member B

**상태:** 신규 데이터베이스 기준으로 Member A가 인수인계를 승인했다. 애플리케이션 배포 승인은 아래 연동 및 회귀 검증을 완료한 뒤 별도로 판단한다. 승인된 B01–B05와 D1–D6을 적용한다.

## 1. 스키마와 동작 변경

- `booking_seats.showtime_id`는 부모 예매에서 채운다. `booking_seats_booking_showtime_fk`는 `(booking_id, showtime_id)`를 부모의 `bookings_id_showtime_key`에 연결하며 부모 삭제 시 `RESTRICT`를 적용한다.
- `booking_seats_showtime_seat_key`는 `(showtime_id, seat_id)`를 유일하게 유지한다. 기존 `(booking_id, seat_id)` 유일성도 유지한다. 취소 및 만료 시 좌석 상세 행을 삭제하여 같은 회차에서 다시 예매할 수 있다.
- 예매 이력은 삭제할 수 없다. 트리거가 `bookings`의 `DELETE`와 `bookings` 및 `booking_seats`의 `TRUNCATE`를 차단한다. 취소 및 만료 이후에도 부모가 남아 D2의 상영 일정 변경 제한을 유지한다.
- 결제 및 취소는 예매 행을 잠근 후 PostgreSQL 시각으로 기한을 평가한다. 기한이 지난 미결제 예매는 `EXPIRED`로 전환하고 좌석을 해제한다. 결제 기한은 확정 시각부터 10분이다.
- `bookings.total_amount`는 `numeric(12,2)`, 단가와 확정 당시 좌석별 단가는 `numeric(10,2)`다. 세 금액 열은 음수 및 유한하지 않은 값을 허용하지 않는다. 최고 단가에서 50석의 총액은 `4999999999.50`이다.
- 상영 일정 ID의 중복 저장은 회차별 좌석 유일성을 선언적으로 보장하기 위한 물리 설계다. 복합 외래 키가 값을 일치시키며, 논리·물리 ERD 및 정규화 설명은 Member A의 별도 문서 검토 대상이다.

## 2. 애플리케이션에 공개하는 DB 함수

| 함수 | 계약 |
| --- | --- |
| `screening_seat_availability(bigint)` | 해당 회차의 미결제 예매 상태를 정리하고 `seat_id`, `seat_row`, `seat_number`, `is_available`을 반환한다. 없는 회차는 `UC011`을 반환한다. |
| `create_booking(bigint, bigint, bigint[])` | 인증된 고객 ID, 회차 ID, 좌석 ID 배열을 받아 좌석을 원자적으로 확정하고 예매 ID를 반환한다. |
| `pay_booking(bigint, bigint)` | 예매 ID와 인증된 고객 ID를 받아 `PAID` 또는 새로 확정된 `EXPIRED`를 반환한다. |
| `cancel_booking(bigint, bigint)` | 예매 ID와 인증된 고객 ID를 받아 `CANCELLED` 또는 새로 확정된 `EXPIRED`를 반환한다. |
| `expire_overdue_bookings(timestamptz DEFAULT clock_timestamp())` | 관리자 목록 및 예매 이력에 사용할 전체 정리 함수다. 애플리케이션은 인수 없이 호출한다. 잠긴 행은 건너뛰므로 좌석 조회의 판정에 사용할 수 없다. |

`expire_locked_showtime_bookings(bigint)`는 회차 잠금을 선행한 내부 호출 전용이다. 결제 및 취소에 시각 인수를 전달하는 이전 호출 형태는 제거되었다. 좌석 조회의 결과는 조회 시점의 상태이며, 고객이 좌석을 선택해도 확정 요청 전에는 점유되지 않는다.

## 3. Flask 연동과 오류 처리

| 파일과 함수 | 작업 |
| --- | --- |
| `app/screenings.py` · `get_screening_seats()` | 기존 전체 정리 함수 호출과 별도 만료 시각 필터를 `SELECT * FROM public.screening_seat_availability(%s)`로 대체한다. 같은 트랜잭션에서 회차 메타데이터를 읽고 기존 `screening` 및 `seats` 응답 구조를 유지한다. 비로그인 접근을 유지한다. |
| `app/booking.py` · `create_booking()`, `pay_booking()`, `cancel_booking()` | 요청 본문이 아닌 인증 세션에서 고객 ID를 가져온다. 결제 및 취소의 `outcome=EXPIRED`는 커밋할 업무 결과다. 트랜잭션을 커밋한 뒤 응답하고, 기한 초과를 이유로 커밋 전에 예외를 던지지 않는다. |
| `app/booking.py` · `list_bookings()`; `app/admin.py` · `admin_list_bookings()` | 부모 상태와 좌석 상세를 한 SQL 문 또는 동일한 스냅샷에서 읽는다. 전체 정리는 이력 조회에 사용할 수 있다. 권한 및 고객별 조회 범위는 유지한다. |
| `app/database.py` · `transaction()`, `expire_overdue_bookings()`; `app/errors.py` · `describe_database_error()` | SQLSTATE 기반 매핑과 트랜잭션 단위 재시도를 구현한다. 오류 위치가 SQL 실행 또는 커밋일 수 있으므로, 재시도는 트랜잭션 컨텍스트 바깥에서 수행한다. |

| SQLSTATE | 처리 |
| --- | --- |
| `UC002` | HTTP 409, `seat_unavailable`. 자동 재시도 없이 좌석 새로고침 및 재선택을 안내한다. |
| `40001` | 롤백 후 새 스냅샷으로 **전체 트랜잭션**을 제한 횟수만큼 다시 실행한다. 최종 실패는 HTTP 503, `booking_retry`. |
| `55P03` | 롤백하고 HTTP 503, `booking_retry`를 반환한다. 응답을 좌석 점유 확정으로 해석하지 않는다. 동일 트랜잭션에서 재시도하지 않는다. |
| `UC011` | 기존 HTTP 404 계약을 유지한다. |

상호작용 함수의 DB 잠금 대기는 잠금 획득 시도당 5초다. 요청 전체의 제한 시간 및 재시도 예산도 별도로 설정한다. 조회·확정은 **회차 → 예매 ID 오름차순 → 좌석 상세**, 결제·취소는 **예매 → 좌석 상세** 순서를 사용한다. 전체 정리는 예매만 잠그며 이미 잠긴 행은 건너뛴다. 한 트랜잭션에 업무 쓰기 요청 하나를 처리하고, 전체 정리를 실행한 트랜잭션에서 이후 회차 잠금을 요청하지 않는다.

## 4. 신규 PostgreSQL 데이터베이스와 실행 역할

새 DB 또는 격리된 개발 인스턴스에서 수행한다. 아래 이름은 예시다. 접속 주소·포트는 신규 인스턴스로 지정하고 인증 정보는 저장소 밖에서 관리한다.

1. PostgreSQL 관리자가 전용 로그인 `cinema_owner`, 전용 로그인 `cinema_app_login`, 그룹 역할 `cinema_app`을 준비한다. 두 로그인에 슈퍼유저, 역할 생성 등의 관리 권한을 부여하지 않는다. `cinema_app_login`에 `cinema_app` 멤버십만 부여하고, 객체 소유자에 대한 멤버십을 주지 않는다.
2. 관리자가 전용 소유자를 지정하여 빈 UTF-8 DB를 만든다. 소유자로 `public`에 스키마와 seed를 적용하고 그룹 역할에 권한을 부여한다. `btree_gist`를 사용할 수 있어야 한다.

```sh
createdb --template=template0 --encoding=UTF8 --owner=cinema_owner cinema_integration
PGOPTIONS='-c search_path=public,pg_catalog' psql -X -v ON_ERROR_STOP=1 -U cinema_owner -d cinema_integration -f database/schema.sql
psql -X -v ON_ERROR_STOP=1 -U cinema_owner -d cinema_integration -f database/seed.sql
psql -X -v ON_ERROR_STOP=1 -U cinema_owner -d cinema_integration -v app_role=cinema_app -f database/grant_application_role.sql
```

3. Flask의 `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`를 신규 인스턴스 및 앱 로그인으로 설정한다. 승인된 비밀 관리 방식으로 `DB_PASSWORD` 또는 libpq 인증을 구성한다. 이 서비스 계정은 최종 사용자에게 노출하지 않는다.
4. 배포 시 위 다섯 업무 함수의 소유자가 전용 객체 소유자인지 확인한다. 함수의 고정 `search_path`는 `pg_catalog, public, pg_temp`다. 스키마는 `PUBLIC`의 `public` 스키마 `CREATE`와 다섯 업무 함수·내부 정리 함수의 `PUBLIC EXECUTE`를 철회한다. 앱 로그인과 상속 역할에도 `public` 스키마 `CREATE`를 부여하지 않는다.
5. 앱 역할은 필요한 조회, 가입에 필요한 열의 삽입, 영화·회차에 필요한 열의 삽입·수정, 다섯 업무 함수 실행 권한을 갖는다. 예매 테이블 직접 변경, 이력 삭제·절단, 내부 정리 함수 실행 및 계정 역할 변경 권한은 부여하지 않는다. Flask가 고객 인증 및 권한을 확인하므로 앱 로그인은 신뢰된 서버에서만 사용한다.

DB 회귀 테스트는 별도의 폐기용 인스턴스에서 `bash database/tests/run_all.sh`로 실행한다. 실행 계정에는 해당 인스턴스에서 DB와 임시 테스트 역할을 생성할 권한이 필요하고, Python 환경에는 `psycopg2`가 필요하다. 스크립트는 고유한 UTF-8 테스트 DB를 만들고 종료 시 정리한다.

## 5. 프런트엔드 및 통합 회귀 검증

- `frontend/js/pages/seats.js`의 확정 핸들러에서 `seat_unavailable`은 좌석 재선택으로, `booking_retry`는 다시 조회 또는 재시도로 연결한다.
- `frontend/js/pages/booking.js`의 상세 표시와 결제·취소 핸들러, `frontend/js/pages/bookings.js`의 이력 표시와 취소 핸들러에서 `EXPIRED` 결과를 명시한다. `BOOKED` 상세에는 각 좌석의 `price_at_booking`을 표시한다. API 금액은 십진 문자열을 유지한다.
- 실제 앱 역할로 가입, 회차 관리, 좌석 조회, 확정, 결제, 취소 및 만료를 검증한다. 별도 연결에서 만료 커밋과 좌석 해제를 확인하고 권한 없는 고객 요청이 거부되는지 점검한다.
- 잠긴 미결제 예매의 기한이 지난 상황에서 좌석 조회와 확정을 동시에 호출한다. 잠금 해제, 유효한 결제의 커밋, 잠금 시간 초과를 각각 검증한다. `40001` 재시도는 신규 트랜잭션에서 수행되고 예매 중복을 만들지 않아야 한다.
- 취소 또는 만료가 이력 조회와 교차하는 상황에서 응답 상태와 좌석 목록이 동일한 스냅샷에 속하는지 확인한다. 50석 최고가 총액 및 좌석별 금액의 API와 UI 표현을 검증한다.

## 6. 실행 결과와 승인 조건

개선 작업의 최종 검증은 PostgreSQL 18.7, 신규 UTF-8 폐기용 DB에서 실행했다. 스키마 및 seed 적용 성공, SQL 무결성 **199/199**, reconciliation **31 MATCH / 0 MISMATCH**, 동시성 **58/58**, 실제 권한을 부여한 테스트 역할 확인 **통과**다. 기존 앱 pytest는 **1197 통과, 2 건너뜀, 0 실패**, Node에 테스트 파일을 직접 전달한 JS 검증은 **85/85**였다. Pytest 건너뜀은 당시 시작된 회차가 시드에 없던 사례 및 Windows 전용 사례다. 상영 시작 이후 예약을 거부하는 SQL 회귀는 통과했다.

DB 인수인계는 신규 설치 기준이다. 기존 데이터 마이그레이션, PostgreSQL 14–17, 배포 환경의 실제 로그인 설정과 새 Flask 연동의 브라우저 동작은 검증 범위에 포함되지 않았다. 배포 승인 전 Member B는 좌석 조회를 새 DB 함수로 전환하고, 오류 및 재시도 계약과 최소 권한 역할을 적용한 뒤 위 통합 회귀 테스트를 통과해야 한다.
