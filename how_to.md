# **Kế hoạch thực hiện dự án Cinema Reservation System**

## **1. Chốt cách triển khai dự án**

**Tên dự án**

영화관 예매 및 좌석 관리 시스템

*Hệ thống đặt vé xem phim và quản lý ghế.*

Thành viên

**2 người**

Thời gian phát triển

**14 ngày**

Hạn nộp

**29/11/2026 – 23:59**

Thuyết trình

**01/12 hoặc 03/12**

**Phạm vi đã thống nhất trong file**

- 1 rạp, 5 phòng chiếu, 250 ghế.
- 5 phim mẫu, 140 suất chiếu trong 7 ngày.
- Khách hàng và quản trị viên.
- Đặt vé, thanh toán mô phỏng, hủy vé.
- Quản lý phim, suất chiếu và xem danh sách đặt vé.

  Nguồn: tài liệu mô tả dự án của nhóm.&#x20;

  영화관에 예매 및 좌석 관라 시스템.md



### **Công nghệ đề xuất**

| Thành phần        | Công nghệ             |
| ----------------- | --------------------- |
| Ngôn ngữ          | Python                |
| Backend           | Flask                 |
| Database          | SQLite                |
| Giao diện         | HTML, CSS, Bootstrap  |
| Kết nối database  | Python `sqlite3`      |
| Thiết kế ERD      | Draw\.io              |
| Kiểm tra database | DB Browser for SQLite |
| Báo cáo           | Word hoặc PDF         |
| Thuyết trình      | PowerPoint            |

**Tại sao chọn Flask + SQLite?**

- SQLite tạo trực tiếp file `.db`, phù hợp với yêu cầu nộp database.
- Flask đủ để xây dựng đăng nhập, đặt vé, quản trị và giao diện demo.
- Không cần triển khai server database riêng.
- Python dễ xử lý nghiệp vụ và kết nối database.

Không nên dùng React + Node.js + MySQL cho dự án này. Nhóm chỉ có hai tuần, trong khi trọng tâm môn học là thiết kế và tích hợp cơ sở dữ liệu.

Mục tiêu cuối cùng là có một ứng dụng chạy được, database có dữ liệu mẫu thực tế và bộ tài liệu thiết kế nhất quán với hệ thống.

## **2. Thiết kế kiến trúc database**

Đây là phần quan trọng nhất của dự án. Nhóm nên hoàn thành ERD và cấu trúc bảng trước khi xây dựng giao diện.

### **2.1. Các bảng cần xây dựng**

Tao đề xuất **7 bảng chính**, không cần tạo quá nhiều bảng.

| STT | Bảng            | Chức năng                          |
| --- | --------------- | ---------------------------------- |
| 1   | `USERS`         | Lưu tài khoản khách hàng và admin  |
| 2   | `MOVIES`        | Lưu thông tin phim                 |
| 3   | `ROOMS`         | Lưu thông tin phòng chiếu          |
| 4   | `SEATS`         | Lưu danh sách ghế trong từng phòng |
| 5   | `SCREENINGS`    | Lưu các suất chiếu                 |
| 6   | `BOOKINGS`      | Lưu thông tin đặt vé               |
| 7   | `BOOKING_SEATS` | Lưu các ghế thuộc từng lượt đặt vé |

### **2.2. Quan hệ giữa các bảng**

**ERD ở mức khái niệm**

```
USERS
  1
  │
  N
BOOKINGS ─────── N:1 ─────── SCREENINGS
  │                              │
  1                              N
  │                              │
  N                         MOVIES (N:1)
BOOKING_SEATS                    │
  N                              │
  │                              │
  1                         ROOMS (N:1)
SEATS
  N
  │
  1
ROOMS
```

Sơ đồ trên thể hiện các quan hệ chính; BOOKING_SEATS là bảng trung gian giữa BOOKINGS và SEATS.

Các quan hệ cần thể hiện đầy đủ trên ERD:

| Quan hệ                  | Cardinality |
| ------------------------ | ----------- |
| USERS – BOOKINGS         | 1:N         |
| MOVIES – SCREENINGS      | 1:N         |
| ROOMS – SCREENINGS       | 1:N         |
| ROOMS – SEATS            | 1:N         |
| SCREENINGS – BOOKINGS    | 1:N         |
| BOOKINGS – BOOKING_SEATS | 1:N         |
| SEATS – BOOKING_SEATS    | 1:N         |

`BOOKING_SEATS` giải quyết quan hệ nhiều-nhiều giữa lượt đặt vé và ghế: một booking có nhiều ghế, còn một ghế có thể được đặt ở nhiều suất chiếu khác nhau.

### **2.3. Các thuộc tính quan trọng**

Đây là cấu trúc đề xuất ban đầu để nhóm triển khai:

**USERS**

| Column        | Ý nghĩa            |
| ------------- | ------------------ |
| user_id (PK)  | ID tài khoản       |
| username      | Tên đăng nhập      |
| password_hash | Mật khẩu đã mã hóa |
| full_name     | Họ tên             |
| role          | CUSTOMER / ADMIN   |
| created_at    | Ngày tạo           |

**MOVIES**

| Column        | Ý nghĩa           |
| ------------- | ----------------- |
| movie_id (PK) | ID phim           |
| title         | Tên phim          |
| genre         | Thể loại          |
| duration      | Thời lượng        |
| rating        | Phân loại độ tuổi |
| description   | Mô tả             |
| release_date  | Ngày phát hành    |

**ROOMS**

| Column       | Ý nghĩa   |
| ------------ | --------- |
| room_id (PK) | ID phòng  |
| room_name    | Tên phòng |

**SEATS**

| Column       | Ý nghĩa        |
| ------------ | -------------- |
| seat_id (PK) | ID ghế         |
| room_id (FK) | Phòng chứa ghế |
| row_label    | Hàng A–E       |
| seat_number  | Số ghế 1–10    |

**SCREENINGS**

| Column            | Ý nghĩa         |
| ----------------- | --------------- |
| screening_id (PK) | ID suất chiếu   |
| movie_id (FK)     | Phim được chiếu |
| room_id (FK)      | Phòng chiếu     |
| start_at          | Giờ bắt đầu     |
| end_at            | Giờ kết thúc    |
| ticket_price      | Giá vé          |

**BOOKINGS**

| Column            | Ý nghĩa            |
| ----------------- | ------------------ |
| booking_id (PK)   | ID lượt đặt        |
| user_id (FK)      | Người đặt          |
| screening_id (FK) | Suất chiếu         |
| booked_at         | Thời gian đặt      |
| status            | BOOKED / CANCELLED |
| total_amount      | Tổng tiền          |
| payment_status    | UNPAID / PAID      |

**BOOKING_SEATS**

| Column               | Ý nghĩa               |
| -------------------- | --------------------- |
| booking_seat_id (PK) | ID chi tiết           |
| booking_id (FK)      | Lượt đặt              |
| seat_id (FK)         | Ghế được chọn         |
| unit_price           | Giá tại thời điểm đặt |

Đây là cấu trúc logic cơ bản. Khi viết SQL, nhóm cần bổ sung các ràng buộc để kiểm tra ghế thuộc đúng phòng của suất chiếu và không bị đặt trùng.

### **2.4. Ba quy tắc database đặc biệt quan trọng**

Có ba vấn đề mà nhóm không được bỏ qua:

**1. Không được đặt trùng ghế**

Ví dụ:

- User A đặt ghế A1 ở suất chiếu 10:00.
- User B không được đặt ghế A1 ở chính suất chiếu 10:00.
- Nhưng User B được đặt A1 ở suất chiếu 13:00.

Tài liệu dự án đề xuất ràng buộc duy nhất theo `(screening_id, seat_id)` ở bảng chi tiết đặt vé. Khi hủy, xóa chi tiết ghế nhưng giữ lại lịch sử booking và chuyển trạng thái sang CANCELLED.&#x20;

영화관에 예매 및 좌석 관라 시스템.md



Lưu ý thiết kế: nếu thêm `screening_id` vào `BOOKING_SEATS` để tạo UNIQUE trực tiếp, đây là dữ liệu lặp lại vì `BOOKINGS` đã xác định suất chiếu. Muốn giữ mô hình chuẩn hóa 3NF, nhóm có thể chỉ lưu `booking_id, seat_id` ở bảng chi tiết và sử dụng trigger kiểm tra trùng qua `BOOKINGS`. Nếu chọn cách lưu lặp `screening_id`, phải có ràng buộc kiểm tra nó khớp với booking tương ứng.

**2. Không được chọn ghế sai phòng**

Ví dụ: suất chiếu thuộc phòng 1 thì khách không thể chọn ghế thuộc phòng 2.

Phải kiểm tra `SCREENINGS.room_id` và `SEATS.room_id` trước khi lưu booking.

**3. Không được xếp lịch chồng nhau**

Ví dụ:

- Phòng 1: phim A từ 10:00 đến 12:30.
- Phòng 1: phim B bắt đầu 12:00.

Phải từ chối suất chiếu thứ hai. Cần kiểm tra cả khi thêm mới và khi sửa lịch chiếu.

Ngoài ra, trạng thái ghế trống/đã đặt phải được tính theo từng suất chiếu từ dữ liệu booking. Không nên lưu một cột `seat_status` cố định trong `SEATS`, bởi cùng một ghế có thể được đặt ở suất này nhưng vẫn trống ở suất khác.

## **3. Phân chia công việc cho 2 thành viên**

Tao khuyên chia theo chuyên môn và đầu ra, không chia mỗi người làm một nửa tài liệu một cách máy móc.

**Thành viên A — Database Lead**

Database

Chịu trách nhiệm thiết kế và triển khai cơ sở dữ liệu.

- Thiết kế Conceptual ERD.
- Thiết kế Logical Data Model.
- Phân tích chuẩn hóa 1NF, 2NF, 3NF.
- Viết DDL, PK, FK, UNIQUE, CHECK, INDEX, TRIGGER.
- Tạo dữ liệu mẫu 5 phim, 5 phòng, 250 ghế, 140 suất chiếu.
- Viết từ điển thuật ngữ, domain definition, table description.
- Kiểm tra tính toàn vẹn dữ liệu.

**Thành viên B — Application Lead**

Application

Chịu trách nhiệm phân tích nghiệp vụ và xây dựng ứng dụng.

- Viết Project Overview.
- Thiết kế Business Function Diagram.
- Viết Unit Business Description.
- Thiết kế Business Flowchart.
- Viết Business Document List.
- Xây dựng Flask application.
- Làm giao diện khách hàng và admin.
- Tích hợp ứng dụng với database do A xây dựng.
- Chuẩn bị PPT và kịch bản demo.

**Cả hai cùng chịu trách nhiệm**

- Thống nhất cấu trúc database trước khi code.
- Review tài liệu chéo.
- Kiểm thử toàn bộ nghiệp vụ.
- Chuẩn bị thuyết trình và trả lời câu hỏi.

**Nguyên tắc phối hợp:** Thành viên A phải bàn giao cấu trúc bảng, tên cột, kiểu dữ liệu và quy tắc nghiệp vụ cho B ngay từ đầu. B không tự ý thay đổi tên bảng hoặc cột khi chưa trao đổi với A.

Hai người nên dùng chung một Git repository để tránh gửi file qua lại và ghi đè phiên bản.

## **4. Cách thực hiện từng tài liệu phải nộp**

Nhóm có 11 đầu mục tài liệu và sản phẩm chính cần hoàn thành. Đừng viết mỗi tài liệu một kiểu. Chúng phải mô tả cùng một hệ thống, cùng tên chức năng và cùng dữ liệu.

### **4.1. 프로젝트 개요서 — Project Overview**

Đây là tài liệu giới thiệu toàn bộ dự án.

Nội dung nên có:

1. 프로젝트명: 영화관 예매 및 좌석 관리 시스템.
2. 프로젝트 목적: Mục đích xây dựng hệ thống.
3. 프로젝트 배경: Vấn đề cần giải quyết.
4. 프로젝트 범위: Một rạp, 5 phòng, 250 ghế, 5 phim.
5. 사용자: Customer và Admin.
6. 주요 기능: Đăng nhập, tra cứu, đặt vé, hủy vé, quản trị.
7. 개발 환경: Python, Flask, SQLite.
8. 기대 효과: Quản lý lịch chiếu và đặt vé chính xác, tránh trùng ghế.

Không cần viết quá dài. Khoảng 2–3 trang là đủ.

### **4.2. 업무 기능도 — Business Function Diagram**

Đây là sơ đồ phân rã các chức năng của hệ thống.

Nhóm có thể triển khai theo cấu trúc sau:

```
영화관 예매 및 좌석 관리 시스템
│
├── 1. 회원 관리
│   ├── 회원가입
│   ├── 로그인
│   └── 로그아웃
│
├── 2. 영화 및 상영 정보 조회
│   ├── 영화 목록 조회
│   ├── 영화 상세 정보 조회
│   ├── 상영 일정 조회
│   └── 좌석 현황 조회
│
├── 3. 예매 관리
│   ├── 좌석 선택
│   ├── 예매 금액 계산
│   ├── 예매 확정
│   ├── 모의 결제
│   ├── 예매 내역 조회
│   └── 예매 취소
│
└── 4. 관리자 관리
    ├── 영화 등록 및 수정
    ├── 상영 일정 등록 및 수정
    └── 전체 예매 내역 조회
```

Có thể sử dụng Draw\.io để vẽ lại thành sơ đồ phân cấp. Đây không phải flowchart, vì mục đích của nó là cho thấy hệ thống có những nhóm chức năng nào.

### **4.3. 단위 업무 기술서 — Unit Business Description**

Tài liệu này mô tả cụ thể từng nghiệp vụ.

Không chỉ viết chức năng có tác dụng gì, mà cần giải thích người dùng thực hiện thế nào, dữ liệu đầu vào và đầu ra là gì.

Sử dụng một mẫu thống nhất:

| Hạng mục | Nội dung                                   |
| -------- | ------------------------------------------ |
| 업무 ID    | BK-01                                      |
| 업무명      | 영화 예매                                      |
| 담당자      | Customer                                   |
| 사전 조건    | Đã đăng nhập                               |
| 입력 데이터   | Screening ID, Seat ID                      |
| 처리 내용    | Kiểm tra ghế, tính tiền, xác nhận đặt      |
| 출력 데이터   | Booking ID, tổng tiền                      |
| 예외 처리    | Ghế đã đặt, suất đã bắt đầu                |
| 관련 테이블   | BOOKINGS, BOOKING_SEATS, SCREENINGS, SEATS |

Tạo ít nhất 8 nghiệp vụ:

| ID    | Nghiệp vụ |
| ----- | --------- |
| AC-01 | 회원가입      |
| AC-02 | 로그인       |
| MV-01 | 영화 조회     |
| SC-01 | 상영 일정 조회  |
| SC-02 | 좌석 현황 조회  |
| BK-01 | 영화 예매     |
| BK-02 | 예매 취소     |
| AD-01 | 영화 관리     |
| AD-02 | 상영 일정 관리  |
| AD-03 | 전체 예매 조회  |

Mỗi nghiệp vụ nên có một bảng mô tả riêng.

### **4.4. 업무 흐름도 — Business Flowchart**

Nên vẽ ba quy trình quan trọng nhất:

- Quy trình đặt vé.
- Quy trình hủy vé.
- Quy trình quản trị thêm suất chiếu.

Ví dụ quy trình đặt vé:

\#chatgpt-mermaid-\_r_61q\_{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;fill:rgb(237, 237, 237);}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#chatgpt-mermaid-\_r_61q\_ .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_61q\_ .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_61q\_ .error-icon{fill:rgb(48, 48, 48);}#chatgpt-mermaid-\_r_61q\_ .error-text{fill:rgb(237, 237, 237);stroke:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_61q\_ .edge-thickness-normal{stroke-width:1px;}#chatgpt-mermaid-\_r_61q\_ .edge-thickness-thick{stroke-width:3.5px;}#chatgpt-mermaid-\_r_61q\_ .edge-pattern-solid{stroke-dasharray:0;}#chatgpt-mermaid-\_r_61q\_ .edge-thickness-invisible{stroke-width:0;fill:none;}#chatgpt-mermaid-\_r_61q\_ .edge-pattern-dashed{stroke-dasharray:3;}#chatgpt-mermaid-\_r_61q\_ .edge-pattern-dotted{stroke-dasharray:2;}#chatgpt-mermaid-\_r_61q\_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_61q\_ .marker.cross{stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_61q\_ svg{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;}#chatgpt-mermaid-\_r_61q\_ p{margin:0;}#chatgpt-mermaid-\_r_61q\_ .label{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_61q\_ .cluster-label text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_61q\_ .cluster-label span{color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_61q\_ .cluster-label span p{background-color:transparent;}#chatgpt-mermaid-\_r_61q\_ .label text,#chatgpt-mermaid-\_r_61q\_ span{fill:rgb(237, 237, 237);color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_61q\_ .node rect,#chatgpt-mermaid-\_r_61q\_ .node circle,#chatgpt-mermaid-\_r_61q\_ .node ellipse,#chatgpt-mermaid-\_r_61q\_ .node polygon,#chatgpt-mermaid-\_r_61q\_ .node path{fill:rgb(65, 49, 17);stroke:rgb(217, 163, 55);stroke-width:1px;}#chatgpt-mermaid-\_r_61q\_ .rough-node .label text,#chatgpt-mermaid-\_r_61q\_ .node .label text,#chatgpt-mermaid-\_r_61q\_ .image-shape .label,#chatgpt-mermaid-\_r_61q\_ .icon-shape .label{text-anchor:middle;}#chatgpt-mermaid-\_r_61q\_ .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#chatgpt-mermaid-\_r_61q\_ .rough-node .label,#chatgpt-mermaid-\_r_61q\_ .node .label,#chatgpt-mermaid-\_r_61q\_ .image-shape .label,#chatgpt-mermaid-\_r_61q\_ .icon-shape .label{text-align:center;}#chatgpt-mermaid-\_r_61q\_ .node.clickable{cursor:pointer;}#chatgpt-mermaid-\_r_61q\_ .root .anchor path{fill:rgb(175, 175, 175)!important;stroke-width:0;stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_61q\_ .arrowheadPath{fill:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_61q\_ .edgePath .path{stroke:rgb(175, 175, 175);stroke-width:1px;}#chatgpt-mermaid-\_r_61q\_ .flowchart-link{stroke:rgb(175, 175, 175);fill:none;}#chatgpt-mermaid-\_r_61q\_ .edgeLabel{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-\_r_61q\_ .edgeLabel p{background-color:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_61q\_ .edgeLabel rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_61q\_ .labelBkg{background-color:rgba(0, 0, 0, 0.5);}#chatgpt-mermaid-\_r_61q\_ .cluster rect{fill:rgb(48, 48, 48);stroke:rgba(255, 255, 255, 0.15);stroke-width:1px;}#chatgpt-mermaid-\_r_61q\_ .cluster text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_61q\_ .cluster span{color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_61q\_ div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:12px;background:rgb(48, 48, 48);border:1px solid rgba(255, 255, 255, 0.15);border-radius:2px;pointer-events:none;z-index:100;}#chatgpt-mermaid-\_r_61q\_ .flowchartTitleText{text-anchor:middle;font-size:18px;fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_61q\_ rect.text{fill:none;stroke-width:0;}#chatgpt-mermaid-\_r_61q\_ .icon-shape,#chatgpt-mermaid-\_r_61q\_ .image-shape{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-\_r_61q\_ .icon-shape p,#chatgpt-mermaid-\_r_61q\_ .image-shape p{background-color:rgb(0, 0, 0);padding:2px;}#chatgpt-mermaid-\_r_61q\_ .icon-shape .label rect,#chatgpt-mermaid-\_r_61q\_ .image-shape .label rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_61q\_ .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#chatgpt-mermaid-\_r_61q\_ .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#chatgpt-mermaid-\_r_61q\_ .node .neo-node{stroke:rgb(217, 163, 55);}#chatgpt-mermaid-\_r_61q\_ [data-look="neo"].node rect,#chatgpt-mermaid-\_r_61q\_ [data-look="neo"].cluster rect,#chatgpt-mermaid-\_r_61q\_ [data-look="neo"].node polygon{stroke:url(#chatgpt-mermaid-\_r_61q\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_61q\_ [data-look="neo"].swimlane.cluster rect{filter:none;}#chatgpt-mermaid-\_r_61q\_ [data-look="neo"].node path{stroke:url(#chatgpt-mermaid-\_r_61q\_-gradient);stroke-width:1px;}#chatgpt-mermaid-\_r_61q\_ [data-look="neo"].node .outer-path{filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_61q\_ [data-look="neo"].node .neo-line path{stroke:rgb(217, 163, 55);filter:none;}#chatgpt-mermaid-\_r_61q\_ [data-look="neo"].node circle{stroke:url(#chatgpt-mermaid-\_r_61q\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_61q\_ [data-look="neo"].node circle .state-start{fill:#000000;}#chatgpt-mermaid-\_r_61q\_ [data-look="neo"].icon-shape .icon{fill:url(#chatgpt-mermaid-\_r_61q\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_61q\_ [data-look="neo"].icon-shape .icon-neo path{stroke:url(#chatgpt-mermaid-\_r_61q\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_61q\_ .node text{font-size:14px;font-weight:600;letter-spacing:normal;fill:rgb(255, 228, 140);}#chatgpt-mermaid-\_r_61q\_ .edgeLabels text{font-size:13px;font-weight:600;letter-spacing:-0.08px;fill:rgb(255, 228, 140);}#chatgpt-mermaid-\_r_61q\_ .node tspan[font-weight="normal"],#chatgpt-mermaid-\_r_61q\_ .edgeLabels tspan[font-weight="normal"]{font-weight:600;}#chatgpt-mermaid-\_r_61q\_ .edgeLabel .label rect{opacity:1;rx:13px;ry:13px;fill:rgb(39, 29, 0);stroke:rgb(95, 79, 26);stroke-width:1px;}#chatgpt-mermaid-\_r_61q\_ .node rect,#chatgpt-mermaid-\_r_61q\_ .node circle,#chatgpt-mermaid-\_r_61q\_ .node ellipse,#chatgpt-mermaid-\_r_61q\_ .node polygon,#chatgpt-mermaid-\_r_61q\_ .node path{fill:rgb(77, 59, 0);stroke:rgba(255, 255, 255, 0.1);stroke-width:1px;}#chatgpt-mermaid-\_r_61q\_ .node rect{rx:16px;ry:16px;}#chatgpt-mermaid-\_r_61q\_ .mermaid-decision .label-container{fill:rgb(39, 29, 0);stroke:rgb(95, 79, 26);stroke-dasharray:2,2;}#chatgpt-mermaid-\_r_61q\_ .edgePaths .flowchart-link{stroke:rgb(175, 175, 175);stroke-width:1px;stroke-linecap:round;stroke-linejoin:round;}#chatgpt-mermaid-\_r_61q\_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_61q\_ :root{--mermaid-font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";}시작영화 선택상영 일정 선택좌석 현황 조회좌석 선택로그인 여부로그인좌석 예약 가능 여부 확인좌석 예약 가능?오류 메시지 출력총 금액 계산예매 정보 확인모의 결제예매 및 좌석 정보 저장완료아니오예아니오예

Flowchart phải thể hiện cả nhánh thành công và thất bại, không chỉ mô tả một luồng lý tưởng.

### **4.5. 업무 문서 리스트 — Business Document List**

Đây là danh sách các biểu mẫu hoặc thông tin được sử dụng trong quá trình vận hành nghiệp vụ.

Nhóm có thể làm bảng như sau:

| 문서 ID  | 문서명      | Mục đích            | Người sử dụng  |
| ------ | -------- | ------------------- | -------------- |
| DOC-01 | 회원 정보    | Thông tin tài khoản | Admin          |
| DOC-02 | 영화 정보    | Thông tin phim      | Customer/Admin |
| DOC-03 | 상영 일정표   | Lịch chiếu          | Customer/Admin |
| DOC-04 | 좌석 배치도   | Sơ đồ ghế           | Customer       |
| DOC-05 | 예매 내역서   | Kết quả đặt vé      | Customer       |
| DOC-06 | 예매 취소 내역 | Lịch sử hủy vé      | Customer/Admin |
| DOC-07 | 전체 예매 목록 | Theo dõi đặt vé     | Admin          |

Không cần tạo bảy file Word riêng. Đây là tài liệu liệt kê các loại thông tin hoặc chứng từ mà hệ thống sử dụng.

### **4.6. 개념적 데이터 모델 — Conceptual Data Model**

Đây là ERD ở mức khái niệm.

Cần thể hiện:

- Entity.
- Relationship.
- Cardinality.
- Primary Key ở mức định hướng.
- Các thuộc tính quan trọng.

Đầu ra: một sơ đồ ERD rõ ràng, được vẽ bằng Draw\.io hoặc công cụ ERD phù hợp.

### **4.7. 논리적 데이터 모델 — Logical Data Model**

Đây là phần chuyển ERD thành các Relation Schema.

Ví dụ:

```
USERS(
    user_id PK,
    username,
    password_hash,
    full_name,
    role,
    created_at
)

MOVIES(
    movie_id PK,
    title,
    genre,
    duration,
    rating,
    release_date,
    description
)

ROOMS(
    room_id PK,
    room_name
)

SEATS(
    seat_id PK,
    room_id FK,
    row_label,
    seat_number
)

SCREENINGS(
    screening_id PK,
    movie_id FK,
    room_id FK,
    start_at,
    end_at,
    ticket_price
)

BOOKINGS(
    booking_id PK,
    user_id FK,
    screening_id FK,
    booked_at,
    status,
    total_amount,
    payment_status
)

BOOKING_SEATS(
    booking_seat_id PK,
    booking_id FK,
    seat_id FK,
    unit_price
)
```

**Phải có phần chuẩn hóa dữ liệu (정규화).**

Ví dụ:

- 1NF: Mỗi ô chỉ lưu một giá trị, không lưu nhiều Seat ID trong một cột.
- 2NF: Thuộc tính không khóa phải phụ thuộc đầy đủ vào khóa chính.
- 3NF: Không có phụ thuộc bắc cầu giữa các thuộc tính không khóa.

Nhóm cần lấy các bảng thực tế của mình để phân tích, không chỉ ghi định nghĩa lý thuyết.

### **4.8. 물리적 데이터 모델 — Physical Data Model**

Đây là phần chuyển Logical Model thành database thực tế.

Phải có:

- DDL tạo bảng.
- Primary Key.
- Foreign Key.
- NOT NULL.
- UNIQUE.
- CHECK.
- DEFAULT.
- INDEX.
- TRIGGER nếu cần.

Ví dụ:

```
CREATE TABLE rooms (
    room_id INTEGER PRIMARY KEY,
    room_name TEXT NOT NULL UNIQUE
);

CREATE TABLE seats (
    seat_id INTEGER PRIMARY KEY,
    room_id INTEGER NOT NULL,
    row_label TEXT NOT NULL,
    seat_number INTEGER NOT NULL,

    FOREIGN KEY (room_id)
        REFERENCES rooms(room_id),

    UNIQUE (room_id, row_label, seat_number),

    CHECK (row_label IN ('A', 'B', 'C', 'D', 'E')),
    CHECK (seat_number BETWEEN 1 AND 10)
);
```

Đây chỉ là ví dụ một phần. Các bảng còn lại phải được triển khai đầy đủ và nhất quán với Logical Model.

### **4.9. 용어 사전 — Glossary**

Bắt buộc

Nên tạo bảng thuật ngữ riêng:

| Thuật ngữ | Tiếng Anh      | Định nghĩa                   |
| --------- | -------------- | ---------------------------- |
| 영화        | Movie          | Phim được cung cấp trong rạp |
| 상영관       | Room           | Phòng chiếu phim             |
| 좌석        | Seat           | Vị trí ghế trong phòng       |
| 상영 일정     | Screening      | Một lần chiếu phim cụ thể    |
| 예매        | Booking        | Một lượt đặt vé              |
| 예매 상세     | Booking Seat   | Danh sách ghế thuộc lượt đặt |
| 예매 상태     | Booking Status | Trạng thái đặt vé            |
| 취소        | Cancellation   | Hành động hủy lượt đặt       |
| 관리자       | Administrator  | Người quản trị hệ thống      |
| 고객        | Customer       | Người sử dụng dịch vụ đặt vé |

Nên thống nhất cách gọi ngay từ đầu để tránh lúc viết `Screening`, lúc lại dùng `Showtime` nhưng không có sự phân biệt rõ ràng.

### **4.10. 도메인 정의서 — Domain Definition**

Tài liệu này định nghĩa miền giá trị hợp lệ của các thuộc tính.

Ví dụ:

| Attribute      | Data Type     | Domain            | Constraint |
| -------------- | ------------- | ----------------- | ---------- |
| role           | TEXT          | CUSTOMER, ADMIN   | NOT NULL   |
| status         | TEXT          | BOOKED, CANCELLED | NOT NULL   |
| payment_status | TEXT          | UNPAID, PAID      | NOT NULL   |
| row_label      | TEXT          | A, B, C, D, E     | NOT NULL   |
| seat_number    | INTEGER       | 1–10              | NOT NULL   |
| duration       | INTEGER       | Số phút dương     | CHECK      |
| ticket_price   | INTEGER       | Số tiền dương     | CHECK      |
| start_at       | DATETIME/TEXT | Ngày giờ hợp lệ   | NOT NULL   |

Lưu ý: SQLite không có kiểu ENUM native. Sử dụng `TEXT CHECK(...)` để giới hạn giá trị.

### **4.11. 테이블 기술서 — Table Description**

Mô tả chi tiết từng bảng, từng column.

Ví dụ:

**Table: USERS**

| Column        | Type    | PK | FK | NN | Description      |
| ------------- | ------- | -- | -- | -- | ---------------- |
| user_id       | INTEGER | ✓  |    | ✓  | ID người dùng    |
| username      | TEXT    |    |    | ✓  | Tên đăng nhập    |
| password_hash | TEXT    |    |    | ✓  | Mật khẩu đã hash |
| full_name     | TEXT    |    |    | ✓  | Họ tên           |
| role          | TEXT    |    |    | ✓  | Quyền tài khoản  |
| created_at    | TEXT    |    |    | ✓  | Thời gian tạo    |

Làm tương tự cho cả 7 bảng.

### **4.12. 응용프로그램 + 데이터베이스 통합 파일 (.DB)**

Phần này phải chứng minh database không chỉ được thiết kế trên giấy mà đã được sử dụng trong ứng dụng.

Nhóm cần có:

- Chương trình Flask chạy được.
- File SQLite `.db`.
- Dữ liệu mẫu đầy đủ.
- Ứng dụng có thể đọc và ghi dữ liệu thực tế.
- Các chức năng trong giao diện phản ánh đúng trạng thái database.

**Định dạng bàn giao đề xuất:**

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
│   ├── seed.sql
│   └── cinema.db
│
├── docs/
│   ├── project_overview.pdf
│   ├── business_documents.pdf
│   └── database_design.pdf
│
├── presentation/
│   └── presentation.pptx
│
└── README.md
```

File `.db` là database SQLite thật, còn source code ứng dụng được đóng gói kèm theo. Không chỉ nộp file SQL rồi xem đó là database đã tích hợp.

## **5. Xây dựng ứng dụng demo**

Tao đề xuất làm giao diện đơn giản, ưu tiên chứng minh database hoạt động đúng.

### **Giao diện khách hàng**

[Am Saiyavath](https://images.openai.com/static-rsc-4/lFV9kQzjYcU-jSMRSIPMiIETu5PtenzqEK0MZ0HAtc11GIJreIVJeCx1FVNRXhaRyEQpod_KOVyrLoPvaoeglUbXwQZ24CtQS10ErsBplN1_uFA27yOhP17v0nt8IN0YB11Kb_Pc1OEPN1NimQkPwDrUXcCI_gZE0ZSGcoushcg?purpose=inline)

**1. Movie List**

Hiển thị danh sách 5 phim, poster, thể loại và thời lượng.

[Cinebook | Movie Booking Website by Rehanoor Hasan Rashed on Dribbble](https://images.openai.com/static-rsc-4/vdAsYqeMwHqi9wvFo68i3gSUJ5BTnwMmpXOBigBdm3JRRFuUnuKxPkPTscPfWcSVkr2y_lwX5EU0knYUA_PhJz6mblO5-SNVmDROnMRY5rFArLsVeicClnpB3fIx-OeT8Kph6--QJcHQHp5Gl7evpaxkbIdM5NtAg7T5XgTAS_Q?purpose=inline)

**2. Screening Selection**

Chọn phim, ngày chiếu, giờ chiếu và phòng.

[GitHub - VyLanTran/RoyalCinemaWebApp: Royal Cinema · GitHub](https://images.openai.com/static-rsc-4/UnG4awL2ZCbR77n4pjPTKUIQTXBFrfjIi8mAkj--oepDQs9hkDNgWkmpY53yY95GuQkz9vr-txj9ubcawDej1YEaF5KcSGoF-vn1VRXZgEGHRjtOlLS0j9E3lsbTERo09Dtq4vmDjSv9nofmqTp8lXG9DHIVqvoV_G818sgcVjI?purpose=inline)

**3. Seat Selection**

Hiển thị 5 hàng A–E, mỗi hàng 10 ghế. Ghế trống, đã đặt và đang được chọn phải có trạng thái khác nhau.

[Movie Ticket Booking App and Website Design](https://images.openai.com/static-rsc-4/VeVg1ODAK3xCWnMZgkNhmMqZUJcVV75Y4-Dz3onx_YPwqfPZZOb-CM3nO6IOgtJZ6DTzhiSbilQHpV1MH72GiFl6pVLAnMJdRigilid6VeCp1JxbY4cQhXTqoShseZ-VcHgNz9TmRe0c71WniAu1Hs2xnLiOBr9Hpcfucx3-_sU?purpose=inline)

**4. Booking Confirmation**

Hiển thị thông tin suất chiếu, ghế đã chọn, tổng tiền và nút thanh toán mô phỏng.

[Movie Ticket booking POS System by Rajesh Mandaviya on Dribbble](https://images.openai.com/static-rsc-4/vUFH_3PKoj60cFYoXVaVKqFwl8QkL5l6FaY6OQbz_0KjP77Xs7zu-ZJK-zobgyuBYRXuqh8aci2IlZSFw5F3XvDv7s5QOS7YTmrLj1FvnfeiLPtQBpUBBkP5cLJ4hj_FPHCoTwurfXJCl9LV7qQ9XwyBe-UBOkWc4QZlriMOmMg?purpose=inline)

**5. My Bookings**

Xem lịch sử booking và hủy lượt đặt hợp lệ.

### **Giao diện admin**

Chỉ cần ba chức năng:

1. Quản lý phim: thêm và sửa.
2. Quản lý suất chiếu: thêm, sửa và kiểm tra lịch trùng.
3. Xem toàn bộ booking.

Không cần thiết kế dashboard phức tạp hay hiệu ứng giao diện.

### **Luồng hoạt động cần hoàn thành**

```
Flask Application
       │
       ▼
   User Login
       │
       ▼
 Movie / Screening
       │
       ▼
  Select Seats
       │
       ▼
 Validate Availability
       │
       ▼
  Confirm Booking
       │
       ▼
 Simulated Payment
       │
       ▼
  SQLite Database
       │
       ▼
 Booking + Booking Seats
```

Một điểm kỹ thuật quan trọng: khi kiểm tra ghế và lưu booking, cần thực hiện trong transaction để tránh hai người đồng thời đặt cùng một ghế. Có thể sử dụng `BEGIN IMMEDIATE`, kiểm tra lại trạng thái ghế và chỉ `COMMIT` khi toàn bộ thao tác thành công. Nếu lỗi thì `ROLLBACK`.

## **6. Kế hoạch thực hiện trong 14 ngày**

Hôm nay là 11/11, hạn nộp là 29/11. Nhóm nên hoàn thành phiên bản chính vào ngày 24/11, giữ 5 ngày cuối để kiểm tra và sửa lỗi.

| Ngày  | Công việc chung               | Thành viên A                        | Thành viên B                |
| ----- | ----------------------------- | ----------------------------------- | --------------------------- |
| 11/11 | Khởi động dự án               | Chốt cấu trúc database              | Chốt phạm vi nghiệp vụ      |
| 12/11 | Phân tích hệ thống            | Xác định entity                     | Vẽ chức năng, nghiệp vụ     |
| 13/11 | Hoàn thành thiết kế sơ bộ     | Conceptual ERD                      | Overview, Function Diagram  |
| 14/11 | Hoàn thành tài liệu nghiệp vụ | Review ERD                          | Unit Description, Flowchart |
| 15/11 | Thiết kế database             | Logical Model, chuẩn hóa            | Business Document List      |
| 16/11 | Hoàn thiện thiết kế           | Domain, Glossary, Table Description | Thiết kế giao diện Flask    |
| 17/11 | Xây dựng database             | Viết DDL, Constraints               | Xây dựng Login              |
| 18/11 | Tạo dữ liệu mẫu               | Seed 140 suất, 250 ghế              | Movie, Screening            |
| 19/11 | Phát triển ứng dụng           | Kiểm tra database                   | Seat Selection, Booking     |
| 20/11 | Phát triển ứng dụng           | Kiểm tra ràng buộc                  | Payment, Booking History    |
| 21/11 | Hoàn thiện chức năng          | Admin/DB integration                | Cancellation, Admin UI      |
| 22/11 | Integration Test              | Test database                       | Test toàn bộ ứng dụng       |
| 23/11 | Hoàn thiện tài liệu           | Review database documents           | PPT, Flowchart              |
| 24/11 | Đóng băng phiên bản           | Kiểm tra DB cuối                    | Kiểm tra ứng dụng và demo   |

### **Thời gian dự phòng: 25/11–29/11**

- 25–26/11: sửa lỗi và hoàn thiện các tài liệu.
- 27/11: chạy thử toàn bộ hệ thống.
- 28/11: kiểm tra file nộp, backup và đóng gói.
- 29/11: nộp trước 23:59.

Không nên để đến ngày 29 mới tạo file PDF, PPT hoặc database cuối cùng.

## **7. Các tình huống phải kiểm thử**

Đây là phần rất quan trọng khi thuyết trình, vì giảng viên có thể thử thao tác trực tiếp trên ứng dụng.

| ID    | Test case                            | Kết quả mong muốn               |
| ----- | ------------------------------------ | ------------------------------- |
| TC-01 | Đăng ký tài khoản khách              | Tạo account thành công          |
| TC-02 | Đăng ký với username đã tồn tại      | Báo lỗi                         |
| TC-03 | Khách chưa đăng nhập xác nhận đặt vé | Yêu cầu đăng nhập               |
| TC-04 | Hai khách đặt cùng ghế, cùng suất    | Chỉ một người đặt thành công    |
| TC-05 | Đặt ghế thuộc phòng khác             | Từ chối                         |
| TC-06 | Đặt vé cho suất đã bắt đầu           | Từ chối                         |
| TC-07 | Hủy booking trước giờ chiếu          | Hủy thành công, ghế được mở lại |
| TC-08 | Hủy booking sau giờ bắt đầu          | Từ chối                         |
| TC-09 | Khách xem booking của người khác     | Không được phép                 |
| TC-10 | Admin thêm suất bị trùng lịch        | Từ chối                         |
| TC-11 | Customer truy cập chức năng admin    | Không được phép                 |
| TC-12 | Admin thêm phim mới                  | Database cập nhật thành công    |

Đặc biệt, hãy thực hiện TC-04 và TC-07 trực tiếp khi demo. Đây là hai tình huống chứng minh database xử lý nghiệp vụ đặt ghế đúng.

## **8. Nội dung PowerPoint thuyết trình**

Đề xuất khoảng 10 slide:

| Slide | Nội dung                                       |
| ----- | ---------------------------------------------- |
| 1     | Project Title, thành viên                      |
| 2     | Project Background & Objectives                |
| 3     | Project Scope & System Functions               |
| 4     | Business Flowchart                             |
| 5     | Conceptual ER Diagram                          |
| 6     | Logical Data Model & Normalization             |
| 7     | Physical Data Model, DDL & Constraints         |
| 8     | Application & Database Integration             |
| 9     | Demo: Đăng nhập → Chọn phim → Đặt ghế → Hủy vé |
| 10    | Testing Results & Conclusion                   |

**Phân bổ thời gian thuyết trình:** ưu tiên ERD, chuẩn hóa, các ràng buộc và demo. Không dành quá nhiều thời gian giới thiệu giao diện.

Lưu ý lịch thuyết trình: 14주차 ngày 1/12 (thứ Ba) và 3/12 (thứ Năm), mỗi ngày hai nhóm theo đề bài. Nhóm cần xác định lịch của mình để chuẩn bị phần demo.

## **9. Những vấn đề phải thống nhất trước khi bắt đầu code**

Có một số chi tiết file mô tả chưa đưa ra giá trị cụ thể. Nhóm cần quyết định và ghi lại thành quy tắc thiết kế:

| Vấn đề            | Đề xuất                                                                          |
| ----------------- | -------------------------------------------------------------------------------- |
| Giá vé            | Dùng một mức giá demo cố định, ví dụ 12.000 KRW; ghi rõ đây là giả định của nhóm |
| Phim              | Tạo 5 phim mẫu có thông tin đầy đủ                                               |
| Thời lượng        | Không quá 150 phút                                                               |
| Admin             | Seed sẵn 1 tài khoản                                                             |
| Customer          | Seed 1–2 tài khoản demo, đồng thời cho phép đăng ký                              |
| Thanh toán        | Mô phỏng thành công, cập nhật trạng thái PAID                                    |
| Hoàn tiền khi hủy | Không triển khai vì đề bài chỉ yêu cầu hủy vé và mở lại ghế                      |
| Database          | SQLite, file `cinema.db`                                                         |

Dữ liệu ban đầu phải đảm bảo:

- 5 phòng.
- 50 ghế mỗi phòng.
- 250 ghế tổng cộng.
- 5 phim.
- 20 suất chiếu mỗi ngày.
- 140 suất chiếu trong 7 ngày.

Đây là các con số cần kiểm tra trực tiếp bằng SQL trước khi đóng gói database.&#x20;

영화관에 예매 및 좌석 관라 시스템.md



## **10. Tiêu chí xác nhận dự án hoàn thành**

**Project Completion Checklist**

# **0/16**

프로젝트 개요서

업무 기능도

단위 업무 기술서

업무 흐름도

업무 문서 리스트

개념적 데이터 모델 (ERD)

논리적 데이터 모델 + 정규화

물리적 데이터 모델 + DDL

용어 사전

도메인 정의서

테이블 기술서

Flask Application + SQLite .db

Dữ liệu mẫu đầy đủ

Kiểm thử 12 tình huống

PowerPoint + kịch bản demo

README hướng dẫn chạy dự án

Reset checklist

## **Kết luận: Thứ tự nhóm nên làm ngay**

Tao muốn nhóm tuân thủ đúng thứ tự này:

1. **Chốt 7 bảng và các mối quan hệ.** Không bắt đầu code giao diện khi database chưa được thống nhất.
2. **Hoàn thành ERD và Logical Model.** Đây là nền tảng cho các tài liệu còn lại.
3. **Tạo SQLite database và dữ liệu mẫu.**
4. **Bắt đầu Flask application và tích hợp database.**
5. **Hoàn thiện toàn bộ tài liệu, kiểm thử và PPT.**

Một lỗi cần tránh là làm tài liệu ERD một kiểu, viết SQL một kiểu, rồi giao diện lại sử dụng cấu trúc khác. Tất cả phải xuất phát từ cùng một thiết kế dữ liệu.

**Bước tiếp theo nên thực hiện:** bắt đầu với việc xây dựng bộ tài liệu phân tích database, bao gồm ERD, Logical Model và danh sách thuộc tính chuẩn cho cả 7 bảng. Sau khi hai người thống nhất phần này, việc code sẽ thuận lợi hơn nhiều.

Có thể đặt nhắc kiểm tra tiến độ dự án mỗi 2 ngày đến hạn nộp:

📚Nhắc kiểm tra tiến độ dự ánNhấn để thiết lập