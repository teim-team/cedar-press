"""Maintained definition overrides require exact evidence and a current header."""

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

_PATH = Path(__file__).resolve().parents[2] / "scripts/preview_definitions.py"
_SPEC = importlib.util.spec_from_file_location("preview_definition_override_test_subject", _PATH)
assert _SPEC and _SPEC.loader
defs = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(defs)


class PreviewDefinitionOverridesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "press"
        self.producer = Path(self.temp.name) / "producer"
        self.root.mkdir()
        self.producer.mkdir()
        self.source = self.producer / "src" / "source.py"
        self.source.parent.mkdir()
        self.source.write_bytes(b"Source action date contract.\n")
        self.path = self.root / "data/cedar/preview_definition_overrides.json"
        self.path.parent.mkdir(parents=True)
        self.document = {
            "schema_version": 1,
            "evidence": {
                "source": {
                    "repository": "producer",
                    "path": "src/source.py",
                    "sha256": hashlib.sha256(self.source.read_bytes()).hexdigest(),
                    "revision": "a" * 40,
                }
            },
            "collections": {
                "funding": {
                    "action_date": {
                        "label": "Action date",
                        "meaning": "Source agency action date, distinct from the publication date.",
                        "evidence": ["source"],
                        "definition_source": {
                            "kind": "reviewed_transform_contract",
                            "path": "src/source.py",
                            "revision": "a" * 40,
                        },
                    }
                }
            },
        }

    def write(self):
        self.path.write_text(json.dumps(self.document), encoding="utf-8")

    def test_verified_override_fills_placeholder_and_carries_hashes(self):
        self.write()
        overrides = defs.load_overrides(self.root, self.producer)
        fields = defs.require_fields(
            "funding",
            ["action_date"],
            {"action_date": {"description": "Reviewed Cedar field contract: action_date"}},
            {},
            {},
            overrides=overrides,
        )
        self.assertEqual(
            fields[0]["meaning"], self.document["collections"]["funding"]["action_date"]["meaning"]
        )
        provenance = fields[0]["definition_source"]
        self.assertEqual(
            provenance["evidence"][0]["sha256"], self.document["evidence"]["source"]["sha256"]
        )
        self.assertEqual(
            provenance["override_file_sha256"], hashlib.sha256(self.path.read_bytes()).hexdigest()
        )
        again = defs.require_fields(
            "funding",
            ["action_date"],
            {
                "action_date": {
                    "description": fields[0]["meaning"],
                    "label": fields[0]["label"],
                    "definition_source": fields[0]["definition_source"],
                }
            },
            {},
            {},
            overrides=overrides,
        )
        self.assertEqual(again, fields)
        self.assertEqual(again[0]["definition_source"]["kind"], "reviewed_transform_contract")

    def test_changed_maintained_override_refreshes_its_own_previous_definition(self):
        self.write()
        first = defs.require_fields(
            "funding",
            ["action_date"],
            {},
            {},
            {},
            overrides=defs.load_overrides(self.root, self.producer),
        )
        self.document["collections"]["funding"]["action_date"]["meaning"] = (
            "The clarified source agency action date; publication is separate."
        )
        self.write()
        refreshed = defs.require_fields(
            "funding",
            ["action_date"],
            {
                "action_date": {
                    "description": first[0]["meaning"],
                    "definition_source": first[0]["definition_source"],
                }
            },
            {},
            {},
            overrides=defs.load_overrides(self.root, self.producer),
        )
        self.assertEqual(
            refreshed[0]["meaning"],
            self.document["collections"]["funding"]["action_date"]["meaning"],
        )
        self.assertNotEqual(
            refreshed[0]["definition_source"]["override_file_sha256"],
            first[0]["definition_source"]["override_file_sha256"],
        )

    def test_changed_evidence_and_missing_producer_are_refused(self):
        self.write()
        with self.assertRaisesRegex(ValueError, "requires --producer"):
            defs.load_overrides(self.root)
        self.source.write_bytes(b"Changed contract.\n")
        with self.assertRaisesRegex(ValueError, "evidence changed"):
            defs.load_overrides(self.root, self.producer)

    def test_override_does_not_replace_substantive_current_definition(self):
        self.write()
        overrides = defs.load_overrides(self.root, self.producer)
        evidence = {"kind": "pinned_current_contract", "sha256": "b" * 64}
        fields = defs.require_fields(
            "funding",
            ["action_date"],
            {
                "action_date": {
                    "description": "The exact existing agency action date.",
                    "definition_source": evidence,
                }
            },
            {},
            {},
            overrides=overrides,
        )
        self.assertEqual(fields[0]["meaning"], "The exact existing agency action date.")
        self.assertEqual(fields[0]["definition_source"], evidence)

    def test_unknown_current_column_does_not_silently_use_old_override(self):
        self.write()
        overrides = defs.load_overrides(self.root, self.producer)
        with self.assertRaisesRegex(ValueError, "absent from current"):
            defs.require_fields("funding", ["new_date"], {}, {}, {}, overrides=overrides)

    def test_definition_provenance_must_match_referenced_path_and_revision(self):
        for key, value in [("path", "src/other.py"), ("revision", "b" * 40)]:
            with self.subTest(key=key):
                source = self.document["collections"]["funding"]["action_date"]["definition_source"]
                previous = source[key]
                source[key] = value
                self.write()
                with self.assertRaisesRegex(ValueError, "not covered"):
                    defs.load_overrides(self.root, self.producer)
                source[key] = previous

    def test_placeholder_override_and_duplicate_json_keys_are_refused(self):
        self.document["collections"]["funding"]["action_date"]["meaning"] = "action date"
        self.write()
        with self.assertRaisesRegex(ValueError, "Substantive override"):
            defs.load_overrides(self.root, self.producer)
        self.path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Duplicate override"):
            defs.load_overrides(self.root, self.producer)

    def test_evidence_path_escape_and_silent_line_end_normalization_are_refused(self):
        self.document["evidence"]["source"]["path"] = "../outside.py"
        self.write()
        with self.assertRaisesRegex(ValueError, "escapes"):
            defs.load_overrides(self.root, self.producer)
        self.document["evidence"]["source"]["path"] = "src/source.py"
        self.write()
        self.source.write_bytes(b"Source action date contract.\r\n")
        with self.assertRaisesRegex(ValueError, "evidence changed"):
            defs.load_overrides(self.root, self.producer)

    def test_namespaced_source_field_labels_are_not_substantive_definitions(self):
        for value in ["source_system", "source system"]:
            self.assertFalse(defs.is_substantive(value, "documents__source_system"))
        self.assertTrue(
            defs.is_substantive(
                "Original Federal Register source-system label.", "documents__source_system"
            )
        )


if __name__ == "__main__":
    unittest.main()
