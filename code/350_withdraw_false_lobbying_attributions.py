#!/usr/bin/env python3
"""
Cedar Press - 350: withdraw the false lobbying attributions the ORG-TYPE GUARD
could not see, IN PLACE, in the shipping file.

WHAT WAS ALREADY TRUE, AND WHY IT WAS NOT ENOUGH
------------------------------------------------
`65_lobbying_organization_type_guard.py` withdrew 841 filings / $39,425,500 on
2026-08-06 by barring LEGAL FORMS a Native entity cannot be: `CITY OF`,
`MINES`, `... POWER DISTRICT`, `SALT RIVER PROJECT`. That was right, and it is
still right.

**A name-form bar only catches the form it spells.** `docs/EDITORIAL_PIPELINE.md`
blocker 2 documents what walked straight past it, all still live at `medium`
in the shipping file this morning:

  TRBF-SROSAR-00  Santa Rosa Rancheria Tachi Tribe, California, alias `rosa santa`
      SANTA ROSA COUNTY FL / SANTA ROSA COUNTY, FL / SANTA ROSA COUNTY /
      SANTA ROSA CO BOARD OF SUPERVISORS      a FLORIDA COUNTY
      SANTA ROSA JUNIOR COLLEGE               a California community college
      TEAM SANTA ROSA / TEAM SANTA ROSA ECONOMIC DEVELOPMENT COUNCIL
                                              a Florida economic-development council
      SANTA ROSA MEMORIAL / ... HOSPITAL      a California hospital
      CHRISTUS SANTA ROSA HOSPITAL (+ CHILDRENS)  a Texas hospital system
      -> 220 filings / $3,100,334 on a tribe whose own filings are 13 / $210,000.
         In ROW COUNT that is a larger error than Salt River Project was.

  TRBF-CRDALN-00  COEUR D'ALENE MINING - the guard bars `MINES`, and this is
      the same company spelled `MINING`. 8 filings / $90,000.

  ANRC-BRBYCO-00  Bristol Bay Native Corporation, alias `bay bristol corp`
      BRISTOL BAY ECONOMIC DEVELOPMENT CORPORATION / CORP  - BBEDC is a
          separate CDQ nonprofit, not BBNC.        135 filings / $2,048,500
      BRISTOL BAY AREA HEALTH CORP / CORPORATION - BBAHC is a separate tribal
          health organisation, not BBNC.            99 filings / $500,000

  SGVF-BRBYAS-00  Bristol Bay Native Association, alias `association bay bristol`
      BRISTOL BAY REGIONAL SEAFOOD DEVELOPMENT ASSOCIATION / BRISTOL BAY
      DRIFTNETTERS ASSOCIATION - fishermen's groups.  9 filings / $18,000

WHY UNLINK AND NOT REPOINT
--------------------------
`data/spine/cedar_entity_spine.csv` was searched for every one of them. BBEDC,
BBAHC, the seafood associations and the Santa Rosa organisations have NO spine
entity. There is nothing to repoint to, so the honest state is UNLINKED, with
the evidence kept beside it. An entity that does not exist in the spine yet is
a spine task, not a licence to attach the filing to the nearest name.

WHY NOT TIER X
--------------
Because `169_build_identifier_graph.py` treats X as a statement about the
IDENTIFIER, and blocking `TRBF-SROSAR-00` would suppress the 13 filings that
genuinely ARE the Santa Rosa Rancheria Tachi Tribe. The identifier is sound.
The LINK on 471 specific filings is not. Unlink the link.

WHAT IS PRESERVED, DELIBERATELY
-------------------------------
`matched_alias`, `attribution_method` and `client_name` are UNTOUCHED. The
correction has to be VISIBLE, not erased: anyone auditing this file must be
able to see that `rosa santa` fired, that it fired on a Florida county, and
that a human refused it. Four new columns carry the refusal.

WHAT THIS DOES NOT TOUCH
------------------------
- Every `high`-confidence row. All 471 withdrawals are `medium`, so the
  publishable slice `docs/EDITORIAL_PIPELINE.md` names - **23,741 filings /
  $627,601,108** - is unchanged by this script, and that sentence stays true.
- The 841 rows script 65 already withdrew.
- SANTA ROSA RANCHERIA TACHI TRIBE (13 / $210,000), COEUR D'ALENE TRIBE,
  BRISTOL BAY NATIVE CORPORATION, BRISTOL BAY NATIVE ASSOCIATION - the real
  ones, kept exactly as they were.

REBUILD THAT WOULD UNDO THIS
----------------------------
`code/lobbying_pull/05_match_filings_v2.py` REBUILDS
`native_entity_lobbying_disclosures.csv` from `raw_filings.jsonl` and would
revert this AND script 65. Standing rule: the enricher runs LAST. If 05 is
ever re-run, run 65 and then 350, in that order, before anything reads the
file.

Reads/Writes  data/clean/native_entity_lobbying_disclosures.csv   (in place)
Writes        review/lobbying_withdrawn_false_attribution_2026-08-26.csv
              data/clean/cedar_correction_register.csv            (append)
"""

import csv
import importlib.util
import os
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

csv.field_size_limit(min(sys.maxsize, 2147483647))

CEDAR = Path(__file__).resolve().parent.parent
CODE = CEDAR / "code"
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()
SCRIPT = "350_withdraw_false_lobbying_attributions.py"

SRC = CLEAN / "native_entity_lobbying_disclosures.csv"
OUT_REVIEW = REVIEW / f"lobbying_withdrawn_false_attribution_{TODAY}.csv"

WITHDRAWN_CONF = "withdrawn_false_attribution"

NEW_COLS = ["attribution_withdrawn", "attribution_withdrawn_entity_id",
            "attribution_withdrawn_reason", "attribution_withdrawn_by_script",
            "attribution_withdrawn_date"]

# (entity_id, client_name EXACTLY as filed) -> the reason, verbatim.
# EXACT client strings, never a regex. A regex is what produced this defect;
# a second regex is not the fix for the first one. Every string below was read
# off the file and its subject identified by hand.
WITHDRAWALS = {
    ("TRBF-SROSAR-00", "SANTA ROSA COUNTY FL"):
        "Santa Rosa County, FLORIDA - a county government, not the Santa Rosa "
        "Rancheria Tachi Tribe of California. Matched on the token pair "
        "'rosa santa'.",
    ("TRBF-SROSAR-00", "SANTA ROSA COUNTY, FL"):
        "Santa Rosa County, FLORIDA - a county government, not the Santa Rosa "
        "Rancheria Tachi Tribe of California. Matched on the token pair "
        "'rosa santa'.",
    ("TRBF-SROSAR-00", "SANTA ROSA COUNTY"):
        "Santa Rosa County, FLORIDA - a county government, not the Santa Rosa "
        "Rancheria Tachi Tribe of California. Matched on the token pair "
        "'rosa santa'.",
    ("TRBF-SROSAR-00", "SANTA ROSA CO BOARD OF SUPERVISORS"):
        "The Santa Rosa County, FLORIDA board of supervisors - a county "
        "government body, not the Santa Rosa Rancheria Tachi Tribe.",
    ("TRBF-SROSAR-00", "SANTA ROSA JUNIOR COLLEGE"):
        "Santa Rosa Junior College, a California community college - not a "
        "tribal college and not the Santa Rosa Rancheria Tachi Tribe.",
    ("TRBF-SROSAR-00", "TEAM SANTA ROSA ECONOMIC DEVELOPMENT COUNCIL"):
        "Team Santa Rosa, the economic development council of Santa Rosa "
        "County, FLORIDA - not the Santa Rosa Rancheria Tachi Tribe.",
    ("TRBF-SROSAR-00", "TEAM SANTA ROSA"):
        "Team Santa Rosa, the economic development council of Santa Rosa "
        "County, FLORIDA - not the Santa Rosa Rancheria Tachi Tribe.",
    ("TRBF-SROSAR-00", "SANTA ROSA MEMORIAL"):
        "Santa Rosa Memorial Hospital, a California hospital - not the Santa "
        "Rosa Rancheria Tachi Tribe.",
    ("TRBF-SROSAR-00", "SANTA ROSA MEMORIAL HOSPITAL"):
        "Santa Rosa Memorial Hospital, a California hospital - not the Santa "
        "Rosa Rancheria Tachi Tribe.",
    ("TRBF-SROSAR-00", "CHRISTUS SANTA ROSA HOSPITAL"):
        "CHRISTUS Santa Rosa, a Texas hospital system - not the Santa Rosa "
        "Rancheria Tachi Tribe.",
    ("TRBF-SROSAR-00", "CHRISTUS SANTA ROSA CHILDRENS HOSPITAL"):
        "CHRISTUS Santa Rosa Children's Hospital, a Texas hospital - not the "
        "Santa Rosa Rancheria Tachi Tribe.",

    ("TRBF-CRDALN-00", "COEUR D'ALENE MINING"):
        "Coeur d'Alene Mining, the mining company - not the Coeur d'Alene "
        "Tribe. Script 65 bars the spelling 'MINES' and this is the same "
        "company spelled 'MINING': a correction that covers one spelling and "
        "not its variant.",

    ("ANRC-BRBYCO-00", "BRISTOL BAY ECONOMIC DEVELOPMENT CORPORATION"):
        "Bristol Bay Economic Development Corporation (BBEDC) is a separate "
        "CDQ nonprofit representing 17 Bristol Bay communities. It is NOT "
        "Bristol Bay Native Corporation. Matched on 'bay bristol corp'. No "
        "spine entity exists for BBEDC, so this is unlinked, not repointed.",
    ("ANRC-BRBYCO-00", "BRISTOL BAY ECONOMIC DEVELOPMENT CORP"):
        "Bristol Bay Economic Development Corporation (BBEDC) is a separate "
        "CDQ nonprofit. It is NOT Bristol Bay Native Corporation.",
    ("ANRC-BRBYCO-00", "BRISTOL BAY AREA HEALTH CORP"):
        "Bristol Bay Area Health Corporation (BBAHC) is a separate tribal "
        "health organisation. It is NOT Bristol Bay Native Corporation. "
        "Matched on 'bay bristol corp'.",
    ("ANRC-BRBYCO-00", "BRISTOL BAY AREA HEALTH CORPORATION"):
        "Bristol Bay Area Health Corporation (BBAHC) is a separate tribal "
        "health organisation. It is NOT Bristol Bay Native Corporation.",

    ("SGVF-BRBYAS-00", "BRISTOL BAY REGIONAL SEAFOOD DEVELOPMENT ASSOCIATION"):
        "A regional seafood development association of fishermen - not the "
        "Bristol Bay Native Association. Matched on 'association bay bristol'.",
    ("SGVF-BRBYAS-00", "BRISTOL BAY DRIFTNETTERS ASSOCIATION"):
        "A driftnet fishermen's association - not the Bristol Bay Native "
        "Association. Matched on 'association bay bristol'.",
}


def load_register():
    spec = importlib.util.spec_from_file_location(
        "reg354", CODE / "354_correction_register.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def read_csv(p):
    with open(p, newline="", encoding="utf-8-sig", errors="replace") as fh:
        return list(csv.DictReader(fh)), None


def declare_from_markers(rows):
    """Re-state the register declaration from the file's own markers."""
    per = defaultdict(lambda: {"n": 0, "reason": ""})
    for r in rows:
        if (r.get("attribution_withdrawn") or "") != "1":
            continue
        if (r.get("attribution_withdrawn_by_script") or "") != SCRIPT:
            continue
        k = ((r.get("attribution_withdrawn_entity_id") or "").strip(),
             (r.get("client_name") or "").strip())
        per[k]["n"] += 1
        per[k]["reason"] = r.get("attribution_withdrawn_reason") or ""
    reg = load_register()
    decl = [{
        "finding_id": "FA-01", "entity_id": eid, "withdrawn_key": cname,
        "table": SRC.name, "column_unlinked": "entity_id",
        "rows_affected": v["n"], "rows_removed": 0, "action": "UNLINK",
        "repointed_to": "",
        "provenance_preserved":
            "client_name; matched_alias; attribution_method; spend_usd",
        "reason": v["reason"],
    } for (eid, cname), v in sorted(per.items())]
    n = reg.record(decl, SCRIPT)
    print(f"  {len(decl)} declaration(s) re-asserted, {n} newly written to "
          f"{reg.REGISTER.relative_to(CEDAR)}")
    return 0


def main():
    print(f"=== Cedar Press 350: withdraw false lobbying attributions ===\n")

    before_mtime = SRC.stat().st_mtime
    rows, _ = read_csv(SRC)
    fields = list(rows[0].keys())
    print(f"  {SRC.name}: {len(rows):,} filings, {len(fields)} columns")

    for c in NEW_COLS:
        if c not in fields:
            fields.append(c)

    per_client = defaultdict(lambda: {"n": 0, "usd": 0.0, "alias": "",
                                      "entity": "", "reason": "",
                                      "canonical": "", "years": set()})
    n_hit = 0
    unseen = set(WITHDRAWALS)
    for r in rows:
        for c in NEW_COLS:
            r[c] = r.get(c) or ""
        key = ((r.get("entity_id") or "").strip(),
               (r.get("client_name") or "").strip())
        if key not in WITHDRAWALS:
            continue
        unseen.discard(key)
        reason = WITHDRAWALS[key]
        k = per_client[key]
        k["n"] += 1
        k["usd"] += float(r.get("spend_usd") or 0)
        k["alias"] = r.get("matched_alias") or k["alias"]
        k["canonical"] = r.get("canonical_name") or k["canonical"]
        k["entity"] = key[0]
        k["reason"] = reason
        if r.get("filing_year"):
            k["years"].add(r["filing_year"])

        # THE WITHDRAWAL. `matched_alias`, `attribution_method`, `client_name`
        # and every dollar column are left exactly as recorded - the evidence
        # of what fired stays in the row.
        r["attribution_withdrawn"] = "1"
        r["attribution_withdrawn_entity_id"] = key[0]
        r["attribution_withdrawn_reason"] = reason
        r["attribution_withdrawn_by_script"] = SCRIPT
        r["attribution_withdrawn_date"] = TODAY
        r["entity_id"] = ""
        r["canonical_name"] = ""
        r["entity_type"] = ""
        r["entity_state"] = ""
        r["match_confidence"] = WITHDRAWN_CONF
        n_hit += 1

    if unseen:
        # A declared withdrawal that matched nothing is either already applied
        # or misspelled, and the two must not print the same way.
        print(f"\n  !! {len(unseen)} declared withdrawal(s) matched NO row - "
              f"already applied, or the client string moved:")
        for k in sorted(unseen):
            print(f"       {k[0]}  {k[1]!r}")

    total_usd = sum(v["usd"] for v in per_client.values())
    print(f"\n  filings withdrawn : {n_hit:,}")
    print(f"  spend withdrawn   : ${total_usd:,.2f}")
    print(f"  clients withdrawn : {len(per_client)}\n")
    for (eid, cname), v in sorted(per_client.items(),
                                  key=lambda kv: -kv[1]["usd"]):
        print(f"     {v['n']:>4}  ${v['usd']:>12,.0f}  {cname[:46]:46s} "
              f"was -> {eid}")

    if n_hit == 0:
        # ALREADY APPLIED. Re-assert the DECLARATION anyway, from the marker
        # columns in the file itself. A script that applies a correction must
        # be able to re-state it without re-applying it - otherwise the
        # register can only ever be written by the run that happened to be
        # first, and a lost register can never be rebuilt from the data.
        print("\n  no live false links; re-asserting the declaration from the "
              "withdrawal markers already in the file.")
        return declare_from_markers(rows)

    # --- concurrency: nobody else may have written while we were thinking ---
    if SRC.stat().st_mtime != before_mtime:
        print(f"\n  !! {SRC.name} CHANGED UNDER US "
              f"(mtime moved). Refusing to write. Re-run.")
        return 2

    bak = SRC.with_name(SRC.name + f".bak_{TODAY}_pre_{SCRIPT}")
    if not bak.exists():
        bak.write_bytes(SRC.read_bytes())
        print(f"\n  backed up -> {bak.name}")

    part = SRC.with_suffix(SRC.suffix + ".part")
    with open(part, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})
    os.replace(part, SRC)
    print(f"  wrote {SRC.name}")

    REVIEW.mkdir(parents=True, exist_ok=True)
    with open(OUT_REVIEW, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["client_name_as_filed", "withdrawn_from_entity_id",
                    "withdrawn_from_canonical_name", "matched_alias",
                    "n_filings", "spend_usd", "first_year", "last_year",
                    "reason", "withdrawn_by_script", "withdrawn_date"])
        for (eid, cname), v in sorted(per_client.items(),
                                      key=lambda kv: -kv[1]["usd"]):
            yrs = sorted(v["years"])
            w.writerow([cname, eid, v["canonical"], v["alias"], v["n"],
                        round(v["usd"], 2), yrs[0] if yrs else "",
                        yrs[-1] if yrs else "", v["reason"], SCRIPT, TODAY])
    print(f"  wrote {OUT_REVIEW.relative_to(CEDAR)}")

    # --- declare it, so a sibling table that never got it becomes visible ---
    reg = load_register()
    decl = []
    for (eid, cname), v in per_client.items():
        decl.append({
            "finding_id": "FA-01",
            "entity_id": eid,
            "withdrawn_key": cname,
            "table": SRC.name,
            "column_unlinked": "entity_id",
            "rows_affected": v["n"],
            "rows_removed": 0,
            "action": "UNLINK",
            "repointed_to": "",
            "provenance_preserved":
                "client_name; matched_alias; attribution_method; spend_usd",
            "reason": v["reason"],
        })
    n = reg.record(decl, SCRIPT)
    print(f"  declared {n} correction(s) in "
          f"{reg.REGISTER.relative_to(CEDAR)}")

    # --- verify by RE-READING, never by trusting the run log (rule 4) -------
    back, _ = read_csv(SRC)
    still = sum(1 for r in back
                if ((r.get("entity_id") or "").strip(),
                    (r.get("client_name") or "").strip()) in WITHDRAWALS)
    marked = sum(1 for r in back if r.get("attribution_withdrawn") == "1")
    from collections import Counter
    conf = Counter(r.get("match_confidence") for r in back)
    print(f"\n  RE-READ: {len(back):,} rows · still falsely linked {still} "
          f"(must be 0) · marked withdrawn {marked}")
    print(f"           match_confidence: "
          f"{', '.join(f'{k}={v:,}' for k, v in conf.most_common())}")
    high_usd = sum(float(r.get("spend_usd") or 0)
                   for r in back if r.get("match_confidence") == "high")
    print(f"           the PUBLISHABLE slice is unchanged: high = "
          f"{conf.get('high', 0):,} filings / ${high_usd:,.0f}")
    return 0 if still == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
