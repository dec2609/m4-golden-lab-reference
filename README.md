# M4 Golden Lab Reference

**This repository is an experimental integration reference, not the official M4 release baseline.**

Golden Lab là sandbox tích hợp local của Thuận cho OrderFlow/N08 Saigon Continental. Bản Private này giúp thành viên có quyền truy cập đối chiếu source/patch/tests; không thay repository nhóm, không phải current `origin/main`, không phải verified release.

- Candidate checkpoint lịch sử: `53f18d8b5689a25bc03b647b54eb1a4ba0cd78ef`.
- Local package checkpoint lịch sử: `5cba5d2e45f946865737dfec5762427e8a7de6e5`.
- Contract chính thức **m4-contract-1.0**: [PR17 / commit9f1469f](https://github.com/UEH-CSS-26C/CSS-26C-N08-SaiGon-Continental/blob/9f1469f64d6a9ae8d5ef4b2758e878a2dfed5e1d/docs/m4-contract/CONTRACT.md).
- Các SHA trên là checkpoint nguồn cũ; **không mặc định fetch/checkout được chúng từ repo tham chiếu mới**. Repo này có lịch sử publication mới hoàn toàn, không copy `.git` cũ. Publication source SHA được ghi trong handoffs ở bước công bố.

## Dùng bản tham chiếu

Đọc handoff của mình trong `M4-TEAM-HANDOFF/`, đối chiếu contract trên GitHub nhóm rồi sửa implementation trên branch của mình trong **repo nhóm**. Clone repo tham chiếu ở thư mục riêng; không thay remote của repo nhóm. Không copy cả candidate, không cherry-pick assembled commit, không áp patch tự động lên HEAD mới. Tên private helpers/test harness có thể khác nếu behavior tương đương và tests chứng minh.

`candidate/` là bản trích source tracked từ checkpoint nêu trên: scripts/tests/fixtures/config/backend/frontend, Compose và Makefile. Bỏ `bang-chung/`, nested historical evidence, image archives và phần tài liệu nhóm không cần đối chiếu. Vì không có Git history cũ/whole historical artifacts, đây không phải drop-in replay của source fingerprint, Gitleaks full history hoặc full workflow. Chỉ dùng để xem implementation và port semantic changes có review.

`contract-spec/` giữ nguyên docs/schema/examples/specification tests từ official commit9f1469f; không đưa contract mới. `patches/` dựa trên assembled base `af25ea8f4220e032e4b739f8be204e116fb7e025`, không phải patch bảo đảm apply vào owner HEAD hiện tại. Hai bản implementation có thể khác cấu trúc nhưng phải cùng contract; không nhận định thiếu helper name là thiếu chức năng.

## Mapping owner → source → patch → evidence

| Owner | Source trong candidate | Patch | Evidence chọn lọc |
|---|---|---|---|
| Quang | scripts/production_gate.py, artifact_security.py, verify_registry.py, run_m4_workflow.py, deploy_staging.py, test_rollback.py; .github/workflows/verify.yml | patches/quang.patch | evidence/fresh-before/, actual-gate-source-only.*, actual-build-guard.*, frozen-source-run/run-summary.json |
| Trâm | scripts/m4_result_adapter.py, m4_candidate_controls.py, run_m4_controls.py, dependency_policy.py | patches/tram.patch; shared-tests.patch chỉ chọn cases | evidence/portability/, package-checkpoint.log, frozen-source-run/dependency-* và unit-* |
| Ngân | scripts/source_security.py; tests/test_source_security.py, test_reference_source.py | patches/ngan.patch | evidence/frozen-source-run/gitleaks-*, linux-source-run/, gitleaks-download.json |
| Tuyết | ma-nguon/order-app/, ma-nguon/database/, docker-compose*.yml | Không có runtime patch Tuyết trong experiment này | evidence/final-backend.*, backend-author-report.md (historical owner report, không fresh runtime) |

## Kết quả lịch sử — không chạy lại khi publication

Candidate đã ghi root255/255, contract17/17, frontend68/68, hai typechecks và production build exit0; selected backend18/18 dùng DB doubles. Các counts không cộng thành integrated runtime acceptance. Local source phase có dependency/unit PASS và Gitleaks ERROR bị chặn; không phải positive eight-control release.

Docker/RAM/daemon đã chặn build/runtime tại thời điểm experiment. Pinned Gitleaks archive được đo hash, nhưng clean Linux full-history/worktree scan chưa xác minh thành công. Syft diagnostic filesystem attempt thất bại/zero report; Trivy/Cosign attempts không chứng minh successful scan/signature. Không có current built/signed candidate, positive gate, fresh PostgreSQL persistence/recovery, staging/rollback hoặc browser cùng run. Không suy môi trường hiện tại còn lỗi y hệt. Không có CI PASS mới.

`EXPERIMENT-RESULTS.md`, `TEST-MATRIX.md`, `OWNER-HANDOFF.md` và các top-level manifests là **historical experiment records**; câu nói PR/branches/policy chưa merge thuộc thời điểm ghi, không là live GitHub status. Handoffs mới hướng dẫn làm việc trên repo nhóm theo commit/PR thực tế của từng người. Không dùng historical evidence làm current release PASS.

## Safety, redaction và integrity

Không đưa private keys, tokens, `.env`, venv/cache, Docker images, pytest temp outputs, frontend dist hoặc browser trace archives. Các development credentials/placeholders đã có trong source/Compose/SQL được giữ để không đổi implementation; chúng là lab-only defaults, không dùng như secrets production hoặc bằng chứng secrets đã externalize.

Absolute Windows home locations trong tài liệu/logs đã đổi thành `<USER_HOME>`, Git Bash host path thành placeholder khi cần; nguồn gốc/raw logs giữ local. Bản redact **không là raw nguyên byte**; historical report/hash fields vẫn ghi original-byte identities. `PUBLICATION-MANIFEST.json` giữ source→publication hashes và file bị loại; `SHA256SUMS.json` kiểm bytes công bố, không self-hash. Không dùng redacted diagnostic records làm executable current gate inputs.

Không chạy lại Golden Lab, Docker, scanner hoặc tests để tạo results mới trong lần publication. Chỉ kiểm inventory, hashes, JSON và liên kết. Nhóm cần review/port/test trên owner branch và same-candidate runtime riêng. Quyền đọc Private repo của các thành viên cần Thuận cấp qua GitHub; không tự mời/cấp quyền thay Thuận.

## Frozen publication source

Source/patch/evidence pin: **`4c35990241e96f8d1d35de7e2615e12c55cf673b`**. Handoffs/docs bổ sung ở commit delivery sau pin này, source bytes không thay đổi. Xem [handoffs](M4-TEAM-HANDOFF/) và [manifest](PUBLICATION-MANIFEST.json). Repository clone URL: `https://github.com/dec2609/m4-golden-lab-reference.git`. Thuận cần cấp quyền đọc Private repo cho từng thành viên trước khi họ clone; không có lời mời/cấp quyền tự động trong phiên publication.
