# Export safety — which tables a buyer may total

*Generated 2026-09-02 by `code/517_export_safety.py`. Derived from the grain contracts and the temporal layer; this file measures nothing new, it REFUSES on what they already know.*

**The rule that matters most:** unknown ownership may ship as unknown. **Contradicted ownership may never ship as a definite historical owner.**

- **SAFE_TO_AGGREGATE**: 221
- **AGGREGATE_ONLY_NO_KEY**: 1 — total it at its declared grain; do **not** expect to address or join a single row. Granted only against a `key_refused` block that `512` re-measures against the file every run.
- **ROW_LEVEL_ONLY**: 0 (of which **0 carry money columns** — the unsafe analysis is also the most likely one)

## Ownership as-of status

14823 (uei, fiscal-year) cells resolved; **3840 are NOT definite** and must not be exported as a historical owner:

- `RESOLVED` — 10,983
- `UNKNOWN_OUTSIDE_EVIDENCE` — 2,913
- `AMBIGUOUS_OVERLAP` — 502
- `NO_FACT_ON_SUBJECT` — 416
- `NO_COVERING_FACT` — 8
- `AMBIGUOUS_GRANULARITY` — 1

## Tables a buyer must NOT aggregate

| table | collection | money columns | why |
|---|---|---|---|