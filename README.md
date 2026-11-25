# Cinema Reservation System

A ticket booking application for a single cinema. Customers can browse showtimes, select seats, book tickets, complete simulated payments, and view or cancel tickets. Admins manage movies and showtimes, and look up bookings by status, showtime ID, and customer ID.

PostgreSQL holds seats for 10 minutes while awaiting payment, stores the price at the time of booking, and prevents two customers from holding the same seat. Admins can delete future showtimes that have never had a booking. Deleting a movie also deletes eligible showtimes for that movie. Showtimes that have already started or have booking history are protected.

| Component | Technology |
|---|---|
| Frontend | React, TypeScript, Vite |
| API | Python 3.12, Flask, psycopg2 |
| Database | PostgreSQL 18, SQL migrations, `btree_gist` extension |
| Testing | pytest, Node test runner, SQL, Playwright |
| Local operation | Docker Compose v2 or running directly on the host |

[Docker Compose](#run-with-docker-compose) · [Run Directly](#run-directly-on-the-host) · [Testing](#testing) · [Troubleshooting](#troubleshooting)

## Run with Docker Compose

Docker bundles Python, Node.js, and PostgreSQL. Run all commands from the root directory containing `docker-compose.yml`.

### 1. Install and open Docker Desktop

| Operating System | Installation |
|---|---|
| macOS | Choose the Apple Silicon or Intel installer matching your machine's architecture. Open Docker Desktop and wait for the engine to be ready. [Docker Desktop for macOS](https://docs.docker.com/desktop/setup/install/mac-install/) |
| Windows | Install Docker Desktop with the WSL 2 backend according to the official documentation. Open Docker Desktop in Linux containers mode and run commands using PowerShell. [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/) |

Verify the engine and Compose. The second command must print `linux`.

```sh
docker compose version
docker info --format '{{.OSType}}'
```


### 2. Configure environment

If `.env` does not exist yet, copy the example file.

**macOS — Terminal**

```sh
test -f .env || cp backend/.env.example .env
```

**Windows — PowerShell**

```powershell
if (-not (Test-Path -LiteralPath .env)) { Copy-Item backend/.env.example .env }
```

For a new setup, run the following command to generate `SECRET_KEY` and `DB_PASSWORD`. This command works on both macOS and Windows.

```sh
docker run --rm python:3.12-slim-trixie python -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32)); print('DB_PASSWORD=' + secrets.token_hex(32))"
```

Open `.env` in an editor and fill in the two generated values for their corresponding keys. If using an already initialized PostgreSQL volume, `DB_PASSWORD` must match the password of the `cinema_api` role in that volume. The Compose API connects internally to `db:5432/cinema`.

### 3. Start and load demo data

Use the same commands on both operating systems.

```sh
docker compose up --build -d --wait
docker compose ps
```

On the first run, Docker needs to pull images and build. Compose applies the schema and grants permissions when creating an empty volume. Once all services report `healthy`, if the database was newly created and is empty, load the demo data **once**.

```sh
docker compose exec -T db psql -X -v ON_ERROR_STOP=1 -U cinema_owner -d cinema -f /opt/cinema/demo.sql
```

The seed creates 6 movies, 5 rooms, 250 seats, and 280 showtimes over 14 days starting from the load date in Seoul time. Once the demo showtimes have passed, create future showtimes in **Screenings (Admin)**.

### 4. Open the application

| Address | Purpose |
|---|---|
| [http://localhost:8080](http://localhost:8080) | Open the UI |
| [Movies (Admin)](http://localhost:8080/admin-movies.html) | Manage movies |
| [Screenings (Admin)](http://localhost:8080/admin-screenings.html) | Manage showtimes |
| [All Bookings](http://localhost:8080/admin-bookings.html) | Look up bookings |
| [http://localhost:5000/health](http://localhost:5000/health) | Check if the API is responding |
| [http://localhost:5000/health/db](http://localhost:5000/health/db) | Check PostgreSQL connection |

| Demo account | Username | Password |
|---|---|---|
| Admin | `admin` | `admin1234` |
| Customer | `customer1` or `customer2` | `customer1234` |

To test the main flow, log in as a customer, select a future showtime, book seats, and complete the simulated payment. Then log in as admin to look up the ticket in **All Bookings**.

### Daily commands

| Task | Command |
|---|---|
| Rebuild and start after editing source code | `docker compose up --build -d --wait` |
| Apply new `.env` configuration | `docker compose up -d --wait` |
| Run only the API and database | `docker compose up -d --wait api` |
| Run only the frontend when the API is already up | `docker compose up -d --wait --no-deps frontend` |
| Follow logs | `docker compose logs -f api db frontend` |
| Verify required SQL objects | `docker compose exec -T api python -m scripts.check_schema` |
| Stop stack and keep volumes | `docker compose down` |

For volumes created before the **Delete** feature, apply the permission migration so the runtime role can delete movies and showtimes. Existing volumes also require migrations 0003 and 0004. See the [booking integrity upgrade](database/README.md#nâng-cấp-toàn-vẹn-booking-0003). [PostgreSQL Guide](database/README.md#quyền-xóa-phim-trên-database-hiện-hữu)

**Change ports.** The example below uses port 8081 for the frontend and 5001 for the API. Put all four lines in `.env`, run `docker compose up -d --wait`, and open `http://localhost:8081`.

```dotenv
FRONTEND_PORT=8081
API_PORT=5001
API_BASE_URL=http://localhost:5001
CORS_ALLOWED_ORIGINS=http://localhost:8081
```

**Access from LAN.** Set `CINEMA_BIND_HOST=0.0.0.0`. Use the LAN IP of the host machine in `API_BASE_URL` and `CORS_ALLOWED_ORIGINS` with the corresponding ports. Apply the configuration with `docker compose up -d --wait`, then open the frontend address from a second device. Compose PostgreSQL uses the internal network.

## Run Directly on the Host

This approach runs Flask and Vite in two terminals so you can edit code and restart each service individually. Use Python 3.12, Node.js 24, and PostgreSQL 18, matching the project images.

### macOS — install tools

Install Homebrew and run the following commands in Terminal. You can add the `export PATH` line to `.zshrc` to use Node.js and PostgreSQL in future sessions. [Homebrew](https://brew.sh/) · [Python 3.12](https://formulae.brew.sh/formula/python@3.12) · [Node.js 24](https://formulae.brew.sh/formula/node@24) · [PostgreSQL 18](https://formulae.brew.sh/formula/postgresql@18)

```sh
brew install python@3.12 node@24 postgresql@18
export PATH="$(brew --prefix node@24)/bin:$(brew --prefix postgresql@18)/bin:$PATH"
brew services start postgresql@18

python3.12 --version
node --version
psql --version
pg_isready -h 127.0.0.1 -p 5432
```

### Windows — install tools

1. Install Python Install Manager, then run `py install 3.12` if the machine does not have Python 3.12 yet. [Install Python on Windows](https://docs.python.org/3/using/windows.html#installing-runtimes)
2. Install Node.js 24 using the Windows Installer. Use `npm.cmd` in PowerShell. [Node.js Downloads](https://nodejs.org/en/download)
3. Install PostgreSQL 18, selecting **PostgreSQL Server** and **Command Line Tools**. Note the `postgres` setup account password and chosen port. Verify the PostgreSQL service is running in **Services**. [PostgreSQL Windows installers](https://www.postgresql.org/download/windows/)

Open a new PowerShell window. If `psql` is not in PATH yet, adjust the path below to match your installation location.

```powershell
$env:Path = "C:\Program Files\PostgreSQL\18\bin;$env:Path"

py -3.12 --version
node --version
psql --version
pg_isready -h 127.0.0.1 -p 5432
```

### Prepare database and configuration

The following example is for a local server and a **new database** named `cinema_demo`. Run `createdb` and apply migrations 0001, 0003 and 0004 before seeding. For a database that already contains data, perform a backup, restore onto a copy, and compare schemas before connecting the application. [Workflow for an existing database](database/README.md#database-đã-có-dữ-liệu)

**macOS — Terminal**

With PostgreSQL freshly installed via Homebrew, use the setup role of the current macOS account.

```sh
createdb cinema_demo
psql -X -v ON_ERROR_STOP=1 -d cinema_demo -f backend/migrations/0001_baseline.sql
psql -X -v ON_ERROR_STOP=1 -d cinema_demo -f backend/migrations/0003_booking_integrity.sql
psql -X -v ON_ERROR_STOP=1 -d cinema_demo -f backend/migrations/0004_finite_money.sql
psql -X -v ON_ERROR_STOP=1 -d cinema_demo -f backend/seeds/demo.sql
psql -X -v ON_ERROR_STOP=1 -d cinema_demo
```

**Windows — PowerShell**

Use the `postgres` setup account and enter the password when prompted.

```powershell
createdb -h 127.0.0.1 -p 5432 -U postgres cinema_demo
psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 5432 -U postgres -d cinema_demo -f backend/migrations/0001_baseline.sql
psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 5432 -U postgres -d cinema_demo -f backend/migrations/0003_booking_integrity.sql
psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 5432 -U postgres -d cinema_demo -f backend/migrations/0004_finite_money.sql
psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 5432 -U postgres -d cinema_demo -f backend/seeds/demo.sql
psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 5432 -U postgres -d cinema_demo
```

In the `psql` session just opened, grant permissions to the API runtime role. `\password` prompts for the password twice. If the `cinema_api` role already exists, start from the `GRANT` lines and use that role's existing password.

```sql
CREATE ROLE cinema_api LOGIN;
\password cinema_api

GRANT USAGE ON SCHEMA public TO cinema_api;
GRANT SELECT ON users, movies, theater_rooms, seats, showtimes, bookings, booking_seats TO cinema_api;
GRANT INSERT ON users TO cinema_api;
GRANT INSERT, UPDATE ON movies, showtimes, bookings TO cinema_api;
GRANT INSERT, DELETE ON booking_seats TO cinema_api;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO cinema_api;
\i backend/migrations/0002_movie_delete_permissions.sql
\q
```

If `.env` does not exist yet, use the copy command from the Docker section. Fill in `DB_PASSWORD` with the password set for `cinema_api`. Generate `SECRET_KEY` using `python3.12 -c "import secrets; print(secrets.token_hex(32))"` on macOS or `py -3.12 -c "import secrets; print(secrets.token_hex(32))"` on Windows.

```dotenv
SECRET_KEY=
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=cinema_demo
DB_USER=cinema_api
DB_PASSWORD=
API_BASE_URL=http://localhost:5000
CORS_ALLOWED_ORIGINS=http://localhost:8080
APP_TIMEZONE=Asia/Seoul
```

### Start Flask and Vite

If the Compose stack is running on port 5000 or 8080, stop the stack before using the same ports for Flask and Vite. Open two terminals at the root.

**macOS — Terminal 1, Flask**

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
cd backend
../.venv/bin/python -m scripts.check_schema
../.venv/bin/python -m flask --app app.main:create_app run --debug --host 127.0.0.1 --port 5000
```

**macOS — Terminal 2, Vite**

```sh
export PATH="$(brew --prefix node@24)/bin:$PATH"
npm --prefix frontend ci
npm --prefix frontend run dev
```

**Windows — PowerShell 1, Flask**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
Set-Location backend
..\.venv\Scripts\python.exe -m scripts.check_schema
..\.venv\Scripts\python.exe -m flask --app app.main:create_app run --debug --host 127.0.0.1 --port 5000
```

**Windows — PowerShell 2, Vite**

```powershell
npm.cmd --prefix frontend ci
npm.cmd --prefix frontend run dev
```

Open [http://localhost:8080](http://localhost:8080). Vite serves `/config.js` based on `API_BASE_URL` in the root `.env`. Use `Ctrl+C` in each terminal to stop Flask or Vite.

**Test the production build.** Stop Vite to free port 8080. From the root, run `npm --prefix frontend run build` followed by `.venv/bin/python frontend/server.py` on macOS. On Windows, run `npm.cmd --prefix frontend run build` followed by `.\.venv\Scripts\python.exe frontend/server.py`. The static server reads `API_BASE_URL`, `FRONTEND_HOST`, and `FRONTEND_PORT` from the process environment. To test the fallback HTML UI, build with `build:legacy` and set `CINEMA_LEGACY_UI=1` for the frontend process.

## Testing

### Run full suite on macOS or Windows

Run from the root with Docker Desktop open.

```sh
docker compose --profile test run --build --rm verify
docker compose --profile test stop test-db
```

The runner builds the frontend and executes pytest, JavaScript unit tests, SQL integrity, reconciliation, concurrent seat booking checks, and Playwright flows against the real API. The `test` profile provisions its own PostgreSQL instance on the internal `verification` network. An exit code of `0` indicates the entire test suite passed. The second command stops only the test PostgreSQL container.

### Quick frontend unit test run

| macOS | Windows PowerShell |
|---|---|
| `npm --prefix frontend ci` | `npm.cmd --prefix frontend ci` |
| `npm --prefix frontend test` | `npm.cmd --prefix frontend test` |

Run `ci` on a fresh checkout or whenever the lockfile changes.

### Debug tests directly

For machines with Python, Node.js, `psql`, and a dedicated test PostgreSQL instance prepared. Set `TEST_DB_HOST`, `TEST_DB_PORT`, `TEST_DB_ADMIN_USER`, and `TEST_DB_ADMIN_PASSWORD` according to your test server. `TEST_DB_PORT` is required. The test role needs permissions to create databases, extensions, and temporary roles.

**macOS — Terminal**

```sh
npm --prefix frontend ci
(cd frontend && npm exec -- playwright install chromium)
.venv/bin/python backend/tests/verify.py
```

**Windows — PowerShell**

```powershell
npm.cmd --prefix frontend ci
Push-Location frontend
npm.cmd exec -- playwright install chromium
Pop-Location
.\.venv\Scripts\python.exe backend/tests/verify.py
```

Run pytest individually with `-m pytest -ra backend/tests`, the SQL suite with `backend/tests/run_database.py`, or Playwright with `backend/tests/run_browser.py` using the venv interpreter. Before running pytest or Playwright individually, prepare the builds with `npm run build` and `npm run build:legacy` inside `frontend/`. [PostgreSQL test case details](docs/database/database_test_documentation.md)

## Troubleshooting

| Symptom | How to check |
|---|---|
| Docker cannot connect to the engine | Open Docker Desktop and re-run `docker info --format '{{.OSType}}'`. On Windows, check Linux containers mode. |
| Database stops with `Set DB_PASSWORD in the project .env` | Fill in `DB_PASSWORD` at the root and re-run the start command. Check `docker compose logs --tail 80 db api` for any remaining errors. |
| API reports wrong password after changing `.env` | Reuse the PostgreSQL password from the volume or change the `cinema_api` role password in PostgreSQL and update `.env`. |
| UI opens but movies do not load | Open the API's `/health/db`. Then compare `API_BASE_URL` with the API address and `CORS_ALLOWED_ORIGINS` with the frontend origin being opened. |
| Port 5000 or 8080 is already in use | With Compose, use the port-change configuration above. When running directly, adjust Flask's `--port` or run `npm exec -- vite --host 127.0.0.1 --port 8081` from `frontend/` using `npm.cmd` on Windows. Update the corresponding origins. |
| Seed refuses because the database already has data | Use the existing data or add showtimes in **Screenings (Admin)**. The seed requires an initialized schema and empty business tables. |
| Update reports an error when using **Delete** on an old volume | Grant permissions to the runtime role according to the migration. [PostgreSQL Guide](database/README.md#quyền-xóa-phim-trên-database-hiện-hữu) |

## Project Structure

```text
backend/
  app/          Flask factory, API, configuration, validation, and business logic
  migrations/   PostgreSQL schema and application role permissions
  seeds/        Demo data
  scripts/      Setup tools and schema verification
  tests/        Pytest, SQL, concurrency checks, and Playwright runner
frontend/
  src/          React pages, components, and features
  public/       Posters, fonts, and font licenses
  js/           Shared JavaScript modules
  legacy/       Fallback HTML UI
  tests/        Frontend unit tests
  e2e/          Browser tests
database/       PostgreSQL guide
docs/           API contract, data model, and business rules
docker-compose.yml
```

[REST API Contract](docs/api/api_contract.md) · [Business Rules](docs/business/business_rules_decision_log.md) · [Physical Data Model](docs/database/physical_data_model.md) · [PostgreSQL–Flask Integration Contract](docs/database/postgresql_flask_integration_contract.md) · [Migration Progress](docs/project/Project_progress.md)
