#!/usr/bin/env python3
"""
Cedar Press - 841: WHAT IS MISSING, measured.

    py -3 code/841_missing_probe.py            # print the measurements
    py -3 code/841_missing_probe.py --json     # docs/WHAT_IS_MISSING.json

WHY THIS SCRIPT EXISTS
----------------------
`docs/WHAT_IS_MISSING.md` is a reading of `dist/samples/` as a BUYER would read
it. A reading is an opinion; the numbers underneath it must not be. Every
figure quoted in that document is produced here, from the clean tables, with
zero network requests, so the next agent can re-run it and see the same thing
or see that it moved.

WHAT IT DOES NOT DO
-------------------
It changes nothing. No table is written, no sample is rebuilt, no column is
added. Workstream `missing` is a READ.

THE ONE DISTINCTION IT IS BUILT TO MAKE
---------------------------------------
An absence has four causes and they are completely different work:

  SOURCE_DOES_NOT_PUBLISH  a fact about the world. Never a Cedar deficiency.
  ON_DISK_NOT_PROMOTED     already local. A join or a column list, not a fetch.
  NOT_ACQUIRED             a real acquisition task.
  CONSTRAINED              licence, statute or terms forbid it.

The middle one is the one this project keeps mislabelling as the third, which
is why every probe below reports the FILL COUNT of the column somewhere on
disk rather than only its absence from the sample.
"""
from __future__ import annotations

import argparse
import csv
import collections
import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
SPINE = ROOT / "data" / "spine"
RAW = ROOT / "data" / "raw"
csv.field_size_limit(10_000_000)

OUT: dict = {}
DS = ""


def rows(path: Path):
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        yield from csv.DictReader(fh)


def filled(path: Path, cols: list[str]) -> tuple[int, dict]:
    c = collections.Counter()
    n = 0
    for r in rows(path):
        n += 1
        for k in cols:
            if (r.get(k) or "").strip():
                c[k] += 1
    return n, {k: c[k] for k in cols}


def counts(path: Path, col: str, top: int = 15):
    c = collections.Counter((r.get(col) or "") for r in rows(path))
    return c.most_common(top)


def say(label: str, value):
    OUT[f"{DS}.{label.strip()}"] = value
    print(f"  {label:<58} {value}")


def register_names() -> dict:
    return {r["cedar_uid"]: r["canonical_name"]
            for r in rows(SPINE / "cedar_identity_register.csv")}


# ---------------------------------------------------------------- entity layer
def probe_entity():
    print("\n_ENTITY_LAYER  (cedar_identity_register.csv)")
    p = SPINE / "cedar_identity_register.csv"
    n, f = filled(p, ["cedar_uid", "canonical_name", "former_names",
                      "class_since_basis"])
    say("register rows", n)
    say("distinct minted values", len({r["minted"] for r in rows(p)}))
    say("distinct register_status values",
        len({r["register_status"] for r in rows(p)}))
    say("former_names filled", f["former_names"])

    reg = register_names()
    latest: dict = {}
    for r in rows(CLEAN / "federal_recognition_roster.csv"):
        u = (r.get("cedar_uid") or "").strip()
        nm = (r.get("entity_name") or "").strip()
        if u and nm:
            y = r.get("notice_year", "")
            if u not in latest or y > latest[u][0]:
                latest[u] = (y, nm)
    hit = set(reg) & set(latest)
    say("register entities with an FR legal name ON DISK", len(hit))
    say("  of those, register name differs from the FR legal name",
        sum(1 for u in hit if reg[u].lower() != latest[u][1].lower()))


# ----------------------------------------------------------------- contractors
def probe_contractors():
    print("\nCONTRACTORS  (prime_contracts.csv)")
    p = CLEAN / "prime_contracts.csv"
    n = 0
    zero = 0
    dup = collections.Counter()
    have = collections.Counter()
    for r in rows(p):
        n += 1
        if (r.get("total_obligations") or "").strip() in ("0", "0.0", "0.00"):
            zero += 1
        dup[r.get("contract_number", "")] += 1
        for k in ("total_award_value", "cedar_uid", "parent_contract_number",
                  "extent_competed", "cage_code"):
            if (r.get(k) or "").strip():
                have[k] += 1
    say("rows", n)
    say("total_award_value filled (omitted from sample)", have["total_award_value"])
    say("parent_contract_number filled (omitted from sample)",
        have["parent_contract_number"])
    say("cedar_uid filled", have["cedar_uid"])
    say("$0 obligation rows", zero)
    short = [k for k in dup if len(k) <= 6]
    say("rows whose contract_number is <=6 chars (not a key)",
        sum(dup[k] for k in short))
    say("most-reused contract_number", dup.most_common(1))

    # NAICS-6 is already on disk in the filtered archive extract.
    tot = withn = 0
    for fp in sorted(glob.glob(str(RAW / "contracts" / "usaspending_archive_2026-08-07"
                                   / "filtered" / "FY*_ledger_rows.csv"))):
        for r in rows(Path(fp)):
            tot += 1
            if (r.get("naics_code") or "").strip():
                withn += 1
    say("archive extract rows ON DISK", tot)
    say("  of those carrying 6-digit naics_code", withn)
    say("prime_contracts columns carrying NAICS",
        [c for c in next(rows(p)) if "naics" in c.lower()] or "none (sector = 2-digit only)")


# --------------------------------------------------------------------- funding
def probe_funding():
    print("\nFUNDING  (federal_funding_transactions.csv)")
    p = CLEAN / "federal_funding_transactions.csv"
    reg = register_names()
    n = neg = zero = blank = drift = 0
    drift_usd = 0.0
    have = collections.Counter()
    for r in rows(p):
        n += 1
        for k in ("recipient_uei", "cedar_uid", "assistance_type_description",
                  "awarding_sub_agency_name"):
            if (r.get(k) or "").strip():
                have[k] += 1
        try:
            v = float(r.get("obligated_usd") or 0)
        except ValueError:
            v = 0.0
        if v < 0:
            neg += 1
        if v == 0:
            zero += 1
        cn = (r.get("canonical_name") or "").strip()
        u = (r.get("cedar_uid") or "").strip()
        if not cn:
            blank += 1
        elif u in reg and cn.lower() != reg[u].lower():
            drift += 1
            drift_usd += v
    say("rows", n)
    say("recipient_uei filled (omitted from sample)", have["recipient_uei"])
    say("cedar_uid filled (omitted from sample)", have["cedar_uid"])
    say("assistance_type_description BLANK", n - have["assistance_type_description"])
    say("negative (deobligation) rows", neg)
    say("$0 rows", zero)
    say("blank canonical_name", blank)
    say("canonical_name DISAGREES with the register for the same cedar_uid", drift)
    say("  dollars on those rows", f"${drift_usd/1e9:.3f}B")


# ---------------------------------------------------------------------- gaming
def probe_gaming():
    print("\nGAMING  (gaming_facilities.csv)")
    g = list(rows(CLEAN / "gaming_facilities.csv"))
    say("facilities", len(g))
    say("property_status distribution",
        collections.Counter(r["property_status"] for r in g).most_common())
    say("status=current AND close_date populated",
        sum(1 for r in g if r["property_status"] == "current" and r["close_date"].strip()))
    say("open_date precision mix",
        collections.Counter(r.get("open_date_precision", "") for r in g).most_common())
    say("no city", sum(1 for r in g if not r.get("city", "").strip()))
    say("gaming class column on the facility",
        [c for c in g[0] if "class_ii" in c.lower()] or "none")

    rb = list(rows(CLEAN / "gaming_revenue_bounds.csv"))
    say("gaming_revenue_bounds rows ON DISK", len(rb))
    say("  facilities covered by a revenue bound",
        len({r["facility_id"] for r in rb} & {r["facility_id"] for r in g}))
    o = list(rows(CLEAN / "gaming_ordinances.csv"))
    gt = {r["tribe_id"] for r in g if r.get("tribe_id", "").strip()}
    ot = {r["tribe_id"] for r in o if r.get("tribe_id", "").strip()}
    say("facility-bearing tribes", len(gt))
    say("  with a gaming ordinance stating class II/III", len(gt & ot))
    loc = list(rows(CLEAN / "gaming_property_locations.csv"))
    say("location observations carrying a county",
        sum(1 for r in loc if r.get("county", "").strip()))


# ----------------------------------------------------------------- legislation
def probe_legislation():
    print("\nLEGISLATION  (bill_votes.csv)")
    bv = list(rows(CLEAN / "bill_votes.csv"))
    nb = {r["bill_id"]: r for r in rows(CLEAN / "native_bills.csv")}
    say("roll-call votes", len(bv))
    say("votes whose bill TITLE is on disk in native_bills.csv",
        sum(1 for r in bv if (nb.get(r["bill_id"], {}).get("title") or "").strip()))
    say("votes whose bill OUTCOME is on disk in native_bills.csv",
        sum(1 for r in bv if (nb.get(r["bill_id"], {}).get("outcome") or "").strip()))
    say("D_yea / R_yea filled (omitted from sample)",
        sum(1 for r in bv if (r.get("D_yea") or "").strip()))
    bad = [r for r in bv if r["result"].lower().startswith("fail")
           and int(r["yea"] or 0) > int(r["nay"] or 0)]
    say("votes recorded FAILED with more yea than nay", len(bad))
    say("  a threshold_required column exists",
        "yes" if "threshold_required" in bv[0] else "NO")
    say("  the sampled specimen", [r["vote_id"] for r in bad][:12])


# ------------------------------------------------------------------- lobbying
def probe_lobbying():
    print("\nLOBBYING  (lobbying_registrants.csv)")
    p = CLEAN / "lobbying_registrants.csv"
    lr = list(rows(p))
    say("registrants", len(lr))
    for k in ("spend_reported_usd", "issue_codes", "government_entities_lobbied"):
        say(f"{k} filled (omitted from sample)",
            sum(1 for r in lr if (r.get(k) or "").strip()))
    tot = sum(float(r["spend_reported_usd"]) for r in lr
              if (r.get("spend_reported_usd") or "").strip())
    say("sum of spend_reported_usd", f"${tot/1e6:,.1f}M")
    say("rows where n_native_clients == n_distinct_native_entities",
        f"{sum(1 for r in lr if r['n_native_clients'] == r['n_distinct_native_entities'])} of {len(lr)}")


# ------------------------------------------------------------ federal-register
def probe_fedreg():
    print("\nFEDERAL-REGISTER  (consultation_events.csv)")
    c = list(rows(CLEAN / "consultation_events.csv"))
    say("consultation event-participant rows", len(c))
    say("consultation_type distribution",
        collections.Counter(r["consultation_type"] for r in c).most_common(10))
    for k in ("event_start_date", "location", "format", "source_url"):
        say(f"{k} filled", sum(1 for r in c if (r.get(k) or "").strip()))
    say("agencies represented",
        collections.Counter(r["agency"] for r in c).most_common(6))


# --------------------------------------------------------------------- nagpra
def probe_nagpra():
    print("\nNAGPRA  (sample flagship = fr_nagpra_title_index.csv)")
    ti = list(rows(CLEAN / "fr_nagpra_title_index.csv"))
    say("title index rows / columns", f"{len(ti)} / {len(ti[0])}")
    nn = list(rows(CLEAN / "nagpra_notices.csv"))
    say("nagpra_notices rows / columns ON DISK", f"{len(nn)} / {len(nn[0])}")
    for k in ("institution_name", "institution_state", "mni_total_stated",
              "affiliated_entity_ids", "removal_states",
              "repatriation_eligible_date", "html_url"):
        say(f"  {k} filled", sum(1 for r in nn if (r.get(k) or "").strip() not in ("", "0")))
    br = list(rows(CLEAN / "nagpra_notice_entity_bridge.csv"))
    say("nagpra_notice_entity_bridge rows ON DISK", len(br))
    say("  notice-to-tribe links resolved to an entity",
        sum(1 for r in br if (r.get("tribe_id") or "").strip()))


# ----------------------------------------------------- native-owned businesses
def probe_nob():
    print("\nNATIVE-OWNED-BUSINESSES  (native_owned_businesses.csv)")
    b = list(rows(CLEAN / "native_owned_businesses.csv"))
    say("rows", len(b))
    for k in ("naics", "service_category_raw", "city", "certification_start",
              "certification_expiration", "business_entity_id",
              "ownership_percent", "source_last_updated"):
        say(f"{k} filled", sum(1 for r in b if (r.get(k) or "").strip()))
    import re
    fmt = collections.Counter()
    for r in b:
        v = (r.get("certification_expiration") or "").strip()
        if v:
            fmt[re.sub(r"\d", "#", v)] += 1
    say("distinct certification_expiration FORMATS", fmt.most_common())
    say("a cedar_uid column exists", "yes" if "cedar_uid" in b[0] else "NO")


# ---------------------------------------------------------- natural resources
def probe_resources():
    print("\nNATURAL-RESOURCES  (resource_revenue.csv)")
    r = list(rows(CLEAN / "resource_revenue.csv"))
    say("rows", len(r))
    say("aggregation_level distribution",
        collections.Counter(x["aggregation_level"] for x in r).most_common())
    for k in ("recipient_entity_name", "recipient_entity_id", "cedar_uid",
              "period_end", "payer_entity_name"):
        say(f"{k} filled", sum(1 for x in r if (x.get(k) or "").strip()))
    say("volume / production / price column",
        [c for c in r[0] if any(t in c.lower() for t in ("volume", "product", "price"))]
        or "none")


# ----------------------------------------------------------------- nonprofits
def probe_nonprofits():
    print("\nNONPROFITS  (np_orgs.csv)")
    n = list(rows(CLEAN / "np_orgs.csv"))
    say("rows", len(n))
    say("classification_ruling distribution",
        collections.Counter(r["classification_ruling"] for r in n).most_common())
    say("funnel_stage x classification_ruling (top 8)",
        collections.Counter((r["funnel_stage"], r["classification_ruling"])
                            for r in n).most_common(8))
    say("rows excluded_by_prior_ruling that still read UNRULED",
        sum(1 for r in n if r["funnel_stage"] == "excluded_by_prior_ruling"
            and r["classification_ruling"] == "UNRULED"))
    say("rows verified_strict that still read UNRULED",
        sum(1 for r in n if r["funnel_stage"] == "verified_strict"
            and r["classification_ruling"] == "UNRULED"))
    say("cedar_uid filled", sum(1 for r in n if (r.get("cedar_uid") or "").strip()))
    say("placename_risk_flag distribution",
        collections.Counter(r.get("placename_risk_flag", "") for r in n).most_common())


# -------------------------------------------------------------- subcontracting
def probe_sub():
    print("\nSUBCONTRACTING  (subawards.csv)")
    n = 0
    have = collections.Counter()
    dup = collections.Counter()
    for r in rows(CLEAN / "subawards.csv"):
        n += 1
        dup[r.get("duplicate_status", "")] += 1
        for k in ("description", "naics_title", "psc", "prime_award_id",
                  "prime_award_amount", "cedar_uid", "source_url"):
            if (r.get(k) or "").strip():
                have[k] += 1
    say("rows", n)
    say("description filled (omitted from sample)", have["description"])
    say("prime_award_id filled (omitted from sample)", have["prime_award_id"])
    say("prime_award_amount filled (omitted from sample)", have["prime_award_amount"])
    say("naics_title filled", have["naics_title"])
    say("psc filled", have["psc"])
    say("cedar_uid filled", have["cedar_uid"])
    say("duplicate_status distribution", dup.most_common())


# ------------------------------------------ contractors: PSC / description reach
def probe_psc_reach():
    """How much of prime_contracts could get PSC + award description WITHOUT a
    download. The archive zips are DELETED by design after filtering
    (code/114_pull_prime_archive.py :: release()), and a filesystem sweep on
    2026-09-01 found no FY*_All_Contracts_Full* anywhere on this machine - so
    the only local copies of those FPDS columns are the gapfill zips, and the
    reachable share is a measurement, not an assumption."""
    print("")
    print("CONTRACTORS - PSC / description reachability (no download)")
    import zipfile, io
    gap = set()
    rows_local = 0
    for fp in sorted(glob.glob(str(RAW / "contracts" / "usaspending_gapfill_2026-08-05" / "*.zip"))):
        try:
            z = zipfile.ZipFile(fp)
        except Exception:
            continue
        for n in z.namelist():
            if "PrimeAward" not in n:
                continue
            with z.open(n) as fh:
                for r in csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8",
                                                         errors="replace")):
                    rows_local += 1
                    k = (r.get("contract_award_unique_key") or "").strip()
                    if k:
                        gap.add(k)
    say("gapfill prime-award rows ON DISK (psc+description+naics ~100%)", rows_local)
    say("  distinct contract_award_unique_key", len(gap))

    bridge = {}
    for fp in sorted(glob.glob(str(RAW / "contracts" / "usaspending_archive_2026-08-07"
                                   / "filtered" / "FY*_ledger_rows.csv"))):
        for r in rows(Path(fp)):
            t = (r.get("contract_transaction_unique_key") or "").strip()
            a = (r.get("contract_award_unique_key") or "").strip()
            if t and a:
                bridge[t] = a
    say("archive bridge tx->award pairs", len(bridge))

    n = haskey = reach = 0
    for r in rows(CLEAN / "prime_contracts.csv"):
        n += 1
        t = (r.get("contract_transaction_unique_key") or "").strip()
        if not t:
            continue
        haskey += 1
        if bridge.get(t) in gap:
            reach += 1
    say("prime_contracts rows", n)
    say("  carrying a transaction key", haskey)
    say("  REACHABLE to a local psc/description row", f"{reach} ({reach/n:.1%})")
    say("  requiring a re-pull", f"{n - reach} ({(n-reach)/n:.1%})")


# ----------------------------------------------------------------------- deals
def probe_deals():
    print("\nDEALS  (deals_classified.csv)")
    d = list(rows(CLEAN / "deals_classified.csv"))
    say("rows", len(d))
    for k in ("Announced_Value_USD", "Value_Type", "Project_Total_Value_USD",
              "Source_1", "Description", "State", "cedar_uid",
              "Verification_Status", "Confidence"):
        say(f"{k} filled (omitted from sample)"
            if k not in ("Value_Type",) else f"{k} filled",
            sum(1 for r in d if (r.get(k) or "").strip()))
    say("Status distribution",
        collections.Counter(r["Status"] for r in d).most_common(8))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    print("Cedar Press - 841: what is missing, measured. Zero network requests.")
    for fn in (probe_entity, probe_contractors, probe_funding, probe_gaming,
               probe_legislation, probe_lobbying, probe_fedreg, probe_nagpra,
               probe_nob, probe_resources, probe_nonprofits, probe_sub,
               probe_deals, probe_psc_reach):
        global DS
        try:
            DS = fn.__name__.replace("probe_", "")
            fn()
        except Exception as exc:                      # a missing table is data
            print(f"  !! {fn.__name__}: {type(exc).__name__}: {exc}")
            OUT[fn.__name__ + "__error"] = f"{type(exc).__name__}: {exc}"
    if a.json:
        p = ROOT / "docs" / "WHAT_IS_MISSING.json"
        p.write_text(json.dumps(OUT, indent=2, default=str), encoding="utf-8")
        print(f"\nwrote {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
