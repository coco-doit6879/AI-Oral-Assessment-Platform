# Quy trình khảo thí, duyệt đề, lịch thi và điểm chính thức

Hướng dẫn này mô tả kỳ thi được tạo trong **Điều phối kỳ thi**. Một kỳ thi ứng với một đề thuộc một môn; mỗi môn có một giảng viên phụ trách theo `Course.owner_id`. Phân công lại môn chuyển quyền quản lý toàn bộ đề và bài chấm của môn đó.

## Phân quyền

| Role | Quyền |
| --- | --- |
| ADMIN | Cấp/thu hồi role; quản trị hệ thống và hỗ trợ mọi bước |
| EXAM_OFFICER | Tạo kỳ thi, phân công tài khoản có quyền TEACHER (gồm ADMIN), nhập Excel, xem đề đã duyệt, trả đề, xếp lịch, mở thi, xuất điểm |
| TEACHER | Khi không có ADMIN/EXAM_OFFICER, chỉ quản lý môn được phân công; cấu hình đề, sinh/sửa câu hỏi và rubric, duyệt gửi khảo thí; chấm lại bài thuộc môn |
| STUDENT | Đăng nhập email/mật khẩu hoặc Google trên desktop, xem bài được giao, thi đúng lịch, xem xác nhận nộp bài |

Admin mở **Người dùng** để tạo tài khoản hoặc phân role EXAM_OFFICER cho nhân sự khảo thí. Một tài khoản có thể có nhiều vai trò; quyền được cộng gộp, ADMIN có mọi quyền. Vai trò được kiểm tra ở mỗi request; danh sách, lịch và trạng thái đề vẫn áp dụng. [Chi tiết phân quyền](multi-role-access.md). Có mẫu Excel nhập giảng viên/khảo thí tại trang quản lý người dùng.

## Bố cục Điều phối kỳ thi

Danh sách có tìm kiếm theo tên/môn và lọc trạng thái. Mở phần tạo kỳ thi hoặc
nhập Excel khi cần; bấm **Mở kỳ thi** để xem chi tiết. Tab **Đề thi & duyệt**
chứa cấu hình, soạn, duyệt và mở thi; tab **Sinh viên & lịch thi** chứa nhập
sinh viên, chọn danh sách, xếp lịch và xuất điểm. Nút tự xuống dòng trên màn
hình nhỏ; bảng rộng cuộn ngang trong vùng riêng.

Câu hỏi có nút **Sửa câu N**, editor định dạng/chèn ảnh cho admin, giảng
viên và khảo thí trên bản GENERATED. **Xong câu** xem trước, **Lưu nội dung
đã review** mới lưu server. Đề đã duyệt/công bố cần sao chép giữ nội dung để
sửa và duyệt lại. [Editor và minh chứng mới](question-editor-recording.md).

## Tổ chức một kỳ thi

1. Admin tạo môn học và phân role TEACHER cho giảng viên.
2. Khảo thí mở **Điều phối kỳ thi → Tạo kỳ thi**, nhập tên kỳ thi, môn, giảng viên và thời lượng. Hệ thống tạo đề DRAFT cùng rubric tạm; giảng viên cần cấu hình trước khi sinh đề.
3. Khảo thí tải [Excel mẫu](../templates/danh-sach-sinh-vien.xlsx), sửa dữ liệu rồi nhập trong tab **Sinh viên & lịch thi** của kỳ thi. Có thể nhập trước khi giảng viên soạn đề.
4. Giảng viên vào **Môn học → môn được giao** để bổ sung giáo trình, chủ đề và LO. Trong **Ngân hàng đề thi → chọn môn → Sửa bản nháp**, chọn rubric, số câu và độ khó EASY/MEDIUM/HARD. Mỗi hàng blueprint có chủ đề, độ khó, số lượng; chọn số lượng 1 để cấu hình từng câu. Tối đa 20 câu.
5. Cấu hình **Hotword STT của môn học** nếu cần, rồi bấm **Sinh câu hỏi & rubric để review**. AI tạo bản GENERATED, chưa mở cho sinh viên. Demo tạo nội dung mẫu, không chấm điểm AI thật.
6. Giảng viên sửa câu hỏi, ý chính mong đợi, tên/mô tả/điểm tối đa/trọng số rubric; bấm **Lưu nội dung đã review**, sau đó **Duyệt đề & gửi khảo thí**. Trạng thái TEACHER_APPROVED. Các nguồn tham chiếu phải nằm trong tài liệu của chủ đề; server kiểm tra điều này.
7. Khảo thí xem toàn bộ đề/rubric trong **Điều phối kỳ thi → Đề thi & duyệt**. Nếu cần sửa, nhập lý do **Trả về bản nháp**; hệ thống hủy bản sinh và dấu duyệt, giảng viên cấu hình/sinh/review lại.
8. Trong tab **Sinh viên & lịch thi**, khảo thí chọn một, nhiều hoặc tất cả sinh viên, nhập giờ mở/đóng vào thi rồi **Lưu lịch thi**. Chỉ xếp lịch sau khi giảng viên duyệt. Mỗi sinh viên có thể có khung giờ riêng; thời gian nhập theo múi giờ máy, lưu dưới dạng Unix timestamp.
9. Khi tất cả sinh viên có lịch hợp lệ, khảo thí bấm **Xác nhận đã kiểm tra đề & mở kỳ thi**. Trạng thái PUBLISHED, khóa đề, danh sách và lịch. Bản snapshot lưu câu hỏi, rubric, nguồn kiến thức, cấu hình AI, hotword môn học và dấu duyệt.
10. Sinh viên mở desktop, đăng nhập bằng email trong Excel, vào **Bài thi của tôi**, chọn bài khi đến giờ. Server kiểm tra danh sách và lịch ở cả bước tạo phiên và bắt đầu thi. Quyền thi kỳ thi dựa trên danh sách và lịch được khảo thí xác nhận.
11. Sau khi nộp, worker server chấm AI. Bài có điểm AI trung bình **< 5/10**, thiếu điểm hoặc cần kiểm tra độ tin cậy chuyển REVIEW_REQUIRED; sinh viên chưa thấy điểm chính thức.
12. Giảng viên mở **Kết quả & xem lại**. Bài dưới 5 có nền cảnh báo và điểm AI đề xuất. Xem transcript/audio/video, nhập điểm 0–10 cùng nhận xét ít nhất 10 ký tự, bấm **Lưu điểm chính thức**. Hệ thống lưu riêng điểm AI, người chấm lại, thời gian và lý do; giữ audit trước/sau.
13. Khảo thí chọn **Xuất điểm Excel** trong kỳ thi. Mỗi lần thi không bị xóa là một dòng; sinh viên chưa thi vẫn có dòng NOT_STARTED. `final_score` chỉ có khi COMPLETED; điểm đang chờ duyệt không bị xuất nhầm thành điểm chính thức.

Giờ đóng là **hạn bắt đầu vào thi**, không phải thời điểm cưỡng bức kết thúc mọi phiên. Sau khi bắt đầu hợp lệ, sinh viên có đủ `time_limit`. Khung giờ vào thi tối thiểu bằng thời lượng đề. Đề đã PUBLISHED không sửa trực tiếp; tạo kỳ thi mới khi cần thay đề/lịch/danh sách.

## Excel

File `.xlsx`, sheet đầu tiên, đúng 4 cột theo thứ tự:

| Cột | Ý nghĩa |
| --- | --- |
| student_number | MSSV bắt buộc; dùng ô Text để giữ số 0 đầu; tối đa 80 ký tự |
| email | Email bắt buộc, được chuẩn hóa chữ thường; phải khớp tài khoản đăng nhập |
| full_name | Họ tên bắt buộc, tối đa 150 ký tự |
| initial_password | Tùy chọn, 12–128 ký tự nếu nhập; chỉ dùng khi tạo tài khoản mới |

Thay/xóa dòng ví dụ trong mẫu trước khi nhập. Nếu để trống mật khẩu ở tài khoản mới, sinh viên cần đăng nhập Google bằng đúng email (admin phải bật Google login). Google chỉ tự gắn danh tính có `email_verified=true` với duy nhất tài khoản STUDENT đang hoạt động do import tạo (`sv-…`); không tự liên kết tài khoản quản trị/giảng viên hoặc tài khoản thủ công. Tài khoản có sẵn giữ tên, mật khẩu và role, không bị Excel ghi đè.

Giới hạn 2 MB, 5000 sinh viên, 20 MB sau giải nén. Không nhận công thức, email/MSSV trùng, MSSV xung đột với danh sách cũ hoặc email thuộc tài khoản khác role. Toàn bộ import nằm trong một transaction: một dòng lỗi hủy cả lượt nhập. Nhập lại cùng danh sách không tạo thêm assignment. Mật khẩu được hash; không lưu trong audit hoặc trả về ở export.

Export gồm `student_number`, `email`, `full_name`, `attempt`, `status`, `ai_score`, `final_score`, `review_reason`. Chuỗi được ghi dưới kiểu text để tên sinh viên bắt đầu bằng `=` không trở thành công thức Excel.

## Hotword STT

Hotword được lưu riêng theo môn. Admin hoặc giảng viên quản lý môn vào **Ngân hàng đề thi → chọn môn → Hotword STT của môn học**. API GET/PUT `/admin/courses/{id}/hotwords` kiểm tra quyền với đúng môn đó. Mỗi môn có danh sách độc lập; xóa danh sách một môn không ảnh hưởng môn khác.

Tối đa **500 từ/cụm từ**, **100 ký tự mỗi mục**, **10.000 ký tự tổng cộng** (không tính dấu xuống dòng). Bỏ khoảng trắng đầu/cuối, dòng trống và mục trùng trước khi tính giới hạn. Web hiển thị bộ đếm và thông báo lỗi tiếng Việt trước khi gửi; API kiểm tra lại và từ chối toàn bộ nếu vượt giới hạn, không lưu một phần. Electron dùng cùng giới hạn, kể cả ký tự Unicode.

Từ vựng môn được cố định trong snapshot khi sinh hoặc công bố đề; muốn thay cần trả về nháp và sinh/duyệt lại. Snapshot có danh sách rỗng giữ nguyên danh sách rỗng. Nếu snapshot thiếu trường hotword, hệ thống dùng danh sách hiện tại của chính môn đó. `/stt/config` chỉ trả từ vựng khi có phiên thi hợp lệ.

API cấu hình giọng nói lưu nhà cung cấp, ngôn ngữ và tiền xử lý. Từ vựng được quản lý qua API hotword của môn học.

Desktop lấy `/stt/config?session_id=…`; server kiểm tra chủ sở hữu phiên rồi trả hotword, không trả đáp án hoặc expected concepts. Renderer truyền cấu hình qua IPC, main process kiểm tra giới hạn, rồi helper nhận `STT_HOTWORDS` JSON. Whisper-small desktop và Whisper server dùng tham số `hotwords`; Google Speech v1 dùng `speechContexts` với boost 10; Gemini nhận gợi ý từ vựng với chỉ dẫn không thêm từ không nghe thấy. Luồng chấm bài vẫn độc lập STT.

Hotword hỗ trợ nhận dạng, không tự sửa đáp án hoặc bảo đảm chính xác. Ưu tiên bảng từ vựng ngắn, sát môn; không nhập đáp án. Thuật ngữ tiếng Anh do AI sinh cho từng câu vẫn để giảng viên review, **không tự lấy expected concepts hoặc đáp án làm gợi ý STT**. Giảng viên đối chiếu transcript với audio/video minh chứng đã upload.

Tham khảo triển khai: [faster-whisper hotwords](https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/transcribe.py), [Google SpeechContext](https://github.com/googleapis/googleapis/blob/master/google/cloud/speech/v1/cloud_speech.proto).

## Module và triển khai

- `exam_generation.py`: dựng snapshot từ blueprint và RAG, không tự publish/commit.
- `examination.py`, `examination_schemas.py`: phân công, duyệt, lịch, roster, chấm tay và xuất điểm.
- `excel.py`: đọc XLSX có giới hạn, kiểm tra dữ liệu, tạo template/export.
- `worker.finalize`: tính điểm AI, áp dụng ngưỡng dưới 5, giữ riêng điểm chấm lại.
- `examination.tsx`, `exam-draft-review.tsx`, `course-hotwords.tsx`: UI điều phối và review tách khỏi component quản trị lớn.

Mọi đề tạo qua Điều phối hoặc chuyển qua **Sinh câu hỏi & rubric để review** có `workflow=true` và phải qua quy trình duyệt. Đề do TEACHER tạo cũng dùng workflow. Với `workflow=false`, ADMIN có thể publish/giao đề trực tiếp và cấp quyền qua đăng ký môn. Server kiểm tra `workflow` tại các endpoint publish/assign để bảo đảm đề khảo thí đi qua đầy đủ bước duyệt.

Khởi động server bằng `docker compose up -d --build --wait`; service migrate chạy `alembic upgrade head`. Nếu chạy thủ công: cài dependency từ `services/api/requirements.lock`, chạy `alembic upgrade head` trong `services/api`, rồi khởi động API/worker/web. Quy trình triển khai bao gồm sao lưu database và dữ liệu lưu trữ.

## Đợt thi theo lớp (migration 0010)

Ngoài kỳ thi độc lập, admin/khảo thí tạo lớp theo môn, phân công giáo viên, nhập danh sách rồi tạo đợt từ đề đã công bố. Đợt thi của lớp không xuất hiện trong danh sách Điều phối kỳ thi; quản lý tại **Lớp học → Đợt thi & kết quả**. Mỗi đợt giữ snapshot đề, roster và lịch riêng; giáo viên chỉ xem/chấm lớp được phân công. [Chi tiết](academic-classes.md).


## Danh sách thí sinh và xem bài — 25/10/2026

Thẻ kỳ thi có `participant_count` và `sitting_count`, truy vấn tổng hợp theo
các kỳ thi thuộc phạm vi người dùng. Nút Danh sách thí sinh mở trực tiếp tab
Sinh viên & lịch thi; có tìm kiếm tên/MSSV/email, cột Số lượt thi, bộ lọc đã
nộp bài và các nút Xem bài lần N. Chỉ đếm phiên chưa xóa, khác DEVICE_CHECK.
Roster tự cập nhật 10 giây khi đang hiển thị; xem bài dùng ReviewPage chia
tab và quay lại giữ bộ lọc. [Chi tiết](review-diagnostics.md).
