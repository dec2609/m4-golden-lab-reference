const test = require('node:test');
const assert = require('node:assert/strict');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { MemoryRouter } = require('react-router-dom');
const { createLoader } = require('./load-ts.cjs');
let Decision, Identity, Notice, Trace, ordersService, mockReleaseV2Pass;
test.before(async () => {
  // Use the actual package's ESM entry, matching Vite, rather than its CJS entry.
  const icons = await import('lucide-react');
  const load = createLoader({}, { 'lucide-react': icons });
  Decision = load('src/components/release/ReleaseDecision.tsx').default;
  Identity = load('src/components/release/ArtifactIdentity.tsx').default;
  Notice = load('src/components/orders/OrdersSourceNotice.tsx').default;
  Trace = load('src/components/orders/OrderReleaseTrace.tsx').default;
  ({ ordersService } = load('src/services/orders.ts'));
  ({ mockReleaseV2Pass } = load('src/mocks/release.ts'));
});
const render = (component, props = {}) => renderToStaticMarkup(React.createElement(component, props));

test('[unit presentation/SSR] registry equality is explicitly not registry verification', () => {
  const html = render(Identity, { release: mockReleaseV2Pass });
  assert.match(html, /EQUAL IN PAYLOAD/); assert.match(html, /No registry query or authenticity verification/);
  assert.doesNotMatch(html, /Registry verification confirmed|Internal manifest digest/);
});

test('[unit presentation/SSR] rollback PASS remains reported and restoration unverified', () => {
  const html = render(Decision, { status: 'PASS', showDeployment: true, deploymentGate: 'FAIL', rollbackStatus: 'PASS' });
  assert.match(html, /RESTORATION UNVERIFIED/); assert.match(html, /post-restore health require producer evidence/);
  assert.doesNotMatch(html, /ROLLBACK EXECUTED|routine completed successfully|Restored to last known/);
});

test('[unit presentation/SSR] deployment omission and invalid release are unavailable', () => {
  assert.match(render(Decision, { status: 'PASS', showDeployment: true }), /Deployment result: NOT AVAILABLE/);
  const invalid = render(Decision, { status: 'NOT AVAILABLE' });
  assert.match(invalid, /No release approval can be inferred/); assert.doesNotMatch(invalid, /Payload reports Production Gate PASS/);
});

test('[unit presentation/SSR] deployment PASS does not assert active traffic', () => {
  const html = render(Decision, { status: 'PASS', deploymentGate: 'PASS' });
  assert.match(html, /active traffic is not verified here/); assert.doesNotMatch(html, /Release verified for production|Deployment verified &amp; traffic active/);
});

test('[F1 presentation/SSR] pre-deploy has a neutral NOT_RUN state, not a failed deployment', () => {
  for (const status of ['PASS', 'BLOCKED']) {
    const html = render(Decision, { status, showDeployment: true, deploymentGate: 'NOT_RUN', rollbackStatus: 'NOT_REQUIRED' });
    assert.match(html, /Deployment Gate: NOT_RUN/);
    assert.match(html, /Not deployed \/ deployment checks not run/);
    assert.match(html, /No deployment outcome or approval is available/);
    assert.doesNotMatch(html, /Payload reports Deployment Gate (PASS|FAIL)|ROLLBACK REPORTED/);
    assert.match(html, status === 'PASS' ? /Payload reports Production Gate PASS/ : /Payload reports BLOCKED/);
  }
});

test('[F1 presentation/SSR] failed deployment keeps reported rollback PASS and FAIL distinct', () => {
  for (const rollbackStatus of ['PASS', 'FAIL']) {
    const html = render(Decision, { status: 'PASS', showDeployment: true, deploymentGate: 'FAIL', rollbackStatus });
    assert.match(html, /Payload reports Deployment Gate FAIL/);
    assert.match(html, new RegExp('ROLLBACK REPORTED ' + rollbackStatus));
    assert.doesNotMatch(html, /Payload reports Deployment Gate PASS|SYSTEM HEALTH.*RESTORED/);
  }
});

test('[unit presentation/SSR] selected Live mode alone never asserts API or DB connectivity', () => {
  ordersService.setScenario('live'); const html = render(Notice);
  assert.match(html, /LIVE MODE SELECTED/); assert.match(html, /unverified/); assert.match(html, /Database readiness: NOT CHECKED/);
  assert.doesNotMatch(html, /Connected to PostgreSQL|LIVE BACKEND ACTIVE/);
  ordersService.setScenario('empty'); assert.match(render(Notice), /not saved to PostgreSQL/);
});

test('[unit presentation/SSR] order release trace explicitly has no attributed commit', () => {
  const html = renderToStaticMarkup(React.createElement(MemoryRouter, null, React.createElement(Trace)));
  assert.match(html, /No release is attributed to this order/); assert.match(html, /NOT AVAILABLE/);
  assert.doesNotMatch(html, /7c33671e|This order was processed by this release|Gate: PASS/);
});
