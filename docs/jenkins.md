# Cập nhật OralAI qua Jenkins

[README / danh mục tài liệu](../README.md#hướng-dẫn-theo-nhu-cầu) · [Hướng dẫn sử dụng](user-guide.md) · [Jenkinsfile](../Jenkinsfile)

Jenkins build, kiểm thử và triển khai web/API/worker. Bộ cài desktop được tạo riêng bằng workflow **Desktop installers** trên GitHub Actions.

## Điều kiện của job hiện tại

Các giá trị dưới đây lấy từ `Jenkinsfile` đang có trong repo:

| Thành phần | Thiết lập |
| --- | --- |
| Agent | Nhãn `docker`, có Python 3, Docker, Docker Compose và plugin Buildx |
| SCM | Repository này; nhánh do job SCM chọn (`checkout scm`), credential Git được chọn trong cấu hình job |
| Biến môi trường triển khai | Jenkins credential loại **Secret file**, ID `oral-ai-env` |
| Reverse proxy | Docker network ngoài `nginx-network` |
| Domain triển khai | `https://oral-test.paperlens.uk` |
| Cổng trên host | Web `127.0.0.1:13000`, MinIO console `127.0.0.1:19001` |

Trong credential, `PUBLIC_ORIGIN` và `ALLOWED_ORIGINS` phải khớp domain trên; `COOKIE_SECURE=true`, `WEB_BIND=127.0.0.1`, `WEB_PORT=13000`, `MINIO_CONSOLE_PORT=19001`. Các biến database, storage và AI cần giữ giá trị phù hợp với server đang chạy. Sửa `.env` trên máy phát triển không tự cập nhật credential Jenkins.

Jenkinsfile này dành cho địa chỉ triển khai trên. Nếu đổi domain, network hoặc cổng, phải cập nhật cả cấu hình pipeline, credential và reverse proxy tương ứng.

## Ollama riêng cho Oral và chấm lại local

Lỗi `LOCAL_REVIEW_NOT_CONFIGURED` là thiếu tên model chấm lại, không phải lỗi trùng cổng.
Để dùng `qwen2.5:3b` trong container riêng, cập nhật **Secret file `oral-ai-env`**
(giữ nguyên các biến database, storage, domain và provider hiện tại):

```dotenv
ORAL_OLLAMA_ENABLED=true
LOCAL_REVIEW_LLM_MODEL=qwen2.5:3b
```

Triển khai Jenkinsfile mới rồi chạy **Build Now**. Pipeline chọn `docker-compose.ollama.yml`,
tải image Ollama và tải model nếu chưa có trước khi dừng API/worker để migration.
Không cần đổi `AI_PROVIDER` hay `LLM_MODEL` của kỳ thi đã phát hành. Nếu provider hiện tại
là `local`, pipeline cũng yêu cầu và chuẩn bị `LLM_MODEL`, `EMBEDDING_MODEL` trong Ollama mới.

- Container: `oral-assessment-web-ollama-1`; volume model: `oral-assessment-web_ollama_data`.
- API/worker tự dùng `http://ollama:11434` trên network `oral-assessment-web_default`.
- Không publish port lên host, không dùng chung volume/network của SOS. Không sửa hay dừng
  `sos-ai-ollama`; model cùng tên được tải riêng, cần thêm dung lượng đĩa.
- Ollama, worker và GOPT không đặt quota CPU/RAM trong Compose. Ollama giữ
  một model và một lượt suy luận; worker chấm tuần tự từng tác vụ.
  Không gắn GPU; review giải phóng model sau chấm. Nếu CPU chậm gây timeout,
  có thể tăng `LOCAL_LLM_TIMEOUT` trong credential, ví dụ `600`, thay vì tăng concurrency.
- Không bật cloud model. Xem [cấu hình Ollama](https://docs.ollama.com/faq) và
  [mạng bridge Docker](https://docs.docker.com/engine/network/drivers/bridge/).

Kiểm tra sau khi Jenkins deploy thành công:

```bash
docker exec oral-assessment-web-ollama-1 ollama list
docker exec oral-assessment-web-worker-1 python -c "import urllib.request; print(urllib.request.urlopen('http://ollama:11434/api/tags', timeout=10).read().decode())"
```

### Bật thêm GOPT khi rubric có phát âm

Ollama không thay thế GOPT. Trước khi bật, build image GOPT một lần từ thư mục repo
trên Docker host mà Jenkins sử dụng (hoặc build ở máy khác cùng kiến trúc rồi load image).
Build Kaldi ban đầu cần nhiều thời gian và dung lượng; không chạy đồng thời với giờ thi:

```bash
docker build --build-arg BUILD_JOBS=1 -t oral-assessment-gopt:cpu services/gopt
```

Sau đó thêm vào `oral-ai-env` và deploy lại:

```dotenv
GOPT_ENABLED=true
ORAL_GOPT_IMAGE=oral-assessment-gopt:cpu
```

Jenkins chọn thêm `docker-compose.gopt.yml`, kiểm tra image đã có và khởi động
`oral-assessment-web-gopt-1` (không publish port). Thiếu image hoặc tải model thất bại
sẽ chặn deployment trước bước dừng ứng dụng. Không tự build Kaldi trong mỗi lượt deploy.
Xem [giới hạn và luồng GOPT](architecture/gopt.md).

### AI không giới hạn CPU/RAM, chấm tuần tự — 26/10/2026

Bản này thay cấu hình 3 CPU/4 GiB trước đó: bỏ `cpus`, `mem_limit`,
`memswap_limit`, `pids_limit` khỏi Ollama, worker và GOPT. Các biến cũ
`ORAL_OLLAMA_CPUS`, `ORAL_OLLAMA_MEMORY`, `WORKER_CPUS`, `WORKER_MEMORY`,
`GOPT_CPUS`, `GOPT_MEMORY`, `GOPT_BLAS_THREADS` không còn được dùng để đặt
hạn mức; có thể xóa khỏi credential `oral-ai-env`.

- Hai overlay ép `WORKER_SERIAL=true`: một tác vụ chấm tại một thời điểm
  trên các worker dùng cùng PostgreSQL, giữ khóa đến khi tác vụ kết thúc.
  Chấm lại vẫn được phép; đây không phải giới hạn một lần chấm trong lịch sử.
- Ollama giữ `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_MAX_LOADED_MODELS=1`; GOPT có
  một process và khóa chặn request đồng thời. Whisper có một inference worker.
- Ollama/Whisper dùng cấu hình luồng tự động (`LOCAL_LLM_CPU_THREADS=0`,
  `STT_CPU_THREADS=0`); overlay ghi đè cả giá trị 1/3 cũ trong credential.
  Worker/GOPT khởi chạy bằng `env -u` để bỏ biến OMP/BLAS/MKL/NumExpr giới hạn
  luồng từ credential hoặc image cũ. GOPT mới không ép PyTorch dùng một luồng.
- Không có quota container không có nghĩa một request luôn sử dụng hết CPU;
  engine tự chọn mức song song trong một bài. Một bài vẫn có thể dùng nhiều
  RAM. Giữ timeout, giới hạn audio, dung lượng `/tmp` của GOPT và các kiểm tra
  dữ liệu; không bật GPU hoặc tăng số bài chấm đồng thời.

**Triển khai GOPT:** Jenkins dùng image đã build sẵn, không tự build Kaldi.
Để bỏ cả giới hạn PyTorch trong engine cũ, build lại image từ commit mới
trên Docker host của Jenkins (dùng đúng tag trong `ORAL_GOPT_IMAGE`):

```bash
docker build --build-arg BUILD_JOBS=1 -t oral-assessment-gopt:cpu services/gopt
```

Sau đó deploy commit mới để tạo lại API/worker/GOPT/Ollama với Compose mới.
Nếu chưa build lại GOPT, quota CPU/RAM vẫn được gỡ sau deploy nhưng PyTorch
trong image cũ còn ép một luồng. `.env` workspace đã được dọn các biến hạn
mức, không đưa vào Git và không thay thế toàn bộ credential production.

Kiểm tra trên Docker host:

```bash
docker inspect --format '{{.Name}} CPU={{.HostConfig.NanoCpus}} quota={{.HostConfig.CpuQuota}} RAM={{.HostConfig.Memory}} swap={{.HostConfig.MemorySwap}}' oral-assessment-web-ollama-1 oral-assessment-web-worker-1 oral-assessment-web-gopt-1
docker stats --no-stream oral-assessment-web-ollama-1 oral-assessment-web-worker-1 oral-assessment-web-gopt-1
```

`NanoCpus=0`, `Memory=0` nghĩa là Docker không đặt các hạn mức đó, không phải
không được dùng tài nguyên. Vẫn chịu tài nguyên thực tế và giới hạn từ host/
Docker daemon nếu có. Bản cập nhật không tự bật dịch vụ AI đang tắt.

## Jenkins Docker báo `python3: not found`

Lỗi tại **Preflight**, exit code `127`, nghĩa là môi trường chạy agent thiếu Python. Nếu log ghi `Running on Jenkins` / `(built-in)` và Jenkins chạy bằng Docker, phải cài Python **trong container Jenkins**, không chỉ trên host. Pipeline dùng Python ở cả kiểm thử cleanup, snapshot, deploy và dọn image nên không bỏ dòng kiểm tra để xử lý lỗi này.

Trên máy chủ đang chạy container Jenkins, tìm tên container:

```bash
docker ps --format 'table {{.Names}}\t{{.Image}}'
```

Với image Jenkins nền Debian/Ubuntu, thay `TEN_CONTAINER_JENKINS` bằng tên vừa tìm rồi chạy:

```bash
docker exec -u 0 TEN_CONTAINER_JENKINS sh -c 'apt-get update && apt-get install -y --no-install-recommends python3'
docker exec TEN_CONTAINER_JENKINS sh -c 'python3 --version && docker compose version && docker buildx version && docker info --format "{{.ServerVersion}}"'
```

Nếu image nền Alpine (không có `apt-get`), dùng `apk add --no-cache python3` thay cho lệnh cài bằng apt. Sau khi kiểm tra thành công, chạy lại **Build Now**. Không cần khởi động lại Jenkins chỉ để nhận lệnh Python mới.

Lệnh `docker exec` sửa container hiện tại; Python sẽ mất khi **tạo lại container từ image cũ**. Để giữ lâu dài, thêm vào Dockerfile Jenkins hiện đang dùng (giữ nguyên các bước cài Docker CLI, Compose và Buildx):

```dockerfile
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 \
    && rm -rf /var/lib/apt/lists/*
USER jenkins
```

Build lại image Jenkins và cập nhật service Jenkins dùng image đó, giữ cấu hình volume `/var/jenkins_home` và kết nối Docker hiện tại. Nếu Dockerfile dùng user agent khác, trở về user đó thay cho `jenkins`. Đây là cách [Jenkins hướng dẫn bổ sung công cụ vào image](https://github.com/jenkinsci/docker#installing-more-tools).

Kiểm tra dòng `Checking out Revision ... (refs/remotes/origin/...)`: nếu job lấy **`Staging`**, thay đổi chỉ push lên `main` chưa chắc được dùng. Merge commit cần triển khai vào `Staging` theo quy trình hiện tại hoặc sửa nhánh SCM của job theo chủ đích.

## Chạy một bản cập nhật

1. Commit và push thay đổi lên nhánh mà job theo dõi.
2. Mở job Jenkins, bấm **Build Now** nếu job chưa được webhook kích hoạt.
3. Trong **Console Output**, kiểm tra bước **Checkout** lấy đúng commit mong muốn.
4. Theo dõi các bước **Prepare Docker builder → Build MinIO → Build API → Test API - isolated SQLite → Build and check web → Deploy Oral web → Clean old Docker releases**.
5. Khi job báo `SUCCESS`, mở web quản trị và đăng nhập kiểm tra. Đóng rồi mở lại desktop để tải giao diện server mới.

Test API lỗi sẽ chặn các bước build web và deploy tiếp theo. Không coi việc push thành công hoặc bước build image thành công là đã triển khai xong.

## Giữ hai phiên bản và dọn Docker sau deploy

Sau khi web/API qua healthcheck và worker chạy đúng image của build mới, stage **Clean old Docker releases** tự động:

- Giữ tối đa **2 phiên bản image API** (`oral-assessment-api`) và **2 phiên bản image web** (`oral-assessment-web`): bản vừa deploy và bản đang chạy trước đó. API dùng chung cho worker/migration. Nếu không có bản trước khác biệt còn tồn tại, lấy thêm image gần nhất theo thời gian tạo; các tag cùng ID tính là một phiên bản.
- Xóa container đã dừng của project `oral-assessment-web`, container kiểm thử do pipeline tạo, image build/check cũ và image không còn tag có nhãn sở hữu OralAI.
- Giữ cache của builder riêng `oral-assessment-web-jenkins` (driver `docker-container`) để tái sử dụng dependency. Dọn cache không được dùng trong **168 giờ**, sau đó dọn theo dung lượng với mục tiêu **10 GB**, ưu tiên bỏ cache ít được dùng gần đây. Hai lượt dọn riêng biệt để giới hạn dung lượng vẫn áp dụng cho cache mới. Cache đang được dùng có thể không dọn được; đây không phải giới hạn cứng cho toàn bộ Docker disk. Pipeline build bằng `buildx --load` để image có sẵn cho kiểm thử/deploy.
- In `docker system df` để theo dõi dung lượng sau dọn.

Pipeline chụp ID/reference của image đang chạy ngay trước bước deploy vào `.data/jenkins/previous-images.json`, gắn với đúng build. Image còn được bất kỳ container nào sử dụng sẽ được giữ; khi đó số phiên bản có thể lớn hơn hai và cần kiểm tra container đó. Các image hạ tầng PostgreSQL/Redis/MinIO, volume dữ liệu, backup database và tài nguyên thuộc project khác được giữ nguyên. Không dùng `docker system prune`, không xóa volume và không ép xóa image/container trong bước dọn.

Stage dọn chỉ chạy sau deploy thành công. Nếu dọn gặp lỗi hoặc phát hiện ứng dụng không còn khỏe/đúng image, Jenkins báo **UNSTABLE** để kiểm tra; ứng dụng đã deploy tiếp tục chạy. Nếu build/deploy thất bại, pipeline chỉ dọn container test và image check của chính lượt chạy đó trong `post always`.

Theo [Docker Buildx prune](https://docs.docker.com/reference/cli/docker/buildx/prune/), thao tác dọn áp dụng cho builder được chọn. Cache ở builder dùng chung từ các lượt build trước cần được quản trị riêng vì Docker không phân loại cache đó theo project. Từ bản sửa **26/10/2026**, không dùng `prune --all --force` không giới hạn sau mỗi deploy. Script dùng `--max-used-space` hoặc `--keep-storage` trên Buildx cũ; nếu không hỗ trợ cả hai, giữ cache và báo lỗi cleanup (UNSTABLE), không quay về xóa hết. Các giá trị nằm trong `CACHE_MAX_AGE` / `CACHE_MAX_SIZE` của script. Chỉ một job Jenkins nên quản lý deployment và builder này; `disableConcurrentBuilds()` tuần tự hóa các lượt của job đó.

Giữ image trước hỗ trợ thao tác khôi phục ứng dụng, nhưng không tự rollback schema/database. Người vận hành cần kiểm tra tương thích migration trước khi đổi về phiên bản trước.

Logic dọn nằm trong [docker_cleanup.py](../scripts/docker_cleanup.py), được kiểm tra bằng `python3 -m unittest discover -s tests -p test_docker_cleanup.py -v`. Các test dùng Docker giả lập, không dọn dữ liệu thật.

## Giảm thời gian CI/CD — 26/10/2026

- **Cache API/web:** dependency đã được cài ở các layer trước khi copy source. Giữ cache giúp không phải cài lại pip/npm khi chỉ đổi code; chỉnh lockfile vẫn cài lại đúng dependency. Không bỏ test API, lint/typecheck, backup, migration hay healthcheck.
- **MinIO:** [build_minio.py](../scripts/build_minio.py) tính SHA-256 từ tên, quyền và nội dung file trong `services/minio`, so với nhãn `uk.paperlens.oral.minio-source` của image. Có image đúng nhãn thì dùng lại; thiếu image, thiếu nhãn hoặc đổi đầu vào thì build lại. Cả hai nhánh đều chạy `minio --version`. Image cũ chưa có nhãn sẽ build lại một lần. Khi cần cập nhật base image dù source không đổi, người vận hành rebuild MinIO theo quy trình cập nhật hạ tầng; nhãn này không kiểm tra bản mới của upstream/base image.
- **Pull:** PostgreSQL/Redis được pull một lần ở stage **Check infrastructure images**; deploy kiểm tra image đã có trước khi dừng ứng dụng, dùng `--pull never`. Ollama vẫn có bước pull riêng khi bật; model chỉ tải khi chưa có trong volume.
- **Đo thời gian:** build dùng `--progress=plain` để thấy `CACHED` và thời gian từng bước; các lệnh triển khai qua helper `command()` in nhãn thao tác cùng thời gian chạy, không in command/env/output có thể chứa bí mật. Dùng Stage View và Console Output để so sánh.

Lượt đầu sau sửa có thể vẫn chậm vì cache cũ đã bị xóa. So sánh với lượt tiếp
theo khi lockfile và đầu vào MinIO không đổi; không cam kết số phút trước khi
đo trên Jenkins thật. Cache được giữ sẽ dùng thêm dung lượng đĩa so với cách
xóa hết trước đây; kiểm tra cả dung lượng image, volume và backup độc lập.

## Chẩn đoán lỗi

| Bước lỗi | Cách kiểm tra |
| --- | --- |
| Checkout | Nhánh/commit, quyền đọc repo và credential SCM |
| Preflight | Docker agent, Compose, network `nginx-network` và các Dockerfile |
| Build API / web | Dòng lỗi đầu tiên của lệnh build, dependency và kết nối tải package |
| Test API | Tên ca `FAILED`, lỗi trước HTTP 500 và báo cáo JUnit; đối chiếu commit đã checkout |
| Deploy | Thông báo kiểm tra domain, cổng, credential, migration hoặc trạng thái dịch vụ |
| Clean old Docker releases | Image/container còn được sử dụng, trạng thái healthcheck và quyền truy cập builder OralAI |

Đối chiếu lỗi đầu tiên và phần tổng kết `FAILED` trước khi chỉnh cấu hình.

Pipeline không tự downgrade database hoặc rollback khi deploy thất bại. Giữ volume dữ liệu để kiểm tra và khắc phục. Không xóa volume để xử lý lỗi test.

## Cập nhật desktop sau server

- **Chỉ đổi web/API:** triển khai server rồi mở lại desktop.
- **Đổi Electron/preload:** người chạy source cập nhật repo, chạy `npm ci` khi dependency đổi rồi mở lại app. Người dùng bộ cài cần bản desktop mới.
- **Đổi helper/model STT:** build lại bundle và bộ cài theo [hướng dẫn đóng gói](desktop-build.md).

Push lên `main` không tự tạo bộ cài: vào GitHub Actions → **Desktop installers → Run workflow**, chọn nhánh cần build rồi tải artifact đúng hệ điều hành.
