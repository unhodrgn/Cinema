# Nội Dung Thuyết Trình Chi Tiết — Cinema Reservation System

**Tên dự án:** 영화관 예매 및 좌석 관리 시스템 (Hệ thống Đặt vé & Quản lý Ghế Rạp chiếu phim — Cinema Reservation System)  
**Thời lượng mục tiêu:** 15 phút thuyết trình + 5–10 phút hỏi đáp (Q&A)  
**Đối tượng tham gia:** Thành viên A (Database Lead) — **응오후인느** (소프트웨어학과) & Thành viên B (Application Lead) — **응웬치롱** (AI소프트웨어학과). Cả hai cùng trình bày và demo.  
**Ngôn ngữ slide & thuyết trình:** tiếng Hàn — bản PPT: `presentation/cinema_presentation_ko.pptx`  
**Tài liệu đối chiếu:** `presentation/important.md` (yêu cầu của môn học), `chia_viec.md`, `README.md`, `docs/business/*`, `docs/database/*`, `docs/api/api_contract.md`, `PROJECT_PROGRESS.md`, `backend/migrations/*`, `database/demo/*`

---

## 0. Tổng quan Bố cục & Phân bổ Thời gian (15 Phút)

Bài thuyết trình được xây dựng theo **mạch câu chuyện (Storytelling)** từ **Đặt vấn đề → Môi trường & Kiến trúc → Phân tích nghiệp vụ → Thiết kế & Tiến hóa Database → Hiện thực hóa Backend/Frontend → Kiểm chứng đa tầng → Live Demo (UI + SQL) → Giá trị làm việc nhóm trong kỷ nguyên AI**.

| Slide | Chủ đề (Việt / Hàn) | Thời lượng | Mốc thời gian | Đáp ứng yêu cầu `important.md` |
|---|---|---|---|---|
| **01** | Trang bìa & Giới thiệu nhóm (`프로젝트 소개`) | 0:30 | 00:00 – 00:30 | Mở đầu mạch lạc |
| **02** | Bài toán & Quy mô hệ thống (`배경 및 시스템 규모`) | 0:35 | 00:30 – 01:05 | Đặt vấn đề từ bản chất dữ liệu |
| **03** | Môi trường phát triển, DBMS & Công cụ (`개발 환경 및 기술 스택`) | 0:35 | 01:05 – 01:40 | Giải thích cấu hình ban đầu, DBMS, ngôn ngữ, công cụ |
| **04** | Kiến trúc tách biệt Logic & Vật lý (`논리적·물리적 분리 아키텍처`) | 0:50 | 01:40 – 02:30 | Chứng minh DB/Backend/Frontend tách rời độc lập |
| **05** | Phân tích nghiệp vụ & 6 Quyết định cốt lõi (`업무 분석 및 D1–D6`) | 0:55 | 02:30 – 03:25 | Câu chuyện từ 기획 → 분석, 14 chức năng, BR-01~15 |
| **06** | Thiết kế dữ liệu: Conceptual → Logical → 3NF (`데이터 모델링 및 정규화`) | 0:50 | 03:25 – 04:15 | ERD 7 bảng, chuẩn hóa & *Controlled Redundancy* |
| **07** | Thiết kế vật lý & Động cơ toàn vẹn PostgreSQL (`물리 설계 및 무결성 엔진`) | 1:00 | 04:15 – 05:15 | Tính năng lõi: `btree_gist`, Trigger, Lock, Snapshot giá |
| **08** | Đối soát bàn giao & Tiến hóa Schema `0001–0005` (`교차 검증 및 고도화`) | 0:50 | 05:15 – 06:05 | Độ vững chắc thiết kế: phát hiện & sửa lỗi MVCC/NaN |
| **09** | Hiện thực hóa Backend API & Bảo mật (`백엔드 REST API 및 보안`) | 0:40 | 06:05 – 06:45 | Fail-closed policy, Token, SQLSTATE, chống SQLi/XSS |
| **10** | Hiện thực hóa Frontend SPA & Trải nghiệm (`프런트엔드 및 사용자 흐름`) | 0:30 | 06:45 – 07:15 | React 19 + TS + Vite, Responsive, Legacy UI fallback |
| **11** | Kiểm chứng đa tầng & Kết quả (`다층 검증 및 테스트 결과`) | 0:50 | 07:15 – 08:05 | SQL Integrity, Concurrency, Pytest, Node, Playwright |
| **12** | **Live Demo 1:** Trải nghiệm Web UI (`웹 애플리케이션 시연`) | 2:00 | 08:05 – 10:05 | Luồng Customer & Admin thực tế trên Docker Compose |
| **13** | **Live Demo 2:** Kịch bản SQL trực tiếp (`SQL 데이터 제어 시연`) | 3:10 | 10:05 – 13:15 | Chứng minh trạng thái, ngoại lệ, quyền `cinema_api`, đồng thời |
| **14** | **Slide trọng tâm:** Làm việc nhóm trong kỷ nguyên AI (`AI 시대의 팀 프로젝트 의미`) | 1:15 | 13:15 – 14:30 | Câu hỏi bắt buộc cuối/giữa bài dựa trên trải nghiệm thật |
| **15** | Tổng kết & Định hướng (`결론 및 Q&A`) | 0:30 | 14:30 – 15:00 | Chốt giá trị dự án & mở phần hỏi đáp |
| **16** | *Phụ lục:* Bộ câu hỏi Q&A dự kiến & Checklist trước giờ G | — | Q&A (5–10p) | Dự phòng phản biện kỹ thuật |

**Phân công trình bày & demo** (vai trò A/B suy từ lịch sử commit: commit `fix(db)` / `docs(db)` của 응오후인느, commit backend/giao diện của 응웬치롱; nhóm có thể đổi lại):

| Người nói | Slide | Thời lượng |
|---|---|---|
| **응웬치롱** (B) | 01 – 05 (mở đầu, bài toán, môi trường, kiến trúc, nghiệp vụ) | 3:25 |
| **응오후인느** (A) | 06 – 08 (mô hình dữ liệu, thiết kế vật lý, đối soát & migration) | 2:40 |
| **응웬치롱** (B) | 09 – 12 (backend, frontend, kiểm thử, **Live Demo 1 Web UI**) | 4:00 |
| **응오후인느** (A) | 13 (**Live Demo 2 SQL**) | 3:10 |
| Cả hai | 14 (AI 시대 팀 프로젝트): 응오후인느 nói ý 1–2 (hợp đồng, đối soát chéo), 응웬치롱 nói ý 3 và thông điệp chốt | 1:15 |
| **응웬치롱** (B) | 15 (kết luận, mời Q&A) | 0:30 |

Tổng: 응웬치롱 ≈ 8:30, 응오후인느 ≈ 6:30. Q&A: câu hỏi DB/SQL do 응오후인느 trả lời, câu hỏi API/UI/kiểm thử do 응웬치롱 trả lời.

---

## SLIDE 1 — Trang Bìa (Title Slide)

* **Tiêu đề PPT gợi ý:** `영화관 예매 및 좌석 관리 시스템` (Cinema Reservation System)
* **Phụ đề:** `데이터 무결성과 아키텍처 분리를 중심으로 설계·구현·검증한 데이터베이스 팀 프로젝트`
* **Thời lượng:** 00:00 – 00:30

### Nội dung hiển thị trên Slide
- **Tên dự án:** Cinema Reservation System (영화관 예매 및 좌석 관리 시스템)
- **Thời gian thực hiện:** 17/11/2026 – 29/11/2026
- **Thành viên & Vai trò:**
  - **Thành viên A (Database Lead) — 응오후인느 (소프트웨어학과):** Thiết kế ERD, Chuẩn hóa, DDL/Triggers/Constraints PostgreSQL, Dữ liệu mẫu & Kiểm thử DB
  - **Thành viên B (Application Lead) — 응웬치롱 (AI소프트웨어학과):** Phân tích nghiệp vụ, REST API (Flask), Giao diện (React + TypeScript), Tích hợp & Đóng gói Docker
  - **Người trình bày & demo:** cả hai (xem bảng phân công ở mục 0). 응웬치롱 demo Web UI (Slide 12), 응오후인느 demo SQL (Slide 13).
- **Thông điệp chính:** *"Không chỉ xây dựng web đặt vé — mà xây dựng một hệ thống đặt vé không thể bán trùng ghế, không thể chồng lịch chiếu và bảo toàn lịch sử giao dịch ngay ở tầng Database."*

### Lời thoại thuyết trình (Speaker Notes)
> Xin chào thầy/cô và các bạn. Hôm nay nhóm chúng em xin trình bày dự án cuối kỳ: **Hệ thống Đặt vé và Quản lý Ghế Rạp chiếu phim — Cinema Reservation System**.
>
> Trong bài thuyết trình 15 phút hôm nay, nhóm không chỉ liệt kê các màn hình hay tính năng, mà sẽ đi theo câu chuyện xuyên suốt từ lúc **phân tích bài toán, chốt quy tắc nghiệp vụ, thiết kế và đối soát cơ sở dữ liệu, xây dựng kiến trúc tách biệt 3 tầng, kiểm chứng bằng bộ test tự động**, cho đến **demo trực tiếp cả giao diện web lẫn câu lệnh SQL xử lý đồng thời**, và cuối cùng là chia sẻ góc nhìn của nhóm về **ý nghĩa của làm việc nhóm trong kỷ nguyên AI**.

---

## SLIDE 2 — Bài toán & Quy mô Hệ thống

* **Tiêu đề PPT gợi ý:** `01. 프로젝트 배경 및 시스템 규모 (Bối cảnh & Quy mô hệ thống)`
* **Thời lượng:** 00:30 – 01:05

### Nội dung hiển thị trên Slide
- **Vấn đề cốt lõi của nghiệp vụ đặt vé rạp chiếu phim:**
  1. **Tranh chấp ghế (Double Booking):** Hai khách hàng cùng bấm đặt một ghế tại cùng một thời điểm.
  2. **Giữ chỗ vô thời hạn:** Khách đặt vé nhưng không thanh toán làm "chết" ghế của suất chiếu.
  3. **Chồng lịch chiếu (Schedule Overlap):** Hai suất chiếu xếp trùng giờ trong cùng một phòng chiếu.
  4. **Mất vết lịch sử & sai lệch giá:** Hủy vé hoặc đổi giá vé làm hỏng dữ liệu đối soát lịch sử.
- **Quy mô hệ thống chuẩn hóa (`project_overview.md` & `demo.sql`):**
  - **1** Rạp chiếu phim · **5** Phòng chiếu (`Hall 1` ~ `Hall 5`)
  - **50** Ghế/phòng (Hàng `A–E`, Số `1–10`) → **Tổng 250 ghế**
  - **6** Phim mẫu (`movies`) · **280** Suất chiếu trong **14 ngày** liên tiếp (20 suất/ngày theo giờ `Asia/Seoul`)
  - **2** Vai trò tài khoản: `CUSTOMER` và `ADMIN` (không tồn tại tài khoản `GUEST`)

### Lời thoại thuyết trình (Speaker Notes)
> Đặt vé xem phim nhìn qua tưởng là một ứng dụng CRUD đơn giản, nhưng thực chất đây là một **bài toán điển hình về tính toàn vẹn dữ liệu và xử lý đồng thời (concurrency)**.
>
> Có 4 bài toán thực tế buộc hệ thống phải giải quyết triệt để: thứ nhất, không thể để 2 người cùng đặt trúng 1 ghế trong cùng một suất chiếu; thứ hai, vé đã đặt nhưng chưa thanh toán chỉ được phép giữ ghế trong đúng 10 phút; thứ ba, trong cùng một phòng chiếu thì thời gian giữa các suất không được phép chồng lấn; và thứ tư, khi khách hủy vé hay vé hết hạn, ghế phải được nhả ra cho người khác đặt nhưng lịch sử giao dịch và số tiền vẫn phải được bảo toàn.
>
> Hệ thống của nhóm được thiết kế cho 1 rạp gồm 5 phòng chiếu, mỗi phòng 50 ghế (tổng 250 ghế), kèm dữ liệu demo gồm 6 phim và 280 suất chiếu trải dài 14 ngày liên tiếp theo múi giờ `Asia/Seoul`, phục vụ 2 vai trò chính là Khách hàng (`CUSTOMER`) và Quản trị viên (`ADMIN`).

---

## SLIDE 3 — Môi trường Phát triển, DBMS & Công cụ

* **Tiêu đề PPT gợi ý:** `02. 초기 환경 설정 및 기술 스택 (Cấu hình ban đầu & Tech Stack)`
* **Thời lượng:** 01:05 – 01:40

### Nội dung hiển thị trên Slide

| Thành phần | Công nghệ & Phiên bản | Vai trò trong hệ thống |
|---|---|---|
| **DBMS** | **PostgreSQL 18** (`18.6`, tương thích `14+`) + extension `btree_gist` | Lưu trữ quan hệ, ràng buộc khai báo, Trigger, Function giao dịch, khóa đồng thời |
| **Backend API** | **Python 3.12**, **Flask 3.1.3**, **`psycopg2-binary 2.9.13`**, `Werkzeug`, `itsdangerous`, `python-dotenv`, `tzdata` | REST API thuần JSON, xác thực Bearer Token, mapping mã lỗi `SQLSTATE` |
| **Frontend UI** | **React 19.3.1**, **TypeScript 5.9.3**, **Vite 7.3.8** (+ bản dự phòng `legacy` HTML/JS) | Giao diện SPA 12 trang, gọi API qua HTTP, kiểm tra kiểu tĩnh |
| **Container & Runtime** | **Docker Compose v2** (`db`, `api`, `frontend`, profile `test` với `test-db` trên `tmpfs` & `verify`) | Đóng gói độc lập, tự động chạy migration, khởi tạo 1 lệnh |
| **Kiểm thử & Tài liệu** | **pytest 9.2.0**, **Node test runner**, **Playwright 1.65.1**, `psql`, Mermaid | Test đa tầng (SQL, Concurrency, API, Unit JS, E2E trình duyệt) |
| **Làm việc nhóm** | **Git/GitHub** (nhánh + pull request), bảng phân công `chia_viec.md` | Phối hợp giữa Thành viên A và B |

- **Thiết lập môi trường ban đầu (`README.md`):**
  1. Tạo `.env` từ `backend/.env.example`, sinh `SECRET_KEY` và `DB_PASSWORD` ngẫu nhiên.
  2. `docker compose up --build -d --wait` → Tự động khởi tạo DB, áp dụng tuần tự `0001` → `compose-role` → `0002` → `0003` → `0004` → `0005`.
  3. Nạp `backend/seeds/demo.sql` **duy nhất 1 lần** trên DB trống (có cơ chế khóa bảng & chặn chạy đè nếu DB đã có dữ liệu).

### Lời thoại thuyết trình (Speaker Notes)
> Về công nghệ và thiết lập môi trường ban đầu:
> - Ở tầng **Database**, nhóm lựa chọn **PostgreSQL 18** cùng extension **`btree_gist`** vì nhu cầu kiểm tra ràng buộc khoảng thời gian (`tstzrange`) và kiểm soát đồng thời mạnh mẽ.
> - Tầng **Backend** sử dụng **Python 3.12** với **Flask 3.1.3** và driver **`psycopg2-binary`** làm việc trực tiếp bằng SQL tham số hóa — không dùng ORM ẩn, để kiểm soát chính xác ranh giới giao dịch (`transaction`) và bắt trực tiếp mã `SQLSTATE` từ PostgreSQL.
> - Tầng **Frontend** được xây dựng bằng **React 19, TypeScript và Vite** (đồng thời giữ một bản UI HTML/JS dự phòng có thể chuyển qua biến môi trường `CINEMA_LEGACY_UI=1`).
> - Toàn bộ hệ thống được đóng gói bằng **Docker Compose** gồm 3 service chính (`db`, `api`, `frontend`) và 1 profile `test` chuyên biệt chạy DB tạm trên `tmpfs`. Khi cài đặt lần đầu, chỉ cần sinh khóa bí mật vào `.env`, bật Compose để tự động chạy chuỗi migration `0001` đến `0004`, và nạp `demo.sql` một lần duy nhất.
> - Về làm việc nhóm: nhóm dùng Git/GitHub (nhánh, pull request) và bảng phân công `chia_viec.md`.

---

## SLIDE 4 — Kiến trúc Tách biệt Logic & Vật lý

* **Tiêu đề PPT gợi ý:** `03. 논리적·물리적 분리 아키텍처 (Kiến trúc tách biệt 3 tầng)`
* **Thời lượng:** 01:40 – 02:30

### Nội dung hiển thị trên Slide

```
┌─────────────────────────┐      JSON / HTTP + CORS       ┌──────────────────────────┐     PostgreSQL Protocol     ┌─────────────────────────┐
│   Frontend Container    │ ◄───────────────────────────► │    Backend API Container │ ◄─────────────────────────► │   PostgreSQL Container  │
│  (frontend/server.py)   │     (Authorization: Bearer)   │   (Flask REST :5000)     │   (Role: cinema_api)        │    (PostgreSQL :5432)   │
│   Port 8080 · Static    │                               │   static_folder=None     │   Mạng nội bộ Docker        │    Duy nhất API truy cập│
└─────────────────────────┘                               └──────────────────────────┘                             └─────────────────────────┘
```

- **Tách biệt Vật lý (Physical Separation):**
  - **3 tiến trình / 3 container độc lập**, có cấu hình biến môi trường riêng biệt.
  - **PostgreSQL (`:5432`)** chỉ giao tiếp nội bộ với API; ngay cả khi triển khai truy cập qua mạng LAN từ thiết bị thứ hai (`0.0.0.0`), trình duyệt vẫn **không bao giờ** có đường dẫn tới DB.
  - **Frontend (`:8080`)** dùng server tĩnh Python (`frontend/server.py`) phục vụ bản build `dist/`, cấp động địa chỉ API qua `/config.js` (từ biến `API_BASE_URL`), hoàn toàn không có thư viện DB hay code Flask.
- **Tách biệt Logic (Logical Separation):**
  - **Frontend (`frontend/src/`):** Chỉ hiển thị UI, giữ ghế chọn tạm trên trình duyệt, lưu token ở `sessionStorage`. Tuyệt đối không chứa SQL, không tự quyết định quy tắc nghiệp vụ.
  - **Backend (`backend/app/`):** Phân lớp `api/v1/` (HTTP) → `schemas/` (kiểm tra định dạng) → `services/` (transaction) → `models/` (SQL) → `core/` (bảo mật, lỗi, CORS). `Flask(..., static_folder=None, template_folder=None)` — chỉ trả JSON.
  - **Database (`backend/migrations/`):** Thực thi toàn bộ quy tắc toàn vẹn, tính giá, đếm hạn 10 phút theo đồng hồ DB (`clock_timestamp()`).

### Lời thoại thuyết trình (Speaker Notes)
> Một yêu cầu trọng tâm của đồ án là hệ thống phải được tách biệt cả về **mặt logic lẫn vật lý** giữa cơ sở dữ liệu/backend và client.
>
> Như trên sơ đồ kiến trúc 3 tầng, đây là **3 tiến trình và 3 container hoàn toàn độc lập**:
> 1. **Tầng Frontend** chạy ở cổng `8080`, là một ứng dụng React/TypeScript tĩnh được phục vụ qua `frontend/server.py`. Nó không biết bất cứ gì về cấu trúc bảng, không chứa chuỗi kết nối DB, và nhận địa chỉ API lúc chạy qua endpoint `/config.js`.
> 2. **Tầng Backend API** chạy Flask ở cổng `5000`, khởi tạo với `static_folder=None` và `template_folder=None` — nghĩa là server API không render bất kỳ trang HTML nào mà giao tiếp 100% qua JSON và CORS (`Access-Control-Allow-Origin` khớp chính xác origin, không dùng wildcard `*`, không dùng cookie).
> 3. **Tầng Database PostgreSQL** ở cổng `5432` chỉ mở cho API bằng tài khoản runtime **`cinema_api`** có quyền tối thiểu. Mọi tính toán thời gian hết hạn hay giờ chiếu đều lấy từ `clock_timestamp()` của PostgreSQL chứ không dùng đồng hồ của máy chủ ứng dụng hay trình duyệt.

---

## SLIDE 5 — Phân tích Nghiệp vụ & 6 Quyết định Cốt lõi (`BR-DL-001`)

* **Tiêu đề PPT gợi ý:** `04. 업무 기능 분석 및 핵심 규칙 결정 (BR-DL-001: D1–D6)`
* **Thời lượng:** 02:30 – 03:25

### Nội dung hiển thị trên Slide
- **14 Chức năng nghiệp vụ (`business_function.md`) & 15 Quy tắc (`BR-01 ~ BR-15`):**
  - **Chung (`CM-01~02`):** Đăng nhập, Đăng xuất
  - **Khách hàng (`C-01~09`):** Đăng ký, Xem phim/Suất chiếu/Ghế, Chọn ghế tạm, Xác nhận đặt vé, Thanh toán mô phỏng, Xem lịch sử, Hủy vé
  - **Quản trị (`A-01~03`):** Quản lý phim, Quản lý suất chiếu, Xem toàn bộ vé đặt
- **6 Quyết định kiến trúc-nghiệp vụ đã chốt (`BR-DL-001` — 17/11/2026):**

| ID | Quyết định nghiệp vụ | Hệ quả thiết kế hệ thống |
|---|---|---|
| **D1** | Hủy vé (`BOOKED` → `CANCELLED`) | Xóa toàn bộ dòng ở `booking_seats` để nhả ghế; **giữ lại** bản ghi `bookings`, `total_amount` & `payment_status` làm lịch sử. Không hủy lẻ ghế, không luồng hoàn tiền. |
| **D2** | Khóa sửa/xóa suất có lịch sử | Suất chiếu có **bất kỳ** booking nào (`BOOKED`/`CANCELLED`/`EXPIRED`) bị **khóa sửa toàn bộ 5 thuộc tính** (`UC001`). Chỉ xóa được suất/phim chưa chiếu và chưa từng có booking. |
| **D3** | Hết hạn sau **10 phút** | `expires_at = booked_at + 10 min`. Chưa trả quá hạn → `EXPIRED` + xóa `booking_seats`. Triển khai bằng **request-time expiry** (`expire_overdue_bookings()`), không dùng cron ngoài. |
| **D4** | Khách xem không cần đăng nhập | `C-02 ~ C-05` mở công khai; chỉ buộc đăng nhập `CUSTOMER` tại `C-06` (xác nhận đặt). Không tồn tại role `GUEST`. |
| **D5** | Dữ liệu đăng ký & Phim | Đăng ký chỉ nhận `username` + `password` (hash một chiều, tự gán `CUSTOMER`); tên đăng nhập chuẩn hóa NFKC, cắt khoảng trắng, không phân biệt hoa/thường (`0005`). Phim gồm 6 thuộc tính chuẩn + `poster_url` tùy chọn. |
| **D6** | Giá vé theo từng suất chiếu | Không dùng giá cố định toàn rạp; lưu `ticket_price` ở `showtimes`, snapshot `price_at_booking` ở `booking_seats` và tổng `total_amount` ở `bookings`. |

### Lời thoại thuyết trình (Speaker Notes)
> Trước khi viết một dòng DDL hay code nào, nhóm đã phân rã hệ thống thành **14 đơn vị nghiệp vụ** (`CM-01~02`, `C-01~09`, `A-01~03`), **3 lưu đồ quy trình nghiệp vụ (`business_flowchart.md`)** có nhánh lỗi và **15 quy tắc nghiệp vụ (`BR-01~15`)**.
>
> Đặc biệt, để loại bỏ các điểm mơ hồ giữa người làm DB và người làm ứng dụng, nhóm đã lập tài liệu **Nhật ký quyết định nghiệp vụ (`BR-DL-001`)** gồm **6 quyết định D1 đến D6**:
> - Với **D1 & D3**, nhóm tách biệt hai thuộc tính `status` (`BOOKED / CANCELLED / EXPIRED`) và `payment_status` (`UNPAID / PAID`). Khi hủy hoặc quá hạn thanh toán 10 phút, chi tiết ghế ở `booking_seats` được xóa sạch để ghế lập tức có thể đặt lại, còn bản ghi cha ở `bookings` vẫn giữ nguyên làm vết kiểm toán. Thời điểm quá hạn được xử lý theo cơ chế **request-time expiry** — tức là hệ thống tự động quét và hết hạn các vé quá 10 phút ngay trước khi kiểm tra ghế trống, tạo vé, thanh toán hay hủy vé, giúp không cần tiến trình nền phức tạp mà dữ liệu vẫn luôn chính xác tuyệt đối.
> - Với **D2 & D6**, giá vé gắn theo từng suất chiếu và được chụp snapshot lại lúc đặt; một khi suất chiếu đã phát sinh dù chỉ một booking (kể cả đã hủy hay hết hạn), suất chiếu đó bị khóa toàn bộ thông tin để bảo toàn ngữ cảnh lịch sử.

---

## SLIDE 6 — Thiết kế Dữ liệu: Conceptual → Logical → 3NF

* **Tiêu đề PPT gợi ý:** `05. 데이터 모델링 및 정규화 (Mô hình dữ liệu & Chuẩn hóa 1NF–3NF)`
* **Thời lượng:** 03:25 – 04:15

### Nội dung hiển thị trên Slide
- **7 Thực thể / Bảng cốt lõi (Logical ↔ Physical mapping):**
  1. `USERS` (`users`) — Tài khoản (`CUSTOMER` | `ADMIN`)
  2. `MOVIES` (`movies`) — Danh mục phim (6 thuộc tính + `poster_url`)
  3. `ROOMS` (`theater_rooms`) — 5 phòng chiếu (`Hall 1..5`)
  4. `SEATS` (`seats`) — 50 ghế/phòng (`seat_row` A–E, `seat_number` 1–10), **không lưu cột trạng thái ghế toàn cục**
  5. `SCREENINGS` (`showtimes`) — Suất chiếu (`starts_at`, `ends_at`, `ticket_price`)
  6. `BOOKINGS` (`bookings`) — Giao dịch đặt vé (`status`, `payment_status`, `booked_at`, `expires_at`, `total_amount`)
  7. `BOOKING_SEATS` (`booking_seats`) — Chi tiết ghế đang giữ (`booking_id`, `showtime_id`, `seat_id`, `price_at_booking`)
- **Luồng chuẩn hóa (`normalization.md`):**
  - **1NF:** Loại bỏ nhóm lặp (không lưu chuỗi `'A1,A2'` trong `bookings` → tách thành từng dòng ở `booking_seats`).
  - **2NF & 3NF:** Mọi thuộc tính không khóa phụ thuộc toàn phần và trực tiếp vào khóa chính; tên phim/phòng không lặp lại ở `showtimes` hay `bookings`.
- **Dư thừa có kiểm soát (*Controlled Redundancy*) phục vụ nghiệp vụ & đồng thời:**

| Cột lưu trữ | Nguồn suy diễn | Lý do nghiệp vụ/kỹ thuật | Cơ chế giữ đồng bộ |
|---|---|---|---|
| `bookings.total_amount` | `Σ price_at_booking` | Giữ tổng tiền sau khi xóa `booking_seats` khi hủy/hết hạn (`D1, D3`) | Deferred trigger kiểm tra lúc `COMMIT` + bất biến |
| `booking_seats.showtime_id` | `bookings.showtime_id` | Cho phép đánh `UNIQUE(showtime_id, seat_id)` tức thời dưới MVCC | FK kép `(booking_id, showtime_id)` |
| `booking_seats.price_at_booking` | `showtimes.ticket_price` | Chụp snapshot đơn giá tại thời điểm đặt (`D6`) | Trigger ép khớp giá suất chiếu |
| `showtimes.ends_at` | `starts_at + duration` | Sửa `duration_minutes` của phim không làm xê dịch suất đã tạo | `BEFORE` trigger điền mặc định nếu trống |

### Lời thoại thuyết trình (Speaker Notes)
> Về thiết kế dữ liệu, từ mô hình khái niệm gồm **7 thực thể**, nhóm chuyển sang mô hình logic và rà soát chuẩn hóa từ **1NF lên 3NF**:
> - Trước hết, bảng `seats` cố tình **không có cột trạng thái `AVAILABLE/BOOKED`**, vì một chiếc ghế vật lý có thể trống ở suất 10 giờ nhưng đã bán ở suất 13 giờ. Trạng thái ghế được tính động theo từng suất chiếu dựa trên sự tồn tại của dòng hợp lệ trong `booking_seats`.
> - Thứ hai, để tránh lặp nhóm như lưu danh sách `'A1, A2'`, nhóm tách `booking_seats` đạt **1NF**, và kiểm tra phụ thuộc hàm để đảm bảo **2NF và 3NF** trên cả 7 bảng.
> - Tuy nhiên, nhóm cũng chủ động áp dụng **Dư thừa có kiểm soát (Controlled Redundancy)** ở 4 điểm có lý do kỹ thuật rõ ràng: lưu `total_amount` ở `bookings` để giữ doanh thu/lịch sử khi chi tiết ghế bị xóa; lưu snapshot `price_at_booking` và `ends_at` để thay đổi ở bảng phim không làm biến dạng dữ liệu quá khứ; và đặc biệt là lưu `showtime_id` kèm khóa ngoại kép trên `booking_seats` để biến ràng buộc chống đặt trùng ghế thành một `UNIQUE` index tức thời ở tầng DB.

---

## SLIDE 7 — Thiết kế Vật lý & Động cơ Toàn vẹn PostgreSQL

* **Tiêu đề PPT gợi ý:** `06. 물리 설계 및 DB 무결성 엔진 (Thiết kế vật lý & Bảo vệ toàn vẹn)`
* **Thời lượng:** 04:15 – 05:15

### Nội dung hiển thị trên Slide
**Điểm nổi bật kỹ thuật: Đẩy toàn bộ quy tắc bất biến xuống tầng PostgreSQL (`0001`–`0005`)**

1. **Chống chồng lịch chiếu không cần Lock thủ công (`BR-04`):**
   - `EXCLUDE USING gist (room_id WITH =, tstzrange(starts_at, ends_at, '[)') WITH &&)` → Từ chối chồng lấn với `23P01`, cho phép xếp suất nối tiếp sát giờ (`12:00` kết thúc, `12:00` bắt đầu).
2. **Chống đặt trùng ghế an toàn đồng thời (`BR-08`):**
   - Khóa hàng `showtimes ... FOR UPDATE` trong `trg_booking_seats_validate` + `UNIQUE(showtime_id, seat_id)` + FK kép `FOREIGN KEY (booking_id, showtime_id) REFERENCES bookings(booking_id, showtime_id) ON DELETE CASCADE` → Hai người đặt cùng ghế cùng lúc: 1 người thắng, người kia nhận `UC002`.
3. **9 Triggers & 4 Atomic DB Functions:**
   - **Functions (`Flask` chỉ gọi qua 1 transaction):** `create_booking()`, `pay_booking()`, `cancel_booking()`, `expire_overdue_bookings()` (dùng `FOR UPDATE SKIP LOCKED` tránh nghẽn).
   - **Constraint Triggers (`DEFERRABLE INITIALLY DEFERRED`):** `trg_bookings_z_consistency` & `trg_booking_seats_consistency` kiểm tra lúc `COMMIT` rằng vé `BOOKED` phải có `≥ 1` ghế và `total_amount = SUM(price_at_booking)`.
   - **State Machine Trigger (`trg_bookings_validate`):** Khóa mọi chuyển trạng thái trái phép (`UC007`), chặn đặt/hủy sau giờ chiếu (`UC004`, `UC005`), chặn thanh toán quá hạn 10 phút (`UC006`), tự động xóa ghế khi `CANCELLED`/`EXPIRED` (`trg_bookings_release_seats`).
4. **Hiệu năng & Miền giá trị:**
   - 6 Index (gồm **Partial Index** `idx_bookings_pending_expiry ON bookings(expires_at) WHERE status='BOOKED' AND payment_status='UNPAID'`).
   - Kiểu `timestamptz` chuẩn `clock_timestamp()` + `CHECK` chặn `NaN`, `Infinity`, `-Infinity`.

### Lời thoại thuyết trình (Speaker Notes)
> Đây là phần trái tim kỹ thuật của dự án: thay vì tin tưởng các bước kiểm tra rời rạc trên code Python vốn dễ bị race condition, nhóm xây dựng hẳn một **"động cơ toàn vẹn" ngay trong PostgreSQL**.
> - Để chống chồng lịch chiếu trong cùng phòng, nhóm dùng ràng buộc khai báo **`EXCLUDE USING gist`** trên khoảng nửa mở `[starts_at, ends_at)`, vừa an toàn tuyệt đối dưới xử lý song song, vừa cho phép hai suất nối tiếp nhau đúng phút kết thúc.
> - Để chống đặt trùng ghế, nhóm kết hợp **khóa hàng `FOR UPDATE` trên suất chiếu**, **khóa ngoại kép** cố định `showtime_id` và **ràng buộc `UNIQUE(showtime_id, seat_id)`** ngay trên bảng `booking_seats`.
> - Toàn bộ vòng đời đặt vé được đóng gói vào **4 hàm PostgreSQL nguyên tử** (`create_booking`, `pay_booking`, `cancel_booking`, `expire_overdue_bookings`). Đặc biệt, `expire_overdue_bookings()` sử dụng **`FOR UPDATE SKIP LOCKED`** để bỏ qua các dòng đang được người dùng thanh toán hoặc hủy song song, còn các **Deferred Constraint Triggers** sẽ đảm bảo tại thời điểm `COMMIT` không bao giờ tồn tại một đơn `BOOKED` bị rỗng ghế hay lệch tổng tiền.

---

## SLIDE 8 — Câu chuyện Thực tế: Đối soát & Tiến hóa Schema (`0001` → `0005`)

* **Tiêu đề PPT gợi ý:** `07. 교차 검증 및 스키마 고도화 (Đối soát bàn giao & 4 lần nâng cấp Migration)`
* **Thời lượng:** 05:15 – 06:05

### Nội dung hiển thị trên Slide
**Quá trình phát hiện & xử lý lỗi qua kiểm chứng thực tế (`handover_reconciliation_report.md`):**

1. **Mốc 20/11 — Đối soát bàn giao A → B (13 Mismatch → 0 Mismatch):**
   - Bản DDL đầu tiên của A chạy tốt mô hình cũ (`CONFIRMED`), nhưng đối chiếu với `BR-DL-001` lộ ra: thiếu `EXPIRED` & `expires_at` (`D3`), thiếu khóa `ticket_price` khi có booking (`D2`), thiếu 3 cột phim (`D5`), và tự ý thêm buffer dọn phòng 15 phút (`X1`) + khóa `duration_minutes` (`X2`).
   - Kết quả: Chốt 11 đầu mục chỉnh sửa `DB-01 ~ DB-11` thành **`0001_baseline.sql`**.
2. **Phát hiện lỗi thứ tự Trigger theo bảng chữ cái (`SET CONSTRAINTS ALL IMMEDIATE`):**
   - Trong PostgreSQL, các `AFTER` trigger cùng sự kiện chạy theo **thứ tự alphabet**. Ban đầu trigger kiểm tra nhất quán chạy trước `trg_bookings_release_seats` → lỗi khi hủy/hết hạn ở chế độ `IMMEDIATE`. Đã đổi tên thành `trg_bookings_z_consistency` và thêm regression test.
3. **Chuỗi nâng cấp `0002` → `0003` → `0004` → `0005`:**
   - **`0002_movie_delete_permissions.sql`:** Cấp quyền `DELETE` trên `movies`, `showtimes` cho runtime role `cinema_api` để hỗ trợ xóa phim/suất có điều kiện.
   - **`0003_booking_integrity.sql`:** Đưa `showtime_id` lên `booking_seats` thành `UNIQUE(showtime_id, seat_id)` tức thời (chặn kẽ hở MVCC snapshot), thêm `trg_bookings_z_version_showtime` đánh dấu phiên bản suất khi có vé đầu tiên, và mở rộng `total_amount` từ `numeric(10,2)` lên **`numeric(12,2)`** (đủ chứa 50 ghế × `99,999,999.99` = `4,999,999,999.50`).
   - **`0004_finite_money.sql`:** Trong PostgreSQL, `'NaN'::numeric >= 0` trả về `TRUE`! Đã bổ sung 3 ràng buộc `CHECK (... NOT IN ('NaN', 'Infinity', '-Infinity'))` để khóa chặt miền tiền tệ.
   - **`0005_username_case_insensitive.sql`:** Qua rà soát đối kháng, `Customer1`, ` customer1 ` và `ａｄｍｉｎ` (full-width) từng đăng ký được thành tài khoản riêng. Nay API chuẩn hóa NFKC + cắt khoảng trắng và so trùng không phân biệt hoa/thường; DB có unique index `users_username_lower_key` trên `lower(username)`. Migration tự kiểm dữ liệu và dừng (23505/23514) nếu có tên trùng hoặc chưa chuẩn hóa, không sửa dữ liệu.

### Lời thoại thuyết trình (Speaker Notes)
> Hệ thống vững chắc hiện tại không tự nhiên sinh ra trong lần code đầu tiên, mà là kết quả của quá trình **đối soát chéo và sửa lỗi liên tục**.
>
> Khi Thành viên A bàn giao bản Database đầu tiên ngày 20/11, Thành viên B đã viết một bộ **Reconciliation Probes** chạy kiểm tra từng quy tắc D1–D6 và phát hiện **13 điểm lệch**: bản cũ vẫn dùng trạng thái `CONFIRMED`, chưa có hạn 10 phút, chưa khóa giá vé trong trigger `D2`, thậm chí có thêm quy tắc "nghỉ 15 phút giữa 2 suất" không nằm trong đặc tả. Sau khi đối soát qua `DB-01` đến `DB-11`, nhóm thống nhất bản chuẩn `0001_baseline.sql`.
>
> Tiếp đó, quá trình kiểm thử sâu tiếp tục giúp nhóm phát hiện và nâng cấp qua 4 migration: `0002` bổ sung quyền xóa phim có điều kiện cho role `cinema_api`; `0003` bổ sung `UNIQUE` tức thời theo `(showtime_id, seat_id)` chống kẽ hở MVCC giữa các mức cô lập giao dịch và nâng `total_amount` lên `numeric(12,2)` để không tràn số khi đặt cả phòng 50 ghế; và `0004` xử lý một bẫy đặc thù của PostgreSQL: kiểu `numeric` coi `'NaN' >= 0` là hợp lệ, nên nhóm đã thêm 3 ràng buộc từ chối `NaN` và vô cực ở tầng DB; cuối cùng `0005` chuẩn hóa tên đăng nhập (NFKC, cắt khoảng trắng, không phân biệt hoa/thường) sau khi rà soát đối kháng cho thấy `Customer1` hay `ａｄｍｉｎ` từng đăng ký được thành tài khoản riêng.

---

## SLIDE 9 — Hiện thực hóa Backend API & Bảo mật

* **Tiêu đề PPT gợi ý:** `08. 백엔드 REST API 및 다층 보안 (Backend REST API & Bảo mật)`
* **Thời lượng:** 06:05 – 06:45

### Nội dung hiển thị trên Slide
- **28 REST Endpoints (`docs/api/api_contract.md`):**
  - Health & Meta (3): `/api`, `/health`, `/health/db`
  - Auth (4): `/api/auth/{register,login,me,logout}`
  - Public Catalog & Seats (5): `/api/movies`, `/api/movies/{id}`, `/api/screenings`, `/api/screenings/{id}`, `/api/screenings/{id}/seats`
  - Customer Bookings (5): `POST /api/bookings`, `GET /api/bookings`, `GET /api/bookings/{id}`, `POST /api/bookings/{id}/pay`, `POST /api/bookings/{id}/cancel`
  - Admin Management (11): CRUD + conditional `DELETE` cho `/api/admin/movies*`, `/api/admin/screenings*`, và lọc `GET /api/admin/bookings`
- **Các cơ chế phòng thủ tại Backend (`backend/app/core/`):**
  - **Fail-Closed Route Policies:** Mọi route bắt buộc gắn `@policy(PUBLIC | AUTHENTICATED | CUSTOMER | ADMIN)` — `create_app()` **từ chối khởi động** nếu có route quên phân quyền.
  - **Stateless Token + Live DB Lookup:** Token `itsdangerous` (`URLSafeTimedSerializer`, mặc định 8 giờ) chỉ chứa `user_id` (không lưu role/username); mỗi request đều tải lại dòng `users` hiện tại từ PostgreSQL nên tài khoản bị đổi role hoặc bị xóa sẽ mất hiệu lực ngay lập tức.
  - **Chống lộ thông tin & Lỗi chuẩn hóa:** Mapping `e.pgcode` (`UC001~UC011`, `23P01`, `23505`, `23514`, `23503`, `22003`) sang JSON `{"error": {"code", "message"}}` — không bao giờ trả SQL, stack trace hay tên cột ra client. Sai ID hoặc sai mật khẩu trả cùng thông báo `401 invalid_credentials` và thực hiện hash giả để tránh timing attack.
  - **Tự thử lại giao dịch (`40001` / `40P01`):** `run_retryable_transaction()` (`backend/app/core/database.py`) chạy lại toàn bộ thao tác trong một transaction mới, tối đa 3 lần, khi PostgreSQL báo serialization failure (`40001`) hoặc deadlock (`40P01`); áp dụng cho đặt vé (`booking_service.reserve`), thanh toán (`payment_service.pay`) và hủy vé (`bookings.cancel_booking`).
  - **Bảo mật HTTP & Injection:** 100% SQL tham số hóa (`%s`), `MAX_CONTENT_LENGTH = 64 KiB`, header `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'`.

### Lời thoại thuyết trình (Speaker Notes)
> Trên nền tảng database đó, tầng Backend cung cấp **28 REST API endpoint** chuẩn hóa toàn bộ bằng JSON.
>
> Điểm nhấn của Backend là thiết kế bảo mật theo nguyên tắc **Fail-Closed**: mỗi endpoint bắt buộc khai báo một trong 4 mức quyền (`PUBLIC`, `AUTHENTICATED`, `CUSTOMER`, `ADMIN`); nếu lập trình viên lỡ thêm một route mà quên gắn phân quyền, hàm `check_route_policies()` sẽ chặn không cho Flask khởi động. Token xác thực được ký bằng `itsdangerous` chỉ chứa duy nhất `user_id`, không lưu `role`, và ở mỗi request API đều truy vấn lại bảng `users` thực tế.
>
> Toàn bộ lỗi từ PostgreSQL được dịch thông qua mã `pgcode` (`UC001` đến `UC011` và các mã chuẩn `23xxx`) thành thông báo JSON an toàn cho người dùng, tuyệt đối không làm rò rỉ câu lệnh SQL hay tên ràng buộc. Kèm theo đó là truy vấn tham số hóa hoàn toàn để chống SQL Injection và các header bảo mật chặt chẽ trên mọi phản hồi.
>
> Ngoài ra, khi PostgreSQL hủy một giao dịch vì xung đột tuần tự hóa (`40001`) hoặc deadlock (`40P01`), backend không báo lỗi ngay mà chạy lại toàn bộ thao tác trong một transaction mới, tối đa 3 lần. Cơ chế này chỉ dùng cho các thao tác an toàn khi chạy lại từ đầu: đặt vé, thanh toán và hủy vé.

---

## SLIDE 10 — Hiện thực hóa Frontend SPA & Trải nghiệm Người dùng

* **Tiêu đề PPT gợi ý:** `09. 프런트엔드 SPA 및 사용자 흐름 (Giao diện React/TS & Trải nghiệm)`
* **Thời lượng:** 06:45 – 07:15

### Nội dung hiển thị trên Slide
- **Kiến trúc Frontend (`frontend/src/`):**
  - **12 trang độc lập tương ứng URL rõ ràng:** `index.html`, `movies.html`, `movie.html`, `screenings.html`, `seats.html`, `booking.html`, `bookings.html`, `login.html`, `register.html`, `admin-movies.html`, `admin-screenings.html`, `admin-bookings.html`.
  - **Đồng bộ trải nghiệm mượt mà (`D4` + `D3`):**
    - Khách chưa đăng nhập vẫn xem phim, chọn suất, chọn ghế trên sơ đồ 50 ghế (`A1–E10`).
    - Khi bấm *"Proceed to booking"*, hệ thống điều hướng qua `login.html?next=...` / `register.html` và **giữ nguyên lựa chọn ghế** quay lại màn hình đặt vé sau khi đăng nhập.
    - Hiển thị đồng hồ đếm ngược 10 phút (`CountdownTimer.tsx` & `useCountdown.ts`) từ `expires_at` của server.
    - **Chống nhấn đúp khi đặt vé:** Khóa đồng bộ bằng `useRef(false)` (`inFlight.current`) + trạng thái `aria-busy` trên nút *"Booking…"*.
- **An toàn phía Client & Khả năng tương thích:**
  - Server tĩnh (`frontend/server.py`) áp dụng `Content-Security-Policy` chặn script ngoài, không dùng `innerHTML`, render toàn bộ dữ liệu API dưới dạng text an toàn trước Stored XSS.
  - Chuẩn hóa hiển thị qua `frontend/js/format.js`: xử lý chuỗi tiền tệ `"12000.00"` → `₩12,000` bằng regex (không ép kiểu số thực floating-point) và hiển thị giờ theo đúng chuỗi offset `Asia/Seoul` từ API (không bị lệch theo múi giờ trình duyệt).
  - Responsive đã kiểm thử trên nhiều độ rộng màn hình (`320px`, `375px`, `768px`, `1024px`, `1440px`).
  - Hỗ trợ chuyển nhanh sang giao diện dự phòng (`dist-legacy/`) qua `CINEMA_LEGACY_UI=1`.

### Lời thoại thuyết trình (Speaker Notes)
> Về phía người dùng, giao diện gồm **12 trang React + TypeScript** đáp ứng đầy đủ cả luồng Khách hàng và Quản trị viên.
>
> Nhóm chú trọng 3 trải nghiệm thực tế: thứ nhất, đúng với quyết định `D4`, khách vãng lai có thể xem lịch chiếu và chọn ghế trước, sau khi đăng nhập hoặc đăng ký mới thì lựa chọn ghế vẫn được bảo lưu liền mạch; thứ hai, màn hình thanh toán hiển thị đếm ngược 10 phút dựa trên mốc `expires_at` do PostgreSQL trả về, kết hợp khóa `inFlight` đồng bộ ở nút đặt vé để tránh người dùng bấm đúp gửi hai request cùng lúc; và thứ ba, giao diện không bao giờ dùng `innerHTML`, kết hợp với `Content-Security-Policy` của server tĩnh để vô hiệu hóa Stored XSS và hiển thị gọn gàng từ màn hình điện thoại `320px` đến desktop `1440px`.

---

## SLIDE 11 — Kiểm chứng Đa tầng & Kết quả Kiểm thử

* **Tiêu đề PPT gợi ý:** `10. 다층 검증 전략 및 테스트 결과 (Kiểm thử toàn diện & Kết quả)`
* **Thời lượng:** 07:15 – 08:05

### Nội dung hiển thị trên Slide
**Hệ thống được kiểm thử độc lập trên 5 tầng qua `docker compose --profile test run --build --rm verify` và `backend/tests/verify.py`:**

| Tầng kiểm thử | Bộ test & Công cụ | Phạm vi & Kết quả ghi nhận |
|---|---|---|
| **1. SQL Toàn vẹn & Đối soát** | `integrity_tests.sql`, `reconciliation_probes.sql`, `money_domain.sql` | **177** kiểm tra toàn vẹn (baseline `run_all.sh`), **31/31 MATCH** (0 mismatch), kiểm tra `0004` miền tiền tệ; **5 mutation checks** xác nhận bộ test phát hiện được lỗi cố tình cài vào. |
| **2. Đồng thời đa phiên DB** | `test_booking_concurrency.py` (6 kịch bản `C1–C6`, đa luồng `psycopg2`) | **16/16 checks PASS**: 8 phiên tranh 1 ghế (1 thắng, 7 `UC002`), khóa 2 phiên `C2`, 40 luồng trả tiền vs 2 luồng hết hạn tại mốc 10 phút (`C4`), trả tiền vs hủy (`C5`), 5 luồng hết hạn song song (`C6`). |
| **3. Backend API & Bảo mật** | `pytest` (`test_access_matrix`, `test_booking_flow`, `test_security_injection.py`, ...) | **1.409 pytest đạt**, skip 1 (ca chỉ dành cho Windows) — chạy `verify` trên Docker Compose ngày 26/11/2026 sau commit `80092c6`. Bổ sung active SQLi & Stored XSS suite (`test_security_injection.py`) và `test_migration_upgrade.py` (4 test nâng cấp `0001→0003→0004` trên DB tạm). |
| **4. Logic Frontend** | `npm test` (Node test runner) + `npm run build` (`tsc --noEmit`) | **121/121 Node tests PASS**; kiểm tra type TypeScript không lỗi. |
| **5. E2E Trình duyệt & DB Dump/Restore** | Playwright (`reservation.spec.ts` — 6 luồng), `pg_dump -Fc` / `pg_restore` | **6/6 luồng E2E PASS** (mobile `320px`/`375px`, desktop `1440px`, `UI-01` double-click/bàn phím/retry/reload-Back-Forward & `SEC-01` XSS); đối chiếu checksum cả 7 bảng sau backup/restore khớp 100%. |

### Lời thoại thuyết trình (Speaker Notes)
> Nhóm không chỉ kiểm tra bằng tay trên giao diện, mà xây dựng một đường ống kiểm chứng tự động 5 tầng chạy trên database cô lập hoàn toàn qua lệnh `docker compose --profile test run --build --rm verify`:
> - Ở tầng SQL, **177 kiểm tra toàn vẹn** và **31 đầu dò đối soát** đều đạt, kèm **5 bài test đột biến (mutation checks)** — tức là nhóm cố tình làm hỏng trigger rồi chạy lại test để chắc chắn bộ test thực sự bắt được lỗi.
> - Ở tầng đồng thời, `test_booking_concurrency.py` chạy **6 kịch bản đa phiên thật (`C1–C6`)**, như cho 8 kết nối tranh nhau 1 ghế, hoặc cho 40 luồng thanh toán đụng độ với 2 luồng hết hạn ngay tại mốc 10 phút để chứng minh không bao giờ có ca thanh toán muộn nào lọt qua.
> - Ở tầng ứng dụng, bản kiểm thử Compose đạt **1.409 ca pytest**, **121 bài Node test**, **6 kịch bản Playwright E2E** chạy HTTP thật trên cả mobile lẫn desktop (gồm chống nhấn đúp/retry/Back-Forward `UI-01` và XSS `SEC-01`), cùng suite `test_security_injection.py` chủ động kiểm tra SQL Injection và Stored XSS trên toàn bộ các endpoint. Sau tất cả, nhóm còn kiểm tra `pg_dump` và `pg_restore` để xác nhận checksum toàn bộ 7 bảng khớp 100%.

---

## SLIDE 12 — Kịch bản Live Demo 1: Trải nghiệm Web UI (2 Phút)

* **Tiêu đề PPT gợi ý:** `11. 실시간 시연 ① — 웹 애플리케이션 (Demo trực tiếp trên Web UI)`
* **Thời lượng:** 08:05 – 10:05

### Nội dung hiển thị trên Slide
**Môi trường:** `http://localhost:8080` (Frontend) ↔ `http://localhost:5000/health/db` (API + PostgreSQL Compose)

- **Bước 1 — Khách vãng lai → Đặt vé & Thanh toán (60 giây):**
  1. Mở trang chủ `http://localhost:8080` (chưa đăng nhập) → vào một phim → chọn suất chiếu tương lai → chọn ghế `A1, A2`.
  2. Bấm **Proceed to booking** → hệ thống chuyển sang `/login.html?next=...`, đăng nhập bằng `customer1` / `customer1234` → **ghế `A1, A2` vẫn giữ nguyên**.
  3. Xác nhận đặt vé (`BOOKED` + `UNPAID`, thấy đồng hồ đếm ngược 10 phút và tổng `₩24,000` = 2 ghế × ₩12,000 — giá demo của dữ liệu mẫu, không phải mức giá đã được nhóm duyệt).
  4. Bấm **Pay Now** → trạng thái chuyển `PAID`.
  5. Vào **My Bookings** → bấm **Cancel** (xác nhận hộp thoại) → trạng thái chuyển `CANCELLED` (giữ `PAID` và tổng tiền). Quay lại suất chiếu đó → `A1, A2` đã mở lại màu trống (`available`)!
- **Bước 2 — Quản trị viên & Quy tắc bảo vệ D2 (60 giây):**
  1. Đăng nhập `admin` / `admin1234` → vào **Manage Movies** (`admin-movies.html`) tạo nhanh 1 phim mới.
  2. Vào **Screenings (Admin)** (`admin-screenings.html`) thử tạo suất chiếu trùng giờ cùng phòng → API chặn với lỗi trùng lịch (`409 screening_overlap`). Tạo suất hợp lệ cho phim mới.
  3. Mở một suất chiếu **đã có booking** (suất vừa đặt ở Bước 1) và thử đổi giá vé → bị chặn theo quy tắc **D2** (`409 screening_has_bookings`).
  4. Vào **All Bookings** (`admin-bookings.html`) lọc theo trạng thái `CANCELLED` để xem lịch sử được bảo toàn.

### Lời thoại thuyết trình (Speaker Notes)
> Bây giờ nhóm xin chuyển sang phần **Demo trực tiếp**. Trước tiên là luồng ứng dụng web đang chạy trên 3 container Docker tách biệt tại `localhost:8080`.
> *(Thao tác theo từng bước trên màn hình và thuyết minh ngắn gọn)*:
> - Hiện em chưa đăng nhập, vẫn có thể xem 6 phim, chọn một suất chiếu ngày mai và chọn ghế `A1, A2`. Khi bấm đặt vé, hệ thống yêu cầu đăng nhập. Em đăng nhập bằng tài khoản `customer1` — ngay lập tức trang web đưa quay lại đúng 2 ghế vừa chọn.
> - Sau khi bấm xác nhận, vé được tạo ở trạng thái `BOOKED / UNPAID`, hiện tổng tiền `₩24,000` (giá demo 12.000 mỗi ghế) và hạn thanh toán 10 phút. Em bấm thanh toán mô phỏng (`Pay Now`) để chuyển sang `PAID`. Tiếp theo, em vào *My Bookings* và hủy vé này: trạng thái thành `CANCELLED` nhưng lịch sử tiền và trạng thái `PAID` vẫn giữ nguyên, còn khi mở lại sơ đồ ghế suất chiếu vừa rồi thì ghế `A1, A2` đã xanh trở lại.
> - Bây giờ em chuyển sang quyền `admin`: tạo nhanh một phim mới, sau đó thử tạo một suất chiếu cố tình trùng giờ trong Hall 1 — hệ thống lập tức từ chối do ràng buộc `EXCLUDE` của PostgreSQL. Cuối cùng, khi thử sửa giá của suất chiếu vừa có lịch sử hủy vé lúc nãy, hệ thống cũng chặn theo quy tắc `D2`, và trong trang *All Bookings* chúng ta vẫn tra cứu được đầy đủ vé `CANCELLED` đó.

---

## SLIDE 13 — Kịch bản Live Demo 2: Chứng minh trực tiếp bằng SQL (3 Phút 10 Giây)

* **Tiêu đề PPT gợi ý:** `12. 실시간 시연 ② — SQL 데이터 제어 및 예외·권한 검증 (Demo SQL trực tiếp)`
* **Thời lượng:** 10:05 – 13:15

### Nội dung hiển thị trên Slide
**Bộ script chuẩn bị sẵn trong `database/demo/` (chạy trên DB cô lập `cinema_test_demo`, tự động `ROLLBACK` sạch dữ liệu mẫu):**

1. **`database/demo/main.sql` — Vòng đời đặt, trả tiền, hủy & đặt lại ghế:**
   - Kiểm tra DB cô lập & số liệu (6 phim / 250 ghế / 280 suất).
   - `create_booking(...)` 2 ghế → `BOOKED / UNPAID / 24,000.00`.
   - `pay_booking(...)` → `cancel_booking(...)` → xác nhận `CANCELLED / PAID / 24,000.00` và `active_seats = 0`.
   - Khách khác (`user 3`) gọi `create_booking(...)` đúng ghế số 1 vừa hủy → **Thành công**.
2. **`database/demo/exceptions.sql` — Chứng minh các ngoại lệ ngay tại DB:**
   - Đặt trùng ghế → **`UC002`**
   - Đặt ghế thuộc phòng khác (`seat_id = 51` ở Hall 2 cho suất Hall 1) → **`UC003`**
   - Thêm suất chiếu trùng giờ cùng phòng → **`23P01`** (`EXCLUDE USING gist`)
   - Nhập giá `'NaN'::numeric` hoặc `-1` → **`23514`** (`0004` finite money + non-negative check)
3. **`database/demo/permissions_grants.sql` — Role, GRANT/REVOKE và truy vấn kiểm tra quyền (`cinema_api`):**
   - Thuộc tính role `cinema_api`: có `LOGIN`, không phải superuser, không tạo được DB/role.
   - Bảng quyền `has_table_privilege` theo 7 bảng × `SELECT/INSERT/UPDATE/DELETE/TRUNCATE`, và danh sách quyền từ `information_schema.role_table_grants`.
   - Chạy trực tiếp `REVOKE INSERT ON showtimes` → `has_table_privilege` đổi `true → false`, rồi `GRANT INSERT` trả lại (trong transaction, `ROLLBACK` ở cuối).
   - `SET LOCAL ROLE cinema_api`: đọc được `movies`, nhưng `DELETE bookings`, `UPDATE seats`, `UPDATE users` đều bị từ chối với **`42501` (`insufficient_privilege`)**.
4. *(Dự phòng, đã có từ trước)* **`database/demo/permissions.sql`:** `SET LOCAL ROLE cinema_api`, cho phép `INSERT` `showtimes`, từ chối `DELETE FROM bookings` (`42501`).
5. *(Dự phòng nếu Q&A hỏi về tranh chấp 2 phiên)* **`concurrency_prepare.sql` + `concurrency_a.sql` / `concurrency_b.sql`:**
   - Phiên A giữ lock chưa commit; Phiên B chờ cho đến khi A commit và lập tức bị đẩy ra với **`UC002`**, chỉ còn đúng 1 ghế được giữ.

- **Phân bổ 3:10 (đề xuất, cần tập lại):** `main.sql` ~0:55 · `exceptions.sql` ~0:50 · `permissions_grants.sql` ~1:05 · dự phòng ~0:20. `database/demo/README.md` ghi kịch bản chính 3–4 phút, nên khi thiếu giờ thì bỏ `permissions.sql` cũ và các script `concurrency_*` (để dành cho Q&A).

### Lời thoại thuyết trình (Speaker Notes)
> Theo đúng yêu cầu chuẩn bị script SQL kiểm soát dữ liệu và kiểm tra ngoại lệ, nhóm đã chuẩn bị sẵn bộ script trong thư mục `database/demo/` chạy trên một database cô lập tên `cinema_test_demo`.
> *(Chạy lần lượt `main.sql`, `exceptions.sql`, `permissions_grants.sql` trên terminal đã mở sẵn)*:
> - Đầu tiên, `main.sql` thực thi trực tiếp các hàm PostgreSQL: tạo vé 2 ghế (`24,000.00`), thanh toán, rồi hủy. Như thấy trên kết quả `SELECT`, `bookings` vẫn giữ nguyên `CANCELLED / PAID / 24,000.00` nhưng `active_seats` bằng `0`, nên khách hàng số 3 ngay lập tức đặt lại được ghế số 1.
> - Thứ hai, `exceptions.sql` chứng minh ngay cả khi gọi thẳng SQL không qua Flask API, PostgreSQL vẫn tự chặn toàn bộ vi phạm: trùng ghế báo `UC002`, ghế sai phòng báo `UC003`, trùng lịch phòng báo `23P01`, và giá `'NaN'` hay số âm báo `23514`.
> - Cuối cùng, `permissions_grants.sql` trả lời phần phân quyền: bảng quyền thực tế của role `cinema_api` mà Backend dùng; sau đó nhóm chạy `REVOKE INSERT` trên `showtimes` để thấy `has_table_privilege` đổi từ `true` sang `false`, rồi `GRANT` lại; cuối cùng chuyển sang `SET LOCAL ROLE cinema_api` và thử `DELETE bookings`, `UPDATE seats`, `UPDATE users` — cả ba bị chặn với mã `42501`. *(Nếu còn thời gian hoặc vào phần Q&A, nhóm có sẵn `permissions.sql` và kịch bản 2 terminal `concurrency_a.sql` / `concurrency_b.sql` để trình diễn cơ chế lock đa phiên.)*

---

## SLIDE 14 — Ý nghĩa của Dự án Nhóm trong Kỷ nguyên AI *(Slide Bắt Buộc)*

* **Tiêu đề PPT gợi ý:** `13. AI가 모든 것을 다 해주는 시대에 팀 단위 프로젝트가 왜 의미가 있는가?`
* **Thời lượng:** 13:15 – 14:30

### Nội dung hiển thị trên Slide
**Câu hỏi:** *"Trong thời đại AI có thể làm hộ mọi thứ, vì sao dự án làm việc theo nhóm vẫn có ý nghĩa?"*

**Câu trả lời từ trải nghiệm thực tế của nhóm (Dự án Cinema, 17/11 – 29/11):**
> **AI có thể viết code nhanh khi có yêu cầu rõ ràng — nhưng AI không tự chịu trách nhiệm cho ranh giới nghiệp vụ, sự đồng thuận giữa con người, và việc phát hiện điểm mù chéo giữa các tầng hệ thống.**

1. **Chốt quyết định & Hợp đồng giao tiếp (Decision Ownership & Contracts):**
   - AI không thể tự quyết thay nhóm việc nên giữ hay xóa ghế khi hủy (`D1`), hạn 10 phút (`D3`), hay không tạo role `GUEST` (`D4`).
   - Nhờ phân vai **A (Database Lead)** và **B (Application Lead)**, nhóm buộc phải viết rõ **`BR-DL-001`**, **`postgresql_flask_integration_contract.md`** và **`api_contract.md`** để hai bên chạy song song mà không gãy khi tích hợp.
2. **Phản biện chéo để loại bỏ "ảo giác hợp lý" (Cross-Review & Reconciliation):**
   - Ngày 20/11, bản schema bàn giao ban đầu trông rất sạch và tự vượt qua test nội bộ của chính nó — nhưng khi thành viên còn lại đối soát chéo (`handover_reconciliation_report.md`), nhóm phát hiện **13 điểm lệch nghiệp vụ** (thiếu `EXPIRED`, thiếu khóa giá `D2`, tự thêm buffer 15 phút `X1`).
   - Khi làm một mình với AI, người ta rất dễ tin vào một kết quả "chạy được trên bề mặt"; làm nhóm tạo ra **áp lực phản biện độc lập**.
3. **Kỷ luật kiểm chứng & Trách nhiệm đầu-cuối (Accountability):**
   - Các lỗi biên thực tế (thứ tự trigger alphabet ở `IMMEDIATE`, kẽ hở MVCC ở `READ COMMITTED` dẫn tới `0003`, hay lỗi `NaN >= 0` của PostgreSQL dẫn tới `0004`) chỉ lộ ra khi người phụ trách DB và người phụ trách App cùng ép hệ thống qua bài test thực chiến.

- **Thông điệp chốt:** Trong kỷ nguyên AI, giá trị của làm việc nhóm chuyển từ *"chia nhau gõ code"* sang **"cùng định nghĩa đúng bài toán, thiết lập hợp đồng giao diện, phản biện chéo điểm mù và cùng chịu trách nhiệm cho hệ thống vận hành thật."**

### Lời thoại thuyết trình (Speaker Notes)
> Cuối cùng, nhóm xin chia sẻ câu trả lời cho câu hỏi đặt ra trong đề bài: **"Trong thời đại AI có thể làm mọi thứ, vì sao dự án làm việc theo nhóm vẫn có ý nghĩa?"**
>
> Từ trải nghiệm 2 tuần làm dự án Cinema này, nhóm nhận ra: **có ý nghĩa, thậm chí còn quan trọng hơn trước** — nhưng trọng tâm đã thay đổi.
>
> AI có thể sinh ra hàng trăm dòng SQL hay React trong vài giây, nhưng AI không biết khách hàng và nhóm mong muốn quy tắc nào, và càng không chịu trách nhiệm khi hai phần của hệ thống không khớp nhau.
>
> Thứ nhất, làm việc nhóm buộc chúng em phải **định nghĩa ranh giới và ký "hợp đồng kỹ thuật"**. Việc phân vai Thành viên A giữ toàn vẹn dữ liệu và Thành viên B giữ nghiệp vụ ứng dụng đã tạo ra bộ quyết định `D1–D6` và hai bản hợp đồng tích hợp rõ ràng để hai phía phát triển song song.
>
> Thứ hai — đây là bài học lớn nhất của nhóm — là **sức mạnh của phản biện chéo**. Khi bản DDL đầu tiên được bàn giao ngày 20/11, nó chạy không lỗi và qua hết test tự viết, nhưng khi người phụ trách ứng dụng thực hiện đối soát độc lập lại từng yêu cầu, nhóm phát hiện ra tới **13 điểm lệch nghiệp vụ** và những quy tắc bị tự ý thêm vào như khoảng nghỉ 15 phút. Nếu chỉ một người dùng AI, rất dễ rơi vào trạng thái tự hài lòng với code "tưởng là đúng". Nhờ làm nhóm, hai góc nhìn độc lập đã liên tục kiểm tra nhau, tìm ra cả lỗi thứ tự trigger theo bảng chữ cái, lỗi đồng thời MVCC ở migration `0003` và bẫy `NaN` ở migration `0004`.
>
> Vì vậy, trong thời đại AI, làm việc nhóm không còn là chia việc gõ code, mà là **cùng tư duy thiết kế, thiết lập hợp đồng rõ ràng, phản biện điểm mù cho nhau và cùng chịu trách nhiệm đến tận khâu vận hành cuối cùng**.

---

## SLIDE 15 — Tổng kết & Hướng Mở rộng

* **Tiêu đề PPT gợi ý:** `14. 결론 및 향후 계획 (Tổng kết & Hướng phát triển)`
* **Thời lượng:** 14:30 – 15:00

### Nội dung hiển thị trên Slide
- **Những gì hệ thống đã đạt được:**
  - Thiết kế CSDL chuẩn hóa 3NF, bảo vệ toàn vẹn và đồng thời ngay tại tầng PostgreSQL 18 (`0001`–`0005`).
  - Kiến trúc 3 tầng tách biệt vật lý & logic hoàn chỉnh trên Docker Compose.
  - Đầy đủ 14 đơn vị nghiệp vụ, 28 API endpoints, 12 trang React/TS + bản UI dự phòng.
  - Kiểm chứng toàn diện: 177 SQL integrity checks, 31 reconciliation probes, 16 concurrency checks, 1.409 pytest, 121 Node tests, 6 Playwright E2E, upgrade migration `0001→0003→0004→0005`, active SQLi/XSS & dump/restore checksum.
- **Hướng mở rộng (nằm ngoài phạm vi MVP hiện tại):**
  - Tích hợp cổng thanh toán thật & luồng hoàn tiền cho vé `CANCELLED + PAID`.
  - Cơ chế thu hồi token phía server (Token Revocation / Redis) & HTTPS Reverse Proxy.
  - Hỗ trợ nhiều cụm rạp, chỉnh sửa sơ đồ ghế linh hoạt và đặt combo bắp nước.
- **Lời cảm ơn:** 감사합니다! 질의응답을 받겠습니다. (Xin cảm ơn! Nhóm xin sẵn sàng nhận câu hỏi Q&A.)

### Lời thoại thuyết trình (Speaker Notes)
> Tóm lại, dự án Cinema Reservation System đã hoàn thiện từ khâu phân tích nghiệp vụ, mô hình hóa dữ liệu, hiện thực hóa kiến trúc tách biệt 3 tầng cho đến kiểm chứng tự động đa lớp. Trong tương lai, nền tảng này hoàn toàn có thể mở rộng thêm cổng thanh toán thật kèm luồng hoàn tiền, cơ chế thu hồi token bằng Redis, hay quản lý nhiều chi nhánh rạp.
>
> Phần trình bày của nhóm đến đây là kết thúc. Xin cảm ơn thầy/cô và các bạn đã lắng nghe, rất mong nhận được câu hỏi và góp ý ạ.

---

## SLIDE 16 (Phụ lục / Q&A) — Bộ Câu Hỏi Phản Biện Dự Kiến (5–10 Phút)

1. **Tại sao lại kiểm tra hết hạn 10 phút theo kiểu *request-time expiry* (`expire_overdue_bookings()`) mà không dùng Cron job hay background worker?**
   - *Trả lời:* Để không phụ thuộc thêm dịch vụ/tiến trình nền ngoài PostgreSQL và tránh độ trễ đồng bộ giữa lịch chạy cron với thời điểm khách bấm xem ghế hoặc thanh toán. Mọi thao tác đọc trạng thái ghế, đặt vé, trả tiền, hủy vé và xem lịch sử đều gọi `expire_overdue_bookings()` (dùng `FOR UPDATE SKIP LOCKED`) hoặc kiểm tra `clock_timestamp()` ngay trong cùng transaction, nên độ chính xác đạt tới từng micro-giây mà vẫn hoàn toàn lũy đẳng (idempotent).
2. **Tại sao ở bảng `booking_seats` lại lưu thêm cột `showtime_id` dù `bookings` đã có `showtime_id`? Như vậy có vi phạm 3NF không?**
   - *Trả lời:* Về lý thuyết, do phụ thuộc hàm `booking_id → showtime_id` mà `booking_id` không phải siêu khóa nên bảng vật lý không đạt BCNF, nhưng `showtime_id` là một phần của khóa ứng viên `(showtime_id, seat_id)` nên **không vi phạm 3NF**. Mục đích của *controlled redundancy* này (migration `0003`) là để PostgreSQL dựng được `UNIQUE(showtime_id, seat_id)` tức thời, ngăn chặn hai transaction đồng thời ở mức `READ COMMITTED` đọc snapshot cũ rồi cùng chèn một ghế cho cùng suất chiếu; sự khớp nhau giữa `booking_seats.showtime_id` và `bookings.showtime_id` được khóa cứng bằng khóa ngoại kép `(booking_id, showtime_id)`.
3. **Nếu khách hàng thanh toán đúng vào giây hết hạn 10 phút (`clock_timestamp() >= expires_at`) thì chuyện gì xảy ra?**
   - *Trả lời:* Điều kiện biên `D3` quy định chỉ hợp lệ khi `current_time < expires_at`. Khi gọi `pay_booking()`, PostgreSQL khóa dòng booking bằng `FOR UPDATE`; nếu đã chạm hoặc quá `expires_at`, hàm sẽ từ chối thanh toán, tự động chuyển `status = 'EXPIRED'`, giữ `payment_status = 'UNPAID'`, kích hoạt trigger xóa `booking_seats`, và trả `'EXPIRED'` để Flask `COMMIT` (lưu lại trạng thái hết hạn) rồi mới báo cho người dùng.
4. **Nếu một bộ phim thay đổi `duration_minutes` (thời lượng) thì các suất chiếu đã lên lịch có bị đổi `ends_at` không?**
   - *Trả lời:* Không. Khi tạo suất chiếu mà bỏ trống `ends_at`, trigger `trg_showtimes_default_end_time` sẽ tính và **lưu cứng** `ends_at` vào bảng `showtimes`. Về sau sửa thời lượng phim chỉ áp dụng cho suất chiếu mới tạo, không làm xê dịch các suất chiếu đã công bố và không vi phạm quy tắc `D2`.
5. **Làm thế nào chứng minh Frontend và Database được tách biệt hoàn toàn?**
   - *Trả lời:* Frontend chỉ là static bundle phục vụ qua `frontend/server.py` (không chứa thư viện `psycopg2`, không có thông tin DB trong môi trường container `frontend`), chỉ nhận `API_BASE_URL` để gọi HTTP JSON tới Flask (`:5000`). Trong Flask khởi tạo `Flask(..., static_folder=None, template_folder=None)` nên API chỉ trả JSON. Mọi kết nối tới PostgreSQL chỉ xuất phát từ container `api` bằng role hạn chế `cinema_api` trên mạng Docker nội bộ.
6. **Tại sao lại cần migration `0004_finite_money.sql` trong khi đã có `CHECK (ticket_price >= 0)`?**
   - *Trả lời:* Đây là một đặc thù của kiểu `numeric` trong PostgreSQL: PostgreSQL quy ước `'NaN'` lớn hơn mọi giá trị số hữu hạn, nên `'NaN'::numeric >= 0` cho kết quả `TRUE`! Do đó nhóm thêm 3 ràng buộc `NOT IN ('NaN', 'Infinity', '-Infinity')` để khóa chặt hoàn toàn cả ở tầng DB bên cạnh lớp validation Python.

---

## Phụ Lục Thực Hành: Checklist Chuẩn Bị Môi Trường Trước Giờ Thuyết Trình (`important.md`)

Thực hiện trước khi lên thuyết trình ít nhất 15–20 phút (theo `README.md` & `database/demo/README.md`):

### 1. Khởi động Stack Demo Web UI
```powershell
# Tại thư mục gốc d:\dev\project\Cinema
docker compose up --build -d --wait
docker compose ps

# Nếu volume DB mới tạo và đang trống, nạp demo data 1 lần duy nhất:
docker compose exec -T db psql -X -v ON_ERROR_STOP=1 -U cinema_owner -d cinema -f /opt/cinema/demo.sql

# Kiểm tra nhanh health trước khi mở trình duyệt:
# - http://localhost:5000/health/db  -> {"status": "ok", "database": "ok"}
# - http://localhost:8080            -> Giao diện Cinema Reservation
```
- **Mở sẵn 2 tab hoặc 2 profile trình duyệt** (1 tab đăng nhập sẵn hoặc chuẩn bị sẵn `customer1`/`customer1234`, 1 tab ẩn danh hoặc chuẩn bị sẵn `admin`/`admin1234`).
- **Xác nhận có suất chiếu tương lai** trong `http://localhost:8080/screenings.html` (nếu seed chạy từ ngày trước đó và cần thêm suất mới cho demo, tạo sẵn 1 suất tương lai trong *Screenings (Admin)*).

### 2. Chuẩn bị DB cô lập cho SQL Demo (`cinema_test_demo`)
Không chạy `database/demo/*.sql` lên database đang phục vụ Web UI (`cinema`): các script có `guard.sql` chỉ chạy trên DB tên `cinema_test_*` đã có ràng buộc `0004`.

> **Đã chạy thử ngày 26/11/2026** trên Docker Compose (máy Windows của nhóm): các bước dựng DB và cả 3 script `main.sql`, `exceptions.sql`, `permissions_grants.sql` đều kết thúc exit 0 và `ROLLBACK`. Vẫn nên chạy lại trên đúng máy trình chiếu trước giờ G.

`db` trong Compose không mở cổng ra máy chủ, nên dùng `psql` bên trong container (không cần cài `psql` trên máy):

```powershell
# Từ thư mục gốc dự án: chép script demo vào container, rồi mở shell trong container
docker compose cp database/demo db:/tmp/demo
docker compose exec db sh
```
```sh
# Trong shell của container `db` (một lần):
psql -X -v ON_ERROR_STOP=1 -U cinema_owner -d postgres -c "CREATE DATABASE cinema_test_demo"
for f in /docker-entrypoint-initdb.d/10-schema.sql \
         /docker-entrypoint-initdb.d/40-booking-integrity.sql \
         /docker-entrypoint-initdb.d/50-finite-money.sql \
         /opt/cinema/demo.sql; do
  psql -X -v ON_ERROR_STOP=1 -U cinema_owner -d cinema_test_demo -f "$f" || break
done
# Role cinema_api đã tồn tại ở mức cluster; chỉ cấp lại GRANT cho DB mới (bỏ CREATE ROLE và \getenv):
grep -vE 'CREATE ROLE|getenv' /docker-entrypoint-initdb.d/20-runtime-role.sql \
  | psql -X -v ON_ERROR_STOP=1 -U cinema_owner -d cinema_test_demo
psql -X -v ON_ERROR_STOP=1 -U cinema_owner -d cinema_test_demo -f /docker-entrypoint-initdb.d/30-movie-delete-permissions.sql

# Mở sẵn terminal này; tới Slide 13 chỉ việc chạy lần lượt:
cd /tmp/demo
psql -X -v ON_ERROR_STOP=1 -U cinema_owner -d cinema_test_demo -f main.sql
psql -X -v ON_ERROR_STOP=1 -U cinema_owner -d cinema_test_demo -f exceptions.sql
psql -X -v ON_ERROR_STOP=1 -U cinema_owner -d cinema_test_demo -f permissions_grants.sql
```
- Dự phòng: `permissions.sql`; kịch bản 2 terminal `concurrency_prepare.sql`, `concurrency_a.sql`, `concurrency_b.sql` (xem `database/demo/README.md`).
- Cả 4 script `main.sql`, `exceptions.sql`, `permissions.sql`, `permissions_grants.sql` đều kết thúc bằng `ROLLBACK;` nên chạy lại nhiều lần được. Riêng `concurrency_a.sql` sẽ `COMMIT`: muốn trở về trạng thái đầu, chạy `DROP DATABASE cinema_test_demo` rồi dựng lại bằng các lệnh ở trên.
- Nếu đã có sẵn một PostgreSQL test riêng (cổng riêng), có thể dùng `psql -d cinema_test_demo -f database/demo/<file>.sql` như trong `database/demo/README.md`.

### 3. Thông tin còn thiếu (không có trong dự án)
- [x] Tên Thành viên A và B; ai trình bày, ai demo (mục 0).
- [x] Công cụ làm việc nhóm: chỉ Git/GitHub (Slide 3).
- [ ] Phương án dự phòng khi Docker/DB lỗi lúc demo (ảnh chụp màn hình hoặc video quay sẵn).
- [x] Số pytest sau commit `80092c6`: 1.409 đạt, skip 1 (`verify` ngày 26/11/2026), đã điền Slide 11 và 15.
- [ ] Ngày giờ thuyết trình và máy trình chiếu thật, để chạy thử toàn bộ checklist. (Bản theo dõi tiến độ cũ, đã xóa ở commit `a9ed9f1`, ghi "01/12 hoặc 03/12/2026"; chưa có xác nhận mới.)
