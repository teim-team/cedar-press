"""40_contracts_ledger_pass.py — Pass B. Measure what the flag route cannot see.

WHY THIS EXISTS
    Pass A (code/37) retrieves post-2023 prime contracts by socioeconomic
    ownership flag. Four flag values work; `indian_tribe_federally_recognized`,
    `us_tribal_government`, `housing_authorities_public_tribal` and
    `tribal_college` all return ZERO as filter values even though they exist as
    populated output columns. So a tribal GOVERNMENT contracting in its own name
    is invisible to Pass A unless it also carries an ownership flag.

    This pass queries USAspending by the LEDGER'S OWN UEIs instead of by flag,
    which does not depend on any flag being set. The difference between the two
    is the size of the hole, measured rather than asserted.

METHOD NOTES
    * `recipient_search_text` is OR-ed across values. Verified: querying five
      UEIs individually returned 1+0+2202+130+87 and the batched query returned
      exactly 2420.
    * The array is capped at 20 values. 21+ returns HTTP 503, NOT a clean 400.
      BATCH is therefore 20 and must not be raised.
    * Scope is the ledger's tier-A UEIs (Elijah-ruled / hand-checked /
      source-verified). Tiers B and C are algorithmic and are not worth
      spending a rate-limited request budget on before they are ruled.

Output: review/contract_ledger_pass_tierA_2026-08-05.csv
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, "data", "clean", "cedar_identifier_ledger_final.csv")
REVIEW = os.path.join(ROOT, "review")
RAW = os.path.join(ROOT, "data", "raw", "contracts", "usaspending_gapfill_2026-08-05")
LOGFILE = os.path.join(ROOT, "logs", "40_contracts_ledger_pass.log")
OUT = os.path.join(REVIEW, "contract_ledger_pass_tierA_2026-08-05.csv")
CKPT = os.path.join(RAW, "_ledger_pass_state.json")

COUNT = "https://api.usaspending.gov/api/v2/search/spending_by_award_count/"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")

BATCH = 20              # hard cap, see docstring
START, END = "2023-04-05", "2026-08-05"
SLEEP = 3


def log(msg):
    line = f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')}] {msg}"
    print(line, flush=True)
    os.makedirs(os.path.dirname(LOGFILE), exist_ok=True)
    with open(LOGFILE, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def post(payload, tries=5):
    body = json.dumps(payload).encode()
    for i in range(tries):
        try:
            req = urllib.request.Request(
                COUNT, data=body,
                headers={"Content-Type": "application/json", "User-Agent": UA},
                method="POST")
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            w = 15 * (2 ** i)
            log(f"   retry {i+1}/{tries} {type(e).__name__} — sleep {w}s")
            time.sleep(w)
    return None


def main():
    ueis, meta = [], {}
    for r in csv.DictReader(open(LEDGER, encoding="utf-8-sig")):
        if r["identifier_type"] == "UEI" and r["confidence_tier"] == "A":
            if r["identifier"] not in meta:
                ueis.append(r["identifier"])
                meta[r["identifier"]] = r
    log(f"tier-A ledger UEIs: {len(ueis):,}")

    state = {}
    if os.path.exists(CKPT):
        state = json.load(open(CKPT, encoding="utf-8"))

    batches = [ueis[i:i + BATCH] for i in range(0, len(ueis), BATCH)]
    for bi, b in enumerate(batches, 1):
        key = str(bi)
        if key in state:
            continue
        # batch count first; only split to per-UEI when the batch is non-empty,
        # so a request is never spent resolving a batch that has no awards.
        r = post({"filters": {
            "award_type_codes": ["A", "B", "C", "D", "IDV_A", "IDV_B", "IDV_C",
                                 "IDV_D", "IDV_E"],
            "time_period": [{"start_date": START, "end_date": END,
                             "date_type": "action_date"}],
            "recipient_search_text": b}})
        if r is None:
            log(f"BATCH {bi}/{len(batches)} FAILED — stopping, progress saved")
            break
        tot = r["results"]["contracts"] + r["results"]["idvs"]
        log(f"BATCH {bi}/{len(batches)}: {tot:,} awards across {len(b)} UEIs")
        per = {}
        if tot:
            for u in b:
                rr = post({"filters": {
                    "award_type_codes": ["A", "B", "C", "D", "IDV_A", "IDV_B",
                                         "IDV_C", "IDV_D", "IDV_E"],
                    "time_period": [{"start_date": START, "end_date": END,
                                     "date_type": "action_date"}],
                    "recipient_search_text": [u]}})
                if rr is None:
                    break
                per[u] = rr["results"]["contracts"] + rr["results"]["idvs"]
                time.sleep(SLEEP)
        else:
            per = {u: 0 for u in b}
        state[key] = {"ueis": b, "batch_total": tot, "per_uei": per}
        os.makedirs(RAW, exist_ok=True)
        json.dump(state, open(CKPT, "w", encoding="utf-8"), indent=1)
        time.sleep(SLEEP)

    rows = []
    for k, v in state.items():
        for u, n in v.get("per_uei", {}).items():
            m = meta.get(u, {})
            rows.append({
                "uei": u, "n_awards_2023_04_05_to_2026_08_05": n,
                "ledger_tribe_id": m.get("tribe_id", ""),
                "ledger_canonical_name": m.get("canonical_name", ""),
                "ledger_legal_business_name": m.get("legal_business_name", ""),
                "ledger_entity_class": m.get("entity_class", ""),
            })
    rows.sort(key=lambda r: -r["n_awards_2023_04_05_to_2026_08_05"])
    if rows:
        with open(OUT, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        act = [r for r in rows if r["n_awards_2023_04_05_to_2026_08_05"] > 0]
        log(f"WROTE {OUT} — {len(rows):,} tier-A UEIs resolved, "
            f"{len(act):,} with >=1 post-gap award, "
            f"{sum(r['n_awards_2023_04_05_to_2026_08_05'] for r in rows):,} awards total")


if __name__ == "__main__":
    main()
