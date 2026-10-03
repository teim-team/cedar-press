import copy
import unittest

from cedar_press import plot_map, repository


class PlotMapTest(unittest.TestCase):
    def setUp(self):
        self.selected = [
            {
                "release_row_sha256": "a" * 64,
                "source_part": "wi_000001",
                "row": {"plot_record_id": "plot-1"},
                "source": {"publisher": "County"},
            }
        ]
        self.value = {
            "type": "FeatureCollection",
            "collection": "plot",
            "component": "ownership_observations",
            "release_id": "b" * 64,
            "scope": "permitted_review_preview",
            "source_rows": 5000,
            "crs": "OGC:CRS84",
            "axis_order": "longitude,latitude",
            "omitted": [],
            "features": [
                {
                    "type": "Feature",
                    "id": "plot-1",
                    "properties": {
                        "release_row_sha256": "a" * 64,
                        "source_part": "wi_000001",
                        "ownership_inference_permitted": False,
                        "entity_link": None,
                        "crs": "OGC:CRS84",
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[-90, 44], [-89, 44], [-89, 45], [-90, 44]]],
                    },
                }
            ],
        }

    def read(self, value=None):
        return plot_map.present(
            self.value if value is None else value,
            release_id="b" * 64,
            component="ownership_observations",
            scope="permitted_review_preview",
            source_rows=5000,
            selected=self.selected,
        )

    def test_exact_coordinates_separate_from_fitted_display(self):
        result = self.read()
        self.assertEqual(result["features"], self.value["features"])
        outline = result["outlines"][0]
        self.assertEqual(outline["bbox"], [-90, 44, -89, 45])
        self.assertIn("M-90 -44", outline["path"])
        self.assertEqual(outline["source"], {"publisher": "County"})

    def test_wrong_release_rights_identity_and_coordinate_units_refused(self):
        for key, value in [
            ("release_id", "c" * 64),
            ("scope", "internal_only"),
            ("crs", "EPSG:3857"),
            ("component", "internal_parcels"),
        ]:
            with self.subTest(key=key), self.assertRaises(repository.FullReleaseUnavailable):
                self.read({**self.value, key: value})
        for key, value in [
            ("release_row_sha256", "d" * 64),
            ("source_part", "different"),
            ("ownership_inference_permitted", True),
            ("entity_link", "CE-fabricated"),
        ]:
            changed = copy.deepcopy(self.value)
            changed["features"][0]["properties"][key] = value
            with self.subTest(key=key), self.assertRaises(repository.FullReleaseUnavailable):
                self.read(changed)
        changed = copy.deepcopy(self.value)
        changed["features"][0]["geometry"]["coordinates"][0][1] = [500000, 4000000]
        with self.assertRaises(repository.FullReleaseUnavailable):
            self.read(changed)
