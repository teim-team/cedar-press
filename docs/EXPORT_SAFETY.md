# Export safety — which tables a buyer may total

*Generated 2026-09-01 by `code/517_export_safety.py`. Derived from the grain contracts and the temporal layer; this file measures nothing new, it REFUSES on what they already know.*

**The rule that matters most:** unknown ownership may ship as unknown. **Contradicted ownership may never ship as a definite historical owner.**

- **SAFE_TO_AGGREGATE**: 217
- **ROW_LEVEL_ONLY**: 4 (of which **3 carry money columns** — the unsafe analysis is also the most likely one)

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
| `congressional_correspondence_log.csv` | legislation | — | grain UNSTATED; no validated primary key |
| `faads_transactions_all_agencies.csv` | funding | obligated_usd | grain UNSTATED; no validated primary key; 3441 literal duplicate rows |
| `native_passthrough.csv` | funding | amount_usd | grain UNSTATED; no validated primary key; 116 literal duplicate rows |
| `subawards.csv` | subcontracting | subaward_amount|prime_award_amount|subaward_amount_real2025 | grain UNSTATED; no validated primary key; 10770 literal duplicate rows |