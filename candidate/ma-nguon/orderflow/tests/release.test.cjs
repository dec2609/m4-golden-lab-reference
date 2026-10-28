const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createLoader } = require('./load-ts.cjs');
const load = createLoader();
const { validateReleaseStatus: validate, validateReleaseJson, inspectReleaseEvidence, releaseService } = load('src/services/release.ts');
const fixtures = load('src/mocks/release.ts');
const copy = (version = 2) => structuredClone(fixtures[version === 1 ? 'mockReleaseV1Pass' : 'mockReleaseV2Pass']);
function rejectMutation(mutate, version = 2) {
  const payload = copy(version); mutate(payload); const result = validate(payload);
  assert.equal(result.isValid, false); assert.equal(result.data, undefined); assert.ok(result.errorReason);
}

test('[F1 contract] pre-deploy NOT_RUN preserves reported production PASS or BLOCKED', () => {
  for (const production of ['PASS', 'BLOCKED']) {
    const payload = copy();
    payload.PRODUCTION_GATE = production;
    payload.deployment = { READINESS_STATUS: 'NOT_RUN', API_STATUS: 'NOT_RUN', DEPLOYMENT_GATE: 'NOT_RUN', ROLLBACK_STATUS: 'NOT_REQUIRED' };
    const result = validate(payload);
    assert.equal(result.isValid, true, result.errorReason);
    assert.equal(result.data.PRODUCTION_GATE, production);
    assert.equal(result.data.deployment.DEPLOYMENT_GATE, 'NOT_RUN');
  }
});

test('[F1 contract] v2 requires complete deployment and registry even when production is BLOCKED', () => {
  const blocked = copy();
  blocked.PRODUCTION_GATE = 'BLOCKED';
  blocked.controls.REGISTRY_STATUS = 'FAIL';
  blocked.deployment = { READINESS_STATUS: 'FAIL', API_STATUS: 'FAIL', DEPLOYMENT_GATE: 'FAIL', ROLLBACK_STATUS: 'NOT_REQUIRED' };
  assert.equal(validate(blocked).isValid, true);
  const reject = mutate => {
    const payload = structuredClone(blocked); mutate(payload);
    const result = validate(payload);
    assert.equal(result.isValid, false); assert.equal(result.data, undefined);
  };
  for (const key of ['registry', 'deployment']) reject(p => { delete p[key]; });
  for (const key of Object.keys(blocked.deployment)) reject(p => { delete p.deployment[key]; });
  for (const key of ['image_reference', 'image_digest']) reject(p => { delete p.registry[key]; });
  for (const value of [null, [], {}, { image_reference: '' }, { image_digest: 'bad' }]) reject(p => { p.registry = value; });
});

test('[F1 contract] NOT_RUN cannot contain executed probes or rollback outcomes', () => {
  for (const field of ['READINESS_STATUS', 'API_STATUS', 'ROLLBACK_STATUS']) {
    for (const value of ['PASS', 'FAIL']) {
      rejectMutation(p => {
        p.deployment = { READINESS_STATUS: 'NOT_RUN', API_STATUS: 'NOT_RUN', DEPLOYMENT_GATE: 'NOT_RUN', ROLLBACK_STATUS: 'NOT_REQUIRED', [field]: value };
      });
    }
  }
});

test('[F1 contract] strict deployment enums reject unknown, null and unagreed rollback NOT_RUN', () => {
  for (const field of Object.keys(copy().deployment)) {
    for (const value of ['UNKNOWN', 'ERROR', 'INFRA_BLOCKED', '', null, true]) rejectMutation(p => { p.deployment[field] = value; });
  }
  rejectMutation(p => { p.deployment.ROLLBACK_STATUS = 'NOT_RUN'; });
  for (const field of ['READINESS_STATUS', 'API_STATUS']) rejectMutation(p => { p.deployment[field] = 'NOT_RUN'; });
  for (const field of ['READINESS_STATUS', 'API_STATUS']) rejectMutation(p => { p.deployment.DEPLOYMENT_GATE = 'FAIL'; p.deployment[field] = 'NOT_RUN'; });
  rejectMutation(p => { p.source_commit = 'abcdef0'; });
});

test('[F1 contract] failed deployment supports reported rollback outcomes without inferring deployment PASS', () => {
  for (const rollback of ['PASS', 'FAIL', 'NOT_REQUIRED']) {
    const payload = copy();
    payload.deployment = { READINESS_STATUS: 'PASS', API_STATUS: 'PASS', DEPLOYMENT_GATE: 'FAIL', ROLLBACK_STATUS: rollback };
    const result = validate(payload);
    assert.equal(result.isValid, true, result.errorReason);
    assert.equal(result.data.deployment.DEPLOYMENT_GATE, 'FAIL');
  }
});

test('[contract] existing v1 schema fields and real historical BLOCKED payload remain compatible', () => {
  const schema = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../../../cau-hinh/release-status.schema.v1.json'), 'utf8'));
  for (const fixture of [fixtures.mockReleaseV1Pass, fixtures.mockReleaseV1Blocked]) {
    assert.equal(validate(fixture).isValid, true);
    assert.deepEqual(Object.keys(fixture).sort(), [...schema.required].sort());
    for (const field of ['source_commit', 'artifact_sha256', 'image_digest']) assert.match(fixture[field], new RegExp(schema.properties[field].pattern));
  }
  const historical = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../../../bang-chung/m3/release-gate/release-status.json'), 'utf8'));
  assert.equal(validate(historical).isValid, true);
});

test('[contract] all supported demo fixtures validate without making authenticity claims', () => {
  for (const key of ['mockReleaseV1Pass', 'mockReleaseV1Blocked', 'mockReleaseV2Pass', 'mockReleaseV2PreDeploy', 'mockReleaseV2Blocked', 'mockReleaseV2Rollback']) {
    assert.equal(validate(fixtures[key]).isValid, true, key);
  }
  assert.equal(validate(fixtures.mockReleaseInvalid).isValid, false);
});

test('[contract] every mandatory control FAIL or missing rejects production PASS in v1/v2', () => {
  for (const version of [1, 2]) for (const key of Object.keys(copy(version).controls)) {
    rejectMutation((p) => { p.controls[key] = 'FAIL'; }, version);
    rejectMutation((p) => { delete p.controls[key]; }, version);
    rejectMutation((p) => { p.controls[key] = 'UNKNOWN'; }, version);
  }
});

test('[contract] BLOCKED is never upgraded to PASS even when all controls report PASS', () => {
  for (const version of [1, 2]) {
    const payload = copy(version); payload.PRODUCTION_GATE = 'BLOCKED';
    if (version === 2) payload.deployment = structuredClone(fixtures.mockReleaseV2PreDeploy.deployment);
    const result = validate(payload); assert.equal(result.isValid, true); assert.equal(result.data.PRODUCTION_GATE, 'BLOCKED');
  }
});

test('[contract] strict identities, object shapes, schema version and v1 unknown fields', () => {
  for (const value of [null, [], 'PASS', 7]) assert.equal(validate(value).isValid, false);
  for (const version of [1, 2]) {
    for (const field of ['source_commit', 'artifact_sha256', 'image_digest']) {
      for (const value of ['', 'x', null, 1, ' A '.repeat(40)]) rejectMutation((p) => { p[field] = value; }, version);
    }
    rejectMutation((p) => { p.controls = []; }, version);
    rejectMutation((p) => { p.PRODUCTION_GATE = 'SUCCESS'; }, version);
  }
  rejectMutation((p) => { p.extra = true; }, 1);
  rejectMutation((p) => { p.controls.EXTRA_STATUS = 'PASS'; }, 1);
  rejectMutation((p) => { p.schema_version = 3; });
});

test('[contract] registry PASS requires complete well-formed metadata and consistent digests', () => {
  for (const value of [undefined, null, [], {}, { image_digest: copy().image_digest }, { image_reference: 'ghcr.io/team/order-app:v1' }]) {
    rejectMutation((p) => { p.registry = value; });
  }
  for (const value of ['x', 'sha256:bad', 'sha256:' + 'A'.repeat(64), 'sha256:' + 'b'.repeat(64)]) rejectMutation((p) => { p.registry.image_digest = value; });
  for (const value of ['', ' ', 'https://ghcr.io/team/app', 'invalid reference', 7]) rejectMutation((p) => { p.registry.image_reference = value; });
  rejectMutation((p) => { p.registry.image_reference = 'ghcr.io/team/app@sha256:' + 'b'.repeat(64); });
});

test('[contract] deployment PASS requires production, readiness and API PASS', () => {
  rejectMutation((p) => { p.PRODUCTION_GATE = 'BLOCKED'; });
  for (const field of ['READINESS_STATUS', 'API_STATUS']) for (const value of ['FAIL', undefined, 'UNKNOWN', true]) {
    rejectMutation((p) => { p.deployment[field] = value; });
  }
  for (const value of [null, [], {}, { DEPLOYMENT_GATE: 'UNKNOWN' }]) rejectMutation((p) => { p.deployment = value; });
});

test('[contract] missing v2 deployment rejects the payload; v1 does not require deployment', () => {
  rejectMutation(p => { delete p.deployment; });
  assert.equal(validate(copy(1)).isValid, true);
});

test('[contract] contradictory rollback results and non-string enums are rejected', () => {
  for (const value of ['PASS', 'FAIL', {}, 'EXECUTED']) rejectMutation((p) => { p.deployment.ROLLBACK_STATUS = value; });
  const payload = structuredClone(fixtures.mockReleaseV2Rollback);
  assert.equal(validate(payload).isValid, true); // reported result, not evidence of restoration
  payload.PRODUCTION_GATE = 'BLOCKED'; assert.equal(validate(payload).isValid, false);
});

test('[contract] malformed or contradictory transport JSON never supplies a decision', () => {
  assert.equal(validateReleaseJson('{bad').isValid, false);
  const payload = copy(); payload.controls.COSIGN_STATUS = 'FAIL';
  assert.equal(validateReleaseJson(JSON.stringify(payload)).isValid, false);
  assert.equal(validateReleaseJson(JSON.stringify(copy(1))).isValid, true);
});

test('[unit] ingestion preparation labels even valid source data UNVERIFIED', async () => {
  const result = await inspectReleaseEvidence({ description: 'test source only', read: async () => copy() });
  assert.equal(result.isValid, true); assert.equal(result.authenticity, 'UNVERIFIED'); assert.equal(result.source, 'test source only');
  const unavailable = await inspectReleaseEvidence({ description: 'unavailable test source', read: async () => { throw Error('offline'); } });
  assert.equal(unavailable.isValid, false); assert.equal(unavailable.data, undefined);
  const invalid = await inspectReleaseEvidence({ description: 'invalid test source', read: async () => ({ PRODUCTION_GATE: 'PASS' }) });
  assert.equal(invalid.isValid, false);
  const controller = new AbortController(); controller.abort();
  const cancelled = await inspectReleaseEvidence({ description: 'cancelled source', read: async () => copy() }, controller.signal);
  assert.equal(cancelled.isValid, false); assert.equal(cancelled.data, undefined);
});

test('[unit] release fixture changes reject stale loads and returned fixtures cannot be mutated globally', async () => {
  releaseService.setScenario('v2-pass'); const old = releaseService.getReleaseStatus();
  const rejected = assert.rejects(old, /stale/); releaseService.setScenario('v2-blocked'); await rejected;
  const value = await releaseService.getReleaseStatus(); value.PRODUCTION_GATE = 'PASS';
  assert.equal((await releaseService.getReleaseStatus()).PRODUCTION_GATE, 'BLOCKED');
  releaseService.setScenario('v2-pass'); const aba = releaseService.getReleaseStatus();
  const rejectAba = assert.rejects(aba, /stale/);
  releaseService.setScenario('v2-blocked'); releaseService.setScenario('v2-pass'); await rejectAba;
  releaseService.setScenario('unsupported'); await assert.rejects(releaseService.getReleaseStatus(), /unavailable/);
});
