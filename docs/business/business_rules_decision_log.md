# Business Rules Decision Log

**Project:** 영화관 예매 및 좌석 관리 시스템 (Cinema Reservation System)  
**Document ID:** BR-DL-001  
**Version:** 1.0  
**Decision date:** 2026-11-17 (KST)  
**Status:** APPROVED BY PROJECT TEAM  
**Applies to:** B03 Unit Business Description, database design (A), and subsequent application implementation (B)

---

## 1. Purpose and authority

This document records the six business decisions explicitly approved by the project team on 2026-11-17. It is the authoritative supplement to the approved project overview (B01) and business function diagram (B02).

Where this document clarifies or extends an earlier underspecified point, the decisions below take precedence for B03 and subsequent database/application design. The approved project scope and existing function IDs remain unchanged.

## 2. Approved decisions

### D1 — Treatment of booking-seat details after cancellation

**Decision: Option A — Delete booking-seat detail rows and retain the booking record.**

1. When a customer cancels a booking, change the booking status to `CANCELLED`.
2. Delete all detail rows belonging to that booking from `BOOKING_SEATS`.
3. Retain the parent row in `BOOKINGS` as cancellation history, including its booking ID, customer, screening, booking time, total amount, booking status, and payment status.
4. The released seats become available for another booking in the same screening.
5. The application must not claim that it can display the exact seat list of a cancelled booking, because those detail rows have been deleted. Booking-history screens may display the retained booking summary and its `CANCELLED` status.

The same detail-row release and parent-history retention principle applies when a booking expires under D3: set status to `EXPIRED`, delete its `BOOKING_SEATS` rows, and retain the parent booking record.

### D2 — Editing and deleting screenings or movies after bookings/start

**Decision: Do not allow screening modifications once any booking exists or once the screening has started; allow conditional deletion of unstarted, unbooked screenings and movies.**

1. An administrator may modify a screening only when it has not yet started (`starts_at > clock_timestamp()`) and no row in `BOOKINGS` references that screening (saving identical values on an unstarted booked screening is treated as a no-op).
2. If any booking record exists, reject every actual modification to that screening, including changes to its movie, room, start time, end time, or ticket price (`UC001`).
3. The booking-protection rule applies regardless of booking status: `BOOKED`, `CANCELLED`, or `EXPIRED`.
4. This rule preserves the integrity of existing booking history and avoids changing the screening context associated with a past booking.
5. Adding a new screening remains allowed when all existing screening rules are satisfied. An administrator may delete a screening only if it has not yet started and has no `BOOKINGS` rows of any status (`DELETE /api/admin/screenings/{id}`). An administrator may delete a movie (`DELETE /api/admin/movies/{id}`) together with its upcoming unbooked screenings in one transaction, provided none of its screenings have started or have any booking records.

### D3 — Expiration of unpaid bookings

**Decision: Option B — An unpaid booking expires 10 minutes after booking confirmation.**

1. A booking is initially created with booking status `BOOKED` and payment status `UNPAID`.
2. The 10-minute payment window begins when booking confirmation is successfully recorded, not when seat selection begins.
3. Store an expiration timestamp calculated as `booked_at + 10 minutes` (for example, `expires_at`).
4. Payment is valid only while the booking is still `BOOKED`, its payment status is `UNPAID`, and the current time is strictly earlier than `expires_at`.
5. At or after `expires_at`, if the booking is still unpaid, change its booking status to `EXPIRED`, delete all its `BOOKING_SEATS` detail rows, and retain the parent `BOOKINGS` row as history.
6. Once expired, the booking cannot be paid, cancelled, or reactivated. The customer must make a new booking if seats are still available.
7. A successfully paid booking changes payment status to `PAID` and does not expire under this rule.
8. Expiration releases every seat in the booking together. Partial expiration or partial seat release is not supported.
9. The expiration operation and seat release must be atomic. A booking must not be left `EXPIRED` while its seat details continue to block availability, or have its details deleted while it remains an active booking.
10. The application must enforce expiration before processing payment and before calculating seat availability or confirming a new booking. The implementation may use a scheduled cleanup routine, request-triggered cleanup, or both, but it must reliably enforce the 10-minute deadline and perform the transition transactionally.

**Boundary condition:** if `current_time >= expires_at`, the unpaid booking is expired. Payment completed at or after that timestamp must be rejected.

### D4 — Login requirement for browsing and seat selection

**Decision: Option A — Login is not required for browsing or selecting seats.**

1. Users may access movie listing/detail (C-02), screening lookup (C-03), seat availability lookup (C-04), and seat selection (C-05) without logging in.
2. Login is mandatory before booking confirmation (C-06), as already specified in B01.
3. Selecting seats does not itself reserve or hold those seats. The seats are held only after a successful booking confirmation.
4. The project continues to have only the two approved account roles, `CUSTOMER` and `ADMIN`. Do not add a `GUEST` account role. “Unauthenticated visitor” describes access without a logged-in session, not a third account type.

### D5 — Registration inputs and movie attributes

**Decision: Option A for registration; all six listed movie attributes are approved.**

**Customer registration inputs:**
- Account ID
- Password

No full name, email address, phone number, or other registration field is required by the approved scope. The role is assigned by the system as `CUSTOMER`; public registration must never create an `ADMIN` account. Passwords must be stored as a secure one-way password hash, not as plaintext and not as reversibly encrypted text.

**Account ID policy (0005–0006):** public registration accepts a Unicode ID or a common ASCII email address used as the account ID. The first character of a normal ID is a Unicode letter or decimal digit. Subsequent characters can also include `_`, `-`, `.` and `+`. An email has exactly one `@`, an alphanumeric start, and a dotted domain with valid labels. Registration checks raw input and NFKC-normalized output, rejects spaces and invisible/control characters, and allows at most 60 normalized code points. Empty IDs are invalid. Case-insensitive uniqueness uses the 0005 database index. Login retains its existing NFKC and edge-whitespace handling. No email verification or separate email field is required.

**Movie attributes to support:**
- `title` — 영화 제목
- `genre` — 장르
- `duration_minutes` (business term `duration`) — 상영 시간 (minutes)
- `rating` — 관람 등급
- `synopsis` — 줄거리
- `release_date` — 개봉일
- `poster_url` — 포스터 경로 (optional, relative path `/images/posters/<name>.(jpg|png)`)

The database may also contain a generated movie identifier/primary key. That identifier is a technical key, not an additional user-entered movie attribute.

### D6 — Ticket price model

**Decision: Option B — A separate ticket price is defined for each screening.**

1. Each screening has one ticket price per seat, stored with the screening information.
2. The booking total is calculated as `screening ticket price × number of selected seats` at booking confirmation.
3. Store the per-seat price applied at booking time in each `BOOKING_SEATS` detail row (price snapshot), and store the calculated total in `BOOKINGS`.
4. Do not use one global fixed ticket price for the whole cinema.
5. Under D2, the price of a screening cannot be modified once any booking record references that screening.
6. The team has not approved a specific numeric ticket price. Seed-data values may be selected separately and must be documented as demo data, not as a new business rule.

---

## 3. Canonical status model

The following status values are approved for the initial implementation.

### 3.1 Booking status (`BOOKINGS.status`)

| Value | Meaning | Holds seats? | Booking-seat detail rows |
|---|---|---:|---|
| `BOOKED` | Booking has been confirmed and has not been cancelled or expired | Yes, subject to D3 if unpaid | Retained while active |
| `CANCELLED` | Customer cancelled the complete booking before screening start | No | Deleted |
| `EXPIRED` | Payment was not completed before the 10-minute deadline | No | Deleted |

### 3.2 Payment status (`BOOKINGS.payment_status`)

| Value | Meaning |
|---|---|
| `UNPAID` | Simulated payment has not been completed |
| `PAID` | Simulated payment has been completed successfully |

Payment status and booking status are separate attributes. For example, a paid booking that is later cancelled remains `payment_status = PAID` and changes to `status = CANCELLED`. Refund processing is outside the approved project scope; do not invent a refund status or refund workflow.

An expired booking remains `payment_status = UNPAID` and changes to `status = EXPIRED`.

---

## 4. Required updates to B03

Update `docs/business/unit_business_description.md` to reflect the approved decisions. Keep the existing 14 function IDs, nine-field template, section structure, and Korean academic writing style.

| B03 unit | Required update |
|---|---|
| CM-01 | Keep account ID and password as login inputs. Use role-specific access checks for `CUSTOMER` and `ADMIN`. |
| C-01 | Registration inputs are only account ID and password. Assign `CUSTOMER` server-side. Say password is stored as a secure one-way hash (`해시 처리`), not merely “encrypted”. |
| C-02 | Movie list/detail supports the six core movie attributes (`title`, `genre`, `duration_minutes`, `rating`, `synopsis`, `release_date`) plus optional `poster_url`. |
| C-02–C-05 | Explicitly state that login is not required for these lookup/selection functions. Selecting seats does not reserve them. |
| C-04 | An unpaid `BOOKED` reservation blocks the seat only until its expiry deadline; paid `BOOKED` reservations continue to block it. Cancelled and expired bookings do not block seats. Expiration must be processed before availability is returned. |
| C-05 | Seat selection is provisional only. It does not hold seats or start the 10-minute payment timer. |
| C-06 | On successful confirmation, create `BOOKED` + `UNPAID`, set `booked_at` and `expires_at = booked_at + 10 minutes`, save the booking and all seat details atomically, and hold those seats during the payment window. |
| C-07 | Accept simulated payment only before `expires_at` and only for a `BOOKED` + `UNPAID` booking owned by the logged-in customer. On success set payment status to `PAID`. Reject payment at or after expiry. |
| C-08 | Keep cancelled and expired parent booking records visible. Since D1 removes booking-seat rows, do not promise to show exact seats for `CANCELLED` or `EXPIRED` records. |
| C-09 | On customer cancellation before screening start, set `CANCELLED`, delete all associated booking-seat detail rows, and retain the parent booking. No partial-seat cancellation. Do not allow cancellation of an `EXPIRED` booking. |
| A-01 | Use the supported movie attributes (6 core attributes + optional `poster_url`) and support adding, editing, and conditionally deleting movies (blocked if any screening has started or has bookings). |
| A-02 | Reject edits to started screenings or actual modifications to screenings referenced by any booking row (`BOOKED`, `CANCELLED`, `EXPIRED`), including price changes. Support deleting unstarted screenings that have no booking records. |
| A-03 | Include cancelled and expired booking summaries in the global list, but do not promise exact seat details for those records because their detail rows are deleted. |

For C-08 and A-03, retain booking-level fields such as booking ID, customer, movie/screening reference, booking time, total amount, booking status, and payment status where available. Seat details are shown only while corresponding detail rows still exist.

---

## 5. Database design handoff for Member A

Member A must use this section as an approved business-rule input when designing the logical and physical data models. It does not prescribe every column name or force an unnormalized schema, but the database must support the following behavior.

### 5.1 Required data support

| Entity/table | Required data or behavior |
|---|---|
| `USERS` | Unique account ID/username, password hash, role (`CUSTOMER` or `ADMIN`). Public registration creates `CUSTOMER` only. |
| `MOVIES` | Title, genre, duration, rating, synopsis, release date, optional poster URL (`poster_url`). |
| `SCREENINGS` | Movie, room, start time, end time, and per-seat ticket price. |
| `BOOKINGS` | Customer, screening, booking timestamp, expiration timestamp, total amount, booking status, payment status. |
| `BOOKING_SEATS` | Booking, selected seat, and price snapshot per seat. Rows exist only while the booking is active; delete all rows on cancellation or expiration. |

### 5.2 Constraints and transaction requirements

1. Enforce that a seat can have at most one active booking in the same screening. A cancelled or expired booking must not prevent the seat from being booked again.
2. Enforce that every selected seat belongs to the room assigned to the booking's screening.
3. Enforce that screening intervals do not overlap within the same room.
4. Enforce the D2 immutability rule: reject updates to a screening if any `BOOKINGS` row references it, including `CANCELLED` and `EXPIRED` records. This is different from checking only active bookings.
5. Create a booking and all its seat-detail rows atomically. If any seat fails validation, do not create a partial booking.
6. Process payment, expiry, cancellation, and seat release transactionally.
7. Expiry processing must be safe to run more than once (idempotent). It must only expire rows still in `BOOKED` + `UNPAID` state whose deadline has passed.
8. When expiring or cancelling a booking, update the parent booking status and delete all associated `BOOKING_SEATS` rows in the same transaction.
9. Do not store a global seat status in `SEATS`; availability is determined per screening from active booking details.
10. For the `(screening, seat)` uniqueness rule, `booking_seats` stores `showtime_id` constrained by a composite FK to `bookings(booking_id, showtime_id)` with an immediate `UNIQUE(showtime_id, seat_id)` constraint (migration `0003_booking_integrity.sql`) alongside the validation triggers.

### 5.3 Recommended status and timestamp domains

- Booking status: `BOOKED`, `CANCELLED`, `EXPIRED`.
- Payment status: `UNPAID`, `PAID`.
- `booked_at`: timestamp when booking confirmation succeeds.
- `expires_at`: timestamp ten minutes after `booked_at`.
- Per-seat ticket price snapshot: stored with the booking-seat detail while that detail exists.

The DBMS is PostgreSQL 18 (see B01 Project Overview, section 7.1), accessed via `psycopg2`. All timestamps use `timestamptz` with `Asia/Seoul` as the business time zone.

### 5.4 Important implementation note for Member B

Request-time expiration is implemented via `expire_overdue_bookings()` (called on seat availability, customer booking history, and admin booking lists) and built directly into `create_booking()`, `pay_booking()`, and `cancel_booking()`. There is no background scheduler or cron job.

---

## 6. Decisions not made by this log

The following are not specified here and must not be silently invented as business rules:

- A fixed numeric ticket price; only the per-screening pricing model is approved.
- A specific format or minimum length for account IDs and passwords.
- A specific movie rating vocabulary.
- A specific genre list.
- Refund behavior or refund processing.
- Partial-seat cancellation.

Technical choices needed to implement the approved rules (for example, exact SQL trigger definitions, column types, and request-time expiry invocation) belong in the database/application design and must preserve the decisions above.

---

## 7. Approval and change control

The six decisions D1–D6 were explicitly selected by the project owner on 2026-11-17. Subsequent alignments (PostgreSQL 18 migration, `poster_url` support, conditional movie/screening deletion, migration `0003` composite FK + immediate unique index, migration `0004` finite money checks, migration `0005` account ID normalization) are reflected across B01–B03, `docs/database/*`, `docs/api/api_contract.md`, and the application codebase.
