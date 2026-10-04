"""NEED attribution corrections: the guards, 1072's flagging, 1130's crosswalk, 1189, masks.

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


class Builder1072(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load("need1072_for_tests", CODE / "1072_tribally_owned_enterprises.py")

    def test_guard_flags_and_never_drops_or_repoints(self):
        kept = [{"child_name_raw": "Arctic Catering Inc", "hub_cedar_uid": "CE-00V01-AA"},
                {"child_name_raw": "Kipnuk Technology LLC", "hub_cedar_uid": "CE-00V02-AA"}]
        refused = self.m.flag_attribution(kept, REGISTER_ROWS)
        self.assertEqual(dict(refused), {na.GUARD_GENERIC_TOKEN: 1})
        self.assertEqual(len(kept), 2)
        self.assertEqual(kept[0]["attribution_refusal"], na.GUARD_GENERIC_TOKEN)
        self.assertEqual(kept[0]["hub_cedar_uid"], "CE-00V01-AA")
        self.assertEqual(kept[1]["attribution_refusal"], "")

    def test_human_review_is_counted_never_defaulted(self):
        self.assertEqual(self.m._edge()["source_review_status"], "not_recorded")
        es = [{"source_review_status": "reviewed"}, {},
              {"source_review_status": "auto_ruled_not_human_reviewed"},
              {"source_review_status": "not_recorded"}]
        self.assertEqual(self.m.review_summary(es), ("Y", 1))
        self.assertEqual(self.m.review_summary(es[1:]), ("N", 0))


class Crosswalk1130(unittest.TestCase):
    """The four owner hand rulings the audit found under a same-word sibling tribe."""

    @classmethod
    def setUpClass(cls):
        cls.m = _load("need1130_for_tests", CODE / "1130_need_owner_v6_reconcile.py")
        cls.reg = cls.m.rd(str(ROOT / "data/spine/cedar_identity_register.csv"))

    def test_rule_7_residue_picks_the_tribe_the_name_names(self):
        for canon, want in [("Flandreau Santee Sioux Tribe", "CE-0014E-C7"),
                            ("Confederated Salish and Kootenai Tribes", "CE-0013X-1E"),
                            ("Mashpee Wampanoag Tribe", "CE-0017D-NY"),
                            ("Crow Tribe of Indians", "CE-0013W-VN"),
                            ("Santee Sioux Nation", "CE-0019J-XV")]:
            with self.subTest(canon=canon):
                uid, method, _ = self.m.resolve_parent("TRBF-NOTLIVE-00", canon, {}, {},
                                                       self.reg)
                self.assertEqual((uid, method), (want, "name_tokens_class_gated_unique"))

    def test_a_handle_the_row_name_contradicts_is_not_taken(self):
        k = next(r for r in self.reg if r["cedar_uid"] == "CE-0015Z-Q0")
        by_handle = {"TRBF-KTNIID-00": dict(k, handle="TRBF-KTNIID-00")}
        uid, method, _ = self.m.resolve_parent(
            "TRBF-KTNIID-00", "Confederated Salish and Kootenai Tribes", by_handle, {},
            self.reg)
        self.assertEqual((uid, method), ("", "UNRESOLVED_HANDLE_NAME_DISAGREES"))
        uid, method, _ = self.m.resolve_parent(
            "TRBF-KTNIID-00", "Kootenai Tribe of Idaho", by_handle, {}, self.reg)
        self.assertEqual((uid, method), ("CE-0015Z-Q0", "handle_exact"))


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


class PublicationMask(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(CODE))
        cls.p = _load("cedar_publication", CODE / "cedar_publication.py")

    def test_a_refused_owner_link_is_masked_and_the_row_ships(self):
        row = {"enterprise_name": "Arctic Catering Inc", "cedar_uid": "CE-00V01-AA",
               "owner_hub_name": "Arctic Village", "owner_class": "tribal_government",
               "attribution_refusal": na.GUARD_GENERIC_TOKEN}
        disposition, why = self.p.adjudication(row)
        self.assertEqual(disposition, self.p.MASK)
        self.p.mask_attribution(row, why)
        self.assertEqual((row["cedar_uid"], row["owner_hub_name"], row["owner_class"]),
                         ("", "", ""))
        self.assertEqual(row["enterprise_name"], "Arctic Catering Inc")
        clean = {"cedar_uid": "CE-00V02-AA", "attribution_refusal": ""}
        self.assertEqual(self.p.adjudication(clean)[0], self.p.PUBLISH)


if __name__ == "__main__":
    unittest.main()
