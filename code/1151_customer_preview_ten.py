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
N = 100        # was 10; the owner asked for a hundred so it reads as real

from cedar_publication import (          # noqa: E402
    STOREFRONT_SHELVES, shelves, publishable_columns,
)

#: Curated, per dataset, in reading order. The Cedar id goes LAST.
#:
#: READ FROM THE REAL HEADERS, 2026-09-02, AFTER THE FIRST VERSION GUESSED.
#: The first draft of this dict was written from what the columns SHOULD be
#: called and was wrong on 8 of 13 datasets - `business_name` where the file
#: says `business_name_raw`, `state` where it says `state_province`,
#: `deal_value_usd` where it says `Announced_Value_USD`, `sub_awardee_name`
#: where it says `sub_name`. A missing column is silently skipped, so the
#: previews rendered narrow and nobody was told. On the one artifact a
#: prospective customer opens first. Every name below now appears in the
#: delivered file, and `verify` fails if one stops appearing.
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
        "sub_name", "prime_name", "prime_parent_name", "subaward_amount",
        "subaward_date", "fiscal_year", "naics_title", "sub_state",
        "subaward_number", "cedar_uid"],
    "legislation": [
        "bill_id", "title", "congress", "chamber", "sponsor",
        "introduced_date", "latest_action", "policy_area", "entity_names"],
    "federal-register": [
        "tribe_name", "channel", "agency", "consultation_type", "topic",
        "notice_date", "federal_register_citation", "cedar_uid"],
    "nagpra": [
        "institution_name", "institution_city", "institution_state", "title",
        "publication_date", "document_number", "affiliated_entity_ids"],
    "deals": [
        "native_party_canonical_name", "Deal_Title", "Counterparty_or_Funder",
        "Deal_Category", "Event_Date", "Announced_Value_USD", "State",
        "Deal_ID", "cedar_uid"],
    "lobbying": [
        "canonical_name", "client_name", "registrant_name", "filing_year",
        "filing_type_display", "spend_usd", "government_entities",
        "cedar_uid"],
    "nonprofits": [
        "org_name", "city", "state", "ntee_code", "bmf_revenue_amt",
        "classification_ruling", "EIN", "cedar_uid"],
    "natural-resources": [
        "recipient_entity_name", "payer_entity_name", "commodity",
        "revenue_type", "period_start", "amount_usd", "aggregation_level",
        "cedar_uid"],
    "native-owned-businesses": [
        "business_name_raw", "certifying_authority_name", "programme_name",
        "service_category_raw", "city", "state_province", "harvest_date",
        "business_source_id"],
    "nest": [
        "enterprise_name", "owner_hub_name", "relation_class", "owner_class",
        "city", "state_province", "in_federal_contracting", "cedar_uid"],
    "gaming": [
        "facility_name", "tribe", "city", "state", "open_date",
        "gaming_class_iii_authorized", "n_operating_entities",
        "cedar_place_id"],
}

#: What makes two rows LOOK different, per dataset.
#:
#: A generic "find the entity column" test returned one entity for four
#: datasets and the previews were all the same thing repeated. The reason is
#: not a missing column - it is that the unit differs. A bill has no single
#: tribe; a NAGPRA notice is about an institution; a NEST row IS an
#: enterprise. Stating the unit per dataset is the honest version of a rule
#: that cannot be generic.
DIVERSITY: dict[str, str] = {
    "contractors": "awardee_name",
    "funding": "recipient_name",
    "subcontracting": "sub_name",
    "legislation": "title",
    "federal-register": "tribe_name",
    "nagpra": "institution_name",
    "deals": "native_party_canonical_name",
    "lobbying": "client_name",
    "nonprofits": "org_name",
    "natural-resources": "recipient_entity_name",
    "native-owned-businesses": "business_name_raw",
    "nest": "enterprise_name",
    "gaming": "facility_name",
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


def entity_of(r, coll=None):
    """The value that makes this row distinct, for THIS dataset.

    Falls back to a generic search only when the dataset has no declared key,
    which `verify` reports rather than tolerating silently. The generic search
    is what produced "1 distinct entity across 10 rows" on four datasets: it
    looked for a tribe on a table whose rows are bills.
    """
    if coll and coll in DIVERSITY:
        return (r.get(DIVERSITY[coll]) or "").strip()
    for c in ("canonical_name", "tribe", "tribe_name", "tribe_canonical_name",
              "owner_hub_name", "native_party_canonical_name", "cedar_uid"):
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


def pick(rows, cols, coll=None, n=N):
    """Maximise distinct entities; prefer complete rows and real money."""
    scored = sorted(
        rows,
        key=lambda r: (-sum(1 for c in cols if (r.get(c) or "").strip()),
                       -money_of(r, cols)))
    seen, out = set(), []
    for r in scored:
        e = entity_of(r, coll)
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
            rows = [r for i, r in zip(range(40000), rd)]
        curated = PREVIEW.get(coll)
        if curated:
            cols = [c for c in curated if c in hdr]
            missing = [c for c in curated if c not in hdr]
        else:
            cols, missing = score_fallback(hdr, rows), []
        chosen = pick(rows, cols, coll)
        if write:
            with (OUT / f"{coll}.csv").open("w", encoding="utf-8", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
                w.writeheader()
                w.writerows(chosen)
        man.append({
            "dataset": coll, "rows": len(chosen), "columns": len(cols),
            "curated": int(bool(curated)),
            "curated_columns_absent": "; ".join(missing),
            "distinct_entities": len({entity_of(r, coll) for r in chosen}),
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
        # A curated name that is not in the delivered file was silently
        # skipped by the builder, which is how 8 of 13 lists shipped wrong.
        for c in PREVIEW.get(coll, []):
            if c not in hdr:
                bad.append(f"{coll}: curated column {c} is missing from the "
                           f"preview - it is not in the delivered file")
        if coll not in DIVERSITY:
            bad.append(f"{coll}: no declared diversity key")
        if coll not in PREVIEW:
            bad.append(f"{coll}: using the FALLBACK scorer, not a curated list")
        # a preview whose rows are all one entity understates the dataset
        ents = len({entity_of(r, coll) for r in rows})
        if len(rows) >= N and ents < max(3, N // 4):
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
