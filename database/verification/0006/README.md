# Migration 0006 verification

Results are from disposable PostgreSQL 18 instances. The upgrade log records the expected refusal with invalid rows and the successful migration after guarded cleanup on an isolated restore. It contains no account rows or database credentials. See the upgrade procedure in the [database runbook](../../README.md).

- Run the full verification on a separate Compose project with `docker compose --profile test run --build --rm verify`. It builds React and legacy assets and runs pytest, SQL, concurrency and Chromium regressions.
- The 28-row CSV corresponds to `USERNAME_CASES` in `backend/tests/test_auth_api.py`. For a targeted run, use `python -m pytest backend/tests/test_auth_api.py -k 'username_matrix or simultaneous_registrations'` with the isolated test database configured.
- To repeat the focused legacy smoke, temporarily copy `legacy-username.spec.ts` into `frontend/e2e/` in a disposable checkout, set `CINEMA_LEGACY_UI=1` for `backend/tests/run_browser.py` and pass the test filename to the Playwright CLI in the disposable runner. Build `dist-legacy` first, as described in the root README.
- The demo restore output columns are target database, users, movies, rooms, seats, screenings, bookings and validated username CHECK count. [Dump generation](../../dump/README.md) · [Model generation](../../model/README.md)
