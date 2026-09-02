#!/usr/bin/env python3
"""
Cedar Press - 1137: THIRTEEN datasets, thirteen spreadsheets. One each.
Twelve of them are the Cedar Press storefront; the thirteenth is Cedar Grove's.

    py -3 code/1137_customer_dataset_combine.py            # plan, writes nothing
    py -3 code/1137_customer_dataset_combine.py build
    py -3 code/1137_customer_dataset_combine.py build gaming   # one dataset
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

THE BUILD SET AND THE STOREFRONT SET ARE DIFFERENT SETS
-------------------------------------------------------
Owner, 2026-09-02: *"you're always working on thirteen datasets, the twelve in
Cedar Press, and then the gaming dataset. Those are the ones that you're always
prioritizing."*

From `shelf` in `500_build_architecture_map.py`, via `cedar_publication`:

    standard  funding · federal-register · legislation · deals · nagpra ·
              lobbying                                     -- Cedar Press
    pro       contractors · subcontracting ·
              native-owned-businesses · nest ·
              natural-resources · nonprofits               -- Cedar Press
    grove     gaming                                       -- Cedar Grove

    BUILD_SHELVES      = standard + pro + grove   13 datasets, all delivered
    STOREFRONT_SHELVES = standard + pro           12 datasets, sold here

Until 2026-09-02 those were one tuple and `gaming` was excluded from this build
for the same test that keeps it off the Press storefront. It is the LARGEST
maintained collection in the project - 65 tables, 56 shippable - and it was
undelivered while the check that should have noticed was green, because that
check counted the storefront. Where a dataset is SOLD and whether it is BUILT
are two facts; the code now names both, and `MANIFEST.csv` carries
`storefront` and `sold_through` columns so a reader of the output cannot
re-conflate them either.

`_entity_layer` is infrastructure - it is what the others join to, not a
product. `newsletters` was withdrawn by owner ruling on 2026-09-02: shelf
`withdrawn`, addressable, not sold, not built.

**A silent extra dataset is a defect**, and `verify` holds that three ways: a
thirteenth STOREFRONT slot fails the storefront count (this is how
`newsletters` shipped), a fourteenth BUILT dataset fails the build count, and a
spreadsheet on disk that no manifest line claims fails outright.

THE ONE RULE THAT MAKES A JOIN SAFE
------------------------------------
**The flagship's row count may not change.** A LEFT JOIN onto a table with more
than one row per key does not enrich the flagship, it MULTIPLIES it - and when
the multiplied rows carry money, every total downstream is silently wrong. This
project has already paid for that lesson once: the unfiltered `subaward_amount`
overstates the countable total - by 63.4% as measured on 2026-09-02, and the
point is that the number MOVES. It has shipped as 46.5%, 86.9%, 82.9% and
63.4%; two of those were right when written and all four were hardcoded while
the table grew from 76,859 rows to 89,809. `cedar_publication.subaward_warning()`
now measures it from the delivered file on every build, and returns both
denominators named, because `removed / countable` and `removed / unfiltered`
differ by nearly 2x and quoting one as the other is the original defect.

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
# `code/` on the path so `cedar_publication` imports whether this file is run
# as a script or loaded by importlib from another module.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cedar_publication import (          # noqa: E402
    NEVER, GATES, FLAGSHIP, DROP_COLS, YEAR_COLS, CUSTOMER_SHELVES,
    STOREFRONT_SHELVES, GROVE_SHELVES, BUILD_SHELVES,
    N_STOREFRONT_EXPECTED, N_BUILT_EXPECTED,
    row_ok, publishable_columns, shelves, subaward_warning,
)

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
# `YEAR_COLS`, `CUSTOMER_SHELVES` and `DROP_COLS` are imported above from
# `code/cedar_publication.py`. `DROP_COLS` and `YEAR_COLS` were literals here
# AND in 1135 - two hand-maintained copies of a licensing rule with nothing
# comparing them, which is worse than the text-scraping below because at least
# the scraping was trying.


# `NEVER`, `GATES` and `FLAGSHIP` used to be read out of
# `770_sample_extracts.py` here BY TEXT, and `COLLECTIONS` out of
# `500_build_architecture_map.py`, on the reasoning that "a module whose name
# begins with a digit is not importable". That is true of the `import`
# STATEMENT and false of `importlib` - measured 2026-09-02, 770 imports in
# 0.04 s and does no file work at import - so the scrape was never necessary.
#
# It was also the exact defect it claimed to prevent. The regex could not match
# the annotated binding `COLLECTIONS: list[dict] = [`, so `shelves()` returned
# `{}`, every collection failed the shelf test, and this build printed "0
# customer shelves" and **exited 0**. A regex over source text fails OPEN. An
# import fails CLOSED, with a traceback that names the missing symbol.
#
# All four now come from `code/cedar_publication.py`, imported at the top.
# `shelves()` still reads 500 - 500 owns the collection map and duplicating it
# here would be the same defect - but through `importlib`, and it raises on an
# empty map rather than returning one.


def contracts():
    d = json.loads(CONTRACTS.read_text(encoding="utf-8"))
    return {c["collection"]: c for c in d.get("contracts", [])}


def find(name):
    for d in (CLEAN, SPINE):
        p = d / name
        if p.exists():
            return p
    return None


# `row_ok(row) -> (publishable, reason)` is imported from
# `cedar_publication`. It was reimplemented identically here and in 1135.


def load(path, gate=True):
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        hdr = publishable_columns(rd.fieldnames or [])
        rows, held = [], defaultdict(int)
        for r in rd:
            # PROJECT BEFORE GATING. `hdr` is already `publishable_columns`,
            # so projecting first removes the personal-contact fields; running
            # `row_ok` on the RAW row instead fires its NEVER backstop on the
            # very fields about to be dropped. Measured cost of the wrong
            # order: 582 of 587 rows of the BIA tribal leaders directory,
            # withheld whole for carrying a phone number that was never going
            # to be published.
            r = {c: r.get(c, "") for c in hdr}
            if gate:
                ok, why = row_ok(r)
                if not ok:
                    held[why] += 1
                    continue
            rows.append(r)
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
    # MEASURED, not typed. This sentence carried 86.9% while the live figure
    # was 63.4% and MONEY_TOTALLING_RULES said 82.9% - three vintages of one
    # warning shipping at once, because the table underneath kept growing
    # (76,859 rows when the rules doc was written, 89,809 now). A figure that
    # has moved three times is a derivation problem, which is the same rule
    # this project already applied to the gaming denominator.
    A("- A **sum** in the table above is the raw column total. It is NOT "
      "necessarily the dataset's money answer — filters and de-duplication "
      "rules live in the methodology paper. " + subaward_warning())
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
                   "de-duplication rules live in the methodology paper. "
                   + subaward_warning()))
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


# ---------------------------------------------------------------------------
# COLUMN ORDER - the readability rule, and why it is ORDER and not DELETION
# ---------------------------------------------------------------------------
# Owner, 2026-09-02: *"make sure that we don't have any wonky columns, rows.
# like, structurally, this spreadsheet is good."*
#
# `gaming` came out at 310 columns where the other twelve are 29-91, and the
# obvious fix - drop some - is the wrong one twice over. Most of that width is
# Cedar's PROVENANCE, four columns per measured fact:
#
#     gaming_machines · gaming_machines_value_basis
#     gaming_machines_observation_status · gaming_machines_observed_date
#
# That quartet is the product's differentiator; a competitor ships the number
# alone. And `770` rule 6 already settled the general case: dropping columns
# makes the schema depend on which rows shipped, and a buyer diffing two
# deliveries watches columns appear and vanish.
#
# So nothing is removed and the FIRST SCREEN is made readable instead. Four
# bands, in this order, every column landing in exactly one:
#
#     1  IDENTITY      the keys you join on, then the names you read
#     2  SUBSTANTIVE   what the row is: where, what kind, how big, whose
#     3  PROVENANCE    how each of those is known - `*_basis`,
#                      `*_observed_date`, `*_source_url`, `*_absent_reason`
#     4  JOINED        everything folded in, grouped by the table it came from
#
# Within a band the original order is preserved, so this is a stable
# permutation: run it twice and nothing moves. It is applied to ALL THIRTEEN,
# not to gaming, because a rule that fires on one dataset is a special case
# waiting to be forgotten.
#
# DO NOT reshuffle this into "nicest first" by hand. The bands are the
# contract; a buyer scripting against column position is already wrong, but a
# buyer scanning the first screen is the reader this serves.

_ID_FIRST = ("cedar_uid", "cedar_place_id", "cedar_entity_id", "tribe_id",
             "entity_id", "facility_id", "handle")
_NAME_ISH = ("name", "canonical_name", "tribe_canonical_name", "facility_name",
             "legal_name", "title", "tribe", "entity", "company")
# A column is PROVENANCE when it describes how a neighbouring value is known,
# rather than being a value itself. Suffix-matched, so it covers the per-metric
# quartets without naming 90 columns.
_PROV_SUFFIX = ("_basis", "_source_url", "_source_value_verbatim",
                "_observed_date", "_observation_status", "_absent_reason",
                "_evidence", "_evidence_url", "_evidence_quote", "_quote",
                "_method", "_tier", "_precision", "_as_of", "_verbatim",
                "_source_page", "_scheme", "_note", "_rung", "_md5",
                "_as_published", "_literal", "_test")
_PROV_EXACT = {"fetched_date", "built_date", "temporal_build_date",
               "retrieved_at", "first_seen", "last_seen", "source_url",
               "source_quote", "source_datasets", "source_page",
               "source_authority", "source_document_type", "built_by_script",
               "match_status", "match_basis", "coords_basis",
               "entity_keyed_date", "checked_date", "built_by",
               "observation_status", "value_completeness", "notes"}


def _band(col: str, keys) -> int:
    c = col.lower()
    if c in _ID_FIRST or c in keys or (c.endswith("_id") and
                                       not c.endswith("_absent_reason")):
        return 0
    if c in _NAME_ISH or c.endswith("_name"):
        return 0
    if c in _PROV_EXACT or c.endswith(_PROV_SUFFIX):
        return 2
    return 1


def order_columns(cols, key_cols, own_cols):
    """Stable four-band permutation. Returns EXACTLY the columns given.

    `own_cols` is the flagship's own header, so anything outside it is a
    joined column and lands in band 4 grouped by its source table. The
    identity band is ordered by `_ID_FIRST`, then the contract's declared
    key columns, then any remaining `*_id`, then the name-ish columns.
    """
    keys = {k.lower() for k in (key_cols or [])}
    own = [c for c in cols if c in own_cols]
    joined = [c for c in cols if c not in own_cols]

    bands = {0: [], 1: [], 2: []}
    for c in own:
        bands[_band(c, keys)].append(c)

    def id_rank(c):
        lc = c.lower()
        if lc in _ID_FIRST:
            return (0, _ID_FIRST.index(lc))
        if lc in keys:
            return (1, 0)
        if lc.endswith("_id"):
            return (2, 0)
        return (3, 0)

    # POSITIONS ARE CAPTURED BEFORE THE SORT. `list.index()` inside a sort key
    # reads the list as it is being reordered - the first version of this
    # raised `x not in list` on the second comparison, which is the lucky
    # outcome; the unlucky one is a silently unstable order.
    pos0 = {c: i for i, c in enumerate(bands[0])}
    bands[0].sort(key=lambda c: (id_rank(c), pos0[c]))

    # Band 4: grouped by source table. `pre__col` names its table; `n_pre`
    # is the count column for the same table and sorts with it.
    def group(c):
        return c.split("__", 1)[0] if "__" in c else (
            c[2:] if c.startswith("n_") else c)
    posj = {c: i for i, c in enumerate(joined)}
    joined.sort(key=lambda c: (group(c), "__" not in c, posj[c]))

    out = bands[0] + bands[1] + bands[2] + joined
    # A permutation, or nothing. A reorder that loses or duplicates a column
    # is a data loss wearing a formatting change, and it would be invisible in
    # every row-count check in this file.
    if sorted(out) != sorted(cols) or len(out) != len(cols):
        raise SystemExit(f"order_columns is not a permutation: "
                         f"{len(cols)} in, {len(out)} out")
    return out


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


def build(dry: bool, only: tuple = ()) -> int:
    """Build the THIRTEEN. `only` restricts the pass to named datasets.

    THE BUILD SET AND THE STOREFRONT SET ARE DIFFERENT SETS, and this function
    iterates the BUILD set. Owner, 2026-09-02: *"you're always working on
    thirteen datasets, the twelve in Cedar Press, and then the gaming
    dataset."* `gaming` is `shelf: grove` - it is sold through Cedar Grove and
    appears on no Cedar Press shelf - and it is the largest maintained
    collection in the project. One membership test used to answer both
    questions, so "not on the storefront" silently meant "not built", and 65
    tables went undelivered.

    `only` exists because a full pass rewrites 1.2M-row deliverables and takes
    a very long time. Rebuilding one dataset must not require rebuilding all
    of them, and when the pass is restricted the manifest is MERGED rather
    than replaced - a partial build that dropped the other twelve lines would
    orphan twelve spreadsheets that are still on disk and still correct.
    """
    cs, sh = contracts(), shelves()
    built = [c for c in cs if sh.get(c) in BUILD_SHELVES]
    unknown = [c for c in only if c not in built]
    if unknown:
        print(f"  REFUSING TO BUILD: not in the build set: "
              f"{', '.join(sorted(unknown))}\n"
              f"  the build set is: {', '.join(sorted(built))}", file=sys.stderr)
        return 2
    selected = [c for c in built if not only or c in only]
    man = []
    print(f"  1137 customer datasets   {'PLAN' if dry else 'BUILD'}")
    print(f"    build set        : {len(built)}  "
          f"({len([c for c in built if sh.get(c) in STOREFRONT_SHELVES])} on the "
          f"Cedar Press storefront, "
          f"{len([c for c in built if sh.get(c) in GROVE_SHELVES])} through "
          f"Cedar Grove)")
    if only:
        print(f"    restricted to    : {', '.join(sorted(selected))}")
    print(f"    datasets         : {', '.join(sorted(selected))}\n")

    for coll in sorted(selected):
        c = cs[coll]
        fname = FLAGSHIP.get(coll)
        fpath = find(fname) if fname else None
        if not fpath:
            man.append({"dataset": coll, "shelf": sh.get(coll),
                        "storefront": "Y" if sh.get(coll) in STOREFRONT_SHELVES
                                      else "N",
                        "note": f"flagship {fname} absent"})
            print(f"    {coll:<26} FLAGSHIP MISSING ({fname})")
            continue

        fhdr, frows, fheld = load(fpath)
        own_cols = set(fhdr)      # everything added after this is a join
        n0 = len(frows)
        meta = {t["table"]: t for t in c.get("tables", [])}
        fmeta = meta.get(fname, {})
        fkeys = [k for k in (fmeta.get("key_columns") or []) if k in fhdr]
        # THE SHARED KEY MUST BE THE FINEST ONE BOTH TABLES CARRY, and this
        # was taking the first one DECLARED instead - which is a different
        # thing and it silently answers a different question.
        #
        # Measured on gaming, 2026-09-02. `gaming_facilities.csv` declares
        # `key_columns = [tribe_id, cedar_uid, entity_id, facility_id]` and
        # its grain is the PROPERTY: 787 rows, 787 distinct `facility_id`, 250
        # distinct `tribe_id`. `gaming_revenue_bounds.csv` carries both. Taking
        # the first declared key joined on `tribe_id`, so `n_gaming_revenue_bounds`
        # on a property row was the count for that property's whole NATION -
        # Cherokee Nation's ten casinos each reporting the tribe's total. The
        # column is named for the property and counted for the tribe, which is
        # this project's signature defect in one cell.
        #
        # So rank the shared keys by how finely they cut the FLAGSHIP - most
        # distinct non-blank values wins - and fall back to declared order on a
        # tie. `facility_id` (787 distinct) beats `tribe_id` (250), and the
        # count means what its row means.
        _fine = {}
        for k in fkeys:
            _fine[k] = len({(r.get(k) or "").strip() for r in frows
                            if (r.get(k) or "").strip()})
        fkeys = sorted(fkeys, key=lambda k: (-_fine[k], fkeys.index(k)))

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
                # RE-MEASURE. The contracts file records a cardinality that was
                # true when the grain sweep ran; the table may have been
                # rebuilt since. Codex, PR #35: `setdefault` silently keeps the
                # first row and discards the rest, and the row-count check
                # CANNOT catch it - a join widens rows and never appends to
                # `frows`, so the count is unchanged by construction and the
                # advertised safeguard passes while the customer receives an
                # arbitrary one of N supporting records.
                #
                # It also answers the review question I put in the PR: no,
                # trusting the declared measurement is not sufficient. Measure
                # on the rows actually loaded, and refuse when it fails.
                idx = {}
                dupe_key = 0
                for r in trows:
                    k2 = (r.get(key) or "").strip()
                    if k2 in idx:
                        dupe_key += 1
                        continue
                    idx[k2] = r
                if dupe_key:
                    refused.append(f"{tpath.stem}(DECLARED 1:1 on {key}, "
                                   f"MEASURED {dupe_key} duplicate key(s) - "
                                   f"join refused, contracts file is stale)")
                    print(f"      !! {tpath.stem}: declared one-to-one on "
                          f"{key}, measured {dupe_key} duplicate key(s); "
                          f"REFUSED")
                    continue
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
            # Sweep EVERY artifact of the previous build, notes included.
            # Codex, PR #35: if a later build runs without reportlab, an old
            # __NOTES.pdf survives, notes() records generation as unavailable,
            # and verify passes because it only checks the path exists - a
            # current CSV shipping beside outdated notes. A failed
            # regeneration has to be visibly absent.
            for _pat in (f"{coll}.csv", f"{coll}__*.csv",
                         f"{coll}__NOTES.txt", f"{coll}__NOTES.pdf",
                         f"{coll}__NOTES.pdf.absent",
                         f"{coll}__CODEBOOK.md", f"{coll}.xlsx"):
                for stale_f in OUT.glob(_pat):
                    stale_f.unlink()

        # BAND THE COLUMNS BEFORE ANYTHING IS WRITTEN, so the CSV, the
        # codebook and the notes all present the same order. Doing it inside
        # `emit` alone would have shipped a spreadsheet whose columns ran in a
        # different order from the codebook describing it.
        fhdr = order_columns(fhdr, fmeta.get("key_columns"), own_cols)

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
            "dataset": coll, "shelf": sh.get(coll),
            # WHERE IT IS SOLD IS A COLUMN, not a thing the reader infers from
            # the shelf string. `standard` and `pro` are Cedar Press shelves;
            # `grove` is Cedar Grove. Both get built; only the first two are on
            # the Press storefront, and a manifest that does not say so invites
            # the next reader to count thirteen storefront slots.
            "storefront": "Y" if sh.get(coll) in STOREFRONT_SHELVES else "N",
            "sold_through": ("Cedar Press" if sh.get(coll) in STOREFRONT_SHELVES
                             else "Cedar Grove"),
            "name": c.get("name", ""),
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

    if not dry:
        OUT.mkdir(parents=True, exist_ok=True)
    keys = ["dataset", "shelf", "storefront", "sold_through", "name",
            "flagship", "grain", "rows",
            "rows_withheld", "withheld_why", "columns", "columns_added_by_join",
            "tables_folded_in", "tables_counted_not_joined", "sparse_columns",
            "files", "largest_mb", "split", "codebook", "notes_txt",
            "notes_pdf", "notes_pdf_absent_reason", "note"]
    if only and not dry:
        # A RESTRICTED BUILD MERGES, IT DOES NOT REPLACE. Writing only the
        # selected lines would leave the other datasets' spreadsheets on disk
        # with no manifest line - which `verify` correctly reads as an orphan,
        # and which is exactly the failure a partial pass must not manufacture.
        keep = []
        mf = OUT / "MANIFEST.csv"
        if mf.exists():
            with mf.open(encoding="utf-8-sig", errors="replace") as fh:
                keep = [r for r in csv.DictReader(fh)
                        if r.get("dataset") not in {m["dataset"] for m in man}]
        man = sorted(keep + man, key=lambda r: r.get("dataset") or "")
    # A DRY RUN THAT WRITES IS NOT A DRY RUN. `plan` printed "nothing written"
    # and then overwrote `MANIFEST.csv` anyway, with dry-run values - no
    # `files`, no `largest_mb`, no `codebook`, no notes, and no join columns,
    # because none of that work ran under `dry`. The manifest is the only
    # record of what was actually DELIVERED, and `verify` reads it to decide
    # whether a spreadsheet on disk is an orphan - so replacing it with a plan
    # turns twelve delivered datasets into twelve apparent orphans, while the
    # command that did it reported writing nothing. Measured 2026-09-02, when a
    # single `plan` invocation did exactly that to a manifest built by `build`.
    if dry:
        print(f"\n    {len(man)} dataset(s) planned. NOTHING WRITTEN - not the "
              f"spreadsheets, and not {(OUT/'MANIFEST.csv').name}, which still "
              f"describes the last real build. Re-run with `build`.")
        return 0
    with (OUT / "MANIFEST.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(man)
    print(f"\n    manifest : {(OUT/'MANIFEST.csv').relative_to(ROOT)}")
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
        # THE BUILD SET, not the storefront set. Gaming is delivered, so a
        # stale gaming spreadsheet is a wrong deliverable in exactly the way a
        # stale contractors spreadsheet is.
        if sh.get(coll) not in BUILD_SHELVES:
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
            bad.append(f"{coll}: NEVER BUILT - no spreadsheet exists")
        else:
            bad.append(f"{coll}: STALE - {src} is {age:.1f}h newer than the "
                       f"delivered spreadsheet; re-run "
                       f"`1137 build {coll}`")
    with mf.open(encoding="utf-8-sig", errors="replace") as fh:
        man = list(csv.DictReader(fh))
    sh = shelves()
    # TWO SETS, TWO COUNTS, AND THEY ARE CHECKED SEPARATELY.
    #
    # Thirteen datasets are BUILT; twelve of them are on the Cedar Press
    # storefront and one - `gaming` - is sold through Cedar Grove. The old
    # single check asserted "12 customer datasets" and that one number was
    # doing two jobs: it was the storefront's price list AND the delivery
    # commitment. Under it, the project's largest collection was silently
    # undelivered and the check was green.
    #
    # The property that must survive is the one that caught `newsletters`:
    # A SILENT EXTRA DATASET IS A DEFECT. It survives twice over now - a
    # thirteenth STOREFRONT slot fails the storefront count, and a fourteenth
    # BUILT dataset fails the build count - plus a third way the old check
    # could not see: a spreadsheet on disk that no manifest line claims.
    want = {c for c, s in sh.items() if s in BUILD_SHELVES}
    store = {c for c, s in sh.items() if s in STOREFRONT_SHELVES}
    grove = want - store
    got = {m["dataset"] for m in man}
    for miss in sorted(want - got):
        bad.append(f"{miss}: built dataset with no manifest line")
    for extra in sorted(got - want):
        bad.append(f"{extra}: manifest line for a dataset on no built shelf "
                   f"- a silent extra dataset is a defect")
    if len(want) != N_BUILT_EXPECTED:
        bad.append(f"{len(want)} datasets in the build set, expected "
                   f"{N_BUILT_EXPECTED}: {', '.join(sorted(want))}")
    if len(store) != N_STOREFRONT_EXPECTED:
        bad.append(f"{len(store)} datasets on the Cedar Press storefront, "
                   f"expected {N_STOREFRONT_EXPECTED}: "
                   f"{', '.join(sorted(store))}")
    # A DELIVERABLE THAT NO MANIFEST LINE CLAIMS. The manifest is the record of
    # what was built; a `.csv` beside it that the record does not name is a
    # leftover from a shelf change or a withdrawn dataset, and it looks exactly
    # as finished as the real ones. `newsletters.csv` would sit here today.
    for f in sorted(OUT.glob("*.csv")):
        if f.name != "MANIFEST.csv" and f.stem not in got:
            bad.append(f"{f.name}: on disk and in no manifest line - an "
                       f"unclaimed deliverable; a silent extra dataset is a "
                       f"defect")
    # The storefront must be a subset of what is built.
    for c in sorted(store - want):
        bad.append(f"{c}: on a Cedar Press shelf but not in the build set")
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
        # RE-READ THE DELIVERED FILE. Codex, PR #35: a truncated or partially
        # written CSV has a NEWER mtime, so stale() calls it current, and
        # checking only that the path exists while taking the row count from
        # the manifest lets a header-only paid dataset pass. The manifest is
        # this script's own claim about its work; a gate that reads it is
        # grading its own homework.
        _f = OUT / f"{m['dataset']}.csv"
        if _f.exists():
            try:
                with _f.open(encoding="utf-8-sig", errors="replace",
                             newline="") as fh:
                    _rd = csv.reader(fh)
                    _hdr = next(_rd, [])
                    _n = sum(1 for _ in _rd)
            except OSError as e:
                bad.append(f"{m['dataset']}: unreadable ({e})")
            else:
                _want_r = int(m.get("rows") or 0)
                _want_c = int(m.get("columns") or 0)
                if _n != _want_r:
                    bad.append(f"{m['dataset']}: manifest says {_want_r:,} "
                               f"rows, the file holds {_n:,}")
                if len(_hdr) != _want_c:
                    bad.append(f"{m['dataset']}: manifest says {_want_c} "
                               f"columns, the header holds {len(_hdr)}")
    for b in bad[:25]:
        print("  FAIL " + b)
    print(f"  1137 verify   {'FAIL' if bad else 'ok'}   {len(bad)} problem(s); "
          f"{len(man)} datasets")
    return 1 if bad else 0


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "plan"
    if mode == "verify":
        return verify()
    # `build <dataset> [<dataset> ...]` restricts the pass. Everything after
    # the mode is a dataset id; a name that is not in the build set is refused
    # rather than silently matching nothing, because a filter that quietly
    # selects zero datasets prints a clean report of no work.
    only = tuple(a for a in sys.argv[2:] if not a.startswith("-"))
    return build(dry=(mode != "build"), only=only)


if __name__ == "__main__":
    sys.exit(main())
