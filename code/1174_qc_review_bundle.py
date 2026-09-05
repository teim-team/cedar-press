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
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cedar_publication import lobbying_row_counts  # noqa: E402

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
    num = defaultdict(lambda: {"n": 0, "usd": 0.0, "sup": 0, "fenced_usd": 0.0})
    with (CUSTOMER / "lobbying.csv").open(encoding="utf-8-sig", errors="replace",
                                          newline="") as fh:
        for r in csv.DictReader(fh):
            if not in_window(r.get("filing_year")):
                continue
            # ONE ROW PER CLIENT means the client is IN the key. Keyed on the
            # entity alone, a tribe's several subsidiaries filing as distinct
            # LDA clients collapsed into one row with their spend combined
            # and only three names surviving (Codex, PR #56).
            uid = (r.get("cedar_uid") or "").strip()
            client = (r.get("client_name") or "").strip().upper()
            key = (uid or "NO_UID", client)
            a, n = agg[key], num[key]
            n["n"] += 1
            # THE FENCE. An amendment restates the filing it supersedes, so
            # summing both counts the money twice; the shared fence in
            # cedar_publication is what makes the money column summable, and
            # this sheet presented the double-counted total (Codex, PR #56).
            if lobbying_row_counts(r):
                n["usd"] += money(r.get("spend_usd"))
            else:
                n["fenced_usd"] += money(r.get("spend_usd"))
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
            "spend_excluded_by_fence_usd": round(num[key]["fenced_usd"], 2),
            "years": " | ".join(sorted(a["filing_year"])),
            "filing_types": " | ".join(sorted(a["filing_type_display"])[:4]),
            "government_entities": " | ".join(sorted(a["government_entities"])[:3]),
        })
    recs.sort(key=lambda r: -r["reported_spend_usd"])
    return write("5_lobbying_2025_2026_unique_clients.csv", recs)



CONTRACT_CAP = 3000


def _fy(v):
    v = (v or "").strip()
    return v[:4] if len(v) >= 4 and v[:4].isdigit() else ""


def _num(v):
    try:
        return float(str(v).replace(",", "").replace("$", "").strip() or 0)
    except ValueError:
        return 0.0


def federal_contracting():
    """Prime contracting, ONE ROW PER CONTRACT, not per modification.

    Owner, 2026-09-04: *"in the row should be, like, unique by contract or
    award. We don't need to have every contract modification."*

    Measured: the 2025-2026 window holds 110,692 rows but only 68,616 distinct
    `contract_number` values - roughly 1.6 rows per contract - so the file
    counts modifications as if they were awards. Anyone reading it as a deal
    count is overstating activity by 61%.

    WHY IT IS CAPPED. 68,616 contracts x 79 columns is about 40 MB and the
    artifact ceiling is 16 MB, so the sheet carries the largest CONTRACT_CAP
    contracts by obligation and says so. It is a review surface for judging
    STRUCTURE, not a complete extract, and a sheet that silently truncates is
    worse than one that states its own limit.

    TWO PASSES, ON PURPOSE. Pass one aggregates obligations per contract using
    small values only; pass two re-reads to collect the full rows for the
    contracts that made the cut. Holding 68,616 wide rows in memory to save a
    pass is exactly the shape that took this machine down twice today.
    """
    src = CUSTOMER / "contractors.csv"
    if not src.exists():
        print("    contractors.csv absent - skipped")
        return
    years = {"2025", "2026"}

    agg = {}
    with src.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            if _fy(r.get("fiscal_year")) not in years:
                continue
            cn = (r.get("contract_number") or "").strip()
            if not cn:
                continue
            a = agg.get(cn)
            ob = _num(r.get("total_obligations"))
            # total_award_value is CUMULATIVE, RESTATED PER ROW - docs/
            # MONEY_TOTALLING_RULES.md: NEVER SUM, measured 18.88x overstated
            # when summed. Obligations are summed; the award value is read
            # off the latest action for the contract (Codex, PR #56).
            av = _num(r.get("total_award_value"))
            when = (r.get("action_date") or "").strip()
            if a is None:
                agg[cn] = [ob, av, 1, when]
            else:
                a[0] += ob
                a[2] += 1
                if when >= a[3]:
                    a[1], a[3] = av, when
    keep = {cn for cn, _v in sorted(agg.items(), key=lambda kv: -kv[1][0])[:CONTRACT_CAP]}

    best = {}
    with src.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            if _fy(r.get("fiscal_year")) not in years:
                continue
            cn = (r.get("contract_number") or "").strip()
            if cn not in keep:
                continue
            cur = best.get(cn)
            if cur is None or _num(r.get("total_obligations")) > _num(
                    cur.get("total_obligations")):
                best[cn] = r

    recs = []
    for cn, r in best.items():
        ob, av, n, _when = agg[cn]
        r = dict(r)
        r["contract_total_obligations"] = "%.2f" % ob
        r["contract_total_award_value"] = "%.2f" % av
        r["n_rows_collapsed"] = str(n)
        r["grain_note"] = ("ONE ROW PER CONTRACT. %d source row(s) collapsed; "
                           "obligations are summed, award value is the latest "
                           "action's restated total." % n)
        recs.append(r)
    recs.sort(key=lambda r: -_num(r.get("contract_total_obligations")))
    order = ["cedar_uid", "canonical_name", "awardee_name", "contract_number",
             "parent_contract_number", "fiscal_year",
             "contract_total_obligations", "contract_total_award_value",
             "n_rows_collapsed", "grain_note", "awardee_uei", "setaside"]
    keepc = order + [k for k in (recs[0] if recs else {}) if k not in order]
    write("6_federal_contracting_2025_2026.csv", recs, keepc)
    print("      (%d contracts of %d in window; capped at %d by obligation)"
          % (len(recs), len(agg), CONTRACT_CAP))


def subcontracting():
    """Subawards in the window, one row per prime->sub award."""
    src = CUSTOMER / "subcontracting.csv"
    if not src.exists():
        print("    subcontracting.csv absent - skipped")
        return
    years = {"2025", "2026"}
    recs = []
    with src.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            if _fy(r.get("fiscal_year")) in years:
                recs.append(r)
    recs.sort(key=lambda r: -_num(r.get("subaward_amount")))
    # CAPPED for the same reason as contracting: 10,410 subawards x 86 columns
    # is 13.7 MB, and with contracting's 4.6 MB that alone exceeds the 16 MB
    # artifact ceiling before the other five sheets are counted. Largest by
    # amount, and the sheet says so rather than truncating quietly.
    total_in_window = len(recs)
    recs = recs[:CONTRACT_CAP]
    for r in recs:
        r["grain_note"] = ("one row per prime-to-sub award; sheet capped at the "
                           "largest %d of %d in window by amount"
                           % (CONTRACT_CAP, total_in_window))
    order = ["prime_cedar_uid", "sub_cedar_uid", "prime_name", "sub_name",
             "prime_award_id", "subaward_amount", "subaward_date",
             "fiscal_year", "prime_uei", "sub_uei", "sub_state", "naics"]
    order = [c for c in order if recs and c in recs[0]]
    keepc = order + [k for k in (recs[0] if recs else {}) if k not in order]
    write("7_subcontracting_2025_2026.csv", recs, keepc)
    print("      (%d subawards of %d in window; capped at %d by amount)"
          % (len(recs), total_in_window, CONTRACT_CAP))



def federal_awards():
    """Federal spending at the AWARD grain - the reviewer's main dataset.

    Verdict, 2026-09-04: *"do not publish this version as the federal-spending
    dataset."* The old sheet was one row per recipient UEI summarising 61,579
    transactions, so it could not say what awards exist nor separate 2025 from
    2026. Worse, 1,028 of its 1,060 attributions came from `uei_exact_archive`
    and $980.6M of San Jose public housing was keyed to a New Mexico pueblo.

    1186 rebuilds it: 29,622 awards, obligations split by year, and attribution
    that is deny-by-default - tier A or B in the identifier ledger, tier X
    honoured as a refusal, and 14 recipients proven false refused outright.
    """
    src = CUSTOMER / "federal_awards_2025_2026.csv"
    if not src.exists():
        print("    federal_awards_2025_2026.csv absent - run 1186 build")
        return
    with src.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        recs = list(csv.DictReader(fh))
    total = len(recs)
    recs.sort(key=lambda r: -_num(r.get("obligated_window_usd")))
    recs = recs[:CONTRACT_CAP]
    for r in recs:
        r["grain_note"] = ("ONE ROW PER AWARD, modifications summed. Sheet "
                           "capped at the largest %d of %d awards by window "
                           "obligations." % (CONTRACT_CAP, total))
    order = ["cedar_uid", "name", "entity_type", "recipient_uei",
             "recipient_name", "award_id", "award_type", "awarding_agency",
             "program_code", "program_name", "obligated_2025_usd",
             "obligated_2026_usd", "obligated_window_usd", "attribution_basis",
             "grain_note"]
    keepc = order + [k for k in (recs[0] if recs else {}) if k not in order]
    write("8_federal_awards_2025_2026.csv", recs, keepc)
    print("      (%d awards of %d; capped at %d by window obligations)"
          % (len(recs), total, CONTRACT_CAP))



def advocacy():
    """Native Federal Advocacy & Engagement - replaces the 222-client summary.

    Reviewer, 2026-09-04: "'Lobbying' alone would be misleading because formal
    tribal consultations, public comments and official tribal-government
    communications are not necessarily lobbying under the LDA." One flat table,
    one row per documented activity per entity, activity_type carrying the
    distinction. Client totals and meeting counts are DERIVABLE from it, which
    is why the summary could be retired rather than maintained beside it.
    """
    src = CUSTOMER / "native_federal_advocacy_2025_2026.csv"
    if not src.exists():
        print("    native_federal_advocacy absent - run 1187 build")
        return
    with src.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        recs = list(csv.DictReader(fh))
    order = ["cedar_uid", "name", "entity_type", "activity_id", "activity_type",
             "activity_date", "year", "quarter", "reported_party_name",
             "representative_or_registrant", "federal_entity", "topic",
             "reported_amount_usd", "amount_type", "source_type",
             "source_record_id", "source_url", "notes"]
    keepc = order + [k for k in (recs[0] if recs else {}) if k not in order]
    write("9_native_federal_advocacy_2025_2026.csv", recs, keepc)


def main():
    print("\n  Cedar Press - owner review bundle\n")
    native_entities()
    deals()
    funding()
    lobbying()
    federal_contracting()
    subcontracting()
    federal_awards()
    advocacy()
    print(f"\n  written to {OUT.relative_to(ROOT)}")
    print("  every sheet leads with YOUR_NOTES. Silence means approved.")


if __name__ == "__main__":
    main()
