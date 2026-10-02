"""Structural audit of the served public previews, the descriptors and the spine.

As a test (``make test-python`` runs it) each check below is an invariant that
fires: a served preview that drifts from the producer's pinned ``sample_sha256``,
a descriptor file that stops mirroring the manifest, an identifier that loses
its leading zeros, a ``cedar_uid`` that is not in the register or whose name or
class disagrees with it, a spine file whose links do not resolve.

As a report it prints the measurements the fact-check handoff quotes:

    python3 server/tests/test_public_preview_audit.py --report
    python3 server/tests/test_public_preview_audit.py --report --json

It writes nothing. The served CSVs are producer artifacts and are never edited
here; a finding is a measurement for ``docs/FACT_CHECK_*.md`` and a producer
queue item, not a value to recode.
"""

from __future__ import annotations

import contextlib
import csv
import hashlib
import json
import re
import sys
import unittest
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "public" / "data" / "cedar" / "samples"
SPINE = ROOT / "data" / "spine"

TOKENS = re.compile(
    r"^(nan|n/a|na|null|none|tbd|unknown|undisclosed|#n/a|#ref!|lorem|ipsum|-|--|\?)$", re.I
)
LEAK = re.compile(
    r"\b[A-Za-z]:[\\/](?!/)|\\\\|/home/|/Users/|api[_-]?key|synthetic|fixture|placeholder", re.I
)
UID = re.compile(r"^CE-[0-9A-Z]{5}-[0-9A-Z]{2}$")
EIN = re.compile(r"^\d{9}$|^\d{2}-\d{7}$")
UEI = re.compile(r"^[A-HJ-NP-Z0-9]{12}$")
FIPS5 = re.compile(r"^\d{5}$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}(T.*)?$|^\d{4}-\d{2}$")


def read_csv(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    return rows[0], rows[1:]


def audit_collection(path: Path, pinned: dict, manifest_entry: dict | None) -> dict:
    header, rows = read_csv(path)
    out: dict = {"collection": path.parent.name, "rows": len(rows), "columns": len(header)}
    out["ragged_rows"] = [i for i, row in enumerate(rows) if len(row) != len(header)]
    out["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    out["sha256_matches_pinned"] = out["sha256"] == pinned.get("sample_sha256")
    if manifest_entry:
        sample = manifest_entry.get("sample", {})
        out["manifest_rows_match"] = sample.get("rows") == len(rows)
        out["manifest_columns_match"] = sample.get("columns") == len(header)
        out["manifest_of"] = sample.get("of")
    cols = {h: [row[i] if i < len(row) else "" for row in rows] for i, h in enumerate(header)}
    out["all_blank_columns"] = [h for h, v in cols.items() if all(not x.strip() for x in v)]
    out["tokens"] = {
        h: dict(Counter(x for x in v if TOKENS.match(x.strip())))
        for h, v in cols.items()
        if any(TOKENS.match(x.strip()) for x in v)
    }
    out["leak_hits"] = {
        h: [x for x in v if LEAK.search(x) and not x.startswith("http")]
        for h, v in cols.items()
        if any(LEAK.search(x) and not x.startswith("http") for x in v)
    }
    keys = {}
    for h, v in cols.items():
        if re.search(r"(^|_)(id|uid|key|number|ein|uei)$", h, re.I):
            c = Counter(v)
            keys[h] = {
                "distinct": len(c),
                "blank": c.get("", 0),
                "duplicated": {k: n for k, n in c.items() if n > 1 and k},
            }
    out["keys"] = keys
    formats = {}
    for h, v in cols.items():
        filled = [x for x in v if x.strip()]
        if not filled:
            continue
        if h.endswith("cedar_uid") or h == "cedar_uid":
            formats[h] = {"bad_uid": [x for x in filled if not UID.match(x)]}
        if h.endswith("ein"):
            formats[h] = {"bad_ein": [x for x in filled if not EIN.match(x)]}
        if h.endswith("uei"):
            formats[h] = {"bad_uei": [x for x in filled if not UEI.match(x)]}
        if h.endswith("_fips"):
            formats[h] = {"bad_fips": [x for x in filled if not FIPS5.match(x)]}
        if re.search(r"date|_on$", h) and not h.endswith("_precision"):
            bad = [x for x in filled if not DATE.match(x)]
            if bad:
                formats[h] = {"unparsed_dates": bad}
    out["identifier_formats"] = {h: f for h, f in formats.items() if any(f.values())}
    numbers = {}
    for h, v in cols.items():
        parsed = []
        for x in v:
            with contextlib.suppress(ValueError):
                parsed.append(float(x.replace(",", "")))
        if (
            parsed
            and len(parsed) == sum(1 for x in v if x.strip())
            and re.search(r"usd|amount|percent|ratio|count|_year$|^n_", h)
        ):
            numbers[h] = {
                "min": min(parsed),
                "max": max(parsed),
                "zeros": sum(1 for n in parsed if n == 0),
                "negative": sum(1 for n in parsed if n < 0),
            }
    out["numeric"] = numbers
    hosts = Counter()
    for h, v in cols.items():
        if h.endswith("url") or h.endswith("_urls"):
            for x in v:
                if x.startswith("http"):
                    hosts[urlparse(x).netloc] += 1
    out["source_hosts"] = dict(hosts)
    return out, cols


def spine() -> dict:
    reg = {
        r["cedar_uid"]: r
        for r in csv.DictReader(
            (SPINE / "cedar_identity_register.csv").open(newline="", encoding="utf-8")
        )
    }
    names = {
        r["cedar_uid"]: r
        for r in csv.DictReader(
            (SPINE / "cedar_entity_names.csv").open(newline="", encoding="utf-8")
        )
    }
    types = list(
        csv.DictReader((SPINE / "cedar_entity_types.csv").open(newline="", encoding="utf-8"))
    )
    cw = list(
        csv.DictReader(
            (SPINE / "cedar_retired_neid_crosswalk.csv").open(newline="", encoding="utf-8")
        )
    )
    ein = list(
        csv.DictReader((SPINE / "cedar_nonprofit_ein_links.csv").open(newline="", encoding="utf-8"))
    )
    class_counts = Counter(r["entity_class"] for r in reg.values())
    dup_names = Counter(r["canonical_name"] for r in reg.values())
    return (
        {
            "register_rows": len(reg),
            "names_rows": len(names),
            "bad_uid_format": [u for u in reg if not UID.match(u)],
            "register_status": dict(Counter(r["register_status"] for r in reg.values())),
            "register_without_name_row": sorted(set(reg) - set(names)),
            "name_row_without_register": sorted(set(names) - set(reg)),
            "published_name_differs_from_register_canonical": sum(
                1 for u in reg if u in names and reg[u]["canonical_name"] != names[u]["name"]
            ),
            "class_differs_between_files": [
                u for u in reg if u in names and reg[u]["entity_class"] != names[u]["entity_class"]
            ],
            "duplicate_canonical_names": {
                k: [u for u, r in reg.items() if r["canonical_name"] == k]
                for k, n in dup_names.items()
                if n > 1
            },
            "crosswalk_rows": len(cw),
            "crosswalk_unresolved": [r["retired_neid"] for r in cw if r["cedar_uid"] not in reg],
            "ein_link_rows": len(ein),
            "ein_bad_format": [r["EIN"] for r in ein if not re.match(r"^\d{9}$", r["EIN"])],
            "ein_unresolved": [r["EIN"] for r in ein if r["cedar_uid"] not in reg],
            "ein_duplicated": [k for k, n in Counter(r["EIN"] for r in ein).items() if n > 1],
            "type_row_count_vs_register": {
                t["type_code"]: {
                    "types_file": int(t["row_count"]),
                    "register": class_counts.get(t["type_code"], 0),
                }
                for t in types
                if int(t["row_count"]) != class_counts.get(t["type_code"], 0)
            },
        },
        reg,
        names,
    )


def name_agreement(cols: dict, reg: dict, names: dict) -> dict:
    pairs = []
    n = len(next(iter(cols.values()))) if cols else 0
    for i in range(n):
        if cols.get("cedar_uid", [""] * n)[i]:
            pairs.append(
                (
                    cols["cedar_uid"][i],
                    cols.get("canonical_name", [""] * n)[i],
                    cols.get("entity_class", [""] * n)[i],
                )
            )
        raw = cols.get("cedar_uids", [""] * n)[i]
        if raw and raw != "[]":
            us = json.loads(raw)
            ns = (
                json.loads(cols["canonical_names"][i])
                if cols.get("canonical_names") and cols["canonical_names"][i]
                else [None] * len(us)
            )
            cs = (
                json.loads(cols["entity_classes"][i])
                if cols.get("entity_classes") and cols["entity_classes"][i]
                else [None] * len(us)
            )
            pairs.extend(zip(us, ns, cs, strict=True))
    result = {
        "pairs": len(pairs),
        "uid_not_in_register": [],
        "name_not_published_name": [],
        "class_mismatch": [],
    }
    for u, name, cls in pairs:
        if u not in reg:
            result["uid_not_in_register"].append(u)
            continue
        if name and name != names[u]["name"]:
            result["name_not_published_name"].append((u, name, names[u]["name"]))
        if cls and cls != reg[u]["entity_class"]:
            result["class_mismatch"].append((u, cls, reg[u]["entity_class"]))
    return result


def build_report() -> dict:
    pinned = json.loads(
        (ROOT / "data/cedar/verified-preview-releases.json").read_text(encoding="utf-8")
    )["collections"]
    manifest = {
        c["id"]: c
        for c in json.loads(
            (ROOT / "data/cedar/collections.manifest.json").read_text(encoding="utf-8")
        )["collections"]
    }
    spine_report, reg, names = spine()
    report = {"spine": spine_report, "collections": []}
    for path in sorted(SAMPLES.glob("*/spreadsheet__10.csv")):
        entry, cols = audit_collection(
            path, pinned.get(path.parent.name, {}), manifest.get(path.parent.name)
        )
        entry["entity_agreement"] = name_agreement(cols, reg, names)
        report["collections"].append(entry)
    report["manifest_collections_without_served_sample"] = sorted(
        set(manifest) - {e["collection"] for e in report["collections"]}
    )
    return report


def print_report(report: dict, as_json: bool) -> None:
    if as_json:
        json.dump(report, sys.stdout, indent=1, default=str)
        return
    s = report["spine"]
    print(
        f"spine: register {s['register_rows']} rows, names {s['names_rows']}, "
        f"bad uid {len(s['bad_uid_format'])}, published name differs from canonical handle "
        f"on {s['published_name_differs_from_register_canonical']}, "
        f"duplicate canonical names {s['duplicate_canonical_names']}, "
        f"crosswalk {s['crosswalk_rows']} ({len(s['crosswalk_unresolved'])} unresolved), "
        f"EIN links {s['ein_link_rows']} ({len(s['ein_bad_format'])} bad format, "
        f"{len(s['ein_unresolved'])} unresolved), class counts differing from the types file: "
        f"{s['type_row_count_vs_register']}"
    )
    for e in report["collections"]:
        print(
            f"\n{e['collection']}: {e['rows']} rows x {e['columns']} cols; "
            f"pinned sha match={e['sha256_matches_pinned']}; manifest rows/cols match="
            f"{e.get('manifest_rows_match')}/{e.get('manifest_columns_match')}; "
            f"of={e.get('manifest_of')}; ragged={e['ragged_rows']}"
        )
        print(f"  all-blank columns ({len(e['all_blank_columns'])}): {e['all_blank_columns']}")
        print(f"  tokens: {e['tokens']}")
        print(f"  identifier/date format problems: {e['identifier_formats']}")
        print(f"  leak hits: {e['leak_hits']}")
        print(f"  numeric: {e['numeric']}")
        print(f"  source hosts: {e['source_hosts']}")
        a = e["entity_agreement"]
        print(
            f"  entity pairs {a['pairs']}: uid not in register {a['uid_not_in_register']}; "
            f"name differs {len(a['name_not_published_name'])}; "
            f"class differs {len(a['class_mismatch'])}"
        )
        for h, k in e["keys"].items():
            if k["blank"] or k["duplicated"]:
                print(
                    f"  key {h}: distinct {k['distinct']}, blank {k['blank']}, "
                    f"duplicated {k['duplicated']}"
                )
    if report["manifest_collections_without_served_sample"]:
        print(
            "\nmanifest collections without a served sample:",
            report["manifest_collections_without_served_sample"],
        )


class PublicPreviewAuditTest(unittest.TestCase):
    """The invariants the 2026-10-02 fact-check measured, kept firing."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.report = build_report()
        cls.by_id = {e["collection"]: e for e in cls.report["collections"]}
        cls.manifest = json.loads(
            (ROOT / "data/cedar/collections.manifest.json").read_text(encoding="utf-8")
        )

    def test_every_manifest_collection_has_a_served_preview(self) -> None:
        self.assertEqual(self.report["manifest_collections_without_served_sample"], [])
        self.assertEqual(len(self.by_id), 14)

    def test_served_previews_are_the_producers_pinned_bytes(self) -> None:
        for e in self.report["collections"]:
            with self.subTest(collection=e["collection"]):
                self.assertTrue(
                    e["sha256_matches_pinned"],
                    "served preview drifted from verified-preview-releases.json",
                )
                self.assertTrue(
                    e["manifest_rows_match"] and e["manifest_columns_match"],
                    "manifest sample shape disagrees with the file",
                )
                self.assertEqual(e["ragged_rows"], [])

    def test_record_key_is_present_and_distinct_on_every_row(self) -> None:
        for e in self.report["collections"]:
            with self.subTest(collection=e["collection"]):
                key = e["keys"]["record_key"]
                self.assertEqual(key["blank"], 0)
                self.assertEqual(key["duplicated"], {})
                self.assertEqual(key["distinct"], e["rows"])

    def test_identifier_formats_and_dates_hold(self) -> None:
        for e in self.report["collections"]:
            with self.subTest(collection=e["collection"]):
                self.assertEqual(
                    e["identifier_formats"],
                    {},
                    "an identifier lost its format or a date did not parse",
                )

    def test_no_private_path_or_key_in_a_served_cell(self) -> None:
        # The one tolerated hit is the word "placeholder" inside a research note
        # that explains a date convention; a path or a key is never tolerated.
        for e in self.report["collections"]:
            for column, hits in e["leak_hits"].items():
                for hit in hits:
                    with self.subTest(collection=e["collection"], column=column):
                        self.assertNotRegex(
                            hit, r"\b[A-Za-z]:[\\/](?!/)|/home/|/Users/|api[_-]?key", hit[:120]
                        )

    def test_entity_links_resolve_to_the_register_with_the_published_name_and_class(self) -> None:
        for e in self.report["collections"]:
            a = e["entity_agreement"]
            with self.subTest(collection=e["collection"]):
                self.assertEqual(a["uid_not_in_register"], [])
                self.assertEqual(a["name_not_published_name"], [])
                self.assertEqual(a["class_mismatch"], [])

    def test_spine_files_are_internally_consistent(self) -> None:
        s = self.report["spine"]
        self.assertEqual(s["bad_uid_format"], [])
        self.assertEqual(s["register_without_name_row"], [])
        self.assertEqual(s["name_row_without_register"], [])
        self.assertEqual(s["class_differs_between_files"], [])
        self.assertEqual(s["crosswalk_unresolved"], [])
        self.assertEqual(s["ein_bad_format"], [])
        self.assertEqual(s["ein_unresolved"], [])
        self.assertEqual(s["ein_duplicated"], [])

    def test_collection_descriptors_mirror_the_manifest(self) -> None:
        # The descriptors file was a 2026-09-02 copy with the pre-rename lobbying
        # name and superseded row labels until 2026-10-02; this keeps it honest.
        descriptors = json.loads(
            (ROOT / "data/cedar/collection_descriptors.json").read_text(encoding="utf-8")
        )
        self.assertEqual(descriptors, [c["descriptor"] for c in self.manifest["collections"]])

    def test_deals_method_describes_the_served_rows(self) -> None:
        deals = next(c for c in self.manifest["collections"] if c["id"] == "deals")
        method = deals["descriptor"]["method"]
        self.assertIn("excerpted from the verified producer spreadsheet", method)
        self.assertNotIn("contains ten selected events checked against primary sources", method)
        with (ROOT / "public/data/cedar/samples/deals/spreadsheet__10.csv").open(
            newline="", encoding="utf-8"
        ) as handle:
            rows = list(csv.DictReader(handle))
        self.assertTrue(
            all(row["deal_type"] == "Acquisition" for row in rows),
            "the method prose names only acquisitions",
        )
        self.assertEqual(
            Counter(row["entity_class"] for row in rows),
            Counter({"Federally recognized tribe": 6, "Alaska Native Regional Corporation": 4}),
        )


if __name__ == "__main__":
    if "--report" in sys.argv:
        print_report(build_report(), "--json" in sys.argv)
    else:
        unittest.main()
