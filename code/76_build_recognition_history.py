#!/usr/bin/env python3
"""
Cedar Press - 76: the federal recognition roster, 1995-2026, and its events.

ELIJAH, 2026-08-06
------------------
    "if we have federal register data we can make a dataset on federal
     recognition changes over time and tribe name changes? that seems to be
     low hanging fruit that would maybe help with identification historically
     and seems like something that we can just add thats more authoritative
     than wikipedia since we have voting and stuff we can probably also tie
     recognition to those tribes"

Right on every count. The BIA has been required to publish the list annually
since the Federally Recognized Indian Tribe List Act of 1994 (Pub. L. 103-454),
and the Federal Register API serves the full text of every one of those
notices. Diffing consecutive notices turns a set of static lists into an event
stream, and the old names on it are the thing that makes 1990s and 2000s
contracting and funding rows resolve.

WHAT THIS SCRIPT DOES
---------------------
  A  discovers every annual "Indian Entities Recognized ..." notice on
     federalregister.gov and caches its raw text
  B  parses each into a roster of listed entities
  C  builds entity identity ACROSS notices (names change constantly)
  D  diffs consecutive notices into ADDED / REMOVED / RENAMED / RESTORED
  E  attaches a mechanism and a verbatim quote to every event
  F  proposes historical names as spine aliases
  G  writes docs/RECOGNITION_HISTORY_LOG.md

PRIME DIRECTIVE - ZERO FABRICATION
----------------------------------
Every event carries its FR citation and a verbatim quote from a Federal
Register document, plus `quote_basis` saying which document the quote is from.
Where the reason for a change is not in the record, `mechanism` is blank and
`mechanism_basis` says `not_stated_in_record`. A REMOVED row is NEVER written
as a termination without text that says so - a removal is just as often a merge
into another listing, and calling it a termination would be an invented fact
about a nation's legal existence.

THE PARSING RULES, AND WHY EACH ONE EXISTS
------------------------------------------
1. A wrapped line ends with a trailing space; a complete entry does not.
   (Script 69's rule. It is right about 99.7% of lines.)
2. A line that leaves a bracket OPEN is also a wrap, even without the trailing
   space - GPO breaks at a hyphen ("Alabama-" / "Coushatta Tribes of Texas]")
   and once mid-phrase ("... St. Regis Band of Mohawk Indians" / "of New
   York)"). Rule 1 alone splits those into phantom tribes.
3. Rule 2 BACKS OUT if four more lines do not close the bracket. The 2014
   notice contains an unclosed paren in the source - "Northwestern Band of
   Shoshoni Nation of Utah (Washakie" - and an unbounded rule 2 swallows the
   remaining 90 tribes into a single 6,016-character row.
4. `[[Page NNNN]]` markers are removed before de-wrapping, TOGETHER WITH THE
   BLANK LINES AROUND THEM. Two forms occur and both break an entry:
     - inline: "Crow Tribe of Montana [[Page 9252]] " appends a trailing space
       and makes a complete entry look wrapped. Verified across all notices: no
       inline marker ever sits on a line whose content exceeds 60 characters,
       i.e. never on a genuinely wrapped line. The script asserts this.
     - standalone: a blank line, the marker, a blank line, dropped INTO the
       middle of an entry. The 2003 notice splits "Sisseton-Wahpeton Oyate ...
       (formerly the Sisseton-Wahpeton" / "Sioux Tribe of the Lake Traverse
       Reservation)" that way, and 2024 splits Capitan Grande's constituents.
       Removing only the marker leaves the blanks, which terminate the wrap and
       emit "Sioux Tribe of the Lake Traverse Reservation)" as a phantom tribe.

PARENTHESES CARRY FOUR DIFFERENT MEANINGS - NEVER FLATTEN THEM
--------------------------------------------------------------
  (previously listed as X) / [previously listed as X] / (formerly X)
        a RENAME. X is an alias of the SAME entity.
  (See Y)
        a CROSS-REFERENCE. This name is a listed tribe, but Y is the entity
        that acts for it. "Arctic Village (See Native Village of Venetie
        Tribal Government)". Collapsing this into a rename MERGES TWO TRIBES.
  (See Supplementary Information ...)
        NOT a cross-reference at all - it is a pointer to the preamble. The
        2026 Lumbee entry uses it. A naive `\\(See` rule turns the single most
        important recognition event in the dataset into a pointer to nothing.
  (A; B) or a trailing colon with indented lines
        CONSTITUENT parts under one parent - Capitan Grande listing Barona and
        Viejas, the Minnesota Chippewa Tribe listing six reservations. These
        are sub-entities, not separate listings, and the BIA does not count
        them in its own total.

Reads   federalregister.gov/api/v1 (GET, no key)
        data/raw/external/fr_recognized/*_raw.txt          (cached)
        data/clean/federal_actions.csv                     (156k FR documents)
        data/clean/native_bills.csv                        (read-only)
        data/spine/cedar_entity_spine.csv                  (read-only)
Writes  data/clean/federal_recognition_roster.csv
        data/clean/federal_recognition_events.csv
        data/raw/external/fr_recognized/_notice_manifest.csv
        review/recognition_alias_proposals.csv
        docs/RECOGNITION_HISTORY_LOG.md
        logs/76_recognition_history_<date>.log

DOES NOT TOUCH the spine, data/clean/cedar_*, review/cedar_*, or any file owned
by the four agents concurrently adding TCU-/CDFI-/BIE-/UIO- entities. Alias
additions are written as a PROPOSAL for Elijah to merge.
"""

import csv
import html
import importlib.util
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
SPINE_P = CEDAR / "data" / "spine" / "cedar_entity_spine.csv"
RAW = CEDAR / "data" / "raw" / "external" / "fr_recognized"
REVIEW = CEDAR / "review"
DOCS = CEDAR / "docs"
LOGS = CEDAR / "logs"
TODAY = date.today().isoformat()

API = "https://www.federalregister.gov/api/v1/documents.json"
HOST = "www.federalregister.gov"
UA = ("Cedar Press dataset build (research; elijahsamsonmoreno@gmail.com)")
SLEEP = 0.8

# The title the BIA has used for the annual list since 1995. Wording drifts
# ("Recognized and" -> "Recognized by and", "From the United States Bureau"
# -> "From the Bureau"), so the pattern matches only the stable head.
TITLE_RE = re.compile(r"Indian (Entities|Tribal Entities) Recogni", re.I)

_logfh = None


def log(msg=""):
    print(msg, flush=True)
    if _logfh:
        _logfh.write(msg + "\n")
        _logfh.flush()


# ----------------------------------------------------------------- shared ---

def load_m33():
    """ONE resolver (standing rule 8). Never re-implement name matching."""
    spec = importlib.util.spec_from_file_location(
        "m33", CEDAR / "code" / "33_apply_party_rulings.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def read_csv(p):
    p = Path(p)
    if not p.exists():
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


def nk(s):
    """Local normaliser for name KEYS only. Entity resolution uses m33.norm.

    `St.` and `Saint` alternate freely across notices - "Saint Paul" (1995),
    "St .Paul" (1997, with the source's own typo), "Saint Paul Island" (2022) -
    so the abbreviation is expanded here. Without it the Pribilof entries churn
    in and out of the roster on spelling alone.
    """
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("\u02bb", "").replace("\u02bc", "").replace("\u2018", "")
    s = s.replace("\u0142", "l")
    s = re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()
    return " ".join("saint" if w == "st" else w for w in s.split())


# ------------------------------------------------------------ A. discovery --

def http_json(params):
    u = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(u, headers={"User-Agent": UA,
                                             "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.load(r)


def claim_host():
    """Pull discipline rule 2: claim the host before any remote fetch."""
    LOGS.mkdir(parents=True, exist_ok=True)
    p = LOGS / f"_HOSTLOCK_{HOST}.json"
    p.write_text(json.dumps({
        "host": HOST, "pid": os.getpid(),
        "script": "code/76_build_recognition_history.py",
        "started": TODAY, "queue": [],
        "note": "GET-only, ~35 requests total, 0.8s apart"}, indent=2),
        encoding="utf-8")
    return p


def discover(offline=False):
    """Every annual recognition notice, with its raw-text URL.

    The search term is full text, so it returns 129 documents that merely
    MENTION the list. Selection is on the TITLE, which is what makes a document
    the annual list rather than a document citing it. Both the accepted and the
    rejected are written to the manifest so the choice is auditable.
    """
    RAW.mkdir(parents=True, exist_ok=True)
    man = RAW / "_notice_manifest.csv"
    if offline and man.exists():
        log("  [offline] reusing the cached notice manifest")
        return [r for r in read_csv(man) if r["selected"] == "1"]

    lock = claim_host()
    log(f"  claimed {lock.relative_to(CEDAR)}")
    fields = ["document_number", "publication_date", "title", "citation",
              "raw_text_url", "html_url", "abstract", "type"]
    params = [("per_page", "1000"), ("order", "oldest"),
              ("conditions[term]", '"Indian Entities Recognized"')]
    params += [("fields[]", f) for f in fields]
    d = http_json(params)
    log(f"  API returned {d['count']} documents mentioning the phrase")

    rows = []
    for r in d["results"]:
        sel = bool(TITLE_RE.search(r.get("title") or ""))
        rows.append({k: r.get(k) or "" for k in fields}
                    | {"selected": "1" if sel else "0",
                       "api_endpoint": API, "fetched_date": TODAY})
    write_csv(man, rows, list(rows[0].keys()))
    sel = [r for r in rows if r["selected"] == "1"]
    log(f"  {len(sel)} have the annual-list TITLE and are selected")
    return sel


def fetch_raw(notices):
    got, missing = [], []
    for r in notices:
        p = RAW / f"{r['document_number']}_raw.txt"
        if p.exists() and p.stat().st_size > 500:
            got.append(r)
            continue
        if not r.get("raw_text_url"):
            missing.append((r["document_number"], "no raw_text_url"))
            continue
        try:
            req = urllib.request.Request(r["raw_text_url"],
                                         headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=180) as resp:
                p.write_text(resp.read().decode("utf-8", errors="replace"),
                             encoding="utf-8")
            got.append(r)
            log(f"    fetched {r['document_number']} ({p.stat().st_size:,} b)")
            time.sleep(SLEEP)
        except Exception as exc:                       # noqa: BLE001
            missing.append((r["document_number"], str(exc)[:80]))
    return got, missing


# ---------------------------------------------------------------- B. parse --

PAGE_RE = re.compile(r"\s*\[\[Page \d+\]\]\s*$")
RUNHEAD_RE = re.compile(r"^\s*Federal Register\s*/", re.I)
SEC48_RE = re.compile(r"Indian Tribal Entities Within\s+[Tt]he Contiguous 48 States", re.I)
SECAK_RE = re.compile(r"Native Entities Within the State of Alaska", re.I)
END_RE = re.compile(r"^\s*(Dated:|\[FR Doc|BILLING CODE|_{5,}|\(Authority)", re.I)
NOISE_RE = re.compile(
    r"^(AGENCY|ACTION|SUMMARY|DATES|ADDRESSES|FOR FURTHER|SUPPLEMENTARY|"
    r"Dated:|BILLING|\[FR Doc|DEPARTMENT|Bureau of Indian Affairs$|"
    r"Assistant Secretary|Deputy|Principal Deputy|Acting Assistant)", re.I)
CLARIF_RE = re.compile(r"^Clarification\s*$", re.I)
CNTHDR_RE = re.compile(r"^\[\s*(\d+)\s+Federally Recognized", re.I)
PAGE_ONLY_RE = re.compile(r"^\s*\[\[Page \d+\]\]\s*$")
# The 1995 Alaska list runs straight into the signature block, and "Ada E.
# Deer," parses as a tribe unless the signature is recognised for what it is.
SIGNATURE_RE = re.compile(r"^[A-Z][A-Za-z.'\-]+(?: [A-Z][A-Za-z.'\-]*\.?){1,3},$")
STATED_RE = re.compile(r"(?:list of|total of)\s+(\d{3})\s+(?:federally recognized\s+)?"
                       r"(?:Tribal entities|tribal entities|Indian Tribes)", re.I)

# TWO PATTERNS, TRIED IN ORDER, AND THE ORDER IS LOad-BEARING.
#
# STRICT wants the parenthetical closed at the end of the entry, which is the
# normal case and the only one that can contain nested brackets - "Ak-Chin
# Indian Community [previously listed as Ak Chin Indian Community of the
# Maricopa (Ak Chin) Indian Reservation, Arizona]".
#
# LOOSE handles the parenthetical the source never closed - the 2012 notice
# prints "Snoqualmie Indian Tribe (previously listed as the Snoqualmie Tribe,
# Washington" with no ")" - and refuses to cross a closing bracket, which is
# what stops it from eating a SECOND TRIBE glued onto the same line. The 2018
# notice runs "... Rancheria of California) Tejon Indian Tribe" together; a
# pattern that matched there would delete the Tejon Indian Tribe from the
# roster and publish it as removed from federal recognition.
_PREV_HEAD = (r"[\(\[]\s*(?:previously listed as|previously known as|"
              r"formerly known as|formerly)\s+(?:the\s+)?")
PREV_STRICT_RE = re.compile(_PREV_HEAD + r"(?P<prev>.+?)\s*[\)\]]\s*$", re.I)
PREV_LOOSE_RE = re.compile(_PREV_HEAD + r"(?P<prev>[^)\]]+?)\s*$", re.I)
# A cross-reference points at ANOTHER LISTED ENTITY. "(See Supplementary
# Information ...)" points at the preamble and is not one; excluding it by name
# is what keeps the 2026 Lumbee entry an entity instead of a pointer.
# The closing bracket is optional: the 2023-01-12 notice prints
# "Saint George Island (See Pribilof Islands ... ``Clarification'' section
# below" with no ")" at all, and a pattern that demands one reads a
# cross-reference as a tribe whose name is a sentence.
SEE_RE = re.compile(
    r"[\(\[]\s*See\s+(?!Supplementary\b)(?P<target>[^)\]]+?)\s*(?:[\)\]]|$)", re.I)
# "(See Supplementary Information ...)" is a pointer to the preamble, not a
# cross-reference. The 2026 Lumbee entry carries one.
NOTE_RE = re.compile(r"[\(\[]\s*See\s+Supplementary\s+Information[^)\]]*[\)\]]?", re.I)
AKA_RE = re.compile(r"\(\s*(?:aka|a\.k\.a\.)\s+(?P<aka>[^)]+)\)", re.I)


def clean_lines(path):
    t = Path(path).read_text(encoding="utf-8", errors="replace")
    t = re.sub(r"(?s)^.*?<pre>", "", t)
    t = re.sub(r"(?s)</pre>.*$", "", t)
    t = re.sub(r"(?s)<[^>]+>", "", t)
    t = html.unescape(t)
    out = []
    for l in t.split("\n"):
        if RUNHEAD_RE.match(l):
            continue
        if PAGE_ONLY_RE.match(l):
            # A standalone page marker arrives wrapped in blank lines that were
            # not in the entry. Drop the marker AND the blank that preceded it,
            # and swallow the blank that follows, so a page break in the middle
            # of an entry stops terminating the wrap.
            while out and not out[-1].strip():
                out.pop()
            out.append(None)             # sentinel: skip the next blank line
            continue
        if out and out[-1] is None:
            out.pop()
            if not l.strip():
                continue
        m = PAGE_RE.search(l)
        if m:
            # Rule 4's assumption, asserted rather than assumed.
            assert len(l[:m.start()].rstrip()) < 60, f"page marker mid-wrap: {l!r}"
            l = l[:m.start()]
        out.append(l)
    return [l for l in out if l is not None]


def _unclosed(s):
    return s.count("(") - s.count(")") > 0 or s.count("[") - s.count("]") > 0


def dewrap(lines):
    out, i, n = [], 0, len(lines)
    while i < n:
        raw = lines[i]
        if not raw.strip():
            out.append((0, ""))
            i += 1
            continue
        indent = len(raw) - len(raw.lstrip())
        buf, j = raw, i + 1
        while buf.endswith(" ") and j < n and lines[j].strip():          # rule 1
            buf += lines[j]
            j += 1
        if _unclosed(buf):                                              # rule 2
            trial, k = buf, j
            for _ in range(4):
                if k >= n or not lines[k].strip():
                    break
                trial = trial + lines[k] if trial.endswith("-") else trial + " " + lines[k]
                k += 1
                if not _unclosed(trial):
                    buf, j = trial, k
                    break                                               # rule 3
        out.append((indent, re.sub(r"\s+", " ", buf).strip()))
        i = j
    return out


def section(L, i0, i1):
    out, in_clar = [], False
    for ind, s in L[i0 + 1:i1]:
        if not s:
            continue
        if END_RE.match(s) or NOISE_RE.match(s) or SIGNATURE_RE.match(s):
            break
        if CLARIF_RE.match(s):
            in_clar = True
            continue
        if CNTHDR_RE.match(s):
            out.append((ind, s, "count_header"))
            continue
        out.append((ind, s, "clarification" if in_clar else "listed"))
    return out


def preamble(L, i48):
    """SUPPLEMENTARY INFORMATION .. first list header. Where reasons live."""
    start = next((n for n, (_, s) in enumerate(L)
                  if s.startswith("SUPPLEMENTARY INFORMATION")), 0)
    return " ".join(s for _, s in L[start:i48] if s)


def parse_notice(path):
    L = dewrap(clean_lines(path))
    i48 = next((n for n, (_, l) in enumerate(L) if SEC48_RE.search(l)), None)
    if i48 is None:
        return None                       # a supplement or correction, not a roster
    iak = next((n for n, (_, l) in enumerate(L) if n > i48 and SECAK_RE.search(l)),
               len(L))
    body = " ".join(s for _, s in L)
    st = STATED_RE.search(body)
    return {
        "sec48": section(L, i48, iak),
        "secak": section(L, iak, len(L)) if iak < len(L) else [],
        "stated_total": int(st.group(1)) if st else None,
        "preamble": preamble(L, i48),
        "full_text": body,
    }


SPLIT_CONSTITUENTS = re.compile(r";|,\s+and\s+|\s+and\s+|,")
CONSTITUENT_CUE_WORDS = re.compile(
    r"\b(Band|Village|Group|Colony|Rancheria|Island|Reservation|Community)s?\b")
CONSTITUENT_CUE_PHRASE = re.compile(
    r"component reservations|constituent bands|includes ", re.I)
CONSTITUENT_LIST_ITEM = re.compile(r"(?:^|[;,]\s*(?:&\s*|and\s+)?)[A-Z][A-Za-z'\-]+")


def looks_like_constituents(inner):
    """Does this trailing parenthetical name sub-units rather than qualify a name?

    Three signals, any one of which is enough, because the BIA writes these
    lists five different ways across the window:

      "Six component reservations: Bois Forte Band (Nett Lake); ..."   phrase
      "Cedar Band of Paiutes, Kanosh Band of Paiutes, ..."             >=2 unit words
      "Dania, Big Cypress, Brighton, Hollywood, & Tampa Reservations"  >=3 items

    And it must stay clear of the parentheticals that are part of a NAME:
    "(Aquinnah)", "(Klukwan)", "(Nett Lake)", "(Verona Tract)" - one item, no
    unit word, no phrase.
    """
    if CONSTITUENT_CUE_PHRASE.search(inner):
        return True
    if len(CONSTITUENT_CUE_WORDS.findall(inner)) >= 2:
        return True
    return len(CONSTITUENT_LIST_ITEM.findall(inner)) >= 3
# Capitan Grande and the Minnesota Chippewa Tribe list their parts three
# different ways across the window: an indented block under a colon (1995), a
# colon on one flattened line (2009), and a trailing parenthetical (2012 on).
# All three must yield the same parent and the same constituents, or the parts
# churn in and out of the roster as the typesetting changes.
COLON_PARENT_RE = re.compile(r"^(?P<parent>[^:]{10,120}):\s*(?P<parts>.+)$")

# A constituent line is indented by four spaces. One 2023 entry carries a
# single stray leading space (" Big Pine Paiute Tribe of the Owens Valley") and
# would be demoted to a sub-entity by an `indent > 0` test.
CONSTITUENT_INDENT = 3


CLARIF_TAIL_RE = re.compile(r"\s*--\s*is not included in the official count.*$", re.I)


def classify(entry, indent, parent):
    """One listed line -> a dict describing it. Nothing is flattened."""
    # The Clarification section appends its own sentence to the entity's name:
    # "Native Village of Venetie Tribal Government (Arctic Village and Village
    # of Venetie)--is not included in the official count of 574 ... but is
    # recognized as an entity authorized to act on behalf of ...". The sentence
    # is a statement about the entity, not part of what it is called.
    entry = CLARIF_TAIL_RE.sub("", entry)
    note = NOTE_RE.search(entry)
    prev = PREV_STRICT_RE.search(entry) or PREV_LOOSE_RE.search(entry)
    aka = AKA_RE.search(entry)
    see = SEE_RE.search(entry)

    base = entry
    if prev:
        base = base[:prev.start()].strip()
    if note:
        base = (base[:note.start()] + base[note.end():]).strip()
    if see:
        base = (base[:see.start()] + base[see.end():]).strip()
    # An "aka" is an alias, not part of the name. Leaving it attached makes
    # "Native Village of Chenega (aka Chanega)" and "Native Village of Chenega"
    # look like two different tribes across the 2026 notice.
    if aka:
        base = AKA_RE.sub("", base).strip()
    base = base.rstrip(",;:").strip()

    parts = ""
    m = re.search(r"\(([^()]*(?:\([^()]*\)[^()]*)*)\)\s*$", base)
    if m and not aka and looks_like_constituents(m.group(1)):
        parts = "; ".join(x.strip() for x in SPLIT_CONSTITUENTS.split(m.group(1))
                          if len(x.strip()) > 2)
        base = base[:m.start()].strip().rstrip(",;:")
    elif ":" in base and indent < CONSTITUENT_INDENT:
        cm = COLON_PARENT_RE.match(base)
        if cm and looks_like_constituents(cm.group("parts")):
            parts = "; ".join(x.strip() for x in
                              SPLIT_CONSTITUENTS.split(cm.group("parts"))
                              if len(x.strip()) > 2)
            base = cm.group("parent").strip()

    # An entry that lists its own constituents is a parent whatever its
    # indentation - the 2010 notice indents the Minnesota Chippewa Tribe.
    is_child = indent >= CONSTITUENT_INDENT and not parts
    kind = ("constituent" if is_child else
            "cross_reference" if see else
            "rename" if prev else "entity")
    # THE DECLARED OLD NAME CAN CARRY ITS OWN PARENTHETICALS, and they are not
    # part of the old name. 2026 prints "Aleut Community of St. Paul Island
    # (previously listed as Saint Paul Island (See Pribilof Islands ...))" and
    # "Louden Tribe (previously listed as Galena Village (aka Louden
    # Village))". Left in, neither declared name matches the listing it refers
    # to and the BIA's own statement that these are the same tribe is lost.
    prior = prev.group("prev").strip() if prev else ""
    if prior:
        prior = AKA_RE.sub("", SEE_RE.sub("", prior)).strip().rstrip(",;:) ")

    return (kind, base, prior,
            see.group("target").strip() if see else "",
            aka.group("aka").strip() if aka else "",
            parts, parent if is_child else "",
            note.group(0).strip() if note else "")


GLUE_RE = re.compile(r"(?<=[a-z])(?=[A-Z])")
GLUE_LOG = []   # every split made, for the build log


def repair_glue(sections, all_names):
    """Split two entries the source printed with no separator between them.

    Two forms occur. The 2015 notice prints "Eklutna Native VillageEmmonak
    Village" with the line break lost entirely. The 2000 notice ends "White
    Mountain Apache Tribe of the Fort Apache Reservation, Arizona " with a
    spurious trailing space, so the de-wrap rule glues the Wichita and
    Affiliated Tribes onto it and both tribes disappear from that year.

    The repair fires ONLY where the whole string is a name no notice ever
    carries AND both halves are names that other notices do carry - it is
    evidence-driven, never a guess - and the original string is preserved in
    `entry_raw_source` on both rows.
    """
    def base_of(t):
        return nk(classify(t, 0, "")[1])

    out, repaired = [], 0
    for ind, text, tag in sections:
        if tag == "listed":
            spots = ([mm.start() for mm in GLUE_RE.finditer(text)] +
                     [mm.start() for mm in re.finditer(r"(?<=[a-z\)])\s+(?=[A-Z])", text)])
            for pos in sorted(set(spots)):
                a, b = text[:pos].strip(), text[pos:].strip()
                if (len(a) >= 12 and len(b) >= 12 and not _unclosed(a)
                        and base_of(a) in all_names and base_of(b) in all_names):
                    out.append((ind, a, tag, text))
                    out.append((ind, b, tag, text))
                    GLUE_LOG.append((text, a, b))
                    repaired += 1
                    break
            else:
                out.append((ind, text, tag, text))
            continue
        out.append((ind, text, tag, text))
    return out, repaired


def build_roster(notices, spine, m):
    """One row per (listed entry, notice). Two passes.

    Pass 1 collects every name the notices ever declare to be a CONSTITUENT
    (from a `(A; B)` parenthetical or an indented block) plus every name that
    ever appears as a normal listing. Pass 2 uses the first set to demote
    constituents in the years where the typesetting lost the indentation, and
    the second to split glued lines.
    """
    parsed_all, const_names, parents = {}, set(), set()
    seen_in = defaultdict(set)
    for nrec in notices:
        p = RAW / f"{nrec['document_number']}_raw.txt"
        pn = parse_notice(p)
        parsed_all[nrec["document_number"]] = pn
        if pn is None:
            continue
        for sec in (pn["sec48"], pn["secak"]):
            for ind, text, tag in sec:
                if tag != "listed":
                    continue
                _, base, _, _, _, parts, _, _ = classify(text, ind, "")
                if ind >= CONSTITUENT_INDENT:
                    const_names.add(nk(base))
                if parts:
                    parents.add(nk(base))
                for c in parts.split(";"):
                    if len(c.strip()) > 8:
                        const_names.add(nk(c))
                seen_in[nk(base)].add(nrec["document_number"])
    # A GLUE ARTEFACT APPEARS ONCE; A REAL LISTING RECURS. The reference set
    # for the glue repair is therefore names carried by at least TWO notices -
    # otherwise "Eklutna Native VillageEmmonak Village" is in the set that is
    # supposed to prove it is not a name.
    all_names = {n for n, docs in seen_in.items() if len(docs) >= 2}
    # A NAME THAT CARRIES ITS OWN CONSTITUENTS IS A PARENT, NEVER A CHILD.
    # The 2010 notice indents "Minnesota Chippewa Tribe, Minnesota" by four
    # spaces - a typesetting slip. Without this subtraction that one line
    # demotes a federally recognized tribe to a sub-entity in all 30 notices,
    # and the roster silently loses it everywhere.
    demoted = const_names & parents
    if demoted:
        log(f"    parents rescued from a stray indent: {sorted(demoted)}")
    const_names -= parents

    resolved = {}

    def resolve(name):
        if name not in resolved:
            resolved[name] = m.resolve_entity(name, spine)
        return resolved[name]

    rows, per_notice, unparsed, glue_fixed = [], {}, [], 0
    for nrec in notices:
        dn = nrec["document_number"]
        parsed = parsed_all[dn]
        if parsed is None:
            unparsed.append(dn)
            continue
        cite, pub = nrec.get("citation") or "", nrec["publication_date"]
        n_listed = 0
        for sec_name, sec in (("contiguous_48", parsed["sec48"]),
                              ("alaska", parsed["secak"])):
            sec, nfix = repair_glue(sec, all_names)
            glue_fixed += nfix
            parent = ""
            for order, (ind, text, tag, src) in enumerate(sec):
                if tag == "count_header":
                    continue
                (kind, base, prev, see, aka, parts, par,
                 note) = classify(text, ind, parent)
                if not base:
                    # An orphan parenthetical. The 2023-01-12 notice breaks
                    # after "Minnesota Chippewa Tribe, Minnesota" with no
                    # trailing space, so its six component reservations land on
                    # a line of their own. They belong to the entry above.
                    if text.startswith("(") and rows and parts:
                        if not rows[-1]["constituents"]:
                            rows[-1]["constituents"] = parts
                            log(f"    orphan constituent list in {dn} attached to "
                                f"{rows[-1]['entity_name']!r}")
                            continue
                    log(f"    !! empty entity name in {dn}: {text[:80]!r} - skipped")
                    continue
                if ind < CONSTITUENT_INDENT and parts:
                    parent = base
                elif ind < CONSTITUENT_INDENT:
                    parent = ""
                if kind == "entity" and nk(base) in const_names:
                    kind, par = "constituent", parent
                if tag == "clarification":
                    kind = "clarification_note"
                if kind in ("entity", "rename", "cross_reference"):
                    n_listed += 1
                tid, canon, how = resolve(base)
                rows.append({
                    "fr_document_number": dn,
                    "fr_citation": cite,
                    "publication_date": pub,
                    "notice_year": pub[:4],
                    "section": sec_name,
                    "list_order": order,
                    "entry_kind": kind,
                    "entity_name": base,
                    "previously_listed_as": prev,
                    "see_instead": see,
                    "also_known_as": aka,
                    "constituents": parts,
                    "parent_fr_name": par,
                    "listing_note": note,
                    "entry_raw": text,
                    "entry_raw_source": src,
                    "tribe_id": tid or "",
                    "spine_canonical_name": canon or "",
                    "resolve_method": how,
                    "source_url": nrec.get("html_url") or "",
                    "fetched_date": TODAY,
                })
        per_notice[dn] = {
            "publication_date": pub, "citation": cite,
            "title": nrec.get("title") or "",
            "stated_total": parsed["stated_total"],
            "parsed_listed": n_listed,
            "preamble": parsed["preamble"],
            "full_text": parsed["full_text"],
            "html_url": nrec.get("html_url") or "",
        }
    if glue_fixed:
        log(f"    glued source lines split on adjacent-notice evidence: {glue_fixed}")
    return rows, per_notice, unparsed


# --------------------------------------------------- C. identity across years

class UF:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra


DECLARED_MATCH_MIN = 0.85


def build_identity(rows, order, m):
    """Give every name that has ever denoted one entity a single key.

    Three sources of identity, in order of authority:
      1. the notice's own "(previously listed as X)" - the BIA saying these are
         the same nation
      2. the same resolved spine tribe_id
      3. the same normalised name

    Without this the 2012 notice alone produces ~100 phantom ADDED and ~98
    phantom REMOVED, because that year the BIA restyled a hundred names at once.
    """
    import difflib
    pos = {dn: i for i, dn in enumerate(order)}
    names_by_notice = defaultdict(set)
    for r in rows:
        if r["entry_kind"] not in ("constituent", "clarification_note"):
            names_by_notice[r["fr_document_number"]].add(nk(r["entity_name"]))

    uf = UF()
    for r in rows:
        if r["entry_kind"] in ("constituent", "clarification_note"):
            continue
        k = nk(r["entity_name"])
        uf.find(k)
        if not r["previously_listed_as"]:
            continue
        for prior in re.split(r",\s*and as\s+|\s+and as\s+|,\s*and\s+the\s+",
                              r["previously_listed_as"]):
            prior = prior.strip().rstrip(".")
            if len(prior) <= 3:
                continue
            np = nk(prior)
            uf.union(k, np)
            # THE BIA WRITES THE OLD NAME FROM MEMORY, NOT FROM THE OLD LIST.
            # The 1998 notice says "(formerly the Coast Indian Community of
            # Yurok Indians of the Resighini Rancheria)" while the 1997 list
            # reads "... Resighini Rancheria, California". Exact matching on
            # the declared string therefore fails, and the tribe is published
            # as removed and separately re-recognised. The declared name is
            # matched to the closest name actually listed in an EARLIER notice.
            i = pos.get(r["fr_document_number"], 0)
            best, score = None, 0.0
            for dn in order[:i]:
                for cand in names_by_notice[dn]:
                    if cand == np:
                        best, score = cand, 1.0
                        break
                    s = difflib.SequenceMatcher(None, np, cand).ratio()
                    if s > score:
                        best, score = cand, s
                if score == 1.0:
                    break
            if best and score >= DECLARED_MATCH_MIN:
                uf.union(k, best)
    # A SHARED tribe_id IS EVIDENCE ONLY WHEN THE RESOLVER WAS CERTAIN.
    #
    # `resolve_entity` returns `containment` and `core` matches that are good
    # enough for attributing a contract and far too loose for asserting that
    # two Federal Register listings are one nation. Measured on this corpus,
    # containment sent "Alturas Indian Rancheria of Pit River Indians of
    # California" to the PIT RIVER TRIBE, "Cherokee Nation, Oklahoma" to the
    # UNITED KEETOOWAH BAND, and "Jena Band of Choctaw Indians, Louisiana" to a
    # STATE-recognized Louisiana Choctaw band. Each of those unions merges two
    # different nations, and the merge then MASKS a real event: the Alturas
    # rename vanished because its old name had been absorbed into Pit River,
    # which was present in both years.
    #
    # So only `exact` and `alias` count here. Everything looser is left to the
    # notice's own "previously listed as" and to the bridging pass, both of
    # which are recorded per pair and auditable.
    by_tid = defaultdict(set)
    for r in rows:
        if (r["tribe_id"] and r["resolve_method"] in ("exact", "alias")
                and r["entry_kind"] in PRESENT_KINDS):
            by_tid[r["tribe_id"]].add(nk(r["entity_name"]))
    for names in by_tid.values():
        names = sorted(names)
        for x in names[1:]:
            uf.union(names[0], x)
    return uf


# ------------------------------------------------------------------ D. diff --

ADD_TITLE_RE = re.compile(
    r"final determination.*acknowledg|determination to acknowledg|"
    r"acknowledg.*final determination|restoration of|reaffirm|"
    r"final determination that .* does exist|to acknowledge the", re.I)
NEG_TITLE_RE = re.compile(r"against|decline|not to acknowledg", re.I)

# Ordered. The first pattern that matches wins, so the most specific statutory
# and judicial language is tested before the generic acknowledgment wording -
# the Virginia tribes' notice says both "Federal Recognition Act of 2017" and
# "acknowledged", and the Act is the mechanism.
MECHANISMS = [
    ("act_of_congress",
     re.compile(r"\bPub(?:lic)?\.?\s*L(?:aw)?\.?\s*\d+-\d+|Act of Congress|"
                r"enactment of|National Defense Authorization Act|"
                r"Restoration Act|Recognition Act|Welfare Act|"
                r"under federal statute|by (?:Federal )?statute|"
                r"legislation|"
                r"Titles? \d+ (?:and \d+ )?of the Act", re.I)),
    ("court_order",
     re.compile(r"court order|court-ordered|United States District Court|"
                r"stipulated judgment|settlement stipulation|consent decree|"
                r"court of appeals|final judgment and order", re.I)),
    ("administrative_appeal_order_ibia",
     re.compile(r"Interior Board of Indian Appeals|\bIBIA\b", re.I)),
    ("administrative_reaffirmation",
     re.compile(r"reaffirm|administrative oversight|omitted from (?:the )?earlier|"
                r"had been omitted", re.I)),
    ("administrative_acknowledgment_25cfr83",
     re.compile(r"25 CFR (?:[Pp]art )?83|part 83|Federal acknowledgment|"
                r"acknowledgment regulations|final determination|"
                r"acknowledged under", re.I)),
    ("restoration",
     re.compile(r"\brestor(?:ation|ed|e)\b|reestablish", re.I)),
]
# The Federally Recognized Indian Tribe List Act is cited in the preamble of
# EVERY notice as the authority to publish the list. It is never the reason a
# particular tribe was added, so recording it as one would put a false statute
# on 30 years of events.
PUBLICATION_AUTHORITY_PL = {"Pub. L. 103-454"}


def sentences(t):
    return [s.strip() for s in re.split(r"(?<=[.;])\s+(?=[A-Z(])", t or "")
            if s.strip()]


def distinctive(name, m):
    """Tokens that actually identify a tribe, for text search."""
    toks = [w for w in m.norm(name).split()
            if w not in m.STRUCTURAL and len(w) > 3]
    return toks


def find_quote(name, notice, prior_notice, fed_actions, m):
    """A verbatim sentence that speaks to this entity's status change.

    Order: the notice's own preamble, then any acknowledgment/restoration
    document filed between the two notices, then the roster line itself.
    Never a paraphrase, and `quote_basis` always says which of the three.
    """
    toks = distinctive(name, m)
    lead = lead_token(name, m)
    if toks:
        sents = sentences(notice["preamble"])
        for i, s in enumerate(sents):
            ns = m.norm(s)
            hits = sum(1 for t in toks if t in ns)
            # The lead identifying word must be there. Two matching words is
            # the normal bar, but a single distinctive one is enough when it is
            # long: the 2002 preamble names "the Graton Rancheria" and the 2000
            # preamble "the Snoqualmie Tribe" without the state, and requiring
            # two words loses the sentence that states the mechanism.
            if lead and lead in ns and (hits >= 2 or len(lead) >= 6):
                # The reason often sits in the NEXT sentence: 2026 names the
                # Lumbee Tribe in one sentence and cites "Public Law 119-60,
                # section 8803" in the one after. The quote stays the single
                # sentence; the window is what statute extraction reads.
                ctx = " ".join(sents[max(0, i - 1):i + 3])
                return (s, "notice_preamble", notice["citation"],
                        notice["html_url"], ctx)

    lo = prior_notice["publication_date"] if prior_notice else "1994-01-01"
    hi = notice["publication_date"]
    best = None
    for a in fed_actions:
        if not (lo <= a["publication_date"] <= hi):
            continue
        title = a.get("title") or ""
        if not ADD_TITLE_RE.search(title) or NEG_TITLE_RE.search(title):
            continue
        nt = m.norm(title + " " + (a.get("abstract") or ""))
        if toks and all(t in nt for t in toks[:2]):
            best = a
            break
    if best:
        q = (best.get("title") or "").strip()
        ab = (best.get("abstract") or "").strip()
        if ab:
            q = q + " -- " + sentences(ab)[0]
        return (q, "related_fr_document",
                f"FR {best['publication_date']} doc {best['document_number']}",
                best.get("html_url") or "", q)
    return None, "", "", "", ""


def classify_mechanism(quote, context=""):
    """The QUOTE is the evidence; the surrounding window is only a fallback.

    Classifying on the window first put "administrative_reaffirmation" on the
    Cowlitz Indian Tribe because the sentence AFTER its own - "The Assistant
    Secretary reaffirmed the formal recognition of the King Salmon Tribe ..." -
    was in the window. Cowlitz was acknowledged under 25 CFR part 83, and its
    own sentence says so.
    """
    for text, where in ((quote, "quote"), (context, "surrounding_text")):
        if not text:
            continue
        for label, pat in MECHANISMS:
            hit = pat.search(text)
            if hit:
                return label, f"matched_in_{where}:{hit.group(0)[:60]}"
    return "", "not_stated_in_record"


BRIDGE_MIN = 0.90


# PRESENT IN THE NOTICE, THOUGH NOT IN THE COUNT.
#
# In 2022 and 2023-01 the BIA moved the Native Village of Venetie Tribal
# Government and the Pribilof Islands Aleut Communities into a *Clarification*
# section reading "is not included in the official count of 574 federally
# recognized Indian Tribes but IS RECOGNIZED as an entity authorized to act on
# behalf of ...". They are excluded from `parsed_listed`, because the BIA
# excludes them from its total - but they are emphatically still recognised, so
# treating their move as a de-listing and their return as a restoration would
# publish four events that did not happen.
PRESENT_KINDS = ("entity", "rename", "cross_reference", "clarification_note")


def _index(roster, uf):
    idx = defaultdict(dict)
    for r in roster:
        if r["entry_kind"] not in PRESENT_KINDS:
            continue
        idx[r["fr_document_number"]][uf.find(nk(r["entity_name"]))] = r
    return idx


CORE_OVERLAP_MIN = 0.50


def core_subset_bridge(a, b, m):
    """Is the shorter name the BIA's shortened form of the longer one?

    Between 1998 and 2019 the BIA repeatedly dropped the geographic tail from
    listings without marking the change: "Alturas Indian Rancheria of Pit River
    Indians of California" -> "Alturas Indian Rancheria, California",
    "Cherokee Nation, Oklahoma" -> "Cherokee Nation", "Jena Band of Choctaw
    Indians, Louisiana" -> "Jena Band of Choctaw Indians". Those are one nation
    under two names and must not be published as a removal plus an addition.

    Three conditions, and all three are needed:

      1. the shorter name's identifying tokens are ALL inside the longer's
      2. they are at least half of the longer's - this refuses "Chickahominy
         Indian Tribe" against "Chickahominy Indian Tribe--Eastern Division"
         (one token in common out of three), two different tribes both
         recognised in 2018
      3. THE TWO NAMES LEAD WITH THE SAME IDENTIFYING WORD. `core` is a set and
         throws away word order, so without this the rule paired the Wichita
         and Affiliated Tribes with the White Mountain Apache Tribe, the Potter
         Valley Rancheria with the Port Gamble Indian Community, and the
         Muscogee (Creek) Nation with the Muckleshoot Indian Tribe. Every one
         of those would have published a tribe as de-listed and another as
         newly recognised, on nothing.

    Returns the overlap ratio, or 0.0 for no bridge.
    """
    ca, cb = m.core(a), m.core(b)
    if not ca or not cb:
        return 0.0
    if lead_token(a, m) != lead_token(b, m) or not lead_token(a, m):
        return 0.0
    if ca == cb:
        # Identical identifying tokens, same leading word, different strings:
        # "Chickasaw Nation" / "The Chickasaw Nation", "Osage Tribe, Oklahoma"
        # / "Osage Nation, Oklahoma", "Kaw Indian Tribe of Oklahoma" / "Kaw
        # Nation, Oklahoma". Everything that differs is a structural word.
        # The leading-word test is what keeps this away from the pair `core`
        # cannot tell apart at all - "Shoshone-Paiute Tribes of the Duck Valley
        # Reservation" and "Paiute-Shoshone Tribes of the Fallon Reservation".
        return 1.0
    small, big = (ca, cb) if len(ca) < len(cb) else (cb, ca)
    if not small <= big:
        return 0.0
    ratio = len(small) / len(big)
    return ratio if ratio >= CORE_OVERLAP_MIN else 0.0


def lead_token(name, m):
    for w in m.norm(name).split():
        if w not in m.STRUCTURAL:
            return w
    return ""


def bridge_near_identical(roster, uf, order, m):
    """Bridge the source's own misspellings between consecutive notices.

    The notices carry real typographical drift - "Qawalingin"/"Qawalangin",
    "San Manual"/"San Manuel", "Sokoagon"/"Sokaogon", "Chuatbaluk"/
    "Chuathbaluk", "Muskogee"/"Muscogee", "Clarks's Point"/"Clark's Point",
    "Artic Village"/"Arctic Village". Each pair is one nation, and emitting it
    as a removal plus an addition would assert that a tribe lost and regained
    federal recognition. That is a fabricated fact about a nation's legal
    status, so it is not acceptable to leave it.

    The bridge is deliberately narrow: only names left over after exact and
    declared-rename matching, only between CONSECUTIVE notices, only at
    difflib ratio >= 0.90, and only one-to-one, best pair first. Every bridge
    is recorded and reported. "Chickahominy Indian Tribe" against
    "Chickahominy Indian Tribe--Eastern Division" scores 0.85 and is refused -
    they are two different tribes, both recognised in 2018.
    """
    import difflib
    bridges = []
    for i in range(1, len(order)):
        idx = _index(roster, uf)
        cur, prev = idx[order[i]], idx[order[i - 1]]
        adds, rems = sorted(set(cur) - set(prev)), sorted(set(prev) - set(cur))
        cands = []
        for a in adds:
            for b in rems:
                na, nb = cur[a]["entity_name"], prev[b]["entity_name"]
                ratio = difflib.SequenceMatcher(None, nk(na), nk(nb)).ratio()
                if ratio >= BRIDGE_MIN:
                    cands.append((ratio, "typographic_variant", a, b))
                    continue
                sub = core_subset_bridge(na, nb, m)
                if sub:
                    cands.append((sub, "bia_shortened_the_listed_name", a, b))
        cands.sort(key=lambda x: -x[0])
        used_a, used_b = set(), set()
        for ratio, why, a, b in cands:
            if a in used_a or b in used_b:
                continue
            used_a.add(a)
            used_b.add(b)
            bridges.append({"notice": order[i],
                            "new_name": cur[a]["entity_name"],
                            "old_name": prev[b]["entity_name"],
                            "rule": why,
                            "similarity": round(ratio, 4)})
            uf.union(b, a)
    return bridges


def diff_notices(roster, per_notice, uf, order, fed_actions, m, bridged):
    import difflib
    idx = _index(roster, uf)
    seen_before = {}                              # key -> last dn it appeared in
    events = []
    for i, dn in enumerate(order):
        cur = idx[dn]
        if i == 0:
            for k in cur:
                seen_before[k] = dn
            continue
        prev_dn = order[i - 1]
        prev = idx[prev_dn]
        note, pnote = per_notice[dn], per_notice[prev_dn]
        adds, rems = sorted(set(cur) - set(prev)), sorted(set(prev) - set(cur))

        def counterpart(name, pool, src):
            """Nearest same-notice opposite-side name, REPORTED not asserted.

            Anything that survived the 0.90 bridge but still looks like the
            same nation renamed is surfaced here so a reviewer sees it. The
            event type is left as ADDED or REMOVED because the evidence did not
            reach the bar - a flag, never a claim.
            """
            best, score = "", 0.0
            for k2 in pool:
                other = src[k2]["entity_name"]
                r2 = difflib.SequenceMatcher(None, nk(name), nk(other)).ratio()
                if r2 > score:
                    best, score = other, r2
            return (f"{best} (similarity {score:.2f})"
                    if score >= 0.60 else "")

        for k in adds:
            row = cur[k]
            ever = k in seen_before
            q, basis, qcite, qurl, ctx = find_quote(row["entity_name"], note,
                                                    pnote, fed_actions, m)
            mech, mbasis = classify_mechanism(q, ctx)
            events.append(dict(
                event_type="RESTORED" if ever else "ADDED",
                entity_name=row["entity_name"],
                previous_name=row["previously_listed_as"],
                entity_key=k,
                tribe_id=row["tribe_id"],
                spine_canonical_name=row["spine_canonical_name"],
                effective_date=note["publication_date"],
                effective_date_basis="fr_publication_date_of_first_listing",
                fr_document_number=dn,
                fr_citation=note["citation"],
                prior_notice_document=prev_dn,
                prior_notice_citation=pnote["citation"],
                mechanism=mech,
                mechanism_basis=mbasis,
                quote=q or row["entry_raw"],
                quote_basis=basis or "roster_line",
                quote_context=ctx or "",
                quote_citation=qcite or note["citation"],
                quote_url=qurl or note["html_url"],
                section=row["section"],
                possible_rename_counterpart=counterpart(
                    row["entity_name"], rems, prev),
                source_url=note["html_url"],
                fetched_date=TODAY))

        for k in rems:
            row = prev[k]
            q, basis, qcite, qurl, ctx = find_quote(row["entity_name"], note,
                                                    pnote, fed_actions, m)
            mech, mbasis = classify_mechanism(q, ctx)
            events.append(dict(
                event_type="REMOVED",
                entity_name=row["entity_name"],
                previous_name=row["previously_listed_as"],
                entity_key=k,
                tribe_id=row["tribe_id"],
                spine_canonical_name=row["spine_canonical_name"],
                effective_date=note["publication_date"],
                effective_date_basis="fr_publication_date_of_first_absence",
                fr_document_number=dn,
                fr_citation=note["citation"],
                prior_notice_document=prev_dn,
                prior_notice_citation=pnote["citation"],
                # A REMOVAL IS NOT A TERMINATION unless the record says so.
                mechanism=mech,
                mechanism_basis=(mbasis if mech else
                                 "not_stated_in_record; a removal is not "
                                 "evidence of termination"),
                quote=q or row["entry_raw"],
                quote_basis=basis or "roster_line_of_prior_notice",
                quote_context=ctx or "",
                quote_citation=qcite or pnote["citation"],
                quote_url=qurl or pnote["html_url"],
                section=row["section"],
                possible_rename_counterpart=counterpart(
                    row["entity_name"], adds, cur),
                source_url=note["html_url"],
                fetched_date=TODAY))

        for k in sorted(set(cur) & set(prev)):
            row, old = cur[k], prev[k]
            if nk(row["entity_name"]) == nk(old["entity_name"]):
                continue
            marked = bool(row["previously_listed_as"])
            br = bridged.get((dn, nk(row["entity_name"]), nk(old["entity_name"])))
            events.append(dict(
                event_type="RENAMED",
                entity_name=row["entity_name"],
                previous_name=row["previously_listed_as"] or old["entity_name"],
                entity_key=k,
                tribe_id=row["tribe_id"],
                spine_canonical_name=row["spine_canonical_name"],
                effective_date=note["publication_date"],
                effective_date_basis="fr_publication_date_of_the_new_name",
                fr_document_number=dn,
                fr_citation=note["citation"],
                prior_notice_document=prev_dn,
                prior_notice_citation=pnote["citation"],
                mechanism="name_change_listed_by_bia",
                mechanism_basis=(
                    "notice_marks_previously_listed_as" if marked else
                    f"bridged:{br[0]}:{br[1]:.2f}" if br else
                    "name_differs_between_consecutive_notices"),
                quote=row["entry_raw"] if marked else
                      f'{old["entry_raw"]}  ->  {row["entry_raw"]}',
                quote_basis="roster_line" if marked else "roster_lines_both_notices",
                quote_context="",
                quote_citation=note["citation"],
                quote_url=note["html_url"],
                section=row["section"],
                possible_rename_counterpart="",
                source_url=note["html_url"],
                fetched_date=TODAY))

        for k in cur:
            seen_before[k] = dn
    return events


def offlist_events(notices, m, spine):
    """The supplement and the correction - real events with no roster of their own."""
    out = []
    for nrec in notices:
        dn = nrec["document_number"]
        p = RAW / f"{dn}_raw.txt"
        if not p.exists() or parse_notice(p) is not None:
            continue
        L = dewrap(clean_lines(p))
        body = " ".join(s for _, s in L if s)
        body = body[body.find("SUPPLEMENTARY INFORMATION"):] or body
        for s in sentences(body):
            add = re.search(r"(?P<n>[A-Z][^,.]{6,90}?)\s+is an Indian entity "
                            r"recognized and eligible", s)
            if add:
                nm = add.group("n").strip()
                nm = re.sub(r"^(the|As of [^,]+, the)\s+", "", nm, flags=re.I)
                tid, canon, _ = m.resolve_entity(nm, spine)
                mech, mbasis = classify_mechanism(s)
                out.append(dict(
                    event_type="ADDED", entity_name=nm, previous_name="",
                    entity_key=nk(nm), tribe_id=tid or "",
                    spine_canonical_name=canon or "",
                    effective_date=nrec["publication_date"],
                    effective_date_basis="fr_publication_date_of_supplement",
                    fr_document_number=dn, fr_citation=nrec.get("citation") or "",
                    prior_notice_document="", prior_notice_citation="",
                    mechanism=mech, mechanism_basis=mbasis,
                    quote=s, quote_basis="supplemental_notice", quote_context=s,
                    quote_citation=nrec.get("citation") or "",
                    quote_url=nrec.get("html_url") or "", section="",
                    possible_rename_counterpart="",
                    source_url=nrec.get("html_url") or "", fetched_date=TODAY))
            corr = re.search(r"correct\s+(?:the name of\s+)?``(?P<old>[^`]+?)''\s*"
                             r"to read\s+``(?P<new>[^`]+?)''", s)
            if corr:
                old = re.sub(r"\s*[\[(].*", "", corr.group("old")).strip()
                new = re.sub(r"\s*[\[(].*", "", corr.group("new")).strip()
                tid, canon, _ = m.resolve_entity(new, spine)
                out.append(dict(
                    event_type="RENAMED", entity_name=new, previous_name=old,
                    entity_key=nk(new), tribe_id=tid or "",
                    spine_canonical_name=canon or "",
                    effective_date=nrec["publication_date"],
                    effective_date_basis="fr_publication_date_of_correction",
                    fr_document_number=dn, fr_citation=nrec.get("citation") or "",
                    prior_notice_document="", prior_notice_citation="",
                    mechanism="name_change_listed_by_bia",
                    mechanism_basis="correction_notice_requested_by_the_tribe",
                    quote=s, quote_basis="correction_notice", quote_context=s,
                    quote_citation=nrec.get("citation") or "",
                    quote_url=nrec.get("html_url") or "", section="",
                    possible_rename_counterpart="",
                    source_url=nrec.get("html_url") or "", fetched_date=TODAY))
    return out


# ---------------------------------------------------- E. tie to legislation --

# The hyphen can carry a line break. GPO wraps "See Public Law 119-\n60,
# section 8803" and the de-wrap leaves "Public Law 119- 60", so a pattern
# without \s* around the dash misses the statute that recognised the Lumbee
# Tribe - the single most important citation in this dataset.
PL_RE = re.compile(
    r"P(?:ub|ublic)\.?\s*L(?:aw|\.)?\s*(?:No\.\s*)?(\d{2,3})\s*[-\u2013]\s*(\d+)")
BILL_RECOG_RE = re.compile(
    r"recogni|acknowledg|restor|reaffirm|federal status|status.*restor", re.I)


STATUTE_NAME_RE = re.compile(
    r"\b(?:the\s+)?((?:[A-Z][\w'’.\-]*\s+){1,10}Act(?:\s+of\s+\d{4})?)")
BILL_LOOKBACK_YEARS = 12


def tie_to_legislation(events, per_notice, bills, m):
    """Three links, in descending order of certainty, all auditable.

    1. `public_law_cited` - a public law number in the Federal Register text
       that evidences THIS event. The Lumbee entry is the worked example: the
       2026 preamble says "See Public Law 119-60, section 8803."
    2. `statute_named` - the Act's title as the notice writes it, verbatim, for
       the several statutes the BIA names without a number ("Thomasina E.
       Jordan Indian Tribes of Virginia Federal Recognition Act of 2017").
    3. `bill_ids` - rows of native_bills.csv. Two strengths, never mixed:
         enacted_public_law_number_matches   the bill BECAME that public law
         bill_title_names_the_tribe          a bill on this tribe's
                                             recognition, introduced before the
                                             event and within 12 years of it

    The time window matters. Without it the Samish Indian Tribe's 1996
    acknowledgment was linked to House bills from 2019, 2021 and 2023 - real
    bills about the Samish, and no part of why the tribe was listed in 1996.

    We write join keys onto OUR rows. `native_bills.csv` is not modified; a
    bills-and-votes agent owns it.
    """
    by_title, by_pl = [], defaultdict(list)
    for b in bills:
        t = b.get("title") or ""
        if BILL_RECOG_RE.search(t):
            by_title.append((m.norm(t), b))
        for a, c in PL_RE.findall((b.get("latest_action") or "") + " "
                                  + (b.get("outcome") or "")):
            by_pl[f"Pub. L. {a}-{c}"].append(b["bill_id"])

    linked = 0
    for e in events:
        text = " ".join([e.get("quote_context") or "", e["quote"]])
        pls = sorted({f"Pub. L. {a}-{b}" for a, b in PL_RE.findall(text)}
                     - PUBLICATION_AUTHORITY_PL)
        e["public_law_cited"] = "; ".join(pls)
        e["public_law_basis"] = ("cited_in_the_fr_text_evidencing_this_event"
                                 if pls else "")
        # Quote first, window second, and say which - the window around the
        # Wilton Rancheria sentence contains the Oklahoma Indian Welfare Act,
        # which is the Delaware Tribe's statute, not Wilton's.
        # The window is consulted ONLY when the quote already established that
        # an Act of Congress was the mechanism. Otherwise the Oklahoma Indian
        # Welfare Act, which sits one sentence away in the 2009 preamble, lands
        # on the Wilton Rancheria - whose own sentence says a court order.
        sources = [(e["quote"], "quote")]
        if e["mechanism"] == "act_of_congress":
            sources.append((e.get("quote_context") or "", "surrounding_text"))
        names, where = [], ""
        for src, lbl in sources:
            names = sorted({n.strip() for n in STATUTE_NAME_RE.findall(src)
                            if "Indian Tribe List Act" not in n
                            and len(n.split()) >= 3})
            if names:
                where = lbl
                break
        e["statute_named"] = "; ".join(names[:3])
        e["statute_named_basis"] = (f"verbatim_from_the_{where}" if names else "")

        hits, basis = [], ""
        for pl in pls:
            hits += by_pl.get(pl, [])
        if hits:
            basis = "enacted_public_law_number_matches_native_bills_latest_action"
        elif e["event_type"] in ("ADDED", "RESTORED"):
            toks = distinctive(e["entity_name"], m)
            yr = int(e["effective_date"][:4])
            for nt, b in by_title:
                if not toks or not all(t in nt for t in toks[:2]):
                    continue
                d = (b.get("introduced_date") or "")[:4]
                if d.isdigit() and yr - BILL_LOOKBACK_YEARS <= int(d) <= yr:
                    hits.append(b["bill_id"])
            if hits:
                basis = ("bill_title_names_the_tribe_and_recognition; "
                         f"introduced within {BILL_LOOKBACK_YEARS} years before "
                         "the listing; NOT evidence that this bill caused it")
        e["bill_ids"] = "; ".join(sorted(set(hits))[:8])
        e["bill_link_basis"] = basis
        # A REMOVAL WITH A LOOK-ALIKE IN THE SAME NOTICE IS PROBABLY A RENAME.
        # It did not clear the bridging bar, so it is not asserted as one - it
        # is flagged, and a reviewer settles it in one pass.
        e["review_flag"] = ("possible_unmarked_rename"
                            if (e["event_type"] in ("ADDED", "REMOVED")
                                and e.get("possible_rename_counterpart")) else "")
        if pls or hits or names:
            linked += 1
    return linked


# ------------------------------------------------------- F. alias proposals --

def propose_aliases(roster, spine, m):
    have = {}
    for r in spine:
        s = {m.norm(r["canonical_name"])}
        s |= {m.norm(a) for a in (r.get("aliases") or "").split("|") if a.strip()}
        if r.get("fr_official_name"):
            s.add(m.norm(r["fr_official_name"]))
        have[r["tribe_id"]] = s

    seen, props, dropped = set(), [], []
    for r in roster:
        tid = r["tribe_id"]
        if not tid or r["entry_kind"] in ("constituent", "clarification_note"):
            continue
        cands = [(r["entity_name"], "fr_listed_name"),
                 (r["previously_listed_as"], "fr_previously_listed_as"),
                 (r["also_known_as"], "fr_also_known_as")]
        for name, why in cands:
            name = (name or "").strip()
            if len(name) < 4:
                continue
            n = m.norm(name)
            if n in have.get(tid, set()) or (tid, n) in seen:
                continue
            seen.add((tid, n))
            # PRECISION OVER RECALL. A loose (`containment`) resolution whose
            # leading identifying word does not match the spine entity's is
            # almost always the wrong entity - "Alturas Indian Rancheria of Pit
            # River Indians of California" resolving to the PIT RIVER TRIBE is
            # the measured case. Merging that alias would make every historical
            # Alturas contract resolve to Pit River, which is the exact failure
            # this file exists to prevent, so the row is dropped and counted
            # rather than handed over for a hand check that has to catch it.
            conf = {"exact": "high", "alias": "high",
                    "core": "medium"}.get(r["resolve_method"], "low")
            if conf == "low" and lead_token(name, m) != lead_token(
                    r["spine_canonical_name"], m):
                dropped.append({
                    "proposed_alias": name,
                    "resolved_to_tribe_id": tid,
                    "resolved_to_canonical_name": r["spine_canonical_name"],
                    "resolve_method": r["resolve_method"],
                    "drop_reason": "leading identifying word differs from the "
                                   "resolved spine entity; a containment match "
                                   "across different lead words is usually a "
                                   "different tribe",
                    "first_seen_fr_document": r["fr_document_number"],
                    "first_seen_citation": r["fr_citation"],
                    "verbatim_entry": r["entry_raw"],
                    "YOUR_RULING": "",
                })
                continue
            props.append({
                "tribe_id": tid,
                "spine_canonical_name": r["spine_canonical_name"],
                "proposed_alias": name,
                "alias_source": why,
                "first_seen_fr_document": r["fr_document_number"],
                "first_seen_citation": r["fr_citation"],
                "first_seen_publication_date": r["publication_date"],
                "resolve_method": r["resolve_method"],
                # HOW MUCH THIS ROW CAN BE TRUSTED WITHOUT READING IT.
                # `containment` is the method that put Alturas on the Pit River
                # Tribe and Cherokee Nation, Oklahoma on the United Keetoowah
                # Band. Merging an alias onto the wrong spine row would make
                # every historical contract of one tribe resolve to another -
                # exactly the failure this file exists to prevent. So the
                # method is carried through, ranked, and the loose ones sort
                # last for review.
                "resolve_confidence": conf,
                "verbatim_entry": r["entry_raw"],
                "proposed_by": "code/76_build_recognition_history.py",
                "proposed_date": TODAY,
                "YOUR_RULING": "",
            })
    # keep the EARLIEST sighting of each alias
    props.sort(key=lambda x: (x["tribe_id"], x["proposed_alias"],
                              x["first_seen_publication_date"]))
    out, last = [], None
    for p in props:
        key = (p["tribe_id"], m.norm(p["proposed_alias"]))
        if key == last:
            continue
        last = key
        out.append(p)
    rank = {"high": 0, "medium": 1, "low": 2}
    out.sort(key=lambda x: (rank[x["resolve_confidence"]],
                            x["first_seen_publication_date"], x["tribe_id"]))
    return out, dropped


# ------------------------------------------------------------------- main ---

def main():
    global _logfh
    LOGS.mkdir(parents=True, exist_ok=True)
    _logfh = open(LOGS / f"76_recognition_history_{TODAY}.log", "w",
                  encoding="utf-8")
    offline = "--offline" in sys.argv

    log("=== Cedar Press 76: federal recognition roster and events ===\n")
    m = load_m33()
    spine = read_csv(SPINE_P)
    log(f"spine entities: {len(spine):,}")

    log("\n--- A. discovery -------------------------------------------------")
    notices = discover(offline=offline)
    got, missing = ([n for n in notices
                     if (RAW / f"{n['document_number']}_raw.txt").exists()], []) \
        if offline else fetch_raw(notices)
    log(f"  raw text on disk for {len(got)} of {len(notices)} notices")
    for dn, why in missing:
        log(f"    MISSING {dn}: {why}")

    log("\n--- B. parse -----------------------------------------------------")
    roster, per_notice, unparsed = build_roster(got, spine, m)
    log(f"  roster notices parsed : {len(per_notice)}")
    log(f"  not a roster (supplement/correction): {unparsed}")
    log(f"  roster rows           : {len(roster):,}")
    kinds = Counter(r["entry_kind"] for r in roster)
    for k, v in kinds.most_common():
        log(f"    {k:22s} {v:6,}")

    log("\n  parsed vs the count each notice states about itself:")
    log(f"    {'document':14s} {'date':11s} {'parsed':>7s} {'stated':>7s} {'diff':>6s}")
    recon = []
    for dn, n in sorted(per_notice.items(), key=lambda x: x[1]["publication_date"]):
        d = (n["parsed_listed"] - n["stated_total"]) if n["stated_total"] else None
        recon.append((dn, n, d))
        log(f"    {dn:14s} {n['publication_date']:11s} {n['parsed_listed']:7d} "
            f"{n['stated_total'] if n['stated_total'] else '-':>7} "
            f"{d if d is not None else '-':>6}")

    log("\n--- C. entity identity across notices -----------------------------")
    order = [dn for dn, _ in sorted(per_notice.items(),
                                    key=lambda x: x[1]["publication_date"])]
    uf = build_identity(roster, order, m)
    keys = {uf.find(nk(r["entity_name"])) for r in roster
            if r["entry_kind"] in PRESENT_KINDS}
    log(f"  distinct entities over the whole window: {len(keys):,}")
    log(f"  resolved to a spine tribe_id           : "
        f"{sum(1 for r in roster if r['tribe_id']):,} of {len(roster):,} rows")

    log("\n--- D/E. diff and evidence ----------------------------------------")
    fed_actions = read_csv(CLEAN / "federal_actions.csv")
    log(f"  federal_actions.csv rows available as evidence: {len(fed_actions):,}")
    bridges = bridge_near_identical(roster, uf, order, m)
    log(f"  unmarked renames bridged: {len(bridges)}")
    for b in sorted(bridges, key=lambda x: x["rule"]):
        log(f"    [{b['rule'][:28]:28s} {b['similarity']:.2f}]  "
            f"{b['old_name'][:40]:40s} -> {b['new_name'][:40]}")
    bridged = {(b["notice"], nk(b["new_name"]), nk(b["old_name"])):
               (b["rule"], b["similarity"]) for b in bridges}
    events = diff_notices(roster, per_notice, uf, order, fed_actions, m, bridged)
    extra = offlist_events(got, m, spine)
    log(f"  events from consecutive-notice diffs : {len(events):,}")
    log(f"  events from supplement/correction    : {len(extra):,}")
    events += extra
    events.sort(key=lambda e: (e["effective_date"], e["event_type"],
                               e["entity_name"]))

    bills = read_csv(CLEAN / "native_bills.csv")
    linked = tie_to_legislation(events, per_notice, bills, m)
    log(f"  native_bills.csv rows read (not modified): {len(bills):,}")
    log(f"  events carrying a public law or a bill_id: {linked:,}")

    for k, v in Counter(e["event_type"] for e in events).most_common():
        log(f"    {k:10s} {v:5,}")
    log("  mechanisms:")
    for k, v in Counter(e["mechanism"] or "(not stated)"
                        for e in events).most_common():
        log(f"    {k:42s} {v:5,}")
    log("  quote basis:")
    for k, v in Counter(e["quote_basis"] for e in events).most_common():
        log(f"    {k:42s} {v:5,}")

    noquote = [e for e in events if not e["quote"]]
    if noquote:
        log(f"  !! {len(noquote)} events with no quote - PRIME DIRECTIVE breach")
        raise SystemExit(1)

    log("\n--- F. outputs ----------------------------------------------------")
    write_csv(CLEAN / "federal_recognition_roster.csv", roster,
              list(roster[0].keys()))
    write_csv(CLEAN / "federal_recognition_events.csv", events,
              list(events[0].keys()))
    props, dropped = propose_aliases(roster, spine, m)
    write_csv(REVIEW / "recognition_alias_proposals.csv", props,
              list(props[0].keys()))
    log(f"  historical names NEW to the spine: {len(props):,} "
        f"over {len({p['tribe_id'] for p in props}):,} entities")
    log(f"  loose matches dropped on a leading-word mismatch: {len(dropped):,}")
    if dropped:
        write_csv(REVIEW / "recognition_alias_dropped.csv", dropped,
                  list(dropped[0].keys()))
        for d in dropped[:6]:
            log(f"    {d['proposed_alias'][:52]:52s} -/-> "
                f"{d['resolved_to_canonical_name'][:28]}")
    for k, v in Counter(p["resolve_confidence"] for p in props).most_common():
        log(f"    resolve_confidence {k:7s} {v:5,}")
    log(f"    first seen before 2012 (the pre-restyle names that make old "
        f"contracting rows resolve): "
        f"{sum(1 for p in props if p['first_seen_publication_date'] < '2012'):,}")

    write_log_doc(recon, roster, events, props, per_notice, missing,
                  unparsed, notices, keys, bridges, GLUE_LOG, dropped)
    log("\ndone.")
    _logfh.close()


def write_log_doc(recon, roster, events, props, per_notice, missing, unparsed,
                  notices, keys, bridges, glue_log, dropped):
    """Everything below is recomputed from the data on every run (rule 10)."""
    et = Counter(e["event_type"] for e in events)
    mech = Counter(e["mechanism"] or "(not stated in the record)" for e in events)
    qb = Counter(e["quote_basis"] for e in events)
    years = sorted({n["publication_date"][:4] for n in per_notice.values()})
    gaps = [str(y) for y in range(1994, 2027) if str(y) not in years]
    flagged = [e for e in events if e.get("review_flag")]
    with_pl = [e for e in events if e["public_law_cited"]]
    with_stat = [e for e in events if e["statute_named"]]
    with_bill = [e for e in events if e["bill_ids"]]
    renames = [e for e in events if e["event_type"] == "RENAMED"]
    marked = [e for e in renames
              if e["mechanism_basis"] == "notice_marks_previously_listed_as"]
    keyed = sum(1 for e in events if e["tribe_id"])

    L = []
    A = L.append
    A("# Federal recognition history — build log")
    A("")
    A(f"*`code/76_build_recognition_history.py`, run {TODAY}. Every number here "
      "is recomputed from the data on each run; none is hand-edited "
      "(standing rule 10).*")
    A("")
    A("## What this is")
    A("")
    A("The BIA has been required to publish the list of federally recognized "
      "tribes annually since the Federally Recognized Indian Tribe List Act of "
      "1994 (Pub. L. 103-454). Each notice is a snapshot; the difference "
      "between consecutive snapshots is an event. Two files come out of that:")
    A("")
    A(f"- `data/clean/federal_recognition_roster.csv` — {len(roster):,} rows, "
      f"one per listed entry per notice, {min(years)}–{max(years)}.")
    A(f"- `data/clean/federal_recognition_events.csv` — {len(events):,} events, "
      f"{keyed:,} of them carrying a spine `tribe_id`.")
    A("")
    A("## Which notices were retrievable")
    A("")
    A("Source: Federal Register API v1 (`federalregister.gov/api/v1/"
      "documents.json`) — free, GET, no key. A full-text search for "
      "`\"Indian Entities Recognized\"` returns every document that *mentions* "
      "the list; selection is on the **title**, because a document that cites "
      "the list is not the list. Accepted and rejected candidates are both in "
      "`data/raw/external/fr_recognized/_notice_manifest.csv`.")
    A("")
    A(f"- **{len(notices)} documents selected by title**, "
      f"**{len(per_notice)} of them full rosters**, {min(years)}–{max(years)}.")
    A("- **" + str(len(unparsed)) + " selected documents are not rosters**: `"
      + "`, `".join(unparsed) + "`. One is the 2010 supplement adding the "
      "Shinnecock Indian Nation, one the 2021 correction of three names. Both "
      "carry real events and are parsed for them separately.")
    if missing:
        A("- **Not retrievable**: " + ", ".join(f"`{d}` ({w})" for d, w in missing))
    else:
        A("- **Nothing was unretrievable.** Every selected notice returned its "
          "raw text on the first request.")
    A("")
    A("### Calendar years with no annual notice")
    A("")
    A("The List Act says annually; in practice the BIA has missed years and "
      "doubled up in others. Years in 1994–2026 with no notice: "
      + ", ".join(gaps) + ".")
    A("")
    A("Two of those absences are findings rather than gaps in this build:")
    A("")
    A("- **1994.** The previous list was published 1993-10-21 (58 FR 54364), "
      "before the Federal Register API's 1994 floor. The 1995 notice says so "
      "itself: *\"The list is updated from the last such list published "
      "October 21, 1993 (58 FR 54364)\"*. The window therefore opens at "
      "1995-02-16 and no pre-1995 diff is possible from this source.")
    A("- **2025.** No annual list was published in calendar 2025. The "
      "2024-12-11 notice (89 FR 99899) governs through 2025 and the next is "
      "2026-01-30 (91 FR 4102). A BIA-agency search across 2025 returns no "
      "list document — the absence was checked, not assumed.")
    A("")
    A("## Method")
    A("")
    A("### De-wrapping the GPO text")
    A("")
    A("1. A wrapped line ends with a trailing space; a complete entry does not.")
    A("2. A line that leaves a bracket **open** is also a wrap. GPO breaks at a "
      "hyphen (`Alabama-` / `Coushatta Tribes of Texas]`) and once mid-phrase "
      "(`... St. Regis Band of Mohawk Indians` / `of New York)`); rule 1 alone "
      "splits those into phantom tribes.")
    A("3. Rule 2 **backs out** if four further lines do not close the bracket. "
      "The 2014 notice contains an unclosed paren in the source — "
      "`Northwestern Band of Shoshoni Nation of Utah (Washakie` — and an "
      "unbounded rule 2 swallowed the remaining 90 tribes into one "
      "6,016-character row.")
    A("4. `[[Page NNNN]]` markers are removed **with the blank lines around "
      "them**. Inline, the marker appends a trailing space and makes a complete "
      "entry look wrapped. Standalone, it arrives as blank/marker/blank dropped "
      "into the middle of an entry — that is how the 2003 notice splits the "
      "Sisseton-Wahpeton Oyate's former name into a phantom "
      "`Sioux Tribe of the Lake Traverse Reservation)`.")
    A("")
    A("### Four meanings of a parenthesis, kept apart")
    A("")
    A("| Form | Meaning | Treatment |")
    A("|---|---|---|")
    A("| `(previously listed as X)`, `[previously listed as X]`, `(formerly X)` "
      "| RENAME | X becomes an alias of the same entity |")
    A("| `(See Y)` | CROSS-REFERENCE | a listed tribe whose affairs Y conducts; "
      "recorded in `see_instead` and **never merged into Y** |")
    A("| `(See Supplementary Information ...)` | pointer to the preamble | **not** "
      "a cross-reference — the 2026 Lumbee entry uses one, and a naive `(See` "
      "rule turns the most important event in the dataset into a pointer |")
    A("| `(A; B)`, or a trailing colon with indented lines | CONSTITUENT parts "
      "| recorded in `constituents` / `parent_fr_name`, excluded from counts |")
    A("")
    A("`(aka X)` is stripped into `also_known_as`: it is an alias, not part of "
      "the name, and leaving it attached makes "
      "`Native Village of Chenega (aka Chanega)` and `Native Village of "
      "Chenega` look like two tribes across the 2026 notice.")
    A("")
    A("### Entity identity across notices")
    A("")
    A("A name-level diff is meaningless here — the 2012 notice alone restyles "
      "about a hundred entries, and diffing raw names reports ~100 additions "
      "and ~98 removals for that year alone. Identity is union-find over four "
      "signals, in descending authority:")
    A("")
    A("1. the notice's own `previously listed as` — the BIA saying these are "
      "one nation. The declared old name is **fuzzy-matched to the name "
      "actually listed in an earlier notice**, because the BIA writes it from "
      "memory: 1998 says *\"(formerly the Coast Indian Community of Yurok "
      "Indians of the Resighini Rancheria)\"* while the 1997 list reads "
      "`... Resighini Rancheria, California`.")
    A("2. a shared spine `tribe_id`, **but only from `exact` and `alias` "
      "resolution**. `containment` is good enough to attribute a contract and "
      "far too loose to assert that two listings are one nation: measured on "
      "this corpus it sent *Alturas Indian Rancheria of Pit River Indians of "
      "California* to the **Pit River Tribe**, *Cherokee Nation, Oklahoma* to "
      "the **United Keetoowah Band**, and *Jena Band of Choctaw Indians, "
      "Louisiana* to a **state-recognized** Louisiana Choctaw band. Each merge "
      "then *masks* a real event.")
    A("3. normalised name equality (`St.` expanded to `Saint`).")
    A("4. a bridging pass over what is left, described next.")
    A("")
    A(f"Result: **{len(keys):,} distinct entities** across the window.")
    A("")
    A("Entity resolution itself is `resolve_entity` from "
      "`code/33_apply_party_rulings.py`. No matching logic is re-implemented "
      "here (standing rule 8).")
    A("")
    A(f"### The bridging pass — {len(bridges)} unmarked renames")
    A("")
    A("Only names left over after exact and declared-rename matching, only "
      "between **consecutive** notices, only one-to-one, best pair first. Two "
      "rules:")
    A("")
    A("- **typographic_variant** — difflib ratio >= 0.90. The notices carry real "
      "drift: `Qawalingin`/`Qawalangin`, `San Manual`/`San Manuel`, "
      "`Sokoagon`/`Sokaogon`, `Chuatbaluk`/`Chuathbaluk`, "
      "`Muskogee`/`Muscogee`, `Artic Village`/`Arctic Village`. Each pair is "
      "one nation; publishing it as a removal plus an addition would assert "
      "that a tribe lost and regained federal recognition.")
    A("- **bia_shortened_the_listed_name** — the shorter name's identifying "
      "tokens are all inside the longer's, they are at least half of the "
      "longer's, **and both names lead with the same identifying word**. The "
      "leading-word test is load-bearing: `core` is a set and discards word "
      "order, and without it the rule paired the Wichita and Affiliated Tribes "
      "with the White Mountain Apache Tribe, the Potter Valley Rancheria with "
      "the Port Gamble Indian Community, and the Muscogee (Creek) Nation with "
      "the Muckleshoot Indian Tribe.")
    A("")
    A("It refuses `Chickahominy Indian Tribe` against `Chickahominy Indian "
      "Tribe--Eastern Division` — two different tribes, both recognised in "
      "2018 by the same Act.")
    A("")
    A("| rule | n |")
    A("|---|---:|")
    for k, v in Counter(b["rule"] for b in bridges).most_common():
        A(f"| {k} | {v} |")
    A("")
    A(f"### Source lines carrying two tribes — {len(glue_log)} repaired")
    A("")
    A("Some entries arrive with the separator lost. The 2015 notice prints "
      "`Eklutna Native VillageEmmonak Village` as one line; the 2018 notice "
      "runs `... Rancheria of California) Tejon Indian Tribe` together. Left "
      "alone, both tribes vanish from that year and the dataset publishes them "
      "as removed from federal recognition and then restored.")
    A("")
    A("The split fires only where **both halves are names other notices "
      "carry** (a real listing recurs; a glue artefact appears once), the left "
      "half has balanced brackets, and both halves are at least 12 characters. "
      "The original string is kept in `entry_raw_source` on both rows.")
    A("")
    for orig, a, b in glue_log:
        A(f"- `{orig[:96]}` -> `{a[:44]}` + `{b[:44]}`")
    A("")
    A("## Parsed count vs the count each notice states about itself")
    A("")
    A("Every notice declares its own total in the SUMMARY, and the 2022 notice "
      "also prints bracketed per-section counts. That is a free, independent "
      "check on the parse — reported here, not reconciled away.")
    A("")
    A("| document | published | parsed listed | notice states | diff |")
    A("|---|---|---:|---:|---:|")
    for dn, n, d in recon:
        A(f"| `{dn}` | {n['publication_date']} | {n['parsed_listed']} | "
          f"{n['stated_total'] if n['stated_total'] else '—'} | "
          f"{d if d is not None else '—'} |")
    A("")
    A("**Reading the residuals.** The 2022 notice is the only one that prints "
      "its own per-section counts, `[347 ...]` and `[227 ...]`; the parse "
      "reproduces both exactly, and 347 + 227 = 574 is its stated total. "
      "Elsewhere the parse runs **+2**, and the +2 has a name: the Native "
      "Village of Venetie Tribal Government and the Pribilof Islands Aleut "
      "Communities, which the BIA excludes from its own count. The 2022 and "
      "2023-01 notices say so explicitly, in a *Clarification* section reading "
      "*\"is not included in the official count of 574 federally recognized "
      "Indian Tribes but is recognized as an entity authorized to act on "
      "behalf of ...\"* — and those are exactly the two years the residual is 0, "
      "because there the two sit in that section rather than in the lists.")
    A("")
    A("The 2015 notice is +3. Its extra row is real and is the BIA's: that "
      "notice lists **both** `Native Village of Old Harbor (previously listed "
      "as Village of Old Harbor)` **and** `Village of Old Harbor`, having left "
      "the superseded entry in place.")
    A("")
    A("## Events")
    A("")
    A("| event type | n |")
    A("|---|---:|")
    for k, v in et.most_common():
        A(f"| {k} | {v:,} |")
    A("")
    A(f"Of the {len(renames):,} renames, **{len(marked):,} are marked by the "
      "notice itself** with `previously listed as` / `formerly`; the rest are "
      "unmarked changes bridged by the pass above, each carrying its rule and "
      "score in `mechanism_basis`.")
    A("")
    A("**A removal is not a termination.** Removals are as often a merge into "
      "another listing, an unmarked rename, or a correction. `mechanism` stays "
      "blank and `mechanism_basis` reads `not_stated_in_record; a removal is "
      "not evidence of termination` unless a Federal Register document says "
      "otherwise. The one removal in this window with a stated legal reason is "
      "the **Delaware Tribe of Indians**, removed in the 2005-11-25 notice "
      "*\"in response to a final judgment and order sought by the Cherokee "
      "Nation of Oklahoma in the United States District Court\"* and restored "
      "in 2009 after reorganising under the Oklahoma Indian Welfare Act.")
    A("")
    A(f"`review_flag = possible_unmarked_rename` is set on **{len(flagged)}** "
      "ADDED/REMOVED rows that have a same-notice look-alike above 0.60 "
      "similarity but did not clear the bridging bar — `Narragansett Indian "
      "Tribe of Rhode Island` -> `Narragansett Indian Tribe` is the shape. They "
      "are flagged, not asserted; `possible_rename_counterpart` names the "
      "other row.")
    A("")
    A("### Mechanism, where the record states one")
    A("")
    A("| mechanism | n |")
    A("|---|---:|")
    for k, v in mech.most_common():
        A(f"| {k} | {v:,} |")
    A("")
    A("The mechanism is read from the **quote** first and only then from the "
      "sentences around it, and `mechanism_basis` says which. Reading the "
      "window first put `administrative_reaffirmation` on the Cowlitz Indian "
      "Tribe because the *next* sentence reaffirms three Alaska tribes; "
      "Cowlitz's own sentence says it *\"was acknowledged under 25 CFR part "
      "83.\"*")
    A("")
    A("### Where each quote comes from")
    A("")
    A("Every event carries a verbatim quote and a `quote_basis` naming the "
      "document it was taken from, so a quote can never be mistaken for an "
      "inference. `quote_context` holds the surrounding sentences when the "
      "quote came from a notice preamble.")
    A("")
    A("| quote_basis | n |")
    A("|---|---:|")
    for k, v in qb.most_common():
        A(f"| {k} | {v:,} |")
    A("")
    A("## Recognition tied to legislation")
    A("")
    A("Three links, descending in certainty, never mixed:")
    A("")
    A(f"- **`public_law_cited`** — {len(with_pl)} events carry a public law "
      "number taken from the Federal Register text that evidences that event.")
    A(f"- **`statute_named`** — {len(with_stat)} carry the Act's title exactly "
      "as the notice writes it, for the statutes the BIA names without a "
      "number.")
    A(f"- **`bill_ids`** — {len(with_bill)} join to `data/clean/native_bills.csv`. "
      "`bill_link_basis` distinguishes "
      "`enacted_public_law_number_matches_native_bills_latest_action` (the "
      "bill became that law) from `bill_title_names_the_tribe_and_recognition` "
      "(a recognition bill for that tribe, introduced within 12 years before "
      "the listing — **explicitly not evidence that it caused the listing**). "
      "The window matters: without it the Samish Indian Tribe's 1996 "
      "acknowledgment was linked to House bills from 2019, 2021 and 2023.")
    A("")
    A("`native_bills.csv` and `bill_votes.csv` are **read, never written** — a "
      "bills-and-votes agent owns them. The join key is written onto our rows.")
    A("")
    A("### The worked example")
    A("")
    lum = next((e for e in events if "Lumbee" in e["entity_name"]), None)
    if lum:
        A(f"**{lum['entity_name']}**, {lum['event_type']} "
          f"{lum['effective_date']}, {lum['fr_citation']}:")
        A("")
        A(f"> {lum['quote']}")
        A("")
        A(f"`mechanism` = `{lum['mechanism']}` · "
          f"`public_law_cited` = `{lum['public_law_cited']}` · "
          f"`statute_named` = `{lum['statute_named']}` · "
          f"`bill_ids` = `{lum['bill_ids']}`")
        A("")
        A("The public law number sits one sentence past the quote — *\"See "
          "Public Law 119-60, section 8803.\"* — with the hyphen carrying a "
          "line break, so the citation reads `119- 60` in the raw text. That "
          "is why the statute pattern tolerates whitespace around the dash.")
    A("")
    A("## Historical names for the spine")
    A("")
    A(f"`review/recognition_alias_proposals.csv` — **{len(props):,} names** "
      f"across **{len({p['tribe_id'] for p in props}):,} entities** that appear "
      "in a Federal Register recognition notice and are not already in the "
      "spine's `canonical_name`, `aliases` or `fr_official_name`. Each row "
      "carries the FR document, its citation, its publication date and the "
      "verbatim entry the name came from, plus an empty `YOUR_RULING` column.")
    A("")
    A("**This is the product benefit Elijah named.** A tribe listed in 2005 "
      "under one name and renamed in 2015 appears in the contracting and "
      "funding rows of that era under the old name. Feeding these names into "
      "`aliases` is what makes those rows resolve.")
    A("")
    A("Each row carries `resolve_confidence`: **high** where the FR name "
      "resolved to the spine exactly or through an existing alias, **medium** "
      "on identifying-token equality, **low** on containment. The file sorts "
      "high first.")
    A("")
    A(f"**{len(dropped)} candidate aliases were dropped, not proposed**, and "
      "are in `review/recognition_alias_dropped.csv` with their reason. Each "
      "is a containment match whose leading identifying word differs from the "
      "spine entity it landed on, and the three worst show why the guard "
      "exists: *Cherokee Nation of Oklahoma* resolved to the **United "
      "Keetoowah Band**, *Alturas Indian Rancheria of Pit River Indians of "
      "California* to the **Pit River Tribe**, and *Hoopa Valley Tribe of the "
      "Hoopa Valley Reservation, California* to the **California Valley Miwok "
      "Tribe**. Merging any of those would send one nation's entire "
      "1990s-2000s contracting history to another. The guard also drops a few "
      "correct ones — *Covelo Indian Community* really is the Round Valley "
      "Indian Tribes' former name — which is why they are written out for a "
      "ruling instead of discarded.")
    A("")
    A("The file is a **proposal, not an edit**. Four agents are concurrently "
      "adding `TCU-`, `CDFI-`, `BIE-` and `UIO-` entities to "
      "`data/spine/cedar_entity_spine.csv`; this script never opens it for "
      "writing.")
    A("")
    A("## Scope")
    A("")
    A("State-recognized tribes are not on this federal roster and their absence "
      "from it is not evidence of anything. Cedar Press carries 64 of them "
      "from the CICD roster under `TRBS-`. One of them, a Louisiana Choctaw "
      "band, is also the entity a loose containment match confused with the "
      "federally recognized Jena Band — which is why `TRBS-` rows can never "
      "supply identity in this build.")
    A("")
    p = DOCS / "RECOGNITION_HISTORY_LOG.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(L) + "\n", encoding="utf-8")
    log(f"  wrote {p.relative_to(CEDAR)}")


if __name__ == "__main__":
    main()
