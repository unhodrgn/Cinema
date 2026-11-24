# 테이블 기술서 (Table Description)

**기준:** `backend/migrations/0001_baseline.sql` (PostgreSQL 14+, 18.6에서 검증). 업무 규칙은 BR-DL-001(D1~D6)과 B01~B05를 따른다.
**논리 명칭 ↔ 물리 테이블:** USERS=`users`, MOVIES=`movies`, ROOMS=`theater_rooms`, SEATS=`seats`, SCREENINGS=`showtimes`, BOOKINGS=`bookings`, BOOKING_SEATS=`booking_seats`.

모든 기본키(`*_id`)는 `bigint GENERATED ALWAYS AS IDENTITY`이다.

## 1. users — 계정 (USERS)

| 컬럼 | 타입 | NULL | 기본값 | 제약 / 설명 |
|---|---|---|---|---|
| `user_id` | bigint | N | identity | PK |
| `username` | varchar(60) | N | | UNIQUE. 계정 ID (D5) |
| `password_hash` | text | N | | 일방향 해시만 저장 (D5) |
| `role` | varchar(10) | N | `'CUSTOMER'` | CHECK ∈ {`CUSTOMER`,`ADMIN`}. `GUEST` 없음 (D4) |
| `created_at` | timestamptz | N | `now()` | 기술 컬럼 |

## 2. movies — 영화 (MOVIES) — 승인된 6개 속성 (D5)

| 컬럼 | 타입 | NULL | 제약 / 설명 |
|---|---|---|---|
| `movie_id` | bigint | N | PK (기술 키) |
| `title` | varchar(200) | N | 영화 제목 |
| `genre` | varchar(100) | Y | 장르 — 자유 텍스트(승인된 목록 없음, ENUM 미사용) |
| `duration_minutes` | integer | N | 상영 시간(분). CHECK 1~300 (기술적 범위). 수정 가능, 이미 만들어진 상영 일정의 종료 시각을 바꾸지 않음 |
| `rating` | varchar(50) | Y | 관람 등급 — 자유 텍스트(승인된 어휘 없음) |
| `synopsis` | text | Y | 줄거리 |
| `release_date` | date | Y | 개봉일 |

## 3. theater_rooms — 상영관 (ROOMS)

| 컬럼 | 타입 | NULL | 제약 |
|---|---|---|---|
| `room_id` | bigint | N | PK |
| `room_name` | varchar(60) | N | UNIQUE |

## 4. seats — 좌석 (SEATS)

| 컬럼 | 타입 | NULL | 제약 |
|---|---|---|---|
| `seat_id` | bigint | N | PK |
| `room_id` | bigint | N | FK → `theater_rooms` (RESTRICT) |
| `seat_row` | char(1) | N | CHECK A~E |
| `seat_number` | smallint | N | CHECK 1~10 |
| | | | UNIQUE (`room_id`,`seat_row`,`seat_number`) |

좌석에는 예매 가능 여부 컬럼이 없다. 가용 여부는 상영 일정별로 `booking_seats`로 판정한다.

## 5. showtimes — 상영 일정 (SCREENINGS)

| 컬럼 | 타입 | NULL | 제약 / 설명 |
|---|---|---|---|
| `showtime_id` | bigint | N | PK |
| `movie_id` | bigint | N | FK → `movies` (RESTRICT) |
| `room_id` | bigint | N | FK → `theater_rooms` (RESTRICT) |
| `starts_at` | timestamptz | N | 상영 시작 시각 |
| `ends_at` | timestamptz | N | 상영 종료 시각. CHECK `ends_at > starts_at`. 생략 시 시작 + 영화 상영 시간으로 채워 **저장**함 |
| `ticket_price` | numeric(10,2) | N | 좌석당 관람 가격, CHECK ≥ 0. 상영 일정별 (D6) |

* **EXCLUDE `showtimes_no_room_overlap`** (`room_id` =, `tstzrange(starts_at, ends_at,'[)')` &&): 같은 상영관의 시간 겹침 금지(BR-04). 15분 정비 간격 등 추가 규칙 없음.
* **트리거 `trg_showtimes_protect_booked`:** 이 상영 일정을 참조하는 `bookings` 행이 하나라도 있으면(상태 무관) 영화·상영관·시작·종료·가격의 변경을 `UC001`로 거부 (D2).
* **트리거 `trg_showtimes_default_end_time`:** `ends_at` 미입력 시에만 기본값 계산.

## 6. bookings — 예매 (BOOKINGS)

| 컬럼 | 타입 | NULL | 기본값 | 제약 / 설명 |
|---|---|---|---|---|
| `booking_id` | bigint | N | identity | PK |
| `user_id` | bigint | N | | FK → `users` (RESTRICT) |
| `showtime_id` | bigint | N | | FK → `showtimes` (RESTRICT) |
| `status` | varchar(10) | N | `'BOOKED'` | CHECK ∈ {`BOOKED`,`CANCELLED`,`EXPIRED`} |
| `payment_status` | varchar(10) | N | `'UNPAID'` | CHECK ∈ {`UNPAID`,`PAID`} |
| `booked_at` | timestamptz | N | `now()` | 트리거가 INSERT 시 `clock_timestamp()`로 고정 |
| `expires_at` | timestamptz | N | | 트리거가 `booked_at + 10분`으로 설정. CHECK `expires_at = booked_at + interval '10 minutes'` |
| `total_amount` | numeric(10,2) | N | | CHECK ≥ 0. 좌석 가격 스냅샷 합계와 일치(D6), 이후 변경 불가, 취소·만료 후에도 유지 |
| `paid_at` | timestamptz | Y | | `payment_status='PAID'`일 때만 값 있음(CHECK, 트리거가 설정) |
| `cancelled_at` | timestamptz | Y | | `status='CANCELLED'`일 때만 값 있음(CHECK, 트리거가 설정) |

* CHECK `bookings_paid_never_expired`: `EXPIRED`이면서 `PAID`인 행은 없다 (D3).
* **트리거 `trg_bookings_validate`:** 상태 전이 규칙(`BOOKED+UNPAID→PAID`는 `expires_at` 이전만, `→EXPIRED`는 `expires_at` 이후만(상영 시작 후에도 가능), `→CANCELLED`는 상영 시작 전·결제 상태 유지, 종결 상태 불변, 식별·시각·금액 불변), 고객만 예매 가능, 상영 시작 후 예매 불가.
* **트리거 `trg_bookings_release_seats`:** `BOOKED`에서 `CANCELLED`/`EXPIRED`로 바뀌면 모든 `booking_seats` 행을 같은 트랜잭션에서 삭제 (D1, D3).
* **지연 제약 트리거 `trg_bookings_z_consistency`:** COMMIT 시 `BOOKED`는 좌석 1개 이상이고 `total_amount = SUM(price_at_booking)`; `CANCELLED`/`EXPIRED`는 좌석 행 0개.

## 7. booking_seats — 예매 좌석 (BOOKING_SEATS)

| 컬럼 | 타입 | NULL | 제약 / 설명 |
|---|---|---|---|
| `booking_seat_id` | bigint | N | PK |
| `booking_id` | bigint | N | FK → `bookings` (ON DELETE CASCADE) |
| `seat_id` | bigint | N | FK → `seats` (RESTRICT) |
| `price_at_booking` | numeric(10,2) | N | CHECK ≥ 0. 예매 시점 좌석 단가 스냅샷. 상영 일정 가격과 같아야 하며 생략(NULL)하면 그 가격으로 채워짐 |
| | | | UNIQUE (`booking_id`,`seat_id`) |

행은 `BOOKED` 예매에만 존재한다(취소·만료 시 모두 삭제).
* **트리거 `trg_booking_seats_validate`:** 상영 일정 행을 잠근 뒤 ① 예매가 `BOOKED`인지 ② 상영 시작 전인지 ③ 좌석이 존재하고 상영관이 일치하는지(BR-07) ④ 단가 스냅샷이 일치하는지 ⑤ 같은 상영 일정에서 `BOOKED` 예매에 이미 배정된 좌석이 아닌지(BR-08)를 검사한다. 수정(UPDATE)은 불가.
* **트리거 `trg_booking_seats_protect_delete`:** `BOOKED` 예매의 좌석 행은 직접 삭제 불가.

## 8. 인덱스

`idx_showtimes_movie_start`(movie_id, starts_at), `idx_showtimes_room_start`(room_id, starts_at), `idx_bookings_user`(user_id, booked_at DESC), `idx_bookings_showtime_status`(showtime_id, status), `idx_booking_seats_seat`(seat_id), `idx_bookings_pending_expiry`(expires_at) WHERE `status='BOOKED' AND payment_status='UNPAID'` (만료 처리 탐색용 기술 인덱스).

## 9. 함수 (응용 프로그램 호출용)

`create_booking(user_id, showtime_id, seat_ids[])`, `pay_booking(booking_id, user_id)`, `cancel_booking(booking_id, user_id)`, `expire_overdue_bookings()` — 사용 방법은 `postgresql_flask_integration_contract.md` 참조.
