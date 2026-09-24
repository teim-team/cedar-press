"""Read-only namespace, role and transformation boundaries for Cedar IDs."""

import importlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "code") not in sys.path:
    sys.path.insert(0, str(ROOT / "code"))
ids = importlib.import_module("cedar_ids")


class IdentifierContractsTest(unittest.TestCase):
    def contract(self, collection, table, column):
        return ids.identifier_contract(collection, table, column)

    def setUp(self):
        self.entity = self.contract("identity", "cedar_identity_register.csv", "cedar_uid")
        self.owner = self.contract("need", "need_enterprises.csv", "owner_hub_cedar_uid")
        self.business = self.contract(
            "business", "registries/Cedar_Business_Register.csv", "business_uid"
        )

    def test_federal_register_publisher_ids_remain_exact_and_source_bound(self):
        contract = self.contract("nagpra", "nagpra_notices.csv", "document_number")
        # The publisher API returns each exact document_number, including the
        # correction/republication prefix: /api/v1/documents/<id>.json.
        keys = {"94-4238", "2026-05038", "X94-11116", "C9-6658",
                "R4-28004", "E5-7680", "C1-2013-10220", "R1-2026-05038"}
        for value in keys:
            with self.subTest(value=value):
                self.assertEqual(ids.validate_identifier(
                    value, contract, keys, source_system="Federal Register"), value)
                with self.assertRaises(ids.IdentifierContractError):
                    ids.validate_identifier(value, self.entity)
        for value in ("E5-999999", "CE-0016J-EB", "CB-1000520", "LOB-2000-001",
                      "E5-7680/../x", "E5-7680\n", "X-11116", "C1-foo-10220"):
            with self.subTest(refused=value):
                with self.assertRaises(ids.IdentifierContractError):
                    ids.validate_identifier(value, contract, keys, source_system="Federal Register")
        with self.assertRaises(ids.IdentifierContractError):
            ids.validate_identifier("E5-7680", contract, keys, source_system="LDA source")
        with self.assertRaises(ids.IdentifierContractError):
            ids.validate_identifier("E5-7680", contract, source_system="Federal Register")

    def test_checked_entity_namespace_is_exact(self):
        identity = ids._entity_validator()
        good = "CE-0016J-EB"
        self.assertTrue(identity.valid(good))
        for value in (
            good.replace("CE-", "CB-"),
            good.replace("CE-", "LOB-"),
            good.replace("CE-", "SRC-"),
            "CE-0016J-EA",
            None,
        ):
            with self.subTest(value=value):
                self.assertFalse(identity.valid(value))
                with self.assertRaises(ids.IdentifierContractError):
                    ids.validate_identifier(value, self.entity)
        identity.selftest()

    def test_shape_is_not_register_membership(self):
        with self.assertRaises(ids.IdentifierContractError):
            ids.validate_identifier("CE-0016J-EB", self.entity, registered_ids=set())
        self.assertEqual(
            ids.validate_identifier("CE-0016J-EB", self.entity, registered_ids={"CE-0016J-EB"}),
            "CE-0016J-EB",
        )

    def test_source_tribe_id_cannot_be_treated_as_cedar_uid(self):
        with self.assertRaises(ids.IdentifierContractError):
            ids.validate_identifier("TRBF-CHKSWN-00", self.entity)
        with self.assertRaises(ids.IdentifierContractError):
            self.contract("unknown-source", "input.csv", "tribe_id")

    def test_business_is_not_owner_entity(self):
        self.assertEqual(ids.validate_identifier("CB-1000520", self.business), "CB-1000520")
        with self.assertRaises(ids.IdentifierContractError):
            ids.validate_identifier("CB-1000520", self.owner)
        with self.assertRaises(ids.IdentifierContractError):
            ids.validate_identity_join(self.business, self.owner)

    def test_issued_need_ids_keep_their_namespace(self):
        enterprise = self.contract("need", "need_enterprises.csv", "enterprise_id")
        ids.validate_identifier("CEDAR-NEST-004804-P8", enterprise)
        with self.assertRaises(ids.IdentifierContractError):
            ids.validate_identifier("CEDAR-NEED-004804-P8", enterprise)
        relationship = self.contract("need", "need_enterprise_relations.csv", "enterprise_edge_id")
        ids.validate_identifier("NESTREL-00073120948274", relationship)

    def test_source_ids_are_not_invented_cedar_event_namespaces(self):
        deals = self.contract("deals", "deals_classified.csv", "Deal_ID")
        ids.validate_identifier("ND-2000-001", deals)
        with self.assertRaises(ids.IdentifierContractError):
            ids.validate_identifier("LOB-2000-001", deals)
        filing = self.contract("lobbying", "native_entity_lobbying_disclosures.csv", "filing_uuid")
        ids.validate_identifier(
            "0e43d288-9e15-4381-803d-5bba9cfb0c85",
            filing,
            {"0e43d288-9e15-4381-803d-5bba9cfb0c85"},
            source_system="LDA source",
        )
        with self.assertRaises(ids.IdentifierContractError):
            ids.validate_identifier("LOB-000001", filing)

    def test_cross_collection_join_requires_exact_explicit_mapping(self):
        recipient = self.contract("funding", "federal_funding_transactions.csv", "cedar_uid")
        with self.assertRaises(ids.IdentifierContractError):
            ids.validate_identity_join(self.owner, recipient)
        mapping = {
            "left": self.owner.binding,
            "right": recipient.binding,
            "left_role": "related_native_hub",
            "right_role": "recipient_attribution",
            "kind": "identity",
            "evidence": "fixture reviewed edge",
            "registry_version": "fixture-register-v1",
            "decision_id": "fixture-decision",
        }
        self.assertTrue(ids.validate_identity_join(self.owner, recipient, mapping))
        mapping["right_role"] = "business"
        with self.assertRaises(ids.IdentifierContractError):
            ids.validate_identity_join(self.owner, recipient, mapping)

    def test_mutable_attributes_cannot_define_identity(self):
        for field in ("canonical_name", "entity_class", "owner_cedar_uid", "address", "state"):
            with self.subTest(field=field), self.assertRaises(ids.IdentifierContractError):
                ids.validate_identity_key([field], stable_columns={field})
        self.assertTrue(ids.validate_identity_key(["filing_uuid"], {"filing_uuid"}))

    def test_derived_tables_preserve_without_minting(self):
        with patch.object(ids, "allocate", side_effect=AssertionError("no mint")):
            self.assertTrue(ids.validate_derived_identifiers(["CE-0016J-EB"], ["CE-0016J-EB"]))
            self.assertTrue(ids.validate_derived_identifiers(["CE-0016J-EB"], []))
            with self.assertRaises(ids.IdentifierContractError):
                ids.validate_derived_identifiers(["CE-0016J-EB"], ["CB-1000520"])

    def test_arbitrary_source_id_requires_authority_and_pinned_keys(self):
        source = self.contract("owned", "native_owned_businesses.csv", "business_source_id")
        with self.assertRaises(ids.IdentifierContractError):
            ids.validate_identifier("TBD-030:5196", source)
        with self.assertRaises(ids.IdentifierContractError):
            ids.validate_identifier(
                "TBD-030:5196", source, {"TBD-030:5196"}, source_system="wrong source"
            )
        ids.validate_identifier(
            "TBD-030:5196", source, {"TBD-030:5196"}, source_system=source.mint_authority
        )

    def test_duplicate_and_blank_record_keys_refused(self):
        for rows in ([{"document_number": "94-4238"}] * 2, [{"document_number": ""}], [{}]):
            with self.subTest(rows=rows), self.assertRaises(ids.IdentifierContractError):
                ids.validate_unique_record_keys(rows, ["document_number"])
        self.assertEqual(
            ids.validate_unique_record_keys([{"document_number": "94-4238"}], ["document_number"]),
            frozenset({("94-4238",)}),
        )

    def test_reassignment_competing_ids_and_disappearing_history_refused(self):
        previous = {"CE-0016J-EB": "immutable-object-1"}
        for current in (
            {},
            {"CE-0016J-EB": "different-object"},
            {**previous, "CE-00001-6S": "immutable-object-1"},
        ):
            with self.subTest(current=current), self.assertRaises(ids.IdentifierContractError):
                ids.validate_binding_history(previous, current)
        self.assertTrue(ids.validate_binding_history(previous, dict(previous)))

    def test_global_reference_keeps_collection_table_release_and_grain(self):
        manifest = {
            "collections": [
                {"id": "nagpra", "descriptor": {"version": "v1"}},
                {"id": "deals", "descriptor": {"version": "v1"}},
            ]
        }
        row = {"document_number": "94-4238"}
        grain = {
            "collection": "nagpra",
            "table": "nagpra_notices.csv",
            "grain": "one notice",
            "primary_key": ["document_number"],
        }
        keys = ids.validate_unique_record_keys([row], grain["primary_key"])
        ref = ids.global_record_reference(
            "nagpra",
            "nagpra_notices.csv",
            row,
            release_version="v1",
            manifest=manifest,
            grain_contract=grain,
            validated_keys=keys,
        )
        self.assertEqual(ref, ("nagpra", "nagpra_notices.csv", "v1", ("94-4238",)))
        for collection, version in (("missing", "v1"), ("nagpra", "v2")):
            with self.assertRaises(ids.IdentifierContractError):
                ids.validate_release_reference(collection, version, manifest)
        with self.assertRaises(ids.IdentifierContractError):
            ids.global_record_reference(
                "deals",
                "nagpra_notices.csv",
                row,
                release_version="v1",
                manifest=manifest,
                grain_contract=grain,
                validated_keys=keys,
            )
        with self.assertRaises(ids.IdentifierContractError):
            ids.global_record_reference(
                "nagpra",
                "nagpra_notices.csv",
                row,
                release_version="v1",
                manifest=manifest,
                grain_contract=grain,
                validated_keys=set(),
            )

    def test_contract_inventory_covers_twelve_launch_collections(self):
        collections = {c.collection for c in ids.IDENTIFIER_CONTRACTS.values()}
        self.assertEqual(
            collections - {"identity", "business"},
            {
                "funding",
                "federal-register",
                "legislation",
                "deals",
                "nagpra",
                "lobbying",
                "contractors",
                "subcontracting",
                "owned",
                "need",
                "natural-resources",
                "nonprofits",
            },
        )


if __name__ == "__main__":
    unittest.main()
