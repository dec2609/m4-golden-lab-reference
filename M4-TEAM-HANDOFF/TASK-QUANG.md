# TASK M4 — Nguyễn Minh Quang

## A. Mục tiêu cá nhân

**Vai trò:** Production Gate, Release Workflow, Artifact Identity, Signing/Verification, Deployment/Rollback.

Hoàn thiện phần gate và release orchestration trên code hiện tại của repo nhóm theo contract; chỉ sửa defect/integration gap còn tồn tại. Không ghép nguyên candidate hoặc tự viết lại producer của Trâm/Ngân.

## B. Chuẩn bị môi trường và clone reference

1. Bạn chỉ cần TASK này, HANDOFF của mình và contract/repo chính thức; không cần TASK của người khác.
2. Clone repository tham chiếu **Private** ở thư mục riêng. Nếu403/404, nhờ Thuận cấp quyền đọc, không đổi sang tài khoản/organization khác hoặc dùng token trong URL.

```bash
git clone https://github.com/dec2609/m4-golden-lab-reference.git m4-golden-lab-reference
```

- Publication commit: `31fdb6e8fc51a08aa94e8d9d386cb970019676fc`.
- Source/evidence reference commit: `4c35990241e96f8d1d35de7e2615e12c55cf673b`.
- Contract **m4-contract-1.0**: commit `9f1469f64d6a9ae8d5ef4b2758e878a2dfed5e1d` tại [PR17](https://github.com/UEH-CSS-26C/CSS-26C-N08-SaiGon-Continental/pull/17).
- Repository chính thức: [https://github.com/UEH-CSS-26C/CSS-26C-N08-SaiGon-Continental](https://github.com/UEH-CSS-26C/CSS-26C-N08-SaiGon-Continental).

**Golden Lab là kho tham khảo, không phải nơi sửa/nộp implementation. Không push code của bạn vào Golden Lab.** Candidate SHA local cũ không thay main của nhóm; không copy cả candidate, không cherry-pick assembled commit hoặc áp nguyên owner patch. So behavior với code hiện tại, giữ phần đã hoàn thành có evidence tương đương. Helpers/tests có thể khác tên.

3. Mở checkout repo nhóm **khác** với reference. Nếu chưa có checkout, clone repo nhóm vào thư mục mới; không clone đè thư mục đang có. Kiểm remote/status/branch/HEAD trước sửa. Commands dưới dùng Bash/Git Bash; ghi môi trường thực tế, không chạy chúng trong clone reference.
4. Đọc [contract](https://github.com/UEH-CSS-26C/CSS-26C-N08-SaiGon-Continental/blob/9f1469f64d6a9ae8d5ef4b2758e878a2dfed5e1d/docs/m4-contract/CONTRACT.md), [schema](https://github.com/UEH-CSS-26C/CSS-26C-N08-SaiGon-Continental/blob/9f1469f64d6a9ae8d5ef4b2758e878a2dfed5e1d/docs/m4-contract/SCHEMA.md), [workflow](https://github.com/UEH-CSS-26C/CSS-26C-N08-SaiGon-Continental/blob/9f1469f64d6a9ae8d5ef4b2758e878a2dfed5e1d/docs/m4-contract/WORKFLOW.md), [acceptance](https://github.com/UEH-CSS-26C/CSS-26C-N08-SaiGon-Continental/blob/9f1469f64d6a9ae8d5ef4b2758e878a2dfed5e1d/docs/m4-contract/ACCEPTANCE.md). Contract là chuẩn bắt buộc; implementation reference chỉ là ví dụ.

## C. Những file cần đọc

Trước hết đọc [HANDOFF-QUANG.md](https://github.com/dec2609/m4-golden-lab-reference/blob/31fdb6e8fc51a08aa94e8d9d386cb970019676fc/M4-TEAM-HANDOFF/HANDOFF-QUANG.md) của mình. Sau đó đọc các mục sau tại source/evidence pin; không cần xin đường dẫn máy local của Thuận.

| File tại reference | Cần lấy thông tin gì |
|---|---|
| [candidate/scripts/production_gate.py](https://github.com/dec2609/m4-golden-lab-reference/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/candidate/scripts/production_gate.py) | Đối chiếu evaluate_gate/main, exact status, security_approved và release JSON. |
| [candidate/scripts/artifact_security.py](https://github.com/dec2609/m4-golden-lab-reference/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/candidate/scripts/artifact_security.py) | Build-once artifact, measured digests và signing CLI. |
| [candidate/scripts/verify_registry.py](https://github.com/dec2609/m4-golden-lab-reference/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/candidate/scripts/verify_registry.py) | Index/platform/config và actual registry verification. |
| [candidate/scripts/run_m4_workflow.py](https://github.com/dec2609/m4-golden-lab-reference/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/candidate/scripts/run_m4_workflow.py) | Canonical M4 call sequence, guards và failure propagation. |
| [candidate/.github/workflows/verify.yml](https://github.com/dec2609/m4-golden-lab-reference/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/candidate/.github/workflows/verify.yml) | Workflow arguments/paths và điều kiện chạy từng bước. |
| [candidate/scripts/deploy_staging.py](https://github.com/dec2609/m4-golden-lab-reference/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/candidate/scripts/deploy_staging.py) | Readiness/status/body và command failure. |
| [candidate/scripts/test_rollback.py](https://github.com/dec2609/m4-golden-lab-reference/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/candidate/scripts/test_rollback.py) | Previous approved immutable identity và rollback failure. |
| [candidate/tests/test_production_gate.py](https://github.com/dec2609/m4-golden-lab-reference/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/candidate/tests/test_production_gate.py) | Gate regression; tên test cụ thể không bắt buộc giống reference. |
| [patches/quang.patch](https://github.com/dec2609/m4-golden-lab-reference/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/patches/quang.patch) | Đọc từng hunk theo ownership; không tự git apply nguyên patch. |
| [evidence/frozen-source-run/run-summary.json](https://github.com/dec2609/m4-golden-lab-reference/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/evidence/frozen-source-run/run-summary.json) | Historical dependency/unit PASS nhưng source ERROR bị block. |
| [evidence/actual-gate-source-only.json](https://github.com/dec2609/m4-golden-lab-reference/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/evidence/actual-gate-source-only.json) | Historical source-only input bị reject, không positive release. |

Các source paths trong cột đầu bỏ tiền tố `candidate/` là path đích trong repo nhóm khi tương ứng đã có. Patches không là file phải đưa vào implementation PR. Reference evidence là lịch sử, không kết quả đã chạy trên branch bạn. Source pin và publication SHA nêu trên bất biến; current main có thể đã thay đổi.

## D. Công việc cần thực hiện theo thứ tự

### D.1. Chốt baseline của mình

**Thực hiện:** Ghi branch/PR, HEAD40, main base và shared adapter commit đang dùng. Kiểm tra PR12/branch m4-quang hiện tại; không suy implementation đã đúng/sai từ metadata hay count.

**Đầu ra để chuyển bước:** Bảng baseline và checklist behavior: đã có evidence / cần kiểm / thực sự cần sửa.

### D.2. Đối chiếu gate approval

**Thực hiện:** Đích scripts/production_gate.py::evaluate_gate/main/clean_status hoặc functions tương đương. Gọi validate_control rồi đọc assessment.security_approved rõ ràng; không bool(assessment), không đổi evidence_valid=True thành control PASS.

**Đầu ra để chuyển bước:** Positive control PASS hợp lệ có thể approve; valid FAIL/ERROR và invalid evidence không approve; có test chỉ đúng consumer path.

### D.3. Kiểm negative evidence

**Thực hiện:** Probe wrong execution subject, missing tool/execution, boolean raw exit, wrong source/run/hash/artifact digest, empty/malformed report, BYPASS/NOT_PASS và fixture-like names. Lỗi validation phải map control FAIL/global BLOCKED, không legacy fallback.

**Đầu ra để chuyển bước:** Fresh minimal reproduction hoặc test mapping chứng minh từng nhóm; control probe không được gọi là entire release bypass.

### D.4. Kiểm identity và trust

**Thực hiện:** Đích artifact_security.py, verify_registry.py và artifact helpers shared adapter. Tách archive SHA, OCI index, platform manifest, config/layer digests; kiểm source fingerprint/run, immutable reference và provenance cùng build. Cosign verify đúng archive với independently approved key pin; không producer literal PASS hoặc tự approve key.

**Đầu ra để chuyển bước:** Identity mapping và negative tests; actual signing/registry chưa có prerequisite thì ghi NOT_VERIFIED + input cần operator.

### D.5. Nối shared producers

**Thực hiện:** Nhận canonical adapter từ PR/commit của Trâm; dùng Gitleaks producer đã merge của Ngân. Kiểm actual producer CLI → pair execution/result → validate_control → gate trên đúng versions; scanner double phải được ghi nhãn. Không giữ adapter copy riêng.

**Đầu ra để chuyển bước:** Không TypeError/signature mismatch; valid scanner ERROR vẫn chặn; ghi dependency PR/SHA cụ thể.

### D.6. Đối chiếu workflow/CLI

**Thực hiện:** Đích scripts/run_m4_workflow.py hoặc canonical equivalent, .github/workflows/verify.yml, Makefile. Kiểm actual supported --candidate/--run-dir/--trusted-key-sha256; no M3 paths/literal security PASS. Source → build-once → sign/verify → signed preflight → scan → gate. Không rebuild giữa scan/sign/deploy.

**Đầu ra để chuyển bước:** CLI/help/import + workflow/static checks hoặc local source-phase logs; không gọi đó CI PASS.

### D.7. Rà release boundaries

**Thực hiện:** Đích deploy_staging.py/test_rollback.py: gate BLOCKED không deploy; ready cần HTTP200 + status=ready/database=connected; command errors nonzero/FAIL. Rollback chỉ previous approved immutable artifact, thiếu approval thì NOT_RUN/BLOCKED. Giữ resource guards và DB volumes.

**Đầu ra để chuyển bước:** Affected contracts/negative tests; positive actual deployment/rollback chỉ khi có môi trường riêng được phép.

### D.8. Sửa nhỏ và kiểm lại

**Thực hiện:** Chỉ sửa những behavior còn sai trên current SHA; review shared adapter hunks cùng Trâm. Rerun affected tests, ghi scope/limitations và evidence mới. Không ép source giống private helper layout trong candidate.

**Đầu ra để chuyển bước:** Không regression đã biết trong phạm vi kiểm; diff đúng ownership, không thay backend/frontend/contract.

## E. Kiểm thử và evidence

Unit/contract positive với mocked Cosign/scanners chỉ chứng minh logic. Actual release positive cần same-source/candidate/run, approved key/pin, registry/scanners và gate0 thật. Thiếu prerequisite thì ghi NOT_VERIFIED, không thay bằng fixture/historical PASS. Docker/Compose/staging/rollback chỉ chạy sau khi xác nhận project/ports/volumes riêng và được phép; không production credentials hoặc shared deployment.

**Lệnh chọn lọc khi thực sự cần xác minh hoặc sau thay đổi:**

```bash
python -B -m pytest -q -p no:cacheprovider tests/test_production_gate.py tests/test_artifact_security.py
M4_CONTRACT_IMPLEMENTATION="$PWD" python -B -m pytest -q -p no:cacheprovider tests/contracts
git diff --check
```

Không chạy lại suite đã có log đúng SHA nếu không đổi code hoặc còn concern chưa giải quyết. Kiểm tên file/tests tồn tại trước khi gọi; thiếu coverage thì bổ sung test đúng behavior trong owned suite, không bắt port `tests/test_contract_freeze.py` hoặc ép count giống sandbox. Không sửa assertions/xóa tests để che lỗi. Với tests/contracts, schema-only run không có implementation path có thể skip implementation tests; không dùng nó làm conformance PASS.

| Case / ID | Mục tiêu và oracle | Command / môi trường | Actual exit / HTTP / counts | Layer | Evidence / source SHA / run / hash | Verdict / limit |
|---|---|---|---|---|---|---|
| [Bạn điền] | | | | static / unit / contract / double / actual runtime | | PASS / FAIL / NOT_VERIFIED / NOT_APPLICABLE |

Giữ raw evidence cũ; run mới/output/cache ngoài measured source khi contract yêu cầu. Không ghi secret/private key/DSN thật vào log công bố. Golden Lab historical255/17/68/18 hoặc expected negative block không chứng minh current release positive, CI hoặc full M4 PASS. Không chạy full Golden Lab trong task này.

## F. Git/PR trên repository chính thức

Trong checkout **repo nhóm**:

```bash
git remote -v
git status --short
git branch --show-current
git rev-parse HEAD
# Chỉ đồng bộ refs trong checkout của mình khi đã kiểm remote:
git fetch origin main
```

Origin phải trỏ `UEH-CSS-26C/CSS-26C-N08-SaiGon-Continental`, không phải `dec2609/m4-golden-lab-reference`. Dirty/untracked chưa bảo toàn thì dừng mutation hoặc dùng checkout sạch; không reset/clean/force-push, không ghi đè commits hiện có. Fetch không tự merge. Kiểm nội dung `docs/m4-contract` và `tests/contracts` trên main với pin9f1469f; không đòi cùng ancestry nếu squash. Nếu main contract khác nội dung, báo Thuận trước khi đổi interface.

Nếu PR12 vẫn mở và branch m4-quang đang làm, tiếp tục branch đó. Nếu đã merge thì chỉ tạo follow-up branch từ main khi thực sự còn thay đổi; giữ mọi commits/dirty work. Đồng bộ main trong checkout sạch và review từng conflict, không chép cả reference. Gửi implementation PR vào repo nhóm, cùng docs/report-input/QUANG.md hoặc PR tài liệu riêng theo cách nhóm thống nhất. Không tự merge main.

Review diff/file list và stage explicit paths thuộc mình trước commit/push. PR vào **repo nhóm** có source SHA, tests/evidence/limits và shared changes cần owner review. Không merge main, không push/mời cộng tác vào repo tham chiếu. Mọi thay đổi implementation chính thức nằm ở repo nhóm, không trong clone Golden Lab.

## G. Báo cáo cá nhân A–J

Hoàn thiện **`docs/report-input/QUANG.md`** trong repository nhóm, có thể viết song song với các bước kỹ thuật. Không thay `TEMPLATE.md`, file của người khác hoặc `docs/bao-cao.md`; Thuận tổng hợp báo cáo chính sau.

| Mục | Nội dung bạn phải điền |
|---|---|
| A | Họ tên/vai trò, branch/PR, source SHA40, trạng thái implementation và ngày/môi trường |
| B | 100–150 từ: vấn đề phần mình giải quyết, input/output và ranh giới đóng góp |
| C | Thiết kế/module/công cụ và interfaces thực sự có; tách phần dự kiến |
| D | File:function, quyết định và commit triển khai/review/integration; không nhận công của merge toàn bộ code |
| E | Methods, positive/negative cases, commands/exits/counts/HTTP, actual observations và evidence đúng SHA/layer |
| F | Triệu chứng, nguyên nhân, xử lý, verification sau sửa hoặc trạng thái còn mở |
| G | Giới hạn môi trường/coverage/runtime và hướng cải tiến; không biến proposal thành implemented |
| H | 100–150 từ kết luận đóng góp cá nhân có căn cứ, không tự kết luận full M4 READY |
| I | PR/commit/source/log/report/screenshot links, source/run/time và hashes khi có |
| J | AI/LLM thực sự dùng, mục đích/phần hỗ trợ, quyết định của mình/cách kiểm đầu ra, người khai/ngày/xác nhận; không điền giả |

PASS chỉ khi có evidence; thiếu dữ liệu ghi rõ NOT_VERIFIED/NOT_RUN/BLOCKED theo mẫu, không bịa kết quả. Không yêu cầu sửa code chỉ để có nội dung báo cáo. Evidence ngoài repo cần link nhóm đọc được, không chỉ absolute path máy cá nhân.

## H. Tiêu chí hoàn thành và mẫu phản hồi cho Thuận

- [ ] Gate/validator approval semantics và negative cases đúng contract, có evidence đúng SHA.
- [ ] Actual workflow/producer/gate interfaces tương thích trong phạm vi đã kiểm; dependency với Trâm/Ngân được ghi.
- [ ] Artifact/signing/registry/deploy/rollback còn thiếu runtime proof đều công khai, không giả positive.
- [ ] Affected regressions không còn lỗi đã biết; PR đúng scope và QUANG.md A–J hoàn thiện.

**Đầu ra bắt buộc:** branch/PR repo nhóm (PR code nếu có thay đổi cần thiết), source SHA đã kiểm, test commands/counts/exits, evidence paths/hashes, behavior đã đáp ứng/còn thiếu, dependency owner/PR/SHA và report input A–J. Không làm lại phần đã chứng minh tương đương chỉ để khớp reference.

```text
Người thực hiện:
Repository nhóm / Branch / PR URL:
HEAD40 đã test / main base / ngày:
Contract: m4-contract-1.0 @ 9f1469f64d6a9ae8d5ef4b2758e878a2dfed5e1d
Reference publication: 31fdb6e8fc51a08aa94e8d9d386cb970019676fc
Reference source/evidence: 4c35990241e96f8d1d35de7e2615e12c55cf673b
Các bước D đã hoàn thành và file:function/commit tương ứng:
Behavior đã có từ trước và evidence tái sử dụng:
Behavior còn thiếu / khác reference có chủ đích:
Command | exit/HTTP | pass/fail/skip/error | layer:
Evidence paths + source/run/time/hash; redaction:
Dependency chờ ai, PR/SHA/API/input cụ thể:
NOT_VERIFIED/NOT_APPLICABLE/NOT_RUN và lý do:
Report input docs/report-input/QUANG.md A–J đã điền / phần còn thiếu:
Việc Thuận cần kiểm khi tích hợp / bug cần quyết định:
```

Task completion chỉ áp dụng phạm vi đã kiểm và evidence đã bàn giao; **không tự là nghiệm thu full runtime M4 hoặc production-ready**.
