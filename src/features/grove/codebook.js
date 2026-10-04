/**
 * PURPOSE
 * The codebook (`data/cedar/codebook.json`), loaded when a surface needs it
 * rather than with every page.
 *
 * WHY IT IS LOADED, NOT IMPORTED
 * It is 400 kB minified, 35 kB brotli, and it used to be compiled into the
 * shared chunk every page loads before it mounts (400 of that chunk's 556 kB,
 * measured 2026-10-04), although only the record table (labels and
 * meanings), the column plan and the sample check in `collectionCsv` read it. The bundler now emits it as
 * its own chunk, fetched the first time `loadCodebook()` is called.
 *
 * CONTRACT
 * `loadCodebook()` resolves to the frozen `tables` map and is idempotent: one
 * fetch however many callers ask. A failed load is not remembered, so the
 * next call (a Retry, or the next page) tries again.
 *
 * `codebookTables()` is the synchronous read the existing accessors keep
 * (`labelFor`, `meaningFor`, `codebookFor`, `codebookColumns` in explore.js,
 * `collectionCsv` in collection.js). Called before the load has finished it
 * THROWS rather than answering "no codebook entry": that answer would be a
 * plausible wrong one (a heading built from the column name, a sample
 * refused as off-schema), and the surfaces that read it are gated on the load
 * instead -- the two routes in their lazy imports, the door's preview with
 * its sample, the download before it builds the file.
 */

let tables = null;
let pending = null;

const importCodebook = () => import("../../../data/cedar/codebook.json", { with: { type: "json" } });

/**
 * The codebook's tables, loading them on the first call. `load` is the
 * import, injectable so a test can make it fail.
 */
export function loadCodebook(load = importCodebook) {
  if (tables) return Promise.resolve(tables);
  pending ??= load().then(
    (module) => {
      tables = Object.freeze(module.default.tables);
      return tables;
    },
    (error) => {
      // Not cached: the reader's next attempt must be a real one.
      pending = null;
      throw error;
    },
  );
  return pending;
}

/** Whether `codebookTables()` can be read now. */
export function codebookLoaded() {
  return tables !== null;
}

/** The loaded tables. Throws if `loadCodebook()` has not finished. */
export function codebookTables() {
  if (!tables) {
    throw new Error("The codebook was read before it loaded; await loadCodebook() first.");
  }
  return tables;
}
