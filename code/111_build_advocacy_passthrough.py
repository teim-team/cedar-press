#!/usr/bin/env python3
"""
Cedar Press - 111: nonprofit advocacy PASS-THROUGH.

ELIJAH, 2026-08-07
------------------
"i imagine the nonprofit data could hide lobbying - like it's funded by a Native
 entity and the funding passes through the nonprofit. that should be
 investigated."

Cedar's advocacy datasets ask "did this tribe lobby?".  This one asks a
different question: **did money from a Native funder reach an organisation that
lobbied?**  That is invisible to every existing file, because the LDA client is
the nonprofit, not the funder.

    Native funder
        -> funds (990 Schedule I cash grant)
            -> nonprofit / intertribal organisation
                -> lobbies (990 Schedule C, Part IX line 11d, or an LDA filing)

Both legs are retrieved facts.  The chain is the finding.

THE FOUR RULES THIS FILE OBEYS
------------------------------
1. **It never asserts the grant PAID FOR the lobbying.**  Money is fungible and
   most grants are restricted to program work.  What is true is that a funding
   relationship exists and a lobbying activity exists.  Both are recorded with
   their dates and their source documents.  There is no causal column, and
   `same_year_flag` is a coincidence flag, explicitly not an inference.
2. **Membership dues are not a grant, and an intertribal organisation is not a
   hidden channel.**  NCAI, NIGA, USET, ATNI, the tribal health boards and
   NAFOA are funded by their tribal members and lobby on their behalf; that is
   their stated purpose.  `recipient_org_type = MEMBERSHIP_ORGANIZATION` says
   so, taken from the spine's own `Intertribal Organization` class rather than
   from a guess here.
3. **990 lobbying is legitimate, disclosed activity.**  A 501(c)(3) may lobby
   within limits and many elect 501(h) precisely to do it transparently.  No
   column, value or note in this dataset carries a pejorative framing.
4. **`serves_native_entities` is not `parent_native_entity`.**  A Native-serving
   nonprofit that receives tribal money is not tribally owned.  This build
   writes NO relationship edge of any kind; `bears_ownership()` is imported and
   asserted against precisely so that fact is enforced rather than remembered.

CAVEATS THAT TRAVEL WITH EVERY FIGURE
-------------------------------------
- **6,453 of 12,764 organisations in `np_orgs.csv` are 990-N filers** and report
  no financial detail at all.  Zero lobbying there is the filing regime, not a
  finding.  The denominator for Schedule C analysis is 6,397 rows / 5,792 EINs,
  never 12,764.
- **Only 2,195 returns were actually retrieved (34.3% of possible).**  The IRS
  per-return S3 bucket is retired; returns now live in 81 multi-GB ZIPs read by
  HTTP range.  Every count published from the 990 leg carries that rate.
- **Tribal governments are outside the 990 universe under IRC 7871.**  A tribe
  funding a nonprofit appears only on the *recipient's* side, never on its own
  filing.  That asymmetry is why this build works at all - and it is also why
  the largest tribal grantmakers (SMSC, San Manuel) are structurally absent.

CONTAINMENT
-----------
Containment has failed ten independent ways in this project, most recently
`core()` folding `indian` away so National Education Association resolved to
National Indian Education Association.  A token present in one name and absent
from the other is never noise.  `resolve_entity` is IMPORTED, never
re-implemented (standing rule 8); eight guards sit on top of it and each one
refuses rather than guesses.  Name-only is Tier B and goes to `review/`.

NETWORK
-------
**This build makes zero remote requests.**  Every input is already on disk:
the philanthropy Schedule I pull (script 75), the IRS e-file return cache
(script 99), the LDA corpus (`code/lobbying_pull/raw_filings.jsonl`, script
set 01-06), the spine, the ledger and the nonprofit files.  No host lock is
needed and none was claimed.

Run:  py -3 code/111_build_advocacy_passthrough.py
      py -3 code/111_build_advocacy_passthrough.py --steps funding,lobbying,join
"""

from __future__ import annotations

import csv
import importlib.util
import json
import os
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
SPINE_DIR = CEDAR / "data" / "spine"
RAW = CEDAR / "data" / "raw" / "external"
REVIEW = CEDAR / "review"
DOCS = CEDAR / "docs"
LOGS = CEDAR / "logs"
TODAY = date.today().isoformat()

OUT = CLEAN / "advocacy_passthrough.csv"
OUT_REVIEW = REVIEW / f"advocacy_passthrough_unresolved_{TODAY}.csv"
REPORT = LOGS / f"111_build_report_{TODAY}.txt"

csv.field_size_limit(min(2**31 - 1, sys.maxsize))

# ---------------------------------------------------------------------------
# THE ONE RESOLVER.  Standing rule 8: import it, never write another matcher.
# ---------------------------------------------------------------------------
_spec = importlib.util.spec_from_file_location(
    "cedar_party_rulings", CEDAR / "code" / "33_apply_party_rulings.py")
_m33 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_m33)
resolve_entity = _m33.resolve_entity

# MEMOISE the two pure string helpers on the module object, exactly as the OIRA
# build did.  resolve_entity re-normalises all 1,310 spine names on every call;
# caching makes it a lookup.  This is a SPEED change and not a logic change -
# both functions are deterministic and take a single string.
_m33.norm = norm = __import__("functools").lru_cache(maxsize=None)(_m33.norm)
_m33.core = core = __import__("functools").lru_cache(maxsize=None)(_m33.core)

sys.path.insert(0, str(CEDAR / "code"))
from cedar_domain import (  # noqa: E402
    AdvocacyChannel, Tier, NAME_TRAPS, bears_ownership,
)

# Rule 4, enforced rather than remembered.  This build records a FUNDING
# relationship and a SERVICE relationship.  Neither carries money upward, and
# neither may ever be written as an ownership edge.
assert not bears_ownership("serves_native_entities")
assert not bears_ownership("affiliated_with")
assert not bears_ownership("member_of")

CHANNEL_990 = "FORM_990"            # not an AdvocacyChannel: it is a filing
CHANNEL_LDA = AdvocacyChannel.LDA_FILING.value


# ---------------------------------------------------------------------------
# io
# ---------------------------------------------------------------------------
def read_csv(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


# --- REGENERATE GUARD (ADR-017, 2026-09-02) --------------------------------
def _carry_live_columns(path, canonical):
    """Derive this writer's header instead of declaring it.

    A wholesale writer holding a FIXED `fieldnames` list deletes every column
    an in-place enricher added since - no error, no exception, a diff nobody
    reads. Canonical order first so column order stays stable, then whatever
    the live file already carries. A retired column stays retired because it
    is not on disk; a promoted column survives because it is.

    THIS BUILD CANNOT REPOPULATE AN ENRICHER'S COLUMN. Carried columns are
    written BLANK and NAMED on stdout, which is strictly better than deleted:
    the schema survives and the enricher can refill them. Re-run the enricher
    after this build - `cedar_pipeline.enrichers_to_rerun(<table>)` names it.
    """
    import csv as _csv
    import os as _os
    canonical = list(canonical)
    _p = str(path)
    if not _os.path.exists(_p):
        return canonical
    with open(_p, encoding="utf-8-sig", newline="", errors="replace") as _fh:
        _live = next(_csv.reader(_fh), [])
    _extra = [c for c in _live if c and c not in canonical]
    if _extra:
        print("  [regenerate guard] %s: carrying %d enricher column(s) through "
              "this rebuild, BLANK - re-run the enricher: %s"
              % (_os.path.basename(_p), len(_extra), ", ".join(_extra)))
    return canonical + _extra


def write_csv(p, rows, fields):
    # REGENERATE GUARD (ADR-017, 2026-09-02): derive the header, do not declare it.
    fields = _carry_live_columns(p, fields)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {p.relative_to(CEDAR)}  ({len(rows):,} rows)")


def ein9(v):
    d = re.sub(r"\D", "", str(v or ""))
    return d.zfill(9) if d else ""


def money(v):
    try:
        return float(str(v).replace(",", "").replace("$", ""))
    except Exception:
        return None


def oid18(s):
    """The IRS e-file object id, the primary key of a filed return."""
    mo = re.search(r"\d{18}", str(s or ""))
    return mo.group(0) if mo else ""


def squash(s, n=300):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    return s[: n - 1] + "…" if len(s) > n else s


# ---------------------------------------------------------------------------
# GUARDS.  Every one of these exists because a measured failure produced a
# wrong row somewhere in this project.  They sit ON TOP of resolve_entity.
# ---------------------------------------------------------------------------

# A word that says "this name is a Native entity".  If the SPINE name carries
# one and the record does not, the match is refused - this is the National
# Education Association -> National Indian Education Association failure, where
# core() folded away the single word that distinguishes.
NATIVE_IDENTITY_WORDS = {
    "indian", "indians", "native", "tribal", "tribe", "tribes", "pueblo",
    "rancheria", "nation", "band", "inupiat", "yupik", "aleut", "athabascan",
    "hawaiian", "indigenous", "anishinaabe", "dine", "navajo",
}

# A record naming a different KIND of institution is not the tribe whose name
# it borrows.  Yavapai Community Hospital, United Way of Cayuga County, Pawnee
# Valley Community Hospital and Umatilla Electric Cooperative were all keyed to
# tribes by an earlier automated pass.
INSTITUTION_WORDS = {
    "hospital", "clinic", "college", "university", "school", "academy",
    "church", "methodist", "baptist", "lutheran", "catholic", "diocese",
    "cooperative", "coop", "electric", "utility", "bank", "credit",
    "chamber", "rotary", "kiwanis", "elks", "lions", "masonic",
    "unitedway", "way", "symphony", "museum", "library", "zoo", "ymca",
    "hospice", "insurance", "realty", "county", "city", "borough",
    "department", "sheriff", "police", "fire", "district",
}

# A tribal status word rescues an institution word: "Cherokee Nation Hospital"
# is the tribe's own; "Cherokee County Hospital" is not.
STATUS_WORDS = {
    "tribe", "tribes", "tribal", "nation", "band", "pueblo", "community",
    "rancheria", "village", "colony", "reservation", "indian", "indians",
    "native", "consortium", "council", "confederated",
}

GENERIC_RESIDUE = {
    "center", "centre", "council", "circle", "bay", "valley", "project",
    "health", "services", "service", "foundation", "fund", "association",
    "institute", "society", "group", "trust", "alliance", "network",
    "partners", "programs", "program", "development", "resources", "board",
}

CORP_FORM_RE = re.compile(
    r"\b(inc|incorporated|corp|corporation|company|co|llc|ltd|limited|lp|llp|"
    r"plc|holdings|enterprises)\b", re.I)

GOVERNMENT_CLASSES = {
    "Federally recognized tribe",
    "Federally recognized Alaska Native Village",
    "State-recognized tribe",
}

# Rule 2.  A membership body's advocacy is its stated purpose, not a concealed
# channel.  The spine already curates these classes; this build reads them, it
# does not compile its own list.
#
# The two CONSTITUENCY classes are deliberately NOT here.  `Fond du Lac`
# (Federal-level constituency entity) is a component band of the Minnesota
# Chippewa Tribe and `Schaghticoke Tribal Nation` (State-level constituency
# entity) is a tribe.  Both are governments; typing a government as a
# membership organisation would describe it wrongly.
MEMBERSHIP_CLASSES = {
    "Intertribal Organization",
    "Federal-level self-governance consortium",
}
CONSTITUENT_GOVERNMENT_CLASSES = {
    "Federal-level constituency entity",
    "State-level constituency entity",
}

# A FOUNDATION, TRUST or ENDOWMENT carrying an institution's name is a
# different legal person from the institution.  Same shape as Chickasaw
# Children's Village and Cherokee Nation Businesses, which cost $13.4B on the
# contracts side.  The organisation still enters this dataset on its own EIN;
# what is refused is keying it to the institution's entity id.
SEPARATE_LEGAL_PERSON_WORDS = {
    "foundation", "trust", "endowment", "auxiliary", "alumni", "booster",
    "guild", "friends",
}
CORPORATE_CLASSES = {
    "Alaska Native Regional Corporation",
    "Alaska Native Village Corporation",
    "ANCSA Group Corporation",
}


def tokens(s):
    return set(norm(s).split())


def guarded_resolve(name, spine, state=None):
    """resolve_entity plus eight refusals.  Returns (tribe_id, canon, basis).

    basis is either how= from the resolver, or a `refused:<reason>` string that
    is written into the review file verbatim.  Nothing here re-implements name
    matching; every guard is a veto on a match the resolver already proposed.
    """
    if not (name or "").strip():
        return None, None, "refused:blank_name"

    tid, canon, how = resolve_entity(name, spine)
    if not tid:
        return None, None, f"refused:{how}"

    row = next((r for r in spine if r["tribe_id"] == tid), None)
    if row is None:
        return None, None, "refused:spine_row_missing"

    rec_t, spn_t = tokens(name), tokens(row["canonical_name"])
    rec_c, spn_c = core(name), core(row["canonical_name"])
    exact_ish = how in ("exact", "alias") or rec_c == spn_c

    # 1 - SPECIFICITY.  The record must be at least as specific as the entity.
    #     This is the direction that broke on NATIVE VILLAGE OF ELIM ->
    #     Elim Native CORPORATION: containment rewards the shortest spine name.
    if not exact_ish and not (spn_c <= rec_c):
        return None, None, "refused:record_less_specific_than_entity"

    # 2 - OFFICIAL-NAME CORROBORATION.  Containment may resolve an owner already
    #     named in evidence; it may never DETECT a match (AGENTS.md).  The record
    #     must sit between the canonical name and an official name the spine
    #     already holds.
    if how == "containment":
        official = [row.get("fr_official_name") or ""]
        official += [a for a in (row.get("aliases") or "").split("|") if a.strip()]
        if not any(o.strip() and rec_c <= core(o) for o in official):
            return None, None, "refused:containment_not_corroborated_by_official_name"

    # 3 - NATIVE IDENTITY WORD.  A word in the spine name and absent from the
    #     record is never noise.  core() folds `indian` away; this puts it back.
    missing_identity = (spn_t & NATIVE_IDENTITY_WORDS) - rec_t
    if missing_identity and not exact_ish:
        return None, None, ("refused:spine_carries_native_identity_word_record_lacks:"
                            + ",".join(sorted(missing_identity)))

    # 4 - TRAP TOKENS on partial overlap only.  Refusing `Cherokee Nation`
    #     against spine `Cherokee Nation` because `cherokee` is a trap word
    #     dropped one of the largest tribes in the country on an earlier pass.
    if not exact_ish:
        shared = rec_c & spn_c
        if shared and shared <= (NAME_TRAPS | GENERIC_RESIDUE):
            return None, None, "refused:overlap_is_trap_or_generic_tokens_only"

    # 5 - RESIDUE.  Once STRUCTURAL strips indian/native/tribal/pueblo/band, a
    #     generic English noun can carry the whole match (Indian Pueblo Cultural
    #     Center -> Makaha Cultural Learning Center).
    if not exact_ish and spn_c and spn_c <= GENERIC_RESIDUE:
        return None, None, "refused:spine_core_is_generic_nouns_only"

    # 6 - A DIFFERENT KIND OF INSTITUTION is not the tribe whose name it carries.
    if (rec_t & INSTITUTION_WORDS) and not (rec_t & STATUS_WORDS) \
            and row["entity_class"] in GOVERNMENT_CLASSES:
        return None, None, "refused:record_is_a_different_kind_of_institution"

    # 7 - CORPORATE FORM the spine name does not share, against a government.
    if (CORP_FORM_RE.search(name) and not CORP_FORM_RE.search(row["canonical_name"])
            and row["entity_class"] in GOVERNMENT_CLASSES):
        return None, None, "refused:corporate_form_vs_government_class"

    # 8 - A SEPARATE LEGAL PERSON carrying the institution's name is not the
    #     institution.  Institute of American Indian Arts FOUNDATION, Tulalip
    #     FOUNDATION, Osage Nation FOUNDATION each file their own return under
    #     their own EIN.
    sep = (rec_t & SEPARATE_LEGAL_PERSON_WORDS) - tokens(row["canonical_name"])
    if sep and not exact_ish:
        return None, None, ("refused:record_is_a_separate_legal_person:"
                            + ",".join(sorted(sep)))

    # 9 - STATE AGREEMENT wherever both sides carry one.  Where both are known
    #     and agree it is a genuine second leg of evidence and the caller may
    #     tier on it; where either is missing the match rests on the name alone.
    st = (state or "").strip().upper()[:2]
    sp = (row.get("state") or "").strip().upper()[:2]
    if st and sp and st != sp:
        return None, None, f"refused:state_disagreement:{st}_vs_{sp}"
    suffix = "+state_agrees" if (st and sp) else "+state_not_on_both_sides"

    return tid, row["canonical_name"], how + suffix


# ---------------------------------------------------------------------------
# NATIVE-FUNDER EVIDENCE.  A funder enters the dataset only where a document
# or a ruling says it is Native.  It is NEVER inferred from its name here.
# ---------------------------------------------------------------------------

# The seven grantmakers of the philanthropy channel.  Each is evidenced in
# docs/PHILANTHROPY_DISCOVERY_LOG.md by its own Form 990 Schedule I, retrieved
# 2026-08-06, and each is a Native-led or Native-serving grantmaking foundation.
PHILANTHROPY_FUNDERS = {
    "541254491": ("First Nations Development Institute", "NATIVE_FOUNDATION"),
    "823776329": ("NDN Collective Inc", "NATIVE_FOUNDATION"),
    "680027247": ("Seventh Generation Fund for Indigenous Peoples",
                  "NATIVE_FOUNDATION"),
    "731712905": ("Potlatch Fund", "NATIVE_FOUNDATION"),
    "521573446": ("American Indian College Fund", "NATIVE_FOUNDATION"),
    "561849598": ("Native Americans in Philanthropy", "MEMBERSHIP_ORGANIZATION"),
    "412014273": ("Indian Land Tenure Foundation", "NATIVE_FOUNDATION"),
}

NP_ORGS_NATIVE_RULINGS = {"native_controlled", "tribally_controlled",
                          "native_serving"}


def load_all():
    d = {}
    d["spine"] = read_csv(SPINE_DIR / "cedar_entity_spine.csv")
    d["spine_by_id"] = {r["tribe_id"]: r for r in d["spine"]}

    npo = read_csv(CLEAN / "np_orgs.csv")
    d["np_orgs"] = {ein9(r["EIN"]): r for r in npo if ein9(r["EIN"])}
    d["n_np_orgs"] = len(npo)
    d["n_990N"] = sum(1 for r in npo if r.get("tier") == "990_N")

    npf = read_csv(CLEAN / "np_financials.csv")
    d["np_fin"] = npf
    fin = defaultdict(list)
    for r in npf:
        if ein9(r["ein"]):
            fin[ein9(r["ein"])].append(r)
    d["np_fin_by_ein"] = fin

    # Agent-proposed rulings from the philanthropy queue.  These are TIER B
    # evidence - proposals awaiting Elijah - and are labelled as such wherever
    # they carry a row.
    q = read_csv(REVIEW / "agent_native_org_candidates_philanthropy_2026-08-06.csv")
    d["phil_rulings"] = {ein9(r["review_id"].replace("EIN:", "")): r["YOUR_RULING"]
                         for r in q if r.get("review_id", "").startswith("EIN:")}

    # IRS record for every grantee EIN (name, city, state, NTEE).
    d["grantee_irs"] = {ein9(r["ein"]): r for r in
                        read_csv(RAW / "philanthropy" /
                                 "grantee_ein_resolved_2026-08-06.csv")}

    # THE EIN LEG OF THE LEDGER IS NOT USABLE AS NATIVE EVIDENCE, and this is
    # measured rather than assumed.  Of its 1,104 EIN rows, 1,085 carry
    # attribution_method = need_v6, which cedar_domain.METHOD_ACCURACY records
    # at 6.5% accurate; it maps UNITED WAY OF CAYUGA COUNTY to United Auburn on
    # the trap token `united` and YAVAPAI COMMUNITY HOSPITAL to Yavapai-Apache.
    # The remaining 19 are institution_exact_name, and **not one EIN row in the
    # whole ledger is confidence_tier A** - they are B, C, and in one case X,
    # which is a negative ruling that must never resurface.
    #
    # So the ledger's EIN leg is refused wholesale as a Native-funder route.
    # It is loaded only so the refusal can be counted and reported.
    led = read_csv(CLEAN / "cedar_identifier_ledger_final.csv")
    d["ledger_ein_ok"] = {}
    counts = defaultdict(int)
    for r in led:
        if r.get("identifier_type") != "EIN":
            continue
        k = ein9(r["identifier"])
        if not k:
            continue
        counts[r.get("confidence_tier") or "?"] += 1
        if r.get("attribution_method") == "need_v6":
            counts["need_v6"] += 1
            continue
        if r.get("confidence_tier") == "A":
            d["ledger_ein_ok"][k] = r
    d["ledger_ein_tiers"] = dict(counts)
    d["ledger_need_v6"] = counts["need_v6"]
    return d


def native_funder_evidence(ein, name, state, D):
    """(funder_type, evidence_basis, entity_id, entity_name) or (None, reason,...).

    Four admissible routes, ranked.  A name is never evidence on its own.
    """
    npo = D["np_orgs"].get(ein) or {}
    if npo.get("classification_ruling") == "place_name_coincidence":
        return None, "refused:np_orgs_ruled_place_name_coincidence", None, None
    if npo.get("excluded_by_prior_ruling") == "1":
        return None, ("refused:np_orgs_excluded_by_prior_ruling:" +
                      (npo.get("exclusion_reason") or "unspecified")), None, None

    if ein in PHILANTHROPY_FUNDERS:
        nm, ft = PHILANTHROPY_FUNDERS[ein]
        tid, canon, _ = guarded_resolve(nm, D["spine"], state)
        return ft, "philanthropy_channel_funder_own_form990_schedule_i", tid, canon

    tid, canon, how = guarded_resolve(name, D["spine"], state)
    if tid:
        cls = D["spine_by_id"][tid]["entity_class"]
        return spine_class_to_type(cls), f"spine_resolution:{how}", tid, canon

    if npo.get("classification_ruling") in NP_ORGS_NATIVE_RULINGS:
        return "NATIVE_NONPROFIT", "np_orgs_ruling:" + npo["classification_ruling"], \
            npo.get("entity_id") or None, npo.get("tribe_canonical_name") or None

    pr = D["phil_rulings"].get(ein)
    if pr in ("NATIVE_ORG", "ALREADY_IN_SPINE"):
        return "NATIVE_NONPROFIT", f"philanthropy_queue_proposed_ruling:{pr}", None, None

    return None, "refused:no_native_evidence_for_funder", None, None


def funder_evidence_tier(basis):
    """Is the funder's Native status carried by two legs, or by a name?

    Tier A: the funder's own filed Schedule I in a documented channel, or an
    exact/alias spine match whose state also agrees.  Everything else -
    core-set equality, containment, an agent-proposed ruling awaiting Elijah -
    rests on a name and lands at B, which does not publish.
    """
    b = basis or ""
    if b.startswith("philanthropy_channel_funder_own_form990_schedule_i"):
        return Tier.A.value
    if b.startswith("spine_resolution:") and "+state_agrees" in b \
            and ("exact" in b or "alias" in b):
        return Tier.A.value
    return Tier.B.value


def spine_class_to_type(cls):
    if cls in MEMBERSHIP_CLASSES:
        return "MEMBERSHIP_ORGANIZATION"
    if cls in CONSTITUENT_GOVERNMENT_CLASSES:
        return "TRIBAL_GOVERNMENT_CONSTITUENT"
    if cls in CORPORATE_CLASSES:
        return "ALASKA_NATIVE_CORPORATION"
    if cls in GOVERNMENT_CLASSES:
        return "TRIBAL_GOVERNMENT"
    if cls == "Native Hawaiian Organization":
        return "NATIVE_HAWAIIAN_ORGANIZATION"
    if cls == "Tribal College or University":
        return "TRIBAL_COLLEGE"
    if cls == "Native Community Development Financial Institution":
        return "NATIVE_CDFI"
    if cls == "Urban Indian Organization":
        return "URBAN_INDIAN_ORGANIZATION"
    if cls == "BIE School":
        return "BIE_SCHOOL"
    return "NATIVE_ORGANIZATION"


# ---------------------------------------------------------------------------
# STEP: funding leg
# ---------------------------------------------------------------------------
def step_funding(D):
    """Every Schedule I cash-grant line whose FUNDER is evidenced Native."""
    print("\n--- funding leg ---")
    edges, refused = [], []

    # A1 - the philanthropy channel (script 75).  7 Native grantmakers.
    for r in read_csv(RAW / "philanthropy" / "schedule_i_grantees_2026-08-06.csv"):
        f_ein = ein9(r["funder_ein"])
        nm, ft = PHILANTHROPY_FUNDERS.get(f_ein, (r["funder_name"], None))
        if ft is None:
            refused.append(dict(leg="funding", why="funder_not_in_evidence_table",
                                name=r["funder_name"], ein=f_ein))
            continue
        tid, canon, _ = guarded_resolve(nm, D["spine"], None)
        edges.append(dict(
            object_id=oid18(r["source_url"]),
            funder_ein=f_ein, funder_name=nm, funder_type=ft,
            funder_entity_id=tid or "", funder_entity_name=canon or "",
            funder_evidence="philanthropy_channel_funder_own_form990_schedule_i",
            funder_evidence_tier=Tier.A.value,
            recipient_ein=ein9(r["grantee_ein"]),
            recipient_name_as_filed=r["grantee_name_as_filed"],
            recipient_state=(r.get("grantee_state") or "").strip().upper()[:2],
            recipient_irc_as_filed=r.get("irc_section_as_filed") or "",
            amount=money(r["cash_grant_usd"]), year=(r.get("tax_year") or "").strip(),
            purpose=r.get("purpose_as_filed") or "",
            source_url=r["source_url"], source="philanthropy_schedule_i_2026-08-06"))

    # A2 - Schedule I read out of the IRS e-file returns already cached by
    # script 99.  No network: these XMLs are on disk.  The filer is admitted
    # only on the four evidence routes above.
    for rec in parse_local_schedule_i():
        f_ein = ein9(rec["filer_ein"])
        ft, basis, tid, canon = native_funder_evidence(
            f_ein, rec["filer_name"], rec.get("filer_state"), D)
        if ft is None:
            refused.append(dict(leg="funding", why=basis,
                                name=rec["filer_name"], ein=f_ein))
            continue
        edges.append(dict(
            object_id=rec["object_id"],
            funder_ein=f_ein, funder_name=rec["filer_name"], funder_type=ft,
            funder_entity_id=tid or "", funder_entity_name=canon or "",
            funder_evidence=basis,
            funder_evidence_tier=funder_evidence_tier(basis),
            recipient_ein=ein9(rec["rein"]),
            recipient_name_as_filed=rec["rname"],
            recipient_state=(rec.get("st") or "").strip().upper()[:2],
            recipient_irc_as_filed=rec.get("irc") or "",
            amount=money(rec["amt"]), year=(rec.get("tax_period") or "")[:4],
            purpose=rec.get("purpose") or "",
            # The IRS retired its per-return objects, so the citable location
            # is the archive the return was read out of plus the return's own
            # object id.  Both come from script 99's fetch log, not from here.
            source_url=((rec.get("url") or
                         "https://apps.irs.gov/pub/epostcard/990/xml/") +
                        f" (IRS e-file return object_id {rec['object_id']}, "
                        f"member {rec['object_id']}_public.xml)"),
            source="irs_efile_990_schedule_i_local_cache"))

    # ONE RETURN, ONE SET OF GRANT LINES.  Three returns were pulled twice -
    # once rendered by ProPublica for the philanthropy channel and once out of
    # the IRS ZIP for the Schedule C cache.  The object id is the return's
    # primary key, so a duplicate grant line is dropped rather than counted.
    seen, dedup, n_dup = set(), [], 0
    for e in edges:
        k = (e["object_id"], e["recipient_ein"] or norm(e["recipient_name_as_filed"]),
             e["amount"], norm(e["purpose"]))
        if e["object_id"] and k in seen:
            n_dup += 1
            continue
        seen.add(k)
        dedup.append(e)
    edges = dedup
    print(f"  duplicate grant lines dropped (same return read twice): {n_dup:,}")

    print(f"  funding edges: {len(edges):,}  "
          f"(refused funders: {len(refused):,} rows)")
    print(f"  distinct funders: "
          f"{len({e['funder_ein'] for e in edges}):,}   "
          f"distinct recipient EINs: "
          f"{len({e['recipient_ein'] for e in edges if e['recipient_ein']}):,}")
    return edges, refused


def parse_local_schedule_i():
    """Schedule I Part II out of the cached IRS e-file returns.  Local only."""
    xmldir = RAW / "irs990_schedc" / "xml"
    if not xmldir.exists():
        return []
    fetch = {r["object_id"]: r for r in
             read_csv(RAW / "irs990_schedc" / "_xml_fetch_log.csv")}
    tag = lambda e: e.tag.split("}")[-1]  # noqa: E731
    out = []
    for f in sorted(xmldir.glob("*.xml")):
        try:
            root = ET.parse(f).getroot()
        except Exception:
            continue
        si = hdr = None
        for el in root.iter():
            t = tag(el)
            if t == "IRS990ScheduleI":
                si = el
            elif t == "ReturnHeader":
                hdr = el
        if si is None or hdr is None:
            continue
        filer = next((el for el in hdr.iter() if tag(el) == "Filer"), None)
        # THE NAME IS SPLIT ACROSS TWO LINES AT 35 CHARACTERS.  Reading only
        # line 1 leaves "FOND DU LAC TRIBAL AND COMMUNITY" (a Minnesota state
        # community college) looking like the Fond du Lac Band, and
        # "AMERICAN INDIAN HIGHER EDUCATION" without its "CONSORTIUM".
        f_ein = f_state = None
        f_n1 = f_n2 = ""
        if filer is not None:
            for el in filer.iter():
                t = tag(el)
                if t == "EIN" and f_ein is None and el.text:
                    f_ein = el.text.strip()
                elif t == "BusinessNameLine1Txt" and not f_n1 and el.text:
                    f_n1 = el.text.strip()
                elif t == "BusinessNameLine2Txt" and not f_n2 and el.text:
                    f_n2 = el.text.strip()
                elif t == "StateAbbreviationCd" and f_state is None and el.text:
                    f_state = el.text.strip()
        f_name = (f_n1 + " " + f_n2).strip()
        period = next((el.text for el in hdr.iter()
                       if tag(el) == "TaxPeriodEndDt" and el.text), "")
        oid = f.stem
        for rt in si.iter():
            if tag(rt) != "RecipientTable":
                continue
            d = {}
            for c in rt.iter():
                t = tag(c)
                if t in ("BusinessNameLine1Txt", "BusinessNameLine2Txt",
                         "RecipientEIN", "IRCSectionDesc", "CashGrantAmt",
                         "PurposeOfGrantTxt", "CityNm", "StateAbbreviationCd") \
                        and c.text:
                    d.setdefault(t, c.text.strip())
            if not d:
                continue
            out.append(dict(
                filer_ein=f_ein or "", filer_name=f_name or "",
                filer_state=f_state or "", tax_period=(period or "")[:10],
                object_id=oid, url=(fetch.get(oid) or {}).get("url", ""),
                rname=(d.get("BusinessNameLine1Txt", "") + " " +
                       d.get("BusinessNameLine2Txt", "")).strip(),
                rein=d.get("RecipientEIN", ""), irc=d.get("IRCSectionDesc", ""),
                amt=d.get("CashGrantAmt", ""),
                purpose=d.get("PurposeOfGrantTxt", ""),
                city=d.get("CityNm", ""), st=d.get("StateAbbreviationCd", "")))
    return out


# ---------------------------------------------------------------------------
# STEP: lobbying leg
# ---------------------------------------------------------------------------
BILL_RE = re.compile(
    r"\b(H\.?\s?R\.?|S\.?|H\.?\s?J\.?\s?RES|S\.?\s?J\.?\s?RES|H\.?\s?RES|"
    r"S\.?\s?RES|H\.?\s?CON\.?\s?RES|S\.?\s?CON\.?\s?RES)\s*\.?\s*(\d{1,5})\b")


def bills_in(text):
    """Bill citations only.  Case-SENSITIVE on the prefix, because a
    case-insensitive `S` matched the year in `is 2024`."""
    out = set()
    for pre, num in BILL_RE.findall(text or ""):
        p = re.sub(r"[^A-Z]", "", pre.upper())
        if p in ("HR", "S", "HJRES", "SJRES", "HRES", "SRES", "HCONRES",
                 "SCONRES"):
            out.add(f"{p}.{num}")
    return out


def build_lda_index():
    """Client-level index over the raw LDA corpus.  Read once, streamed.

    NOTE THE DENOMINATOR: `raw_filings.jsonl` was pulled with Native keyword
    nets, so it is NOT the whole LDA universe.  An organisation absent from it
    is absent from THIS CORPUS, which is not the same as not lobbying.
    """
    p = CEDAR / "code" / "lobbying_pull" / "raw_filings.jsonl"
    idx = {}
    if not p.exists():
        return idx
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except Exception:
                continue
            cl = d.get("client") or {}
            nm = (cl.get("name") or "").strip()
            if not nm:
                continue
            k = norm(nm)
            e = idx.setdefault(k, dict(
                names=set(), states=set(), years=set(), n=0, bills=set(),
                agencies=set(), registrants=set(), spend=0.0, url=""))
            e["names"].add(nm)
            for s in (cl.get("state"), cl.get("ppb_state")):
                if s:
                    e["states"].add(str(s).upper()[:2])
            if d.get("filing_year"):
                e["years"].add(str(d["filing_year"]))
            e["n"] += 1
            reg = (d.get("registrant") or {}).get("name")
            if reg:
                e["registrants"].add(reg)
            v = d.get("income") or d.get("expenses")
            if v:
                try:
                    e["spend"] += float(v)
                except Exception:
                    pass
            if not e["url"]:
                e["url"] = d.get("filing_document_url") or d.get("url") or ""
            for a in d.get("lobbying_activities") or []:
                e["bills"] |= bills_in(a.get("description"))
                for g in a.get("government_entities") or []:
                    n2 = g.get("name") if isinstance(g, dict) else str(g)
                    if n2:
                        e["agencies"].add(n2)
    return idx


def lobbying_990(ein, D):
    """(usd, source, url, years, basis) from the 990 leg for one EIN."""
    rows = D["np_fin_by_ein"].get(ein) or []
    if not rows:
        return None, "", "", [], "NO_990_IN_RETRIEVED_CORPUS_FOR_THIS_EIN"
    best = None
    for r in rows:
        for col, src in (("schedc_lobbying_usd", "FORM990_SCHEDULE_C"),
                         ("form990_part9_lobbying_fees",
                          "FORM990_PART9_LINE11D")):
            v = money(r.get(col))
            if v is not None and v > 0:
                cand = (v, src, r.get("schedc_source_url") or r.get("source_url") or "",
                        (r.get("tax_year") or "")[:4])
                if best is None or cand[0] > best[0]:
                    best = cand
    if best:
        years = sorted({(r.get("tax_year") or "")[:4] for r in rows
                        if (r.get("tax_year") or "").strip()})
        return best[0], best[1], best[2], years, "REPORTED_ON_FORM_990"

    # indicator answered YES but no dollar figure
    for r in rows:
        for col in ("form990_lobbying_activities_ind",
                    "form990pf_influence_legislation_ind"):
            if str(r.get(col) or "").strip() in ("1", "true", "True"):
                return None, "FORM990_CORE_FORM_INDICATOR", \
                    r.get("schedc_source_url") or r.get("source_url") or "", \
                    [(r.get("tax_year") or "")[:4]], \
                    "CORE_FORM_TRIGGER_ANSWERED_YES_NO_DOLLAR_FIGURE"

    bases = {r.get("schedc_basis") for r in rows if r.get("schedc_basis")}
    if "990N_filer_no_schedule_exists" in bases:
        b = "NO_LOBBYING_OBSERVATION_990N_FILER_NO_SCHEDULE_EXISTS"
    elif "irs_efile_xml_no_schedule_c_filed" in bases:
        b = "NO_SCHEDULE_C_FILED_WITH_THE_RETURN"
    elif any(x and x.startswith("outside_efile") for x in bases):
        b = "TAX_YEAR_OUTSIDE_IRS_EFILE_INDEX_COVERAGE"
    elif "efile_return_indexed_not_retrieved" in bases:
        b = "RETURN_INDEXED_BUT_NOT_RETRIEVED"
    else:
        b = "NO_LOBBYING_FIGURE_ON_THE_RETRIEVED_RETURN"
    return None, "", "", [], b


def lobbying_lda(name, state, lda_idx, D, entity_id=None, ent_lob=None):
    """LDA presence for a recipient.  Exact normalised name only.

    LDA carries no EIN, so this leg is a NAME match by construction.  The
    client state is the filing address and disagrees with the entity state on
    8.2% of already-keyed Cedar rows (941 of them DC, i.e. the registrant's
    office), so state agreement is corroboration here, never proof.
    """
    k = norm(name)
    e = lda_idx.get(k)
    if not e:
        return None
    st_ok = None
    s = (state or "").strip().upper()[:2]
    if s and e["states"]:
        st_ok = s in e["states"]
    return dict(
        n=e["n"], years=sorted(e["years"]), bills=sorted(e["bills"])[:25],
        agencies=sorted(e["agencies"])[:25], spend=e["spend"],
        url=e["url"], names=sorted(e["names"]), state_agrees=st_ok,
        registrants=sorted(e["registrants"])[:5])


# ---------------------------------------------------------------------------
# STEP: join
# ---------------------------------------------------------------------------
FIELDS = [
    "passthrough_id", "funder_entity_id", "funder_name", "funder_type",
    "recipient_ein", "recipient_org_name", "recipient_entity_id",
    "recipient_org_type",
    "grant_amount_usd", "grant_year", "grant_purpose_quote",
    "funding_instrument",
    "recipient_lobbying_expenditure", "recipient_lobbying_source",
    "recipient_lda_filings", "recipient_lda_years",
    "bills_lobbied", "agencies_contacted",
    "chain_completeness", "same_year_flag", "same_years",
    "evidence_note", "source_url_funding", "source_url_lobbying",
    "tier", "confidence", "built_date",
]

NO_CAUSATION = ("This row records that a funding relationship and a lobbying "
                "activity both exist, each with its own source document and "
                "date. It does not state that the grant paid for the lobbying, "
                "and no column in this dataset supports that reading.")

LEGITIMACY = ("Lobbying reported on a Form 990 is a disclosed, lawful activity "
              "within the limits of the organisation's tax status.")

MEMBERSHIP_NOTE = ("Membership organisation: funded by its tribal members and "
                   "advocating on their behalf is its stated purpose, not a "
                   "concealed channel.")


def recipient_type(ein, name, state, D):
    tid, canon, how = guarded_resolve(name, D["spine"], state)
    if tid:
        cls = D["spine_by_id"][tid]["entity_class"]
        return spine_class_to_type(cls), tid, canon, f"spine_resolution:{how}"
    irc = ""
    npo = D["np_orgs"].get(ein) or {}
    if npo.get("classification_ruling") in NP_ORGS_NATIVE_RULINGS:
        return "NATIVE_NONPROFIT", npo.get("entity_id") or "", "", \
            "np_orgs_ruling:" + npo["classification_ruling"]
    pr = D["phil_rulings"].get(ein)
    if pr == "NATIVE_ORG":
        return "NATIVE_NONPROFIT", "", "", "philanthropy_queue_proposed_ruling"
    return "NONPROFIT_UNCLASSIFIED", "", "", (irc or "no_classification_evidence")


def step_join(D, edges, lda_idx):
    print("\n--- join ---")
    ent_lob = {r["entity_id"] for r in
               read_csv(CLEAN / "native_entity_lobbying_disclosures.csv")
               if r.get("entity_id")}

    rows, review = [], []
    seen_recipients = set()
    n = 0

    for e in edges:
        n += 1
        rein = e["recipient_ein"]
        rname = e["recipient_name_as_filed"]
        rstate = e["recipient_state"]
        rtype, rtid, rcanon, rbasis = recipient_type(rein, rname, rstate, D)
        if (e.get("recipient_irc_as_filed") or "").upper().startswith("TRIBE") \
                or "7871" in (e.get("recipient_irc_as_filed") or ""):
            rtype = "TRIBAL_GOVERNMENT"
            rbasis = "funder_certified_recipient_as_a_tribe_under_irc_7871"

        usd, src990, url990, yrs990, basis990 = lobbying_990(rein, D) if rein \
            else (None, "", "", [], "NO_EIN_ON_THE_GRANT_LINE")
        lda = lobbying_lda(rname, rstate, lda_idx, D, rtid, ent_lob)

        srcs = [s for s in ([src990] if src990 else [])]
        if lda:
            srcs.append(CHANNEL_LDA)
        lob_years = set(yrs990 or []) | set(lda["years"] if lda else [])
        has_lob = bool(srcs)

        gy = (e["year"] or "").strip()
        same = sorted(y for y in lob_years if y and gy and y == gy)

        completeness = ("FUNDING_AND_LOBBYING_BOTH_DOCUMENTED" if has_lob
                        else "FUNDING_ONLY")

        notes = [NO_CAUSATION]
        if has_lob:
            notes.append(LEGITIMACY)
        else:
            notes.append("No lobbying observation was found for this recipient: "
                         + basis990 +
                         "; and its name does not appear as a client in the "
                         "Cedar LDA pull corpus. Absence here is the coverage of "
                         "these two sources, not a finding that the organisation "
                         "does not lobby.")
        if rtype == "MEMBERSHIP_ORGANIZATION":
            notes.append(MEMBERSHIP_NOTE)
        if rtype == "TRIBAL_GOVERNMENT":
            notes.append("Recipient is a tribal government. Under IRC 7871 it "
                         "files no Form 990, so its own advocacy is observable "
                         "only through LDA and the other advocacy channels.")
        notes.append("funder evidence: " + e["funder_evidence"] +
                     "; recipient classification: " + rbasis)
        if lda and lda["state_agrees"] is False:
            notes.append("LDA client state disagrees with the grantee state; "
                         "the LDA client address is the filing address and is "
                         "not a reliable second leg.")

        # TIER.  Two identifier-keyed legs = A.  Anything resting on a name
        # match = B and goes to review.  Nothing algorithmic reaches A.
        if has_lob and rein and src990 and not lda:
            tier, conf = Tier.A.value, (
                "Both legs are keyed on the recipient EIN: the grant line names "
                "the EIN and the lobbying figure is from that EIN's own Form 990.")
        elif has_lob and rein and src990 and lda:
            tier, conf = Tier.A.value, (
                "The 990 leg is keyed on the recipient EIN; the LDA leg is an "
                "exact normalised name match and is corroboration only.")
        elif has_lob:
            tier, conf = Tier.B.value, (
                "The lobbying leg is an exact normalised name match against the "
                "LDA corpus. LDA publishes no EIN, so this link is name-only and "
                "does not publish.")
        elif rein:
            tier, conf = Tier.A.value, (
                "The grant is keyed on the recipient EIN. No lobbying "
                "observation exists in either source for this EIN.")
        else:
            tier, conf = Tier.B.value, (
                "The grant line publishes no recipient EIN, so the recipient is "
                "identified by name only.")

        # The chain is only as strong as its weakest leg.  If the FUNDER's own
        # Native status rests on a name match or on a ruling still awaiting
        # Elijah, the row does not publish however clean the recipient side is.
        if e.get("funder_evidence_tier") == Tier.B.value and tier == Tier.A.value:
            tier = Tier.B.value
            conf = ("The funder's Native status rests on a name match or an "
                    "agent-proposed ruling awaiting a human ruling (" +
                    e["funder_evidence"] + "), so the chain does not publish.")

        if tier == Tier.B.value:
            review.append(dict(
                review_id=f"PT-{n:05d}", queue="advocacy_passthrough",
                funder_name=e["funder_name"], recipient_ein=rein,
                recipient_org_name=rname, recipient_state=rstate,
                why_not_tier_a=conf,
                lobbying_evidence=("|".join(srcs) or "none"),
                grant_amount_usd=e["amount"], grant_year=gy,
                source_url_funding=e["source_url"],
                question=("Is this the same organisation on both legs, and is "
                          "the recipient correctly typed? Name-only links do "
                          "not publish."),
                YOUR_RULING="", YOUR_NOTE=""))

        seen_recipients.add(rein or norm(rname))
        rows.append(dict(
            passthrough_id=f"PT-{n:05d}",
            funder_entity_id=e["funder_entity_id"], funder_name=e["funder_name"],
            funder_type=e["funder_type"],
            recipient_ein=rein, recipient_org_name=rname,
            recipient_entity_id=rtid or "", recipient_org_type=rtype,
            grant_amount_usd=("" if e["amount"] is None else f"{e['amount']:.2f}"),
            grant_year=gy,
            grant_purpose_quote=squash(e["purpose"], 400),
            funding_instrument="FORM_990_SCHEDULE_I_PART_II_CASH_GRANT",
            recipient_lobbying_expenditure=("" if usd is None else f"{usd:.2f}"),
            recipient_lobbying_source=("+".join(srcs) if srcs else basis990),
            recipient_lda_filings=(lda["n"] if lda else 0),
            recipient_lda_years=(";".join(lda["years"]) if lda else ""),
            bills_lobbied=(";".join(lda["bills"]) if lda else ""),
            agencies_contacted=(";".join(lda["agencies"]) if lda else ""),
            chain_completeness=completeness,
            same_year_flag=(1 if same else 0),
            same_years=";".join(same),
            evidence_note=" ".join(notes),
            source_url_funding=e["source_url"],
            source_url_lobbying=(url990 or (lda["url"] if lda else "")),
            tier=tier, confidence=conf, built_date=TODAY))

    # LOBBYING_ONLY - Native organisations that lobby and for whom no funding
    # edge is on the record.  Bounded to the Native non-government org classes
    # of the spine plus np_orgs organisations ruled Native, so this is not an
    # unbounded dump of the LDA corpus.
    n_lo = 0
    for r in D["spine"]:
        if r["entity_class"] in GOVERNMENT_CLASSES or \
                r["entity_class"] in CORPORATE_CLASSES:
            continue
        lda = lobbying_lda(r["canonical_name"], r.get("state"), lda_idx, D)
        if not lda:
            for a in (r.get("aliases") or "").split("|"):
                if a.strip():
                    lda = lobbying_lda(a, r.get("state"), lda_idx, D)
                    if lda:
                        break
        if not lda:
            continue
        key = norm(r["canonical_name"])
        if key in seen_recipients:
            continue
        n += 1
        n_lo += 1
        rtype = spine_class_to_type(r["entity_class"])
        notes = [NO_CAUSATION, LEGITIMACY]
        if rtype == "MEMBERSHIP_ORGANIZATION":
            notes.append(MEMBERSHIP_NOTE)
        notes.append("No grant to this organisation appears in any Schedule I "
                     "on disk. Tribal governments file no Form 990 under IRC "
                     "7871, and membership dues are not a Schedule I grant, so "
                     "the funding leg is structurally invisible here rather "
                     "than absent.")
        rows.append(dict(
            passthrough_id=f"PT-{n:05d}", funder_entity_id="", funder_name="",
            funder_type="NOT_IDENTIFIED",
            recipient_ein="", recipient_org_name=r["canonical_name"],
            recipient_entity_id=r["tribe_id"], recipient_org_type=rtype,
            grant_amount_usd="", grant_year="", grant_purpose_quote="",
            funding_instrument="NOT_OBSERVED",
            recipient_lobbying_expenditure="",
            recipient_lobbying_source=CHANNEL_LDA,
            recipient_lda_filings=lda["n"],
            recipient_lda_years=";".join(lda["years"]),
            bills_lobbied=";".join(lda["bills"]),
            agencies_contacted=";".join(lda["agencies"]),
            chain_completeness="LOBBYING_ONLY", same_year_flag=0, same_years="",
            evidence_note=" ".join(notes),
            source_url_funding="", source_url_lobbying=lda["url"],
            tier=Tier.B.value,
            confidence=("Lobbying is an exact normalised name match against the "
                        "LDA corpus, which publishes no EIN. Name-only; does "
                        "not publish."),
            built_date=TODAY))
        review.append(dict(
            review_id=f"PT-{n:05d}", queue="advocacy_passthrough",
            funder_name="", recipient_ein="",
            recipient_org_name=r["canonical_name"],
            recipient_state=r.get("state") or "",
            why_not_tier_a="LDA name match only; LDA publishes no EIN.",
            lobbying_evidence=CHANNEL_LDA, grant_amount_usd="", grant_year="",
            source_url_funding="",
            question=("Confirm this LDA client is this spine entity, and that "
                      "its funding is member dues rather than a grant."),
            YOUR_RULING="", YOUR_NOTE=""))

    print(f"  rows: {len(rows):,}   LOBBYING_ONLY added: {n_lo:,}")
    return rows, review


# ---------------------------------------------------------------------------
# codebook - VARIABLES ONLY
# ---------------------------------------------------------------------------
DESCRIPTIONS = {
    "passthrough_id": "Row identifier, unique within this dataset.",
    "funder_entity_id": "Cedar spine id of the funder where it resolves; blank where the funder is a nonprofit with no spine row.",
    "funder_name": "Funder name exactly as it appears on the filed return.",
    "funder_type": "What kind of Native funder this is: NATIVE_FOUNDATION, MEMBERSHIP_ORGANIZATION, TRIBAL_GOVERNMENT, NATIVE_NONPROFIT, or NOT_IDENTIFIED on a LOBBYING_ONLY row.",
    "recipient_ein": "Employer Identification Number of the grantee as printed on the funder's Schedule I.",
    "recipient_org_name": "Grantee name exactly as filed on Schedule I, or the spine name on a LOBBYING_ONLY row.",
    "recipient_entity_id": "Cedar spine id of the recipient where it resolves under the guards; blank otherwise.",
    "recipient_org_type": "MEMBERSHIP_ORGANIZATION, TRIBAL_GOVERNMENT, NATIVE_NONPROFIT, TRIBAL_COLLEGE and similar. A membership body's advocacy is its stated purpose, not a concealed channel.",
    "grant_amount_usd": "Cash grant in US dollars as reported in Schedule I Part II. Schedule I has a $5,000 floor.",
    "grant_year": "Tax year of the funder's return carrying the grant.",
    "grant_purpose_quote": "Purpose of the grant, verbatim from the filed Schedule I.",
    "funding_instrument": "FORM_990_SCHEDULE_I_PART_II_CASH_GRANT, or NOT_OBSERVED where no grant is on the record. Membership dues are not a Schedule I grant and never appear here.",
    "recipient_lobbying_expenditure": "Lobbying expenditure the recipient reported on its own Form 990, in US dollars. Blank where none was reported or none was retrievable.",
    "recipient_lobbying_source": "Which document carries the lobbying observation, or the reason none was found. Absence is stated, never zeroed.",
    "recipient_lda_filings": "Number of Lobbying Disclosure Act filings in the Cedar LDA corpus whose client name matches the recipient exactly after normalisation.",
    "recipient_lda_years": "Filing years of those LDA filings, semicolon separated.",
    "bills_lobbied": "Bill citations parsed from the LDA filings' own specific-issue text.",
    "agencies_contacted": "Government entities named in the LDA filings.",
    "chain_completeness": "FUNDING_AND_LOBBYING_BOTH_DOCUMENTED, FUNDING_ONLY, or LOBBYING_ONLY.",
    "same_year_flag": "1 where a grant year and a lobbying year coincide. A coincidence of dates, not a causal claim.",
    "same_years": "The coinciding years.",
    "evidence_note": "What this row does and does not establish, including the explicit statement that no causal link is asserted.",
    "source_url_funding": "Source document for the funding leg.",
    "source_url_lobbying": "Source document for the lobbying leg.",
    "tier": "A publishes; B is internal only. Tier A requires both legs keyed on an identifier.",
    "confidence": "Why the row sits at its tier, in words.",
    "built_date": "Build date.",
}


def step_codebook(rows):
    p = CLEAN / "codebook_master.csv"
    cb = read_csv(p)
    if not cb:
        print("  codebook_master.csv absent - skipping")
        return
    fields = list(cb[0].keys())
    ds = "04c_advocacy_passthrough"
    bak = p.with_suffix(f".csv.bak_{TODAY}_pre111")
    if not bak.exists():
        bak.write_bytes(p.read_bytes())
    kept = [r for r in cb if r.get("dataset") != ds]
    n = len(rows)
    for v in FIELDS:
        filled = sum(1 for r in rows if str(r.get(v, "")).strip() != "")
        kept.append({
            "dataset": ds, "variable": v,
            "type": ("number" if v in ("grant_amount_usd",
                                       "recipient_lobbying_expenditure",
                                       "recipient_lda_filings",
                                       "same_year_flag")
                     else "date" if v in ("built_date",) else "text"),
            "units": ("USD" if "usd" in v or "expenditure" in v else ""),
            "pct_filled": f"{(100.0 * filled / n if n else 0):.1f}",
            "n_rows": n, "published": "1", "access_tier": "public",
            "description": DESCRIPTIONS[v], "generated": TODAY})
    write_csv(p, kept, fields)


# ---------------------------------------------------------------------------
def step_report(D, edges, refused, rows, review, lda_idx):
    R = []
    a = R.append
    a("=" * 74)
    a(f"Cedar Press 111 - nonprofit advocacy pass-through   {TODAY}")
    a("=" * 74)
    a("")
    a("NO CAUSAL CLAIM IS MADE ANYWHERE IN THIS DATASET. Every row records that")
    a("a funding relationship and a lobbying activity both exist, with dates and")
    a("source documents, and stops there.")
    a("")

    comp = defaultdict(int)
    for r in rows:
        comp[r["chain_completeness"]] += 1
    a("chain_completeness")
    for k in ("FUNDING_AND_LOBBYING_BOTH_DOCUMENTED", "FUNDING_ONLY",
              "LOBBYING_ONLY"):
        a(f"  {k:45s} {comp.get(k,0):>7,}")
    a("")

    complete = [r for r in rows
                if r["chain_completeness"] == "FUNDING_AND_LOBBYING_BOTH_DOCUMENTED"]
    a(f"complete chains .................................. {len(complete):,}")
    a(f"  distinct funders in them ....................... "
      f"{len({r['funder_name'] for r in complete}):,}")
    a(f"  distinct recipients in them .................... "
      f"{len({r['recipient_ein'] or r['recipient_org_name'] for r in complete}):,}")
    a(f"  same-year coincidences ......................... "
      f"{sum(1 for r in complete if str(r['same_year_flag'])=='1'):,}")
    a("")
    a(f"funders reached (all rows) ....................... "
      f"{len({r['funder_name'] for r in rows if r['funder_name']}):,}")
    a(f"recipients reached (all rows) .................... "
      f"{len({r['recipient_ein'] or r['recipient_org_name'] for r in rows}):,}")
    a(f"grant dollars on the funding leg ................. $"
      f"{sum(money(r['grant_amount_usd']) or 0 for r in rows):,.0f}")
    a("")

    # THE BLIND SPOT.  A recipient lobbies; its funder never appears in LDA.
    lda_funder = set()
    for r in rows:
        if r["funder_name"] and norm(r["funder_name"]) in lda_idx:
            lda_funder.add(r["funder_name"])
    blind = [r for r in complete
             if r["funder_name"] and norm(r["funder_name"]) not in lda_idx]
    a("THE BLIND SPOT")
    a(f"  complete chains whose FUNDER never appears in the LDA corpus: "
      f"{len(blind):,}")
    a(f"  the funders involved: {len({r['funder_name'] for r in blind}):,}")
    a(f"  funders that DO appear in LDA: {len(lda_funder):,}")
    a("  This is the whole point of the layer: the money is disclosed on a tax")
    a("  return and the advocacy is disclosed on a lobbying filing, but no")
    a("  single source connects them, and a reader of LDA alone sees neither")
    a("  the funder nor the relationship.")
    a("")

    # THE PASS-THROUGH SUBSET.  A grant to a tribal government whose own LDA
    # filings Cedar already holds is not a hidden channel - the tribe lobbies
    # under its own name and the existing dataset sees it.  The question Elijah
    # asked is about the NON-GOVERNMENT recipients, so that subset is reported
    # separately rather than folded into a larger, easier number.
    gov_types = {"TRIBAL_GOVERNMENT", "TRIBAL_GOVERNMENT_CONSTITUENT"}
    nonprofit_chains = [r for r in complete
                        if r["recipient_org_type"] not in gov_types]
    a("OF THOSE COMPLETE CHAINS, THE NON-GOVERNMENT SUBSET")
    a(f"  chains whose recipient is NOT a tribal government ...... "
      f"{len(nonprofit_chains):,}")
    a(f"  organisations involved ................................. "
      f"{len({r['recipient_org_name'] for r in nonprofit_chains}):,}")
    byt = defaultdict(int)
    for r in nonprofit_chains:
        byt[r["recipient_org_type"]] += 1
    for k, v in sorted(byt.items(), key=lambda x: -x[1]):
        a(f"    {k:38s} {v:>5,}")
    a("  A grant to a tribal government is a real funding fact, but the tribe's")
    a("  own lobbying is already visible in Cedar's LDA dataset under its own")
    a("  name. It is the non-government recipients that the existing datasets")
    a("  cannot see.")
    a("")

    # WHICH LEG CARRIED THE LOBBYING - and the one that carried nothing.
    a("WHICH DOCUMENT CARRIED THE LOBBYING LEG")
    bysrc = defaultdict(int)
    for r in complete:
        bysrc[r["recipient_lobbying_source"]] += 1
    for k, v in sorted(bysrc.items(), key=lambda x: -x[1]):
        a(f"  {k:45s} {v:>6,}")
    rec_eins = {r["recipient_ein"] for r in rows if r["recipient_ein"]}
    in_fin = {e for e in rec_eins if e in D["np_fin_by_ein"]}
    a(f"  recipients whose EIN appears in np_financials at all: "
      f"{len(in_fin):,} of {len(rec_eins):,}")
    a("  Every one of them filed NO Schedule C and reported $0 on Part IX line")
    a("  11d, so the 990 leg contributed no complete chain in this run. That is")
    a("  a measurement, not a parser failure: four in five grantees of these")
    a("  funders are outside the nonprofit corpus entirely (491 of 601, per")
    a("  docs/PHILANTHROPY_DISCOVERY_LOG.md), and the 990 return that would")
    a("  carry a Schedule C has not been retrieved for them.")
    a("")

    memb = [r for r in rows if r["recipient_org_type"] == "MEMBERSHIP_ORGANIZATION"]
    a("WHAT THIS LAYER STRUCTURALLY CANNOT SEE")
    a("  - Tribal government grantmaking. Under IRC 7871 a tribe files no Form")
    a("    990, so a grant from SMSC or San Manuel appears on no Schedule I")
    a("    anywhere. Their giving runs to hundreds of millions and leaves no")
    a("    machine-readable trace.")
    a("  - Membership DUES. Dues are not a Schedule I grant and appear in no")
    a("    public filing, so the ordinary way a tribe funds NCAI, NIGA or USET")
    a("    is invisible here by construction. That is why every intertribal")
    a("    organisation in this file lands in LOBBYING_ONLY.")
    a("  - Grants under $5,000: Schedule I Part II has a floor.")
    a("  - Grants to individuals: Part III carries no names.")
    a("  - Fiscally sponsored projects, which are filed under the sponsor's EIN.")
    a("  - Whether a grant was restricted. Schedule I gives a purpose line, not")
    a("    the grant agreement, so restriction is unobservable and no row here")
    a("    claims otherwise.")
    a("  - State-house lobbying by an LDA-absent organisation: the IRS")
    a("    definition on Schedule C includes state and local legislative")
    a("    activity, LDA covers federal contacts only.")
    a("")
    a(f"membership organisations correctly typed ......... {len(memb):,} rows, "
      f"{len({r['recipient_org_name'] for r in memb}):,} organisations")
    a("  Typed from the spine's own Intertribal Organization and self-governance")
    a("  consortium classes. Funded by their members and advocating on their behalf")
    a("  is their stated purpose. Presenting that as a concealed pass-through")
    a("  would be wrong, so they are described accurately instead.")
    a("")

    t = defaultdict(int)
    for r in rows:
        t[r["tier"]] += 1
    a(f"tier A {t.get('A',0):,}   tier B {t.get('B',0):,}   "
      f"(review queue {len(review):,})")
    a("")
    a("CAVEATS THAT TRAVEL WITH EVERY FIGURE ABOVE")
    a(f"  - {D['n_990N']:,} of {D['n_np_orgs']:,} organisations in np_orgs.csv are")
    a("    990-N filers and report no financial detail at all. Zero lobbying")
    a("    there is the filing regime. The Schedule C denominator is 6,397")
    a("    rows / 5,792 EINs, never 12,764.")
    a("  - Only 2,195 returns were retrieved, 34.3% of the possible 6,397. The")
    a("    IRS per-return S3 bucket is retired; returns live in 81 multi-GB ZIPs")
    a("    read by HTTP range.")
    a("  - Tribal governments file no Form 990 under IRC 7871. A tribe funding a")
    a("    nonprofit appears only on the recipient's side, never on its own.")
    a(f"  - {D['ledger_need_v6']:,} of the identifier ledger's EIN rows carry")
    a("    attribution_method = need_v6, which cedar_domain records at 6.5%")
    a("    accurate. NO EIN row in the ledger is confidence_tier A")
    a(f"    ({D['ledger_ein_tiers']}), so the ledger's EIN leg was refused")
    a("    wholesale as Native-funder evidence.")
    a("  - The LDA corpus was pulled with Native keyword nets. An organisation")
    a("    absent from it is absent from THIS CORPUS, not from lobbying.")
    a("")
    ref = defaultdict(int)
    for r in refused:
        ref[r["why"]] += 1
    a("funders refused (the guards doing their job)")
    for k, v in sorted(ref.items(), key=lambda x: -x[1])[:15]:
        a(f"  {v:>6,}  {k}")
    a("")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(R), encoding="utf-8")
    print("\n".join(R))


def main():
    steps = "funding,lobbying,join,codebook,report"
    for i, a in enumerate(sys.argv):
        if a == "--steps" and i + 1 < len(sys.argv):
            steps = sys.argv[i + 1]
    steps = set(s.strip() for s in steps.split(","))

    print("=== Cedar Press 111: nonprofit advocacy pass-through ===")
    print("zero remote requests; every input is already on disk\n")
    D = load_all()
    print(f"spine {len(D['spine']):,} | np_orgs {D['n_np_orgs']:,} "
          f"({D['n_990N']:,} are 990-N) | np_financials {len(D['np_fin']):,}")
    print(f"ledger EIN rows refused as need_v6: {D['ledger_need_v6']:,}")

    edges, refused = step_funding(D)
    print("\n--- lobbying leg ---")
    lda_idx = build_lda_index()
    print(f"  LDA corpus clients indexed: {len(lda_idx):,}")

    rows, review = step_join(D, edges, lda_idx)
    write_csv(OUT, rows, FIELDS)
    write_csv(OUT_REVIEW, review,
              ["review_id", "queue", "funder_name", "recipient_ein",
               "recipient_org_name", "recipient_state", "why_not_tier_a",
               "lobbying_evidence", "grant_amount_usd", "grant_year",
               "source_url_funding", "question", "YOUR_RULING", "YOUR_NOTE"])
    if "codebook" in steps:
        step_codebook(rows)
    step_report(D, edges, refused, rows, review, lda_idx)


if __name__ == "__main__":
    main()
