# 영화관 예매 시스템 — 15분 팀 발표 원고

**DB 기준:** `database-remediation`, `121854a0e006d824dd4aba7274deec7524da9694`. 이 원고는 팀 발표의 기획·설계·구현·검증 흐름을 연결한다. PostgreSQL 신규 설치와 DB 검증은 완료되었다. 변경된 좌석 조회 및 재시도 계약의 Flask·브라우저 연동은 Member B의 확인 대상이다.

## 발표 구성

| 시간 | 주제 | 화면 및 담당 제안 |
|---|---|---|
| 00:00–01:30 | 기획·업무 요구사항 | B01–B05와 D1–D6. 좌석 임시 선택, 확정, 10분 결제 기한, 이력 보존의 흐름. 팀 공동 |
| 01:30–03:00 | 개발 환경과 3계층 | 브라우저와 정적 프런트엔드 → Flask HTTP API → PostgreSQL. Member B는 실제 연동 범위를 표시 |
| 03:00–06:00 | 일곱 테이블과 세 단계 모델 | 개념, 논리, 물리 ERD 순서. Member A |
| 06:00–08:45 | 무결성과 동시성 구현 | 후보키와 통제된 중복, 회차별 유일성, 잠금 순서, 상태 전이, DB 역할. Member A |
| 08:45–11:45 | 실시간 SQL | 준비된 폐기용 DB에서 확정·예외·경합·권한 확인. Member A |
| 11:45–14:00 | 실제 검증 및 남은 연동 | 기록된 DB 결과, 아직 필요한 API·화면 검증. A/B |
| 14:00–15:00 | AI 사용 경험 및 한계 | 제안과 실제 검증의 차이, 최종 검토 및 책임. 팀 공동 |

## 1. 기획과 개발 환경

고객은 로그인 없이 영화·상영 일정·좌석을 조회하고 좌석을 임시 선택한다. 로그인한 고객의 확정에만 좌석을 할당하고, 모의 결제에 10분 기한을 부여한다. 취소·만료 시 좌석 상세를 없애고 총액·상태를 포함한 예매 이력을 보존한다. 동일 상영관에는 겹치는 상영 일정을 등록할 수 없다.

검증 환경은 macOS arm64, PostgreSQL 18.7, 신규 UTF-8 DB, Asia/Seoul 업무 시간대, Python·psycopg2다. `btree_gist`를 사용한다. 데모 서버는 임시 Unix 소켓만 사용한다.

| 계층 | 구성 | 책임 |
|---|---|---|
| 표현 | 브라우저의 HTML/CSS/JavaScript, 독립 정적 파일 서버 | 영화·시간·좌석 표시, 입력, HTTP API 요청 |
| 응용 | Flask와 psycopg2 | 인증, 소유권·관리자 권한, JSON 변환, 트랜잭션 및 오류 응답 |
| 데이터 | PostgreSQL | 참조 및 유일성, 일정 중첩 배제, 가격·상태, 동시 처리와 이력 |

업무 기준은 [B01](../docs/business/project_overview.md)과 [D1–D6](../docs/business/business_rules_decision_log.md), 구현 진입점은 [frontend/server.py](../frontend/server.py), [Flask 팩터리](../app/__init__.py), [DB 연결 및 트랜잭션](../app/database.py)이다.

## 2. 개념·논리·물리 설계

- **개념:** 사용자 계정·영화·상영관·좌석·상영 일정·예매·예매 좌석의 관계를 표시한다. 상영관은 업무상 여러 좌석을 갖는다. 예매 좌석은 예매와 물리 좌석을 연결한다. [개념 ERD](../docs/database/erd/conceptual.svg)
- **논리:** 일곱 릴레이션의 속성, PK와 대체 후보키, 참조를 정의한다. 예매와 좌석의 다대다 관계를 예매 좌석으로 분해한다. [논리 ERD](../docs/database/erd/logical.svg)
- **물리:** users, movies, theater_rooms, seats, showtimes, bookings, booking_seats의 PostgreSQL 자료형, NULL, FK, UNIQUE 및 세부 구현을 적용한다. FK는 자식의 정확히 한 부모를 보장하며 부모의 최소 자식 수를 보장하지 않는다. [물리 ERD](../docs/database/erd/physical.svg) · [DDL](../database/schema.sql)

1NF는 좌석을 목록 열 대신 개별 행으로 저장하여 구현한다. 단가는 예매 또는 회차에 의해 결정되므로 상세에 저장된 단가는 합성 후보키의 일부에 종속한다. 물리 스키마의 `booking_seats.showtime_id`는 예매에서 도출하며 복합 FK로 맞추고 회차별 유일성에 사용한다. `price_at_booking`은 확정 단가, `expires_at`은 확정 시각과 10분 등식, `total_amount`는 상세 삭제 후에도 유지할 집계다. 물리 스키마 전체에 3NF나 BCNF를 부여하지 않는다. [정규화 분석](../docs/database/normalization.md)

## 3. 구현 원리와 실시간 검증

- **무결성:** 제약은 참조, 상태 값과 시각, 유한한 비음수 금액을 검증한다. GiST 배제 제약은 동일 상영관에서 겹치는 `[시작, 종료)` 구간을 막는다. 지연 트리거가 확정 예매의 좌석 수와 합계를 검증한다.
- **중복 예매:** `UNIQUE(showtime_id, seat_id)`가 여러 트랜잭션에서 동일 배정을 금지한다. READ COMMITTED에서는 충돌 시 UC002를 관찰했다. REPEATABLE READ와 SERIALIZABLE의 오래된 스냅샷은 40001로 종료될 수 있다. 새 트랜잭션 재시도에서 좌석이 이미 점유되면 UC002를 처리한다.
- **결제 만료:** 결제·취소는 예매 잠금 획득 후 DB 시간을 확인한다. 기한 이상이면 미결제 상태를 EXPIRED로 바꾸고 모든 좌석을 해제한다. 회차별 좌석 조회·확정은 같은 처리 흐름을 사용한다. 잠금 대기 초과 55P03은 좌석 충돌과 구분한다.
- **보안:** 앱 로그인과 DB 객체 소유자를 분리한다. 앱 역할은 필요한 조회, 지정된 열 쓰기, 다섯 업무 함수만 허용받는다. SECURITY DEFINER 함수의 검색 경로는 고정하며 PUBLIC 기본 실행 권한을 철회한다. DB의 서비스 역할과 앱의 CUSTOMER/ADMIN 계정 역할은 구분한다. [권한 SQL](../database/grant_application_role.sql)
- **실시간 시연:** [데모 순서와 명령](../database/demo/README.md)에 따라 확정·중복·취소·만료 → 잘못된 좌석·겹친 회차 → 두 터미널 경합 → 앱 역할 순으로 실행한다. [실제 시연 로그](../database/demo/verification.log)를 예비 자료로 준비한다.

## 4. 결과, 한계와 책임 분담

| 항목 | 검증 사실 |
|---|---|
| DB 검증 | PostgreSQL 18.7에서 무결성 199/199, 동시성 58/58, 대조 31 MATCH·0 MISMATCH, 앱 역할 검사 통과. [원문 증빙](../docs/database/evidence/README.md) |
| 두 세션 시연 | B가 A의 락을 기다리는 상태를 확인했다. A 커밋 후 B는 UC002를 반환했고 최종 부모 1건, 좌석 배정 1건을 확인했다. |
| 현행 앱 검증 | 앞선 개선 시점에는 pytest 1197 통과·2 건너뜀과 JavaScript 85/85가 기록되었다. 그 실행은 신규 Flask 연동을 검증한 결과가 아니다. |
| 기술 범위 | 신규 UTF-8 설치 기준이다. 기존 데이터 마이그레이션, PostgreSQL 14–17 및 실제 배포 계정·브라우저 연동은 미검증이다. |
| Member B | 좌석 조회 함수 사용, 40001 재시도, 55P03 오류 매핑, EXPIRED와 좌석별 단가 표시, 앱 계정 및 UI 포함 회귀. [연동 계약](../docs/database/postgresql_flask_integration_contract.md) |

## 5. 팀 개발에서 AI를 사용한 경험

확인 가능한 사례로 AI는 기존 DDL과 승인 요구사항의 대조, 동시성 실패를 재현할 시나리오 제안, 한국어 문서 및 시연 스크립트 작성에 사용되었다. 팀원 개인별 사용 범위는 추정하지 않는다. 검토 과정에서 기존 테스트 통과만으로 세 격리 수준의 안전성을 입증하기 어렵다는 점을 발견했다. 따라서 두 실제 DB 세션의 잠금 대기, SQLSTATE와 커밋 후 상태를 확인하였다. DB 개선에는 Git 변경 범위 확인, 폐기용 DB 실행과 Member A 승인 절차를 적용하였다. 새 시연 자료는 실행 검증을 마쳤으며 이 제출 패키지의 최종 제출 승인은 검토 후 결정한다. 인터페이스 변경은 담당자가 승인한다.
