#!/usr/bin/env python3
"""
Cedar Press - 40: Build the prime contracting transaction table (Dataset 2).

WHY THIS EXISTS
---------------
The coverage audit found Dataset 2 - a launch dataset - had NO clean
transaction table. Identifier maps derived from FPDS existed
(fpds_uei_cage_map, fpds_uei_edges) but the contract rows themselves had never
been built, so nothing downstream could chart prime contracting at all.

SOURCE AUTHORITY
----------------
`data/raw/esm_hci/ESM/clean/master prime file.dta` - Elijah's hand-checked
prime file, 617,142 rows, FY2000-2022 contiguous. This is the authoritative
source and it outranks any API pull.

Do NOT rebuild this from USAspending's /spending_by_award/ endpoint. That
endpoint returns CUMULATIVE award snapshots, not transactions, and summing it
inflates obligations by roughly 2.2x. The .dta is transaction-level and
already reconciled. FY2023+ is a separate forward-fill and must be pulled
transaction-level to match.

ATTRIBUTION
-----------
Rows are linked to Native entities ONLY through the Cedar Press identifier
ledger, on UEI first and CAGE second. No name matching happens here - name
matching is what produced the false attributions this project keeps finding.
A row whose UEI and CAGE are both unknown to the ledger is left unattributed
and counted, never guessed.

Reads  data/raw/esm_hci/ESM/clean/master prime file.dta
       data/clean/cedar_identifier_ledger_final.csv
       data/spine/cedar_entity_spine.csv        (via cedar_prime_panel)
Writes data/clean/prime_contracts.csv
       data/clean/prime_contracts_entity_year.csv
       review/prime_unlinked_top_vendors.csv
"""

import csv
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import pandas as pd

CEDAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CEDAR / "code"))

import cedar_prime_panel  # noqa: E402  (needs CEDAR on the path first)
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()

SRC = CEDAR / "data" / "raw" / "esm_hci" / "ESM" / "clean" / "master prime file.dta"


def _load_deflator():
    """BEA GDP implicit price deflator, rebased to the latest COMPLETE year."""
    p = CLEAN / "inflation_deflator.csv"
    if not p.exists():
        return {}
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return {int(r["year"]): float(r["factor_to_base"])
                for r in csv.DictReader(fh)}


DEFLATOR = _load_deflator()
FLOOR = 2000


def main():
    print("=== Cedar Press 40: build prime contracting table ===\n")

    # ---- ledger ----------------------------------------------------------
    by_uei, by_cage = {}, {}
    with open(CLEAN / "cedar_identifier_ledger_final.csv",
              encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            tier = (r.get("confidence_tier") or "").strip()
            if tier not in ("A", "B"):        # X and C never attribute
                continue
            ident = (r.get("identifier") or "").strip().upper()
            rec = (r.get("canonical_name", ""), r.get("tribe_id", ""), tier)
            if r.get("identifier_type") == "UEI":
                by_uei.setdefault(ident, rec)
            elif r.get("identifier_type") == "CAGE":
                by_cage.setdefault(ident, rec)
    print(f"ledger: {len(by_uei):,} UEIs, {len(by_cage):,} CAGEs (tiers A+B)")

    # ---- source ----------------------------------------------------------
    print(f"reading {SRC.name} ...")
    df = pd.read_stata(SRC)
    print(f"  {len(df):,} rows, FY{int(df.year.min())}-{int(df.year.max())}")

    df["awardee_uei"] = df["awardee_uei"].astype(str).str.strip().str.upper()
    df["parent_uei"] = df["parent_uei"].astype(str).str.strip().str.upper()
    df["cage_code"] = df["cage_code"].astype(str).str.strip().str.upper()

    out = []
    stats = Counter()
    unlinked = defaultdict(lambda: [0.0, 0, ""])

    for row in df.itertuples(index=False):
        # Match order is a claim about evidence strength, not convenience.
        # The awardee's own UEI identifies the contracting party outright.
        # CAGE is equally direct. The PARENT uei only tells us who owns the
        # awardee, so it attributes the row to the parent's entity - correct
        # for roll-up, but recorded as a distinct, weaker method so it can be
        # audited or withdrawn separately.
        hit = by_uei.get(row.awardee_uei)
        method = "uei_exact"
        if not hit:
            hit = by_cage.get(row.cage_code)
            method = "cage_exact"
        if not hit:
            hit = by_uei.get(row.parent_uei)
            method = "parent_uei"
        if not hit:
            method = None

        if hit:
            canon, tid, tier = hit
            stats[f"linked:{method}:{tier}"] += 1
        else:
            canon = tid = tier = ""
            stats["unlinked"] += 1
            k = row.awardee_name
            unlinked[k][0] += float(row.total_obligations or 0)
            unlinked[k][1] += 1
            unlinked[k][2] = row.awardee_uei

        y = int(row.year)
        out.append({
            "contract_number": row.contract_number,
            # THE .dta ENCODES "STANDALONE" AS SELF-PARENT, AND CEDAR MUST
            # NOT SHIP THAT AS A VEHICLE REFERENCE. Measured in the raw
            # source: 216,882 of 617,142 rows carry
            # parent_contract_number == contract_number and NOT ONE is blank.
            # A column where "no parent" never occurs and self-parent occurs
            # on 35.1% of rows is a column where self-parent IS "no parent" -
            # and the FPDS archive rows carry a genuine blank on 31.2%, the
            # same population at the same rate under the honest encoding.
            # Codex, PR #29 finding 4. See code/1076_clear_self_parent_piid.py.
            "parent_contract_number": (
                "" if (row.parent_contract_number or "") ==
                      (row.contract_number or "")
                else row.parent_contract_number),
            "fiscal_year": y,
            "pre_2000_flag": int(y < FLOOR),
            "awardee_name": row.awardee_name,
            "awardee_uei": row.awardee_uei if row.awardee_uei != "NAN" else "",
            "cage_code": row.cage_code if row.cage_code != "NAN" else "",
            "parent_name": row.parent_name,
            "parent_uei": row.parent_uei if row.parent_uei != "NAN" else "",
            # NOMINAL IS ALWAYS PRIMARY. REAL IS ALWAYS DERIVED AND LABELLED.
            #
            # Elijah, 2026-08-06: "we should have nominally what was reported
            # and then we can also have a switch or another column for
            # inflation adjustment too."
            #
            # `total_obligations` is exactly what the federal record reported -
            # never replaced, never silently adjusted. The real columns sit
            # beside it carrying their base year IN THE COLUMN NAME, because a
            # constant-dollar figure whose base year is not stated is unusable
            # and a figure whose base year has to be looked up gets misquoted.
            #
            # BASE YEAR IS 2025, NOT 2022.
            #
            # Elijah, 2026-08-06: "you should use a more up to date inflation, i
            # worked on that data in like 2023 lol, everything should be in 2026
            # dollars no?"
            #
            # Right that 2022 was stale - his `inflfac` came from the 2023
            # build. Rebased on the BEA GDP implicit price deflator (NIPA Table
            # 1.1.9), pulled fresh today.
            #
            # 2025 rather than 2026 because **2026 is not a complete year**, so
            # BEA publishes no annual index for it. Deflating to a base year
            # that does not exist yet would mean forecasting the index and
            # presenting the forecast as a measurement. 2025 is the most recent
            # year that is actually observed.
            #
            # The old 2022-dollar columns are DROPPED. Elijah: "2022 columns
            # dont need to be kept". Carrying two constant-dollar bases invites
            # someone to quote the wrong one, and the nominal column is what
            # makes any base reproducible anyway.
            "total_obligations": row.total_obligations,
            "total_award_value": row.total_award_value,
            "total_obligations_real2025": round(
                float(row.total_obligations or 0) * DEFLATOR.get(int(row.year), 1.0), 2),
            "total_award_value_real2025": round(
                float(row.total_award_value or 0) * DEFLATOR.get(int(row.year), 1.0), 2),
            "deflator_factor_2025": DEFLATOR.get(int(row.year), ""),
            "inflation_base_year": 2025,
            "setaside": row.setaside,
            # WHY EVERY ONE OF THESE IS PREFIXED `reported_`.
            #
            # Elijah, 2026-08-06: "the fields arent always reliable which is why
            # our field is the best since we are linking to native entities but
            # we can say if the contract reported being an indian business".
            #
            # Exactly the right framing, and the naming has to carry it. The
            # set-aside is SELF-REPORTED by the contracting office and the
            # vendor. `is_8a` asserts a fact about the firm; `reported_8a`
            # states what the record claims, which is all FPDS can support.
            #
            # Cedar Press's `tribe_id` is the DETERMINED field - built from
            # hand rulings, firm-declared FPDS parentage, and retrieved
            # ownership pages. Where the two disagree, ours is the authority
            # and theirs is the claim. That is the product.
            #
            # NATIVE PREFERENCE PROGRAMMES AS FLAGS, NOT AS SEPARATE DATASETS.
            #
            # Elijah, 2026-08-06: "8a participation should just sort of be
            # within our prime dataset same with buy indian". Right - these are
            # ATTRIBUTES of a contract, not populations. Cutting them into
            # separate files would duplicate rows and let the copies drift.
            #
            # The three Native-specific programmes are legally distinct:
            #   8(a)             SBA business development, 13 CFR 124. Open to
            #                    tribes, ANCs and NHOs, and the channel that
            #                    carries almost all Native federal work.
            #   Buy Indian       25 U.S.C. 47, Interior and IHS only.
            #   Indian Business  a separate FPDS set-aside code.
            #
            # The measured proportions are themselves a finding worth
            # publishing: 8(a) is $74.41B while Buy Indian and Indian Business
            # TOGETHER are $1.38B - 0.5% of Native prime dollars. The
            # Native-specific set-asides are not how Native firms win federal
            # work.
            "reported_8a": int(row.setaside == "8(a)"),
            "reported_buy_indian": int(row.setaside == "Buy Indian"),
            "reported_indian_business": int(row.setaside == "Indian Business"),
            "reported_native_preference": int(row.setaside in
                                          ("8(a)", "Buy Indian", "Indian Business")),
            "setaside_reported": int(row.setaside != "None reported"),
            "extent_competed": row.extent_competed,
            "funding_agency": row.funding_agency,
            "sector": row.sector,
            "supersector": row.supersector,
            "defense": row.defense,
            "recipient_city_name": row.recipient_city_name,
            "recipient_state_code": row.recipient_state_code,
            "place_of_perform_city": row.primary_place_of_perform_city,
            "place_of_perform_state": row.primary_place_of_perform_sta,
            "tribe_id": tid,
            "canonical_name": canon,
            "attribution_method": method or "unattributed",
            "confidence_tier": tier or "C",
            "attributed_flag": int(bool(hit)),
            "source_file": SRC.name,
            "source_authority": "Elijah hand-checked master prime file",
            "built_date": TODAY,
        })

    fields = list(out[0].keys())
    p = CLEAN / "prime_contracts.csv"
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(out)
    print(f"\nwrote {p.relative_to(CEDAR)}  ({len(out):,} rows)")

    print("\nattribution")
    for k, v in stats.most_common():
        print(f"  {v:9,}  {k}")
    linked = sum(v for k, v in stats.items() if k.startswith("linked"))
    print(f"  {linked/len(out)*100:.1f}% of rows linked to a Native entity")

    obl_all = sum(float(r["total_obligations"] or 0) for r in out)
    obl_lnk = sum(float(r["total_obligations"] or 0) for r in out
                  if r["attributed_flag"])
    print(f"  obligations linked: ${obl_lnk/1e9:,.1f}B of ${obl_all/1e9:,.1f}B "
          f"({obl_lnk/obl_all*100:.1f}%)")

    # ---- entity-year panel ----------------------------------------------
    #
    # THE GRAIN IS (tribe_id, fiscal_year) AND NOTHING ELSE.
    #
    # This block used to key the panel on (tribe_id, canonical_name,
    # fiscal_year, confidence_tier), so one entity-year held up to three rows -
    # measured 2026-08-29 at 8,464 rows over 6,713 entity-years, 1,635 keys
    # colliding. The file is NAMED entity-year and declares `tribe_id` as a key
    # column, so a buyer merging any other entity-year table onto this one
    # FANNED OUT and multiplied their own dollars. `131` and `114` carried
    # copies of the same key, so the aggregation now lives in ONE module and
    # all three call it. See `cedar_prime_panel` for the evidence that
    # collapsing is lossless (both keys sum to the identical cent) and for why
    # `confidence_tier` survives as COLUMNS rather than as rows.
    prows, pstats = cedar_prime_panel.aggregate(
        out, TODAY,
        spine_names=cedar_prime_panel.spine_canonical_names(),
        uid_of=cedar_prime_panel.existing_uids(
            CLEAN / "prime_contracts_entity_year.csv"))
    cedar_prime_panel.assert_grain(prows)
    cedar_prime_panel.assert_conservation(
        prows, sum(float(r["total_obligations"] or 0) for r in out
                   if r["attributed_flag"] and r["tribe_id"]
                   and str(r["fiscal_year"]).strip()))
    p2 = cedar_prime_panel.write_panel(
        prows, CLEAN / "prime_contracts_entity_year.csv")
    print(f"wrote {p2.relative_to(CEDAR)}  ({len(prows):,} rows, "
          f"{len({r['tribe_id'] for r in prows}):,} entities, "
          f"one row per (tribe_id, fiscal_year) - verified)")
    cedar_prime_panel.print_stats(pstats)
    _xp, _xn = cedar_prime_panel.write_excluded(pstats, TODAY)
    print(f"wrote {_xp.relative_to(CEDAR)}  ({_xn:,} named exclusions - every (awardee_uei, awardee_name, fiscal_year, reason) that entered no entity total)")

    # ---- what we are missing --------------------------------------------
    top = sorted(unlinked.items(), key=lambda kv: -kv[1][0])[:400]
    p3 = REVIEW / "prime_unlinked_top_vendors.csv"
    with open(p3, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["awardee_name", "awardee_uei", "obligations_usd",
                    "n_rows", "note"])
        for nm, (v, n, uei) in top:
            w.writerow([nm, uei, round(v, 2), n,
                        "Unlinked to any ledger identifier - candidate, NOT a "
                        "Native attribution"])
    print(f"wrote {p3.relative_to(CEDAR)}  (top {len(top):,} unlinked vendors)")

    print("\nFY coverage of the built table")
    yr = Counter(r["fiscal_year"] for r in out)
    lo, hi = min(yr), max(yr)
    gaps = [y for y in range(lo, hi + 1) if not yr.get(y)]
    print(f"  {lo}-{hi}, interior gaps: {gaps if gaps else 'none'}")
    print(f"  FY2023-2026 absent by construction - forward-fill is a separate "
          f"transaction-level pull.")


if __name__ == "__main__":
    main()
