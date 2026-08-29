#!/usr/bin/env python3
"""
269 - THE OWNERSHIP-CHAIN RANKING of tribal, ANC and NHO federal prime
contractors.

    py -3 code/269_build_contractor_ranking.py

WHAT IT PRODUCES

    data/clean/contractor_ranking.csv            one row per OPERATING COMPANY,
                                                 carrying its OWNER, the owner's
                                                 CLASS, and the IDENTIFIER that
                                                 establishes the link plus that
                                                 identifier's TIER.
    data/clean/codebook/02h_contractor_ranking.csv   codebook fragment
    docs/codebooks/02h_contractor_ranking.md         the prose fragment
    docs/CONTRACTOR_RANKING_MEASUREMENTS.json    every figure the article quotes,
                                                 each stamped with the mtime of
                                                 the file it was measured from.

SAFETY
------
**READ-ONLY against every input.** Zero network calls. Writes only the four
paths above, each `.part`-then-rename, each backed up first if it exists.
Never runs `01_build_entity_spine.py`, `09_import_rulings.py`,
`41_build_codebooks.py` or `88_build_deals_taxonomy.py`. Idempotent: running it
twice produces the same bytes apart from the build date.

THE FIVE RULES THIS SCRIPT ENFORCES, AND WHY EACH ONE COST SOMETHING
--------------------------------------------------------------------

**1. TIER A ONLY. A tier-B link never publishes alone.**
This is the whole difference between a ranking and a libel. Measured on this
file at build time, the four largest tier-B owner-totals are:

  * `AKNF-INPTBW-00-ARCSLO` (Native Village of Barrow) at $8.75B - whose largest
    "operating companies" are GENERAL DYNAMICS INFORMATION TECHNOLOGY ($3.53B)
    and PERATON GOVERNMENT COMMUNICATIONS ($2.03B). Neither is Native-owned.
  * `TRBF-BLULKE-00` (Blue Lake Rancheria) at $3.66B - of which $3.51B is
    BLUE TECH INC., plus BLUE SPADER, BLUE SKIES FURNITURE and BLUE PACIFIC.
    The token doing the work is "blue".
  * `AKNF-VEAGLE-00-...` (Eagle) at $2.88B - AMERICAN EAGLE PROTECTIVE SERVICES,
    RED EAGLE JV, EAGLE GLOBAL SCIENTIFIC. `eagle` is in `NAME_TRAPS` already.
  * `AKNF-PRBLFC-00` (Pribilof Islands) at $1.06B - Aleut-named firms booked to
    a village government rather than to a corporation.

99%+ of each of those totals is `confidence_tier = B`. Publishing the ranking
off `attributed_flag` alone would have put a $3.5B General Dynamics subsidiary
inside an Alaska Native village's contracting record, at rank 8, in a piece
whose entire subject is that ownership can be resolved correctly.

**2. A TIER IS INHERITED FROM THE LEDGER ROW, NEVER ASSIGNED HERE.**
`prime_contracts.attribution_method` records the JOIN ROUTE (`uei_exact`,
`cage_exact`, `parent_uei`, `ruling_applied`). `confidence_tier` records the
strength of the LINK, and it came from `cedar_identifier_ledger_final.csv`.
An exact UEI match to a tier-B ledger row is a tier-B link: the exactness of the
KEY says nothing about the correctness of the LINK. This script copies the
tier; it never derives one.

**3. `total_obligations` IS THE ONLY SUMMABLE MONEY COLUMN.**
`cedar_domain.SUM_COLUMNS`. `total_award_value` is restated on every transaction
of an award and sums to $5.63T; `total_obligations_real2025` sums to $385.0B.
Asserted at run time against `cedar_domain`, so an edit to that module cannot
silently change what this script sums.

**4. `setaside` MUST BE FORWARD-FILLED TO AWARD LEVEL BEFORE ANY SHARE.**
`docs/ANOMALY_REPORT.md` seam register: *"the archive leaves it blank on ~56% of
rows so it must be forward-filled to award level before any share is computed."*
In the clean file a blank arrives as the literal `None reported`, and
`setaside_reported = 0` on exactly those rows - so `None reported` conflates
*"no set-aside"* with *"this transaction did not carry the field"*. Measured:
`None reported` runs 30.9% of attributed FY2017 rows and 68.3% of FY2023 rows,
which is a reporting step, not a policy change. So the no-set-aside measure is
computed at AWARD level: an award counts as carrying a Native set-aside if ANY
of its transactions does.

**The award key is `(contract_number, awardee_uei)`, matching
`docs/CICD_BENCHMARK.md` `UNDERCOUNT-01` exactly** - a sibling artefact quoting
the same file, and two documents that disagree about their own basis are worse
than either being slightly wrong. On the all-attributed universe this script
reproduces that document to the third decimal: **$140.004B**. Grouping on
`contract_number` alone instead moves it to $129.82B, because a PIID can be
re-used across vendors and across a DUNS-to-UEI migration, and filling a
set-aside across that boundary would spread one award's flag onto another's
money. Both are reported; the compound key is the headline.

The row-level figure is also reported and is the UPPER bound, since it counts
every blank transaction as unflagged.

**5. `reported_native_preference` IS NOT A NATIVE IDENTIFIER.**
Verified at run time: its dollars equal the union of `reported_8a`,
`reported_buy_indian` and `reported_indian_business` to the cent. 8(a) is open
to non-Native disadvantaged firms, so the union is GENEROUS to the flag-based
instrument - which is what makes the undercount a floor rather than an estimate.

PRIVACY AND LICENSING
---------------------
* `awardee_name` here comes from BGOV `master prime file.dta` and the
  USAspending award archive, **not** from a SAM entity extract, so the D&B Open
  Data bulk-dissemination restriction does not attach. Stated per field in
  `docs/codebooks/02f_individual_native_verification.md`
  (`dnb_open_data_attaches`). Any future SAM-sourced row needs its own answer -
  `data/clean/sam_prime_contracts_fy2000_2007.csv` is 100% D&B-marked and is
  NOT an input here.
* This is a ranking of **entity-owned** firms. Individually Native-owned firms
  are a separate and stricter case and are out of scope by construction: the
  owner side is the entity spine, and a sole proprietor is not on it. A
  belt-and-braces personal-name guard still runs over every operating-company
  name (`publishable_operating_name`); a firm failing it keeps its contract
  facts and loses its name and its UEI.

WHAT THIS SCRIPT DOES NOT CLAIM
-------------------------------
It does not claim the tier-A total is the true size of Native federal
contracting. It is the part that is *evidenced to a hand-checked or
independently-corroborated identifier link*. Everything below tier A is real
money that we have not finished proving the owner of. That is a floor twice
over, and both floors are stated in the outputs.
"""
from __future__ import annotations

import csv
import json
import os
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime, date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cedar_domain as dom  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PRIME = ROOT / "data" / "clean" / "prime_contracts.csv"
SPINE = ROOT / "data" / "spine" / "cedar_entity_spine.csv"
LEDGER = ROOT / "data" / "clean" / "cedar_identifier_ledger_final.csv"
#: OPTIONAL authority list. Any UEI this file has already adjudicated as
#: not-nameable stays not-nameable here, whatever our own guard says. A privacy
#: ruling only ever tightens.
PRIVACY_AUTHORITY = ROOT / "data" / "clean" / "individual_native_ownership_verification.csv"

OUT = ROOT / "data" / "clean" / "contractor_ranking.csv"
FRAG_CSV = ROOT / "data" / "clean" / "codebook" / "02h_contractor_ranking.csv"
FRAG_MD = ROOT / "docs" / "codebooks" / "02h_contractor_ranking.md"
MEAS = ROOT / "docs" / "CONTRACTOR_RANKING_MEASUREMENTS.json"

TODAY = date.today().isoformat()
BUILT_BY = "code/269_build_contractor_ranking.py"
DATASET = "02h_contractor_ranking"

csv.field_size_limit(10 ** 9)

# --------------------------------------------------------------------------
# Owner class. The four the piece names, plus the ones that exist and must not
# be silently folded into them.
# --------------------------------------------------------------------------
CLASS_MAP = {
    "Federally recognized tribe": "TRIBE",
    "State-recognized tribe": "STATE_RECOGNIZED_TRIBE",
    "Alaska Native Regional Corporation": "ANC_REGIONAL",
    "Alaska Native Village Corporation": "ANC_VILLAGE",
    "ANCSA Group Corporation": "ANC_GROUP",
    "Native Hawaiian Organization": "NHO",
    # A village GOVERNMENT is not an ANC and never owns one (ANCSA ruling
    # rule 2, `cedar_domain.village_government_owns_an_anc`). It gets its own
    # label so nobody can read it as an ANC row.
    "Federally recognized Alaska Native Village": "ALASKA_NATIVE_VILLAGE_GOVERNMENT",
}

NATIVE_SETASIDE_TOKENS = {"8(a)", "Indian Business", "Buy Indian"}
#: The two that are Native BY DEFINITION. 8(a) is not one of them - it is open
#: to any disadvantaged firm - which is why it is tracked separately.
NATIVE_SPECIFIC_TOKENS = {"Indian Business", "Buy Indian"}

# COPIED VERBATIM from `code/171_build_individual_native_verification.py`
# lines 227-232, and the predicate below is that script's `privacy_class()`.
# Reproduced rather than re-invented so that one project rule about naming a
# private individual has ONE definition. If 171's regex changes, this must be
# re-synced - the alternative is two guards that disagree, and the direction
# they disagree in is a person's name in print.
CORP_SUFFIX_RE = re.compile(
    r"\b(inc|llc|l\.l\.c|corp|corporation|company|co|ltd|lp|llp|plc|group|"
    r"services|systems|enterprises|associates|solutions|holdings|technologies|"
    r"construction|consulting|industries|partners|international|joint venture|jv)\b",
    re.I,
)


def stamp(p: Path) -> str:
    return datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds")


def f(v) -> float:
    try:
        return float(v or 0)
    except ValueError:
        return 0.0


def privacy_class(name: str) -> str:
    """`code/171_build_individual_native_verification.py::privacy_class`, verbatim.

    A sole proprietorship's legal name is frequently a private person's name,
    and SAM's public search resolves a UEI to it. Deliberately CONSERVATIVE: a
    two-or-three token name with no corporate form is treated as possibly
    personal even when it plainly is not - 'JVYS' and 'YAKAMA POWER' both fail
    it - because the cost of the two errors is not symmetric. The row keeps
    every contract fact either way; it loses only the name and the UEI.
    """
    n = (name or "").strip()
    if not n:
        return "UNKNOWN"
    if CORP_SUFFIX_RE.search(n):
        return "CORPORATE_FORM_PRESENT"
    toks = [t for t in re.split(r"[\s,]+", n) if t]
    if len(toks) <= 3:
        return "POSSIBLE_PERSONAL_NAME"
    return "NO_CORPORATE_FORM"


def publishable_name(name: str) -> str:
    return "N" if privacy_class(name) in ("POSSIBLE_PERSONAL_NAME", "UNKNOWN") else "Y"


def main() -> int:
    # --- Rule 3, asserted rather than remembered --------------------------
    assert "total_obligations" in dom.SUM_COLUMNS, "SUM_COLUMNS moved"
    assert "total_award_value" in dom.MAX_PER_AWARD_COLUMNS, "MAX column moved"
    for p in (PRIME, SPINE, LEDGER):
        if not p.exists():
            print(f"MISSING INPUT: {p}", file=sys.stderr)
            return 2

    vintages = {str(p.relative_to(ROOT)).replace("\\", "/"): stamp(p)
                for p in (PRIME, SPINE, LEDGER)}
    print("=== 269 contractor ranking ===")
    for k, v in vintages.items():
        print(f"  input {k}  mtime {v}")

    # --- spine -------------------------------------------------------------
    spine = {}
    for r in csv.DictReader(SPINE.open(encoding="utf-8", newline="")):
        spine[r["tribe_id"]] = r
    print(f"[1] spine {len(spine)} entities")

    # --- ledger, keyed (type, identifier) ---------------------------------
    ledger = {}
    for r in csv.DictReader(LEDGER.open(encoding="utf-8", newline="")):
        ident = (r["identifier"] or "").strip()
        if not ident:
            continue
        k = (r["identifier_type"].strip().upper(), ident.upper())
        prev = ledger.get(k)
        # Prefer the tier-A row where a key repeats; within a tier prefer a
        # RULED method. Never invent a tier - just choose which recorded row
        # describes the link.
        if prev is None:
            ledger[k] = r
        else:
            def score(x):
                return (x["confidence_tier"] == "A",
                        dom.is_ruling(x["attribution_method"]))
            if score(r) > score(prev):
                ledger[k] = r
    print(f"[2] ledger {len(ledger)} distinct (type, identifier) keys")

    never_name = set()
    if PRIVACY_AUTHORITY.exists():
        for r in csv.DictReader(PRIVACY_AUTHORITY.open(encoding="utf-8-sig",
                                                       newline="")):
            if (r.get("publishable_entity_name") or "").strip() == "N":
                u = (r.get("awardee_uei") or "").strip().upper()
                if u:
                    never_name.add(u)
        vintages[str(PRIVACY_AUTHORITY.relative_to(ROOT)).replace("\\", "/")] = \
            stamp(PRIVACY_AUTHORITY)
    print(f"[2b] privacy authority: {len(never_name)} UEIs already ruled "
          f"not-nameable")

    # --- one streaming pass over prime ------------------------------------
    tot_all = 0.0
    n_rows = 0
    att_rows = 0
    att_usd = 0.0
    a_rows = 0
    a_usd = 0.0
    pref_usd = 0.0
    union_usd = 0.0
    fy_rows_all = Counter()
    fy_att_rows = Counter()
    a_fy_usd = Counter()

    # tier-A firm grain: (tribe_id, firm_key)
    firm_usd = defaultdict(float)
    firm_rows = Counter()
    firm_name = {}
    firm_uei = {}
    firm_fy_min = {}
    firm_fy_max = {}
    firm_flag_usd = defaultdict(float)
    firm_8a_usd = defaultdict(float)
    firm_specific_usd = defaultdict(float)
    firm_route_usd = defaultdict(lambda: defaultdict(float))
    firm_link_usd = defaultdict(lambda: defaultdict(float))

    # award-level forward fill, tier-A universe.
    # KEY = (contract_number, awardee_uei) - see rule 4 in the docstring.
    contract_usd = defaultdict(float)
    contract_flag = set()
    contract_entity = {}
    contract_rows = Counter()
    # robustness variant: contract_number alone
    piid_usd = defaultdict(float)
    piid_flag = set()

    # all-attributed comparison universe (any tier) - reported, never ranked
    att_firm_keys = set()
    att_firm_flag_keys = set()
    att_firm_usd = defaultdict(float)
    att_ent_usd = defaultdict(float)
    att_ent_flag = set()
    att_rowlevel_noflag_usd = 0.0
    att_rowlevel_noflag_rows = 0
    att_contract_usd = defaultdict(float)
    att_contract_flag = set()

    with PRIME.open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            n_rows += 1
            o = f(r["total_obligations"])
            tot_all += o
            fy = r["fiscal_year"]
            fy_rows_all[fy] += 1
            if r["reported_native_preference"] == "1":
                pref_usd += o
            if (r["reported_8a"] == "1" or r["reported_buy_indian"] == "1"
                    or r["reported_indian_business"] == "1"):
                union_usd += o
            if r["attributed_flag"] != "1":
                continue

            att_rows += 1
            att_usd += o
            fy_att_rows[fy] += 1
            tid = r["tribe_id"]
            uei = (r["awardee_uei"] or "").strip().upper()
            cage = (r["cage_code"] or "").strip().upper()
            fkey = uei or ("NAME:" + (r["awardee_name"] or "").strip().upper())
            setaside = r["setaside"]
            flagged = setaside in NATIVE_SETASIDE_TOKENS
            cnum = (r["contract_number"], uei)
            piid = r["contract_number"]

            att_ent_usd[tid] += o
            att_firm_usd[(tid, fkey)] += o
            att_firm_keys.add((tid, fkey))
            att_contract_usd[cnum] += o
            if flagged:
                att_ent_flag.add(tid)
                att_firm_flag_keys.add((tid, fkey))
                att_contract_flag.add(cnum)
            else:
                att_rowlevel_noflag_usd += o
                att_rowlevel_noflag_rows += 1

            # ---- rule 1: tier A only from here down ----
            if r["confidence_tier"] != "A":
                continue
            a_rows += 1
            a_usd += o
            a_fy_usd[fy] += o
            k = (tid, fkey)
            firm_usd[k] += o
            firm_rows[k] += 1
            firm_name.setdefault(k, r["awardee_name"])
            firm_uei.setdefault(k, uei)
            y = int(fy) if fy.isdigit() else None
            if y:
                firm_fy_min[k] = min(firm_fy_min.get(k, y), y)
                firm_fy_max[k] = max(firm_fy_max.get(k, y), y)
            if flagged:
                firm_flag_usd[k] += o
            if setaside == "8(a)":
                firm_8a_usd[k] += o
            if setaside in NATIVE_SPECIFIC_TOKENS:
                firm_specific_usd[k] += o

            route = r["attribution_method"]
            firm_route_usd[k][route] += o
            if route == "uei_exact" and uei:
                firm_link_usd[k][("UEI", uei)] += o
            elif route == "cage_exact" and cage:
                firm_link_usd[k][("CAGE", cage)] += o
            elif route == "parent_uei" and (r["parent_uei"] or "").strip():
                firm_link_usd[k][("UEI", r["parent_uei"].strip().upper())] += o
            elif uei:
                firm_link_usd[k][("UEI", uei)] += o

            contract_usd[cnum] += o
            contract_rows[cnum] += 1
            contract_entity.setdefault(cnum, tid)
            piid_usd[piid] += o
            if flagged:
                contract_flag.add(cnum)
                piid_flag.add(piid)

    print(f"[3] prime {n_rows:,} rows  ${tot_all/1e9:,.2f}B")
    print(f"    attributed {att_rows:,} rows  ${att_usd/1e9:,.2f}B "
          f"({100*att_usd/tot_all:.1f}%)  {len(att_ent_usd)} entities")
    print(f"    tier A     {a_rows:,} rows  ${a_usd/1e9:,.2f}B "
          f"({100*a_usd/att_usd:.1f}% of attributed)  "
          f"{len({t for t, _ in firm_usd})} entities  "
          f"{len(firm_usd)} operating companies")

    # --- rule 5, verified rather than asserted ----------------------------
    pref_is_union = abs(pref_usd - union_usd) < 0.01
    print(f"[4] reported_native_preference == union(8a, buy_indian, "
          f"indian_business): {pref_is_union} "
          f"(${pref_usd/1e9:,.4f}B vs ${union_usd/1e9:,.4f}B)")

    # --- rule 4: award-level forward fill ---------------------------------
    a_noflag_contract_usd = sum(v for c, v in contract_usd.items()
                                if c not in contract_flag)
    a_noflag_contract_rows = sum(contract_rows[c] for c in contract_usd
                                 if c not in contract_flag)
    a_noflag_piid_usd = sum(v for c, v in piid_usd.items() if c not in piid_flag)
    a_rowlevel_noflag_usd = a_usd - sum(firm_flag_usd.values())
    att_noflag_contract_usd = sum(v for c, v in att_contract_usd.items()
                                  if c not in att_contract_flag)

    ent_firms = defaultdict(list)
    for (tid, fk) in firm_usd:
        ent_firms[tid].append(fk)

    ent_usd = defaultdict(float)
    ent_rows = Counter()
    ent_flag_usd = defaultdict(float)
    ent_8a = defaultdict(float)
    ent_specific = defaultdict(float)
    ent_ids = defaultdict(set)
    ent_fy_min, ent_fy_max = {}, {}
    for k, v in firm_usd.items():
        tid = k[0]
        ent_usd[tid] += v
        ent_rows[tid] += firm_rows[k]
        ent_flag_usd[tid] += firm_flag_usd.get(k, 0.0)
        ent_8a[tid] += firm_8a_usd.get(k, 0.0)
        ent_specific[tid] += firm_specific_usd.get(k, 0.0)
        for lk in firm_link_usd[k]:
            ent_ids[tid].add(lk)
        if k in firm_fy_min:
            ent_fy_min[tid] = min(ent_fy_min.get(tid, 9999), firm_fy_min[k])
            ent_fy_max[tid] = max(ent_fy_max.get(tid, 0), firm_fy_max[k])

    ent_noflag_contract = defaultdict(float)
    for c, v in contract_usd.items():
        if c not in contract_flag:
            ent_noflag_contract[contract_entity[c]] += v

    order = sorted(ent_usd, key=lambda t: -ent_usd[t])
    rank = {t: i + 1 for i, t in enumerate(order)}

    # --- firm-level invisibility to a flag-based discoverer ---------------
    a_firms = set(firm_usd)
    a_flag_firms = {k for k in firm_usd if firm_flag_usd.get(k, 0.0) > 0}
    a_invisible = a_firms - a_flag_firms
    a_invisible_usd = sum(firm_usd[k] for k in a_invisible)
    att_invisible = att_firm_keys - att_firm_flag_keys
    att_invisible_usd = sum(att_firm_usd[k] for k in att_invisible)
    a_ents_no_flag = [t for t in ent_usd if ent_flag_usd.get(t, 0.0) == 0]
    att_ents_no_flag = [t for t in att_ent_usd if t not in att_ent_flag]

    # --- many-UEI structure inside the publishable set --------------------
    ent_uei_count = {t: len({i for (ty, i) in ent_ids[t] if ty == "UEI"})
                     for t in ent_usd}
    multi = {t: n for t, n in ent_uei_count.items() if n >= 2}

    # --- write the ranking -------------------------------------------------
    cols = [
        "owner_rank", "owner_entity_id", "owner_name", "owner_class",
        "owner_entity_class_as_recorded", "owner_state",
        "owner_obligations_usd", "owner_share_of_publishable_pct",
        "owner_n_operating_companies", "owner_n_identifiers",
        "owner_n_uei_links", "owner_first_fy", "owner_last_fy",
        "owner_native_setaside_usd", "owner_8a_usd",
        "owner_native_specific_setaside_usd",
        "owner_no_setaside_usd_award_level", "owner_no_setaside_share_pct",
        "operating_company_name", "operating_company_uei",
        "publishable_operating_name", "privacy_class",
        "link_identifier_type", "link_identifier", "link_tier",
        "link_join_route", "link_ledger_method", "link_is_ruling",
        "link_tier_rationale", "link_ledger_source_file", "link_evidence_url",
        "link_legal_business_name_internal_only",
        "firm_obligations_usd", "firm_transaction_rows",
        "firm_first_fy", "firm_last_fy",
        "firm_native_setaside_usd", "firm_carries_any_native_setaside",
        "firm_8a_usd",
        "measured_from", "source_vintage", "built_date", "built_by",
    ]
    rows_out = []
    for tid in order:
        s = spine.get(tid, {})
        raw_class = s.get("entity_class", "")
        owner_name = (s.get("fr_official_name") or "").strip() or \
            (s.get("canonical_name") or "").strip() or tid
        for fk in sorted(ent_firms[tid], key=lambda k: -firm_usd[(tid, k)]):
            k = (tid, fk)
            links = firm_link_usd[k]
            if links:
                (lt, li) = max(links, key=lambda x: links[x])
            else:
                lt, li = "", ""
            led = ledger.get((lt, li), {})
            route = max(firm_route_usd[k], key=lambda x: firm_route_usd[k][x]) \
                if firm_route_usd[k] else ""
            nm = firm_name.get(k, "")
            pc = privacy_class(nm)
            pub = publishable_name(nm)
            if firm_uei.get(k, "") in never_name:
                pub, pc = "N", "RULED_NOT_NAMEABLE_BY_02f"
            rows_out.append({
                "owner_rank": rank[tid],
                "owner_entity_id": tid,
                "owner_name": owner_name,
                "owner_class": CLASS_MAP.get(raw_class, "OTHER_NATIVE_INSTITUTION"),
                "owner_entity_class_as_recorded": raw_class,
                "owner_state": s.get("state", ""),
                "owner_obligations_usd": round(ent_usd[tid], 2),
                "owner_share_of_publishable_pct": round(100 * ent_usd[tid] / a_usd, 4),
                "owner_n_operating_companies": len(ent_firms[tid]),
                "owner_n_identifiers": len(ent_ids[tid]),
                "owner_n_uei_links": ent_uei_count[tid],
                "owner_first_fy": ent_fy_min.get(tid, ""),
                "owner_last_fy": ent_fy_max.get(tid, ""),
                "owner_native_setaside_usd": round(ent_flag_usd[tid], 2),
                "owner_8a_usd": round(ent_8a[tid], 2),
                "owner_native_specific_setaside_usd": round(ent_specific[tid], 2),
                "owner_no_setaside_usd_award_level":
                    round(ent_noflag_contract.get(tid, 0.0), 2),
                "owner_no_setaside_share_pct":
                    round(100 * ent_noflag_contract.get(tid, 0.0) / ent_usd[tid], 2)
                    if ent_usd[tid] else "",
                "operating_company_name": nm if pub == "Y" else "WITHHELD_POSSIBLE_PERSONAL_NAME",
                "operating_company_uei": (firm_uei.get(k, "") if pub == "Y" else ""),
                "publishable_operating_name": pub,
                "privacy_class": pc,
                "link_identifier_type": lt,
                "link_identifier": li if pub == "Y" else "",
                "link_tier": "A",
                "link_join_route": route,
                "link_ledger_method": led.get("attribution_method", "NOT_IN_LEDGER"),
                "link_is_ruling": "Y" if dom.is_ruling(led.get("attribution_method")) else "N",
                "link_tier_rationale": led.get("tier_rationale", ""),
                "link_ledger_source_file": led.get("source_file", ""),
                "link_evidence_url": led.get("evidence_url", ""),
                "link_legal_business_name_internal_only": led.get("legal_business_name", ""),
                "firm_obligations_usd": round(firm_usd[k], 2),
                "firm_transaction_rows": firm_rows[k],
                "firm_first_fy": firm_fy_min.get(k, ""),
                "firm_last_fy": firm_fy_max.get(k, ""),
                "firm_native_setaside_usd": round(firm_flag_usd.get(k, 0.0), 2),
                "firm_carries_any_native_setaside":
                    "Y" if firm_flag_usd.get(k, 0.0) > 0 else "N",
                "firm_8a_usd": round(firm_8a_usd.get(k, 0.0), 2),
                "measured_from": "data/clean/prime_contracts.csv",
                "source_vintage": vintages["data/clean/prime_contracts.csv"],
                "built_date": TODAY,
                "built_by": BUILT_BY,
            })

    write_csv(OUT, cols, rows_out)
    print(f"[5] wrote {OUT.relative_to(ROOT)}  {len(rows_out):,} rows")

    withheld = [r for r in rows_out if r["publishable_operating_name"] == "N"]
    withheld_usd = sum(r["firm_obligations_usd"] for r in withheld)
    print(f"    personal-name guard withheld {len(withheld)} of {len(rows_out)} "
          f"operating-company names (${withheld_usd/1e9:,.2f}B of contract "
          f"facts still publish)")

    # --- measurements block ------------------------------------------------
    top = []
    for tid in order[:25]:
        s = spine.get(tid, {})
        firms = sorted(ent_firms[tid], key=lambda k: -firm_usd[(tid, k)])[:4]
        top.append({
            "rank": rank[tid],
            "entity_id": tid,
            "name": (s.get("fr_official_name") or s.get("canonical_name") or tid).strip(),
            "class": CLASS_MAP.get(s.get("entity_class", ""), "OTHER_NATIVE_INSTITUTION"),
            "state": s.get("state", ""),
            "obligations_usd": round(ent_usd[tid], 2),
            "n_operating_companies": len(ent_firms[tid]),
            "n_uei_links": ent_uei_count[tid],
            "fy_span": f"{ent_fy_min.get(tid,'')}-{ent_fy_max.get(tid,'')}",
            "no_setaside_share_pct":
                round(100 * ent_noflag_contract.get(tid, 0.0) / ent_usd[tid], 1)
                if ent_usd[tid] else None,
            "top_operating_companies": [
                {"name": (firm_name[(tid, k)]
                          if publishable_name(firm_name[(tid, k)]) == "Y"
                          and firm_uei.get((tid, k), "") not in never_name
                          else "WITHHELD_POSSIBLE_PERSONAL_NAME"),
                 "usd": round(firm_usd[(tid, k)], 2),
                 "flagged": firm_flag_usd.get((tid, k), 0.0) > 0}
                for k in firms],
        })

    meas = {
        "built": TODAY,
        "built_by": BUILT_BY,
        "release_written_against": "prime_contracts.csv @ "
                                   + vintages["data/clean/prime_contracts.csv"],
        "input_vintages": vintages,
        "universe": {
            "prime_rows": n_rows,
            "prime_obligations_usd": round(tot_all, 2),
            "attributed_rows": att_rows,
            "attributed_obligations_usd": round(att_usd, 2),
            "attributed_share_pct": round(100 * att_usd / tot_all, 2),
            "attributed_entities": len(att_ent_usd),
            "attributed_operating_companies": len(att_firm_keys),
            "tierA_rows": a_rows,
            "tierA_obligations_usd": round(a_usd, 2),
            "tierA_share_of_attributed_pct": round(100 * a_usd / att_usd, 2),
            "tierA_share_of_all_pct": round(100 * a_usd / tot_all, 2),
            "tierA_entities": len(ent_usd),
            "tierA_operating_companies": len(firm_usd),
            "note": "TIER A ONLY publishes. See rule 1 in the module docstring.",
        },
        "attribution_rate_is_a_blend": {
            "fy2023_2026_rows": sum(fy_rows_all[y] for y in ("2023", "2024", "2025", "2026")),
            "fy2023_2026_attributed_rows": sum(fy_att_rows[y] for y in ("2023", "2024", "2025", "2026")),
            "fy2023_2026_attributed_pct": round(
                100 * sum(fy_att_rows[y] for y in ("2023", "2024", "2025", "2026"))
                / sum(fy_rows_all[y] for y in ("2023", "2024", "2025", "2026")), 2),
            "why": "identifier-seeded archive backfill: those years entered the "
                   "clean file already filtered to Cedar's identifier "
                   "population, so 100% is BY CONSTRUCTION and the headline "
                   "attribution rate is a blend over two differently-built "
                   "populations.",
        },
        "setaside_instrument": {
            "reported_native_preference_equals_union": pref_is_union,
            "reported_native_preference_usd": round(pref_usd, 2),
            "union_8a_buyindian_indianbusiness_usd": round(union_usd, 2),
            "note": "the flag family INCLUDES 8(a), which is open to non-Native "
                    "disadvantaged firms. The instrument is therefore generous, "
                    "which is what makes the undercount a FLOOR.",
        },
        "undercount_tierA": {
            "row_level_no_setaside_usd": round(a_rowlevel_noflag_usd, 2),
            "row_level_no_setaside_pct": round(100 * a_rowlevel_noflag_usd / a_usd, 2),
            "award_level_no_setaside_usd": round(a_noflag_contract_usd, 2),
            "award_level_no_setaside_pct": round(100 * a_noflag_contract_usd / a_usd, 2),
            "award_level_no_setaside_rows": a_noflag_contract_rows,
            "award_key": "(contract_number, awardee_uei) - matches "
                         "docs/CICD_BENCHMARK.md UNDERCOUNT-01",
            "robustness_piid_only_no_setaside_usd": round(a_noflag_piid_usd, 2),
            "robustness_piid_only_no_setaside_pct":
                round(100 * a_noflag_piid_usd / a_usd, 2),
            "awards_total": len(contract_usd),
            "awards_never_flagged": len(contract_usd) - len(contract_flag),
            "firms_total": len(a_firms),
            "firms_never_flagged": len(a_invisible),
            "firms_never_flagged_pct": round(100 * len(a_invisible) / len(a_firms), 1),
            "firms_never_flagged_usd": round(a_invisible_usd, 2),
            "entities_never_flagged": len(a_ents_no_flag),
            "entities_total": len(ent_usd),
            "headline_measure": "award_level_no_setaside_usd",
            "why_award_level": "the setaside column is blank on the majority of "
                               "archive-era transactions and arrives as 'None "
                               "reported'; forward-filling to the contract is "
                               "required before any share is computed "
                               "(docs/ANOMALY_REPORT.md seam register).",
        },
        "undercount_all_attributed_any_tier": {
            "row_level_no_setaside_usd": round(att_rowlevel_noflag_usd, 2),
            "row_level_no_setaside_rows": att_rowlevel_noflag_rows,
            "row_level_no_setaside_pct": round(100 * att_rowlevel_noflag_usd / att_usd, 2),
            "award_level_no_setaside_usd": round(att_noflag_contract_usd, 2),
            "award_level_no_setaside_pct": round(100 * att_noflag_contract_usd / att_usd, 2),
            "firms_total": len(att_firm_keys),
            "firms_never_flagged": len(att_invisible),
            "firms_never_flagged_pct": round(100 * len(att_invisible) / len(att_firm_keys), 1),
            "firms_never_flagged_usd": round(att_invisible_usd, 2),
            "entities_never_flagged": len(att_ents_no_flag),
            "entities_total": len(att_ent_usd),
            "note": "REPORTED, NOT RANKED. Includes tier-B links that never "
                    "publish alone.",
        },
        "native_specific_setasides_tierA": {
            "usd": round(sum(ent_specific.values()), 2),
            "pct_of_tierA": round(100 * sum(ent_specific.values()) / a_usd, 3),
            "definition": "setaside in {Indian Business, Buy Indian}. Excludes "
                          "8(a), which is not Native-specific.",
        },
        "one_owner_many_identifiers_tierA": {
            "entities_with_2plus_uei_links": len(multi),
            "entities_total": len(ent_usd),
            "max_uei_links_on_one_entity": max(ent_uei_count.values()) if ent_uei_count else 0,
            "total_uei_links": sum(ent_uei_count.values()),
            "note": "the publishable, attributed version of the 8(a) "
                    "nine-year-term mechanism. The 267-name-cluster / $13.19B "
                    "figure in docs/EDITORIAL_PIPELINE.md C3 is measured on "
                    "UNATTRIBUTED rows and is a question, not a finding.",
        },
        "privacy_guard": {
            "rows_name_withheld": len(withheld),
            "rows_total": len(rows_out),
            "usd_on_withheld_rows": round(withheld_usd, 2),
            "rule": "code/171_build_individual_native_verification.py::"
                    "privacy_class, verbatim, plus any UEI already ruled "
                    "not-nameable in individual_native_ownership_verification.csv",
            "note": "contract facts publish on a withheld row; the name and "
                    "the UEI do not. The rule is blunt on purpose.",
        },
        "class_totals_tierA": {},
        "top25": top,
        "tierA_by_fiscal_year_usd": {y: round(a_fy_usd[y], 2)
                                     for y in sorted(a_fy_usd)},
        "fy2025_last_complete_year": {
            "tierA_usd": round(a_fy_usd.get("2025", 0.0), 2),
            "note": "FY2025 is the last publishable complete fiscal year for "
                    "this dataset. FY2026 is cut at action_date 2026-07-03 - a "
                    "nine-month partial - and every FY2026 figure is "
                    "year-to-date.",
        },
        "fy2026_partial": {
            "tierA_usd": round(a_fy_usd.get("2026", 0.0), 2),
            "share_of_tierA_pct": round(100 * a_fy_usd.get("2026", 0.0) / a_usd, 2),
            "cut_at": "action_date 2026-07-03",
        },
        "final_vs_will_move": {
            "FINAL": ["FY2000-FY2025 obligations as recorded at this vintage "
                      "(FPDS restates retroactively up to five years, so even "
                      "closed years drift slightly)"],
            "WILL_MOVE": ["every FY2026 figure - the prime cut is at "
                          "action_date 2026-07-03, a nine-month partial; these "
                          "only ever grow",
                          "the tier-A total - it grows as links are ruled, "
                          "never shrinks except by a negative ruling"],
        },
    }
    cls_usd = defaultdict(float)
    cls_n = Counter()
    for tid in ent_usd:
        c = CLASS_MAP.get(spine.get(tid, {}).get("entity_class", ""),
                          "OTHER_NATIVE_INSTITUTION")
        cls_usd[c] += ent_usd[tid]
        cls_n[c] += 1
    meas["class_totals_tierA"] = {
        c: {"entities": cls_n[c], "usd": round(cls_usd[c], 2),
            "pct": round(100 * cls_usd[c] / a_usd, 2)}
        for c in sorted(cls_usd, key=lambda x: -cls_usd[x])
    }

    backup(MEAS)
    tmp = MEAS.with_suffix(".json.part")
    tmp.write_text(json.dumps(meas, indent=1), encoding="utf-8")
    tmp.replace(MEAS)
    print(f"[6] wrote {MEAS.relative_to(ROOT)}")

    write_codebook(cols, len(rows_out), vintages)
    print(f"[7] wrote {FRAG_CSV.relative_to(ROOT)} and {FRAG_MD.relative_to(ROOT)}")

    print()
    print("=== TOP 15, TIER A ONLY ===")
    for t in top[:15]:
        print(f"{t['rank']:>3}  {t['name'][:46]:<46} {t['class']:<34} "
              f"${t['obligations_usd']/1e9:>7.3f}B  "
              f"{t['n_operating_companies']:>3} firms  "
              f"{t['no_setaside_share_pct']:>5}% no set-aside")
    print()
    print(f"tier A total ${a_usd/1e9:,.2f}B  ·  award-level no-set-aside "
          f"${a_noflag_contract_usd/1e9:,.2f}B "
          f"({100*a_noflag_contract_usd/a_usd:.1f}%)  ·  "
          f"{len(a_invisible)} of {len(a_firms)} firms "
          f"({100*len(a_invisible)/len(a_firms):.1f}%, "
          f"${a_invisible_usd/1e9:,.2f}B) never carry a flag")
    return 0


def backup(p: Path) -> None:
    if p.exists():
        shutil.copy2(p, p.with_name(p.name + f".bak_{TODAY}_pre269"))


def write_csv(path: Path, cols, rows) -> None:
    backup(path)
    tmp = path.with_name(path.name + ".part")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    tmp.replace(path)


VARDOC = {
 "owner_rank": "Rank of the OWNING entity by tier-A prime obligations, FY2000-FY2026. Dense over entities; repeated on every operating-company row belonging to that owner. Recomputed every build - never join on it.",
 "owner_entity_id": "The owning entity's Cedar identifier. Prefix and token follow the NEID scheme published by the Center for Indian Country Development, Federal Reserve Bank of Minneapolis (Native Entity Connector Crosswalk, Feb 2026), which seeded this spine. `ANVC-`/`ANRC-` are Cedar extensions to that scheme.",
 "owner_name": "`fr_official_name` from the entity spine where present - the name as it appears in the Federal Register list of federally recognized tribes - otherwise `canonical_name`. Several `canonical_name` values are truncated stems ('Houlton', 'Blue Lake') and must not be printed.",
 "owner_class": "TRIBE · STATE_RECOGNIZED_TRIBE · ANC_REGIONAL · ANC_VILLAGE · ANC_GROUP · NHO · ALASKA_NATIVE_VILLAGE_GOVERNMENT · OTHER_NATIVE_INSTITUTION. A village GOVERNMENT is never folded into ANC_VILLAGE: under the ANCSA ownership ruling (docs/ANCSA_OWNERSHIP_RULING.md) a village government never owns an ANC, in either direction, and the two populations name each other by statute.",
 "owner_entity_class_as_recorded": "The spine's `entity_class` verbatim, so the mapping above is auditable rather than lossy.",
 "owner_state": "Spine state.",
 "owner_obligations_usd": "Sum of `total_obligations` over this owner's TIER-A attributed prime transactions, FY2000-FY2026, nominal dollars. `total_obligations` is the only summable money column (cedar_domain.SUM_COLUMNS); `total_award_value` is restated per transaction and sums to $5.63T.",
 "owner_share_of_publishable_pct": "`owner_obligations_usd` as a percent of the tier-A publishable total. NOT a share of all Native federal contracting.",
 "owner_n_operating_companies": "Distinct operating companies (by UEI, or by name where no UEI is recorded) carrying tier-A links to this owner.",
 "owner_n_identifiers": "Distinct (identifier_type, identifier) pairs establishing this owner's tier-A links.",
 "owner_n_uei_links": "Of those, how many are UEIs. Two or more is the visible signature of the SBA 8(a) nine-year non-renewable term: a continuing programme requires a new legal entity with a new UEI.",
 "owner_first_fy": "Earliest fiscal year with a tier-A transaction.",
 "owner_last_fy": "Latest fiscal year with a tier-A transaction. FY2026 is a NINE-MONTH PARTIAL - the prime cut is at action_date 2026-07-03.",
 "owner_native_setaside_usd": "Tier-A dollars on transactions whose `setaside` is 8(a), Indian Business or Buy Indian. Transaction level, not forward-filled - use the award-level column for shares.",
 "owner_8a_usd": "Tier-A dollars on `setaside = 8(a)` alone. 8(a) is open to non-Native disadvantaged firms and is NOT evidence of Native ownership.",
 "owner_native_specific_setaside_usd": "Tier-A dollars on the two Native-BY-DEFINITION set-asides only: Indian Business and Buy Indian.",
 "owner_no_setaside_usd_award_level": "Tier-A dollars on AWARDS none of whose transactions carries any Native set-aside. Award key is `(contract_number, awardee_uei)`, matching `docs/CICD_BENCHMARK.md` UNDERCOUNT-01. Award level because `setaside` is blank on the majority of archive-era transactions and arrives as the literal 'None reported' - see the seam register in docs/ANOMALY_REPORT.md. This is the conservative measure and the one the article quotes.",
 "owner_no_setaside_share_pct": "The award-level column over `owner_obligations_usd`.",
 "operating_company_name": "`awardee_name` as recorded on the prime transactions. From BGOV `master prime file.dta` and the USAspending award archive, NOT a SAM entity extract, so the D&B Open Data bulk restriction does not attach. `WITHHELD_POSSIBLE_PERSONAL_NAME` where the personal-name guard fired.",
 "operating_company_uei": "SAM Unique Entity ID. Blank where the name was withheld, and blank where the transactions carry no UEI.",
 "publishable_operating_name": "`N` where the name may be a private individual's. Contract facts still publish on an `N` row; the name and the UEI do not. Deliberately over-inclusive: SAM's public search resolves a UEI to a legal name, and a sole proprietor's legal name is a private person's name.",
 "privacy_class": "`CORPORATE_FORM_PRESENT` · `POSSIBLE_PERSONAL_NAME` · `NO_CORPORATE_FORM` · `UNKNOWN` · `RULED_NOT_NAMEABLE_BY_02f`. The first four use `code/171_build_individual_native_verification.py::privacy_class` VERBATIM so that one project rule about naming a private individual has one definition; the fifth means the UEI was already adjudicated not-nameable in `individual_native_ownership_verification.csv` and a privacy ruling only ever tightens. The rule is blunt on purpose and it withholds names that are plainly corporate (`JVYS`, `YAKAMA POWER`); a reviewer clears those one at a time, never by widening the rule.",
 "link_identifier_type": "UEI or CAGE - which identifier carries the majority of this firm's tier-A dollars into the owner.",
 "link_identifier": "The identifier value itself. Blank on a withheld row.",
 "link_tier": "Always A on this file. Tier is INHERITED from the ledger row that made the link and is never assigned here. A tier-B link never publishes alone; nothing below tier A appears in this table at all.",
 "link_join_route": "How prime_contracts reached the ledger: `uei_exact`, `cage_exact`, `parent_uei` or `ruling_applied`. This is the JOIN ROUTE, not the strength of the link - an exact UEI match to a tier-B ledger row is still a tier-B link.",
 "link_ledger_method": "The ledger's own `attribution_method`: how a human or a pass established that this identifier belongs to this owner. `hand`, `bgov_manual`, `elijah_ruling`, `web_verified`, `agent_research_two_leg`, `subsidiary_lookup`. `NOT_IN_LEDGER` where the identifier could not be re-found at this vintage.",
 "link_is_ruling": "`Y` where `link_ledger_method` is in `cedar_domain.RULED_METHODS` - a permanent human decision that only a new ruling reverses. `N` marks a link that is tier A on evidence but has not been ruled.",
 "link_tier_rationale": "The ledger's written reason for the tier, verbatim.",
 "link_ledger_source_file": "Which upstream file the link came from.",
 "link_evidence_url": "Evidence URL where the ledger carries one. Frequently blank on `hand` and `bgov_manual` rows, whose evidence is the crosswalk itself.",
 "link_legal_business_name_internal_only": "The ledger's `legal_business_name`. Retained for audit. Treat as internal: it is the one field on this table whose provenance varies by ledger source.",
 "firm_obligations_usd": "This operating company's tier-A prime obligations.",
 "firm_transaction_rows": "Tier-A transaction rows behind that figure. The grain of prime_contracts is contract x fiscal year x vendor, not one row per award.",
 "firm_first_fy": "Earliest tier-A fiscal year for this firm. Together with `firm_last_fy` this is what makes a successor-firm sequence visible.",
 "firm_last_fy": "Latest tier-A fiscal year for this firm.",
 "firm_native_setaside_usd": "Transaction-level Native set-aside dollars for this firm.",
 "firm_carries_any_native_setaside": "`N` means a flag-based method would never have found this firm at all. This is the column the undercount finding is built on.",
 "firm_8a_usd": "8(a) dollars for this firm.",
 "measured_from": "The file every dollar on this row was summed from.",
 "source_vintage": "mtime of that file at build time. Several agents write it concurrently; a count without a vintage is a claim about a file that no longer exists.",
 "built_date": "Build date.",
 "built_by": "This script.",
}


def write_codebook(cols, nrows: int, vintages) -> None:
    backup(FRAG_CSV)
    head = ["dataset", "variable", "type", "units", "pct_filled", "n_rows",
            "published", "access_tier", "description", "generated"]
    typ = {}
    for c in cols:
        if c.endswith("_usd") or c.endswith("_pct"):
            typ[c] = ("numeric", "usd" if c.endswith("_usd") else "percent")
        elif c in ("owner_rank", "owner_n_operating_companies",
                   "owner_n_identifiers", "owner_n_uei_links",
                   "firm_transaction_rows"):
            typ[c] = ("integer", "count")
        elif c.endswith("_fy"):
            typ[c] = ("integer", "fiscal year")
        elif c in ("built_date",):
            typ[c] = ("date", "date")
        else:
            typ[c] = ("text", "code")
    rows = [{
        "dataset": DATASET, "variable": c, "type": typ[c][0], "units": typ[c][1],
        "pct_filled": "", "n_rows": nrows,
        "published": 0 if c == "link_legal_business_name_internal_only" else 1,
        "access_tier": "internal" if c == "link_legal_business_name_internal_only" else "public",
        "description": VARDOC[c], "generated": TODAY,
    } for c in cols]
    tmp = FRAG_CSV.with_name(FRAG_CSV.name + ".part")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=head)
        w.writeheader()
        w.writerows(rows)
    tmp.replace(FRAG_CSV)

    backup(FRAG_MD)
    md = [
        f"# 02h — `contractor_ranking.csv`",
        "",
        f"*Codebook fragment. Written by `{BUILT_BY}` on {TODAY}. "
        "`data/clean/codebook_master.csv` is deliberately NOT touched — "
        "reconciling master from fragments is `cedar_register_codebook.py`'s "
        "job and its owner's timing.*",
        "",
        "## What a row is",
        "",
        "**One OPERATING COMPANY, with the entity that owns it, that entity's "
        "class, and the identifier that establishes the link.** An owner with "
        "nine subsidiaries occupies nine rows carrying one `owner_rank`.",
        "",
        "## The four things to know before quoting a number off this file",
        "",
        "1. **Tier A only.** Nothing below tier A is in this table. The tier is "
        "inherited from `cedar_identifier_ledger_final.csv`, never assigned "
        "here. `attributed_flag = 1` alone would put a $3.53B General Dynamics "
        "subsidiary inside an Alaska Native village government's record at "
        "rank 8 — that is a tier-B name-cluster artefact and it is excluded by "
        "construction.",
        "2. **This is a FLOOR, twice.** Once because tier B is real money whose "
        "owner is not yet proven, and once because the set-aside flags used as "
        "the comparison instrument are generous.",
        "3. **`total_obligations` is the only summable money column.** "
        "`cedar_domain.SUM_COLUMNS`.",
        "4. **FY2026 is a nine-month partial**, cut at `action_date` "
        "2026-07-03. Every FY2026 figure is year-to-date and only ever grows.",
        "",
        "## Provenance",
        "",
        "| input | vintage (mtime at build) |",
        "|---|---|",
    ]
    for k, v in vintages.items():
        md.append(f"| `{k}` | {v} |")
    md += [
        "",
        "Entity identifiers follow the NEID scheme published by the **Center "
        "for Indian Country Development, Federal Reserve Bank of Minneapolis** "
        "(*Native Entity Connector Crosswalk*, February 2026), which seeded "
        "the Cedar Press entity spine. `ANVC-` and `ANRC-` prefixes are Cedar "
        "extensions to that scheme.",
        "",
        "## Variables",
        "",
        "| variable | type | published | description |",
        "|---|---|---|---|",
    ]
    for c in cols:
        pub = "no" if c == "link_legal_business_name_internal_only" else "yes"
        md.append(f"| `{c}` | {typ[c][0]} | {pub} | "
                  + VARDOC[c].replace("|", "\\|") + " |")
    md.append("")
    tmp = FRAG_MD.with_name(FRAG_MD.name + ".part")
    tmp.write_text("\n".join(md), encoding="utf-8")
    tmp.replace(FRAG_MD)


if __name__ == "__main__":
    raise SystemExit(main())
