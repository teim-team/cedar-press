#!/usr/bin/env python3
# ORDERING, WRITTEN DOWN, as AGENTS.md asks. `nagpra_notices.csv` is rebuilt
# wholesale here and enriched in place by
# `1077_nagpra_institution_grain.py` (Codex PR #29 findings 6 and 8), declared
# in `ENRICHER_ORDERING` in code/cedar_pipeline.py. The usual class-6 hazard -
# a rebuild silently reverting the enricher - does NOT apply to the six
# institution columns, because 1077's parser fix was made HERE, in
# TYPE_PREFIX_RE, OBJECT_HEAD_RE and institution_parts, so this build
# reproduces them rather than reverting them. What this build cannot produce
# is `nagpra_notice_institutions.csv`, the one-row-per-(notice, institution)
# bridge, which 1077 alone writes. RE-RUN 1077 AFTER ANY BUILD HERE, or the
# bridge describes a different universe from the notices beside it - which is
# exactly the FERC failure (102,615 filings, a 183-row docket table, neither
# file wrong on its own).
# lint-ok: class6 - ordering declared above and in cedar_pipeline.ENRICHER_ORDERING; 1077 is the enricher and runs last.
"""
Cedar Press - 77: the NAGPRA repatriation notice dataset (subset of Dataset 9).

WHAT THIS IS
------------
Every Notice of Inventory Completion, Notice of Intent to Repatriate / Intended
Repatriation, and Notice of Intended Disposition published in the Federal
Register, 1994-2026, cut out of the 156,452-document Dataset 9 corpus and
parsed into structure.

`docs/SUBSET_DATASETS.md`: "No structured public database of this exists."
That is still true. The National NAGPRA Program publishes a notice *search*;
it does not publish the notices as data. A THPO who wants to know every notice
that has ever named their nation, or a registrar who wants to know what peer
institutions have determined, has to read Federal Register prose one document
at a time.

WHY THE CARE HERE IS NOT THE USUAL DATA-QUALITY CARE
----------------------------------------------------
These records are about ancestral human remains and funerary objects. A wrong
tribe on a row is not a mismatch; it is a false claim about whose ancestors
those are, and NAGPRA's whole architecture rests on that claim being made by
the institution and the consulted nations, never by a third party.

Three consequences run through every design decision below:

  1. CONSULTED IS NOT AFFILIATED. A notice may consult twenty nations and find
     cultural affiliation with three. Those are different legal findings under
     25 U.S.C. 3003-3005. The bridge carries `relationship` and the two are
     never collapsed, never summed, never defaulted to one another.

  2. MNI IS STATED, NEVER INFERRED. `mni_total_stated` is filled only where the
     notice itself gives a single total for the notice. Where a notice
     enumerates several removal events with their own minima, every figure is
     preserved verbatim in `mni_statements` and the total is left EMPTY. Adding
     them up would be arithmetic on people, performed by a machine that has not
     read the notice.

  3. AN UNRESOLVED NAME IS RECORDED, NOT DROPPED. A 1996 notice uses a nation's
     1996 name. Dropping the row because the 2026 spine spells it differently
     would erase a consultation that happened. Every named party gets a bridge
     row with its verbatim string; `tribe_id` is filled only when the resolver
     is certain.

HOW TRIBE NAMES ARE FOUND (the precision argument)
--------------------------------------------------
NAGPRA notices are FULL of county names, and counties in this corpus are named
Cherokee, Creek, Shawnee, Apache, Oneida, Eagle, Rio Arriba, Santa Barbara.
A document-wide name search would attribute Cherokee County, Iowa to the
Cherokee Nation. That is the exact "Cherokee Inc." trap from AGENTS.md, wearing
a worse hat.

So no name is ever searched for across the document. Instead:

  * The parser first locates the SPANS that are, by the Federal Register's own
    drafting convention, lists of tribes - the consultation sentence, the
    shared-group-identity sentence, the post-2024 rule's bulleted
    "Determinations" list. Those spans are the only text tribe names are read
    from.
  * Inside a span, names are split on the FR's own delimiters (semicolons in
    prose lists, because official names contain commas - "Pit River Tribe,
    California"; newline bullets in the post-2024 layout).
  * Each verbatim string is then handed to `resolve_entity` from
    `code/33_apply_party_rulings.py`. That is the project's ONE resolver
    (standing rule 8). No matching is re-implemented here.
  * A hard refuse-list backstops all of it: a fragment that is only a trap word
    (creek, cherokee, colorado, ojibwe, shawnee, oneida, apache, central,
    eagle, river, mountain, santa) never resolves, whatever the resolver says.

SPINE
-----
Read-only. Four agents are adding TCU-/CDFI-/BIE-/UIO- entities concurrently
and a fifth is building recognition history, so this script never writes to
data/spine/. Names that look like real historical tribe names but do not
resolve are written to review/nagpra_alias_proposals.csv for the recognition
agent and for Elijah.

ROW CONSERVATION - every source row lands in a NAMED bucket
-----------------------------------------------------------
Added 2026-08-29 to close contract point **C5** for this dataset
(`docs/DATASET_READINESS.md`): *every harvested row has a named disposition*.
Before this, the honest statement about the build was "6,772 notices and 51,521
bridge rows came out" with no statement at all about what went in - 156,452
parent-corpus rows were read and 149,678 of them left the build through a
`break`/`continue` that counted nothing.

Two ledgers now account for every row, and the totals must reconcile:

    data/clean/nagpra_notices.csv               rows_in = federal_actions.csv
    data/clean/nagpra_notice_entity_bridge.csv  rows_in = party fragments cut
                                                out of the tribe-list spans

They are merged into `data/clean/cedar_harvest_conservation.csv`, the file
`510_assertions.py` invariant **I13** and `62_no_regression_check.py`
(`harvest_rows_unaccounted`, MUST_BE_ZERO) already gate, using the same seven
columns and the same rules: a reason of `other` / `unknown` / `misc` is refused
by name, because an unnamed rejection is the defect the ledger exists to catch.

TWO THINGS TO KNOW ABOUT THAT FILE, both of which cost time to discover:

  * 510 keys its ledgers by the SOURCE table it harvests. These are keyed by
    the OUTPUT table whose construction they account for, because a NAGPRA
    output has no single source table - `nagpra_notices.csv` is cut out of
    `federal_actions.csv` and `nagpra_notice_entity_bridge.csv` out of spans
    inside cached document text. The arithmetic I13 checks is identical either
    way: `rows_in == sum(dispositions)` within one key.

  * `510_assertions.py all --apply` REWRITES that file from its own ledgers
    only, so it will delete these four row-groups. That is not a hypothetical:
    it is a plain `write_csv` in 510. So the ledgers are ALSO kept, durably and
    in full, in `review/nagpra_row_conservation.csv`, and the repair is one
    cheap command that recomputes nothing:

        py -3 code/77_build_nagpra_dataset.py conservation

    Run it whenever `62` reports `harvest_source_rows_read` falling, or
    `518_dataset_readiness.py` puts `nagpra` back to BLOCKED on C5.

STAGES
------
    py -3 code/77_build_nagpra_dataset.py fetch    # full text -> local cache
    py -3 code/77_build_nagpra_dataset.py build    # cache -> the two CSVs
    py -3 code/77_build_nagpra_dataset.py conservation         # re-merge C5
    py -3 code/77_build_nagpra_dataset.py conservation verify  # exit 1 on a gap

Reads   data/clean/federal_actions.csv                     (the parent corpus)
        data/raw/federal_register/nagpra_fulltext/**.txt.gz (cached notice text)
        data/spine/cedar_entity_spine.csv                  (read-only)
Writes  data/clean/nagpra_notices.csv                      one row per notice
        data/clean/nagpra_notice_entity_bridge.csv         one row per (notice, party)
        data/clean/cedar_harvest_conservation.csv          MERGED, never rewritten
        review/nagpra_row_conservation.csv                 the durable C5 ledger
        review/nagpra_alias_proposals.csv                  unresolved names
        review/nagpra_unparsed.csv                         notices that would not parse
        logs/77_nagpra_<date>.log
"""

import csv
import gzip
import html
import json
import os
import re
import sys
import threading
import time
from collections import Counter, defaultdict
import pathlib
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import importlib

_pr = importlib.import_module("33_apply_party_rulings")
resolve_entity = _pr.resolve_entity          # STANDING RULE 8: the one resolver
norm = _pr.norm

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
LOGS = CEDAR / "logs"
CACHE = CEDAR / "data" / "raw" / "federal_register" / "nagpra_fulltext"

PARENT = CLEAN / "federal_actions.csv"
OUT_NOTICES = CLEAN / "nagpra_notices.csv"
OUT_BRIDGE = CLEAN / "nagpra_notice_entity_bridge.csv"
OUT_ALIASES = REVIEW / "nagpra_alias_proposals.csv"
OUT_UNPARSED = REVIEW / "nagpra_unparsed.csv"

# ------------------------------------------------------- row conservation ---
#: The shared ledger 510 I13 and 62 gate on. MERGED into, never rewritten.
CONSERVATION = CLEAN / "cedar_harvest_conservation.csv"
#: This dataset's own durable copy of its four ledgers. It lives in review/
#: and not data/clean/ on purpose: a new file under data/clean is a new
#: SHIPPABLE table as far as 62 is concerned, and would raise four MUST_NOT_RISE
#: registration metrics for a file that is process metadata, not product.
LEDGER_LOCAL = REVIEW / "nagpra_row_conservation.csv"
CONSERVATION_COLS = ["source_table", "rows_in", "disposition", "rows", "pct",
                     "examples", "harvest_date"]

#: The four customer tables of the `nagpra` collection, in the exact key form
#: the ledger uses. `conservation verify` refuses to pass while any of them has
#: no coverage, so a future builder cannot drop a ledger and stay green.
CONSERVED_TABLES = (
    "data/clean/nagpra_notices.csv",
    "data/clean/nagpra_notice_entity_bridge.csv",
    "data/clean/fr_nagpra_title_index.csv",         # written by 78
    "data/clean/fr_nagpra_title_index_year.csv",    # written by 78
)

#: 510's I13 refuses these by name. Re-stated here so the refusal happens at
#: the point a disposition is INVENTED, not two layers downstream.
UNNAMED_REASON_RE = re.compile(r"(?:^|:)(other|unknown|misc|n/?a)\s*$", re.I)


class RowLedger:
    """Per-table row accounting. Named dispositions only.

    Deliberately the same shape as `510_assertions.RowLedger`, because the two
    write the same file and a second shape would be a second thing to keep in
    step. Not imported from 510: 510 is another workstream's file and importing
    it executes its module body.
    """

    def __init__(self, table):
        self.table = table
        self.rows_in = 0
        self.counts = Counter()
        self.examples = defaultdict(list)

    def seen(self):
        self.rows_in += 1

    def note(self, disposition, example=""):
        if UNNAMED_REASON_RE.search(disposition):
            raise ValueError(
                f"disposition {disposition!r} is not a NAMED reason - an "
                f"unnamed rejection is the defect this ledger exists to catch")
        self.counts[disposition] += 1
        if example and len(self.examples[disposition]) < 3:
            self.examples[disposition].append(str(example)[:80])

    def unaccounted(self):
        return self.rows_in - sum(self.counts.values())


def conservation_rows(ledgers):
    out = []
    for lg in ledgers:
        for disp, n in sorted(lg.counts.items()):
            out.append(dict(source_table=lg.table, rows_in=lg.rows_in,
                            disposition=disp, rows=n,
                            pct=round(100.0 * n / max(lg.rows_in, 1), 2),
                            examples="; ".join(lg.examples.get(disp, [])),
                            harvest_date=TODAY))
    return out


def publish_conservation():
    """MERGE the dataset's own ledger into the shared file. Never rewrite it.

    Every key in `cedar_harvest_conservation.csv` that this dataset does not
    own is preserved verbatim and in order; only the nagpra keys are replaced.
    A wholesale rewrite here would delete 510's 37 rows - which is exactly the
    failure this function is written to survive coming the other way.

    Cheap: it reads two small CSVs and recomputes nothing, which is what makes
    the documented repair after a 510 rewrite a one-liner rather than a
    3-minute rebuild.
    """
    local = read_csv(LEDGER_LOCAL)
    if not local:
        log(f"  no {LEDGER_LOCAL.relative_to(CEDAR)} - nothing to publish. "
            f"Run `build` (77) and `--nagpra-only` (78) first.")
        return 1
    ours = {r["source_table"] for r in local}
    keep = [r for r in read_csv(CONSERVATION)
            if (r.get("source_table") or "") not in ours]
    write_csv(CONSERVATION, keep + local, CONSERVATION_COLS)
    log(f"  merged {len(local)} nagpra disposition row(s) over "
        f"{len(ours)} table(s); {len(keep)} row(s) of other ledgers untouched")
    return 0


def merge_conservation(ledgers):
    """Record these ledgers and publish them.

    Refuses to record a ledger that does not add up. A ledger with an
    unaccounted remainder is worse than no ledger: it states a total that
    licenses a reader to believe the rest was named.
    """
    bad = [lg for lg in ledgers if lg.unaccounted()]
    if bad:
        for lg in bad:
            log(f"  CONSERVATION BREACH {lg.table}: {lg.rows_in:,} rows read, "
                f"{sum(lg.counts.values()):,} accounted for, "
                f"{lg.unaccounted():,} with no named disposition")
        raise SystemExit(1)
    ours = {lg.table for lg in ledgers}
    keep = [r for r in read_csv(LEDGER_LOCAL)
            if (r.get("source_table") or "") not in ours]
    write_csv(LEDGER_LOCAL, keep + conservation_rows(ledgers),
              CONSERVATION_COLS)
    for lg in ledgers:
        log(f"  conservation {lg.table}: {lg.rows_in:,} rows read")
        for disp, n in sorted(lg.counts.items(), key=lambda kv: -kv[1]):
            log(f"      {n:>9,}  {disp}")
    publish_conservation()


def conservation_verify():
    """Exit 1 while any nagpra table lacks reconciling, named coverage.

    Cheap - it reads one small CSV and computes nothing - so it can be a
    handoff check and a pre-ship check without a rebuild.
    """
    by = defaultdict(list)
    for r in read_csv(CONSERVATION):
        by[r.get("source_table") or ""].append(r)
    fails = []
    for t in CONSERVED_TABLES:
        rs = by.get(t)
        if not rs:
            fails.append(f"{t}: NO row-conservation coverage in "
                         f"{CONSERVATION.name} - C5 is not met. Rebuild the "
                         f"dataset, or see the ROW CONSERVATION note at the "
                         f"top of this file")
            continue
        rows_in = int(rs[0]["rows_in"] or 0)
        total = sum(int(r["rows"] or 0) for r in rs)
        if total != rows_in:
            fails.append(f"{t}: {rows_in:,} rows read but {total:,} accounted "
                         f"for - {abs(rows_in - total):,} vanished without a "
                         f"named disposition")
        for r in rs:
            d = r["disposition"]
            if d == "UNACCOUNTED_FOR" and int(r["rows"] or 0):
                fails.append(f"{t}: {r['rows']} row(s) UNACCOUNTED_FOR")
            if UNNAMED_REASON_RE.search(d):
                fails.append(f"{t}: disposition {d!r} is not a NAMED reason")
        log(f"  OK  {t:48s} {rows_in:>9,} rows read, "
            f"{len(rs)} named disposition(s)")
    for f in fails:
        log(f"  FAIL {f}")
    if fails:
        log(f"\n  {len(fails)} conservation failure(s). C5 NOT met.")
        return 1
    log(f"\n  all {len(CONSERVED_TABLES)} nagpra tables have reconciling, "
        f"named row-conservation coverage. C5 met.")
    return 0

HOST = "www.federalregister.gov"
HOSTLOCK = LOGS / f"_HOSTLOCK_{HOST}.json"
TODAY = date.today().isoformat()


def cache_fetched_date(path) -> str:
    """When the CACHED DOCUMENT was fetched - not when this build ran.

    `fetched_date` used to hold `TODAY`, so every rebuild rewrote the column
    and `nagpra_notices.csv` could never be byte-identical across runs. That
    is blocker B4 in docs/RELEASE_REPLAY_LOG.md, and it was the ONLY column
    separating this table from an exact replay: the 2026-08-30 clean-room run
    reproduced 6,772 of 6,772 rows and 65 of 66 columns, differing on this one.

    RETRACTED 2026-08-30, same day, on external review. The first fix read the
    artifact's MTIME and called it fetched_date. That made the column
    deterministic and WRONG: an mtime is set by whichever of download, local
    copy, extraction, restore or rsync touched the file last, and some tools
    preserve the REMOTE modification time, so a file fetched today can carry
    an mtime from 2019. "Deterministically wrong metadata is worse than
    deterministically missing metadata" - the reviewer, and they are right.

    So this returns the recorded retrieval time when one exists in the fetch
    sidecar, and "" otherwise. The mtime is still emitted, but under its own
    honest name (artifact_mtime) as technical metadata - never renamed into
    provenance. Determinism is preserved either way; correctness is no longer
    traded for it. Going forward `fetch` writes retrieval time explicitly at
    the acquisition boundary.
    """
    p = pathlib.Path(path)
    side = p.with_suffix(p.suffix + ".fetchmeta")
    if side.exists():
        try:
            import json as _json
            v = (_json.loads(side.read_text(encoding="utf-8"))
                 .get("retrieved_at") or "")
            return v[:10]
        except (OSError, ValueError):
            pass
    return ""                       # unknown retrieval time stays UNKNOWN


def artifact_mtime(path) -> str:
    """The cached file's mtime, under its own name. Technical metadata about
    OUR copy of the artifact - not a claim about when it was retrieved."""
    try:
        from datetime import datetime as _dt
        return _dt.utcfromtimestamp(
            pathlib.Path(path).stat().st_mtime).date().isoformat()
    except (OSError, ValueError, TypeError):
        return ""
LOG_PATH = LOGS / f"77_nagpra_{TODAY}.log"

TEXT_URL = "https://www.federalregister.gov/documents/full_text/text/{y}/{m}/{d}/{dn}.txt"

# Politeness. The 2026-08-05 harvest ran this host at 2 workers / 0.60s and was
# never throttled; this stays inside that envelope.
WORKERS = 2
SLEEP = 0.55
MAX_RETRIES = 5

# ---------------------------------------------------------------- universe ---
#
# Title-anchored, because the title of a NAGPRA notice is a controlled string.
# A full-text keyword net would sweep in the Review Committee's meeting notices
# and the rulemakings, which are about NAGPRA but are not repatriation notices
# and have no institution, no MNI and no affiliation finding.
NOTICE_TYPES = [
    # (regex, notice_type, statute_stage)
    (re.compile(r"notice of inventory completion", re.I),
     "inventory_completion", "25 U.S.C. 3003 inventory / cultural affiliation"),
    (re.compile(r"notice of intent to repatriate", re.I),
     "intent_to_repatriate", "25 U.S.C. 3004 summary / cultural items"),
    # The 2023 rule (43 CFR 10, eff. 2024-01-12) renamed the 3004 notice from
    # "Intent To Repatriate" to "Intended Repatriation". Same legal stage,
    # different label - so notice_type is shared and notice_title_form records
    # which wording the document actually used. Merging the STAGE is correct;
    # pretending the wording was the same would not be.
    (re.compile(r"notice of intended repatriation", re.I),
     "intent_to_repatriate", "25 U.S.C. 3004 summary / cultural items"),
    # A genuinely distinct third stage: remains removed from Federal or tribal
    # lands with no cultural affiliation determined, disposed of by priority
    # order rather than repatriated on an affiliation finding. Not merged.
    (re.compile(r"notice of intended disposition", re.I),
     "intended_disposition", "43 CFR 10.7 disposition of unclaimed remains"),
]
CORRECTION_RE = re.compile(r"\bcorrection\b", re.I)


# --------------------------------------------------------------------- log ---

_log_lock = threading.Lock()
_log_fh = None


def log(msg=""):
    with _log_lock:
        print(msg, flush=True)
        if _log_fh:
            _log_fh.write(str(msg) + "\n")
            _log_fh.flush()


def read_csv(p):
    if not Path(p).exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(p, rows, fields):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    log(f"  wrote {p.relative_to(CEDAR)}  ({len(rows):,} rows)")


#: The one reason a parent-corpus row does not enter the NAGPRA universe. It is
#: 149,678 of 156,452 rows, and naming it is the whole point: "the rest" is not
#: a disposition.
NOT_A_NOTICE = ("rejected:federal_register_title_is_not_one_of_the_four_NAGPRA_"
                "notice_headings_prescribed_by_43_CFR_10")


def universe(led=None):
    """The NAGPRA notice universe, from the parent corpus. No network.

    `led` is the `nagpra_notices.csv` row ledger. The title filter is the
    dataset's single largest drop, so it is counted HERE, where it happens,
    rather than reconstructed afterwards by subtraction - a subtracted count
    agrees with itself by construction and cannot detect a second silent drop.
    """
    csv.field_size_limit(10 ** 9)
    out = []
    for r in read_csv(PARENT):
        if led is not None:
            led.seen()
        t = r.get("title") or ""
        hit = False
        for rx, ntype, stage in NOTICE_TYPES:
            m = rx.search(t)
            if m:
                hit = True
                out.append({
                    "document_number": r["document_number"],
                    "publication_date": r["publication_date"],
                    "title": t,
                    "abstract": r.get("abstract") or "",
                    "dates_field": r.get("dates") or "",
                    "agency_names": r.get("agency_names") or "",
                    "html_url": r.get("html_url") or "",
                    "pdf_url": r.get("pdf_url") or "",
                    "json_url": r.get("json_url") or "",
                    "notice_type": ntype,
                    "statute_stage": stage,
                    "notice_title_form": m.group(0),
                    "is_correction": "1" if CORRECTION_RE.search(t) else "0",
                })
                break
        if led is not None and not hit:
            led.note(NOT_A_NOTICE, r.get("document_number") or "")
    out.sort(key=lambda r: (r["publication_date"], r["document_number"]))
    return out


# =========================================================== stage: fetch ====

def cache_path(pub, dn):
    return CACHE / pub[:4] / f"{dn}.txt.gz"


CF_MAIL_RE = re.compile(
    r'<a [^>]*email-protection[^>]*>.*?</a>', re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
BULLET = "•"


def raw_notice_text(response_text):
    """What gets CACHED: the GPO text body, with its markup intact.

    An earlier version of this function cleaned the text before caching and
    destroyed something load-bearing. GPO's plain-text rendition marks the
    determination findings with a literal `<bullet>` token:

        <bullet> The human remains described in this notice represent the
        physical remains of one individual of Native American ancestry.
        <bullet> There is a relationship of shared group identity ...

    A generic tag-stripper eats `<bullet>` along with the `<a href>` around the
    GPO link, and the two findings - the MNI and the cultural affiliation -
    silently merge into one run of prose. That is precisely the boundary the
    parser needs, and it cannot be recovered from the cache once thrown away.

    So the cache keeps the bytes and cleaning happens at build time, where it
    can be revised without re-touching the host. Standing rule: keep raw.
    """
    m = re.search(r"<pre>(.*?)</pre>", response_text, re.S | re.I)
    return m.group(1) if m else response_text


def clean_fr_text(raw):
    """Cache -> parseable text. Runs at BUILD time, never at fetch time.

    `<bullet>` becomes a real bullet character so the parser can split the
    determination findings. Cloudflare's email obfuscation is collapsed to a
    placeholder (the address is unrecoverable either way, and leaving the
    markup in would let a stray '<' swallow the following sentence). Line
    breaks and indentation are the Federal Register's own and are preserved -
    the section detector depends on them.
    """
    body = CF_MAIL_RE.sub("[email protected]", raw)
    body = re.sub(r"<bullet>", BULLET, body, flags=re.I)
    body = TAG_RE.sub("", body)
    return html.unescape(body)


def fetch_stage(limit=None):
    import requests

    docs = universe()
    if limit:
        docs = docs[:limit]
    todo = [d for d in docs if not cache_path(d["publication_date"],
                                              d["document_number"]).exists()]
    log(f"universe {len(docs):,} notices; already cached "
        f"{len(docs) - len(todo):,}; to fetch {len(todo):,}")
    if not todo:
        log("nothing to fetch.")
        return

    claim_host(len(todo))

    sess = threading.local()

    def S():
        s = getattr(sess, "s", None)
        if s is None:
            s = requests.Session()
            s.headers.update({"User-Agent": (
                "Cedar Press NAGPRA dataset build (research; "
                "elijahsamsonmoreno@gmail.com)")})
            sess.s = s
        return s

    state = {"ok": 0, "miss": 0, "fail": 0, "edge": 0}
    lock = threading.Lock()

    def one(d):
        dn, pub = d["document_number"], d["publication_date"]
        y, m, dd = pub[:4], pub[5:7], pub[8:10]
        url = TEXT_URL.format(y=y, m=m, d=dd, dn=dn)
        delay = 5.0
        for attempt in range(1, MAX_RETRIES + 1):
            t0 = time.time()
            try:
                r = S().get(url, timeout=120)
            except requests.RequestException as exc:
                # PULL_DISCIPLINE rule 4: an instant connection failure is an
                # edge block and more requests extend it; a slow one is a slow
                # server and retrying is fine.
                if time.time() - t0 < 1.0:
                    with lock:
                        state["edge"] += 1
                if attempt == MAX_RETRIES:
                    with lock:
                        state["fail"] += 1
                    return (dn, f"network:{exc.__class__.__name__}")
                time.sleep(delay)
                delay = min(delay * 2, 900)
                continue
            if r.status_code == 200:
                p = cache_path(pub, dn)
                p.parent.mkdir(parents=True, exist_ok=True)
                tmp = p.with_suffix(".tmp")
                with gzip.open(tmp, "wt", encoding="utf-8") as fh:
                    fh.write(raw_notice_text(r.text))
                tmp.replace(p)
                time.sleep(SLEEP)
                with lock:
                    state["ok"] += 1
                return (dn, "ok")
            if r.status_code == 404:
                # A real answer: this document has no plain-text rendition.
                # Recorded, not retried, not invented.
                time.sleep(SLEEP)
                with lock:
                    state["miss"] += 1
                return (dn, "http_404_no_text_rendition")
            if r.status_code in (429, 500, 502, 503, 504):
                wait = float(r.headers.get("Retry-After", delay))
                time.sleep(wait)
                delay = min(delay * 2, 900)
                continue
            with lock:
                state["fail"] += 1
            return (dn, f"http_{r.status_code}")
        with lock:
            state["fail"] += 1
        return (dn, "retries_exhausted")

    from concurrent.futures import ThreadPoolExecutor
    problems = []
    t0 = time.time()
    with ThreadPoolExecutor(WORKERS) as ex:
        for i, (dn, status) in enumerate(ex.map(one, todo), 1):
            if status != "ok":
                problems.append((dn, status))
            if i % 250 == 0:
                rate = i / max(time.time() - t0, 1)
                log(f"  [{i:,}/{len(todo):,}] ok={state['ok']:,} "
                    f"404={state['miss']:,} fail={state['fail']:,} "
                    f"{rate:.1f}/s  eta {(len(todo)-i)/max(rate,.01)/60:.0f}m")
            if state["edge"] >= 20:
                log("  !! edge-block signature (20 instant connection "
                    "failures). Stopping per PULL_DISCIPLINE rule 4.")
                break

    log(f"\nfetch done in {time.time()-t0:,.0f}s: ok={state['ok']:,} "
        f"404={state['miss']:,} failed={state['fail']:,}")
    if problems:
        with open(LOGS / f"77_nagpra_fetch_problems_{TODAY}.csv", "w",
                  encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["document_number", "status"])
            w.writerows(problems)
        log(f"  {len(problems):,} problems -> "
            f"logs/77_nagpra_fetch_problems_{TODAY}.csv")
    release_host()


def claim_host(n_jobs):
    """PULL_DISCIPLINE rules 1-2. One poller per host, claimed in a lock file.

    The existing lock names code/76_build_recognition_history.py with pid 0 and
    an empty queue. pid 0 is not a live process, no such script exists on disk,
    and no python process on this machine is running it - so the lock is stale
    under the six-hour clause and is taken over rather than blocked on. The
    previous holder is preserved in the file so the recognition agent can see
    what happened and append rather than start a second loop.

    FIXED 2026-08-26: this read `prev["pid"] > 0` alone, which is not what a
    lock file means. A lock records its holder's pid FOREVER - a poller that
    releases correctly leaves `active: false` and a `released` timestamp behind
    a pid that is simply history. Reading the pid alone made this script unable
    to claim a host that any well-behaved poller had ever used: on 2026-08-26
    the NAGPRA fetch queued itself behind a lock
    `code/342_pull_federal_register_incremental.py` had released nine seconds
    earlier, and exited having fetched nothing. A false "host is busy" stops
    work that would have succeeded, exactly as PULL_DISCIPLINE records for the
    mirror-image case. The lock is HELD only while `active` is true and no
    `released` stamp is present - the two fields PULL_DISCIPLINE defines.
    """
    prev = {}
    if HOSTLOCK.exists():
        try:
            prev = json.loads(HOSTLOCK.read_text(encoding="utf-8"))
        except Exception:
            prev = {}
    held = (bool(prev.get("pid")) and prev["pid"] > 0
            and prev.get("active", True) and not prev.get("released"))
    if held:
        log(f"!! {HOST} is locked by pid {prev['pid']} "
            f"({prev.get('script')}). Appending to its queue and exiting.")
        prev.setdefault("queue", []).append(
            {"script": "code/77_build_nagpra_dataset.py",
             "jobs": n_jobs, "requested": datetime.now(timezone.utc).isoformat(timespec='seconds')})
        HOSTLOCK.write_text(json.dumps(prev, indent=2), encoding="utf-8")
        raise SystemExit(0)
    HOSTLOCK.write_text(json.dumps({
        "host": HOST, "pid": os.getpid(),
        "script": "code/77_build_nagpra_dataset.py",
        "started": datetime.now(timezone.utc).isoformat(timespec='seconds'),
        "jobs": n_jobs, "queue": [],
        "previous_holder": prev,
        "takeover_reason": ("stale lock: pid 0, >6h old, holder script absent "
                            "from disk and from Win32_Process"),
    }, indent=2), encoding="utf-8")
    log(f"claimed {HOSTLOCK.name} (pid {os.getpid()}, {n_jobs:,} jobs)")


def release_host():
    if not HOSTLOCK.exists():
        return
    try:
        d = json.loads(HOSTLOCK.read_text(encoding="utf-8"))
    except Exception:
        return
    if d.get("pid") == os.getpid():
        d["pid"] = 0
        d["released"] = datetime.now(timezone.utc).isoformat(timespec='seconds')
        HOSTLOCK.write_text(json.dumps(d, indent=2), encoding="utf-8")
        log(f"released {HOSTLOCK.name}")


# =========================================================== stage: build ====
#
# Everything below reads the local cache. No network.

PAGE_RE = re.compile(r"\[\[Page[^\]]*\]\]")

# The headings the NAGPRA templates actually use. A closed list, not a
# general-purpose heading detector: these are controlled documents and guessing
# at headings would let a stray capitalised line become a tribe-list span.
HEAD_RE = re.compile(
    r"(?m)^(?P<h>Consultation"
    r"|History and Description[^\n]*"
    r"|Description of the[^\n]*"
    r"|Description"
    r"|Abstract of Information Available"
    r"|Cultural Affiliation[^\n]*"
    r"|Determinations[^\n]*"
    r"|Requests for Repatriation[^\n]*"
    r"|Requests for Disposition[^\n]*"
    r"|Additional Requestors[^\n]*"
    r"|Disposition[^\n]*"
    r"|Background[^\n]*)\s*$")

HEAD_KEY = [
    ("consultation", re.compile(r"^Consultation", re.I)),
    ("history_description", re.compile(r"^(History and Description|Description)", re.I)),
    ("abstract_of_information", re.compile(r"^Abstract of Information", re.I)),
    ("cultural_affiliation", re.compile(r"^Cultural Affiliation", re.I)),
    ("determinations", re.compile(r"^Determinations", re.I)),
    ("requests", re.compile(r"^Requests for", re.I)),
    ("additional_requestors", re.compile(r"^Additional Requestors", re.I)),
    ("disposition", re.compile(r"^Disposition", re.I)),
    ("background", re.compile(r"^Background", re.I)),
]


def flatten(s):
    """Un-wrap Federal Register hard wrapping into flowing text.

    `[[Page 76777]]` markers are deleted rather than kept, because GPO inserts
    them MID-SENTENCE: '...between the Native American human remains and\n\n
    [[Page 76777]]\n\nassociated funerary objects and the Pit River Tribe...'.
    A sentence-scoped regex that does not remove them stops at the page break
    and truncates the tribe list - losing every nation after the column break.
    """
    s = PAGE_RE.sub(" ", s)
    s = s.replace("\n", " ")
    return re.sub(r"[ \t]+", " ", s).strip()


def split_sections(text):
    """{section_key: flattened body} plus '_preamble'. Unknown text is ignored."""
    out = {}
    marks = [(m.start(), m.end(), m.group("h").strip())
             for m in HEAD_RE.finditer(text)]
    out["_preamble"] = flatten(text[:marks[0][0]] if marks else text)
    for i, (s0, e0, h) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        key = next((k for k, rx in HEAD_KEY if rx.match(h)), None)
        if not key:
            continue
        body = flatten(text[e0:end])
        # A notice can carry several 'Determinations Made by X' sections when
        # two institutions share one notice. Concatenating keeps both findings
        # rather than letting the second overwrite the first.
        out[key] = (out[key] + " " + body).strip() if key in out else body
        out.setdefault(key + "_headings", "")
        out[key + "_headings"] = (out[key + "_headings"] + " | " + h).strip(" |")
    return out


# ------------------------------------------------------- number handling -----

_UNITS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve "
    "thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split())}
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fourty": 40, "fifty": 50,
         "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}


def to_int(s):
    """'one' -> 1, '1,234' -> 1234, 'one hundred fifty-six' -> 156.

    Returns None when the phrase is not a plain cardinal. None means "the
    notice did not state a number I can read", and the caller must then leave
    the numeric column EMPTY - never fall back to a guess.
    """
    s = (s or "").strip().lower().replace(",", "")
    if re.fullmatch(r"\d+", s):
        return int(s)
    words = re.split(r"[\s-]+", s.replace(" and ", " "))
    words = [w for w in words if w]
    if not words or any(w not in _UNITS and w not in _TENS
                        and w not in ("hundred", "thousand") for w in words):
        return None
    total, cur = 0, 0
    for w in words:
        if w in _UNITS:
            cur += _UNITS[w]
        elif w in _TENS:
            cur += _TENS[w]
        elif w == "hundred":
            cur = (cur or 1) * 100
        elif w == "thousand":
            total += (cur or 1) * 1000
            cur = 0
    return total + cur


# A cardinal, spelled or in digits - and NOTHING else. Built from the same
# vocabulary `to_int` can read, so a match always yields a number.
#
# The first version of this was `(?:[\d,]+|(?:[a-z]+[\s-]){0,3}?[a-z]+)`, which
# happily read "human remains of Native American individuals" as an MNI
# statement of "Native American" individuals. It produced no number, but it did
# put a non-statement into the audit column - and on this dataset a spurious
# count statement is exactly the kind of thing that must not exist.
_NUMTOK = sorted(list(_UNITS) + list(_TENS) + ["hundred", "thousand"],
                 key=len, reverse=True)
_TOK = "|".join(_NUMTOK)
NUMWORD = r"(?:[\d,]+|(?:" + _TOK + r")(?:[\s-]+(?:and[\s-]+)?(?:" + _TOK + r"))*)"

# MNI. Two anchors, deliberately different in standing:
#   REMOVED  - the description's per-removal-event minimum
#   DET      - the Determinations finding, which is the institution's own
#              total FOR THE NOTICE and is therefore the only figure allowed
#              to fill mni_total_stated on its own.
#
# 'minimum of' is OPTIONAL because the 1990s notices do not use it: "human
# remains representing one individual were recovered from site UKT-023". That
# is still a stated count, and requiring the later boilerplate would have
# silently emptied MNI for the first decade of the series.
MNI_REMOVED_RE = re.compile(
    r"human remains (?:representing|of)[, ]{1,3}"
    r"(?:(?:a |the )?(?:minimum(?: number)? of|at minimum,?)[, ]{1,3})?"
    r"(" + NUMWORD + r")\s+individuals?\b", re.I)
MNI_DET_RE = re.compile(
    r"represents?\s+the physical remains of\s+(" + NUMWORD +
    r")\s+individuals?\s+of Native American ancestry", re.I)
MNI_NEW_RE = re.compile(
    r"\bthe\s+([\d,]+|one)\s+individuals?\s+(?:were|was)\s+removed\b", re.I)

OBJ_COUNT_RES = {
    "associated_funerary_objects": re.compile(
        r"\b(" + NUMWORD + r")\s+associated funerary objects?\b", re.I),
    "unassociated_funerary_objects": re.compile(
        r"\b(" + NUMWORD + r")\s+unassociated funerary objects?\b", re.I),
    "sacred_objects": re.compile(
        r"\b(" + NUMWORD + r")\s+sacred objects?\b", re.I),
    "objects_of_cultural_patrimony": re.compile(
        r"\b(" + NUMWORD + r")\s+objects? of cultural patrimony\b", re.I),
}
CULTURAL_ITEMS_RE = re.compile(
    r"total of\s+([\d,]+)\s+cultural items?\s+(?:have|has)\s+been requested", re.I)

# Category presence is read ONLY from the notice's own subject statement (the
# SUMMARY, or the 'Notice is hereby given ... of ...' sentence). Reading it
# from the whole document would mark every notice as containing sacred objects,
# because the boilerplate 'Requests for Repatriation' paragraph enumerates all
# five statutory categories whether or not the notice concerns them.
CATEGORY_PHRASES = [
    ("unassociated_funerary_objects", re.compile(r"unassociated funerary object", re.I)),
    ("associated_funerary_objects", re.compile(r"(?<!un)associated funerary object", re.I)),
    ("sacred_objects", re.compile(r"sacred object", re.I)),
    ("objects_of_cultural_patrimony", re.compile(r"object[s]? of cultural patrimony", re.I)),
    ("human_remains", re.compile(r"human remains", re.I)),
]
NEG_PRESENT_RE = re.compile(
    r"\bno\s+(associated funerary objects?|unassociated funerary objects?|"
    r"sacred objects?|objects? of cultural patrimony)\s+(?:are|were|is)\s+present",
    re.I)


# ------------------------------------------------------------ tribe lists ----
#
# THE SPANS. These are the only places a tribe name is ever read from.

# END-OF-SENTENCE, for spans that stop at one.
#
# The obvious rule - stop at the next '. ' - cuts "Sault Ste. Marie Tribe of
# Chippewa Indians of Michigan" down to "Sault Ste", and did so 13 times before
# this was noticed. The tribe still resolved, which is what made it easy to
# miss: the verbatim column, which is meant to preserve exactly what the
# Federal Register published, was quietly holding a fragment of a nation's
# name. Abbreviations that legitimately carry an internal period are excluded
# here; a single capital letter before the period covers initials and U.S.
# `(?<![^A-Za-z][A-Z])` blocks a period that follows a lone capital - an
# initial ('J. P. Harrington') or 'U.S.' - while still allowing a state
# abbreviation to end a sentence ('... County, CA.'), because the 'A'
# there follows another letter.
_SENT = (r"(?<![^A-Za-z][A-Z])(?<!\bSte)(?<!\bSt)(?<!\bMt)(?<!\bFt)(?<!\bNo)"
         r"(?<!\bInc)(?<!\bCo)(?<!\bJr)(?<!\bSr)\.(?:\s|$)")

_SENT_RE = re.compile(_SENT)


def cut_at_sentence(span):
    """Truncate a captured span at its first genuine sentence end."""
    m = _SENT_RE.search(span or "")
    return (span[:m.start()] if m else (span or "")).strip()


CONSULT_RES = [
    re.compile(r"in consultation with representatives of\s+(?:the\s+)?(?P<L>.+?)"
               r"(?=" + _SENT + r")", re.I),
    re.compile(r"consulted with representatives of\s+(?:the\s+)?(?P<L>.+?)"
               r"(?=" + _SENT + r")", re.I),
    re.compile(r"consultation was (?:held|conducted) with\s+(?:the\s+)?(?P<L>.+?)"
               r"(?=" + _SENT + r")", re.I),
    re.compile(r"in consultation with\s+(?:the\s+)?(?P<L>.+?)(?=" + _SENT + r")", re.I),
]

# The affiliation finding. The lead-in is stripped by matching it explicitly
# rather than by taking "everything after the last 'and'", because the object
# clause itself contains 'and' ('human remains AND associated funerary
# objects') and a greedy rule would silently drop the first tribe named.
#
# 'that' vs 'which' and 'the' vs 'these' are not stylistic here - the 1990s
# notices write "shared group identity WHICH can be reasonably traced between
# THESE Native American human remains". A regex fixed on the later wording
# matched 8 affiliation findings in the first five years of the series and
# would have reported, falsely, that early notices made no affiliation
# determination.
_DEM = r"(?:the|these|those|this)\s+"
_OBJ = (r"(?:Native American\s+)?"
        r"(?:human remains(?:\s*,?\s*(?:and\s+)?(?:the\s+)?(?:associated\s+)?"
        r"funerary objects?)?"
        r"|cultural items?|sacred objects?|unassociated funerary objects?"
        r"|objects? of cultural patrimony)")

# Repair for the generic affiliation leadin. It is lazy and requires an
# article after the conjunction, which is normally what stops it at the right
# place - but "the human remains and THE associated funerary object and the
# Kaibab Band ..." satisfies it one clause too early, and the captured list
# then begins 'associated funerary object and the Kaibab Band'. The entity
# still resolved correctly, but party_name_verbatim is supposed to be what the
# notice called the nation, so a polluted verbatim is a defect in its own
# right. Stripping a LEADING object clause is safe: no nation's name begins
# with one.
OBJ_PREFIX_RE = re.compile(
    r"^(?:(?:un)?associated\s+)?(?:funerary objects?|human remains|cultural items?|"
    r"sacred objects?|objects? of cultural patrimony)"
    r"(?:\s+described (?:in this notice|above))?\s*,?\s+(?:and|to)\s+(?:the\s+)?",
    re.I)


def strip_object_prefix(span):
    prev = None
    while prev != span:
        prev = span
        span = OBJ_PREFIX_RE.sub("", span).strip()
    return span
AFFIL_LEADINS = [
    re.compile(
        r"relationship of shared group identity (?:that|which) can be reasonably "
        r"traced between\s+" + _DEM + _OBJ +
        r"(?:\s+described (?:in this notice|above|herein))?\s*,?\s*"
        r"(?:and|to)\s+" + _DEM + r"(?P<L>.+?)(?=" + _SENT + r")", re.I),
    re.compile(
        r"reasonable connection between\s+" + _DEM + _OBJ +
        r"(?:\s+described in this notice)?\s+and\s+" + _DEM +
        r"(?P<L>.+?)(?=" + _SENT + r")", re.I),
    # THE CURRENT WORDING, and it is not a variant of the old one.
    #
    # Notices published under the 2023 rule increasingly state the finding as
    # a plain "There is a connection between the human remains and associated
    # funerary objects described in this notice and the Absentee-Shawnee Tribe
    # ...; Cherokee Nation; ...". The statutory phrase 'relationship of shared
    # group identity that can be reasonably traced' is simply gone.
    #
    # Without this pattern every 2025 and 2026 inventory completion tested had
    # NO affiliation finding extracted at all - the newest and most useful end
    # of the series would have shipped empty while looking complete, because
    # the notices still parsed and still produced institution, MNI and dates.
    re.compile(
        r"There is a connection between\s+" + _DEM + _OBJ +
        r"(?:\s+described in this notice)?\s+and\s+" + _DEM +
        r"(?P<L>.+?)(?=" + _SENT + r")", re.I),
    re.compile(
        r"There is a connection between\s+" + _DEM +
        r"[^.]{0,140}?\s*,?\s+and\s+" + _DEM +
        r"(?P<L>.+?)(?=" + _SENT + r")", re.I),
    # 'traced between these remains and PRESENT-DAY MEMBERS OF Hui Malama I Na
    # Kupuna O Hawai'i Nei'. The bridge phrase replaces the article, so the
    # patterns above cannot reach the organisation. Placed before the generic
    # rule below because that rule requires an article and would miss it.
    re.compile(
        r"relationship of shared group identity (?:that|which) can be reasonably "
        r"traced between\s+[^.]{0,220}?\s+(?:and|to)\s+present[- ]day members of\s+"
        r"(?:the\s+)?(?P<L>.+?)(?=" + _SENT + r")", re.I),
    # Last resort, still anchored on the statutory phrase: skip an object
    # clause of ANY wording. The named list is not enough - a 1994 notice says
    # "between the figure and the Pueblo of Zuni", and 'figure', 'mandible',
    # 'cranium', 'bundle' and 'war god' are all object words the FR has used.
    #
    # Safe because it is lazy AND requires 'the' after the conjunction: against
    # "between the human remains and associated funerary objects and the Pit
    # River Tribe" the first candidate stop ('human remains and ') is followed
    # by 'associated', not 'the', so it backtracks to the real boundary rather
    # than truncating the list.
    re.compile(
        r"relationship of shared group identity (?:that|which) can be reasonably "
        r"traced between\s+" + _DEM + r"[^.]{0,110}?\s*,?\s*(?:and|to)\s+"
        + _DEM + r"(?P<L>.+?)(?=" + _SENT + r")", re.I),
    re.compile(
        r"(?:are|is) culturally affiliated with\s+" + _DEM +
        r"(?P<L>.+?)(?=" + _SENT + r")", re.I),
]

# 43 CFR 10.7 disposition: not an affiliation finding at all, but a statutory
# PRIORITY order. Kept as its own relationship so it can never be read as, or
# counted with, a cultural-affiliation determination.
# THE CULTURALLY UNIDENTIFIABLE FINDING - the other half of NAGPRA.
#
# Hundreds of notices determine the OPPOSITE of an affiliation: "Pursuant to 25
# U.S.C. 3001(2), a relationship of shared group identity CANNOT be reasonably
# traced between the Native American human remains and any present-day Indian
# tribe." Culturally unidentifiable human remains are the central and most
# contested category in NAGPRA's history, and a dataset that recorded only
# affirmative findings would make them invisible - a notice determining that
# no nation can be identified would look identical to a notice the parser
# simply failed on.
#
# It is also the single most dangerous sentence in the corpus for a matcher.
# It names nations immediately afterwards - as ABORIGINAL LAND holders and as
# disposition recipients - and reading either as cultural affiliation would
# assert exactly the determination the institution declined to make.
CULT_UNID_RE = re.compile(
    r"relationship of shared group identity\s+(?:that\s+|which\s+)?"
    r"can\s?not be reasonably traced", re.I)

# Those two other findings, each recorded under its own relationship.
#
# Aboriginal land is a judicial fact about TERRITORY, established by the Indian
# Claims Commission or the Court of Federal Claims. It is not a statement that
# the ancestors are of that nation.
ABORIGINAL_RES = [
    re.compile(r"is the aboriginal land of\s+(?:the\s+)?(?P<L>.+?)"
               r"(?=" + _SENT + r")", re.I),
    re.compile(r"aboriginal (?:lands?|territory) of\s+(?:the\s+)?(?P<L>.+?)"
               r"(?=" + _SENT + r")", re.I),
]

DISPOSITION_RES = [
    # 43 CFR 10.11 disposition of culturally unidentifiable remains: "Pursuant
    # to 43 CFR 10.11(c)(1), the disposition of the human remains may be to
    # Kalispel Indian Community of the Kalispel Reservation." This appears
    # inside INVENTORY COMPLETION notices, not only in intended-disposition
    # ones, which is why the disposition search is no longer gated on
    # notice_type.
    re.compile(r"disposition of the (?:human remains|cultural items|"
               r"Native American human remains)[^•.]{0,70}?"
               r"\s(?:may be|will be|is|shall be)\s+to\s+(?:the\s+)?(?P<L>.+?)"
               r"(?=" + _SENT + r")", re.I),
    # The finding names the nation FIRST: "The Ute Indian Tribe of the Uintah &
    # Ouray Reservation, Utah has priority for disposition of the human remains
    # described in this notice." Anchored on the determination bullet so the
    # capture cannot start mid-paragraph.
    # `[^•]` not `.` - a lazy dot crosses bullet boundaries and starts the
    # capture at the FIRST finding ("The human remains ... represent the
    # physical remains of one individual"), not the disposition one.
    re.compile(r"[•]\s*(?:The\s+)?(?P<L>[^•]{3,200}?)\s+(?:has|have) priority "
               r"for disposition", re.I),
    re.compile(r"priority for disposition (?:of the [^.]{0,80}?)?"
               r"(?:is|are|belongs to|lies with)\s+(?:the\s+)?(?P<L>.+?)"
               r"(?=" + _SENT + r")", re.I),
    re.compile(r"disposition of the (?:human remains|cultural items)"
               r"[^.]{0,120}?\bto\s+the\s+(?P<L>.+?)(?=" + _SENT + r")", re.I),
]

# The 2023-rule notices distinguish nations the institution found a connection
# to from nations that merely wrote in support: "... The Seminole Nation of
# Oklahoma WITH LETTERS OF SUPPORT FROM the Alabama-Coushatta Tribe of Texas
# and the Jena Band of Choctaw Indians." A letter of support is not an
# affiliation determination, and swallowing the tail into the affiliated list
# would assert one for two nations that made none - so the clause is split off
# and carried under its own relationship.
LETTERS_RE = re.compile(r"\s+with letters? of support from\s+", re.I)

# The operative sentence: who the notice says the ancestors or items may
# actually go to. In the 1994-95 notices this is the ONLY named-party sentence
# there is - they predate the formulaic affiliation finding entirely, and
# without this span 68 of the first 435 notices named nobody at all. It is kept
# as its own relationship and never merged into culturally_affiliated: a
# repatriation can run to a joint requestor, or to a tribe acting on behalf of
# others, without that being the affiliation determination.
REPAT_TO_RES = [
    re.compile(r"Repatriation of the [^.]{0,110}?\bto the\s+(?P<L>.+?)"
               r"\s+may (?:begin|proceed|occur)", re.I),
    re.compile(r"may be repatriated to\s+(?:the\s+)?(?P<L>.+?)(?=" + _SENT + r")", re.I),
    # The 1994-95 notices frequently report a repatriation that has ALREADY
    # happened - 'The object has been transferred to representatives of the
    # Pueblo of Zuni' - and that sentence is the only place the nation is
    # named. Without it those notices name nobody.
    re.compile(r"(?:has|have) been (?:transferred|repatriated|returned) to\s+"
               r"(?:the\s+)?(?:representatives of\s+)?(?:the\s+)?"
               r"(?P<L>.+?)(?=" + _SENT + r")", re.I),
    re.compile(r"(?:was|were) repatriated[^.]{0,40}?\sto\s+"
               r"(?:the\s+)?(?:representatives of\s+)?(?:the\s+)?"
               r"(?P<L>.+?)(?=" + _SENT + r")", re.I),
]

STATE_WORDS = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana", "maine",
    "maryland", "massachusetts", "michigan", "minnesota", "mississippi",
    "missouri", "montana", "nebraska", "nevada", "new hampshire", "new jersey",
    "new mexico", "new york", "north carolina", "north dakota", "ohio",
    "oklahoma", "oregon", "pennsylvania", "rhode island", "south carolina",
    "south dakota", "tennessee", "texas", "utah", "vermont", "virginia",
    "washington", "west virginia", "wisconsin", "wyoming",
    "district of columbia", "puerto rico", "guam", "american samoa",
}
USPS = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT",
    "delaware": "DE", "florida": "FL", "georgia": "GA", "hawaii": "HI",
    "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
    "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME",
    "maryland": "MD", "massachusetts": "MA", "michigan": "MI",
    "minnesota": "MN", "mississippi": "MS", "missouri": "MO",
    "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM",
    "new york": "NY", "north carolina": "NC", "north dakota": "ND",
    "ohio": "OH", "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA",
    "rhode island": "RI", "south carolina": "SC", "south dakota": "SD",
    "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT",
    "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY", "district of columbia": "DC",
    "puerto rico": "PR", "guam": "GU", "american samoa": "AS",
}

# THE REFUSE LIST. A fragment that reduces to nothing but these words is a
# county, a river or a mountain, and must never resolve to a nation - however
# confident the resolver is. NAGPRA notices are dense with such names, and the
# span discipline above should mean this rarely fires; `guard_refusals` in the
# run report is the check on that, because a high count would mean the spans
# are picking up prose rather than tribe lists.
TRAP_WORDS = {"creek", "cherokee", "colorado", "ojibwe", "shawnee", "oneida",
              "apache", "central", "eagle", "river", "mountain", "santa"}

# The SAME trap, from the other side, and it is the more dangerous direction.
#
# `resolve_entity`'s containment rule accepts a match when one core is a subset
# of the other. The spine contains Alaska villages whose whole name is a single
# ordinary word - Council, Eagle, Central, Barrow. Under containment, spine
# core {council} is a subset of "Blackfeet Tribal Business Council" -> and the
# Blackfeet consultation would have been booked to the Native Village of
# Council, 3,000 miles away. Measured: 38 such matches in the first 435
# notices, saved from being written only because a same-named ANCSA
# corporation happened to make them ambiguous.
#
# So: a spine entity whose core is nothing but non-distinctive words may match
# by EQUALITY but may never SWALLOW a longer name.
NON_DISTINCTIVE = TRAP_WORDS | {
    "council", "village", "community", "town", "city", "state", "north",
    "south", "east", "west", "big", "little", "lower", "upper", "grand",
    "white", "red", "black", "blue", "round", "star", "bear", "elk", "hill",
    "point", "bay", "cove", "spring", "springs", "st", "saint", "new", "old",
    "hawaiian", "alaska", "association", "group", "organization",
}
ORG_WORD_RE = re.compile(
    r"\b(tribe|tribes|tribal|nation|nations|band|bands|pueblo|village|"
    r"community|rancheria|colony|reservation|corporation|corp|inc|council|"
    r"organization|association|society|foundation|museum|committee|"
    r"consortium|agency|department|office|hui|ohana|estate|schools?)\b", re.I)
PERSONAL_NAME_RE = re.compile(
    r"^(?:Mr\.|Mrs\.|Ms\.|Dr\.)\s|^[A-Z][a-z]+\s+and\s+[A-Z][a-z]+\s+[A-Z][a-z]+$"
    r"|^[A-Z][a-z]+\s+[A-Z]\.\s+[A-Z][a-z]+$")
CORP_FORM_RE = _pr.CORP_FORM_RE
core = _pr.core
GEO_TAIL = {"county", "counties", "parish", "borough", "township", "city",
            "state", "valley", "canyon", "creek", "river", "mountain",
            "mountains", "lake", "island", "site", "reservoir"}

# Boilerplate that names no one. These are recorded as generic references so
# the count of notices with NO enumerated consultation is measurable, but they
# are never party rows and never proposed as aliases.
GENERIC_RES = [
    re.compile(r"^(the\s+)?(appropriate\s+)?indian tribes?(\s+or\s+native hawaiian"
               r"\s+organizations?)?$", re.I),
    re.compile(r"^(the\s+)?native hawaiian organizations?$", re.I),
    re.compile(r"^(the\s+)?(consulting|invited|following|above[- ]named)\s+"
               r"(parties|tribes?|indian tribes?)$", re.I),
    re.compile(r"^(the\s+)?tribes?$", re.I),
    re.compile(r"^(any|all|other|various)\b.{0,60}$", re.I),
    re.compile(r"^(the\s+)?(present[- ]day\s+)?indian tribes?\b.{0,40}$", re.I),
    re.compile(r"^(the\s+)?lineal descendants?\b.{0,60}$", re.I),
    re.compile(r"^(the\s+)?(tribal|indian)\s+(representatives?|officials?)$", re.I),
    # A statutory definition quoted mid-sentence is not a party:
    # 'a Native Hawaiian organization as defined in 25 U.S.C. 3001(11)'.
    re.compile(r"\b(?:as defined in|25 U\.?S\.?C|43 CFR|Public Law)\b", re.I),
    # The statutory description of Native Hawaiians, quoted verbatim: "the
    # descendants of the aboriginal people who, prior to 1778, occupied and
    # exercised sovereignty in the area that now constitutes the State of
    # Hawai'i". A definition, not an organisation.
    re.compile(r"^(?:the\s+)?descendants? of the aboriginal", re.I),
    re.compile(r"^(?:the\s+)?aboriginal (?:people|inhabitants)", re.I),
    # Descriptions of a class of party rather than a party.
    re.compile(r"^(?:the\s+)?culturally[- ]affiliated\b", re.I),
    re.compile(r"^(?:a|an)\s+non-?\s?federally[\s-]recognized\b", re.I),
    re.compile(r"^(?:the\s+)?(?:tribes?|indian groups?)\s+and\s+the\s+indian\b", re.I),
    re.compile(r"^(?:the\s+)?(?:above|following|listed)\b", re.I),
]

# Every word that appears in a state or territory name. Used only by the
# containment exemption above.
STATE_TOKENS = {w for s in STATE_WORDS for w in s.split()}


def is_generic(frag):
    return any(rx.match(frag.strip()) for rx in GENERIC_RES)


COUNTY_TAIL_RE = re.compile(r"\b(count(?:y|ies)|parish|borough)\s*$", re.I)

# A NAME IS NOT A SENTENCE.
#
# Where a span regex over-reaches it captures narrative prose, and the resolver
# then finds a nation's name inside the narrative. Three false attributions got
# through this way before the guard existed, and every one of them looked like
# a clean match in the output:
#
#   'human remains representing one individual were uncovered during a legally
#    authorized runway construction'          -> The NATIVE Project
#   'associated funerary object should contact Joseph Horse Capture, Associate
#    Curator, Minneapolis ...'                -> Tohono O'odham
#   'human remains ... removed from the KARLUK ONE site (4...)'
#                                             -> Karluk  (an Alaska village,
#                                                named here only as a dig site)
#
# The last is the whole hazard of this dataset in one row: an archaeological
# site named after a place is not the nation of that place, and the notice was
# making no claim of the kind the row asserted.
#
# None of these words can occur in the name of a nation or an organisation, so
# a fragment containing one is prose and is refused outright.
PROSE_WORDS = re.compile(
    r"\b(?:were|was|been|being|representing|removed|recovered|excavated|"
    r"uncovered|donated|collected|purchased|described|contact|telephone|"
    r"pursuant|minimum|individual|individuals|remains|funerary|patrimony|"
    r"notice|catalog|catalogue|accession|approximately|thereof|excavation|"
    r"believed|identified|located|consists|consisting|during|between)\b", re.I)


def refuses_alone(frag):
    """The trap guard. True = never resolve this fragment, whatever it matches.

    The geographic-tail test is deliberately narrow. An earlier version refused
    anything whose last word was in GEO_TAIL, which threw out the NARRAGANSETT
    INDIAN TRIBE OF RHODE ISLAND - because the last word is 'island'. A guard
    against false attribution that erases a real nation's consultation has done
    the same kind of damage it was built to prevent, just quietly. So a
    geographic word only disqualifies a SHORT fragment that is nothing else
    ('Eagle River', 'Bear Creek'), while '... County' is refused outright at
    any length.
    """
    toks = [t for t in norm(frag).split() if t not in ("the", "of", "and")]
    if not toks:
        return True
    if PROSE_WORDS.search(frag):
        return True
    if COUNTY_TAIL_RE.search(frag) or "county" in toks or "counties" in toks:
        return True
    if set(toks) <= TRAP_WORDS:
        return True
    if len(toks) <= 2 and toks[-1] in GEO_TAIL:
        return True
    return False


PARTY_STRIP_RE = re.compile(
    r"^(?:and\s+)?(?:the\s+)?|[\s,;.]+$", re.I)


def split_parties(span):
    """A tribe-list span -> the verbatim names the Federal Register wrote.

    Delimiter choice is the FR's own, not an invention:

      * If the span contains a SEMICOLON, the drafter used semicolons because
        the names themselves contain commas ('Pit River Tribe, California;
        Redding Rancheria, California'). Split on semicolons only.
      * Otherwise the names contain no commas and a comma split is safe -
        except for two mechanical repairs that involve no name knowledge:
        a fragment that is bare a state name belongs to the fragment before it
        ('Santa Ynez Band of Chumash Indians of the Santa Ynez Reservation,
        California'), and a fragment with unbalanced parentheses continues
        into the next ('Wichita and Affiliated Tribes (Wichita, Keechi, Waco
        & Tawakonie), Oklahoma').

    Bare ' and ' is NOT a delimiter here. 'Confederated Tribes and Bands of the
    Yakama Nation' would be cut in half. The caller handles the two-name
    'A and B' case by splitting only when BOTH halves resolve to the spine.
    """
    span = span.strip().rstrip(".")
    parts = span.split(";") if ";" in span else span.split(",")
    merged = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if merged:
            prev = merged[-1]
            bare = re.sub(r"^and\s+", "", p, flags=re.I).strip().rstrip(".").lower()
            # A trailing geographic or corporate qualifier, or an unclosed
            # parenthesis in the previous fragment, all mean the comma was
            # INSIDE a name rather than between two names:
            #   'Kamehameha Schools/Bishop Estate, Inc.'      -> party 'Inc'
            #   'Navajo Nation, Arizona, New Mexico & Utah'   -> 'New Mexico & Utah'
            #   '... Village, AK'                             -> 'AK'
            #   'Wanapum Band, a non-Federally recognized Indian group'
            # Each of those produced a phantom party name before its rule
            # existed, and the last one is the worst of them: it turned a
            # descriptor of a nation's FEDERAL STATUS into a nation.
            if is_state_only(bare) or bare in CORP_SUFFIX \
                    or APPOSITIVE_RE.match(p) \
                    or prev.count("(") != prev.count(")"):
                merged[-1] = prev + ", " + p
                continue
        merged.append(p)
    out = []
    for p in merged:
        p = re.sub(r"^\s*and\s+", "", p, flags=re.I).strip(" ,;.")
        p = re.sub(r"^the\s+", "", p, flags=re.I).strip()
        if not p:
            continue
        # 'X on behalf of Y' names TWO parties and the FR uses it often
        # ('Chugach Heritage Foundation on behalf of the Native Village of
        # Eyak'). Both are recorded - but only fragments that read as
        # organisations, because the same construction also carries the names
        # of private individuals ('the Blackfeet Nation, on behalf of George
        # and Melinda Kipp') and a person is not a party to a bridge like this.
        if re.search(r"\bon behalf of\b", p, re.I):
            subs = [s.strip(" ,.") for s in
                    re.split(r"\s+on behalf of\s+", p, flags=re.I)]
            subs = [re.sub(r"^the\s+", "", s, flags=re.I).strip() for s in subs]
            keep = [s for s in subs
                    if s and ORG_WORD_RE.search(s) and not PERSONAL_NAME_RE.match(s)]
            out.extend(keep or [subs[0]] if subs else [])
            continue
        out.append(p)
    return out


CORP_SUFFIX = {"inc", "inc.", "incorporated", "llc", "l.l.c.", "ltd", "ltd.",
               "corp", "corp.", "corporation", "co", "co.", "company", "lp"}

STATE_ABBR = set(USPS.values())
# A federal-status descriptor, not a name. The FR appends these to a nation's
# name in apposition and the comma split otherwise promotes them to parties.
APPOSITIVE_RE = re.compile(
    r"^(?:a|an)\s+(?:non-?\s?federally[\s-]recognized|federally[\s-]recognized|"
    r"state[\s-]recognized|unrecognized|non-?recognized)\b", re.I)


def is_state_only(s):
    """True if the fragment is nothing but state names/abbreviations.

    Covers 'California', 'AK', and the multi-state tails the FR writes for
    nations spanning several states - 'Navajo Nation, Arizona, New Mexico &
    Utah'.
    """
    parts = [p.strip() for p in re.split(r"\s*(?:&|\band\b|,)\s*", s or "")
             if p.strip()]
    return bool(parts) and all(
        p.lower() in STATE_WORDS or p.upper() in STATE_ABBR for p in parts)


# ------------------------------------------------------------- institution ---

TYPE_PREFIX_RE = re.compile(
    # `Notice To Rescind a Notice of Inventory Completion: <institution>` is a
    # real title form on 6 notices; without this lead the whole rescission
    # phrase ends up inside institution_name.
    r"^(?:Notice To Rescind an?\s+)?"
    r"Notice of (?:Inventory Completion|Intent to Repatriate|"
    r"Intended Repatriation|Intended Disposition)\b", re.I)
# THE 2015+ TITLE FORM PUTS AN OBJECT PHRASE BETWEEN THE NOTICE TYPE AND THE
# COLON: "Notice of Intent To Repatriate Cultural Items: <institution>".
# TYPE_PREFIX_RE stops at "Repatriate", the startswith(":") test then fails,
# and the parser falls through to title_remainder keeping "Cultural Items:"
# inside institution_name - 857 of 6,792 rows, splitting 287 institutions in
# two (Codex PR #29 finding 6). Anchored on a lookahead for the colon, so
# where there is no colon nothing is consumed and no institution name can be
# eaten. See code/1077_nagpra_institution_grain.py.
OBJECT_HEAD_RE = re.compile(
    r"^\s*(?:of\s+)?(?:an?\s+|the\s+)?"
    r"(?:Cultural Items?|"
    r"Human Remains(?:\s+and\s+(?:Associated\s+)?Funerary Objects)?|"
    r"Native American Human Remains[^:]{0,80})?"
    r"(?:\s*Amendment)?\s*(?=:)", re.I)
POSSESSION_RE = re.compile(
    r"\b(?:in the (?:possession|control|physical custody) of)\s+", re.I)
CITY_STATE_RE = re.compile(r",\s*([A-Za-z][A-Za-z .'\-]{1,30}?),\s*([A-Z]{2})\s*$")

INST_TYPE_RULES = [
    ("federal_agency", re.compile(
        r"\bU\.?S\.? Department|Bureau of|National Park Service|Forest Service|"
        r"Army Corps|Department of the Interior|Department of Agriculture|"
        r"Bureau of Land Management|Bureau of Reclamation|Fish and Wildlife|"
        r"Tennessee Valley Authority|Smithsonian|National Forest", re.I)),
    ("tribal", re.compile(r"\bTribe\b|\bNation\b|\bPueblo\b|Tribal ", re.I)),
    ("university", re.compile(r"Universit|College|Institute of Technology", re.I)),
    ("state_agency", re.compile(
        r"\bState of\b|Department of Environment|State Historic|"
        r"State Archaeolog|Division of|Commonwealth of", re.I)),
    ("historical_society", re.compile(r"Historical Society|History Connection|"
                                      r"Historic(?:al)? Commission", re.I)),
    ("museum", re.compile(r"Museum|Gallery|Center for|Science Cent", re.I)),
]


def parse_institution(title):
    """Institution string, city and state, from the notice title.

    The title of a NAGPRA notice is a controlled string: the notice type, a
    colon, the institution(s), then ', City, ST'. The 1994-96 notices predate
    that convention and name the institution in prose after 'in the possession
    of', which is handled as a second shape. Nothing is inferred beyond those
    two shapes - a title matching neither yields the whole title, flagged.
    """
    t = re.sub(r"\s+", " ", (title or "").strip())
    body, how = "", ""
    m = TYPE_PREFIX_RE.match(t)
    rest = t[m.end():] if m else t
    _om = OBJECT_HEAD_RE.match(rest)
    if _om:
        rest = rest[_om.end():]
    if rest.lstrip().startswith(":"):
        body, how = rest.lstrip()[1:].strip(), "title_colon"
    else:
        pm = POSSESSION_RE.search(rest)
        if pm:
            body, how = rest[pm.end():].strip(), "title_possession"
        else:
            body, how = rest.strip(" :,"), "title_remainder"
    body = re.sub(r"\s*;?\s*Correction\s*$", "", body, flags=re.I).strip(" ,;")
    # 'in the Control of the Alaska State Office' leaves a leading article that
    # would make 'the Field Museum' and 'Field Museum' two institutions.
    body = re.sub(r"^the\s+", "", body, flags=re.I).strip()
    city = state = ""
    cm = CITY_STATE_RE.search(body)
    if cm:
        city, state = cm.group(1).strip(), cm.group(2)
        body = body[:cm.start()].strip(" ,")
    return body, city, state, how


def institution_type(name):
    for label, rx in INST_TYPE_RULES:
        if rx.search(name or ""):
            return label
    return "other"


# A notice can be issued jointly - 'Lassen National Forest ... and Phoebe A.
# Hearst Museum of Anthropology', or 'in the Control of the Bureau of Indian
# Affairs and in the Possession of the Oshkosh Public Museum'. Counting the
# joined string as one institution overstates the number of distinct holders
# and hides both parties from a per-institution view.
# SPLIT ON THE SEMICOLON FIRST. The Federal Register separates co-holders
# with "; " and closes the list with "; and ". Splitting on ", and " first
# cuts INSIDE ordinary organisation names: "South Carolina Department of
# Parks, Recreation, and Tourism" became two institutions, one of them
# "Tourism, Columbia, SC", which does not exist (Codex PR #29 finding 8). The
# legacy rule is kept for the pre-2000 titles that carry no semicolon.
INST_SEMI_RE = re.compile(r";")
# SPLIT ON THE SEMICOLON FIRST. The Federal Register separates co-holders
# with "; " and closes the list with "; and ". Splitting on ", and " first
# cuts INSIDE ordinary organisation names: "South Carolina Department of
# Parks, Recreation, and Tourism" became two institutions, one of them
# "Tourism, Columbia, SC", which does not exist (Codex PR #29 finding 8). The
# legacy rule is kept for the pre-2000 titles that carry no semicolon.
INST_SEMI_RE = re.compile(r";")
# SPLIT ON THE SEMICOLON FIRST. The Federal Register separates co-holders
# with "; " and closes the list with "; and ". Splitting on ", and " first
# cuts INSIDE ordinary organisation names: "South Carolina Department of
# Parks, Recreation, and Tourism" became two institutions, one of them
# "Tourism, Columbia, SC", which does not exist (Codex PR #29 finding 8). The
# legacy rule is kept for the pre-2000 titles that carry no semicolon.
INST_SEMI_RE = re.compile(r";")
# SPLIT ON THE SEMICOLON FIRST. The Federal Register separates co-holders
# with "; " and closes the list with "; and ". Splitting on ", and " first
# cuts INSIDE ordinary organisation names: "South Carolina Department of
# Parks, Recreation, and Tourism" became two institutions, one of them
# "Tourism, Columbia, SC", which does not exist (Codex PR #29 finding 8). The
# legacy rule is kept for the pre-2000 titles that carry no semicolon.
INST_SEMI_RE = re.compile(r";")
INST_SPLIT_RE = re.compile(
    r",\s+and\s+|;\s+and\s+|\s+and in the (?:possession|control|physical custody) of\s+",
    re.I)


def institution_parts(body):
    _b = body or ""
    _segs = _b.split(";") if ";" in _b else INST_SPLIT_RE.split(_b)
    parts = [re.sub(r"^\s*and\s+", "", p.strip(" ,;."), flags=re.I)
             for p in _segs if p.strip()]
    parts = [re.sub(r"^the\s+", "", p, flags=re.I).strip() for p in parts]
    # Strip a trailing ', City, ST' from each part, not just the last.
    out = []
    for p in parts:
        cm = CITY_STATE_RE.search(p)
        out.append(p[:cm.start()].strip(" ,") if cm else p)
    return [p for p in out if p]


# ---------------------------------------------------------------- geography --

# 'recovered from' is the 1990s wording and 'excavated from' appears
# throughout; all three describe the same fact - where the ancestors were
# taken from.
REMOVED_RE = re.compile(
    r"\b(?:removed|recovered|excavated|collected|exhumed) from\s+(?P<L>[^.]{2,240})",
    re.I)
# Fallback for the 1996-98 title form, which carries the provenance the body
# sometimes leaves implicit:
#   'Notice of Inventory Completion for Native American Human Remains From
#    Unalakleet, AK, in the Control of the Alaska State Office ...'
TITLE_PROV_RE = re.compile(
    r"\bFrom\s+(?P<L>[^,]{2,60}(?:,\s*[A-Z]{2})?)\s*,?\s*in the (?:Control|Possession"
    r"|Physical Custody) of", re.I)
COUNTY_RE = re.compile(
    r"\b([A-Z][A-Za-z'\.\- ]{1,28}?)\s+Count(?:y|ies)\b")
ABBR_STATE_RE = re.compile(r",\s*([A-Z]{2})\b")
FULL_STATE_RE = re.compile(
    r"\b(" + "|".join(sorted((s.title() for s in STATE_WORDS), key=len,
                             reverse=True)) + r")\b")

DATE_TXT = r"([A-Z][a-z]+\s+\d{1,2},\s+\d{4})"
ELIGIBLE_RE = re.compile(r"may (?:occur|proceed|begin)\s+on or after\s+" + DATE_TXT, re.I)
DEADLINE_RE = re.compile(r"(?:by|before)\s+" + DATE_TXT, re.I)
MONTHS = {m: i for i, m in enumerate(
    "january february march april may june july august september october "
    "november december".split(), 1)}


def to_iso(s):
    m = re.match(r"([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})", (s or "").strip())
    if not m or m.group(1).lower() not in MONTHS:
        return ""
    return f"{int(m.group(3)):04d}-{MONTHS[m.group(1).lower()]:02d}-{int(m.group(2)):02d}"


# ------------------------------------------------------------- the parser ----

def parse_notice(meta, text):
    """One cached notice -> (notice_row, [party_rows_without_resolution])."""
    text = clean_fr_text(text)
    sec = split_sections(text)
    whole = flatten(text)
    pre = sec.get("_preamble", "")

    # template
    # `parse_template` is a structural label, and it has to stay honest about
    # WHY a notice is unheaded. 44 of the 46 post-2012 notices this first
    # classified as `A_early_freeform` are CORRECTIONS - short amendment
    # notices that carry no sections because they have nothing to section. A
    # column that calls a 2016 correction "early freeform" invites a reader to
    # conclude the 1990s drafting style persisted for twenty years. It did not.
    if "requests" in sec and re.search(r"SUMMARY:", pre):
        tmpl = "C_2024_rule"
    elif ("determinations" in sec or "consultation" in sec
          or re.search(r"Officials of ", whole)
          or re.search(r"SUMMARY:|SUPPLEMENTARY INFORMATION:", pre)):
        tmpl = "B_nps_template"
    elif meta["is_correction"] == "1":
        tmpl = "correction_unheaded"
    else:
        tmpl = "A_early_freeform"

    # ---- the subject statement: what this notice is ABOUT ------------------
    summary = ""
    ms = re.search(r"SUMMARY:\s*(.+?)(?=\s+DATES:|\s+ADDRESSES:|$)", pre, re.S)
    if ms:
        summary = ms.group(1).strip()
    if not summary:
        mn = re.search(r"Notice is here(?:by)? given[^.]{0,600}?\.", whole, re.I)
        summary = mn.group(0) if mn else ""
    neg = {g.lower().rstrip("s") for m in NEG_PRESENT_RE.finditer(whole)
           for g in [m.group(1)]}
    cats = []
    for label, rx in CATEGORY_PHRASES:
        if rx.search(summary or meta["title"]):
            cats.append(label)
    # 'No associated funerary objects are present' in the description overrides
    # a category the summary boilerplate mentioned.
    if any("associated funerary object" in n and not n.startswith("un")
           for n in neg) and "associated_funerary_objects" in cats \
            and not OBJ_COUNT_RES["associated_funerary_objects"].search(whole):
        cats.remove("associated_funerary_objects")

    # ---- MNI ---------------------------------------------------------------
    det = sec.get("determinations", "")
    # The 1994-98 notices carry no headings at all, so there is no
    # Determinations SECTION to scope to - but they do carry the determination
    # SENTENCE ('officials have determined that ... represent the physical
    # remains of one individual of Native American ancestry'). Falling back to
    # the whole document is safe for this one pattern because the phrase
    # appears nowhere else; scoping stays in force wherever the section exists.
    det_src = det or whole
    mni_stmts, mni_vals = [], []
    for rx, where, tag in ((MNI_DET_RE, det_src, "determinations"),
                           (MNI_REMOVED_RE, whole, "description"),
                           (MNI_NEW_RE, whole, "description_new_rule")):
        for m in rx.finditer(where):
            mni_stmts.append(f"{tag}:{m.group(0).strip()}")
            mni_vals.append((tag, to_int(m.group(1))))
    det_hits = [v for t, v in mni_vals if t == "determinations" and v is not None]
    desc_hits = [v for t, v in mni_vals if t != "determinations" and v is not None]
    # STATED, NEVER INFERRED. One determination finding is the notice's own
    # total. Several removal events are several numbers and are NOT added up.
    if len(det_hits) == 1:
        mni_total, mni_basis = det_hits[0], "determinations_finding"
    elif not det_hits and len(set(desc_hits)) == 1 and len(desc_hits) == 1:
        mni_total, mni_basis = desc_hits[0], "single_description_statement"
    else:
        mni_total, mni_basis = "", (
            "multiple_statements_not_summed" if (det_hits or desc_hits)
            else "no_mni_stated")

    # ---- object counts -----------------------------------------------------
    obj_counts = {}
    for key, rx in OBJ_COUNT_RES.items():
        vals = [to_int(m.group(1)) for m in rx.finditer(det)] or \
               [to_int(m.group(1)) for m in rx.finditer(whole)]
        vals = [v for v in vals if v is not None]
        obj_counts[key] = vals[0] if len(set(vals)) == 1 and vals else ""
    ci = CULTURAL_ITEMS_RE.findall(whole)
    ci_vals = {to_int(x) for x in ci}
    cultural_items_total = (to_int(ci[0]) if len(ci_vals) == 1 and ci else "")

    # ---- tribe-list spans --------------------------------------------------
    parties, spans_found = [], []

    def take(span_text, relationship, label):
        """Record the parties in one span.

        `cut_at_sentence` is not belt-and-braces. Some span patterns end on a
        phrase rather than on a sentence boundary - 'Repatriation of the ... to
        the X may occur' - and their capture group can therefore run PAST a
        full stop to reach the terminator later in the paragraph. Against the
        2023-rule boilerplate it did exactly that, and swept up 'Requests for
        repatriation may be submitted by any lineal descendant, Indian Tribe,
        or Native Hawaiian organization not identified in this notice who
        shows, by a preponderance of the evidence ...' as a list of parties.
        """
        span_text = cut_at_sentence(span_text)
        if not span_text:
            return
        # Letters of support are a different finding; peel them off first.
        parts = LETTERS_RE.split(span_text, maxsplit=1)
        head = parts[0]
        support = parts[1] if len(parts) > 1 else ""
        spans_found.append(label)
        for frag in split_parties(head):
            parties.append({"party_name_verbatim": frag,
                            "relationship": relationship,
                            "source_span_label": label,
                            "source_span_text": span_text[:600]})
        for frag in split_parties(support):
            parties.append({"party_name_verbatim": frag,
                            "relationship": "letter_of_support",
                            "source_span_label": label + "+letters_of_support",
                            "source_span_text": span_text[:600]})

    consult_src = sec.get("consultation") or whole
    for rx in CONSULT_RES:
        m = rx.search(consult_src)
        if m:
            take(m.group("L"), "consulted",
                 "consultation_section" if "consultation" in sec else "body_sentence")
            break

    # THE 'Requests for Repatriation' SECTION IS BOILERPLATE AND IS EXCLUDED.
    #
    # Under the 2023 rule it recites who MAY request repatriation - "any lineal
    # descendant, Indian Tribe, or Native Hawaiian organization not identified
    # in this notice who shows, by a preponderance of the evidence ..." - in
    # every notice, about nobody. Searched, it manufactures parties: five
    # phantom rows per modern notice, two of which resolved to a real entity.
    #
    # Sections are also searched BEFORE the whole document rather than
    # concatenated with it. Concatenating meant every finding matched twice,
    # once in its own section and once in the copy of that section inside
    # `whole`.
    sectioned = " ".join(x for x in (det, sec.get("cultural_affiliation", ""),
                                     sec.get("additional_requestors", "")) if x)
    body_only = whole
    if sec.get("requests"):
        body_only = body_only.replace(sec["requests"], " ")
    aff_src = sectioned or body_only
    # ALL matches of the first pattern that fires, not just the first match.
    # A notice can make several affiliation findings - the University of
    # Pennsylvania Museum's 1996 Hawai'i notice makes two, for two separately
    # catalogued groups of ancestors. Taking only the first would have dropped
    # the second finding while reporting the notice as fully parsed.
    for rx in AFFIL_LEADINS:
        ms = list(rx.finditer(aff_src)) or list(rx.finditer(body_only))
        if ms:
            for m in ms:
                take(strip_object_prefix(m.group("L")),
                     "culturally_affiliated", "affiliation_finding")
            break

    # NOT gated on notice_type: a 43 CFR 10.11 disposition finding sits inside
    # ordinary inventory-completion notices whenever the remains were found
    # culturally unidentifiable.
    for rx in DISPOSITION_RES:
        mm = rx.search(aff_src) or rx.search(body_only)
        if mm:
            take(mm.group("L"), "disposition_priority", "disposition_finding")
            break

    for rx in ABORIGINAL_RES:
        mm = rx.search(aff_src) or rx.search(body_only)
        if mm:
            take(mm.group("L"), "aboriginal_land", "aboriginal_land_finding")
            break

    for rx in REPAT_TO_RES:
        m = rx.search(sec.get("additional_requestors", "") or body_only)
        if m:
            take(m.group("L"), "repatriation_recipient", "repatriation_sentence")
            break

    # ---- geography ---------------------------------------------------------
    counties, states, removal_stmts = [], [], []
    for m in REMOVED_RE.finditer(whole):
        seg = m.group("L").strip()
        removal_stmts.append(seg[:200])
        for c in COUNTY_RE.findall(seg):
            c = c.strip()
            # 'removed from Kingsley Cave (CA-Teh-1), Tehama County, CA' - the
            # county token can trail a site description; keep the last 1-2 words.
            c = " ".join(c.split()[-3:])
            if c and c.lower() not in ("the", "a"):
                counties.append(c)
        for s in ABBR_STATE_RE.findall(seg):
            states.append(s)
        for s in FULL_STATE_RE.findall(seg):
            states.append(USPS[s.lower()])
    prov_basis = "body_removal_statement" if removal_stmts else ""
    if not removal_stmts:
        tm = TITLE_PROV_RE.search(meta["title"])
        if tm:
            seg = tm.group("L").strip()
            removal_stmts.append(seg)
            prov_basis = "title_from_clause"
            for c in COUNTY_RE.findall(seg):
                counties.append(" ".join(c.strip().split()[-3:]))
            states += ABBR_STATE_RE.findall(seg)
            states += [USPS[s.lower()] for s in FULL_STATE_RE.findall(seg)]
    counties = sorted(set(counties))
    states = sorted(set(states))

    # ---- dates -------------------------------------------------------------
    dsrc = (meta.get("dates_field") or "") + " " + whole
    em = ELIGIBLE_RE.search(dsrc)
    eligible = to_iso(em.group(1)) if em else ""
    deadline = ""
    if not eligible:
        dm = DEADLINE_RE.search((meta.get("dates_field") or "")) or \
             DEADLINE_RE.search(sec.get("additional_requestors", "")) or \
             DEADLINE_RE.search(whole)
        if dm:
            deadline = to_iso(dm.group(1))
    window = ""
    ref = eligible or deadline
    if ref and meta["publication_date"]:
        try:
            window = (date.fromisoformat(ref)
                      - date.fromisoformat(meta["publication_date"])).days
        except ValueError:
            window = ""

    # NAGPRA also provides for repatriation to a LINEAL DESCENDANT rather than
    # to a nation (25 U.S.C. 3005(a)(1)). Those notices correctly name no
    # affiliated tribe, so the flag distinguishes "this notice made no
    # affiliation finding" from "the parser found none". The individual is
    # NEVER recorded - a private person's name has no place in this bridge.
    # Both wordings the FR uses for an actual finding. Deliberately NOT the
    # post-2024 boilerplate "Requests for repatriation may be submitted by any
    # lineal descendant, Indian Tribe, or Native Hawaiian organization", which
    # appears in every modern notice and asserts nothing about this one.
    lineal = "1" if (
        re.search(r"\b(?:is|are)\s+the\s+(?:direct\s+)?lineal descendants?\b",
                  whole, re.I)
        or re.search(r"\blineal descendants?\s+of the individual", whole, re.I)
    ) else "0"

    inst, city, st, how = parse_institution(meta["title"])
    resp = ""
    rm = re.search(r"sole responsibility of\s+(?:the\s+)?(.+?)(?=\.(?:\s|$)|,\s*and)",
                   whole, re.I)
    if rm:
        cand = rm.group(1).strip()[:200]
        # The pre-2016 template names no one here - it says "the museum,
        # institution, or Federal agency that has control of the Native
        # American human remains". Storing that as a responsible party would
        # dress boilerplate up as a fact, so it is left empty instead.
        if not re.match(r"museum,\s*institution,\s*or Federal agency", cand, re.I):
            resp = cand

    row = {
        "document_number": meta["document_number"],
        "publication_date": meta["publication_date"],
        "publication_year": meta["publication_date"][:4],
        "notice_type": meta["notice_type"],
        "notice_title_form": meta["notice_title_form"],
        "statute_stage": meta["statute_stage"],
        "is_correction": meta["is_correction"],
        "title": meta["title"],
        "institution_name": inst,
        "institution_city": city,
        "institution_state": st,
        "institution_primary": (institution_parts(inst) or [""])[0],
        "institution_names_all": "|".join(institution_parts(inst)),
        "institution_count": len(institution_parts(inst)),
        "institution_name_basis": how,
        "institution_type_derived": institution_type(inst),
        "responsible_party_statement": resp,
        "object_categories": "|".join(cats),
        "mni_total_stated": mni_total,
        "mni_basis": mni_basis,
        "mni_statement_count": len(mni_stmts),
        "mni_statements": " || ".join(mni_stmts[:12]),
        "n_associated_funerary_objects_stated":
            obj_counts["associated_funerary_objects"],
        "n_unassociated_funerary_objects_stated":
            obj_counts["unassociated_funerary_objects"],
        "n_sacred_objects_stated": obj_counts["sacred_objects"],
        "n_objects_of_cultural_patrimony_stated":
            obj_counts["objects_of_cultural_patrimony"],
        "cultural_items_total_stated": cultural_items_total,
        "removal_counties": "|".join(counties),
        "removal_states": "|".join(states),
        "removal_location_statements": " || ".join(
            list(dict.fromkeys(removal_stmts))[:6]),
        "removal_location_basis": prov_basis,
        "repatriation_eligible_date": eligible,
        "response_deadline_date": deadline,
        "window_days_derived": window,
        "lineal_descendant_determination": lineal,
        "culturally_unidentifiable": "1" if CULT_UNID_RE.search(whole) else "0",
        "parse_template": tmpl,
        "spans_found": "|".join(sorted(set(spans_found))),
        "n_parties_named": len(parties),
        "agency_names": meta["agency_names"],
        "html_url": meta["html_url"],
        "pdf_url": meta["pdf_url"],
        "source_url": meta["html_url"],
        "full_text_url": TEXT_URL.format(
            y=meta["publication_date"][:4], m=meta["publication_date"][5:7],
            d=meta["publication_date"][8:10], dn=meta["document_number"]),
        "parent_dataset": "federal_actions.csv (Cedar Press Dataset 9)",
        # WAS `TODAY`. See cache_fetched_date() - this is a property of
        # the cached artifact, not of the run that parsed it.
        "fetched_date": cache_fetched_date(
            cache_path(meta["publication_date"], meta["document_number"])),
        "artifact_mtime": artifact_mtime(
            cache_path(meta["publication_date"], meta["document_number"])),
    }
    return row, parties


def build_stage():
    spine_raw = read_csv(SPINE / "cedar_entity_spine.csv")
    # A read-only VIEW. `resolve_entity` searches canonical_name and aliases;
    # the spine's `fr_official_name` column holds exactly the long official
    # form NAGPRA notices use ('Pit River Tribe, California') and would
    # otherwise be invisible to it. Folding it into the alias list of an
    # in-memory copy uses the one resolver on more of the spine's own data -
    # it does not re-implement matching, and data/spine/ is never written.
    spine = []
    for r in spine_raw:
        r = dict(r)
        extra = (r.get("fr_official_name") or "").strip()
        if extra:
            r["aliases"] = ((r.get("aliases") or "") + "|" + extra).strip("|")
        spine.append(r)
    log(f"spine entities: {len(spine):,} "
        f"({sum(1 for r in spine_raw if (r.get('fr_official_name') or '').strip()):,} "
        f"carry fr_official_name)")

    # C5. `led_notices.rows_in` is every row of the parent corpus, not the
    # 6,774 that survive the title filter - the filter is itself a drop and it
    # is the one this dataset is built on.
    led_notices = RowLedger("data/clean/nagpra_notices.csv")
    docs = universe(led_notices)
    log(f"NAGPRA notice universe (title-anchored): {len(docs):,}")

    notices, party_rows, unparsed = [], [], []
    missing = 0
    for meta in docs:
        p = cache_path(meta["publication_date"], meta["document_number"])
        if not p.exists():
            missing += 1
            led_notices.note("rejected:no_cached_full_text_retrieved_for_this_"
                             "document", meta["document_number"])
            unparsed.append({"document_number": meta["document_number"],
                             "publication_date": meta["publication_date"],
                             "title": meta["title"][:180],
                             "reason": "no_cached_full_text",
                             "html_url": meta["html_url"]})
            continue
        with gzip.open(p, "rt", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        try:
            row, parties = parse_notice(meta, text)
        except Exception as exc:                       # never silently skip
            # The exception CLASS, not str(exc): the message can carry a
            # document-specific fragment, which would split one failure mode
            # into hundreds of one-row buckets and hide the shape of it.
            led_notices.note(f"rejected:parse_error:{exc.__class__.__name__}",
                             meta["document_number"])
            unparsed.append({"document_number": meta["document_number"],
                             "publication_date": meta["publication_date"],
                             "title": meta["title"][:180],
                             "reason": f"parse_error:{exc.__class__.__name__}:{exc}",
                             "html_url": meta["html_url"]})
            continue
        # A notice with no tribe-list span still EMITS a notice row - it is
        # recorded in review/nagpra_unparsed.csv as a parser gap, not as a
        # dropped source row, and calling it a rejection here would understate
        # the table by 370.
        led_notices.note("emitted", meta["document_number"])
        notices.append(row)
        for pr in parties:
            pr.update({"document_number": row["document_number"],
                       "publication_date": row["publication_date"],
                       "notice_type": row["notice_type"],
                       "institution_name": row["institution_name"]})
            party_rows.append(pr)
        if not parties:
            unparsed.append({"document_number": meta["document_number"],
                             "publication_date": meta["publication_date"],
                             "title": meta["title"][:180],
                             "reason": f"no_tribe_list_span_found:{row['parse_template']}",
                             "html_url": meta["html_url"]})

    log(f"parsed {len(notices):,} notices; {missing:,} had no cached text")

    # ---- resolution -------------------------------------------------------
    cache, stats = {}, Counter()

    # TWO VIEWS OF THE SPINE, chosen by the shape of the name being resolved.
    #
    # NAGPRA's own definition of "Indian tribe" (25 U.S.C. 3001(7)) expressly
    # INCLUDES ANCSA village and regional corporations, so they cannot simply
    # be excluded - a notice really can name Koniag, Incorporated as a party.
    # But the spine holds both 'Teller' (the federally recognised village
    # government) and 'Teller Native Corporation', and their cores are
    # identical once 'native'/'corporation' are stripped as structural. Every
    # such pair resolves to `ambiguous_core` and is lost.
    #
    # The notice itself breaks the tie: it writes 'Native Village of Teller'
    # for the government and spells out 'Corporation' for the corporation. So a
    # fragment with no corporate form in it is matched against the spine
    # WITHOUT the ANCSA corporations. This is the same principle as standing
    # rules 2 and 3 - name shape decides which legal person is meant - applied
    # in the direction NAGPRA needs.
    ANCSA_CORP_CLASSES = {"Alaska Native Village Corporation",
                          "Alaska Native Regional Corporation",
                          "ANCSA Group Corporation"}
    # The CNSF- layer is the spine's federal CONSTITUENCY sub-units - 'Shoshone-
    # Bannock Tribes of the Fort Hall Reservation - Fort Hall Bannock Band',
    # 'Minnesota Chippewa Tribe - Fond du Lac Band'. They exist so federal
    # money can be split within a tribe; they are not NAGPRA parties, and the
    # nation they sit under is separately in the spine. Left in, they made
    # 'Shoshone-Bannock Tribes of the Fort Hall Reservation of Idaho'
    # permanently ambiguous between two of its own bands, so the notice
    # resolved to nobody. Keyed on the id prefix rather than entity_class,
    # because all 22 carry the generic class 'Federal-level constituency
    # entity' and the prefix is the thing that actually means sub-unit.
    def is_subunit(r):
        return r["tribe_id"].startswith("CNSF-")

    spine_nocorp = [r for r in spine
                    if r["entity_class"] not in ANCSA_CORP_CLASSES
                    and not is_subunit(r)]
    spine_all = [r for r in spine if not is_subunit(r)]
    log(f"  resolution views: {len(spine_all):,} entities, "
        f"{len(spine_nocorp):,} excluding ANCSA corporations")

    def accept(name, canon, how):
        """Post-hoc test on a match the resolver already made.

        Only one thing is checked, and only for containment: a spine entity
        whose core is nothing but non-distinctive words may not SWALLOW a
        longer name.

          rejected   Council            inside  Blackfeet Tribal Business Council
          rejected   White Mountain     inside  White Mountain Apache Tribe
          rejected   Council            inside  Hawai'i Island Burial Council

        Three exemptions, each narrow, each earned by a case the blunt rule got
        wrong:

          * equality - `Council` == `Native Village of Council` is the entity.

          * a pure geographic qualifier - `Oneida` inside `Oneida Nation of New
            York` adds only the words of a state name, which says WHICH Oneida
            rather than naming a different body. Eleven correct matches.

          * the spine name LEADS the fragment and is at least two words -
            `White Mountain` in `White Mountain Apache Tribe`, `Little River`
            in `Little River Band of Ottawa Indians`, `Colorado River` in
            `Colorado River Indian Tribes`. This is the structural difference
            between a real match and the trap: a nation's name comes first and
            the qualifiers follow, whereas `Council` sits at the TAIL of
            `Blackfeet Tribal Business Council`. The two-word floor is what
            keeps `Central` out of `Central Council of the Tlingit & Haida
            Indian Tribes` and `Creek`, `Santa`, `Eagle` out of everything -
            a single trap word still has to match by equality.
        """
        if how != "containment":
            return True
        sc, fc = core(canon), core(name)
        if not sc:
            return False
        if sc == fc or not (sc <= NON_DISTINCTIVE):
            return True
        if bool(fc - sc) and (fc - sc) <= STATE_TOKENS:
            return True
        return len(sc) >= 2 and norm(name).startswith(norm(canon))

    def resolve_one(name, _blocked=None, _depth=0):
        """One name -> (tribe_id, canonical_name, method). View + acceptance.

        On rejection the offending entity is removed and the resolver is asked
        again. Rejecting without retrying threw away the CORRECT answer along
        with the wrong one: 'White Mountain Apache Tribe' was matched to White
        Mountain, Alaska, refused, and then reported unresolved - even though
        the White Mountain Apache Tribe is in the spine and would have been the
        next candidate.
        """
        blocked = _blocked or set()
        base = spine_all if CORP_FORM_RE.search(name) else spine_nocorp
        view = [r for r in base if r["tribe_id"] not in blocked] if blocked else base
        tid, canon, how = resolve_entity(name, view)
        if tid and not accept(name, canon, how):
            stats["containment_rejected"] += 1
            if _depth < 3:
                return resolve_one(name, blocked | {tid}, _depth + 1)
            return None, None, "rejected_nondistinctive_containment"
        return tid, canon, how

    def conj_halves(name):
        """Split 'A and B' - but only where the 'and' really joins two nations.

        Two failures made the extra guards necessary, both from ONE tribe whose
        own name contains 'and':

          'Standing Rock Sioux Tribe of North and South Dakota'
              -> 'Standing Rock Sioux Tribe of North'  +  'South Dakota'

        The first half resolved (to the right tribe, with a mutilated name),
        the second half resolved to something matching 'Washington'/'Dakota',
        and the pair passed the different-entities test. One nation went in and
        two came out, one of them an unrelated organisation. So a half that is
        only geography, or that ends on a dangling qualifier, kills the split.
        """
        halves = [re.sub(r"^the\s+", "", h.strip(" ,;."), flags=re.I).strip()
                  for h in re.split(r"\band\b", name, maxsplit=1, flags=re.I)]
        if len(halves) != 2 or not all(len(h) > 6 for h in halves):
            return []
        if any(is_generic(h) or refuses_alone(h) for h in halves):
            return []
        for h in halves:
            c = core(h)
            if not c or c <= STATE_TOKENS:          # 'South Dakota', 'Washington'
                return []
            if re.search(r"\b(of|the|in|at|for|north|south|east|west|upper|lower)$",
                         h, re.I):                  # '... Tribe of North'
                return []
        return halves

    def resolve(name):
        if name in cache:
            return cache[name]
        if is_generic(name):
            out = ("", "", "generic_reference", "X")
        elif refuses_alone(name):
            stats["guard_refusals"] += 1
            stats["refused_prose" if PROSE_WORDS.search(name)
                  else "refused_placename"] += 1
            out = ("", "", "refused_by_trap_guard", "")
        else:
            tid, canon, how = resolve_one(name)
            if tid and how in ("exact", "alias", "core"):
                # A strong match on the WHOLE string means the whole string is
                # one entity - 'Cheyenne and Arapaho Tribes, Oklahoma' is one
                # nation, not two - so no split is attempted.
                out = (tid, canon, how, "B" if how in ("exact", "alias") else "C")
            else:
                # CONTAINMENT ON A CONJOINED STRING IS THE DANGEROUS CASE.
                #
                # 'Seneca Nation of New York and the Seneca-Cayuga Tribe of
                # Oklahoma' resolved by containment to CAYUGA NATION OF NEW
                # YORK - a third nation that shares the most tokens with the
                # merged string. Two nations went in, one unrelated nation came
                # out, and it looked like a clean match. On this dataset that
                # is a false statement about whose ancestors are at issue.
                #
                # So where the whole string only reaches containment, the split
                # is tried FIRST and wins if both halves land on DIFFERENT
                # entities. Containment is accepted only when the split fails.
                out = ("", "", how, "")
                halves = conj_halves(name)
                if halves:
                    got = [resolve_one(h) for h in halves]
                    if all(g[0] for g in got) and got[0][0] != got[1][0]:
                        cache[name] = ("SPLIT", "|".join(g[0] for g in got),
                                       "conjunction_split", "C")
                        return cache[name]
                if tid:
                    out = (tid, canon, how, "C")
        cache[name] = out
        return out

    # C5, second ledger. One row IN is one fragment the span parser cut out of
    # a tribe-list span; one row OUT is one bridge row. The two are not equal
    # in either direction - a conjunction splits one fragment into two bridge
    # rows, and the de-duplication at the end collapses some - so the ledger
    # carries `_src`, the index of the fragment a bridge row came from, and
    # settles every fragment's disposition AFTER the dedupe rather than
    # guessing at it here.
    led_bridge = RowLedger("data/clean/nagpra_notice_entity_bridge.csv")
    disp_by_src = {}
    REFUSED_PROSE = ("rejected:fragment_refused_by_the_trap_guard_as_narrative_"
                     "prose_not_a_party_name")
    REFUSED_PLACE = ("rejected:fragment_refused_by_the_trap_guard_as_a_place_"
                     "name_or_trap_word")
    DEDUPED = ("duplicate:same_notice_relationship_and_verbatim_name_already_"
               "recorded_from_an_earlier_span")

    bridge, alias_props, refused = [], Counter(), []
    for _src, pr in enumerate(party_rows):
        led_bridge.seen()
        name = pr["party_name_verbatim"]
        tid, canon, how, tier = resolve(name)
        if tid == "SPLIT":
            for h in conj_halves(name):
                sid, scanon, show = resolve_one(h)
                bridge.append(dict(pr, party_name_verbatim=h,
                                   party_name_as_published=name,
                                   tribe_id=sid, canonical_name=scanon,
                                   resolve_method="conjunction_split+" + show,
                                   confidence_tier="C", resolve_status="resolved",
                                   _src=_src))
                stats["resolved"] += 1
            continue
        # A fragment the guard refused is not a party at all - it is prose or a
        # place name that a span regex over-reached into. Leaving it in the
        # bridge would put a row in a (notice, tribe) table that names no
        # tribe, and would put narrative sentences in front of a human as
        # proposed tribe aliases. It is recorded as a diagnostic instead, so
        # the mis-firing span stays visible without becoming data.
        if how == "refused_by_trap_guard":
            is_prose = bool(PROSE_WORDS.search(name))
            disp_by_src[_src] = REFUSED_PROSE if is_prose else REFUSED_PLACE
            refused.append({"document_number": pr["document_number"],
                            "publication_date": pr["publication_date"],
                            "relationship": pr["relationship"],
                            "span_label": pr["source_span_label"],
                            "refused_fragment": name[:300],
                            "reason": ("prose_not_a_name" if is_prose
                                       else "place_name_or_trap_word")})
            continue

        status = ("generic_reference" if how == "generic_reference"
                  else "resolved" if tid else "unresolved")
        stats[status] += 1
        if status == "unresolved" and not is_generic(name):
            alias_props[name] += 1
        bridge.append(dict(pr, party_name_as_published=name,
                           tribe_id=tid, canonical_name=canon,
                           resolve_method=how, confidence_tier=tier,
                           resolve_status=status, _src=_src))

    # de-duplicate: one row per (notice, relationship, verbatim name)
    seen, deduped = set(), []
    for b in bridge:
        k = (b["document_number"], b["relationship"],
             b["party_name_verbatim"].lower())
        if k in seen:
            continue
        seen.add(k)
        deduped.append(b)
    log(f"bridge rows: {len(bridge):,} -> {len(deduped):,} after de-duplication")
    bridge = deduped

    # Settle every fragment. A fragment counts as `emitted` when AT LEAST ONE
    # bridge row descended from it survived the dedupe; a conjunction that
    # produced two rows of which one collapsed still emitted.
    survivors = {b["_src"] for b in bridge}
    for _src, pr in enumerate(party_rows):
        led_bridge.note(disp_by_src.get(
            _src, "emitted" if _src in survivors else DEDUPED),
            f"{pr['document_number']}: {pr['party_name_verbatim'][:48]}")
    for b in bridge:
        b.pop("_src", None)

    # notice-level rollups computed FROM the bridge, so they can never disagree
    by_doc = defaultdict(lambda: defaultdict(list))
    for b in bridge:
        by_doc[b["document_number"]][b["relationship"]].append(b)
    for row in notices:
        d = by_doc.get(row["document_number"], {})
        for rel, pfx in (("consulted", "consulted"),
                         ("culturally_affiliated", "affiliated"),
                         ("disposition_priority", "disposition_priority"),
                         ("repatriation_recipient", "repatriation_recipient"),
                         ("letter_of_support", "letter_of_support"),
                         ("aboriginal_land", "aboriginal_land")):
            rows_ = d.get(rel, [])
            row[f"n_{pfx}_named"] = len(rows_)
            row[f"n_{pfx}_resolved"] = sum(1 for x in rows_ if x["tribe_id"])
            row[f"{pfx}_entity_ids"] = "|".join(
                sorted({x["tribe_id"] for x in rows_ if x["tribe_id"]}))
        row["n_parties_named"] = sum(len(v) for v in d.values())
        row["n_entities_resolved"] = len(
            {b["tribe_id"] for b in bridge
             if b["document_number"] == row["document_number"] and b["tribe_id"]})
        row["has_resolved_entity"] = "1" if row["n_entities_resolved"] else "0"

    NOTICE_FIELDS = [
        "document_number", "publication_date", "publication_year", "notice_type",
        "notice_title_form", "statute_stage", "is_correction", "title",
        "institution_name", "institution_primary", "institution_names_all",
        "institution_city", "institution_state", "institution_count", "institution_name_basis", "institution_type_derived",
        "responsible_party_statement", "object_categories",
        "mni_total_stated", "mni_basis", "mni_statement_count", "mni_statements",
        "n_associated_funerary_objects_stated",
        "n_unassociated_funerary_objects_stated", "n_sacred_objects_stated",
        "n_objects_of_cultural_patrimony_stated", "cultural_items_total_stated",
        "removal_counties", "removal_states", "removal_location_statements",
        "removal_location_basis",
        "repatriation_eligible_date", "response_deadline_date",
        "window_days_derived",
        "n_consulted_named", "n_consulted_resolved", "consulted_entity_ids",
        "n_affiliated_named", "n_affiliated_resolved", "affiliated_entity_ids",
        "n_disposition_priority_named", "n_disposition_priority_resolved",
        "disposition_priority_entity_ids",
        "n_repatriation_recipient_named", "n_repatriation_recipient_resolved",
        "repatriation_recipient_entity_ids",
        "n_letter_of_support_named", "n_letter_of_support_resolved",
        "letter_of_support_entity_ids",
        "n_aboriginal_land_named", "n_aboriginal_land_resolved",
        "aboriginal_land_entity_ids",
        "n_parties_named", "n_entities_resolved", "has_resolved_entity",
        "lineal_descendant_determination", "culturally_unidentifiable",
        "parse_template", "spans_found", "agency_names",
        "html_url", "pdf_url", "full_text_url", "source_url",
        "parent_dataset", "fetched_date", "artifact_mtime",
    ]
    BRIDGE_FIELDS = [
        "document_number", "publication_date", "notice_type", "institution_name",
        "relationship", "party_name_verbatim", "party_name_as_published",
        "tribe_id", "canonical_name", "resolve_method", "resolve_status",
        "confidence_tier", "source_span_label", "source_span_text",
    ]
    write_csv(OUT_NOTICES, notices, NOTICE_FIELDS)
    write_csv(OUT_BRIDGE, bridge, BRIDGE_FIELDS)
    write_csv(OUT_UNPARSED, unparsed,
              ["document_number", "publication_date", "title", "reason",
               "html_url"])
    write_csv(REVIEW / "nagpra_refused_fragments.csv", refused,
              ["document_number", "publication_date", "relationship",
               "span_label", "refused_fragment", "reason"])
    write_csv(OUT_ALIASES,
              [{"proposed_alias": n, "n_notices": c,
                "first_seen_relationship": next(
                    (b["relationship"] for b in bridge
                     if b["party_name_verbatim"] == n), ""),
                "example_document": next(
                    (b["document_number"] for b in bridge
                     if b["party_name_verbatim"] == n), ""),
                "note": "named in a NAGPRA tribe-list span; did not resolve to "
                        "the 2026 spine - may be a historical name",
                "YOUR_RULING": ""}
               for n, c in alias_props.most_common()],
              ["proposed_alias", "n_notices", "first_seen_relationship",
               "example_document", "note", "YOUR_RULING"])

    # LAST, and after the outputs are on disk: a conservation ledger that
    # disagreed with the table it describes would be worse than none.
    merge_conservation([led_notices, led_bridge])

    report(notices, bridge, unparsed, stats, alias_props)


def report(notices, bridge, unparsed, stats, alias_props):
    log("")
    log("=" * 68)
    log("NOTICES")
    log(f"  parsed                        {len(notices):,}")
    for k, v in Counter(r["notice_type"] for r in notices).most_common():
        log(f"    {k:<26} {v:>6,}")
    log(f"  corrections (amend an earlier notice) "
        f"{sum(1 for r in notices if r['is_correction'] == '1'):,}")
    log("  by parse template")
    for k, v in Counter(r["parse_template"] for r in notices).most_common():
        log(f"    {k:<26} {v:>6,}")

    log("")
    log("INSTITUTIONS")
    insts = Counter(p for r in notices
                    for p in (r["institution_names_all"] or "").split("|") if p)
    log(f"  distinct institutions named   {len(insts):,}")
    log(f"  jointly issued notices        "
        f"{sum(1 for r in notices if int(r['institution_count'] or 0) > 1):,}")
    for k, v in insts.most_common(15):
        log(f"    {v:>5,}  {k[:66]}")
    log("  by derived type")
    for k, v in Counter(r["institution_type_derived"] for r in notices).most_common():
        log(f"    {k:<20} {v:>6,}")

    log("")
    log("PARTIES (the bridge)")
    log(f"  rows                          {len(bridge):,}")
    for k, v in Counter(b["relationship"] for b in bridge).most_common():
        log(f"    {k:<26} {v:>6,}")
    log("  resolution")
    for k, v in Counter(b["resolve_status"] for b in bridge).most_common():
        log(f"    {k:<26} {v:>6,}")
    ents = {b["tribe_id"] for b in bridge if b["tribe_id"]}
    log(f"  distinct spine entities reached {len(ents):,}")
    aff = {b["tribe_id"] for b in bridge if b["tribe_id"]
           and b["relationship"] == "culturally_affiliated"}
    con = {b["tribe_id"] for b in bridge if b["tribe_id"]
           and b["relationship"] == "consulted"}
    log(f"    reached as culturally affiliated {len(aff):,}")
    log(f"    reached as consulted             {len(con):,}")
    log(f"  distinct verbatim names       "
        f"{len({b['party_name_verbatim'].lower() for b in bridge}):,}")
    log(f"  unresolved distinct names     {len(alias_props):,} "
        f"-> review/nagpra_alias_proposals.csv")
    log(f"  fragments refused as not-a-name {stats['guard_refusals']:,} "
        f"(kept out of the bridge -> review/nagpra_refused_fragments.csv)")
    log(f"    prose, not a name           {stats['refused_prose']:,}")
    log(f"    place name / trap word      {stats['refused_placename']:,}")

    n_res = sum(1 for r in notices if r["has_resolved_entity"] == "1")
    log("")
    log(f"NOTICES WITH >=1 RESOLVED SPINE ENTITY  {n_res:,} of {len(notices):,} "
        f"({n_res / max(len(notices), 1):.1%})")

    log("")
    log("MNI")
    have = [r for r in notices if str(r["mni_total_stated"]) != ""]
    log(f"  notices with a stated total   {len(have):,}")
    log(f"  total individuals, summed over notices that state one: "
        f"{sum(int(r['mni_total_stated']) for r in have):,}")
    for k, v in Counter(r["mni_basis"] for r in notices).most_common():
        log(f"    {k:<34} {v:>6,}")

    log("")
    log("CULTURAL AFFILIATION DETERMINATIONS")
    cu = [r for r in notices if r["culturally_unidentifiable"] == "1"]
    log(f"  notices finding NO affiliation traceable  {len(cu):,}  "
        f"(culturally unidentifiable, 43 CFR 10.11)")
    log(f"    of which we assert an affiliation anyway "
        f"{sum(1 for r in cu if int(r['n_affiliated_named'] or 0) > 0):,}  "
        f"<- MUST BE 0")
    log(f"    naming an aboriginal-land holder instead "
        f"{sum(1 for r in cu if int(r['n_aboriginal_land_named'] or 0) > 0):,}")
    log(f"    naming a disposition priority instead    "
        f"{sum(1 for r in cu if int(r['n_disposition_priority_named'] or 0) > 0):,}")
    log(f"  notices with a lineal-descendant finding   "
        f"{sum(1 for r in notices if r['lineal_descendant_determination'] == '1'):,}")

    log("")
    log("SERIES BY YEAR")
    log("  'consult' counts notices that ENUMERATE the nations consulted. Its "
        "collapse after 2022")
    log("  is the 2023 rule changing what the notice must print, not a change "
        "in consultation.")
    yrs = sorted({r["publication_year"] for r in notices})
    types = ["inventory_completion", "intent_to_repatriate", "intended_disposition"]
    log(f"  {'year':<6}{'inv_compl':>10}{'intent_rep':>11}{'dispos':>8}"
        f"{'total':>7}{'MNI stated':>11}{'consult':>9}{'affil':>7}{'cult_unid':>10}")
    for y in yrs:
        rs = [r for r in notices if r["publication_year"] == y]
        cnt = Counter(r["notice_type"] for r in rs)
        mni = sum(int(r["mni_total_stated"]) for r in rs
                  if str(r["mni_total_stated"]) != "")
        con = sum(1 for r in rs if int(r["n_consulted_named"] or 0) > 0)
        aff = sum(1 for r in rs if int(r["n_affiliated_named"] or 0) > 0)
        unid = sum(1 for r in rs if r["culturally_unidentifiable"] == "1")
        log(f"  {y:<6}{cnt.get(types[0],0):>10,}{cnt.get(types[1],0):>11,}"
            f"{cnt.get(types[2],0):>8,}{len(rs):>7,}{mni:>11,}"
            f"{con:>9,}{aff:>7,}{unid:>10,}")

    log("")
    log("WOULD NOT PARSE")
    for k, v in Counter(u["reason"].split(":")[0] for u in unparsed).most_common():
        log(f"    {v:>6,}  {k}")
    log("=" * 68)


# ------------------------------------------------------------------- main ----

def main():
    global _log_fh
    LOGS.mkdir(parents=True, exist_ok=True)
    _log_fh = open(LOG_PATH, "a", encoding="utf-8")
    log(f"\n=== 77 NAGPRA  {datetime.now().isoformat(timespec='seconds')} "
        f"{' '.join(sys.argv[1:])} ===")
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "fetch":
        lim = int(sys.argv[2]) if len(sys.argv) > 2 else None
        try:
            fetch_stage(lim)
        finally:
            release_host()
    elif cmd == "build":
        build_stage()
    elif cmd == "conservation":
        # `conservation` re-publishes the dataset's durable ledger into the
        # shared file and then verifies it; `conservation verify` only reads.
        rc = 0
        if "verify" not in sys.argv[2:]:
            rc = publish_conservation()
        raise SystemExit(rc or conservation_verify())
    else:
        raise SystemExit(f"unknown command {cmd!r} "
                         f"(fetch | build | conservation [verify])")


if __name__ == "__main__":
    main()
