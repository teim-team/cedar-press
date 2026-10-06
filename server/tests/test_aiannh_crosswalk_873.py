"""873 writes one assignment row per AIANNH polygon a point falls in.

AIANNH areas overlap: off-reservation trust land sits inside Oklahoma tribal
statistical areas. 873 used to keep only the first polygon the index returned,
so a point on trust land inside an OTSA could be recorded under the OTSA alone
and never raise Lumecon-data's ``in_home_area`` link (legal land only). These
tests build SYNTHETIC areas and points (invented GEOIDs, names and boxes, no
TIGER bytes) and need no shapely: the geometry is passed in.
"""

import contextlib
import csv
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "code" / "873_build_aiannh_crosswalk.py"


def _load():
    spec = importlib.util.spec_from_file_location("aiannh_crosswalk_873", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Box:
    """A synthetic polygon: an axis-aligned box that covers its boundary."""

    def __init__(self, minx, miny, maxx, maxy):
        self.bbox = (minx, miny, maxx, maxy)

    def covers(self, point):
        lo, la = point
        x0, y0, x1, y1 = self.bbox
        return x0 <= lo <= x1 and y0 <= la <= y1


#: A synthetic OTSA (D6) and, inside it, synthetic trust land (D3). The OTSA is
#: listed first, as the index happened to return it in the defect.
OTSA = {"geoid": "9902R", "name": "Synthetic OTSA", "classfp": "D6", "comptyp": "R"}
TRUST = {"geoid": "9901T", "name": "Synthetic Trust Land", "classfp": "D3", "comptyp": "T"}
GEOMS = [Box(-98.0, 35.0, -96.0, 37.0), Box(-97.2, 35.8, -96.8, 36.2)]
META = [OTSA, TRUST]


class ContainingAreas(unittest.TestCase):
    def setUp(self):
        self.m = _load()

    def rows(self, lo, la, cand=(0, 1)):
        rows, areas = self.m.assignment_rows(
            "gaming_facilities.csv:SYN-1",
            "gaming_facilities.csv",
            "SYN-1",
            "Synthetic",
            la,
            lo,
            "99001",
            "synthetic",
            (lo, la),
            list(cand),
            GEOMS,
            META,
        )
        return [dict(zip(self.m.PTS_FIELDS, row, strict=True)) for row in rows], areas

    def test_point_in_trust_land_inside_an_otsa_gets_both_rows(self):
        rows, areas = self.rows(-97.0, 36.0)
        self.assertEqual([r["aiannh_geoid"] for r in rows], ["9901T", "9902R"])
        self.assertEqual([r["aiannh_classfp"] for r in rows], ["D3", "D6"])
        self.assertEqual({r["point_id"] for r in rows}, {"gaming_facilities.csv:SYN-1"})
        self.assertTrue(all(r["inside_flag"] == "1" for r in rows))
        self.assertTrue(all(r["n_containing_areas"] == 2 for r in rows))
        self.assertEqual([a["geoid"] for a in areas], ["9901T", "9902R"])
        # Candidate order does not decide which area is recorded.
        reordered, _ = self.rows(-97.0, 36.0, cand=(1, 0))
        self.assertEqual(reordered, rows)

    def test_point_only_in_the_otsa_gets_one_row(self):
        rows, _ = self.rows(-97.9, 35.1)
        self.assertEqual([r["aiannh_geoid"] for r in rows], ["9902R"])
        self.assertEqual(rows[0]["n_containing_areas"], 1)

    def test_point_outside_every_area_keeps_its_one_outside_row(self):
        rows, areas = self.rows(-90.0, 40.0)
        self.assertEqual(areas, [])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["inside_flag"], "0")
        self.assertEqual(rows[0]["aiannh_geoid"], "")
        self.assertEqual(rows[0]["n_containing_areas"], 0)

    def test_the_consumer_links_the_trust_land_point_in_home_area(self):
        """Lumecon-data's home_community reads 873 rows; skipped where it is absent."""
        try:
            from lumecon_data import home_community as hc
        except ImportError:
            self.skipTest("lumecon_data.home_community is not installed in this job")
        rows, _ = self.rows(-97.0, 36.0)
        entity = "CE-SYN01-AA"
        homes = hc.build_entity_homes(
            [hc.EntityGeography(entity)],
            [hc.AiannhHome(entity, "9901T", "Synthetic Trust Land", "D3")],
        )
        assignments = [hc.point_assignment_from_873(r) for r in reversed(rows)]
        (link,) = hc.benefit_links(homes, assignments=assignments)
        self.assertEqual((link.benefit_entity_id, link.benefit_link), (entity, "in_home_area"))


class VerifyAndSelftest(unittest.TestCase):
    """verify and selftest still work on the one-row-per-(point, area) layout."""

    def setUp(self):
        self.m = _load()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        # No live source tables: point conservation (I3) is not measured here.
        self.m.CLEAN = self.tmp.name
        base = Path(self.tmp.name)
        self.dim, self.pts, self.ovl = (base / n for n in ("dim.csv", "pts.csv", "ovl.csv"))
        areas = [(OTSA, GEOMS[0]), (TRUST, GEOMS[1])]
        areas += [
            (
                {
                    "geoid": f"{8000 + i:04d}R",
                    "name": f"Synthetic {i}",
                    "classfp": "D2",
                    "comptyp": "R",
                },
                Box(-80.0, 30.0, -79.0, 31.0),
            )
            for i in range(862)
        ]
        with self.dim.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(self.m.DIM_FIELDS)
            for meta, box in areas:
                w.writerow(
                    [
                        meta["geoid"],
                        meta["geoid"][:4],
                        meta["name"],
                        meta["name"],
                        "",
                        meta["classfp"],
                        meta["comptyp"],
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        *(f"{v:.6f}" for v in box.bbox),
                        1,
                        "0",
                    ]
                )
        with self.pts.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(self.m.PTS_FIELDS)
            for rid, (lo, la) in enumerate([(-97.0, 36.0), (-97.9, 35.1), (-90.0, 40.0)]):
                rows, _ = self.m.assignment_rows(
                    f"t.csv:{rid}",
                    "t.csv",
                    str(rid),
                    "",
                    la,
                    lo,
                    "99001",
                    "",
                    (lo, la),
                    [0, 1],
                    GEOMS,
                    META,
                )
                w.writerows(rows)
        with self.ovl.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(self.m.OVL_FIELDS)
            w.writerow(
                [
                    "9901T",
                    "Synthetic Trust Land",
                    "99001",
                    "99",
                    1,
                    "t.csv",
                    "observed_point",
                    self.m.COVERAGE_NOTE,
                ]
            )

    def quiet(self, call):
        with contextlib.redirect_stdout(io.StringIO()):
            return call()

    def test_verify_accepts_several_rows_for_one_point(self):
        self.assertEqual(self.m.verify(self.dim, self.pts, self.ovl, quiet=True), 0)

    def test_verify_refuses_a_repeated_point_area_pair(self):
        with self.pts.open(newline="", encoding="utf-8") as fh:
            rows = list(csv.reader(fh))
        rows.append(list(rows[1]))
        with self.pts.open("w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerows(rows)
        self.assertEqual(self.m.verify(self.dim, self.pts, self.ovl, quiet=True), 1)

    def test_verify_refuses_a_dropped_containing_area(self):
        # The defect's output shape: the first area kept, the nested one lost.
        with self.pts.open(newline="", encoding="utf-8") as fh:
            rows = list(csv.reader(fh))
        self.assertEqual(rows[1][0], rows[2][0])
        with self.pts.open("w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerows(rows[:2] + rows[3:])
        self.assertEqual(self.m.verify(self.dim, self.pts, self.ovl, quiet=True), 1)

    def test_selftest_fires_every_invariant(self):
        self.assertEqual(
            self.quiet(lambda: self.m.selftest(str(self.dim), str(self.pts), str(self.ovl))), 0
        )


if __name__ == "__main__":
    unittest.main()
