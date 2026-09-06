# Dataset discovery — 2026-09-06 round: historical archives

Frame: sources with time-depth below the datasets' modern floors (contractors
FY2000, NEST 2016). 2 rows in `dataset_discovery_2026-09-06.jsonl`
(WebSearch-only; figures/URLs literal).

## One continuous statistical backbone

The Census Bureau's business-owner surveys give a ~35-year aggregate series
of Native-owned business counts and receipts by industry and state:

- **Survey of Business Owners (SBO), 1987–2007** — 52,980 firms / $3.7B
  (1987) rising to 236,967 / $34.4B (2007); construction and retail dominant.
- **Annual Business Survey (ABS), 2017–present** — the successor; 47,519
  AIAN-owned employer businesses / $78.5B receipts / 333,153 employees (2022),
  queryable via data.census.gov and the Census API.

This is exactly the "how many, what industries, over time" backbone the owner
described for the research-article framing — the **aggregate complement** to
the entity-level registry, and it fits the aggregate-context-only constraint
(no business-level roster implied).

## The load-bearing caveat

**SBO and ABS measure different universes.** SBO counted employer *and*
nonemployer firms (~237k in 2007); ABS counts employer firms only (~47k).
Comparing them naively shows a fake 80% collapse. The nonemployer AIAN
universe (~378k firms) lives in a separate product — Nonemployer Statistics
by Demographics (NES-D) — logged here as a future lead. Both are Coverage
Frame class: aggregate context, never entity rosters. No registry rows added.
