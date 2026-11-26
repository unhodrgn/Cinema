# Checklist chuẩn bị và nộp theo yêu cầu của giáo sư

Cập nhật: 26/11/2026. Trạng thái ghi theo những gì có trong dự án và đã kiểm tra trên máy.

**Nguồn yêu cầu (chỉ dùng những nguồn này, không thêm hạng mục nào khác):**

| Ký hiệu | Nguồn |
|---|---|
| **[S1]** | `presentation/important.md` (hướng dẫn tiêu chuẩn phát biểu cuối kỳ của giáo sư, bản tiếng Hàn) |
| **[S2]** | Tin nhắn của bạn ngày 26/11 03:52 UTC, tóm tắt lại yêu cầu thuyết trình (có thêm điều kiện "không làm admin dashboard nên phân quyền thể hiện bằng script SQL") |
| **[S3]** | Tin nhắn của bạn ngày 26/11 07:03 UTC: danh sách 12 sản phẩm phải nộp (mục 5) |
| **[P]** | `chia_viec.md`, kế hoạch nội bộ của nhóm. **Không phải yêu cầu của giáo sư**: chỉ nhắc ở mục 6 về hạn nội bộ |

> **Lưu ý:** đề bài gốc của môn không có trong thư mục dự án. `important.md` chỉ là hướng dẫn về buổi phát biểu; danh sách 12 sản phẩm nộp (mục 5) lấy từ tin nhắn của bạn. Định dạng nộp, nơi nộp và hạn nộp chính thức vẫn chưa có nguồn, cần đối chiếu với đề gốc.

Ký hiệu trạng thái: ✅ xong (có bằng chứng) · ⚠️ xong một phần hoặc cần làm trước giờ G · ❌ thiếu · ❓ chưa xác minh được với đề gốc

---

## 1. Yêu cầu về nội dung buổi thuyết trình

| # | Yêu cầu | Nguồn | Trạng thái | Bằng chứng / việc còn lại |
|---|---|---|---|---|
| 1.1 | DB (backend server) và client (web/app frontend) tách riêng cả logic lẫn vật lý | S1, S2 | ✅ | 3 container độc lập trong `docker-compose.yml` (`db`, `api`, `frontend`). Test: `backend/tests/test_process_separation.py`, `test_architecture_live.py`. Tài liệu: `docs/api/api_contract.md` mục 1. Slide 4 |
| 1.2 | Giới thiệu môi trường cài đặt ban đầu | S1, S2 | ✅ | Slide 3 (ba bước: `.env` → `docker compose up` → `demo.sql`). Chi tiết ở `README.md` và speaker notes slide 3 |
| 1.3 | Giới thiệu DBMS, ngôn ngữ | S1, S2 | ✅ | Slide 3: PostgreSQL 18, Python 3.12 + Flask, React + TypeScript |
| 1.4 | Giới thiệu công cụ đi kèm: framework, container, công cụ làm việc nhóm | S1, S2 | ✅ | Slide 3: Flask, React/Vite, Docker Compose, pytest/Playwright, Git/GitHub. Công cụ làm việc nhóm: chỉ Git/GitHub (bạn đã xác nhận) |
| 1.5 | Kể theo mạch ý tưởng → thiết kế → cài đặt → kiểm chứng, không chỉ liệt kê tính năng | S1, S2 | ✅ | Slide 2–5 (bài toán, môi trường, kiến trúc, nghiệp vụ), 6–8 (thiết kế), 9–10 (cài đặt), 11 (kiểm chứng), 12–13 (demo). Bảng thời lượng ở `presentation_content.md` mục 0 |
| 1.6 | Tính năng cốt lõi riêng của nhóm | S1 (tiêu chí chấm) | ✅ | Slide 7: chống đặt trùng ghế và chồng lịch chiếu ngay ở DB, hết hạn 10 phút, bất biến lịch sử. Slide 13 chứng minh bằng SQL |
| 1.7 | Slide cuối hoặc giữa: "AI làm được mọi thứ thì làm dự án nhóm có ý nghĩa gì?", dựa trên trải nghiệm thật | S1, S2 | ✅ | Slide 14, dựa trên trải nghiệm thật của nhóm (đối soát chéo ngày 20/11 ra 13 điểm lệch, các lỗi 0003/0004/0005). Nguồn dẫn chứng: `docs/database/handover_reconciliation_report.md` |
| 1.8 | Thời lượng 15 phút thuyết trình + 5–10 phút hỏi đáp | S1, S2 | ⚠️ | Kịch bản 15:00 đã phân bổ theo từng slide. **Chưa có bằng chứng đã tập bấm giờ.** Việc cần làm: tập đủ một lượt, có hai người nói theo phân vai |
| 1.9 | Phát biểu và demo: thông thường 1 người, tùy tình huống 2 người trở lên | S1, S2 | ✅ | Nhóm chọn 2 người, được `important.md` cho phép. Phân vai ở `presentation_content.md` mục 0: 응웬치롱 và 응오후인느 |
| 1.10 | Tài liệu slide (PPT), mẫu tự do | S1 | ✅ | `presentation/cinema_presentation_ko.pptx` (16 slide, tiếng Hàn, có speaker notes). Bản cũ: `cinema_presentation_ko.backup.pptx`. Nội dung nguồn: `presentation_content.md` |

## 2. Chuẩn bị môi trường demo trước giờ G

Yêu cầu: S1 và S2 đều nói phải demo được ngay khi bắt đầu, lỗi môi trường hay app không chạy thì nhóm tự chịu.

| # | Việc | Nguồn | Trạng thái | Bằng chứng / việc còn lại |
|---|---|---|---|---|
| 2.1 | App chạy được bằng `docker compose` | S1, S2 | ✅ | Đã chạy thử ngày 26/11: db, api, frontend đều healthy |
| 2.2 | Stack có đang chạy sẵn trên máy trình chiếu | S1, S2 | ❌ | Lúc kiểm tra gần nhất (26/11), chỉ container `test-db` còn chạy, stack chính đã tắt. Cần khởi động lại trước giờ G: `docker compose up -d --wait` (dữ liệu nằm trong volume nên giữ nguyên) |
| 2.3 | Có suất chiếu trong tương lai để demo đặt vé | S1, S2 | ⚠️ | Seed tạo 280 suất cho 14 ngày kể từ ngày nạp, **suất cuối khoảng 08/12/2026**. Nếu buổi thuyết trình sau ngày đó thì không còn suất tương lai: phải tạo suất mới ở trang Screenings (Admin). Ngày giờ thuyết trình **chưa được xác nhận** |
| 2.4 | Mở sẵn trình duyệt: một phiên khách (`customer1`), một phiên admin | S1, S2 | ⚠️ | Hướng dẫn ở phụ lục `presentation_content.md`. Cần làm tay trước giờ G |
| 2.5 | Đã chạy thử trọn quy trình trên **đúng máy trình chiếu** | S1, S2 | ❌ | Mới chạy trên máy phát triển (26/11). Cần chạy lại trên máy thật, kể cả kiểm tra font Malgun Gothic của PPT |
| 2.6 | Chạy lại bộ kiểm thử trước giờ G | (khuyến nghị của nhóm) | ⚠️ | `docker compose --profile test run --build --rm verify`. Lần gần nhất đạt (pytest 1.409, concurrency 16/16, Playwright 6/6). Có 2 lần chạy ngắt quãng bị lỗi, chưa rõ nguyên nhân (ghi ở `PROJECT_PROGRESS.md`) |
| 2.7 | Phương án dự phòng khi Docker/DB lỗi | S1, S2 (hệ quả của "tự chịu trách nhiệm") | ❌ | Chưa có (bạn quyết định để trống). Ý tưởng trong `presentation_content.md`: ảnh chụp màn hình hoặc video quay sẵn. Bộ ảnh chụp app thật đã có ở `presentation/assets/ui_*.png` |

## 3. Script SQL chuẩn bị sẵn để demo

Yêu cầu: S1 và S2 đều nói phải có script cho thấy được ngay khi demo: **thay đổi trạng thái dữ liệu**, **test tình huống ngoại lệ**, **kiểm tra phân quyền**. S2 nói thêm: không làm admin dashboard nên phân quyền phải thể hiện bằng script SQL (role/GRANT hoặc truy vấn kiểm tra quyền).

| # | Yêu cầu | Trạng thái | Script (trong `database/demo/`) và kết quả đã chạy ngày 26/11 |
|---|---|---|---|
| 3.1 | Thay đổi trạng thái dữ liệu | ✅ | `main.sql`: đặt vé 2 ghế, thanh toán, hủy, người khác đặt lại. Chạy exit 0, kết thúc `ROLLBACK` |
| 3.2 | Test tình huống ngoại lệ | ✅ | `exceptions.sql`: UC002 (trùng ghế), UC003 (ghế phòng khác), 23P01 (chồng lịch), 23514 (giá NaN/âm). Chạy exit 0, `ROLLBACK` |
| 3.3 | Kiểm tra phân quyền bằng role/GRANT hoặc truy vấn quyền | ✅ | `permissions_grants.sql`: thuộc tính role `cinema_api`, bảng quyền 7 bảng, `REVOKE`/`GRANT`, `SET LOCAL ROLE`, ba lệnh bị từ chối với `42501`. Chạy exit 0, `ROLLBACK`. Có thêm `permissions.sql` làm dự phòng |
| 3.4 | Script nằm sẵn, chạy được ngay trong lúc demo | ⚠️ | Dựng DB cô lập `cinema_test_demo` theo phụ lục `presentation_content.md`, mở sẵn một terminal trong container `db`. **Cần dựng lại trước giờ G** nếu container bị tạo mới |
| 3.5 | Demo tranh chấp hai phiên (dự phòng, phục vụ Q&A) | ✅ | `concurrency_prepare.sql`, `concurrency_a.sql`, `concurrency_b.sql` (dùng hai terminal). Chưa chạy lại ngày 26/11 |

Lưu ý ngoài nguồn: web UI có các trang quản trị (`admin-movies`, `admin-screenings`, `admin-bookings`). Nếu giáo sư hỏi về chuyện "không làm admin dashboard", cần thống nhất cách trả lời trước, vì các trang này tồn tại và được dùng ở slide 12.

## 4. Tiêu chí chấm và slide/bằng chứng tương ứng

Nguồn: S1 (mục "Đánh giá").

| Tiêu chí | Nơi thể hiện |
|---|---|
| Mạch trình bày | Toàn bộ slide 2–13; bảng thời lượng `presentation_content.md` mục 0 |
| Tính năng cốt lõi riêng của nhóm | Slide 7 (bộ máy toàn vẹn trong PostgreSQL), 13 (chứng minh bằng SQL) |
| Mức hiểu kỹ thuật | Slide 6–8 và speaker notes; bộ câu hỏi Q&A dự kiến ở cuối `presentation_content.md` (6 câu có đáp án) |
| Độ chắc của thiết kế | Slide 8 (13 điểm lệch → 0, 4 migration nâng cấp 0002–0005), slide 11 (1.409 pytest, 177 kiểm tra SQL, 16 kiểm tra đồng thời, 6 E2E) |
| Sáng tạo hoặc độ hoàn thiện | Slide 4, 7, 12; `PROJECT_PROGRESS.md` (kiểm chứng đối kháng ngày 26/11) |

## 5. Hạng mục nộp bài (12 sản phẩm theo danh sách của giáo sư)

Nguồn: **[S3]** tin nhắn của bạn ngày 26/11 07:03 UTC liệt kê 12 sản phẩm phải nộp. Đã kiểm tra từng file ngày 26/11: nội dung theo đúng tên mục, đối chiếu với schema hiện tại (migrations `0001`–`0005`), và render thử tất cả sơ đồ Mermaid (đều hợp lệ). Đã sửa các tài liệu lỗi thời sau migration `0005` (tên đăng nhập không phân biệt hoa/thường) cùng ngày.

**Kết luận:** cả 12 mục đều có file và nội dung đúng tên mục. Mục 12 (.DB) được hiểu là file mô hình kiểu erwin: đã làm bằng draw.io, và vẫn giữ bản dump, **chờ xác nhận định dạng với giáo sư**.

| # | Sản phẩm | File | Trạng thái | Nhận xét |
|---|---|---|---|---|
| 1 | 프로젝트 개요서 | `docs/business/project_overview.md` | ✅ | Tổng quan, quy mô, bối cảnh/mục tiêu, phạm vi, người dùng, chức năng, quy tắc BR-01~15, môi trường, kỳ vọng. Đã cập nhật tham chiếu migration tới `0005` |
| 2 | 업무 기능도 | `docs/business/business_function.md` | ✅ | Cây phân rã chức năng (mindmap, 14 chức năng CM/C/A) và bảng chức năng theo người dùng. Render được |
| 3 | 단위 업무 기술서 | `docs/business/unit_business_description.md` | ✅ | 14 đơn vị nghiệp vụ, mỗi đơn vị có mục đích, điều kiện, đầu vào, xử lý, đầu ra, ngoại lệ. Đã cập nhật CM-01 và C-01 theo quy tắc tên đăng nhập mới |
| 4 | 업무 흐름도 | `docs/business/business_flowchart.md` | ✅ | 3 lưu đồ (đặt vé và thanh toán, hủy, quản lý suất chiếu) có nhánh lỗi và bảng giải thích từng bước. Render được. Đăng nhập, đăng ký và tra cứu không có lưu đồ riêng (theo phạm vi tài liệu) |
| 5 | 업무 문서 리스트 | `docs/business/business_document_list.md` | ✅ | DOC-01~07 (thành viên, phim, lịch chiếu, sơ đồ ghế, phiếu đặt vé, lịch sử hủy/hết hạn, danh sách đặt vé), có chú thích không cần là file riêng |
| 6 | 개념적 데이터 모델 (ER) | `docs/database/conceptual_data_model.md` | ✅ | 7 thực thể, bảng quan hệ và bản số, ERD Mermaid, quyết định mô hình hóa. ERD khái niệm chỉ có thực thể và quan hệ, không có thuộc tính (thuộc tính ở mô hình logic) |
| 7 | 논리적 데이터 모델 (relation schema, chuẩn hóa) | `docs/database/logical_data_model.md` + `docs/database/normalization.md` | ✅ ⚠️ | Đủ: lược đồ quan hệ 7 bảng (PK/FK/UK), quy tắc toàn vẹn, ERD logic; chuẩn hóa 1NF→3NF, phụ thuộc hàm, dư thừa có kiểm soát. Đã thêm `0005` và quy tắc tên đăng nhập. **Chuẩn hóa nằm ở file riêng** `normalization.md`: nộp kèm, hoặc gộp nếu giáo sư muốn "bao gồm". `normalization.md` tự ghi không có chứng minh hình thức (Armstrong) |
| 8 | 물리적 데이터 모델 (DDL, ràng buộc, index) | `docs/database/physical_data_model.md` + `backend/migrations/0001`~`0005` | ✅ ⚠️ | Đủ: ERD vật lý, ràng buộc, trigger (9), hàm (4), index (7, khớp DB thật), thiết kế đồng thời; đã thêm `0005`. DDL gốc nằm rải ở các migration tăng dần, nên đã tạo **file DDL gộp** `database/dump/cinema_schema.sql` (chỉ schema, 905 dòng, 7 bảng, 9 trigger, index `0005`; đã áp thử vào DB trống, chạy sạch) |
| 9 | 용어 사전 (bắt buộc) | `docs/database/glossary.md` | ✅ | Có (bắt buộc), 27 thuật ngữ. Đã cập nhật mục "계정 ID" |
| 10 | 도메인 정의서 | `docs/database/domain_definition.md` | ✅ | Miền cho mọi cột, mã lỗi, quy tắc thời gian. Đã cập nhật tiêu đề `0005` và câu về kiểm tra định dạng tên đăng nhập |
| 11 | 테이블 기술서 | `docs/database/table_description.md` | ✅ | 7 bảng, từng cột (kiểu, NULL, mặc định, ràng buộc), trigger, index, hàm và quyền. Đã thêm `0005` và index `users_username_lower_key` |
| 12 | 응용프로그램 + 데이터베이스 통합 파일 (.DB) | `database/model/` (file mô hình `cinema_model.drawio` + PDF + 3 ảnh PNG) và `database/dump/` (dump đầy đủ, DDL gộp) + mã nguồn + `docker-compose.yml` | ✅ ❓ | Bạn cho biết giáo sư muốn file mô hình kiểu erwin (cho phép dùng công cụ bất kỳ) nên đã làm **file mô hình bằng draw.io desktop 32.7.4** (miễn phí, cài bằng winget): 3 trang gồm mô hình logic (7 thực thể, tên thuộc tính tiếng Hàn, PK/FK/UK, quan hệ chân chim), mô hình vật lý (7 bảng, kiểu dữ liệu, NN, PK/FK/UK, quan hệ) và trang ràng buộc, index, trigger. Nội dung lấy từ chính DB (migrations `0001`–`0005`), đã xem từng ảnh xuất ra. **Giới hạn:** draw.io là công cụ vẽ chung, không đồng bộ hai chiều với DB như erwin; hướng dẫn tạo lại ở `database/model/README.md`. Đồng thời vẫn giữ các bản dump (`cinema_full.sql`, `cinema_full.dump`, `cinema_schema.sql`) trong `database/dump/` (dữ liệu mẫu đến 09/12/2026, nên dump lại trước ngày nộp). Dấu ❓: chưa biết giáo sư có chấp nhận định dạng `.drawio` thay cho file erwin hay không |

**Các tài liệu khác cũng đã cập nhật cho khớp `0005`:** `business_rules_decision_log.md` (D5: ghi quy tắc tên đăng nhập đã duyệt ngày 26/11), `database_test_documentation.md` (mục kiểm chứng `0005`), `handover_reconciliation_report.md` (phụ chú), `database/demo/README.md`, `database/README.md`, `docs/api/api_contract.md`, và "7 index" trong `presentation_content.md`.

## 6. Còn thiếu thông tin (không có trong dự án)

- [ ] Ngày giờ thuyết trình và máy trình chiếu thật (ảnh hưởng mục 2.3 và 2.5)
- [ ] Đề bài gốc của môn: định dạng và nơi nộp, hạn nộp chính thức. Hạn nội bộ trong `chia_viec.md` là 29/11/2026 23:59 KST, nhưng đó không phải của giáo sư
- [ ] Giáo sư có chấp nhận file `.drawio` (draw.io) cho "응용프로그램 + 데이터베이스 통합 파일(.DB)" không. Đã có thêm bản dump làm phương án dự phòng (mục 5, hạng mục 12)
- [ ] Giáo sư có muốn một file DDL gộp và phần chuẩn hóa nằm cùng file mô hình logic không (mục 5, hạng mục 7 và 8)
- [ ] Phương án dự phòng khi demo lỗi (mục 2.7), nếu quyết định có làm
- [ ] Cách trả lời nếu giáo sư hỏi về "không làm admin dashboard" khi web có trang quản trị (mục 3)
