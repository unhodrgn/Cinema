# Database Design Handoff — Member A

**Project:** 영화관 예매 및 좌석 관리 시스템  
**Date:** 2026-11-17 (KST)  
**Source of truth:** `business_rules_decision_log.md` (BR-DL-001, v1.0)  
**DBMS:** PostgreSQL (changed from SQLite on 2026-11-20; see `docs/business/project_overview.md` section 7.1). SQLite-specific wording in this handoff was aligned accordingly; the approved decisions below are unchanged.

## A. Approved decisions to implement

| ID | Approved decision | Database consequence |
|---|---|---|
| D1 | Delete booking-seat details on cancellation; retain parent booking | Set `BOOKINGS.status = CANCELLED`; delete all matching `BOOKING_SEATS`; keep `BOOKINGS` row. |
| D2 | No screening modification after any booking exists | Reject updates if any `BOOKINGS` row references the screening, including cancelled/expired. |
| D3 | Unpaid booking expires after 10 minutes | Store `expires_at`; add `EXPIRED` booking status; after deadline set `EXPIRED` and delete seat details. |
| D4 | Browse/select without login; login required to confirm | No database requirement for guest account/role; authentication enforcement is an application concern. |
| D5 | Registration ID + password; six movie attributes | Store unique account ID and password hash; store title, genre, duration, rating, synopsis, release_date. |
| D6 | Price is per screening | Store price per seat on `SCREENINGS`; snapshot unit price in `BOOKING_SEATS`; total in `BOOKINGS`. |

## B. Required entities

Use the seven agreed primary entities/tables:

1. `USERS`
2. `MOVIES`
3. `ROOMS`
4. `SEATS`
5. `SCREENINGS`
6. `BOOKINGS`
7. `BOOKING_SEATS`

Do not add a `GUEST` role or a separate expiration-history table unless a technical necessity is identified and explained first.

## C. Minimum fields and domains to support

- `USERS`: unique account ID, `password_hash`, `role` constrained to `CUSTOMER` / `ADMIN`.
- `MOVIES`: `title`, `genre`, `duration`, `rating`, `synopsis`, `release_date`.
- `SCREENINGS`: movie FK, room FK, start/end timestamps, per-seat ticket price.
- `BOOKINGS`: customer FK, screening FK, booked timestamp, expiry timestamp, total amount, booking status, payment status.
- `BOOKING_SEATS`: booking FK, seat FK, per-seat price snapshot.
- Booking status domain: `BOOKED`, `CANCELLED`, `EXPIRED`.
- Payment status domain: `UNPAID`, `PAID`.
- Expiry: `expires_at = booked_at + 10 minutes`.

## D. Critical integrity rules

1. One seat cannot appear in two active bookings for the same screening.
2. A selected seat must belong to the room of the booking's screening.
3. Same-room screening intervals must not overlap.
4. A screening is immutable after any booking row references it, regardless of booking status.
5. Booking row and all booking-seat rows are created atomically.
6. Cancellation/expiry updates the parent status and deletes all child seat-detail rows atomically.
7. Expiry only applies when booking status is `BOOKED`, payment status is `UNPAID`, and current time is at or after `expires_at`.
8. Paid bookings do not expire.
9. No global seat availability flag in `SEATS`; availability is screening-specific.
10. Migration 0003 enforces active allocation uniqueness with immediate `UNIQUE(showtime_id, seat_id)`. A composite FK ties that showtime to the booking, and the seat FK references the physical seat. `bookings.total_amount` is `numeric(12,2)`; unit prices remain `numeric(10,2)`.

## E. Original seed requirements

The current seed has 6 films and 280 screenings over 14 days in Seoul time. The initial requirements below are retained for context.

- 5 rooms.
- 50 seats per room, 250 total.
- 5 movies.
- 140 screenings across 7 consecutive days.
- 1 pre-created ADMIN account.
- 1–2 pre-created CUSTOMER demo accounts.

## F. Deliverables from A

1. Conceptual ERD.
2. Logical relation schema and normalization (1NF–3NF).
3. Physical model and PostgreSQL DDL.
4. Constraints, indexes, triggers as required.
5. Seed data (PostgreSQL seed SQL; no SQLite `cinema.db` file).
6. Domain definition and table description.
7. A short validation report demonstrating:
   - duplicate seat booking is rejected;
   - wrong-room seat selection is rejected;
   - same-room overlapping screenings are rejected;
   - screening updates are rejected after any booking exists;
   - cancellation and expiry release all seats but preserve the parent booking;
   - expired unpaid bookings cannot be paid.

## G. Required coordination with B

B owns application behavior and must execute expiry processing before payment, seat availability, and booking confirmation. A must expose the `expires_at` and status fields needed for this behavior. A and B should agree on one timestamp format and timezone convention before implementation.

**Important:** Use `Asia/Seoul` consistently for application-local times and seed screening schedules unless the team agrees otherwise. Store/compare timestamps consistently; do not mix naive local timestamps and timezone-aware timestamps.
