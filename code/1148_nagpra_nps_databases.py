#!/usr/bin/env python3
"""
1148_nagpra_nps_databases.py - the National NAGPRA Program's own six databases.

Cedar Press collection `nagpra`.  Six NEW tables, plus one corroboration table
that is the point of the whole pass.

    data/clean/nagpra_nps_grant_awards.csv          NAGPRA grants, FY1994-
    data/clean/nagpra_nps_inventories.csv           inventory MNI/AFO by origin
    data/clean/nagpra_nps_summaries.csv             institution -> tribes consulted
    data/clean/nagpra_nps_intended_dispositions.csv notices of intended disposition
    data/clean/nagpra_nps_notice_index.csv          NPS's own notice register
    data/clean/nagpra_nps_unclaimed_remains.csv     unclaimed human remains
    data/clean/nagpra_notice_source_corroboration.csv

WHY THIS IS NOT A REPUBLICATION OF WHAT CEDAR ALREADY HOLDS
-----------------------------------------------------------
`nagpra_notices.csv` (6,792 rows) is parsed out of the FEDERAL REGISTER TEXT by
`code/77_build_nagpra_dataset.py`.  `docs/NAGPRA_BUILD_LOG.md` line 20 says the
National NAGPRA Program "publishes a notice *search*, not the notices as data."
**That is now false**: the search at `apps.cr.nps.gov/nagprapublic` is a
server-side DataTables grid whose JSON endpoint returns the register as data,
including the Program's OWN `TotalMNI` and `TotalAFO` per notice.

So this is the thing `START_HERE.md` item 0 asks for and that the assertion
layer has never had: **a genuinely independent evidence family for a fact Cedar
already asserts.**  Cedar's MNI comes from reading the notice's prose; NPS's
comes from the Program's internal record of the same repatriation.  They are
two observers, not one source copied twice, and where they disagree that is a
FINDING - `nagpra_notice_source_corroboration.csv` records agreement and
disagreement per notice and NEITHER value is overwritten.

The other five tables have no Cedar counterpart at all.

THE GRANTS TABLE PARTLY DOES, AND THE CHECK CHANGED THE CLAIM.  A first draft
of this docstring said NAGPRA grants "appear in no other Cedar table."  That is
FALSE and the measurement is worth carrying:
`federal_funding_transactions.csv` holds **696 rows on CFDA 15.922 (NATIVE
AMERICAN GRAVES PROTECTION AND REPATRIATION ACT), FY2007-2026, $11,215,956.86**.
What it does NOT hold is the years:

    Cedar assistance, CFDA 15.922   FY2007  1 row  $4,000 | FY2008-2012  ZERO
    NPS grants database             FY2007-2012  212 awards  $10,556,264

**736 of the 1,221 awards - $38,248,137 - are FY2012 or earlier, a window in
which Cedar's assistance stream holds one $4,000 transaction.**  From FY2013 the
two overlap but do not agree: Cedar counts transactions (modifications
included, and FY2026 nets to -$29,464 in deobligations) while NPS publishes the
award, so the annual dollars run roughly a third to a half of the NPS figure.
Treat them as two grains of one programme, never as one series - and never sum
them together.

SOURCE, ROUTE AND TERMS
-----------------------
Host `apps.cr.nps.gov`, path `/nagprapublic/home/get*`, POST, the standard
DataTables server-side protocol the public grid itself uses.  No login, no
token, no admin path - the same request the "CSV" and "Excel" export buttons on
each public page issue.  `https://apps.cr.nps.gov/robots.txt` is **404**, which
per `docs/PULL_DISCIPLINE.md` is NOT a disallow (a site that will not serve a
robots file is not a site that forbids you); `https://www.nps.gov/robots.txt`
answers 200 and disallows only `/ns/`, `/search/` and `/loader.cfm`, none of
which is on this path.  U.S. National Park Service work: the NPS disclaimer
states the material "is generally considered in the public domain", so
`source_terms_status = TERMS_STATED_NO_REUSE_RESTRICTION` - which is the value
`cedar_publication.GATES` allows.  See the comment on `TERMS` below: the
accurate-sounding `PUBLIC_DOMAIN_US_GOVERNMENT_WORK` is NOT in that allow-set
and would have withheld all 21,658 rows from the product without a word.

REFUSED, DELIBERATELY: `/nagprapublic/home/getcontacts`.  Its columns are
`FirstName, LastName, Company, Title, Phone, Email` - a natural person's
contact details.  It is reachable and it is not harvested.  See `REFUSED_EP`.

RUN
---
    py -3 code/1148_nagpra_nps_databases.py report    # no network
    py -3 code/1148_nagpra_nps_databases.py fetch     # hostlock, paged, resumable
    py -3 code/1148_nagpra_nps_databases.py apply     # the seven tables
    py -3 code/1148_nagpra_nps_databases.py verify    # exits 1 if it did not land
    py -3 code/1148_nagpra_nps_databases.py selftest  # proves verify FIRES

`verify` is a LANDING check, not a conservation check (AGENT_FIELD_GUIDE rule
5): per-table row floors taken from the source's own `recordsTotal`, the
corroboration table non-empty, and the refused endpoint absent from every
output.  `selftest` injects each breach and asserts the named invariant fires.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
LOGS = ROOT / "logs"
RAW = ROOT / "data" / "raw" / "external" / "nagpra_nps_1148"

HOST = "apps.cr.nps.gov"
HOSTLOCK = LOGS / f"_HOSTLOCK_{HOST}.json"
BASE = f"https://{HOST}/nagprapublic/home/"
UA = "CedarPress/1.0 (research data collection; elijahsamsonmoreno@gmail.com)"
PAGE = 1000
SLEEP_S = 1.5
MAX_RUN_S = 45 * 60
MAX_ATTEMPTS = 4

# MUST be a value in `cedar_publication.GATES["source_terms_status"]`
# ({SILENT, TERMS_STATED_NO_REUSE_RESTRICTION, ""}) or every row here is
# WITHHELD at publication time and nothing says so. The first draft wrote
# `PUBLIC_DOMAIN_US_GOVERNMENT_WORK`, which is true and would have gated all
# 21,658 rows out of the product silently. The vocabulary has no public-domain
# member; `TERMS_STATED_NO_REUSE_RESTRICTION` is the accurate one it does have,
# and the public-domain fact is carried in `source_terms_basis` and
# `source_terms_url` instead of being smuggled into the gate column.
TERMS = "TERMS_STATED_NO_REUSE_RESTRICTION"
TERMS_URL = "https://www.nps.gov/aboutus/disclaimer.htm"
TERMS_BASIS = (
    "National Park Service disclaimer, quoted 2026-09-02: 'material created by "
    "the National Park Service and presented on this website, unless otherwise "
    "indicated, is generally considered in the public domain. It may be "
    "distributed or copied as permitted by applicable law' (17 U.S.C. 101, "
    "105). Robots: apps.cr.nps.gov/robots.txt is 404, which is NOT a disallow; "
    "www.nps.gov/robots.txt answers 200 and disallows only /ns/, /search/ and "
    "/loader.cfm, none of which is on this path.")
BUILD_DATE = datetime.now(timezone.utc).strftime("%Y-%m-%d")

# Endpoint -> (referer page, DataTables column list, output table, out columns)
# The column lists are copied VERBATIM from each page's own `myArray.push`
# block; they are the server's contract, not a guess.
EP = {
    "getgrants": {
        "page": "grant",
        "cols": ["FiscalYear", "ApplicationType", "Name", "State",
                 "ApplicantType", "AmountAwarded"],
        "table": "nagpra_nps_grant_awards.csv",
        "map": {"FiscalYear": "fiscal_year", "ApplicationType": "grant_type",
                "Name": "recipient_name_as_recorded", "State": "recipient_state",
                "ApplicantType": "recipient_type",
                "AmountAwarded": "amount_awarded_usd"},
    },
    "getinventories": {
        "page": "inventory",
        # `InventoryType` is the second hidden default on this site and it is
        # the DISCRIMINATOR the published grid otherwise omits. Asked without
        # it the endpoint returns 11,812 rows of which 4,139 are literal
        # duplicates of another row - 35% - because culturally affiliated and
        # culturally UNIDENTIFIABLE holdings render as the same six columns.
        # Measured 2026-09-02: CulturallyAssociated 454 + NotCulturallyAssociated
        # 11,358 = 11,812 exactly. Splitting the pull recovers the distinction
        # instead of collapsing it, which matters here more than anywhere:
        # "culturally unidentifiable" is a legal status under 43 CFR 10.11 with
        # consequences for who may claim an ancestor.
        # NOTE, RECORDED NOT REPAIRED: on the NotCulturallyAssociated request
        # the server reports recordsTotal 11,358 and recordsFiltered 11,357 -
        # its own two counters disagree by one.
        "variants": [
            {"InventoryType": "CulturallyAssociated",
             "_label": "culturally_affiliated"},
            {"InventoryType": "NotCulturallyAssociated",
             "_label": "culturally_unidentifiable"},
        ],
        "cols": ["State", "Institution", "MNI", "AFO", "GeoOrigin", "County"],
        "table": "nagpra_nps_inventories.csv",
        "map": {"State": "institution_state", "Institution": "institution_name",
                "MNI": "mni", "AFO": "associated_funerary_objects",
                "GeoOrigin": "geographic_origin_state", "County": "geographic_origin_county"},
    },
    "getsummaries": {
        "page": "summary",
        "cols": ["State", "Institution", "Tribe"],
        "table": "nagpra_nps_summaries.csv",
        "map": {"State": "institution_state", "Institution": "institution_name",
                "Tribe": "tribes_listed_semicolon"},
    },
    "getnids": {
        "page": "nid",
        "cols": ["State", "Institution", "PublishedDate"],
        "table": "nagpra_nps_intended_dispositions.csv",
        "map": {"State": "institution_state", "Institution": "institution_name",
                "PublishedDate": "publication_as_recorded"},
    },
    "getnotices": {
        "page": "notice",
        # FOUR VARIANTS, NOT ONE. `NoticeType` is a radio group on the page and
        # it DEFAULTS TO `NIC`. A pull that never sends it returns 4,810 of
        # 6,818 rows - 70.6% - and looks complete, because the loop's own
        # `got >= recordsTotal` test never fires and `recordsFiltered` is the
        # only place the truncation is visible. Measured 2026-09-02:
        # NIC 4,810 + NIR 1,869 + NID 131 + NOT 8 = 6,818 exactly.
        # AGENT_FIELD_GUIDE section 3: read the denominator the server gives
        # you, not the one your loop computed.
        "variants": [
            {"NoticeType": "NIC", "_label": "notice_of_inventory_completion"},
            {"NoticeType": "NIR", "_label": "notice_of_intended_repatriation"},
            {"NoticeType": "NID", "_label": "notice_of_intended_disposition"},
            {"NoticeType": "NOT", "_label": "notice_of_transfer_or_reinterment"},
        ],
        "cols": ["State", "Institution", "PublicationDate", "RepatriationDate",
                 "FederalRegisterLink", "UFO", "SO", "CP", "CPOAndSO",
                 "TotalMNI", "TotalAFO"],
        "table": "nagpra_nps_notice_index.csv",
        "map": {"State": "institution_state", "Institution": "institution_name",
                "PublicationDate": "publication_date", "RepatriationDate": "repatriation_date",
                "FederalRegisterLink": "fr_document_number", "TotalMNI": "total_mni",
                "TotalAFO": "total_associated_funerary_objects",
                "UFO": "unassociated_funerary_objects", "SO": "sacred_objects",
                "CP": "objects_of_cultural_patrimony",
                "CPOAndSO": "sacred_objects_and_cultural_patrimony"},
    },
    "getunclaimedlists": {
        "page": "unclaimedlist",
        "cols": ["Institution", "State", "County", "MNI", "AFO", "UFO", "SO",
                 "OCP", "SOAndOCP"],
        "table": "nagpra_nps_unclaimed_remains.csv",
        "map": {"Institution": "institution_name", "State": "institution_state",
                "County": "county", "MNI": "mni",
                "AFO": "associated_funerary_objects",
                "UFO": "unassociated_funerary_objects", "SO": "sacred_objects",
                "OCP": "objects_of_cultural_patrimony",
                "SOAndOCP": "sacred_objects_and_cultural_patrimony"},
    },
}

# Reachable, NOT harvested. A natural person's contact details are outside what
# Cedar publishes even when the publisher is a federal agency and the page is
# open. docs/PUBLICATION_POLICY.md; AGENT_FIELD_GUIDE section 5.
REFUSED_EP = {
    "getcontacts": ("columns FirstName, LastName, Company, Title, Phone, Email "
                    "- a natural person's contact details. Reachable (HTTP 200, "
                    "measured 2026-09-02) and deliberately not harvested."),
}

CORROB = CLEAN / "nagpra_notice_source_corroboration.csv"
CEDAR_NOTICES = CLEAN / "nagpra_notices.csv"

PROV_COLS = ["source_dataset", "source_endpoint", "source_url",
             "source_terms_status", "source_terms_url", "source_terms_basis",
             "retrieved_at"]

# Floors for verify. Taken from the source's own recordsTotal on the first full
# run and deliberately set just under it. Never re-baselined to clear a gate.
FLOORS = {
    "nagpra_nps_grant_awards.csv": 1200,
    "nagpra_nps_inventories.csv": 11000,
    "nagpra_nps_summaries.csv": 1500,
    "nagpra_nps_intended_dispositions.csv": 240,
    "nagpra_nps_notice_index.csv": 6700,
    "nagpra_nps_unclaimed_remains.csv": 15,
}


# ---------------------------------------------------------------------------


def read_csv(p: Path) -> list[dict]:
    csv.field_size_limit(10 ** 9)
    with open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(p: Path, cols: list[str], rows: list[dict]) -> None:
    part = p.with_suffix(p.suffix + ".part")
    with open(part, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    os.replace(part, p)


def backup(p: Path) -> None:
    if not p.exists():
        return
    bak = p.with_name(p.name + f".bak_{BUILD_DATE}_pre_1148_nagpra_nps_databases")
    if bak.exists() and bak.stat().st_size == p.stat().st_size:
        return
    shutil.copy2(p, bak)


def variants_of(spec: dict) -> list[dict]:
    return spec.get("variants") or [{"_label": ""}]


def page_path(ep: str, start: int, label: str = "") -> Path:
    sub = f"{ep}__{label}" if label else ep
    return RAW / sub / f"start{start:07d}.json"


# ---------------------------------------------------------------------------
# network
# ---------------------------------------------------------------------------


def take_hostlock(queue: list[str]) -> bool:
    LOGS.mkdir(exist_ok=True)
    if HOSTLOCK.exists():
        try:
            cur = json.loads(HOSTLOCK.read_text(encoding="utf-8"))
        except Exception:
            cur = {}
        if not cur.get("released"):
            print(f"  HOSTLOCK {HOST} HELD by {cur.get('script')!r} "
                  f"(pid {cur.get('pid')}). Queued and exiting.")
            cur.setdefault("queue", []).extend(queue)
            HOSTLOCK.write_text(json.dumps(cur, indent=2), encoding="utf-8")
            return False
    HOSTLOCK.write_text(json.dumps({
        "host": HOST, "pid": os.getpid(),
        "script": "code/1148_nagpra_nps_databases.py",
        "started": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "queue": queue, "released": False}, indent=2), encoding="utf-8")
    return True


def release_hostlock() -> None:
    if not HOSTLOCK.exists():
        return
    try:
        cur = json.loads(HOSTLOCK.read_text(encoding="utf-8"))
    except Exception:
        return
    if cur.get("pid") == os.getpid():
        cur["released"] = True
        cur["released_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        HOSTLOCK.write_text(json.dumps(cur, indent=2), encoding="utf-8")


def datatables_post(ep: str, spec: dict, start: int, length: int,
                    extra: dict | None = None) -> dict:
    d = {"draw": "1", "start": str(start), "length": str(length),
         "search[value]": "", "search[regex]": "false",
         "order[0][column]": "0", "order[0][dir]": "asc", "State": ""}
    for k, v in (extra or {}).items():
        if not k.startswith("_"):
            d[k] = v
    for i, c in enumerate(spec["cols"]):
        d[f"columns[{i}][data]"] = c
        d[f"columns[{i}][name]"] = ""
        d[f"columns[{i}][searchable]"] = "true"
        d[f"columns[{i}][orderable]"] = "true"
        d[f"columns[{i}][search][value]"] = ""
        d[f"columns[{i}][search][regex]"] = "false"
    req = urllib.request.Request(
        BASE + ep, data=urllib.parse.urlencode(d).encode(),
        headers={"User-Agent": UA,
                 "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                 "X-Requested-With": "XMLHttpRequest",
                 "Accept": "application/json, text/javascript, */*; q=0.01",
                 "Referer": BASE + spec["page"]})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def cmd_fetch(only: str | None) -> int:
    eps = [e for e in EP if (not only or e == only)]
    if not take_hostlock(eps):
        return 0
    RAW.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    try:
        for ep in eps:
            spec = EP[ep]
            for var in variants_of(spec):
                label = var.get("_label", "")
                tag = f"{ep}[{label}]" if label else ep
                page_path(ep, 0, label).parent.mkdir(parents=True, exist_ok=True)
                start = 0
                filtered = None
                got = 0
                while True:
                    if time.time() - t0 > MAX_RUN_S:
                        print(f"  HARD STOP at {MAX_RUN_S}s inside {tag}. "
                              f"Resume by re-running fetch.")
                        return 0
                    p = page_path(ep, start, label)
                    if p.exists():
                        try:
                            j = json.loads(p.read_text(encoding="utf-8"))
                        except Exception:
                            p.unlink()
                            continue
                    else:
                        j = None
                        for attempt in range(1, MAX_ATTEMPTS + 1):
                            try:
                                j = datatables_post(ep, spec, start, PAGE, var)
                                break
                            except urllib.error.HTTPError as e:
                                if e.code in (429, 503):
                                    w = min(60 * 2 ** (attempt - 1), 900)
                                    print(f"    {tag} HTTP {e.code} - "
                                          f"backing off {w}s")
                                    time.sleep(w)
                                    continue
                                print(f"    {tag} HTTP {e.code} at "
                                      f"start={start}; stopping this variant")
                                break
                            except Exception as e:
                                w = min(30 * 2 ** (attempt - 1), 300)
                                print(f"    {tag} {type(e).__name__} - "
                                      f"retry in {w}s")
                                time.sleep(w)
                        if j is None:
                            break
                        j["_ep"] = ep
                        j["_variant"] = label
                        j["_variant_params"] = {k: v for k, v in var.items()
                                                if not k.startswith("_")}
                        j["_start"] = start
                        j["_retrieved_utc"] = datetime.now(timezone.utc).isoformat()
                        j["_source_url"] = BASE + ep
                        tmp = p.with_suffix(".json.part")
                        tmp.write_text(json.dumps(j), encoding="utf-8")
                        os.replace(tmp, p)
                        time.sleep(SLEEP_S)
                    # THE DENOMINATOR IS `recordsFiltered`, NOT `recordsTotal`.
                    # recordsTotal is the whole table; recordsFiltered is what
                    # THIS request's filters select. Reading the wrong one is
                    # how the notice pull silently stopped at 70.6%.
                    filtered = j.get("recordsFiltered", j.get("recordsTotal"))
                    n = len(j.get("data") or [])
                    got += n
                    print(f"  {tag:42s} start={start:>6,} got={n:>5,} "
                          f"cum={got:>7,} of {filtered} "
                          f"(table total {j.get('recordsTotal')})", flush=True)
                    if n == 0 or (filtered is not None and got >= int(filtered)):
                        if filtered is not None and got != int(filtered):
                            print(f"    WARNING {tag}: retrieved {got:,} "
                                  f"against recordsFiltered {filtered}")
                        break
                    start += PAGE
    finally:
        release_hostlock()
    print("  fetch done.")
    return 0


# ---------------------------------------------------------------------------
# apply
# ---------------------------------------------------------------------------


def load_ep(ep: str) -> tuple[list[dict], int | None, str]:
    """Return (rows, source recordsTotal, latest retrieved_at).

    Every row carries `_variant` so a multi-variant endpoint keeps the
    distinction the server made. Old single-variant cache directories are
    still read, so an earlier partial pull is not orphaned.
    """
    rows, total, retrieved = [], None, ""
    dirs = [d for d in sorted(RAW.iterdir()) if d.is_dir()
            and (d.name == ep or d.name.startswith(ep + "__"))] \
        if RAW.exists() else []
    for d in dirs:
        for p in sorted(d.glob("start*.json")):
            j = json.loads(p.read_text(encoding="utf-8"))
            total = j.get("recordsTotal", total)
            retrieved = max(retrieved, j.get("_retrieved_utc", "") or "")
            lab = j.get("_variant", "")
            for r in (j.get("data") or []):
                r = dict(r)
                r["_variant"] = lab
                rows.append(r)
    return rows, total, retrieved


def _norm_money(v: str) -> str:
    v = (v or "").strip().replace(",", "").replace("$", "")
    if not v:
        return ""
    try:
        return f"{float(v):.2f}"
    except Exception:
        return ""


def _norm_int(v) -> str:
    v = str(v or "").strip().replace(",", "")
    if v == "":
        return ""
    try:
        return str(int(float(v)))
    except Exception:
        return ""


def _iso(v: str) -> str:
    v = (v or "").strip()
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", v)
    if m:
        return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    return ""


def cmd_apply() -> int:
    written = {}
    for ep, spec in EP.items():
        raw, total, retrieved = load_ep(ep)
        if not raw:
            print(f"  {ep}: NO CACHE. Run fetch. (table not written)")
            continue
        out_cols = list(spec["map"].values()) + PROV_COLS
        # endpoint-specific derived columns
        if ep == "getgrants":
            out_cols = out_cols[:0] + list(spec["map"].values()) + PROV_COLS
        if ep == "getnotices":
            out_cols = (["notice_type", "notice_type_label"]
                        + list(spec["map"].values())
                        + ["publication_date_iso", "repatriation_date_iso"]
                        + PROV_COLS)
        if ep == "getsummaries":
            out_cols = list(spec["map"].values()) + ["n_tribes_listed"] + PROV_COLS
        if ep == "getinventories":
            out_cols = (["cultural_affiliation_status"]
                        + list(spec["map"].values()) + PROV_COLS)
        rows = []
        for r in raw:
            o = {}
            for src, dst in spec["map"].items():
                v = r.get(src)
                v = "" if v is None else str(v).strip()
                if dst == "amount_awarded_usd":
                    v = _norm_money(v)
                elif dst in ("mni", "total_mni", "associated_funerary_objects",
                             "total_associated_funerary_objects",
                             "unassociated_funerary_objects", "sacred_objects",
                             "objects_of_cultural_patrimony",
                             "sacred_objects_and_cultural_patrimony"):
                    v = _norm_int(v)
                o[dst] = v
            if ep == "getnotices":
                lab = r.get("_variant", "")
                o["notice_type_label"] = lab
                o["notice_type"] = {
                    "notice_of_inventory_completion": "NIC",
                    "notice_of_intended_repatriation": "NIR",
                    "notice_of_intended_disposition": "NID",
                    "notice_of_transfer_or_reinterment": "NOT",
                }.get(lab, "")
                o["publication_date_iso"] = _iso(o.get("publication_date", ""))
                o["repatriation_date_iso"] = _iso(o.get("repatriation_date", ""))
            if ep == "getinventories":
                o["cultural_affiliation_status"] = {
                    "culturally_affiliated": "CULTURALLY_AFFILIATED",
                    "culturally_unidentifiable": "CULTURALLY_UNIDENTIFIABLE",
                }.get(r.get("_variant", ""), "")
            if ep == "getsummaries":
                t = o.get("tribes_listed_semicolon", "")
                o["n_tribes_listed"] = str(len([x for x in t.split(";")
                                                if x.strip()])) if t else "0"
            o.update({
                "source_dataset": f"national_nagpra_online_database:{ep}",
                "source_endpoint": ep,
                "source_url": BASE + ep,
                "source_terms_status": TERMS,
                "source_terms_url": TERMS_URL,
                "source_terms_basis": TERMS_BASIS,
                "retrieved_at": retrieved[:19],
            })
            rows.append(o)
        p = CLEAN / spec["table"]
        backup(p)
        write_csv(p, out_cols, rows)
        written[spec["table"]] = (len(rows), total)
        print(f"  WROTE {spec['table']:44s} {len(rows):>7,} rows "
              f"(source recordsTotal {total})")

    # ---- the corroboration table --------------------------------------
    nps_rows, _, _ = load_ep("getnotices")
    if nps_rows and CEDAR_NOTICES.exists():
        cedar = read_csv(CEDAR_NOTICES)
        ccol = "document_number" if cedar and "document_number" in cedar[0] else None
        mcol = None
        for cand in ("mni_total_stated", "mni_total", "mni"):
            if cedar and cand in cedar[0]:
                mcol = cand
                break
        by_doc = {}
        for r in cedar:
            if ccol and r.get(ccol):
                by_doc[r[ccol].strip()] = r
        # ONE DECLARED KEY REPAIR, AND ONLY ONE. Two NPS rows write the FR
        # document number with a literal '?' where the hyphen belongs
        # (`2016?26975`, `2016?29537`); both '-' forms exist in Cedar and
        # neither '?' form does, so without this the same notice appears once
        # as IN_NPS_ONLY and once as IN_CEDAR_ONLY and the corroboration is
        # wrong twice. Measured 2026-09-02 across all 6,818 NPS rows: 608 are
        # non-canonical and 606 of those are legitimate FR prefixes
        # (E8-/E9-/X94-/R7-), which are NOT touched. The repair applies only
        # when substituting '-' for '?' yields a key Cedar actually holds.
        nps_by_doc = defaultdict(list)
        repaired = {}
        for r in nps_rows:
            k = (r.get("FederalRegisterLink") or "").strip()
            if not k:
                continue
            if "?" in k and k not in by_doc:
                cand = k.replace("?", "-")
                if cand in by_doc:
                    repaired[k] = cand
                    k = cand
            nps_by_doc[k].append(r)
        if repaired:
            print(f"  key repair '?'->'-' applied to {len(repaired)}: "
                  f"{repaired}")

        out = []
        st = Counter()
        for doc in sorted(set(by_doc) | set(nps_by_doc)):
            c = by_doc.get(doc)
            n = nps_by_doc.get(doc)
            cv = _norm_int(c.get(mcol, "")) if (c and mcol) else ""
            # A SET WOULD SILENTLY DE-DUPLICATE TWO LINES OF ONE NOTICE.
            # `{norm(x) for x in rows}` collapses two lines each reporting 5
            # into one 5, and the sum then reads 5 instead of 10 - invisibly,
            # and only on the rows where it matters. Sum the LIST.
            # Three FR documents carry two NPS rows (Autry E7-5977, Field
            # Museum 04-17582 - byte-identical, a source duplicate - and AMNH
            # 2012-26223). All three are NIR with total_mni 0, so the sum is
            # 0 either way today; the handling is written for the case where
            # it is not, and such a document is reported
            # NOT_TESTABLE_MULTIPLE_NPS_ROWS rather than quietly aggregated
            # against a single Cedar figure.
            if n:
                vals = [_norm_int(x.get("TotalMNI")) for x in n]
                vals = [v for v in vals if v != ""]
                nv = str(sum(int(v) for v in vals)) if vals else ""
            else:
                nv = ""
            if c is None:
                status = "IN_NPS_ONLY"
            elif not n:
                status = "IN_CEDAR_ONLY"
            elif len(n) > 1:
                status = "NOT_TESTABLE_MULTIPLE_NPS_ROWS"
            elif cv == "" or nv == "":
                status = "NOT_TESTABLE_NO_MNI_ONE_SIDE"
            elif cv == nv:
                status = "AGREE"
            else:
                status = "DISAGREE"
            st[status] += 1
            out.append({
                "fr_document_number": doc,
                "in_cedar_nagpra_notices": "Y" if c else "N",
                "in_nps_notice_index": "Y" if n else "N",
                "n_nps_rows_for_this_document": str(len(n or [])),
                "cedar_mni_total_stated": cv,
                "nps_total_mni": nv,
                "corroboration_status": status,
                "cedar_source": (f"data/clean/nagpra_notices.csv "
                                 f"({mcol}), parsed from Federal Register text "
                                 f"by code/77_build_nagpra_dataset.py"),
                "nps_source": BASE + "getnotices",
                "evidence_families": "2_FEDERAL_REGISTER_TEXT_AND_NPS_PROGRAM_RECORD",
                "corroboration_basis": (
                    "two observers of one repatriation: Cedar reads the notice "
                    "prose, NPS reports its own programme record. NEITHER VALUE "
                    "IS OVERWRITTEN; a DISAGREE row is a finding, not an error "
                    "to resolve."),
                "retrieved_at": BUILD_DATE,
            })
        cols = list(out[0].keys())
        backup(CORROB)
        write_csv(CORROB, cols, out)
        print(f"  WROTE {CORROB.name:44s} {len(out):>7,} rows")
        print(f"  corroboration: {dict(st)}")
        written[CORROB.name] = (len(out), None)
    else:
        print("  corroboration SKIPPED: no getnotices cache or no "
              "nagpra_notices.csv")

    # refused endpoint, recorded so the refusal is visible
    for ep, why in REFUSED_EP.items():
        print(f"  REFUSED {ep}: {why}")
    return 0


# ---------------------------------------------------------------------------
# verify / selftest
# ---------------------------------------------------------------------------


def cmd_verify(quiet: bool = False) -> int:
    bad = 0

    # NPS-1  every table landed, at or above its floor
    for tbl, floor in FLOORS.items():
        p = CLEAN / tbl
        if not p.exists():
            print(f"  FAIL NPS-1: {tbl} does not exist. The work did not land.")
            bad += 1
            continue
        n = len(read_csv(p))
        if n < floor:
            print(f"  FAIL NPS-1: {tbl} has {n:,} rows < floor {floor:,}. "
                  f"Reverted or partial.")
            bad += 1

    # NPS-2  corroboration table exists and actually corroborates something
    if not CORROB.exists():
        print(f"  FAIL NPS-2: {CORROB.name} does not exist.")
        bad += 1
    else:
        cor = read_csv(CORROB)
        tested = [r for r in cor if r["corroboration_status"] in
                  ("AGREE", "DISAGREE")]
        if len(tested) < 1000:
            print(f"  FAIL NPS-2: only {len(tested):,} notices could be "
                  f"compared on MNI; the second source is not landing.")
            bad += 1

    # NPS-3  provenance on every row of every table
    for tbl in FLOORS:
        p = CLEAN / tbl
        if not p.exists():
            continue
        rows = read_csv(p)
        miss = sum(1 for r in rows if not (r.get("source_terms_status") or "").strip())
        if miss:
            print(f"  FAIL NPS-3: {tbl} has {miss:,} rows with no "
                  f"source_terms_status")
            bad += 1

    # NPS-4  the refused endpoint never reached a table
    for tbl in list(FLOORS) + [CORROB.name]:
        p = CLEAN / tbl
        if not p.exists():
            continue
        head = open(p, encoding="utf-8").readline().lower()
        for banned in ("firstname", "lastname", "email", "phone"):
            if banned in head:
                print(f"  FAIL NPS-4: {tbl} carries a column named "
                      f"{banned!r} - the refused contacts endpoint leaked.")
                bad += 1
    if (RAW / "getcontacts").exists():
        print(f"  FAIL NPS-4: {RAW/'getcontacts'} exists on disk; the refused "
              f"endpoint was fetched.")
        bad += 1

    # NPS-5  money is parseable and non-zero in aggregate
    p = CLEAN / "nagpra_nps_grant_awards.csv"
    if p.exists():
        rows = read_csv(p)
        tot = 0.0
        badm = 0
        for r in rows:
            v = r.get("amount_awarded_usd", "")
            if v == "":
                badm += 1
                continue
            try:
                tot += float(v)
            except Exception:
                badm += 1
        if tot <= 0:
            print("  FAIL NPS-5: grant dollars sum to 0.")
            bad += 1
        elif not quiet:
            print(f"  grants: {len(rows):,} awards, "
                  f"${tot:,.2f}, {badm:,} unparseable")

    if not quiet:
        print("  " + ("VERIFY OK" if bad == 0 else f"VERIFY FAILED ({bad})"))
    return 1 if bad else 0


def cmd_selftest() -> int:
    if cmd_verify(quiet=True) != 0:
        print("  UNMEASURED: live tables already fail verify; selftest cannot "
              "distinguish its own injection.")
        return 1
    tbl = CLEAN / "nagpra_nps_grant_awards.csv"
    baks = {}
    for p in [tbl, CORROB]:
        b = p.with_suffix(".csv.selftest_bak")
        shutil.copy2(p, b)
        baks[p] = b
    ok = True
    try:
        rows = read_csv(tbl)
        cols = list(rows[0].keys())
        cor = read_csv(CORROB)
        ccols = list(cor[0].keys())

        cases = [
            ("NPS-1", lambda: write_csv(tbl, cols, rows[:5])),
            ("NPS-2", lambda: write_csv(
                CORROB, ccols,
                [dict(r, corroboration_status="NOT_TESTABLE_NO_MNI_ONE_SIDE")
                 for r in cor])),
            ("NPS-3", lambda: write_csv(
                tbl, cols, [dict(r, source_terms_status="") for r in rows])),
            ("NPS-4", lambda: write_csv(tbl, cols + ["Email"],
                                        [dict(r, Email="") for r in rows])),
            ("NPS-5", lambda: write_csv(
                tbl, cols, [dict(r, amount_awarded_usd="0") for r in rows])),
        ]
        for inv, inject in cases:
            for p, b in baks.items():
                shutil.copy2(b, p)
            inject()
            buf = io.StringIO()
            real, sys.stdout = sys.stdout, buf
            try:
                rc = cmd_verify(quiet=True)
            finally:
                sys.stdout = real
            fired = rc == 1 and inv in buf.getvalue()
            print(f"  {inv}: exit {rc}, {'FIRED' if fired else 'DID NOT FIRE'}")
            ok = ok and fired
    finally:
        for p, b in baks.items():
            shutil.copy2(b, p)
            b.unlink(missing_ok=True)
    rc = cmd_verify(quiet=True)
    print(f"  restored, verify exit {rc}")
    ok = ok and rc == 0
    print("  SELFTEST " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def cmd_report() -> int:
    print("=" * 74)
    print("1148 report - National NAGPRA online databases. No network here.")
    print("=" * 74)
    for ep, spec in EP.items():
        rows, total, ret = load_ep(ep)
        p = CLEAN / spec["table"]
        live = len(read_csv(p)) if p.exists() else 0
        print(f"  {ep:20s} cache {len(rows):>7,} (source total {total}) "
              f"-> {spec['table']:44s} live {live:>7,}")
    for ep, why in REFUSED_EP.items():
        print(f"  {ep:20s} REFUSED - {why}")
    if CORROB.exists():
        cor = read_csv(CORROB)
        st = Counter(r["corroboration_status"] for r in cor)
        print(f"  {CORROB.name}: {len(cor):,} rows {dict(st)}")
    return 0


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1]
    return {"report": cmd_report, "fetch": lambda: cmd_fetch(only),
            "apply": cmd_apply, "verify": cmd_verify,
            "selftest": cmd_selftest}.get(cmd, lambda: (print(__doc__), 2)[1])()


if __name__ == "__main__":
    raise SystemExit(main())
