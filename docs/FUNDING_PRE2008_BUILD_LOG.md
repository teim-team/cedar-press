# Dataset 3 — FY2001–2007 backfill, multi-agency build log

*Run 2026-08-05. Evidence trail: `logs/30_funding_pre2008.log`. Code: `code/30_funding_pre2008.py`.*
*Predecessor: `docs/FAADS_FEASIBILITY_2026-08-05.md` (method, route and limits — not re-derived here).*
*Prime directive observed: zero fabrication. No agency-year was estimated, interpolated or
reconstructed. An agency-year that is not in the output was not retrieved, and is named below.*

---

## 1. Result

| | |
|---|---|
| Agencies targeted | 10 — HHS, Education, HUD, USDA, DOJ, DOL, EPA, DOT, Energy, Commerce |
| **Complete FY2001–2007** | **all 10** |
| Not retrieved | none |
| Already held | Interior FY2001–2007 (prior run), carried forward unchanged |
| **Rows added this run** | **2,709,087** |
| **Obligations added** | **$1,821,290,844,508** (all recipient types) |
| Tribal-flagged rows added | 38,656 |
| Tribal-flagged obligations added | $6,193,983,025 |
| Combined file total | 2,769,748 rows · 11 agencies · $1,830,639,317,708 · 46,302 tribal-flagged rows · $7,810,716,166 |

The run was rate-limited twice and resumed twice from checkpoint; no agency was lost to it.

Every row carries `tribe_id` **blank** and is **Tier C**. No name matching was attempted.

---

## 2. The open question is answered, and the answer changes the recommendation

The brief asked whether HHS or Education carry DUNS pre-2008, because if they did, per-tribe
attribution would be possible for those agencies. **Measured, per agency per year:**

### `pct_with_duns`

| agency | 2001 | 2002 | 2003 | 2004 | 2005 | 2006 | **2007** |
|---|---:|---:|---:|---:|---:|---:|---:|
| Health and Human Services | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | **99.7** |
| Education | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | **100.0** |
| Housing and Urban Development | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | **100.0** |
| Agriculture | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | **98.0** |
| Justice | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | **96.2** |
| Labor | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | **100.0** |
| Environmental Protection Agency | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | **97.8** |
| Commerce | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | **100.0** |
| Energy | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | **100.0** |
| Transportation | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | **0.7** |
| Interior | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | **0.0** |

UEI is **0.0% everywhere in FY2001–2006**. In FY2007 it appears alongside DUNS but is
consistently lower and more variable: HUD 97.5, Education 95.7, Commerce 95.0, Labor 92.1,
Energy 88.6, Justice 88.1, EPA 86.8, HHS 76.4, **USDA 47.6**, DOT 0.7, Interior 0.0. UEI is
back-assigned from later SAM registration rather than reported at the time, so for FY2007 work
**DUNS is the join key and UEI is the weaker fallback** — using UEI alone would silently drop
roughly half of USDA and a quarter of HHS.

### What this establishes

**1. FY2001–2006 is universally identifier-free.** All eleven agencies — every one of the ten
targeted plus Interior — are at **0.0% DUNS and 0.0% UEI in all six years**. There is not a
single exception across 66 agency-years. Per-tribe attribution is impossible for FY2001–2006
for every agency, not just Interior. This closes the question the prior run had to leave open,
and it closes it in the restrictive direction: **no, HHS and Education do not carry DUNS
pre-2007.**

**2. The identifier regime begins at FY2007, not FY2008.** Nine of the eleven agencies jump
from 0.0% to 96–100% DUNS in FY2007 — one year earlier than Dataset 3's current floor. This is
the FAADS PLUS transition under FFATA landing in the data.

**3. The prior run's "agency-specific, not year-specific" reading needs both halves.** It is
year-specific up to FY2007 (everyone is at zero) and agency-specific from FY2007 (Interior at
0.0% and **Transportation at 0.7%** lag the field). DOT is a newly identified laggard — it sits
at 100% DUNS in Cedar Press's FY2008 data, so its gap is confined to FY2007 and earlier.

### The consequence worth acting on

**Dataset 3's per-tribe series can be extended back one full year — to FY2007 — for nine
agencies** (HHS, Education, HUD, USDA, DOJ, DOL, EPA, Commerce, Energy), using the same
DUNS/UEI join the FY2008+ data already uses. That is a real, immediate gain: FY2007 tribal
assistance becomes attributable rather than aggregate-only.

It cannot be extended to FY2001–2006 for anybody without a name-matching ruling.

---

## 3. A second finding: the tribal flag is not uniformly populated

The feasibility doc established that `business_types_code = 'I'` isolates federally recognized
tribal-government recipients with zero name matching, and reported it 100% populated for
Interior. **That does not generalise.** Measured share of rows coded `X` = OTHER:

| agency | 2001 | 2002 | 2003 | 2004 | 2005 | 2006 | 2007 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Health and Human Services | 0.5 | 0.5 | 0.3 | 0.3 | 0.4 | 0.4 | **100.0** |
| Justice | 0.2 | 1.3 | 2.4 | 3.0 | 1.1 | **11.5** | **38.2** |
| Commerce | 2.9 | 3.4 | 3.4 | 2.8 | 4.8 | 5.8 | 4.6 |
| Agriculture | 0.2 | 0.1 | 0.2 | 0.2 | 0.2 | 0.2 | 4.6 |
| Education | 2.7 | 2.2 | 1.9 | 1.2 | 0.3 | 0.2 | 0.3 |
| all others | ≤1.4 | ≤1.7 | ≤2.2 | ≤1.8 | ≤1.7 | ≤1.2 | ≤2.5 |

**HHS codes 74,160 of its 74,163 FY2007 rows as `X` = OTHER.** Its tribal-flagged count
collapses from 1,675 in FY2006 to **1** in FY2007. That is a coding change, not a funding
change, and anyone reading tribal-flagged HHS rows straight across FY2006→FY2007 will see a
99.9% collapse that did not happen.

So the two tribal-identification routes are **inverted in time within the same agency**:

| HHS | FY2001–2006 | FY2007 |
|---|---|---|
| DUNS | 0.0% — unusable | 99.7% — usable |
| `business_types_code = 'I'` | 1,675–3,480 rows/yr — usable | 1 row — unusable |

Neither route works in both regimes, but between them **every year FY2001–2007 has exactly one
working tribal-identification route for HHS.** That is the practical path forward.

Two further anomalies, recorded as observed and **not** explained:

- **HUD tribal-flagged rows fall 482 → 21 at FY2006→FY2007** while its `X` share stays at 0.3%.
  Unlike HHS this is not an `X` substitution, and the cause is not established here.
- **DOJ's `X` share rises to 11.5% in FY2006 and 38.2% in FY2007**, so its flag is partially
  degraded in exactly the years its DUNS becomes available.

`pct_business_type_other_X` is now a column in the coverage deliverable so this class of defect
is visible rather than latent.

---

## 4. Route-equivalence control

Two retrieval routes were used, and a comparison across FY2006/FY2007 is worthless if they
differ. USAspending's static **Award Data Archive** supplied FY2007; **generated bulk_download
jobs** supplied FY2001–2006. The archive's assistance coverage begins at FY2007 (verified from
the index: 100 files each for FY2007, FY2008, FY2009, 97 for FY2010, none earlier), so the
split was forced.

The control used the one agency-year obtainable both ways — Interior FY2007, held from the
prior run's bulk job and re-pulled from the archive:

| | rows | DUNS | UEI | tribal-flagged | obligations |
|---|---:|---:|---:|---:|---:|
| Interior FY2007 via **bulk job** | 9,662 | 0.0% | 0.0% | 841 | $1,466,244,955 |
| Interior FY2007 via **archive** | 9,662 | 0.0% | 0.0% | 841 | $1,466,244,955 |

Identical on rows, identifier fill, tribal-flag count, obligations and the full business-type
distribution. **The routes are interchangeable**, so the FY2006→FY2007 changes above are real
reporting changes, not retrieval artefacts. Control file retained at
`data/raw/external/faads/agencies/_control_doi_fy2007_archive.zip`.

---

## 5. Rows and dollars by agency-year

Full detail is in `data/clean/faads_identifier_coverage_by_agency_year.csv` (77 agency-year
rows, 11 columns). Summary — rows, and tribal-flagged rows in brackets:

| agency | 2001 | 2002 | 2003 | 2004 | 2005 | 2006 | 2007 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Health and Human Services | 38,111 [2,361] | 72,497 [1,955] | 78,411 [3,480] | 66,921 [1,842] | 69,899 [1,796] | 65,296 [1,675] | 74,163 [1] |
| Education | 34,108 [187] | 41,932 [192] | 36,399 [79] | 30,849 [116] | 28,995 [241] | 50,197 [317] | 344,401 [1,480] |
| Housing and Urban Development | 64,292 [266] | 8,026 [176] | 15,170 [477] | 21,762 [967] | 30,565 [1,040] | 80,126 [482] | 171,554 [21] |
| Agriculture | 75,609 [1,193] | 83,010 [927] | 83,132 [932] | 81,886 [708] | 79,426 [654] | 63,459 [682] | 67,615 [1,652] |
| Justice | 11,517 [439] | 16,141 [387] | 17,629 [550] | 14,416 [406] | 15,315 [479] | 9,074 [493] | 4,470 [245] |
| Labor | 995 [45] | 3,195 [301] | 2,729 [254] | 2,658 [258] | 2,489 [258] | 2,512 [249] | 3,085 [207] |
| Environmental Protection Agency | 7,278 [905] | 7,707 [834] | 6,770 [1,047] | 7,126 [1,182] | 6,702 [1,082] | 6,120 [957] | 4,595 [977] |
| Transportation | 68,810 [20] | 72,996 [3] | 76,401 [20] | 73,094 [13] | 74,905 [12] | 82,719 [30] | 86,921 [59] |
| Energy | 5,350 [32] | 5,870 [57] | 6,292 [80] | 6,049 [55] | 6,367 [76] | 5,629 [63] | 5,765 [83] |
| Commerce | 2,985 [113] | 3,074 [87] | 3,093 [85] | 3,079 [75] | 3,459 [84] | 3,371 [76] | 2,524 [79] |
| Interior *(prior run)* | 6,951 [1,219] | 6,842 [1,176] | 8,180 [739] | 10,703 [1,138] | 9,088 [1,145] | 9,235 [1,388] | 9,662 [841] |

### Third finding: USDA pre-2007 is majority county-aggregate, and this one bites

The feasibility doc raised `record_type = 1` — county-aggregate rows whose recipient name reads
`MULTIPLE RECIPIENTS` and which are unattributable *in principle, not merely in practice* — as
a caveat to check per agency. It is zero for Interior. **For USDA it is the majority of the
file:**

| USDA | 2001 | 2002 | 2003 | 2004 | 2005 | 2006 | 2007 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `record_type = 1` share | 65.6% | 70.2% | 68.7% | 69.0% | 64.1% | 58.2% | **0.3%** |

Across FY2001–2006 that is **309,339 rows carrying $321,175,279,055 — 52.1% of USDA's pre-2007
assistance dollars — attached to no identifiable recipient at all.** Every one of those rows
has `recipient_name = 'MULTIPLE RECIPIENTS'`.

Every other agency in this build is at **0** in every year. USDA is the sole exception, and its
share collapses to 0.3% in FY2007 — the same regime boundary that turns DUNS on.

Two consequences:

- **A USDA row count or dollar total for FY2001–2006 is not comparable to any other agency's**,
  and is not comparable to USDA's own FY2007. Filter on `record_type = 2` before using USDA
  pre-2007, or say plainly that half the dollars are county aggregates.
- **The tribal-flagged USDA rows are safe.** In FY2001, 1,189 of the 1,193 flagged rows are
  `record_type = 2`; only 4 are aggregates. The tribal subset is action-by-action data even
  where the surrounding file is not.

`n_record_type_1` is carried per agency-year in the coverage file so this is checkable rather
than assumed.

### Caveat that must travel with any published aggregate

`federal_action_obligation` is signed, and a large downward modification lands in the year it
was executed. **Interior's FY2007 tribal-flagged total is net −$20,688,089**: 801 of 841 rows
are positive ($148.7M), and a **single Bureau of Reclamation deobligation of −$167,234,595**
flips the year. Publish these as *net obligations*, say so, and prefer multi-year totals to
single-year points.

---

## 6. The rate limit, and how the run survived it

**Nothing is missing. All 70 targeted agency-years were retrieved** (10 agencies × FY2001–2007;
77 in the file counting Interior's 7 from the prior run). That happened despite the block firing
twice, because every agency-year was checkpointed the moment it landed.

Timeline:

| time (UTC) | event |
|---|---|
| — | inherited an active block from the prior run |
| 19:53–20:10 | probed at 5-minute intervals; **cleared after ~65 min** |
| 20:10–20:16 | 10 Award Data Archive files (FY2007, all 10 agencies) |
| 20:17–21:15 | 42 generated jobs — HHS, Education, HUD, USDA, DOJ, DOL, EPA complete |
| 21:15:55 | **re-blocked** on `dot_fy2001`, after ~53 retrievals |
| 21:18–22:21 | probed again; **cleared after ~66 min** |
| 22:21–22:47 | final 18 jobs — DOT, Energy, Commerce complete |

The two clearing intervals — 65 and 66 minutes — are consistent enough to plan around.

Characterisation of the block, for whoever hits it next:

- It is **not** DNS, routing, TLS or an outage. `curl -v` shows TCP connect and TLS handshake
  succeeding and the request line sent before the server closes; `www.usaspending.gov` serves
  200 from the same client at the same moment.
- It hits **both** `api.usaspending.gov` and `files.usaspending.gov` (same address,
  `166.123.8.118`), so the archive route is blocked too — it is gentler on the budget, not
  immune to it.
- **The budget is per-IP and spans sessions**, and it counts *downloads*, not just generated
  jobs. Both blocks fired after roughly 40–55 retrievals from this address.
- **It clears on its own in ~65 minutes** (65 and 66 minutes, twice measured). It was waited
  out, never worked around: no alternate egress, no IPv6 fallback, no proxy, no header spoofing.
- Practical plan: budget ~50 retrievals per hour, checkpoint everything, and let a waiter resume
  automatically. The full 77-agency-year build takes ~3 hours wall-clock including two waits,
  and needs no supervision.

---

## 7. How it was built

`code/30_funding_pre2008.py` — stages `pull` / `pull_archive` / `build` / `coverage` /
`manifest`, fully resumable. `code/30_wait_and_pull.py` waits out a block and pulls the moment
it lifts. `code/30_probe_usaspending.py` is a standalone availability probe.

Verification done before any new agency was trusted:

- The extractor re-derived FY2001 Interior from the prior run's staged zip and matched the prior
  `faads_transactions.csv` **row-for-row: 6,951 vs 6,951, identical on all 23 non-provenance
  columns.**
- A **regression guard** in the build asserts the carried Interior slice is exactly 60,661 rows
  / $9,348,473,200.00 / 7,646 tribal-flagged and aborts the build otherwise. It passes.
- An **agency-year claim guard** ensures each agency-year is counted from exactly one staged
  file, so the two overlapping retrieval routes cannot double-count rows or dollars.

Design points that mattered:

1. **Checkpoint per agency-year** into `data/raw/external/faads/agencies/_state.json` the moment
   each zip lands. The re-block cost nothing already retrieved.
2. **Never spend the budget twice.** The job planner computes missing fiscal years per agency
   and skips anything already held by either route — which is why FY2007 was never re-pulled as
   a job after the archive supplied it.
3. **20-column subset instead of the full 112.** Everything the output schema needs plus
   `recipient_duns` / `recipient_uei`. Total staged raw is 155 MB rather than several GB.
4. **Range mode detected, not assumed.** The endpoint rejected a multi-year `date_range`
   (HTTP 400), so the planner fell back to per-fiscal-year jobs — 60 jobs, not 10.
5. **Agency names verified** against `/api/v2/references/toptier_agencies/` before any pull.
   This caught that Labor's toptier code is **`1601`, not 3 digits**, which a `\d{3}` archive
   filename pattern silently dropped.

---

## 8. Deliverables

| File | State |
|---|---|
| `data/clean/faads_transactions_all_agencies.csv` | **2,769,748 rows** (1,075 MB), 11 agencies, FY2001–2007, 24 columns including `agency`. **This supersedes `data/clean/faads_transactions.csv`**, which is retained unmodified as the prior run's artefact and is a strict subset of it (Interior only). |
| `data/clean/faads_identifier_coverage_by_agency_year.csv` | 77 agency-year rows, 11 columns: `agency, fiscal_year, n_rows, pct_with_duns, pct_with_uei, n_tribal_flagged, pct_with_duns_tribal_rows_only, pct_business_type_other_X, n_record_type_1, obligated_usd, obligated_usd_tribal_flagged` |
| `data/raw/external/faads/_SOURCE_MANIFEST_faads.csv` | 88 rows (was 16). Every new artefact carries source URL, bytes, row count, SHA-256 and retrieved date. |
| `data/raw/external/faads/agencies/` | 70 staged zips + `_state.json` + the route-equivalence control file |
| `data/raw/external/faads/_award_data_archive_index.html` | archive listing as retrieved, establishing the FY2007 floor |

Verified after the final build: **24 columns, 2,769,748 rows, and `tribe_id` non-blank on 0 of
them.**

Not modified, per constraints: `data/spine/`, `data/clean/cedar_*`, `review/`,
`data/clean/federal_funding_transactions.csv` (read only, for the FY2008–09 baseline).

---

## 9. What Elijah should rule on

The feasibility doc's three questions stand, plus one new one that is more valuable than the
others:

1. **New — extend the per-tribe series back to FY2007?** Nine agencies carry 96–100% DUNS in
   FY2007. The existing FY2008+ attribution method applies unchanged. This is a one-year gain in
   *attributed* coverage, not just an aggregate pool, and it is the highest-value item here.
2. Accept **FY2001** as Dataset 3's published floor for the aggregate pool, against the
   project-wide 2000 target?
3. Publish aggregate tribal totals for FY2001–2006 from `business_types_code = 'I'` — now known
   to be **agency-dependent**, sound for Interior/EPA/USDA/DOJ/Education, and requiring the HHS
   FY2007 and HUD FY2007 caveats above?
4. The FY2010 Interior discontinuity flagged by the prior run still needs adding to the live
   warnings in `docs/handoffs/STATE_OF_BUILD.md`. It affects the currently published dataset.

## 10. Next session

The retrieval job is finished — all 10 agencies, all 7 years. What is left is analysis and one
loose end:

1. **Cheap, closes a loose end:** pull HUD FY2007 as a generated job and compare against the
   archive file, to see whether HUD's 482 → 21 tribal-flag drop survives a second route the way
   Interior's numbers did. One request. The Interior control makes a route artefact unlikely,
   but HUD's drop is the one anomaly here with no established cause.
2. If ruling 1 in §9 goes ahead, join FY2007 to the spine on DUNS for the nine agencies that
   carry it, exactly as FY2008+ is joined today. Prefer DUNS over UEI (see §2).
3. If the aggregate pool is published, apply the three caveats — HHS FY2007 flag failure, USDA
   `record_type = 1`, and signed net obligations — at the point of publication, not in a
   footnote.
