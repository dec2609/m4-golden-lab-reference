# Contract freeze versus release acceptance

**PROPOSED_FOR_TEAM_REVIEW - m4-contract-1.0.**

## Contract-only PR checks

```bash
python -B -m pytest -q -p no:cacheprovider tests/contracts
M4_CONTRACT_IMPLEMENTATION=/absolute/owner-checkout python -B -m pytest -q -p no:cacheprovider tests/contracts
```

The first command checks schemas/examples; implementation tests explicitly SKIP when no implementation path. It is NOT evidence that any owner conformed. The second loads the actual external adapter and tests PASS/FAIL/ERROR, identity/hash/tool/exit tampering and source-only subjects. Synthetic reports/dummy signatures are labeled FIXTURE and cannot prove scanner/signature/runtime success. Never claim schema-only PASS is full conformance.

Freeze acceptance:

- exact shared emitter signature and result/execution schemas;
- invalid data rejected; valid FAIL/ERROR never security_approved;
- no fixture-name/hash-specific production validator;
- actual Gitleaks producer/emitter call is tested (scanner double is labeled);
- workflow uses real CLI options/paths, no M3/literal security PASS;
- v1/v2 frontend consumer unchanged, 68 tests and build preserved;
- all owners agree to this reviewed commit/version and source-scope semantics.

The laboratory has 17 package conformance tests, plus larger root regression and actual source CLI evidence. See [experimental provenance](README.md#experimental-provenance-and-test-interpretation) for source/checkpoint/evidence locations. These specification tests are expected to fail against nonconforming implementations; the 17/17 result belongs to the experimental candidate, not unmodified main. These results support freezing interfaces WITH runtime limitations, not merging untested runtime implementations.

## Mandatory follow-up after owner implementation

- Re-run conformance plus each owner's original suites at exact merged source.
- Source scan: actual pinned tool, clean full history + worktree, same-run raw outputs, findings/raw0 blocks, corruption rejected.
- Build one OCI candidate and verify Git provenance/index/platform/config/archive; confirm supported Buildx exporter output, no manual provenance fabrication.
- Actual Syft and Trivy on that candidate with supported versions/cache; raw exit/report hash/subject and CRITICAL-only policy; missing/invalid/wrong-source/run/subject/hash blocked.
- Actual approved key/bundle/archive verification; unsigned/wrong-key/tampered artifact blocked. No generated lab key called organization-approved.
- Positive gate0 plus fresh wrong-evidence negatives; source-only record must bind to built source. No positive release from fixtures.
- Fresh PG17/bootstrap/runtime role; ready200, POST201/GET200, restart persistence, DB outage503/recovery.
- Isolated staging smoke; command/readiness failures propagate; rollback only to independently approved immutable previous artifact. No destructive volume cleanup.
- Nginx/browser with actual current evidence; HTTP remains UNVERIFIED; fixture FIXTURE; deployment NOT_RUN stays NOT_RUN.
- CI actual run if available; billing block is environment, not code failure. No local simulation called CI PASS.

Academic package acceptance is separate: actual course file 07_css-yeu-cau-package-cuoi-va-lich-danh-gia-vi-v1.md requires report/slides/YouTube15min/all faces/artifacts/README index, peer review/main/final complete-package SHA by 31/10/2026 23:59 VN. No report/slide/video or approval is fabricated by this package. S03 optional, not an M4 blocker.
