#!/usr/bin/env python3
"""
Cedar Press - THE ONE DECLARATION OF WHICH COLUMN CARRIES A TABLE'S PERIOD.

WHY THIS MODULE EXISTS
----------------------
Three tools ask "what period is this row in?" and each of them used to answer it
its own way:

  code/35_coverage_audit.py        a GLOBAL candidate list, `DATE_COLS`,
                                   first name present in the file wins
  code/301_source_freshness_probe.py  a PER-COLLECTION `period_cols` in its
                                   own REGISTRY
  code/102_build_coverage_profile.py  no period concept at all; it declares
                                   (file, column) key pairs instead

Three lists drift, and drift silently, because **a period column that is absent
under the name a tool looks for is indistinguishable from a table with no
dates in it.** That is not a hypothetical. It is the third instance of the same
defect recorded in this repo in one day:

  * `102` printed **0.0% coverage for 19 days** on `nigc_declination_letters`
    (307 rows) and `gaming_financing_events` (274 rows) because it looked for
    `tribe_id` and both tables key `tribe_entity_id`.
  * `35` reported gaming as "no usable date column" when both gaming files were
    fully dated - the defect was in `DATE_COLS`, not the data.
  * And these five, measured 2026-08-26, every one of them **100% dated** and
    every one of them invisible to a generic date scan:

      gaming_revenue_bounds.csv    fiscal_year  13,803/13,803  1994-2025
      ca_gaming_payments.csv       period_end   40,164/40,164  2001-2026
      resource_revenue.csv         period_end    9,993/10,482  1994-2026
      consultation_events.csv      notice_date  11,402/11,402  1994-2026
      ferc_docket_filings.csv      filed_date  102,615/102,615 1990-2026

    `35`'s `DATE_COLS` contains `filing_date` but not `filed_date`; it contains
    `publication_date` but not `notice_date`; and it contains neither
    `period_end` nor `payment_date`. Four of the five were missed on a NAME,
    while holding a complete date series.

So the fix is not another candidate list. It is ONE declaration, here, that all
three tools read.

THE TWO RULES THIS MODULE ENFORCES
----------------------------------
**1. A DECLARED COLUMN THAT IS ABSENT IS A FATAL ERROR, NEVER A ZERO.**
`102` already does this - it raises rather than printing 0.0% - and that
behaviour is preserved and generalised. `resolve()` raises `PeriodColumnMissing`
when a table declares a column it does not have. A tool may catch it and report,
but it must never silently treat it as "no dates".

**2. A YEAR IS A YEAR. NEVER FABRICATE A DAY.**
`gaming_revenue_bounds` keys its period as `fiscal_year` and that is all the
source gives. `kind="year"` says so. Synthesising `2019-07-01` or `2019-12-31`
to make it look like a date column is the defect that already put **415 gaming
dates on day-15 and day-31** in this project, and the deal-ledger convention is
explicit: *"Never invent a day silently."* Consumers that need a date must
handle `kind="year"` by bucketing to the year, not by inventing a month.

THE COALESCE CASE, AND WHY IT IS DECLARED RATHER THAN GUESSED
--------------------------------------------------------------
`resource_revenue` splits its period across two columns, and the split is
DISJOINT and LABELLED BY THE SOURCE - measured: `period_end` on 9,993 rows,
`payment_date` on 489, **both on 0, neither on 0**, and `period_type` reads
`payment_date_only` on exactly those 489. So the declaration is an ordered
coalesce, and `period_type` is the column that says which one applies. That is
a documented source structure, not a fallback invented to paper over blanks.

Consumers
---------
    from cedar_period_columns import PERIOD_COLUMNS, resolve, PeriodColumnMissing

    spec = PERIOD_COLUMNS["ferc_docket_filings.csv"]
    col  = resolve("ferc_docket_filings.csv", header)   # raises if absent
"""

from __future__ import annotations


class PeriodColumnMissing(KeyError):
    """A table declared a period column and the file does not have it.

    This is FATAL by design. An absent declared column means either the
    declaration is stale or the table was rebuilt with a different schema, and
    both are findings. What it must never become is a silent 0% coverage
    reading, which is what this whole module exists to prevent.
    """


# ---------------------------------------------------------------------------
# file name under data/clean/  ->  the declaration
#
#   cols        ordered; the first one PRESENT IN THE HEADER wins. More than
#               one entry means a documented coalesce, never a guess.
#   kind        "date"  -> a full date, bucket to month or year
#               "year"  -> a bare year. DO NOT SYNTHESISE A MONTH OR DAY.
#   basis       what the column means at source, and how it was verified
#   fill        measured fill of the winning column, recorded so a later
#               reader can tell a regression from a known partial
#   selector    optional: a column whose value says WHICH of `cols` applies
# ---------------------------------------------------------------------------
PERIOD_COLUMNS: dict[str, dict] = {

    # ---- the five that a generic date scan could not see -------------------

    "gaming_revenue_bounds.csv": dict(
        cols=["fiscal_year"],
        kind="year",
        basis="The source states a FISCAL YEAR and nothing finer. NIGC regional "
              "totals and tribal audited statements are annual. There is no "
              "day to be had and none is invented.",
        fill="13,803 / 13,803 (100%), span 1994-2025, measured 2026-08-26",
    ),

    "ca_gaming_payments.csv": dict(
        cols=["period_end"],
        kind="date",
        basis="CGCC publishes RSTF/SDF allocations by quarter; `period_end` is "
              "the close of the allocation period as printed. `period_start` "
              "is the matching open and is equally populated - `period_end` is "
              "declared because a period is conventionally dated at its close "
              "and because 301 already keys on it.",
        fill="40,164 / 40,164 (100%), span 2001-2026, measured 2026-08-26",
    ),

    "resource_revenue.csv": dict(
        cols=["period_end", "payment_date"],
        kind="date",
        selector="period_type",
        basis="A DOCUMENTED, DISJOINT COALESCE. Measured 2026-08-26: "
              "`period_end` on 9,993 rows, `payment_date` on 489, both on 0, "
              "neither on 0. `period_type` names which applies and reads "
              "`payment_date_only` on exactly those 489 rows. ONRR disburses "
              "monthly (period_type='month', 9,238 rows); the remainder are "
              "fiscal-year, quarter, or payment-dated only.",
        fill="10,482 / 10,482 (100%) across the coalesce, span 1993-2026",
    ),

    "consultation_events.csv": dict(
        cols=["notice_date"],
        kind="date",
        basis="The date the consultation notice was published. "
              "`event_start_date` / `event_end_date` exist but are populated on "
              "only 93 of 11,402 rows (0.8%) and must NOT be used as the "
              "period - they would silently reduce the table to those 93.",
        fill="11,402 / 11,402 (100%), span 1994-2026, measured 2026-08-26",
    ),

    "ferc_docket_filings.csv": dict(
        cols=["filed_date"],
        kind="date",
        basis="The date FERC eLibrary records the filing as filed. NOTE: the "
              "sibling `issued_date` is populated on ZERO of 102,615 rows, so "
              "any lag measured from filed->issued is measuring nothing - see "
              "the note in 301's registry.",
        fill="102,615 / 102,615 (100%), span 1990-2026, measured 2026-08-26",
    ),

    # ---- the sibling table, same shape, declared so it cannot drift apart --
    "section_106_consultation_events.csv": dict(
        cols=["notice_date"],
        kind="date",
        basis="Same build family and same column as consultation_events.csv.",
        fill="1,363 / 1,363 (100%), span 1994-2026, measured 2026-08-26",
    ),
}


def resolve(filename: str, header) -> str | None:
    """Return the period column this table declares, or None if it declares none.

    Raises PeriodColumnMissing when a declaration exists and NONE of its
    columns are in `header`. That is the whole point: an absent declared column
    must be loud, never a zero.
    """
    spec = PERIOD_COLUMNS.get(filename)
    if not spec:
        return None
    have = {c.lower(): c for c in (header or [])}
    for cand in spec["cols"]:
        if cand.lower() in have:
            return have[cand.lower()]
    raise PeriodColumnMissing(
        f"{filename} declares period column(s) {spec['cols']} in "
        f"code/cedar_period_columns.py and the file has none of them. "
        f"Header starts: {list(header or [])[:10]}. "
        f"This is FATAL, not 0% coverage - fix the declaration or the table."
    )


def kind(filename: str) -> str | None:
    spec = PERIOD_COLUMNS.get(filename)
    return spec["kind"] if spec else None


def declared_pairs():
    """(filename, column) for every declaration - what a gate should verify."""
    return [(f, c) for f, s in PERIOD_COLUMNS.items() for c in s["cols"]]
