import { test, expect, type Page } from "@playwright/test";

const live = (page: Page) => page.getByRole("status").filter({ hasText: "[LIVE MODE SELECTED]" });

test("F2 SIMULATED M4 readiness distinguishes liveness, outage, invalid responses and recovery", async ({ page }, info) => {
  info.annotations.push({ type: "test-double", description: "Orders and readiness HTTP interception; no Flask/PostgreSQL execution or real outage" });
  await page.route("**/api/orders", route => route.fulfill({ json: { orders: [] } }));
  let response = { status: 200, body: JSON.stringify({ status: "ready", database: "connected" }), networkError: false };
  let calls = 0;
  await page.route("**/api/ready", async route => {
    calls++;
    if (response.networkError) await route.abort("failed");
    else await route.fulfill({ status: response.status, contentType: "application/json", body: response.body });
  });
  await page.goto("/orders");
  await expect(live(page)).toContainText("responding");
  await expect(live(page)).toContainText("Database readiness: NOT CHECKED.");
  for (const item of [
    { status: 200, body: JSON.stringify({ status: "ready", database: "connected" }), expected: "READY." },
    { status: 503, body: JSON.stringify({ status: "unready", error: "database unreachable" }), expected: "UNREADY." },
    { status: 404, body: "Route absent", expected: "NOT_IMPLEMENTED." },
    { status: 200, body: "{broken", expected: "ERROR / NOT CONFIRMED." },
    { status: 503, body: JSON.stringify({ status: "unready", database: "connected" }), expected: "ERROR / NOT CONFIRMED." },
    { status: 500, body: JSON.stringify({ error: "Internal server error" }), expected: "ERROR / NOT CONFIRMED." },
    { status: 200, body: "", networkError: true, expected: "ERROR / NOT CONFIRMED." },
    { status: 200, body: JSON.stringify({ status: "ready", database: "connected" }), expected: "READY." },
  ]) {
    response = { status: item.status, body: item.body, networkError: item.networkError ?? false };
    const before = calls;
    await page.getByRole("button", { name: "Check readiness", exact: true }).click();
    await expect.poll(() => calls).toBe(before + 1);
    await expect(live(page)).toContainText("Database readiness: " + item.expected);
    await expect(live(page)).toContainText("API: responding");
  }
});

test("F2 SIMULATED late readiness cannot survive Live to Mock to Live switching", async ({ page }, info) => {
  info.annotations.push({ type: "test-double", description: "Delayed intercepted readiness; tests cancellation/UI scope, not real database recovery" });
  await page.route("**/api/orders", route => route.fulfill({ json: { orders: [] } }));
  let release!: () => void;
  const delayed = new Promise<void>(resolve => { release = resolve; });
  let requested = 0;
  await page.route("**/api/ready", async route => {
    requested++;
    await delayed;
    await route.fulfill({ json: { status: "ready", database: "connected" } }).catch(() => {});
  });
  try {
    await page.goto("/orders");
    await page.getByRole("button", { name: "Check readiness", exact: true }).click();
    await expect.poll(() => requested).toBe(1);
    await expect(live(page)).toContainText("Database readiness: CHECKING.");
    await page.getByRole("button", { name: "Mock Empty", exact: true }).click();
    await expect(page.getByText("[MOCK FIXTURE MODE]", { exact: true })).toBeVisible();
    release();
    await page.unroute("**/api/ready");
    await page.getByRole("button", { name: "Live API", exact: true }).click();
    await expect(live(page)).toContainText("API: responding");
    await expect(live(page)).toContainText("Database readiness: NOT CHECKED.");
    await expect(live(page)).not.toContainText("Database readiness: READY.");
  } finally {
    release();
    await page.unrouteAll({ behavior: "ignoreErrors" });
  }
});
