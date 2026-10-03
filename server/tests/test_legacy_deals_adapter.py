"""The legacy 40-column Deals preview against the 36-column producer header.

Holds ``legacy_deals_adapter`` to the two files it mediates between: the
PR #149 regression fixture (``CEV-*`` events, 40 legacy columns) and the
served producer sample (36 columns). The header the adapter emits must be the
served header exactly; the decomposition 40 - 6 - 3 + 2 + 3 = 36 is computed
from the field map, not typed; a uid is copied and never altered; a combine
target is owed, never filled from "whichever is nonblank". Nothing here reads
or writes the served sample.
"""

from __future__ import annotations

import json
import unittest

from tests import legacy_deals_adapter as adapter


class HeaderAndMapping(unittest.TestCase):
    def setUp(self) -> None:
        self.table = adapter.field_map_table()
        self.served_header, self.served_rows = adapter.read_csv(adapter.SERVED_SAMPLE)
        self.legacy_header, self.legacy_rows = adapter.read_csv(adapter.LEGACY_FIXTURE)

    def test_adapter_header_is_the_served_header_exactly(self) -> None:
        self.assertEqual(adapter.producer_header(self.table), self.served_header)
        self.assertEqual(len(self.served_header), 36)
        self.assertEqual(len(self.legacy_header), 40)
        # Same 33 approved names as the field map's reading order; the
        # producer writer sorts them after the three reserved columns.
        self.assertEqual(sorted(self.table["order"]), self.served_header[3:])
        self.assertNotEqual(self.table["order"], self.served_header[3:])

    def test_every_legacy_column_has_one_decision_and_the_counts_decompose(self) -> None:
        decisions = {f["column"]: f for f in self.table["fields"]}
        for column in self.legacy_header:
            self.assertIn(column, decisions, column)
        d = adapter.decomposition(self.table)
        self.assertEqual(d["legacy_columns"], 40)
        self.assertEqual(d["served_columns"], 36)
        self.assertEqual(d["net_difference"], 4)
        self.assertEqual(
            sorted(d["dropped"]),
            sorted(
                [
                    "Event_Quarter",
                    "Event_Month",
                    "Confidence",
                    "Date_Added",
                    "Data_As_Of",
                    "native_party_attribution_tier",
                ]
            ),
        )
        self.assertEqual(
            {k: sorted(v) for k, v in d["pairs_folded"].items()},
            {
                "additional_sources": ["Source_2", "Source_2_Type"],
                "deal_type": ["Deal_Category", "transaction_type"],
                "deal_status": ["Status", "deal_status_std"],
                "research_note": ["Candidate_Status", "Caveat", "Notes"],
            },
        )
        # research_note's three sources include two the legacy header never
        # carried (Caveat, Candidate_Status are build-time qualifications), so
        # only three pairs change the legacy count.
        folded_from_legacy = sum(
            len([s for s in sources if s in self.legacy_header]) - 1
            for sources in d["pairs_folded"].values()
            if len([s for s in sources if s in self.legacy_header]) > 1
        )
        self.assertEqual(folded_from_legacy, 3)
        self.assertEqual(d["one_to_one_derivations"], {"transaction_structure": ["Event_Type"]})
        self.assertEqual(d["added_from_register"], ["cedar_entity_role", "entity_class"])
        self.assertEqual(40 - len(d["dropped"]) - folded_from_legacy + 2 + 3, 36)

    def test_mapping_table_names_a_destination_or_a_drop_for_every_legacy_column(self) -> None:
        mapping = {
            m["legacy_column"]: m for m in adapter.column_mapping(self.table) if m["legacy_column"]
        }
        served = set(self.served_header)
        for column in self.legacy_header:
            m = mapping[column]
            if m["decision"] in ("internal", "document"):
                self.assertIsNone(m["destination"], column)
                self.assertNotIn(column, served, column)
            else:
                self.assertIn(m["destination"], served, (column, m["destination"]))
        blocking = {m["legacy_column"] for m in adapter.column_mapping(self.table) if m["blocking"]}
        # Caveat and Candidate_Status are build-time qualifications the field
        # map also marks blocking; the legacy header carries only Notes.
        self.assertEqual(blocking, {"Notes", "Caveat", "Candidate_Status"})
        self.assertEqual(blocking & set(self.legacy_header), {"Notes"})
        destinations = {
            m["destination"] for m in adapter.column_mapping(self.table) if m["destination"]
        }
        self.assertEqual(destinations, served)


class AdaptingTheFixture(unittest.TestCase):
    def setUp(self) -> None:
        self.table = adapter.field_map_table()
        self.register = adapter.register_names()
        _, self.legacy_rows = adapter.read_csv(adapter.LEGACY_FIXTURE)
        self.result = adapter.adapt(self.legacy_rows, self.register, table=self.table)

    def test_row_count_header_and_record_columns(self) -> None:
        self.assertEqual(self.result["report"]["rows_in"], 10)
        self.assertEqual(self.result["report"]["rows_out"], 10)
        served_header, served_rows = adapter.read_csv(adapter.SERVED_SAMPLE)
        self.assertEqual(self.result["header"], served_header)
        for row in self.result["rows"]:
            self.assertEqual(list(row), served_header)
            self.assertEqual(row["record_type"], adapter.RECORD_TYPE)
            self.assertEqual(json.loads(row["record_key"]), [row["deal_id"]])
            self.assertEqual(row["record_grain"], adapter.RECORD_GRAIN)
        # The same record_key shape the producer writes.
        self.assertEqual(
            served_rows[0]["record_key"],
            json.dumps([served_rows[0]["deal_id"]], separators=(",", ":")),
        )
        self.assertEqual(served_rows[0]["record_grain"], adapter.RECORD_GRAIN)

    def test_uids_are_copied_never_altered_and_names_come_from_the_register(self) -> None:
        for legacy, new in zip(self.legacy_rows, self.result["rows"], strict=True):
            self.assertEqual(new["cedar_uid"], legacy["cedar_uid"])
            self.assertIn(new["cedar_uid"], self.register)
            self.assertEqual(new["canonical_name"], self.register[new["cedar_uid"]][0])
            self.assertEqual(new["entity_class"], self.register[new["cedar_uid"]][1])
            self.assertEqual(new["cedar_entity_role"], "")
        self.assertEqual(self.result["report"]["uids_not_in_register"], [])
        self.assertEqual(self.result["report"]["name_disagreements"], [])

    def test_renames_and_keeps_are_value_for_value(self) -> None:
        renames = {f["column"]: f["to"] for f in self.table["fields"] if f["decision"] == "rename"}
        renames.pop("native_party_canonical_name")  # rewritten from the register by uid
        keeps = {f["column"] for f in self.table["fields"] if f["decision"] == "keep"} - {
            "research_note"
        }
        for legacy, new in zip(self.legacy_rows, self.result["rows"], strict=True):
            for source, target in renames.items():
                self.assertEqual(new[target], legacy[source], (legacy["Deal_ID"], source))
            for column in keeps:
                self.assertEqual(new[column], legacy[column], (legacy["Deal_ID"], column))
            for dropped in adapter.decomposition(self.table)["dropped"]:
                self.assertNotIn(dropped, new)

    def test_additional_sources_is_a_json_list_built_from_source_2(self) -> None:
        for row in self.result["rows"]:
            self.assertEqual(
                json.loads(row["additional_sources"]), []
            )  # the fixture carries no Source_2
        built = adapter.additional_sources(
            {"Source_2": "https://example.org/x", "Source_2_Type": "Government release"}
        )
        self.assertEqual(
            json.loads(built),
            [{"url": "https://example.org/x", "source_type": "Government release"}],
        )

    def test_crosswalk_targets_are_owed_without_a_crosswalk_and_never_whichever_is_nonblank(
        self,
    ) -> None:
        report = self.result["report"]
        for target in ("deal_type", "deal_status", "transaction_structure"):
            self.assertEqual(len(report["owed"][target]), 10, target)
            self.assertEqual(report["crosswalked"][target], 0)
            for row in self.result["rows"]:
                self.assertEqual(row[target], "")
        # A row whose two sources disagree stays owed even when the crosswalk
        # maps one of them: the field map forbids keeping whichever is nonblank.
        disagreeing = dict(
            self.legacy_rows[0], Deal_Category="ACQUISITION", transaction_type="DEBT_FINANCING"
        )
        out = adapter.adapt(
            [disagreeing],
            self.register,
            {"deal_type": {"ACQUISITION": "Acquisition"}},
            table=self.table,
        )
        self.assertEqual(out["rows"][0]["deal_type"], "")
        self.assertEqual(
            out["report"]["owed"]["deal_type"],
            [(disagreeing["Deal_ID"], ["ACQUISITION", "DEBT_FINANCING"])],
        )

    def test_a_supplied_crosswalk_applies_only_where_both_sources_agree_on_a_mapped_value(
        self,
    ) -> None:
        crosswalks = {
            "deal_type": {"ACQUISITION": "Acquisition"},
            "deal_status": {"Acquisition completed": "Completed"},
            "transaction_structure": {"CLOSING_MONTH": "Acquisition closed in the stated month"},
        }
        out = adapter.adapt(self.legacy_rows, self.register, crosswalks, table=self.table)
        by_id = {row["deal_id"]: row for row in out["rows"]}
        pokagon = by_id["CEV-2021-357C5BC869"]
        self.assertEqual(pokagon["deal_type"], "Acquisition")
        self.assertEqual(pokagon["deal_status"], "Completed")
        self.assertEqual(pokagon["transaction_structure"], "Acquisition closed in the stated month")
        self.assertEqual(
            out["report"]["crosswalked"],
            {"deal_type": 2, "deal_status": 1, "transaction_structure": 1},
        )
        self.assertEqual(len(out["report"]["owed"]["deal_type"]), 8)

    def test_populated_notes_block_until_an_editorial_research_note_exists(self) -> None:
        report = self.result["report"]
        self.assertTrue(report["blocking"])
        self.assertEqual(len(report["blocking_notes"]), 10)
        for row in self.result["rows"]:
            self.assertEqual(row["research_note"], "")
        silent = adapter.adapt(
            [dict(self.legacy_rows[0], Notes="")], self.register, table=self.table
        )
        self.assertFalse(silent["report"]["blocking"])

    def test_adapter_does_not_touch_the_served_sample(self) -> None:
        import hashlib

        pinned = json.loads(
            (adapter.ROOT / "data/cedar/verified-preview-releases.json").read_text(encoding="utf-8")
        )
        digest = hashlib.sha256(adapter.SERVED_SAMPLE.read_bytes()).hexdigest()
        self.assertEqual(digest, pinned["collections"]["deals"]["sample_sha256"])


if __name__ == "__main__":
    unittest.main()
