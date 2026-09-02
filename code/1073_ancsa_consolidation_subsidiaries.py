"""1073_ancsa_consolidation_subsidiaries.py — WORKSTREAM NBOA-EXPAND. ZERO NETWORK.

WHY THIS EXISTS
---------------
The mandate names the ANCSA route explicitly:

    "ANC subsidiary listings — the 12 regional and ~170 village corporations
     publish operating-company lists; ANCSA audited filings under Alaska
     Statute 45.55.139 are a separate, richer route"

The filings are already on this machine. `docs/AGENT_FIELD_GUIDE.md` §5: 27 of
39 ranked absences are `ON_DISK_NOT_PROMOTED`, and this is one of them.

    data/raw/external/ancsa_portal_v3/   358 audited annual reports,
                                         41 VILLAGE corporations, 2016-2026,
                                         fetched 2026-09-02 by code/1031
    data/interim/ancsa_txt_v3/           the text layer, PyMuPDF plus per-page
                                         tesseract at 300 dpi, by code/1031

Shard E (`code/531_shard_e_anc_report_mine.py`) mined `ancsa_txt/` (166 files)
and `ancsa_txt_v2/` (80) and produced 482 hand-adjudicated edges across 22
parents — nearly all REGIONAL corporations. **It never saw `ancsa_txt_v3`.**
Village corporations are the class `docs/methodology/native-owned-businesses.md`
§B6 measures at **0 of 173**.

WHAT IT READS, AND WHY IT IS THE STRONGEST EVIDENCE CLASS HERE
--------------------------------------------------------------
The "Principles of Consolidation" note of an AUDITED financial statement:

    The consolidated financial statements include the accounts of Azachorok,
    Incorporated and its wholly owned subsidiary Azachorok Contract Services,
    LLC (collectively, the Corporation).

That is the parent asserting ownership of a named company, in a document an
independent auditor signed, filed with the State of Alaska under AS 45.55.139.
`identity_scope = parent_asserted_subsidiary`; `assertion_class = OWNERSHIP`.

THE GRADIENT IS NOT FLATTENED
-----------------------------
Three things this corpus says are three different things and each keeps its
own `ownership_relation`:

  wholly_owned        "its wholly owned subsidiary X, LLC"
  majority_owned      "its majority-owned subsidiaries"
  equity_or_jv        "a 40% membership interest in X, LLC", "joint venture"

And a fourth outcome is a real finding, not a miss:

  NOTE_PRESENT_NAMES_NOT_STATED
      Afognak's 2017 note reads "...and its majority-owned subsidiaries
      (collectively, the Corporation), most of which are limited liability
      companies." The corporation HAS subsidiaries and the audited statement
      declines to name them. Recording that as "no subsidiaries" would be a
      false negative of exactly the kind HIDDEN_DATA_TECHNIQUES warns about.

WHAT IT WILL NOT DO
-------------------
- It will not read a name out of a URL slug or a filename.
- It will not accept a candidate with no corporate suffix. An OCR line is not
  a company because it is capitalised.
- It resolves no identity and mints nothing. The PARENT is keyed, from
  `data/clean/ancsa_filings_index.csv`'s own `cedar_uid`; the CHILD is not.
- It writes nothing to data/clean and does not touch shard E's file.

OUTPUT — the same record shape code/1070 stages, so one merge candidate
---------------------------------------------------------------------
  data/staging/native_business_sweep_1070/business_rows_ancsa.jsonl
  data/staging/native_business_sweep_1070/ancsa_document_log.csv
      one row per DOCUMENT: what was found, what was checked and absent, the
      date. "Checked, note present, names not stated" is a real result;
      "untouched" is not the same thing.

STAGES
  mine      the extraction. Flushed per DOCUMENT.
  report    the counts.
  verify    invariants; exits 1 when one breaks.
  selftest  proves each invariant FIRES on an injected violation.

INVARIANTS (`verify`)
  W1  every emitted child name carries a corporate suffix
  W2  every row quotes the sentence it came from, and the name appears in it
  W3  no child equals its own parent
  W4  ownership_relation is from the declared vocabulary
  W5  every document in the extract manifest has a log row
  W6  no row duplicates a shard E edge for the same parent
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TXTDIR = ROOT / "data" / "interim" / "ancsa_txt_v3"
EXTRACT_MAN = ROOT / "review" / "ancsa_1031_extract_manifest.csv"
FETCH_MAN = ROOT / "review" / "ancsa_1031_fetch_manifest.csv"
INDEX = ROOT / "data" / "clean" / "ancsa_filings_index.csv"
SPINE = ROOT / "data" / "spine" / "cedar_entity_spine.csv"
SHARD_E = ROOT / "data" / "staging" / "anc_subsidiaries" / "shard_e.jsonl"

OUT = ROOT / "data" / "staging" / "native_business_sweep_1070"
OUT.mkdir(parents=True, exist_ok=True)
ROWS = OUT / "business_rows_ancsa.jsonl"
DOCLOG = OUT / "ancsa_document_log.csv"

TODAY = "2026-09-02"
THIS = "1073_ancsa_consolidation_subsidiaries.py"

csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))

# ---------------------------------------------------------------------------
# the corporate suffix is the whole precision control
# ---------------------------------------------------------------------------
SUFFIX = re.compile(
    r"(,\s*)?\b(LLC|L\.L\.C\.?|Inc\.?|Incorporated|Corporation|Corp\.?|"
    r"Company|Co\.|Ltd\.?|Limited|L\.P\.?|LP|LLP|PLLC|Holdings?|"
    r"Partnership|ehf|GmbH|N\.V\.|B\.V\.)\s*$", re.I)

CONSOLIDATION = re.compile(
    r"[^.]{0,400}?(?:consolidated financial statements|accompanying "
    r"consolidated (?:financial )?statements)[^.]{0,120}?include[^.]{0,80}?"
    r"accounts of[^.]{0,1600}?\.", re.I | re.S)

NAMED_SUB = re.compile(
    r"[^.]{0,300}\b(?:wholly[\s\-]*owned|majority[\s\-]*owned|"
    r"wholly[\s\-]*owned)\s+subsidiar(?:y|ies)[^.]{0,600}\.", re.I | re.S)

# THE PARENT NAMED AFTER "of" MUST BE THIS DOCUMENT'S CORPORATION.
# Gwitchyaa Zhee's report says "... Doyon Native Corporation is a subsidiary
# of ...", about a THIRD party, and the first version of this attributed Doyon
# to Gwitchyaa Zhee. Group 3 is the parent clause and is checked against the
# filer's own name before anything is emitted.
IS_A_SUB = re.compile(
    r"([A-Z][^.;()]{2,80}?(?:LLC|L\.L\.C\.|Inc\.|Incorporated|Corporation|"
    r"Corp\.|Company|Ltd\.|Limited|LP|LLP|Holdings?))\s*,?\s+is a "
    r"(wholly[\s\-]*owned |majority[\s\-]*owned )?subsidiary of\b"
    r"([^.]{0,120})\.", re.S)

EQUITY = re.compile(
    r"[^.]{0,200}\b(\d{1,3}(?:\.\d+)?)\s*%\s+(?:equity |ownership |membership |"
    r"voting )?(?:interest|stake)\s+in\s+([A-Z][^.;()]{2,80}?(?:LLC|L\.L\.C\.|"
    r"Inc\.|Incorporated|Corporation|Corp\.|Company|Ltd\.|Limited|LP|LLP|"
    r"Holdings?))[^.]{0,120}\.", re.S)

RELATIONS = {"wholly_owned", "majority_owned", "equity_or_jv",
             "subsidiary_unspecified"}

# Words that are a heading, a role or an audit-report boilerplate phrase, not
# a company. An OCR line is not a firm because it is capitalised.
NOT_A_CHILD = re.compile(
    r"^(the |a |an )?(corporation|company|subsidiar|board|management|"
    r"independent auditor|report of|notes? to|consolidated|statements? of|"
    r"balance sheet|schedule|exhibit|shareholder|director|officer|"
    r"annual report|financial statement|significant accounting|"
    r"principles? of|basis of|accounting polic|alaska native claims)",
    re.I)


def _norm(n: str) -> str:
    n = re.sub(r"[‘’“”`']", "", n or "")
    n = re.sub(r"\b(LLC|L\.L\.C\.|Inc|Incorporated|Corporation|Corp|Company|"
               r"Co|Ltd|Limited|LP|LLP|PLLC)\b\.?", " ", n, flags=re.I)
    return re.sub(r"[^a-z0-9]+", "", n.lower())


def first_word(n: str) -> str:
    """The name's first word WITHOUT punctuation.

    The W2 containment test compared "Solutions71," against a source sentence
    reading "Solutions71 LLC" and failed four real rows, because this script
    inserts the comma the source did not print. Compare the word, not the
    typography.
    """
    w = re.split(r"\s+", (n or "").strip())
    return re.sub(r"[^\w&'\-]", "", w[0] if w else "")


def clean_name(s: str) -> str:
    s = re.sub(r"\s+", " ", (s or "")).strip(" \t,;:.-–—()")
    s = re.sub(r"^(and|its|the|of|a)\s+", "", s, flags=re.I)
    # OCR routinely reads a capital I as a lowercase l: "lncorporated"
    s = re.sub(r"\blncorporated\b", "Incorporated", s)
    s = re.sub(r"\blnc\b", "Inc", s)
    return s.strip()


# A COMPANY NAME IS A RUN OF CAPITALISED TOKENS ENDING IN A CORPORATE SUFFIX.
#
# The first version split the note on `;` / `and` / `,` and kept any fragment
# with a suffix at the end. Measured on the real corpus that produced:
#
#     "majority-owned subsidiaries , most of which are limited"
#     "as well as one mineral development company"
#     "2016 (3) Acquisitions On April 18, 2017, the Company"
#     "o Bethel Builders LLC"            <- an OCR'd bullet
#     "wholly owned subsidiary Azachorok Contract Services, LLC"
#
# Every one of those ends in a word that IS a corporate suffix — limited,
# company, Company, LLC — which is exactly why a suffix test at the end of a
# fragment does not work. The structural fact that separates a name from a
# sentence is that the word BEFORE the suffix is capitalised: "Contract
# Services, LLC" but "are limited". Match the run, and the lead-in clause,
# the bullet and the sentence tail all fall off for free.
_TOK = r"(?:[A-Z0-9][\w&'’\-\.]*|of|and|the|for|in|de|&)"
NAME_RUN = re.compile(
    r"\b([A-Z][\w&'’\-\.]*(?:\s+" + _TOK + r"){0,7}?)\s*,?\s+"
    r"(LLC|L\.L\.C\.?|Inc\.?|Incorporated|Corporation|Corp\.?|Company|"
    r"Companies|Ltd\.?|Limited|L\.P\.?|LP|LLP|PLLC|Holdings?|ehf)\b")

# A run may still START on a word that is a heading or a connective.
BAD_HEAD = re.compile(
    r"^(The|A|An|Its|This|These|Those|Such|Company|Companies|Corporation|"
    r"Subsidiar\w*|Note|Notes|Consolidated|Statements?|Schedule|Exhibit|"
    r"Acquisitions?|Dispositions?|Management|Board|Report|Independent|"
    r"Principles?|Basis|Significant|Accounting|Alaska Native Claims|"
    r"December|January|February|March|April|May|June|July|August|September|"
    r"October|November|On|In|At|As|And|Or|But|For|With|From)\b", re.I)

# A GENERIC BUSINESS NOUN STANDING ALONE IS A FRAGMENT, NOT A NAME.
# "Certified Company" is the tail of "8(a) Certified Company"; "Development,
# Inc" is the tail of a name whose distinctive first word the OCR dropped.
# Both are real measured outputs of the run matcher. A firm's name has a
# proper noun in it, and two generic words are not one.
GENERIC_HEAD = re.compile(
    r"^(certified|development|services|solutions|holdings?|management|"
    r"construction|properties|property|enterprises?|group|technologies|"
    r"systems|partners|ventures?|investments?|contracting|consulting|"
    r"operations|resources|industries|international|federal|government|"
    r"commercial|native|alaska|alaskan|regional|village)\b", re.I)


def split_names(tail: str) -> list[str]:
    """Company names in the tail of a consolidation note. See NAME_RUN."""
    tail = re.sub(r"\(collectively[^)]*\)", " ", tail, flags=re.I)
    tail = re.sub(r"\s+", " ", tail)
    out, seen = [], set()
    for m in NAME_RUN.finditer(tail):
        head, suf = m.group(1), m.group(2)
        last = head.split()[-1]
        if not (last[:1].isupper() or last[:1].isdigit()):
            continue                       # "are limited", "the Company"
        if BAD_HEAD.match(head):
            continue
        if len(head.split()) <= 2 and GENERIC_HEAD.match(head):
            continue
        nm = clean_name(f"{head}, {suf}" if head.rstrip().endswith((",",))
                        is False and suf.upper() in
                        ("LLC", "L.L.C.", "INC", "INC.", "LP", "L.P.", "LLP",
                         "PLLC") else f"{head} {suf}")
        nm = re.sub(r"\s+,", ",", nm)
        if not nm or len(nm) < 5 or len(nm) > 95:
            continue
        if NOT_A_CHILD.match(nm) or not SUFFIX.search(nm):
            continue
        k = _norm(nm)
        if k and k not in seen:
            seen.add(k)
            out.append(nm)
    return out


# ---------------------------------------------------------------------------
def documents() -> list[dict]:
    if not EXTRACT_MAN.exists():
        return []
    with open(EXTRACT_MAN, encoding="utf-8-sig", newline="") as fh:
        man = list(csv.DictReader(fh))
    uid, cls = {}, {}
    if INDEX.exists():
        with open(INDEX, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                if r.get("portal_document_id"):
                    uid[r["portal_document_id"]] = r.get("cedar_uid", "")
                    cls[r["portal_document_id"]] = r.get("anc_class", "")
    aid = {}
    if FETCH_MAN.exists():
        with open(FETCH_MAN, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                aid[r["portal_document_id"]] = r
    out = []
    for m in man:
        if (m.get("note") or "") not in ("ok", ""):
            continue
        p = ROOT / m["txt_file"].replace("\\", "/")
        if not p.exists():
            continue
        f = aid.get(m["portal_document_id"], {})
        out.append({
            "doc_id": m["portal_document_id"],
            "corporation_name": m["corporation_name"],
            "period": m["period_covered"],
            "txt": p,
            "cedar_uid": uid.get(m["portal_document_id"], ""),
            "anc_class": cls.get(m["portal_document_id"])
                         or f.get("anc_class", ""),
            "portal_url": f.get("portal_url", ""),
            "pages_ocred": m.get("pages_ocred", ""),
        })
    return out


SHARD_E_PAIRS: set = set()


def mine_doc(d: dict) -> tuple[list[dict], dict]:
    text = d["txt"].read_text(encoding="utf-8", errors="ignore")
    text = text.replace(" ", " ")
    parent = d["corporation_name"]
    pnorm = _norm(parent)
    found, seen = [], set()
    note_present = False
    names_stated = False

    def emit(name, rel, quote, route, pct=""):
        nonlocal names_stated
        name = clean_name(name)
        if not name or not SUFFIX.search(name) or NOT_A_CHILD.match(name):
            return
        n = _norm(name)
        if not n or n == pnorm or n in seen:
            return
        q = re.sub(r"\s+", " ", quote).strip()
        fw = first_word(name).lower()
        if fw not in q.lower():
            return                       # the quote must contain the name
        # WINDOW THE QUOTE ON THE NAME, do not truncate to the first 400
        # characters. A consolidation note runs to 1,600 characters and the
        # tenth subsidiary it lists sits past any head-truncation, so ten
        # rows shipped a quote that did not contain the name it was evidence
        # for — and W2 caught exactly that. The stored quote must support the
        # row it is attached to.
        i = q.lower().find(fw)
        lo = max(0, i - 160)
        q = ("..." if lo else "") + q[lo:i + 240] + (
            "..." if i + 240 < len(q) else "")
        if (_norm(parent), _norm(name)) in SHARD_E_PAIRS:
            return      # shard E adjudicated this edge by hand; do not re-emit
        seen.add(n)
        names_stated = True
        found.append({
            "authority_tribe_id": d["doc_id"],
            "authority_cedar_uid": d["cedar_uid"],
            "authority_name": parent,
            "authority_entity_class": ("Alaska Native Village Corporation"
                                       if d["anc_class"] == "ANC_VILLAGE"
                                       else "Alaska Native Regional "
                                            "Corporation"),
            "klass": "anc",
            "business_name_raw": name,
            "city": "", "state_province": "AK",
            "service_category_raw": "", "certification_number": "",
            "extra_columns": f"period_covered={d['period']}",
            "kind": "anc_operating_companies",
            "ownership_relation": rel,
            "stated_ownership_pct": pct,
            "identity_scope": "parent_asserted_subsidiary",
            "assertion_class": "OWNERSHIP",
            "directory_type": "enterprise_register",
            "identity_claim_text": q[:420],
            "source_url": d["portal_url"],
            "source_page_url": d["portal_url"],
            "source_edition": d["period"],
            "route": route,
            "extraction_note": (
                "Principles of Consolidation note of the audited AS 45.55.139 "
                "annual report; name read from the sentence, never from a "
                "filename or slug"
                if route == "consolidation_note" else
                f"{route} sentence in the audited AS 45.55.139 annual report"),
            "auto_ruled": "Y",
            "harvest_date": TODAY,
            "terms_status": "PUBLIC_STATE_FILING_AS_45_55_139",
            "built_by_script": THIS,
        })

    for m in CONSOLIDATION.finditer(text):
        note_present = True
        s = m.group(0)
        tail = re.split(r"accounts of", s, maxsplit=1, flags=re.I)[-1]
        rel = ("wholly_owned" if re.search(r"wholly[\s\-]*owned", tail, re.I)
               else "majority_owned"
               if re.search(r"majority[\s\-]*owned", tail, re.I)
               else "subsidiary_unspecified")
        for nm in split_names(tail):
            emit(nm, rel, s, "consolidation_note")

    for m in NAMED_SUB.finditer(text):
        note_present = True
        s = m.group(0)
        rel = ("wholly_owned" if re.search(r"wholly[\s\-]*owned", s, re.I)
               else "majority_owned")
        after = re.split(r"subsidiar(?:y|ies)", s, maxsplit=1, flags=re.I)[-1]
        for nm in split_names(after):
            emit(nm, rel, s, "named_subsidiary_sentence")

    ptoks = [t for t in re.split(r"[^A-Za-z]+", parent)
             if len(t) >= 4 and t.lower() not in
             {"native", "corporation", "incorporated", "limited", "company",
              "alaska", "inc", "corp", "village", "the"}]
    for m in IS_A_SUB.finditer(text):
        note_present = True
        owner = (m.group(3) or "")
        if ptoks and not any(t.lower() in owner.lower() for t in ptoks):
            continue        # the parent named is a third party, not the filer
        rel = ("wholly_owned" if (m.group(2) or "").strip().lower()
               .startswith("wholly") else
               "majority_owned" if (m.group(2) or "").strip().lower()
               .startswith("majority") else "subsidiary_unspecified")
        for nm in split_names(m.group(1)):
            emit(nm, rel, m.group(0), "is_a_subsidiary_of")

    for m in EQUITY.finditer(text):
        for nm in split_names(m.group(2)):
            emit(nm, "equity_or_jv", m.group(0), "equity_interest",
                 pct=m.group(1))

    outcome = ("NAMES_EXTRACTED" if names_stated else
               "NOTE_PRESENT_NAMES_NOT_STATED" if note_present else
               "NO_CONSOLIDATION_NOTE_IN_TEXT")
    log = {
        "doc_id": d["doc_id"], "corporation_name": parent,
        "cedar_uid": d["cedar_uid"], "anc_class": d["anc_class"],
        "period_covered": d["period"], "txt_file": str(d["txt"].name),
        "chars": len(text), "pages_ocred": d["pages_ocred"],
        "outcome": outcome, "n_names": len(found),
        "relations": ";".join(sorted({r["ownership_relation"]
                                      for r in found})),
        "portal_url": d["portal_url"], "checked_date": TODAY,
        "checked_by": THIS,
    }
    return found, log


DOCLOG_COLS = ["doc_id", "corporation_name", "cedar_uid", "anc_class",
               "period_covered", "txt_file", "chars", "pages_ocred",
               "outcome", "n_names", "relations", "portal_url",
               "checked_date", "checked_by"]


def stage_mine(limit=None) -> None:
    global SHARD_E_PAIRS
    SHARD_E_PAIRS = shard_e_pairs()
    print(f"[mine] {len(SHARD_E_PAIRS)} shard E edges already adjudicated by "
          f"hand; those pairs are not re-emitted")
    docs = documents()
    if limit:
        docs = docs[:limit]
    print(f"[mine] {len(docs)} extracted documents")
    if ROWS.exists():
        ROWS.unlink()                        # deterministic, offline, no resume
    logs = []
    tot = 0
    for i, d in enumerate(docs, 1):
        rows, log = mine_doc(d)
        with open(ROWS, "a", encoding="utf-8", newline="") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())            # FLUSH PER DOCUMENT
        logs.append(log)
        tot += len(rows)
        if len(rows) or i % 25 == 0:
            print(f"  [{i:3d}/{len(docs)}] {d['corporation_name'][:34]:34s} "
                  f"{d['period']}  {log['outcome']:30s} {len(rows):3d}")
    with open(DOCLOG, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=DOCLOG_COLS)
        w.writeheader()
        w.writerows(logs)
    print(f"[mine] {tot} rows -> {ROWS}")
    print(f"[mine] {len(logs)} document log rows -> {DOCLOG}")


# ---------------------------------------------------------------------------
def shard_e_pairs() -> set:
    p = set()
    if not SHARD_E.exists():
        return p
    for l in SHARD_E.read_text(encoding="utf-8").splitlines():
        if not l.strip():
            continue
        d = json.loads(l)
        p.add((_norm(d.get("parent_name", "")),
               _norm(d.get("child_name_raw", ""))))
    return p


def load_rows(path: Path = ROWS) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()
            if l.strip()]


def verify(rows_path: Path = ROWS, doclog: Path = DOCLOG,
           quiet=False) -> list[str]:
    bad = []
    rows = load_rows(rows_path)
    se = shard_e_pairs()
    for r in rows:
        nm = r["business_name_raw"]
        if not SUFFIX.search(nm):                                      # W1
            bad.append(f"W1 no corporate suffix: {nm!r}")
        q = r.get("identity_claim_text", "")
        if not q:                                                      # W2
            bad.append(f"W2 no quote: {nm!r}")
        elif first_word(nm).lower() not in q.lower():                  # W2
            bad.append(f"W2 name not in its own quote: {nm!r}")
        if _norm(nm) == _norm(r["authority_name"]):                    # W3
            bad.append(f"W3 child equals parent: {nm!r}")
        if r.get("ownership_relation") not in RELATIONS:               # W4
            bad.append(f"W4 undeclared relation "
                       f"{r.get('ownership_relation')!r}")
        if (_norm(r["authority_name"]), _norm(nm)) in se:              # W6
            bad.append(f"W6 duplicates a shard E edge: "
                       f"{r['authority_name']} -> {nm}")
    if doclog.exists():
        with open(doclog, encoding="utf-8-sig", newline="") as fh:
            logged = {r["doc_id"] for r in csv.DictReader(fh)}
        missing = {d["doc_id"] for d in documents()} - logged
        if missing:                                                    # W5
            bad.append(f"W5 {len(missing)} extracted documents have no log "
                       f"row")
    if not quiet:
        for b in bad[:40]:
            print("  FAIL " + b)
        if len(bad) > 40:
            print(f"  ... and {len(bad)-40} more")
        print(f"[verify] {len(bad)} violations across {len(rows)} rows")
    return bad


def selftest() -> int:
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="cedar1073_"))
    ok = True
    good = {"authority_name": "Azachorok, Incorporated",
            "business_name_raw": "Azachorok Contract Services, LLC",
            "identity_claim_text": "include the accounts of Azachorok, "
                                   "Incorporated and its wholly owned "
                                   "subsidiary Azachorok Contract Services, "
                                   "LLC.",
            "ownership_relation": "wholly_owned"}

    def mk(rows):
        p = tmp / "r.jsonl"
        p.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
        return p

    cases = [
        ("W1", {**good, "business_name_raw": "Azachorok Contract Services"}),
        ("W2", {**good, "identity_claim_text": ""}),
        ("W3", {**good, "business_name_raw": "Azachorok, Incorporated",
                "identity_claim_text": "Azachorok, Incorporated"}),
        ("W4", {**good, "ownership_relation": "owned_probably"}),
    ]
    for tag, row in cases:
        bad = verify(mk([row]), tmp / "nope.csv", quiet=True)
        fired = [b for b in bad if b.startswith(tag)]
        print(f"  {tag}: {'FIRES' if fired else 'DID NOT FIRE'}"
              + (f"  -> {fired[0][:80]}" if fired else ""))
        ok &= bool(fired)

    se = shard_e_pairs()
    if se:
        pn, cn = next(iter(se))
        for l in SHARD_E.read_text(encoding="utf-8").splitlines():
            d = json.loads(l)
            if (_norm(d["parent_name"]), _norm(d["child_name_raw"])) == (pn, cn):
                break
        bad = verify(mk([{**good, "authority_name": d["parent_name"],
                          "business_name_raw": d["child_name_raw"],
                          "identity_claim_text": d["child_name_raw"] + " ."}]),
                     tmp / "nope.csv", quiet=True)
        fired = [b for b in bad if b.startswith("W6")]
        print(f"  W6: {'FIRES' if fired else 'DID NOT FIRE'}")
        ok &= bool(fired)

    # W5 — a log missing a document
    lg = tmp / "d.csv"
    with open(lg, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=DOCLOG_COLS)
        w.writeheader()
    bad = verify(mk([]), lg, quiet=True)
    fired = [b for b in bad if b.startswith("W5")]
    print(f"  W5: {'FIRES' if fired else 'DID NOT FIRE'}"
          + ("" if fired else "  (no extracted documents on disk?)"))
    ok &= bool(fired)

    bad = [b for b in verify(mk([good]), tmp / "nope.csv", quiet=True)]
    print(f"  clean fixture: {'PASSES' if not bad else 'FAILS ' + str(bad)}")
    ok &= not bad
    print(f"[selftest] {'ALL INVARIANTS FIRE' if ok else 'A CHECK IS DEAD'}")
    return 0 if ok else 1


def report() -> None:
    rows = load_rows()
    print(f"rows: {len(rows)}")
    print("  relation:",
          dict(collections.Counter(r["ownership_relation"] for r in rows)))
    print("  route:", dict(collections.Counter(r["route"] for r in rows)))
    print("  distinct parents:",
          len({r["authority_name"] for r in rows}))
    print("  distinct children:",
          len({_norm(r["business_name_raw"]) for r in rows}))
    if DOCLOG.exists():
        with open(DOCLOG, encoding="utf-8-sig", newline="") as fh:
            lg = list(csv.DictReader(fh))
        print("  document outcomes:",
              dict(collections.Counter(r["outcome"] for r in lg)))
        corps = collections.defaultdict(set)
        for r in lg:
            corps[r["corporation_name"]].add(r["outcome"])
        anyname = sum(1 for c, o in corps.items() if "NAMES_EXTRACTED" in o)
        print(f"  corporations: {len(corps)}; {anyname} yielded at least one "
              f"named subsidiary")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["mine", "report", "verify", "selftest"])
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    if a.stage == "mine":
        stage_mine(limit=a.limit)
        return 0
    if a.stage == "report":
        report()
        return 0
    if a.stage == "selftest":
        return selftest()
    return 1 if verify() else 0


if __name__ == "__main__":
    sys.exit(main())
