import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { heldSampleFiles } from "./measure-samples.mjs";

test("held sample gate catches orphan and relocated files despite null manifest paths", () => {
  const root = mkdtempSync(join(tmpdir(), "cedar-held-samples-"));
  try {
    mkdirSync(join(root, "data/cedar"), { recursive: true });
    writeFileSync(join(root, "data/cedar/collections.manifest.json"), JSON.stringify({ collections: [
      { id: "need", publication_hold: { message: "held" }, sample: { path: null },
        tables: [{ sample_path: null, sample_withheld_path: "/data/cedar/samples/old/related.csv" }] },
    ] }));
    assert.deepEqual(heldSampleFiles(root), []);
    for (const part of ["need/orphan.csv", "old/related.csv", "deals/allowed.csv"]) {
      const path = join(root, "public/data/cedar/samples", part);
      mkdirSync(join(path, ".."), { recursive: true });
      writeFileSync(path, "id\nSYNTHETIC-ROW\n");
    }
    assert.deepEqual(heldSampleFiles(root), [
      "/data/cedar/samples/need/orphan.csv", "/data/cedar/samples/old/related.csv",
    ]);
  } finally {
    // Only this test's freshly created, literal temporary directory.
    rmSync(root, { recursive: true, force: true });
  }
});
