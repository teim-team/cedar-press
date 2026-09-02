#!/usr/bin/env python3
"""
Cedar Press - 167: link the nonprofit family to the spine through the EIN hub.

THE GAP
-------
Five nonprofit-family tables are joined to nothing, despite being Native
organisations by construction in a large part of their mass:

    np_orgs.csv                  12,764 rows      54 carry `entity_id`
    np_schedule_i_grants.csv     58,685 rows     552 carry a recipient tribe_id
    np_schedule_i_filers.csv     10,314 rows   1,652 carry a filer tribe_id
    np_financials.csv             8,507 rows       0 - no entity column at all
    grantmaker_funding_flows.csv 18,656 rows       0 - no entity column at all

Every one of those tables is keyed on an **EIN**. The EIN is the hub. This
script builds the hub once, from links Cedar has ALREADY made elsewhere, and
propagates it. Almost none of the linkage here is new research: it is
propagation of existing rulings across a key nobody had joined on.

WHAT IS NOT A LINK SOURCE, AND WHY - measured today
---------------------------------------------------
**The identifier ledger's EIN leg must not be imported as attribution.**
1,104 rows, and after measuring them:

    need_v6                B 1029 | C 1 | X 13     6.5% accurate (cedar_domain)
    elijah_ruling          X 42                    every one is a NEGATIVE ruling
    institution_exact_name B 15 | C 3 | X 1
    ...tier A: ZERO

Of the 1,011 positive ledger EINs that also sit in `np_orgs`, 599 propose a
link `np_orgs` does not have. Reading them one at a time is enough:

    ONONDAGA GOLF AND COUNTRY CLUB        -> Onondaga Nation
    TUSCARORA GOLF CLUB INC               -> Tuscarora Nation
    LENAPE VALLEY SOCCER CLUB INC         -> Lenape Indian Tribe of Delaware
    AKWESASNE BOYS & GIRLS CLUB           -> St. Croix          (Wisconsin)
    ONONDAGA COMMUNITY COLLEGE FOUNDATION -> Onondaga Nation

That is need_v6 behaving exactly as documented. **The ledger's EIN leg enters
this build ONLY through its 55 tier-X rows, as exclusions.** Its 1,044 positive
rows are not imported at all, in either direction - not as links and not as
conflicts, because a 6.5%-accurate disagreement is not evidence about the row
it disagrees with, and 97 such disagreements in a review queue is 97 ways to
spend a person's attention on need_v6.

The same applies to `np_ein_uei_bridge.csv`'s `tribe_id_token_match` column:
UNITED HOUMA NATION INC -> *United Auburn*, MACHIS LOWER CREEK -> *Confederated
Coos*, DOUGLAS-CHEROKEE ECONOMIC AUTHORITY -> *Douglas* (Alaska). Not used.
What that file IS good for is its second identifier: **EIN -> UEI**, and the
UEI leg of the ledger is a different, better population (`cluster_v3`, 97.7%).
24 of its 28 UEIs resolve there, and the UEI answer CORRECTS the token column
on both Houma and Kickapoo.

THE HUB SOURCES, each contributing its OWN tier
------------------------------------------------
  H1  np_orgs.tribe_id / entity_tier            - script 70's name pass
  H2  fac_tribal_single_audits.auditee_ein      - script 147. The strongest
      source in the build: the auditee told the federal government it is an
      Indian tribe or tribal organisation, and the EIN is its own.
  H3  advocacy_passthrough.recipient_ein        - script 111
  H4  bie_uio_identifier_links.ein              - script 75
  H5  np_ein_uei_bridge.ein -> UEI -> ledger UEI row
  H6  intertribal_orgs.ein / nho_register.ein   - the registers that SEEDED
      the spine's ITO and NHO classes, resolved back onto it by name

  XX  EXCLUSIONS, applied last and unconditionally:
      cedar_identifier_ledger_final tier X (56 rows, 55 distinct EINs) and
      data/spine/nonprofit_exclusion_rulings.csv (4,656 EINs).

A TIER IS INHERITED FROM THE SOURCE ROW, NEVER ASSIGNED HERE
------------------------------------------------------------
No rule in this file promotes a tier. Where two sources agree on the entity the
link keeps the best tier ANY of them carried on its own row, and records that
it was corroborated; two tier-B legs stay tier B, because two-leg promotion is
a ledger method (`agent_research_two_leg`) and not something a consumer may
mint. Where two sources name DIFFERENT entities, nothing is written.

THE CLASS IS READ OFF THE SPINE ROW
------------------------------------
`native_entity_class` is derived from the spine's own `entity_class` and never
from the organisation's name, its state, or what this script thinks it is.

Reads   data/spine/cedar_entity_spine.csv
        data/spine/nonprofit_exclusion_rulings.csv
        data/clean/{np_orgs,fac_tribal_single_audits,advocacy_passthrough}.csv
        data/clean/{bie_uio_identifier_links,np_ein_uei_bridge}.csv
        data/clean/{intertribal_orgs,nho_register}.csv
        data/clean/cedar_identifier_ledger_final.csv
Writes  data/clean/np_ein_entity_hub.csv                            new
        data/clean/{np_orgs,np_financials}.csv                      in place
        data/clean/{np_schedule_i_grants,np_schedule_i_filers}.csv  in place
        data/clean/grantmaker_funding_flows.csv                     in place
        data/clean/codebook/06b_np_entity_hub.csv                   fragment
        review/np_ein_hub_conflicts_<date>.csv
        review/np_ein_hub_exclusion_hits_<date>.csv
        review/np_name_candidates_<date>.csv
        logs/163_report_<date>.txt

NUMBERING: this was written as 163 and renumbered to 167 mid-session, because
three OTHER agents claimed 163 concurrently (`163_promote_nho_universe_in_place
.py`, `163_link_adjudication_hubs.py`, `163_load_sam_contract_awards.py`). The
prefix does not imply step order - check `ls code/<n>_*` before claiming one.

    py -3 code/167_link_nonprofit_family_via_ein_hub.py --check
    py -3 code/167_link_nonprofit_family_via_ein_hub.py
"""

import csv
import functools
import importlib.util
import os
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
SPINEDIR = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
LOGS = CEDAR / "logs"
CODEBOOK = CLEAN / "codebook"
TODAY = date.today().isoformat()
SCRIPT = "167_link_nonprofit_family_via_ein_hub.py"

csv.field_size_limit(10 ** 8)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

REPORT = []


def say(s=""):
    print(s)
    REPORT.append(s)


# --------------------------------------------------------------------- io ---

def rd(p):
    p = Path(p)
    if not p.exists():
        say(f"    !! missing {p}")
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def wr(p, rows, fields=None):
    """Write `.part`, then rename. An interruption must not look like a
    completion (START_HERE, standing rule)."""
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or (list(rows[0].keys()) if rows else [])
    tmp = p.with_suffix(p.suffix + ".part")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, p)
    say(f"    wrote {p.relative_to(CEDAR)}  ({len(rows):,} rows)")


def rewrite_in_place(p, rows, extra_cols):
    p = Path(p)
    bak = Path(str(p) + f".bak_{TODAY}_pre167")
    if not bak.exists():
        shutil.copy2(p, bak)
        say(f"    backed up -> {bak.name}")
    fields = list(rows[0].keys())
    for c in extra_cols:
        if c not in fields:
            fields.append(c)
    wr(p, rows, fields)


def dig(s):
    return re.sub(r"\D", "", s or "")


# ----------------------------------------------------------------- class ----
# Read off the SPINE row's own entity_class. Never inferred from a name.
CLASS_MAP = {
    "Alaska Native Regional Corporation": "ANC",
    "Alaska Native Village Corporation": "ANC",
    "ANCSA Group Corporation": "ANC",
    "Native Hawaiian Organization": "NHO",
    "Federally recognized tribe": "tribe",
    "Federally recognized Alaska Native Village": "tribe",
    "State-recognized tribe": "tribe",
    "BIE School": "native org",
    "Tribal College or University": "native org",
    "Native Community Development Financial Institution": "native org",
    "Native Financial Institution": "native org",
    "Intertribal Organization": "native org",
    "Urban Indian Organization": "native org",
    "Federal-level constituency entity": "native org",
    "State-level constituency entity": "native org",
    "Federal-level self-governance consortium": "native org",
}


def coarse(entity_class):
    return CLASS_MAP.get((entity_class or "").strip(), "unknown")


# ---------------------------------------------------------------- resolver --

def load_m33():
    spec = importlib.util.spec_from_file_location(
        "m33", CEDAR / "code" / "33_apply_party_rulings.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def load_domain():
    spec = importlib.util.spec_from_file_location(
        "cedar_domain", CEDAR / "code" / "cedar_domain.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


M = load_m33()
DOM = load_domain()
# Pure memoisation, exactly as script 70 does it. norm/core are pure functions
# of a string, so caching cannot change an answer - it only stops the same
# 1,310 spine names being re-normalised tens of millions of times.
M.norm = functools.lru_cache(maxsize=None)(M.norm)
M.core = functools.lru_cache(maxsize=None)(M.core)
norm = M.norm

# Legal forms a Native entity cannot be. Lifted from code/70 (itself from
# code/65). A statement about what the organisation IS, not a similarity score.
BARRED = [
    (re.compile(r"^\s*city of\b", re.I), "a municipality"),
    (re.compile(r"^\s*town of\b", re.I), "a municipality"),
    (re.compile(r"^\s*county of\b|\bcounty government\b", re.I), "a county"),
    (re.compile(r"^\s*state of\b", re.I), "a state government"),
    (re.compile(r"\bmines?\b|\bmining (co|corp|company)\b", re.I), "a mining company"),
    (re.compile(r"\b(power|irrigation|water|utility|electric)\s+district\b", re.I),
     "a special district"),
    (re.compile(r"\bsalt river project\b", re.I), "the Salt River Project"),
    (re.compile(r"\bschool district\b", re.I), "a school district"),
    (re.compile(r"\bchamber of commerce\b", re.I), "a chamber of commerce"),
    (re.compile(r"\bcooperative\b|\bco-?op\b", re.I), "a member cooperative"),
    (re.compile(r"\brotary\b|\bkiwanis\b|\blions club\b|\boptimist club\b", re.I),
     "a service club"),
    (re.compile(r"\bfarm bureau\b|\b4-?h\b|\bffa\b", re.I), "an agricultural body"),
    (re.compile(r"\bymca\b|\bywca\b|\bboy scouts\b|\bgirl scouts\b", re.I),
     "a national youth or fitness affiliate"),
    (re.compile(r"\bunited way\b", re.I),
     "a United Way chapter - the measured `united` trap"),
    (re.compile(r"\bhistorical society\b|\bgenealogical\b", re.I),
     "a county historical or genealogical society"),
]
EXEMPT = re.compile(
    r"salish kootenai college|haskell|dine college|ilisagvik|"
    r"college of the menominee|sinte gleska|oglala lakota college|"
    r"tribal college|navajo technical", re.I)


def org_type_bar(name):
    if EXEMPT.search(name or ""):
        return ""
    for rx, why in BARRED:
        if rx.search(name or ""):
            return why
    return ""


@functools.lru_cache(maxsize=None)
def _resolve(name):
    return M.resolve_entity(name, SPINE_ROWS_T)


# --- review-queue triage. NOT a matcher, and it never creates a link. -------
# Its only job is to stop 2,474 containment refusals burying the handful that
# a person could actually rule on. The test is script 148's: does the name
# carry a word that occurs in exactly ONE spine entity and is not a trap?
_TRIAGE_STOP = {
    "the", "of", "and", "inc", "incorporated", "llc", "corporation", "company",
    "corp", "ltd", "limited", "tribe", "tribal", "nation", "native", "indian",
    "alaska", "alaskan", "village", "community", "band", "pueblo", "council",
    "group", "services", "service", "center", "centre", "foundation",
    "institute", "association", "society", "enterprises", "enterprise",
    "holdings", "health", "housing", "authority", "school", "college",
    "university", "fund", "trust", "development", "management", "program",
    "programs", "project", "america", "american", "united", "national",
    "regional", "county", "state", "city", "north", "south", "east", "west",
    "new", "town", "cook", "clark", "graham", "hughes", "burns", "salmon",
}
_UNIQUE_TOKENS = None


def _unique_tokens():
    global _UNIQUE_TOKENS
    if _UNIQUE_TOKENS is None:
        seen = defaultdict(set)
        for r in SPINE_ROWS_T:
            for w in norm(r["canonical_name"]).split():
                if w in _TRIAGE_STOP or len(w) < 5:
                    continue
                seen[w].add(r["tribe_id"])
        _UNIQUE_TOKENS = {w for w, ids in seen.items() if len(ids) == 1}
    return _UNIQUE_TOKENS


def triage(name):
    toks = set(norm(name).split()) - DOM.NAME_TRAPS
    return "PLAUSIBLE" if toks & _unique_tokens() else "CONTAINMENT_NOISE"


def deterministic_name_match(name, state=""):
    """exact / alias / core ONLY. Containment and token paths are refused here.

    Containment has failed ten distinct ways in this repo and every one of them
    landed on a nonprofit-shaped name. This pass is deliberately narrower than
    script 148's, which used containment and a token path and whose 2,138
    proposals are still unruled in `review/`.

    Returns (tribe_id, canonical_name, how) or (None, None, reason).
    """
    nm = (name or "").strip()
    if len(nm) < 4:
        return None, None, "name_too_short"
    tid, canon, how = _resolve(nm)
    if not tid:
        return None, None, how or "no_spine_match"
    # The organisation-type bar is applied AFTER resolution, deliberately. Run
    # first it would file 1,306 Rotary clubs and YMCAs in the review queue that
    # never matched anything - noise that makes the queue unreadable. A bar is
    # only interesting where it STOPPED a match.
    bar = org_type_bar(nm)
    if bar:
        return None, None, f"org_type_barred:{bar}"
    if how not in ("exact", "alias", "core"):
        return None, None, f"non_deterministic:{how}"
    # NAME_TRAPS: a whole-name match carrying a trap token still needs the
    # state before it counts. `Oneida Nation`/WI onto spine `Oneida`/NY is the
    # $716M mis-split.
    toks = set(norm(nm).split())
    traps = toks & DOM.NAME_TRAPS
    row = SPINE_BY_ID.get(tid, {})
    sstate = (row.get("state") or "").strip().upper()
    rstate = (state or "").strip().upper()
    if traps:
        if not (rstate and sstate and rstate == sstate):
            return None, None, ("name_trap_without_state_agreement:"
                                + ",".join(sorted(traps)))
    # A tribe name followed by a place suffix is a PLACE.
    words = norm(nm).split()
    for i, w in enumerate(words[:-1]):
        if w in toks and words[i + 1] in DOM.PLACE_SUFFIXES and w in set(
                norm(canon).split()):
            return None, None, f"place_suffix:{w} {words[i+1]}"
    # State disagreement demotes to a candidate, never a link.
    if rstate and sstate and rstate != sstate:
        return None, None, f"state_disagreement:{rstate}_vs_{sstate}"
    return tid, canon, how


# ============================================================== the hub ======

def build_hub(spine_by_id):
    """ein -> list of candidate dicts, one per source."""
    cand = defaultdict(list)

    def add(ein, tid, tier, src, basis, method=""):
        e = dig(ein)
        if not (e and tid):
            return
        if tid not in spine_by_id:
            SKIPPED[f"{src}: entity_id not in spine"] += 1
            return
        cand[e].append({"entity_id": tid, "tier": (tier or "B").strip().upper(),
                        "source": src, "basis": basis, "method": method})

    # -- H1 np_orgs -----------------------------------------------------
    for r in NP_ORGS:
        if r.get("tribe_id", "").strip():
            add(r["EIN"], r["tribe_id"], r.get("entity_tier") or "B",
                "np_orgs", f"script 70 name pass: {r.get('entity_match_basis','')}"[:220],
                r.get("entity_match_method", ""))

    # -- H2 FAC tribal Single Audits ------------------------------------
    for r in rd(CLEAN / "fac_tribal_single_audits.csv"):
        if r.get("entity_id", "").strip():
            add(r["auditee_ein"], r["entity_id"], r.get("entity_tier") or "B",
                "fac_single_audits",
                "auditee filed a Single Audit under entity_type=tribal; "
                f"entity keyed by script 147 ({r.get('entity_match_method','')})",
                r.get("entity_match_method", ""))

    # -- H3 advocacy passthrough ----------------------------------------
    # The row's own `tier` column grades the FUNDING->LOBBYING CHAIN, not the
    # entity link, so it may not be inherited as a link tier. There is no link
    # tier on the row; the link therefore enters at B and never above it.
    for r in rd(CLEAN / "advocacy_passthrough.csv"):
        if r.get("recipient_entity_id", "").strip():
            add(r["recipient_ein"], r["recipient_entity_id"], "B",
                "advocacy_passthrough",
                "recipient keyed by script 111; the row's own tier grades the "
                "funding->lobbying chain, not this link, so B is the floor",
                "")

    # -- H4 BIE / UIO identifier links ----------------------------------
    for r in rd(CLEAN / "bie_uio_identifier_links.csv"):
        if r.get("tribe_id", "").strip() and dig(r.get("ein")):
            add(r["ein"], r["tribe_id"], r.get("confidence_tier") or "B",
                "bie_uio_identifier_links",
                f"script 75 identifier link: {r.get('tier_rationale','')}"[:220],
                r.get("match_method", ""))

    # -- H5 EIN -> UEI -> ledger UEI leg --------------------------------
    uei_led = defaultdict(list)
    for r in LEDGER:
        if (r.get("identifier_type") or "").upper() == "UEI" \
                and r.get("identifier", "").strip() and r.get("tribe_id", "").strip():
            uei_led[r["identifier"].strip().upper()].append(r)
    for r in rd(CLEAN / "np_ein_uei_bridge.csv"):
        u = (r.get("uei") or "").strip().upper()
        for lr in uei_led.get(u, []):
            if (lr.get("confidence_tier") or "") == "X":
                continue
            add(r["ein"], lr["tribe_id"], lr.get("confidence_tier") or "B",
                "ein_uei_bridge_to_ledger",
                f"EIN->UEI {u} on np_ein_uei_bridge, then the ledger's UEI leg "
                f"({lr.get('attribution_method','')}, tier "
                f"{lr.get('confidence_tier','')}) - inherited, not promoted",
                lr.get("attribution_method", ""))

    # -- H6 the ITO and NHO registers -----------------------------------
    # These two files SEEDED the spine's Intertribal Organization and Native
    # Hawaiian Organization classes (scripts 36/61). Resolving a register row
    # back onto the spine by its own name is reading the spine's own source,
    # not a fresh name guess - so exact/alias/core only, same bar as everywhere.
    for fn, src, namecol in [("intertribal_orgs.csv", "intertribal_register",
                              "organization_name"),
                             ("nho_register.csv", "nho_register",
                              "organization_name")]:
        for r in rd(CLEAN / fn):
            if not dig(r.get("ein")):
                continue
            tid, canon, how = deterministic_name_match(r.get(namecol, ""),
                                                       r.get("state", ""))
            if tid:
                add(r["ein"], tid, "B", src,
                    f"register row '{r.get(namecol,'')}' resolved onto the "
                    f"spine it seeded ({how})", how)
            else:
                SKIPPED[f"{src}: {str(how).split(':')[0]}"] += 1
    return cand


# ============================================================== main =========

SKIPPED = Counter()
SPINE_ROWS_T = ()
SPINE_BY_ID = {}
NP_ORGS = []
LEDGER = []


def main():
    global SPINE_ROWS_T, SPINE_BY_ID, NP_ORGS, LEDGER
    check = "--check" in sys.argv
    say("=== 163: link the nonprofit family through the EIN hub ===")
    say(f"    {TODAY}   mode={'CHECK (writes nothing)' if check else 'WRITE'}\n")

    spine = rd(SPINEDIR / "cedar_entity_spine.csv")
    SPINE_ROWS_T = tuple(spine)
    SPINE_BY_ID = {r["tribe_id"]: r for r in spine}
    NP_ORGS = rd(CLEAN / "np_orgs.csv")
    LEDGER = rd(CLEAN / "cedar_identifier_ledger_final.csv")
    say(f"  spine entities : {len(spine):,}")
    say(f"  np_orgs rows   : {len(NP_ORGS):,}")

    # ---------------------------------------------------- exclusions -----
    excl = {}
    for r in rd(SPINEDIR / "nonprofit_exclusion_rulings.csv"):
        if (r.get("reinstated") or "").strip() in ("1", "yes", "Y", "true"):
            continue
        e = dig(r.get("ein"))
        if e:
            excl[e] = (f"nonprofit_exclusion_rulings {r.get('exclusion_id','')}: "
                       f"{r.get('exclusion_reason','')}")
    n_np_excl = len(excl)
    for r in LEDGER:
        if (r.get("identifier_type") or "").upper() != "EIN":
            continue
        if (r.get("confidence_tier") or "") != "X":
            continue
        e = dig(r.get("identifier"))
        if e:
            excl[e] = (f"cedar_identifier_ledger_final tier X "
                       f"({r.get('attribution_method','')}) against "
                       f"{r.get('tribe_id','')}: {r.get('tier_rationale','') or 'ruled out'}")[:300]
    say(f"  exclusion EINs : {len(excl):,}  "
        f"({n_np_excl:,} nonprofit rulings + {len(excl)-n_np_excl:,} ledger tier X)")

    # ---------------------------------------------------- the hub --------
    say("\n[1] building the EIN hub")
    cand = build_hub(SPINE_BY_ID)
    say(f"    candidate EINs from all sources: {len(cand):,}")
    for k, v in sorted(Counter(c["source"] for cs in cand.values()
                               for c in cs).items()):
        say(f"      {k:28s} {v:>6,} candidate rows")
    for k, v in SKIPPED.most_common():
        say(f"      skipped: {k:36s} {v:>5,}")

    TIER_RANK = {"A": 3, "B": 2, "C": 1, "": 0, "X": -1}
    hub, conflicts, excl_hits = {}, [], []
    for ein, cs in sorted(cand.items()):
        if ein in excl:
            excl_hits.append({
                "ein": ein,
                "org_name": NAME_BY_EIN.get(ein, ""),
                "blocked_entity_ids": "; ".join(sorted({c["entity_id"] for c in cs})),
                "blocked_sources": "; ".join(sorted({c["source"] for c in cs})),
                "exclusion": excl[ein],
                "note": "A ruled-out EIN must never resurface through another "
                        "table. No link written.",
                "built_date": TODAY,
            })
            continue
        ids = {c["entity_id"] for c in cs}
        resolved_by = ""
        if len(ids) > 1:
            # SPECIFICITY PRECEDENCE, and nothing wider than that.
            #
            # AGENTS.md's standing repair for the containment defect is
            # "require the record to be at least as specific as the entity",
            # and `resolve_entity` itself ranks exact > core > alias >
            # containment. Where exactly ONE candidate entity is supported by
            # a deterministic method and EVERY rival rests only on
            # containment, the deterministic one wins. This is not a new
            # judgement: it is the documented rule, applied to two answers
            # that already exist.
            #
            # It matters because the losing side is always the same defect -
            # `RED LAKE NATION COLLEGE` -> the Red Lake Band, `COLLEGE OF THE
            # MENOMINEE NATION` -> the Menominee Tribe, `MAKAHA HAWAIIAN CIVIC
            # CLUB` -> "Hawaiian Native Corporation". The tribe is not the
            # college, and a containment link onto the parent government books
            # an institution's money to its tribe.
            det = {c["entity_id"] for c in cs
                   if c["method"] in ("exact", "core", "alias")}
            rest = {c["entity_id"] for c in cs
                    if c["method"] not in ("exact", "core", "alias")}
            if len(det) == 1 and all(
                    c["method"] in ("containment", "contain", "")
                    for c in cs if c["entity_id"] not in det):
                keep = det.pop()
                resolved_by = ("specificity precedence: a deterministic "
                               "(exact/core/alias) match outranks a "
                               "containment match onto a broader entity")
                conflicts.append({
                    "ein": ein,
                    "org_name": NAME_BY_EIN.get(ein, ""),
                    "n_sources": len(cs),
                    "proposals": "; ".join(
                        f"{c['entity_id']}({SPINE_BY_ID[c['entity_id']]['canonical_name']})"
                        f"<-{c['source']}/{c['method'] or 'n/a'}/tier {c['tier']}"
                        for c in cs),
                    "auto_resolved_to": keep,
                    "auto_resolved_name": SPINE_BY_ID[keep]["canonical_name"],
                    "auto_resolution_basis": resolved_by,
                    "question": "Specificity precedence picked the more "
                                "specific entity and DROPPED the containment "
                                "match onto the broader one. Confirm or "
                                "correct.",
                    "YOUR_RULING": "",
                    "YOUR_NOTE": "",
                    "built_date": TODAY,
                })
                cs = [c for c in cs if c["entity_id"] == keep]
                ids = {keep}
                AUTO_RESOLVED.append((ein, keep, rest))
        if len(ids) > 1:
            conflicts.append({
                "ein": ein,
                "org_name": NAME_BY_EIN.get(ein, ""),
                "n_sources": len(cs),
                "proposals": "; ".join(
                    f"{c['entity_id']}({SPINE_BY_ID[c['entity_id']]['canonical_name']})"
                    f"<-{c['source']}/{c['method'] or 'n/a'}/tier {c['tier']}"
                    for c in cs),
                "auto_resolved_to": "",
                "auto_resolved_name": "",
                "auto_resolution_basis": "",
                "question": "Two Cedar tables key this EIN to DIFFERENT spine "
                            "entities and specificity precedence does not "
                            "separate them. NO LINK WRITTEN. Which is right, "
                            "or is neither?",
                "YOUR_RULING": "",
                "YOUR_NOTE": "",
                "built_date": TODAY,
            })
            continue
        tid = ids.pop()
        best = max(cs, key=lambda c: TIER_RANK.get(c["tier"], 0))
        tier = best["tier"] if best["tier"] in ("A", "B", "C") else "B"
        srow = SPINE_BY_ID[tid]
        srcs = sorted({c["source"] for c in cs})
        hub[ein] = {
            "ein": ein,
            "org_name": NAME_BY_EIN.get(ein, ""),
            "entity_id": tid,
            "entity_canonical_name": srow["canonical_name"],
            "entity_class": srow["entity_class"],
            "native_entity_class": coarse(srow["entity_class"]),
            "entity_state": srow.get("state", ""),
            "link_tier": tier,
            "link_tier_source": best["source"],
            "link_method": best["method"],
            "n_corroborating_sources": len(srcs),
            "link_sources": "; ".join(srcs),
            "link_basis": best["basis"],
            "tier_note": (
                "Tier is INHERITED from the source row named in "
                "`link_tier_source`. Corroboration by a second source is "
                "recorded in `n_corroborating_sources` and NEVER promotes the "
                "tier - two-leg promotion is a ledger method, not a consumer's "
                "to mint."),
            "built_by_script": SCRIPT,
            "built_date": TODAY,
        }

    say(f"    hub EINs written              : {len(hub):,}")
    say(f"    conflicts seen               : {len(conflicts):,}")
    say(f"      auto-resolved by specificity precedence: {len(AUTO_RESOLVED):,}")
    say(f"      refused, no link written              : "
        f"{len(conflicts)-len(AUTO_RESOLVED):,}")
    say(f"    refused - prior exclusion     : {len(excl_hits):,}")
    tc = Counter(h["link_tier"] for h in hub.values())
    say(f"    hub tier distribution         : "
        + ", ".join(f"{k} {v:,}" for k, v in sorted(tc.items())))
    cc = Counter(h["native_entity_class"] for h in hub.values())
    say(f"    hub class distribution        : "
        + ", ".join(f"{k} {v:,}" for k, v in cc.most_common()))
    multi = sum(1 for h in hub.values() if h["n_corroborating_sources"] > 1)
    say(f"    EINs corroborated by 2+ sources: {multi:,}")

    # links np_orgs ALREADY carries that a prior ruling forbids
    resurfaced = [h for h in excl_hits
                  if NP_BY_EIN.get(h["ein"], {}).get("tribe_id", "").strip()]
    for h in excl_hits:
        h["np_orgs_already_carries_this_link"] = (
            NP_BY_EIN.get(h["ein"], {}).get("tribe_id", "").strip() or "")
    say(f"    ...of the exclusion hits, {len(resurfaced):,} are links np_orgs "
        f"ALREADY carries and that a ruling forbids")

    # ---------------------------------------------------- propagation ----
    say("\n[2] propagating the hub into the five tables")
    summary = []
    name_cands = []

    def link_cols(prefix):
        # `spine_entity_id`, not `entity_id`. The spine's OWN `cedar_entity_id`
        # column is a different identifier system entirely - a short public
        # code (T-, A-, N-, E-, I-, NP-) - and reusing that name for a
        # `tribe_id` would invite a join between two things that are not the
        # same key. Same reason `link_tier` is not `entity_tier`: np_orgs
        # already carries `entity_tier` from script 70.
        return [f"{prefix}spine_entity_id", f"{prefix}spine_canonical_name",
                f"{prefix}spine_entity_class", f"{prefix}native_entity_class",
                f"{prefix}link_tier", f"{prefix}link_basis",
                f"{prefix}link_key", f"{prefix}link_sources"]

    def apply_link(row, prefix, ein, namecol=None, statecol=None, dataset=""):
        """EIN first. Name only where the EIN missed. Returns 'ein'/'name'/''."""
        for c in link_cols(prefix):
            row.setdefault(c, "")
        e = dig(ein)
        if e and e in hub:
            h = hub[e]
            row[f"{prefix}spine_entity_id"] = h["entity_id"]
            row[f"{prefix}spine_canonical_name"] = h["entity_canonical_name"]
            row[f"{prefix}spine_entity_class"] = h["entity_class"]
            row[f"{prefix}native_entity_class"] = h["native_entity_class"]
            row[f"{prefix}link_tier"] = h["link_tier"]
            row[f"{prefix}link_basis"] = h["link_basis"]
            row[f"{prefix}link_key"] = f"EIN {e}"
            row[f"{prefix}link_sources"] = h["link_sources"]
            return "ein"
        if e and e in excl:
            row[f"{prefix}link_basis"] = "REFUSED: " + excl[e][:200]
            row[f"{prefix}link_tier"] = "X"
            return "excluded"
        if not namecol:
            return ""
        nm = (row.get(namecol) or "").strip()
        if not nm:
            return ""
        st = (row.get(statecol) or "") if statecol else ""
        tid, canon, how = deterministic_name_match(nm, st)
        if tid:
            srow = SPINE_BY_ID[tid]
            row[f"{prefix}spine_entity_id"] = tid
            row[f"{prefix}spine_canonical_name"] = canon
            row[f"{prefix}spine_entity_class"] = srow["entity_class"]
            row[f"{prefix}native_entity_class"] = coarse(srow["entity_class"])
            # A name match is a name match. It never reaches A here.
            row[f"{prefix}link_tier"] = "B"
            row[f"{prefix}link_basis"] = (
                f"deterministic name match ({how}) via "
                f"33_apply_party_rulings.resolve_entity; no EIN in the hub")
            row[f"{prefix}link_key"] = f"NAME {nm}"
            row[f"{prefix}link_sources"] = "resolve_entity"
            NAME_HITS[(dataset, nm, tid, canon, how)] += 1
            return "name"
        NAME_MISS[(dataset, nm, str(how))] += 1
        return ""

    # ---- np_orgs -------------------------------------------------------
    rows = NP_ORGS
    before = sum(1 for r in rows if r.get("entity_id", "").strip())
    st = Counter()
    filled_entity_id = 0
    for r in rows:
        st[apply_link(r, "cedar_", r.get("EIN"))] += 1
        # `entity_id` is the PUBLISHABLE key and script 70's rule is that it is
        # set only at tier A. Fill it where it is blank and the hub tier is A -
        # additively, never overwriting a value script 70 already wrote.
        if not (r.get("entity_id") or "").strip()                 and r.get("cedar_link_tier") == "A"                 and r.get("cedar_spine_entity_id", "").strip():
            r["entity_id"] = r["cedar_spine_entity_id"]
            filled_entity_id += 1
    after = sum(1 for r in rows if r.get("cedar_spine_entity_id", "").strip())
    say(f"    np_orgs `entity_id` (the publishable key) filled on "
        f"{filled_entity_id:,} further rows at inherited tier A; total now "
        f"{sum(1 for r in rows if (r.get('entity_id') or '').strip()):,}")
    summary.append(("np_orgs.csv", len(rows), before, after, st))
    if not check:
        rewrite_in_place(CLEAN / "np_orgs.csv", rows, link_cols("cedar_"))

    # ---- np_schedule_i_filers -----------------------------------------
    rows = rd(CLEAN / "np_schedule_i_filers.csv")
    before = sum(1 for r in rows if r.get("filer_tribe_id_np_orgs", "").strip())
    st = Counter()
    for r in rows:
        st[apply_link(r, "cedar_filer_", r.get("filer_ein"),
                      "filer_name_as_filed", "filer_state",
                      "np_schedule_i_filers")] += 1
    after = sum(1 for r in rows if r.get("cedar_filer_spine_entity_id", "").strip())
    summary.append(("np_schedule_i_filers.csv", len(rows), before, after, st))
    if not check:
        rewrite_in_place(CLEAN / "np_schedule_i_filers.csv", rows,
                         link_cols("cedar_filer_"))

    # ---- np_schedule_i_grants (BOTH sides) -----------------------------
    rows = rd(CLEAN / "np_schedule_i_grants.csv")
    before = sum(1 for r in rows if r.get("recipient_np_orgs_tribe_id", "").strip())
    stf, stg = Counter(), Counter()
    for r in rows:
        stf[apply_link(r, "cedar_filer_", r.get("filer_ein"),
                       "filer_name_as_filed", "filer_state",
                       "np_schedule_i_grants.filer")] += 1
        stg[apply_link(r, "cedar_recipient_", r.get("recipient_ein"),
                       "recipient_name_as_filed", "recipient_state",
                       "np_schedule_i_grants.recipient")] += 1
    after_r = sum(1 for r in rows if r.get("cedar_recipient_spine_entity_id", "").strip())
    after_f = sum(1 for r in rows if r.get("cedar_filer_spine_entity_id", "").strip())
    after_e = sum(1 for r in rows if r.get("cedar_recipient_spine_entity_id", "").strip()
                  or r.get("cedar_filer_spine_entity_id", "").strip())
    summary.append(("np_schedule_i_grants.csv (recipient)", len(rows), before,
                    after_r, stg))
    summary.append(("np_schedule_i_grants.csv (filer)", len(rows),
                    0, after_f, stf))
    summary.append(("np_schedule_i_grants.csv (either side)", len(rows), before,
                    after_e, Counter()))
    if not check:
        rewrite_in_place(CLEAN / "np_schedule_i_grants.csv", rows,
                         link_cols("cedar_filer_") + link_cols("cedar_recipient_"))

    # ---- np_financials -------------------------------------------------
    rows = rd(CLEAN / "np_financials.csv")
    st = Counter()
    for r in rows:
        st[apply_link(r, "cedar_", r.get("ein"), "org_name", "state",
                      "np_financials")] += 1
    after = sum(1 for r in rows if r.get("cedar_spine_entity_id", "").strip())
    summary.append(("np_financials.csv", len(rows), 0, after, st))
    if not check:
        rewrite_in_place(CLEAN / "np_financials.csv", rows, link_cols("cedar_"))

    # ---- grantmaker_funding_flows (BOTH sides) -------------------------
    rows = rd(CLEAN / "grantmaker_funding_flows.csv")
    stf, stg = Counter(), Counter()
    for r in rows:
        stf[apply_link(r, "cedar_funder_", r.get("funder_ein"),
                       "funder_name_canonical", "funder_state",
                       "grantmaker_funding_flows.funder")] += 1
        stg[apply_link(r, "cedar_recipient_", r.get("recipient_ein"),
                       "recipient_name_as_filed", "recipient_state",
                       "grantmaker_funding_flows.recipient")] += 1
    after_f = sum(1 for r in rows if r.get("cedar_funder_spine_entity_id", "").strip())
    after_r = sum(1 for r in rows if r.get("cedar_recipient_spine_entity_id", "").strip())
    summary.append(("grantmaker_funding_flows.csv (funder)", len(rows), 0,
                    after_f, stf))
    summary.append(("grantmaker_funding_flows.csv (recipient)", len(rows), 0,
                    after_r, stg))
    if not check:
        rewrite_in_place(CLEAN / "grantmaker_funding_flows.csv", rows,
                         link_cols("cedar_funder_") + link_cols("cedar_recipient_"))

    say("")
    say(f"    {'table':44s} {'rows':>8s} {'before':>8s} {'after':>8s} {'%':>7s}")
    for name, n, b, a, st in summary:
        say(f"    {name:44s} {n:>8,} {b:>8,} {a:>8,} {100.0*a/max(n,1):>6.1f}%")
        if st:
            bits = ", ".join(f"{k or 'unlinked'} {v:,}" for k, v in st.most_common())
            say(f"      by route: {bits}")

    # ---------------------------------------------------- review ---------
    say("\n[3] what went to review rather than being forced")
    agg = defaultdict(lambda: {"n_rows": 0, "datasets": set()})
    for (ds, nm, why), n in NAME_MISS.items():
        k = (nm, why)
        agg[k]["n_rows"] += n
        agg[k]["datasets"].add(ds)
    for (nm, why), v in agg.items():
        if why.startswith("no_spine_match") or why == "name_too_short":
            continue          # an ordinary charity is not a review item
        name_cands.append({
            "org_name": nm,
            "refusal_reason": why,
            "triage": triage(nm),
            "n_rows_affected": v["n_rows"],
            "datasets": "; ".join(sorted(v["datasets"])),
            "question": "Is this organisation a Native entity already on the "
                        "spine, a Native entity MISSING from the spine, or "
                        "neither?",
            "triage_note": "TRIAGE IS NOT A MATCH. `PLAUSIBLE` means the name "
                           "contains a word that occurs in exactly one spine "
                           "entity and is not in NAME_TRAPS. "
                           "`CONTAINMENT_NOISE` means the refusal rests on a "
                           "generic or shared word - the containment defect. "
                           "Neither creates a link.",
            "YOUR_RULING": "",
            "YOUR_NOTE": "",
            "built_date": TODAY,
        })
    name_cands.sort(key=lambda r: (r["triage"] != "PLAUSIBLE",
                                   -r["n_rows_affected"]))
    say(f"    triage: "
        + ", ".join(f"{k} {v:,}" for k, v in
                    Counter(r["triage"] for r in name_cands).most_common()))
    reasons = Counter(r["refusal_reason"].split(":")[0] for r in name_cands)
    say(f"    name candidates queued : {len(name_cands):,}")
    for k, v in reasons.most_common(12):
        say(f"      {k:44s} {v:>5,}")
    no_match = sum(n for (ds, nm, why), n in NAME_MISS.items()
                   if why.startswith("no_spine_match"))
    say(f"    rows left unlinked with no spine candidate at all: {no_match:,} "
        f"(ordinary charities - correctly left alone)")

    if check:
        say("\n  [check] NAME-route links, most rows first (all tier B):")
        for (ds, nm, tid, canon, how), n in NAME_HITS.most_common(40):
            say(f"      {ds:36s} {nm[:42]:42s} -> {canon[:26]:26s} [{how}] x{n}")
        say("\n  --check: nothing written.")
        _flush(check=True)
        return

    wr(CLEAN / "np_ein_entity_hub.csv", sorted(hub.values(),
                                               key=lambda r: r["ein"]))
    if conflicts:
        wr(REVIEW / f"np_ein_hub_conflicts_{TODAY}.csv", conflicts)
    if excl_hits:
        wr(REVIEW / f"np_ein_hub_exclusion_hits_{TODAY}.csv", excl_hits)
    if name_cands:
        wr(REVIEW / f"np_name_candidates_{TODAY}.csv", name_cands)

    # ---------------------------------------------------- codebook -------
    # A FRAGMENT. `codebook_master.csv` is never touched here.
    frag = []
    hub_rows = list(hub.values())
    for col in (hub_rows[0].keys() if hub_rows else []):
        filled = sum(1 for r in hub_rows if str(r.get(col, "")).strip())
        frag.append({
            "dataset": "06b_np_entity_hub", "variable": col, "type": "text",
            "units": "", "pct_filled": round(100.0 * filled / max(len(hub_rows), 1), 1),
            "n_rows": len(hub_rows), "published": "0",
            "access_tier": "internal",
            "description": CODEBOOK_DESC.get(col, ""),
            "generated": TODAY,
        })
    # ...and the columns this script appended to the five existing tables.
    for ds, path, prefixes in [
            ("06_nonprofit/np_orgs", CLEAN / "np_orgs.csv", ["cedar_"]),
            ("06_nonprofit/np_financials", CLEAN / "np_financials.csv", ["cedar_"]),
            ("04e_schedule_i_filers", CLEAN / "np_schedule_i_filers.csv",
             ["cedar_filer_"]),
            ("04e_schedule_i_grants", CLEAN / "np_schedule_i_grants.csv",
             ["cedar_filer_", "cedar_recipient_"]),
            ("06c_grantmaker_funding_flows", CLEAN / "grantmaker_funding_flows.csv",
             ["cedar_funder_", "cedar_recipient_"])]:
        rr = rd(path)
        for pre in prefixes:
            for col in link_cols(pre):
                filled = sum(1 for r in rr if str(r.get(col, "")).strip())
                stem = col[len(pre):]
                frag.append({
                    "dataset": ds, "variable": col, "type": "text", "units": "",
                    "pct_filled": round(100.0 * filled / max(len(rr), 1), 1),
                    "n_rows": len(rr), "published": "0",
                    "access_tier": "internal",
                    "description": PROP_DESC.get(stem, "").replace(
                        "{side}", pre.replace("cedar_", "").strip("_") or "row"),
                    "generated": TODAY,
                })
    wr(CODEBOOK / "06b_np_entity_hub.csv", frag)
    _flush()


PROP_DESC = {
    "spine_entity_id": "Cedar spine tribe_id for the {side} side, from "
                 "np_ein_entity_hub.csv keyed on this row's EIN, or from a "
                 "deterministic resolve_entity name match where the EIN was "
                 "not in the hub. Blank means unlinked, NOT 'not Native'.",
    "spine_canonical_name": "Spine canonical name for the {side} entity.",
    "spine_entity_class": "The SPINE row's entity_class, verbatim.",
    "native_entity_class": "ANC / NHO / tribe / native org / unknown, derived "
                           "only from entity_class.",
    "link_tier": "INHERITED tier. A publishes; B never publishes alone; "
                   "X means an existing ruling forbids a link on this EIN and "
                   "the row is deliberately left unlinked.",
    "link_basis": "Why the link exists, quoting the source row's own basis.",
    "link_key": "'EIN <n>' or 'NAME <string>' - which key carried the link.",
    "link_sources": "Which Cedar tables contributed the hub entry.",
}

CODEBOOK_DESC = {
    "ein": "Employer Identification Number, digits only. The hub key.",
    "org_name": "Organisation name as it appears in np_orgs, for reading only. "
                "Never a join key.",
    "entity_id": "Cedar spine tribe_id.",
    "entity_canonical_name": "Spine canonical name for entity_id.",
    "entity_class": "The SPINE row's own entity_class, copied verbatim.",
    "native_entity_class": "Coarse class - ANC / NHO / tribe / native org / "
                           "unknown - derived only from entity_class.",
    "entity_state": "Spine state for entity_id.",
    "link_tier": "INHERITED from the source row named in link_tier_source. "
                 "A publishes; B never publishes alone; C is unattributed.",
    "link_tier_source": "Which Cedar table the tier was inherited from.",
    "link_method": "The match method recorded on that source row.",
    "n_corroborating_sources": "How many independent Cedar tables key this EIN "
                               "to this entity. Does NOT raise the tier.",
    "link_sources": "All contributing sources.",
    "link_basis": "Verbatim basis carried on the winning source row.",
    "tier_note": "Standing statement that the tier is inherited, not assigned.",
    "built_by_script": "Producer.",
    "built_date": "Build date.",
}

NAME_MISS = Counter()
NAME_HITS = Counter()
AUTO_RESOLVED = []
NAME_BY_EIN = {}
NP_BY_EIN = {}


def _flush(check=False):
    LOGS.mkdir(parents=True, exist_ok=True)
    p = LOGS / f"167_report_{TODAY}{'_check' if check else ''}.txt"
    p.write_text("\n".join(REPORT) + "\n", encoding="utf-8")
    print(f"\n  report -> {p.relative_to(CEDAR)}")


if __name__ == "__main__":
    # np_orgs is read once here so the hub, the exclusion audit and the
    # propagation all see the same rows.
    _pre = rd(CLEAN / "np_orgs.csv")
    NAME_BY_EIN = {dig(r["EIN"]): r.get("org_name", "") for r in _pre if dig(r["EIN"])}
    NP_BY_EIN = {dig(r["EIN"]): r for r in _pre if dig(r["EIN"])}
    main()
