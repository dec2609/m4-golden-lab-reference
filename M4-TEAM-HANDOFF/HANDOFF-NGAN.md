# Bàn giao M4 — Nguyễn Ngọc Tuyết Ngân

### A. Bối cảnh và cách dùng reference

Golden Lab là **sandbox tích hợp nội bộ của Thuận**, nay công bố thành [repository tham chiếu Private](https://github.com/dec2609/m4-golden-lab-reference). Nó không phải repository nhóm, `origin/main` của nhóm hoặc một dependency bắt buộc phải copy. Source/patch chỉ để đối chiếu behavior; sửa implementation và gửi PR tại **https://github.com/UEH-CSS-26C/CSS-26C-N08-SaiGon-Continental**. Không copy cả candidate, không cherry-pick assembled commit hoặc dùng historical evidence làm current PASS.

Clone tham chiếu ở thư mục riêng (cần Thuận cấp quyền đọc Private repo; không dùng token trong URL):

~~~bash
git clone https://github.com/dec2609/m4-golden-lab-reference.git m4-golden-lab-reference
~~~

**Publication source/evidence SHA bất biến: `4c35990241e96f8d1d35de7e2615e12c55cf673b`.** Đây là commit mới trong repo tham chiếu; khác candidate checkpoint local `53f18d8b5689a25bc03b647b54eb1a4ba0cd78ef` và local package checkpoint `5cba5d2e45f946865737dfec5762427e8a7de6e5`. Không yêu cầu checkout các SHA local đó trên GitHub. Handoffs được bổ sung ở commit publication sau source pin; khi cần đọc đúng source dùng GitHub `/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/candidate/...` hoặc `git show 4c35990241e96f8d1d35de7e2615e12c55cf673b:candidate/<path>` trong clone tham chiếu. Links tương đối dưới đây hoạt động ở bản publication chứa handoffs.

Bạn có thể hiểu việc cần làm từ file này và contract chính thức; không phải xin thư mục máy Thuận để biết semantics. Reference source là một cách triển khai đã thử, **không yêu cầu giữ tên private helper hoặc tên file regression giống sandbox** nếu behavior tương đương đã được chứng minh. Không tự coi một tên hàm thiếu là finding.

Ngân phụ trách Gitleaks/source-security. **PR15 đã merge**, metadata28/10 HEAD `32765c19aa377c17b10582de594d674a6ea9fc40`. Conflict EOL cũ không còn là nhiệm vụ đang chặn merge trong snapshot này. Bước hiện tại là kiểm source producer trên main/branch follow-up đúng contract; không khôi phục old PR15 hoặc yêu cầu merge nó lần nữa.

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

Historical F2 là producer truyền metadata mà adapter không nhận/control unsupported, không quy lỗi một mình Ngân. History/worktree findings khác execution ERROR. Bốn conflict EOL trước đây thuộc workflow/Compose/dependency/gate-tests đã là lịch sử; **không chạy restore main theo hướng dẫn cũ**. Nếu có conflict mới, xác minh diff mới trên branch riêng, tách khỏi implementation task.

### D. Evidence hiện có và giới hạn

Kết quả Golden Lab là **lịch sử của checkpoint53f18d8**, chưa phải kết quả branch người nhận: root255/255, contract17/17, frontend68/68 và typechecks/build exit0; backend18/18 DB doubles. Không cộng counts thành full-stack PASS. Source-phase thật thu dependency/unit PASS và Gitleaks ERROR bị chặn; chưa có positive eight-control signed release.

Docker/RAM/daemon chặn build và runtime; pinned Gitleaks archive hash có evidence nhưng full clean Linux scan chưa thành công; Syft diagnostic attempt có zero report/error, Trivy/Cosign chưa có successful verification. Fresh PG/persistence, staging/rollback và browser cùng candidate chưa kiểm chứng. Không suy máy hôm nay còn cùng lỗi. Publication chỉ kiểm files/hashes/links, **không chạy lại tests hoặc runtime**.

Đọc tùy chọn [kết quả lịch sử](../EXPERIMENT-RESULTS.md), [test matrix](../TEST-MATRIX.md), [source manifest](../SOURCE-MANIFEST.json). Bản log redact/UTF-8-converted không là raw nguyên byte; mapping/hash publication giải thích tại README. Những câu trạng thái PR trong experiment docs là historical, không dùng thay metadata hiện tại.

[Archive integrity record](../evidence/gitleaks-download.json), [source ERROR envelope](../evidence/frozen-source-run/gitleaks-result.json), [Linux dirty-context attempt](../evidence/linux-source-run/source-security/run_manifest.json). Không gọi chúng là actual clean scanner PASS. Source unit results trước đây không tự thay fresh checks trên merged PR15.

### E. Hướng dẫn kỹ thuật tự đầy đủ

Files đích `scripts/source_security.py` và source-security tests/config thuộc Ngân. [Producer](../candidate/scripts/source_security.py), [original suite](../candidate/tests/test_source_security.py), [negative regression](../candidate/tests/test_reference_source.py), [ngan.patch](../patches/ngan.patch). Không copy cả adapter, gate hoặc workflow của người khác.

Producer đo `head_commit`, source_snapshot/dirty/shallow, history và worktree scope; outputs/tool cache ngoài measured checkout. Gọi canonical `emit_control` mục B với GITLEAKS, source context, report thật, raw exit/verdict/tool và flat producer CLI argv. Mapping: scan_scope→scope, head_commit→head_commit, is_dirty→dirty, measured shallow→shallow; per-scope exits→raw_exit_codes; scanner name/version/archive/executable hashes→scanner_integrity/tool. Multi-scope scanner argv giữ riêng trong raw manifest. `execution_started` nói scanner process chạy hay chưa, không phải wrapper CLI có chạy.

~~~python
# Pseudocode mapping; lấy values từ actual scan, không điền sẵn PASS.
emit_control(context, run_dir, 'GITLEAKS', report_or_none,
             actual_raw_exit, verdict, actual_tool, producer_argv, reason,
             scope=measured_scope, head_commit=measured_head,
             dirty=measured_dirty, shallow=measured_shallow,
             raw_exit_codes=scope_exits, scanner_integrity=integrity,
             repository_root=repository_root)
~~~

PASS đòi clean full history+worktree, head/context khớp, dirty=false/shallow=false, raw exits typed `[0,0]`, valid empty reports và actual verified tool. Findings kể cả raw0→FAIL; install/version/platform/execution/report error→ERROR/nonzero hoặc rawnull khi chưa chạy. Không fake [] để thay missing report, không raw2→0, không ignore finding/history để xanh. Source controls giữ artifact_subject null; canonical output `gitleaks-execution.json`/`gitleaks-result.json`, raw reports/commands/manifests cùng run. Legacy GITLEAKS_STATUS=FAIL chưa đủ nói có secret findings; đọc reason/finding_count/execution.

Kiểm archive pin và executable bytes độc lập, cached corrupt reject, actual tool version đúng pin đã approve trong repo. Reference dùng Gitleaks8.18.4/Linuxx64 và archive pin `ba6dbb656933921c775ee5a2d1c13a91046e7952e9d919f9bac4cec61d628e7d`; đây là snapshot, không approval mới. Không lấy archive SHA làm binary SHA hoặc đổi version mà vẫn khai pin cũ. Giữ controls hiện có nếu đã tương đương; helper `execute_scanner` là seam testing tham khảo, không API bắt buộc.

Trâm chịu shared emitter/signature và validator; Quang consumer/workflow. Nếu actual call còn TypeError, cung cấp argv/trace đã redact và adapter commit cho Trâm, không fork adapter. `_assess_envelope`/`unit_main`/`runtime_allowed` không phải việc Ngân phải copy; test actual handoff mới xác nhận tương thích.

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

PR15 đã merge: nếu chưa có follow-up branch thì tạo branch mới từ main đã fetch, ví dụ `fix/m4-ngan-contract`; nếu đã có branch/commits đang làm thì tiếp tục, kiểm scope/dependencies, không tạo thêm hoặc reset. Không merge old PR15, không áp lại bốn EOL-only files hoặc duplicate source-security vào PR12. Phối hợp bằng PR/SHA emitter của Trâm và consumer của Quang; contract task diễn ra sau phase merge đã xong.

### G. Kiểm thử và checklist hoàn thành

Dùng suite hiện tại và map equivalent cases; không yêu cầu có harness `test_contract_freeze.py`. Chỉ bổ sung nếu chưa có: archive/binary corruption/version mismatch; history+worktree đều chạy; raw0 có findings; raw2/missing/empty/malformed; wrong/dirty/shallow source; run/hash/tool mismatch; outputs ngoài checkout; **actual producer main gọi actual emitter** với scanner double được ghi nhãn. Test này không thay real Gitleaks scan.

~~~bash
python -B -m pytest -q -p no:cacheprovider tests/test_source_security.py
M4_CONTRACT_IMPLEMENTATION="$PWD" python -B -m pytest -q -p no:cacheprovider tests/contracts
git diff --check
~~~

Tests supplemental chỉ gọi khi có trên branch; count khác lab không tự là regression. Khi actual scanner đủ điều kiện, dùng Linux/tool pin sạch/full history/context orchestration, run/cache ngoài checkout; context phải đo thật. CLI contract: `python -B scripts/source_security.py --candidate "$RUN/source-context.json" --run-dir "$RUN"`. Thiếu tool/platform/emitter thì ghi NOT_VERIFIED/DEPENDENCY_PENDING và reason, không hạ control. Không báo lại ba mock errors cũ nếu chưa reproduce.

- [ ] Không còn task resolve conflict cũ; chỉ follow-up thay đổi thực sự cần.
- [ ] Pin/archive/executable/version và source scopes được giữ; raw0/findings không PASS.
- [ ] Producer/emitter không TypeError trên adapter commit đã thống nhất.
- [ ] Source/run/subject/tool/raw exits/report hash đúng, không normalize current identity theo evidence cũ.
- [ ] Suite/negative cases có logs/source SHA; real scan chưa có ghi NOT_VERIFIED.
- [ ] PR không chạm workflow/Compose/policy/gate của người khác trừ shared review được giao rõ.

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

