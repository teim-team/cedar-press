#!/usr/bin/env python3
"""
Cedar Press - 583: FACT-CHECK and finish the LABOR surface of the gaming
collection (DOL Form 5500 + OSHA ITA 300A).  WORKSTREAM INT-1 (LABOR).

NO NETWORK.  Everything read here is already on disk.

WHY THIS SCRIPT EXISTS
----------------------
`docs/datasets/gaming_sources.md` said of Form 5500: **"PROMOTION OWED. Two
rulings block it."**  That line is STALE.  Measured 2026-09-01:

    data/staging/gaming_employment_form5500_staged.csv     2,046 rows
    data/clean/gaming_employment_observations.csv           1,975 FORM5500 rows
                                                               71 refused
    data/staging/gaming_employment_osha_tribe_staged.csv      502 rows
    data/clean/gaming_employment_observations.csv             502 OSHA_TRIBE rows

Both staged files are ALREADY MERGED.  `cedar_domain.MeasurementType` already
carries `FORM5500_ACTIVE_PARTICIPANTS` (added by 156) and
`OSHA_TRIBE_LEVEL_REPORTED` (added by 157), each with a full definition.  The 71
unpromoted Form 5500 rows are the correct refusals - every one of them is a
NON-TRIBAL commercial casino that a name match had keyed to a tribe.

So the job left is not promotion.  It is the FACT-CHECK that was never run over
what promotion already wrote, plus the review backlog nobody adjudicated.

WHAT THE FACT-CHECK FOUND, AND THE ONE DEFECT IT FIXES
-------------------------------------------------------
Script 157's own header records that unguarded containment resolved
`CAESARS PALACE LAS VEGAS`, `BALLY'S LAS VEGAS` and `Circus Circus Las Vegas`
to **Las Vegas** - the Las Vegas Paiute Tribe, `TRBF-LSVGAS-00` - and 157 guarded
against it.  **Script 156 took the Form 5500 rows from 4wheeler's resolver, which
has no such guard, and the same defect went into `data/clean/` unnoticed.**

`TRBF-LSVGAS-00` carries 25 Form 5500 rows.  Six are the tribe.  Nineteen are
four unrelated commercial Las Vegas employers:

    WESTGATE LAS VEGAS RESORT & CASINO                    11 rows   454-809
    GAMING VENTURES OF LAS VEGAS, INC(.)                   6 rows   105-144
    LAS VEGAS GAMING, INC.                                 1 row     34
    BARDEN NEVADA GAMING, LLC DBA FITZGERALDS LAS VEGAS    1 row    275
    ------------------------------------------------------------
    LAS VEGAS PAIUTE TRIBE  (the actual tribe)             6 rows   204-343

The tribe's own filings run 204-343.  Westgate's run 454-809.  Left in place a
buyer reads the Las Vegas Paiute Tribe's workforce as tripling in 2015 and
collapsing after.  These 19 are removed here, for exactly the reason the other
71 were never promoted, and written to `review/` with the diagnosis.

THE TEST THAT ISOLATED THEM, so it can be re-run on any future labour source:

    a row is EXPOSED when the sponsor/company text carries NO governmental word
    (tribe / nation / band / community / pueblo / rancheria / indians / village)
    AND no facility in `gaming_facilities.csv` belonging to that tribe has its
    distinctive name tokens present in the text.

Run over all 1,975 promoted Form 5500 rows the test returns 114, of which 95 are
correct enterprise brands that Cedar's facility table simply spells differently
(GILA RIVER GAMING ENTERPRISES, PCI GAMING AUTHORITY, SENECA GAMING CORPORATION,
RED LAKE GAMING ENTERPRISES, OSAGE CASINOS ...).  The remaining 19 are the
`TRBF-LSVGAS-00` block above.  The test is a PROMPT, not a verdict, which is why
its full output is written to review rather than acted on wholesale.

THE 160 NON-COMMERCIAL HOLDS IN review/osha_gambling_unresolved_2026-08-26.csv
------------------------------------------------------------------------------
That file holds 4,560 OSHA ITA filings script 157 did not attach.  2,551 are
`blocked_commercial` (Boyd, Caesars, MGM, IGT, Station, state lotteries) and
1,849 are `unresolved` with no spine match - overwhelmingly commercial too, and
both sets stay refused.  **160 are neither, and those are the ones nobody looked
at.**  They are adjudicated here under two rules, both of which require evidence
that is IN THE FILING or in Cedar's own curated facility table - never outside
knowledge:

  RULE O1  the filing's own text contains a spine entity's name AND a
           governmental word AND the state agrees.
           ("Mississippi Band of Choctaw Indinas" - the typo is the source's -
            "Kalispel Tribal Economic Authority", "Rincon Band of Luiseno
            Indians", "Forest County Potawatomi Community".)

  RULE O2  the filed establishment or company name IS a facility name in
           `gaming_facilities.csv`, for exactly one tribe, in that state.
           (This is the same pass-B evidence 157 used for 345 of its 502 rows.)

Anything the two rules do not reach is HELD, with the reason recorded per row.
The governmental-word / facility-corroboration requirement is what keeps
"Sahara Las Vegas", "Harrah's Las Vegas" and "Hotspur Resorts / Rampart Casino"
(which containment offers as the Native Village of Rampart, Alaska) out.

usage:
    py -3 code/583_labor_surface_factcheck.py            # measure, write review
    py -3 code/583_labor_surface_factcheck.py --apply    # + repair + promote
"""
import csv
import re
import sys
import hashlib
import shutil
import collections
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "clean"
STAGING = ROOT / "data" / "staging"
SPINE = ROOT / "data" / "spine"
REVIEW = ROOT / "review"
RAW_ITA = ROOT / "data" / "raw" / "external" / "osha_ita"

EMP = CLEAN / "gaming_employment_observations.csv"
FACS = CLEAN / "gaming_facilities.csv"
SPINE_F = SPINE / "cedar_entity_spine.csv"
HOLDS = REVIEW / "osha_gambling_unresolved_2026-08-26.csv"
POOL = RAW_ITA / "_gambling_naics_rows.csv"

TODAY = "2026-09-01"
BY = "583_labor_surface_factcheck.py"

# A governmental word in the filing is the corroborator that a name match on a
# US place name cannot fake. "Las Vegas Paiute Tribe" has one; "Sahara Las
# Vegas" does not, and that single predicate is the whole Las Vegas guard.
GOV_WORDS = set(
    "tribe tribes tribal nation nations band bands pueblo rancheria community "
    "indians indian village villages nsn reservation keetoowah".split())

# Tokens that carry no identity and must never be the thing a match rests on.
NOISE = set(
    "of the and a in at for inc llc l p lp corp corporation co ltd dba d b "
    "casino casinos resort resorts hotel hotels gaming game games enterprise "
    "enterprises authority board group holdings development commission plan "
    "benefit employees employee retirement welfare savings trust k 401 bingo "
    "travel plaza center centre lodge spa".split())


# Only these spine classes can own a casino, so only these may receive an OSHA
# gaming filing. Not a hand-written opinion: it is the set of entity_class
# values that actually own a row in gaming_facilities.csv (739 / 43 / 3).
# Without it the subset test hands "Yakama Nation Legends Casino Hotel" to
# BIE-YKMNTN-00, the Yakama Nation TRIBAL SCHOOL, and "Harrah's Cherokee" to
# CEDAR-ENT-000061, an individually Native-owned business called Cherokee
# Enterprises Inc - both of which beat the real tribe on uniqueness because the
# real tribe's spine name carries an extra token ("Confederated Yakama",
# "Eastern Cherokee") that the filing does not print.
CAN_OWN_A_CASINO = {
    "Federally recognized tribe",
    "Federal-level constituency entity",
    "Federally recognized Alaska Native Village",
}


def rd(p):
    with open(p, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def wr(p, rows, fields=None):
    if not rows:
        return 0
    fields = fields or list(rows[0].keys())
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def norm(s):
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def distinctive(s):
    return set(norm(s).split()) - NOISE - GOV_WORDS


# ---------------------------------------------------------------- fact check

def exposure_test(emp, spine, facs_by_tribe):
    """Rows whose tribe attribution rests on nothing but a name token.

    Returns (exposed_rows, per_sponsor_counter). A row PASSES if either
    corroborator holds:
      * the filing text itself carries a governmental word, or
      * a facility Cedar already attributes to that tribe has its distinctive
        name tokens present in the filing text.
    """
    exposed, seen = [], collections.Counter()
    for r in emp:
        if r["measurement_type"] != "FORM5500_ACTIVE_PARTICIPANTS":
            continue
        text = norm(r["sponsor_name"]) + " " + norm(r["plan_name"])
        toks = set(text.split())
        if toks & GOV_WORDS:
            continue
        corroborated = False
        for f in facs_by_tribe.get(r["tribe_id"], []):
            ft = distinctive(f["facility_name"])
            if ft and ft <= toks:
                corroborated = True
                break
        if corroborated:
            continue
        s = spine.get(r["tribe_id"], {})
        exposed.append(r)
        seen[(r["tribe_id"], s.get("canonical_name", "?"),
              r["sponsor_name"], r["sponsor_state"])] += 1
    return exposed, seen


# The four sponsors below are the exposure test's true positives, confirmed one
# at a time against the filing itself. Each is a NON-TRIBAL commercial Las Vegas
# employer that reached TRBF-LSVGAS-00 because the tribe's spine handle is the
# bare US settlement name "Las Vegas". None of the four is a Cedar facility and
# none names a tribal government. They are the same class of row as the 71 the
# Form 5500 promotion already refused.
LSVGAS_REFUSALS = {
    "WESTGATE LAS VEGAS RESORT & CASINO",
    "GAMING VENTURES OF LAS VEGAS, INC",
    "GAMING VENTURES OF LAS VEGAS, INC.",
    "LAS VEGAS GAMING, INC.",
    "BARDEN NEVADA GAMING, LLC DBA FITZGERALDS LAS VEGAS",
}

# Correctly keyed to the right entity, but the plan sponsor is not a gaming
# employer and Cedar holds no gaming facility for it. Flagged in place, never
# removed: the attribution is right and the row is a real filing.
NON_GAMING_SPONSORS = {
    "SITNASUAK NATIVE CORPORATION",
    "BERING STRAITS DEVELOPMENT COMPANY",
}
NON_GAMING_FLAG = "SPONSOR_IS_NOT_A_GAMING_EMPLOYER_NO_CEDAR_FACILITY"


# ------------------------------------------------------------- adjudication

def build_matchers(spine, facs):
    """Two evidence indexes. Neither reaches outside the filing."""
    # O1: (frozenset of distinctive tokens, state) -> tribe_id.
    # A SUBSET test, not a substring test, because a filing writes the tribe's
    # name the long way round - the spine says "Mississippi Choctaw" and the
    # 300A says "Mississippi Band of Choctaw Indinas" (the typo is OSHA's).
    # Uniqueness within the state plus a governmental word is what keeps the
    # looser test safe.
    names = []
    for s in spine.values():
        if s["entity_class"] not in CAN_OWN_A_CASINO:
            continue
        cand = [s["canonical_name"]] + [
            a for a in (s.get("aliases") or "").split("|") if a.strip()]
        for n in cand:
            d = distinctive(n)
            if d:
                names.append((frozenset(d), s["tribe_id"], s["state"], norm(n)))
    # O2: (normalised facility name, state) -> {tribe_id}, and the same name
    # nationally, so a border property filed from the other side of the line
    # (Paradise Casino, Yuma AZ, owned by a tribe Cedar states is in CA) is a
    # flagged match rather than a silent miss.
    brands = collections.defaultdict(set)
    brands_any = collections.defaultdict(set)
    for f in facs:
        d = frozenset(distinctive(f["facility_name"]))
        if not d or not f["tribe_id"]:
            continue
        brands[(d, f["state"])].add(f["tribe_id"])
        brands_any[d].add(f["tribe_id"])
    return names, (brands, brands_any)


def adjudicate(row, names, brand_idx):
    """-> (tribe_id, rule, evidence, state_mismatch) or (None, ...)."""
    brands, brands_any = brand_idx
    company, est = row["company_name"], row["establishment_name"]
    state = row["state"]
    text = norm(company) + " | " + norm(est)
    toks = set(text.replace("|", " ").split())

    # RULE O2 first, exactly as 157 ordered its passes: OSHA files a BRAND, and
    # Cedar's curated facility table is the only bridge from brand to tribe.
    for fld, val in (("establishment_name", est), ("company_name", company)):
        hit = brands.get((frozenset(distinctive(val)), state))
        if hit and len(hit) == 1:
            return (next(iter(hit)), "O2_cedar_facility_brand_exact",
                    f"{fld}=\"{val}\" carries the same distinctive name "
                    f"tokens as a gaming_facilities.facility_name belonging "
                    f"to exactly one tribe in {state}", "0")

    # RULE O1: the filing names a tribal government, in this state.
    if toks & GOV_WORDS:
        got = {}
        for dtoks, tid, st, shown in names:
            if st == state and dtoks <= toks:
                # keep the longest matching name as the evidence string
                if len(shown) > len(got.get(tid, "")):
                    got[tid] = shown
        if len(got) == 1:
            tid, matched = next(iter(got.items()))
            return (tid, "O1_filing_names_the_government",
                    f"every distinctive token of spine name \"{matched}\" is "
                    f"present in the filing, the filing carries a governmental "
                    f"word, state {state} agrees, and no other spine entity in "
                    f"{state} matches", "0")
        if len(got) > 1:
            return (None, None,
                    "HELD ambiguous: filing text matches "
                    + ", ".join(sorted(got)), "")

    # RULE O2b: the brand is a Cedar facility name found in exactly one tribe
    # NATIONALLY, but that tribe's spine state differs from the filing state.
    # Recorded as a match with state_mismatch_flag=1, the same way the Form
    # 5500 layer records Rosebud filing from NE and Catawba from NC. A border
    # property is a real thing; a silent drop is not.
    for fld, val in (("establishment_name", est), ("company_name", company)):
        hit = brands_any.get(frozenset(distinctive(val)))
        # The governmental word is REQUIRED here and not merely preferred.
        # Without it "Double Eagle Hotel & Casino", Cripple Creek CO, matches
        # Cedar's Double Eagle Casino in Chewelah WA and lands a commercial
        # Colorado property on the Spokane Tribe of Indians.
        if hit and len(hit) == 1 and (toks & GOV_WORDS):
            return (next(iter(hit)), "O2b_cedar_facility_brand_state_mismatch",
                    f"{fld}=\"{val}\" is gaming_facilities.facility_name for "
                    f"exactly one tribe nationally; filed in {state}, spine "
                    f"state differs - flagged, not silently accepted", "1")

    if not (toks & GOV_WORDS):
        return (None, None,
                "HELD no governmental word in the filing and no Cedar facility "
                "brand - a bare place-name match is what put Westgate Las Vegas "
                "on the Las Vegas Paiute Tribe", "")
    return (None, None,
            "HELD names a government but no spine entity in this state", "")


def obs_id(r):
    """Stable id derived from THE ROW, never from a counter.

    `293`/`284` class 7 is "an id minted from OUTSIDE the row - a process hash,
    a rank or a sequence". A counter is exactly that: insert one filing earlier
    in the source and every id after it shifts, so a re-run silently renumbers
    rows a consumer has already joined against. The digest is over the natural
    key OSHA itself provides - establishment, state, year, filed headcount - so
    the same filing gets the same id in every build, in any order.
    """
    key = "|".join((r["establishment_name"].strip().lower(),
                    r["company_name"].strip().lower(), r["state"],
                    r["year"], str(r["annual_average_employees"])))
    return "EMP-OSHATRIBE-A" + hashlib.sha1(
        key.encode("utf-8")).hexdigest()[:10].upper()


OSHA_NOTE = (
    "The ESTABLISHMENT'S OWN FILED annual average employees, rolled to the "
    "tribe that owns it. It is a headcount, not an FTE and not a payroll. OSHA "
    "ITA coverage is NOT a census: electronic submission is required only of "
    "establishments above size thresholds in covered industries, and compliance "
    "is uneven. AN ESTABLISHMENT ABSENT FROM ITA IS NOT AN ESTABLISHMENT WITH "
    "ZERO EMPLOYEES - it is an establishment that did not file. The set of "
    "establishments filing under one tribe CHANGES YEAR TO YEAR, so a tribe-year "
    "SUM of these rows is not a consistent panel and must never be differenced "
    "as if it were.")


def main():
    apply = "--apply" in sys.argv
    emp = rd(EMP)
    facs = rd(FACS)
    spine = {r["tribe_id"]: r for r in rd(SPINE_F)}
    facs_by_tribe = collections.defaultdict(list)
    for f in facs:
        facs_by_tribe[f["tribe_id"]].append(f)

    print(f"gaming_employment_observations.csv: {len(emp):,} rows")
    mt = collections.Counter(r["measurement_type"] for r in emp)
    for k, v in mt.most_common():
        print(f"   {v:>6}  {k}")

    # -------- 1. staged vs clean: is anything actually unpromoted? ----------
    print("\n[1] STAGED vs CLEAN")
    for name, path, mtype in (
            ("form5500", STAGING / "gaming_employment_form5500_staged.csv",
             "FORM5500_ACTIVE_PARTICIPANTS"),
            ("osha_tribe", STAGING / "gaming_employment_osha_tribe_staged.csv",
             "OSHA_TRIBE_LEVEL_REPORTED")):
        st = rd(path)
        # natural key, because observation_ids were renumbered after promotion
        if mtype.startswith("FORM"):
            def k(r):
                return (r["sponsor_name"].strip().lower(), r["year"],
                        str(r["employment"]))
        else:
            def k(r):
                return (r["establishment_name"].strip().lower(), r["state"],
                        r["year"])
        have = {k(r) for r in emp if r["measurement_type"] == mtype}
        miss = [r for r in st if k(r) not in have]
        print(f"   {name}: staged {len(st):,}  in clean "
              f"{sum(1 for r in emp if r['measurement_type'] == mtype):,}  "
              f"NOT PROMOTED {len(miss):,}")

    # -------- 2. keying: does every tribe_id resolve, by more than a name? --
    print("\n[2] KEYING")
    tids = {r["tribe_id"] for r in emp if r["tribe_id"]}
    orphan = sorted(tids - set(spine))
    print(f"   distinct tribe_id {len(tids)}   unresolvable in spine "
          f"{len(orphan)} {orphan[:5]}")

    exposed, per_sponsor = exposure_test(emp, spine, facs_by_tribe)
    print(f"   exposure test (no gov word AND no facility corroboration): "
          f"{len(exposed)} rows over {len(per_sponsor)} sponsors")
    rows = [{"tribe_id": t, "spine_name": n, "sponsor_name": sp,
             "sponsor_state": ss, "n_rows": c,
             "disposition": ("REMOVE_commercial_non_tribal"
                             if sp in LSVGAS_REFUSALS else
                             ("FLAG_sponsor_not_a_gaming_employer"
                              if sp in NON_GAMING_SPONSORS else
                              "KEEP_enterprise_brand_cedar_spells_differently"))}
            for (t, n, sp, ss), c in sorted(per_sponsor.items(),
                                            key=lambda x: -x[1])]
    wr(REVIEW / f"gaming_employment_exposure_{TODAY}.csv", rows)
    print(f"   -> review/gaming_employment_exposure_{TODAY}.csv")

    bad = [r for r in emp
           if r["measurement_type"] == "FORM5500_ACTIVE_PARTICIPANTS"
           and r["tribe_id"] == "TRBF-LSVGAS-00"
           and r["sponsor_name"] in LSVGAS_REFUSALS]
    print(f"   TRBF-LSVGAS-00 commercial misattributions: {len(bad)} rows")

    # -------- 3. double counting -------------------------------------------
    print("\n[3] DOUBLE COUNTING")
    dup = collections.Counter(
        (r["measurement_type"], r["tribe_id"], r["year"],
         (r["sponsor_name"] or r["establishment_name"]).strip().lower(),
         r["employment"]) for r in emp)
    print(f"   exact duplicate (type,tribe,year,name,value): "
          f"{sum(v - 1 for v in dup.values() if v > 1)}")
    both = collections.defaultdict(set)
    for r in emp:
        both[(r["tribe_id"], r["year"])].add(r["measurement_type"])
    multi = sum(1 for v in both.values() if len(v) > 1)
    print(f"   tribe-years carrying MORE THAN ONE measurement_type: {multi}"
          f"  <- these are the summing trap; see the codebook block")
    aff = sum(1 for r in emp if r.get("already_facility_attached") == "1")
    print(f"   OSHA tribe-level rows that are the SAME 300A filing as a "
          f"facility-grain row: {aff}")

    # -------- 4. magnitudes -------------------------------------------------
    print("\n[4] MAGNITUDES")
    f5, osh = {}, collections.Counter()
    for r in emp:
        try:
            v = float(r["employment"])
        except (TypeError, ValueError):
            continue
        key = (r["tribe_id"], r["year"])
        if r["measurement_type"] == "FORM5500_ACTIVE_PARTICIPANTS":
            f5[key] = max(f5.get(key, 0.0), v)
        elif r["measurement_type"] == "OSHA_TRIBE_LEVEL_REPORTED":
            osh[key] += v
    pairs = [(f5[k] / osh[k], k) for k in set(f5) & set(osh) if osh[k] > 0]
    pairs.sort()
    if pairs:
        med = pairs[len(pairs) // 2][0]
        print(f"   {len(pairs)} overlapping tribe-years, median "
              f"F5500/OSHA ratio {med:.2f}")
        wild = [p for p in pairs if p[0] > 3]
        print(f"   ratio > 3 on {len(wild)} tribe-years - NOT a defect: the "
              f"5500 covers the whole enterprise, ITA only the establishments "
              f"that filed. Worst: "
              + ", ".join(f"{k[0]} {k[1]} x{r:.0f}" for r, k in wild[::-1][:4]))
    fac_n = collections.Counter(f["tribe_id"] for f in facs)
    est = collections.defaultdict(set)
    for r in emp:
        if r["measurement_type"] == "OSHA_TRIBE_LEVEL_REPORTED":
            est[(r["tribe_id"], r["year"])].add(
                r["establishment_name"].strip().lower())
    over = [(t, y, len(v), fac_n.get(t, 0))
            for (t, y), v in est.items() if len(v) > fac_n.get(t, 0)]
    print(f"   tribe-years with more OSHA establishments than Cedar "
          f"facilities: {len(over)} "
          + ", ".join(f"{t} {y} {a}>{b}" for t, y, a, b in sorted(over)[:4]))

    # -------- 5. adjudicate the review holds --------------------------------
    print("\n[5] REVIEW BACKLOG")
    holds = rd(HOLDS)
    v = collections.Counter(r["verdict"] for r in holds)
    print(f"   {len(holds):,} filings held by 157: " +
          ", ".join(f"{k} {n}" for k, n in v.most_common()))
    looked_at = [r for r in holds
                 if r["verdict"] not in ("blocked_commercial", "unresolved")]
    print(f"   {len(looked_at)} are NEITHER commercial NOR unmatched - "
          f"the set nobody adjudicated")

    names, brands = build_matchers(spine, facs)
    pool = {}
    for p in rd(POOL):
        pool[(p["company_name"], p["establishment_name"], p["state"],
              p["year_filing_for"], p["annual_average_employees"])] = p

    promoted, held = [], []
    have = {(r["establishment_name"].strip().lower(), r["state"], r["year"])
            for r in emp
            if r["measurement_type"] == "OSHA_TRIBE_LEVEL_REPORTED"}
    for r in looked_at:
        tid, rule, ev, smm = adjudicate(r, names, brands)
        if not tid:
            held.append({**r, "adjudication": ev})
            continue
        key = (r["establishment_name"].strip().lower(), r["state"], r["year"])
        if key in have:
            held.append({**r, "adjudication":
                         "ALREADY PRESENT in gaming_employment_observations"})
            continue
        raw = pool.get((r["company_name"], r["establishment_name"], r["state"],
                        r["year"], r["annual_average_employees"]), {})
        hours = raw.get("total_hours_worked") or ""
        try:
            fte = round(float(hours) / 2080.0, 1) if hours else ""
            hpe = (round(float(hours) / float(r["annual_average_employees"]))
                   if hours and float(r["annual_average_employees"]) else "")
        except (TypeError, ValueError, ZeroDivisionError):
            fte, hpe = "", ""
        promoted.append({
            "observation_id": obs_id(r),
            "facility_id": "",
            "tribe_id": tid,
            "entity_id": tid,
            "entity_level": "tribe",
            "geographic_level": "establishment_rolled_to_tribe",
            "year": r["year"],
            "employment": r["annual_average_employees"],
            "measurement_type": "OSHA_TRIBE_LEVEL_REPORTED",
            "measurement_type_status": "ACTIVE in cedar_domain.MeasurementType",
            "total_hours_worked": hours,
            "fte_2080": fte,
            "fte_divisor": "2080" if hours else "",
            "fte_is_derived_not_filed": "1" if hours else "",
            "hours_per_employee": hpe,
            "hours_per_employee_plausible": (
                "1" if hpe != "" and 200 <= hpe <= 5000 else
                ("0" if hpe != "" else "")),
            "establishment_name": r["establishment_name"],
            "company_name": r["company_name"],
            "establishment_id": raw.get("establishment_id", ""),
            "ein": raw.get("ein", ""),
            "street_address": raw.get("street_address", ""),
            "city": raw.get("city", ""),
            "state": r["state"],
            "naics": r["naics"],
            "name_in_source": r["establishment_name"],
            "match_rule": rule,
            "matched_on_field": rule,
            "state_mismatch_flag": smm,
            "source_url": "https://www.osha.gov/itadata",
            "source_name": ("OSHA Injury Tracking Application, Form 300A "
                            "establishment summary"),
            "source_record": raw.get("_file", ""),
            "source_quote": (
                f'company_name="{r["company_name"]}"; '
                f'establishment_name="{r["establishment_name"]}"; '
                f'city="{raw.get("city", "")}"; state="{r["state"]}"; '
                f'naics_code="{r["naics"]}"; '
                f'annual_average_employees="{r["annual_average_employees"]}"; '
                f'year_filing_for="{r["year"]}"'),
            "measurement_note": OSHA_NOTE,
            "confidence": "medium",
            "flags": ("TRIBE_LEVEL_ROLLUP_NOT_A_FACILITY_FIGURE;"
                      "ITA_COVERAGE_IS_NOT_A_CENSUS;"
                      "DO_NOT_SUM_ACROSS_YEARS_WITHOUT_A_BALANCED_PANEL;"
                      "ADJUDICATED_FROM_REVIEW_HOLD_2026-09-01"),
            "attribution_repair_basis": ev,
            "attribution_repaired_by": BY,
            "attribution_repair_date": TODAY,
            "fetched_date": "2026-08-07",
            "built_date": TODAY,
            "built_by_script": BY,
            "cedar_entity_name": spine.get(tid, {}).get("canonical_name", ""),
            "entity_class": spine.get(tid, {}).get("entity_class", ""),
        })
        have.add(key)

    byrule = collections.Counter(p["match_rule"] for p in promoted)
    print(f"   ADJUDICATED AND PROMOTABLE: {len(promoted)} rows over "
          f"{len({p['tribe_id'] for p in promoted})} tribes - "
          + ", ".join(f"{k} {n}" for k, n in byrule.most_common()))
    hr = collections.Counter(h["adjudication"].split(":")[0] for h in held)
    print(f"   STILL HELD: {len(held)} - "
          + "; ".join(f"{k} {n}" for k, n in hr.most_common()))
    wr(REVIEW / f"osha_gambling_adjudicated_{TODAY}.csv",
       [{"disposition": "PROMOTE", "tribe_id": p["tribe_id"],
         "rule": p["match_rule"], "evidence": p["attribution_repair_basis"],
         "state_mismatch_flag": p["state_mismatch_flag"],
         "company_name": p["company_name"],
         "establishment_name": p["establishment_name"],
         "state": p["state"], "year": p["year"],
         "employment": p["employment"]} for p in promoted]
       + [{"disposition": "HOLD", "tribe_id": "", "rule": "",
           "state_mismatch_flag": "",
           "evidence": h["adjudication"], "company_name": h["company_name"],
           "establishment_name": h["establishment_name"], "state": h["state"],
           "year": h["year"], "employment": h["annual_average_employees"]}
          for h in held])
    print(f"   -> review/osha_gambling_adjudicated_{TODAY}.csv")

    if not apply:
        print("\nDRY RUN. Re-run with --apply to write.")
        return

    # -------- 6. apply ------------------------------------------------------
    print("\n[6] APPLY")
    shutil.copy2(EMP, EMP.with_suffix(f".csv.bak_{TODAY}_pre583"))
    print(f"   backup -> {EMP.name}.bak_{TODAY}_pre583")

    fields = list(emp[0].keys())
    for extra in ("company_name", "establishment_id", "naics"):
        if extra not in fields:
            fields.append(extra)

    badset = {r["observation_id"] for r in bad}
    out, removed, flagged = [], 0, 0
    for r in emp:
        if r["observation_id"] in badset:
            removed += 1
            continue
        if r["sponsor_name"] in NON_GAMING_SPONSORS:
            f = [x for x in (r.get("flags") or "").split(";") if x]
            if NON_GAMING_FLAG not in f:
                f.append(NON_GAMING_FLAG)
                r["flags"] = ";".join(f)
                flagged += 1
        out.append(r)
    wr(REVIEW / f"gaming_employment_lsvgas_removed_{TODAY}.csv",
       [{**r, "removal_reason":
         "NON-TRIBAL commercial Las Vegas employer keyed to the Las Vegas "
         "Paiute Tribe because the tribe's spine handle is the bare US "
         "settlement name 'Las Vegas'. Same defect 157 guarded against and 156 "
         "did not. Removed by 583 on 2026-09-01."} for r in bad])
    print(f"   removed {removed} misattributed rows -> "
          f"review/gaming_employment_lsvgas_removed_{TODAY}.csv")
    print(f"   flagged {flagged} non-gaming sponsor rows in place")

    for p in promoted:
        out.append({f: p.get(f, "") for f in fields})
    wr(EMP, out, fields)
    print(f"   promoted {len(promoted)} adjudicated OSHA rows")
    print(f"   gaming_employment_observations.csv: {len(emp):,} -> "
          f"{len(out):,}")


if __name__ == "__main__":
    main()
