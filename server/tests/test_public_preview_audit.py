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
import unicodedata
import unittest
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "data" / "cedar" / "samples"
SPINE = ROOT / "data" / "spine"
# Source renderings of a register name (diacritics, case, spacing) live here,
# never in the published-names file: the register's spelling is canonical and
# the source's spelling is an alias with its source. Same contract as
# Lumecon-data's `lumecon-data spine check` (src/lumecon_data/spine.py).
ALIASES = SPINE / "cedar_entity_name_aliases.csv"
ALIAS_KINDS = {"source_rendering"}
# A canonical name shared by two uids is an identity question for the owner.
# It is a review item only when this file names exactly those uids with a
# reason; otherwise it is a failure. Nothing here decides which uid the name
# belongs to, and no uid is merged, renamed or re-minted.
DUPLICATE_NAME_REVIEW = SPINE / "cedar_duplicate_name_review.json"


def fold_name(value: str) -> str:
    """Rendering-insensitive form of a name: diacritics, case and spacing removed."""
    stripped = "".join(
        ch for ch in unicodedata.normalize("NFKD", value) if not unicodedata.combining(ch)
    )
    return " ".join(stripped.casefold().split())


def duplicate_name_review() -> list[dict]:
    """Reviewed duplicate-name entries; each needs the exact uids and a reason."""
    if not DUPLICATE_NAME_REVIEW.exists():
        return []
    document = json.loads(DUPLICATE_NAME_REVIEW.read_text(encoding="utf-8"))
    entries = document.get("entries") if isinstance(document, dict) else None
    if not isinstance(entries, list):
        raise ValueError("duplicate-name review must be an object with an entries list")
    for entry in entries:
        uids = entry.get("cedar_uids") if isinstance(entry, dict) else None
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("canonical_name"), str)
            or not isinstance(uids, list)
            or len(uids) < 2
            or len(set(uids)) != len(uids)
            or any(not isinstance(u, str) or not UID.match(u) for u in uids)
            or not isinstance(entry.get("reason"), str)
            or not entry["reason"].strip()
        ):
            raise ValueError("review entry needs canonical_name, two or more uids and a reason")
    return entries

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
    aliases = (
        list(csv.DictReader(ALIASES.open(newline="", encoding="utf-8")))
        if ALIASES.exists()
        else []
    )
    class_counts = Counter(r["entity_class"] for r in reg.values())
    dup_names = Counter(r["canonical_name"] for r in reg.values())
    duplicates = {
        k: sorted(u for u, r in reg.items() if r["canonical_name"] == k)
        for k, n in dup_names.items()
        if n > 1
    }
    review = duplicate_name_review()
    reviewed = {
        (e["canonical_name"], tuple(sorted(e["cedar_uids"]))): e["reason"] for e in review
    }
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
            # A published name that is the register's name in another rendering
            # is a source spelling, not a different name: it belongs in the
            # aliases file with the register's spelling published.
            "published_name_is_rendering_variant_of_register": [
                (u, names[u]["name"], reg[u]["canonical_name"])
                for u in reg
                if u in names
                and reg[u]["canonical_name"] != names[u]["name"]
                and fold_name(reg[u]["canonical_name"]) == fold_name(names[u]["name"])
            ],
            "class_differs_between_files": [
                u for u in reg if u in names and reg[u]["entity_class"] != names[u]["entity_class"]
            ],
            "duplicate_canonical_names": duplicates,
            "duplicate_canonical_names_reviewed": {
                k: reviewed[(k, tuple(v))]
                for k, v in duplicates.items()
                if (k, tuple(v)) in reviewed
            },
            "duplicate_canonical_names_unreviewed": {
                k: v for k, v in duplicates.items() if (k, tuple(v)) not in reviewed
            },
            "duplicate_name_review_stale": [
                e["canonical_name"]
                for e in review
                if (e["canonical_name"], tuple(sorted(e["cedar_uids"])))
                not in {(k, tuple(v)) for k, v in duplicates.items()}
            ],
            "alias_rows": len(aliases),
            "alias_unresolved": [a["cedar_uid"] for a in aliases if a["cedar_uid"] not in reg],
            "alias_kind_unknown": [
                a["alias"] for a in aliases if a["alias_kind"] not in ALIAS_KINDS
            ],
            # An alias is a rendering of the register's name for its uid; one
            # that equals the published name is not an alias, and one that is
            # not a rendering of the register name is a different name.
            "alias_not_a_rendering_of_register_name": [
                (a["cedar_uid"], a["alias"])
                for a in aliases
                if a["cedar_uid"] in reg
                and (
                    a["alias"] == names.get(a["cedar_uid"], {}).get("name")
                    or a["register_canonical_name"] != reg[a["cedar_uid"]]["canonical_name"]
                    or fold_name(a["alias"]) != fold_name(reg[a["cedar_uid"]]["canonical_name"])
                )
            ],
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
        {(a["cedar_uid"], a["alias"]) for a in aliases},
    )


def name_agreement(cols: dict, reg: dict, names: dict, aliases: set | None = None) -> dict:
    aliases = aliases or set()
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
        # A served name that is a recorded source rendering of the register
        # name (the producer pinned the sample before the register's spelling
        # was published) resolves through the aliases file, not by editing
        # the sample.
        "name_is_recorded_alias": [],
        "class_mismatch": [],
    }
    for u, name, cls in pairs:
        if u not in reg:
            result["uid_not_in_register"].append(u)
            continue
        if name and name != names[u]["name"]:
            if (u, name) in aliases:
                result["name_is_recorded_alias"].append((u, name, names[u]["name"]))
            else:
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
    spine_report, reg, names, aliases = spine()
    report = {"spine": spine_report, "collections": []}
    for path in sorted(SAMPLES.glob("*/spreadsheet__10.csv")):
        entry, cols = audit_collection(
            path, pinned.get(path.parent.name, {}), manifest.get(path.parent.name)
        )
        entry["entity_agreement"] = name_agreement(cols, reg, names, aliases)
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
        f"duplicate canonical names {s['duplicate_canonical_names']} "
        f"(reviewed {sorted(s['duplicate_canonical_names_reviewed'])}, unreviewed "
        f"{sorted(s['duplicate_canonical_names_unreviewed'])}), rendering variants "
        f"{s['published_name_is_rendering_variant_of_register']}, aliases {s['alias_rows']}, "
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
            f"name is a recorded alias {len(a['name_is_recorded_alias'])}; "
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
        # The types file's row_count is the register's count per class, so
        # it is derived from the register, never edited by hand (it read 359
        # Native nonprofits against 361 in the register until 2026-10-02).
        self.assertEqual(s["type_row_count_vs_register"], {})
        # The register's spelling is canonical; a source rendering of the same
        # name is published as an alias with its source, never over it
        # (Ukpeagvik for Ukpeaġvik, Shee Atiká for Shee Atika, until 2026-10-02).
        self.assertEqual(s["published_name_is_rendering_variant_of_register"], [])
        self.assertEqual(s["alias_unresolved"], [])
        self.assertEqual(s["alias_kind_unknown"], [])
        self.assertEqual(s["alias_not_a_rendering_of_register_name"], [])
        # A canonical name shared by two uids is an identity question, never a
        # merge or a rename by name: it must be recorded with a reason in
        # data/spine/cedar_duplicate_name_review.json (which uid the name
        # belongs to is the owner's call), and an entry whose pair no longer
        # exists in the register is stale and must be removed.
        self.assertEqual(s["duplicate_canonical_names_unreviewed"], {})
        self.assertEqual(s["duplicate_name_review_stale"], [])
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

    def test_preview_definitions_state_the_blank_convention_for_unevaluated_scope(self) -> None:
        # The spreadsheet's missing convention is a blank cell. The producer
        # writes blank for an unevaluated collective scope since
        # fr-participant-observations-v2 and legislation-projection-v3
        # (Lumecon-data d780401); a definition that still calls the
        # unevaluated value "null" describes the text token the v1/v2
        # transforms wrote, which a pinned sample built before them may still
        # show and the guide then reports as a producer finding, not a value.
        codebook = json.loads((ROOT / "data/cedar/codebook.json").read_text(encoding="utf-8"))
        for collection in ("federal-register", "legislation"):
            table = codebook["tables"][f"{collection}/{collection}"]
            field = next(f for f in table["fields"] if f["column"] == "collective_scopes")
            with self.subTest(collection=collection):
                self.assertIn("blank", field["meaning"].lower())
                self.assertNotRegex(
                    field["meaning"],
                    r"JSON null|null when not evaluated|scope is null|always null",
                )

    def test_owned_ownership_percent_definition_states_whose_share_it_is(self) -> None:
        # Cashwork Atm (certification 1482) reads ownership_percent 0.0 on a
        # Native-owned registry row because Tulalip's registry prints the
        # Tulalip-member share and certifies firms Native-owned through other
        # tribes (identity_claim_text "Tribe: Snoqualmie; Tulalip Owned: 0%").
        # The value is the source's; the definition must say the column is the
        # certifying tribe's stated share, or a reader takes it as the Native
        # ownership share and the zero as a false zero.
        codebook = json.loads((ROOT / "data/cedar/codebook.json").read_text(encoding="utf-8"))
        fields = codebook["tables"]["owned/owned"]["fields"]
        field = next(f for f in fields if f["column"] == "ownership_percent")
        meaning = field["meaning"].lower()
        self.assertIn("certifying tribe", meaning)
        self.assertIn("not the native ownership share overall", meaning)
        self.assertIn("not zero", meaning)

    def test_deals_method_describes_the_served_rows(self) -> None:
        deals = next(c for c in self.manifest["collections"] if c["id"] == "deals")
        method = deals["descriptor"]["method"]
        # The method describes the release, not the ten-row sample, so it
        # names no sample composition for the sample file to contradict.
        self.assertIn(
            "This release includes deals verified by hand against their primary source.", method
        )
        self.assertNotIn("preview", method.lower())
        self.assertNotIn("contains ten selected events checked against primary sources", method)


if __name__ == "__main__":
    if "--report" in sys.argv:
        print_report(build_report(), "--json" in sys.argv)
    else:
        unittest.main()
