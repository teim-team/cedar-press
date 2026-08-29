#!/usr/bin/env python3
"""
Cedar Press - 07: Parse the ANCSA corporation list into the ANC ceiling roster.

Per Elijah (2026-08-05): the ANCSA corporations list bounds the ANC universe,
the Federal Register / BIA list bounds the tribe universe (575), and DOI+8(a)
bounds NHOs. Together those three give the CEILING - the maximum number of
parent native entities that can ever exist. Coverage is then measurable as a
fraction of a known denominator instead of an open-ended guess.

Two specifics Elijah flagged:
  * The Thirteenth Regional Corporation (for Alaska Natives living outside
    Alaska) is defunct/bankrupt but DID hold federal contracts historically.
    A current-state roster will omit it; historical contracting data will not.
    It is therefore added explicitly with a status flag rather than lost.
  * Lumbee contracted federally while STATE-recognized, before federal
    recognition. Entity status is time-varying; never backfill current status
    onto historical rows.

Output
------
data/clean/anc_ceiling_roster.csv
"""

import csv
import re
import sys
import unicodedata
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent

# The one place a row identity is minted. See ANC_KEY_COLUMNS below.
sys.path.insert(0, str(CEDAR / "code"))
from cedar_keys import surrogate_id                            # noqa: E402
SRC = CEDAR / "data" / "raw" / "external" / "ancsa_lbblawyers_native_corporations.html"
OUT = CEDAR / "data" / "clean" / "anc_ceiling_roster.csv"
TODAY = date.today().isoformat()
SOURCE_URL = "https://ancsa.lbblawyers.com/native-corporations.htm"

# --------------------------------------------------------------------------
# THE PRIMARY KEY OF anc_ceiling_roster.csv, AND WHAT IT IS MADE OF
#
# `anc_id` used to be `f"ANC-{i:04d}"` over this list after it was sorted by
# (anc_class, lowercased name) - a POSITION, not an identity. Adding one
# corporation renumbered every corporation after it, and 19,269 rows of
# `ancsa_filings_index.csv` plus 40 rows of `deals_party_matches.csv` point at
# these ids. Nothing would have errored.
#
# It is now a deterministic blake2b digest of the two things ANCSA itself
# states about a corporation: its NAME and whether it is a REGIONAL or a
# VILLAGE corporation. Measured 2026-08-26: unique over all 196 rows, 0 blank.
# Same inputs -> same id, in every process, on every machine, forever.
#
# Migrated in the live files by `327_migrate_class7_keys_to_digests.py`; the
# old -> new map is in `docs/schema/class7_key_migration_map.json`.
# --------------------------------------------------------------------------
ANC_KEY_COLUMNS = ["corporation_name", "anc_class"]

REGIONALS = {
    "ahtna", "aleut", "arctic slope", "bering straits", "bristol bay",
    "calista", "chugach", "cook inlet", "doyon", "koniag", "nana",
    "sealaska", "thirteenth",
}

NOISE_LINE = re.compile(
    r"^(home|about|contact|search|menu|native corporations|links?|index|"
    r"copyright|\u00a9.*|all rights reserved.*)$", re.IGNORECASE)

CORP_HINT = re.compile(
    r"\b(corp|corporation|inc|incorporated|company|ltd|limited|"
    r"association|native|village)\b", re.IGNORECASE)


class TextGrab(HTMLParser):
    """Collect visible text lines and link text, in document order."""

    def __init__(self):
        super().__init__()
        self.lines = []
        self._skip = 0
        self._buf = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1
        if tag in ("br", "p", "tr", "td", "li", "div", "h1", "h2", "h3", "a"):
            self._flush()

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1
        if tag in ("p", "tr", "td", "li", "div", "h1", "h2", "h3", "a"):
            self._flush()

    def handle_data(self, data):
        if not self._skip:
            self._buf.append(data)

    def _flush(self):
        txt = " ".join("".join(self._buf).split())
        if txt:
            self.lines.append(txt)
        self._buf = []

    def close(self):
        self._flush()
        super().close()


def clean(s):
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("\u00a0", " ")
    return " ".join(s.split()).strip(" .,;:\u2013\u2014-")


def classify(name):
    low = name.lower()
    if any(r in low for r in REGIONALS) and "village" not in low:
        return "ANC_REGIONAL"
    if "urban" in low:
        return "ANC_URBAN"
    if "group" in low:
        return "ANCSA_GROUP"
    return "ANC_VILLAGE"


def main():
    if not SRC.exists():
        raise SystemExit(f"missing: {SRC}")

    parser = TextGrab()
    parser.feed(SRC.read_text(encoding="utf-8", errors="replace"))
    parser.close()

    seen, rows = set(), []
    for raw in parser.lines:
        name = clean(raw)
        if not name or len(name) < 4 or len(name) > 120:
            continue
        if NOISE_LINE.match(name):
            continue
        if not CORP_HINT.search(name):
            continue
        if name.lower() in seen:
            continue
        seen.add(name.lower())
        rows.append({
            "anc_id": "",
            "corporation_name": name,
            "anc_class": classify(name),
            "status": "active_per_source",
            "uei": "",
            "cage_code": "",
            "parent_entity_class": "ANC",
            "confidence_tier": "C",
            "source": "ANCSA Regional/Village Corporation list (lbblawyers.com)",
            "source_url": SOURCE_URL,
            "note": "",
            "fetched_date": TODAY,
        })

    # The 13th Regional Corporation: defunct but historically a contractor.
    if not any("thirteenth" in r["corporation_name"].lower() for r in rows):
        rows.append({
            "anc_id": "",
            "corporation_name": "The Thirteenth Regional Corporation",
            "anc_class": "ANC_REGIONAL",
            "status": "defunct_historically_contracting",
            "uei": "", "cage_code": "",
            "parent_entity_class": "ANC",
            "confidence_tier": "C",
            "source": "Added per Elijah 2026-08-05; absent from current-state rosters",
            "source_url": SOURCE_URL,
            "note": ("Regional corporation for Alaska Natives residing outside "
                     "Alaska. Bankrupt/defunct, so omitted from current rosters, "
                     "but held federal contracts historically. Required for any "
                     "backward-looking contracting panel."),
            "fetched_date": TODAY,
        })

    rows.sort(key=lambda r: (r["anc_class"] != "ANC_REGIONAL",
                             r["corporation_name"].lower()))
    for r in rows:
        r["anc_id"] = surrogate_id("ANC", r, ANC_KEY_COLUMNS)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fields = ["anc_id", "corporation_name", "anc_class", "status", "uei",
              "cage_code", "parent_entity_class", "confidence_tier", "note",
              "source", "source_url", "fetched_date"]
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    from collections import Counter
    print(f"parsed {len(rows):,} ANC entries -> {OUT.relative_to(CEDAR)}\n")
    for k, v in Counter(r["anc_class"] for r in rows).most_common():
        print(f"  {v:>4}  {k}")
    print("\n--- regionals detected ---")
    for r in rows:
        if r["anc_class"] == "ANC_REGIONAL":
            flag = "  [DEFUNCT]" if r["status"].startswith("defunct") else ""
            print(f"  {r['anc_id']}  {r['corporation_name']}{flag}")
    print("\nAll rows tier C: roster presence bounds the universe, it does not")
    print("attribute a contract. Identifiers get attached in the linking pass.")


if __name__ == "__main__":
    main()
