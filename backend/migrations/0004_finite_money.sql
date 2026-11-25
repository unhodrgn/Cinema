-- DB-02: PostgreSQL numeric orders NaN above finite values, so >= 0 alone
-- does not exclude it. Preserve all existing types and nonnegative checks.
BEGIN;
SET LOCAL lock_timeout = '5s';
LOCK TABLE showtimes, bookings, booking_seats IN ACCESS EXCLUSIVE MODE;

DO $$
DECLARE
 invalid_prices bigint;
 invalid_totals bigint;
 invalid_snapshots bigint;
BEGIN
 SELECT count(*) INTO invalid_prices FROM showtimes
  WHERE ticket_price IN ('NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric);
 SELECT count(*) INTO invalid_totals FROM bookings
  WHERE total_amount IN ('NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric);
 SELECT count(*) INTO invalid_snapshots FROM booking_seats
  WHERE price_at_booking IN ('NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric);
 IF invalid_prices + invalid_totals + invalid_snapshots > 0 THEN
  RAISE EXCEPTION USING ERRCODE = '23514',
   MESSAGE = format('Migration 0004 stopped: non-finite values in showtimes=%s, bookings=%s, booking_seats=%s',
                    invalid_prices, invalid_totals, invalid_snapshots),
   HINT = 'Reconcile existing records before retrying; this migration does not modify data.';
 END IF;
END $$;

ALTER TABLE showtimes ADD CONSTRAINT showtimes_ticket_price_finite
 CHECK (ticket_price NOT IN ('NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric));
ALTER TABLE bookings ADD CONSTRAINT bookings_total_amount_finite
 CHECK (total_amount NOT IN ('NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric));
ALTER TABLE booking_seats ADD CONSTRAINT booking_seats_price_at_booking_finite
 CHECK (price_at_booking NOT IN ('NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric));
COMMIT;
