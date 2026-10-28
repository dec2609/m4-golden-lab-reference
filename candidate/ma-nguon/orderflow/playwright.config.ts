import { defineConfig } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const frontend = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(frontend, "../..");
if (!process.env.D1_RUN_DIR) throw new Error("D1_RUN_DIR must identify a new controlled D1 evidence run.");
const run = path.resolve(process.env.D1_RUN_DIR);
if (path.dirname(run) !== path.join(root, "bang-chung/m4/orderflow/e2e")) {
  throw new Error("Evidence output must stay inside bang-chung/m4/orderflow/e2e/<run-id>.");
}
const stageA = JSON.parse(fs.readFileSync(path.join(run, "api-results.json"), "utf8"));
if (stageA.status !== "PASS") throw new Error("Browser D1-B requires a real D1-A PASS first.");
if (fs.existsSync(path.join(run, "browser-results.json"))) {
  throw new Error("Browser results already exist. Preserve evidence; initialize a new run before repeating.");
}

export default defineConfig({
  testDir: "./e2e",
  testMatch: "orders.spec.ts",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  forbidOnly: true,
  timeout: 35_000,
  expect: { timeout: 7_000 },
  outputDir: path.join(run, "browser-artifacts"),
  reporter: [
    ["line"],
    ["json", { outputFile: path.join(run, "browser-results.json") }],
  ],
  use: {
    baseURL: "http://127.0.0.1:5173",
    browserName: "chromium",
    channel: "msedge",
    headless: true,
    viewport: { width: 1440, height: 1000 },
    serviceWorkers: "block",
    trace: "on",
    screenshot: "only-on-failure",
    video: "off",
  },
});
