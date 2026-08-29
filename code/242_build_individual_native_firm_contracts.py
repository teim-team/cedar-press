#!/usr/bin/env python3
r"""
Cedar Press - 242: roll the individually Native-owned firm class's federal
prime contracting up into its OWN totals, and split what publishes from what
does not.

WHY THIS IS A SEPARATE TABLE AND NOT A COLUMN ON `prime_contracts.csv`
-----------------------------------------------------------------------
Two reasons, and the second is the one that matters.

1. `prime_contracts.csv` is the most-rebuilt file in this repo. An in-place
   enricher on a file a full-rebuild stage also writes is the documented
   collision, now on its fourth instance (`09` reverting `50`; `133 build`
   reverting `168`; the partial restore of the FERC docket table). This script
   opens it READ ONLY and writes nothing to it.

2. **`attributed_flag` and the $244.77B attributed total are the flagship
   figure, and this class must never enter them.** Writing 16,910 rows of
   individually Native-owned firms into the attributed pool would raise a
   published number by summing two classes the project has ruled must never be
   summed:

       tribally/ANC owned        7,329 rows / $2.76B
       individually Native-owned 14,029 rows / $0.98B      (first 15 rulings)

   The individual class is LARGER by row count and SMALLER by dollars. Summing
   them moves both numbers in opposite directions from the truth, and it would
   look like a discovery while doing it - the same shape as the set-aside
   definition change that nearly corrupted the 60.9% finding.

   Every tribal, ANC and NHO figure Cedar Press has published is unchanged by
   this script and by `code/241`. These firms were never in them.

WHAT PUBLISHES, AND WHERE THE LINE IS
--------------------------------------
Two outputs, two publication rules, one internal source - exactly as the class
proposal requires (the research file and the register are different tables).

    individual_native_firm_contracts.csv            INTERNAL
        firm-year grain, carries the surrogate id AND the UEI AND the name.
        Never ships. It is the join surface.

    individual_native_firm_contracts_published.csv  PUBLISHABLE
        (a) per-firm rows keyed ONLY on the Cedar surrogate, carrying nothing
            but obligation totals and a fiscal-year span. No name, no UEI, no
            state, no agency, no sector - because a state plus a sector plus a
            year on a single firm is a name written in another alphabet.
        (b) aggregate cells over year / agency / sector / state / set-aside,
            each SUPPRESSED where it resolves to fewer than
            `cedar_domain.INDIVIDUAL_NATIVE_MIN_CELL_FIRMS` firms. The
            suppression is REPORTED on the row, never silently dropped - the
            CGCC precedent, where 318 rows carry
            `value_suppressed_by_regulator` with a blank value.

The withholding rule is per FIELD and is asked of
`cedar_domain.may_publish_individual_native_field()`, never decided here. The
UEI carve-out is the one people get wrong: **SAM's own public entity search
resolves a UEI to a legal name and a street address, so for a firm whose legal
name is a person's name the UEI publishes the name by ONE HOP.** It is withheld
wherever `firm_legal_name_is_person` is 1 or UNKNOWN.

This restriction is INDEPENDENT of D&B licensing and survives any answer to it.
Cedar Press's own written policy is inherited, not restated:
`nrc_meeting_participants` - *"Cedar Press names an individual only where a
public professional capacity is established"*; `ferc_ex_parte_parties` -
*"Cedar Press does not publish datasets about private individuals."*

SELF-CERTIFICATION IS A COLUMN, NOT A VERDICT
----------------------------------------------
`no_native_setaside_share` is computed and published because it is a fact about
the CONTRACTS. It is not a fact about the firms. Measured project-wide,
**$140.00B of the $244.77B attributed (57.2%) carries no Native set-aside at
all**, and 22 of the 40 prior-ruled firms here carry ZERO native flags on any
row - the largest, Frontier Electronic Systems, on 998 rows and $204,225,019.
**Absence of a flag is not evidence against.**

    py -3 code/242_build_individual_native_firm_contracts.py

Reads   data/clean/individual_native_firm_register.csv   (written by code/241)
        data/clean/prime_contracts.csv                   (READ ONLY)
Writes  data/clean/individual_native_firm_contracts.csv
        data/clean/individual_native_firm_contracts_published.csv
        logs/242_build_individual_native_firm_contracts.log
"""

import csv
import importlib.util
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
REGISTER = CLEAN / "individual_native_firm_register.csv"
PRIME = CLEAN / "prime_contracts.csv"
OUT_INTERNAL = CLEAN / "individual_native_firm_contracts.csv"
OUT_PUBLISHED = CLEAN / "individual_native_firm_contracts_published.csv"
LOGS = CEDAR / "logs"
TODAY = date.today().isoformat()
BACKUP_TAG = "pre_242_build_individual_native_firm_contracts"

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))
LOG_LINES = []


def log(m=""):
    print(m)
    LOG_LINES.append(m)


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, CEDAR / "code" / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


D = load_module("cedar_domain", "cedar_domain.py")
CLASS = D.INDIVIDUAL_NATIVE_CLASS
MIN_FIRMS = D.INDIVIDUAL_NATIVE_MIN_CELL_FIRMS

NATIVE_FLAGS = ("reported_8a", "reported_buy_indian", "reported_indian_business",
                "reported_native_preference")


def load(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def write_atomic(path, rows, fields):
    path = Path(path)
    if path.exists():
        bak = Path(f"{path}.bak_{TODAY}_{BACKUP_TAG}")
        if not bak.exists():
            shutil.copy2(path, bak)
            log(f"  backed up -> {bak.name}")
    part = Path(str(path) + ".part")
    with open(part, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({f: r.get(f, "") for f in fields})
    part.replace(path)
    log(f"  wrote {path.relative_to(CEDAR)}  ({len(rows):,} rows, "
        f"{len(fields)} columns)")


def truthy(v):
    return str(v or "").strip().upper() in {"1", "Y", "YES", "TRUE"}


def main():
    log("=== Cedar Press 242: individually Native-owned firm contracting ===\n")

    register = load(REGISTER)
    if not register:
        raise SystemExit("ABORT: individual_native_firm_register.csv is empty "
                         "or missing. Run code/241 first.")
    log(f"  register : {len(register)} firms in class {CLASS!r}")

    # Key on IDENTITY - UEI then CAGE. Never on a rank, an index or a row
    # number: `verification_id` is positional and a concurrent rewrite of
    # prime_contracts.csv on 2026-08-26 shifted every id below an insertion
    # point, putting one firm's ownership sentence on another firm's row.
    by_uei, by_cage = {}, {}
    for r in register:
        if r["identifier_type"] == "UEI":
            by_uei[r["identifier"].upper()] = r
        elif r["identifier_type"] == "CAGE":
            by_cage[r["identifier"].upper()] = r
    n_name_only = sum(1 for r in register if r["identifier_type"] == "NAME")
    log(f"  keyed on UEI {len(by_uei)}, on CAGE {len(by_cage)}, "
        f"name-only {n_name_only}")
    log("  a name-only ruling binds NOTHING: a name is not an identifier, so "
        "those")
    log("  firms carry an entity and no contract rows rather than a guessed "
        "join.")

    # ---- one READ-ONLY pass over prime_contracts --------------------------
    log("\n[1] Scanning prime_contracts.csv (READ ONLY - nothing is written "
        "back)")
    fy = defaultdict(lambda: {"rows": 0, "usd": 0.0, "usd_real": 0.0,
                              "flagged_rows": 0, "flagged_usd": 0.0,
                              "agencies": set(), "sectors": set(),
                              "states": set(), "setasides": Counter(),
                              "competed": Counter()})
    cell_agency = defaultdict(lambda: {"rows": 0, "usd": 0.0, "firms": set()})
    cell_sector = defaultdict(lambda: {"rows": 0, "usd": 0.0, "firms": set()})
    cell_state = defaultdict(lambda: {"rows": 0, "usd": 0.0, "firms": set()})
    cell_year = defaultdict(lambda: {"rows": 0, "usd": 0.0, "firms": set()})
    cell_setaside = defaultdict(lambda: {"rows": 0, "usd": 0.0, "firms": set()})
    scanned = 0
    attributed_flag_seen = Counter()

    with open(PRIME, encoding="utf-8-sig", errors="replace", newline="") as fh:
        for row in csv.DictReader(fh):
            scanned += 1
            u = (row.get("awardee_uei") or "").strip().upper()
            c = (row.get("cage_code") or "").strip().upper()
            reg = by_uei.get(u) or (by_cage.get(c) if c else None)
            if reg is None:
                continue
            sid = reg["surrogate_entity_id"]
            year = (row.get("fiscal_year") or "").strip()
            year = str(int(float(year))) if year else ""
            try:
                usd = float(row.get("total_obligations") or 0)
            except ValueError:
                usd = 0.0
            try:
                usd_real = float(row.get("total_obligations_real2025") or 0)
            except ValueError:
                usd_real = 0.0
            flagged = any(truthy(row.get(f)) for f in NATIVE_FLAGS)

            b = fy[(sid, year)]
            b["rows"] += 1
            b["usd"] += usd
            b["usd_real"] += usd_real
            if flagged:
                b["flagged_rows"] += 1
                b["flagged_usd"] += usd
            ag = (row.get("funding_agency") or "").strip()
            sec = (row.get("sector") or "").strip()
            st = (row.get("recipient_state_code") or "").strip()
            sa = (row.get("setaside") or "").strip() or "(none reported)"
            if ag:
                b["agencies"].add(ag)
            if sec:
                b["sectors"].add(sec)
            if st:
                b["states"].add(st)
            b["setasides"][sa] += 1
            b["competed"][(row.get("extent_competed_normalized")
                           or row.get("extent_competed") or "").strip()] += 1
            attributed_flag_seen[row.get("attributed_flag") or ""] += 1

            for store, key in ((cell_year, (year,)),
                               (cell_agency, (year, ag)),
                               (cell_sector, (year, sec)),
                               (cell_state, (st,)),
                               (cell_setaside, (sa,))):
                d = store[key]
                d["rows"] += 1
                d["usd"] += usd
                d["firms"].add(sid)

    log(f"  scanned {scanned:,} prime rows")
    log(f"  matched {sum(v['rows'] for v in fy.values()):,} rows on "
        f"{len({k[0] for k in fy})} firms")
    log(f"  their attributed_flag as it stands in prime_contracts.csv: "
        f"{dict(attributed_flag_seen)}")
    log("  -> UNCHANGED by this script. The tribal attributed total is "
        "untouched.")

    # ---- internal table ---------------------------------------------------
    reg_by_sid = {r["surrogate_entity_id"]: r for r in register}
    internal = []
    for (sid, year), b in sorted(fy.items()):
        r = reg_by_sid[sid]
        internal.append({
            "surrogate_entity_id": sid,
            "entity_class": CLASS,
            "fiscal_year": year,
            # INTERNAL ONLY. Present so the table can be joined; every one of
            # these three is in cedar_domain.INDIVIDUAL_NATIVE_WITHHELD_FIELDS.
            "canonical_name": r["canonical_name"],
            "identifier_type": r["identifier_type"],
            "identifier": r["identifier"],
            "recipient_states": "|".join(sorted(b["states"])),
            "n_contract_rows": b["rows"],
            "total_obligations_usd": f"{b['usd']:.2f}",
            "total_obligations_real2025_usd": f"{b['usd_real']:.2f}",
            "rows_with_a_native_setaside_flag": b["flagged_rows"],
            "obligations_with_a_native_setaside_flag": f"{b['flagged_usd']:.2f}",
            "n_funding_agencies": len(b["agencies"]),
            "funding_agencies": "|".join(sorted(b["agencies"]))[:2000],
            "sectors": "|".join(sorted(b["sectors"]))[:1000],
            "top_setaside": (b["setasides"].most_common(1)[0][0]
                             if b["setasides"] else ""),
            "extent_competed_modal": (b["competed"].most_common(1)[0][0]
                                      if b["competed"] else ""),
            "evidence_tier": r["evidence_tier"],
            "evidence_grade": r["evidence_grade"],
            "sam_self_certification": r["sam_self_certification"],
            "firm_legal_name_is_person": r["firm_legal_name_is_person"],
            "publish_name": r["publish_name"],
            "publish_federal_identifier": r["publish_federal_identifier"],
            "publishable_contract_facts": "Y",
            "temporal_caveat": r["temporal_caveat"],
            "source_table": "prime_contracts.csv (read only)",
            "built_date": TODAY,
            "built_by": "code/242_build_individual_native_firm_contracts.py",
        })

    # ---- published table --------------------------------------------------
    pub = []

    def cell(kind, dim1, dim2, d, note=""):
        n_firms = len(d["firms"])
        supp = D.suppress_small_cell(n_firms)
        return {
            "cell_type": kind,
            "dimension_1": dim1,
            "dimension_2": dim2,
            "entity_class": CLASS,
            "n_firms": n_firms,
            "n_contract_rows": "" if supp else d["rows"],
            "total_obligations_usd": "" if supp else f"{d['usd']:.2f}",
            "value_suppressed_small_cell": "1" if supp else "0",
            "suppression_rule":
                (f"Fewer than {MIN_FIRMS} firms resolve to this cell. A "
                 f"one- or two-firm cell in a class of privately owned firms "
                 f"is a person's name written in another alphabet. The cell is "
                 f"REPORTED with its n_firms and a blank value, never silently "
                 f"dropped.") if supp else "",
            "note": note,
            "built_date": TODAY,
        }

    # (a) per-firm, surrogate only. No name, no identifier, no state, no
    #     agency, no sector - only totals and a span.
    per_firm = defaultdict(lambda: {"rows": 0, "usd": 0.0, "years": set()})
    for (sid, year), b in fy.items():
        p = per_firm[sid]
        p["rows"] += b["rows"]
        p["usd"] += b["usd"]
        if year:
            p["years"].add(int(year))
    for r in register:
        sid = r["surrogate_entity_id"]
        p = per_firm.get(sid, {"rows": 0, "usd": 0.0, "years": set()})
        pub.append({
            "cell_type": "FIRM",
            "dimension_1": sid,
            "dimension_2": "",
            "entity_class": CLASS,
            "n_firms": 1,
            "n_contract_rows": p["rows"],
            "total_obligations_usd": f"{p['usd']:.2f}",
            "value_suppressed_small_cell": "0",
            "suppression_rule": "",
            "note": (f"Keyed on a Cedar-internal surrogate that resolves to no "
                     f"public record. fy {min(p['years']) if p['years'] else ''}"
                     f"-{max(p['years']) if p['years'] else ''}. Name, "
                     f"identifier, state, agency and sector are WITHHELD on "
                     f"this row: released only in an aggregate of at least "
                     f"{MIN_FIRMS} firms, or on a name released by recorded "
                     f"consent. evidence_tier "
                     f"{r['evidence_tier']} ({r['evidence_grade']}); "
                     f"sam_self_certification {r['sam_self_certification']} - "
                     f"a channel, never a verdict."),
            "built_date": TODAY,
        })

    for (year,), d in sorted(cell_year.items()):
        pub.append(cell("FISCAL_YEAR", year, "", d))
    for (year, ag), d in sorted(cell_agency.items()):
        pub.append(cell("FISCAL_YEAR_x_AGENCY", year, ag, d))
    for (year, sec), d in sorted(cell_sector.items()):
        pub.append(cell("FISCAL_YEAR_x_SECTOR", year, sec, d))
    for (st,), d in sorted(cell_state.items()):
        pub.append(cell("STATE", st, "", d))
    for (sa,), d in sorted(cell_setaside.items()):
        pub.append(cell(
            "SETASIDE", sa, "", d,
            note="A set-aside is a property of the AWARD and is blank on ~56% "
                 "of archive rows. It is recorded, never read as evidence "
                 "about the firm's owners."))

    # ---- the class total, and the flag finding ----------------------------
    tot_rows = sum(b["rows"] for b in fy.values())
    tot_usd = sum(b["usd"] for b in fy.values())
    flag_rows = sum(b["flagged_rows"] for b in fy.values())
    flag_usd = sum(b["flagged_usd"] for b in fy.values())
    n_firms_with_contracts = len({k[0] for k in fy})
    years = sorted({int(k[1]) for k in fy if k[1]})

    pub.append({
        "cell_type": "CLASS_TOTAL",
        "dimension_1": "ALL", "dimension_2": "",
        "entity_class": CLASS,
        "n_firms": n_firms_with_contracts,
        "n_contract_rows": tot_rows,
        "total_obligations_usd": f"{tot_usd:.2f}",
        "value_suppressed_small_cell": "0",
        "suppression_rule": "",
        "note": (f"Federal prime contract obligations to individually "
                 f"Native-owned firms carrying an owner ruling, FY"
                 f"{years[0]}-{years[-1]}. **NEVER summed with any tribal, ANC "
                 f"or NHO total** - these firms were never in one, and the two "
                 f"classes move in opposite directions (the individual class "
                 f"is larger by row count and smaller by dollars). This is a "
                 f"FLOOR on the class: it counts only firms the owner has "
                 f"already ruled."),
        "built_date": TODAY,
    })
    pub.append({
        "cell_type": "NATIVE_SETASIDE_COVERAGE",
        "dimension_1": "ALL", "dimension_2": "",
        "entity_class": CLASS,
        "n_firms": n_firms_with_contracts,
        "n_contract_rows": tot_rows - flag_rows,
        "total_obligations_usd": f"{tot_usd - flag_usd:.2f}",
        "value_suppressed_small_cell": "0",
        "suppression_rule": "",
        "note": (f"Rows and dollars in this class carrying NO Native "
                 f"set-aside or socio-economic flag of any kind: "
                 f"{tot_rows - flag_rows:,} of {tot_rows:,} rows "
                 f"({100.0 * (tot_rows - flag_rows) / max(tot_rows, 1):.1f}%), "
                 f"${tot_usd - flag_usd:,.2f} of ${tot_usd:,.2f} "
                 f"({100.0 * (tot_usd - flag_usd) / max(tot_usd, 1e-9):.1f}%). "
                 f"**Absence of a flag is not evidence against.** "
                 f"Project-wide, $140.00B of the $244.77B attributed (57.2%) "
                 f"carries no Native set-aside either, and 22 of the 40 "
                 f"prior-ruled firms here carry zero flags on every row - the "
                 f"largest, Frontier Electronic Systems, on 998 rows and "
                 f"$204,225,019. The flag is a discovery channel with a "
                 f"documented blind spot, never a definition of the "
                 f"population."),
        "built_date": TODAY,
    })

    # ---- GUARDS -----------------------------------------------------------
    log("\n[2] Publication guards")
    leaked = []
    for r in pub:
        blob = " | ".join(str(v) for v in r.values())
        for reg in register:
            nm = reg["canonical_name"]
            if reg["publish_name"] != "1" and nm and nm.lower() in blob.lower():
                leaked.append((r["cell_type"], r["dimension_1"], nm))
            ident = reg["identifier"]
            if (reg["publish_federal_identifier"] != "1"
                    and reg["identifier_type"] in {"UEI", "CAGE"}
                    and ident and ident.upper() in blob.upper()):
                leaked.append((r["cell_type"], r["dimension_1"], ident))
    if leaked:
        raise SystemExit(
            f"ABORT: the publishable table contains {len(leaked)} withheld "
            f"names or identifiers: {leaked[:5]}. Publishing a UEI whose firm "
            f"name is a person's publishes the name by one hop through SAM's "
            f"own entity search.")
    log(f"  withheld names/identifiers appearing in the published table : 0")

    bad = [r for r in pub
           if r["value_suppressed_small_cell"] == "0"
           and r["cell_type"] not in {"FIRM", "CLASS_TOTAL",
                                      "NATIVE_SETASIDE_COVERAGE"}
           and int(r["n_firms"]) < MIN_FIRMS]
    if bad:
        raise SystemExit(f"ABORT: {len(bad)} aggregate cells under {MIN_FIRMS} "
                         f"firms were not suppressed.")
    n_supp = sum(1 for r in pub if r["value_suppressed_small_cell"] == "1")
    log(f"  aggregate cells suppressed (<{MIN_FIRMS} firms) : {n_supp} of "
        f"{len(pub)}")
    log("  suppressed cells keep n_firms and state the rule; none is dropped.")

    for r in pub + internal:
        for k, v in r.items():
            if not D.absence_value_ok(v):
                raise SystemExit(f"ABORT: forbidden absence value {v!r} in {k}.")
    log("  forbidden absence values (NOT_NATIVE et al.) : 0")

    # ---- write ------------------------------------------------------------
    log("\n[3] Writing")
    write_atomic(OUT_INTERNAL, internal, list(internal[0].keys()))
    write_atomic(OUT_PUBLISHED, pub, list(pub[0].keys()))

    log("\n[4] Verify by RE-READING")
    a, b = load(OUT_INTERNAL), load(OUT_PUBLISHED)
    log(f"  internal on disk : {len(a):,} firm-year rows")
    log(f"  published on disk: {len(b):,} cells")

    log("\n[5] The class, measured")
    log(f"  firms with contract rows : {n_firms_with_contracts} of "
        f"{len(register)}")
    log(f"  prime rows               : {tot_rows:,}")
    log(f"  obligations              : ${tot_usd:,.2f}")
    log(f"  fiscal years             : FY{years[0]}-FY{years[-1]}")
    log(f"  rows with NO native flag : {tot_rows - flag_rows:,} "
        f"({100.0 * (tot_rows - flag_rows) / tot_rows:.1f}%)")
    log(f"  dollars with NO native flag : ${tot_usd - flag_usd:,.2f} "
        f"({100.0 * (tot_usd - flag_usd) / tot_usd:.1f}%)")
    log("  NEVER summed with a tribal, ANC or NHO total.")

    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / "242_build_individual_native_firm_contracts.log").write_text(
        "\n".join(LOG_LINES), encoding="utf-8")
    log("\n  now run:  py -3 code/243_write_individual_native_class_codebook_fragment.py")


if __name__ == "__main__":
    main()
