Hệ thống đặt vé xem phim và quản lý ghế
Nov 10, 2026 · @unho-drgn
Mục tiêu
Hệ thống cho phép người dùng xem suất chiếu, chọn ghế, đặt và hủy vé, đồng thời kiểm tra tình trạng ghế của từng suất. Phần thuyết trình tập trung vào thiết kế cơ sở dữ liệu; giao diện chỉ cần đủ để minh họa.
Phạm vi dự án — 프로젝트 범위
Phạm vi đã chốt đầy đủ, không còn điểm bỏ ngỏ.
Nội dung
Phạm vi
Rạp
1 rạp, 5 phòng chiếu
Ghế
50 ghế/phòng (5 hàng A–E × 10 ghế), tổng 250 ghế
Dữ liệu ban đầu
5 phim mẫu và các suất chiếu trong 7 ngày
Người dùng
Khách hàng và quản trị viên
Thanh toán
Mô phỏng: bấm thanh toán là đánh dấu đã thanh toán, không dùng cổng thật
Tài khoản
Cho đăng ký tài khoản khách hàng; tạo sẵn 1 tài khoản admin và 1–2 tài khoản khách demo

Chức năng chính
Đăng ký (khách hàng), đăng nhập, đăng xuất; phân quyền khách hàng và quản trị viên.
Xem danh sách phim và suất chiếu.
Xem ghế trống/đã đặt của một suất chiếu.
Chọn một hoặc nhiều ghế, xem tổng tiền và xác nhận đặt vé với thanh toán mô phỏng.
Xem và hủy vé đã đặt của bản thân.
Quản trị viên thêm/sửa phim và suất chiếu, xem danh sách đặt vé.
Quy tắc nghiệp vụ
Mỗi phòng chiếu có nhiều ghế; mỗi ghế thuộc đúng một phòng.
Mỗi suất chiếu gắn với một phim và một phòng.
Không xếp các suất chiếu chồng thời gian trong cùng phòng.
Khách hàng phải đăng nhập trước khi xác nhận đặt vé.
Một lần đặt vé chỉ thuộc một suất chiếu, nhưng có thể gồm nhiều ghế.
Ghế được chọn phải thuộc phòng của suất chiếu đó.
Mỗi ghế chỉ được có một lượt đặt còn hiệu lực trong cùng suất chiếu.
Khách hàng chỉ được xem và hủy vé của chính mình.
Cho phép hủy toàn bộ một lần đặt trước giờ chiếu; các ghế được mở lại để đặt.
Không cho đặt vé cho suất đã bắt đầu.
Chỉ quản trị viên được thêm/sửa phim và suất chiếu; đăng ký chỉ tạo được tài khoản khách hàng.
Mô tả nghiệp vụ chính — 주요 업무 설명
Chức năng cho biết hệ thống làm được gì; bảng dưới giải thích mỗi việc diễn ra như thế nào.
Nghiệp vụ
Người thực hiện
Xử lý chính
Kết quả
Đăng nhập
Khách hàng, quản trị viên
Nhập ID/mật khẩu, kiểm tra tài khoản và quyền
Mở chức năng phù hợp; sai thì báo lỗi
Tra cứu suất chiếu
Người xem
Chọn phim và ngày
Hiển thị giờ chiếu, phòng và ghế còn trống
Đặt vé
Khách hàng đã đăng nhập
Chọn suất, ghế; kiểm tra ghế; tính tiền; xác nhận và thanh toán mô phỏng
Lưu vé và cập nhật tình trạng ghế
Hủy vé
Khách hàng đã đăng nhập
Chọn vé của mình, kiểm tra chưa đến giờ chiếu, xác nhận hủy
Lưu trạng thái hủy và mở lại ghế
Quản lý phim
Quản trị viên
Nhập hoặc sửa thông tin phim
Lưu thông tin phim
Quản lý suất chiếu
Quản trị viên
Chọn phim, phòng, giờ; kiểm tra trùng lịch
Lưu suất chiếu hợp lệ











Dữ liệu mẫu
Mỗi ngày có 20 suất chiếu (5 phòng × 4 suất), mỗi phim chiếu 4 lần ở các phòng và khung giờ khác nhau.
Phòng
10:00
13:00
16:00
19:00
Phòng 1
Phim 1
Phim 2
Phim 3
Phim 4
Phòng 2
Phim 2
Phim 3
Phim 4
Phim 5
Phòng 3
Phim 3
Phim 4
Phim 5
Phim 1
Phòng 4
Phim 4
Phim 5
Phim 1
Phim 2
Phòng 5
Phim 5
Phim 1
Phim 2
Phim 3

Các suất cùng phòng cách nhau 3 giờ, nên phim mẫu dài tối đa khoảng 2h30 để còn 15–30 phút nghỉ và không chồng giờ. Seed 7 ngày liên tiếp từ ngày demo (140 suất), cùng 250 ghế, 1 tài khoản admin và 1–2 tài khoản khách demo.
Lưu ý khi thiết kế database
Quy tắc "mỗi ghế chỉ có một lượt đặt còn hiệu lực trong cùng suất" sẽ chặn việc đặt lại ghế nếu vẫn giữ dòng ghế của vé đã hủy.
Lưu ghế đã đặt ở bảng chi tiết đặt vé, với ràng buộc duy nhất theo (suất chiếu, ghế).
Khi hủy: đổi trạng thái lần đặt thành "đã hủy" và xóa các dòng ghế của lần đặt đó, để ghế được mở lại. Bảng đặt vé vẫn giữ lịch sử hủy.
Mỗi ghế là một dòng gắn với phòng, duy nhất theo (phòng, hàng, số ghế); việc không trùng giờ giữa các suất cùng phòng được kiểm tra khi admin lưu suất chiếu.
