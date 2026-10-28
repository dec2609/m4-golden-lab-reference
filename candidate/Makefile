# PROPOSED_REFERENCE_CHANGE: explicit isolated M4 run; no historical status inputs.
SHELL := bash
.PHONY: test-gate verify release-gate artifact-security

test-gate:
	python -B -m pytest -q -p no:cacheprovider tests/test_production_gate.py tests/test_contract_freeze.py

verify:
	@test -n "$(RUN_DIR)" || (echo 'RUN_DIR outside checkout required'; exit 2)
	python -B scripts/run_m4_workflow.py --phase source --run-dir "$(RUN_DIR)"

release-gate:
	@test -n "$(CANDIDATE)" -a -n "$(RUN_DIR)" -a -n "$(KEY_PIN)" || exit 2
	python -B scripts/production_gate.py --candidate "$(CANDIDATE)" --run-dir "$(RUN_DIR)" --trusted-key-sha256 "$(KEY_PIN)"

artifact-security:
	@test -n "$(RUN_DIR)" -a -n "$(IMAGE)" -a -n "$(SOURCE_GIT_CONTEXT)" || exit 2
	python -B scripts/artifact_security.py --run-dir "$(RUN_DIR)" --image "$(IMAGE)" --source-git-context "$(SOURCE_GIT_CONTEXT)"
