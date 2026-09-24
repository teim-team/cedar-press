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
    def test_accuracy_hold_overrides_stale_publishable_flag(self):
        self.assertEqual(
            policy.is_publication_eligible({"publish_hold": "Y", "publishable": "Y"}),
            (False, "publish_hold", policy.WITHHOLD),
        )

    def test_false_treaty_inclusion_is_held_without_erasing_issued_id(self):
        for identifier in policy.LEGISLATION_INCLUSION_HOLDS:
            row = {"bill_id": identifier, "publishable": "Y"}
            self.assertFalse(policy.is_publication_eligible(row)[0])
            self.assertEqual(row["bill_id"], identifier)
        self.assertTrue(
            policy.is_publication_eligible({"bill_id": "99-s-1396", "publishable": "Y"})[0]
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

    def test_refused_schema_keeps_filtered_preview_but_no_release(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            base = Path(directory)
            source = base / "source"
            clean = source / "data/clean"
            clean.mkdir(parents=True)
            raw = b"bill_id,title,source_url,publishable,email\nb1,<script>bad</script>,https://example.test/1,Y,private\nb2,withheld,https://example.test/2,N,secret\nb3,allowed,https://example.test/3,Y,private\n"
            file = clean / "native_bills.csv"
            file.write_bytes(raw)
            metadata = base / "authority/data/cedar"
            metadata.mkdir(parents=True)
            (metadata / "collections.manifest.json").write_text(
                json.dumps(
                    {
                        "collections": [
                            {
                                "id": "legislation",
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
                                "collection": "legislation",
                                "tables": [
                                    {"table": "native_bills.csv", "primary_key": ["bill_id"]}
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
                                "flagship": "native_bills.csv",
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
                        "legislation": {
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
                    side_effect=policy.FieldMapRefusal("legislation", [], "fixture refusal"),
                )
            )
            for name in ("translate_neid_values", "apply_official_names"):
                stack.enter_context(patch.object(customer, name))
            stack.enter_context(patch.object(customer, "enforce_denials", return_value=0))
            with redirect_stdout(io.StringIO()):
                bundle.candidate_review(source, base / "output", queue)
            rows = json.loads((base / "output/measurements.json").read_text())
            self.assertEqual(len(rows), 12)
            for result in rows:
                self.assertEqual(
                    (result["rows"], result["row_policy_eligible"], result["withheld"]), (3, 2, 1)
                )
                self.assertEqual(result["candidate_projection_rows"], 0)
                self.assertEqual(result["release_eligible_rows"], 0)
                self.assertTrue(result["source_unchanged"])
            self.assertEqual(list((base / "output").glob("*__candidate.csv")), [])
            preview = (base / "output/fixture-0.html").read_text()
            self.assertNotIn("<script>bad", preview)
            self.assertNotIn("private", preview)
            self.assertIn("&lt;script&gt;bad", preview)
            self.assertEqual(file.read_bytes(), raw)
            with self.assertRaises(ValueError):
                bundle.candidate_review(source, base / "output", queue)

    def test_repository_and_source_output_paths_refused(self):
        with self.assertRaises(ValueError):
            bundle.candidate_review(ROOT, ROOT / "dist/new-candidate", "unused.json")


if __name__ == "__main__":
    unittest.main()
