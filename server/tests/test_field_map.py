"""The approved field list, applied to the sample files.

``code/cedar_publication.apply_field_map`` generates the customer header from
``data/cedar/field_map.json`` (docs/PUBLIC_DATASET_SPEC_2026-09-05.md, the
addendum's exact column lists and the identifier retirement rule). The full
tables are not in this repository, so the ten-row samples the site serves
are the fixtures: the same header the writer sees, ten rows deep. What is
asserted is the applier's contract, not the data:

- the opening block leads every mapped dataset, filled from the register;
  Legislation and NAGPRA carry the plural aligned JSON arrays, one position
  per entity-role association, and never several ids in one singular cell;
- the header is the map's exact ``order`` minus what is still owed, with
  ``research_note`` last and anything the build synthesised appended;
- a column the map marks internal, document, combine or derive is gone from
  the header and from every row; a rename is applied to both;
- the named rules build what they promise (geography status, source system,
  the URLs, the activity id, the additional sources);
- the retirement rule is enforced: an alias of cedar_uid is verified row by
  row, an identifier awaiting adjudication stops the dataset, and a retired
  scheme's name in a shipped value or a prohibited column name stops it;
- a flagship column with no decision stops the build, by name;
- an unmapped collection is left exactly as it was.
"""

from __future__ import annotations

import csv
import importlib.util
import json
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

#: Datasets whose samples the applier must REFUSE as they stand, with the
#: column that stops them. These are findings, not fixture defects: the
#: writer will refuse the full table for the same reason until the terminal
#: resolves it, and that is the point of the retirement rule.
REFUSED_AS_SAMPLED = {
    "funding": (("attribution_status",), pub.RetiredIdentifierPresent),   # value `cedar_neid`
    "nest": (("enterprise_existing_cedar_uid",), pub.UnadjudicatedIdentifier),
    # entity_id and cedar_spine_entity_id both disagree with cedar_uid on the
    # Menominee row: neither is an alias, and neither is deleted unadjudicated.
    "nonprofits": (("entity_id", "cedar_spine_entity_id"), pub.UnadjudicatedIdentifier),
    # Notes and the beneficiary note carry caveats that must reach
    # research_note before they leave (Codex, PR #67).
    "deals": (("Notes",), pub.OwedDerivation),
    "natural-resources": (("beneficiary_note",), pub.OwedDerivation),
}


def has_sample(collection: str, table: str) -> bool:
    return (SAMPLES / collection / f"{table}__10.csv").exists()


def sample(collection: str, table: str):
    path = SAMPLES / collection / f"{table}__10.csv"
    with path.open(encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        return list(rd.fieldnames), list(rd)


def neutralised(collection: str, header, rows):
    """The sample with the one finding that stops it resolved, so the rest of
    the contract can be asserted on that dataset too."""
    cols, _ = REFUSED_AS_SAMPLED[collection]
    for r in rows:
        for col in cols:
            if collection == "funding":
                r[col] = "attributed"        # the recoded vocabulary the terminal owes
            else:
                r[col] = ""                  # adjudicated away, for the test only
    return header, rows


class TestApplyFieldMap(unittest.TestCase):
    def test_every_sampled_flagship_comes_out_as_the_exact_approved_header(self):
        fm = pub.field_map()
        for coll, entry in fm.items():
            if not entry["fields"]:
                continue
            table = entry["key"].split("/")[1]
            if not has_sample(coll, table):
                continue
            with self.subTest(collection=coll):
                header, rows = sample(coll, table)
                if coll in REFUSED_AS_SAMPLED:
                    header, rows = neutralised(coll, header, rows)
                own = set(header)
                result = pub.apply_field_map(coll, header, rows, own)
                self.assertTrue(result["mapped"])
                expected = [c for c in entry["order"] if c not in result["owed"]]
                opening = [c for c in entry["opening"] if c not in result["owed"]]
                self.assertEqual(header[:len(opening)], opening)
                self.assertEqual(header, expected)
                self.assertEqual(header[-1], "research_note")
                # Nothing internal, documented, combined or derived survives.
                targets = {f["to"] for f in entry["fields"] if f["decision"] == "rename"}
                gone = {f["column"] for f in entry["fields"]
                        if f["decision"] in ("internal", "document", "combine", "derive")} - targets
                self.assertFalse(gone & set(header))
                for r in rows:
                    self.assertFalse(gone & set(r), sorted(gone & set(r)))
                    self.assertEqual(set(r), set(header))
                for f in entry["fields"]:
                    if f["decision"] == "rename":
                        if f["column"] not in targets:   # a chain: the name is reused
                            self.assertNotIn(f["column"], header)
                        self.assertIn(f["to"], header)
                # No prohibited name, no retired scheme's name anywhere shipped.
                for c in header:
                    self.assertIsNone(pub.PROHIBITED_PUBLIC_COLUMN.search(c), c)
                    for r in rows:
                        self.assertIsNone(pub.RETIRED_TOKEN.search(r[c] or ""), (c, r[c]))
                # Every retirement entry is reported with its rows.
                self.assertEqual({r["column"] for r in result["retirement"]},
                                 {r["column"] for r in entry["retire"]})

    def test_the_singular_block_is_filled_from_the_register(self):
        reg = pub.register()
        singular = (("contractors", "prime_contracts"), ("subcontracting", "subawards"),
                    ("natural-resources", "resource_revenue"),
                    ("lobbying", "native_entity_lobbying_disclosures"))
        for coll, table in singular:
            header, rows = sample(coll, table)
            if coll in REFUSED_AS_SAMPLED:
                neutralised(coll, header, rows)
            pub.apply_field_map(coll, header, rows, set(header))
            for r in rows:
                known = reg.get(r["cedar_uid"])
                if known:
                    self.assertEqual(r["canonical_name"], known[0], (coll, r["cedar_uid"]))
                    self.assertEqual(r["entity_class"], known[1], (coll, r["cedar_uid"]))
                self.assertNotIn("|", r["cedar_uid"], "never several ids in one singular cell")

    def test_the_role_is_a_constant_or_read_from_the_declared_column(self):
        header, rows = sample("funding", "federal_funding_transactions")
        neutralised("funding", header, rows)
        pub.apply_field_map("funding", header, rows, set(header))
        self.assertTrue(all(r["cedar_entity_role"] == "recipient" for r in rows))
        header, rows = sample("subcontracting", "subawards")
        pub.apply_field_map("subcontracting", header, rows, set(header))
        for r in rows:
            self.assertEqual(r["cedar_entity_role"], r["native_direction"])
            self.assertTrue(r["sub_cedar_uid"] and r["prime_cedar_uid"])
        header, rows = sample("deals", "deals_classified")
        neutralised("deals", header, rows)
        result = pub.apply_field_map("deals", header, rows, set(header))
        # The party's own role stays; the block's role is owed and absent,
        # never an ambiguous constant (Codex, PR #67).
        self.assertIn("cedar_entity_role", result["owed"])
        self.assertNotIn("cedar_entity_role", header)
        self.assertIn("native_party_role", header)
        self.assertTrue(all(r["native_party_role"] for r in rows))
        self.assertNotIn("Notes", header)
        self.assertNotIn("Deal_Category", header)
        self.assertIn("deal_type", pub.field_map()["deals"]["order"])

    def test_the_plural_block_is_aligned_json_with_one_position_per_association(self):
        for coll, table in (("nagpra", "nagpra_notices"), ("legislation", "native_bills")):
            header, rows = sample(coll, table)
            entry = pub.field_map()[coll]
            before = [dict(r) for r in rows]
            pub.apply_field_map(coll, header, rows, set(header))
            self.assertEqual(header[:5], list(pub.OPENING_PLURAL))
            self.assertNotIn("cedar_uid", header)
            reg = pub.register()
            for r0, r in zip(before, rows, strict=True):
                cols = {c: json.loads(r[c]) for c in pub.OPENING_PLURAL}
                n = len(cols["cedar_uids"])
                for c in pub.OPENING_PLURAL:
                    self.assertEqual(len(cols[c]), n, (coll, c))
                # Every association from every role list survives, with its role.
                expected = []
                for uid in (r0[entry["entity_uid"]] or "").split("|"):
                    if uid.strip():
                        expected.append((uid.strip(), entry["primary_role"]))
                for declared in entry.get("entity_roles") or []:
                    for uid in (r0[declared["column"]] or "").split("|"):
                        if uid.strip():
                            expected.append((uid.strip(), declared["role"]))
                got = list(zip(cols["cedar_uids"], cols["entity_roles"], strict=True))
                self.assertEqual(got, expected)
                aligned = zip(cols["cedar_uids"], cols["canonical_names"],
                              cols["entity_classes"], strict=True)
                for uid, name, cls in aligned:
                    if uid in reg:
                        self.assertEqual((name, cls), reg[uid])
                # Names as published are owed from the bridge: null, never a register name.
                self.assertEqual(cols["entity_names_as_published"], [None] * n)
            if coll == "legislation":
                self.assertIn("entity_link_statuses", header)
                for r in rows:
                    statuses = json.loads(r["entity_link_statuses"])
                    self.assertEqual(len(statuses), len(json.loads(r["cedar_uids"])))
                    self.assertTrue(r["source_url"].startswith("https://www.congress.gov/bill/"),
                                    r["source_url"])
            else:
                for r in rows:
                    additional = json.loads(r["additional_institution_names"])
                    self.assertIsInstance(additional, list)
                    self.assertNotIn(r["institution_name"], additional)

    def test_the_named_rules_build_what_they_promise(self):
        header, rows = sample("funding", "federal_funding_transactions")
        neutralised("funding", header, rows)
        pub.apply_field_map("funding", header, rows, set(header))
        for r in rows:
            statuses = ("placed", "placed_ambiguous", "unplaced")
            self.assertIn(r["recipient_geography_status"], statuses)
            self.assertIn(r["performance_geography_status"], statuses)
            self.assertEqual(r["source_system"], "usaspending")
            self.assertTrue(r["source_url"].startswith("https://www.usaspending.gov/award/ASST_"))
            self.assertEqual(r["research_note"], "")
        header, rows = sample("lobbying", "native_entity_lobbying_disclosures")
        pub.apply_field_map("lobbying", header, rows, set(header))
        for r in rows:
            self.assertEqual(r["activity_id"], f"lda:{r['source_record_id']}")
            self.assertEqual(r["activity_type"], "lda_filing")
            self.assertEqual(r["source_system"], "lda")
            self.assertEqual(r["participant_name"], "")
        header, rows = sample("deals", "deals_classified")
        neutralised("deals", header, rows)
        pub.apply_field_map("deals", header, rows, set(header))
        for r in rows:
            extra = json.loads(r["additional_sources"])
            self.assertIsInstance(extra, list)
            for src in extra:
                self.assertEqual(set(src), {"url", "source_type"})
                self.assertTrue(src["url"].startswith("http"))

    def test_an_alias_of_cedar_uid_is_verified_row_by_row(self):
        header, rows = sample("natural-resources", "resource_revenue")
        neutralised("natural-resources", header, rows)
        rows[3]["recipient_entity_id"] = "CE-00000-00"      # disagrees with cedar_uid
        with self.assertRaises(pub.AliasDisagreement) as caught:
            pub.apply_field_map("natural-resources", header, rows, set(header))
        self.assertIn("recipient_entity_id", caught.exception.columns)
        # A populated alias beside a BLANK cedar_uid is unresolved too:
        # retiring it would turn an identity into none (Codex, PR #67).
        header, rows = sample("natural-resources", "resource_revenue")
        neutralised("natural-resources", header, rows)
        rows[4]["cedar_uid"] = ""
        with self.assertRaises(pub.AliasDisagreement):
            pub.apply_field_map("natural-resources", header, rows, set(header))
        # And where every row agrees, the alias is retired and reported.
        header, rows = sample("natural-resources", "resource_revenue")
        neutralised("natural-resources", header, rows)
        result = pub.apply_field_map("natural-resources", header, rows, set(header))
        self.assertNotIn("recipient_entity_id", header)
        line = next(r for r in result["retirement"] if r["column"] == "recipient_entity_id")
        self.assertEqual(line["disposition"], "alias_verified")
        self.assertEqual(line["rows_affected"], 10)

    def test_the_samples_the_retirement_rule_refuses_are_refused_by_name(self):
        for coll, (cols, exc) in REFUSED_AS_SAMPLED.items():
            table = pub.field_map()[coll]["key"].split("/")[1]
            header, rows = sample(coll, table)
            with self.subTest(collection=coll), self.assertRaises(exc) as caught:
                pub.apply_field_map(coll, header, rows, set(header))
            self.assertIn(caught.exception.columns[0], cols)
            self.assertIsInstance(caught.exception, SystemExit)

    def test_a_retired_scheme_in_a_shipped_value_or_name_stops_the_dataset(self):
        header, rows = sample("contractors", "prime_contracts")
        rows[0]["award_base_description"] = "keyed via NEID TRBF-0001"   # ships as `description`
        # (the sample carries 'Oneida' in several cells, which must not match)
        rows[1]["awardee_name"] = "ONEIDA NATION ENTERPRISES"
        with self.assertRaises(pub.RetiredIdentifierPresent) as caught:
            pub.apply_field_map("contractors", header, rows, set(header))
        self.assertIn("description", caught.exception.columns)
        self.assertIsNone(pub.RETIRED_TOKEN.search("Oneida, New York"))
        self.assertIsNotNone(pub.RETIRED_TOKEN.search("cedar_neid"))
        self.assertIsNotNone(pub.RETIRED_TOKEN.search("casino_city_id 4412"))

    def test_a_withdrawn_attribution_clears_the_cedar_block_and_keeps_the_filing(self):
        header, rows = sample("lobbying", "native_entity_lobbying_disclosures")
        rows[2]["attribution_withdrawn"] = "1"
        rows[2]["attribution_withdrawn_reason"] = "client is a county housing authority"
        kept = rows[2]["filing_uuid"]
        pub.apply_field_map("lobbying", header, rows, set(header))
        self.assertEqual(rows[2]["source_record_id"], kept)
        block = (rows[2]["cedar_uid"], rows[2]["canonical_name"], rows[2]["entity_class"])
        self.assertEqual(block, ("", "", ""))
        self.assertEqual(rows[2]["attribution_withdrawn"], "1")
        self.assertTrue(rows[1]["cedar_uid"])

    def test_the_owned_map_is_declared_from_the_builder_and_copies_the_authority_uid(self):
        entry = pub.field_map()["owned"]
        self.assertEqual(entry["columns_today"], 53)
        self.assertIn("builder declaration", entry["header_source"])
        header = [f["column"] for f in entry["fields"]]
        rows = [{c: "" for c in header} for _ in range(2)]
        some_uid = next(iter(pub.register()))
        for r in rows:
            r["certifying_authority_entity_id"] = some_uid
            r["business_name_raw"] = "Example Builders LLC"
            r["programme_name"] = "TERO vendor list"
        result = pub.apply_field_map("owned", header, rows, set(header))
        self.assertEqual(header[:4], list(pub.OPENING_SINGULAR))
        self.assertEqual(header, entry["order"])
        self.assertEqual(rows[0]["cedar_uid"], some_uid)
        self.assertEqual(rows[0]["cedar_entity_role"], "certifying_authority")
        self.assertEqual(rows[0]["business_name"], "Example Builders LLC")
        self.assertIn("certifying_authority_entity_id", header)
        self.assertNotIn("nation_id", header)
        adjudicated = [r["column"] for r in result["retirement"]
                       if r["disposition"] == "adjudicate"]
        self.assertEqual(adjudicated, ["nation_id"])
        # A populated nation_id stops the dataset until it is adjudicated.
        rows2 = [dict(r) for r in rows]
        header2 = [f["column"] for f in entry["fields"]]
        rows2 = [{c: "" for c in header2} for _ in range(1)]
        rows2[0]["nation_id"] = "NATION-17"
        with self.assertRaises(pub.UnadjudicatedIdentifier):
            pub.apply_field_map("owned", header2, rows2, set(header2))

    def test_a_withheld_register_name_never_falls_back_to_a_raw_name(self):
        import cedar_domain
        reg = pub.register()
        withheld_class = cedar_domain.INDIVIDUAL_NATIVE_CLASS
        withheld = [uid for uid, (name, cls) in reg.items() if cls == withheld_class]
        self.assertTrue(withheld, "the register carries the withheld class")
        self.assertTrue(all(reg[uid][0] == "" for uid in withheld))
        header, rows = sample("contractors", "prime_contracts")
        rows[0]["cedar_uid"] = withheld[0]
        rows[0]["canonical_name"] = "A Raw Name That Must Not Ship"
        pub.apply_field_map("contractors", header, rows, set(header))
        self.assertEqual(rows[0]["canonical_name"], "")
        self.assertEqual(rows[0]["entity_class"], cedar_domain.INDIVIDUAL_NATIVE_CLASS)

    def test_an_undecided_flagship_column_stops_the_build_by_name(self):
        header, rows = sample("contractors", "prime_contracts")
        header.append("new_upstream_field")
        for r in rows:
            r["new_upstream_field"] = "x"
        with self.assertRaises(pub.UndecidedColumns) as caught:
            pub.apply_field_map("contractors", header, rows, set(header))
        self.assertIn("new_upstream_field", caught.exception.columns)
        self.assertIsInstance(caught.exception, SystemExit)

    def test_a_joined_column_needs_a_decision_too(self):
        # A count or a join the build synthesised is outside the flagship's
        # header and outside the map: refused by name, never appended
        # (Codex, PR #67).
        header, rows = sample("contractors", "prime_contracts")
        own = set(header)
        header.append("n_prime_contracts_awards")
        for r in rows:
            r["n_prime_contracts_awards"] = "2"
        with self.assertRaises(pub.UndecidedColumns) as caught:
            pub.apply_field_map("contractors", header, rows, own)
        self.assertEqual(caught.exception.columns, ["n_prime_contracts_awards"])

    def test_a_blocking_derivation_holds_the_dataset_until_its_target_is_supplied(self):
        header, rows = sample("deals", "deals_classified")
        with self.assertRaises(pub.OwedDerivation) as caught:
            pub.apply_field_map("deals", header, rows, set(header))
        self.assertEqual(caught.exception.columns, ["Notes"])
        # Once the editorial research_note is on the row, Notes may leave and
        # the supplied note ships as it was written.
        header, rows = sample("deals", "deals_classified")
        header.append("research_note")
        for r in rows:
            r["research_note"] = ("Announced value is the Native party's consideration; "
                                  "the project total is the whole project.")
        pub.apply_field_map("deals", header, rows, set(header) - {"research_note"})
        self.assertNotIn("Notes", header)
        self.assertTrue(all(r["research_note"].startswith("Announced value") for r in rows))

    def test_supplied_names_as_published_are_kept_and_must_align(self):
        header, rows = sample("legislation", "native_bills")
        header.append("entity_names_as_published")
        for r in rows:
            n = len([u for u in r["entity_cedar_uids"].split("|") if u.strip()])
            r["entity_names_as_published"] = json.dumps(["As the bill says"] * n)
        own = set(header) - {"entity_names_as_published"}
        pub.apply_field_map("legislation", header, rows, own)
        for r in rows:
            names = json.loads(r["entity_names_as_published"])
            self.assertEqual(len(names), len(json.loads(r["cedar_uids"])))
            self.assertTrue(all(x == "As the bill says" for x in names))
        header, rows = sample("legislation", "native_bills")
        header.append("entity_names_as_published")
        for r in rows:
            r["entity_names_as_published"] = json.dumps(["one name only"])
        misaligned = [r for r in rows
                      if len([u for u in r["entity_cedar_uids"].split("|") if u.strip()]) != 1]
        if misaligned:
            own = set(header) - {"entity_names_as_published"}
            with self.assertRaises(pub.FieldMapRefusal):
                pub.apply_field_map("legislation", header, rows, own)

    def test_an_unmapped_collection_is_left_alone(self):
        header = ["facility_id", "name", "built_date"]
        rows = [{"facility_id": "1", "name": "x", "built_date": "2026-01-01"}]
        result = pub.apply_field_map("gaming", header, rows, set(header))
        self.assertEqual(result, {"mapped": False})
        self.assertEqual(header, ["facility_id", "name", "built_date"])

    def test_the_map_and_the_codebook_name_the_same_shipped_columns(self):
        codebook = json.loads((ROOT / "data" / "cedar" / "codebook.json").read_text("utf-8"))
        for coll, entry in pub.field_map().items():
            if not entry["fields"] or entry["key"] not in codebook["tables"]:
                continue
            book = codebook["tables"][entry["key"]]
            listed = {f["column"] for f in book["fields"] if not f.get("add")}
            ships = {f["column"] for f in entry["fields"]
                     if f["decision"] in ("keep", "withhold", "rename")}
            self.assertTrue(ships <= listed, (coll, sorted(ships - listed)))


if __name__ == "__main__":
    unittest.main()
