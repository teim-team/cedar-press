#!/usr/bin/env python3
"""1132_fac_nontribal_native_audits.py -- Cedar asked the FAC the wrong question.

    py -3 code/1132_fac_nontribal_native_audits.py report    # the gap, no network
    py -3 code/1132_fac_nontribal_native_audits.py fetch     # the FAC bulk CSVs
    py -3 code/1132_fac_nontribal_native_audits.py apply     # match + write the tables
    py -3 code/1132_fac_nontribal_native_audits.py verify    # exits 1 when the work did NOT land
    py -3 code/1132_fac_nontribal_native_audits.py selftest  # proves verify FIRES

===========================================================================
THE DEFECT
===========================================================================
`code/147_build_fac_single_audits.py` discovers Single Audit filings with

    api.fac.gov/general?entity_type=eq.tribal

plus three `auditee_name ilike` nets for gaming. Measured on the live table
2026-09-02: 6,774 of 6,780 rows arrive on the `entity_type_tribal` net, and
the whole table reaches **638** of the 1,555 entities in
`data/spine/cedar_entity_spine.csv`.

The 917 it does not reach are not a random remainder. Counted by
`entity_class`:

    Native Hawaiian Organization                        210
    Alaska Native Village Corporation                   152
    Federally recognized Alaska Native Village          115
    BIE School                                          114
    State-recognized tribe                               63
    Native Community Development Financial Institution   55
    Individually Native-owned business                   45
    Intertribal Organization                             37
    Native Financial Institution                         29
    Urban Indian Organization                            28
    Federal-level self-governance consortium             22
    Federally recognized tribe                           19
    ... 8 smaller classes

**An NHO does not file a Single Audit as a tribe.** `entity_type` is the
auditee's own self-typing on the SF-SAC and its vocabulary is
tribal / higher-ed / non-profit / state / local / unknown. A Native Hawaiian
501(c)(3), a BIE-funded school, a Native CDFI and an ANCSA village corporation
each file, and each files as something other than `tribal`. The filter is a
statement about the FILER'S FORM, and Cedar was reading it as a statement about
WHO THE FILER IS.

So this is not a "more rows" pass. It is the same source asked a question that
can return the entities Cedar actually holds.

===========================================================================
WHY A SECOND TABLE AND NOT A WIDER 147
===========================================================================
`147 --all` is a FULL REBUILD of `data/clean/fac_tribal_single_audits.csv`.
Appending non-tribal rows into that file in place is reverted by the next 147
run, and it prints a larger row count while it happens - the FERC
rebuild/in-place collision in `START_HERE.md`, four times over.

So this script owns its own tables and 147 keeps owning its own. The two are
kept DISJOINT ON `report_id`, and `verify` exits 1 if a single report_id
appears in both. A row is 147's or it is 1132's; it is never both, and no
consumer can double-count a dollar across them.

`fac_tribal_single_audits.csv` is also named for what it holds. Loading 210
Native Hawaiian organisations into a file called "tribal" would be a
correctness defect wearing the costume of coverage.

===========================================================================
THE ROUTE, AND WHY IT IS NOT THE API
===========================================================================
Measured 2026-09-02 17:52 UTC, every path on `api.fac.gov` answered

    HTTP 404  "Requested route ('fac-production-postgrest.app.cloud.gov')
               does not exist."

with `X-Ratelimit-Remaining: 997`, i.e. the api.data.gov gateway accepted the
key and the FAC's own PostgREST backend was not routed. That is not a dead
endpoint and not a bad key. `www.fac.gov` states the cause in a banner:

    "Scheduled system maintenance. FAC.gov will be undergoing maintenance on
     Wednesday, September 2, 2026, between 9:00 AM and 4:00 PM EDT. During
     this period, the entire application may be unavailable."

`START_HERE.md` rule 3 in another vocabulary: a 404 is a state of the host,
never evidence that the path is wrong.

The route used instead is the FAC's **own published bulk export**, linked from
`https://www.fac.gov/data/download/current/` - a page whose `robots.txt` is
`User-agent: * / Disallow:` (nothing disallowed) and which documents these
files for exactly this use ("Using the data files in code ... import pandas").
The files carry the same columns as the API tables of the same name; the FAC
says so on that page. One GET per table replaces ~540 paginated API calls, so
it is also the politer of the two.

**The robots observation, recorded rather than skipped.** The files are served
from `app.fac.gov`, whose `robots.txt` is `Disallow: /`. That directive covers
the interactive Django application - audit search, submission, Login.gov - and
this script touches none of it: it fetches only the four static export objects
that `www.fac.gov` publishes for programmatic use, one request each, no
crawling, no link following, no search. Nothing here was refused: every fetch
below returned HTTP 200/206. If any of them ever returns 403, STOP - do not
re-route to the search UI.

===========================================================================
TIER DISCIPLINE - THE THING THAT MAKES THIS SAFE
===========================================================================
START_HERE §1: **a tier is INHERITED from the source row, never assigned by
the consumer**, and §1b: **a ruled method is not a positive ruling.** An EIN is
an exact key and says nothing about whether the LINK is right - 821 of the
1,104 EIN rows in the ledger are tier B via `need_v6`, which is 6.5% accurate.

So every match here carries the tier of the row that supplied the key:

    identifier match  -> tier of the ledger / np-hub row that holds it,
                         verbatim; never upgraded because the key was exact
    name match        -> 147's rule: containment is tier B, anything else A
    tier X source row -> REFUSED outright and written to the review file.
                         X is a NEGATIVE ruling; inheriting its authority
                         while dropping its sign is the 148 defect.

Two further refusals, both borrowed from 147 because they are already paid for:

  * **state disagreement.** FAC auditee_state vs spine state; a disagreement
    refuses the match (the Indian Pueblo Cultural Center NM -> HI failure).
  * **one key, two entities.** An EIN or UEI that reaches more than one of the
    917 resolves to none of them and is logged.

And one this pass had to add:

  * **no CONTAINMENT name match, at all.** This one was learned the expensive
    way inside this very script. The first `apply` run matched 1,126 filings
    and $243.32B, and the top of that table was:

        $29.64B  COMMONWEALTH OF VIRGINIA  -> Pribilof Islands
        $14.95B  STATE OF OKLAHOMA         -> Security State Bank of Oklahoma
        $ 1.13B  SAN BERNARDINO COUNTY     -> Riverside-San Bernardino County
                                              Indian Health, Inc.

    Every one is `resolve_entity`'s CONTAINMENT leg, which accepts a match when
    one distinctive-token core is a SUBSET of the other. `{state, oklahoma}` is
    a subset of `{security, state, bank, oklahoma}`, and a $14.95B state audit
    lands on a tribal bank. The Riverside/San Bernardino case is already in
    `START_HERE.md` as a refusal an owner made BY HAND, and it came straight
    back through a different door.

    A single-token guard did not stop any of them - each shares two or three
    tokens. So the rule is structural, not a threshold: **containment may name
    an owner; it may not key a dollar** (START_HERE §1). This table keys
    dollars on every row, so only `exact`, `core` (set equality) and `alias`
    are accepted, and the whole containment leg is refused and counted.

  * **no US state, ever.** No Cedar spine entity is a state government, so a
    FAC record whose `entity_type` is `state` cannot be one of ours by any
    route. Refused structurally rather than caught by a dollar threshold.

  * **`additional_eins` / `additional_ueis` do not bind a filing.** They say a
    reporting package COVERS a component unit with that identifier; the
    filing's `total_amount_expended` is still the whole auditee's. Binding on
    one attaches the Commonwealth of Virginia's $29.64B to a component. Only
    the filing's OWN `auditee_ein` / `auditee_uei` may bind it. The two files
    are still fetched and are still used, but only to REFUSE - a report whose
    additional identifiers reach a different Cedar entity than its primary key
    is logged as a disagreement rather than kept.

===========================================================================
WHAT A FILING IS WORTH AS EVIDENCE
===========================================================================
A Single Audit is an `audited_filing` - an independent evidence family, from
an auditor's opinion rather than from a spending system. It gives per year:

  * `total_amount_expended`  -- total federal awards expended, audited
  * auditee legal name, city, state, EIN, UEI as the auditee itself filed them
  * the whole SEFA: every ALN (CFDA) the auditee drew on, with dollars

It is independent of FPDS and of FSRS, so a corroboration from it is a real
second source in the sense `docs/ASSERTION_LAYER.md` means - not a
republication of a roster Cedar already holds.

===========================================================================
PII
===========================================================================
`general.csv` carries `auditee_email`, `auditee_phone`, `auditee_contact_name`,
`auditee_certify_name`, `auditor_email`, `auditor_phone`,
`auditor_contact_name` and street address lines. AGENT_FIELD_GUIDE §5: a
natural person's data held apart from their public role is CONSTRAINED. None
of those columns is written to any output here, and `verify` exits 1 if one
appears.

Reads   https://app.fac.gov/dissemination/public-data/gsa/full/{general,
          federal_awards,additional_eins,additional_ueis}.csv  (published at
          https://www.fac.gov/data/download/current/)
        data/spine/cedar_entity_spine.csv
        data/spine/cedar_identifier_ledger.csv          (READ ONLY - owned by
                                                         another workstream)
        data/clean/np_ein_entity_hub.csv
        data/clean/np_orgs.csv
        data/clean/bie_uio_identifier_links.csv
        data/clean/fac_tribal_single_audits.csv         (disjointness only)
Writes  data/raw/fac/bulk/*.csv                          (the export objects)
        data/clean/fac_native_nontribal_single_audits.csv
        data/clean/fac_native_nontribal_sefa_programs.csv
        data/clean/source_coverage_fac_nontribal.csv
        review/fac_nontribal_refused_matches.csv
        docs/fac_nontribal_native_audits.json
MINTS ZERO Cedar ids. Does not commit.
"""
from __future__ import annotations

import csv
import datetime as dt
import functools
import hashlib
import importlib.util
import json
import os
import re
import shutil
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

csv.field_size_limit(10 ** 8)

ROOT = Path(__file__).resolve().parent.parent
CODE = ROOT / "code"
CLEAN = ROOT / "data" / "clean"
SPINE = ROOT / "data" / "spine"
BULK = ROOT / "data" / "raw" / "fac" / "bulk"
REVIEW = ROOT / "review"
DOCS = ROOT / "docs"
LOGS = ROOT / "logs"
SCRIPT = "code/1132_fac_nontribal_native_audits.py"
TODAY = dt.date.today().isoformat()
NOW = dt.datetime.now(dt.timezone.utc).isoformat()

BULK_HOST = "app.fac.gov"
BULK_BASE = "https://app.fac.gov/dissemination/public-data/gsa/full/%s.csv"
BULK_PAGE = "https://www.fac.gov/data/download/current/"
UA = ("CedarPress-research/1.0 (+https://cedarpress.co; "
      "elijahsamsonmoreno@gmail.com)")
DISK_FLOOR_GB = 6.0

# The four export objects. `federal_awards` is 1.34 GB and is STREAMED and
# filtered to the matched report_ids rather than stored - one request, and the
# disk floor is never approached.
BULK_STORE = ["general", "additional_eins", "additional_ueis"]
BULK_STREAM = ["federal_awards"]

OUT_CENSUS = CLEAN / "fac_native_nontribal_single_audits.csv"
OUT_SEFA = CLEAN / "fac_native_nontribal_sefa_programs.csv"
OUT_COV = CLEAN / "source_coverage_fac_nontribal.csv"
OUT_REFUSED = REVIEW / "fac_nontribal_refused_matches.csv"
OUT_JSON = DOCS / "fac_nontribal_native_audits.json"

# Columns that may never be written. Checked by verify against the real
# headers of the real outputs, not against this list's own good intentions.
PII_COLS = {
    "auditee_email", "auditee_phone", "auditee_contact_name",
    "auditee_certify_name", "auditee_contact_title", "auditee_certify_title",
    "auditee_address_line_1", "auditor_email", "auditor_phone",
    "auditor_contact_name", "auditor_certify_name", "auditor_contact_title",
    "auditor_certify_title", "auditor_address_line_1",
}

# `verify` floors. A conservation check would pass on a no-op (AGENT_FIELD_GUIDE
# rule 5), so these assert the INTENDED delta instead. They are set BELOW the
# measured run (545 filings / 99 entities on 2026-09-02) so a real regression
# fails and normal source drift does not.
#
# They were 700/150 for one run, taken from the FIRST, DEFECTIVE apply - and
# `verify` duly went red when the containment refusal cut the table to its
# honest size. That is the floor doing its job in the direction nobody plans
# for, and it is the reason the numbers below were re-derived from a measured
# green run rather than from an expectation.
FLOOR_ENTITIES = 90
FLOOR_ROWS = 500


# --------------------------------------------------------------------------
def read_csv(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(p, rows, cols=None):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    cols = cols or (list(rows[0].keys()) if rows else [])
    tmp = p.with_suffix(p.suffix + ".part")
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, p)


def free_gb(path=ROOT):
    return shutil.disk_usage(str(path)).free / 1024 ** 3


def sha256(path, cap=None):
    h = hashlib.sha256()
    n = 0
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
            n += len(chunk)
            if cap and n >= cap:
                break
    return h.hexdigest()


# --------------------------------------------------------------------------
# host discipline -- PULL_DISCIPLINE.md, one poller per host
# --------------------------------------------------------------------------
def lock_path(host):
    return LOGS / ("_HOSTLOCK_%s.json" % host)


def pid_alive(pid):
    try:
        import subprocess
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-Process -Id %d -ErrorAction SilentlyContinue | "
             "Select-Object -ExpandProperty Id" % int(pid)],
            capture_output=True, text=True, timeout=30).stdout
        return str(int(pid)) in out
    except Exception:
        return False


def claim_host(host, purpose):
    LOGS.mkdir(parents=True, exist_ok=True)
    p = lock_path(host)
    cur = None
    if p.exists():
        try:
            cur = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            cur = None
    if cur and cur.get("active") and not cur.get("released"):
        holder = cur.get("pid")
        if holder and pid_alive(holder):
            cur.setdefault("queue", []).append(
                {"script": SCRIPT, "purpose": purpose, "queued_at": NOW})
            p.write_text(json.dumps(cur, indent=1), encoding="utf-8")
            print("  host busy, queued: %s" % host)
            return False
    p.write_text(json.dumps({
        "host": host, "pid": os.getpid(), "script": SCRIPT,
        "claimed_at": NOW, "active": True, "queue": [],
        "policy": "sequential, one poller, <=4 static export objects, "
                  ">=3s gap, stop on first refusal",
        "note": purpose}, indent=1), encoding="utf-8")
    return True


def release_host(host, note_text=""):
    p = lock_path(host)
    cur = {}
    if p.exists():
        try:
            cur = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            cur = {}
    cur.update({"host": host, "active": False, "released": NOW,
                "note": note_text})
    p.write_text(json.dumps(cur, indent=1), encoding="utf-8")


# --------------------------------------------------------------------------
# the gap
# --------------------------------------------------------------------------
def load_spine():
    return read_csv(SPINE / "cedar_entity_spine.csv")


def load_147_hits():
    """report_ids and entity_ids 147 already holds."""
    rows = read_csv(CLEAN / "fac_tribal_single_audits.csv")
    return ({r["report_id"] for r in rows if r.get("report_id")},
            {r["entity_id"] for r in rows if r.get("entity_id")},
            len(rows))


def the_917(spine, hit_entities):
    return [r for r in spine if r["tribe_id"] not in hit_entities]


def normalise_ein(s):
    d = re.sub(r"\D", "", s or "")
    return d.zfill(9) if 0 < len(d) <= 9 else ""


def normalise_uei(s):
    s = re.sub(r"[^A-Za-z0-9]", "", s or "").upper()
    return s if len(s) == 12 else ""


def gather_keys(target_ids):
    """Every EIN / UEI Cedar holds for one of the target entities, WITH the
    tier and method of the row that holds it. Nothing is upgraded and nothing
    is invented; a key with no tier on its source row is tier C.

    A key that reaches more than one target entity is dropped here and
    recorded - an ambiguous key may not name an owner.
    """
    keys = defaultdict(list)   # (kind, value) -> [dict]

    def add(kind, raw, ent, tier, method, source, url=""):
        v = normalise_ein(raw) if kind == "EIN" else normalise_uei(raw)
        if not v or ent not in target_ids:
            return
        keys[(kind, v)].append({
            "entity_id": ent, "tier": (tier or "C").strip().upper() or "C",
            "method": method or "", "source": source, "evidence_url": url})

    for r in read_csv(SPINE / "cedar_identifier_ledger.csv"):
        t = r.get("identifier_type")
        if t in ("EIN", "UEI"):
            add(t, r.get("identifier"), r.get("tribe_id"),
                r.get("confidence_tier"), r.get("attribution_method"),
                "data/spine/cedar_identifier_ledger.csv", r.get("evidence_url"))

    for r in read_csv(CLEAN / "np_ein_entity_hub.csv"):
        add("EIN", r.get("ein"), r.get("entity_id"), r.get("link_tier"),
            r.get("link_method"), "data/clean/np_ein_entity_hub.csv")

    for r in read_csv(CLEAN / "np_orgs.csv"):
        add("EIN", r.get("EIN"), r.get("entity_id"),
            r.get("confidence_tier") or r.get("tier"),
            "np_orgs_entity_link", "data/clean/np_orgs.csv")

    for r in read_csv(CLEAN / "bie_uio_identifier_links.csv"):
        add("EIN", r.get("ein"), r.get("tribe_id"), r.get("confidence_tier"),
            r.get("match_method"), "data/clean/bie_uio_identifier_links.csv")

    resolved, ambiguous, refused_x = {}, [], []
    for k, cands in keys.items():
        live = [c for c in cands if c["tier"] != "X"]
        if not live:
            refused_x.append((k, cands))
            continue
        ents = {c["entity_id"] for c in live}
        if len(ents) > 1:
            ambiguous.append((k, sorted(ents)))
            continue
        # best available tier for the one entity this key reaches
        order = {"A": 0, "B": 1, "C": 2}
        live.sort(key=lambda c: order.get(c["tier"], 3))
        resolved[k] = live[0]
    return resolved, ambiguous, refused_x


# --------------------------------------------------------------------------
# name resolution -- ONE resolver, 147's guards
# --------------------------------------------------------------------------
def load_resolver():
    spec = importlib.util.spec_from_file_location(
        "m33", str(CODE / "33_apply_party_rulings.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.norm = functools.lru_cache(maxsize=None)(m.norm)
    m.core = functools.lru_cache(maxsize=None)(m.core)
    return m


PROGRAM_SUFFIX = re.compile(
    r"\s*[-,]?\s*(department of tribal programs and admin\w*|"
    r"tribal programs? and admin\w*|"
    r"consolidated tribal government program|"
    r"office of the controller|finance department|"
    r"tribal government)\s*$", re.I)


# `resolve_entity` legs that may key a dollar. `containment` is deliberately
# absent - see the docstring; it produced $29.64B of Commonwealth of Virginia
# on the first run of this script.
NAME_METHODS_ALLOWED = {"exact", "core", "alias"}


def name_match(m33, name, state, subspine, by_id, cache):
    """-> (entity_id, how, tier, basis). ('' , ..) when refused."""
    key = (name or "").strip().upper() + "|" + (state or "").strip().upper()
    if key in cache:
        return cache[key]
    out = ("", "", "", "no_name")
    raw = (name or "").strip()
    if raw:
        tries = [(raw, "auditee_name")]
        stripped = PROGRAM_SUFFIX.sub("", raw).strip(" -,")
        if stripped and stripped.lower() != raw.lower():
            tries.append((stripped, "auditee_name_program_suffix_stripped"))
        for cand, how_in in tries:
            eid, ename, how = m33.resolve_entity(cand, subspine)
            if not eid:
                out = ("", "", "", "%s: %s" % (how_in, how))
                continue
            # THE CONTAINMENT REFUSAL. Not a threshold, a structural rule.
            if how not in NAME_METHODS_ALLOWED:
                out = ("", "", "",
                       "REFUSED_NAME_METHOD_MAY_NOT_KEY_A_DOLLAR: %s -> %s "
                       "via %s" % (cand[:60], ename, how))
                continue
            srow = by_id.get(eid) or {}
            sstate = (srow.get("state") or "").strip()
            st = (state or "").strip()
            if st and sstate and st != sstate:
                out = ("", "", "",
                       "REFUSED_STATE_DISAGREEMENT: fac=%s spine=%s via %s"
                       % (st, sstate, how))
                continue
            # AGENT_FIELD_GUIDE 11: one token of a multi-token hub name is not
            # a name. Kept on top of the containment refusal because `core`
            # equality on a one-token name is still one token.
            shared = m33.core(cand) & m33.core(srow.get("canonical_name", ""))
            if len(shared) < 2:
                out = ("", "", "",
                       "REFUSED_SINGLE_TOKEN_CORE: shared=%s via %s"
                       % ("|".join(sorted(shared)) or "-", how))
                continue
            out = (eid, how, "A", how_in)
            break
    cache[key] = out
    return out


# --------------------------------------------------------------------------
# fetch
# --------------------------------------------------------------------------
def stream_to(url, dest, session, gap=3.0):
    """One GET, streamed to disk, atomic rename. Returns (status, bytes)."""
    import requests
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    r = session.get(url, headers={"User-Agent": UA}, timeout=300, stream=True,
                    allow_redirects=True)
    if r.status_code >= 400:
        return r.status_code, 0
    n = 0
    with open(tmp, "wb") as f:
        for chunk in r.iter_content(1 << 20):
            if not chunk:
                continue
            f.write(chunk)
            n += len(chunk)
            if free_gb() < DISK_FLOOR_GB:
                r.close()
                tmp.unlink(missing_ok=True)
                raise SystemExit("STOP: free disk below %.1f GB" % DISK_FLOOR_GB)
    os.replace(tmp, dest)
    time.sleep(gap)
    return r.status_code, n


def cmd_fetch(force=False):
    import requests
    BULK.mkdir(parents=True, exist_ok=True)
    print("1132 fetch  free=%.1f GB" % free_gb())
    if not claim_host(BULK_HOST, "FAC published bulk export objects "
                                 "(general, additional_eins, additional_ueis)"):
        print("  another poller holds %s; deferring per PULL_DISCIPLINE."
              % BULK_HOST)
        return 1
    manifest = {}
    s = requests.Session()
    try:
        for name in BULK_STORE:
            dest = BULK / ("%s.csv" % name)
            if dest.exists() and not force:
                print("  %-18s cached %.1f MB" % (name, dest.stat().st_size / 1e6))
            else:
                url = BULK_BASE % name
                print("  GET %s" % url)
                st, n = stream_to(url, dest, s)
                if st >= 400:
                    print("  REFUSED HTTP %s on %s -- STOPPING, not re-routing."
                          % (st, name))
                    return 2
                print("  %-18s HTTP %s  %.1f MB" % (name, st, n / 1e6))
            manifest[name] = {
                "path": str(dest.relative_to(ROOT)).replace("\\", "/"),
                "bytes": dest.stat().st_size,
                "sha256_first_64MB": sha256(dest, cap=64 << 20),
                "url": BULK_BASE % name,
                "published_at": BULK_PAGE,
                "retrieved_at": NOW}
    finally:
        release_host(BULK_HOST, "FAC bulk export objects")
    (BULK / "_manifest.json").write_text(json.dumps(manifest, indent=1),
                                         encoding="utf-8")
    print("  manifest -> %s" % (BULK / "_manifest.json"))
    return 0


def stream_federal_awards(report_ids, session):
    """One GET of the 1.34 GB SEFA export, filtered to `report_ids` in flight.

    Nothing but the matched lines is ever written to disk.
    """
    import requests
    url = BULK_BASE % "federal_awards"
    print("  GET %s  (streamed, filtered to %d reports)"
          % (url, len(report_ids)))
    r = session.get(url, headers={"User-Agent": UA}, timeout=900, stream=True,
                    allow_redirects=True)
    if r.status_code >= 400:
        print("  REFUSED HTTP %s on federal_awards -- STOPPING." % r.status_code)
        return None, r.status_code
    r.encoding = "utf-8"
    kept, seen, mb = [], 0, 0
    it = r.iter_lines(chunk_size=1 << 20, decode_unicode=True)
    header = next(it)
    rdr = csv.reader([header])
    cols = next(rdr)
    buf = []
    for line in it:
        if line is None:
            continue
        buf.append(line)
        seen += 1
        if len(buf) >= 20000:
            for row in csv.reader(buf):
                if row and row[0] in report_ids:
                    kept.append(dict(zip(cols, row)))
            buf = []
            mb += 1
            if mb % 5 == 0:
                print("      %d SEFA lines scanned, %d kept" % (seen, len(kept)))
    for row in csv.reader(buf):
        if row and row[0] in report_ids:
            kept.append(dict(zip(cols, row)))
    print("      %d SEFA lines scanned, %d kept" % (seen, len(kept)))
    return kept, r.status_code


# --------------------------------------------------------------------------
# apply
# --------------------------------------------------------------------------
CENSUS_COLS = [
    "report_id", "audit_year", "auditee_name", "auditee_ein", "auditee_uei",
    "auditee_city", "auditee_state", "auditee_zip", "entity_type",
    "discovery_net", "match_key", "match_key_value",
    "entity_id", "entity_name", "entity_class",
    "entity_match_method", "entity_tier", "entity_match_basis",
    "entity_tier_inherited_from",
    "fy_start_date", "fy_end_date", "fac_accepted_date",
    "total_amount_expended", "auditor_firm_name", "auditor_ein",
    "gaap_results", "is_going_concern_included", "cognizant_agency",
    "oversight_agency", "is_public", "reporting_package_availability",
    "availability_basis", "source_authority", "source_url",
    "retrieved_at", "verbatim_quote", "measurement_type", "confidence_tier",
    "evidence_family", "built_by", "built_date",
]

SEFA_COLS = [
    "report_id", "award_reference", "audit_year", "entity_id", "entity_name",
    "entity_class", "aln", "federal_agency_prefix", "federal_award_extension",
    "federal_program_name", "amount_expended", "cluster_name",
    "federal_program_total", "is_major", "is_loan", "is_direct",
    "is_passthrough_award", "findings_count",
    "confidence_tier", "entity_match_method", "source_authority",
    "source_url", "retrieved_at", "evidence_family", "built_by", "built_date",
]

AVAIL_BASIS_PUB = ("the auditee did not elect to withhold; the reporting "
                   "package PDF is served by app.fac.gov")
AVAIL_BASIS_PRIV = (
    "2 CFR 200.512(b)(2): an Indian tribe or tribal organization may elect "
    "not to authorise the FAC to make the reporting package publicly "
    "available. The audit EXISTS and its SEFA is disseminated; the reporting "
    "package is not.")


def cmd_apply(no_sefa=False):
    t0 = time.time()
    gen_path = BULK / "general.csv"
    if not gen_path.exists():
        print("general.csv not present -- run `fetch` first.")
        return 2

    spine = load_spine()
    by_id = {r["tribe_id"]: r for r in spine}
    hit_reports, hit_entities, n147 = load_147_hits()
    targets = the_917(spine, hit_entities)
    target_ids = {r["tribe_id"] for r in targets}
    subspine = targets                      # the resolver sees ONLY the gap
    print("  spine %d; 147 reaches %d; target gap %d entities"
          % (len(spine), len(hit_entities), len(target_ids)))

    keys, ambiguous, refused_x = gather_keys(target_ids)
    n_ein = sum(1 for k in keys if k[0] == "EIN")
    n_uei = sum(1 for k in keys if k[0] == "UEI")
    print("  keys on the gap: %d EIN, %d UEI (%d ambiguous dropped, "
          "%d tier-X refused)" % (n_ein, n_uei, len(ambiguous), len(refused_x)))

    # additional EIN / UEI declared by the auditee on its own filing
    extra_ein = defaultdict(set)
    for r in read_csv(BULK / "additional_eins.csv"):
        v = normalise_ein(r.get("additional_ein"))
        if v:
            extra_ein[r["report_id"]].add(v)
    extra_uei = defaultdict(set)
    for r in read_csv(BULK / "additional_ueis.csv"):
        v = normalise_uei(r.get("additional_uei"))
        if v:
            extra_uei[r["report_id"]].add(v)
    print("  additional identifiers: %d reports with extra EINs, %d with "
          "extra UEIs" % (len(extra_ein), len(extra_uei)))

    m33 = load_resolver()
    ncache = {}
    census, refused = [], []
    net = Counter()
    scanned = 0

    with open(gen_path, encoding="utf-8-sig", newline="") as f:
        for g in csv.DictReader(f):
            scanned += 1
            rid = g.get("report_id") or ""
            if not rid or rid in hit_reports:
                continue                     # 147 owns it; stay disjoint

            # NO CEDAR ENTITY IS A US STATE. Structural, not a threshold.
            if (g.get("entity_type") or "").strip().lower() == "state":
                continue

            hits = []       # (net, key, value, entity_id, tier, method, src)
            e = normalise_ein(g.get("auditee_ein"))
            if e and ("EIN", e) in keys:
                k = keys[("EIN", e)]
                hits.append(("ein_exact", "EIN", e, k["entity_id"], k["tier"],
                             k["method"], k["source"]))
            u = normalise_uei(g.get("auditee_uei"))
            if u and ("UEI", u) in keys:
                k = keys[("UEI", u)]
                hits.append(("uei_exact", "UEI", u, k["entity_id"], k["tier"],
                             k["method"], k["source"]))

            # additional_eins / additional_ueis say the PACKAGE covers a
            # component unit; they do not make the auditee that component, and
            # `total_amount_expended` stays the whole auditee's. They are read
            # only to CONTRADICT, never to bind.
            covers = set()
            for v in extra_ein.get(rid, ()):
                if ("EIN", v) in keys:
                    covers.add(("additional_ein", v, keys[("EIN", v)]["entity_id"]))
            for v in extra_uei.get(rid, ()):
                if ("UEI", v) in keys:
                    covers.add(("additional_uei", v, keys[("UEI", v)]["entity_id"]))

            nm_id, nm_how, nm_tier, nm_basis = name_match(
                m33, g.get("auditee_name"), g.get("auditee_state"),
                subspine, by_id, ncache)
            if nm_id:
                hits.append(("auditee_name", "NAME", g.get("auditee_name"),
                             nm_id, nm_tier, nm_how, "code/33_apply_party_"
                             "rulings.py::resolve_entity"))

            if not hits:
                if covers:
                    refused.append({
                        "report_id": rid, "auditee_name": g.get("auditee_name"),
                        "auditee_state": g.get("auditee_state"),
                        "auditee_ein": g.get("auditee_ein"),
                        "entity_type": g.get("entity_type"),
                        "audit_year": g.get("audit_year"),
                        "reason": "COVERED_COMPONENT_ONLY_NOT_THE_AUDITEE",
                        "detail": "; ".join("%s=%s->%s" % c for c in
                                            sorted(covers))})
                continue

            ents = {h[3] for h in hits}
            if len(ents) > 1:
                refused.append({
                    "report_id": rid, "auditee_name": g.get("auditee_name"),
                    "auditee_state": g.get("auditee_state"),
                    "auditee_ein": g.get("auditee_ein"),
                    "entity_type": g.get("entity_type"),
                    "audit_year": g.get("audit_year"),
                    "reason": "KEYS_DISAGREE_ON_ENTITY",
                    "detail": "; ".join("%s->%s" % (h[0], h[3]) for h in hits)})
                continue

            # identifier before name; then best tier. The tier still comes
            # from the winning row -- never from the fact that a key was exact.
            rank = {"ein_exact": 0, "uei_exact": 1, "additional_ein_exact": 2,
                    "additional_uei_exact": 3, "auditee_name": 4}
            torder = {"A": 0, "B": 1, "C": 2}
            hits.sort(key=lambda h: (torder.get(h[4], 3), rank.get(h[0], 9)))
            netname, ktype, kval, eid, tier, method, src = hits[0]
            net[netname] += 1
            srow = by_id.get(eid) or {}
            # THE PUBLISHED EXPORT WRITES `t` / `f`, NOT `true` / `false`.
            # Measured over 200,000 rows of general.csv: 197,628 `t`, 2,374
            # `f`, and NOTHING ELSE. The first build of this table tested
            # `in ("true","1","yes","y")` and therefore recorded
            # `is_public = 0` on all 545 rows - every filing marked withheld
            # under 2 CFR 200.512(b)(2) when almost none of them is. Same
            # shape as `AMERICANTRIBAL GOVERNMENT` in START_HERE, where one
            # missing space drops 7,160 rows from an exact filter. V14 now
            # fails a table whose is_public is constant.
            pub = str(g.get("is_public", "")).strip().lower() in (
                "t", "true", "1", "yes", "y")
            census.append({
                "report_id": rid,
                "audit_year": g.get("audit_year"),
                "auditee_name": g.get("auditee_name"),
                "auditee_ein": g.get("auditee_ein"),
                "auditee_uei": g.get("auditee_uei"),
                "auditee_city": g.get("auditee_city"),
                "auditee_state": g.get("auditee_state"),
                "auditee_zip": g.get("auditee_zip"),
                "entity_type": g.get("entity_type"),
                "discovery_net": "|".join(sorted({h[0] for h in hits})),
                "match_key": ktype,
                "match_key_value": kval,
                "entity_id": eid,
                "entity_name": srow.get("canonical_name", ""),
                "entity_class": srow.get("entity_class", ""),
                "entity_match_method": method,
                "entity_tier": tier,
                "entity_match_basis": "%s via %s" % (netname, src),
                "entity_tier_inherited_from": src,
                "fy_start_date": g.get("fy_start_date"),
                "fy_end_date": g.get("fy_end_date"),
                "fac_accepted_date": g.get("fac_accepted_date"),
                "total_amount_expended": g.get("total_amount_expended"),
                "auditor_firm_name": g.get("auditor_firm_name"),
                "auditor_ein": g.get("auditor_ein"),
                "gaap_results": g.get("gaap_results"),
                "is_going_concern_included": g.get("is_going_concern_included"),
                "cognizant_agency": g.get("cognizant_agency"),
                "oversight_agency": g.get("oversight_agency"),
                "is_public": int(pub),
                "reporting_package_availability":
                    "PUBLISHES" if pub else "WITHHOLDS",
                "availability_basis": AVAIL_BASIS_PUB if pub
                                      else AVAIL_BASIS_PRIV,
                "source_authority": "Federal Audit Clearinghouse (GSA), "
                                    "published bulk export general.csv",
                "source_url": BULK_BASE % "general",
                "retrieved_at": TODAY,
                "verbatim_quote": (
                    "report_id=%s audit_year=%s auditee=%s entity_type=%s "
                    "is_public=%s total_amount_expended=%s"
                    % (rid, g.get("audit_year"), g.get("auditee_name"),
                       g.get("entity_type"), g.get("is_public"),
                       g.get("total_amount_expended"))),
                "measurement_type": "AUDITED_FEDERAL_EXPENDITURES",
                "confidence_tier": tier,
                "evidence_family": "audited_filing",
                "built_by": SCRIPT,
                "built_date": TODAY,
            })

    for k, ents in ambiguous:
        refused.append({"report_id": "", "auditee_name": "",
                        "auditee_state": "", "auditee_ein": "",
                        "entity_type": "", "audit_year": "",
                        "reason": "AMBIGUOUS_CEDAR_KEY_%s" % k[0],
                        "detail": "%s=%s reaches %s" % (k[0], k[1],
                                                        ",".join(ents))})
    for k, cands in refused_x:
        refused.append({"report_id": "", "auditee_name": "",
                        "auditee_state": "", "auditee_ein": "",
                        "entity_type": "", "audit_year": "",
                        "reason": "TIER_X_NEGATIVE_RULING",
                        "detail": "%s=%s is a REFUTATION on %s; not used as a "
                                  "key" % (k[0], k[1],
                                           ",".join(sorted({c["entity_id"]
                                                            for c in cands})))})

    ents = {c["entity_id"] for c in census}
    dollars = 0.0
    for c in census:
        try:
            dollars += float(c["total_amount_expended"] or 0)
        except ValueError:
            pass
    # Refusals the name net made, counted out of its own cache so they are a
    # measurement and not an intention.
    nrefuse = Counter()
    for v in ncache.values():
        if not v[0] and v[3].startswith("REFUSED_"):
            nrefuse[v[3].split(":")[0]] += 1
    for k, v in nrefuse.items():
        refused.append({"report_id": "", "auditee_name": "",
                        "auditee_state": "", "auditee_ein": "",
                        "entity_type": "", "audit_year": "",
                        "reason": k,
                        "detail": "%d distinct (auditee_name, state) pairs "
                                  "refused on this rule" % v})

    print("  scanned %d FAC general records in %.0fs" % (scanned, time.time() - t0))
    print("  MATCHED %d filings on %d entities Cedar could not previously "
          "reach" % (len(census), len(ents)))
    print("  audited federal expenditures on those filings: $%s"
          % format(dollars, ",.2f"))
    print("  nets: %s" % dict(net))
    print("  name-net refusals (distinct name/state pairs): %s" % dict(nrefuse))
    # AGENT_FIELD_GUIDE rule 3: print worked rows. The top of this table by
    # dollars is where the first run's containment defect was visible, and it
    # was invisible in every summary count.
    print("  --- the 12 largest matched filings, so a bad match is seen ---")
    for c in sorted(census, key=lambda x: -float(x["total_amount_expended"] or 0))[:12]:
        print("   %16s %-4s %-40s -> %-32s %s/%s"
              % (format(float(c["total_amount_expended"] or 0), ",.0f"),
                 c["audit_year"], (c["auditee_name"] or "")[:40],
                 (c["entity_name"] or "")[:32], c["entity_tier"],
                 c["entity_match_method"]))

    write_csv(OUT_CENSUS, census, CENSUS_COLS)
    write_csv(OUT_REFUSED, refused,
              ["report_id", "auditee_name", "auditee_state", "auditee_ein",
               "entity_type", "audit_year", "reason", "detail"])

    # ---- SEFA ------------------------------------------------------------
    sefa_rows = []
    sefa_status = "SKIPPED"
    if census and not no_sefa:
        import requests
        if claim_host(BULK_HOST, "FAC federal_awards export, streamed and "
                                 "filtered to matched reports"):
            try:
                s = requests.Session()
                got, st = stream_federal_awards({c["report_id"] for c in census}, s)
                sefa_status = "HTTP %s" % st
            finally:
                release_host(BULK_HOST, "federal_awards stream")
            if got is not None:
                byrep = {c["report_id"]: c for c in census}
                for a in got:
                    c = byrep.get(a.get("report_id"))
                    if not c:
                        continue
                    pfx = (a.get("federal_agency_prefix") or "").strip()
                    ext = (a.get("federal_award_extension") or "").strip()
                    sefa_rows.append({
                        "report_id": a.get("report_id"),
                        "award_reference": a.get("award_reference"),
                        "audit_year": a.get("audit_year"),
                        "entity_id": c["entity_id"],
                        "entity_name": c["entity_name"],
                        "entity_class": c["entity_class"],
                        "aln": ("%s.%s" % (pfx, ext)) if pfx and ext else "",
                        "federal_agency_prefix": pfx,
                        "federal_award_extension": ext,
                        "federal_program_name": a.get("federal_program_name"),
                        "amount_expended": a.get("amount_expended"),
                        "cluster_name": a.get("cluster_name"),
                        "federal_program_total": a.get("federal_program_total"),
                        "is_major": a.get("is_major"),
                        "is_loan": a.get("is_loan"),
                        "is_direct": a.get("is_direct"),
                        "is_passthrough_award": a.get("is_passthrough_award"),
                        "findings_count": a.get("findings_count"),
                        "confidence_tier": c["entity_tier"],
                        "entity_match_method": c["entity_match_method"],
                        "source_authority": "Federal Audit Clearinghouse "
                                            "(GSA), published bulk export "
                                            "federal_awards.csv",
                        "source_url": BULK_BASE % "federal_awards",
                        "retrieved_at": TODAY,
                        "evidence_family": "audited_filing",
                        "built_by": SCRIPT,
                        "built_date": TODAY})
    write_csv(OUT_SEFA, sefa_rows, SEFA_COLS)
    sefa_usd = 0.0
    for r in sefa_rows:
        try:
            sefa_usd += float(r["amount_expended"] or 0)
        except ValueError:
            pass
    print("  SEFA lines %d on %d ALNs, $%s (%s)"
          % (len(sefa_rows), len({r["aln"] for r in sefa_rows if r["aln"]}),
             format(sefa_usd, ",.2f"), sefa_status))

    # ---- coverage --------------------------------------------------------
    cls = Counter(c["entity_class"] for c in census)
    cov = [
        {"source": "Federal Audit Clearinghouse", "host": "app.fac.gov",
         "facet": "general record for a Native entity that does NOT file as "
                  "entity_type=tribal",
         "status": "PUBLISHES", "n": len(census),
         "evidence": "147 filters entity_type=eq.tribal and reaches %d of "
                     "%d spine entities. Re-asked without that filter, keyed "
                     "on EIN/UEI/name, the same source answers for %d further "
                     "entities across %d filings, $%s audited federal "
                     "expenditures."
                     % (len(hit_entities), len(spine), len(ents), len(census),
                        format(dollars, ",.0f")),
         "retrieved_at": TODAY, "source_url": BULK_PAGE},
        {"source": "Federal Audit Clearinghouse", "host": "app.fac.gov",
         "facet": "SEFA line items (federal_awards) for those filings",
         "status": "PUBLISHES", "n": len(sefa_rows),
         "evidence": "%d SEFA lines, %d distinct ALNs, $%s expended."
                     % (len(sefa_rows),
                        len({r["aln"] for r in sefa_rows if r["aln"]}),
                        format(sefa_usd, ",.0f")),
         "retrieved_at": TODAY, "source_url": BULK_BASE % "federal_awards"},
        {"source": "Federal Audit Clearinghouse", "host": "api.fac.gov",
         "facet": "dissemination API (the route 147 uses)",
         "status": "MEASURED", "n": 0,
         "evidence": "HTTP 404 'Requested route "
                     "(fac-production-postgrest.app.cloud.gov) does not exist' "
                     "on every path at 2026-09-02T17:52Z, with "
                     "X-Ratelimit-Remaining 997. www.fac.gov states scheduled "
                     "maintenance 09:00-16:00 EDT that day. The 404 is a state "
                     "of the host, not of the path.",
         "retrieved_at": TODAY, "source_url": "https://api.fac.gov/general"},
    ]
    for k, v in cls.most_common():
        cov.append({
            "source": "Federal Audit Clearinghouse", "host": "app.fac.gov",
            "facet": "filings reached for entity_class = %s" % (k or "(blank)"),
            "status": "PUBLISHES", "n": v,
            "evidence": "%d filings on %d entities of this class."
                        % (v, len({c["entity_id"] for c in census
                                   if c["entity_class"] == k})),
            "retrieved_at": TODAY, "source_url": BULK_PAGE})
    write_csv(OUT_COV, cov,
              ["source", "host", "facet", "status", "n", "evidence",
               "retrieved_at", "source_url"])

    OUT_JSON.write_text(json.dumps({
        "built_by": SCRIPT, "built_date": TODAY, "measured_at": NOW,
        "spine_entities": len(spine),
        "entities_147_reaches": len(hit_entities),
        "gap_entities": len(target_ids),
        "gap_by_class": dict(Counter(r["entity_class"] for r in targets)
                             .most_common()),
        "fac_general_records_scanned": scanned,
        "filings_matched": len(census),
        "entities_reached": len(ents),
        # NAMED FOR WHAT IT COUNTS. This is FILINGS per class, and it sums
        # to `filings_matched`; the per-class ENTITY count is the line below
        # it. The first draft called this `entities_reached_by_class` and its
        # values summed to 545, which is the filing count.
        "filings_by_entity_class": dict(cls.most_common()),
        "entities_by_entity_class": {
            k: len({c["entity_id"] for c in census if c["entity_class"] == k})
            for k, _ in cls.most_common()},
        "is_public": dict(Counter(c["is_public"] for c in census)),
        "audit_years": ["%s" % min(c["audit_year"] for c in census),
                        "%s" % max(c["audit_year"] for c in census)],
        "audited_federal_expenditures_usd": round(dollars, 2),
        "sefa_rows": len(sefa_rows),
        "sefa_distinct_aln": len({r["aln"] for r in sefa_rows if r["aln"]}),
        "sefa_amount_expended_usd": round(sefa_usd, 2),
        "tier": dict(Counter(c["entity_tier"] for c in census)),
        "nets": dict(net),
        "refused": dict(Counter(r["reason"] for r in refused)),
        "disjoint_from_147": True,
        "fac_tribal_rows_147": n147,
    }, indent=1), encoding="utf-8")
    print("  wrote %s" % OUT_JSON)
    return 0


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------
def cmd_report():
    spine = load_spine()
    hit_reports, hit_entities, n147 = load_147_hits()
    targets = the_917(spine, hit_entities)
    target_ids = {r["tribe_id"] for r in targets}
    print("=== 1132 REPORT (no network) ===")
    print("  spine entities                 %6d" % len(spine))
    print("  147 rows                       %6d" % n147)
    print("  entities 147 reaches           %6d" % len(hit_entities))
    print("  entities 147 MISSES            %6d" % len(target_ids))
    for k, v in Counter(r["entity_class"] for r in targets).most_common():
        print("      %-52s %5d" % (k, v))
    keys, ambiguous, refused_x = gather_keys(target_ids)
    ein_ents = {v["entity_id"] for k, v in keys.items() if k[0] == "EIN"}
    uei_ents = {v["entity_id"] for k, v in keys.items() if k[0] == "UEI"}
    print("  Cedar keys usable on the gap:")
    print("      EIN  %4d keys on %4d entities" % (
        sum(1 for k in keys if k[0] == "EIN"), len(ein_ents)))
    print("      UEI  %4d keys on %4d entities" % (
        sum(1 for k in keys if k[0] == "UEI"), len(uei_ents)))
    print("      entities with NO identifier key: %d (name is the only net)"
          % len(target_ids - ein_ents - uei_ents))
    print("      ambiguous keys dropped %d; tier-X keys refused %d"
          % (len(ambiguous), len(refused_x)))
    g = BULK / "general.csv"
    print("  bulk general.csv on disk: %s"
          % ("%.0f MB" % (g.stat().st_size / 1e6) if g.exists() else "NO"))
    return 0


# --------------------------------------------------------------------------
# verify -- must FAIL when the work did not land
# --------------------------------------------------------------------------
def _verify(quiet=False):
    """-> (ok, [failures], [notes])"""
    fail, note = [], []
    census = read_csv(OUT_CENSUS)
    sefa = read_csv(OUT_SEFA)

    # 1. the work landed at all
    if not census:
        fail.append("V1 census table absent or empty -- nothing landed")
        return False, fail, note
    ents = {c["entity_id"] for c in census if c.get("entity_id")}
    if len(census) < FLOOR_ROWS:
        fail.append("V1 filings %d < floor %d" % (len(census), FLOOR_ROWS))
    if len(ents) < FLOOR_ENTITIES:
        fail.append("V2 entities reached %d < floor %d"
                    % (len(ents), FLOOR_ENTITIES))
    note.append("V1/V2 %d filings on %d entities" % (len(census), len(ents)))

    # 2. every entity reached is one 147 could NOT reach. If this fails the
    #    pass measured 147's own coverage back to itself.
    _, hit_entities, _ = load_147_hits()
    overlap = ents & hit_entities
    if overlap:
        fail.append("V3 %d entities also reached by 147 -- not net-new: %s"
                    % (len(overlap), sorted(overlap)[:5]))
    else:
        note.append("V3 0 of %d entities overlap 147" % len(ents))

    # 3. report_id disjointness -- no dollar can be counted twice
    hit_reports, _, _ = load_147_hits()
    dup = {c["report_id"] for c in census} & hit_reports
    if dup:
        fail.append("V4 %d report_ids appear in BOTH tables: %s"
                    % (len(dup), sorted(dup)[:3]))
    else:
        note.append("V4 report_id disjoint from 147")

    # 4. every entity_id exists in the spine
    spine_ids = {r["tribe_id"] for r in load_spine()}
    orphan = ents - spine_ids
    if orphan:
        fail.append("V5 %d entity_ids not in the spine: %s"
                    % (len(orphan), sorted(orphan)[:3]))

    # 5. no tier invented, no tier X published
    tiers = Counter(c["entity_tier"] for c in census)
    if tiers.get("X"):
        fail.append("V6 %d rows published at tier X (a NEGATIVE ruling)"
                    % tiers["X"])
    bad = [c for c in census if c["entity_tier"] not in ("A", "B", "C")]
    if bad:
        fail.append("V6 %d rows carry a tier outside A/B/C" % len(bad))
    blank_basis = [c for c in census if not c.get("entity_tier_inherited_from")]
    if blank_basis:
        fail.append("V7 %d rows do not name where their tier came from"
                    % len(blank_basis))
    note.append("V6/V7 tiers %s, every row names its tier source" % dict(tiers))

    # 6. PII
    for path in (OUT_CENSUS, OUT_SEFA, OUT_COV):
        if not Path(path).exists():
            continue
        with open(path, encoding="utf-8-sig", newline="") as f:
            hdr = next(csv.reader(f), [])
        leak = PII_COLS & set(hdr)
        if leak:
            fail.append("V8 %s carries PII column(s) %s"
                        % (Path(path).name, sorted(leak)))
    note.append("V8 no PII column in any output")

    # 7. dollars are present and non-zero -- a match with no money is a match
    #    that did not read the filing
    usd = 0.0
    for c in census:
        try:
            usd += float(c["total_amount_expended"] or 0)
        except ValueError:
            pass
    if usd <= 0:
        fail.append("V9 total audited federal expenditures is $0")
    note.append("V9 $%s audited federal expenditures" % format(usd, ",.2f"))

    # 7b. THE THREE RULES THE FIRST RUN OF THIS SCRIPT BROKE. Each is a named
    #     invariant because each cost a nine-figure false attribution.
    #     V11 tests the NET, not the method string. AGENT_FIELD_GUIDE §14:
    #     `containment` is ALSO a value of `attribution_method` on 19 ledger
    #     rows, and those rows are keyed by an EXACT EIN here. One word, two
    #     bindings - testing the string alone failed 19 correct rows.
    cont = [c for c in census
            if "auditee_name" in (c["discovery_net"] or "")
            and c["entity_match_method"] not in ("exact", "core", "alias")]
    if cont:
        fail.append("V11 %d rows keyed a dollar on a NAME match that is not "
                    "exact/core/alias (e.g. %s -> %s via %s)"
                    % (len(cont), cont[0]["auditee_name"],
                       cont[0]["entity_name"], cont[0]["entity_match_method"]))
    else:
        note.append("V11 0 name matches outside exact/core/alias")
    st = [c for c in census
          if (c["entity_type"] or "").strip().lower() == "state"]
    if st:
        fail.append("V12 %d rows attribute a US STATE's Single Audit to a "
                    "Cedar entity (e.g. %s)" % (len(st), st[0]["auditee_name"]))
    else:
        note.append("V12 0 state-typed auditees")
    add = [c for c in census if "additional_" in (c["discovery_net"] or "")]
    if add:
        fail.append("V13 %d rows bound on an additional_ein/uei, which names a "
                    "COVERED COMPONENT and not the auditee" % len(add))
    else:
        note.append("V13 0 rows bound on a covered-component identifier")

    # 7c. is_public must not be CONSTANT. The published export writes `t`/`f`
    #     and a `true`/`false` test silently marks every filing withheld.
    pubvals = Counter(c["is_public"] for c in census)
    if len(pubvals) < 2:
        fail.append("V14 is_public is constant (%s) across all %d rows. The "
                    "FAC export writes `t`/`f`; a true/false test reads every "
                    "filing as withheld." % (dict(pubvals), len(census)))
    else:
        note.append("V14 is_public %s" % dict(pubvals))

    # 8. SEFA, when present, points only at census reports and carries ALNs
    if sefa:
        rid = {c["report_id"] for c in census}
        stray = {r["report_id"] for r in sefa} - rid
        if stray:
            fail.append("V10 %d SEFA rows reference a report not in the census"
                        % len(stray))
        if not {r["aln"] for r in sefa if r["aln"]}:
            fail.append("V10 SEFA rows carry no ALN")
        note.append("V10 %d SEFA lines, %d ALNs"
                    % (len(sefa), len({r["aln"] for r in sefa if r["aln"]})))
    else:
        note.append("V10 SEFA table empty -- UNMEASURED, not clean")

    return (not fail), fail, note


def cmd_verify():
    ok, fail, note = _verify()
    print("=== 1132 VERIFY ===")
    for n in note:
        print("  ok   %s" % n)
    for f in fail:
        print("  FAIL %s" % f)
    print("  %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def cmd_selftest():
    """Prove verify FIRES. Inject each violation, assert exit 1 AND that the
    NAMED invariant is the one that fired, restore, assert exit 0.
    """
    if not OUT_CENSUS.exists():
        print("selftest needs a built census -- run apply first.")
        return 2
    ok, fail, _ = _verify()
    if not ok:
        print("selftest refuses to run on a RED baseline: %s" % fail)
        return 2
    rows = read_csv(OUT_CENSUS)
    bak = OUT_CENSUS.with_suffix(".csv.selftest_bak")
    shutil.copy2(OUT_CENSUS, bak)
    results = []
    try:
        # V1: empty table
        write_csv(OUT_CENSUS, [], CENSUS_COLS)
        ok1, f1, _ = _verify()
        results.append(("V1 empty table", not ok1,
                        any(x.startswith("V1") for x in f1)))

        # V3: an entity 147 already reaches
        _, hit_entities, _ = load_147_hits()
        poisoned = [dict(r) for r in rows]
        poisoned[0]["entity_id"] = sorted(hit_entities)[0]
        write_csv(OUT_CENSUS, poisoned, CENSUS_COLS)
        ok3, f3, _ = _verify()
        results.append(("V3 non-net-new entity", not ok3,
                        any(x.startswith("V3") for x in f3)))

        # V6: a tier X row
        poisoned = [dict(r) for r in rows]
        poisoned[0]["entity_tier"] = "X"
        write_csv(OUT_CENSUS, poisoned, CENSUS_COLS)
        ok6, f6, _ = _verify()
        results.append(("V6 tier X published", not ok6,
                        any(x.startswith("V6") for x in f6)))

        # V8: a PII column
        cols = CENSUS_COLS + ["auditee_email"]
        poisoned = [dict(r, auditee_email="x@y.z") for r in rows]
        write_csv(OUT_CENSUS, poisoned, cols)
        ok8, f8, _ = _verify()
        results.append(("V8 PII column", not ok8,
                        any(x.startswith("V8") for x in f8)))

        # V9: no dollars
        poisoned = [dict(r, total_amount_expended="0") for r in rows]
        write_csv(OUT_CENSUS, poisoned, CENSUS_COLS)
        ok9, f9, _ = _verify()
        results.append(("V9 zero dollars", not ok9,
                        any(x.startswith("V9") for x in f9)))

        # V11: a containment match back in the table
        poisoned = [dict(r) for r in rows]
        poisoned[0]["entity_match_method"] = "containment"
        write_csv(OUT_CENSUS, poisoned, CENSUS_COLS)
        ok11, f11, _ = _verify()
        results.append(("V11 containment match", not ok11,
                        any(x.startswith("V11") for x in f11)))

        # V12: a US state auditee
        poisoned = [dict(r) for r in rows]
        poisoned[0]["entity_type"] = "state"
        write_csv(OUT_CENSUS, poisoned, CENSUS_COLS)
        ok12, f12, _ = _verify()
        results.append(("V12 state auditee", not ok12,
                        any(x.startswith("V12") for x in f12)))

        # V13: a covered-component identifier binding a filing
        poisoned = [dict(r) for r in rows]
        poisoned[0]["discovery_net"] = "additional_uei_exact"
        write_csv(OUT_CENSUS, poisoned, CENSUS_COLS)
        ok13, f13, _ = _verify()
        results.append(("V13 additional_* binding", not ok13,
                        any(x.startswith("V13") for x in f13)))

        # V14: every filing marked withheld (the t/f vocabulary defect)
        poisoned = [dict(r, is_public="0") for r in rows]
        write_csv(OUT_CENSUS, poisoned, CENSUS_COLS)
        ok14, f14, _ = _verify()
        results.append(("V14 is_public constant", not ok14,
                        any(x.startswith("V14") for x in f14)))
    finally:
        shutil.copy2(bak, OUT_CENSUS)
        bak.unlink(missing_ok=True)

    okr, fr, _ = _verify()
    print("=== 1132 SELFTEST ===")
    bad = 0
    for name, fired, named in results:
        print("  %-26s fired=%s named_invariant=%s"
              % (name, fired, named))
        if not (fired and named):
            bad += 1
    print("  restored baseline green: %s" % okr)
    if not okr:
        bad += 1
    print("  %s" % ("PASS" if bad == 0 else "FAIL (%d)" % bad))
    return 0 if bad == 0 else 1


# --------------------------------------------------------------------------
def main():
    args = sys.argv[1:]
    cmd = args[0] if args else "report"
    if cmd == "report":
        return cmd_report()
    if cmd == "fetch":
        return cmd_fetch(force="--force" in args)
    if cmd == "apply":
        return cmd_apply(no_sefa="--no-sefa" in args)
    if cmd == "verify":
        return cmd_verify()
    if cmd == "selftest":
        return cmd_selftest()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
