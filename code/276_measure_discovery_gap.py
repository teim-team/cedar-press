#!/usr/bin/env python3
"""
Cedar Press - 276: MEASURE THE DISCOVERY GAP.

READ-ONLY. Zero network requests. Writes exactly one new file,
`docs/DISCOVERY_GAP.json`, and prints a report. It touches no table in
`data/clean/` and imports nothing that rebuilds one.

THE QUESTION
------------
An identifier-seeded pull can never discover an entity we do not already know.
That is not a bug in any one script; it is the defining property of the
selection. `docs/PULL_DISCIPLINE.md` now states the doctrine - a targeted pull
selects on `TYPE_FILTER OR KNOWN_IDENTIFIER` and records which leg fired in
`population_basis`. This script measures what the second leg would cost us if
it were the ONLY leg:

    How many entities does a TYPE FILTER find that our IDENTIFIER LIST
    would have missed?

`docs/CICD_BENCHMARK.md` UNDERCOUNT-01..03 answers the mirror question - the
flag-side blind spot, $140.00B / 57.2% / 195 of 498 entities that Cedar
attributes by hand and no flag ever sees. This is the other side of the same
seam and it has never been sized.

WHY IT MATTERS RIGHT NOW
------------------------
All 209,495 FY2023-FY2026 prime rows are `attributed_flag = 1`
(`CICD_BENCHMARK.md` INTERNAL-02). That is not a quality result. Those years
were pulled FILTERED to the ledger's own UEIs, so a Native firm the ledger has
never seen is absent from them ENTIRELY. The unattributed reconciliation
backlog is structurally FY2000-2022 because the recent years contain no
unknowns - nobody looked for any.

THREE MEASUREMENTS, THREE SOURCES ALREADY ON DISK
-------------------------------------------------
A. ASSISTANCE - the only place both legs already ran, by construction.
   `code/115_pull_assistance_archive.py` kept every row under a UNION of
   `recipient_type` (business_types_code in I/J/K) and `ledger_uei`, and
   stamped `population_basis` on each. Entity-level leg membership is
   therefore directly computable. FY2007-FY2026, 20 years.

   TRAP, and the reason this reads the RAW PER-FY EXTRACTS and not the clean
   table: 115's merge pass BACK-STAMPS `population_basis = 'recipient_type'`
   onto every pre-existing row that carries no value (115, line ~940). Those
   rows are the FY2008-2023 API-route spine and NEVER HAD A LEDGER LEG
   EVALUATED. In the clean file they are indistinguishable from rows the type
   filter genuinely selected, and counting them manufactures a type-filter
   share out of a default. `data/raw/usaspending_archive_2026-08-07/
   assistance_filtered/FY####_assistance_filtered.csv` holds only rows that
   went through both legs, so that is what is measured.

   Note the published counts in `docs/ASSISTANCE_ARCHIVE_PULL_LOG.md` lines
   123-128 (495,985 / 96,191 / 12,950 / 3,293) are STALE - the live clean file
   reads 502,082 / 122,933 / 61,062 / 15,878 over 701,955 rows.
   `docs/EDITORIAL_PIPELINE.md` line 696 already flags this. This script
   recomputes and never quotes them.

B. PRIME - the type-filter leg exists on disk and nobody has used it as one.
   `Data Request 4-5-2023 File 1.csv` is HigherGov's FLAG-AT-AWARD extract.
   Siken, verbatim (docs/PRE2007_SPENDING_SOURCES.md Part 2): *"every
   transaction from FPDS where they flagged the contract as Tribal Owned,
   Alaskan Native, etc"*. It carries the TRUE USAspending business-type
   self-certification columns - `tribally_owned_firm`,
   `indian_tribe_federally_recognized`, `alaskan_native_corporation_owned_firm`,
   `native_hawaiian_organization_owned_firm`, `american_indian_owned_business`,
   `native_american_owned_business`, `us_tribal_government`,
   `housing_authorities_public_tribal`, `tribal_college`, and the two
   servicing-institution flags - which `prime_contracts.csv` does NOT carry.
   `CICD_BENCHMARK.md` UNDERCOUNT-05 says a flag-defined universe cannot
   measure what the flag MISSES. True, and irrelevant here: this measurement
   runs the other way. A flag-defined universe is exactly the right instrument
   for asking what the flag FINDS.

C. File 2 is a THIRD leg - SAM current-registration match, parent or child -
   and it is measured the same way, because it is the closest thing on disk to
   a registration-based discovery sweep.

WHAT A "MISS" MEANS HERE, PRECISELY
-----------------------------------
An entity is counted as MISSED BY THE IDENTIFIER LEG when its UEI is absent
from every tier A/B row of `cedar_identifier_ledger_final.csv`, AND absent
after CAGE resolution through `fpds_uei_cage_map.csv`, AND its declared
ultimate parent UEI is absent too. All three legs of the identifier route are
given to the identifier route before it is called a miss. Tier X is EXCLUDED
from the ledger set on purpose - an X ruling says the entity is not ours, so
finding it again is not discovery.

Being missed does NOT mean the entity is Native. A self-certification is a
self-certification (Goldbelt Raven, an ANC subsidiary, certifies
`alaskanNativeCorporationOwnedFirm = NO`). These are CANDIDATES a sweep would
surface for adjudication, never rows to attribute. The number is a measure of
the SEARCH SURFACE an identifier-only pull cannot see, not a count of missing
Native entities.

D. And the narrowness of `44` is measured while the same files are open:
   `code/114_pull_prime_archive.py` selected on uei OR cage OR parent_uei and
   recorded which in `match_key`; `code/44_pull_contracts_transactions.py`
   selects on UEI alone. The per-FY count of archive rows owed to a non-UEI
   identifier is the size of 44's blind spot.

VOCABULARY ASSERTION (AGENTS.md rule earned 2026-08-26)
--------------------------------------------------------
`code/203` filtered Census-era FAC on the modern vocabulary and printed a
clean, entirely artefactual zero. Every categorical filter below asserts that
its vocabulary intersects the data and RAISES when it does not. A filter
matching nothing is a bug until proven otherwise.

    py -3 code/276_measure_discovery_gap.py            # all stages
    py -3 code/276_measure_discovery_gap.py --stages A,D

Reads  data/clean/cedar_identifier_ledger_final.csv
       data/clean/fpds_uei_cage_map.csv
       data/clean/federal_funding_transactions.csv
       data/raw/esm_hci/ESM/raw/Data Request 4-5-2023 File {1,2}.csv
       data/raw/contracts/usaspending_archive_2026-08-07/filtered/FY*_ledger_rows.csv
Writes docs/DISCOVERY_GAP.json      (new file, nothing else)
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
ESM = CEDAR / "data" / "raw" / "esm_hci" / "ESM" / "raw"
FILTERED = (CEDAR / "data" / "raw" / "contracts"
            / "usaspending_archive_2026-08-07" / "filtered")
OUT = CEDAR / "docs" / "DISCOVERY_GAP.json"

FILE1 = ESM / "Data Request 4-5-2023 File 1.csv"
FILE2 = ESM / "Data Request 4-5-2023 File 2.csv"

# The USAspending contract business-type self-certification family. These are
# the flags CICD's method uses and `prime_contracts.csv` does not carry.
NATIVE_FLAG_COLS = [
    "alaskan_native_corporation_owned_firm",
    "american_indian_owned_business",
    "indian_tribe_federally_recognized",
    "native_hawaiian_organization_owned_firm",
    "tribally_owned_firm",
    "native_american_owned_business",
    "us_tribal_government",
    "housing_authorities_public_tribal",
    "tribal_college",
    "alaskan_native_servicing_institution",
    "native_hawaiian_servicing_institution",
]

# Assistance recipient-type codes = "Indian/Native American Tribal Government".
TRIBAL_BUSINESS_TYPE_CODES = {"I", "J", "K"}

TRUEISH = {"T", "TRUE", "Y", "YES", "1"}
FALSEISH = {"F", "FALSE", "N", "NO", "0", ""}


def log(m):
    print(m, flush=True)


def _num(v):
    try:
        return float(str(v).replace(",", "").replace("$", "").strip() or 0)
    except ValueError:
        return 0.0


def assert_vocabulary(name, observed, expected):
    """A filter matching nothing is a bug until proven otherwise."""
    hit = {v for v in observed if v in expected}
    if not hit:
        raise SystemExit(
            f"VOCABULARY ASSERTION FAILED for {name}: none of the expected "
            f"tokens {sorted(expected)} appear in the data. Observed instead: "
            f"{sorted(observed)[:20]}. Refusing to print a zero that is an "
            f"artefact of the filter (AGENTS.md, code/203 precedent).")
    return hit


# --------------------------------------------------------------------------
# stage 0 - the identifier route, given every leg it has
# --------------------------------------------------------------------------

def load_identifier_route():
    led = CLEAN / "cedar_identifier_ledger_final.csv"
    ueis_ab, cages_ab, ueis_x = set(), set(), set()
    ueis_c, cages_c = set(), set()
    tiers = defaultdict(int)
    idtypes = defaultdict(int)
    with open(led, encoding="utf-8-sig", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            it = (r.get("identifier_type") or "").strip().upper()
            idv = (r.get("identifier") or "").strip().upper()
            tier = (r.get("confidence_tier") or "").strip().upper()
            idtypes[it] += 1
            tiers[tier] += 1
            if not idv:
                continue
            if it == "UEI":
                if tier in ("A", "B"):
                    ueis_ab.add(idv)
                elif tier == "C":
                    ueis_c.add(idv)
                elif tier == "X":
                    ueis_x.add(idv)
            elif it == "CAGE" and tier in ("A", "B"):
                cages_ab.add(idv)
            elif it == "CAGE" and tier == "C":
                cages_c.add(idv)

    assert_vocabulary("ledger identifier_type", set(idtypes), {"UEI", "CAGE"})
    assert_vocabulary("ledger confidence_tier", set(tiers), {"A", "B"})

    # CAGE -> UEI, offline, from the derived crosswalk. This is exactly the leg
    # code/44 does not have and code/114 does.
    cage_ueis, cage_ueis_c = set(), set()
    xw = CLEAN / "fpds_uei_cage_map.csv"
    if xw.exists():
        with open(xw, encoding="utf-8-sig", errors="replace", newline="") as fh:
            for r in csv.DictReader(fh):
                c = (r.get("cage_code") or "").strip().upper()
                u = (r.get("uei") or "").strip().upper()
                if not (c and u):
                    continue
                if c in cages_ab:
                    cage_ueis.add(u)
                elif c in cages_c:
                    cage_ueis_c.add(u)

    known = (ueis_ab | cage_ueis) - ueis_x
    # SENSITIVITY. Tier C is 12,382 ledger rows the project holds an identifier
    # for and does not publish. It is not in any puller's selection set today
    # (44 pulls A|B|X; 114 matched A|B|X), so the headline gap is measured
    # against A/B. But "we already know this entity" is arguably true of a
    # tier-C row too, and if the answer moved a lot on that choice the finding
    # would be an artefact of it. It is reported so the reader can see it does not.
    known_incl_c = (ueis_ab | ueis_c | cage_ueis | cage_ueis_c) - ueis_x
    log(f"identifier route: {len(ueis_ab):,} tier-A/B UEIs "
        f"+ {len(cage_ueis):,} resolved from {len(cages_ab):,} tier-A/B CAGEs "
        f"- {len(ueis_x):,} tier-X = {len(known):,} known UEIs "
        f"({len(known_incl_c):,} if tier C is counted as known)")
    return {
        "known_uei_incl_tier_C": len(known_incl_c),
        "tier_c_uei": len(ueis_c),
        "tier_c_cage": len(cages_c),
        "ledger_rows_by_tier": dict(tiers),
        "ledger_rows_by_identifier_type": dict(idtypes),
        "tier_ab_uei": len(ueis_ab),
        "tier_ab_cage": len(cages_ab),
        "uei_resolved_from_cage": len(cage_ueis),
        "tier_x_uei_excluded": len(ueis_x),
        "known_uei_total": len(known),
    }, known, known_incl_c


# --------------------------------------------------------------------------
# stage A - assistance: both legs already ran, per row
# --------------------------------------------------------------------------

TYPE_LEG_BASES = {"recipient_type", "both"}
# `ledger_uei_withheld` IS the identifier leg firing. 115's state-agreement
# guard withheld the ATTRIBUTION on those rows, not the SELECTION - the row is
# in the file because the ledger identifier matched. Treating it as anything
# else would understate what the identifier leg finds and flatter this
# measurement in the direction it is arguing.
ID_LEG_BASES = {"ledger_uei", "ledger_uei_withheld", "both"}


def stage_a(known=frozenset(), known_incl_c=frozenset()):
    src = (CEDAR / "data" / "raw" / "usaspending_archive_2026-08-07"
           / "assistance_filtered")
    files = sorted(src.glob("FY*_assistance_filtered.csv"))
    if not files:
        raise SystemExit(f"STAGE A: no per-FY extracts under {src}. An absent "
                         f"input reads as an empty source - refusing.")
    legs = defaultdict(lambda: [False, False])
    dollars = defaultdict(float)
    rows = defaultdict(int)
    basis_seen = defaultdict(int)
    legacy_rows = 0

    for p in files:
        with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
            rd = csv.DictReader(fh)
            if "population_basis" not in (rd.fieldnames or []):
                raise SystemExit(f"STAGE A: {p.name} has no population_basis "
                                 f"column (AGENTS.md rule 8).")
            for r in rd:
                basis = (r.get("population_basis") or "").strip()
                basis_seen[basis] += 1
                fy = (r.get("fiscal_year") or "").strip() \
                    or p.stem.split("_")[0].replace("FY", "")
                uei = (r.get("recipient_uei") or "").strip().upper()
                obl = _num(r.get("obligated_usd"))
                rows[(fy, basis)] += 1
                dollars[(fy, basis)] += obl
                if not uei:
                    continue
                t = legs[(fy, uei)]
                if basis in TYPE_LEG_BASES:
                    t[0] = True
                if basis in ID_LEG_BASES:
                    t[1] = True

    assert_vocabulary("assistance population_basis", set(basis_seen),
                      {"recipient_type", "ledger_uei", "both"})

    per_fy = {}
    tot = {"type_only": set(), "id_only": set(), "both": set()}
    for (fy, uei), (t, i) in legs.items():
        k = "both" if (t and i) else ("type_only" if t else "id_only")
        per_fy.setdefault(fy, {"type_only": 0, "id_only": 0, "both": 0})
        per_fy[fy][k] += 1
        tot[k].add(uei)

    for fy in per_fy:
        d = per_fy[fy]
        id_leg_found = d["both"] + d["id_only"]
        d["entities_total"] = d["type_only"] + d["id_only"] + d["both"]
        d["rows_by_population_basis"] = {
            b: rows[(f2, b)] for (f2, b) in rows if f2 == fy}
        d["usd_by_population_basis"] = {
            b: round(dollars[(f2, b)], 2) for (f2, b) in dollars if f2 == fy}
        d["usd_type_leg_only_rows"] = round(
            dollars.get((fy, "recipient_type"), 0), 2)
        d["pct_of_universe_invisible_to_identifier_leg"] = (
            round(100.0 * d["type_only"] / d["entities_total"], 2)
            if d["entities_total"] else None)
        d["multiplier_type_filter_over_identifier_only"] = (
            round(d["entities_total"] / id_leg_found, 3)
            if id_leg_found else None)

    overall_known = len(tot["both"] | tot["id_only"])
    overall_all = len(tot["type_only"] | tot["id_only"] | tot["both"])

    # THE DECOMPOSITION THAT CHANGES WHAT THE NUMBER MEANS.
    # An entity outside the pull set is not necessarily an entity we have
    # never seen. Tier C holds 9,335 UEI rows, 9,320 of them
    # `attribution_method = unmatched` and every one sourced from
    # master_tribal_entity_registry.csv - identifiers HARVESTED and never
    # adjudicated to an entity. Those are a REVIEW backlog, not a discovery
    # problem: a sweep would re-find them and learn nothing. Only a UEI absent
    # from the ledger ENTIRELY is something no Cedar file has ever recorded.
    type_only = tot["type_only"]
    stranded = {u for u in type_only if u in known_incl_c and u not in known}
    novel = {u for u in type_only if u not in known_incl_c}
    already = len(type_only) - len(stranded) - len(novel)
    res = {
        "source": str(src),
        "files_read": len(files),
        "restricted_to": "115's per-FY archive extracts, the only rows that "
                         "went through BOTH legs",
        "excluded_and_why":
            "the FY2008-2023 API-route spine in the clean table is NOT read "
            "here: 115's merge back-stamps population_basis='recipient_type' "
            "on rows that never had a ledger leg evaluated, and counting them "
            "manufactures a type-filter share out of a default",
        "population_basis_rows": dict(basis_seen),
        "leg_definitions": {"type_leg": sorted(TYPE_LEG_BASES),
                            "identifier_leg": sorted(ID_LEG_BASES)},
        "by_fiscal_year": dict(sorted(per_fy.items())),
        "distinct_entities_all_years": {
            "type_filter_only": len(tot["type_only"]),
            "identifier_only": len(tot["id_only"]),
            "both": len(tot["both"]),
            "union": overall_all,
            "identifier_leg_alone_would_have_found": overall_known,
            "pct_invisible_to_identifier_leg":
                round(100.0 * len(tot["type_only"]) / overall_all, 2)
                if overall_all else None,
            "multiplier_union_over_identifier_only":
                round(overall_all / overall_known, 3) if overall_known else None,
        },
        "decomposition_of_the_type_filter_only_entities": {
            "total": len(type_only),
            "on_file_at_tier_C_unadjudicated_a_REVIEW_backlog": len(stranded),
            "absent_from_the_ledger_entirely_TRUE_DISCOVERY": len(novel),
            "in_the_pull_set_but_the_ledger_leg_did_not_fire_on_these_rows":
                already,
            "note": "the middle row is the number a discovery sweep would "
                    "surface and a reviewer would already recognise; the "
                    "TRUE_DISCOVERY row is what no Cedar file has ever held",
        },
    }
    return res


# --------------------------------------------------------------------------
# stages B / C - prime: a flag-defined extract vs the identifier route
# --------------------------------------------------------------------------

def stage_flagfile(path, label, known, known_incl_c=None):
    """Stream a HigherGov extract; split its entities by whether the
    identifier route already knows them."""
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.reader(fh)
        head = next(rd)
        ix = {}
        for i, c in enumerate(head):
            ix.setdefault(c, i)          # first occurrence wins; File 1 has dups
        need = ["uei_id", "federal_action_obligation", "action_date_fiscal_year",
                "ultimate_parent_uei", "cage_code"]
        for c in need:
            if c not in ix:
                raise SystemExit(f"{label}: required column {c!r} absent. "
                                 f"An absent column reads as an empty source "
                                 f"(AGENTS.md rule 8) - refusing to continue.")
        flagix = [(c, ix[c]) for c in NATIVE_FLAG_COLS if c in ix]
        if not flagix:
            raise SystemExit(f"{label}: none of the business-type flag columns "
                             f"are present. Refusing to print a zero.")

        seen_flag_tokens = set()
        n = 0
        # uei -> [flagged_any, dollars, parent_uei_seen]
        ent = defaultdict(lambda: [False, 0.0, set()])
        by_fy_flagged = defaultdict(lambda: defaultdict(lambda: [False, 0.0]))
        for row in rd:
            n += 1
            if len(row) <= ix["uei_id"]:
                continue
            uei = (row[ix["uei_id"]] or "").strip().upper()
            if not uei:
                continue
            obl = _num(row[ix["federal_action_obligation"]]
                       if len(row) > ix["federal_action_obligation"] else 0)
            fy = (row[ix["action_date_fiscal_year"]] or "").strip() \
                if len(row) > ix["action_date_fiscal_year"] else ""
            flagged = False
            for c, i in flagix:
                if len(row) <= i:
                    continue
                v = (row[i] or "").strip().upper()
                seen_flag_tokens.add(v)
                if v in TRUEISH:
                    flagged = True
            e = ent[uei]
            e[0] = e[0] or flagged
            e[1] += obl
            p = (row[ix["ultimate_parent_uei"]] or "").strip().upper() \
                if len(row) > ix["ultimate_parent_uei"] else ""
            if p:
                e[2].add(p)
            if flagged and fy:
                f = by_fy_flagged[fy][uei]
                f[0] = True
                f[1] += obl

        assert_vocabulary(f"{label} business-type flags", seen_flag_tokens,
                          TRUEISH)

    flagged_ueis = {u for u, v in ent.items() if v[0]}
    # give the identifier route its parent leg too, before calling it a miss
    missed = set()
    missed_via_parent_rescued = 0
    for u in flagged_ueis:
        if u in known:
            continue
        if ent[u][2] & known:
            missed_via_parent_rescued += 1
            continue
        missed.add(u)

    usd_missed = round(sum(ent[u][1] for u in missed), 2)
    usd_flagged = round(sum(ent[u][1] for u in flagged_ueis), 2)

    missed_c = None
    if known_incl_c is not None:
        missed_c = len({u for u in flagged_ueis
                        if u not in known_incl_c
                        and not (ent[u][2] & known_incl_c)})

    per_fy = {}
    for fy, d in by_fy_flagged.items():
        fl = set(d)
        mi = {u for u in fl if u not in known and not (ent[u][2] & known)}
        per_fy[fy] = {
            "flagged_entities": len(fl),
            "flagged_entities_unknown_to_identifier_route": len(mi),
            "pct_unknown": round(100.0 * len(mi) / len(fl), 2) if fl else None,
            "usd_on_flagged_rows": round(sum(d[u][1] for u in fl), 2),
            "usd_on_flagged_rows_unknown_entities":
                round(sum(d[u][1] for u in mi), 2),
        }

    log(f"  {label}: {n:,} rows, {len(ent):,} distinct UEIs, "
        f"{len(flagged_ueis):,} flagged Native, {len(missed):,} of those "
        f"UNKNOWN to the identifier route")
    return {
        "source": str(path),
        "rows_streamed": n,
        "distinct_uei": len(ent),
        "flag_columns_used": [c for c, _ in flagix],
        "entities_carrying_a_native_business_type_flag": len(flagged_ueis),
        "of_those_already_known_to_identifier_route":
            len(flagged_ueis) - len(missed) - missed_via_parent_rescued,
        "of_those_rescued_only_by_the_parent_uei_leg": missed_via_parent_rescued,
        "THE_DISCOVERY_GAP_entities_the_flag_finds_that_the_identifier_"
        "list_would_have_missed": len(missed),
        "pct_of_flagged_entities_unknown":
            round(100.0 * len(missed) / len(flagged_ueis), 2)
            if flagged_ueis else None,
        "SENSITIVITY_gap_if_tier_C_counted_as_known": missed_c,
        "usd_on_flagged_entities": usd_flagged,
        "usd_on_flagged_entities_unknown_to_identifier_route": usd_missed,
        "by_fiscal_year": dict(sorted(per_fy.items())),
        "caveat": "A self-certification is not a determination. These are "
                  "CANDIDATES for adjudication, never rows to attribute. "
                  "Goldbelt Raven, an ANC subsidiary, certifies "
                  "alaskanNativeCorporationOwnedFirm = NO.",
    }, missed, ent


# --------------------------------------------------------------------------
# stage D - how narrow is 44?
# --------------------------------------------------------------------------

def stage_d():
    if not FILTERED.exists():
        raise SystemExit(f"STAGE D: {FILTERED} absent.")
    per_fy = {}
    tokens = set()
    for p in sorted(FILTERED.glob("FY*_ledger_rows.csv")):
        fy = p.stem.split("_")[0].replace("FY", "")
        c = defaultdict(int)
        ueis = defaultdict(set)
        with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
            rd = csv.DictReader(fh)
            if "match_key" not in (rd.fieldnames or []):
                raise SystemExit(f"STAGE D: {p.name} has no match_key column.")
            for r in rd:
                k = (r.get("match_key") or "").strip()
                tokens.add(k)
                c[k] += 1
                ueis[k].add((r.get("recipient_uei") or "").strip().upper())
        tot = sum(c.values())
        # 44 selects on ledger rows with identifier_type == 'UEI' at ANY tier
        # (A, B and X - it pulls X so an excluded UEI's rows can be counted and
        # excluded rather than silently missing). So the legs 44 reproduces are
        # recipient_uei and excluded_tier_X. The legs it CANNOT reproduce are
        # cage_code and recipient_parent_uei: the API filters on the RECIPIENT,
        # and neither a CAGE nor a parent's UEI is the recipient's UEI.
        UEI_LEGS = {"recipient_uei", "excluded_tier_X"}
        non_uei = sum(v for k, v in c.items() if k not in UEI_LEGS)
        uei_ents = set()
        non_uei_ents = set()
        for k, s in ueis.items():
            (uei_ents if k in UEI_LEGS else non_uei_ents).update(s)
        per_fy[fy] = {
            "rows_total": tot,
            "rows_by_match_key": dict(sorted(c.items())),
            "rows_a_uei_only_pull_would_lose": non_uei,
            "pct_rows_lost": round(100.0 * non_uei / tot, 2) if tot else None,
            "entities_a_uei_only_pull_would_lose":
                len(non_uei_ents - uei_ents),
        }
    assert_vocabulary("114 match_key", tokens,
                      {"recipient_uei", "cage_code", "recipient_parent_uei"})
    return {"source": str(FILTERED), "by_fiscal_year": dict(sorted(per_fy.items()))}


# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stages", default="A,B,C,D")
    a = ap.parse_args()
    want = {s.strip().upper() for s in a.stages.split(",")}

    res = {"generated": datetime.now(timezone.utc)
           .strftime("%Y-%m-%dT%H:%M:%SZ"),
           "script": "code/276_measure_discovery_gap.py",
           "network_requests": 0}

    log("stage 0: the identifier route")
    res["identifier_route"], known, known_c = load_identifier_route()

    if "A" in want:
        log("stage A: assistance - both legs already ran (population_basis)")
        res["A_assistance_population_basis"] = stage_a(known, known_c)

    if "B" in want:
        log("stage B: prime - HigherGov File 1 (FLAG-AT-AWARD) vs the ledger")
        r, missed1, _ = stage_flagfile(FILE1, "File 1 (flag-at-award)", known,
                                       known_c)
        res["B_prime_flag_at_award"] = r
    if "C" in want:
        log("stage C: prime - HigherGov File 2 (SAM registration match)")
        r2, missed2, _ = stage_flagfile(FILE2, "File 2 (registration match)",
                                        known, known_c)
        res["C_prime_registration_match"] = r2
        if "B" in want:
            res["BC_union"] = {
                "entities_unknown_to_identifier_route_in_either_file":
                    len(missed1 | missed2),
                "in_both_files": len(missed1 & missed2),
            }

    if "D" in want:
        log("stage D: how much does a UEI-ONLY pull lose? (44 vs 114)")
        res["D_uei_only_narrowness"] = stage_d()

    part = OUT.with_suffix(".json.part")
    part.write_text(json.dumps(res, indent=2), encoding="utf-8")
    part.replace(OUT)
    log(f"\nwrote {OUT}")

    # ---- report ----------------------------------------------------------
    log("\n" + "=" * 74)
    log("THE DISCOVERY GAP")
    log("=" * 74)
    if "A" in want:
        d = res["A_assistance_population_basis"]["distinct_entities_all_years"]
        log(f"\nASSISTANCE (archive years, both legs ran per row):")
        log(f"  entities found by the TYPE FILTER ONLY : {d['type_filter_only']:,}")
        log(f"  entities found by the IDENTIFIER ONLY  : {d['identifier_only']:,}")
        log(f"  entities found by BOTH                 : {d['both']:,}")
        log(f"  union                                  : {d['union']:,}")
        log(f"  an identifier-only pull would have found "
            f"{d['identifier_leg_alone_would_have_found']:,} of {d['union']:,} "
            f"-> {d['pct_invisible_to_identifier_leg']}% INVISIBLE")
        dd = res["A_assistance_population_basis"][
            "decomposition_of_the_type_filter_only_entities"]
        log(f"  of the {dd['total']:,} type-filter-only entities: "
            f"{dd['on_file_at_tier_C_unadjudicated_a_REVIEW_backlog']:,} sit "
            f"at tier C unadjudicated (a REVIEW backlog), "
            f"{dd['absent_from_the_ledger_entirely_TRUE_DISCOVERY']:,} are "
            f"absent from the ledger entirely (TRUE DISCOVERY)")
    for key, name in (("B_prime_flag_at_award", "PRIME / flag-at-award"),
                      ("C_prime_registration_match", "PRIME / registration")):
        if key in res:
            r = res[key]
            g = r["THE_DISCOVERY_GAP_entities_the_flag_finds_that_the_"
                  "identifier_list_would_have_missed"]
            log(f"\n{name}:")
            log(f"  entities carrying a Native business-type flag : "
                f"{r['entities_carrying_a_native_business_type_flag']:,}")
            log(f"  UNKNOWN to the identifier route (uei|cage|parent): "
                f"{g:,}  ({r['pct_of_flagged_entities_unknown']}%)")
            log(f"  obligations on those unknown entities         : "
                f"${r['usd_on_flagged_entities_unknown_to_identifier_route']:,.0f}")
    if "D" in want:
        log("\nWHAT A UEI-ONLY PULL LOSES (44 vs 114, per FY):")
        for fy, d in res["D_uei_only_narrowness"]["by_fiscal_year"].items():
            log(f"  FY{fy}: {d['rows_a_uei_only_pull_would_lose']:,} of "
                f"{d['rows_total']:,} rows ({d['pct_rows_lost']}%), "
                f"{d['entities_a_uei_only_pull_would_lose']:,} entities  "
                f"{d['rows_by_match_key']}")


if __name__ == "__main__":
    main()
