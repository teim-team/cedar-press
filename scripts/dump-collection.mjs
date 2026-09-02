// Dump the JavaScript collection module's values as JSON, so the Python
// implementation can be compared against them value for value.
//
//   node scripts/dump-collection.mjs > /tmp/collection.json
//
// WHY THIS EXISTS
// `server/cedar_press/collections.py` and `src/features/grove/collection.js`
// are required to hold the same values, and the Python docstring claimed a
// test enforced it. None did, and the two had drifted. Both now read one
// manifest, which makes a descriptor difference impossible; this dump covers
// the rest -- the derived strings, the figures, the findings, the citations
// and the download bytes -- where the two still have separate code that can
// disagree even reading identical inputs.
//
// Executed by `server/tests/test_collection.py`, which runs in the same CI job
// as the rest of the Python suite and after `npm ci`, so `node` is present.
//
// The output is deliberately flat and sorted: a diff between the two dumps
// should read as "this field, this dataset", not as a whole-file mismatch.

import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

import {
  COLLECTION_FIGURES,
  EXCLUDED_COLLECTIONS,
  LAUNCH_COLLECTION,
  UNMEASURED_FIELDS,
  collectionCedarFacts,
  collectionCitation,
  collectionContextLine,
  collectionCsv,
  collectionFindings,
  collectionSample,
  collectionTables,
  figuresInShelfOrder,
  hasSample,
  samplePath,
} from "../src/features/grove/collection.js";

const PUBLIC = fileURLToPath(new URL("../public", import.meta.url));

// The same fixed date on both sides. `collectionCitation` takes the accessed
// date as an argument precisely so neither implementation reads a clock, which
// is what would make this comparison flap at midnight.
const ACCESSED = "1 January 2026";

const csvs = {};
for (const dataset of LAUNCH_COLLECTION) {
  if (!hasSample(dataset.id)) {
    csvs[dataset.id] = null;
    continue;
  }
  const text = await readFile(`${PUBLIC}${samplePath(dataset.id)}`, "utf8");
  csvs[dataset.id] = collectionCsv(dataset.id, text);
}

const findings = collectionFindings();

process.stdout.write(
  JSON.stringify(
    {
      launchCollection: LAUNCH_COLLECTION,
      unmeasuredFields: UNMEASURED_FIELDS,
      excluded: EXCLUDED_COLLECTIONS,
      contextLine: collectionContextLine(),
      figures: COLLECTION_FIGURES,
      figureOrder: figuresInShelfOrder().map((figure) => figure.id),
      findings: {
        // `requires` is a list of `{label}` objects here and a list of strings
        // in Python: the JavaScript shape is what FindingsPanel renders and
        // the Python one is what a dataclass can hold. Flattened to the label
        // so the comparison is of the content rather than of two renderers'
        // conveniences -- the one place the two shapes legitimately differ,
        // named here rather than silently skipped.
        supported: findings.supported,
        needs: findings.needs,
        narratives: findings.narratives.map((lead) => ({
          ...lead,
          requires: lead.requires.map((item) => item.label),
        })),
      },
      citations: Object.fromEntries(
        LAUNCH_COLLECTION.map((d) => [d.id, collectionCitation(d.id, ACCESSED)]),
      ),
      citationsWithoutDate: Object.fromEntries(
        LAUNCH_COLLECTION.map((d) => [d.id, collectionCitation(d.id)]),
      ),
      unknownIdCitation: collectionCitation("not-a-collection"),
      cedarFacts: Object.fromEntries(
        LAUNCH_COLLECTION.map((d) => [d.id, collectionCedarFacts(d.id)]),
      ),
      samples: Object.fromEntries(LAUNCH_COLLECTION.map((d) => [d.id, collectionSample(d.id)])),
      tables: Object.fromEntries(LAUNCH_COLLECTION.map((d) => [d.id, collectionTables(d.id)])),
      csvs,
    },
    null,
    2,
  ),
);
