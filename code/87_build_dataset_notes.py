#!/usr/bin/env python3
"""
Cedar Press - 87: The notes contract each dataset ships with.

ELIJAH, 2026-08-06
------------------
"how about we have a pdf thats branded and more elegant instead, with notes and
 the terms in one ... this terminal im just focused on building the datasets and
 pipelines for them, if that makes sense, then the wiring me and Havlaa will
 work on."

So this script does NOT render anything. It emits the CONTENT as a contract the
app repo renders into a branded PDF. Presentation lives where the brand lives;
the facts live where the data lives, and they are versioned together.

The earlier .xlsx build is withdrawn. Its content survives as sections here -
that part was never about Excel.

WHAT SHIPS TO A SUBSCRIBER
--------------------------
    <name>.csv          the data. CSV, always, uncapped.
    <name>_notes.pdf    branded, rendered by the app from notes.json
    notes.json          this file. the contract.

CSV IS NOT NEGOTIABLE, AND HERE IS THE NUMBER
---------------------------------------------
    faads_transactions_all_agencies.csv   2,769,748 rows
    Excel worksheet maximum               1,048,576 rows

That file loses 1,721,172 rows in a worksheet, SILENTLY - Excel truncates
without an error and the sheet reads as complete. This project has already
been bitten by exactly that, in the CBP extract that arrived capped at
1,048,576 and looked whole. Research-ready also means a script can read it.

THE CONTRACT
------------
notes.json per dataset:

    identity      name, file, vintage, rows, columns, sha256
    coverage      year span, entity count, what is in and out
    codebook      public variables only, never internal
    reading       what a zero, a negative and a blank mean
    comparability breaks that make a time series lie
    research_ready  properties, NOT methods
    terms         authorised use
    citation      required form

Every section is a list of {heading, body} or typed rows, so the renderer never
has to parse prose to lay it out.

Writes dist/<dataset>/notes.json
       dist/<dataset>/NOTES.md      same content, readable without the app
       dist/notes_index.json        every dataset, for the app to enumerate
"""

import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
DIST = CEDAR / "dist"
TODAY = date.today().isoformat()
XLSX_MAX = 1_048_576

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

TERMS = [
    ("What you may do", [
        "Use this dataset for research, analysis, and internal "
        "decision-making within your organisation.",
        "Publish findings, articles, reports, briefings, newsletters and "
        "academic papers derived from it, with the citation below.",
        "Quote and reproduce limited extracts - a figure, a table, a chart - "
        "inside that content.",
    ]),
    ("What you may not do", [
        "Redistribute the dataset, in whole or in substantial part, to anyone "
        "outside your subscribing organisation, including people who ask for "
        "it. Access is per subscribing organisation; a request from a third "
        "party is not a licence.",
        "Share access credentials or download links outside your "
        "organisation.",
        "Resell the data, or incorporate it into a product, platform, API, "
        "feed or derivative dataset that is sold, licensed or distributed to "
        "others.",
        "Use it to build or train a competing data product.",
        "Extract the entity crosswalk as a standalone deliverable.",
    ]),
    ("What is proprietary, stated precisely", [
        "CAGE codes, UEIs and EINs are public federal identifiers. Cedar "
        "Press claims no ownership of any individual identifier, and says so "
        "rather than overclaiming.",
        "What is proprietary is the CROSSWALK and the COMPILATION: which "
        "entity an identifier belongs to, the Cedar Press entity IDs and "
        "hierarchy, the confidence tiering, the rulings, the ownership "
        "determinations, and the assembled dataset as a whole. That linkage "
        "is the product.",
        "DUNS numbers are proprietary to a third party and are never "
        "published by Cedar Press.",
    ]),
    ("No warranty", [
        "Cedar Press assembles federal records and other public sources and "
        "documents what it measures. The data is provided as is. Known "
        "limits, oddities and breaks in comparability are stated here rather "
        "than omitted - read them before publishing a figure.",
    ]),
    ("Term", [
        "These terms apply for the duration of your subscription and survive "
        "it as to redistribution and resale. Data already downloaded may be "
        "retained and used for work already published.",
    ]),
]

# Properties, not methods - the same rule the codebooks follow.
RESEARCH_READY = [
    ("Stable entity identifiers",
     "Every entity carries a persistent Cedar Press ID that does not change "
     "between vintages, so panels join across releases and across datasets."),
    ("One resolved entity, not a name string",
     "Records attach to a determined entity rather than to whatever name the "
     "source printed. Name variants, subsidiaries and renamings resolve to "
     "the same ID."),
    ("Ownership and service kept apart",
     "Who owns an entity and who an entity serves are separate fields and are "
     "never collapsed into one another."),
    ("A roll-up hierarchy",
     "Immediate parent and ultimate parent are both present, so a figure can "
     "be reported at the subsidiary, the enterprise or the government level "
     "without rebuilding the structure yourself."),
    ("Confidence is on the row",
     "Attribution carries a tier. Determined and inferred attributions are "
     "distinguishable, and inferred ones never publish as settled."),
    ("Provenance on every row",
     "source_url and fetched_date travel with the record, so any figure can "
     "be traced to the document it came from."),
    ("Documented oddities",
     "What a zero, a negative and a blank mean is stated per field rather "
     "than left for you to infer."),
    ("Flagged breaks in comparability",
     "Where a source changed what it counts, who must report, or how it "
     "defines a category, the affected years are flagged."),
    ("Nominal and inflation-adjusted",
     "Dollar figures are given as reported and rebased to constant dollars, "
     "so a long series can be read either way."),
    ("No silent exclusions",
     "Rows we exclude from a total are flagged as columns rather than "
     "deleted, so our published figures can be reproduced or disagreed "
     "with."),
]

READING = [
    ("Negative", "Money was taken back - a deobligation, a cancelled option "
     "year, a corrected overstatement. Not an error, and it belongs in the "
     "total."),
    ("Zero", "An action occurred that moved no money - a change to the period "
     "of performance, an address correction, an administrative modification. "
     "Not a missing value."),
    ("Blank", "Not reported. The field was left empty at source. NOT zero - "
     "zero is an assertion, blank is a silence."),
]

YEAR_COLS = ("fiscal_year", "year", "calendar_year", "tax_year",
             "filing_year", "action_date", "open_date", "period_start")

# ---------------------------------------------------------------------------
# VENDOR-LICENSED DATA NEVER SHIPS.
#
# Elijah, 2026-08-06: "im basically saying we cant just resell casinocity lol,
# but it could be a source of internal fact checking if that makes sense."
#
# Exactly the DUNS rule, one level up. DUNS is held internally, joined on, and
# never published. A vendor's panel is the same: we may VALIDATE against it and
# we may not RESELL it.
#
# Measured 2026-08-06: all 64,181 rows of gaming_property_capacity_history.csv
# carry `source = "Casino City Press gaming-property panel"` and
# `value_basis = reported`. Not one independent observation. So the panel is an
# internal QA layer, and the PUBLISHED capacity layer must be rebuilt from
# regulators, compacts, environmental reviews and bond disclosures.
#
# This list is a HARD GATE, not a warning. A file named here does not get a
# notes contract, which means it does not get a bundle, which means it cannot
# ship by accident.
#
# 2026-08-26: IT WAS NOT A GATE. Both names below were declared here and
# referenced NOWHERE ELSE IN THIS FILE - `main()` filtered only on a leading
# underscore and two literal filenames. Measured that day, dist/07_gaming/ held
# live notes contracts for BOTH licensed files (129,404 rows of Casino City
# panel) and `casino_city_id` sat in the published gaming_facilities codebook.
# Three build logs cited this gate as enforced while relying on a dead constant.
#
# The gate is now wired in below and it is LOUD: a licensed file reaching this
# script is named on stdout and counted separately, because "it did not ship"
# and "we never noticed it was there" are different states and only one of them
# is safe. See docs/GAMING_SOURCE_AUDIT_2026-08-26.md.
# ---------------------------------------------------------------------------
LICENSED_SOURCE_FILES = {
    "gaming_property_capacity_history.csv":
        "100% Casino City Press panel - internal fact-checking only",
    "gaming_facility_metrics.csv":
        "Casino City Press derived - internal fact-checking only",
}

# Columns that identify a licensed vendor's record. Never published, for the
# same reason DUNS is not: it is the vendor's key, not our fact.
#
# `duns` is matched by PATTERN, not by equality, because it appears as
# `duns`, `duns_number`, `parent_duns`, `duns_9`... - the same reasoning as
# 41_build_codebooks.py's LICENSED_COLS regex. A licensed identifier must not
# survive because someone prefixed it.
LICENSED_COLS = {"casino_city_id"}
LICENSED_COL_PATTERN = re.compile(r"(^|_)duns(_|$)|^duns", re.I)

# The INTERNAL-BY-DECISION registry, IMPORTED rather than copied. A second
# copy of a list is a second place for it to go stale, which is exactly how
# LICENSED_SOURCE_FILES above sat declared-and-unreferenced for twenty days.
sys.path.insert(0, str(Path(__file__).parent))
import cedar_codebook as _CB                                   # noqa: E402
CB_INTERNAL_TABLES = _CB.INTERNAL_TABLES


def is_licensed_col(col):
    """A column that identifies a licensed vendor's record. Never published."""
    c = (col or "").strip().lower()
    return c in LICENSED_COLS or bool(LICENSED_COL_PATTERN.search(c))


def read_csv(p):
    if not Path(p).exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def header_of(p):
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return next(csv.reader(fh), [])


# Columns that record WHICH PUBLISHED STATE OF A SOURCE a row was cut from.
# Counted so a collection assembled from more than one of them cannot ship
# claiming a single vintage. See `docs/VINTAGE_MIXING_AUDIT.json`
# (code/334_audit_source_vintage_mixing.py) for the audit across all 276 tables.
VINTAGE_COLS = ("source_vintage", "source_archive_stamp", "vintage")


def scan(p):
    """Rows (CSV records, not physical lines), year span, entity count,
    THE SOURCE'S OWN LAST COVERED PERIOD, and the vintage composition.

    The last two are why this function changed on 2026-08-26.

    `vintage` used to be `TODAY` — the build date. `docs/REFRESH_CADENCE.md`
    Part 4 is explicit that this is a FALSE CITATION, and false in the
    direction that flatters us: prime data stops 2026-07-03 and assistance
    2026-06-30, so a collection stamped `vintage: 2026-08-26` overstates its
    own currency by 40 and 57 days respectively. **`vintage` must name the last
    date the SOURCE covers, never the date we pulled.**

    `source_vintages` is the second half of the same rule. A table assembled
    from more than one published state of its source cannot be described by one
    string at all. `federal_funding_transactions.csv` is the measured case:
    476,924 rows from a 2023-04-09 bulk download, 93,536 from archive stamp
    `20260806`, and 131,495 from `20260706` — and the composition is
    YEAR-ALIGNED, with FY2007 and FY2024–26 sitting on the older stamp. Rather
    than pick one and be wrong about the rest, the composition ships.
    """
    yrs, ents, n = set(), set(), 0
    last_date = None
    vintages = {}
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        r = csv.DictReader(fh)
        hdr = r.fieldnames or []
        yc = next((c for c in YEAR_COLS if c in hdr), None)
        ec = next((c for c in ("tribe_id", "entity_id", "cedar_entity_id")
                   if c in hdr), None)
        # The table's DECLARED period column beats any name list — one
        # declaration, read by 35, 102 and 301 alike.
        dc = None
        try:
            import cedar_period_columns as _PC
            dc = _PC.resolve(p.name, hdr)
        except Exception:
            dc = None
        if dc is None:
            dc = next((c for c in ("action_date", "filed_date", "notice_date",
                                   "period_end", "publication_date",
                                   "decision_date", "Event_Date", "event_date")
                       if c in hdr), None)
        vc = next((c for c in VINTAGE_COLS if c in hdr), None)
        for row in r:
            n += 1
            if yc:
                v = (row.get(yc) or "")[:4]
                if v.isdigit() and 1900 < int(v) < 2030:
                    yrs.add(int(v))
            if ec and (row.get(ec) or "").strip():
                ents.add(row[ec].strip())
            if dc:
                d = (row.get(dc) or "").strip()
                # ISO dates compare correctly as strings; a bare year does too.
                if d and (last_date is None or d > last_date):
                    last_date = d
            if vc:
                key = (row.get(vc) or "").strip() or "(unstamped)"
                vintages[key] = vintages.get(key, 0) + 1
    return (n, (min(yrs), max(yrs)) if yrs else None, len(ents), yc, ec,
            last_date, dc, vintages)


def sha256(p, cap=64 * 1024 * 1024):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        while (b := fh.read(1 << 20)):
            h.update(b)
            if fh.tell() > cap:
                return h.hexdigest() + f"-first{cap // 1024 // 1024}mb"
    return h.hexdigest()


def match_group(header, groups):
    """Assign a file to its codebook group by column overlap, so a renamed
    file cannot silently lose its notes."""
    hs = {h.strip().lower() for h in header}
    if not hs:
        return None, 0.0
    best, score = None, 0.0
    for g, vs in groups.items():
        ov = len(hs & vs) / len(hs)
        if ov > score:
            best, score = g, ov
    return best, score


def relevant_breaks(breaks, stem, group):
    out = []
    for b in breaks:
        ds = (b.get("dataset") or "").lower()
        if stem in ds or any(t and t in stem for t in ds.replace("/", " ").split()):
            out.append(b)
    return out


def md(notes):
    L = [f"# {notes['identity']['dataset']}", "",
         f"*Cedar Press · vintage {notes['identity']['vintage']}*", "",
         f"**{notes['identity']['rows']:,} rows · "
         f"{notes['identity']['columns']} columns**", ""]
    cv = notes["coverage"]
    if cv.get("year_span"):
        L += [f"Coverage: {cv['year_span'][0]}–{cv['year_span'][1]} "
              f"({cv['n_years']} years)"]
    if cv.get("n_entities"):
        L += [f"Entities: {cv['n_entities']:,}"]
    L += ["", "## Reading the data", ""]
    for k, v in notes["reading"]:
        L += [f"**{k}** — {v}", ""]
    if notes["comparability"]:
        L += ["## Comparability", "",
              "Where a source changed what it counts. Read this before "
              "publishing any figure over time.", ""]
        for b in notes["comparability"]:
            L += [f"**{b['break_period']}** ({b['verification_status']})  ",
                  f"{b['what_changed']}  ", f"*{b['effect_on_series']}*", ""]
    L += ["## What makes this research ready", ""]
    for k, v in notes["research_ready"]:
        L += [f"**{k}** — {v}", ""]
    L += ["## Codebook", "", "| Variable | Type | % filled | Description |",
          "|---|---|---|---|"]
    for c in notes["codebook"]:
        d = (c["description"] or "").replace("|", "\\|")
        L += [f"| `{c['variable']}` | {c['type']} | {c['pct_filled']} | {d} |"]
    L += ["", "## Terms of use", ""]
    for h, items in notes["terms"]:
        L += [f"### {h}", ""] + [f"- {i}" for i in items] + [""]
    L += ["## Citation", "", notes["citation"]["text"], ""]
    return "\n".join(L)


def main():
    print("=== Cedar Press 87: dataset notes contract ===\n")
    DIST.mkdir(exist_ok=True)

    # The withdrawn workbook build left artefacts. Remove them so nothing
    # stale ships.
    stale = list(DIST.rglob("*_notes.xlsx")) + list(DIST.rglob("TERMS.txt")) \
        + list(DIST.rglob("CITATION.txt"))
    for f in stale:
        f.unlink()
    if stale:
        print(f"removed {len(stale)} artefacts from the withdrawn .xlsx build\n")

    cb = read_csv(CLEAN / "codebook_master.csv")
    groups = defaultdict(set)
    for r in cb:
        groups[r["dataset"]].add((r.get("variable") or "").strip().lower())
    breaks = read_csv(CLEAN / "series_breaks.csv")
    print(f"codebook {len(cb):,} vars / {len(groups)} datasets · "
          f"{len(breaks)} series breaks\n")

    index, stats = [], Counter()
    licensed_hits, undocumented, internal_hits = [], [], []
    for p in sorted(CLEAN.glob("*.csv")):
        # A BACKUP IS NOT A DATASET. The house convention is
        # `<name>.csv.bak_<date>_pre<n>`, which this loop never saw because the
        # name does not end in `.csv`. Two agents wrote theirs the other way
        # round on 2026-09-02 - `native_owned_businesses.bak_2026-09-02_010526.csv`,
        # `prime_contracts.bak_2026-09-02_011205_pre772.csv` - and 87 issued
        # each of them a SHIPPING CONTRACT, put them in `dist/`, and counted
        # their rows in the ship rate. A buyer's bundle listing
        # `prime_contracts.bak_...` is the kind of thing that gets noticed
        # first and explained last.
        if (p.name.startswith("_")
                or ".bak" in p.name
                or p.name in ("codebook_master.csv", "series_breaks.csv")):
            continue

        # ------------------------------------------------------------------
        # THE LICENCE GATE. First test, before anything else, so a licensed
        # file cannot acquire a notes contract by any later path.
        #
        # It is LOUD by design. A silent refusal and a silent skip look
        # identical in the output, and this project has already paid for that
        # once: the gate was dead for twenty days and nobody could tell,
        # because a file that is refused and a file that is absent both
        # produce no line. Naming it is the difference.
        # ------------------------------------------------------------------
        if p.name in LICENSED_SOURCE_FILES:
            licensed_hits.append((p.name, LICENSED_SOURCE_FILES[p.name]))
            stats["REFUSED: vendor-licensed, may never ship"] += 1
            # Any contract written by an earlier run predates the gate and is
            # an active licensing exposure. Remove it here rather than leaving
            # it for a human to notice.
            for existing in DIST.rglob(f"{p.stem}.notes.json"):
                existing.unlink()
                stats["purged: stale licensed notes contract"] += 1
            for existing in DIST.rglob(f"{p.stem}.NOTES.md"):
                existing.unlink()
            continue

        # ------------------------------------------------------------------
        # INTERNAL BY DECISION. Second test, right after the licence gate and
        # for the same reason: a file we RULED not to ship and a file we never
        # noticed must not produce the same output.
        #
        # This is NOT the licence gate. A licensed file may never ship on
        # somebody else's terms. These are ours, the decision is recorded with
        # its reason in `cedar_codebook.INTERNAL_TABLES` and in
        # `docs/UNSHIPPED_TABLE_TRIAGE.json`, and it is reversible.
        #
        # It must sit ABOVE the match test, because two of them would
        # otherwise be matched by a SHIPPING SIBLING'S block and would ship
        # with no block of their own -
        # `cedar_identifier_ledger_tiered.csv` has a header identical to
        # `cedar_identifier_ledger_final.csv`. A subset header is a back door
        # onto the shelf.
        # ------------------------------------------------------------------
        if p.name in CB_INTERNAL_TABLES:
            internal_hits.append((p.name, CB_INTERNAL_TABLES[p.name]))
            stats["internal by decision, not a shipping gap"] += 1
            continue

        group, score = match_group(header_of(p), groups)
        if not group or score < 0.60:
            # NAME IT. A drop counter with no filename is how twenty days of
            # loss stayed invisible: 29 gaming tables and 33,817 rows were
            # skipped here every run and the output said only a number.
            undocumented.append((p.name, group, score))
            stats["skipped: not a documented dataset"] += 1
            continue

        n, span, n_ents, yc, ec, last_date, dc, vintages = scan(p)
        hdr = header_of(p)
        hs = {h.strip().lower() for h in hdr}

        # A licensed COLUMN is stripped even when the file itself publishes.
        # The vendor's key is the vendor's fact, exactly like DUNS.
        withheld = [h for h in hdr if is_licensed_col(h)]
        if withheld:
            stats["licensed columns withheld"] += 1
            print(f"  [licensed column] {p.name}: withholding "
                  f"{', '.join(withheld)}")
        hs -= {h.strip().lower() for h in withheld}

        rows_cb = [{"variable": r["variable"], "type": r.get("type", ""),
                    "units": r.get("units", ""),
                    "pct_filled": r.get("pct_filled", ""),
                    "description": r.get("description", "")}
                   for r in cb
                   if r["dataset"] == group
                   and (r.get("variable") or "").strip().lower() in hs
                   and not is_licensed_col(r.get("variable"))
                   and (r.get("access_tier") or "") != "internal"]

        # ---- THE CITATION FIELDS, and they are load-bearing ---------------
        # `vintage` names what the SOURCE covers. `built` names what we did.
        # Conflating them is the false citation named in REFRESH_CADENCE Part 4
        # and it is the one that flatters us, so it gets the careful treatment.
        if last_date:
            vintage = last_date
            vintage_basis = (f"maximum value of `{dc}` — the last period the "
                             f"SOURCE covers, not the date Cedar built or "
                             f"pulled the table")
        elif span:
            vintage = str(span[1])
            vintage_basis = (f"maximum year in `{yc}`; the table has no "
                             f"finer-grained period column, so the vintage is "
                             f"a YEAR and no day is invented for it")
        else:
            vintage = "UNDATED"
            vintage_basis = ("no period column found. This table cannot state "
                             "a source vintage and must not be cited as if it "
                             "could — see code/cedar_period_columns.py to "
                             "declare one.")

        # A table cut from more than one published state of its source cannot
        # be named by one string. Ship the composition instead of choosing.
        multi = {k: v for k, v in vintages.items() if k != "(unstamped)"}
        if len(vintages) > 1:
            vintage_basis += (
                f" ⚠ ASSEMBLED FROM {len(vintages)} SOURCE VINTAGES — see "
                f"`source_vintages` below; no single stamp describes this file")

        notes = {
            "identity": {
                "dataset": p.stem, "file": p.name, "group": group,
                "vintage": vintage,
                "vintage_basis": vintage_basis,
                "vintage_is_a_range": len(vintages) > 1,
                "source_vintages": vintages or None,
                "built": TODAY,
                "rows": n, "columns": len(hdr),
                "sha256": sha256(p),
                "fits_in_a_worksheet": n <= XLSX_MAX - 2,
                # The physical file still carries these. The BUNDLER must drop
                # them from the CSV it ships - a notes contract can declare a
                # column withheld but cannot remove it from the file. Stated as
                # a column rather than deleted silently, which is this
                # project's own no-silent-exclusions rule applied to itself.
                "licensed_columns_withheld": withheld,
            },
            "coverage": {
                "year_column": yc, "year_span": list(span) if span else None,
                "n_years": (span[1] - span[0] + 1) if span else 0,
                "entity_column": ec, "n_entities": n_ents,
            },
            "reading": READING,
            "comparability": relevant_breaks(breaks, p.stem, group),
            "research_ready": RESEARCH_READY,
            "codebook": rows_cb,
            "terms": TERMS,
            "citation": {
                "text": f'Cedar Press, "{p.stem}", {TODAY}. '
                        f'https://cedarpress.co',
                "url": "https://cedarpress.co",
                "note": "Where a figure originates with a federal source, "
                        "cite that source too. The per-row source_url columns "
                        "exist for that purpose.",
            },
        }

        out = DIST / group
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{p.stem}.notes.json").write_text(
            json.dumps(notes, indent=2, ensure_ascii=False), encoding="utf-8")
        (out / f"{p.stem}.NOTES.md").write_text(md(notes), encoding="utf-8")

        index.append({"dataset": p.stem, "group": group, "file": p.name,
                      "rows": n, "columns": len(hdr),
                      "year_span": list(span) if span else None,
                      "n_entities": n_ents,
                      "n_codebook_vars": len(rows_cb),
                      "n_comparability_notes": len(notes["comparability"]),
                      "licensed_columns_withheld": withheld,
                      "notes_json": f"{group}/{p.stem}.notes.json"})
        stats["notes written"] += 1
        if not rows_cb:
            stats["WARNING: no public codebook variables"] += 1
        # A variable with a name and no definition is a column the subscriber
        # has to guess at. Registering a block makes a table SHIPPABLE; it does
        # not make it DOCUMENTED, and the two must not be confused.
        blank = [c["variable"] for c in rows_cb
                 if not (c.get("description") or "").strip()]
        if blank:
            stats["WARNING: shipped variables with no definition"] += 1
            print(f"  [undefined] {p.name}: {len(blank)} of {len(rows_cb)} "
                  f"published variables have no description "
                  f"(e.g. {', '.join(blank[:4])})")
        if n > XLSX_MAX:
            stats["too large for any worksheet - CSV only"] += 1

    (DIST / "notes_index.json").write_text(
        json.dumps({"vintage": TODAY, "n_datasets": len(index),
                    "datasets": sorted(index, key=lambda r: -r["rows"])},
                   indent=2, ensure_ascii=False), encoding="utf-8")

    # -----------------------------------------------------------------------
    # THE SHIP-RATE LEDGER. Rows in data/clean vs rows that reached a notes
    # contract, per file, every run.
    #
    # This exists because on 2026-08-26 the gaming collection was measured at a
    # 0.87% ship rate - 912 of 104,412 rows - and that had been true for twenty
    # days without anyone being able to see it. Coverage of the SOURCE was
    # audited constantly; coverage of the SHIPMENT was audited never. A number
    # nobody prints is a number nobody checks.
    # -----------------------------------------------------------------------
    if licensed_hits:
        print(f"\n  LICENCE GATE - {len(licensed_hits)} file(s) REFUSED, "
              f"by name:")
        for name, why in licensed_hits:
            print(f"     {name}\n        {why}")

    if internal_hits:
        print(f"\n  INTERNAL BY DECISION - {len(internal_hits)} table(s) are "
              f"deliberately not shipped and are NOT part of the backlog "
              f"below. Reasons: docs/UNSHIPPED_TABLE_TRIAGE.md")
        for name, why in sorted(internal_hits):
            print(f"     {name:52s} {why[:84]}")

    if undocumented:
        print(f"\n  NOT SHIPPED - {len(undocumented)} clean table(s) have no "
              f"codebook block at >=0.60. Each is a dataset that exists and "
              f"cannot leave the building:")
        for name, g, sc in sorted(undocumented, key=lambda r: -r[2]):
            print(f"     {sc:4.2f}  {name:46s} best group: {g}")

    shipped_rows = sum(r["rows"] for r in index)
    lost_rows = 0
    ledger = []
    for name, g, sc in undocumented:
        # `scan()` RETURNS EIGHT VALUES AND THIS LINE UNPACKED FIVE.
        # Corrected 2026-08-26 by code/391-392. The ValueError was swallowed
        # by the `except` below, so every unshipped file was written to
        # dist/_ship_rate.csv as `rows = -1`, `lost_rows` stayed at 0, and
        # SHIP RATE printed shipped-of-shipped - 100.0%, every run, on the one
        # number this script exists to make visible. Measured before the fix:
        # 140 of 140 NO_CODEBOOK rows in dist/_ship_rate.csv carried -1.
        #
        # THE SHAPE IS THIS FILE'S OWN LESSON TURNED ON ITSELF: a drop ledger
        # that could not say what it dropped. Element 0 is taken BY INDEX so a
        # future change to scan()'s return cannot silently zero it again, and
        # the failure is now printed rather than swallowed.
        try:
            n_lost = scan(CLEAN / name)[0]
        except Exception as e:
            print(f"  [ship-rate] could not count {name}: "
                  f"{type(e).__name__}: {e}")
            n_lost = -1
        lost_rows += max(n_lost, 0)
        ledger.append({"file": name, "rows": n_lost, "fate": "NO_CODEBOOK",
                       "best_group": g, "score": round(sc, 3)})
    for r in index:
        ledger.append({"file": r["file"], "rows": r["rows"],
                       "fate": "NOTES_WRITTEN", "best_group": r["group"],
                       "score": ""})
    for name, why in licensed_hits:
        ledger.append({"file": name, "rows": "", "fate": "LICENSED_REFUSED",
                       "best_group": "", "score": ""})
    # An internal-by-decision table goes in the ledger with its own fate and
    # is NOT counted against the ship rate. Keeping it out of the denominator
    # is the point: a ratio that can never reach 100% is a ratio nobody reads.
    # It is still listed BY NAME, because a decision that leaves no trace in
    # the output is indistinguishable from an oversight.
    for name, why in internal_hits:
        try:
            n_int = scan(CLEAN / name)[0]
        except Exception as e:
            print(f"  [ship-rate] could not count {name}: "
                  f"{type(e).__name__}: {e}")
            n_int = -1
        ledger.append({"file": name, "rows": n_int,
                       "fate": "INTERNAL_BY_DECISION",
                       "best_group": "", "score": ""})

    total = shipped_rows + lost_rows
    rate = (shipped_rows / total * 100) if total else 0.0
    with open(DIST / "_ship_rate.csv", "w", encoding="utf-8",
              newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["file", "rows", "fate",
                                           "best_group", "score"])
        w.writeheader()
        w.writerows(sorted(ledger, key=lambda r: (r["fate"], r["file"])))

    for k, v in stats.most_common():
        print(f"  {v:4d}  {k}")
    # THREE DECIMALS, NOT ONE. At one decimal a genuine 99.954% and the old
    # arithmetic bug both print `100.0%`, so fixing the bug would have looked
    # like changing nothing. A meter whose resolution hides the last mile is
    # the same failure as a meter that reads zero.
    print(f"\n  SHIP RATE: {shipped_rows:,} of {total:,} rows in data/clean "
          f"reached a notes contract  ({rate:.3f}%)")
    if lost_rows:
        print(f"             {lost_rows:,} rows are in data/clean and in no "
              f"bundle. dist/_ship_rate.csv has the per-file ledger.")
    print(f"\n  dist/notes_index.json lists {len(index)} datasets for the app "
          f"to enumerate")

    nocb = [r for r in index if r["n_codebook_vars"] == 0]
    if nocb:
        print(f"\n  {len(nocb)} datasets have NO public codebook variables and "
              f"must not ship until documented:")
        for r in nocb[:12]:
            print(f"     {r['dataset']}")


if __name__ == "__main__":
    main()
