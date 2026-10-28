const test = require('node:test');
const assert = require('node:assert/strict');
const { createLoader } = require('./load-ts.cjs');
const load = createLoader();
const { createOrdersService, parseOrder, parseOrders } = load('src/services/orders.ts');
const { ApiError } = load('src/services/apiError.ts');
const { createRequestScope } = load('src/services/requestScope.ts');
const row = { id: 1, customer_name: 'Alice', product_name: 'Widget', quantity: 2, status: 'pending', created_at: '2026-10-19T01:02:03.123456Z' };
const input = { customer_name: ' Alice ', product_name: ' Widget ', quantity: 2 };
const response = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
const service = (fetch, extra = {}) => createOrdersService({ fetch, baseUrl: () => '/api', mockDelayMs: 0, ...extra });
const rejectKind = (promise, kind) => assert.rejects(promise, (error) => error instanceof ApiError && error.kind === kind);
const deferred = () => { let resolve; const promise = new Promise((r) => { resolve = r; }); return { promise, resolve }; };

test('[contract] valid GET and POST call the real adapter with current backend shapes', async () => {
  const calls = [];
  const api = service(async (url, options) => { calls.push([url, options]); return response(options.method === 'POST' ? row : { orders: [row] }, options.method === 'POST' ? 201 : 200); });
  assert.deepEqual(await api.getOrders(), [row]);
  assert.deepEqual(await api.getOrderById(1), row);
  assert.deepEqual(await api.createOrder(input), row);
  assert.equal(calls[0][0], '/api/orders');
  assert.equal(calls[2][1].method, 'POST');
  assert.deepEqual(JSON.parse(calls[2][1].body), { customer_name: 'Alice', product_name: 'Widget', quantity: 2 });
  assert.ok(calls[0][1].signal instanceof AbortSignal);
});

test('[contract] required order fields reject omissions and wrong runtime types', () => {
  for (const field of Object.keys(row)) {
    const missing = { ...row }; delete missing[field];
    assert.throws(() => parseOrder(missing), { kind: 'contract' }, field);
    assert.throws(() => parseOrder({ ...row, [field]: null }), { kind: 'contract' }, field);
  }
  for (const mutation of [{ id: true }, { id: '1' }, { quantity: true }, { quantity: 0 }, { quantity: 1.5 }, { quantity: Number.MAX_SAFE_INTEGER + 1 }, { customer_name: 7 }, { customer_name: ' ' }, { product_name: '' }, { status: 'unknown' }, { created_at: '2026-02-30T01:02:03Z' }, { created_at: 'not a date' }, { created_at: '2026-10-19' }]) {
    assert.throws(() => parseOrder({ ...row, ...mutation }), { kind: 'contract' }, JSON.stringify(mutation));
  }
});

test('[contract] invalid list envelopes, rows and duplicate identities are rejected', async () => {
  for (const body of [null, [], {}, { orders: {} }, { orders: [null] }, { orders: [{ id: 1, customer_name: 7 }] }, { orders: [row, row] }]) {
    await rejectKind(service(async () => response(body)).getOrders(), 'contract');
  }
  assert.deepEqual(parseOrders({ orders: [] }), []);
});

test('[contract] POST rejects empty, mismatched and malformed success responses', async () => {
  for (const body of [{}, null, { orders: [row] }, { ...row, quantity: 3 }, { ...row, customer_name: 'Other' }, { ...row, status: 'shipped' }]) {
    await rejectKind(service(async () => response(body, 201)).createOrder(input), 'contract');
  }
  for (const method of ['getOrders', 'createOrder']) {
    const api = service(async () => new Response('{bad json', { status: method === 'createOrder' ? 201 : 200, headers: { 'Content-Type': 'application/json' } }));
    await rejectKind(api[method](input), 'contract');
  }
});

test('[contract] unexpected success status and content type cannot produce success', async () => {
  await rejectKind(service(async () => response(row, 200)).createOrder(input), 'contract');
  await rejectKind(service(async () => response({ orders: [row] }, 201)).getOrders(), 'contract');
  await rejectKind(service(async () => new Response(JSON.stringify(row), { status: 201, headers: { 'Content-Type': 'text/html' } })).createOrder(input), 'contract');
});

test('[unit] HTTP errors retain status; non-string error fields do not become UI content', async () => {
  for (const error of ['Rejected', { unexpected: 'object' }]) {
    const api = service(async () => response({ error }, 400));
    await assert.rejects(api.getOrders(), (e) => e.status === 400 && typeof e.message === 'string' && e.kind === 'http');
  }
  await assert.rejects(service(async () => new Response('<html>fail</html>', { status: 500 })).getOrders(), { status: 500, kind: 'http' });
});

test('[unit] invalid runtime create input is rejected before any fetch', async () => {
  let calls = 0; const api = service(async () => { calls++; return response(row, 201); });
  for (const value of [null, {}, { ...input, customer_name: 7 }, { ...input, product_name: false }, { ...input, customer_name: '  ' }, ...[true, 0, -1, 1.5, '2', Number.MAX_SAFE_INTEGER + 1].map((quantity) => ({ ...input, quantity }))]) {
    await assert.rejects(api.createOrder(value), { status: 400 });
  }
  assert.equal(calls, 0);
});

test('[unit] offline write rejects, remains live, never retries or inserts a mock order', async () => {
  let calls = 0; const api = service(async () => { calls++; throw new Error('controlled offline'); });
  await assert.rejects(api.createOrder(input), (e) => e.kind === 'network' && e.isNetworkError && /not confirmed/.test(e.message));
  assert.equal(calls, 1); assert.equal(api.getScenario(), 'live');
  api.setScenario('empty'); assert.deepEqual(await api.getOrders(), []);
});

test('[unit] timeout covers both fetch and delayed JSON body; POST outcome stays unconfirmed', async () => {
  const never = () => new Promise(() => {});
  for (const fetch of [never, async () => ({ ok: true, status: 201, headers: new Headers({ 'Content-Type': 'application/json' }), json: never })]) {
    const api = service(fetch, { timeoutMs: 15 });
    await assert.rejects(api.createOrder(input), (e) => e.kind === 'timeout' && /not confirmed/.test(e.message));
    assert.equal(api.getSnapshot().connection, 'unavailable');
  }
});

test('[unit] changing mode cancels a late live result and prevents stale connectivity updates', async () => {
  const late = deferred(), started = deferred(); let signal;
  const api = service(async (_, options) => { signal = options.signal; started.resolve(); return late.promise; });
  const pending = api.getOrders(); const rejected = rejectKind(pending, 'cancelled');
  await started.promise; api.setScenario('empty');
  await rejected; assert.equal(signal.aborted, true);
  late.resolve(response({ orders: [row] }));
  await new Promise((resolve) => setImmediate(resolve));
  assert.deepEqual(await api.getOrders(), []);
  assert.equal(api.getSnapshot().connection, 'unverified');
});

test('[unit] view cancellation and pre-aborted signal do not emit a success or call fetch', async () => {
  let calls = 0; const controller = new AbortController(); controller.abort();
  const api = service(async () => { calls++; return response({ orders: [row] }); });
  await rejectKind(api.getOrders({ signal: controller.signal }), 'cancelled'); assert.equal(calls, 0);
  const live = new AbortController(); const started = deferred();
  const slow = service(async () => { started.resolve(); return new Promise(() => {}); });
  const pending = slow.getOrders({ signal: live.signal }); const rejected = rejectKind(pending, 'cancelled');
  await started.promise; live.abort(); await rejected;
  assert.equal(slow.getSnapshot().connection, 'unverified');
});

test('[unit] stale mock writes are cancelled before they modify the new selection', async () => {
  const api = service(async () => { throw Error('unexpected fetch'); }, { initialScenario: 'empty', mockDelayMs: 15 });
  const pending = api.createOrder(input); const rejected = rejectKind(pending, 'cancelled');
  api.setScenario('populated'); await rejected;
  await new Promise((resolve) => setTimeout(resolve, 25));
  assert.equal((await api.getOrders()).length, 8);
});

test('[unit] empty mock create -> list -> detail is consistent; stores are isolated', async () => {
  const api = service(async () => { throw Error('unexpected fetch'); }, { initialScenario: 'empty' });
  assert.deepEqual(await api.getOrders(), []);
  const created = await api.createOrder(input);
  assert.deepEqual(await api.getOrders(), [created]);
  assert.deepEqual(await api.getOrderById(created.id), created);
  const copy = await api.getOrders(); copy[0].customer_name = 'mutated';
  assert.equal((await api.getOrderById(created.id)).customer_name, 'Alice');
  const other = service(async () => response({ orders: [] }), { initialScenario: 'empty' });
  assert.deepEqual(await other.getOrders(), []);
  api.resetData(); assert.deepEqual(await api.getOrders(), []);
});

test('[unit] connectivity is observed, resets with selection, and liveness never proves readiness', async () => {
  const api = service(async (url) => response(url.endsWith('/health') ? { status: 'ok' } : { orders: [] }));
  assert.equal(api.isLiveMode(), true); assert.equal(api.getSnapshot().connection, 'unverified');
  let events = 0; const unsubscribe = api.subscribe(() => events++);
  await api.getOrders(); assert.equal(api.getSnapshot().connection, 'responding'); assert.ok(api.getSnapshot().observedAt);
  assert.equal((await api.checkHealth()).isLive, true);
  api.setScenario('live'); assert.equal(api.getSnapshot().connection, 'unverified'); assert.equal(api.getSnapshot().observedAt, undefined);
  assert.ok(events >= 3); unsubscribe();
  const bad = service(async () => response({ status: 'unready' }));
  assert.equal((await bad.checkHealth()).isLive, false); assert.equal(bad.getSnapshot().connection, 'error');
});

test('[unit] earlier same-mode responses cannot overwrite latest connectivity observations', async () => {
  const late = deferred(); let calls = 0;
  const api = service(async () => ++calls === 1 ? late.promise : response({ error: 'unavailable' }, 503));
  const first = api.getOrders(); await new Promise((r) => setImmediate(r));
  await assert.rejects(api.getOrders(), { status: 503 });
  late.resolve(response({ orders: [row] })); await first;
  assert.equal(api.getSnapshot().connection, 'error');
});

test('[unit] latest view request guards data, errors, loading and unmount cleanup', async () => {
  const scope = createRequestScope(); let view = 'loading';
  const late = deferred(); const first = scope.start();
  const settle = late.promise.catch(() => { if (first.isCurrent()) view = 'error'; }).finally(() => { if (first.isCurrent()) view = 'finished-old'; });
  const second = scope.start(); assert.equal(first.signal.aborted, true);
  if (second.isCurrent()) view = 'new-data';
  late.resolve(); await settle; assert.equal(view, 'new-data');
  scope.cancel(); assert.equal(second.isCurrent(), false); assert.equal(second.signal.aborted, true);
});

test('[unit] switching live -> mock -> live still rejects the first selection result', async () => {
  const late = deferred(), started = deferred();
  const api = service(async () => { started.resolve(); return late.promise; });
  const first = api.getOrders(); const rejected = rejectKind(first, 'cancelled');
  await started.promise; api.setScenario('empty'); api.setScenario('live'); await rejected;
  late.resolve(response({ orders: [row] })); await new Promise((resolve) => setImmediate(resolve));
  assert.equal(api.getSnapshot().connection, 'unverified'); assert.equal(api.getSnapshot().revision, 2);
});
