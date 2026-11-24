-- DB-03: materialize the screening key on active allocations for an immediate unique index.
-- DB-01: widen booking totals while leaving the screening and seat unit prices unchanged.
BEGIN;
SET LOCAL lock_timeout = '5s';
LOCK TABLE bookings, booking_seats IN ACCESS EXCLUSIVE MODE;

-- Fail atomically if an earlier snapshot allowed conflicting allocations. Resolving
-- conflicting reservations is an operator decision; the migration never edits history.
DO $$
BEGIN
 IF EXISTS (
   SELECT 1
   FROM booking_seats bs JOIN bookings b USING (booking_id)
   GROUP BY b.showtime_id, bs.seat_id HAVING count(*) > 1
 ) THEN
   RAISE EXCEPTION 'Historical duplicate seat allocations exist; reconcile before applying migration 0003'
     USING ERRCODE = '23505';
 END IF;
END $$;

ALTER TABLE bookings
 ALTER COLUMN total_amount TYPE numeric(12,2),
 ADD CONSTRAINT bookings_id_showtime_key UNIQUE (booking_id, showtime_id);

ALTER TABLE booking_seats ADD COLUMN showtime_id bigint;
-- Only the immutability trigger must be suspended for this internal backfill.
-- Transaction and ACCESS EXCLUSIVE locks prevent any other writer observing it.
ALTER TABLE booking_seats DISABLE TRIGGER trg_booking_seats_validate;
UPDATE booking_seats bs SET showtime_id = b.showtime_id
FROM bookings b WHERE b.booking_id = bs.booking_id;
ALTER TABLE booking_seats ENABLE TRIGGER trg_booking_seats_validate;

ALTER TABLE booking_seats
 ALTER COLUMN showtime_id SET NOT NULL,
 DROP CONSTRAINT booking_seats_booking_id_fkey,
 ADD CONSTRAINT booking_seats_booking_showtime_fkey
   FOREIGN KEY (booking_id, showtime_id) REFERENCES bookings(booking_id, showtime_id) ON DELETE CASCADE,
 ADD CONSTRAINT booking_seats_showtime_seat_key UNIQUE (showtime_id, seat_id);

-- The first booking changes whether a showtime is editable. Publish that change
-- as a row version even though its attributes stay the same, so a scheduler with
-- an older snapshot cannot update the row based on stale absence of bookings.
CREATE FUNCTION bookings_version_first_showtime_reference() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 UPDATE showtimes s SET ticket_price = s.ticket_price
 WHERE s.showtime_id = NEW.showtime_id
   AND NOT EXISTS (SELECT 1 FROM bookings b WHERE b.showtime_id = s.showtime_id);
 RETURN NEW;
END $$;

-- Run after the existing BEFORE trigger has validated the new booking.
CREATE TRIGGER trg_bookings_z_version_showtime BEFORE INSERT ON bookings
FOR EACH ROW EXECUTE FUNCTION bookings_version_first_showtime_reference();

CREATE OR REPLACE FUNCTION booking_seats_validate() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
 v_showtime bigint; v_status text; v_room bigint; v_start timestamptz;
 v_price numeric(10,2); v_seat_room bigint;
BEGIN
 IF TG_OP = 'UPDATE' THEN
   RAISE EXCEPTION 'Seat allocations are immutable' USING ERRCODE = 'UC007';
 END IF;
 -- Share-lock the parent so a concurrent state change cannot leave terminal rows allocated.
 SELECT showtime_id, status INTO v_showtime, v_status
   FROM bookings WHERE booking_id = NEW.booking_id FOR SHARE;
 IF v_status IS DISTINCT FROM 'BOOKED' THEN
   RAISE EXCEPTION 'Booking is not BOOKED' USING ERRCODE = 'UC007';
 END IF;
 IF NEW.showtime_id IS NOT NULL AND NEW.showtime_id <> v_showtime THEN
   RAISE EXCEPTION 'Seat allocation must use its booking showtime' USING ERRCODE = '23503';
 END IF;
 NEW.showtime_id := v_showtime;
 SELECT room_id, starts_at, ticket_price INTO v_room, v_start, v_price
   FROM showtimes WHERE showtime_id = v_showtime FOR UPDATE;
 IF v_start <= clock_timestamp() THEN
   RAISE EXCEPTION 'Showtime has already started' USING ERRCODE = 'UC004';
 END IF;
 SELECT room_id INTO v_seat_room FROM seats WHERE seat_id = NEW.seat_id;
 IF v_seat_room IS NULL THEN
   RAISE EXCEPTION 'Seat does not exist' USING ERRCODE = '23503';
 END IF;
 IF v_room IS DISTINCT FROM v_seat_room THEN
   RAISE EXCEPTION 'Seat belongs to another room' USING ERRCODE = 'UC003';
 END IF;
 IF NEW.price_at_booking IS NULL THEN
   NEW.price_at_booking := v_price;                         -- snapshot defaults to the screening price
 ELSIF NEW.price_at_booking <> v_price THEN
   RAISE EXCEPTION 'Price snapshot must equal the screening ticket price' USING ERRCODE = 'UC009';
 END IF;
 -- Fast rejection for visible allocations; the unique index is authoritative.
 IF EXISTS (
   SELECT 1 FROM booking_seats
   WHERE showtime_id = v_showtime AND seat_id = NEW.seat_id
 ) THEN
   RAISE EXCEPTION 'Seat already reserved for this showtime' USING ERRCODE = 'UC002';
 END IF;
 RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION booking_check_consistency() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE v_status text; v_total numeric; v_cnt integer; v_sum numeric;
BEGIN
 SELECT status, total_amount INTO v_status, v_total FROM bookings WHERE booking_id = NEW.booking_id;
 IF v_status IS NULL THEN RETURN NULL; END IF;
 SELECT count(*), COALESCE(sum(price_at_booking), 0) INTO v_cnt, v_sum
   FROM booking_seats WHERE booking_id = NEW.booking_id;
 IF v_status = 'BOOKED' THEN
   IF v_cnt = 0 THEN
     RAISE EXCEPTION 'A BOOKED booking must contain at least one seat' USING ERRCODE = 'UC010';
   END IF;
   IF v_sum <> v_total THEN
     RAISE EXCEPTION 'total_amount (%) must equal the sum of seat price snapshots (%)', v_total, v_sum
       USING ERRCODE = 'UC009';
   END IF;
 ELSIF v_cnt <> 0 THEN
   RAISE EXCEPTION 'A % booking must not keep seat rows', v_status USING ERRCODE = 'UC007';
 END IF;
 RETURN NULL;
END $$;

CREATE OR REPLACE FUNCTION create_booking(p_user_id bigint, p_showtime_id bigint, p_seat_ids bigint[])
RETURNS bigint LANGUAGE plpgsql AS $$
DECLARE v_price numeric(10,2); v_id bigint; v_n integer; v_constraint text;
BEGIN
 v_n := COALESCE(cardinality(p_seat_ids), 0);
 IF v_n = 0 THEN
   RAISE EXCEPTION 'At least one seat is required' USING ERRCODE = 'UC010';
 END IF;
 IF (SELECT count(DISTINCT s) FROM unnest(p_seat_ids) AS s) <> v_n THEN
   RAISE EXCEPTION 'Seat list contains duplicates or NULL' USING ERRCODE = 'UC010';
 END IF;
 SELECT ticket_price INTO v_price FROM showtimes WHERE showtime_id = p_showtime_id FOR UPDATE;
 IF NOT FOUND THEN
   RAISE EXCEPTION 'Screening not found' USING ERRCODE = 'UC011';
 END IF;
 PERFORM expire_overdue_bookings();
 INSERT INTO bookings(user_id, showtime_id, total_amount)
 VALUES (p_user_id, p_showtime_id, v_price * v_n)
 RETURNING booking_id INTO v_id;
 BEGIN
   INSERT INTO booking_seats(booking_id, seat_id, price_at_booking)
   SELECT v_id, s, v_price FROM unnest(p_seat_ids) AS s ORDER BY s;
 EXCEPTION WHEN unique_violation THEN
   GET STACKED DIAGNOSTICS v_constraint = CONSTRAINT_NAME;
   IF v_constraint = 'booking_seats_showtime_seat_key' THEN
     RAISE EXCEPTION 'Seat already reserved for this showtime' USING ERRCODE = 'UC002';
   END IF;
   RAISE;
 END;
 RETURN v_id;
END $$;

COMMIT;
