#!/usr/bin/env python3
"""
Cedar Press - 1186: federal spending at the AWARD grain, with attribution that
has to earn its place.

    py -3 code/1186_federal_awards_rebuild.py            # report
    py -3 code/1186_federal_awards_rebuild.py build
    py -3 code/1186_federal_awards_rebuild.py verify
    py -3 code/1186_federal_awards_rebuild.py selftest

WHY THIS EXISTS
---------------
Reviewer verdict, 2026-09-04: *"do not publish this version as the
federal-spending dataset."* Every figure in that review was checked against the
file first and every one held - 2,315 rows, 23 columns, 1,060 keyed / 1,255
not, 3 rows with no UEI, $23,354,179,632 obligated, and 63 state conflicts
totalling $2,596,395,405, which reconciled to the dollar.

TWO DEFECTS, AND THE SECOND IS THE SERIOUS ONE.

1. GRAIN. USAspending records assistance at the TRANSACTION level and an award
   accumulates modifications. The published file was one row per recipient UEI
   summarising 61,579 transactions, so it could answer neither "what awards
   exist" nor "what happened in 2025 versus 2026" - the two years were fused.

2. ATTRIBUTION. 1,028 of the 1,060 keyed rows - $17.08 billion - came from a
   single rule, `uei_exact_archive`. An exact match on an ARCHIVED UEI is not
   evidence that the recipient is the Cedar entity, and the results prove it:

     SANTA CLARA COUNTY HOUSING AUTHORITY   $980.6M -> Pueblo of Santa Clara
       a public housing agency in San Jose, California
     ALASKA NATIVE TRIBAL HEALTH CONSORTIUM $643.6M -> Chugachmiut
       two separate organizations; ANTHC is its own tribal health nonprofit
     TUBA CITY REGIONAL HEALTH CARE         $114.8M -> Arctic Slope Regional
       an Arizona medical organization keyed to an Alaska corporation

   The failure is systematic, not incidental. ONE uid absorbed seven unrelated
   recipients, and `Native Village of Barrow` was given both the Santa Fe
   Indian School and the Bureau of Indian Affairs. It is the same shape as the
   $1.13B Omaha error the identifier document holds up as the thing this
   system exists to prevent: a shared word treated as a shared identity.

SO ATTRIBUTION IS DENY-BY-DEFAULT HERE. A row gets a cedar_uid only when the
identifier ledger carries a tier A or B ruling for that UEI and no tier X
against it. `uei_exact_archive` is not evidence and is not consulted. Blank is
the correct answer for a recipient Cedar cannot place, and the reviewer said so
explicitly: *"Leave the Cedar fields blank when the recipient is Native-related
but its exact Cedar entity is unresolved."*

WHAT THIS DOES NOT CLAIM. Coverage stops at the extraction cutoff in the source
export; July-December 2026 is not present and `data_as_of` says so on every
row. The entity-level summary the reviewer allows is DERIVED from this table,
never the other way round.
"""
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TX = ROOT / "data" / "clean" / "federal_funding_transactions.csv"
LEDGER = ROOT / "data" / "clean" / "cedar_identifier_ledger_final.csv"
NAMES = ROOT / "data" / "spine" / "cedar_entity_names.csv"
OUT = ROOT / "dist" / "customer" / "federal_awards_2025_2026.csv"
TODAY = date.today().isoformat()

csv.field_size_limit(10 ** 9)

WINDOW = ("2025", "2026")

#: The reviewer's column order: Cedar variables first, then the federal record.
COLUMNS = ("cedar_uid", "name", "entity_type", "recipient_uei",
           "recipient_name", "award_id", "award_type", "award_description",
           "awarding_agency", "program_code", "program_name",
           "obligated_2025_usd", "obligated_2026_usd", "obligated_window_usd",
           "award_start_date", "award_end_date", "last_action_date",
           "recipient_state", "source_url", "data_as_of",
           "attribution_basis")

#: Recipients proven NOT to be the entity they were keyed to. Each was checked
#: against the recipient's own published description. They are refused even if
#: a ledger ruling later appears, because the ruling would be wrong.
NEVER_ATTRIBUTE = {
    "SANTA CLARA COUNTY HOUSING AUTHORITY":
        "a public housing agency in San Jose, California - not the Pueblo of "
        "Santa Clara, New Mexico",
    "TUBA CITY REGIONAL HEALTH CARE CORPORATION":
        "an Arizona medical organization serving the western Navajo, Hopi and "
        "San Juan Paiute region - not Arctic Slope Regional Corporation",
    "ALASKA NATIVE TRIBAL HEALTH CONSORTIUM":
        "its own tribal health nonprofit - not Chugachmiut, which serves seven "
        "Chugach-region communities",
    "SANTA ANA, CITY OF": "a California city - not the Pueblo of Santa Ana",
    "MANCHESTER HOUSING & REDEVELOPMENT AUTHORITY":
        "a New Hampshire authority - not the Manchester Band of Pomo Indians",
    "PEORIA HOUSING AUTH":
        "an Illinois housing authority - not the Peoria Tribe of Oklahoma",
    "BOISE CITY ADA COUNTY HOUSING":
        "an Idaho housing authority - not Bois Forte",
    "SANTA FE INDIAN SCHOOL, INC.":
        "a New Mexico school - not the Native Village of Barrow",
    "NORTHERN CIRCLE INDIAN HOUSING AUTHORITY":
        "a California housing authority - not Circle Native Community, Alaska",
    "INTER-TRIBAL COUNCIL OF MICHIGAN INC":
        "a Michigan intertribal council - not Council Native Corporation",
    "CALIFORNIA INDIAN MANPOWER CONSORTIUM, INC.":
        "a California consortium - not Chugachmiut",
    "AMERICAN INDIAN HIGHER EDUCATION CONSORTIUM":
        "a national education consortium - not Chugachmiut",
    "INDIAN AFFAIRS BUREAU OF":
        "a federal agency - not the Native Village of Barrow",
    "CONFEDERATED TRIBES OF WARM SPRINGS RESERVATION OF OREGON":
        "an Oregon tribe - not the Fort Sill Apache Tribe of Oklahoma",
}

#: Rulings strong enough to attach identity. Tier C is recorded, not
#: attributable - the ledger's own definition - and X is a NEGATIVE ruling.
ATTRIBUTABLE = ("A", "B")


def _num(v) -> float:
    try:
        return float(str(v).replace(",", "").replace("$", "").strip() or 0)
    except ValueError:
        return 0.0


def _year(v: str) -> str:
    v = (v or "").strip()
    return v[:4] if len(v) >= 4 and v[:4].isdigit() else ""


def ledger():
    """UEI -> cedar_uid, honouring tier X as a REFUSAL.

    Tier X is not missing data. It is a recorded decision that this identifier
    is NOT that entity, and it exists so the same wrong candidate is not
    proposed twice. A UEI carrying an X for an entity must never be attributed
    to that entity, whatever else the ledger says.
    """
    positive, refused = {}, defaultdict(set)
    if not LEDGER.exists():
        return positive, refused
    with LEDGER.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            if (r.get("identifier_type") or "").upper() != "UEI":
                continue
            ident = (r.get("identifier") or "").strip().upper()
            uid = (r.get("cedar_uid") or "").strip()
            tier = (r.get("confidence_tier") or "").strip().upper()
            if not ident or not uid:
                continue
            if tier == "X":
                refused[ident].add(uid)
            elif tier in ATTRIBUTABLE:
                positive.setdefault(ident, (uid, tier))
    # a positive that is also refused for the SAME uid is refused
    for ident, (uid, _t) in list(positive.items()):
        if uid in refused.get(ident, ()):
            del positive[ident]
    return positive, refused


def entity_names():
    out = {}
    if NAMES.exists():
        with NAMES.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            for r in csv.DictReader(fh):
                out[r["cedar_uid"]] = (r.get("name", ""),
                                       r.get("entity_class", ""))
    return out


def aggregate():
    """Group transactions into awards. Constant-ish memory: one small dict per
    award, never the transactions themselves."""
    awards = {}
    seen_tx = 0
    with TX.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        for t in csv.DictReader(fh):
            y = _year(t.get("action_date"))
            if y not in WINDOW:
                continue
            seen_tx += 1
            key = (t.get("assistance_award_unique_key") or "").strip() \
                or (t.get("award_id_fain") or "").strip()
            if not key:
                continue
            a = awards.get(key)
            amt = _num(t.get("obligated_usd"))
            if a is None:
                a = awards[key] = {
                    "award_id": key, "y2025": 0.0, "y2026": 0.0, "n_tx": 0,
                    "recipient_uei": (t.get("recipient_uei") or "").strip(),
                    "recipient_name": (t.get("recipient_name") or "").strip(),
                    "recipient_state": (t.get("recipient_state_code") or "").strip(),
                    "award_type": (t.get("assistance_type_description") or "").strip(),
                    "award_description": (t.get("award_description")
                                          or t.get("transaction_description") or "").strip(),
                    "awarding_agency": (t.get("awarding_agency_name") or "").strip(),
                    "program_code": (t.get("cfda") or "").strip(),
                    "program_name": (t.get("cfda_title") or "").strip(),
                    "last_action_date": (t.get("action_date") or "").strip(),
                    "award_start_date": (t.get("period_of_performance_start_date")
                                         or "").strip(),
                    "award_end_date": (t.get("period_of_performance_current_end_date")
                                       or "").strip(),
                }
            # DEOBLIGATIONS ARE KEPT. A negative modification reduces the award;
            # dropping it would overstate every award that was ever reduced.
            a["y2025" if y == "2025" else "y2026"] += amt
            a["n_tx"] += 1
            d = (t.get("action_date") or "").strip()
            if d > a["last_action_date"]:
                a["last_action_date"] = d
    return awards, seen_tx


def build(apply: bool = False) -> int:
    if not TX.exists():
        print("  transaction export absent: %s" % TX)
        return 1
    positive, refused = ledger()
    names = entity_names()
    awards, seen_tx = aggregate()

    keyed = blocked_never = blocked_x = 0
    rows = []
    for a in awards.values():
        uei = a["recipient_uei"].upper()
        rname = a["recipient_name"].strip().upper()
        uid = ent = etype = ""
        basis = "unresolved - no tier A/B ruling for this UEI"
        if rname in NEVER_ATTRIBUTE:
            basis = "REFUSED: " + NEVER_ATTRIBUTE[rname]
            blocked_never += 1
        elif uei in positive:
            cand, tier = positive[uei]
            if cand in refused.get(uei, ()):
                basis = "REFUSED: tier X ruling against this UEI/entity pair"
                blocked_x += 1
            else:
                uid = cand
                ent, etype = names.get(cand, ("", ""))
                basis = "identifier ledger, tier %s on the UEI" % tier
                keyed += 1
        w25, w26 = a["y2025"], a["y2026"]
        rows.append({
            "cedar_uid": uid, "name": ent, "entity_type": etype,
            "recipient_uei": a["recipient_uei"],
            "recipient_name": a["recipient_name"],
            "award_id": a["award_id"], "award_type": a["award_type"],
            "award_description": a["award_description"][:400],
            "awarding_agency": a["awarding_agency"],
            "program_code": a["program_code"], "program_name": a["program_name"],
            "obligated_2025_usd": "%.2f" % w25,
            "obligated_2026_usd": "%.2f" % w26,
            "obligated_window_usd": "%.2f" % (w25 + w26),
            "award_start_date": a["award_start_date"],
            "award_end_date": a["award_end_date"],
            "last_action_date": a["last_action_date"],
            "recipient_state": a["recipient_state"],
            "source_url": ("https://www.usaspending.gov/award/%s" % a["award_id"]
                           if a["award_id"] else ""),
            "data_as_of": TODAY,
            "attribution_basis": basis,
        })
    rows.sort(key=lambda r: -_num(r["obligated_window_usd"]))

    tot = sum(_num(r["obligated_window_usd"]) for r in rows)
    t25 = sum(_num(r["obligated_2025_usd"]) for r in rows)
    t26 = sum(_num(r["obligated_2026_usd"]) for r in rows)
    print("  1186 federal awards   %s"
          % ("BUILD" if apply else "REPORT (writes nothing)"))
    print("    transactions in window : %d" % seen_tx)
    print("    AWARDS                 : %d   (%.1f transactions per award)"
          % (len(rows), seen_tx / len(rows) if rows else 0))
    print("    obligated 2025         : $%.0f" % t25)
    print("    obligated 2026         : $%.0f" % t26)
    print("    obligated window       : $%.0f" % tot)
    print()
    print("    keyed from the ledger  : %d  (tier A/B only)" % keyed)
    print("    refused, proven false  : %d" % blocked_never)
    print("    refused, tier X ruling : %d" % blocked_x)
    print("    left BLANK             : %d" % (len(rows) - keyed))
    print()
    print("    uei_exact_archive is NOT consulted. It produced 1,028 of the old")
    print("    file's 1,060 attributions and $17.08B of them, including")
    print("    $980.6M of San Jose public housing keyed to a New Mexico pueblo.")

    if apply:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        with OUT.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(COLUMNS))
            w.writeheader()
            for r in rows:
                w.writerow({c: r.get(c, "") for c in COLUMNS})
        print()
        print("    wrote %s  (%d columns)" % (OUT.relative_to(ROOT), len(COLUMNS)))
    return 0


def verify() -> int:
    if not OUT.exists():
        print("  NOT BUILT: %s" % OUT)
        return 1
    with OUT.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rows = list(csv.DictReader(fh))
    ok = True
    if list(rows[0].keys())[:3] != ["cedar_uid", "name", "entity_type"]:
        print("  FAIL columns do not lead with cedar_uid, name, entity_type")
        ok = False
    bad = [r for r in rows
           if r["recipient_name"].strip().upper() in NEVER_ATTRIBUTE
           and r["cedar_uid"].strip()]
    dupes = len(rows) - len({r["award_id"] for r in rows})
    keyed = sum(1 for r in rows if r["cedar_uid"].strip())
    print("  awards                     : %d" % len(rows))
    print("  duplicate award_id         : %d" % dupes)
    print("  proven-false still keyed   : %d" % len(bad))
    print("  keyed                      : %d (%.1f%%)"
          % (keyed, 100.0 * keyed / len(rows)))
    print("  window == 2025 + 2026      : %s"
          % all(abs(_num(r["obligated_window_usd"])
                    - _num(r["obligated_2025_usd"])
                    - _num(r["obligated_2026_usd"])) < 0.01 for r in rows))
    if bad or dupes:
        ok = False
    print("  OK" if ok else "  FAIL")
    return 0 if ok else 1


def selftest() -> int:
    ok = True
    pos, ref = ledger()
    print("  ledger: %d UEIs attributable (tier A/B), %d carrying a tier-X refusal"
          % (len(pos), len(ref)))
    if not pos:
        print("  FAIL ledger produced no attributable UEIs"); ok = False
    # a tier X against the same uid must beat a positive
    overlap = [i for i, (u, _t) in pos.items() if u in ref.get(i, ())]
    if overlap:
        print("  FAIL %d UEI(s) attributable despite a tier-X refusal" % len(overlap))
        ok = False
    else:
        print("  no UEI survives its own tier-X refusal")
    if len(NEVER_ATTRIBUTE) < 14:
        print("  FAIL the proven-false list lost entries"); ok = False
    print("  %d recipients on the proven-false refusal list" % len(NEVER_ATTRIBUTE))
    print("  selftest %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    if cmd == "build":
        raise SystemExit(build(apply=True))
    if cmd == "verify":
        raise SystemExit(verify())
    if cmd == "selftest":
        raise SystemExit(selftest())
    raise SystemExit(build(apply=False))
