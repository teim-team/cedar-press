# Cedar Press — sample extracts

*Built 2026-09-02 by `code/770_sample_extracts.py`. 10 real rows per dataset, straight from the clean tables — nothing synthesised.*

These exist so the finished shape can be judged before the datasets are finished. Every automated gate in Cedar checks the data against a rule; none of them checks whether thirty rows make sense to someone reading them.

**What is excluded, and why the counts here are smaller than the dataset:** rows marked `publishable = N`, and any source marked `TERMS_STATED_RESTRICTIVE` (Navajo's NBOA list, Colville, CTUIR and five others). Sampling prefers complete rows and then spreads evenly across the file, so a sample is not the first ten rows of one agency in one year.

**On natural persons, narrowly.** A table is refused if it carries a person's data held APART from a public role — home address, personal email or phone, date of birth, SSN or TIN. It is *not* refused for naming an individual who is the public record: `lobbying_registrants.csv` publishes STEPHEN GRAHAM of Boston MA, and that is correct, because an individual may register as a lobbyist and the registration IS the disclosure the LDA creates. Codex was right that the older blanket wording — *any table carrying a natural person is refused* — described neither what this enforces nor what it should.

| dataset | table | rows shown | of | cols | one row is |
|---|---|---:|---:|---:|---|
| `_entity_layer` | `cedar_identity_register.csv` | 10 | 1,555 | 6 | UNSTATED |
| `contractors` | `prime_contracts.csv` | 10 | 1,217,768 | 18 | TWO populations under one schema, and the seam is real. Archive rows (FY2008-FY2026, source_file `FY*_All_Cont |
| `deals` | `deals_classified.csv` | 10 | 1,073 | 17 | one row per classified deal event - the merged deals ledger |
| `federal-register` | `consultation_events.csv` | 10 | 11,402 | 15 | one row per (consultation event, participant as published). `consultation_event_id` alone is NOT unique - an e |
| `funding` | `federal_funding_transactions.csv` | 10 | 701,955 | 12 | one row per federal assistance award TRANSACTION, across the union of the assistance and archive pulls |
| `gaming` | `gaming_facilities.csv` | 10 | 787 | 21 | one row per gaming facility - the directory core, docs/GAMING_BUILD_LOG_2026-08-05.md |
| `legislation` | `bill_votes.csv` | 10 | 423 | 15 | one row per roll-call vote on a Native-relevant bill |
| `lobbying` | `lobbying_registrants.csv` | 10 | 653 | 15 | one row per Senate LDA registrant_id - docs/LOBBYING_REGISTRANT_BUILD_LOG.md |
| `nagpra` | `nagpra_notices.csv` | 10 | 6,792 | 16 | one row per NAGPRA notice, keyed on the Federal Register document number - docs/NAGPRA_BUILD_LOG.md. A correct |
| `owned` | `native_owned_businesses.csv` | 10 | 2,916 | 16 | UNSTATED |
| `natural-resources` | `resource_revenue.csv` | 10 | 11,305 | 9 | one row per resource revenue event as recorded by its source system |
| `nest` | `nest_enterprises.csv` | 10 | 1,610 | 17 | one row per ENTERPRISE that a Native entity owns or has published a tie to - a sub-hub of its owner, never a s |
| `nonprofits` | `np_orgs.csv` | 10 | 12,764 | 15 | one row per EIN considered for the Native nonprofit universe, ruled in or out |
| `subcontracting` | `subawards.csv` | 10 | 87,177 | 17 | one row per SUBAWARD FILING AS INGESTED FROM ONE SOURCE - not one row per subaward. FFATA/FSRS requires the PR |

## Before totalling any money column

See `docs/MONEY_TOTALLING_RULES.md`. Two that bite hardest:

- **`subawards.subaward_amount`** summed unfiltered gives **$51.45B** against a correct **$29.47B**. The filter removes **$21.98B** — which is **74.6% of the correct total** and **42.7% of the unfiltered one**. *Both percentages are of that same amount; they differ only in denominator, and an overstatement is measured against the truth, so the number to quote is the first.* Filter to `duplicate_status = 'primary'` and `subaward_exceeds_prime_flag != 'yes'`.
- **`contractor_ranking.owner_obligations_usd`** sums to $6,535.96B against a true $176.74B — a **36.98×** inflation, because owner-grain attributes repeat on every operating-company row. `firm_*` is the additive family.
- **A subaward is a slice of a prime award.** Never add `subawards` to `prime_contracts`.

## Two columns that look like keys and are not, alone

- **`prime_contracts.contract_number`** is the awarding PIID and on 290,519 rows (23.9%) it is a modification stub — `0098`, `0006`, `SBA0001` — meaningless without the IDV it references. **`parent_contract_number` ships beside it and the pair is the key.** Re-measured 2026-09-02 after `1076_clear_self_parent_piid.py`: **507,884** rows carry a real parent and a full child PIID, **290,519** a real parent and a modification stub, **419,359** no parent and a complete standalone PIID, and **6** have neither — all six a six-character PIID from the legacy `.dta` with no vehicle, which is a short pre-FPDS-NG identifier rather than a stub, so they are named rather than counted as broken. *This paragraph read 664,470 / 290,525 / 262,773 / **zero** with neither until today. That zero was true only because 156,592 rows (12.86%) carried `parent_contract_number == contract_number` — a self-parent the legacy source uses to mean standalone, and which Cedar was shipping as a vehicle reference. Codex, PR #29 finding 4, saw one of them.*
- **`federal_funding_transactions.canonical_name`** is a legacy display label, not Cedar's name for the entity. Group on **`cedar_uid`**, which is the key ADR-009 mandates. `haaku community academy` sits on rows correctly keyed to Pueblo of Acoma: grouping on the label credits a school, grouping on the uid credits the nation.

  Re-measured 2026-09-02, and **this paragraph previously carried the contradiction it was describing** — 345,108 in one sentence and 345,180 in the next, with a parenthetical calling the gap a rebuild artefact and the last two digits unimportant. It was neither. Codex, PR #29 round 3, found the stale pair still shipping here after the sibling README had been corrected. The method, so the number is reproducible rather than quoted: compare `canonical_name` against the `canonical_name` the identity register holds for that row's `cedar_uid`, **case-insensitive**, exact string.

  | | rows |
  |---|---:|
  | carry a `cedar_uid` | 552,602 |
  | …name disagrees with the register | **340,738** |
  | …`canonical_name` blank, uid present | 3,622 |
  | …`cedar_uid` absent from the register | **0** |
  | total not matching the register's label | **344,360** |

  **340,653 of the 340,738 — 100.0%, $94,256,591,555.42 —** carry a label appearing verbatim in the legacy do-file key `lineageA_dta_corrtd_tribe_key.csv` (393 distinct name strings): right identity, stale label, one known cause. The 85-row residue needs no repoint. 72 rows / $29,694,344.00 on `CE-001GC-WN` are labelled `Forest County` while the register calls that entity *Sonoma County Indian Health Project, Inc.*, and **all 72 are `recipient_state_code = CA`** — the key is right and only the label is wrong, and that label is worse than stale because Forest County Potawatomi is a real Wisconsin nation. The other 13 are a `Warms Springs` / `Warm Springs` typo, all Oregon.

  The comparison mode has to be stated or the figure is not reproducible: **case-sensitive** the same measurement returns 364,754, which is 24,016 higher and is the likeliest origin of the two numbers that used to sit here.

## Columns that are in the schema and empty in this sample

The column set of every sample is fixed by the curated `SHOW` list in `code/770_sample_extracts.py` and does not change with which rows are drawn. Where a requested column came back blank on all ten rows it is still shipped, and named here, because that is a coverage fact about the dataset rather than something to hide by dropping the column.

- `federal-register` — blank on all 10 sampled rows: `format`
- `owned` — blank on all 10 sampled rows: `naics`, `federal_uei_candidate`

## Mojibake: repaired where it can be, de-preferred where it cannot

Codex, PR #29 round 4, found `2Â€? CONDUIT` in the subcontracting sample. It is real in the bytes — unlike a round-2 report of the same shape, which was a cp1252 console rendering a correct UTF-8 en dash and was measured before being reported.

In `subawards.csv` (87,177 rows) **1,433 cells** carry it: `description` 1,423 rows (1.63%), `subaward_number` 6, `sub_parent_name` 2, `sub_name` 2.

**The obvious remedy only reaches 9.6% of it.** The repeated UTF-8-read-as-cp1252 chain is reversible and is reversed here — `Ã‚Â½` becomes `½`, `Ã‚Â°C` becomes `°C`. But **116 of 1,214 affected cells recover and 1,098 (90.4%) do not**, because they are not a pure re-encoding chain: characters have been substituted. Codex's own example is the clearest case — `2Â€?` holds a literal `?` where a character was destroyed upstream, and you cannot re-decode information that is gone.

So a cell that is still corrupt after repair scores as **empty** for sampling, and the sampler prefers a clean row. 98.4% of subaward rows are unaffected and a ten-row showcase should not spend one of them on corruption. **No row is dropped from the dataset and no money column is touched** — only the sample's choice is steered, and the counts are here so the guard surfaces the defect rather than hiding it.

- `contractors` — `awardee_name` 1 repaired / 0 unrecoverable, `parent_name` 1 repaired / 0 unrecoverable
- `nagpra` — `institution_name` 0 repaired / 2 unrecoverable
- `subcontracting` — `description` 114 repaired / 1089 unrecoverable, `sub_name` 0 repaired / 1 unrecoverable, `subaward_number` 0 repaired / 6 unrecoverable

## Null sentinels, stripped here and named rather than hidden

Codex, PR #29 round 3, found `funding_agency = "Nan"` in the contractors sample — a stringified float any consumer would group and filter on as a real agency. **No sample ships one now.** A cell whose ENTIRE content is a null token (`nan`, `none`, `null`, `<na>`, `nat`, case-insensitive) is blanked before the rows are drawn, so a row is also never judged complete for holding one. Whole cell only: `NANA Regional Corporation` and `Nanakuli` are real values here and a substring rule would eat both. `NA` and `N/A` are deliberately left alone — `NA` is an abbreviation a human may have typed to mean *not applicable*, which is a statement, not a float.

Counted across the **whole source table**, not the ten sampled rows, and only in the columns a sample ships:

- `contractors` — `funding_agency` 33,263  (**33,263** cells)
- `subcontracting` — `subaward_number` 1  (**1** cells)

**The source fix exists and lost a race, which is why this guard is here too.** `772_strip_nan_sentinels.py` had matched the sentinel case-SENSITIVELY, justified in its own docstring by `Nanticoke`, `Nanakuli` and `NANA` — every one of which is an argument against a substring rule, which it never was. A whole-cell test cannot match a 4- or 8-character value with a 3-character token, so the case-sensitivity guarded nothing and hid 617,097 cells. Corrected, it cleared them; then a concurrent in-place enricher, which had read the table before 772 started, wrote back its own copy with five new `identifier_ruling_*` columns and every sentinel restored. 772's guard compares size and mtime across its own read and correctly saw nothing — the other writer's read predated it. **Two in-place enrichers on one table need a declared ordering and these two had none.** The product layer cannot be raced, so the guard sits here as well.
