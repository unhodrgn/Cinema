# Cinema Reservation System — Tiến độ chuyển đổi

**24/11/2026 · Đã triển khai trên working tree.** Mốc đối chiếu là commit `c6a17d4`. Nhật ký trước migration nằm trong [PROJECT_PROGRESS.md](../../PROJECT_PROGRESS.md). Lệnh vận hành và cấu hình hiện hành nằm trong [README](../../README.md).

## Các giai đoạn đã duyệt

| Giai đoạn | Phần đã triển khai | Kiểm chứng |
|---|---|---|
| 0 · Lập baseline | Kiểm tra Git và chạy bản gốc từ archive trên PostgreSQL riêng. Python 3.12.10, Node 26.9.0, PostgreSQL 18.6 trên Windows. | Pytest gốc đạt 1.350, lỗi 4, skip 2. Ba test bỏ port trong subprocess vẫn đọc cấu hình từ dotenv. Test thứ tư thiếu mật khẩu cho role thử nên dừng ở xác thực trước khi kiểm tra quyền UPDATE. |
| 1 · Di chuyển Flask | Factory tại `backend/app/main.py`, cấu hình local đọc `.env` tại root. Requirements, công cụ setup và test theo backend. | Khởi động API qua Flask factory. Kiểm tra health của API và kết nối DB, test quyền và lỗi kết nối. |
| 2 · Tách theo nghiệp vụ | Route ở `api/v1/`, logic đặt, trả tiền và suất ở `services/`, phép biến đổi dữ liệu và validation ở `models/`, `schemas/`. Giữ hợp đồng HTTP, giao dịch PostgreSQL và kết quả hết hạn thanh toán. | Pytest kiểm tra method/path, chính sách truy cập, mã phản hồi, JSON, admin, transaction và luồng đặt vé. Thư mục `v1` là đường dẫn mã nguồn. Client tiếp tục gọi `/api/screenings` và `/api/bookings/{id}/pay`. |
| 3 · PostgreSQL và test | Tách baseline, seed, quyền runtime, kiểm tra schema read-only và runner test. Ba test thiếu port dùng tệp dotenv riêng. Test phân quyền dùng role tạm có mật khẩu cho SCRAM. | SQL integrity, reconciliation/P16, concurrency. Đã dump/restore DB Compose thử nghiệm rồi đối chiếu số dòng và checksum của toàn bộ 7 bảng. |
| 4 · Compose | Development có frontend, API, DB, healthcheck và volume. Profile test dùng mạng riêng cùng PostgreSQL trên tmpfs. | Ba service development đều healthy. Tạo booking, dừng/mở stack và đọc lại dữ liệu thành công. Nạp lại seed trên DB đã có dữ liệu bị từ chối. Config profile test hợp lệ với tệp env trống. |
| 5 · React + TypeScript | Chuyển 12 trang sang React, dùng Vite và kiểm tra TypeScript. Giữ URL HTML, tham số lọc/chọn ghế, poster, font và cấu hình API theo origin. | Hai luồng Playwright qua HTTP thật đã chạy trên cả bản dựng local và stack Compose với role runtime giới hạn. Luồng khách kiểm tra chiều rộng 375 px, luồng admin dùng viewport desktop. |
| 6 · Chuyển mặc định và bàn giao | Compose phục vụ React. Có tùy chọn UI dự phòng và hướng dẫn riêng cho checkout mới, debug, DB hiện hữu và thiết bị khác. | Đã chạy toàn bộ runner trên bản sao mã nguồn sạch Windows. Kết quả Linux và giới hạn nghiệm thu ghi bên dưới. |

## Mapping và điểm phải bảo toàn

| Current path (trước migration) | Proposed path (đã triển khai) | Reason | Risk |
|---|---|---|---|
| `app/__init__.py`, `app/api.py` | `backend/app/main.py`, `backend/app/api/__init__.py` | Tách factory và đăng ký blueprint | Sai prefix hoặc khởi tạo Flask nhiều lần |
| `app/{admin,auth,booking,movies,screenings}.py` | `backend/app/api/v1/`, `services/`, `schemas/`, `models/` | Phân vai HTTP, validation, truy vấn và transaction theo nghiệp vụ | Mất trường JSON, đổi quyền, commit sai khi giữ ghế hoặc hết hạn |
| `app/{config,database,security,cors,health,...}.py` | `backend/app/core/` | Dùng chung cấu hình, kết nối và chính sách bảo mật | Đọc nhầm dotenv hoặc đổi CORS |
| `requirements.txt`, `.env.example`, `scripts/set_demo_passwords.py` | `backend/requirements.txt`, `backend/.env.example`, `backend/scripts/` | Tập hợp phụ thuộc và công cụ setup | Credential setup và runtime phải độc lập |
| `database/schema.sql`, `database/seed.sql` | `backend/migrations/0001_baseline.sql`, `backend/seeds/demo.sql` | Tách khởi tạo schema và nạp demo | Áp baseline hoặc seed nhầm vào DB hiện hữu |
| `tests/`, `database/tests/{*.sql,test_concurrency.py}` | `backend/tests/`, `backend/tests/sql/`, `backend/tests/test_booking_concurrency.py` | Chung cơ chế cấp phát DB tạm, giữ các suite SQL | Nhầm DB test, bỏ lọt probe hoặc ca concurrency |
| `database/tests/run_all.sh`, `pytest.ini` | Giữ vị trí, cập nhật entry point và discovery | Hỗ trợ caller cũ | Sai working directory hoặc thiếu port test |
| `frontend/*.html`, `frontend/js/` | `frontend/src/`, `frontend/index.html`; HTML cũ ở `frontend/legacy/`, helper vẫn ở `frontend/js/` | UI theo trang/tính năng, dùng lại logic được test, có bản dự phòng | Mất liên kết sâu, token, lựa chọn ghế hoặc tham số đăng nhập quay lại |
| `frontend/css/`, `frontend/fonts/`, `frontend/images/` | `frontend/src/assets/`, `frontend/public/fonts/`, `frontend/public/images/` | Vite build CSS, phục vụ font và poster theo URL cũ | Sai URL, CSP hoặc thiếu giấy phép font |
| `frontend/server.py`, `frontend/tests/`, `frontend/package.json` | Giữ vị trí; thêm `frontend/e2e/` và lockfile npm | Kiểm tra qua HTTP và cấu hình API lúc chạy | Khác hành vi giữa Vite và server của bản build |
| `README.md`, `database/README.md`, `docs/api/`, `docs/database/` | Giữ vị trí, cập nhật đường dẫn/lệnh | Hướng dẫn từ root, hợp đồng và kiểm chứng DB | Người dùng nạp seed hoặc chạy script theo đường dẫn cũ |
| `.env`, lịch sử ở `PROJECT_PROGRESS.md`, `presentation/` | Giữ tại chỗ | Bảo toàn cấu hình cá nhân và tài liệu dự án | Lộ credential hoặc ghi đè lịch sử |

## Quy trình vận hành

Dọn thư mục sau migration. Đã kiểm tra và dọn cache bytecode của `app/`, `tests/`, `scripts/` ở root cùng các thư mục tài nguyên trống `frontend/css/`, `frontend/fonts/`, `frontend/images/`. Các thư mục này chỉ còn tồn tại ở máy đã chạy phiên bản cũ.

Từ root, dùng mẫu `backend/.env.example` khi tạo cấu hình development lần đầu. Các biến và giá trị cần điền có trong README.

| Tác vụ | Lệnh |
|---|---|
| Build và mở development | `docker compose up --build -d --wait` |
| Seed một lần vào volume mới | `docker compose exec -T db psql -X -v ON_ERROR_STOP=1 -U cinema_owner -d cinema -f /opt/cinema/demo.sql` |
| Chỉ mở API và DB | `docker compose up api db` |
| Chỉ mở frontend | `docker compose up --no-deps frontend` |
| Kiểm thử đầy đủ trên DB độc lập | `docker compose --profile test run --build --rm verify` |
| Dừng development và giữ volume | `docker compose down` |

Seed trong Compose chạy bằng role setup bên trong DB container. API tiếp tục dùng role giới hạn `cinema_api`. Có thể chuyển về giao diện HTML dự phòng bằng `CINEMA_LEGACY_UI=1` rồi cập nhật riêng service frontend. Hướng dẫn dùng PostgreSQL ngoài Compose và kiểm tra DB đã có dữ liệu nằm trong [database/README.md](../../database/README.md).

## Kết quả nghiệm thu và giới hạn

- **Windows, checkout sạch** — `backend/tests/verify.py` build TypeScript/React và UI dự phòng, pytest đạt **1.354**, skip **2** do quyền tạo symlink, sau đó chạy thành công SQL, concurrency và cả hai luồng Playwright. Bộ Node có 120 test. Việc chuyển test HTML tĩnh sang bản build dự phòng thay đổi số case tham số hóa theo file. Có thêm 25 case kiểm tra module React và các URL của bản build.
- **SQL** — 177 kiểm tra integrity, 31 đối chiếu reconciliation và xác nhận riêng P16 sau commit lỗi. Suite concurrency đạt 16/16 kiểm tra. Các lần chạy dùng database do chính runner cấp phát.
- **UI trên stack Compose** — khách đăng ký, quay lại ghế đã chọn sau đăng nhập, đặt vé, trả tiền, tải lại, xem lịch sử và hủy vé. Admin tạo/sửa phim, tạo/sửa suất và lọc booking.
- **Dữ liệu** — bản khôi phục qua `pg_dump -Fc` / `pg_restore` vượt qua `check_schema`. Checksum theo dòng của bảy bảng trùng khớp, gồm 1 booking, 4 user, 7 phim, 5 phòng, 250 ghế, 281 suất và 0 liên kết ghế sau hủy. So sánh SQL dump ghi nhận PostgreSQL biểu diễn lại kiểu ép mảng của ba CHECK enum sau restore. Chỉ sử dụng dữ liệu thử nghiệm cho phép đối chiếu này.
- **Linux Compose** — `docker compose --profile test run --build --rm verify` kết thúc với mã 0. Pytest đạt **1.355**, skip **1** do directory junction chỉ có trên Windows. Các bài symlink chạy đạt trên Linux. SQL, 16/16 kiểm tra concurrency và 2/2 luồng Playwright đạt. Lệnh `npm test` riêng cũng đạt 120/120 trên Node 24 trong container và Node 26 trên Windows. Stack nghiệm thu đã dừng, volume dữ liệu thử được giữ lại.
- **Giới hạn** — viewport mobile đã được kiểm tra bằng Chromium. Trình diễn từ một thiết bị vật lý thứ hai qua LAN còn chờ môi trường có thiết bị. Redis, gửi thông báo, bán combo và chỉnh sơ đồ ghế thuộc phạm vi tính năng mới đã tách khỏi migration.

## Rà soát giao diện sau migration

Đã khôi phục danh mục dạng lưới, thu gọn poster trong lịch chiếu, bổ sung lại các bước đặt vé và chỉnh hiển thị biểu mẫu. Kiểm tra Chromium ở các chiều rộng 320, 375, 768, 1024 và 1440 px. Bộ Compose verify đạt 1.356 test pytest, bỏ qua một ca dành cho Windows, và đạt cả ba bài Playwright. Bản demo tại `http://localhost:8163` đã được cập nhật.
