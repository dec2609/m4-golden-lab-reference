# OrderFlow D1 — controlled real-stack E2E

D1 kiểm Browser → Vite /api → Flask → PostgreSQL. Happy-path không routing/interception.
Chỉ chạy hai service backend/DB từ Compose hiện có; không frontend container, release pipeline, registry/deploy/rollback.

## Phạm vi và dữ liệu

- @playwright/test ghim 1.64.1, Edge channel msedge đã cài, headless, một worker, retries = 0. Không tải Chromium.
- Python runner chỉ dùng standard library. Docker Desktop và quyền truy cập engine phải sẵn sàng.
- Mỗi run tạo project orderflow-d1-<UTC>-<suffix>, network và named volume riêng. Nếu resource đã tồn tại, preflight/up từ chối reuse.
- App bind loopback 8081; Vite loopback 5173. Vite bỏ inherited VITE_* để dùng /api proxy mặc định; nếu có frontend .env* runner dừng để review.
- Tạo ba row tổng hợp có marker run ID: -api, -browser, -uncertain-post. Mock/invalid requests không được tạo thêm row.
- Giữ volume, containers đã dừng, network, image và toàn bộ evidence sau test. Không dùng make down, down -v, prune hoặc reset dữ liệu.
- Dùng npm.cmd trên PowerShell nếu npm.ps1 bị execution policy chặn; không thay execution policy.

## Khởi tạo và D1-A

Chạy từ repository root. Các lệnh build/service/ghi DB chỉ dùng khi đã được người dùng cho phép.

    $d1Run = (python ma-nguon/orderflow/e2e/d1_environment.py init | ConvertFrom-Json).run_dir
    python ma-nguon/orderflow/e2e/d1_environment.py preflight --run-dir $d1Run
    if ($LASTEXITCODE -ne 0) { throw "Preflight failed; stop." }
    python ma-nguon/orderflow/e2e/d1_environment.py up --run-dir $d1Run
    if ($LASTEXITCODE -ne 0) { throw "Backend startup failed; do not run browser." }

Giữ nguyên giá trị $d1Run được in từ init. Ở terminal thứ hai, đặt cùng đường dẫn đó và chạy:

    python ma-nguon/orderflow/e2e/d1_environment.py vite --run-dir $d1Run

Runner giữ foreground; stdout Vite nằm trong vite.log. Không chạy thêm server khác vào cùng port.
Quay lại terminal thứ nhất:

    python ma-nguon/orderflow/e2e/d1_environment.py api --run-dir $d1Run
    if ($LASTEXITCODE -ne 0) { throw "D1-A failed; do not run browser." }

D1-A kiểm DB mới rỗng, /health, GET direct/proxy, POST 201 qua proxy, GET lại ID, SELECT row thật và 10 invalid payloads trả 400 không đổi row count.
Chưa có /ready không được gọi là DB readiness; SELECT/API assertions chỉ chứng minh trạng thái tại thời điểm đo.
Không đổi credentials hoặc log resolved Compose environment. Runner chỉ ghi summary config và redact password trong logs.

## D1-B: Edge suite

Nếu dependencies đã được cài đúng lockfile, không cần cài lại. Lần bổ sung D1 dùng:

    npm.cmd install --save-dev --save-exact @playwright/test@1.64.1 --ignore-scripts --no-audit --no-fund

Lệnh trên thay package.json/lockfile/node_modules và npm cache, thêm ba packages khoảng 18 MB giải nén, không tải browser.
Muốn cài trên máy khác cần quyền cài dependency; không tự chạy playwright install. Nếu Edge không launch được, ghi BLOCKED.

Từ frontend:

    $env:D1_RUN_DIR = $d1Run
    npm.cmd run test:e2e

Config từ chối chạy nếu api-results.json chưa PASS hoặc browser-results.json đã tồn tại, để không ghi đè evidence.
Chạy lại cần init một run mới và preflight tài nguyên mới; không tự tái sử dụng volume cũ.
JSON report, traces, screenshot và HTTP observations nằm trong run folder, không trong M3.

Bảy tests bao phủ mười scenario yêu cầu D1:

| Test | Loại bằng chứng |
|---|---|
| UI create → list → detail → reload → fresh context | REAL, không interception; POST 201 và GET thật |
| Mock Empty create → list → detail | MOCK lifecycle, kiểm không POST và DB không đổi |
| Live response chậm → Mock → Live | SIMULATED latency, giữ response GET thật; không stale overwrite |
| Backend unavailable | SIMULATED connection refusal; không stop backend thật |
| Timeout GET | SIMULATED stalled response, adapter timeout 10 giây thật |
| POST response mất sau commit | POST thật được 201 rồi response bị chặn; UI uncertain, một POST/một row |
| Invalid UI input | Client validation; không POST, không success |

Routing chỉ xuất hiện trong ba nhóm fault: latency, unavailable/timeout và response loss. Happy-path không dùng mock/interception.
Không suy ra outage/recovery thật từ simulated network failure. Không retry POST khi kết quả chưa xác định.
Test no-retry kiểm một submit và cửa sổ quan sát 1,5 giây sau lỗi; không khẳng định có idempotency phía server.

## D1-C và cleanup luôn cần thực hiện

Từ repository root, trước khi dừng:

    python ma-nguon/orderflow/e2e/d1_environment.py db-verify --run-dir $d1Run

Lệnh đối chiếu PostgreSQL với attachments browser, kể cả timestamps; thu versions, local image IDs và logs redacted.
Nếu browser suite chưa chạy/FAIL, không tự tạo database verification PASS; giữ lỗi và thực hiện cleanup.

Luôn dừng chỉ resources của run, kể cả khi assertions fail:

    python ma-nguon/orderflow/e2e/d1_environment.py stop-vite --run-dir $d1Run
    python ma-nguon/orderflow/e2e/d1_environment.py cleanup --run-dir $d1Run

stop-vite kiểm PID + exact Vite entry/port trước khi dừng process tree; hữu ích khi Ctrl+C không ngắt Python wait trên Windows.
Node có thể trả exit 1 do chủ động terminate; đây là controlled cleanup, không đổi thành test failure hay che raw exit.
cleanup chỉ compose stop hai service thuộc project; không down/remove. Kiểm lại port, volume và prior sandbox state trong evidence.
Nếu chưa tạo resource do preflight thất bại, không chạy cleanup sang project khác; xử lý nguyên nhân rồi init run mới.

## Kiểm tra frontend bổ sung không ghi đè evidence M3

Chạy từ ma-nguon/orderflow:

    npm.cmd test
    node node_modules/typescript/bin/tsc --noEmit --module ESNext --moduleResolution Bundler --target ES2022 --lib ES2023,DOM --types node --skipLibCheck e2e/orders.spec.ts playwright.config.ts

npm test mặc định không --write-evidence; output Phase B chỉ mô tả unit/contract/SSR. Những dòng integration NOT_RUN trong runner đó không phủ định report D1 riêng.
Không chạy test:m3 hoặc make verify cho D1 vì có thể ghi evidence lịch sử/DB ngoài run.

## Evidence và giới hạn

Mỗi run: baseline.json (HEAD/branch/dirty/hash inventory), commands.jsonl (raw exits), sanitized Compose summary, preflight/startup/logs,
api-results.json, browser-command.json, browser-results.json + trace attachments, database-after-browser.json, runtime-versions.json,
vite.json/vite-cleanup.json, cleanup.json và checks bổ sung. Báo cáo tổng hợp phải dựa trên các file này, ghi hash và phiên bản source hiện hành.

PASS cần D1-A + browser + DB verification + cleanup/provenance đạt. Chỉ API PASS là PARTIAL; browser launch không được là BLOCKED.
Không gọi kết quả này là production-ready, verified release, deployment hay rollback. /ready, quantity upper bound, trusted release ingestion,
production reverse proxy/three-container topology và release gates vẫn thuộc scope tiếp theo của owners.

Tham chiếu cấu hình Edge/retries/workers: https://playwright.dev/docs/browsers và https://playwright.dev/docs/test-configuration .
