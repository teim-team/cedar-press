"""Preview dictionary resolution must preserve roles and declared renames."""

import importlib.util
import unittest
from pathlib import Path

_PATH = Path(__file__).resolve().parents[2] / "scripts" / "preview_definitions.py"
_SPEC = importlib.util.spec_from_file_location("preview_definitions_for_test", _PATH)
assert _SPEC and _SPEC.loader
defs = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(defs)


def inputs():
    fields = [
        {
            "column": "assistance_type",
            "label": "Assistance type code",
            "meaning": "The source's coded assistance type.",
            "rename_to": "assistance_type_code",
        },
        {
            "column": "assistance_type_description",
            "label": "Assistance type",
            "meaning": "The source's readable assistance type.",
            "rename_to": "assistance_type",
        },
        {
            "column": "action_date",
            "label": "Action date",
            "meaning": "The date of this agency action.",
        },
        {
            "column": "cedar_entity_role",
            "label": "Entity role",
            "meaning": "Owner of the awardee.",
            "add": True,
        },
    ]
    book = {"tables": {"funding/legacy": {"collection": "funding", "fields": fields}}}
    mapping = {
        "tables": {
            "funding/legacy": {
                "collection": "funding",
                "order": [
                    "assistance_type_code",
                    "assistance_type",
                    "action_date",
                    "cedar_entity_role",
                ],
                "fields": [
                    {
                        "column": "assistance_type",
                        "decision": "rename",
                        "to": "assistance_type_code",
                    },
                    {
                        "column": "assistance_type_description",
                        "decision": "rename",
                        "to": "assistance_type",
                    },
                    {"column": "action_date", "decision": "keep"},
                ],
                "new": [
                    {
                        "column": "cedar_entity_role",
                        "from": "constant:affiliate",
                        "why": "Affiliation.",
                    }
                ],
            }
        }
    }
    return book, mapping


class PreviewDefinitionsTest(unittest.TestCase):
    def test_rename_target_does_not_borrow_same_named_source_meaning(self):
        book, mapping = inputs()
        fields = defs.require_fields(
            "funding", ["assistance_type", "assistance_type_code"], {}, book, mapping
        )
        self.assertEqual(fields[0]["meaning"], "The source's readable assistance type.")
        self.assertEqual(
            fields[0]["definition_source"]["source_column"], "assistance_type_description"
        )
        self.assertEqual(fields[1]["meaning"], "The source's coded assistance type.")

    def test_placeholder_resolves_only_through_declared_direct_field(self):
        book, mapping = inputs()
        fields = defs.require_fields(
            "funding",
            ["action_date"],
            {"action_date": {"description": "Reviewed Cedar field contract: action_date"}},
            book,
            mapping,
        )
        self.assertEqual(fields[0]["meaning"], "The date of this agency action.")
        self.assertEqual(fields[0]["definition_source"]["kind"], "reviewed_field_map_source")

    def test_substantive_producer_description_is_preserved(self):
        book, mapping = inputs()
        fields = defs.require_fields(
            "funding",
            ["action_date"],
            {
                "action_date": {
                    "description": "Current exact action date, with source qualification."
                }
            },
            book,
            mapping,
        )
        self.assertEqual(
            fields[0]["meaning"], "Current exact action date, with source qualification."
        )
        self.assertEqual(fields[0]["definition_source"]["kind"], "producer_description")

    def test_stale_derived_owner_role_is_not_imported(self):
        book, mapping = inputs()
        result = defs.resolve_fields("funding", ["cedar_entity_role"], {}, book, mapping)
        self.assertEqual(result["fields"], [])
        self.assertEqual(result["unresolved"][0]["column"], "cedar_entity_role")
        self.assertIn("derived", result["unresolved"][0]["rejected_candidates"][0])

    def test_disagreeing_rename_and_multiple_targets_fail(self):
        book, mapping = inputs()
        book["tables"]["funding/legacy"]["fields"][0]["rename_to"] = "wrong_target"
        with self.assertRaisesRegex(ValueError, "unresolved"):
            defs.require_fields("funding", ["assistance_type_code"], {}, book, mapping)
        book, mapping = inputs()
        book["tables"]["funding/second"] = book["tables"]["funding/legacy"]
        mapping["tables"]["funding/second"] = mapping["tables"]["funding/legacy"]
        result = defs.resolve_fields("funding", ["action_date"], {}, book, mapping)
        self.assertEqual(result["unresolved"][0]["reason"], "ambiguous_target")
        self.assertEqual(len(result["unresolved"][0]["candidates"]), 2)

    def test_internal_fields_cannot_supply_public_meanings(self):
        book, mapping = inputs()
        mapping["tables"]["funding/legacy"]["fields"][2]["decision"] = "internal"
        result = defs.resolve_fields("funding", ["action_date"], {}, book, mapping)
        self.assertEqual(result["fields"], [])
        self.assertEqual(len(result["unresolved"]), 1)

    def test_missing_definition_never_becomes_a_generic_review_claim(self):
        book, mapping = inputs()
        result = defs.resolve_fields(
            "funding",
            ["unknown_field"],
            {"unknown_field": {"description": "See the exact release contract."}},
            book,
            mapping,
        )
        self.assertEqual(result["fields"], [])
        self.assertEqual(result["unresolved"][0]["column"], "unknown_field")
        for value in [
            "",
            "action_date",
            "action date",
            "Reviewed Cedar field contract: action_date",
        ]:
            self.assertFalse(defs.is_substantive(value, "action_date"))

    def test_metadata_contract_and_header_shape_are_explicit(self):
        fields = defs.require_fields(
            "funding", ["record_type", "record_key", "record_grain"], {}, {}, {}
        )
        self.assertEqual([field["column"] for field in fields], list(defs.METADATA_MEANINGS))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            defs.require_fields("funding", ["same", "same"], {}, {}, {})


if __name__ == "__main__":
    unittest.main()
