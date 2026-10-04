"""D-U-N-S never ships, in any dataset, at any tier.

docs/PUBLICATION_POLICY.md (2026-09-02): "Casino City and D-U-N-S are licensed
to Cedar for internal use and never ship, in any dataset, at any tier."
docs/PUBLIC_DATASET_SPEC_2026-09-05.md: DUNS is used internally to reconcile
historical records and is not published. The owner reaffirmed it on
2026-10-04, keeping coverage statistics such as ``pct_with_duns``, which name
no identifier.

The substring rule (895854c) was reverted with the publication holds in
341f950; it is a licensing and identifier rule, not a hold, and is restored.
These tests hold it two ways: the rule itself on planted rows, and every
committed data file under ``dist/``, ``public/data/`` and
``data/cedar/samples/`` (plus ``dist-site/`` when built). The contact-data
rules of 895854c are restored separately and tested beside them.
"""

from __future__ import annotations

import csv
import importlib.util
import io
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CODE = ROOT / "code"
sys.path.insert(0, str(CODE))


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pub = _load("cedar_publication_duns", CODE / "cedar_publication.py")
importer = _load("import_cedar_manifest_duns", ROOT / "scripts" / "import_cedar_manifest.py")
csv.field_size_limit(10_000_000)

DATA_ROOTS = ("dist", "public/data", "data/cedar/samples")
SITE_DATA = ROOT / "dist-site" / "data"


def _data_files() -> list[Path]:
    out = subprocess.run(  # noqa: S603
        ["git", "-C", str(ROOT), "ls-files", "-z", "--", *DATA_ROOTS],  # noqa: S607
        capture_output=True,
        check=True,
    ).stdout.decode("utf-8")
    files = [ROOT / p for p in out.split("\0") if p.endswith(".csv") and (ROOT / p).exists()]
    if SITE_DATA.is_dir():
        files += sorted(SITE_DATA.rglob("*.csv"))
    return files


class DunsRule(unittest.TestCase):
    def test_any_duns_spelling_is_proprietary(self) -> None:
        for name in (
            "duns",
            "recipient_duns",
            "Recipient_DUNS",
            "duns_internal_only",
            "awardee_parent_duns_number",
        ):
            self.assertTrue(pub.is_proprietary_column(name), name)

    def test_a_coverage_statistic_is_not_an_identifier(self) -> None:
        for name in ("pct_with_duns", "pct_with_duns_tribal_rows_only", "n_duns"):
            self.assertFalse(pub.is_proprietary_column(name), name)
        self.assertIn("pct_with_duns", pub.publishable_columns(["pct_with_duns", "uei"]))
        self.assertNotIn("recipient_duns", pub.publishable_columns(["recipient_duns", "uei"]))

    def test_a_duns_as_the_rows_subject_withholds_the_row(self) -> None:
        self.assertEqual(
            pub.row_ok({"identifier_type": "DUNS", "identifier": "x"}),
            (False, "proprietary:duns"),
        )
        self.assertEqual(pub.row_ok({"node": "DUNS:000000000"}), (False, "proprietary:duns"))
        self.assertEqual(pub.row_ok({"note": "no DUNS/UEI exists on the row"}), (True, ""))

    def test_the_importer_drops_the_column_and_the_row_from_a_served_copy(self) -> None:
        raw = "a,recipient_duns,pct_with_duns,b\n1,000000000,0.4,2\nDUNS:123456789,x,0.1,3\n"
        text, dropped, withheld = importer.drop_proprietary(raw)
        self.assertEqual(dropped, ["recipient_duns"])
        self.assertEqual(withheld, 1)
        self.assertEqual(text, "a,pct_with_duns,b\n1,0.4,2\n")
        self.assertEqual(importer.clean_sample_text(raw), text)


class CommittedDataCarriesNoDuns(unittest.TestCase):
    def test_no_duns_column_or_duns_subject_in_any_committed_or_built_file(self) -> None:
        hits = []
        for path in _data_files():
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            reader = csv.DictReader(io.StringIO(text, newline=""))
            rows = list(reader)
            bad = [c for c in reader.fieldnames or [] if pub.is_proprietary_column(c)]
            if bad:
                hits.append(f"{path.relative_to(ROOT)}: {bad}")
            if any(
                pub.row_ok({k: v for k, v in r.items() if k})[1] == "proprietary:duns" for r in rows
            ):
                hits.append(f"{path.relative_to(ROOT)}: a row whose subject is a DUNS")
        self.assertEqual(hits, [], "run `python3 scripts/import_cedar_manifest.py --audit`")


if __name__ == "__main__":
    unittest.main()
