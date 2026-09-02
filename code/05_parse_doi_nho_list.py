#!/usr/bin/env python3
"""
Cedar Press - 05: Parse the DOI Office of Native Hawaiian Relations
NHO Notification List into a structured roster.

IMPORTANT SCOPE NOTE (Elijah, 2026-08-05): this is a NOTIFICATION list under
NHPA consultation, not a federal-contracting registry. It is deliberately
broad - civic clubs, family 'ohana, land trusts, and homestead associations
sit alongside genuine federal contractors. It is a STARTING roster only.

The verification that actually counts is 8(a): an entity cannot pursue 8(a)
as an NHO without SBA verifying NHO status first, so an 8(a) certification is
a single authoritative verification. This script therefore emits the roster
with a blank verification column, to be joined against 8(a) evidence in 06.

Output
------
data/clean/nho_doi_notification_roster.csv
"""

import csv
import re
from datetime import date
from pathlib import Path

import pdfplumber

CEDAR = Path(__file__).resolve().parent.parent
PDF = CEDAR / "data" / "raw" / "external" / "doi_nho_complete_list_2025-04.pdf"
OUT = CEDAR / "data" / "clean" / "nho_doi_notification_roster.csv"
TODAY = date.today().isoformat()

SOURCE_URL = ("https://www.doi.gov/sites/default/files/documents/2025-04/"
              "nhol-complete-list-final-web.pdf")

# Table-of-contents line:  Name ......... 12
TOC_RE = re.compile(r"^(?P<name>.+?)\s*\.{3,}\s*(?P<page>\d+)\s*$")

SKIP = {
    "contents (alphabetical order)",
    "u.s. department of the interior",
    "office of native hawaiian relations",
    "native hawaiian organization (nho) notification list",
}


# --- REGENERATE GUARD (ADR-017, 2026-09-02) --------------------------------
def _carry_live_columns(path, canonical):
    """Derive this writer's header instead of declaring it.

    A wholesale writer holding a FIXED `fieldnames` list deletes every column
    an in-place enricher added since - no error, no exception, a diff nobody
    reads. Canonical order first so column order stays stable, then whatever
    the live file already carries. A retired column stays retired because it
    is not on disk; a promoted column survives because it is.

    THIS BUILD CANNOT REPOPULATE AN ENRICHER'S COLUMN. Carried columns are
    written BLANK and NAMED on stdout, which is strictly better than deleted:
    the schema survives and the enricher can refill them. Re-run the enricher
    after this build - `cedar_pipeline.enrichers_to_rerun(<table>)` names it.
    """
    import csv as _csv
    import os as _os
    canonical = list(canonical)
    _p = str(path)
    if not _os.path.exists(_p):
        return canonical
    with open(_p, encoding="utf-8-sig", newline="", errors="replace") as _fh:
        _live = next(_csv.reader(_fh), [])
    _extra = [c for c in _live if c and c not in canonical]
    if _extra:
        print("  [regenerate guard] %s: carrying %d enricher column(s) through "
              "this rebuild, BLANK - re-run the enricher: %s"
              % (_os.path.basename(_p), len(_extra), ", ".join(_extra)))
    return canonical + _extra


def main():
    if not PDF.exists():
        raise SystemExit(f"missing: {PDF}")

    names, seen = [], set()
    with pdfplumber.open(PDF) as pdf:
        npages = len(pdf.pages)
        # The ToC runs until the body starts; scan generously, the regex is strict.
        for pageno, page in enumerate(pdf.pages[:40], 1):
            text = page.extract_text() or ""
            for raw in text.split("\n"):
                line = raw.strip()
                if not line or line.lower() in SKIP:
                    continue
                m = TOC_RE.match(line)
                if not m:
                    continue
                name = m.group("name").strip(" .\u2026")
                # Kill running heads and page furniture.
                if len(name) < 3 or name.lower().startswith("contents"):
                    continue
                if name.lower() in seen:
                    continue
                seen.add(name.lower())
                names.append({
                    "nho_id": "",
                    "organization_name": name,
                    "doi_list_page": m.group("page"),
                    "source": "DOI Office of Native Hawaiian Relations, "
                              "NHO Notification List (updated 2025-04-02)",
                    "source_url": SOURCE_URL,
                    "list_type": "NHPA consultation notification list "
                                 "(broad; NOT a contracting registry)",
                    "verification_8a": "",       # filled by script 06
                    "uei": "",
                    "cage_code": "",
                    "is_federal_contractor": "",
                    "confidence_tier": "C",      # roster-only until 8(a) verified
                    "fetched_date": TODAY,
                })

    names.sort(key=lambda r: r["organization_name"].lower())
    for i, r in enumerate(names, 1):
        r["nho_id"] = f"NHO-DOI-{i:04d}"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    NHO_CANONICAL = ["nho_id", "organization_name", "doi_list_page",
                     "verification_8a", "uei", "cage_code",
                     "is_federal_contractor", "confidence_tier",
                     "list_type", "source", "source_url", "fetched_date"]
    fields = _carry_live_columns(OUT, NHO_CANONICAL)
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, restval="")
        w.writeheader()
        w.writerows(names)

    print(f"PDF pages            : {npages}")
    print(f"organizations parsed : {len(names):,}")
    print(f"wrote {OUT.relative_to(CEDAR)}")
    print("\nAll rows land at tier C: roster presence alone is NOT verification.")
    print("Script 06 promotes only those with 8(a) evidence.\n")
    print("--- first 15 ---")
    for r in names[:15]:
        print(f"  {r['nho_id']}  {r['organization_name']}")


if __name__ == "__main__":
    main()
