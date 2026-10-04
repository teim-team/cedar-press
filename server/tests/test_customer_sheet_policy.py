"""The customer-table rules are the producer's, and every sample download obeys them.

``cedar_press/customer_sheet.py`` is vendored byte for byte from Lumecon-data
(``src/lumecon_data/customer_sheet.py``): the owner's rulings of 2026-10-04 --
dataset and public registry identifiers stay; the only Cedar IDs are the Cedar
Entity ID (CE-) and the Cedar Business ID (CB-); an event carries its own
dataset's event ID and never another's; proprietary identifiers (DUNS, Casino
City) and outdated Cedar identifier schemes (NEID handles, every CEDAR-
namespace, NESTREL-) are removed; public-citation sources, one table per
collection, no version labels -- are one set of rules on both sides.
"""

import csv
import io
import os
import sys
import unittest
from pathlib import Path

from cedar_press import customer_sheet

ROOT = Path(__file__).resolve().parents[2]


class VendoredPolicy(unittest.TestCase):
    def test_vendored_copy_is_the_producers(self):
        """Required where the producer is installed (Lumecon-data cedar-check, Gaming job)."""
        required = os.environ.get("CEDAR_REQUIRE_LUMECON_GAMING") == "1"
        try:
            from lumecon_data import customer_sheet as producer
        except ImportError:
            if required:
                raise
            self.skipTest("Lumecon-data is not installed in this job")
        self.assertEqual(
            Path(producer.__file__).read_bytes(),
            Path(customer_sheet.__file__).read_bytes(),
        )


class IdentifierRules(unittest.TestCase):
    """Owner rulings 2026-10-04: dataset and registry IDs stay; the only Cedar IDs
    are the Cedar Entity ID and the Cedar Business ID; an event carries its own
    dataset's event ID; DUNS, Casino City and outdated Cedar schemes go."""

    DATASET_IDS = {
        "deal_id": "CEV-2025-01F262669F",
        "award_id": "AWD-77",
        "source_record_id": "990PF-2019-25",
        "activity_id": "LDA-ACT-9",
        "superseded_by_record_id": "f0a2-lda",
        "supersession_group_id": "LDA-GRP-4",
        "subject_binding": "uei:Y1WNAYBJH9Z6",
        "business_source_id": "OWNERV6-12",
        "plot_record_id": "PLOT-TRACT-1",
        "uei": "Y1WNAYBJH9Z6",
        "ein": "47-0000001",
        "cedar_uid": "CE-0017X-NE",
        "business_uid": "CB-0000001",
    }
    #: Other datasets' own event IDs: never in a Deals row.
    FOREIGN_EVENT_IDS = {
        "disclosure_id": "GIV-000123",
        "resource_revenue_event_id": "ONRR-2020-55",
        "subaward_record_id": "FSRS-SUB-31",
        "filing_uuid": "0000fadb-51d5-4875-9736-9f42d07717af",
    }
    #: Outdated Cedar business and facility keys: no register binds a CB- ID.
    OUTDATED_CEDAR_IDS = {
        "enterprise_id": "CEDAR-NEST-000049-BS",
        "gaming_facility_id": "CEDAR-PLACE-000123-AB",
    }
    REMOVED = {
        "recipient_duns": "123456789",
        "casino_city_id": "CC-55",
        "row_sha256": "a" * 64,
        "schema_version": "v1.0",
        "record_key": '["K"]',
        "legacy_facility_id": "VP-0170",
        "tribe_id": "TRBF-CHKNAT-00",
        "neid_join_status": "joined",
    }
    RETIRED_VALUES = (
        "TRBF-",
        "AKNF-",
        "CEDAR-",
        "NESTREL-",
        "VP-",
        "CED-",
        "PROV-",
        "cedar_neid",
        "RRE-",
        "lda:",
    )

    def test_dataset_ids_are_presented_and_proprietary_ids_are_not(self):
        row = {
            **self.DATASET_IDS,
            **self.FOREIGN_EVENT_IDS,
            **self.OUTDATED_CEDAR_IDS,
            **self.REMOVED,
            "enterprise_edge_id": "NESTREL-291D0B2DBBCBD1",
            "identifier_type": "DUNS",
            "identifier_value": "987654321",
            "facility_keys": "CCP-843900; VP-0171; CEDAR-FAC-000011; CEDAR-PLACE-000123-AB",
            "entity_ids": "TRBF-POARCH-00-NIGC-2007-0011-0010|CE-0016T-YK|CEDAR-ENT-000048",
            "related_events": "CEV-2025-09E060E63E; RRE-MMS-CY1925-OTHER; "
            "lda:0000fadb-51d5-4875-9736-9f42d07717af",
            "attribution_status": "cedar_neid",
            "component_key": "PROV-OBS-ABCDEF123456",
            "match_note": "matched AKNF-AFGNAK-00-KONIAG via CICD crosswalk, CED-12",
            "note": "listed by Casino City",
            "remark": "DUNS 123456789 per vendor list",
            "label": "v1.0",
        }
        fields = [{"name": name, "type": "string"} for name in row]
        header, rows, report = customer_sheet.present_rows("deals", fields, [row])
        for name, value in self.DATASET_IDS.items():
            self.assertIn(name, header)
            self.assertEqual(rows[0][name], value)
        for name in {**self.REMOVED, **self.FOREIGN_EVENT_IDS}:
            self.assertNotIn(name, header)
        for name in self.OUTDATED_CEDAR_IDS:
            self.assertIsNone(rows[0][name])
        self.assertEqual(rows[0][customer_sheet.NEEDS_CEDAR_ID_COLUMN], "yes")
        self.assertIsNone(rows[0]["enterprise_edge_id"])
        self.assertIsNone(rows[0]["identifier_value"])
        self.assertIsNone(rows[0]["facility_keys"])
        self.assertEqual(rows[0]["entity_ids"], "CE-0016T-YK")
        self.assertEqual(rows[0]["related_events"], "CEV-2025-09E060E63E")
        self.assertIsNone(rows[0]["attribution_status"])
        self.assertIsNone(rows[0]["component_key"])
        self.assertEqual(rows[0]["match_note"], "matched via CICD crosswalk")
        self.assertIsNone(rows[0]["note"])
        self.assertEqual(rows[0]["remark"], "per vendor list")
        self.assertIsNone(rows[0]["label"])
        text = repr(rows)
        for leaked in ("123456789", "987654321", "CCP-", "Casino City", *self.RETIRED_VALUES):
            self.assertNotIn(leaked, text)
        self.assertGreater(report["counts"]["retired_id_values_removed"], 0)
        self.assertEqual(report["counts"]["foreign_event_id_values_removed"], 2)
        self.assertEqual(report["event_id_column"], "deal_id")
        self.assertIn("deal_id", report["dataset_id_columns"])
        self.assertIn("uei", report["public_registry_id_columns"])
        self.assertEqual(customer_sheet.check_table(header, rows, "deals"), [])

    def test_outdated_ids_bind_only_through_the_exact_register(self):
        from cedar_press.spreadsheet import cedar_id_crosswalk

        crosswalk = cedar_id_crosswalk()
        self.assertEqual(len(crosswalk), 1555)
        self.assertEqual(crosswalk["AKNF-AFGNAK-00-KONIAG"], "CE-00002-CJ")
        self.assertEqual(sum(key.startswith("CEDAR-ENT-") for key in crosswalk), 45)
        outdated = ("CEDAR-NEST", "CEDAR-PLACE", "NESTREL")
        self.assertFalse([k for k in crosswalk if k.startswith(outdated)])
        row = {"cedar_uid": "AKNF-AFGNAK-00-KONIAG", "business_uid": "CEDAR-NEST-000049-BS"}
        fields = [{"name": name, "type": "string"} for name in row]
        header, rows, report = customer_sheet.present_rows(
            "need", fields, [row], crosswalk=crosswalk
        )
        self.assertEqual(rows[0]["cedar_uid"], "CE-00002-CJ")
        self.assertIsNone(rows[0]["business_uid"])
        self.assertEqual(rows[0]["needs_cedar_id"], "yes")
        self.assertEqual(report["counts"]["cedar_ids_mapped"], 1)
        self.assertEqual(customer_sheet.check_table(header, rows, "need"), [])


class SampleDownloads(unittest.TestCase):
    """Every collection's sample download is one clean customer table."""

    def test_every_sample_download_obeys_the_customer_table_rules(self):
        from cedar_press import collections as launch
        from cedar_press import repository

        served = [d.id for d in launch.LAUNCH_COLLECTION if launch.collection_csv(d.id)]
        self.assertGreaterEqual(len(served), 10)
        for collection in served:
            with self.subTest(collection=collection):
                text = repository.collection_csv(collection)
                rows = list(csv.DictReader(io.StringIO(text, newline="")))
                self.assertTrue(rows)
                header = [name for name in rows[0] if name != "cite_as"]
                self.assertEqual(customer_sheet.check_table(header, rows, collection), [])
                self.assertNotIn("CEDAR-", text)
                self.assertNotIn("NESTREL-", text)
                event = customer_sheet.EVENT_ID_COLUMNS.get(collection)
                if event:
                    # Every event row carries its own dataset's event ID, once.
                    values = [row[event] for row in rows]
                    self.assertTrue(all(values), collection)
                    self.assertEqual(len(set(values)), len(values), collection)
                self.assertFalse([c for c in header if "duns" in c.lower()])
                self.assertFalse([c for c in header if "casino" in c.lower()])
                for packaging in ("record_type", "record_key", "record_grain"):
                    self.assertNotIn(packaging, header)
                self.assertIn("cite_as", rows[0])

    def test_identity_collections_carry_the_native_identity_basis(self):
        """Owner request 2026-10-04: the evidence behind each record's Native identity."""
        import json

        from cedar_press import collections as launch
        from cedar_press import repository

        declared = json.loads((ROOT / "data/cedar/field_map.json").read_text("utf-8"))
        declared = declared["presentation_columns"]
        self.assertEqual(set(declared["collections"]), set(customer_sheet.IDENTITY_COLLECTIONS))
        values = next(
            c["values"] for c in declared["columns"] if c["column"] == "native_identity_basis"
        )
        self.assertEqual(tuple(values), customer_sheet.NATIVE_IDENTITY_BASES)
        served = [d.id for d in launch.LAUNCH_COLLECTION if launch.collection_csv(d.id)]
        for collection in served:
            with self.subTest(collection=collection):
                rows = list(csv.DictReader(io.StringIO(repository.collection_csv(collection))))
                present = "native_identity_basis" in rows[0]
                self.assertEqual(present, collection in customer_sheet.IDENTITY_COLLECTIONS)
                self.assertEqual(present, "native_identity_source" in rows[0])
                if not present:
                    continue
                bases = customer_sheet.NATIVE_IDENTITY_BASES
                for row in rows:
                    self.assertIn(row["native_identity_basis"], bases)
                    if row["native_identity_basis"] == "unknown":
                        self.assertFalse(row["native_identity_source"])


if __name__ == "__main__":
    sys.exit(unittest.main())
