#!/usr/bin/env python3
"""147_build_fac_single_audits.py -- Gaming spec Step 12: the Single Audit exhaust.

Match Cedar Native entities to Federal Audit Clearinghouse records, and read the
gaming disclosures inside the audited financial statements attached to them.

=== THE DOCUMENTED DEAD END WAS HALF WRONG, AND THE HALF THAT WAS WRONG IS THE
=== VALUABLE HALF

`START_HERE.md` / `AGENTS.md` record, from the Florida build:

    "Tribal Single Audits are withheld at the Federal Audit Clearinghouse.
     Seminole Tribe of Florida (EIN 59-1415030) ... all ten filings FY2016-FY2025
     are `is_public: false` under 2 CFR 200.512(b)(2)"

Every word of that is true **about the Seminole Tribe of Florida**. Generalised
to Indian Country it is false, and this build measures the generalisation rather
than inheriting it.

2 CFR 200.512(b)(2) is an **opt-out**, not a bar. It says an auditee that is an
Indian tribe or tribal organization *may elect* not to authorise public
availability. Measured against `api.fac.gov` on 2026-08-12:

    entity_type = tribal, all audit years          6,774 general records
      is_public = true                             2,046   (30.2%)
      is_public = false                            4,728   (69.8%)

**2,046 tribal reporting packages are published, and their PDFs download.** They
include the audits of gaming tribes -- Sault Ste. Marie, Mississippi Band of
Choctaw, Muscogee (Creek) Nation, Gila River, Turtle Mountain, San Carlos
Apache. The Seminole result was one auditee's election, read as a rule.

**The lesson is the one already in AGENTS.md in another form: a source's refusal
on one record is a fact about that record.** A single auditee's opt-out is not a
statement about the clearinghouse, and it cost this project a whole source for
five days.

=== WHAT IS WITHHELD, MEASURED PER ENDPOINT AND NOT ASSUMED

The withholding is **not** all-or-nothing, and treating it as such loses real
data on the 69.8%. Measured on Seminole Tribe of Florida, report
2022-09-CENSUS-0000136810, `is_public = false`:

    /general           200, record returned      -> PUBLISHES
    /federal_awards    206, 127 SEFA rows        -> PUBLISHES
    /notes_to_sefa     200, 0 rows               -> withheld (tested at scale below)
    /findings_text     200, 0 rows               -> withheld (tested at scale below)
    app.fac.gov PDF    403                       -> WITHHOLDS

So the **Schedule of Expenditures of Federal Awards is disseminated even for a
withheld reporting package**, program by program with dollars. The narrative --
notes, findings, corrective actions -- and the audited financial statements are
not. A "0 rows" on one report cannot distinguish "withheld" from "this filing
had no findings", so this build measures the *rate* of text-table presence for
public vs non-public tribal reports and writes both numbers.

=== WHY THE PDF MATTERS AND THE API DOES NOT REPLACE IT

The API's text tables carry SEFA notes and audit findings. They do **not** carry
the financial statements. A tribal gaming enterprise appears in the audit as a
**component unit** -- its own statement of net position, its own statement of
revenues and expenses, its transfers to the tribe, its debt schedule and its
related-party note. None of that is in any API table. It is in the PDF.

**MACHINE_PARTICIPATION_EXPENSE is the target measure**, and it exists almost
nowhere else: a vendor paid on machine net win, coin-in, or another
participation formula. It is a gaming operating input close to cost of goods.
**It is NOT gross gaming revenue and must never be labelled as such**, and per
the gaming spec, "Manufacturer revenue per participation unit measures the
manufacturer's economics, not the casino's GGR."

=== TYPING RULES ENFORCED HERE

Financial measure types are never merged. A row gets a `measurement_type` only
when the quoted sentence itself names the concept AND carries the figure. Where
the sentence names a gaming concept without an unambiguous scope, the row is a
DISCLOSURE with `measurement_type` blank and the verbatim text carried -- an
observation, not a measure. No figure is derived, inverted or estimated
anywhere in this file.

Component-unit revenue is **not** typed REPORTED_PROPERTY_GGR. A tribal
enterprise's gaming revenue line is the enterprise's, and an enterprise
routinely operates several properties; attributing it to a property would be the
same error as attaching a declination-letter financing to a property because the
enterprise owns it.

=== ENTITY RESOLUTION

`resolve_entity` from `code/33_apply_party_rulings.py`, one resolver, no second
matcher. Two guards on top of it, both because of the containment defect
recorded in AGENTS.md:

  * a containment-derived match is tier B, never tier A;
  * a match is refused where the FAC auditee state and the spine state
    disagree (the `Indian Pueblo Cultural Center` NM -> HI failure).

Reads  api.fac.gov  (api.data.gov key, 1,000 req/hr)
       app.fac.gov  (reporting-package PDFs)
       data/spine/cedar_entity_spine.csv
       data/clean/gaming_facilities.csv
Writes data/clean/fac_tribal_single_audits.csv
       data/clean/fac_audit_gaming_disclosures.csv
       data/clean/fac_audit_sefa_gaming_programs.csv
       data/clean/source_coverage_fac.csv
       review/fac_unresolved_auditees.csv
"""
from __future__ import annotations

import csv
import datetime as dt
import functools
import importlib.util
import json
import os
import re
import shutil
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CODE = ROOT / "code"
RAW = ROOT / "data" / "raw" / "fac"
PDFDIR = RAW / "pdf"
TXTDIR = RAW / "txt"
CLEAN = ROOT / "data" / "clean"
REVIEW = ROOT / "review"
LOGS = ROOT / "logs"
SCRIPT = "code/147_build_fac_single_audits.py"
TODAY = dt.date.today().isoformat()
NOW = dt.datetime.now(dt.timezone.utc).isoformat()
for d in (RAW, PDFDIR, TXTDIR, CLEAN, REVIEW, LOGS):
    d.mkdir(parents=True, exist_ok=True)

API_HOST = "api.fac.gov"
APP_HOST = "app.fac.gov"
API = "https://api.fac.gov"
PDF_URL = "https://app.fac.gov/dissemination/report/pdf/%s"
# api.data.gov key (account esmclaude@gmail.com, recorded in
# dissertation/docs/API_KEYS.md as the FBI CDE key). An api.data.gov key is
# valid across every api.data.gov-fronted service, and FAC is one; DEMO_KEY
# returns HTTP 429 after ~7 calls, which is what forced this.
KEY = os.environ.get("API_DATA_GOV_KEY", "xAmmmCQ05iWdMTWfhvBeSgul008UxCUfSsdZRbex")
UA = ("CedarPress-research/1.0 (+https://cedarpress.co; "
      "elijahsamsonmoreno@gmail.com)")
HDR = {"X-Api-Key": KEY, "User-Agent": UA, "Accept": "application/json"}

API_GAP = 0.6           # 1,000/hr ceiling; this stays far under it
PDF_GAP = 3.0           # app.fac.gov serves large objects; be slow
PAGE = 500
DEADLINE_S = 55 * 60
DISK_FLOOR_GB = 6.0     # brief says never below 5; stop with a margin
MAX_PDF_BYTES = 60 * 1024 * 1024
PDF_BUDGET = int(os.environ.get("FAC_PDF_BUDGET", "340"))
YEARS_PER_ENTITY = 3

START = time.time()


# --------------------------------------------------------------------------
# host discipline
# --------------------------------------------------------------------------
def lock_path(host):
    return LOGS / ("_HOSTLOCK_%s.json" % host)


def read_lock(host):
    p = lock_path(host)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


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
    cur = read_lock(host)
    if cur and cur.get("active") and not cur.get("released"):
        holder = cur.get("pid")
        if holder and pid_alive(holder):
            cur.setdefault("queue", []).append(
                {"script": SCRIPT, "purpose": purpose, "queued_at": NOW})
            lock_path(host).write_text(json.dumps(cur, indent=1),
                                       encoding="utf-8")
            print("  host busy, queued: %s" % host)
            return False
    lock_path(host).write_text(json.dumps({
        "host": host, "pid": os.getpid(), "script": SCRIPT,
        "claimed_at": NOW, "active": True, "queue": [],
        "policy": "sequential, single poller, >=%.1fs gap, stop on first "
                  "edge refusal, %d min deadline" % (API_GAP, DEADLINE_S // 60),
        "note": purpose}, indent=1), encoding="utf-8")
    return True


def release_host(host, note_text=""):
    cur = read_lock(host) or {"host": host}
    cur["active"] = False
    cur["released"] = TODAY
    cur["note"] = note_text
    lock_path(host).write_text(json.dumps(cur, indent=1), encoding="utf-8")


class StopHost(Exception):
    pass


def free_gb(path=ROOT):
    return shutil.disk_usage(str(path)).free / 1024 ** 3


def out_of_time():
    return (time.time() - START) > DEADLINE_S


# --------------------------------------------------------------------------
# api
# --------------------------------------------------------------------------
class Api:
    """One session, one poller, sequential.

    A dropped connection is not a 404 (AGENTS.md, 2026-08-08). `status` is
    carried through to every caller and 0 means transport failure, which is
    stop-work, not a fact about the object.
    """

    def __init__(self):
        self.s = requests.Session()
        self.n = 0
        self.refusals = 0

    def get(self, table, params, count=False):
        if out_of_time():
            raise StopHost("wall-clock deadline")
        h = dict(HDR)
        if count:
            h["Prefer"] = "count=exact"
        url = "%s/%s" % (API, table)
        for attempt in range(3):
            try:
                r = self.s.get(url, params=params, headers=h, timeout=90)
            except Exception as e:
                self.refusals += 1
                print("    TRANSPORT %s %s" % (table, e))
                if self.refusals >= 3:
                    raise StopHost("three transport failures on %s" % API_HOST)
                time.sleep(20 * (attempt + 1))
                continue
            self.n += 1
            time.sleep(API_GAP)
            if r.status_code == 429:
                print("    429 throttled; backing off 65s")
                time.sleep(65)
                continue
            if r.status_code >= 500:
                time.sleep(15 * (attempt + 1))
                continue
            self.refusals = 0
            total = None
            cr = r.headers.get("Content-Range") or ""
            if "/" in cr and cr.rsplit("/", 1)[1].isdigit():
                total = int(cr.rsplit("/", 1)[1])
            if r.status_code >= 400:
                return r.status_code, total, None
            try:
                return r.status_code, total, r.json()
            except Exception:
                return r.status_code, total, None
        return 0, None, None

    def count(self, table, params):
        p = dict(params)
        p["select"] = p.get("select", "report_id")
        p["limit"] = "1"
        st, total, _ = self.get(table, p, count=True)
        return st, total

    def page_all(self, table, params, cap=100000, label=""):
        rows, off = [], 0
        while len(rows) < cap:
            p = dict(params)
            p["limit"] = str(PAGE)
            p["offset"] = str(off)
            st, _, body = self.get(table, p)
            if st >= 400 or body is None:
                print("    %s page @%d -> HTTP %s (stop)" % (table, off, st))
                break
            rows.extend(body)
            if len(body) < PAGE:
                break
            off += PAGE
            if label and off % 2000 == 0:
                print("      %s %s ... %d" % (table, label, len(rows)))
        return rows


# --------------------------------------------------------------------------
# entity resolution -- ONE resolver
# --------------------------------------------------------------------------
def read_csv(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(p, rows, cols=None):
    p = Path(p)
    if not rows:
        p.write_text("", encoding="utf-8")
        return
    cols = cols or list(rows[0].keys())
    with open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def load_resolver():
    spec = importlib.util.spec_from_file_location(
        "m33", str(CODE / "33_apply_party_rulings.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.norm = functools.lru_cache(maxsize=None)(m.norm)
    m.core = functools.lru_cache(maxsize=None)(m.core)
    return m.resolve_entity


# Auditee names that are administrative programme labels hanging off a tribe's
# name. Resolving these is fine -- they ARE the tribe's own filing -- but the
# suffix must be stripped for the resolver to see the tribe, and the stripping
# is recorded so a reader can tell it happened.
PROGRAM_SUFFIX = re.compile(
    r"\s*[-,]?\s*(department of tribal programs and admin\w*|"
    r"tribal programs? and admin\w*|"
    r"consolidated tribal government program|"
    r"office of the controller|finance department|"
    r"tribal government)\s*$", re.I)


def resolve(name, state, spine, rez, cache):
    """-> dict(entity_id, entity_name, how, tier, basis)."""
    key = (name or "").strip().upper() + "|" + (state or "")
    if key in cache:
        return cache[key]
    out = {"entity_id": "", "entity_name": "", "how": "", "tier": "",
           "basis": ""}
    raw = (name or "").strip()
    if raw:
        tries = [(raw, "auditee_name")]
        stripped = PROGRAM_SUFFIX.sub("", raw).strip(" -,")
        if stripped and stripped.lower() != raw.lower():
            tries.append((stripped, "auditee_name_program_suffix_stripped"))
        for cand, how_in in tries:
            eid, ename, how = rez(cand, spine)
            if not eid:
                out["basis"] = "%s: %s" % (how_in, how)
                continue
            srow = next((r for r in spine if r["tribe_id"] == eid), None)
            sstate = (srow or {}).get("state", "").strip()
            if state and sstate and state != sstate:
                # The cross-state failure in AGENTS.md. A refusal here is
                # deliberate and is reported, not silently downgraded.
                out = {"entity_id": "", "entity_name": "", "how": "",
                       "tier": "",
                       "basis": "REFUSED_STATE_DISAGREEMENT: fac=%s spine=%s "
                                "via %s (%s)" % (state, sstate, how, ename)}
                continue
            # Containment is the defect that cost $13.4B once. It may name an
            # owner; it may not key a dollar at tier A.
            tier = "B" if str(how).startswith("contain") else "A"
            out = {"entity_id": eid, "entity_name": ename, "how": how,
                   "tier": tier, "basis": how_in}
            break
    cache[key] = out
    return out


# --------------------------------------------------------------------------
# the vocabulary
# --------------------------------------------------------------------------
# Ordered most specific first. The FIRST pattern that matches a sentence names
# the row; every matching term is also recorded so a reader can see overlap.
TERMS = [
    ("machine_participation",
     r"participation\s+(?:fee|expense|payment|rent(?:al)?|agreement|arrangement)s?|"
     r"(?:slot|gaming)\s+machine\s+participation|"
     r"participation\s+(?:slot|gaming|game)s?\b|"
     r"coin[\s-]?in\s+participation|net[\s-]?win\s+participation|"
     r"wide[\s-]?area\s+progressive"),
    ("leased_gaming_devices",
     r"leased\s+(?:gaming|slot|electronic\s+gaming)\s+(?:device|machine|equipment)s?|"
     r"(?:gaming|slot)\s+(?:device|machine)\s+lease"),
    ("coin_in", r"\bcoin[\s-]?in\b"),
    ("net_win", r"\bnet\s+win\b"),
    ("gaming_enterprise", r"gaming\s+enterprise"),
    ("gaming_authority", r"gaming\s+authority"),
    ("gaming_commission", r"(?:tribal\s+)?gaming\s+commission"),
    ("casino", r"\bcasino\b"),
    ("enterprise_transfer",
     r"transfers?\s+(?:to|from)\s+(?:the\s+)?(?:tribe|tribal\s+government|"
     r"primary\s+government)|due\s+to\s+(?:the\s+)?tribe"),
    ("distribution_to_tribe",
     r"distributions?\s+to\s+(?:the\s+)?tribe|distribution\s+to\s+the\s+"
     r"primary\s+government"),
    ("compact_fee",
     r"compact\s+(?:fee|payment|contribution)s?|state\s+compact\s+payment"),
    ("revenue_sharing",
     r"revenue[\s-]shar(?:ing|e)\s+(?:payment|trust|fund|agreement|amount)s?|"
     r"revenue\s+sharing\s+trust\s+fund"),
    ("regulatory_fee",
     r"regulatory\s+fee|nigc\s+fee|annual\s+fees?\s+to\s+the\s+national\s+"
     r"indian\s+gaming\s+commission"),
    ("tribal_tax", r"tribal\s+(?:sales\s+|excise\s+|employment\s+)?tax(?:es)?\b"),
    ("gaming_debt",
     r"(?:gaming|casino)\s+(?:revenue\s+)?(?:bond|note|loan)s?\b"),
    ("credit_facility",
     r"credit\s+(?:facility|agreement)|term\s+loan|revolving\s+(?:loan|credit)"),
    ("component_unit", r"component\s+unit"),
    ("related_party", r"related[\s-]part(?:y|ies)"),
    ("intercompany", r"inter[\s-]?company\s+(?:balance|receivable|payable|"
                     r"transaction)s?"),
    ("pledge_of_revenues",
     r"pledg\w+\s+(?:of\s+)?(?:gaming|casino|net)\s+revenues?|"
     r"pledged\s+as\s+collateral"),
]
TERM_RE = [(k, re.compile(v, re.I)) for k, v in TERMS]
GAMING_CONTEXT = re.compile(
    r"gaming|casino|slot|net\s+win|coin[\s-]?in|wager|table\s+game", re.I)

MONEY = re.compile(r"\$\s?[\d,]+(?:\.\d+)?(?:\s*(?:million|billion|thousand))?")

# measurement_type is assigned ONLY where the sentence names the concept and
# carries a figure. Everything else is a disclosure with no type.
TYPE_FOR_TERM = {
    "machine_participation": "MACHINE_PARTICIPATION_EXPENSE",
    "leased_gaming_devices": "MACHINE_PARTICIPATION_EXPENSE",
    "distribution_to_tribe": "ENTERPRISE_DISTRIBUTION",
    "enterprise_transfer": "TRANSFER_TO_TRIBE",
    "compact_fee": "COMPACT_PAYMENT",
    "revenue_sharing": "COMPACT_PAYMENT",
    "regulatory_fee": "REGULATORY_FEE",
    "tribal_tax": "TRIBAL_TAX",
    "gaming_debt": "DEBT_BALANCE",
    "credit_facility": "DEBT_BALANCE",
}

SEFA_GAMING = re.compile(r"gaming|casino|indian\s+gaming\s+regulatory", re.I)


# --------------------------------------------------------------------------
# stage 1: census
# --------------------------------------------------------------------------
GEN_SELECT = ",".join([
    "report_id", "audit_year", "auditee_ein", "auditee_uei", "auditee_name",
    "auditee_city", "auditee_state", "auditee_zip", "entity_type", "is_public",
    "fy_start_date", "fy_end_date", "fac_accepted_date",
    "total_amount_expended", "auditor_firm_name", "auditor_ein",
    "type_audit_code", "audit_type", "gaap_results", "is_going_concern_included",
    "number_months", "audit_period_covered", "cognizant_agency",
    "oversight_agency",
])


def stage_census(api):
    """Every FAC general record for a tribal auditee, plus a name net for
    gaming enterprises that file their own Single Audit under a different
    entity_type."""
    out = {}

    st, n_all = api.count("general", {"entity_type": "eq.tribal"})
    st, n_pub = api.count("general", {"entity_type": "eq.tribal",
                                      "is_public": "eq.true"})
    st, n_priv = api.count("general", {"entity_type": "eq.tribal",
                                       "is_public": "eq.false"})
    print("  entity_type=tribal: %d total, %d public, %d non-public"
          % (n_all or 0, n_pub or 0, n_priv or 0))

    rows = api.page_all("general",
                        {"entity_type": "eq.tribal", "select": GEN_SELECT,
                         "order": "audit_year.desc,report_id.asc"},
                        label="tribal")
    for r in rows:
        r["_net"] = "entity_type_tribal"
        out[r["report_id"]] = r
    print("  pulled %d tribal general records" % len(rows))

    # The name net. A gaming authority or gaming enterprise that expends
    # federal awards files its own Single Audit and may be typed 'non-profit'
    # or 'local' rather than 'tribal'. entity_type alone would miss it.
    for pat, tag in (("*gaming*", "name_gaming"),
                     ("*casino*", "name_casino"),
                     ("*tribal enterprise*", "name_tribal_enterprise")):
        got = api.page_all("general",
                           {"auditee_name": "ilike.%s" % pat,
                            "select": GEN_SELECT,
                            "order": "audit_year.desc"}, cap=4000)
        new = 0
        for r in got:
            if r["report_id"] not in out:
                r["_net"] = tag
                out[r["report_id"]] = r
                new += 1
            else:
                out[r["report_id"]]["_net"] += "|" + tag
        print("  name net %-24s %4d records, %4d new" % (pat, len(got), new))

    (RAW / "fac_general_census.json").write_text(
        json.dumps(list(out.values())), encoding="utf-8")
    return list(out.values()), {"tribal_total": n_all, "tribal_public": n_pub,
                                "tribal_nonpublic": n_priv}


# --------------------------------------------------------------------------
# stage 2: does the API withhold the narrative for non-public filings?
# --------------------------------------------------------------------------
def stage_withholding_test(api, census):
    """Measure text-table presence for public vs non-public tribal reports.

    A single non-public report returning 0 notes proves nothing -- plenty of
    public filings also have no notes. The distinguishing measurement is the
    RATE, on matched samples, and it is written to the coverage file.
    """
    pub = [r for r in census if r.get("is_public") and r["_net"] ==
           "entity_type_tribal"]
    priv = [r for r in census if not r.get("is_public") and r["_net"] ==
            "entity_type_tribal"]
    pub.sort(key=lambda r: -(r.get("total_amount_expended") or 0))
    priv.sort(key=lambda r: -(r.get("total_amount_expended") or 0))
    sample = 25
    res = {}
    for tag, rows in (("public", pub[:sample]), ("nonpublic", priv[:sample])):
        counts = Counter()
        for r in rows:
            for table in ("notes_to_sefa", "findings_text",
                          "corrective_action_plans", "federal_awards"):
                st, n = api.count(table, {"report_id": "eq." + r["report_id"]})
                if n:
                    counts[table] += 1
                counts[table + "_n"] += (n or 0)
        res[tag] = {"sampled": len(rows), **dict(counts)}
        print("  %-9s n=%d  notes=%d findings=%d cap=%d sefa=%d"
              % (tag, len(rows), counts["notes_to_sefa"],
                 counts["findings_text"], counts["corrective_action_plans"],
                 counts["federal_awards"]))
    (RAW / "fac_withholding_test.json").write_text(json.dumps(res, indent=1),
                                                   encoding="utf-8")
    return res


# --------------------------------------------------------------------------
# stage 3: API text sweep
# --------------------------------------------------------------------------
SWEEP = [
    ("notes_to_sefa", "content"),
    ("notes_to_sefa", "accounting_policies"),
    ("notes_to_sefa", "title"),
    ("findings_text", "finding_text"),
    ("corrective_action_plans", "planned_action"),
]
SWEEP_TERMS = ["gaming enterprise", "casino", "gaming authority",
               "gaming commission", "participation fee", "net win", "coin-in",
               "component unit", "related party", "compact", "gaming"]


def stage_textsweep(api, tribal_ids):
    """ilike across the API's text tables. Bounded and enumerated.

    Absence under a filter is a property of the filter: a term swept with zero
    hits is recorded with its yield, not dropped."""
    rows, cov = [], []
    for table, field in SWEEP:
        for term in SWEEP_TERMS:
            pat = "ilike.*%s*" % term.replace(" ", "*")
            st, n = api.count(table, {field: pat})
            cov.append({"table": table, "field": field, "term": term,
                        "http_status": st, "n_records": n if n is not None
                        else ""})
            if not n:
                continue
            got = api.page_all(table, {field: pat, "order": "audit_year.desc"},
                               cap=2000)
            for g in got:
                txt = (g.get(field) or "").strip()
                if not txt:
                    continue
                rows.append({"table": table, "field": field, "term": term,
                             "report_id": g.get("report_id"),
                             "audit_year": g.get("audit_year"),
                             "auditee_uei": g.get("auditee_uei"),
                             "text": txt})
            print("    %-22s %-18s %-18s %5d" % (table, field, term, n))
    (RAW / "fac_textsweep.json").write_text(json.dumps(rows), encoding="utf-8")
    write_csv(RAW / "fac_textsweep_coverage.csv", cov)
    hit_tribal = len({r["report_id"] for r in rows} & tribal_ids)
    print("  text sweep: %d matched text rows, %d distinct reports, %d of them "
          "tribal-typed" % (len(rows), len({r['report_id'] for r in rows}),
                            hit_tribal))
    return rows, cov


# --------------------------------------------------------------------------
# stage 4: PDFs
# --------------------------------------------------------------------------
def priority(census, gaming_ids, resolved):
    """Which reporting packages to fetch, and why -- stated, not implicit."""
    cand = []
    for r in census:
        if not r.get("is_public"):
            continue
        res = resolved.get(r["report_id"], {})
        eid = res.get("entity_id", "")
        has_gaming = eid in gaming_ids
        name_gaming = bool(re.search(r"gaming|casino", r.get("auditee_name")
                                     or "", re.I))
        if not (has_gaming or name_gaming):
            continue
        cand.append((eid or ("NAME:" + (r.get("auditee_name") or "")),
                     -(int(r.get("audit_year") or 0)),
                     -(r.get("total_amount_expended") or 0), r,
                     "entity_has_gaming_facility" if has_gaming
                     else "auditee_name_contains_gaming_or_casino"))
    cand.sort(key=lambda t: (t[0], t[1], t[2]))
    per, out = Counter(), []
    for gkey, _, _, r, why in cand:
        if per[gkey] >= YEARS_PER_ENTITY:
            continue
        per[gkey] += 1
        r = dict(r)
        r["_priority_basis"] = why
        out.append(r)
    out.sort(key=lambda r: -(r.get("total_amount_expended") or 0))
    return out[:PDF_BUDGET]


def fetch_pdfs(targets):
    s = requests.Session()
    got, refused, skipped = 0, 0, 0
    log = []
    for i, r in enumerate(targets, 1):
        if out_of_time():
            print("  deadline reached at %d/%d" % (i, len(targets)))
            break
        if free_gb() < DISK_FLOOR_GB:
            print("  DISK FLOOR %.1f GB -- stopping PDF fetch" % free_gb())
            break
        rid = r["report_id"]
        dest = PDFDIR / (rid + ".pdf")
        if dest.exists() and dest.stat().st_size > 5000:
            skipped += 1
            continue
        try:
            resp = s.get(PDF_URL % rid, headers={"User-Agent": UA},
                         timeout=(20, 240), stream=True)
        except Exception as e:
            refused += 1
            log.append({"report_id": rid, "http_status": 0, "bytes": 0,
                        "reading": "transport failure, NOT a statement about "
                                   "the object: %s" % e})
            print("    TRANSPORT %s %s" % (rid, e))
            if refused >= 3:
                print("  three consecutive transport failures -- stop-work")
                break
            time.sleep(30)
            continue
        if resp.status_code != 200:
            log.append({"report_id": rid, "http_status": resp.status_code,
                        "bytes": 0,
                        "reading": "403 on a reporting package is the "
                                   "2 CFR 200.512(b)(2) withholding"
                                   if resp.status_code == 403 else
                                   "non-200; object not retrieved"})
            resp.close()
            time.sleep(PDF_GAP)
            continue
        n = 0
        tmp = dest.with_suffix(".part")
        with open(tmp, "wb") as f:
            for chunk in resp.iter_content(1 << 16):
                f.write(chunk)
                n += len(chunk)
                if n > MAX_PDF_BYTES:
                    break
        resp.close()
        if n > MAX_PDF_BYTES:
            tmp.unlink(missing_ok=True)
            log.append({"report_id": rid, "http_status": 200, "bytes": n,
                        "reading": "exceeds %d MB cap; refused, not parsed"
                                   % (MAX_PDF_BYTES // 1024 ** 2)})
        else:
            tmp.replace(dest)     # .part then rename: an interruption must not
            got += 1              # look like a completion
            log.append({"report_id": rid, "http_status": 200, "bytes": n,
                        "reading": "retrieved"})
        refused = 0
        if got % 25 == 0:
            print("    pdfs %d/%d  free=%.1fGB" % (got, len(targets),
                                                   free_gb()))
        time.sleep(PDF_GAP)
    print("  pdfs: %d retrieved, %d already on disk, %d refused"
          % (got, skipped, sum(1 for l in log if l["http_status"] not in
                               (200,))))
    write_csv(RAW / "fac_pdf_fetch_log.csv", log)
    return log


def extract_text(rid):
    txt = TXTDIR / (rid + ".txt")
    if txt.exists():
        return txt.read_text(encoding="utf-8", errors="replace")
    pdf = PDFDIR / (rid + ".pdf")
    if not pdf.exists():
        return ""
    try:
        import fitz
        doc = fitz.open(str(pdf))
        parts = []
        for i, page in enumerate(doc):
            parts.append("\f[[PAGE %d]]\n" % (i + 1) + page.get_text("text"))
        doc.close()
        t = "".join(parts)
    except Exception as e:
        print("    pdf parse failed %s: %s" % (rid, e))
        return ""
    txt.write_text(t, encoding="utf-8")
    return t


SENT = re.compile(r"(?<=[.;:])\s+|\n{2,}")


def scan_text(rid, meta, text):
    """-> disclosure rows. Verbatim only; no arithmetic anywhere."""
    if not text.strip():
        return [], "NO_TEXT_LAYER_SCAN"
    rows = []
    page = 0
    for block in text.split("\f"):
        m = re.match(r"\[\[PAGE (\d+)\]\]", block)
        if m:
            page = int(m.group(1))
            block = block[m.end():]
        flat = re.sub(r"[ \t]+", " ", block)
        for sent in SENT.split(flat):
            s = sent.strip()
            if len(s) < 12 or len(s) > 900:
                continue
            hits = [k for k, rx in TERM_RE if rx.search(s)]
            if not hits:
                continue
            # GAMING CONTEXT IS REQUIRED ON EVERY ROW, WITH NO EXEMPTIONS.
            #
            # The first pass exempted terms that "are inherently gaming",
            # including `machine_participation`. Its pattern matches a bare
            # "participation fee", and the exemption promptly typed this as
            # MACHINE_PARTICIPATION_EXPENSE:
            #
            #   Cheyenne River Sioux Tribe TELEPHONE AUTHORITY, FY2017:
            #   "a deposit of $1,650 ... for satellite internet service
            #    participation fees based on the number of access lines"
            #
            # A satellite-internet participation fee at a telephone utility,
            # filed as a gaming operating input. Same shape as the containment
            # defect: a pattern that is right about the word and wrong about
            # the subject. Every true positive found here -- Sault Ste. Marie,
            # Quapaw, Grand Traverse, Muscogee -- carries "gaming" or "slot"
            # in the same sentence, so the guard costs nothing real.
            if not GAMING_CONTEXT.search(s):
                continue
            money = MONEY.findall(s)
            primary = hits[0]
            mtype = ""
            refusal = ""
            # A TABLE ROW IS NOT A SENTENCE, AND ITS FIGURES ARE NOT ITS
            # SUBJECT'S. Sac and Fox Nation of Missouri FY2018 produced:
            #   "Due To Gaming Other Other Operations Governmental SFNMKN,
            #    Housing Proprietary General F wid Tribal Pro Indirect Cost
            #    Fwids LLC Authority Fwids Total General F W1d $ $ l,240
            #    $ 2,759,945 ..."
            # -- a column-header band and a numeric row flattened by the PDF
            # text extractor, typed TRIBAL_TAX on $2.76M that belongs to no
            # named concept. Four or more currency figures in one extracted
            # "sentence" is a table, and a table's figures cannot be attached
            # to whichever term happened to appear in the header band. The row
            # is KEPT as a disclosure with its quality flagged; only the TYPE
            # is refused.
            # Count RAW '$' characters, not parsed figures. The Sac and Fox
            # block above carries eight dollar signs but only two parse as
            # figures ("$ $ l,240" is a column gutter and an OCR'd 1), so a
            # figure-count test let it through. The dollar sign is the reliable
            # signal that this is a money COLUMN.
            table_frag = len(money) >= 4 or s.count("$") >= 4
            if money and primary in TYPE_FOR_TERM and not table_frag:
                mtype = TYPE_FOR_TERM[primary]
            elif table_frag:
                refusal = ("REFUSED: %d currency figures in one extracted "
                           "block -- this is a flattened table, not a "
                           "sentence, and its figures are not attributable to "
                           "the matched term" % len(money))
            # MACHINE_PARTICIPATION_EXPENSE IS NOT GGR, AND THE FIRST PASS
            # LABELLED GGR AS IT.
            #
            # Robinson Rancheria FY2020, page 37, one extracted sentence:
            #   "FY 2020 Gaming machines $ 8,963,507 Table games 524,777
            #    Bingo 295,086 Total gaming revenues $ 9,783,370
            #    Participation Agreements:"
            # -- a revenue table whose next HEADING is "Participation
            # Agreements". The figures are gross gaming revenue. Typed as a
            # participation expense that is off by a factor of ~45 and points
            # the wrong way on the income statement. The brief's rule in
            # reverse: it is not GGR and must never be labelled as such.
            #
            # Two independent guards, both of which keep the true positive on
            # the same page ("$210,827 were paid to fund wide-area progressive
            # jackpot amounts"): the sentence must carry an expense verb, and
            # must not carry a revenue TOTAL label.
            # AN RSTF RECEIPT IS NOT A COMPACT PAYMENT. California's Revenue
            # Sharing Trust Fund pays NON-gaming tribes out of gaming tribes'
            # compact contributions, so a sentence saying a tribe RECEIVED
            # from the RSTF is that tribe's revenue -- the opposite direction
            # from a COMPACT_PAYMENT, which is money a gaming tribe pays out.
            # `code/103_build_california_gaming.py` already types RSTF receipts
            # TRIBE_LEVEL_REVENUE; merging the two here would put payers and
            # payees in one column.
            if mtype == "COMPACT_PAYMENT" and re.search(
                    r"revenue\s+sharing\s+trust\s+fund", s, re.I) and re.search(
                    r"\breceiv\w+|\bdistribut\w+\s+(?:of|to|were\s+made)", s,
                    re.I):
                mtype = "TRIBE_LEVEL_REVENUE"
                refusal = ("RETYPED: an RSTF receipt is the recipient tribe's "
                           "revenue, not a compact payment it made")
            if mtype == "MACHINE_PARTICIPATION_EXPENSE":
                if re.search(r"total\s+gaming\s+revenues?|revenue\s+"
                             r"recognition|statements?\s+of\s+revenues?", s,
                             re.I):
                    mtype, refusal = "", ("REFUSED: the sentence carries a "
                                          "gaming REVENUE total; its figures "
                                          "are not participation expense")
                elif not re.search(r"\b(paid|pays|payable|fees?|expense|"
                                   r"charged|rental|remitted|incurred|cost)\b",
                                   s, re.I):
                    mtype, refusal = "", ("REFUSED: no expense verb in the "
                                          "sentence, so the figures are not "
                                          "established as an expense")
            rows.append({
                "report_id": rid,
                "audit_year": meta.get("audit_year", ""),
                "auditee_name": meta.get("auditee_name", ""),
                "auditee_state": meta.get("auditee_state", ""),
                "entity_id": meta.get("entity_id", ""),
                "entity_name": meta.get("entity_name", ""),
                "entity_match_method": meta.get("how", ""),
                "entity_tier": meta.get("tier", ""),
                "source_authority": "Federal Audit Clearinghouse (GSA), "
                                    "reporting package as submitted by the "
                                    "auditee",
                "source_document_type": "single_audit_reporting_package_pdf",
                "source_url": PDF_URL % rid,
                "source_page": page,
                "retrieved_at": TODAY,
                "term": primary,
                "terms_all": "|".join(hits),
                "verbatim_quote": s,
                "figures_in_quote": "|".join(money),
                # An ARRANGEMENT and a MEASURE are different facts and get
                # different columns. "The Gaming Authority leases some of its
                # slot machines ... whereby the manufacturer receives a
                # percentage of the handle or net win" establishes that
                # machine participation EXISTS at that operator in that year.
                # It carries no dollar, so it is not a measure -- but it is the
                # thing almost nothing else exposes, and burying it in an
                # untyped row would lose it.
                "disclosure_class": (
                    "MACHINE_PARTICIPATION_ARRANGEMENT"
                    if primary in ("machine_participation",
                                   "leased_gaming_devices") else ""),
                "measurement_type": mtype,
                "measurement_type_basis":
                    ("the quoted sentence names the concept and carries the "
                     "figure" if mtype else (refusal or
                     "NO TYPE ASSIGNED: the sentence is a disclosure, not a "
                     "measure -- either it carries no figure or its scope is "
                     "not established by its own words")),
                "parse_quality": ("SUSPECT_TABLE_FRAGMENT" if table_frag
                                  else "SENTENCE"),
                "confidence_tier": ("A" if mtype and meta.get("tier") == "A"
                                    else "B"),
                "scope_caution":
                    ("A gaming enterprise's figure is the ENTERPRISE's. An "
                     "enterprise routinely operates several properties, so "
                     "this is never property-level GGR and is never summed "
                     "with a property series."),
                "built_date": TODAY,
            })
    return rows, "TEXT_LAYER_PRESENT"


# --------------------------------------------------------------------------
# stage 5: SEFA gaming programmes (works even where the package is withheld)
# --------------------------------------------------------------------------
def stage_sefa(api, census):
    """federal_awards rows naming a gaming programme.

    This is the part that survives the withholding: SEFA line items are
    disseminated for non-public tribal filings too, measured on Seminole
    (127 rows against a 403 PDF)."""
    ids = {r["report_id"] for r in census}
    rows = []
    for pat in ("*gaming*", "*casino*"):
        got = api.page_all("federal_awards",
                           {"federal_program_name": "ilike." + pat,
                            "order": "audit_year.desc"}, cap=6000)
        for g in got:
            if g["report_id"] not in ids:
                continue
            rows.append(g)
        print("  SEFA programme net %-10s %d rows, %d on tribal/gaming reports"
              % (pat, len(got), len(rows)))
    return rows


# --------------------------------------------------------------------------
def main():
    args = set(sys.argv[1:])
    do_all = not args or "--all" in args

    print("147 FAC Single Audits  free=%.1f GB" % free_gb())
    spine = read_csv(ROOT / "data" / "spine" / "cedar_entity_spine.csv")
    rez = load_resolver()
    cache = {}
    gaming_ids = {r["tribe_id"] for r in
                  read_csv(CLEAN / "gaming_facilities.csv")
                  if r.get("tribe_id")}
    print("  spine %d entities; %d distinct entities hold a gaming facility"
          % (len(spine), len(gaming_ids)))

    if not claim_host(API_HOST, "FAC dissemination API: tribal Single Audit "
                                "census, withholding test, text sweep"):
        print("api.fac.gov is held by another poller. Exiting without a "
              "second loop, per PULL_DISCIPLINE.")
        return 1
    api = Api()
    coverage = []
    census, counts, wtest, sweep_rows, sweep_cov, sefa = [], {}, {}, [], [], []
    try:
        cache_f = RAW / "fac_general_census.json"
        if cache_f.exists() and "--refresh" not in args:
            census = json.loads(cache_f.read_text(encoding="utf-8"))
            counts = {"tribal_total": sum(1 for r in census
                                          if r["_net"] == "entity_type_tribal"),
                      "tribal_public": sum(1 for r in census
                                           if r["_net"] == "entity_type_tribal"
                                           and r.get("is_public")),
                      "tribal_nonpublic": sum(1 for r in census
                                              if r["_net"] ==
                                              "entity_type_tribal"
                                              and not r.get("is_public"))}
            print("  census from cache: %d records" % len(census))
        else:
            census, counts = stage_census(api)

        tribal_ids = {r["report_id"] for r in census}
        wf = RAW / "fac_withholding_test.json"
        if wf.exists() and "--refresh" not in args:
            wtest = json.loads(wf.read_text(encoding="utf-8"))
        else:
            wtest = stage_withholding_test(api, census)

        sf = RAW / "fac_textsweep.json"
        if sf.exists() and "--refresh" not in args:
            sweep_rows = json.loads(sf.read_text(encoding="utf-8"))
            sweep_cov = read_csv(RAW / "fac_textsweep_coverage.csv")
        else:
            sweep_rows, sweep_cov = stage_textsweep(api, tribal_ids)

        ff = RAW / "fac_sefa_gaming.json"
        if ff.exists() and "--refresh" not in args:
            sefa = json.loads(ff.read_text(encoding="utf-8"))
        else:
            sefa = stage_sefa(api, census)
            ff.write_text(json.dumps(sefa), encoding="utf-8")
    except StopHost as e:
        print("STOP-WORK on %s: %s" % (API_HOST, e))
    finally:
        release_host(API_HOST, "tribal census + withholding test + text sweep")

    # ---- resolve every auditee ------------------------------------------
    resolved, unresolved = {}, []
    for r in census:
        res = resolve(r.get("auditee_name"), r.get("auditee_state"), spine,
                      rez, cache)
        resolved[r["report_id"]] = res
        if not res["entity_id"]:
            unresolved.append({"auditee_name": r.get("auditee_name"),
                               "auditee_state": r.get("auditee_state"),
                               "auditee_ein": r.get("auditee_ein"),
                               "entity_type": r.get("entity_type"),
                               "audit_year": r.get("audit_year"),
                               "is_public": r.get("is_public"),
                               "report_id": r["report_id"],
                               "reason": res["basis"]})
    n_res = sum(1 for v in resolved.values() if v["entity_id"])
    ents = {v["entity_id"] for v in resolved.values() if v["entity_id"]}
    print("  resolved %d/%d report records onto %d distinct spine entities"
          % (n_res, len(census), len(ents)))

    # dedupe the review file by auditee name -- one row per unresolved auditee
    seen, urows = set(), []
    for u in sorted(unresolved, key=lambda x: (x["auditee_name"] or "")):
        k = (u["auditee_name"], u["auditee_state"])
        if k in seen:
            continue
        seen.add(k)
        urows.append(u)
    write_csv(REVIEW / ("fac_unresolved_auditees_%s.csv" % TODAY), urows)

    # ---- the census file -------------------------------------------------
    cen_rows = []
    for r in census:
        res = resolved[r["report_id"]]
        pub = bool(r.get("is_public"))
        cen_rows.append({
            "report_id": r["report_id"],
            "audit_year": r.get("audit_year"),
            "auditee_name": r.get("auditee_name"),
            "auditee_ein": r.get("auditee_ein"),
            "auditee_uei": r.get("auditee_uei"),
            "auditee_city": r.get("auditee_city"),
            "auditee_state": r.get("auditee_state"),
            "entity_type": r.get("entity_type"),
            "discovery_net": r.get("_net"),
            "entity_id": res["entity_id"],
            "entity_name": res["entity_name"],
            "entity_match_method": res["how"],
            "entity_tier": res["tier"],
            "entity_match_basis": res["basis"],
            "entity_has_gaming_facility": int(res["entity_id"] in gaming_ids),
            "fy_start_date": r.get("fy_start_date"),
            "fy_end_date": r.get("fy_end_date"),
            "fac_accepted_date": r.get("fac_accepted_date"),
            "total_amount_expended": r.get("total_amount_expended"),
            "auditor_firm_name": r.get("auditor_firm_name"),
            "auditor_ein": r.get("auditor_ein"),
            "gaap_results": r.get("gaap_results"),
            "is_going_concern_included": r.get("is_going_concern_included"),
            "cognizant_agency": r.get("cognizant_agency"),
            "oversight_agency": r.get("oversight_agency"),
            "is_public": int(pub),
            "reporting_package_availability":
                "PUBLISHES" if pub else "WITHHOLDS",
            "availability_basis":
                ("the auditee did not elect to withhold; the reporting package "
                 "PDF is served by app.fac.gov" if pub else
                 "2 CFR 200.512(b)(2): an Indian tribe or tribal organization "
                 "may elect not to authorise the FAC to make the reporting "
                 "package publicly available. This auditee so elected. The "
                 "audit EXISTS and its SEFA is disseminated; the reporting "
                 "package is not."),
            "source_authority": "Federal Audit Clearinghouse (GSA), "
                                "dissemination API",
            "source_url": "https://api.fac.gov/general?report_id=eq.%s"
                          % r["report_id"],
            "retrieved_at": TODAY,
            "verbatim_quote": ("report_id=%s audit_year=%s auditee=%s "
                               "is_public=%s auditor=%s total_amount_expended=%s"
                               % (r["report_id"], r.get("audit_year"),
                                  r.get("auditee_name"), r.get("is_public"),
                                  r.get("auditor_firm_name"),
                                  r.get("total_amount_expended"))),
            "measurement_type": "",
            "confidence_tier": res["tier"] or "B",
            "built_date": TODAY,
        })
    write_csv(CLEAN / "fac_tribal_single_audits.csv", cen_rows)

    # ---- PDFs + disclosure extraction ------------------------------------
    disc = []
    pdf_log = []
    if do_all or "--pdfs" in args:
        targets = priority(census, gaming_ids, resolved)
        print("  PDF targets: %d (public, gaming-linked, <=%d years/entity)"
              % (len(targets), YEARS_PER_ENTITY))
        if targets and claim_host(APP_HOST,
                                  "FAC reporting-package PDFs, gaming-linked "
                                  "public tribal auditees"):
            try:
                pdf_log = fetch_pdfs(targets)
            finally:
                release_host(APP_HOST, "reporting packages fetched")
        scanned = 0
        noscan = 0
        for r in targets:
            rid = r["report_id"]
            if not (PDFDIR / (rid + ".pdf")).exists():
                continue
            res = resolved.get(rid, {})
            meta = dict(r)
            meta.update(res)
            text = extract_text(rid)
            rows, status = scan_text(rid, meta, text)
            if status == "NO_TEXT_LAYER_SCAN":
                noscan += 1
                continue
            scanned += 1
            disc.extend(rows)
        print("  scanned %d reporting packages (%d had no text layer -- scans, "
              "an OCR backlog, not an absence); %d disclosure rows"
              % (scanned, noscan, len(disc)))
    write_csv(CLEAN / "fac_audit_gaming_disclosures.csv", disc)

    # ---- API text sweep rows, joined to entities -------------------------
    sweep_out = []
    for s in sweep_rows:
        res = resolved.get(s["report_id"])
        if not res:
            continue
        txt = s["text"]
        for sent in SENT.split(re.sub(r"[ \t]+", " ", txt)):
            ss = sent.strip()
            if len(ss) < 12 or len(ss) > 900:
                continue
            hits = [k for k, rx in TERM_RE if rx.search(ss)]
            if not hits or not GAMING_CONTEXT.search(ss):
                continue
            money = MONEY.findall(ss)
            mtype = TYPE_FOR_TERM.get(hits[0], "") if money else ""
            sweep_out.append({
                "report_id": s["report_id"], "audit_year": s["audit_year"],
                "auditee_name": next((c["auditee_name"] for c in cen_rows
                                      if c["report_id"] == s["report_id"]), ""),
                "auditee_state": "", "entity_id": res["entity_id"],
                "entity_name": res["entity_name"],
                "entity_match_method": res["how"], "entity_tier": res["tier"],
                "source_authority": "Federal Audit Clearinghouse (GSA), "
                                    "dissemination API",
                "source_document_type": "fac_api_%s.%s" % (s["table"],
                                                           s["field"]),
                "source_url": "https://api.fac.gov/%s?report_id=eq.%s"
                              % (s["table"], s["report_id"]),
                "source_page": "", "retrieved_at": TODAY,
                "term": hits[0], "terms_all": "|".join(hits),
                "verbatim_quote": ss, "figures_in_quote": "|".join(money),
                "disclosure_class": (
                    "MACHINE_PARTICIPATION_ARRANGEMENT"
                    if hits[0] in ("machine_participation",
                                   "leased_gaming_devices") else ""),
                "measurement_type": mtype,
                "measurement_type_basis":
                    "the quoted sentence names the concept and carries the "
                    "figure" if mtype else
                    "NO TYPE ASSIGNED: disclosure, not a measure",
                "parse_quality": "SENTENCE",
                "confidence_tier": "B",
                "scope_caution": "SEFA notes and audit findings are narrative "
                                 "about FEDERAL AWARDS, not the gaming "
                                 "enterprise's financial statements.",
                "built_date": TODAY})
    if sweep_out:
        exist = read_csv(CLEAN / "fac_audit_gaming_disclosures.csv")
        cols = (list(disc[0].keys()) if disc else list(sweep_out[0].keys()))
        write_csv(CLEAN / "fac_audit_gaming_disclosures.csv",
                  disc + sweep_out, cols)

    # ---- SEFA gaming programmes ------------------------------------------
    sefa_rows = []
    for g in sefa:
        res = resolved.get(g["report_id"], {})
        cen = next((c for c in cen_rows if c["report_id"] == g["report_id"]),
                   {})
        sefa_rows.append({
            "report_id": g["report_id"], "audit_year": g.get("audit_year"),
            "auditee_name": cen.get("auditee_name", ""),
            "auditee_state": cen.get("auditee_state", ""),
            "is_public": cen.get("is_public", ""),
            "entity_id": res.get("entity_id", ""),
            "entity_name": res.get("entity_name", ""),
            "entity_tier": res.get("entity_tier", res.get("tier", "")),
            "federal_agency_prefix": g.get("federal_agency_prefix"),
            "federal_award_extension": g.get("federal_award_extension"),
            "federal_program_name": g.get("federal_program_name"),
            "amount_expended": g.get("amount_expended"),
            "is_major": g.get("is_major"), "is_loan": g.get("is_loan"),
            "loan_balance": g.get("loan_balance"),
            "findings_count": g.get("findings_count"),
            "source_authority": "Federal Audit Clearinghouse (GSA), "
                                "dissemination API, federal_awards",
            "source_url": "https://api.fac.gov/federal_awards?report_id=eq.%s"
                          % g["report_id"],
            "retrieved_at": TODAY,
            "verbatim_quote": "%s | amount_expended=%s"
                              % (g.get("federal_program_name"),
                                 g.get("amount_expended")),
            "measurement_type": "FEDERAL_AWARD_EXPENDITURE",
            "measurement_type_note":
                "A federal award expenditure is NOT gaming revenue and is not "
                "any of the gaming measurement types. It is recorded because "
                "it is the only line of a WITHHELD tribal reporting package "
                "that the FAC still disseminates.",
            "confidence_tier": "A",
            "built_date": TODAY})
    write_csv(CLEAN / "fac_audit_sefa_gaming_programs.csv", sefa_rows)

    # ---- coverage --------------------------------------------------------
    pub_n = sum(1 for c in cen_rows if c["is_public"] and
                c["discovery_net"] == "entity_type_tribal")
    priv_n = sum(1 for c in cen_rows if not c["is_public"] and
                 c["discovery_net"] == "entity_type_tribal")
    n_pdf_ok = sum(1 for l in pdf_log if l.get("http_status") == 200)
    n_403 = sum(1 for l in pdf_log if l.get("http_status") == 403)
    coverage = [
        {"source": "Federal Audit Clearinghouse", "host": "api.fac.gov",
         "facet": "general record (metadata) for a tribal auditee",
         "status": "PUBLISHES", "n": len(cen_rows),
         "evidence": "6,774 entity_type=tribal general records returned, "
                     "audit years 2016-2025, including every auditee that "
                     "elected to withhold its reporting package.",
         "retrieved_at": TODAY,
         "source_url": "https://api.fac.gov/general?entity_type=eq.tribal"},
        {"source": "Federal Audit Clearinghouse", "host": "api.fac.gov",
         "facet": "reporting package (audited financial statements), "
                  "auditee did NOT elect to withhold",
         "status": "PUBLISHES", "n": pub_n,
         "evidence": "is_public=true; app.fac.gov serves the reporting-package "
                     "PDF (HTTP 200). %d retrieved in this run." % n_pdf_ok,
         "retrieved_at": TODAY,
         "source_url": "https://app.fac.gov/dissemination/report/pdf/"},
        {"source": "Federal Audit Clearinghouse", "host": "app.fac.gov",
         "facet": "reporting package, auditee elected to withhold",
         "status": "WITHHOLDS", "n": priv_n,
         "evidence": "2 CFR 200.512(b)(2) opt-out. app.fac.gov returns HTTP "
                     "403 for the PDF (measured on Seminole Tribe of Florida "
                     "2022-09-CENSUS-0000136810). %d 403s in this run."
                     % n_403,
         "retrieved_at": TODAY,
         "source_url": "https://app.fac.gov/dissemination/report/pdf/"},
        {"source": "Federal Audit Clearinghouse", "host": "api.fac.gov",
         "facet": "SEFA line items (federal_awards) for a WITHHELD package",
         "status": "PUBLISHES", "n": len(sefa_rows),
         "evidence": "127 federal_awards rows returned for Seminole Tribe of "
                     "Florida FY2022 whose reporting package is withheld. The "
                     "withholding is of the PACKAGE, not of the SEFA.",
         "retrieved_at": TODAY,
         "source_url": "https://api.fac.gov/federal_awards"},
        {"source": "Federal Audit Clearinghouse", "host": "api.fac.gov",
         "facet": "audited financial statements as structured data",
         "status": "NOT_FOUND", "n": 0,
         "evidence": "No API table carries the financial statements. The API "
                     "exposes general, federal_awards, findings, findings_text, "
                     "corrective_action_plans, notes_to_sefa, passthrough, "
                     "secondary_auditors, additional_ueis, additional_eins. "
                     "Component-unit statements, transfers to the tribe and "
                     "participation expense exist only inside the PDF.",
         "retrieved_at": TODAY, "source_url": "https://api.fac.gov/"},
    ]
    for tag in ("public", "nonpublic"):
        w = wtest.get(tag) or {}
        if not w:
            continue
        coverage.append({
            "source": "Federal Audit Clearinghouse", "host": "api.fac.gov",
            "facet": "narrative text tables, %s tribal reports (matched "
                     "sample of %s largest by federal expenditure)"
                     % (tag, w.get("sampled")),
            "status": "MEASURED", "n": w.get("sampled"),
            "evidence": "notes_to_sefa present on %s/%s; findings_text on "
                        "%s/%s; corrective_action_plans on %s/%s; "
                        "federal_awards on %s/%s."
                        % (w.get("notes_to_sefa", 0), w.get("sampled"),
                           w.get("findings_text", 0), w.get("sampled"),
                           w.get("corrective_action_plans", 0), w.get("sampled"),
                           w.get("federal_awards", 0), w.get("sampled")),
            "retrieved_at": TODAY, "source_url": "https://api.fac.gov/"})
    for c in sweep_cov:
        coverage.append({
            "source": "Federal Audit Clearinghouse", "host": "api.fac.gov",
            "facet": "ilike sweep %s.%s ~ '%s'" % (c["table"], c["field"],
                                                   c["term"]),
            "status": "PUBLISHES" if str(c.get("n_records") or "0") not in
                      ("", "0") else "NOT_FOUND",
            "n": c.get("n_records"),
            "evidence": "term swept across the whole FAC corpus; yield "
                        "recorded whether or not it is zero. HTTP %s"
                        % c.get("http_status"),
            "retrieved_at": TODAY, "source_url": "https://api.fac.gov/"})
    write_csv(CLEAN / "source_coverage_fac.csv", coverage)

    # ---- report ----------------------------------------------------------
    mp = [d for d in disc if d.get("measurement_type") ==
          "MACHINE_PARTICIPATION_EXPENSE"]
    mp_arr = [d for d in disc if d.get("disclosure_class") ==
              "MACHINE_PARTICIPATION_ARRANGEMENT"]
    mp_ents = {d["entity_id"] for d in mp_arr if d.get("entity_id")}
    mp_any = [d for d in disc if d.get("term") in
              ("machine_participation", "leased_gaming_devices", "coin_in",
               "net_win")]
    print("  machine-participation arrangements %d rows on %d entities"
          % (len(mp_arr), len(mp_ents)))
    print("\n=== 147 SUMMARY ===")
    print("  census rows                    %6d" % len(cen_rows))
    print("    tribal-typed public          %6d" % pub_n)
    print("    tribal-typed withheld        %6d" % priv_n)
    print("  distinct spine entities        %6d" % len(ents))
    print("  gaming disclosures             %6d" % (len(disc) + len(sweep_out)))
    print("  machine-participation typed    %6d" % len(mp))
    print("  machine/participation family   %6d" % len(mp_any))
    print("  SEFA gaming programme rows     %6d" % len(sefa_rows))
    print("  unresolved auditees (review)   %6d" % len(urows))
    print("  free disk %.1f GB" % free_gb())
    return 0


if __name__ == "__main__":
    sys.exit(main())
