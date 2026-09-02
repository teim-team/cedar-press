# 02f_individual_native_verification — individually Native-owned business verification

*Generated 2026-08-26 by `code/172_write_individual_native_codebook_fragment.py`.*

**335 rows**, one per candidate awardee. Source table: `data/clean/individual_native_ownership_verification.csv`.

## What this dataset is

A register of federal prime contractors that assert Native ownership to the government and are NOT attributed to any tribe, ANC or NHO in the Cedar entity spine — checked, one firm at a time, against what the company itself publishes and against third-party listings.

It exists because a SAM socio-economic flag is a **self-certification**. Filing one falsely to a contracting officer carries False Claims Act exposure, so it is weighty evidence; it is not proof. The counter-example on record: Goldbelt Raven, an ANC subsidiary, certifies `alaskanNativeCorporationOwnedFirm = NO`.

## The four evidence fields are never collapsed

| field | what it is | independent of the firm? |
|---|---|---|
| `sam_self_certification` | the federal filing | **no** |
| `self_description` | the company's own website | **no** |
| `third_party` | SBA / certifying body / press / court | **yes** |
| `tribal_affiliation_named` | does any source name the tribe | depends on the source |

**A federal flag and a company website are one voice in two venues.** When they agree, what has been shown is that the firm is consistent. That is worth recording and it is not corroboration. `evidence_tier = A` therefore requires a leg that is not the firm.

## Three things this dataset will never say

1. **`NOT_NATIVE`.** Absence of a website claim is `NO_CLAIM_FOUND`. Plenty of small contractors never mention ownership on their site.
2. **Ownership inferred from a name.** `name_trap_warning` marks the rows where the name would tempt you; the name carries no weight in any row of this file.
3. **That a 2026 page describes 2003 ownership.** `temporal_caveat` is populated on 100% of rows and must be quoted alongside any sentence.

## Variables

| variable | type | filled | published | description |
|---|---|---:|---|---|
| `verification_id` | text | 100.0% | yes | Cedar-internal row key, `INV-nnnn`, assigned in descending order of total obligations within the candidate set. Stable only within a build; join on `awardee_uei`, never on this. |
| `awardee_uei` | text | 100.0% | yes | SAM Unique Entity ID as carried on the prime contract rows. Blank where the awardee appears only under a name key. |
| `cage_code_modal` | text | 81.8% | yes | Most frequent CAGE code across the awardee's contract rows. CAGE persists across the 2022 DUNS-to-UEI transition and is the more durable identifier of the two. |
| `awardee_name_modal` | text | 100.0% | yes | Most frequent awardee name string across the contract rows. **A NAME IS NOT EVIDENCE OF OWNERSHIP.** See `name_trap_warning`. Sourced from BGOV `master prime file.dta` and the USAspending award archive, NOT from a SAM entity extract - see `dnb_open_data_attaches`. |
| `awardee_name_variants` | text | 100.0% | yes | Up to four distinct name spellings observed, most frequent first. Variation here is normal: DBA strings, punctuation and case differ between filings for one firm. |
| `candidate_basis` | categorical | 100.0% | yes | How the firm entered the register. `TOP400_FLAGGED` — an unattributed awardee in the top 400 by obligations carrying a native self-certification. `PRIOR_OWNER_RULING` — the owner had already ruled it individually Native-owned and the flag route does not reach it. **The second stream is not a footnote: 22 of the 40 prior-ruled firms carry no native self-certification on any contract row**, so the federal flag is a discovery channel with a measured blind spot, not a definition of the population. |
| `recipient_state_modal` | text | 100.0% | yes | Most frequent recipient state on the contract rows. The FILING address, not necessarily the owner's residence. |
| `n_contract_rows` | integer | 100.0% | yes | Prime contract rows in `prime_contracts.csv` for this awardee, all years. Transaction-level for archive years, award-year-vendor aggregate for BGOV years - the two grains are not the same and this count mixes them. |
| `total_obligations_usd` | float | 100.0% | yes | Nominal obligations summed across those rows. Not deflated. |
| `fy_min` | integer | 100.0% | yes | Earliest fiscal year observed. |
| `fy_max` | integer | 100.0% | yes | Latest fiscal year observed. **Measured 2026-08-26: this is 2022 or earlier on 100% of rows**, because every FY2023-2026 row in `prime_contracts.csv` already carries `attributed_flag = 1` - the archive backfill was seeded from known Native identifiers and is not a full-universe pull. See `temporal_caveat`. |
| `obligations_rank_among_unattributed` | integer | 91.6% | yes | Rank by obligations among all `attributed_flag = 0` awardees. The candidate set is the flagged subset of the top 400. |
| `sam_self_certification` | categorical | 100.0% | yes | EVIDENCE FIELD 1 of 4. `YES` on every row by construction: the awardee carries at least one of `reported_8a`, `reported_buy_indian`, `reported_indian_business`, `reported_native_preference` on at least one contract row. **This is the firm asserting its own status to the government.** It carries False Claims Act exposure and is therefore weighty, and it is still self-certification. START_HERE's counter-example: Goldbelt Raven, an ANC subsidiary, certifies `alaskanNativeCorporationOwnedFirm = NO`. |
| `sam_flags_asserted` | text | 93.4% | yes | Which of the four flags were ever set, pipe-separated. |
| `sam_flag_contract_rows` | integer | 100.0% | yes | Contract rows carrying at least one flag. |
| `sam_flag_row_share` | float | 100.0% | yes | `sam_flag_contract_rows / n_contract_rows`. A LOW share is not evidence against the firm: a set-aside is a property of the AWARD and the archive leaves it blank on 56% of transactions (AGENTS.md, 2026-08-08). |
| `sam_setaside_values` | text | 93.4% | yes | Most frequent `setaside` strings with counts. |
| `sam_fine_flags` | text | 1.2% | yes | Where the awardee also appears in `sam_prime_contracts_fy2000_2007.csv`: the SAM entity flags that separate a PERSON from an ENTITY - `flag_american_indian_owned`, `flag_sole_proprietorship`, `flag_tribally_owned_firm`, `flag_alaskan_native_corporation_owned`, `flag_indian_tribe_federally_recognized` - as `flag=hits/rows`. STILL the same voice as `sam_self_certification`, at higher resolution; never a second leg. |
| `sam_fine_flags_source` | text | 1.2% | yes | Names the extract variant the fine flags came from, because only the TRIBAL variant is loaded as of 2026-08-26. |
| `sam_individual_vs_entity` | categorical | 1.2% | yes | Derived from `sam_fine_flags`. One of: `INDIVIDUAL_ASSERTED` (american indian owned set, no entity-ownership flag ever set), `ENTITY_ASSERTED`, `BOTH_ASSERTED_ON_DIFFERENT_ROWS`, or blank where the firm is not in the extract. Blank means NOT MEASURED, never `no`. |
| `self_description` | categorical | 100.0% | yes | EVIDENCE FIELD 2 of 4. What the company's OWN website says. One of: `CLAIM_FOUND`, `NO_CLAIM_FOUND`, `SITE_UNREACHABLE`, `NO_SITE_FOUND`, `NOT_CHECKED`. **`NO_CLAIM_FOUND` IS NOT `NOT_NATIVE`.** Many small contractors simply do not advertise ownership. `SITE_UNREACHABLE` covers 500s and timeouts, which are facts about the moment; only 404 and 403 are facts about the object. |
| `self_description_sentence` | text | 44.8% | yes | The VERBATIM SENTENCE from the company's own site stating ownership. This is the unit of evidence and the thing the project owner asked to see. Never paraphrased, never two fragments stitched together. Suppress on any row where `publishable_sentence = N`. |
| `self_description_url` | text | 70.7% | yes | The exact page the sentence was read from. |
| `self_description_fetch_date` | date | 99.1% | yes | When it was retrieved. Pair this with `fy_max` before drawing any conclusion about the contract years. |
| `self_description_http_status` | text | 69.6% | yes | Observed status. `404`/`403` are facts about the object; anything else is a fact about the moment. |
| `self_description_ownership_kind` | categorical | 41.5% | yes | What KIND of owner the company's own sentence describes. One of: `INDIVIDUAL_NATIVE`, `TRIBAL_ENTITY`, `ALASKA_NATIVE_CORPORATION`, `NATIVE_HAWAIIAN_ORGANIZATION`, `NATIVE_UNSPECIFIED` (says Native-owned without saying which), `NON_NATIVE_OWNER_NAMED`, or blank. |
| `third_party` | categorical | 100.0% | yes | EVIDENCE FIELD 3 of 4. `FOUND` / `NOT_FOUND` / `NOT_CHECKED`. The only leg in this table that is NOT the firm speaking about itself, and therefore the only one that can carry a row to tier A. |
| `third_party_source_type` | categorical | 10.1% | yes | One of: `SBA_8A`, `SBA_DSBS`, `TRIBAL_CERTIFYING_BODY`, `TRADE_PRESS`, `COURT_OR_GAO`, `OTHER`. |
| `third_party_sentence` | text | 10.1% | yes | Verbatim sentence from the third-party source. |
| `third_party_url` | text | 10.1% | yes | Its URL. |
| `third_party_fetch_date` | date | 10.1% | yes | When retrieved. |
| `third_party_independence` | categorical | 10.1% | yes | **Not every third party is a third party.** Typed by host. `INDEPENDENT` — a government, court, regulator, certifying body or independent journalism; the only kind that can carry a row to tier A. `RELATED_PARTY` — a parent, JV partner or corporate-family site: real evidence, and it is the owner speaking, so it is a leg but not an independent one. `SELF_SOURCED_AGGREGATOR` — a SAM mirror (govcb, govcon, opengovus, govtribe, HigherGov, fedbizconnect), a business-data directory (Buzzfile, BisProfiles, ZoomInfo, LinkedIn) or a company press release (PRNewswire, PRLog): **this is the firm's own certification arriving by a longer road and is NOT counted as a leg at all.** Classifying these correctly moved 21 rows out of tier A. |
| `tribal_affiliation_named` | categorical | 100.0% | yes | EVIDENCE FIELD 4 of 4. `YES` only where a source names the SPECIFIC tribe or nation. "A citizen of the Cherokee Nation" is `YES`; "Native American owned" is `NO`. The distinction is the whole point of the field - an unnamed claim cannot be checked against a tribal roll and cannot be joined to the entity spine. |
| `tribal_affiliation_name` | text | 9.3% | yes | The tribe or nation as the source names it. NOT resolved to a `tribe_id`: resolving it would key a dollar off a name, which is the containment defect. |
| `tribal_affiliation_source` | text | 9.3% | yes | The URL that names the tribe. |
| `prior_owner_ruling` | categorical | 11.9% | yes | The project owner's own standing ruling where one exists. `INDIVIDUAL_NATIVE` or `INDIVIDUAL_NATIVE_NOT_TRIBAL`. **Never overwritten by anything in this table.** A later web pass may add evidence to such a row; it may not change the ruling. |
| `prior_owner_ruling_note` | text | 11.9% | yes | The owner's note, verbatim. |
| `prior_owner_ruling_evidence_url` | text | 10.7% | yes | The URL he cited. |
| `prior_owner_ruling_evidence_type` | text | 11.9% | yes | How he evidenced it. `GAO decision`, `CAGE registry lookup` and `OpenCorporates filing` are THIRD-PARTY documents and make the ruling an independent leg. `Company website`, `Archived company website` and `Owner note` are the firm speaking about itself and do not. |
| `prior_owner_ruling_source_file` | text | 11.9% | yes | Which ruling file it came from, so the ruling can be re-read in place. |
| `prior_owner_ruling_date` | date | 11.9% | yes | When he ruled it. |
| `prior_ruling_honored` | categorical | 11.9% | yes | `YES` where a standing ruling was carried through unchanged. |
| `evidence_tier` | categorical | 100.0% | yes | COMPUTED, never chosen. `A` an independent leg plus a second agreeing leg; `B` exactly one non-SAM leg; `C` federal self-certification only; `X` a source names a non-Native owner against the federal flag. The function is `compute_tier()` in `code/171_build_individual_native_verification.py` and `tier_basis` names the legs on every row so it can be recomputed by hand. |
| `tier_basis` | text | 100.0% | yes | The exact legs the tier was computed from, `+`-separated. |
| `evidence_independence` | categorical | 100.0% | yes | **The most important column in the file.** `FEDERAL_SELF_CERT_ONLY`, `SELF_ASSERTION_ONLY` (SAM and/or the firm's website - one voice, two venues), `INDEPENDENT_CORROBORATION` (at least one leg is not the firm), `INDEPENDENT_CONTRADICTION`. A SAM flag and a company website agreeing establishes CONSISTENCY, not corroboration. |
| `ownership_class` | categorical | 100.0% | yes | The class of owner, from the strongest EVIDENCED source. One of: `INDIVIDUAL_NATIVE`, `TRIBAL_ENTITY`, `ALASKA_NATIVE_CORPORATION`, `NATIVE_HAWAIIAN_ORGANIZATION`, `NATIVE_UNSPECIFIED`, `NON_NATIVE_OWNER_NAMED`, `UNDETERMINED`. **`UNDETERMINED` means nobody said, not that the firm is not Native-owned.** |
| `ownership_class_source` | categorical | 56.4% | yes | Which leg supplied the class: `OWNER_RULING`, `SELF_DESCRIPTION`, `THIRD_PARTY`, or blank. |
| `name_trap_warning` | text | 12.2% | yes | Fires where the awardee name contains one of the 39 `NAME_TRAPS` terms, or a tribe name followed by a place suffix. It exists to make visible that the NAME did no work in this row. `Cherokee`, `Creek`, `Indian`, `United` and 35 others have each produced a measured false attribution. |
| `temporal_caveat` | text | 100.0% | yes | Populated on 100% of rows. Names the gap between the last contract year and the fetch year. Three gaming rulings were withdrawn 2026-08-06 for ruling a historical record against a current page; this column is the guard against repeating that here, and must travel with any quotation of `self_description_sentence`. |
| `prime_source_files` | text | 100.0% | yes | Which upstream files the contract rows came from, with counts. |
| `privacy_class` | categorical | 100.0% | yes | `CORPORATE_FORM_PRESENT`, `NO_CORPORATE_FORM`, `POSSIBLE_PERSONAL_NAME`, `UNKNOWN`. A sole proprietorship's legal name is frequently a private person's name. Deliberately over-inclusive: the cost of the two errors is not symmetric. |
| `publishable_entity_name` | categorical | 100.0% | yes | `N` where the name may be a private individual's. **Cedar does not publish a page that names a private individual.** |
| `publishable_sentence` | categorical | 100.0% | yes | `N` where the quoted sentence carries a personal name on a row already flagged `POSSIBLE_PERSONAL_NAME`. |
| `publishable_contract_facts` | categorical | 100.0% | yes | `Y` throughout. PIID, action date, obligation, NAICS, agency and socio-economic flags are contract facts and publish. |
| `dnb_open_data_attaches` | text | 100.0% | yes | Answers the D&B question PER FIELD rather than per dataset. These rows come from BGOV `master prime file.dta` and the USAspending award archive, NOT from a SAM entity extract, so the bulk-dissemination restriction on D&B Open Data recorded in START_HERE does not attach. Any future SAM-sourced row must carry its own answer. |
| `researcher_note` | text | 99.7% | **no** | Working note from the web pass: which pages were tried, what the site actually said, whether an owner is named. **`published = 0`: may contain a private individual's name.** |
| `web_pass_batch` | text | 99.7% | **no** | Which verification batch produced the row. Provenance for re-running one batch without disturbing the others. |
| `web_pass_matched_on` | categorical | 99.7% | yes | Which STABLE key joined the web result to this row: `UEI`, `CAGE`, `NORMALISED_NAME`, or blank where no web row exists. **Never joined on `verification_id`** — that field is positional and drifts when the upstream contract file changes. See `web_pass_verification_id`. |
| `web_pass_verification_id` | text | 99.7% | yes | The `verification_id` this firm carried WHEN THE WEB PASS RAN. It differs from the current `verification_id` on every row below an insertion point, and the divergence is the audit trail for a real incident on 2026-08-26: a concurrent agent rewrote `prime_contracts.csv` mid-build, the candidate set grew by one, and a positional join briefly attached Frontier Electronic Systems' website sentence to Cherokee Construction, Inc. Keep this column: where it disagrees with `verification_id`, it proves the join was done on identity. |
| `built_date` | date | 100.0% | yes | When the CANDIDATE row was built by 170. |
| `built_by` | text | 100.0% | yes | The candidate builder, `code/170_build_individual_native_candidates.py`. |
| `verification_built_date` | date | 100.0% | yes | When the VERIFICATION row was assembled by 171. Differs from `built_date` whenever the web pass is re-run against a standing candidate set. |
| `verification_built_by` | text | 100.0% | yes | The assembler, `code/171_build_individual_native_verification.py`. |

## Registration status

This fragment is **not yet in `data/clean/codebook_master.csv`**. Registering it belongs to `41_build_codebooks.py`, which is a global rebuild and is currently unsafe to run — it would delete 21 of the 43 blocks the master now holds, because several fragments postdate its dataset map. Recorded rather than worked around.
