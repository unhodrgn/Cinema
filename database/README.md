# PostgreSQL cho Cinema

Schema hiện tại gồm [baseline 0001](../backend/migrations/0001_baseline.sql) cùng [migration 0003](../backend/migrations/0003_booking_integrity.sql) [migration 0004](../backend/migrations/0004_finite_money.sql) và [migration 0005](../backend/migrations/0005_username_case_insensitive.sql) và [migration 0006](../backend/migrations/0006_username_validation.sql). Migration 0002 cấp quyền cho role runtime nếu dùng role đó. [Seed demo](../backend/seeds/demo.sql) và [quyền cho volume Compose mới](../backend/migrations/compose-role.sql) có vòng đời riêng. PostgreSQL cần extension `btree_gist`. Phiên bản dùng để kiểm chứng migration là PostgreSQL 18.

## Tạo database mới

Để chạy bằng Compose, làm theo [README gốc](../README.md). Để tự quản lý server, dùng role setup có quyền tạo DB và extension. Ví dụ sau dành cho database mới tên `cinema_demo`, chạy từ root bằng client PostgreSQL:

```sh
createdb cinema_demo
psql -X -v ON_ERROR_STOP=1 -d cinema_demo -f backend/migrations/0001_baseline.sql
psql -X -v ON_ERROR_STOP=1 -d cinema_demo -f backend/migrations/0003_booking_integrity.sql
psql -X -v ON_ERROR_STOP=1 -d cinema_demo -f backend/migrations/0004_finite_money.sql
psql -X -v ON_ERROR_STOP=1 -d cinema_demo -f backend/migrations/0005_username_case_insensitive.sql
psql -X -v ON_ERROR_STOP=1 -d cinema_demo -f backend/migrations/0006_username_validation.sql
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

3. Trên bản sao đã restore, chạy `python -m scripts.check_schema` từ `backend/` (phiên `readonly=True`) để kiểm tra bảng, hàm, trigger đang bật, index, constraint (gồm `0003`, `0004`, index `users_username_lower_key` của `0005` và CHECK username của `0006`), kiểu `bookings.total_amount numeric(12,2)`, `booking_seats.showtime_id NOT NULL`, extension `btree_gist` và cột `movies.poster_url`.
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
   - Nếu DB đang ở `0002` (chưa có `0003`): áp `0003_booking_integrity.sql`, `0004_finite_money.sql` rồi `0005_username_case_insensitive.sql`.
   - Nếu DB đã ở `0003`: áp `0004_finite_money.sql` rồi `0005_username_case_insensitive.sql`.
   - Nếu DB đã ở `0004`: áp `0005_username_case_insensitive.sql`.
   - Khi bản sao đã ở 0005, tiếp tục theo [quy trình 0006](#quy-tắc-username-thống-nhất-0006).
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

## Tên đăng nhập không phân biệt hoa/thường (0005)

Ở phiên bản 0005, API lưu tên đăng nhập ở dạng NFKC đã cắt khoảng trắng hai đầu và so trùng không phân biệt hoa/thường (`Customer1`, ` customer1 ` và `ｃｕｓｔｏｍｅｒ１` là cùng tài khoản với `customer1`). `0005_username_case_insensitive.sql` thêm unique index `users_username_lower_key` trên `lower(username)`. File tự kiểm dữ liệu dưới khóa và dừng, không sửa dữ liệu: `23505` nếu có hai tên chỉ khác chữ hoa/thường, `23514` nếu có tên còn khoảng trắng hai đầu hoặc chưa ở dạng NFKC (tên đó sẽ không thể gõ lại khi đăng nhập). Câu truy vấn đối soát nằm trong HINT của lỗi.

```sh
docker compose exec -T db psql -X -v ON_ERROR_STOP=1 -U cinema_owner -d cinema < backend/migrations/0005_username_case_insensitive.sql
```

## Kiểm chứng độc lập

Từ root chạy `docker compose --profile test run --build --rm verify`. Nếu đã có server test riêng, dùng `python backend/tests/run_database.py`. Lệnh Bash cũ `bash database/tests/run_all.sh` vẫn gọi cùng runner. Cần chỉ định port test hoặc `PGPORT` tường minh khi dùng wrapper này. Cả integrity và reconciliation chạy bằng `psql`; concurrency commit vào database riêng của runner. [Tài liệu kiểm thử](../docs/database/database_test_documentation.md)

## Quy tắc username thống nhất (0006)

Trên bản sao phục hồi ở schema 0005, migration 0006 giữ unique index `users_username_lower_key`, áp một CHECK cho mọi tài khoản và dừng với SQLSTATE `23514` nếu còn dòng không hợp lệ. Kiểu cột là `varchar` và CHECK kiểm tra giới hạn 60 ký tự. Cách này giữ được khoảng trắng cuối đầu vào cho CHECK phát hiện khi ghi bằng SQL trực tiếp. React, legacy và Flask đều kiểm tra đầu vào gốc và kết quả chuẩn hóa NFKC. Frontend gửi dữ liệu gốc để Flask kiểm tra lại và lưu giá trị đã chuẩn hóa. PostgreSQL yêu cầu giá trị đã chuẩn hóa khi INSERT/UPDATE. Login tiếp tục chấp nhận khoảng trắng hai đầu theo cách tra cứu hiện có.

1. Khi có phê duyệt, dừng writer, backup database 0005 và kiểm tra restore trên đích riêng. Giữ database và volume cũ. Xác nhận hai tài khoản thử đã được duyệt vẫn đúng ID, username và role, không có booking và không có phụ thuộc mới. Trong môi trường khác, bỏ qua bước xóa trừ khi hai dòng đúng là dữ liệu thử đã được xác nhận.
2. Trên bản sao đích đã đối chiếu, chạy `psql -X -v ON_ERROR_STOP=1 -d <database-dich> -f database/maintenance/remove_confirmed_test_accounts.sql`. Script khóa hai bảng, xác minh danh tính và phụ thuộc, và chỉ commit nếu xóa đúng hai dòng. Đây là thao tác bảo trì riêng.
3. Chạy `psql -X -v ON_ERROR_STOP=1 -d <database-dich> -f backend/migrations/0006_username_validation.sql`. Nếu còn dữ liệu vi phạm, giữ website ở 0005 và quyết định từng dòng trước khi thử lại. Khoảng chờ lấy khóa cho mỗi bước là 5 giây.
4. Xác minh `users_username_format_check` đã validate, unique index 0005 còn hiệu lực và chỉ hai dòng đã duyệt biến mất. So checksum tài khoản còn lại, lịch sử booking và sequence. Chạy `python -m scripts.check_schema` từ thư mục `backend/` và smoke test bằng bộ image cùng phiên bản trước khi mở lại ghi.
5. Nếu bất kỳ kiểm tra nào thất bại trước khi mở ghi, khởi động lại dịch vụ 0005 với volume cũ. Nếu đã mở ghi, dừng writer và đối soát các giao dịch mới trước khi đổi kết nối.

Compose tự áp dụng file 0006 trên volume mới. Với volume hiện có, thực hiện quy trình nâng cấp ở trên. Dump demo và ERD hiện hành là 0006. Xem [bản 0005 lưu trữ riêng](history/0005/README.md).
