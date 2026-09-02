"""39_contracts_match.py — match the 2023-04-05..2026-08-05 contract gapfill to
the identifier ledger, and emit spiderweb expansion CANDIDATES.

INPUTS
  data/raw/contracts/usaspending_gapfill_2026-08-05/*.zip   (script 37)
  data/clean/cedar_identifier_ledger_final.csv              (ONLY attribution source)
  data/spine/cedar_exclusion_rulings.csv                    (blocks)

OUTPUTS (all NEW files; data/clean/ is not modified)
  data/raw/contracts/usaspending_gapfill_2026-08-05/_SOURCE.md
  data/raw/contracts/usaspending_gapfill_2026-08-05/gapfill_recipient_universe.csv
  review/contract_spiderweb_candidates_2026-08-05.csv

ATTRIBUTION RULES
  * A recipient is "matched" ONLY on an EXACT recipient_uei present in the
    ledger. No name matching anywhere in this script.
  * Spiderweb candidates are CANDIDATES. They are written with the evidence
    (shared parent UEI, that parent's ledger tier and canonical name) and are
    NOT attributed to any entity. `parent_award_id` / recipient_parent_uei is a
    corporate-parent claim made by the FPDS registration, nothing more.
  * UEI NW2RJN8TQQW1 ("GOVERNMENT OF THE UNITED STATES") is a federal registrant
    roll-up, not a corporate owner. It is blocked as a spiderweb parent.
  * Any parent carrying an exclusion ruling is blocked.
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys
import zipfile
from collections import defaultdict
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw", "contracts", "usaspending_gapfill_2026-08-05")
REVIEW = os.path.join(ROOT, "review")
LEDGER = os.path.join(ROOT, "data", "clean", "cedar_identifier_ledger_final.csv")
EXCL = os.path.join(ROOT, "data", "spine", "cedar_exclusion_rulings.csv")
LOGFILE = os.path.join(ROOT, "logs", "39_contracts_match.log")

FED_ROLLUP = "NW2RJN8TQQW1"
FLAG_COLS = ["alaskan_native_corporation_owned_firm", "american_indian_owned_business",
             "tribally_owned_firm", "native_hawaiian_organization_owned_firm",
             "indian_tribe_federally_recognized", "us_tribal_government",
             "housing_authorities_public_tribal", "tribal_college"]


def log(msg):
    line = f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')}] {msg}"
    print(line, flush=True)
    os.makedirs(os.path.dirname(LOGFILE), exist_ok=True)
    with open(LOGFILE, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def money(v):
    try:
        return float(str(v).replace(",", "").replace("$", ""))
    except Exception:
        return 0.0


def main():
    # ---- ledger
    led = {}
    for r in csv.DictReader(open(LEDGER, encoding="utf-8-sig")):
        if r["identifier_type"] != "UEI":
            continue
        # keep the strongest tier seen for a UEI
        cur = led.get(r["identifier"])
        rank = {"A": 0, "B": 1, "C": 2, "X": 3}
        if cur is None or rank.get(r["confidence_tier"], 9) < rank.get(cur["confidence_tier"], 9):
            led[r["identifier"]] = r
    log(f"ledger UEIs: {len(led):,}")

    blocked = {r["identifier"] for r in csv.DictReader(open(EXCL, encoding="utf-8-sig"))
               if r["identifier_type"] == "UEI"}
    blocked.add(FED_ROLLUP)
    log(f"blocked parent UEIs: {len(blocked)}")

    # ---- read every staged award-summary file
    state = json.load(open(os.path.join(RAW, "_state.json"), encoding="utf-8"))
    uni = {}
    n_rows = 0
    n_dupe = 0
    seen_awards = set()      # LEGACY_WINDOWS overlaps w1; dedup or n_awards inflates
    files_read = []
    for jk in sorted(state.get("jobs", {})):
        p = os.path.join(RAW, jk + ".zip")
        if not os.path.exists(p):
            log(f"WARN {jk}.zip missing")
            continue
        files_read.append(jk)
        with zipfile.ZipFile(p) as z:
            for m in z.namelist():
                if not m.lower().endswith(".csv") or "Subawards" in m:
                    continue
                with z.open(m) as fh:
                    for r in csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8-sig")):
                        n_rows += 1
                        ak = r.get("contract_award_unique_key") or ""
                        if ak:
                            if ak in seen_awards:
                                n_dupe += 1
                                continue
                            seen_awards.add(ak)
                        u = (r.get("recipient_uei") or "").strip().upper()
                        if not u:
                            continue
                        d = uni.get(u)
                        if d is None:
                            d = uni[u] = {
                                "recipient_uei": u,
                                "recipient_name": r.get("recipient_name", ""),
                                "cage_code": r.get("cage_code", ""),
                                "recipient_parent_uei": "",
                                "recipient_parent_name": "",
                                "n_awards": 0, "total_obligated_usd": 0.0,
                                "first_action_date": "", "last_action_date": "",
                                "example_award_id_piid": r.get("award_id_piid", ""),
                                "example_parent_award_id_piid": r.get("parent_award_id_piid", ""),
                                "awarding_agency_example": r.get("awarding_agency_name", ""),
                                "flags": set(),
                            }
                        d["n_awards"] += 1
                        d["total_obligated_usd"] += money(r.get("total_obligated_amount"))
                        pu = (r.get("recipient_parent_uei") or "").strip().upper()
                        if pu and pu != u:
                            d["recipient_parent_uei"] = pu
                            d["recipient_parent_name"] = r.get("recipient_parent_name", "")
                        for c in FLAG_COLS:
                            if str(r.get(c, "")).lower() in ("t", "true", "1", "y"):
                                d["flags"].add(c)
                        for k, col in (("first_action_date", "award_base_action_date"),
                                       ("last_action_date", "award_latest_action_date")):
                            v = (r.get(col) or "").strip()
                            if not v:
                                continue
                            if not d[k]:
                                d[k] = v
                            elif k == "first_action_date" and v < d[k]:
                                d[k] = v
                            elif k == "last_action_date" and v > d[k]:
                                d[k] = v
        log(f"  read {jk}")
    log(f"award rows scanned: {n_rows:,}; duplicate award keys skipped: {n_dupe:,}; "
        f"distinct awards: {len(seen_awards):,}; distinct recipient UEIs: {len(uni):,}")

    # ---- match
    for u, d in uni.items():
        m = led.get(u)
        d["in_ledger"] = "YES" if m else "NO"
        d["ledger_tribe_id"] = m["tribe_id"] if m else ""
        d["ledger_canonical_name"] = m["canonical_name"] if m else ""
        d["ledger_confidence_tier"] = m["confidence_tier"] if m else ""
        d["ledger_entity_class"] = m["entity_class"] if m else ""

    hit = [d for d in uni.values() if d["in_ledger"] == "YES"]
    miss = [d for d in uni.values() if d["in_ledger"] == "NO"]
    aw_hit = sum(d["n_awards"] for d in hit)
    aw_all = sum(d["n_awards"] for d in uni.values())
    log("")
    log("=== HIT RATE against cedar_identifier_ledger_final.csv (exact UEI) ===")
    log(f"  distinct UEIs : {len(hit):,} / {len(uni):,}  = {100.0*len(hit)/max(len(uni),1):.1f}%")
    log(f"  award records : {aw_hit:,} / {aw_all:,}  = {100.0*aw_hit/max(aw_all,1):.1f}%")
    dh = sum(d["total_obligated_usd"] for d in hit)
    da = sum(d["total_obligated_usd"] for d in uni.values())
    log(f"  obligated $   : ${dh:,.0f} / ${da:,.0f} = {100.0*dh/max(da,1):.1f}%")
    from collections import Counter
    log("  matched UEIs by ledger tier: "
        + str(dict(Counter(d["ledger_confidence_tier"] for d in hit))))

    # ---- write universe
    cols = ["recipient_uei", "recipient_name", "cage_code", "recipient_parent_uei",
            "recipient_parent_name", "n_awards", "total_obligated_usd",
            "first_action_date", "last_action_date", "example_award_id_piid",
            "example_parent_award_id_piid", "awarding_agency_example",
            "native_flags", "in_ledger", "ledger_tribe_id",
            "ledger_canonical_name", "ledger_confidence_tier", "ledger_entity_class"]
    up = os.path.join(RAW, "gapfill_recipient_universe.csv")
    with open(up, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for d in sorted(uni.values(), key=lambda x: -x["total_obligated_usd"]):
            d = dict(d)
            d["native_flags"] = ";".join(sorted(d.pop("flags")))
            d["total_obligated_usd"] = f"{d['total_obligated_usd']:.2f}"
            w.writerow(d)
    log(f"WROTE {up} — {len(uni):,} rows")

    # ---- spiderweb candidates
    # A NEW uei (not in ledger) whose recipient_parent_uei IS a ledger UEI.
    cands = []
    for d in miss:
        pu = d["recipient_parent_uei"]
        if not pu or pu in blocked:
            continue
        pm = led.get(pu)
        if not pm:
            continue
        cands.append({
            "candidate_uei": d["recipient_uei"],
            "candidate_name": d["recipient_name"],
            "candidate_cage": d["cage_code"],
            "n_awards_2023_2026": d["n_awards"],
            "total_obligated_usd": f"{d['total_obligated_usd']:.2f}",
            "first_action_date": d["first_action_date"],
            "last_action_date": d["last_action_date"],
            "native_flags_on_award": ";".join(sorted(d["flags"])),
            "shared_parent_uei": pu,
            "shared_parent_name_fpds": d["recipient_parent_name"],
            "parent_ledger_tribe_id": pm["tribe_id"],
            "parent_ledger_canonical_name": pm["canonical_name"],
            "parent_ledger_confidence_tier": pm["confidence_tier"],
            "parent_ledger_entity_class": pm["entity_class"],
            "evidence": ("recipient_parent_uei on a USAspending prime contract award "
                         "summary equals a UEI present in cedar_identifier_ledger_final.csv"),
            "attribution_status": "CANDIDATE_ONLY_NOT_ATTRIBUTED",
            "YOUR_RULING": "",
        })
    cands.sort(key=lambda r: -float(r["total_obligated_usd"]))
    cp = os.path.join(REVIEW, "contract_spiderweb_candidates_2026-08-05.csv")
    os.makedirs(REVIEW, exist_ok=True)
    with open(cp, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(cands[0].keys()) if cands else ["candidate_uei"])
        w.writeheader()
        w.writerows(cands)
    log(f"WROTE {cp} — {len(cands):,} spiderweb candidates")
    log("  by parent ledger tier: "
        + str(dict(Counter(c["parent_ledger_confidence_tier"] for c in cands))))
    return uni, hit, miss, cands, n_rows, files_read


if __name__ == "__main__":
    main()
