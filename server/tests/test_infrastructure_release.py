"""Grove-only Infrastructure declaration and full-component permission boundary."""

import copy
import unittest

from cedar_press import collections, governed_collections, repository


class InfrastructureReleaseTest(unittest.TestCase):
    def test_infrastructure_is_grove_only(self):
        self.assertIn("infrastructure", collections.GROVE_RELEASE_IDS)
        self.assertNotIn("infrastructure", {row.id for row in collections.LAUNCH_COLLECTION})
        self.assertNotIn("infrastructure", governed_collections.SHARED_COLLECTIONS)
        target = next(
            row for row in collections.GROVE_RELEASE_COLLECTIONS if row["id"] == "infrastructure"
        )
        self.assertEqual((target["name"], target["shelf"]), ("Native Infrastructure", "grove"))
        for tier in ("free", "press", "press_pro", "seed", "sprout", "sapling"):
            with self.subTest(tier=tier):
                self.assertFalse(repository.may_download_full(tier, "infrastructure"))
                self.assertFalse(repository.may_open(tier, "infrastructure"))
        for tier in ("grove", "tree"):
            with self.subTest(tier=tier):
                self.assertTrue(repository.may_download_full(tier, "infrastructure"))
                self.assertFalse(repository.may_open(tier, "infrastructure"))

    def test_generated_components_preserve_the_separate_table_contracts(self):
        declarations = governed_collections.component_declarations("infrastructure")
        self.assertEqual(
            set(declarations),
            {
                "profiles",
                "annual",
                "spatial",
                "records",
                "housing",
                "assets",
                "links",
                "energy",
                "environment",
                "datacenters",
                "audit",
                "coverage",
                "codebook",
                "sources",
            },
        )
        self.assertEqual(set(repository.grove_components("infrastructure")), set(declarations))
        self.assertEqual(len(declarations["records"]["order"]), 41)
        self.assertIn("amount_basis", declarations["records"]["order"])
        self.assertIn("source_text", declarations["housing"]["order"])
        for component, entry in declarations.items():
            with self.subTest(component=component):
                self.assertEqual(entry["collection"], "infrastructure")
                self.assertEqual(len(entry["order"]), len(set(entry["order"])))
                self.assertEqual(
                    set(entry["order"]), {field["column"] for field in entry["fields"]}
                )
                self.assertTrue(all(field["description"] for field in entry["fields"]))

    def manifest(self, component="records", permitted=True):
        order = governed_collections.presentation("infrastructure", component)["order"]
        return {
            "components": {
                component: {
                    "fields": [{"name": name, "type": "string"} for name in order],
                    "metadata": {},
                    "rights": {
                        "publication_class": "public" if permitted else "restricted",
                        "redistribution": permitted,
                    },
                    "download_permitted": permitted,
                    "primary_key": ["record_id"] if component == "records" else [order[0]],
                    "record_count": 1,
                    "files": {"records.jsonl": {"bytes": 1, "sha256": "a" * 64}},
                }
            }
        }

    def test_permitted_record_schema_uses_the_generated_exact_header(self):
        manifest = self.manifest()
        _contract, header, key, count, _expected = repository.grove_component_contract(
            manifest, "infrastructure", "records"
        )
        self.assertEqual(
            header, governed_collections.presentation("infrastructure", "records")["order"]
        )
        self.assertEqual((key, count), (["record_id"], 1))
        changed = copy.deepcopy(manifest)
        changed["components"]["records"]["fields"].pop()
        with self.assertRaisesRegex(repository.FullReleaseUnavailable, "field map"):
            repository.grove_component_contract(changed, "infrastructure", "records")

    def test_owner_ruling_restricted_components_are_not_held_for_rights(self):
        # Owner ruling 2026-10-04 (Elijah Moreno): Lumecon transforms the data
        # it publishes; source rights statuses are provenance, not a gate.
        for component in ("profiles", "housing", "datacenters"):
            with self.subTest(component=component):
                try:
                    repository.grove_component_contract(
                        self.manifest(component, False), "infrastructure", component
                    )
                except repository.ComponentPublicationHeld as error:
                    self.fail(f"rights status held {component}: {error}")
                except repository.FullReleaseUnavailable:
                    pass  # other contract checks may still apply to the fixture

    def test_missing_component_refuses_without_substitute_rows(self):
        with self.assertRaisesRegex(repository.FullReleaseUnavailable, "not in the pinned release"):
            repository.grove_component_contract({"components": {}}, "infrastructure", "records")


if __name__ == "__main__":
    unittest.main()
