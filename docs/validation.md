# Kiểm thử OralAI

[README](../README.md#hướng-dẫn-theo-nhu-cầu) · [Build desktop](desktop-build.md)

## AI không quota CPU/RAM, vẫn chấm tuần tự — 26/10/2026

- **27 ca API đạt, 1 bỏ qua trên SQLite:** chấm local với luồng tự động hoặc
  cấu hình riêng, Ollama không nhận `num_thread` khi auto, Whisper nhận
  `cpu_threads=0` nhưng chỉ một inference worker; hồi quy lỗi và khóa worker.
- **4 ca worker đạt trên PostgreSQL thật**, gồm ca đã bỏ qua ở SQLite:
  database tạm qua `pgserver`, bật extension vector trước khi tạo schema;
  một kết nối giữ advisory lock thì worker khác không gọi xử lý. Không dùng
  database production. Khóa nhả sau tác vụ/lỗi vẫn được kiểm tra.
- **18 ca GOPT đạt:** khởi tạo engine không ép luồng PyTorch, chặn request
  đồng thời, nhả khóa sau lỗi, timeout tiến trình, audio/đặc trưng/assets.
  Model được giả lập; `kaldiio` cài vào thư mục tạm, không tải trọng số.
- **9 ca deploy đạt:** Compose thật với bốn tổ hợp overlay; không còn quota
  CPU/RAM/swap/PID, credential cũ không khôi phục hạn mức, worker luôn tuần
  tự và lệnh khởi chạy gỡ biến OMP/BLAS/MKL/NumExpr cũ.
- Ruff và `git diff --check` đạt. Chưa build image GOPT mới hoặc xác nhận
  container đang chạy trên Jenkins; cần build lại GOPT để nhận code engine.

## RAM worker/GOPT và chấm tuần tự — 26/10/2026

- **9 ca deploy đạt:** Compose thật xác nhận worker/GOPT có RAM và RAM+swap
  4 GiB, CPU 3, `WORKER_SERIAL=true` trong các tổ hợp overlay.
- **3 ca worker đạt, 1 bỏ qua:** khóa chống chạy đồng thời, nhả khóa khi lỗi
  và đường đi khóa PostgreSQL bằng giả lập; ca khóa PostgreSQL thật bỏ qua
  vì môi trường hiện dùng SQLite.
- **6 ca GOPT HTTP đạt:** chặn request đồng thời, healthcheck vẫn đáp ứng,
  nhả khóa sau lỗi và giới hạn upload. Engine được giả lập, không tải model.
  Cài `kaldiio==2.18.1` vào thư mục tạm cho test, không thay môi trường dự án.
- Ruff đạt; chưa xác minh credential Jenkins/container production.

## CPU AI local — 26/10/2026

- **23 ca API đạt:** chấm lại local với 1/3 luồng Ollama, không gọi cloud,
  giữ audio/đánh giá cũ khi lỗi; hồi quy log AI.
- **9 ca deploy đạt:** Compose thật với bốn tổ hợp overlay; CPU mặc định 3,
  RAM giữ nguyên, số luồng đúng cho API/worker/GOPT và credential ghi đè
  vẫn được giữ khi gộp hai overlay. Ruff đạt.
- AI/HTTP được giả lập trong test API; chưa benchmark trên server thật,
  chưa xác nhận cập nhật credential hoặc CPU container đang chạy.

## Tối ưu Jenkins — 26/10/2026

- **25 ca đạt:** 12 ca cleanup, 5 ca build/reuse MinIO, 8 ca deploy; kiểm tra
  Compose thật với bốn tổ hợp bật/tắt Ollama/GOPT. Ruff đạt cho Python thay đổi.
- Cleanup vẫn bảo vệ project khác, image đang chạy, bản trước và tình huống
  tranh chấp/xóa lỗi; xác minh dọn có giới hạn trên Buildx mới/cũ, không quay
  về xóa toàn bộ cache khi thiếu hỗ trợ.
- MinIO kiểm tra image khớp/thiếu nhãn/thiếu image, đổi nội dung/tên/thêm file,
  lỗi build và kiểm tra binary; tag khớp Compose. Lệnh Docker dùng giả lập.
- Log thời gian deploy không lộ command/output riêng tư. Chưa chạy pipeline
  Jenkins thật hoặc benchmark build có cache; không khẳng định mức giảm phút.

## Log lỗi phát âm — 25/10/2026

- **48 ca đạt**: `test_pronunciation.py`, `test_local_audio_review.py`,
  `test_ai_diagnostics.py`, `test_diagnostic_logs.py`; Ruff đạt.
- Kiểm thử đi qua endpoint yêu cầu chấm lại, worker, kho log và endpoint
  admin đọc log. Xác minh lỗi GOPT tắt, sai ngôn ngữ, timeout, mất kết nối,
  HTTP 422/429/503 xuất hiện khi lọc AI / ERROR / model / mã tác vụ.
- Kiểm tra thông báo cụ thể, giữ điểm cũ, không lưu transcript/response/
  exception thô. Kiểm tra thiếu audio, quá dung lượng, checksum, transcript
  rỗng và kết quả sai schema; các ca chấm thành công vẫn đạt.
- Model/HTTP được giả lập, database tạm; chưa kiểm tra tác vụ người dùng
  trên server hoặc xác nhận triển khai domain chính.

## Xem bài theo tab, log hệ thống và danh sách thí sinh — 25/10/2026

| Nhóm | Kết quả |
| --- | --- |
| API SQLite toàn bộ | **226 đạt, 10 bỏ qua** theo điều kiện môi trường của suite |
| Playwright Chromium | **26 đạt** trong lượt chạy cuối |
| Node API retry / proxy | **6 đạt** |
| Kiểm tra tĩnh và build | Ruff, ESLint, TypeScript và Next production build đạt |

API kiểm tra quyền admin với log, chặn người chưa đăng nhập và các vai trò
khác; lọc/pagination/correlation, giới hạn 7 ngày/10.000 sự kiện, rate limit
WEB, chuẩn hóa route và loại bỏ dữ liệu nhạy cảm. Có ca chạy hàng đợi STT →
chấm và đối chiếu log API/worker/AI bằng ID lượt thi; kho log lỗi không làm
hỏng API nghiệp vụ. Tổng lượt thi loại phiên kiểm tra thiết bị/lượt đã xóa,
đếm nhiều lượt và giữ phạm vi quyền.

Giao diện kiểm tra các tab, chỉ dựng một câu trả lời, dừng media khi chuyển
tab, mở log theo lượt thi, quyền nhiều vai trò, lọc/phân trang log và báo lỗi
JavaScript chỉ gửi metadata. Kiểm tra roster tìm sinh viên, mở thẳng danh
sách từ thẻ kỳ thi, mở đúng bài, quay lại giữ bộ lọc; hồi quy chấm lại cloud,
điểm/rubric, retake và hồ sơ sinh viên. Đã kiểm tra ảnh giao diện câu trả lời,
log và điều phối; layout log/media ở 1440px/768px, điều phối ở 1440px/390px.

Kiểm thử dùng database tạm, API/AI giả lập ở các ca tương ứng, không gọi
model trả phí hoặc thay đổi dữ liệu production. Hai kỳ vọng UI cũ (payload
cấu hình STT và nhãn chọn sinh viên) đã được cập nhật theo hành vi hiện có.
Không cần migration mới; chưa xác nhận Jenkins/domain chính triển khai bản này.

## Editor câu hỏi, camera và audio từng câu — 22/10/2026

Kiểm thử local với database tạm; không thay đổi môn, đề hoặc bài làm trên
production. Không cần migration mới.

| Nhóm | Kết quả |
| --- | --- |
| API SQLite toàn bộ | **174 đạt, 9 bỏ qua**; sau đó bổ sung và kiểm tra riêng ca cấu trúc JSON sai kiểu |
| Playwright Chromium | **38 ca khác nhau đạt** qua các lượt kiểm tra; 8 ca editor/điều hướng/ghi âm theo giờ chạy lại cuối đều đạt |
| Electron thật từ source | Đạt tại 1024×640, 1280×680, 1366×700; camera giả lập có tỉ lệ khung khớp kích thước video và không cắt ảnh |
| Node screen recording/recovery | **8 đạt** |
| Kiểm tra tĩnh và build | Ruff, ESLint, TypeScript và Next production build đạt |

Backend xác minh ba vai trò được sửa trong phạm vi quyền, chặn sinh viên và
đề đã duyệt/công bố, giữ ảnh qua sao chép và lượt thi, không đổi đề nguồn,
chặn nội dung HTML/script/ảnh ngoài/ảnh quá giới hạn. Nộp bài cần audio mỗi
câu và SCREEN nếu bật; không cần VIDEO camera. Media cũ vẫn xem được.

Trình duyệt kiểm tra chèn ảnh, đậm, xem trước, hủy/lưu/tải lại, chỉ một câu
mở editor, layout 390px, mở đúng sinh viên/lượt thi ở tổng quan, recorder chỉ
thu audio, thử lại upload và khôi phục ghi màn hình. Đã xem ảnh chụp editor
và camera Electron. API và bridge trong kiểm thử UI được giả lập; media dùng
MediaRecorder với thiết bị giả. Chưa kiểm tra camera/microphone vật lý hoặc
bộ cài Windows mới; chưa xác nhận triển khai phiên bản này trên domain chính.

## Điều phối kỳ thi và nhiều vai trò — 21/10/2026

Kiểm thử trên server local, database tạm và API giả lập cho trình duyệt;
không thay đổi dữ liệu production.

| Nhóm | Kết quả |
| --- | --- |
| API SQLite | **163 đạt, 8 bỏ qua** |
| PostgreSQL: nhiều vai trò, tài khoản, lớp học | **19 đạt**, gồm hai admin đồng thời tự gỡ quyền, luôn còn một admin |
| Migration PostgreSQL | `0011 → 0012` đạt; tài khoản ADMIN cũ giữ quyền khi bảng grants mới trống |
| Playwright: lớp, điều phối, profile/policy, nhiều vai trò | **14 đạt**; chạy lại 6 ca điều phối/nhiều vai trò sau chỉnh CSS cuối, đều đạt |
| Kiểm tra tĩnh và build | Ruff, ESLint, TypeScript và Next production build đạt |

Đã kiểm tra ảnh và độ tràn ngang ở chiều rộng 1440px/390px; kiểm thử bộ lọc,
form tạo, hai tab chi tiết, chọn danh sách sinh viên và lưu nhiều vai trò.
Backend kiểm tra cộng gộp quyền, thu hồi quyền với token hiện có, chặn tự
nâng quyền, quyền admin, hồ sơ gồm cả lớp dạy/lớp học và migration. Chưa xác
nhận bản này trên domain chính; kiểm thử trình duyệt không thay thế kiểm
tra thiết bị desktop vật lý.

## Desktop gọn và bộ cài Windows nhẹ — 21/10/2026

Kiểm tra trên Windows 10 x64. Các phiên kiểm thử dùng profile cô lập, không
đăng nhập hoặc sửa dữ liệu bài thi production.

- **18/18 ca Node desktop đạt**, gồm ba ca trình tải model: revision cố định,
  SHA-256, dùng lại model khi offline, tệp sai checksum, lỗi mạng và thử lại.
- **Kiểm thử Electron bố cục đạt** tại 1024×640, 1280×680 và 1366×700: đăng
  nhập, kiểm tra thiết bị, câu hỏi, camera và nút thao tác. API được giả lập;
  đây không phải xác minh camera/microphone vật lý.
- **Kiểm thử đóng Electron/IPC đạt**: giữ/rời trang theo xác nhận và thoát thật.
- **Bản Windows nhẹ thật trên profile trống đạt**: màn hình thiết lập, tải
  khoảng 464 MiB từ Hugging Face, kiểm tra model, helper đóng gói nạp model,
  vào đăng nhập server online với CSS desktop và khởi động lại dùng model đã
  lưu. Lượt kiểm tra cuối hoàn tất trong khoảng 43 giây trên kết nối máy build;
  đây không phải cam kết tốc độ tải cho máy sinh viên.
- Build NSIS bản đầy đủ khoảng 639 MB (609 MiB), bản nhẹ khoảng 203 MB
  (194 MiB). Xác minh bản nhẹ không chứa thư mục trọng số model và metadata
  bật tải lần đầu; file bàn giao đã được đối chiếu SHA-256 với output build.
- Cú pháp Electron/trình tải, cú pháp script Python build và `git diff --check`
  đạt. Không có thay đổi web/API/worker hoặc migration trong bản desktop này.

Chưa kiểm tra bộ cài mới trên máy Windows sạch thứ hai, macOS/Linux hoặc ghi
và nộp một bài thi thật với thiết bị vật lý. Không coi việc helper nạp được
model là phép đo chất lượng nhận dạng. Lệnh tái kiểm tra nằm trong
[hướng dẫn build](desktop-build.md#kiểm-tra-trước-phát-hành).

## Hồ sơ người dùng và quy định desktop — 19/10/2026

Kiểm tra bằng database/container tạm và máy chủ web local. Không đổi cấu hình hoặc dữ liệu production.

| Nhóm | Kết quả |
| --- | --- |
| API PostgreSQL/pgvector | **167 đạt**, không bỏ qua; bổ sung phân quyền profile/lớp/lịch sử và policy/audit/snapshot/nộp audio-only |
| Migration | `0010 → 0011 → 0010 → 0011` đạt trên PostgreSQL và SQLite; bài kiểm tra nâng từ MVP giữ dữ liệu, điểm/transcript và NULL policy cũ đạt |
| Playwright Chromium | 24 ca đạt trong nhóm hồ sơ/policy, đăng ký môn, lớp học, thiết bị, screen và recovery; API/bridge giả lập, dùng MediaRecorder thật với thiết bị giả |
| Electron thật, source | Đạt kiểm thử IPC/cookie lấy policy, một màn hình/kiosk bật/tắt, phím F12 mở DevTools khi cho phép, đóng DevTools khi hết quyền và luồng xác nhận thoát |
| Node | 18 ca desktop và 8 ca screen đạt |
| ESLint, TypeScript, Next production build, Ruff và cú pháp Electron | Đạt |

Kiểm thử UI mới xác nhận profile → lọc lớp → đợt chưa thi/đã thi → ReviewPage, admin lưu độc lập các công tắc, audio-only không xin camera/không tạo video recorder, clipboard được phép khi tắt chặn và focus-loss có/không dừng trả lời theo policy. Mở lại bài không yêu cầu screen vẫn phải khôi phục chế độ thi. API kiểm tra lịch sử sau khi rời lớp, quyền khi đổi giáo viên, camera/screen snapshot, thiếu audio vẫn không nộp được và bật lại camera không làm đổi lượt đang thi.

Các lệnh kiểm tra chính:

```bash
TEST_DATABASE_URL=postgresql+psycopg://... .venv/bin/python -m pytest services/api/tests -q
E2E_BASE_URL=http://127.0.0.1:3100 npx playwright test \
  tests/e2e/user-profile-policy.spec.ts tests/e2e/access-enrollment.spec.ts \
  tests/e2e/academic.spec.ts tests/e2e/exam-recovery.spec.ts \
  tests/e2e/desktop-devices.spec.ts tests/e2e/exam-screen.spec.ts
npm run test:desktop
npm run test:screen
npm run test:desktop-exit
```

Chưa phát hành bộ cài Windows/macOS hoặc thử capture trên mọi cấu hình nhiều màn hình. Test Electron dùng server fixture và mô phỏng số màn hình; không đánh giá STT/LLM thật. Server cần migration `0011` và desktop mới; xem [triển khai và giới hạn](architecture/user-profiles-desktop-policy.md).

## Bộ môn, lớp học và ngân hàng đề — 18/10/2026

Kiểm tra trên dữ liệu tạm, PostgreSQL/pgvector trong container riêng và web production build local; không thao tác dữ liệu production.

| Nhóm | Kết quả |
| --- | --- |
| Toàn bộ API trên PostgreSQL | **164 đạt**, không bỏ qua; gồm quyền lớp, snapshot đề/roster, lịch, nhập Excel nguyên tử, chấm lại và các ca khóa đồng thời |
| Migration `0009 → 0010 → 0009 → 0010` | Đạt trên SQLite và PostgreSQL; kiểm thử nâng từ MVP giữ dữ liệu cũ, FK và điểm/transcript đạt |
| Playwright Chromium | **18 đạt**, API/bridge desktop giả lập; 4 ca mới về bộ môn/lớp, quyền giáo viên, người dùng và ngân hàng đề |
| ESLint, TypeScript, production build Next.js | Đạt |
| Ruff theo phạm vi workflow CI và kiểm tra cú pháp Electron | Đạt; sửa các import/định dạng cũ khiến Ruff báo lỗi |
| Node backend/retry, audio, desktop, screen | Đạt |
| Kiểm tra giao diện | Xem ảnh trang Người dùng ở 1024×768; bảng, hai khối nhập Excel, tìm kiếm và lọc vai trò không tràn ngang |

Các ca API mới xác nhận giáo viên không quản lý bộ môn/lớp hoặc xem/chấm lớp khác, đổi phân công thu hồi quyền ngay, đề nguồn duyệt vào ngân hàng không tự giao cho sinh viên, mỗi đợt có lịch/roster/điểm riêng, và thao tác gỡ môn legacy không xóa roster của lớp. Import lỗi rollback toàn bộ; nhập lại không nhân đôi thành viên. Xóa bộ môn/lớp đang có dữ liệu bị chặn; admin xóa toàn bộ môn dọn đủ cây lớp/đợt thi.

18 ca trình duyệt chạy các file `academic`, `course-hotwords`, `course-management`, `retakes`, `storage-imports`, `exam-screen`, `timed-questions` và ca `staff web` trong `platform.spec.ts`. Bao gồm khôi phục màn hình, lỗi upload, mất response và lỗi refresh của các thay đổi đã có trong workspace. Không đồng nghĩa toàn bộ 85 ca E2E đã chạy; hai ca platform dùng backend thật chưa chạy trong lượt này. Không đánh giá độ chính xác STT/LLM thật hoặc phát hành bộ cài native.

Chạy lại với PostgreSQL test riêng bằng `TEST_DATABASE_URL=... .venv/bin/python -m pytest services/api/tests -q`. Không trỏ biến này vào database đang sử dụng: fixture tạo/xóa bảng. Chạy UI sau khi build và mở web local:

```bash
E2E_BASE_URL=http://127.0.0.1:3100 npx playwright test \
  tests/e2e/academic.spec.ts tests/e2e/course-hotwords.spec.ts \
  tests/e2e/course-management.spec.ts tests/e2e/retakes.spec.ts \
  tests/e2e/storage-imports.spec.ts tests/e2e/exam-screen.spec.ts \
  tests/e2e/timed-questions.spec.ts tests/e2e/platform.spec.ts \
  --grep-invert 'login, responsive|admin enrolls'
```

Nâng cấp server cần migration **0010** và web/API/worker đồng bộ. [Thiết kế và quy tắc dữ liệu](architecture/academic-classes.md).

## Bản sửa thiếu model và khôi phục chế độ thi — 12/10/2026

Kiểm thử trên checkout cô lập; không thao tác bài thi hay dữ liệu production.

- API: **123 đạt, 5 bỏ qua**. Năm ca bỏ qua cần PostgreSQL/row locking; lần này dùng SQLite. Bao phủ payload thiếu model, ownership/kênh desktop, hạn giờ/trạng thái, idempotency, tiến câu, minh chứng bắt buộc và nhận dạng lại có quyền.
- Thiếu model: không chạy STT/LLM, transcript rỗng, confidence/điểm `null`, trạng thái cần review; audio/video gốc và màn hình theo chính sách vẫn bắt buộc. Lỗi runtime/STT thông thường không được chuyển thành bỏ qua.
- Node: **15 desktop, 8 screen, 3 audio, 2 proxy backend đạt**. Bao phủ model có/không có, runtime hỏng, kiosk lặp/rollback, hủy chooser, stream đến muộn, lỗi encoder và giữ các đoạn minh chứng.
- Kiểm tra hook React cô lập bổ sung: **9/9 đạt** với ScreenRecording thật và bridge/media giả lập, gồm lỗi begin/capture/report, hủy + kết quả đến muộn, chooser blur, sự kiện sau khóa lại và timeout/retry. Đây không thay thế kiểm thử Electron trên hệ điều hành thật.
- Python: 4 ca launcher/STT, 3 ca GNOME và 10 ca Docker cleanup đạt. Ruff các file Python thay đổi, cú pháp Electron, ESLint, TypeScript và production build đạt.
- Đã bổ sung Playwright regression cho thiếu model, cài model rồi thử lại, begin/capture/report thất bại, hủy/retry, chooser blur và sự kiện mới sau khi khóa lại. Danh sách test/biên dịch fixture kiểm tra được; **chưa chạy qua trình duyệt thành công trong môi trường này**: Chromium dừng ngay khi khởi chạy với `socket() failed: Operation not permitted`, trước khi mở ứng dụng. Không coi lỗi hạ tầng này là pass UI.
- Chưa xác minh Electron/Windows/macOS/GNOME/PipeWire thật hoặc model Whisper thật cho bản sửa này; các kết quả native ngày 11/10 bên dưới là của bản trước. Cần chạy lại các ca trên máy đích trước khi phát hành bộ cài.
- Không thay workflow/Jenkins, không kích hoạt CI thủ công, merge hoặc deploy. Cập nhật cần web/API và Electron đồng bộ, không có migration mới.

## Phạm vi xác minh ngày 11/10/2026

Desktop nhận dạng bằng Whisper-small, sinh viên chọn tiếng Việt/Anh, câu hỏi và hướng dẫn hiển thị, transcript gửi tự động để server chấm. Kiểm thử dùng dữ liệu cô lập; các ca UI bên dưới giả lập API và bridge STT, ghi media bằng thiết bị giả lập Chromium.

| Nhóm | Kết quả |
| --- | --- |
| API trên SQLite cô lập | 105 ca đạt, 5 ca cần PostgreSQL bỏ qua |
| TypeScript, ESLint, Next production build | Đạt |
| Ruff cho backend, scripts và helper | Đạt |
| Cú pháp Electron | Đạt |
| Node desktop: quyền, hotword, model, đóng cửa sổ, khóa thi và màn hình | 11 ca đạt |
| Node audio, ghi màn hình, proxy backend | 3 + 4 + 2 ca đạt |
| Python helper STT | Đạt: mặc định Whisper-small, vi/en, hotword, JSON tiếng Việt qua cp1252/ASCII/UTF-8 và đầu vào không hợp lệ |
| Python quản lý màn hình GNOME | 3 ca đạt |
| Playwright desktop và audio web | 12 ca đạt sau khi cập nhật kỳ vọng UI và fixture lưu ngôn ngữ |
| Build helper và nạp model offline | Đạt: protocol 2, Whisper-small, vi/en, hotword |
| Electron thực → IPC → helper native | Đạt với vi/en; mặc định Whisper-small khi request không truyền model |
| Đóng gói Linux unpacked | Đạt; tài nguyên gồm helper, Whisper-small và license |

## Hành vi được kiểm tra

- Model cố định dù profile lưu lựa chọn khác; ngôn ngữ được nhớ sau reload và bị khóa khi đang ghi/xử lý/nộp.
- Giao diện sinh viên hiển thị câu hỏi và trạng thái STT. Payload nộp gồm đúng transcript cùng confidence.
- Lỗi lần nhận dạng đầu chặn nộp, cho thử lại; lỗi nhận dạng lại giữ kết quả thành công trước. Hotword từ phiên thi giữ nguyên.
- Hash audio nhận dạng và audio upload khớp bản ghi gốc. Thiết bị bị rút, từ chối quyền và kết nối lại có trạng thái phù hợp; stream/recorder được giải phóng.
- Bài luyện tập web giữ luồng audio và ô transcript của web.
- Kiểm tra native dùng file giọng nói công khai `tests/data/jfk.flac` của faster-whisper, profile Electron và trang HTTP local riêng. Test xác nhận đường chạy/metadata/transcript có nội dung, không đo độ chính xác ASR.

## Chạy lại

```bash
npm run lint
npm run typecheck
npm run build
npm run check -w apps/desktop
npm run test:desktop
npm run test:audio
npm run test:screen
npm run test:backend
npm run test:desktop-displays
python3 -m unittest discover -s tests -p test_desktop_stt.py
```

Mở giao diện source bằng `npm run dev`, rồi chạy các ca dùng API giả lập:

```bash
E2E_BASE_URL=http://localhost:3001 npx playwright test tests/e2e/desktop-stt.spec.ts tests/e2e/desktop-speech-settings.spec.ts tests/e2e/desktop-devices.spec.ts tests/e2e/desktop-displays.spec.ts tests/e2e/original-audio.spec.ts
```

Chuẩn bị bundle theo [hướng dẫn build](desktop-build.md), rồi kiểm tra native và đóng gói:

```bash
ORAL_STT_TEST_AUDIO=/path/to/sample.wav npm run test:desktop-stt
npm run pack -w apps/desktop
```

Các ca Playwright dùng API thật như `platform.spec.ts` cần backend kiểm thử riêng. Không trỏ toàn bộ suite vào server đang chứa bài thi thật. Bộ API dùng fixture cô lập; các ca khóa đồng thời cần PostgreSQL:

```bash
TEST_DATABASE_URL=sqlite:// PYTHONPATH=services/api .venv/bin/python -m pytest services/api/tests -q
```

## Giới hạn xác minh

Lượt kiểm tra này chạy Linux; chưa build hoặc thử bản cài Windows/macOS. Unit test JSON kiểm tra mã hóa pipe Windows, không thay cho kiểm tra bộ cài trên Windows thật. Chưa benchmark WER/CER, hiệu chuẩn confidence hay chất lượng chấm trên dữ liệu sinh viên. Không gọi LLM trả phí và không chạy kỳ thi thật trong các ca UI/native này. Ghi màn hình và chống gian lận còn giới hạn ở cấp ứng dụng như [hướng dẫn desktop](../readme-desktop.md#truy-cập-và-ghi-màn-hình-bắt-buộc).
