\ir 00_context.sql
BEGIN;
DO $demo$
DECLARE
  customer bigint := (SELECT user_id FROM demo_customers WHERE customer_no=1);
  screening bigint := (SELECT showtime_id FROM demo_cases WHERE case_no=1);
  seat bigint := (SELECT seat_id FROM seats WHERE room_id=(SELECT room_id FROM demo_cases WHERE case_no=1)
                 ORDER BY seat_id LIMIT 1);
  booking bigint;
  next_booking bigint;
  actual text;
BEGIN
  booking := create_booking(customer, screening, ARRAY[seat]);
  IF NOT EXISTS (SELECT FROM bookings b JOIN booking_seats bs USING (booking_id)
                 WHERE b.booking_id=booking AND b.status='BOOKED' AND b.payment_status='UNPAID'
                   AND b.total_amount=bs.price_at_booking AND b.expires_at=b.booked_at+interval '10 minutes') THEN
    RAISE EXCEPTION 'Unexpected successful booking state';
  END IF;
  RAISE NOTICE 'PASS 성공 예매: BOOKED/UNPAID, 좌석 1건, 10분 기한';
  BEGIN
    PERFORM create_booking(customer, screening, ARRAY[seat]);
    RAISE EXCEPTION 'Duplicate allocation accepted';
  EXCEPTION WHEN SQLSTATE 'UC002' THEN
    RAISE NOTICE 'PASS 중복 좌석 거부: SQLSTATE %', SQLSTATE;
  END;

  actual := cancel_booking(booking, customer);
  IF actual <> 'CANCELLED' OR EXISTS (SELECT FROM booking_seats WHERE booking_id=booking)
     OR NOT EXISTS (SELECT FROM bookings WHERE booking_id=booking AND status='CANCELLED') THEN
    RAISE EXCEPTION 'Cancellation did not preserve history and release the seat';
  END IF;
  RAISE NOTICE 'PASS 취소: CANCELLED 이력 보존, 좌석 해제';

  next_booking := create_booking(customer, screening, ARRAY[seat]);
  RAISE NOTICE 'PASS 같은 좌석 재예매';
  -- 시연 전용: 10분을 기다리지 않고 시각만 과거로 이동한다. 전체 작업은 롤백한다.
  SET CONSTRAINTS ALL IMMEDIATE;
  ALTER TABLE bookings DISABLE TRIGGER trg_bookings_validate;
  UPDATE bookings SET booked_at=booked_at-interval '11 minutes',
                      expires_at=expires_at-interval '11 minutes' WHERE booking_id=next_booking;
  ALTER TABLE bookings ENABLE TRIGGER trg_bookings_validate;
  actual := pay_booking(next_booking, customer);
  IF actual <> 'EXPIRED' OR EXISTS (SELECT FROM booking_seats WHERE booking_id=next_booking)
     OR NOT EXISTS (SELECT FROM bookings WHERE booking_id=next_booking AND status='EXPIRED' AND payment_status='UNPAID') THEN
    RAISE EXCEPTION 'Late payment did not expire and release the seat';
  END IF;
  RAISE NOTICE 'PASS 기한 경과 결제: EXPIRED/UNPAID, 좌석 해제';
END
$demo$;
ROLLBACK;
