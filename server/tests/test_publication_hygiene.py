"""What this public repository and the site it builds may never carry.

FOUND 2026-10-04, in a public repository: a FOIA sample with requesters'
personal email addresses and phone numbers inside free text, a source-registry
template holding a real roster row, NEED rows outside the cleared set served
by the site, and ``recipient_duns`` in four funding samples. Each one passed
a gate that matched column NAMES. These tests hold the line two ways:

* the rules themselves, in ``code/cedar_publication.py`` and the importer,
  on planted rows, so a weakened rule fails here before it ships; and
* every committed data file under ``dist/``, ``public/data/`` and
  ``data/cedar/samples/``, plus the site build (``dist-site/``) when it is
  present, scanned for the four leaks.

Run from the repository root by ``make test-python``.
"""
from __future__ import annotations

import csv
import importlib.util
import io
import json
import re
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


pub = _load("cedar_publication_hygiene", CODE / "cedar_publication.py")
importer = _load("import_cedar_manifest_hygiene", ROOT / "scripts" / "import_cedar_manifest.py")

csv.field_size_limit(10_000_000)

#: Where data that reaches a reader is committed. `dist-site/` is the built
#: site; it is not tracked, and is scanned when a build has produced it.
DATA_ROOTS = ("dist", "public/data", "data/cedar/samples")
SITE_DATA = ROOT / "dist-site" / "data"


def _tracked(*roots: str) -> list[Path]:
    out = subprocess.run(  # noqa: S603
        ["git", "-C", str(ROOT), "ls-files", "-z", "--", *roots],
        capture_output=True, check=True,
    ).stdout.decode("utf-8")
    return [ROOT / p for p in out.split("\0") if p and (ROOT / p).exists()]


def _data_files(suffixes: tuple[str, ...]) -> list[Path]:
    files = [p for p in _tracked(*DATA_ROOTS) if p.suffix in suffixes]
    if SITE_DATA.is_dir():
        files += [p for p in sorted(SITE_DATA.rglob("*")) if p.suffix in suffixes]
    return files


def _rows(path: Path) -> tuple[list[str], list[dict]]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text, newline=""))
    rows = list(reader)
    return list(reader.fieldnames or []), rows


def _rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


class ContactRedactionRule(unittest.TestCase):
    """`redact_personal_contacts`: free-text contact data goes, the row stays."""

    def test_email_and_phone_in_free_text_are_redacted(self) -> None:
        row = {
            "request_description": "Please reply to someone.private@webmail.example or "
                                   "call (555) 010-0123; fax 555.010.0199.",
            "agency": "Bureau of Indian Affairs",
        }
        n = pub.redact_personal_contacts(row)
        self.assertEqual(n, 3)
        self.assertNotIn("@", row["request_description"])
        self.assertNotRegex(row["request_description"], r"\d{3}\D\d{4}")
        self.assertIn(pub.EMAIL_REMOVED, row["request_description"])
        self.assertIn(pub.PHONE_REMOVED, row["request_description"])
        self.assertEqual(row["agency"], "Bureau of Indian Affairs")

    def test_identifiers_dates_and_money_are_not_phones(self) -> None:
        for text in ("award 123456789", "FAIN 1234567890", "2017-08-12",
                     "ZIP 74601-1234", "$1,234,567.89", "CFDA 15.022",
                     "MOU 2019-0412-07", "uei ABCDEF123456"):
            with self.subTest(text=text):
                self.assertEqual(pub.redact_contact_text(text), (text, 0))

    def test_every_writer_applies_the_redaction(self) -> None:
        for stem in pub.GATE_CALLERS + ("770_sample_extracts.py",):
            with self.subTest(writer=stem):
                self.assertIn("redact_personal_contacts(",
                              (CODE / stem).read_text(encoding="utf-8"))


class ProprietaryColumnRule(unittest.TestCase):
    """Any column whose name contains `duns` drops, whatever its spelling."""

    def test_any_duns_spelling_is_proprietary(self) -> None:
        for name in ("duns", "recipient_duns", "Recipient_DUNS", "duns_internal_only",
                     "awardee_parent_duns_number"):
            with self.subTest(name=name):
                self.assertTrue(pub.is_proprietary_column(name))
                self.assertNotIn(name, pub.publishable_columns(["fiscal_year", name]))
        self.assertFalse(pub.is_proprietary_column("recipient_uei"))

    def test_a_duns_as_the_rows_subject_withholds_the_row(self) -> None:
        self.assertEqual(pub.row_ok({"identifier_type": "DUNS", "identifier": "x"}),
                         (False, "proprietary:duns"))
        self.assertEqual(pub.row_ok({"node": "DUNS:000000000"}),
                         (False, "proprietary:duns"))
        self.assertEqual(pub.row_ok({"note": "no DUNS/UEI exists on the row"}), (True, ""))

    def test_the_importer_drops_the_column_from_a_served_copy(self) -> None:
        raw = "a,recipient_duns,b\n1,000000000,2\n"
        clean, dropped = importer.clean_sample_text(raw)
        self.assertEqual(dropped, ["recipient_duns"])
        self.assertEqual(clean, "a,b\n1,2\n")


class NeedPublicationHold(unittest.TestCase):
    """Only the cleared NEED enterprise ids may publish."""

    def test_the_cleared_set_is_pinned_and_whole(self) -> None:
        pin = json.loads(pub.NEED_CLEARED_PATH.read_text(encoding="utf-8"))
        ids = pin["enterprise_ids"]
        self.assertEqual(len(ids), pin["record_count"])
        self.assertEqual(len(set(ids)), len(ids))
        self.assertRegex(pin["source_sha256"], r"^[0-9a-f]{64}$")
        for i in ids:
            self.assertRegex(i, pub.NEED_ID.pattern)

    def test_only_cleared_need_rows_publish(self) -> None:
        cleared = sorted(pub.need_cleared_ids())[0]
        self.assertEqual(pub.need_row_cleared({"enterprise_id": cleared}, "need"), (True, ""))
        held = (False, "held:need_publication")
        stray = {"enterprise_id": "CEDAR-NEST-999999-ZZ"}
        self.assertEqual(pub.need_row_cleared(stray, "need"), held)
        # A NEED-collection row with no NEED id (the dual-role table) is held.
        self.assertEqual(pub.need_row_cleared({"cedar_uid": "CE-00000-00"}, "need"), held)
        # And a NEED id in any other table is held too.
        self.assertEqual(pub.need_row_cleared({"counterparty_need_enterprise_id":
                                               "CEDAR-NEST-999999-ZZ"}), held)
        self.assertEqual(pub.is_publication_eligible({"enterprise_id": "CEDAR-NEST-999999-ZZ"},
                                                     "need")[:2], held)


class CommittedDataCarriesNoLeak(unittest.TestCase):
    """Every committed data file, and the site build when present."""

    def test_no_email_or_phone_in_any_committed_or_built_sample(self) -> None:
        hits = []
        for path in _data_files((".csv",)):
            _, rows = _rows(path)
            n = sum(pub.redact_contact_text(v or "")[1]
                    for row in rows for v in row.values() if isinstance(v, str))
            if n:
                hits.append(f"{_rel(path)}: {n} value(s)")
        self.assertEqual(hits, [], "contact data in a published file; run "
                         "`python3 scripts/import_cedar_manifest.py --audit`")

    def test_no_duns_column_in_any_committed_or_built_sample(self) -> None:
        hits = []
        for path in _data_files((".csv",)):
            header, rows = _rows(path)
            bad = [c for c in header if pub.is_proprietary_column(c)]
            if bad:
                hits.append(f"{_rel(path)}: {bad}")
            if any(not pub.row_ok({k: v for k, v in r.items() if k})[0]
                   and pub.row_ok({k: v for k, v in r.items() if k})[1] == "proprietary:duns"
                   for r in rows):
                hits.append(f"{_rel(path)}: a row whose subject is a DUNS")
        self.assertEqual(hits, [])

    def test_no_uncleared_need_row_is_committed_or_built(self) -> None:
        cleared = pub.need_cleared_ids()
        hits = []
        for path in _data_files((".csv", ".json", ".jsonl")):
            if path == pub.NEED_CLEARED_PATH:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            stray = sorted(set(pub.NEED_ID.findall(text)) - cleared)
            if stray:
                hits.append(f"{_rel(path)}: {len(stray)} uncleared NEED id(s)")
            # A file of the NEED collection whose rows carry no id at all
            # (the dual-role table, the 100-row preview) is held whole.
            is_need = (path.parent.name == pub.NEED_COLLECTION
                       or re.match(r"need(__|\.)", path.name))
            if is_need and path.suffix == ".csv":
                _, rows = _rows(path)
                held = sum(not pub.need_row_cleared(r, pub.NEED_COLLECTION)[0] for r in rows)
                if held:
                    hits.append(f"{_rel(path)}: {held} NEED row(s) outside the cleared set")
        self.assertEqual(hits, [])

    def test_the_manifest_serves_no_held_need_sample(self) -> None:
        manifest = json.loads((ROOT / "data" / "cedar" / "collections.manifest.json")
                              .read_text(encoding="utf-8"))
        for collection in manifest["collections"]:
            if collection["cedar"]["cedar_id"] != pub.NEED_COLLECTION:
                continue
            for table in collection["tables"]:
                path = table.get("sample_path")
                if path:
                    served = ROOT / "public" / path.lstrip("/")
                    with self.subTest(table=table["table"]):
                        self.assertTrue(served.exists())
                        _, rows = _rows(served)
                        self.assertTrue(all(pub.need_row_cleared(r, "need")[0] for r in rows))


class SourceRegistryTemplates(unittest.TestCase):
    """The worked examples are synthetic: rosters are never committed."""

    TEMPLATES = ("cedar_source_registry/templates/source_record.example.jsonl",
                 "cedar_source_registry/templates/harmonized_entity.example.json")

    def test_template_contacts_are_reserved_example_values(self) -> None:
        for rel in self.TEMPLATES:
            text = (ROOT / rel).read_text(encoding="utf-8")
            with self.subTest(template=rel):
                for email in pub.CONTACT_EMAIL.findall(text):
                    self.assertTrue(email.endswith("@example.com"), "non-example email")
                for phone in pub.CONTACT_PHONE.findall(text):
                    self.assertIn("555", phone, "phone outside the fictional 555 range")
                self.assertIn("SYNTHETIC", text)


if __name__ == "__main__":
    unittest.main()
