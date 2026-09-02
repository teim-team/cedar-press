# Nonprofit & Philanthropy layer (Dataset 6) — build log, 2026-08-05

Build script: `code/17_build_nonprofit_990.py` (one script, `--steps` switches)
Run log: `logs/17_nonprofit_990_2026-08-05.log`
Plan: `NONPROFIT_DATASET_PLAN.md`

Vintage of every number below: IRS Exempt Organizations Business Master File as
downloaded 2026-04-29 (source page
https://www.irs.gov/charities-non-profits/exempt-organizations-business-master-file-extract-eo-bmf,
files `https://www.irs.gov/pub/irs-soi/eo{1,2,3,4}.csv`). Derived identification
files are dated 2026-04-29 / 2026-04-30 / 2026-05-01 as noted per file.

## What shipped

| File | Rows | What it is |
|---|---:|---|
| `data/spine/nonprofit_exclusion_rulings.csv` | 4,656 | Prior EXCLUSION rulings, one row per ruled-out EIN. Block list. |
| `data/clean/np_orgs.csv` | 12,764 | Candidate nonprofit universe with 990 tier, confidence tier, evidence. |
| `data/clean/np_ein_uei_bridge.csv` | 28 | EIN ↔ UEI pairs with match method and evidence. |
| `data/raw/external/irs990/` | 11 CSVs + BMF slice | Local copies + `_SOURCE_MANIFEST.csv`. |
| `data/raw/external/irs990/irs_bmf_slice_universe_2026-08-05.csv` | 12,764 | BMF rows for the candidate EIN universe (streamed from the 323 MB BMF). |

`entity_id` in `np_orgs.csv` is written **blank on every row**. Spine linking is
not done here. No new ID series was minted.

## 1. Source inventory

The BMF was streamed in 200k-row chunks, `dtype=str`, never loaded whole:
**1,952,238 rows** across eo1 (277,214), eo2 (717,691), eo3 (952,412), eo4 (4,921).

| File | Rows | Unique EIN | Role |
|---|---:|---:|---|
| `tribal_irs990_candidates_2026_04_29.csv` | 12,764 | 12,764 | Net-1 raw pool: BMF names carrying a tribal token |
| `tribal_irs990_strict_2026_04_29.csv` | 7,682 | 7,682 | Name-matched to the canonical tribe table (ICR input) |
| `tribal_irs990_state_validated_2026_04_29.csv` | 4,222 | 4,222 | IRS state = tribe state or adjacent |
| `tribal_irs990_unmatched_2026_04_29.csv` | 198 | 198 | Distinctive token, no canonical tribe match |
| `tribal_irs990_icr_high_confidence_2026_04_29.csv` | 2,590 | 2,590 | ICR ≥3 of 5 coders |
| `tribal_irs990_icr_review_queue_2026_04_29.csv` | 3,156 | 3,156 | ICR exactly 2 of 5 coders |
| `tribal_irs990_verified_2026_04_30.csv` | 4,072 | 4,072 | ICR pool minus place-name false positives |
| `tribal_irs990_verified_strict_2026_04_30.csv` | 1,090 | 1,090 | Survived the v2 ambiguous-token filter |
| `tribal_irs990_dropped_falsepositive_2026_04_30.csv` | 1,674 | 1,674 | **Exclusion rulings** (place-name pass) |
| `tribal_irs990_dropped_strict_2026_04_30.csv` | 2,982 | 2,982 | **Exclusion rulings** (v2 strict pass) |
| `irs_990_to_federal_funding_match_2026_05_01.csv` | 1,090 | 1,090 | EIN → assistance recipient; 28 rows carry a UEI |

Arithmetic checks out end to end: 2,590 + 3,156 = 5,746 = 4,072 verified + 1,674
dropped; 4,072 = 1,090 verified-strict + 2,982 dropped-strict. `strict` is a
strict subset of `candidates` (0 EINs outside it).

**Discrepancy flagged, not resolved:** `CHANGELOG.md` in the dissertation repo
records the funnel as "12,764 raw → 7,484 strict → 4,222 state-validated → 2,590
ICR hi-conf → 1,090". The strict file on disk has **7,682** rows, not 7,484. The
file is more recent than the prose, so this build uses 7,682 and flags the prose.

## 2. Intercoder reliability, as documented upstream

Framework: `irs_990_intercoder_reliability.py`. Five mechanical coders vote on each
of the 7,682 strict candidates; ≥3 agree → high confidence, exactly 2 → review queue.

| Coder | Rule | Positive | Rate |
|---|---|---:|---:|
| A name_distinctive | name contains a distinctive tribal token | 7,162 | 95.7% |
| B state_validated | IRS state = tribe state or adjacent | 4,222 | 56.4% |
| C ntee_plausible | NTEE letter in {A,B,L,N,P,S,T,W,X} | 3,726 | 49.8% |
| D name_strong_signal | tribal token **and** org descriptor | 433 | 5.8% |
| E usaspending_match | (tribe, state, city) seen in USAspending | 843 | 11.3% |

**Pairwise Cohen's kappa is below 0.05 for every pair except B–E (0.143).** That
is not agreement in the classical sense; it is five weakly correlated signals
counted as votes. The upstream note frames this as intentional ("coders catch
different aspects"), which is defensible as a screening device but means the
"≥3 of 5" line is a **coverage threshold, not a reliability-validated ruling.**
Nothing downstream should be described as validated by kappa.

## 3. Exclusion jurisprudence (extracted first, as instructed)

`data/spine/nonprofit_exclusion_rulings.csv` — 4,656 rows, 4,656 unique EINs, no
EIN ruled out twice.

| Reason | Rows |
|---|---:|
| `ambiguous_place_token_no_tribal_purpose` | 2,982 |
| `place_name_false_positive` | 1,674 |

Each row carries `ein, org_name, exclusion_reason, evidence, source_file,
ruled_date, ruled_by, ruling_type, recheck_candidate, state,
tribe_id_token_match, n_coders_agree`. The `evidence` field names the **specific
rule that fired** — the exact place-name regex matched (e.g. `CHEROKEE COUNTY`),
or the ambiguous tribe_id plus the absence of a tribal-purpose term — so any
ruling can be audited without rerunning the upstream scripts.

**Important distinction from the `hci_analysis.do` per-UEI drops.** Those were
hand rulings with per-row citations (cage.dla.mil, GAO decisions, OpenCorporates).
These 4,656 are **rule-based script filters** authored by Elijah
(`verify_irs_990_with_real_filters.py`, `verify_irs_990_v2_strict.py`), applied
mechanically. `ruling_type = rule_based_script_filter` records this on every row.
They should block attribution by default, but they are not per-org adjudications
and they contain false negatives.

**67 rows carry `recheck_candidate = 1`** — the name reads like a real tribal
institution despite the drop (e.g. `NAVAJO TECHNICAL COLLEGE`, `CAYUGA HOUSING
DEVELOPMENT CORPORATION`, `PONCA ECONOMIC DEVELOPMENT CORPORATION`, `CHEYENNE
ELDERS COUNCIL INC`). Many of the 67 are genuinely non-tribal (`MOHAWK VALLEY
COMMUNITY COLLEGE FOUNDATION`), which is exactly why they need a human ruling
rather than an automated reversal.

## 4. `np_orgs.csv` — 12,764 rows

Confidence tier:

| Tier | Rows | Definition |
|---|---:|---|
| A | 1,090 | In `verified_strict` |
| B | 7,018 | Candidate universe, not excluded, below strict-verified |
| X | 4,656 | Blocked by a prior exclusion ruling |

Funnel stage (finest position reached): `verified_strict` 1,090, `state_validated`
105, `canonical_name_match` 1,831, `raw_name_candidate` 5,082,
`excluded_by_prior_ruling` 4,656.

990 tier (from BMF `FILING_REQ_CD`, with 990-EZ eligibility thresholds applied to
`REVENUE_AMT` < $200k and `ASSET_AMT` < $500k; `tier_basis` records the reasoning
per row):

| Tier | All rows | Within tier A |
|---|---:|---:|
| `990_N` | 6,453 | 572 |
| `full_990` | 2,806 | 244 |
| `990_EZ` | 1,316 | 103 |
| `not_required_to_file` | 2,060 | 160 |
| `UNKNOWN` | 129 | 11 |

**Half the universe (50.6%) sits in the 990-N postcard tier**, and another 16%
are not required to file at all. The financial layer of this dataset will only
ever cover the `full_990` + `990_EZ` tiers.

`classification_ruling` is **`UNRULED` on all 12,764 rows.** This is deliberate,
not an omission. The IRS BMF has no control-status field; nothing in the local
corpus states who controls a board. Minting `tribally_controlled` from a name
match would be exactly the fabrication the prime directive forbids. The `evidence`
column instead records the reproducible signals per row: which tribe token
matched, which attribution method, which coders fired, whether the org survived
each filter, and whether it appears in the BMF snapshot. Rulings are the next
step and belong in a reconcile-queue cycle with Nets 3 and 4 evidence.

### QC finding: the strict-verified set still leaks place-name organizations

A review flag (`review_flag`, `review_flag_token`) fires when the org name
contains a civic or place descriptor (COUNTY, CHAMBER OF COMMERCE, KIWANIS,
ELECTRIC COOPERATIVE, SCHOOL DISTRICT, HISTORICAL SOCIETY, BOOSTER, PTA/PTO, …).

| Tier | Flagged | Share |
|---|---:|---:|
| A | 161 of 1,090 | 14.8% |
| B | 676 of 7,018 | 9.6% |
| X | 917 of 4,656 | 19.7% |

Tier-A examples: `MODOC COUNTY HISTORICAL SOCIETY`, `MOJAVE CHAMBER OF COMMERCE
INC`, `KIOWA COUNTY FARM BUREAU`, `COLORADO STATE UNIVERSITY-PUEBLO FOUNDATION`,
`APACHE BASEBALL BOOSTER CLUB INC`.

`tribe_id_token_match` is carried through for provenance and must not be read as
an attribution. It is the upstream token match and it is sometimes plainly wrong:
`LAKOTA LANGUAGE CONSORTIUM INC` (IN) carries `SGVF-CHGCMT-00` (Chugachmiut
self-governance consortium, AK) — a token collision on "consortium". Any spine
linking must re-derive the tribe, not inherit this column.

Unflagged rows are not clean either: the three largest tier-A organizations by
reported BMF revenue are `UMATILLA ELECTRIC COOPERATIVE ASSOCIATION` ($592.5M),
`YAVAPAI COMMUNITY HOSPITAL ASSOCIATION` ($497.2M) and `LUMBEE RIVER ELECTRIC
MEMBERSHIP CORPORATION` ($169.6M) — a rural co-op, a Prescott AZ community
hospital, and a rural co-op. Tier A is a **screened candidate set, not a Native
organization list**, and the aggregate "$2.51B tier-A BMF revenue" figure is
therefore not publishable as Native nonprofit revenue. Do not quote it.

## 5. `np_ein_uei_bridge.csv` — 28 rows, and the net-new count

Only one EIN↔UEI co-occurrence source exists in the corpus:
`irs_990_to_federal_funding_match_2026_05_01.csv`. Of its 1,090 rows, **33 carry
assistance dollars and 28 carry a UEI**. Checked and found to contain no usable
EIN↔UEI pairs: `data/clean/funding_identifier_harvest.csv` (`recipient_ein`
present as a column but populated on 0 of 37,704 rows), the SAM parsed extracts
(no EIN field — SAM public extracts do not publish TINs), and
`Assistance_56G180126_TransactionHistory_1.csv` (UEI/DUNS only).

Match method on all 28: `normalized_name_plus_state_exact` — BMF org name
normalized (uppercase, non-alphanumerics stripped, whitespace collapsed) and
joined to USAspending assistance recipients aggregated by (normalized
`recipient_name`, `recipient_state_code`), per `enrich_need_v2.py` step [4].
That is an algorithmic, unreviewed join, so every bridge row is
`confidence_tier = B` regardless of the EIN's own tier (all 28 EINs are tier A).
Total assistance attached: $1,792.0M, largest single row Winnebago Tribe of
Nebraska $572.1M.

**Headline: of the 28 bridge UEIs, 19 are already in
`cedar_identifier_ledger_final.csv` and 9 are NET-NEW.**

| UEI | Organization |
|---|---|
| F5QVWHNPLKL5 | TUSCARORA NATION OF INDIANS OF THE CAROLINAS |
| HA5BGKKZWE55 | MACHIS LOWER CREEK INDIAN TRIBE OF ALABAMA |
| HLDTLQF6RUD9 | MUSCOGEE NATION OF FLORIDA INC |
| HYBNGZAEENR3 | SENECA NATION OF INDIANS ECONOMIC DEVELOPMENT COMPANY |
| JKR5MEXMD5B6 | LUMBEE LAND DEVELOPMENT INC |
| MKMRDDVYAP18 | QUILEUTE TRIBAL SCHOOL |
| N6U3L6J2DMX8 | UNITED CHEROKEE ANIYUNWIYA NATION |
| PT74Q7MKNP78 | DOUGLAS-CHEROKEE ECONOMIC AUTHORITY INC |
| U3AQJ3SKHC99 | KIOWA COUNTY COUNCIL ON AGING INC — **review flag: civic/place descriptor** |

Substantively interesting: five of the nine are state-recognized or
non-federally-recognized tribal bodies (Tuscarora NC, MaChis Lower Creek AL,
Muscogee Nation of Florida, United Cherokee AniYunWiya, Lumbee-affiliated), which
is precisely the population that falls out of contracting-flag universes. Two
(`DOUGLAS-CHEROKEE ECONOMIC AUTHORITY`, `KIOWA COUNTY COUNCIL ON AGING`) are
likely place-name traps and are flagged, not asserted.

`np_ein_uei_bridge.csv` carries `uei_already_in_cedar_ledger` per row.
`cedar_identifier_ledger_final.csv` was read only; nothing under `data/clean/cedar_*`,
`data/spine/cedar_*` or `review/` was modified.

### Conflict with the brief: EIN is thin in the stack, not absent

The brief states EIN is "the one identifier the Cedar Press stack currently
lacks." It is not absent: `cedar_identifier_ledger_final.csv` already carries
**1,104 EIN rows (1,101 unique)**, all sourced from `need_v6_geocoded.csv`, which
itself ingested the 1,090 strict-verified 990 EINs. So:

| Tier | EINs | Already in ledger | Net-new to ledger |
|---|---:|---:|---:|
| A | 1,090 | 1,089 | 1 |
| B | 7,018 | 11 | 7,007 |
| X | 4,656 | 1 | 4,655 |
| **All** | **12,764** | **1,101** | **11,663** |

The one tier-A EIN not in the ledger is `953804363 MOJAVE FOURSQUARE CHURCH` (CA),
which is a filing-exempt church and almost certainly a token false positive.
The honest EIN gain from this build is not raw count — it is the **evidence
layer**: filing tier, revenue/asset amounts, exclusion status, and per-row
evidence attached to EINs the ledger holds bare.

### Ruling violation found in the existing ledger

`850303705 NAVAJO TECHNICAL COLLEGE` (NM) sits in
`cedar_identifier_ledger_final.csv` as `canonical_name = Navajo,
entity_class = TRIBAL_COLLEGE`, while the 2026-04-30 v2 strict pass ruled that
same EIN OUT (`ambiguous_place_token_no_tribal_purpose`: "Navajo" is on the
ambiguous-token list and the name lacks a literal tribal-purpose term).

Navajo Technical University is a real tribally chartered institution, so the
probable error is the **exclusion**, not the ledger. This is exactly the false
negative class the `recheck_candidate` flag was built for. Flagged, not silently
resolved — the ruling authority decides which record wins.

## 6. Required caveats (publish these with any table)

1. **Tribal instrumentalities largely do not file 990s.** Entities of tribal
   governments are generally outside the Form 990 universe under IRC §7871 and
   related treatment. The largest tribal institutions — tribal governments
   themselves, most 638-contracted health and education operations, many tribal
   authorities — can be entirely invisible in IRS data. This dataset cannot see
   them, and the tribal-government side of the ledger lives in the federal
   contracting and assistance datasets, not here. A tribe absent from `np_orgs`
   is evidence about IRS filing obligations, never about that tribe's nonprofit
   sector.
2. **990-N postcard filers yield existence only.** 6,453 of 12,764 rows (50.6%)
   are 990-N filers (gross receipts under the $50k threshold): name, EIN, state,
   existence. No revenue, no expenses, no officers, no program detail. A large
   share of grassroots Native organizations lives in this tier permanently.
3. **Fiscal sponsorship hides organizations entirely.** Native projects operating
   under a non-Native fiscal sponsor never hold an EIN of their own and cannot
   appear here at any tier. The EIN universe is not the organization universe.
4. **Churches and certain religious organizations are exempt from filing.**
   2,060 rows (16.1%) carry a BMF filing-requirement code meaning not required to
   file (church, government 501(c)(1), religious, state institution). Native
   ministries and mission-adjacent institutions are systematically thin here.
5. **Filing lag is one to two years.** The BMF `TAX_PERIOD` and revenue fields
   trail the calendar; the "current year" in this dataset is always a trailing
   year. Every table must state the BMF vintage — here, downloaded 2026-04-29.
6. **NTEE codes are weak signal only.** `ntee_code` is recorded because it is on
   the record, and it was used upstream only as one of five screening votes
   (coder C, 49.8% positive). The NTEE taxonomy has no Native category and does
   not distinguish Native organizations. It must never be used to classify Native
   status, and no claim in this dataset rests on it.

Two further caveats this build adds:

7. **The BMF-presence check is circular.** All 12,764 universe EINs appear in the
   BMF slice because the universe was derived from that same BMF snapshot. This
   is not a revocation check; a real one needs a newer BMF vintage compared
   against this one.
8. **Tier A is a screened candidate set, not a Native organization list** (see
   §4). Any headline aggregate computed over tier A without human rulings will
   include electric cooperatives, county historical societies and booster clubs.

## 7. Not done, by instruction or by dependency

- **Net 2 (geography)** not run — depends on the spine.
- **Entity linking / `entity_id` population** not done — spine work, owner's.
- **Classification rulings** not minted — needs Nets 3 (roster seeding: Native
  CDFI Network, NAP, First Nations grantees, AIHEC, NCUIH/IHS urban Indian orgs)
  and 4 (Schedule R related orgs, Schedule I grants), plus a reconcile-queue cycle.
- **990 XML financial panel, Schedules I/R/J/O** not built — phase 2 per the plan.
- ProPublica Nonprofit Explorer not queried this session.

## 8. Next steps, ranked

1. Rule the 67 `recheck_candidate` exclusions and the 161 flagged tier-A rows
   through a reconcile-queue cycle. That converts the block list from mechanical
   to adjudicated and settles the Navajo Technical College conflict.
2. Run Net 3 roster seeding — it is the only cheap way to get real
   `tribally_controlled` / `native_controlled` rulings, because rosters are
   pre-ruled populations.
3. Pull 990 financials for the 244 tier-A `full_990` organizations that survive
   ruling, then compare 990 revenue against the tribal obligations panel to find
   the attribution gaps the brief describes.
4. Re-run the EIN↔UEI harvest after Net 3: more ruled organizations means more
   name+state joins worth attempting, and each one should be verified at UEI level
   rather than left at the algorithmic tier.
