#!/usr/bin/env python3
"""
Cedar Press - 1107: VERIFY THE PUNCH LIST'S OWN CLAIMS against the live files.

    py -3 code/1107_punchlist_claim_verify.py            measure + write report
    py -3 code/1107_punchlist_claim_verify.py verify     read-only, exit 1 on breach
    py -3 code/1107_punchlist_claim_verify.py selftest   prove verify FIRES

WHY THIS EXISTS
---------------
`code/526_dataset_standard.py` generates `docs/datasets/_PUNCHLIST.md`, and ten
agents work from it. Every line is an INSTRUCTION with a target, so a false line
is not a stale number - it is an instruction to damage the data.

526's `scan()` reads at most `cap = 20000` rows and then asserts, on that
sample, that a column is "always empty in 20,001 rows". Measured 2026-09-02
over the FULL files:

    prime_contracts.csv        10 of 10 "always empty" columns are FALSE.
                               contract_transaction_unique_key holds 841,002
                               non-blank values (69.1% of 1,217,768);
                               naics_code holds 838,229.
    federal_funding_...csv     16 of 18 FALSE (face_value_of_loan: 225,031)
    faads_..._all_agencies     3 of 7 FALSE (recipient_duns: 677,035)
    across the 13 capped tables: 43 of 65 claims FALSE (66%).

An agent that did what `prime_contracts.csv`'s line says - "drop 10 always-empty
column(s)" - would delete the contracting table's award keys and its NAICS.

This is the repo's signature defect in its most expensive form: the number was
produced, it was plausible, and it was about a 20,000-row prefix rather than the
file. See `docs/AGENT_FIELD_GUIDE.md` section 3, habit 3 - print the denominator
and the sample cap.

WHAT THIS FILE IS, AND IS NOT
-----------------------------
It is a GUARD, not a replacement. `526` is owned by the integrator
(`docs/ARCHITECTURE_DECISIONS.md` line 87: "Integrator owns 62, 503, 510, 512,
517, 518, 526, 527 and all commits."), so this pass does not edit it. The
correction to 526 is written out as an exact patch in
`docs/datasets/_PUNCHLIST_CLAIM_AUDIT.md` and is the integrator's to apply.

Until it is applied, THIS is what says which punch-list lines may be acted on.

WHAT IT VERIFIES, AND HOW
-------------------------
It imports `526` and calls its `build()` - so it audits the LIVE generator's
output, never the markdown, which is a snapshot. Four claim families, each
re-measured exactly:

  V1  C11 "always empty in N rows"
      Full-file recount with `csv.reader` over the named columns only, no cap.
      FALSE if any named column is non-blank on any row. Reports the TRUE row
      count and the true non-blank count.

  V2  C11 "not in any codebook"
      Exact set membership against `data/clean/codebook_master.csv`.

  V3  C5 "no conservation coverage"
      526 compares `source_table.split("/")[-1]` against the table name, but
      the established convention in `cedar_harvest_conservation.csv` is to
      QUALIFY the source in brackets -
      `data/clean/np_orgs.csv [IRS BMF rows via np_orgs own cedar_uid link...]`
      - which can never equal `np_orgs.csv`. So a dataset agent who adds
      conservation the way the file already does it does NOT close its punch
      item. FALSE if the table is covered once the bracketed qualifier is
      stripped.

  V4  C9 "no runbook"
      Exact file existence.

And it reports, as FINDINGS rather than breaches (they make C12 stricter, and
tightening a HIGH check under ten live agents is the integrator's call):

  F1  hollow C12 passes - the table has a name that matches the basis regex and
      that column is blank on most rows.
  F2  C12 passing on a FIELD-LEVEL provenance basis. `faads_transactions_all_
      agencies.csv` passes the inclusion-basis check because the string "tier"
      appears inside `geo_key_tier`, a county-geocoding confidence tier that
      says nothing about why the row is in Cedar.
  F3  a declared `population_scope` in `docs/schema/dataset_contracts.json`
      that C12 does not read - the table-level ADR-013 declaration is already
      written for 2 tables and is scored as absent.
  F4  shippable tables INVISIBLE to the standard: `scan()` returns an empty
      header on a zero-row or unreadable file, and every column check is then
      skipped, so the table produces no findings at all and looks clean.

BREACH = any V1-V4 false claim. `verify` exits 1 and names the invariant.

Writes  docs/datasets/_PUNCHLIST_CLAIM_AUDIT.md
        docs/datasets/_punchlist_claim_audit.json
"""
from __future__ import annotations

import csv
import importlib.util
import json
import re
import shutil
import sys
import tempfile
from collections import Counter
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()

OUT_MD = ROOT / "docs" / "datasets" / "_PUNCHLIST_CLAIM_AUDIT.md"
OUT_JSON = ROOT / "docs" / "datasets" / "_punchlist_claim_audit.json"

# 526's own cap, read from the module at run time where it exposes one.
DEFAULT_CAP = 20000

# A field-level provenance basis. These say how ONE FIELD was derived; none of
# them says why the ROW is in Cedar, which is what ADR-013 asks for.
PROVENANCE_BASIS = re.compile(
    r"^(geo_key_tier|geo_key_basis|date_basis|[a-z0-9]+_date_basis|"
    r"[a-z0-9_]*_date_tier)$", re.I)

RE_EMPTY = re.compile(r"^always empty in ([\d,]+) rows: (.+?)( \.\.\.)?$")
RE_CB = re.compile(r"^not in any codebook: (.+?)( \.\.\.)?$")


def load_526():
    spec = importlib.util.spec_from_file_location(
        "m526", str(HERE / "526_dataset_standard.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ---------------------------------------------------------------------------
# exact measurement helpers - no cap, no DictReader
# ---------------------------------------------------------------------------

def full_counts(path, cols):
    """Exact (n_rows, {col: non_blank}) over the WHOLE file.

    csv.reader with fixed indices: one pass, no dict per row, so 2.8M rows is
    cheap. A column named in `cols` that is not in the header comes back None,
    so the caller can say ABSENT rather than zero - a column that is not there
    is not a column that is empty.
    """
    idx, n = {}, 0
    cnt = {}
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.reader(fh)
        try:
            hdr = next(rd)
        except StopIteration:
            return 0, {c: None for c in cols}
        for c in cols:
            if c in hdr:
                idx[c] = hdr.index(c)
                cnt[c] = 0
        width = len(hdr)
        for row in rd:
            n += 1
            if len(row) < width:
                row = row + [""] * (width - len(row))
            for c, i in idx.items():
                if row[i].strip():
                    cnt[c] += 1
    return n, {c: cnt.get(c) for c in cols}


def conservation_keys(m):
    """The conservation table's coverage, as 526 reads it and as it is."""
    rows = m.read_csv(m.CONSERVATION)
    naive, strict = set(), set()
    for r in rows:
        s = (r.get("source_table") or "").strip()
        naive.add(s.split("/")[-1])
        strict.add(re.sub(r"\s*\[.*$", "", s).split("/")[-1])
    return naive, strict


# ---------------------------------------------------------------------------
# the audit
# ---------------------------------------------------------------------------

def audit(m):
    """Re-measure every checkable punch-list claim.

    Returns (items, breaches, findings, stats). Raises rather than returning a
    clean result it cannot support.
    """
    items = m.build()
    if not items:
        raise SystemExit("UNMEASURED: 526.build() returned no items - the "
                         "contracts file is missing or empty. A clean result "
                         "here would be an absence of evidence reported as "
                         "evidence of absence.")

    cb = {(r.get("variable") or r.get("column") or "").strip().lower()
          for r in m.read_csv(m.CODEBOOK)}
    cb.discard("")
    if not cb:
        raise SystemExit("UNMEASURED: codebook_master.csv is empty or missing. "
                         "526 silently drops EVERY C11 codebook item when this "
                         "set is empty (`if undoc and cb`), so the punch list "
                         "would look cleaner for the wrong reason.")

    naive_cons, strict_cons = conservation_keys(m)
    cap = getattr(m, "SCAN_CAP", DEFAULT_CAP)

    breaches, findings = [], []
    stats = Counter()

    for it in items:
        ds, pt, tbl, ev = it["dataset"], it["point"], it["table"], it["evidence"]

        if pt == "C11":
            mm = RE_EMPTY.match(ev)
            if mm:
                stats["V1_checked"] += 1
                claimed_rows = int(mm.group(1).replace(",", ""))
                p = m.table_path(tbl)
                if p is None:
                    breaches.append(dict(
                        invariant="V1", dataset=ds, table=tbl,
                        why="punch list names a table that is not on disk",
                        evidence=ev))
                    continue
                # The evidence line truncates the column list at four, so
                # re-derive the real candidate set from the live header the
                # same way 526 does. The audit is not limited by the prose.
                hdr, n_s, nn_s = m.scan(tbl)
                cand = [h for h in hdr if nn_s[h] == 0]
                n_true, cnt = full_counts(p, cand)
                false_cols = {c: v for c, v in cnt.items() if v}
                if false_cols:
                    stats["V1_false"] += 1
                    stats["V1_false_columns"] += len(false_cols)
                    breaches.append(dict(
                        invariant="V1", dataset=ds, table=tbl,
                        why=("'always empty' asserted from a "
                             + format(cap, ",") + "-row sample of a "
                             + format(n_true, ",") + "-row file"),
                        claimed_rows=claimed_rows,
                        true_rows=n_true,
                        claimed_empty=len(cand),
                        actually_empty=len(cand) - len(false_cols),
                        false_columns=dict(sorted(false_cols.items(),
                                                  key=lambda kv: -kv[1])),
                        evidence=ev))
                continue
            if RE_CB.match(ev):
                stats["V2_checked"] += 1
                hdr, _, _ = m.scan(tbl)
                undoc = [h for h in hdr if h.lower() not in cb]
                if not undoc:
                    stats["V2_false"] += 1
                    breaches.append(dict(
                        invariant="V2", dataset=ds, table=tbl,
                        why="every column IS in the codebook", evidence=ev))
                continue

        if pt == "C5":
            stats["V3_checked"] += 1
            if tbl in strict_cons and tbl not in naive_cons:
                stats["V3_false"] += 1
                breaches.append(dict(
                    invariant="V3", dataset=ds, table=tbl,
                    why=("conservation IS recorded, under a bracket-qualified "
                         "source_table that 526's split('/')[-1] cannot match"),
                    evidence=ev))
            continue

        if pt == "C9" and ev == "no runbook":
            stats["V4_checked"] += 1
            if (m.ROOT / "docs" / "datasets" / (ds + ".md")).exists():
                stats["V4_false"] += 1
                breaches.append(dict(invariant="V4", dataset=ds, table=tbl,
                                     why="the runbook exists", evidence=ev))
            continue

    # ---- F1..F4, findings ----------------------------------------------
    doc = json.loads(m.CONTRACTS.read_text(encoding="utf-8"))
    for coll in doc.get("contracts", []):
        cid = coll["collection"]
        for t in coll.get("tables", []):
            if t.get("status") != "shippable":
                continue
            name = t["table"]
            p = m.table_path(name)
            hdr, n, nn = m.scan(name)
            stats["tables_scored"] += 1

            if p is None or n == 0:
                stats["F4"] += 1
                findings.append(dict(
                    finding="F4", dataset=cid, table=name,
                    why=("shippable but INVISIBLE to the standard: "
                         + ("not on disk" if p is None else "zero rows")
                         + " - 526 skips every column check, so the table "
                           "produces no punch items at all"),
                    detail=""))
                continue

            hits = [h for h in hdr if m.BASIS_RE.search(h or "")]
            if hits:
                best = max(nn[h] / n for h in hits)
                if best < 0.5:
                    stats["F1"] += 1
                    findings.append(dict(
                        finding="F1", dataset=cid, table=name,
                        why="C12 PASSES on a basis column that is mostly blank",
                        detail=", ".join(h + " filled " + str(nn[h]) + "/"
                                         + str(n) for h in hits)))
                if not [h for h in hits if not PROVENANCE_BASIS.match(h)]:
                    stats["F2"] += 1
                    findings.append(dict(
                        finding="F2", dataset=cid, table=name,
                        why=("C12 PASSES only on a FIELD-level provenance "
                             "basis, which is not an inclusion basis"),
                        detail=", ".join(hits)))
            elif t.get("population_scope"):
                stats["F3"] += 1
                findings.append(dict(
                    finding="F3", dataset=cid, table=name,
                    why=("population_scope IS declared in "
                         "dataset_contracts.json and C12 does not read it"),
                    detail=json.dumps(t["population_scope"])[:300]))

    return items, breaches, findings, stats


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------

def write_report(items, breaches, findings, stats):
    by_inv = Counter(b["invariant"] for b in breaches)
    L = ["# Punch-list claim audit", "",
         "*Generated " + TODAY + " by `code/1107_punchlist_claim_verify.py`. "
         "It imports `code/526_dataset_standard.py` and re-measures its output "
         "against the live files with **no row cap**. `526` is "
         "integrator-owned; this file does not edit it.*", "",
         "**" + str(len(items)) + " punch items. " + str(len(breaches))
         + " carry a FALSE claim. " + str(len(findings))
         + " findings on the checks themselves.**", "",
         "| invariant | what it re-measures | false claims |",
         "|---|---|---:|",
         "| V1 | C11 *always empty in N rows*, full-file recount | **"
         + str(by_inv["V1"]) + "** |",
         "| V2 | C11 *not in any codebook*, exact set membership | "
         + str(by_inv["V2"]) + " |",
         "| V3 | C5 *no conservation coverage*, bracket qualifier stripped | **"
         + str(by_inv["V3"]) + "** |",
         "| V4 | C9 *no runbook*, file existence | " + str(by_inv["V4"]) + " |",
         "",
         "V1 checked " + str(stats["V1_checked"]) + " items and found **"
         + str(stats["V1_false_columns"]) + "** individual column claims "
         "false.", ""]

    if breaches:
        L += ["## FALSE CLAIMS — do not act on these punch-list lines", ""]
        for b in sorted(breaches, key=lambda x: (x["invariant"], x["dataset"])):
            L.append("### `" + b["table"] + "` — " + b["dataset"] + " — "
                     + b["invariant"])
            L.append("")
            L.append("- punch list says: *" + b["evidence"] + "*")
            L.append("- why it is false: " + b["why"])
            if "true_rows" in b:
                L.append("- true row count: **" + format(b["true_rows"], ",")
                         + "** (the line says "
                         + format(b["claimed_rows"], ",") + ")")
                L.append("- of " + str(b["claimed_empty"]) + " columns called "
                         "always empty, **" + str(b["actually_empty"])
                         + "** are")
                L.append("- non-blank counts over the full file:")
                for c, v in b["false_columns"].items():
                    L.append("  - `" + c + "` — **" + format(v, ",")
                             + "** non-blank")
            L.append("")

    if findings:
        L += ["## Findings on the checks themselves", "",
              "*Not breaches. Each would make a check STRICTER, and C12 is a "
              "HIGH-severity check ten agents are working from, so retuning it "
              "is the integrator's call, not this pass's.*", "",
              "| finding | dataset | table | why |", "|---|---|---|---|"]
        for f in sorted(findings, key=lambda x: (x["finding"], x["dataset"])):
            L.append("| " + f["finding"] + " | `" + f["dataset"] + "` | `"
                     + f["table"] + "` | " + f["why"] + " |")
        L.append("")

    L += ["## The patch `526` needs (integrator)", "",
          "```python",
          "# 1. C5 - strip the bracket qualifier before comparing (V3).",
          "cons_tables = {re.sub(r'\\s*\\[.*$', '', (r.get('source_table')"
          " or '')).split('/')[-1]",
          "               for r in read_csv(CONSERVATION)}",
          "",
          "# 2. C11 - never assert 'always empty' from the capped pass (V1).",
          "#    scan() stops at cap=20000; recount the candidates on the FULL",
          "#    file before writing an instruction to DROP a column.",
          "empty_cand = [h for h in hdr if nn[h] == 0]",
          "if empty_cand and n > CAP:",
          "    n, empty = full_counts(table_path(name), empty_cand)",
          "else:",
          "    empty = empty_cand",
          "",
          "# 3. refuse to report a clean result you did not measure.",
          "if not cb:",
          "    raise SystemExit('UNMEASURED: codebook_master.csv is empty')",
          "if n == 0:",
          "    add(cid, 'C0', 'high', name, 'zero rows or unreadable - every "
          "column check was SKIPPED', 'table invisible to the standard')",
          "",
          "# 4. verify must exit non-zero. Today main() returns 0 always,",
          "#    so `526 verify` cannot fail and is not a gate.",
          "```", ""]
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(L), encoding="utf-8")
    OUT_JSON.write_text(json.dumps(
        dict(generated=TODAY, n_items=len(items), breaches=breaches,
             findings=findings, stats=dict(stats)), indent=1), encoding="utf-8")


# ---------------------------------------------------------------------------
# selftest - a fixture that PROVES the check fires, in both directions
# ---------------------------------------------------------------------------

def _fixture(tmp, late_filler, bracket_conservation):
    """Build a complete synthetic tree for 526 to be pointed at."""
    clean = tmp / "data" / "clean"
    clean.mkdir(parents=True, exist_ok=True)
    (tmp / "docs" / "schema").mkdir(parents=True, exist_ok=True)
    (tmp / "docs" / "datasets").mkdir(parents=True, exist_ok=True)

    # A table WIDER than the cap. `truly_empty` is blank on every row;
    # `late_filler` is blank for the first 20,000 rows and filled after - the
    # exact shape that made 526 call prime_contracts' award keys empty.
    with open(clean / "zz_wide.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["row_id", "inclusion_basis", "truly_empty", "late_filler"])
        for i in range(20050):
            w.writerow([i, "term_match", "",
                        "X" if (late_filler and i >= 20000) else ""])

    with open(clean / "zz_covered.csv", "w", encoding="utf-8",
              newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["row_id", "inclusion_basis", "documented_col"])
        w.writerow([1, "term_match", "v"])

    src = ("data/clean/zz_covered.csv [a qualifier 526 cannot parse]"
           if bracket_conservation else "data/clean/zz_covered.csv")
    with open(clean / "cedar_harvest_conservation.csv", "w", encoding="utf-8",
              newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["source_table", "rows_in", "disposition", "rows"])
        w.writerow([src, 1, "kept", 1])
        w.writerow(["data/clean/zz_wide.csv", 20050, "kept", 20050])

    with open(clean / "codebook_master.csv", "w", encoding="utf-8",
              newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["dataset", "variable", "description"])
        for v in ("row_id", "inclusion_basis", "truly_empty", "late_filler",
                  "documented_col"):
            w.writerow(["zz", v, "d"])

    contracts = dict(contracts=[dict(
        collection="zz", name="zz", shelf="x", rebuild_command="", n_tables=2,
        tables=[dict(table="zz_wide.csv", status="shippable",
                     grain="one row per row_id", primary_key=["row_id"],
                     population_scope={}),
                dict(table="zz_covered.csv", status="shippable",
                     grain="one row per row_id", primary_key=["row_id"],
                     population_scope={})])])
    (tmp / "docs" / "schema" / "dataset_contracts.json").write_text(
        json.dumps(contracts), encoding="utf-8")
    (tmp / "docs" / "datasets" / "zz.md").write_text("runbook",
                                                     encoding="utf-8")


def _point(m, tmp):
    m.ROOT = tmp
    m.CONTRACTS = tmp / "docs" / "schema" / "dataset_contracts.json"
    m.SAFETY = tmp / "data" / "clean" / "cedar_export_safety.csv"
    m.READINESS = tmp / "data" / "clean" / "cedar_dataset_readiness.csv"
    m.CONSERVATION = tmp / "data" / "clean" / "cedar_harvest_conservation.csv"
    m.CODEBOOK = tmp / "data" / "clean" / "codebook_master.csv"


def selftest():
    ok = True

    def case(label, late_filler, bracket, expect_v1, expect_v3):
        nonlocal ok
        tmp = Path(tempfile.mkdtemp(prefix="cedar1107_"))
        try:
            _fixture(tmp, late_filler, bracket)
            m = load_526()
            _point(m, tmp)
            items, breaches, findings, stats = audit(m)
            v1 = sum(1 for b in breaches if b["invariant"] == "V1")
            v3 = sum(1 for b in breaches if b["invariant"] == "V3")
            rc = 1 if breaches else 0
            want_rc = 1 if (expect_v1 or expect_v3) else 0
            good = (v1 == expect_v1 and v3 == expect_v3 and rc == want_rc)
            print("  [" + ("PASS" if good else "FAIL") + "] " + label)
            print("         V1=" + str(v1) + " (want " + str(expect_v1)
                  + ")  V3=" + str(v3) + " (want " + str(expect_v3)
                  + ")  exit=" + str(rc) + " (want " + str(want_rc) + ")")
            if not good:
                ok = False
                for b in breaches:
                    print("          ", b["invariant"], b["table"], b["why"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    print("selftest - a check that has never failed on purpose is not known "
          "to work.")
    print()
    print(" injected violations:")
    case("V1 fires: a column blank for 20,000 rows then filled; "
         "V3 fires: conservation recorded with a bracket qualifier",
         True, True, 1, 1)
    print()
    print(" violations removed:")
    case("silent: the column really is empty everywhere, conservation "
         "recorded unqualified", False, False, 0, 0)
    print()
    print(" the UNMEASURED guard:")
    tmp = Path(tempfile.mkdtemp(prefix="cedar1107u_"))
    try:
        _fixture(tmp, False, False)
        (tmp / "data" / "clean" / "codebook_master.csv").write_text(
            "dataset,variable,description\n", encoding="utf-8")
        m = load_526()
        _point(m, tmp)
        try:
            audit(m)
            print("  [FAIL] an empty codebook returned a result instead of "
                  "raising")
            ok = False
        except SystemExit as e:
            good = "UNMEASURED" in str(e)
            print("  [" + ("PASS" if good else "FAIL") + "] empty codebook "
                  "raises UNMEASURED rather than reporting clean")
            ok = ok and good
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    print("SELFTEST " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


# ---------------------------------------------------------------------------

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "measure"
    if mode == "selftest":
        return selftest()

    m = load_526()
    items, breaches, findings, stats = audit(m)

    print("  punch-list claim audit   " + str(len(items)) + " items scored")
    print("                           " + str(len(breaches))
          + " FALSE claims, " + str(len(findings)) + " findings")
    by = Counter(b["invariant"] for b in breaches)
    for inv, label in (("V1", "C11 always-empty (full-file recount)"),
                       ("V2", "C11 not-in-codebook"),
                       ("V3", "C5 no-conservation (bracket-qualified)"),
                       ("V4", "C9 no-runbook")):
        print("      " + inv + "  " + str(by[inv]).rjust(3) + " false   "
              + label)
    print("      false COLUMN claims: " + str(stats["V1_false_columns"]))
    for f in ("F1", "F2", "F3", "F4"):
        print("      " + f + "  " + str(stats[f]).rjust(3) + " findings")
    print()

    if mode != "verify":
        write_report(items, breaches, findings, stats)
        print("  wrote docs/datasets/_PUNCHLIST_CLAIM_AUDIT.md")
        print("  wrote docs/datasets/_punchlist_claim_audit.json")
        return 0

    if breaches:
        print("BREACH - the punch list carries claims that are false against "
              "the live files.")
        for b in sorted(breaches, key=lambda x: x["invariant"])[:12]:
            print("   " + b["invariant"] + "  " + b["dataset"].ljust(22) + " "
                  + b["table"])
            print("        " + b["why"])
        print()
        print("Do not act on those lines. See "
              "docs/datasets/_PUNCHLIST_CLAIM_AUDIT.md")
        return 1
    print("clean - every checkable punch-list claim re-measured true.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
