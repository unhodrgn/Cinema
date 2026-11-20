# **Master Task Breakdown — Cinema Reservation System**

**Thời gian:** 17/11–29/11/2026\
**Nhân sự:** A (Database Lead) và B (Application Lead)\
**Deadline cuối:** 29/11/2026, 23:59 KST.

Tao sẽ cụ thể hóa kế hoạch thành các công việc có thể giao trực tiếp cho từng người. Mỗi task sẽ có 5 yếu tố:

1. ID để theo dõi.
2. Người chịu trách nhiệm.
3. Công việc cần thực hiện.
4. Sản phẩm phải bàn giao.
5. Tiêu chí xác nhận hoàn thành.

## **1. Phân tích cấu trúc công việc**

Trước hết, cần hiểu dự án này có hai luồng công việc lớn, cùng hội tụ vào một sản phẩm cuối.

**Cinema Reservation System**

Phạm vi và yêu cầu đã thống nhất

A — Database Lead

**Database Development**

Conceptual Model → Logical Model → Physical Model → PostgreSQL

B — Application Lead

**Business & Application**

Business Documents → Flask → UI → Application Logic

**Integration & Testing**

Kết nối ứng dụng với database, kiểm thử nghiệp vụ

**Final Submission**

Source Code + Database (PostgreSQL schema/seed SQL) + Documents + PPT

### **Nguyên tắc phân công**

**A chịu trách nhiệm về tính đúng đắn của dữ liệu.**

A phải đảm bảo rằng:

- ERD phản ánh chính xác nghiệp vụ.
- Các bảng được chuẩn hóa.
- PK, FK và các ràng buộc hoạt động.
- Dữ liệu mẫu đầy đủ.
- Database có thể chạy độc lập và được ứng dụng sử dụng.

**B chịu trách nhiệm về tính đúng đắn của nghiệp vụ và ứng dụng.**

B phải đảm bảo rằng:

- Tất cả chức năng được mô tả trong tài liệu.
- Flowchart khớp với cách ứng dụng hoạt động.
- Giao diện có thể thao tác thực tế.
- Customer và Admin được phân quyền.
- Ứng dụng thao tác với database thật.

Đây là phân chia quyền sở hữu, không có nghĩa A không hỗ trợ kiểm thử ứng dụng hoặc B không được tham gia review database.

## **2. Task Assignment chi tiết**

### **PHASE 1 — Database Design & Business Analysis**

17/11 – 20/11

Mục tiêu: Hoàn thành thiết kế trước khi triển khai các chức năng phụ thuộc vào nó.

#### **Thành viên A — Database**

| ID  | Task                   | Công việc cụ thể                                  | Deliverable            | Hạn   |
| --- | ---------------------- | ------------------------------------------------- | ---------------------- | ----- |
| A01 | Conceptual Data Model  | Xác định entity, attribute, PK và relationship    | ERD                    | 17/11 |
| A02 | Logical Data Model     | Xác định đầy đủ column, type, PK, FK, cardinality | Relation Schema        | 18/11 |
| A03 | Database Normalization | Phân tích 1NF, 2NF, 3NF trên cấu trúc bảng        | Normalization Document | 19/11 |
| A04 | Terminology Design     | Thống nhất tên bảng, cột và thuật ngữ             | Glossary bản đầu       | 19/11 |
| A05 | Domain Definition      | Xác định data type, miền giá trị và constraint    | Domain Definition      | 20/11 |
| A06 | Table Description      | Mô tả chi tiết từng bảng và từng cột              | Table Description      | 20/11 |

**Chi tiết đầu ra cần có:**

A01 phải thể hiện đủ 7 entity dự kiến: USERS, MOVIES, ROOMS, SEATS, SCREENINGS, BOOKINGS và BOOKING_SEATS.

A02 phải có đầy đủ:

- Tên relation.
- Primary Key.
- Foreign Key.
- Data type.
- Relationship.
- Cardinality.

A03 phải thể hiện quá trình chuẩn hóa bằng dữ liệu ví dụ hoặc bảng trước/sau, không chỉ ghi định nghĩa 1NF, 2NF, 3NF.

#### **Thành viên B — Business Analysis**

| ID  | Task                      | Công việc cụ thể                                                | Deliverable | Hạn   |
| --- | ------------------------- | --------------------------------------------------------------- | ----------- | ----- |
| B01 | Project Overview          | Giới thiệu mục tiêu, phạm vi, người dùng, môi trường phát triển | 프로젝트 개요서    | 17/11 |
| B02 | Business Function Diagram | Phân rã chức năng cấp 1, cấp 2                                  | 업무 기능도      | 18/11 |
| B03 | Unit Business Description | Đặc tả từng nghiệp vụ, input, process, output, exception        | 단위 업무 기술서   | 19/11 |
| B04 | Business Flowchart        | Vẽ quy trình đặt vé, hủy vé và quản lý suất chiếu               | 업무 흐름도      | 20/11 |
| B05 | Business Document List    | Liệt kê các biểu mẫu và thông tin được sử dụng                  | 업무 문서 리스트   | 20/11 |

**Chi tiết đầu ra cần có:**

B03 nên đặc tả khoảng 10 nghiệp vụ:

1. 회원가입.
2. 로그인.
3. 영화 조회.
4. 상영 일정 조회.
5. 좌석 현황 조회.
6. 좌석 선택.
7. 영화 예매 및 결제.
8. 예매 내역 조회.
9. 예매 취소.
10. 관리자 영화 및 상영 일정 관리.

B04 cần ít nhất 3 flowchart riêng, có nhánh xử lý lỗi.

B05 phải thể hiện ID, tên tài liệu, mục đích và người sử dụng.

#### **Công việc chung**

| ID  | Công việc                     | Kết quả                                              | Hạn   |
| --- | ----------------------------- | ---------------------------------------------------- | ----- |
| S01 | Review ERD và nghiệp vụ       | Hai người duyệt thiết kế chung                       | 19/11 |
| S02 | Chốt Database Schema Contract | Danh sách bảng và column được cố định để B lập trình | 20/11 |

Điểm kiểm soát quan trọng

Ngày 20/11, hai người phải thống nhất phiên bản schema cuối cùng. Sau mốc này không tự ý đổi tên bảng, cột hoặc kiểu dữ liệu vì sẽ làm ảnh hưởng code của người còn lại.

### **PHASE 2 — Physical Database Development**

21/11 – 23/11

Mục tiêu: Có một PostgreSQL database hoàn chỉnh, đủ dữ liệu và đủ ràng buộc để ứng dụng kết nối.

#### **Thành viên A — Database Implementation**

| ID  | Task                      | Công việc cụ thể                                | Deliverable       | Hạn   |
| --- | ------------------------- | ----------------------------------------------- | ----------------- | ----- |
| A07 | DDL Implementation        | Viết CREATE TABLE cho 7 bảng                    | schema.sql        | 21/11 |
| A08 | Constraint Implementation | PK, FK, NOT NULL, UNIQUE, CHECK, DEFAULT        | Constraints       | 21/11 |
| A09 | Index & Trigger           | Kiểm tra lịch trùng, ghế trùng, ghế sai phòng   | Index/Trigger SQL | 22/11 |
| A10 | Seed Data Generation      | Tạo phim, phòng, ghế, tài khoản, suất chiếu mẫu | seed.sql          | 22/11 |
| A11 | Database Validation       | Kiểm tra số lượng và tính toàn vẹn của dữ liệu  | DB Test Report    | 23/11 |

Các điều kiện A phải kiểm tra:

- Có đúng 5 phòng.
- Có đúng 250 ghế.
- Mỗi phòng có đủ 50 ghế.
- Có đúng 5 phim mẫu.
- Có đủ 140 suất chiếu.
- Không có suất chiếu chồng thời gian trong cùng phòng.
- Không có ghế trùng trong cùng một suất chiếu.
- Foreign Key hoạt động.

**Một vấn đề thiết kế phải được A và B duyệt trước khi viết DDL:**

Bảng BOOKING_SEATS phải đảm bảo một ghế không được đặt hai lần trong cùng một suất chiếu. Chỉ đặt `UNIQUE(booking_id, seat_id)` là chưa đủ, vì hai booking khác nhau vẫn có thể đặt cùng một ghế.

Theo hướng thiết kế trong tài liệu dự án, nhóm phải đảm bảo tính duy nhất theo `(screening_id, seat_id)`; khi hủy thì xóa các dòng ghế tương ứng nhưng giữ lịch sử BOOKING với trạng thái CANCELLED.&#x20;

영화관에 예매 및 좌석 관라 시스템.md



A cần chọn cách thực hiện phù hợp với Logical Model, ví dụ dùng trigger kiểm tra qua quan hệ BOOKING hoặc một thiết kế ràng buộc tương đương đã được kiểm chứng. Không được vô tình làm sai chuẩn hóa chỉ để có thêm một UNIQUE constraint.

Ngoài ra:

- Phải kiểm tra ghế thuộc đúng phòng của suất chiếu.
- Phải ngăn lịch chiếu chồng lấn khi INSERT và UPDATE.
- Không lưu trạng thái AVAILABLE/BOOKED cố định cho SEATS. Trạng thái ghế phải được tính theo SCREENING và booking còn hiệu lực.

#### **Thành viên B — Application Foundation**

| ID  | Task                | Công việc cụ thể                                | Deliverable   | Hạn   |
| --- | ------------------- | ----------------------------------------------- | ------------- | ----- |
| B06 | Flask Project Setup | Tạo cấu trúc ứng dụng và cấu hình môi trường    | Flask Project | 21/11 |
| B07 | Database Connection | Xây dựng lớp kết nối PostgreSQL (driver chốt cùng A: psycopg2 hoặc SQLAlchemy) và truy vấn dữ liệu | database.py   | 22/11 |
| B08 | Authentication      | Register, Login, Logout                         | Auth Module   | 23/11 |

B có thể bắt đầu B06 và chuẩn bị giao diện từ ngày 20/11, sử dụng schema contract đã chốt. Phần kết nối thực tế và kiểm thử phải dùng database của A.

**Cấu trúc project ban đầu:**

```
CinemaReservation/
│
├── app/
│   ├── app.py
│   ├── database.py
│   ├── auth.py
│   ├── booking.py
│   ├── admin.py
│   │
│   ├── templates/
│   └── static/
│
├── database/
│   ├── schema.sql
│   └── seed.sql
│
├── docs/
├── presentation/
└── README.md
```

Chưa cần thiết kế giao diện đẹp. Giai đoạn này chỉ cần Flask khởi chạy và kết nối thành công PostgreSQL.

### **PHASE 3 — Application Development**

23/11 – 27/11

Mục tiêu: Hoàn thiện tất cả chức năng chính của hệ thống. Ưu tiên chạy đúng nghiệp vụ trước khi nâng cấp giao diện.

Giai đoạn này chủ yếu do B phát triển. A tiếp tục kiểm tra database và hỗ trợ xử lý các vấn đề liên quan đến dữ liệu.

#### **Thành viên B — Application Development**

| ID  | Task                       | Công việc cụ thể                                  | Deliverable           | Hạn   |
| --- | -------------------------- | ------------------------------------------------- | --------------------- | ----- |
| B09 | Movie Management View      | Hiển thị danh sách và chi tiết phim               | Movie Pages           | 23/11 |
| B10 | Screening View             | Hiển thị ngày, giờ, phòng và phim                 | Screening Pages       | 23/11 |
| B11 | Seat Selection             | Hiển thị 50 ghế, phân biệt ghế trống và đã đặt    | Seat Selection UI     | 24/11 |
| B12 | Booking Logic              | Chọn nhiều ghế, tính tổng tiền, xác nhận booking  | Booking Module        | 25/11 |
| B13 | Simulated Payment          | Xác nhận thanh toán và chuyển sang PAID           | Payment Module        | 25/11 |
| B14 | Booking History            | Khách xem danh sách booking của mình              | My Bookings           | 26/11 |
| B15 | Booking Cancellation       | Hủy booking hợp lệ, mở lại ghế                    | Cancellation Module   | 26/11 |
| B16 | Admin Movie Management     | Admin thêm và sửa phim                            | Admin Movie Pages     | 27/11 |
| B17 | Admin Screening Management | Admin thêm, sửa suất chiếu và kiểm tra trùng lịch | Admin Screening Pages | 27/11 |
| B18 | Admin Booking View         | Admin xem danh sách booking toàn hệ thống         | Admin Booking Pages   | 27/11 |

#### **Thành viên A — Database Support**

| ID  | Task                      | Công việc cụ thể                              | Deliverable          | Hạn   |
| --- | ------------------------- | --------------------------------------------- | -------------------- | ----- |
| A12 | Booking Constraint Review | Kiểm tra việc đặt trùng ghế bằng SQL          | Constraint Test      | 24/11 |
| A13 | Cancellation Data Review  | Kiểm tra xóa chi tiết ghế và giữ lịch sử      | Cancellation DB Test | 26/11 |
| A14 | Admin Data Review         | Kiểm tra thao tác thêm/sửa phim và suất chiếu | Admin DB Test        | 27/11 |

**Một số quy tắc B phải thực hiện trong ứng dụng:**

| Chức năng    | Điều kiện xử lý                                 |
| ------------ | ----------------------------------------------- |
| Booking      | Chỉ khách đã đăng nhập mới được xác nhận        |
| Booking      | Không đặt suất đã bắt đầu                       |
| Booking      | Không chọn ghế thuộc phòng khác                 |
| Booking      | Kiểm tra lại tình trạng ghế ngay trước khi lưu  |
| Payment      | Thanh toán mô phỏng chuyển trạng thái sang PAID |
| Cancellation | Chỉ được hủy booking của chính mình             |
| Cancellation | Phải hủy trước giờ chiếu                        |
| Cancellation | Cập nhật CANCELLED và mở lại ghế                |
| Admin        | Chỉ ADMIN được thêm/sửa phim và suất chiếu      |

**Lưu ý kỹ thuật cho B:** thao tác xác nhận booking cần chạy trong một database transaction. Không được chỉ kiểm tra ghế ở giao diện rồi mới lưu mà không kiểm tra lại trong database. Thực hiện trong một transaction PostgreSQL (INSERT `bookings`, INSERT `booking_seats`, rồi COMMIT; rollback khi có lỗi). Trigger `trg_validate_booking_seat` của A khóa dòng suất chiếu và chặn đặt trùng ghế; B phải bắt exception của trigger và hiển thị thông báo ghế đã được đặt.

### **PHASE 4 — Integration & Testing**

28/11

Mục tiêu: Xác nhận ứng dụng và database hoạt động như một hệ thống thống nhất.

Đây là giai đoạn bắt buộc cả hai cùng tham gia.

| ID  | Người phụ trách | Task                    | Công việc                               | Deliverable             |
| --- | --------------- | ----------------------- | --------------------------------------- | ----------------------- |
| S03 | Both            | Full Integration        | Kết nối toàn bộ chức năng với PostgreSQL DB | Integrated Application  |
| S04 | A               | Database Integrity Test | Kiểm tra PK, FK, UNIQUE, CHECK, Trigger | DB Test Results         |
| S05 | B               | Functional Test         | Kiểm thử tất cả chức năng trên UI       | Functional Test Results |
| S06 | Both            | Bug Fix                 | Sửa các lỗi phát hiện trong kiểm thử    | Stable Version          |
| S07 | Both            | Version Freeze          | Chốt source code và database            | Release Candidate       |

#### **Test checklist bắt buộc**

| Test ID | Tình huống                          | Người kiểm tra |
| ------- | ----------------------------------- | -------------- |
| TC01    | Đăng ký tài khoản thành công        | B              |
| TC02    | Username bị trùng                   | B              |
| TC03    | Customer không truy cập Admin       | B              |
| TC04    | Hiển thị đúng trạng thái ghế        | A + B          |
| TC05    | Đặt một ghế thành công              | A + B          |
| TC06    | Đặt nhiều ghế thành công            | A + B          |
| TC07    | Hai người đặt cùng một ghế          | A              |
| TC08    | Đặt ghế sai phòng                   | A              |
| TC09    | Đặt vé cho suất đã bắt đầu          | A + B          |
| TC10    | Hủy booking hợp lệ                  | A + B          |
| TC11    | Ghế được mở lại sau khi hủy         | A + B          |
| TC12    | Customer hủy booking của người khác | B              |
| TC13    | Admin thêm phim                     | B              |
| TC14    | Admin thêm suất bị trùng lịch       | A + B          |
| TC15    | Dữ liệu booking được lưu chính xác  | A              |

Không được đánh dấu hoàn thành chỉ vì giao diện hiển thị đúng. Phải xác nhận dữ liệu trong PostgreSQL thực sự thay đổi đúng.

### **PHASE 5 — Documentation & Final Submission**

27/11 – 29/11

Giai đoạn này có một số công việc chạy song song với Phase 4.

#### **Thành viên A — Database Documentation**

\| ID | Task | Công việc | Deliverable | Hạn |\
\|---|---|---|---|---|\
\| A15 | Final ERD | Cập nhật ERD theo database cuối cùng | ERD Final |\
\| A16 | Final Logical Model | Đồng bộ Relation Schema | Logical Model Final |\
\| A17 | Final Physical Model | Đồng bộ DDL, constraint, index, trigger | Physical Model Final |\
\| A18 | Glossary Final | Hoàn thiện 용어 사전 | Glossary |\
\| A19 | Domain Definition Final | Đồng bộ domain và constraint | Domain Definition |\
\| A20 | Table Description Final | Đồng bộ toàn bộ column và type | Table Description |\
\| A21 | DB Packaging | Kiểm tra và đóng gói schema.sql, seed.sql, hướng dẫn khởi tạo PostgreSQL | Final DB Package |

#### **Thành viên B — Business Documentation & Presentation**

\| ID | Task | Công việc | Deliverable | Hạn |\
\|---|---|---|---|---|\
\| B19 | Business Documents Final | Hoàn thiện 5 tài liệu nghiệp vụ | Business Documents |\
\| B20 | Application README | Hướng dẫn cài đặt và chạy | README.md |\
\| B21 | PPT Structure | Thiết kế cấu trúc bài thuyết trình | PPT Draft |\
\| B22 | PPT Final | Hoàn thiện slide, hình ảnh, kết quả test | presentation.pptx |\
\| B23 | Demo Scenario | Chuẩn bị trình tự thao tác demo | Demo Script |\
\| B24 | Final Packaging | Tổ chức các file và kiểm tra bộ nộp | Final Package |

#### **Công việc chung**

| ID  | Công việc                                      | Hạn   |
| --- | ---------------------------------------------- | ----- |
| S08 | Review toàn bộ 11 đầu mục tài liệu và sản phẩm | 28/11 |
| S09 | Kiểm tra project trên môi trường sạch          | 28/11 |
| S10 | Backup, kiểm tra file và nộp bài               | 29/11 |

Họp biên bản 회의록 không đưa vào danh sách deliverable chung này vì đề bài đã yêu cầu mỗi thành viên nộp riêng hằng tuần.

## **3. Lịch triển khai theo ngày**

Đây là lịch phối hợp để hai người không phải chờ nhau.

| Ngày  | Thành viên A                         | Thành viên B                               | Kết quả cuối ngày    |
| ----- | ------------------------------------ | ------------------------------------------ | -------------------- |
| 17/11 | A01 – ERD                            | B01 – Overview, B02 bắt đầu                | ERD v1               |
| 18/11 | A02 – Logical Model                  | B02 – Function Diagram                     | Business + ERD       |
| 19/11 | A03, A04 – Normalization, Glossary   | B03 – Unit Description                     | Thiết kế dữ liệu     |
| 20/11 | A05, A06 – Domain, Table Description | B04, B05 – Flowchart, Document List        | Hoàn thành thiết kế  |
| 21/11 | A07, A08 – DDL, Constraints          | B06, B07 – Flask, Database Connection      | DB + App Skeleton    |
| 22/11 | A09, A10 – Trigger, Seed             | B08 – Authentication                       | Database có dữ liệu  |
| 23/11 | A11 – DB Validation                  | B09, B10 – Movie, Screening                | Tra cứu phim và suất |
| 24/11 | A12 – Booking Constraint Test        | B11 – Seat Selection                       | Chọn ghế             |
| 25/11 | Hỗ trợ kiểm tra DB                   | B12, B13 – Booking, Payment                | Đặt vé               |
| 26/11 | A13 – Cancellation DB Test           | B14, B15 – History, Cancellation           | Hủy vé               |
| 27/11 | A14, A15–A20 – DB Review, Documents  | B16–B19 – Admin, Business Docs             | Hoàn thiện chức năng |
| 28/11 | S04, S08 – DB Test, Review           | S05, B20–B23 – App Test, README, PPT, Demo | Release Candidate    |
| 29/11 | Xác nhận DB cuối                     | B24 – Đóng gói                             | Final Submission     |

**Quy tắc:** Task có thể thực hiện song song, nhưng task phụ thuộc phải có đầu ra từ task trước. Ví dụ B không thể kiểm thử booking thực tế trước khi A bàn giao database.

## **4. Các điểm bàn giao giữa A và B**

Đây là phần rất quan trọng khi chỉ có hai người. Hai người phải thống nhất chính xác những thứ cần trao đổi.

**Handoff 1 — Database Schema**

A → B

20/11

A cung cấp:

- ERD đã duyệt.
- Relation Schema.
- Tên bảng, column và datatype.
- PK, FK, constraint.
- Các trạng thái và giá trị hợp lệ.

B xác nhận code ứng dụng sẽ sử dụng đúng schema này.

**Handoff 2 — Database**

A → B

22/11

A cung cấp:

- `schema.sql`
- `seed.sql`
- `verify.sql`
- Hướng dẫn khởi tạo DB.

B kết nối và kiểm tra dữ liệu thực tế.

**Handoff 3 — Application Testing**

B → A

26–27/11

B cung cấp:

- Danh sách chức năng đã hoàn thành.
- Các thao tác thực tế trên ứng dụng.
- Những lỗi liên quan tới dữ liệu.

A kiểm tra database sau từng thao tác.

**Handoff 4 — Final Submission**

Both

28–29/11

A chịu trách nhiệm xác nhận database và tài liệu database.

B chịu trách nhiệm đóng gói ứng dụng và PowerPoint.

Cả hai duyệt sản phẩm cuối cùng.

## **5. Quy tắc kỹ thuật để tránh xung đột khi làm chung**

Tao đề xuất dùng chung Git repository với cấu trúc thư mục đã thống nhất.

```
CinemaReservation/
│
├── app/                    # B quản lý
│   ├── app.py
│   ├── auth.py
│   ├── booking.py
│   ├── admin.py
│   ├── database.py
│   ├── templates/
│   └── static/
│
├── database/               # A quản lý
│   ├── schema.sql
│   ├── seed.sql
│   └── tests/
│
├── docs/
│   ├── business/            # B quản lý
│   └── database/            # A quản lý
│
├── presentation/            # B quản lý
│
├── requirements.txt
└── README.md
```

Quy tắc Git:

- A không sửa trực tiếp code nghiệp vụ của B nếu chưa thống nhất.
- B không thay đổi cấu trúc bảng trong schema.sql nếu chưa trao đổi với A.
- Mỗi chức năng hoàn thành phải được kiểm tra trước khi merge.
- Giữ lại một phiên bản database có thể tạo lại từ `schema.sql` và `seed.sql`.
- Không đưa mật khẩu thật hoặc secret vào Git.

## **6. Những rủi ro cần kiểm soát**

| Rủi ro                                  | Người chịu trách nhiệm | Cách xử lý                       |
| --------------------------------------- | ---------------------- | -------------------------------- |
| ERD không khớp database                 | A                      | Review trước khi viết DDL        |
| Schema thay đổi liên tục                | A + B                  | Freeze schema ngày 20/11         |
| Giao diện xong nhưng DB không hoạt động | B                      | Tích hợp sớm từ 22/11            |
| Đặt trùng ghế                           | A + B                  | Constraint/trigger + transaction |
| Hủy vé nhưng ghế không mở lại           | A + B                  | Kiểm tra xóa booking details     |
| Quá nhiều chức năng phụ                 | B                      | Chỉ giữ MVP theo phạm vi đã chốt |
| Tài liệu không khớp ứng dụng            | Both                   | Review cuối ngày 28/11           |

Không triển khai thêm các chức năng ngoài phạm vi như thanh toán thật, gửi email, mã QR, tích điểm hoặc ứng dụng mobile. Thời gian hiện tại không phù hợp để mở rộng.

## **7. Bảng theo dõi tiến độ tổng thể**

Đây là các mốc mà cả nhóm cần đạt được:

## **Project Milestones**

1. **20/11 — Design Freeze**

   Critical

   ERD, Logical Model và tài liệu nghiệp vụ hoàn thành. Schema được cả hai duyệt.
2. **23/11 — Database Ready**

   PostgreSQL DB có đầy đủ dữ liệu, constraint và có thể kết nối.
3. **27/11 — Feature Complete**

   Toàn bộ chức năng khách hàng và admin hoạt động.
4. **28/11 — Release Candidate**

   Critical

   Hoàn thành kiểm thử, sửa lỗi và đóng băng phiên bản.
5. **29/11 — Final Submission**

   Deadline

   Nộp toàn bộ tài liệu, source code, DB và PPT trước 23:59.

## **8. Việc cần bắt đầu ngay hôm nay**

Không cần tiếp tục bàn về phương pháp quản lý dự án. Bắt đầu thực hiện các task đầu tiên.

**SPRINT 1 — 17/11**

**Thành viên A**

Database

A01 — Vẽ Conceptual ERD

Xác định 7 entity và thuộc tính

Xác định PK, relationship và cardinality

Kiểm tra các quy tắc đặt vé và hủy vé

**Thành viên B**

Application

B01 — Hoàn thiện Project Overview

B02 — Vẽ Business Function Diagram

Xác định danh sách nghiệp vụ và tác nhân

**Kết quả cần bàn giao cuối ngày**

A gửi ERD bản đầu tiên.

B gửi Project Overview và Function Diagram.

Hai người review chéo trước khi chuyển sang ngày 18/11.

**Quyết định triển khai:** Từ giờ, A là người chịu trách nhiệm cuối cùng về database; B là người chịu trách nhiệm cuối cùng về ứng dụng và tài liệu nghiệp vụ. Các mốc S01–S10 là trách nhiệm chung.
