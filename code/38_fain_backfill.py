"""38_fain_backfill.py — FAIN + real action-date backfill for the 594 federal
award rows in data/clean/deals_federal_awards_additions.csv.

WHAT IS BROKEN IN THOSE ROWS
    All 594 carry no FAIN. 169 carry a Medium-confidence date:
      148 HUD rows dated from a PDF's embedded CreationDate ("NOT an award
          action date", per the row's own Date_Basis)
       21 DOE rows with a month-level period-of-performance start and a
          disclosed day-15 placeholder

ASSISTANCE LISTING CORRECTION
    The brief specified 11.554 for the NTIA Tribal Broadband Connectivity
    Program. 11.554 matches ZERO awards. TBCP is **11.029** (confirmed via
    /api/v2/autocomplete/cfda/, 276 awards — against GAO-24-106541's stated
    universe of 274). 11.554 is carried in NOT_FOUND below so nobody re-tries it.

EVIDENCE STANDARD FOR REPLACING A DATE (deliberately strict)
    A candidate award may supply a FAIN and an action date to a ledger row ONLY
    when ALL of:
      1. program (assistance listing) matches the row's funder/program, AND
      2. recipient matches on a normalised name key, AND
      3. the obligated amount agrees within $1 of Announced_Value_USD, AND
      4. exactly ONE candidate survives 1-3.
    Anything else is left untouched and reported unresolved. A precise date on
    an ambiguous match is the exact failure mode this project exists to prevent.
    Amount agreement is required, not optional: recipient+program alone routinely
    matches several rounds of the same recurring grant to the same tribe.

    NOTE: `total_obligated_amount` on an award summary is CUMULATIVE across the
    award's life, so it can legitimately exceed a single announced award value.
    That is why a non-match is reported rather than treated as a discrepancy.

Nothing in data/clean/ is modified. Output is staged to new files.

Usage:
  py -3 code/38_fain_backfill.py pull
  py -3 code/38_fain_backfill.py match
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw", "contracts", "usaspending_gapfill_2026-08-05",
                   "assistance_fain")
REVIEW = os.path.join(ROOT, "review")
LOGFILE = os.path.join(ROOT, "logs", "38_fain_backfill.log")
STATE = os.path.join(RAW, "_state.json")
SRC = os.path.join(ROOT, "data", "clean", "deals_federal_awards_additions.csv")

DOWNLOAD = "https://api.usaspending.gov/api/v2/download/awards/"
STATUS = "https://api.usaspending.gov/api/v2/download/status"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")

# assistance listing -> the Counterparty_or_Funder substring it corresponds to
PROGRAMS = {
    "11.029": ["NTIA"],                                   # Tribal Broadband Connectivity
    "14.862": ["ICDBG"],                                  # Indian Community Dev Block Grant
    "14.867": ["IHBG", "Indian Housing Block Grant"],     # Indian Housing Block Grant
    "81.087": ["Energy"],                                 # Renewable Energy R&D
    "81.214": ["Energy"],                                 # Tribal Energy
    "11.307": ["Economic"],                               # EDA Economic Adjustment Assistance
}
NOT_FOUND = {"11.554": "specified in the brief; matches ZERO awards. TBCP is 11.029."}

AWARD_TYPES = ["02", "03", "04", "05", "06", "07", "08", "09", "10", "11"]
START, END = "2007-10-01", "2026-08-05"


def log(msg):
    line = f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')}] {msg}"
    print(line, flush=True)
    os.makedirs(os.path.dirname(LOGFILE), exist_ok=True)
    with open(LOGFILE, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def _post(url, payload, t=240):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": UA}, method="POST")
    with urllib.request.urlopen(req, timeout=t) as r:
        return json.loads(r.read().decode())


def _get(url, t=180):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=t) as r:
        return json.loads(r.read().decode())


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def stage_pull():
    os.makedirs(RAW, exist_ok=True)
    st = {}
    if os.path.exists(STATE):
        st = json.load(open(STATE, encoding="utf-8"))
    st.setdefault("jobs", {})
    for cfda in PROGRAMS:
        dest = os.path.join(RAW, f"cfda_{cfda.replace('.','_')}.zip")
        if cfda in st["jobs"] and os.path.exists(dest):
            log(f"SKIP {cfda}")
            continue
        payload = {"filters": {
            "award_type_codes": AWARD_TYPES,
            "time_period": [{"start_date": START, "end_date": END,
                             "date_type": "action_date"}],
            "program_numbers": [cfda],
        }, "columns": [], "file_format": "csv"}
        log(f"SUBMIT cfda {cfda}")
        resp = _post(DOWNLOAD, payload)
        echoed = resp.get("download_request", {}).get("filters", {})
        if "program_numbers" not in echoed:
            raise RuntimeError(f"program_numbers dropped by endpoint: {echoed}")
        fn = resp["file_name"]
        waited, meta = 0, {}
        while waited < 3600:
            time.sleep(15)
            waited += 15
            try:
                meta = _get(STATUS + "?file_name=" + urllib.parse.quote(fn))
            except Exception as e:
                log(f"   poll err {e}")
                continue
            if meta.get("status") in ("finished", "failed"):
                break
        if meta.get("status") != "finished":
            log(f"FAIL {cfda}: {meta.get('status')} {meta.get('message')}")
            continue
        log(f"   rows={meta.get('total_rows')}")
        req = urllib.request.Request(meta["file_url"], headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=3600) as r, open(dest + ".part", "wb") as fh:
            while True:
                c = r.read(1 << 20)
                if not c:
                    break
                fh.write(c)
        os.replace(dest + ".part", dest)
        meta["_payload"] = payload
        meta["_sha256"] = sha256(dest)
        meta["_bytes"] = os.path.getsize(dest)
        meta["_local_file"] = os.path.basename(dest)
        st["jobs"][cfda] = meta
        json.dump(st, open(STATE, "w", encoding="utf-8"), indent=1)
        log(f"CHECKPOINT {cfda} {meta['_bytes']:,} bytes")
        time.sleep(10)
    log("PULL COMPLETE")


# ------------------------------------------------------------------- matching
STOP = {"the", "of", "and", "inc", "llc", "corporation", "corp", "company", "co",
        "authority", "tribal", "tribe", "tribes", "nation", "band", "indian",
        "indians", "community", "council", "housing", "development", "a", "an",
        "incorporated", "association", "government", "pueblo", "village",
        "native", "peoples", "people", "of", "reservation", "rancheria"}


def nkey(s):
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    toks = [t for t in s.split() if t and t not in STOP]
    return " ".join(sorted(set(toks)))


def load_awards():
    out = []
    for cfda in PROGRAMS:
        p = os.path.join(RAW, f"cfda_{cfda.replace('.','_')}.zip")
        if not os.path.exists(p):
            log(f"WARN missing {p}")
            continue
        with zipfile.ZipFile(p) as z:
            for m in z.namelist():
                if not m.lower().endswith(".csv") or "Subawards" in m:
                    continue
                with z.open(m) as fh:
                    for r in csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8-sig")):
                        r["_cfda_job"] = cfda
                        out.append(r)
    return out


def money(v):
    try:
        return round(float(str(v).replace(",", "").replace("$", "")), 2)
    except Exception:
        return None


def stage_match():
    rows = list(csv.DictReader(open(SRC, encoding="utf-8-sig")))
    awards = load_awards()
    log(f"loaded {len(rows)} ledger rows, {len(awards):,} USAspending assistance awards")

    # index awards by normalised recipient key
    idx = {}
    for a in awards:
        k = nkey(a.get("recipient_name") or a.get("recipient_name_raw"))
        if k:
            idx.setdefault(k, []).append(a)

    out, unresolved = [], []
    matched = 0
    for r in rows:
        funder = r["Counterparty_or_Funder"]
        want = [c for c, tags in PROGRAMS.items()
                if any(t.lower() in funder.lower() for t in tags)]
        k = nkey(r["Native_Party"])
        amt = money(r["Announced_Value_USD"])
        cands = [a for a in idx.get(k, []) if a["_cfda_job"] in want]
        exact = [a for a in cands
                 if amt is not None and money(a.get("total_obligated_amount")) == amt]
        rec = {
            "Deal_ID": r["Deal_ID"],
            "Native_Party": r["Native_Party"],
            "Counterparty_or_Funder": funder,
            "Announced_Value_USD": r["Announced_Value_USD"],
            "existing_Event_Date": r["Event_Date"],
            "existing_Confidence": r["Confidence"],
            "existing_Date_Basis": r["Date_Basis"][:120],
            "n_program_recipient_candidates": len(cands),
            "n_amount_exact_candidates": len(exact),
            "resolution": "", "matched_fain": "", "matched_action_date": "",
            "matched_latest_action_date": "",
            "matched_recipient_uei": "", "matched_recipient_name": "",
            "matched_obligated_amount": "", "matched_cfda": "",
            "usaspending_permalink": "", "implausibility": "",
        }
        if len(exact) == 1:
            a = exact[0]
            rec.update(
                resolution="RESOLVED_UNAMBIGUOUS",
                matched_fain=a.get("award_id_fain", ""),
                matched_action_date=a.get("award_base_action_date", ""),
                matched_latest_action_date=a.get("award_latest_action_date", ""),
                matched_recipient_uei=a.get("recipient_uei", ""),
                matched_recipient_name=a.get("recipient_name", ""),
                matched_obligated_amount=a.get("total_obligated_amount", ""),
                matched_cfda=a.get("_cfda_job", ""),
                usaspending_permalink=a.get("usaspending_permalink", ""))
            matched += 1
        else:
            if not cands:
                rec["resolution"] = "UNRESOLVED_no_recipient_program_candidate"
            elif not exact:
                rec["resolution"] = "UNRESOLVED_amount_disagrees"
            else:
                rec["resolution"] = "UNRESOLVED_ambiguous_multiple_exact"
            unresolved.append(rec)
        out.append(rec)

    # ---- integrity gate 1: one FAIN may serve at most ONE ledger row.
    # A FAIN claimed twice means at least one of the two is wrong.
    import collections
    fc = collections.Counter(r["matched_fain"] for r in out
                             if r["resolution"] == "RESOLVED_UNAMBIGUOUS")
    for r in out:
        if r["resolution"] == "RESOLVED_UNAMBIGUOUS" and fc[r["matched_fain"]] > 1:
            r["resolution"] = "UNRESOLVED_fain_claimed_by_multiple_rows"
            matched -= 1

    # ---- integrity gate 2: temporal plausibility, per Date_Basis group.
    # Each source document dates a whole ROUND, so the imputed->real shift is
    # tightly clustered within a group (e.g. HUD publishes a list, then
    # obligates ~2 months later). A row far outside its own group's cluster is
    # a same-amount collision with a different round, not a match. Observed:
    # every group spans <150 days except one row at +977.
    def shift(r):
        try:
            return (datetime.strptime(r["matched_action_date"][:10], "%Y-%m-%d").date()
                    - datetime.strptime(r["existing_Event_Date"], "%Y-%m-%d").date()).days
        except Exception:
            return None

    groups = collections.defaultdict(list)
    for r in out:
        if r["resolution"] == "RESOLVED_UNAMBIGUOUS":
            s = shift(r)
            if s is not None:
                groups[r["existing_Date_Basis"]].append(s)
    med = {k: sorted(v)[len(v) // 2] for k, v in groups.items()}
    for r in out:
        if r["resolution"] != "RESOLVED_UNAMBIGUOUS":
            continue
        s = shift(r)
        if s is None:
            continue
        m = med.get(r["existing_Date_Basis"], 0)
        if abs(s) > 365 or abs(s - m) > 180:
            r["resolution"] = "UNRESOLVED_temporally_implausible"
            r["implausibility"] = f"shift {s}d vs group median {m}d"
            matched -= 1

    os.makedirs(REVIEW, exist_ok=True)
    op = os.path.join(REVIEW, "federal_awards_fain_backfill_2026-08-05.csv")
    with open(op, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()), extrasaction="ignore")
        w.writeheader()
        w.writerows(out)
    log(f"WROTE {op} — {len(out)} rows, {matched} RESOLVED, {len(unresolved)} unresolved")
    import collections
    for k, v in collections.Counter(x["resolution"] for x in out).most_common():
        log(f"   {v:5d}  {k}")
    return op


if __name__ == "__main__":
    s = sys.argv[1] if len(sys.argv) > 1 else "pull"
    if s == "pull":
        stage_pull()
    elif s == "match":
        stage_match()
