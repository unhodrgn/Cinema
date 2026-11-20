# database/ — canonical PostgreSQL database

Status: **verified** against D1–D6 on PostgreSQL 18.6 (see `docs/database/database_test_documentation.md`). Not yet tested on PostgreSQL 14–17.

| File | Purpose |
|---|---|
| `schema.sql` | Canonical schema: 7 tables, constraints, triggers, 4 operations for Flask. Apply **once** to a new empty database. Needs the `btree_gist` extension. |
| `seed.sql` | Canonical seed (demo data): 3 accounts, 5 movies, 5 rooms, 250 seats, 140 screenings over 7 `Asia/Seoul` days from the day it runs. Apply after `schema.sql`, once. |
| `tests/run_all.sh` | Creates a disposable database, runs everything below, drops it. |
| `tests/integrity_tests.sql` | 177 checks for D1–D6 and retained rules (rolled back). |
| `tests/reconciliation_probes.sql` | 31 probes keyed to the audit's P-numbers (rolled back; fails on any mismatch). |
| `tests/test_concurrency.py` | Real multi-session race tests (psycopg2). Needs a fresh DB with no bookings. |

`CinemaDB_FINAL_PostgreSQL_Handover/` (Member A's delivery) is kept **unchanged** as the historical reference. `schema.sql` and `seed.sql` here are derived from it and corrected as documented in `docs/database/handover_reconciliation_report.md`; do not edit the handover folder or maintain a second schema.

## Setup

```bash
createdb cinema_demo                                   # new, empty database
psql -X -v ON_ERROR_STOP=1 -d cinema_demo -f database/schema.sql
psql -X -v ON_ERROR_STOP=1 -d cinema_demo -f database/seed.sql
```
Connection via the libpq variables (`PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`). Never commit credentials.

## Verify (disposable database only)

```bash
python -m pip install psycopg2-binary
bash database/tests/run_all.sh
```
Never run the tests or the seed against a shared or demo database: the concurrency test leaves bookings behind, and (D2) a screening that has any booking record can never be edited again.

## For Flask

Read `docs/database/postgresql_flask_integration_contract.md`. In short: call `create_booking`, `pay_booking`, `cancel_booking` and `expire_overdue_bookings()` (request-time expiry; nothing runs automatically); use physical table names; handle the `UC…` SQLSTATEs.

## Open items

* Demo account password hashes come from Member A; their plaintext is undocumented and unverified.
* Database driver choice (`psycopg2` recommended) and `requirements.txt` are not settled; `requirements.txt` is unchanged.
* Application-role privileges / `SECURITY DEFINER` is a deployment decision, not implemented.
