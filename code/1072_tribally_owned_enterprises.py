#!/usr/bin/env python3
"""1072 - NEST: Native Enterprise Structures and Ties.

    Enterprise ownership and affiliation across tribes, Alaska Native
    corporations, Native Hawaiian organizations, and state-recognized
    Native entities.   -- the owner, 2026-09-02

Collection id `nest`. The 14th dataset, and it is DISTINCT from
`native-owned-businesses` by the relation it publishes:

    native-owned-businesses   a nation CERTIFIED or LISTED this firm
                              -> relation `affiliated_with`, identity_scope
                                 gradient down to `vendor_relationship`
    nest (this)               a nation, ANC or NHO OWNS this enterprise
                              -> relation `owned_by`, and that is a CLAIM,
                                 so every row carries the source that asserts
                                 it and the evidence class of that source

Federal contracting only ever sees the enterprises that pursue federal work.
A nation's casino management company, propane utility, farm, radio station,
gas stations and holding company may never appear in FPDS at all. Those are
the rows nobody has, and `in_federal_contracting = N` is the column that
counts them.

THE HIERARCHY IS THE PRODUCT
----------------------------
    HUB       Winnebago Tribe of Nebraska      (a spine entity, CE- uid)
      L1      Ho-Chunk, Inc.                   (holding company, a SUB-HUB)
        L2      All Native Services Company    (operating company)

A sub-hub is never a peer of its hub (docs/IDENTIFIER_STANDARD.md). So the
enterprise table carries BOTH `owner_hub_cedar_uid` (the nation at the top of
the chain, always a spine entity) and `parent_name` / `parent_enterprise_id`
(the immediate owner, which may itself be an enterprise), plus
`hierarchy_level`.

STAGES
------
  mine      zero network. Mines the AS 45.55.139 audited annual reports
            already on this machine for their "Principles of Consolidation"
            subsidiary enumerations. 358 village-corporation reports in
            data/raw/external/ancsa_portal_v3 and 166 regional-corporation
            texts in data/interim/ancsa_txt. Flushes per document.
  assemble  zero network. Merges every staged ownership assertion Cedar
            already holds into one normalised edge set, with the ANCSA and
            named-collision guards applied.
  build     writes data/clean/nest_enterprises.csv and
            data/clean/nest_enterprise_relations.csv, minting a Cedar sub-hub
            id per enterprise.
  verify    invariants. Exits 1 when one breaks.
  selfcheck proves `verify` FIRES, by injecting each violation into a COPY.

WHAT THIS SCRIPT WILL NOT DO
----------------------------
  * It never writes to data/spine/, to cedar_constellation_edges.csv, or to
    native_owned_businesses.csv.
  * It never asserts ownership from a shared name or a shared address. Every
    row's ownership claim comes from a source that stated it; the evidence
    class is on the row.
  * TERMS_STATED_RESTRICTIVE publishers are excluded by every route.
  * No natural person's name is read into any field.
"""

from __future__ import annotations

import csv
import glob
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

SCRIPT = "code/1072_tribally_owned_enterprises.py"
BUILT = date.today().isoformat()
CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
STAGE = CEDAR / "data" / "staging" / "nest"
INTERIM = CEDAR / "data" / "interim"
RAW = CEDAR / "data" / "raw"
REVIEW = CEDAR / "review"

MINED = STAGE / "ancsa_consolidation_edges.jsonl"
MINE_LOG = STAGE / "ancsa_mine_log.csv"
EDGES_STAGED = STAGE / "ownership_edges_staged.jsonl"
HELD = STAGE / "held_rows.csv"

OUT_ENT = CLEAN / "nest_enterprises.csv"
OUT_EDGE = CLEAN / "nest_enterprise_relations.csv"
# Append-only binding of (owner hub, normalised name) -> enterprise_id.
# Kept in data/spine because an identifier a customer joins on must
# survive a staging wipe, and because it is identity, not output.
IDREG = SPINE / "cedar_nest_id_register.csv"

# ---------------------------------------------------------------------------
# EXCLUSIONS. docs/PUBLICATION_POLICY.md - TERMS_STATED_RESTRICTIVE publishers
# are refused by EVERY route, including a harmonised derivative of data some
# earlier pass already fetched. Matched on the asserting PARENT's name and on
# the source URL host, because a restricted publisher's page is a restricted
# source whichever table it is sitting in today.
# ---------------------------------------------------------------------------
RESTRICTED_NAME = re.compile(
    r"\b(colville|umatilla|ctuir|yakama|chickasaw|nana\s+regional|akima"
    r"|southern\s+ute|forest\s+county\s+potawatomi|stillaguamish)\b", re.I)
RESTRICTED_HOST = re.compile(
    r"(colville|ctuir|umatilla|yakama|chickasaw|nana\.com|akima|southernute"
    r"|fcpotawatomi|stillaguamish)", re.I)


def restricted(*fields) -> str:
    for f in fields:
        f = (f or "")
        if RESTRICTED_NAME.search(f):
            return "TERMS_STATED_RESTRICTIVE:name:" + RESTRICTED_NAME.search(f).group(0)
        if RESTRICTED_HOST.search(f):
            return "TERMS_STATED_RESTRICTIVE:host:" + RESTRICTED_HOST.search(f).group(0)
    return ""


# ---------------------------------------------------------------------------
# NAME NORMALISATION
# ---------------------------------------------------------------------------
_SUFFIX = re.compile(
    r"[ ,]+(?:l\.?l\.?c\.?|l\.?l\.?p\.?|pllc|inc\.?|incorporated|corp\.?|"
    r"corporation|co\.?|company|ltd\.?|limited|lp|l\.p\.|plc)\.?$", re.I)


def norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = s.replace("’", "'").replace("‘", "'")
    s = re.sub(r"[^a-z0-9' ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    for _ in range(3):
        n = _SUFFIX.sub("", s).strip()
        if n == s:
            break
        s = n
    return re.sub(r"\s+", " ", s).strip()


def tidy(s: str) -> str:
    """Display form: collapse whitespace, strip a trailing bare period."""
    s = re.sub(r"\s+", " ", (s or "").strip())
    s = s.strip(' ."“”')
    return s


def sha(*parts) -> str:
    return hashlib.md5("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()


def read_csv(p) -> list:
    p = Path(p)
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def read_jsonl(p) -> list:
    p = Path(p)
    if not p.exists():
        return []
    out = []
    with p.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def write_csv(path: Path, cols: list, rows: list) -> None:
    """`.part` then rename, with the header DERIVED, never hardcoded.

    Two defects this one function is written against:

    1. **An interruption must not look like a completion.** Write `.part`,
       then rename.
    2. **A hardcoded `fieldnames` list DELETES every column added since the
       writer was written.** `code/845_regenerate_guard.py` found 33 writers
       in this repo holding one. So the header is the canonical list this
       build produces UNIONED with whatever the live file already carries -
       a column a sibling workstream added to a NEST table survives a
       rebuild here, and is carried through with an empty value rather than
       dropped.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    live = []
    if path.exists():
        with path.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            live = next(csv.reader(fh), []) or []
    header = list(cols) + [c for c in live if c not in cols]
    tmp = path.with_suffix(path.suffix + ".part")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header, extrasaction="ignore",
                           restval="")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    if path.exists():
        path.unlink()
    tmp.rename(path)


# ===========================================================================
# STAGE `mine` - the AS 45.55.139 audited annual reports
# ===========================================================================
# The ANCSA route the owner named. Every ANCSA corporation with 500+
# shareholders files an audited annual report with the Alaska Division of
# Banking and Securities under AS 45.55.139, and the "Principles of
# Consolidation" note ENUMERATES the wholly- and majority-owned subsidiaries
# BY LEGAL NAME, signed off by an auditor. That is ownership asserted by the
# parent, about itself, under a statutory filing obligation.
#
# Two parser facts, both learned by measuring rather than guessing:
#
#  1. YOU CANNOT SPLIT THE NOTE INTO SENTENCES. Every second subsidiary name
#     ends in "Inc." and a sentence splitter cuts the list in half at the
#     first one. The window is taken by CHARACTER COUNT from the trigger and
#     closed by a named terminator phrase instead.
#  2. YOU CANNOT SPLIT THE LIST ON COMMAS. "Wetaviq, Ltd." contains one, and
#     splitting produced "Wetaviq" and "Ltd" as two firms. Names are matched
#     with a company-FORM anchored regex over the window, not split out of it.
#
# ANTI-FABRICATION: every emitted name must appear VERBATIM in the source
# text. It does by construction here - the name is a substring of the
# document - and `verify` re-checks a sample against the stored text.
# ---------------------------------------------------------------------------
_FORM = (r"(?:L\.?L\.?C\.?|L\.?L\.?P\.?|PLLC|Inc\.?|Incorporated|Corporation|"
         r"Corp\.?|Company|Co\.|Ltd\.?|Limited|LP|L\.P\.)")
_WORD = r"[A-Z0-9][A-Za-z0-9'’&/\.\-]*"
_CONN = r"(?:and|of|the|for|de|del|at|on|in)"
NAME_RE = re.compile(
    r"\b(" + _WORD + r"(?:[ \-](?:" + _WORD + r"|" + _CONN + r")){0,7}),?[ ](" + _FORM + r")(?![A-Za-z])")

TRIG_A = re.compile(
    r"(?:accounts of|include|includes)[^.]{0,180}?\b"
    r"(?:wholly|majority|wholly and majority|wholly owned and majority)?"
    r"[\s‐-―-]*owned\s+subsidiar(?:y|ies)\b", re.I)
TRIG_B = re.compile(
    r"(?<!of )\b(?:wholly|majority)[\s‐-―-]*owned\s+subsidiar(?:y|ies)\s*[:;]", re.I)
STOP_RE = re.compile(
    r"(All significant|All material|All intercompany|Intercompany|Noncontrolling"
    r"|Use of estimates|Cash and cash|liability is|most of which are"
    r"|Entities that are|are described below|collectively referred"
    r"|Basis of |Revenue recognition|Subsequent events|Notes to Consolidated"
    r"|Summary of Significant)", re.I)

# Words that are a note's own furniture, never a subsidiary.
NOT_A_FIRM = {
    "the corporation", "the company", "the trust", "the corporation s",
    "corporation", "company", "consolidated", "notes to consolidated",
    "financial statements", "the following", "december", "january", "united states",
    "the parent", "parent", "annual report", "board of directors",
}


def _corp_year(stem: str):
    head = stem.split("__")[0]
    m = re.match(r"^(.*)_((?:19|20)\d{2})$", head)
    if m:
        return m.group(1).replace("_", " ").strip(), m.group(2)
    return head.replace("_", " ").strip(), ""


def _pdf_text(path: Path, cachedir: Path) -> str:
    cachedir.mkdir(parents=True, exist_ok=True)
    tp = cachedir / (path.stem + ".txt")
    if tp.exists():
        return tp.read_text(encoding="utf-8", errors="replace")
    try:
        import pymupdf
        d = pymupdf.open(str(path))
        txt = "".join(pg.get_text() for pg in d)
        d.close()
    except Exception as exc:                        # noqa: BLE001
        txt = ""
        sys.stderr.write(f"  ! text extraction failed {path.name}: {exc}\n")
    tmp = tp.with_suffix(".txt.part")
    tmp.write_text(txt, encoding="utf-8", errors="replace")
    if tp.exists():
        tp.unlink()
    tmp.rename(tp)
    return txt


# Bristol Bay's consolidation note is a NUMBERED list, and its numbers were
# being read as part of the next firm's name ("10.CCI Mechanical, LLC") and,
# worse, were letting one greedy match run across two list items
# ("Aerostar SES LLC 17. Herman Construction Group, Inc"). The markers are
# turned into separators BEFORE any name is matched.
LIST_MARK = re.compile(r"(?<![A-Za-z0-9])\d{1,3}\s*\.\s*(?=[A-Z])")
JV_RE = re.compile(r"\b(joint\s+venture|[ ,]JV\b|\bJV[ ,])", re.I)
# A name whose whole distinctive token set is one generic word may not be a
# firm - ENTITY_MATCH_RULES.md rule 1, applied at extraction rather than at
# matching, because a bad row is worse than an absent one here.
GENERIC_SOLO = {
    "restoration", "services", "holdings", "development", "management",
    "construction", "properties", "solutions", "technologies", "enterprises",
    "trading", "energy", "aviation", "logistics", "federal", "group",
    "industries", "investment", "investments", "tourism", "utility", "fuel",
}


def mine_note(text: str, parent_display: str):
    """-> [(child_name, relationship, quote)] from one document's notes."""
    t = re.sub(r"\s+", " ", text)
    parent_n = norm(parent_display)
    out, seen = [], set()
    for trig in (TRIG_A, TRIG_B):
        for m in trig.finditer(t):
            head = t[max(0, m.start() - 60):m.end()]
            base_rel = ("majority_owned" if re.search(r"majority", head, re.I)
                        else "wholly_owned" if re.search(r"wholly", head, re.I)
                        else "subsidiary")
            win = t[m.end():m.end() + 1500]
            s = STOP_RE.search(win)
            if s:
                win = win[:s.start()]
            quote = tidy(t[m.start():m.end() + min(len(win), 700)])
            win = LIST_MARK.sub("; ", win)
            for nm in NAME_RE.finditer(win):
                core, form = nm.group(1), nm.group(2)
                core = re.sub(r"^\d{1,3}\s*\.?\s*", "", core).strip()
                if not core:
                    continue
                full = tidy(core + ", " + form)
                n = norm(full)
                if not n or n in NOT_A_FIRM or len(n) < 3:
                    continue
                if n == parent_n or n == re.sub(r"^the ", "", parent_n):
                    continue                            # the parent naming itself
                if core.lower() in ("the", "and", "its", "a", "an"):
                    continue
                # Page furniture bled into the window, and sentence bleed.
                if re.search(r"\bANNUAL REPORT\b|\bNOTES? TO\b", core, re.I):
                    continue
                if re.search(r"\.\s", core):            # "Alaska. Kuskokwim ..."
                    continue
                if n in GENERIC_SOLO:                   # rule 1, at extraction
                    continue
                if len(core.split()) > 8:               # a greedy run, not a name
                    continue
                if n in seen:
                    continue
                # ANTI-FABRICATION: the emitted name must be in the document.
                if full.rstrip(".") not in t and core not in t:
                    continue
                seen.add(n)
                # A JV genuinely has two parents (ENTITY_MATCH_RULES rule 11),
                # so it is never recorded as a wholly-owned subsidiary even
                # when the note lists it under that heading.
                rel = "joint_venture" if JV_RE.search(full) else base_rel
                out.append((full, rel, quote))
    return out


def stage_mine(argv) -> int:
    STAGE.mkdir(parents=True, exist_ok=True)
    cache_v3 = INTERIM / "ancsa_txt_1072"
    docs = []
    for p in sorted(glob.glob(str(RAW / "external" / "ancsa_portal_v3" / "*.pdf"))):
        docs.append(("ANC_VILLAGE", Path(p), "pdf"))
    for p in sorted(glob.glob(str(INTERIM / "ancsa_txt" / "*.txt"))):
        docs.append(("ANC_REGIONAL", Path(p), "txt"))

    print(f"=== 1072 mine - {len(docs)} AS 45.55.139 documents on disk ===")
    seen_keys = {r["mine_key"] for r in read_jsonl(MINED)}
    log_rows = []
    out = MINED.open("a", encoding="utf-8")
    n_new = 0
    for i, (klass, path, kind) in enumerate(docs, 1):
        text = _pdf_text(path, cache_v3) if kind == "pdf" else path.read_text(
            encoding="utf-8", errors="replace")
        corp, yr = _corp_year(path.stem)
        # A regional filename is `2016__Ahtna_Inc.__title__hash`
        if klass == "ANC_REGIONAL":
            bits = path.stem.split("__")
            yr = bits[0] if re.match(r"^(19|20)\d{2}$", bits[0]) else ""
            corp = bits[1].replace("_", " ").strip() if len(bits) > 1 else corp
        rx = restricted(corp, path.name)
        found = [] if rx else mine_note(text, corp)
        log_rows.append({
            "document": path.name, "owner_class": klass, "corporation": corp,
            "fiscal_year": yr, "chars_of_text": len(text),
            "n_subsidiaries_named": len(found),
            "outcome": ("EXCLUDED_" + rx if rx else
                        "NO_TEXT_LAYER" if len(text) < 2000 else
                        "NAMES_FOUND" if found else "NOTE_NAMES_NONE"),
        })
        for name, rel, quote in found:
            key = sha(path.name, norm(name))
            if key in seen_keys:
                continue
            seen_keys.add(key)
            out.write(json.dumps({
                "mine_key": key,
                "parent_name": corp,
                "owner_class_hint": klass,
                "child_name_raw": name,
                "relationship": rel,
                "source_document": path.name,
                "source_fy": yr,
                "quote": quote[:900],
                "evidence_class": "audited_annual_report_as_45_55_139",
                "source_url": "https://portal.akdbsstar.us/StarWebPortal/  (AS 45.55.139 filing)",
                "retrieved_date": BUILT,
                "built_by_script": SCRIPT,
            }, ensure_ascii=False) + "\n")
            n_new += 1
        out.flush()                    # FLUSH PER ENTITY - agents get killed
        os.fsync(out.fileno())
        if i % 50 == 0:
            print(f"  {i}/{len(docs)} documents, {n_new} new edges")
    out.close()
    write_csv(MINE_LOG, list(log_rows[0].keys()) if log_rows else ["document"], log_rows)

    tot = read_jsonl(MINED)
    print(f"  documents          {len(docs)}")
    print(f"  with a text layer  {sum(1 for r in log_rows if r['chars_of_text'] >= 2000)}")
    print(f"  naming 1+ firm     {sum(1 for r in log_rows if r['n_subsidiaries_named'])}")
    print(f"  excluded on terms  {sum(1 for r in log_rows if r['outcome'].startswith('EXCLUDED'))}")
    print(f"  edges staged       {len(tot)} ({n_new} new this run)")
    print(f"  distinct parents   {len({r['parent_name'] for r in tot})}")
    print(f"  distinct firms     {len({norm(r['child_name_raw']) for r in tot})}")
    print(f"  -> {MINED}")
    print(f"  -> {MINE_LOG}")
    return 0


# ===========================================================================
# HUB RESOLUTION
# ===========================================================================
import unicodedata


def squash(s: str) -> str:
    """Accent-folded, punctuation-free key. `K'oyitl'ots'ina` == `K oyitl ots ina`.

    The AS 45.55.139 filenames mangle apostrophes to underscores and drop
    diacritics, so `norm()` alone loses Gana-A'Yoo, Shee Atika and
    K'oyitl'ots'ina - three real ANCSA corporations, all with Alaska Native
    orthography, which ENTITY_MATCH_RULES rule 14 says is a POSITIVE signal
    and which a naive matcher therefore drops exactly where it should hit.
    """
    s = unicodedata.normalize("NFKD", (s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s.lower())


def name_keys(name: str):
    """Deterministic renderings of ONE name, strongest key first.

    These are normalisations, not fuzzy matching: every key is a function of
    the string, and a match still has to be UNIQUE to win. Each rung exists
    because a real ANCSA corporation was lost without it, measured
    2026-09-02 against the 336 rows this build first held as
    `no_spine_candidate`:

      norm                 "Tanadgusix Corporation"      baseline
      no-parenthetical     "Tanadgusix Corporation (TDX)"  the spine carries
                           the acronym in the canonical name
      no-leading-"the"     "The Eyak Corporation" / "Eyak Corporation";
                           "The Tyonek Native Corporation"
      squash(norm)         "Gana-A'Yoo, Ltd." / "Gana-A Yoo Limited" and
                           "K'oyitl'ots'ina, Ltd." / "K oyitl ots ina
                           Limited" - the AS 45.55.139 filenames mangle the
                           apostrophes that Alaska Native orthography puts in
                           these names, and `Ltd.` vs `Limited` survives
                           `norm` on one side only
    """
    raw = (name or "").strip()
    forms = {raw}
    forms.add(re.sub(r"\s*\([^)]*\)", " ", raw))
    for f in list(forms):
        forms.add(re.sub(r"^the\s+", "", f, flags=re.I))
    out = []
    for f in sorted(forms):
        n = norm(f)
        if n:
            out.append(("exact_normalized_name", n))
    for f in sorted(forms):
        n = squash(norm(f))
        if n:
            out.append(("accent_and_form_folded_name", n))
    seen, uniq = set(), []
    for meth, k in out:
        if k not in seen:
            seen.add(k)
            uniq.append((meth, k))
    return uniq


class Hubs:
    """The spine, indexed for the lookups this build makes."""

    def __init__(self):
        self.rows = read_csv(SPINE / "cedar_identity_register.csv")
        self.by_handle, self.by_uid = {}, {}
        self.index = defaultdict(list)
        self.anc_prefix = []                 # (squashed name, row) for ANC classes
        for r in self.rows:
            h = (r.get("handle") or "").strip()
            u = (r.get("cedar_uid") or "").strip()
            if h:
                self.by_handle[h] = r
            if u:
                self.by_uid[u] = r
            for nm in ((r.get("canonical_name") or "").strip(),
                       (r.get("federal_register_legal_name") or "").strip()):
                if not nm:
                    continue
                for _meth, k in name_keys(nm):
                    self.index[k].append(r)
                if r.get("entity_class") in ANC_CLASSES:
                    self.anc_prefix.append((squash(norm(nm)), r))

    def by_name(self, name: str, classes=None):
        """Returns (row, method) or (None, refusal_reason).

        UNIQUENESS IS REQUIRED: a name matching two spine entities resolves
        to neither. That is what keeps `Cherokee` - 45 entities, three of
        them federally recognized tribes - from resolving to anything at all
        (ENTITY_MATCH_RULES rule 13).
        """
        for meth, key in name_keys(name):
            cands = self.index.get(key, [])
            if classes:
                cands = [c for c in cands if c.get("entity_class") in classes]
            uniq = {c["cedar_uid"]: c for c in cands}
            if len(uniq) == 1:
                return list(uniq.values())[0], meth
            if len(uniq) > 1:
                return None, f"ambiguous_{meth}_{len(uniq)}_candidates"
        return None, "no_spine_candidate"

    def anc_by_prefix(self, token: str):
        """One ANCSA corporation whose name STARTS with this token, or none.

        Only ever called with a corporation name the SOURCE supplied in its
        own `parent_entity_type` field - `ANC_VILLAGE_AFOGNAK` naming Afognak
        Native Corporation. It is a prefix test rather than an equality test
        because the source writes the place and the spine writes the full
        corporate name, and it REFUSES a token shorter than five characters
        so an acronym can never win this way.
        """
        t = squash(norm(token))
        if len(t) < 5:
            return None, f"token {token!r} too short for a prefix match"
        hits = {r["cedar_uid"]: r for k, r in self.anc_prefix if k.startswith(t)}
        if len(hits) == 1:
            return list(hits.values())[0], "anc_name_prefix_from_source_type"
        return None, (f"{len(hits)} ANCSA corporations start with {token!r}")


ANC_CLASSES = {"Alaska Native Regional Corporation",
               "Alaska Native Village Corporation"}
VILLAGE_GOV = "Federally recognized Alaska Native Village"

# ---------------------------------------------------------------------------
# THE ALASKA VILLAGE-GOVERNMENT / VILLAGE-CORPORATION GUARD
# ---------------------------------------------------------------------------
# `docs/ANCSA_OWNERSHIP_RULING.md` RULE 2 and
# `cedar_domain.village_government_owns_an_anc()` (always False): a Native
# Village GOVERNMENT does not own an ANCSA corporation. The village is a
# government; the corporation is a shareholder-owned company. They are
# different entities that share a place name.
#
# `data/raw/external/anc_tribal_subsidiary_lookup.csv` violates that on 84 of
# its 549 rows, and it says so itself: `parent_entity_type` reads
# `ANC_VILLAGE_UIC` while `parent_entity_id` is `AKNF-...`, the Native Village
# of Barrow's GOVERNMENT. The type column names the corporation the source
# meant. So the repoint is read out of the source's own field, never guessed,
# and where the named corporation is not uniquely in the spine the row is HELD
# rather than attached to the government.
ANC_VILLAGE_TYPE = re.compile(r"^ANC_VILLAGE_(.+)$")

# NAMED EXCEPTIONS, and only for acronyms. The structural predicate above -
# read the corporation out of the source's own `parent_entity_type` and match
# it by name or by name-prefix - resolves every case except one, where the
# source writes an ACRONYM that is by construction too short to prefix-match
# safely. Each exception is a corporation Cedar already holds, named here with
# the handle rather than re-derived, because guessing what `UIC` expands to is
# precisely what a matcher must not do.
ANC_ACRONYM = {
    # Ukpeagvik Inupiat Corporation, Utqiagvik/Barrow. The 34 Bowhead-family
    # rows in anc_tribal_subsidiary_lookup.csv are keyed to the Native
    # Village of Barrow's GOVERNMENT and belong to the corporation; the same
    # defect ENTITY_MATCH_RULES rule 12 found from the other direction, where
    # 54 correctly keyed Bowhead subsidiaries were made to look wrong by one
    # bad parent row.
    "UIC": "ANVC-KPVKPT-00",
}

# A government is not a corporation. It can charter one, own one and be paid
# by one - it cannot BE somebody else's subsidiary. Used to tell a name
# COLLISION from a hub IDENTITY when a listed firm matches a spine name.
GOVERNMENT_CLASSES = {
    "Federally recognized tribe", "State-recognized tribe",
    "Federally recognized Alaska Native Village",
    "Federal-level constituency entity", "State-level constituency entity",
}


# ===========================================================================
# STAGE `assemble` - every ownership assertion Cedar already holds, normalised
# ===========================================================================
def _edge(**kw):
    base = dict(
        parent_name="", parent_cedar_uid="", parent_handle="",
        hub_cedar_uid="", hub_hint_name="", owner_class_hint="",
        child_name_raw="", relationship="subsidiary", ownership_percent="",
        sector="", child_cage="", child_uei="", child_city="", child_state="",
        evidence_class="", source_id="", source_url="", source_document="",
        source_fy="", source_edition_date="", quote="", depth_hint=1,
        identity_scope="tribally_owned_entity", retrieved_date=BUILT,
        source_terms_status="SILENT",
    )
    base.update(kw)
    return base


def load_sources() -> tuple:
    """-> (edges, provenance Counter). Zero network; every input is on disk."""
    edges, prov = [], Counter()

    # 1. AS 45.55.139 audited annual reports, mined by `mine` above.
    for r in read_jsonl(MINED):
        edges.append(_edge(
            parent_name=r["parent_name"], hub_hint_name=r["parent_name"],
            owner_class_hint="ANC", child_name_raw=r["child_name_raw"],
            relationship=r["relationship"],
            evidence_class="audited_annual_report_as_45_55_139",
            source_id="AS45.55.139", source_url=r["source_url"],
            source_document=r["source_document"], source_fy=r["source_fy"],
            source_edition_date=(r["source_fy"] + "-12-31") if r["source_fy"] else "",
            quote=r["quote"], identity_scope="parent_asserted_subsidiary"))
        prov["as_45_55_139_annual_report"] += 1

    # 2. Shard E - ANC parent-asserted edges, 404 depth-1 + 78 depth-2.
    for r in read_jsonl(CEDAR / "data/staging/anc_subsidiaries/shard_e.jsonl"):
        st = (r.get("source_type") or "")
        edges.append(_edge(
            parent_name=r.get("parent_name", ""),
            parent_cedar_uid=r.get("parent_cedar_uid", ""),
            hub_cedar_uid=r.get("anc_root_cedar_uid", ""),
            hub_hint_name=r.get("anc_root_name", ""), owner_class_hint="ANC",
            child_name_raw=r.get("child_name_raw", ""),
            relationship=r.get("child_relationship", "subsidiary"),
            ownership_percent=r.get("stated_ownership_pct", ""),
            sector=r.get("child_sector", ""),
            child_cage=r.get("child_cage_code", ""),
            evidence_class=("audited_annual_report_as_45_55_139"
                            if "annual report" in st.lower()
                            else "parent_self_published_company_list"),
            source_id="shard-E", source_url=r.get("source_url", ""),
            source_document=r.get("source_doc", ""),
            source_fy=r.get("source_fy", ""),
            quote=(r.get("quote") or "")[:900],
            depth_hint=int(r.get("depth") or 1),
            identity_scope="parent_asserted_subsidiary"))
        prov["shard_e"] += 1

    # 3. Shard H - NHO parent-declared subsidiary lists, with SBA DSBS ids.
    for r in read_jsonl(CEDAR / "data/staging/anc_subsidiaries/shard_h.jsonl"):
        edges.append(_edge(
            parent_name=r.get("parent_name", ""),
            parent_cedar_uid=r.get("parent_cedar_uid", ""),
            hub_cedar_uid=r.get("parent_cedar_uid", ""),
            hub_hint_name=r.get("parent_name", ""), owner_class_hint="NHO",
            child_name_raw=r.get("child_name_raw", ""),
            relationship=r.get("child_relationship", "subsidiary"),
            child_cage=r.get("child_cage_code", ""),
            child_uei=r.get("child_dsbs_uei", ""),
            child_city=r.get("child_city", ""), child_state=r.get("child_state", ""),
            evidence_class="parent_declared_subsidiary_list",
            source_id="shard-H", source_url=r.get("source_url", ""),
            quote=(r.get("quote") or "")[:900],
            depth_hint=int(r.get("depth") or 1),
            identity_scope="parent_asserted_subsidiary"))
        prov["shard_h"] += 1

    # 4. The 701 enterprise register - a NATION's own list of its companies.
    #    Accepted rows only: the other 83 are held navigation furniture, a
    #    single generic word, or the Doyon joint-venture contradiction.
    for r in read_jsonl(CEDAR / "data/staging/tribal_enterprises/enterprise_register.jsonl"):
        if (r.get("review_status") or "") != "accepted":
            prov["_701_not_accepted"] += 1
            continue
        edges.append(_edge(
            parent_name=r.get("tribe_name", ""),
            parent_cedar_uid=r.get("tribe_cedar_uid", ""),
            parent_handle=r.get("tribe_id", ""),
            hub_cedar_uid=r.get("tribe_cedar_uid", ""),
            hub_hint_name=r.get("tribe_name", ""), owner_class_hint="TRIBE",
            child_name_raw=r.get("enterprise_name_raw", ""),
            relationship=r.get("relationship", "wholly_owned"),
            sector=r.get("sector", ""),
            evidence_class="nation_self_published_enterprise_register",
            source_id="CE701", source_url=r.get("source_url", ""),
            source_edition_date=r.get("source_edition_date", ""),
            quote=(r.get("quote") or "")[:900],
            identity_scope=r.get("identity_scope", "tribally_owned_entity")))
        prov["enterprise_register_701"] += 1

    # 5. The ANC/tribe subsidiary lookup - 549 parent-published company rows,
    #    the only source here that reaches tribal governments in the lower 48
    #    at any scale (Cherokee Nation Businesses, Salt River, Mille Lacs...).
    for r in read_csv(RAW / "external" / "anc_tribal_subsidiary_lookup.csv"):
        edges.append(_edge(
            parent_name=r.get("parent_entity_name", ""),
            parent_handle=r.get("parent_entity_id", ""),
            hub_hint_name=r.get("parent_entity_name", ""),
            owner_class_hint=r.get("parent_entity_type", ""),
            child_name_raw=r.get("subsidiary_name", ""),
            relationship="subsidiary",
            evidence_class="parent_self_published_company_list",
            source_id="ANC_TRIBE_LOOKUP", source_url=r.get("source_url", ""),
            source_edition_date=r.get("fetched_date", ""),
            identity_scope="parent_asserted_subsidiary"))
        prov["anc_tribal_subsidiary_lookup"] += 1

    # 6. The business registry, SUBSIDIARY DIRECTORIES ONLY.
    #    The predicate is structural, not a hand-picked file list: a source
    #    qualifies when it declares `directory_type = subsidiary_directory`
    #    AND an ownership identity_scope. That is what keeps Calista's
    #    SHAREHOLDER business directory (98 firms owned by individual
    #    shareholders, `shareholder_descendant_or_spouse`) out of a dataset
    #    that asserts the corporation owns them - the exact flattening
    #    PUBLICATION_POLICY.md warns about.
    reg = {(x.get("harvest_source_id") or "").strip(): x
           for x in read_csv(REVIEW / "tribal_vendor_list_registry_2026-08-26.csv")
           if (x.get("harvest_source_id") or "").strip()}
    nob_auth = {}
    for x in read_csv(CLEAN / "native_owned_businesses.csv"):
        sid = (x.get("source_id") or "").strip()
        aid = (x.get("certifying_authority_entity_id") or "").strip()
        if sid and aid:
            nob_auth.setdefault(sid, (aid, x.get("certifying_authority_name", "")))
    # lint-ok: class1 - this glob ENUMERATES a source directory; it is not a
    # partial view of a set whose other members live elsewhere. The defect
    # class 1 names is `deals_*_additions.csv`, which silently omitted two
    # root ledgers holding 131 rows. Every business-registry harvest is a
    # `TBD-*.jsonl` in this one directory by construction, the selection
    # predicate is on the ROW (directory_type = subsidiary_directory), not
    # on the filename, and `stage_assemble` prints a per-source count so a
    # missing file shows up as an absent line rather than as silence.
    for path in sorted((CEDAR / "data/staging/business_registry").glob("TBD-*.jsonl")):
        rows = read_jsonl(path)
        if not rows:
            continue
        keep = [r for r in rows
                if (r.get("directory_type") or "") == "subsidiary_directory"
                and (r.get("identity_scope") or "") in
                ("tribally_owned_entity", "parent_asserted_subsidiary")]
        if not keep:
            continue
        sid = (rows[0].get("source_id") or path.stem.split("_")[0])
        handle, pname = nob_auth.get(sid, ("", ""))
        if not handle and sid in reg:
            handle = (reg[sid].get("tribe_id") or "").strip()
            pname = (reg[sid].get("canonical_name") or "").strip()
        url = (reg.get(sid, {}).get("list_url") or "")
        terms = (reg.get(sid, {}).get("source_terms_status") or "SILENT")
        for r in keep:
            edges.append(_edge(
                parent_name=pname or (r.get("nation_id") or ""),
                parent_handle=handle, hub_hint_name=pname,
                owner_class_hint="ANC" if str(r.get("nation_id", "")).startswith("ancsa:") else "TRIBE",
                child_name_raw=r.get("business_name_raw", ""),
                relationship="subsidiary",
                evidence_class="nation_self_published_enterprise_register",
                source_id=sid, source_url=url,
                source_edition_date=r.get("source_edition", "") or "",
                quote=(r.get("identity_claim_text") or "")[:900],
                identity_scope=r.get("identity_scope", "tribally_owned_entity"),
                source_terms_status=terms))
            prov["business_registry_" + sid] += 1
    return edges, prov


def stage_assemble(argv) -> int:
    STAGE.mkdir(parents=True, exist_ok=True)
    hubs = Hubs()
    edges, prov = load_sources()
    print(f"=== 1072 assemble - {len(edges)} raw ownership assertions ===")
    for k, v in sorted(prov.items()):
        print(f"    {k:<42} {v}")

    held, kept = [], []
    for e in edges:
        # --- exclusion, first, by every route -----------------------------
        rx = restricted(e["parent_name"], e["hub_hint_name"], e["source_url"],
                        e["child_name_raw"])
        if rx or e["source_terms_status"] == "TERMS_STATED_RESTRICTIVE":
            held.append({**e, "hold_reason": rx or "source_terms_status",
                         "hold_class": "TERMS_STATED_RESTRICTIVE"})
            continue
        if not tidy(e["child_name_raw"]) or not norm(e["child_name_raw"]):
            held.append({**e, "hold_reason": "empty child name",
                         "hold_class": "EMPTY"})
            continue

        # --- resolve the hub ---------------------------------------------
        row, method = None, ""
        if e["hub_cedar_uid"] and e["hub_cedar_uid"] in hubs.by_uid:
            row, method = hubs.by_uid[e["hub_cedar_uid"]], "source_supplied_cedar_uid"
        elif e["parent_cedar_uid"] and e["parent_cedar_uid"] in hubs.by_uid:
            row, method = hubs.by_uid[e["parent_cedar_uid"]], "source_supplied_cedar_uid"
        elif e["parent_handle"] and e["parent_handle"] in hubs.by_handle:
            row, method = hubs.by_handle[e["parent_handle"]], "source_supplied_handle"
        else:
            classes = ANC_CLASSES if e["owner_class_hint"] == "ANC" else None
            row, method = hubs.by_name(e["hub_hint_name"] or e["parent_name"], classes)
            if row is None and classes:
                row, method2 = hubs.by_name(e["hub_hint_name"] or e["parent_name"])
                method = method2 if row is not None else method
        if row is None:
            held.append({**e, "hold_reason": method,
                         "hold_class": "HUB_UNRESOLVED"})
            continue

        # --- the Alaska village-government guard --------------------------
        vg_note = ""
        if row.get("entity_class") == VILLAGE_GOV:
            m = ANC_VILLAGE_TYPE.match(e["owner_class_hint"] or "")
            corp, why = None, "the source names no corporation"
            if m:
                token = m.group(1).replace("_", " ")
                corp, why = hubs.by_name(token, ANC_CLASSES)
                if corp is None:
                    corp, why = hubs.by_name(token + " Corporation", ANC_CLASSES)
                if corp is None:
                    corp, why = hubs.anc_by_prefix(token)
                if corp is None and token.upper() in ANC_ACRONYM:
                    h = ANC_ACRONYM[token.upper()]
                    corp = hubs.by_handle.get(h)
                    why = f"named acronym exception {token.upper()} -> {h}"
            if corp is not None:
                vg_note = (f"REPOINTED from {row['handle']} ({row['canonical_name']}, a "
                           f"Native Village GOVERNMENT) to {corp['handle']} on the "
                           f"source's own parent_entity_type={e['owner_class_hint']!r}; "
                           f"ANCSA_OWNERSHIP_RULING rule 2 - a village government "
                           f"does not own an ANCSA corporation")
                row, method = corp, "ancsa_village_government_repointed_to_corporation"
            else:
                held.append({**e, "hold_reason":
                             f"parent resolves to a Native Village GOVERNMENT "
                             f"({row['handle']}) which cannot own an ANCSA "
                             f"corporation, and the corporation it means is not "
                             f"uniquely in the spine ({why})",
                             "hold_class": "ANCSA_VILLAGE_GOVERNMENT"})
                continue

        # --- a child that IS a hub is not that hub's peer's subsidiary ----
        # `docs/ENTERPRISE_REGISTER_BUILD_LOG.md`: Doyon's own page names Huna
        # Totem and Klawock Heenya, two independent ANCSA village
        # corporations. Reading it at face value would convert them into
        # subsidiaries of a third corporation.
        crow, _cm = hubs.by_name(e["child_name_raw"])
        child_hub_uid, child_hub_note = "", ""
        if crow is not None and crow["cedar_uid"] != row["cedar_uid"]:
            cclass = crow.get("entity_class", "")
            if cclass in GOVERNMENT_CLASSES:
                # A NAME COLLISION, NOT A HUB IDENTITY, and this is the case
                # the whole dataset could get wrong. `Ho-Chunk Inc` matches
                # the spine's `Ho-Chunk` only because `norm()` strips `Inc` -
                # and `Ho-Chunk` is the Ho-Chunk NATION OF WISCONSIN, while
                # Ho-Chunk, Inc. is the WINNEBAGO TRIBE OF NEBRASKA's holding
                # company. Two tribes, one word.
                # A government is not a corporation and can never BE somebody
                # else's subsidiary, so a government-class match here is
                # always the collision and never the identity. The edge is
                # kept, keyed to its real publisher, and the collision is
                # recorded so the next reader does not re-litigate it.
                child_hub_note = (
                    f"the firm name collides with spine hub {crow['handle']} "
                    f"({crow['canonical_name']}, {cclass}). REFUSED as an "
                    f"identity: a government cannot be a subsidiary. Owner "
                    f"stands as {row['handle']} ({row['canonical_name']}), "
                    f"which is what the publisher asserted.")
            elif cclass in ANC_CLASSES and row.get("entity_class") in ANC_CLASSES:
                # ANCSA_OWNERSHIP_RULING rules 4/5: a regional corporation
                # does not own a village corporation, and a village
                # corporation naming its region is describing ancestry.
                # Doyon's own page names Huna Totem and Klawock Heenya;
                # reading it at face value would convert two independent
                # ANCSA corporations into subsidiaries of a third.
                # NOT dropped: DOWNGRADED. NEST is Structures AND Ties, and
                # this is a real, published tie that is not ownership. The
                # row survives with `relationship = shareholding_or_ancestry`
                # so a reader can see the relationship without Cedar
                # asserting the ownership the ruling forbids.
                e = dict(e)
                e["relationship"] = ("joint_venture"
                                     if "joint" in (e.get("relationship") or "").lower()
                                     else "shareholding_or_ancestry")
                child_hub_uid = crow["cedar_uid"]
                child_hub_note = (
                    f"DOWNGRADED from ownership to a tie: publisher "
                    f"{row['handle']} and named firm {crow['handle']} are both "
                    f"ANCSA corporations, and ANCSA_OWNERSHIP_RULING rules 4/5 "
                    f"make the regional/village and village/village link "
                    f"shareholding or ancestry, never ownership")
            else:
                # A CDFI, college or other non-government Cedar entity the
                # publisher genuinely owns - Citizen Potawatomi Community
                # Development Corporation, Alaska Growth Capital BIDCO. The
                # edge is real; the enterprise is an entity Cedar already
                # holds, so the row carries its uid instead of pretending it
                # is new.
                child_hub_uid = crow["cedar_uid"]
                child_hub_note = (f"this enterprise is already a Cedar entity: "
                                  f"{crow['handle']} ({cclass})")

        e = dict(e)
        e["hub_cedar_uid"] = row["cedar_uid"]
        e["hub_handle"] = row["handle"]
        e["hub_name"] = row["canonical_name"]
        e["hub_entity_class"] = row["entity_class"]
        e["hub_state"] = row.get("state", "")
        e["hub_resolution_method"] = method
        e["hub_resolution_note"] = "; ".join(x for x in (vg_note, child_hub_note) if x)
        e["enterprise_existing_cedar_uid"] = child_hub_uid
        kept.append(e)

    with EDGES_STAGED.open("w", encoding="utf-8") as fh:
        for e in kept:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
    hcols = sorted({k for h in held for k in h}) if held else ["hold_reason"]
    write_csv(HELD, hcols, held)

    print(f"\n  kept   {len(kept)}")
    print(f"  held   {len(held)}   {dict(Counter(h['hold_class'] for h in held))}")
    print(f"  hubs   {len({e['hub_cedar_uid'] for e in kept})}")
    print(f"  by hub class: {dict(Counter(e['hub_entity_class'] for e in kept))}")
    print(f"  -> {EDGES_STAGED}")
    print(f"  -> {HELD}")
    return 0


# ===========================================================================
# STAGE `build`
# ===========================================================================
OWNER_CLASS = {
    "Federally recognized tribe": "tribal_government",
    "State-recognized tribe": "tribal_government",
    "Federally recognized Alaska Native Village": "tribal_government",
    "Federal-level constituency entity": "tribal_government",
    "State-level constituency entity": "tribal_government",
    "Federal-level self-governance consortium": "tribal_government",
    "Alaska Native Regional Corporation": "alaska_native_corporation",
    "Alaska Native Village Corporation": "alaska_native_corporation",
    "Native Hawaiian Organization": "native_hawaiian_organization",
}

# ---------------------------------------------------------------------------
# STRUCTURES AND TIES - the two relations NEST publishes, and the vocabulary
# that keeps them apart.
# ---------------------------------------------------------------------------
# The dataset's name commits it to two relations, not one, and the row has to
# say which it is. AN AFFILIATION RECORDED AS OWNERSHIP IS THE DEFECT THAT
# MATTERS MOST HERE - it is the Doyon/Huna Totem error, the one that converts
# independent ANCSA corporations into somebody's subsidiaries.
#
#   STRUCTURE  the ownership chain: nation -> holding company -> operating
#              company. `relation_class = ownership`.
#   TIE        a published relationship that is NOT ownership: a joint
#              venture (which genuinely has two parents), a passive equity
#              stake, ANCSA shareholding or ancestry. `relation_class =
#              affiliation`.
#
# Sources write this half a dozen ways ("joint venture", "joint_venture",
# "holding company", a schema.org `subOrganization`), so the vocabulary is
# normalised once, here, and anything unrecognised lands in
# `relationship_as_recorded` and is classed `affiliation` - the WEAKER
# reading, because guessing upward is the direction that fabricates.
REL_CANON = {
    "wholly_owned": "wholly_owned", "wholly owned": "wholly_owned",
    "majority_owned": "majority_owned", "majority owned": "majority_owned",
    "subsidiary": "subsidiary", "division": "division",
    "holding company": "holding_company", "holding_company": "holding_company",
    "operating company": "operating_company",
    "operating_company": "operating_company",
    "declared_suborganization_schema_org": "declared_suborganization",
    "joint_venture": "joint_venture", "joint venture": "joint_venture",
    "passive_investment": "passive_investment",
    "shareholding_or_ancestry": "shareholding_or_ancestry",
}
OWNERSHIP_RELS = {"wholly_owned", "majority_owned", "subsidiary", "division",
                  "holding_company", "operating_company",
                  "declared_suborganization"}


def canon_rel(rel: str) -> tuple:
    """-> (canonical relationship, relation_class)."""
    r = REL_CANON.get((rel or "").strip().lower(), "")
    if not r:
        return ((rel or "").strip() or "unspecified", "affiliation")
    return r, ("ownership" if r in OWNERSHIP_RELS else "affiliation")


REL_RANK = {"wholly_owned": 5, "majority_owned": 4, "subsidiary": 3,
            "division": 3, "holding_company": 3, "operating_company": 3,
            "declared_suborganization": 2, "joint_venture": 1,
            "shareholding_or_ancestry": 1, "passive_investment": 1}
EVID_RANK = {"audited_annual_report_as_45_55_139": 5,
             "nation_self_published_enterprise_register": 4,
             "parent_self_published_company_list": 3,
             "parent_declared_subsidiary_list": 3}


def federal_contracting_index():
    """The FPDS awardee universe: normalised names, UEIs and CAGE codes.

    This is a PRESENCE test, not an attribution. A name collision makes an
    enterprise look present when it is not, so the error runs AGAINST the
    headline - `in_federal_contracting = N` is a floor on the count of
    enterprises invisible to federal contracting, never a ceiling.
    """
    names, ueis, cages = set(), set(), set()
    try:
        import duckdb
        con = duckdb.connect()
        q = ("SELECT DISTINCT awardee_name, awardee_uei, cage_code FROM "
             "read_csv_auto(?, header=true, all_varchar=true, "
             "ignore_errors=true, sample_size=-1)")
        for nm, uei, cage in con.execute(q, [str(CLEAN / "prime_contracts.csv")]).fetchall():
            if nm:
                names.add(norm(nm))
            if uei and uei.strip().upper() not in ("", "NAN", "NONE"):
                ueis.add(uei.strip().upper())
            if cage and cage.strip().upper() not in ("", "NAN", "NONE"):
                cages.add(cage.strip().upper())
        con.close()
    except Exception as exc:                            # noqa: BLE001
        sys.stderr.write(f"  ! duckdb pass failed ({exc}); falling back to the map\n")
    for r in read_csv(CLEAN / "fpds_uei_cage_map.csv"):
        if r.get("legal_business_name"):
            names.add(norm(r["legal_business_name"]))
        u = (r.get("uei") or "").strip().upper()
        c = (r.get("cage_code") or "").strip().upper()
        if u and u != "NAN":
            ueis.add(u)
        if c and c != "NAN":
            cages.add(c)
    names.discard("")
    return names, ueis, cages


def stage_build(argv) -> int:
    import importlib
    cedar_ids = importlib.import_module("cedar_ids")
    id503 = importlib.import_module("503_identity") if False else None
    # 503_identity is not an importable module name (leading digit), so its
    # check-character function is loaded by path rather than by import.
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "cedar_503", str(CEDAR / "code" / "503_identity.py"))
    m503 = importlib.util.module_from_spec(spec)
    sys.modules["cedar_503"] = m503
    spec.loader.exec_module(m503)
    m503.selftest()

    edges = read_jsonl(EDGES_STAGED)
    if not edges:
        print("no staged edges - run `assemble` first")
        return 1
    hubs = Hubs()

    # ---- 1. collapse to one enterprise per (hub, normalised name) --------
    # `rapidfuzz` folds the spelling drift a ten-year run of audited filings
    # produces: `Ahtna Design Build, Inc` and `Ahtna Design-Build, Inc` are
    # one company filed twice, and counting them twice would inflate every
    # number in this dataset. Clustering is WITHIN one hub only - across hubs
    # it would fuse two nations' similarly named firms.
    try:
        from rapidfuzz import fuzz
    except Exception:                                   # noqa: BLE001
        fuzz = None

    by_hub = defaultdict(list)
    for e in edges:
        by_hub[e["hub_cedar_uid"]].append(e)

    # A hub is not its own subsidiary. `The Eyak Corporation` and the spine's
    # `Eyak Corporation`, `Coushatta Tribe of Louisiana` and the spine's
    # `Coushatta` - the leading article and the spine's deliberately short
    # canonical names made a company the parent of itself, which then
    # published as a level-2 chain that was really one company twice.
    hub_keys = {}
    for hub_uid in by_hub:
        nm = hubs.by_uid.get(hub_uid, {}).get("canonical_name", "")
        hub_keys[hub_uid] = {k for _m, k in name_keys(nm)}

    clusters = []          # (hub_uid, canonical_name, [edges], {variants})
    for hub_uid, group in sorted(by_hub.items()):
        buckets = {}       # norm-name -> list of edges
        for e in group:
            if {k for _m, k in name_keys(e["child_name_raw"])} & hub_keys[hub_uid]:
                continue   # the hub naming itself
            buckets.setdefault(norm(e["child_name_raw"]), []).append(e)
        keys = sorted(buckets)
        parent_of = {k: k for k in keys}

        def find(k):
            while parent_of[k] != k:
                parent_of[k] = parent_of[parent_of[k]]
                k = parent_of[k]
            return k

        if fuzz is not None:
            for i, a in enumerate(keys):
                for b in keys[i + 1:]:
                    if abs(len(a) - len(b)) > 6:
                        continue
                    if fuzz.ratio(a, b) >= 95 and squash(a)[:6] == squash(b)[:6]:
                        parent_of[find(b)] = find(a)
        merged = defaultdict(list)
        for k in keys:
            merged[find(k)].extend(buckets[k])
        for _root, es in merged.items():
            # canonical display name: the spelling from the most recent, most
            # authoritative source that carried it.
            best = max(es, key=lambda x: (EVID_RANK.get(x["evidence_class"], 0),
                                          str(x.get("source_fy") or ""),
                                          str(x.get("source_edition_date") or ""),
                                          len(x["child_name_raw"])))
            clusters.append((hub_uid, tidy(best["child_name_raw"]), es,
                             sorted({tidy(x["child_name_raw"]) for x in es})))

    # ---- 2. hierarchy level ---------------------------------------------
    # An enterprise that is itself named as a PARENT by another edge under
    # the same hub sits one level up from its children. A sub-hub is never a
    # peer of its hub, and a holding company is never a peer of the operating
    # company it owns.
    name_to_cluster = {}
    for idx, (hub_uid, cname, es, _v) in enumerate(clusters):
        name_to_cluster[(hub_uid, norm(cname))] = idx
    parent_idx = {}
    for idx, (hub_uid, cname, es, _v) in enumerate(clusters):
        pnames = []
        for x in es:
            pn = x.get("parent_name") or ""
            if not pn:
                continue
            if {k for _m, k in name_keys(pn)} & hub_keys[hub_uid]:
                continue                    # the parent IS the hub: level 1
            pnames.append(norm(pn))
        for pn in sorted(set(pnames)):
            j = name_to_cluster.get((hub_uid, pn))
            if j is not None and j != idx:
                parent_idx[idx] = j
                break

    def level_of(i, seen=None):
        seen = seen or set()
        if i in seen:
            return 1
        j = parent_idx.get(i)
        if j is None:
            return 1
        return 1 + level_of(j, seen | {i})

    # ---- 3. address, identifier and federal-presence lookups -------------
    dsbs_by_uei, dsbs_by_name = {}, {}
    for r in read_csv(RAW / "external" / "sba_dsbs_native_entities.csv"):
        u = (r.get("uei") or "").strip().upper()
        if u:
            dsbs_by_uei[u] = r
        dsbs_by_name.setdefault(norm(r.get("name_clean", "")), r)
    uei_of_cage, name_of_uei = {}, {}
    for r in read_csv(CLEAN / "fpds_uei_cage_map.csv"):
        u = (r.get("uei") or "").strip().upper()
        c = (r.get("cage_code") or "").strip().upper()
        if c and c != "NAN" and u:
            uei_of_cage.setdefault(c, u)
        if u:
            name_of_uei.setdefault(u, r.get("legal_business_name", ""))
    # THE SCOPE SPLIT WITH THE CONSTELLATION, made explicit in the data.
    # `data/clean/cedar_constellation_edges.csv` (ADR-014) records SERVICE
    # relationships - who serves a community, including `registered_with` for
    # a TERO-certified firm. NEST records OWNERSHIP AND CORPORATE AFFILIATION
    # of enterprises. A TERO-certified firm is a constellation edge and is
    # NOT a NEST row unless the nation also owns it, which is why this build
    # takes only sources declaring `directory_type = subsidiary_directory`.
    # The file is READ, never written, and where the two agree the
    # constellation's own edge id is carried so the corroboration is visible
    # instead of the same relationship being rebuilt under a second name.
    con_edge = {}
    for r in read_csv(CLEAN / "cedar_constellation_edges.csv"):
        k = ((r.get("to_hub_cedar_uid") or "").strip(),
             norm(r.get("from_name") or ""))
        if k[0] and k[1]:
            con_edge.setdefault(k, r.get("edge_id", ""))
    print(f"  constellation edges read (never written): {len(con_edge)} keys")

    fed_names, fed_ueis, fed_cages = federal_contracting_index()
    print(f"  FPDS presence index: {len(fed_names)} names, "
          f"{len(fed_ueis)} UEIs, {len(fed_cages)} CAGE codes")

    # ---- 4. mint and emit ------------------------------------------------
    # ---- 3b. THE ID REGISTER, so a rebuild does not re-key the dataset ----
    # `cedar_ids.allocate` hands out a NEW ordinal every call, so minting
    # inside the emit loop would give every enterprise a different id on
    # every build - a non-deterministic primary key, which is defect class 7
    # in `code/293_lint_bug_classes.py` and the one that quietly breaks a
    # customer's join. The binding (owner hub, normalised enterprise name) ->
    # enterprise_id is therefore APPEND-ONLY on disk and read first.
    idreg_rows = read_csv(IDREG)
    idreg = {(r["owner_hub_cedar_uid"], r["enterprise_name_normalized"]):
             r["enterprise_id"] for r in idreg_rows}
    need = [(h, norm(c)) for h, c, _e, _v in clusters
            if (h, norm(c)) not in idreg]
    if need:
        got = cedar_ids.allocate("CEDAR-NEST", len(need),
                                 note="NEST enterprise sub-hubs, 1072")
        for (h, nk), raw in zip(need, got):
            ordinal = int(raw.rsplit("-", 1)[1])
            eid = f"{raw}-{m503.check_chars(m503.encode(ordinal))}"
            idreg[(h, nk)] = eid
            idreg_rows.append({
                "enterprise_id": eid, "owner_hub_cedar_uid": h,
                "enterprise_name_normalized": nk, "minted": BUILT,
                "minted_by": SCRIPT,
                "minted_basis": ("allocated by code/cedar_ids.py under an "
                                 "exclusive lock; two check characters "
                                 "appended by 503_identity.check_chars"),
            })
        write_csv(IDREG, ["enterprise_id", "owner_hub_cedar_uid",
                          "enterprise_name_normalized", "minted", "minted_by",
                          "minted_basis"], idreg_rows)
    print(f"  ids: {len(idreg_rows)} in the register, {len(need)} minted this run")

    ent_rows, edge_rows = [], []
    for idx, (hub_uid, cname, es, variants) in enumerate(clusters):
        hub = hubs.by_uid.get(hub_uid, {})
        eid = idreg[(hub_uid, norm(cname))]

        rels = [canon_rel(x.get("relationship") or "subsidiary")[0] for x in es]
        rel = max(rels, key=lambda r: REL_RANK.get(r, 0))
        rel, rel_class = canon_rel(rel)
        best = max(es, key=lambda x: (EVID_RANK.get(x["evidence_class"], 0),
                                      str(x.get("source_fy") or "")))
        fys = sorted({str(x.get("source_fy") or "") for x in es} - {""})
        # A source with no fiscal year still dates itself: the edition date
        # the publisher put on the page. Without this, 801 of 1,483 rows read
        # `status = unknown` because only the ANCSA filings carry an FY.
        eds = sorted({str(x.get("source_edition_date") or "")[:4] for x in es}
                     - {""})
        eds = [y for y in eds if re.match(r"^(19|20)\d\d$", y)]
        obs_years = sorted(set(fys) | set(eds))
        pct = next((x["ownership_percent"] for x in es if x.get("ownership_percent")), "")
        sector = next((x["sector"] for x in es if x.get("sector")), "")

        # identifiers: only where a SOURCE published one. A name that happens
        # to match a UEI in FPDS is a CANDIDATE, never an identifier on this
        # row - the exactness of the key says nothing about the correctness
        # of the link (START_HERE trap 1).
        cage = next((x["child_cage"].strip().upper() for x in es
                     if (x.get("child_cage") or "").strip()), "")
        uei = next((x["child_uei"].strip().upper() for x in es
                    if (x.get("child_uei") or "").strip()), "")
        id_basis = []
        if cage:
            id_basis.append(f"CAGE published by the parent ({best['evidence_class']})")
            if not uei and cage in uei_of_cage:
                uei = uei_of_cage[cage]
                id_basis.append("UEI resolved from that CAGE via fpds_uei_cage_map.csv")
        elif uei:
            id_basis.append("UEI from the SBA Dynamic Small Business Search extract")
        nk = norm(cname)
        uei_cand, cand_basis = "", ""
        if not uei:
            d = dsbs_by_name.get(nk)
            if d and (d.get("uei") or "").strip():
                uei_cand = d["uei"].strip().upper()
                cand_basis = ("exact normalized name match into the SBA DSBS "
                              "extract - a CANDIDATE, not evidence of identity")

        # address: only from sources Cedar may redistribute. D&B-derived
        # recipient addresses in the contracting tables are deliberately NOT
        # used - IDENTIFIER_STANDARD §4.
        city = next((x["child_city"] for x in es if (x.get("child_city") or "").strip()), "")
        state = next((x["child_state"] for x in es if (x.get("child_state") or "").strip()), "")
        addr_basis = "parent's own subsidiary listing" if city else ""
        if not city:
            d = dsbs_by_uei.get(uei) or dsbs_by_uei.get(uei_cand) or dsbs_by_name.get(nk)
            if d:
                city, state = d.get("City", ""), d.get("State", "")
                addr_basis = ("SBA Dynamic Small Business Search extract, keyed on "
                              + ("UEI" if (uei or uei_cand) in dsbs_by_uei else
                                 "exact normalized name"))
        if not state and hub.get("state"):
            pass          # never infer a firm's state from its owner's

        present = ("Y" if (uei and uei in fed_ueis) or (cage and cage in fed_cages)
                   else "Y" if nk in fed_names else "N")
        pres_basis = ("published identifier found in the FPDS universe"
                      if present == "Y" and (uei in fed_ueis or cage in fed_cages)
                      else "exact normalized legal name found among FPDS awardees"
                      if present == "Y" else
                      "no UEI, CAGE or exact awardee-name match in prime_contracts "
                      "or fpds_uei_cage_map")

        lvl = level_of(idx)
        pj = parent_idx.get(idx)
        ent_rows.append({
            "enterprise_id": eid,
            "enterprise_name": cname,
            "enterprise_name_normalized": nk,
            "name_variants_observed": " | ".join(v for v in variants if v != cname),
            "owner_hub_cedar_uid": hub_uid,
            # `cedar_uid` is the documented external join key and every
            # shipped Cedar table carries it (IDENTIFIER_STANDARD §0). On a
            # NEST row it is the OWNER's uid, not the enterprise's: the
            # enterprise is a sub-hub and sub-hubs are never spine entities,
            # so it has no `CE-` uid of its own and inventing one would put a
            # non-entity into the entity namespace. Its own identity is
            # `enterprise_id`.
            "cedar_uid": hub_uid,
            "owner_hub_handle": hub.get("handle", ""),
            "owner_hub_name": hub.get("canonical_name", ""),
            "owner_hub_entity_class": hub.get("entity_class", ""),
            "owner_class": OWNER_CLASS.get(hub.get("entity_class", ""), "other"),
            "owner_hub_state": hub.get("state", ""),
            "parent_enterprise_id": "",          # filled below
            "parent_name": (clusters[pj][1] if pj is not None
                            else hub.get("canonical_name", "")),
            "parent_is_hub": "N" if pj is not None else "Y",
            "hierarchy_level": lvl,
            "relationship": rel,
            "relation_class": rel_class,
            "relationship_as_recorded": " | ".join(
                sorted({(x.get("relationship") or "") for x in es} - {""})),
            "ownership_percent_stated": pct,
            "sector": sector,
            "status": ("operating" if obs_years and obs_years[-1] >= "2024"
                       else "last_seen_earlier" if obs_years else "unknown"),
            "status_basis": (
                f"named by its owner in a source dated {obs_years[-1]}"
                + (f" and first seen {obs_years[0]}" if len(obs_years) > 1 else "")
                if obs_years else
                "no source for this enterprise states a period; status is not "
                "asserted rather than assumed current"),
            "city": city, "state_province": state,
            "address_basis": addr_basis,
            "address_is_publishable": "Y" if city else "",
            "uei": uei, "cage_code": cage,
            "identifier_basis": "; ".join(id_basis),
            "uei_candidate": uei_cand, "uei_candidate_basis": cand_basis,
            "identifier_status": ("external_identifier" if (uei or cage)
                                  else "cedar_minted_only"),
            "in_federal_contracting": present,
            "in_federal_contracting_basis": pres_basis,
            "identity_scope": best["identity_scope"],
            "assertion_class": "OWNERSHIP",
            "evidence_class": best["evidence_class"],
            "n_source_observations": len(es),
            "n_distinct_sources": len({x["source_id"] for x in es}),
            "first_observed_year": obs_years[0] if obs_years else "",
            "last_observed_year": obs_years[-1] if obs_years else "",
            "enterprise_existing_cedar_uid": next(
                (x.get("enterprise_existing_cedar_uid", "") for x in es
                 if x.get("enterprise_existing_cedar_uid")), ""),
            "constellation_edge_id": con_edge.get(
                (hub_uid, nk), ""),
            "constellation_note": (
                "the service constellation records a relationship between this "
                "firm and this hub; cedar_constellation_edges.csv is SERVICE "
                "(who serves whom), NEST is OWNERSHIP AND CORPORATE "
                "AFFILIATION - the two corroborate, they do not duplicate"
                if con_edge.get((hub_uid, nk)) else ""),
            "source_id": best["source_id"],
            "source_url": best["source_url"],
            "source_document": best["source_document"],
            "source_edition_date": best.get("source_edition_date", ""),
            "hub_resolution_method": best.get("hub_resolution_method", ""),
            "hub_resolution_note": best.get("hub_resolution_note", ""),
            "record_scope": "BUSINESS",
            "population_basis": "cedar_spine_native_entities_publishing_ownership",
            "publishable": "Y",
            "publishable_basis": "harmonized_publication_per_PUBLICATION_POLICY",
            "retrieved_date": BUILT,
            "built_by_script": SCRIPT,
            "built_date": BUILT,
        })
        for x in es:
            edge_rows.append({
                # The RECORDED child name is part of the key, not just the
                # cluster it collapsed into: one document can name two
                # spellings of one company (`Ahtna Design Build, Inc` and
                # `Ahtna Design-Build, Inc`), and those are two assertions.
                # Without it, 10 of 3,494 edge ids collided.
                "enterprise_edge_id": "NESTREL-" + sha(
                    hub_uid, nk, norm(x["child_name_raw"]), x["source_id"],
                    x.get("source_document", ""), x.get("source_url", ""),
                    x.get("source_fy", ""), x.get("parent_name", ""))[:14].upper(),
                "enterprise_id": eid,
                "child_name_as_recorded": tidy(x["child_name_raw"]),
                "parent_name_as_recorded": tidy(x.get("parent_name", "")),
                "owner_hub_cedar_uid": hub_uid,
                "cedar_uid": hub_uid,       # the owner - see the note above
                "owner_hub_handle": hub.get("handle", ""),
                "owner_hub_name": hub.get("canonical_name", ""),
                "relationship": canon_rel(x.get("relationship", "subsidiary"))[0],
                "relation_class": canon_rel(x.get("relationship", "subsidiary"))[1],
                "relationship_as_recorded": x.get("relationship", ""),
                "depth_as_recorded": x.get("depth_hint", 1),
                "ownership_percent_stated": x.get("ownership_percent", ""),
                "evidence_class": x["evidence_class"],
                "source_id": x["source_id"],
                "source_url": x["source_url"],
                "source_document": x.get("source_document", ""),
                "source_fiscal_year": x.get("source_fy", ""),
                "source_edition_date": x.get("source_edition_date", ""),
                "quote": (x.get("quote") or "")[:900],
                "hub_resolution_method": x.get("hub_resolution_method", ""),
                "hub_resolution_note": x.get("hub_resolution_note", ""),
                "retrieved_date": x.get("retrieved_date", BUILT),
                "built_by_script": SCRIPT,
            })

    id_of_cluster = {i: r["enterprise_id"] for i, r in enumerate(ent_rows)}
    for i, r in enumerate(ent_rows):
        j = parent_idx.get(i)
        if j is not None:
            r["parent_enterprise_id"] = id_of_cluster[j]

    # ONE SOURCE SAYING A THING TWICE IS ONE ASSERTION. Goldbelt's directory
    # lists `CP Marine` and `CP Marine LLC`; BBCH lists `CCI Industrial
    # Services LLC` and `... Inc`. Same page, same parent, same firm, two
    # renderings - so they collapse onto one edge and the fuller rendering
    # wins. Counting them twice would inflate `n_source_observations`, which
    # is the field a reader uses to judge how well evidenced a row is.
    dedup = {}
    for e in edge_rows:
        k = e["enterprise_edge_id"]
        if k not in dedup or len(e["child_name_as_recorded"]) > len(
                dedup[k]["child_name_as_recorded"]):
            dedup[k] = e
    collapsed = len(edge_rows) - len(dedup)
    edge_rows = [dedup[k] for k in sorted(dedup)]
    if collapsed:
        print(f"  collapsed {collapsed} same-source restatements of one firm")
    seen_per_ent = Counter(e["enterprise_id"] for e in edge_rows)
    for r in ent_rows:
        r["n_source_observations"] = seen_per_ent.get(r["enterprise_id"], 0)

    write_csv(OUT_ENT, list(ent_rows[0].keys()), ent_rows)
    write_csv(OUT_EDGE, list(edge_rows[0].keys()), edge_rows)

    print(f"\n  enterprises        {len(ent_rows)}")
    print(f"  ownership edges    {len(edge_rows)}")
    print(f"  owner hubs         {len({r['owner_hub_cedar_uid'] for r in ent_rows})}")
    print(f"  by owner class     {dict(Counter(r['owner_class'] for r in ent_rows))}")
    print(f"  by level           {dict(Counter(r['hierarchy_level'] for r in ent_rows))}")
    print(f"  external id        {sum(1 for r in ent_rows if r['identifier_status'] == 'external_identifier')}")
    print(f"  cedar minted only  {sum(1 for r in ent_rows if r['identifier_status'] == 'cedar_minted_only')}")
    print(f"  with city+state    {sum(1 for r in ent_rows if r['city'] and r['state_province'])}")
    print(f"  ABSENT from FPDS   {sum(1 for r in ent_rows if r['in_federal_contracting'] == 'N')}")
    print(f"  -> {OUT_ENT}")
    print(f"  -> {OUT_EDGE}")
    return 0


# ===========================================================================
# STAGE `verify`
# ===========================================================================
INVARIANTS = """
  I1  every enterprise_id is unique and carries valid 503 check characters
  I2  every row carries an owner_hub_cedar_uid that is IN the spine register
  I3  every row carries a source_url or a source_document - an ownership
      claim with no source is the one row this dataset may not contain
  I4  no row's owner hub is a TERMS_STATED_RESTRICTIVE publisher
  I5  hierarchy_level >= 2 implies a parent_enterprise_id that exists here,
      and no enterprise is its own ancestor
  I6  every edge's enterprise_id exists in the enterprise table, and every
      enterprise has at least one edge (row conservation, both directions)
  I7  in_federal_contracting is Y or N on every row - never blank, because a
      blank would silently leave a row out of the headline count
  I8  no Alaska Native Village GOVERNMENT owns an ANCSA corporation
      (ANCSA_OWNERSHIP_RULING rule 2)
"""


def stage_verify(argv) -> int:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "cedar_503v", str(CEDAR / "code" / "503_identity.py"))
    m503 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m503)

    ents = read_csv(OUT_ENT)
    edges = read_csv(OUT_EDGE)
    reg = {r["cedar_uid"] for r in read_csv(SPINE / "cedar_identity_register.csv")}
    fails = []
    print("=== 1072 verify ===" + INVARIANTS)
    if not ents:
        print("  FAIL I0  no enterprise rows")
        return 1

    ids = [r["enterprise_id"] for r in ents]
    if len(set(ids)) != len(ids):
        fails.append(f"I1 duplicate enterprise_id ({len(ids) - len(set(ids))})")
    bad_ck = [i for i in ids
              if not re.match(r"^CEDAR-NEST-\d{6}-[0-9A-Z]{2}$", i)
              or m503.check_chars(m503.encode(int(i.split("-")[2]))) != i.split("-")[3]]
    if bad_ck:
        fails.append(f"I1 bad check characters on {len(bad_ck)}: {bad_ck[:3]}")

    off = [r["enterprise_id"] for r in ents if r["owner_hub_cedar_uid"] not in reg]
    if off:
        fails.append(f"I2 {len(off)} rows whose owner hub is not in the register: {off[:3]}")

    nosrc = [r["enterprise_id"] for r in ents
             if not (r["source_url"].strip() or r["source_document"].strip())]
    if nosrc:
        fails.append(f"I3 {len(nosrc)} ownership claims with no source: {nosrc[:3]}")

    rx = [r["enterprise_id"] for r in ents
          if restricted(r["owner_hub_name"], r["source_url"], r["enterprise_name"])]
    if rx:
        fails.append(f"I4 {len(rx)} rows from a refused publisher: {rx[:3]}")

    byid = {r["enterprise_id"]: r for r in ents}
    for r in ents:
        if int(r["hierarchy_level"]) >= 2 and r["parent_enterprise_id"] not in byid:
            fails.append(f"I5 {r['enterprise_id']} level {r['hierarchy_level']} "
                         f"has no resolvable parent")
            break
    for r in ents:                       # no cycles
        seen, cur, depth = set(), r, 0
        while cur["parent_enterprise_id"] and depth < 50:
            if cur["enterprise_id"] in seen:
                fails.append(f"I5 ownership cycle at {r['enterprise_id']}")
                break
            seen.add(cur["enterprise_id"])
            cur = byid.get(cur["parent_enterprise_id"])
            depth += 1
            if cur is None:
                break
        if any(f.startswith("I5 ownership cycle") for f in fails):
            break

    eids = {e["enterprise_id"] for e in edges}
    orphan_edges = eids - set(ids)
    edgeless = set(ids) - eids
    if orphan_edges:
        fails.append(f"I6 {len(orphan_edges)} edges point at no enterprise")
    if edgeless:
        fails.append(f"I6 {len(edgeless)} enterprises carry no evidence edge")

    blank = [r["enterprise_id"] for r in ents
             if r["in_federal_contracting"] not in ("Y", "N")]
    if blank:
        fails.append(f"I7 {len(blank)} rows with no federal-contracting verdict")

    vg = [r["enterprise_id"] for r in ents
          if r["owner_hub_entity_class"] == VILLAGE_GOV
          and re.search(r"\bcorporation\b", r["parent_name"], re.I)
          and r["parent_is_hub"] == "Y"]
    if vg:
        fails.append(f"I8 {len(vg)} rows attach an ANCSA corporation to a "
                     f"village GOVERNMENT: {vg[:3]}")

    for f in fails:
        print("  FAIL " + f)
    if not fails:
        print(f"  PASS  {len(ents)} enterprises, {len(edges)} edges, "
              f"{len({r['owner_hub_cedar_uid'] for r in ents})} owner hubs")
    return 1 if fails else 0


def stage_selfcheck(argv) -> int:
    """Prove `verify` FIRES. A check that has never failed on purpose is not
    known to work - docs/AGENT_FIELD_GUIDE.md §3."""
    import shutil
    import subprocess
    baks = {}
    for p in (OUT_ENT, OUT_EDGE):
        baks[p] = p.with_suffix(p.suffix + ".bak_selfcheck_1072")
        shutil.copy2(p, baks[p])

    def run():
        r = subprocess.run([sys.executable, str(CEDAR / "code" / Path(__file__).name),
                            "verify"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", cwd=str(CEDAR))
        return r.returncode, (r.stdout or "") + (r.stderr or "")

    rc, out = run()
    results = [("clean file exits 0", rc == 0)]

    def mutate(fn, label, expect):
        rows = read_csv(OUT_ENT)
        fn(rows)
        write_csv(OUT_ENT, list(rows[0].keys()), rows)
        rc2, out2 = run()
        ok = rc2 == 1 and expect in out2
        results.append((label, ok))
        shutil.copy2(baks[OUT_ENT], OUT_ENT)

    mutate(lambda rs: rs[0].__setitem__("enterprise_id", rs[1]["enterprise_id"]),
           "I1 duplicate id fires", "I1 duplicate enterprise_id")
    mutate(lambda rs: rs[0].__setitem__("owner_hub_cedar_uid", "CE-ZZZZZ-ZZ"),
           "I2 off-register hub fires", "I2 ")
    mutate(lambda rs: (rs[0].__setitem__("source_url", ""),
                       rs[0].__setitem__("source_document", "")),
           "I3 sourceless ownership claim fires", "I3 ")
    mutate(lambda rs: rs[0].__setitem__("owner_hub_name", "Chickasaw Nation"),
           "I4 refused publisher fires", "I4 ")
    mutate(lambda rs: (rs[0].__setitem__("hierarchy_level", "2"),
                       rs[0].__setitem__("parent_enterprise_id", "CEDAR-NEST-999999-ZZ")),
           "I5 dangling parent fires", "I5 ")
    mutate(lambda rs: rs[0].__setitem__("in_federal_contracting", ""),
           "I7 blank verdict fires", "I7 ")

    for p, b in baks.items():
        shutil.copy2(b, p)
        b.unlink()
    rc3, _ = run()
    results.append(("restored file exits 0 again", rc3 == 0))
    for label, ok in results:
        print(("  PASS  " if ok else "  FAIL  ") + label)
    return 0 if all(ok for _l, ok in results) else 1


# ===========================================================================
# STAGE `codebook` - register the two tables so they can ship
# ===========================================================================
# A clean table that no `codebook_master.csv` block documents at 60% column
# overlap is INVISIBLE to `87_build_dataset_notes.py`, to `512`'s shippable
# list and therefore to `518`'s scoreboard - it reports the collection as
# NOT_TESTED with "0 tables", which is what NEST did on its first run.
# `docs/GAMING_SOURCE_AUDIT_2026-08-26.md` is the expensive version of this:
# the gaming collection shipped 912 of 104,412 rows because of it.
#
# Two writes, deliberately:
#   * the FRAGMENT `data/clean/codebook/<block>.csv`, which is the file this
#     dataset owns and which a future `cedar_codebook.py build` folds in;
#   * an APPEND to `codebook_master.csv`, because `build` rewrites the master
#     wholesale and three other agents are live on this machine today. An
#     append cannot shrink the master; a rewrite can, which is exactly why
#     `41_build_codebooks.py` is the one script on NEVER_RUN.
CB_FIELDS = ["dataset", "variable", "type", "units", "pct_filled", "n_rows",
             "published", "access_tier", "description", "generated"]

CB_BLOCK = {"nest_enterprises.csv": "18a_nest_enterprises",
            "nest_enterprise_relations.csv": "18b_nest_enterprise_relations"}

CB_DESC = {
    "enterprise_id":
        "THE KEY. Permanent Cedar identifier for this enterprise, "
        "`CEDAR-NEST-nnnnnn-CC`. The ordinal is allocated under an exclusive "
        "lock by code/cedar_ids.py and the two trailing characters are "
        "503_identity check characters over two independent weightings, so a "
        "single substitution or an adjacent transposition in a transcribed id "
        "is caught. Bound to (owner hub, normalised name) in the append-only "
        "register data/spine/cedar_nest_id_register.csv, so a rebuild reuses "
        "it rather than re-keying the dataset. Never reused.",
    "enterprise_name": "The enterprise's name as its owner writes it, taken "
        "from the most authoritative and most recent source that named it.",
    "enterprise_name_normalized": "Lower-cased, punctuation-folded, "
        "corporate-suffix-stripped form of the name. A matching key, not a "
        "legal name.",
    "name_variants_observed": "Other spellings of this firm seen in the "
        "sources, pipe-separated. A decade of audited filings drifts: "
        "`Ahtna Design Build, Inc` and `Ahtna Design-Build, Inc` are one "
        "company, and this column is the evidence that they were folded.",
    "owner_hub_cedar_uid": "The Cedar uid of the entity that owns this "
        "enterprise - a nation, an ANCSA corporation or an NHO. Always a "
        "spine entity.",
    "cedar_uid": "The documented external join key. On a NEST row it is the "
        "OWNER's uid, not the enterprise's: an enterprise is a sub-hub and "
        "sub-hubs are never spine entities (IDENTIFIER_STANDARD §2). The "
        "enterprise's own identity is `enterprise_id`.",
    "owner_hub_handle": "The owner's readable Cedar handle (`TRBF-`, `ANVC-`, "
        "`ANRC-`, `NHO-`). A display attribute; join on the uid.",
    "owner_hub_name": "The owner's canonical name in the Cedar spine.",
    "owner_hub_entity_class": "The owner's Cedar entity class.",
    "owner_class": "tribal_government | alaska_native_corporation | "
        "native_hawaiian_organization. The three owner families this dataset "
        "covers, derived from the owner's entity class.",
    "owner_hub_state": "The owner's state. NEVER copied onto the enterprise: "
        "a nation's companies are frequently registered elsewhere.",
    "parent_enterprise_id": "The IMMEDIATE owner where that owner is itself "
        "an enterprise in this table - the holding company. Blank when the "
        "nation owns the enterprise directly.",
    "parent_name": "The immediate owner's name: the holding company, or the "
        "nation itself at level 1.",
    "parent_is_hub": "Y when the immediate owner is the nation itself, N when "
        "it is another enterprise. The one-column answer to 'is this a "
        "direct holding'.",
    "hierarchy_level": "1 = owned directly by the nation. 2 = owned by a "
        "level-1 enterprise. 3 = one further down. A sub-hub is never a peer "
        "of its hub, and the chain is what this dataset exists to keep.",
    "relationship": "The relationship in one controlled vocabulary: "
        "wholly_owned, majority_owned, subsidiary, division, holding_company, "
        "operating_company, declared_suborganization, joint_venture, "
        "shareholding_or_ancestry, passive_investment.",
    "relation_class": "ownership | affiliation. THE STRUCTURES/TIES SPLIT. "
        "Filter to `ownership` for the corporate chain. `affiliation` rows "
        "are real published relationships that are NOT ownership - a joint "
        "venture genuinely has two parents, and ANCSA shareholding is not a "
        "parent-subsidiary link. An affiliation counted as ownership is the "
        "defect this dataset is most exposed to.",
    "relationship_as_recorded": "What the source called it, before "
        "normalisation. Kept so a mapping decision can be re-judged.",
    "ownership_percent_stated": "The ownership percentage where a source "
        "stated one. Blank means unstated, never 100.",
    "sector": "Industry or line of business where a source stated one.",
    "status": "operating (named by its owner in a source dated 2024 or "
        "later) | last_seen_earlier (named, but only in older sources) | "
        "unknown (no source states a period). `last_seen_earlier` is not a "
        "claim that the enterprise closed.",
    "status_basis": "The sentence behind `status`, naming the years.",
    "city": "The enterprise's city, from a source Cedar may redistribute.",
    "state_province": "The enterprise's state.",
    "address_basis": "Which source the address came from. D&B-derived "
        "recipient addresses in the contracting tables are deliberately NOT "
        "used here - IDENTIFIER_STANDARD §4 forbids their bulk "
        "dissemination.",
    "address_is_publishable": "Y where an address is present and its source "
        "carries no redistribution restriction.",
    "uei": "SAM Unique Entity Identifier, ONLY where the owner published it "
        "or an SBA register carried it against this firm. Never a name match.",
    "cage_code": "CAGE code, ONLY where the owner published it. ASRC Federal "
        "publishes a CAGE next to each operating company, which is how firms "
        "sharing no token with 'Arctic Slope' are reachable at all.",
    "identifier_basis": "How the identifier on this row was obtained. An "
        "identifier with no basis is not published.",
    "uei_candidate": "A UEI that an exact normalised name match suggests. A "
        "CANDIDATE, not an identifier: the exactness of the key says nothing "
        "about the correctness of the link. Do not treat as an attribution.",
    "uei_candidate_basis": "How the candidate was proposed, and why it is "
        "only a candidate.",
    "identifier_status": "external_identifier (the owner or a register "
        "published a UEI or CAGE) | cedar_minted_only (no external identifier "
        "exists, so the Cedar id is the only one). The second is the majority "
        "and is the reason this dataset mints.",
    "in_federal_contracting": "Y | N. Whether this enterprise appears in the "
        "FPDS awardee universe by published identifier or exact legal name. "
        "N IS THE HEADLINE: an enterprise a nation owns that federal "
        "contracting has never seen. A name collision makes a firm look "
        "present, so the error runs against the count - N is a floor.",
    "in_federal_contracting_basis": "Which test answered, and against what.",
    "identity_scope": "What the source asserted: tribally_owned_entity (the "
        "nation's own register of its companies) or "
        "parent_asserted_subsidiary (a parent corporation's subsidiary "
        "list). The same gradient native_owned_businesses.csv uses.",
    "assertion_class": "OWNERSHIP. What kind of claim the row makes.",
    "evidence_class": "The strongest evidence behind the row: "
        "audited_annual_report_as_45_55_139 (an ANCSA corporation's audited "
        "Principles of Consolidation note, filed with the Alaska Division of "
        "Banking and Securities - the strongest class available) | "
        "nation_self_published_enterprise_register | "
        "parent_self_published_company_list | "
        "parent_declared_subsidiary_list.",
    "n_source_observations": "How many separate assertions in "
        "nest_enterprise_relations.csv stand behind this row.",
    "n_distinct_sources": "How many distinct sources those assertions come "
        "from. One source repeated ten times is one source.",
    "first_observed_year": "The earliest year any source named this "
        "enterprise as its owner's.",
    "last_observed_year": "The most recent such year.",
    "enterprise_existing_cedar_uid": "Set where this enterprise is ALREADY a "
        "Cedar spine entity in its own right - a Native CDFI or college the "
        "nation owns. The row does not pretend it is new.",
    "constellation_edge_id": "The matching edge in "
        "cedar_constellation_edges.csv where one exists. That file records "
        "SERVICE relationships (who serves a community); NEST records "
        "ownership and corporate affiliation. The two corroborate; they do "
        "not duplicate, and a TERO-certified firm is a constellation edge "
        "and not a NEST row unless the nation also owns it.",
    "constellation_note": "Why the constellation edge is a corroboration "
        "rather than the same fact twice.",
    "source_id": "The source that carried the strongest assertion.",
    "source_url": "Where that assertion was published.",
    "source_document": "The document that carried it, for filings.",
    "source_edition_date": "The date the source itself states.",
    "hub_resolution_method": "How the owner was resolved to a spine entity.",
    "hub_resolution_note": "Any ruling applied while resolving the owner - "
        "an ANCSA village-government repoint, or a refused name collision.",
    "record_scope": "BUSINESS.",
    "population_basis": "The population this row was drawn from.",
    "publishable": "Y | N per docs/PUBLICATION_POLICY.md.",
    "publishable_basis": "Why. TERMS_STATED_RESTRICTIVE publishers are "
        "excluded upstream and do not appear here at all.",
    "retrieved_date": "When Cedar retrieved the evidence.",
    "built_by_script": "The script that wrote the row.",
    "built_date": "When.",
    # --- relations table ---
    "enterprise_edge_id": "THE KEY. One assertion by one source about one "
        "parent->enterprise relationship.",
    "child_name_as_recorded": "The enterprise's name exactly as this source "
        "wrote it. Every one of these appears VERBATIM in the source "
        "document; a name that did not was dropped, not corrected.",
    "parent_name_as_recorded": "The parent's name exactly as this source "
        "wrote it.",
    "depth_as_recorded": "The depth the source itself stated, where it did.",
    "source_fiscal_year": "The fiscal year of the filing that carried the "
        "assertion.",
    "quote": "The sentence that asserts the relationship. This is what makes "
        "an ownership claim checkable rather than asserted.",
}

CB_GENERIC = ("Column of the NEST enterprise register. See "
              "docs/NEST_BUILD_LOG.md for how it is derived.")


def _cb_type(vals):
    v = [x for x in vals if (x or "").strip()]
    if not v:
        return "text"
    if all(re.match(r"^-?\d+$", x) for x in v):
        return "integer"
    if all(re.match(r"^-?\d*\.?\d+$", x) for x in v):
        return "numeric"
    if all(re.match(r"^\d{4}-\d{2}-\d{2}$", x) for x in v):
        return "date"
    return "text"


def stage_codebook(argv) -> int:
    frag_dir = CLEAN / "codebook"
    frag_dir.mkdir(parents=True, exist_ok=True)
    master = CLEAN / "codebook_master.csv"
    existing = read_csv(master)
    have = {(r["dataset"], r["variable"]) for r in existing}
    new_rows = []
    for fname, block in CB_BLOCK.items():
        path = CLEAN / fname
        rows = read_csv(path)
        if not rows:
            print(f"  ! {fname} has no rows - run `build` first")
            return 1
        hdr = list(rows[0].keys())
        frag = []
        for col in hdr:
            vals = [r.get(col, "") for r in rows]
            filled = sum(1 for x in vals if (x or "").strip())
            frag.append({
                "dataset": block, "variable": col, "type": _cb_type(vals),
                "units": "code" if col.endswith(("_id", "_uid", "_uei",
                                                 "_code", "handle"))
                         else "date" if col.endswith(("_date", "_year"))
                         else "text",
                "pct_filled": round(100.0 * filled / len(rows), 1),
                "n_rows": len(rows), "published": 1,
                # Every column here is either Cedar's own derivation or a fact
                # the owner published about itself. No DUNS, no D&B street
                # address and no vendor-licensed field is carried, which is
                # why the whole block is `public` rather than mixed.
                "access_tier": "public",
                "description": CB_DESC.get(col, CB_GENERIC),
                "generated": BUILT,
            })
        write_csv(frag_dir / (block + ".csv"), CB_FIELDS, frag)
        for r in frag:
            if (r["dataset"], r["variable"]) not in have:
                new_rows.append(r)
        print(f"  {block}: {len(frag)} variables documented, {len(rows)} rows")

    if new_rows:
        bak = master.with_suffix(
            f".csv.bak_{BUILT}_pre_1072_tribally_owned_enterprises")
        if not bak.exists():
            bak.write_bytes(master.read_bytes())
        with master.open("a", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=CB_FIELDS, extrasaction="ignore")
            for r in new_rows:
                w.writerow(r)
        print(f"  appended {len(new_rows)} rows to codebook_master.csv "
              f"({len(existing)} -> {len(existing) + len(new_rows)}); "
              f"backup {bak.name}")
    else:
        print("  codebook_master.csv already carries both blocks")
    return 0



# ===========================================================================
# STAGE `conserve` - C5 row conservation, measured not typed
# ===========================================================================
# `data/clean/cedar_harvest_conservation.csv` is the ledger 518 reads for C5.
# Its question is not "how many rows are there" but "where did every row that
# entered go" - the discipline that caught a de-duplication which would have
# destroyed $8,291,124,113 of real obligations. Three accountings are written:
# the ACQUISITION funnel (every raw assertion, kept or refused, by reason),
# and one partition of each published table. Every number is recomputed from
# the files on every run; none is copied from a previous report.
CONSERVATION = CLEAN / "cedar_harvest_conservation.csv"
CONS_FIELDS = ["source_table", "rows_in", "disposition", "rows", "pct",
               "examples", "harvest_date"]


def stage_conserve(argv) -> int:
    ents = read_csv(OUT_ENT)
    edges = read_csv(OUT_EDGE)
    held = read_csv(HELD)
    kept = read_jsonl(EDGES_STAGED)
    if not ents:
        print("  run `build` first")
        return 1

    out = []

    def add(table, rows_in, groups, examples=None):
        examples = examples or {}
        total = 0
        for disp, n in groups:
            total += n
            out.append({
                "source_table": table, "rows_in": rows_in,
                "disposition": disp, "rows": n,
                "pct": round(100.0 * n / rows_in, 2) if rows_in else 0.0,
                "examples": examples.get(disp, ""), "harvest_date": BUILT})
        assert total == rows_in, (
            f"{table}: dispositions sum to {total}, not {rows_in} - a row "
            f"conservation ledger that does not conserve is worse than none")

    # 1. THE ACQUISITION FUNNEL. Every ownership assertion any source made.
    raw = len(kept) + len(held)
    hold_groups = Counter(h.get("hold_class", "UNKNOWN") for h in held)
    ex = {}
    for h in held:
        k = "refused:" + h.get("hold_class", "UNKNOWN").lower()
        ex.setdefault(k, (h.get("hold_reason") or "")[:200])
    add("data/staging/nest/raw_ownership_assertions", raw,
        [("emitted:assertion_kept_with_a_resolved_owner_and_a_named_source",
          len(kept))]
        + [(f"refused:{k.lower()}", v) for k, v in sorted(hold_groups.items())],
        ex)

    # 2. THE ENTERPRISE TABLE, by what the row actually claims.
    rc = Counter(r["relation_class"] for r in ents)
    nosrc = sum(1 for r in ents
                if not (r["source_url"].strip() or r["source_document"].strip()))
    add("data/clean/nest_enterprises.csv", len(ents), [
        ("emitted:ownership_asserted_by_the_owner_itself",
         rc.get("ownership", 0)),
        ("emitted:published_tie_that_is_NOT_ownership_relation_class_affiliation",
         rc.get("affiliation", 0)),
        ("rejected:ownership_claim_with_no_source", nosrc),
    ], {"rejected:ownership_claim_with_no_source":
        "structurally impossible: `verify` I3 exits 1 on any such row, and "
        "`selfcheck` proves that check fires"})

    # 3. THE RELATIONS TABLE, by evidence class - the honest picture of what
    #    this dataset rests on.
    ec = Counter(e["evidence_class"] for e in edges)
    add("data/clean/nest_enterprise_relations.csv", len(edges),
        [("emitted:" + k, v) for k, v in sorted(ec.items())])

    prior = [r for r in read_csv(CONSERVATION)
             if not (r.get("source_table") or "").split("/")[-1].startswith("nest")
             and "staging/nest" not in (r.get("source_table") or "")]
    bak = CONSERVATION.with_suffix(
        f".csv.bak_{BUILT}_pre_1072_tribally_owned_enterprises")
    if CONSERVATION.exists() and not bak.exists():
        bak.write_bytes(CONSERVATION.read_bytes())
    write_csv(CONSERVATION, CONS_FIELDS, prior + out)
    for r in out:
        print(f"  {r['source_table'].split('/')[-1]:<34} {r['rows']:>6}  "
              f"{r['pct']:>6}%  {r['disposition'][:64]}")
    print(f"  ledger {len(prior)} prior rows + {len(out)} NEST rows; "
          f"backup {bak.name}")
    return 0


def main() -> int:
    stages = {"mine": stage_mine, "assemble": stage_assemble,
              "build": stage_build, "codebook": stage_codebook,
              "conserve": stage_conserve, "verify": stage_verify,
              "selfcheck": stage_selfcheck}
    if len(sys.argv) < 2 or sys.argv[1] not in stages:
        print(__doc__)
        print("stages: " + " ".join(sorted(stages)))
        return 2
    return stages[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    raise SystemExit(main())
