# OralAI — Thi vấn đáp

Web dành cho **ADMIN, EXAM_OFFICER và TEACHER** quản lý môn, đề, lịch thi, kết quả và dung lượng. Sinh viên làm bài qua **OralAI Desktop**: ghi audio từng câu, hiển thị camera và ghi toàn màn hình theo chính sách thi và tải bản ghi gốc lên server. Sau khi nộp toàn bài, server chạy hàng đợi **STT → chấm điểm** với trạng thái theo dõi; dùng nhà cung cấp STT trong cấu hình hệ thống và LLM Ollama/Gemini để chấm theo rubric/RAG.

Các menu **Môn học**, **Ngân hàng đề thi**, **Bộ môn** và **Lớp học** tách riêng. Admin/khảo thí quản lý bộ môn, lớp, danh sách sinh viên, phân công giáo viên và lịch từng đợt thi. Giáo viên xem/chấm lại bài trong lớp được phân công. Ngân hàng đề theo môn có lọc category và rubric. [Chi tiết lớp học và phân quyền](docs/architecture/academic-classes.md).

**Người dùng → Chi tiết** mở profile, lớp đã/đang/sẽ học, các đợt thi và bài làm. **Cấu hình hệ thống → Quy định desktop** cho admin bật/tắt 10 quy định; desktop mô tả khi mở app và giữ cấu hình theo từng lượt thi. [Hồ sơ và quy định desktop](docs/architecture/user-profiles-desktop-policy.md).

Hệ thống hỗ trợ nhập Excel môn học, rubric, câu hỏi có sẵn, giảng viên, khảo thí và danh sách sinh viên; đề được review/duyệt trước khi mở thi. Admin quản lý dung lượng từng lần thi, dọn bản ghi giữ điểm hoặc xóa toàn bộ lần thi được chọn.

Một tài khoản có thể giữ nhiều vai trò; **ADMIN có mọi quyền**. Admin chọn
checkbox tại **Người dùng → Vai trò**. Điều phối kỳ thi có bộ lọc, phần tạo
thu gọn và hai tab **Đề thi & duyệt / Sinh viên & lịch thi**. Cần migration
`0012`. [Phân quyền nhiều vai trò](docs/architecture/multi-role-access.md).

Câu hỏi hỗ trợ editor định dạng và chèn ảnh, có nút sửa riêng từng câu cho
admin/khảo thí/giảng viên. Desktop chỉ upload audio từng câu và video màn
hình cho cả lượt thi khi bật; camera nằm trong khung hiển thị đúng tỉ lệ.
**Lượt thi gần đây → Xem bài** mở đúng lượt sinh viên được chọn.
[Editor và ghi hình](docs/architecture/question-editor-recording.md).

Chi tiết bài thi chia tab **Tổng quan & điểm / Câu trả lời / Màn hình & giám
sát**; admin có **Log xử lý** và menu **Log hệ thống** để tra API, lỗi web,
AI và worker theo request/tác vụ/lượt thi. Điều phối kỳ thi hiển thị số sinh
viên, số lượt thi và mở trực tiếp bài từng lượt từ danh sách thí sinh.
[Xem bài và chẩn đoán](docs/architecture/review-diagnostics.md).

## Hướng dẫn theo nhu cầu

| Bạn muốn làm gì? | Tài liệu |
| --- | --- |
| Tạo môn, sinh câu hỏi/thuật ngữ, giao bài, làm bài và xóa môn | [Hướng dẫn sử dụng cho admin, giảng viên và học viên](docs/user-guide.md) |
| Cài desktop, chọn server, kết nối thiết bị và làm bài | [Hướng dẫn OralAI Desktop](readme-desktop.md) |
| Chọn đúng lệnh mở desktop từ source hoặc server | [Bắt đầu nhanh](readme-desktop.md#bắt-đầu-nhanh) |
| Cập nhật server và xử lý lỗi pipeline | [Hướng dẫn Jenkins](docs/jenkins.md) |
| Chọn mic, nhận dạng câu trả lời hoặc thoát app | [Microphone và thoát desktop](docs/microphone-desktop.md) |
| Đối chiếu transcript và bản ghi | [Transcript và review](docs/transcript-correction.md) |
| Build, đóng gói và kiểm tra bộ cài Windows/Linux/macOS | [Build desktop](docs/desktop-build.md) |
| Build bộ cài Windows nhẹ, tải model tùy chọn | [Bộ cài Windows nhẹ](docs/desktop-build.md#bộ-cài-windows-nhẹ-tải-model-theo-quyền-admin) |
| Chuẩn bị helper và tài nguyên STT | [STT resources](apps/desktop/resources/stt/README.md) |
| Hiểu luồng nhận dạng, tài liệu kiến thức và LLM chấm bài | [Kiến trúc STT/LLM](docs/architecture/knowledge-speech.md) |
| Quản lý bộ môn, lớp, ngân hàng đề và phân công giáo viên | [Bộ môn và lớp học](docs/architecture/academic-classes.md) |
| Quản lý tài khoản, môn học và đăng nhập Google | [Tài khoản, OAuth và desktop](docs/architecture/accounts-courses-desktop.md) |
| Quản lý dữ liệu, phân biệt audio desktop và kiểm tra/lọc nhiễu trên web | [CRUD và kiểm tra tiếng ồn](docs/architecture/crud-noise-check.md) |
| Cấu hình số lần thi, cấp thêm lượt và xem lịch sử | [Làm lại bài thi](docs/architecture/exam-retakes.md) |
| Hiểu độ tin cậy AI và thao tác chấm lại | [Độ tin cậy và chấm lại](docs/architecture/grading-confidence.md) |
| Chấm phát âm tiếng Anh bằng GOPT trên CPU | [GOPT và hàng đợi tuần tự](docs/architecture/gopt.md) |
| Nạp bộ câu hỏi mẫu môn Kiểm thử phần mềm | [Bộ dữ liệu Software Testing](data/software-testing-istqb/README.md) |
| Xem 6 môn ENT001–ENT503, đề và rubric riêng cho từng môn | [Bộ dữ liệu ENT Speaking](data/ent-speaking/README.md) |
| Hiểu kiến trúc và quy tắc phát triển | [Tổng quan kiến trúc](docs/architecture/phase-1.md), [Project Guide](AI_Oral_Assessment_PROJECT_GUIDE.md) |
| Xem những gì đã kiểm thử và giới hạn còn lại | [Biên bản kiểm thử](docs/validation.md) |

Để bắt đầu: chạy server theo mục bên dưới, sau đó làm theo hướng dẫn desktop. Các tài liệu mô tả luồng hiện hành và phạm vi kiểm thử tương ứng.

## Chọn học viên cho kỳ thi trên web

Trong **Điều phối kỳ thi → Mở kỳ thi → Danh sách sinh viên**, ngoài nhập Excel, khảo thí/admin có thể **Thêm học viên từ môn / lớp học phần**: chọn môn nguồn, chọn một lớp hoặc toàn môn, tìm và chọn từng học viên hoặc chọn tất cả rồi thêm. Học viên đã có sẽ được bỏ qua; lịch thi và MSSV đã lưu không thay đổi. Sau đó xếp lịch như bình thường. Danh sách thêm là bản chụp tại thời điểm chọn, không tự đồng bộ khi lớp thay đổi.

Lớp học phần dùng chung dữ liệu tại **Quản lý lớp học**; danh sách toàn môn gồm cả học viên ghi danh trực tiếp và học viên trong các lớp của môn. Không tạo thêm cấu trúc lớp hoặc migration mới; giữ chuỗi migration hiện có đến `0012`. Cập nhật đồng bộ API/web để dùng bộ chọn này.

## Desktop dành cho sinh viên

Bản Windows nhẹ `OralAI-0.1.0-Windows-Setup-Light.exe` khoảng **203 MB (194 MiB)**,
chứa Electron và helper STT, không kèm trọng số Whisper và không bắt tải model khi mở app.
Admin bật quyền tải trong cấu hình giọng nói thì học sinh có thể bấm tải khoảng **464 MiB** Whisper cho bài thử thiết bị. Trình tải kiểm tra SHA-256 và tự thử lại
khi mạng lỗi. Model được lưu riêng trong dữ liệu người dùng và dùng lại ở những
lần mở sau. Sinh viên không cần tự cài Node, Python, Docker hoặc thư viện.

App mặc định kết nối `https://oral-test.paperlens.uk`; có thể đổi tại **Cấu hình
máy chủ**. Giao diện desktop bỏ khoảng trống sidebar web, đặt câu hỏi và thiết
bị cạnh nhau; nội dung dài cuộn trong từng vùng. Vẫn cần mạng để đăng nhập,
lấy đề và nộp bài. Xem [cài và kết nối](readme-desktop.md#cài-và-kết-nối) và
[hướng dẫn build](docs/desktop-build.md). Bộ cài/model không được đưa vào Git.

## Chạy server

### Chạy web và desktop local, chọn backend trên giao diện

Tại thư mục gốc, chạy `npm run dev` để mở giao diện local tại **http://localhost:3001**.
Chạy `npm run desktop` để mở Electron dùng cùng giao diện; nếu web local chưa chạy, lệnh này tự khởi động web.
Trên Windows, Linux và macOS, chọn **Local / Online** ở thanh **Backend** đầu trang:

- **Online:** `https://oral-test.paperlens.uk` (mặc định), dùng dữ liệu/tài khoản trên máy chủ này; không cần chạy Docker local.
- **Local:** `http://localhost:3000`, dùng server Docker trên máy này. Khởi động bằng `docker compose up -d --build --wait` nếu cần.

Lựa chọn được nhớ riêng trong trình duyệt và profile desktop. Đổi backend kiểm tra kết nối rồi tải lại giao diện;
cookie đăng nhập được tách riêng cho mỗi backend. Hãy hoàn tất bản ghi/nộp bài trước khi đổi.
Tab cũ sẽ yêu cầu tải lại nếu backend đã đổi ở tab khác. Không có thao tác đồng bộ dữ liệu giữa hai server.

Các giá trị mặc định có thể chỉnh trong `.env`, sau đó khởi động lại web/desktop local:

```dotenv
ORAL_BACKEND_MODE=online
ORAL_LOCAL_BACKEND_URL=http://localhost:3000
ORAL_ONLINE_BACKEND_URL=https://oral-test.paperlens.uk
ORAL_CLIENT_PORT=3001
```

`ORAL_BACKEND_MODE` chỉ dùng khi profile chưa lưu lựa chọn. Đây là lựa chọn **máy chủ ứng dụng**,
khác với `AI_PROVIDER=local` (Ollama chạy tại backend). Bài thử desktop nhận dạng trên máy người dùng; bài thi mới được xử lý trên server.
Launcher dùng `.venv-stt` nếu có; chuẩn bị bundle Whisper-small theo [hướng dẫn desktop](readme-desktop.md#chạy-từ-source).
Đăng nhập Google trên web local mở cửa sổ đăng nhập của backend và hoàn tất bằng luồng polling.

`npm run desktop:server` giữ cách mở Electron trực tiếp tới `ORAL_WEB_URL`/server đã lưu,
không chạy giao diện local và không có bộ chọn backend local này. Bộ cài desktop chọn server tại **Cấu hình máy chủ** trên màn hình đăng nhập.

Cần Docker Compose và Python 3. Tại thư mục gốc:

```bash
python3 scripts/setup_env.py
# Sửa cấu hình LLM trong .env trước khi dùng chấm thật.
docker compose up -d --build --wait
```

Mở **http://localhost:3000**, đăng nhập bằng `BOOTSTRAP_ADMIN` / `BOOTSTRAP_PASSWORD` trong `.env`. Mặc định `AI_PROVIDER=demo` chỉ thử quy trình, không chấm điểm.

## Chọn LLM qua .env

**Gemini:**

```dotenv
AI_CONFIG_SOURCE=env
AI_PROVIDER=gemini
GEMINI_API_KEY=your-key
LLM_MODEL=gemini-2.5-flash
EMBEDDING_MODEL=gemini-embedding-001
```

**Ollama chạy local trên server:** tải sẵn một model chat hỗ trợ JSON schema và model embedding **768 chiều**, ví dụ `qwen3:8b` và `nomic-embed-text`:

```bash
ollama pull qwen3:8b
ollama pull nomic-embed-text
```

```dotenv
AI_CONFIG_SOURCE=env
AI_PROVIDER=local
LOCAL_LLM_URL=http://host.docker.internal:11434
LOCAL_LLM_TIMEOUT=180
LLM_MODEL=qwen3:8b
EMBEDDING_MODEL=nomic-embed-text
```

Ollama phải lắng nghe tại địa chỉ API/worker truy cập được. Docker dùng `host.docker.internal` để tới host; chạy API native thì dùng `http://127.0.0.1:11434`. Đặt Ollama trong mạng nội bộ. Không dùng `localhost` trong container để trỏ tới host.

Sau khi đổi `.env`:

```bash
docker compose up -d --no-deps --force-recreate api worker
```

`AI_CONFIG_SOURCE=env` ưu tiên cấu hình AI trong `.env`, bỏ qua AI cũ lưu trên web. `admin` chỉ dành cho triển khai cũ muốn tiếp tục chỉnh AI trên web. OAuth và cấu hình ngôn ngữ STT vẫn chỉnh trên web. Đề đã công bố giữ snapshot AI/rubric; đổi provider/model thì xử lý lại tài liệu và công bố đề mới.

## Desktop và thiết bị ghi âm

Chạy `npm run desktop` để dùng giao diện source. Bộ cài từ workflow **Desktop installers** chứa Whisper-small đa ngôn ngữ, runtime STT và FFmpeg; nhận dạng CPU INT8. Máy sinh viên vẫn cần mạng để đăng nhập, lấy đề, tải minh chứng và nhận xác nhận nộp bài.

1. Chọn server tại **Cấu hình máy chủ** trước khi đăng nhập.
2. Mở bài, xem quy định, cấp quyền microphone và camera nếu được yêu cầu.
3. Chuẩn bị một màn hình và đồng ý ghi toàn màn hình khi quy định yêu cầu; bài thi nhận dạng theo ngôn ngữ cấu hình trên server.
4. Bấm **Bắt đầu thi**. Câu hỏi đếm ngược chuẩn bị mặc định 10 giây rồi tự ghi tối đa 60 giây. N/M cấu hình riêng cho từng câu trong Review câu hỏi & rubric. Có thể bấm **Kết thúc trả lời** sớm.
5. App tự tải bản ghi, chuyển câu tiếp theo và tự nộp ở câu cuối khi đủ minh chứng. Nếu tải lỗi, thử lại rồi nộp; chỉ đóng app sau xác nhận đã nộp. Server tiếp tục nhận dạng và chấm.

Desktop hiển thị câu hỏi, hướng dẫn và xác nhận nộp bài; không hiển thị điểm. Trạng thái STT/chấm, điểm và chi tiết đánh giá chỉ dành cho admin, khảo thí và giáo viên có quyền trên web. STT theo cấu hình hệ thống, ưu tiên ngôn ngữ của đề. Whisper-small cục bộ giữ để tương thích client cũ. [Hướng dẫn desktop](readme-desktop.md), [microphone](docs/microphone-desktop.md), [transcript và review](docs/transcript-correction.md).

Chức năng **Học & thi thử** đã bỏ trên web/desktop. Server không tạo lại môn luyện tập và không cho mở các đề luyện tập cũ.

## Thuật ngữ tiếng Anh và xóa môn học

Khi bấm **Sinh câu hỏi & rubric để review**, AI gợi ý thuật ngữ tiếng Anh kèm nghĩa tiếng Việt cho từng câu hỏi. Admin xem ngay trong **Ngân hàng đề thi → chọn môn → Câu hỏi & thuật ngữ tiếng Anh gợi ý**. Gợi ý được lưu cùng phiên bản đề; đề cũ không tự sinh lại, chế độ demo không tạo thuật ngữ. Thuật ngữ do AI sinh để giảng viên kiểm tra; STT dùng bảng hotword riêng do admin/giảng viên cấu hình, không tự đưa đáp án vào nhận dạng.

Thao tác từng bước từ chuẩn bị giáo trình đến giao đề: [hướng dẫn admin/giảng viên](docs/user-guide.md#admin-và-giảng-viên-chuẩn-bị-bài-thi). Hiện chưa sửa trực tiếp thuật ngữ; sao chép đề thành bản nháp rồi công bố để sinh bộ câu hỏi/gợi ý mới.

Admin vào **Môn học → Cài đặt → Xóa môn học**, nhập đúng mã môn để xóa vĩnh viễn toàn bộ tài liệu, chủ đề, rubric, đề thi, lượt thi, kết quả và bản ghi, kể cả bài đang làm. Tài khoản người dùng và môn khác được giữ lại. Worker dọn tệp sau khi giao dịch xóa thành công, tự thử lại nếu storage lỗi. Nếu môn đang được worker xử lý, chờ rồi thử xóa lại. Giảng viên chỉ xóa được môn trống do mình quản lý.

## Số lần làm bài và kết quả

**Độ tin cậy AI:** lỗi chấm, demo và bài không tính điểm hiện “Chưa có độ tin cậy AI”, không hiển thị 0% giả. Số phần trăm khi chấm thành công do LLM tự báo, chưa được hiệu chuẩn. Nếu gặp `AI_CONFIG_MISMATCH`, lần chấm thông thường cần tài liệu và phiên bản đề khớp cấu hình AI hiện tại. Admin có thể chọn **Nhận dạng lại & chấm lại → Local → Chấm lại toàn bộ từ audio**: Whisper → Ollama → GOPT theo rubric, giữ bản nộp/lịch sử và yêu cầu xem lại. Xem [cấu hình local và GOPT](docs/architecture/gopt.md#chấm-lại-toàn-bộ-bằng-model-local).

Admin mở **Ngân hàng đề thi → chọn môn → Cấu hình số lần làm lại**: không cho làm lại, cho làm lại N lần hoặc không giới hạn. Ví dụ cho làm lại 1 lần là tổng cộng 2 lượt.

**Kết quả & xem lại** hiển thị ngay bài gần nhất của mỗi sinh viên khi chọn môn; đề/kỳ thi và ngày thi là bộ lọc tùy chọn. Không lọc theo số lần làm bài. Danh sách hiển thị cả sinh viên chưa thi, trạng thái hàng đợi và điểm chính thức; bấm **Xem bài** để mở chi tiết. Câu lỗi có nút **Thử xử lý lại** cho giảng viên phụ trách/admin. Mở **Quản lý lượt thi** để cấp thêm lượt riêng cho sinh viên hoặc xóa lần thi được chọn. Sinh viên xem lịch sử nộp bài không kèm điểm và bấm **Làm lại bài thi** khi còn lượt. [Chi tiết và nâng cấp database](docs/architecture/exam-retakes.md).

## Admin chọn STT trên server

Trong **Cấu hình hệ thống → STT & giọng nói**, admin chọn Whisper server, Gemini hoặc Google Cloud STT cho hàng đợi và trình duyệt web. Bài thi mới nhận dạng trên server qua hàng đợi; bài thử desktop vẫn nhận dạng local.

Khi xem kết quả, mở **Nhận dạng lại & chấm lại**, chọn nhà cung cấp và nhập lý do:

- **Gemini STT:** dùng API key và model trong `.env`:

```dotenv
GEMINI_API_KEY=your-key
GEMINI_STT_MODEL=gemini-2.5-flash
```

- **Google Cloud STT:** mở mục cấu hình JSON trong tab STT, upload service-account JSON hợp lệ (tối đa 64 KB). Cần bật Speech-to-Text API, billing và cấp quyền cho tài khoản. Upload không tự đổi nhà cung cấp.

Nhận dạng lại dùng audio gốc và hoạt động cả khi `AI_PROVIDER=local`. Nhà cung cấp đã chọn nhận dạng, còn LLM chấm vẫn theo snapshot đề. **Chỉ Google Cloud STT cần JSON; Gemini không cần.** Giữ transcript đã nộp và lịch sử trước/sau. Gemini không trả độ tin cậy âm học nên kết quả này cần giảng viên kiểm tra trước khi công nhận điểm.

## Build, cập nhật và tài liệu

Build desktop cần chuẩn bị bundle STT trước; xem [hướng dẫn desktop](readme-desktop.md) và [đóng gói](docs/desktop-build.md). Không đưa binary/model hoặc `.env` vào Git.

`Jenkinsfile` build/kiểm tra/deploy web và API; bộ cài desktop dùng workflow riêng. Nếu deploy bằng Jenkins, đồng bộ các biến mới trong credential `oral-ai-env`.

Xem [các bước cập nhật và chẩn đoán lỗi Jenkins](docs/jenkins.md).

Cập nhật server: `docker compose up -d --build --wait`, sau đó build/cài desktop mới hoặc mở lại Electron source đã cập nhật. Compose tự chạy migration đến `0011` để bổ sung cấu hình desktop theo lượt thi và bộ môn/lớp/đợt thi, giữ đồng hồ chuẩn bị câu hỏi, cùng hàng đợi STT/chấm điểm bền vững, cùng các thay đổi lượt thi/khảo thí/giám sát trước đó; không cần thêm biến `.env`. Không xóa volume dữ liệu. Kiểm tra chờ chấm/lỗi bằng `docker compose logs --tail=100 worker`.

Admin có trang **Lần thi & dung lượng** để lọc theo môn/người, xuất báo cáo Excel, chọn dọn bản ghi giữ điểm hoặc xóa toàn bộ dữ liệu lần thi. Có mẫu Excel và kiểm tra trước khi nhập môn, rubric, câu hỏi có sẵn, giảng viên và khảo thí. Cần cập nhật đồng bộ web, API và worker; xem [quản lý dung lượng và nhập Excel](docs/user-guide.md#quản-lý-lần-thi-và-dung-lượng).

```bash
.venv/bin/python -m pytest services/api/tests -q
npm run lint
npm run typecheck
npm run build
npm run test:audio
npm run test:desktop
```

Tra cứu thêm trong [Hướng dẫn theo nhu cầu](#hướng-dẫn-theo-nhu-cầu) ở đầu trang.

## Môn luyện nói TOEIC

Bộ dữ liệu `TOEIC-SPEAKING-01`: 11 câu, 2 tranh minh họa, tài liệu RAG, đáp án và rubric chấm nội dung transcript thang 10; 30 phút/lượt, làm lại không giới hạn. Script nhập môn và giao đề cho toàn bộ sinh viên đang hoạt động: [hướng dẫn và dữ liệu](data/toeic-speaking/README.md). Điểm này chưa đánh giá phát âm/ngữ điệu và không quy đổi thành điểm TOEIC chính thức.

Hàng đợi STT dùng **bản ghi gốc** được desktop tải lên. Bài thử desktop cũng dùng bản gốc khi nhận dạng/thử lại. Trên web, checkbox **Lọc nhiễu RNNoise khi nhận dạng câu trả lời** ban đầu tắt; có thể bật khi cần hoặc chọn bản gốc/bản lọc để nhận dạng lại. Với môn tiếng Anh này, hàng đợi và web nhận ngôn ngữ tiếng Anh từ phiên bản đề; bài thử desktop chọn **Tiếng Anh**.

### Cài bộ luyện TOEIC trên server khác

Source chứa dữ liệu mẫu và script nhập; `git pull` không sao chép database, tài khoản hoặc danh sách giao bài từ máy khác. Sau khi cấu hình môi trường và tài khoản trên server đích, chạy tại thư mục gốc dự án:

```bash
git pull --ff-only origin main
docker compose up -d --build --wait
docker compose cp data/toeic-speaking api:/tmp/toeic-speaking
docker compose exec -T api python /tmp/toeic-speaking/import_course.py
```

Cần có ADMIN đang hoạt động và cấu hình LLM/embedding thật. Script tạo môn, tài liệu và đề, rồi thêm/giao bài cho các tài khoản **STUDENT / ACTIVE trên server đích**. Chạy lại cùng phiên bản không tạo trùng; có thể dùng lại lệnh import để thêm sinh viên mới. Chi tiết dữ liệu và cách kiểm tra chấm: [bộ TOEIC Speaking](data/toeic-speaking/README.md).

Khi có lần nộp mới hơn của cùng sinh viên/cùng đề, worker dọn audio/video/màn hình của lần cũ đã xử lý xong; giữ điểm, transcript và lịch sử. Bài cũ đang STT/chấm/chấm lại được giữ file đến khi hoàn tất. Quy tắc cũng dọn các lần cũ đã có sau khi triển khai.
