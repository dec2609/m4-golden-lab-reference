import { test, expect, type Page } from "@playwright/test";
import { mockReleaseV2Pass, mockReleaseV2PreDeploy, mockReleaseV2Blocked } from "../src/mocks/release";

async function load(page: Page, path: string) {
  await page.getByLabel("Evidence JSON path (same origin)").fill(path);
  await page.getByRole("button", { name: "Load evidence JSON" }).click();
}
test("D3 SIMULATED producer: valid stays UNVERIFIED; contradictions/missing/malformed fail closed; recovery", async ({ page }, info) => {
  info.annotations.push({ type: "test-double", description: "Synthetic proposed producer JSON over intercepted HTTP; NOT trusted producer integration" });
  let body = JSON.stringify({ ...mockReleaseV2Pass, authenticity: "VERIFIED" });
  let status = 200;
  await page.route("**/__consumer_fixture__/release.json", route => route.fulfill({ status, contentType: "application/json", body }));
  await page.goto("/release");
  await expect(page.getByText("[FIXTURE — DEMO / MOCK]", { exact: true })).toBeVisible();
  await load(page, "/__consumer_fixture__/release.json");
  await expect(page.getByText("[UNVERIFIED EVIDENCE SOURCE]", { exact: true })).toBeVisible();
  await expect(page.getByText("Payload reports Production Gate PASS.", { exact: true })).toBeVisible();
  await expect(page.getByText(/VERIFIED requires a trusted verifier that is not configured/)).toBeVisible();
  const contradictory = structuredClone(mockReleaseV2Pass);
  contradictory.controls.COSIGN_STATUS = "FAIL";
  body = JSON.stringify(contradictory);
  await load(page, "/__consumer_fixture__/release.json");
  await expect(page.getByRole("heading", { name: "INVALID / INCOMPLETE" })).toBeVisible();
  await expect(page.getByText("Payload reports Production Gate PASS.", { exact: true })).toHaveCount(0);
  body = "null";
  await load(page, "/__consumer_fixture__/release.json");
  await expect(page.getByRole("heading", { name: "NO RELEASE EVIDENCE" })).toBeVisible();
  body = "{broken";
  await load(page, "/__consumer_fixture__/release.json");
  await expect(page.getByRole("heading", { name: "Unable to load release data" })).toBeVisible();
  status = 500; body = "{}";
  await load(page, "/__consumer_fixture__/release.json");
  await expect(page.getByText("Source returned HTTP 500.", { exact: true })).toBeVisible();
  status = 200; body = JSON.stringify(mockReleaseV2Pass);
  await page.getByRole("button", { name: "Retry evidence load" }).click();
  await expect(page.getByText("Payload reports Production Gate PASS.", { exact: true })).toBeVisible();
  await expect(page.getByText("[UNVERIFIED EVIDENCE SOURCE]", { exact: true })).toBeVisible();
});
test("D3 SIMULATED delayed evidence cannot overwrite selected fixture", async ({ page }, info) => {
  info.annotations.push({ type: "test-double", description: "Delayed synthetic producer, no release verification" });
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  let requested = 0;
  await page.route("**/__consumer_fixture__/slow.json", async route => {
    requested++; await gate;
    await route.fulfill({ json: mockReleaseV2Pass }).catch(() => {});
  });
  try {
    await page.goto("/release");
    await load(page, "/__consumer_fixture__/slow.json");
    await expect.poll(() => requested).toBeGreaterThan(0);
    await page.getByRole("button", { name: "2. V1 BLOCKED", exact: true }).click();
    await expect(page.getByText(/Payload reports BLOCKED/)).toBeVisible();
    release();
    await page.unrouteAll({ behavior: "wait" });
    await expect(page.getByText("[FIXTURE — DEMO / MOCK]", { exact: true })).toBeVisible();
    await expect(page.getByText("Payload reports Production Gate PASS.", { exact: true })).toHaveCount(0);
  } finally {
    release();
    await page.unrouteAll({ behavior: "ignoreErrors" });
  }
});
test("REAL M4 missing release source and database readiness through the proxy", async ({ page }, info) => {
  info.annotations.push({ type: "evidence-layer", description: "Real Nginx/Flask missing release source404 and PR14 database-backed /ready200; no intercepted responses" });
  await page.goto("/release");
  await load(page, "/api/release-not-configured");
  await expect(page.getByRole("heading", { name: "Unable to load release data" })).toBeVisible();
  await expect(page.getByText("Source returned HTTP 404.", { exact: true })).toBeVisible();
  await expect(page.getByText("Payload reports Production Gate PASS.", { exact: true })).toHaveCount(0);
  await page.goto("/orders");
  await expect(page.getByRole("status").filter({ hasText: "[LIVE MODE SELECTED]" })).toContainText("responding");
  await expect(page.getByRole("status").filter({ hasText: "[LIVE MODE SELECTED]" })).toContainText("Database readiness: NOT CHECKED.");
  const ready = await page.request.get("/api/ready");
  expect(ready.status()).toBe(200);
  expect(await ready.json()).toEqual({ status: "ready", database: "connected" });
  await page.getByRole("button", { name: "Check readiness", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "[LIVE MODE SELECTED]" })).toContainText("Database readiness: READY.");
  await page.getByRole("button", { name: "Mock Empty", exact: true }).click();
  await expect(page.getByRole("heading", { name: "No orders yet" })).toBeVisible();
  await page.getByRole("button", { name: "Live API", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "[LIVE MODE SELECTED]" })).toContainText("Database readiness: NOT CHECKED.");
});

test("F1 SIMULATED pre-deploy PASS/BLOCKED, NOT_RUN and invalid recovery keep trust labels", async ({ page }, info) => {
  info.annotations.push({ type: "test-double", description: "Explicit pre-deploy fixtures over intercepted HTTP; no scanner, deployment or trust verification" });
  let payload: unknown = { ...mockReleaseV2PreDeploy, authenticity: "VERIFIED" };
  await page.route("**/__consumer_fixture__/predeploy.json", route => route.fulfill({ json: payload }));
  await page.goto("/release");
  for (const fixture of [mockReleaseV2PreDeploy, mockReleaseV2Blocked]) {
    payload = { ...fixture, authenticity: "VERIFIED" };
    await load(page, "/__consumer_fixture__/predeploy.json");
    await expect(page.getByText("[UNVERIFIED EVIDENCE SOURCE]", { exact: true })).toBeVisible();
    await expect(page.getByText("Deployment Gate: NOT_RUN", { exact: true })).toBeVisible();
    await expect(page.getByText(fixture.PRODUCTION_GATE === "PASS" ? "Payload reports Production Gate PASS." : "Payload reports BLOCKED. This display does not perform artifact promotion.", { exact: true })).toBeVisible();
    await expect(page.getByText("Payload reports Deployment Gate FAIL.", { exact: true })).toHaveCount(0);
  }
  payload = { ...mockReleaseV2PreDeploy, deployment: {} };
  await load(page, "/__consumer_fixture__/predeploy.json");
  await expect(page.getByRole("heading", { name: "INVALID / INCOMPLETE" })).toBeVisible();
  await expect(page.getByText("Payload reports Production Gate PASS.", { exact: true })).toHaveCount(0);
  payload = mockReleaseV2PreDeploy;
  await load(page, "/__consumer_fixture__/predeploy.json");
  await expect(page.getByText("Deployment Gate: NOT_RUN", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "4. V2 BLOCKED (CVE/Reg)", exact: true }).click();
  await expect(page.getByText("[FIXTURE — DEMO / MOCK]", { exact: true })).toBeVisible();
  await expect(page.getByText("Deployment Gate: NOT_RUN", { exact: true })).toBeVisible();
});
