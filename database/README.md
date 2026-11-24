# PostgreSQL cho Cinema

Schema hiện tại gồm [baseline 0001](../backend/migrations/0001_baseline.sql) cùng [migration 0003](../backend/migrations/0003_booking_integrity.sql) và [migration 0004](../backend/migrations/0004_finite_money.sql). Migration 0002 cấp quyền cho role runtime nếu dùng role đó. [Seed demo](../backend/seeds/demo.sql) và [quyền cho volume Compose mới](../backend/migrations/compose-role.sql) có vòng đời riêng. PostgreSQL cần extension `btree_gist`. Phiên bản dùng để kiểm chứng migration là PostgreSQL 18.

## Tạo database mới

Để chạy bằng Compose, làm theo [README gốc](../README.md). Để tự quản lý server, dùng role setup có quyền tạo DB và extension. Ví dụ sau dành cho database mới tên `cinema_demo`, chạy từ root bằng client PostgreSQL:

```sh
createdb cinema_demo
psql -X -v ON_ERROR_STOP=1 -d cinema_demo -f backend/migrations/0001_baseline.sql
psql -X -v ON_ERROR_STOP=1 -d cinema_demo -f backend/migrations/0003_booking_integrity.sql
psql -X -v ON_ERROR_STOP=1 -d cinema_demo -f backend/migrations/0004_finite_money.sql
psql -X -v ON_ERROR_STOP=1 -d cinema_demo -f backend/seeds/demo.sql
```

Đặt `PGHOST`, `PGPORT`, `PGUSER` và credential libpq cho phiên setup. API dùng role runtime riêng. Xem danh sách quyền trong [hợp đồng DB](../docs/database/postgresql_flask_integration_contract.md). Có thể chạy lại công cụ đổi mật khẩu bằng `python backend/scripts/set_demo_passwords.py --username admin` với các biến `SETUP_DB_*` riêng.

## Database đã có dữ liệu

1. Tạo backup bằng công cụ PostgreSQL và restore vào DB riêng. Cấu hình kết nối của terminal kiểm tra trỏ vào bản sao.
2. Từ `backend/` chạy `python -m scripts.check_schema`. Công cụ sử dụng session read-only, kiểm tra bảng, hàm, trigger đang bật, index, constraint có tên, extension và cột poster.
3. Đối chiếu định nghĩa bằng `pg_dump --schema-only --no-owner --no-privileges` của bản sao và một DB mới từ cùng chuỗi migration trên cùng major version. Kiểm tra riêng các khác biệt. Preflight chỉ kiểm tra inventory; sự tồn tại của một tên hàm chưa xác minh nội dung hàm.
4. Khi schema khớp, có thể dùng bản ứng dụng mới với DB hiện hữu. Nếu thiếu đối tượng, chuẩn bị migration tăng dần riêng và kiểm chứng trên bản sao trước. Baseline có các lệnh tạo bảng một lần. Seed dành cho database trống.

## Quyền xóa phim trên database hiện hữu

Database Compose mới tự áp dụng [migration quyền xóa phim](../backend/migrations/0002_movie_delete_permissions.sql). Với volume Compose đã có, chạy từ root để cập nhật quyền của role `cinema_api` bằng tài khoản chủ database:

```powershell
Get-Content -Raw backend/migrations/0002_movie_delete_permissions.sql |
  docker compose exec -T db psql -X -v ON_ERROR_STOP=1 -U cinema_owner -d cinema
```

Với PostgreSQL tự quản lý, chủ database cấp quyền `DELETE` trên `movies` và `showtimes` cho role chạy Flask. Lệnh cấp quyền có thể chạy lại.

## Nâng cấp toàn vẹn booking (0003)

Backup và thử restore, upgrade trên bản sao trước. Đặt lịch bảo trì vì migration khóa bảng booking và chi tiết, backfill và dựng unique index. Dừng các writer vào DB mục tiêu trong lúc áp dụng. Với volume Compose đã có và chưa áp dụng 0003, chạy một lần bằng role owner từ root:

```sh
docker compose exec -T db psql -X -v ON_ERROR_STOP=1 -U cinema_owner -d cinema < backend/migrations/0003_booking_integrity.sql
```

PowerShell dùng `Get-Content -Raw backend/migrations/0003_booking_integrity.sql |` trước lệnh `docker compose exec` thay cho redirect `<`. Với PostgreSQL tự quản lý, dùng `psql -X -v ON_ERROR_STOP=1 -d <database> -f backend/migrations/0003_booking_integrity.sql`. Không chạy lại 0001 hoặc seed trên dữ liệu có sẵn.

Nếu gặp 23505 do giữ ghế trùng từ trước, migration dừng và rollback. Chủ dữ liệu cần đối soát các booking bị ảnh hưởng trước khi áp dụng lại. Nếu không lấy được khóa trong 5 giây, kiểm tra writer đang hoạt động và thử lại trong cửa sổ bảo trì. Sau khi chạy, xác minh precision 12, scale 2 và hai constraint `booking_seats_showtime_seat_key`, `booking_seats_booking_showtime_fkey`. Không hạ precision xuống 10,2 khi đã có tổng vượt miền cũ.

## Nâng cấp miền tiền (0004)

Khi 0003 đã áp dụng, tiếp tục trong cùng cửa sổ bảo trì, sau khi dừng writer và đã xác minh backup qua restore biệt lập:

```sh
docker compose exec -T db psql -X -v ON_ERROR_STOP=1 -U cinema_owner -d cinema < backend/migrations/0004_finite_money.sql
```

PowerShell dùng `Get-Content -Raw backend/migrations/0004_finite_money.sql |` rồi cùng lệnh `docker compose exec`. Với PostgreSQL tự quản lý dùng `psql -X -v ON_ERROR_STOP=1 -d <database> -f backend/migrations/0004_finite_money.sql`. File tự kiểm dữ liệu dưới khóa và dừng với 23514, báo số hàng theo từng bảng nếu gặp NaN, Infinity hoặc -Infinity. Không tự sửa dữ liệu. Nếu 0003 vừa commit và 0004 dừng, DB vẫn ở 0003.

Trước khi mở writer, xác nhận ba constraint `showtimes_ticket_price_finite`, `bookings_total_amount_finite`, `booking_seats_price_at_booking_finite` đều có `convalidated = true`. Đối chiếu booking/seat history với trước migration, gọi `/health` và `/health/db`, rồi chạy smoke catalog, đặt/thanh toán/hủy trên suất được phép. Nếu cần phục hồi sau commit, dừng writer và restore trên cluster khác trước khi chuyển kết nối được duyệt. Không reset volume hay hạ precision.

## Kiểm chứng độc lập

Từ root chạy `docker compose --profile test run --build --rm verify`. Nếu đã có server test riêng, dùng `python backend/tests/run_database.py`. Lệnh Bash cũ `bash database/tests/run_all.sh` vẫn gọi cùng runner. Cần chỉ định port test hoặc `PGPORT` tường minh khi dùng wrapper này. Cả integrity và reconciliation chạy bằng `psql`; concurrency commit vào database riêng của runner. [Tài liệu kiểm thử](../docs/database/database_test_documentation.md)
