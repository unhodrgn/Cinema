# 도메인 정의서 (Domain Definition)

**기준:** `backend/migrations/0001_baseline.sql`. 승인되지 않은 값 목록(장르, 관람 등급)은 정의하지 않는다 (BR-DL-001 §6).

| 도메인 | 적용 컬럼 | PostgreSQL 타입 | 허용 범위 / 형식 | 검증 수단 |
|---|---|---|---|---|
| 식별자 | 모든 PK `*_id` | bigint | identity 자동 생성 | `GENERATED ALWAYS AS IDENTITY`, PK |
| 참조 식별자 | `room_id`, `movie_id`, `user_id`, `showtime_id`, `booking_id`, `seat_id` | bigint | 부모 행 존재 | FK |
| 계정 ID | `users.username` | varchar(60) | 유일. 형식·최소 길이는 승인되지 않음 | UNIQUE, NOT NULL |
| 비밀번호 해시 | `users.password_hash` | text | 일방향 해시 문자열(평문 금지). 해시 생성은 Flask 책임 | NOT NULL |
| 권한 | `users.role` | varchar(10) | `CUSTOMER`, `ADMIN` (기본 `CUSTOMER`). `GUEST` 없음 | CHECK |
| 영화 제목 | `movies.title` | varchar(200) | 문자열 | NOT NULL |
| 장르 | `movies.genre` | varchar(100) | **자유 텍스트**(목록 없음) | 없음 (NULL 허용) |
| 상영 시간 | `movies.duration_minutes` | integer | 1~300 (분) | CHECK |
| 관람 등급 | `movies.rating` | varchar(50) | **자유 텍스트**(어휘 없음) | 없음 (NULL 허용) |
| 줄거리 | `movies.synopsis` | text | 문자열 | NULL 허용 |
| 개봉일 | `movies.release_date` | date | 날짜 | 타입 (NULL 허용) |
| 상영관명 | `theater_rooms.room_name` | varchar(60) | 유일 | UNIQUE, NOT NULL |
| 좌석 행 | `seats.seat_row` | char(1) | `A`~`E` | CHECK |
| 좌석 번호 | `seats.seat_number` | smallint | 1~10 | CHECK |
| 상영 시각 | `showtimes.starts_at`, `showtimes.ends_at` | timestamptz | `ends_at > starts_at`. 같은 상영관에서 `[시작, 종료)` 구간이 겹치지 않음 | CHECK, EXCLUDE |
| 금액 | `showtimes.ticket_price`, `booking_seats.price_at_booking`, `bookings.total_amount` | numeric(10,2) | 0 이상 | CHECK |
| 예매 상태 | `bookings.status` | varchar(10) | `BOOKED`, `CANCELLED`, `EXPIRED` (기본 `BOOKED`) | CHECK + 전이 트리거 |
| 결제 상태 | `bookings.payment_status` | varchar(10) | `UNPAID`, `PAID` (기본 `UNPAID`) | CHECK + 전이 트리거 |
| 예매 시각 | `bookings.booked_at` | timestamptz | 예매 확정 성공 시각 | 트리거 |
| 결제 기한 | `bookings.expires_at` | timestamptz | `booked_at + 10분` | CHECK, 트리거 |
| 결제 일시 | `bookings.paid_at` | timestamptz | `PAID`일 때만 값 있음 | CHECK, 트리거 |
| 취소 일시 | `bookings.cancelled_at` | timestamptz | `CANCELLED`일 때만 값 있음 | CHECK, 트리거 |

## 시간 표기 규칙

모든 시각은 `timestamptz`로 저장한다. 업무 기준 시간대는 `Asia/Seoul`이며, 변환은 응용 프로그램 경계에서 한다. 기한 판정(`expires_at`, 상영 시작 등)은 항상 데이터베이스의 `clock_timestamp()`로 하며 Flask 서버 시계를 사용하지 않는다.

## 데이터베이스 오류 코드 도메인

`UC001`~`UC011`(사용자 정의, Cinema)과 표준 `23505`, `23503`, `23514`, `23P01`, `23001`. 의미는 `schema.sql` 머리말과 연동 계약 §6에 정의되어 있다.

## 응용 프로그램이 검증할 항목

로그인·권한·소유권 확인, 회원가입 시 `role` 미전달, 비밀번호 해시 생성, 입력 형식 검증(계정 ID·비밀번호 형식은 미승인), 만료 처리 호출 시점(요청 시점 처리).
