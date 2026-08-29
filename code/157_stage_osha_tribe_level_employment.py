#!/usr/bin/env python3
"""
Cedar Press - 157: STAGE tribe-level OSHA ITA employment + FTE for gaming.

NO NETWORK. Everything is already on disk.

WHAT THIS DOES AND WHY IT IS NOT WHAT WAS ASKED FOR
---------------------------------------------------
The brief was "Cedar attached only 364 of 5,062 gambling-NAICS rows; attach the
remaining ~4,700 at tribe level."

**~4,700 tribal rows do not exist.** Measured before building: the 5,062-row
gambling-NAICS pool is overwhelmingly COMMERCIAL. The largest filers are
International Game Technology (201 rows), Boyd Gaming (177+76), Caesars
Entertainment (175), Station Casinos (155), MGM Resorts (138), M.G. Oil (110+38),
VICI Properties (96), plus the California and Oregon state lotteries. NAICS
7132/721120 is the GAMBLING INDUSTRY, not the tribal gambling industry.

So the honest job is not "attach the rest" but "find the tribal ones and refuse
the rest out loud." The refusals are the product here as much as the matches.

WHY CEDAR'S OWN RESOLVER, AND WHY IT IS NOT ENOUGH ON ITS OWN
-------------------------------------------------------------
AGENTS.md standing rule 8: never write another name matcher.
`code/33_apply_party_rulings.py::resolve_entity` is the one resolver, and it is
used here unmodified. 4wheeler's `lib_cedar_resolver` is NOT used - it has an
open exact-alias defect (Hamilton / Evansville / Georgetown, 131 bad rows).

But `resolve_entity`'s CONTAINMENT path has failed in many documented directions
and the central fix was never built - every guard in this project is local.
Measured on this exact input, unguarded containment produced:

    CAESARS PALACE LAS VEGAS HOTEL AND CASINO  -> Las Vegas   (Paiute Tribe)
    BALLY'S LAS VEGAS HOTEL & CASINO           -> Las Vegas
    Circus Circus Las Vegas                    -> Las Vegas
    Arrow International, Inc - Las Vegas Studio-> Las Vegas
    CA State Lottery - Santa Ana District Office -> Pueblo of Santa Ana
    Chumash Casino & Resort Enterprise         -> Enterprise  (Enterprise Rancheria)
    Black Diamond Capital, LLC                 -> Native Community Capital
    Capital Region Gaming LLC dba Rivers Casino-> Native Community Capital
    Black Eagle Office                         -> Eagle
    Comfort Suites Oceanside/Camp Pendleton    -> Oceanside Corporation
    Billings                                   -> Billings Urban Indian Health

Every one of those would have written a wrong tribe onto an OSHA INJURY record.
That is worse than a blank, so the guards below are deliberately strict and the
refusals are all recorded with their reason.

TWO PASSES, AND THE ORDER BETWEEN THEM IS LOAD-BEARING
-------------------------------------------------------
PASS B runs FIRST: `establishment_name` is looked up in Cedar's own curated
`data/clean/gaming_facilities.csv` (facility_name -> tribe_id), requiring an
unambiguous single tribe AND state agreement. This exists because OSHA files a
BRAND, not a tribe name - "Yaamava", "Turning Stone", "Talking Stick", "Thunder
Valley", "Cache Creek" - and the spine keys on TRIBE names, so the spine can
never bridge it. Measured: pass B alone attaches 345 rows the spine refuses,
including Turning Stone (4,570 employees), Casino Arizona / Talking Stick
(3,331), Thunder Valley (2,555) and Cache Creek (2,044).

PASS A runs second: `resolve_entity` + the seven guards below.

Why B before A, and why B is exempt from the commercial blocklist: see the
comment on `build_brand_index`. Short version - a MANAGEMENT BRAND IS NOT
OWNERSHIP. Caesars manages Harrah's Cherokee; the Eastern Band of Cherokee
Indians owns it. Blocking first refused three genuine tribal properties, one of
which (Treasure Island Resort & Casino, MN) carried `company_name = "Prairie
Island Indian Community"` - the field literally named the tribe and the
blocklist fired anyway. A curated Cedar ruling outranks a heuristic blocklist,
and `commercial_name_present` records the tension instead of hiding it.

THE SEVEN GUARDS ON PASS A, EACH EARNED BY A MEASURED FAILURE ABOVE
--------------------------------------------------------------------
G1 COMMERCIAL BLOCK IS PER ROW, NOT PER NAME STRING.
   The first version checked each name string independently and let
   `establishment_name = "Las Vegas"` resolve to the Las Vegas Paiute Tribe -
   306 employees - while that row's `company_name` said **AGS, LLC**, a slot
   manufacturer. A row is blocked if EITHER field names a commercial operator.
   Same for "Billings" and "Omaha", both J&J Ventures Gaming LLC.

G2 OWNER CLASS. A casino is owned by a tribe, a village, or an ANCSA
   corporation. It is never owned by a CDFI, an urban Indian health programme,
   a BIE school or a tribal college. That single rule kills the Native Community
   Capital and Billings Urban Indian Health misroutes.

G3 THE ENTITY NAME MUST LEAD THE FILED NAME.
   `Blue Lake Casino` leads with "Blue Lake"; `CAESARS PALACE LAS VEGAS ...`
   does not lead with "Las Vegas". This is the single most effective guard and
   it is 4wheeler's rule 6 reached independently: the remainder after an alias
   must be suffix vocabulary, or "Salt River" swallows "Salt River Valley Water
   Users Association".

G4 THE REMAINDER MUST BE PERMITTED VOCABULARY - gaming, corporate and
   structural words only. `Chumash Casino & Resort Enterprise` cannot reach
   Enterprise Rancheria because "chumash" would have to sit in the remainder.

G5 A TRIBAL WORD OR A GAMING WORD MUST BE PRESENT.
   A bare US place name resolves to nothing. This is what finally kills
   `Las Vegas`, `Omaha` and `Billings`, none of which carries either. 4wheeler
   reached the same rule from the same failure ("las vegas" catching Las Vegas
   Sands).

G6 STATE AGREEMENT, ALWAYS. A mismatch is not dropped silently - it is written
   to the review file with both states named.

G7 A TRAP-ONLY CORE NEVER AUTO-ATTACHES. Where the entity's distinctive core
   (`core` minus `cedar_domain.NAME_TRAPS`, 39 terms) is EMPTY, the match rests
   entirely on a token that has already cost a real misattribution - cherokee,
   creek, little, omaha, seminole. Those become `candidate_review` rows carrying
   the full evidence, never attachments. Cherokee Nation Entertainment LLC and
   Little River Casino Resort are both *probably right* and both go to review
   anyway, because "probably right" is not the standard for writing a tribe onto
   an injury record.

Writes  data/staging/gaming_employment_osha_tribe_staged.csv
        review/osha_gambling_unresolved_2026-08-26.csv
        docs fragment is appended by hand to LABOR_SOURCES_FOR_GAMING_2026-08-26.md

STAGED, NEVER MERGED. Another agent holds the gaming host locks and is
rebuilding parts of the gaming collection. See `MERGE CONTRACT` at the bottom of
this docstring for exactly what a later merge must do.

MERGE CONTRACT - what a later merge into data/clean/ must do
------------------------------------------------------------
1. Back up the target first. `gaming_employment_observations.csv` is 769 rows
   and that count is asserted in docs/GAMING_EMPLOYMENT_LOG.md.
2. Add `OSHA_TRIBE_LEVEL_REPORTED` to `cedar_domain.MeasurementType`, in
   `is_observed` (an establishment counted its own people) and NOT in
   `NEVER_PROMOTES_TO_ACTIVE` (it is a real headcount, unlike plan participants).
3. Set `entity_level = "tribe"` on every row and leave `facility_id` blank -
   the pattern `gaming_facility_metrics.csv` already uses on 1,039 rows.
4. DE-DUPLICATE AGAINST THE FACILITY-LEVEL LAYER. `already_facility_attached`
   is set on every row that the existing 364-row OSHA layer already carries at
   facility grain. Those rows are the SAME filing seen at a coarser grain and
   must never be summed with it.
5. `fte_2080` is DERIVED, not filed. If it is merged it needs its own
   measurement type; it must never enter an `employment` column.
"""

import csv
import importlib.util
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CODE = CEDAR / "code"
CLEAN = CEDAR / "data" / "clean"
STAGING = CEDAR / "data" / "staging"
REVIEW = CEDAR / "review"
LOGS = CEDAR / "logs"
SRC = CEDAR / "data" / "raw" / "external" / "osha_ita" / "_gambling_naics_rows.csv"
SPINE = CEDAR / "data" / "spine" / "cedar_entity_spine.csv"
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

sys.path.insert(0, str(CODE))
_spec = importlib.util.spec_from_file_location("m33", CODE / "33_apply_party_rulings.py")
M33 = importlib.util.module_from_spec(_spec)
try:
    _spec.loader.exec_module(M33)
except SystemExit:
    pass                      # 33 guards its own __main__; importing is safe
import cedar_domain as CD     # noqa: E402

norm = M33.norm
core = M33.core
resolve_entity = M33.resolve_entity

# --------------------------------------------------------------- ANNUAL HOURS
# THE FTE ASSUMPTION, STATED IN ONE PLACE AND CARRIED ON EVERY ROW.
#
#   FTE = total_hours_worked / 2080,   2080 = 40 hours x 52 weeks.
#
# 2080 is the federal full-time-equivalent convention (OPM, and the same divisor
# BLS uses for FTE conversions). It is a CONVENTION, not a measurement, and two
# things bias it in opposite directions:
#
#   - OSHA 300A `total_hours_worked` is ALL hours worked by ALL employees
#     INCLUDING OVERTIME. Overtime therefore inflates FTE above the true
#     full-time-staff count.
#   - It EXCLUDES paid leave, holidays and sick time. A salaried full-timer with
#     three weeks off books ~1,960 hours, not 2,080, and scores 0.94 FTE.
#
# Measured in this sector by 4wheeler: median hours per employee is 1,859, which
# is what a part-time-heavy casino floor looks like. So FTE will normally run
# BELOW `annual_average_employees`, and the ratio is the interesting quantity -
# it is a staffing-mix measure, not an error.
ANNUAL_HOURS_PER_FTE = 2080

# Rows outside this band are internally impossible and are flagged, not fixed.
# 4wheeler measured 6 of 327 outside it: Central Valley Indian Health filed 122
# employees against 500 total hours; "Choctaw Casino Amenity Refresh" filed 19
# employees against 117,335 hours (a construction project booking contractor
# hours against a casino establishment).
HOURS_PER_EMPLOYEE_MIN, HOURS_PER_EMPLOYEE_MAX = 200, 5000

# ------------------------------------------------------------- OWNER CLASSES
OWNER_CLASSES = {
    "Federally recognized tribe",
    "Federally recognized Alaska Native Village",
    "State-recognized tribe",
    "Alaska Native Village Corporation",
    "Alaska Native Regional Corporation",
    "ANCSA Group Corporation",
}

TRIBAL_WORDS = {
    "tribe", "tribes", "tribal", "nation", "nations", "band", "bands",
    "pueblo", "rancheria", "indian", "indians", "village", "community",
    "colony", "reservation", "chippewa", "paiute", "shoshone", "sioux",
    "apache", "creek", "cherokee", "choctaw", "chickasaw", "seminole",
}

GAMING_WORDS = {
    "casino", "casinos", "gaming", "gambling", "bingo", "resort", "resorts",
    "entertainment", "enterprise", "enterprises", "lottery",
}

# Everything allowed to sit AFTER the entity name (G4).
PERMITTED_REMAINDER = GAMING_WORDS | TRIBAL_WORDS | {
    "hotel", "hotels", "lodge", "inn", "travel", "plaza", "center", "centre",
    "spa", "commission", "authority", "development", "management",
    "operations", "operating", "holdings", "properties", "property", "group",
    "services", "service", "corporation", "corp", "inc", "incorporated",
    "llc", "lp", "llp", "ltd", "limited", "company", "co", "dba", "the", "of",
    "and", "at", "federal", "north", "south", "east", "west", "ii", "i",
}

# --------------------------------------------------------- COMMERCIAL BLOCK
# Applied to the WHOLE ROW (G1). Every string here was read off the actual
# filer list in this file, not guessed.
COMMERCIAL = [
    "caesars", "mgm resorts", "mgm grand", "boyd gaming", "station casinos",
    "international game technology", "igt global", "igt ", "brightstar lottery",
    "everi", "ags llc", "ags inc", "vici properties", "penn national",
    "penn entertainment", "eldorado resorts", "affinity gaming",
    "golden entertainment", "accel entertainment", "century gaming",
    "century casinos", "treasure island", "circus circus", "ballys",
    "bally s", "fontainebleau", "wynn", "venetian", "las vegas sands",
    "churchill downs", "delaware north", "jacobs entertainment",
    "monarch casino", "red rock resorts", "full house resorts",
    "state lottery", "lottery commission", "lottery corporation",
    "j j ventures", "m g oil", "mg oil", "laceys place", "lacey s place",
    "arrow international", "light wonder", "scientific games", "aristocrat",
    "konami", "bowtie hospitality", "comfort suites", "black diamond capital",
    "capital region gaming", "rivers casino", "greektown", "motorcity",
    "hollywood casino", "ameristar", "isle of capri", "tropicana",
    "golden nugget", "hard rock international", "seminole hard rock support",
]


def log(msg):
    LOGS.mkdir(exist_ok=True)
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii","replace").decode("ascii"))
    with open(LOGS / f"157_osha_tribe_{TODAY}.log", "a", encoding="utf-8") as fh:
        fh.write(msg + "\n")


def read_csv(p):
    if not Path(p).exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(path.suffix + ".part")
    with open(part, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    part.replace(path)
    log(f"  wrote {path.relative_to(CEDAR)}  ({len(rows):,} rows)")


def num(x):
    try:
        v = float(str(x).strip())
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def clean_year(x):
    """`year_filing_for` arrives as 2019, '2019.00' and '2019'. Normalise."""
    v = num(x)
    return str(int(v)) if v else ""


# --------------------------------------------------------- BRAND CROSSWALK
# PASS B. OSHA's `establishment_name` is a BRAND - "Yaamava", "Turning Stone",
# "Talking Stick", "Thunder Valley" - and the spine keys on TRIBE names, so the
# spine can never bridge it. Cedar already owns that bridge:
# `data/clean/gaming_facilities.csv` maps facility_name -> tribe_id, curated.
#
# This is NOT a new name matcher (AGENTS.md standing rule 8). It is a lookup
# against a Cedar-ruled table, and it is required to be UNAMBIGUOUS and to agree
# on state before it attaches.
#
# PASS B OUTRANKS THE COMMERCIAL BLOCKLIST, AND THAT ORDERING IS THE WHOLE POINT.
# Measured: blocking first refused three genuine tribal properties -
#
#   HARRAH'S CHEROKEE CASINO RESORT  company_name = "Caesars Entertainment"
#       -> owned by the EASTERN BAND OF CHEROKEE INDIANS, merely MANAGED by
#          Caesars. Blocked as commercial. Wrong.
#   Harrah's Ak-Chin Casino          company_name = "Caesars"
#       -> owned by the AK-CHIN INDIAN COMMUNITY. Same shape.
#   Treasure Island Resort & Casino  company_name = "Prairie Island Indian
#       Community" - the company field NAMES THE TRIBE, and the blocklist still
#       fired, because "treasure island" is also a Las Vegas property.
#
# THE RULE: A MANAGEMENT-COMPANY BRAND IS NOT OWNERSHIP. The blocklist exists to
# stop HEURISTIC name matching from inventing a tribe. It must never override a
# ruling Cedar has already made about a named property. Where the two disagree,
# the curated table wins and `commercial_name_present` records the tension
# rather than hiding it.
def build_brand_index(fac):
    idx = defaultdict(set)
    for f in fac:
        tid, fname = f.get("tribe_id"), f.get("facility_name")
        if tid and fname:
            idx[norm(fname)].add((tid, (f.get("state") or "").strip().upper()))
    return idx


def brand_lookup(est, state, idx):
    """Exact first, then facility-name-leads. Unambiguous + state-agreeing only."""
    e = norm(est)
    if not e:
        return None, None
    cands = idx.get(e)
    if cands:
        m = {t for t, st in cands if st == state}
        if len(m) == 1:
            return m.pop(), "cedar_gaming_facilities_brand_exact"
    hits = []
    for k, v in idx.items():
        if k and (e == k or e.startswith(k + " ")):
            for t, st in v:
                if st == state:
                    hits.append((len(k), t))
    if hits:
        best = max(h[0] for h in hits)
        top = {t for ln, t in hits if ln == best}
        if len(top) == 1:
            return top.pop(), "cedar_gaming_facilities_brand_lead"
    return None, None


def commercial_hit(row):
    blob = " " + norm(f"{row.get('company_name','')} {row.get('establishment_name','')}") + " "
    for c in COMMERCIAL:
        if (" " + c.strip() + " ") in blob or c.strip() in blob:
            return c.strip()
    return None


def try_name(name, state, spine, by_id):
    """All seven guards. Returns (verdict, tribe_id, canonical, method, reason)."""
    if not name or not name.strip():
        return "unresolved", None, None, None, "empty"
    tid, cn, how = resolve_entity(name, spine)
    if not tid:
        return "unresolved", None, None, how, how
    ent = by_id[tid]

    if ent["entity_class"] not in OWNER_CLASSES:
        return ("blocked_class", None, None, how,
                f"owner_class_cannot_own_a_casino:{ent['entity_class']}")

    n, cnn = norm(name), norm(cn)
    if not (n == cnn or n.startswith(cnn + " ")):
        return ("blocked_not_leading", None, None, how,
                f"spine_name_does_not_lead_filed_name:{cn}")

    rem = [t for t in n[len(cnn):].split() if t]
    bad = [t for t in rem if t not in PERMITTED_REMAINDER]
    if bad:
        return ("blocked_remainder", None, None, how,
                f"remainder_carries_identity_tokens:{','.join(bad[:4])}")

    toks = set(n.split())
    if not (toks & TRIBAL_WORDS) and not (toks & GAMING_WORDS):
        return ("blocked_no_tribal_or_gaming_word", None, None, how,
                "bare_place_name:no tribal word and no gaming word present")

    st_row = (state or "").strip().upper()
    st_ent = (ent.get("state") or "").strip().upper()
    if st_ent and st_row and st_ent != st_row:
        return ("candidate_review", tid, cn, how,
                f"state_disagreement:filed_in_{st_row}_spine_says_{st_ent}")

    if not (core(cn) - CD.NAME_TRAPS):
        return ("candidate_review", tid, cn, how,
                "distinctive_core_is_entirely_NAME_TRAPS")

    return "attached", tid, cn, how, ""


def main():
    log(f"=== Cedar Press 157: stage tribe-level OSHA employment ({TODAY}) ===")
    log("NO NETWORK. Reading only local files.")
    if not SRC.exists():
        log(f"FATAL: {SRC} not found")
        return 1

    spine = read_csv(SPINE)
    by_id = {r["tribe_id"]: r for r in spine}
    rows = read_csv(SRC)
    fac = read_csv(CLEAN / "gaming_facilities.csv")
    brand_idx = build_brand_index(fac)
    log(f"spine {len(spine):,} entities | OSHA gambling-NAICS rows {len(rows):,}")
    log(f"brand crosswalk: {len(fac):,} Cedar facilities -> "
        f"{len(brand_idx):,} distinct normalised facility names")

    # --- what the existing facility-level layer already covers --------------
    existing = read_csv(CLEAN / "gaming_employment_observations.csv")
    already = set()
    for e in existing:
        if e.get("measurement_type") != "OSHA_ESTABLISHMENT_REPORTED":
            continue
        q = e.get("source_quote", "")
        mname = re.search(r'establishment_name="([^"]*)"', q)
        myr = re.search(r'year_filing_for="([^"]*)"', q)
        mst = re.search(r'state="([^"]*)"', q)
        if mname and myr:
            already.add((norm(mname.group(1)),
                         clean_year(myr.group(1)),
                         (mst.group(1) if mst else "").upper()))
    log(f"existing facility-level OSHA observations: "
        f"{sum(1 for e in existing if e.get('measurement_type')=='OSHA_ESTABLISHMENT_REPORTED'):,} "
        f"-> {len(already):,} distinct (establishment, year, state) keys")

    out, rev = [], []
    verdicts = Counter()
    n = 0

    for r in rows:
        state = (r.get("state") or "").strip().upper()
        yr = clean_year(r.get("year_filing_for"))
        emp = num(r.get("annual_average_employees"))
        hrs = num(r.get("total_hours_worked"))
        est = (r.get("establishment_name") or "").strip()
        comp = (r.get("company_name") or "").strip()

        ch = commercial_hit(r)

        # --- PASS B first: a Cedar ruling outranks a heuristic blocklist ----
        btid, bhow = brand_lookup(est, state, brand_idx)
        if btid:
            field, nm, v, tid, cn, how, reason = (
                "establishment_name", est, "attached", btid,
                by_id[btid]["canonical_name"], bhow, "")
            verdicts["attached_via_cedar_facility_brand"] += 1
        else:
            if ch:
                verdicts["blocked_commercial"] += 1
                rev.append(dict(
                    verdict="blocked_commercial",
                    reason=f"commercial_operator:{ch}",
                    company_name=comp, establishment_name=est,
                    city=r.get("city", ""), state=state, year=yr,
                    naics=r.get("naics_code", ""),
                    annual_average_employees=r.get("annual_average_employees", ""),
                    proposed_tribe_id="", proposed_entity="", method=""))
                continue

            # --- PASS A: spine resolution + the seven guards ---------------
            # company_name is the PARENT and is tried first; establishment_name
            # is the property. A parent that resolves is the stronger statement.
            best = None
            for field, nm in (("company_name", comp), ("establishment_name", est)):
                v, tid, cn, how, reason = try_name(nm, state, spine, by_id)
                if v == "attached":
                    best = (field, nm, v, tid, cn, how, reason)
                    break
                if best is None or (best[2] != "candidate_review"
                                    and v == "candidate_review"):
                    best = (field, nm, v, tid, cn, how, reason)
            field, nm, v, tid, cn, how, reason = best
            verdicts[v] += 1

        if v != "attached":
            rev.append(dict(
                verdict=v, reason=reason, company_name=comp,
                establishment_name=est, city=r.get("city", ""), state=state,
                year=yr, naics=r.get("naics_code", ""),
                annual_average_employees=r.get("annual_average_employees", ""),
                proposed_tribe_id=tid or "", proposed_entity=cn or "",
                method=how or ""))
            continue

        hpe = (hrs / emp) if (hrs and emp) else None
        plausible = (hpe is not None
                     and HOURS_PER_EMPLOYEE_MIN <= hpe <= HOURS_PER_EMPLOYEE_MAX)
        n += 1
        out.append({
            "observation_id": f"EMP-OSHATRIBE-{n:05d}",
            "facility_id": "",
            "entity_level": "tribe",
            "tribe_id": tid,
            "cedar_entity_name": cn,
            "entity_class": by_id[tid]["entity_class"],
            "year": yr,
            "employment": r.get("annual_average_employees", ""),
            "measurement_type": "OSHA_TRIBE_LEVEL_REPORTED",
            "measurement_type_status":
                "PROPOSED - not yet in cedar_domain.MeasurementType",
            "geographic_level": "establishment_rolled_to_tribe",
            "total_hours_worked": r.get("total_hours_worked", ""),
            "fte_2080": (f"{hrs / ANNUAL_HOURS_PER_FTE:.1f}" if hrs else ""),
            "fte_divisor": ANNUAL_HOURS_PER_FTE,
            "fte_is_derived_not_filed": "1",
            "hours_per_employee": (f"{hpe:.0f}" if hpe is not None else ""),
            "hours_per_employee_plausible": "1" if plausible else "0",
            "establishment_name": est,
            "company_name": comp,
            "establishment_id": r.get("establishment_id", ""),
            "ein": r.get("ein", ""),
            "street_address": r.get("street_address", ""),
            "city": r.get("city", ""),
            "state": state,
            "naics": r.get("naics_code", ""),
            "matched_on_field": field,
            "commercial_name_present": ch or "",
            "match_rule": f"cedar_resolve_entity_{how}_plus_7_local_guards",
            "already_facility_attached":
                "1" if (norm(est), yr, state) in already else "0",
            "source_url": "https://www.osha.gov/itadata",
            "source_name": "OSHA Injury Tracking Application, Form 300A "
                            "establishment summary",
            "source_record": r.get("_file", ""),
            "source_quote":
                f'establishment_name="{est}"; company_name="{comp}"; '
                f'city="{r.get("city","")}"; state="{state}"; '
                f'naics_code="{r.get("naics_code","")}"; '
                f'annual_average_employees="{r.get("annual_average_employees","")}"; '
                f'total_hours_worked="{r.get("total_hours_worked","")}"; '
                f'year_filing_for="{yr}"',
            "measurement_note":
                "The ESTABLISHMENT'S OWN FILED annual average employees, rolled "
                "to the tribe that owns it. It is a headcount, not an FTE and "
                "not a payroll. `fte_2080` is DERIVED here, not filed: "
                "total_hours_worked / 2080 (40h x 52w, the federal FTE "
                "convention). Those hours INCLUDE overtime and EXCLUDE paid "
                "leave, so FTE normally runs BELOW annual_average_employees in "
                "this sector - median hours per employee is about 1,859, which "
                "is what a part-time-heavy casino floor looks like. OSHA ITA "
                "coverage is NOT a census: electronic submission is required "
                "only of establishments above size thresholds in covered "
                "industries, and compliance is uneven. AN ESTABLISHMENT ABSENT "
                "FROM ITA IS NOT AN ESTABLISHMENT WITH ZERO INJURIES AND NOT "
                "AN ESTABLISHMENT WITH ZERO EMPLOYEES - it is an establishment "
                "that did not file. The set of establishments filing under one "
                "tribe CHANGES YEAR TO YEAR, so a tribe-year SUM of these rows "
                "is not a consistent panel and must never be differenced as if "
                "it were.",
            "confidence": "medium",
            "flags": "TRIBE_LEVEL_ROLLUP_NOT_A_FACILITY_FIGURE;"
                     "ITA_COVERAGE_IS_NOT_A_CENSUS;"
                     "DO_NOT_SUM_ACROSS_YEARS_WITHOUT_A_BALANCED_PANEL"
                     + (";HOURS_PER_EMPLOYEE_IMPLAUSIBLE" if not plausible else ""),
            "built_by_script": "157_stage_osha_tribe_level_employment.py",
            "built_date": TODAY,
        })

    write_csv(STAGING / "gaming_employment_osha_tribe_staged.csv", out,
              list(out[0].keys()) if out else ["observation_id"])

    revf = ["verdict", "reason", "company_name", "establishment_name", "city",
            "state", "year", "naics", "annual_average_employees",
            "proposed_tribe_id", "proposed_entity", "method"]
    rev.sort(key=lambda r: (r["verdict"] != "candidate_review", r["verdict"],
                            r["establishment_name"]))
    write_csv(REVIEW / f"osha_gambling_unresolved_{TODAY}.csv", rev, revf)

    # ------------------------------------------------------------ reporting --
    log("")
    log("VERDICTS over %d rows:" % len(rows))
    for k, v in verdicts.most_common():
        log(f"  {k:34} {v:5,}  ({v/len(rows)*100:4.1f}%)")

    tribes = {r["tribe_id"] for r in out}
    years = sorted({r["year"] for r in out if r["year"]})
    emp_existing = read_csv(CLEAN / "gaming_employment_observations.csv")
    emp_tribes = {e["tribe_id"] for e in emp_existing if e.get("tribe_id")}
    fac_tribes = {f["tribe_id"] for f in fac if f.get("tribe_id")}
    dup = sum(1 for r in out if r["already_facility_attached"] == "1")
    impl = sum(1 for r in out if r["hours_per_employee_plausible"] == "0")
    withfte = sum(1 for r in out if r["fte_2080"])

    log("")
    log("SUMMARY")
    log(f"  attached rows                    {len(out):,} of {len(rows):,} "
        f"({len(out)/len(rows)*100:.1f}%)")
    log(f"  distinct tribes                  {len(tribes)}")
    log(f"  year span                        {years[0]}-{years[-1]}")
    log(f"  rows carrying a derived FTE      {withfte:,}")
    log(f"  rows already covered at facility {dup:,}  (flagged, not dropped)")
    log(f"  NET NEW rows                     {len(out)-dup:,}")
    log(f"  hours/employee implausible       {impl}")
    log(f"  tribes NEW to employment table   {len(tribes - emp_tribes)}")
    log(f"  tribes with a Cedar facility     {len(tribes & fac_tribes)}")
    log(f"  review file rows                 {len(rev):,}")
    log(f"    of which candidate_review      "
        f"{sum(1 for r in rev if r['verdict']=='candidate_review')}")
    log("")
    log("STAGED, NOT MERGED. Merge contract is in this file's docstring and in "
        "docs/LABOR_SOURCES_FOR_GAMING_2026-08-26.md.")

    per_year = defaultdict(set)
    for r in out:
        per_year[r["year"]].add(r["tribe_id"])
    log("")
    log("  year   rows  tribes")
    cnt = Counter(r["year"] for r in out)
    for y in years:
        log(f"  {y}  {cnt[y]:5,}  {len(per_year[y]):5,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
