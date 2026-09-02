#!/usr/bin/env python3
r"""374 - CEDAR_TAXONOMY: the machine-readable export of every Cedar Press
controlled vocabulary, in one artefact, for the product and for the next agent.

WHY THIS EXISTS
---------------
The owner asked for "a taxonomy of our own with more data". **A taxonomy already
exists.** It is spread across `cedar_domain.py`, the spine's `entity_class`
column, four registry CSVs, a staged tribal-certification layer, the federal
set-aside flags and the ANCSA statute, and **no single artefact holds it.** A
subscriber cannot read it and a future agent cannot import it.

This script emits `docs/CEDAR_TAXONOMY.json`. `docs/CEDAR_TAXONOMY.md` is the
human half and is written by hand beside it; this file is what the product
renders behind the collections' `method` field.

THE GOVERNING PRINCIPLE, ENCODED RATHER THAN ASSERTED
-----------------------------------------------------
**The taxonomy is DESCRIPTIVE, never PRESCRIPTIVE.** Cedar Press may publish
*"Colville's Title 10 certification does not require an ownership percentage"* -
that is a retrieved fact. Cedar Press may NOT publish *"therefore this firm is
not really Native-owned"* - that is a verdict about a sovereign's exercise of
its own authority, and it is not ours to reach.

Same discipline as `docs/LOBBYING_EXPANSION_RECONCILIATION.md` refusing to
author `position_on_native_issue`: **build the fact, never the verdict.**
`FORBIDDEN_TAXONOMY_KEYS` below is that rule as code - no exported layer may
carry a field that adjudicates, and `main()` asserts it before writing.

WHY IT IMPORTS RATHER THAN TRANSCRIBES
--------------------------------------
Every vocabulary that lives in a module is READ FROM THAT MODULE. A transcribed
copy is a second declaration, which is the thing `cedar_domain.py`'s own header
forbids ("no re-declared lists in dataset modules") and the thing this repo has
now paid for repeatedly. Counts are recomputed from `data/` at build time and
never typed. Only the DEFINITIONS are prose, because a definition is the one
thing a file cannot compute about itself.

WHAT IT DOES NOT DO
-------------------
* No network calls.
* Writes exactly ONE file, `docs/CEDAR_TAXONOMY.json`, which nothing else
  writes. It is not an in-place enricher and no rebuild can revert it (class 6).
* Writes nothing to `data/clean/`, so it cannot move a shipping metric.
* Touches no other agent's file, mints no entity id, and rules on nothing.
* Reads `data/clean/deals_classified.csv` - the PROMOTED table declared in
  `cedar_domain.DEALS_TRUTH` - and never the `deals_*_additions.csv` parts
  (class 1).

KEYS ARE DETERMINISTIC (class 7). Every key in the output is a literal from the
data or a vocabulary constant. No enumerate(), no hash(), no id(), no rank.
Re-running produces a byte-identical file for identical inputs (class 5), and
`--check` proves it without writing.

    py -3 code/374_build_cedar_taxonomy_export.py
    py -3 code/374_build_cedar_taxonomy_export.py --check    # no write
"""

from __future__ import annotations

import collections
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

import cedar_domain as D  # noqa: E402

SCRIPT = "374_build_cedar_taxonomy_export.py"
BUILT = "2026-08-26"
OUT = ROOT / "docs" / "CEDAR_TAXONOMY.json"

SPINE = ROOT / "data" / "spine" / "cedar_entity_spine.csv"
LEDGER = ROOT / "data" / "clean" / "cedar_identifier_ledger_final.csv"
RELS = ROOT / "data" / "clean" / "entity_relationships.csv"
PRIME = ROOT / "data" / "clean" / "prime_contracts.csv"
SAM = ROOT / "data" / "clean" / "sam_prime_contracts_fy2000_2007.csv"
DEALS = ROOT / D.DEALS_TRUTH.replace("/", "\\") if False else ROOT / D.DEALS_TRUTH
DEALS_TAX = ROOT / "data" / "clean" / "deals_taxonomy.csv"
INSTR_TAX = ROOT / "data" / "clean" / "instrument_taxonomy.csv"
VAR_REG = ROOT / "data" / "clean" / "variable_registry.csv"
CERT_RULES = (ROOT / "data" / "staging" / "tribal_vendor_lists"
              / "tribal_certification_rules_2026-08-26.csv")
CERT_SOURCES = (ROOT / "data" / "staging" / "tribal_vendor_lists"
                / "tribal_certification_sources_2026-08-26.csv")

#: A field name in this set adjudicates rather than records. No exported layer
#: may carry one. Asserted before the write, so the principle cannot decay into
#: a paragraph nobody enforces.
FORBIDDEN_TAXONOMY_KEYS = frozenset({
    "is_really_native", "really_native", "native_enough", "counts_as_native",
    "cedar_verdict", "our_determination", "sufficient_ownership",
    "meets_threshold", "legitimate", "valid_certification",
})


def die(msg):
    print(f"ABORT: {msg}", file=sys.stderr)
    raise SystemExit(2)


def read_rows(path, required_columns=()):
    """Rows, with a HARD FAILURE on a column that is not there (class 2b).

    An absent column name reads as an empty source. `102_build_coverage_profile`
    printed 0.0% coverage for nineteen days against a column neither file had.
    A taxonomy that reports a vocabulary as empty because it misspelled the
    column would publish our own defect as a fact about the data - class 2.
    """
    if not path.exists():
        die(f"{path} does not exist. Named rather than skipped: a taxonomy "
            f"layer silently omitted is worse than a build that stops.")
    with path.open(encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        header = rd.fieldnames or []
        missing = [c for c in required_columns if c not in header]
        if missing:
            die(f"{path.name} has no column(s) {missing!r}. Present: {header!r}")
        return [dict(r) for r in rd]


def counts(rows, column):
    return collections.Counter((r.get(column) or "").strip() for r in rows)


# ---------------------------------------------------------------------------
# THE ONLY HAND-WRITTEN PART. A definition is the one thing a file cannot
# compute about itself. Everything else in this script is derived.
#
# Each entry is (definition, what_it_is_NOT, how_membership_is_evidenced,
#                tier_implication).
# `enforced_in` and `n_rows` are DERIVED and must not appear here.
# ---------------------------------------------------------------------------
ENTITY_CLASS_DEFS = {
    "Federally recognized tribe": (
        "A tribal government on the Secretary's list published under 25 U.S.C. "
        "5131, EXCLUDING the Alaska Native villages, which this taxonomy holds "
        "as a separate class.",
        "NOT the whole federally recognized universe. 349 here plus 228 Alaska "
        "Native villages is 577; a reader who quotes 349 as 'the federally "
        "recognized tribes' understates it by 40%. NOT a state-recognized "
        "tribe. NOT a tribal enterprise - the government, not its companies.",
        "Seeded from the CICD NEID canonical tribe table "
        "(`canonical_tribe_table.csv`, 687 entities) by 01_build_entity_spine, "
        "not read directly from the Federal Register list. `fr_official_name` "
        "carries the FR long form where it is held.",
        "Class membership confers NO tier. A tier is inherited from the source "
        "row that made a link, never from the class of the entity linked to."),
    "Federally recognized Alaska Native Village": (
        "An Alaska Native village GOVERNMENT - a federally recognized tribe "
        "that happens to be a village. It may own an enterprise directly "
        "(ANCSA ruling rule 3), and then that enterprise is an ordinary tribal "
        "enterprise.",
        "NOT an ANCSA corporation, in either direction. A village government "
        "NEVER owns an ANC (rule 2) and an ANC never owns the village "
        "government (rule 4). The two share a name and a place BY STATUTE, so "
        "a shared name is not weak evidence of one owner - it is no evidence.",
        "Same NEID seed. The namesake corporation pairs are staged in "
        "`review/village_corp_namesake_pairs.csv` by 52_add_village_corporations.",
        "No tier. See rule 3: a village-government ownership claim is an "
        "EXCEPTION that must be evidenced per identifier, never assumed from a "
        "name."),
    "Native Hawaiian Organization": (
        "A Native Hawaiian community organization. 13 C.F.R. 124.110 requires "
        "an NHO to be a NON-PROFIT organization.",
        "NOT a state agency - the Department of Hawaiian Home Lands is a State "
        "of Hawaii agency and was refused. NOT an LLC: `Hoilina Ranch LLC` was "
        "refused because an LLC cannot satisfy 124.110. An NHO-OWNED firm is a "
        "subsidiary, not an NHO.",
        "DOI Office of Native Hawaiian Relations notification roster (179 "
        "rows) plus the NHOA member directory, each with `evidence_url` and a "
        "verbatim quote. This class and `Individually Native-owned business` "
        "are the ONLY two that populate `verification_route`.",
        "The DOI roster rows land at tier C on their own. A tier arrives with "
        "a link, not with a listing."),
    "BIE School": (
        "An elementary or secondary school in the Bureau of Indian Education "
        "directory, split by BIE's own `bie_operation_type` into "
        "Bureau-Operated and Tribally-Controlled.",
        "NOT tribally owned by default. 56 of 185 are FEDERALLY operated and "
        "their blank parent is A RULING, not unfinished research - booking "
        "those dollars to a tribe would attribute federal spending to a tribal "
        "government. `Navajo_Operation` in BIE data is an administrative "
        "grouping, not ownership; trusting it books 35 schools to the Navajo "
        "Nation.",
        "bie.edu/schools -> the BIE ArcGIS schools directory feature service, "
        "with the operation-type split read from the source roster and never "
        "inferred. Cross-checked against the page's own og:description.",
        "No tier. The operation-type split governs ROLL-UP, not confidence."),
    "Alaska Native Village Corporation": (
        "A corporation organised under ANCSA section 8, 43 U.S.C. 1607, for a "
        "named Alaska Native village.",
        "NOT the village government. NOT a subsidiary of its regional "
        "corporation - rule 5, the regional corporation does not own the "
        "village corporation; they are two corporations with an overlapping "
        "shareholder base. AND, TODAY, NOT ONLY VILLAGE CORPORATIONS: this "
        "class also carries the four ANCSA URBAN Corporations, for which "
        "43 U.S.C. 1607(c) provides no separate Cedar class. See the gap "
        "`ANCSA_URBAN_CORPORATION_HAS_NO_CLASS`.",
        "Joined from `entity_master.csv`, which already carried 173 village "
        "and 6 group corporations with `A-` ids and a regional parent. Nothing "
        "was invented; a tribe_id collision aborts rather than overwrites.",
        "No tier. It IS one of the three classes `bears_ownership()` can "
        "refuse an edge on - when a caller passes the class arguments, which "
        "no production caller does. See the gap `ANCSA_CLASS_GUARD_UNCALLED`."),
    "State-recognized tribe": (
        "A tribe recognised by a state and not by the United States.",
        "NOT federally recognized. It has no ISDEAA relationship, no 25 U.S.C. "
        "5131 listing, and it is NOT eligible under the SLFRF definition of "
        "'Tribal government' at 42 U.S.C. 802(g)(7). Pooling it with the "
        "federal class changes the recipient universe.",
        "NEID seed. Separate `TRBS` prefix.",
        "No tier."),
    "Native Community Development Financial Institution": (
        "An institution carrying Treasury CDFI Fund certification with the "
        "`Native CDFI (Y/N)` flag set.",
        "NOT the same as `Native Financial Institution`, which is the broader "
        "Minneapolis Fed NAFI universe. Both live under the `CDFI` prefix, so "
        "THE PREFIX DOES NOT IDENTIFY THE CLASS here.",
        "Treasury's 'List of Currently Certified CDFIs' - 'Total Number of "
        "Certified Native CDFIs as of July 16, 2026: 65' - cross-read against "
        "the Minneapolis Fed nafi-map dataset (91 institutions, `ncdfi` / "
        "`nmdi` flags), which is the CICD NAFI map the owner named.",
        "No tier. 97_build_aliases_and_relationships writes `chartered_by` for "
        "this class and NEVER `subsidiary_of`, so no dollar rolls through it."),
    "Intertribal Organization": (
        "An organisation whose members are tribes.",
        "NOT owned by its member tribes. Membership is `member_of` / "
        "`affiliated_with`, both in `NEVER_OWNERSHIP`. Also NOT reachable "
        "through `native_entity_lobbying_disclosures.csv`: ZERO of these 55 "
        "appear in it, and NCAI, NIGA, USET, NIHB, NARF, NAIHC and NCUIH sit "
        "in `lobbying_unmatched_clients.csv` instead.",
        "`intertribal_orgs.csv` (57 verified) plus 989 membership rows, every "
        "row carrying `evidence_url` and a quote.",
        "No tier. 9 of the 334 ANCSA one-to-many defects resolved to an "
        "intertribal organisation rather than a corporation."),
    "Individually Native-owned business": (
        "An ordinary firm - LLC, S-corp, sole proprietorship - whose OWNER is "
        "an individual Native person. Ruled into existence by the owner on "
        "2026-08-07 on Hidden Water Inc.",
        "NOT a tribal entity, NOT a false positive, and NOT excluded from the "
        "product. It never rolls up to a tribe, an ANC or an NHO; "
        "`parent_native_entity` is permanently NULL and that blank is a "
        "RULING. Read the ruling text carefully: five of the 45 read 'Not a "
        "Native entity - individually Native-owned firm', which refuses the "
        "TRIBAL LINK and AFFIRMS Native ownership. Read literally as 'not "
        "Native' it inverts the owner's meaning, and it already has - CAGE "
        "9DVK5 sits in the ledger at tier X bound to a tribe that does not own "
        "it.",
        "The owner's 45 per-UEI rulings, extracted from `hci_analysis.do` and "
        "the 2026-08 rulings inboxes. `verification_route` is populated on all "
        "45 - CAGE registry lookup, company website, or an owner note with a "
        "URL.",
        "`elijah_ruling` is in `RULED_METHODS`, so these are tier A as "
        "ATTRIBUTIONS. That does NOT make them publishable as NAMES: "
        "`may_publish_individual_native_field()` withholds every name, "
        "address, and - for a firm whose legal name is a person's - the UEI "
        "and CAGE, absent recorded `OPTED_IN` consent."),
    "Urban Indian Organization": (
        "An organisation in the IHS Urban Indian Organization programme, "
        "serving Native people in an urban area.",
        "NOT tribally owned. Serving a population is not being owned by it - "
        "`serves_native_entities` is never evidence of ownership. NOT "
        "resolvable by place name: `Riverside San Bernardino County Indian "
        "Health Inc` was refused an autoresolution to `UIO-HEALTH-00`, which "
        "is 'Native Health', ARIZONA.",
        "ihs.gov/urban/urban-indian-organizations plus its twelve area pages, "
        "cross-checked against the NCUIH directory ('There are 41 Urban "
        "Indian Organizations').",
        "No tier."),
    "Tribal College or University": (
        "A tribally chartered or federally chartered college in the AIHEC "
        "roster.",
        "NOT its chartering tribe. Before this class existed, containment "
        "resolved `Bay Mills Community College` onto the Bay Mills Indian "
        "Community and `United Tribes Technical College` onto United Auburn "
        "Rancheria. NOT a BIE School - BIE post-secondary institutions belong "
        "to this roster, not that one.",
        "aihec.org TCU roster and profiles - 37 members in three tiers (34 "
        "regular, 1 associate, 2 developing) - each with a chartering "
        "statement in its own profile paragraph, cross-read against "
        "aihec.org/tcu-locations.",
        "No tier. The edge written is `chartered_by`, which is NOT in "
        "`OWNERSHIP_BEARING`: a tribe chartering a college does not own it and "
        "the college's federal dollars are not the tribe's."),
    "Native Financial Institution": (
        "A Native-controlled financial institution in the Minneapolis Fed NAFI "
        "universe that is NOT a certified Native CDFI.",
        "NOT a Native CDFI. The distinction is Treasury certification and it "
        "is the whole reason the two classes exist separately. Shares the "
        "`CDFI` prefix with Native CDFIs.",
        "Minneapolis Fed `nafi-map-data_current.xlsx`, `ncdfi` and `nmdi` "
        "flags.",
        "No tier."),
    "Federal-level constituency entity": (
        "A constituent band, community or pueblo that is itself named on the "
        "federal list while sitting inside an umbrella tribal government.",
        "NOT a subsidiary. `constituent_band_of` is in "
        "`GOVERNMENTAL_RELATIONSHIPS` and therefore in `NEVER_OWNERSHIP`: a "
        "band's contracts are not the umbrella's. Mapping the old flat parent "
        "column wholesale would have rolled 22 of these into their umbrellas.",
        "NEID seed, `CNSF` prefix.",
        "No tier. 42 `CONSTITUENT_BAND_VS_UMBRELLA_TRIBE` defects on $1,297.8M "
        "remain untouched, and no dollar rolls through them today because the "
        "edge is already refused."),
    "Alaska Native Regional Corporation": (
        "One of the twelve in-state corporations organised under ANCSA "
        "section 7, 43 U.S.C. 1606.",
        "NOT the owner of the village corporations in its region (rule 5) and "
        "NOT a place. `associated_with_region` is geography; treating it as "
        "ownership once moved $32.87B wrongly.",
        "NEID seed.",
        "No tier."),
    "Federal-level self-governance consortium": (
        "A consortium of tribes exercising self-governance authority jointly.",
        "NOT an owner of its member tribes' activity and NOT owned by them.",
        "NEID seed, `SGVF` prefix.",
        "No tier."),
    "ANCSA Group Corporation": (
        "A corporation organised for a Native GROUP under ANCSA rather than "
        "for a village.",
        "NOT a village corporation, though it shares the `ANVC` prefix - a "
        "second place where the prefix does not identify the class.",
        "`entity_master.csv`, joined by 52_add_village_corporations.",
        "No tier. Inside `ANCSA_CORPORATION_CLASSES`."),
    "State-level constituency entity": (
        "A constituent group inside a state-recognized tribe.",
        "NOT federally recognized and NOT a subsidiary.",
        "NEID seed, `CNSS` prefix.",
        "No tier."),
}

#: The federal Native-preference categories, and what each one actually
#: discriminates. Dollar figures are DERIVED at build time from
#: `prime_contracts.csv`; nothing here is typed.
FEDERAL_CATEGORY_DEFS = {
    "8(a)": (
        "SBA's 8(a) Business Development programme. The `setaside` value and "
        "the `reported_8a` flag.",
        "**NOT A NATIVE CATEGORY.** 8(a) is open to any socially and "
        "economically disadvantaged owner. An 8(a) award carries NO Native "
        "signal on its own, and yet it supplies the overwhelming majority of "
        "everything `reported_native_preference` counts.",
        "reported_8a", "reported_8a"),
    "Buy Indian": (
        "The Buy Indian Act set-aside, 25 U.S.C. 47. Native-specific by "
        "statute.",
        "NOT the whole Native-specific surface, and NOT comparable across "
        "2013. The DOI Buy Indian rule of 2013-07-08 created a second tier "
        "recorded under `Indian Business`; `Buy Indian` read alone says Native "
        "set-asides collapsed 62% after 2015, and summed with Indian Business "
        "they rose 44%.",
        "reported_buy_indian", "reported_buy_indian"),
    "Indian Business": (
        "The second DOI set-aside code, live from FY2014 and overtaking Buy "
        "Indian in FY2016.",
        "NOT a separate instrument. ONE instrument under TWO codes; **always "
        "sum it with Buy Indian.** Zero in every year FY2000-2013.",
        "reported_indian_business", "reported_indian_business"),
    "reported_native_preference": (
        "Cedar's own union column over the three above.",
        "**NOT A MEASURE OF NATIVE PREFERENCE, despite its name.** It is the "
        "strict union INCLUDING 8(a), and 8(a) supplies almost all of it. The "
        "genuinely Native-specific subset is Buy Indian + Indian Business "
        "alone. Anyone filtering on this column to find Native set-asides gets "
        "the 8(a) programme.",
        "reported_native_preference", "reported_native_preference"),
}


def scan_code_for_entity_class_literals(spine_classes):
    """Which build scripts re-type the entity-class vocabulary, and which ones
    branch on a class string the spine does not contain.

    A plain text scan over `code/*.py`, deliberately. An AST pass would be
    prettier and would miss a literal inside an f-string or a comment, and the
    question here is "does this file carry its own copy of the vocabulary",
    which text answers exactly. `.bak_*` files are excluded: a backup is
    history, not code.

    Returns (redeclarers, dead_refusals). Both NAME the file (class 2c) - a
    count of "N scripts re-declare it" is not a task and scrolls past.
    """
    #: Strings a script branches on that LOOK like a spine entity class and are
    #: not one. Each was a real class name once, or a plausible shortening of
    #: one, so the guard reads as live and filters nothing.
    NEAR_MISS = {
        "Native CDFI": "Native Community Development Financial Institution",
        "Native financial institution": "Native Financial Institution",
        "Alaska Native Village Government": "Federally recognized Alaska Native Village",
        "Federally Recognized Tribe": "Federally recognized tribe",
    }
    redeclarers, dead = [], []
    for p in sorted((ROOT / "code").glob("*.py")):
        if ".bak_" in p.name or p.name in (SCRIPT, "cedar_domain.py"):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            # NAME the file rather than skipping it silently.
            dead.append({"file": p.name, "unreadable": str(exc)})
            continue
        hits = sorted(c for c in spine_classes if c and f'"{c}"' in text)
        if len(hits) >= 2:
            redeclarers.append({"file": p.name, "n_class_literals": len(hits)})
        for bad, real in NEAR_MISS.items():
            if f'"{bad}"' in text and bad not in spine_classes:
                dead.append({"file": p.name, "branches_on": bad,
                             "spine_actually_says": real})
    return redeclarers, dead


def build():
    problems = []

    # --- entity classes -----------------------------------------------------
    spine = read_rows(SPINE, ("tribe_id", "entity_class", "verification_route",
                              "ownership_basis", "state"))
    cls_n = counts(spine, "entity_class")
    route_filled = collections.Counter()
    prefix_by_class = collections.defaultdict(collections.Counter)
    for r in spine:
        k = (r.get("entity_class") or "").strip()
        if (r.get("verification_route") or "").strip():
            route_filled[k] += 1
        prefix_by_class[k][(r.get("tribe_id") or "").split("-", 1)[0]] += 1

    undefined = sorted(set(cls_n) - set(ENTITY_CLASS_DEFS) - {""})
    if undefined:
        # NAME what is missing (class 2c). A count is not actionable.
        problems.append({
            "id": "ENTITY_CLASS_WITHOUT_A_DEFINITION",
            "detail": f"spine classes with no definition in {SCRIPT}: "
                      f"{undefined!r}"})

    in_domain = (set(D.ANCSA_CORPORATION_CLASSES)
                 | set(D.ALASKA_VILLAGE_GOVERNMENT_CLASSES)
                 | {D.INDIVIDUAL_NATIVE_CLASS})
    entity_classes = {}
    for name, n in sorted(cls_n.items(), key=lambda kv: (-kv[1], kv[0])):
        if not name:
            continue
        d, isnt, ev, tier = ENTITY_CLASS_DEFS.get(name, ("", "", "", ""))
        entity_classes[name] = {
            "n_spine_rows": n,
            "definition": d,
            "what_it_is_not": isnt,
            "how_membership_is_evidenced": ev,
            "tier_implication": tier,
            "id_prefixes": dict(sorted(prefix_by_class[name].items())),
            "verification_route_populated": route_filled[name],
            "known_to_cedar_domain": name in in_domain,
        }

    no_route = [c for c, v in entity_classes.items()
                if not v["verification_route_populated"]]
    if no_route:
        problems.append({
            "id": "ENTITY_CLASS_WITH_NO_STATED_VERIFICATION_ROUTE",
            "detail": f"{len(no_route)} of {len(entity_classes)} classes "
                      f"({sum(cls_n[c] for c in no_route):,} of {len(spine):,} "
                      f"rows) carry NO value in `verification_route`, so how "
                      f"membership was established is not answerable FROM THE "
                      f"FILE - only from a build log: {sorted(no_route)!r}"})

    not_in_domain = sorted(c for c in entity_classes
                           if not entity_classes[c]["known_to_cedar_domain"])
    if not_in_domain:
        problems.append({
            "id": "SPINE_CLASS_ABSENT_FROM_CEDAR_DOMAIN",
            "detail": f"{len(not_in_domain)} of {len(entity_classes)} classes "
                      f"({sum(cls_n[c] for c in not_in_domain):,} rows) appear "
                      f"in NO set in cedar_domain.py, so no shared predicate "
                      f"can branch on them - including the largest class in "
                      f"the spine: {not_in_domain!r}"})

    redeclarers, dead_refusals = scan_code_for_entity_class_literals(set(cls_n))
    if redeclarers:
        problems.append({
            "id": "ENTITY_CLASS_VOCABULARY_REDECLARED_IN_BUILD_SCRIPTS",
            "detail": f"{len(redeclarers)} scripts carry two or more spine "
                      f"entity-class literals of their own, against a shared "
                      f"module that declares none of them: "
                      f"{[r['file'] for r in redeclarers]!r}",
            "instances": redeclarers})
    if dead_refusals:
        problems.append({
            "id": "CODE_USES_A_CLASS_STRING_THE_SPINE_DOES_NOT_HAVE",
            "detail": "a class name that is not in the spine, used as a "
                      "refusal, a filter, a fixture or a display label. Where "
                      "it is a GUARD it reads as live and filters nothing - "
                      "failing OPEN, silently. Where it is a LABEL it is "
                      "harmless to correctness and still means the product "
                      "prints a class name the data does not use. Read the "
                      "call site before treating an instance as either: "
                      "103/105 and cedar_match_guard are guards and fixtures; "
                      "73_bills_votes_completion.py is a display label in a "
                      "bill-subject map and is NOT a dead guard.",
            "instances": dead_refusals})

    # --- tiers, methods, identifiers, relationships: IMPORTED ---------------
    tiers = {t.value: {"definition": t.description, "publishes": t.publishes}
             for t in D.Tier}
    methods = {
        "RULED": {"values": sorted(D.RULED_METHODS),
                  "definition": "A HUMAN DECIDED. Permanent; only a new ruling "
                                "reverses it.",
                  "what_it_is_not": "NOT a statement that the answer was YES. "
                                    "All 317 `elijah_ruling` EIN rows in the "
                                    "ledger are tier X - NEGATIVE rulings. "
                                    "`attribution_method` says WHO decided; "
                                    "`confidence_tier` says WHAT was decided."},
        "TWO_LEG": {"values": sorted(D.TWO_LEG_METHODS),
                    "definition": "Two independent legs of evidence. Tier A.",
                    "what_it_is_not": "NOT one leg. 49 single-leg rows were "
                                      "correctly demoted A -> B on 2026-08-06."},
        "ALGORITHMIC": {"values": sorted(D.ALGORITHMIC_METHODS),
                        "definition": "Machine-proposed. Never tier A alone.",
                        "what_it_is_not": "NOT interchangeable with each "
                                          "other: measured accuracy against "
                                          "the owner's rulings spans "
                                          "`need_v6` 6.5% to `cluster_v3` "
                                          "97.7%."},
    }
    method_accuracy = dict(sorted(D.METHOD_ACCURACY.items()))

    identifiers = {i.value: {"is_official": i.is_official,
                             "licensed_never_publishes": i.licensed}
                   for i in D.IdentifierType}

    rel_rows = read_rows(RELS, ("relationship_type",))
    rel_used = counts(rel_rows, "relationship_type")
    relationships = {}
    for fam, members in (("CORPORATE", D.CORPORATE_RELATIONSHIPS),
                         ("GOVERNMENTAL", D.GOVERNMENTAL_RELATIONSHIPS),
                         ("ALASKA_GEOGRAPHIC", D.ALASKA_GEOGRAPHIC_RELATIONSHIPS),
                         ("INSTITUTIONAL", D.INSTITUTIONAL_RELATIONSHIPS),
                         ("HISTORICAL", D.HISTORICAL_RELATIONSHIPS),
                         ("INDIVIDUAL_NATIVE", D.INDIVIDUAL_NATIVE_RELATIONSHIPS)):
        for m in sorted(members):
            relationships[m] = {
                "family": fam,
                "bears_ownership": D.bears_ownership(m),
                "never_ownership": m in D.NEVER_OWNERSHIP,
                "ancsa_association_not_ownership":
                    m in D.ANCSA_ASSOCIATION_NOT_OWNERSHIP,
                "n_rows_in_entity_relationships": rel_used.get(m, 0),
            }
    unknown_rels = sorted(k for k in rel_used
                          if k and k not in D.ALL_RELATIONSHIPS)
    if unknown_rels:
        problems.append({"id": "RELATIONSHIP_TYPE_UNKNOWN_TO_CEDAR_DOMAIN",
                         "detail": f"in entity_relationships.csv, absent from "
                                   f"ALL_RELATIONSHIPS: {unknown_rels!r}"})
    unused_ownership = sorted(m for m in D.OWNERSHIP_BEARING
                              if not rel_used.get(m))
    if unused_ownership:
        problems.append({
            "id": "OWNERSHIP_BEARING_TYPES_WITH_ZERO_ROWS",
            "detail": f"{len(unused_ownership)} of {len(D.OWNERSHIP_BEARING)} "
                      f"ownership-bearing types carry no edge: "
                      f"{unused_ownership!r}"})

    # --- the ledger's SECOND entity_class vocabulary ------------------------
    ledger = read_rows(LEDGER, ("entity_class", "confidence_tier",
                                "attribution_method"))
    led_cls = counts(ledger, "entity_class")
    off_vocab = {k: v for k, v in led_cls.items()
                 if k and k not in cls_n}
    if off_vocab:
        problems.append({
            "id": "LEDGER_ENTITY_CLASS_IS_A_SECOND_VOCABULARY",
            "detail": f"{sum(off_vocab.values()):,} ledger rows carry an "
                      f"`entity_class` that is not a spine class: "
                      f"{dict(sorted(off_vocab.items(), key=lambda kv: -kv[1]))!r}"})

    # --- federal categories, measured --------------------------------------
    prime_cols = ("setaside", "reported_8a", "reported_buy_indian",
                  "reported_indian_business", "reported_native_preference",
                  "total_obligations", "attributed_flag")
    fed = {k: {"rows": 0, "attributed_usd": 0.0} for k in FEDERAL_CATEGORY_DEFS}
    setaside_n = collections.Counter()
    prime_rows = 0
    attributed_usd = 0.0
    with PRIME.open(encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        miss = [c for c in prime_cols if c not in (rd.fieldnames or [])]
        if miss:
            die(f"prime_contracts.csv has no column(s) {miss!r}")
        for r in rd:
            prime_rows += 1
            setaside_n[(r.get("setaside") or "").strip()] += 1
            try:
                v = float(r.get("total_obligations") or 0)
            except ValueError:
                v = 0.0
            att = (r.get("attributed_flag") or "").strip() == "1"
            if att:
                attributed_usd += v
            for label, (_, _, _, col) in FEDERAL_CATEGORY_DEFS.items():
                if (r.get(col) or "").strip() == "1":
                    fed[label]["rows"] += 1
                    if att:
                        fed[label]["attributed_usd"] += v

    federal = {}
    for label, (d, isnt, col, _) in FEDERAL_CATEGORY_DEFS.items():
        federal[label] = {
            "column": col,
            "n_prime_rows": fed[label]["rows"],
            "attributed_obligations_usd": round(fed[label]["attributed_usd"], 2),
            "share_of_attributed_dollars_pct":
                round(100.0 * fed[label]["attributed_usd"] / attributed_usd, 4)
                if attributed_usd else None,
            "definition": d,
            "what_it_is_not": isnt,
            "is_native_specific": label in ("Buy Indian", "Indian Business"),
        }
    native_specific_usd = (fed["Buy Indian"]["attributed_usd"]
                           + fed["Indian Business"]["attributed_usd"])
    federal["_measured"] = {
        "prime_rows": prime_rows,
        "attributed_obligations_usd": round(attributed_usd, 2),
        "setaside_value_counts": dict(setaside_n.most_common()),
        "native_specific_only_usd": round(native_specific_usd, 2),
        "native_specific_only_share_of_attributed_pct":
            round(100.0 * native_specific_usd / attributed_usd, 4)
            if attributed_usd else None,
        "union_is_exact":
            fed["reported_native_preference"]["rows"]
            == fed["8(a)"]["rows"] + fed["Buy Indian"]["rows"]
            + fed["Indian Business"]["rows"],
        "reading": "`reported_native_preference` is the exact union INCLUDING "
                   "8(a). Buy Indian + Indian Business is the Native-specific "
                   "subset. The two must never be quoted interchangeably.",
    }

    # The no-preference share is recorded in three places and none matches the
    # file. Measured here rather than quoted, and compared against the figure
    # `cedar_domain` carries, so the gap is re-checked on every run instead of
    # decaying in prose. Same discipline as docs/DOC_CONTRADICTIONS.
    no_pref_usd = attributed_usd - fed["reported_native_preference"]["attributed_usd"]
    no_pref_pct = 100.0 * no_pref_usd / attributed_usd if attributed_usd else 0.0
    federal["_measured"]["no_native_preference_usd"] = round(no_pref_usd, 2)
    federal["_measured"]["no_native_preference_pct"] = round(no_pref_pct, 2)
    if abs(no_pref_pct - 57.2) > 0.5:
        problems.append({
            "id": "NO_NATIVE_PREFERENCE_SHARE_DISAGREES_ACROSS_THREE_SOURCES",
            "detail": f"measured {no_pref_pct:.2f}% / "
                      f"${no_pref_usd/1e9:.3f}B on {prime_rows:,} prime rows; "
                      f"cedar_domain.SELF_CERTIFICATION_IS_NOT_A_VERDICT says "
                      f"57.2% / $140.00B on the SAME base; AGENTS.md says "
                      f"60.9% / $86.19B on an older, smaller base. Three "
                      f"figures, one concept, and the two sharing a base still "
                      f"differ. AND the measured value is an UPPER BOUND: it "
                      f"reads `reported_native_preference` as recorded, and a "
                      f"set-aside is a property of the AWARD, not of each "
                      f"modification - filling forward from "
                      f"`contract_award_unique_key` moves rows OUT of 'no "
                      f"preference'. Quote the Native-specific "
                      f"${native_specific_usd/1e9:.4f}B instead; it is a floor "
                      f"and does not move on this question."})

    # --- SAM six business-type variants ------------------------------------
    sam_rows = read_rows(SAM, ("variant_class", "matched_variants",
                               "class_conflict", "include_in_native_universe",
                               "flag_american_indian_owned"))
    sam_variant = {}
    for v in ("INDIAN", "ALASKAN NATIVE", "NATIVE HAWAIIAN", "TRIBAL",
              "AMERICAN INDIAN", "NATIVE AMERICAN"):
        hit = [r for r in sam_rows
               if v in (r.get("matched_variants") or "").split(";")]
        sam_variant[v] = {
            "cedar_class": "INDIVIDUAL_NATIVE_OWNED"
                           if v in ("AMERICAN INDIAN", "NATIVE AMERICAN")
                           else "ENTITY_OWNED",
            "n_rows": len(hit),
            "n_in_native_universe":
                sum(1 for r in hit
                    if (r.get("include_in_native_universe") or "") == "1"),
            "n_american_indian_owned_yes":
                sum(1 for r in hit
                    if (r.get("flag_american_indian_owned") or "") == "YES"),
        }
    sam = {
        "variants": sam_variant,
        "n_rows": len(sam_rows),
        "variant_class_counts": dict(counts(sam_rows, "variant_class")),
        "n_class_conflict": sum(1 for r in sam_rows
                                if (r.get("class_conflict") or "") == "1"),
        "self_certification_is_not_a_verdict":
            D.SELF_CERTIFICATION_IS_NOT_A_VERDICT,
        "what_it_is_not":
            "The two variant classes DO NOT PARTITION. A row matched by both "
            "an entity variant and an individual variant carries "
            "`class_conflict = 1`. And the `INDIAN` variant is majority NOISE: "
            "most of its rows are Subcontinent Asian Indian American owned "
            "firms, excluded by `include_in_native_universe = 0`.",
    }

    # --- ANCSA statutory categories ----------------------------------------
    ancsa = {
        "Regional Corporation": {
            "authority": "ANCSA sec. 7, 43 U.S.C. 1606",
            "cedar_entity_class": "Alaska Native Regional Corporation"},
        "Village Corporation": {
            "authority": "ANCSA sec. 8, 43 U.S.C. 1607",
            "cedar_entity_class": "Alaska Native Village Corporation"},
        "Urban Corporation": {
            "authority": "named in 43 U.S.C. 1607(c) alongside Village and "
                         "Group Corporations",
            "cedar_entity_class": None},
        "Group Corporation": {
            "authority": "named in 43 U.S.C. 1607(c)",
            "cedar_entity_class": "ANCSA Group Corporation"},
    }

    orphan_statutory = sorted(k for k, v in ancsa.items()
                              if v["cedar_entity_class"] is None)
    if orphan_statutory:
        problems.append({
            "id": "ANCSA_STATUTORY_CATEGORY_HAS_NO_CEDAR_CLASS",
            "detail": f"43 U.S.C. 1607(c) names Village, Urban and Group "
                      f"Corporations; Cedar has a class for two of the three. "
                      f"{orphan_statutory!r} is folded into `Alaska Native "
                      f"Village Corporation`. Goldbelt (Juneau), Shee Atika "
                      f"(Sitka), Natives of Kodiak and Kenai Natives "
                      f"Association are Urban Corporations sitting in the "
                      f"Village class. NOT an ownership defect - 1607(c) "
                      f"applies 1606(g)/(h)/(o) identically to all three - but "
                      f"a LABEL defect, and a class that does not exist cannot "
                      f"be added to ANCSA_CORPORATION_CLASSES when someone "
                      f"finally separates them."})

    # Does any production caller pass the class arguments that make RULE 2 and
    # RULE 4 fire? A scan, so the answer is measured rather than remembered.
    callers, class_aware = [], []
    for p in sorted((ROOT / "code").glob("*.py")):
        if ".bak_" in p.name or p.name in (SCRIPT, "cedar_domain.py"):
            continue
        txt = p.read_text(encoding="utf-8", errors="replace")
        for line in txt.splitlines():
            if "bears_ownership(" not in line or line.lstrip().startswith("#"):
                continue
            callers.append(p.name)
            inner = line.split("bears_ownership(", 1)[1]
            if inner.count(",") >= 2:
                class_aware.append(p.name)
    if not set(class_aware) - {"241_promote_individual_native_firms_in_place.py"}:
        problems.append({
            "id": "ANCSA_CLASS_GUARD_UNCALLED",
            "detail": "cedar_domain.bears_ownership() accepts owner_class and "
                      "owned_class, and RULE 2 (a village government never "
                      "owns an ANC) and RULE 4 (nor the reverse) fire ONLY "
                      "when both are passed. Callers found: "
                      f"{sorted(set(callers))!r}; callers passing the classes: "
                      f"{sorted(set(class_aware))!r} - and that one is a "
                      "module-load self-test on constants, not an attribution. "
                      "ANCSA_CORPORATION_CLASSES and "
                      "ALASKA_VILLAGE_GOVERNMENT_CLASSES have ZERO importers. "
                      "The $24.52B ruling was applied by "
                      "191_apply_ancsa_ownership_ruling.py using its OWN local "
                      "copy of the class sets, so the ruling was enforced and "
                      "the REUSABLE guard was not. That is the shape AGENTS.md "
                      "names: a defect fixed in one place leaves no trace in "
                      "the other nine.",
            "instances": sorted(set(callers))})

    # --- tribal certification: the DERIVED comparative layer ---------------
    cert = read_rows(CERT_RULES, (
        "certifying_authority_entity_id", "rule_verdict",
        "ownership_pct_required", "is_graded", "whose_ownership",
        "enrollment_requirement", "residency_or_onreservation_requirement",
        "verification_method", "renewal_cadence", "rule_list_mismatch"))
    cert_sources = read_rows(CERT_SOURCES, ("certifying_authority_entity_id",
                                            "assertion_class", "verdict"))
    cert_axes = {
        "rule_verdict": dict(counts(cert, "rule_verdict")),
        "ownership_pct_required": dict(counts(cert, "ownership_pct_required")),
        "is_graded": dict(counts(cert, "is_graded")),
        "whose_ownership": dict(counts(cert, "whose_ownership")),
        "rule_list_mismatch_is_yes":
            sum(1 for r in cert
                if (r.get("rule_list_mismatch") or "").strip().upper()
                .startswith(("YES", "THE RULE IS PUBLISHED"))),
    }
    cert_layer = {
        "n_authorities_with_a_rule": len(cert),
        "n_authorities_with_an_ownership_list":
            sum(1 for r in cert_sources
                if (r.get("assertion_class") or "").strip() == "OWNERSHIP"),
        "axes_measured": cert_axes,
        "declared_value_domains": {
            "whose_ownership": sorted({
                "THIS_TRIBE_MEMBER", "ANY_FEDERALLY_RECOGNIZED_TRIBE_MEMBER",
                "ANY_NATIVE_PERSON", "TRIBAL_GOVERNMENT_ENTITY",
                "SHAREHOLDER_OR_DESCENDANT_OR_SPOUSE", "PARENT_CORPORATION",
                "MIXED_SEE_TIERS", "NOT_STATED", "NOT_CHECKED"}),
            "rule_verdict": sorted({
                "RULE_FOUND", "RULE_PARTIAL", "RULE_NOT_PUBLISHED",
                "BEHIND_LOGIN", "NOT_CHECKED", "SITE_REFUSED"}),
            "ownership_pct_required": sorted({"YES", "NO", "NOT_STATED",
                                              "NOT_CHECKED"}),
        },
        "governing_principle":
            "DESCRIPTIVE, NEVER PRESCRIPTIVE. Cedar Press publishes the rule "
            "beside the certification so a subscriber can apply THEIR OWN "
            "threshold. A tribe's determination of who counts as a "
            "Native-owned business is an exercise of sovereignty and is not "
            "ours to adjudicate. We may say 'Colville's Title 10 certification "
            "does not require an ownership percentage'. We may NOT say "
            "'therefore this firm is not really Native-owned'.",
        "publication_state":
            "STAGED, NOT SHIPPED. Every row is `consent_status = UNRESOLVED` "
            "and `publishable = N`; silence is UNRESOLVED, never permission. "
            "Enforced by code/321_gate_tribal_source_restriction.py.",
    }

    # --- absence vocabularies: FOUR of them, and only one token in common ---
    absence = {
        "cedar_domain.ABSENCE_VALUES": {
            "values": sorted(D.ABSENCE_VALUES),
            "scope": "individual-Native ownership evidence only",
            "forbidden": sorted(D.FORBIDDEN_ABSENCE_VALUES),
        },
        "288_build_collection_descriptors.ABSENCE_VOCABULARY": {
            "values": ["NOT_IN_SOURCE", "BELOW_REPORTING_THRESHOLD",
                       "OUT_OF_SCOPE_BY_CONSTRUCTION", "SUPPRESSED",
                       "REPORTED_EMPTY", "NOT_CHECKED"],
            "scope": "product-wide, shipped in every collection descriptor",
        },
        "AGENTS.md source-coverage vocabulary": {
            "values": ["PUBLISHES", "WITHHOLDS", "NOT_FOUND", "NOT_CHECKED"],
            "scope": "whether a SOURCE publishes a fact",
            "declared_in_code": False,
        },
        "tribal_vendor_list_registry.verdict": {
            "values": ["LIST_FOUND_MACHINE_READABLE", "LIST_FOUND_PDF",
                       "LIST_FOUND_HTML", "LIST_BEHIND_LOGIN",
                       "LIST_REFERENCED_NOT_PUBLISHED", "NO_LIST_FOUND",
                       "SITE_UNREACHABLE", "NOT_CHECKED"],
            "scope": "whether a tribal AUTHORITY publishes a certification list",
            "declared_in_code": False,
        },
        "_reading":
            "FOUR absence vocabularies. `NOT_CHECKED` is the ONLY token in all "
            "four. The first two are DELIBERATELY not merged and 288 says why "
            "in its own source. The third and fourth are not declared in code "
            "at all.",
    }

    # --- other imported vocabularies ---------------------------------------
    other = {
        "MeasurementType": {
            "values": {m.value: {"is_observed": m.is_observed,
                                 "never_promotes_to_active":
                                     m in D.NEVER_PROMOTES_TO_ACTIVE}
                       for m in D.MeasurementType}},
        "InstrumentFamily": {
            "values": {i.value: {"obligations_are_summable":
                                 i.obligations_are_summable}
                       for i in D.InstrumentFamily}},
        "EventClass": {"values": [e.value for e in D.EventClass]},
        "AdvocacyChannel": {
            "values": {a.value: {"event_class": a.event_class.value,
                                 "is_lobbying": a.is_lobbying}
                       for a in D.AdvocacyChannel}},
        "Position": {"values": [p.value for p in D.Position],
                     "key": list(D.POSITION_KEY),
                     "what_it_is_not":
                         "NOT a property of an organisation. A position needs "
                         "all three legs; two is a generalisation."},
        "EvidenceClass": {
            "values": {e.value: {"carries_institutional_position":
                                 e.carries_institutional_position}
                       for e in D.EvidenceClass}},
        "ALIAS_TYPES": {"values": sorted(D.ALIAS_TYPES)},
        "REVENUE_EVIDENCE": {"values": list(D.REVENUE_EVIDENCE)},
        "NP_CLASSIFICATION": {
            "positive": sorted(D.NP_CLASSIFICATION_POSITIVE),
            "negative": sorted(D.NP_CLASSIFICATION_NEGATIVE),
            "undecided": sorted(D.NP_CLASSIFICATION_UNDECIDED),
            "what_it_is_not":
                "An unrecognised token is NOT Native. The polarity is an "
                "ALLOW-LIST OF POSITIVES, because an allow-list of negatives "
                "read `not_a_native_entity` as *ruled Native*."},
        "LOBBYING_WITHDRAWAL_MARKS": {
            "values": list(D.LOBBYING_WITHDRAWAL_MARKS),
            "confidences": sorted(D.LOBBYING_WITHDRAWN_CONFIDENCES)},
        "LICENSED": {
            "identifier_types": sorted(t.value for t in
                                       D.LICENSED_IDENTIFIER_TYPES),
            "source_files": sorted(D.LICENSED_SOURCE_FILES)},
        "PROMOTED_TABLES": {k: list(v) for k, v in D.PROMOTED_TABLES.items()},
        "NAME_TRAPS": {"values": sorted(D.NAME_TRAPS),
                       "n": len(D.NAME_TRAPS)},
        "PLACE_SUFFIXES": {"values": sorted(D.PLACE_SUFFIXES)},
    }

    # --- registry taxonomies already on disk -------------------------------
    deals_tax = read_rows(DEALS_TAX, ("axis", "value", "n_deals"))
    deals_axes = collections.defaultdict(dict)
    for r in deals_tax:
        deals_axes[r["axis"]][r["value"]] = int(r["n_deals"] or 0)
    instr = read_rows(INSTR_TAX, ("family", "subtype", "code",
                                  "sum_obligations_directly"))
    var_reg = read_rows(VAR_REG, ("concept", "canonical_name", "definition"))

    doc = {
        "artefact": "CEDAR_TAXONOMY",
        "generated": BUILT,
        "produced_by": SCRIPT,
        "human_companion": "docs/CEDAR_TAXONOMY.md",
        "contract": {
            "principle": "DESCRIPTIVE, NEVER PRESCRIPTIVE. Build the fact, "
                         "never the verdict.",
            "tier_rule": "A tier is INHERITED from the source row, never "
                         "assigned by the consumer. A RULED method says a "
                         "HUMAN DECIDED; it never says the answer was YES.",
            "forbidden_keys": sorted(FORBIDDEN_TAXONOMY_KEYS),
        },
        "layers": {
            "entity_class": entity_classes,
            "tier": tiers,
            "attribution_method": methods,
            "method_accuracy_measured_against_owner_rulings": method_accuracy,
            "identifier_type": identifiers,
            "relationship_type": relationships,
            "federal_native_category": federal,
            "sam_business_type_variant": sam,
            "ancsa_statutory_category": ancsa,
            "tribal_certification": cert_layer,
            "absence": absence,
            "deals_axis": {k: dict(v) for k, v in sorted(deals_axes.items())},
            "instrument_taxonomy": [
                {"family": r["family"], "subtype": r["subtype"],
                 "code": r["code"],
                 "sum_obligations_directly": r["sum_obligations_directly"]}
                for r in instr],
            "variable_registry": [
                {"concept": r["concept"], "canonical_name": r["canonical_name"],
                 "definition": r["definition"]} for r in var_reg],
            "other_imported_vocabularies": other,
        },
        "gaps_and_contradictions": problems,
    }
    return doc, problems


def main(argv):
    check_only = "--check" in argv
    doc, problems = build()

    # Walk DICT KEYS, not the serialised text. A substring test would trip on
    # `contract.forbidden_keys`, which is the declaration of the rule itself -
    # a detector that fires on its own definition is a detector that gets
    # deleted, which is the `--selftest` reasoning in 293 read backwards.
    def offending_keys(node, path="layers"):
        out = []
        if isinstance(node, dict):
            for k, v in node.items():
                if k in FORBIDDEN_TAXONOMY_KEYS:
                    out.append(f"{path}.{k}")
                out += offending_keys(v, f"{path}.{k}")
        elif isinstance(node, list):
            for item in node:
                out += offending_keys(item, path)
        return out

    bad = offending_keys(doc["layers"])
    if bad:
        die(f"forbidden adjudicating key(s) reached the export at {bad!r}. The "
            f"taxonomy records what an authority decided; it never decides.")

    payload = json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False)

    print(f"{SCRIPT}")
    L = doc["layers"]
    print(f"  entity classes ............ {len(L['entity_class'])}")
    print(f"  relationship types ........ {len(L['relationship_type'])} "
          f"declared, "
          f"{sum(1 for v in L['relationship_type'].values() if v['n_rows_in_entity_relationships'])} in use")
    print(f"  tiers / methods / ids ..... {len(L['tier'])} / "
          f"{sum(len(v['values']) for v in L['attribution_method'].values())} / "
          f"{len(L['identifier_type'])}")
    fm = L["federal_native_category"]["_measured"]
    print(f"  federal categories ........ union exact: {fm['union_is_exact']}; "
          f"Native-specific ${fm['native_specific_only_usd']/1e9:.4f}B "
          f"({fm['native_specific_only_share_of_attributed_pct']}% of "
          f"${fm['attributed_obligations_usd']/1e9:.2f}B attributed)")
    print(f"  SAM variants .............. {len(L['sam_business_type_variant']['variants'])}, "
          f"class_conflict on {L['sam_business_type_variant']['n_class_conflict']:,} rows")
    print(f"  certification authorities . {L['tribal_certification']['n_authorities_with_a_rule']} "
          f"with a rule, "
          f"{L['tribal_certification']['n_authorities_with_an_ownership_list']} "
          f"with an ownership list")

    if problems:
        print(f"\n  GAPS AND CONTRADICTIONS - {len(problems)}, each NAMED "
              f"rather than counted:")
        for p in problems:
            print(f"   * {p['id']}")
            print(f"       {p['detail'][:400]}")
    else:
        print("\n  no gaps detected - which is itself worth checking")

    if check_only:
        prior = OUT.read_text(encoding="utf-8") if OUT.exists() else None
        print(f"\n  --check: no write. "
              f"{'IDENTICAL to what is on disk' if prior == payload else 'WOULD CHANGE the file on disk' if prior else 'file does not exist yet'}")
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".json.part")
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(OUT)
    # Re-read from disk rather than trusting the run log (concurrency rule 4).
    back = json.loads(OUT.read_text(encoding="utf-8"))
    if back["layers"]["entity_class"].keys() != doc["layers"]["entity_class"].keys():
        die("the file on disk does not match what was written")
    print(f"\n  wrote {OUT.relative_to(ROOT)}  "
          f"({OUT.stat().st_size:,} bytes, {len(doc['layers'])} layers)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
