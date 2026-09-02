# WS5 — contractors, nonprofits, deals: the grain, the guard, and the sources

*Measured 2026-09-01 by `code/731_ws5_grain_contractors_nonprofits_deals.py`. Regenerate rather than edit — every number is taken from the files on disk at run time, and `verify` exits 1 when one of them stops being true.*

## 1. `contractor_ranking.csv` — DECLARED, and the privacy guard was the bigger finding

WS2 established that this table had no key: `269` emits one row per `(tribe_id, firm_key)` and **never writes `firm_key`**, and the personal-name guard then blanked `operating_company_uei` and replaced `operating_company_name` with a constant, so two operating companies of one owner became literally indistinguishable. WS2 proposed the fix and did not make it. It is made now.

| | |
|---|---:|
| rows | 1,429 |
| duplicates on `(owner_entity_id, operating_company_seq)` | **0** |
| rows with a blank key component | 0 |

`operating_company_seq` is 1..n within the owner in the sort order `269` already used — descending `firm_obligations_usd`. It is unique by construction and it leaks nothing a redaction was protecting. It is a **position, not an identity**: it is recomputed every build and it moves when a firm's obligations move, so a buyer who needs something stable joins on `operating_company_uei`.

### The guard was firing on sovereign governments

The rule exists to protect a natural person. Measured on the live file, it fired on **134 of 1,429 rows and exactly one of those 134 was a natural person** — `BARRETT, MICHAEL`, $20,000. The other 133 were tribal governments and their instrumentalities: Nez Perce Tribe, Pueblo of Acoma, Rosebud Sioux Tribe, Ramah Navajo Chapter, Blackfeet Utilities, Wyandotte Net Tel, Yakama Power, Santa Clara Pueblo, Quinault Indian Nation, Havasupai Tribe. One carried $71.9M.

The owner settled the principle in `docs/PUBLICATION_POLICY.md`: a firm's legal name is the firm's name, and the surviving distinction is whether a column describes the **firm** or a **person separate from it**. `269`'s own docstring already said the population has no sole proprietors in it — *"the owner side is the entity spine, and a sole proprietor is not on it"*.

So `privacy_class` is unchanged and still carries 171's verbatim verdict — the audit trail of what the blunt rule said — and the **decision** now requires the absence of positive entity evidence. The evidence is written onto the row in a new `entity_class_basis` column:

| basis | rows freed |
|---|---:|
| `governmental_or_institutional_token` | 104 |
| `corporate_form_missed_by_171_regex` | 14 |
| `single_token_name_cannot_be_a_natural_persons_full_name` | 6 |
| `shares_owner_entity_name_stem` | 5 |

**129 rows freed, $6.08B.** Names still withheld: **5**, carrying $1,267,755.14 — and not one of them is a government. The residual is deliberate: a two- or three-token name with no entity evidence at all, a blank name, a `SURNAME, FIRSTNAME` comma form, and any UEI already ruled not-nameable in `individual_native_ownership_verification.csv`. Absence of entity evidence is still resolved in the person's favour, and a privacy ruling only ever tightens.

### C7 — what may be summed

| statement | measured |
|---|---:|
| `SUM(firm_obligations_usd)` over every row | $176.74B |
| `SUM(owner_obligations_usd)` over every row | $6,535.96B |
| the same, over distinct `owner_entity_id` | $176.74B |
| inflation if row-summed, over 283 owners | **36.98x** |

`firm_*` is the additive family. Every `owner_*` column is an owner-grain attribute repeated on every operating-company row of that owner. And the table totals to within $0.04 of `prime_contracts.csv`'s tier-A attributed obligations, so it is a **lossless partition of the same money** — summing both, or unioning them, double-counts $176.74B.

## 2. `np_schedule_i_grants.csv` — REFUSED, and the refusal is the finding

101 literal duplicate rows over 58,685, in 90 groups covering 191 rows. **They are not duplicates.** 11 `object_id`s carry a collision and 0 of them appear more than once in `np_schedule_i_filers.csv` — so every group sits inside ONE return that was parsed exactly once, and the FILER listed the line twice. First Nations Development Institute lists two $20,000 Economic Development grants to Seneca Nation of Indians on its FY2017 return, and both are real.

**A de-dupe deletes $2,089,185.00 of real grants.** The fix is a LINE ORDINAL, not a DELETE: `132.parse_one` walks `RecipientTable` in document order and records no ordinal, and one column — `schedule_i_line_seq`, 1..n within `object_id` — makes `(object_id, schedule_i_line_seq)` unique and takes the count to zero without removing a row. That is the same shape as `430`'s fix for `prime_contracts` and as `operating_company_seq` above. **`132` is not this workstream's to edit**, so the table stays UNSTATED and the task now has a name.

C7: `cash_grant_usd` totals $16,439,532,633.00 and `np_schedule_i_filers.part2_cash_grant_total_usd` totals $16,439,532,633.00 — the same money at two grains, to the dollar, and all 10,314 returns reconcile individually. Never add it to federal obligations either: a re-granted federal award is in both, and Cedar's shape for that is `native_passthrough.csv`'s directed edge plus its `amount_countable` flag, which Schedule I lacks.

## 3. `deals` — two declarations, and the source-link coverage the owner asked for

### Every row of the originated dataset carries a source

`deals_classified.csv` is the one dataset Cedar **originates** rather than collates, so `PUBLICATION_POLICY.md` asks for a source on every row of it. Measured:

| | rows | share |
|---|---:|---:|
| two independent source URLs | 651 | 69.6% |
| one source URL | 284 | 30.4% |
| **no source URL at all** | 0 | 0.0% |
| **at least one** | **935** | **100.0%** |

61 distinct hosts; 662 rows cite a `.gov` source. The top hosts are:

- `broadbandusa.ntia.gov` — 272
- `hud.gov` — 224
- `portal.akdbsstar.us` — 77
- `tribalbusinessnews.com` — 65
- `eda.gov` — 51
- `energy.gov` — 49
- `sec.gov` — 41
- `web.archive.org` — 28
- `transportation.gov` — 18
- `waseyabek.com` — 14
- `chickasaw.com` — 14
- `prnewswire.com` — 7

### `deals_2026_ytd_additions.csv` — the empty file, answered

GRAIN_OPEN asked whether it was consumed or emptied by a rebuild. **Consumed.** All 790 of the 790 rows across the nine staging slices carry a `Deal_ID` the classified ledger already holds — 100%, not one row left behind:

| staging slice | rows | already in `deals_classified` |
|---|---:|---:|
| `deals_2000_2019_additions.csv` | 40 | 40 |
| `deals_2026_ytd_additions.csv` | 0 | 0 |
| `deals_anc_reports_additions.csv` | 28 | 28 |
| `deals_ancsa_portal_additions.csv` | 34 | 34 |
| `deals_ancsa_portal_v2_additions.csv` | 42 | 42 |
| `deals_federal_awards_additions.csv` | 594 | 594 |
| `deals_historical_additions.csv` | 30 | 30 |
| `deals_sec_2010_2017_additions.csv` | 16 | 16 |
| `deals_tribal_debt_additions.csv` | 6 | 6 |

So it is declared from the writer and its eight siblings, on `Deal_ID` — the route GRAIN-WS3 used for `admin_appeal_positions.csv`. **The double-counting statement is the point of the declaration:** 790 of 935 classified rows are also in a slice, worth $22.67B against a $45.20B headline. All nine tables are individually safe to aggregate and **no two of them are safe together.**

The second path is bigger than it looks: 618 of 935 rows carry a `Value_Type` naming a FEDERAL award — $6.87B that Cedar already ships in the funding and contracting datasets. A deal announcement and the obligation behind it are one dollar.

### `tribal_resolution_financings.csv` — declared from the builder

One row, `instrument_number` blank, so the instrument key the open question asks about is **absent**, not merely unproven. `149`'s sweep holds `doc_links` as a set of `(document_url, link_text, index_page, how_found)` tuples and emits at most one row per tuple inside one nation's host loop, so a row is a RETRIEVED DOCUMENT whose text names a financing authorisation — and `instrument_title` is load-bearing because one document reached under two link texts is two rows by construction. Key `(entity_id, source_url, source_index_url, instrument_title)`: 0 duplicates, 0 blank components.

`financing_status` is AUTHORIZED on the whole table. A council resolution records that a governing body voted to **permit** an officer to enter a transaction; it does not establish that the transaction was negotiated, executed or funded. `principal_amount_text` and `pledged_revenues_text` are free text and are not money columns — they may not be totalled at all.

## 4. What is still blocked, and who owns it

| blocker | table | owner |
|---|---|---|
| C1/C2/C3 — no line ordinal, so 90 real grant lines render identical | `np_schedule_i_grants.csv` | `132_build_schedule_i_layer.py`: emit `schedule_i_line_seq` |
| C4 — 13% of rows carry a Cedar id, scope `mixed` | `nonprofits` | the identity workstream; ADR-010 |
| C8 — `88_build_deals_taxonomy.py` is in `NEVER_RUN` | `deals` | the pipeline owner; see the characterisation below |

### C8, characterised rather than touched

`cedar_pipeline.NEVER_RUN` names two things and only one of them is still live. **The first is fixed.** 88's glob read `deals_*_additions.csv` and never saw the root ledgers, which is the miscount that shipped as '790 deals' for three weeks; the glob was repaired at source. Re-measured today, the input side is now a COMPLETE COVER of the output: 790 of 935 classified rows are in a staging slice and the remaining 145 are in `deals_2026_ytd.csv` / `deals_historical_2020_2025.csv` at the repo root — **0 rows are in neither**, so a rebuild that reads both surfaces loses no row.

**The second is live and it is the whole of the blocker.** 886 of 935 rows carry `native_party_entity_id`, `native_party_attribution_source` and `cedar_uid` — written IN PLACE by 33/53/57/154 after 88 ran, and present in neither the slices nor the root ledgers. A full taxonomy rebuild discards all 886. This is the class-6 shape the whole project keeps meeting — a full-rebuild writer and in-place enrichers on one table with no declared ordering — and the fix is the one `510` already applied to `cedar_harvest_conservation.csv` and the one `01` still needs: 88 takes a `.bak` before writing, records a pre-rebuild census (row count, distinct `Deal_ID`, count of non-blank `native_party_entity_id`), and the four party enrichers are replayed in a recorded order and gated on that census. Until then the correct posture is the one in force: keep it in `NEVER_RUN`.

## 5. `62` gate state at handoff — every red line named with its owner

Standing rule 15: red is recorded, never stepped around. WS5 raised four lint findings of its own and cleared all four before handoff — three `class1` (reading the staging slices IS this workstream's subject; waived on the line with a reason, which 293 counts and names) and one `class2c` (a superseded-row counter that named nothing; it now prints every superseded ledger row with its table, disposition and row count, because a ledger row leaving a SHARED file is exactly the event that destroyed 2,146,673 accounted rows on 2026-09-01).

What is still red belongs to other workstreams:

| red line | owner | already named in `AGENTS.md`? |
|---|---|---|
| `lint_new_defect_instances` — `NEW class6: 518_dataset_readiness.py / cedar_dataset_readiness.csv` | 518's author | yes |
| `lint_new_defect_instances` — `NEW class6: 73_faads_name_attribution.py / faads_entity_attribution.csv` | the funding / FAADS workstream, which has `710_faads_attribution_content_key.py` staged | **no — recorded here because `AGENTS.md` is not WS5's to edit** |
| `rulings_unapplied` ROSE 1,215 → 2,894 | the rulings-propagation workstream. The metric reads `status` on `cedar_ruling_ledger_consolidated.csv`, which `173` rebuilds from `23`'s output — the same three-table defect WS2 documented, and no file WS5 touched is in its surface | **no — recorded here for the same reason** |
| `contract_violations = 7`, `contract_orphan_shippable = 6`, `tables_missing_from_25_TABLES` 179 → 187 | the contracts and curated-override workstreams; new `data/clean` tables from other shards | yes |
| `files_with_columns_lost_vs_backup = 1` — `entity_evidence_profile.csv` | whoever ran `505` | yes |
| `SHIPPING LOST: advocacy_passthrough_2026-08-07.csv` | the owner's own deliberate deregistration; `AGENTS.md` says in as many words that the gate's wording is wrong and nobody should spend further time on it | yes |

WS5 moved these in the right direction: `contract_grain_stated_shippable` 185 → 204, `contract_grain_unstated_shippable` 25 → 19, `export_unsafe_money_tables` 11 → 8, `harvest_source_rows_read` 2,146,807 → 12,743,700, `lint_bug_class_instances` 146 → 145.
