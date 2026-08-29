"""316 - build the 30-entity roster for the TRIBAL VENDOR LIST feasibility study.

WHAT THIS IS
------------
A tribal government certifying a business is a THIRD PARTY with authority over
the ownership question.  That is a tier-A evidence leg, and Cedar Press has
almost none: measured 2026-08-26, a SAM socio-economic flag is
self-certification (Goldbelt Raven, an ANC subsidiary, certifies
`alaskanNativeCorporationOwnedFirm = NO`), and typing the SAM mirrors
correctly moved tier A from 39 to 18 on the reconciliation queue.

This script produces the deliberately stratified 30-entity roster the
feasibility study is run over, keyed to real `data/spine/cedar_entity_spine.csv`
ids, and seeds / refreshes the re-runnable tracking file

    review/tribal_vendor_list_registry_2026-08-26.csv

RE-RUNNABLE, NOT REBUILT
------------------------
Defect class 6.  This script is an ENRICHER over the registry, never a full
rebuild: it reads any existing registry, PRESERVES every verdict and every
field a later pass wrote, and only fills in the spine-derived columns.  A
verdict already recorded is never reverted to NOT_CHECKED.  Re-running changes
nothing but the spine-derived facts and `roster_built_date`, so a later sweep
RESUMES rather than restarts.

Defect class 2b: every spine / ranking column this script reads is asserted
present before use.  A coverage computation must RAISE on a missing column,
never print a zero.

Defect class 2c: entities named in ROSTER that are absent from the spine are
printed BY NAME, never counted.

NO NETWORK CALLS.  This script reads local files only.
"""

from __future__ import annotations

import csv
import datetime as _dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPINE = ROOT / "data" / "spine" / "cedar_entity_spine.csv"
RANKING = ROOT / "data" / "clean" / "contractor_ranking.csv"
REGISTRY = ROOT / "review" / "tribal_vendor_list_registry_2026-08-26.csv"

SCRIPT = "316_build_tribal_vendor_list_roster.py"
STUDY_DATE = "2026-08-26"

# --------------------------------------------------------------------------
# THE 30.  Every row states WHY it is in the sample.  The strata are:
#   scale      - federal prime contracting dollars (the ranking, ASRC $25.17B
#                down to entities with none)
#   gaming     - whether the entity's revenue base is gaming rather than
#                contracting, which predicts a DIFFERENT publication habit
#   geography  - Southwest / Plains / Great Lakes / Southeast / Northwest /
#                California / Northeast / Oklahoma / Alaska
#   coverage   - what Cedar Press already holds.  A list that only works for
#                entities we already cover is worth much less, so entities we
#                hold NOTHING for are deliberately included.
# Order is the study's PRIORITY ORDER: lower 48 first, then ANC regional
# corporations, then Alaska Native villages.  Alaska is never the start.
# --------------------------------------------------------------------------
ROSTER = [
    # ---- LOWER 48 (20) ----------------------------------------------------
    ("TRBF-NAVAJO-00", "lower48", "Southwest", "large",
     "Largest land base and enrolled population in the lower 48. The Navajo "
     "Business Opportunity Act runs a CERTIFIED NAVAJO-OWNED / priority "
     "business list - a statutory ownership certification, the single "
     "highest-value target in the study."),
    ("TRBF-GILARV-00", "lower48", "Southwest", "gaming_not_contracting",
     "Large Phoenix-corridor gaming revenue against rank 168 in federal "
     "contracting. Tests whether a tribe whose money is NOT federal still "
     "publishes an ownership certification."),
    ("TRBF-CHKNAT-00", "lower48", "Oklahoma", "very_large",
     "Rank 6, $9.92B - the largest lower-48 federal contractor. If the "
     "best-resourced tribal government does not publish, few will."),
    ("TRBF-CTWNAT-00", "lower48", "Oklahoma", "large_but_evidence_poor",
     "Rank 65 on $239.9M yet ZERO tier-A UEI links and 28 tier-B. Big "
     "dollars, weak evidence - exactly the shape a certification leg fixes."),
    ("TRBF-CSKTFR-00", "lower48", "Northwest", "large_but_evidence_poor",
     "Rank 22, $1.82B, and ZERO tier-A UEI links (13 tier-B). One of the "
     "oldest TERO ordinances in Indian country."),
    ("TRBF-COLVLL-00", "lower48", "Northwest", "mid",
     "Rank 87. Long-standing TERO office; large reservation workforce."),
    ("TRBF-YAKAMA-00", "lower48", "Northwest", "mid",
     "Rank 93. TERO office; heavy construction and agriculture contracting "
     "on-reservation, which is what a TERO list is FOR."),
    ("TRBF-UMATLL-00", "lower48", "Northwest", "large",
     "Rank 42, $542M. A contracting tribe with an active employment rights "
     "programme - both legs present."),
    ("TRBF-MHATAT-00", "lower48", "Plains", "large",
     "Rank 31, $889M. Bakken-era TERO with the largest oilfield vendor "
     "certification volume of any tribe; if a certified list exists anywhere "
     "in machine-readable form it is likely here."),
    ("TRBF-STNDRK-00", "lower48", "Plains", "mid",
     "Rank 119. TERO office, pipeline-era contractor scrutiny, large land "
     "base, modest contracting dollars."),
    ("TRBF-OGLALA-00", "lower48", "Plains", "population_not_dollars",
     "Rank 117. One of the largest enrolled populations in the lower 48 "
     "against small contracting dollars - tests the population stratum."),
    ("TRBF-ONDAWI-00", "lower48", "Great Lakes", "large",
     "Rank 49, $422M. Gaming AND contracting, with a formal purchasing "
     "function."),
    ("TRBF-LCORLS-00", "lower48", "Great Lakes", "HOLD_NOTHING",
     "WE HOLD NOTHING: no contracting rank, no tier-A UEI. Included "
     "deliberately - a source that only works where we are already covered "
     "is worth much less."),
    ("TRBF-MSBCTW-00", "lower48", "Southeast", "large",
     "Rank 69, $208M. The Southeast's largest tribal industrial employer; "
     "Choctaw manufacturing enterprises are exactly the firms a list would "
     "name."),
    ("TRBF-POARCH-00", "lower48", "Southeast", "large",
     "Rank 34, $812M. Only federally recognised tribe in Alabama; heavy "
     "8(a) presence, which is where the ownership question actually bites."),
    ("TRBF-ESTCHK-00", "lower48", "Southeast", "mid",
     "Rank 95. EBCI runs a well-established TERO; separate legal and "
     "geographic setting from the Oklahoma Cherokee, which also tests the "
     "NAME_TRAPS problem ('cherokee' is a trap token)."),
    ("TRBF-SNCNAT-00", "lower48", "Northeast", "large",
     "Rank 21, $1.84B. Large Northeast contractor with a TERO."),
    ("TRBF-SRMHWK-00", "lower48", "Northeast", "small_dollars",
     "Rank 270 - $3,500 lifetime. A TERO office on a border reservation with "
     "essentially no federal contracting. Tests whether TERO publication "
     "tracks contracting at all."),
    ("TRBF-PCHNGA-00", "lower48", "California", "HOLD_NOTHING",
     "WE HOLD NOTHING: no contracting rank, no tier-A UEI, one tier-B. "
     "Among the largest gaming revenues in the country. California is the "
     "densest tribal jurisdiction in the study and is represented by an "
     "entity we cannot see at all."),
    ("TRBF-ELYTNV-00", "lower48", "Great Basin", "HOLD_ABSOLUTELY_NOTHING",
     "WE HOLD ABSOLUTELY NOTHING: n_uei_tierA=0, n_uei_tierB=0, n_cage=0, "
     "n_ein=0, no contracting rank. A very small Great Basin tribe. This is "
     "the floor case and a NO_LIST_FOUND here is a real finding."),

    # ---- TRANCHE 2, added 2026-08-26 -------------------------------------
    # The owner's instruction was to scale from the 30 toward the central
    # estimate of ~120-150 lists. This tranche is deliberately weighted to the
    # MIDDLE AND TAIL of federal contracting, because tranche 1 over-sampled
    # the top and the honest question is whether publication holds up further
    # down. It also fills the two strata tranche 1 was thin on: Rio Grande
    # Pueblos and California.
    ("TRBF-CHKSWN-00", "lower48", "Oklahoma", "very_large",
     "Rank 14, $3.18B. Tranche-1 dropped it for geographic balance; at this "
     "size its publication behaviour is load-bearing."),
    ("TRBF-WNNBGO-00", "lower48", "Plains", "very_large",
     "Rank 15, $3.13B. Ho-Chunk Inc. is one of the largest tribal holding "
     "companies outside Alaska - tests whether a corporate arm publishes."),
    ("TRBF-HLTNML-00", "lower48", "Northeast", "very_large",
     "Rank 17, $2.48B on a very small tribe. The sharpest "
     "dollars-without-visible-apparatus case in the data."),
    ("TRBF-PSKNML-00", "lower48", "California", "very_large",
     "Rank 18, $2.45B. Second California entity, and a large contractor - "
     "tranche 1 had California represented only by a zero-coverage tribe."),
    ("TRBF-MSENAT-00", "lower48", "Oklahoma", "large",
     "Rank 48. Large Oklahoma nation with a distinct contracting office."),
    ("TRBF-FSTCTY-00", "lower48", "Great Lakes", "large",
     "Rank 32, $864M. Gaming and contracting with a corporate arm."),
    ("TRBF-OKYOWG-00", "lower48", "Southwest", "large",
     "Rank 37, $748M. RIO GRANDE PUEBLO - a stratum tranche 1 could not "
     "cover, and the brief named the Southwest explicitly."),
    ("TRBF-LAGUNA-00", "lower48", "Southwest", "mid",
     "Rank 81. Second Rio Grande Pueblo, so one Pueblo's behaviour is not "
     "generalised into a rule about Pueblos."),
    ("TRBF-PNBSCT-00", "lower48", "Northeast", "large",
     "Rank 52. Maine tribe under a distinct settlement-act jurisdiction."),
    ("TRBF-ONDANY-00", "lower48", "Northeast", "large",
     "Rank 73. DIFFERENT NATION from Oneida Nation of Wisconsin - included "
     "deliberately as a live test of the conflation risk."),
    ("TRBF-JMSTSK-00", "lower48", "Northwest", "large",
     "Rank 68, $218M. Small tribe, large contracting."),
    ("TRBF-COQLLE-00", "lower48", "Northwest", "large",
     "Rank 70, $207M. Oregon coastal restored tribe."),
    ("TRBF-OSAGEN-00", "lower48", "Oklahoma", "mid",
     "Rank 88. Mineral estate and a separate business-licence regime."),
    ("TRBF-SRPMCP-00", "lower48", "Southwest", "mid",
     "Rank 91. Large Phoenix-corridor community with heavy licensing "
     "infrastructure."),
    ("TRBF-SMNLFL-00", "lower48", "Southeast", "mid",
     "Rank 100. Largest tribal gaming operator in the country against "
     "modest federal contracting."),
    ("TRBF-ABSXFP-00", "lower48", "Plains", "mid",
     "Rank 92. Fort Peck runs one of the oldest and best-regarded TEROs in "
     "Indian country - a strong prior that publication should exist."),
    ("TRBF-THNODM-00", "lower48", "Southwest", "large_but_evidence_poor",
     "Rank 110 and ZERO tier-A UEI links. Large land base, weak evidence."),
    ("TRBF-UTEMTN-00", "lower48", "Southwest", "large_but_evidence_poor",
     "Rank 114 and ZERO tier-A UEI links."),
    ("TRBF-WRMSPR-00", "lower48", "Northwest", "mid",
     "Rank 115. Confederated Oregon tribe with a standing TERO."),
    ("TRBF-REDLKE-00", "lower48", "Great Lakes", "mid",
     "Rank 111. A CLOSED reservation - tests whether a closed-land-tenure "
     "tribe publishes differently."),
    ("TRBF-CHYNRV-00", "lower48", "Plains", "mid",
     "Rank 116. Large Great Plains land base."),
    ("TRBF-TURTLM-00", "lower48", "Plains", "small",
     "Rank 164. Large enrolled population, small contracting."),
    ("TRBF-BLCKFT-00", "lower48", "Plains", "mid",
     "Rank 129. Rocky Mountain front, energy-adjacent contracting."),
    ("TRBF-HOPIAZ-00", "lower48", "Southwest", "mid",
     "Rank 130. Distinct land tenure inside the Navajo Nation's boundary."),
    ("TRBF-SNCRLS-00", "lower48", "Southwest", "small",
     "Rank 195. Large land base, small contracting."),
    ("TRBF-WMTNAZ-00", "lower48", "Southwest", "small",
     "Rank 180. Timber and forestry contracting."),
    ("TRBF-LUMMIT-00", "lower48", "Northwest", "mid",
     "Rank 128. Coast Salish tribe with an economic policy office."),
    ("TRBF-TULALP-00", "lower48", "Northwest", "small",
     "Rank 172. Well-resourced TERO relative to contracting scale."),
    ("TRBF-QUINLT-00", "lower48", "Northwest", "small",
     "Rank 165. TERO established 1987 under its own code title."),
    ("TRBF-MNMNEE-00", "lower48", "Great Lakes", "small",
     "Rank 198. Forest-products economy, small contracting."),
    ("TRBF-SMARIE-00", "lower48", "Great Lakes", "mid",
     "Rank 135. Largest tribe east of the Mississippi by enrolment."),
    ("TRBF-STHUTE-00", "lower48", "Southwest", "mid",
     "Rank 154. Energy arm (Growth Fund) alongside the tribal government - "
     "tests whether an energy subsidiary appears in a TERO list."),

    # ---- ANC REGIONAL CORPORATIONS (5) ------------------------------------
    ("ANRC-ARCSLO-00", "anc_regional", "Alaska", "very_large",
     "Rank 1, $25.17B - the largest Native federal contractor there is, 57 "
     "operating companies. A published SUBSIDIARY DIRECTORY from the parent "
     "is a third-party ownership assertion of exactly the kind we lack."),
    ("ANRC-NANARC-00", "anc_regional", "Alaska", "very_large",
     "Rank 2, $19.89B. Same test as ASRC on a second large corporation, so "
     "one corporation's habit is not generalised into a rule."),
    ("ANRC-CALSTA-00", "anc_regional", "Alaska", "large",
     "Rank 7, $8.83B. Largest shareholder base of any ANCSA regional; the "
     "village-corporation relationships under it are the hardest hierarchy "
     "in the spine."),
    ("ANRC-DOYONL-00", "anc_regional", "Alaska", "mid",
     "Rank 24, $1.61B. Mid-scale regional with a distinct government-"
     "services grouping."),
    ("ANRC-SEALSK-00", "anc_regional", "Alaska", "low_contracting",
     "Rank 174, $0.70M - a very large shareholder base with almost no "
     "federal contracting. Tests whether publication tracks contracting "
     "dollars or shareholder obligation."),

    # ---- ALASKA NATIVE VILLAGES (5) ---------------------------------------
    ("AKNF-CHNEGA-00-CHGCCO-CHGCMT", "ak_village", "Alaska", "large",
     "Rank 41, $549M at the village-government level, sitting beside "
     "Chenega Corporation at rank 4 ($10.64B). The clearest village/"
     "corporation split in the data."),
    ("AKNF-INPTBW-00-ARCSLO", "ak_village", "Alaska", "mid",
     "Rank 216. Utqiagvik - the village government beside Ukpeagvik Inupiat "
     "Corporation at rank 8 ($5.76B). Same split, opposite proportions."),
    ("AKNF-WAINWT-00-ARCSLO", "ak_village", "Alaska", "small",
     "Rank 122 with 35 tier-A UEI links - an unusually well-identified "
     "small village. Beside Olgoonik Corporation, rank 25."),
    ("AKNF-KTZBUE-00-NANARC-MANLLQ", "ak_village", "Alaska", "HOLD_NOTHING",
     "WE HOLD NOTHING: no contracting rank, no tier-A UEI. A NANA-region "
     "hub village."),
    ("AKNF-EKLTNA-00-CKINLT", "ak_village", "Alaska", "HOLD_NOTHING",
     "WE HOLD NOTHING: no contracting rank, no tier-A UEI. Anchorage-"
     "adjacent, so it is the village most likely to have a real web "
     "presence - which makes a NO_LIST_FOUND here informative rather than "
     "an artefact of connectivity."),
]

# --------------------------------------------------------------------------
# Registry schema.  Spine-derived columns are (re)computed every run; every
# other column is PRESERVED from any existing registry.
# --------------------------------------------------------------------------
SPINE_DERIVED = [
    "tribe_id", "canonical_name", "entity_class", "state", "bia_region",
    "priority_group", "geography", "scale_stratum", "why_chosen",
    "contracting_rank", "contracting_obligations_usd",
    "n_uei_tierA", "n_uei_tierB", "n_cage", "n_ein",
    "cedar_holds_nothing", "roster_built_date", "roster_built_by",
]

FIELD_COLUMNS = [
    # ---- THREE PRODUCTS, TYPED SEPARATELY AND NEVER CONFLATED -------------
    # 1 CERTIFICATION      an assertion about OWNERSHIP        (TERO etc.)
    # 2 VENDOR_RELATIONSHIP an assertion that a firm DOES BUSINESS WITH the
    #                       tribe. A bad ownership claim and a GOOD
    #                       procurement/leakage claim.
    # 3 BUSINESS_LICENCE    an assertion that a firm OPERATES ON tribal land.
    # Each carries its own typed verdict because a tribe can publish one, two,
    # all three, or none, and a tribe with a licence registry but no TERO list
    # is still a useful source. Conflating them is the single failure mode
    # that would discredit all three.
    "verdict_certification",
    "verdict_vendor_relationship",
    "verdict_business_licence",
    "vendor_relationship_url",
    "vendor_relationship_note",
    "business_licence_url",
    "business_licence_note",
    "types_published",          # semicolon list of the products this tribe serves
    # ---- the CERTIFICATION product's detail (the study's priority) --------
    # `verdict` is the CERTIFICATION verdict and is kept under its original
    # name because 317/318/319 and the deliverable all key on it.
    "verdict",               # LIST_FOUND_MACHINE_READABLE | LIST_FOUND_PDF |
                               # LIST_FOUND_HTML | LIST_BEHIND_LOGIN |
                               # LIST_REFERENCED_NOT_PUBLISHED | NO_LIST_FOUND |
                               # NOT_CHECKED | SITE_UNREACHABLE
    "official_site",
    "hosts",                   # semicolon-joined, for the CDX sweep
    "list_url",
    "list_type",               # TERO | VENDOR | LICENSE | TERO_EMPLOYER |
                               # SUBSIDIARY_DIRECTORY | SHAREHOLDER_VENDOR | NONE
    "assertion_class",         # OWNERSHIP | RELATIONSHIP | OPERATING_ON_LAND |
                               # NONE  - derived from list_type, never guessed
    "list_format",             # MACHINE_READABLE | PDF | HTML |
                               # PORTAL_SEARCH_ONLY | NONE
    "entry_count_approx",
    "identifiers_present",
    "update_frequency",
    # WHO published it.  A village government with no website sitting beside a
    # corporation that publishes a full subsidiary directory is a real and
    # common Alaska pattern, and collapsing the two would misattribute the
    # find to the wrong entity.
    "publisher_relationship",   # SELF | AFFILIATED_CORPORATION | NONE
    "affiliated_publisher",
    "affiliated_publisher_verdict",
    # Pointer from the LIST to its governing RULE. The rule itself lives in
    # `tribal_certification_rules_*.csv` (script 323) - this is the join, and
    # it is populated even where no list is published, because a tribe can
    # publish the rule without the roster (Seneca) or the roster without the
    # rule (Cherokee).
    "rule_url",
    "robots_note",              # crawl-delay, named user-agents, WAF behaviour
    "wayback_priority",         # HIGH | MEDIUM | LOW | EXCLUDED
    "wayback_excluded_reason",
    # consent / licence, treated as engineering rather than prose
    "source_terms_status",     # SILENT | TERMS_STATED_PERMISSIVE |
                               # TERMS_STATED_RESTRICTIVE | ROBOTS_DISALLOW |
                               # NOT_CHECKED
    "source_terms_quote",
    "consent_status",          # UNRESOLVED | OPT_IN | OPT_OUT
    "suppression_key",         # flip this one field to remove a tribe
    "publishable",             # Y | N - N whenever consent is not resolved AND
                               # the row would reproduce the tribe's document
    # wayback
    "wayback_snapshots",       # count from the CDX API
    "wayback_first_capture",
    "wayback_last_capture",
    "wayback_checked_date",
    # audit
    "searched",                # required when verdict is NO_LIST_FOUND
    "notes",
    "checked_date",
    "checked_by",
]

ALL_COLUMNS = SPINE_DERIVED + FIELD_COLUMNS

ASSERTION_BY_LIST_TYPE = {
    "TERO": "OWNERSHIP",
    "SUBSIDIARY_DIRECTORY": "OWNERSHIP",
    "SHAREHOLDER_VENDOR": "OWNERSHIP",
    "VENDOR": "RELATIONSHIP",
    "TERO_EMPLOYER": "RELATIONSHIP",
    "LICENSE": "OPERATING_ON_LAND",
    "NONE": "NONE",
    "": "NONE",
}


def _require(row, cols, where):
    """Defect class 2b: RAISE on a missing column, never print a zero."""
    missing = [c for c in cols if c not in row]
    if missing:
        raise KeyError(
            f"{where} is missing column(s) {missing}. A computation aimed at "
            f"a column that is not there prints a zero and looks like a "
            f"finding about the source. Refusing to continue.")


def load_spine():
    with SPINE.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise SystemExit(f"{SPINE} is empty")
    _require(rows[0],
             ["tribe_id", "canonical_name", "entity_class", "state",
              "bia_region", "n_uei_tierA", "n_uei_tierB", "n_cage", "n_ein"],
             str(SPINE))
    return {r["tribe_id"]: r for r in rows}


def load_ranking():
    """Owner-level contracting dollars.  One row per operating company in the
    source, so it is collapsed to one entry per OWNER here."""
    if not RANKING.exists():
        print(f"  ! {RANKING.name} absent - contracting columns will be blank")
        return {}
    with RANKING.open(encoding="utf-8-sig", newline="") as fh:
        rdr = csv.DictReader(fh)
        first = next(rdr, None)
        if first is None:
            return {}
        _require(first,
                 ["owner_entity_id", "owner_rank", "owner_obligations_usd"],
                 str(RANKING))
        out = {}
        for r in [first] + list(rdr):
            out[r["owner_entity_id"]] = (
                r["owner_rank"], r["owner_obligations_usd"])
    return out


def load_existing():
    """Read whatever a previous pass recorded.  NEVER discard it."""
    if not REGISTRY.exists():
        return {}
    with REGISTRY.open(encoding="utf-8-sig", newline="") as fh:
        return {r["tribe_id"]: r for r in csv.DictReader(fh)}


def main():
    spine = load_spine()
    rank = load_ranking()
    existing = load_existing()

    absent = [tid for tid, *_ in ROSTER if tid not in spine]
    if absent:
        # Defect class 2c: a count is not actionable. A NAME is a task.
        raise SystemExit(
            "These roster ids are not in the spine and must be corrected "
            "before the study runs:\n  " + "\n  ".join(absent))

    out_rows = []
    for tid, group, geo, stratum, why in ROSTER:
        s = spine[tid]
        r = rank.get(tid, ("", ""))
        prev = existing.get(tid, {})

        row = {c: "" for c in ALL_COLUMNS}
        # Preserve everything a later pass wrote.  Defect class 2a: these keys
        # already exist holding "", so setdefault would be a silent no-op.
        for c in FIELD_COLUMNS:
            row[c] = prev.get(c) or ""

        holds_nothing = (
            (s["n_uei_tierA"] or "0") == "0"
            and (s["n_cage"] or "0") == "0"
            and (s["n_ein"] or "0") == "0"
            and not r[0])

        row.update({
            "tribe_id": tid,
            "canonical_name": s["canonical_name"],
            "entity_class": s["entity_class"],
            "state": s["state"],
            "bia_region": s["bia_region"],
            "priority_group": group,
            "geography": geo,
            "scale_stratum": stratum,
            "why_chosen": why,
            "contracting_rank": r[0],
            "contracting_obligations_usd": r[1],
            "n_uei_tierA": s["n_uei_tierA"],
            "n_uei_tierB": s["n_uei_tierB"],
            "n_cage": s["n_cage"],
            "n_ein": s["n_ein"],
            "cedar_holds_nothing": "Y" if holds_nothing else "N",
            "roster_built_date": STUDY_DATE,
            "roster_built_by": SCRIPT,
        })

        # Defaults that must never overwrite a recorded value.
        row["verdict"] = row["verdict"] or "NOT_CHECKED"
        row["source_terms_status"] = row["source_terms_status"] or "NOT_CHECKED"
        # Silence is NOT permission.
        row["consent_status"] = row["consent_status"] or "UNRESOLVED"
        row["suppression_key"] = row["suppression_key"] or f"SUPPRESS::{tid}"
        row["publishable"] = row["publishable"] or "N"
        row["list_type"] = row["list_type"] or "NONE"
        row["assertion_class"] = ASSERTION_BY_LIST_TYPE.get(
            row["list_type"], "NONE")
        # The certification verdict mirrors `verdict`; the other two products
        # were not the subject of this pass and default to NOT_CHECKED, which
        # is honest. A guess is not.
        row["verdict_certification"] = (
            row["verdict_certification"] or row["verdict"])
        row["verdict_vendor_relationship"] = (
            row["verdict_vendor_relationship"] or "NOT_CHECKED")
        row["verdict_business_licence"] = (
            row["verdict_business_licence"] or "NOT_CHECKED")
        out_rows.append(row)

    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    if REGISTRY.exists():
        bak = REGISTRY.with_suffix(
            REGISTRY.suffix + f".bak_{STUDY_DATE}_pre_{SCRIPT}")
        bak.write_bytes(REGISTRY.read_bytes())
        print(f"  backed up -> {bak.name}")

    part = REGISTRY.with_suffix(REGISTRY.suffix + ".part")
    with part.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=ALL_COLUMNS)
        w.writeheader()
        w.writerows(out_rows)
    part.replace(REGISTRY)

    # Verify by RE-READING, not by trusting the run log (concurrency rule 4).
    with REGISTRY.open(encoding="utf-8-sig", newline="") as fh:
        back = list(csv.DictReader(fh))
    if len(back) != len(ROSTER):
        raise SystemExit(
            f"re-read got {len(back)} rows, wrote {len(ROSTER)}")

    print(f"\n{REGISTRY.relative_to(ROOT)}  ({len(back)} rows, re-read OK)")
    by_group = {}
    for r in back:
        g = r["priority_group"]
        by_group[g] = by_group.get(g, 0) + 1
    print("  priority groups:", by_group)
    print("  hold-nothing entities:",
          sum(1 for r in back if r["cedar_holds_nothing"] == "Y"))
    verdicts = {}
    for r in back:
        verdicts[r["verdict"]] = verdicts.get(r["verdict"], 0) + 1
    print("  verdicts:", verdicts)
    print("\n  hosts recorded so far:",
          sum(1 for r in back if r["hosts"]),
          "- run 317 for the Wayback CDX sweep once these are populated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
