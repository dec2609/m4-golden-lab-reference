# TASK M4 — Nguyễn Thị Phương Trâm

## A. Mục tiêu cá nhân

**Vai trò:** Canonical Adapter/Emitter, Dependency Policy, SBOM/Syft/Trivy, Evidence Normalization.

Tiếp tục implementation đang có, đối chiếu các behavior còn thiếu và bàn giao một canonical adapter commit cho cả Quang/Ngân. Trâm đã báo 17/17 contract, 52/52 adapter/candidate regression và37/37 security regression PASS; giữ kết quả là reported cho tới khi có SHA/log/test-list. Không làm lại từ đầu, không cộng106 thành runtime assurance.

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

Trước hết đọc [HANDOFF-TRAM.md](https://github.com/dec2609/m4-golden-lab-reference/blob/31fdb6e8fc51a08aa94e8d9d386cb970019676fc/M4-TEAM-HANDOFF/HANDOFF-TRAM.md) của mình. Sau đó đọc các mục sau tại source/evidence pin; không cần xin đường dẫn máy local của Thuận.

| File tại reference | Cần lấy thông tin gì |
|---|---|
| [candidate/scripts/m4_result_adapter.py](https://github.com/dec2609/m4-golden-lab-reference/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/candidate/scripts/m4_result_adapter.py) | emit_control, validate_control, ControlAssessment và helper behavior. |
| [candidate/scripts/m4_candidate_controls.py](https://github.com/dec2609/m4-golden-lab-reference/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/candidate/scripts/m4_candidate_controls.py) | Candidate preflight, actual producers, normalization/error propagation. |
| [candidate/scripts/run_m4_controls.py](https://github.com/dec2609/m4-golden-lab-reference/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/candidate/scripts/run_m4_controls.py) | Candidate CLI --candidate/--run-dir và run-owned output. |
| [candidate/scripts/dependency_policy.py](https://github.com/dec2609/m4-golden-lab-reference/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/candidate/scripts/dependency_policy.py) | Allowlist/direct exact pins, raw input hashes và parsing. |
| [candidate/tests/test_m4_result_adapter.py](https://github.com/dec2609/m4-golden-lab-reference/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/candidate/tests/test_m4_result_adapter.py) | Map coverage vào suite hiện tại. |
| [candidate/tests/test_m4_candidate_contract.py](https://github.com/dec2609/m4-golden-lab-reference/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/candidate/tests/test_m4_candidate_contract.py) | Identity/handoff regressions. |
| [candidate/tests/test_contract_freeze.py](https://github.com/dec2609/m4-golden-lab-reference/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/candidate/tests/test_contract_freeze.py) | Harness sandbox để đọc behavior; không bắt buộc port file. |
| [patches/tram.patch](https://github.com/dec2609/m4-golden-lab-reference/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/patches/tram.patch) | Semantic hunks tham khảo, không nguyên assembled adapter. |
| [evidence/portability/results.json](https://github.com/dec2609/m4-golden-lab-reference/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/evidence/portability/results.json) | Historical LF/CRLF parsing, raw hashes khác nhau. |
| [evidence/package-checkpoint.log](https://github.com/dec2609/m4-golden-lab-reference/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/evidence/package-checkpoint.log) | Historical17-case conformance, không là branch result của Trâm. |

Các source paths trong cột đầu bỏ tiền tố `candidate/` là path đích trong repo nhóm khi tương ứng đã có. Patches không là file phải đưa vào implementation PR. Reference evidence là lịch sử, không kết quả đã chạy trên branch bạn. Source pin và publication SHA nêu trên bất biến; current main có thể đã thay đổi.

## D. Công việc cần thực hiện theo thứ tự

### D.1. Giữ baseline đã làm

**Thực hiện:** Tiếp tục fix/m4-tram-contract nếu đây vẫn là branch đang làm. Ghi HEAD40/main base và gom commands/logs/test-list cho các kết quả17/52/37 đã báo. Không yêu cầu tạo branch khác hay rerun chỉ vì reference có thêm helper.

**Đầu ra để chuyển bước:** Bảng coverage đã có, behavior chưa xác minh và dependency pending; không suy coverage từ count.

### D.2. Đối chiếu public adapter API

**Thực hiện:** Đích scripts/m4_result_adapter.py::emit_control/validate_control/ControlAssessment. So signature exact với CONTRACT.md; hỗ trợ năm normalized controls, GITLEAKS metadata keywords và flat argv. Pair report/execution đúng schema/nullability, no overwrite và report hash raw bytes.

**Đầu ra để chuyển bước:** Compatible API; bool(assessment) gây TypeError; valid FAIL/ERROR không security_approved dù evidence_valid=True; invalid raise ValueError/OSError.

### D.3. Kiểm identity/report binding

**Thực hiện:** Source/run/snapshot/tool/raw/wrapper/policy exits và execution/artifact subjects phải khớp context/pair. SOURCE_EXECUTION source-only không bịa artifact; GITLEAKS/DEPENDENCY/UNIT_TEST artifact_subject=null. BUILD_EXECUTION và SBOM/Trivy dùng measured OCI index subject, không archive/config digest lẫn nhau.

**Đầu ra để chuyển bước:** Map wrong source/run/subject/hash/tool/boolean raw exit/missing/empty/fixture bypass vào tests thật; chỉ thêm case còn thiếu.

### D.4. Đối chiếu bốn thành phần hỏi thêm

**Thực hiện:** _assess_envelope(r,e,c,root,...) là private validator chung của emitter/consumer; chỉ cần behavior tương đương. runtime_allowed() là resource guard build/deploy của Quang, không emitter API; phối hợp nếu caller import còn thiếu, không tự port vào adapter chỉ vì tên. unit_main() là handler reference cho CLI --unit --candidate --run-dir, actual pytest/JUnit→UNIT_TEST; giữ CLI/output behavior nếu handler khác tên. tests/test_contract_freeze.py là sandbox harness dùng fixtures/doubles: map assertions vào tests của mình, không bắt buộc tên file.

**Đầu ra để chuyển bước:** Bốn dòng: behavior đã đáp ứng ở đâu/test nào; cần bổ sung gì thực sự; ai sở hữu dependency. Không copy aliases/helpers để giống layout.

### D.5. Dependency Policy và portability

**Thực hiện:** Đích dependency_policy.py và adapter dependency branch. Giữ existing allowlist/direct scope, exact pins; report có policy_sha256 và manifest_sha256 so raw current files. LF/CRLF parse tương đương nhưng hash raw khác; admission violation FAIL, syntax/execution error không PASS.

**Đầu ra để chuyển bước:** Case approved/unapproved/syntax, wrong input hash và LF/CRLF có evidence; không đổi allowlist/requirements cho xanh.

### D.6. SBOM/Trivy và candidate runner

**Thực hiện:** Đích m4_candidate_controls.py/run_m4_controls.py; --candidate/--run-dir thật, run-owned paths, SPDX typed/nonempty package inventory, Trivy typed SchemaVersion2/container_image/immutable subject/Results. Giữ CRITICAL-only policy, tool/version/raw exit tách wrapper/policy; missing/error/invalid report không PASS. Validate source records trước reuse, không rewrite identity/historical outputs.

**Đầu ra để chuyển bước:** Output pair chuẩn; actual tool chưa chạy không zero findings; signed artifact/preflight giữ nguyên, không tháo kiểm để scanner chạy.

### D.7. Kiểm actual call boundary khi dependency sẵn sàng

**Thực hiện:** Phối hợp Ngân dùng đúng GITLEAKS metadata/signature và Quang dùng .security_approved. Kiểm actual producer main→actual emitter/consumer; scanner doubles ghi rõ. Kiểm UNIT_TEST CLI dispatch/JUnit nếu chưa covered.

**Đầu ra để chuyển bước:** Không TypeError/import gap ở code path thực; cùng adapter commit, source/run identity và raw outputs. Missing Quang build context/key hoặc Ngân producer thì ghi dependency pending.

### D.8. Chốt implementation và bàn giao

**Thực hiện:** Chỉ sửa thiếu sót đã xác định; rerun affected tests sau code change, giữ tests cũ/assertions. Gửi một adapter commit/PR GitHub cho Quang và Ngân sử dụng thống nhất.

**Đầu ra để chuyển bước:** Không regression đã biết, behavior mapping+limitations rõ, không fork adapter và không yêu cầu whole lab.

## E. Kiểm thử và evidence

17 conformance chỉ có giá trị implementation khi trỏ M4_CONTRACT_IMPLEMENTATION và không skip; schema-only PASS không đủ.52/37 chứng minh actual assertions trong log/test-list, không scanner/signing success. Không bắt rerun toàn bộ nếu chưa đổi code. Khi cần runtime Syft/Trivy, Quang cung cấp same-candidate signed archive/context/trust, Ngân source output; thiếu tool/DB/cache/resource ghi NOT_VERIFIED. Không fake scanner/provenance hoặc tự nới CRITICAL policy.

**Lệnh chọn lọc khi thực sự cần xác minh hoặc sau thay đổi:**

```bash
M4_CONTRACT_IMPLEMENTATION="$PWD" python -B -m pytest -q -p no:cacheprovider tests/contracts
python -B -m pytest -q -p no:cacheprovider tests/test_dependency_policy.py tests/test_m4_result_adapter.py tests/test_m4_candidate_contract.py
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

PR13 đã merge theo snapshot handoff. Giữ branch fix/m4-tram-contract và công việc đang có; kiểm local/remote trước khi switch/sync, không tạo thêm branch nếu đang có đúng branch. Không cần old lab SHA trong Git ancestry. Public contract files mới là chuẩn đối chiếu. Commit đúng owned/shared-reviewed paths, push branch đang làm và mở/cập nhật implementation PR trong repo nhóm; gửi adapter SHA cho Quang/Ngân, không tự sửa branches của họ.

Review diff/file list và stage explicit paths thuộc mình trước commit/push. PR vào **repo nhóm** có source SHA, tests/evidence/limits và shared changes cần owner review. Không merge main, không push/mời cộng tác vào repo tham chiếu. Mọi thay đổi implementation chính thức nằm ở repo nhóm, không trong clone Golden Lab.

## G. Báo cáo cá nhân A–J

Hoàn thiện **`docs/report-input/TRAM.md`** trong repository nhóm, có thể viết song song với các bước kỹ thuật. Không thay `TEMPLATE.md`, file của người khác hoặc `docs/bao-cao.md`; Thuận tổng hợp báo cáo chính sau.

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

- [ ] Public emitter/validator và producer records tương thích contract, có behavior mapping cho bốn helper/harness.
- [ ] Actual producer/consumer không signature mismatch trong phạm vi đã kiểm; shared dependency còn thiếu ghi rõ PR/SHA/owner.
- [ ] Affected regression đạt hoặc kết quả17/52/37 được gắn đúng SHA/log; không ép count giống lab.
- [ ] Runtime limitations công khai; adapter commit/PR và TRAM.md A–J đã bàn giao.

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
Report input docs/report-input/TRAM.md A–J đã điền / phần còn thiếu:
Việc Thuận cần kiểm khi tích hợp / bug cần quyết định:
```

Task completion chỉ áp dụng phạm vi đã kiểm và evidence đã bàn giao; **không tự là nghiệm thu full runtime M4 hoặc production-ready**.
