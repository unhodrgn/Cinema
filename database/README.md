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

Chỉ thực hiện nâng cấp trên database đang có sau khi đã có phê duyệt. **Lưu ý với Docker Compose:** `docker compose restart` hoặc `docker compose up` **không chạy lại** các init script trong `/docker-entrypoint-initdb.d/` khi volume `cinema_data` đã tồn tại; các migration mới phải được áp dụng thủ công bằng role chủ database (`cinema_owner`).

1. **Dừng toàn bộ writer** vào đúng project (ví dụ `docker compose stop api`), kiểm tra catalog hiện tại và dữ liệu bất thường trước khi backup.
2. **Tạo backup custom + globals không có password** và thử restore vào cluster/database test biệt lập trước khi chạm vào bản chính:

```sh
# Ví dụ với Compose (chạy từ thư mục gốc)
docker compose exec -T db pg_dump -Fc -U cinema_owner -d cinema > cinema_pre_upgrade.dump
docker compose exec -T db pg_dumpall --globals-only --no-role-passwords -U cinema_owner > cinema_globals.sql
```

3. Trên bản sao đã restore, chạy `python -m scripts.check_schema` từ `backend/` (phiên `readonly=True`) để kiểm tra bảng, hàm, trigger đang bật, index, constraint (gồm `0003` và `0004`), kiểu `bookings.total_amount numeric(12,2)`, `booking_seats.showtime_id NOT NULL`, extension `btree_gist` và cột `movies.poster_url`.
4. Đối chiếu định nghĩa bằng `pg_dump --schema-only --no-owner --no-privileges` giữa bản sao và một DB mới dựng từ cùng chuỗi migration trên cùng major version. Ngoài ra, **so sánh riêng grants của role runtime**, **constraints (`convalidated = true`)** và **fingerprint/số dòng** của 7 bảng trước và sau nâng cấp:

```sql
-- Kiểm tra grants của cinema_api
SELECT table_name, privilege_type
FROM information_schema.role_table_grants
WHERE grantee = 'cinema_api' AND table_schema = 'public'
ORDER BY table_name, privilege_type;

-- Kiểm tra constraint 0003 & 0004 đã được xác thực
SELECT conname, contype, convalidated
FROM pg_constraint
WHERE connamespace = 'public'::regnamespace
  AND conname IN (
    'bookings_id_showtime_key',
    'booking_seats_booking_showtime_fkey',
    'booking_seats_showtime_seat_key',
    'showtimes_ticket_price_finite',
    'bookings_total_amount_finite',
    'booking_seats_price_at_booking_finite'
  )
ORDER BY conname;

-- Fingerprint nhanh theo số dòng và tổng tiền lịch sử
SELECT 'users' AS tbl, count(*) AS cnt, NULL::numeric AS total_sum FROM users
UNION ALL SELECT 'movies', count(*), NULL FROM movies
UNION ALL SELECT 'theater_rooms', count(*), NULL FROM theater_rooms
UNION ALL SELECT 'seats', count(*), NULL FROM seats
UNION ALL SELECT 'showtimes', count(*), NULL FROM showtimes
UNION ALL SELECT 'bookings', count(*), COALESCE(sum(total_amount), 0) FROM bookings
UNION ALL SELECT 'booking_seats', count(*), COALESCE(sum(price_at_booking), 0) FROM booking_seats;
```

5. **Phân nhánh áp migration bằng owner (`cinema_owner`):**
   - Nếu DB đang ở `0002` (chưa có `0003`): áp `0003_booking_integrity.sql` rồi `0004_finite_money.sql`.
   - Nếu DB đã ở `0003`: chỉ áp `0004_finite_money.sql`.
   - Không bao giờ chạy lại `0001_baseline.sql` hoặc `backend/seeds/demo.sql` trên dữ liệu có sẵn.

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
