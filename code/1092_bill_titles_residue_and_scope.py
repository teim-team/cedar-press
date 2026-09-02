#!/usr/bin/env python3
# lint-ok: class6 - an IN-PLACE ENRICHER by design. It reads native_bills.csv
# and writes it back with `title` filled on the residue rows and the two
# `bill_scope` columns refreshed. Ordering: AFTER 14_build_bills_votes.py and
# AFTER 73_bills_votes_completion.py, and 890 must run AFTER THIS ONE so the
# newly-titled bills reach bill_votes.bill_title. Declared in
# cedar_pipeline.KNOWN_ORDERINGS.
"""
Cedar Press - 1092: finish the bill-title backfill, and un-stale the scope
column the first backfill left behind.

    py -3 code/1092_bill_titles_residue_and_scope.py measure   # read-only, no network
    py -3 code/1092_bill_titles_residue_and_scope.py pull      # api.congress.gov, <= 12 requests
    py -3 code/1092_bill_titles_residue_and_scope.py write     # in-place enrich native_bills.csv
    py -3 code/1092_bill_titles_residue_and_scope.py verify    # read-only, exit 1
    py -3 code/1092_bill_titles_residue_and_scope.py selftest  # prove verify fires

WHY - TWO DEFECTS, AND NEITHER IS A SOURCE GAP
==============================================

**1. Eight bills carry no title, and all eight share one cause: a bill_type
slug the puller's own allow-list rejects.** Measured 2026-09-02 with
csv.reader over all 3,069 rows of `native_bills.csv`:

    bill_type   rows   with a title
    hr          1651   1651
    s           1332   1332
    hres          38     38
    hjres         23     23
    sjres         12     12
    sconres        5      5
    ---------------------------------  every canonical slug: 100%
    hre            2      0
    hjr            1      0
    treatydoc      2      0
    treatydocno    3      0
    ---------------------------------  every NON-canonical slug: 0%

`code/14_pull_cosponsors.py` line ~87 hard-codes
`ok_types = {"hr","s","hres","sres","hjres","sjres","hconres","sconres"}` and
`73_bills_votes_completion.py --titles` reproduced that filter. `hre` IS
`hres` and `hjr` IS `hjres` - Voteview's abbreviation, not a different kind of
measure - so three of the eight were never asked for because Cedar spelled the
type wrong, not because congress.gov withholds them. That is `NOT_ACQUIRED`,
the only one of the four states in AGENT_FIELD_GUIDE.md sec.5 that is a real
acquisition task, and it is twelve HTTP requests wide.

The remaining five are treaty documents, which do not live on `/bill` at all.
They live on `/treaty/{congress}/{number}`, a different endpoint nobody had
called.

**2. The 2026-08-05 backfill filled 128 titles and never re-ran the scope
ruler, so 128 rows still say `bill_scope_basis = no_title_available` while
carrying a title.** [measured 2026-09-02: 128 of 128 rows whose `record_basis`
contains `title_backfill` have a non-blank `title`, a blank `bill_scope`, and
`bill_scope_basis = 'no_title_available'`.] This is the ordering defect
`code/287_build_dependency_manifest.py` exists to catch, in its purest form:
an enricher wrote a column that another derivation depends on, and that
derivation was never replayed. `93-hr-10337` - *"An Act to provide for final
settlement of the conflicting rights and interests of the Hopi and Navajo
Tribes..."* - is scored `no_title_available` today.

    bill_scope blank on 168 of 3,069 = 128 (backfilled, stale)
                                     +   8 (the residue above)
                                     +  32 (73 --sweep rows, blank basis)

THE IDENTIFIER PROBLEM, AND HOW IT IS SETTLED BY EVIDENCE RATHER THAN BY GUESS
==============================================================================
Voteview writes the treaty identifier into `bill_number` WITH NO SEPARATOR:

    S099-0723  bill_number = TREATYDOCNO98    dtl_desc quotes 'TREATY DOC. NO. 98-29'
    S099-0724  bill_number = TREATYDOCNO97    dtl_desc quotes 'TREATY DOC. NO. 97-12'
    S099-0725  bill_number = TREATYDOCNO99    dtl_desc quotes 'TREATY DOC. NO. 99-11'
    S116-0208  bill_number = TREATYDOC1134    dtl_desc EMPTY
    S117-0809  bill_number = TREATYDOC1173    dtl_desc EMPTY

Cedar's `bill_id` then took the digits as the *number*, so `99-treatydocno-98`
means treaty doc **98-29** and its "98" is a CONGRESS. The three 99th-Congress
rows are unambiguous: **the vote's own question text quotes the full
identifier verbatim**, so nothing is inferred.

`TREATYDOC1134` and `TREATYDOC1173` are ambiguous - 1|134, 11|34, 113|4 all
read that string. **This script does not pick the plausible one.** It fetches
every candidate whose congress is inside the API's own treaty coverage (94th
forward) and accepts a candidate ONLY if the treaty's action list contains a
Senate action ON THE DATE OF THE ROLL CALL. Zero surviving candidates or more
than one is a REFUSAL written to the staging file as
`UNRESOLVED_AMBIGUOUS_IDENTIFIER`, never a choice.

WHAT THIS SCRIPT WILL NOT DO
============================
* It will not touch the 25 votes with no `bill_id`. Twenty-two are Panama
  Canal / US-UK tax treaty reservation votes with no bill and no bill title;
  three name a measure in their question text but assigning them a `bill_id`
  changes the vote-to-bill linkage, `n_rollcalls` and the entity bridge, which
  is a build decision and not an enrichment. `890` already states the reason
  on each row and `1093` re-states the classification.
* It will not paraphrase, shorten or case-fold a title. Verbatim or blank.
* It will not run the scope ruler on a row whose title is still blank.

WHAT IT READS / WRITES
======================
reads   data/clean/native_bills.csv
        data/raw/external/votingpatterns/HSall_rollcalls.csv  (identifier evidence)
        data/spine/cedar_entity_spine.csv                     (via 14's scope ruler)
network api.congress.gov  /bill/{c}/{type}/{n}   and  /treaty/{c}/{n}
staging data/raw/external/congress_gov/1092_title_residue/*.json   (raw, verbatim)
        data/raw/external/congress_gov/1092_title_residue_targets.csv
writes  data/clean/native_bills.csv   (in place; .bak_<date>_pre_1092_... first)
        columns touched: title, record_basis, bill_scope, bill_scope_basis
        rows: 3,069 in -> 3,069 out, proven every run
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CLEAN = ROOT / "data" / "clean"
SPINE = ROOT / "data" / "spine"
RAW = ROOT / "data" / "raw" / "external"
LOGS = ROOT / "logs"
sys.path.insert(0, str(HERE))
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()
STEM = "1092_bill_titles_residue_and_scope"

BILLS = CLEAN / "native_bills.csv"
VOTEVIEW = RAW / "votingpatterns" / "HSall_rollcalls.csv"
STAGE_DIR = RAW / "congress_gov" / "1092_title_residue"
STAGE_CSV = RAW / "congress_gov" / "1092_title_residue_targets.csv"

HOST = "api.congress.gov"
BASE = "https://api.congress.gov/v3"
HOSTLOCK = LOGS / f"_HOSTLOCK_{HOST}.json"
ENVFILE = Path(r"C:\Users\esm247\Desktop\votingpatterns\.env")
# The field guide records a 403 from this host as a MISSING USER-AGENT, not an
# access restriction. Declare a real one, the same one 14_pull_cosponsors.py
# used for the only other live call this dataset has ever made.
UA = ("Mozilla/5.0 (academic research; Cedar Press; "
      "elijahsamsonmoreno@gmail.com)")
SLEEP = 0.7
RUN_DEADLINE_S = 900          # this job is 12 requests; 15 minutes is generous

# The API's own treaty coverage floor. congress.gov publishes treaty documents
# from the 94th Congress (1975) forward; below that the endpoint 404s and a
# 404 there is coverage, not absence of the treaty.
TREATY_COVERAGE_FROM = 94

# --- the eight targets -----------------------------------------------------
# Every entry states the EVIDENCE for its identifier. `question_quotes` means
# the roll call's own dtl_desc contains the identifier as a literal string and
# nothing is inferred. `ambiguous_split` means the identifier must be settled
# against the treaty's own action dates before anything is written.
BILL_TARGETS = [
    # cedar bill_id      congress  api type  number  why the slug changed
    ("94-hre-1210",  94, "hres",  "1210",
     "Voteview writes House Resolution as `hre`; the congress.gov bill type "
     "code is `hres`. Same measure, different abbreviation."),
    ("95-hre-1030",  95, "hres",  "1030",
     "Voteview writes House Resolution as `hre`; the congress.gov bill type "
     "code is `hres`. Same measure, different abbreviation."),
    ("96-hjr-637",   96, "hjres", "637",
     "Voteview writes House Joint Resolution as `hjr`; the congress.gov bill "
     "type code is `hjres`. Same measure, different abbreviation."),
]

TREATY_TARGETS = [
    # cedar bill_id           vote_id     evidence      candidates [(cong,num)]
    ("99-treatydocno-98",  "S099-0723", "question_quotes", [(98, 29)],
     "The roll call's own dtl_desc reads 'TO ADOPT TREATY DOC. NO. 98-29, "
     "REQUEST FOR ADVICE AND CONSENT TO WITHDRAWAL OF A RESERVATION MADE TO "
     "THE 1975 PATENT COOPERATION TREATY.' - the identifier is published on "
     "the vote row, not inferred from it."),
    ("99-treatydocno-97",  "S099-0724", "question_quotes", [(97, 12)],
     "The roll call's own dtl_desc reads 'TO ADOPT TREATY DOC. NO. 97-12, "
     "INTER-AMERICAN CONVENTION ON COMMERCIAL ARBITRATION, WITH THREE "
     "RESERVATIONS.'"),
    ("99-treatydocno-99",  "S099-0725", "question_quotes", [(99, 11)],
     "The roll call's own dtl_desc reads 'TO ADOPT TREATY DOC. NO. 99-11, "
     "HAGUE CONVENTION ON THE CIVIL ASPECTS OF INTERNATIONAL CHILD "
     "ABDUCTION, WITH TWO RESERVATIONS.'"),
    ("116-treatydoc-1134", "S116-0208", "ambiguous_split",
     [(1, 134), (11, 34), (113, 4)],
     "Voteview writes `TREATYDOC1134` with no separator and its dtl_desc is "
     "EMPTY. Three splits read that string. The candidate is accepted only if "
     "the treaty's own action list carries a Senate action on the roll call's "
     "date."),
    ("117-treatydoc-1173", "S117-0809", "ambiguous_split",
     [(1, 173), (11, 73), (117, 3)],
     "Voteview writes `TREATYDOC1173` with no separator and its dtl_desc is "
     "EMPTY. Three splits read that string. The candidate is accepted only if "
     "the treaty's own action list carries a Senate action on the roll call's "
     "date."),
]

STAGE_FIELDS = ["cedar_bill_id", "vote_id", "endpoint", "url", "http_status",
                "identifier_evidence", "accepted", "title_verbatim",
                "title_field", "reject_reason", "fetched_utc"]


# ---------------------------------------------------------------------------
# small shared helpers
# ---------------------------------------------------------------------------
def read_csv(p: Path):
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        return list(rd.fieldnames or []), list(rd)


def measure_rows(p: Path) -> int:
    """Row count by csv.reader. Never from a manifest or a docstring."""
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        r = csv.reader(fh)
        next(r, None)
        return sum(1 for _ in r)


def write_csv_atomic(p: Path, fields: list, rows: list) -> None:
    part = p.with_suffix(p.suffix + ".part")
    with part.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore",
                           lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    os.replace(part, p)


# ---------------------------------------------------------------------------
# NETWORK - one poller per host, .part then rename, real User-Agent
# ---------------------------------------------------------------------------
def get_key() -> str:
    k = os.environ.get("CONGRESS_API_KEY", "").strip()
    if k:
        return k
    if ENVFILE.exists():
        for line in ENVFILE.read_text(encoding="utf-8-sig",
                                      errors="replace").splitlines():
            m = re.match(r"\s*(?:export\s+)?CONGRESS_API_KEY\s*=\s*"
                         r"['\"]?([^'\"\s]+)", line)
            if m:
                return m.group(1)
    return ""


def take_hostlock(script: str) -> bool:
    """Return True if the host is ours. Never steal a live lock."""
    if HOSTLOCK.exists():
        try:
            cur = json.loads(HOSTLOCK.read_text(encoding="utf-8"))
        except Exception:
            cur = {}
        if not cur.get("released"):
            print(f"  HOSTLOCK {HOST} is HELD by {cur.get('script')!r} "
                  f"(pid {cur.get('pid')}, started {cur.get('started')}). "
                  f"Deferring - PULL_DISCIPLINE rule 1, one poller per host.")
            return False
    LOGS.mkdir(exist_ok=True)
    HOSTLOCK.write_text(json.dumps({
        "host": HOST, "pid": os.getpid(), "script": f"code/{script}",
        "started": datetime.now(timezone.utc).isoformat(), "queue": [],
        "note": "1092 title residue: <=12 GETs, /bill and /treaty",
    }, indent=1), encoding="utf-8")
    return True


def release_hostlock(note: str) -> None:
    try:
        cur = json.loads(HOSTLOCK.read_text(encoding="utf-8"))
    except Exception:
        cur = {"host": HOST}
    cur["released"] = datetime.now(timezone.utc).isoformat()
    cur["note"] = note
    HOSTLOCK.write_text(json.dumps(cur, indent=1), encoding="utf-8")


def api_get(path: str, key: str, deadline: float):
    """Return (json_or_None, status_string, full_url_without_key)."""
    shown = f"{BASE}{path}?format=json"
    if time.time() > deadline:
        return None, "run_deadline_exceeded", shown
    url = f"{BASE}{path}?" + urllib.parse.urlencode(
        {"format": "json", "api_key": key})
    delay = 2.0
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={
                "Accept": "application/json", "User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                body = json.loads(r.read().decode("utf-8"))
            time.sleep(SLEEP)
            return body, "http_200", shown
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None, "http_404", shown
            if e.code == 403:
                # The field guide's recorded trap. We DO send a UA, so a 403
                # here is a real refusal or a bad key - say which, do not
                # silently retry it into a "source is empty".
                return None, "http_403_with_declared_user_agent", shown
            if e.code in (429, 500, 502, 503, 504):
                if time.time() + delay > deadline:
                    return None, f"http_{e.code}_deadline", shown
                time.sleep(delay)
                delay *= 2
                continue
            return None, f"http_{e.code}", shown
        except Exception as ex:                       # noqa: BLE001
            if time.time() + delay > deadline:
                return None, f"error_deadline:{type(ex).__name__}", shown
            time.sleep(delay)
            delay *= 2
    return None, "failed_after_retries", shown


def stage_raw(name: str, payload) -> None:
    STAGE_DIR.mkdir(parents=True, exist_ok=True)
    p = STAGE_DIR / f"{name}.json"
    part = p.with_suffix(".json.part")
    part.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    os.replace(part, p)


def rollcall_dates() -> dict:
    """vote_id -> ISO date, straight from Voteview. Used as the ONLY evidence
    that settles an ambiguous treaty identifier."""
    out = {}
    with VOTEVIEW.open(encoding="utf-8-sig", errors="replace",
                       newline="") as fh:
        for row in csv.DictReader(fh):
            ch = "S" if row["chamber"] == "Senate" else "H"
            vid = f"{ch}{int(row['congress']):03d}-{int(row['rollnumber']):04d}"
            out[vid] = row["date"]
    return out


def pull() -> int:
    key = get_key()
    if not key:
        print("  UNMEASURED: no CONGRESS_API_KEY in the environment or in "
              f"{ENVFILE}. Nothing was fetched and nothing is claimed about "
              "what the source holds.")
        return 1
    print("  API key loaded (value not logged).")
    if not take_hostlock(f"{STEM}.py"):
        return 2

    deadline = time.time() + RUN_DEADLINE_S
    dates = rollcall_dates()
    staged, n_req = [], 0
    try:
        # --- /bill targets: unambiguous, one request each ------------------
        for bid, cong, btype, num, why in BILL_TARGETS:
            path = f"/bill/{cong}/{btype}/{num}"
            body, status, shown = api_get(path, key, deadline)
            n_req += 1
            stage_raw(f"bill_{cong}_{btype}_{num}",
                      {"url": shown, "status": status, "body": body})
            title = ""
            if body:
                title = ((body.get("bill") or {}).get("title") or "").strip()
            staged.append({
                "cedar_bill_id": bid, "vote_id": "",
                "endpoint": f"bill/{cong}/{btype}/{num}", "url": shown,
                "http_status": status,
                "identifier_evidence": "type_slug_normalised: " + why,
                "accepted": "Y" if title else "N",
                "title_verbatim": title, "title_field": "bill.title",
                "reject_reason": "" if title else
                    f"no title on the response ({status})",
                "fetched_utc": datetime.now(timezone.utc).isoformat()})
            print(f"    {bid:22s} {status:12s} "
                  f"{'TITLE' if title else 'no title'}")

        # --- /treaty targets: candidates, settled by action date -----------
        for bid, vid, evid, cands, why in TREATY_TARGETS:
            vote_date = dates.get(vid, "")
            survivors = []
            for cong, num in cands:
                if cong < TREATY_COVERAGE_FROM:
                    staged.append({
                        "cedar_bill_id": bid, "vote_id": vid,
                        "endpoint": f"treaty/{cong}/{num}", "url": "",
                        "http_status": "not_requested",
                        "identifier_evidence": evid,
                        "accepted": "N", "title_verbatim": "",
                        "title_field": "",
                        "reject_reason": f"congress {cong} is below the API's "
                                         f"treaty coverage floor "
                                         f"({TREATY_COVERAGE_FROM}); no "
                                         f"request made",
                        "fetched_utc": ""})
                    continue
                body, status, shown = api_get(f"/treaty/{cong}/{num}", key,
                                              deadline)
                n_req += 1
                stage_raw(f"treaty_{cong}_{num}",
                          {"url": shown, "status": status, "body": body})
                # /treaty returns `treaty` as a LIST of one. `topic` on that
                # object is a CATEGORY ("Commercial"), not a title - the title
                # is the `Treaty - Short Title` entry in `titles`, and nothing
                # else is accepted as one.
                tl = (body or {}).get("treaty") or []
                t = tl[0] if isinstance(tl, list) and tl else (
                    tl if isinstance(tl, dict) else {})
                topic = ""
                for e in (t.get("titles") or []):
                    if (e.get("titleType") or "").strip() == (
                            "Treaty - Short Title"):
                        topic = (e.get("title") or "").strip()
                        break
                considered = t.get("congressConsidered")
                ok_date = ""
                if body and evid == "ambiguous_split":
                    ab, astatus, aurl = api_get(
                        f"/treaty/{cong}/{num}/actions", key, deadline)
                    n_req += 1
                    stage_raw(f"treaty_{cong}_{num}_actions",
                              {"url": aurl, "status": astatus, "body": ab})
                    acts = (ab or {}).get("actions") or []
                    hits = [a for a in acts
                            if (a.get("actionDate") or "")[:10] == vote_date]
                    ok_date = "Y" if hits else "N"
                    # Second, independent evidence: congress.gov records which
                    # Congress CONSIDERED the treaty. It must be the Congress
                    # the roll call sits in.
                    vote_cong = int(vid[1:4])
                    if considered != vote_cong:
                        ok_date = (f"N_congressConsidered={considered}"
                                   f"_vote={vote_cong}")
                elif body:
                    ok_date = "NOT_REQUIRED_identifier_quoted_in_question"
                accepted = bool(topic) and ok_date in (
                    "Y", "NOT_REQUIRED_identifier_quoted_in_question")
                if accepted:
                    survivors.append((cong, num, topic))
                staged.append({
                    "cedar_bill_id": bid, "vote_id": vid,
                    "endpoint": f"treaty/{cong}/{num}", "url": shown,
                    "http_status": status, "identifier_evidence": evid,
                    "accepted": "Y" if accepted else "N",
                    "title_verbatim": topic if accepted else "",
                    "title_field": ("treaty.titles[Treaty - Short Title]"
                                    if accepted else ""),
                    "reject_reason": "" if accepted else (
                        f"status={status}; congressConsidered={considered}; "
                        f"senate action on the roll-call date {vote_date}: "
                        f"{ok_date or 'n/a'}"),
                    "fetched_utc": datetime.now(timezone.utc).isoformat()})
                print(f"    {bid:22s} treaty/{cong}/{num:<4} {status:12s} "
                      f"date_match={ok_date or '-':6s} "
                      f"{'ACCEPT' if accepted else 'reject'}")
            if len(survivors) != 1:
                print(f"    {bid:22s} UNRESOLVED_AMBIGUOUS_IDENTIFIER: "
                      f"{len(survivors)} candidate(s) survived - REFUSING to "
                      f"pick one")
    finally:
        release_hostlock(f"1092 title residue: {n_req} GET(s), "
                         f"{TODAY}; host free")

    STAGE_CSV.parent.mkdir(parents=True, exist_ok=True)
    write_csv_atomic(STAGE_CSV, STAGE_FIELDS, staged)
    acc = [s for s in staged if s["accepted"] == "Y"]
    print(f"\n  requests {n_req}   staged rows {len(staged)}   "
          f"accepted titles {len(acc)} for "
          f"{len({s['cedar_bill_id'] for s in acc})} bill_id(s)")
    print(f"  raw       {STAGE_DIR}")
    print(f"  targets   {STAGE_CSV}")
    return 0


# ---------------------------------------------------------------------------
# the scope ruler, imported from the script that DEFINES it, not re-written
# ---------------------------------------------------------------------------
def load_scope_ruler():
    """Import build_scope_ruler() out of 14_build_bills_votes.py by path.

    Re-implementing it here would be a second definition of the rule the
    codebook documents, and the two would drift. If the import fails this
    returns None and the caller emits UNMEASURED rather than a scope.
    """
    import importlib.util
    src = HERE / "14_build_bills_votes.py"
    if not src.exists():
        return None, f"{src.name} not on disk"
    try:
        spec = importlib.util.spec_from_file_location("_m14", src)
        mod = importlib.util.module_from_spec(spec)
        # 14 runs pandas/spine work at import time only inside functions.
        spec.loader.exec_module(mod)
        return mod.build_scope_ruler(), ""
    except Exception as ex:                            # noqa: BLE001
        return None, f"{type(ex).__name__}: {ex}"


# ---------------------------------------------------------------------------
# WRITE
# ---------------------------------------------------------------------------
BASIS_1092_BILL = ("voteview_rollcall_only + congress_gov_bill_endpoint_title_"
                   "backfill (1092: bill_type slug normalised)")
BASIS_1092_TREATY = ("voteview_rollcall_only + congress_gov_treaty_endpoint_"
                     "topic (1092)")
#: Stamped into `record_basis` on every row whose scope this script rules.
#: There is no new column: `record_basis` IS this table's provenance string,
#: and the stamp is what lets `verify` re-derive exactly the rulings 1092 made
#: and no others. THE STAMP MATTERS because the spine has grown: the ruler
#: built 2026-09-02 carries 3,717 names where the 2026-08-05 build had far
#: fewer, so a ruling made today is not the ruling that build would have made.
#: A `no_specific_entity_matched` is vintage-safe in one direction - a SUBSET
#: spine cannot produce a match a SUPERSET spine did not - so only the
#: `tribe-specific` rulings are vintage-sensitive, and `write` names them.
SCOPE_STAMP = f"scope_ruled_1092_{TODAY}"


def staged_titles() -> dict:
    """cedar_bill_id -> (title, field, url). Accepted rows only, and a
    bill_id with more than one accepted row is dropped as unresolved."""
    if not STAGE_CSV.exists():
        return {}
    _, rows = read_csv(STAGE_CSV)
    by = {}
    for r in rows:
        if r["accepted"] != "Y" or not r["title_verbatim"].strip():
            continue
        by.setdefault(r["cedar_bill_id"], []).append(r)
    out = {}
    for bid, rs in by.items():
        if len(rs) != 1:
            print(f"  REFUSING {bid}: {len(rs)} accepted candidates in the "
                  f"staging file - ambiguous, nothing written")
            continue
        out[bid] = (rs[0]["title_verbatim"], rs[0]["title_field"],
                    rs[0]["url"], rs[0]["endpoint"])
    return out


def enrich(bills: list, titles: dict, rule) -> tuple:
    """Pure. Returns (rows, stats). `rule` may be None -> scope UNMEASURED."""
    out, stats = [], Counter()
    for b in bills:
        r = dict(b)
        bid = r["bill_id"]
        if bid in titles and not r["title"].strip():
            t, field, url, endpoint = titles[bid]
            r["title"] = t
            r["record_basis"] = (BASIS_1092_TREATY if field == "treaty.topic"
                                 else BASIS_1092_BILL)
            stats["title_filled"] += 1
        # Refresh the scope columns ONLY where a title exists and the basis is
        # one of the two UNRULED states - the stale `no_title_available` left
        # by the 2026-08-05 backfill (128 rows) or a blank left by
        # `73 --sweep` (32 rows). Never overwrite a real ruling.
        if (r["title"].strip()
                and r["bill_scope_basis"] in ("no_title_available", "")):
            if rule is None:
                r["bill_scope_basis"] = "UNMEASURED_scope_ruler_unavailable"
                stats["scope_unmeasured"] += 1
            else:
                scope, basis = rule(r["title"])
                r["bill_scope"], r["bill_scope_basis"] = scope, basis
                if SCOPE_STAMP not in r["record_basis"]:
                    r["record_basis"] = (r["record_basis"] + " + "
                                         + SCOPE_STAMP).strip(" +")
                stats["scope_refreshed"] += 1
                stats["scope_" + (scope or "blank")] += 1
        out.append(r)
    return out, stats


def scope_drift(rows: list, rule) -> list:
    """Rows RULED BEFORE 1092 whose ruling today's spine no longer
    reproduces. This is a MEASUREMENT, not a check: it is an upstream
    condition 1092 did not create and deliberately does not repair."""
    if rule is None:
        return []
    out = []
    for r in rows:
        b = r["bill_scope_basis"]
        if SCOPE_STAMP in r["record_basis"]:
            continue
        if not (b.startswith("spine_name_match:")
                or b.startswith("designator_pattern:")
                or b == "no_specific_entity_matched"):
            continue
        scope, basis = rule(r["title"])
        if (scope, basis) != (r["bill_scope"], b):
            out.append((r["bill_id"], r["bill_scope"], b, scope, basis))
    return out


# ---------------------------------------------------------------------------
# THE CHECKS. Each returns a list of failure strings; selftest proves each
# one FIRES on a synthetic violation.
# ---------------------------------------------------------------------------
def check_titles_verbatim(rows: list, titles: dict) -> list:
    """C1 - a title written here must be byte-equal to the staged source."""
    out = []
    idx = {r["bill_id"]: r for r in rows}
    for bid, (t, _f, _u, _e) in titles.items():
        r = idx.get(bid)
        if r is None:
            out.append(f"C1 {bid}: staged a title for a bill_id that is not "
                       f"in native_bills.csv")
        elif r["title"] != t:
            out.append(f"C1 {bid}: title on the row is not byte-equal to the "
                       f"staged source value - a title was edited or "
                       f"reconstructed")
    return out


def check_no_stale_scope(rows: list) -> list:
    """C2 - the defect this script exists to close must stay closed."""
    bad = [r["bill_id"] for r in rows
           if r["bill_scope_basis"] == "no_title_available"
           and r["title"].strip()]
    return ([f"C2 {len(bad)} row(s) say bill_scope_basis='no_title_available' "
             f"while carrying a title - the scope ruler has not been replayed "
             f"since the title arrived: {bad[:5]}"] if bad else [])


def check_scope_basis_agrees(rows: list, rule) -> list:
    """C3 - no invented scope. Every ruling THIS SCRIPT STAMPED must be
    reproducible from the title by the ruler that 14 defines.

    It is deliberately scoped to the stamped rows. 76 of the 2,901 rulings
    made on 2026-08-05 no longer reproduce under today's larger spine
    [measured 2026-09-02]; that is an upstream vintage difference, it is
    printed by `verify` as a measurement, and repairing it is an owner
    decision with a real blast radius - not something a check should force by
    failing red on work this script did not do."""
    if rule is None:
        return ["C3 UNMEASURED: the scope ruler could not be imported, so "
                "no ruling on this file was checked. This is not a pass."]
    out = []
    for r in rows:
        if SCOPE_STAMP not in r["record_basis"]:
            continue
        scope, basis = rule(r["title"])
        if (scope, basis) != (r["bill_scope"], r["bill_scope_basis"]):
            out.append(f"C3 {r['bill_id']}: row says ({r['bill_scope']!r}, "
                       f"{r['bill_scope_basis']!r}); the ruler on this title "
                       f"says ({scope!r}, {basis!r})")
    return out[:10] + ([f"C3 ... {len(out)-10} more"] if len(out) > 10 else [])


def check_titled_row_has_scope(rows: list) -> list:
    """C5 - a row with a title must carry a scope ruling. This is the
    invariant the 2026-08-05 backfill broke on 128 rows."""
    bad = [r["bill_id"] for r in rows
           if r["title"].strip() and not r["bill_scope"].strip()]
    return ([f"C5 {len(bad)} row(s) carry a title and a BLANK bill_scope - "
             f"the ruler has not been run on them: {bad[:5]}"]
            if bad else [])


def check_no_blank_title_without_reason(rows: list) -> list:
    """C4 - a blank title must still carry a stated reason."""
    bad = [r["bill_id"] for r in rows
           if not r["title"].strip() and not r["bill_scope_basis"].strip()]
    return ([f"C4 {len(bad)} row(s) have a blank title AND a blank "
             f"bill_scope_basis - a silence with no stated reason: "
             f"{bad[:5]}"] if bad else [])


def run_checks(rows: list, titles: dict, rule) -> list:
    return (check_titles_verbatim(rows, titles)
            + check_no_stale_scope(rows)
            + check_scope_basis_agrees(rows, rule)
            + check_no_blank_title_without_reason(rows)
            + check_titled_row_has_scope(rows))


# ---------------------------------------------------------------------------
def measure() -> int:
    fields, bills = read_csv(BILLS)
    n = len(bills)
    by_type = Counter()
    for b in bills:
        by_type[(b["bill_type"], bool(b["title"].strip()))] += 1
    print(f"\n  1092 measure   native_bills.csv  {measure_rows(BILLS):,} rows "
          f"(csv.reader), {len(fields)} columns\n")
    print("    bill_type      rows   with a title")
    types = sorted({t for t, _ in by_type})
    for t in types:
        tot = by_type[(t, True)] + by_type[(t, False)]
        print(f"    {t:12s} {tot:6d} {by_type[(t, True)]:14d}")
    blank = [b for b in bills if not b["title"].strip()]
    print(f"\n    titles blank on {len(blank)} of {n}")
    stale = [b for b in bills if b["bill_scope_basis"] == "no_title_available"
             and b["title"].strip()]
    print(f"    bill_scope_basis='no_title_available' WITH a title: "
          f"{len(stale)}  <- the ordering defect")
    print(f"    bill_scope blank: "
          f"{sum(1 for b in bills if not b['bill_scope'].strip())}")
    if STAGE_CSV.exists():
        _, s = read_csv(STAGE_CSV)
        print(f"\n    staging file present: {len(s)} candidate row(s), "
              f"{sum(1 for r in s if r['accepted'] == 'Y')} accepted")
    else:
        print(f"\n    staging file ABSENT - run `pull` first")
    return 0


def write() -> int:
    fields, bills = read_csv(BILLS)
    rows_in = measure_rows(BILLS)
    titles = staged_titles()
    rule, why = load_scope_ruler()
    if rule is None:
        print(f"  scope ruler UNAVAILABLE ({why}) - scope will be written as "
              f"UNMEASURED, not guessed")
    print(f"\n  1092 write   native_bills.csv  rows in {rows_in:,}   "
          f"columns {len(fields)}")
    print(f"               staged titles to apply: {len(titles)}")

    rows, stats = enrich(bills, titles, rule)
    fails = run_checks(rows, titles, rule)
    if fails:
        for f in fails:
            print("  FAIL " + f)
        raise SystemExit("1092 refuses to write: its own checks failed above.")

    bak = BILLS.with_suffix(BILLS.suffix + f".bak_{TODAY}_pre_{STEM}")
    if not bak.exists():
        bak.write_bytes(BILLS.read_bytes())
    write_csv_atomic(BILLS, fields, rows)
    rows_out = measure_rows(BILLS)
    print(f"  backup   {bak.name}")
    print(f"  rows     in {rows_in:,}  ->  out {rows_out:,}   "
          f"{'CONSERVED' if rows_in == rows_out else 'ROW LOSS - INVESTIGATE'}")
    if rows_in != rows_out:
        return 1
    print(f"  changes  {dict(stats)}")
    for b in rows:
        if b["bill_id"] in titles:
            print(f"    {b['bill_id']:22s} {b['bill_scope']:14s} "
                  f"{b['bill_scope_basis'][:34]:34s} {b['title'][:60]!r}")
    return 0


def verify() -> int:
    _, bills = read_csv(BILLS)
    titles = staged_titles()
    rule, why = load_scope_ruler()
    print(f"\n  1092 verify   {len(bills):,} rows")
    if rule is None:
        print(f"  UNMEASURED: scope ruler unavailable ({why})")
    fails = run_checks(bills, titles, rule)
    for f in fails:
        print("  FAIL " + f)
    if fails:
        return 1
    print(f"  titles blank: "
          f"{sum(1 for b in bills if not b['title'].strip())}")
    print(f"  bill_scope blank: "
          f"{sum(1 for b in bills if not b['bill_scope'].strip())}")
    print(f"  rows ruled by 1092: "
          f"{sum(1 for b in bills if SCOPE_STAMP in b['record_basis'])}")
    report_drift(bills, rule)
    print("  all checks pass")
    return 0


def report_drift(rows: list, rule) -> None:
    """FLAGGED, NOT FIXED. Rows ruled before 1092 whose ruling today's spine
    no longer reproduces - the spine gained names since 2026-08-05."""
    if rule is None:
        print("  UNMEASURED: scope drift not measured (ruler unavailable)")
        return
    d = scope_drift(rows, rule)
    n_checked = sum(1 for r in rows
                    if SCOPE_STAMP not in r["record_basis"]
                    and (r["bill_scope_basis"].startswith("spine_name_match:")
                         or r["bill_scope_basis"].startswith(
                             "designator_pattern:")
                         or r["bill_scope_basis"]
                         == "no_specific_entity_matched"))
    print(f"  PRE-1092 SCOPE DRIFT (flagged, not fixed): {len(d)} of "
          f"{n_checked} rulings made before this script no longer reproduce "
          f"under today's spine.")
    for bid, s0, b0, s1, b1 in d[:3]:
        print(f"    {bid:16s} on file ({s0!r}, {b0!r})  ->  today "
              f"({s1!r}, {b1!r})")
    if len(d) > 3:
        print(f"    ... {len(d)-3} more. Re-ruling them is an owner decision: "
              f"it moves the published tribe-specific count.")


def selftest() -> int:
    """Prove each check FIRES. A check that cannot fail is not a check."""
    import copy
    _, bills = read_csv(BILLS)
    titles = staged_titles()
    rule, _ = load_scope_ruler()
    if rule is None:
        print("  selftest cannot run: the scope ruler did not import, so C3 "
              "cannot be exercised. UNMEASURED, not a pass.")
        return 1
    base = run_checks(bills, titles, rule)
    if base:
        print("  selftest cannot run: the live data already fails a check:")
        for f in base:
            print("    " + f)
        return 1

    cases = []
    if titles:
        m = copy.deepcopy(bills)
        bid = next(iter(titles))
        tgt = next(r for r in m if r["bill_id"] == bid)
        tgt["title"] = tgt["title"].upper() + " (tidied)"
        cases.append((f"C1 verbatim title ({bid})",
                      check_titles_verbatim(m, titles)))
    else:
        cases.append(("C1 verbatim title", ["SKIPPED - no staged titles; "
                                            "run `pull` first"]))
    m = copy.deepcopy(bills)
    tgt = next(r for r in m if r["title"].strip())
    tgt["bill_scope_basis"] = "no_title_available"
    cases.append((f"C2 stale scope basis ({tgt['bill_id']})",
                  check_no_stale_scope(m)))

    m = copy.deepcopy(bills)
    tgt = next(r for r in m
               if r["bill_scope_basis"] == "no_specific_entity_matched")
    tgt["bill_scope"] = "tribe-specific"
    tgt["bill_scope_basis"] = "spine_name_match:Invented Nation"
    cases.append((f"C3 invented scope ruling ({tgt['bill_id']})",
                  check_scope_basis_agrees(m, rule)))

    # C4 - after this script runs there is no blank title left to mutate, so
    # the violation is SYNTHESISED: strip a title and its stated reason.
    m = copy.deepcopy(bills)
    tgt = next(r for r in m if SCOPE_STAMP not in r["record_basis"])
    tgt["title"], tgt["bill_scope_basis"] = "", ""
    cases.append((f"C4 silence with no reason ({tgt['bill_id']})",
                  check_no_blank_title_without_reason(m)))

    m = copy.deepcopy(bills)
    tgt = next(r for r in m if r["title"].strip() and r["bill_scope"].strip())
    tgt["bill_scope"] = ""
    cases.append((f"C5 titled row with no scope ({tgt['bill_id']})",
                  check_titled_row_has_scope(m)))

    print(f"\n  1092 selftest   {len(cases)} synthetic violations\n")
    ok = True
    for name, fired in cases:
        skipped = bool(fired) and str(fired[0]).startswith("SKIPPED")
        print(f"    {'SKIP  ' if skipped else ('FIRES ' if fired else 'SILENT')}"
              f"  {name}")
        if fired:
            print(f"              {str(fired[0])[:150]}")
        if not fired:
            ok = False
    print(f"\n  {'every check fires' if ok else 'A CHECK DID NOT FIRE'}")
    return 0 if ok else 1


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "measure"
    return {"measure": measure, "pull": pull, "write": write,
            "verify": verify, "selftest": selftest}.get(mode, measure)()


if __name__ == "__main__":
    sys.exit(main())
