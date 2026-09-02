#!/usr/bin/env python3
"""
Cedar Press - 1137: TWELVE datasets, twelve spreadsheets. One each.

    py -3 code/1137_customer_dataset_combine.py            # plan, writes nothing
    py -3 code/1137_customer_dataset_combine.py build
    py -3 code/1137_customer_dataset_combine.py verify

WHY THIS EXISTS
---------------
Owner, 2026-09-02: *"What do you mean three hundred plus spreadsheets? It's
supposed to be twelve. I don't know what you have to do to combine and
correlate them, but that's the point."*

He is right and `1135` answered the wrong question. It published Cedar's 294
INTERNAL TABLES, organised by collection - which is Cedar's filing system, not
a product. A customer buys **Federal Funding to Indian Country** and expects a
spreadsheet called that, not twenty tables to join themselves. **The combining
is the product.** If the buyer has to do it, we sold them a filing cabinet.

The twelve, from `shelf` in `500_build_architecture_map.py`:

    standard  funding · federal-register · legislation · deals · nagpra · lobbying
    pro       contractors · subcontracting · native-owned-businesses · nest ·
              natural-resources · nonprofits

`gaming` is shelf `grove` and belongs to Cedar Grove. `_entity_layer` is
infrastructure. `newsletters` was withdrawn by owner ruling on 2026-09-02.

THE ONE RULE THAT MAKES A JOIN SAFE
------------------------------------
**The flagship's row count may not change.** A LEFT JOIN onto a table with more
than one row per key does not enrich the flagship, it MULTIPLIES it - and when
the multiplied rows carry money, every total downstream is silently wrong. This
project has already paid for that lesson once: the unfiltered `subaward_amount`
runs **86.9% above** the correct figure (the filter removes $21.21B; 86.9% is
of the correct $24.41B, not the inflated $45.62B).

So a supporting table is folded in only when the contracts file has MEASURED
its cardinality on the shared key as one. That is not a guess: `1137` reads
`join_cardinality` and `measured_rows_per_join_key` out of
`docs/schema/dataset_contracts.json`, which carry the grain sweep's evidence.
Anything one-to-many is NOT joined - it contributes a count column instead, so
the buyer still learns "this award has 4 subawards" without the row being
duplicated four times.

And then it is checked anyway. After every join the row count is compared to
the flagship's, and a join that moved it is REVERTED, not reported. A rule that
is only documented is a rule that will be broken by the next writer.

WHAT A COLUMN IS ALLOWED TO BE
-------------------------------
Joined columns are prefixed with their source table's stem, because two tables
both calling something `state` and silently overwriting each other is how the
identifier ledger came to hold UEIs in `state` on 12,127 rows.

Columns that are blank on every row after the join are KEPT and NAMED in the
manifest as sparse. `770` rule 6 learned this the hard way: dropping all-blank
columns made the schema depend on which rows were sampled, and a buyer diffing
two deliveries watched columns appear and vanish. Sparsity is a fact about
coverage, not something to hide by deleting the column.

WHAT THIS DOES NOT DO
---------------------
It does not invent a row, a column, or a value; every cell comes from a Cedar
table. It does not drop a row for being awkward - withheld rows are `1135`'s
publication gates, applied identically here and counted per dataset. And it
does not claim a dataset is finished: a collection whose flagship is missing
gets a manifest line saying so rather than an empty file that looks complete.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()
CLEAN = ROOT / "data" / "clean"
SPINE = ROOT / "data" / "spine"
OUT = ROOT / "dist" / "customer"
CONTRACTS = ROOT / "docs" / "schema" / "dataset_contracts.json"

GITHUB_BYTES = 95 * 1024 * 1024
EXCEL_ROWS = 1_048_576
# WORKBOOK_MAX_ROWS is gone. It capped workbooks at 200,000 rows on my
# judgement about what someone would want to open, and the effect was that two
# of twelve datasets silently had no workbook. XLSX caps a SHEET, not a
# WORKBOOK; a big dataset spans several Data sheets in one file.
YEAR_COLS = ("fiscal_year", "fy", "action_date_fiscal_year", "award_fiscal_year",
             "year", "report_year", "filing_year")

# Shelves a paying customer sees. `grove` goes to Cedar Grove, `infrastructure`
# is the hub, `withdrawn` is the owner's newsletters ruling of 2026-09-02.
CUSTOMER_SHELVES = ("standard", "pro")

DROP_COLS = ("casino_city_id", "duns", "duns_number", "dnb_duns",
             "ultimate_duns", "parent_duns")


def _from(mod: str, name: str):
    """Read a constant out of another numbered script by text.

    A module whose name begins with a digit is not importable, and restating a
    safety rule creates a second copy that drifts - the drifting copy always
    being the one that ships.
    """
    src = ROOT / "code" / mod
    if not src.exists():
        return None
    txt = src.read_text(encoding="utf-8", errors="replace")
    # `COLLECTIONS: list[dict] = [` - the annotation is part of the binding and
    # the first version of this pattern did not allow for it, so `shelves()`
    # returned {} and the build reported "0 customer shelves" instead of
    # failing. A lookup that silently finds nothing is worse than one that
    # raises, which is why the caller now refuses to build on an empty map.
    m = re.search(rf"^{name}\s*(?::[^=\n]+)?=\s*", txt, re.M)
    if not m:
        return None
    i, depth, j = m.end(), 0, m.end()
    while j < len(txt):
        if txt[j] in "([{":
            depth += 1
        elif txt[j] in ")]}":
            depth -= 1
            if depth == 0:
                j += 1
                break
        j += 1
    try:
        import ast
        return ast.literal_eval(txt[i:j])
    except Exception:
        return None


NEVER = _from("770_sample_extracts.py", "NEVER")
GATES = _from("770_sample_extracts.py", "GATES")
FLAGSHIP = _from("770_sample_extracts.py", "FLAGSHIP")
if not (NEVER and GATES and FLAGSHIP):
    print("  REFUSING TO BUILD: could not read NEVER/GATES/FLAGSHIP out of 770.\n"
          "  Those are the publication rules and the curated flagship choice.\n"
          "  Restating them here would put a second copy in the tree.",
          file=sys.stderr)
    raise SystemExit(2)


def contracts():
    d = json.loads(CONTRACTS.read_text(encoding="utf-8"))
    return {c["collection"]: c for c in d.get("contracts", [])}


def shelves():
    """collection -> shelf, read out of 500's declared map.

    Refuses to return an empty map. The first version's regex could not match
    the annotated binding `COLLECTIONS: list[dict] = [`, so this returned {},
    every collection failed the shelf test, and the build printed "0 customer
    shelves" and exited 0 - a clean, confident report of nothing. That is the
    defect this project keeps paying for, so an empty map is now fatal.
    """
    cols = _from("500_build_architecture_map.py", "COLLECTIONS") or []
    out = {c["id"]: c.get("shelf") for c in cols}
    if not out:
        print("  REFUSING TO BUILD: could not read COLLECTIONS out of 500.\n"
              "  The shelf assignment decides which datasets a customer sees.\n"
              "  Guessing it would ship the wrong storefront.", file=sys.stderr)
        raise SystemExit(2)
    return out


def find(name):
    for d in (CLEAN, SPINE):
        p = d / name
        if p.exists():
            return p
    return None


def row_ok(r):
    for col, allowed in GATES.items():
        if col in r and (r.get(col) or "").strip() not in allowed:
            return False, col
    for col in NEVER:
        if col in r and (r.get(col) or "").strip():
            return False, "personal:" + col
    return True, ""


def load(path, gate=True):
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        hdr = [c for c in (rd.fieldnames or []) if c.lower() not in DROP_COLS]
        rows, held = [], defaultdict(int)
        for r in rd:
            if gate:
                ok, why = row_ok(r)
                if not ok:
                    held[why] += 1
                    continue
            rows.append({c: r.get(c, "") for c in hdr})
    return hdr, rows, held


def one_per_key(meta, key):
    """Has the grain sweep MEASURED at most one row per this key?"""
    if (meta.get("join_cardinality") or {}).get(key) != "one":
        return False
    m = (meta.get("measured_rows_per_join_key") or {}).get(key)
    return m is not None and float(m) <= 1.0


def write_csv(path, cols, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return path.stat().st_size


def profile(cols, rows):
    """Per-column fill rate and a few honest stats. No inference."""
    out = []
    n = len(rows) or 1
    for c in cols:
        # Coerce rather than assume. A single non-string cell anywhere in a
        # 1.2M-row table crashed the whole build after six minutes of work.
        vals = [str(r.get(c) or "").strip() for r in rows]
        filled = [v for v in vals if v]
        nums = []
        if filled and len(filled) > 20:
            probe = filled[:2000]
            ok = 0
            for v in probe:
                try:
                    float(v.replace(",", "").replace("$", ""))
                    ok += 1
                except ValueError:
                    pass
            if ok / len(probe) > 0.95:
                for v in filled:
                    try:
                        nums.append(float(v.replace(",", "").replace("$", "")))
                    except ValueError:
                        pass
        d = {"column": c, "filled": len(filled),
             "fill_pct": round(100 * len(filled) / n, 1),
             "distinct": len(set(filled)), "example": (filled[0][:60] if filled else "")}
        if nums:
            d["min"], d["max"] = f"{min(nums):,.2f}", f"{max(nums):,.2f}"
            d["sum"] = f"{sum(nums):,.2f}"
        out.append(d)
    return out


def known_issues(coll):
    """Quirks for this dataset, lifted from docs/KNOWN_ISSUES.md by mention."""
    p = ROOT / "docs" / "KNOWN_ISSUES.md"
    if not p.exists():
        return []
    hits = []
    for block in p.read_text(encoding="utf-8", errors="replace").split("\n## "):
        if coll.replace("-", " ") in block.lower() or coll in block.lower():
            hits.append(block.strip().splitlines()[0][:160])
    return hits[:8]


def codebook(coll, c, fname, fmeta, cols, rows, prof, joined, refused, held):
    """The agent-facing note the owner asked for: sources, quirks, variables.

    Owner, 2026-09-02: *"each of these single datasets should probably have a
    markdown for agents working on them, updating them. All the sources, the
    quirks, things like that."* And separately: *"notes, what variables read,
    maybe several stats"* - explicitly NOT the full methodology paper, which is
    a different document per dataset.

    Generated from the same pass that writes the data, so the two cannot drift.
    A hand-maintained note describing a moving table is the defect `500` exists
    to prevent, and it would be worse here: this one has the buyer's name on it.
    """
    L = []
    A = L.append
    A(f"# {c.get('name', coll)}")
    A("")
    A(f"**Dataset id** `{coll}` · **shelf** `{c.get('shelf','')}` · "
      f"**last built** {TODAY}")
    A("")
    A("> Generated by `code/1137_customer_dataset_combine.py` on every build. "
      "Do not hand-edit — the next build overwrites it. Fix the source table "
      "or the builder instead.")
    A("")
    A("## What one row is")
    A("")
    A(fmeta.get("grain") or "_Grain not declared in dataset_contracts.json._")
    A("")
    A(f"`{len(rows):,}` rows × `{len(cols)}` columns. Flagship table: "
      f"`{fname}`.")
    A("")
    A("## Where it comes from")
    A("")
    if joined:
        A("Folded in one-to-one (measured cardinality, not assumed):")
        A("")
        for j in joined:
            A(f"- `{j}`")
    else:
        A("_No supporting table met the one-to-one test; this is the flagship "
          "table alone._")
    A("")
    if refused:
        A("Counted, **not** joined — these are one-to-many on the shared key, "
          "so joining them would multiply the rows and inflate every money "
          "total. Each contributes a count column instead:")
        A("")
        for r in refused:
            A(f"- `{r}`")
        A("")
    A("## Quirks to know before you use it")
    A("")
    ki = known_issues(coll)
    if held:
        A(f"- **{sum(held.values()):,} rows withheld** from publication: "
          + ", ".join(f"`{k}`={v:,}" for k, v in sorted(held.items()))
          + ". These are the standing publication gates (unpublishable rows, "
            "restrictive source terms, personal data held apart from a public "
            "role) — not a data-quality trim.")
    sparse = [p["column"] for p in prof if p["filled"] == 0]
    if sparse:
        A(f"- **{len(sparse)} columns are empty on every row** and are kept "
          f"deliberately: {', '.join('`'+s+'`' for s in sparse[:12])}"
          + (" …" if len(sparse) > 12 else "")
          + ". Dropping blank columns would make the schema depend on which "
            "rows shipped, and a buyer diffing two deliveries would watch "
            "columns appear and vanish. Sparsity is a coverage fact.")
    thin = [p["column"] for p in prof if 0 < p["fill_pct"] < 10]
    if thin:
        A(f"- **{len(thin)} columns are under 10% populated** — real, but do "
          f"not build a headline on them: "
          f"{', '.join('`'+s+'`' for s in thin[:10])}"
          + (" …" if len(thin) > 10 else "") + ".")
    for k in ki:
        A(f"- {k}")
    if not (held or sparse or thin or ki):
        A("_No withheld rows, no empty columns, nothing open in KNOWN_ISSUES._")
    A("")
    A("## Variables")
    A("")
    A("| column | filled | fill % | distinct | example | min | max | sum |")
    A("|---|---:|---:|---:|---|---:|---:|---:|")
    for p in prof:
        ex = (p["example"] or "").replace("|", "\\|")
        A(f"| `{p['column']}` | {p['filled']:,} | {p['fill_pct']} | "
          f"{p['distinct']:,} | {ex} | {p.get('min','')} | {p.get('max','')} | "
          f"{p.get('sum','')} |")
    A("")
    A("## For the agent updating this dataset")
    A("")
    A(f"- Rebuild: `py -3 code/1137_customer_dataset_combine.py build`")
    A(f"- Check freshness: `py -3 code/1137_customer_dataset_combine.py verify` "
      f"— fails if any source table is newer than this spreadsheet.")
    A(f"- Rebuild the sources first: `{c.get('rebuild_command','(not declared)')}`")
    A("- A **sum** in the table above is the raw column total. It is NOT "
      "necessarily the dataset's money answer — filters and de-duplication "
      "rules live in the methodology paper, and the unfiltered subaward total "
      "runs 86.9% above the correct one.")
    (OUT / f"{coll}__CODEBOOK.md").write_text("\n".join(L) + "\n",
                                              encoding="utf-8")


def _wrap(text, width=78):
    import textwrap
    return textwrap.wrap(text, width) or [""]


def notes(coll, c, fname, fmeta, cols, rows, prof, joined, refused, held):
    """Plain-text and PDF notes beside the CSV. NO XLSX, deliberately.

    Owner, 2026-09-02: *"if CSVs are less error prone because we can have as
    much as we want rows wise, or also they don't do weird things with numbers
    or dates, then we should just offer a CSV and then offer separately a text
    file or PDF of the notes to the dataset."*

    That is the right call and it retires the workbook entirely. Excel is not a
    neutral container: it drops the leading zero from a zip code or a CAGE,
    reads `3-10` as a date, renders a long identifier in scientific notation,
    and converts URL-shaped cells to hyperlinks until it hits a 65,530-link cap
    and silently stops. Every one of those had to be defended against by hand
    in the version this replaces, and the last of them was found only because a
    warning happened to be printed. CSV does none of them and has no row
    ceiling, so the data ships as CSV and the notes ship as their own files.

    Per dataset:
        <id>.csv            the data - complete, no ceiling, no coercion
        <id>__CODEBOOK.md   agent-facing note (sources, quirks, variables)
        <id>__NOTES.txt     the same for a person, plain text
        <id>__NOTES.pdf     the same, typeset, for someone sent a file

    Not the methodology paper - that is a separate per-dataset document. This
    is what a buyer wants open beside the spreadsheet.
    """
    L = []
    A = L.append
    title = c.get("name", coll)
    A(title.upper())
    A("=" * len(title))
    A("")
    A(f"Dataset id     {coll}")
    A(f"Shelf          {c.get('shelf', '')}")
    A(f"Last updated   {TODAY}")
    A(f"Rows           {len(rows):,}")
    A(f"Columns        {len(cols)}")
    A(f"Data file      {coll}.csv")
    A("")
    A("WHAT ONE ROW IS")
    A("-" * 15)
    L.extend(_wrap(fmeta.get("grain") or "Grain not declared."))
    A("")
    A("WHERE IT COMES FROM")
    A("-" * 19)
    A(f"Flagship table: {fname}")
    if joined:
        A("")
        A("Folded in one-to-one (cardinality measured, not assumed):")
        for x in joined:
            A(f"  - {x}")
    if refused:
        A("")
        L.extend(_wrap("Counted but NOT joined. These are one-to-many on the "
                       "shared key, so joining them would multiply the rows "
                       "and inflate every money total. Each contributes a "
                       "count column instead:"))
        for x in refused:
            A(f"  - {x}")
    A("")
    A("BEFORE YOU USE IT")
    A("-" * 17)
    if held:
        L.extend(_wrap(f"{sum(held.values()):,} rows are withheld from "
                       "publication ("
                       + ", ".join(f"{k}={v:,}" for k, v in sorted(held.items()))
                       + "). These are the standing publication gates, not a "
                         "data-quality trim."))
        A("")
    sparse = [q["column"] for q in prof if q["filled"] == 0]
    if sparse:
        L.extend(_wrap(f"{len(sparse)} columns are empty on every row and are "
                       "kept deliberately - dropping blank columns would make "
                       "the schema depend on which rows shipped: "
                       + ", ".join(sparse[:15])))
        A("")
    thin = [q["column"] for q in prof if 0 < q["fill_pct"] < 10]
    if thin:
        L.extend(_wrap(f"{len(thin)} columns are under 10% populated - real, "
                       "but do not build a headline on them: "
                       + ", ".join(thin[:12])))
        A("")
    L.extend(_wrap("A column total is the raw sum of that column. It is NOT "
                   "necessarily this dataset's money answer - filters and "
                   "de-duplication rules live in the methodology paper. The "
                   "unfiltered subaward total runs 86.9% above the correct "
                   "one."))
    A("")
    A("COLUMNS")
    A("-" * 7)
    A(f"{'column':<38}{'filled':>10}{'fill%':>8}{'distinct':>10}")
    for q in prof:
        A(f"{q['column'][:37]:<38}{q['filled']:>10,}{q['fill_pct']:>8}"
          f"{q['distinct']:>10,}")

    (OUT / f"{coll}__NOTES.txt").write_text("\n".join(L) + "\n",
                                            encoding="utf-8")

    try:
        from reportlab.lib.pagesizes import LETTER
        from reportlab.lib.units import inch
        from reportlab.pdfgen import canvas as _canvas
    except ImportError as e:
        return "", f"reportlab unavailable ({e}); .txt and .md notes complete"

    path = OUT / f"{coll}__NOTES.pdf"
    cv = _canvas.Canvas(str(path), pagesize=LETTER)
    W, H = LETTER
    x, y, lead = 0.75 * inch, H - 0.85 * inch, 11.0
    cv.setTitle(f"{title} - dataset notes")
    for line in L:
        if y < 0.8 * inch:
            cv.showPage()
            y = H - 0.85 * inch
        heavy = (line and (set(line) <= {"=", "-"} or line == line.upper()
                           and any(ch.isalpha() for ch in line)))
        cv.setFont("Courier-Bold" if heavy else "Courier", 8)
        cv.drawString(x, y, line[:112])
        y -= lead
    cv.save()
    return path.name, ""


def emit(coll, cols, rows, flag_path):
    """ONE dataset, ONE spreadsheet. No splitting, ever.

    Owner, 2026-09-02: *"There's no splitting by year. That's stupid. You can
    have years in the same dataset as a variable. In fact, all these are
    multiple years. They can still be - and should be - a single spreadsheet."*

    He is right and the earlier version had the reasoning backwards. Fiscal
    year is a COLUMN. Splitting on it does not make the dataset smaller, it
    makes it twenty-seven datasets, and then the buyer's first act is to
    concatenate them back - which is the same failure as shipping 294 internal
    tables, one level down. A dataset the customer has to reassemble is not a
    finished product.

    The size limits are real and they are DELIVERY-FORMAT problems, not
    reasons to fragment the data:

      * Excel stops at 1,048,576 rows. `contractors` has 1,217,768. Excel is
        one reader among many and every other one - R, Stata, pandas, DuckDB,
        Power BI - reads the whole file. The row cap is a property of a
        spreadsheet application, not of a spreadsheet.
      * GitHub refuses a file over 100 MB. That is an argument about where the
        file is HOSTED, answered by release assets or object storage, not by
        cutting the dataset into pieces.

    So this writes one file and reports its true size. `MANIFEST.csv` names any
    dataset that exceeds either limit, so the fact is visible instead of being
    silently engineered around.
    """
    n_bytes = write_csv(OUT / f"{coll}.csv", cols, rows)
    over = []
    if len(rows) > EXCEL_ROWS:
        over.append(f"{len(rows):,} rows exceeds Excel's {EXCEL_ROWS:,}")
    if n_bytes > GITHUB_BYTES:
        over.append(f"{n_bytes/1e6:,.0f} MB exceeds GitHub's 100 MB")
    return 1, n_bytes, ("single" if not over else "single; " + "; ".join(over))


def build(dry: bool) -> int:
    cs, sh = contracts(), shelves()
    customer = [c for c in cs if sh.get(c) in CUSTOMER_SHELVES]
    man = []
    print(f"  1137 customer datasets   {'PLAN' if dry else 'BUILD'}")
    print(f"    customer shelves : {len(customer)}  "
          f"({', '.join(sorted(customer))})\n")

    for coll in sorted(customer):
        c = cs[coll]
        fname = FLAGSHIP.get(coll)
        fpath = find(fname) if fname else None
        if not fpath:
            man.append({"dataset": coll, "note": f"flagship {fname} absent"})
            print(f"    {coll:<26} FLAGSHIP MISSING ({fname})")
            continue

        fhdr, frows, fheld = load(fpath)
        n0 = len(frows)
        meta = {t["table"]: t for t in c.get("tables", [])}
        fmeta = meta.get(fname, {})
        fkeys = [k for k in (fmeta.get("key_columns") or []) if k in fhdr]

        joined, refused, added_cols = [], [], 0
        if not dry:
            for tname, tmeta in sorted(meta.items()):
                if tname == fname or tmeta.get("status") != "shippable":
                    continue
                tpath = find(tname)
                if not tpath:
                    continue
                key = next((k for k in fkeys
                            if k in (tmeta.get("key_columns") or [])), None)
                if not key:
                    continue
                if not one_per_key(tmeta, key):
                    # One-to-many. Joining would MULTIPLY the flagship, so the
                    # buyer gets a count instead of a duplicated row.
                    thdr, trows, _ = load(tpath)
                    if key not in thdr:
                        continue
                    cnt = defaultdict(int)
                    for r in trows:
                        cnt[(r.get(key) or "").strip()] += 1
                    col = f"n_{tpath.stem}"
                    for r in frows:
                        # str, not int. Every other cell in these dicts is a
                        # string read out of a CSV, and a lone int made
                        # `profile()` raise on `.strip()`. A row that is
                        # str-typed everywhere except one column is a trap for
                        # the next reader too.
                        r[col] = str(cnt.get((r.get(key) or "").strip(), 0))
                    fhdr.append(col)
                    added_cols += 1
                    refused.append(f"{tpath.stem}(1:many on {key} -> {col})")
                    continue
                thdr, trows, _ = load(tpath)
                idx = {}
                for r in trows:
                    idx.setdefault((r.get(key) or "").strip(), r)
                new = [c2 for c2 in thdr if c2 != key and c2 not in fhdr]
                if not new:
                    continue
                pre = tpath.stem
                for r in frows:
                    src = idx.get((r.get(key) or "").strip())
                    for c2 in new:
                        r[f"{pre}__{c2}"] = (src or {}).get(c2, "")
                fhdr.extend(f"{pre}__{c2}" for c2 in new)
                added_cols += len(new)
                joined.append(f"{pre}({key})")
                # THE CHECK, not the promise. A join that moved the row count
                # is reverted, because a rule that is only documented is a rule
                # the next writer breaks.
                if len(frows) != n0:
                    print(f"      !! {pre} moved rows {n0}->{len(frows)}; "
                          f"REVERTED")
                    for c2 in new:
                        fhdr.remove(f"{pre}__{c2}")
                    joined.pop()

        # SWEEP THE PRIOR BUILD FIRST. Nothing here removed old artifacts, so a
        # dataset that stops qualifying for a workbook kept its old one for
        # ever - `funding.xlsx` survived the introduction of the 200,000-row
        # cap and sat on disk looking current at 701,955 rows. That is the same
        # defect the freshness gate exists to catch, one file type over: a
        # deliverable that no longer corresponds to anything.
        if not dry:
            for stale_f in list(OUT.glob(f"{coll}.csv")) +                     list(OUT.glob(f"{coll}__*.csv")) +                     list(OUT.glob(f"{coll}.xlsx")) +                     list(OUT.glob(f"{coll}__CODEBOOK.md")):
                stale_f.unlink()

        files = size = 0
        kind = ""
        if not dry:
            files, size, kind = emit(coll, fhdr, frows, fpath)
            prof = profile(fhdr, frows)
            codebook(coll, c, fname, fmeta, fhdr, frows, prof, joined,
                     refused, fheld)
            xlsx, xlsx_why = notes(coll, c, fname, fmeta, fhdr, frows,
                                   prof, joined, refused, fheld)
        else:
            xlsx = xlsx_why = ""

        sparse = [c2 for c2 in fhdr
                  if not any((r.get(c2) or "") != "" for r in frows)]
        man.append({
            "dataset": coll, "shelf": sh.get(coll), "name": c.get("name", ""),
            "flagship": fname, "grain": (fmeta.get("grain") or "")[:300],
            "rows": len(frows), "rows_withheld": sum(fheld.values()),
            "withheld_why": "; ".join(f"{k}={v}" for k, v in sorted(fheld.items())),
            "columns": len(fhdr), "columns_added_by_join": added_cols,
            "tables_folded_in": "; ".join(joined),
            "tables_counted_not_joined": "; ".join(refused),
            "sparse_columns": "; ".join(sparse),
            "files": files, "largest_mb": round(size / 1e6, 1), "split": kind,
            "codebook": f"{coll}__CODEBOOK.md" if not dry else "",
            "notes_pdf": xlsx, "notes_pdf_absent_reason": xlsx_why,
            "notes_txt": f"{coll}__NOTES.txt" if not dry else "",
        })
        print(f"    {coll:<26} {len(frows):>9,} rows x {len(fhdr):>3} cols   "
              f"+{added_cols} joined   {files} file(s)")

    OUT.mkdir(parents=True, exist_ok=True)
    keys = ["dataset", "shelf", "name", "flagship", "grain", "rows",
            "rows_withheld", "withheld_why", "columns", "columns_added_by_join",
            "tables_folded_in", "tables_counted_not_joined", "sparse_columns",
            "files", "largest_mb", "split", "codebook", "notes_txt",
            "notes_pdf", "notes_pdf_absent_reason", "note"]
    with (OUT / "MANIFEST.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(man)
    print(f"\n    manifest : {(OUT/'MANIFEST.csv').relative_to(ROOT)}")
    if dry:
        print("    nothing written. re-run with `build`.")
    return 0


def _inputs_for(coll, c, fname):
    """Every table this dataset was built from - flagship plus folded-in."""
    out = []
    p = find(fname)
    if p:
        out.append(p)
    for t in c.get("tables", []):
        if t.get("status") != "shippable":
            continue
        q = find(t["table"])
        if q:
            out.append(q)
    return out


def stale() -> list:
    """Customer datasets older than a table they were built from.

    Owner, 2026-09-02: *"it's sort of like we always have a finished product
    we're building and all the cleaning and stuff gets updated and gets
    converted to the finished product."*

    That is a FRESHNESS requirement and it needs a gate, because the failure is
    silent: a cleaning pass rewrites `prime_contracts.csv`, the customer's
    `contractors__2019.csv` still sits on disk looking finished, and nothing
    anywhere says the product no longer matches the data. This project's
    signature defect is a check whose name claims more than its body measures;
    a product with no freshness check is the same defect wearing a price tag.

    So: an output older than any input it was built from is STALE, named with
    the input that moved. Not a warning - `verify` exits 1, because a stale
    deliverable is a wrong deliverable.
    """
    cs, sh = contracts(), shelves()
    out = []
    for coll, c in cs.items():
        if sh.get(coll) not in CUSTOMER_SHELVES:
            continue
        outs = list(OUT.glob(f"{coll}.csv"))
        if not outs:
            out.append((coll, "NEVER BUILT", 0))
            continue
        built = min(p.stat().st_mtime for p in outs)
        for src in _inputs_for(coll, c, FLAGSHIP.get(coll, "")):
            if src.stat().st_mtime > built:
                age = (src.stat().st_mtime - built) / 3600
                out.append((coll, src.name, age))
                break
    return out


def verify() -> int:
    bad = []
    mf = OUT / "MANIFEST.csv"
    if not mf.exists():
        print("  FAIL no manifest - never built")
        return 1
    for coll, src, age in stale():
        if src == "NEVER BUILT":
            bad.append(f"{coll}: NEVER BUILT - no customer spreadsheet exists")
        else:
            bad.append(f"{coll}: STALE - {src} is {age:.1f}h newer than the "
                       f"delivered spreadsheet; re-run `1137 build`")
    with mf.open(encoding="utf-8-sig", errors="replace") as fh:
        man = list(csv.DictReader(fh))
    sh = shelves()
    want = {c for c, s in sh.items() if s in CUSTOMER_SHELVES}
    got = {m["dataset"] for m in man}
    for miss in sorted(want - got):
        bad.append(f"{miss}: customer dataset with no manifest line")
    if len(want) != 12:
        bad.append(f"{len(want)} customer datasets on the shelves, expected 12")
    for m in man:
        if m.get("note"):
            bad.append(f"{m['dataset']}: {m['note']}")
            continue
        if not (OUT / f"{m['dataset']}.csv").exists():
            bad.append(f"{m['dataset']}: no spreadsheet on disk")
        # ONE dataset is ONE file. A leftover split from an older build is a
        # failure; the SIZE of the single file is not - that is a hosting fact,
        # recorded in the manifest. Failing on size would push the next writer
        # straight back to splitting, which the owner ruled out.
        # A workbook the manifest says should not exist is an ORPHAN from an
        # earlier build. It looks current and corresponds to nothing.
        # Every dataset ships notes in BOTH forms. XLSX is retired: Excel
        # coerces leading zeros, dates and long identifiers, so it is not a
        # safe container for this data - see notes().
        for suffix, label in ((".txt", "notes text"), (".pdf", "notes PDF")):
            f = OUT / f"{m['dataset']}__NOTES{suffix}"
            if not f.exists():
                bad.append(f"{m['dataset']}: no {label} ({f.name})")
        orphan = OUT / f"{m['dataset']}.xlsx"
        if orphan.exists():
            bad.append(f"{m['dataset']}: {orphan.name} is a retired-format "
                       f"leftover; XLSX is no longer produced")
        if (m.get("codebook") or "").strip() and not                 (OUT / m["codebook"]).exists():
            bad.append(f"{m['dataset']}: manifest names {m['codebook']}, absent")
        leftover = list(OUT.glob(f"{m['dataset']}__*.csv"))
        if leftover:
            bad.append(f"{m['dataset']}: {len(leftover)} split file(s) still on "
                       f"disk ({leftover[0].name}...); one dataset is one "
                       f"spreadsheet")
        if int(m.get("rows") or 0) == 0:
            bad.append(f"{m['dataset']}: zero rows")
    for b in bad[:25]:
        print("  FAIL " + b)
    print(f"  1137 verify   {'FAIL' if bad else 'ok'}   {len(bad)} problem(s); "
          f"{len(man)} datasets")
    return 1 if bad else 0


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "plan"
    if mode == "verify":
        return verify()
    return build(dry=(mode != "build"))


if __name__ == "__main__":
    sys.exit(main())
