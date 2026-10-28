import { test, expect, type Page, type TestInfo } from "@playwright/test";
import path from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { fileURLToPath } from "node:url";
const exec = promisify(execFile);
const helper = fileURLToPath(new URL("./d2_environment.py", import.meta.url));

const runId = path.basename(process.env.D2_RUN_DIR!);
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
  testInfo.annotations.push({ type: "evidence-layer", description: "REAL Edge -> production Nginx -> Flask -> PostgreSQL" });
  const customer = runId + "-browser";
  const product = "D2 production browser product";
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
  await row.focus();
  await row.press("Enter");
  await detail(page, order);
  await page.reload();
  await detail(page, order);
  const persisted = await page.request.get("/api/orders");
  expect(persisted.status()).toBe(200);
  expect((await persisted.json()).orders).toContainEqual(order);
  const fresh = await browser.newContext({ baseURL: "http://127.0.0.1:5180" });
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
  await attach(testInfo, "production-persisted-order", order);
  await expect(page.locator('script[src*="/@vite/client"]')).toHaveCount(0);
});


test("REAL invalid UI input: no POST, no success and database unchanged", async ({ page }, testInfo) => {
  const before = await (await page.request.get("/api/orders")).json();
  let posts = 0;
  page.on("request", req => { if (req.method() === "POST" && req.url().endsWith("/api/orders")) posts++; });
  await page.goto("/orders/new");
  await fillOrder(page, "   ", "D2 invalid form", "0");
  await submit(page);
  await expect(page.getByRole("alert").filter({ hasText: "Customer name is required." })).toBeVisible();
  await expect(page.getByRole("alert").filter({ hasText: "Quantity must be a positive integer." })).toBeVisible();
  await expect(page.getByLabel("Customer name")).toHaveAttribute("aria-invalid", "true");
  await expect(page.getByLabel("Customer name")).toHaveAttribute("aria-describedby", "customer-error");
  await expect(page.getByLabel("Quantity")).toHaveAttribute("aria-describedby", "quantity-error");
  await expect(page.getByRole("heading", { name: "Order Created Successfully" })).toHaveCount(0);
  expect(posts).toBe(0);
  expect(await (await page.request.get("/api/orders")).json()).toEqual(before);
  await attach(testInfo, "invalid-no-write", { posts, rows_before: before.orders.length });
});

test("REAL backend stop/recovery: Nginx error preserved, UI error then persistence restored", async ({ page }, testInfo) => {
  test.setTimeout(90_000);
  testInfo.annotations.push({ type: "fault-injection", description: "Actual D2 order-app container stop/start; not routing/interception; D1 untouched" });
  await page.goto("/orders");
  await expect(page.getByRole("row").filter({ hasText: runId + "-api" })).toBeVisible();
  let failureStatus: number | undefined;
  try {
    await exec("python", [helper, "app-stop", "--run-dir", process.env.D2_RUN_DIR!]);
    const res = await page.request.get("/api/orders");
    failureStatus = res.status();
    expect([502, 503, 504]).toContain(failureStatus);
    await page.reload();
    await expect(page.getByRole("heading", { name: "Unable to load orders" })).toBeVisible();
    await expect(page.getByRole("table")).toHaveCount(0);
    await expect(page.getByRole("status").filter({ hasText: "[MOCK FIXTURE MODE]" })).toHaveCount(0);
    // Static SPA still loads when the backend is genuinely down.
    expect((await page.request.get("/orders/1")).status()).toBe(200);
  } finally {
    await exec("python", [helper, "app-start", "--run-dir", process.env.D2_RUN_DIR!]);
  }
  await page.getByRole("button", { name: "Try again", exact: true }).click();
  await expect(page.getByRole("row").filter({ hasText: runId + "-browser" })).toBeVisible();
  await expect(page.getByRole("status").filter({ hasText: "[LIVE MODE SELECTED]" })).toContainText("responding");
  await attach(testInfo, "actual-outage-and-recovery", { failureStatus, recovery_status: (await page.request.get("/api/health")).status(), intercepted: false });
});
