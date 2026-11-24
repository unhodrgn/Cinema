# PostgreSQL–Flask 연동 계약

**대상:** DB 개선 커밋 65c9632a1becb1282ec020111c7c3c94ecff4a2b. DB 동작은 PostgreSQL 18.7에서 확인했다. 이 문서의 좌석 조회 전환, 재시도, 응답 매핑 및 화면 항목은 Member B가 구현할 계약이다. Flask 소스의 현재 상태와 완료 상태를 구분한다.

## 1. 데이터 명칭과 접근 규칙

| 업무 개체 | 물리 테이블 |
|---|---|
| 사용자 계정 · 영화 | users · movies |
| 상영관 · 좌석 · 상영 일정 | theater_rooms · seats · showtimes |
| 예매 · 예매 좌석 | bookings · booking_seats |

회원가입은 계정 ID와 비밀번호만 받는다. Flask가 단방향 해시를 생성하고 users의 username, password_hash만 삽입한다. 데이터베이스 기본 역할은 CUSTOMER다. 브라우징, 좌석 조회·임시 선택은 비로그인 허용이다. 확정·결제·취소·고객 이력은 인증 고객의 범위에서 처리한다. 영화·일정 관리 및 전체 예매 목록은 ADMIN 전용이다. DB 서비스 계정은 신뢰된 서버 프로세스에서만 사용하며, 고객 ID는 요청 본문이 아닌 인증 세션에서 가져온다.

상영 일정·예매 시각은 timestamptz다. API는 UTC 오프셋을 포함한 ISO 8601, 개봉일은 ISO 날짜, 금액은 십진 문자열을 사용한다. 화면 및 오프셋 없는 입력의 업무 시간대는 Asia/Seoul이다. 기한 및 상영 시작 판정은 DB의 실제 시각을 사용한다. 상세 자료형은 [테이블 기술서](../06_테이블_기술서/table_description.md)에 있다.

## 2. 호출과 트랜잭션

| 업무 | 호출 형태 | 정상 결과와 주의점 |
|---|---|---|
| 좌석 조회 | SELECT * FROM public.screening_seat_availability(%s) | seat_id, seat_row, seat_number, is_available. 회차별 만료를 처리하므로 쓰기 가능한 트랜잭션이 필요하다. |
| 예매 확정 | SELECT public.create_booking(%s, %s, %s::bigint[]) | 고객 ID, 회차 ID, 좌석 배열로 호출. 가격과 총액은 DB가 계산하고 확정 ID를 반환한다. |
| 결제 | SELECT public.pay_booking(%s, %s) | 예매 ID와 고객 ID. PAID 또는 이번 요청에서 만료시킨 EXPIRED. |
| 취소 | SELECT public.cancel_booking(%s, %s) | 예매 ID와 고객 ID. CANCELLED 또는 이번 요청에서 만료시킨 EXPIRED. |
| 이력용 전체 정리 | SELECT public.expire_overdue_bookings() | 처리한 건수. 잠긴 행을 건너뛴다. 좌석 가용성을 판정하는 호출로 사용하지 않는다. |

모든 호출은 매개변수를 바인딩한다. 지연 제약은 기본 모드를 사용한다. 함수 반환 뒤 트랜잭션을 커밋한 다음 응답한다. 새로 발생한 EXPIRED는 커밋 가능한 업무 결과이며, 이미 종결된 예매에 대한 재호출은 UC006일 수 있다. 커밋 오류까지 처리 범위에 포함한다.

조회·확정의 잠금 순서는 회차 → 예매 ID 오름차순 → 좌석 상세다. 결제·취소는 해당 예매 → 좌석 상세 순이며 회차 배타 잠금을 요청하지 않는다. 전체 정리는 예매 ID 순으로 잠금을 시도하고 잠긴 행을 건너뛴다. 한 트랜잭션에서 업무 쓰기 동작 하나를 실행한다. 전체 정리를 먼저 실행한 트랜잭션에서 회차 잠금을 요청하지 않는다. 가용성 판정은 해당 처리 시점 기준이며 후속 선택에 대한 점유 보장은 없다.

잠금 획득 시도당 5초는 좌석 조회·확정·결제·취소 DB 함수에 적용된다. HTTP 전체 제한 시간 및 재시도 예산은 별도로 관리한다. 40001이 나오면 롤백 후 새 스냅샷으로 전체 트랜잭션을 제한 횟수만큼 재시도한다. 55P03이면 롤백하고 재시도 가능한 응답을 반환한다. 이미 확정적으로 커밋된 요청이나 커밋 여부가 불명인 연결 오류는 자동으로 재전송하지 않는다.

## 3. 오류 계약

psycopg2의 pgcode로 판정하고 DB 원문을 응답에 노출하지 않는다.

| SQLSTATE | 의미 | HTTP 및 처리 |
|---|---|---|
| UC001 | 예매 이력이 있는 일정 변경 | 409 screening_has_bookings |
| UC002 | 같은 회차에서 선택 좌석이 이미 배정됨 | 409 seat_unavailable, 다시 조회하고 재선택 |
| UC003 | 다른 상영관의 좌석 | 400 invalid_seat |
| UC004 | 상영 시작 이후 확정 | 409 screening_started |
| UC005 | 상영 시작 이후 취소 | 409 cancellation_closed |
| UC006 | 종결 상태·이미 결제 등 허용되지 않는 상태 또는 직접 SQL의 기한 위반 | 409 invalid_booking_state |
| UC007 | 직접 이력 삭제·절단, 불변 열 변경, 허용되지 않는 전이 | 내부 오류 |
| UC008 | 고객 계정이 아닌 예매 주체 | 403 customer_only |
| UC009 | 단가 스냅샷 또는 합계 불일치 | 내부 오류 |
| UC010 | 빈 좌석 배열, 배열 내 중복·NULL, 확정 상세 누락 | 400 no_seat_selected (정상 API가 빈 배열 등은 사전에 검증) |
| UC011 | 없는 일정 또는 해당 고객의 예매를 찾을 수 없음 | 404 not_found |
| 23505 / 23503 / 23514 | 일반 유일성 / 참조 / CHECK 위반 | 현재 계약상 각각 409 duplicate_value / 400 unknown_reference / 400 invalid_value |
| 23P01 / 23001 / 22003 | 일정 중첩 / 참조 대상 삭제 제한 / 숫자 범위 오류 | 중첩은 409 screening_overlap. 그 외 원인과 입력 경로를 확인한다. |
| 40001 / 55P03 | 직렬화 실패 / 잠금 시간 초과 | 40001은 제한된 전체 재시도. 소진 또는 55P03이면 503 booking_retry. 이 매핑은 연동 작업이다. |

## 4. 조회와 관리자 작업

이력은 소유자 범위와 관리자 범위를 구분한다. 예매 상태와 좌석을 한 문장 또는 같은 스냅샷에서 읽는다. BOOKED의 상세에는 각 좌석과 price_at_booking을 포함한다. BOOKED/UNPAID에서 결제 기한을 표시한다. CANCELLED와 EXPIRED는 삭제된 좌석 상세를 반환하거나 화면에 복원하지 않는다. 취소·만료 이력의 총액은 남는다.

관리자는 영화·일정을 추가하거나 수정한다. 일정 종료 시각은 NULL로 제출하면 DB가 영화 길이로 계산해 저장한다. 명시한 종료 시각은 검증 후 저장한다. 영화 길이의 후속 변경은 기존 일정 종료 시각을 바꾸지 않는다. 예매가 있는 일정은 상태를 불문하고 업무 속성을 변경할 수 없다.

## 5. 전환 작업과 권한

| 파일 | 함수 및 작업 |
|---|---|
| app/screenings.py | get_screening_seats()의 기존 전체 정리 + 별도 만료 필터를 회차별 함수 호출로 교체한다. 공개 접근과 screening/seats 응답 구조는 유지한다. |
| app/database.py, app/errors.py | transaction() 바깥에서 재시도하고 describe_database_error()의 신규 오류 매핑을 적용한다. |
| app/booking.py, app/admin.py | create_booking(), pay_booking(), cancel_booking()의 커밋 경로를 확인하고 list_bookings(), admin_list_bookings()의 일관된 조회를 적용한다. |
| frontend/js/pages/seats.js, booking.js, bookings.js | 충돌과 재시도 안내를 구분하며, EXPIRED와 좌석별 단가를 표시한다. |

현재 저장소는 psycopg2-binary를 사용한다. 서비스 역할은 [권한 스크립트](../07_PostgreSQL_구현/database/grant_application_role.sql)로 구성하고 로그인은 따로 관리한다. 다섯 공개 업무 함수는 전용 객체 소유자의 권한으로 실행되며, 직접 예매 쓰기 권한은 앱 역할에 부여하지 않는다. 신규 DB 구성은 [설치 안내서](postgresql_setup_guide.md), 통합 회귀와 배포 조건은 [Member B 인수인계](member_b_integration_handover.md)에서 확인한다.
