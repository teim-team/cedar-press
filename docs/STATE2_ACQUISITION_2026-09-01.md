# The nine "published, not pulled" sources — what each one actually was

*Written 2026-09-01 by workstream `pull`. Every number here was measured on the
day, and the command that produced it is named beside it. Nothing on this page
is cited from another document without being re-measured.*

The mandate: `docs/REFRESH_CADENCE.md` PART 0 put **9 sources in state ②
PUBLISHED AND NOT PULLED** and **1 in state ③ PULLED, NOT PROMOTED**. Pull the
nine, promote the one, and report the state-2 count before and after.

```
py -3 code/630_refresh_cadence.py     BEFORE          AFTER
  CURRENT                                14             16
  ① source has not published              7              7
  ② PUBLISHED, NOT PULLED                 9              7
  ③ PULLED, NOT PROMOTED                  1              1
  closed by design                        5              5
  ❓ source edge not established          19             19
```

**Two sources moved out of state 2 by measurement, not by assertion** — `lda`
and `mi_mgcb`. Four more had real data pulled and promoted without the label
moving, and the reason is worth more than the label: **five of the nine are
pinned to state 2 by a hard-coded `state_hint=S2` in `630`, and two more are
misclassified by a one-line bug**. The count is not the whole answer, so the
per-source table below is.

---

## What each of the nine turned out to be

| # | source | what it actually was | rows pulled | promoted | new `cedar_holds_through` |
|---|---|---|---:|---|---|
| 1 | `lda` | **a real 28-day gap** | 1,520 filings raw / 29 matched | yes | 2026-08-04T15:47 → **2026-09-01T20:50** ✅ CURRENT |
| 2 | `mi_mgcb` | **a real 1-month gap** | 105 observations | yes | 2026-06-30 → **2026-07-31** ✅ CURRENT |
| 3 | `fr_consultation` | **already current** — a classifier bug | 0 | n/a | 2026-08-18, and the source has published nothing since |
| 4 | `fr_ex_parte` | **already current** — same bug | 0 | n/a | 2026-08-31, and no ex parte notice published 2026-09-01 |
| 5 | `irs990_schedc` | **half state 3, half a much bigger state 2** | 7,271+ returns and counting | in progress | fetch backlog under 99's own selection is CLOSED |
| 6 | `foia_logs` | **a client bug, not an agency refusal** | 10,621 FOIA requests | yes | 3 agencies → **4**; `foia_request_index` 9,481 → **20,102** |
| 7 | `sec_edgar` | **genuinely never swept** | 16,964 hits / 2,557 accessions | to `review/`, by doctrine | window swept 2017-05-22 → 2026-09-01, 18 shards, 0 incomplete |
| 8 | `regulations_gov` | **an 8-hour entity sweep, running** | 51 → 166+ of 1,712 entities | continuous | entity coverage, not a date |
| 9 | `congressional_correspondence` | **no source publishes it** — see below | 0 | n/a | 2026-01-27, and that is a SORN date |
| ③ | `labor_form5500_osha` | **promoted on 2026-08-26** — a detector bug | 0 | already done | re-running the merge would have DAMAGED the table |

---

## The four things that were not what the table said

### 1. `_event_driven` in `630` reads the wrong key, and it costs two sources

`630` already contains the correct guard. Its comment is exactly right:

> *"An EVENT-DRIVEN SOURCE CANNOT BE SCORED AGAINST A CALENDAR EDGE… it
> produced the loudest false alarm of 2026-09-01: `fr_consultation` was
> reported as the most overdue source in Cedar at 104 days."*

```python
EVENT_DRIVEN = ("fr_consultation", "nagpra_notices", "nagpra", "fr_ex_parte",
                "section_106", "admin_appeal", "ibia", "ibla")

if _event_driven(str(entry.get("source") or entry.get("id")
                     or entry.get("name") or "")):
```

**The keys are `source_id` values and the lookup reads `source`.** Every
registry entry sets both, `source` is always truthy, so `_event_driven` is
handed the human label:

| `source_id` (what the keys match) | `source` (what is actually tested) | fires? |
|---|---|---|
| `fr_consultation` | "Tribal consultation notices (Federal Register)" | **no** |
| `fr_ex_parte` | "Federal Register ex parte notices, all agencies" | **no** |
| `section_106` | "Section 106 / NHPA consultation notices…" | **no** — the key has an underscore, the label a space |
| `nagpra_notices` | "NAGPRA notices (Federal Register)" | yes, by accident — "nagpra" appears in the label |

So the guard fires for exactly one of the four it was written for, and the one
it fires for is the one it matches by coincidence. `fr_consultation` and
`fr_ex_parte` are still reported as ② on today's run.

**The one-line fix, for whoever owns `630`:** test `source_id` first —
`entry.get("source_id") or entry.get("source") or …`. This workstream does not
edit `630`.

**And the underlying claim was re-measured, not assumed.** `code/342` merged the
Federal Register corpus to **2026-09-01** (156,772 → 156,897 documents) and
`code/751 consultation` was re-run over that corpus on the same day:

```
FR corpus: 156,897 documents (newest 2026-09-01)
fr_consultation_notices.csv   485 ->   485 rows, 11 -> 11 cols
```

**485 in, 485 out, newest still 2026-08-18.** A full rebuild against a corpus
that reaches 2026-09-01 produced no notice after 2026-08-18, which is what
"the source has not published" means. `fr_ex_parte` is the same shape: `154`
ran at 22:09, eight minutes after the merge, and its edge is 2026-08-31.

### 2. `backlog_labor_staged` guesses a filename, and the state-③ row is a phantom

`630`'s state-3 detector pairs each `*_staged.csv` with a clean file of the
same name minus `_staged`:

```python
pairs = [("gaming_employment_form5500_staged.csv",
          "gaming_employment_form5500.csv"), ...]
```

`gaming_employment_form5500.csv` does not exist and never did. **The merge
target is `gaming_employment_observations.csv`**, so `clean_rows` is 0 and all
2,548 staged rows read as unpromoted.

They were promoted on 2026-08-26. `logs/158_merge_2026-08-26.log`:

```
target holds 769 rows
  form5500:   2,046 new rows      osha_tribe:  485 new rows
MERGED: 769 + 2,531 = 3,300 rows (0 already present, skipped)
```

The live table is **3,421 rows / 63 columns**. Both "blocking owner rulings"
were made the same day in §10 of `docs/LABOR_SOURCES_FOR_GAMING_2026-08-26.md`,
and a third — that the table has no single grain — on 2026-09-01 in
`code/584`. `refresh_command` says the merge is "BLOCKED ON TWO OWNER RULINGS";
`158`'s only gate is a 30-minute concurrency check, which passes today.

**Running it would have damaged the table.** Measured before deciding:

* **90 Form 5500 rows** absent from the target are absent *on purpose* —
  `code/262` withdrew them as `NOT_NATIVE` (Las Vegas Paiute capturing Vegas
  commercial casinos; Prairie Band capturing Prairie Meadows, Prairie Wind and
  Prairie Knights; a BIE school "owning" a casino) and moved them to
  `review/form5500_gaming_not_native_2026-08-26.csv`.
* **16 OSHA rows** have ids not in the target and are all already present under
  different ids. `EMP-OSHATRIBE-*` is **positional**, so `157`'s re-run
  renumbered them; `code/265` says in its docstring *"Do not re-run 158 against
  a re-run 157."*

**This is the whole value of the ②/③ distinction, inverted.** The table's
warning against re-downloading something already on disk applies just as hard
to re-merging something already promoted, and here the damage would have been
worse than a wasted request: 90 rows this project spent an adjudication
removing.

### 3. HHS was never refusing Cedar — `urllib` was being refused

`code/136` recorded HHS, USDA and DOT as `NOT_CHECKED` on 2026-08-12 because
every path answered **HTTP 403 to a full browser header set**, and its build log
is careful about why that is not `NOT_FOUND`:

> *"recording them as NOT_FOUND would have manufactured a coverage claim out of
> a block."*

Right call, incomplete evidence. `docs/ACCESS_TECHNIQUES.md` §9 already records
the discriminator — *"`urllib` with a browser UA still drew 403 on 9 of 10;
`curl --compressed` with the full navigation header set drew 200 on 10 of 10.
The discriminator is the header SHAPE"* — and `136` fetches through `code/96`'s
`urllib` helper. Re-probed today, same UA, same header set:

| URL | urllib | curl |
|---|---|---|
| `www.hhs.gov/foia/index.html` | **403** | **200** |
| `www.usace.army.mil/Resources/FOIA/` | **403** | **200** |
| `www.michigan.gov/robots.txt` | **403** | (n/a — the media path 200s) |

HHS then leads to `…/foia/electronic-reading-room/foia-logs/index.html`, a page
`136`'s seed list never carried, publishing **seven annual FOIA logs as .xlsx**
— the format `136`'s own generic parser reads. **10,621 requests, FY2017–FY2023,
139 of them native-related**, parsed with `136.parse_xlsx_log` + `136.enrich`
and **appended**: 9,481 → 20,102 rows, 46 → 46 columns.

`136`'s `build` and `quality` stages were NOT run. Both rewrite that table from
a 28-name `FOIA_FIELDS` against a live 46-column file and would drop `cedar_uid`
and the fourteen entity-link and withdrawal columns `168` wrote.

**This is the same lesson as the `robots.txt` one in `PULL_DISCIPLINE.md`, in a
new place: a check that fails closed for a reason that is about the CLIENT gets
recorded as a fact about the HOST.** Three agencies were written off on it.

### 4. The `?rev=` token on `michigan.gov` was serving a stale workbook

`code/119` pins `Internet-Gaming---2026.xlsx?rev=ce2ca758…`. The regulator's own
page today links `?rev=ff226c04…`, and the object on disk (64,561 B, md5
`5a6005d5…`) is not the object being served (66,385 B, md5 `ba0b38d2…`). This is
the `?wpdmdl=` trap from `AGENTS.md` — the request stays green forever and
quietly returns last month's file. **`code/860` re-reads the rev from the index
page on every run and md5s every object**, and it also found that `119`'s
`MI_FILES` lists 2023, 2024 and 2026 and **not 2025**.

---

## The five sources pinned to ② by hand

These carry `state_hint=S2` in `630` and cannot leave state 2 by any pull:

| source | line | what the pin actually means |
|---|---:|---|
| `regulations_gov` | 323 | ENTITY coverage: 51 of 1,712 spine names swept |
| `foia_logs` | 429 | AGENCY coverage: 3 of ~100 agencies |
| `irs990_schedc` | 450 | fetch backlog against the full IRS index |
| `congressional_correspondence` | 592 | source edge not establishable |
| `sec_edgar` | 632 | reachable, never swept past 2017 |

**Every one of them is a coverage statement, not a date.** They are correct as
warnings and they are not answerable by "is Cedar behind the source's calendar
edge?" — which is the only question the derivation can ask. Four of the five had
real acquisition today; none of them will show it in the state column, and that
is a property of the instrument, not of the work.

---

## What was pulled, precisely

### `lda` — the full universe of the window, not a keyword sweep

`code/860_state2_acquisition.py lda`

The registry says *"key on `dt_posted >= last_pull`, NEVER on filing_year +
filing_period."* Followed. And the filter was **proved before it was trusted**,
because an unknown parameter on this host returns 200 and the full count:

```
no filter                    HTTP 200  count=1,976,576
bogus param                  HTTP 200  count=1,976,576   <- silently ignored
posted>=2026-08-04T00:00:00  HTTP 200  count=1,527       <- honoured
```

1,527 advertised, **1,527 retrieved over 62 pages with 62 distinct page md5s**,
1,520 new after dedupe on `filing_uuid`. Sanity: the same window a year earlier
returns 1,858, so 1,527 is an August, not a truncation.

This replaces the 216-keyword sweep with **the complete LDA population for the
window**, filtered locally — the type-leg-free selection `PULL_DISCIPLINE.md`'s
selection doctrine asks for. 29 of 1,520 matched a Cedar entity (1.9%), which is
what a full-universe window should look like.

`05_match_filings_v2.py` was **not** run: it writes the clean table in `"w"` mode
with 31 columns against a live 40-column file. Its index builders and
`match_client` were imported and applied to the new filings only, and the rows
appended. Then `65` (0 withdrawals) and `351` (panel 4,997 → 5,001 rows,
$680,041,390 → $680,561,640) — and **`351` writes the panel from a 13-name
`PANEL_FIELDS` against a 14-column file, so `cedar_uid` was restored afterwards
using `503`'s own `register_map()`.** That is the sixth column-drop of the day.

### `mi_mgcb` — 105 observations, July 2026

`code/860 … mgcb` then `mgcb-promote`. `119`'s own `Builder.build_michigan()`
against the refreshed workbooks; `119` itself was not run, because its `emit()`
writes 27 columns against a live 34-column table and would also re-fetch
Connecticut, Arizona and eleven loyalty hosts for a Michigan month.
`digital_gaming_revenue.csv` 10,661 → 10,766.

### `irs990_schedc` — two different backlogs wearing one number

The registry's `refresh_command` is `code/99 --steps irs-xml`. Run: **its queue
was 270 objects and every one came back `indexed_but_absent_from_archives`.**
15 archives opened, 51 range reads, 0 extracted. **Under 99's own selection the
fetch backlog is closed, and that is a real result.**

But `nonprofit_schedule_c_coverage.csv` reports `not_downloaded = 25,348`
against all 32,218 index rows, and the two numbers count different populations:
`step_irs_xml` fetches priority 1 (returns already in `np_financials`) plus
priority 2 (**the latest return per remaining EIN**). The difference is every
*prior year* of every organisation — a time series, and lobbying is a
longitudinal question.

`code/860 … schedc-full` fetches the wider queue over the same route: 81
archives, HTTP range reads, `99`'s own `Fetcher` / `HttpRangeFile` /
`zip_manifest` / `_xml_fetch_log.csv`, nothing in `99` edited.
**24,573 queued; XML on disk 6,870 → 14,141 and rising at the time of writing.**
Six archives are DEFLATE64 and report `undecodable` rather than silently
dropping (`--steps irs-deflate64` with 7-Zip is the documented recovery).

### `sec_edgar` — swept, and it is a candidate index, not deals

`code/860 … sec`. `hits.total.value` saturates at 10,000 with
`relation: "gte"` (`API_MANUALS_AND_QUIRKS` §5.3), so every window that reports
`gte` is split before it is paged: `"Tribal Gaming Authority"` saturated over
the whole window and was split by year. The date filter was proved first —
`"Tribal Chairman"` returns 100 over 2001→2026 and 9 over 2017-05-22→2026-09-01.

**18 shards, 0 incomplete. 16,964 hits, 2,557 distinct accessions, 2,520 of them
absent from `148`'s cache, 171 distinct page md5s.** Landed at
`review/sec_edgar_post2017_candidates_2026-09-01.csv` with
`record_scope = SEARCH_HIT_CANDIDATE_NOT_A_DEAL` on every row.

**Nothing was written to `data/clean`, deliberately.** A deal row asserts a
dated, quantified transaction with a named Native principal; that is an
adjudication over a read filing. `PULL_DISCIPLINE.md`: *"The sweep does not
attribute anything. It produces candidates for `review/`."* The known
false-positive classes are visible in the top filers and were predicted by
`DEALS_SEC_2010_2017_BUILD_LOG.md` — 9,594 `NPORT-P` fund-holdings rows, and
Ark Restaurants, whose dividend boilerplate carries "operated by the Seminole
Indian Tribe" in every filing.

### `congressional_correspondence` — the absence is the finding, and it is already recorded

`congressional_correspondence_log.csv` holds **0 data rows**, and `136`'s build
log says why: *"no agency in scope publishes the log itself, and a row is only
written where a retrieved record names a congressional office as a party."*
Cedar's edge of 2026-01-27 is the newest of **eight Privacy Act SORNs** — the
date an agency last *described* its correspondence system, not the date of a
letter. There is no index of member letter releases to probe, and 249 rows of
`congressional_correspondence_systems.csv` are FOIA requests *asking* bureaux
for their congressional-letter logs. **No pull was made because no source
publishes the object.** That boundary was already documented; this run confirms
it rather than re-discovering it.

---

## Things the next workstream should pick up

These are named because they are cheap and because nobody owns them today.

1. **`630`, one line:** `_event_driven` should test `source_id`. Two sources
   are misreported until it does, and `section_106` will misreport the moment
   it goes behind.
2. **`630`, `backlog_labor_staged`:** compare against
   `gaming_employment_observations.csv` filtered on `built_by_script`, not
   against a guessed filename. The state-③ row is a phantom.
3. **`docs/GAMING_EMPLOYMENT_LOG.md` lines 5 and 40 still assert 769 rows**;
   the table is 3,421. `docs/GRAIN_AUDIT.md:299` says 3,246. §4 of the labor
   doc predicted this number would move and said to back up before it did.
4. **20 BIA/DOI FOIA-log PDFs are on disk and unparsed** — refused because the
   column geometry could not be solved, which is the right refusal. **22 HUD
   quarterly log PDFs were discovered and never fetched.** Both are cheaper
   than any new agency.
5. **USDA, DOT, EPA, DOE, USACE and Commerce still have no working log URL.**
   Re-probed today through `curl`: EPA `/foia` 200 but its log links are gone,
   DOE publishes annual reports and no logs, USDA `/foia` 404s, Commerce
   `/opog/foia` 403s even to `curl`, USACE 200s and points at the Army-wide
   reading room. **Only HHS was a client-side false negative; the rest are
   real.** That is a documented boundary, not a gap.
6. **`code/119`'s `MI_FILES` pins a stale `?rev=` and omits 2025.** The 2025
   workbooks are now on disk; the list is not this workstream's to edit.
