# Methodology — Federal Subcontracting

<!-- BEGIN GENERATED:IDENTITY -->

**`subcontracting` — Federal Subcontracting.** Delivered as `dist/customer/subcontracting.csv`: **89,809 rows × 90 columns, 120.7 MB**, built from the flagship table `data/clean/subawards.csv`. Shelf `pro`; sold through **Cedar Press**; on the Cedar Press storefront. Readiness **READY**. [measured 2026-09-02 from the delivered file]

> **This block and Appendix M at the foot of this paper are GENERATED** by `code/1143_methodology_papers.py` from the delivered file itself, on every build — the same reason the codebooks are generated. Do not hand-edit either; the next build overwrites them.
>
> Everything between `<!-- BEGIN EDITORIAL:subcontracting -->` and `<!-- END EDITORIAL:subcontracting -->` is **hand-written and preserved byte-for-byte** across rebuilds. Put prose there and nowhere else.
>
> This paper is **not** the codebook. `dist/customer/subcontracting__CODEBOOK.md` carries the grain, the folded-in tables and the per-column fill rates, and `__NOTES.txt` carries the same for a person. This paper says how the dataset came to exist and why you should believe it.
>
> Generated 2026-09-02. `py -3 code/1143_methodology_papers.py verify` **fails** if the delivered file has moved since — see §M7.

<!-- END GENERATED:IDENTITY -->

<!-- BEGIN EDITORIAL:subcontracting -->
**`subcontracting`. `data/clean/subawards.csv`, 89,809 rows.
Unfiltered `subaward_amount` $57,020,557,710.47; the correct total is
$34,906,694,737.65.** [re-measured 2026-09-02T17:00Z, cents-exact]

> ### EVERY FIGURE BELOW DATED EARLIER ON 2026-09-02 PREDATES TWO FOLD-INS AND IS SUPERSEDED.
>
> `121 append` ran twice today: **+10,318 rows at 12:09Z** (FY2023 Q3, FY2024
> Q1–Q4) and **+2,632 at 16:49Z** (FY2023 Q4, which had come back as a
> header-only object and was re-pulled). 76,859 → 87,177 → **89,809**. The full
> declared enricher chain was then run in order — `910 rescan`, `910 apply`,
> `911 apply`, `871`, `81`, `1109 index`, `1109 apply` — and every step proved
> row and money conservation to the cent.
>
> ```
> all 89,809 rows                            $57,020,557,710.47   <- never quote this
> countable: duplicate_status == 'primary'
>        AND subaward_exceeds_prime_flag != 'yes'
>        69,921 rows                         $34,906,694,737.65   <- the correct total
> the money rule removes                     $22,113,862,972.82
>    = 38.8% of the unfiltered figure
>    = 63.4% MORE than the correct total
> ```
>
> **State the denominator.** 38.8% and 63.4% are the same difference over two
> bases. Both the older pairs — 45.3% / 82.9%, and 46.5% / 86.9% before that —
> are now wrong on both numbers *and* were each quoted at some point with the
> wrong noun. The overstatement has FALLEN because the money the fold-in added
> is overwhelmingly `primary`, which is what a real year of coverage looks like.
>
> `duplicate_status` [re-measured]: `primary` **70,597** ·
> `exact_repeat_within_source` **18,366** · `superseded_by_primary_source` 846.
>
> **The two years this document tells a buyer not to quote:**
>
> | | this doc says | measured now |
> |---|---|---|
> | FY2023 | *"half a year: 4,100 rows / $1,537,605,212, Q1 and Q2 only"* | **8,216 rows, 7,063 countable, $7,528,402,466 — all four quarters** |
> | FY2024 | *"166 countable / $113,334,471, zero FSRS"* | **8,965 rows, 8,291 countable, $3,157,482,237** |
> | FY2022 | *"89 countable / $47,021,525"* | **unchanged — 89 / $47,021,525.** `fy2022_q1..q4` were never submitted; all four went in at 16:47Z and are generating. This is now the only empty year. |
>
> Enricher coverage on the whole table after the chain: primary key
> `(source_dataset, subaward_source_record_id)` **0 blank / 0 collisions on
> 89,809 rows**; `subaward_sam_report_id` **88,811 (98.89%)**; at least one
> Cedar leg **87,355 (97.27%)**; **subawardee's own county 85,858 (95.6%)**.

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

> ### ✅ RE-LANDED 2026-09-02T16:58Z, ON THE ENLARGED TABLE. What follows is the record of how it was lost.
>
> **Re-run after the fold-in, in the declared order, as the LAST step.**
> `1109 index` was rebuilt first because the old index predated the FY2023 Q3
> and Q4 zips: **68 CSV members, 8,916,498 source rows, 8,869,339 distinct
> `subaward_sam_report_id`, 0 rows with no id, 57 ids seen twice with a
> different subawardee address** (first occurrence kept). Then `apply`:
>
> | | |
> |---|---:|
> | rows | 89,809 → 89,809 **conserved** |
> | `subaward_amount` | $57,020,557,710.47 → $57,020,557,710.47 **conserved to the cent** |
> | **county from the subawardee's own ZIP** | **85,858 (95.6%)** |
> | ZIP recovered, not in the county crosswalk | 2,424 (2.7%) |
> | no `subaward_sam_report_id`, no join possible | 998 (1.1%) |
> | source published no ZIP | 529 (0.6%) |
> | live header | **81 columns; all ten `geo_subawardee_*` present** |
> | `selftest` | exit 0 — all three invariants proven to FIRE on an injected violation |
>
> **`verify` reports INV-SGEO-1 as UNMEASURED for this run, and that is the
> honest answer rather than a pass.** Its baseline is the newest
> `.bak_*_pre_1109_*` on disk, and the only one there was the 76,859-row
> vintage from 10:24Z — two fold-ins ago. Comparing against it produced a
> "FAIL rows 76,859 → 89,809", which is not a breach, it is the day's work.
> The stale snapshot was moved aside
> (`.superseded_pre_fold_in_76859_kept_as_evidence`) so `verify` says
> UNMEASURED instead of reporting somebody else's legitimate change as a
> violation. The conservation figures above are measured **by the apply itself,
> during the write**, which is the run that can actually see it.
>
> **Two code fixes so neither half recurs**, both 2026-09-02:
> - `1109`'s and `1085`'s `backup()` now supersede a same-day snapshot whose
>   size does not match the live file and re-take it — the rule
>   `871_promote_geo_keys_contracts.py` already earned the hard way.
> - the ten columns are registered in `121`'s `POST_PROMOTION_COLS` and in
>   `cedar_pipeline.KNOWN_ORDERINGS`, so the next `121 match` accepts them
>   instead of refusing, and `build.py` and `62` know 1109 runs last.
>
> ---
>
> ### ⚠ HOW IT WAS LOST. Measured 2026-09-02T15:45Z, before the re-run above.
>
> `docs/SUBAWARDEE_GEO_PROMOTION.json` records a successful apply at
> **10:37:13Z** — written by `cmd_apply` only *after* `atomic_replace`
> succeeded, so it did land. **It was not there at 15:45Z.** The live
> `data/clean/subawards.csv` has **71 columns and carries exactly one
> `geo_subawardee_*` column — `geo_subawardee_county_gap_reason`, the old gap
> sentence.** None of the ten promoted columns is present.
>
> **The mechanism is in this project's own logs, to the minute, and it is not
> an accident — it is a guard doing its job and the operator paying it off in
> the wrong currency.**
>
> | time | event | evidence |
> |---|---|---|
> | 10:37:13Z | `1109 apply` lands the ten columns, county on 73,388 of 76,859 | `docs/SUBAWARDEE_GEO_PROMOTION.json` |
> | **12:01:12Z** | **`121 match` REFUSES**: *"subawards.csv header is not the promoted schema … columns append() cannot fill=['geo_subawardee_city', 'geo_subawardee_state_code', …]"* — naming exactly these ten | `logs/121_match.log` |
> | **12:03:54Z** | **`121 match` runs clean on the same file** | `logs/121_match2.log` |
> | 12:09:09Z | `121 append` reads the file as *"76,859 existing … 71 columns"* | `logs/121_append.log` |
>
> **In the 162 seconds between those two `match` runs the ten columns were
> taken back out of the table so the promotion could proceed.** The guard was
> right — a column `append()` cannot fill WOULD be blanked on every appended
> row — and the resolution chosen was to delete the blocked work rather than to
> register it. `POST_PROMOTION_COLS` had been extended for `871`'s ten geo
> columns eleven hours earlier, *explicitly on the geography workstream's
> behalf*, and 1109's ten were simply never added.
>
> **A separate, larger revert happened an hour later and is worth not
> confusing with this one.** `871_promote_geo_keys_contracts.py :: backup()`
> carries its own 2026-09-02 incident note: a same-day second run addressed the
> FIRST run's date-stamped snapshot and **rebuilt both live tables from a
> morning vintage** — *"at 09:04 it took `subawards.csv` from 87,177 rows back
> to 76,859 … and it took `prime_contracts.csv` back to a 01:14 snapshot,
> discarding `1085`'s 326,166 PSC/description fills and dropping five columns
> belonging to `1079`."* That bug is fixed and the row count was repaired; it is
> **not** what removed the ten columns, which were already gone by 12:03Z.
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
  'primary'` AND `subaward_exceeds_prime_flag != 'yes'`.**
  ~~58,117 rows, **$25,864,997,128.19**.~~ **RE-MEASURED 2026-09-02 by
  `code/1128_cicd_benchmark_refresh_2026_09_02.py measure`, independently of the
  banner at the top of this file and agreeing with it to the cent: 69,921 rows,
  $34,906,694,737.65.** The struck figures predate the two `121 append`
  fold-ins this document's own header records, and they are the pair that was
  still circulating as settled — see that header for both denominators.
- **Never add subawards to `prime_contracts.csv`.** A subaward is a slice of a
  prime award already counted there.

<!-- BEGIN REGIME-1128 -->
### The deeper reason the two never sum: they are not the same KIND of measurement

*Added 2026-09-02 from the owner's own account of why CICD's 2022 article
graphed a prime series and stated the prime+subaward figure as a single total
rather than graphing it. Written as a fact about the SOURCES, not as a Cedar
limitation.*

**A prime obligation is what the government recorded paying. A subaward is what
a vendor said it paid onward.** FPDS is a government reporting system; FSRS is a
prime contractor's self-report, threshold-gated and unaudited, with no
government verification on the sub side. Two reporting regimes, two completeness
profiles, two different epistemic objects.

That is the reason underneath the slice-of-a-prime rule, and it is the stronger
one. Even if double-counting were somehow not a concern, a
government-recorded figure and a vendor-reported figure would not belong in one
sum, because the reader cannot tell which half of the total carries which
warranty.

**Consequence for any annual series: year-over-year movement in this table is
partly reporting behaviour, not economic activity.** Measured on the live file,
countable subaward dollars by fiscal year run FY2018 $3.82B → FY2019 $3.27B →
**FY2020 $0.58B** → FY2021 $4.83B → **FY2022 $0.05B** → FY2023 $7.53B →
FY2024 $3.16B. FY2020 and FY2022 are collection and filing artefacts this
document already names in §6 — an empty FSRS contracts member and four
never-submitted jobs — and nothing economic happened in either year to justify
the shape. **Any chart of subawards by year must carry that caveat on its face,
or it will be read as a trend.** A single stated total is the honest form for
this quantity in a publication, which is exactly the form CICD chose.

**None of this is an argument against holding the data or linking it to
entities.** The subaward layer is the only place a Native entity appears as the
*subcontractor* rather than the prime, and no FPDS row can show that
relationship. `911` resolved `prime_cedar_uid` and `sub_cedar_uid` separately
for that reason. ~~43,282 rows (56%)~~ **RE-MEASURED 2026-09-02 on the
89,809-row file by `code/1128_cicd_benchmark_refresh_2026_09_02.py`: 47,671 rows
(53.1%) have a `sub_cedar_uid` and NO `prime_cedar_uid` — their only Native party
is the SUBAWARDEE — and 47,561 of those carry a blank `cedar_uid`, which is the
prime leg and is legitimately blank there.** 1,733 rows carry both legs, 37,951
the prime leg only, and **2,454 (2.73%) carry neither**, so at least one leg is
resolved on 97.27%. The 43,282/56% pair predates the two `121 append` fold-ins
and should not be re-quoted. Vendor-reported is a reason to **label** the
dataset, not a reason to discount it.
<!-- END REGIME-1128 -->
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

- ~~**FY2022 and FY2024 are effectively empty and must not be quoted.** FY2022
  holds **89 countable rows / $47,021,525**; FY2024 **166 / $113,334,471** —
  all HigherGov and forward-fill, **zero FSRS**. FY2023 is **half a year**:
  4,100 rows / $1,537,605,212, Q1 and Q2 only (2022-10-01..2023-03-31, 361,109
  raw rows). Label it as such.~~ **TWO OF THE THREE ARE CLOSED, 2026-09-02.**
  FY2024 is **8,291 countable rows / $3,157,482,237** and FY2023 is **7,063 /
  $7,528,402,466 across all four quarters** — 749,548 raw rows over
  2022-10-01..2023-09-30. **FY2022 is unchanged at 89 / $47,021,525 and is the
  one year that must still not be quoted**; its four quarters were submitted at
  16:47Z and are generating.
- **A `finished` job with no error message can still be empty, and the row
  count is the only thing that says so.** `fy2023_q4` returned HTTP 200,
  `status: finished`, `message: null` — and a 1,889-byte zip whose two CSV
  members are 4,144 and 3,992 bytes: one header line each, **0 rows**, built in
  80 seconds where its four sibling quarters took 2,809–4,087. The re-pull
  returned **231,453 rows**, the largest of any FY2023 or FY2024 quarter. The
  detector that caught it was not the pull log: it was three months of the
  clean table reading **14 / 24 / 23** rows against 484–704 in every
  neighbouring month. **Compare a window against its neighbours; a zero that
  the server reports without complaint looks exactly like a fact about the
  world.**
- ~~Countable rows by fiscal year [measured]: 2010 129 · 2011 1,567 · 2012 2,131
  · 2013 2,471 · 2014 3,658 · 2015 4,014 · 2016 4,174 · 2017 3,552 · 2018 5,485
  · 2019 6,259 · **2020 3,185** · 2021 7,408 · **2022 87** · **2023 3,457** ·
  **2024 126** · 2025 7,042 · 2026 3,325.~~
  **RE-MEASURED 2026-09-02T17:00Z after both fold-ins** — 2010 129 · 2011 1,567
  · 2012 2,131 · 2013 2,471 · 2014 3,658 · 2015 4,014 · 2016 4,174 · 2017 3,552
  · 2018 5,485 · 2019 6,259 · 2020 3,185 · **2021 7,441** · **2022 87** ·
  **2023 7,063** · **2024 8,291** · 2025 7,042 · 2026 3,325. Only the three bold
  years moved; every other year reproduces to the row, which is the check that
  the append added rather than disturbed. **FY2022 is now the only year a buyer
  must be told not to quote.**
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
<!-- END EDITORIAL:subcontracting -->

<!-- BEGIN GENERATED:MEASURED -->

---

# Appendix M — measured from the delivered file

*Generated 2026-09-02 by `code/1143_methodology_papers.py` from `dist/customer/subcontracting.csv`, read whole with duckdb and never sampled. Not from `data/clean/`, not from a build log, not from `MANIFEST.csv`. Where this appendix and a document disagree, **the delivered file is right** and `verify` prints the disagreement rather than smoothing it over.*

*Grain, folded-in tables and per-column fill rates are in `dist/customer/subcontracting__CODEBOOK.md` and are deliberately not repeated here.*

## M1 · Sources, as the delivered rows themselves record them

**`source_file`** — 89,809 of 89,809 rows populated, 34 distinct values:

| value | rows |
|---|---:|
| `usaspending_2026-08-12/fy2021` | 9,366 |
| `fy2019` | 9,254 |
| `fy2018` | 8,492 |
| `fy2025` | 7,130 |
| `fy2016` | 5,566 |
| `fy2017` | 5,512 |
| `fy2015` | 5,198 |
| `fy2014` | 4,913 |
| `fy2020` | 3,704 |
| `fy2013` | 3,631 |
| `fy2026` | 3,341 |
| `fy2012` | 3,070 |
| `usaspending_2026-08-12/fy2024_q1` | 2,641 |
| `usaspending_2026-08-12/fy2024_q4` | 2,501 |
| `usaspending_2026-08-12/fy2023_q4` | 2,407 |
| `usaspending_2026-08-12/fy2023_q1` | 2,363 |
| `usaspending_2026-08-12/fy2024_q2` | 2,064 |
| `fy2011` | 1,939 |
| `usaspending_2026-08-12/fy2023_q2` | 1,665 |
| `usaspending_2026-08-12/fy2023_q3` | 1,661 |
| `usaspending_2026-08-12/fy2024_q3` | 1,593 |
| `subcontract-05-09-23-22-23-37.csv` | 998 |
| `Assistance_Subawards_2026-08-05_H22M21S36_1.csv` | 230 |
| `Assistance_Subawards_2026-08-05_H21M11S29_1.csv` | 166 |
| `fy2010` | 141 |
| `Assistance_Subawards_2026-08-05_H22M29S09_1.csv` | 116 |
| `Assistance_Subawards_2026-08-05_H21M06S27_1.csv` | 96 |
| `fy2009` | 33 |
| `fy2008` | 7 |
| `fy2002` | 7 |
| `fy2004` | 1 |
| `fy2007` | 1 |
| `fy2003` | 1 |
| `fy2001` | 1 |

**`source_dataset`** — 89,809 of 89,809 rows populated, 5 distinct values:

| value | rows |
|---|---:|
| `usaspending_fsrs_pull` | 84,538 |
| `usaspending_fsrs_name_match` | 3,329 |
| `highergov_2023_export` | 998 |
| `funding_forward_fill` | 608 |
| `usaspending_fsrs_parent_cluster` | 336 |

**`source_population`** — 89,809 of 89,809 rows populated, 3 distinct values:

| value | rows |
|---|---:|
| `full_federal_subaward_universe` | 88,203 |
| `highergov_query_frame_unpreserved` | 998 |
| `prime_tribal_filtered` | 608 |

**`source_url`** — 89,809 of 89,809 rows carry one. Hosts, by row count:

| host | rows |
|---|---:|
| `www.usaspending.gov` | 88,811 |
| `www.highergov.com` | 998 |

**`fetched_date`** — 89,809 of 89,809 rows populated, 4 distinct values:

| value | rows |
|---|---:|
| `2026-08-05` | 63,548 |
| `2026-09-02` | 16,895 |
| `2026-08-12` | 9,289 |
| `2026-08-27` | 77 |

### The terms rulings that bind this dataset

Quoted from `docs/PUBLICATION_POLICY.md`, which holds the rulings; this paper does not restate them from memory.

- **Owner ruling, 2026-09-02** (`<!-- BEGIN TERMS-OWNER-RULING-2026-09-02 -->`): *"So tribal websites, I actually don't care if they say it does scrape. Because if it's publicly available and you can scrape it, scrape it."* A tribal entity's own public pages may be harvested regardless of a terms statement. `source_terms_status = TERMS_STATED_RESTRICTIVE` on a Native entity's own site is now **a recorded observation, not a gate**.
- **Four things that ruling does NOT touch, and none is a terms question:** (1) technical access controls — nothing login-gated, no admin or staging paths, no exploiting a misconfiguration; (2) a natural person's data held apart from their public role — home address, personal email or phone, DOB, SSN/TIN; (3) non-tribal licensors — EMMA/MSRB bars redistribution of its output "sold or free of charge" and names "any manual process", with CUSIP Global Services as a second licensor; (4) proprietary identifiers — Casino City, D-U-N-S — held internally, never shipped.
- **A terms restriction is scoped to the SOURCE that stated it, not to the nation** (`<!-- BEGIN TERMS-SCOPE -->`), and it does not bind a third party's filing of the same fact.

## M2 · How the rows were built — the pipeline, in order

**One documented rebuild:** `py -3 code/build.py run subcontracting --execute`. `py -3 code/build.py plan subcontracting` prints the ordering below live; it is reproduced here so the paper stands alone.

The collection holds **5 tables**. Those with a named build stage, flagship first:

| table | rebuilt by | then enriched by (must run LAST) | status |
|---|---|---|---|
| `subawards.csv` **(flagship)** | `121_pull_subawards_api.py`, `20_build_subcontracts.py` | `1109_subawardee_geo_promote.py`, `121_pull_subawards_api.py`, `250_demote_stale_tierA_subaward_rows.py`, `45_promote_subawards.py`, `871_promote_geo_keys_contracts.py`, `910_subaward_report_id_backfill.py`, `911_subaward_sub_leg_cedar_uid.py` | shippable |

**A full rebuild and an in-place enricher on one file need an ordering, and the enricher must run LAST.** A `.bak_*_pre<script>` file sitting beside a table is the signal that an enricher has touched it since the last build. This has cost this project four reverts of one file in a single day.

The delivered spreadsheet is then assembled by `code/1137_customer_dataset_combine.py`, which folds supporting tables onto the flagship **only where the measured cardinality on the shared key is one**, reverts any join that moved the row count, and prefixes every joined column with its source table's stem. One-to-many tables contribute a count column instead of rows, so a money total cannot be multiplied by a join.

## M3 · How entities were attributed

Cedar keys every dataset to one identity layer. `cedar_uid` is permanent and never reused; the human-readable handle retires when an entity is reclassified, so **join on `cedar_uid`, never on the handle**. A compound handle is canonical, not broken — stripping a suffix to make a join work turns joinable rows into unjoinable ones while looking like a normalisation.

**Entity attachment in the delivered file:**

| key column | rows carrying one | distinct values | coverage |
|---|---:|---:|---:|
| `cedar_uid` | 40,201 | 169 | 44.8% |

**An unkeyed row is often the right answer, not a defect.** ADR-010 separates *"we could not identify the entity"* — a defect — from *"there is no single entity to identify"* — the correct representation. Coverage is measured against the *resolvable* denominator, not the row count.

### What `attribution_method` means **in this dataset**

`docs/schema/attribution_method_vocabulary.json`, declared 2026-09-02: *"`attribution_method` is three different columns sharing a name — a join method, an evidence provenance, and a name-match algorithm. Each table is gated against its OWN vocabulary."* Reading one table's sense into another is how a containment match came to key a dollar.

**This dataset carries no `attribution_method` column.** The identity evidence it does carry is measured below. Do not import another dataset's term list to interpret it.

**And a RULED METHOD IS NOT A POSITIVE RULING.** `attribution_method` says WHO decided; `confidence_tier` says WHAT was decided. All 317 `elijah_ruling` EIN rows in the ledger are tier **X** — *negative* — and a script that read "the method is in the RULED set" as "the answer was yes" published 317 owner *exclusions* as confident attributions. Standing detector: `py -3 code/293_lint_bug_classes.py`. [from the record — `START_HERE.md`, defect class 1b]

### Every identity, tier and method column, measured

- **`geo_key_tier`** — 1 distinct value: `(blank)` 71,615 · `exact_award_summary` 18,194
- **`prime_native_tier`** — 3 distinct values: `(blank)` 49,921 · `A` 26,712 · `B` 12,972 · `source_filter` 204
- **`sub_native_tier`** — 2 distinct values: `(blank)` 40,371 · `B` 30,186 · `A` 19,252
- **`subaward_entity_rollup__confidence_tier`** — 2 distinct values: `(blank)` 53,792 · `A` 18,676 · `B` 17,341

### The evidence tiers

| tier | what it means |
|---|---|
| **A** | an identifier (UEI, CAGE, EIN, declared parent UEI), or a human ruling. The only grade a dollar may be keyed on without corroboration |
| **B** | a strong name method with an independent corroborator, or inheritance from a tier-A parent |
| **C** | a weak method — containment, token subset — held as a candidate, not published as a fact |
| **X** | **refused.** A negative ruling. Never read as a confirmation |

**A tier is INHERITED from the source row, never assigned by the consumer.** The exactness of the KEY says nothing about the correctness of the LINK: 873 of 1,104 EIN rows in the ledger sit on 52 entities carrying five or more EINs each, and 821 are tier B via `need_v6`, which is 6.5% accurate and never publishes alone. [from the record — `START_HERE.md`, defect class 1]

## M4 · What is **not** in it, and why

**No row was withheld from this delivery.** Every row that passed the collection's own inclusion test is in the spreadsheet. [measured — `dist/customer/MANIFEST.csv`, `rows_withheld = 0`]

The gate itself is `code/cedar_publication.row_ok`, applied identically by every publisher: a row is withheld if `publishable` is set to anything outside `{Y, y, 1, true, TRUE, blank}`, or if `source_terms_status` is outside `{SILENT, TERMS_STATED_NO_REUSE_RESTRICTION, blank}`. **A blank gate column means the gate was never evaluated for that row, not that it failed.** Separately, ten column names are refused outright wherever they appear — `owner_name_raw`, `email`, `phone`, `home_address`, `personal_email`, `ssn`, `tin`, `date_of_birth`, `officer_name`, `contact_name` — and the proprietary identifier families (Casino City, D-U-N-S) drop as **columns**, not rows: the row is ours, the identifier is not.

### Known gaps — every line in `docs/WHAT_IS_MISSING.md` that names this dataset or its flagship

- **L74** *(under “READ THIS FIRST — the sample is a hand-curated column list, and that is where most of the loss happens”)* — - **`subcontracting` shows no `description`.** Populated on **76,813 of
- **L242** *(under “`_entity_layer` — `cedar_identity_register.csv`, 1,555 rows, 6 columns shown”)* — is (`_entity_layer`, `native-owned-businesses`, `subcontracting`).
- **L675** *(under “`subcontracting` — `subawards.csv`, 76,859 rows”)* — ## `subcontracting` — `subawards.csv`, 76,859 rows
- **L747** *(under “THE SHORT LIST — what this week can fix without a single download”)* — | 5 | `subcontracting` | add `description`, `prime_award_amount`; swap tribe handle → `cedar_uid` | 76,813 / 73,057 / 33,503 |

### Open issues — every line in `docs/KNOWN_ISSUES.md` that names this dataset or its flagship

- **L164** *(under “A5 [RESOLVED 2026-09-02 — see note at end] · S1 · The arbiter document of last resort had gone stale in 6 of 14 rows”)* — | `subawards.csv` | 63,548 | **72,837** |
- **L516** *(under “C2 · S1 · `subawards.csv` — 10,770 duplicate rows, same shape suspected, unproven”)* — ## C2 · S1 · `subawards.csv` — 10,770 duplicate rows, same shape suspected, unproven
- **L523** *(under “C2 · S1 · `subawards.csv` — 10,770 duplicate rows, same shape suspected, unproven”)* — over-stated by an unmeasured amount. **Blocks `subcontracting` and `funding`.**
- **L1451** *(under “The data side, adjacent and NOT the same defect”)* — `subawards.csv`, `compact_structured_terms.csv`, `compact_required_reports.csv`,
- **L2110** *(under “M3 · CORRECTED · `subcontracting` is 97.27% linked, not 44.8%”)* — ## M3 · CORRECTED · `subcontracting` is 97.27% linked, not 44.8%
- **L2112** *(under “M3 · CORRECTED · `subcontracting` is 97.27% linked, not 44.8%”)* — `cedar_uid` in `subawards.csv` is the **PRIME leg**: 39,567 of its 40,201
- **L2120** *(under “M3 · CORRECTED · `subcontracting` is 97.27% linked, not 44.8%”)* — them / $98,041,089.48** on `data/clean/subawards.csv` by exact-UEI

## M5 · The money rules — which columns may be summed

Measured over the delivered file. **A sum printed here is the unfiltered arithmetic sum of the column and is NOT necessarily a figure a buyer may quote** — the fence below says which are and which are not.

| column | rows populated | distinct values | sum (unfiltered) | min | max |
|---|---:|---:|---:|---:|---:|
| `prime_award_amount` | 86,007 | 17,533 | $16,518,182,158,970.29 | $-514,458,497.00 | $35,035,280,267.19 |
| `subaward_amount` | 89,809 | 55,110 | $57,020,557,710.47 | $-24,530,372.00 | $4,501,612,694.00 |
| `subaward_amount_real2025` | 86,352 | 57,727 | $67,761,377,946.46 | $-32,813,420.06 | $4,743,961,514.99 |
| `subaward_entity_rollup__usd_as_prime_a` ⚠ **joined** | 36,020 | 100 | $26,496,699,783,573.18 | $0.00 | $1,740,005,674.45 |
| `subaward_entity_rollup__usd_as_subawardee_b` ⚠ **joined** | 36,020 | 114 | $19,583,506,623,258.34 | $0.00 | $1,684,411,206.21 |
| `subaward_entity_rollup__usd_both_sides` ⚠ **joined** | 36,020 | 66 | $1,806,176,548,444.73 | $0.00 | $544,639,166.45 |

**⚠ A column carrying a folded-in table's stem prefix is that table's grain repeated onto flagship rows, and row-summing it multiplies.** `subaward_entity_rollup__usd_as_prime_a`, `subaward_entity_rollup__usd_as_subawardee_b`, `subaward_entity_rollup__usd_both_sides` came from a supporting table joined one-to-one onto the flagship; the figure belongs to the entity or award the supporting table keys on, not to the row it is printed on. Sum it once per that key, never down the column. This is the owner-grain trap that turns $176.74B into $6,535.96B — a 36.98× inflation — in `contractor_ranking.csv`. [from the record — `docs/MONEY_TOTALLING_RULES.md`, block `GRAIN-WS5`]

**Which of these columns are a PARENT's figure printed on a CHILD's row — measured, not asserted.** A column appears below only where its value is *constant within* the key named, which is proof it belongs to that key and not to the row. The right-hand column is what it totals once per key, and the multiple is what row-summing costs you.

| column | belongs to | row-summed | once per that key | row-summing inflates by |
|---|---|---:|---:|---:|
| `subaward_entity_rollup__usd_as_prime_a` | `cedar_uid` (123 keys) | $26,496,699,783,573.18 | $7,943,989,328.24 | 3335.44× |
| `subaward_entity_rollup__usd_as_subawardee_b` | `cedar_uid` (123 keys) | $19,583,506,623,258.34 | $7,000,813,664.93 | 2797.32× |
| `subaward_entity_rollup__usd_both_sides` | `cedar_uid` (123 keys) | $1,806,176,548,444.73 | $1,231,925,611.55 | 1466.14× |

**The once-per-key figure is not automatically the figure to publish either.** It is the arithmetic that removes the repetition, nothing more; whether that total is meaningful is the fence's question, not this table's. A column absent from this table is *not* thereby declared summable — it is only declared not to be constant within any key this file carries.

### The fence, quoted verbatim from `docs/MONEY_TOTALLING_RULES.md`

That document is authoritative on which columns may be summed. It is **quoted here, never re-derived** — re-deriving a totalling rule from the data is precisely the error it exists to prevent.

| table | additive measure | sum it at | what double-counts |
|---|---|---|---|
| `subawards.csv` | `subaward_amount` | **only** rows with `duplicate_status == 'primary'` AND `subaward_exceeds_prime_flag != 'yes'` | summing past the flag; and adding subawards to prime obligations — **a subaward is a slice of a prime award already counted in `prime_contracts.csv`** |

Marked blocks in that document that name `subawards.csv`: `<!-- BEGIN GAMING-TOTAL -->`, `<!-- BEGIN GEO -->`, `<!-- BEGIN GRAIN-WS4 -->`, `<!-- BEGIN SUBAWARD-FUNDING -->`.

### The overstatement, measured from the delivered file

Summing `subaward_amount` over all 89,809 delivered rows gives **$57,020,557,710.47**. **That figure must never be quoted.** Applying the fence — `duplicate_status = 'primary'` AND `subaward_exceeds_prime_flag <> 'yes'` — leaves 69,921 rows and **$34,906,694,737.65**. The rule removes $22,113,862,972.82.

**State the denominator, every time.** An overstatement is measured against the truth, so the number to quote is **63.4%** — summing unfiltered lands you that far above the correct total. The share-of-the-inflated-total figure is a different and much less alarming sentence about the same error, and is not what a warning is for. [measured 2026-09-02 from `dist/customer/subcontracting.csv`]

And the corrected total is **still not additive with prime contracting**. A subaward is a slice of a prime award Cedar already publishes. Federal dollars obligated = primes; subawards say where those dollars went next.

### Time span, measured

| year column | min | max | rows with no parseable year |
|---|---:|---:|---:|
| `fiscal_year` | 2001 | 2026 | 0 |

**Read a trend against the reporting regime, not as behaviour.** `docs/ASSUMPTIONS_AND_LIMITATIONS.md` registers the breaks; a rise that begins at a rule change is the rule operating.

## M6 · Known limits, stated plainly

**Readiness: READY.** [measured — `docs/DATASET_READINESS.md`, regenerated by `py -3 code/518_dataset_readiness.py`]

| tables | grain | keys | duplicates | agg-unsafe | rebuild |
|---|---|---|---|---|---|
| 3 | 3/3 | 3/3 | clean | 0 | declared  |

The twelve-point contract a dataset is held to — grain declared and validated; keys and cardinality measured, not guessed; duplicates removed or the distinguishing dimension declared; entity attachment where the subject is an entity; every harvested row in a named disposition bucket; unresolved identity conflicts never shipping as definite facts; no double-counting path; one documented rebuild that does not destroy later enrichment; an update runbook another session can execute from the document alone; regression and semantic-diff gates over the outputs; column hygiene; and an inclusion basis on every row.

**1 column is blank on every delivered row** and is kept deliberately. Dropping them would make the schema depend on which rows shipped, and a buyer diffing two deliveries would watch columns appear and vanish. Sparsity is a coverage fact. They are named in the codebook.

**Do not sell past the evidence.** Where this paper states a figure it was measured on the date stamped beside it, from the file named beside it. Where it states a decision it names who made it. Anything not stated here is not known.

## M8 · Figures that have circulated in more than one value

Each row below was re-measured from the delivered file just now. The superseded values are the ones this project has actually watched drift; where one still appears in this paper's own hand-written body it is named, and **the measured figure is the one that is right**.

| figure | measured today | superseded values | still in this paper's prose? |
|---|---:|---|---|
| rows in the delivered file | **89,809** | 76,859, 76859 | ⚠ **yes** — 76,859, 76859 |
| how far a row-summed `subaward_amount` lands above the fenced total | **63.4%** | 82.9%, 86.9%, 45.3% | ⚠ **yes** — 82.9%, 86.9%, 45.3% |
| the unfiltered `subaward_amount` total | **$57,020,557,710.47** | $47,301,660,819.78, $45.62B, $47.30B | ⚠ **yes** — $47,301,660,819.78, $45.62B |
| the fenced `subaward_amount` total | **$34,906,694,737.65** | $25,864,997,128.19, $24.41B, $25.86B | ⚠ **yes** — $25,864,997,128.19 |

**Where the prose above and this appendix disagree, this appendix is right.** It was measured from `dist/customer/subcontracting.csv` on 2026-09-02; the prose was written against an earlier state of the same table. The prose is left standing rather than silently corrected, because a superseded figure that is *labelled* is recoverable and one that has been overwritten is not — and because the reasoning around it is usually still sound even when the number under it has moved.

## M7 · Fingerprint — what makes this paper stale

`verify` re-measures the four values below against `dist/customer/subcontracting.csv` and **exits 1 if any has moved**. A methodology paper is stale the moment its dataset is rebuilt, and a stale paper that cannot say so is worse than no paper.

```json
{
  "dataset": "subcontracting",
  "file": "dist/customer/subcontracting.csv",
  "bytes": 120663224,
  "rows": 89809,
  "columns": 90,
  "header_sha256": "707b8b05d0080ce8330b69cd79ad9274030c6cf8f90b4c45d96c513bcb975274",
  "measured": "2026-09-02"
}
```

Cross-check against `dist/customer/MANIFEST.csv`, which `code/1137_customer_dataset_combine.py` wrote at build time: it records **89809 rows × 90 columns**. The two agree.

<!-- END GENERATED:MEASURED -->
