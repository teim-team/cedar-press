#!/usr/bin/env python3
"""
Cedar Press - 73: Complete Dataset 10 (Bills & Votes).

Three jobs, three switches. Every one of them writes incrementally, because a
killed run must lose nothing (PULL_DISCIPLINE rule 6).

    py -3 code/73_bills_votes_completion.py --rollcalls
    py -3 code/73_bills_votes_completion.py --actions
    py -3 code/73_bills_votes_completion.py --sweep
    py -3 code/73_bills_votes_completion.py --outcomes     (no network; needs --actions first)
    py -3 code/73_bills_votes_completion.py --bridge       (no network; needs --sweep first)


WHY EACH STAGE EXISTS
=====================

--rollcalls  THE QUESTION IS THE MEANING OF THE COUNT
-------------------------------------------------------------------------------
`bill_votes.csv` carried `question` and `result` on 305 of 423 roll calls. A
vote record without its question is a count with no meaning: 245-180 on passage
and 245-180 on a motion to table are opposite political facts.

The 118 blanks are NOT random and they are NOT a scraping failure. They are
exactly the roll calls that predate the official electronic record:

    House   clerk.house.gov/evs begins with calendar year 1990.
            /evs/1989/roll001.xml -> HTTP 404 (probed 2026-08-06).
    Senate  senate.gov LIS roll-call XML begins with the 101st Congress.
            vote_100_2_00001.xml -> 301 to roll-call-vote-not-available.htm.

    House roll calls in this dataset dated before 1990 : 69
    Senate roll calls before the 101st Congress        : 49
                                                  total 118  <- exactly the blanks

Voteview does not populate `vote_question` for those Congresses either, for the
same reason: it ingests the Clerk and LIS feeds. So the instruction "fill them
from clerk.house.gov / senate.gov" cannot be carried out for any of the 118, and
saying so is the finding. What CAN be done, and is done here:

  1. Fetch the official record for all 305 roll calls the sources DO cover and
     VERIFY our yea/nay against it. Disagreement is reported, never silently
     overwritten (`official_*` columns sit beside ours; ours are untouched).
  2. Fill the 118 from the ICPSR roll-call description that Voteview ships as
     `dtl_desc`, which is populated on 100% of Congresses 93-101. That text is
     the question as the Congressional Record put it ("TO SUSPEND THE RULES AND
     PASS H.R. 1234, ..."), so the leading clause is extracted VERBATIM - a
     substring of a sourced field, not a paraphrase - and labelled with a
     `question_source` that says precisely where it came from.
  3. `result` is NOT invented for those 118. yea > nay does not imply passage
     (a suspension motion needs two thirds), so an arithmetic "result" would be
     a guess wearing a fact's clothing. It is backfilled instead by --outcomes,
     from the Congress.gov action recorded on the same date for the same bill,
     and left blank where no such action exists.

--actions / --outcomes  A BILL DYING IN COMMITTEE IS A POLITICAL FACT
-------------------------------------------------------------------------------
Elijah: "we want to keep track of stuff that didnt get a vote."

423 roll calls against 3,000+ bills. The dataset could only see measures that
reached a floor vote, which is the rarest thing a bill can do. `native_bills`
carried a coarse `outcome` derived from `latest_action` alone, and latest_action
cannot tell "reported out of committee, calendared, and never called up" from
"referred and never heard of again" - both end at a committee-shaped string.
Those are different political facts: one is a committee saying yes and a floor
saying nothing, the other is a committee saying nothing.

So --actions pulls the FULL action history per bill from Congress.gov, and
--outcomes classifies from the whole history, recording the action text and date
that establishes each disposition. Where a disposition rests on the ABSENCE of
an action, `disposition_basis` says so in those words.

--sweep / --bridge  NOT ONLY TRIBES
-------------------------------------------------------------------------------
The spine holds 952 entities: 173 ANCSA village corporations, 12 regional
corporations, 31 NHOs, 55 intertribal organisations, 64 state-recognised tribes.
The bill universe was inherited from a build whose inclusion rule was tribal,
so ANCSA amendments, Native Hawaiian health and education programmes and
NAHASDA reauthorisations were under-covered.

--sweep scans the 183,233-bill `all_bill_intros.csv` corpus for those families
and adds what it finds, with the matching phrase recorded per bill. --bridge
then re-keys the enlarged corpus to entities THROUGH THE BRIDGE TABLE. A bill
affects many entities; forcing one `tribe_id` onto it would be a false
attribution dressed as completeness.

GUARDS
------
`resolve_entity` from 33_apply_party_rulings is imported, never re-implemented
(standing rule 8). The free-text scanner from 70_key_unjoined_datasets is
imported whole, with its designator requirement, its compound-name demotion and
its NAME_TRAPS refusal - creek, cherokee, colorado, ojibwe, shawnee, oneida,
apache, central, eagle, river, mountain refuse on their own.

HOSTS
-----
clerk.house.gov, www.senate.gov, api.congress.gov. NOT api.usaspending.gov,
which is held by a subaward puller. One lock file per host under logs/.
"""

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
RAW = CEDAR / "data" / "raw" / "external" / "votingpatterns"
REVIEW = CEDAR / "review"
DOCS = CEDAR / "docs"
LOGS = CEDAR / "logs"
CODE = CEDAR / "code"
TODAY = date.today().isoformat()

csv.field_size_limit(10 ** 8)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

UA = ("CedarPress/1.0 (academic research dataset; "
      "elijahsamsonmoreno@gmail.com)")

# Coverage boundaries of the official electronic roll-call records. Probed
# 2026-08-06; the probe evidence is in docs/BILLS_VOTES_COMPLETION_LOG.md.
HOUSE_EVS_FIRST_YEAR = 1990
SENATE_LIS_FIRST_CONGRESS = 101


# ----------------------------------------------------------------------------
# io helpers
# ----------------------------------------------------------------------------
def rd(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def wr(p, rows, cols=None):
    p = Path(p)
    if not rows:
        return
    cols = cols or list(rows[0].keys())
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


class Appender:
    """Incremental writer. Header written once; every row flushed."""

    def __init__(self, path, cols):
        self.path = Path(path)
        self.cols = cols
        self.path.parent.mkdir(parents=True, exist_ok=True)
        new = not self.path.exists() or self.path.stat().st_size == 0
        self.fh = open(self.path, "a", encoding="utf-8", newline="")
        self.w = csv.DictWriter(self.fh, fieldnames=cols, extrasaction="ignore")
        if new:
            self.w.writeheader()
            self.fh.flush()

    def add(self, row):
        self.w.writerow(row)
        self.fh.flush()

    def close(self):
        self.fh.close()


def backup(p):
    p = Path(p)
    if p.exists():
        b = p.with_suffix(p.suffix + f".bak_{TODAY}_pre73")
        if not b.exists():
            b.write_bytes(p.read_bytes())


# ----------------------------------------------------------------------------
# host lock (PULL_DISCIPLINE rules 1 and 2)
# ----------------------------------------------------------------------------
def running_pids():
    """Command lines of live processes. `ps aux` cannot see these on Windows."""
    import subprocess
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process | "
             "Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"],
            capture_output=True, text=True, timeout=90).stdout
        data = json.loads(out) if out.strip() else []
        if isinstance(data, dict):
            data = [data]
        return {int(d["ProcessId"]): (d.get("CommandLine") or "") for d in data}
    except Exception as e:
        print(f"  ! could not enumerate processes ({e}); assuming none")
        return {}


def claim_host(host, work):
    """Return True if we may poll `host`. Never start a second poller."""
    LOGS.mkdir(exist_ok=True)
    lock = LOGS / f"_HOSTLOCK_{host}.json"
    procs = running_pids()
    if lock.exists():
        try:
            d = json.loads(lock.read_text(encoding="utf-8"))
        except Exception:
            d = {}
        pid = d.get("pid")
        alive = pid in procs
        started = d.get("started", "")
        stale = False
        try:
            stale = (datetime.utcnow()
                     - datetime.fromisoformat(started.replace("Z", ""))).total_seconds() > 6 * 3600
        except Exception:
            pass
        if alive and not stale:
            d.setdefault("queue", []).append(work)
            lock.write_text(json.dumps(d, indent=2), encoding="utf-8")
            print(f"  HOST {host} already held by pid {pid} ({d.get('script')}). "
                  f"Queued our work and exiting - PULL_DISCIPLINE rule 1.")
            return False
        print(f"  stale/dead lock on {host} (pid {pid}, started {started}) - taking over")
    lock.write_text(json.dumps({
        "host": host, "pid": os.getpid(), "script": "code/73_bills_votes_completion.py",
        "started": datetime.utcnow().isoformat() + "Z", "queue": [work]},
        indent=2), encoding="utf-8")
    return True


def release_host(host):
    lock = LOGS / f"_HOSTLOCK_{host}.json"
    if lock.exists():
        try:
            d = json.loads(lock.read_text(encoding="utf-8"))
            if d.get("pid") == os.getpid():
                lock.unlink()
        except Exception:
            pass


# ----------------------------------------------------------------------------
# fetching, with the three failure shapes kept apart (PULL_DISCIPLINE rule 4)
# ----------------------------------------------------------------------------
class Blocked(Exception):
    pass


def fetch(url, tries=4, pause=0.35, timeout=45):
    """-> (body_bytes, status_string). Never raises on a 404: absence is data."""
    delay = 60.0
    for attempt in range(tries):
        t0 = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                       "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
            time.sleep(pause)
            return body, "ok"
        except urllib.error.HTTPError as e:
            if e.code == 404:
                time.sleep(pause)
                return None, "http_404"
            if e.code == 429:
                ra = e.headers.get("Retry-After")
                wait = float(ra) if (ra or "").isdigit() else delay
                print(f"    429 throttle; honouring Retry-After {wait:.0f}s")
                time.sleep(wait)
                delay = min(delay * 2, 1800)
                continue
            if e.code in (500, 502, 503, 504):
                time.sleep(min(5 * (attempt + 1), 30))
                continue
            return None, f"http_{e.code}"
        except Exception as e:
            elapsed = time.time() - t0
            if elapsed < 1.0:
                # instant refusal at the edge - more requests extend it
                print(f"    edge refusal after {elapsed:.2f}s ({type(e).__name__}); "
                      f"backing off {delay:.0f}s")
                time.sleep(delay)
                delay = min(delay * 2, 1800)
                if delay >= 1800:
                    raise Blocked(f"{url}: {e}")
                continue
            time.sleep(min(5 * (attempt + 1), 30))
    return None, "failed_after_retries"


# ============================================================================
# STAGE 1 -- official roll-call records
# ============================================================================
HOUSE_URL = "https://clerk.house.gov/evs/{year}/roll{num:03d}.xml"
SENATE_URL = ("https://www.senate.gov/legislative/LIS/roll_call_votes/"
              "vote{cong}{sess}/vote_{cong}_{sess}_{num:05d}.xml")

VERIFY_COLS = ["vote_id", "chamber", "congress", "session", "rollnumber",
               "clerk_rollnumber", "date", "source_host", "source_url",
               "fetch_status", "official_question", "official_question_detail",
               "official_result", "official_vote_type", "official_legis_num",
               "official_vote_desc", "official_yea", "official_nay",
               "official_present", "official_not_voting",
               "cedar_yea", "cedar_nay", "yea_agrees", "nay_agrees",
               "disagreement_note", "fetched_date"]


def _txt(el, path):
    n = el.find(path)
    if n is None:
        return ""
    return " ".join("".join(n.itertext()).split())


def parse_house(body):
    root = ET.fromstring(body)
    md = root.find("vote-metadata")
    if md is None:
        return None
    out = {
        "official_question": _txt(md, "vote-question"),
        "official_question_detail": "",
        "official_result": _txt(md, "vote-result"),
        "official_vote_type": _txt(md, "vote-type"),
        "official_legis_num": _txt(md, "legis-num"),
        "official_vote_desc": _txt(md, "vote-desc"),
    }
    tot = md.find("vote-totals/totals-by-vote")
    if tot is not None:
        out["official_yea"] = (_txt(tot, "yea-total") or _txt(tot, "aye-total"))
        out["official_nay"] = (_txt(tot, "nay-total") or _txt(tot, "no-total"))
        out["official_present"] = _txt(tot, "present-total")
        out["official_not_voting"] = _txt(tot, "not-voting-total")
    return out


def parse_senate(body):
    root = ET.fromstring(body)
    return {
        "official_question": _txt(root, "question") or _txt(root, "vote_question_text"),
        "official_question_detail": _txt(root, "vote_question_text"),
        "official_result": _txt(root, "vote_result") or _txt(root, "vote_result_text"),
        "official_vote_type": _txt(root, "majority_requirement"),
        "official_legis_num": (_txt(root, "document/document_name")
                               or _txt(root, "amendment/amendment_number")),
        "official_vote_desc": (_txt(root, "vote_document_text")
                               or _txt(root, "vote_title")),
        "official_yea": _txt(root, "count/yeas"),
        "official_nay": _txt(root, "count/nays"),
        "official_present": _txt(root, "count/present"),
        "official_not_voting": _txt(root, "count/absent"),
    }


def stage_rollcalls():
    print("=" * 78)
    print("STAGE --rollcalls : official House Clerk / Senate LIS records")
    print("=" * 78)

    votes = rd(CLEAN / "bill_votes.csv")
    hs = {}
    with open(RAW / "HSall_rollcalls.csv", encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            k = ("H" if r["chamber"] == "House" else "S") + \
                f"{int(r['congress']):03d}-{int(r['rollnumber']):04d}"
            hs[k] = r
    print(f"  bill_votes rows: {len(votes)}   Voteview roll-call index: {len(hs):,}")

    out = CLEAN / "bill_votes_official_verification.csv"
    done = {r["vote_id"] for r in rd(out) if r.get("fetch_status") == "ok"}
    if done:
        print(f"  resuming: {len(done)} roll calls already verified")

    covered, uncovered = [], []
    for v in votes:
        yr = int(v["date"][:4])
        cg = int(v["congress"])
        if v["chamber"] == "House":
            (covered if yr >= HOUSE_EVS_FIRST_YEAR else uncovered).append(v)
        else:
            (covered if cg >= SENATE_LIS_FIRST_CONGRESS else uncovered).append(v)
    print(f"  inside official coverage : {len(covered)}")
    print(f"  outside official coverage: {len(uncovered)}  "
          f"(House pre-{HOUSE_EVS_FIRST_YEAR}, Senate pre-{SENATE_LIS_FIRST_CONGRESS}th)")

    todo = [v for v in covered if v["vote_id"] not in done]
    if todo:
        hosts = ["clerk.house.gov", "www.senate.gov"]
        got = [h for h in hosts if claim_host(h, f"bill_votes verification ({len(todo)} roll calls)")]
        if len(got) < len(hosts):
            print("  ! a required host is held elsewhere; stopping rather than "
                  "starting a second poller")
            for h in got:
                release_host(h)
            return
        app = Appender(out, VERIFY_COLS)
        try:
            n_ok = n_404 = 0
            for i, v in enumerate(todo, 1):
                meta = hs.get(v["vote_id"], {})
                sess = meta.get("session", "")
                clerk = meta.get("clerk_rollnumber", "")
                row = {"vote_id": v["vote_id"], "chamber": v["chamber"],
                       "congress": v["congress"], "session": sess,
                       "rollnumber": v["rollnumber"], "clerk_rollnumber": clerk,
                       "date": v["date"], "cedar_yea": v["yea"],
                       "cedar_nay": v["nay"], "fetched_date": TODAY}
                try:
                    if v["chamber"] == "House":
                        # The Clerk numbers roll calls WITHIN A CALENDAR YEAR and
                        # Voteview numbers them within a Congress. Using Voteview's
                        # number against the Clerk URL silently returns a different
                        # vote - H101-0706 is /evs/1990/roll356.xml, not roll706.
                        if not clerk or clerk in ("", "NA"):
                            row["fetch_status"] = "no_clerk_rollnumber_in_voteview"
                            app.add(row)
                            continue
                        url = HOUSE_URL.format(year=int(v["date"][:4]),
                                               num=int(float(clerk)))
                        row["source_host"] = "clerk.house.gov"
                    else:
                        if not sess or sess in ("", "NA"):
                            row["fetch_status"] = "no_session_in_voteview"
                            app.add(row)
                            continue
                        url = SENATE_URL.format(cong=int(v["congress"]),
                                                sess=int(float(sess)),
                                                num=int(float(clerk or v["rollnumber"])))
                        row["source_host"] = "www.senate.gov"
                    row["source_url"] = url
                    body, st = fetch(url)
                    row["fetch_status"] = st
                    if st == "ok" and body:
                        try:
                            p = (parse_house(body) if v["chamber"] == "House"
                                 else parse_senate(body))
                        except ET.ParseError as e:
                            row["fetch_status"] = f"xml_parse_error:{e}"
                            p = None
                        if p:
                            row.update(p)
                            n_ok += 1
                            for side in ("yea", "nay"):
                                o, c = row.get(f"official_{side}", ""), row[f"cedar_{side}"]
                                row[f"{side}_agrees"] = (
                                    "1" if (o.isdigit() and str(c).isdigit()
                                            and int(o) == int(c)) else
                                    ("0" if o.isdigit() else ""))
                            if row.get("yea_agrees") == "0" or row.get("nay_agrees") == "0":
                                row["disagreement_note"] = (
                                    f"official {row.get('official_yea')}-{row.get('official_nay')} "
                                    f"vs cedar {row['cedar_yea']}-{row['cedar_nay']}")
                    elif st == "http_404":
                        n_404 += 1
                except Blocked as e:
                    print(f"  BLOCKED: {e}")
                    row["fetch_status"] = "edge_block_stopped"
                    app.add(row)
                    break
                app.add(row)
                if i % 25 == 0:
                    print(f"    {i}/{len(todo)}  ok={n_ok} 404={n_404}")
        finally:
            app.close()
            for h in hosts:
                release_host(h)

    ver = {r["vote_id"]: r for r in rd(out)}
    print(f"\n  verification rows on file: {len(ver)}")
    print(f"    fetch_status: {dict(Counter(r['fetch_status'] for r in ver.values()))}")

    apply_official(votes, ver, uncovered)


# --- the ICPSR description -> question, for the 118 with no official record ---
#
# The leading clause of dtl_desc IS the question as the Congressional Record put
# it. Taking a VERBATIM substring keeps this inside the prime directive; writing
# a normalised Clerk-style phrase instead would be a paraphrase of a source that
# does not say it.
QUESTION_CUT = re.compile(
    r"^(.*?)(?:,\s+(?:A BILL|A RESOLUTION|A JOINT RESOLUTION|AN ACT|TO ESTABLISH|"
    r"TO PROVIDE|TO AMEND|TO AUTHORIZE|TO DIRECT|TO REQUIRE|TO MAKE|TO EXTEND)\b|$)",
    re.S)

# Purely descriptive: which family of motion the verbatim clause belongs to.
# Reported in its own column so nothing overwrites the sourced text.
QUESTION_FAMILY = [
    ("On Passage", re.compile(r"\bTO PASS\b|\bON PASSAGE\b|\bTO SUSPEND THE RULES AND PASS\b", re.I)),
    ("On Motion to Suspend the Rules and Pass", re.compile(r"\bTO SUSPEND THE RULES AND PASS\b", re.I)),
    ("On Agreeing to the Resolution", re.compile(r"\bTO AGREE TO H\.? ?RES\b|\bTO ADOPT H\.? ?RES\b", re.I)),
    ("On Ordering the Previous Question", re.compile(r"\bPREVIOUS QUESTION\b", re.I)),
    ("On Agreeing to the Amendment", re.compile(r"\bTO AMEND\b.*\bSO AS TO\b|\bTO ADOPT THE AMENDMENT\b|\bAMENDMENT\b", re.I)),
    ("On the Conference Report", re.compile(r"\bCONFERENCE REPORT\b", re.I)),
    ("On the Motion to Table", re.compile(r"\bTO TABLE\b|\bTO LAY ON THE TABLE\b", re.I)),
    ("On the Motion to Recommit", re.compile(r"\bTO RECOMMIT\b", re.I)),
    ("On Overriding the Veto", re.compile(r"\bVETO\b", re.I)),
    ("On the Motion to Proceed", re.compile(r"\bTO PROCEED\b|\bTO TAKE UP\b", re.I)),
    ("On Cloture", re.compile(r"\bCLOTURE\b", re.I)),
    ("On Concurring", re.compile(r"\bTO CONCUR\b", re.I)),
    ("On Confirmation", re.compile(r"\bTO CONFIRM\b", re.I)),
]


def question_from_dtl(dtl):
    if not dtl or not dtl.strip():
        return "", ""
    s = " ".join(dtl.split())
    m = QUESTION_CUT.match(s)
    clause = (m.group(1) if m else s).strip().rstrip(",.")
    # A clause that swallowed the whole description is not a question; keep the
    # first sentence only, still verbatim.
    if len(clause) > 240:
        clause = clause[:240].rsplit(" ", 1)[0]
    fam = ""
    for lab, rx in QUESTION_FAMILY:
        if rx.search(clause):
            fam = lab
            break
    return clause, fam


NO_OFFICIAL = ("no_official_electronic_record: House EVS begins 1990, "
               "Senate LIS begins the 101st Congress")
NO_RESULT_REASON = (
    NO_OFFICIAL + "; NOT derived from yea>nay - a suspension motion needs two "
    "thirds, so arithmetic would be a guess. Recovered by --outcomes only where "
    "a Congress.gov action names THIS roll call's own yea-nay tally.")


def apply_official(votes, ver, uncovered):
    """Write official_* alongside ours. Never overwrite a sourced count."""
    print("\n  applying to bill_votes.csv ...")
    backup(CLEAN / "bill_votes.csv")

    dtl = {}
    with open(RAW / "HSall_rollcalls.csv", encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            k = ("H" if r["chamber"] == "House" else "S") + \
                f"{int(r['congress']):03d}-{int(r['rollnumber']):04d}"
            dtl[k] = r.get("dtl_desc") or ""

    unc = {v["vote_id"] for v in uncovered}
    n_q_official = n_r_official = n_q_icpsr = 0
    disagree = []
    for v in votes:
        o = ver.get(v["vote_id"], {})
        v["official_source_url"] = o.get("source_url", "")
        v["official_question"] = o.get("official_question", "")
        v["official_result"] = o.get("official_result", "")
        v["official_yea"] = o.get("official_yea", "")
        v["official_nay"] = o.get("official_nay", "")
        v["official_record_status"] = (
            o.get("fetch_status", "") if o else
            (NO_OFFICIAL if v["vote_id"] in unc else "not_fetched"))
        v["counts_agree_with_official"] = (
            "1" if (o.get("yea_agrees") == "1" and o.get("nay_agrees") == "1")
            else ("0" if o.get("disagreement_note") else ""))
        if o.get("disagreement_note"):
            disagree.append((v["vote_id"], v["chamber"], v["date"],
                             o["disagreement_note"], o.get("source_url", "")))

        if not (v.get("question") or "").strip():
            if o.get("official_question"):
                v["question"] = o["official_question"]
                v["question_source"] = "official_" + (
                    "house_clerk_evs_xml" if v["chamber"] == "House"
                    else "senate_lis_roll_call_xml")
                n_q_official += 1
            elif v["vote_id"] in unc:
                q, fam = question_from_dtl(dtl.get(v["vote_id"], ""))
                if q:
                    v["question"] = q
                    v["question_family"] = fam
                    v["question_source"] = (
                        "icpsr_rollcall_description_verbatim_via_voteview_dtl_desc; "
                        + NO_OFFICIAL)
                    n_q_icpsr += 1
        if not (v.get("result") or "").strip():
            if o.get("official_result"):
                v["result"] = o["official_result"]
                v["result_source"] = "official_" + (
                    "house_clerk_evs_xml" if v["chamber"] == "House"
                    else "senate_lis_roll_call_xml")
                n_r_official += 1
            elif v["vote_id"] in unc:
                v["result_source"] = NO_RESULT_REASON
        v.setdefault("question_family", "")

    cols = list(votes[0].keys())
    for c in ["question_family", "official_source_url", "official_question",
              "official_result", "official_yea", "official_nay",
              "official_record_status", "counts_agree_with_official"]:
        if c not in cols:
            cols.append(c)
    wr(CLEAN / "bill_votes.csv", votes, cols)

    filled = sum(1 for v in votes if (v.get("question") or "").strip())
    print(f"    question filled from the official record : {n_q_official}")
    print(f"    question filled from the ICPSR description: {n_q_icpsr}")
    print(f"    result   filled from the official record : {n_r_official}")
    print(f"    question populated overall: {filled}/{len(votes)}")
    print(f"    result   populated overall: "
          f"{sum(1 for v in votes if (v.get('result') or '').strip())}/{len(votes)}")

    if disagree:
        print(f"\n  !! COUNT DISAGREEMENTS AGAINST THE OFFICIAL RECORD: {len(disagree)}")
        for d in disagree[:20]:
            print(f"     {d[0]} {d[2]} {d[3]}")
        wr(REVIEW / f"bill_votes_count_disagreements_{TODAY}.csv",
           [{"vote_id": a, "chamber": b, "date": c, "note": d, "source_url": e}
            for a, b, c, d, e in disagree])
    else:
        print("\n  no count disagreements against the official record.")


# ============================================================================
# STAGE 2 -- Congress.gov action histories
# ============================================================================
CONGRESS_BASE = "https://api.congress.gov/v3"
ENVFILE = Path(r"C:\Users\esm247\Desktop\votingpatterns\.env")


def congress_key():
    k = os.environ.get("CONGRESS_API_KEY", "").strip()
    if k:
        return k
    if ENVFILE.exists():
        for line in ENVFILE.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"\s*(?:export\s+)?CONGRESS_API_KEY\s*=\s*['\"]?([^'\"\s]+)", line)
            if m:
                return m.group(1)
    return ""


ACTION_COLS = ["bill_id", "congress", "bill_type", "number", "action_date",
               "action_text", "action_type", "action_code", "source_system",
               "committee_names", "recorded_vote_chamber", "recorded_vote_number",
               "recorded_vote_date", "recorded_vote_url", "fetched_date"]

API_TYPES = {"hr", "s", "hres", "sres", "hjres", "sjres", "hconres", "sconres"}


def stage_actions(limit=None):
    print("=" * 78)
    print("STAGE --actions : Congress.gov full action histories")
    print("=" * 78)
    key = congress_key()
    if not key:
        print("  no CONGRESS_API_KEY; cannot pull actions.")
        return
    print("  API key loaded (value not logged).")

    bills = rd(CLEAN / "native_bills.csv")
    tgt = [b for b in bills if b.get("bill_type") in API_TYPES and b.get("number")]
    skipped = len(bills) - len(tgt)
    print(f"  bills: {len(bills):,}   API-servable: {len(tgt):,}   "
          f"unservable bill_type: {skipped}")

    logp = CLEAN / "_bill_actions_fetch_log.csv"
    done = {r["bill_id"] for r in rd(logp)}
    todo = [b for b in tgt if b["bill_id"] not in done]
    if limit:
        todo = todo[:limit]
    print(f"  already fetched: {len(done):,}   to fetch: {len(todo):,}")
    if not todo:
        return

    if not claim_host("api.congress.gov", f"bill actions ({len(todo)} bills)"):
        return

    app = Appender(CLEAN / "_bill_actions.csv", ACTION_COLS)
    lg = Appender(logp, ["bill_id", "congress", "bill_type", "number", "status",
                         "n_actions", "fetched_date"])
    try:
        n_act = 0
        for i, b in enumerate(todo, 1):
            url = (f"{CONGRESS_BASE}/bill/{int(b['congress'])}/{b['bill_type']}/"
                   f"{b['number']}/actions")
            acts, status, offset = [], "ok", 0
            while True:
                q = urllib.parse.urlencode({"format": "json", "limit": 250,
                                            "offset": offset, "api_key": key})
                body, st = fetch(url + "?" + q, pause=0.35)
                if body is None:
                    status = st
                    break
                try:
                    d = json.loads(body.decode("utf-8"))
                except Exception as e:
                    status = f"json_error:{e}"
                    break
                got = d.get("actions", [])
                acts.extend(got)
                tot = (d.get("pagination") or {}).get("count", len(acts))
                offset += 250
                if offset >= tot or not got:
                    break
            for a in acts:
                rv = (a.get("recordedVotes") or [{}])
                rv = rv[0] if rv else {}
                app.add({
                    "bill_id": b["bill_id"], "congress": b["congress"],
                    "bill_type": b["bill_type"], "number": b["number"],
                    "action_date": a.get("actionDate", ""),
                    "action_text": " ".join((a.get("text") or "").split()),
                    "action_type": a.get("type", ""),
                    "action_code": a.get("actionCode", ""),
                    "source_system": ((a.get("sourceSystem") or {}).get("name", "")),
                    "committee_names": "|".join(
                        c.get("name", "") for c in (a.get("committees") or [])),
                    "recorded_vote_chamber": rv.get("chamber", ""),
                    "recorded_vote_number": rv.get("rollNumber", ""),
                    "recorded_vote_date": rv.get("date", ""),
                    "recorded_vote_url": rv.get("url", ""),
                    "fetched_date": TODAY})
            n_act += len(acts)
            lg.add({"bill_id": b["bill_id"], "congress": b["congress"],
                    "bill_type": b["bill_type"], "number": b["number"],
                    "status": status if acts or status != "ok" else "zero_actions_reported",
                    "n_actions": len(acts), "fetched_date": TODAY})
            if i % 100 == 0:
                print(f"    {i}/{len(todo)} bills; {n_act:,} actions")
    except Blocked as e:
        print(f"  BLOCKED: {e}")
    finally:
        app.close()
        lg.close()
        release_host("api.congress.gov")
    print(f"  done. actions on file: {sum(1 for _ in rd(CLEAN / '_bill_actions.csv')):,}")


META_COLS = ["bill_id", "congress", "bill_type", "number", "title",
             "policy_area", "sponsor", "sponsor_bioguide_id", "introduced_date",
             "latest_action_text", "latest_action_date", "status", "fetched_date"]


def stage_titles():
    """136 bills carry a roll call but no title, because they predate the
    all_bill_intros corpus (which starts at the 103rd Congress). A bill with no
    title cannot be entity-keyed at all - the bridge scans titles - so this is
    the single cheapest way to reach more entities."""
    print("=" * 78)
    print("STAGE --titles : backfill titles for bills the corpus never carried")
    print("=" * 78)
    key = congress_key()
    if not key:
        print("  no CONGRESS_API_KEY; cannot pull.")
        return
    bills = rd(CLEAN / "native_bills.csv")
    need = [b for b in bills if not (b.get("title") or "").strip()
            and b.get("bill_type") in API_TYPES]
    unservable = [b for b in bills if not (b.get("title") or "").strip()
                  and b.get("bill_type") not in API_TYPES]
    outp = CLEAN / "_bill_metadata_backfill.csv"
    done = {r["bill_id"] for r in rd(outp)}
    todo = [b for b in need if b["bill_id"] not in done]
    print(f"  titleless bills: {len(need) + len(unservable)}   API-servable: {len(need)}"
          f"   unservable bill_type: {len(unservable)}"
          f" ({sorted({b['bill_type'] for b in unservable})})")
    print(f"  to fetch: {len(todo)}")

    if todo:
        if not claim_host("api.congress.gov", f"bill titles ({len(todo)})"):
            return
        app = Appender(outp, META_COLS)
        try:
            for i, b in enumerate(todo, 1):
                url = (f"{CONGRESS_BASE}/bill/{int(b['congress'])}/{b['bill_type']}/"
                       f"{b['number']}?" +
                       urllib.parse.urlencode({"format": "json", "api_key": key}))
                body, st = fetch(url, pause=0.35)
                row = {"bill_id": b["bill_id"], "congress": b["congress"],
                       "bill_type": b["bill_type"], "number": b["number"],
                       "status": st, "fetched_date": TODAY}
                if body:
                    try:
                        d = (json.loads(body.decode("utf-8")) or {}).get("bill", {})
                    except Exception as e:
                        d, row["status"] = {}, f"json_error:{e}"
                    la = d.get("latestAction") or {}
                    sp = (d.get("sponsors") or [{}])[0] if d.get("sponsors") else {}
                    row.update({
                        "title": " ".join((d.get("title") or "").split()),
                        "policy_area": (d.get("policyArea") or {}).get("name", ""),
                        "sponsor": sp.get("fullName", ""),
                        "sponsor_bioguide_id": sp.get("bioguideId", ""),
                        "introduced_date": d.get("introducedDate", ""),
                        "latest_action_text": " ".join((la.get("text") or "").split()),
                        "latest_action_date": la.get("actionDate", "")})
                app.add(row)
                if i % 25 == 0:
                    print(f"    {i}/{len(todo)}")
        except Blocked as e:
            print(f"  BLOCKED: {e}")
        finally:
            app.close()
            release_host("api.congress.gov")

    meta = {r["bill_id"]: r for r in rd(outp) if (r.get("title") or "").strip()}
    n = 0
    for b in bills:
        m = meta.get(b["bill_id"])
        if not m or (b.get("title") or "").strip():
            continue
        b["title"] = m["title"]
        for src, dst in (("policy_area", "policy_area"), ("sponsor", "sponsor"),
                         ("sponsor_bioguide_id", "sponsor_bioguide_id"),
                         ("introduced_date", "introduced_date"),
                         ("latest_action_text", "latest_action"),
                         ("latest_action_date", "latest_action_date")):
            if m.get(src) and not (b.get(dst) or "").strip():
                b[dst] = m[src]
        b["record_basis"] = ((b.get("record_basis") or "")
                             + " + congress_gov_bill_endpoint_title_backfill").strip(" +")
        n += 1
    if n:
        backup(CLEAN / "native_bills.csv")
        wr(CLEAN / "native_bills.csv", bills, list(bills[0].keys()))
    print(f"  titles written back into native_bills.csv: {n}")
    print(f"  bills still without a title: "
          f"{sum(1 for b in bills if not (b.get('title') or '').strip())}")


# ============================================================================
# STAGE 3 -- disposition classification (no network)
# ============================================================================
#
# Ordered most-final first. Each pattern names the fact it establishes, and the
# classifier records the action text + date that matched, so every row can be
# audited back to one sentence from Congress.gov.
DISPOSITION_RULES = [
    ("enacted", re.compile(
        r"became public law|became private law|public law no|signed by president", re.I)),
    ("veto-overridden", re.compile(
        r"passed (house|senate) over veto|veto overridden", re.I)),
    ("vetoed", re.compile(r"\bvetoed by president\b|pocket vetoed", re.I)),
    ("passed-both-chambers-not-enacted", re.compile(
        r"presented to president|cleared for white house", re.I)),
    ("passed-one-chamber", re.compile(
        r"^passed (house|senate)|passed/agreed to in (house|senate)|"
        r"^agreed to in (house|senate)|resolution agreed to in (house|senate)|"
        r"received in (the )?(senate|house)|held at the desk|"
        r"message on (senate|house) action (sent|received)", re.I)),
    ("floor-vote-failed", re.compile(
        r"failed of passage|failed to pass|motion to suspend the rules and pass.*(fail|reject)|"
        r"failed of adoption|rejected by (yea|recorded|the yeas)|"
        r"on passage.*failed|cloture (motion )?(on the motion to proceed )?(was )?(not invoked|rejected)", re.I)),
    ("withdrawn", re.compile(r"\bwithdrawn by (sponsor|author)\b|by unanimous consent.*withdrawn", re.I)),
    ("superseded-by-another-measure", re.compile(
        r"for further action see|provisions of .* incorporated in|"
        r"laid on the table.*(companion|similar) measure", re.I)),
    # Calendared but never called up. In the House this follows a report; in
    # the Senate a bill can reach the calendar under Rule XIV WITHOUT ever
    # being referred to a committee, so this is kept distinct from "reported".
    ("placed-on-calendar-never-voted", re.compile(
        r"placed on .{0,40}calendar|returned to the calendar", re.I)),
    ("reported-from-committee-never-voted", re.compile(
        r"^reported (originally |to (house|senate) )?(by|from)|"
        r"^committee on .* reported|ordered to be reported|"
        r"reported \(amended\)|reported with(out)? amendment|"
        r"filed written report|submitted written report|"
        r"star print ordered on (the )?(report|bill|joint resolution)|"
        r"errata sheet on written report|written report no\.", re.I)),
    # The committee engaged and never reported. A different fact from silence,
    # and the one a lobbying user asks about next. Covers hearings, markup,
    # subcommittee forwarding, granted extensions and executive comments -
    # every recorded sign that the committee took the bill up.
    ("committee-acted-never-reported", re.compile(
        r"hearings held|hearings printed|hearing scheduled|"
        r"committee consideration and mark.?up session|markup session|"
        r"forwarded by subcommittee to full committee|"
        r"granted an extension for further consideration|"
        r"executive comment received", re.I)),
    ("referred-and-died-in-committee", re.compile(
        r"referred to (the )?(house |senate )?committee|referred to the subcommittee|"
        r"referred to subcommittee|^introduced in (house|senate)|"
        r"read twice and referred|^read twice|"
        r"^sponsor introductory remarks|executive comment requested|"
        r"referred to department of|^referred to (house|senate) ", re.I)),
]

FINALITY = {"enacted": 100, "veto-overridden": 95, "vetoed": 90,
            "passed-both-chambers-not-enacted": 80, "passed-one-chamber": 70,
            "floor-vote-failed": 60, "withdrawn": 55,
            "superseded-by-another-measure": 50,
            "placed-on-calendar-never-voted": 35,
            "reported-from-committee-never-voted": 30,
            "committee-acted-never-reported": 20,
            "referred-and-died-in-committee": 10}

NEVER_VOTED = {"placed-on-calendar-never-voted",
               "reported-from-committee-never-voted",
               "committee-acted-never-reported",
               "referred-and-died-in-committee"}

# Congress -> last calendar year. 119th runs to Jan 2027.
LAST_COMPLETE_CONGRESS = 118


def stage_outcomes():
    print("=" * 78)
    print("STAGE --outcomes : one row per bill, with its final disposition")
    print("=" * 78)

    bills = rd(CLEAN / "native_bills.csv")
    acts = defaultdict(list)
    for a in rd(CLEAN / "_bill_actions.csv"):
        acts[a["bill_id"]].append(a)
    fetchlog = {r["bill_id"]: r for r in rd(CLEAN / "_bill_actions_fetch_log.csv")}
    print(f"  bills {len(bills):,}   bills with an action history "
          f"{len(acts):,}   fetch-log rows {len(fetchlog):,}")

    votes_by_bill = defaultdict(list)
    for v in rd(CLEAN / "bill_votes.csv"):
        if v.get("bill_id"):
            votes_by_bill[v["bill_id"]].append(v)

    bridge = defaultdict(set)
    for r in rd(CLEAN / "native_bills_entity_bridge.csv"):
        bridge[r["bill_id"]].add(r["tribe_id"])

    rows = []
    stat = Counter()
    for b in bills:
        bid = b["bill_id"]
        aa = sorted(acts.get(bid, []), key=lambda r: (r["action_date"] or ""))
        best = None                     # (finality, disposition, text, date)
        for a in aa:
            t = a["action_text"]
            for disp, rx in DISPOSITION_RULES:
                if rx.search(t):
                    f = FINALITY[disp]
                    if best is None or f > best[0]:
                        best = (f, disp, t, a["action_date"])
                    break

        n_rc = len(votes_by_bill.get(bid, []))
        floor_votes = ";".join(v["vote_id"] for v in votes_by_bill.get(bid, []))

        if best:
            disp, txt, dt = best[1], best[2], best[3]
            basis = "congress_gov_action_text"
            # A committee report with no floor action after it is the whole
            # point of this file: committee said yes, floor said nothing.
            if disp in NEVER_VOTED:
                basis = ("congress_gov_action_text; this is the MOST FINAL "
                         "action in the bill's full history - the disposition "
                         "is INFERRED FROM THE ABSENCE of any later passage, "
                         "failure, withdrawal or enactment action, not from a "
                         "statement that the bill died")
        elif aa:
            disp, txt, dt = "unclassified", aa[-1]["action_text"], aa[-1]["action_date"]
            basis = "congress_gov_action_text matched no disposition rule"
        else:
            la = (b.get("latest_action") or "").strip()
            st = (fetchlog.get(bid, {}) or {}).get("status", "not_fetched")
            if la:
                hit = next((d for d, rx in DISPOSITION_RULES if rx.search(la)), "")
                disp = hit or "unclassified"
                txt, dt = la, b.get("latest_action_date", "")
                basis = ("native_bills.latest_action (no action history "
                         f"available from Congress.gov: {st})")
            else:
                disp, txt, dt = "no-action-record", "", ""
                basis = (f"NO ACTION RECORD AT ALL (Congress.gov: {st}). This is "
                         "not evidence the bill died - it is evidence we have no "
                         "record of what happened to it.")

        if disp in NEVER_VOTED and int(b["congress"]) > LAST_COMPLETE_CONGRESS:
            disp = "pending-in-committee"
            basis += ("; congress " + str(b["congress"]) +
                      " is still in session, so no death can be inferred")

        # A recorded floor vote that failed outranks a stale committee string.
        if n_rc and disp in (NEVER_VOTED | {"pending-in-committee",
                                            "unclassified"}):
            disp = "floor-vote-held-outcome-unresolved"
            basis += (f"; overridden by {n_rc} recorded roll call(s) in "
                      "bill_votes.csv - a bill with a roll call did reach a floor")

        stat[disp] += 1
        rows.append({
            "bill_id": bid, "congress": b["congress"], "chamber": b["chamber"],
            "bill_type": b["bill_type"], "number": b["number"],
            "title": b.get("title", ""), "policy_area": b.get("policy_area", ""),
            "bill_scope": b.get("bill_scope", ""),
            "introduced_date": b.get("introduced_date", ""),
            "sponsor": b.get("sponsor", ""),
            "disposition": disp,
            "disposition_action_text": txt,
            "disposition_action_date": dt,
            "disposition_basis": basis,
            "reached_floor_vote": "1" if n_rc else "0",
            "n_rollcalls": str(n_rc),
            "rollcall_vote_ids": floor_votes,
            "n_actions_on_record": str(len(aa)),
            "first_action_date": aa[0]["action_date"] if aa else "",
            "last_action_date": aa[-1]["action_date"] if aa else "",
            "n_entities_in_bridge": str(len(bridge.get(bid, ()))),
            "entity_ids": "|".join(sorted(bridge.get(bid, ()))),
            "outcome_prior_build": b.get("outcome", ""),
            "source": "Congress.gov API v3 /bill/{congress}/{type}/{number}/actions",
            "build_date": TODAY,
        })

    wr(CLEAN / "native_bill_outcomes.csv", rows)
    print(f"  WROTE native_bill_outcomes.csv  rows={len(rows):,}")
    for k, v in sorted(stat.items(), key=lambda x: -x[1]):
        print(f"    {k:42s} {v:6,}  ({v/len(rows)*100:5.1f}%)")
    nofloor = sum(1 for r in rows if r["reached_floor_vote"] == "0")
    print(f"  bills that NEVER reached a floor vote: {nofloor:,} "
          f"({nofloor/len(rows)*100:.1f}%)")

    # Backfill pre-1990 vote results from an action on the same date.
    backfill_vote_results(acts)


# A tally written into an action sentence: "roll call #253 (290-38)",
# "Yea-Nay Vote: 273 - 136", "by Yea-Nay Vote. 64-34."
TALLY_RE = re.compile(r"(?<!\d)(\d{1,3})\s*[-–]\s*(\d{1,3})(?!\d)")

RESULT_MAP = [
    ("Failed", re.compile(r"failed of passage|failed to pass|failed of adoption|"
                          r"\bfailed\b|\brejected\b|not agreed to|not invoked", re.I)),
    ("Passed", re.compile(r"\bpassed\b", re.I)),
    ("Agreed to", re.compile(r"agreed to|\badopted\b", re.I)),
]


def backfill_vote_results(acts):
    """Recover a pre-electronic vote result from a Congress.gov action.

    THE TRAP THIS AVOIDS, because the first version walked straight into it.
    Matching on "same bill, same date" alone is WRONG. Congresses routinely
    take several roll calls on one bill in one day - three separate amendment
    votes on H.R. 1426 on 1986-09-18 - and the action Congress.gov records for
    that date describes the PASSAGE vote. Keying on the date therefore stamped
    "Passed" onto amendment votes, motions to table and votes on the rule. That
    is a false attribution of an outcome, which is the one thing this project
    must never produce, and it was caught only by reading the filled rows.

    So the rule is now identity, not adjacency: the action must contain a TALLY
    THAT EQUALS THIS ROLL CALL'S OWN yea-nay. "roll call #253 (290-38)" against
    a 290-38 recount is the same vote and nothing else can be. Where no action
    names our numbers, `result` stays blank - a blank is a true statement about
    the evidence, and "Passed" on the wrong motion is not.
    """
    votes = rd(CLEAN / "bill_votes.csv")
    if not votes or "result_source" not in votes[0]:
        return
    # Withdraw anything the date-keyed version wrote.
    n_withdrawn = 0
    for v in votes:
        if (v.get("result_source") or "").startswith(
                "congress_gov_action_on_the_same_date"):
            v["result"] = ""
            v["result_source"] = NO_RESULT_REASON
            n_withdrawn += 1
    if n_withdrawn:
        print(f"  withdrew {n_withdrawn} date-keyed result fills "
              f"(unsafe: several roll calls share a date on one bill)")

    n = 0
    for v in votes:
        if (v.get("result") or "").strip() or not v.get("bill_id"):
            continue
        try:
            yea, nay = int(v["yea"]), int(v["nay"])
        except (ValueError, KeyError):
            continue
        for a in acts.get(v["bill_id"], []):
            if not any((int(x), int(y)) == (yea, nay)
                       for x, y in TALLY_RE.findall(a["action_text"])):
                continue
            for lab, rx in RESULT_MAP:
                if rx.search(a["action_text"]):
                    v["result"] = lab
                    v["result_source"] = (
                        f"congress_gov_action naming this roll call's own tally "
                        f"{yea}-{nay}: " + a["action_text"][:180])
                    n += 1
                    break
            if (v.get("result") or "").strip():
                break
    wr(CLEAN / "bill_votes.csv", votes, list(votes[0].keys()))
    print(f"  pre-electronic results recovered on an exact tally match: {n}")
    print(f"  result populated overall: "
          f"{sum(1 for v in votes if (v.get('result') or '').strip())}/{len(votes)}")


# ============================================================================
# STAGE 4 -- extended subject sweep (no network)
# ============================================================================
#
# Families the inherited tribal classification under-covers, each with the
# phrase that must appear. Deliberately phrase-level, not token-level: "native"
# alone matches "native plant species" and "hawaiian" alone matches the state.
SUBJECT_FAMILIES = {
    "ANCSA / Alaska Native corporations": [
        r"alaska native claims settlement",
        r"\bANCSA\b",
        r"alaska native (village|regional) corporation",
        r"alaska native corporation",
        r"\bcook inlet region\b",
        r"native (village|regional) corporation",
        r"alaska native allotment",
        r"alaska native vietnam(-| )era veterans",
    ],
    "Native Hawaiian": [
        r"native hawaiian",
        r"hawaiian home ?land",
        r"hawaiian homes commission",
        r"papa ola lokahi",
        r"\bkanaka maoli\b",
        r"office of hawaiian affairs",
        r"hawaiian recogni[sz]ation",
    ],
    "Native American Housing (NAHASDA)": [
        r"\bNAHASDA\b",
        r"native american housing assistance and self.?determination",
        r"indian housing block grant",
        r"native hawaiian housing block grant",
        r"indian community development block grant",
    ],
    "Intertribal / inter-tribal organisations": [
        r"\bintertribal\b", r"\binter.tribal\b",
        r"tribal consortium", r"tribal organi[sz]ation",
        r"national congress of american indians",
        r"council of energy resource tribes",
    ],
    "Alaska Native (non-ANCSA)": [
        r"alaska native (people|health|education|language|elders|subsistence)",
        r"alaska native tribal health consortium",
        r"\bANTHC\b",
    ],
    "Native American / American Indian (general)": [
        r"american indian", r"native american", r"indian tribes?\b",
        r"indian country", r"tribal government", r"federally recogni[sz]ed tribe",
        r"indian self.?determination", r"indian health service",
    ],
}
FAMILY_RX = {k: [re.compile(p, re.I) for p in v] for k, v in SUBJECT_FAMILIES.items()}

# Titles that carry a family phrase but are not Native measures. Each of these
# was observed in the corpus, not imagined.
SWEEP_EXCLUDE = [
    (re.compile(r"\bindian ocean\b", re.I), "Indian Ocean, not Indian country"),
    (re.compile(r"\brepublic of india\b|\bindia\b(?!n)", re.I), "the country India"),
    (re.compile(r"\bwest indian\b|\beast indian\b", re.I), "West/East Indies"),
    (re.compile(r"\bnative (plant|species|grass|fish|wildlife|vegetation|forest)",
                re.I), "native species, not Native peoples"),
    (re.compile(r"\bnative born\b|\bnative.born\b", re.I), "native-born, an immigration term"),
]

# Non-Native subject families that use "tribal organization" style language.
SWEEP_COLS = ["bill_id", "congress", "chamber", "bill_type", "number", "title",
              "policy_area", "subjects", "introduced_date", "sponsor",
              "sponsor_party", "sponsor_state", "cosponsor_count",
              "latest_action_text", "latest_action_date",
              "subject_family", "matched_phrase", "matched_in",
              "already_in_native_bills", "sweep_basis", "build_date"]


def stage_sweep():
    print("=" * 78)
    print("STAGE --sweep : ANCSA / Native Hawaiian / intertribal subject sweep")
    print("=" * 78)

    existing = {b["bill_id"] for b in rd(CLEAN / "native_bills.csv")}
    print(f"  native_bills already holds {len(existing):,} bills")

    corpus = rd(RAW / "all_bill_intros.csv")
    print(f"  all_bill_intros corpus: {len(corpus):,} bills "
          f"(Congresses {min(int(r['congress']) for r in corpus)}-"
          f"{max(int(r['congress']) for r in corpus)})")

    # THE CORPUS REPEATS ITSELF, AND THE SWEEP INHERITED IT (workstream
    # UPSTREAM, 2026-09-01). `all_bill_intros.csv` holds 183,233 rows and 595
    # of them are BYTE-IDENTICAL repeats of a bill already in the file - all
    # 595 groups identical on every one of the 18 columns, so no group carries
    # a second fact. The sweep emits one row per corpus row, so five of those
    # repeats matched a subject family and became the five literal duplicate
    # rows in native_bills_subject_sweep.csv - the ONLY thing standing between
    # `legislation` and a declarable grain.
    #
    # THE DE-DUPE BELONGS HERE, ON THE CORPUS, AND NOWHERE ELSE. Deleting a
    # row from the swept output would be deleting a Cedar row (house rule:
    # flag, never delete). Declining to read one source row twice is not a
    # deletion, it is the same discipline `98` applies to a Congress.gov event
    # that lists a related bill twice. A bill is one bill; the second copy of
    # its metadata says nothing the first did not.
    seen_corpus, deduped, repeats = set(), [], 0
    for r in corpus:
        try:
            k = (int(r["congress"]), str(r["bill_type"]).lower(),
                 int(float(r["bill_number"])))
        except (TypeError, ValueError):
            deduped.append(r)      # unparseable key: never silently dropped
            continue
        if k in seen_corpus:
            repeats += 1
            continue
        seen_corpus.add(k)
        deduped.append(r)
    if repeats:
        print(f"  corpus repeats itself {repeats:,} times on "
              f"(congress, bill_type, bill_number); the FIRST occurrence of "
              f"each is read and the repeats are NOT read a second time. "
              f"Every repeat is byte-identical to its first occurrence - "
              f"re-verified {TODAY}. No Cedar row is deleted by this.")
    corpus = deduped
    print(f"  corpus after source de-duplication: {len(corpus):,} bills")

    hits, stat, newstat, excl = [], Counter(), Counter(), Counter()
    for r in corpus:
        title = r.get("title") or ""
        subj = r.get("subjects") or ""
        pa = r.get("policy_area") or ""
        hay_title = title
        hay_all = f"{title} || {subj} || {pa}"

        fam = phrase = where = ""
        for f, rxs in FAMILY_RX.items():
            for rx in rxs:
                m = rx.search(hay_title)
                if m:
                    fam, phrase, where = f, m.group(0), "title"
                    break
                m = rx.search(hay_all)
                if m:
                    fam, phrase, where = f, m.group(0), "subjects_or_policy_area"
                    break
            if fam:
                break
        if not fam and pa.strip().lower() == "native americans":
            fam, phrase, where = ("Native American / American Indian (general)",
                                  "policyArea=Native Americans",
                                  "congress_gov_policy_area")
        if not fam:
            continue

        bad = next((why for rx, why in SWEEP_EXCLUDE if rx.search(hay_title)), "")
        if bad and where == "title":
            excl[bad] += 1
            continue

        bid = f"{int(r['congress'])}-{str(r['bill_type']).lower()}-{int(float(r['bill_number']))}"
        stat[fam] += 1
        already = bid in existing
        if not already:
            newstat[fam] += 1
        hits.append({
            "bill_id": bid, "congress": r["congress"],
            "chamber": r.get("origin_chamber") or r.get("chamber", ""),
            "bill_type": str(r["bill_type"]).lower(),
            "number": str(int(float(r["bill_number"]))),
            "title": title, "policy_area": pa, "subjects": subj,
            "introduced_date": r.get("introduced_date", ""),
            "sponsor": r.get("sponsor_name", ""),
            "sponsor_party": r.get("sponsor_party", ""),
            "sponsor_state": r.get("sponsor_state", ""),
            "cosponsor_count": r.get("cosponsor_count", ""),
            "latest_action_text": r.get("latest_action_text", ""),
            "latest_action_date": r.get("latest_action_date", ""),
            "subject_family": fam, "matched_phrase": phrase, "matched_in": where,
            "already_in_native_bills": "1" if already else "0",
            "sweep_basis": (f"phrase '{phrase}' matched in {where} of the "
                            "Congress.gov bill record"),
            "build_date": TODAY})

    backup(CLEAN / "native_bills_subject_sweep.csv")
    wr(CLEAN / "native_bills_subject_sweep.csv", hits, SWEEP_COLS)
    print(f"  WROTE native_bills_subject_sweep.csv  rows={len(hits):,}")
    print("  by family (total / new to native_bills):")
    for f in SUBJECT_FAMILIES:
        print(f"    {f:44s} {stat[f]:6,} / {newstat[f]:5,}")
    if excl:
        print("  refused on a title exclusion:")
        for k, v in excl.most_common():
            print(f"    {k:56s} {v:5,}")

    add_new_bills(hits)


def add_new_bills(hits):
    """Append newly swept bills to native_bills.csv. Provenance is explicit:
    classification_source names the phrase rule, so no swept row can ever be
    mistaken for one of the two-coder adjudicated rows."""
    bills = rd(CLEAN / "native_bills.csv")
    have = {b["bill_id"] for b in bills}
    cols = list(bills[0].keys())
    new = []
    seen = set()
    for h in hits:
        if h["bill_id"] in have or h["bill_id"] in seen:
            continue
        seen.add(h["bill_id"])
        row = {c: "" for c in cols}
        row.update({
            "bill_id": h["bill_id"], "congress": h["congress"],
            "chamber": h["chamber"], "number": h["number"],
            "bill_type": h["bill_type"], "title": h["title"],
            "policy_area": h["policy_area"], "sponsor": h["sponsor"],
            "introduced_date": h["introduced_date"],
            "latest_action": h["latest_action_text"],
            "latest_action_date": h["latest_action_date"],
            "cosponsor_count": h["cosponsor_count"],
            "n_rollcalls": "0", "has_rollcall": "0",
            "classification_source": (
                "subject_family_phrase_sweep:" + h["subject_family"]),
            "classification_kappa": "",
            "record_basis": "congress_api_bill_metadata (all_bill_intros.csv)",
            "source_file": "all_bill_intros.csv via 73_bills_votes_completion.py --sweep",
            "build_date": TODAY,
        })
        new.append(row)
    if not new:
        print("  no new bills to add.")
        return
    backup(CLEAN / "native_bills.csv")
    wr(CLEAN / "native_bills.csv", bills + new, cols)
    print(f"  appended {len(new):,} bills to native_bills.csv "
          f"-> {len(bills) + len(new):,} rows")
    print(f"    by family: "
          f"{dict(Counter(h['subject_family'] for h in hits if h['bill_id'] in seen))}")


# ============================================================================
# STAGE 5 -- re-key the enlarged corpus (no network)
# ============================================================================
def stage_bridge():
    print("=" * 78)
    print("STAGE --bridge : re-key native_bills to entities (many-to-many)")
    print("=" * 78)

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "k70", CODE / "70_key_unjoined_datasets.py")
    k70 = importlib.util.module_from_spec(spec)
    # 70's module body builds the scanner tables at import; it also has a
    # main() we do NOT call.
    sys.modules["k70"] = k70
    spec.loader.exec_module(k70)
    print("  imported 70_key_unjoined_datasets (scan_text, resolve_entity, guards)")

    bills = rd(CLEAN / "native_bills.csv")
    old = rd(CLEAN / "native_bills_entity_bridge.csv")
    oldkeys = {(r["bill_id"], r["tribe_id"]) for r in old}
    print(f"  bills {len(bills):,}   existing bridge rows {len(old):,}")

    bridge = {r["bill_id"] + "|" + r["tribe_id"]: r for r in old}
    added = 0
    refusals = Counter()
    for b in bills:
        for span, tid, tier, basis in k70.scan_text(b.get("title") or ""):
            if not tid:
                refusals[basis.split(":")[0]] += 1
                continue
            k = b["bill_id"] + "|" + tid
            prev = bridge.get(k)
            if prev and prev.get("entity_tier") == "A":
                continue
            row = {
                "bill_id": b["bill_id"], "tribe_id": tid,
                "tribe_canonical_name":
                    (k70.SPINE_BY_ID.get(tid) or {}).get("canonical_name", ""),
                "matched_span": span, "matched_in": "title",
                "entity_tier": tier, "entity_match_method": "spine_name_in_title",
                "entity_match_basis": basis, "bill_scope": b.get("bill_scope", ""),
                "congress": b.get("congress", ""), "bill_title": b.get("title", ""),
                "entity_keyed_date": TODAY,
            }
            if prev is None:
                added += 1
            bridge[k] = row

    # canonical names from the spine, via the one resolver's own table
    spname = {r["tribe_id"]: r["canonical_name"]
              for r in rd(SPINE / "cedar_entity_spine.csv")}
    for r in bridge.values():
        if not r.get("tribe_canonical_name"):
            r["tribe_canonical_name"] = spname.get(r["tribe_id"], "")

    rows = sorted(bridge.values(), key=lambda r: (r["bill_id"], r["tribe_id"]))
    backup(CLEAN / "native_bills_entity_bridge.csv")
    wr(CLEAN / "native_bills_entity_bridge.csv", rows, list(old[0].keys()))
    print(f"  bridge rows {len(old):,} -> {len(rows):,}  (+{added:,})")

    byclass = Counter(r["tribe_id"].split("-")[0] for r in rows)
    print(f"  by entity prefix: {dict(byclass)}")
    nontribe = sum(v for k, v in byclass.items() if k != "TRBF")
    ents = {r["tribe_id"] for r in rows}
    print(f"  distinct entities reached: {len(ents):,}  "
          f"(non-federally-recognised-tribe links: {nontribe:,})")
    print(f"  top refusal reasons: {dict(refusals.most_common(6))}")

    # vote bridge inherits through bill_id, exactly as script 70 does.
    votes = rd(CLEAN / "bill_votes.csv")
    by_bill = defaultdict(list)
    for r in rows:
        by_bill[r["bill_id"]].append(r)
    oldvb = rd(CLEAN / "bill_votes_entity_bridge.csv")
    vb = []
    for v in votes:
        for x in by_bill.get(v.get("bill_id"), ()):
            vb.append({"vote_id": v["vote_id"], "bill_id": v["bill_id"],
                       "tribe_id": x["tribe_id"],
                       "tribe_canonical_name": x["tribe_canonical_name"],
                       "entity_tier": x["entity_tier"],
                       "entity_match_method": "inherited_via_bill_id",
                       "entity_match_basis":
                           f"structural inheritance from {v['bill_id']} "
                           f"({x['entity_match_basis']})",
                       "chamber": v["chamber"], "date": v["date"],
                       "entity_keyed_date": TODAY})
    if vb:
        backup(CLEAN / "bill_votes_entity_bridge.csv")
        wr(CLEAN / "bill_votes_entity_bridge.csv", vb,
           list(oldvb[0].keys()) if oldvb else list(vb[0].keys()))
    print(f"  vote bridge rows {len(oldvb):,} -> {len(vb):,}")


# ============================================================================
# STAGE 6 -- entity CLASS keying (no network)
# ============================================================================
#
# The named-entity bridge can only reach a bill that names an entity in its
# title. Most of the non-tribe Native legislation does not: a NAHASDA
# reauthorisation, an ANCSA amendment or a Native Hawaiian health programme
# names a STATUTE and a CLASS, never a corporation.
#
# Writing tribe_ids for those would be exactly the false attribution the bridge
# exists to prevent - the bill does not concern Sealaska in particular, it
# concerns every ANCSA regional corporation. So the class is recorded AS a
# class, joinable to the spine by `entity_class` / id prefix, and it is kept in
# its own file so it can never be mistaken for a named-entity link.
CLASS_MAP = {
    "ANCSA / Alaska Native corporations": [
        ("ANVC-", "Alaska Native Village Corporation"),
        ("ANRC-", "Alaska Native Regional Corporation")],
    "Native Hawaiian": [("NHO-", "Native Hawaiian Organization")],
    "Native American Housing (NAHASDA)": [
        ("TRBF-", "Federally Recognized Tribe"),
        ("ANVC-", "Alaska Native Village Corporation"),
        ("AKNF-", "Alaska Native Village Government"),
        ("NHO-", "Native Hawaiian Organization")],
    "Intertribal / inter-tribal organisations": [
        ("ITO-", "Intertribal Organization")],
    "Alaska Native (non-ANCSA)": [
        ("AKNF-", "Alaska Native Village Government")],
    "Native American / American Indian (general)": [
        ("TRBF-", "Federally Recognized Tribe")],
}


def stage_classes():
    print("=" * 78)
    print("STAGE --classes : which CLASS of Native entity each bill reaches")
    print("=" * 78)
    bills = rd(CLEAN / "native_bills.csv")
    spine = rd(SPINE / "cedar_entity_spine.csv")
    npref = Counter()
    for s in spine:
        npref[s["tribe_id"].split("-")[0] + "-"] += 1

    named = defaultdict(set)
    for r in rd(CLEAN / "native_bills_entity_bridge.csv"):
        named[r["bill_id"]].add(r["tribe_id"])

    rows, stat, bills_hit = [], Counter(), set()
    for b in bills:
        title = b.get("title") or ""
        if not title.strip():
            continue
        fams = []
        for f, rxs in FAMILY_RX.items():
            for rx in rxs:
                m = rx.search(title)
                if m:
                    fams.append((f, m.group(0)))
                    break
        if not fams and (b.get("policy_area") or "").strip().lower() == "native americans":
            fams = [("Native American / American Indian (general)",
                     "policyArea=Native Americans")]
        for f, phrase in fams:
            for pref, label in CLASS_MAP[f]:
                rows.append({
                    "bill_id": b["bill_id"], "congress": b["congress"],
                    "bill_type": b["bill_type"], "number": b["number"],
                    "title": title,
                    "entity_class": label, "entity_id_prefix": pref,
                    "n_spine_entities_in_class": str(npref.get(pref, 0)),
                    "subject_family": f, "matched_phrase": phrase,
                    "class_match_basis": (
                        f"the bill's title names '{phrase}', which is a statute or "
                        f"programme applying to the {label} class as a whole. This is "
                        "a CLASS-level fact, NOT a claim about any individual entity - "
                        "no tribe_id is asserted."),
                    "named_entities_also_in_bridge":
                        "|".join(sorted(named.get(b["bill_id"], ()))),
                    "build_date": TODAY})
                stat[label] += 1
                bills_hit.add(b["bill_id"])

    wr(CLEAN / "native_bills_entity_class.csv", rows)
    print(f"  WROTE native_bills_entity_class.csv  rows={len(rows):,}  "
          f"bills covered={len(bills_hit):,}/{len(bills):,}")
    for k, v in sorted(stat.items(), key=lambda x: -x[1]):
        print(f"    {k:38s} {v:6,} bill-class links "
              f"({npref.get(dict((l, p) for p, l in sum(CLASS_MAP.values(), []))[k], 0)} "
              f"spine entities in the class)")
    nont = sum(v for k, v in stat.items() if k != "Federally Recognized Tribe")
    print(f"  non-federally-recognised-tribe class links: {nont:,}")


# ============================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rollcalls", action="store_true")
    ap.add_argument("--actions", action="store_true")
    ap.add_argument("--titles", action="store_true")
    ap.add_argument("--outcomes", action="store_true")
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--bridge", action="store_true")
    ap.add_argument("--classes", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    if not any([a.rollcalls, a.actions, a.titles, a.outcomes, a.sweep,
                a.bridge, a.classes]):
        ap.error("pick at least one stage")
    if a.rollcalls:
        stage_rollcalls()
    if a.sweep:
        stage_sweep()
    if a.titles:
        stage_titles()
    if a.actions:
        stage_actions(a.limit)
    if a.outcomes:
        stage_outcomes()
    if a.bridge:
        stage_bridge()
    if a.classes:
        stage_classes()


if __name__ == "__main__":
    main()
