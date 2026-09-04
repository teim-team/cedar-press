#!/usr/bin/env python3
"""
Cedar Press - 1174: the owner's review bundle.

    py -3 code/1174_qc_review_bundle.py

Owner, 2026-09-04:

    "5 things, that doc, the native entity spreadsheet (ALL), indian country
     deals, federal spending and lobbying (2025-2026) on the last three but all
     observations that are UNIQUE even if we identified them confidently just
     to review in spreadsheet format that i can download i'll have a column
     i'll add with my notes if anything needs to change if its good i wont say
     anything"

Five files. Every reviewable sheet leads with `YOUR_NOTES`, blank, so a note
can be typed without scrolling. Silence means approved.

UNIQUE OBSERVATIONS, NOT TRANSACTIONS - AND WHY THAT MATTERS
-------------------------------------------------------------
The owner asked for this and it is the right unit. Federal funding's 2025-2026
window is 61,579 transaction rows and 2,315 distinct recipients; reviewing the
transactions means reading the same entity hundreds of times and still not
seeing the entity-level truth. Measured on that window:

    keyed by row      85.0%
    keyed by dollar   80.9%
    keyed by ENTITY   45.8%

The first two are what a row-level review reports, and they hide the third.
Cedar keyed the high-volume recipients and left the long tail: 227 unkeyed
entities carry over $1M each, $4.2B together. That gap is invisible at the
transaction grain and unmissable at the entity grain.

"EVEN IF WE IDENTIFIED THEM CONFIDENTLY" is the load-bearing half of the
instruction. A review of only the uncertain rows can never find a confident
mistake, and this session produced two worth remembering: `Tikigaq Corporation`
was keyed to `Paiute of Utah`, and `Amee Bay` to the `Three Affiliated Tribes`
on the word "Three" in `Three Saints Bay`. Both were tier A. So the sheets
carry every distinct observation, keyed or not, sorted by dollars so the
largest claims are read first.
"""
from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dist" / "qc_review"
CUSTOMER = ROOT / "dist" / "customer"
SPINE = ROOT / "data" / "spine" / "cedar_identity_register.csv"
csv.field_size_limit(10_000_000)

NOTES = "YOUR_NOTES"


def rows(p):
    with Path(p).open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def write(name, recs, order=None):
    """Write a sheet with YOUR_NOTES first. Refuses to write nothing."""
    if not recs:
        raise SystemExit(f"FATAL: {name} would be empty - refusing to write a "
                         f"sheet that says nothing")
    OUT.mkdir(parents=True, exist_ok=True)
    fields = [NOTES] + (order or [k for k in recs[0] if k != NOTES])
    with (OUT / name).open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in recs:
            r.setdefault(NOTES, "")
            w.writerow(r)
    print(f"  {name:<44} {len(recs):>7,} rows")
    return len(recs)


def money(v):
    try:
        return float(str(v).replace(",", "").replace("$", "") or 0)
    except ValueError:
        return 0.0


def in_window(v):
    return str(v).strip()[:4] in ("2025", "2026")


# ---------------------------------------------------------------------------

def native_entities():
    """ALL of them, not a window. This is the reference the others key to."""
    # NO HANDLE. Owner, 2026-09-04: "the readable code we dont need and it is
    # CICD's - remove from all datasets, remove every trace from every
    # dataset... we dont need a readable id cuz we just have the entity name".
    # The prefixed handle is the CICD Native Entity Connector Crosswalk code,
    # not Cedar's. `cedar_uid` joins, `canonical_name` reads; there is no third
    # thing for a second code to do.
    # NO SHORT HANDLE EITHER. Owner, 2026-09-04: "there should be no short
    # handle we cant use it reliable". Measured, and he is right: matching the
    # BIA list on `canonical_name` resolved 29 of 577 rows (5.0%); matching on
    # the official name resolved 576 of 577 (99.8%). `Benton` carries nothing
    # that connects it to the Utu Utu Gwaitu Paiute Tribe of the Benton Paiute
    # Reservation, which is also why 21 corrupted handles went undetected -
    # nothing could reach them to notice.
    #
    # So this reads the SOURCED spreadsheet built by 1181, where `name` is the
    # official name with its register, URL and capture date beside it, rather
    # than re-deriving a second answer from the spine.
    src = ROOT / "dist" / "customer" / "native_entities.csv"
    if not src.exists():
        raise SystemExit(
            "1_native_entities_ALL.csv needs dist/customer/native_entities.csv"
            " - run `py -3 code/1181_native_entities_spreadsheet.py build`")
    with src.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        recs = list(csv.DictReader(fh))
    order = ["cedar_uid", "name", "entity_type", "state", "register_status",
             "former_names", "name_source", "name_source_url",
             "name_captured", "name_match_route"]
    return write("1_native_entities_ALL.csv", recs, order)


def deals():
    """One row per DEAL - a deal is already an observation, not a transaction."""
    recs = [r for r in rows(CUSTOMER / "deals.csv")
            if in_window(r.get("Event_Year"))]

    # record_class AND Record_Scope COME BACK, for the review sheet only.
    # Reviewer, 2026-09-04: the schema cleanup "removed record_class and
    # Record_Scope from the working dataset. Those should remain internally
    # because the 208 rows still include 84 public-award records, 36
    # unverified tribal-press candidates, 21 project milestones and 4 staged,
    # unmerged candidates. Without those fields, later code cannot reliably
    # distinguish release-ready deals from records that should be moved,
    # reviewed, or excluded."
    #
    # He is right, and the two columns are in DEALS_INTERNAL for a good but
    # DIFFERENT reason: they must not reach a CUSTOMER. This sheet is the
    # owner's internal review bundle, which is exactly where they belong. So
    # they are read back from the source table rather than un-withheld
    # globally - the public download stays clean, 41 columns become 43 here.
    src = {}
    spath = ROOT / "data" / "clean" / "deals_classified.csv"
    if spath.exists():
        for r in rows(spath):
            did = (r.get("Deal_ID") or "").strip()
            if did:
                src[did] = r
    for r in recs:
        s = src.get((r.get("Deal_ID") or "").strip(), {})
        r["record_class"] = s.get("record_class", "")
        r["Record_Scope"] = s.get("Record_Scope", "")

    order = ["Deal_ID", "native_party_canonical_name", "cedar_uid",
             "Deal_Title", "Counterparty_or_Funder", "Deal_Category",
             "Event_Date", "Event_Year", "Announced_Value_USD", "State",
             "record_class", "Record_Scope"]
    keep = order + [k for k in (recs[0] if recs else {}) if k not in order]
    return write("3_indian_country_deals_2025_2026.csv", recs, keep)


def funding():
    """2,315 unique recipients out of 61,579 transactions.

    Grouped on the UEI where there is one, else on the recipient name - a
    recipient without a UEI is still a distinct party and must not be silently
    merged with every other unidentified one.
    """
    # THE OFFICIAL NAME, not the register's short handle. Reading
    # `canonical_name` here would have reintroduced `Confederated Yakama` into
    # the owner's review bundle after every shipped dataset had been cleaned
    # of it - the sheet is built from the spine, so it bypasses the
    # substitution that 1137 and 1182 apply to dist/customer.
    _names = ROOT / "data" / "spine" / "cedar_entity_names.csv"
    if _names.exists():
        reg = {r["cedar_uid"]: r.get("name", "") for r in rows(_names)
               if r.get("cedar_uid")}
    else:
        reg = {r["cedar_uid"]: r.get("canonical_name", "")
               for r in rows(SPINE) if r.get("cedar_uid")}
    # Every UEI Cedar keys positively ANYWHERE, so a gap here can be told from
    # a genuine unknown. This is the "we have a rule and did not apply it" test.
    known = {}
    for path, ucol in (("data/clean/cedar_identifier_ledger_final.csv", "identifier"),
                       ("data/clean/prime_contracts.csv", "awardee_uei")):
        p = ROOT / path
        if not p.exists():
            continue
        with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            for r in csv.DictReader(fh):
                u = (r.get(ucol) or "").strip().upper()
                k = (r.get("cedar_uid") or "").strip()
                t = (r.get("confidence_tier") or "").strip().upper()
                if u and k and len(u) == 12:
                    prev = known.get(u)
                    if prev is None or (prev[2] == "X" and t != "X"):
                        known[u] = (k, (r.get("canonical_name") or "").strip(), t, Path(path).name)

    agg = defaultdict(lambda: defaultdict(set))
    num = defaultdict(lambda: {"n": 0, "usd": 0.0, "first": "", "last": ""})
    with (CUSTOMER / "funding.csv").open(encoding="utf-8-sig", errors="replace",
                                         newline="") as fh:
        for r in csv.DictReader(fh):
            if not in_window(r.get("action_date")):
                continue
            uei = (r.get("recipient_uei") or "").strip().upper()
            key = uei or "NO_UEI::" + (r.get("recipient_name") or "").strip().upper()
            a, n = agg[key], num[key]
            n["n"] += 1
            n["usd"] += money(r.get("obligated_usd"))
            d = (r.get("action_date") or "")[:10]
            if d:
                n["first"] = min(n["first"] or d, d)
                n["last"] = max(n["last"], d)
            for col in ("recipient_name", "cedar_uid", "canonical_name",
                        "awarding_agency_name", "cfda_title",
                        "attribution_status", "attribution_method",
                        "excluded_flag", "recipient_state_code"):
                v = (r.get(col) or "").strip()
                if v:
                    a[col].add(v)

    recs = []
    for key, a in agg.items():
        uids = sorted(a["cedar_uid"])
        uid = uids[0] if len(uids) == 1 else "|".join(uids)
        uei = "" if key.startswith("NO_UEI::") else key
        hit = known.get(uei) if (uei and not uid) else None
        recs.append({
            "recipient_uei": uei,
            "recipient_name": " | ".join(sorted(a["recipient_name"])[:3]),
            "n_name_variants": len(a["recipient_name"]),
            "cedar_uid": uid,
            "n_cedar_uids": len(uids),
            "canonical_name_in_data": " | ".join(sorted(a["canonical_name"])[:2]),
            "register_canonical_name": reg.get(uid, "") if len(uids) == 1 else "",
            "cedar_knows_this_uei_elsewhere": (hit[0] if hit and hit[2] != "X" else
                                               "(refused elsewhere)" if hit else ""),
            "known_as": hit[1] if hit and hit[2] != "X" else "",
            "known_from": hit[3] if hit and hit[2] != "X" else "",
            "attribution_status": " | ".join(sorted(a["attribution_status"])),
            "attribution_method": " | ".join(sorted(a["attribution_method"])[:2]),
            "excluded_flag": " | ".join(sorted(a["excluded_flag"])),
            "state": " | ".join(sorted(a["recipient_state_code"])[:3]),
            "n_transactions": num[key]["n"],
            "obligated_usd": round(num[key]["usd"], 2),
            "first_action_date": num[key]["first"],
            "last_action_date": num[key]["last"],
            "n_agencies": len(a["awarding_agency_name"]),
            "agencies": " | ".join(sorted(a["awarding_agency_name"])[:3]),
            "n_programs": len(a["cfda_title"]),
            "top_programs": " | ".join(sorted(a["cfda_title"])[:3]),
        })
    recs.sort(key=lambda r: -r["obligated_usd"])
    return write("4_federal_spending_2025_2026_unique_entities.csv", recs)


def lobbying():
    """One row per unique CLIENT, not per filing.

    A client files quarterly and amends, so the filing grain repeats the same
    party many times over. `n_filings` and `n_superseded` are carried so the
    amendment behaviour is still visible from the entity row.
    """
    agg = defaultdict(lambda: defaultdict(set))
    num = defaultdict(lambda: {"n": 0, "usd": 0.0, "sup": 0})
    with (CUSTOMER / "lobbying.csv").open(encoding="utf-8-sig", errors="replace",
                                          newline="") as fh:
        for r in csv.DictReader(fh):
            if not in_window(r.get("filing_year")):
                continue
            key = ((r.get("cedar_uid") or "").strip()
                   or "NO_UID::" + (r.get("client_name") or "").strip().upper())
            a, n = agg[key], num[key]
            n["n"] += 1
            n["usd"] += money(r.get("spend_usd"))
            if (r.get("supersession_status") or "").upper().startswith("SUPERSEDED"):
                n["sup"] += 1
            for col in ("client_name", "canonical_name", "registrant_name",
                        "cedar_uid", "filing_type_display", "government_entities",
                        "filing_year", "supersession_status"):
                v = (r.get(col) or "").strip()
                if v:
                    a[col].add(v)
    recs = []
    for key, a in agg.items():
        recs.append({
            "cedar_uid": " | ".join(sorted(a["cedar_uid"])),
            "client_name": " | ".join(sorted(a["client_name"])[:3]),
            "n_client_name_variants": len(a["client_name"]),
            "canonical_name": " | ".join(sorted(a["canonical_name"])[:2]),
            "n_registrants": len(a["registrant_name"]),
            "registrants": " | ".join(sorted(a["registrant_name"])[:4]),
            "n_filings": num[key]["n"],
            "n_superseded_filings": num[key]["sup"],
            "reported_spend_usd": round(num[key]["usd"], 2),
            "years": " | ".join(sorted(a["filing_year"])),
            "filing_types": " | ".join(sorted(a["filing_type_display"])[:4]),
            "government_entities": " | ".join(sorted(a["government_entities"])[:3]),
        })
    recs.sort(key=lambda r: -r["reported_spend_usd"])
    return write("5_lobbying_2025_2026_unique_clients.csv", recs)


def main():
    print("\n  Cedar Press - owner review bundle\n")
    native_entities()
    deals()
    funding()
    lobbying()
    print(f"\n  written to {OUT.relative_to(ROOT)}")
    print("  every sheet leads with YOUR_NOTES. Silence means approved.")


if __name__ == "__main__":
    main()
