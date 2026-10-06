// The codebook loads on demand (codebook.js). These hold the three things
// that make that safe: nothing reads it unloaded by accident, a failed load
// is tried again, and no module pulls the 400 kB file back into the bundle
// every page loads.
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { codebookLoaded, codebookTables, loadCodebook } from "./codebook.js";

const SRC = fileURLToPath(new URL("../../", import.meta.url));

test("reading before the load throws instead of answering 'no entry'", () => {
  assert.equal(codebookLoaded(), false);
  assert.throws(() => codebookTables(), /await loadCodebook\(\) first/);
});

test("a failed load is not remembered, and concurrent loads share one import", async () => {
  let calls = 0;
  const failing = () => { calls += 1; return Promise.reject(new Error("chunk did not arrive")); };
  await assert.rejects(loadCodebook(failing), /did not arrive/);
  await assert.rejects(loadCodebook(failing), /did not arrive/);
  assert.equal(calls, 2, "the second call tried again");
  assert.equal(codebookLoaded(), false);

  let imports = 0;
  const real = () => { imports += 1; return import("../../../data/cedar/codebook.json", { with: { type: "json" } }); };
  const [a, b] = await Promise.all([loadCodebook(real), loadCodebook(real)]);
  assert.equal(imports, 1);
  assert.equal(a, b);
  assert.equal(codebookTables(), a);
  assert.ok(Object.isFrozen(a));
  assert.ok(a["funding/funding"].fields.length > 0);
  // Loaded once, the import is never repeated.
  await loadCodebook(() => { throw new Error("not called"); });
});

function sources(dir) {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return sources(path);
    return /\.(js|jsx)$/.test(entry.name) && !/\.test\.js$/.test(entry.name) ? [path] : [];
  });
}

test("no production module imports codebook.json statically", () => {
  const offenders = [];
  for (const file of sources(SRC)) {
    const text = readFileSync(file, "utf8");
    // A static `import ... from "...codebook.json"` puts the file into the
    // chunk of every page that reaches this module.
    if (/import\s+[^;()]*?from\s+["'][^"']*codebook\.json["']/.test(text)) offenders.push(file.slice(SRC.length));
  }
  assert.deepEqual(offenders, []);
  const loader = readFileSync(join(SRC, "features/grove/codebook.js"), "utf8");
  assert.match(loader, /import\("\.\.\/\.\.\/\.\.\/data\/cedar\/codebook\.json"/);
});
