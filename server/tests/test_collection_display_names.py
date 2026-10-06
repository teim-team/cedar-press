"""The owned collection's display name is "Individual Native-Owned Businesses".

Owner decision, 2026-10-02: never "Native-Owned Businesses" standing alone,
because that name makes NEED sound redundant, and not the interim wording
"Individually Owned Native Businesses" either. Collection id ``owned``, uids and pinned
samples are unchanged. This holds every served artifact, descriptor, guide,
SEO string and catalog label to the new name; dated logs and the release
ledger's earlier versions keep the name those releases shipped with.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NEW = "Individual Native-Owned Businesses"
#: The retired name standing alone (not as the tail of the new one), and the interim wording.
FORBIDDEN = re.compile(
    r"(?<!Individual )Native-Owned Businesses|Individually Owned Native Businesses"
)
TEXT = {".json", ".md", ".html", ".xml", ".js", ".jsx", ".py", ".csv", ".txt", ".css"}

#: Reader-facing and served surfaces. The release ledger is checked on its own.
SURFACES = (
    "public",
    "data/cedar",
    "docs/guides",
    "docs/datasets/_descriptors.json",
    "index.html",
    "README.md",
    "server/cedar_press",
    "src",
    "tests",
    "server/tests/fixtures",
)


def files(prefix: str):
    path = ROOT / prefix
    if path.is_file():
        yield path
        return
    for p in sorted(path.rglob("*")):
        if (
            p.is_file()
            and p.suffix.lower() in TEXT
            and "__pycache__" not in p.parts
            and p.name != "releases.json"
        ):
            yield p


class OwnedDisplayName(unittest.TestCase):
    def test_no_served_surface_carries_the_retired_name(self) -> None:
        hits = []
        for prefix in SURFACES:
            for p in files(prefix):
                text = p.read_text(encoding="utf-8", errors="replace")
                for match in FORBIDDEN.finditer(text):
                    hits.append(f"{p.relative_to(ROOT)}: {match.group(0)}")
        self.assertEqual(hits, [], hits)

    def test_manifest_descriptors_catalog_and_dump_agree(self) -> None:
        manifest = json.loads(
            (ROOT / "data/cedar/collections.manifest.json").read_text(encoding="utf-8")
        )
        owned = next(c for c in manifest["collections"] if c["id"] == "owned")
        self.assertEqual(owned["descriptor"]["name"], NEW)
        descriptors = json.loads(
            (ROOT / "data/cedar/collection_descriptors.json").read_text(encoding="utf-8")
        )
        self.assertEqual(next(d for d in descriptors if d["id"] == "owned")["name"], NEW)
        docs_desc = json.loads(
            (ROOT / "docs/datasets/_descriptors.json").read_text(encoding="utf-8")
        )
        self.assertEqual(docs_desc["native-owned-businesses"]["name"], NEW)
        dump = (ROOT / "server/cedar_press/_press_data.json").read_text(encoding="utf-8")
        self.assertIn(f'"name": "{NEW}"', dump)
        catalog = (ROOT / "src/features/grove/pressCatalog.js").read_text(encoding="utf-8")
        self.assertIn(f'name: "{NEW}"', catalog)
        self.assertIn('short: "Individual Native-Owned",', catalog)
        codebook = json.loads((ROOT / "data/cedar/codebook.json").read_text(encoding="utf-8"))
        self.assertEqual(
            {t["dataset"] for k, t in codebook["tables"].items() if k.startswith("owned/")}, {NEW}
        )

    def test_forbidden_rule_distinguishes_the_tail_of_the_new_name(self) -> None:
        self.assertIsNone(FORBIDDEN.search(NEW))
        self.assertIsNotNone(FORBIDDEN.search("Native-Owned Businesses"))
        self.assertIsNotNone(FORBIDDEN.search("the Native-Owned Businesses collection"))
        self.assertIsNotNone(FORBIDDEN.search("Individually Owned Native Businesses"))

    def test_release_ledger_keeps_history_and_records_the_rename_as_a_version(self) -> None:
        manifest = json.loads(
            (ROOT / "data/cedar/collections.manifest.json").read_text(encoding="utf-8")
        )
        owned = next(c for c in manifest["collections"] if c["id"] == "owned")
        ledger = json.loads((ROOT / "data/cedar/releases.json").read_text(encoding="utf-8"))[
            "releases"
        ]["owned"]
        current = next(r for r in ledger if r["version"] == owned["descriptor"]["version"])
        self.assertEqual(current["name"], NEW)
        self.assertEqual(current["date"], owned["descriptor"]["updated"])
        # Releases before the rename (v4) shipped under their own name; v4 and
        # every later release carry the new one.
        for row in ledger:
            renamed = int(row["version"].lstrip("v")) >= 4
            self.assertEqual(
                row["name"], NEW if renamed else "Native-Owned Businesses", row
            )
        # The rename changed no served bytes: the pinned sample and receipt are untouched.
        receipts = json.loads(
            (ROOT / "data/cedar/verified-preview-releases.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            owned["sample"]["release_id"], receipts["collections"]["owned"]["release_id"]
        )

    def test_guide_and_seo_carry_the_new_name(self) -> None:
        guide = (ROOT / "docs/guides/owned.md").read_text(encoding="utf-8")
        self.assertTrue(guide.startswith(f"# {NEW}"))
        self.assertIn(f'Lumecon, "{NEW}", Cedar Press collection', guide)
        head = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn(NEW, head)


if __name__ == "__main__":
    unittest.main()
