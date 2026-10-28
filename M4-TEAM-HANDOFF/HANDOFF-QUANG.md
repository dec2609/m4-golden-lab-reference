# Bàn giao M4 — Nguyễn Minh Quang

### A. Bối cảnh và cách dùng reference

Golden Lab là **sandbox tích hợp nội bộ của Thuận**, nay công bố thành [repository tham chiếu Private](https://github.com/dec2609/m4-golden-lab-reference). Nó không phải repository nhóm, `origin/main` của nhóm hoặc một dependency bắt buộc phải copy. Source/patch chỉ để đối chiếu behavior; sửa implementation và gửi PR tại **https://github.com/UEH-CSS-26C/CSS-26C-N08-SaiGon-Continental**. Không copy cả candidate, không cherry-pick assembled commit hoặc dùng historical evidence làm current PASS.

Clone tham chiếu ở thư mục riêng (cần Thuận cấp quyền đọc Private repo; không dùng token trong URL):

~~~bash
git clone https://github.com/dec2609/m4-golden-lab-reference.git m4-golden-lab-reference
~~~

**Publication source/evidence SHA bất biến: `4c35990241e96f8d1d35de7e2615e12c55cf673b`.** Đây là commit mới trong repo tham chiếu; khác candidate checkpoint local `53f18d8b5689a25bc03b647b54eb1a4ba0cd78ef` và local package checkpoint `5cba5d2e45f946865737dfec5762427e8a7de6e5`. Không yêu cầu checkout các SHA local đó trên GitHub. Handoffs được bổ sung ở commit publication sau source pin; khi cần đọc đúng source dùng GitHub `/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/candidate/...` hoặc `git show 4c35990241e96f8d1d35de7e2615e12c55cf673b:candidate/<path>` trong clone tham chiếu. Links tương đối dưới đây hoạt động ở bản publication chứa handoffs.

Bạn có thể hiểu việc cần làm từ file này và contract chính thức; không phải xin thư mục máy Thuận để biết semantics. Reference source là một cách triển khai đã thử, **không yêu cầu giữ tên private helper hoặc tên file regression giống sandbox** nếu behavior tương đương đã được chứng minh. Không tự coi một tên hàm thiếu là finding.

Quang phụ trách gate/artifact/workflow và release boundaries. Metadata28/10 cho PR12 còn open, branch `m4-quang`, HEAD `4fe477e26487c97040568e33fa770f177e1c62de`; đây chỉ là PR snapshot, không technical verdict. Không mặc định implementation hiện tại giống old f0c9af1 hoặc assembled reference.

### B. Contract và giao diện liên quan

Contract chính thức: **m4-contract-1.0**, [PR17](https://github.com/UEH-CSS-26C/CSS-26C-N08-SaiGon-Continental/pull/17), commit **`9f1469f64d6a9ae8d5ef4b2758e878a2dfed5e1d`**. Metadata đọc ngày28/10/2026 cho thấy PR17 đã merge; đây không phải một cuộc audit lại source hoặc CI.

- [CONTRACT.md](https://github.com/UEH-CSS-26C/CSS-26C-N08-SaiGon-Continental/blob/9f1469f64d6a9ae8d5ef4b2758e878a2dfed5e1d/docs/m4-contract/CONTRACT.md)
- [SCHEMA.md](https://github.com/UEH-CSS-26C/CSS-26C-N08-SaiGon-Continental/blob/9f1469f64d6a9ae8d5ef4b2758e878a2dfed5e1d/docs/m4-contract/SCHEMA.md)
- [WORKFLOW.md](https://github.com/UEH-CSS-26C/CSS-26C-N08-SaiGon-Continental/blob/9f1469f64d6a9ae8d5ef4b2758e878a2dfed5e1d/docs/m4-contract/WORKFLOW.md)
- [ACCEPTANCE.md](https://github.com/UEH-CSS-26C/CSS-26C-N08-SaiGon-Continental/blob/9f1469f64d6a9ae8d5ef4b2758e878a2dfed5e1d/docs/m4-contract/ACCEPTANCE.md)

Contract quy định interface/behavior, không tự đưa runtime fixes vào main. Bản read-only giống commit trên nằm trong `contract-spec/` của repo tham chiếu. Không đổi schema/acceptance hoặc thêm policy ngoài contract.

~~~python
emit_control(context, run_dir, control, report_path, raw_exit, verdict,
             tool, command, reason, *, wrapper_exit_code=None,
             policy_exit_code=None, repository_root=None,
             dependency_policy_path=None,
             expected_dependency_policy_sha256=None,
             scope=None, head_commit=None, dirty=None, shallow=None,
             raw_exit_codes=None, scanner_integrity=None)
~~~

Đây là signature cần tương thích của shared `scripts/m4_result_adapter.py`. `command` là flat argv thật; không lồng hai scanner commands vào một argv. GITLEAKS metadata qua keyword; multi-scope raw argv giữ trong manifest. Five normalized controls: GITLEAKS/DEPENDENCY/UNIT_TEST/SBOM/VULNERABILITY; DIGEST/REGISTRY/COSIGN do gate xác minh.

`validate_control(run_dir, control, context, repository_root=None, dependency_policy_path=None, expected_dependency_policy_sha256=None)` trả `ControlAssessment(evidence_valid, security_approved, policy_verdict, reason)`. Invalid data raise ValueError/OSError; gate phải chặn, không fallback. `bool(assessment)` phải raise TypeError. Valid FAIL/ERROR có thể `evidence_valid=True` nhưng `security_approved=False`. PASS chỉ approve control đó khi execution/raw0/report/policy/identity đúng; chưa đồng nghĩa production PASS.

SOURCE_EXECUTION: source_commit SHA40, raw-byte source_snapshot SHA256 và run_id `[A-Za-z0-9_-]{1,100}` khớp basename output run ngoài checkout. Scope fingerprint: sorted tracked path+NUL+raw bytes+NUL trong scripts/tests/ma-nguon/.github/cau-hinh, Makefile và root Compose, bỏ `/evidence/`. GITLEAKS/DEPENDENCY/UNIT_TEST giữ `artifact_subject=null`, source execution_subject, kể cả sau build. BUILD_EXECUTION thêm archive SHA, OCI index (`manifest_digest`), platform manifest, config digest và immutable reference; SBOM/Trivy subject là index. Không tráo các digests hoặc bịa artifact cho source controls.

Result schema_version="1.0", contract_version=m4-contract-1.0; source/run/subjects/tool/raw exits phải khớp execution pair/context. Tool name/version, reason, raw report path/hash, execution_path, wrapper_exit_code/policy_exit_code có mặt theo schema; nullable không đồng nghĩa được bỏ field. Raw exit là int thật, không bool; null chỉ ERROR khi process chưa chạy. PASS/SUCCESS/raw0; FAIL với report findings/admission rejection không approve; ERROR giữ actual exit hoặc null, không đổi thành PASS. UNKNOWN/UNAVAILABLE chỉ có thể mô tả error. Hash raw bytes trước parse; path confined/run-owned, cặp dở dang/missing/malformed/stale/wrong source/run/subject/hash bị reject. Không fixture-name/hash bypass, không M3/env-only/literal security PASS.

### C. Vấn đề cần đối chiếu

F1 validity-as-approval, F3 weak fixture validation, F4 workflow/CLI mismatch là historical repros dùng để xác định behavior cần đối chiếu. Chỉ gọi còn lỗi khi test trên current SHA reproduce. Sync main/resolve Git không là implementation fix; ngược lại thiếu tên helper reference không tự là lỗi.

### D. Evidence hiện có và giới hạn

Kết quả Golden Lab là **lịch sử của checkpoint53f18d8**, chưa phải kết quả branch người nhận: root255/255, contract17/17, frontend68/68 và typechecks/build exit0; backend18/18 DB doubles. Không cộng counts thành full-stack PASS. Source-phase thật thu dependency/unit PASS và Gitleaks ERROR bị chặn; chưa có positive eight-control signed release.

Docker/RAM/daemon chặn build và runtime; pinned Gitleaks archive hash có evidence nhưng full clean Linux scan chưa thành công; Syft diagnostic attempt có zero report/error, Trivy/Cosign chưa có successful verification. Fresh PG/persistence, staging/rollback và browser cùng candidate chưa kiểm chứng. Không suy máy hôm nay còn cùng lỗi. Publication chỉ kiểm files/hashes/links, **không chạy lại tests hoặc runtime**.

Đọc tùy chọn [kết quả lịch sử](../EXPERIMENT-RESULTS.md), [test matrix](../TEST-MATRIX.md), [source manifest](../SOURCE-MANIFEST.json). Bản log redact/UTF-8-converted không là raw nguyên byte; mapping/hash publication giải thích tại README. Những câu trạng thái PR trong experiment docs là historical, không dùng thay metadata hiện tại.

[Old F1 probe](../evidence/fresh-before/f1-current-source.json), [source-only gate block](../evidence/actual-gate-source-only.log), [resource guard](../evidence/actual-build-guard.log), [source sequence](../evidence/frozen-source-run/run-summary.json). Positive Cosign/deployment trong regression là doubles, không current runtime.

### E. Hướng dẫn kỹ thuật tự đầy đủ

Files đích: `scripts/production_gate.py`, `artifact_security.py`, `verify_registry.py`, `run_m4_workflow.py` (hoặc canonical entrypoint tương đương theo WORKFLOW), `deploy_staging.py`, `test_rollback.py`, `.github/workflows/verify.yml`, Makefile. [Gate](../candidate/scripts/production_gate.py), [artifact](../candidate/scripts/artifact_security.py), [registry](../candidate/scripts/verify_registry.py), [orchestrator](../candidate/scripts/run_m4_workflow.py), [deployment](../candidate/scripts/deploy_staging.py), [rollback](../candidate/scripts/test_rollback.py), [quang.patch](../patches/quang.patch). Các path là reference, không nói owner branch thiếu chức năng nếu helper khác tên.

**F1/approval:** consumer gọi `assessment = validate_control(...)`, dùng `assessment.security_approved`; không `bool(assessment)`, không coi record hợp lệ là PASS. Invalid/missing/malformed/FAIL/ERROR phải controlFAIL/globalBLOCKED. Exact enum chỉ literal PASS là approve; BYPASS/NOT_PASS/UNKNOWN không PASS. Tám controls phải approve trước gate0; invalid/preflight2, blocked1. Chỉ genuine build context mới tạo release status đúng schema, không zero digest giả.

**F3/validation:** Trâm sở hữu shared adapter/emitter, Quang review invariant consumed: source/run/subject/tool/execution/report-hash, bool raw exit, typed reports, required-null fields. Không fork/copy adapter riêng hoặc fixture-name/SHA bypass. `_assess_envelope` là cách reference gói checks; không bắt Trâm port tên đó. Cần kiểm caller/consumer hợp tác chứ không chỉ import thành công.

**Artifact/trust:** build once, đo archive SHA, OCI index/platform/config/layer bytes và source/provenance; không dùng mutable tag thay identity, không rebuild sau scan/sign. Verify exact archive bằng approved external public-key pin/bundle/Cosign; literal producer PASS không thay verification, không tự approve key đi kèm evidence. Registry index/platform/config phải quan hệ đúng. Actual Buildx/provenance compatibility còn phải chạy, không tự synthesize metadata.

**F4/workflow:** dùng actual CLIs/paths trong official WORKFLOW, không M3/literal digest/Cosign PASS, không invoke thiếu `--candidate/--run-dir`. Source→Gitleaks/dependency/unit→build once→sign/verify→signed candidate preflight→Syft/Trivy→gate→staging/readiness→rollback khi cần→Console. Ký trước scan là integrity prerequisite hiện hành, không admission approval. `unit_main()` chỉ tên handler reference; giữ CLI `m4_result_adapter.py --unit ...` tương thích cùng Trâm. `runtime_allowed()` là tên resource helper reference (RAM>=1536MiB/disk>=5GiB); Quang bảo đảm caller build/deploy/orchestration fail-closed và cùng guard dù dùng helper khác. Không buộc Trâm copy guard chỉ vì reference đặt trong adapter.

**Deployment/lifecycle:** chỉ staging sau gate approve; `/ready` cần HTTP200 và JSON ready/database connected; 404/503/body sai không PASS. Command failure phải nonzero/FAIL. Rollback chỉ previous approved immutable artifact có evidence; thiếu previous approval thì NOT_RUN/BLOCKED, không giả recovery. Không down-v/xóa volume; giữ API/frontend v1/v2, NOT_RUN, FIXTURE/UNVERIFIED. Publisher run-bound, không coi stale last-reported response là candidate mới.

### F. Git và phối hợp trên GitHub

Đây là hướng dẫn người nhận thực hiện trên **checkout repo nhóm**; phiên tạo handoff không làm các thao tác này. Kiểm remote/status trước; có dirty/untracked chưa bảo toàn thì giữ nguyên hoặc dùng clone riêng. Không reset/clean/force-push, không đổi remote repo nhóm sang reference repo.

~~~bash
git remote -v
git status --short
git branch --show-current
git fetch origin main
git cat-file -e '9f1469f64d6a9ae8d5ef4b2758e878a2dfed5e1d^{commit}'
git diff --exit-code 9f1469f64d6a9ae8d5ef4b2758e878a2dfed5e1d origin/main -- docs/m4-contract tests/contracts
~~~

So **nội dung contract files**, không bắt buộc cùng Git ancestry nếu main dùng squash. Nếu SHA chưa có do shallow clone, đọc contract pin trên GitHub và nhờ Thuận xác nhận commit mapping; không fetch một branch publication cũ có thể đã bị xóa. Nếu nội dung contract main khác pin, báo khác biệt thay vì tự redesign. Không merge main khi working tree chưa sạch hoặc chưa review diff/conflicts.

PR12 đang mở: tiếp tục branch `m4-quang` và commits của mình; kiểm diff với main trước khi đồng bộ, không tạo lại hoặc cherry-pick whole reference. Shared adapter do Trâm cung cấp qua PR/commit GitHub; Ngân PR15 đã merge theo metadata28/10, không copy lại old PR15. Nếu mergeability thay đổi, giải quyết Git trên branch riêng rồi làm implementation ở bước riêng. Không force-push hoặc chỉnh branch người khác.

### G. Kiểm thử và checklist hoàn thành

Đối chiếu tests đã có; chỉ bổ sung/đạy lại affected cases sau code change. Không yêu cầu `tests/test_contract_freeze.py` nếu equivalent tests đã bao phủ. Cases cần map: valid PASS/FAIL/ERROR qua **actual gate consumer**; wrong subject/source/run/hash/tool/bool/missing/empty; fixture name không bypass; actual CLI `--help`/workflow options; artifact digest relations; readiness wrong body; command failure; rollback identity.

~~~bash
M4_CONTRACT_IMPLEMENTATION="$PWD" python -B -m pytest -q -p no:cacheprovider tests/contracts
python -B -m pytest -q -p no:cacheprovider tests/test_production_gate.py tests/test_artifact_security.py
git diff --check
~~~

Các file tests bổ sung chỉ gọi khi đã có trên branch; tên/count sandbox không bắt buộc. CLI/help/static workflow không là CI hoặc actual deployment PASS. Operator cung cấp approved trust config/registry/previous image và isolated environment trước runtime, không tự tạo approval.

- [ ] Gate đọc `.security_approved`, FAIL/ERROR/invalid không approve; fresh proof đúng SHA.
- [ ] Strict shared validator; no fixture/M3/env-only/literal PASS bypass.
- [ ] Workflow gọi actual supported CLI, UNIT_TEST/source metadata thống nhất Trâm/Ngân.
- [ ] Build-once identity/sign/registry đúng; chưa actual execution ghi NOT_VERIFIED.
- [ ] Guard, readiness, command failure/rollback boundaries có affected tests; runtime còn pending tách riêng.
- [ ] PR chỉ scope Quang/shared hunks được owner review; không claim full release từ fixtures.

### H. Bàn giao lại cho Thuận

~~~text
Người thực hiện / branch / PR URL:
Source SHA40 đã kiểm / base main SHA / ngày:
Contract: m4-contract-1.0 @ 9f1469f64d6a9ae8d5ef4b2758e878a2dfed5e1d
Reference source publication SHA: 4c35990241e96f8d1d35de7e2615e12c55cf673b
Behavior đã đáp ứng (file:function + test/evidence):
Behavior còn thiếu hoặc chưa xác minh:
Khác biệt có chủ đích với reference và vì sao tương đương:
Dependency đang chờ owner khác (PR/SHA/API):
Command | exit | pass/fail/skip/error | unit/double/actual/runtime:
Evidence relative path/link + hash + source/run/artifact identity:
Giới hạn runtime / thông tin thiếu:
Việc Thuận cần kiểm khi tích hợp:
~~~

Không gửi credentials/private keys hoặc tự xác nhận approval. Chỉ commit/push branch thuộc mình theo quy trình nhóm khi đã review; không merge main thay nhóm.

