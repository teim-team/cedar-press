# Methodology — Native Federal Subcontracting

**`subcontracting`. `data/clean/subawards.csv`, 87,177 rows.
Unfiltered `subaward_amount` $51,447,159,579.79; the correct total is
$29,468,837,987.91.** [re-measured 2026-09-02T15:50Z]

> **EVERY FIGURE BELOW DATED EARLIER ON 2026-09-02 PREDATES THE 12:09Z FOLD-IN
> AND IS SUPERSEDED.** `121 append` added **10,318 rows** at 12:09Z — the
> FY2023 Q3 and FY2024 Q1–Q4 bulk-download quarters — taking the table
> 76,859 → **87,177**. The money rule moves with it:
>
> ```
> all 87,177 rows                            $51,447,159,579.79   <- never quote this
> countable: duplicate_status == 'primary'
>        AND subaward_exceeds_prime_flag != 'yes'
>        67,583 rows                         $29,468,837,987.91   <- the correct total
> the money rule removes                     $21,978,321,591.88
>    = 42.7% of the unfiltered figure
>    = 74.6% MORE than the correct total
> ```
>
> `duplicate_status` [re-measured]: `primary` **68,249** ·
> `exact_repeat_within_source` **18,082** · `superseded_by_primary_source` 846.
> **State the denominator** — 42.7% and 74.6% are the same difference against
> two different bases, and the older pair (45.3% / 82.9%) is now wrong on both.
>
> FY2024 is no longer empty: **8,839 rows, 8,175 countable, $3,133,280,000**,
> against the 166 / $113,334,471 the "known limits" section still reports. FY2023
> is **5,745 rows / 4,874 countable** and is now Q1–Q3, not Q1–Q2.
> **FY2022 is still 89 countable rows and `fy2022_q1..q4` have never been
> submitted** — see §7.

*Written 2026-09-02. This is the methodology record: what was pulled and from
where, how the rows were made, how entities were attributed, what was decided
and why, what the known limits are, and how often it has to be re-pulled. It is
not the product copy (`docs/datasets/_descriptors.json`) and not the codebook
(`docs/codebooks/`).*

**A note on the figures.** `[measured]` means the figure was re-counted from
the live file with `csv.reader` on 2026-09-02, streaming the whole file.
`[from the record]` means it came from a build log or docstring without
independent measurement. Where a doc and the data disagreed, the measurement
won; the disagreements are listed at the end.

**Readiness: BLOCKED**, with five named blockers — C1 grain unstated on
`subawards.csv`, C2 no validated primary key, C3 10,770 literal duplicates,
C7 double-counting risk, C4 42% of entity-bearing rows keyed. [measured —
`docs/DATASET_READINESS.md`, regenerated 2026-09-02] Every one of those is
explained below, and three of the five are **deliberate**.

---

## The number a buyer must not quote, stated first

```
subawards.csv, all 76,859 rows            $47,301,660,819.78   <- never quote this
countable: duplicate_status == 'primary'
       AND subaward_exceeds_prime_flag != 'yes'
       58,117 rows                        $25,864,997,128.19   <- the correct total
the money rule removes                    $21,436,663,691.59
   = 45.3% of the unfiltered figure
   = 82.9% MORE than the correct total
```

[measured] **State the denominator.** The same difference is 45.3% one way and
82.9% the other, and quoting either without saying which base it uses makes an
honest warning look like an arithmetic error. Cedar's shipped documents have
done exactly that — see the stale-claims list.

**And the corrected total is still not additive with prime contracting.** A
subaward is a slice of a prime award Cedar already publishes. Federal dollars
obligated = primes. Subawards say where those dollars went **next**.

---

## 1. Sources

Three, each keeping its provenance in `source_dataset` [measured]:

| `source_dataset` | rows | $ | what it is |
|---|---:|---:|---|
| `usaspending_fsrs_pull` | 72,159 | $45,698,045,935.75 | the primary source |
| `usaspending_fsrs_name_match` | 2,797 | $435,246,029.37 | the same corpus, reached by the guarded name route |
| `usaspending_fsrs_parent_cluster` | 297 | $104,830,139.60 | the same corpus, reached through a declared parent |
| `highergov_2023_export` | 998 | $669,825,812.00 | frozen, superseded, never deleted |
| `funding_forward_fill` | 608 | $393,712,903.06 | a by-product of the assistance pull |

**The primary route** is `POST https://api.usaspending.gov/api/v2/bulk_download/awards/`
with `filters.sub_award_types = ["procurement","grant"]` and
`date_type = "action_date"` — verified on 2026-08-05 against a 2015-10-01..02
probe that it keys on the **subaward's** action date, not the prime's. One
fiscal year per job, `file_format=csv`, **no `columns` filter and no recipient
filter**: the full federal subaward universe, attributed afterwards. Raw:
`data/raw/subcontracts/usaspending_subawards_2026-08-05/` (22 jobs, **6,613,471
rows**) and `data/raw/subcontracts/usaspending_2026-08-12/`.

**`highergov_2023_export`** is `subcontract-05-09-23-22-23-37.csv`, FY2011–2023.
**Its query definition was never preserved, so its sampling frame is unknown
and no share-of-market claim can rest on it.** Only 19 of its rows recur in the
primary-source pull.

**`funding_forward_fill`** came out of the assistance pull, which filtered
`recipient_type_names=indian_native_american_tribal_government` **on the
PRIME** — so the prime is Native by construction and **this file cannot observe
a Native subcontractor under a non-Native prime at all**. It is carried as
`source_population = prime_tribal_filtered` so a consumer can see the
selection.

### What was deliberately not used

- **The USAspending static archive.** Settled by a **full enumeration of 4,597
  keys: zero contain the string `sub` in any case**, and every plausible
  subaward path returned 404 or 403. `files.usaspending.gov` publishes
  Contracts and Assistance only. **Do not re-spend host budget re-probing
  this.**
- **SAM's `prod/contract/v1/subcontracts/search`** — 2,733,178 records,
  paginated at 1,000 a page = about 2,733 requests = **273 days at the
  10-requests-a-day tier**. Not viable, and the elevated org role never landed.
- **A UEI-seeded pull.** 121 pulls the whole federal subaward universe and
  attributes afterwards. Narrowing it to known identifiers would import the
  blind spot `docs/PULL_DISCIPLINE.md` sizes at roughly three quarters of the
  entity universe. **This must not be "optimised."**
- **Terms-restricted tribal directories** — Colville, CTUIR/Umatilla, Yakama,
  Chickasaw, NANA/Akima, Southern Ute, Forest County Potawatomi — excluded by
  every route across Cedar. They do not bite here: FSRS is a federal reporting
  system and those nations' subaward rows are public record.

---

## 2. How the rows were made

> ⚠ **Script numbers collide.** `ls code/41_*` returns
> `41_build_codebooks.py` and `41_match_subawards_to_ledger.py`; `45_*`, `94_*`,
> `20_*` and `40_*` also collide. Cite the filename.

1. **`code/20_build_subcontracts.py`** — the HigherGov leg, read
   **positionally**, because the export ships **two columns both literally
   named `CAGE Code`** at positions 22 and 23.
2. **`code/41_match_subawards_to_ledger.py`** — UEI exact, uppercased, against
   the ledger only.
3. **`code/45_promote_subawards.py`** — the three-source merge, 2026-08-06,
   55,035 rows.
4. **`code/94_match_raw_subawards.py`** — the guarded name pass, 2026-08-07,
   +8,513 → 63,548.
5. **`code/121_pull_subawards_api.py`** (`canary` → `pull` → `collect` →
   `match` → `append`) — 2026-08-26 FY2021; 2026-08-28 +9,289; 2026-09-01/02
   +4,022.
6. **`code/249_audit_*.py`** and **`code/250_demote_stale_tierA_subaward_rows.py
   --apply`** — the tier demotion.

`promoted_date` reproduces that history exactly [measured]: 2026-08-06
**55,035** · 2026-08-07 **8,513** · 2026-08-28 **9,289** · 2026-09-01 **4,022**
= 76,859.

> **`45_promote_subawards.py` cannot promote a `121` pull, and running it is
> destructive.** It reads only the `usaspending_subawards_2026-08-05`
> directory, would re-stamp `source_dataset = highergov_2023_export` on rows it
> re-reads, and would write 49 columns — reverting the deflator enrichment. The
> route for anything from `121` is **`121 match` then `121 append`**, and
> `append` is also the inflation enricher, so there is no third step. It is
> idempotent on columns but **not on rows**: run it once per `match`.

### The sibling tables

| table | rows | $ |
|---|---:|---:|
| `subawards.csv` | **76,859** | $47,301,660,819.78 unfiltered |
| `subaward_entity_rollup.csv` | 450 | prime-side $8,628,034,411.03 · sub-side $8,579,396,759.50 · both-sides $1,357,141,080.50 |
| `prime_sub_network.csv` | 220 | $669,825,812.00; 153 primes, 92 subs, **3 self-edges** |
| `subaward_identifier_harvest.csv` | 304 | $2,679,303,248.00 |
| `subaward_identifier_netnew.csv` | 210 | 181 new against the tiered ledger; **0 new against the union** |

[measured]

---

## 3. How entities were attributed

**Route order, with a tier ceiling on each:**

| route | tier |
|---|---|
| identifier — UEI exact against `cedar_identifier_ledger_final.csv` | the ledger's own A or B |
| declared parent UEI | **B, family level** |
| name + 8 guards + `cedar_match_guard` | **B, always, and always to review** |
| containment | **attributes NOTHING** |

**Nothing in this dataset reaches tier A on its own. Tier A requires a ruling.**

Measured: `prime_native_tier` A 21,144 · B 12,359 · `source_filter` 204 · blank
43,152. `sub_native_tier` A 16,156 · B 28,823 · blank 31,880. `cedar_uid` is
populated on **33,503 of 76,859 rows (43.6%)** — the C4 blocker.

**Both sides are resolved independently**, which is the whole point of the
dataset. `direction` [measured]:

| direction | rows | $ |
|---|---:|---:|
| `b_native_as_subawardee` | 43,108 | $25.85B |
| `a_native_as_prime` | 32,040 | $18.20B |
| `both_sides_native` | 1,667 | $3.21B |
| `unknown` | 44 | $39.0M |

**643 distinct Native entities are touched** — 161 prime-side, 633 sub-side.
Either side is populated on 76,785 of 76,859 rows (**99.9%**), so quoting the
43.6% `cedar_uid` rate alone badly understates the linkage. [measured]

### Why a name pass was needed at all

The 2026-08-07 pass added 134 first-time entities, **109 of them on the name
route**, concentrated in **BIE schools (27), Urban Indian Organisations (23),
intertribal organisations (21), village corporations (20), tribal colleges (15)
and Native CDFIs (14)** — classes that are in the spine and largely absent from
the identifier ledger. No number of identifier re-runs could have reached them.

### Containment attributes nothing — the seventh face of one bug

An intermediate version let containment link after guards 1–6 and produced, on
the first 600,000 raw rows:

```
FL DEPT OF HEALTH               -> Native Health        3,135 subawards
RI DEPT OF ELEM & SEC ED        -> Elem Indian Colony   1,617
BOOZ ALLEN HAMILTON INC         -> Hamilton               535
PERSPECTA ENTERPRISE SOLUTIONS  -> Enterprise             376
SPOKANE, CITY OF                -> Spokane Tribe           19
```

Every guard satisfied, every answer wrong — because **the spine stores short
canonical names and a short tribal name is usually also a place name.**
Containment now banks a `CANDIDATE_NOT_APPENDED` instead: **127 banked**, some
of which probably *are* right, and none of which is asserted.

Guard refusal counts on that pass: municipal/county 872,042 · single-token core
435,382 · separate legal person 432,062 · non-US country 106,904 · state
disagreement 4,860 · record-less-specific 173 · trap-token 36 · ANCSA namesake
pair 1 · parent-route guards 197. The review file
`review/subaward_matches_2026-08-07.csv` holds 4,353 rows: STAGED_TIER_B 226,
CANDIDATE_NOT_APPENDED 127, REFUSED_BY_GUARD 4,000.

### The tier demotion, and why it only runs downward

`sub_native_tier` and `prime_native_tier` are a **copy of the ledger's
`confidence_tier` at promotion time** — this file mints no tier of its own. Of
204 tier-A rows the ANCSA ownership pass repointed, **111 keep A** (the ledger
is A today and names the same corporation) and **93 demote A→B** (91 sub-side,
2 prime-side; seven Olgoonik UEIs sitting at tier B via
`agent_research_one_leg`). A whole-file scan found exactly 93 rows that are
A-here, B-in-ledger and same-entity, so the demotion set is closed.

It is safe to do in place because it moves the file **toward** what a rebuild
would write. **Nothing is promoted. Demoting is safe; promoting is not.**

---

## 4. Decisions that shaped the data

### The duplicates are RETAINED, not de-duplicated

`duplicate_status` [measured]:

| status | rows | $ |
|---|---:|---:|
| `primary` | 58,731 | $32.67B |
| `exact_repeat_within_source` | 17,282 | $14.11B |
| `superseded_by_primary_source` | 846 | $0.53B |

Literal byte-identical duplicate rows: **10,770 across 2,933 groups, worst
group 22.** [measured — this matches the readiness scoreboard exactly.]

**They are monthly SAM re-filings of one subaward, not repeated subawards**,
and that was proved rather than assumed on the FY2021 pull: **one group is 93
re-filings of a single $57,500 subaward running 2022-08 to 2025-01, each with
its own `subaward_sam_report_id`, one action date, one subaward number.**
`m45.identity_key` collides on **111,933 of 765,109** FY2021 raw rows (14.6%).

Per Cedar's flag-never-delete rule they are kept and flagged in band. **The flag
is the fix; the delete would be the defect.**

This is one of five duplicate allegations across Cedar and **the only one that
turned out to be real repetition of anything** — and even here the repeated
thing is a *filing*, not a subaward. The other four dissolved on measurement:
`prime_contracts` 80,778 → 0, `prime_contracts_archive_backfill` 60,919 → 0,
`faads_*` 180,260 → 3,441 (a de-dupe there would have destroyed
**$8,291,124,113** of real obligations), and `np_schedule_i_grants` 101 → 0.
Each of those was fixed by restoring or adding an identifying column, never by
deleting a row.

### The obvious dedup key was refused, and the reason is eleven Alaska Native villages

`(prime_award_id, subaward_number)` collapses 53,417 rows onto 30,773 keys,
destroying 22,644. FEMA disaster grant `1843DRAKP0000000` reports subaward
number **`1843-GR35056` against eleven different subawardees** — Native Village
of Eagle, Tuluksak, Akiak, Akiachak, Tanana, Fort Yukon, Kwethluk and more.
**Deduping on it would silently merge eleven distinct Alaska Native villages
into one row.**

### The source HAS a unique row id, the mapper drops it, and that is still correct

The FSRS extract carries **121 columns**; `94_match_raw_subawards.build_row`
reads **26**. Among the dropped columns is `subaward_sam_report_id`, a UUID
that is globally unique (FY2021 765,109 of 765,109 distinct; FY2020 456,412 of
456,412; zero overlap between years). That is the same shape as the
`prime_contracts` 80,778 — a lossy projection.

**But it identifies a SAM subaward REPORT, not a subaward.** Minting a
surrogate over it and calling it a subaward id was explicitly refused. This is
why ADR-012 registers "no usable event id" as **MISSING rather than solved**: a
surrogate over a non-unique key would manufacture 31,078 false distinctions and
make the eventual prime-link harder, not easier. **Diagnose the source extract;
do not paper the key.**

Also dropped and recoverable: `subawardee_duns` / `prime_awardee_duns` (the
HigherGov export has no DUNS at all), sub-side city, ZIP and place of
performance, congressional districts, CFDA numbers, and the five
highly-compensated-officer pairs.

> ### ⚠ THIS BLOCK DESCRIBED A LANDING THAT IS NOT IN THE FILE. Measured 2026-09-02T15:45Z.
>
> `docs/SUBAWARDEE_GEO_PROMOTION.json` records a successful apply at
> **10:37:13Z** — written by `cmd_apply` only *after* `atomic_replace`
> succeeded, so it did land. **It is not there now.** The live
> `data/clean/subawards.csv` has **71 columns and carries exactly one
> `geo_subawardee_*` column — `geo_subawardee_county_gap_reason`, the old gap
> sentence.** None of the ten promoted columns is present.
>
> **The mechanism is named, in another script's own docstring.**
> `871_promote_geo_keys_contracts.py :: backup()` carries a 2026-09-02 incident
> note: its same-day second run addressed the FIRST run's date-stamped snapshot
> and so **rebuilt the live tables from a morning vintage** — *"at 09:04 it took
> `subawards.csv` from 87,177 rows back to 76,859 … and it took
> `prime_contracts.csv` back to a 01:14 snapshot, discarding `1085`'s 326,166
> PSC/description fills and dropping five columns belonging to `1079`."*
> **That note lists 1085 and 1079 as the casualties and does not list 1109; the
> ten `geo_subawardee_*` columns are a third.** The bug in `backup()` is fixed;
> the damage to this promotion was not repaired when the row count was.
>
> **The lesson, which this repo has now paid for twice in one day: a
> conservation proof is not a landing proof.** 1109's `verify` and `selftest`
> both exited 0 and its report conserved rows and money to the cent — all of
> which was true at 10:37Z and none of which says anything about 15:45Z. The
> check that would have caught this is the one that fails when the work did NOT
> happen: *are the ten columns in the live header, today?* One `head -1`.
>
> **It must be re-run, and it must run LAST**, after `121 append`, after
> `910`/`911`, and after `871`. Note also that the outcome table below is
> against **76,859** rows and the table is now **87,177**; the 10,318 appended
> rows have never been through 1109 at all, and `1109 index` predates the
> FY2023 Q3/Q4 zips, so the index must be rebuilt before the apply.
>
> *The original block follows, unaltered, because its method is correct and is
> what the re-run executes.*
>
> **RECOVERED 2026-09-02 — the subawardee's own geography.**
> `code/1109_subawardee_geo_promote.py`. `ON_DISK_NOT_PROMOTED`, not a fetch:
> zero network requests.
>
> `geo_subawardee_county_gap_reason` was populated on all 76,859 rows and read
> *"subawards.csv carries sub_state and no sub city, zip or county column; the
> subawardee's county is not derivable from this table. The county columns here
> are the PRIME award's, not the subawardee's."* That is exactly right about the
> clean table and wrong about the corpus — the staged FSRS extracts carry 118
> columns including `subawardee_city_name`, `subawardee_state_code` and
> **`subawardee_zip_code`**.
>
> The join is one exact identifier against one exact identifier:
> `910_subaward_report_id_backfill.py` had already put `subaward_sam_report_id`
> back on **75,861 of 76,859 rows (98.7%)**, and an index over all 62 CSV
> members of the staged zips holds **8,480,914 distinct ids from 8,480,999
> source rows** (85 seen twice; **52** of those disagree on the subawardee's
> address between filings — first occurrence kept, since a re-filing may be
> correcting it). ZIP → county uses the same
> `data/clean/geo_place_county_crosswalk.csv` (`place_key_type = 'zip5'`,
> 21,923 entries) and the same dominance/ambiguity discipline as `871`.
>
> | outcome | rows | share |
> |---|---:|---:|
> | **county derived from the subawardee's own ZIP** | **73,388** | **95.5%** |
> | address recovered, ZIP not in the county crosswalk | 1,986 | 2.6% |
> | no `subaward_sam_report_id`, so no join is possible | 998 | 1.3% |
> | source published no ZIP | 391 | 0.5% |
> | report id present, not found in any staged extract | 96 | 0.1% |
>
> Ten columns added, all prefixed `geo_subawardee_`, plus
> `geo_subawardee_basis` which is **never blank** and says which of the five
> outcomes a row is in. Rows 76,859 → 76,859 and $47,301,660,819.78 →
> $47,301,660,819.78, **conserved to the cent**; `verify` and `selftest` both
> exit 0, the latter proving all three invariants FIRE on injected violations.
>
> **`sub_state` and the `geo_prime_award_*` columns are untouched** — the
> latter are and remain the PRIME award's geography, which is the distinction
> the gap reason existed to protect. The gap sentence is now rewritten PER ROW
> rather than left as one blanket claim that contradicts the columns beside it.
>
> **This is an IN-PLACE ENRICHER.** Anything that rebuilds or appends to
> `subawards.csv` — `121 append`, `45`, `94` — leaves the new columns blank on
> the rows it adds. Re-run 1109 (`index` only if the raw corpus changed, then
> `apply`) as the LAST step of any refresh.

### An accepted token is not a working job

On 2026-08-12 nine `bulk_download` jobs ran over 80 minutes, **all accepted
with tokens and all failed server-side with the opaque body `"An error
occurred."`** Three two-day probes separated the candidate causes: a
`diag_sub_2015` failure killed *"the FY2021–24 window is broken"*; a PRIME
control `diag_prime_2021` failure killed *"`sub_award_types` is broken"*; and a
two-day canary failing killed *"the jobs are too big."* Verdict: **the whole
`bulk_download` service was building nothing that day.** `121` now runs a
canary first. Both hostnames were refusing the same IP within two minutes — the
peer's log was the cheapest probe and cost zero requests.

### "Slice for size" was disproved

`fy2021` is a full year, 765,109 rows, and **finished in 23,613 seconds (6.6
hours)**; `fy2022` reached 221,865 rows and died; a **two-day** canary failed on
2026-08-12. Jobs died in pairs at two instants (00:07:14Z and 02:36:10Z) while
everything that completed did so between them. **Quarters are a scheduling
hedge, not a size fix.** Also disproved: *"a job at 0 rows for 80 minutes is
dead"* — the server reports `rows_so_far = 0` until the file is built.

---

## 5. What a buyer may total

- **`subaward_amount` is additive only on rows where `duplicate_status ==
  'primary'` AND `subaward_exceeds_prime_flag != 'yes'`.** 58,117 rows,
  **$25,864,997,128.19**. [measured]
- **Never add subawards to `prime_contracts.csv`.** A subaward is a slice of a
  prime award already counted there.
- **Never pool the two populations.** A Native prime paying a non-Native sub
  and a non-Native prime paying a Native sub are different economic
  relationships running in opposite directions, and summing them double-counts
  the 1,667 `both_sides_native` rows.
- **`native_passthrough.csv` is a PROJECTION of this table, not new money** —
  ~~1,522 rows / $2,972,389,900.81, of which only 1,135 rows /
  $869,328,591.38 are `amount_countable = 1`~~ **RE-MEASURED 2026-09-02:
  1,663 rows / $3,209,170,541.63, of which 1,259 rows / $1,050,719,668.88 are
  `amount_countable = 1`.** The struck figures predate the FY2023 Q1/Q2
  promotion; `81_build_passthrough_dataset.py` rebuilt the file at 01:20 on
  2026-09-02 and it IS consistent with its parent. It was the documents that
  were behind, not the file. FSRS is self-reported by the
  prime with no validation: **the RELATIONSHIP is the product; the AMOUNT
  carries a filter.**
- **Never compute network leakage without filtering `self_edge_flag`** — 3 of
  220 edges in `prime_sub_network.csv` are self-edges. [measured]

---

## 6. Known limits

- **FY2022 and FY2024 are effectively empty and must not be quoted.** FY2022
  holds **89 countable rows / $47,021,525**; FY2024 **166 / $113,334,471** —
  all HigherGov and forward-fill, **zero FSRS**. FY2023 is **half a year**:
  4,100 rows / $1,537,605,212, Q1 and Q2 only (2022-10-01..2023-03-31, 361,109
  raw rows). Label it as such. [measured]
- Countable rows by fiscal year [measured]: 2010 129 · 2011 1,567 · 2012 2,131
  · 2013 2,471 · 2014 3,658 · 2015 4,014 · 2016 4,174 · 2017 3,552 · 2018 5,485
  · 2019 6,259 · **2020 3,185** · 2021 7,408 · **2022 87** · **2023 3,457** ·
  **2024 126** · 2025 7,042 · 2026 3,325.
- **FY2020 has no FSRS contract subawards at all.** The 2026-08-05 `fy2020` job
  returned an assistance member of 456,412 rows and a **contracts member of
  4,144 bytes — one header line and zero data rows**, against FY2019's 439 MB.
  The only FY2020 contract rows are 180 inherited from HigherGov.
  `fy2020_procurement` was re-submitted so that an empty answer would be
  unambiguous; **it has not been answered.** `fy2022`, `fy2023` and `fy2024`
  remain `status: failed` upstream with the same opaque body.
- **FSRS begins FY2010, and that is statutory, not a gap.** FFATA dropped the
  reporting threshold from $25M to $25,000 in October 2010. Demonstrated:
  FY2001–2009 jobs returned 4,945 raw rows in total and **every one carries
  `subaward_sam_report_year >= 2010`** — filer typos, including a SpaceX
  subaward dated 2000-11-09 and filed in 2024. **51 rows carry
  `action_date_precedes_ffata_flag = yes`** [measured]. Never chart by
  `subaward_date` without excluding them.
- **774 rows report a subaward LARGER than their own prime award** [measured],
  worst case **12,240×**: prime `N6945011M3601`, a $64,910.88 award, reporting a
  **$794,526,041** subaward to GEOPAVE LLC. That one row alone put a
  state-recognized tribe at the top of the subcontracting-out league table,
  which is why `subaward_exceeds_prime_flag` is part of the money rule rather
  than a footnote.
- **No validated primary key and no declared grain, on purpose.**
  `45_promote_subawards.identity_key` is unique across the `primary` rows **and
  only there**, because byte-identical repeat filings are retained deliberately
  with no per-occurrence ordinal. `GRAIN_WS1` in
  `code/512_build_dataset_contracts.py` is empty for this reason: a declared
  grain the data contradicts is a release-blocking violation, and an honest
  blank is better than a false declaration.
- **`naics` and `psc` are the PRIME award's codes, not the sub's.** Assistance
  subawards carry **no NAICS at all**, so any industry cut silently drops
  exactly where the Native-subcontractor population lives.
- **The Native-sub population is overwhelmingly state agencies passing federal
  grants through to tribal governments** — Washington OSPI → Makah, Montana DOT
  → Fort Peck, Wisconsin DPI → Menominee. Those flows are invisible in prime
  contracting and in federal funding alike, which is the argument for the
  dataset.
- **FSRS is threshold-gated, self-reported and unaudited.** Absence is not
  evidence of no subcontracting, and every total here is a lower bound.
- **`description` is populated on 76,813 of 76,859 rows** — 99.94% fill on the
  single most informative column in the table — and is not in the shipped
  sample. Nor are `prime_award_amount` (73,057) or
  `subaward_to_prime_ratio`, which is the whole question in subcontracting.
- **`code/62_no_regression_check.py` does not measure this dataset at all.**
  Its passing is not evidence about a subaward build.

---

## 7. Refresh

| source | cadence | Cedar holds | state |
|---|---|---|---|
| FSRS subawards via `api.usaspending.gov` | continuous; primes file by the end of the month following the award month | 2026-08-03 | source edge **NOT ESTABLISHED** |

[measured — `docs/REFRESH_CADENCE.json`, regenerated 2026-09-02]

**The route:** `121 canary` (about 9 minutes, one two-day job) → `pull --only
<jobs>` → `collect` → `match` → `append` → `910 rescan` → `910 apply` →
`911 apply` → `871` → `81` → **`1109 index` → `1109 apply` (LAST)** → `250`.

> **`871` writes `prime_contracts.csv` as well as this table, and it reverts
> `1085`.** Added 2026-09-02 after it did so. Any refresh that runs `871` must
> finish with `py -3 code/1085_prime_psc_desc_repull.py apply`, or 592,925 PSC
> and description values silently disappear from contracting. The ordering rule
> is one rule with two tables in it.

**Two named holes in the pull, both closeable, both measured 2026-09-02:**

1. **`fy2023_q4` came back header-only.** The server said `finished` with no
   message in 80 seconds and returned a 1,889-byte zip whose two CSV members
   are 4,144 and 3,992 bytes — one header line each. In the clean table that
   shows as 2023-07/08/09 at **14 / 24 / 23** rows against 484–704 in every
   neighbouring month. Re-submitted 15:42:31Z on the script's own
   re-submit-an-empty-build-once path.
2. **`fy2022_q1..q4` have never been submitted.** `121 status` says
   `NOT SUBMITTED` for all four; FY2022 is still **89 countable rows /
   $47,021,525** and is the largest remaining hole in the dataset. The
   full-year `fy2022` job is a corpse and rule 5 does not bind on it.
**Never raise `MAX_INFLIGHT` above 1**, and run one poller per host. On Windows,
check for a live poller with `Win32_Process.CommandLine` including
`ParentProcessId` — `ps aux` cannot see command lines here and has returned 0
with four pullers running.

Target cadence: monthly, once the FY2022–24 hole closes.

**What breaks if it is not re-pulled: a closed year keeps moving.** 93 SAM
reports landed on one FY2021 subaward between 2022-08 and 2025-01, so *"we
pulled FY2019 once"* is not *"we hold FY2019."* Re-reading a window is
idempotent through `m45.identity_key` rather than stacked.
`prime_sub_network.csv` and `subaward_entity_rollup.csv` are rebuilt by a
refresh.

---

## Stale claims found while writing this

1. **`docs/MONEY_TOTALLING_RULES.md` says the money rule removes "$21,210,637,456.80
   — 86.9% of the unfiltered figure."** That is arithmetically wrong on its own
   numbers: $21.21B / $45.62B = **46.5%**. 86.9% is the removed amount as a
   share of the **correct** total, i.e. the overstatement factor. And all three
   figures have since moved: measured today, **$47,301,660,819.78 unfiltered →
   $25,864,997,128.19 correct → $21,436,663,691.59 removed = 45.3% of
   unfiltered, 82.9% overstatement.** The same document's `duplicate_status`
   table (primary 55,316 / exact_repeat 16,675 / superseded 846, over 72,837
   rows) measures to **58,731 / 17,282 / 846 over 76,859 rows**, and its
   countable figure of 54,719 rows / $24,413,436,422.47 is now **58,117 rows /
   $25,864,997,128.19**. The file is regenerated by `code/574`, which last ran
   before the 2026-09-01 append.
2. **`docs/WHAT_IS_MISSING.md` already caught the denominator problem and named
   it correctly**, quoting the sample README at *"46.5% overstatement"* and the
   dataset descriptor at *"86.9%"* and observing that a buyer who reads both
   concludes one of them is wrong. That diagnosis is right and the fix — the
   figure living in one place, with its base stated — has not been made.
3. **Every row count for `subawards.csv` in the docs is behind.**
   `docs/DOC_CONTRADICTIONS_2026-08-26.md` (re-measured 2026-09-01),
   `docs/datasets/02b_subcontracting.md` and `docs/datasets/subcontracting.md`
   all say **72,837**; `docs/ARCHITECTURE.md` says **87,363**. It is
   **76,859**. Only `docs/WHAT_IS_MISSING.md` and `docs/REFRESH_CADENCE.md` are
   current.
4. **`docs/ARCHITECTURE.md`'s 87,363 is a LINE count, not a row count.**
   `500_build_architecture_map.py::read_rows()` is `sum(1 for _ in f) - 1`, and
   `subawards.csv` holds **92,929 lines against 76,859 CSV records** — 16,070
   embedded newlines, mostly in `description`. Anything counting this table
   must parse it.
5. **`docs/SUBCONTRACTING_BUILD_LOG_2026-08-05.md` still reads
   "`subawards.csv` | 998 | `direction` = `unknown` on all 998, by design."**
   Both halves are dead. Measured: **44 rows** carry `direction = unknown`. A
   banner was added 2026-08-26; the body is intact.
6. **`docs/datasets/02b_subcontracting.md` tells the reader to run `41` then
   `45` to promote.** That route is wrong for anything pulled by `121` — `41`
   and `45` cannot see the 08-12 or later pulls at all, and `45` would re-stamp
   provenance and drop the deflator columns. The correct route is `121 match`
   then `121 append`.
7. **The same doc's "NEVER do these" cites "5,941 of 345,090 rows (1.7%) …
   totalling $68.7B"** for the exceeds-prime flag. 345,090 is the raw
   all-recipient row count from the first 11 of 26 fiscal years, superseded the
   same day by 6,613,471. The measured flag on the clean file today is **774
   rows**. The warning is right; the denominator is a phantom.
8. **`docs/SUBAWARD_API_PULL_LOG.md` and `code/121`'s docstring still cite
   "zero of 4,631 keys"** in the argument that settles the static-archive
   question. The correct enumeration is **4,597**. Zero of 4,597 is still zero,
   but citing a retired listing invites a closed question to be re-opened on a
   technicality.
9. **`docs/datasets/subcontracting.md`'s §2 re-cites "the archive holds 4,631
   objects"** — the same issue, in the most current document of the family.
