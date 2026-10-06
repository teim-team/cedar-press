import assert from "node:assert/strict";
import test from "node:test";

import { READING_KEYS, readingKey } from "./readingKeys.js";
import { STOREFRONT_CATALOG } from "./pressCatalog.js";

test("NEED and PLOT carry a reading key; the other collections do not need one", () => {
  assert.deepEqual(Object.keys(READING_KEYS).sort(), ["need", "plot"]);
  const ids = new Set(STOREFRONT_CATALOG.map((entry) => entry.id));
  for (const id of Object.keys(READING_KEYS)) assert.ok(ids.has(id), `${id} is not a storefront collection`);
  assert.equal(readingKey("funding"), null);
});

test("every key term has a plain meaning and states no figure", () => {
  for (const [id, key] of Object.entries(READING_KEYS)) {
    assert.ok(key.intro.length > 40, id);
    assert.ok(key.terms.length >= 5, id);
    const names = key.terms.map((item) => item.term);
    assert.equal(new Set(names).size, names.length, `${id}: a term is listed twice`);
    for (const { term, meaning } of key.terms) {
      assert.ok(term && meaning.length > 20, `${id}: ${term}`);
      // A key explains columns; a count here would go stale against a release.
      assert.doesNotMatch(meaning, /\b\d{2,}(,\d{3})*\s+(rows|records|observations)\b/i, `${id}: ${term}`);
    }
  }
});
