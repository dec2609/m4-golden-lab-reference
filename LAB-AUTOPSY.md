# Laboratory autopsy ? 27/10/2026

The historical 201/201 result belongs to **fa6daef97dabdaf0ff853676634a60e4c41c65c2**, not this candidate or current main. Verified existing `../lab-evidence/integrated-candidate-20261025/assembled-source.json` and `final-sha-python-suite.log` (201 passed in24.73s). Existing reports were read, not edited.

## Actual historical inputs

Main12771681f228a054e9cbde7bcbdc55c271f1da62; PR12 513b78a976a24cd18cf110d5f149e529896605b4; PR13 8030fd053a20e560b8222166f52b0a844d69373a; PR14 3cead23c17e2b4a8d9692f5ad962268ec6345c05; PR15 55aa907c41dda4183ef133aee9493b7b4d36a784; PR16 e58eb574af1b299cd64fa9f85feed77b74ce6f18. Source provenance and local semantic imports are recorded in ../INTEGRATED-CANDIDATE-MANIFEST.md and old provenance/fix-provenance.json. That candidate used selected owner paths and local fixes, not five current PR HEADs.

Lab-only fixes included exact/typed gate validation, adapter context, source archive/executable checks, DB role mount/attributes, readiness and rollback checks. Historical root tests included fixture reports, subprocess/scanner/Cosign/deployment doubles. Frontend68 were module/SSR/contract tests; backend18 used DB doubles. Historical two real-DB tests could not run successfully without DB. They were not persistence proof.

Actual historical source CLI stopped on Windows platform, build stopped resource guard, scanner runner lacked image/tools, gate rejected incomplete candidate and HTTP404 was rejected. Dependency standalone policy really ran. The workflow still had M3 paths, with no complete build-once release. There was no current signed artifact, trusted positive gate, fresh integrated PG runtime or rollback. No owner approval/external acceptance was produced. Thus 201 PASS was logic evidence, never final integrated acceptance.

## Reuse rules

Old logs remain valid historical observations at their own SHA only. Reuse old negative scenarios and design lessons; do NOT reuse reports as current run inputs, counts as current regression, or old candidate as current main. Current experiment freshly fetched six refs and assembled checkpointaf25ea8f4220e032e4b739f8be204e116fb7e025; final53f18d8b5689a25bc03b647b54eb1a4ba0cd78ef. See [SOURCE-MANIFEST](SOURCE-MANIFEST.json).

PR13/14 are already merged into frozen main; PR15 is an ancestor of PR12. Merge frozen main with PR12 then PR16, without duplicate cherry-picks. Windows long-path checkout failed partway; all175 materialized untracked files were blob-verified against PR16 and checkpointed before completing merge. No reset/clean/delete. Assembly and resolutions are in assembly.log, partial-pr16-paths.txt, implementation-notes.txt and local Git history.

## Why the new work is different

The candidate executes actual source producer, dependency policy and pytest/JUnit through one CLI. Its validity/approval distinction is proven with real ERROR records as well as fixtures. A single canonical adapter is consumed by gate and producers; the contract-only package contains no replacement owner runtime code. Artifact/runtime gaps remain explicit, not disguised by the larger255 test count.
