# Hướng dẫn sử dụng OralAI

## Xem bài theo tab và tra log (25/10/2026)

Trong **Kết quả & xem lại**, mở bài của sinh viên rồi chọn **Tổng quan &
điểm**, **Câu trả lời** hoặc **Màn hình & giám sát**. Tab Câu trả lời cho
chọn từng câu; mở **Nhận dạng, chấm lại AI & lịch sử** để dùng chức năng
chấm lại hiện có. Chuyển tab/câu sẽ dừng audio/video đang xem.

Trong **Điều phối kỳ thi**, bấm **Danh sách thí sinh** trên thẻ kỳ thi để
xem người được giao thi, số lượt thi và trạng thái từng lượt. Tìm theo
MSSV/tên/email; bấm **Xem bài lần N** để mở đúng lượt. Số lượt không tính
phiên kiểm tra thiết bị hoặc lượt đã xóa. Danh sách tự cập nhật 10 giây.

Admin vào **Log hệ thống** để lọc nguồn API/WEB/AI/WORKER, mức log, model
và mã request/tác vụ/lượt thi. Bấm dòng log để mở chi tiết; bật làm mới tự
động khi theo dõi chấm bài. **Log xử lý** trong bài thi tự điền mã lượt
đó. Mặc định xem 24 giờ; chọn 7 ngày khi tra bài cũ. Chưa có log có thể do
bài xử lý trước khi triển khai hoặc log đã hết hạn (7 ngày/10.000 sự kiện).
[Phạm vi dữ liệu và vận hành log](architecture/review-diagnostics.md).


Bấm tên menu bên trái để quay về trang gốc của mục đó. Thao tác này có hiệu lực cả khi menu đang được chọn và bạn đang xem chi tiết bên trong; các lựa chọn/bộ lọc cục bộ được đặt lại.

## Cấp nhiều vai trò

Admin vào **Người dùng**, mở **Vai trò**, tích các vai trò và bấm **Lưu quyền**.
Khi tạo tài khoản mới cũng chọn được nhiều vai trò. Phải giữ ít nhất một vai
trò cho tài khoản và một admin đang hoạt động trong hệ thống. Bộ lọc tìm
trên tất cả vai trò của tài khoản.

Quyền được cộng gộp: TEACHER + EXAM_OFFICER có quyền soạn đề và điều phối;
STUDENT + TEACHER quản lý trên web và làm bài được giao trên desktop. ADMIN
có mọi quyền; vẫn cần được giao bài và đủ điều kiện thi.
[Chi tiết](architecture/multi-role-access.md).

## Hồ sơ người dùng và quy định desktop

Vào **Người dùng → Chi tiết** để xem profile và danh sách lớp. Lọc **Đã học / Đang học / Sẽ học** theo lịch lớp; bấm **Chi tiết lớp** để xem các đợt thi. Đợt chưa có lượt hiển thị **Chưa thi**; đợt đã làm có từng lượt và **Chi tiết bài thi** để mở transcript, minh chứng, điểm và chấm lại theo quyền. Lớp đã rời vẫn giữ lịch sử thi. Giáo viên chỉ thấy lớp trong phạm vi được phân công. Nút **Quản lý môn học được giao** mở phần đăng ký môn cũ.

Chỉ admin có **Cấu hình hệ thống → Quy định desktop**. Có 10 công tắc độc lập: ghi màn hình, camera, một màn hình, kiosk, phím tắt, clipboard, điều hướng, tải xuống, tạm dừng khi rời cửa sổ và DevTools. Sau khi lưu, quy định áp dụng cho lượt tạo mới; lượt đã tạo giữ nguyên. Desktop hiển thị mô tả ở trang đăng nhập, danh sách bài và trong từng lượt thi. Tắt camera cho phép thi bằng audio; microphone vẫn bắt buộc. Cần desktop mới cùng migration `0011`. [Bảng quy định, phân quyền và giới hạn](architecture/user-profiles-desktop-policy.md).

## Câu hỏi có định dạng và hình ảnh

Trong ngân hàng đề hoặc phần review của Điều phối kỳ thi, bấm **Sửa câu N**
để mở editor riêng. Dùng thanh công cụ định dạng chữ, danh sách và **Chèn
ảnh**. **Xong câu** là xem trước; bấm **Lưu nội dung đã review** để lưu lên
server. Admin, khảo thí và giảng viên được sửa bản GENERATED theo phạm vi
quyền. Với đề đã duyệt/công bố, **Sao chép thành bản nháp** giữ nội dung và
ảnh để sửa, sau đó duyệt lại. [Giới hạn ảnh và hướng dẫn](architecture/question-editor-recording.md).

**Tổng quan → Lượt thi gần đây → Xem bài** mở đúng bài của sinh viên ở hàng
đã chọn; có thể đổi lượt trong lịch sử của sinh viên đó.

## Quy trình khảo thí

Bắt đầu tại [hướng dẫn khảo thí → giảng viên → sinh viên](architecture/examination-workflow.md). Tải [Excel mẫu](templates/danh-sach-sinh-vien.xlsx). Admin duyệt role khảo thí và cấp role giảng viên; khảo thí giao môn, nhập danh sách, kiểm tra đề đã được giảng viên duyệt, xếp lịch từng sinh viên rồi mở thi. Bài AI dưới 5 được đánh dấu để giảng viên chấm lại; khảo thí xuất điểm chính thức trong Điều phối kỳ thi.


[README / danh mục tài liệu](../README.md#hướng-dẫn-theo-nhu-cầu) · [Desktop](../readme-desktop.md) · [Cập nhật qua Jenkins](jenkins.md)

Admin, khảo thí và giảng viên quản lý trên web; sinh viên dùng desktop ghi và nộp bài lên server. Server thực hiện STT và chấm điểm.

## Chuẩn bị và đăng nhập

- Dùng địa chỉ web do người vận hành cung cấp. Khi chạy Docker mặc định trên máy cá nhân, địa chỉ là `http://localhost:3000`.
- Admin ban đầu đăng nhập bằng `BOOTSTRAP_ADMIN` và `BOOTSTRAP_PASSWORD` đã cấu hình cho server. Admin có thể tạo tài khoản ở **Người dùng** và phân vai trò phù hợp.
- Học viên dùng tài khoản được cấp hoặc đăng nhập Google nếu server đã bật chức năng này.
- Server phải hoạt động để đăng nhập, lấy đề và nộp bài. Desktop chỉ hiển thị xác nhận nộp; admin, khảo thí và giáo viên có quyền xem kết quả trên web. STT local không đồng nghĩa làm bài hoàn toàn offline.

## Admin và giảng viên chuẩn bị bài thi

### 1. Tạo môn và chuẩn bị kiến thức

1. Vào **Môn học → Tạo môn học**, nhập mã, tên và mô tả rồi lưu.
2. Mở môn vừa tạo, chọn **01 · Kiến thức → Giáo trình**. Tải PDF và chờ xử lý thành **Sẵn sàng** (`READY`). Kiểm tra mục lục; sửa tên chương và khoảng trang nếu cần.
3. Trong **Chuẩn đầu ra**, tạo các LO mô tả kiến thức/kỹ năng cần đánh giá.
4. Trong **Chủ đề**, tạo chủ đề, chọn ít nhất một LO và một chương/mục giáo trình. Có thể bổ sung mô tả và tài liệu liên quan.
5. Nếu cần, tải thêm tài liệu tại **Tài liệu bổ sung**. Dùng **Tra cứu kiến thức** để kiểm tra nội dung được truy xuất trước khi sinh đề.

Tài liệu phải ở trạng thái `READY` và dùng cấu hình embedding hiện tại để công bố đề. Nếu nút tạo bài thi chưa bật, kiểm tra môn còn hoạt động và đã có chủ đề/rubric.

### 2. Tạo rubric và bản nháp đề

1. Mở **02 · Rubric**, tạo rubric gồm tiêu chí, mô tả, điểm tối đa và trọng số; bấm **Lưu rubric**.
2. Mở **Ngân hàng đề thi → chọn môn → Tạo bài thi**.
3. Nhập tên, thời gian, chọn rubric và phân bổ câu hỏi theo chủ đề, độ khó, số lượng. Bấm **Lưu bản nháp**.
4. Kiểm tra lại bản nháp. Admin có thể đặt **Cấu hình số lần làm lại**: không cho làm lại, cho thêm N lần hoặc không giới hạn.
5. Bấm **Sinh câu hỏi & rubric để review**, sửa câu hỏi/ý chính/rubric và lưu, rồi **Duyệt đề & gửi khảo thí**. Khảo thí kiểm tra, nhập danh sách, xếp lịch và mở kỳ thi.

Chế độ `AI_PROVIDER=demo` chỉ thử quy trình, không chấm điểm thật và không sinh gợi ý thuật ngữ. Người vận hành cấu hình Gemini/Ollama trên server theo [README](../README.md#chọn-llm-qua-env).

### 3. Xem câu hỏi và thuật ngữ tiếng Anh

Sau khi công bố, ngay dưới đề xuất hiện **Câu hỏi & thuật ngữ tiếng Anh gợi ý**. Mỗi câu hiển thị nội dung câu hỏi và các cặp thuật ngữ/nghĩa tiếng Việt, ví dụ `unit test: kiểm thử đơn vị`.

- AI gợi ý tối đa 20 thuật ngữ mỗi câu; giảng viên cần kiểm tra cách viết và nghĩa.
- Gợi ý được lưu cùng phiên bản đề và hiển thị trong trang quản lý. Học viên không nhận danh sách này qua màn hình câu hỏi.
- Đề cũ, đề demo hoặc câu không có thuật ngữ phù hợp có thể hiển thị **Chưa có gợi ý thuật ngữ cho câu hỏi này**.
- Hiện chưa có thao tác sửa trực tiếp danh sách thuật ngữ. Để sinh lại câu hỏi/gợi ý, chọn **Sao chép thành bản nháp**, điều chỉnh bản nháp và công bố lại; bản đề mới có thể có câu hỏi khác.
- Hotword STT lưu riêng tại **Ngân hàng đề thi → chọn môn → Hotword STT của môn học**, áp dụng cho desktop/server khi làm bài của môn đó. Mỗi dòng một thuật ngữ; tối đa 500 mục, 100 ký tự/mục, tổng 10.000 ký tự sau khi bỏ dòng trống/mục trùng. Bấm **Lưu hotword môn học**, kiểm tra thông báo tên môn và số mục đã lưu. Đề giữ hotword lúc sinh; sau khi sửa danh sách, cần sinh đề mới hoặc trả đề về nháp rồi sinh/duyệt lại để áp dụng. Danh sách thuật ngữ AI không tự trở thành hotword. Giảng viên đối chiếu transcript với bản ghi khi xem bài.

Đề đã công bố giữ nguyên nội dung để đối chiếu kết quả. Kỳ thi mới bắt buộc giảng viên và khảo thí duyệt trước; chỉ sinh viên trong roster thấy kỳ thi và chỉ bắt đầu trong lịch được xếp.

### 4. Giao bài

| Cách giao | Thao tác | Phạm vi |
| --- | --- | --- |
| Giao cả môn, dành cho admin | **04 · Học viên → chọn tài khoản → Thêm vào môn học** | Học viên thấy các đề đã công bố và đề công bố sau này trong môn |
| Giao riêng một đề | Mở đề đã công bố → **Giao riêng đề này cho học viên** → chọn người → **Giao bài cho sinh viên đã chọn** | Chỉ giao đề đã chọn |

Học viên bấm **Làm mới bài thi** nếu danh sách chưa cập nhật. **Bỏ khỏi môn** không xóa lịch sử thi hoặc thu hồi đề đã giao riêng.

Hai cách giao trong bảng trên chỉ áp dụng đề legacy. Kỳ thi mới dùng danh sách Excel trong **Điều phối kỳ thi**; đăng ký môn không cấp quyền thi tự động.

## Bộ môn, lớp học và đợt thi

1. Admin/khảo thí mở **Bộ môn → Tạo bộ môn**, nhập mã/tên. Trong **Gắn môn học vào bộ môn**, chọn môn và bộ môn rồi lưu.
2. Mở **Lớp học → Tạo lớp học**, đặt mã/tên, chọn một môn, giáo viên phụ trách và ngày giờ bắt đầu/kết thúc. Có thể phân công sau bằng **Sửa** hoặc **Nhập phân công giáo viên theo lớp**; tải mẫu `class_code`, `teacher_username` ngay trên trang. Giáo viên phải có tài khoản TEACHER đang hoạt động.
3. **Mở lớp → Sinh viên**: chọn nhiều tài khoản có sẵn hoặc nhập Excel theo mẫu của lớp. Danh sách hiển thị MSSV, tên và email; admin/khảo thí có thể gỡ thành viên.
4. Chuẩn bị đề trong **Ngân hàng đề thi → chọn môn**. Mở phần **Category** của đề để đặt nhãn như Giữa kỳ/Cuối kỳ; dùng bộ lọc category và rubric. Giảng viên/admin sinh và duyệt bản nháp; khảo thí/admin bấm **Duyệt vào ngân hàng đề** để công bố đề nguồn không cần roster. Đề nguồn không được giao tự động cho sinh viên; sau đó chọn đề vào đợt của lớp.
5. **Lớp học → Mở lớp → Đợt thi & kết quả → Tạo đợt thi từ ngân hàng đề**: đặt tên đợt, chọn đề cùng môn, giờ mở/đóng nằm trong thời gian lớp và đủ thời lượng bài. Chốt danh sách sinh viên trước bước này.
6. Chọn đợt thi để xem người chưa thi, tất cả lượt đã làm, trạng thái và điểm. **Xem bài / chấm lại** mở transcript, minh chứng và biểu mẫu chấm lại cho admin/giáo viên được phân công; khảo thí có quyền xem. Điểm thủ công cần lý do và có lịch sử audit.

Giáo viên mở **Lớp được phân công**; không có nút tạo/sửa/xóa lớp, quản lý bộ môn hoặc thay đổi roster. Phân công lớp không thay giáo viên chủ sở hữu môn. Dữ liệu của lớp khác vẫn bị chặn ở API.

Mỗi đợt là bản sao đề và danh sách riêng. Thêm/gỡ sinh viên khỏi lớp sau khi tạo đợt không thay đổi roster cũ; muốn dùng danh sách/lịch khác, tạo đợt mới. Xóa lớp chỉ áp dụng lớp chưa có đợt thi; xóa bộ môn chỉ áp dụng khi không còn môn trực thuộc. [Mô hình dữ liệu, Excel và nâng cấp](architecture/academic-classes.md).

## Danh sách người dùng

Trang **Người dùng** hiển thị bảng thu gọn. Dùng ô tìm tên/email/tên đăng nhập và bộ lọc vai trò để giảm số dòng; admin đổi vai trò và lưu trực tiếp trong hàng của tài khoản. Nhập Excel giảng viên/khảo thí nằm trong các khối có thể mở/thu gọn.

## Học viên làm bài trên desktop

1. Mở OralAI, chọn **Cấu hình máy chủ** tại màn hình đăng nhập. Dùng tài khoản được cấp hoặc Google đúng email trong danh sách thi.
2. Chọn bài, bấm **Mở bài thi → Cho phép camera & mic** và chọn đúng thiết bị.
3. Kiểm tra âm thanh và camera; ngôn ngữ nhận dạng của bài thi được cấu hình trên server.
4. Chuẩn bị một màn hình, đồng ý ghi toàn màn hình, bấm **Bắt đầu thi** và cấp quyền chia sẻ.
5. Đọc câu hỏi trong N giây chuẩn bị (mặc định 10). Hết đếm ngược app tự ghi trong tối đa M giây (mặc định 60); có thể bấm **Kết thúc trả lời** sớm.
6. App tự tải bản ghi rồi chuyển câu. N/M được giảng viên cấu hình riêng trong Review câu hỏi & rubric trước khi duyệt đề.
7. Câu cuối tự nộp toàn bài sau khi tải đủ minh chứng; nếu tải lỗi, thử tải lại và nộp. Chờ xác nhận đã nộp rồi có thể đóng app.

Desktop hiển thị câu hỏi, hướng dẫn và xác nhận nộp bài. Điểm và trạng thái chấm chỉ có trên web cho nhân sự có quyền. [Transcript và review](transcript-correction.md), [microphone](microphone-desktop.md), [ghi màn hình và chế độ thi](../readme-desktop.md#truy-cập-và-ghi-màn-hình-bắt-buộc).

Đã bỏ Học & thi thử trên web và desktop.

## Xem kết quả và làm lại

Trên web dành cho admin, khảo thí và giáo viên có quyền, **Điểm tổng** là trung bình cộng điểm tất cả câu hỏi,
làm tròn đến 2 chữ số thập phân trên thang 10. Ví dụ: `(6 + 8 + 10) / 3 = 8/10`.
Bảng bên dưới hiển thị điểm từng câu và phép tính. Điểm 0 vẫn được tính; câu chưa
chấm hoặc chấm lỗi không được thay bằng 0 và bài chưa có điểm tổng cho đến khi đủ
điểm các câu. Chấm lại câu hỏi sẽ cập nhật điểm tổng theo kết quả mới.

Với bài đang chờ duyệt, điểm tổng được ghi là tạm tính. **Điểm chính thức** vẫn theo
quy trình duyệt; nếu giảng viên đã chấm lại toàn bài, điểm chính thức có thể khác
trung bình do AI đề xuất. Bài luyện tập không tính điểm không hiển thị điểm tổng.
Tính năng cần cập nhật cả API/worker và giao diện trên server sử dụng.

- Admin/khảo thí/giảng viên mở **Kết quả & xem lại**, chọn môn để thấy lần gần nhất, có thể lọc thêm đề/ngày để xem transcript, audio/video, đánh giá và tài liệu dẫn chứng.
- **Chưa có độ tin cậy AI** có thể xuất hiện khi chưa chấm, chấm lỗi hoặc dùng demo. Confidence do AI tự báo không phải bảo đảm độ chính xác.
- Admin dùng **Quản lý lượt thi → Cấp thêm lượt** khi cần cho một học viên thi lại. Học viên làm mới danh sách rồi chọn **Làm lại bài thi** nếu còn lượt; **Xem lần N** mở xác nhận nộp bài cũ, không hiển thị điểm.
- Nhận dạng lại audio và chấm lại transcript là hai thao tác riêng, đều có lịch sử. Xem [lượt thi](architecture/exam-retakes.md) và [chấm lại](architecture/grading-confidence.md).

## Lưu trữ hoặc xóa môn học

**Lưu trữ môn học** phù hợp khi muốn ngừng tạo bài mới và giữ dữ liệu lịch sử. Trong môn, vào **Cài đặt → Lưu trữ môn học**; dùng **Khôi phục môn học** để mở lại.

Để xóa toàn bộ môn học bằng tài khoản admin:

1. Vào **Môn học → chọn môn → Cài đặt → Xóa môn học**.
2. Đọc tên môn và phạm vi dữ liệu trong hộp thoại **Xóa toàn bộ môn học**.
3. Nhập đúng mã môn đang hiển thị, rồi bấm **Xóa vĩnh viễn môn học và dữ liệu**.

Thao tác không hoàn tác được: xóa tài liệu, chủ đề, LO, rubric, đề thi, danh sách thành viên môn, lượt thi (kể cả bài đang làm), kết quả và bản ghi. Tài khoản người dùng và môn khác vẫn còn. Tệp được worker dọn sau khi dữ liệu được xóa; lỗi storage sẽ được thử lại. Nếu báo **Môn học đang được xử lý**, chờ tác vụ hoàn tất rồi thử lại.

Giảng viên chỉ xóa được môn trống mình phụ trách. Xóa riêng một lần thi tại **Kết quả & xem lại** khác với xóa toàn bộ môn học.

## Quản lý lần thi và dung lượng

Admin mở **Lần thi & dung lượng** để xem dung lượng từng lần thi, tổng theo môn/người làm bài, file đang tải và file chờ worker xóa. Lọc theo môn, người làm bài hoặc ngày tạo trước mốc đã chọn; **Xuất báo cáo dung lượng Excel** xuất đúng bộ lọc, tối đa 10.000 lần thi. Bảng theo người hiển thị tối đa 100 người; chọn một người trong bộ lọc để xem riêng.

1. Chọn các lần thi đã kết thúc, từng dòng hoặc cả trang. Có thể chọn qua nhiều trang, tối đa 500 lần/lượt; đổi bộ lọc sẽ xóa lựa chọn cũ.
2. Mặc định **Chỉ xóa bản ghi, giữ điểm và lịch sử**: xóa audio, camera, màn hình; giữ transcript, điểm, lịch sử chấm và số lượt đã sử dụng. Sau đó không thể phát hoặc nhận dạng lại những file này.
3. Nếu cần, chọn **Xóa toàn bộ dữ liệu lần thi đã chọn**: xóa cả câu trả lời, điểm và lịch sử chấm. Giữ môn, đề, tài khoản và dấu vết kiểm toán tối thiểu. Lần thi bị xóa không còn tính vào số lượt đã dùng.
4. Bấm **Xem trước dữ liệu sẽ xóa**, kiểm tra số lần thi/file/dung lượng, nhập lý do và chuỗi xác nhận, rồi xác nhận xóa. Không thể hoàn tác.

Server chặn bài đang thi/đang chấm lại, kiểm tra lại phạm vi khi xác nhận và yêu cầu xem trước lại nếu dữ liệu thay đổi. Bản xem trước hết hạn sau 10 phút. Việc xóa file chạy qua worker, có tự thử lại khi kho lưu trữ lỗi; bấm **Làm mới dung lượng** để xem số file chờ xóa.

Dung lượng báo cáo là kích thước bản ghi được hệ thống quản lý, không phải tổng dung lượng database, tài liệu học, bản sao lưu hoặc hóa đơn S3. Số liệu file tạm, kho local và ổ đĩa là toàn hệ thống, không theo bộ lọc. Với S3, dung lượng trống hiển thị là ổ đĩa API. Nếu bucket bật versioning/retention, các phiên bản cũ vẫn có thể chiếm dung lượng sau khi xóa đối tượng; cần quản lý vòng đời các phiên bản tại kho lưu trữ.

## Nhập Excel môn học, rubric, bài thi và nhân sự

Mỗi khu vực có mục **Nhập … từ Excel**, nút **Tải mẫu Excel**, chọn file, **Kiểm tra file** và nút nhập sau khi kiểm tra thành công:

| Dữ liệu | Nơi tải mẫu và nhập | Quy tắc |
| --- | --- | --- |
| Môn học | Môn học | Một dòng/môn; có thể chỉ định email giảng viên phụ trách đã tồn tại. Giáo viên chỉ tạo môn của mình. |
| Rubric | Chọn môn → Rubric | Một dòng/tiêu chí; nhóm theo mã môn và tên rubric. `max_score` và `weight` là số dương. |
| Bài thi | Ngân hàng đề thi → chọn môn, hoặc Điều phối kỳ thi | Một dòng/câu hỏi có sẵn, nhóm theo mã môn và tên đề. |
| Giảng viên | Người dùng (admin) | Tài khoản mới có vai trò TEACHER. |
| Khảo thí | Người dùng (admin) | Tài khoản mới có vai trò EXAM_OFFICER. |

Nhập theo thứ tự giảng viên → môn → chuẩn bị chủ đề/tài liệu → rubric → bài thi. Với mẫu tải trong một môn, mã môn và danh mục rubric/chủ đề được điền theo môn đó. Sửa sheet **Data**, giữ nguyên tên/thứ tự cột; sheet **Huong dan** giải thích định dạng. Thay hoặc xóa các dòng mẫu vì chúng được coi là dữ liệu cần nhập.

Mẫu bài thi **chỉ nhập câu hỏi đã soạn**. `question_number` liên tiếp từ 1 (tối đa 20); `topic_name` và `rubric_name` phải tồn tại duy nhất trong môn; `difficulty` là EASY/MEDIUM/HARD; `time_minutes` là số nguyên 1–180. Các dòng cùng đề phải cùng rubric và thời lượng. `expected_concepts` ngăn cách bằng dấu `;`; `english_terms` tùy chọn theo dạng `term=meaning;term=meaning`. Đây là thuật ngữ của câu hỏi; bảng hotword STT vẫn quản lý riêng trong môn.

Đề nhập được lưu **DRAFT**, chưa mở thi. Chuẩn bị tài liệu READY đúng chủ đề, bấm **Tạo bản nháp từ câu hỏi đã nhập** để gắn nguồn tài liệu, rồi review/duyệt qua Điều phối kỳ thi. Hệ thống giữ nguyên câu hỏi và rubric đã nhập, không gọi AI sinh lại chúng. Có thể sửa nội dung trong bản nháp review; muốn đổi phân bổ chủ đề/số câu, nhập đề mới.

File tối đa 2 MB, 1.000 dòng (nhân sự: 200), không có công thức. Lỗi được báo theo dòng; có lỗi thì không nhập dòng nào. Môn/rubric/tài khoản giống dữ liệu đã có được bỏ qua; trùng khóa nhưng khác nội dung báo lỗi. Tên đề đã tồn tại cũng báo lỗi, cần đổi tên để tạo đề mới. Import không đổi vai trò hoặc mật khẩu tài khoản đã có. Tài khoản nhân sự mới cần mật khẩu ban đầu riêng 12–128 ký tự; phân phối qua kênh của đơn vị.

## Khi chưa thấy chức năng mới

Giao diện quản lý và API cần cùng được cập nhật. Với server Docker local, xem [cập nhật server](../README.md#build-cập-nhật-và-tài-liệu). Với server Jenkins, xem [hướng dẫn cập nhật](jenkins.md). Sau khi server cập nhật thành công, mở lại desktop. Thay đổi Electron/preload cần chạy source mới hoặc cài bộ desktop mới.


## Quyền truy cập và môn học của sinh viên

Web chỉ cho **ADMIN, EXAM_OFFICER và TEACHER** truy cập. Sinh viên dùng OralAI Desktop.

Trong **Người dùng**, bấm tên sinh viên để mở chi tiết và danh sách môn. Admin/khảo thí chọn môn rồi bấm **Thêm môn**, hoặc **Gỡ môn** để thu hồi cả đăng ký môn và các đề/lịch thi đã giao trong môn. Thao tác gỡ giữ nguyên bài làm, điểm và minh chứng; bị chặn khi sinh viên còn phiên đang mở hoặc đang làm. Với kỳ thi theo lịch, thêm môn không thay cho bước đưa sinh viên vào roster và xếp lịch. Giáo viên chỉ xem các môn mình phụ trách tại màn hình này.

## Xem bản ghi màn hình và sự kiện giám sát

Lần thi mới trên Desktop bắt buộc ghi toàn màn hình sau khi sinh viên đồng ý (bài thử thiết bị và phiên cũ trước migration không áp dụng). App chỉ hoàn tất nộp khi tải xong bằng chứng. Trong **Kết quả & xem lại → Xem bài**, mở các video có nhãn **Bản ghi màn hình bài thi** ở câu đầu tiên; các đoạn được sắp theo thứ tự tạo. Audio từng câu có nhãn riêng; bản mới không lưu video camera từng câu. Camera hiển thị trong video màn hình khi bật. Video camera cũ vẫn xem được. Giáo viên chỉ xem bằng chứng môn mình phụ trách; admin/khảo thí xem theo quyền quản lý.

Mục **Sự kiện giám sát bài thi** ghi thời điểm server nhận các sự kiện như rời cửa sổ, thay màn hình, ngắt ghi hoặc khởi động lại. Bài có sự kiện cần giảng viên xem lại trước khi công bố điểm. Đối chiếu bản ghi và hoàn cảnh thực tế trước khi chấm lại, không coi một sự kiện là bằng chứng chắc chắn của gian lận. Độ trễ mạng có thể làm thời điểm nhận sự kiện khác thời điểm xảy ra.

Bản ghi dùng cơ chế lưu trữ, phân quyền và xóa cùng bài thi hiện có; bản này chưa bổ sung tự động xóa theo thời hạn. Hạn chế kỹ thuật và yêu cầu cập nhật server/desktop được ghi trong [hướng dẫn desktop](../readme-desktop.md#truy-cập-và-ghi-màn-hình-bắt-buộc).
