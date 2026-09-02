#!/usr/bin/env python3
"""
Cedar Press - 954: CODEBOOK BLOCKS FOR THE COLUMNS 950/952/953 PROMOTED.

    py -3 code/954_register_promoted_columns_codebook.py
    py -3 code/954_register_promoted_columns_codebook.py verify
    py -3 code/954_register_promoted_columns_codebook.py selftest

WHY
---
A column a buyer cannot look up is a column a buyer will guess at. The
promotion pass (ADR-016) put 17 new columns on three shipped tables and
`data/clean/codebook/` is the registry that says what each one means, how full
it is, and what it may not be used for. Writing the column and not the block
would leave `award_attributes_basis` as a wall of prose with no entry, and
`federal_uei_candidate` as something a reader would reasonably mistake for a
resolved key.

Every `pct_filled` and `n_rows` below is MEASURED off the live table at run
time - none is typed. That matters because the fill rates here are the honest
part of the story: PSC and award description reach 20.4% of contracting rows
and not one row more, and the block says so where a buyer will read it.

Fragments only. `cedar_codebook.write_fragment` cannot affect another
dataset's block, and `build()` refuses a rebuild that would shrink the master -
which is the guard that makes this safe to run while other agents are writing
their own fragments.

INVARIANT
---------
  INV-REGISTERED  every column 950/952/953 added is present in the codebook
                  master with a non-empty description, and its recorded
                  pct_filled matches the live table to 0.1pp.
"""
from __future__ import annotations

import csv
import importlib.util
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()
CLEAN = ROOT / "data" / "clean"
FRAG = CLEAN / "codebook"
MASTER = CLEAN / "codebook_master.csv"

_spec = importlib.util.spec_from_file_location(
    "cedar_codebook", ROOT / "code" / "cedar_codebook.py")
cb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cb)

NA = ("NOT a resolved key and it may not key a dollar. ")

BLOCKS = {
    ("02_prime_contracting", "prime_contracts.csv"): [
        ("contract_award_unique_key", "text", "code", "subscriber",
         "The USAspending AWARD this transaction belongs to. Promoted from "
         "the FY2008-FY2026 archive extract by "
         "`code/950_promote_contract_attributes.py`; blank on the 376,766 "
         "rows that carry no `contract_transaction_unique_key` because they "
         "come from the BGOV / master-prime lineage, which never had one. "
         "This is the key the award-grain columns below were joined on."),
        ("naics_code", "text", "code", "subscriber",
         "SIX-digit NAICS, transaction grain, as recorded in the archive "
         "extract. The table's older `sector` column is the TWO-digit prefix "
         "and is kept; where both exist they agree on 838,207 of 838,227 "
         "cross-checked rows. The 20 that disagree are all FY2008, all at the "
         "archive/BGOV merge seam, and are enumerated by transaction key in "
         "`review/prime_naics_sector_conflicts_2026-09-02.csv` - flagged, not "
         "resolved. The archive renders a missing NAICS as the literal string "
         "`nan`; 2,773 such values were normalised to blank rather than "
         "shipped as a code."),
        ("naics_description", "text", "text", "subscriber",
         "The NAICS industry title. AWARD grain, from the local "
         "`usaspending_gapfill_2026-08-05` corpus, so it is present only "
         "where that corpus holds the award - 20.4% of rows. Its absence is "
         "not evidence the NAICS is unknown; `naics_code` is on 68.8%."),
        ("action_date", "date", "date", "subscriber",
         "The exact date of the contract action. The table previously carried "
         "only `fiscal_year`. Transaction grain, archive extract, 69.1% - "
         "blank wherever `contract_transaction_unique_key` is blank."),
        ("award_type", "text", "category", "subscriber",
         "FPDS award type, e.g. DELIVERY ORDER, PURCHASE ORDER, DEFINITIVE "
         "CONTRACT, BPA CALL. Transaction grain, archive extract. 71,134 "
         "archive rows carry the literal `nan` for this field and were "
         "normalised to blank, which is why the fill is below that of "
         "`action_date`."),
        ("product_or_service_code", "text", "code", "subscriber",
         "FPDS PSC - WHAT was bought. AWARD grain, from the local gapfill "
         "corpus, joined through the archive's transaction-to-award bridge. "
         "**20.4% of rows and that is the ceiling of what is reachable "
         "without a re-pull**: the corpus holds 1,041,147 award keys and only "
         "87,171 of the 307,671 awards this table needs. The other 79.6% is a "
         "genuine FPDS re-pull, not a join we have not done yet."),
        ("product_or_service_code_description", "text", "text", "subscriber",
         "The PSC title, e.g. `SUPPORT- ADMINISTRATIVE: OTHER`. Same source, "
         "grain and 20.4% ceiling as `product_or_service_code`."),
        ("award_base_description", "text", "text", "subscriber",
         "The contracting officer's description of the BASE AWARD - what the "
         "work is. FPDS publishes this at base-award grain, NOT per "
         "modification, and the column name says so: on an award with 40 "
         "modifications all 40 rows carry the same text. Do not read it as a "
         "description of the individual action. 20.4%, same ceiling as PSC. "
         "Six rows read `NA`; that is what the contracting officer typed and "
         "it is left as recorded."),
        ("award_attributes_basis", "text", "provenance", "public",
         "Per-row provenance for the eight columns above, never blank. Three "
         "values: the archive+gapfill case (247,987 rows), archive-only "
         "because the award is not in the local gapfill corpus (593,015), and "
         "no transaction key on the row at all (376,766). A reader can tell a "
         "blank PSC that means 'not acquired' from one that means 'this row "
         "has no federal transaction key' without leaving the table."),
    ],
    ("06_nonprofit", "np_orgs.csv"): [
        ("disposition", "text", "category", "public",
         "What Cedar concluded about this EIN, on ONE vocabulary and never "
         "blank. Ten values: EXCLUDED_PRIOR_RULING, "
         "EXCLUDED_PLACE_NAME_COINCIDENCE, NATIVE_VERIFIED_STRICT, "
         "NATIVE_RULED_VERIFIED, NATIVE_PROPOSED_AWAITING_OWNER_RULING, "
         "CANDIDATE_STATE_VALIDATED, CANDIDATE_NAME_MATCH_UNVERIFIED, "
         "CANDIDATE_NAME_MATCH_GENERIC_TOKEN_ONLY, CANDIDATE_NAME_ONLY, "
         "CONFLICT_EXCLUDED_AND_RULED_NATIVE. **This is not the same column "
         "as `classification_ruling`**, which records a HAND ruling by a "
         "named authority and is `UNRULED` on 96.9% of rows precisely because "
         "most rows were disposed of by rule rather than by hand. Derived by "
         "`code/952_nonprofit_disposition.py` from `funnel_stage` and "
         "`excluded_by_prior_ruling`; a CANDIDATE_* value is not a claim that "
         "the organisation is Native."),
        ("disposition_basis", "text", "provenance", "public",
         "The columns and the rule that produced `disposition`, on the row. "
         "Two rows read CONFLICT_EXCLUDED_AND_RULED_NATIVE and their basis "
         "says which two prior decisions disagree; nothing was resolved to "
         "make the column tidy."),
        ("name_match_support", "text", "category", "public",
         "Whether the cited canonical-name match rests on a DISTINCTIVE token "
         "or only on a generic one. Four values: `distinctive_token`, "
         "`generic_token_only` (578 rows), "
         "`no_shared_token_with_canonical_name` (2,268 - the displayed "
         "canonical name does not explain the match at all), and "
         "`not_a_name_match`. **A statement about the EVIDENCE, never about "
         "Native status** - Cedar's standing rule is that Native status comes "
         "from an organisation's own filing, never from a name and never from "
         "an NTEE code. The 258 live `generic_token_only` rows include 55 VFW "
         "posts matched to United Auburn on UNITED and 38 Order of the "
         "Eastern Star chapters matched to Chickahominy Indians-Eastern "
         "Division on EASTERN."),
        ("name_match_shared_tokens", "text", "text", "public",
         "The actual tokens the organisation name and the matched tribe's "
         "canonical name have in common, pipe-separated. This is the evidence "
         "for `name_match_support` and it is on the row so the label can be "
         "checked rather than trusted."),
    ],
    ("02m_native_owned_businesses", "native_owned_businesses.csv"): [
        ("federal_uei_candidate", "text", "code", "subscriber",
         "A CANDIDATE federal UEI for this firm, " + NA +
         "Derived by `code/953_nob_federal_identifier_candidates.py` from "
         "local data only - no download - by exact match of the normalised "
         "business name against the 31,059 UEI-bearing names in "
         "`prime_contracts.csv`, `fpds_uei_cage_map.csv`, `subawards.csv` and "
         "the gapfill recipient universe, and written ONLY where that name "
         "resolves to exactly one UEI. The directory's own resolved-entity "
         "column, `business_entity_id`, is populated on 4 of 2,393 rows and "
         "is NOT written by this script. Adopt or refuse the candidate "
         "explicitly. **A second, independent matcher exists and is the "
         "richer authority**: `native_business_identifier_crosswalk.csv` "
         "(`code/1001_link_businesses_to_contracting.py`) reaches 263 "
         "business ids to this column's 220 and carries A/B/C/X tiers, a "
         "self-published rung and a contract-number rung. Measured "
         "2026-09-02, the two share 196 ids and agree on **196 of 196**, "
         "which is a real corroboration because neither was derived from the "
         "other; 953's `verify` fails if they ever disagree. Join the "
         "crosswalk when you want the tier."),
        ("federal_cage_candidate", "text", "code", "subscriber",
         "The CAGE code for `federal_uei_candidate`, where "
         "`fpds_uei_cage_map.csv` holds exactly one for that UEI. Same "
         "candidate status. Note that the map carries blank and literal-`NAN` "
         "CAGE values on the same UEIs, so those are excluded."),
        ("federal_identifier_match_status", "text", "category", "public",
         "Never blank. Five values: `unique_name_match`, "
         "`ambiguous_name_match_refused` (two or more UEIs share the "
         "normalised name), `no_match`, `refused_person_name_too_weak` (the "
         "source flagged the name as a person's and it normalises to two "
         "tokens or fewer - the NAME SHIPS, only the match is refused), and "
         "`refused_source_terms_restrictive`. **`no_match` is not evidence "
         "the firm holds no federal award**: the universe searched is Cedar's "
         "Native-attributed slice of FPDS, not all of FPDS."),
        ("federal_identifier_match_basis", "text", "provenance", "public",
         "The sources, the normalisation and the refusal, on the row. On the "
         "346 rows whose source is `TERMS_STATED_RESTRICTIVE` it records that "
         "no identifier is attached by any route - 58 of them would have "
         "matched. A harmonized derivative is still a derivative."),
    ],
}
ALL = {t: [c[0] for c in cols] for (_d, t), cols in BLOCKS.items()}


def measure(table: str, cols: list):
    p = CLEAN / table
    if not p.exists():
        raise SystemExit(f"[954] FATAL: {p} not found")
    n = 0
    fill = {c: 0 for c in cols}
    with p.open(encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        missing = [c for c in cols if c not in (rd.fieldnames or [])]
        if missing:
            raise SystemExit(f"[954] FATAL: {table} has no column(s) "
                             f"{missing} - run 950/952/953 first. A coverage "
                             "computation must RAISE on a missing column, "
                             "never print a zero.")
        for r in rd:
            n += 1
            for c in cols:
                if (r.get(c) or "").strip():
                    fill[c] += 1
    return n, fill


def build_rows():
    out = {}
    for (ds, table), specs in BLOCKS.items():
        cols = [s[0] for s in specs]
        n, fill = measure(table, cols)
        rows = []
        for name, typ, units, tier, desc in specs:
            rows.append({
                "dataset": ds, "variable": name, "type": typ, "units": units,
                "pct_filled": round(100.0 * fill[name] / n, 1),
                "n_rows": n, "published": 1, "access_tier": tier,
                "description": desc, "generated": TODAY})
        out[ds] = rows
    return out


def register() -> int:
    fields = ["dataset", "variable", "type", "units", "pct_filled", "n_rows",
              "published", "access_tier", "description", "generated"]
    total_before = len(cb.read(MASTER))
    for ds, rows in build_rows().items():
        frag = FRAG / f"{ds}.csv"
        existing = cb.read(frag) if frag.exists() else []
        have = {r["variable"] for r in existing}
        keep = [r for r in existing if r["variable"] not in
                {x["variable"] for x in rows}]
        merged = keep + [{k: r[k] for k in fields} for r in rows]
        replaced = sum(1 for r in rows if r["variable"] in have)
        cb.write_fragment(ds, merged, fields)
        print(f"  [954] {ds:<32} {len(existing):>3} -> {len(merged):>3} rows "
              f"({len(rows) - replaced} new, {replaced} refreshed)")
    cb.build()
    print(f"  [954] codebook master {total_before:,} -> "
          f"{len(cb.read(MASTER)):,} rows")
    return 0


def verify() -> int:
    master = cb.read(MASTER)
    have = {(r["dataset"], r["variable"]): r for r in master}
    fails = []
    for (ds, table), specs in BLOCKS.items():
        cols = [s[0] for s in specs]
        n, fill = measure(table, cols)
        for name, *_rest in specs:
            row = have.get((ds, name))
            if row is None:
                fails.append(f"INV-REGISTERED {ds}.{name} is not in the "
                             "codebook master")
                continue
            if not (row.get("description") or "").strip():
                fails.append(f"INV-REGISTERED {ds}.{name} has an empty "
                             "description")
            want = round(100.0 * fill[name] / n, 1)
            try:
                got = float(row.get("pct_filled") or -1)
            except ValueError:
                got = -1.0
            if abs(got - want) > 0.1:
                fails.append(f"INV-REGISTERED {ds}.{name} records "
                             f"pct_filled={got} against a live {want}")
    print(f"  [954] verify  {sum(len(v) for v in ALL.values())} promoted "
          f"columns checked against the codebook master   "
          f"{len(fails)} breaches")
    for f in fails:
        print(f"  [954] !! {f}")
    return 1 if fails else 0


def selftest() -> int:
    """Prove INV-REGISTERED fires: hide one block, expect exit 1."""
    import contextlib
    import io
    import shutil
    ds = "06_nonprofit"
    frag = FRAG / f"{ds}.csv"
    keep = MASTER.with_suffix(".csv._954_selftest")
    shutil.copyfile(MASTER, keep)
    try:
        rows = cb.read(MASTER)
        fields = list(rows[0].keys())
        cut = [r for r in rows
               if not (r["dataset"] == ds and r["variable"] == "disposition")]
        cb._write(MASTER, cut, fields)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            dirty = verify()
        named = "INV-REGISTERED" in buf.getvalue() and "disposition" in \
            buf.getvalue()
        shutil.copyfile(keep, MASTER)
        clean = verify()
    finally:
        shutil.copyfile(keep, MASTER)
        keep.unlink(missing_ok=True)
        _ = frag
    checks = [("a removed block exits 1", dirty == 1),
              ("...and names INV-REGISTERED and the column", named),
              ("the restored master exits 0", clean == 0)]
    for label, ok in checks:
        print(f"  [954] selftest  {'PASS' if ok else 'FAIL'}  {label}")
    return 0 if all(ok for _, ok in checks) else 1


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "register"
    sys.exit({"register": register, "verify": verify,
              "selftest": selftest}[cmd]())
