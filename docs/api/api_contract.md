# REST API Contract

**Project:** 영화관 예매 및 좌석 관리 시스템 (Cinema Reservation System)
**Status:** foundation (T1), authentication (T2) and the public catalog (T3) are implemented. Only the endpoints in section 11 exist. The endpoints in section 12 are planned for T4–T8 and may be refined there; everything else in this document is already implemented and tested.
**Authority:** B01–B05 and BR-DL-001 (D1–D6) for business rules; [`postgresql_flask_integration_contract.md`](../database/postgresql_flask_integration_contract.md) for the database. This document defines only how the independent frontend and the backend talk to each other. It changes no business rule.

---

## 1. Architecture

```
 Browser ── static files ──────► Frontend server  :8080   frontend/server.py (HTML, CSS, JS only)
    │
    └──── JSON over HTTP ──────► Backend API      :5000   Flask, JSON only
                                      │
                                      └── PostgreSQL protocol ──► PostgreSQL :5432 (reachable by the API only)
```

| Layer | Does | Never does |
|---|---|---|
| **Frontend** (`frontend/`) | Pages, forms, provisional seat selection, rendering API data as text, holding the token. | Access PostgreSQL, contain SQL or credentials, import backend code, decide a business outcome. |
| **Backend** (`app/`) | Authentication, authorization, validation, ownership checks, calling the database functions, translating database errors. | Render HTML, serve static files or templates. |
| **Database** | Schema, constraints, triggers, `create_booking`, `pay_booking`, `cancel_booking`, `expire_overdue_bookings`, every deadline. | Change as part of this work. |

The three layers are separate processes with separate configuration. PostgreSQL is configured for the API only; the frontend device never needs a route to it.

## 2. Conventions

* **Base URL:** the API origin, e.g. `http://localhost:5000`. All API paths start with `/api`; the two health endpoints are at `/health` and `/health/db`. There is no version segment.
* **Methods:** `GET`, `POST`, `PUT`. There is no `DELETE`: the approved scope has no delete function for movies or screenings (B03 A-01, A-02), and no refund or other removal workflow. (Decision D2 is a different rule: it forbids *editing* a screening that any booking references.)
* **Paths:** lower-case nouns, integer ids, no trailing slash (`/api/movies/3`). Actions that are not CRUD use a verb sub-path (`/api/bookings/{id}/pay`).
* **Encoding:** UTF-8 JSON. Responses are `Content-Type: application/json`.
* **Names:** JSON fields use the physical column names where one exists (`username`, `user_id`, `showtime_id`, `ticket_price`, …) in `snake_case`.
* **Caching:** every response carries `Cache-Control: no-store`.
* **Security headers on every response:** `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'`.

## 3. Requests

* A request with a body (`POST`, `PUT`) must send `Content-Type: application/json` and a **JSON object**.
* Maximum body size: 64 KiB (`MAX_CONTENT_LENGTH`).
* Query parameters are used for filtering `GET` requests only.
* The server never reads authentication from the query string or from cookies.

| Problem | Status | `error.code` |
|---|---|---|
| Body present but not `application/json` | 415 | `unsupported_media_type` |
| Empty, malformed, or not a JSON object | 400 | `invalid_json` |
| Body larger than 64 KiB | 413 | `payload_too_large` |

## 4. Serialization

| Type | JSON form | Example |
|---|---|---|
| Timestamp (`timestamptz`) | ISO 8601 string **with UTC offset**; the offset is the application time zone (`APP_TIMEZONE`, default `Asia/Seoul`) | `"2026-11-25T19:00:00+09:00"` |
| Date | ISO 8601 date | `"2026-11-25"` |
| Money (`numeric(10,2)`) | decimal **string**, never a number | `"12000.00"` |
| Identifiers | integers | `3` |
| Missing optional value | `null` | `"genre": null` |

A naive (offset-less) timestamp is never produced: the server refuses to serialize one. Clients that **send** a time without an offset mean cinema-local time (`APP_TIMEZONE`); the conversion is done in SQL, never with the server's own clock. All deadlines (payment window, screening start) are decided by the database; the frontend only displays them.

## 5. Errors

Every error, including the ones Flask raises itself, uses one envelope:

```json
{ "error": { "code": "seat_unavailable", "message": "One or more of the selected seats are no longer available. Please choose again." } }
```

Validation errors add a `fields` object (field name → fixed message):

```json
{ "error": { "code": "validation_error", "message": "One or more fields are not valid.",
             "fields": { "title": "Title is required." } } }
```

* `code` is stable and machine-readable; `message` is fixed, user-safe English text. Clients branch on `code`, never on `message`.
* Messages never contain SQL, constraint or column names, hosts, users, request data, parser output or stack traces. Details go to the server log without secrets.
* Responses to `GET /health/db` use their own small body (section 11), not this envelope.

| HTTP | `code` | Meaning |
|---|---|---|
| 400 | `bad_request` | The request could not be understood |
| 400 | `invalid_json` | Body is not a valid JSON object |
| 400 | `validation_error` | Field-level problems, see `fields` |
| 400 | `invalid_seat` | Seat not valid for the screening (`UC003`) |
| 400 | `no_seat_selected` | No seat, or a duplicate seat (`UC010`) |
| 400 | `unknown_reference` | A referenced record does not exist (`23503`) |
| 400 | `invalid_value` | A value violates a database CHECK (`23514`) |
| 401 | `unauthorized` | Missing, malformed, expired or invalid token, or the account no longer exists |
| 401 | `invalid_credentials` | Login failed: unknown account ID **or** wrong password (one message for both) |
| 403 | `forbidden` | Authenticated, but the role is not allowed |
| 403 | `customer_only` | The booking owner is not a customer (`UC008`) |
| 404 | `not_found` | Unknown path, or the booking/screening does not exist for this user (`UC011`) |
| 405 | `method_not_allowed` | Wrong method; the `Allow` header lists the right ones |
| 409 | `screening_has_bookings` | Screening has booking records and cannot be modified, any status (`UC001`, D2) |
| 409 | `seat_unavailable` | Seat already reserved, including a lost race (`UC002`) |
| 409 | `screening_started` | Screening already started (`UC004`) |
| 409 | `screening_has_started` | An administrator tried to edit a screening that has already started (database clock); not a database rule |
| 409 | `cancellation_closed` | Screening started, no cancellation (`UC005`) |
| 409 | `invalid_booking_state` | Not possible in the booking's state (`UC006`) |
| 409 | `screening_overlap` | Overlaps another screening in the room (`23P01`) |
| 409 | `duplicate_value` | Value already in use, e.g. account ID (`23505`) |
| 413 | `payload_too_large` | Body larger than 64 KiB |
| 415 | `unsupported_media_type` | Body not `application/json` |
| 500 | `internal_error` | Server fault, including bugs the contract marks internal (`UC007`, `UC009`, `23001`) |
| 503 | `database_unavailable` | The database cannot be reached |

Other HTTP statuses use `http_error` (4xx) or `server_error` (5xx) with a fixed message. The SQLSTATE → `code` mapping is the one in `app/errors.py`, checked against section 6 of the database integration contract by the tests.

## 6. Authentication

* **Bearer token** in the `Authorization` header: `Authorization: Bearer <token>`. No cookies are used or accepted, which is what makes the API usable from another origin or another machine over plain HTTP.
* The token is signed (`itsdangerous`, the application's `SECRET_KEY`) and contains only the user id. It carries **no role and no username**: on every request the server loads the account from the database, so a changed role or a deleted account takes effect immediately.
* Lifetime: `AUTH_TOKEN_MAX_AGE_SECONDS`, default 28800 (8 hours), between 60 and 2592000.
* `401` always includes `WWW-Authenticate: Bearer` (with `error="invalid_token"` when a token was sent but is no good). `403` means the token is valid but the role is wrong.
* **Limitation:** tokens are stateless and cannot be revoked on the server. Logout discards the token in the browser; a stolen token stays valid until it expires. A server-side revocation list would need a new table, which is outside the approved database.
* The frontend keeps the token in `sessionStorage` (cleared when the tab closes). Because injected script could read it, the frontend renders API data only as text (no `innerHTML`), loads no third-party scripts, and is served with a restrictive Content-Security-Policy.

**Account fields (D5).** The business term is *account ID* (계정 ID); the database column and the JSON field are `username` (`users.username`, `varchar(60)`, unique). Registration takes only `username` and `password`: no name, e-mail or phone. `role` is `CUSTOMER` or `ADMIN` and is **never accepted from a request**: public registration always creates a `CUSTOMER`. The password is only ever received, never returned. A user object, where one is returned, is `{ "user_id": 1, "username": "customer_demo", "role": "CUSTOMER" }`; the password hash is never serialized.

### 6.1 Endpoints

**`POST /api/auth/register`** (public), body `{"username": "...", "password": "..."}`, answers `201`:

```json
{ "user": { "user_id": 7, "username": "alice", "role": "CUSTOMER" } }
```

* Only `username` (the account ID) and `password` are read. Any other key (`role`, `user_id`, …) is ignored: the role is never taken from the request and is always `CUSTOMER` (BR-14); an `ADMIN` cannot be created through the API.
* Registration does not log the user in (B03 C-01: the new account is used through login).
* Technical limits only, no business password policy (none is approved): `username` is required, text, at most 60 characters (the width of `users.username`), no control characters, not blank; `password` is required, text, at most 256 characters (stops the server hashing an unbounded string). Violations answer `400 validation_error` with `fields`.
* A duplicate account ID answers `409 duplicate_value` (SQLSTATE `23505`, the existing mapping) with `fields.username`.
* The password is stored only as a one-way salted hash, `pbkdf2:sha256:600000`, the method of the seeded accounts.

**`POST /api/auth/login`** (public), body `{"username": "...", "password": "..."}`, answers `200`:

```json
{ "token": "…", "token_type": "Bearer", "expires_in": 28800,
  "user": { "user_id": 7, "username": "alice", "role": "CUSTOMER" } }
```

* A missing field answers `400 validation_error`.
* An unknown account ID and a wrong password answer the identical `401 invalid_credentials` ("The account ID or password is incorrect."); for an unknown account the server still performs one full password-hash verification, so the two cases also take the same time.
* Both roles (`CUSTOMER`, `ADMIN`) log in here; what each may call is decided by the route policies (section 7).

**`GET /api/auth/me`** (policy `authenticated`) answers `200 {"user": {...}}` with the account's **current** database row.

**`POST /api/auth/logout`** (public) answers `204` with no body. Tokens are stateless, so the server has nothing to revoke: the browser discards its token. It is public on purpose: B03 CM-02 says logging out while not logged in is not an error.

The password hash is never serialized, and passwords, hashes and tokens are never written to the log.

**Demo account passwords.** The three seeded accounts keep password hashes whose plaintext nobody knows. `scripts/set_demo_passwords.py` sets known passwords for existing accounts. It is a setup tool, not part of the API: it needs a database role that may `UPDATE users` (the API's role is only granted `INSERT` on `users`, integration contract section 8), connects with explicit `SETUP_DB_*` settings and never falls back to the API's `DB_*` credentials, never prints a password or hash, and changes nothing if any named account does not exist.

### 6.2 Corrections to the T1 draft of this document

* `POST /api/auth/logout` was listed as token-protected. That would answer `401` to a logged-out user and conflicts with B03 CM-02, so it is public.
* A policy `authenticated` (any logged-in role) was added for `GET /api/auth/me`.
* The failed-login code `invalid_credentials` was added: B03 CM-01 requires the same message for an unknown account and a wrong password, and the generic `unauthorized` is reserved for missing or invalid tokens.

## 7. Route policies

Every route declares who may call it, and the application **refuses to start** if any route has no declared policy.

| Policy | Who | Enforced as |
|---|---|---|
| `public` | Anyone, no token | — |
| `authenticated` | Any authenticated account, whatever its role | 401 without a valid token |
| `customer` | An authenticated account with role `CUSTOMER` | 401 without a valid token, 403 for `ADMIN` (an administrator is not a booking customer, B03) |
| `admin` | An authenticated account with role `ADMIN` | 401 without a valid token, 403 for `CUSTOMER` |

For every protected request the server verifies the token's signature and age, then loads the account from PostgreSQL (`app.auth.load_user`): a deleted account answers `401`, and a changed role applies on the very next request. If no user loader is registered the guards **fail closed** (401). The frontend's own hiding of admin pages is a convenience only; the backend is the authority.

## 8. CORS

The frontend is another origin (another port, or another machine), so browsers enforce CORS.

* `CORS_ALLOWED_ORIGINS` lists **exact** origins, comma-separated: `http://localhost:8080,http://192.168.0.10:8080`. `*`, paths, queries and credentials in the URL are rejected at startup. Scheme, host and port must all match (`http://localhost:8080` is not `http://localhost` or `http://127.0.0.1:8080`).
* Empty (the default) means no cross-origin access at all.
* An allowed origin gets `Access-Control-Allow-Origin: <that origin>` on **every** response, error responses included. Any other origin gets no CORS header. `Vary: Origin` is always present when a list is configured.
* **Preflight** (`OPTIONS` with `Access-Control-Request-Method`) is answered `204` with `Allow-Methods: GET, POST, PUT`, `Allow-Headers: Authorization, Content-Type`, `Max-Age: 600` only if the origin is allowed, the path is a real route that accepts the requested method, the method is one of those three and the requested headers are limited to those two. Otherwise it gets no CORS header and the browser blocks the request.
* `Access-Control-Allow-Credentials` is never sent (no cookies).
* CORS is a browser-side protection, not authentication: the server still answers other origins, it only withholds the permission to read the answer.

## 9. Status codes

`200` success · `201` created · `204` success without body · `400` bad request / validation · `401` not authenticated · `403` not allowed · `404` not found · `405` wrong method · `409` conflict with the current state · `413` too large · `415` wrong media type · `500` server fault · `503` database unavailable.

## 10. Frontend rules

* All backend access goes through `frontend/js/api.js`. It only sends requests whose path starts with `/api` or `/health`, to the configured origin; sends no cookies; refuses redirects; and clears the token when the server answers `401` to a request that carried one.
* The API address comes from `/config.js`, which the frontend server generates from `API_BASE_URL`; it is not a file in the repository.
* The frontend contains no business rules. Anything it shows before the server has answered (for example an estimated total) is labelled as an estimate; the authoritative values come from the API.

## 11. Endpoints that exist now

| Method | Path | Policy | Response |
|---|---|---|---|
| GET | `/api` | public | `200 {"service": "cinema-reservation-api", "status": "ok"}` |
| GET | `/health` | public | `200 {"status": "ok"}` (no database access) |
| POST | `/api/auth/register` | public | `201 {"user": {...}}`, section 6.1 |
| POST | `/api/auth/login` | public | `200 {"token", "token_type", "expires_in", "user"}`, section 6.1 |
| GET | `/api/auth/me` | authenticated | `200 {"user": {...}}` |
| POST | `/api/auth/logout` | public | `204` |
| GET | `/api/movies` | public | `200 {"movies": [...]}`, section 11.1 |
| GET | `/api/movies/{id}` | public | `200 {"movie": {...}}`; `404` if unknown |
| GET | `/api/screenings` | public | `200 {"date", "screenings": [...]}`, query `movie_id`, `date`, section 11.1 |
| GET | `/api/screenings/{id}` | public | `200 {"screening": {...}}`; `404` if unknown |
| GET | `/api/screenings/{id}/seats` | public | `200 {"screening": {...}, "seats": [...]}`, section 11.2 |
| POST | `/api/bookings` | customer | `201 {"booking": {...}}`, section 11.3 |
| POST | `/api/bookings/{id}/pay` | customer | `200 {"outcome": "PAID"|"EXPIRED", "booking": {...}}`, section 11.3 |
| GET | `/api/bookings` | customer | `200 {"bookings": [...]}`, section 11.4 |
| GET | `/api/bookings/{id}` | customer | `200 {"booking": {...}}`, section 11.4 |
| POST | `/api/bookings/{id}/cancel` | customer | `200 {"outcome": "CANCELLED"|"EXPIRED", "booking": {...}}`, section 11.4 |
| GET | `/api/admin/movies` | admin | `200 {"movies": [...]}`, section 11.5 |
| GET | `/api/admin/movies/{id}` | admin | `200 {"movie": {...}}`; `404` if unknown |
| POST | `/api/admin/movies` | admin | `201 {"movie": {...}}`, section 11.5 |
| PUT | `/api/admin/movies/{id}` | admin | `200 {"movie": {...}}`, section 11.5 |
| GET | `/api/admin/screenings` | admin | `200 {"screenings": [...], "rooms": [...]}`, section 11.6 |
| GET | `/api/admin/screenings/{id}` | admin | `200 {"screening": {...}}`; `404` if unknown |
| POST | `/api/admin/screenings` | admin | `201 {"screening": {...}}`, section 11.6 |
| PUT | `/api/admin/screenings/{id}` | admin | `200 {"screening": {...}}`, section 11.6 |
| GET | `/api/admin/bookings` | admin | `200 {"bookings": [...]}`, section 11.7 |
| GET | `/health/db` | public | `200 {"status": "ok", "database": "ok"}`; `503 {"status": "unavailable", "database": "unavailable"}` if PostgreSQL cannot be reached or does not answer correctly. No host, port, name, user, version or error text. |

### 11.1 Catalog shapes (T3, public: no login, D4)

**Movie** (the six approved attributes, D5, plus the technical key): `movie_id`, `title`, `genre` (nullable), `duration_minutes` (B03 calls it *duration*), `rating` (nullable), `synopsis` (nullable), `release_date` (nullable, `YYYY-MM-DD`). Genre and rating are free text: no vocabulary is approved.

**Screening:** `showtime_id`, `movie_id`, `title`, `room_id`, `room_name`, `starts_at`, `ends_at` (ISO 8601 with offset), `ticket_price` (decimal string, per screening, D6), `has_started` (boolean). `has_started` is computed by the database clock and is a display state only: the rule that a started screening cannot be booked (BR-12) is enforced by the database when a booking is made.

**`GET /api/screenings?movie_id=&date=`** lists the screenings that **start** on one calendar day of the cinema's time zone (`APP_TIMEZONE`, half-open `[00:00, next 00:00)`), ordered by start time then room.

* `date` is strictly `YYYY-MM-DD`; omitted or empty means today in the cinema's time zone, decided by the database. The answer repeats the date used.
* `movie_id` is optional (positive integer). An unknown movie answers `404` (B03 C-03).
* A bad `date` or `movie_id` answers `400 validation_error` with `fields.date` / `fields.movie_id`.
* No screenings on that day is an empty list, not an error.

A path id that is not a positive integer, or is larger than the database can hold, is an ordinary `404`.

### 11.2 Seat availability (T4, public, C-04, C-05)

**`GET /api/screenings/{id}/seats`** runs `expire_overdue_bookings()` in the same transaction, then returns the screening information and its room's 50 seats with availability status.
* `screening`: the screening object (same shape as `GET /api/screenings/{id}`).
* `seats`: array of `{"seat_id": 1, "seat_row": "A", "seat_number": 1, "is_available": true/false}`.
* A seat is unavailable if reserved by an active `BOOKED` booking (paid or within 10-minute payment window).
* An unknown screening ID answers `404`.

### 11.3 Booking creation and simulated payment (T5, customer, C-06, C-07)

**`POST /api/bookings`** creates a booking atomically via database function `create_booking()`.
* Request body: `{"screening_id": 5, "seat_ids": [1, 2]}`.
* Validates `screening_id` and non-empty `seat_ids` list.
* Sets `status = 'BOOKED'`, `payment_status = 'UNPAID'`, `expires_at = booked_at + 10 min`, and records price snapshots.
* Answers `201 {"booking": {...}}`.
* Fails with `409 seat_unavailable` if any seat is already booked or taken concurrently (`UC002`).
* Fails with `409 screening_started` if the screening has started (`UC004`).
* Fails with `400 no_seat_selected` if seat list is empty or invalid (`UC010`).

**`POST /api/bookings/{id}/pay`** processes simulated payment atomically via database function `pay_booking()`.
* Must be called by the booking's owner (customer).
* If paid within the 10-minute window, changes `payment_status` to `PAID` and returns `200 {"outcome": "PAID", "booking": {...}}`.
* If payment window elapsed, marks booking `EXPIRED`, releases seats, commits, and returns `200 {"outcome": "EXPIRED", "booking": {...}}`.
* Fails with `404` if not found or not owned by user (`UC011`).
* Fails with `409 invalid_booking_state` if already paid or cancelled (`UC006`).

### 11.4 Customer booking history and cancellation (T6, customer, C-08, C-09)

**`GET /api/bookings`** returns all bookings belonging to the authenticated customer, running expiry first.
* Sorted by `booked_at DESC`.
* Each booking includes `seats: [{seat_id, seat_row, seat_number, price_at_booking}]` if `status == 'BOOKED'`, or `seats: []` if cancelled/expired (D1, D3).
* Answers `200 {"bookings": [...]}`.

**`GET /api/bookings/{id}`** returns a single booking belonging to the customer, running expiry first.
* Answers `200 {"booking": {...}}`.
* Fails with `404` if not found or not owned by user.

**`POST /api/bookings/{id}/cancel`** cancels a booking atomically via database function `cancel_booking()`.
* Must be called by the booking owner before the screening starts (D1).
* If booking was UNPAID and overdue, it expires instead (`outcome: "EXPIRED"`).
* If successfully cancelled, changes status to `CANCELLED`, retains `total_amount` and `payment_status` (stays `PAID` if already paid - D1), deletes `booking_seats` (seats released!), sets `cancelled_at`, and returns `200 {"outcome": "CANCELLED", "booking": {...}}`.
* Fails with `404` if not found or not owned by user (`UC011`).
* Fails with `409 cancellation_closed` if screening has started (`UC005`).
* Fails with `409 invalid_booking_state` if already cancelled or expired (`UC006`).

### 11.5 Admin Movie Management (T7, admin, A-01)

**`GET /api/admin/movies`** returns all movies ordered by `movie_id ASC`.
* Answers `200 {"movies": [...]}`.
* Requires `Policy.ADMIN`.

**`GET /api/admin/movies/{id}`** returns a single movie.
* Answers `200 {"movie": {...}}`.
* Fails with `404` if movie does not exist.
* Requires `Policy.ADMIN`.

**`POST /api/admin/movies`** creates a new movie.
* Request body: `{"title": "...", "duration_minutes": 120, "genre": "...", "rating": "...", "synopsis": "...", "release_date": "YYYY-MM-DD"}`.
* `title` (1..200 chars) and `duration_minutes` (1..300 integer) are required.
* `genre` (text up to 100 chars, free text, D5) and `rating` (text up to 50 chars, free text, D5) are optional/nullable.
* `synopsis` (text) and `release_date` (exactly `YYYY-MM-DD`, a real date; `20261120` is refused) are optional/nullable.
* Text is trimmed; a blank optional value is stored as `null`.
* Answers `201 {"movie": {...}}`.
* Requires `Policy.ADMIN`.

**`PUT /api/admin/movies/{id}`** updates an existing movie.
* **Full replace:** the body is validated exactly like creation and every editable field is overwritten, so an optional field that is left out becomes `null`. Send all fields to keep them.
* A movie can be edited even when its screenings have bookings. Changing `duration_minutes` does **not** change the end time of screenings that already exist.
* Answers `200 {"movie": {...}}`.
* Fails with `404` if movie does not exist.
* Requires `Policy.ADMIN`.

### 11.6 Admin Screening Management (T7, admin, A-02)

**`GET /api/admin/screenings?movie_id=`** returns screenings (optionally filtered by movie) and the list of rooms.
* Sorted by `starts_at DESC, room_id ASC`.
* Each screening includes `has_started` (boolean) and `has_bookings` (boolean).
* Answers `200 {"screenings": [...], "rooms": [...]}`.
* Requires `Policy.ADMIN`.

**`GET /api/admin/screenings/{id}`** returns a single screening.
* Answers `200 {"screening": {...}}`.
* Fails with `404` if screening does not exist.
* Requires `Policy.ADMIN`.

**`POST /api/admin/screenings`** creates a new screening.
* Request body: `{"movie_id": 1, "room_id": 1, "starts_at": "...", "ends_at": "...", "ticket_price": "14000.00"}`.
* `movie_id`, `room_id` (positive integers of existing records; otherwise `400` with that field), `starts_at` (ISO 8601) and `ticket_price` are required.
* `ticket_price`: a number or a decimal string, `0` to `99999999.99` with at most two decimal places. Negative, non-finite (`Infinity`, `NaN`), too large or over-precise values are `400` with the field `ticket_price`. These are technical limits (`numeric(10,2)`), not business rules.
* `starts_at` / `ends_at`: ISO 8601. A time **without** an offset (for example `2030-01-05T10:00`, which is what a `datetime-local` input sends) is the cinema's local time (`APP_TIMEZONE`); a time with an offset keeps its instant. Responses always carry the cinema's offset. The year must be 1900–2200 (technical limit).
* `ends_at` is optional (if omitted, empty or null, calculated automatically as `starts_at + movie.duration_minutes`); if given it must be strictly after `starts_at`.
* Overlapping screenings in the same room fail with `409 screening_overlap` (`23P01`); a screening may start at the exact end time of the previous one (the end instant is not part of a screening).
* Answers `201 {"screening": {...}}`.
* Requires `Policy.ADMIN`.

**`PUT /api/admin/screenings/{id}`** updates an existing screening.
* Same body and validation as creation (full replace). If `ends_at` is omitted it is calculated again from the (possibly new) movie's duration.
* A screening that has already started (`starts_at` is not in the future, database clock) can no longer be edited: any `PUT` is rejected with `409 screening_has_started` ("This screening has already started and can't be edited."), even an identical save. This is checked first, so a started screening that also has bookings answers `screening_has_started`.
* Enforces **D2**: rejected with `409 screening_has_bookings` (`UC001`) if ANY booking references this screening, regardless of booking status (BOOKED, CANCELLED, or EXPIRED), **and** the save would change `movie_id`, `room_id`, `starts_at`, `ends_at` or `ticket_price`. Saving a booked screening with identical values is not a modification and answers `200`.
* Overlapping screenings in the same room fail with `409 screening_overlap` (`23P01`).
* Answers `200 {"screening": {...}}`.
* Fails with `404` if screening does not exist.
* Requires `Policy.ADMIN`.

### 11.7 Admin Booking List (T8, admin, A-03)

**`GET /api/admin/bookings?status=&screening_id=&user_id=`** view-only list of all bookings across all customers and statuses.
* Runs `expire_overdue_bookings()` in the same transaction before reading.
* Optional filters: `status` (`BOOKED`, `CANCELLED`, or `EXPIRED`; case-insensitive, blank means all), `screening_id`, `user_id` (positive whole numbers). Filters combine with AND; an unknown screening or customer gives an empty list; a bad value is `400` with that field in `fields`. Expiry changes made by the request are committed even though the endpoint only reads.
* Sorted by `booked_at DESC, booking_id DESC`.
* Each booking includes customer `username`, movie `title`, room `room_name`, times, amounts, and statuses (`status`, `payment_status`).
* `seats` list is included ONLY for `status == 'BOOKED'`. For cancelled and expired bookings, `seats` is empty `[]` (D1, D3).
* Answers `200 {"bookings": [...]}`.
* Requires `Policy.ADMIN`.

## 12. Planned endpoints (all Phase 4 endpoints implemented)

All Phase 4 planned endpoints (T1–T8) are implemented and documented in Section 11.

## 13. Deployment settings

| Process | Default port | Configuration (environment variables) |
|---|---|---|
| Frontend server | 8080 | `FRONTEND_HOST` (default `127.0.0.1`), `FRONTEND_PORT`, `API_BASE_URL` (the API address **as the browser reaches it**) |
| Backend API | 5000 | `flask --app app run --host … --port …` (or `FLASK_RUN_HOST` / `FLASK_RUN_PORT`); `SECRET_KEY`, `DB_*`, `CORS_ALLOWED_ORIGINS`, `AUTH_TOKEN_MAX_AGE_SECONDS`, `APP_TIMEZONE` |
| PostgreSQL | 5432 | Not changed by this work. Reachable from the API process only. |

Start (three independent terminals; any one can be stopped and started again alone):

```bash
python frontend/server.py                      # frontend, FRONTEND_PORT / API_BASE_URL from the environment
flask --app app run --port 5000                # API
# PostgreSQL: the existing database service
```

**One machine (tier 1).** Defaults work: frontend on `http://localhost:8080`, API on `http://localhost:5000`, `CORS_ALLOWED_ORIGINS=http://localhost:8080`, `API_BASE_URL=http://localhost:5000`. `localhost` and `127.0.0.1` are different origins: use the same spelling everywhere.

**Browser on another device (tier 2).** Let both servers listen on the network and give them the address the other device will use (example: the server machine is `192.168.0.10`):

```text
FRONTEND_HOST=0.0.0.0   FRONTEND_PORT=8080   API_BASE_URL=http://192.168.0.10:5000
flask --app app run --host 0.0.0.0 --port 5000
CORS_ALLOWED_ORIGINS=http://192.168.0.10:8080
```

The device then opens `http://192.168.0.10:8080`. The operating system's firewall must allow inbound connections on 8080 and 5000. **PostgreSQL stays local to the API and is never exposed to the other device.** This work changes no firewall rule and no PostgreSQL setting.

## 14. What is deliberately not here

No cookies or sessions, no CSRF tokens (nothing is sent automatically by the browser), no server-side token revocation, no rate limiting, no HTTPS termination (use a reverse proxy or a TLS-capable server for that), no refund, no delete endpoints. The remaining business endpoints are T4–T8.
