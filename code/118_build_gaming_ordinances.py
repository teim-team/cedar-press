#!/usr/bin/env python3
"""
Cedar Press - 118: the TRIBAL GAMING ORDINANCE layer.

WHY THIS IS A DISTINCT UNIVERSE, NOT A DUPLICATE OF THE COMPACTS
---------------------------------------------------------------
Under IGRA the two instruments cover different populations:

  * Class III gaming requires a tribal-state COMPACT.  We hold 707 of those,
    reaching 276 tribes.
  * Class II gaming requires an NIGC-approved tribal gaming ORDINANCE and NO
    compact at all (25 U.S.C. 2710(b)).

Every tribe conducting regulated gaming has an ordinance; only the Class III
tribes have a compact.  So the ordinance universe is strictly WIDER, and the
part it adds is exactly the Class II population that compact-derived work
cannot see.

Elijah, 2026-08-07: "what about gaming ordinances, which are all available I
believe and distinct from compacts - maybe they will provide some additional
information."

WHAT AN ORDINANCE IS, AND WHAT IT IS NOT
----------------------------------------
An ordinance is an AUTHORISATION.  A tribe may hold an approved ordinance and
operate nothing at all.  Two rules follow and are enforced in code, not prose:

  1. **Never infer a facility from an ordinance.**  This build writes no
     property row, touches no property file, and asserts that it has not.
  2. **Authorisation is not operation.**  `class_ii_authorized` says the
     ordinance authorises class II; it does not say a class II floor exists.
     A floor can be swapped between classes with no federal record, which is
     why the class actually operated is unobservable here.  Every class field
     carries `measurement_type = AUTHORIZED_MAXIMUM`-style semantics: it is a
     legal permission, and `cedar_domain.may_promote` refuses to turn it into
     a count.

THE DOWNLOAD TRAP (docs/NIGC_REGION_BUILD_LOG.md 15, re-confirmed here)
-----------------------------------------------------------------------
Every `nigc.gov/download/<slug>/` page carries a sidebar WPDM link with the
same `wpdmdl=`.  Matching the first `wpdmdl=` on a page returns the identical
PDF every time, same byte length, looking like success.

On THIS page the trap presents differently and worse: the links live inside
`<table id="tablepress-1">` and each carries its own `wpdmdl`+`ind` pair, but
**one pair is printed twice under two different dates** - Absentee Shawnee's
`wpdmdl=3252&ind=3246` is listed as both the 1995-01-10 ORIGINAL ordinance and
the 2008-03-25 AMENDMENT, and the file served is the 2008 amendment.  So the
index's own date is not a reliable label for the document behind the link.

Three guards, all measurable:
  * links are taken only from inside tablepress-1;
  * every retrieved file is md5'd and a duplicate md5 under a different
    ordinance id is RECORDED as a collision, never silently accepted;
  * the approval date is re-read FROM THE LETTER and compared with the index
    date.  `date_agreement` carries the answer on every row.

PULL DISCIPLINE
---------------
One poller, one host.  `logs/_HOSTLOCK_www.nigc.gov.json` is claimed before the
first request, requests are sequential with a 2 s floor gap, failures back off
60/120/240... and stop at ~30 min, and the manifest is checkpointed so a killed
run resumes without re-fetching.

USAGE
-----
    py -3 code/118_build_gaming_ordinances.py fetch       # index + PDFs
    py -3 code/118_build_gaming_ordinances.py parse       # PDFs -> dataset
    py -3 code/118_build_gaming_ordinances.py reconcile   # 3-population diff
    py -3 code/118_build_gaming_ordinances.py all

Reads   https://www.nigc.gov/office-of-general-counsel/gaming-ordinances/
        data/spine/cedar_entity_spine.csv          (read only)
        data/clean/compacts.csv                    (read only)
        review/nigc_roster_diff_2026-08-06.csv     (read only)
Writes  data/raw/external/nigc_ordinances/...      index, PDFs, manifest
        data/clean/gaming_ordinances.csv
        data/clean/codebook/07f_gaming_ordinances.csv    (FRAGMENT only)
        review/ordinance_compact_diff_<date>.csv
        review/ordinance_unresolved_<date>.csv
        data/interim/118_run_summary.txt

Touches NOTHING else.  compacts.csv, compact_structured_terms.csv,
gaming_facilities.csv, gaming_capacity_official.csv, nigc_*, the ledger, the
spine and codebook_master.csv are read-only or untouched here.
"""

import csv
import hashlib
import html as htmllib
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CODE = CEDAR / "code"
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
INTERIM = CEDAR / "data" / "interim"
RAW = CEDAR / "data" / "raw" / "external" / "nigc_ordinances"
IDX = RAW / "_index"
PDFDIR = RAW / "pdf"
LOGS = CEDAR / "logs"
TODAY = date.today().isoformat()

HOST = "www.nigc.gov"
LOCK = LOGS / f"_HOSTLOCK_{HOST}.json"
STATE = RAW / "_fetch_state.json"
MANIFEST = RAW / "_SOURCE_MANIFEST.csv"
INDEX_URL = ("https://www.nigc.gov/office-of-general-counsel/gaming-ordinances/")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
GAP = 2.0
SCRIPT = "code/118_build_gaming_ordinances.py"

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

# ---------------------------------------------------------------------------
# THE ONE RESOLVER.  Standing rule 8: import it, never re-implement matching.
# ---------------------------------------------------------------------------
_spec = importlib.util.spec_from_file_location(
    "party_rulings", CODE / "33_apply_party_rulings.py")
_pr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pr)
resolve_entity, norm, core = _pr.resolve_entity, _pr.norm, _pr.core

sys.path.insert(0, str(CODE))
import cedar_domain as CD                      # noqa: E402
import cedar_codebook as CB                    # noqa: E402

# An ordinance authorisation must never become an operating count.
assert not CD.may_promote(CD.MeasurementType.AUTHORIZED_MAXIMUM,
                          CD.MeasurementType.ACTIVE_FLOOR_COUNT), \
    "cedar_domain would let an authorisation become a floor count"


def read_csv(p):
    if not Path(p).exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(p, rows, fields):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(p) + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    tmp.replace(p)
    print(f"  wrote {Path(p).relative_to(CEDAR)}  ({len(rows):,} rows)")


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


# ===========================================================================
# FETCH
# ===========================================================================

def curl(url, out_path=None, timeout=180):
    cmd = ["curl", "-s", "-L", "-A", UA,
           "-H", "Accept: text/html,application/xhtml+xml,application/pdf,*/*;q=0.8",
           "--max-time", str(timeout),
           "-w", "%{http_code}\t%{url_effective}", url]
    if out_path:
        cmd[1:1] = ["-o", str(out_path)]
        p = subprocess.run(cmd, capture_output=True, text=True)
        tail = (p.stdout or "").strip().split("\t")
        status = int(tail[0]) if tail and tail[0].isdigit() else 0
        eff = tail[1] if len(tail) > 1 else ""
        return status, eff, None
    p = subprocess.run(cmd, capture_output=True)
    out = p.stdout
    m = re.search(rb"(\d{3})\t(\S*)$", out)
    if not m:
        return 0, "", out
    return int(m.group(1)), m.group(2).decode("utf-8", "replace"), out[:m.start()]


def claim_lock(queue):
    """One poller per host.  Append to an existing lock rather than compete."""
    if LOCK.exists():
        try:
            cur = json.load(open(LOCK))
        except Exception:
            cur = {}
        if cur.get("active") and cur.get("script") != SCRIPT:
            pid = cur.get("pid")
            alive = False
            if pid:
                r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"],
                                   capture_output=True, text=True)
                alive = str(pid) in (r.stdout or "")
            stale = True
            try:
                age = (datetime.utcnow() - datetime.fromisoformat(
                    str(cur.get("started", "")).rstrip("Z"))).total_seconds()
                stale = age > 6 * 3600
            except Exception:
                pass
            if alive and not stale:
                cur.setdefault("queue", []).extend(queue)
                json.dump(cur, open(LOCK, "w"), indent=1)
                print(f"HOSTLOCK held by {cur.get('script')} (pid {pid}); "
                      f"queued {queue} and exiting per docs/PULL_DISCIPLINE.md.")
                sys.exit(0)
    LOGS.mkdir(parents=True, exist_ok=True)
    json.dump({"host": HOST, "pid": os.getpid(), "script": SCRIPT,
               "started": datetime.utcnow().isoformat() + "Z",
               "active": True, "queue": queue,
               "note": "gaming ordinance index + approved-ordinance PDFs"},
              open(LOCK, "w"), indent=1)


def release_lock():
    if LOCK.exists():
        try:
            cur = json.load(open(LOCK))
        except Exception:
            return
        if cur.get("script") == SCRIPT:
            cur["active"] = False
            cur["released"] = datetime.utcnow().isoformat() + "Z"
            json.dump(cur, open(LOCK, "w"), indent=1)
            print("host lock released")


def flat(x):
    return re.sub(r"\s+", " ",
                  htmllib.unescape(re.sub("<[^>]+>", " ", x))).strip()


def parse_index(text):
    """Rows from tablepress-1 ONLY.  Nothing outside the table is an ordinance.

    Column 1 is the tribe as NIGC prints it, column 2 the original ordinance
    (one dated link), column 3 the amendments (zero or more dated links).
    """
    m = re.search(r'<table id="tablepress-1".*?</table>', text, re.S)
    if not m:
        raise SystemExit("tablepress-1 not found - the index layout changed.")
    tab = m.group(0)
    out = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", tab, re.S):
        tds = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)
        if len(tds) < 3:
            continue
        tribe = flat(tds[0])
        if not tribe or tribe.lower() == "tribe name":
            continue
        for kind, cell in (("ORIGINAL_ORDINANCE", tds[1]),
                           ("AMENDMENT", tds[2])):
            for href, d in re.findall(
                    r'href="([^"]+)"[^>]*>\s*(\d{4}-\d{2}-\d{2})', cell):
                url = htmllib.unescape(href)
                wp = re.search(r"wpdmdl=(\d+)", url)
                ind = re.search(r"ind=(\d+)", url)
                out.append({"index_tribe": tribe, "ordinance_type": kind,
                            "index_date": d, "index_url": url,
                            "wpdmdl": wp.group(1) if wp else "",
                            "wpdm_ind": ind.group(1) if ind else ""})
            # A date printed with no link is a fact about the index: NIGC says
            # the instrument exists but posts no document.  Record it.
            linkless = re.sub(r"<a\b.*?</a>", " ", cell, flags=re.S)
            for d in re.findall(r"\d{4}-\d{2}-\d{2}", linkless):
                out.append({"index_tribe": tribe, "ordinance_type": kind,
                            "index_date": d, "index_url": "",
                            "wpdmdl": "", "wpdm_ind": ""})
    return out


def assign_ids(rows):
    """Stable Cedar id: approval date + sequence within that date on the
    index's own order.  NEVER derived from the WPDM id, which is a CMS
    artefact that changes when a file is re-uploaded (NIGC region log 15)."""
    seq = Counter()
    for r in rows:
        seq[r["index_date"]] += 1
        r["ordinance_id"] = (f"NIGC-ORD-{r['index_date'].replace('-', '')}"
                             f"-{seq[r['index_date']]:02d}")
    return rows


def cmd_fetch(argv):
    for d in (RAW, IDX, PDFDIR):
        d.mkdir(parents=True, exist_ok=True)
    claim_lock(["gaming_ordinance_index", "gaming_ordinance_pdfs"])
    try:
        _fetch(argv)
    finally:
        release_lock()


def _fetch(argv):
    state = json.load(open(STATE)) if STATE.exists() else {"done": {}}
    json.dump(state, open(STATE, "w"), indent=1)     # checkpoint before req 1

    idx_html = IDX / "gaming_ordinances_index.html"
    if not idx_html.exists() or "--refetch-index" in argv:
        st, eff, body = curl(INDEX_URL)
        print(f"index {st} {eff} {len(body or b'')} bytes")
        if st != 200:
            raise SystemExit("index fetch failed - refusing to parse a "
                             "non-200 body (a 404 page still has <main>)")
        idx_html.write_bytes(body)
        time.sleep(GAP)
    text = idx_html.read_text(encoding="utf-8", errors="replace")
    rows = assign_ids(parse_index(text))

    dates = [r["index_date"] for r in rows]
    print(f"index rows: {len(rows)}  {min(dates)} .. {max(dates)}")
    print(f"  tribes: {len({r['index_tribe'] for r in rows})}  "
          f"originals: {sum(1 for r in rows if r['ordinance_type'] == 'ORIGINAL_ORDINANCE')}  "
          f"amendments: {sum(1 for r in rows if r['ordinance_type'] == 'AMENDMENT')}")

    # THE INDEX'S OWN DUPLICATE LINKS.  Recorded, never deduplicated away.
    by_url = defaultdict(list)
    for r in rows:
        if r["index_url"]:
            by_url[r["index_url"]].append(r["ordinance_id"])
    dup = {u: v for u, v in by_url.items() if len(v) > 1}
    for u, v in dup.items():
        print(f"  INDEX DUPLICATE LINK: {u} printed under {v}")

    write_csv(IDX / "gaming_ordinances_index.csv", rows,
              ["ordinance_id", "index_tribe", "ordinance_type", "index_date",
               "wpdmdl", "wpdm_ind", "index_url"])

    manifest = read_csv(MANIFEST)
    have = {m["ordinance_id"]: m for m in manifest}
    by_md5 = {m["md5"]: m["ordinance_id"] for m in manifest if m.get("md5")}

    backoff, fails, got = 60, 0, 0
    todo = [r for r in rows if r["index_url"]]
    for i, r in enumerate(todo, 1):
        oid = r["ordinance_id"]
        if oid in have and (PDFDIR / have[oid]["local_name"]).exists():
            continue
        url = r["index_url"].replace("https://www.nigc.gov?",
                                     "https://www.nigc.gov/?")
        tmp = PDFDIR / f"_tmp_{oid}.pdf"
        st, eff, _ = curl(url, out_path=tmp)
        fname = os.path.basename(eff.split("?")[0]) or f"{oid}.pdf"
        if not fname.lower().endswith(".pdf"):
            fname = f"{oid}.pdf"
        head = tmp.read_bytes()[:5] if tmp.exists() else b""
        ok = (st == 200 and tmp.exists() and tmp.stat().st_size > 2000
              and head == b"%PDF-")
        if not ok:
            fails += 1
            print(f"  {oid}: FAILED status={st} "
                  f"size={tmp.stat().st_size if tmp.exists() else 0}")
            if tmp.exists():
                tmp.unlink()
            time.sleep(backoff)
            backoff = min(backoff * 2, 1800)
            if backoff > 1700:
                print("backing off past 30 min - stopping per PULL_DISCIPLINE")
                break
            continue
        backoff = 60
        digest = md5(tmp)
        collision = by_md5.get(digest)
        target = PDFDIR / fname
        if target.exists() and md5(target) != digest:
            target = PDFDIR / f"{Path(fname).stem}__{oid}.pdf"
        os.replace(tmp, target)
        by_md5.setdefault(digest, oid)
        rec = {"ordinance_id": oid,
               "local_path": str(target.relative_to(CEDAR)).replace("\\", "/"),
               "local_name": target.name,
               "source_host": HOST,
               "source_url": r["index_url"],
               "resolved_url": eff,
               "retrieval_note": ("WPDM link taken from inside tablepress-1 on "
                                  "the gaming-ordinances index; 302 resolved to "
                                  "the wp-content object; md5 checked against "
                                  "every file already written"),
               "bytes": target.stat().st_size,
               "md5": digest,
               "md5_duplicate_of": collision or "",
               "index_tribe": r["index_tribe"],
               "index_date": r["index_date"],
               "ordinance_type": r["ordinance_type"],
               "wpdmdl": r["wpdmdl"], "wpdm_ind": r["wpdm_ind"],
               "http_status": st, "fetched_date": TODAY}
        manifest = [m for m in manifest if m["ordinance_id"] != oid] + [rec]
        have[oid] = rec
        state["done"][oid] = digest
        got += 1
        if got % 10 == 0 or i == len(todo):
            write_csv(MANIFEST, manifest, list(rec.keys()))
            json.dump(state, open(STATE, "w"), indent=1)
            print(f"  [{i}/{len(todo)}] {oid} {target.name} {rec['bytes']:,}B "
                  f"{digest[:8]}" + ("  DUPLICATE-MD5" if collision else ""))
        time.sleep(GAP)

    if manifest:
        write_csv(MANIFEST, manifest, list(manifest[-1].keys()))
    json.dump(state, open(STATE, "w"), indent=1)
    dupes = [m for m in manifest if m.get("md5_duplicate_of")]
    print(f"\nretrieved {len(manifest)} of {len(todo)} linked index rows; "
          f"{len({m['md5'] for m in manifest})} distinct md5s; "
          f"{len(dupes)} md5 collisions; {fails} failures")


# ===========================================================================
# EXTRACTION
#
# Every extractor returns (value, verbatim_quote).  A fact that cannot be
# quoted is not written - the same rule the compact parse ran under.  Recall
# is deliberately below precision throughout, and each guard's reason is
# recorded beside it.
# ===========================================================================

def sq(t, i, j, pad=170):
    """A verbatim window, whitespace-collapsed only."""
    return re.sub(r"\s+", " ", t[max(0, i - pad):j + pad]).strip()[:600]


# --- classes -------------------------------------------------------------
# OCR turns roman numerals into l/1 constantly: "Class 111", "Class ll",
# "Class Ill" are all in these documents.  Normalising on the character class
# rather than on the literal "II"/"III" is the difference between 55% recall
# and the real rate.
CLASS_TOK = re.compile(r"\bclass\s*(?:no\.?\s*)?([iIlL1]{1,4}|2|3|two|three)\b",
                       re.I)


def spaced(word):
    """OCR of these scans letter-spaces headings: `11. G a m i n a Authorized`.
    A word matcher that tolerates a space between every character recovers
    those headings without loosening anything else - the words are long enough
    that spurious matches do not occur."""
    return r"\s*".join(re.escape(c) for c in word)


AUTHZ = spaced("authoriz")
AUTH_HEAD = re.compile(
    rf"({spaced('gaming')}\s+(?:activit(?:y|ies)\s+)?{AUTHZ}(?:ed|ation)?"
    rf"|{AUTHZ}(?:ation|ed)\s+of\s+{spaced('gaming')}(?:\s+activit\w*)?"
    rf"|class\s*[iIlL12]{{1,3}}\s+gaming\s+{AUTHZ}(?:ation|ed)"
    rf"|gaming\s+{AUTHZ}ed\s+and\s+regulat\w+)", re.I)
AUTH_VERB = re.compile(
    rf"(hereby\s+{AUTHZ}\w*|is\s+{AUTHZ}\w*|are\s+{AUTHZ}\w*"
    rf"|shall\s+be\s+{AUTHZ}\w*|may\s+be\s+conducted|may\s+conduct"
    rf"|is\s+hereby\s+permitted|are\s+permitted|{AUTHZ}ed\s+to\s+conduct)", re.I)
# The scope sentence every ordinance opens with: "hereby enacts this ordinance
# in order to set the terms for Class II and Class III gaming operations on
# the Indian lands of ...".  That IS the authorisation, stated as scope.
SCOPE_RE = re.compile(
    r"(enacts?\s+this\s+ordinance|set(?:ting)?\s+the\s+terms\s+for"
    r"|this\s+ordinance\s+(?:shall\s+)?(?:govern|appl(?:y|ies)|regulate)\w*"
    r"|provide\s+for\s+the\s+(?:sound\s+)?(?:regulation|licensing)\s+of)", re.I)
# The instrument's own title: "Class II Tribal Gaming Ordinance".
TITLE_CLASS_RE = re.compile(
    r"class\s*([iIlL1]{1,4}|2|3)\s+(?:tribal\s+|and\s+class\s*[iIlL123]{1,4}\s+)?"
    r"gaming\s+(?:ordinance|code)", re.I)
# NEGATION MUST ATTACH TO THE CLASS TOKEN ITSELF.
# A loose "is there a `not` nearby" test over-fired on eight of the first
# fourteen negations and every one was wrong. The misfires were all the same
# shape: an ADJACENT sentence about a DIFFERENT class -
#   "Class I Gaming on the Reservation is not governed by this Code.
#    Class II Gaming. The Community is hereby authorized ..."
# and one worse case where `\bno\b` matched the ordinance's own number,
# "Ordinance, No. 96, to regulate class II gaming", and booked Blackfeet as
# NOT authorised for the class its ordinance exists to authorise.
NEG_BEFORE = re.compile(r"(?:\bno|\bnot|\bneither|\bnor|prohibits?)\s+$", re.I)
NEG_AFTER = re.compile(
    r"^\s*(?:gaming|gambling|activit\w+|games?|operations?)?\s*"
    r"(?:on\s+\w+\s+\w+\s+)?"
    r"(?:is|are|shall|may|will|can)\s+(?:be\s+)?(?:not|never)\b"
    r"|^\s*(?:gaming\s+)?(?:is|are|shall\s+be)\s+prohibit", re.I)


def _class_num(tok):
    t = tok.strip().lower()
    if t in ("2", "two"):
        return "II"
    if t in ("3", "three"):
        return "III"
    if re.fullmatch(r"[il1]+", t):
        return {1: "I", 2: "II", 3: "III"}.get(len(t))
    return None


# A TABLE OF CONTENTS IS NOT A PROVISION.
# `Section 1.05 Gaming Authorized ....... 5` matched the authorisation-heading
# pattern on the Koi Nation ordinance and the 900-character window that
# followed it ran through the rest of the contents page, picking up a class
# token from an unrelated line. Dot leaders are the tell.
TOC_LEADER = re.compile(r"\.{6,}")
# "All Classes of gaming ... is hereby authorized" authorises II and III
# without naming either.
ALLCLASS_RE = re.compile(r"all\s+class(?:es)?\s+of\s+gam(?:ing|bling)", re.I)


def _classes_in(win, offset=0):
    """Classes named in a window, split into authorised and negated."""
    found, neg = set(), set()
    if ALLCLASS_RE.search(win):
        found |= {"II", "III"}
    for cm in CLASS_TOK.finditer(win):
        c = _class_num(cm.group(1))
        if c not in ("II", "III"):
            continue
        before = win[max(0, cm.start() - 18):cm.start()]
        # Stop the forward window at the NEXT class token: a negation that
        # belongs to the following sentence about a different class is not
        # this class's negation.
        after = win[cm.end():cm.end() + 110]
        nxt = CLASS_TOK.search(after)
        if nxt:
            after = after[:nxt.start()]
        if NEG_BEFORE.search(before) or NEG_AFTER.search(after):
            neg.add(c)
        else:
            found.add(c)
    return found, neg


def extract_classes(t):
    """Return (authorized_set, negated_set, quote, basis).

    Five passes, HIGHEST PRECISION FIRST, and the basis is written to the
    dataset so a consumer can filter on how the fact was established.

    A class merely NAMED in a definitions section has NOT been AUTHORISED.
    The compact build refused 1,296 rows for exactly that confusion; the same
    guard runs here, which is why a bare class token never yields a row.
    """
    # 1. An authorisation HEADING, then the classes inside its section.
    for m in AUTH_HEAD.finditer(t):
        win = t[m.start():m.start() + 900]
        if TOC_LEADER.search(win[:250]):
            continue                      # contents page, not a provision
        f, n = _classes_in(win)
        if f or n:
            return f, n, sq(t, m.start(), m.start() + 420, pad=0), \
                "authorisation_section_heading"

    # 2. The ordinance's own scope sentence.
    for m in SCOPE_RE.finditer(t):
        f, n = _classes_in(t[m.start():m.end() + 320])
        if f or n:
            return f, n, sq(t, m.start(), m.end() + 320, pad=0), \
                "ordinance_scope_statement"

    # 3. A class token and an authorising verb inside one window.
    for vm in AUTH_VERB.finditer(t):
        s, e = max(0, vm.start() - 220), vm.end() + 220
        f, n = _classes_in(t[s:e])
        if f or n:
            return f, n, sq(t, s, e, pad=0), "authorising_verb_window"

    # 4. The instrument's own title names its class.
    m = TITLE_CLASS_RE.search(t)
    if m:
        f, n = _classes_in(m.group(0))
        if f or n:
            return f, n, sq(t, m.start(), m.end()), \
                "instrument_title_names_class"

    # 5. LOWEST PRECISION, and labelled as such: the word `authoriz...` within
    #    150 characters of a class token, in a sentence about gaming. This
    #    recovers scanned headings the OCR destroyed and nothing else; every
    #    row it produces carries this basis so it can be excluded wholesale.
    for m in re.finditer(AUTHZ, t, re.I):
        s, e = max(0, m.start() - 90), m.end() + 150
        win = t[s:e]
        if not re.search(r"gam(?:e|ing|ling)", win, re.I):
            continue
        f, n = _classes_in(win)
        if f or n:
            return f, n, sq(t, s, e, pad=0), \
                "authorisation_word_near_class_token"

    return set(), set(), "", "no_authorising_language_found"


# --- tribal gaming agency ------------------------------------------------
# The whole point of this field: the compact parse found 674 reporting
# obligations running to a TRIBAL gaming agency rather than a state one, and
# nobody has assembled who those bodies are.  The ordinance names them.
# LOWERCASE CONNECTORS MUST BE ALLOWED INSIDE THE NAME.
# Without `of`, the capitalised run breaks and the body is truncated to its
# tail: `Jena Band of Choctaw Indians Gaming Commission` became "Choctaw
# Indians Gaming Commission", and `Kickapoo Traditional Tribe of Texas Gaming
# Regulatory Authority` became "Texas Gaming Regulatory Authority" - which
# reads like a STATE agency and would have inverted the fact the column
# exists to record.
AGENCY_RE = re.compile(
    r"((?:[A-Z][\w'’\-\.]*\s+|(?:of|the|and|for|de|del)\s+){0,8}"
    r"(?:Tribal\s+|Tribe\s+|Nation\s+|Community\s+|Band\s+|Pueblo\s+)?"
    r"Gaming\s+(?:Regulatory\s+)?"
    r"(?:Commission|Agency|Authority|Board|Office|Bureau))")
# OCR SPELLS THE FEDERAL REGULATOR WRONG AND IT SLIPS THE NAME FILTER.
# `NeHonel Indian Gaming Commission` is the National Indian Gaming
# Commission with two characters mangled, and it was written as Ysleta del
# Sur's own gaming agency. Any `... Indian Gaming Commission` that shares no
# distinctive token with the tribe is refused.
NIGC_LOOKALIKE = re.compile(r"indian\s+gaming\s+(?:commission|agency)\s*$", re.I)
# The federal regulator and any state body are NOT the tribal gaming agency.
# Filing NIGC as a tribe's own regulator would invert the whole fact.
AGENCY_REJECT = re.compile(
    r"national indian gaming|\bnigc\b|state gaming|state of |commission\s*\(nigc"
    r"|gaming control board of|department of (?:the )?interior", re.I)


# Leading tokens that belong to the sentence, not to the body's name.
# "Executive Director Absentee Shawnee Tribe Gaming Commission" is a person's
# title glued to an agency name; "Nation Class II Gaming Commission" is a
# fragment. Strip them from the left until a token that can start a name.
AGENCY_LEAD_DROP = {
    "executive", "director", "chairman", "chairwoman", "chairperson", "chair",
    "class", "i", "ii", "iii", "the", "a", "an", "of", "to", "by", "and",
    "member", "members", "commissioner", "commissioners", "secretary",
    "treasurer", "attorney", "general", "counsel", "staff", "acting",
    "contact", "cc", "via", "email", "e", "mail", "dear", "sincerely",
    # from measured leaks: "Administrative Assistant St. Croix Gaming
    # Commission", "Authority. Means the Kickapoo ... Authority",
    # "Amended Kickapoo Nation Tribal Gaming Commission"
    "administrative", "assistant", "amended", "restated", "authority",
    "means", "shall", "said", "such", "this", "that", "agency", "commission",
    "office", "president", "governor", "council",
}


def extract_agency(t, tribe_name):
    cands = Counter()
    spans = {}
    tribe_tokens = core(tribe_name)
    for m in AGENCY_RE.finditer(t):
        name = re.sub(r"\s+", " ", m.group(1)).strip(" .,;:")
        toks = name.split()
        while toks and toks[0].strip(".,").lower() in AGENCY_LEAD_DROP:
            toks.pop(0)
        name = " ".join(toks)
        if len(name) < 12 or len(name) > 90:
            continue
        if AGENCY_REJECT.search(name):
            continue
        if NIGC_LOOKALIKE.search(name) and not (core(name) & tribe_tokens):
            continue
        if not re.match(r"^[A-Z]", name):
            continue
        cands[name] += 1
        # Prefer a span that is NOT a table-of-contents line, so the quote
        # shows the body being established rather than a page number.
        is_toc = bool(TOC_LEADER.search(t[max(0, m.start() - 120):m.end() + 120]))
        if name not in spans or (spans[name][2] and not is_toc):
            spans[name] = (m.start(), m.end(), is_toc)
    if not cands:
        return "", "", ""
    # Prefer a body whose name carries the tribe's own distinctive tokens.
    specific = [n for n in cands if core(n) & tribe_tokens]
    pool = specific or list(cands)
    best = max(pool, key=lambda n: (cands[n], len(n)))
    i, j, _toc = spans[best]
    return best, sq(t, i, j), ("tribe_specific_name" if specific
                               else "generic_name_in_ordinance")


# --- revenue allocation plan / per capita --------------------------------
# MEASURED ON THIS CORPUS: the per-capita language is almost always the
# CONDITIONAL statutory recitation of 25 U.S.C. 2710(b)(3) -
#   "If the Tribe elects to make per capita payments to tribal members, it
#    shall authorize such payments only upon approval of a plan submitted to
#    the Secretary of the Interior"
# That sentence proves the ordinance CONTEMPLATES per capita.  It does NOT
# prove a Revenue Allocation Plan exists or that any distribution is made.
# Reading it as evidence of distribution would be the same class of error as
# reading a compact's authorised device cap as an operating floor count.
RAP_RE = re.compile(
    r"(revenue\s+allocation\s+plan|plan\s+to\s+allocate\s+(?:net\s+)?revenue"
    r"|allocation\s+plan\s+(?:submitted|approved)"
    r"|2710\s*\(?\s*b\s*\)?\s*\(?\s*3|522\.4\s*\(b\)\(2\)\(ii\)|522\.6\s*\(b\))",
    re.I)
PERCAP_RE = re.compile(r"per\s*[-‐-― ]?\s*capita", re.I)
COND_RE = re.compile(r"\b(if|should|elects?|may be used to make|in the event)\b",
                     re.I)
ASSERT_RE = re.compile(
    r"(has\s+(?:been\s+)?(?:approved|submitted)|was\s+approved"
    r"|the\s+Secretary\s+(?:has\s+)?approved|approved\s+revenue\s+allocation"
    r"|has\s+elected\s+to\s+make|currently\s+makes|does\s+make"
    r"|makes\s+per\s*[- ]?capita)", re.I)
# "Section 7. Per Capita Payments 6" is a table of contents, not a provision.
TOC_RE = re.compile(r"\.{4,}|\bSection\s+\d+[.\s]+[A-Z][^.]{0,40}\s+\d+\s")
PROHIB_RE = re.compile(
    r"(no\s+per\s*[- ]?capita|shall\s+not\s+(?:be\s+used\s+to\s+)?make\s+per"
    r"\s*[- ]?capita|per\s*[- ]?capita\s+payments?\s+(?:are|is|shall\s+be)\s+"
    r"(?:not\s+(?:be\s+)?)?prohibit)", re.I)


def extract_rap_percap(t):
    rap_m = RAP_RE.search(t)
    rap_val = "REFERENCED" if rap_m else "NOT_REFERENCED"
    rap_q = sq(t, rap_m.start(), rap_m.end()) if rap_m else ""

    # EVERY occurrence is classified, not just the first - the first is very
    # often a table-of-contents line and the governing clause is pages later.
    # Priority: an explicit prohibition, then an assertion that the tribe DOES
    # distribute, then the conditional statutory recitation, then a bare
    # mention.
    best, bq, rank = "NOT_REFERENCED", "", -1
    order = {"PER_CAPITA_PROHIBITED": 4, "PER_CAPITA_PLAN_ASSERTED": 3,
             "PER_CAPITA_CONDITIONAL_RECITATION": 2,
             "PER_CAPITA_REFERENCED_UNQUALIFIED": 1,
             "PER_CAPITA_TABLE_OF_CONTENTS_ONLY": 0}
    for pm in PERCAP_RE.finditer(t):
        s = max(0, pm.start() - 300)
        win = t[s:pm.end() + 300]
        # Offsets come from the match, never from a string .find() of the
        # literal words - PERCAP_RE matches "per-capita" and "per capita"
        # alike and a find() on one of them silently misses the other.
        lead = t[s:pm.start()]
        trail = t[pm.end():pm.end() + 140]
        if PROHIB_RE.search(win):
            v = "PER_CAPITA_PROHIBITED"
        elif ASSERT_RE.search(win):
            v = "PER_CAPITA_PLAN_ASSERTED"
        elif COND_RE.search(lead[-160:]) or COND_RE.search(trail):
            v = "PER_CAPITA_CONDITIONAL_RECITATION"
        elif TOC_RE.search(win):
            v = "PER_CAPITA_TABLE_OF_CONTENTS_ONLY"
        else:
            v = "PER_CAPITA_REFERENCED_UNQUALIFIED"
        if order[v] > rank:
            best, bq, rank = v, sq(t, pm.start(), pm.end(), pad=300), order[v]
    return rap_val, rap_q, best, bq


# --- internal controls ---------------------------------------------------
MICS_RE = re.compile(
    r"(minimum\s+internal\s+control\s+standards?|\bMICS\b|\bTICS\b"
    r"|internal\s+control\s+standards?"
    r"|25\s*C\.?\s*F\.?\s*R\.?\s*(?:Part\s*)?54[23]|Part\s*54[23])", re.I)


def extract_mics(t):
    m = MICS_RE.search(t)
    if not m:
        return "", ""
    refs = {re.sub(r"\s+", " ", x.group(0)).strip()
            for x in MICS_RE.finditer(t)}
    return "|".join(sorted(refs))[:200], sq(t, m.start(), m.end())


# --- licensing -----------------------------------------------------------
LIC_FEATURES = (
    ("KEY_EMPLOYEE_LICENSE", r"key\s+employee"),
    ("PRIMARY_MANAGEMENT_OFFICIAL_LICENSE", r"primary\s+management\s+official"),
    ("FACILITY_LICENSE", r"facility\s+licens|licens\w*\s+of\s+the\s+facility"),
    ("BACKGROUND_INVESTIGATION", r"background\s+(?:investigation|check)"),
    ("VENDOR_LICENSE", r"vendor\s+licens|gaming\s+vendor|supplier\s+licens"),
    ("SUSPENSION_REVOCATION", r"(?:suspend|revoke|revocation)\w*\s+(?:a\s+|the\s+)?licen"),
    ("GAMING_EMPLOYEE_LICENSE", r"gaming\s+employee\s+licens"),
    ("ELIGIBILITY_DETERMINATION", r"eligibility\s+determination"),
)


def extract_licensing(t):
    hits, q = [], ""
    for label, pat in LIC_FEATURES:
        m = re.search(pat, t, re.I)
        if m:
            hits.append(label)
            q = q or sq(t, m.start(), m.end())
    return "|".join(hits), q


# --- dates ---------------------------------------------------------------
MONTHS = {m.lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"], 1)}
MONTH_ALT = ("jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec")
DATE_RE = re.compile(
    rf"\b({MONTH_ALT})[a-z]*\.?\s*,?\s*(\d{{1,2}})\s*,?\s*(\d{{4}})\b", re.I)


def _iso(m):
    key = m.group(1)[:3].lower()
    mon = next((v for k, v in MONTHS.items() if k.startswith(key)), None)
    d, y = int(m.group(2)), int(m.group(3))
    # IGRA was enacted in 1988; no ordinance approval predates it.
    if not mon or not (1 <= d <= 31) or not (1988 <= y <= 2030):
        return None
    return f"{y:04d}-{mon:02d}-{d:02d}"


# The letterhead date sits BEFORE the salutation. Everything after "Dear ..."
# is the body, and the body's first date is almost always the TRIBE's
# submission date - "This letter responds to your letter of January 10, 2000".
# Reading that as the approval date produced 117 false disagreements on the
# first pass, every one of which would have looked like an index defect.
SALUTATION = re.compile(r"\bDear\s+[A-Z]", re.M)
DATE_REJECT_LEAD = re.compile(
    r"(letter\s+of|dated|submitted\s+on|adopted\s+(?:on|by)|request(?:ed)?\s+of"
    r"|received\s+on|your\s+letter|resolution\s+no[^\n]{0,30}|meeting\s+held\s+on"
    r"|effective)\s*$", re.I)
# OCR of the old date STAMPS spaces the digits: `NOV 1 5 1993`, `MAR 2 7 2000`.
STAMP_RE = re.compile(
    rf"\b({MONTH_ALT})[a-z]*\.?\s+(\d)\s*(\d)?\s*,?\s+(\d{{4}})\b", re.I)


def extract_letter_date(page1):
    """The NIGC letterhead date, or nothing.

    A date the OCR destroyed is a MISS, not a licence to take the nearest
    parseable number.  Where the stamp cannot be read the row carries
    LETTER_DATE_NOT_FOUND and the index date stands unchallenged.
    """
    sm = SALUTATION.search(page1)
    head = page1[:sm.start()] if sm else page1[:1200]
    for m in DATE_RE.finditer(head):
        if DATE_REJECT_LEAD.search(head[max(0, m.start() - 45):m.start()]):
            continue
        iso = _iso(m)
        if iso:
            return iso, sq(page1, m.start(), m.end(), pad=80)
    for m in STAMP_RE.finditer(head):
        if DATE_REJECT_LEAD.search(head[max(0, m.start() - 45):m.start()]):
            continue
        day = m.group(2) + (m.group(3) or "")
        key = m.group(1)[:3].lower()
        mon = next((v for k, v in MONTHS.items() if k.startswith(key)), None)
        y = int(m.group(4))
        if mon and 1 <= int(day) <= 31 and 1988 <= y <= 2030:
            return f"{y:04d}-{mon:02d}-{int(day):02d}", \
                sq(page1, m.start(), m.end(), pad=80)
    return "", ""


EFF_RE = re.compile(
    r"(effective\s+(?:date|immediately|upon|as\s+of|on\s+the)[^.;]{0,160}"
    r"|shall\s+(?:become|be)\s+effective[^.;]{0,160})", re.I)


def extract_effective(t):
    m = EFF_RE.search(t)
    if not m:
        return "", ""
    seg = m.group(1)
    dm = DATE_RE.search(seg)
    return (_iso(dm) or "") if dm else "", sq(t, m.start(), m.end())


# --- signature -----------------------------------------------------------
TITLE_RE = re.compile(
    r"^\s*(?:NIGC\s+)?(Acting\s+)?(Chairman|Chairwoman|Chairperson|Chair|"
    r"Vice\s*-?\s*Chair(?:man|woman)?|Associate\s+Commissioner|Commissioner|"
    r"Chief\s+of\s+Staff|Acting\s+General\s+Counsel)\s*,?\s*$", re.I)
NAME_RE = re.compile(r"^[A-Z][A-Za-z.'’\-]+(?:\s+[A-Z][A-Za-z.'’\-]+)"
                     r"{1,3}\s*$")
NAME_REJECT = re.compile(
    r"nigc|national|interior|street|tel|fax|www|regional|office|mail|"
    r"washington|sincerely|attest|enclosure", re.I)


def extract_chair(page_text):
    lines = [l.rstrip() for l in page_text.splitlines()]
    for i, l in enumerate(lines):
        tm = TITLE_RE.match(l)
        if not tm:
            continue
        title = re.sub(r"\s+", " ", l.strip(" ,")).strip()
        for j in range(i - 1, max(-1, i - 6), -1):
            cand = lines[j].strip()
            if not cand:
                continue
            if NAME_REJECT.search(cand) or not NAME_RE.match(cand):
                break
            return f"{cand}, {title}", sq(page_text, page_text.find(cand),
                                          page_text.find(cand) + len(cand), 90)
        # A title with no legible name above it is still a fact about who
        # signed the class of officer; OCR loses signatures constantly.
        return title, sq(page_text, page_text.find(l),
                         page_text.find(l) + len(l), 90)
    return "", ""


# --- supersession --------------------------------------------------------
SUPERSEDE_RE = re.compile(
    r"(supersed\w*|replaces?\s+(?:in\s+its\s+entirety\s+)?the\s+"
    r"(?:tribe’s\s+|tribe's\s+)?(?:prior|previous|existing)|"
    r"amends?\s+and\s+restates?|repeals?\s+and\s+replaces?)[^.]{0,240}", re.I)


def extract_supersedes(t):
    m = SUPERSEDE_RE.search(t)
    if not m:
        return "", "", ""
    seg = m.group(0)
    dm = DATE_RE.search(seg)
    return (_iso(dm) or "") if dm else "", re.sub(r"\s+", " ", seg)[:300], \
        "stated_in_document"


# ===========================================================================
# ENTITY KEYING - one resolver, with the guards the containment defect earned
# ===========================================================================

STATES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT",
    "delaware": "DE", "florida": "FL", "georgia": "GA", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "louisiana": "LA", "maine": "ME", "massachusetts": "MA",
    "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM",
    "new york": "NY", "north carolina": "NC", "north dakota": "ND",
    "ohio": "OH", "oklahoma": "OK", "oregon": "OR", "rhode island": "RI",
    "south carolina": "SC", "south dakota": "SD", "texas": "TX",
    "utah": "UT", "virginia": "VA", "washington": "WA", "wisconsin": "WI",
    "wyoming": "WY",
}


def states_from_name(name):
    """States named INSIDE a tribe's own name, as a SET.

    Three measured traps, all of which produced a WRONG state on the first
    pass and would have refused a correct match:

      * `Alabama-Coushatta Tribe of Texas` - the LEADING token is the tribe's
        own name, not a state. Likewise Delaware Nation, Iowa Tribe, Colorado
        River Indian Tribes, Mississippi Band of Choctaw. So a state token in
        the first two positions is ignored.
      * `Washoe Tribe of Nevada and California` and `Iowa Tribe of Kansas and
        Nebraska` name TWO states. A single answer forces a false
        disagreement, so this returns a set and agreement means membership.
      * Token-sequence matching only: `Otoe-Missouria` must not read as
        Missouri and `Indians` must not read as Indiana.
    """
    toks = norm(name).split()
    out = set()
    for s, ab in STATES.items():
        st = s.split()
        for i in range(2, len(toks) - len(st) + 1):
            if toks[i:i + len(st)] == st:
                out.add(ab)
    return out


# IGRA ordinances are approved for federally recognised TRIBES. A tribal
# college, a BIE school, a CDFI or an ANCSA corporation can never hold one, so
# they are not candidates and must not be offered to the resolver.
#
# This is a domain restriction on the spine VIEW, not a new name matcher
# (standing rule 8). It is also the guard AGENTS.md records as one that works:
# "restrict parents to government-class rows". Measured on this build it is
# what stops `Keweenaw Bay Indian Community` resolving to Keweenaw Bay Ojibwa
# Community COLLEGE - containment scores the college higher because it shares
# two tokens with the record and the tribe's short canonical name shares one.
ORDINANCE_ELIGIBLE_CLASSES = {
    "Federally recognized tribe",
    "Federally recognized Alaska Native Village",
}


def official_name_candidates(name, spine):
    """Eligible spine entities whose FEDERAL REGISTER official name contains
    every distinctive token of the record.

    This is a VERIFICATION leg on the resolver's answer, not a second matcher.
    It is used two ways and only two ways, because both were measured on all
    321 NIGC tribe names:

      * as CORROBORATION where it agrees - 242 of 321 agree, and an agreement
        between a canonical-name match and the Federal Register official name
        is a second leg;
      * as a REFUSAL where it conflicts - 1 case, `Flandreau Santee Sioux
        Tribe`, which the resolver's max-overlap containment sent to *Santee
        Sioux* (Nebraska) because that shares two tokens while the correct
        entity's short canonical name `Flandreau` (South Dakota) shares one.
        The official name settles it, and refusing costs nothing.

    It is NEVER used to resolve a name the resolver refused. Measured on the
    15 refusals it would have produced 7 answers of which at least 3 are
    WRONG - `Cherokee Nation, Oklahoma` to the *United Keetoowah Band*, and
    `Shawnee Tribe of Oklahoma` to the *Eastern* Shawnee Tribe. That is the
    shape of guard AGENTS.md records as measured-and-removed, so it is not
    built in the first place.
    """
    cn = core(name)
    if not cn:
        return set()
    return {r["tribe_id"] for r in spine
            if r.get("fr_official_name") and cn <= core(r["fr_official_name"])}


def key_tribe(name, spine, by_id):
    """Returns (tribe_id, canonical, method, entity_tier, state, reason)."""
    tid, canon, how = resolve_entity(name, spine)
    sts = states_from_name(name)
    st = "|".join(sorted(sts))
    if not tid:
        return "", "", how, "B", st, how
    ent = by_id.get(tid, {})
    offi = official_name_candidates(name, spine)
    if len(offi) == 1 and tid not in offi:
        other = by_id.get(next(iter(offi)), {}).get("canonical_name", "")
        return "", "", how, "B", st, (
            f"official_name_conflict:resolver={ent.get('canonical_name')}"
            f"|federal_register_official_name={other}")
    official_ok = tid in offi and len(offi) == 1
    ent_state = (ent.get("state") or "").strip()
    state_ok = bool(sts and ent_state and ent_state in sts)
    # GUARD 1 - state disagreement. The record names states and the entity is
    # in none of them.
    if sts and ent_state and ent_state not in sts:
        return "", "", how, "B", st, f"state_disagreement:{st}!={ent_state}"
    # GUARD 2 - the record must be at least as specific as the entity.
    # Containment rewards the SHORTEST spine name; that is how NATIVE VILLAGE
    # OF ELIM landed on Elim Native Corporation.
    if how == "containment" and len(core(name)) < len(core(ent.get(
            "canonical_name", ""))):
        return "", "", how, "B", st, "containment_record_less_specific"
    # GUARD 3 - a containment match whose only shared tokens are trap words
    # does not link ON ITS OWN. With state corroboration it does: `Oneida
    # Nation of New York` shares only the trap token `oneida` with the spine's
    # `Oneida`, and that IS the New York nation - the state is the second leg
    # that makes it safe. Refusing it outright was measured and cost a correct
    # match, which is the failure mode AGENTS.md records for over-eager guards.
    if how == "containment" and not state_ok:
        shared = core(name) & core(ent.get("canonical_name", ""))
        if shared and shared <= CD.NAME_TRAPS:
            return "", "", how, "B", st, "containment_on_trap_tokens_only"
    # TWO INDEPENDENT LEGS IS TIER A; ONE LEG IS TIER B.
    # Leg 1 is the canonical-name match. Leg 2 is either a state derived from
    # the record's own name agreeing with the entity's state, or the Federal
    # Register official name confirming the same entity. Containment NEVER
    # reaches A whatever corroborates it - the defect has cost real money in
    # both directions and a second leg does not repair the first.
    tier = "A" if (how in ("exact", "core", "alias")
                   and (state_ok or official_ok)) else "B"
    return tid, ent.get("canonical_name", canon), how, tier, st, ""


# ===========================================================================
# PARSE
# ===========================================================================

FIELDS = [
    # the specified contract, in order
    "ordinance_id", "tribe_id", "tribe_name", "ordinance_type",
    "amendment_number", "approval_date", "effective_date", "chair_or_designee",
    "classes_authorized", "class_ii_authorized", "class_iii_authorized",
    "licensing_provisions", "tribal_gaming_agency_named",
    "revenue_allocation_plan_referenced", "per_capita_referenced",
    "minimum_internal_control_reference", "supersedes_ordinance_id",
    "source_url", "source_quote", "pdf_path", "fetched_date", "tier",
    "confidence", "built_date",
    # historical range - an ordinance amended four times is five rows
    "superseded_by_ordinance_id", "supersedes_basis",
    "effective_range_start", "effective_range_end", "in_force_status",
    # provenance and honest limits
    "index_tribe_name", "index_date", "document_approval_date",
    "date_agreement", "classes_basis", "classes_negated",
    "authorisation_measurement_type", "tribal_gaming_agency_basis",
    "index_anomaly", "document_names_tribe",
    "text_layer_status", "pdf_pages", "pdf_chars", "pdf_md5", "pdf_bytes",
    "resolved_pdf_url", "md5_duplicate_of",
    "entity_match_method", "entity_tier", "entity_state",
    "classes_quote", "tribal_gaming_agency_quote",
    "revenue_allocation_plan_quote", "per_capita_quote", "licensing_quote",
    "minimum_internal_control_quote", "chair_quote", "effective_date_quote",
    "supersedes_quote",
]


def cmd_parse(argv):
    import fitz
    INTERIM.mkdir(parents=True, exist_ok=True)
    full_spine = read_csv(SPINE / "cedar_entity_spine.csv")
    spine = [r for r in full_spine
             if r["entity_class"] in ORDINANCE_ELIGIBLE_CLASSES]
    by_id = {r["tribe_id"]: r for r in full_spine}
    index = read_csv(IDX / "gaming_ordinances_index.csv")
    man = {m["ordinance_id"]: m for m in read_csv(MANIFEST)}
    print(f"index rows {len(index):,}   retrieved PDFs {len(man):,}   "
          f"ordinance-eligible spine entities {len(spine):,} "
          f"of {len(full_spine):,}")

    # The index's own duplicate links, computed once so every affected row can
    # carry the anomaly rather than the finding living only in a log.
    url_count = Counter(r["index_url"] for r in index if r["index_url"])

    rows, unresolved = [], []
    keycache = {}
    for r in index:
        oid = r["ordinance_id"]
        mrec = man.get(oid)
        tribe = r["index_tribe"]
        if tribe not in keycache:
            keycache[tribe] = key_tribe(tribe, spine, by_id)
        tid, canon, method, etier, est, reason = keycache[tribe]

        out = {f: "" for f in FIELDS}
        out.update({
            "ordinance_id": oid, "tribe_id": tid,
            "tribe_name": canon or tribe, "index_tribe_name": tribe,
            "ordinance_type": r["ordinance_type"], "index_date": r["index_date"],
            "approval_date": r["index_date"],
            "entity_match_method": method, "entity_tier": etier,
            "entity_state": est,
            "source_url": r["index_url"] or INDEX_URL,
            "tier": "B", "built_date": TODAY,
            "authorisation_measurement_type": "LEGAL_AUTHORISATION_NOT_A_COUNT",
        })

        # ANOMALIES IN NIGC'S OWN INDEX, recorded on the row rather than
        # smoothed away. IGRA was enacted 17 Oct 1988, so an approval date of
        # 1985-12-02 (Muscogee (Creek) Nation) cannot be an NIGC approval
        # date; it is a fact about the index, and both stay visible.
        anom = []
        if r["index_date"] < "1988-10-17":
            anom.append("INDEX_DATE_PRECEDES_IGRA_ENACTMENT")
        if r["index_url"] and url_count[r["index_url"]] > 1:
            anom.append("INDEX_LINK_PRINTED_UNDER_MORE_THAN_ONE_DATE")
        if not r["index_url"]:
            anom.append("NO_DOCUMENT_LINKED_ON_INDEX")
        if r["index_url"] and not re.match(r"^https?://[\w.\-]+(/|\?|$)",
                                           r["index_url"]):
            # NIGC's index carries `href="http://Cahto Indian Tribe of the
            # Laytonville Rancheria"` - the tribe's NAME pasted into the href.
            anom.append("INDEX_LINK_IS_NOT_A_URL")
        # THE SAME PDF SERVED FOR TWO DIFFERENT TRIBES.
        # Kialegee Tribal Town's 2022-06-02 amendment link (wpdmdl=10058) and
        # the Kalispel Tribe's (wpdmdl=10013) are different links that return
        # a byte-identical file - Kalispel's. Trusting the index would have
        # written Kalispel's ordinance under Kialegee's name. Only md5s catch
        # this; the byte lengths, the dates and the links all look right.
        cross_tribe_file = False
        if mrec and mrec.get("md5_duplicate_of"):
            other = man.get(mrec["md5_duplicate_of"], {})
            oname = other.get("index_tribe", "")
            if oname and oname != tribe:
                # Two index names can be the SAME tribe: NIGC lists Santa
                # Ysabel twice, once as `Iipay Nation of Santa Ysabel
                # (Formally ...)` and once under the old name, and serves the
                # same PDF for both. That is a duplicate listing, not a
                # mislink. Distinctive-token overlap tells them apart.
                if (core(tribe) & core(oname)) - CD.NAME_TRAPS:
                    anom.append("SAME_PDF_UNDER_TWO_INDEX_NAMES_SAME_TRIBE")
                else:
                    anom.append("SAME_PDF_SERVED_FOR_A_DIFFERENT_TRIBE")
                    cross_tribe_file = True
            else:
                anom.append("SAME_PDF_AS_ANOTHER_INSTRUMENT_SAME_TRIBE")
        out["index_anomaly"] = "|".join(anom)

        # Record the tribe in the review queue BEFORE any early exit, so a
        # tribe whose instruments are all image-only scans is still queued.
        if not tid:
            unresolved.append({"ordinance_id": oid, "index_tribe": tribe,
                               "reason": reason, "index_date": r["index_date"],
                               "resolver_method": method, "tier": "B",
                               "built_date": TODAY})

        if not mrec:
            out.update({
                "confidence": "index_only",
                "text_layer_status": ("NO_DOCUMENT_LINKED_ON_INDEX"
                                      if not r["index_url"] else "NOT_RETRIEVED"),
                "fetched_date": TODAY,
                "source_url": INDEX_URL,
                "source_quote": (f"{tribe} | "
                                 f"{'Ordinance Date' if r['ordinance_type'] == 'ORIGINAL_ORDINANCE' else 'Amendment Date'}"
                                 f": {r['index_date']}"),
                "date_agreement": "NO_DOCUMENT",
            })
            rows.append(out)
            continue

        pdf = CEDAR / mrec["local_path"]
        out.update({"pdf_path": mrec["local_path"], "pdf_md5": mrec["md5"],
                    "pdf_bytes": mrec["bytes"],
                    "resolved_pdf_url": mrec["resolved_url"],
                    "md5_duplicate_of": mrec.get("md5_duplicate_of", ""),
                    "fetched_date": mrec["fetched_date"]})
        try:
            doc = fitz.open(pdf)
            pages = [p.get_text() for p in doc]
        except Exception as e:
            out.update({"confidence": "document_unreadable",
                        "text_layer_status": f"UNREADABLE:{type(e).__name__}",
                        "source_quote": f"{tribe} | {r['index_date']}",
                        "date_agreement": "NO_TEXT"})
            rows.append(out)
            continue
        t = "\n".join(pages)
        out["pdf_pages"] = len(pages)
        out["pdf_chars"] = len(t)

        # DOES THE DOCUMENT NAME THE TRIBE IT IS FILED UNDER?
        # Cheap, general, and the only thing that separates a mislinked file
        # from a correct one. Trap tokens are excluded because `indian`,
        # `united` or `river` appearing in an ordinance proves nothing.
        # Computed BEFORE the no-text-layer exit so a mislinked SCAN is still
        # labelled as mislinked rather than as a scan.
        distinctive = core(tribe) - CD.NAME_TRAPS
        nt = norm(t)
        names_tribe = (any(f" {tok} " in f" {nt} " for tok in distinctive)
                       if distinctive and len(t.strip()) >= 300 else None)
        out["document_names_tribe"] = ("1" if names_tribe else
                                       "0" if names_tribe is False else "")

        if cross_tribe_file and names_tribe is not True:
            # The file is another tribe's and says so. Writing its classes,
            # its gaming agency or its per-capita clause under this tribe
            # would be a fabricated fact with a real URL attached.
            out.update({
                "confidence": "document_served_belongs_to_another_tribe",
                "date_agreement": "NO_USABLE_DOCUMENT",
                "source_url": INDEX_URL,
                "source_quote": (f"{tribe} | {r['ordinance_type']} | "
                                 f"{r['index_date']} (NIGC gaming ordinances "
                                 f"index; the linked PDF is byte-identical to "
                                 f"another tribe's and does not name this "
                                 f"tribe)"),
            })
            rows.append(out)
            continue

        if len(t.strip()) < 300:
            # A near-empty extraction is a SCAN, not an empty document.
            out.update({
                "confidence": "document_no_text_layer",
                "text_layer_status": "IMAGE_ONLY_SCAN_NO_TEXT_LAYER",
                "date_agreement": "NO_TEXT",
                "source_url": INDEX_URL,
                "source_quote": (f"{tribe} | "
                                 f"{'Ordinance Date' if r['ordinance_type'] == 'ORIGINAL_ORDINANCE' else 'Amendment Date'}"
                                 f": {r['index_date']}"),
            })
            rows.append(out)
            continue

        out["text_layer_status"] = "TEXT_LAYER_PRESENT"
        out["confidence"] = "document_parsed"

        auth, neg, cq, cbasis = extract_classes(t)
        out["classes_authorized"] = "|".join(sorted(auth, key=len))
        out["classes_negated"] = "|".join(sorted(neg, key=len))
        out["class_ii_authorized"] = ("1" if "II" in auth
                                      else "0" if "II" in neg else "")
        out["class_iii_authorized"] = ("1" if "III" in auth
                                       else "0" if "III" in neg else "")
        out["classes_quote"] = cq
        out["classes_basis"] = cbasis

        ag, agq, agb = extract_agency(t, tribe)
        out["tribal_gaming_agency_named"] = ag
        out["tribal_gaming_agency_quote"] = agq
        out["tribal_gaming_agency_basis"] = agb

        rap, rapq, pc, pcq = extract_rap_percap(t)
        out["revenue_allocation_plan_referenced"] = rap
        out["revenue_allocation_plan_quote"] = rapq
        out["per_capita_referenced"] = pc
        out["per_capita_quote"] = pcq

        mics, micsq = extract_mics(t)
        out["minimum_internal_control_reference"] = mics
        out["minimum_internal_control_quote"] = micsq

        lic, licq = extract_licensing(t)
        out["licensing_provisions"] = lic
        out["licensing_quote"] = licq

        eff, effq = extract_effective(t)
        out["effective_date"] = eff
        out["effective_date_quote"] = effq

        chair, chq = extract_chair(pages[0])
        out["chair_or_designee"] = chair
        out["chair_quote"] = chq

        sup_date, sup_q, sup_basis = extract_supersedes(t)
        out["supersedes_quote"] = sup_q
        out["_stated_supersedes_date"] = sup_date
        out["supersedes_basis"] = sup_basis

        ldate, _ = extract_letter_date(pages[0])
        out["document_approval_date"] = ldate
        if not ldate:
            out["date_agreement"] = "LETTER_DATE_NOT_FOUND"
        elif ldate == r["index_date"]:
            out["date_agreement"] = "AGREE"
        else:
            d1 = datetime.fromisoformat(ldate)
            d2 = datetime.fromisoformat(r["index_date"])
            if abs((d1 - d2).days) <= 45:
                out["date_agreement"] = "AGREE_WITHIN_45_DAYS"
            elif (d1.month, d1.day) == (d2.month, d2.day) \
                    and abs(d1.year - d2.year) <= 3:
                # Same month and day, a year or two apart, on a scanned
                # letterhead: that is an OCR digit, not two instruments.
                # Calling it an index defect would be the stronger claim on
                # the weaker evidence.
                out["date_agreement"] = "LIKELY_OCR_YEAR_MISREAD"
            else:
                out["date_agreement"] = "DISAGREE_DOCUMENT_IS_ANOTHER_INSTRUMENT"

        out["source_quote"] = (cq or out["chair_quote"] or agq
                               or sq(t, 0, 380, pad=0))
        rows.append(out)

    # ---- historical chain: five rows for an ordinance amended four times ---
    bytribe = defaultdict(list)
    for r in rows:
        bytribe[r["index_tribe_name"]].append(r)
    for tribe, rs in bytribe.items():
        rs.sort(key=lambda x: (x["index_date"],
                               0 if x["ordinance_type"] == "ORIGINAL_ORDINANCE"
                               else 1, x["ordinance_id"]))
        bydate = {x["index_date"]: x["ordinance_id"] for x in rs}
        for i, x in enumerate(rs):
            # The original instrument is 0; amendments count 1..n in approval
            # order. Five rows for an ordinance amended four times.
            x["amendment_number"] = "0" if i == 0 else str(i)
            x["effective_range_start"] = x["index_date"]
            if i + 1 < len(rs):
                x["effective_range_end"] = rs[i + 1]["index_date"]
                x["in_force_status"] = "SUPERSEDED_BY_LATER_INSTRUMENT"
                x["superseded_by_ordinance_id"] = rs[i + 1]["ordinance_id"]
            else:
                x["effective_range_end"] = ""
                x["in_force_status"] = "LATEST_INSTRUMENT_ON_NIGC_INDEX"
            stated = x.pop("_stated_supersedes_date", "")
            if stated and stated in bydate and bydate[stated] != x["ordinance_id"]:
                x["supersedes_ordinance_id"] = bydate[stated]
                x["supersedes_basis"] = "stated_in_document_date_matched"
            elif i > 0:
                x["supersedes_ordinance_id"] = rs[i - 1]["ordinance_id"]
                x["supersedes_basis"] = "chronological_prior_instrument"
            else:
                x["supersedes_ordinance_id"] = ""
                x["supersedes_basis"] = ""
    for r in rows:
        r.pop("_stated_supersedes_date", None)

    # ---- integrity assertions --------------------------------------------
    assert all(r["source_url"] and r["source_quote"] for r in rows), \
        "a row without a source_url or a verbatim source_quote"
    assert not any(r["class_ii_authorized"] == "1" and
                   r["authorisation_measurement_type"] != "LEGAL_AUTHORISATION_NOT_A_COUNT"
                   for r in rows)

    write_csv(CLEAN / "gaming_ordinances.csv", rows, FIELDS)
    if unresolved:
        # One row per unresolved NIGC tribe NAME, not per instrument - a
        # ruling settles the tribe, and 30 rows asking the same question is
        # a queue nobody works through.
        seen, uq = set(), []
        for u in unresolved:
            if u["index_tribe"] in seen:
                continue
            seen.add(u["index_tribe"])
            n_inst = sum(1 for x in rows
                         if x["index_tribe_name"] == u["index_tribe"])
            uq.append({
                "review_id": f"ORDINANCE-TRIBE:{u['index_tribe']}",
                "index_tribe": u["index_tribe"],
                "n_ordinance_instruments": n_inst,
                "first_index_date": min(x["index_date"] for x in rows
                                        if x["index_tribe_name"] == u["index_tribe"]),
                "resolver_method": u["resolver_method"],
                "reason": u["reason"],
                "question": ("Which Cedar spine entity is this NIGC-listed "
                             "tribe, or is it absent from the spine?"),
                "source_url": INDEX_URL,
                "source_quote": f"{u['index_tribe']} (NIGC gaming ordinances index)",
                "tier": "B", "built_date": TODAY, "YOUR_RULING": "",
            })
        write_csv(REVIEW / f"ordinance_unresolved_{TODAY}.csv", uq,
                  list(uq[0].keys()))

    # ---- summary ----------------------------------------------------------
    L = []
    def p(s=""):
        print(s)
        L.append(s)

    p(f"instrument rows            {len(rows):,}")
    p(f"  originals                {sum(1 for r in rows if r['ordinance_type'] == 'ORIGINAL_ORDINANCE'):,}")
    p(f"  amendments               {sum(1 for r in rows if r['ordinance_type'] == 'AMENDMENT'):,}")
    p(f"distinct NIGC tribe names  {len(bytribe):,}")
    p(f"keyed to a spine entity    {len({r['tribe_id'] for r in rows if r['tribe_id']}):,} tribes / "
      f"{sum(1 for r in rows if r['tribe_id']):,} rows")
    p(f"date range                 {min(r['index_date'] for r in rows)} .. "
      f"{max(r['index_date'] for r in rows)}")
    for k, c in Counter(r["confidence"] for r in rows).most_common():
        p(f"  confidence {k:28} {c:,}")
    for k, c in Counter(r["date_agreement"] for r in rows).most_common():
        p(f"  date_agreement {k:44} {c:,}")
    p(f"class II authorised rows   {sum(1 for r in rows if r['class_ii_authorized'] == '1'):,}")
    p(f"class III authorised rows  {sum(1 for r in rows if r['class_iii_authorized'] == '1'):,}")
    p(f"named a tribal gaming body {sum(1 for r in rows if r['tribal_gaming_agency_named']):,} rows / "
      f"{len({r['tribal_gaming_agency_named'] for r in rows if r['tribal_gaming_agency_named']}):,} distinct names")
    for k, c in Counter(r["per_capita_referenced"] for r in rows
                        if r["per_capita_referenced"]).most_common():
        p(f"  per_capita {k:40} {c:,}")
    p(f"RAP referenced rows        {sum(1 for r in rows if r['revenue_allocation_plan_referenced'] == 'REFERENCED'):,}")
    p(f"MICS referenced rows       {sum(1 for r in rows if r['minimum_internal_control_reference']):,}")
    p(f"entity tier A / B          "
      f"{sum(1 for r in rows if r['entity_tier'] == 'A'):,} / "
      f"{sum(1 for r in rows if r['entity_tier'] == 'B'):,}")
    p(f"unresolved to review       {len(unresolved):,}")
    (INTERIM / "118_run_summary.txt").write_text("\n".join(L), encoding="utf-8")
    return rows


# ===========================================================================
# RECONCILE - three populations, and the diff is where the value lands
# ===========================================================================

def cmd_reconcile(argv):
    rows = read_csv(CLEAN / "gaming_ordinances.csv")
    if not rows:
        raise SystemExit("run parse first")
    compacts = read_csv(CLEAN / "compacts.csv")
    roster = read_csv(REVIEW / "nigc_roster_diff_2026-08-06.csv")
    spine = read_csv(SPINE / "cedar_entity_spine.csv")
    by_id = {r["tribe_id"]: r for r in spine}

    unresolved_names = sorted({r["index_tribe_name"] for r in rows
                               if not r["tribe_id"]})
    ord_by_tribe = defaultdict(list)
    for r in rows:
        ord_by_tribe[r["tribe_id"] or f"NAME:{r['index_tribe_name']}"].append(r)

    cmp_by_tribe = defaultdict(list)
    for c in compacts:
        if c.get("tribe_id"):
            cmp_by_tribe[c["tribe_id"]].append(c)

    map_by_tribe = defaultdict(list)
    map_unkeyed = 0
    for m in roster:
        if m["outcome"] not in ("MATCHED", "IN_NIGC_NOT_IN_CEDAR"):
            continue
        if m.get("tribe_id"):
            map_by_tribe[m["tribe_id"]].append(m)
        else:
            map_unkeyed += 1

    # AN UNKEYED ORDINANCE TRIBE WOULD FAKE A CLASS II FINDING.
    # 15 of the 321 NIGC names do not resolve to a spine entity. Joined on
    # tribe_id they all come out as "ordinance, no compact" - and several of
    # them (Viejas, Santa Ysabel, Mille Lacs, Cherokee Nation, St. Regis)
    # certainly DO hold class III compacts. Counting them would inflate the
    # headline by 38% with tribes that contradict it.
    #
    # So they are excluded from the headline and cross-checked by NAME as a
    # lead for review - never as a join.
    # THESE COLUMNS ARE LEADS FOR A HUMAN, AND A WRONG LEAD BIASES THE RULING.
    # A loose version of this test proposed `Cherokee Nation, Oklahoma` ->
    # *United Keetoowah Band*, `Shawnee Tribe of Oklahoma` -> *Absentee*-
    # Shawnee and `Fond du Lac` -> *Mille Lacs*. So the test is strict - every
    # distinctive token of the candidate must appear in the other name - and
    # where more than one candidate qualifies ALL are printed rather than one
    # being chosen.
    # A STATE NAME IS NOT A DISTINCTIVE TOKEN EITHER. Without this,
    # `Apache Tribe of Oklahoma` reduces to {oklahoma} and matched
    # `Cherokee Nation, Oklahoma` - two different nations sharing a state.
    # State tokens join the trap set for this test only.
    STATE_TOKENS = {t for s_ in STATES for t in s_.split()}

    def distinctive(nm):
        return core(nm) - CD.NAME_TRAPS - STATE_TOKENS

    cmp_names = {}
    for c in compacts:
        nm = (c.get("tribe_canonical_name") or c.get("tribe") or "").strip()
        if nm:
            cmp_names[nm] = distinctive(nm)

    def name_level_compact(nm):
        cn = distinctive(nm)
        if not cn:
            return ""
        return "|".join(sorted(v for v, k in cmp_names.items() if k and k <= cn))

    keys = set(ord_by_tribe) | set(cmp_by_tribe) | set(map_by_tribe)
    out = []
    for k in sorted(keys):
        o = ord_by_tribe.get(k, [])
        c = cmp_by_tribe.get(k, [])
        g = map_by_tribe.get(k, [])
        keyed = not k.startswith("NAME:")
        name = (by_id.get(k, {}).get("canonical_name") if keyed
                else k.split(":", 1)[1])
        if not name:
            name = (o[0]["tribe_name"] if o else
                    c[0].get("tribe", "") if c else
                    g[0].get("nigc_location_name", ""))
        nlc = "" if (keyed or not o) else name_level_compact(name)
        # The mirror check: a tribe that looks like "compact, no ordinance"
        # may simply be one whose NIGC index NAME did not resolve. 12 of the
        # first 18 were exactly that, so the raw count is not the finding.
        nlo = ""
        if keyed and c and not o:
            ck = distinctive(by_id.get(k, {}).get("canonical_name") or name)
            if ck:
                nlo = "|".join(sorted(un for un in unresolved_names
                                      if ck <= distinctive(un)))
        flags = (("ORD" if o else "---"), ("CMP" if c else "---"),
                 ("MAP" if g else "---"))
        pop = "+".join(flags)
        finding = ""
        if o and not c:
            finding = ("NOT_COMPARABLE_ORDINANCE_TRIBE_UNRESOLVED" if not keyed
                       else "ORDINANCE_NO_COMPACT_CLASS_II_UNIVERSE")
        elif c and not o:
            finding = ("COMPACT_ORDINANCE_LIKELY_UNDER_UNRESOLVED_INDEX_NAME"
                       if nlo else "COMPACT_NO_ORDINANCE_ON_NIGC_INDEX")
        if o and not g:
            finding = (finding + ";" if finding else "") + \
                "ORDINANCE_NO_NIGC_MAPPED_LOCATION"
        if g and not o:
            finding = (finding + ";" if finding else "") + \
                "NIGC_MAPPED_LOCATION_NO_ORDINANCE_ON_INDEX"
        latest = max(o, key=lambda x: x["index_date"]) if o else None
        out.append({
            "tribe_id": k if keyed else "",
            "tribe_name": name,
            "key_basis": "spine_entity" if keyed else "name_only_unresolved",
            "has_ordinance": int(bool(o)),
            "n_ordinance_instruments": len(o),
            "first_ordinance_date": min((x["index_date"] for x in o), default=""),
            "latest_instrument_date": max((x["index_date"] for x in o), default=""),
            "class_ii_authorized_any": int(any(x["class_ii_authorized"] == "1"
                                               for x in o)),
            "class_iii_authorized_any": int(any(x["class_iii_authorized"] == "1"
                                                for x in o)),
            "latest_instrument_id": latest["ordinance_id"] if latest else "",
            "tribal_gaming_agency_named": next(
                (x["tribal_gaming_agency_named"] for x in
                 sorted(o, key=lambda y: y["index_date"], reverse=True)
                 if x["tribal_gaming_agency_named"]), ""),
            "has_compact": int(bool(c)),
            "n_compacts": len(c),
            "compact_states": "|".join(sorted({x.get("state", "") for x in c
                                               if x.get("state")})),
            "on_nigc_gaming_location_map": int(bool(g)),
            "n_nigc_mapped_locations": len(g),
            "population_class": pop,
            "finding": finding,
            "name_level_compact_candidate": nlc,
            "name_level_ordinance_candidate": nlo,
            "source_url": INDEX_URL,
            "built_date": TODAY,
        })
    write_csv(REVIEW / f"ordinance_compact_diff_{TODAY}.csv", out,
              list(out[0].keys()))

    L = []
    def p(s=""):
        print(s)
        L.append(s)
    p("\n=== THREE-POPULATION RECONCILIATION ===")
    p(f"tribes with an ordinance (keyed)   "
      f"{sum(1 for r in out if r['has_ordinance'] and r['tribe_id']):,}")
    p(f"tribes with an ordinance (name-only, unresolved) "
      f"{sum(1 for r in out if r['has_ordinance'] and not r['tribe_id']):,}")
    p(f"tribes with a compact              {sum(1 for r in out if r['has_compact']):,}")
    p(f"tribes on the NIGC location map    "
      f"{sum(1 for r in out if r['on_nigc_gaming_location_map']):,}"
      f"   ({map_unkeyed} mapped locations carry no keyed tribe)")
    for k, c in Counter(r["population_class"] for r in out).most_common():
        p(f"   {k:20} {c:,}")
    cls2 = [r for r in out if r["has_ordinance"] and not r["has_compact"]
            and r["tribe_id"]]
    notcomp = [r for r in out if r["has_ordinance"] and not r["tribe_id"]]
    p(f"\nORDINANCE BUT NO COMPACT (the class II universe): {len(cls2):,} tribes")
    for r in sorted(cls2, key=lambda x: x["tribe_name"]):
        p(f"   {r['tribe_name']}  ({r['first_ordinance_date']}, "
          f"{r['n_ordinance_instruments']} instrument(s)"
          + (f", class II authorised in the text"
             if r["class_ii_authorized_any"] else "") + ")")
    p(f"\nNOT COMPARABLE - ordinance tribe unresolved to the spine: "
      f"{len(notcomp):,}. These are EXCLUDED from the count above; joining "
      f"them on a missing key would score every one of them as 'no compact'.")
    for r in sorted(notcomp, key=lambda x: x["tribe_name"]):
        p(f"   {r['tribe_name']}"
          + (f"   [name-level compact candidate: {r['name_level_compact_candidate']}]"
             if r["name_level_compact_candidate"] else "   [no name-level compact found]"))
    noloc = [r for r in out if r["has_ordinance"]
             and not r["on_nigc_gaming_location_map"]]
    p(f"\nORDINANCE BUT NO NIGC MAPPED LOCATION (authorised, not observed "
      f"operating): {len(noloc):,} tribes")
    nocmp = [r for r in out if r["has_compact"] and not r["has_ordinance"]]
    real = [r for r in nocmp if not r["name_level_ordinance_candidate"]]
    p("")
    p(f"COMPACT BUT NO ORDINANCE ON THE NIGC INDEX: {len(nocmp):,} tribes, of "
      f"which {len(nocmp) - len(real):,} are the mirror of the unresolved "
      f"index names above and {len(real):,} are unexplained.")
    p("  IGRA requires an approved ordinance for class III as well as class "
      "II, so an unexplained row here is a gap in NIGC's published index, not "
      "a tribe operating without one.")
    for r in sorted(nocmp, key=lambda x: x["tribe_name"]):
        tag = (f"  <- NIGC index name: {r['name_level_ordinance_candidate']}"
               if r["name_level_ordinance_candidate"] else "  UNEXPLAINED")
        p(f"   {r['tribe_name']} ({r['compact_states']}, "
          f"{r['n_compacts']} compact(s)){tag}")
    with open(INTERIM / "118_run_summary.txt", "a", encoding="utf-8") as fh:
        fh.write("\n" + "\n".join(L))
    return out


# ===========================================================================
# CODEBOOK FRAGMENT - fragment only.  codebook_master.csv is NOT touched.
# ===========================================================================

CODEBOOK = [
    ("ordinance_id", "Stable Cedar id, NIGC-ORD-<approval date>-<sequence within that date on the NIGC index's own order>. Never derived from the WPDM id, which is a CMS artefact."),
    ("tribe_id", "Cedar spine entity id. Blank where the resolver refused; those rows are in review/ordinance_unresolved_<date>.csv at tier B."),
    ("tribe_name", "Spine canonical name where keyed, otherwise NIGC's own string."),
    ("ordinance_type", "ORIGINAL_ORDINANCE or AMENDMENT, as NIGC's index columns state."),
    ("amendment_number", "0 for the original instrument, 1..n for amendments in approval-date order within the tribe."),
    ("approval_date", "The date NIGC's index prints for this instrument. NIGC's own published statement."),
    ("effective_date", "An effective date stated INSIDE the document. Blank where the document does not state one - it is not inferred from the approval date."),
    ("chair_or_designee", "Signatory of the approval letter as printed, 'Name, Title'. A title alone means OCR lost the signature."),
    ("classes_authorized", "Pipe-joined IGRA classes the ordinance AUTHORISES (II, III). An authorisation, never an operating class. A class merely DEFINED in a definitions section is not captured."),
    ("class_ii_authorized", "1 authorised, 0 explicitly not authorised, blank not determinable from the document."),
    ("class_iii_authorized", "As class_ii_authorized."),
    ("licensing_provisions", "Pipe-joined licensing features quoted in the instrument: KEY_EMPLOYEE_LICENSE, PRIMARY_MANAGEMENT_OFFICIAL_LICENSE, FACILITY_LICENSE, BACKGROUND_INVESTIGATION, VENDOR_LICENSE, SUSPENSION_REVOCATION, GAMING_EMPLOYEE_LICENSE, ELIGIBILITY_DETERMINATION."),
    ("tribal_gaming_agency_named", "The TRIBAL regulatory body the ordinance names. The National Indian Gaming Commission and any state body are rejected by name - NIGC is the federal regulator, not the tribe's own agency."),
    ("revenue_allocation_plan_referenced", "REFERENCED / NOT_REFERENCED. A reference to a plan under 25 U.S.C. 2710(b)(3) or 25 C.F.R. 522.4(b)(2)(ii)/522.6(b)."),
    ("per_capita_referenced", "PER_CAPITA_CONDITIONAL_RECITATION (the statutory 'if the Tribe elects...' clause - it proves the ordinance contemplates per capita, NOT that any plan or distribution exists), PER_CAPITA_PLAN_ASSERTED, PER_CAPITA_PROHIBITED, PER_CAPITA_REFERENCED_UNQUALIFIED, NOT_REFERENCED."),
    ("minimum_internal_control_reference", "Pipe-joined verbatim internal-control references found (MICS, TICS, 25 C.F.R. Part 542/543)."),
    ("supersedes_ordinance_id", "The instrument this one follows. See supersedes_basis: an AMENDMENT amends the instrument in force, it does not necessarily replace it in whole."),
    ("source_url", "The NIGC index link for this instrument, or the index page itself where no document was retrieved."),
    ("source_quote", "Verbatim text supporting the row. Present on every row."),
    ("pdf_path", "Repo-relative path to the retrieved PDF."),
    ("fetched_date", "Date the PDF was retrieved."),
    ("tier", "B on every row. These are algorithmic extractions with receipts, not human rulings; spec 10.1 lands them at B pending review."),
    ("confidence", "document_parsed / document_no_text_layer / document_unreadable / index_only - the evidentiary basis, not a probability."),
    ("built_date", "Build date."),
    ("superseded_by_ordinance_id", "The next instrument for this tribe on the NIGC index, if any."),
    ("supersedes_basis", "stated_in_document_date_matched where the letter names the superseded instrument and its date; chronological_prior_instrument otherwise."),
    ("effective_range_start", "Approval date of this instrument."),
    ("effective_range_end", "Approval date of the tribe's next instrument; blank while this is the latest. The range is when this instrument was the operative version on NIGC's index - amendments are stored historically and nothing is overwritten."),
    ("in_force_status", "SUPERSEDED_BY_LATER_INSTRUMENT / LATEST_INSTRUMENT_ON_NIGC_INDEX."),
    ("index_anomaly", "Anomalies in NIGC's own index, recorded rather than smoothed: INDEX_DATE_PRECEDES_IGRA_ENACTMENT (a date before 17 Oct 1988 cannot be an NIGC approval date), INDEX_LINK_PRINTED_UNDER_MORE_THAN_ONE_DATE, INDEX_LINK_IS_NOT_A_URL, NO_DOCUMENT_LINKED_ON_INDEX, SAME_PDF_SERVED_FOR_A_DIFFERENT_TRIBE, SAME_PDF_AS_ANOTHER_INSTRUMENT_SAME_TRIBE."),
    ("document_names_tribe", "1 where the retrieved PDF's text contains a distinctive token of the tribe it is filed under, 0 where it does not, blank where no distinctive token exists or there is no text. Trap tokens (indian, united, river, ...) are excluded because they prove nothing."),
    ("index_tribe_name", "The tribe string exactly as NIGC's index prints it."),
    ("index_date", "The date NIGC's index prints. Same as approval_date; kept separate so a later re-key cannot blur the two."),
    ("document_approval_date", "The date read from the approval letter itself. Blank where OCR could not recover it."),
    ("date_agreement", "AGREE / AGREE_WITHIN_45_DAYS / DISAGREE_DOCUMENT_IS_ANOTHER_INSTRUMENT / LETTER_DATE_NOT_FOUND / NO_TEXT / NO_DOCUMENT. NIGC's index prints one wpdmdl link under two different dates, so the index date is not always a reliable label for the document behind the link."),
    ("classes_basis", "authorisation_section_heading (highest precision) / authorising_verb_window / no_authorising_language_found."),
    ("classes_negated", "Classes the instrument explicitly does NOT authorise."),
    ("authorisation_measurement_type", "LEGAL_AUTHORISATION_NOT_A_COUNT on every row. An ordinance authorisation can never become a device count, a facility, or an operating class."),
    ("tribal_gaming_agency_basis", "tribe_specific_name where the body's name carries the tribe's own distinctive tokens; generic_name_in_ordinance otherwise."),
    ("text_layer_status", "TEXT_LAYER_PRESENT / IMAGE_ONLY_SCAN_NO_TEXT_LAYER / UNREADABLE:<error> / NOT_RETRIEVED. A near-empty extraction is a scan, not an empty document."),
    ("pdf_pages", "Pages in the retrieved PDF."),
    ("pdf_chars", "Characters of extractable text."),
    ("pdf_md5", "md5 of the retrieved file. Distinct md5s are the guard against the NIGC download trap."),
    ("pdf_bytes", "Byte length of the retrieved file."),
    ("resolved_pdf_url", "The wp-content object the WPDM link resolved to."),
    ("md5_duplicate_of", "Another ordinance_id whose retrieved file is byte-identical. A collision is recorded, never silently accepted."),
    ("entity_match_method", "How the one resolver keyed the tribe: exact / core / alias / containment, or the refusal reason."),
    ("entity_tier", "A only where an exact/core/alias name match agrees with a state derived from the tribe's own name (two independent legs). B otherwise."),
    ("entity_state", "State parsed out of the tribe's own name, where it states one."),
    ("classes_quote", "Verbatim text behind classes_authorized."),
    ("tribal_gaming_agency_quote", "Verbatim text behind tribal_gaming_agency_named."),
    ("revenue_allocation_plan_quote", "Verbatim text behind revenue_allocation_plan_referenced."),
    ("per_capita_quote", "Verbatim text behind per_capita_referenced."),
    ("licensing_quote", "Verbatim text behind licensing_provisions."),
    ("minimum_internal_control_quote", "Verbatim text behind minimum_internal_control_reference."),
    ("chair_quote", "Verbatim text behind chair_or_designee."),
    ("effective_date_quote", "Verbatim text behind effective_date."),
    ("supersedes_quote", "Verbatim supersession language where the document states it."),
]


def cmd_codebook(argv):
    """FRAGMENT ONLY.  codebook_master.csv is a derived concatenation with a
    dozen writers and is never touched here (cedar_codebook.py docstring)."""
    master = read_csv(CLEAN / "codebook_master.csv")
    fields = (list(master[0].keys()) if master else
              ["dataset", "variable", "type", "units", "pct_filled", "n_rows",
               "published", "access_tier", "description", "generated"])
    data = read_csv(CLEAN / "gaming_ordinances.csv")
    n = len(data)
    rows = []
    for var, definition in CODEBOOK:
        filled = sum(1 for r in data if (r.get(var) or "").strip())
        num = all(re.fullmatch(r"-?\d+", (r.get(var) or "0").strip() or "0")
                  for r in data) if data else False
        r = {f: "" for f in fields}
        r.update({
            "dataset": "07f_gaming_ordinances", "variable": var,
            "type": "integer" if num and var.endswith(
                ("_authorized", "_number", "_pages", "_chars", "_bytes"))
            else "date" if var.endswith("_date") else "text",
            "units": "code" if var.endswith("_id") else "",
            "pct_filled": f"{100.0 * filled / n:.1f}" if n else "",
            "n_rows": n,
            # Tier B on every row: algorithmic extraction, not a human ruling.
            "published": 0,
            "access_tier": "internal_pending_review",
            "description": definition,
            "generated": TODAY,
        })
        rows.append(r)
    n = CB.write_fragment("07f_gaming_ordinances", rows, fields)
    print(f"  wrote codebook fragment data/clean/codebook/"
          f"07f_gaming_ordinances.csv ({n} rows) - codebook_master.csv "
          f"NOT touched")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "fetch":
        cmd_fetch(sys.argv[2:])
    elif cmd == "parse":
        cmd_parse(sys.argv[2:])
        cmd_codebook(sys.argv[2:])
    elif cmd == "reconcile":
        cmd_reconcile(sys.argv[2:])
    elif cmd == "codebook":
        cmd_codebook(sys.argv[2:])
    elif cmd == "all":
        cmd_fetch(sys.argv[2:])
        cmd_parse(sys.argv[2:])
        cmd_codebook(sys.argv[2:])
        cmd_reconcile(sys.argv[2:])
    else:
        raise SystemExit(f"unknown command {cmd!r}")
