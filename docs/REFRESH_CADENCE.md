# Refresh Cadence — measured, not cited

*Rewritten 2026-08-26 by `code/301_source_freshness_probe.py`. The 2026-08-06
version is preserved at `docs/REFRESH_CADENCE.md.bak_2026-08-26_pre301`; it was
written from publication schedules rather than from the files, and **four of its
recommendations are wrong against measurement**. Those four are named in
"WHAT THIS CORRECTS" at the bottom.*

**Every number in this document was produced by one re-runnable script.**
Re-run it and the numbers update:

```
py -3 code/301_source_freshness_probe.py            # zero network requests
py -3 code/301_source_freshness_probe.py --probe-net # + 3 bounded probes
```

Outputs `docs/SOURCE_FRESHNESS.json` (full measurement) and
`docs/SOURCE_FRESHNESS_SNAPSHOT.json` (compact state for the next diff). The
diff is the point: **the oldest period whose row count moved between two runs is
the empirical answer to "how far back does a refresh actually reach?"** — and
that number is what sets the trailing re-pull window. It gets sharper every run.

---

## TWO SCRIPTS, TWO QUESTIONS — read this before reading anything else

*Added 2026-09-01 by workstream `cadence`, which owns PART 0.*

| | `301_source_freshness_probe.py` | `630_refresh_cadence.py` |
|---|---|---|
| grain | **collection** (20 of them) | **SOURCE** (55 of them, across all 13 datasets) |
| answers | *where does our data stop, and how far back does a refresh reach?* | *how often does each source publish, has it published since we pulled, and is the gap acquisition or processing?* |
| output | `docs/SOURCE_FRESHNESS.json` + PARTS 1–5 below | `docs/REFRESH_CADENCE.json` + **PART 0** below |
| run | `py -3 code/301_source_freshness_probe.py` | `py -3 code/630_refresh_cadence.py [--probe-net]` |

**Neither replaces the other and the split is not cosmetic.** 301 measures
Cedar's own edge and the shape of retroactive fill. 630 measures the SOURCE's
edge beside it, which is the only way to tell *"the source hasn't published"*
from *"we haven't pulled"* from *"we pulled and never promoted"* — and those
three demand completely different work. **A dataset does not have a cadence. Its
sources do**, and they differ by two orders of magnitude inside a single
dataset: `natural-resources` alone draws on twelve source systems, ONRR monthly
at one end and a retired MMS series that stopped in 2000 at the other.

> **The owner's instruction this answers:** *"Throughout all the datasets, we
> need to know how often we have to scrape and update these things."*
> **Start at PART 0.** Its first two tables — the state split, and what is owed
> most-overdue-first — are the whole answer in one screen.

---

<!-- CEDAR:CADENCE-MEASURED START -->

# PART 0 — THE CADENCE TABLE, ONE ROW PER SOURCE

*Generated 2026-09-02T01:51:54+00:00 by `code/630_refresh_cadence.py`. Every `cedar_holds_through` below was MEASURED from the file named beside it on this run. Re-run the script and the numbers update; do not hand-edit inside the markers.*

**55 sources across 13 datasets.**

## The split that decides what the work actually is

| state | sources | what it means |
|---|---:|---|
| ✅ CURRENT | 12 | Cedar holds everything the source offers |
| ① the source has not published yet | 7 | nothing to do; the expected date is in the row |
| ② **published and NOT PULLED** | 12 | an **acquisition** task |
| ③ **pulled and NOT PROMOTED** | 1 | already on disk. **NOT an acquisition task.** |
| ⛔ closed by design | 5 | the source ended, or is one-time |
| ❓ source edge NOT ESTABLISHED | 18 | no key, no index, or no schedule exists to probe |

> **Read the ② / ③ split before planning any session.** They look identical in a staleness column and are completely different work. Three times this project has recorded a ③ as a ② and sent the next agent to re-download something already on disk: California RSTF, New Mexico gaming FY2023–2026Q2, and the staged NIGC set. All three were promotion jobs. All three are now resolved, and none of them was ever a fetch.

## What is owed right now, most overdue first

*`gap` is days between Cedar's measured edge and the source's measured edge — 0 where the source edge is not established, in which case rank on `edge age` and read the row.*

| # | dataset | source | Cedar holds | source has | gap | edge age | why |
|---:|---|---|---|---|---:|---:|---|
| 1 | `lobbying` | `fr_consultation` | 2026-05-20 | 2026-09-01 | 104d | 104d | the source offers 2026-09-01 and Cedar holds 2026-05-20. Check data/raw, data/staging and review/ before treating this as an acquisition task. |
| 2 | `gaming` | `mi_mgcb` | 2026-06-30 | 2026-07-31 | 31d | 63d | the source offers 2026-07-31 and Cedar holds 2026-06-30. Check data/raw, data/staging and review/ before treating this as an acquisition task. |
| 3 | `lobbying` | `lda` | 2026-08-04T15:47:06-04:00 | 2026-09-01 | 28d | 28d | the source offers 2026-09-01 and Cedar holds 2026-08-04T15:47:06-04:00. Check data/raw, data/staging and review/ before treating this as an acquisitio |
| 4 | `lobbying` | `section_106` | 2026-08-11 | 2026-09-01 | 21d | 21d | the source offers 2026-09-01 and Cedar holds 2026-08-11. Check data/raw, data/staging and review/ before treating this as an acquisition task. |
| 5 | `lobbying` | `fr_ex_parte` | 2026-08-24 | 2026-09-01 | 8d | 8d | the source offers 2026-09-01 and Cedar holds 2026-08-24. Check data/raw, data/staging and review/ before treating this as an acquisition task. |
| 6 | `nagpra` | `nagpra_notices` | 2026-08-24 | 2026-09-01 | 8d | 8d | the source offers 2026-09-01 and Cedar holds 2026-08-24. Check data/raw, data/staging and review/ before treating this as an acquisition task. |
| 7 | `federal-register` | `federal_register` | 2026-08-26 | 2026-09-01 | 6d | 6d | the source offers 2026-09-01 and Cedar holds 2026-08-26. Check data/raw, data/staging and review/ before treating this as an acquisition task. |
| 8 | `deals` | `sec_edgar` | 2017-05-21 | — | 0d | 3390d | declared in the registry: NOT SWEPT — reachable, never swept past 2017 |
| 9 | `legislation` | `congressional_correspondence` | 2026-01-27 | — | 0d | 217d | declared in the registry: NOT ESTABLISHED |
| 10 | `lobbying` | `regulations_gov` | 2026-07-28 | — | 0d | 35d | declared in the registry: NOT ESTABLISHED as a date — the gap here is ENTITY coverage, not time: 51 of 1,712 query names banked (97% of the sweep un-r |
| 11 | `lobbying` | `foia_logs` | 2026-08-12 | — | 0d | 20d | declared in the registry: NOT ESTABLISHED — the gap is AGENCY coverage: 3 of ~100 agencies publish here and are pulled; EPA, USDA, HHS, DOE, Corps and |
| 12 | `lobbying` | `irs990_schedc` | 2026 | 2026 | 0d | 0d | declared in the registry: sibling: nonprofit_schedule_c_coverage.csv, built 2026-09-01 by code/99 from the IRS index itself |
| 13 | `gaming` | `labor_form5500_osha` | — | 2025 | 0d | —d | declared in the registry: both corpora are held through CY2025 in data/raw; nothing newer is published |

## Where the source edge is NOT ESTABLISHED, and why

*An unprobed source is never reported as current. `knowledge age` is how many days old our last statement about the SOURCE is — it is the cheapest number in this file to fix, because closing it costs one request.*

| dataset | source | Cedar holds | knowledge age | reason |
|---|---|---|---:|---|
| `funding` | `bie_uio` | — | never | NOT ESTABLISHED, and neither agency states a schedule. BIE posts a school directory and IHS a UIO list; both are snapshots that change without notice. This is a change-detection source, not a calendar source. |
| `subcontracting` | `fsrs_subawards` | 2026-08-03 | never | NOT ESTABLISHED — code/121_pull_subawards_api.py holds the host right now; one poller per host |
| `legislation` | `congress_gov_bills` | 2026-04-16 | 0d | NOT ESTABLISHED — **api.congress.gov requires a key and Cedar holds none** (checked 2026-09-01: CONGRESS_API_KEY, CONGRESS_GOV_API_KEY and DATA_GOV_API_KEY are all absent from the environment and .env.local). This is the |
| `legislation` | `rollcall_votes` | 2025-05-06 | never | NOT PROBED. **And the naive reading is a trap:** this table holds only 423 NATIVE-RELEVANT roll calls since 1973 — roughly 8 a year. Its edge at 2025-05-06 is as likely to be the last Native-relevant vote as it is our st |
| `deals` | `deals_press` | 2026-08-20 | never | NOT ESTABLISHABLE — there is no index to probe. A deal is current when someone looked. |
| `native-owned-businesses` | `tribal_vendor_lists` | 2026-09-01 | 0d | NOT ESTABLISHABLE ON A CALENDAR. See the CHANGE DETECTION section below — this source needs a trigger, not a schedule. |
| `_entity_layer` | `nho_doi_register` | 2026-08-05 | 26d | NOT RE-PROBED this run |
| `natural-resources` | `nd_treasurer` | 2026-08-21 | 25d | NOT RE-PROBED this run |
| `lobbying` | `ibia_ibla` | 2026-07-28 | 20d | NOT RE-PROBED this run; the pull is COMPLETE to 114/114 board-years as of 2026-08-12 |
| `lobbying` | `oira_nrc_hearings` | 2026-08-13 | 20d | NOT RE-PROBED this run |
| `federal-register` | `nepa_eplanning` | 2026-08-12 | 20d | NOT RE-PROBED this run |
| `gaming` | `nigc_ordinances` | 2026-06-02 | 20d | NOT RE-PROBED this run |
| `gaming` | `fac_sefa_gaming` | 2021 | 20d | shares the FAC pull; see the nonprofits FAC row |
| `nonprofits` | `irs_bmf` | 202603 | 20d | NOT RE-PROBED this run. **The BMF is the fastest-moving source in the nonprofits dataset (monthly) and the 990 returns are the slowest (18 months) — this is the clearest case in Cedar of one dataset with two clocks.** |
| `nonprofits` | `fac_single_audits` | 2026-08-12 | 20d | NOT RE-PROBED this run (an unkeyed request 403s; the keyed route answered 22 requests on 2026-08-26) |
| `contractors` | `fpds_atom` | — | 6d | an EXPIRY DATE, not a cadence — anything depending on this route must extract before retirement, not schedule around it |
| `lobbying` | `ferc_elibrary` | 2026-08-26 | 6d | NOT RE-PROBED this run; was same-day current on 2026-08-26 |
| `deals` | `tribal_debt` | 2021-01-26 | 6d | NOT RE-PROBED this run |

## Per dataset

| dataset | sources | fastest source | slowest edge | states |
|---|---:|---|---|---|
| `_entity_layer` | 3 | **annual** (`fr_recognition_notice`) | 2026-01-30 | ①1 · ⛔1 · ❓1 |
| `contractors` | 4 | **continuous** (`sam_contract_awards`) | 2007 | ⛔1 · ✅2 · ❓1 |
| `deals` | 4 | **continuous** (`deals_press`) | 2017-05-21 | ②1 · ✅1 · ❓2 |
| `federal-register` | 2 | **daily** (`federal_register`) | 2026-08-12 | ②1 · ❓1 |
| `funding` | 4 | **monthly** (`usaspending_assistance_archive`) | 2007-09-30 | ⛔2 · ✅1 · ❓1 |
| `gaming` | 11 | **continuous** (`fac_sefa_gaming`) | 2021 | ①3 · ②1 · ③1 · ✅4 · ❓2 |
| `legislation` | 3 | **continuous** (`congress_gov_bills`) | 2025-05-06 | ②1 · ❓2 |
| `lobbying` | 10 | **continuous** (`regulations_gov`) | 2026 | ②7 · ❓3 |
| `nagpra` | 1 | **daily** (`nagpra_notices`) | 2026-08-24 | ②1 |
| `native-owned-businesses` | 1 | **none** (`tribal_vendor_lists`) | 2026-09-01 | ❓1 |
| `natural-resources` | 7 | **monthly** (`onrr_nrrd_monthly`) | 2000-12-31 | ①1 · ⛔1 · ✅4 · ❓1 |
| `nonprofits` | 4 | **continuous** (`fac_single_audits`) | 2025-11-30 | ①2 · ❓2 |
| `subcontracting` | 1 | **continuous** (`fsrs_subawards`) | 2026-08-03 | ❓1 |

> **A dataset's cadence is its fastest-moving source that anyone actually depends on, and its staleness is its slowest.** `nonprofits` is the clearest case: the IRS BMF is monthly and the 990 returns lag ~18 months. `natural-resources` draws on twelve source systems whose edges span 2000-12-31 to 2026-09-30. One number per dataset would be wrong for every source in it.

### `_entity_layer`

#### Interior's annual Federally Recognized Indian Tribes notice

| field | value |
|---|---|
| state | ① source not published |
| host | `www.federalregister.gov` |
| publish_cadence | annual, late January (91 FR 4102 was 2026-01-30) |
| publish_lag | published on the day it is signed |
| cadence basis | the notice series' own history, 1979-2026 |
| **cedar_holds_through** | **2026-01-30** — measured from `data/clean/federal_recognition_roster.csv`, column `publication_date`, 17,058 rows in scope |
| **source_has_through** | **2026-01-30** — 91 FR 4102, 2026-01-30, is the newest annual notice; the next is due late January 2027 (established 2026-09-01) |
| cedar_last_pulled | 2026-08-06 — max(fetched_date) in data/clean/federal_recognition_roster.csv |
| **refresh_due** | **no** — Cedar holds through 2026-01-30 and the source offers 2026-01-30 — nothing is owed. declared in the registry: 91 FR 4102, 2026-01-30, is the newest annual notice; the next is due late January 2027 |
| age | Cedar's edge is 214 days old; our knowledge of the SOURCE is 0 days old; measured gap behind the source 0 days |
| refresh_cost | one document |
| refresh_command | **TRIGGER THE SPINE REBUILD FROM THE NOTICE, NOT FROM A TIMER.** The FR daily pull is what sees it. |
| breaks_on_refresh | **everything.** And `01_build_entity_spine.py` / `09_import_rulings.py` are DESTRUCTIVE: a direct invocation drops 868 of 1,555 entities and 32 of 44 columns, and 09 drops 1,345 ledger rows, 18 of them tier A owner adjudications. Neither takes a .bak. `data/spine/cedar_entity_spine.csv` IS NOT IN GIT. |

#### DOI Native Hawaiian Organization notification roster · IHS UIO register · TCU and Native CDFI rosters

| field | value |
|---|---|
| state | ❓ edge not established |
| host | `doi.gov / ihs.gov / aihec.org / cdfifund.gov` |
| publish_cadence | irregular — DOI posts NHO notifications as filed; the TCU and CDFI rosters change a few times a year |
| publish_lag | weeks to months |
| cadence basis | NHO_INTERTRIBAL_REGISTER_LOG.md, TCU_CDFI_BUILD_LOG.md |
| **cedar_holds_through** | **2026-08-05** — measured from `data/clean/nho_register.csv`, column `retrieved_date`, 218 rows in scope |
| **source_has_through** | **—** — NOT RE-PROBED this run (established 2026-08-06) |
| cedar_last_pulled | 2026-08-05 — max(retrieved_date) in data/clean/nho_register.csv |
| **refresh_due** | **no** — source_has_through is NOT ESTABLISHED — this source cannot be called current or stale on the evidence held |
| age | Cedar's edge is 27 days old; our knowledge of the SOURCE is 26 days old; measured gap behind the source 0 days |
| refresh_cost | a handful of pages |
| refresh_command | code/05 / 591 / 592 — never 01 or 09 |
| breaks_on_refresh | the 210 NHOs, 185 BIE schools, 173 ANC village corporations and 64 Native CDFIs in the hub |

#### Owner adjudications (Elijah's rulings)

| field | value |
|---|---|
| state | ⛔ closed |
| host | `—` |
| publish_cadence | event-driven — whenever the owner rules |
| publish_lag | 0 |
| cadence basis | the one class of row that is NOT re-derivable |
| **cedar_holds_through** | **—** — measured from `data/clean/cedar_correction_register.csv` |
| **source_has_through** | **—** — not a source in the fetch sense (established 2026-09-01) |
| cedar_last_pulled | 2026-09-01 — recorded in a build log |
| **refresh_due** | **no** — declared in the registry: not a source in the fetch sense |
| age | Cedar's edge is — days old; our knowledge of the SOURCE is 0 days old; measured gap behind the source 0 days |
| refresh_cost | zero |
| refresh_command | py -3 code/124_apply_rulings_in_place.py after ANY refresh |
| breaks_on_refresh | **an upsert must NEVER overwrite a human ruling. Rulings are the only promotion path above tier A.** |

### `contractors`

#### USAspending award-data archive — prime contracts

| field | value |
|---|---|
| state | ✅ CURRENT |
| host | `files.usaspending.gov` |
| publish_cadence | monthly (same object set as assistance) |
| publish_lag | ~4d to publication; a month keeps filling ~2 further months (2026-05 at 44%, 2026-06 at 54% of plateau) |
| cadence basis | REFRESH_CADENCE 1.2/1.3 |
| **cedar_holds_through** | **2026-07-03** — measured from `data/raw/contracts/usaspending_archive_2026-08-07/filtered/FY2026_ledger_rows.csv`, column `action_date`, 62,168 rows in scope |
| **source_has_through** | **2026-07-03** — the archive cut under stamp 20260806 — the newest action_date the source served at pull time (established 2026-08-26) |
| cedar_last_pulled | 2026-08-07 — recorded in a build log |
| **refresh_due** | **no** — Cedar holds through 2026-07-03; the source offers 2026-07-03. Nothing is owed. |
| age | Cedar's edge is 60 days old; our knowledge of the SOURCE is 6 days old; measured gap behind the source 0 days |
| refresh_cost | 20 objects; hours. **api.usaspending.gov and files.usaspending.gov share one rate-limit budget** |
| refresh_command | probe the stamp PER YEAR on the 11th, then re-filter |
| breaks_on_refresh | 207 (extent_competed, in place), 269 (contractor_ranking), 168 (adjudication hubs) — enrichers run LAST |

#### SAM.gov Contract Awards API — FY2000-2007 prime backfill

| field | value |
|---|---|
| state | ✅ CURRENT |
| host | `api.sam.gov` |
| publish_cadence | continuous (the API), but Cedar's use is a one-time backfill |
| publish_lag | n/a — historical years are settled |
| cadence basis | docs/API_KEYS.md; the only route to FY2000-2007 prime |
| **cedar_holds_through** | **2007** — measured from `data/clean/sam_prime_contracts_fy2000_2007.csv`, column `fiscal_year`, 269,312 rows in scope |
| **source_has_through** | **2007** — Cedar's use of this host is bounded to FY2000-2007; later years come from the archive (established 2026-08-26) |
| cedar_last_pulled | 2026-08-12 — recorded in a build log |
| **refresh_due** | **no** — Cedar holds through 2007; the source offers 2007. Nothing is owed. |
| age | Cedar's edge is 6819 days old; our knowledge of the SOURCE is 6 days old; measured gap behind the source 0 days |
| refresh_cost | **10 requests/day** pending the org role request; extract mode only (1,000,000 records/request) |
| refresh_command | code/141_pull_sam_contract_awards.py — never casually |
| breaks_on_refresh | prime_contracts_archive_backfill.csv and its reconciliation |

#### FPDS-NG ATOM feed

| field | value |
|---|---|
| state | ❓ edge not established |
| host | `fpds.gov` |
| publish_cadence | continuous |
| publish_lag | 3 business days for entry; corrections run months longer |
| cadence basis | sam.gov/contracting: *'will be retired later in FY 2026'* |
| **cedar_holds_through** | **—** — measured from `—` |
| **source_has_through** | **—** — an EXPIRY DATE, not a cadence — anything depending on this route must extract before retirement, not schedule around it (established 2026-08-26) |
| cedar_last_pulled | 2026-08-26 — recorded in a build log |
| **refresh_due** | **no** — declared in the registry: an EXPIRY DATE, not a cadence — anything depending on this route must extract before retirement, not schedule around it |
| age | Cedar's edge is — days old; our knowledge of the SOURCE is 6 days old; measured gap behind the source 0 days |
| refresh_cost | n/a |
| refresh_command | code/562/563 probe it; no production pull |
| breaks_on_refresh | the pre-2000 Native-flag probe only |

#### CICD published prime series 1981-2021 (article __NEXT_DATA__)

| field | value |
|---|---|
| state | ⛔ closed |
| host | `—` |
| publish_cadence | one-time (a 2022-12-21 article) |
| publish_lag | n/a |
| cadence basis | docs/datasets/02_contracting.md COVERAGE |
| **cedar_holds_through** | **—** — measured from `data/staging/cicd_published/cicd_prime_series_1981_2021.csv` |
| **source_has_through** | **2021** — the article's own series arrays end 2021 (established 2026-09-01) |
| cedar_last_pulled | 2026-09-01 — recorded in a build log |
| **refresh_due** | **no** — declared in the registry: the article's own series arrays end 2021 |
| age | Cedar's edge is — days old; our knowledge of the SOURCE is 0 days old; measured gap behind the source 0 days |
| refresh_cost | zero |
| refresh_command | none — a PUBLISHED benchmark, never merged as a Cedar measurement |
| breaks_on_refresh | nothing |

### `deals`

#### Press, trade and tribal announcements (manual + assisted sweep)

| field | value |
|---|---|
| state | ❓ edge not established |
| host | `many` |
| publish_cadence | continuous — deals ARE discovery |
| publish_lag | 0-14 days from announcement to a findable source |
| cadence basis | REFRESH_CADENCE 3.1 — the one collection where delay destroys evidence (link rot) |
| **cedar_holds_through** | **2026-08-20** — measured from `data/clean/deals_classified.csv`, column `Event_Date`, 935 rows in scope |
| **source_has_through** | **—** — NOT ESTABLISHABLE — there is no index to probe. A deal is current when someone looked. (established —) |
| cedar_last_pulled | 2026-08-26 — max(Data_As_Of) in data/clean/deals_classified.csv |
| **refresh_due** | **no** — declared in the registry: NOT ESTABLISHABLE — there is no index to probe. A deal is current when someone looked. |
| age | Cedar's edge is 12 days old; our knowledge of the SOURCE is — days old; measured gap behind the source 0 days |
| refresh_cost | manual + press; a weekly sweep, a quarterly deep pass |
| refresh_command | code/54 / 153 additions merge; backfill REVERSE-CHRONOLOGICALLY |
| breaks_on_refresh | deals_party_attribution.csv and the autoresolver — an upsert must NEVER overwrite a human ruling |

#### SEC EDGAR full-text (tribal issuer and counterparty filings)

| field | value |
|---|---|
| state | ② **NOT PULLED** |
| host | `www.sec.gov` |
| publish_cadence | continuous |
| publish_lag | same-day on acceptance |
| cadence basis | EDGAR publishes on acceptance; Cedar's 2010-2017 pass was one-time |
| **cedar_holds_through** | **2017-05-21** — measured from `data/clean/deals_sec_2010_2017_additions.csv`, column `Event_Date`, 16 rows in scope |
| **source_has_through** | **—** — NOT SWEPT — reachable, never swept past 2017 (established 2026-08-26) |
| cedar_last_pulled | 2026-08-05 — recorded in a build log |
| **refresh_due** | **YES** — declared in the registry: NOT SWEPT — reachable, never swept past 2017 |
| age | Cedar's edge is 3390 days old; our knowledge of the SOURCE is 6 days old; measured gap behind the source 0 days |
| refresh_cost | full-text search is free; hours for a full sweep |
| refresh_command | the SEC leg of the deals additions chain |
| breaks_on_refresh | deals_classified.csv merge order |

#### ANCSA Regional Association portal + ANC annual reports

| field | value |
|---|---|
| state | ✅ CURRENT |
| host | `ancsaregional.com and 12 corporate sites` |
| publish_cadence | annual (corporate fiscal-year reports) |
| publish_lag | 3-9 months after corporate FY end |
| cadence basis | DEALS_ANC_REPORTS_BUILD_LOG.md |
| **cedar_holds_through** | **2026-02-09** — measured from `data/clean/deals_ancsa_portal_v2_additions.csv`, column `Event_Date`, 42 rows in scope |
| **source_has_through** | **2025 (corporate FY)** — ANCSA_7i_7j_annual_reports in resource_revenue.csv reach corporate FY2025-12-31 (established 2026-09-01) |
| cedar_last_pulled | 2026-08-05 — max(retrieved_date) over 80 rows of data/raw/external/ancsa_portal_v2/_SOURCE_MANIFEST_V2.csv |
| **refresh_due** | **no** — Cedar holds through 2026-02-09; the source offers 2025 (corporate FY). Nothing is owed. |
| age | Cedar's edge is 204 days old; our knowledge of the SOURCE is 0 days old; measured gap behind the source 0 days |
| refresh_cost | ~80 documents; ~1 hour |
| refresh_command | code/531 / 532 (shard E) |
| breaks_on_refresh | the ANC subsidiary edge set (5,167 declared ownership edges) |

#### Municipal / tribal debt disclosures (EMMA, official statements)

| field | value |
|---|---|
| state | ❓ edge not established |
| host | `emma.msrb.org` |
| publish_cadence | continuous on issuance; continuing disclosure annual |
| publish_lag | days on issuance, months on continuing disclosure |
| cadence basis | TRIBAL_DEBT_BUILD_LOG.md |
| **cedar_holds_through** | **2021-01-26** — measured from `data/clean/tribal_bond_issuances.csv`, column `issue_date`, 29 rows in scope |
| **source_has_through** | **—** — NOT RE-PROBED this run (established 2026-08-26) |
| cedar_last_pulled | 2026-08-26 — recorded in a build log |
| **refresh_due** | **no** — source_has_through is NOT ESTABLISHED — this source cannot be called current or stale on the evidence held |
| age | Cedar's edge is 2044 days old; our knowledge of the SOURCE is 6 days old; measured gap behind the source 0 days |
| refresh_cost | small |
| refresh_command | the tribal-debt additions leg |
| breaks_on_refresh | seminole_bond_disclosures.csv |

### `federal-register`

#### federalregister.gov API — the 14 Cedar nets

| field | value |
|---|---|
| state | ② **NOT PULLED** |
| host | `www.federalregister.gov` |
| publish_cadence | every federal business day; public inspection the day before |
| publish_lag | 0 — same-day |
| cadence basis | REFRESH_CADENCE 5.1 and probe 2026-09-01 |
| **cedar_holds_through** | **2026-08-26** — measured from `data/clean/federal_actions.csv`, column `publication_date`, 156,772 rows in scope |
| **source_has_through** | **2026-09-01** — probe 2026-09-01: /api/v1/documents.json?order=newest -> publication_date 2026-09-01, HTTP 200 (established 2026-09-01) |
| cedar_last_pulled | 2026-08-26 — max(fetched_date) in data/clean/federal_actions.csv |
| **refresh_due** | **YES** — the source offers 2026-09-01 and Cedar holds 2026-08-26. Check data/raw, data/staging and review/ before treating this as an acquisition task. |
| age | Cedar's edge is 6 days old; our knowledge of the SOURCE is 0 days old; measured gap behind the source 6 days |
| refresh_cost | minutes, ~1 API page/day of gap x 14 nets |
| refresh_command | py -3 code/342_pull_federal_register_incremental.py — **never 10 (re-shards 1994..today) and never 11 (full rebuild; reverts 22's two in-place columns)** |
| breaks_on_refresh | fr_content_classification.csv (78, which also rebuilds five LOBBYING tables), 130, 76, 98, 133, 136 — each a separate owner's build |

#### BLM/DOI NEPA ePlanning project register

| field | value |
|---|---|
| state | ❓ edge not established |
| host | `eplanning.blm.gov` |
| publish_cadence | continuous as projects are registered |
| publish_lag | days |
| cadence basis | NEPA_* build logs; no schedule published by BLM |
| **cedar_holds_through** | **2026-08-12** — measured from `data/clean/nepa_eplanning_projects.csv`, column `fetched_date`, 312 rows in scope |
| **source_has_through** | **—** — NOT RE-PROBED this run (established 2026-08-12) |
| cedar_last_pulled | 2026-08-12 — max(fetched_date) over 719 rows of data/raw/advocacy/nepa_eplanning/_SOURCE_MANIFEST.csv |
| **refresh_due** | **no** — source_has_through is NOT ESTABLISHED — this source cannot be called current or stale on the evidence held |
| age | Cedar's edge is 20 days old; our knowledge of the SOURCE is 20 days old; measured gap behind the source 0 days |
| refresh_cost | 719 documents in the last pass; ~1 hour |
| refresh_command | the NEPA register step (see nepa_source_coverage.csv) |
| breaks_on_refresh | nepa_project_documents.csv, nepa_administrative_record_parties.csv |

### `funding`

#### USAspending award-data archive — assistance (files.usaspending.gov)

| field | value |
|---|---|
| state | ✅ CURRENT |
| host | `files.usaspending.gov` |
| publish_cadence | monthly (whole 93.9 GB archive replaced atomically) |
| publish_lag | stamp dated the 6th, published the 10th ~00:14Z (~4d); a month keeps filling for ~2 further months (2026-05 at 66%, 2026-06 at 60% of plateau) |
| cadence basis | REFRESH_CADENCE 1.2/1.3 — S3 last_modified over 4,597 objects |
| **cedar_holds_through** | **2026-06-30** — measured from `data/clean/federal_funding_transactions.csv`, column `action_date`, 701,955 rows in scope |
| **source_has_through** | **2026-06-30** — the archive's own edge under stamp 20260806; assistance carries no action_date past 2026-06-30 (established 2026-08-26) |
| cedar_last_pulled | 2026-08-26 — max(fetched_date) in data/clean/federal_funding_transactions.csv |
| **refresh_due** | **no** — Cedar holds through 2026-06-30; the source offers 2026-06-30. Nothing is owed. |
| age | Cedar's edge is 63 days old; our knowledge of the SOURCE is 6 days old; measured gap behind the source 0 days |
| refresh_cost | 20 objects x ~1.2-2.0 GB; hours |
| refresh_command | probe the stamp PER YEAR on the 11th, then re-filter; do NOT run 41 or 88 (they rebuild from stale upstream) |
| breaks_on_refresh | `source_vintage` on all 701,955 rows (code/335); the notes vintage (code/87); federal_funding_tribe_year_panel.csv |

#### USAspending bulk download 2023-04-09 (historical stratum A)

| field | value |
|---|---|
| state | ⛔ closed |
| host | `api.usaspending.gov` |
| publish_cadence | one-time |
| publish_lag | n/a |
| cadence basis | docs/REFRESH_CADENCE 4.0a — 476,924 rows, FY2008-2023 |
| **cedar_holds_through** | **—** — measured from `—` |
| **source_has_through** | **—** — superseded by the monthly archive; retained only because deduplication makes the strata disjoint on transaction key (0 shared keys) (established 2026-08-26) |
| cedar_last_pulled | 2023-04-09 — recorded in a build log |
| **refresh_due** | **no** — declared in the registry: superseded by the monthly archive; retained only because deduplication makes the strata disjoint on transaction key (0 shared keys) |
| age | Cedar's edge is — days old; our knowledge of the SOURCE is 6 days old; measured gap behind the source 0 days |
| refresh_cost | zero — never re-pull |
| refresh_command | none |
| breaks_on_refresh | nothing; re-pulling would re-open the vintage-mixing defect 335 closed |

#### FAADS (Federal Assistance Award Data System)

| field | value |
|---|---|
| state | ⛔ closed |
| host | `—` |
| publish_cadence | retired |
| publish_lag | n/a |
| cadence basis | superseded by USAspending; the series ends FY2007 by design |
| **cedar_holds_through** | **2007-09-30** — measured from `data/clean/faads_transactions_all_agencies.csv`, column `action_date`, 2,769,748 rows in scope |
| **source_has_through** | **2007-09-30** — the source ended 2007-09-30 (established 2026-08-05) |
| cedar_last_pulled | 2026-08-05 — max(retrieved_date) over 88 rows of data/raw/external/faads/_SOURCE_MANIFEST_faads.csv |
| **refresh_due** | **no** — declared in the registry: the source ended 2007-09-30 |
| age | Cedar's edge is 6911 days old; our knowledge of the SOURCE is 27 days old; measured gap behind the source 0 days |
| refresh_cost | zero |
| refresh_command | none — stamp it once and never touch it |
| breaks_on_refresh | nothing |

#### BIE / IHS Urban Indian Organization rosters

| field | value |
|---|---|
| state | ❓ edge not established |
| host | `bie.edu / ihs.gov` |
| publish_cadence | irregular (roster snapshots) |
| publish_lag | unknown |
| cadence basis | no publication schedule stated by either agency |
| **cedar_holds_through** | **—** — measured from `data/clean/bie_uio_dollars_by_entity.csv`. column `fiscal_year` is not in this file |
| **source_has_through** | **—** — NOT ESTABLISHED, and neither agency states a schedule. BIE posts a school directory and IHS a UIO list; both are snapshots that change without notice. This is a change-detection source, not a calendar source. (established —) |
| cedar_last_pulled | 2026-08-06 — max(fetched_date) over 16 rows of data/raw/external/bie_uio/_SOURCE_MANIFEST.csv |
| **refresh_due** | **no** — source_has_through is NOT ESTABLISHED — this source cannot be called current or stale on the evidence held |
| age | Cedar's edge is — days old; our knowledge of the SOURCE is — days old; measured gap behind the source 0 days |
| refresh_cost | 16 documents; minutes |
| refresh_command | code/40_build_bie_uio.py (see BIE_UIO_BUILD_LOG.md) |
| breaks_on_refresh | the spine's BIE school population (185 entities) |

### `gaming`

#### NIGC gross gaming revenue report (national + by region)

| field | value |
|---|---|
| state | ① source not published |
| host | `nigc.gov` |
| publish_cadence | annual, for the prior federal fiscal year |
| publish_lag | ~10 months after the FY closes |
| cadence basis | sibling: docs/datasets/gaming_sources.md PART 1 |
| **cedar_holds_through** | **2025** — measured from `data/clean/nigc_regional_ggr.csv`, column `fiscal_year`, 198 rows in scope |
| **source_has_through** | **2025** — sibling gaming_sources.md, measured 2026-09-01: FY2025 is the newest published. FY2026 closes 2026-09-30 and the report follows ~mid-2027. (established 2026-09-01) |
| cedar_last_pulled | 2026-08-06 — max(fetched_date) in data/clean/nigc_regional_ggr.csv |
| **refresh_due** | **no** — Cedar holds through 2025 and the source offers 2025 — nothing is owed. declared in the registry: sibling gaming_sources.md, measured 2026-09-01: FY2025 is the newest published. FY2026 closes 2026-09-30 and the report follows ~mid-2027. |
| age | Cedar's edge is 244 days old; our knowledge of the SOURCE is 0 days old; measured gap behind the source 0 days |
| refresh_cost | one report |
| refresh_command | code/586_promote_nigc_gaming.py after the pull |
| breaks_on_refresh | gaming_revenue_bounds.csv — its vintage is a BARE YEAR (2025), never a fabricated 2025-12-31 |

#### NIGC document surface — declinations, enforcement, Indian-lands and game-classification opinions, management-contract approvals

| field | value |
|---|---|
| state | ✅ CURRENT |
| host | `nigc.gov` |
| publish_cadence | irregular — posted as issued, with NIGC's own posting date (datePublished) distinct from the document date |
| publish_lag | days to months; the two dates differ and both are recorded |
| cadence basis | sibling: gaming_sources.md PART 3 |
| **cedar_holds_through** | **2026-09-01** — measured from `data/clean/nigc_document_surface.csv`, column `index_post_date`, 7,930 rows in scope |
| **source_has_through** | **2026-09-01** — the index was read 2026-09-01 by the NIGC workstream; 430 documents in the manifest, all five staged tables promoted the same day (established 2026-09-01) |
| cedar_last_pulled | 2026-09-01 — max(fetched_date) over 430 rows of data/raw/external/nigc_documents/_SOURCE_MANIFEST.csv |
| **refresh_due** | **no** — Cedar holds through 2026-09-01; the source offers 2026-09-01. Nothing is owed. |
| age | Cedar's edge is 0 days old; our knowledge of the SOURCE is 0 days old; measured gap behind the source 0 days |
| refresh_cost | one index read + the new documents |
| refresh_command | code/344_pull_nigc_document_surface.py then code/586 |
| breaks_on_refresh | the five nigc_* clean tables and their contracts (registered today; grain still UNSTATED on two) |
| **measured backlog** | `kind` = staged_vs_clean · `unpromoted_rows` = 0 |
| backlog reading | 0 unpromoted rows means the staged set has been promoted; the staging file is a cache, not a backlog |

#### Connecticut DCP monthly casino win (data.ct.gov)

| field | value |
|---|---|
| state | ① source not published |
| host | `data.ct.gov` |
| publish_cadence | monthly per casino — **the only true monthly gaming series Cedar holds** |
| publish_lag | the source has published nothing since 2025-12; 747 facility-months 1993-01..2025-12 with ZERO gaps |
| cadence basis | sibling: gaming_sources.md, re-probed live 2026-09-01 |
| **cedar_holds_through** | **2025-12-31** — measured from `data/clean/gaming_facility_metrics.csv`, column `observation_date`, 68,211 rows in scope |
| **source_has_through** | **2025-12-31** — sibling probe 2026-09-01: data.ct.gov/resource/i6ts-ib7c reports min 1993-01-31, max 2025-12-31, count 748. **Cedar holds every casino-month it serves.** (established 2026-09-01) |
| cedar_last_pulled | 2026-08-26 — max(fetched_date) in data/clean/gaming_facility_metrics.csv |
| **refresh_due** | **no** — Cedar holds through 2025-12-31 and the source offers 2025-12-31 — nothing is owed. declared in the registry: sibling probe 2026-09-01: data.ct.gov/resource/i6ts-ib7c reports min 1993-01-31, max 2025-12-31, count 748. **Cedar holds every casino-month it serves.** |
| age | Cedar's edge is 244 days old; our knowledge of the SOURCE is 0 days old; measured gap behind the source 0 days |
| refresh_cost | two bounded requests |
| refresh_command | py -3 code/343_refresh_ct_gaming_monthly.py |
| breaks_on_refresh | nothing — `payout` and `hold` stay withheld on the recorded unit break (91.45 in 1993-01 vs 0.912 in 2025-12) |

#### California CGCC — RSTF distribution and SDF commission staff reports

| field | value |
|---|---|
| state | ✅ CURRENT |
| host | `cgcc.ca.gov` |
| publish_cadence | quarterly (a numbered commission staff report per quarter) |
| publish_lag | ~6 weeks after quarter close |
| cadence basis | the report series' own numbering; 98th report = quarter ended 2026-03-31 |
| **cedar_holds_through** | **2026-06-30** — measured from `data/clean/ca_gaming_payments.csv`, column `period_end`, 41,758 rows in scope |
| **source_has_through** | **2026-06-30** — 181 documents on disk; the newest quarter Cedar has a document for is 2026-06-30 and it parses (established 2026-09-01) |
| cedar_last_pulled | 2026-08-07 — max(fetched_date) over 181 rows of data/raw/external/ca_gaming/_SOURCE_MANIFEST.csv |
| **refresh_due** | **no** — Cedar holds through 2026-06-30; the source offers 2026-06-30. Nothing is owed. |
| age | Cedar's edge is 63 days old; our knowledge of the SOURCE is 0 days old; measured gap behind the source 0 days |
| refresh_cost | small — a handful of PDFs |
| refresh_command | code/103_build_california_gaming.py. **DO NOT RE-FETCH the short quarters — see the backlog note.** |
| breaks_on_refresh | ca_gaming_facilities_official.csv |
| **measured backlog** | `kind` = captured_not_parsed · `documents_on_disk` = 181 · `documents_not_parsed` = 53 |
| backlog reading | every one of these is ON DISK. A zone appears here because its numbers do not reconcile with the report's OWN printed total, and Cedar does not publish a money row the source's arithmetic refuses. **This is state 3, not state 2. Re-downloading them changes nothing.** |

#### New Mexico Gaming Control Board quarterly revenue-sharing releases

| field | value |
|---|---|
| state | ✅ CURRENT |
| host | `gcb.nm.gov` |
| publish_cadence | quarterly |
| publish_lag | ~6-8 weeks after quarter close |
| cadence basis | 14 NMGCB quarterly releases, footed 14/14 by code/216 |
| **cedar_holds_through** | **2026-06-30** — measured from `data/clean/gaming_capacity_official.csv`, column `period_end`, partition `state=NM`, 1,278 rows in scope |
| **source_has_through** | **2026-06-30** — the 14 extracted releases reach 2026Q2; promoted 2026-09-01 through code/92 (NM 1,090 -> 1,278 rows) (established 2026-09-01) |
| cedar_last_pulled | 2026-08-26 — recorded in a build log |
| **refresh_due** | **no** — Cedar holds through 2026-06-30; the source offers 2026-06-30. Nothing is owed. |
| age | Cedar's edge is 63 days old; our knowledge of the SOURCE is 0 days old; measured gap behind the source 0 days |
| refresh_cost | small |
| refresh_command | code/216 then code/92 — and NM was NEVER a fetch problem |
| breaks_on_refresh | gaming_capacity_official.csv row conservation |

#### Arizona Department of Gaming — device/table counts; STATEWIDE aggregate GGR only

| field | value |
|---|---|
| state | ✅ CURRENT |
| host | `gaming.az.gov` |
| publish_cadence | quarterly device reports, annual aggregate |
| publish_lag | ~1 quarter |
| cadence basis | sibling: gaming_sources.md — A.R.S. 5-601.02(H)(1) REQUIRES aggregation; per-tribe revenue does not exist |
| **cedar_holds_through** | **2026-07-01** — measured from `data/clean/gaming_capacity_official.csv`, column `as_of_date`, partition `state=AZ`, 463 rows in scope |
| **source_has_through** | **2026** — sibling gaming_sources.md 2026-09-01: COMPLETE for what AZ publishes. gaming.az.gov 403s an automated client; the route is the Wayback archive (code/217). (established 2026-09-01) |
| cedar_last_pulled | 2026-08-07 — recorded in a build log |
| **refresh_due** | **no** — Cedar holds through 2026-07-01; the source offers 2026. Nothing is owed. |
| age | Cedar's edge is 62 days old; our knowledge of the SOURCE is 0 days old; measured gap behind the source 62 days |
| refresh_cost | Wayback CDX route; ~1 hour |
| refresh_command | code/217_pull_az_adg_report_archive.py |
| breaks_on_refresh | nothing |

#### Michigan Gaming Control Board — tribal payments and iGaming

| field | value |
|---|---|
| state | ② **NOT PULLED** |
| host | `michigan.gov/mgcb` |
| publish_cadence | monthly |
| publish_lag | ~3 weeks after month end |
| cadence basis | sibling: gaming_sources.md |
| **cedar_holds_through** | **2026-06-30** — measured from `data/clean/digital_gaming_revenue.csv`, column `period_end`, 10,661 rows in scope |
| **source_has_through** | **2026-07-31** — sibling gaming_sources.md 2026-09-01: MGCB publishes monthly ~3 weeks after month end, so July is out and August is the only genuinely open month (established 2026-09-01) |
| cedar_last_pulled | 2026-08-07 — max(fetched_date) in data/clean/digital_gaming_revenue.csv |
| **refresh_due** | **YES** — the source offers 2026-07-31 and Cedar holds 2026-06-30. Check data/raw, data/staging and review/ before treating this as an acquisition task. |
| age | Cedar's edge is 63 days old; our knowledge of the SOURCE is 0 days old; measured gap behind the source 31 days |
| refresh_cost | one page per month |
| refresh_command | code/164 (digital gaming leg) |
| breaks_on_refresh | digital_gaming_relationships.csv entity links (168) |

#### WI · NY · WA · FL and the remaining state regulators

| field | value |
|---|---|
| state | ① source not published |
| host | `various` |
| publish_cadence | annual, mostly; FL is compact-schedule (forward-dated) |
| publish_lag | months to a year |
| cadence basis | sibling: gaming_sources.md PART 1 |
| **cedar_holds_through** | **2025-06-30** — measured from `data/clean/state_gaming_observations.csv`, column `period_end`, 494 rows in scope |
| **source_has_through** | **2025-06-30** — sibling gaming_sources.md 2026-09-01: WI complete to 2025, NY publishes numerics in the 2019 edition only. **Per-property WI revenue is prohibited by compact confidentiality; NV is sealed by NRS 463.120. Withheld is not never-collected.** (established 2026-09-01) |
| cedar_last_pulled | 2026-08-07 — max(fetched_date) over 280 rows of data/raw/external/state_gaming/_SOURCE_MANIFEST.csv |
| **refresh_due** | **no** — Cedar holds through 2025-06-30 and the source offers 2025-06-30 — nothing is owed. declared in the registry: sibling gaming_sources.md 2026-09-01: WI complete to 2025, NY publishes numerics in the 2019 edition only. **Per-property WI revenue is prohibited by compact confidentiality; NV is sealed by NRS 463.120. Withheld is not never-collected.** |
| age | Cedar's edge is 428 days old; our knowledge of the SOURCE is 0 days old; measured gap behind the source 0 days |
| refresh_cost | one host per state, one poller each |
| refresh_command | code/107 / 217 per state |
| breaks_on_refresh | **fl_gaming_payments.period_end runs to 2031-06-30 — those are forward-dated compact SCHEDULE rows, not observations. Never read them as freshness.** |

#### NIGC gaming ordinance approvals

| field | value |
|---|---|
| state | ❓ edge not established |
| host | `nigc.gov` |
| publish_cadence | irregular — as approved |
| publish_lag | weeks |
| cadence basis | GAMING_ORDINANCE_BUILD_LOG.md |
| **cedar_holds_through** | **2026-06-02** — measured from `data/clean/gaming_ordinances.csv`, column `document_approval_date`, 1,155 rows in scope |
| **source_has_through** | **—** — NOT RE-PROBED this run (established 2026-08-12) |
| cedar_last_pulled | 2026-08-12 — max(fetched_date) over 1151 rows of data/raw/external/nigc_ordinances/_SOURCE_MANIFEST.csv |
| **refresh_due** | **no** — source_has_through is NOT ESTABLISHED — this source cannot be called current or stale on the evidence held |
| age | Cedar's edge is 91 days old; our knowledge of the SOURCE is 20 days old; measured gap behind the source 0 days |
| refresh_cost | 1,151 documents held; incremental is small |
| refresh_command | the ordinance leg + OCR merge |
| breaks_on_refresh | the OCR merge (GAMING_ORDINANCE_OCR_MERGE_LOG.md) |

#### DOL Form 5500 plan filings + OSHA ITA establishment records (gaming employment)

| field | value |
|---|---|
| state | ③ **pulled, not promoted** |
| host | `efast.dol.gov / osha.gov` |
| publish_cadence | annual — Form 5500 by plan year, OSHA ITA by calendar year |
| publish_lag | Form 5500 ~9-12 months after plan-year end (extensions routine); OSHA ITA published the following spring |
| cadence basis | docs/LABOR_SOURCES_FOR_GAMING_2026-08-26.md — Form 5500 2009-2025, OSHA ITA CY2016-CY2025 (3,189,050 rows held) |
| **cedar_holds_through** | **—** — measured from `data/clean/gaming_employment_observations.csv`. column `period_end` is not in this file |
| **source_has_through** | **2025** — both corpora are held through CY2025 in data/raw; nothing newer is published (established 2026-08-26) |
| cedar_last_pulled | 2026-08-07 — max(fetched_date) over 10 rows of data/raw/external/osha_ita/_SOURCE_MANIFEST.csv |
| **refresh_due** | **YES** — declared in the registry: both corpora are held through CY2025 in data/raw; nothing newer is published |
| age | Cedar's edge is — days old; our knowledge of the SOURCE is 6 days old; measured gap behind the source 0 days |
| refresh_cost | zero to promote; the data is already extracted |
| refresh_command | **NOT A PULL.** code/158_merge_staged_labor_employment.py — and it is BLOCKED ON TWO OWNER RULINGS (§4 of LABOR_SOURCES_FOR_GAMING_2026-08-26.md), not on a fetch |
| breaks_on_refresh | gaming_employment_observations.csv. **A Form 5500 row keys to an EIN, never to a facility** — merging it as a property observation would be a grain error. |
| **measured backlog** | `kind` = staged_never_promoted · `unpromoted_rows` = 2548 |
| backlog reading | **These are STATE 3 and the only true state-3 rows this sweep found.** Both files were extracted on 2026-08-26 and neither has a clean twin. They are blocked on two OWNER RULINGS, not on a fetch — a Form 5500 row keys to an EIN and not to a facility, so merging it as a property observation needs an adjudicated rule first. Nothing about this is an acquisition task. |

#### Federal Audit Clearinghouse SEFA — gaming programs

| field | value |
|---|---|
| state | ❓ edge not established |
| host | `api.fac.gov` |
| publish_cadence | continuous acceptance |
| publish_lag | median 271d from fy_end; p90 569d; 30.9% land after the 9-month deadline |
| cadence basis | REFRESH_CADENCE 1.4 — the source's OWN two dates, n=6,780 |
| **cedar_holds_through** | **2021** — measured from `data/clean/fac_audit_sefa_gaming_programs.csv`, column `audit_year`, 1 rows in scope |
| **source_has_through** | **—** — shares the FAC pull; see the nonprofits FAC row (established 2026-08-12) |
| cedar_last_pulled | 2026-08-12 — recorded in a build log |
| **refresh_due** | **no** — source_has_through is NOT ESTABLISHED — this source cannot be called current or stale on the evidence held |
| age | Cedar's edge is 1705 days old; our knowledge of the SOURCE is 20 days old; measured gap behind the source 0 days |
| refresh_cost | api.data.gov key, 1,000/hr |
| refresh_command | code/147_build_fac_single_audits.py |
| breaks_on_refresh | fac_audit_gaming_disclosures.csv |

### `legislation`

#### Congress.gov API — bills, actions, cosponsors

| field | value |
|---|---|
| state | ❓ edge not established |
| host | `api.congress.gov` |
| publish_cadence | continuous while Congress sits |
| publish_lag | ~1 day for introductions; action histories update continuously |
| cadence basis | no Cedar measurement exists; the API publishes continuously |
| **cedar_holds_through** | **2026-04-16** — measured from `data/clean/native_bills.csv`, column `introduced_date`, 3,069 rows in scope |
| **source_has_through** | **—** — NOT ESTABLISHED — **api.congress.gov requires a key and Cedar holds none** (checked 2026-09-01: CONGRESS_API_KEY, CONGRESS_GOV_API_KEY and DATA_GOV_API_KEY are all absent from the environment and .env.local). This is the one dataset whose source edge cannot be established at all. (established 2026-09-01) |
| cedar_last_pulled | 2026-08-06 — max(build_date) in data/clean/native_bills.csv |
| **refresh_due** | **no** — declared in the registry: NOT ESTABLISHED — **api.congress.gov requires a key and Cedar holds none** (checked 2026-09-01: CONGRESS_API_KEY, CONGRESS_GOV_API_KEY and DATA_GOV_API_KEY are all absent from the environment and .env.local). This is the one dataset whose source edge cannot be established at all. |
| age | Cedar's edge is 138 days old; our knowledge of the SOURCE is 0 days old; measured gap behind the source 0 days |
| refresh_cost | unknown until a key exists |
| refresh_command | code/14_build_bills_votes.py then code/73 --rollcalls --sweep --titles --actions --outcomes |
| breaks_on_refresh | native_bill_outcomes.csv, member_positions.csv (136,119 rows), the two entity bridges |

#### Roll-call votes — senate.gov XML and clerk.house.gov

| field | value |
|---|---|
| state | ❓ edge not established |
| host | `www.senate.gov / clerk.house.gov` |
| publish_cadence | continuous while Congress sits (each roll call within hours) |
| publish_lag | hours |
| cadence basis | the chambers publish per vote; no key required |
| **cedar_holds_through** | **2025-05-06** — measured from `data/clean/bill_votes.csv`, column `date`, 423 rows in scope |
| **source_has_through** | **—** — NOT PROBED. **And the naive reading is a trap:** this table holds only 423 NATIVE-RELEVANT roll calls since 1973 — roughly 8 a year. Its edge at 2025-05-06 is as likely to be the last Native-relevant vote as it is our staleness, and nothing on disk distinguishes the two. (established —) |
| cedar_last_pulled | 2026-08-05 — max(build_date) in data/clean/bill_votes.csv |
| **refresh_due** | **no** — declared in the registry: NOT PROBED. **And the naive reading is a trap:** this table holds only 423 NATIVE-RELEVANT roll calls since 1973 — roughly 8 a year. Its edge at 2025-05-06 is as likely to be the last Native-relevant vote as it is our staleness, and nothing on disk distinguishes the two. |
| age | Cedar's edge is 483 days old; our knowledge of the SOURCE is — days old; measured gap behind the source 0 days |
| refresh_cost | two chamber indices per Congress; minutes |
| refresh_command | code/73_bills_votes_completion.py --rollcalls |
| breaks_on_refresh | bill_votes_entity_bridge.csv, bill_votes_official_verification.csv |

#### Congressional correspondence systems (member letter releases)

| field | value |
|---|---|
| state | ② **NOT PULLED** |
| host | `various house.gov / senate.gov` |
| publish_cadence | irregular, per office |
| publish_lag | unknown |
| cadence basis | none — 257 SYSTEM rows describe where letters would be found |
| **cedar_holds_through** | **2026-01-27** — measured from `data/clean/congressional_correspondence_systems.csv`, column `publication_date`, 257 rows in scope |
| **source_has_through** | **—** — NOT ESTABLISHED (established —) |
| cedar_last_pulled | 2026-08-12 — recorded in a build log |
| **refresh_due** | **YES** — declared in the registry: NOT ESTABLISHED |
| age | Cedar's edge is 217 days old; our knowledge of the SOURCE is — days old; measured gap behind the source 0 days |
| refresh_cost | one parser per office |
| refresh_command | code/136 (correspondence leg) |
| breaks_on_refresh | nothing — congressional_correspondence_log.csv is empty |
| **measured backlog** | `kind` = empty_table · `congressional_correspondence_log_rows` = 0 · `systems_rows` = 257 |
| backlog reading | 257 rows describe WHERE letters would be found and the log itself is empty. That is a source that has never been pulled, not one that has nothing. |

### `lobbying`

#### Lobbying Disclosure Act filings (LD-2 / LD-203)

| field | value |
|---|---|
| state | ② **NOT PULLED** |
| host | `lda.gov` |
| publish_cadence | quarterly LD-2 (due +20d), semiannual LD-203 (30 Jan / 30 Jul); amendments arrive CONTINUOUSLY and indefinitely |
| publish_lag | median 20d = the statutory deadline exactly; only 57.4% filed by day 20, 74.0% by day 34, p99 = 495d, max = 5,885d (n = 27,796) |
| cadence basis | REFRESH_CADENCE 2.1 — measured over Cedar's own 27,796 filings |
| **cedar_holds_through** | **2026-08-04T15:47:06-04:00** — measured from `data/clean/native_entity_lobbying_disclosures.csv`, column `dt_posted`, 27,796 rows in scope |
| **source_has_through** | **2026-09-01** — probe 2026-09-01: lda.gov/api/v1/filings ?ordering=-dt_posted -> newest dt_posted 2026-09-01T20:53:39-04:00 (a 2026-Q2 no-activity report). count 1,976,576 (established 2026-09-01) |
| cedar_last_pulled | 2026-08-04 — recorded in a build log |
| **refresh_due** | **YES** — the source offers 2026-09-01 and Cedar holds 2026-08-04T15:47:06-04:00. Check data/raw, data/staging and review/ before treating this as an acquisition task. |
| age | Cedar's edge is 28 days old; our knowledge of the SOURCE is 0 days old; measured gap behind the source 28 days |
| refresh_cost | 15 req/min anonymous, 120 keyed — cheap |
| refresh_command | key on `dt_posted >= last_pull`, NEVER on filing_year + filing_period, and re-read the trailing 4 quarters |
| breaks_on_refresh | 78_content_analysis.py rebuilds FIVE lobbying tables AND fr_content_classification.csv — run it when no other lobbying build is live |

#### regulations.gov public submissions (API v4)

| field | value |
|---|---|
| state | ② **NOT PULLED** |
| host | `api.regulations.gov` |
| publish_cadence | continuous — comment periods are the events |
| publish_lag | posting is near-immediate; the docket, not the entity, is the clock |
| cadence basis | docs/datasets/lobbying_sources.md §4 |
| **cedar_holds_through** | **2026-07-28** — measured from `data/clean/regulations_gov_comments.csv`, column `posted_date`, 172 rows in scope |
| **source_has_through** | **—** — NOT ESTABLISHED as a date — the gap here is ENTITY coverage, not time: 51 of 1,712 query names banked (97% of the sweep un-run) (established 2026-09-01) |
| cedar_last_pulled | 2026-09-01 — max(retrieved_date) in data/clean/regulations_gov_comments.csv |
| **refresh_due** | **YES** — declared in the registry: NOT ESTABLISHED as a date — the gap here is ENTITY coverage, not time: 51 of 1,712 query names banked (97% of the sweep un-run) |
| age | Cedar's edge is 35 days old; our knowledge of the SOURCE is 0 days old; measured gap behind the source 0 days |
| refresh_cost | 1,712 query names at ~12 s/query = ~8 wall-clock hours; checkpoints per entity |
| refresh_command | code/221 — sweep DOCKET-first, never entity-first |
| breaks_on_refresh | regulations_gov_entity_coverage.csv (one row per entity, measured zeros included) |

#### Tribal consultation notices (Federal Register)

| field | value |
|---|---|
| state | ② **NOT PULLED** |
| host | `www.federalregister.gov` |
| publish_cadence | every federal business day |
| publish_lag | 0-1 day |
| cadence basis | rides the same request stream as dataset 9 |
| **cedar_holds_through** | **2026-05-20** — measured from `data/clean/fr_consultation_notices.csv`, column `publication_date`, 484 rows in scope |
| **source_has_through** | **2026-09-01** — probe 2026-09-01: federalregister.gov newest publication_date = 2026-09-01, HTTP 200. **The FR corpus is same-day. Whether a tribal consultation notice actually published in the 104-day gap is a question only the sweep answers — but lobbying_sources.md, written today by the docs workstream, independently calls this leg '3 months stale; 29 agencies only'.** (established 2026-09-01) |
| cedar_last_pulled | 2026-08-07 — max(fetched_date) in data/clean/consultation_events.csv |
| **refresh_due** | **YES** — the source offers 2026-09-01 and Cedar holds 2026-05-20. Check data/raw, data/staging and review/ before treating this as an acquisition task. |
| age | Cedar's edge is 104 days old; our knowledge of the SOURCE is 0 days old; measured gap behind the source 104 days |
| refresh_cost | free — same requests as the FR pull |
| refresh_command | ride code/342_pull_federal_register_incremental.py |
| breaks_on_refresh | consultation_agency_coverage.csv, fr_consultation_year.csv |

#### Section 106 / NHPA consultation notices (Federal Register)

| field | value |
|---|---|
| state | ② **NOT PULLED** |
| host | `www.federalregister.gov` |
| publish_cadence | every federal business day |
| publish_lag | 0-1 day |
| cadence basis | docs/datasets/lobbying_sources.md row 5 |
| **cedar_holds_through** | **2026-08-11** — measured from `data/clean/section_106_consultation_events.csv`, column `notice_date`, 1,363 rows in scope |
| **source_has_through** | **2026-09-01** — probe 2026-09-01: same FR corpus (established 2026-09-01) |
| cedar_last_pulled | 2026-08-12 — max(fetched_date) in data/clean/section_106_consultation_events.csv |
| **refresh_due** | **YES** — the source offers 2026-09-01 and Cedar holds 2026-08-11. Check data/raw, data/staging and review/ before treating this as an acquisition task. |
| age | Cedar's edge is 21 days old; our knowledge of the SOURCE is 0 days old; measured gap behind the source 21 days |
| refresh_cost | free — same request stream |
| refresh_command | code/130 after the FR pull |
| breaks_on_refresh | section_106_project_parties.csv |

#### IBIA / IBLA administrative appeals (Interior OHA year indices)

| field | value |
|---|---|
| state | ❓ edge not established |
| host | `oha.doi.gov` |
| publish_cadence | event-driven; posted to the year index as issued |
| publish_lag | ~1 month observed |
| cadence basis | docs/datasets/lobbying_sources.md row 7 — 114/114 board-years, all 200 |
| **cedar_holds_through** | **2026-07-28** — measured from `data/clean/admin_appeal_decisions.csv`, column `decision_date`, 15,613 rows in scope |
| **source_has_through** | **—** — NOT RE-PROBED this run; the pull is COMPLETE to 114/114 board-years as of 2026-08-12 (established 2026-08-12) |
| cedar_last_pulled | 2026-08-12 — max(fetched_date) in data/clean/admin_appeal_decisions.csv |
| **refresh_due** | **no** — source_has_through is NOT ESTABLISHED — this source cannot be called current or stale on the evidence held |
| age | Cedar's edge is 35 days old; our knowledge of the SOURCE is 20 days old; measured gap behind the source 0 days |
| refresh_cost | year indices only; minutes |
| refresh_command | code/163 --year 2026 |
| breaks_on_refresh | 168_link_adjudication_hubs.py runs in place and 133 reverts it — this collision has bitten FERC four times |

#### Federal Register ex parte notices, all agencies

| field | value |
|---|---|
| state | ② **NOT PULLED** |
| host | `www.federalregister.gov` |
| publish_cadence | every federal business day |
| publish_lag | 0-1 day |
| cadence basis | docs/datasets/lobbying_sources.md row 10 — COMPLETE to the API floor (1994) |
| **cedar_holds_through** | **2026-08-24** — measured from `data/clean/fr_ex_parte_notices.csv`, column `publication_date`, 7,820 rows in scope |
| **source_has_through** | **2026-09-01** — probe 2026-09-01: same FR corpus (established 2026-09-01) |
| cedar_last_pulled | 2026-08-26 — max(built_date) in data/clean/fr_ex_parte_notices.csv |
| **refresh_due** | **YES** — the source offers 2026-09-01 and Cedar holds 2026-08-24. Check data/raw, data/staging and review/ before treating this as an acquisition task. |
| age | Cedar's edge is 8 days old; our knowledge of the SOURCE is 0 days old; measured gap behind the source 8 days |
| refresh_cost | free — same request stream |
| refresh_command | ride the FR pull, then code/98 |
| breaks_on_refresh | fr_ex_parte_parties.csv, fr_ex_parte_party_entity_links.csv |

#### FERC eLibrary docket filings

| field | value |
|---|---|
| state | ❓ edge not established |
| host | `elibrary.ferc.gov` |
| publish_cadence | continuous |
| publish_lag | indexed ~1 business day after acceptance |
| cadence basis | REFRESH_CADENCE Part 2 — confirmed same-day 2026-08-26 |
| **cedar_holds_through** | **2026-08-26** — measured from `data/clean/ferc_docket_filings.csv`, column `filed_date`, 102,615 rows in scope |
| **source_has_through** | **—** — NOT RE-PROBED this run; was same-day current on 2026-08-26 (established 2026-08-26) |
| cedar_last_pulled | 2026-08-26 — max(fetched_date) in data/clean/ferc_docket_filings.csv |
| **refresh_due** | **no** — source_has_through is NOT ESTABLISHED — this source cannot be called current or stale on the evidence held |
| age | Cedar's edge is 6 days old; our knowledge of the SOURCE is 6 days old; measured gap behind the source 0 days |
| refresh_cost | ~300 docket sheets; hours |
| refresh_command | code/133 build — then RE-RUN 168, which 133 reverts |
| breaks_on_refresh | **168's in-place links. 133 has destroyed them four times in one day. Enricher runs LAST.** |

#### Agency FOIA logs (DOI, Indian Affairs, IHS only)

| field | value |
|---|---|
| state | ② **NOT PULLED** |
| host | `various` |
| publish_cadence | agency-dependent, typically annual or quarterly postings |
| publish_lag | months |
| cadence basis | docs/datasets/lobbying_sources.md row 14 |
| **cedar_holds_through** | **2026-08-12** — measured from `data/clean/foia_request_index.csv`, column `fetched_date`, 9,481 rows in scope |
| **source_has_through** | **—** — NOT ESTABLISHED — the gap is AGENCY coverage: 3 of ~100 agencies publish here and are pulled; EPA, USDA, HHS, DOE, Corps and Commerce all publish and none is pulled (established 2026-09-01) |
| cedar_last_pulled | 2026-08-12 — max(fetched_date) in data/clean/foia_request_index.csv |
| **refresh_due** | **YES** — declared in the registry: NOT ESTABLISHED — the gap is AGENCY coverage: 3 of ~100 agencies publish here and are pulled; EPA, USDA, HHS, DOE, Corps and Commerce all publish and none is pulled |
| age | Cedar's edge is 20 days old; our knowledge of the SOURCE is 0 days old; measured gap behind the source 0 days |
| refresh_cost | one parser per agency |
| refresh_command | code/136 — extend to the six named agencies first |
| breaks_on_refresh | correspondence_foia_source_coverage.csv |

#### IRS 990 Schedule C (lobbying / political activity), e-file XML

| field | value |
|---|---|
| state | ② **NOT PULLED** |
| host | `apps.irs.gov` |
| publish_cadence | annual index per SUBMISSION year, returns released in batches as processed |
| publish_lag | index years 2017-2026 only; 2009-2016 are 404 at the IRS — that floor is the IRS's, not ours |
| cadence basis | docs/datasets/lobbying_sources.md §4b, measured today |
| **cedar_holds_through** | **2026** — measured from `data/clean/nonprofit_schedule_c_lobbying.csv`, column `index_year`, 6,870 rows in scope |
| **source_has_through** | **2026** — sibling: nonprofit_schedule_c_coverage.csv, built 2026-09-01 by code/99 from the IRS index itself (established 2026-09-01) |
| cedar_last_pulled | 2026-08-07 — max(fetched_date) over 81 rows of data/raw/external/irs990_schedc/_zip_manifest.csv |
| **refresh_due** | **YES** — declared in the registry: sibling: nonprofit_schedule_c_coverage.csv, built 2026-09-01 by code/99 from the IRS index itself |
| age | Cedar's edge is 0 days old; our knowledge of the SOURCE is 0 days old; measured gap behind the source 0 days |
| refresh_cost | one host, rate-disciplined; the backlog is the fetch, not the parse |
| refresh_command | code/99_build_earmarks_and_schedc.py --steps irs-xml |
| breaks_on_refresh | nonprofit_schedule_c_coverage.csv must be rebuilt in the same pass or it reports a stale backlog |
| **measured backlog** | `kind` = fetch_backlog · `index_target_returns` = 32218 · `downloaded` = 6870 · `parsed` = 6870 · `not_downloaded` = 25348 · `parse_backlog` = 0 |
| backlog reading | downloaded == parsed on every index year, so the PARSE backlog is zero. What remains is a pure ACQUISITION backlog — state 2 — and the returns exist at the IRS. |

#### OIRA EO-12866 meetings · NRC public meetings · congressional hearings

| field | value |
|---|---|
| state | ❓ edge not established |
| host | `reginfo.gov / nrc.gov / govinfo.gov` |
| publish_cadence | event-driven; posted within days |
| publish_lag | days |
| cadence basis | OIRA_HEARINGS_BUILD_LOG.md |
| **cedar_holds_through** | **2026-08-13** — measured from `data/clean/nrc_public_meetings.csv`, column `meeting_date`, 251 rows in scope |
| **source_has_through** | **—** — NOT RE-PROBED this run (established 2026-08-12) |
| cedar_last_pulled | 2026-08-12 — max(fetched_date) in data/clean/nrc_public_meetings.csv |
| **refresh_due** | **no** — source_has_through is NOT ESTABLISHED — this source cannot be called current or stale on the evidence held |
| age | Cedar's edge is 19 days old; our knowledge of the SOURCE is 20 days old; measured gap behind the source 0 days |
| refresh_cost | small |
| refresh_command | code/98 |
| breaks_on_refresh | agency_attention_vs_advocacy*.csv (written by 78) |

### `nagpra`

#### NAGPRA notices (Federal Register documents)

| field | value |
|---|---|
| state | ② **NOT PULLED** |
| host | `www.federalregister.gov` |
| publish_cadence | every federal business day, event-driven arrival |
| publish_lag | 0 — same-day, but the SOURCE's own gap between notices runs days |
| cadence basis | REFRESH_CADENCE 5.2 |
| **cedar_holds_through** | **2026-08-24** — measured from `data/clean/nagpra_notices.csv`, column `publication_date`, 6,772 rows in scope |
| **source_has_through** | **2026-09-01** — probe 2026-09-01: the FR corpus is same-day. Whether a NAGPRA notice published between 2026-08-24 and 2026-09-01 is a separate question the sweep answers, not the index (established 2026-09-01) |
| cedar_last_pulled | 2026-08-26 — recorded in a build log |
| **refresh_due** | **YES** — the source offers 2026-09-01 and Cedar holds 2026-08-24. Check data/raw, data/staging and review/ before treating this as an acquisition task. |
| age | Cedar's edge is 8 days old; our knowledge of the SOURCE is 0 days old; measured gap behind the source 8 days |
| refresh_cost | free — rides the FR request stream |
| refresh_command | py -3 code/77_build_nagpra_dataset.py fetch && ... build |
| breaks_on_refresh | nagpra_notice_entity_bridge.csv (51,521 bridge rows). **mni_total_stated MUST NEVER BE SUMMED.** The 2024 surge is the 43 CFR 10 regime change, bounded by the 2029-01-10 deadline — never publish it as behaviour. |

### `native-owned-businesses`

#### Tribal TERO / Indian-preference vendor and business directories (~1,555 entity websites)

| field | value |
|---|---|
| state | ❓ edge not established |
| host | `~1,555 hosts` |
| publish_cadence | **NONE. There is no publication schedule and inventing one would be a lie.** A list changes when a tribal office remembers to update it. |
| publish_lag | unknowable |
| cadence basis | sibling: docs/datasets/native-owned-businesses.md — 62 of 1,555 entities (4.0%) have EVER been checked |
| **cedar_holds_through** | **2026-09-01** — measured from `data/clean/native_owned_businesses.csv`, column `source_last_updated`, 2,393 rows in scope |
| **source_has_through** | **—** — NOT ESTABLISHABLE ON A CALENDAR. See the CHANGE DETECTION section below — this source needs a trigger, not a schedule. (established 2026-09-01) |
| cedar_last_pulled | 2026-09-01 — max(harvest_date) in data/clean/native_owned_businesses.csv |
| **refresh_due** | **no** — declared in the registry: NOT ESTABLISHABLE ON A CALENDAR. See the CHANGE DETECTION section below — this source needs a trigger, not a schedule. |
| age | Cedar's edge is 0 days old; our knowledge of the SOURCE is 0 days old; measured gap behind the source 0 days |
| refresh_cost | ~15 tribes per agent-day including the terms read; the remaining 297 federally recognised tribes are ~20 agent-days |
| refresh_command | code/570 / 588 (shards L and M) — **read robots.txt and the terms page FIRST; 6 publishers have stated restrictive terms and are excluded by every route** |
| breaks_on_refresh | **NOTHING HERE PUBLISHES.** Every row carries consent_status = UNRESOLVED and publishable = N. |
| **measured backlog** | `kind` = entity_coverage · `rows` = 2393 · `entity_universe` = 1555 |
| backlog reading | the gap here is ENTITY coverage, not time. An entity absent from the registry is NEVER_CHECKED, which is a different fact from NO_LIST_FOUND and must not be read as one. |

### `natural-resources`

#### ONRR Natural Resources Revenue Data — monthly revenue, Native American land class

| field | value |
|---|---|
| state | ✅ CURRENT |
| host | `revenuedata.doi.gov` |
| publish_cadence | monthly |
| publish_lag | ~6 weeks after month close |
| cadence basis | sibling: docs/datasets/natural_resources_sources.md row 1 |
| **cedar_holds_through** | **2026-07-31** — measured from `data/clean/resource_revenue.csv`, column `period_end`, partition `source_system=ONRR_NRRD_monthly_revenue`, 9,277 rows in scope |
| **source_has_through** | **2026-07-31** — sibling natural_resources_sources.md, verified 2026-09-01: upstream 2003-01..2026-07, Cedar holds 2003-01..2026-07, gap NONE (established 2026-09-01) |
| cedar_last_pulled | 2026-09-01 — max(fetched_date) in data/clean/resource_revenue.csv |
| **refresh_due** | **no** — Cedar holds through 2026-07-31; the source offers 2026-07-31. Nothing is owed. |
| age | Cedar's edge is 32 days old; our knowledge of the SOURCE is 0 days old; measured gap behind the source 0 days |
| refresh_cost | small — one filtered portal export |
| refresh_command | code/83_build_resource_ledger.py (ONRR leg) |
| breaks_on_refresh | **87% of these dollars name no tribe, and that is the LAW (the collector may not publish below a national aggregate), not a backlog.** |

#### ONRR fiscal-year disbursements

| field | value |
|---|---|
| state | ① source not published |
| host | `revenuedata.doi.gov` |
| publish_cadence | annual (federal fiscal year) |
| publish_lag | ~3 months after FY close |
| cadence basis | sibling: natural_resources_sources.md |
| **cedar_holds_through** | **2025-09-30** — measured from `data/clean/resource_revenue.csv`, column `period_end`, partition `source_system=ONRR_NRRD_fiscal_year_disbursements`, 157 rows in scope |
| **source_has_through** | **2025-09-30** — FY2025 is the newest closed federal fiscal year the portal publishes; FY2026 closes 2026-09-30 (established 2026-09-01) |
| cedar_last_pulled | 2026-09-01 — max(fetched_date) in data/clean/resource_revenue.csv |
| **refresh_due** | **no** — Cedar holds through 2025-09-30 and the source offers 2025-09-30 — nothing is owed. declared in the registry: FY2025 is the newest closed federal fiscal year the portal publishes; FY2026 closes 2026-09-30 |
| age | Cedar's edge is 336 days old; our knowledge of the SOURCE is 0 days old; measured gap behind the source 0 days |
| refresh_cost | small |
| refresh_command | code/83 (ONRR FY leg) |
| breaks_on_refresh | the reconciliation check against the monthly series |

#### Osage Minerals Council headright payment history

| field | value |
|---|---|
| state | ✅ CURRENT |
| host | `osagemineralscouncil.com` |
| publish_cadence | quarterly (1906+); annual before 1906 |
| publish_lag | ~1 quarter |
| cadence basis | sibling: natural_resources_sources.md row 10 — 1880..2026-Q2 in ONE spreadsheet |
| **cedar_holds_through** | **2026-06-30** — measured from `data/clean/resource_revenue.csv`, column `period_end`, partition `source_system=OMC_headright_payment_history`, 508 rows in scope |
| **source_has_through** | **2026-06-30** — sibling natural_resources_sources.md 2026-09-01: the spreadsheet reaches 2026-Q2, gap NONE (established 2026-09-01) |
| cedar_last_pulled | 2026-09-01 — max(fetched_date) in data/clean/resource_revenue.csv |
| **refresh_due** | **no** — Cedar holds through 2026-06-30; the source offers 2026-06-30. Nothing is owed. |
| age | Cedar's edge is 63 days old; our knowledge of the SOURCE is 0 days old; measured gap behind the source 0 days |
| refresh_cost | one spreadsheet |
| refresh_command | code/83 (Osage leg) |
| breaks_on_refresh | **the 30 pre-1907 rows carry no commodity — the Osage Mineral Estate did not exist yet. Whether they belong in this table is an OPEN SCOPING QUESTION with the owner.** |

#### North Dakota State Treasurer tribal tax distribution search

| field | value |
|---|---|
| state | ❓ edge not established |
| host | `nd.gov` |
| publish_cadence | monthly distributions, searchable |
| publish_lag | ~1 month |
| cadence basis | ND_SEVERANCE_BUILD_LOG.md / ND_TRIBAL_TAX_LOG.md |
| **cedar_holds_through** | **2026-08-21** — measured from `data/clean/resource_revenue.csv`, column `payment_date`, partition `source_system=ND_State_Treasurer_tax_distribution_search`, 492 rows in scope |
| **source_has_through** | **—** — NOT RE-PROBED this run (established 2026-08-07) |
| cedar_last_pulled | 2026-08-07 — max(fetched_date) over 21 rows of data/raw/external/nd_tribal_tax/_SOURCE_MANIFEST.csv |
| **refresh_due** | **no** — source_has_through is NOT ESTABLISHED — this source cannot be called current or stale on the evidence held |
| age | Cedar's edge is 11 days old; our knowledge of the SOURCE is 25 days old; measured gap behind the source 0 days |
| refresh_cost | one search per month |
| refresh_command | code/83 (ND leg) |
| breaks_on_refresh | **period_type is `payment_date_only` on all 492 rows — there is no period_end and none should be invented.** |

#### OSMRE Abandoned Mine Land grant distributions (fee-based + IIJA)

| field | value |
|---|---|
| state | ✅ CURRENT |
| host | `osmre.gov` |
| publish_cadence | annual (federal fiscal year) |
| publish_lag | at appropriation |
| cadence basis | sibling: natural_resources_sources.md |
| **cedar_holds_through** | **2026-09-30** — measured from `data/clean/resource_revenue.csv`, column `period_end`, partition `source_system=OSMRE_AML_fee_based_grant_distribution`, 76 rows in scope |
| **source_has_through** | **2026-09-30** — FY2026 distributions are published at appropriation, ahead of the FY close — a forward-dated federal_fiscal_year period_end that is CORRECT, not a defect (established 2026-09-01) |
| cedar_last_pulled | 2026-09-01 — max(fetched_date) in data/clean/resource_revenue.csv |
| **refresh_due** | **no** — Cedar holds through 2026-09-30; the source offers 2026-09-30. Nothing is owed. |
| age | Cedar's edge is -29 days old; our knowledge of the SOURCE is 0 days old; measured gap behind the source 0 days |
| refresh_cost | small |
| refresh_command | code/83 (OSMRE leg) |
| breaks_on_refresh | **FY2010-FY2012 are scanned images, retrieved and held rather than guessed — do not re-fetch them.** |

#### MMS/MRM American Indian revenues (the pre-ONRR series)

| field | value |
|---|---|
| state | ⛔ closed |
| host | `mrm.mms.gov (archived)` |
| publish_cadence | retired — superseded by ONRR |
| publish_lag | n/a |
| cadence basis | the agency no longer exists |
| **cedar_holds_through** | **2000-12-31** — measured from `data/clean/resource_revenue.csv`, column `period_end`, partition `source_system=MMS_MRM_american_indian_revenues_calendar`, 315 rows in scope |
| **source_has_through** | **2000-12-31** — the series ends where ONRR's begins (established 2026-09-01) |
| cedar_last_pulled | 2026-08-06 — recorded in a build log |
| **refresh_due** | **no** — declared in the registry: the series ends where ONRR's begins |
| age | Cedar's edge is 9375 days old; our knowledge of the SOURCE is 0 days old; measured gap behind the source 0 days |
| refresh_cost | zero |
| refresh_command | none |
| breaks_on_refresh | nothing |

#### MT DOR county oil-gas distribution · UT COBI fund financials · ANCSA 7(i)/7(j) annual reports · OMC quarterly newsletter

| field | value |
|---|---|
| state | ✅ CURRENT |
| host | `revenue.mt.gov / cobi-ws.utah.gov / 12 ANC sites` |
| publish_cadence | MT quarterly · UT state-FY annual · ANCSA corporate-FY annual · OMC newsletter quarterly (stopped 2022) |
| publish_lag | 1 quarter to 9 months |
| cadence basis | sibling: natural_resources_sources.md |
| **cedar_holds_through** | **2026-03-31** — measured from `data/clean/resource_revenue.csv`, column `period_end`, partition `source_system=MT_DOR_county_oil_gas_distribution`, 49 rows in scope |
| **source_has_through** | **2026-03-31** — MT is the fastest of the four and reaches 2026Q1; UT stops at state-FY2025-06-30, ANCSA at corporate-FY2025-12-31, and the OMC newsletter STOPPED at 2022-03-31 (established 2026-09-01) |
| cedar_last_pulled | 2026-08-06 — max(fetched_date) over 116 rows of data/raw/resources/montana/MANIFEST_montana_2026-08-06.csv |
| **refresh_due** | **no** — Cedar holds through 2026-03-31; the source offers 2026-03-31. Nothing is owed. |
| age | Cedar's edge is 154 days old; our knowledge of the SOURCE is 0 days old; measured gap behind the source 0 days |
| refresh_cost | four hosts, one poller each |
| refresh_command | code/83 (state legs) |
| breaks_on_refresh | **four cadences in one registry row. If any of these ever needs its own refresh date, split it out rather than averaging them.** |

### `nonprofits`

#### IRS 990 e-file returns and the annual submission-year index

| field | value |
|---|---|
| state | ① source not published |
| host | `apps.irs.gov` |
| publish_cadence | annual index; returns released in batches as processed |
| publish_lag | **~18 months structural.** p10 = 584 days from fiscal-year end to our retrieval (n = 58,355) — and that is an UPPER bound containing our own delay |
| cadence basis | REFRESH_CADENCE 1.4 |
| **cedar_holds_through** | **2025-12-31** — measured from `data/clean/np_schedule_i_grants.csv`, column `tax_period_end`, 58,685 rows in scope |
| **source_has_through** | **2025-12-31** — calendar-2025 fiscal-year ends sit at 12% of a December plateau because their extended deadline is 2026-11-15; 2026 is zero rows. Maturity ~mid-2027. (established 2026-08-26) |
| cedar_last_pulled | 2026-08-07 — max(retrieved_date) in data/clean/np_schedule_i_grants.csv |
| **refresh_due** | **no** — Cedar holds through 2025-12-31 and the source offers 2025-12-31 — nothing is owed. declared in the registry: calendar-2025 fiscal-year ends sit at 12% of a December plateau because their extended deadline is 2026-11-15; 2026 is zero rows. Maturity ~mid-2027. |
| age | Cedar's edge is 244 days old; our knowledge of the SOURCE is 6 days old; measured gap behind the source 0 days |
| refresh_cost | 10 annual index files, ~77 MB each |
| refresh_command | the 990 leg — SEMIANNUAL (Feb / Aug). A quarterly cadence on an 18-month lag manufactures churn. |
| breaks_on_refresh | np_schedule_i_filers.csv, np_financials.csv, np_org_scale.csv |

#### IRS Business Master File — exempt-organisation extract

| field | value |
|---|---|
| state | ❓ edge not established |
| host | `irs.gov` |
| publish_cadence | monthly |
| publish_lag | ~1 month |
| cadence basis | IRS publishes the EO BMF monthly; 1,957,340 rows held |
| **cedar_holds_through** | **202603** — measured from `data/clean/np_orgs.csv`, column `bmf_tax_period`, 12,764 rows in scope |
| **source_has_through** | **—** — NOT RE-PROBED this run. **The BMF is the fastest-moving source in the nonprofits dataset (monthly) and the 990 returns are the slowest (18 months) — this is the clearest case in Cedar of one dataset with two clocks.** (established 2026-08-12) |
| cedar_last_pulled | 2026-08-12 — max(fetched_date) over 4 rows of data/raw/external/irs990/bmf_full_2026-08-12/_fetch_manifest.csv |
| **refresh_due** | **no** — source_has_through is NOT ESTABLISHED — this source cannot be called current or stale on the evidence held |
| age | Cedar's edge is 154 days old; our knowledge of the SOURCE is 20 days old; measured gap behind the source 0 days |
| refresh_cost | one monthly extract |
| refresh_command | the BMF leg of code/112 |
| breaks_on_refresh | np_ein_entity_hub.csv, np_ein_uei_bridge.csv |

#### Federal Audit Clearinghouse single audits (api.fac.gov)

| field | value |
|---|---|
| state | ❓ edge not established |
| host | `api.fac.gov` |
| publish_cadence | continuous acceptance |
| publish_lag | median 271d (2 CFR 200.512(a) allows 9 months = 274d); p90 569d; **30.93% land LATE**; max 3,464d |
| cadence basis | REFRESH_CADENCE 1.4 — from the source's own fy_end_date and fac_accepted_date, n = 6,780 |
| **cedar_holds_through** | **2026-08-12** — measured from `data/clean/fac_tribal_single_audits.csv`, column `fac_accepted_date`, 6,780 rows in scope |
| **source_has_through** | **—** — NOT RE-PROBED this run (an unkeyed request 403s; the keyed route answered 22 requests on 2026-08-26) (established 2026-08-12) |
| cedar_last_pulled | 2026-08-12 — max(built_date) in data/clean/fac_tribal_single_audits.csv |
| **refresh_due** | **no** — source_has_through is NOT ESTABLISHED — this source cannot be called current or stale on the evidence held |
| age | Cedar's edge is 20 days old; our knowledge of the SOURCE is 20 days old; measured gap behind the source 0 days |
| refresh_cost | api.data.gov key, 1,000/hr |
| refresh_command | code/147_build_fac_single_audits.py — **with a TWO-YEAR trailing window, every time. A deadline the median hits and a third of filers miss is not a cadence.** |
| breaks_on_refresh | fac_audit_gaming_disclosures.csv, fac_audit_sefa_gaming_programs.csv |

#### Grantmaker 990-PF / 990 Schedule I (the funder side)

| field | value |
|---|---|
| state | ① source not published |
| host | `apps.irs.gov` |
| publish_cadence | same as the 990 e-file corpus |
| publish_lag | ~18 months |
| cadence basis | GRANTMAKER_FUNDING_FLOWS_BUILD_LOG.md |
| **cedar_holds_through** | **2025-11-30** — measured from `data/clean/grantmaker_funding_flows.csv`, column `tax_period_end`, 18,656 rows in scope |
| **source_has_through** | **2025-12-31** — same corpus and the same structural lag as the 990 row above (established 2026-08-26) |
| cedar_last_pulled | 2026-08-12 — max(retrieved_date) in data/clean/grantmaker_funding_flows.csv |
| **refresh_due** | **no** — Cedar holds through 2025-11-30 and the source offers 2025-12-31 — nothing is owed. declared in the registry: same corpus and the same structural lag as the 990 row above |
| age | Cedar's edge is 275 days old; our knowledge of the SOURCE is 6 days old; measured gap behind the source 31 days |
| refresh_cost | rides the 990 pull |
| refresh_command | code/113 (grantmaker leg) |
| breaks_on_refresh | grantmaker_funding_coverage.csv, grantmaker_funding_overlap.csv |

### `subcontracting`

#### FSRS subawards via api.usaspending.gov

| field | value |
|---|---|
| state | ❓ edge not established |
| host | `api.usaspending.gov` |
| publish_cadence | continuous; primes file by end of the month following the award month |
| publish_lag | NOT MEASURABLE — the mature window (2021-08..2024-08) falls inside the FY2021-24 hole, so every plateau ratio computed from it is meaningless (PLATEAU_WARNING in 301) |
| cadence basis | REFRESH_CADENCE 1.5(b) |
| **cedar_holds_through** | **2026-08-03** — measured from `data/clean/subawards.csv`, column `subaward_date`, 72,837 rows in scope |
| **source_has_through** | **—** — NOT ESTABLISHED — code/121_pull_subawards_api.py holds the host right now; one poller per host (established —) |
| cedar_last_pulled | 2026-08-12 — max(fetched_date) in data/clean/subawards.csv |
| **refresh_due** | **no** — declared in the registry: NOT ESTABLISHED — code/121_pull_subawards_api.py holds the host right now; one poller per host |
| age | Cedar's edge is 29 days old; our knowledge of the SOURCE is — days old; measured gap behind the source 0 days |
| refresh_cost | ~2,733 paginated calls |
| refresh_command | code/121_pull_subawards_api.py pull --sequential (ALREADY RUNNING — do not start a second) |
| breaks_on_refresh | prime_sub_network.csv, subaward_entity_rollup.csv; the FEMA key 1843-GR35056 is NOT unique (11 villages) |

---

## THE SOURCES WITH NO SCHEDULE — a trigger, not a calendar

Roughly **1,555 entity websites** have no publication schedule at all, and inventing one would be a lie. Re-crawling them on a timer costs ~20 agent-days per pass and would mostly re-read pages that did not move.

**What the harvest ALREADY knows, with no re-crawl:**

| measured | value |
|---|---:|
| entities in the hub | 1,555 |
| entities with at least one mapped URL | 1,090 |
| URL rows in `data/staging/tribe_web_map/` | 5,260 |
| when those URLs were last checked | 2026-09-01 .. 2026-09-02 |
| **`wp-json` endpoints already proven** | **307** across 188 entities |
| of those, HTTP 200 | 279 |
| endpoints where `X-WP-Total` was captured | 65 |
| total items behind those endpoints (`archive_depth`) | 3,181 (median 27) |
| newsletter records harvested | 1,000 |

**Observed posting cadence, measured from the item dates behind those endpoints — not from anything a site claims:**

| observed cadence | sites |
|---|---:|
| roughly quarterly | 13 |
| roughly monthly | 12 |
| roughly semiannual | 7 |

### The proposal: CHECK, then HARVEST

A three-tier trigger that replaces the calendar. Nothing below requires a new crawler — every input already exists on disk.

**Tier 1 — the free check (`HEAD`-cheap, once a month).** For the 188 entities with a proven `wp-json` endpoint, one request each to `/wp-json/wp/v2/media?per_page=1` and `/wp-json/wp/v2/posts?per_page=1` returns the `X-WP-Total` header and the newest item's date **without downloading anything.** Store both. A site whose `X-WP-Total` and newest-item date are unchanged since the last check has not published, and needs no harvest. Baseline: 3,181 items across 65 endpoints are already recorded.

**Tier 2 — the cheap check for everything else (quarterly).** For the remaining sites, a conditional `GET` on the mapped URL (`If-Modified-Since` / `If-None-Match` from the stored `checked_date` and ETag) answers the same question in one request. A `304` is a definitive no-change. Where a host serves neither header, compare a hash of the extracted text, which the harvest already stores as `source_md5`.

**Tier 3 — a full harvest, and ONLY on a trigger.** Run the shard harvest for an entity when tier 1 or tier 2 says something moved, when the entity has never been checked (465 entities today), or when the owner asks. Never on a timer.

**Why this is the honest answer rather than a schedule.** A cadence column for a tribal vendor list would be a fabrication — the list changes when a tribal office remembers to update it, and no header, notice or index announces that. What CAN be established cheaply is whether the page moved, and that is a measurement rather than a guess. The observed cadences in the table above are exactly that: **derived from the dates of items the sites actually posted**, and they should be used to set each site's own check interval — a site posting monthly is worth checking monthly; one posting semiannually is not.

**Two rules this inherits and must not lose.** Read `robots.txt` and the terms page before any check, not just before a harvest — six publishers have stated restrictive terms and are excluded by every route. And one poller per host, always: a change-detection sweep across 1,555 hosts is still 1,555 requests and must be paced.

---

## The bounded probes that established the source edges above

*3 requests, one per host, ≥6s apart, taken on **2026-09-01** and carried forward — this run issued none. Re-take them with `--probe-net`. Host locks respected: ['eaglemountaincasino.com'].*

```
{"host": "www.federalregister.gov", "url": "https://www.federalregister.gov/api/v1/documents.json?per_page=1&order=newest&fields[]=publication_date", "status": 200, "count": 10000, "publication_date": "2026-09-01"}
{"host": "lda.gov", "url": "https://lda.gov/api/v1/filings/?page_size=1&ordering=-dt_posted", "status": 200, "count": 1976576, "dt_posted": "2026-09-01T20:53:39-04:00", "filing_year": 2026, "filing_period": "second_quarter", "filing_type_display": "2nd Quarter - Report (No Activity)"}
{"host": "lda.gov", "url": "https://lda.gov/api/v1/filings/?page_size=1&ordering=dt_posted", "status": 200, "count": 1976576, "dt_posted": "1905-06-24T00:00:00-05:00", "filing_year": 1999, "filing_period": "mid_year", "filing_type_display": "Mid-Year Report"}
```

<!-- CEDAR:CADENCE-MEASURED END -->

---

## THE SPINE OF THIS DOCUMENT: TWO JOBS, TWO CLOCKS

The owner's instinct — *"every quarter we can check for new entities … but
there's probably data that's more recurring"* — is right, and it splits cleanly.

| | **REFRESH** | **DISCOVERY** |
|---|---|---|
| question | new rows for entities we already know | entities we do **not** know |
| route | identifier-seeded (UEI / CAGE / EIN / tribe_id) | broad filter or full sweep |
| cost | small — a filtered read of a period window | large — a full-corpus scan |
| clock | **the LAG PROFILE below** — how long a period keeps growing | **the drift rate** — how fast the identifier list goes stale |
| owner | this document | `docs/DISCOVERY_GAP.json` · `code/276_measure_discovery_gap.py` |

They are different jobs because they fail differently. A refresh that runs too
slowly gives you *stale* numbers, which every reader can see. A discovery pass
that runs too slowly gives you *confidently wrong* numbers, which no reader can
see, because a missing entity leaves no hole in the table.

**The discovery clock, measured by script 276 (do not re-derive it here):**

| FY | rows a UEI-only pull would lose | |
|---|---:|---|
| FY2015 | 0.23% | the identifier list was near-complete |
| FY2019 | 6.24% | |
| FY2022 | 6.77% | |
| FY2023 | 7.49% | |
| FY2024 | 8.74% | |
| **FY2025** | **12.66%** | **+3.9 pp in one year** |

and, on the flag route, **9,719 entities carry a Native business-type flag in
FPDS prime data that the identifier route has never seen — 76.9% of all flagged
entities, $70.96B of obligations.**

Read those two together: coverage of the *known* population is fine and the
*known population itself* is drifting. The drift accelerated from ~1 pp/yr
(FY2019–23) to 3.9 pp in FY2025. **Quarterly discovery is the right instinct and
is, if anything, slightly conservative for contracting; annual is now too slow.**

⚠ A self-certification is not a determination. Everything discovery surfaces is
a **candidate for adjudication**, never a row to attribute. Goldbelt Raven, an
ANC subsidiary, certifies `alaskanNativeCorporationOwnedFirm = NO`.

---

# PART 1 — THE MEASURED LAG PROFILE

## 1.1 Where every collection actually stops, today

`EXACT_LAST_DATE` is the true maximum date in the file, not the month bucket. A
month bucket rounds a source that stops on the 3rd up to the 31st and hides four
weeks of lag — measured: prime `action_date` stops **2026-07-03**, which the
bucket `2026-07` reports as 12 days of lag when it is 40.

| collection | last data | our as-of | gap | **whose lag is it?** |
|---|---|---|---:|---|
| FERC docket filings | 2026-08-26 | 2026-08-26 | 0d | current |
| deals | 2026-08-20 | 2026-08-26 | 6d | current |
| subawards | 2026-08-03 | 2026-08-26 | 23d | source |
| FAC single audits | 2026-08-12 | 2026-08-13 | 1d | current |
| Federal Register | ~~2026-08-05~~ **2026-08-26** | 2026-08-26 | **0d** | ✅ **CLOSED 2026-08-26 — see PART 5** |
| NAGPRA notices | ~~2026-08-03~~ **2026-08-24** | 2026-08-26 | **2d** | ✅ **CLOSED 2026-08-26 — 2d is the source's own event gap** |
| lobbying (LDA) | 2026-08-04 | 2026-08-06 | 2d | **OURS — 20 days stale** |
| IBIA / IBLA appeals | 2026-07-28 | 2026-08-26 | 29d | source |
| prime contracts | **2026-07-03** | 2026-08-12 | **40d** | source (archive cut) |
| assistance | **2026-06-30** | 2026-08-26 | **57d** | source (archive cut) |
| CA gaming | 2026-06-30 | 2026-08-07 | 38d | ⚠ **NEITHER — re-diagnosed 2026-09-01 (cadence). See below the table.** |
| resource revenue | 2026-06-30 | 2026-08-13 | 44d | source |
| 990 Schedule I | 2025-12-31 | 2026-08-26 | **238d** | source (structural) |
| gaming facility metrics (CT monthly) | 2025-12-31 | 2026-08-26 | **238d** | ⚠ **RE-DIAGNOSED 2026-08-26: the SOURCE's, not ours — see PART 5** |
| FAADS | 2007-09-30 | — | 6,884d | **CLOSED BY DESIGN** |
| FL gaming | 2031-06-30 | — | — | ⚠ see 1.6 |

**The single most useful column here is the last one.** Three collections that
look "behind" are behind because *we have not pulled*, not because the source
has not published. **Two of those three were closed on 2026-08-26 (PART 5) and
lobbying is the one that remains.** Verified live at the run that first measured
this:

> `www.federalregister.gov` → HTTP 200, newest `publication_date` = **2026-08-26**.
> Cedar's newest is 2026-08-05. **The source is same-day current and we are 21
> days behind it.**

Do not diagnose a source from a stale local file. That is the cheapest error in
this whole document to make and it points every remedy in the wrong direction.

> ### ⚠ THE CALIFORNIA ROW WAS WRONG IN A THIRD WAY, AND IT IS THE EXPENSIVE ONE
>
> *Corrected 2026-09-01 by workstream **cadence**, on top of INT-2's parse
> repairs recorded at §1.6. This table's `whose lag is it?` column offers two
> answers — "source" or "OURS" — and California is **neither**.*
>
> **Measured today:** CGCC has published through the quarter ended
> **2026-06-30** and `ca_gaming_payments.csv` **holds 2026-06-30**. There is no
> acquisition gap. **181 California documents are on disk** in
> `data/raw/external/ca_gaming/`, fetched 2026-08-07, and *every* quarter this
> table ever called a "hole" was among them the whole time.
>
> What remains short is **53 money zones inside documents Cedar already has**,
> refused because their columns do not foot against the report's *own printed
> total*. That is `CAPTURED_NOT_PARSED` — **state 3, not state 2** — and it is
> enumerated per document with its measured discrepancy in
> `review/ca_rstf_captured_not_parsed_2026-09-01.md`. **Nothing here is a
> fetch. Re-downloading any of it changes nothing.**
>
> Two specific claims this document made and that measurement refuted:
>
> * **"the 98th report is an image-only scan needing OCR."** It is not. Measured
>   with the same library that produced the "0 characters" figure: **24,824
>   characters across 13 pages.** Its Exhibit 1 parses to 89 rows and foots on
>   all five columns, and it now contributes **445 rows**. The blocker was a
>   missing five-column mapping in `metric_for`, not an absent text layer.
> * **"2026-03 is missing; the CCGC series has real holes at the edge."** It was
>   never missing. It went **0 → 445 rows** the moment the parser was fixed.
>
> **The rule this earns, and it is a third one alongside the two already here.**
> §1.1 says *do not diagnose a source from a stale local file.* §5.3 says *do
> not diagnose OUR lag from a cached copy of the source either.* The third is:
> **do not diagnose a lag at all until you have looked in `data/raw/`,
> `data/staging/` and `review/`.** A row that is absent from a clean table has
> three possible causes and only one of them is a download. Naming the wrong one
> costs a session — this project has now spent three that way (California RSTF,
> New Mexico gaming FY2023–2026Q2, the staged NIGC set), and in every case the
> data was already on the disk of the machine doing the re-download.
>
> **Owner of the remaining fix: the gaming promotion workstream** (`code/103`
> and `code/92`), not this document and not an acquisition pass.

## 1.2 How long a period keeps filling in

Method: take the median row count over a **mature window** (periods old enough
that nothing should still be arriving), then walk backwards from the newest
period counting how many sit below 90% of it. For sources whose periods are not
uniform — 990 `tax_period_end` piles onto months 12 and 06, LD-2 posting onto
Jan/Apr/Jul/Oct, CA gaming onto quarter ends — the flat plateau is compared
against the **same calendar month** in the mature window instead. Both are
reported; **the seasonal one is the correct one wherever the two disagree.**

| collection | flat | **seasonal** | reading |
|---|---:|---:|---|
| prime contracts (monthly) | 3 | **3** | 2026-05 at 44%, 2026-06 at 54%, 2026-07 at 5% — the last is the archive cut |
| assistance | 2 | **2** | 2026-05 at 66%, 2026-06 at 60% |
| **990 Schedule I** | 6 | **1** | flat is an artifact; only 2025-12 is short — **at 12% of a December plateau** |
| FAC single audits | 2 | **2** | |
| CA gaming | ~~5~~ **2** | ~~**5**~~ **2** | ⚠ **RE-DIAGNOSED 2026-09-01 — see 1.6. Not lag and not a hole: a PARSE DEFECT in `code/103`, now fixed. 2024-12 went 0 -> 468 rows and 2026-03 went 0 -> 445. Two quarters remain short and the reason is named per document.** |
| resource revenue | 0 | **1** | |
| Federal Register · NAGPRA · FERC · lobbying | 1 | **1** | the current month only, i.e. our staleness |
| IBIA/IBLA · deals · gaming metrics · FAADS | 0 | **0** | no detectable fill |
| subawards | 1 | 1 | ⚠ **untrustworthy — see 1.5** |

**The headline: the two federal spending series stop filling in about two months
after a month closes, and they stop hard.** Prime: 2026-05 at 44% and 2026-06 at
54% of plateau, while every month before 2026-05 is at or above it. Assistance:
identical shape, two months. That is the number that sets their cadence, and it
is not the vendor's schedule.

## 1.3 The USAspending award archive — measured to the second

All 4,597 objects, **93.9 GB**, from the on-disk listing:

| | |
|---|---|
| stamp on every key | **`20260806`** |
| S3 `last_modified`, earliest | **2026-08-10T00:14:25Z** |
| S3 `last_modified`, latest | **2026-08-10T00:18:05Z** |
| distinct write timestamps | 206, all inside **3 minutes 40 seconds** |
| previous stamp | `20260706`, dead everywhere by 2026-08-12 |

Four things follow, and all four are operational:

1. **The whole archive is rewritten atomically, once a month, in under four
   minutes, at ~00:14 UTC.** FY2007 is rewritten as surely as FY2026.
2. **The stamp is the 6th; publication is the 10th.** A ~4-day production lag
   between as-of date and availability, consistent across the two stamps we
   hold. **Never probe for a new stamp before the 10th of the month.**
3. **Object metadata carries no signal about which years changed** — every
   object's `last_modified` moves every month whether its contents did or not.
   You cannot decide what to re-download from the listing. You must diff
   contents, which is what script 301's snapshot diff is for.
4. Probe the stamp **per-year at run start, never globally.** FY2007–2016 in
   Cedar came down under `20260806` and FY2017–2026 under `20260706`; a single
   global stamp variable would have mislabelled half the corpus.

> ⚠ **A TRAP, ENCODED IN THE SCRIPT SO NOBODY REPEATS IT.**
> `data/raw/contracts/usaspending_archive_2026-08-07/_SOURCE_MANIFEST.csv` is
> **generated from** `_state.json`. Their `rows_scanned` columns are identical by
> construction. Differencing them produces a clean "0.000% change across every
> fiscal year" table that looks exactly like a month-over-month archive
> comparison and **is not one.** It measures nothing.
> **Cedar holds no genuine cross-vintage measurement today.** Getting one is
> cheap and worth doing: re-filter one already-held fiscal year under the next
> stamp and diff the row counts. Until then, section 1.2's within-vintage fill
> curve is the best evidence available, and it should be labelled as such.

### 1.3a Whether a cross-vintage measurement can be had from disk — ANSWERED, and it cannot

*Measured 2026-08-26 by the harmonisation pass (`code/334`–`337`). The
conclusion above stands; what is new is that the REASON is now measured rather
than assumed, and the exact cost of obtaining one is stated.*

Two routes exist in principle. **Both are closed, and each for its own
structural reason.**

**Route 1 — diff the same fiscal year across the two archive stamps. CLOSED:
no fiscal year is held under both.** The stamps partition the years rather than
overlapping them:

| stamp | fiscal years held | rows |
|---|---|---:|
| `20260706` | FY2007, FY2024, FY2025, FY2026 | 131,495 |
| `20260806` | FY2008 … FY2023 | 93,536 |

There is no intersection, so there is nothing to difference.
`data/raw/contracts/usaspending_archive_2026-08-07/_state.json` carries a
single global `stamp = 20260706`, which is also why the per-year stamp had to
be recovered from the clean table rather than the manifest.

**Route 2 — diff the 2023 bulk extract against the 2026 archive on their
overlapping years. CLOSED: the two strata are DISJOINT ON TRANSACTION KEY.**
They do cover the same span (FY2008–2023), which makes the route look
available. Measured on `assistance_transaction_unique_key`:

```
stratum A (2023-04-09 bulk download)   476,924 keys
stratum B (archive stamp 20260806)      93,536 keys
keys present in BOTH                          0
```

Zero. `24_funding_merge.py` deduplicated on that key, so the archive
contributed only transactions the 2023 extract did not already have. **The
merge that made the table correct is the same merge that destroyed its ability
to measure retroactive correction.** That is worth stating plainly, because it
is not a defect — a deduplicated table is the right table to ship — but it does
mean the measurement has to be taken from the RAW extracts, before the merge,
or not at all.

**What would actually be needed, and what it costs.** One fiscal year already
held, re-pulled under the NEXT stamp, kept as a separate raw extract, and
diffed against the copy we hold — row counts first, then field values on the
shared transaction keys. **FY2023 is the cheapest candidate**: 34,511 rows, one
object, already held under `20260806`, and it is the only year served by both
eras so it exercises the merge logic too. The next stamp is `20260906`,
published **2026-09-10**; do not probe before the 11th.

⚠ **It is not attemptable today.** `code/121_pull_subawards_api.py pull
--sequential` holds `api.usaspending.gov` (PID 13736, confirmed live at 20:10Z
via `Win32_Process`), and `files.usaspending.gov` shares its rate-limit budget.
One poller per host, always.

> **The finding this earns: a table can be correct and unmeasurable at the same
> time.** Deduplication, backfill-merge and "replace the trailing window" all
> improve the shipped product and all destroy the evidence a freshness
> measurement needs. If a cross-vintage number is wanted, **the raw extract of
> at least one year must be retained unmerged, on purpose, before the merge
> runs.** Nothing in the pipeline does that today.

## 1.4 Submission lag, measured from the source's own two dates

The strongest evidence in this document, because it does not depend on our pull
history at all — only on two dates the source itself stamped.

**Federal Audit Clearinghouse — `fy_end_date` → `fac_accepted_date`, n = 6,780**

| | days |
|---|---:|
| p10 | 179 |
| **median** | **271** |
| p75 | 336 |
| **p90** | **569** |
| p99 | 1,370 |
| max | 3,464 |

2 CFR 200.512(a) requires submission within **9 months (274 days)** of the audit
period end. The median is **271 days** — the deadline describes the median
auditee almost exactly. **And 30.93% of tribal single audits land after it**,
with a p90 of 569 days and a tail past nine years.

> **A deadline that the median hits and a third of filers miss is not a
> cadence.** Planning FAC around 274 days captures half the population. A FAC
> refresh must re-read a **two-year trailing window**, every time.

**IRS 990 Schedule I — `tax_period_end` → our retrieval, n = 58,355**

p10 = **584 days**. That is an upper bound (it contains our own delay), but the
*tightest* bound available, and it is already 19 months. The structural ~18-month
990 lag is confirmed from the files, not assumed. Corroborated by the fill curve:
calendar-2025 fiscal-year-ends sit at **12% of a December plateau** and 2026 is
**zero rows**.

## 1.5 Two places the naive measurement lies, and the guards that catch them

Both are now detectors in script 301, not footnotes.

**(a) A single entity can move a monthly row count by 9x.**
Prime `2026-03` shows 37,323 rows against ~4,500 in the neighbouring months — a
ratio of 9.74 to plateau, which reads as a colossal reporting surge. It is one
vendor: **`ASRC FEDERAL FACILITIES LOGISTICS, LLC` (UEI `MA1VZ6667CB1`)
contributed 33,502 of them, 89.8% of the month**, matched on
`recipient_parent_uei`. It holds 62.6% of 2026-04 as well.

At fiscal-year granularity the same entity is **66% of all 61,813 FY2026 prime
rows** (`ANRC-ARCSLO-00`). **An FY2026 that is two-thirds one ANC is not a normal
year**, and any FY2026-vs-FY2025 comparison must say so.
`SINGLE_ENTITY_DOMINATED_PERIODS` now flags every period where one entity holds
≥25% of rows. **Row counts are not a robust series; `distinct_entities_by_period`
is, and it is now emitted alongside.**

**(b) The mature window can land inside a known hole.**
Subawards' mature window (2021-08 → 2024-08) is *exactly* the FY2021–24 upstream
gap — 152 / 80 / 155 rows in calendar 2021/22/23 against an all-period median of
249. Every ratio computed from it was 30–70x and meaningless.
`PLATEAU_WARNING` now fires whenever the plateau falls below 25% of the
all-period median. **No subaward cadence can be measured until the hole is
filled**, and `code/121_pull_subawards_api.py pull --sequential` is running right
now (PID 13736, submitted 21:19Z, collect deadline 2026-08-27T05:19Z) trying to
fill it.

## 1.6 Data oddities this measurement surfaced

- **`fl_gaming.period_end` runs to 2031-06-30** with a steady 22–24 rows/month
  through 2031. These are forward-dated compact *schedule* rows, not
  observations. `period_end` is the wrong freshness column for that collection
  and any "last data" claim built on it is wrong by five years.
- ~~**CA gaming is missing 2026-03 entirely**, and 2025-03 (112) / 2025-12 (110)
  are ~25% of a ~450-row quarter. The CCGC series has real holes at the edge; it
  is not merely lagging.~~

  > **CORRECTED 2026-09-01, workstream INT-2. This entry was wrong in the way
  > that costs the most: it described a PARSE DEFECT as a source gap, which
  > sends the next agent to re-download documents already on disk.**
  >
  > Every one of those quarters was on disk in `data/raw/external/ca_gaming/`
  > the whole time. Three separate defects in `code/103_build_california_gaming.py`
  > were discarding them, all three now fixed and all three verified against
  > the reports' OWN printed totals:
  >
  > 1. **A number split across two text spans.** Two of the 93rd report's 89
  >    Exhibit-1 rows render `25,438,385.42` as `25,438` + `,385.42`, 2.74pt
  >    apart. The tail is not money-shaped, so it fell into the row LABEL
  >    ("Pinoleville Pomo Nation ,385.42") and the 2.74pt offset opened a
  >    phantom fifth column holding two values. `metric_for` has no
  >    five-column mapping, so **all five columns were refused as
  >    `unmapped_column` and the entire 89-row exhibit produced nothing.**
  >    Rejoined, the inception column foots to $1,826,037,694.56 against a
  >    printed $1,826,037,694.56, exactly.
  > 2. **All-or-nothing footing.** One column short by **$1.00 over 62 tribes**
  >    (1.6e-8 of the total — the source's own per-row cent rounding) failed
  >    the whole zone and threw away 62 good rows. Footing is now per column
  >    with a stated relative tolerance, and a column accepted that way is
  >    labelled `foots_within_rounding` on every row. The 95th report's
  >    **$40,000** discrepancy is 2.4e-5 relative and is still refused.
  > 3. **A column CGCC added.** From the 98th report on, Exhibit 1 carries
  >    "Annual Distribution from Revenue Received" as a fifth column. No
  >    five-column mapping existed, so the two newest reports produced almost
  >    nothing.
  >
  > **And the 98th report is NOT an image-only scan.** `docs/datasets/gaming_sources.md`
  > 1E said it had 0 characters and needed OCR. Measured 2026-09-01: **24,824
  > characters across 13 pages**, Exhibit 1 parses to 89 rows and foots on all
  > five columns. There is no OCR job here and there never was.
  >
  > **Result:** `ca_gaming_payments.csv` 40,164 -> **41,758**. 2024-12-31
  > 0 -> **468**; 2026-03-31 0 -> **445**; 2026-06-30 167 -> **612**.
  >
  > **What is genuinely still short, and why, per document** — these are
  > `CAPTURED_NOT_PARSED`, listed with their measured discrepancy in
  > `review/ca_rstf_captured_not_parsed_2026-09-01.md`. No row is invented for
  > any of them.
- **`gaming_facility_metrics` is two series wearing one name.** Its monthly
  component is *only* Connecticut: `CT Dept of Consumer Protection /
  data.ct.gov`, **3,240 rows, 747 facility-months, 1993-01 → 2025-12**, Foxwoods
  396 + Mohegan Sun 351, **with zero missing months in either**. Everything else
  in the file is annual or irregular. Cadence must be set per series, not per
  file.
  > *Doc correction:* the standing figure is **748** casino-months; the file
  > holds **747**. Off by one, harmless to any conclusion, recorded so nobody
  > re-derives it.
- **`federal_funding_transactions.csv` holds 701,955 rows, not 684,923.**
  `START_HERE.md` and the dataset table still say 684,923. The table was
  refreshed today (`fetched_date` max = 2026-08-26) and **carries two archive
  vintages simultaneously — `20260706` on 131,495 rows and `20260806` on
  93,536.** That is fine as provenance and fatal as a `vintage` string; see
  Part 4.

---

# PART 2 — THE DOCUMENTED SCHEDULE, PER SOURCE

Each row: what the source says, then what we measured. Verified rows are marked.

| source | stated schedule | measured | verdict |
|---|---|---|---|
| **USAspending award archive** | monthly replacement | stamp = 6th, published 10th 00:14Z, whole 93.9 GB in 3m40s | ✅ **confirmed, and tightened to the minute** |
| **USAspending transaction load** | agencies submit ≥ twice monthly (DATA Act) | assistance fills for ~2 months past a month's close | ✅ consistent |
| **FPDS-NG** | agencies report within 3 business days of award | prime fills for ~2 months past a month's close | ⚠ the 3-day rule is about *entry*; corrections run months longer |
| **FPDS-NG ATOM feed** | — | `sam.gov/contracting`: *"will be retired later in FY 2026"* | ⛔ **an expiry date, not a standing option** |
| **LDA (LD-2)** | quarterly, **due 20 days after quarter close** — 20 Jan / Apr / Jul / Oct | median **exactly 20 days**; only **57.4%** filed by day 20 | ⚠ **half-true — see 2.1** |
| **LDA (LD-203)** | semiannual, due 30 Jan / 30 Jul | visible as Feb (2,147) and Aug (2,435) posting bumps with no May/Nov twin | ✅ **inferred from the seasonal profile** |
| **LDA pre-2008 (HLOGA break)** | LD-2 was **semiannual** before 2008 | 2006–07: `mid_year` + `year_end` only. 2008: four quarters. | ✅ **the break is in the data, at exactly 2008** |
| **FSRS subawards** | prime files by end of the month following the award month | not measurable — the mature window is inside the FY2021–24 hole | ⚠ **unmeasurable today** |
| **Federal Audit Clearinghouse** | 2 CFR 200.512(a): earlier of +30d after auditor's report or **9 months** after period end | median 271d, **p90 569d, 30.9% late** | ⚠ **the deadline is not the cadence** |
| **Federal Register** | every federal business day; public inspection the day before | newest `publication_date` = 2026-08-26 (probed live, HTTP 200) | ✅ **confirmed same-day** |
| **IRS 990 e-file index** | annual `index_YYYY.csv`, submission years **2017–2026**; `index_2016` and earlier → 302 → /404 | 5,576,866 index rows streamed (concurrent agent) | ✅ e-filing begins 2017 (Taxpayer First Act) |
| **IRS 990 returns** | released in batches as processed | p10 = **584 days** from fiscal-year end | ✅ **~18-month structural lag confirmed** |
| **IRS BMF** | monthly exempt-organisation extract | 1,957,340 rows held | not re-probed this run |
| **FERC eLibrary** | indexed ~1 business day after acceptance | last filed date = **2026-08-26**, i.e. today | ✅ **confirmed** |
| **IBIA / IBLA** | posted to Interior year indices as issued | last decision 2026-07-28, 29d back | ✅ event-driven, ~1 month |
| **NAGPRA notices** | Federal Register documents | same daily cadence, event-driven arrival | ✅ |
| **regulations.gov** | continuous; comment periods are the events | not yet built — `code/221`, staged in `review/` | ⚠ **sweep docket-first, never entity-first** |
| **CourtListener / RECAP** | continuous | 200 anon, **429s under load**; get a free Free Law Project token | not swept |
| **SEC EDGAR full-text** | continuous | reachable, not swept | not swept |
| **NIGC gaming revenue report** | **annual**, for the prior FY | our gaming series ends 2025-12 | annual |
| **CT DCP** | **monthly per casino** | **747 facility-months, zero gaps, 1993-01 → 2025-12** | ✅ **the only true monthly gaming series Cedar holds** |
| **CA CCGC** | quarterly | ~~quarterly, **with 2026-03 missing and edge quarters short**~~ **CORRECTED 2026-09-01: quarterly, and Cedar holds the newest quarter CGCC has published (2026-06-30). 2026-03 was never missing — it was mis-parsed and is now 445 rows.** | ✅ **no lag and no hole.** The residual is 53 money zones inside documents already on disk that do not foot against the report's own printed total — `CAPTURED_NOT_PARSED`, **state 3**, enumerated in `review/ca_rstf_captured_not_parsed_2026-09-01.md`. **Not a fetch.** |
| **other state regulators** | annual, mostly | ~~NM & AZ 403 behind Cloudflare — `NOT_CHECKED`, **not** `NOT_FOUND`~~ **NM CORRECTED 2026-09-01: New Mexico was never a fetch problem for FY2023-2026Q2. Fourteen NMGCB quarterly releases were already extracted and footed 14/14 by `code/216` and sat in `review/`. Promoted 2026-09-01 through `code/92`; `gaming_capacity_official` NM went 1,090 -> 1,278 and now reaches 2026-06-30. AZ is unchanged.** | |
| **ONRR / resource revenue** | monthly disbursement, monthly + annual statistics | monthly, flat, ends 2026-06-30 | ✅ |
| **LODES** | annual, ~2-year lag | not re-probed | annual |
| **QWI** | quarterly, ~2–3 quarter lag | not re-probed | quarterly |
| **QCEW** | quarterly, ~5 months after quarter close | not re-probed | quarterly |
| **FAADS** | **retired** — superseded by USAspending | ends **2007-09-30**, 6,884 days back | ⛔ **closed by design; no cadence** |
| **Advan / Dewey** | weekly patterns | usable window **2018-03 → 2025, 2026 breaking** | ⛔ **cannot serve a recent-first cadence at all** |
| **api.sam.gov** | — | **10 calls/day** pending an org role request | ⛔ **not contacted; uniquely required for nothing** |

## 2.1 The LDA finding, because it changes the pull date

Measured over all **27,796** Cedar LD-2/LD-203 filings, days from the reporting
period's close to `dt_posted`:

| | |
|---|---:|
| median | **20** — the statutory deadline, exactly |
| **filed by day 20 (the deadline)** | **57.4%** |
| filed by day 27 (deadline + 1 week) | 70.5% |
| filed by day 34 (deadline + 2 weeks) | **74.0%** |
| filed by day 55 | 88.2% |
| filed by day 90 | 92.0% |
| filed by day 180 | 95.2% |
| filed by day 365 | 98.1% |
| p90 / p99 / max | 64 / 495 / 5,885 days |
| posted on or before the period close | 1,373 (early filers and terminations) |

Per quarter the medians are identical (20d) and the p90s are 42–55d. Under the
pre-2008 semiannual regime they were far looser: median 45d, p90 151–224d.

**And then the live probe, which is the finding that matters:**

> `lda.senate.gov` → HTTP 200. 1,976,414 filings. Ordered by `-dt_posted`, **the
> single most recently posted filing in the entire LDA system today is a
> `2A — 2nd Quarter Amendment` for filing year 2024** — a period that closed
> **2024-06-30, 787 days ago.**

The back-catalogue never stops moving. **A period-keyed pull is structurally
incapable of catching that filing.** The refresh key must be `dt_posted`, not
`filing_year` + `filing_period`.

> ⚠ **The strength of this one deserves stating precisely.** It rests on a
> *single* request. The API echoed `ordering=-dt_posted` back in its `next` URL,
> so the parameter was **accepted** — and acceptance is not application. This
> repo already records the shape: `recipient_type_names` on USAspending returns
> HTTP 200 with an empty set for a bogus value rather than an error. **Confirm
> with a second request** (`?ordering=dt_posted`, oldest-first) before quoting
> "787 days" as a headline. What does *not* depend on the probe, and is measured
> over 27,796 rows, is the distribution: **p99 = 495 days, max = 5,885**. The
> trailing re-pull is justified by the distribution alone.

### 2.1a THE SECOND REQUEST WAS TAKEN, 2026-09-01 (workstream `cadence`)

*Three requests to `lda.gov`, ≥7s apart, recorded verbatim in PART 0's probe
block and in `docs/REFRESH_CADENCE.json`.*

**The caution above was right to be issued, and it splits three ways.**

**1. `ordering` IS applied, not merely accepted.** Ascending and descending
return different records, and the ascending one is unmistakable:

| request | `dt_posted` | filing |
|---|---|---|
| `?ordering=-dt_posted` | **2026-09-01T20:53:39-04:00** | 2026 Q2, `Q2Y` no-activity report |
| `?ordering=dt_posted` | **1905-06-24T00:00:00-05:00** | `filing_year` 1999, mid-year |

A parameter that was accepted-but-ignored would have returned the same row
twice. **The `-dt_posted` refresh key is sound** and §3.3's recommendation
stands unchanged. *(The 1905 date is LDA's own data-quality artefact on a 1999
filing, recorded here so nobody reads it as a Cedar parse defect.)*

**2. The "787 days" headline does NOT survive, and it was never structural.**
Today the newest posted filing in the whole LDA system is **a 2026 Q2 report
posted this evening**, not a 2024 amendment. What the 2026-08-26 probe caught
was one moment. **The durable evidence is the distribution measured over 27,796
Cedar filings — p99 = 495 days, max = 5,885 — exactly as the caution said.**
Quote the distribution; never quote the single newest filing as a property of
the system.

**3. `lda.senate.gov` is NOT dead, and `docs/API_KEYS.md` says it is.**
`API_KEYS.md` records *"`lda.senate.gov` published a `Sunset: Fri, 31 Jul 2026`
header and is now dead."* Probed 2026-09-01: **`lda.senate.gov/api/v1/filings/`
returns HTTP 200** and serves lda.gov's content — the `next` URL in its own
response body is `https://lda.gov/api/v1/filings/?page=2`. It redirects; it has
not stopped answering. Both documents are half-right and the operational
consequence is small but real: **a script pointed at the old host will keep
working, which is precisely why nobody will notice when it eventually stops.**
Point new code at `lda.gov`. `docs/API_KEYS.md` is another owner's file and is
**named, not edited**, here.

**4. A free growth rate, from the two counts.** The corpus went **1,976,414
(2026-08-26) → 1,976,576 (2026-09-01)**: **+162 filings in 6 days, ~27/day
system-wide.** That is the cheapest possible sanity check on any future LDA
pull — a refresh that returns far more or far less than ~27/day × elapsed is
reporting on something other than new filings.

---

# PART 3 — THE CALENDAR

## 3.1 The recommended default

| collection | REFRESH | DISCOVERY | trigger date | cost | if you skip a cycle |
|---|---|---|---|---|---|
| **Federal Register / federal actions** | **daily** | n/a — no entity population | any business day | minutes, ~1 API page/day | you go blind to the recognition-notice trigger that fires the spine rebuild |
| **FERC dockets** | **weekly** | quarterly | any | ~300 docket sheets, hours | little — filings persist; only the review queue goes stale |
| **NAGPRA notices** | **weekly** (rides the FR pull) | with the FR sweep | any | free, same request stream | nothing |
| **Prime contracts** | **monthly, on the 11th** | **quarterly** | archive publishes the 10th ~00:14Z | 20 objects × ~1.2–2.0 GB; hours | one month of new awards; the 2-month fill window means the *previous* month was provisional anyway |
| **Assistance** | **monthly, on the 11th** | **quarterly** | same object set | 20 objects; hours | same |
| **Subawards (FSRS)** | **monthly**, once the FY2021–24 hole closes | quarterly | after the prime refresh | ~2,733 paginated calls; **gated on the SAM org role** | the hole stays open; nothing else moves |
| **Lobbying (LDA)** | **quarterly at deadline + 10d (= day 30 from close), keyed on `dt_posted`, with a 4-quarter trailing re-pull** | annual | 30 Jan / 30 Apr / 30 Jul / 30 Oct | 15/min anon, 120/min keyed — cheap | you miss ~28% of the quarter *and* every amendment to the last two years |
| **990 / nonprofits** | **semiannual** | annual | Feb and Aug | e-file index is 10 annual files, ~77 MB each | **nothing.** An 18-month structural lag makes any faster cadence theatre |
| **FAC single audits** | **quarterly, with a 2-YEAR trailing window** | annual | ~3 weeks after each calendar quarter | api.data.gov key, 1,000/hr | ~31% of audits land late; a 9-month window silently drops them |
| **CT gaming (monthly)** | **monthly** | n/a — 2 facilities | ~mid-month | trivial, one open-data endpoint | ~~currently 8 months behind; the cheapest win in the file~~ — **wrong: measured live 2026-08-26, the endpoint itself stops at 2025-12-31. Cedar holds every casino-month it serves. See PART 5.** |
| **CA gaming (quarterly)** | **quarterly** | quarterly | ~6 weeks after quarter close | small | ~~edge quarters are already short and 2026-03 is already missing~~ **corrected 2026-09-01: that was a parse defect, fixed. 2026-03 is present (445 rows). What remains short is named per document in `review/ca_rstf_captured_not_parsed_2026-09-01.md`.** |
| **Other state gaming** | **annual** | annual | per state | ~~varies; NM/AZ blocked at 403~~ **NM is quarterly and current to 2026-06-30 as of 2026-09-01; AZ still 403s an automated client** | little |
| **NIGC gaming revenue** | **annual** | annual | on release | one report | a year |
| **Resource revenue (ONRR)** | **monthly** | annual | ~6 weeks after month close | small | one month |
| **Deals** | **weekly sweep, quarterly deep pass** | continuous — deals *are* discovery | any | manual + press | **link rot.** Backfill reverse-chronologically; this is the one collection where delay destroys evidence |
| **IBIA / IBLA appeals** | **monthly** | annual | any | year indices | one month |
| **Entity spine** | **on the Federal Register recognition notice** | — | event | cascades everywhere | the whole build keys to it |
| **FAADS** | ⛔ **never** | ⛔ never | — | zero | **nothing, ever. The source ended in 2007 by design.** |
| **Advan / Dewey** | ⛔ **no recent-first cadence possible** | — | — | 298 GB national | its window ends in 2025 |
| **SAM** | ⛔ **not required for anything** | — | — | 10 calls/day | nothing — a concurrent agent proved SAM is uniquely required for nothing |

## 3.2 Why "the 11th"

The archive publishes on the **10th at ~00:14 UTC** with a stamp dated the
**6th**. Probing on the 9th finds last month's objects and burns a request
budget against a host that has already given us a 62-minute IP cooldown for
exactly that kind of impatience. Probing on the 11th finds the new stamp on the
first try. **Probe per-year, and never assume one global stamp.**

## 3.3 Why LDA moves from "+2 weeks" to "+10 days with a 4-quarter tail"

The old doc said *"pull two weeks after each deadline so late and amended
filings are in."* Measured, day 34 from period close captures **74.0%**. The
correction is not to wait longer — the curve is flat after day 55 and you would
be waiting for a 4% tail — but to **stop pulling by period at all**. Key on
`dt_posted >= last_pull` and re-read the trailing four quarters every cycle.
That is what catches a 2024-Q2 amendment posted in 2026.

## 3.4 Constraints that gate the calendar

- **SAM is 10 calls/day** pending an org role request. It gates nothing in the
  table above, because SAM is now uniquely required for nothing — but any plan
  that reintroduces a SAM dependency inherits a 10/day ceiling and must be
  costed at that rate. **Do not contact `api.sam.gov` casually.**
- **The FPDS-NG ATOM feed retires in FY2026.** It is a route with an expiry
  date. Anything that depends on it needs its data extracted *before* the
  retirement, not a cadence *around* it.
- **990s lag ~18 months structurally.** The 2025 endpoint is already near the
  source's own limit. A quarterly nonprofit cadence buys nothing.
- **Advan/Dewey's usable window is 2018-03 → 2025, 2026 breaking.** It cannot
  serve a recent-first cadence at all. Treat it as a historical panel.
- **One poller per host, always.** `api.usaspending.gov` and
  `files.usaspending.gov` are different hostnames and **one rate-limit budget** —
  they refused the same IP within two minutes of each other. Check
  `Win32_Process.CommandLine`; `ps aux` cannot answer this on Windows and
  manufactures false confidence. Where a peer is already polling, **its log is
  the cheapest probe available** and strictly better than adding a second prober.

### Host state observed at this run

- **`code/121_pull_subawards_api.py pull --sequential` is LIVE** (PID 13736,
  parent 8404). Both usaspending hosts were therefore refused by this script by
  policy, not by preference. Script 301 enumerates live pollers at start and
  records them in its output. **A dead wrapper is not a dead poller — and a live
  wrapper is not a live poller either. Check the child.**
- **`logs/_HOSTLOCK_web.archive.org.json` is no longer stale.** It was recorded
  as `active: true` behind dead PID 7420 with two items queued for 19 days. It
  has since been taken over by `code/213_cdx_targeted_nm_az_documents.py` (PID
  26476, claimed 22:58:48Z, `took_over_from: code/211_…`) and **released at
  2026-08-26T23:08:38Z**. No takeover was needed by this work.
- 266 host locks exist on disk. **Two were active at the final run** —
  `api.usaspending.gov` (PID 13736, `code/121_pull_subawards_api.py pull`, three
  jobs queued behind it) and `gaming.az.gov` (`code/217_pull_az_adg_report_archive.py`,
  claimed 23:29:32Z, a concurrent agent working the NM/AZ regulators). Script 301
  reads both and defers; it never probes a locked host.
- Three bounded probes were issued, one per host, ≥6s apart, honouring locks:
  `www.federalregister.gov` **200**, `lda.senate.gov` **200**, `api.fac.gov`
  **403**. The 403 is a fact about *that unauthenticated request* — `api.fac.gov`
  is fronted by api.data.gov and the keyed route answered 22 requests
  successfully at 22:37Z today. **A 403 on an unkeyed request is not a statement
  that the endpoint is closed.**

---

# PART 4 — TYING IT TO THE PRODUCT

Collections ship carrying `vintage`, `version` and `updated`, and the server's
docstring is explicit: **"Version and vintage are load-bearing, not garnish"** —
the citation string is generated from them. So the cadence must produce an
**honest** `vintage` on a schedule, and honesty here has a specific meaning:

> **`vintage` must name the last date the SOURCE covers, never the date we
> pulled.** They differ by 40 days on prime and 57 on assistance right now. A
> collection stamped `vintage: 2026-08-26` whose newest contract action is
> `2026-07-03` is a false citation, and it is false in the direction that
> flatters us.

**A second rule the measurement forces:** a collection assembled from more than
one source vintage cannot carry a single `vintage` string honestly.
`federal_funding_transactions.csv` today holds **`20260706` on 131,495 rows and
`20260806` on 93,536** — the file is real and correct, and no single stamp
describes it. Either re-pull the whole span under one stamp before shipping, or
publish `vintage` as the **oldest** contributing stamp and say so. Do not publish
the newest.

### 4.0a BOTH RULES ARE NOW IMPLEMENTED, AND THE COMPOSITION IS THREE, NOT TWO

*2026-08-26, `code/335`–`337` and the `code/87_build_dataset_notes.py` change.*

**The count above was incomplete.** 131,495 + 93,536 = 225,031 against a file
of **701,955 rows**, so **476,924 rows — 67.9% of the table — carried NO stamp
at all** and were invisible to a two-way description. They are not a mystery:
`source_file` names them to the day as the `Assistance_PrimeTransactions_`
**2023-04-09** bulk download. The composition is three strata, and it is
**year-aligned**:

| stratum | vintage | fiscal years | rows |
|---|---|---|---:|
| A | `usaspending_bulk_download_2023-04-09` | FY2008–2023 | 476,924 |
| B | `usaspending_award_archive_20260806` | FY2008–2023 | 93,536 |
| C | `usaspending_award_archive_20260706` | FY2007, FY2024–26 | 131,495 |

⚠ **Read stratum C carefully. FY2024, FY2025 and FY2026 sit on `20260706`,
which START_HERE records as dead everywhere since 2026-08-12.** The most recent
fiscal years — the ones a launch piece leads on — are the un-refreshed ones.
That is the opposite of the intuitive assumption and it should drive the next
re-pull's priority.

**What was implemented, so the next reader does not redo it:**

1. **Per-row vintage, never blank.** `code/335_harmonize_assistance_seams_in_place.py`
   adds `source_vintage` and `source_vintage_basis` to every one of the 701,955
   rows. A reader can now tell which rows came from which vintage by reading
   the row. The stamp is derived from `source_archive_stamp` where present and
   from the pull date recorded in `source_file` where it is not — both are
   recorded facts, neither is inferred.
2. **`vintage` in the notes contract is no longer the build date.**
   `code/87_build_dataset_notes.py` set `"vintage": TODAY`, which is exactly the
   false citation this section warns about. It now emits the **maximum of the
   table's period column** — so assistance cites **`2026-06-30`**, its true
   source edge, instead of `2026-08-26`, a **57-day overstatement removed** —
   plus `vintage_basis`, `built` (the old value, honestly named), and
   `source_vintages` carrying the full composition with
   `vintage_is_a_range: true`. A collection assembled from several vintages now
   ships the composition rather than choosing one and being wrong about the
   rest.
3. **A bare year stays a bare year.** Where a table's only period is a fiscal
   year — `gaming_revenue_bounds` — the vintage is `2025`, not a fabricated
   `2025-12-31`. Inventing a day is the defect that already put 415 gaming
   dates on day-15 and day-31.

**The audit that says this is the only such table:**
`code/334_audit_source_vintage_mixing.py` scanned **all 276 tables** under
`data/clean/` for multiple source vintages in one file. **One is mixed —
`federal_funding_transactions.csv` — and 275 are not.** See
`docs/VINTAGE_MIXING_AUDIT.json`.

⚠ **`prime_contracts.csv` is clean only because it records nothing.** It has no
`source_archive_stamp` column, so it cannot be mixed by measurement — but its
raw extracts came down under **both** stamps (FY2007–2016 under `20260806`,
FY2017–2026 under `20260706`, per §1.3), and that split survives into the clean
table with no column to expose it. **Assistance is the better-documented of the
two, not the worse one.** Giving prime the same `source_vintage` column is the
obvious next step and was not done here.

## 4.1 The year-turn refresh, per collection, stated exactly

Launch before end of calendar 2026; refresh once the year turns. FY2026 closed
2026-09-30, **but prime data stops 2026-07-03 and assistance 2026-06-30, so
FY2025 is the last complete fiscal year** and must be what the launch
collections advertise.

| collection | what the year-turn refresh changes | **when the data supports saying it** |
|---|---|---|
| **Prime contracts** | FY2026 becomes complete; `vintage` moves FY2025 → FY2026 | **archive published 2027-01-10** (stamp `20270106`). FY2026 closed 2026-09-30 + the measured 2-month fill = settled by ~2026-12-01, and the January archive is the first to carry all of it. **Do not claim a complete FY2026 before 2027-01-11.** |
| **Assistance** | same | same object set, same date |
| **Subawards** | FY2026 subawards land — **only if the FY2021–24 hole closed first** | FSRS filing +1 month after award month, so FY2026 is filed by ~2026-11-30 and appears in the **2027-01-10** archive. Blocked until 121 succeeds. |
| **Lobbying** | 2026 Q4 (closes 2026-12-31) | **2027-01-30**, deadline + 10d. Also re-read 2025Q4–2026Q3 for amendments; expect ~4% of 2026 filings still to arrive after this pull. |
| **990 / Schedule I** | **almost nothing** | tax-year-2025 volume is **4,614 rows against 9,779 for 2024 — 47%**, and the split says why: **June-2025 fiscal-year ends are fully in, December-2025 ends are at 12% of a December plateau**, because their extended deadline is 2026-11-15. Maturity ~mid-2027. **A year-turn 990 refresh is not worth running.** Move it to the Feb cycle and describe the collection as 2024-complete / 2025-partial. |
| **FAC single audits** | FY2025 audits (Dec-2025 year ends, due 2026-09-30) mostly land | **2027-01**, and *still* re-read two years back — 31% arrive late. FY2026 will not be presentable until 2027-09 at the earliest. |
| **CT gaming** | 2026 monthly series completes | **~2027-01-15**, one month after December. This one is genuinely current if we pull it. |
| **CA gaming** | 2026 Q4 | ~**2027-02-15**. ~~Backfill 2025-03, 2025-12 and the missing **2026-03** in the same pass — those are holes, not lag.~~ **2026-03 needed no backfill: it was on disk and mis-parsed, fixed 2026-09-01. 2025-03 and 2025-12 are still short and the reason is a footing failure in the document, not an absent document — do not re-fetch them.** |
| **NIGC** | FY2026 gaming revenue report | **mid-2027**. Nothing to do at the year turn. |
| **Resource revenue** | 2026 months complete | ~**2027-02-15** |
| **Federal Register / NAGPRA / FERC / appeals** | continuous; the year turn means nothing | any day — but **pull now**, they are 20–21 days stale |
| **Entity spine** | Interior's annual recognised-entities notice | published late January (91 FR 4102 was **2026-01-30**). **Trigger the spine rebuild from that notice, not from a timer.** |
| **FAADS** | ⛔ nothing, ever | it is a fixed historical asset; stamp it once and never touch it |
| **Advan / Dewey** | ⛔ nothing | window ends 2025 |

**The one-sentence version for the owner:** *the year turn is a single event on
2027-01-10/11 that upgrades prime, assistance and subawards from FY2025-complete
to FY2026-complete; lobbying follows on 2027-01-30; nonprofits do not move at all
and should not be re-pulled; and four collections are stale today for reasons
that have nothing to do with the calendar.*

## 4.2 The collections that need no cadence

- **FAADS** — closed by design, ends FY2007. Stamp it once.
- **Advan / Dewey** — window closes 2025.
- **Anything sourced from the FPDS-NG ATOM feed** — extract before the FY2026
  retirement; there is no cadence, only a deadline.
- **Historical statute, compact text, ANCSA rulings** — settled facts with URLs.
  They change only when Congress acts, which the Federal Register feed sees.

---

## WHAT THIS CORRECTS IN THE 2026-08-06 VERSION

The previous document was written from publication schedules. Four of its rows
do not survive contact with the files.

1. **"Prime contracting — pull weekly."** ❌ The archive is replaced **monthly**,
   atomically, and there is nothing new between replacements. Weekly costs seven
   probes to learn one fact and risks the IP cooldown. → **Monthly, on the 11th.**
2. **"Federal funding — pull weekly; the last ~4 weeks are provisional."**
   ❌ Right in spirit, wrong in size. Measured, **two months** are provisional
   (2026-05 at 66%, 2026-06 at 60%), not four weeks. → **Monthly, trailing
   2-month re-read.**
3. **"Lobbying — quarterly, +2 weeks."** ❌ Day 34 from period close captures
   **74.0%**, and the newest filing in the whole LDA system today amends a period
   that closed in 2024. → **Deadline + 10d, keyed on `dt_posted`, with a
   4-quarter trailing re-pull.**
4. **"Nonprofit / 990 — quarterly."** ❌ p10 is 584 days. A quarterly cadence on
   an 18-month lag manufactures churn in a dataset that did not change. →
   **Semiannual.**

Three of its rules survive unchanged and are re-affirmed here:
**re-pull the trailing window rather than appending**; **never use a natural key
you have not proved unique** (the FEMA subaward `1843-GR35056` files against
eleven different Alaska Native villages); and **an upsert must never overwrite a
human ruling**.

## After ANY refresh, re-run in this order

```
py -3 code/62_no_regression_check.py       # baseline BEFORE
<the refresh>
py -3 code/124_apply_rulings_in_place.py   # rulings reapplied on top
py -3 code/207_normalize_extent_competed.py  # in-place; a prime rebuild reverts it
py -3 code/168_link_adjudication_hubs.py   # in-place enrichers run LAST
py -3 code/301_source_freshness_probe.py   # record what actually moved
py -3 code/62_no_regression_check.py       # must report no regressions
```

**Never run `01`, `09`, `41` or `88`.** They rebuild from a stale upstream and
silently delete later work.

**A full-rebuild stage and an in-place enricher on one file need an ordering, and
the enricher must run LAST.** This has now bitten FERC four times in one day.
Before any rebuild, check for a `.bak_*_pre<script>` file sitting beside the
target — that is the signal that an in-place linker has touched it.

**And run script 301 immediately after every refresh.** Its snapshot diff is the
only mechanism that turns "we think the source corrects retroactively" into a
measured trailing-window number. Today it holds a baseline for all 20
collections and reports no movement (nothing has refreshed since it was taken).
After the next refresh it will name **the oldest period that moved**, and that
number replaces every within-vintage estimate in Part 1.

> **The rule 301 earned against itself, on its first day.**
> `py -3 code/301_source_freshness_probe.py --only deals --stages files`
> overwrote the 243 KB full measurement with a 3.9 KB one and truncated the
> snapshot to 68 bytes — **erasing the diff baseline for all twenty
> collections**. It printed `wrote docs/SOURCE_FRESHNESS.json` and looked like
> progress. Same shape as `133 build` reverting `168`'s in-place links: a
> narrower run replacing a wider one, silently.
> Fixed and verified: a filtered or `files`-only run now writes
> `SOURCE_FRESHNESS.partial.json` and leaves the full measurement alone, and the
> snapshot **merges** rather than replaces, so a partial run updates only what it
> measured. **A partial run must never replace a full one** — and a monitoring
> tool that can destroy its own baseline is worse than no monitoring, because
> the loss is invisible until the next diff comes back empty.

---

# PART 5 — THE 2026-08-26 REFRESH, MEASURED BEFORE AND AFTER

*Executed the same evening this document was written, against the three
collections it named as stale for OUR reasons. Every figure below is from
`docs/SOURCE_FRESHNESS.json`, re-measured by script 301 after the work, and the
before-figures are from the same script's run four hours earlier — not from a
run log.*

| collection | last data BEFORE | last data AFTER | rows before → after | verdict |
|---|---|---|---:|---|
| **Federal Register** | 2026-08-05 (21d behind) | **2026-08-26 (0d)** | 156,452 → **156,772** (+320) | **CLOSED** |
| **NAGPRA notices** | 2026-08-03 (23d behind) | **2026-08-24 (2d)** | 6,729 → **6,772** (+43) | **CLOSED** — 2d is the source's own gap since the last notice |
| **CT gaming (monthly)** | 2025-12-31 (238d) | 2025-12-31 (238d) | 68,211 → 68,211 (0) | **NOT OURS — see below** |

## 5.1 Federal Register — incremental, because the two obvious tools are traps

`code/342_pull_federal_register_incremental.py`. 14 nets (1 agency + 13 keyword),
one shard each over **2026-08-06 .. 2026-08-26**, 320 documents, **zero already
held**, and **`records_retrieved == source_reported_total` on every one of the
14 shards**.

Neither existing script could do this:

- **`10_pull_federal_register.py` re-shards 1994..today.** Its cache key is
  `net__key__d0__d1`, so moving `END_DATE` renames the 2026 shard and refetches
  the whole year across all 14 nets to re-learn what we already hold.
- **`11_classify_federal_actions.py` is a FULL REBUILD** of
  `federal_actions.csv` from the raw file, and that table carries two columns 11
  does not write — `pre_2000_flag` and `floor_basis_field`, put there in place
  by `22_apply_temporal_floor.py`. **Running 11 reverts them.** This is the
  133-vs-168 collision (concurrency rule 5), which had already bitten this
  project four times in one day. **11 WAS NOT RUN.** 342 imports 11's own
  `classify()` and 22's own `year_of()` and appends instead.

`action_type` of the 320 new rows: `other` 176 · `rulemaking` 138 ·
`liquor_ordinance` 3 · `consultation` 1 · `federal_acknowledgment` 1 ·
`grant_solicitation` 1.

**THE COMPLETENESS CONTRACT, and why it is not optional here.** The next
incremental run derives its start date from `max(publication_date)` in the file.
So a partial window merged forward would advance that maximum past documents
never retrieved, and the gap would be **permanent and invisible** — defect class
4 with no `done` flag to inspect. 342 therefore merges **only** if every net
returned and every shard's retrieved count equals the `count` the API itself
reported; otherwise the fetched shards stay on disk as cache, the CSVs are not
touched, and the run is recorded `INCOMPLETE`. This run recorded `COMPLETE`.

## 5.2 NAGPRA — rode the same request stream, exactly as this document predicted

`77_build_nagpra_dataset.py fetch` then `build`. Universe 6,729 → **6,774**
notices; 43 fetched, **2 returned HTTP 404** (`96-9758-2`, `97-18431-2` — 1996
and 1997 documents with no plain-text rendition, a fact about those objects,
recorded not retried), so the built table is **6,772**. Bridge rows 51,521.

**A defect fixed to get there.** `77`'s `claim_host()` read `prev["pid"] > 0`
alone and treated any lock naming a pid as held. A lock records its holder's pid
forever — a poller that releases correctly leaves `active: false` and a
`released` stamp behind a pid that is simply history. So 77 could never claim a
host any well-behaved poller had used: it queued itself behind a lock 342 had
released **nine seconds earlier** and exited having fetched nothing. Now held
means `active` **and** no `released` stamp. **A false "host is busy" stops work
that would have succeeded**, which PULL_DISCIPLINE already records for the
mirror-image case.

> ⚠ **THE 2024 SURGE IS A REGIME CHANGE, NOT A FINDING.** The revised
> regulations at **43 CFR 10 took effect 2024-01-12**: the notice trigger became
> unconditional (*"for all human remains … in the inventory"*), the
> culturally-unidentifiable section was deleted, and **43 CFR 10.10(d)(3) sets a
> 2029-01-10 deadline** that is compressing a decades-old backlog into a
> five-year window. Notices per year go 244 (2022) → 496 (2023) → 707 (2024) →
> 900 (2025). **That is BOUNDED, not a trend, and it must fall after 2029.**
> Already documented at `docs/ASSUMPTIONS_AND_LIMITATIONS.md` (`NAGPRA_2024_RULE`)
> and in `series_breaks.csv`; do not re-derive it, and never publish the rise as
> institutional behaviour.

> ⚠ **`mni_total_stated` MUST NEVER BE SUMMED.** Those are counts of human
> beings. Note that **`77`'s own build log prints a sum** — *"total individuals,
> summed over notices that state one: 158,327"*. That line is not a licence:
> it is a diagnostic in a run log, it is not a column in any shipped table, and
> nothing downstream may reproduce it.

## 5.3 CT gaming — the diagnosis in this document was wrong, and the fix is free

`code/343_refresh_ct_gaming_monthly.py`, two bounded requests behind the
`data.ct.gov` lock:

```
$select=count(1)                     -> 200   748 rows reported
$limit=50000&$order=date             -> 200   748 rows retrieved
source span                                   1993-01-31 .. 2025-12-31
casino-months at the source Cedar does not hold:   0
```

**`gaming_facility_metrics.csv` was not touched, because there was nothing to
add.** Cedar already holds all 747 casino-months (× 4 measures = 2,988 rows,
plus the `Mohegan Sun Prior Period Adj.` row excluded and named), landed earlier
the same day by `159_extend_gaming_metrics.py`.

So **the 238-day gap is the SOURCE's**: CT DCP has published no month after
2025-12-31. Section 3.1's *"currently 8 months behind; this is the cheapest win
in the file"* is corrected above.

> **The rule this earns, and it is the mirror of one already in this document.**
> §1.1 says *"do not diagnose a source from a stale local file."* The mirror is
> equally cheap to get wrong: **do not diagnose OUR lag from a cached copy of
> the source either.** The cadence audit read "our file stops at 2025-12, CT
> publishes monthly, therefore we are eight months behind" — every clause true,
> the conclusion false, because nobody asked the endpoint. Whose lag it is
> changes the remedy completely: there is no pull to run, and the collection is
> current with its source. `payout` and `hold` stay withheld on the
> already-recorded unit break (`91.45` in 1993-01 vs `0.912` in 2025-12); that
> finding was inherited from 159, not re-derived.

## 5.4 What the diff measured, and what is now one refresh behind

Script 301's snapshot diff, the whole point of running it after rather than
asserting an improvement:

| collection | oldest period that moved | detail |
|---|---|---|
| `federal_register` | **2026-08** | 82 → 402 rows |
| `nagpra` | **2026-08** | 18 → 61 rows |
| every other collection | — | 0 rows moved |

**Nothing reached back past the current month.** For a 21-day incremental that
is the expected shape and it is now measured rather than assumed; a longer gap
would be needed to size any genuine retroactive reach for these two.

**NAMED, NOT MINE — downstream tables derived from `federal_actions.csv` are now
one refresh behind it.** The largest is `fr_content_classification.csv` at
156,452 rows against the parent's 156,772. Its writer,
`78_content_analysis.py`, is a single-writer full rebuild **that also rebuilds
five lobbying tables** (`lobbying_issue_families_filing.csv`,
`lobbying_issue_family_year.csv`, `lobbying_disclosure_verbosity_year.csv`,
`lobbying_target_entities.csv`, `agency_attention_vs_advocacy*.csv`), and a
lobbying-registrant agent was live on 2026-08-26. **Run it when no lobbying
build is running, not before.** The same applies to every other consumer of the
parent corpus — `130` (Section 106), `76` (recognition history), `98` (OIRA RIN
join), `133` (FERC seeds), `136` (FOIA index): each is a separate owner's build
and none of them was run here.
