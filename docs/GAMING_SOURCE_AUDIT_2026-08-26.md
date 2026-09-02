# Gaming source audit — where the sources go

*2026-08-26. Diagnosis only. No dataset, script or codebook was modified by this
pass. Every number below was measured against the files on disk today, not read
out of a build log.*

---

## THE QUESTION

> "the gaming dataset — we had so many sources like their websites, promotional
> material, slot machine info, OSHA, retirement data, like a bunch of stuff. Why
> are things getting lost in the shuffle?"

He is right on the premise. **Fifteen raw gaming source families are on disk,
5.5 GB, and every one of them was successfully turned into a clean table.**
Nothing is being lost during collection, and nothing is being lost during the
build. The extraction work is intact and, as far as this audit can measure,
correct.

**The loss happens in one place: the step between `data/clean/` and the shipping
bundle.** That step is a separate, manual, unowned script that has not been run
since **2026-08-06 17:54**, and even when it is run it silently drops any table
whose columns do not overlap a block in `codebook_master.csv` by 60%.

### The headline

| | rows |
|---|---:|
| Publishable gaming-family rows sitting in `data/clean/` | **104,412** |
| …that appear in any shipping artefact (`dist/`, `cedar_press.db`, manifests) | **912** |
| **share of the gaming dataset that actually ships** | **0.87%** |

The 912 are `gaming_facilities` (774) and `gaming_land_decisions` (138). They are
the two tables that existed on 2026-08-05.

There is a second, inverted half to this. `dist/07_gaming/` contains four notes
contracts. **Two of the four are the Casino City files** —
`gaming_property_capacity_history` (64,181 rows) and `gaming_facility_metrics`
(65,223 rows) — which the licence gate is supposed to make unshippable, and
`casino_city_id` is in the published codebook for `gaming_facilities`.
Meanwhile `gaming_properties.csv`, the 774-row de-vendored replacement built
specifically so the vendor panel would not have to ship, does **not** ship.

**The vendor data ships and the free replacement does not.** That is the
situation exactly backwards, and it is the same single defect.

---

## PART 1 — THE RAW SOURCE INVENTORY

Every gaming-related source family on disk, with what it became.

| # | Source family | Where it lives | Size | Manifest | Built by | Clean output | Rows |
|---|---|---|---:|---|---|---|---:|
| 1 | **Tribal enterprise websites** (crawled pages) | `data/raw/external/gaming_property_sites/pages/` | 1,749 files / 357 MB | **NO** | `142` | `gaming_property_site_observations.csv` | 262 |
| 2 | **Slot / game finders** (Chickasaw, Coushatta, FireKeepers) | `.../gaming_property_sites/gamefinder/`, `_recon/` | 236 files | **NO** | `142` | `gaming_game_finder_observations.csv` | **6,851** |
| 3 | **Careers / Indian-preference pages** (same crawl) | `.../gaming_property_sites/pages/` | — | — | `142` | `gaming_property_labor_demand.csv` | 43 |
| 4 | **Loyalty / rewards programme pages** (promotional) | `data/raw/external/digital_gaming/loyalty/` | — | yes | `119` | `loyalty_programs.csv` + `loyalty_program_property.csv` | 66 |
| 5 | **State regulator sites & annual reports** | `data/raw/external/gaming_official/` | 612 files / **929 MB** | **NO** | `92`,`93`,`94`,`95`,`96`,`97`,`117` | `gaming_capacity_official.csv` | **6,461** |
| 6 | **State gaming pulls (15 states)** | `data/raw/external/state_gaming/` | 281 files / 209 MB | yes | `107`,`107b` | `state_gaming_observations.csv` | 494 |
| 7 | **Slot-machine / device info — SEC manufacturer filings** | `data/raw/external/gaming_devices/` | 26 files / 64 MB | yes | `117` | `gaming_device_observations.csv`, `gaming_manufacturer_facts.csv` | 1,388 |
| 8 | **Washington per-tribe machine allocations** | `data/raw/external/wa_gaming/` | 46 files | yes | `104` | `wa_machine_allocations.csv` (+ `wa_machine_transfers.csv`, 0 by design) | 75 |
| 9 | **NIGC gaming ordinances** | `data/raw/external/nigc_ordinances/` | 1,417 files / **3.2 GB** | yes | `118`,`122`,`150`,`153` | `gaming_ordinances.csv`, `gaming_ordinance_ocr.csv` | 1,418 |
| 10 | **NIGC declination letters** | `data/raw/external/nigc_declinations/` | 490 files / 104 MB | yes | `90`,`91`,`100` | `nigc_declination_letters.csv` | 327 |
| 11 | **NIGC map / GGR reports / roster** | `data/raw/external/nigc/` | 82 files | yes | `84`,`89`,`143`,`155`,`156` | `nigc_regional_ggr.csv`, `nigc_region_assignments.csv`, `gaming_property_locations.csv` | 4,848 |
| 12 | **OSHA ITA 300A, CY2016–CY2025** | `data/raw/external/osha_ita/` | 12 files / 244 MB | yes | `100` | `gaming_employment_observations.csv` (OSHA share 364) | 769 |
| 13 | **Census LODES WAC** (block workplace jobs) | `data/raw/external/lodes/` | 37 files | yes | `100`,`101` | same file (LODES share 384) | — |
| 14 | **Gaming NEPA / environmental reviews** | `data/raw/external/gaming_nepa/` | 25 files / 190 MB | yes | `32a`,`32b` | `gaming_project_facilities`, `gaming_projections`, `gaming_mitigation_agreements` | 159 |
| 15 | **CA regulator (CGCC) documents** | `data/raw/external/ca_gaming/` | 195 files | yes | `103` | `ca_gaming_payments.csv`, `ca_gaming_facilities_official.csv` | 40,409 |
| 16 | **FL regulator / EDR / courts** | `data/raw/external/fl_gaming/` | 112 files | yes | `105` | `fl_gaming_payments.csv`, `seminole_bond_disclosures.csv` | 9,785 |
| 17 | **Digital gaming regulators (MI/CT/AZ)** | `data/raw/external/digital_gaming/` | 76 files | yes | `119` | `digital_gaming_revenue.csv`, `digital_gaming_relationships.csv` | 10,815 |
| 18 | **FAC tribal Single Audit PDFs + API** | `data/raw/fac/pdf/`, `/txt/` | 680 files | — | `147` | `fac_tribal_single_audits.csv`, `fac_audit_gaming_disclosures.csv` | 8,302 |
| 19 | **SEC vendor / supplier disclosure** | `data/raw/sec_vendor_disclosure/txt/` | 655 files | — | `148` | `gaming_vendor_tribal_licenses.csv` | 740 |
| 20 | **Compact corpus (Class III terms)** | `data/raw/external/compacts/` | — | yes | `15a–15e`,`95`,`127` | `compacts`, `compact_terms`, `compact_structured_terms`, … | 10,215 |

**Every one of these produced output. Not one source family died in collection.**

### Two provenance gaps worth fixing

`gaming_official/` (929 MB, 612 files) and `gaming_property_sites/` (357 MB,
1,985 files) are the **only two gaming raw directories with no
`_SOURCE_MANIFEST.csv`**. Every other directory carries one with an md5 and a
byte count per object. These two are the largest and the least traceable, and
between them they are the "websites and promotional material" the owner is
asking about.

### The source that genuinely is not here: retirement / pension

**Form 5500 has never existed inside Cedar Press.** There is no EBSA, ERISA,
EFAST or 5500 file, reference, or plan anywhere in `data/`, `code/` or `docs/` —
the string `5500` appears exactly once in the whole repo, inside an unrelated
Federal Register filename.

It was built, and it was built somewhere else:

    C:\Users\esm247\Desktop\4wheeler\casino_employment_validation\

That project holds a full tribal-casino employment source stack that Cedar Press
does not have, ~6.3 GB of raw:

| source | file | rows |
|---|---|---:|
| **Form 5500** (plan sponsor, active participants) | `data/resolved_form5500_tribal.csv` | **10,733** |
| **NLRB representation elections** | `data/resolved_nlrb_gaming.csv` | 250 |
| **PPP loans** | `data/resolved_ppp_tribal.csv` | 1,069 |
| **OSHA, independently resolved** | `data/resolved_osha_tribal.csv` | 2,009 |
| **SEC employment sentences** | `data/sec_employment_sentences.csv` | 1,736 |
| **QCEW** | `data/raw_qcew/` | 969 files |
| **IMPLAN benchmarks** | `data/implan_benchmarks.csv` | 42 |
| **Impact-study backlog extractions** | `data/impact_study_backlog_extractions.csv` | 34 |

**This is the second loss mechanism, and it is not a bug — it is a repository
boundary.** The owner remembers collecting retirement data because retirement
data *was* collected. It landed in the sister project on 2026-08-12 and has been
invisible from inside Cedar Press ever since.

**As of today it has started to cross.** A concurrent agent wrote
`code/156_stage_form5500_gaming_employment.py` at 17:04 and produced
`data/staging/gaming_employment_form5500_staged.csv` — **2,046 rows, 140 tribes,
195 EINs, 2009–2025**, of which roughly **25 tribes per year are new to Cedar's
employment table entirely**. It is correctly staged rather than merged, pending
two rulings (a new `MeasurementType` term, and whether the employment table
admits tribe-level rows with no `facility_id`). NLRB, PPP, QCEW, IMPLAN and the
impact studies have not crossed at all.

---

## PART 2 — THE FATE OF EVERY GAMING CLEAN TABLE

Fate was determined by re-implementing the exact gate in
`code/87_build_dataset_notes.py` (lines 326–331) against today's files.

### Ships today — 13 tables, 69,683 rows — but has not shipped since 2026-08-06

These pass the gate. They are absent from `dist/` and from `cedar_press.db` only
because **script 87 has not been run since 2026-08-06 17:54** and script 25 has
not been run since 2026-08-06 14:29.

| table | rows |
|---|---:|
| `ca_gaming_payments.csv` | 40,164 |
| `digital_gaming_revenue.csv` | 10,661 |
| `fl_gaming_payments.csv` | 9,756 |
| `gaming_capacity_official.csv` | 6,461 |
| `gaming_device_observations.csv` | 1,326 |
| `state_gaming_observations.csv` | 494 |
| `gaming_decision_events.csv` | 265 |
| `ca_gaming_facilities_official.csv` | 245 |
| `digital_gaming_relationships.csv` | 154 |
| `gaming_manufacturer_facts.csv` | 62 |
| `loyalty_program_property.csv` | 48 |
| `seminole_bond_disclosures.csv` | 29 |
| `loyalty_programs.csv` | 18 |
| **total** | **69,683** |

### Blocked by the gate — 29 tables, 33,817 rows

These are silently skipped. `87` increments a counter named
`"skipped: not a documented dataset"` and **never prints which file it skipped**.
That is why this has been invisible for twenty days.

| table | rows | facilities | tribes | best group | score | needs 0.60 |
|---|---:|---:|---:|---|---:|---|
| `gaming_revenue_bounds.csv` | 13,803 | 694 | 260 | `07e_fl_gaming` | 0.37 | no block |
| `gaming_game_finder_observations.csv` | 6,851 | 4 | 2 | `07e_fl_gaming` | 0.29 | **fragment is a 5-var stub** |
| `nigc_region_assignments.csv` | 2,438 | 772 | 275 | `13_admin_regions` | 0.55 | no block |
| `gaming_property_locations.csv` | 2,212 | 751 | — | `05_entities` | 0.22 | no block |
| `fac_audit_gaming_disclosures.csv` | 1,521 | — | 70 | `07e_fl_gaming` | 0.42 | no block |
| `gaming_ordinances.csv` | 1,155 | — | 298 | `16_digital_gaming` | 0.11 | **fragment exists — 1.00** |
| `gaming_employment_observations.csv` | 769 | 425 | 204 | `07f_gaming_device_observations` | 0.47 | no block |
| `gaming_properties.csv` | 774 | 774 | 275 | `07_gaming` | 0.39 | no block |
| `gaming_property_federal_traces.csv` | 774 | 774 | 275 | `07_gaming` | 0.15 | no block |
| `gaming_property_coverage.csv` | 774 | 774 | 275 | `07_gaming` | 0.21 | no block |
| `gaming_vendor_tribal_licenses.csv` | 740 | — | 51 | `07d_california_gaming` | 0.27 | no block |
| `nigc_declination_letters.csv` | 327 | — | — | `07d_california_gaming` | 0.07 | no block |
| `gaming_financing_events.csv` | 293 | — | — | `07d_california_gaming` | 0.11 | no block |
| `gaming_ordinance_ocr.csv` | 263 | — | 135 | `15_tribal_tax` | 0.17 | **fragment exists — 0.78** |
| `gaming_property_site_observations.csv` | 262 | 72 | 54 | `14_state_gaming` | 0.54 | **fragment is a 6-var stub** |
| `nigc_regional_ggr.csv` | 198 | — | — | `13_admin_regions` | 0.22 | no block |
| `gaming_decision_compact_join.csv` | 138 | — | 95 | `07_gaming` | 0.56 | no block |
| `gaming_projections.csv` | 116 | — | 2 | `07_gaming` | 0.27 | no block |
| `gaming_source_claims.csv` | 113 | — | — | `12_resources` | 0.20 | no block |
| `gaming_field_coverage.csv` | 101 | — | — | `16_digital_gaming` | 0.29 | no block |
| `wa_machine_allocations.csv` | 75 | — | 29 | `07f_gaming_device_observations` | 0.50 | no block |
| `gaming_property_labor_demand.csv` | 43 | 17 | 14 | `07d_california_gaming` | 0.43 | **fragment is a 2-var stub** |
| `gaming_mitigation_agreements.csv` | 24 | — | 2 | `01_deals` | 0.10 | no block |
| `nigc_revenue_bands.csv` | 20 | — | — | `07g_gaming_manufacturer_facts` | 0.24 | no block |
| `gaming_project_facilities.csv` | 19 | — | — | `07_gaming` | 0.23 | no block |
| `gaming_property_universe_events.csv` | 10 | — | — | `12_resources` | 0.17 | no block |
| `gaming_game_finder_systems.csv` | 3 | — | — | `08_compacts` | 0.12 | no block |
| `fac_audit_sefa_gaming_programs.csv` | 1 | — | 1 | `07d_california_gaming` | 0.25 | no block |
| `wa_machine_transfers.csv` | 0 | — | — | — | 0.33 | empty by design |
| **total** | **33,817** | | | | | |

### Staged in `review/`, never promoted — 10,766 rows

Not lost, but not moving either. The largest blocks:

| file | rows | what it is |
|---|---:|---|
| `compact_parse_unresolved_2026-08-07.csv` | 2,402 | compact terms held for a ruling |
| `gaming_property_site_refused_2026-08-12.csv` | 1,621 | website numbers refused as possible counts — recall is recoverable |
| `nigc_roster_diff_2026-08-06.csv` | 914 | NIGC roster vs Cedar universe |
| `employment_osha_unmatched_2026-08-07.csv` | 711 | **1,879 OSHA filings on 711 establishments** sharing a distinctive token with a Cedar property |
| `gaming_property_triage_2026-08-06.csv` | 774 | property triage |
| `fac_unresolved_auditees_2026-08-12.csv` | 540 | FAC auditees the spine does not hold |
| `gaming_game_finder_signals_2026-08-12.csv` | 447 | 58 hosts with finder-shaped language, unharvested |
| `gaming_locations_geocode_conflicts_2026-08-12.csv` | 422 | 189 conflicts exceed 5 km |
| `gaming_capacity_official_unresolved_*.csv` | 491 | regulator names not matched to a property |
| `ordinance_compact_diff_2026-08-{12,26}.csv` | 678 | ordinance/compact reconciliation |
| `gaming_additions_2026-08-06.csv` | 140 | **140 NIGC properties Cedar does not hold**, behind `do_not_append_without_ruling` |
| `gaming_nigc_additions_2026-08-26.csv` | 147 | written today by the concurrent roster agent |
| others (34 files) | 1,479 | |

### Stranded in `data/interim/` — parsed, then held

One gaming source was fully extracted and deliberately parked short of
`data/clean/`:

| file | rows | why |
|---|---:|---|
| `103_sdf_local_mitigation_unverified.csv` | **1,292** | CA SDF local-mitigation line items. Parsed, then withheld — the items do not foot against CGCC's printed per-county totals (a three-column Amount Paid / Allocated / Reverted layout beside a free-text purpose column defeats the leftmost-money rule). Staged "so the next pass starts from the parse rather than from the retrieval." |
| `105_litigation_figures.csv` | 48 | Florida court-record dollar figures, all 48 from one appendix |
| `103_zone_log.csv` / `105_zone_log.csv` | 3,076 | per-table extraction and footing records |
| `142_crawl_manifest.csv` | 2,307 | the website crawl trail — the only provenance record for `gaming_property_sites/` |

The 1,292 SDF rows are the only gaming extraction sitting in `interim/` with real
content and no clean-table home. It is a documented hold, not a leak.

### Deliberately killed, with the reason documented — 839 rows

These are the healthiest entries in this audit. Nothing here needs recovering;
they are recorded so nobody rebuilds them.

| what | rows | why it was killed |
|---|---:|---|
| **California derived revenue** | **795** | Joining the 51 `INVERTIBLE_FLAT_RATE` CA rates to RSTF receipts produced 795 publishable-looking figures. Every rate is a **marginal** base. San Manuel FY2025-26 would have shipped `$19,000,000 / 15% = $126.7M` as annual Net Win — wrong by an order of magnitude, with a correct citation. **0 derived revenue rows published.** |
| **Florida bounded derived revenue** | **44** | Built, published in a draft, then withdrawn. `Net Win <= payment / rate_min` is true of the **obligation**; EDR publishes **receipts**, which lag by a fiscal year. FY2013/14 receipts implied a $1.978bn ceiling against EDR's own $2.098bn Net Win — bound violated. All 44 withdrawn. |
| SEC capacity windows | 1,168 refused | area-of-property, forward-looking, competitor property, ambiguous issuer — each written to `agent_bond_sec_rejected_2026-08-07.csv` with its reason |
| MGCB `cumulative_prior` / `ltd_total` | withheld | double-count risk; only the seven explicit year columns publish |
| Arizona Machine Compliance figure | withheld | interleaved infographic columns; column membership unresolvable from the text layer |
| `bia_compact_properties_geocoded_v2.csv` | 766 refused | 590 of 766 `No_Match`; addresses regex-extracted from compact PDFs (`11 Supreme Court`) |

### Graveyard — nothing gaming was ever killed

`graveyard/` holds only pre-build snapshots: three `gaming_facilities`
pre-temporal/pre-ruling copies (774 each), two `gaming_facility_metrics`
(65,223), two `gaming_projections` (116), and a partial ordinance run.
**No gaming source was ever deliberately retired.** There is nothing to
resurrect and no undocumented kill.

---

## PART 3 — THE MECHANISM, TESTED NOT ASSUMED

Five candidate causes were named. Three are real, two are not.

### MECHANISM 1 (primary) — the codebook fragment migration cut the shipping wire

This is the whole story, and the irony is that it was caused by *fixing* the
clobbering problem.

On 2026-08-07 `codebook_master.csv` was clobbered three times in one day (a
22-row `15_tribal_tax` block lost, 34 rows dropped twice). The correct fix was
built: `code/cedar_codebook.py`, per-dataset fragments under
`data/clean/codebook/`, and the master becomes a derived concatenation. Every
gaming build from that day forward obeyed it. `118` says so in its own docstring:

> `data/clean/codebook/07f_gaming_ordinances.csv    (FRAGMENT only)`
> `spine and codebook_master.csv are read-only or untouched here.`

The device build, the digital build and the property-site build all say the same
thing in their logs. **They were right to.**

But `87_build_dataset_notes.py` still reads `codebook_master.csv`, and
**nothing ever ran `cedar_codebook.py build` to regenerate it from the
fragments.** So:

    a build writes a correct, complete fragment
      -> the master never learns about it
        -> 87 finds no matching block
          -> the file scores under 0.60
            -> "skipped: not a documented dataset", no filename printed
              -> no notes.json, no bundle, no ship

**And the rebuild cannot succeed even if someone runs it.** Measured today:

| | |
|---|---:|
| `codebook_master.csv` | 1,647 rows, 34 datasets |
| fragments | 1,554 rows, 29 datasets |
| in master, no fragment (**would be LOST**) | **262 keys** |
| in fragments, not in master (**never shipped**) | **131 keys** |

`build()` refuses any rebuild that shrinks the codebook — correctly, that is the
bug it exists to prevent. So `cedar_codebook.py build` prints
`REFUSING: … losing 93 rows` and stops. **The codebook is deadlocked.** Six
blocks live only in the master (`04b_section_106_consultation` 58,
`17_grantmaker_funding_flows` 43, `04e_schedule_i_grants` 30, and the four
`13_*` FOIA/correspondence blocks, 92 total); six live only as fragments
(`07f_gaming_ordinances` 70, `07h_gaming_device_observations` 19,
`07i_gaming_manufacturer_facts` 20, `07j`/`07k`/`07l` 13, `02b_subawards` 8).

There is a second latch behind the first: **`02b_subawards_api.csv` has a
different 9-column schema** (`source`, `added_by`, `added_date`) from the other
27 fragments' 10 columns. `build()` takes its field list from the first
fragment alphabetically and writes with a default `DictWriter`, so even
`--force` raises on the extra keys.

**Block-letter collision.** `07f` means `gaming_device_observations` in the
master and `gaming_ordinances` in the fragments. Script `117` registered `07f`
for devices in the master on 2026-08-07; `118` claimed `07f` for ordinances in
the fragment dir on 2026-08-12; `117`'s block was later re-filed as `07h`/`07i`
in fragments but the orphaned `07f`/`07g` rows still sit in the master. **This is
the script-number collision problem reproduced inside the codebook namespace.**
For the record, `ls code/` shows **31 colliding script numbers** today, including
`142`, `148`, `149`, `153`, `154` and `156`.

### MECHANISM 1b — four gaming codebooks were WRITTEN and never registered

This is the same defect one step earlier, and it explains the single largest
blocked table.

`docs/codebooks/` contains **five gaming codebooks that exist only as prose
markdown**, because scripts `84`, `91`, `100` and `106` each followed the
precedent of writing their own file rather than registering with `41`:

| codebook file | documents | rows now blocked |
|---|---|---:|
| `07e_revenue_bounds.md` | `gaming_revenue_bounds`, `nigc_revenue_bands` | **13,823** |
| `07b_nigc_regions.md` | `nigc_region_assignments`, `nigc_regional_ggr` | **2,636** |
| `07c_gaming_employment.md` | `gaming_employment_observations` | **769** |
| `07d_nigc_declination_variables.md` | `nigc_declination_letters` | **327** |
| | **total** | **17,555** |

**17,555 of the 33,817 blocked rows — 52% — already have a written codebook.**
The gate cannot see it, because the gate reads `codebook_master.csv` and these
were never added to `41_build_codebooks.py`'s `DATASETS` dict. Verified: the
string `07e_revenue_bounds` appears **zero times** in `code/41_build_codebooks.py`.

And `REVENUE_BOUNDS_LOG.md` says so, in as many words, on the day it happened:

> "**One step is deliberately left open.** … It is NOT yet registered in
> `code/41_build_codebooks.py`'s `DATASETS`, so the two files do not appear in
> `codebook_master.csv`. **That file was being rewritten by another agent's run
> of script 41 while this build was running, and editing 41 concurrently would
> have collided.** Adding `"07e_revenue_bounds": [...]` and re-running 41 is the
> whole remaining job."

That agent made the right call on 2026-08-07 — 41 overwrites the master wholesale
and a concurrent edit would have lost someone's block. It deferred one line of
work to avoid a collision, wrote down exactly what was owed, and **the one line
was never written.** 13,803 rows have been invisible for nineteen days as a
result.

**The codebook namespace has its own collisions**, for the same reason the script
numbers do: `07d` is both `07d_california_gaming.md` and
`07d_nigc_declination_variables.md`; `07e` is both `07e_fl_gaming.md` (script 105)
and `07e_revenue_bounds.md` (script 106), **both dated 2026-08-07**. That is why
`gaming_revenue_bounds.csv` best-matches the *Florida* block at 0.37 — its own
number was already taken.

### MECHANISM 1c — the clobbering, for the record

The lost-update race was real, and the timeline is preserved in
`STATE_GAMING_PULL_LOG.md`:

    18:43:23  script 108 snapshots codebook_master.csv       1,099 rows
    18:43:42  script 107 snapshots codebook_master.csv       1,121 rows
              (a third agent added 15_tribal_tax in that 19-second window)
    18:43:42  script 107 writes 107 + everything it saw
    18:58:00  script 108 writes 108 + everything IT saw      1,174 rows
              -> 15_tribal_tax   (22 rows)  GONE
              -> 14_state_gaming (31 rows)  GONE

Both blocks were later restored by hand, and both are present today. **The
clobbering did not cause the gaming loss — the *migration away from* the
clobbering did.** Everyone did the right thing; nobody owned the second half.

### MECHANISM 2 — the shipping step is written down and never done

`STATE_OF_THE_LAND_2026-08-07.md`, section 7, "recommended next session, in
order", item **6 of 6**:

    6. Re-run 62 (gate), 87 (notes contracts), 102 (coverage), 110 (views)

It was never run. Mtimes:

| artefact | last written |
|---|---|
| `dist/manifests/*.json` | **2026-08-05 15:36** |
| `dist/cedar_press.db`, `cedar_press_master.xlsx` | **2026-08-06 14:29** |
| `dist/notes_index.json`, `dist/07_gaming/*` | **2026-08-06 17:54** |

Twenty days and roughly twenty gaming builds later, nothing has re-run. And
`AGENTS.md` mentions script 87 **once**, in passing, in a sentence about where
presentation lives. **There is no rule anywhere in the project that says a build
is not finished until it ships.** Every gaming build log ends with its own row
counts and a regression check; none of them ends with a bundle.

### MECHANISM 3 — two hardcoded allowlists nobody has touched since 2026-08-05

Even a full re-run would not fix everything, because two of the three
publication paths do not enumerate `data/clean/` at all.

- **`code/25_build_publication_layer.py`** — a literal `TABLES` list. It contains
  exactly two gaming entries: `gaming_decisions ← gaming_land_decisions.csv` and
  `gaming_facilities ← gaming_facilities.csv`. That is why `cedar_press.db` holds
  26 tables and only 3 are gaming.
- **`code/27_build_dataset_manifests.py`** — a literal `SPEC` dict with a single
  `"gaming"` bundle pointing at `gaming_land_decisions.csv`.
- **`code/41_build_codebooks.py`** — a hardcoded `DATASETS` dict covering 19
  groups and **7 gaming files**, and it writes `codebook_master.csv` in `"w"`
  mode, a full overwrite. **This is a loaded gun.** Running `41` today would
  delete 15 dataset blocks from the master, including `14_state_gaming`,
  `16_digital_gaming`, `07f`/`07g`, `15_tribal_tax`, `04b_section_106` and every
  `13_*` block. Do not run it until the fragment path owns the master.

### MECHANISM 4 — the licence gate is documented but not implemented

`code/87_build_dataset_notes.py` line 191 defines `LICENSED_SOURCE_FILES` with
36 lines of comment ending *"This list is a HARD GATE, not a warning."* Line 200
defines `LICENSED_COLS = {"casino_city_id"}`.

**Neither name is referenced anywhere else in the file.** `main()` filters only
on `_`-prefixed names and two literal filenames. The gate is a dead constant.

The consequence is measurable in `dist/` right now:

| | |
|---|---|
| `gaming_property_capacity_history.notes.json` | exists — **64,181 rows, 100% Casino City** |
| `gaming_facility_metrics.notes.json` | exists — **65,223 rows, Casino City derived** |
| `casino_city_id` in `gaming_facilities` published codebook | **yes** |
| `gaming_properties.csv` (774 rows, 54 cols, **no licensed column**) | **skipped** |

`GAMING_SPEC_RECONCILIATION.md` states this is "already enforced as a hard gate…
so the vendor panel gets no notes contract and therefore cannot ship."
`GAMING_LOCATION_LAYER.md` proposes extending the same gate. **Both are relying
on code that does not run.** This is a licensing exposure, not just a data
problem, and it is the highest-severity finding in this audit.

### RULED OUT — a build superseded by a later script that dropped columns

Tested directly on six before/after pairs. Every gaming supersession is
**additive**:

| file | rows | columns |
|---|---|---|
| `gaming_ordinances` (pre-153 → now) | 1,155 → 1,155 | 58 → **70** |
| `gaming_ordinance_ocr` (pre-153 → now) | 2 → **263** | 14 → **18** |
| `gaming_facilities` (pre-temporal → now) | 774 → 774 | 92 → **102** |
| `gaming_financing_events` (pre-100 → now) | 145 → **293** | 33 → **38** |
| `gaming_source_claims` (pre-100 → now) | 113 → 113 | 22 → **25** |
| `nigc_declination_letters` (pre-100 → now) | 327 → 327 | 47 → **60** |

**Zero columns dropped in any pair. Zero rows lost.**

### RULED OUT — clobbering of the gaming data tables

The `codebook_master.csv` clobbering was real and is documented. It did **not**
propagate to gaming data tables. Every recent gaming build explicitly declares a
do-not-edit list and writes only its own outputs, and the two clobbering
incidents that did occur were caught and fixed in the same session (`119`'s
`save_manifest()` overwriting md5s on a `--skip-fetch` run; `142`'s killed
process losing manifest rows while the HTML survived).

### RULED OUT — joins silently dropping rows

Where a join could not resolve, the build wrote the unresolved rows to `review/`
rather than dropping them: 10,766 gaming rows are staged and accounted for.
Where a coordinate or a count was doubtful it was refused with a reason
(1,621 site-metric refusals, 133 revenue-bound refusals, 22 device refusals).
The extraction discipline in this project is very good. **That is precisely why
the shipping failure is so expensive** — high-quality work is accumulating
behind a closed door.

---

## PART 4 — THE SOURCES HE NAMED, ONE BY ONE

| what he remembers | is it here? | current fate |
|---|---|---|
| **their websites** | **yes** — 1,749 pages, 144 hosts, 357 MB | built into 262 site observations + 43 labor-demand rows; **both blocked at the gate**. 1,621 refusals recoverable in `review/`. 281 open properties never crawled. |
| **promotional material** | **yes** — loyalty/rewards pages, game finders, marketing pages | 18 loyalty programmes + 48 programme-property rows **ship**; 6,851 game-finder observations **blocked**; 447 unharvested signals in `review/` |
| **slot machine info** | **yes** — SEC manufacturer filings, WA allocations, WI LFB, OK OMES, AZ ADG | 1,326 device observations + 62 manufacturer facts **ship**; 75 WA allocations **blocked** |
| **OSHA** | **yes** — ITA 300A, CY2016–2025, 3,189,050 establishment-years | 364 rows matched into `gaming_employment_observations.csv` (769 total) — **blocked at the gate**; 1,879 filings on 711 establishments staged in `review/` |
| **retirement data** | **not in Cedar Press** | Form 5500 lives in `Desktop\4wheeler\casino_employment_validation` (10,733 resolved rows). A 2,046-row gaming subset reached `data/staging/` **today** via `code/156`. NLRB, PPP, QCEW, IMPLAN, impact studies have not crossed at all. |
| "a bunch of stuff" | **yes** — 15 further families | see Part 1 |

---

## PART 5 — RECOVERY, RANKED BY VALUE

**Tier 0 — do this first, it is a licensing exposure not a backlog item.**

0. **Implement `LICENSED_SOURCE_FILES` and `LICENSED_COLS` in `87`.** Four lines.
   Then delete `dist/07_gaming/gaming_property_capacity_history.*` and
   `gaming_facility_metrics.*`, and drop `casino_city_id` from the
   `gaming_facilities` notes contract. **129,404 rows of licensed vendor panel
   currently have a live shipping contract.**

**Tier 1 — mechanical, no rulings, unblocks the most rows per unit of effort.**

1. **Unstick the codebook.** Split the six master-only blocks into fragments
   (`cedar_codebook.py split` is non-destructive and does exactly this), normalise
   `02b_subawards_api.csv` to the 10-column schema, resolve the `07f` collision,
   then `build`. Fixes the deadlock and immediately makes
   **`gaming_ordinances` (1,155 rows, 298 tribes) and `gaming_ordinance_ocr`
   (263)** shippable — their fragments already score 1.00 and 0.78.
2. **Re-run the shipping chain: `62` → `87` → `102` → `110` → `25` → `27`.**
   Releases the **69,683 rows already past the gate**, including CA payments
   (40,164), digital revenue (10,661), FL payments (9,756) and official capacity
   (6,461). This is the single highest-yield action in the audit.
3. **Make `87` name what it skips.** Change
   `stats["skipped: not a documented dataset"] += 1` to print the filename and
   its best score. Twenty days of invisible loss becomes one line of output.
   Consider making 87 **fail** on a `data/clean/*.csv` with no codebook block,
   rather than skipping it.

**Tier 1b — the four codebooks that already exist. 17,555 rows for four
registrations.**

These need no new writing. The codebook is written; it just is not in the
machine-readable master. Convert each `docs/codebooks/07*.md` into a fragment
under `data/clean/codebook/` (or register it in 41 once 41 is safe), resolving
the `07d` and `07e` number collisions on the way.

4. **`07e_revenue_bounds` → `gaming_revenue_bounds` (13,803 rows, 694
   properties, 260 tribes) + `nigc_revenue_bands` (20).** The single largest
   blocked table, and `REVENUE_BOUNDS_LOG.md` already states the exact one-line
   fix. Highest rows-per-keystroke in the whole audit.
5. **`07b_nigc_regions` → `nigc_region_assignments` (2,438, 772 properties) +
   `nigc_regional_ggr` (198).**
6. **`07c_gaming_employment` → `gaming_employment_observations` (769 rows, 425
   properties, 204 tribes).** The OSHA + LODES layer he asked about by name.
7. **`07d_nigc_declination_variables` → `nigc_declination_letters` (327).**

**Tier 2 — write new codebook blocks; ~16,300 rows behind these.**

8. **`gaming_game_finder_observations` (6,851)** — replace the 5-variable stub
   fragment with a real 31-variable block. This is the slot-machine-info layer
   from the operators' own finders.
9. **`gaming_property_locations` (2,212 rows, 751 properties)** — the
   539-publishable-coordinate win `START_HERE.md` lists as a headline
   achievement. It ships nowhere. **Needs a row-level filter as well as a
   codebook block: 741 of 2,212 rows are `publishable = N` and 592 of those are
   Casino City addresses.** `GAMING_LOCATION_LAYER.md` already specifies this.
10. **`fac_audit_gaming_disclosures` (1,521 rows, 70 entities)** — the machine
    participation seam, including the two exact Robinson Rancheria figures.
11. **`gaming_ordinance_ocr` (263)** — fragment already scores 0.78; rides along
    with item 1.
12. **`gaming_properties` (774)** — and once it ships, the vendor
    `gaming_facilities` should stop shipping in its current form.
13. **`gaming_property_site_observations` (262) + `gaming_property_labor_demand`
    (43)** — replace the 6- and 2-variable stubs. This is the tribal-website
    layer.
14. The remaining 16 blocked tables (~4,000 rows).

**Tier 3 — cross the repository boundary.**

15. **Rule the two Form 5500 questions** (`FORM5500_ACTIVE_PARTICIPANTS` as a
    `MeasurementType`; tribe-level employment rows with no `facility_id`) and
    promote `data/staging/gaming_employment_form5500_staged.csv` — **2,046 rows,
    140 tribes, 2009–2025, ~25 new tribes per year.**
16. **Inventory the rest of `4wheeler/casino_employment_validation`** — NLRB
    (250 elections), PPP (1,069), QCEW (969 files), SEC employment sentences
    (1,736), IMPLAN (42), impact studies (34). Decide per source whether it
    belongs in Cedar Press. Right now the decision is being made by accident.

**Tier 4 — rulings and backlogs already queued, 10,766 rows plus an OCR pile.**

17. **264 image-only ordinance scans (23% of the archive)**, concentrated in the
    1990s–2000s. Their provisions are an OCR backlog, not an absence. The
    declination build closed an identical ceiling with `rapidocr-onnxruntime`;
    `code/150_run_ocr_overnight.py` is resumable and stood at 27 of 263.
18. The 140 staged NIGC property additions + 147 more staged today.
19. The 711 OSHA establishments (1,879 filings) in
    `review/employment_osha_unmatched_2026-08-07.csv`.
20. The 422 geocode conflicts (189 over 5 km, incl. Northern Edge Navajo at
    492 km).
21. The 1,292 CA SDF local-mitigation line items in `data/interim/` — the parse
    is done; only the footing is owed.
22. Write `_SOURCE_MANIFEST.csv` for `gaming_official/` and
    `gaming_property_sites/` — 1.3 GB and 2,597 files with no md5 trail.
    `data/interim/142_crawl_manifest.csv` (2,307 rows) is most of the second one
    already.

---

## PART 6 — WHAT WAS ACTED ON, 2026-08-26

Diagnosis ran first; the following was then authorised and done. **The shipping
chain was deliberately NOT run** — two agents were live, one rebuilding the
gaming collection against NIGC and state regulators, one rebuilding
`coverage_audit.csv`. `gaming_facilities.csv` moved 774 → 784 and
`gaming_facility_metrics.csv` 65,223 → 68,211 *during this audit*. The chain is
staged in `docs/SHIPPING_RUNBOOK.md`.

### 6.1 The licence gate is now a gate

`code/87_build_dataset_notes.py` — `LICENSED_SOURCE_FILES` and `LICENSED_COLS`
were declared under 36 lines of comment calling them a HARD GATE and referenced
nowhere. Both are now wired into `main()`:

- a licensed **file** is refused before any other test, **named on stdout**, and
  any contract an earlier run left behind is deleted on sight;
- a licensed **column** is stripped from the codebook of a file that does
  publish, and recorded as `licensed_columns_withheld` in the notes contract so
  the bundler can drop it from the CSV — stated as a column rather than deleted
  silently, which is this project's own no-silent-exclusions rule applied to
  itself;
- `duns` is matched by **pattern**, not equality, so `recipient_duns` and
  `parent_duns` cannot survive by being prefixed.

### 6.2 What was purged from `dist/`

All of it moved to `graveyard/2026-08-26_licensed_dist_purge/`, not deleted —
the licence permits internal QA, so the record is kept out of the shipping
directory rather than destroyed.

| removed | detail |
|---|---|
| `dist/07_gaming/gaming_property_capacity_history.notes.json` + `.NOTES.md` | **64,181 rows**, 100% Casino City panel |
| `dist/07_gaming/gaming_facility_metrics.notes.json` + `.NOTES.md` | **65,223 rows**, Casino City derived |
| `casino_city_id` from `gaming_facilities.notes.json` | codebook 82 → 81 vars; `licensed_columns_withheld` set |
| `casino_city_id` row from `gaming_facilities.NOTES.md` | 167 → 166 lines |
| two entries from `dist/notes_index.json` | 53 → 51 datasets |
| **`dist/cedar_press.db`** | **quarantined** — see below |
| **`dist/cedar_press_master.xlsx`** | **quarantined** — same DB content |
| `dist/schema.sql` | quarantined — its DDL declares `casino_city_id` and `recipient_duns`, describing a schema that no longer ships. Regenerated by step 6. |

**The database was a bigger exposure than the notes contracts.** Measured before
removal:

| table.column | populated |
|---|---:|
| `funding_transactions.recipient_duns` | **404,236 of 476,924** |
| `gaming_facilities.casino_city_id` | **595 of 774** |

`START_HERE.md` and the shipped `TERMS` section both state DUNS is never
published by Cedar Press. **The shipping database contradicted the terms it
shipped under, on 404,236 rows.** Both bundles were 20 days stale and are
regenerated by step 6 of the runbook, so quarantining them costs nothing and
closes the exposure now rather than at the next release.

`match_status` was deliberately **kept**. Its values name the vendor
(`casino_city_only`) but it is Cedar's own provenance taxonomy, not the vendor's
key — the same reasoning that keeps `assignment_basis` public in
`13_admin_regions`. Naming what KIND of fact a row is does not disclose how the
row was made. An over-broad first pass removed it and was reverted.

### 6.3 The gate now names what it drops

`87` printed `"skipped: not a documented dataset"` with a count and no
filenames. It now prints, every run:

- **`LICENCE GATE — n file(s) REFUSED, by name`**, with the reason;
- **`NOT SHIPPED`** — every clean table with no codebook block, with its score
  and its best-matching block;
- **`SHIP RATE: x of y rows (z%)`**, plus `dist/_ship_rate.csv`, a per-file
  ledger of `NOTES_WRITTEN` / `NO_CODEBOOK` / `LICENSED_REFUSED`;
- **`[undefined]`** — tables shipping public variables with no description,
  because registering a block makes a table *shippable*, not *documented*.

`25` gained the same `SHIP RATE` line and names every table it could not
publish. `27` now checks `SPEC` against the registry and names every documented
dataset with no manifest — a validator that only validates what it was told
about cannot find an omission, which is why it reported `all valid: True` while
holding one gaming entry against 47 gaming tables.

### 6.4 The codebook deadlock is cleared

New tool: **`code/cedar_register_codebook.py`** (unnumbered on purpose — 31
script numbers already collide).

`reconcile` made the fragments a superset of the master:

- **8 master-only blocks written to fragments**, one file at a time —
  deliberately *not* `cedar_codebook.py split`, which rewrites every fragment
  from the master and would have downgraded `16c_loyalty_programs` from the
  fragment's 32 vars to the master's stale 31;
- **`02b_subawards_api.csv` normalised 9 → 10 columns** — the second latch.
  `build()` takes its field list from the first fragment alphabetically and
  writes with a default `DictWriter`, so this raised on `source`/`added_by`/
  `added_date` and `--force` did not clear it;
- **`07f_gaming_device_observations` and `07g_gaming_manufacturer_facts`
  retired** — verified byte-identical variable sets to `07h_`/`07i_`. Script 117
  registered `07f` for devices, 118 later claimed `07f` for ordinances, 117's
  block was re-filed as `07h`/`07i`, and two orphans stayed behind. The
  script-number collision problem, inside the codebook namespace.

Result: `in master, no fragment: 0`. `cedar_codebook.py build` then took the
master **1,647 → 2,005 rows across 43 fragments**, and `check` now prints
`SAFE — a rebuild loses nothing`.

### 6.5 The four orphaned codebooks are registered

`register` generated blocks **from each file's own header** — so a codebook
cannot drift from the file it documents, script 41's rule kept — taking
descriptions from the hand-written markdown, type and fill from the data, and
access tier by *importing* 41's `access_tier` rather than copying it.

New keys avoid `07d`/`07e`, both already taken by `07d_california_gaming` and
`07e_fl_gaming` and both minted on 2026-08-07.

| new block | documents | rows | vars | with a written definition |
|---|---|---:|---:|---|
| `07p_revenue_bounds` | `gaming_revenue_bounds`, `nigc_revenue_bands` | **13,823** | 42 | 42 / 42 |
| `07m_nigc_regions` | `nigc_region_assignments`, `nigc_regional_ggr` | **2,636** | 40 | 40 / 40 |
| `07n_gaming_employment` | `gaming_employment_observations` | **769** | 19 | 19 / 19 |
| `07o_nigc_declinations` | `nigc_declination_letters` | **327** | 60 | **13 / 60** |

**`nigc_declination_letters` is shippable and not yet documented.** Its markdown
covers only the 13 columns script 100 added, not the 47 script 91 built; 45 of
those are public tier. No definitions were invented to close the gap — that
would be exactly the fabrication this project refuses. `87` now names the file
in an `[undefined]` line, and the runbook says to write the definitions or tier
the columns internal before it reaches a subscriber.

### 6.6 Measured effect

| | before | after |
|---|---:|---:|
| gaming rows past the notes gate | 69,683 | **88,656** |
| gaming rows blocked | 33,817 | 14,844 |
| **newly unblocked** | | **18,973** |
| tables `25` would put in the database | 26 (2 gaming) | **117 (22 gaming)** |
| codebook master rows / fragments | 1,647 / 1,554, deadlocked | **2,005 / 2,005, in sync** |
| licensed files with a shipping contract | 2 | **0** |
| populated DUNS in a shipping artefact | 404,236 | **0** |

Nine tables moved from blocked to shipping: `gaming_revenue_bounds` (13,803),
`nigc_region_assignments` (2,438), `gaming_ordinances` (1,155),
`gaming_employment_observations` (769), `nigc_declination_letters` (327),
`gaming_ordinance_ocr` (263), `nigc_regional_ggr` (198), `nigc_revenue_bands`
(20). All now score 1.00 except ordinance OCR at 0.78.

**Nothing in `data/` was modified except `codebook_master.csv` and the codebook
fragments**, both backed up to `graveyard/2026-08-26_codebook_pre_reconcile/`.

### 6.8 THE WEBSITE LAYER WAS RE-MINED — later the same day

*Added by a later agent. Full log: `docs/GAMING_PROPERTY_SITE_REMINE_2026-08-26.md`.
This is the pointer so Part 1 row 1 and Part 4 row 1 are not read as current.*

Part 4 of this audit answers *"their websites"* with **"262 site observations +
43 labor-demand rows"** off 1,749 pages and 357 MB, and names two open items:
**1,621 refusals recoverable in `review/`** and **281 open properties never
crawled**. Both were worked, and the corpus re-mined for the four kinds of fact
`142` never looked for.

| | before | after |
|---|---:|---:|
| rows extracted from `gaming_property_sites/` | 262 + 43 + 66 | **+ 959** |
| …employment claims (any non-vendor source) | **0** | **29** |
| …ownership / management assertions | 0 | 288 |
| …date assertions | 0 | 292 |
| …loyalty tier rows | 66 | +65 (22 programmes, 20 hosts) |
| the 1,621-row refusal pile | 1 generic reason, never re-read | **305 distinct candidates adjudicated: 231 RECOVERED, 45 confirmed with 7 NAMED reasons, 29 left ambiguous** |

**The employment line is the one that matters.** Measured today: all **10,122**
`metric = employees` rows in `gaming_facility_metrics.csv` come from **one**
source, the Casino City panel, which may never publish. The 29 operator-published
claims are the only per-property employment evidence Cedar holds that can ship.

Two new `cedar_domain.MeasurementType` terms carry the discipline —
`SELF_PUBLISHED_MARKETING_CLAIM` and `SELF_PUBLISHED_EMPLOYMENT_CLAIM`, both
`is_observed`, **both in `NEVER_PROMOTES_TO_ACTIVE`**, with the verbatim
sentence and a bound direction on every row.

**Everything is staged to `data/staging/` and `review/`. Nothing was merged into
`data/clean/`**, so no new table and no movement in any shipping counter.

---

### 6.7 The facility hub was wired to the entity — later the same day

*Added by a later agent. See `docs/GAMING_FACILITY_HUB_LINKAGE_2026-08-26.md`
for the full log; this is the pointer so Part 1's inventory is not read as
current.*

Script 159 keyed `gaming_facility_metrics.csv` in the morning. Scripts
`164`/`165` then keyed **everything else that hangs off a `facility_id`** —
capacity history, game finders, devices, websites, labor demand, loyalty,
digital, employment, universe events and the coverage profile: **85,107 rows,
`entity_id` 0 → 80,318 (94.4%)**, tier INHERITED from the facility row on every
one, no coordinate used by any rung, 173 rows to `review/`.

Two corrections this pass makes to the tables above:

- **`gaming_property_coverage` is 784 rows, not 774**, and it counted **eight of
  fourteen** facility-level hub sources. Six more were added to
  `102_build_coverage_profile.py` (game finder, website, labor demand, device,
  loyalty, vendor metrics) plus two tribe-level (digital gaming, digital
  revenue). STRONG-evidence properties 662 → **713**.
- **`nigc_declination_letters` and `gaming_financing_events` were reported at
  0.0% coverage for nineteen days because `102` read a column named `tribe_id`
  that neither file has** — both key `tribe_entity_id`. Real coverage is
  **460 (58.7%)** and **400 (51.0%)** of properties. A named column that is
  absent and a source that is empty produced the same `0.0%`; `102` now fails
  loudly instead.

**`87`, `25`, `27` and the rest of `docs/SHIPPING_RUNBOOK.md` were still NOT
run.** This pass moved what a shipped row can be joined to, not the ship rate.

---

---

## SHIPPED IS PART OF DONE

The single sentence this audit exists to produce:

> **Every build log in this project ends by confessing its defects. Not one ends
> by asking whether the table can leave the building.**

The gaming logs are, genuinely, some of the most careful build documentation I
have read. Sources named with md5 and byte count. Refusals counted and
explained. Four typing errors caught before shipping and written down *with the
failing quote*. A bound built, published in a draft, and killed when the source
falsified it. A regression gate run before and after.

And then nothing. No line saying "this reached `dist/`", or "this did not, and
here is why." The word "ship" does not appear as a step in any of them.
`AGENTS.md` names script 87 once, in a sentence about where presentation lives.
The shipping step was written down exactly once, in
`STATE_OF_THE_LAND_2026-08-07.md` §7 as **item 6 of 6**, and carried forward
unread through twenty days and roughly twenty builds.

The result is a project that audits its **sources** constantly and its
**shipment** never. Coverage of what we collected: measured, tabled, ranked, in
a dozen documents. Coverage of what we delivered: **0.87%, for twenty days,
unnoticed** — because no number anywhere in the pipeline compared the two.

### The check that catches it

Now implemented in `87` and `25`, and it is deliberately the smallest possible
thing. **The chain has not been run — two agents are live — so this is the
shape of the output, not a transcript of one:**

```
SHIP RATE: <n> of <total> rows in data/clean reached a notes contract (<pct>%)
           <n> rows are in data/clean and in no bundle.
           dist/_ship_rate.csv has the per-file ledger.

NOT SHIPPED - <k> clean table(s) have no codebook block at >=0.60:
   0.54  gaming_property_site_observations.csv     262 rows   best block: 14_state_gaming
   0.29  gaming_game_finder_observations.csv     6,851 rows   best block: 07e_fl_gaming
   ...
```

The gaming figures it will report, measured today by re-implementing the gate
against the files rather than by running the chain: **88,656 of 103,500 rows
past the gate — 85.7%**, against **912 of 104,412 — 0.87%** actually in a
shipping artefact this morning. (The two denominators differ by exactly the 912
already-shipped rows, which the "past the gate" figure counts separately from
the 69,683 that passed but had nowhere to go.) Both are as-measured during the
audit; a live agent moved `gaming_facilities.csv` 774 → 784 while it ran, so
treat them as the shape of the gap, not as a closing balance.

Two properties make it work, and both were missing before:

1. **It compares rows-in-clean against rows-in-dist.** Every existing coverage
   report measures the source against the world. None measured the product
   against our own data. A ratio nobody computes is a ratio nobody checks.
2. **It names the files.** The old code counted its drops and printed only the
   number. A count is not actionable and does not accuse anyone of anything, so
   it scrolls past. A filename is a task. This is `START_HERE.md`'s own rule —
   *an interruption must not look like a completion* — applied to the script
   that decides what completion means.

`dist/_ship_rate.csv` makes it diffable between runs, so a **regression in ship
rate** becomes as visible as a regression in row counts, which script 62 has
guarded since day one.

### The rule to adopt

**A build is not finished when the table is written. It is finished when the
table can leave the building, or when a named line says why it cannot.**

Concretely, a build log should not be closed until it can state: rows written,
codebook block registered (name it), ship rate after the next chain run, and any
row-level or column-level filter the bundler must apply. Three of those four are
now printed automatically.

---

## THE SYSTEMIC CAUSE, PLAINLY

**Cedar Press treats "built" as done. Nothing in the project treats "shipped" as
part of done.**

Every gaming build log is excellent — sources named, md5s recorded, refusals
counted, defects confessed with the failing quote, regression gate run before and
after. Not one of them ends by asking whether the table can leave the building.
`AGENTS.md` names script 87 once and states no rule about it. The one place the
shipping step was written down —
`STATE_OF_THE_LAND_2026-08-07.md`, item 6 of 6 — has been carried forward unread
through twenty days and roughly twenty builds.

On top of that, publication is gated on `codebook_master.csv`, a file the project
**correctly stopped writing to** in order to fix a clobbering race, and never
finished the other half of the migration. The fix removed the writers; nothing
replaced the reader. So the gate now silently fails closed on everything built
after 2026-08-07, and it fails closed **without printing a filename**.

Three separate publication paths (notes contracts, the SQLite/xlsx layer, the
manifests) each maintain their own idea of what a dataset is — one derived, two
hardcoded — and all three disagree with `data/clean/`. A table has to be
registered in three places to ship, and there is no check anywhere that a clean
table is registered in any of them.

**And registration is the one job that concurrency makes unsafe.** Every shared
registry in this project — `codebook_master.csv`, `41`'s `DATASETS`, `25`'s
`TABLES`, `27`'s `SPEC` — is a single file that every build must edit. A careful
agent facing a concurrent writer does the right thing and defers: script 106
deferred one line and wrote down exactly what it owed; script 118 wrote a
fragment and left the master alone; script 92 wrote no codebook at all and its
table ships only by accidentally scoring 0.91 against *another dataset's* block.
**Three correct decisions, three tables that do not ship.** When the safe move
and the shipping move are opposites, the data stops shipping — and because
`87` counts its drops without naming them, nobody finds out for twenty days.

**The pattern this repeats.** The project already learned that
`codebook_master.csv` and `01_build_entity_spine.py` are the wrong shape because
a shared mutable file with many writers loses updates. The publication layer is
the same shape one level up: **a shared registry with many writers and no
reconciliation**, where the failure mode is not a crash but a silence. And the
silence is the specific defect — `87` counts what it drops and refuses to name
it, which is exactly the *"an interruption must not look like a completion"* rule
in `START_HERE.md`, violated by the script that decides what completion means.

---

*Diagnosis only. No dataset, script, codebook or dist artefact was modified.
Concurrent activity observed during this audit: another agent added
`code/155_pull_nigc_roster.py`, `code/156_reconcile_nigc_roster.py` and
`code/156_stage_form5500_gaming_employment.py`, and wrote
`review/gaming_nigc_additions_2026-08-26.csv` (147),
`review/gaming_nigc_closed_row_conflicts_2026-08-26.csv` (8),
`data/staging/gaming_employment_form5500_staged.csv` (2,046) and
`review/form5500_gaming_coverage_2026-08-26.csv`. Note the new `156_` prefix
collision.*

---

## PART 8 — THE SOURCE SURFACE WAS ENUMERATED, 2026-09-01

*Added by workstream M. This audit answered "why is what we built not
shipping?" It never asked "what exists that we never collected?" — and nobody
had. The answer is now a file:* **`docs/datasets/gaming_sources.md`**, *which
carries a per-source COVERAGE table (earliest available / earliest held /
latest available / latest held / gap / why) so the next session reads it
instead of re-deriving it.*

### 8.1 The NIGC document surface, measured for the first time

Part 1 of this audit lists five NIGC families on disk. **The agency publishes
72.**

| | |
|---|---:|
| wpdm categories declared by `wp-sitemap-taxonomies-wpdmcategory-1.xml` | **72** |
| distinct documents in `wp-sitemap-posts-wpdmpro-{1,2,3}.xml` | **4,071** |
| (category, document) memberships enumerated | **7,930** |
| categories Cedar held before this pass | **5** |
| documents in the sitemap that no category listing surfaced | 3, carried as `_UNCATEGORISED_IN_LISTINGS` |

Route, with the probes that killed each alternative
(`docs/PULL_DISCIPLINE.md`): `robots.txt` disallows only `/wp-admin/` and
`/wp-content/uploads/wpforms/` and declares a sitemap, so every path used is
permitted. **`/wp-json/wp/v2/*` returns 401 `rest_not_logged_in`** — the same
closed REST API script 155 measured on the map route, from WordPress's own
`rest_authentication_errors` filter, not a nonce failure. The server-rendered
`/downloads/<category>/[page/N/]` listings are the only public enumeration;
they paginate at 24 with `rel="next"` and each item is a clean `<article
class="wpdmpro">` carrying title, `/download/<slug>/` and a `datePublished`.

**Two refresh signals fell out of the enumeration**, and neither was visible
from any build log: NIGC's ordinance index now holds **1,162** documents
against Cedar's **1,155**, and **329** declination letters against Cedar's
**327**.

### 8.2 Four families were never collected. All four were fetched.

| family | what it is | outcome |
|---|---|---|
| **Indian lands opinions** | tribe × parcel × legal theory × **theory accepted Y/N** × date, as a structured index table | **102 rows, 1997-08-12 → 2026-05-18**, 98 keyed to the spine, 4 refused as `ambiguous_containment` and queued |
| **Game classification opinions** | game × Class II/III × bingo / cards / pull-tabs / internet flags × date | **122 rows, 1992-09-14 → 2024-04-26** — the earliest-reaching gaming series Cedar holds |
| **Enforcement actions** | NOVs, civil fine assessments, closure orders, settlement agreements | **362 documents indexed and fetched** |
| **Approved management contracts** | Chair-approved management contracts, by tribe | **68 documents indexed and fetched** — this is `GAMING_TEMPORAL_BUILD_LOG.md` §10.6's named hole, where `trace_nigc_management_contract` was 0 on all 774 property rows and read `not_held_by_cedar_press_this_session` |

The two opinion families are **fully structured in the index HTML**, so they
are datasets before any PDF is opened. Everything is staged to
`data/staging/`, not `data/clean/` — a new grain with no codebook block is
exactly the failure this audit spent 945 lines documenting.

### 8.3 THE FINDING THIS AUDIT'S METHOD WOULD NOT HAVE CAUGHT

Part 1 measured **raw → clean** and found nothing lost. It never measured
**raw vs clean for CURRENCY**, and on that axis two states are broken:

* **New Mexico.** `gaming_capacity_official` NM `net_win` stops at **FY2022**.
  `code/216` extracted **FY2023 – 2026Q2** on 2026-08-26, footed 14 of 14
  quarters against the source's own printed totals, and wrote **188 rows** to
  `review/nm_revshare_2023_2026_staged_2026-08-26.csv`. Four fiscal years of
  the country's second-best per-tribe revenue series, never promoted.
* **California.** `ca_gaming_payments` has **zero rows** for `period_end
  2024-12-31` and **zero** for `2026-03-31`. Both RSTF reports are on disk.
  The 93rd (2024Q4) has **37,974 characters of extractable text** — a parse
  defect. The 98th (2026Q1) has **0 characters** — an image-only scan needing
  the OCR path `code/122`/`150` already runs for ordinances.
  **`REFRESH_CADENCE.md` records "CA gaming is missing 2026-03 entirely" as
  lag. It is not lag. The document is on disk and it is a scan.**

**A source audit that walks forward from `data/raw/` finds nothing wrong with
either.** Both only appear when you walk *backwards* from the latest period in
`data/clean/` and ask what the raw directory holds past it.

### 8.4 And one measurement that closed a gap by proving it was not ours

`data.ct.gov/resource/i6ts-ib7c`, probed live **2026-09-01**, one request:
`min 1993-01-31, max 2025-12-31, count 748`. **Cedar holds every casino-month
Connecticut serves.** The 238-day lag in `REFRESH_CADENCE.md` is the SOURCE's,
confirming `code/343`'s 2026-08-26 finding six days later. Nothing to fetch.

*Written by `code/344_pull_nigc_document_surface.py`. Host lock claimed and
released with all four outcome fields. Full coverage table, exclusions and
ranked backlog: `docs/datasets/gaming_sources.md`.*

### 8.5 A 200, a valid PDF, and the wrong document — 302 times

**Worth more than the data it nearly cost.** The first attempt at the document
stage requested `https://www.nigc.gov/download/<slug>/?wpdmdl=` — the parameter
**present and empty**. WP Download Manager answered **HTTP 200 with a valid PDF
on every single request**, and it was **the same PDF every single time**:
NIGC's generic *"Helpful Hints: Requesting a Game Classification Opinion"*,
md5 `a917db80b6027b0ffd8a8b233eb8331a`.

**302 enforcement actions were "downloaded". All 302 were that one file.**

Nothing in the transport said so. Right status, right content type, right
`%PDF` magic bytes, plausible 192,025-byte size, one file per requested slug on
disk. A row count, a byte count, a manifest and an HTTP log would all have read
as a clean pull. It surfaced only because several files shared an identical
byte size, and `md5sum | sort | uniq -c` then returned **one line: `302`**.

This is `PART`-2026-08-12's **"AN ACCEPTED TOKEN IS NOT A WORKING JOB"** in a
new costume — the transport succeeded and the CONTENT was wrong — and it
generalises past NIGC:

> **A `?param=` with an empty value is not the same request as no parameter at
> all.** A CMS plugin that would 404 on a bad id will happily serve a default
> for a blank one. Where a URL carries an object id, either the id is present
> and real or the request must not be made.

The run was killed, all 302 objects deleted, and the host lock released with
`accepted_then_failed_server_side: 302` and the cause named in it — the fourth
lock field exists for exactly this and would otherwise have read as a clean
run. Two guards now stand in `code/344`:

1. **The download URL is read off the landing page and must contain the
   package's own slug.** That is what excluded the trap: NIGC's site navigation
   carries `https://www.nigc.gov/?wpdmdl=3974` links with **no slug**, which is
   what makes a bare `?wpdmdl=` look like a reasonable shape in the first place.
2. **`IDENTICAL_MD5_CEILING = 6`.** If one md5 comes back for more than six
   distinct slugs the run raises and stops. Duplicates are normal in this
   corpus — NIGC re-posts the same letter under two slugs — three hundred are
   not.

And a **canary before the fleet**, per the same rule: three objects, three
distinct md5s, resolved filenames carrying three different dates, checked
before re-committing to 430.
