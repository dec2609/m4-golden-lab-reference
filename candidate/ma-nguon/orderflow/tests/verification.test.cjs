const test = require('node:test');
const assert = require('node:assert/strict');
const { buildReport } = require('../verify_m4_frontend.cjs');

test('[unit] verification report reflects failure or execution error without reporting PASS', () => {
  for (const [status, expected] of [[1, 'FAIL'], [null, 'ERROR']]) {
    const report = buildReport({ status, stdout: 'controlled test output', stderr: '' }, { test: true });
    assert.match(report, new RegExp(`UNIT_CONTRACT_PRESENTATION_STATUS=${expected}`));
    assert.doesNotMatch(report, /UNIT_CONTRACT_PRESENTATION_STATUS=PASS/);
  }
});

test('[unit] even a passing unit run discloses unexecuted integration/E2E and security checks', () => {
  const report = buildReport({ status: 0, stdout: '', stderr: '' }, { test: true });
  assert.match(report, /UNIT_CONTRACT_PRESENTATION_STATUS=PASS/);
  for (const name of ['INTEGRATION', 'BROWSER_E2E', 'BACKEND_POSTGRESQL_E2E', 'SECURITY_TOOLS_REGISTRY_DEPLOYMENT_ROLLBACK']) {
    assert.match(report, new RegExp(`${name}_STATUS=NOT_RUN`));
  }
  assert.doesNotMatch(report, /daemon is not running|Local PostgreSQL: Not running|successfully triggered and restored/);
});
