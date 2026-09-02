#!/usr/bin/env python3
"""
Cedar Press - 575: CLOSURE of the `native-owned-businesses` dataset (C5).

    py -3 code/575_closure_native_owned_businesses.py conserve
    py -3 code/575_closure_native_owned_businesses.py conserve --publish-only
    py -3 code/575_closure_native_owned_businesses.py verify

WHY THIS FILE EXISTS
--------------------
`518_dataset_readiness.py` scored `native-owned-businesses` BLOCKED on exactly
ONE point of the ten-point shipping contract:

    C5  every harvested row has a named disposition

Six customer tables, every grain declared AND validated, every primary key
unique, not one literal duplicate row, a declared non-destructive rebuild path
- and no statement anywhere about what went INTO the build. "45 firms came out"
licenses a reader to believe nothing was lost between 12,491 federal awardees
and those 45, and the build had no way to say whether that was true.

This file gives every source row of this dataset a NAMED bucket, and refuses to
pass while a single row lacks one.

THE LEDGER KEY IS THE OUTPUT TABLE, NOT THE INPUT
-------------------------------------------------
`510_assertions.py` keys its ledgers by the SOURCE table it harvests. These are
keyed by the OUTPUT table whose construction they account for, following the
convention `77_build_nagpra_dataset.py` set and `519_closure_federal_register.py`
reused: most of these outputs have no single source table, and one output is cut
out of two inputs at two different grains (the published table is aggregated
from the firm-year contracts AND from the 45-row register). The arithmetic
invariant 510's I13 checks is identical either way: within one key,
`rows_in == sum(dispositions)`.

`518_dataset_readiness.py` reads C5 coverage as `basename(source_table)`, so the
key must be exactly `data/clean/<output>.csv` with NO bracketed annotation. 510
annotates grain inside the `source_table` string (`np_orgs.csv [IRS BMF rows]`)
and that string does not basename-match its own table, which is why the grain of
a ledger is stated here in the DISPOSITION NAME instead.

TWO LEDGERS DO NOT COUNT ROWS OF THE SAME THING, AND SAY SO
------------------------------------------------------------
Three of these six builds read an input at a grain that is not "one row of a
CSV":

  * the candidate build reads 1,217,768 prime contract transaction rows and
    aggregates them to 12,491 AWARDEES before it decides anything. The unit
    that survives or is dropped is the awardee, so the ledger counts awardees
    and every disposition name says `awardee`.
  * the register build's unit is one owner RULING (45 of them).
  * the published build's units are a firm-year row (324) and a register firm
    (45). Both are counted, and each disposition names which.

Stating the unit in the disposition is not decoration. A reader who assumes
`rows_in = 12,491` means 12,491 CSV rows will conclude prime_contracts.csv has
12,491 rows, and it has ninety-seven times that.

MERGE, NEVER REWRITE - the failure this file is written to survive
-------------------------------------------------------------------
`data/clean/cedar_harvest_conservation.csv` is SHARED. 510 (36 ledgers), 519
(federal-register, 22 ledgers) and 77/78 (nagpra) all merge into it. On
2026-09-01 a wholesale rewrite took it from 2,146,673 accounted rows to
101,176 and wiped the C5 evidence for two datasets that had just been closed on
it. So:

  * `publish()` preserves every `source_table` key it does not own.
  * the six ledgers are ALSO kept, durably and in full, in
    `review/native_owned_businesses_row_conservation.csv`, and the repair after
    somebody else rewrites the shared file is one cheap command that recomputes
    nothing:  `575 conserve --publish-only`.
  * `verify` names that repair in its own failure text.

RECOMPUTED vs MEASURED, and why the difference is stated
--------------------------------------------------------
  RECOMPUTED  the builder's own selection rule was re-run over the input on
              disk (170's awardee aggregation, its `attributed_flag` test, its
              TOP_N cut and its SAM_FLAG_COLS test, with 170's own constants
              imported from 170 rather than retyped here). The recomputation is
              reconciled against the shipped table and FAILS LOUDLY if the two
              disagree - a ledger that quietly describes a build that no longer
              happens is worse than no ledger.
  MEASURED    the disposition is established by key membership between the
              input and the output on disk, and the REASON is the builder's
              documented rule.

WHAT THIS FILE DOES NOT TOUCH
------------------------------
It writes two files: the durable local ledger and the shared conservation file
(merged). It runs no builder, rebuilds no table, mints no identifier, and opens
`prime_contracts.csv` read-only.

Reads   data/clean/prime_contracts.csv,
        data/clean/individual_native_*.csv,
        data/raw/web/individual_native_verification_2026-08-26/output_batch_*.csv
Writes  data/clean/cedar_harvest_conservation.csv     MERGED, never rewritten
        review/native_owned_businesses_row_conservation.csv   durable C5 ledger
"""
from __future__ import annotations

import argparse
import csv
import glob
import importlib.util
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
csv.field_size_limit(10 ** 8)
TODAY = date.today().isoformat()

COLLECTION = "native-owned-businesses"
CONSERVATION_REL = "data/clean/cedar_harvest_conservation.csv"
LEDGER_LOCAL_REL = "review/native_owned_businesses_row_conservation.csv"
CONSERVATION_COLS = ["source_table", "rows_in", "disposition", "rows", "pct",
                     "examples", "harvest_date"]

CLEAN = "data/clean"
PRIME_REL = f"{CLEAN}/prime_contracts.csv"
CAND_REL = f"{CLEAN}/individual_native_verification_candidates.csv"
VERIF_REL = f"{CLEAN}/individual_native_ownership_verification.csv"
PRIOR_REL = f"{CLEAN}/individual_native_prior_rulings.csv"
REG_REL = f"{CLEAN}/individual_native_firm_register.csv"
CONTR_REL = f"{CLEAN}/individual_native_firm_contracts.csv"
PUB_REL = f"{CLEAN}/individual_native_firm_contracts_published.csv"
EXCL_REL = f"{CLEAN}/individual_native_exclusion_pairs.csv"
WEB_GLOB = ("data/raw/web/individual_native_verification_2026-08-26/"
            "output_batch_*.csv")

#: 510's I13 refuses these by name. Re-stated so the refusal happens where a
#: disposition is INVENTED, not two layers downstream.
UNNAMED_REASON_RE = re.compile(r"(?:^|:)(other|unknown|misc|n/?a)\s*$", re.I)

#: The six SHIPPABLE customer tables of this collection, as
#: `500_build_architecture_map.COLLECTIONS` selects them and
#: `cedar_codebook` grades them. `individual_native_prior_rulings.csv` is
#: `internal-by-decision` and is therefore NOT a C5 obligation - but it is the
#: measured INPUT to the register ledger, so it is read here regardless.
CUSTOMER_TABLES = [
    "individual_native_verification_candidates.csv",
    "individual_native_ownership_verification.csv",
    "individual_native_firm_register.csv",
    "individual_native_firm_contracts.csv",
    "individual_native_firm_contracts_published.csv",
    "individual_native_exclusion_pairs.csv",
]


# =====================================================================
# helpers
# =====================================================================
def read_csv(rel_or_path):
    p = Path(rel_or_path)
    if not p.is_absolute():
        p = ROOT / p
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(rel_or_path, rows, cols):
    p = Path(rel_or_path)
    if not p.is_absolute():
        p = ROOT / p
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".part")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, p)


def load_170():
    """Import 170's constants so the recomputation cannot drift from it.

    170 is `if __name__ == '__main__'`-guarded (checked), so importing it
    executes definitions only and reads nothing.
    """
    spec = importlib.util.spec_from_file_location(
        "m170", HERE / "170_build_individual_native_candidates.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)                                   # type: ignore
    return mod


class RowLedger:
    """Per-OUTPUT-table row accounting. Named dispositions only."""

    def __init__(self, table, evidence, unit):
        self.table = f"{CLEAN}/{table}"
        self.evidence = evidence          # RECOMPUTED | MEASURED
        self.unit = unit                  # what one counted row IS
        self.rows_in = 0
        self.counts = Counter()
        self.examples = defaultdict(list)

    def note(self, disposition, n, example=""):
        if UNNAMED_REASON_RE.search(disposition):
            raise ValueError(
                f"disposition {disposition!r} is not a NAMED reason - an "
                f"unnamed rejection is the defect this ledger exists to catch")
        self.counts[disposition] += n
        if example:
            self.examples[disposition].append(str(example)[:90])

    def unaccounted(self):
        return self.rows_in - sum(self.counts.values())


def conservation_rows(ledgers):
    out = []
    for lg in ledgers:
        for disp, n in sorted(lg.counts.items(), key=lambda kv: -kv[1]):
            out.append(dict(
                source_table=lg.table, rows_in=lg.rows_in, disposition=disp,
                rows=n, pct=round(100.0 * n / max(lg.rows_in, 1), 2),
                examples="; ".join(lg.examples.get(disp, [])),
                harvest_date=TODAY))
        if lg.unaccounted():
            out.append(dict(
                source_table=lg.table, rows_in=lg.rows_in,
                disposition="UNACCOUNTED_FOR", rows=lg.unaccounted(),
                pct=round(100.0 * lg.unaccounted() / max(lg.rows_in, 1), 2),
                examples="", harvest_date=TODAY))
    return out


# =====================================================================
# LEDGER 1 - the candidate set, RECOMPUTED from prime_contracts.csv
# =====================================================================
def led_candidates(cand, prior):
    """170's own selection rule, re-run over prime_contracts.csv.

    The counted unit is an AWARDEE, not a contract row: 170 aggregates
    1.2M transactions to an awardee key before it selects anything, so the
    awardee is what survives or is dropped.
    """
    m = load_170()
    lg = RowLedger("individual_native_verification_candidates.csv",
                   "RECOMPUTED (170's aggregation, attributed_flag test, "
                   "TOP_N cut and SAM_FLAG_COLS test, its constants imported)",
                   "awardee key (awardee_uei, else NAME:awardee_name)")

    agg = defaultdict(lambda: dict(obl=0.0, cages=set(), flag=0, att=False))
    n_prime = 0
    p = ROOT / PRIME_REL
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            n_prime += 1
            key = ((r.get("awardee_uei") or "").strip().upper()
                   or "NAME:" + (r.get("awardee_name") or "").strip().upper())
            a = agg[key]
            if r.get("attributed_flag") not in ("0", "", None):
                a["att"] = True
            try:
                a["obl"] += float(r.get("total_obligations") or 0)
            except ValueError:
                pass
            if r.get("cage_code"):
                a["cages"].add(r["cage_code"].upper())
            if any(r.get(c) not in ("", "0", "0.0", None)
                   for c in m.SAM_FLAG_COLS):
                a["flag"] += 1

    lg.rows_in = len(agg)
    unatt = {k: v for k, v in agg.items() if not v["att"]}
    n_att = len(agg) - len(unatt)
    ranked = sorted(unatt.items(), key=lambda kv: -kv[1]["obl"])
    top = ranked[:m.TOP_N]
    flagged = [k for k, v in top if v["flag"] > 0]
    unflagged = [k for k, v in top if v["flag"] == 0]
    already = set(flagged)
    ruled = {r["identifier"].upper() for r in prior if r.get("identifier")}
    stream2 = [k for k, v in unatt.items()
               if k not in already
               and (k.upper() in ruled or (v["cages"] & ruled))]
    rest = len(unatt) - len(top) - len(stream2)

    lg.note("emitted:awardee_selected_as_candidate_TOP400_FLAGGED",
            len(flagged), f"{len(flagged)} of the top {m.TOP_N} unattributed "
                          f"awardees carry a SAM native self-certification")
    lg.note("emitted:awardee_selected_as_candidate_PRIOR_OWNER_RULING",
            len(stream2), "an owner ruling reaches this awardee by UEI or CAGE "
                          "and the flag route missed it")
    lg.note("excluded:awardee_already_attributed_to_a_Native_entity_"
            "attributed_flag_is_not_0_on_every_row", n_att,
            "170 selects from attributed_flag = 0 awardees only")
    lg.note("excluded:awardee_in_the_top400_by_obligations_but_carries_no_SAM_"
            "native_self_certification_on_any_row", len(unflagged),
            "a flag is a discovery channel, not a definition - see 170's "
            "measured blind spot")
    lg.note("excluded:unattributed_awardee_outside_the_top400_by_obligations_"
            "and_reached_by_no_owner_ruling", rest,
            f"{len(unatt):,} unattributed awardees, {m.TOP_N} ranked in")

    # Reconcile against the shipped table. A ledger that describes a build the
    # file no longer matches is a lie with arithmetic in it.
    drift = []
    got = Counter(r.get("candidate_basis", "") for r in cand)
    if got.get("TOP400_FLAGGED", 0) != len(flagged):
        drift.append(f"TOP400_FLAGGED recomputed {len(flagged)} vs "
                     f"{got.get('TOP400_FLAGGED', 0)} on disk")
    if got.get("PRIOR_OWNER_RULING", 0) != len(stream2):
        drift.append(f"PRIOR_OWNER_RULING recomputed {len(stream2)} vs "
                     f"{got.get('PRIOR_OWNER_RULING', 0)} on disk")
    if len(cand) != len(flagged) + len(stream2):
        drift.append(f"{len(cand)} candidate rows on disk vs "
                     f"{len(flagged) + len(stream2)} recomputed")
    return lg, n_prime, drift


# =====================================================================
# LEDGERS 2-6 - MEASURED by key membership
# =====================================================================
def led_verification(cand, verif):
    lg = RowLedger("individual_native_ownership_verification.csv",
                   "MEASURED (verification_id membership; web-pass match "
                   "recorded on the row by 171)",
                   "candidate row + web-pass result row")
    web = []
    for f in sorted(glob.glob(str(ROOT / WEB_GLOB))):
        web += read_csv(f)
    lg.rows_in = len(cand) + len(web)
    matched = sum(1 for r in verif if (r.get("web_pass_matched_on") or "").strip())
    lg.note("emitted:candidate_carried_forward_with_a_matched_web_pass_result",
            matched, "171 matched the researcher batch onto the candidate on UEI")
    lg.note("emitted:candidate_carried_forward_with_NO_web_pass_result_"
            "web_pass_matched_on_is_blank", len(verif) - matched,
            "the candidate was still verified from SAM and the owner rulings; "
            "the web leg is simply absent and the row says so")
    lg.note("merged:web_pass_output_row_matched_onto_its_candidate_on_UEI",
            len(web), f"{len(web)} researcher rows over "
                      f"{len(glob.glob(str(ROOT / WEB_GLOB)))} output batches")
    drift = []
    if {r["verification_id"] for r in verif} != {r["verification_id"] for r in cand}:
        drift.append("the verification table's verification_id set is not the "
                     "candidate table's - the 1:1 this ledger asserts is gone")
    if len(web) != matched:
        drift.append(f"{len(web)} web-pass rows read but {matched} rows carry "
                     f"web_pass_matched_on - a researcher row reached nobody")
    return lg, drift


def led_register(prior, reg):
    lg = RowLedger("individual_native_firm_register.csv",
                   "MEASURED (241 seeds from the 45 owner rulings, not from "
                   "the 335 candidates - a ruling is evidence, a candidate is "
                   "a question)",
                   "owner ruling")
    lg.rows_in = len(prior)
    out = Counter(r.get("ruling_outcome", "") for r in reg)
    for outcome, n in sorted(out.items(), key=lambda kv: -kv[1]):
        lg.note(f"emitted:ruling_promoted_to_a_firm_row_"
                f"ruling_outcome_{outcome or 'BLANK'}", n)
    drift = []
    if len(reg) != len(prior):
        drift.append(f"{len(prior)} owner rulings but {len(reg)} register rows "
                     f"- the 1:1 this ledger asserts is gone")
    # NAME-keyed rulings are upper-cased into the register identifier, so the
    # membership test is case-folded. It is still a membership test.
    pk = {(r["identifier_type"], r["identifier"].upper()) for r in prior}
    rk = {(r["identifier_type"], r["identifier"].upper()) for r in reg}
    if pk != rk:
        drift.append(f"{len(rk - pk)} register row(s) carry an identifier no "
                     f"owner ruling does, {len(pk - rk)} ruling(s) reached no "
                     f"register row")
    return lg, drift


def led_contracts(reg, contr):
    lg = RowLedger("individual_native_firm_contracts.csv",
                   "MEASURED (surrogate_entity_id membership between the "
                   "register and the firm-year table)",
                   "register firm")
    lg.rows_in = len(reg)
    have = {r["surrogate_entity_id"] for r in contr}
    hit = [r for r in reg if r["surrogate_entity_id"] in have]
    miss = [r for r in reg if r["surrogate_entity_id"] not in have]
    lg.note("emitted:register_firm_expanded_to_one_row_per_fiscal_year_with_"
            "prime_contract_activity", len(hit),
            f"{len(hit)} firms -> {len(contr)} firm-year rows, "
            f"{sum(int(r['n_contract_rows'] or 0) for r in contr):,} prime "
            f"transaction rows rolled up")
    lg.note("excluded:register_firm_identified_only_by_NAME_or_CAGE_so_no_"
            "prime_contracts_awardee_key_resolves_to_it", len(miss),
            "; ".join(f"{r['identifier_type']} {r['canonical_name']}"
                      for r in miss[:3]))
    drift = []
    bad = [r for r in miss if int(r.get("n_contract_rows") or 0)]
    if bad:
        drift.append(f"{len(bad)} register firm(s) claim n_contract_rows > 0 "
                     f"and yet have no firm-year row - the stated reason for "
                     f"their absence is not the real one")
    if any(r["identifier_type"] == "UEI" for r in miss):
        drift.append("a UEI-keyed register firm has no firm-year row - the "
                     "NAME/CAGE reason this ledger states does not cover it")
    reg_tot = sum(int(r.get("n_contract_rows") or 0) for r in reg)
    con_tot = sum(int(r.get("n_contract_rows") or 0) for r in contr)
    if reg_tot != con_tot:
        drift.append(f"the register accounts for {reg_tot:,} prime rows and "
                     f"the firm-year table for {con_tot:,}")
    return lg, drift


def led_published(reg, contr, pub):
    lg = RowLedger("individual_native_firm_contracts_published.csv",
                   "MEASURED (242 aggregates the firm-year table into cells "
                   "and writes one surrogate-only FIRM cell per register firm)",
                   "firm-year row (324) + register firm (45) - two grains, "
                   "each named in its disposition")
    lg.rows_in = len(contr) + len(reg)
    firm_cells = [r for r in pub if r.get("cell_type") == "FIRM"]
    agg_cells = [r for r in pub if r.get("cell_type") != "FIRM"]
    supp = sum(1 for r in pub
               if (r.get("value_suppressed_small_cell") or "") == "1")
    lg.note("emitted:firm_year_row_aggregated_into_the_year_agency_sector_"
            "state_and_setaside_cells", len(contr),
            f"{len(agg_cells)} aggregate cells written; {supp} of {len(pub)} "
            f"published cells carry value_suppressed_small_cell = 1 under the "
            f"fewer-than-3-firms rule, REPORTED with n_firms and a blank "
            f"value, never silently dropped")
    lg.note("emitted:register_firm_written_as_one_surrogate_only_FIRM_cell",
            len(firm_cells),
            "no name, no UEI, no state, no agency, no sector - 242's rule (a)")
    drift = []
    if len(firm_cells) != len(reg):
        drift.append(f"{len(reg)} register firms but {len(firm_cells)} FIRM "
                     f"cells")
    return lg, drift


def led_exclusions(reg, excl):
    lg = RowLedger("individual_native_exclusion_pairs.csv",
                   "MEASURED (refuses_tribal_link_not_native_ownership on the "
                   "register row is the flag that produces an exclusion)",
                   "register firm")
    lg.rows_in = len(reg)
    refuse = [r for r in reg
              if (r.get("refuses_tribal_link_not_native_ownership") or "")
              == "1"]
    lg.note("emitted:register_firm_carrying_refuses_tribal_link_not_native_"
            "ownership_written_as_an_exclusion", len(refuse),
            "; ".join(sorted(r["firm_surrogate_entity_id"] for r in excl)[:3]))
    lg.note("excluded:register_firm_asserts_no_tribal_link_that_would_need_"
            "refusing_so_it_has_nothing_to_exclude", len(reg) - len(refuse))
    drift = []
    if {r["firm_surrogate_entity_id"] for r in excl} != \
            {r["surrogate_entity_id"] for r in refuse}:
        drift.append("the set of firms with an exclusion row is not the set "
                     "flagged refuses_tribal_link_not_native_ownership")
    return lg, drift


# =====================================================================
# conserve / publish / verify
# =====================================================================
def build_ledgers():
    cand = read_csv(CAND_REL)
    verif = read_csv(VERIF_REL)
    prior = read_csv(PRIOR_REL)
    reg = read_csv(REG_REL)
    contr = read_csv(CONTR_REL)
    pub = read_csv(PUB_REL)
    excl = read_csv(EXCL_REL)

    ledgers, drift = [], []
    lg, n_prime, d = led_candidates(cand, prior)
    ledgers.append(lg)
    drift += d
    print(f"  read {n_prime:,} prime_contracts.csv transaction rows -> "
          f"{lg.rows_in:,} awardee keys")
    for fn, args in ((led_verification, (cand, verif)),
                     (led_register, (prior, reg)),
                     (led_contracts, (reg, contr)),
                     (led_published, (reg, contr, pub)),
                     (led_exclusions, (reg, excl))):
        lg, d = fn(*args)
        ledgers.append(lg)
        drift += d
    return ledgers, drift


def publish():
    """MERGE the durable ledger into the shared file. Never rewrite it."""
    local = read_csv(LEDGER_LOCAL_REL)
    if not local:
        print(f"  no {LEDGER_LOCAL_REL} - run `conserve` first")
        return 1
    ours = {r["source_table"] for r in local}
    keep = [r for r in read_csv(CONSERVATION_REL)
            if (r.get("source_table") or "") not in ours]
    write_csv(CONSERVATION_REL, keep + local, CONSERVATION_COLS)
    print(f"  merged {len(local)} disposition row(s) over {len(ours)} "
          f"{COLLECTION} table(s); {len(keep)} row(s) of other ledgers left "
          f"untouched")
    return 0


def cmd_conserve(args):
    if args.publish_only:
        return publish()
    print(f"=== 575 conserve: {COLLECTION} row conservation ===\n")
    ledgers, drift = build_ledgers()
    bad = [lg for lg in ledgers if lg.unaccounted()]
    for lg in bad:
        print(f"\n  CONSERVATION BREACH {lg.table}: {lg.rows_in:,} read, "
              f"{sum(lg.counts.values()):,} accounted, "
              f"{lg.unaccounted():,} unnamed")
    for d in drift:
        print(f"\n  DRIFT: {d}")
    if bad or drift:
        print("\n  nothing published - fix the ledger, not the file")
        return 1
    for lg in ledgers:
        print(f"\n  {lg.table}")
        print(f"      [{lg.evidence}]")
        print(f"      unit: {lg.unit}   |   {lg.rows_in:,} read")
        for disp, n in sorted(lg.counts.items(), key=lambda kv: -kv[1]):
            print(f"      {n:>9,}  {disp}")
    write_csv(LEDGER_LOCAL_REL, conservation_rows(ledgers), CONSERVATION_COLS)
    print(f"\n  wrote {LEDGER_LOCAL_REL}")
    return publish()


def cmd_verify(_args):
    fails = []
    by = defaultdict(list)
    for r in read_csv(CONSERVATION_REL):
        by[r.get("source_table") or ""].append(r)
    for t in CUSTOMER_TABLES:
        rs = by.get(f"{CLEAN}/{t}")
        if not rs:
            fails.append(
                f"C5 {t}: NO row-conservation coverage in {CONSERVATION_REL}. "
                f"If a wholesale rewrite of that shared file has run since, "
                f"the repair is: py -3 code/"
                f"575_closure_native_owned_businesses.py conserve "
                f"--publish-only")
            continue
        rows_in = int(rs[0]["rows_in"] or 0)
        total = sum(int(r["rows"] or 0) for r in rs)
        if total != rows_in:
            fails.append(f"C5 {t}: {rows_in:,} read but {total:,} accounted "
                         f"for - {abs(rows_in - total):,} vanished without a "
                         f"named disposition")
        for r in rs:
            if r["disposition"] == "UNACCOUNTED_FOR" and int(r["rows"] or 0):
                fails.append(f"C5 {t}: {r['rows']} UNACCOUNTED_FOR")
            if UNNAMED_REASON_RE.search(r["disposition"]):
                fails.append(f"C5 {t}: disposition {r['disposition']!r} is "
                             f"not a NAMED reason")
    print(f"=== 575 verify: {COLLECTION} C5 ===\n")
    if fails:
        for f in fails:
            print(f"  FAIL  {f}")
        return 1
    print(f"  C5 OK - all {len(CUSTOMER_TABLES)} customer tables have "
          f"row-conservation coverage and every read row has a named "
          f"disposition")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("conserve")
    c.add_argument("--publish-only", action="store_true",
                   help="re-merge the durable ledger without recomputing it")
    c.set_defaults(fn=cmd_conserve)
    v = sub.add_parser("verify")
    v.set_defaults(fn=cmd_verify)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
