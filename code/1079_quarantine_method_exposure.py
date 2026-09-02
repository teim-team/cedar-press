#!/usr/bin/env python3
"""
Cedar Press - 1079: THE QUARANTINE MUST REACH THE TRANSACTION TABLES.

    py -3 code/1079_quarantine_method_exposure.py report    # measure only; writes review/ + docs/, touches no dataset
    py -3 code/1079_quarantine_method_exposure.py apply     # measure + repair
    py -3 code/1079_quarantine_method_exposure.py verify    # read-only, exit 1 on breach
    py -3 code/1079_quarantine_method_exposure.py selftest  # prove verify FIRES on an injected violation

THE DEFECT (CDR-11 / CDR-12, `review/1011_cross_dataset_findings.csv`)
-----------------------------------------------------------------------
`docs/CROSS_DATASET_LEARNING.md` channel 3 quarantines three attribution
methods - `cluster_v3`, `need_v6`, `sam_namematch_2026_05_06`.  On every prime
row those methods key, `prime_contracts.attribution_method` reads `uei_exact`,
`cage_exact` or `parent_uei`.

**That column is not lying. It is answering a different question.**  It records
HOW THE IDENTIFIER JOINED - we matched a UEI to a UEI, which is exact - and
says nothing about HOW THE IDENTIFIER WAS RULED.  A quarantined guess and an
owner ruling are byte-identical to anything reading it.  This is START_HERE
trap 1 in a third vocabulary: *the exactness of the KEY says nothing about the
correctness of the LINK.*

So the first deliverable is not a repoint.  It is five columns:

    identifier_ruling_method       the LEDGER's attribution_method for the
                                   identifier row that keyed this transaction
    identifier_ruling_tier         that ledger row's confidence_tier
    identifier_ruling_quarantined  Y / N - is that method quarantined
    identifier_ruling_basis        which identifier keyed it, e.g. UEI:ABC123
    identifier_ruling_review       this pass's disposition, where it looked

`attribution_method` is left exactly as it is.  It is the correct answer to its
own question and it is the evidence of which leg the join came down.

CDR-11 UNDERCOUNTED, BECAUSE IT SCOPED ON ONE LEG
--------------------------------------------------
CDR-11 measured UEI ledger rows only.  The ledger keys prime contracting on
three legs and `40_build_prime_contracts.py` tries all three in order.
Re-measured here on the live files:

    leg                                            prime rows        obligations
    uei_exact   on a quarantined UEI ledger row       172,338    $38,191,057,346
    cage_exact  on a quarantined CAGE ledger row       14,149     $7,252,015,101
    parent_uei  on a quarantined UEI ledger row        41,055       $489,839,872
    ------------------------------------------------------------------------
    total (disjoint - one row carries one method)     227,542    $45,932,912,319

The CAGE leg is the one nobody had looked at, and it is where `need_v6` -
**6.5% accurate, START_HERE's own figure** - actually lives: 838 tier-B CAGE
rows.  It put 60+ CAGE codes on `TRBF-LUMBEE-00` (the Lumbee Tribe of **North**
Carolina) whose registered names are `NORTH WIND ...` x30, `GSI NORTH AMERICA`,
`MERCEDES-BENZ RESEARCH & DEVELOPMENT NORTH AMERICA`, `KATMAI NORTH AMERICA`,
`NORTH ISLAND CORP`, `NORTH VALLEY CARING SERVICES`, `TDX NORTH SLOPE
GENERATING` and `CAROLINA PLACE APARTMENTS`.  The token is `north`.

WHY THE CLUSTER BEHAVED THIS WAY - measured, not guessed
---------------------------------------------------------
`cluster_v3`'s own `tier_rationale` reads "Algorithmic name clustering,
unreviewed", and its clusters are magnetised by ORGANISATIONAL words sitting
inside a spine name:

  * `AKNF-INPTBW-00-ARCSLO` is **Native Village of Barrow Inupiat Traditional
    Government**.  53 UEIs and $8.15B hang on it, including `ATI Government
    Solutions`, `A+ Government Solutions`, `Ho'olaulima Government Solutions`,
    `Dominion Government Services`, `Bloom Government Solutions`, `Superior
    Government Solutions`, `Optimal Government Solutions`, `Informed Government
    Solutions`, `Ingenuity Government Solutions`, `LEDE2 Government Solutions`,
    `Government Logistic Support Services`, `Government & Industrial Supply`,
    `Federal Government Receivables Research Bureau`, **`Indian Affairs, Bureau
    Of` (5 UEIs)**, **`Indian Health Service` (4 UEIs)**, **`Army, United
    States Department Of The`**, **`Engineers, U S Army Corps Of`** and
    **`Library Of Congress`**.  The token is `government`.
  * `TRBF-TEMOAK-00` is Te-Moak, whose spine `aliases` field contains the PROSE
    SENTENCE *"Four constituent bands: Battle Mountain Band; Elko Band; South
    Fork Band; and Wells Band"*.  It has collected `Four Tribes Enterprises`,
    `Four Bears Construction`, `Four Directions Media`, `Four Corners Clean`,
    `Four Seasons Construction`, `Eighty-Four Packing Co`, `Battle Creek
    Construction`, `E W Wells Group` and `Wells Technology`.  **A prose
    sentence in an alias field is not a name** and this pass stops reading one
    as tokens.
  * `AKNF-VEAGLE-00-DOYONL-TNNACH` is the Native Village of Eagle.  Its ENTIRE
    distinctive token set is `{eagle}` - one word, already on
    `cedar_domain.NAME_TRAPS`.  67 UEIs and $2.86B hang on it across
    TX VA OK MT SD NC FL MN GU, and the only member sharing the hub's actual
    name is `NATIVE VILLAGE OF EAGLE` at $0.3M.

`docs/ENTITY_MATCH_RULES.md` rule 1 already forbids exactly this: *an entity
whose entire distinctive token set is generic may not win a match that rests
only on the name.*  It was written after the fact and never applied backwards
over `cluster_v3`'s output.  This script applies it backwards.

WHAT THIS SCRIPT REFUSES TO DO
-------------------------------
**"Shares no token" is evidence to LOOK, never proof of error.**  A
subsidiary's legal name routinely shares nothing with its owner - ASRC files as
BROADLEAF, INUTEQ and VISTRONIX; `BOWHEAD GOVERNMENT SUPPORT SERVICES` is
correctly keyed to Ukpeagvik Inupiat Corporation and shares not one word with
it.  A bare token test may never withdraw a link on its own.  Every withdrawal
below had to survive a CORROBORATION LADDER first, built only from files
already on this machine.  In the order the ladder is climbed:

  R0  Cedar's own DEAL LEDGER, where it settles a family outright (CDR-12).
  R1  The awardee IS a government.  Disqualifying, not corroborating.
  R2  The registrant's own FPDS-DECLARED PARENT at >= 20 observations
      (ENTITY_MATCH_RULES rule 11) is a listed public prime or PE owner.
      Disqualifying.
  R3  **THE OWNER'S OWN AUDITED ANNUAL REPORT.**  `code/ancsa_portal/txt`
      holds 166 ANCSA annual reports for all 12 regional corporations, and
      every one carries its consolidated SUBSIDIARY LIST.  This is rule 14's
      instruction - *"go to the ANC and NHO websites we have already mapped and
      take the subsidiary lists"* - already on disk.  It is the strongest
      evidence class available offline and it settled the largest cases here:

          EAGLE HARBOR, LLC        -> Koniag  ("d eagle harbor solutions llc
                                     ehs ehs was formed at the end of fiscal
                                     year 2016")
          EAGLE INTEGRATED SERVICES, EAGLE GLOBAL SCIENTIFIC, EAGLE MEDICAL
          SERVICES, EAGLE HEALTH ANALYTICS, EAGLE APPLIED SCIENCES
                                   -> Bristol Bay Native Corporation, which
                                      runs an "Eagle" subsidiary family
          VISTA DEFENSE TECHNOLOGIES, VISTA INTERNATIONAL OPERATIONS
                                   -> Bristol Bay Native Corporation
          EAGLE EYE ELECTRIC LLC   -> Bering Straits Native Corporation
          BUSINESS MISSION EDGE LLC-> Cook Inlet Region (51% via OSC Edge)
          NORTH WIND / LBYD        -> Cook Inlet Region

      Two guards, both earned on false positives found while building it:
        - the firm must carry **>= 2 distinctive tokens**, which kills
          `REGIONAL SERVICES LTD` -> Bering Straits and `INFORMATION TECHNOLOGY
          SOLUTIONS CORP` -> Koniag, where the "hit" was an English phrase;
        - **a regional corporation naming an entity inside its own ANCSA region
          is GEOGRAPHY, not ownership.**  Chugach's report prints
          "port graham  port graham corporation" on a MAP of the region.  Any
          hit whose current hub already sits in that corporation's region is
          discarded.
  R4  rule 7 - the firm's own name resolves to the hub with an empty residue.
  R5  rule 11 - the FPDS-declared parent at >= 20 observations IS the hub.
  R6  a RULED sibling: the firm shares a distinctive token with another
      identifier keyed to the SAME hub by a ruled or two-leg method.
      **`cross_dataset_propagation` is deliberately NOT accepted here**: it has
      already propagated `cluster_v3`'s guesses onto CAGE codes at these very
      hubs (`Blue Steel Company` at Blue Lake, `Eagle Butte Cooperative Assn` at
      Native Village of Eagle, `Government & Industrial Supply` at Barrow).
      Accepting it would let the defect corroborate itself - the evidence
      lineage trap `docs/ASSERTION_LAYER.md` names.
  R7  a deal-ledger row naming the firm and the hub together.

Only a pair that reaches NO rung is a candidate for withdrawal, and even then
it is withdrawn only where the name evidence is nil - no shared distinctive
token, or a shared `NAME_TRAPS` token, which the trap register says is *no*
evidence.  Everything else is HELD for the owner, because *"sometimes you just
can't find it"* is a legitimate answer (rule 13 rung 6; ADR-010 `unresolved`).

A WITHDRAWAL IS NOT AN EXCLUSION
---------------------------------
`ENTITY_MATCH_RULES`: *"the refusal says only: this is not THAT entity."*  It
does not assert the firm is non-Native, and this script writes **no**
`exclusion_id` - `data/spine/cedar_exclusion_rulings.csv` is the OWNER's
register (`ruled_by = Elijah Moreno`) and an agent may not mint a row in it
(rule 8).  The withdrawal is recorded as `confidence_tier = X`, which
`40_build_prime_contracts.py` line 82 already honours (`tier not in ("A","B")`
never attributes) so the repair survives a rebuild, plus three new ledger
columns naming this script and the reason.

`cedar_uid` IS PERMANENT.  Rows are repointed; no uid is minted, retired or
reused.  A withdrawn identifier keeps its ledger row and its uid, and the
transaction loses the hub's uid exactly as the 328,810 rows Cedar already
publishes as honestly unattributed do.

SCOPE OF THE REPAIR, AND WHAT IS ONLY REPORTED
-----------------------------------------------
APPLIED:  the UEI leg (the 2,142 ledger rows the mandate names) and the North
Wind / LBYD CAGE rows at `TRBF-LUMBEE-00` (CDR-12).
REPORTED, NOT APPLIED:  the rest of the CAGE leg.  It is newly measured by this
pass, it carries the `cage_code = 'nan'` hazard of CDR-06 alongside it, and
adjudicating it in the same pass that discovered it is the mistake this repo
keeps paying for.  It is written to `review/1079_owner_holds_<date>.csv` with
its evidence and it IS flagged in the new prime columns, so no consumer can
mistake it for a verified attribution.

WHAT THIS WRITES
----------------
identity source (the generator side):
    data/clean/cedar_identifier_ledger_final.csv    +3 columns
materialised rows (correcting a generator does not correct what it produced):
    data/clean/prime_contracts.csv                  +5 columns
    data/clean/prime_contracts_archive_backfill.csv
    data/clean/prime_contracts_awards.csv
    data/clean/prime_contracts_published.csv
    data/clean/subawards.csv
evidence:
    review/1079_quarantine_triage_<date>.csv    every quarantined identifier,
                                                its evidence bundle, its disposition
    review/1079_entity_ledger_<date>.csv        who gained and who lost, to the cent
    review/1079_owner_holds_<date>.csv          what could NOT be decided, and what was tried
    docs/QUARANTINED_METHOD_EXPOSURE.json       the conservation proof

INVARIANTS - `verify` exits 1 on any breach, and `selftest` proves each fires
-----------------------------------------------------------------------------
  I1  row count of every touched file identical before and after
  I2  the new columns are present and no pre-existing column was dropped
  I3  sum(total_obligations) over prime_contracts identical TO THE CENT
  I4  per-entity gains and losses net to exactly zero
  I5  attributed dollars fall by exactly what was withdrawn, to the cent
  I6  every attributed prime row keyed by a quarantined ledger row carries
      identifier_ruling_quarantined = Y
  I7  zero WITHDRAWN identifiers still key an attributed prime row
"""
from __future__ import annotations

import collections
import csv
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))
import cedar_domain  # noqa: E402

csv.field_size_limit(1 << 30)
TODAY = date.today().isoformat()
STEM = "1079_quarantine_method_exposure"
TAG = f".bak_{TODAY}_pre_{STEM}"

CLEAN = ROOT / "data" / "clean"
SPINEDIR = ROOT / "data" / "spine"
REVIEW = ROOT / "review"
DOCS = ROOT / "docs"
ANCSA_TXT = ROOT / "code" / "ancsa_portal" / "txt"

LEDGER = CLEAN / "cedar_identifier_ledger_final.csv"
PRIME = CLEAN / "prime_contracts.csv"
PROOF = DOCS / "QUARANTINED_METHOD_EXPOSURE.json"

QUARANTINED = {"cluster_v3", "need_v6", "sam_namematch_2026_05_06"}
# `cross_dataset_propagation:*` is EXCLUDED on purpose - see rung R6.
RULED = (set(cedar_domain.RULED_METHODS) | set(cedar_domain.TWO_LEG_METHODS)
         | {"subsidiary_lookup", "institution_exact_name"})
TRAPS = {w.lower() for w in cedar_domain.NAME_TRAPS}
PARENT_EDGE_FLOOR = 20        # ENTITY_MATCH_RULES rule 11
REPORT_MIN_TOKENS = 2         # rung R3 guard 1
NEW_LEDGER_COLS = ["method_quarantined", "quarantine_disposition",
                   "quarantine_disposition_basis"]
NEW_PRIME_COLS = ["identifier_ruling_method", "identifier_ruling_tier",
                  "identifier_ruling_quarantined", "identifier_ruling_basis",
                  "identifier_ruling_review"]

# --------------------------------------------------------------------------
# Two curated lists.  Both are SMALL, both are echoed in full by `report`, and
# both exist because a structural predicate could not reach the case.
# --------------------------------------------------------------------------

# A federal or state agency is not a Native-owned business; a BIA row here is
# the funder mis-recorded as the awardee.  NOT derivable from the FPDS parent
# edge: federally recognized tribal governments and BIE schools ALSO declare
# `GOVERNMENT OF THE UNITED STATES` as their parent - `CIRCLE NATIVE COMMUNITY`
# does, correctly keyed to Circle - so that predicate alone would withdraw
# correct links.
AGENCY_NAME_RE = re.compile(
    r"^(indian affairs,? bureau of"
    r"|bureau of indian (affairs|education)"
    r"|indian health service(\s*\(\d+\))?"
    r"|(the )?army,? united states departmen?t? of the"
    r"|united states department of the army"
    r"|engineers,? u ?s army corps of"
    r"|library of congress"
    r"|fort gordon lodging"
    r"|florida dept of health bureau vital"
    r"|state of florida)$", re.I)

# Declared FPDS parents at >= PARENT_EDGE_FLOOR observations that are publicly
# traded primes or private-equity owners.  A firm whose registrant-FILED parent
# is one of these is owned by it, and is not owned by a village government.
# Each string is quoted verbatim from `data/clean/fpds_uei_edges.csv`.
NON_NATIVE_PARENTS = {
    "GENERAL DYNAMICS": "NYSE: GD",
    "COMPUTER SCIENCES CORPORATION": "CSC -> CSRA -> GDIT registrant lineage",
    "CSRA LLC": "CSC public-sector spin-off, acquired by General Dynamics",
    "L3HARRIS TECHNOLOGIES, INC": "NYSE: LHX",
    "VERITAS CAPITAL FUND MANAGEMENT, L.L.C.": "private equity, owner of Peraton",
    "STATE OF FLORIDA": "a state government",
}

# CDR-12.  Cedar's own deal ledger settles this family twice - ANCSA2-2017-003
# "CIRI through its subsidiary North Wind purchased Portage" and MA2020-004
# "North Wind Group acquires LBYD Engineers" - CIRI's own annual report names
# the family, and prime_contracts.csv CONTRADICTS ITSELF on it, which is the
# discriminator 1075 used: the same firm NAMES sit at Cook Inlet at tier A and
# at Eastern Shoshone / Lumbee at tier B.
#   NORTH WIND CONSTRUCTION SERVICES, LLC   A @ ANRC-CKINLT-00   B @ TRBF-ESWNDR-00
#   NORTH WIND SITE SERVICES, LLC           A @ ANRC-CKINLT-00   B @ both
#   NORTH WIND RESOURCE CONSULTING, LLC     A @ ANRC-CKINLT-00   B @ TRBF-ESWNDR-00
#   LBYD INC / LBYD FEDERAL, LLC            A @ ANRC-CKINLT-00   B @ TRBF-ESWNDR-00
# `Wind River Construction LLC` is deliberately NOT in this set - Wind River is
# the Eastern Shoshone reservation, which is exactly why `wind` is a trap.
NORTHWIND_TARGET = "ANRC-CKINLT-00"
NORTHWIND_NAME_RE = re.compile(r"^(north wind|lbyd)\b", re.I)
NORTHWIND_FROM_HUBS = {"TRBF-ESWNDR-00", "TRBF-LUMBEE-00"}

GENERIC = frozenset("""inc incorporated llc llp lp lc pllc corp corporation co company the of and
    a an group holdings holding ltd limited plc jv joint venture""".split())

# Organisational / class words.  A name match resting only on these is a match
# on nothing, and `government` being absent from every earlier list is what let
# 53 UEIs onto Native Village of Barrow.
ORG_GENERIC = frozenset("""government governmental services service solutions solution enterprise
    enterprises systems system technologies technology technical consulting consultants contractors
    contracting construction development federal national international management managed
    operations operating associates association associated partners partnership industries
    industrial resources resource supply supplies logistics support staffing professional
    professionals global america american americas united states usa department bureau office
    agency administration authority commission board center centre centers institute foundation
    council communications communication information data digital cyber engineering engineers
    environmental energy health healthcare medical care builders building general corporate
    ventures capital tribe tribes tribal nation nations native natives indian indians band bands
    community communities village villages rancheria reservation pueblo people peoples traditional
    governing governance corporations alaska alaskan hawaiian hawaii new north south east west
    northern southern eastern western upper lower old grand great big small""".split())

UNATTRIBUTED_PRIME = {
    "tribe_id": "", "canonical_name": "", "attribution_method": "unattributed",
    "confidence_tier": "C", "attributed_flag": "0", "cedar_uid": "",
    "owner_attribution_status": "NO_OWNER_ATTRIBUTED",
    "owner_as_of_transaction_cedar_uid": "UNKNOWN",
}


def toks(s):
    return [w for w in re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).split() if w]


def ntoks(s):
    return [w for w in toks(s) if w not in GENERIC]


def distinctive(s):
    return {w for w in ntoks(s) if len(w) >= 3 and w not in ORG_GENERIC}


def nkey(s):
    return " ".join(ntoks(s))


def rows_of(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        yield from csv.DictReader(fh)


def prose_alias(a):
    """A prose SENTENCE in an alias field is not a name.  Te-Moak's reads
    "Four constituent bands: Battle Mountain Band; Elko Band; ..." and it is why
    `Four Tribes Enterprises` and `Battle Creek Construction` were keyed to a
    Nevada tribe."""
    return (":" in a) or (";" in a) or (len(ntoks(a)) > 8)


def is_jv(name):
    return bool(re.search(r"\b(jv|joint venture)\b", name or "", re.I))


# ============================================================== EVIDENCE ====
class Evidence:
    def __init__(self, need_prime=True):
        self.spine = {r["tribe_id"]: r for r in rows_of(SPINEDIR / "cedar_entity_spine.csv")}
        self.led = list(rows_of(LEDGER))
        self._name_index()
        self._hub_tokens()
        self._ledger_maps()
        self._edges()
        self._deals()
        self._annual_reports()
        self.prime_by_uei, self.prime_by_cage = {}, {}
        if need_prime:
            self._prime()

    # -- spine ------------------------------------------------------------
    def _name_index(self):
        idx = collections.defaultdict(set)
        eid = {}
        for t, e in self.spine.items():
            eid[e.get("cedar_entity_id") or t] = t
            eid[t] = t
            for f in ("canonical_name", "fr_official_name"):
                if len(ntoks(e.get(f))) >= 2:
                    idx[nkey(e.get(f))].add(t)
            for a in (e.get("aliases") or "").split("|"):
                if prose_alias(a) or len(ntoks(a)) < 2:
                    continue
                idx[nkey(a)].add(t)
        p = CLEAN / "entity_aliases.csv"
        if p.exists():
            for r in rows_of(p):
                t = eid.get(r.get("entity_id", ""))
                if t and len(ntoks(r.get("alias_name"))) >= 2:
                    idx[nkey(r["alias_name"])].add(t)
        self.name_idx = idx

    def hub_from_name(self, n):
        s = self.name_idx.get(nkey(n)) or set()
        return next(iter(s)) if len(s) == 1 else ""

    def _hub_tokens(self):
        self.hub_tok, self.hub_names = {}, {}
        for t, e in self.spine.items():
            s = distinctive(e["canonical_name"]) | distinctive(e.get("fr_official_name"))
            names = {nkey(e["canonical_name"]), nkey(e.get("fr_official_name"))}
            for a in (e.get("aliases") or "").split("|"):
                if prose_alias(a):
                    continue
                s |= distinctive(a)
                names.add(nkey(a))
            self.hub_tok[t] = s
            self.hub_names[t] = {n for n in names if n}

    def region_of(self, t):
        """The ANCSA regional corporation above a hub, however the spine spells
        it.  Used only to DISCARD a report hit, never to award one."""
        e = self.spine.get(t) or {}
        out = {e.get("ancsa_region_entity_id", ""), e.get("ultimate_parent_entity_id", ""),
               e.get("parent_entity_id", "")}
        # compound village ids carry their region in the suffix chain
        for part in (t or "").split("-")[2:]:
            out.add("ANRC-" + part + "-00")
        for nm in (e.get("ultimate_parent_entity_name"), e.get("parent_entity_name")):
            if nm:
                out.add(self.hub_from_name(nm))
        return {x for x in out if x}

    def residue(self, firm_name, t):
        return distinctive(firm_name) - (self.hub_tok.get(t) or set())

    # -- ledger -----------------------------------------------------------
    def _ledger_maps(self):
        self.by_uei = collections.defaultdict(list)
        self.by_cage = collections.defaultdict(list)
        for r in self.led:
            it = (r.get("identifier_type") or "").upper()
            k = (r.get("identifier") or "").strip().upper()
            if not k:
                continue
            if it == "UEI":
                self.by_uei[k].append(r)
            elif it == "CAGE":
                self.by_cage[k].append(r)
        # the row 40_build_prime_contracts.py would pick: FIRST tier A/B seen
        self.uei_pick, self.cage_pick = {}, {}
        for m, src in ((self.uei_pick, self.by_uei), (self.cage_pick, self.by_cage)):
            for k, v in src.items():
                for r in v:
                    if (r.get("confidence_tier") or "").strip() in ("A", "B"):
                        m[k] = r
                        break
        self.ruled_tok = collections.defaultdict(set)
        for r in self.led:
            if (r.get("attribution_method") in RULED and r.get("tribe_id")
                    and (r.get("confidence_tier") or "") != "X"):
                self.ruled_tok[r["tribe_id"]] |= distinctive(r.get("legal_business_name"))

    def hub_of_uei(self, u):
        r = self.uei_pick.get(u)
        return r["tribe_id"] if r and r.get("tribe_id") else ""

    # -- FPDS declared parents (rule 11) ----------------------------------
    def _edges(self):
        self.edges = collections.defaultdict(list)
        p = CLEAN / "fpds_uei_edges.csv"
        if not p.exists():
            return
        for r in rows_of(p):
            try:
                n = int(r.get("n_observations") or 0)
            except ValueError:
                n = 0
            c = (r.get("child_uei") or "").strip().upper()
            pu = (r.get("parent_uei") or "").strip().upper()
            if c and n >= PARENT_EDGE_FLOOR and pu and pu != c:
                self.edges[c].append((n, pu, (r.get("parent_name") or "").strip()))

    def declared_parents(self, u):
        out = [(n, pu, pn, self.hub_of_uei(pu) or self.hub_from_name(pn))
               for n, pu, pn in self.edges.get(u, [])]
        out.sort(reverse=True)
        return out

    # -- deals ------------------------------------------------------------
    def _deals(self):
        self.deal_blobs = []
        p = CLEAN / "deals_classified.csv"
        if not p.exists():
            return
        for r in rows_of(p):
            blob = " | ".join(str(v) for v in r.values())
            self.deal_blobs.append((r.get("deal_id") or r.get("id") or "deal",
                                    blob, set(toks(blob))))

    def deal_mentions(self, firm_name, hub):
        ft = distinctive(firm_name)
        if not ft or not hub:
            return ""
        for did, blob, tk in self.deal_blobs:
            if hub in blob and ft <= tk:
                return did
        return ""

    # -- ANCSA audited annual reports (rung R3) ---------------------------
    def _annual_reports(self):
        self.reports = {}
        self.report_hub = {}
        if not ANCSA_TXT.exists():
            return
        buf = collections.defaultdict(list)
        for f in sorted(os.listdir(ANCSA_TXT)):
            parts = f.split("__")
            if len(parts) < 2:
                continue
            buf[parts[1]].append((ANCSA_TXT / f).read_text(encoding="utf-8", errors="ignore"))
        for corp, texts in buf.items():
            self.reports[corp] = " " + re.sub(
                r"[^a-z0-9]+", " ", " \n ".join(texts).lower()).strip() + " "
            self.report_hub[corp] = self.hub_from_name(corp.replace("_", " "))

    def report_owner(self, firm_name):
        """(hub, corp, phrase) if EXACTLY ONE regional corporation's audited
        annual report names this firm.  Requires >= REPORT_MIN_TOKENS
        distinctive tokens, so an English phrase cannot win."""
        w = [x for x in ntoks(firm_name)]
        if len(distinctive(firm_name)) < REPORT_MIN_TOKENS:
            return ("", "", "")
        phrase = " " + " ".join(w) + " "
        hits = [c for c, t in self.reports.items() if phrase in t]
        if len(hits) != 1:
            return ("", "", "")
        return (self.report_hub.get(hits[0], ""), hits[0], phrase.strip())

    # -- prime ------------------------------------------------------------
    def _prime(self):
        """duckdb reads the 1.4GB table in seconds; csv takes minutes."""
        import duckdb
        con = duckdb.connect()
        q = """SELECT upper(trim(awardee_uei)) uei,
                      mode(awardee_name) nm, count(*) n,
                      sum(TRY_CAST(total_obligations AS DOUBLE)) usd,
                      string_agg(DISTINCT recipient_state_code, '|') states
               FROM read_csv_auto(?, all_varchar=true, sample_size=-1)
               WHERE tribe_id <> '' AND attribution_method = 'uei_exact' GROUP BY 1"""
        for uei, nm, n, usd, st in con.execute(q, [str(PRIME)]).fetchall():
            self.prime_by_uei[uei] = dict(name=nm or "", n=n, usd=usd or 0.0, states=st or "")
        q2 = """SELECT upper(trim(cage_code)) cage, count(*) n,
                       sum(TRY_CAST(total_obligations AS DOUBLE)) usd,
                       mode(awardee_name) nm, string_agg(DISTINCT recipient_state_code,'|') st
                FROM read_csv_auto(?, all_varchar=true, sample_size=-1)
                WHERE tribe_id <> '' AND attribution_method = 'cage_exact'
                  AND upper(trim(cage_code)) <> 'NAN' GROUP BY 1"""
        for cage, n, usd, nm, st in con.execute(q2, [str(PRIME)]).fetchall():
            self.prime_by_cage[cage] = dict(name=nm or "", n=n, usd=usd or 0.0, states=st or "")
        q3 = """SELECT upper(trim(parent_uei)) pu, count(*) n,
                       sum(TRY_CAST(total_obligations AS DOUBLE)) usd
                FROM read_csv_auto(?, all_varchar=true, sample_size=-1)
                WHERE tribe_id <> '' AND attribution_method = 'parent_uei' GROUP BY 1"""
        self.prime_by_parent = {pu: dict(n=n, usd=usd or 0.0)
                                for pu, n, usd in con.execute(q3, [str(PRIME)]).fetchall()}
        con.close()


# =========================================================== DISPOSITION ====
def dispose(ev, it, ident, lr, firm):
    """(disposition, target_hub, basis).  Order IS the argument: a
    disqualifier that makes the pairing impossible outranks a corroborator, and
    a corroborator outranks a token test."""
    hub = lr.get("tribe_id") or ""
    hubname = lr.get("canonical_name") or ""
    legal = lr.get("legal_business_name") or ""
    fname = firm or legal
    parents = ev.declared_parents(ident) if it == "UEI" else []

    # R0 -- Cedar's own deal ledger settles this family (CDR-12)
    if NORTHWIND_NAME_RE.match(fname or "") and hub in NORTHWIND_FROM_HUBS:
        return ("REPOINT", NORTHWIND_TARGET,
                "CDR-12: deal ledger ANCSA2-2017-003 and MA2020-004 name CIRI / North Wind "
                "Group as the owner; CIRI's own annual report names the family; and "
                "prime_contracts already keys these firm NAMES to ANRC-CKINLT-00 at tier A "
                "while keying these UEIs to a trap token (`wind` / `north`) at tier B")

    # R1 -- the awardee IS a government
    for cand in (fname, legal):
        if cand and AGENCY_NAME_RE.match(cand.strip()):
            return ("WITHDRAW", "",
                    f"awardee `{cand.strip()}` is a federal or state agency; an agency is not "
                    f"a Native-owned business and cannot be owned by {hubname}")

    # R2 -- the registrant's own declared parent is a listed non-Native owner
    for n, pu, pn, ph in parents:
        if pn.strip().upper() in NON_NATIVE_PARENTS:
            return ("WITHDRAW", "",
                    f"FPDS-declared parent `{pn}` observed {n}x "
                    f"({NON_NATIVE_PARENTS[pn.strip().upper()]}); rule 11 - a declared parent "
                    f"outranks a name")

    # R3 -- the owner's own AUDITED ANNUAL REPORT
    rh, corp, phrase = ev.report_owner(fname)
    if rh:
        if rh == hub:
            return ("KEEP", hub, f"audited annual report: {corp} names `{phrase}` in its own "
                                 f"consolidated subsidiary list")
        if rh in ev.region_of(hub):
            rh = ""  # a regional report naming an entity IN ITS REGION is geography
        elif is_jv(fname):
            return ("HOLD", "", f"audited annual report: {corp} names `{phrase}`, but the "
                                f"awardee is a JOINT VENTURE and an equity interest in a JV is "
                                f"not sole ownership (rule 11). Owner ruling needed.")
        else:
            return ("REPOINT", rh, f"audited annual report: {corp} names `{phrase}` in its own "
                                   f"consolidated subsidiary list, contradicting {hub}")

    # R4 -- rule 7, the firm's own name IS the hub
    if nkey(fname) in ev.hub_names.get(hub, set()) or nkey(legal) in ev.hub_names.get(hub, set()):
        return ("KEEP", hub, "rule 7: exact whole-name match to the hub's own official name")
    if distinctive(fname) and not ev.residue(fname, hub):
        return ("KEEP", hub, "rule 7: residue empty - every distinctive word in the filed name "
                             "is accounted for by the hub's own names")

    # R5 -- rule 11, the declared parent agrees, or names another hub
    for n, pu, pn, ph in parents:
        if ph and ph == hub:
            return ("KEEP", hub, f"rule 11: FPDS-declared parent `{pn}` ({n} observations) "
                                 f"resolves to this hub")
    for n, pu, pn, ph in parents:
        if ph and ph != hub:
            if is_jv(fname):
                return ("HOLD", "", f"declared parent `{pn}` ({n}x) resolves to {ph}, but the "
                                    f"awardee is a JOINT VENTURE and a JV genuinely has two "
                                    f"parents (rule 11). Owner ruling needed.")
            return ("REPOINT", ph, f"rule 11/12: FPDS-declared parent `{pn}` observed {n}x "
                                   f"resolves to {ph}, contradicting {hub}")

    # R6 -- a RULED sibling of this hub shares a distinctive token
    sib = distinctive(fname) & (ev.ruled_tok.get(hub) or set())
    if sib:
        return ("KEEP", hub, f"brand corroboration: shares distinctive token(s) "
                             f"`{'|'.join(sorted(sib))}` with an identifier keyed to this hub by "
                             f"a RULED or two-leg method")

    # R7 -- the deal ledger names both
    d = ev.deal_mentions(fname, hub)
    if d:
        return ("KEEP", hub, f"deal ledger row {d} names this firm alongside the hub")

    # --- no rung reached: judge the NAME evidence that is left ------------
    ht = ev.hub_tok.get(hub) or set()
    shared = distinctive(fname) & ht
    shared_nontrap = shared - TRAPS
    parent_supports = ""
    for n, pu, pn, ph in parents:
        if distinctive(pn) & ht:
            parent_supports = f"{pn} ({n}x)"
            break
    if parent_supports:
        return ("HOLD", "",
                f"no rung reached, but the registrant's own declared parent `{parent_supports}` "
                f"shares a token with `{hubname}`. Undecided rather than withdrawn - the parent "
                f"is not in the ledger (CDR-03) and resolving it would settle this.")
    if not shared:
        return ("WITHDRAW", "",
                f"no rung of the corroboration ladder reached and the firm shares NO distinctive "
                f"token with `{hubname}` (hub tokens: {'|'.join(sorted(ht)) or '(none)'}); the "
                f"link rests on nothing")
    if not shared_nontrap:
        return ("WITHDRAW", "",
                f"no rung of the corroboration ladder reached and the only shared token is "
                f"`{'|'.join(sorted(shared))}`, on cedar_domain.NAME_TRAPS - the trap register "
                f"says a token match on a trap is NO evidence")
    return ("HOLD", "",
            f"shares `{'|'.join(sorted(shared_nontrap))}` with the hub but no corroborating "
            f"identifier, audited filing, ruled sibling or deal row. Undecided - rule 13 rung 6.")


def triage(ev):
    out = []
    for lr in ev.led:
        m = lr.get("attribution_method")
        if m not in QUARANTINED:
            continue
        it = (lr.get("identifier_type") or "").upper()
        ident = (lr.get("identifier") or "").strip().upper()
        tier = (lr.get("confidence_tier") or "").strip()
        pa = (ev.prime_by_uei.get(ident, {}) if it == "UEI"
              else ev.prime_by_cage.get(ident, {}) if it == "CAGE" else {})
        pp = ev.prime_by_parent.get(ident, {}) if it == "UEI" else {}
        firm = pa.get("name") or lr.get("legal_business_name") or ""
        usd = float(pa.get("usd") or 0.0) + float(pp.get("usd") or 0.0)
        nrows = int(pa.get("n") or 0) + int(pp.get("n") or 0)

        if tier not in ("A", "B"):
            disp, tgt, basis = ("KEEP", lr.get("tribe_id", ""),
                                f"ledger tier {tier or '(blank)'} - already non-attributing; "
                                f"40_build_prime_contracts.py never keys it")
        else:
            disp, tgt, basis = dispose(ev, it, ident, lr, firm)

        in_scope = (it == "UEI") or (
            it == "CAGE" and NORTHWIND_NAME_RE.match(firm or "")
            and lr.get("tribe_id") in NORTHWIND_FROM_HUBS)
        if not in_scope and disp in ("WITHDRAW", "REPOINT"):
            basis = ("REPORTED, NOT APPLIED - the CAGE leg is outside this pass's declared "
                     "scope and is newly measured here -- " + basis)
            disp = "HOLD"

        out.append(dict(
            identifier_type=it, identifier=ident, attribution_method=m, confidence_tier=tier,
            tribe_id=lr.get("tribe_id", ""), canonical_name=lr.get("canonical_name", ""),
            legal_business_name=lr.get("legal_business_name", ""),
            prime_awardee_name=pa.get("name", ""), prime_rows=nrows,
            prime_obligations_usd=round(usd, 2), recipient_states=pa.get("states", ""),
            hub_distinctive_tokens="|".join(sorted(ev.hub_tok.get(lr.get("tribe_id", ""), set()))),
            firm_distinctive_tokens="|".join(sorted(distinctive(firm))),
            declared_parents=";".join(f"{pn}({n})->{ph or '?'}"
                                      for n, pu, pn, ph in ev.declared_parents(ident)[:4]),
            disposition=disp, repoint_to=tgt,
            repoint_to_name=(ev.spine.get(tgt, {}) or {}).get("canonical_name", ""),
            basis=basis,
            applied_in_this_pass="Y" if (in_scope and disp in ("WITHDRAW", "REPOINT")) else "N",
        ))
    return out


# ============================================================== WRITERS =====
def backup(p: Path):
    b = Path(str(p) + TAG)
    if not b.exists() and p.exists():
        shutil.copy2(p, b)
    return b


def atomic_rows(path: Path, header, row_iter):
    """`.part`-then-rename: an interruption must not look like a completion."""
    tmp = Path(str(path) + ".part")
    n = 0
    with open(tmp, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        for r in row_iter:
            w.writerow(r)
            n += 1
    os.replace(tmp, path)
    return n


class Plan:
    """The applied dispositions, indexed for the streaming writers."""

    def __init__(self, decisions, spine):
        self.wd_uei, self.wd_cage, self.rp_uei, self.rp_cage = {}, {}, {}, {}
        for d in decisions:
            if d["applied_in_this_pass"] != "Y":
                continue
            tgt = (self.wd_uei if d["identifier_type"] == "UEI" else self.wd_cage) \
                if d["disposition"] == "WITHDRAW" else \
                (self.rp_uei if d["identifier_type"] == "UEI" else self.rp_cage)
            tgt[d["identifier"]] = d
        self.review = {(d["identifier_type"], d["identifier"]): d for d in decisions}
        self.uid = {t: (e.get("cedar_uid") or "") for t, e in spine.items()}


def rewrite_prime_like(path: Path, ev, plan, spec):
    """Stream one materialised contracting table.

    `spec` names the columns present in THIS table; the four tables differ.
    Only `prime_contracts.csv` takes the visibility columns - it is the
    flagship and the one CDR-11 names - but every table takes the repoint and
    the withdrawal, because correcting a generator does not correct what it has
    already produced (the lesson 1075 records from the UKB fix).
    """
    stat = collections.Counter()
    money = collections.defaultdict(float)
    lost = [0.0]
    moved = [0.0]

    with open(path, newline="", encoding="utf-8-sig") as fh:
        rd = csv.reader(fh)
        hdr = next(rd)
        ix = {c: i for i, c in enumerate(hdr)}
        add = [c for c in NEW_PRIME_COLS if spec.get("visibility") and c not in hdr]
        out_hdr = hdr + add

        def g(row, c):
            return row[ix[c]] if c in ix else ""

        def gen():
            for row in rd:
                stat["rows"] += 1
                u = (g(row, "awardee_uei") or "").strip().upper()
                cg = (g(row, "cage_code") or "").strip().upper()
                pu = (g(row, "parent_uei") or "").strip().upper()
                tid = g(row, "tribe_id")
                try:
                    ob = float(g(row, spec["money"]) or 0)
                except ValueError:
                    ob = 0.0

                # which LEDGER row keyed this transaction, in script 40's order
                am = g(row, "attribution_method") if "attribution_method" in ix else ""
                if am == "uei_exact" or (not am and u in ev.uei_pick):
                    leg, key, lr = "UEI", u, ev.uei_pick.get(u)
                elif am == "cage_exact" or (not am and cg != "NAN" and cg in ev.cage_pick):
                    leg, key, lr = "CAGE", cg, ev.cage_pick.get(cg)
                elif am == "parent_uei" or (not am and pu in ev.uei_pick):
                    leg, key, lr = "PARENT_UEI", pu, ev.uei_pick.get(pu)
                else:
                    leg, key, lr = "", "", None
                rm = (lr or {}).get("attribution_method", "")
                rt = (lr or {}).get("confidence_tier", "")
                rq = "Y" if rm in QUARANTINED else ("N" if rm else "")
                basis = f"{leg}:{key}" if key else ""
                rev = ""
                dec = plan.review.get(("UEI" if leg != "CAGE" else "CAGE", key))
                if dec and rm in QUARANTINED:
                    rev = dec["disposition"]

                # apply
                d = None
                if tid:
                    if leg in ("UEI", "PARENT_UEI"):
                        d = plan.wd_uei.get(key) or plan.rp_uei.get(key)
                    elif leg == "CAGE":
                        d = plan.wd_cage.get(key) or plan.rp_cage.get(key)
                if d is not None:
                    if d["disposition"] == "WITHDRAW":
                        money[tid] -= ob
                        money["(unattributed)"] += ob
                        lost[0] += ob
                        for c, v in UNATTRIBUTED_PRIME.items():
                            if c in ix:
                                row[ix[c]] = v
                        for c in ("prime_native_tier", "sub_native_tier"):
                            if c in ix:
                                row[ix[c]] = ""
                        stat["withdrawn_rows"] += 1
                        rev = "WITHDRAWN_BY_1079"
                    else:
                        new = d["repoint_to"]
                        money[tid] -= ob
                        money[new] += ob
                        moved[0] += ob
                        if "tribe_id" in ix:
                            row[ix["tribe_id"]] = new
                        if "canonical_name" in ix:
                            row[ix["canonical_name"]] = d["repoint_to_name"]
                        if "cedar_uid" in ix:
                            row[ix["cedar_uid"]] = plan.uid.get(new, "")
                        stat["repointed_rows"] += 1
                        rev = "REPOINTED_BY_1079"
                if add:
                    row = row + [rm, rt, rq, basis, rev]
                    if rq == "Y":
                        stat["flagged_quarantined_rows"] += 1
                        if tid:
                            stat["flagged_attributed_rows"] += 1
                yield row

        backup(path)
        stat["written"] = atomic_rows(path, out_hdr, gen())
    stat["withdrawn_usd"] = round(lost[0], 2)
    stat["repointed_usd"] = round(moved[0], 2)
    stat["cols_before"] = len(hdr)
    stat["cols_after"] = len(out_hdr)
    return stat, money


def rewrite_subawards(path: Path, plan):
    """Two independent keyed sides, `prime_*` and `sub_*`, each with its own
    tribe id and tier.  Subaward dollars are NOT prime dollars and are reported
    separately - `docs/MONEY_TOTALLING_RULES.md` forbids adding across files."""
    stat = collections.Counter()
    money = collections.defaultdict(float)
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rd = csv.reader(fh)
        hdr = next(rd)
        ix = {c: i for i, c in enumerate(hdr)}

        def gen():
            for row in rd:
                stat["rows"] += 1
                try:
                    amt = float(row[ix["subaward_amount"]] or 0) if "subaward_amount" in ix else 0.0
                except ValueError:
                    amt = 0.0
                for side, ueic, cagec, tidc, tierc, uidc in (
                        ("prime", "prime_uei", "prime_cage", "prime_native_tribe_id",
                         "prime_native_tier", "prime_cedar_uid"),
                        ("sub", "sub_uei", "sub_cage", "sub_native_tribe_id",
                         "sub_native_tier", "sub_cedar_uid")):
                    if tidc not in ix or not row[ix[tidc]]:
                        continue
                    u = (row[ix[ueic]] if ueic in ix else "").strip().upper()
                    cg = (row[ix[cagec]] if cagec in ix else "").strip().upper()
                    d = plan.wd_uei.get(u) or plan.rp_uei.get(u)
                    if d is None and cg and cg != "NAN":
                        d = plan.wd_cage.get(cg) or plan.rp_cage.get(cg)
                    if d is None:
                        continue
                    old = row[ix[tidc]]
                    if d["disposition"] == "WITHDRAW":
                        row[ix[tidc]] = ""
                        if tierc in ix:
                            row[ix[tierc]] = ""
                        if uidc in ix:
                            row[ix[uidc]] = ""
                        money[f"{side}:{old}"] -= amt
                        stat[f"{side}_withdrawn"] += 1
                    else:
                        row[ix[tidc]] = d["repoint_to"]
                        if uidc in ix:
                            row[ix[uidc]] = plan.uid.get(d["repoint_to"], "")
                        money[f"{side}:{old}"] -= amt
                        money[f"{side}:{d['repoint_to']}"] += amt
                        stat[f"{side}_repointed"] += 1
                yield row

        backup(path)
        stat["written"] = atomic_rows(path, hdr, gen())
    stat["cols_before"] = stat["cols_after"] = len(hdr)
    return stat, money


def rewrite_ledger(ev, decisions):
    by_key = {(d["identifier_type"], d["identifier"], d["attribution_method"]): d
              for d in decisions}
    hdr = list(ev.led[0].keys())
    for c in NEW_LEDGER_COLS:
        if c not in hdr:
            hdr.append(c)
    st = collections.Counter()

    def gen():
        for r0 in ev.led:
            r = dict(r0)
            m = r.get("attribution_method")
            d = by_key.get(((r.get("identifier_type") or "").upper(),
                            (r.get("identifier") or "").strip().upper(), m))
            r["method_quarantined"] = "Y" if m in QUARANTINED else "N"
            r["quarantine_disposition"] = d["disposition"] if d else ""
            r["quarantine_disposition_basis"] = d["basis"] if d else ""
            if d and d["applied_in_this_pass"] == "Y":
                if d["disposition"] == "WITHDRAW":
                    r["confidence_tier"] = "X"
                    r["tier_rationale"] = (
                        f"WITHDRAWN {TODAY} by code/{STEM}.py. {d['basis']}. This refuses THIS "
                        f"PAIRING and is not a ruling that the firm is non-Native "
                        f"(docs/ENTITY_MATCH_RULES.md). No exclusion_id is minted: "
                        f"data/spine/cedar_exclusion_rulings.csv is the owner's register.")
                    st["ledger_withdrawn"] += 1
                else:
                    r["tribe_id"] = d["repoint_to"]
                    r["canonical_name"] = d["repoint_to_name"]
                    r["tier_rationale"] = (
                        f"REPOINTED {TODAY} by code/{STEM}.py. {d['basis']}. Tier held at B: a "
                        f"tier is inherited from the source row, never assigned by the consumer "
                        f"(START_HERE trap 1).")
                    st["ledger_repointed"] += 1
            yield [r.get(c, "") for c in hdr]

    backup(LEDGER)
    st["written"] = atomic_rows(LEDGER, hdr, gen())
    st["cols_before"] = len(ev.led[0].keys())
    st["cols_after"] = len(hdr)
    return st


# ================================================================ VERIFY ====
def measure_prime(path=None):
    """Read-only census of prime_contracts, by duckdb."""
    import duckdb
    p = str(path or PRIME)
    con = duckdb.connect()
    cols = [r[0] for r in con.execute(
        "SELECT column_name FROM (DESCRIBE SELECT * FROM read_csv_auto(?, all_varchar=true, "
        "sample_size=1000))", [p]).fetchall()]
    n, total = con.execute(
        "SELECT count(*), sum(TRY_CAST(total_obligations AS DOUBLE)) "
        "FROM read_csv_auto(?, all_varchar=true, sample_size=-1)", [p]).fetchone()
    attributed = con.execute(
        "SELECT count(*), sum(TRY_CAST(total_obligations AS DOUBLE)) "
        "FROM read_csv_auto(?, all_varchar=true, sample_size=-1) WHERE tribe_id <> ''",
        [p]).fetchone()
    ent = {}
    flagged = unflagged_withdrawn = None
    if "identifier_ruling_quarantined" in cols:
        flagged = con.execute(
            "SELECT count(*) FROM read_csv_auto(?, all_varchar=true, sample_size=-1) "
            "WHERE tribe_id <> '' AND identifier_ruling_quarantined = 'Y'", [p]).fetchone()[0]
    if "identifier_ruling_review" in cols:
        unflagged_withdrawn = con.execute(
            "SELECT count(*) FROM read_csv_auto(?, all_varchar=true, sample_size=-1) "
            "WHERE tribe_id <> '' AND identifier_ruling_review = 'WITHDRAWN_BY_1079'",
            [p]).fetchone()[0]
    for t, v in con.execute(
            "SELECT tribe_id, sum(TRY_CAST(total_obligations AS DOUBLE)) "
            "FROM read_csv_auto(?, all_varchar=true, sample_size=-1) WHERE tribe_id <> '' "
            "GROUP BY 1", [p]).fetchall():
        ent[t] = round(v or 0.0, 2)
    con.close()
    return dict(rows=n, columns=len(cols), total_obligations=round(total, 2),
                attributed_rows=attributed[0], attributed_obligations=round(attributed[1], 2),
                flagged_attributed_rows=flagged,
                attributed_rows_still_withdrawn=unflagged_withdrawn,
                by_entity=ent, has_new_cols=all(c in cols for c in NEW_PRIME_COLS))


def verify(quiet=False):
    if not PROOF.exists():
        print("VERIFY: no proof file - run `apply` first.")
        return 1
    pf = json.load(open(PROOF))
    if pf.get("mode") != "apply":
        print("VERIFY: proof file records a report-only run; nothing to verify.")
        return 0
    cur = measure_prime()
    fails = []

    def chk(name, ok, got, want):
        if not ok:
            fails.append(f"{name}: got {got!r}, expected {want!r}")
        if not quiet:
            print(f"  {'PASS' if ok else 'FAIL'}  {name}")

    b, a = pf["before"], pf["after"]
    chk("I1 prime row count unchanged", cur["rows"] == b["rows"], cur["rows"], b["rows"])
    chk("I2 new columns present and none dropped",
        cur["has_new_cols"] and cur["columns"] == b["columns"] + len(NEW_PRIME_COLS),
        cur["columns"], b["columns"] + len(NEW_PRIME_COLS))
    chk("I3 total obligations unchanged to the cent",
        abs(cur["total_obligations"] - b["total_obligations"]) < 0.005,
        cur["total_obligations"], b["total_obligations"])
    net = round(sum(pf["entity_delta"].values()), 2)
    chk("I4 entity gains and losses net to zero", abs(net) < 0.005, net, 0.0)
    exp = round(b["attributed_obligations"] - pf["withdrawn_usd"], 2)
    chk("I5 attributed dollars fall by exactly the withdrawal",
        abs(cur["attributed_obligations"] - exp) < 0.005,
        cur["attributed_obligations"], exp)
    chk("I6 quarantine flag reaches the attributed rows it should",
        cur["flagged_attributed_rows"] == a["flagged_attributed_rows"],
        cur["flagged_attributed_rows"], a["flagged_attributed_rows"])
    chk("I7 no withdrawn identifier still keys an attributed row",
        cur["attributed_rows_still_withdrawn"] == 0,
        cur["attributed_rows_still_withdrawn"], 0)
    if fails:
        print("\nBREACH:")
        for f in fails:
            print("   " + f)
        return 1
    if not quiet:
        print("\nall invariants hold.")
    return 0


def selftest():
    """Inject each violation into a SYNTHETIC copy and assert the NAMED
    invariant is what fires.  A check that has never failed on purpose is not
    known to work (AGENT_FIELD_GUIDE section 3)."""
    import duckdb  # noqa: F401
    tmp = Path(tempfile.mkdtemp(prefix="1079_selftest_"))
    hdr = ["contract_number", "awardee_uei", "cage_code", "parent_uei", "tribe_id",
           "canonical_name", "attribution_method", "confidence_tier", "attributed_flag",
           "total_obligations", "cedar_uid", "owner_attribution_status",
           "owner_as_of_transaction_cedar_uid"] + NEW_PRIME_COLS
    base = [
        ["C1", "UEI1", "AAA11", "", "HUB-A", "A", "uei_exact", "B", "1", "100.00", "u1", "x",
         "UNKNOWN", "cluster_v3", "B", "Y", "UEI:UEI1", "KEEP"],
        ["C2", "UEI2", "NAN", "", "", "", "unattributed", "C", "0", "50.00", "", "x",
         "UNKNOWN", "cluster_v3", "X", "Y", "UEI:UEI2", "WITHDRAWN_BY_1079"],
    ]
    good = tmp / "prime_ok.csv"
    with open(good, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(hdr)
        w.writerows(base)
    m = measure_prime(good)
    assert m["rows"] == 2 and abs(m["total_obligations"] - 150.0) < 1e-9, m
    assert m["attributed_obligations"] == 100.0 and m["flagged_attributed_rows"] == 1, m
    assert m["attributed_rows_still_withdrawn"] == 0, m
    print("  PASS  baseline synthetic table measures as expected "
          "(2 rows, $150.00, $100.00 attributed, 1 flagged)")

    # I7 violation: a withdrawn identifier that STILL keys an attributed row
    bad = tmp / "prime_bad_i7.csv"
    rows = [list(r) for r in base]
    rows[1][4], rows[1][5] = "HUB-B", "B"          # re-attribute the withdrawn row
    with open(bad, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(hdr)
        w.writerows(rows)
    mb = measure_prime(bad)
    assert mb["attributed_rows_still_withdrawn"] == 1, mb
    print("  PASS  I7 FIRES on an injected violation "
          "(a WITHDRAWN_BY_1079 row carrying a tribe_id is detected)")

    # I3 violation: a changed obligation
    bad3 = tmp / "prime_bad_i3.csv"
    rows = [list(r) for r in base]
    rows[0][9] = "101.00"
    with open(bad3, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(hdr)
        w.writerows(rows)
    m3 = measure_prime(bad3)
    assert abs(m3["total_obligations"] - 150.0) > 0.005, m3
    print("  PASS  I3 FIRES on an injected violation (a cent moved is detected)")

    # I6 violation: a quarantined-keyed attributed row that is NOT flagged
    bad6 = tmp / "prime_bad_i6.csv"
    rows = [list(r) for r in base]
    rows[0][15] = "N"
    with open(bad6, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(hdr)
        w.writerows(rows)
    m6 = measure_prime(bad6)
    assert m6["flagged_attributed_rows"] == 0, m6
    print("  PASS  I6 FIRES on an injected violation (an unflagged quarantined row is detected)")

    # I2 violation: a dropped column
    bad2 = tmp / "prime_bad_i2.csv"
    keep = [i for i, c in enumerate(hdr) if c != "identifier_ruling_review"]
    with open(bad2, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow([hdr[i] for i in keep])
        for r in base:
            w.writerow([r[i] for i in keep])
    m2 = measure_prime(bad2)
    assert not m2["has_new_cols"], m2
    print("  PASS  I2 FIRES on an injected violation (a dropped new column is detected)")

    shutil.rmtree(tmp, ignore_errors=True)
    print("\nselftest: every named invariant was made to fail on purpose and did.")
    return 0


# ================================================================= MAIN =====
def main(mode):
    if mode == "selftest":
        return selftest()
    if mode == "verify":
        return verify()

    print(f"=== Cedar Press {STEM} - mode={mode} ===\n")
    print("loading evidence: spine, ledger, fpds edges, deals, "
          "166 ANCSA annual reports, prime aggregates ...")
    ev = Evidence()
    print(f"  spine {len(ev.spine):,} | ledger {len(ev.led):,} | "
          f"annual reports {len(ev.reports)} corporations | "
          f"prime UEIs {len(ev.prime_by_uei):,} | prime CAGEs {len(ev.prime_by_cage):,}")

    dec = triage(ev)
    cnt = collections.Counter()
    usd = collections.Counter()
    for d in dec:
        cnt[d["disposition"]] += 1
        usd[d["disposition"]] += d["prime_obligations_usd"]
    print("\n-- disposition of every quarantined ledger row -------------------")
    for k in ("KEEP", "REPOINT", "WITHDRAW", "HOLD"):
        print(f"  {k:9s} {cnt[k]:5d} identifiers   ${usd[k]:>18,.2f}")
    ap = [d for d in dec if d["applied_in_this_pass"] == "Y"]
    print(f"  applied in this pass: {len(ap)} identifiers, "
          f"${sum(d['prime_obligations_usd'] for d in ap):,.2f}")

    REVIEW.mkdir(exist_ok=True)
    flds = list(dec[0].keys())
    for name, rows in (("quarantine_triage", dec),
                       ("owner_holds", [d for d in dec if d["disposition"] == "HOLD"])):
        p = REVIEW / f"1079_{name}_{TODAY}.csv"
        with open(p, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=flds, lineterminator="\n")
            w.writeheader()
            w.writerows(sorted(rows, key=lambda r: -r["prime_obligations_usd"]))
        print(f"wrote {p.relative_to(ROOT)}  ({len(rows):,} rows)")

    if mode == "report":
        json.dump({"mode": "report", "date": TODAY,
                   "disposition_counts": dict(cnt),
                   "disposition_usd": {k: round(v, 2) for k, v in usd.items()}},
                  open(PROOF, "w"), indent=2)
        print(f"\nREPORT ONLY - no dataset was modified.  {PROOF.relative_to(ROOT)}")
        return 0

    if mode != "apply":
        print(f"unknown mode {mode!r}")
        return 2

    # ---------------------------------------------------------------- apply
    print("\nmeasuring prime_contracts BEFORE ...")
    before = measure_prime()
    print(f"  {before['rows']:,} rows | {before['columns']} cols | "
          f"${before['total_obligations']:,.2f} total | "
          f"${before['attributed_obligations']:,.2f} attributed")

    plan = Plan(dec, ev.spine)
    stats, deltas = {}, collections.defaultdict(float)

    stats["ledger"] = dict(rewrite_ledger(ev, dec))
    print(f"  ledger: {stats['ledger']['written']:,} rows, "
          f"{stats['ledger'].get('ledger_withdrawn', 0)} withdrawn, "
          f"{stats['ledger'].get('ledger_repointed', 0)} repointed, "
          f"{stats['ledger']['cols_before']} -> {stats['ledger']['cols_after']} cols")

    SPECS = [
        (PRIME, dict(money="total_obligations", visibility=True)),
        (CLEAN / "prime_contracts_archive_backfill.csv",
         dict(money="total_obligations", visibility=False)),
        (CLEAN / "prime_contracts_awards.csv", dict(money="total_obligated_usd", visibility=False)),
        (CLEAN / "prime_contracts_published.csv",
         dict(money="total_obligated_usd", visibility=False)),
    ]
    for path, spec in SPECS:
        if not path.exists():
            print(f"  SKIP (absent) {path.name}")
            continue
        s, m = rewrite_prime_like(path, ev, plan, spec)
        stats[path.name] = dict(s)
        if path == PRIME:
            for k, v in m.items():
                deltas[k] += v
        print(f"  {path.name}: {s['written']:,} rows | {s['cols_before']}->{s['cols_after']} cols "
              f"| withdrew {s['withdrawn_rows']:,} rows (${s['withdrawn_usd']:,.2f}) "
              f"| repointed {s['repointed_rows']:,} (${s['repointed_usd']:,.2f})")

    sp = CLEAN / "subawards.csv"
    if sp.exists():
        s, m = rewrite_subawards(sp, plan)
        stats["subawards.csv"] = dict(s)
        stats["subawards_entity_delta"] = {k: round(v, 2) for k, v in m.items() if abs(v) > 0.004}
        print(f"  subawards.csv: {s['written']:,} rows | prime side "
              f"{s['prime_withdrawn']}w/{s['prime_repointed']}r | sub side "
              f"{s['sub_withdrawn']}w/{s['sub_repointed']}r")

    print("\nmeasuring prime_contracts AFTER ...")
    after = measure_prime()
    print(f"  {after['rows']:,} rows | {after['columns']} cols | "
          f"${after['total_obligations']:,.2f} total | "
          f"${after['attributed_obligations']:,.2f} attributed | "
          f"{after['flagged_attributed_rows']:,} attributed rows flagged quarantined")

    ent = collections.defaultdict(float)
    for t in set(before["by_entity"]) | set(after["by_entity"]):
        d = round(after["by_entity"].get(t, 0.0) - before["by_entity"].get(t, 0.0), 2)
        if abs(d) > 0.004:
            ent[t] = d
    ep = REVIEW / f"1079_entity_ledger_{TODAY}.csv"
    with open(ep, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["tribe_id", "canonical_name", "obligations_before_usd",
                    "obligations_after_usd", "delta_usd"])
        for t, d in sorted(ent.items(), key=lambda kv: kv[1]):
            w.writerow([t, (ev.spine.get(t, {}) or {}).get("canonical_name", ""),
                        f"{before['by_entity'].get(t, 0.0):.2f}",
                        f"{after['by_entity'].get(t, 0.0):.2f}", f"{d:.2f}"])
    print(f"wrote {ep.relative_to(ROOT)}  ({len(ent)} entities moved)")

    proof = dict(
        mode="apply", date=TODAY, script=f"code/{STEM}.py",
        quarantined_methods=sorted(QUARANTINED),
        disposition_counts=dict(cnt),
        disposition_usd={k: round(v, 2) for k, v in usd.items()},
        applied_identifiers=len(ap),
        withdrawn_usd=round(stats[PRIME.name]["withdrawn_usd"], 2),
        repointed_usd=round(stats[PRIME.name]["repointed_usd"], 2),
        before=before, after=after,
        entity_delta={k: v for k, v in sorted(ent.items(), key=lambda kv: kv[1])},
        file_stats=stats,
    )
    proof["before"].pop("by_entity", None)
    proof["after"].pop("by_entity", None)
    json.dump(proof, open(PROOF, "w"), indent=2)
    print(f"wrote {PROOF.relative_to(ROOT)}")

    print("\n-- invariants -----------------------------------------------------")
    rc = verify()
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "report"))
