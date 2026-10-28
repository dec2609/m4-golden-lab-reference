import { defineConfig } from "@playwright/test";
import production from "./playwright.production.config";
export default defineConfig({
  ...production,
  testMatch: ["d2.orders.spec.ts", "consumer.spec.ts", "readiness.spec.ts"],
});
