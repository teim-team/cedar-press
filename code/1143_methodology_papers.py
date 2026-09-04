#!/usr/bin/env python3
"""
Cedar Press - 1143: THIRTEEN datasets, thirteen methodology papers. One each.

    py -3 code/1143_methodology_papers.py            # report, writes nothing
    py -3 code/1143_methodology_papers.py report
    py -3 code/1143_methodology_papers.py build
    py -3 code/1143_methodology_papers.py build nest # one dataset
    py -3 code/1143_methodology_papers.py verify     # exits 1 on missing OR stale

WHY THIS EXISTS
---------------
Owner, standing instruction: *"every dataset should have its own methodology
paper... gaming needs its own methodology paper, federal contracting, so on and
so forth."* And, later: *"don't focus on building more, focus on making
everything we have good."*

Twelve papers were written by hand on 2026-09-02 and they are good. Two things
were wrong with them anyway.

**1. `nest` had no paper.** `docs/methodology/README.md` listed thirteen and
counted `_entity_layer` as the thirteenth. But `_entity_layer` is
infrastructure - `cedar_publication.BUILD_SHELVES` excludes it by name, and it
has no `dist/customer/` spreadsheet. The dataset that *is* delivered and had no
paper was `nest`. A README that counts to thirteen while the delivered set
counts to thirteen a different way is how a gap hides in plain sight; the same
conflation is what let `newsletters` ship as an unwanted storefront slot.

**2. Nothing measured them.** Every figure was hand-run on 2026-09-02 against
`data/clean/`, and nine of the thirteen datasets were rebuilt or enriched
inside that same window. A hand-measured figure in a hand-written file has no
way to announce that it has gone stale, and this project has already paid for
that: the gaming property denominator circulated in SEVEN values
(787/780/734/727/725/717/714) before the table was made to answer it itself. It
is **717** - `COUNT(DISTINCT cedar_place_id)` - and the way that got settled was
by measuring, not by editing.

So the papers are now GENERATED, for the same reason the codebooks are.

WHAT IS GENERATED AND WHAT IS NOT
----------------------------------
A methodology paper is not fully derivable and pretending otherwise would be
worse than hand-writing it. The reasoning - why a source was refused, what a
regime change means, which of two disagreeing sources to believe - is
editorial and no script can produce it. So each paper has three parts:

    <!-- BEGIN GENERATED:IDENTITY -->   what this dataset IS, measured
    <!-- BEGIN EDITORIAL:<id> -->       the argument, hand-written, PRESERVED
    <!-- BEGIN GENERATED:MEASURED -->   Appendix M, measured, six sections

The editorial block is read out of the existing file and written back
byte-for-byte. `build` never destroys prose. On the first run over a paper that
predates this script, the whole hand-written body is migrated into the
editorial block automatically, so nothing had to be re-typed. Nested markers
inside the body survive - `gaming.md` carries a `<!-- BEGIN SEC-GAMING -->`
pair and it comes through untouched, because the parser matches only the outer
pair by exact name.

**A paper with no editorial block fails `verify`.** An all-generated paper
would be a codebook with a different filename.

WHAT THE APPENDIX IS NOT ALLOWED TO BE
---------------------------------------
It is not the codebook. `dist/customer/<id>__CODEBOOK.md` already carries the
grain, the folded-in tables and the per-column fill rates, and `<id>__NOTES.txt`
carries the same for a person. Restating them here would give a reader two
copies that can disagree. **The codebook says what the columns are; the
methodology paper says how the dataset came to exist and why you should believe
it.** So Appendix M carries only what bears on believing it: where the rows say
they came from, the pipeline that made them, the identity layer and what
`attribution_method` means IN THIS DATASET, what is withheld, which money
columns may be summed, and the fingerprint that makes the paper falsifiable.

MEASURED MEANS MEASURED FROM THE DELIVERED FILE
------------------------------------------------
Every number in Appendix M comes from `dist/customer/<id>.csv` - the artefact a
customer actually receives - read with duckdb over the whole file, never
sampled. Not from `data/clean/`, not from a build log, not from `MANIFEST.csv`.
Where the delivered file and a document disagree, the file wins and the
disagreement is printed by `verify` rather than smoothed over.

The one thing quoted rather than measured is the money fence, and it is quoted
verbatim with its source named, because `docs/MONEY_TOTALLING_RULES.md` is
authoritative on which columns may be summed and re-deriving that from the data
is exactly the mistake it exists to prevent.

WHAT `verify` FAILS ON
-----------------------
1. a BUILT dataset with no paper
2. a paper with no `EDITORIAL` block, or an empty one
3. a paper whose recorded fingerprint does not match the delivered file today -
   bytes, rows, columns or header digest. This is the staleness test, and it is
   the whole point: a paper is stale the moment its dataset is rebuilt.
4. a paper in `docs/methodology/` that no built dataset claims
5. a dataset carrying `attribution_method` with no declared sense in
   `ATTRIBUTION_SENSE` below

`_entity_layer.md` is exempt from (4) and kept: it is the shared identity
chapter every other paper leans on, and deleting it to satisfy a count would
throw away 43 KB of correct work. It is listed as infrastructure, not as a
dataset.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cedar_publication import (          # noqa: E402
    FLAGSHIP, BUILD_SHELVES, STOREFRONT_SHELVES, N_BUILT_EXPECTED, shelves,
)

DIST = ROOT / "dist" / "customer"
PAPERS = ROOT / "docs" / "methodology"
DOCS = ROOT / "docs"
TODAY = date.today().isoformat()

# Papers that are kept but are NOT a delivered dataset. `_entity_layer` is the
# identity chapter the other twelve lean on; it has no spreadsheet because it is
# what the spreadsheets join to.
NON_DATASET_PAPERS = {"_entity_layer", "README"}

# ---------------------------------------------------------------------------
# WHAT `attribution_method` MEANS, PER DATASET - STATED, NOT DERIVED
# ---------------------------------------------------------------------------
# `docs/schema/attribution_method_vocabulary.json`: *"attribution_method is
# three different columns sharing a name - a join method, an evidence
# provenance, and a name-match algorithm."* Which one a given table carries is
# a reading of that table's term list, not a property a script can compute, so
# it is declared here and `verify` fails if a dataset grows the column without
# one. Deriving it would agree with whatever the data happened to look like,
# which is the same failure mode as a derived storefront count.
ATTRIBUTION_SENSE = {
    "contractors": (
        "A JOIN METHOD. The terms name WHICH IDENTIFIER carried the link - "
        "`uei_exact`, `cage_exact`, `parent_uei`, the two `ladder_*` "
        "adjudications and `ruling_applied` - and `unattributed` is a real "
        "value, not a blank. It says nothing about how strong the evidence "
        "was; that is `confidence_tier`, and the two are independent. Reading "
        "an exact key as an exact link is defect class 1 in `AGENTS.md`."
    ),
    "funding": (
        "A JOIN METHOD, plus a DISPOSITION. `uei_exact_archive` and the three "
        "`dofile_corrtd:*` variants say which key joined; "
        "`ledger_exclusion`, `ledger_uei_state_disagreement_withheld`, "
        "`not_evaluated:ak_scope_line9` and `unattributed` say why a row has "
        "no entity, which is a decision rather than a method. The companion "
        "column `attribution_status` is never blank and is the one to filter "
        "on."
    ),
    "lobbying": (
        "A NAME-MATCH ALGORITHM. Every term names the string comparison that "
        "fired - `exact_normalized`, `exact_normalized_skeleton`, "
        "`core_token_set`, `core_containment`, `contains_canonical` and their "
        "subsidiary variants. No identifier is involved anywhere in this "
        "column, so it may never be read as tier-A evidence: a containment "
        "match is tier C by `ENTITY_MATCH_RULES` and containment may never "
        "key a dollar."
    ),
}

# ---------------------------------------------------------------------------
# FIGURES THAT HAVE CIRCULATED IN MORE THAN ONE VALUE - STATED, NOT DERIVED
# ---------------------------------------------------------------------------
# A generated appendix and a hand-written body can disagree, and when they do
# the reader is left holding two numbers and no way to choose. These are the
# figures this project has actually watched drift, each with the superseded
# values it drifted through. `build` re-measures the true one and then searches
# the EDITORIAL body for a superseded literal; where it finds one it prints a
# contradiction in the paper itself rather than leaving both to stand.
#
# Declared rather than inferred, for the same reason `N_BUILT_EXPECTED` is: a
# derived list of "numbers that look stale" would agree with whatever the prose
# happened to say, which is the failure it is meant to catch.
#
# `value` is a callable over the measurement dict so the CORRECT figure is
# always the measured one and never a literal in this file.
PROSE_CHECKS = {
    "gaming": [
        ("distinct gaming properties, `COUNT(DISTINCT cedar_place_id)`",
         lambda m: m.get("gaming_denominator"),
         # SEVEN values circulated for this on 2026-09-02, each from a
         # different definition of "facility" and none saying which.
         ("714", "725", "727", "734", "780")),
        ("rows in the delivered file (a row is NOT a property)",
         lambda m: m.get("rows"), ()),
    ],
    "subcontracting": [
        ("rows in the delivered file",
         lambda m: m.get("rows"),
         # `docs/MONEY_TOTALLING_RULES.md` and `START_HERE.md` both still carry
         # the pre-growth count.
         ("76,859", "76859")),
        ("how far a row-summed `subaward_amount` lands above the fenced total",
         lambda m: (f"{m['subaward_fence']['over_correct_pct']:.1f}%"
                    if m.get("subaward_fence") else None),
         ("82.9%", "86.9%", "45.3%")),
        ("the unfiltered `subaward_amount` total",
         lambda m: (f"${m['subaward_fence']['unfiltered_sum']:,.2f}"
                    if m.get("subaward_fence") else None),
         ("$47,301,660,819.78", "$45.62B", "$47.30B")),
        ("the fenced `subaward_amount` total",
         lambda m: (f"${m['subaward_fence']['filtered_sum']:,.2f}"
                    if m.get("subaward_fence") else None),
         ("$25,864,997,128.19", "$24.41B", "$25.86B")),
    ],
}

# Column-name patterns. Curated rather than inferred: a pattern that matches
# too widely turns the appendix into the codebook it is supposed not to be.
SOURCE_COLS = ("source_file", "source_dataset", "source_datasets",
               "source_document", "source_system", "source_population",
               "source_vintage", "source_terms_status", "source_edition_date",
               "source_agency", "source_url", "fetched_date", "retrieved_date")
IDENTITY_COLS_EXACT = ("attribution_method", "confidence_tier",
                       "attribution_status", "record_scope", "assertion_class",
                       "evidence_class", "inclusion_basis",
                       "hub_resolution_method", "entity_tier",
                       "identifier_status", "identity_scope", "disposition")
MONEY_RE = re.compile(
    r"(_usd$|_usd_|^total_obligations$|amount$|_amount_|_amt$|_amt_|"
    r"obligation|announced_value|_value_usd$|principal|revenue|expenditure|"
    r"expenses|royalt)", re.I)
# ...and a NAME is never enough on its own. Three name-only false positives
# were caught on the first full build and each is a different failure:
#   `n_compact_obligation_tribal_agency_bridge`  a COUNT column, rendered as
#                                                "$1,759.00" - a count with a
#                                                dollar sign in front of it
#   `in_full_irs_bmf`                            a 0/1 FLAG that summed to a
#                                                plausible-looking dollar total
#   `amount_countable`                           the same, and `517.MONEY_HINTS`
#                                                had already made this exact
#                                                mistake once
# So a column must clear a NAME test, a CONTENT test (>=98% of populated values
# parse as a number) and a SHAPE test (not a count by name, not a 0/1 flag by
# value) before this appendix will print a dollar sign in front of it.
NOT_MONEY_RE = re.compile(
    r"(^n_|^num_|_count$|^count_|_flag$|_pct$|_percent|_share$|_ratio$|"
    r"_year$|_date$|_id$|_rank$|_seq$)", re.I)
# Columns whose NAME looks like money and whose CONTENT is not. Each is a
# measured false positive, kept by name so the appendix does not have to
# re-litigate it every build.
MONEY_NAME_FALSE_POSITIVES = {
    # a 0/1 flag, not a dollar column - `517.MONEY_HINTS` made this exact
    # mistake and it is recorded in docs/MONEY_TOTALLING_RULES.md
    "amount_countable",
    # free text, blank on the only row it exists on
    "principal_amount_text", "pledged_revenues_text",
}
YEAR_COLS = ("fiscal_year", "fy", "action_date_fiscal_year",
             "award_fiscal_year", "year", "report_year", "filing_year",
             "first_observed_year", "last_observed_year")

MARK_ID_B, MARK_ID_E = "<!-- BEGIN GENERATED:IDENTITY -->", "<!-- END GENERATED:IDENTITY -->"
MARK_M_B, MARK_M_E = "<!-- BEGIN GENERATED:MEASURED -->", "<!-- END GENERATED:MEASURED -->"


def ed_markers(did: str) -> tuple[str, str]:
    return f"<!-- BEGIN EDITORIAL:{did} -->", f"<!-- END EDITORIAL:{did} -->"


# ---------------------------------------------------------------------------
# READING WHAT ALREADY EXISTS
# ---------------------------------------------------------------------------
def _split_on_marker_line(txt: str, marker: str):
    """Split on a marker that is ALONE ON ITS OWN LINE. Nothing else counts.

    THIS FUNCTION EXISTS BECAUSE A SUBSTRING MATCH DESTROYED A PAPER.
    The generated IDENTITY block tells the reader, in prose, to put text
    between the BEGIN and END EDITORIAL markers - and it names them. A plain
    `txt.split(marker)` then finds that SENTENCE first, and the "editorial
    body" it recovers on the next build is the five characters between the two
    names inside the sentence. `subcontracting.md` rebuilt from 58,874 bytes to
    20,700 and the prose was gone; it was restored from git and this function
    is the fix.

    The lesson generalises past this file: **a marker that a document is
    allowed to talk about must be ANCHORED, not searched for.** Documentation
    of a delimiter is a legal occurrence of the delimiter, and `in` cannot tell
    the two apart.
    """
    lines = txt.split("\n")
    for i, ln in enumerate(lines):
        if ln.strip() == marker:
            return "\n".join(lines[:i]), "\n".join(lines[i + 1:])
    return None


def read_paper(path: Path) -> dict:
    """-> {'title', 'editorial', 'had_markers'}. Never loses prose.

    A paper written before this script has no markers at all. Rather than
    refuse it - which would mean re-typing twelve papers averaging 35 KB - the
    whole hand-written body between the title and EOF is migrated into the
    editorial block on the first build. That is a one-way move and it is
    lossless: the body is copied byte-for-byte, including any nested marker
    pairs another workstream owns.
    """
    if not path.exists():
        return {"title": "", "editorial": "", "had_markers": False}
    txt = path.read_text(encoding="utf-8")
    did = path.stem
    b, e = ed_markers(did)
    after = _split_on_marker_line(txt, b)
    inner = _split_on_marker_line(after[1], e) if after else None
    if inner is not None:
        title = txt.split("\n", 1)[0].strip()
        return {"title": title, "editorial": inner[0].strip("\n"),
                "had_markers": True}
    # Migration path. Strip a leading `# ...` title line; everything else is
    # editorial, including any trailing appendix a hand-writer added.
    lines = txt.split("\n")
    title = ""
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines) and lines[i].startswith("# "):
        title = lines[i].strip()
        i += 1
    return {"title": title, "editorial": "\n".join(lines[i:]).strip("\n"),
            "had_markers": False}


# ---------------------------------------------------------------------------
# MEASUREMENT - from the DELIVERED file, whole, never sampled
# ---------------------------------------------------------------------------
def _rel(path: Path) -> str:
    p = str(path).replace("\\", "/").replace("'", "''")
    return (f"read_csv('{p}', all_varchar=true, sample_size=-1, header=true, "
            f"ignore_errors=false)")


def measure(did: str) -> dict:
    """Every number in Appendix M is produced here, from dist/customer/<id>.csv."""
    import duckdb  # noqa: F401  (kept: types/exceptions)
    import cedar_duck

    path = DIST / f"{did}.csv"
    out: dict = {"dataset": did, "path": path, "exists": path.exists()}
    if not path.exists():
        return out

    raw = path.read_bytes()[:1 << 20]
    header_line = raw.split(b"\n", 1)[0]
    out["bytes"] = path.stat().st_size
    out["header_sha256"] = hashlib.sha256(header_line).hexdigest()

    con = cedar_duck.connect()
    rel = _rel(path)
    cols = [r[0] for r in con.sql(f"DESCRIBE SELECT * FROM {rel}").fetchall()]
    out["columns"] = len(cols)
    out["col_names"] = cols
    out["rows"] = con.sql(f"SELECT count(*) FROM {rel}").fetchone()[0]
    low = {c.lower(): c for c in cols}

    def q(sql):
        return con.sql(sql).fetchall()

    def esc(c):
        return '"' + c.replace('"', '""') + '"'

    # --- entity attachment -------------------------------------------------
    out["entity"] = {}
    for key in ("cedar_uid", "tribe_id", "owner_hub_cedar_uid"):
        if key in low:
            c = esc(low[key])
            n, d = q(f"SELECT count(*) FILTER (WHERE nullif(trim({c}),'') IS NOT NULL), "
                     f"count(DISTINCT nullif(trim({c}),'')) FROM {rel}")[0]
            out["entity"][low[key]] = {"filled": n, "distinct": d}

    # --- vocabulary distributions -----------------------------------------
    # A column is a vocabulary column if it is named as one, or if it is a
    # `*_tier` / `*_method` / `*_status`. Bounded at 40 distinct values: past
    # that it is data, not a vocabulary, and printing it would be a codebook.
    vocab_cols = []
    for c in cols:
        lc = c.lower()
        if lc in IDENTITY_COLS_EXACT or lc.endswith(("_tier", "_method")):
            vocab_cols.append(c)
    out["vocab"] = {}
    for c in vocab_cols:
        e = esc(c)
        d = q(f"SELECT count(DISTINCT nullif(trim({e}),'')) FROM {rel}")[0][0]
        if d == 0:
            out["vocab"][c] = {"distinct": 0, "values": [], "blank": out["rows"]}
            continue
        vals = q(f"SELECT coalesce(nullif(trim({e}),''),'(blank)') v, count(*) n "
                 f"FROM {rel} GROUP BY 1 ORDER BY n DESC LIMIT 41")
        out["vocab"][c] = {"distinct": d, "values": vals[:40],
                           "truncated": len(vals) > 40}

    # --- sources as the rows record them ----------------------------------
    out["sources"] = {}
    for name in SOURCE_COLS:
        if name not in low:
            continue
        c = esc(low[name])
        filled = q(f"SELECT count(*) FILTER (WHERE nullif(trim({c}),'') IS NOT NULL) "
                   f"FROM {rel}")[0][0]
        if name == "source_url":
            vals = q(f"SELECT regexp_extract(trim({c}), '^[a-zA-Z]+://([^/]+)', 1) h, "
                     f"count(*) n FROM {rel} WHERE nullif(trim({c}),'') IS NOT NULL "
                     f"GROUP BY 1 ORDER BY n DESC LIMIT 20")
            out["sources"][low[name]] = {"filled": filled, "kind": "host",
                                         "values": vals}
            continue
        d = q(f"SELECT count(DISTINCT nullif(trim({c}),'')) FROM {rel}")[0][0]
        vals = []
        if 0 < d <= 60:
            vals = q(f"SELECT nullif(trim({c}),'') v, count(*) n FROM {rel} "
                     f"WHERE nullif(trim({c}),'') IS NOT NULL "
                     f"GROUP BY 1 ORDER BY n DESC")
        elif d > 60:
            vals = q(f"SELECT nullif(trim({c}),'') v, count(*) n FROM {rel} "
                     f"WHERE nullif(trim({c}),'') IS NOT NULL "
                     f"GROUP BY 1 ORDER BY n DESC LIMIT 15")
        out["sources"][low[name]] = {"filled": filled, "distinct": d,
                                     "kind": "value", "values": vals,
                                     "truncated": d > 60}

    # --- money -------------------------------------------------------------
    # A column is money only if it PARSES as money. A name test alone promotes
    # `amount_countable` (a 0/1 flag) and `principal_amount_text` (free text),
    # which is the mistake `517.MONEY_HINTS` made and had to be corrected for.
    out["money"] = {}
    # Candidate PARENT keys - the id of the thing a repeated money figure
    # belongs to. Bounded to four so the appendix cannot become a cross-join.
    parent_keys = [c for c in cols
                   if re.search(r"(_unique_key$|^prime_award_id$|_award_id$|"
                                r"^cedar_uid$|^owner_hub_cedar_uid$|"
                                r"^enterprise_id$|^facility_id$)", c.lower())][:4]
    out["parent_keys"] = parent_keys
    for c in cols:
        if (c.lower() in MONEY_NAME_FALSE_POSITIVES
                or not MONEY_RE.search(c) or NOT_MONEY_RE.search(c)):
            continue
        e = esc(c)
        filled, numeric = q(
            f"SELECT count(*) FILTER (WHERE nullif(trim({e}),'') IS NOT NULL), "
            f"count(*) FILTER (WHERE TRY_CAST(trim({e}) AS DOUBLE) IS NOT NULL) "
            f"FROM {rel}")[0]
        if filled == 0 or numeric / filled < 0.98:
            out["money"][c] = {"filled": filled, "numeric": numeric,
                               "is_money": False,
                               "why": "does not parse as a number"}
            continue
        flagvals = q(f"SELECT count(DISTINCT trim({e})) FROM {rel} "
                     f"WHERE nullif(trim({e}),'') IS NOT NULL "
                     f"AND trim({e}) NOT IN ('0','1','0.0','1.0')")[0][0]
        if flagvals == 0:
            out["money"][c] = {"filled": filled, "numeric": numeric,
                               "is_money": False,
                               "why": "every populated value is 0 or 1 - this "
                                      "is a FLAG, not a dollar column"}
            continue
        s, mn, mx, dv = q(f"SELECT sum(TRY_CAST(trim({e}) AS DOUBLE)), "
                          f"min(TRY_CAST(trim({e}) AS DOUBLE)), "
                          f"max(TRY_CAST(trim({e}) AS DOUBLE)), "
                          f"count(DISTINCT nullif(trim({e}),'')) FROM {rel}")[0]
        out["money"][c] = {"filled": filled, "numeric": numeric,
                           "is_money": True, "sum": s, "min": mn, "max": mx,
                           "distinct": dv, "dedup": {}}

        # A MONEY COLUMN THAT REPEATS IS A PARENT'S FIGURE ON A CHILD'S ROW.
        # `contractor_ranking.owner_obligations_usd` row-summed gives $6,535.96B
        # against a true $176.74B - a 36.98x inflation - because it is an
        # OWNER-grain attribute repeated on every operating-company row.
        #
        # THE TEST IS FUNCTIONAL DEPENDENCE, NOT A DISTINCT-VALUE HEURISTIC.
        # The first cut here flagged any column with fewer distinct values than
        # rows, and that fires on `subaward_amount` - 55,110 distinct over
        # 89,809 rows - purely because contract amounts land on round numbers.
        # Printing a "deduped total" for a column that is genuinely row-grain
        # would publish a figure that means nothing and looks authoritative.
        #
        # The column is a PARENT's attribute if and only if it is CONSTANT
        # within the parent key: count(DISTINCT (key, value)) equals
        # count(DISTINCT key). That is exact. Anything else is left alone.
        for pk in parent_keys:
            if pk == c:
                continue
            pe = esc(pk)
            n_k, n_kc, d_s = q(
                f"SELECT count(DISTINCT k), count(*), sum(v) FROM ("
                f"SELECT DISTINCT nullif(trim({pe}),'') k, "
                f"TRY_CAST(trim({e}) AS DOUBLE) v FROM {rel}) "
                f"WHERE k IS NOT NULL AND v IS NOT NULL")[0]
            if not n_k or n_kc != n_k:
                continue
            if d_s is not None and s and abs(d_s - s) / abs(s) > 0.01:
                out["money"][c]["dedup"][pk] = {"sum": d_s, "keys": n_k}

    # --- the subaward fence, measured rather than quoted -------------------
    # The one money rule in this project that is a FILTER rather than a
    # caveat, and the only one where the delivered file can prove its own
    # overstatement. Measured here so no paper has to carry a hand-typed
    # percentage - three different values have circulated.
    if did == "subcontracting" and {"duplicate_status", "subaward_exceeds_prime_flag",
                                    "subaward_amount"} <= set(low):
        u_n, u_s = q(f"SELECT count(*), sum(TRY_CAST(trim("
                     f"{esc(low['subaward_amount'])}) AS DOUBLE)) FROM {rel}")[0]
        f_n, f_s = q(
            f"SELECT count(*), sum(TRY_CAST(trim({esc(low['subaward_amount'])}) AS DOUBLE)) "
            f"FROM {rel} WHERE lower(coalesce(trim("
            f"{esc(low['duplicate_status'])}),'')) = 'primary' "
            f"AND lower(coalesce(trim("
            f"{esc(low['subaward_exceeds_prime_flag'])}),'')) <> 'yes'")[0]
        out["subaward_fence"] = {"unfiltered_rows": u_n, "unfiltered_sum": u_s,
                                 "filtered_rows": f_n, "filtered_sum": f_s,
                                 "removed": (u_s or 0) - (f_s or 0),
                                 "over_correct_pct": (((u_s or 0) - (f_s or 0))
                                                      / f_s * 100) if f_s else None}

    # --- the gaming denominator, measured rather than quoted ---------------
    # SEVEN values circulated for this before the table was made to answer it.
    if did == "gaming" and "cedar_place_id" in low:
        c = esc(low["cedar_place_id"])
        out["gaming_denominator"] = q(
            f"SELECT count(DISTINCT nullif(trim({c}),'')) FROM {rel}")[0][0]

    # --- year span ---------------------------------------------------------
    out["years"] = {}
    for name in YEAR_COLS:
        if name not in low:
            continue
        c = esc(low[name])
        r = q(f"SELECT min(TRY_CAST(trim({c}) AS INTEGER)), "
              f"max(TRY_CAST(trim({c}) AS INTEGER)), "
              f"count(*) FILTER (WHERE TRY_CAST(trim({c}) AS INTEGER) IS NULL) "
              f"FROM {rel}")[0]
        if r[0] is not None:
            out["years"][low[name]] = {"min": r[0], "max": r[1], "unparsed": r[2]}
    con.close()
    return out


# ---------------------------------------------------------------------------
# THE SUPPORTING RECORD - quoted, with its source named
# ---------------------------------------------------------------------------
def manifest() -> dict:
    import csv
    p = DIST / "MANIFEST.csv"
    if not p.exists():
        raise SystemExit(f"FATAL: {p} is missing. Run 1137 first.")
    with p.open(encoding="utf-8", newline="") as fh:
        return {r["dataset"]: r for r in csv.DictReader(fh)}


def contracts() -> dict:
    p = DOCS / "schema" / "dataset_contracts.json"
    if not p.exists():
        return {}
    return {c["collection"]: c
            for c in json.loads(p.read_text(encoding="utf-8"))["contracts"]}


def attribution_vocabulary() -> dict:
    p = DOCS / "schema" / "attribution_method_vocabulary.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def readiness() -> dict:
    """dataset -> (status, row) from the GENERATED scoreboard, not from prose."""
    p = DOCS / "DATASET_READINESS.md"
    out = {}
    if not p.exists():
        return out
    for line in p.read_text(encoding="utf-8").split("\n"):
        m = re.match(r"^\|\s*`([a-z_\-]+)`\s*\|\s*\*\*(\w+)\*\*\s*\|(.*)$", line.strip())
        if m:
            out[m.group(1)] = (m.group(2), m.group(3).strip().rstrip("|"))
    return out


def money_fences() -> dict:
    """table.csv -> the verbatim 'one-line answer per table' row, and its blocks.

    Quoted, not re-derived. `docs/MONEY_TOTALLING_RULES.md` is authoritative on
    which columns may be summed; deriving that from the data is the mistake the
    document exists to prevent.
    """
    p = DOCS / "MONEY_TOTALLING_RULES.md"
    rows, blocks = {}, {}
    if not p.exists():
        return {"rows": rows, "blocks": blocks}
    cur = None
    for line in p.read_text(encoding="utf-8").split("\n"):
        mb = re.match(r"<!--\s*BEGIN\s+([A-Z0-9\-]+)\s*-->", line.strip())
        me = re.match(r"<!--\s*END\s+([A-Z0-9\-]+)\s*-->", line.strip())
        if mb:
            cur = mb.group(1)
            continue
        if me:
            cur = None
            continue
        m = re.match(r"^\|\s*`([A-Za-z0-9_\*\.\-]+\.csv)`", line.strip())
        if m:
            rows.setdefault(m.group(1), line.strip())
        for t in re.findall(r"`([A-Za-z0-9_\-]+\.csv)`", line):
            if cur:
                blocks.setdefault(t, set()).add(cur)
    return {"rows": rows, "blocks": blocks}


def doc_hits(did: str, flagship: str, docname: str, cap: int = 10) -> list:
    """Lines in a standing doc that name this dataset or its flagship table."""
    p = DOCS / docname
    if not p.exists():
        return []
    needles = {f"`{did}`", f"`{flagship}`", flagship}
    hits, head = [], ""
    for i, line in enumerate(p.read_text(encoding="utf-8").split("\n"), 1):
        if line.startswith("#"):
            head = line.lstrip("#").strip()
        if any(n in line for n in needles):
            t = line.strip()
            if len(t) > 260:
                t = t[:257] + "..."
            hits.append((i, head, t))
        if len(hits) >= cap:
            break
    return hits


# ---------------------------------------------------------------------------
# RENDER
# ---------------------------------------------------------------------------
def _n(v):
    return "-" if v is None else f"{v:,}"


def _usd(v):
    return "-" if v is None else f"${v:,.2f}"


def render_absent(did: str, man: dict) -> tuple[str, str]:
    """Both generated blocks, for a dataset whose spreadsheet is not on disk.

    FLAG, NEVER DELETE. The paper is still written and still managed; what it
    says is that the artefact every figure would have been measured from is
    absent, so no figure is stated. `verify` then fails for the right reason.
    """
    row = man.get(did, {})
    name = row.get("name", did)
    flag = FLAGSHIP.get(did, row.get("flagship", ""))
    ident = "\n".join([
        MARK_ID_B, "",
        f"**`{did}` — {name}.** "
        f"**THE DELIVERED FILE `dist/customer/{did}.csv` IS NOT ON DISK.** "
        f"`dist/customer/MANIFEST.csv` still claims it at "
        f"{row.get('rows', '?')} rows x {row.get('columns', '?')} columns, "
        f"written by `code/1137_customer_dataset_combine.py`, so the manifest "
        f"and the directory disagree and the directory is the one a customer "
        f"would be handed. [measured " + TODAY + "]", "",
        "> **No figure in this paper's Appendix M could be measured**, because "
        "the artefact every figure is measured *from* is absent. Nothing has "
        "been estimated, carried over from a previous build, or read out of a "
        "build log to fill the gap — a methodology paper that guesses its own "
        "dataset's shape is worse than one that says it cannot see it.",
        ">",
        f"> The hand-written body between the EDITORIAL markers is untouched "
        f"and is still the record of how `{flag}` was built. Re-run "
        f"`py -3 code/1137_customer_dataset_combine.py build {did}`, then "
        f"`py -3 code/1143_methodology_papers.py build {did}`.",
        ">",
        f"> Generated {TODAY}. "
        "`py -3 code/1143_methodology_papers.py verify` **fails** while this "
        "block is present.",
        "", MARK_ID_E])
    meas = "\n".join([
        MARK_M_B, "", "---", "",
        "# Appendix M — NOT MEASURED: the delivered file is absent", "",
        f"`dist/customer/{did}.csv` was not on disk when this paper was "
        f"generated on {TODAY}. Every section this appendix normally carries — "
        "sources as the rows record them, the pipeline, the identity layer and "
        "what `attribution_method` means here, what is withheld, the money "
        "fence, and the fingerprint — is measured from that file and from "
        "nothing else. None of it is stated.", "",
        "## M7 · Fingerprint", "",
        "```json",
        json.dumps({"dataset": did, "file": f"dist/customer/{did}.csv",
                    "file_absent": True, "measured": TODAY}, indent=2),
        "```", "",
        "`verify` exits 1 on this block. That is the intended behaviour: a "
        "dataset with no spreadsheet has no methodology paper that can be "
        "trusted, and the failure is the notification.", "",
        MARK_M_E])
    return ident, meas


def render_identity(did: str, m: dict, man: dict, ready: dict, con: dict) -> str:
    row = man.get(did, {})
    name = row.get("name", did)
    shelf = row.get("shelf", "")
    sold = row.get("sold_through", "")
    store = row.get("storefront", "")
    flag = FLAGSHIP.get(did, row.get("flagship", ""))
    st, detail = ready.get(did, ("NOT_TESTED", ""))
    mb = m["bytes"] / 1e6 if m.get("exists") else 0
    withheld = row.get("rows_withheld", "0")
    why = row.get("withheld_why", "")

    L = [MARK_ID_B, ""]
    L.append(f"**`{did}` — {name}.** Delivered as `dist/customer/{did}.csv`: "
             f"**{_n(m.get('rows'))} rows × {_n(m.get('columns'))} columns, "
             f"{mb:,.1f} MB**, built from the flagship table "
             f"`data/clean/{flag}`. Shelf `{shelf}`; sold through **{sold}**; "
             f"{'on' if store == 'Y' else 'NOT on'} the Cedar Press storefront. "
             f"Readiness **{st}**. [measured {TODAY} from the delivered file]")
    L.append("")
    if withheld and withheld not in ("0", ""):
        L.append(f"**{withheld} rows were withheld** from this delivery "
                 f"({why or 'reason not recorded'}); §M4 has the count by cause.")
        L.append("")
    L += [
        "> **This block and Appendix M at the foot of this paper are GENERATED** "
        "by `code/1143_methodology_papers.py` from the delivered file itself, on "
        "every build — the same reason the codebooks are generated. Do not "
        "hand-edit either; the next build overwrites them.",
        ">",
        f"> Everything between `<!-- BEGIN EDITORIAL:{did} -->` and "
        f"`<!-- END EDITORIAL:{did} -->` is **hand-written and preserved "
        f"byte-for-byte** across rebuilds. Put prose there and nowhere else.",
        ">",
        "> This paper is **not** the codebook. "
        f"`dist/customer/{did}__CODEBOOK.md` carries the grain, the folded-in "
        "tables and the per-column fill rates, and `__NOTES.txt` carries the "
        "same for a person. This paper says how the dataset came to exist and "
        "why you should believe it.",
        ">",
        f"> Generated {TODAY}. "
        "`py -3 code/1143_methodology_papers.py verify` **fails** if the "
        "delivered file has moved since — see §M7.",
        "", MARK_ID_E,
    ]
    return "\n".join(L)


def render_measured(did: str, m: dict, man: dict, ready: dict, con: dict,
                    vocab: dict, fences: dict, editorial: str = "") -> str:
    row = man.get(did, {})
    flag = FLAGSHIP.get(did, row.get("flagship", ""))
    L = [MARK_M_B, "", "---", "", "# Appendix M — measured from the delivered file", ""]
    L.append(f"*Generated {TODAY} by `code/1143_methodology_papers.py` from "
             f"`dist/customer/{did}.csv`, read whole with duckdb and never "
             f"sampled. Not from `data/clean/`, not from a build log, not from "
             f"`MANIFEST.csv`. Where this appendix and a document disagree, "
             f"**the delivered file is right** and `verify` prints the "
             f"disagreement rather than smoothing it over.*")
    L.append("")
    L.append("*Grain, folded-in tables and per-column fill rates are in "
             f"`dist/customer/{did}__CODEBOOK.md` and are deliberately not "
             "repeated here.*")
    L.append("")

    # ---- M1 sources -------------------------------------------------------
    L += ["## M1 · Sources, as the delivered rows themselves record them", ""]
    if not m.get("sources"):
        L.append("**No `source_*` column survives into the delivered file.** "
                 "That is a coverage fact and a real limit: a buyer holding "
                 "this spreadsheet cannot tell which upstream object a given "
                 "row came from without going back to the build log. The "
                 "narrative inventory of sources is in §1 of this paper.")
        L.append("")
    for cname, info in m["sources"].items():
        if info["kind"] == "host":
            L.append(f"**`{cname}`** — {_n(info['filled'])} of "
                     f"{_n(m['rows'])} rows carry one. Hosts, by row count:")
            L.append("")
            L.append("| host | rows |")
            L.append("|---|---:|")
            for h, n in info["values"]:
                L.append(f"| `{h or '(unparsed)'}` | {_n(n)} |")
            L.append("")
            continue
        if info["filled"] == 0:
            L.append(f"**`{cname}`** — present in the schema and **blank on "
                     f"every one of the {_n(m['rows'])} delivered rows**. That "
                     f"is a coverage fact, not a formatting one: this dataset "
                     f"does not record that piece of provenance per row. The "
                     f"column is kept rather than dropped so the schema does "
                     f"not depend on which rows shipped.")
            L.append("")
            continue
        L.append(f"**`{cname}`** — {_n(info['filled'])} of {_n(m['rows'])} rows "
                 f"populated, {_n(info['distinct'])} distinct value"
                 f"{'' if info['distinct'] == 1 else 's'}"
                 f"{', 15 most common shown' if info.get('truncated') else ''}:")
        L.append("")
        L.append("| value | rows |")
        L.append("|---|---:|")
        for v, n in info["values"]:
            L.append(f"| `{v}` | {_n(n)} |")
        L.append("")

    L += [
        "### The terms rulings that bind this dataset",
        "",
        "Quoted from `docs/PUBLICATION_POLICY.md`, which holds the rulings; "
        "this paper does not restate them from memory.",
        "",
        "- **Owner ruling, 2026-09-02** (`<!-- BEGIN "
        "TERMS-OWNER-RULING-2026-09-02 -->`): *\"So tribal websites, I actually "
        "don't care if they say it does scrape. Because if it's publicly "
        "available and you can scrape it, scrape it.\"* A tribal entity's own "
        "public pages may be harvested regardless of a terms statement. "
        "`source_terms_status = TERMS_STATED_RESTRICTIVE` on a Native entity's "
        "own site is now **a recorded observation, not a gate**.",
        "- **Four things that ruling does NOT touch, and none is a terms "
        "question:** (1) technical access controls — nothing login-gated, no "
        "admin or staging paths, no exploiting a misconfiguration; (2) a "
        "natural person's data held apart from their public role — home "
        "address, personal email or phone, DOB, SSN/TIN; (3) non-tribal "
        "licensors — EMMA/MSRB bars redistribution of its output \"sold or "
        "free of charge\" and names \"any manual process\", with CUSIP Global "
        "Services as a second licensor; (4) proprietary identifiers — Casino "
        "City, D-U-N-S — held internally, never shipped.",
        "- **A terms restriction is scoped to the SOURCE that stated it, not "
        "to the nation** (`<!-- BEGIN TERMS-SCOPE -->`), and it does not bind "
        "a third party's filing of the same fact.",
        "",
    ]

    # ---- M2 pipeline ------------------------------------------------------
    L += ["## M2 · How the rows were built — the pipeline, in order", ""]
    c = con.get(did)
    if not c:
        L.append(f"No contract is registered for `{did}` in "
                 "`docs/schema/dataset_contracts.json`. That is itself a gap.")
        L.append("")
    else:
        L.append(f"**One documented rebuild:** `{c.get('rebuild_command')}`. "
                 f"`py -3 code/build.py plan {did}` prints the ordering below "
                 f"live; it is reproduced here so the paper stands alone.")
        L.append("")
        L.append(f"The collection holds **{c.get('n_tables')} tables**. Those "
                 f"with a named build stage, flagship first:")
        L.append("")
        L.append("| table | rebuilt by | then enriched by (must run LAST) | status |")
        L.append("|---|---|---|---|")
        tabs = sorted(c.get("tables", []),
                      key=lambda t: (t["table"] != flag, t["table"]))
        shown = 0
        for t in tabs:
            rb, eb = t.get("rebuilt_by") or [], t.get("enriched_by") or []
            if not rb and not eb and t["table"] != flag:
                continue
            star = " **(flagship)**" if t["table"] == flag else ""
            L.append(f"| `{t['table']}`{star} | "
                     f"{', '.join(f'`{x}`' for x in rb) or '—'} | "
                     f"{', '.join(f'`{x}`' for x in eb) or '—'} | "
                     f"{t.get('status', '')} |")
            shown += 1
        if shown == 0:
            L.append("| — | — | — | — |")
        L.append("")
        warn = sorted({w for t in c.get("tables", [])
                       for w in (t.get("never_run_warning") or [])})
        if warn:
            L.append(f"**`NEVER_RUN` applies here:** {', '.join(f'`{w}`' for w in warn)}. "
                     "`code/cedar_pipeline.NEVER_RUN` is the only authority on "
                     "run safety — never read that claim out of prose.")
            L.append("")
        L.append("**A full rebuild and an in-place enricher on one file need an "
                 "ordering, and the enricher must run LAST.** A `.bak_*_pre<script>` "
                 "file sitting beside a table is the signal that an enricher has "
                 "touched it since the last build. This has cost this project four "
                 "reverts of one file in a single day.")
        L.append("")

    L.append(f"The delivered spreadsheet is then assembled by "
             f"`code/1137_customer_dataset_combine.py`, which folds supporting "
             f"tables onto the flagship **only where the measured cardinality on "
             f"the shared key is one**, reverts any join that moved the row "
             f"count, and prefixes every joined column with its source table's "
             f"stem. One-to-many tables contribute a count column instead of "
             f"rows, so a money total cannot be multiplied by a join.")
    L.append("")

    # ---- M3 attribution ---------------------------------------------------
    L += ["## M3 · How entities were attributed", ""]
    L.append("Cedar keys every dataset to one identity layer. `cedar_uid` is "
             "permanent and never reused; the human-readable handle retires "
             "when an entity is reclassified, so **join on `cedar_uid`, never "
             "on the handle**. A compound handle is canonical, not broken — "
             "stripping a suffix to make a join work turns joinable rows into "
             "unjoinable ones while looking like a normalisation.")
    L.append("")
    if not m.get("entity"):
        L.append("**The delivered file carries no `cedar_uid`, `tribe_id` or "
                 "`owner_hub_cedar_uid` column.** Where a dataset names parties "
                 "but keys none of them on the row, the link lives in a bridge "
                 "table and the codebook says which. A pipe-delimited list of "
                 "ids in a cell is **not** a join key; join through the bridge.")
        L.append("")
    if m.get("entity"):
        L.append("**Entity attachment in the delivered file:**")
        L.append("")
        L.append("| key column | rows carrying one | distinct values | coverage |")
        L.append("|---|---:|---:|---:|")
        for k, v in m["entity"].items():
            pct = 100.0 * v["filled"] / m["rows"] if m["rows"] else 0
            L.append(f"| `{k}` | {_n(v['filled'])} | {_n(v['distinct'])} | {pct:.1f}% |")
        L.append("")
        L.append("**An unkeyed row is often the right answer, not a defect.** "
                 "ADR-010 separates *\"we could not identify the entity\"* — a "
                 "defect — from *\"there is no single entity to identify\"* — the "
                 "correct representation. Coverage is measured against the "
                 "*resolvable* denominator, not the row count.")
        L.append("")

    has_am = "attribution_method" in {c.lower() for c in m.get("col_names", [])}
    L.append("### What `attribution_method` means **in this dataset**")
    L.append("")
    L.append("`docs/schema/attribution_method_vocabulary.json`, declared "
             "2026-09-02: *\"`attribution_method` is three different columns "
             "sharing a name — a join method, an evidence provenance, and a "
             "name-match algorithm. Each table is gated against its OWN "
             "vocabulary.\"* Reading one table's sense into another is how a "
             "containment match came to key a dollar.")
    L.append("")
    if has_am:
        L.append(ATTRIBUTION_SENSE.get(did, "**UNDECLARED — this is a defect. "
                                            "`verify` fails on it.**"))
    else:
        if m.get("vocab"):
            L.append("**This dataset carries no `attribution_method` column.** "
                     "The identity evidence it does carry is measured below. Do "
                     "not import another dataset's term list to interpret it.")
        else:
            L.append("**This dataset carries no `attribution_method` column and "
                     "no tier or method column of any kind.** Its rows are not "
                     "entity attributions — they are records of a published "
                     "event, and the entity link, where there is one, is made "
                     "through a bridge table rather than carried on the row. Do "
                     "not import another dataset's term list to interpret it.")
    L.append("")
    L.append("**And a RULED METHOD IS NOT A POSITIVE RULING.** "
             "`attribution_method` says WHO decided; `confidence_tier` says "
             "WHAT was decided. All 317 `elijah_ruling` EIN rows in the ledger "
             "are tier **X** — *negative* — and a script that read \"the method "
             "is in the RULED set\" as \"the answer was yes\" published 317 "
             "owner *exclusions* as confident attributions. Standing detector: "
             "`py -3 code/293_lint_bug_classes.py`. [from the record — "
             "`START_HERE.md`, defect class 1b]")
    L.append("")

    if m.get("vocab"):
        L.append("### Every identity, tier and method column, measured")
        L.append("")
        for cname, info in sorted(m["vocab"].items()):
            if info["distinct"] == 0:
                L.append(f"- **`{cname}`** — present but **blank on every one of "
                         f"the {_n(m['rows'])} rows**. Kept deliberately: "
                         "dropping a blank column would make the schema depend "
                         "on which rows shipped.")
                continue
            L.append(f"- **`{cname}`** — {_n(info['distinct'])} distinct value"
                     f"{'' if info['distinct'] == 1 else 's'}"
                     f"{' (40 most common shown)' if info.get('truncated') else ''}: "
                     + " · ".join(f"`{v}` {_n(n)}" for v, n in info["values"]))
        L.append("")

    tv = vocab.get("tables", {})
    named = [t for t in tv if t == flag or t.replace(".csv", "") in did]
    if named:
        L.append("### The frozen term list for this dataset's flagship")
        L.append("")
        L.append("A term listed in the registry is **FROZEN, not blessed**: the "
                 "declaration records what shipped on 2026-09-02 so a NEW term "
                 "cannot appear silently.")
        L.append("")
        for t in named:
            terms = tv[t]["terms"]
            L.append(f"`{t}` — {len(terms)} terms: "
                     + " · ".join(f"`{k}` {v:,}" for k, v in sorted(terms.items())))
        L.append("")

    L.append("### The evidence tiers")
    L.append("")
    L.append("| tier | what it means |")
    L.append("|---|---|")
    L.append("| **A** | an identifier (UEI, CAGE, EIN, declared parent UEI), or a "
             "human ruling. The only grade a dollar may be keyed on without "
             "corroboration |")
    L.append("| **B** | a strong name method with an independent corroborator, or "
             "inheritance from a tier-A parent |")
    L.append("| **C** | a weak method — containment, token subset — held as a "
             "candidate, not published as a fact |")
    L.append("| **X** | **refused.** A negative ruling. Never read as a "
             "confirmation |")
    L.append("")
    L.append("**A tier is INHERITED from the source row, never assigned by the "
             "consumer.** The exactness of the KEY says nothing about the "
             "correctness of the LINK: 873 of 1,104 EIN rows in the ledger sit "
             "on 52 entities carrying five or more EINs each, and 821 are tier B "
             "via `need_v6`, which is 6.5% accurate and never publishes alone. "
             "[from the record — `START_HERE.md`, defect class 1]")
    L.append("")

    # ---- M4 what is not in it --------------------------------------------
    L += ["## M4 · What is **not** in it, and why", ""]
    wh = row.get("rows_withheld", "0")
    if wh and wh not in ("0", ""):
        L.append(f"**{wh} rows were harvested, held, and did not ship.** Cause "
                 f"as recorded by the publication gate: `{row.get('withheld_why') or 'unrecorded'}`. "
                 "The rows are not deleted; the gate is a publication decision, "
                 "not a data decision. [measured by "
                 "`code/1137_customer_dataset_combine.py` at build time]")
    else:
        L.append("**No row was withheld from this delivery.** Every row that "
                 "passed the collection's own inclusion test is in the "
                 "spreadsheet. [measured — `dist/customer/MANIFEST.csv`, "
                 "`rows_withheld = 0`]")
    L.append("")
    L.append("The row gate is `code/cedar_publication.row_ok`, applied "
             "identically by every publisher: a row is withheld if "
             "`publishable` is set to anything outside "
             "`{Y, y, 1, true, TRUE, blank}`, or if `source_terms_status` is "
             "outside `{SILENT, TERMS_STATED_NO_REUSE_RESTRICTION, blank}`. "
             "**A blank gate column means the gate was never evaluated for that "
             "row, not that it failed.**")
    L.append("")
    L.append("Two families are refused as **COLUMNS** rather than as rows, by "
             "`cedar_publication.publishable_columns`, because the row is ours "
             "and the field is not: the proprietary identifiers "
             "(`casino_city_id` — Casino City Press; the D-U-N-S family — Dun "
             "& Bradstreet), and personal data held apart from a public role "
             "(`owner_name_raw`, `email`, `phone`, `home_address`, "
             "`personal_email`, `ssn`, `tin`, `date_of_birth`, `officer_name`, "
             "`contact_name`).")
    L.append("")
    L.append("**The personal-data family became a column drop on 2026-09-02, "
             "and the change is worth understanding.** Until then it was a row "
             "gate only, and measured against the live tree that published "
             "**5 of the 587 rows** of `bia_tribal_leaders_directory.csv` — "
             "every row carrying a phone or an email was withheld whole — "
             "*and shipped the `phone` and `email` headers anyway on the five "
             "survivors*. Both halves of that were wrong. A tribal leader's "
             "name and office is a PUBLIC ROLE and belongs in the dataset; the "
             "phone number is the thing that must not travel. Dropping the "
             "field keeps 587 rows and publishes no contact data, where the "
             "row gate kept 5 rows and still advertised two contact columns. "
             "`row_ok` keeps its check as a **backstop**, for a personal field "
             "arriving under a name the list does not yet know. [from the "
             "record — the docstring of "
             "`cedar_publication.publishable_columns`, 2026-09-02]")
    L.append("")
    for docname, label in (("WHAT_IS_MISSING.md", "Known gaps"),
                           ("KNOWN_ISSUES.md", "Open issues")):
        hits = doc_hits(did, flag, docname, cap=8)
        if not hits:
            continue
        L.append(f"### {label} — every line in `docs/{docname}` that names this "
                 f"dataset or its flagship")
        L.append("")
        for ln, head, txt in hits:
            L.append(f"- **L{ln}** *(under “{head}”)* — {txt}")
        L.append("")

    # ---- M5 money ---------------------------------------------------------
    L += ["## M5 · The money rules — which columns may be summed", ""]
    money = {k: v for k, v in (m.get("money") or {}).items() if v["is_money"]}
    notmoney = {k: v for k, v in (m.get("money") or {}).items() if not v["is_money"]}
    if not money:
        L.append("**This dataset carries no numeric money column.** Nothing in "
                 "it may be presented as a dollar total, and a reader who needs "
                 "one has to go to the money dataset that holds it. A structure "
                 "or directory table with no money column is not an incomplete "
                 "money table.")
        L.append("")
    else:
        L.append("Measured over the delivered file. **A sum printed here is the "
                 "unfiltered arithmetic sum of the column and is NOT necessarily "
                 "a figure a buyer may quote** — the fence below says which are "
                 "and which are not.")
        L.append("")
        stems = sorted({t.split("(")[0].strip().replace(".csv", "")
                        for t in (row.get("tables_folded_in") or "").split(";")
                        if t.strip()})
        L.append("| column | rows populated | distinct values | sum (unfiltered) "
                 "| min | max |")
        L.append("|---|---:|---:|---:|---:|---:|")
        for k, v in sorted(money.items()):
            joined = any(k.startswith(st + "__") for st in stems)
            mark = " ⚠ **joined**" if joined else ""
            L.append(f"| `{k}`{mark} | {_n(v['filled'])} | {_n(v.get('distinct'))} "
                     f"| {_usd(v['sum'])} | {_usd(v['min'])} | {_usd(v['max'])} |")
        L.append("")
        jm = sorted(k for k in money
                    if any(k.startswith(st + "__") for st in stems))
        if jm:
            L.append("**⚠ A column carrying a folded-in table's stem prefix is "
                     "that table's grain repeated onto flagship rows, and "
                     "row-summing it multiplies.** "
                     + ", ".join(f"`{k}`" for k in jm)
                     + " came from a supporting table joined one-to-one onto "
                     "the flagship; the figure belongs to the entity or award "
                     "the supporting table keys on, not to the row it is "
                     "printed on. Sum it once per that key, never down the "
                     "column. This is the owner-grain trap that turns "
                     "$176.74B into $6,535.96B — a 36.98× inflation — in "
                     "`contractor_ranking.csv`. [from the record — "
                     "`docs/MONEY_TOTALLING_RULES.md`, block `GRAIN-WS5`]")
            L.append("")
        ded = {k: v for k, v in money.items() if v.get("dedup")}
        if ded:
            L.append("**Which of these columns are a PARENT's figure printed "
                     "on a CHILD's row — measured, not asserted.** A column "
                     "appears below only where its value is *constant within* "
                     "the key named, which is proof it belongs to that key and "
                     "not to the row. The right-hand column is what it totals "
                     "once per key, and the multiple is what row-summing costs "
                     "you.")
            L.append("")
            L.append("| column | belongs to | row-summed | once per that key | "
                     "row-summing inflates by |")
            L.append("|---|---|---:|---:|---:|")
            for k, v in sorted(ded.items()):
                for pk, d in sorted(v["dedup"].items()):
                    infl = v["sum"] / d["sum"] if d["sum"] else None
                    L.append(f"| `{k}` | `{pk}` ({_n(d['keys'])} keys) | "
                             f"{_usd(v['sum'])} | {_usd(d['sum'])} | "
                             f"{('%.2f' % infl + chr(215)) if infl else '-'} |")
            L.append("")
            L.append("**The once-per-key figure is not automatically the "
                     "figure to publish either.** It is the arithmetic that "
                     "removes the repetition, nothing more; whether that total "
                     "is meaningful is the fence's question, not this table's. "
                     "A column absent from this table is *not* thereby "
                     "declared summable — it is only declared not to be "
                     "constant within any key this file carries.")
            L.append("")
    if notmoney:
        L.append("**Columns whose NAME looks like money and whose CONTENT is "
                 "not** — measured, not assumed, because a name test alone "
                 "promotes a 0/1 flag and a free-text field into a dollar "
                 "column, which is the mistake `517.MONEY_HINTS` made:")
        L.append("")
        for k, v in sorted(notmoney.items()):
            pct = 100.0 * v["numeric"] / v["filled"] if v["filled"] else 0
            why = v.get("why") or f"only {_n(v['numeric'])} of {_n(v['filled'])} populated values ({pct:.1f}%) parse as a number"
            L.append(f"- `{k}` — {why}. Not summable.")
        L.append("")

    fr = fences["rows"]
    fb = fences["blocks"]
    quoted = [flag] if flag in fr else []
    L.append("### The fence, quoted verbatim from `docs/MONEY_TOTALLING_RULES.md`")
    L.append("")
    L.append("That document is authoritative on which columns may be summed. It "
             "is **quoted here, never re-derived** — re-deriving a totalling "
             "rule from the data is precisely the error it exists to prevent.")
    L.append("")
    if quoted:
        L.append("| table | additive measure | sum it at | what double-counts |")
        L.append("|---|---|---|---|")
        for t in quoted:
            L.append(fr[t])
        L.append("")
    else:
        L.append(f"**`docs/MONEY_TOTALLING_RULES.md` states no one-line rule for "
                 f"`{flag}`.** Where this dataset carries a money column and the "
                 f"rules document does not fence it, treat that as an open item, "
                 f"not as permission.")
        L.append("")
    blks = sorted(fb.get(flag, set()))
    if blks:
        L.append(f"Marked blocks in that document that name `{flag}`: "
                 + ", ".join(f"`<!-- BEGIN {b} -->`" for b in blks) + ".")
        L.append("")

    if m.get("subaward_fence"):
        s = m["subaward_fence"]
        L.append("### The overstatement, measured from the delivered file")
        L.append("")
        L.append(f"Summing `subaward_amount` over all {_n(s['unfiltered_rows'])} "
                 f"delivered rows gives **{_usd(s['unfiltered_sum'])}**. **That "
                 f"figure must never be quoted.** Applying the fence — "
                 f"`duplicate_status = 'primary'` AND "
                 f"`subaward_exceeds_prime_flag <> 'yes'` — leaves "
                 f"{_n(s['filtered_rows'])} rows and "
                 f"**{_usd(s['filtered_sum'])}**. The rule removes "
                 f"{_usd(s['removed'])}.")
        L.append("")
        L.append(f"**State the denominator, every time.** An overstatement is "
                 f"measured against the truth, so the number to quote is "
                 f"**{s['over_correct_pct']:.1f}%** — summing unfiltered lands "
                 f"you that far above the correct total. The share-of-the-"
                 f"inflated-total figure is a different and much less alarming "
                 f"sentence about the same error, and is not what a warning is "
                 f"for. [measured {TODAY} from `dist/customer/subcontracting.csv`]")
        L.append("")
        L.append("And the corrected total is **still not additive with prime "
                 "contracting**. A subaward is a slice of a prime award Cedar "
                 "already publishes. Federal dollars obligated = primes; "
                 "subawards say where those dollars went next.")
        L.append("")

    if m.get("gaming_denominator") is not None:
        L.append("### The property denominator, settled by the table itself")
        L.append("")
        L.append(f"**{_n(m['gaming_denominator'])}** = "
                 f"`COUNT(DISTINCT cedar_place_id)` over the delivered file "
                 f"[measured {TODAY}]. Seven values circulated for this before "
                 f"the table was made to answer it — 787, 780, 734, 727, 725, "
                 f"717, 714. {_n(m['rows'])} is the ROW count, which is a "
                 f"different question: a facility row is not a property. Any "
                 f"share quoted about properties must use this denominator and "
                 f"say so.")
        L.append("")
        L.append("**The gaming revenue bounds must never be apportioned or "
                 "summed across facilities.** A bound is a constraint on one "
                 "facility's revenue, not a measurement of it, and the "
                 "regulator layer, the self-published layer and the "
                 "SEC-filed layer are three assertion classes that may never be "
                 "added to each other. [from the record — "
                 "`docs/MONEY_TOTALLING_RULES.md`, blocks `INT-2-GAMING`, "
                 "`GAMING-NR` and `SEC-GAMING`]")
        L.append("")

    if m.get("years"):
        L.append("### Time span, measured")
        L.append("")
        L.append("| year column | min | max | rows with no parseable year |")
        L.append("|---|---:|---:|---:|")
        for k, v in m["years"].items():
            L.append(f"| `{k}` | {v['min']} | {v['max']} | {_n(v['unparsed'])} |")
        L.append("")
        L.append("**Read a trend against the reporting regime, not as "
                 "behaviour.** `docs/ASSUMPTIONS_AND_LIMITATIONS.md` registers "
                 "the breaks; a rise that begins at a rule change is the rule "
                 "operating.")
        L.append("")

    # ---- M6 limits --------------------------------------------------------
    L += ["## M6 · Known limits, stated plainly", ""]
    st, detail = ready.get(did, ("NOT_TESTED", ""))
    L.append(f"**Readiness: {st}.** [measured — `docs/DATASET_READINESS.md`, "
             f"regenerated by `py -3 code/518_dataset_readiness.py`]")
    if detail:
        L.append("")
        L.append("| tables | grain | keys | duplicates | agg-unsafe | rebuild |")
        L.append("|---|---|---|---|---|---|")
        L.append(f"| {detail} |")
    L.append("")
    L.append("The twelve-point contract a dataset is held to — grain declared "
             "and validated; keys and cardinality measured, not guessed; "
             "duplicates removed or the distinguishing dimension declared; "
             "entity attachment where the subject is an entity; every harvested "
             "row in a named disposition bucket; unresolved identity conflicts "
             "never shipping as definite facts; no double-counting path; one "
             "documented rebuild that does not destroy later enrichment; an "
             "update runbook another session can execute from the document "
             "alone; regression and semantic-diff gates over the outputs; "
             "column hygiene; and an inclusion basis on every row.")
    L.append("")
    sparse = [c.strip() for c in (row.get("sparse_columns") or "").split(";") if c.strip()]
    if sparse:
        L.append(f"**{len(sparse)} column{'' if len(sparse) == 1 else 's'} "
                 f"{'is' if len(sparse) == 1 else 'are'} blank on every "
                 f"delivered row** and {'is' if len(sparse) == 1 else 'are'} "
                 f"kept deliberately. Dropping them would make the schema "
                 f"depend on which rows shipped, and a buyer diffing two "
                 f"deliveries would watch columns appear and vanish. Sparsity is "
                 f"a coverage fact. They are named in the codebook.")
        L.append("")
    L.append("**Do not sell past the evidence.** Where this paper states a "
             "figure it was measured on the date stamped beside it, from the "
             "file named beside it. Where it states a decision it names who "
             "made it. Anything not stated here is not known.")
    L.append("")

    # ---- M8 prose contradictions ------------------------------------------
    checks = PROSE_CHECKS.get(did, [])
    if checks:
        L += ["## M8 · Figures that have circulated in more than one value", ""]
        L.append("Each row below was re-measured from the delivered file just "
                 "now. The superseded values are the ones this project has "
                 "actually watched drift; where one still appears in this "
                 "paper's own hand-written body it is named, and **the "
                 "measured figure is the one that is right**.")
        L.append("")
        L.append("| figure | measured today | superseded values | still in this paper's prose? |")
        L.append("|---|---:|---|---|")
        for label, fn, stale in checks:
            try:
                val = fn(m)
            except Exception:
                val = None
            found = [x for x in stale if x in editorial]
            L.append(f"| {label} | **{_n(val) if isinstance(val, int) else (val or '—')}** | "
                     f"{', '.join(stale) or '—'} | "
                     f"{('⚠ **yes** — ' + ', '.join(found)) if found else 'no'} |")
        L.append("")
        anyfound = any(x in editorial for _, _, st in checks for x in st)
        if anyfound:
            L.append("**Where the prose above and this appendix disagree, this "
                     "appendix is right.** It was measured from "
                     f"`dist/customer/{did}.csv` on {TODAY}; the prose was "
                     "written against an earlier state of the same table. The "
                     "prose is left standing rather than silently corrected, "
                     "because a superseded figure that is *labelled* is "
                     "recoverable and one that has been overwritten is not — "
                     "and because the reasoning around it is usually still "
                     "sound even when the number under it has moved.")
            L.append("")

    # ---- M7 fingerprint ---------------------------------------------------
    L += ["## M7 · Fingerprint — what makes this paper stale", ""]
    L.append("`verify` re-measures the four values below against "
             f"`dist/customer/{did}.csv` and **exits 1 if any has moved**. A "
             "methodology paper is stale the moment its dataset is rebuilt, and "
             "a stale paper that cannot say so is worse than no paper.")
    L.append("")
    fp = {"dataset": did, "file": f"dist/customer/{did}.csv",
          "bytes": m.get("bytes"), "rows": m.get("rows"),
          "columns": m.get("columns"), "header_sha256": m.get("header_sha256"),
          "measured": TODAY}
    L.append("```json")
    L.append(json.dumps(fp, indent=2))
    L.append("```")
    L.append("")
    L.append(f"Cross-check against `dist/customer/MANIFEST.csv`, which "
             f"`code/1137_customer_dataset_combine.py` wrote at build time: it "
             f"records **{row.get('rows', '?')} rows × {row.get('columns', '?')} "
             f"columns**. The two agree"
             + ("." if str(row.get("rows")) == str(m.get("rows"))
                and str(row.get("columns")) == str(m.get("columns"))
                else " **— NO, THEY DO NOT. The delivered file is right and the "
                     "manifest is stale; re-run 1137.**"))
    L.append("")
    L += [MARK_M_E]
    return "\n".join(L)


# ---------------------------------------------------------------------------
# COMMANDS
# ---------------------------------------------------------------------------
def built_datasets() -> list:
    sh = shelves()
    out = sorted(d for d, s in sh.items() if s in BUILD_SHELVES)
    return out


def _title(did: str, man: dict) -> str:
    return f"# Methodology — {man.get(did, {}).get('name', did)}"


def cmd_build(only: str | None) -> int:
    man, con, ready = manifest(), contracts(), readiness()
    vocab, fences = attribution_vocabulary(), money_fences()
    ids = built_datasets()
    if only:
        if only not in ids:
            print(f"FATAL: `{only}` is not a built dataset. Built: {', '.join(ids)}")
            return 1
        ids = [only]
    PAPERS.mkdir(parents=True, exist_ok=True)
    for did in ids:
        path = PAPERS / f"{did}.md"
        prev = read_paper(path)
        if not prev["editorial"].strip():
            print(f"  ! {did:26s} NO EDITORIAL BODY — writing the generated "
                  f"frame with a placeholder. A human must fill it.")
            prev["editorial"] = (
                "> **This paper has no methodology body yet.** The generated "
                "blocks above and below are measured and correct; the argument "
                "— why each source was taken, what was refused, what a number "
                "means — has not been written. Write it here, between the "
                "EDITORIAL markers, and it will survive every rebuild.")
        m = measure(did)
        b, e = ed_markers(did)
        if m["exists"]:
            ident = render_identity(did, m, man, ready, con)
            meas = render_measured(did, m, man, ready, con, vocab, fences,
                                   prev["editorial"])
        else:
            ident, meas = render_absent(did, man)
        doc = "\n\n".join([
            _title(did, man),
            ident,
            b + "\n" + prev["editorial"] + "\n" + e,
            meas,
        ]) + "\n"
        path.write_text(doc, encoding="utf-8")
        tag = "migrated" if not prev["had_markers"] else "rebuilt"
        shape = (f"{m['rows']:>9,} rows x {m['columns']:>3} cols"
                 if m["exists"] else "  DELIVERED FILE ABSENT - not measured")
        print(f"  + {did:26s} {tag:9s} {len(doc):>8,} bytes  {shape}")
    _write_readme(man, ready)
    return 0


def _write_readme(man: dict, ready: dict) -> None:
    """The index, regenerated so it cannot disagree with the delivered set."""
    p = PAPERS / "README.md"
    keep = ""
    if p.exists():
        txt = p.read_text(encoding="utf-8")
        a = _split_on_marker_line(txt, "<!-- BEGIN EDITORIAL:README -->")
        i = (_split_on_marker_line(a[1], "<!-- END EDITORIAL:README -->")
             if a else None)
        if i is not None:
            keep = i[0].strip("\n")
        else:
            # migrate: everything from the first '---' rule onward is the
            # genuinely shared background and is worth keeping verbatim.
            keep = txt.split("\n---\n", 1)[1].strip("\n") if "\n---\n" in txt else ""
    ids = built_datasets()
    L = ["# Cedar Press methodology papers", "",
         f"*Index regenerated {TODAY} by `code/1143_methodology_papers.py`. "
         f"Do not hand-edit above the rule — edit the script, or put prose "
         f"inside the EDITORIAL block below.*", "",
         "One paper per **delivered** dataset. The set is "
         "`cedar_publication.BUILD_SHELVES` — the twelve on the Cedar Press "
         f"storefront plus gaming, which ships through Cedar Grove — "
         f"**{len(ids)} papers**, and `N_BUILT_EXPECTED` is "
         f"{N_BUILT_EXPECTED}.", "",
         "| paper | dataset | shelf | sold through | delivered rows | readiness |",
         "|---|---|---|---|---:|---|"]
    for did in ids:
        r = man.get(did, {})
        st = ready.get(did, ("NOT_TESTED", ""))[0]
        L.append(f"| [`{did}.md`]({did}.md) | {r.get('name', did)} | "
                 f"`{r.get('shelf', '')}` | {r.get('sold_through', '')} | "
                 f"{int(r.get('rows') or 0):,} | {st} |")
    L += ["",
          "`_entity_layer.md` is kept and is **not** in that count. It is the "
          "shared identity chapter the other papers lean on — infrastructure, "
          "not a product, with no `dist/customer/` spreadsheet. Counting it as "
          "the thirteenth dataset is what hid the missing `nest` paper.", "",
          "**These are not the product copy and not the codebooks.** Customer-"
          "facing description lives in `docs/datasets/_descriptors.json`; field "
          "definitions, grain and per-column fill rates live in "
          "`dist/customer/<id>__CODEBOOK.md`.", "",
          "Each paper is three parts: a generated IDENTITY block, a hand-written "
          "EDITORIAL block preserved byte-for-byte across rebuilds, and a "
          "generated **Appendix M** measured from the delivered file. "
          "`py -3 code/1143_methodology_papers.py verify` fails when a paper is "
          "missing, has no editorial body, or has gone stale against its "
          "dataset.", "", "---", "",
          "<!-- BEGIN EDITORIAL:README -->", keep, "<!-- END EDITORIAL:README -->", ""]
    p.write_text("\n".join(L), encoding="utf-8")
    print(f"  + README.md                  regenerated, "
          f"{len(ids)} papers indexed")


def cmd_verify() -> int:
    man, fails = manifest(), []
    ids = built_datasets()
    if len(ids) != N_BUILT_EXPECTED:
        fails.append(f"BUILD SET: {len(ids)} datasets, expected "
                     f"{N_BUILT_EXPECTED}. A silent extra dataset is a defect.")
    for did in ids:
        path = PAPERS / f"{did}.md"
        if not path.exists():
            fails.append(f"{did}: NO PAPER at docs/methodology/{did}.md")
            continue
        txt = path.read_text(encoding="utf-8")
        b, e = ed_markers(did)
        after = _split_on_marker_line(txt, b)
        inner = _split_on_marker_line(after[1], e) if after else None
        if inner is None:
            fails.append(f"{did}: no EDITORIAL marker pair on its own line - "
                         f"the paper is unmanaged and a rebuild would destroy "
                         f"it")
            continue
        body = inner[0].strip()
        if len(body) < 400:
            fails.append(f"{did}: EDITORIAL body is {len(body)} bytes. An "
                         f"all-generated paper is a codebook with a different "
                         f"filename.")
        if _split_on_marker_line(txt, MARK_M_B) is None:
            fails.append(f"{did}: no Appendix M")
            continue
        mblk = _split_on_marker_line(txt, MARK_M_B)
        mfp = (re.search(r"```json\s*(\{.*?\})\s*```", mblk[1], re.S)
               if mblk else None)
        if not mfp:
            fails.append(f"{did}: no §M7 fingerprint — staleness cannot be tested")
            continue
        fp = json.loads(mfp.group(1))
        live = measure(did)
        if not live["exists"]:
            fails.append(f"{did}: dist/customer/{did}.csv IS NOT ON DISK. The "
                         f"manifest claims {man.get(did, {}).get('rows', '?')} "
                         f"rows. Re-run 1137 for this dataset, then 1143.")
            print(f"  FAIL {did:26s} delivered file absent")
            continue
        if fp.get("file_absent"):
            fails.append(f"{did}: the paper records the delivered file as "
                         f"absent, but it is present now "
                         f"({live['rows']:,} rows). Re-run `build {did}`.")
        for k in ("bytes", "rows", "columns", "header_sha256"):
            if fp.get(k) != live.get(k):
                fails.append(f"{did}: STALE — {k} recorded {fp.get(k)!r}, "
                             f"delivered file is {live.get(k)!r}. Re-run "
                             f"`build {did}`.")
        r = man.get(did, {})
        if str(r.get("rows")) != str(live["rows"]):
            fails.append(f"{did}: MANIFEST says {r.get('rows')} rows, delivered "
                         f"file has {live['rows']}. The file wins; re-run 1137.")
        if "attribution_method" in {c.lower() for c in live["col_names"]} \
                and did not in ATTRIBUTION_SENSE:
            fails.append(f"{did}: carries `attribution_method` with no declared "
                         f"sense in 1143.ATTRIBUTION_SENSE. It means three "
                         f"different things across the tree; say which.")
        print(f"  {'FAIL' if any(did + ':' in f for f in fails) else 'ok  '} "
              f"{did:26s} {live['rows']:>9,} rows x {live['columns']:>3} cols")
    for extra in sorted(PAPERS.glob("*.md")):
        did = extra.stem
        if did in ids or did in NON_DATASET_PAPERS:
            continue
        fails.append(f"{did}: a paper exists that no built dataset claims "
                     f"(docs/methodology/{did}.md)")
    print()
    if fails:
        print(f"VERIFY FAILED - {len(fails)} problem(s):")
        for f in fails:
            print(f"  - {f}")
        return 1
    print(f"VERIFY OK - {len(ids)}/{N_BUILT_EXPECTED} papers, each with an "
          f"editorial body and a fingerprint that matches its delivered file.")
    return 0


def cmd_report() -> int:
    man, ready = manifest(), readiness()
    ids = built_datasets()
    print(f"THIRTEEN DATASETS, THIRTEEN METHODOLOGY PAPERS  ({TODAY})")
    print(f"build set = {' + '.join(BUILD_SHELVES)}  "
          f"(storefront = {' + '.join(STOREFRONT_SHELVES)})")
    print()
    print(f"{'dataset':26s} {'shelf':6s} {'paper':>9s} {'editorial':>10s} "
          f"{'appendix':>9s}  readiness")
    print("-" * 82)
    for did in ids:
        p = PAPERS / f"{did}.md"
        size = f"{p.stat().st_size:,}" if p.exists() else "MISSING"
        ed = "-"
        ap = "-"
        if p.exists():
            txt = p.read_text(encoding="utf-8")
            b, e = ed_markers(did)
            after = _split_on_marker_line(txt, b)
            inner = _split_on_marker_line(after[1], e) if after else None
            ed = f"{len(inner[0].strip()):,}" if inner else "unmarked"
            ap = "yes" if _split_on_marker_line(txt, MARK_M_B) else "no"
        print(f"{did:26s} {man.get(did, {}).get('shelf', ''):6s} {size:>9s} "
              f"{ed:>10s} {ap:>9s}  {ready.get(did, ('NOT_TESTED',))[0]}")
    print()
    missing = [d for d in ids if not (PAPERS / f"{d}.md").exists()]
    print(f"{len(ids) - len(missing)}/{len(ids)} papers present"
          + (f"; MISSING: {', '.join(missing)}" if missing else ""))
    print("\nrun `build` to (re)generate, `verify` to fail on missing or stale.")
    return 0


def main() -> int:
    args = sys.argv[1:]
    cmd = args[0] if args else "report"
    if cmd == "report":
        return cmd_report()
    if cmd == "build":
        return cmd_build(args[1] if len(args) > 1 else None)
    if cmd == "verify":
        return cmd_verify()
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
