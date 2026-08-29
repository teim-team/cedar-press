"""366 - CourtListener / RECAP as a TARGETED ADJUDICATION TOOL, not a sweep.

WHY THIS SOURCE, AND WHY IT IS DIFFERENT FROM EVERYTHING ELSE CEDAR HOLDS
-------------------------------------------------------------------------
Almost every ownership fact in this project is a SELF-CERTIFICATION.  A SAM
socio-economic flag is the firm describing itself; `docs/PULL_DISCIPLINE.md`
records Goldbelt Raven, an ANC subsidiary, certifying
`alaskanNativeCorporationOwnedFirm = NO`.  Tier A requires a leg that is NOT
the firm.

A federal court filing is one of very few such legs.  A docket's `party` array
is an INDEPENDENT THIRD PARTY - the clerk of court - naming a subsidiary and
its corporate parent together, on the record, on a date.

`docs/UNTAPPED_FREE_SOURCES_2026-08-26.md` section A already proved the shape
on a named Cedar defect row: `Pease v. Sitnasuak Native Corporation`
(D.P.R. 3:16-cv-01562) returns a party array carrying `Aurora Industries, LLC`,
`SNC Technical Services, LLC`, `Sitnasuak Native Corporation` and
`SNC Manufacturing, LLC` - operating company and VILLAGE CORPORATION as
co-defendants, village GOVERNMENT absent.  That is independent corroboration of
`docs/ANCSA_OWNERSHIP_RULING.md` rule 1.

THE RATE LIMIT DEFINES THE DESIGN
---------------------------------
The free authenticated tier is **5 requests/minute, 50/hour, 125/day**.  That
is not a sweep budget.  It is roughly one hundred QUESTIONS, so every request
has to be aimed at a question whose answer is worth a dollar figure.  The
targets are ranked by unattributed obligations before a single socket opens,
and the spend is metered in a persistent ledger that survives a killed run.

`docs/BLOCKED_SOURCE_BYPASS_2026-08-26.md` correctly recorded CourtListener as
`ROBOTS_FORBIDDEN` for SCRAPING - their robots.txt ends `Disallow: /` and names
`ClaudeBot` explicitly.  That still stands.  Their own header says *"We also
have an extensive REST API"*, and the owner has now supplied a token, so the
API is the SANCTIONED route and supersedes that verdict FOR THE API ONLY.
**This script never touches the HTML site.**

THE VERIFICATION RULE, PAID FOR TWICE ALREADY
---------------------------------------------
A search result's `title` / `caseName` is NOT the speaker.
  * `code/221`'s regulations.gov sample: two "Torres Martinez" hits were a
    SURNAME PAIR inside mass-comment campaigns, nothing to do with the Torres
    Martinez Desert Cahuilla Indians.
  * `code/219`'s RECAP sample: `Seminole v. Berkebile` is a prisoner
    civil-rights case; "Seminole" is a surname.
So a hit counts only when the queried name appears in the docket's own `party`
array.  `match_class` separates VERIFIED_PARTY / NAME_IN_CAPTION_ONLY, and
nothing downstream may consume the second as a link.

AND A CAPTION IS A RELATIONSHIP, NOT AN OWNERSHIP
-------------------------------------------------
Co-defendants are joined for many reasons - joint employer, alter ego, a
staffing contract, an insurer.  This script therefore types what the document
SUPPORTS and refuses to type more:

    NAMED_AS_PARENT      the record itself names one party as the other's
                         parent / member / owner
    CO_DEFENDANT_ONLY    both are in the party array; the relationship is
                         not stated in what we retrieved
    ALLEGED_IN_COMPLAINT an allegation.  An allegation is not a finding.
    STIPULATED           the parties agreed it on the record
    COURT_FOUND          the court found it

Only the last two, and NAMED_AS_PARENT off a corporate-disclosure statement,
are ownership evidence.  Typing is a HUMAN step in `code/368`; this script
stages the verbatim strings and assigns nothing.

WHAT IT REFUSES
---------------
  * No shared table.  Everything stages to `review/`.
  * ONE poller.  `logs/_HOSTLOCK_www.courtlistener.com.json`.
  * The token is read from the environment / .env.local / HKCU and is NEVER
    written to a file, a log, or a logged URL.  `redact()` is applied to every
    string that leaves this process.
  * Deterministic keys only (class 7).  Row keys are the SOURCE's own docket
    id, never a position and never `hash()`.
  * Retrieved-vs-reported is recorded on every query (class 4): CourtListener
    states `count`, and a query whose retrieved page is short of it is marked
    `PARTIAL`, never `done`.
  * Idempotent (class 5): the spend ledger and the results file are keyed and
    merged, and a re-run with the budget exhausted writes the same file.

py -3 code/366_courtlistener_ownership_adjudication.py targets   # 0 requests
py -3 code/366_courtlistener_ownership_adjudication.py query --max 12
py -3 code/366_courtlistener_ownership_adjudication.py spend     # 0 requests
"""
import argparse
import csv
import datetime
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

csv.field_size_limit(10 ** 8)

ROOT = pathlib.Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = ROOT / "data" / "clean"
REVIEW = ROOT / "review"
LOGS = ROOT / "logs"
RAW = ROOT / "data" / "raw" / "external" / "courtlistener_2026-08-26"
RAW.mkdir(parents=True, exist_ok=True)

SCRIPT = "366_courtlistener_ownership_adjudication.py"
HOST = "www.courtlistener.com"
SEARCH = "https://www.courtlistener.com/api/rest/v4/search/"
UA = ("CedarPress-research/1.0 (+https://cedarpress.co; "
      "elijahsamsonmoreno@gmail.com)")
TODAY = "2026-08-26"

# --- the budget.  These are the published free-tier limits and are the whole
# --- design constraint.  Never raise them to "get more done".
PER_MIN = 5
PER_HOUR = 50
PER_DAY = 125
GAP_S = 60.0 / PER_MIN + 0.6          # 12.6s -> 4.76/min, inside 5/min
RUN_DEADLINE_S = 110 * 60
MAX_CONSEC_REFUSALS = 3

TARGETS = REVIEW / f"courtlistener_targets_{TODAY}.csv"
RESULTS = REVIEW / f"courtlistener_docket_evidence_{TODAY}.csv"
SPEND = RAW / "_request_ledger.json"
START = time.time()


def log(m):
    try:
        print(m, flush=True)
    except UnicodeEncodeError:
        print(m.encode("ascii", "replace").decode(), flush=True)


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())).strip()


# A corporate suffix is not part of the name a clerk types.  `prime_contracts`
# renders `Manu Kai, Llc`; the docket says `Manu Kai LLC` or `Manu Kai, L.L.C.`
# An exact-phrase query on OUR rendering asks the wrong question and spends a
# request to learn nothing.  Strip the suffix, keep the distinguishing stem,
# and verify on the `party` array as always.
SUFFIX = re.compile(
    r"[,\s]+(l\.?l\.?c\.?|inc\.?|incorporated|corp\.?|corporation|"
    r"co\.?|company|ltd\.?|limited|l\.?p\.?|llp|jv|j\.?v\.?)\.?\s*$",
    re.I)


def query_string(name):
    s = (name or "").strip()
    prev = None
    while prev != s:
        prev = s
        s = SUFFIX.sub("", s).strip(" ,.")
    return s or (name or "").strip()


# ------------------------------------------------------------------ token
def get_token():
    """Read the token.  NEVER write it anywhere.

    Three sources, in order.  The owner recorded it as living in the user
    environment and in `.env.local`; on this machine it is a HKCU User
    variable that the current process did not inherit, so the registry read
    is not belt-and-braces, it is the only route that works today.
    """
    t = os.environ.get("COURTLISTENER_API_TOKEN") or os.environ.get("COURTLISTENER_TOKEN")
    if t:
        return t.strip(), "process_env"
    envf = ROOT / ".env.local"
    if envf.exists():
        for line in envf.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line.startswith("COURTLISTENER") and "=" in line:
                return line.split("=", 1)[1].strip().strip('"').strip("'"), ".env.local"
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            for name in ("COURTLISTENER_API_TOKEN", "COURTLISTENER_TOKEN"):
                try:
                    v, _ = winreg.QueryValueEx(k, name)
                    if v:
                        return str(v).strip(), "HKCU_Environment"
                except FileNotFoundError:
                    continue
    except Exception:
        pass
    return "", "NOT_FOUND"


TOKEN, TOKEN_SOURCE = get_token()


def redact(s):
    """Strip the token out of anything that could be printed or written."""
    s = str(s)
    if TOKEN and TOKEN in s:
        s = s.replace(TOKEN, "REDACTED")
    return s


# ------------------------------------------------------------- host lock
def claim_host(note):
    p = LOGS / f"_HOSTLOCK_{HOST}.json"
    if p.exists():
        cur = json.loads(p.read_text(encoding="utf-8"))
        if cur.get("active"):
            queue = cur.get("queue") or []
            queue.append({"script": f"code/{SCRIPT}", "note": note})
            cur["queue"] = queue
            p.write_text(json.dumps(cur, indent=1), encoding="utf-8")
            log(f"HOSTLOCK held by {cur.get('script')}; queued and exiting")
            return False
    p.write_text(json.dumps({
        "host": HOST, "pid": os.getpid(), "script": f"code/{SCRIPT}",
        "started": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "active": True, "queue": [], "note": note,
        "auth": "Token header, value never logged",
        "policy": (f"ONE poller, sequential, >={GAP_S:.1f}s gap; "
                   f"caps {PER_MIN}/min {PER_HOUR}/hr {PER_DAY}/day; "
                   f"RUN_DEADLINE {RUN_DEADLINE_S}s; stop after "
                   f"{MAX_CONSEC_REFUSALS} consecutive refusals"),
        "downloaded_this_run": 0,
        "already_on_disk_skipped": 0,
        "refused_by_host": [],
    }, indent=1), encoding="utf-8")
    return True


def release_host(note, extra=None):
    p = LOGS / f"_HOSTLOCK_{HOST}.json"
    cur = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"host": HOST}
    cur["active"] = False
    cur["released"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    cur["note"] = note
    if extra:
        cur.update(extra)
    p.write_text(json.dumps(cur, indent=1), encoding="utf-8")


# ---------------------------------------------------------- spend ledger
def load_spend():
    if SPEND.exists():
        return json.loads(SPEND.read_text(encoding="utf-8"))
    return {"requests": [], "note": "one entry per REQUEST SENT, token redacted"}


def save_spend(led):
    tmp = SPEND.with_suffix(".json.part")
    tmp.write_text(redact(json.dumps(led, indent=1)), encoding="utf-8")
    tmp.replace(SPEND)


def spent_counts(led):
    now = time.time()
    day = sum(1 for r in led["requests"] if now - r["t"] < 24 * 3600)
    hour = sum(1 for r in led["requests"] if now - r["t"] < 3600)
    minute = sum(1 for r in led["requests"] if now - r["t"] < 60)
    return day, hour, minute


# -------------------------------------------------------------- targets
def build_targets():
    """Rank the questions by dollars BEFORE spending anything.

    Every target carries the QUESTION it is meant to answer, so a request
    that comes back empty is still a recorded answer to a named question
    rather than a blank row.
    """
    out = []

    # ---- P1: the 7 ruled NATIVE with no owner named.  $2,750,399,689.
    bak = (REVIEW / f"ruling_class_only_owner_unnamed_{TODAY}.csv"
                    ".bak_2026-08-26_pre_309_apply_already_ruled_filter_to_review_queues")
    live = REVIEW / f"ruling_class_only_owner_unnamed_{TODAY}.csv"
    src = bak if bak.exists() else live
    n_needs = 0
    for r in csv.DictReader(src.open(encoding="utf-8-sig")):
        if r.get("triage") != "NEEDS_AN_OWNER":
            continue
        n_needs += 1
        out.append({
            "priority": "1_NEEDS_AN_OWNER",
            "query_name": r["awardee_name"],
            "cedar_key": r["subject_key"],
            "usd_at_stake": r["unattributed_usd"],
            "question": "which Native entity owns this firm?",
            "source_row": src.name,
        })
    if n_needs != 7:
        log(f"  !! expected 7 NEEDS_AN_OWNER rows, found {n_needs} in {src.name}")

    # ---- P4: the ANCSA cases the ruling could not close.
    #      Copper River is the RULE_3_CANDIDATE: the owner ruled the BRAND
    #      FAMILY to the Native Village of Eyak (the tribe), while EyakTek /
    #      Eyak Services / Northtide / Solutions71 belong to Eyak Corporation
    #      (the ANC).  One village, both shapes.  A caption naming which legal
    #      person is a party is exactly the per-identifier evidence rule 3
    #      demands and a brand-family ruling cannot supply.
    for nm, q in [
        ("Copper River Information Technology", "which Eyak legal person is the party - the tribe or Eyak Corporation?"),
        ("Copper River Family of Companies", "same"),
        ("EyakTek", "does a caption place EyakTek with Eyak Corporation or with the Native Village of Eyak?"),
        ("Eyak Corporation", "which operating companies appear beside it?"),
        ("Native Village of Eyak", "does the TRIBE ever appear as a corporate party beside an operating company?"),
    ]:
        out.append({"priority": "4_ANCSA_RULE3", "query_name": nm, "cedar_key": "",
                    "usd_at_stake": "", "question": q, "source_row": "docs/ANCSA_OWNERSHIP_RULING.md"})

    # ---- P2: the conflicting rulings a COURT RECORD can actually break.
    #      Most of the 116 are two spellings of one tribal government and a
    #      docket cannot adjudicate a spelling.  These are the ones where two
    #      rulings name two DIFFERENT LEGAL PERSONS.
    for nm, key, q in [
        ("Alaka`i Services Group", "CAGE:8QYZ6 / UEI:EMNDBXF7JSK9",
         "is the firm owned by Alaka`i Foundation, Inc. (NHO-ALAKA1-00) or standalone?"),
        ("St. George Tanaq Corporation", "UEI:DD76ANKVJKY8",
         "REFUSE vs St. George Tanaq Corporation - which legal person?"),
    ]:
        out.append({"priority": "2_CONFLICT", "query_name": nm, "cedar_key": key,
                    "usd_at_stake": "", "question": q,
                    "source_row": f"review/ruling_conflicts_{TODAY}.csv"})

    # ---- P3: high-dollar unattributed clusters, corporate-family names only.
    #      Ranked from prime_contracts.csv itself, so the dollars are the
    #      file's and not a doc's.  A caption resolves a CORPORATE FAMILY; it
    #      does not resolve a one-man firm, so the shortlist is hand-picked
    #      from the ranked list for family-shaped names.
    fam = [
        "Copper River Information Technology",   # already above, dedup handles it
        "Ke`aki Technologies",
        "Nakupuna Solutions",
        "Kapili Services",
        "Polu Kai Services",
        "Kaihonua",
        "Teya Enterprises",
        "T&H Services",
        "Moss Cape",
        "Dawson Technical",
        "Ross Group Construction",
        "ICI Services Corporation",
        "Pelatron",
        "Environet",
        "All Points Logistics",
        "SES-Tech Global Solutions",
        "Aircraft Readiness Alliance",
        "Kuk BRS Alaska Venture",
        "Native Energy & Technology",
        "Native American Services Corporation",
        "Spiral Solutions & Technologies",
    ]
    # DROPPED deliberately, and named rather than silently omitted (class 2c):
    # `Nova Corporation`, `Global Technical Services`, `Clement Group`,
    # `All Cities Enterprises`, `D7, LLC` and `SGS, LLC` are all high-dollar
    # unattributed clusters and all are names too generic for a phrase query -
    # the request would come back full of unrelated defendants and the
    # `party`-array check would reject every one of them.  A request spent to
    # produce a guaranteed rejection is a request not spent on the 7.
    ranked = rank_unattributed()
    for nm in fam:
        usd = ranked.get(norm(nm), "")
        out.append({"priority": "3_UNATTRIBUTED_CLUSTER", "query_name": nm,
                    "cedar_key": "", "usd_at_stake": usd,
                    "question": "which corporate parent does a caption name?",
                    "source_row": "data/clean/prime_contracts.csv attributed_flag=0"})

    # ---- CONTROL.  A name built so that it CANNOT exist.  If this returns a
    #      docket, every positive above is worthless.  `code/219`'s
    #      CONTROL_ABSENT returning 0 is what made its results mean anything;
    #      ProPublica's organizations endpoint is the counter-example, HTTP
    #      200 + "Unknown Organization" for EIN 999999999.
    out.append({"priority": "0_CONTROL_ABSENT",
                "query_name": "Kwithluk Sentinel Holdings Incorporated",
                "cedar_key": "", "usd_at_stake": "",
                "question": "does the API return something for anything?",
                "source_row": "constructed non-entity"})

    seen, dedup = set(), []
    dropped = []
    for t in out:
        k = norm(t["query_name"])
        if k in seen:
            dropped.append(t["query_name"])       # class 2c: NAME what is dropped
            continue
        seen.add(k)
        dedup.append(t)
    if dropped:
        log(f"  deduplicated {len(dropped)} repeated target name(s): {', '.join(dropped)}")
    order = {"0_CONTROL_ABSENT": 0, "1_NEEDS_AN_OWNER": 1, "4_ANCSA_RULE3": 2,
             "2_CONFLICT": 3, "3_UNATTRIBUTED_CLUSTER": 4}
    dedup.sort(key=lambda t: (order[t["priority"]],
                              -float(t["usd_at_stake"] or 0)))
    return dedup


def rank_unattributed():
    """Obligations on attributed_flag = 0 prime rows, by normalised name.

    Reads the PROMOTED table and nothing else (class 1).
    """
    p = CLEAN / "prime_contracts.csv"
    agg = {}
    with p.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("attributed_flag") == "1":
                continue
            k = norm(row.get("awardee_name"))
            if not k:
                continue
            try:
                v = float(row.get("total_obligations") or 0)
            except ValueError:
                v = 0.0
            agg[k] = agg.get(k, 0.0) + v
    return agg


def step_targets():
    tg = build_targets()
    cols = ["priority", "query_name", "cedar_key", "usd_at_stake", "question", "source_row"]
    tmp = TARGETS.with_suffix(".csv.part")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for t in tg:
            w.writerow(t)
    tmp.replace(TARGETS)
    log(f"{len(tg)} targets -> {TARGETS.name}   (0 requests spent)")
    for t in tg[:12]:
        usd = f"${float(t['usd_at_stake'] or 0)/1e6:,.1f}M" if t["usd_at_stake"] else ""
        log(f"  {t['priority']:24s} {t['query_name'][:44]:44s} {usd}")
    return 0


# ---------------------------------------------------------------- fetch
def cl_get(url):
    hdr = {"User-Agent": UA, "Accept": "application/json"}
    if TOKEN:
        hdr["Authorization"] = f"Token {TOKEN}"
    req = urllib.request.Request(url, headers=hdr)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.status, dict(r.headers), json.loads(r.read().decode("utf-8", "replace"))


def step_query(max_requests):
    if not TOKEN:
        log("NO TOKEN. Refusing to run: the anonymous tier is not the sanctioned "
            "route and would 429. Set COURTLISTENER_API_TOKEN.")
        return 2
    log(f"token source: {TOKEN_SOURCE}   (value never printed, never written)")

    targets = list(csv.DictReader(TARGETS.open(encoding="utf-8-sig")))
    have = {}
    if RESULTS.exists():
        for r in csv.DictReader(RESULTS.open(encoding="utf-8-sig")):
            have.setdefault(r["query_name"], []).append(r)
    done_queries = set(have)

    led = load_spend()
    day, hour, _ = spent_counts(led)
    log(f"budget: {day}/{PER_DAY} today, {hour}/{PER_HOUR} this hour")
    room = min(PER_DAY - day, PER_HOUR - hour, max_requests)
    if room <= 0:
        log("no budget left in this window; nothing sent")
        return 0

    todo = [t for t in targets if t["query_name"] not in done_queries][:room]
    if not todo:
        log("every target already has a recorded answer; nothing sent")
        return 0

    if not claim_host("targeted RECAP ownership adjudication, metered 5/min 50/hr 125/day"):
        return 3

    rows = [r for v in have.values() for r in v]
    consec = 0
    sent = 0
    refused = []
    stopped = None
    try:
        for t in todo:
            if time.time() - START > RUN_DEADLINE_S:
                stopped = "RUN_DEADLINE"
                break
            d, h, m = spent_counts(led)
            if d >= PER_DAY:
                stopped = "PER_DAY"
                break
            if h >= PER_HOUR:
                stopped = "PER_HOUR"
                break
            while spent_counts(led)[2] >= PER_MIN:
                time.sleep(2)
            if sent:
                time.sleep(GAP_S)

            q = '"%s"' % query_string(t["query_name"])
            params = {"q": q, "type": "r", "order_by": "dateFiled desc"}
            url = SEARCH + "?" + urllib.parse.urlencode(params)
            led["requests"].append({"t": time.time(),
                                    "iso": datetime.datetime.now(
                                        datetime.timezone.utc).isoformat(),
                                    "target": t["query_name"],
                                    "url": redact(url), "status": "SENT"})
            save_spend(led)
            sent += 1
            try:
                status, hdrs, js = cl_get(url)
                led["requests"][-1]["status"] = status
                consec = 0
            except urllib.error.HTTPError as e:
                led["requests"][-1]["status"] = f"HTTP {e.code}"
                save_spend(led)
                refused.append([t["query_name"], e.code])
                log(f"  {t['query_name'][:44]:44s} HTTP {e.code}")
                consec += 1
                if e.code == 429:
                    log("  429 - honouring a long backoff and stopping this run")
                    stopped = "HTTP_429"
                    break
                if consec >= MAX_CONSEC_REFUSALS:
                    stopped = f"{consec} consecutive refusals"
                    break
                continue
            except Exception as e:
                led["requests"][-1]["status"] = f"ERR {redact(str(e))[:120]}"
                save_spend(led)
                refused.append([t["query_name"], redact(str(e))[:120]])
                consec += 1
                if consec >= MAX_CONSEC_REFUSALS:
                    stopped = f"{consec} consecutive errors"
                    break
                continue

            reported = js.get("count")
            results = js.get("results") or []
            led["requests"][-1]["reported_count"] = reported
            led["requests"][-1]["retrieved"] = len(results)
            save_spend(led)

            (RAW / f"search_{re.sub(r'[^A-Za-z0-9]+', '_', t['query_name'])[:60]}.json"
             ).write_text(redact(json.dumps(js, indent=1)), encoding="utf-8")

            want = norm(t["query_name"])
            n_ver = 0
            if not results:
                rows.append(mkrow(t, None, "NO_DOCKET_RETURNED", reported, len(results)))
            for d0 in results:
                parties = [p for p in (d0.get("party") or []) if p]
                pn = [norm(p) for p in parties]
                hit_party = any(want in p or (p and p in want) for p in pn)
                hit_caption = want in norm(d0.get("caseName"))
                if hit_party:
                    mc = "VERIFIED_PARTY"
                    n_ver += 1
                elif hit_caption:
                    mc = "NAME_IN_CAPTION_ONLY"
                else:
                    mc = "NAME_IN_DOCUMENT_TEXT_ONLY"
                rows.append(mkrow(t, d0, mc, reported, len(results)))
            log(f"  {t['query_name'][:44]:44s} count={reported:<6} "
                f"page={len(results):<3} verified_party={n_ver}"
                f"{'   <-- CONTROL' if t['priority'].startswith('0_') else ''}")
    finally:
        write_results(rows)
        d, h, _ = spent_counts(led)
        release_host(f"{sent} request(s) sent this run; {d}/{PER_DAY} today",
                     {"downloaded_this_run": sent,
                      "already_on_disk_skipped": len(done_queries),
                      "refused_by_host": refused,
                      "stopped_early": stopped,
                      "requests_today": d, "requests_this_hour": h})
    log(f"\n{sent} request(s) sent. stopped_early={stopped}. "
        f"ledger: {d}/{PER_DAY} today, {h}/{PER_HOUR} this hour.")
    return 0


def mkrow(t, d0, match_class, reported, retrieved):
    """One evidence row.  Key is the SOURCE's own docket id - deterministic,
    never positional, never `hash()` (class 7)."""
    d0 = d0 or {}
    parties = [p for p in (d0.get("party") or []) if p]
    did = d0.get("docket_id") or d0.get("id") or ""
    return {
        "docket_id": str(did),
        "query_name": t["query_name"],
        "priority": t["priority"],
        "cedar_key": t["cedar_key"],
        "usd_at_stake": t["usd_at_stake"],
        "question": t["question"],
        "match_class": match_class,
        "case_name": d0.get("caseName", ""),
        "court": d0.get("court", "") or d0.get("court_id", ""),
        "docket_number": d0.get("docketNumber", ""),
        "date_filed": d0.get("dateFiled", "") or "",
        "date_terminated": d0.get("dateTerminated", "") or "",
        "cause": d0.get("cause", "") or "",
        "suit_nature": d0.get("suitNature", "") or "",
        "assigned_to": d0.get("assignedTo", "") or "",
        "party_verbatim": " | ".join(parties),
        "n_parties": len(parties),
        "firm_verbatim": " | ".join([f for f in (d0.get("firm") or []) if f]),
        "docket_url": ("https://www.courtlistener.com" + d0.get("docket_absolute_url", ""))
                      if d0.get("docket_absolute_url") else "",
        "source_reported_count": "" if reported is None else str(reported),
        "retrieved_this_page": str(retrieved),
        "retrieved_vs_reported": ("COMPLETE" if reported is not None and retrieved >= reported
                                  else "PARTIAL_PAGE_1_ONLY"),
        # typed by a human in 368.  NEVER by this script.
        "relationship_type": "",
        "relationship_basis": "",
        "retrieved_date": TODAY,
    }


RESULT_COLS = ["docket_id", "query_name", "priority", "cedar_key", "usd_at_stake",
               "question", "match_class", "case_name", "court", "docket_number",
               "date_filed", "date_terminated", "cause", "suit_nature",
               "assigned_to", "party_verbatim", "n_parties", "firm_verbatim",
               "docket_url", "source_reported_count", "retrieved_this_page",
               "retrieved_vs_reported", "relationship_type",
               "relationship_basis", "retrieved_date"]


def write_results(rows):
    seen, out = set(), []
    for r in rows:
        k = (r["query_name"], r["docket_id"], r["match_class"])
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    out.sort(key=lambda r: (r["priority"], r["query_name"], r["docket_id"]))
    tmp = RESULTS.with_suffix(".csv.part")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=RESULT_COLS)
        w.writeheader()
        for r in out:
            w.writerow({c: r.get(c, "") for c in RESULT_COLS})
    tmp.replace(RESULTS)
    log(f"  wrote {len(out)} evidence row(s) -> {RESULTS.name}")


def step_spend():
    led = load_spend()
    d, h, m = spent_counts(led)
    log(f"requests in ledger: {len(led['requests'])}")
    log(f"  last 24h: {d}/{PER_DAY}")
    log(f"  last 1h:  {h}/{PER_HOUR}")
    log(f"  last 60s: {m}/{PER_MIN}")
    for r in led["requests"][-200:]:
        log(f"  {r['iso'][11:19]}  {str(r.get('status')):10s} "
            f"count={str(r.get('reported_count','')):>8s}  {r['target'][:48]}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["targets", "query", "spend"])
    ap.add_argument("--max", type=int, default=10)
    a = ap.parse_args()
    if a.stage == "targets":
        return step_targets()
    if a.stage == "query":
        return step_query(a.max)
    return step_spend()


if __name__ == "__main__":
    sys.exit(main())
