# Earmarks + 990 Schedule C — build log, 2026-08-07

Build script: `code/99_build_earmarks_and_schedc.py`
(one script, `--steps probe,irs-index,irs-xml,irs-deflate64,schedc,earmarks-pull,earmarks-stage,earmarks,crosscheck,codebook,report`)

Spec: `docs/plans/SPEC_v2_ENTITY_EVENT_INTELLIGENCE.md` §9.5, §9.3 ·
Reconciliation: `docs/LOBBYING_EXPANSION_RECONCILIATION.md` (item 4 and the
Schedule C row of the "already built" table)

Two layers that sit on **opposite ends** of the influence chain and are never
joined into a causal claim:

| Layer | Side | Output |
|---|---|---|
| Community Project Funding / Congressionally Directed Spending | the **outcome** side — a named member of Congress, a named recipient, a named amount | `data/clean/earmarks.csv` (1,002 rows) |
| 990 Schedule C | the **self-reported** side — what an organisation says it spent influencing legislation | 36 appended columns on `data/clean/np_financials.csv` |

**Nothing in this build asserts that an earmark resulted from lobbying.** Both
events are recorded with dates and the reader draws the line. `resulted_from`
belongs in `entity_relationships.csv`, which another agent holds, and is
reserved for cases where a document says so.

---

## LAYER 2 FIRST, because it is the one the spec mis-describes

The reconciliation memo lists Schedule C as *"partly built — `lobbying_expenditure`
already in `np_financials.csv` (8,507 rows), with `lobbying_field_basis`
recording where it came from."*

Measured before this build ran:

```
lobbying_expenditure non-null ............................ 0  of 8,507
lobbying_field_basis = not_exposed_by_api ............ 8,274
lobbying_field_basis = 990pf_infleg_indicator_only ..... 233
```

**The column existed and was empty, and it said so.** ProPublica Nonprofit
Explorer API v2 does not expose Schedule C at all — its `filings_with_data`
array carries 46 fields and not one of them is a lobbying figure. The previous
build labelled that honestly instead of imputing, which is why the gap was
findable. The fix was never another call to the same host.

### The source, and how it had to be reached

| Leg | URL | Result |
|---|---|---|
| index | `https://apps.irs.gov/pub/epostcard/990/xml/{Y}/index_{Y}.csv` | 200 for **2017–2026 only**; 2009–2016 404 at both apps.irs.gov and the S3 bucket root |
| per-return | `https://s3.amazonaws.com/irs-form-990/{OBJECT_ID}_public.xml` | **404 for every object id tested.** The bucket is retired. |
| archives | `https://apps.irs.gov/pub/epostcard/990/xml/{Y}/*.zip` | 200; 81 archives, ~30 GB in total |

The per-return objects are gone, so the returns exist only inside
multi-gigabyte ZIPs. We need about 7,000 specific returns out of roughly six
million; downloading 30 GB to keep 0.1% of it is the wrong trade.

**apps.irs.gov answers `Accept-Ranges: bytes` and returns 206.** So
`zipfile.ZipFile` is pointed at an HTTP-range-backed file object
(`HttpRangeFile`): it reads the end-of-central-directory record, then the
central directory, then only the local header and compressed bytes of each
member wanted. A 123 MB archive with 21,513 members costs **2 MB of reads** to
enumerate. Measured across all 81 archives: roughly **1.3 GB read instead of
30 GB**, and no archive was ever stored.

Index files were streamed and filtered in flight — 5.5 million index rows read,
32,218 kept, nothing written to disk but the 32,218.

The archive list is **read from the IRS's own download page**, not
reconstructed. Guessing does not work: 2017–2020 use
`download990xml_{Y}_{n}.zip` and 2021–2026 use `{Y}_TEOS_XML_{NN}{A..D}.zip`.
The 2017 and 2018 archives are no longer linked on that page but still serve;
each candidate was HEAD-checked for a real 200 with a Content-Length before
being added and carries `basis = probe_verified_http_200_not_page_listed` in
`_zip_manifest.csv`.

### DEFLATE64 — a real loss, then mostly recovered

Six of the 81 archives are written with compression method 9. CPython's
`zipfile` raises `NotImplementedError`, and the pure-Python replacement needs a
C toolchain this machine does not have. **1,282 returns were lost that way, 95
of them rows of `np_financials`.**

Those six archives were then downloaded whole and opened with the system 7-Zip,
which does implement DEFLATE64, **one at a time with each deleted before the
next began** — peak disk about 500 MB, not the 2.8 GB the six occupy together.
**1,585 returns recovered.**

### What was written

**36 columns appended to `np_financials.csv`. Row count unchanged at 8,507.
Independently verified against the pre-build backup: 33 original columns
preserved in order, 0 pre-existing cells changed.** The step is idempotent — a
re-run drops the columns it owns and rebuilds them, so its own output is never
mistaken for source data.

| Group | Columns |
|---|---|
| filing regime (the caveat) | `filing_regime`, `schedc_expected`, `schedc_basis` |
| provenance | `schedc_source_url`, `schedc_object_id`, `schedc_present` |
| Part II-A, 501(h) electing | `schedc_501h_election`, `schedc_501h_basis`, `schedc_total_lobbying`, `schedc_direct_lobbying`, `schedc_grassroots_lobbying`, `schedc_lobbying_nontaxable`, `schedc_grassroots_nontaxable`, `schedc_exempt_purpose_expend` |
| Part II-B, non-electing | `schedc_nonelecting_total`, `schedc_used_volunteers`, `schedc_used_paid_staff`, `schedc_used_media`, `schedc_used_mailings`, `schedc_used_publications`, `schedc_used_grants`, `schedc_used_direct_contact`, `schedc_used_rallies`, `schedc_used_other` |
| Part I, political | `schedc_political_expenditure`, `schedc_527_amount` |
| Part III, dues | `schedc_dues_lobbying_political`, `schedc_dues_received` |
| core form | `form990_lobbying_activities_ind`, `form990_political_activity_ind`, `form990_part9_lobbying_fees`, `form990pf_influence_legislation_ind`, `form990pf_legislative_political_ind` |
| consolidated | `schedc_lobbying_usd`, `schedc_lobbying_basis`, `schedc_built_date` |

### THE CAVEAT IS A COLUMN, NOT A FOOTNOTE

`schedc_expected` says, per row, whether a Schedule C could have existed at all.
Any denominator built without it is wrong by construction.

```
rows total ................................. 8,507
990-N filers — no schedule EXISTS .......... 1,592   excluded, NOT zeroed
no filing requirement ...................... 518     excluded, NOT zeroed
rows where a Schedule C COULD exist ........ 6,397
```

At the universe level the same rule bites harder: of `np_orgs.csv`'s **12,764
organisations, 6,453 are 990-N** (BMF `FILING_REQ_CD = 02`) and another 468
have no filing requirement. **5,792 could have a Schedule C**; those are the
only EINs the index was filtered against. A 990-N filer reports gross receipts
under $50,000 and nothing else — zero lobbying expenditure there is the filing
regime, not a finding, and none of those organisations was counted as a zero.

### Fill, before and after

| | before | after |
|---|---:|---:|
| `lobbying_expenditure` populated | **0** | 0 (untouched — the old column is left exactly as it was) |
| returns retrieved and read | 0 | **2,195** (34.3% of the 6,397 possible) |
| rows where a Schedule C was filed | 0 | **93** |
| rows carrying a lobbying expenditure figure | 0 | **43** |
| rows carrying Part IX line 11d lobbying fees | 0 | **405** |
| rows where the core-form lobbying/political trigger is answered | 0 | **2,170** |
| distinct EINs with any Schedule C observation | 0 | **377 of 662** |

**Absent is not zero, and the basis column says which absence it is:**

| `schedc_basis` | rows |
|---|---:|
| `outside_efile_index_coverage_submission_years_2017_2026` | 3,289 |
| `irs_efile_xml_no_schedule_c_filed` | 2,102 |
| `990N_filer_no_schedule_exists` | 1,592 |
| `no_efile_return_indexed_for_period` | 652 |
| `bmf_filing_not_required` | 518 |
| `efile_return_indexed_not_retrieved` | 261 |
| `irs_efile_xml_schedule_c` | 93 |

The largest bucket is the honest one: **3,289 rows are tax years before the
e-file index begins.** The IRS publishes no machine-readable return for them at
any URL, so the floor is stated per row rather than smoothed into a zero.

### Three reporting regimes, ranked and never added

Schedule C is not one measurement:

- **Part II-A — 501(h) electing.** Grassroots and direct reported separately
  against a statutory ceiling. Column (a) is the filing organisation; column
  (b) is an affiliated group, a different legal person's money, and only (a) is
  read.
- **Part II-B — non-electing.** Activity checkboxes plus one total. No
  grassroots/direct split exists, so those cells are blank *because the form has
  no such line*, not because the parse failed.
- **Part III** — 501(c)(4)/(5)/(6) dues and proxy tax.

`schedc_lobbying_usd` takes the first available in that order and
`schedc_lobbying_basis` names which. **`form990_part9_lobbying_fees` is
deliberately not a fallback** — Part IX line 11d counts fees paid to *outside*
lobbyists while Schedule C counts the organisation's *own* expenditure. They
overlap without being the same quantity; letting one stand in for the other
produces a column whose meaning changes row to row.

**The 501(h) election is derived and says so.** The election is made on Form
5768 and Schedule C carries no element for it. What the XML shows is which part
the filer completed, and only an electing organisation completes Part II-A.
`schedc_501h_basis` records that derivation instead of implying a checkbox was
read. Observed across the 93 filed schedules: **24 rows electing, 34
non-electing**, the remainder not determinable from the return.

### One methodological note worth keeping

The first draft of the parser used **invented element names** —
`PaidStaffOrMgmtInd`, `LobbyingExpendituresGrp`, `Organization501hElectionInd`
— all plausible, all wrong. The real schema says `PaidStaffOrManagementInd`,
`TotalLobbyingExpendGrp`, and carries no election element at all. It would have
produced a silently empty column that looked like a finding about Native
nonprofits not lobbying. The parser was rewritten against a **tag inventory
taken across 2,647 retrieved returns**. Do not write an XML parser for a
federal schema from memory.

---

## LAYER 1 — Community Project Funding / earmarks

### Sources, all verified by fetch

| Family | Source | Coverage |
|---|---|---|
| House requests | one consolidated XLSX per fiscal year, appropriations.house.gov and democrats-appropriations.house.gov | FY2022–FY2026, 5 files, 23,517 request rows |
| Senate requests | `POST https://www.appropriations.senate.gov/cfc_extensions/data/cds_requests.cfc` — the JSON endpoint behind the committee's DataTables grid | FY2023–FY2027, **83,041 records** pulled complete |
| Enacted amounts | per-subcommittee joint explanatory statement PDFs | FY2023, FY2024, FY2026 (partial) |

`_SOURCE_MANIFEST.csv` in `data/raw/external/earmarks/` records 92 retrievals
with the HTTP status of each. An earlier pass recorded fifty failures that were
worth reading rather than believing: the committee's landing pages emit
**protocol-relative** hrefs (`//host/path`), and a naive "starts with / so
prepend the root" produced
`https://appropriations.house.gov//appropriations.house.gov/...` and fifty HTTP
404s that looked exactly like missing documents. The files were there all
along.

**Senate method → fiscal year mapping** (confirmed against the
`certification_letter` paths each row carries): `getCDSTable23` → FY2023,
`getCDSTable24` → FY2024, **unsuffixed `getCDSTable` → FY2025**,
`getCDSTable26` → FY2026, `getCDSTable27` → FY2027. `getCDSTable25` does not
exist; `getCDSTable22` does not exist. **Senate FY2022 requests are not
retrievable** — the committee's `/download/<slug>` endpoints return HTML site
chrome, and the working `/imo/media/doc/<slug>.pdf` pattern returns **410 Gone**
for every FY22 candidate. A 410 rather than a 404 says the files were removed
deliberately. That is a coverage gap, recorded, not filled by guesswork.

### The three things this layer refuses to conflate

**1. Requested is not enacted.** They are separate columns and neither is ever
copied into the other. `amount_requested` is populated on House and Senate
request rows; `amount_enacted` on rows from the joint tables.

**2. A joint table is not a House-bill-stage table.** The joint explanatory
statement carries a Senate requestor column and an `Origination` column; the
House-stage table carries `House Amount` and `House Requestor(s)` only. A
House-bill amount is neither what a member asked for nor what became law.
**30 House-stage tables were read, counted and excluded**, and the test is on
the document's own header text, not on its filename — FY2026 publishes
`fy26-interior-1.7.pdf` (joint) and
`fy26-interior,-environment,-and-related-agencies-cpf-table.pdf` (House stage)
side by side, and the filenames give no clue which is which.

Consequences, both of them true rather than convenient:
- **FY2022 contributes no enacted amounts.** The committee published only
  House-stage tables at these URLs.
- **FY2025 contributes no enacted amounts.** The full-year continuing
  resolution carried no community project funding, so no joint table exists to
  parse. `is_enacted = 0` on an FY2025 row means UNESTABLISHED, and the row's
  `confidence` field says so in words, because reading it as "rejected" would
  be a fabricated outcome.

**3. Revisions are not additional projects.** FY2024 Commerce-Justice-Science
alone is published four times (base, `updated-10.31.23`, `updated-3.6.2024`,
`final`). `_latest_revision_per_table` picks one deterministically — prefer
`final`, then the latest embedded revision date, then the longest name — and
logs every file it dropped.

### PDF parsing: coordinates, not lines

These are GPO-typeset PDFs with no ruling lines and wrapping cells. The naive
rule "the amount is the rightmost number on the line" gives a recipient of
*Agency + Account + State + Recipient + Project* glued together, which no
resolver can match and which would publish a recipient name appearing nowhere
in the source. The parser instead reads the table's **own header row**, takes
column x-boundaries from it, and assigns every word to a column.
**62 rows were refused** for having no unambiguous amount or recipient, and
**5 joint tables yielded nothing parsable** (their headers are interleaved
across columns and cannot be read; one FY2026 file is typeset in mirror-reversed
text). Refusals are counted, not filled.

### Request ↔ enacted join

No committee source links a request to its enacted outcome by any identifier.
The join can only be made on (fiscal year, recipient), and is only safe when
**exactly one** request and **exactly one** enacted row share the key. A tribe
with two requests in one year and one enacted line is ambiguous, and assigning
the amount to either request would invent which project was funded.

**4 unique joins made; 3 recipient-years left unjoined as ambiguous.** A joined
enacted row is removed from the standalone set, so no dollar appears twice in
the file. The low yield is itself the finding: the enacted tables print a
recipient cell like *"Pueblo of Tesuque for Wastewater Treat-"* — recipient,
purpose and a hyphenation all in one field — so exact recipient matching almost
never fires. Enacted rows that did not join stay as their own rows with
`chamber = Joint`.

### Containment — six documented failures, and two new ones found here

`resolve_entity` from `code/33_apply_party_rulings.py` is the one resolver.
Every guard below sits **on top of** it; none of them re-implements name
matching. Two of them exist because this build reproduced the defect live:

| Guard | The failure it prevents |
|---|---|
| header match may not cross a forbidden word | **The FY2022 House table has no `Recipient` column.** A substring search for "recipient" matched `Recipient Address`, so every FY2022 recipient name became a postal address, and containment then resolved `2333 Biddle Ave, Wyandotte, MI` → Wyandotte Nation, `1654 West Onondaga Street, Syracuse NY` → Onondaga, `485 Gorman St, Shakopee, MN` → Shakopee Mdewakanton. 31 rows of place-name coincidence carrying real dollars and a named member of Congress. |
| a postal address is not a name | belt and braces on the same failure — address-shaped records are refused before the resolver is asked |
| entity core may not be all generic/trap tokens | **`The NATIVE Project`** (a Spokane urban Indian organisation) reduces to the core `{project}` once structural words are stripped, and matched every request whose title ends in "Project" — ~130 rows of noise. `Native Health` → `{health}` matched "UH Rural Health Research Center". |
| a record naming a county is never a tribe | Taos County, Seminole County Sheriff's Office, Pueblo County, Indian River County |
| one-token entity core needs a tribal status word in the record | `Camp Navajo` is an Arizona National Guard installation; `Nooksack Indian Tribe` is not |
| one-token entity core may not pick up other identifying words | spine `Arctic Village` (core `{arctic}`) sat inside `Arctic Slope Native Association Ltd.` — a regional health non-profit, different legal person, different place. `slope` is the word that says so. |
| state agreement where both are known | 87 refusals |
| **no containment on a project title** | a title is a sentence, not a name. `Pueblo of Santa Clara` matched "Boys and Girls Club of Santa Clara Valley Restroom Remodel". Only exact, core-equal or alias matches are accepted on titles, which loses real rows and keeps the file true. |

**Tiering.** Tier A requires an exact name match *and* state agreement: 176
rows. Everything else that resolves is **Tier B — name-only, never publishes**:
826 rows. Nothing algorithmic reaches Tier A.

Two further guards were added after hand-scanning every distinct
(recipient → entity) pair in the built file, because reading the output is the
only way these surface:

- **A record that is a different kind of institution is refused** unless it
  carries a tribal status word. `Santa Ana College` (Santa Ana, California) had
  resolved to `Pueblo of Santa Ana` (New Mexico) — and the FY2023 House table
  publishes no district and no address, so the state guard had nothing to fire
  on. The word `college` was the only signal left. The same rule catches `City
  of Santa Clara`, `City of Sault Ste. Marie` and `Santa Clara Valley
  Transportation Authority`.
- **Subordinate and program entities are refused**, which is AGENTS.md's
  148-TDHE failure reappearing in a new dataset. `Crow Creek Housing
  Authority`, `Pascua Yaqui Development Corporation`, `Mille Lacs Corporate
  Ventures` and `Santa Ana Agricultural Enterprises` are separate legal persons
  receiving separate dollars. They go to review so the relationship can be
  recorded without keying the money to the tribe.

What deliberately still resolves at Tier B: a tribe's own **governmental**
units — `Pueblo of Santa Ana Police Department`, `Fort McDowell Yavapai Nation
- Office of the Prosecutor`, `Prairie Island Indian Community Department of
Public Safety`. A department is the government; a corporation is not.

### Screen → resolve → publish or review

The keyword screen is a deliberately wide net over 106,558 disclosed requests;
it catches Indian River County and the Naval Surface Warfare Center Indian Head
Division on purpose. **7,802 candidates** were screened in. Of those,
**1,002 resolved** to a spine entity and are in `earmarks.csv`; **6,796 did
not** and are in `review/earmark_unresolved_2026-08-07.csv` with the reason,
the amount, the member and the verbatim source quote, for a ruling.

Refusal reasons, which are the guards doing their job:

| reason | rows |
|---|---:|
| `no_spine_match` | 5,111 |
| `blank_name` (source publishes no recipient) | 463 |
| `single_token_entity_core_in_longer_record_with_no_tribal_status_word` | 227 |
| `containment_on_generic_or_trap_tokens_only` | 217 |
| `record_names_a_county_not_a_tribe` | 182 |
| `record_is_a_wrapped_table_cell_not_a_name` | 174 |
| `ambiguous_containment` | 140 |
| `single_token_entity_core_but_record_carries_other_identifying_words` | 85 |
| `record_is_a_different_kind_of_institution` | 66 |
| `state_disagreement` | 48 |
| `containment_record_less_specific_than_entity` | 45 |
| `ambiguous_core` | 22 |
| `project_title_containment_refused` | 14 |
| `record_is_a_postal_address_not_a_name` | 2 |

Publishing the misses with a blank `entity_id` would have shipped exactly the
false attribution this project forbids, so the dataset is the resolved set and
the review file carries the rest.

---

## Results

### Earmarks by fiscal year and chamber

| FY | chamber | rows | requested | enacted | is_enacted=1 |
|---|---|---:|---:|---:|---:|
| 2023 | House | 37 | $85,876,559 | — | 0 |
| 2023 | Joint | 2 | — | $2,208,019 | 2 |
| 2023 | Senate | 149 | $495,280,000 | — | 0 |
| 2024 | House | 33 | $140,551,085 | $850,000 | 1 |
| 2024 | Joint | 2 | — | $1,137,195 | 2 |
| 2024 | Senate | 227 | $479,327,000 | — | 0 |
| 2025 | House | 25 | $144,264,104 | — | 0 |
| 2025 | Senate | 178 | $509,978,000 | — | 0 |
| 2026 | House | 18 | $52,486,212 | — | 0 |
| 2026 | Joint | 1 | — | $500,000 | 1 |
| 2026 | Senate | 164 | $406,074,000 | — | 0 |
| 2027 | Senate | 166 | $363,179,000 | — | 0 |
| **total** | | **1,002** | **$2,677,015,960** | **$4,695,214** | **6** |

**These two totals are not comparable and must never be printed as a funding
rate.** They come from different documents covering different fiscal years:
requested spans FY2023–FY2027, enacted exists only for FY2023, FY2024 and part
of FY2026, and only 4 rows carry both. Dividing one by the other would produce
a "0.8% of tribal earmark requests were funded" headline that the data does not
support.

**FY2022 contributes zero rows.** The House FY2022 table has no recipient
column and title-based containment was refused; the Senate FY2022 requests are
410 Gone. Those 448 FY2022 House candidates are all in the review file.

- **224 distinct spine entities** reached, across 12 entity classes: 704 rows
  on federally recognized tribes, 78 federal-level constituency entities, 75
  Alaska Native villages, 46 intertribal organisations, 36 urban Indian
  organisations, 33 tribal colleges, 8 BIE schools, 7 state-recognized tribes,
  6 self-governance consortia, 5 Native CDFIs, 4 ANCSA corporations.
- **118 distinct members of Congress** named as requesters.
- Every one of the 1,002 rows carries a `source_url` and a verbatim
  `source_quote`. **Zero rows have a blank `entity_id`.**

### Schedule C ↔ LDA cross-check

`review/schedc_lda_gaps_2026-08-07.csv`.

11 organisations report lobbying above zero on a Form 990 (9 via Schedule C,
8 via Part IX line 11d). Of those, **2 also appear in the 27,796 LDA filings**
and **9 do not**.

**6 of those 9 were then dropped, and that is the important part of this
result.** `np_orgs.csv` is a candidate funnel, not a roster. The first pass
surfaced *Yavapai Community Hospital Association*, *Pawnee Valley Community
Hospital*, *Wichita Downtown Development Corporation*, *West Yavapai Guidance
Clinic*, *Ascension Living Via Christi Village Ponca City* and *Maricopa County
Community College District Faculty Association* as "Native organisations
lobbying without registering". Every one of them is **already ruled tier X /
`place_name_coincidence`**. Publishing them would have been a false attribution
dressed as a discovery.

**3 candidates remain**, and each carries `native_universe_status` stating that
its classification is `UNRULED` and that the row is a question for review, not
a finding:

| org | state | year | reported | signal | band |
|---|---|---|---:|---|---|
| Kansas Humane Society Of Wichita Inc | KS | 2019 | $15,000 | Schedule C + Part IX | above LDA quarterly threshold — registration-gap candidate |
| La Union Del Pueblo Entero | CA | 2018 | $38,077 | Schedule C + Part IX | above LDA quarterly threshold — registration-gap candidate |
| Western Dakota Regional Water System Inc | SD | 2024 | $5,590 | Part IX only | below LDA registration threshold — plausible |

The caveat travels on every row: **Schedule C uses the IRS definition and
includes state and local legislative activity; LDA covers federal contacts
only.** An organisation whose lobbying happens entirely at a state capitol is
correctly on the 990 and correctly absent from LDA. The file records the
discrepancy and its size and refuses to label it a violation.

---

## Regression check

**Before:** run clean — `no regressions`, 39 metrics recorded.

**After:** one failure, and it is **not from this build**:

```
!! codebook_undocumented_public = 1, must be 0
   12_resources.source_system   generated 2026-08-07
```

`12_resources` is the resource-ledger dataset, owned by a concurrent agent.
The pre-write backup this script took (`codebook_master.csv.bak_2026-08-07_pre99`)
already contained **10** such rows, of which that agent has since filled 9.
This build's own 58 codebook entries all carry descriptions. Verified against
all three same-day backups: **0 rows written by any other agent were lost** by
this script's codebook write.

Everything else improved or held: `codebook_variables` 641 → 1,054.

---

## Files

| Path | What |
|---|---|
| `code/99_build_earmarks_and_schedc.py` | the build |
| `data/clean/earmarks.csv` | 1,002 rows, 22 columns |
| `data/clean/np_financials.csv` | +36 columns, 8,507 rows unchanged |
| `data/clean/np_financials.csv.bak_2026-08-07_pre99` | pre-build state |
| `data/clean/codebook_master.csv` | +58 variable entries (variables only) |
| `review/earmark_unresolved_2026-08-07.csv` | 6,796 screened candidates awaiting a ruling |
| `review/schedc_lda_gaps_2026-08-07.csv` | 3 candidates, each labelled unsettled |
| `data/raw/external/earmarks/` | 5 XLSX, 5 JSON, 76 PDF, `_SOURCE_MANIFEST.csv` (92 retrievals with status) |
| `data/raw/external/irs990_schedc/` | 6,870 return XMLs, `_index_targets.csv` (32,218), `_zip_manifest.csv` (81), `_xml_fetch_log.csv` |
| `logs/99_*.log` | per-step run logs |

## Pull discipline

`logs/_HOSTLOCK_apps.irs.gov.json`, `_HOSTLOCK_appropriations.house.gov.json`
and `_HOSTLOCK_www.appropriations.senate.gov.json` were claimed before any
request and released after. `api.usaspending.gov` was **not touched** — it is
edge-blocking, and its lock is held by the prime-contracting build.
`www.federalregister.gov`, `api.congress.gov`, `api.govinfo.gov`,
`www.reginfo.gov` and `web.archive.org` were held by other agents throughout
and were not touched. No host rate-limited or edge-blocked this build;
`Fetcher` recorded 1,742 successful range reads and zero refusals.

`s3.amazonaws.com` was claimed, found to serve 404 for every IRS object, and
released without further requests.

## Known limits, stated rather than smoothed

1. **Tax years before 2015 have no machine-readable return.** 3,289
   `np_financials` rows sit outside the e-file index window and carry
   `schedc_basis = outside_efile_index_coverage_submission_years_2017_2026`.
2. **261 rows are indexed but not retrieved** — chiefly DEFLATE64 members in
   archives the recovery pass did not reach.
3. **Senate FY2022 requests are gone** (HTTP 410) and FY2022 House requests
   have no recipient column, so FY2022 contributes no published rows.
4. **5 joint enacted tables could not be parsed** (interleaved or
   mirror-reversed headers). Their subcommittees are named in
   `logs/99_earmarks_stage.log`.
5. **826 of 1,002 earmark rows are Tier B** and do not publish. Tier A needs an
   exact name match plus state agreement.
6. Residuals to watch in Tier B, found by hand-scanning the built file and left
   in deliberately: bare `Santa Clara` and bare `Manchester` come from enacted
   PDF cells and are plausible but unconfirmed; `Mille Lacs Corporate Ventures
   (Mille Lacs Band of Ojibwe)` survives only because the parenthetical names
   its owner in evidence, which is the one use of containment AGENTS.md
   allows.

## What would move this furthest next

- **Rule the 6,796 review candidates**, or even the top 200 by dollar. That is
  the single largest recall gain available and it needs no new access.
- **FY2022 House recipients** exist inside the project-title and address
  fields; a hand pass over 448 rows would recover a whole fiscal year.
- **Extend the e-file pull to the full 5,792-EIN Schedule-C-possible
  universe**, not just the latest return per organisation. The machinery is
  built and checkpointed; it is now only a matter of queue length.
