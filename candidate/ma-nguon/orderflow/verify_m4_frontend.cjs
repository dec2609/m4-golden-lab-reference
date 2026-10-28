const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawnSync } = require('node:child_process');

function buildReport(result, provenance) {
  const status = result.status === 0 ? 'PASS' : result.status === null ? 'ERROR' : 'FAIL';
  return [
    '=== ORDERFLOW PHASE B FRONTEND VERIFICATION ===',
    `Generated: ${new Date().toISOString()}`,
    `UNIT_CONTRACT_PRESENTATION_STATUS=${status}`,
    `Exit code: ${result.status ?? 'not available'}`,
    'Executed: real frontend modules in Node, simulated fetch, in-memory mock stores, React server rendering.',
    'Server rendering is a component unit check, not browser E2E.',
    'INTEGRATION_STATUS=NOT_RUN',
    'BROWSER_E2E_STATUS=NOT_RUN',
    'BACKEND_POSTGRESQL_E2E_STATUS=NOT_RUN',
    'SECURITY_TOOLS_REGISTRY_DEPLOYMENT_ROLLBACK_STATUS=NOT_RUN',
    'No Docker, PostgreSQL, registry or runtime availability is inferred by this script.',
    'Producer schema v2, trusted ingestion and rollback restoration evidence: BLOCKED pending owner confirmation.',
    'Fixture PASS values are test inputs, not security verification results.',
    `Provenance: ${JSON.stringify(provenance)}`,
    '', result.stdout ?? '', result.stderr ?? '',
    result.error ? `Execution error: ${result.error.message}` : '',
  ].join('\n');
}

function collectProvenance() {
  const root = path.resolve(__dirname, '../..');
  const git = (...args) => {
    const result = spawnSync('git', args, { cwd: root, encoding: 'utf8' });
    return result.status === 0 ? result.stdout.trim() : 'UNAVAILABLE';
  };
  const hashes = {};
  function walk(dir) {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const file = path.join(dir, entry.name);
      if (entry.isDirectory()) walk(file);
      else hashes[path.relative(__dirname, file).replaceAll('\\', '/')] = crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
    }
  }
  walk(path.join(__dirname, 'src'));
  walk(path.join(__dirname, 'tests'));
  for (const name of ['verify_m4_frontend.cjs', 'package.json', 'package-lock.json', 'tsconfig.app.json', 'tsconfig.node.json', 'vite.config.ts']) {
    hashes[name] = crypto.createHash('sha256').update(fs.readFileSync(path.join(__dirname, name))).digest('hex');
  }
  return { source_commit: git('rev-parse', 'HEAD'), working_tree: git('status', '--porcelain=v1'), node: process.version, command: 'node --test --test-concurrency=1 --test-reporter=tap tests/*.test.cjs', sha256: hashes };
}

if (require.main === module) {
  const args = process.argv.slice(2);
  if (args.some((arg) => arg !== '--write-evidence')) {
    console.error('Usage: node verify_m4_frontend.cjs [--write-evidence]'); process.exit(2);
  }
  const tests = fs.readdirSync(path.join(__dirname, 'tests')).filter((name) => name.endsWith('.test.cjs')).sort().map((name) => `tests/${name}`);
  const result = spawnSync(process.execPath, ['--test', '--test-concurrency=1', '--test-reporter=tap', ...tests], { cwd: __dirname, encoding: 'utf8' });
  const report = buildReport(result, collectProvenance());
  console.log(report);
  // Default test execution writes no evidence. Explicit opt-in only writes M4.
  if (args.includes('--write-evidence')) {
    const dir = path.resolve(__dirname, '../../bang-chung/m4/orderflow');
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(path.join(dir, 'verification.txt'), report + '\n');
  }
  process.exitCode = result.status === 0 ? 0 : 1;
}

module.exports = { buildReport };
