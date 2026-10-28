const fs = require('fs');
const path = require('path');
const { createJiti } = require('jiti');

// Initialize Jiti runtime loader to import TypeScript implementation and fixtures directly
const jiti = createJiti(__filename);

// 1. Import REAL validation logic from src/services/release.ts (No duplicate logic)
const { validateReleaseStatus } = jiti('./src/services/release.ts');

// 2. Import REAL fixtures from src/mocks/release.ts (No duplicate fixtures)
const {
  mockReleasePass,
  mockReleaseBlocked,
  mockReleaseInvalid,
} = jiti('./src/mocks/release.ts');

let output = [];
output.push("=== ORDERFLOW M3 FRONTEND & INTEGRATION VERIFICATION ===");
output.push(`Generated: ${new Date().toISOString()}`);
output.push("Scope: Workload Presentation, Adapter Boundaries & Release Console v1");
output.push("Disclaimer: Release/order data trong các scenario là UI integration fixtures, không phải technical security evidence.\n");

// Scenario 1 — PASS: mockReleasePass
const resPass = validateReleaseStatus(mockReleasePass);
output.push("--- Scenario 1: Production Gate PASS ---");
output.push(`Valid: ${resPass.isValid}`);
output.push(`Production Gate: ${resPass.data?.PRODUCTION_GATE}`);
output.push(`Controls: ${JSON.stringify(resPass.data?.controls)}`);
const passOk = resPass.isValid && resPass.data?.PRODUCTION_GATE === "PASS";
output.push(passOk ? "Result: PASS\n" : "Result: FAIL\n");

// Scenario 2 — BLOCKED: mockReleaseBlocked
const resBlocked = validateReleaseStatus(mockReleaseBlocked);
output.push("--- Scenario 2: Production Gate BLOCKED ---");
output.push(`Valid: ${resBlocked.isValid}`);
output.push(`Production Gate: ${resBlocked.data?.PRODUCTION_GATE}`);
const failedControl = Object.entries(resBlocked.data?.controls || {}).find(([, v]) => v === "FAIL");
output.push(`Failed Control: ${failedControl ? `${failedControl[0]} = ${failedControl[1]}` : "none"}`);
const blockedOk = resBlocked.isValid && resBlocked.data?.PRODUCTION_GATE === "BLOCKED" && !!failedControl;
output.push(blockedOk ? "Result: PASS\n" : "Result: FAIL\n");

// Scenario 3 — Invalid / Incomplete: mockReleaseInvalid
const resInvalid = validateReleaseStatus(mockReleaseInvalid);
output.push("--- Scenario 3: Invalid / Incomplete Payload ---");
output.push(`Valid: ${resInvalid.isValid}`);
output.push(`Error Reason: ${resInvalid.errorReason}`);
output.push("UI Expected Gate: NOT AVAILABLE (Must never infer BLOCKED or PASS)");
const invalidOk = !resInvalid.isValid && !!resInvalid.errorReason;
output.push(invalidOk ? "Result: PASS (Correctly rejected without gate inference)\n" : "Result: FAIL\n");

// Scenario 4 — Build artifact presence
const distDir = path.join(__dirname, 'dist');
const distHtml = path.join(distDir, 'index.html');
const distExists = fs.existsSync(distHtml);
output.push("--- Scenario 4: Build artifact presence ---");
output.push(`dist/index.html exists: ${distExists}`);
output.push(distExists ? "Result: PASS\n" : "Result: FAIL\n");

const logContent = output.join('\n');
console.log(logContent);

// Save evidence to bang-chung/m3/orderflow/verification.txt
const evidenceDir = path.resolve(__dirname, '../../bang-chung/m3/orderflow');
if (!fs.existsSync(evidenceDir)) {
  fs.mkdirSync(evidenceDir, { recursive: true });
}
fs.writeFileSync(path.join(evidenceDir, 'verification.txt'), logContent);
console.log(`Saved evidence to ${path.join(evidenceDir, 'verification.txt')}`);

if (!passOk || !blockedOk || !invalidOk || !distExists) {
  process.exit(1);
}
