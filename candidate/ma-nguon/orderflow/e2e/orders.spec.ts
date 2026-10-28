import { test, expect, type Page, type TestInfo } from "@playwright/test";
import path from "node:path";

const runId = path.basename(process.env.D1_RUN_DIR!);
const traffic = new Map<Page, { responses: unknown[]; failures: unknown[]; pageErrors: string[] }>();

async function attach(testInfo: TestInfo, name: string, value: unknown) {
  await testInfo.attach(name, { body: JSON.stringify(value, null, 2), contentType: "application/json" });
}
async function fillOrder(page: Page, customer: string, product: string, quantity = "2") {
  await page.getByLabel("Customer name").fill(customer);
  await page.getByLabel("Product name").fill(product);
  await page.getByLabel("Quantity").fill(quantity);
}
async function submit(page: Page) {
  await page.locator("form").getByRole("button", { name: "Create Order", exact: true }).click();
}
async function detail(page: Page, order: { id: number; customer_name: string; product_name: string }) {
  await expect(page.getByRole("heading", { name: "Order #" + order.id, exact: true })).toBeVisible();
  await expect(page.getByText(order.customer_name, { exact: true })).toBeVisible();
  await expect(page.getByText(order.product_name, { exact: true })).toBeVisible();
  await expect(page.getByText("Order fields validated by frontend", { exact: true })).toBeVisible();
}

test.beforeEach(async ({ page, browser }, testInfo) => {
  const seen = { responses: [] as unknown[], failures: [] as unknown[], pageErrors: [] as string[] };
  traffic.set(page, seen);
  page.on("response", response => {
    if (new URL(response.url()).pathname.startsWith("/api/")) {
      seen.responses.push({ method: response.request().method(), url: response.url(), status: response.status() });
    }
  });
  page.on("requestfailed", request => {
    if (new URL(request.url()).pathname.startsWith("/api/")) {
      seen.failures.push({ method: request.method(), url: request.url(), error: request.failure()?.errorText });
    }
  });
  page.on("pageerror", error => seen.pageErrors.push(error.message));
  await attach(testInfo, "execution-context", {
    run_id: runId, browser: browser.version(), channel: "msedge", worker: testInfo.workerIndex,
    retries: testInfo.retry, synthetic_data_only: true,
  });
});
test.afterEach(async ({ page }, testInfo) => {
  const seen = traffic.get(page)!;
  await attach(testInfo, "browser-http-observations", seen);
  expect(seen.pageErrors, "No uncaught frontend JavaScript errors").toEqual([]);
  traffic.delete(page);
});

test("REAL happy path: UI create, list, detail, reload and fresh-context persistence", async ({ page, browser }, testInfo) => {
  // Intentionally no routing/interception/mocks in this test.
  testInfo.annotations.push({ type: "evidence-layer", description: "REAL browser -> Vite /api -> Flask -> PostgreSQL" });
  const customer = runId + "-browser";
  const product = "D1 real browser product";
  let posts = 0;
  page.on("request", request => {
    if (new URL(request.url()).pathname === "/api/orders" && request.method() === "POST") posts++;
  });
  await page.goto("/orders");
  await expect(page.getByRole("status").filter({ hasText: "[LIVE MODE SELECTED]" })).toContainText("responding");
  await page.getByRole("button", { name: "Create Order", exact: true }).click();
  await fillOrder(page, customer, product);
  const responsePromise = page.waitForResponse(response =>
    new URL(response.url()).pathname === "/api/orders" && response.request().method() === "POST");
  await submit(page);
  const response = await responsePromise;
  expect(response.status()).toBe(201);
  const order = await response.json();
  expect(order).toMatchObject({ customer_name: customer, product_name: product, quantity: 2, status: "pending" });
  expect(order.id).toBeGreaterThan(0);
  expect(order.created_at).toMatch(/Z$/);
  await expect(page.getByRole("heading", { name: "Order Created Successfully" })).toBeVisible();
  await page.getByRole("button", { name: "Go to Orders", exact: true }).click();
  const row = page.getByRole("row").filter({ hasText: customer });
  await expect(row).toContainText(product);
  await row.click();
  await detail(page, order);
  await page.reload();
  await detail(page, order);
  const persisted = await page.request.get("/api/orders");
  expect(persisted.status()).toBe(200);
  expect((await persisted.json()).orders).toContainEqual(order);
  const fresh = await browser.newContext({ baseURL: "http://127.0.0.1:5173" });
  try {
    const freshPage = await fresh.newPage();
    const read = freshPage.waitForResponse(res => new URL(res.url()).pathname === "/api/orders" && res.status() === 200);
    await freshPage.goto("/orders/" + order.id);
    await read;
    await detail(freshPage, order);
    await freshPage.screenshot({ path: testInfo.outputPath("fresh-context-real-order.png"), fullPage: true });
  } finally {
    await fresh.close();
  }
  expect(posts).toBe(1);
  await attach(testInfo, "real-persisted-order", { order, post_count: posts, interception: false });
});

test("MOCK fixture: Empty create -> list -> detail stays in memory and does not write DB", async ({ page }, testInfo) => {
  testInfo.annotations.push({ type: "evidence-layer", description: "MOCK lifecycle only; not live persistence" });
  const customer = runId + "-mock-only";
  const before = await (await page.request.get("/api/orders")).json();
  let posts = 0;
  page.on("request", request => { if (request.method() === "POST" && request.url().endsWith("/api/orders")) posts++; });
  await page.goto("/orders");
  await page.getByRole("button", { name: "Mock Empty", exact: true }).click();
  await expect(page.getByRole("heading", { name: "No orders yet" })).toBeVisible();
  await page.getByRole("button", { name: "Create Order", exact: true }).first().click();
  await fillOrder(page, customer, "D1 memory-only item");
  await submit(page);
  await expect(page.getByRole("heading", { name: "Order Created Successfully" })).toBeVisible();
  await expect(page.getByText(/added to the in-memory mock store/)).toBeVisible();
  await page.getByRole("button", { name: "Go to Orders", exact: true }).click();
  const row = page.getByRole("row").filter({ hasText: customer });
  await expect(row).toBeVisible();
  await row.click();
  await expect(page.getByText(customer, { exact: true })).toBeVisible();
  await expect(page.getByRole("status").filter({ hasText: "[MOCK FIXTURE MODE]" })).toContainText("not saved to PostgreSQL");
  const after = await (await page.request.get("/api/orders")).json();
  expect(after).toEqual(before);
  expect(posts).toBe(0);
  await attach(testInfo, "mock-isolation", { rows_before: before.orders.length, rows_after: after.orders.length, posts });
});

test("SIMULATED delayed Live response cannot replace Mock Empty state; switching back reads real API", async ({ page }, testInfo) => {
  testInfo.annotations.push({ type: "fault-injection", description: "Playwright delays actual GET response; simulated latency, not backend outage" });
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  let heldResponses = 0;
  let abortedFulfillments = 0;
  await page.route("**/api/orders", async route => {
    try {
      const response = await route.fetch();
      heldResponses++;
      await gate;
      await route.fulfill({ response });
    } catch {
      // Mode switching legitimately cancels the original browser request.
      abortedFulfillments++;
    }
  });
  try {
    await page.goto("/orders");
    await expect.poll(() => heldResponses).toBeGreaterThan(0);
    await page.getByRole("button", { name: "Mock Empty", exact: true }).click();
    await expect(page.getByRole("heading", { name: "No orders yet" })).toBeVisible();
    release();
    await page.unrouteAll({ behavior: "wait" });
    await expect(page.getByRole("status").filter({ hasText: "[MOCK FIXTURE MODE]" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "No orders yet" })).toBeVisible();
    await expect(page.getByRole("row").filter({ hasText: runId })).toHaveCount(0);
    await page.getByRole("button", { name: "Live API", exact: true }).click();
    await expect(page.getByRole("row").filter({ hasText: runId + "-api" })).toBeVisible();
    await expect(page.getByRole("status").filter({ hasText: "[LIVE MODE SELECTED]" })).toContainText("responding");
  } finally {
    release();
    await page.unrouteAll({ behavior: "ignoreErrors" });
  }
  await attach(testInfo, "simulated-race", { heldResponses, abortedFulfillments });
});

test("SIMULATED backend unavailable shows error without silent Mock fallback", async ({ page }, testInfo) => {
  testInfo.annotations.push({ type: "fault-injection", description: "Playwright connectionrefused; real backend stays running" });
  await page.route("**/api/**", route => route.abort("connectionrefused"));
  await page.goto("/orders");
  await expect(page.getByRole("heading", { name: "Unable to load orders" })).toBeVisible();
  await expect(page.getByRole("status").filter({ hasText: "[LIVE MODE SELECTED]" })).toContainText("unavailable");
  await expect(page.getByRole("status").filter({ hasText: "[MOCK FIXTURE MODE]" })).toHaveCount(0);
  await expect(page.getByRole("table")).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Order Created Successfully" })).toHaveCount(0);
});

test("SIMULATED stalled GET hits real frontend 10-second timeout without success", async ({ page }, testInfo) => {
  testInfo.annotations.push({ type: "fault-injection", description: "Playwright holds GET; real adapter timeout, not real server outage" });
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  let requests = 0;
  await page.route("**/api/orders", async route => {
    requests++;
    await gate;
    await route.abort("timedout").catch(() => {});
  });
  const started = Date.now();
  try {
    await page.goto("/orders");
    await expect(page.getByRole("heading", { name: "Unable to load orders" })).toBeVisible({ timeout: 16_000 });
    await expect(page.getByText("API request timed out.", { exact: true })).toBeVisible();
    expect(Date.now() - started).toBeGreaterThanOrEqual(9_000);
    await expect(page.getByRole("table")).toHaveCount(0);
    await expect(page.getByRole("status").filter({ hasText: "[LIVE MODE SELECTED]" })).toContainText("unavailable");
  } finally {
    release();
    await page.unrouteAll({ behavior: "wait" });
  }
  await attach(testInfo, "simulated-timeout", { elapsed_ms: Date.now() - started, requests });
});

test("SIMULATED lost POST response after real commit: uncertain result, no retry, exactly one stored row", async ({ page }, testInfo) => {
  testInfo.annotations.push({ type: "fault-injection", description: "Actual POST reaches Flask/DB; Playwright drops its response after 201" });
  const customer = runId + "-uncertain-post";
  let posts = 0;
  let serverStatus: number | undefined;
  await page.goto("/orders/new");
  await page.route("**/api/orders", async route => {
    if (route.request().method() !== "POST") return route.continue();
    posts++;
    const actualResponse = await route.fetch();
    serverStatus = actualResponse.status();
    await route.abort("connectionreset");
  });
  await fillOrder(page, customer, "D1 response loss item");
  await submit(page);
  await expect(page.getByText(/Creation was not confirmed\. Refresh orders before retrying/)).toBeVisible();
  await expect(page.getByRole("heading", { name: "Order Created Successfully" })).toHaveCount(0);
  await page.waitForTimeout(1_500); // Observe absence of an automatic retry after failure.
  expect(posts).toBe(1);
  expect(serverStatus).toBe(201);
  const res = await page.request.get("/api/orders");
  expect(res.status()).toBe(200);
  const matches = (await res.json()).orders.filter((order: { customer_name: string }) => order.customer_name === customer);
  expect(matches).toHaveLength(1);
  await attach(testInfo, "uncertain-post-actual-write", { posts, serverStatus, stored_order: matches[0], observation_ms: 1500 });
});

test("UI invalid input blocks submission without success or API write", async ({ page }, testInfo) => {
  let posts = 0;
  page.on("request", request => { if (request.method() === "POST" && request.url().endsWith("/api/orders")) posts++; });
  const before = await (await page.request.get("/api/orders")).json();
  await page.goto("/orders/new");
  await fillOrder(page, "   ", "D1 invalid form", "0");
  await submit(page);
  await expect(page.getByRole("alert").filter({ hasText: "Customer name is required." })).toBeVisible();
  await expect(page.getByRole("alert").filter({ hasText: "Quantity must be a positive integer." })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Order Created Successfully" })).toHaveCount(0);
  expect(posts).toBe(0);
  expect(await (await page.request.get("/api/orders")).json()).toEqual(before);
  await attach(testInfo, "invalid-form-no-write", { posts, rows_before: before.orders.length });
});
