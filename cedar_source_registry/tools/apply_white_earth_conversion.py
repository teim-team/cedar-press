#!/usr/bin/env python3
"""
Apply the TBD-113 (White Earth Nation TERO) conversion to the registry.

The roster was obtained 2026-08-28 as an owner-supplied download, so this source
moves out of Lead. It does NOT become a scrapeable Live source: the roster is
not published at a URL Cedar can poll, so acquisition stays Partnership/request
and the cadence is a repeat ask, not a crawl.

Edits, all in place, all reversible from the .bak written alongside:
  sources.jsonl          TBD-113 -> status_group Obtained, Tribal Primary
  partnership_leads.jsonl TBD-113 -> marked converted (row kept, never deleted)
  verification_log.jsonl  append one entry

Run from cedar_source_registry/.  Pass --write to persist.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_ID = "TBD-113"
TODAY = "2026-08-28"
BAK = f".bak_{TODAY}_pre_white_earth_conversion"

RECORDS_REL = "source_records/TBD-113_white_earth.jsonl"
SNAP_REL = "research/white_earth_2026-08-28/"


def load(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def dump(path, rows, write):
    if not write:
        return
    if os.path.exists(path):
        shutil.copy2(path, path + BAK)
    tmp = path + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()

    n_records = len(load(os.path.join(HERE, RECORDS_REL)))

    # ---- sources.jsonl ----
    sp = os.path.join(HERE, "sources.jsonl")
    sources = load(sp)
    hit = None
    for row in sources:
        if row.get("source_id") != SOURCE_ID:
            continue
        hit = row
        row["public_status"] = (
            "Roster OBTAINED 2026-08-28 (owner-supplied 'Certified Indian Owned "
            "Businesses-updated 2026' docx, with the 2026 TERO Ordinance). Still "
            "not published at a pollable URL."
        )
        row["status_group"] = "Obtained"
        # A tribe's own certification register is the controlling assertion.
        row["source_priority_class"] = "Tribal Primary"
        row["cedar_treatment"] = (
            "Layer-1 source_records ingested; controlling assertion for these "
            "firms. Publication rights NOT yet confirmed with the Nation."
        )
        row["approx_records"] = n_records
        row["format"] = "DOCX register + DOCX ordinance (owner-supplied)"
        row["scrape_grade"] = "N/A - not scraped; supplied"
        row["fields_observed"] = (
            "business, owner, phone, email, address, preference tier, "
            "certification expiration"
        )
        row["caveats"] = (
            "Obtained 2026-08-28, not scraped. PROVENANCE OF THE OWNER'S COPY IS "
            "UNRECORDED and publication rights are unconfirmed - do not publish "
            "records until the Nation confirms. The register is titled "
            "'Certified Indian Owned Businesses' but one row carries a 4th-level "
            "tier, which the ordinance defines as NON-certified; that conflict is "
            "flagged on the record, not resolved. The ordinance's Chapter 6 "
            "category-C sentence is corrupted in the source document."
        )
        row["last_checked"] = TODAY
        row["suggested_cadence"] = "Semiannual re-ask (certifications expire on rolling dates)"
    if hit is None:
        sys.exit(f"{SOURCE_ID} not found in sources.jsonl")

    # ---- partnership_leads.jsonl : keep the row, mark it converted ----
    lp = os.path.join(HERE, "partnership_leads.jsonl")
    leads = load(lp)
    n_leads = 0
    for row in leads:
        if row.get("source_id") == SOURCE_ID:
            n_leads += 1
            row["converted"] = TODAY
            row["converted_note"] = (
                f"Roster obtained {TODAY} (owner-supplied). {n_records} layer-1 "
                f"records at {RECORDS_REL}. Remaining ask: permission to publish, "
                "a data dictionary, and a scheduled refresh."
            )
            row["recommended_next_step"] = (
                "Confirm publication rights and a refresh schedule with the White "
                "Earth TERO office. The roster itself is no longer the blocker."
            )

    # ---- verification_log.jsonl ----
    vp = os.path.join(HERE, "verification_log.jsonl")
    vlog = load(vp)
    vlog.append({
        "source_id": SOURCE_ID,
        "source": "White Earth Nation - TERO Certified Indian-Owned Business Registry",
        "result": f"CONVERTED Lead -> Obtained: roster supplied by owner, {n_records} records ingested",
        "notes": (
            "Owner supplied two documents on 2026-08-28: the 2026 certified-business "
            "register and the 2026 TERO Ordinance. Parsed to layer-1 with zero "
            "unparsed lines and 22/22 addresses resolved. The ordinance yields the "
            "full contracting preference ladder (Chapter 6 categories C-F) and the "
            "Schedule of Percentage Preference, a bid-price preference sliding from "
            "10% under $100k to 1.5% over $7M - the first quantified preference "
            "schedule in the registry. Two source defects recorded, not repaired: a "
            "phone number carrying only 9 digits, and a corrupted category-C sentence in the "
            "ordinance. Publication rights are UNCONFIRMED."
        ),
        "checked": TODAY,
        "channel": "owner_supplied_document",
        "evidence_urls": [
            "https://www.whiteearth.com/divisions/human-services/workforce-center",
            SNAP_REL + "Certified Indian Owned Businesses-updated 2026.docx",
            SNAP_REL + "TERO Ordinance 2026 copy.docx",
        ],
    })

    print(f"TBD-113: Lead -> Obtained, {n_records} records, {n_leads} lead row(s) marked")
    if not a.write:
        print("DRY RUN -- pass --write to persist.")
        return 0

    dump(sp, sources, True)
    dump(lp, leads, True)
    dump(vp, vlog, True)
    print("wrote sources.jsonl, partnership_leads.jsonl, verification_log.jsonl")
    print(f"backups: *{BAK}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
