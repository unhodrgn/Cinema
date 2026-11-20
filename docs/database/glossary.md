# 용어사전

| 용어 | 영문 / 물리 이름 | 정의 |
|---|---|---|
| 사용자 계정 | User / `users` | 계정 ID와 비밀번호 해시, 역할을 가진 로그인 계정. 역할은 `CUSTOMER`, `ADMIN`뿐이다. |
| 비회원 방문자 | Unauthenticated visitor | 로그인하지 않은 접근을 뜻한다. 별도의 계정 역할이 아니며 데이터베이스에 행이 없다 (D4). |
| 계정 ID | Account ID / `users.username` | 유일한 로그인 식별자 (D5). |
| 영화 | Movie / `movies` | 제목, 장르, 상영 시간, 관람 등급, 줄거리, 개봉일의 6개 승인 속성을 가진 영화 정보 (D5). |
| 상영관 | Theater room (ROOMS) / `theater_rooms` | 영화를 상영하는 공간. 시드에는 5개가 있다. |
| 좌석 | Seat / `seats` | 상영관에 고정된 행(A~E)과 번호(1~10)의 위치. 시드에서 상영관당 50석, 총 250석. |
| 상영 일정 | Screening (SCREENINGS) / `showtimes` | 영화·상영관·시작 시각·종료 시각·좌석당 가격이 정해진 하나의 상영. |
| 예매 | Booking / `bookings` | 고객이 한 상영 일정에 대해 확정한 거래. 상태와 결제 상태, 결제 기한, 총 금액을 가진다. |
| 예매 좌석 | Booking seat / `booking_seats` | 상태가 `BOOKED`인 예매에 배정된 개별 좌석과 단가 스냅샷. 취소·만료 시 삭제된다. |
| `BOOKED` | Booking status | 예매가 확정된 저장 상태. 결제 완료 또는 기한 이전인 경우 유효하다. 기한이 지난 미결제 행은 만료 작업이 커밋되기 전까지 이 상태로 남을 수 있다. |
| `CANCELLED` | Booking status | 고객이 상영 시작 전에 예매 전체를 취소한 상태. 좌석 상세는 삭제, 예매 본 정보는 보존 (D1). |
| `EXPIRED` | Booking status | 결제 기한 내에 결제하지 않아 만료된 상태. 좌석 상세는 삭제, 예매 본 정보는 보존, 결제 상태는 `UNPAID` 유지 (D3). |
| `UNPAID` / `PAID` | Payment status | 모의 결제 미완료 / 완료. 예매 상태와 별도로 저장한다. 상태 조합에는 제약이 적용된다. 환불 상태는 없다. |
| 결제 기한 | `expires_at` | 예매 확정 시각 + 10분. 현재 시각 ≥ `expires_at`이고 미결제이면 만료 대상이다 (D3). |
| 만료 처리 | Expiration / `expire_overdue_bookings()` | 기한이 지난 `BOOKED`+`UNPAID` 예매를 `EXPIRED`로 바꾸고 모든 좌석 행을 삭제하는 원자적·멱등 처리. 좌석 조회·확정은 회차별 잠금을 사용한다. 이력용 전체 정리는 잠긴 예매를 건너뛴다. 요청 시점에 실행하며 자동 스케줄러는 없다. |
| 가격 스냅샷 | `booking_seats.price_at_booking` | 예매 시점의 좌석 단가. 이후 상영 일정 가격은 예매가 생기면 변경할 수 없다 (D2, D6). |
| 총 예매 금액 | `bookings.total_amount` | 상영 일정 좌석당 가격 × 좌석 수. 스냅샷 합계와 같으며 취소·만료 후에도 남는다 (D6). |
| 상영 일정 보호 | Screening protection | 예매 기록이 하나라도 있으면(상태 무관) 영화·상영관·시작·종료·가격을 바꿀 수 없는 규칙 (D2). |
| 유효한 예매 | Active booking | `BOOKED`이면서 `PAID`이거나 `UNPAID`이고 `expires_at` 이전인 예매. 좌석 점유 판단 기준. |
| 기본키 / 외래키 | PK / FK | 행을 유일하게 식별하는 키 / 다른 테이블 행을 참조하는 제약. |
| 트리거 | Trigger | INSERT, UPDATE, DELETE 또는 TRUNCATE 시 서버에서 실행되는 검증·후처리 로직. |
| 지연 제약 트리거 | Deferred constraint trigger | 기본 설정에서 COMMIT 시점에 검사되는 트리거. 예매와 좌석을 한 트랜잭션에서 나누어 입력할 수 있게 한다. |
| 배제 제약 | EXCLUDE constraint | 같은 상영관에서 시간 구간이 겹치는 행을 선언적으로 금지하는 제약 (`btree_gist` 필요). |
| 트랜잭션 | Transaction | COMMIT 또는 ROLLBACK 단위로 묶인 작업. |
| 동시성 제어 | Concurrency control | 행 잠금과 회차·좌석의 유일성으로 동시 변경 후에도 무결성을 보장하는 처리. |
| 복합 외래 키 | Composite FK | 예매 좌석의 예매 ID와 회차 ID를 함께 부모의 동일한 조합에 연결한다. |
| 잠금 획득 시간 초과 | Lock timeout / `55P03` | 상호작용 함수에서 한 잠금 획득 시도가 5초를 넘겨 실패한 경우다. |
| 직렬화 실패 | Serialization failure / `40001` | 현재 스냅샷으로 갱신을 계속할 수 없어 트랜잭션 전체를 새로 시작해야 하는 경우다. |
| 최소 권한 역할 | Application role | 신뢰된 Flask 서버가 사용하는 DB 서비스 역할이다. 고객·관리자 구분은 애플리케이션 계정의 역할이다. |
| 정의자 권한 함수 | SECURITY DEFINER | 함수 소유자의 권한으로 실행한다. 제한된 앱 역할이 업무 함수로 예매 상태를 바꾸도록 허용한다. |
