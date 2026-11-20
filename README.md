# Cinema Reservation System

**영화관 예매 및 좌석 관리 시스템** — a web-based cinema booking system where visitors browse movies and screenings, pick seats, book, pay (simulated) and cancel, and administrators manage movies and screenings.

This is a team database-design project (Member A: database, Member B: application). Its focus is a **PostgreSQL database that enforces the booking rules itself** — no double-booked seats, no overlapping screenings, protected booking history — with a Flask web application on top.

> **Project status**
> | Layer | Status |
> |---|---|
> | Business analysis (B01–B05, decisions D1–D6) | Done |
> | PostgreSQL database (schema, seed data, tests, documentation) | **Implemented and verified**; awaiting Member A's review |
> | Flask application and web frontend | **Not started** — `app/` contains empty placeholder files only |
>
> See [PROJECT_PROGRESS.md](PROJECT_PROGRESS.md) for the detailed checklist.

---

## 1. Project Overview

One cinema, 5 screening rooms of 50 seats each (250 seats), 5 sample movies and 140 sample screenings over 7 consecutive days. Two account roles exist: `CUSTOMER` and `ADMIN`. Browsing needs no login; booking requires a customer login. Payment is simulated (no payment gateway).

## 2. Features

| Area | Feature | Status |
|---|---|---|
| **Database** | Seats, screenings, bookings, price snapshots and booking history modelled in 7 tables | Implemented |
| | One active booking per seat per screening (race-safe), seats must belong to the screening's room | Implemented |
| | No overlapping screenings in a room; screenings with any booking record cannot be modified | Implemented |
| | Booking statuses `BOOKED` / `CANCELLED` / `EXPIRED`, payment statuses `UNPAID` / `PAID`, 10-minute payment window | Implemented |
| | Atomic operations: create booking, pay, cancel, expire overdue bookings | Implemented |
| **Customer** | Register, log in / out | Planned |
| | Browse movies, screenings and seat availability (no login) | Planned |
| | Select seats, confirm a booking, pay (simulated) | Planned |
| | View booking history, cancel a booking before the screening starts | Planned |
| **Admin** | Add / edit movies and screenings, view all bookings | Planned |

"Implemented" means verified by the database tests below. "Planned" features are specified in the business documents but have no code yet.

## 3. Technology Stack

| Component | Technology | State |
|---|---|---|
| Language | Python | Selected (no application code yet) |
| Web framework | Flask | Selected (not yet implemented) |
| Database | **PostgreSQL 14+** (tested on 18.6; extension `btree_gist` required) | In use |
| DB driver | `psycopg2` is used by the database tests; the application driver (`psycopg2` or SQLAlchemy) is **not yet decided** | Open |
| Frontend | HTML, CSS, Bootstrap, JavaScript | Selected (templates are empty placeholders) |

## 4. Project Structure

```text
.
├── database/
│   ├── schema.sql        # PostgreSQL schema: tables, constraints, triggers, booking functions
│   ├── seed.sql          # Demo data: 3 accounts, 5 movies, 5 rooms, 250 seats, 140 screenings
│   ├── README.md         # Database setup and safety notes
│   └── tests/            # Integrity, reconciliation and concurrency tests + runner script
├── docs/
│   ├── business/         # Approved business requirements (B01–B05, decision log D1–D6)
│   └── database/         # Data models, glossary, Flask integration contract, test documentation
├── app/                  # Flask application skeleton (empty placeholder files, not implemented)
├── presentation/         # Presentation material (placeholder)
├── tests/                # Application tests (placeholder)
├── PROJECT_PROGRESS.md   # Project checklist and progress log
├── chia_viec.md          # Task division and schedule (Vietnamese)
├── important.md          # Course presentation requirements (Korean)
└── requirements.txt      # Python dependencies (currently empty)
```

`database/` and `docs/database/` are the source of truth for the database. Member A's original handover (an earlier, non-conforming model, audited in the reconciliation report linked below) is no longer part of the repository and must not be used for development.

## 5. Database Overview

PostgreSQL holds the business rules, not just the data.

* **Tables:** `users`, `movies`, `theater_rooms`, `seats`, `showtimes`, `bookings`, `booking_seats`.
* **Rules enforced in the database:** seat/room ownership, no double booking, no screening overlap, screening protection once booked, booking/payment state transitions, price snapshot and total consistency, history kept after cancellation or expiry.
* **Operations for the application:** `create_booking`, `pay_booking`, `cancel_booking`, `expire_overdue_bookings` (expiry runs when called; nothing is scheduled).
* **Details:** [table description](docs/database/table_description.md) · [physical model with ERD](docs/database/physical_data_model.md) · [Flask integration contract](docs/database/postgresql_flask_integration_contract.md).

## 6. Installation & Setup

Only the database can be set up and run today; there is no application to start yet.

**Requirements:** PostgreSQL 14 or newer (including `psql` and `createdb`, and the `btree_gist` extension, which is part of the standard PostgreSQL distribution; some Linux distributions package it separately as `postgresql-contrib`) and a PostgreSQL role that can create databases.

Connection settings come from the standard libpq environment variables (`PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`). Do not commit credentials.

Create the database (new, empty database; apply each script once):

```bash
createdb cinema_demo
psql -X -v ON_ERROR_STOP=1 -d cinema_demo -f database/schema.sql
psql -X -v ON_ERROR_STOP=1 -d cinema_demo -f database/seed.sql
```

Notes:

* The seed creates screenings for 7 days starting on the day it is run (`Asia/Seoul`).
* The three demo accounts (`admin_demo`, `customer_demo`, `customer_demo2`) keep password hashes from Member A; **their plaintext passwords are not documented**. Set known passwords before demonstrating a login.
* Python dependencies: none for the application yet (`requirements.txt` is empty). Only the concurrency test needs `psycopg2-binary` (see Testing).

## 7. Testing

The database tests run against a **disposable** database. Never run them against a shared or demo database: the concurrency test leaves bookings behind, and a screening with any booking can no longer be modified.

```bash
python -m pip install psycopg2-binary     # needed by test_concurrency.py
bash database/tests/run_all.sh            # needs bash (e.g. Git Bash on Windows)
```

`run_all.sh` creates a uniquely named database, applies the schema and seed, runs all tests, and drops only that database (`KEEP_DB=1` keeps it). The connecting role needs `CREATEDB` and must own the database it creates.

| Test | File | Content |
|---|---|---|
| Integrity | `database/tests/integrity_tests.sql` | 177 checks covering decisions D1–D6 and the core booking rules |
| Reconciliation probes | `database/tests/reconciliation_probes.sql` | 31 probes against the approved requirements |
| Concurrency | `database/tests/test_concurrency.py` | 16 checks with real parallel sessions |

At the last verification (PostgreSQL 18.6) all of them passed. There are no application tests yet. How to run the tests step by step and their detailed coverage: [database test documentation](docs/database/database_test_documentation.md).

## 8. Documentation

**Business (approved requirements)** — [`docs/business/`](docs/business/)

* [Project overview](docs/business/project_overview.md)
* [Business functions](docs/business/business_function.md)
* [Unit business descriptions](docs/business/unit_business_description.md)
* [Business flowcharts](docs/business/business_flowchart.md)
* [Business document list](docs/business/business_document_list.md)
* [Business rules decision log (D1–D6)](docs/business/business_rules_decision_log.md)

**Database** — [`docs/database/`](docs/database/)

* [PostgreSQL ↔ Flask integration contract](docs/database/postgresql_flask_integration_contract.md) — start here for application development
* [Conceptual](docs/database/conceptual_data_model.md), [logical](docs/database/logical_data_model.md) and [physical](docs/database/physical_data_model.md) data models (with ERDs)
* [Table description](docs/database/table_description.md), [domain definition](docs/database/domain_definition.md), [glossary](docs/database/glossary.md), [normalization](docs/database/normalization.md)
* [Database test documentation](docs/database/database_test_documentation.md)
* [Handover reconciliation report](docs/database/handover_reconciliation_report.md) — audit of the original handover and how it was corrected
* [Database README](database/README.md)

**Project management** — [Progress checklist](PROJECT_PROGRESS.md)
