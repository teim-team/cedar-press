#!/usr/bin/env python3
r"""Cedar Press 262 - repair the Form 5500 tribe attribution that landed in
`data/clean/gaming_employment_observations.csv` via script 158.

WHY THIS EXISTS
---------------
`158_merge_staged_labor_employment.py` merged 2,046 Form 5500 rows (script 156)
and 485 OSHA rows (script 157) into the employment table on 2026-08-26. The
merge itself is correct: 769 + 2,531 = 3,300, ids unique, nothing clobbered.

**The Form 5500 layer arrived carrying a systematic misattribution.** 156 took
4wheeler's `resolved_form5500_tribal.csv` tribe resolution AS GIVEN. 157, on the
same day, built SEVEN local guards before it would write a tribe onto an OSHA
record, and its output audits clean (141 distinct pairs, one non-tribe class row,
correct). 156 built none, because its docstring records a check that was too
narrow:

    "exact-alias defect names present in this subset: NONE"

That check tested the FOUR names `4wheeler/docs/KNOWN_DEFECTS.md` happens to
list - Hamilton, Evansville, Georgetown, St. Mary's. **`Eagle` is a fifth
place-named Alaska Native village and nobody had listed it**, so the check
passed and 62 rows shipped saying the Native Village of Eagle, Alaska employs
people at Golden Eagle Casino in Horton, Kansas.

**THE RULE THIS EARNS: a defect list is a list of INSTANCES, never the extent of
the DEFECT.** Checking the four known names verified the four known names. The
defect is "a short place-derived spine name captures an unrelated employer", and
its population is every short place-derived spine name, not the four somebody
had already been bitten by. Same shape as the 161 short-name collisions in
AGENTS.md - each one is a collision waiting for the right input string.

WHAT IS WRONG, MEASURED
-----------------------
204 of 2,046 Form 5500 rows (10.0%), in 16 sponsor groups, 3 failure modes:

  place-name capture   `Eagle` (AK village) <- 5 CO/CA/WA/KS casinos      62
                       `Delaware Nation` (OK) <- Gaming Entertainment
                            (Delaware) LLC, a DELAWARE STATE operator     16
                       `Native Hawaiian Community` <- Hawaiian Gardens
                            Casino, a card room in Hawaiian Gardens, CA   16
  token capture        `Prairie Band` (KS) <- Prairie Meadows (IA),
                            Prairie Wind (SD), Prairie Knights (ND)       30
  wrong-tribe-same-name   Sac and Fox Nation (OK) <- the Kansas and the
                            Iowa Sac & Fox tribes                         34
                       Seminole (FL) <- the Seminole Nation of OKLAHOMA   16
                       Cherokee Nation <- United Keetoowah Band          10
  class violation      BIE School <- a casino. 157 already blocks this
                            (`blocked_class`); 156 does not               20

THE TWO DISPOSITIONS, AND WHY EACH IS SAFE
------------------------------------------
**CORRECT_TO (133 rows, 10 groups).** Every one is settled by
`data/clean/gaming_facilities.csv` - Cedar's own CURATED facility table - on
brand + state agreement. This is not a new name matcher; it is the same lookup
`157` Pass B already uses, and it is the principle already written down: *a
management brand is not ownership, and Cedar's curated facility table outranks
any heuristic*. The script REFUSES to write a correction whose cited facility_id
is absent, whose state disagrees, or whose tribe_id is not in the spine.

**NOT_NATIVE (71 rows, 6 groups).** These are commercial operators, and each is
refused on a POSITIVE demonstration of the capture token, never on absence from
a table - `docs/LABOR_SOURCES_FOR_GAMING_2026-08-26.md` s17 records that ~137
genuine tribal properties are MISSING from `gaming_facilities.csv`, so absence
from it proves nothing. They are MOVED to `review/`, not deleted: the filing is
real, the tribal attribution was not, and a tribal-gaming employment table is
not where a Delaware racino's Form 5500 belongs.

NO TIER IS ASSIGNED HERE
------------------------
The employment table has no tier column, so `164` links these rows at
`row_tribe_id_mirror` with a BLANK `entity_tier` and the basis "NOT INHERITED -
the source row carries no tier". That stays true after this repair. The
evidencing facility's own tier is recorded in `attribution_repair_basis` as
TEXT, so a reader can see what it rests on, and no consumer can read a tier off
a column that was never inherited.

SAFETY
  * backup tagged with THIS SCRIPT'S NAME: .bak_<date>_pre262
  * `.part` then rename
  * target re-read inside the write path, never cached
  * idempotent: a row already repaired is left alone
  * verifies by RE-READING the written file, not by trusting the run log

    py -3 code/262_repair_form5500_tribe_attribution.py --check
    py -3 code/262_repair_form5500_tribe_attribution.py --apply
"""

import csv
import shutil
import sys
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
LOGS = CEDAR / "logs"
SPINE = CEDAR / "data" / "spine" / "cedar_entity_spine.csv"
TARGET = CLEAN / "gaming_employment_observations.csv"
FACILITIES = CLEAN / "gaming_facilities.csv"
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

# ---------------------------------------------------------------------------
# THE RULING TABLE. Hand-built, one entry per sponsor group, each carrying the
# evidence that settles it. Nothing here is inferred at run time.
#
#   sponsor_name (exact, as filed)  ->  (disposition, tribe_id, facility_id,
#                                        expected_state, evidence)
# ---------------------------------------------------------------------------
CORRECT_TO = {
    # ---- `Eagle`, the Alaska Native village, capturing four Eagle brands ----
    "KICKAPOO TRIBE IN KANSAS GOLDEN EAGLE CASINO": (
        "TRBF-KCKPKS-00", "CCP-72200", "KS",
        "Cedar CCP-72200 'Golden Eagle Casino' KS is keyed TRBF-KCKPKS-00 at "
        "tier A method=exact; and the sponsor_name names the tribe in full "
        "('KICKAPOO TRIBE IN KANSAS'). Two independent legs."),
    "EAGLE MOUNTAIN CASINO": (
        "TRBF-TULERV-00", "CCP-249900", "CA",
        "Cedar CCP-249900 'Eagle Mountain Casino' CA is keyed TRBF-TULERV-00 "
        "at tier B method=core. Brand and state both agree."),
    "LUCKY EAGLE CASINO": (
        "TRBF-CHEHLS-00", "CCP-17050", "WA",
        "Cedar CCP-17050 'Lucky Eagle Casino & Hotel' WA is keyed "
        "TRBF-CHEHLS-00 at tier A method=alias. Brand and state both agree."),
    # ---- BIE school capturing a casino -------------------------------------
    "FOUR WINDS CASINO RESORT": (
        "TRBF-POKAGN-00", "CEDAR-FAC-000013", "MI",
        "Cedar CEDAR-FAC-000013 'Four Winds Casino Resort' MI is keyed "
        "TRBF-POKAGN-00, as are all six other Four Winds rows (VP-0295/6/7, "
        "CCP-639000/958100/1002700), unanimously, all at tier B. The staged "
        "row said BIE-TTTPTR-00 (Tate Topa Tribal School): 157's blocked_class "
        "rule already states a school cannot own a casino."),
    # ---- `Prairie` token capture -------------------------------------------
    "PRAIRIE WIND CASINO": (
        "TRBF-OGLALA-00", "VP-0366", "SD",
        "Cedar VP-0366 'Prairie Wind Casino' SD and CCP-114700 'Prairie Wind "
        "Casino & Hotel' SD are both keyed TRBF-OGLALA-00 at tier A "
        "method=alias. Prairie Band Potawatomi is a Kansas tribe."),
    "PRAIRIE KNIGHTS CASINO": (
        "TRBF-STNDRK-00", "CCP-22700", "ND",
        "Cedar CCP-22700 'Prairie Knights Casino & Resort' ND is keyed "
        "TRBF-STNDRK-00 at tier B method=containment."),
    # ---- same tribe name, different tribe -----------------------------------
    "SAC & FOX CASINO": (
        "TRBF-SCFXMO-00", "CCP-293600", "KS",
        "Cedar CCP-293600 'Sac & Fox Casino' KS is keyed TRBF-SCFXMO-00 (Sac & "
        "Fox of Missouri, in Kansas and Nebraska) at tier A method=alias; "
        "VP-0358 'Sac and Fox Casino' KS agrees at tier B. The staged row said "
        "TRBF-SCFXOK-00, the Oklahoma nation."),
    "SAC & FOX CASINO BENEFIT PLAN": (
        "TRBF-SCFXMO-00", "CCP-293600", "KS",
        "Same sponsor as 'SAC & FOX CASINO', filed under its benefit-plan "
        "name. Cedar CCP-293600 KS -> TRBF-SCFXMO-00."),
    "MESKWAKI BINGO/CASINO/HOTEL SAC & FOX TRIBE OF THE MISSISSIPPI": (
        "TRBF-SCFXMS-00", "CCP-65700", "IA",
        "Cedar CCP-65700 'Meskwaki Bingo Casino Hotel' IA is keyed "
        "TRBF-SCFXMS-00 at tier A method=alias; the sponsor_name also names "
        "'SAC & FOX TRIBE OF THE MISSISSIPPI' in full. Two independent legs."),
    "SEMINOLE NATION DIVISION OF COMMERCE": (
        "TRBF-SMNLOK-00", "CCP-305200", "OK",
        "Cedar keys all four Oklahoma Seminole properties (CCP-305200, "
        "CCP-648500, TPL-0127, TPL-0128) to TRBF-SMNLOK-00 and all eight "
        "Florida ones to TRBF-SMNLFL-00. The sponsor filed from OK."),
    "SEMINOLE NATION GAMING ENTERPRISE & DIVISION OF COMMERCE": (
        "TRBF-SMNLOK-00", "CCP-305200", "OK",
        "Same sponsor. Cedar's Oklahoma Seminole properties are "
        "TRBF-SMNLOK-00; the staged row said TRBF-SMNLFL-00 (Florida)."),
    "UNITED KEETOOWAH BAND OF CHEROKEE": (
        "TRBF-UKEETW-00", "CCP-410200", "OK",
        "The UKB is a separate federally recognized tribe, in the spine as "
        "TRBF-UKEETW-00; Cedar CCP-410200 'Keetoowah Cherokee Casino' OK is "
        "keyed to it. The staged row said TRBF-CHKNAT-00 (Cherokee Nation) on "
        "the containment of the token 'Cherokee'."),
    "UNITED KEETOOWAH BAND OF CHEROKEE INDIANS": (
        "TRBF-UKEETW-00", "CCP-410200", "OK",
        "Same sponsor, longer filed form. See above."),
}

# Sponsors whose state on the filing differs from the facility's state are
# listed here with the state the FACILITY is in, because the group is keyed on
# sponsor_name alone. A group appearing under two filing states is fine; the
# facility check is what gates the write.
STATE_EXEMPT_SPONSORS = {
    # UKB filed from both OK and KS in different years; the casino is in OK.
    "UNITED KEETOOWAH BAND OF CHEROKEE",
}

NOT_NATIVE = {
    "EAGLE GAMING, L.P.": (
        "COMMERCIAL_COLORADO_OPERATOR",
        "Filed from CO. Matched to AKNF-VEAGLE-00 (Native Village of Eagle, "
        "ALASKA) on the bare token 'Eagle'. Colorado's tribal gaming is at "
        "Towaoc (Ute Mountain Ute) and Ignacio (Southern Ute); no tribal "
        "casino operates under this name. Refused on the demonstrated token "
        "capture, not on absence from gaming_facilities.csv."),
    "COLORADO CASINO RESORTS, INC. DBA DOUBLE EAGLE HOTEL AND CASINO": (
        "COMMERCIAL_COLORADO_OPERATOR",
        "Filed from CO by a named corporate operator. Matched to "
        "AKNF-VEAGLE-00 on 'Eagle'. Cedar's only 'Double Eagle Casino' is "
        "CCP-38600 in WASHINGTON (Spokane Tribe) - a different state and a "
        "different property, which is why brand+state correctly refuses it."),
    "RBG, LLC DBA CASA BLANCA RESORT HOTEL AND CASINO": (
        "COMMERCIAL_NEVADA_OPERATOR",
        "Filed from NV by a named LLC. Matched to BIE-CSBLNC-00, Casa Blanca "
        "Community School, an ARIZONA BIE school. 157's blocked_class rule: a "
        "school cannot own a casino. The capture token is the place name "
        "'Casa Blanca'."),
    "HAWAIIAN GARDENS CASINO": (
        "COMMERCIAL_CALIFORNIA_CARD_ROOM",
        "Filed from CA. Matched to NHO-HWNCMM-00 ('Native Hawaiian "
        "Community'). Hawaiian Gardens is a CITY in Los Angeles County, "
        "California. This is the documented 'a place suffix makes a tribe "
        "name a place' failure, plus the cross-state CA/HI shape already "
        "recorded in AGENTS.md (Indian Pueblo Cultural Center NM -> Makaha "
        "Cultural Learning Center HI)."),
    "GAMING ENTERTAINMENT (DELAWARE), LLC": (
        "COMMERCIAL_DELAWARE_OPERATOR",
        "Filed from DE. Matched to TRBF-DELAWN-00, the Delaware Nation, an "
        "OKLAHOMA tribe. The parenthetical '(Delaware)' is the STATE, "
        "disambiguating the LLC's jurisdiction. Place-name capture."),
    "GAMING ENTERTAINMENT (DELAWARE),LLC": (
        "COMMERCIAL_DELAWARE_OPERATOR", "Same sponsor, punctuation variant."),
    "GAMING ENTERTAINMENT DELAWARE, L.L.C.": (
        "COMMERCIAL_DELAWARE_OPERATOR", "Same sponsor, punctuation variant."),
    "PRAIRIE MEADOWS RACE TRACK AND CASINO": (
        "COMMERCIAL_IOWA_RACINO",
        "Filed from IA. Matched to TRBF-PRAIRB-00 (Prairie Band Potawatomi, "
        "KANSAS) on the token 'Prairie'. Altoona, Iowa."),
    "PRAIRIE MEADOWS RACE TRACK AND CASINO, INC.": (
        "COMMERCIAL_IOWA_RACINO", "Same sponsor, filed-form variant."),
    "PRAIRIE MEADOWS RACETRACK & CASINO, INC.": (
        "COMMERCIAL_IOWA_RACINO", "Same sponsor, filed-form variant."),
    "PRAIRIE MEADOWSRACE TRACK AND CASINO": (
        "COMMERCIAL_IOWA_RACINO", "Same sponsor, filed-form variant (typo in "
        "the filing)."),
}

NEW_COLS = ["attribution_repaired_by", "attribution_repair_date",
            "attribution_repair_basis", "tribe_id_as_staged"]


def log(msg):
    LOGS.mkdir(exist_ok=True)
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"))
    with open(LOGS / f"262_repair_{TODAY}.log", "a", encoding="utf-8") as fh:
        fh.write(msg + "\n")


def read_csv(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def write_atomic(path, fields, rows):
    path = Path(path)
    part = path.with_suffix(path.suffix + ".part")
    with open(part, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    part.replace(path)


def verify_rulings():
    """REFUSE any CORRECT_TO whose evidence does not hold up. Read-only."""
    fac = {r["facility_id"]: r for r in read_csv(FACILITIES)}
    spine = {r["tribe_id"] for r in read_csv(SPINE)}
    bad = []
    for sponsor, (tid, fid, st, _ev) in CORRECT_TO.items():
        if tid not in spine:
            bad.append(f"{sponsor}: tribe_id {tid} NOT IN SPINE")
            continue
        f = fac.get(fid)
        if f is None:
            bad.append(f"{sponsor}: facility_id {fid} NOT IN gaming_facilities")
            continue
        if (f.get("tribe_id") or "").strip() != tid:
            bad.append(f"{sponsor}: {fid} is keyed "
                       f"{f.get('tribe_id')!r}, ruling says {tid!r}")
            continue
        if (f.get("state") or "").strip().upper() != st:
            bad.append(f"{sponsor}: {fid} state is {f.get('state')!r}, "
                       f"ruling says {st!r}")
            continue
        log(f"  OK  {sponsor[:46]:46} -> {tid} via {fid} "
            f"({f.get('state')}, facility tier "
            f"{f.get('entity_tier') or '(blank)'})")
    return bad


def spine_lookup():
    return {r["tribe_id"]: r for r in read_csv(SPINE)}


def classify(rows):
    """Partition the Form 5500 rows. Returns (fix, drop, untouched)."""
    fix, drop = [], []
    for r in rows:
        if r.get("measurement_type") != "FORM5500_ACTIVE_PARTICIPANTS":
            continue
        sp = (r.get("sponsor_name") or "").strip()
        if sp in CORRECT_TO:
            fix.append(r)
        elif sp in NOT_NATIVE:
            drop.append(r)
    return fix, drop


def main():
    apply_ = "--apply" in sys.argv
    log(f"=== Cedar Press 262: repair Form 5500 tribe attribution ({TODAY}) "
        f"[{'APPLY' if apply_ else 'CHECK, read-only'}] ===")

    log("\nverifying every CORRECT_TO ruling against gaming_facilities.csv "
        "and the spine:")
    bad = verify_rulings()
    if bad:
        log("\nREFUSING - a ruling did not verify:")
        for b in bad:
            log(f"  {b}")
        return 1
    log(f"  all {len(CORRECT_TO)} rulings verify")

    rows = read_csv(TARGET)
    if not rows:
        log(f"FATAL: {TARGET} empty or missing")
        return 1
    log(f"\ntarget holds {len(rows):,} rows")

    fix, drop = classify(rows)
    already = sum(1 for r in fix if r.get("attribution_repaired_by"))
    log(f"  rows to CORRECT_TO : {len(fix):,}  "
        f"({already} already repaired, will be left alone)")
    log(f"  rows to NOT_NATIVE : {len(drop):,}")

    by_fix = Counter((r.get("sponsor_name"), r.get("tribe_id")) for r in fix)
    log("\nCORRECT_TO, by sponsor:")
    for (sp, old), n in sorted(by_fix.items(), key=lambda x: -x[1]):
        new = CORRECT_TO[sp][0]
        log(f"  {n:4}  {sp[:50]:50} {old[:28]:28} -> {new}")
    by_drop = Counter(r.get("sponsor_name") for r in drop)
    log("\nNOT_NATIVE, by sponsor:")
    for sp, n in sorted(by_drop.items(), key=lambda x: -x[1]):
        log(f"  {n:4}  {sp[:50]:50} {NOT_NATIVE[sp][0]}")

    if not apply_:
        log("\n--check only. Nothing written. Re-run with --apply.")
        return 0

    # ---- (safety) back up under THIS script's name -------------------------
    bak = TARGET.with_suffix(f".csv.bak_{TODAY}_pre262")
    if not bak.exists():
        shutil.copy2(TARGET, bak)
    log(f"\nbacked up -> {bak.name}")

    # ---- re-read the target INSIDE the write path ---------------------------
    rows = read_csv(TARGET)
    fix, drop = classify(rows)
    drop_ids = {r["observation_id"] for r in drop}
    spine = spine_lookup()

    n_fixed = 0
    for r in fix:
        if r.get("attribution_repaired_by"):
            continue                                  # idempotent
        sp = r["sponsor_name"].strip()
        tid, fid, st, ev = CORRECT_TO[sp]
        r["tribe_id_as_staged"] = r.get("tribe_id", "")
        r["tribe_id"] = tid
        sr = spine.get(tid, {})
        r["cedar_entity_name"] = sr.get("canonical_name", "")
        r["entity_class"] = sr.get("entity_class", "")
        # the entity-link block is now stale for this row; 164 rewrites it
        for c in ("entity_id", "entity_tier", "entity_tier_basis",
                  "entity_link_rung", "entity_link_date"):
            if c in r:
                r[c] = ""
        r["attribution_repaired_by"] = "262_repair_form5500_tribe_attribution"
        r["attribution_repair_date"] = TODAY
        r["attribution_repair_basis"] = ev
        # the state_mismatch flag described the WRONG tribe; recompute it
        if "state_mismatch_flag" in r:
            r["state_mismatch_flag"] = (
                "0" if (r.get("sponsor_state") or "").upper()
                == (sr.get("state") or "").upper() else "1")
        n_fixed += 1

    kept = [r for r in rows if r.get("observation_id") not in drop_ids]

    fields = list(rows[0].keys())
    for c in NEW_COLS:
        if c not in fields:
            fields.append(c)

    write_atomic(TARGET, fields, kept)

    # ---- the refused rows go to review, not to the bin ----------------------
    REVIEW.mkdir(exist_ok=True)
    rf = REVIEW / f"form5500_gaming_not_native_{TODAY}.csv"
    out = []
    for r in drop:
        d = dict(r)
        d["refusal_class"] = NOT_NATIVE[r["sponsor_name"].strip()][0]
        d["refusal_reason"] = NOT_NATIVE[r["sponsor_name"].strip()][1]
        d["tribe_id_as_staged"] = r.get("tribe_id", "")
        d["tribe_id"] = ""
        d["entity_id"] = ""
        out.append(d)
    if out:
        rfields = list(out[0].keys())
        write_atomic(rf, rfields, out)

    # ---- (safety) VERIFY BY RE-READING, not by trusting the run log --------
    back = read_csv(TARGET)
    log("")
    log(f"repaired {n_fixed:,} rows in place")
    log(f"removed  {len(drop):,} non-Native rows -> review/{rf.name}")
    log(f"rows {len(rows):,} -> {len(back):,}  "
        f"(expected {len(rows) - len(drop):,})")

    ok = True
    if len(back) != len(rows) - len(drop):
        log("  FAIL: row count is not what was expected")
        ok = False
    still = [r for r in back
             if (r.get("sponsor_name") or "").strip() in NOT_NATIVE]
    if still:
        log(f"  FAIL: {len(still)} NOT_NATIVE rows survive in the target")
        ok = False
    wrong = [r for r in back
             if (r.get("sponsor_name") or "").strip() in CORRECT_TO
             and r.get("tribe_id")
             != CORRECT_TO[(r.get("sponsor_name") or "").strip()][0]]
    if wrong:
        log(f"  FAIL: {len(wrong)} CORRECT_TO rows still carry the old tribe")
        ok = False
    if len({r["observation_id"] for r in back}) != len(back):
        log("  FAIL: observation_id is no longer unique")
        ok = False
    log("  re-read verification: " + ("PASS" if ok else "FAIL"))
    if not ok:
        log(f"  RESTORE {bak.name}")
        return 1

    log("\nNOW RUN: py -3 code/164_link_facility_hub_sources.py "
        "(the repaired rows need their entity block rebuilt)")
    log("THEN:    py -3 code/62_no_regression_check.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
