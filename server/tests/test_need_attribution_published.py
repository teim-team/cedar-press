"""NEED attribution corrections on the files this repository serves: the guards and 1189.

The generator fixes (1072, 1130, 1102, cedar_publication) and their tests are on PR #132
(server/tests/test_need_attribution.py there); this file covers what main serves.

Register entries and enterprise IDs in the guard fixtures are SYNTHETIC, shaped like the
defects the 2026-10-04 NEED linkage audit found; the same vectors run against the
Lumecon-data copy of the module (tests/test_need_attribution.py there). The 1130 and 1189
tests read the real tracked register and committed files, as the repository's own checks.
"""

import contextlib
import csv
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[2]
CODE = ROOT / "code"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(name, mod)
    spec.loader.exec_module(mod)
    return mod


na = _load("need_attribution", CODE / "need_attribution.py")
VILLAGE = "Federally recognized Alaska Native Village"
TRIBE = "Federally recognized tribe"
ANC = "Alaska Native Village Corporation"


def reg_row(uid, name, cls, fr="", state="AK"):
    return {"cedar_uid": uid, "canonical_name": name, "entity_class": cls,
            "federal_register_legal_name": fr, "former_names": "", "state": state}


REGISTER_ROWS = [
    reg_row("CE-00V01-AA", "Arctic Village", VILLAGE, "Arctic Village Council"),
    reg_row("CE-00V02-AA", "Kipnuk", VILLAGE, "Native Village of Kipnuk"),
    reg_row("CE-00V03-AA", "Tunlik", VILLAGE, "Native Village of Tunlik"),
    reg_row("CE-00C01-AA", "Tunlik Native Corporation", ANC),
    reg_row("CE-00C02-AA", "Ukvik Corporation", ANC),
    reg_row("CE-00T01-AA", "Crow Creek", TRIBE, "Crow Creek Sioux Tribe", "SD"),
    reg_row("CE-00T02-AA", "Prairie Band", TRIBE, "Prairie Band Potawatomi Nation", "KS"),
    reg_row("CE-00T03-AA", "Oglala Sioux", TRIBE, "Oglala Sioux Tribe", "SD"),
    reg_row("CE-00C03-AA", "White Mountain Native Corporation", ANC),
    reg_row("CE-00V04-AA", "Angvik", VILLAGE, "Angvik Community Association"),
    reg_row("CE-00V05-AA", "Bobcat", VILLAGE, "Bobcat Village"),
    reg_row("CE-00N01-AA", "The Pacific Isles Foundation, Inc.",
            "Native Hawaiian Organization"),
]
REGISTER = na.Register(REGISTER_ROWS)


def ent(eid, name, owner, **extra):
    row = {"enterprise_id": eid, "enterprise_name": name,
           "enterprise_name_normalized": " ".join(na.tokens(name)),
           "owner_hub_cedar_uid": owner, "cedar_uid": owner,
           "owner_hub_name": REGISTER.by_uid[owner].canonical_name,
           "evidence_class": "owner_research_dataset_resolver_output",
           "hub_resolution_method": "source_supplied_cedar_uid"}
    row.update(extra)
    return row


TABLE = [ent("E-1", "Ukvik Builders LLC", "CE-00C02-AA"),
         ent("E-2", "Ukvik Marine LLC", "CE-00C02-AA"),
         ent("E-3", "Ukvik Technical LLC", "CE-00C02-AA"),
         ent("E-4", "Sealand Logistics LLC", "CE-00C02-AA")]
CONTEXT = na.TableContext(REGISTER, TABLE)

# The same vectors as Lumecon-data tests/test_need_attribution.py.
VECTORS = [
    ("Arctic Catering Inc", "CE-00V01-AA", na.GUARD_GENERIC_TOKEN),
    ("Crow Tribe of Indians", "CE-00T01-AA", na.GUARD_GENERIC_TOKEN),
    ("Prairie Knights Casino", "CE-00T02-AA", na.GUARD_GENERIC_TOKEN),
    ("White Mountain Apache Tribe", "CE-00C03-AA", na.GUARD_GENERIC_TOKEN),
    ("National Education Association", "CE-00V04-AA", na.GUARD_GENERIC_TOKEN),
    ("Angvik Community Association", "CE-00V04-AA", na.GUARD_HUB_IS_ENTERPRISE),
    ("Bobcat Village Council", "CE-00V05-AA", na.GUARD_HUB_IS_ENTERPRISE),
    ("Kipnuk Technology LLC", "CE-00V02-AA", None),
    ("Prairie Band Casino and Resort", "CE-00T02-AA", None),
    ("Crow Creek Sioux Tribe Farm", "CE-00T01-AA", None),
    ("Oglala Lakota College", "CE-00T03-AA", None),
    ("Broadleaf Inc", "CE-00N01-AA", None),
    ("Sealand Holdings LLC", "CE-00V02-AA", None),
    ("Kipnuk Tribal Council", "CE-00V02-AA", na.GUARD_HUB_IS_ENTERPRISE),
    ("Tunlik, Village", "CE-00V03-AA", na.GUARD_HUB_IS_ENTERPRISE),
    ("Tunlik Native Corporation", "CE-00V03-AA", na.GUARD_VILLAGE_ANC),
    ("Sealand Logistics LLC", "CE-00V03-AA", na.GUARD_VILLAGE_ANC),
    ("Ukvik Fire Protection LLC", "CE-00V03-AA", na.GUARD_VILLAGE_ANC),
]


def code(row):
    found = na.guard(row, CONTEXT)
    return found[0] if found else None


class GuardVectors(unittest.TestCase):
    def test_guards_refuse_only_the_documented_defects(self):
        for name, owner, expected in VECTORS:
            with self.subTest(name=name):
                self.assertEqual(code(ent("X", name, owner)), expected)

    def test_audited_and_hand_ruled_links_are_never_second_guessed(self):
        for evidence in sorted(na.PROTECTED_EVIDENCE):
            self.assertIsNone(code(ent("X", "Arctic Catering Inc", "CE-00V01-AA",
                                       evidence_class=evidence)))


class Apply1189(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load("need1189_for_tests", CODE / "1189_need_attribution_rulings.py")

    def _rulings(self, rows):
        base = {"ruled_date": "2026-10-04", "entity_name": "SYNTHETIC",
                "parent_native_entity": "", "parent_entity_class": "",
                "evidence_url": "https://example.test/", "ruled_by": "test",
                "human_category": ""}
        return na.Rulings([{**base, **r} for r in rows])

    def test_rulings_reattribute_and_mask_without_touching_the_row(self):
        rows = [ent("E-9", "Crow Tribe of Indians", "CE-00T01-AA"),
                ent("E-8", "Arctic Catering Inc", "CE-00V01-AA"),
                ent("E-7", "Kipnuk Technology LLC", "CE-00V02-AA")]
        rulings = self._rulings([
            {"ruling_id": "R1", "identifier_type": "NEED_ENTERPRISE", "identifier": "E-9",
             "ruling": "ATTRIBUTE", "parent_entity_id": "CE-00T03-AA"},
            {"ruling_id": "R1-R", "identifier_type": "NEED_ENTERPRISE", "identifier": "E-9",
             "ruling": "REJECT_ATTRIBUTION", "parent_entity_id": "CE-00T01-AA"},
        ])
        seen = self.m.annotate(rows, rulings=rulings, register=REGISTER)
        self.assertEqual(dict(seen), {na.STATUS_CORRECTED: 1, na.STATUS_REFUSED: 1,
                                      na.STATUS_PUBLISHED: 1})
        self.assertEqual((rows[0]["cedar_uid"], rows[0]["owner_hub_name"]),
                         ("CE-00T03-AA", "Oglala Sioux"))
        self.assertEqual((rows[1]["cedar_uid"], rows[1]["owner_hub_name"]), ("", ""))
        self.assertEqual(rows[1]["enterprise_name"], "Arctic Catering Inc")
        self.assertEqual(rows[2]["cedar_uid"], "CE-00V02-AA")
        again = self.m.annotate(rows, rulings=rulings, register=REGISTER)
        self.assertEqual(dict(again), {na.STATUS_PUBLISHED: 3})

    def test_apply_rewrites_only_decided_rows_and_keeps_other_bytes(self):
        header = "enterprise_name,owner_hub_name,owner_class,cedar_uid\n"
        kept = '"Akiak Technology Llc","Akiak",tribal_government,CE-00006-4P\n'
        wrong = '"Arctic Catering, Inc",Arctic Village,tribal_government,CE-0000J-C2\n'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "need.csv"
            path.write_text(header + kept + wrong, encoding="utf-8")
            root, targets = self.m.ROOT, self.m.TARGETS
            self.m.ROOT, self.m.TARGETS = Path(tmp), ("need.csv",)
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(self.m.run("verify"), 1)
                    self.assertEqual(self.m.run("apply"), 0)
                    self.assertEqual(self.m.run("verify"), 0)
            finally:
                self.m.ROOT, self.m.TARGETS = root, targets
            lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        self.assertEqual(lines[:2], [header, kept])
        self.assertEqual(lines[2], '"Arctic Catering, Inc",,,\n')

    def test_the_committed_need_files_carry_the_rulings(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(self.m.run("verify"), 0, out.getvalue())

    def test_a_drifted_vendored_ruling_file_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "rulings.csv"
            copy.write_bytes(self.m.RULINGS.read_bytes() + b"\n")
            original = self.m.RULINGS
            self.m.RULINGS = copy
            try:
                self.assertTrue(self.m.check_rulings_source())
            finally:
                self.m.RULINGS = original
        self.assertEqual(self.m.check_rulings_source(), [])

    def test_no_withheld_name_is_in_the_vendored_rulings(self):
        with self.m.RULINGS.open(encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        hashed = [r for r in rows if r["identifier_type"] == "NEED_ENTERPRISE_KEY_SHA256"]
        self.assertTrue(hashed)
        self.assertTrue(all(r["entity_name"].startswith("[withheld") for r in hashed))


if __name__ == "__main__":
    unittest.main()
