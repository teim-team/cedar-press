# Dataset 9 — Federal Actions Affecting Tribal Nations

*Maintenance doc. Generated 2026-08-28. Tier: **Cedar Press ($500) - Federal Register***

## What this is

Event-level log of formal federal actions involving Native entities, from the Federal Register. Dates and cross-verifies every other dataset.

## Files

| File | Rows | Size |
|---|---:|---:|
| `data/clean/federal_actions.csv` | 156,772 | 244 MB |
| `data/clean/federal_actions_raw.csv` | 156,772 | 235 MB |

## Refresh

**Cadence:** Weekly or monthly — free GET API, no key, fully in-session runnable.

**Build:** `code/10_pull_federal_register.py, code/11_classify_federal_actions.py`

Run `py -3 code/00_run_all.py --list` to see pipeline stages.

## NEVER do these

- NEVER quote 63,248 as tribal rulemakings. Only 14.2% of the corpus names a tribal term in its own title/abstract — conditions[term] is FULL TEXT, so it pulls in EPA rules that mention Indian country once. Filter on title_abstract_term_hit.
- Never start a rulemaking time series at 1994. 2,838 of 1994's 2,926 rows are typed 'Uncategorized Document', producing 39 rulemakings vs 1,287 in 1995. That is a metadata artifact, not a policy shift. Start at 1995.

## Known issues and caveats

- Agency slug is `indian-affairs-bureau`. `bureau-of-indian-affairs` returns HTTP 400.
- conditions[title] returns HTTP 400 — no title-scoped search exists, which is why the corpus is 156k rather than ~20k.
- The API 503s on bursts. 2 workers / 0.6s pause is the sustainable rate.
- The ten named tribal buckets (2,794 rows) are 82–100% precise. Everything else is a recall tier.
- Unadded but self-labelling and genuine: 5,634 NAGPRA notices, 123 HEARTH Act leasing approvals. 27,981 PRA/information-collection notices are 18% of the corpus.

---

**House rules that apply to every dataset:**

- Never falsely attribute. Missing coverage is expandable; a wrong attribution is not.
- Only tier A publishes. Elijah's rulings are the only promotion path.
- Flag, never delete. Retain and mark rather than drop.
- Cedar Press is self-contained — stage inputs into `data/raw/external/` and build from local copies.
- Temporal floor is 2000; pre-2000 rows carry `pre_2000_flag = 1`.

See `STATE_OF_BUILD.md`, `docs/CROSS_DATASET_LEARNING.md`, and `docs/COVERAGE_EXPANSION_OPTIONS.md`.

## Reference

- **Codebook** — `docs/codebooks/` defines every variable, its type and units. Regenerate with `py -3 code/41_build_codebooks.py`; it is measured from the data, so it cannot drift from the files.
- **Oddities** — `docs/DATA_ODDITIES.md` states what a zero, a negative and a blank MEAN in each dataset. They are not rare: 9.7% of contract rows are negative (deobligations, which belong in the total) and 9.9% are zero (actions that moved no money). Zero is an assertion; blank is a silence; neither is an error. Never filter an oddity out silently - flag it, count it, explain it.
- **Refresh cadence** — `docs/REFRESH_CADENCE.md` gives the pull schedule for every dataset, the incremental change key for each source, and the re-run chain that must follow ANY refresh. Refresh on the SOURCE's clock, not ours: pulling a quarterly source weekly earns rate limits, and every unnecessary rebuild is a chance to lose a hand correction (`code/31` once silently reset a dataset from 93 keyed to 0).
- **Coverage** — `docs/COVERAGE_AUDIT.md` reports the observed year range and any gaps against the 2000-2026 target. Regenerate with `py -3 code/35_coverage_audit.py`.

A codebook says WHAT each variable is. It deliberately does not say how a value was derived - the linkage method is the product, so columns whose values would disclose it are marked internal and withheld from published extracts.