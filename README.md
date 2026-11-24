# Cinema Reservation System

Ứng dụng đặt vé cho một rạp chiếu phim. Khách có thể xem lịch chiếu, chọn ghế, đặt vé, thanh toán mô phỏng và xem hoặc hủy vé. Admin quản lý phim và suất chiếu, đồng thời tra cứu booking theo trạng thái, mã suất và mã khách hàng.

PostgreSQL giữ ghế trong 10 phút khi chờ thanh toán, lưu giá tại thời điểm đặt và ngăn hai khách giữ cùng một ghế. Admin có thể xóa suất tương lai chưa từng có booking. Xóa phim cũng xóa các suất đủ điều kiện của phim đó. Suất đã bắt đầu hoặc có lịch sử booking được bảo vệ.

| Thành phần | Công nghệ |
|---|---|
| Frontend | React, TypeScript, Vite |
| API | Python 3.12, Flask, psycopg2 |
| Database | PostgreSQL 18, SQL migrations, extension `btree_gist` |
| Kiểm thử | pytest, Node test runner, SQL, Playwright |
| Vận hành local | Docker Compose v2 hoặc chạy trực tiếp trên máy |

[Docker Compose](#chạy-bằng-docker-compose) · [Chạy trực tiếp](#chạy-trực-tiếp-trên-máy) · [Kiểm thử](#kiểm-thử) · [Khắc phục lỗi](#khắc-phục-lỗi-thường-gặp)

## Chạy bằng Docker Compose

Docker đóng gói sẵn Python, Node.js và PostgreSQL. Chạy các lệnh từ thư mục gốc chứa `docker-compose.yml`.

### 1. Cài và mở Docker Desktop

| Hệ điều hành | Cài đặt |
|---|---|
| macOS | Chọn bộ cài Apple Silicon hoặc Intel theo kiến trúc máy. Mở Docker Desktop và chờ engine sẵn sàng. [Docker Desktop cho macOS](https://docs.docker.com/desktop/setup/install/mac-install/) |
| Windows | Cài Docker Desktop với backend WSL 2 theo tài liệu chính thức. Mở Docker Desktop ở chế độ Linux containers và chạy lệnh bằng PowerShell. [Docker Desktop cho Windows](https://docs.docker.com/desktop/setup/install/windows-install/) |

Kiểm tra engine và Compose. Lệnh thứ hai phải in `linux`.

```sh
docker compose version
docker info --format '{{.OSType}}'
```

### 2. Cấu hình môi trường

Nếu chưa có `.env`, sao chép file mẫu.

**macOS — Terminal**

```sh
test -f .env || cp backend/.env.example .env
```

**Windows — PowerShell**

```powershell
if (-not (Test-Path -LiteralPath .env)) { Copy-Item backend/.env.example .env }
```

Với cấu hình mới, chạy lệnh sau để sinh `SECRET_KEY` và `DB_PASSWORD`. Lệnh chạy được trên cả macOS và Windows.

```sh
docker run --rm python:3.12-slim-bookworm python -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32)); print('DB_PASSWORD=' + secrets.token_hex(32))"
```

Mở `.env` bằng trình soạn thảo và điền hai giá trị vừa sinh vào các khóa tương ứng. Nếu dùng volume PostgreSQL đã khởi tạo, `DB_PASSWORD` cần khớp mật khẩu của role `cinema_api` trong volume đó. API Compose kết nối nội bộ tới `db:5432/cinema`.

### 3. Khởi động và nạp dữ liệu demo

Dùng cùng lệnh trên hai hệ điều hành.

```sh
docker compose up --build -d --wait
docker compose ps
```

Lần đầu Docker cần tải image và build. Compose áp schema và cấp quyền khi tạo volume trống. Khi các dịch vụ đã báo `healthy`, nếu database mới tạo và đang trống, nạp demo **một lần**.

```sh
docker compose exec -T db psql -X -v ON_ERROR_STOP=1 -U cinema_owner -d cinema -f /opt/cinema/demo.sql
```

Seed tạo 6 phim, 5 phòng, 250 ghế và 280 suất trong 14 ngày tính từ ngày nạp theo giờ Seoul. Khi các suất demo đã qua, tạo suất tương lai trong **Screenings (Admin)**.

### 4. Mở ứng dụng

| Địa chỉ | Dùng để |
|---|---|
| [http://localhost:8080](http://localhost:8080) | Mở giao diện |
| [Movies (Admin)](http://localhost:8080/admin-movies.html) | Quản lý phim |
| [Screenings (Admin)](http://localhost:8080/admin-screenings.html) | Quản lý suất chiếu |
| [All Bookings](http://localhost:8080/admin-bookings.html) | Tra cứu booking |
| [http://localhost:5000/health](http://localhost:5000/health) | Kiểm tra API đang phản hồi |
| [http://localhost:5000/health/db](http://localhost:5000/health/db) | Kiểm tra kết nối PostgreSQL |

| Tài khoản demo | Tên đăng nhập | Mật khẩu |
|---|---|---|
| Admin | `admin` | `admin1234` |
| Khách hàng | `customer1` hoặc `customer2` | `customer1234` |

Để thử luồng chính, đăng nhập khách hàng, chọn một suất tương lai, đặt ghế và thanh toán mô phỏng. Sau đó đăng nhập admin để tra cứu vé trong **All Bookings**.

### Lệnh hằng ngày

| Tác vụ | Lệnh |
|---|---|
| Build lại và khởi động sau khi sửa mã nguồn | `docker compose up --build -d --wait` |
| Áp dụng cấu hình `.env` mới | `docker compose up -d --wait` |
| Chỉ chạy API và database | `docker compose up -d --wait api` |
| Chỉ chạy frontend khi API đã có | `docker compose up -d --wait --no-deps frontend` |
| Theo dõi log | `docker compose logs -f api db frontend` |
| Kiểm tra đối tượng SQL cần thiết | `docker compose exec -T api python -m scripts.check_schema` |
| Dừng stack và giữ volume | `docker compose down` |

Với volume tạo trước chức năng **Delete**, áp dụng migration quyền để role runtime có thể xóa phim và suất. [Hướng dẫn PostgreSQL](database/README.md#quyền-xóa-phim-trên-database-hiện-hữu)

**Đổi cổng.** Ví dụ sau dùng cổng 8081 cho frontend và 5001 cho API. Đặt cả bốn dòng vào `.env`, chạy `docker compose up -d --wait` và mở `http://localhost:8081`.

```dotenv
FRONTEND_PORT=8081
API_PORT=5001
API_BASE_URL=http://localhost:5001
CORS_ALLOWED_ORIGINS=http://localhost:8081
```

**Truy cập từ mạng LAN.** Đặt `CINEMA_BIND_HOST=0.0.0.0`. Dùng IP LAN của máy chạy ứng dụng trong `API_BASE_URL` và `CORS_ALLOWED_ORIGINS` cùng các cổng tương ứng. Áp dụng cấu hình bằng `docker compose up -d --wait` rồi mở địa chỉ frontend từ thiết bị thứ hai. PostgreSQL Compose sử dụng mạng nội bộ.

## Chạy trực tiếp trên máy

Cách này chạy Flask và Vite trong hai terminal để có thể sửa mã và chạy lại từng dịch vụ. Dùng Python 3.12, Node.js 24 và PostgreSQL 18 như các image của dự án.

### macOS — cài công cụ

Cài Homebrew rồi chạy các lệnh sau trong Terminal. Có thể thêm dòng `export PATH` vào `.zshrc` để dùng Node.js và PostgreSQL trong các phiên sau. [Homebrew](https://brew.sh/) · [Python 3.12](https://formulae.brew.sh/formula/python@3.12) · [Node.js 24](https://formulae.brew.sh/formula/node@24) · [PostgreSQL 18](https://formulae.brew.sh/formula/postgresql@18)

```sh
brew install python@3.12 node@24 postgresql@18
export PATH="$(brew --prefix node@24)/bin:$(brew --prefix postgresql@18)/bin:$PATH"
brew services start postgresql@18

python3.12 --version
node --version
psql --version
pg_isready -h 127.0.0.1 -p 5432
```

### Windows — cài công cụ

1. Cài Python Install Manager, rồi chạy `py install 3.12` nếu máy chưa có Python 3.12. [Cài Python trên Windows](https://docs.python.org/3/using/windows.html#installing-runtimes)
2. Cài Node.js 24 bằng Windows Installer. Dùng `npm.cmd` trong PowerShell. [Node.js Downloads](https://nodejs.org/en/download)
3. Cài PostgreSQL 18, chọn **PostgreSQL Server** và **Command Line Tools**. Ghi nhớ mật khẩu tài khoản setup `postgres` và cổng đã chọn. Kiểm tra dịch vụ PostgreSQL đang chạy trong **Services**. [PostgreSQL Windows installers](https://www.postgresql.org/download/windows/)

Mở PowerShell mới. Nếu `psql` chưa có trong PATH, sửa đường dẫn dưới đây theo vị trí cài đặt.

```powershell
$env:Path = "C:\Program Files\PostgreSQL\18\bin;$env:Path"

py -3.12 --version
node --version
psql --version
pg_isready -h 127.0.0.1 -p 5432
```

### Chuẩn bị database và cấu hình

Ví dụ sau dành cho server local và **database mới** tên `cinema_demo`. Chạy `createdb` và baseline một lần từ root. Với database đã có dữ liệu, thực hiện backup, restore lên bản sao và đối chiếu schema trước khi kết nối ứng dụng. [Quy trình dùng database hiện hữu](database/README.md#database-đã-có-dữ-liệu)

**macOS — Terminal**

Với PostgreSQL mới cài bằng Homebrew, dùng role setup của tài khoản macOS hiện tại.

```sh
createdb cinema_demo
psql -X -v ON_ERROR_STOP=1 -d cinema_demo -f backend/migrations/0001_baseline.sql
psql -X -v ON_ERROR_STOP=1 -d cinema_demo -f backend/seeds/demo.sql
psql -X -v ON_ERROR_STOP=1 -d cinema_demo
```

**Windows — PowerShell**

Dùng tài khoản setup `postgres` và nhập mật khẩu khi được hỏi.

```powershell
createdb -h 127.0.0.1 -p 5432 -U postgres cinema_demo
psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 5432 -U postgres -d cinema_demo -f backend/migrations/0001_baseline.sql
psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 5432 -U postgres -d cinema_demo -f backend/seeds/demo.sql
psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 5432 -U postgres -d cinema_demo
```

Trong phiên `psql` vừa mở, cấp quyền cho role chạy API. `\password` hỏi mật khẩu hai lần. Nếu role `cinema_api` đã tồn tại, bắt đầu từ dòng `GRANT` và dùng mật khẩu đang có của role đó.

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

Nếu chưa có `.env`, dùng lệnh sao chép mẫu ở phần Docker. Điền `DB_PASSWORD` với mật khẩu đã đặt cho `cinema_api`. Sinh `SECRET_KEY` bằng `python3.12 -c "import secrets; print(secrets.token_hex(32))"` trên macOS hoặc `py -3.12 -c "import secrets; print(secrets.token_hex(32))"` trên Windows.

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

### Khởi động Flask và Vite

Nếu đang chạy stack Compose ở cổng 5000 hoặc 8080, dừng stack trước khi dùng cùng cổng cho Flask và Vite. Mở hai terminal tại root.

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

Mở [http://localhost:8080](http://localhost:8080). Vite phục vụ `/config.js` theo `API_BASE_URL` trong `.env` ở root. Dùng `Ctrl+C` trong từng terminal để dừng Flask hoặc Vite.

**Thử bản build.** Dừng Vite để giải phóng cổng 8080. Từ root, chạy `npm --prefix frontend run build` rồi `.venv/bin/python frontend/server.py` trên macOS. Trên Windows, chạy `npm.cmd --prefix frontend run build` rồi `.\.venv\Scripts\python.exe frontend/server.py`. Static server đọc `API_BASE_URL`, `FRONTEND_HOST` và `FRONTEND_PORT` từ môi trường tiến trình. Để thử giao diện HTML dự phòng, build bằng `build:legacy` rồi đặt `CINEMA_LEGACY_UI=1` cho tiến trình frontend.

## Kiểm thử

### Chạy toàn bộ trên macOS hoặc Windows

Chạy từ root với Docker Desktop đang mở.

```sh
docker compose --profile test run --build --rm verify
docker compose --profile test stop test-db
```

Runner build frontend và chạy pytest, JavaScript unit test, SQL integrity, reconciliation, kiểm tra đặt ghế đồng thời và các luồng Playwright qua API thật. Profile `test` tự cấp PostgreSQL riêng trên mạng nội bộ `verification`. Mã thoát `0` cho biết toàn bộ bộ kiểm thử đã đạt. Lệnh thứ hai dừng riêng PostgreSQL test.

### Chạy nhanh unit test frontend

| macOS | Windows PowerShell |
|---|---|
| `npm --prefix frontend ci` | `npm.cmd --prefix frontend ci` |
| `npm --prefix frontend test` | `npm.cmd --prefix frontend test` |

Chạy `ci` khi mới checkout hoặc khi lockfile thay đổi.

### Debug test trực tiếp

Dành cho máy đã chuẩn bị Python, Node.js, `psql` và PostgreSQL test riêng. Đặt `TEST_DB_HOST`, `TEST_DB_PORT`, `TEST_DB_ADMIN_USER` và `TEST_DB_ADMIN_PASSWORD` theo server test. `TEST_DB_PORT` là biến bắt buộc. Role test cần quyền tạo database, extension và role tạm.

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

Chạy riêng pytest bằng `-m pytest -ra backend/tests`, bộ SQL bằng `backend/tests/run_database.py`, hoặc Playwright bằng `backend/tests/run_browser.py` với interpreter của venv. Trước khi chạy pytest hoặc Playwright riêng, chuẩn bị bản build bằng `npm run build` và `npm run build:legacy` trong `frontend/`. [Chi tiết các ca kiểm thử PostgreSQL](docs/database/database_test_documentation.md)

## Khắc phục lỗi thường gặp

| Triệu chứng | Cách kiểm tra |
|---|---|
| Docker không kết nối được engine | Mở Docker Desktop và chạy lại `docker info --format '{{.OSType}}'`. Trên Windows, kiểm tra chế độ Linux containers. |
| Database dừng với `Set DB_PASSWORD in the project .env` | Điền `DB_PASSWORD` tại root và chạy lại lệnh khởi động. Xem `docker compose logs --tail 80 db api` để biết lỗi còn lại. |
| API báo sai mật khẩu sau khi đổi `.env` | Dùng lại mật khẩu PostgreSQL của volume hoặc đổi mật khẩu role `cinema_api` trong PostgreSQL rồi cập nhật `.env`. |
| Giao diện mở nhưng phim không tải | Mở `/health/db` của API. Sau đó đối chiếu `API_BASE_URL` với địa chỉ API và `CORS_ALLOWED_ORIGINS` với origin frontend đang mở. |
| Cổng 5000 hoặc 8080 đang được dùng | Với Compose, dùng cấu hình đổi cổng ở trên. Khi chạy trực tiếp, chỉnh `--port` của Flask hoặc chạy `npm exec -- vite --host 127.0.0.1 --port 8081` từ `frontend/` với `npm.cmd` trên Windows. Cập nhật các origin tương ứng. |
| Seed từ chối vì database đã có dữ liệu | Dùng dữ liệu hiện có hoặc thêm suất trong **Screenings (Admin)**. Seed cần schema đã khởi tạo và các bảng nghiệp vụ còn trống. |
| Bản cập nhật báo lỗi khi dùng **Delete** trên volume cũ | Cấp quyền cho role runtime theo migration. [Hướng dẫn PostgreSQL](database/README.md#quyền-xóa-phim-trên-database-hiện-hữu) |

## Cấu trúc dự án

```text
backend/
  app/          Flask factory, API, cấu hình, validation và nghiệp vụ
  migrations/   Schema PostgreSQL và quyền truy cập của role ứng dụng
  seeds/        Dữ liệu demo
  scripts/      Công cụ setup và kiểm tra schema
  tests/        Pytest, SQL, kiểm tra đồng thời và trình chạy Playwright
frontend/
  src/          React pages, components và features
  public/       Poster, font và giấy phép font
  js/           Module JavaScript dùng chung
  legacy/       Giao diện HTML dự phòng
  tests/        Unit test frontend
  e2e/          Kiểm thử trình duyệt
database/       Hướng dẫn PostgreSQL
docs/           Hợp đồng API, mô hình dữ liệu và quy tắc nghiệp vụ
docker-compose.yml
```

[Hợp đồng REST API](docs/api/api_contract.md) · [Quy tắc nghiệp vụ](docs/business/business_rules_decision_log.md) · [Mô hình dữ liệu](docs/database/physical_data_model.md) · [Hợp đồng PostgreSQL–Flask](docs/database/postgresql_flask_integration_contract.md) · [Tiến độ migration](docs/project/Project_progress.md)
