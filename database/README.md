# PostgreSQL cho Cinema

SQL chuẩn nằm tại [baseline 0001](../backend/migrations/0001_baseline.sql). [Seed demo](../backend/seeds/demo.sql) và [quyền cho volume Compose mới](../backend/migrations/compose-role.sql) có vòng đời riêng. PostgreSQL cần extension `btree_gist`. Phiên bản dùng để kiểm chứng migration là PostgreSQL 18.

## Tạo database mới

Để chạy bằng Compose, làm theo [README gốc](../README.md). Để tự quản lý server, dùng role setup có quyền tạo DB và extension. Ví dụ sau dành cho database mới tên `cinema_demo`, chạy từ root bằng client PostgreSQL:

```sh
createdb cinema_demo
psql -X -v ON_ERROR_STOP=1 -d cinema_demo -f backend/migrations/0001_baseline.sql
psql -X -v ON_ERROR_STOP=1 -d cinema_demo -f backend/seeds/demo.sql
```

Đặt `PGHOST`, `PGPORT`, `PGUSER` và credential libpq cho phiên setup. API dùng role runtime riêng. Xem danh sách quyền trong [hợp đồng DB](../docs/database/postgresql_flask_integration_contract.md). Có thể chạy lại công cụ đổi mật khẩu bằng `python backend/scripts/set_demo_passwords.py --username admin` với các biến `SETUP_DB_*` riêng.

## Database đã có dữ liệu

1. Tạo backup bằng công cụ PostgreSQL và restore vào DB riêng. Cấu hình kết nối của terminal kiểm tra trỏ vào bản sao.
2. Từ `backend/` chạy `python -m scripts.check_schema`. Công cụ sử dụng session read-only, kiểm tra bảng, hàm, trigger đang bật, index, constraint có tên, extension và cột poster.
3. Đối chiếu định nghĩa bằng `pg_dump --schema-only --no-owner --no-privileges` của bản sao và một DB mới tạo từ 0001 trên cùng major version. Kiểm tra riêng các khác biệt. Preflight chỉ kiểm tra inventory; sự tồn tại của một tên hàm chưa xác minh nội dung hàm.
4. Khi schema khớp, có thể dùng bản ứng dụng mới với DB hiện hữu. Nếu thiếu đối tượng, chuẩn bị migration tăng dần riêng và kiểm chứng trên bản sao trước. Baseline có các lệnh tạo bảng một lần. Seed dành cho database trống.

## Quyền xóa phim trên database hiện hữu

Database Compose mới tự áp dụng [migration quyền xóa phim](../backend/migrations/0002_movie_delete_permissions.sql). Với volume Compose đã có, chạy từ root để cập nhật quyền của role `cinema_api` bằng tài khoản chủ database:

```powershell
Get-Content -Raw backend/migrations/0002_movie_delete_permissions.sql |
  docker compose exec -T db psql -X -v ON_ERROR_STOP=1 -U cinema_owner -d cinema
```

Với PostgreSQL tự quản lý, chủ database cấp quyền `DELETE` trên `movies` và `showtimes` cho role chạy Flask. Lệnh cấp quyền có thể chạy lại.

## Kiểm chứng độc lập

Từ root chạy `docker compose --profile test run --build --rm verify`. Nếu đã có server test riêng, dùng `python backend/tests/run_database.py`. Lệnh Bash cũ `bash database/tests/run_all.sh` vẫn gọi cùng runner. Cần chỉ định port test hoặc `PGPORT` tường minh khi dùng wrapper này. Cả integrity và reconciliation chạy bằng `psql`; concurrency commit vào database riêng của runner. [Tài liệu kiểm thử](../docs/database/database_test_documentation.md)
