#!/usr/bin/env python3
"""
43_funding_forward_fill.py
Cedar Press Dataset 3 (Federal Funding / assistance) -- FORWARD FILL 2023-04-06 .. 2026-08-05.

WHY
    The spine file
        Federal Spending/raw/Assistance_PrimeTransactions_2023-04-09_H19M53S53_1.csv
    holds 476,924 transactions, FY2008 .. FY2023, and its LAST action_date is
    2023-04-05 (verified by streaming scan, this run). Everything after that is
    absent. This script retrieves the missing window from USAspending and stages
    it. It does NOT touch data/clean/ and does NOT run the master pipeline.

THE FILTER -- REPLICATED, NOT INVENTED
    The spine was not a full-universe download. Measured over all 476,924 rows,
    `business_types_code` takes exactly three values and no others:
        I  427,596  Indian/Native American Tribal Government (Federally Recognized)
        K   46,666  Indian/Native American Tribally Designated Organization
        J    2,662  Indian/Native American Tribal Government (Other than Fed. Rec.)
    That is USAspending's Recipient Type = tribal group. The API equivalent is
    recipient_type_names = ["indian_native_american_tribal_government"], verified
    against the spine's own overlap years via /search/spending_by_transaction_count/:
        FY2022  API 44,347  vs spine 44,297   (+0.11%)
        FY2021  API 43,777  vs spine 43,604   (+0.40%)
    The small excess is post-2023-04-09 corrections and late reporting, which is
    expected and is the right direction. After download every row is re-checked
    locally against business_types_code in {I,J,K}; anything else is reported, not
    silently kept.

ZERO FABRICATION
    Nothing here estimates, interpolates or infers. Every row written comes out of
    a USAspending download file. Every request payload is written to disk next to
    the file it produced.

Run:
    py -3 code/43_funding_forward_fill.py pull     # first run: request + poll + download
    py -3 code/43_funding_forward_fill.py resume   # gentle: reuses already-generated jobs
    py -3 code/43_funding_forward_fill.py build    # counts, ledger match, review files
"""

import csv
import datetime
import io
import json
import os
import sys
import time
import zipfile

import requests

csv.field_size_limit(10_000_000)

CEDAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTDIR = os.path.join(CEDAR, "data", "raw", "federal_funding",
                      "usaspending_2023_2026")
LOGDIR = os.path.join(CEDAR, "logs")
REVIEW = os.path.join(CEDAR, "review")
LEDGER = os.path.join(CEDAR, "data", "clean", "cedar_identifier_ledger_final.csv")
SPINE_RAW = os.path.join(CEDAR, "Federal Spending", "raw",
                         "Assistance_PrimeTransactions_2023-04-09_H19M53S53_1.csv")

API = "https://api.usaspending.gov"
UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
    "Content-Type": "application/json",
}

PRIME_AWARD_TYPES = ["02", "03", "04", "05", "06", "07", "08", "09", "10", "11"]
RECIPIENT_TYPE = "indian_native_american_tribal_government"
TRIBAL_BUSINESS_TYPES = ("I", "J", "K")

# The spine's last action_date, verified by scan this run.
SPINE_LAST_ACTION_DATE = "2023-04-05"
PULL_DATE = "2026-08-05"

CHUNKS = [
    ("fy2023_partial", "2023-04-06", "2023-09-30"),
    ("fy2024", "2023-10-01", "2024-09-30"),
    ("fy2025", "2024-10-01", "2025-09-30"),
    ("fy2026_partial", "2025-10-01", "2026-08-05"),
]

os.makedirs(OUTDIR, exist_ok=True)
os.makedirs(LOGDIR, exist_ok=True)
LOGPATH = os.path.join(LOGDIR, "43_funding_forward_fill.log")
_logf = open(LOGPATH, "a", encoding="utf-8")


def log(msg):
    line = f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    _logf.write(line + "\n")
    _logf.flush()


def payload_for(start, end):
    return {
        "filters": {
            "time_period": [{"start_date": start, "end_date": end,
                             "date_type": "action_date"}],
            "award_type_codes": PRIME_AWARD_TYPES,
            "recipient_type_names": [RECIPIENT_TYPE],
        },
        "columns": [],
        "file_format": "csv",
    }


def post_with_retry(url, body, tries=6, timeout=180):
    delay = 10
    last = None
    for k in range(tries):
        try:
            r = requests.post(url, json=body, headers=UA, timeout=timeout)
            if r.status_code == 200:
                return r.json()
            last = f"HTTP {r.status_code}: {r.text[:400]}"
            log(f"  attempt {k+1}: {last}")
        except Exception as e:                                   # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
            log(f"  attempt {k+1}: {last}")
        time.sleep(delay)
        delay = min(delay * 2, 300)
    raise RuntimeError(f"POST {url} failed after {tries} tries. Last: {last}")


def get_with_retry(url, tries=8, timeout=300, stream=False):
    delay = 10
    last = None
    for k in range(tries):
        try:
            r = requests.get(url, headers={"User-Agent": UA["User-Agent"]},
                             timeout=timeout, stream=stream)
            if r.status_code == 200:
                return r
            last = f"HTTP {r.status_code}"
            log(f"  attempt {k+1}: {last}")
        except Exception as e:                                   # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
            log(f"  attempt {k+1}: {last}")
        time.sleep(delay)
        delay = min(delay * 2, 300)
    raise RuntimeError(f"GET {url} failed after {tries} tries. Last: {last}")


def pull():
    state_path = os.path.join(OUTDIR, "_state.json")
    state = {}
    if os.path.exists(state_path):
        state = json.load(open(state_path, encoding="utf-8"))

    for tag, start, end in CHUNKS:
        if state.get(tag, {}).get("csv_path") and \
                os.path.exists(os.path.join(OUTDIR, state[tag]["csv_path"])):
            log(f"{tag}: already on disk ({state[tag]['csv_path']}) -- skip")
            continue

        body = payload_for(start, end)
        req_path = os.path.join(OUTDIR, f"request_{tag}.json")
        with open(req_path, "w", encoding="utf-8") as fh:
            json.dump({"endpoint": f"{API}/api/v2/download/transactions/",
                       "method": "POST",
                       "requested_utc": datetime.datetime.utcnow().isoformat() + "Z",
                       "payload": body}, fh, indent=2)
        log(f"{tag}: POST /api/v2/download/transactions/ {start} .. {end}")
        resp = post_with_retry(f"{API}/api/v2/download/transactions/", body)
        with open(os.path.join(OUTDIR, f"response_{tag}.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(resp, fh, indent=2)

        file_name = resp.get("file_name")
        file_url = resp.get("file_url")
        status_url = resp.get("status_url") or \
            f"{API}/api/v2/download/status/?file_name={file_name}"
        log(f"{tag}: job {file_name}")

        # poll
        t0 = time.time()
        status = None
        # api.usaspending.gov drops roughly half of these polls with
        # RemoteDisconnected (observed 2026-08-05). It is flaky, not blocked --
        # the job keeps generating server-side. Poll gently and keep going;
        # a dropped poll is not a failed job.
        while time.time() - t0 < 7200:
            time.sleep(45)
            try:
                s = requests.get(status_url, headers={"User-Agent": UA["User-Agent"]},
                                 timeout=120).json()
            except Exception as e:                               # noqa: BLE001
                log(f"  poll error {type(e).__name__}: {e}")
                continue
            status = s.get("status")
            log(f"  status={status} rows={s.get('total_rows')} "
                f"size={s.get('file_size')} elapsed={int(time.time()-t0)}s")
            if status == "finished":
                file_url = s.get("file_url") or file_url
                state.setdefault(tag, {})["status_json"] = s
                break
            if status == "failed":
                raise RuntimeError(f"{tag}: download job failed: {s}")
        if status != "finished":
            raise RuntimeError(f"{tag}: job did not finish within 2h")

        log(f"{tag}: downloading {file_url}")
        r = get_with_retry(file_url, stream=True)
        zip_path = os.path.join(OUTDIR, file_name)
        with open(zip_path, "wb") as fh:
            for chunk in r.iter_content(1 << 20):
                fh.write(chunk)
        log(f"{tag}: wrote {zip_path} ({os.path.getsize(zip_path):,} bytes)")

        members = []
        with zipfile.ZipFile(zip_path) as z:
            for nm in z.namelist():
                z.extract(nm, OUTDIR)
                members.append(nm)
        log(f"{tag}: extracted {members}")

        # The zip carries TWO csvs: Assistance_PrimeTransactions_* (what we
        # want) and Assistance_Subawards_* (FSRS subawards, a free bonus for
        # dataset 2b). Select the prime file by name, never by position.
        csvs = [m for m in members if m.lower().endswith(".csv")
                and "PrimeTransactions" in m]
        state.setdefault(tag, {})
        state[tag].update({"start": start, "end": end, "zip": file_name,
                           "members": members,
                           "csv_path": csvs[0] if csvs else None})
        with open(state_path, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2)
        time.sleep(30)

    log("pull complete")


# ---------------------------------------------------------------------------

def _read_ledger():
    """recipient_uei -> {tier, tribe_id, canonical_name}

    Schema of cedar_identifier_ledger_final.csv (17 cols):
      identifier_type, identifier, tribe_id, canonical_name, legal_business_name,
      entity_class, attribution_method, confidence_tier, tier_rationale,
      is_authority, exclusion_id, exclusion_evidence, evidence_url,
      verified_date, state, prime_dollars_M, source_file
    A UEI may appear on more than one row; the strongest confidence_tier wins,
    EXCEPT tier X (exclusion ruling) which is recorded separately and never
    counted as a Native match.
    """
    uei2 = {}
    order = {"A": 0, "B": 1, "C": 2, "X": 3}
    with open(LEDGER, newline="", encoding="utf-8-sig", errors="replace") as fh:
        rd = csv.DictReader(fh)
        log(f"ledger columns: {rd.fieldnames}")
        for row in rd:
            if (row.get("identifier_type") or "").strip().upper() != "UEI":
                continue
            val = (row.get("identifier") or "").strip().upper()
            if not val:
                continue
            tier = (row.get("confidence_tier") or "").strip().upper()
            rec = {"tier": tier,
                   "tribe_id": row.get("tribe_id") or "",
                   "canonical_name": row.get("canonical_name") or "",
                   "entity_class": row.get("entity_class") or "",
                   "attribution_method": row.get("attribution_method") or ""}
            prev = uei2.get(val)
            if prev is None or order.get(tier, 9) < order.get(prev["tier"], 9):
                uei2[val] = rec
    return uei2


NATIVE_TOKENS = [
    "tribe", "tribal", "tribes", "nation", "band", "pueblo", "rancheria",
    "reservation", "indian", "native", "nsn", "community of", "colony",
    "chippewa", "cherokee", "navajo", "sioux", "apache", "shoshone", "paiute",
    "yakama", "lakota", "dakota", "anishinaabe", "aleut", "inupiat", "yupik",
    "village of", "native village", "confederated", "of indians", "ute ",
    "hopi", "zuni", "seminole", "choctaw", "chickasaw", "creek nation",
    "muscogee", "osage", "comanche", "kiowa", "arapaho", "cheyenne", "crow ",
    "blackfeet", "menominee", "oneida", "mohawk", "seneca", "tlingit", "haida",
]


def build():
    state_path = os.path.join(OUTDIR, "_state.json")
    if not os.path.exists(state_path):
        sys.exit("no _state.json -- run `pull` first")
    state = json.load(open(state_path, encoding="utf-8"))
    import collections

    uei2 = _read_ledger()
    # The ledger is edited by other agent sessions while this runs. WHICH UEIs
    # match is stable (the UEI set is unchanged); the A/B/C/X SPLIT is a
    # snapshot, so fingerprint the ledger the numbers were computed against.
    led_mtime = datetime.datetime.fromtimestamp(
        os.path.getmtime(LEDGER)).strftime("%Y-%m-%d %H:%M:%S")
    led_tiers = dict(collections.Counter(v["tier"] for v in uei2.values()))
    log(f"ledger UEIs: {len(uei2):,}  mtime={led_mtime}  tiers={led_tiers}")

    per_file = {}
    fy_rows = collections.Counter()
    fy_obl = collections.Counter()
    fy_rows_matched = collections.Counter()
    fy_obl_matched = collections.Counter()
    bt_counter = collections.Counter()
    tier_rows = collections.Counter()
    tier_obl = collections.Counter()
    matched_ueis = set()
    new_ueis = collections.Counter()
    new_uei_obl = collections.Counter()
    new_uei_name = {}
    blank_uei_rows = 0
    max_action_date = ""
    min_action_date = "9999"
    schema = None
    unmatched_native = {}

    for tag, _s, _e in CHUNKS:
        rec = state.get(tag) or {}
        # Always re-derive the prime file from members: an early run selected
        # csvs[0], which can be the Subawards file.
        prime = [m for m in (rec.get("members") or [])
                 if m.lower().endswith(".csv") and "PrimeTransactions" in m]
        cp = prime[0] if prime else rec.get("csv_path")
        if not cp:
            log(f"{tag}: NO FILE")
            continue
        path = os.path.join(OUTDIR, cp)
        n = 0
        with open(path, newline="", encoding="utf-8-sig", errors="replace") as fh:
            rd = csv.reader(fh)
            h = next(rd)
            if schema is None:
                schema = h
            i_ad = h.index("action_date")
            i_fy = h.index("action_date_fiscal_year")
            i_ob = h.index("federal_action_obligation")
            i_bt = h.index("business_types_code")
            i_ue = h.index("recipient_uei")
            i_rn = h.index("recipient_name")
            for row in rd:
                n += 1
                ad = row[i_ad]
                if ad > max_action_date:
                    max_action_date = ad
                if ad and ad < min_action_date:
                    min_action_date = ad
                fy = row[i_fy]
                try:
                    ob = float(row[i_ob] or 0)
                except ValueError:
                    ob = 0.0
                fy_rows[fy] += 1
                fy_obl[fy] += ob
                bt_counter[row[i_bt]] += 1
                uei = (row[i_ue] or "").strip().upper()
                if not uei:
                    blank_uei_rows += 1
                hit = uei2.get(uei) if uei else None
                if hit:
                    tier_rows[hit["tier"]] += 1
                    tier_obl[hit["tier"]] += ob
                    # Tier X is an exclusion ruling. It is a ledger HIT but it
                    # is NOT a Native attribution and must never be counted as
                    # one (STATE_OF_BUILD correction 4).
                    if hit["tier"] != "X":
                        matched_ueis.add(uei)
                        fy_rows_matched[fy] += 1
                        fy_obl_matched[fy] += ob
                elif uei:
                    new_ueis[uei] += 1
                    new_uei_obl[uei] += ob
                    new_uei_name.setdefault(uei, row[i_rn])
                    nm = (row[i_rn] or "").lower()
                    hits = [t for t in NATIVE_TOKENS if t in nm]
                    if hits:
                        d = unmatched_native.setdefault(
                            uei, {"recipient_name": row[i_rn], "rows": 0,
                                  "obligations": 0.0,
                                  "business_types_code": row[i_bt],
                                  "matched_tokens": "|".join(hits),
                                  "first_action_date": ad,
                                  "last_action_date": ad})
                        d["rows"] += 1
                        d["obligations"] += ob
                        if ad > d["last_action_date"]:
                            d["last_action_date"] = ad
                        if ad < d["first_action_date"]:
                            d["first_action_date"] = ad
        per_file[tag] = {"path": cp, "rows": n, "ncol": len(h)}
        log(f"{tag}: {n:,} rows, {len(h)} cols")

    # -- report ------------------------------------------------------------
    print()
    print("=== PER FILE ===")
    for tag, d in per_file.items():
        print(f"{tag:18s} {d['rows']:>9,}  cols={d['ncol']}  {d['path']}")
    print(f"\naction_date range in new data: {min_action_date} .. {max_action_date}")
    print(f"spine last action_date:        {SPINE_LAST_ACTION_DATE}")
    print(f"\nbusiness_types_code: {dict(bt_counter)}")
    nontribal = sum(v for k, v in bt_counter.items()
                    if not any(c in k for c in TRIBAL_BUSINESS_TYPES))
    print(f"rows whose business_types_code is NOT in {{I,J,K}}: {nontribal:,}")

    print("\n=== BY FISCAL YEAR ===")
    print(f"{'FY':6s} {'rows':>9s} {'obligations':>20s} {'ledger rows':>12s} "
          f"{'ledger obligations':>20s}")
    for fy in sorted(fy_rows):
        print(f"{fy:6s} {fy_rows[fy]:>9,} {fy_obl[fy]:>20,.2f} "
              f"{fy_rows_matched[fy]:>12,} {fy_obl_matched[fy]:>20,.2f}")
    print(f"{'TOTAL':6s} {sum(fy_rows.values()):>9,} {sum(fy_obl.values()):>20,.2f} "
          f"{sum(fy_rows_matched.values()):>12,} "
          f"{sum(fy_obl_matched.values()):>20,.2f}")

    print("\n=== LEDGER MATCH BY TIER ===")
    for t in sorted(tier_rows):
        print(f"tier {t or '(blank)'}: rows {tier_rows[t]:,}  "
              f"obligations {tier_obl[t]:,.2f}")
    print(f"distinct ledger UEIs hit: {len(matched_ueis):,}")
    print(f"rows with blank recipient_uei: {blank_uei_rows:,}")
    print(f"distinct UEIs NOT in ledger: {len(new_ueis):,} "
          f"({sum(new_ueis.values()):,} rows, "
          f"${sum(new_uei_obl.values()):,.2f})")
    print(f"  of which name looks Native: {len(unmatched_native):,}")

    # -- review file -------------------------------------------------------
    os.makedirs(REVIEW, exist_ok=True)
    out = os.path.join(REVIEW, "funding_new_period_unmatched_2026-08-05.csv")
    rows = sorted(unmatched_native.items(),
                  key=lambda kv: -kv[1]["obligations"])
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["recipient_uei", "recipient_name", "business_types_code",
                    "matched_tokens", "rows", "obligations",
                    "first_action_date", "last_action_date", "source", "note",
                    "YOUR_RULING"])
        for uei, d in rows:
            w.writerow([uei, d["recipient_name"], d["business_types_code"],
                        d["matched_tokens"], d["rows"],
                        f"{d['obligations']:.2f}",
                        d["first_action_date"], d["last_action_date"],
                        "USAspending /api/v2/download/transactions/ 2026-08-05",
                        "DISCOVERY POOL, NOT AN ATTRIBUTION. USAspending "
                        "recipient_type_names=indian_native_american_tribal_government "
                        "and business_types_code in {I,J,K}; UEI absent from "
                        "cedar_identifier_ledger_final.csv. matched_tokens is a "
                        "high-recall name screen and DOES include place-name false "
                        "positives (e.g. 'dakota' in NORTH DAKOTA INDUSTRIAL "
                        "COMMISSION). Rule each row on its own evidence.",
                        ""])
    log(f"wrote {out} ({len(rows):,} rows)")

    # full new-UEI list (all, not just name-looks-Native), for coverage expansion
    out2 = os.path.join(REVIEW, "funding_new_period_new_ueis_2026-08-05.csv")
    with open(out2, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["recipient_uei", "recipient_name", "rows", "obligations",
                    "name_looks_native"])
        for uei, cnt in sorted(new_ueis.items(), key=lambda kv: -new_uei_obl[kv[0]]):
            w.writerow([uei, new_uei_name.get(uei, ""), cnt,
                        f"{new_uei_obl[uei]:.2f}",
                        1 if uei in unmatched_native else 0])
    log(f"wrote {out2} ({len(new_ueis):,} rows)")

    summary = {
        "pull_date": PULL_DATE,
        "per_file": per_file,
        "action_date_min": min_action_date,
        "action_date_max": max_action_date,
        "business_types_code": dict(bt_counter),
        "fy_rows": dict(fy_rows),
        "fy_obligations": {k: round(v, 2) for k, v in fy_obl.items()},
        "fy_rows_ledger_matched": dict(fy_rows_matched),
        "fy_obligations_ledger_matched": {k: round(v, 2)
                                          for k, v in fy_obl_matched.items()},
        "tier_rows": dict(tier_rows),
        "tier_obligations": {k: round(v, 2) for k, v in tier_obl.items()},
        "distinct_ledger_ueis_hit": len(matched_ueis),
        "distinct_new_ueis": len(new_ueis),
        "new_uei_rows": sum(new_ueis.values()),
        "new_uei_obligations": round(sum(new_uei_obl.values()), 2),
        "new_ueis_name_looks_native": len(unmatched_native),
        "blank_uei_rows": blank_uei_rows,
        "schema_ncol": len(schema) if schema else None,
        "schema": schema,
    }
    sp = os.path.join(OUTDIR, "_summary_2026-08-05.json")
    with open(sp, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    log(f"wrote {sp}")


def _host_alive():
    try:
        r = requests.get(f"{API}/api/v2/references/agency/456/",
                         headers={"User-Agent": UA["User-Agent"]}, timeout=45)
        return r.status_code == 200
    except Exception:                                            # noqa: BLE001
        return False


def resume(probe_every=300, max_hours=6):
    """Gentle resume. Never regenerates a job that already exists.

    Why this mode exists: on 2026-08-05 four USAspending pullers were running
    from this machine at once (30_wait_and_pull, 37_wait_then_pull,
    40_pull_usaspending_subawards --workers 3, and this one). The host started
    dropping every connection at 17:17. Job *generation* is the metered
    resource, so a resumed run must reuse the file_name already recorded in
    response_<tag>.json and poll slowly rather than ask for the job again.
    """
    state_path = os.path.join(OUTDIR, "_state.json")
    state = json.load(open(state_path, encoding="utf-8")) \
        if os.path.exists(state_path) else {}
    deadline = time.time() + max_hours * 3600

    for tag, start, end in CHUNKS:
        rec = state.get(tag) or {}
        prime = [m for m in (rec.get("members") or [])
                 if m.lower().endswith(".csv") and "PrimeTransactions" in m]
        if prime and os.path.exists(os.path.join(OUTDIR, prime[0])):
            log(f"{tag}: already on disk -- skip")
            continue

        # Reuse an already-generated job if one was recorded.
        rp = os.path.join(OUTDIR, f"response_{tag}.json")
        file_name = None
        if os.path.exists(rp):
            file_name = json.load(open(rp, encoding="utf-8")).get("file_name")
            log(f"{tag}: reusing already-generated job {file_name}")

        while time.time() < deadline:
            if not _host_alive():
                log(f"{tag}: host still refusing; sleeping {probe_every}s")
                time.sleep(probe_every)
                continue

            if file_name is None:
                body = payload_for(start, end)
                with open(os.path.join(OUTDIR, f"request_{tag}.json"), "w",
                          encoding="utf-8") as fh:
                    json.dump({"endpoint": f"{API}/api/v2/download/transactions/",
                               "method": "POST",
                               "requested_utc":
                                   datetime.datetime.utcnow().isoformat() + "Z",
                               "payload": body}, fh, indent=2)
                log(f"{tag}: POST download/transactions {start} .. {end}")
                try:
                    resp = requests.post(f"{API}/api/v2/download/transactions/",
                                         json=body, headers=UA, timeout=180)
                    if resp.status_code != 200:
                        log(f"{tag}: HTTP {resp.status_code}; backing off")
                        time.sleep(probe_every)
                        continue
                    resp = resp.json()
                except Exception as e:                           # noqa: BLE001
                    log(f"{tag}: {type(e).__name__}: {e}; backing off")
                    time.sleep(probe_every)
                    continue
                with open(rp, "w", encoding="utf-8") as fh:
                    json.dump(resp, fh, indent=2)
                file_name = resp.get("file_name")
                log(f"{tag}: job {file_name}")

            surl = f"{API}/api/v2/download/status/?file_name={file_name}"
            try:
                s = requests.get(surl, headers={"User-Agent": UA["User-Agent"]},
                                 timeout=120).json()
            except Exception as e:                               # noqa: BLE001
                log(f"{tag}: poll dropped ({type(e).__name__}); "
                    f"sleeping {probe_every}s")
                time.sleep(probe_every)
                continue

            st = s.get("status")
            log(f"{tag}: status={st} rows={s.get('total_rows')}")
            if st == "failed":
                log(f"{tag}: job failed server-side; will regenerate")
                file_name = None
                os.remove(rp)
                time.sleep(probe_every)
                continue
            if st != "finished":
                time.sleep(120)
                continue

            url = s.get("file_url") or \
                f"https://files.usaspending.gov/generated_downloads/{file_name}"
            log(f"{tag}: downloading {url}")
            try:
                r = get_with_retry(url, tries=4, stream=True)
            except Exception as e:                               # noqa: BLE001
                log(f"{tag}: download failed ({e}); retry after {probe_every}s")
                time.sleep(probe_every)
                continue
            zp = os.path.join(OUTDIR, file_name)
            with open(zp, "wb") as fh:
                for ch in r.iter_content(1 << 20):
                    fh.write(ch)
            log(f"{tag}: wrote {zp} ({os.path.getsize(zp):,} bytes)")
            members = []
            with zipfile.ZipFile(zp) as z:
                for nm in z.namelist():
                    z.extract(nm, OUTDIR)
                    members.append(nm)
            log(f"{tag}: extracted {members}")
            prime = [m for m in members if m.lower().endswith(".csv")
                     and "PrimeTransactions" in m]
            state.setdefault(tag, {}).update(
                {"start": start, "end": end, "zip": file_name,
                 "members": members, "status_json": s,
                 "csv_path": prime[0] if prime else None})
            with open(state_path, "w", encoding="utf-8") as fh:
                json.dump(state, fh, indent=2)
            time.sleep(90)          # be a good neighbour to the other pullers
            break
        else:
            log(f"{tag}: deadline reached without completion")

    log("resume complete")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "resume"
    if cmd == "pull":
        pull()
    elif cmd == "resume":
        resume()
    elif cmd == "build":
        build()
    else:
        sys.exit(__doc__)
