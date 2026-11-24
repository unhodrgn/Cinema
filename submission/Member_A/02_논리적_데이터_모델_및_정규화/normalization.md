# 정규화 분석

## 제1정규형

좌석 목록을 하나의 열에 저장하면 개별 좌석의 검색과 유일성 검사가 어렵다. 좌석 배정을 개별 행으로 나누어 저장 열은 각 행에서 단일 값을 갖는다. 좌석 ID 배열은 확정 함수의 입력 형식이다. 영화 제목과 상영관명은 해당 마스터에, 예매 소유자와 상태는 예매에 저장한다.

## 후보키와 함수 종속

| 릴레이션 | 최소 후보키 | 분석 |
|---|---|---|
| users | user_id, username | ID와 사용자명 각각이 계정 속성을 결정한다. |
| movies | movie_id | 제목의 유일성을 강제하지 않는다. |
| theater_rooms | room_id, room_name | 두 식별자가 각각 유일하다. |
| seats | seat_id, (room_id, seat_row, seat_number) | 위치 표시는 다른 상영관에서 재사용한다. |
| showtimes | showtime_id. 배제 제약으로 (room_id, starts_at) 및 (room_id, ends_at)도 실질적으로 유일 | 구간이 비어 있지 않아 같은 방의 두 회차가 시작이나 종료 시각을 공유하면 중첩된다. 두 조합은 별도 UNIQUE로 선언하지 않았다. 종료 시각은 현재 영화 길이와 시작 시각만으로 항상 결정되지 않는다. |
| bookings | booking_id | (booking_id, showtime_id)는 FK 대상으로 선언한 슈퍼키다. booked_at → expires_at가 성립한다. |
| booking_seats | booking_seat_id, (booking_id, seat_id), 물리 모델의 (showtime_id, seat_id) | booking_id → showtime_id, booking_id → price_at_booking, 상세 내 showtime_id → price_at_booking이 성립한다. |

## 제2·제3정규형과 BCNF

상세의 price_at_booking은 비주요 속성이며 예매 또는 회차로 결정된다. 합성 후보키의 일부에 대한 종속이므로 상세는 업무 규칙을 고려한 엄밀한 2NF와 3NF를 충족하지 않는다. booking_id → showtime_id에서 결정자는 슈퍼키가 아니지만 종속 속성은 물리 후보키의 구성원이다. 이 종속 자체는 3NF의 주요 속성 예외에 해당하며 BCNF에는 위배된다. bookings의 booked_at → expires_at는 비슈퍼키가 비주요 속성을 결정하므로 3NF와 BCNF에 위배된다. 물리 스키마 전체에 3NF 또는 BCNF를 부여하지 않는다.

## 통제된 중복

| 저장 값 | 저장 목적 | 무결성 통제 |
|---|---|---|
| booking_seats.showtime_id | 회차별 좌석 중복을 고유 인덱스로 차단 | 트리거 도출, (booking_id, showtime_id) 복합 FK, 회차·좌석 UNIQUE |
| booking_seats.price_at_booking | D6에 따른 확정 당시 좌석별 단가 | 삽입 트리거가 회차 가격과 일치 여부를 검증한다. 배정 행 및 이력이 있는 회차 가격의 변경을 차단한다. |
| bookings.expires_at | D3 기한을 보존하고 검색할 수 있게 함 | 삽입 트리거, 10분 등식 CHECK, 미결제 확정 행 부분 인덱스 |
| bookings.total_amount | 상세 삭제 이후에도 확정 총액을 보존 | 확정 함수 계산, 지연 트리거 합계 검사, 본 행 총액 변경 금지 |

총액은 다른 릴레이션의 상세에서 계산하는 집계값이다. 이 저장 자체가 같은 릴레이션 내 추가 함수 종속을 뜻하지는 않는다. ends_at은 입력이 NULL일 때만 기본값을 계산하며 이후 영화 길이가 바뀌어도 기존 종료 시각은 유지된다.
