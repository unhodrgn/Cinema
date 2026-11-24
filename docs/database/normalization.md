# 정규화 검토 (1NF → 3NF)

**대상:** `backend/migrations/0001_baseline.sql`의 7개 릴레이션. 이전 초안(`CinemaDB_FINAL_PostgreSQL_Handover/docs/04_Normalization_Review_KO.md`)은 승인된 결정(D1~D6) 이전 모델을 기준으로 하므로 이 문서가 대체한다.

## 1. 비정규형 예시

`booking_id=B1, movie=영화A, room=1관, seats='A1,A2', price=12000`처럼 한 행에 여러 좌석을 넣으면 반복 그룹과 영화·상영관 정보의 중복이 생긴다.

## 2. 1NF

모든 속성은 원자값이다. 좌석은 한 행에 하나씩 `booking_seats`에 저장한다(`A1,A2` 같은 목록 컬럼 없음). 반복 그룹은 `booking_seats`로 분리했다.

## 3. 2NF

복합 후보키가 있는 릴레이션은 `booking_seats(booking_id, seat_id)`와 `seats(room_id, seat_row, seat_number)`이다(대리키 `booking_seat_id`, `seat_id`도 있음). `booking_seats`의 비키 속성 `price_at_booking`은 좌석 한 건의 가격 사실이므로 후보키 전체에 종속한다. 고객·상영 일정·상태는 `booking_id`에만 종속하므로 `bookings`에 두어 부분 종속을 제거했다.

## 4. 3NF — 함수 종속

| 릴레이션 | 결정자 → 종속 속성 | 이행 종속 여부 |
|---|---|---|
| users | user_id → username, password_hash, role, created_at; username → user_id(후보키) | 없음 |
| movies | movie_id → title, genre, duration_minutes, rating, synopsis, release_date | 없음 |
| theater_rooms | room_id → room_name; room_name → room_id | 없음 |
| seats | seat_id → room_id, seat_row, seat_number; (room_id, seat_row, seat_number) → seat_id | 없음 |
| showtimes | showtime_id → movie_id, room_id, starts_at, ends_at, ticket_price | 영화 제목·상영관명은 `movies`, `theater_rooms`에만 저장 |
| bookings | booking_id → user_id, showtime_id, status, payment_status, booked_at, expires_at, total_amount, paid_at, cancelled_at | 고객 정보·영화·상영관·상영 시각은 FK로만 참조 |
| booking_seats | booking_seat_id → booking_id, seat_id, price_at_booking; (booking_id, seat_id) → booking_seat_id | 상영 일정·상영관을 중복 저장하지 않음 (`booking_id → showtime_id → room_id`) |

`bookings.user_id`, `showtime_id`는 각각 `users`, `showtimes`의 키만 보관하므로 비키 속성 간 이행 종속이 없다. 따라서 모든 릴레이션이 3NF(실제로 BCNF)를 만족한다.

## 5. 승인된 요구사항에 따른 의도적 저장(통제된 중복)

아래 값은 다른 속성에서 계산할 수 있으나, 승인된 규칙이 **이력으로 보존**하거나 **고정**하도록 요구하므로 저장한다. 불일치는 제약·트리거가 막는다.

| 저장 값 | 계산 가능한 원천 | 저장하는 이유 | 일관성 보장 |
|---|---|---|---|
| `bookings.total_amount` | `Σ booking_seats.price_at_booking` | 취소·만료 시 좌석 행이 삭제되어도 총액이 남아야 함 (D1, D3, D6) | COMMIT 시 `BOOKED`의 총액 = 스냅샷 합(지연 제약 트리거), 변경 불가 |
| `booking_seats.price_at_booking` | `showtimes.ticket_price` | 예매 시점 단가 스냅샷 (D6) | 트리거가 상영 일정 가격과 일치 요구 (예매가 있으면 가격은 D2로 고정) |
| `bookings.expires_at` | `booked_at + 10분` | 결제 기한을 저장해 판정·이력 (D3) | CHECK `expires_at = booked_at + 10분`, 트리거가 설정 |
| `showtimes.ends_at` | `starts_at + movies.duration_minutes` | 종료 시각이 승인 속성이며, 영화 상영 시간이 나중에 바뀌어도 기존 일정이 바뀌면 안 됨 (D2, DB-02) | CHECK `ends_at > starts_at`; 생략 시에만 기본 계산; 명시값 존중 |

`paid_at`, `cancelled_at`은 상태와 일치해야 하는 기술적 시각 컬럼이며 CHECK로 상태와 연동된다.

## 6. 한계

이 문서는 함수 종속을 설계 근거로 서술한 것이며 형식적 증명(암스트롱 공리 전개)을 포함하지 않는다. 교수 요구에 따라 후보키·함수 종속 표를 확장할 수 있다.
