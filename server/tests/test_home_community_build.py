"""1190's committed home-community stats re-measure from Git, and its checks fire.

The rules are Lumecon-data's (``lumecon_data.home_community``); 1190 only
gathers Cedar's inputs. Skipped where that producer module is not installed.
"""

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "code" / "1190_build_home_community.py"


def _load():
    spec = importlib.util.spec_from_file_location("build_home_community_1190", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HomeCommunityBuild(unittest.TestCase):
    def setUp(self):
        if importlib.util.find_spec("lumecon_data") is None or (
            importlib.util.find_spec("lumecon_data.home_community") is None
        ):
            self.skipTest("lumecon_data.home_community is not installed in this job")
        self.build = _load()

    def test_stats_are_current(self):
        self.assertEqual(self.build.verify(), 0)

    def test_checks_fire(self):
        self.assertEqual(self.build.selftest(), 0)

    def test_twelve_regional_corporations_bound_to_census_anrc_areas(self):
        from lumecon_data import home_community as hc

        geoids = {geoid for _name, geoid in self.build.ANRC_REGIONAL_CORPORATIONS.values()}
        self.assertEqual(geoids, set(hc.ANRC_AREAS))


if __name__ == "__main__":
    unittest.main()
