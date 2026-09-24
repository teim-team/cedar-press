"""Regression gates for retired Cedar identifiers and read-only resolution."""

import ast
import importlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code"))
ids = importlib.import_module("cedar_ids")
pub = importlib.import_module("cedar_publication")
inventory = importlib.import_module("audit_retired_ids")


class IdentifierRetirementTest(unittest.TestCase):
    def test_inventory_reports_path_column_and_occurrence_count(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "gaming.csv"
            path.write_text("facility_id,entity_id\nCCP-123,TRBF-ONE-00\n"
                            "CEDAR-FAC-000001,CE-0016J-EB\n", encoding="utf-8")
            result = inventory.inventory(path)
            self.assertEqual(result["rows"], 2)
            self.assertEqual({(hit["column"], hit["prefix"], hit["count"])
                              for hit in result["retired"]},
                             {("facility_id", "CCP", 1),
                              ("facility_id", "CEDAR-FAC", 1),
                              ("entity_id", "TRBF", 1)})

    def test_historical_inline_mint_entrypoints_are_closed(self):
        entrypoints = {
            "52_add_village_corporations.py": "main",
            "61_add_nho_intertribal_to_spine.py": "main",
            "73_add_tcu_and_cdfi.py": "cmd_add",
            "75_add_bie_schools_and_uios.py": "main",
            "163_promote_nho_universe_in_place.py": "main",
            "426_mint_bristol_bay_spine_entities.py": "main",
            "524_universe_gap.py": "phase_promote",
        }
        for file, function in entrypoints.items():
            with self.subTest(file=file):
                tree = ast.parse((ROOT / "code" / file).read_text(encoding="utf-8"))
                node = next(
                    n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == function
                )
                self.assertIsInstance(node.body[0], ast.Raise)

    def test_retired_prefixes_cannot_issue_by_any_shared_allocator_api(self):
        for prefix in ids.RETIRED_ISSUANCE_PREFIXES:
            with self.subTest(prefix=prefix):
                with self.assertRaises(ValueError):
                    ids.allocate(prefix)
                with self.assertRaises(ValueError):
                    ids.format_id(prefix, 1)
                with self.assertRaises(ValueError):
                    ids.declare_static_block(prefix, 1, 1, "test", "retired")

    def test_class_reclassification_cannot_construct_another_handle(self):
        with self.assertRaises(ValueError):
            ids.reclassify("TRBS-CHECK-00", "Federally recognized tribe")
        with self.assertRaises(ValueError):
            ids.class_prefix("Federally recognized tribe")
        self.assertEqual(ids.historical_class_prefix("Federally recognized tribe"), "TRBF")

    def test_legacy_handle_is_only_a_checked_read_only_lookup(self):
        with patch.object(pub, "neid_map", return_value={"TRBF-ONE-00": "CE-0016J-EB"}), \
             patch.object(pub, "_NEID_AMBIGUOUS", {"TRBF-TWO-00": ["CE-0016J-EB", "CE-00001-6S"]}):
            self.assertEqual(pub.resolve_retired_entity_handle("TRBF-ONE-00"), "CE-0016J-EB")
            for handle in ("TRBF-TWO-00", "TRBF-UNKNOWN-00", "TRBF-ONE-00 "):
                with self.subTest(handle=handle), self.assertRaises(ValueError):
                    pub.resolve_retired_entity_handle(handle)

    def test_canonical_uid_contract_refuses_legacy_even_if_registered(self):
        contract = ids.identifier_contract("identity", "cedar_identity_register.csv", "cedar_uid")
        with self.assertRaises(ids.IdentifierContractError):
            ids.validate_identifier("TRBF-ONE-00", contract, {"TRBF-ONE-00"})

    def test_gaming_facility_requires_registered_checked_place(self):
        identity = ids._entity_validator()
        place = "CEDAR-PLACE-000001-" + identity.check_chars(identity.encode(1))
        self.assertEqual(ids.validate_gaming_facility_id(place, {place}), place)
        for candidate in ("CCP-123", "VP-0011", "TPL-0127", "CEDAR-FAC-000001",
                          "PROV-GFAC:" + place, place[:-1] + "Z"):
            with self.subTest(candidate=candidate), self.assertRaises(ids.IdentifierContractError):
                ids.validate_gaming_facility_id(candidate, {candidate})
        with self.assertRaises(ids.IdentifierContractError):
            ids.validate_gaming_facility_id(place, set())


if __name__ == "__main__":
    unittest.main()
