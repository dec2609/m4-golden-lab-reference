// F2 contracts against PR14 f31755a; every HTTP response here is an explicit double.
const test = require('node:test');
const assert = require('node:assert/strict');
const { createLoader } = require('./load-ts.cjs');
const load = createLoader();
const { checkReadiness } = load('src/services/readiness.ts');
const { createOrdersService } = load('src/services/orders.ts');
const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
const ready = { status: 'ready', database: 'connected' };
const unready = { status: 'unready', error: 'database unreachable' };

test('[F2 HTTP double] M4 readiness uses /api/ready and preserves 200/503/404 distinctions', async () => {
  for (const [status, body, state] of [[200, ready, 'READY'], [503, unready, 'UNREADY'], [404, null, 'NOT_IMPLEMENTED']]) {
    const result = await checkReadiness({ baseUrl: '/api', simulated: true, fetch: async (url, options) => {
      assert.equal(url, '/api/ready'); assert.equal(options.method, 'GET');
      assert.equal(options.redirect, 'error'); assert.equal(options.cache, 'no-store');
      return status === 404 ? new Response('Backend route absent', { status }) : json(body, status);
    } });
    assert.equal(result.state, state); assert.equal(result.origin, 'SIMULATED');
    assert.ok(Number.isFinite(Date.parse(result.observedAt)));
  }
});

test('[F2 HTTP double] contradictory and incomplete M4 readiness bodies never confirm a database', async () => {
  for (const [status, body] of [
    [200, { status: 'ok' }], [200, { status: 'ready', database: 'disconnected' }],
    [200, { ...ready, error: 'contradictory failure' }],
    [503, { status: 'ready', database: 'connected' }], [503, { status: 'unready' }],
    [503, { ...unready, error: '' }], [503, { ...unready, error: 42 }],
    [503, { ...unready, database: 'connected' }], [200, null], [503, []],
  ]) {
    await assert.rejects(checkReadiness({ simulated: true, fetch: async () => json(body, status) }), { kind: 'contract' });
  }
});

test('[F2 HTTP double] transport errors, HTML and malformed JSON are errors, not readiness PASS', async () => {
  for (const response of [
    new Response('SPA HTML', { headers: { 'Content-Type': 'text/html' } }),
    new Response('{broken', { headers: { 'Content-Type': 'application/json' } }),
    json({ error: 'Internal server error' }, 500), new Response(null, { status: 204 }),
  ]) {
    let calls = 0;
    await assert.rejects(checkReadiness({ simulated: true, fetch: async () => { calls++; return response; } }));
    assert.equal(calls, 1, 'no automatic retry');
  }
  await assert.rejects(checkReadiness({ simulated: true, fetch: async () => { throw Error('network unavailable'); } }), { kind: 'network' });
});

test('[F2 HTTP double] readiness deadline covers the body and mid-request cancellation', async () => {
  await assert.rejects(checkReadiness({ timeoutMs: 15, simulated: true, fetch: async () =>
    new Response(new ReadableStream({ start() {} }), { headers: { 'Content-Type': 'application/json' } }) }), { kind: 'timeout' });
  const controller = new AbortController();
  const pending = checkReadiness({ signal: controller.signal, simulated: true, fetch: () => new Promise(() => {}) });
  controller.abort(); await assert.rejects(pending, { kind: 'cancelled' });
});

test('[F2 HTTP double] readiness recovers independently of successful /health', async () => {
  const health = createOrdersService({ fetch: async url => {
    assert.equal(url, '/api/health'); return json({ status: 'ok' });
  }, baseUrl: () => '/api' });
  for (const [status, body, expected] of [[200, ready, 'READY'], [503, unready, 'UNREADY'], [200, ready, 'READY']]) {
    assert.equal((await health.checkHealth()).status, 'ok');
    const observed = await checkReadiness({ baseUrl: '/api', simulated: true, fetch: async () => json(body, status) });
    assert.equal(observed.state, expected); assert.equal(observed.origin, 'SIMULATED');
  }
});
