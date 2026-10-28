// Standalone frontend contracts: explicit fixtures/doubles, no release evidence or PR imports.
const test = require('node:test');
const assert = require('node:assert/strict');
const React = require('react');
const { createLoader } = require('./load-ts.cjs');
const load = createLoader();
const { createOrdersService, parseOrder } = load('src/services/orders.ts');
const { MAX_ORDER_QUANTITY, validOrderQuantity } = load('src/config/orders.ts');
const { inspectEvidence } = load('src/services/releaseEvidence.ts');
const { mockReleaseV2Pass } = load('src/mocks/release.ts');
const row = { id: 1, customer_name: 'EXPLICIT FIXTURE', product_name: 'No real order', quantity: 1, status: 'pending', created_at: '2026-10-21T00:00:00Z' };

test('[contract / HTTP double] quantity boundaries accepted; invalid values rejected before POST', async () => {
  let calls = 0;
  const api = createOrdersService({ baseUrl: () => '/api', fetch: async (_url, options) => {
    calls++;
    return new Response(JSON.stringify({ ...row, ...JSON.parse(options.body) }), { status: 201, headers: { 'Content-Type': 'application/json' } });
  } });
  for (const quantity of [1, MAX_ORDER_QUANTITY]) {
    assert.equal(validOrderQuantity(quantity), true);
    assert.equal((await api.createOrder({ ...row, quantity })).quantity, quantity);
  }
  for (const quantity of [0, -1, 1.5, 2147483648, Number.MAX_SAFE_INTEGER, NaN, Infinity, true, '2', null]) {
    assert.equal(validOrderQuantity(quantity), false);
    await assert.rejects(api.createOrder({ ...row, quantity }), { status: 400 });
  }
  assert.equal(calls, 2);
});

test('[response contract] int32 boundaries parse; overflow is never accepted as an order', () => {
  for (const quantity of [1, MAX_ORDER_QUANTITY]) assert.equal(parseOrder({ ...row, quantity }).quantity, quantity);
  for (const quantity of [2147483648, Number.MAX_SAFE_INTEGER]) assert.throws(() => parseOrder({ ...row, quantity }), { kind: 'contract' });
});

test('[component contract / hook double] create form enforces the same quantity range', async () => {
  for (const quantity of ['1', '2147483647', '2147483648', '0', '1.5', '']) {
    const inputStates = [' Fixture customer ', ' Fixture product ', quantity];
    const updates = [];
    let stateIndex = 0;
    const formLoad = createLoader({}, { react: { ...React, useState(initial) {
      const index = stateIndex++;
      return [index < 3 ? inputStates[index] : initial, value => { updates[index] = value; }];
    } } });
    const Form = formLoad('src/components/orders/CreateOrderForm.tsx').default;
    const submitted = [];
    const form = Form({ onSubmit: async value => { submitted.push(value); } });
    const findQuantity = node => {
      if (!node || typeof node !== 'object') return undefined;
      if (node.props?.id === 'quantity') return node;
      for (const child of React.Children.toArray(node.props?.children)) {
        const found = findQuantity(child); if (found) return found;
      }
    };
    const input = findQuantity(form);
    assert.equal(input.props.min, 1); assert.equal(input.props.max, MAX_ORDER_QUANTITY);
    await form.props.onSubmit({ preventDefault() {} });
    if (quantity === '1' || quantity === '2147483647') {
      assert.deepEqual(submitted, [{ customer_name: 'Fixture customer', product_name: 'Fixture product', quantity: Number(quantity) }]);
    } else {
      assert.equal(submitted.length, 0);
      assert.match(updates[5], /between 1 and 2147483647/);
    }
  }
});

test('[explicit fixture] pre-deploy NOT_RUN preserves reported production status without deployment approval', () => {
  const payload = structuredClone(mockReleaseV2Pass);
  const context = { source: 'SYNTHETIC frontend fixture; no producer execution', fixture: true };
  const valid = inspectEvidence(payload, context);
  assert.equal(valid.state, 'ready'); assert.equal(valid.authenticity, 'FIXTURE');
  payload.deployment = { READINESS_STATUS: 'NOT_RUN', API_STATUS: 'NOT_RUN', DEPLOYMENT_GATE: 'NOT_RUN', ROLLBACK_STATUS: 'NOT_REQUIRED' };
  for (const production of ['PASS', 'BLOCKED']) {
    payload.PRODUCTION_GATE = production;
    const result = inspectEvidence(payload, context);
    assert.equal(result.state, 'ready');
    assert.equal(result.data.PRODUCTION_GATE, production);
    assert.equal(result.data.deployment.DEPLOYMENT_GATE, 'NOT_RUN');
    assert.equal(result.authenticity, 'FIXTURE');
  }
});

test('[explicit fixture] failed/unknown controls and wrong digest cannot supply Production PASS', () => {
  const context = { source: 'SYNTHETIC negative fixture', fixture: true };
  for (const status of ['FAIL', 'ERROR', 'NOT_RUN', 'UNKNOWN', 'INFRA_BLOCKED']) {
    const payload = structuredClone(mockReleaseV2Pass); payload.controls.GITLEAKS_STATUS = status;
    const result = inspectEvidence(payload, context);
    assert.equal(result.state, 'invalid'); assert.equal(result.data, undefined);
  }
  const payload = structuredClone(mockReleaseV2Pass); payload.registry.image_digest = 'sha256:' + 'b'.repeat(64);
  const result = inspectEvidence(payload, context);
  assert.equal(result.state, 'invalid'); assert.equal(result.data, undefined);
});
