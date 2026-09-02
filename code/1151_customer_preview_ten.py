#!/usr/bin/env python3
"""
Cedar Press - 1151: the ten-row preview a buyer actually opens.

    py -3 code/1151_customer_preview_ten.py            # report
    py -3 code/1151_customer_preview_ten.py build
    py -3 code/1151_customer_preview_ten.py verify

WHY THIS IS NOT `1135`'s SAMPLE
--------------------------------
Owner, 2026-09-02: *"I want the datasets you can download, twelve datasets
right now, to just be ten rows just to test what it looks like. Make sure those
ten rows for every dataset look amazing... I'm gonna send the URL to Brian to
log in and mess around with."*

`1135` already writes ten rows of every internal TABLE, and `1137` writes the
full combined datasets. Neither is what someone opens to decide whether Cedar
is worth paying for, and the reason is measurable:

    dataset            columns   leads with
    contractors             82   cedar_uid, tribe_id, cage_code
    funding                 86   cedar_uid, ledger_proposed_tribe_id
    legislation             39   bill_id, companion_bill_id, sponsor_bioguide_id
    gaming                 311   cedar_uid, cedar_place_id, tribe_id, entity_id

Every one of them opens on a wall of internal identifiers, and `legislation`
shows three ids before it shows the title of the bill. On ten rows and
eighty-plus columns a reader gets a horizontal scroll of mostly-empty cells and
concludes the dataset is thin, which is the opposite of true.

**A PREVIEW IS AN ADVERTISEMENT. THE FULL FILE IS THE PRODUCT.** That is why
this script curates columns and `1137` deliberately does not: dropping a column
from the deliverable loses data a customer paid for, while showing all 311 in a
preview loses the customer. They are different jobs and they get different
files, which is also why this writes to `dist/preview/` and never touches
`dist/customer/`.

HOW COLUMNS ARE CHOSEN
----------------------
`PREVIEW` below is CURATED, per dataset, and stated here rather than derived,
for the same reason `770`'s flagship choice is: a rule that picks by fill rate
or by position picks identifiers, because identifiers are always populated and
always first. The order is the order a person reads in - who, what, how much,
when, where - and the Cedar id comes LAST, present so the preview still shows
that every row is keyed to an entity.

A dataset with no curated list falls back to a scorer, and `verify` names it,
because the fallback is a stopgap and should be visible rather than quietly
permanent.

HOW ROWS ARE CHOSEN
-------------------
Not `head(10)`, which returns one agency, one year, one tribe. Rows are picked
to maximise DISTINCT ENTITIES across the ten, preferring rows that are complete
in the previewed columns and, where the dataset carries money, that carry a
non-zero amount. A preview whose ten rows are all the same nation understates
the coverage as badly as one that shows blank columns.

WHAT THIS WILL NOT DO
---------------------
Reorder, filter or beautify a VALUE. Every cell is exactly what the delivered
file holds. A preview that cleans up its rows is a lie about the product, and
the first thing a buyer does with the real file is discover it.
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()
SRC = ROOT / "dist" / "customer"
OUT = ROOT / "dist" / "preview"
N = 10

from cedar_publication import (          # noqa: E402
    STOREFRONT_SHELVES, shelves, publishable_columns,
)

#: Curated, per dataset, in reading order. The Cedar id goes LAST.
PREVIEW: dict[str, list[str]] = {
    "contractors": [
        "awardee_name", "canonical_name", "parent_name", "funding_agency",
        "setaside", "fiscal_year", "total_obligations", "recipient_city_name",
        "recipient_state_code", "contract_number", "cedar_uid"],
    "funding": [
        "recipient_name", "canonical_name", "awarding_agency_name",
        "cfda_title", "assistance_type_description", "action_date",
        "obligated_usd", "recipient_city_name", "recipient_state_code",
        "award_id_fain", "cedar_uid"],
    "subcontracting": [
        "sub_awardee_name", "prime_awardee_name", "subaward_amount",
        "fiscal_year", "sub_place_of_perform_state", "prime_award_id",
        "cedar_uid"],
    "legislation": [
        "bill_id", "title", "congress", "chamber", "sponsor",
        "introduced_date", "latest_action", "latest_action_date",
        "policy_area"],
    "federal-register": [
        "tribe_name", "channel", "title", "publication_date", "agency",
        "document_number", "cedar_uid"],
    "nagpra": [
        "institution_name", "institution_state", "title", "publication_date",
        "mni_total_stated", "document_number", "affiliated_entity_ids"],
    "deals": [
        "native_party_canonical_name", "counterparty_name", "deal_type",
        "announced_date", "deal_value_usd", "state", "Deal_ID", "cedar_uid"],
    "lobbying": [
        "client_name", "registrant_name", "filing_year", "filing_type",
        "amount_reported", "issue_areas", "cedar_uid"],
    "nonprofits": [
        "org_name", "city", "state", "ntee_description", "ruling_year",
        "total_revenue", "ein", "cedar_uid"],
    "natural-resources": [
        "recipient_name", "commodity", "revenue_type", "fiscal_year",
        "revenue_usd", "state", "cedar_uid"],
    "native-owned-businesses": [
        "business_name", "certifying_authority_name", "certification_type",
        "city", "state", "naics_description", "business_source_id"],
    "nest": [
        "enterprise_name", "owner_hub_canonical_name", "relation_class",
        "uei", "cage_code", "state", "enterprise_id"],
    "gaming": [
        "facility_name", "tribe", "city", "state", "open_date",
        "gaming_class_iii_authorized", "n_operating_entities",
        "cedar_place_id"],
}

#: Columns that are never interesting in a preview even when well populated.
DULL = ("source_file", "build_date", "_basis", "_flag", "inflation_base_year",
        "deflator_factor", "pre_2000", "attribution_", "duplicate_",
        "n_capacity", "vintage")


def score_fallback(hdr, rows):
    """Only for a dataset with no curated list. Named by `verify`."""
    def ok(c):
        cl = c.lower()
        if "__" in c or any(d in cl for d in DULL):
            return False
        return not (cl.endswith("_id") or cl.endswith("_uid"))
    fill = {c: sum(1 for r in rows if (r.get(c) or "").strip()) / max(len(rows), 1)
            for c in hdr}
    cand = [c for c in hdr if ok(c) and fill[c] > 0.6]
    return cand[:12] or hdr[:12]


def entity_of(r):
    for c in ("canonical_name", "tribe", "tribe_name", "tribe_canonical_name",
              "owner_hub_canonical_name", "native_party_canonical_name",
              "cedar_uid", "tribe_id"):
        v = (r.get(c) or "").strip()
        if v:
            return v
    return ""


def money_of(r, cols):
    for c in cols:
        if any(k in c.lower() for k in ("usd", "amount", "obligation", "value",
                                        "revenue")):
            try:
                return abs(float((r.get(c) or "0").replace(",", "").replace("$", "")))
            except ValueError:
                pass
    return 0.0


def pick(rows, cols, n=N):
    """Maximise distinct entities; prefer complete rows and real money."""
    scored = sorted(
        rows,
        key=lambda r: (-sum(1 for c in cols if (r.get(c) or "").strip()),
                       -money_of(r, cols)))
    seen, out = set(), []
    for r in scored:
        e = entity_of(r)
        if e and e in seen:
            continue
        seen.add(e)
        out.append(r)
        if len(out) == n:
            return out
    for r in scored:                    # top up if the table is narrow
        if r not in out:
            out.append(r)
        if len(out) == n:
            break
    return out


def datasets():
    sh = shelves()
    return sorted(c for c, s in sh.items() if s in STOREFRONT_SHELVES)


def run(write: bool) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    man = []
    for coll in datasets():
        f = SRC / f"{coll}.csv"
        if not f.exists():
            man.append({"dataset": coll, "note": "delivered file absent"})
            print(f"    {coll:<26} DELIVERED FILE ABSENT")
            continue
        with f.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            rd = csv.DictReader(fh)
            hdr = publishable_columns(rd.fieldnames or [])
            rows = [r for i, r in zip(range(4000), rd)]
        curated = PREVIEW.get(coll)
        if curated:
            cols = [c for c in curated if c in hdr]
            missing = [c for c in curated if c not in hdr]
        else:
            cols, missing = score_fallback(hdr, rows), []
        chosen = pick(rows, cols)
        if write:
            with (OUT / f"{coll}.csv").open("w", encoding="utf-8", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
                w.writeheader()
                w.writerows(chosen)
        man.append({
            "dataset": coll, "rows": len(chosen), "columns": len(cols),
            "curated": int(bool(curated)),
            "curated_columns_absent": "; ".join(missing),
            "distinct_entities": len({entity_of(r) for r in chosen}),
            "full_columns": len(hdr),
        })
        flag = "" if curated else "   <- FALLBACK, not curated"
        miss = f"   missing {len(missing)}" if missing else ""
        print(f"    {coll:<26} {len(chosen):>2} rows x {len(cols):>2} cols  "
              f"{man[-1]['distinct_entities']:>2} entities"
              f"  (of {len(hdr)} full){flag}{miss}")
    if write:
        (OUT / "MANIFEST.json").write_text(
            json.dumps({"built": TODAY, "rows_per_dataset": N,
                        "datasets": man}, indent=2) + "\n", encoding="utf-8")
    print(f"\n  1151 preview   {'BUILT' if write else 'report only'}   "
          f"{len(man)} dataset(s)")
    if not write:
        print("  nothing written. re-run with `build`.")
    return 0


def verify() -> int:
    bad = []
    want = datasets()
    if len(want) != 12:
        bad.append(f"{len(want)} storefront datasets, expected 12")
    for coll in want:
        p = OUT / f"{coll}.csv"
        if not p.exists():
            bad.append(f"{coll}: no preview")
            continue
        with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            rd = csv.DictReader(fh)
            hdr = list(rd.fieldnames or [])
            rows = list(rd)
        if len(rows) != N:
            bad.append(f"{coll}: {len(rows)} rows, expected {N}")
        if len(hdr) > 14:
            bad.append(f"{coll}: {len(hdr)} preview columns - too wide to read")
        if coll not in PREVIEW:
            bad.append(f"{coll}: using the FALLBACK scorer, not a curated list")
        # a preview whose rows are all one entity understates the dataset
        ents = len({entity_of(r) for r in rows})
        if len(rows) >= N and ents < 3:
            bad.append(f"{coll}: only {ents} distinct entities across {len(rows)} rows")
        # every cell must exist in the delivered file - no beautifying
        src = SRC / f"{coll}.csv"
        if src.exists():
            with src.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
                srchdr = list((csv.DictReader(fh)).fieldnames or [])
            for c in hdr:
                if c not in srchdr:
                    bad.append(f"{coll}: preview column {c} is not in the "
                               f"delivered file")
    for b in bad[:25]:
        print("  FAIL " + b)
    print(f"  1151 verify   {'FAIL' if bad else 'ok'}   {len(bad)} problem(s); "
          f"{len(want)} storefront datasets")
    return 1 if bad else 0


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "report"
    if mode == "verify":
        return verify()
    return run(mode == "build")


if __name__ == "__main__":
    sys.exit(main())
