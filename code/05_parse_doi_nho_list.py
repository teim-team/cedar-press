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

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
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
    fields = ["nho_id", "organization_name", "doi_list_page", "verification_8a",
              "uei", "cage_code", "is_federal_contractor", "confidence_tier",
              "list_type", "source", "source_url", "fetched_date"]
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
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
