# TASK M4 — Nguyễn Ngọc Tuyết Ngân

## A. Mục tiêu cá nhân

**Vai trò:** Gitleaks, Source Security, Scanner Integrity và Evidence Producer.

Xác nhận source-security producer đã merge tương thích canonical emitter/consumer và chỉ bổ sung behavior thực sự thiếu. PR15 đã merge theo metadata28/10 trong handoff: không giao lại việc resolve EOL conflict cũ hoặc sửa lịch sử PR đã merge.

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

Trước hết đọc [HANDOFF-NGAN.md](https://github.com/dec2609/m4-golden-lab-reference/blob/31fdb6e8fc51a08aa94e8d9d386cb970019676fc/M4-TEAM-HANDOFF/HANDOFF-NGAN.md) của mình. Sau đó đọc các mục sau tại source/evidence pin; không cần xin đường dẫn máy local của Thuận.

| File tại reference | Cần lấy thông tin gì |
|---|---|
| [candidate/scripts/source_security.py](https://github.com/dec2609/m4-golden-lab-reference/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/candidate/scripts/source_security.py) | main/run_scan, context, scopes, integrity và emitter call. |
| [candidate/tests/test_source_security.py](https://github.com/dec2609/m4-golden-lab-reference/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/candidate/tests/test_source_security.py) | Existing source-security suite. |
| [candidate/tests/test_reference_source.py](https://github.com/dec2609/m4-golden-lab-reference/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/candidate/tests/test_reference_source.py) | Negative behavior tham khảo, không tên test bắt buộc. |
| [patches/ngan.patch](https://github.com/dec2609/m4-golden-lab-reference/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/patches/ngan.patch) | Source-producer/caching hunks, không whole PR15. |
| [evidence/gitleaks-download.json](https://github.com/dec2609/m4-golden-lab-reference/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/evidence/gitleaks-download.json) | Historical approved-version archive hash check. |
| [evidence/frozen-source-run/gitleaks-execution.json](https://github.com/dec2609/m4-golden-lab-reference/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/evidence/frozen-source-run/gitleaks-execution.json) | Metadata/error execution record. |
| [evidence/frozen-source-run/gitleaks-result.json](https://github.com/dec2609/m4-golden-lab-reference/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/evidence/frozen-source-run/gitleaks-result.json) | Historical ERROR không security approval. |
| [evidence/linux-source-run/source-security/run_manifest.json](https://github.com/dec2609/m4-golden-lab-reference/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/evidence/linux-source-run/source-security/run_manifest.json) | Linux dirty-context attempt; không clean scanner PASS. |

Các source paths trong cột đầu bỏ tiền tố `candidate/` là path đích trong repo nhóm khi tương ứng đã có. Patches không là file phải đưa vào implementation PR. Reference evidence là lịch sử, không kết quả đã chạy trên branch bạn. Source pin và publication SHA nêu trên bất biến; current main có thể đã thay đổi.

## D. Công việc cần thực hiện theo thứ tự

### D.1. Kiểm trạng thái công việc hiện tại

**Thực hiện:** Xác nhận PR15 merge trên GitHub và branch/HEAD đang làm. Nếu chưa cần code change, không tạo PR/code churn chỉ để có task mới; lập checklist/evidence đã đáp ứng.

**Đầu ra để chuyển bước:** Baseline SHA và difference so main; tránh duplicate implementation đã có trong PR12/main.

### D.2. Đối chiếu source context/scopes

**Thực hiện:** Đích source_security.py::get_repo_context/run_scan/main hoặc equivalent. Đo full HEAD/snapshot, dirty/shallow; scan FULL_HISTORY_AND_WORKTREE. Tool cache/output ngoài measured checkout, không bỏ history hoặc tắt clean guard để PASS.

**Đầu ra để chuyển bước:** Measured context và hai per-scope raw commands/exits/reports cùng run; unknown/dirty/shallow không PASS.

### D.3. Đối chiếu scanner integrity

**Thực hiện:** Đích install/approved_executable/verify_binary_integrity. Kiểm archive theo pin đã duyệt, executable bytes riêng từ verified archive, actual version và corrupt-cache rejection. Không lấy archive hash làm executable hash hoặc thay tool rồi khai version cũ.

**Đầu ra để chuyển bước:** Unit negatives + actual tool metadata nếu có; pin/reference là snapshot, không approval mới.

### D.4. Kiểm outcome và report

**Thực hiện:** Actual raw exits là int không bool; findings kể cả raw0 phải FAIL; missing scanner/install/platform/report/execution error là ERROR/nonzero hoặc rawnull nếu chưa chạy. Validate report list, path và hash, không tự tạo [] thay report thiếu.

**Đầu ra để chuyển bước:** PASS/FAIL/ERROR matrix và finding_count/reason chính xác; legacy FAIL không tự chứng minh có secret finding.

### D.5. Nối canonical emitter của Trâm

**Thực hiện:** Dùng shared adapter PR/SHA do Trâm cung cấp, không fork. main gọi emit_control GITLEAKS: scope/head_commit/dirty/shallow/raw_exit_codes/scanner_integrity, tool và flat producer argv. Execution subject=source; artifact_subject=null; per-scope argv nằm raw manifest.

**Đầu ra để chuyển bước:** Actual producer main→emitter không TypeError; pair gitleaks-execution.json/gitleaks-result.json đủ metadata, đúng source/run/path/hash.

### D.6. Kiểm consumer boundary và affected tests

**Thực hiện:** Phối hợp Quang đọc đúng normalized files, Trâm validator reject mismatch; chạy unit và actual-call test khi có dependencies. Scanner double chỉ là handoff test, không actual scan.

**Đầu ra để chuyển bước:** Evidence type phân biệt; missing/wrong source/run/subject/hash/tool records không approve, không sửa Production Gate để tests qua.

### D.7. Bổ sung nhỏ nếu cần và lưu kết quả

**Thực hiện:** Chỉ sửa source-security/tests/config owned của Ngân; preserve integrity/scopes đã đúng. Nếu real pinned Linux scan khả thi trên source sạch/full-history, run mới ngoài checkout; không tự download/đổi pin hoặc dùng secret fixture thật. Nếu chưa đủ điều kiện ghi blocker.

**Đầu ra để chuyển bước:** Không regression đã biết; code/evidence đúng scope, PR follow-up chỉ nếu có thay đổi cần thiết.

## E. Kiểm thử và evidence

Giữ raw reports đã redact phù hợp, commands/exits/version/archive+executable hashes và source/run. Actual history scan có thể tìm historical findings: báo findings/remediation scope, không thêm ignores để xanh. Missing tool/scanner ERROR bị chặn là expected fail-closed, không positive clean scan. Trước actual scan cần full-history clean checkout và agreed pin/context; thiếu adapter hoặc context ghi DEPENDENCY_PENDING/NOT_VERIFIED, không invent identity.

**Lệnh chọn lọc khi thực sự cần xác minh hoặc sau thay đổi:**

```bash
python -B -m pytest -q -p no:cacheprovider tests/test_source_security.py
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

Nếu PR15 đã merge và có code change mới, dùng follow-up branch từ main mới nhất, ví dụ fix/m4-ngan-contract; nếu branch này/công việc đã tồn tại thì tiếp tục, không tạo lại hoặc reset. Không replay old PR15 hoặc EOL-only changes ở workflow/Compose/policy/gate-tests. Nếu không cần code change, chỉ gửi evidence và PR tài liệu NGAN.md. Mọi PR vào repo nhóm; không sửa branch Trâm/Quang hoặc adapter riêng.

Review diff/file list và stage explicit paths thuộc mình trước commit/push. PR vào **repo nhóm** có source SHA, tests/evidence/limits và shared changes cần owner review. Không merge main, không push/mời cộng tác vào repo tham chiếu. Mọi thay đổi implementation chính thức nằm ở repo nhóm, không trong clone Golden Lab.

## G. Báo cáo cá nhân A–J

Hoàn thiện **`docs/report-input/NGAN.md`** trong repository nhóm, có thể viết song song với các bước kỹ thuật. Không thay `TEMPLATE.md`, file của người khác hoặc `docs/bao-cao.md`; Thuận tổng hợp báo cáo chính sau.

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

- [ ] Producer/emitter tương thích đúng adapter commit, không TypeError trong actual boundary đã kiểm.
- [ ] Integrity/scope/raw exits/report semantics đúng; scanner lỗi/missing không PASS.
- [ ] Tests/evidence cho các cases đã chạy, không regression đã biết; real scan chưa có công khai blocker.
- [ ] NGAN.md A–J hoàn thiện; PR code chỉ nếu còn thay đổi cần thiết, không duplicate công việc đã merge.

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
Report input docs/report-input/NGAN.md A–J đã điền / phần còn thiếu:
Việc Thuận cần kiểm khi tích hợp / bug cần quyết định:
```

Task completion chỉ áp dụng phạm vi đã kiểm và evidence đã bàn giao; **không tự là nghiệm thu full runtime M4 hoặc production-ready**.
