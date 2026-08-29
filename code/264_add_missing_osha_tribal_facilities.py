#!/usr/bin/env python3
r"""Cedar Press 264 - append the tribal gaming properties that OSHA names and
`gaming_facilities.csv` does not hold.

THE BRIEF SAID ~137 MISSING BRANDS. THERE ARE THREE, AND THE CORRECTION IS THE
FINDING.
--------------------------------------------------------------------------
`docs/LABOR_SOURCES_FOR_GAMING_2026-08-26.md` s17 closes with: *"the ~137
`blocked_not_leading` / `blocked_remainder` rows are largely real tribal
properties whose brands are simply missing from `gaming_facilities.csv`."*

Measured against the file. Those 137 rows are **65 distinct establishments**,
and they partition:

    already in Cedar under a NAME VARIANT      30 establishments
    commercial operators                       32 establishments
    genuinely absent tribal property            3 establishments

The 30 are not a universe gap. `Warm Springs Indian Head Casino` is Cedar's
`CCP-975800 Indian Head Casino`; `Squaxin Island Gaming dba Little Creek Casino
Resort` is `CCP-46900`; `Yakama Nation Legends Casino Hotel` is `CCP-249300
Legends Casino Hotel`; `Northern Quest Resort and Casino`, `Quinault Beach`,
`Potawatomi`, `The Oneida Hotel`, all three `St. Croix` properties, all four
`Kiowa` rows, `Win-River`, `Tortoise Rock`, `Chumash`, `Pearl River`,
`Harrah's Cherokee`, `Harrah's Rincon`, `Mohegan Sun` and `Naskila` are all
already here. `Eagle Mountian Casino` is `CCP-249900` behind a typo in the
filing. `Downs Racing, LP / Mohegan Sun Pocono` is `VP-0034 Mohegan
Pennsylvania`.

The 32 are the Las Vegas Strip (Paris, Sahara, SLS, Flamingo, Harrah's LV, OYO,
Westgate, Downtown Grand, JW Marriott, Hotspur), Prairie Meadows (IA), Ocean
Downs (MD), Zia Park (NM), Trop Greenville (MS), Club Fortune (NV), Warhorse
Omaha (NE), Double Eagle Cripple Creek (CO), a Courtyard in Houma and the San
Juan Marriott.

**SO THE BOTTLENECK IS NAME-VARIANT MATCHING, NOT FACILITY COVERAGE.** Adding
brands cannot fix a row that fails because Cedar's name is `Indian Head Casino`
and OSHA filed `Warm Springs Indian Head Casino`. That is the same shape as
157's own correction of its brief: *"the brief said attach the remaining ~4,700
at tribe level. There are not ~4,700 tribal rows."* A count carried forward from
a bucket label is not a measurement of what is in the bucket.

THE THREE THAT ARE REAL
-----------------------
Each is a property Cedar does not hold in ANY form, screened NATIONWIDE, not
by state - NIGC files `Cherokee Casino - West Siloam Springs` under an ARKANSAS
mailing address for a casino in OKLAHOMA, so a state-scoped duplicate screen
is the screen that misses.

    Catawba Two Kings Casino   Kings Mountain NC   TRBF-CATWBA-00
    Kalispel Casino            Cusick WA           TRBF-KALSPL-00
    Plateau Travel Plaza       Madras OR           TRBF-WRMSPR-00

**Cedar holds ZERO Catawba facilities.** That is a genuine universe gap on a
tribe that operates a casino, and it is the most valuable of the three.

THE TIER IS PRODUCED BY THE RESOLVER, NOT ASSIGNED HERE
-------------------------------------------------------
Every tier comes from `70_key_unjoined_datasets.key_name` - the same function
that keyed the other 782 rows of this file, called through 172's pattern - fed
the tribe name **as the filer itself published it in the OSHA `company_name`
field**, with the facility's own state. The input string and the resolver's
verdict are both written into `entity_match_basis`.

Catawba lands at **tier B** with `state_conflict:NC!=SC`, and that is correct
and worth keeping: the Catawba Indian Nation is a South Carolina tribe and this
casino is in North Carolina, so state agreement genuinely is absent. A tier that
would be A on a state match and is B without one is the resolver reporting the
evidence it actually has.

WHAT IS DELIBERATELY NOT ADDED
------------------------------
**`Mohegan Casino Las Vegas at Virgin Hotels` (NV) and `Foxwoods El San Juan
Casino` (PR).** Both are a tribal gaming authority MANAGING a property it does
not own - the exact INVERSE of the Harrah's Cherokee case. AGENTS.md and s12 of
the labor doc record that *a management-company brand is not ownership*: Caesars
manages Harrah's Cherokee and EBCI owns it, so the property is tribal. Run the
same rule the other way and a tribe managing a Las Vegas hotel casino does not
make that hotel a tribal property. **The rule is symmetric or it is not a rule.**
Recorded here rather than silently omitted.

`Las Vegas Bingo Unit` (Corpus Christi TX) and `61800002 MOHEGAN TRIBE` are not
added either: the first has no evidence of tribal ownership beyond a place name
already known to be a trap, and the second is a TRIBE, not a property.

SAFETY
  * ids minted via `cedar_ids.allocate("CEDAR-FAC", n)` - never inline
  * NATIONWIDE duplicate screen, refuses on any rare-token collision
  * backup `.bak_<date>_pre264`, `.part` then rename
  * target re-read inside the write path
  * verifies by RE-READING the written file
  * idempotent: a facility already present by name+state is skipped

    py -3 code/264_add_missing_osha_tribal_facilities.py --check
    py -3 code/264_add_missing_osha_tribal_facilities.py --apply
"""

import csv
import importlib.util
import re
import shutil
import sys
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
LOGS = CEDAR / "logs"
FAC = CLEAN / "gaming_facilities.csv"
TODAY = date.today().isoformat()
SCRIPT = "264_add_missing_osha_tribal_facilities.py"

sys.path.insert(0, str(CEDAR / "code"))
csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

# One entry per property. `published` is the tribe name AS THE FILER WROTE IT.
NEW = [
    {
        "facility_name": "Catawba Two Kings Casino",
        "city": "Kings Mountain", "state": "NC",
        "tribe_id": "TRBF-CATWBA-00",
        "published": "Catawba Indian Nation",
        "osha_establishment": "6903_15950",
        "osha_company": "Catawba Two Kings Casino",
        "evidence":
            "OSHA ITA CY2021-2024 files four establishment-years at Kings "
            "Mountain NC under company_name 'Catawba Two Kings Casino' "
            "(establishment_name is the numeric code 6903_15950). SECOND, "
            "INDEPENDENT LEG: the DOL Form 5500 layer merged into "
            "gaming_employment_observations.csv on 2026-08-26 carries "
            "'CATAWBA INDIAN NATION GAMING AUTHORITY' and 'CATAWBA INDIAN "
            "NATION GAMING AUTHORITY DBA CATAWBA TWO KIN[GS]' filed from NC. "
            "Two federal filing systems name the same operator at the same "
            "place. Cedar held NO Catawba facility of any kind before this "
            "row - a genuine universe gap, not a naming variant.",
    },
    {
        "facility_name": "Kalispel Casino",
        "city": "Cusick", "state": "WA",
        "tribe_id": "TRBF-KALSPL-00",
        "published": "Kalispel Tribe of Indians",
        "osha_establishment":
            "Kalispel Tribal Economic Authority d/b/a Kalispel Casino",
        "osha_company":
            "Kalispel Tribal Economic Authority d/b/a Kalispel Casino",
        "evidence":
            "OSHA ITA files this establishment at Cusick WA under a company "
            "name that states the ownership in full - 'Kalispel Tribal "
            "Economic Authority d/b/a Kalispel Casino'. THE FILER NAMES THE "
            "TRIBE ITSELF; no name matching is being relied on. Cedar holds "
            "the Kalispel Tribe's other property (CCP-513400 Northern Quest "
            "Resort & Casino, Airway Heights WA) and not this one. The same "
            "filer files both, under the same authority name.",
    },
    {
        "facility_name": "Plateau Travel Plaza",
        "city": "Madras", "state": "OR",
        "tribe_id": "TRBF-WRMSPR-00",
        "published":
            "Confederated Tribes of the Warm Springs Reservation of Oregon",
        "osha_establishment": "Plateau Travel Plaza",
        "osha_company": "Warm Springs Casino Enterprise",
        "evidence":
            "OSHA ITA files 'Plateau Travel Plaza' / 'Plateau Travel PLaza' "
            "at Madras OR under company_name 'Warm Springs Casino "
            "Enterprise' / 'WARM SPRINGS CASINO ENTERPRISE' - the same filer "
            "that files Cedar's CCP-975800 Indian Head Casino. A tribal "
            "travel plaza with gaming is an established Cedar property type "
            "(TPL-0127 I 40 Seminole Casino, TPL-0128 Seminole Nation Travel "
            "Plaza, CCP-676000 Kickapoo Conoco Station), and AGENTS.md "
            "records that a tribal convenience store appearing in a gaming "
            "roster is evidence FOR gaming, not against.",
    },
]

# Deliberately refused; kept in the code so the reasoning is not lost.
REFUSED = {
    "Mohegan Casino Las Vegas at Virgin Hotels":
        "TRIBAL MANAGER, NON-TRIBAL PROPERTY. The Mohegan Tribal Gaming "
        "Authority operates the casino inside Virgin Hotels Las Vegas. The "
        "management-brand rule is symmetric: Caesars managing Harrah's "
        "Cherokee does not make that property Caesars', so MTGA managing a "
        "Las Vegas hotel casino does not make that hotel tribal.",
    "El San Juan Casino":
        "TRIBAL MANAGER, NON-TRIBAL PROPERTY. Filed as 'Foxwoods El San Juan "
        "Casino', Carolina PR. Same symmetry as above.",
    "Las Vegas Bingo Unit":
        "Corpus Christi TX. No evidence of tribal ownership; 'Las Vegas' is a "
        "trap token this collection has already been bitten by twice (the Las "
        "Vegas Paiute Tribe capturing Caesars Palace and Bally's).",
    "61800002 MOHEGAN TRIBE":
        "This is a TRIBE, not a property. Cedar already holds CCP-45100 "
        "Mohegan Sun for it.",
}

STOP = {"the", "and", "of", "at", "a", "an", "dba", "d", "b", "llc", "inc",
        "lp", "ltd", "co", "corp", "resort", "resorts", "hotel", "casino",
        "casinos", "bingo", "gaming", "travel", "plaza", "center", "&"}


def log(msg):
    LOGS.mkdir(exist_ok=True)
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"))
    with open(LOGS / f"264_add_facilities_{TODAY}.log", "a",
              encoding="utf-8") as fh:
        fh.write(msg + "\n")


def read(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def header_of(p):
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return next(csv.reader(fh), [])


def toks(s):
    return {w for w in re.sub(r"[^a-z0-9 ]", " ", (s or "").lower()).split()
            if w and w not in STOP}


def load70():
    p = CEDAR / "code" / "70_key_unjoined_datasets.py"
    spec = importlib.util.spec_from_file_location("m70", str(p))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def duplicate_screen(spec, fac):
    """NATIONWIDE, never state-scoped. Returns a list of collisions."""
    want = toks(spec["facility_name"])
    hits = []
    for f in fac:
        ft = toks(f.get("facility_name"))
        if not ft or not want:
            continue
        inter = want & ft
        # exact name+state is a hard duplicate; a rare-token overlap is a
        # question that must be answered before minting an id.
        if (f.get("facility_name", "").strip().lower()
                == spec["facility_name"].strip().lower()):
            hits.append(("EXACT_NAME", f))
        elif len(inter) >= min(2, len(want)) and len(inter) / len(want) >= 0.66:
            hits.append(("TOKEN_OVERLAP", f))
    return hits


def main():
    apply_ = "--apply" in sys.argv
    log(f"=== Cedar Press 264: add missing OSHA tribal facilities ({TODAY}) "
        f"[{'APPLY' if apply_ else 'CHECK, read-only'}] ===")

    fac = read(FAC)
    if not fac:
        log(f"FATAL: {FAC} empty or missing")
        return 1
    log(f"gaming_facilities.csv holds {len(fac):,} rows")

    M70 = load70()
    spine_ids = {s["tribe_id"] for s in M70.SPINE_ROWS}

    log("\nDELIBERATELY REFUSED (recorded, not silently omitted):")
    for k, why in REFUSED.items():
        log(f"  {k[:44]:44} {why[:96]}")

    log("\nnationwide duplicate screen + resolver verdicts:")
    plan = []
    for spec in NEW:
        if spec["tribe_id"] not in spine_ids:
            log(f"  REFUSE {spec['facility_name']}: "
                f"{spec['tribe_id']} not in the spine")
            return 1
        hits = duplicate_screen(spec, fac)
        hard = [h for h in hits if h[0] == "EXACT_NAME"]
        if hard:
            log(f"  SKIP   {spec['facility_name'][:38]:38} already present as "
                f"{hard[0][1]['facility_id']} - idempotent")
            continue
        if hits:
            log(f"  REFUSE {spec['facility_name'][:38]:38} token overlap with "
                + ", ".join(f"{f['facility_id']} {f['facility_name']}"
                            for _, f in hits[:3]))
            return 1
        res = M70.key_name(spec["published"], "gaming_facilities",
                           spec["state"])
        if res["tribe_id"] != spec["tribe_id"]:
            log(f"  REFUSE {spec['facility_name']}: resolver returns "
                f"{res['tribe_id']!r} for {spec['published']!r}, ruling "
                f"expects {spec['tribe_id']!r}")
            return 1
        log(f"  OK     {spec['facility_name'][:38]:38} {spec['state']} -> "
            f"{res['tribe_id']} tier {res['tier']} method {res['method']} "
            f"({res['basis']})")
        plan.append((spec, res))

    if not plan:
        log("\nnothing to add (all present). Target untouched.")
        return 0
    log(f"\n{len(plan)} facility row(s) to append")

    if not apply_:
        log("\n--check only. Nothing written. Re-run with --apply.")
        return 0

    bak = FAC.with_suffix(f".csv.bak_{TODAY}_pre264")
    if not bak.exists():
        shutil.copy2(FAC, bak)
    log(f"\nbacked up -> {bak.name}")

    # re-read INSIDE the write path
    fac = read(FAC)
    fields = header_of(FAC)
    have = {(r.get("facility_name", "").strip().lower(),
             (r.get("state") or "").upper()) for r in fac}

    import cedar_ids
    todo = [(s, r) for s, r in plan
            if (s["facility_name"].strip().lower(), s["state"]) not in have]
    if not todo:
        log("a concurrent agent added them; nothing to do")
        return 0
    ids = cedar_ids.allocate("CEDAR-FAC", len(todo),
                             note="tribal gaming properties named by OSHA ITA "
                                  "and absent from gaming_facilities.csv")
    log(f"minted via cedar_ids.allocate: {', '.join(ids)}")

    added = []
    for fid, (spec, res) in zip(ids, todo):
        r = {k: "" for k in fields}
        r["facility_id"] = fid
        r["facility_name"] = spec["facility_name"]
        r["tribe"] = res["canonical_name"]
        r["company"] = spec["osha_company"]
        r["city"] = spec["city"]
        r["state"] = spec["state"]
        r["observation_status"] = "current"
        r["property_status"] = "current"
        for c in ("gaming_machines", "table_games", "poker_tables",
                  "bingo_seats", "gaming_square_feet",
                  "convention_square_feet", "hotel_rooms", "parking_spaces",
                  "employees", "restaurants"):
            k = f"{c}_value_basis"
            if k in r:
                r[k] = "no_capacity_source_for_this_facility"
        r["n_capacity_observations"] = "0"
        r["first_observed_date"] = TODAY
        r["last_observed_date"] = TODAY
        r["source_datasets"] = "OSHA_ITA_300A"
        r["match_status"] = "osha_only_no_cedar_match"
        r["match_basis"] = (
            "no rung of the code/157 ladder matched, and a NATIONWIDE "
            "duplicate screen over every Cedar facility name found no "
            "rare-token collision")
        r["duplicate_risk"] = "0"
        r["fetched_date"] = TODAY
        r["open_date_class"] = "absent"
        r["open_date_absent_reason"] = (
            "no opening date sourced - this row is created from OSHA ITA 300A "
            "establishment filings, which prove the establishment was "
            "OPERATING in the filed year and say nothing about when it opened")
        r["open_date_evidence"] = (
            f"OSHA ITA 300A, establishment_name={spec['osha_establishment']!r}, "
            f"company_name={spec['osha_company']!r}, {spec['city']} "
            f"{spec['state']}")
        r["close_date_class"] = "absent"
        r["temporal_build_date"] = TODAY
        r["tribe_id"] = spec["tribe_id"]
        r["tribe_canonical_name"] = res["canonical_name"]
        r["entity_match_method"] = res["method"]
        r["entity_tier"] = res["tier"]
        r["entity_match_basis"] = (
            f"{SCRIPT} {TODAY}; resolved via 70.key_name("
            f"{spec['published']!r}, state={spec['state']!r}) -> "
            f"{res['basis']}; EVIDENCE: {spec['evidence']}")
        r["entity_keyed_date"] = TODAY
        # entity_id is the PUBLISHABLE key and is written at tier A only -
        # this file's existing invariant.
        r["entity_id"] = spec["tribe_id"] if res["tier"] == "A" else ""
        added.append(r)

    out = fac + added
    part = FAC.with_suffix(".csv.part")
    with open(part, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(out)
    part.replace(FAC)

    # ---- VERIFY BY RE-READING ---------------------------------------------
    back = read(FAC)
    ok = len(back) == len(fac) + len(added)
    log(f"\nrows {len(fac):,} -> {len(back):,} (expected {len(fac)+len(added):,})")
    ids_back = {r["facility_id"] for r in back}
    for fid in ids:
        if fid not in ids_back:
            log(f"  FAIL: {fid} is not in the written file")
            ok = False
    if len(ids_back) != len(back):
        log("  FAIL: facility_id is no longer unique")
        ok = False
    if any(not (r.get("tribe_id") or "").strip() for r in added):
        log("  FAIL: an appended row carries no tribe_id")
        ok = False
    log("  re-read verification: " + ("PASS" if ok else "FAIL"))
    if not ok:
        log(f"  RESTORE {bak.name}")
        return 1
    for r in added:
        log(f"  + {r['facility_id']}  {r['facility_name'][:34]:34} "
            f"{r['state']}  {r['tribe_id']}  tier {r['entity_tier']}")
    log("\nNOW RUN: py -3 code/157_stage_osha_tribe_level_employment.py "
        "(measures the auto-attach lift)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
