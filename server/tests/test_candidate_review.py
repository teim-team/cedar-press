"""Isolated candidate evidence must not become a publishable release by accident."""

import importlib
import io
import json
import sys
import tempfile
import unittest
from contextlib import ExitStack, redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code"))
bundle = importlib.import_module("1135_full_dataset_review_bundle")
customer = importlib.import_module("1137_customer_dataset_combine")
policy = importlib.import_module("cedar_publication")


class CandidateReviewTest(unittest.TestCase):
    def test_migrated_producers_refuse_before_reads_or_writes(self):
        for collection in __import__("cedar_pipeline").RELEASE_PILOTS:
            filename = policy.FLAGSHIP[collection]
            with self.subTest(collection=collection):
                with patch.object(Path, "open") as opened:
                    with self.assertRaisesRegex(ValueError, "RETIRED PRODUCER"):
                        customer.load(Path(filename))
                    opened.assert_not_called()
                with patch.object(customer, "contracts") as contracts:
                    with self.assertRaisesRegex(ValueError, "Lumecon Data collection-build"):
                        customer.build(dry=False, only=(collection,))
                    contracts.assert_not_called()
                with patch.object(bundle, "collections", return_value={collection: {filename: True}}):
                    with patch.object(bundle, "find") as find:
                        with self.assertRaisesRegex(ValueError, "RETIRED PRODUCER"):
                            bundle.build("samples")
                        find.assert_not_called()

    def test_load_receipts_conserve_withheld_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.csv"
            path.write_text("record_id,publishable\nkeep,Y\nhold,N\n")
            receipt = []
            with (
                patch.object(customer, "translate_neid_values"),
                patch.object(customer, "apply_official_names"),
                patch.object(customer, "enforce_denials", return_value=0),
            ):
                _, rows, held = customer.load(path, decision_receipt=receipt)
            self.assertEqual(len(rows) + sum(held.values()), 2)
            self.assertEqual(
                receipt,
                [
                    {
                        "event": "withheld",
                        "source_row_index": 1,
                        "reason": "publishable",
                        "record_id": "hold",
                    }
                ],
            )

    def test_accuracy_hold_overrides_stale_publishable_flag(self):
        self.assertEqual(
            policy.is_publication_eligible({"publish_hold": "Y", "publishable": "Y"}),
            (False, "publish_hold", policy.WITHHOLD),
        )

    def test_competition_uses_existing_dictionary_and_fails_closed(self):
        rows = [
            {"extent_competed": "A", "extent_competed_normalized": "FULL AND OPEN COMPETITION"},
            {"extent_competed": "NAN"},
        ]
        header = ["extent_competed", "extent_competed_normalized"]
        policy.recompute_derived("contractors", header, rows)
        self.assertEqual(
            [r["competition_type"] for r in rows], ["FULL AND OPEN COMPETITION", "NOT_REPORTED"]
        )
        self.assertEqual(rows[0]["extent_competed"], "A")
        for row in [
            {"extent_competed": "unrecognized"},
            {"extent_competed": "A", "extent_competed_normalized": "NOT COMPETED"},
        ]:
            before = dict(row)
            with self.assertRaises(policy.FieldMapRefusal):
                policy.recompute_derived("contractors", ["extent_competed"], [row])
            self.assertEqual(row, before)

    def test_subaward_scientific_homonym_does_not_waive_identity_gate(self):
        value = "OVERSEE NEID\nOBSERVATIONS AND STELLAR CHARACTERIZATION"
        self.assertFalse(policy.retired_identifier_in_value("subcontracting", "description", value))
        for column, text in [
            ("description", value + " cedar_neid"),
            ("attribution_status", value),
            ("description", "NEID-123"),
            ("description", "NEID observations"),
        ]:
            self.assertTrue(policy.retired_identifier_in_value("subcontracting", column, text))
        self.assertTrue(policy.retired_identifier_in_value("funding", "description", value))

    def test_subaward_roles_do_not_assert_ownership(self):
        entry = policy.field_map()["subcontracting"]
        self.assertNotIn("owner of", entry["entity_role"])
        self.assertEqual(
            [r["role"] for r in entry["entity_roles"]],
            ["subcontractor-side Native attribution", "prime-contractor-side Native attribution"],
        )

    def test_samples_and_customer_writer_share_row_policy(self):
        self.assertIs(bundle._customer.publication_row, customer.publication_row)
        with (
            patch.object(customer, "translate_neid_values"),
            patch.object(customer, "apply_official_names"),
            patch.object(customer, "enforce_denials", return_value=0),
        ):
            row, reason = customer.publication_row(
                {"title": "safe", "publishable": "N"}, ["title", "publishable"]
            )
            self.assertIsNone(row)
            self.assertEqual(reason, "publishable")
            row, reason = customer.publication_row(
                {"title": "safe", "publishable": "Y", "email": "private"}, ["title", "publishable"]
            )
            self.assertEqual(row, {"title": "safe", "publishable": "Y"})

    def test_retired_candidate_preview_refuses_before_output_creation(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            base = Path(directory)
            source = base / "source"
            clean = source / "data/clean"
            clean.mkdir(parents=True)
            raw = b"record_id,title,source_url,publishable,email\nb1,<script>bad</script>,https://example.test/1,Y,private\nb2,withheld,https://example.test/2,N,secret\nb3,allowed,https://example.test/3,Y,private\n"
            file = clean / "native_entity_lobbying_disclosures.csv"
            file.write_bytes(raw)
            metadata = base / "authority/data/cedar"
            metadata.mkdir(parents=True)
            (metadata / "collections.manifest.json").write_text(
                json.dumps(
                    {
                        "collections": [
                            {
                                "id": "lobbying",
                                "descriptor": {"tracks": "Bills", "sources": "Fixture"},
                            }
                        ]
                    }
                )
            )
            contracts = base / "contracts.json"
            contracts.write_text(
                json.dumps(
                    {
                        "contracts": [
                            {
                                "collection": "lobbying",
                                "tables": [
                                    {"table": "native_entity_lobbying_disclosures.csv", "primary_key": ["record_id"]}
                                ],
                            }
                        ]
                    }
                )
            )
            queue = base / "queue.json"
            queue.write_text(
                json.dumps(
                    {
                        "collections": [
                            {
                                "collection_id": "fixture-" + str(i),
                                "title": "Fixture",
                                "flagship": "native_entity_lobbying_disclosures.csv",
                            }
                            for i in range(12)
                        ]
                    }
                )
            )
            stack.enter_context(patch.object(bundle, "ROOT", base / "authority"))
            stack.enter_context(patch.object(bundle, "CONTRACTS", contracts))
            stack.enter_context(patch.object(policy, "register", return_value={}))
            stack.enter_context(
                patch.object(
                    policy,
                    "field_map",
                    return_value={
                        "lobbying": {
                            "fields": [
                                {"column": x, "decision": "keep"} for x in ("title", "source_url")
                            ]
                        }
                    },
                )
            )
            stack.enter_context(patch.object(policy, "recompute_derived"))
            stack.enter_context(
                patch.object(
                    policy,
                    "apply_field_map",
                    side_effect=policy.FieldMapRefusal("lobbying", [], "fixture refusal"),
                )
            )
            for name in ("translate_neid_values", "apply_official_names"):
                stack.enter_context(patch.object(customer, name))
            stack.enter_context(patch.object(customer, "enforce_denials", return_value=0))
            saved_queue = queue.read_text()
            queue.write_text(saved_queue.replace("native_entity_lobbying_disclosures.csv", "native_bills.csv"))
            with self.assertRaisesRegex(ValueError, "RETIRED PRODUCER"):
                bundle.candidate_review(source, base / "retired-output", queue)
            self.assertFalse((base / "retired-output").exists())
            queue.write_text(saved_queue)
            with self.assertRaisesRegex(ValueError, "RETIRED PRODUCER"):
                bundle.candidate_review(source, base / "output", queue)
            self.assertFalse((base / "output").exists())
            self.assertEqual(file.read_bytes(), raw)

    def test_repository_and_source_output_paths_refused(self):
        with self.assertRaises(ValueError):
            bundle.candidate_review(ROOT, ROOT / "dist/new-candidate", "unused.json")


if __name__ == "__main__":
    unittest.main()
