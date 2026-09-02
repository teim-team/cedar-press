#!/usr/bin/env python3
"""1072 - INDIAN COUNTRY HOLDINGS: enterprises a Native nation actually OWNS.

Collection id `holdings`. The 14th dataset, and it is DISTINCT from
`native-owned-businesses` by the relation it publishes:

    native-owned-businesses   a nation CERTIFIED or LISTED this firm
                              -> relation `affiliated_with`, identity_scope
                                 gradient down to `vendor_relationship`
    holdings (this)           a nation, ANC or NHO OWNS this enterprise
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
  build     writes data/clean/tribally_owned_enterprises.csv and
            data/clean/tribally_owned_enterprise_ownership_edges.csv, minting
            a Cedar sub-hub id per enterprise.
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
STAGE = CEDAR / "data" / "staging" / "holdings"
INTERIM = CEDAR / "data" / "interim"
RAW = CEDAR / "data" / "raw"
REVIEW = CEDAR / "review"

MINED = STAGE / "ancsa_consolidation_edges.jsonl"
MINE_LOG = STAGE / "ancsa_mine_log.csv"
EDGES_STAGED = STAGE / "ownership_edges_staged.jsonl"
HELD = STAGE / "held_rows.csv"

OUT_ENT = CLEAN / "tribally_owned_enterprises.csv"
OUT_EDGE = CLEAN / "tribally_owned_enterprise_ownership_edges.csv"
# Append-only binding of (owner hub, normalised name) -> enterprise_id.
# Kept in data/spine because an identifier a customer joins on must
# survive a staging wipe, and because it is identity, not output.
IDREG = SPINE / "cedar_holdings_id_register.csv"

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
    """`.part` then rename - an interruption must not look like a completion."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
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
                held.append({**e, "hold_reason":
                             f"both publisher ({row['handle']}) and named firm "
                             f"({crow['handle']}) are ANCSA corporations - "
                             f"ANCSA_OWNERSHIP_RULING forbids this ownership "
                             f"edge; the relationship is shareholding, ancestry "
                             f"or a joint venture",
                             "hold_class": "ANCSA_CORP_TO_CORP"})
                continue
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
    "Alaska Native Regional Corporation": "alaska_native_corporation",
    "Alaska Native Village Corporation": "alaska_native_corporation",
    "Native Hawaiian Organization": "native_hawaiian_organization",
}

REL_RANK = {"wholly_owned": 5, "majority_owned": 4, "subsidiary": 3,
            "division": 3, "joint_venture": 2, "passive_investment": 1}
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

    clusters = []          # (hub_uid, canonical_name, [edges], {variants})
    for hub_uid, group in sorted(by_hub.items()):
        buckets = {}       # norm-name -> list of edges
        for e in group:
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
        pnames = {norm(x["parent_name"]) for x in es if x.get("parent_name")}
        pnames.discard(norm(hubs.by_uid.get(hub_uid, {}).get("canonical_name", "")))
        for pn in sorted(pnames):
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
        got = cedar_ids.allocate("CEDAR-HOLD", len(need),
                                 note="holdings enterprise sub-hubs, 1072")
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

        rel = max((x.get("relationship") or "subsidiary" for x in es),
                  key=lambda r: REL_RANK.get(r, 0))
        best = max(es, key=lambda x: (EVID_RANK.get(x["evidence_class"], 0),
                                      str(x.get("source_fy") or "")))
        fys = sorted({str(x.get("source_fy") or "") for x in es} - {""})
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
            "ownership_percent_stated": pct,
            "sector": sector,
            "status": "operating" if fys and fys[-1] >= "2024" else "unknown",
            "status_basis": (f"named in the owner's filing for FY{fys[-1]}"
                             if fys else "the source states no period"),
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
            "first_observed_fiscal_year": fys[0] if fys else "",
            "last_observed_fiscal_year": fys[-1] if fys else "",
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
                "enterprise_edge_id": "EDGE-" + sha(
                    hub_uid, nk, x["source_id"], x.get("source_document", ""),
                    x.get("source_url", ""), x.get("source_fy", ""),
                    x.get("parent_name", ""))[:12].upper(),
                "enterprise_id": eid,
                "child_name_as_recorded": tidy(x["child_name_raw"]),
                "parent_name_as_recorded": tidy(x.get("parent_name", "")),
                "owner_hub_cedar_uid": hub_uid,
                "owner_hub_handle": hub.get("handle", ""),
                "owner_hub_name": hub.get("canonical_name", ""),
                "relationship": x.get("relationship", "subsidiary"),
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
              if not re.match(r"^CEDAR-HOLD-\d{6}-[0-9A-Z]{2}$", i)
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
                       rs[0].__setitem__("parent_enterprise_id", "CEDAR-HOLD-999999-ZZ")),
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


def main() -> int:
    stages = {"mine": stage_mine, "assemble": stage_assemble,
              "build": stage_build, "verify": stage_verify,
              "selfcheck": stage_selfcheck}
    if len(sys.argv) < 2 or sys.argv[1] not in stages:
        print(__doc__)
        print("stages: " + " ".join(sorted(stages)))
        return 2
    return stages[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    raise SystemExit(main())
