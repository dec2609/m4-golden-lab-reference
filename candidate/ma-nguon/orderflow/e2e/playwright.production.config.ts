import { defineConfig } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../../../", import.meta.url));
if (!process.env.D2_RUN_DIR) throw new Error("D2_RUN_DIR must identify this controlled production test run.");
const run = path.resolve(process.env.D2_RUN_DIR);
if (path.dirname(run) !== path.resolve(root, "bang-chung/m4/orderflow/d2")) throw new Error("Invalid D2 evidence path.");
const proxy = JSON.parse(fs.readFileSync(path.join(run, "proxy-results.json"), "utf8"));
if (proxy.status !== "PASS") throw new Error("Real production proxy tests must PASS before browser execution.");
if (fs.existsSync(path.join(run, "browser-results.json"))) throw new Error("Preserve existing browser evidence; use a new run.");

export default defineConfig({
  testDir: ".",
  testMatch: "d2.orders.spec.ts",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  forbidOnly: true,
  timeout: 45_000,
  expect: { timeout: 8_000 },
  outputDir: path.join(run, "browser-artifacts"),
  reporter: [["line"], ["json", { outputFile: path.join(run, "browser-results.json") }]],
  use: {
    baseURL: "http://127.0.0.1:5180",
    channel: "msedge",
    browserName: "chromium",
    headless: true,
    viewport: { width: 1440, height: 1000 },
    serviceWorkers: "block",
    trace: "on",
    screenshot: "only-on-failure",
    video: "off",
  },
});
