# Xem lại bài thi và log chẩn đoán

Cập nhật: **25/10/2026**.

## Chi tiết bài thi

Trang xem bài dùng chung cho Kết quả & xem lại, hồ sơ sinh viên và Điều phối
kỳ thi có các tab:

- **Tổng quan & điểm:** lịch sử lượt thi, điểm tổng, tiến độ xử lý, thao tác
  quản lý bản ghi và form giảng viên xác nhận/chấm lại điểm.
- **Câu trả lời:** chọn một câu để xem đề, transcript, audio/video cũ, rubric
  và điểm phát âm. Nhận dạng/chấm lại AI và lịch sử nằm trong phần mở rộng.
- **Màn hình & giám sát:** chọn đoạn ghi màn hình và xem sự kiện giám sát.
- **Log xử lý:** chỉ admin; lọc log theo ID lượt thi đang xem.

Chỉ dựng trình phát media của tab/câu đang chọn; chuyển tab/câu sẽ dừng
trình phát trước đó. Form điểm tổng giữ nội dung khi chuyển tab trong cùng
lượt thi. Mở lượt khác đặt lại tab và câu đang xem. Quyền chấm và sửa điểm
vẫn được API kiểm soát theo vai trò và phạm vi môn/lớp hiện hành.

## Danh sách thí sinh trong Điều phối kỳ thi

Mỗi thẻ kỳ thi hiển thị số sinh viên được giao và tổng lượt thi, có nút
**Danh sách thí sinh** mở thẳng phần Sinh viên & lịch thi. Bảng tìm theo tên,
MSSV hoặc email; có bộ lọc đã nộp bài, cột **Số lượt thi** và nút
**Xem bài lần N** cho từng lượt. Bấm tên sinh viên mở lượt mới nhất. Khi quay
lại danh sách, bộ lọc được giữ. Danh sách tự cập nhật mỗi 10 giây khi đang
hiển thị và trình duyệt không bị ẩn.

Số lượt thi đếm các phiên chưa xóa có trạng thái khác `DEVICE_CHECK`, gồm
lượt đang thi và đã kết thúc. Phiên kiểm tra thiết bị vẫn xuất hiện để theo
dõi nhưng chưa tính vào số lượt. Không dùng số thứ tự `attempt_number` làm
số lượt vì có thể có lượt đã xóa. Quyền xem danh sách/bài thi vẫn theo phạm
vi API hiện hành. Tổng ở thẻ kỳ thi được cập nhật khi tải danh sách kỳ thi.

## Log hệ thống dành cho admin

Menu **Log hệ thống** đọc sự kiện API, WEB, AI và WORKER. Có bộ lọc nguồn,
mức log, model (đúng tên), khoảng thời gian và mã liên kết. Bấm một dòng để
xem metadata; lỗi tác vụ (`operation_failed`) mới được ghi ở mức ERROR. Log
trước bản sửa vẫn ở mức WARNING, không chuyển đổi lịch sử. Tải log cũ bằng cursor hoặc bật làm mới mỗi 10 giây. Mặc định
xem 24 giờ gần nhất; đổi sang 7 ngày để tra bài cũ.

- **API:** HTTP method, route template, status, thời gian, request ID và
  loại exception nếu lỗi không được xử lý. ID tài nguyên dạng UUID từ route
  hỗ trợ đối chiếu với lượt thi/câu trả lời. Bỏ qua healthcheck và chính các
  endpoint log để tránh tự tạo log khi đọc log.
- **WEB:** request thất bại sau cơ chế retry, lỗi JavaScript và promise
  không được xử lý khi người dùng đã đăng nhập. Có HTTP status/request ID
  nếu nhận được, route template; lỗi toàn cục có tên màn hình và loại lỗi.
- **AI:** bắt đầu/kết thúc/thất bại ở bước STT, chấm bài, xử lý kết quả có
  cấu trúc; lời gọi Ollama/Gemini/GOPT được gắn provider/model, thời gian,
  timeout/HTTP status/loại exception và metrics sẵn có. `operation_id`
  nối sự kiện đầu/cuối; `request_id`, `session_id`, `attempt_id`, `job_id`
  và `exam_id` nối API, bài thi và tác vụ worker khi có ngữ cảnh.
- **WORKER:** trạng thái xử lý hàng đợi STT/chấm và tác vụ nhận dạng/chấm lại.

Đây là log ứng dụng được thu thập từ bản triển khai này, không phải toàn bộ
stdout của container, Jenkins, Next server hay nội bộ inference server.
Lỗi mạng khiến browser không gửi được telemetry sẽ không có WEB event;
lỗi trước khi API nhận request cần kiểm tra proxy/hạ tầng. Sự kiện bắt đầu
không có kết thúc có thể do tác vụ còn chạy, tiến trình bị ngắt hoặc log đã
bị giới hạn lưu trữ; không tự kết luận tác vụ đang chạy.

## Lưu trữ, quyền và vận hành

`GET /admin/diagnostics` yêu cầu ADMIN (hỗ trợ tài khoản nhiều vai trò).
Lọc theo `source`, `level`, `model`, `correlation`, `since`; phân trang bằng
`before` và `limit` (1–100, mặc định 50), mới nhất trước. `correlation` so
khớp chính xác một mã request/tài nguyên/lượt thi/câu/tác vụ/kỳ thi/operation.
`POST /diagnostics/client` yêu cầu đăng nhập; chỉ nhận schema metadata cố
định và chuẩn hóa URL thành route template. Browser tối đa 10 sự kiện/phút;
server tối đa 20 WEB event/phút/tài khoản. WEB event là báo cáo từ client,
không phải chứng cứ bảo đảm tính xác thực của hoạt động.

Kho SQLite riêng ở `DATA_DIR/diagnostics/events.sqlite3`, API và worker dùng
chung volume `app_data` trong Compose. Tạo tự động, không cần migration
schema nghiệp vụ. Giữ tối đa 10.000 sự kiện hoặc 7 ngày; dọn khi ghi và loại
log hết hạn khi đọc. Cần thư mục ghi được trên volume cục bộ; triển khai nhiều
host không có chung volume cần giải pháp tập trung riêng. Kho log không nằm
trong MinIO và không thuộc màn hình quản lý bản ghi thi.

### Tra lỗi chấm phát âm không thấy trên giao diện

`PRONUNCIATION_FAILED` là lỗi chung của bước phát âm, không đủ để kết luận
GOPT bị timeout. Bản sửa ghi sự kiện `gopt.pronunciation` ở nguồn **AI**, mức
**ERROR**, model `gopt-librispeech`, với `code=PRONUNCIATION_FAILED` và
`reason_code`. Sự kiện này có cả khi kiểm tra đầu vào thất bại trước lời gọi
HTTP: GOPT đang tắt, ngôn ngữ khác `en`, thiếu transcript/audio, audio quá lớn
hoặc sai checksum. Lỗi HTTP phân biệt 413 (quá lớn), 422 (đầu vào không xử lý
được), 429 (bận), 504 (timeout); có mã riêng cho lỗi kết nối và kết quả sai
định dạng. Không lưu nội dung response hoặc exception thô. Lỗi chấm lại hiển
thị thông báo tương ứng; khi thất bại vẫn giữ đánh giá cũ.

Để tra tác vụ cũ, chọn nguồn/mức **Tất cả**, bỏ bộ lọc model, chọn **Tất cả
log còn lưu**, nhập đúng UUID tác vụ và bấm **Lọc log**. Trước bản sửa, lỗi
kiểm tra phát âm nằm ở nguồn WORKER / WARNING (`pronunciation`), lỗi HTTP
GOPT ở AI / WARNING (`gopt.assess`). Bộ lọc ERROR hoặc chỉ AI có thể bỏ sót.

Nếu vẫn không có log, đối chiếu stdout worker theo UUID, kiểm tra API và
worker cùng phiên bản và cùng `DATA_DIR`/volume có quyền ghi. Kiểm tra cả giới
hạn lưu trữ 7 ngày/10.000 sự kiện; lỗi cũ lưu trong lịch sử bài thi có thể tồn
tại lâu hơn log. Kho log lỗi sẽ bỏ sự kiện để bài thi tiếp tục; stdout worker
vẫn là nơi đối chiếu. Không thể khôi phục chi tiết lỗi cũ chỉ từ thông báo
`PRONUNCIATION_FAILED`, và bản sửa không nhập lại log container cũ.

Chỉ lưu metadata cho phép, không lưu request body, header/token, prompt,
transcript, bài làm, response model hay thông báo exception thô. Trace chỉ
gồm tên file, số dòng và hàm, không có biến cục bộ. Ghi log dùng transaction
độc lập; disk/SQLite không sẵn sàng thì bỏ sự kiện để luồng thi tiếp tục.
Đọc kho lỗi trả 503 với mã `DIAGNOSTICS_UNAVAILABLE`. Cập nhật API, worker
và web cùng phiên bản để có đầy đủ log và UI.
