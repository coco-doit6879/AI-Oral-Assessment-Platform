# Chấm phát âm GOPT trên CPU

Nếu triển khai bằng Jenkins, dùng [hướng dẫn bật Ollama riêng và GOPT](../jenkins.md#ollama-riêng-cho-oral-và-chấm-lại-local)
để pipeline quản lý đúng project, image và credential; không chạy lệnh Compose phát triển
đè lên deployment production bên dưới.

## Khởi chạy

```sh
docker compose -f docker-compose.yml -f docker-compose.gopt.yml build gopt
docker compose -f docker-compose.yml -f docker-compose.gopt.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.gopt.yml ps
docker compose -f docker-compose.yml -f docker-compose.gopt.yml logs --tail=100 gopt worker
```

Luôn dùng cả hai file khi cập nhật deployment này. Overlay bật GOPT cho API/worker,
thêm container nội bộ `gopt` và chờ healthcheck trước khi worker khởi động.
Không cần GPU, API key hay port public mới. Chọn ngôn ngữ tiếng Anh cho môn/đề;
đề đã công bố giữ `speech_language` trong snapshot. Bài luyện tập và rubric không
có tiêu chí phát âm không gọi GOPT. Rubric yêu cầu phát âm nhưng chưa bật GOPT hoặc
ngôn ngữ đề không phải tiếng Anh sẽ báo lỗi, không tự bỏ qua tiêu chí. Code local
mặc định `GOPT_ENABLED=false`.

Build đầu cần mạng để tải mã nguồn Kaldi/GOPT, PyTorch CPU, model LibriSpeech m13,
từ điển. Ánh xạ âm vị huấn luyện được đóng sẵn trong source. Kaldi được compile với `BUILD_JOBS=1`, không CUDA;
build có thể mất nhiều thời gian và dung lượng đĩa. Nên build image trên máy build
rồi chuyển image sang server ít tài nguyên. Model được đóng sẵn trong image, không
tải lại mỗi lần restart hoặc mỗi câu trả lời. Không cần tải bộ audio SpeechOcean762.

## Luồng xử lý và điểm

Worker xử lý lần lượt **STT → chấm nội dung theo rubric → GOPT → lưu kết quả**.
GOPT nhận bản ghi AUDIO gốc đã kiểm tra kích thước/SHA-256 và transcript, chuyển
PCM mono 16 kHz, trích MFCC/i-vector, chạy acoustic model Kaldi trên CPU, forced
alignment và trích đặc trưng GOP 84 chiều. Model GOPT dùng checkpoint LibriSpeech
chính thức, đúng ánh xạ 39 âm vị từ nhãn huấn luyện và chuẩn hóa `(feature - 3.203) / 4.045`.
Không thay đặc trưng Kaldi bằng wav2vec2 hoặc điểm giả định.

GOPT có context 50 âm vị. Chuỗi dài được chia theo ranh giới từ, mỗi đoạn tối đa
50 âm vị, chấm batch size 1; tổng hợp các đoạn theo số âm vị. Đây là cách mở rộng
cho bài nói dài của ứng dụng, chưa được hiệu chuẩn như benchmark câu ngắn gốc.
Điểm accuracy/completeness/fluency/prosody/total được quy về 0–10 từ đầu ra model
0–2, giới hạn trong thang điểm. `completeness` đối chiếu transcript, không đo độ
đầy đủ nội dung câu trả lời so với đáp án. ASR có thể chuẩn hóa lỗi phát âm;
transcript sai cần được sửa/chấm lại bằng luồng review hiện có.

Kết quả nằm trong `assessment.pronunciation`, bao gồm model revision, hash audio,
hash transcript, số đoạn, số âm vị và điểm. Màn hình xem bài hiển thị điểm phát âm
riêng. Tiêu chí có tên chứa `Phát âm` (có/không dấu), `Pronunciation` hoặc `pronounce`
được chấm bằng GOPT, không giao LLM đoán phát âm từ văn bản. Nên tạo tiêu chí phát âm
riêng, không gộp với kiến thức. Điểm tiêu chí = `GOPT total / 10 * max_score`;
tổng điểm = trung bình có trọng số của các tiêu chí đã chuẩn hóa về thang 10.
`pronunciation.applied_criteria` và `criteria[].source=gopt` lưu nguồn điểm.
Kết quả có GOPT luôn cần giảng viên kiểm tra. Cần hiệu chuẩn với bài nói và điểm
giảng viên thực tế trước khi sử dụng để quyết định điểm thi; điểm tham khảo cũ
không được tự động cộng vào tổng khi đọc lại lịch sử.

Chỉ chấm từ có trong từ điển tiếng Anh; số cần viết thành chữ trong transcript.
Từ ngoài từ điển, không align đủ âm vị, audio hỏng/dài quá giới hạn, timeout hoặc
dịch vụ lỗi đều trả trạng thái lỗi, không chấm phần bị cắt và không trả điểm 0 giả.
Điểm từng tiêu chí nội dung đã tính được giữ lại, nhưng tổng điểm để trống vì
chưa đủ tiêu chí, yêu cầu review. Với hàng đợi server audio,
tác vụ chuyển FAILED và nút thử lại hiện có sẽ chạy lại bước grading, không chạy
lại STT. Nút **Chấm lại toàn bộ từ audio** luôn chạy lại STT từ đầu.

## Chấm lại toàn bộ bằng model local

Trong **Kết quả & xem lại** (hoặc mở bài từ **Điều phối kỳ thi → Sinh viên & lịch thi**),
admin chọn **Nhận dạng lại & chấm lại → Local → Chấm lại toàn bộ từ audio**.
Hệ thống xếp một `ReviewJob`: audio gốc → Whisper CPU → Ollama → GOPT khi rubric yêu cầu.
Nút chấm riêng transcript đã nộp không còn trên UI; API cũ vẫn giữ tương thích.

- Cấu hình `LOCAL_LLM_URL` trỏ đến Ollama do bạn vận hành và `LOCAL_REVIEW_LLM_MODEL`
  là tên model đã cài trên đó. Để trống chỉ dùng `LLM_MODEL` nếu `AI_PROVIDER=local`.
  Không tự tải hoặc chọn một model LLM lớn, không tự đổi nhà cung cấp khi lỗi.
- `STT_MODEL` được giữ trong policy lúc xếp hàng; chuẩn bị sẵn model Whisper trong
  cache server nếu cần vận hành không có mạng. Model Ollama cũng được giữ trong policy.
- Có thể chấm lại đề được công bố với Gemini/demo mà không sửa snapshot đề.
  Truy xuất `frozen-lexical-v1` xếp hạng theo từ chung trong câu hỏi/câu trả lời,
  chỉ dùng chunk của môn và tài liệu READY trong phạm vi đóng băng của đề, lấy tối đa
  `TOP_K`. Đây không phải vector search; không trộn embedding khác model và không gọi
  cloud để embedding. Cần giảng viên duyệt kết quả sau khi đổi cách chấm.
- Transcript đã nộp, audio, rubric, nguồn kiến thức và đánh giá trước được giữ nguyên
  trong lịch sử. Chỉ cập nhật đánh giá hiện tại khi toàn bộ pipeline thành công.
  STT/LLM/GOPT lỗi thì review FAILED, giữ đánh giá trước; gửi lại yêu cầu để chạy từ đầu.
- Review local dùng số luồng do Ollama tự chọn (`LOCAL_LLM_CPU_THREADS=0`, không gửi `num_thread`), `num_gpu=0`, `keep_alive=0` để
  giải phóng model sau chấm. Các tùy chọn dùng [API chat Ollama](https://docs.ollama.com/api/chat)
  và [Runner options](https://github.com/ollama/ollama/blob/main/api/types.go).
  Ollama ngoài Compose có cấu hình riêng; giới hạn của worker không
  áp dụng cho tiến trình Ollama. Dùng model đã cài tại máy, không dùng model cloud.

### Debug chấm lại và timeout

`LOCAL_LLM_TIMEOUT` mặc định là `600` giây, cho phép cấu hình từ 10 đến 900 giây;
Ollama dùng timeout kết nối riêng 10 giây. File credential cũ có giá trị `180` vẫn
ghi đè mặc định, nên cần cập nhật `oral-ai-env` và deploy lại cả API/worker.
Đây là timeout HTTP chờ phản hồi, không phải deadline tổng của cả STT → LLM → GOPT.
Gemini vẫn dùng `GEMINI_TIMEOUT`, GOPT dùng `GOPT_TIMEOUT` riêng.

Lỗi review hiển thị **Mã tác vụ** (`job_id`) để đối chiếu log worker:

```bash
docker logs --since 30m oral-assessment-web-worker-1 2>&1 | grep 'MA_TAC_VU'
docker logs --since 30m --tail 100 oral-assessment-web-ollama-1
docker logs --since 30m --tail 100 oral-assessment-web-gopt-1
docker stats --no-stream oral-assessment-web-worker-1 oral-assessment-web-ollama-1 oral-assessment-web-gopt-1
```

Log JSON `oral.diagnostics` ghi `job_id`, `attempt_id`, bước đang chạy,
provider/model, thời gian đã chạy, timeout cấu hình, loại exception và HTTP status
nếu có. Các bước gồm `review.audio_download`, `review.stt`, `review.grading`,
`ollama.chat`, `gemini.generateContent`, `gopt.assess`. `frames` chỉ ghi tên file,
dòng và hàm, không ghi nội dung exception, URL, header, transcript hay prompt.
`review_finished` ghi trạng thái cuối `COMPLETED`/`FAILED`.

Lỗi phát âm có thêm sự kiện `gopt.pronunciation` (AI / ERROR), kèm
`reason_code` phân biệt dịch vụ tắt, ngôn ngữ, audio, timeout, kết nối, HTTP
và kết quả sai định dạng. Lỗi trước bản sửa vẫn là WARNING; khi tra mã tác vụ
cũ hãy bỏ bộ lọc mức/nguồn/model và mở toàn bộ thời gian còn lưu.
Xem [cách đối chiếu log không xuất hiện](review-diagnostics.md#tra-lỗi-chấm-phát-âm-không-thấy-trên-giao-diện).

Khi Ollama thành công, các số `load_duration`, `prompt_eval_duration`, `eval_duration`,
`total_duration` trả về từ provider được giữ nguyên (nanosecond), cùng
`prompt_eval_count`/`eval_count` để phân biệt chậm tải model và chậm suy luận.
`ReadTimeout` cho biết hết thời gian chờ đọc; `ConnectTimeout` là hết thời gian kết nối.
HTTP 429/503 cần đối chiếu tình trạng tải/dịch vụ thay vì tăng timeout liên tục.

Không tự retry HTTP khi timeout: yêu cầu trước có thể còn đang xử lý ở provider.
Vẫn giữ `WORKER_SERIAL=true`, giới hạn CPU/RAM hiện có và đánh giá trước nếu thất bại.
Tăng thời gian chờ không bảo đảm mọi bài sẽ hoàn tất; kiểm tra tài nguyên và log
trên server trước khi tăng số luồng hoặc chạy nhiều request.

Bật `GOPT_ENABLED=true` trong `.env` chưa đủ để tạo service trên server: với Jenkins,
cần build/load trước image `ORAL_GOPT_IMAGE` theo [hướng dẫn triển khai](../jenkins.md#bật-thêm-gopt-khi-rubric-có-phát-âm),
upload credential và deploy. GOPT chỉ được gọi cho rubric có phát âm và policy tiếng Anh.

## Bổ sung sinh viên sau công bố

Khảo thí/admin có thể thêm theo môn/lớp, thêm thủ công hoặc import `.xlsx` ngay cả
khi đề đã công bố. Email tài khoản có sẵn giữ mật khẩu; tài khoản mới có mật khẩu
tùy chọn 12–128 ký tự, để trống nếu dùng đăng nhập Google theo email.
Sinh viên mới chưa có lịch, cần chọn và **Lưu lịch thi**. Không thay snapshot đề,
không đổi lịch sinh viên đã có phiên thi chưa xóa. Danh sách hiển thị các lần thi,
trạng thái và điểm đã xác nhận; bấm tên hoặc từng lần thi để mở đầy đủ audio/đánh giá.
Lọc **Chỉ sinh viên đã nộp bài** bao gồm bài đang xử lý, cần duyệt và đã hoàn tất.

## Giới hạn tải

| Cấu hình | Mặc định |
| --- | --- |
| Số bài đang xử lý | 1 trên toàn bộ worker dùng cùng PostgreSQL |
| Số request GOPT đang chấm | 1; request đồng thời trả 429, không xếp hàng trong RAM |
| CPU GOPT / worker / Ollama | Không đặt quota container |
| RAM/swap GOPT / worker / Ollama | Không đặt hạn mức container |
| Luồng Whisper / BLAS / PyTorch | Engine tự chọn; không ép 1/3 luồng |
| i-vector / Kaldi `nj` | Giữ một luồng i-vector và một job theo pipeline căn chỉnh hiện tại |
| Kaldi `nj` / GPU | 1 / tắt |
| Audio | Tối đa 24 MiB và 120 giây mỗi câu |
| Timeout GOPT / HTTP worker | 900 / 960 giây |
| File tạm GOPT | `/tmp` tối đa 512 MiB, dọn sau mỗi request |

`WORKER_SERIAL=true` dùng PostgreSQL transaction advisory lock trên kết nối riêng,
giữ suốt một lượt xử lý, bao gồm STT, review và tài liệu. Worker khác không claim
việc khi khóa bận. Khóa tự nhả khi transaction/kết nối kết thúc hoặc process chết;
hàng đợi và cơ chế lease/recovery hiện tại vẫn hoạt động. SQLite development chỉ
có khóa trong process; deployment nhiều worker phải dùng PostgreSQL như Compose.
Không tắt `WORKER_SERIAL` trên server ít CPU. Service GOPT chỉ chạy **một uvicorn
worker**, không scale replica vì mỗi replica có model và khóa riêng.
Deadline kết thúc cả nhóm tiến trình Kaldi; `init: true` thu hồi tiến trình con
để tránh tích lũy zombie sau timeout.

Không còn dùng các biến `*_CPUS`, `*_MEMORY`, `GOPT_BLAS_THREADS` để giới hạn
container. `STT_CPU_THREADS=0` dùng mặc định của CTranslate2; xem
[tài liệu Whisper/CTranslate2](https://opennmt.net/CTranslate2/python/ctranslate2.models.Whisper.html).
Giữ `GOPT_MAX_AUDIO_MB`, `GOPT_MAX_AUDIO_SECONDS`, `GOPT_JOB_TIMEOUT`,
`GOPT_TIMEOUT`; HTTP timeout lớn hơn job timeout ít nhất 60 giây.
Một bài có thể dùng nhiều CPU/RAM dù hàng đợi chạy tuần tự; kiểm tra tài nguyên
thực tế bằng `docker stats`. Cần build lại image GOPT để bỏ lệnh ép luồng
PyTorch của phiên bản cũ; xem [triển khai Jenkins](../jenkins.md#ai-không-giới-hạn-cpuram-chấm-tuần-tự--26102026).

## Kiểm tra

```sh
cd services/api
python -m pytest tests/test_pronunciation.py tests/test_worker_serial.py tests/test_server_processing.py
cd ../gopt
python -m pytest tests
```

Test service cần `requirements.txt`, `pytest`, `httpx`; test thuật toán/HTTP không
cần tải model. Smoke test thực tế sau build: tạo bài tiếng Anh ngắn có audio,
nộp bài, chờ worker, kiểm tra `assessment.pronunciation.status=COMPLETED` và điểm
hiển thị trong phần xem bài. Thử thêm một bản ghi phát âm khác cùng câu và xác
nhận điểm thay đổi. Unit test có mock không xác nhận chất lượng chấm acoustic.

Smoke test trên Docker CPU đã kiểm tra HTTP, đổi tốc độ audio, chia 124 âm vị
thành ba đoạn, healthcheck khi bận và từ chối request đồng thời bằng 429.
Audio tổng hợp ngắn mất khoảng 6 giây kể cả nạp model; RAM đỉnh nhóm thử nghiệm
khoảng 387 MiB với giới hạn 1 CPU/2 GiB. Đây không phải benchmark phần cứng server
hoặc bằng chứng độ chính xác với người học thực tế.

## Nguồn và khả năng tái lập

- [GOPT chính thức](https://github.com/YuanGongND/gopt), revision
  `bed909daf8eca035095871e51642525acc5b9b55`; checkpoint `gopt_librispeech`.
- [Kaldi GOP recipe](https://github.com/kaldi-asr/kaldi/tree/e02e35f0254bb033fab73d1df99fc34123e31d56/egs/gop_speechocean762),
  revision `e02e35f0254bb033fab73d1df99fc34123e31d56`.
  Build dùng OpenFst/OpenBLAS của Debian 12. `patch_kaldi.py` chuyển tám lời gọi
  LAPACK có tham số ký tự sang wrapper `LAPACK_*` của header Debian để truyền
  đúng độ dài chuỗi Fortran và điều chỉnh wrapper in FST cho OpenFst 1.7.9
  của Debian; không thay thuật toán hay checkpoint. BuildKit cache giữ bản tải
  model và kết quả compiler giữa các lần build.
- [Acoustic model và i-vector LibriSpeech m13](https://kaldi-asr.org/models/m13).
- [Lỗi ánh xạ âm vị upstream](https://github.com/YuanGongND/gopt/issues/15):
  dùng thứ tự nhãn huấn luyện, không tạo ánh xạ mới từ bài đang chấm.
- `services/gopt/training_phones.json` được đối chiếu bằng cách lấy thứ tự xuất hiện
  đầu tiên trong 47.076 nhãn của [bản sao tr_labels_phn.csv](https://github.com/hf49w/custom-gopt/blob/3f2df988d6915d340acc774977b561dc445a9062/tr_labels_phn.csv).
  Link Dropbox của dữ liệu GOP gốc hiện trả HTML; build không phụ thuộc link này.

`prepare_assets.py` kiểm tra các file cần thiết và ghi SHA-256 vào
`/opt/gopt-assets/manifest.json`. Mã nguồn/checkpoint được pin theo revision;
archive model/dữ liệu bên ngoài dùng URL upstream và ghi hash sau tải, chưa có
checksum upstream cố định để xác thực trước tải. Giữ image đã kiểm chứng và
manifest của deployment để so sánh khi rebuild.
