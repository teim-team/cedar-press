"""The approved field list, applied to the sample files.

``code/cedar_publication.apply_field_map`` generates the customer header from
``data/cedar/field_map.json`` (docs/PUBLIC_DATASET_SPEC_2026-09-05.md §17).
The full tables are not in this repository, so the ten-row samples the site
serves are the fixtures: the same header the writer sees, ten rows deep. What
is asserted is the applier's contract, not the data:

- the opening block leads every mapped dataset, filled from the register;
- a column the map marks internal, document, combine or derive is gone from
  the header and from every row; a rename is applied to both;
- the header is the map's ``order`` minus what is still owed, in that order,
  with anything the build synthesised appended behind it;
- a flagship column with no decision stops the build, by name;
- an unmapped collection is left exactly as it was.
"""

from __future__ import annotations

import csv
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CODE = ROOT / "code"
SAMPLES = ROOT / "public" / "data" / "cedar" / "samples"

sys.path.insert(0, str(CODE))


def _load_publication():
    spec = importlib.util.spec_from_file_location(
        "cedar_publication", CODE / "cedar_publication.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pub = _load_publication()


def sample(collection: str, table: str):
    path = SAMPLES / collection / f"{table}__10.csv"
    with path.open(encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        return list(rd.fieldnames), list(rd)


class TestApplyFieldMap(unittest.TestCase):
    def test_every_sampled_flagship_comes_out_as_the_approved_header(self):
        fm = pub.field_map()
        for coll, entry in fm.items():
            if not entry["fields"]:
                continue
            table = entry["key"].split("/")[1]
            with self.subTest(collection=coll):
                header, rows = sample(coll, table)
                own = set(header)
                result = pub.apply_field_map(coll, header, rows, own)
                self.assertTrue(result["mapped"])
                # The opening block leads.
                self.assertEqual(header[:4], list(pub.OPENING_BLOCK))
                # The header is the order minus what is owed, in order.
                expected = [c for c in entry["order"] if c not in result["owed"]]
                self.assertEqual(header, expected)
                # Nothing internal, documented, combined or derived survives,
                # in the header or in any row.
                # (a raw column marked internal whose normalized twin is
                # renamed onto its name - contractors' extent_competed,
                # lobbying's filing_type - survives as the twin, by design)
                targets = {f["to"] for f in entry["fields"] if f["decision"] == "rename"}
                gone = {f["column"] for f in entry["fields"]
                        if f["decision"] in ("internal", "document", "combine", "derive")} - targets
                self.assertFalse(gone & set(header))
                for r in rows:
                    self.assertFalse(gone & set(r), sorted(gone & set(r)))
                    self.assertEqual(set(r), set(header))
                # Every rename landed and nothing retired travels.
                for f in entry["fields"]:
                    if f["decision"] == "rename":
                        self.assertNotIn(f["column"], header)
                        self.assertIn(f["to"], header)
                for c in header:
                    self.assertNotRegex(c.lower(), r"duns|neid|cicd|built_date|fetched_date")
                # The register filled the opening block wherever it knows the uid.
                reg = pub.register()
                for r in rows:
                    for uid, name, kind in zip(r["cedar_uid"].split("|"),
                                               r["cedar_entity_name"].split("|"),
                                               r["cedar_entity_type"].split("|"),
                                               strict=False):
                        known = reg.get(uid.strip())
                        if known:
                            self.assertEqual(name, known[0], (coll, uid))
                            self.assertEqual(kind, known[1], (coll, uid))

    def test_the_role_is_a_constant_or_read_from_the_declared_column(self):
        header, rows = sample("funding", "federal_funding_transactions")
        pub.apply_field_map("funding", header, rows, set(header))
        self.assertTrue(all(r["cedar_entity_role"] == "recipient" for r in rows))
        header, rows = sample("subcontracting", "subawards")
        pub.apply_field_map("subcontracting", header, rows, set(header))
        # Read from native_side (the renamed `direction`), so a row says which
        # side made it Native rather than a constant that cannot.
        for r in rows:
            self.assertEqual(r["cedar_entity_role"], r["native_side"])
            self.assertIn("sub_cedar_uid", r)
            self.assertIn("prime_cedar_uid", r)
        header, rows = sample("deals", "deals_classified")
        pub.apply_field_map("deals", header, rows, set(header))
        # The deal's role column IS the opening role (renamed onto it).
        self.assertTrue(all(r["cedar_entity_role"] for r in rows))
        self.assertNotIn("native_party_role", header)
        self.assertNotIn("Notes", header)
        self.assertNotIn("Deal_Category", header)   # combined: owed, not shipped raw
        self.assertIn("deal_category", pub.field_map()["deals"]["order"])

    def test_a_multi_entity_table_fills_the_block_per_entity(self):
        header, rows = sample("nagpra", "nagpra_notices")
        pub.apply_field_map("nagpra", header, rows, set(header))
        self.assertNotIn("affiliated_entity_ids", header)
        reg = pub.register()
        for r in rows:
            uids = [u for u in r["cedar_uid"].split("|") if u]
            if not uids:
                self.assertEqual(r["cedar_entity_name"], "")
                continue
            self.assertEqual(len(r["cedar_entity_type"].split("|")), len(uids))
            for uid, kind in zip(uids, r["cedar_entity_type"].split("|"), strict=True):
                if uid in reg:
                    self.assertEqual(kind, reg[uid][1])
        # The other roles keep their own lists beside the block.
        for col in ("consulted_entity_ids", "repatriation_recipient_entity_ids",
                    "disposition_priority_entity_ids", "aboriginal_land_entity_ids"):
            self.assertIn(col, header)

    def test_an_undecided_flagship_column_stops_the_build_by_name(self):
        header, rows = sample("funding", "federal_funding_transactions")
        header.append("new_upstream_field")
        for r in rows:
            r["new_upstream_field"] = "x"
        with self.assertRaises(pub.UndecidedColumns) as caught:
            pub.apply_field_map("funding", header, rows, set(header))
        self.assertIn("new_upstream_field", caught.exception.columns)
        self.assertIn("new_upstream_field", str(caught.exception))
        self.assertIsInstance(caught.exception, SystemExit)

    def test_synthesised_columns_are_appended_not_decided(self):
        header, rows = sample("nest", "nest_enterprises")
        own = set(header)
        header.append("n_nest_enterprise_relations")
        for r in rows:
            r["n_nest_enterprise_relations"] = "2"
        result = pub.apply_field_map("nest", header, rows, own)
        self.assertEqual(header[-1], "n_nest_enterprise_relations")
        self.assertEqual(result["synthesised"], ["n_nest_enterprise_relations"])
        self.assertEqual(header[:4], list(pub.OPENING_BLOCK))

    def test_an_unmapped_collection_is_left_alone(self):
        header = ["facility_id", "name", "built_date"]
        rows = [{"facility_id": "1", "name": "x", "built_date": "2026-01-01"}]
        result = pub.apply_field_map("gaming", header, rows, set(header))
        self.assertEqual(result, {"mapped": False})
        self.assertEqual(header, ["facility_id", "name", "built_date"])
        self.assertEqual(rows[0]["built_date"], "2026-01-01")

    def test_the_map_and_the_codebook_name_the_same_shipped_columns(self):
        # The JS suite asserts this from the site's side; this is the
        # pipeline's side of the same promise, so neither can drift alone.
        import json
        codebook = json.loads((ROOT / "data" / "cedar" / "codebook.json").read_text("utf-8"))
        for coll, entry in pub.field_map().items():
            if not entry["fields"]:
                continue
            book = codebook["tables"][entry["key"]]
            listed = {f["column"] for f in book["fields"] if not f.get("add")}
            ships = {f["column"] for f in entry["fields"]
                     if f["decision"] in ("keep", "withhold", "rename")}
            self.assertTrue(ships <= listed, (coll, sorted(ships - listed)))


if __name__ == "__main__":
    unittest.main()
