const test = require('node:test');
const assert = require('node:assert/strict');
const { createLoader } = require('./load-ts.cjs');
const load = createLoader();
const { createHttpEvidenceSource, inspectEvidence, readEvidence } = load('src/services/releaseEvidence.ts');
const { getJson } = load('src/services/jsonTransport.ts');
const { createRequestScope } = load('src/services/requestScope.ts');
const { checkReadiness } = load('src/services/readiness.ts');
const fixtures = load('src/mocks/release.ts');
const clone = () => structuredClone(fixtures.mockReleaseV2Pass);
const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
const reason = kind => error => error.kind === kind;

test('[F1 HTTP double] pre-deploy remains UNVERIFIED and invalid data supplies no old decision', async () => {
  for (const production of ['PASS', 'BLOCKED']) {
    const payload = structuredClone(fixtures.mockReleaseV2PreDeploy);
    payload.PRODUCTION_GATE = production;
    payload.authenticity = 'VERIFIED';
    const source = createHttpEvidenceSource('/__f1_fixture__/release.json', { fetch: async () => json(payload) });
    const result = await readEvidence(source);
    assert.equal(result.state, 'ready'); assert.equal(result.authenticity, 'UNVERIFIED');
    assert.equal(result.provenance, 'MISSING');
    assert.equal(result.data.PRODUCTION_GATE, production);
    assert.equal(result.data.deployment.DEPLOYMENT_GATE, 'NOT_RUN');
    assert.equal(inspectEvidence(payload, { source: 'Explicit F1 fixture', fixture: true }).authenticity, 'FIXTURE');
    delete payload.deployment.API_STATUS;
    const invalid = await readEvidence(source);
    assert.equal(invalid.state, 'invalid'); assert.equal(invalid.data, undefined);
    assert.equal(invalid.authenticity, 'UNVERIFIED');
  }
});

test('[D3 contract] fixtures and HTTP JSON cannot self-upgrade to VERIFIED', async () => {
  const payload = clone(); payload.authenticity = 'VERIFIED'; payload.signature_verified = true;
  const result = await readEvidence(createHttpEvidenceSource('/release.json', { fetch: async () => json(payload) }));
  assert.equal(result.state, 'ready'); assert.equal(result.authenticity, 'UNVERIFIED');
  assert.equal(inspectEvidence(clone(), { source: 'labelled fixture', fixture: true }).authenticity, 'FIXTURE');
});
test('[D3 contract] v1 remains valid; expected identity mismatch fails closed', () => {
  const data = structuredClone(fixtures.mockReleaseV1Pass);
  assert.equal(inspectEvidence(data, { source: 'v1' }).state, 'ready');
  for (const key of ['source_commit','artifact_sha256','image_digest']) {
    const inspected = inspectEvidence(data, { source: 'v1', expected: { [key]: 'wrong' } });
    assert.equal(inspected.state, 'invalid'); assert.equal(inspected.data, undefined);
  }
});
test('[D3 contract] proposed provenance rejects mismatch, stale, future, invalid dates and missing fields', () => {
  const now = Date.parse('2026-10-19T10:00:00Z');
  const base = clone();
  base.provenance = { run_id: 'fixture-run', generated_at: '2026-10-19T09:59:00Z', source_commit: base.source_commit };
  const inspect = data => inspectEvidence(data, { source: 'synthetic provenance', now });
  assert.equal(inspect(base).state, 'ready'); assert.equal(inspect(base).provenance, 'CONSISTENT');
  assert.equal(inspect(base).authenticity, 'UNVERIFIED');
  for (const generated_at of ['2026-10-17T10:00:00Z', '2026-10-20T10:00:00Z', '2026-02-30T10:00:00Z','not-date']) {
    assert.equal(inspect({ ...base, provenance: { ...base.provenance, generated_at } }).state, 'invalid');
  }
  for (const provenance of [null, [], {}, { ...base.provenance, source_commit: 'b'.repeat(40) }]) {
    assert.equal(inspect({ ...base, provenance }).state, 'invalid');
  }
  assert.equal(inspect(clone()).provenance, 'MISSING');
});
test('[D3 contract] empty, malformed, contradictory data never supplies a valid release', async () => {
  for (const body of [null, [], {}, { ...clone(), controls: {} }]) {
    const result = await readEvidence(createHttpEvidenceSource('/release.json', { fetch: async () => json(body) }));
    assert.notEqual(result.state, 'ready'); assert.equal(result.data, undefined);
  }
  const bad = clone(); bad.controls.COSIGN_STATUS = 'FAIL';
  assert.equal(inspectEvidence(bad, { source: 'negative' }).state, 'invalid');
  await assert.rejects(readEvidence(createHttpEvidenceSource('/release.json', { fetch: async () => new Response('{broken', { headers: { 'Content-Type':'application/json' } }) })), reason('contract'));
  assert.equal((await readEvidence(createHttpEvidenceSource('/release.json', { fetch: async () => new Response(null, { status:204 }) }))).state, 'empty');
});
test('[D3 transport] path boundary rejects external/credential/query/traversal URLs', () => {
  for (const path of ['https://evil.test/x','//evil.test/x','/x?token=secret','/../x','/x#fragment','/x\\evil']) {
    assert.throws(() => createHttpEvidenceSource(path));
  }
});
test('[D3 transport] HTTP failure, HTML success, oversized/invalid stream reject with no fallback/retry', async () => {
  for (const response of [new Response('down', {status:500}), new Response('<html>SPA</html>', {headers:{'Content-Type':'text/html'}}),
    new Response('{}', {headers:{'Content-Type':'application/json','Content-Length':'9999999'}})]) {
    let calls=0;
    await assert.rejects(readEvidence(createHttpEvidenceSource('/release.json', {fetch:async()=>{calls++;return response;}})));
    assert.equal(calls,1);
  }
  await assert.rejects(getJson('/x', { maxBytes: 3, fetch: async()=>json({ big:'abc' }) }), reason('contract'));
});
test('[D3 transport] timeout covers stalled headers and body; cancellation works even if fetch ignores signal', async () => {
  await assert.rejects(getJson('/x', {timeoutMs:10,fetch:()=>new Promise(()=>{})}), reason('timeout'));
  await assert.rejects(getJson('/x', {timeoutMs:10,fetch:async()=>new Response(new ReadableStream({start(){}}),{headers:{'Content-Type':'application/json'}})}), reason('timeout'));
  const controller=new AbortController();
  const pending=getJson('/x', {signal:controller.signal,fetch:()=>new Promise(()=>{})});
  controller.abort(); await assert.rejects(pending,reason('cancelled'));
  const aborted=new AbortController();aborted.abort();let called=false;
  await assert.rejects(getJson('/x',{signal:aborted.signal,fetch:async()=>{called=true;return json({});}}),reason('cancelled'));
  assert.equal(called,false);
});
test('[D3 unit] latest request scope rejects late evidence completion', async () => {
  const scope=createRequestScope();const old=scope.start();let finish;
  const pending=readEvidence({description:'delayed fixture',read:()=>new Promise(resolve=>{finish=resolve;})},{signal:old.signal});
  const current=scope.start();finish(clone());
  await assert.rejects(pending,/cancelled/);assert.equal(old.isCurrent(),false);assert.equal(current.isCurrent(),true);
});
test('[readiness M4 simulated] ready/unready/not-implemented are distinct from API liveness', async () => {
  const cases=[[200,{status:'ready',database:'connected'},'READY'],[503,{status:'unready',error:'database unreachable'},'UNREADY'],[404,null,'NOT_IMPLEMENTED']];
  for (const [status,body,expected]of cases) {
    const result=await checkReadiness({baseUrl:'/api',simulated:true,fetch:async()=>status===404?new Response('HTML 404',{status}):json(body,status)});
    assert.equal(result.state,expected);assert.equal(result.origin,'SIMULATED');
  }
  for (const [status,body]of [[200,{status:'ok'}],[200,{status:'ready',database:'disconnected'}],[503,{status:'ready',database:'connected'}]]) {
    await assert.rejects(checkReadiness({simulated:true,fetch:async()=>json(body,status)}),reason('contract'));
  }
});
test('[readiness simulated] deadline/cancel fail closed',async()=>{
  await assert.rejects(checkReadiness({timeoutMs:10,simulated:true,fetch:()=>new Promise(()=>{})}),reason('timeout'));
  const c=new AbortController();c.abort();
  await assert.rejects(checkReadiness({signal:c.signal,simulated:true}),reason('cancelled'));
});
test('[presentation SSR] simulated readiness is explicitly labelled, never live DB evidence',async()=>{
  const React=require('react');const {renderToStaticMarkup}=require('react-dom/server');
  const {ReadinessView}=load('src/components/orders/ReadinessNotice.tsx');
  const html=renderToStaticMarkup(React.createElement(ReadinessView,{observation:{state:'READY',origin:'SIMULATED',observedAt:'fixture'}}));
  assert.match(html,/SIMULATED test double/);assert.match(html,/no database verification/);
});

test('[F16 unit] recent orders sort newest first without mutating API data',()=>{
  const {recentOrders}=load('src/lib/orderPresentation.ts');
  const rows=[{id:1,created_at:'2026-10-18T00:00:00Z'},{id:2,created_at:'2026-10-19T00:00:00Z'},{id:3,created_at:'2026-10-19T00:00:00Z'}];
  assert.deepEqual(recentOrders(rows,2).map(o=>o.id),[3,2]);assert.deepEqual(rows.map(o=>o.id),[1,2,3]);
});
test('[F16 unit] timestamp display explicitly uses UTC independent of host timezone',()=>{
  const {formatUtcOrderDate}=load('src/lib/orderPresentation.ts');
  assert.match(formatUtcOrderDate('2026-10-19T01:15:00Z'),/1:15 AM UTC$/);
  assert.equal(formatUtcOrderDate('invalid'),'invalid');
});
