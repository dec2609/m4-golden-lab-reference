# Bàn giao M4 — Nguyễn Thị Phương Trâm

### A. Bối cảnh và cách dùng reference

Golden Lab là **sandbox tích hợp nội bộ của Thuận**, nay công bố thành [repository tham chiếu Private](https://github.com/dec2609/m4-golden-lab-reference). Nó không phải repository nhóm, `origin/main` của nhóm hoặc một dependency bắt buộc phải copy. Source/patch chỉ để đối chiếu behavior; sửa implementation và gửi PR tại **https://github.com/UEH-CSS-26C/CSS-26C-N08-SaiGon-Continental**. Không copy cả candidate, không cherry-pick assembled commit hoặc dùng historical evidence làm current PASS.

Clone tham chiếu ở thư mục riêng (cần Thuận cấp quyền đọc Private repo; không dùng token trong URL):

~~~bash
git clone https://github.com/dec2609/m4-golden-lab-reference.git m4-golden-lab-reference
~~~

**Publication source/evidence SHA bất biến: `4c35990241e96f8d1d35de7e2615e12c55cf673b`.** Đây là commit mới trong repo tham chiếu; khác candidate checkpoint local `53f18d8b5689a25bc03b647b54eb1a4ba0cd78ef` và local package checkpoint `5cba5d2e45f946865737dfec5762427e8a7de6e5`. Không yêu cầu checkout các SHA local đó trên GitHub. Handoffs được bổ sung ở commit publication sau source pin; khi cần đọc đúng source dùng GitHub `/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/candidate/...` hoặc `git show 4c35990241e96f8d1d35de7e2615e12c55cf673b:candidate/<path>` trong clone tham chiếu. Links tương đối dưới đây hoạt động ở bản publication chứa handoffs.

Bạn có thể hiểu việc cần làm từ file này và contract chính thức; không phải xin thư mục máy Thuận để biết semantics. Reference source là một cách triển khai đã thử, **không yêu cầu giữ tên private helper hoặc tên file regression giống sandbox** nếu behavior tương đương đã được chứng minh. Không tự coi một tên hàm thiếu là finding.

Trâm phụ trách canonical adapter/emitter và dependency/SBOM/Trivy. Tiếp tục branch `fix/m4-tram-contract` đã làm; không bắt đầu lại chỉ vì reference khác layout. PR13 đã merge. Branch nêu trên do Trâm báo cáo; API đọc tại thời điểm đóng gói trả404, không chứng minh branch local không tồn tại.

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

F1 là validity bị dùng như approval; F2 là producer keywords/control support khác emitter; F3 là weak fixture branch/thiếu typed metadata; F5 là CRLF parse sai. Đây là các lỗi trên snapshots cũ dùng thiết kế acceptance, **không kết luận đang còn trên branch Trâm**. Giữ behavior đúng đã có, chỉ sửa invariant thực sự thiếu; không port aliases/helpers chỉ để giống tên reference.

### D. Evidence hiện có và giới hạn

Kết quả Golden Lab là **lịch sử của checkpoint53f18d8**, chưa phải kết quả branch người nhận: root255/255, contract17/17, frontend68/68 và typechecks/build exit0; backend18/18 DB doubles. Không cộng counts thành full-stack PASS. Source-phase thật thu dependency/unit PASS và Gitleaks ERROR bị chặn; chưa có positive eight-control signed release.

Docker/RAM/daemon chặn build và runtime; pinned Gitleaks archive hash có evidence nhưng full clean Linux scan chưa thành công; Syft diagnostic attempt có zero report/error, Trivy/Cosign chưa có successful verification. Fresh PG/persistence, staging/rollback và browser cùng candidate chưa kiểm chứng. Không suy máy hôm nay còn cùng lỗi. Publication chỉ kiểm files/hashes/links, **không chạy lại tests hoặc runtime**.

Đọc tùy chọn [kết quả lịch sử](../EXPERIMENT-RESULTS.md), [test matrix](../TEST-MATRIX.md), [source manifest](../SOURCE-MANIFEST.json). Bản log redact/UTF-8-converted không là raw nguyên byte; mapping/hash publication giải thích tại README. Những câu trạng thái PR trong experiment docs là historical, không dùng thay metadata hiện tại.

[17-case historical log](../evidence/package-checkpoint.log); [LF/CRLF](../evidence/portability/results.json); [actual source run](../evidence/frozen-source-run/run-summary.json). Kết quả17/52/37 Trâm báo là nguồn khác với255/17 của sandbox và cần branch SHA/logs riêng.

### E. Hướng dẫn kỹ thuật tự đầy đủ

**Ownership:** Trâm sửa shared adapter, dependency/SBOM/Trivy normalization; Quang consumer/gate/build/workflow; Ngân source producer. Preserve Orders/frontend. Các file đích repo nhóm: `scripts/m4_result_adapter.py`, `dependency_policy.py`, `m4_candidate_controls.py`, `run_m4_controls.py`; tests tương ứng. [Source adapter](../candidate/scripts/m4_result_adapter.py), [candidate controls](../candidate/scripts/m4_candidate_controls.py), [runner](../candidate/scripts/run_m4_controls.py), [policy](../candidate/scripts/dependency_policy.py), [tram.patch](../patches/tram.patch). Patch không phải drop-in diff từ main hiện tại.

**1. `_assess_envelope`: private helper, không là public API bắt buộc.** Reference signature:

~~~python
_assess_envelope(r, e, c, root, repository_root=None,
                 dependency_policy_path=None,
                 expected_dependency_policy_sha256=None)
~~~

`r`=result dict, `e`=execution dict, `c`=trusted context, `root`=run directory. Reference `emit_control` gọi nó trước khi ghi; `validate_control` đọc pair rồi gọi nó. Nó kiểm exact fields/types/enums/nullability; source/run/subjects đồng nhất; raw exit/tool/flat argv; report raw hash và path confinement; Gitleaks source_context; typed per-control report/policy. Invalid raise ValueError/OSError, valid trả assessment. Reference tạo `ControlAssessment(True, verdict=='PASS' and status=='SUCCESS' and code==0, verdict, reason)`, sau khi mọi invariant đã kiểm — không lấy biểu thức này thay validation.

Nếu implementation hiện tại đã có các bước tương đương và negative tests chứng minh emitter/consumer đều không chấp nhận sai evidence thì **không cần port helper hoặc đổi tên**. Nếu thiếu check cụ thể, thêm đúng check vào kiến trúc hiện tại; không copy toàn assembled adapter. Trâm sở hữu validation API, Quang review consumer `.security_approved`; API public/spec tests mới là chuẩn, không tên `_assess_envelope`.

**2. `runtime_allowed()`: helper tài nguyên của build/deploy/orchestration, không là emitter API.** Reference không nhận argument, đo available RAM bằng Windows GlobalMemoryStatusEx hoặc Linux `/proc/meminfo`, đo disk của repo, trả bool `RAM>=1536MiB and disk>=5GiB`; lỗi đo có thể raise. `artifact_security.py`, `deploy_staging.py`, `run_m4_workflow.py` gọi guard trước runtime. False/measurement failure phải ngăn chạy nặng, không biến thành security PASS. WORKFLOW contract giữ ngưỡng/guard; tên helper/vị trí trong adapter không bắt buộc.

Quang sở hữu caller build/deploy và guard; Trâm chỉ phối hợp shared import nếu caller thật của branch tích hợp còn import tên này. Nếu Quang đã có guard tương đương và không còn unresolved import thì **không cần thêm runtime_allowed vào adapter**. Nếu missing import có reproduction, hai người thống nhất chỗ export/caller; không hạ guard để tests/scan chạy. Guard true không chứng minh Docker/key/registry ready.

**3. `unit_main()`: CLI handler cho UNIT_TEST, không là tên hàm public bắt buộc.** Reference không nhận Python args, parse `--unit --candidate PATH --run-dir PATH`; load context, check run basename, từ chối output replay. Nó chạy pytest thật ở root repo với JUnit/logs ngoài checkout; parse passed/failed/skipped, giữ JUnit hash trong `unit-report.json` (`layer=UNIT_CONTRACT`), emit UNIT_TEST source-bound với pytest tool/version và raw subprocess exit. Handler trả0 nếu pytest0/có tests pass/không failure, ngược lại1; ERROR không approve. CLI dispatch reference dùng `unit_main() if '--unit' in sys.argv else main()`.

Contract yêu cầu đường gọi `python -B scripts/m4_result_adapter.py --unit --candidate "$CONTEXT" --run-dir "$RUN"` và output semantics, **không yêu cầu hàm tên unit_main**. Nếu branch đã có dispatcher/producer tương đương, tests chứng minh actual CLI/JUnit/output/negative exits thì không port. Nếu mới có counts handcrafted hoặc workflow gọi CLI chưa hỗ trợ, bổ sung handler/wiring tối thiểu; Trâm normalization/dispatcher, Quang workflow call. Không dùng source-null artifact digest giả hoặc literal passed count. Ghi raw pytest exit riêng với wrapper exit; giữ error log khi subprocess/JUnit lỗi, không approve.

**4. `tests/test_contract_freeze.py`: regression harness của sandbox, không phải file phải có trên branch.** Nó dùng pytest fixtures `tmp_path/monkeypatch`, handcrafted reports/OCI và mocked Cosign/scanner. Test functions không tạo runtime evidence; pytest trả exit code chung. Cases chính: valid PASS/FAIL/ERROR; bool assessment; wrong subject/tool/bool exit/source/run/hash/missing/empty report; fixture-name không chọn weak path; source-only subjects; source producer gọi emitter thật với scanner double; workflow/CLI importability; dependency policy/manifest hashes; required null fields. Workflow assertions của file còn gắn layout sandbox nên **không port máy móc**.

Mapping các behavior đó sang tests hiện tại của Trâm (`tests/contracts`, adapter/candidate/security regressions). Nếu đã có coverage tương đương thì ghi tên test và **không cần thêm file hoặc chạy lại Golden Lab**. Chỉ thêm case thực sự thiếu vào test file owned đang có. [Harness để đọc tùy chọn](../candidate/tests/test_contract_freeze.py), [shared-tests.patch](../patches/shared-tests.patch); tests cần gate/workflow thuộc shared boundary phải phối hợp Quang. Không coi positive double là scanner/signature thật.

**Producer boundary:** Dependency Policy kiểm direct exact name/version theo actual allowlist, report có `policy_sha256`/`manifest_sha256` của raw bytes, revalidate against measured files; admission rejection FAIL, parse/process error ERROR/invalid. Parse LF/CRLF bằng splitlines/in-memory normalization; hash vẫn raw bytes, không normalize để dùng lại hash cũ. SBOM report SPDX-2.x/document ID/nonempty packages; Trivy typed SchemaVersion2/container_image/immutable ArtifactName/RepoDigests/Results, CRITICAL-only policy. Raw scanner exit khác wrapper/policy exit; missing/process-error/invalid/hash/subject mismatch không PASS.

Actual release-mode runner nhận `--candidate` và `--run-dir`, phát `sbom-*`/`vulnerability-*` trong đúng run, không đọc historical root. Source records cùng run được validate/reuse, không rewrite identity; partial pair không approve. Source fingerprint và OCI index/platform/config/archive mapping phải khớp Quang. Signed archive/provenance preflight thuộc hiện trạng contract workflow: Quang cung cấp measured/signed candidate và approved trust context, Ngân cung cấp GITLEAKS metadata. Không fake candidate/key/tool hoặc tháo preflight để làm scanner xanh.

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

PR13 đã merge; Trâm đang có branch mới `fix/m4-tram-contract`: **tiếp tục branch đó**, không tạo branch nữa hoặc reset theo reference. Nếu local branch có thì kiểm/switch sau khi bảo toàn dirty work; nếu đã push thì kiểm đúng remote branch. Nếu chỉ local, giữ commits và push branch theo quy trình sau review. Không replay PR13 hoặc merged source. Phối hợp Quang/Ngân bằng link PR/commit GitHub của shared adapter, không gửi mỗi người copy một bản local khác nhau.

### G. Kiểm thử và checklist hoàn thành

Trâm **báo cáo** branch `fix/m4-tram-contract` có17/17 contract,52/52 adapter/candidate regression và37/37 security regression PASS. Phiên này chưa nhận SHA/log/test-list tương ứng và không chạy lại, nên chưa gọi độc lập VERIFIED. Counts có thể overlap, không cộng106 thành mức assurance.

- 17/17 chỉ chứng minh các contract vectors đã chạy với đúng implementation nếu có `M4_CONTRACT_IMPLEMENTATION` và không skip; cần command/SHA/log để xác nhận. Schema-only không đủ.
- 52/52 và37/37 chứng minh những assertions trong danh sách thực tế, không tự chứng minh mọi source/CLI/gate branch hoặc scanners thật. Không suy missing coverage chỉ từ count; gửi test names/mapping.
- Các suite chưa thay actual source-producer→emitter→gate cùng version, tool install/scan/sign/registry, real PostgreSQL/staging/rollback/browser.

Chỉ đối chiếu phần thiếu: (1) cung cấp SHA/logs/test-list; (2) map bốn thành phần mục E và negative matrix vào tests đã có; (3) nếu chưa có, thêm actual Gitleaks main→emitter call test, ghi scanner double; (4) kiểm UNIT_TEST CLI dispatch/JUnit và candidate runner args nếu chưa covered; (5) kiểm shared adapter với Quang/Ngân ở cùng commit khi dependency sẵn sàng. Không lặp suite đã PASS nếu không đổi code hoặc có unresolved failure.

Lệnh public khi cần xác nhận lại **sau thay đổi**, từ checkout repo nhóm (Python pytest/jsonschema đã có):

~~~bash
M4_CONTRACT_IMPLEMENTATION="$PWD" python -B -m pytest -q -p no:cacheprovider tests/contracts
python -B -m pytest -q -p no:cacheprovider tests/test_dependency_policy.py tests/test_m4_result_adapter.py tests/test_m4_candidate_contract.py
git diff --check
~~~

Kiểm file tồn tại ở SHA của mình; chọn các security regression file đã dùng cho37 tests, không yêu cầu tên file sandbox. Không ép count255/17/52/37 sau thay đổi; báo counts thực tế và lý do. Runtime chưa đủ tools/candidate/key/cache ghi NOT_VERIFIED và owner cung cấp.

- [ ] Contract/version và actual implementation SHA đã ghi (reported17 PASS, chờ logs/SHA).
- [ ] Shared emitter đúng signature; actual source producer không TypeError (cần test mapping).
- [ ] Valid FAIL/ERROR không approve; identity/hash/subject/null/tool/bool checks đủ (map52/37 tests).
- [ ] LF/CRLF parsing tương đương, raw hashes giữ đúng (cần chỉ ra test).
- [ ] Unit CLI và current candidate scanner CLI gọi được đúng handler (pending nếu chưa có proof).
- [ ] Scanner failure không PASS; runtime success chỉ khi actual tool chạy (runtime chưa xác minh).
- [ ] Không regression; PR đúng ownership; shared hunks đã review với Quang/Ngân.

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

