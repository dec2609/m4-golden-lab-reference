const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { createRequire } = require('node:module');
const ts = require('typescript');

// In-memory compilation of the real TS/TSX modules; no bundle, browser or fs cache.
function createLoader(env = {}, externals = {}) {
  const cache = new Map();
  function load(filename) {
    filename = path.resolve(__dirname, '..', filename);
    if (cache.has(filename)) return cache.get(filename).exports;
    const module = { exports: {} };
    cache.set(filename, module);
    const source = fs.readFileSync(filename, 'utf8').replaceAll('import.meta.env', '__testEnv');
    const { outputText } = ts.transpileModule(source, {
      fileName: filename,
      compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
    });
    const nativeRequire = createRequire(filename);
    const requireModule = (name) => {
      if (Object.prototype.hasOwnProperty.call(externals, name)) return externals[name];
      if (!name.startsWith('.')) return nativeRequire(name);
      const base = path.resolve(path.dirname(filename), name);
      const resolved = [base, base + '.ts', base + '.tsx'].find((candidate) => fs.existsSync(candidate) && fs.statSync(candidate).isFile());
      if (!resolved) throw new Error(`Cannot resolve ${name} from ${filename}`);
      return load(resolved);
    };
    vm.runInThisContext(`(function(require,module,exports,__testEnv){${outputText}\n})`, { filename })(requireModule, module, module.exports, env);
    return module.exports;
  }
  return load;
}
module.exports = { createLoader };
