# Proposed M4 contract-only PR package

Version: **m4-contract-1.0 / PROPOSED_FOR_TEAM_REVIEW**.

Start at [CONTRACT](CONTRACT.md). Then [SCHEMA](SCHEMA.md), [WORKFLOW](WORKFLOW.md), [OWNER-MATRIX](OWNER-MATRIX.md), [ACCEPTANCE](ACCEPTANCE.md).

Contents: normative docs, JSON schemas, explicitly synthetic examples and conformance tests ONLY. No owner runtime replacements, workflow YAML, logs, key, scanner binary or laboratory evidence. tests/contracts/_fixture.py is a test-data constructor, not runtime code.

Prerequisites: Python with `pytest` and `jsonschema` available. Tests do not install dependencies or execute scanners.

Run `python -B -m pytest -q -p no:cacheprovider tests/contracts`; without M4_CONTRACT_IMPLEMENTATION the implementation cases explicitly skip. Set the variable to an owner checkout to verify conformance. See acceptance for limitations and required real-runtime follow-up.

For Thuận: review these paths and propose ONE contract-only PR; do not include sibling candidate/, patches/ or evidence/. This publication proposes the contract for team review; it does not claim owner implementation or runtime completion. All owner implementations must reference the eventual reviewed contract PR SHA.

## Experimental provenance and test interpretation

- Verified package checkpoint: `5cba5d2e45f946865737dfec5762427e8a7de6e5`.
- Experimental implementation: `53f18d8b5689a25bc03b647b54eb1a4ba0cd78ef`.
- Laboratory: `M4-golden-candidate-lab/contract-experiment-20261027-s9irmc29/`.
- Local experiment evidence: SOURCE-MANIFEST.json, EXPERIMENT-RESULTS.md, TEST-MATRIX.md, EXECUTION-LEDGER.jsonl, evidence/frozen-source-run/unit.junit.xml, evidence/package-checkpoint.log. These are local laboratory artifacts, NOT files shipped in this PR.
- Results reported and checked from that experiment: root255/255, contract17/17, frontend68/68, backend18/18 DB doubles; typechecks/build passed. These results belong to the experimental source, not unmodified main or this contract-only branch.
- Full M4 runtime, real same-candidate scanners/signature, PostgreSQL persistence, staging/rollback and browser acceptance remain NOT_VERIFIED.

[Specification tests](../../tests/contracts/test_contract.py) exercise the proposed interface. Default schema-only execution deliberately skips implementation cases. When M4_CONTRACT_IMPLEMENTATION points to an existing nonconforming owner checkout, failures are expected and must not be interpreted as a regression caused by this documentation PR. The 17/17 result was obtained against the experimental candidate. No current owner implementation is certified by publishing this contract.
