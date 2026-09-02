# Methodology — Tribal Gaming

**`gaming`. 54 customer tables; the spine is `gaming_facilities.csv`, **787
ROWS — not 787 facilities** (see the denominator note immediately below), and the
regulatory record runs through NIGC's published document surface — 72 categories,
4,071 documents.** [measured 2026-09-02]

> **GAMING-DENOMINATOR-2026-09-02 — the gaming denominator, re-derived from the live files.**
> `gaming_facilities.csv` holds 787 ROWS. That is not a facility count and must not be a denominator. 7 of them are placeholders whose `facility_name` is literally `No casino`, recording that a nation operates none. 56 duplicate groups sit in `review/gaming_facility_duplicate_candidates_2026-09-02.csv`: 52 are same-tribe (`LIKELY_SAME_PROPERTY`) and hold 53 rows beyond one each, so collapsing them gives 787 - 53 = **734**; the other 4 are `DIFFERENT_TRIBES_CHECK_BOTH` and at least one of those - Stables Casino, Miami Tribe with Modoc Nation - is a JOINT OPERATION, not a duplicate. No verdict is applied: `duplicate_of_facility_id` is populated on 10 rows, not 53. So the honest range is **734 to 780** and the single thing every consumer must stop doing is dividing by 787 - it inflates the denominator by 7.2% and understates every coverage percentage in the gaming dataset by about 6.7%.
>
> Re-derive rather than quote: `py -3 code/1116_ruling_propagation_2026_09_02.py derive`.
> `py -3 code/1116_ruling_propagation_2026_09_02.py verify` exits 1 while any
> document in `docs/` or `review/` still states a superseded figure unmarked.

**Every `of 787` below is arithmetically correct as a share of ROWS and is the
wrong share of FACILITIES.** They are left as measured rather than rewritten,
because the rows are what was counted; read each one against this note. The two
places the noun is actually wrong are called out where they appear.

*Written 2026-09-02. This is the methodology record: what was pulled and from
where, how the rows were made, how entities were attributed, what was decided
and why, what the known limits are, and how often it has to be re-pulled. It is
not the product copy (`docs/datasets/_descriptors.json`) and not the codebook
(`docs/codebooks/`).*

**A note on the figures.** `[measured]` means the figure was re-counted from
the live file with `csv.reader` on 2026-09-02. `[from the record]` means it
came from a build log or docstring without independent measurement. Where a doc
and the data disagreed, the measurement won; the disagreements are listed at
the end.

**Readiness: READY.** [measured — `docs/DATASET_READINESS.md`, regenerated
2026-09-02: 54 tables, 54/54 grain, 54/54 keys, duplicates clean, 0
aggregation-unsafe, rebuild declared. Generations of the per-dataset doc from
2026-09-01 report BLOCKED on C1/C2/C5 and are one day stale.]

---

## The thing a reader has to accept before anything else

**Per-facility gaming revenue does not exist publicly, and no amount of
collection effort will produce it.** NIGC publishes gross gaming revenue by
region and in revenue bands, never per operation. Five states seal per-tribe
revenue outright: **Arizona by statute (A.R.S. § 5-601.02(H)(1) *requires*
aggregation), Nevada (NRS 463.120), North Dakota (N.D.C.C. §54-58-02), Kansas,
and Wisconsin by compact confidentiality clauses** — the Legislative Fiscal
Bureau says so itself.

Cedar's answer is `gaming_revenue_bounds.csv`: **13,803 bound rows covering 694
of the 787 facilities (88%)**, each with a lower bound, an upper bound, a basis
and an assumption note. That is a real answer to the question, and §5 explains
exactly why those bounds must never be summed.

**One narrow exception exists and it is 0.9% wide.** Where a *public SEC
registrant* manages, develops or owns the property, its filings state the
property's revenues or the fee it earned from them. That reaches **7 of 787 rows
(~0.96% of the 734–780 real facilities; see the denominator note in §1)**  ~~facilities** and is held in `sec_gaming_financial_disclosures.csv` as its own
assertion class - see "Rate inversion, third attempt" in §4. It does not make
the sentence above less true.

---

## 1. Sources

### Federal

**NIGC (`nigc.gov`) is the spine.** Five surfaces were harvested: the ordinance
index (`tablepress-1`), the declination-letter index (`tablepress-2`), the
GGR-by-region PDFs, the gaming-location map (a WordPress `wpgmza` plugin), and
— added 2026-09-01 — **the whole `wpdm` document surface: 72 categories and
4,071 documents, enumerated from
`wp-sitemap-posts-wpdmpro-{1,2,3}.xml`.**

**BIA**: the gaming land decisions index → `gaming_land_decisions.csv`, **138
rows** (Approved 104 / Disapproved 29 / Pending 5) [measured]; the compact PDFs
(1,187 files, 2.0 GB); and the NEPA EA and appendix corpus.

**Federal Register** gaming actions live in the `federal-register` collection
and are joined, not duplicated.

**SEC EDGAR** — Mohegan (27 10-Ks, FY1996–2022) and Seneca Gaming (11 10-K and
S-4 filings, FY2004–09) for audited per-property device and room counts;
Everi, IGT, Light & Wonder and PlayAGS for manufacturer KPIs; vendor filings
for tribal-regulator licences.

**Federal Audit Clearinghouse** (`api.fac.gov`) single audits; **DOL Form
5500**; **OSHA ITA 300A**; **Census LODES8 WAC**; the **US Census Geocoder**.

### State regulators actually pulled

Connecticut (`data.ct.gov`, dataset `i6ts-ib7c`), California (CGCC, 181
documents), Florida (EDR), Washington (WSGC compacts), Wisconsin (Legislative
Fiscal Bureau, 7 biennial editions), New York (NYSGC), Arizona (ADG), Michigan
(MGCB), New Mexico (`gcb.nm.gov`), Oklahoma (OMES).

### What was deliberately not used, and why

| not used | reason |
|---|---|
| **Casino City Press / `tribal_property_list`** | A licensed vendor panel. *"Casino City may be read for QA and may never be published or resold."* Enforced as machinery rather than prose — `cedar_codebook.LICENSED_SOURCE_FILES` blocks `gaming_property_capacity_history.csv` and `gaming_facility_metrics.csv` as whole files, and `LICENSED_COLS = {casino_city_id}` blocks the column. **Note that `tribal_property_list` IS Casino City**: `23d_build_gaming_facilities.py` writes `open_date_basis = "Casino City Tribal Property List, 'Open Date'"`, so `TPL-` ids count as vendor |
| CT `payout` and `hold` columns | Connecticut changes units mid-series without renaming the column: `91.45` in January 1993 against `0.912` in December 2025. Withheld |
| `Mohegan Sun Prior Period Adj.` | An accounting adjustment, not a month of operations — excluded by name. **This is why the source says 748 casino-months and Cedar says 747; both are right about different things** |
| FL EDR Revenue Estimating Conference forecast | *"a projection document with two rows labelled Actual"*, plus a one-row column shift. **Publishing a forecast as an actual is the named error** |
| `bia_compact_properties_geocoded_v2.csv` (766 rows) | Addresses regex-extracted from compact PDFs — `11 Supreme Court`, `202 East Drive`; 590 of 766 `No_Match`; nothing keys to a facility |
| **`pdftotext -layout`** | Rejected as a **method**, not as a tool preference, after it shifted every row of the Wisconsin tables — **booking $109.9M of Potawatomi's money to Red Cliff** — and the Michigan and Arizona tables too. Replaced by word-coordinate reading with right-edge column assignment, footed against each document's own printed totals |
| Property websites, in the location build | Held under `logs/_HOSTLOCK_*` by the capacity agent. Coordinated rather than duplicated |
| Arizona per-tribe revenue | **Does not exist**: A.R.S. § 5-601.02(H)(1) requires aggregation. Typed `NOT_PUBLISHED_BY_THIS_BODY`, never `NOT_FOUND` |
| Wisconsin per-property revenue | Prohibited by compact confidentiality clauses |
| Nevada / North Dakota / Kansas per-tribe revenue | Sealed by statute |
| MSRB EMMA document layer | Terms of Use forbid scraping **and forbid using content "to develop or create a database to be sold."** Only the un-gated type-ahead was used, for issuer names only. Logged as a commercial blocker |
| Terms-restricted tribal directories | Colville, CTUIR/Umatilla, Yakama, Chickasaw, NANA/Akima, Southern Ute, Forest County Potawatomi, Stillaguamish — ~~excluded by every route~~ **RELEASED 2026-09-02 for their own public pages by owner ruling** (`PUBLICATION_POLICY.md`, `TERMS-OWNER-RULING-2026-09-02`); the logged refusals are now the harvest worklist. **See §6: the exclusion was source-scoped, and all eight nations were already fully present here through federal and state records** |

---

## 2. How the rows were made

> ⚠ **Script numbers collide heavily in this collection.** `84_*`, `91_*`,
> `153_*`, `155_*`, `157_*`, `158_*`, `160_*`, `88_*` and `95_*` each have two
> or three occupants. `ls code/<n>_*` before citing.

**Directory core.** `code/23d_build_gaming_facilities.py` builds
`gaming_facilities.csv` from the Casino City panel plus the
`votingpatterns_canonical` set plus the Indian Gaming Dataset. **787 rows**;
`facility_id` prefixes **CCP- 595, VP- 164, TPL- 15, CEDAR- 13**;
`casino_city_id` populated on **595**. [measured]

**Compacts.** `code/15a_compacts_inventory.py` → `15b_build_compact_index.py` →
`15c_terms_pilot.py` → `15d_terms_extract.py` → `15e_finalize_terms.py`; then
`code/95_parse_compact_terms.py` re-extracts page-wise with **PyMuPDF**,
because the pre-existing `text/` sidecars had no page delimiters and
`source_page` was therefore uncitable. [measured] `compacts` **707 across 28
states and 286 tribes** (secretarial 518, deemed-approved 165,
secretarial-procedures 22, unknown 2); `compact_versions` **1,158**;
`compact_terms` **1,311**; `compact_structured_terms` **2,887 across 27
states**; `compact_required_reports` **4,121**; `compact_events` **31**.

**NIGC regions and GGR.** `code/84_build_nigc_regions.py`.
`nigc_regional_ggr` **198 region-years, FY2001–FY2025, across four region-schema
versions**; `nigc_region_assignments` **2,438**. [measured]

**Declinations.** `code/90_fetch_nigc_declinations.py` →
`code/91_build_nigc_declinations.py` →
`code/100_finish_declinations_and_employment.py` (OCR plus rebuild) →
`code/174_document_nigc_declination_codebook.py`. 327 letters;
`gaming_source_claims` 113; `gaming_financing_events` 293. [measured]

**Capacity.** `code/91_extract_compact_authorizations.py`,
`code/92_build_gaming_capacity_official.py`, `code/93` / `95` / `97` (Arizona
live and Wayback), `code/94_extract_mi_mgcb_revshare.py`,
`code/96_extract_sec_property_capacity.py`. `gaming_capacity_official`
**6,649 rows, with 0 rows missing `source_url` or `source_quote`** [measured];
by state CT 3,100 · NM 1,278 · OK 680 · AZ 463 · CA 350 · WA 272 · MI 200 ·
OR 84 · ND 51 · SD 37 · NY 37 · WI 24 · MA 20 · NV 16 · MT 14 · PA 9 · NC 8 ·
WY 4 · FL 2.

**State layer.** `code/103_build_california_gaming.py`,
`code/104_build_wa_allocations.py`, `code/105_build_florida_gaming.py`,
`code/107_pull_remaining_states.py` and `code/107b_fill_source_urls.py`.

**Bounds.** `code/106_build_revenue_bounds.py`. `gaming_revenue_bounds`
**13,803 rows, tier B on all**; `nigc_revenue_bands` **20** (4 fiscal years ×
5 bands). [measured]

**Devices, digital and loyalty.** `code/117_build_gaming_devices.py`,
`code/119_build_digital_and_loyalty.py`.

**Ordinances.** `code/118_build_gaming_ordinances.py`
(`fetch|parse|reconcile|codebook`) → `code/122_ocr_ordinance_scans.py` →
`code/153_merge_ordinance_ocr.py`. Links were taken **only from inside
`<table id="tablepress-1">`**, to defeat the WPDM sidebar download trap; 1,151
of 1,152 objects returned HTTP 200; and an md5 cross-check caught **Kialegee's
link serving Kalispel's byte-identical file.**

**The 2026-08-26 universe rebuild.** `code/155_pull_nigc_roster.py` →
`code/157_reconcile_nigc_roster.py` → `code/158_extend_gaming_facilities.py` →
`code/159_extend_gaming_metrics.py` →
`code/160_sync_published_gaming_view.py` →
`code/161_queue_gaming_date_resourcing.py` →
`code/162_resource_dates_from_cedar_evidence.py`.

**Locations.** `code/143_build_gaming_property_locations.py` — all 2,212 rows
carry `built_by_script = code/143_...`. [measured]

**Labor.** `code/156_stage_form5500_gaming_employment.py` →
`code/157_stage_osha_tribe_level_employment.py` →
`code/158_merge_staged_labor_employment.py` →
`code/262_repair_form5500_tribe_attribution.py` →
`code/265_merge_osha_relift_rows.py` → `code/583_labor_surface_factcheck.py` →
`code/589_adjudicate_osha_711.py`.

**Promotion and grain.** `code/344_pull_nigc_document_surface.py`,
`code/585_factcheck_nigc_keys.py`, `code/586_promote_nigc_gaming.py`,
`code/587_gaming_facility_corrections.py`,
`code/588_promote_self_published_claims.py`,
`code/814_gaming_nr_grain_and_conservation.py`.

### The universe rebuild's core method

`157` runs a **six-rung deterministic ladder, one-to-one, with nothing fuzzy
allowed to fire alone**: `exact_name_state` 278 · `core_name_state`
(distinctive-token equality) 80 · `street_state` 38 · `carryover_marker_link`
32 · `name_city_state` 12 · `name_state` 13 = **453 of 496 (91.3%)**.
[measured — `gaming_nigc_roster_link.csv` = 453 rows]

**The ordering is load-bearing.** Running the 1.2 km coordinate carry-over
*first* had **`Sportman's Bar` claim `4 Bears Casino & Lodge`** — one error
producing two wrong answers at opposite ends of the diff.

---

## 3. How entities were attributed

**One resolver, never reimplemented.** `resolve_entity`, imported from
`code/33_apply_party_rulings.py`, is used in every gaming build (92, 95, 103,
104, 105, 106, 107, 117, 118, 119, 156).

**Guards are layered on top as refusals, never as matchers:**

- **Entity-class restriction.** A gaming party may not resolve to a tribal
  college, a BIE school, an Urban Indian Organisation or a financial
  institution — 577 of the then-1,310 spine entities were ordinance-eligible.
  Without that gate a token-subset test hands *Yakama Nation Legends Casino
  Hotel* to the Yakama Nation **tribal school** and *Harrah's Cherokee* to an
  individually Native-owned business called *Cherokee Enterprises Inc*, because
  each beats the real tribe on uniqueness — the real tribe's spine name
  carrying a token (*Confederated* Yakama, *Eastern* Cherokee) the filing does
  not print.
- **State agreement.**
- **The record must be at least as specific as the entity.** The reverse
  direction once *"booked $2.8B onto a school."*
- **`NAME_TRAPS` tokens** — rancheria, santa, san, little, central — **may
  BLOCK a match and may never AWARD one.** Blocking on weak evidence is safe in
  a way awarding on it is not.

**Geography is a ladder, not a gate.** Run ZIP-first and
`HARRAH'S SOUTHERN CALIFORNIA (RINCON)`, 1,400 employees, lands on **San
Pasqual** — ZIP 92082 holds Rincon's Harrah's *and* San Pasqual's Valley View —
and `Twenty Nine Palms Band of Mission Indians`, 720 employees, lands on
**Augustine**, because ZIP 92236 holds both Coachella casinos. In each case the
establishment name **prints the right owner**. Hence the veto: **the record's
own words outrank geography; if the text names or brands any entity other than
the one the ZIP points at, the ZIP match is refused, not reconciled.**

### Tiers

**`tier` / `confidence_tier` is B on every algorithmically extracted row** —
automated results land at B pending human review. [measured:
`gaming_ordinances` tier B on all 1,155; `gaming_revenue_bounds` tier B on all
13,803.] `entity_tier` is separate and **inherited**: ordinances **A 665 / B
490**; facilities **A 228 / B 557 / blank 2**; metrics inherit the facility's
tier by exact `facility_id` join (18,313 rows tier A, 47,123 tier B).

### Measurement typing is asserted at import, per row

`cedar_domain.may_promote(AUTHORIZED_MAXIMUM, ACTIVE_FLOOR_COUNT)` is asserted
`False` in every build, and `gaming_ordinances` carries
`authorisation_measurement_type = LEGAL_AUTHORISATION_NOT_A_COUNT` on **all
1,155 rows** [measured]. A compact ceiling is what a tribe **may** operate; it
is not a count of what exists.

### Evidence

A verbatim quote is required wherever the *claim* is contestable. **0 of 6,649
`gaming_capacity_official` rows and 0 of 494 `state_gaming_observations` rows
lack `source_url` or `source_quote`.** [measured]

---

## 4. Decisions that shaped the data

### Casino City: keep the ids, replace the evidence under them

Two specifications collided — *preserve the existing property universe* against
*do not depend on Casino City*. The resolution was to keep the vendor-minted
identifiers as stable keys and rebuild the facts beneath them from free
sources.

**Vendor-minted ids are 610 of 787 (77.5%)** — CCP- 595 plus TPL- 15.
[measured] The often-quoted "610 of 774" was true of the pre-rebuild file: the
vendor count is unchanged and the denominator grew.

**The licence gate holds where it is wired.** `gaming_facility_metrics`
(68,211 rows) and `gaming_property_capacity_history` (64,181) are **absent from
`dist/cedar_press.db`**, and the `casino_city_id` column is **dropped** from
the shipped `gaming_facilities` (104 columns in dist against 105 in clean).
[measured]

> **And here is the live gap, stated plainly because no build log states it.**
> The gate is wired at two granularities — whole file, and named column — and
> at **neither of the two that actually carry the vendor into the product.**
> In `dist/cedar_press.db`, `gaming_properties.coords_basis` names Casino City
> on **430 of 784 rows, all 430 carrying a latitude**;
> `gaming_facilities.open_date_basis` names it on **447 of 787**,
> `close_date_basis` on **133**, `open_date_event_basis` on **443**,
> `match_basis` on **164**; and
> `gaming_property_federal_traces.gaming_equipment_source` reads *"Casino City
> capacity panel … VENDOR observation, not a federal record"* on **429 of
> 774**. [measured]
>
> Every one is honestly self-labelled in a `*_basis` column, which is why it is
> visible at all. But the standing rule is *"may never be published or
> resold"*, and **the free-source replacement is built, unmerged and
> unshipped**: `gaming_property_locations.csv` holds 1,068 publishable
> geocoded observations over 539 properties and **is not in the shipped
> database at all.** This is the single largest place where gaming's policy and
> gaming's shipped bytes disagree.

**The laundering rule** is explicit and was honoured: *"re-geocoding the
address does not launder it — the address itself is the vendor's fact."*
Vendor addresses were never sent to the Census geocoder, and **0 rows with
`publishable = Y` trace to Casino City through `source_system` or
`address_source_system`; all 592 `casino_city_press` rows are `publishable =
N`.** [measured]

### The location layer, with its unit stated

`gaming_property_locations.csv`: **2,212 rows over 751 distinct
`property_id`**; `publishable = Y` on **1,471**, `N` on **741**; and **1,068
rows are `publishable = Y` AND carry coordinates, resolving to 539 distinct
properties.** [measured]

**Say which unit you mean.** 1,068 is the count of location *observation rows*;
539 is the count of *properties*. Both figures are correct about different
things, and they have been read as the same number more than once.

`coordinate_withheld_reason` is populated on **50 rows**: NIGC reuses one map
point across a tribe's properties — **19 White Earth locations on a single
point, 18 Chickasaw** — so the coordinate is withheld while the
property-specific address is still geocoded.

**Refused:** auto-attaching 46 same-city NIGC markers. In Flandreau, South
Dakota the only unmatched marker is *Royal River Casino* and the only
vendor-only Cedar row is *First American Mart*, **a convenience store**.

### Revenue bounds: two different mechanisms, and neither is summable

**`gaming_revenue_bounds.csv` records a bound IN-ROW**, not as two rows:
`revenue_lower_bound` (populated on 61), `revenue_upper_bound` (13,544),
`point_value` (309). [measured] `bound_basis`: `REGIONAL_GGR_CEILING` 12,518 ·
`..._NET_OF_KNOWN` 951 · `TRIBE_LEVEL_NOT_ATTRIBUTABLE_TO_A_PROPERTY` 133 ·
`SINGLE_PROPERTY_TRIBE_LEVEL_GAMING_REVENUE` 115 ·
`REPORTED_SLOT_WIN_IS_FLOOR_FOR_GGR` 61 · `UNKNOWN_PROPERTIES_RESIDUAL_SUM` 25.

**Summing is wrong because a regional ceiling is repeated onto every property
in the region-year** — 694 distinct facilities share 12,518 ceiling rows. **The
ceiling is never divided by operation count**, and the reason is measured:
NIGC's own FY2025 distribution has **8.6% of operations holding 55.8% of GGR
while 54.3% hold 4.8%.** Dividing evenly would be a fabrication with a
plausible citation.

**The literal two-endpoint-row shape is in `gaming_projections.csv`**, where a
stated range is recorded as two rows: exactly 2 of the 116 rows carry
`unit = "USD per year (low end of range)"` (75,000) and `"USD per year (high
end of range)"` (125,000) — a Kenosha County human-services expenditure
reduction. [measured] **Summing them adds a range's own low and high to each
other.** 114 of the 116 rows are `observation_status = proposed`, and the whole
table is two projects.

### The California summing trap, measured

`ca_gaming_payments.csv` — **41,758 rows** (RSTF 41,506 + TNGF 252), **37,274
keyed (89.3%)**. `exclusion_flag`: `cumulative_do_not_sum` **12,239** ·
`superseded_by_revised_report` **1,927** · `value_suppressed_by_regulator`
**340** · `not_a_single_tribe` **42** · unflagged 27,210. [measured]

**Naive `SUM(value)` = $155,680,332,479.14. The unflagged total is
$6,527,605,775.83. The rule removes $149.15B — a 23.8× inflation.**

### Rate inversion was tried and rejected, twice

California had 51 `INVERTIBLE_FLAT_RATE` compact rows generating 795 candidate
tribe-level revenue figures. **All 795 were rejected**, because the rates are
**marginal-base**: *"6% of Net Win … in excess of 350 devices."* San Manuel's
$19M at 15% would have printed **$126.7M against a true Net Win an order of
magnitude larger** — with a plausible citation attached. Result: **0 derived
tribe-level and 0 derived property revenue.**

Florida built 44 `BOUNDED_DERIVED_REVENUE` rows, published them in a draft, and
then **withdrew all 44**: EDR publishes *receipts*, which lag the obligation by
one fiscal year through a true-up, and the FY2013/14 test **violated its own
bound** ($1.978bn implied ceiling against $2.098bn stated Net Win).

<!-- BEGIN SEC-GAMING -->
### Rate inversion, third attempt - and this one holds, but only twice

*Added 2026-09-02 by workstream SEC-GAMING (`code/1080_sec_gaming_facility_revenue.py`).
Read it against the two rejections directly above: this is the same manoeuvre,
and the reason it survives here is the reason it failed there.*

California's 795 candidates died because the compact rates are **marginal-base**;
Florida's 44 died because the published series is **receipts on a one-year lag**.
Both failures share a shape: the rate was real but the base was not what it
looked like.

A **management or relinquishment contract disclosed in an SEC filing** can escape
that, and 8 distinct (property, rate) formulas were found across 51 statements in
the cached EDGAR corpus. **Six were refused and two were inverted.**

| contract | rate as filed | inverted? | why |
|---|---|---|---|
| Trading Cove Associates / **Mohegan Sun** | 5% of *Revenues* | **yes**, CY2000-2006 | flat rate, no threshold, and the same filing defines the base: *"gross gaming revenues (other than Class II gaming revenue) and all other facility revenues"* |
| Red Rock / **Graton Resort** | 24% of net income years 1-4, **27% years 5-7** | **yes**, CY2018-2020 | flat within the tier, and those three calendar years sit wholly inside years 5-7 |
| Lakes / **Four Winds** | 24% of net income *up to a threshold*, 19% above | no | **marginal-base, and the threshold is undisclosed** - the California failure exactly |
| Lakes / **Cimarron** | 30% of net income *in excess of $4m* | no | the fee sits above a floor; inversion recovers only the excess |
| Red Rock / **Gun Lake** | never stated | no | the "30% of the facility's net income" in the same 10-K belongs to the **North Fork** project |
| Full House / **FireKeepers** | 30% of revenues | no | that is the **statutory NIGC ceiling** (25 U.S.C. 2711) recited in a regulatory-background section, not the contract's fee |
| Nevada Gold / **Buena Vista** | 25% of net income | no | no fee dollars were ever disclosed against it - the casino had not opened |
| Lakes / **Red Hawk** | 30% of net revenue *as defined* | no | the fee is subordinated and **deferred when operating results are insufficient**, so a year's recognised fee is not 30% of that year's base |

**And the inverted figure is still not "revenue".** IGRA defines *net revenues*
at 25 U.S.C. 2703(9) as gross gaming revenues less prizes and less
gaming-related operating expenses excluding management fees - much closer to
operating profit. So the two derived series are typed
`DERIVED_FACILITY_GROSS_REVENUES_AS_DEFINED` (Mohegan Sun, where the contract's
base genuinely is total facility revenue) and
`DERIVED_FACILITY_NET_INCOME_AS_DEFINED` (Graton), never plain revenue.

This does **not** soften the claim at the top of this document. The route
reaches **7 facilities — 0.9% of the 787 ROWS, ~0.96% of the 734–780 real facilities (denominator note, §1)** and only where a public company's books
ran through the property. `docs/SEC_GAMING_FACILITY_REVENUE_BUILD_LOG.md` is the
full record; `docs/MONEY_TOTALLING_RULES.md` `<!-- BEGIN SEC-GAMING -->` is the
fence, and it forbids summing any of it against `gaming_revenue_bounds.csv`.
<!-- END SEC-GAMING -->

### Ordinances: the OCR merge

264 of 1,155 rows (23%) were image-only scans; **263 were recovered.**
Post-merge provision counts [measured, every figure reproducing the merge log
exactly]: `classes_authorized` 827 · `tribal_gaming_agency_named` 973 ·
`licensing_provisions` 932 · `minimum_internal_control_reference` 355 ·
`chair_or_designee` 596 · `document_approval_date` 542 · `effective_date` 34 ·
`supersedes_quote` 202 · `class_ii_authorized = 1` 670 ·
`class_iii_authorized = 1` 644.

`text_layer_status`: TEXT_LAYER_PRESENT 886 / **OCR_RECOVERED 263** /
IMAGE_ONLY 1 / no document 4. **OCR mean confidence 0.8710, minimum 0.7556,
n = 235** carrying a recorded confidence — 28 documents have blank `ocr_dpi`
and confidence because the killed run did not record whether it rendered at 220
or 300 dpi.

**Refused:** re-OCR'ing those 28 — *"not worth 28 documents of CPU."*
**Refused:** normalising `chair_or_designee` across OCR variants (Harold A.
Monteau is spelled four ways) — that needs a **person** matcher, which
`resolve_entity` is not.

### Employment: three rulings that shaped the table

1. **`FORM5500_ACTIVE_PARTICIPANTS` is an enrollment, never a payroll.**
   `measurement_type_status = NEVER_PROMOTES_TO_ACTIVE`.
2. **The table admits tribe-level rows with no `facility_id`** — **2,617 of
   3,421 (76.5%) are blank** [measured] — because a Form 5500 names a **plan
   sponsor** and an OSHA 300A names an **establishment**. Requiring a facility
   would mean inventing an attribution.
3. **OSHA and Form 5500 are not reconciled.** The median Form 5500 / OSHA ratio
   across overlapping tribe-years is **1.03** — the same people, measured two
   ways — and 332 tribe-level OSHA rows are the same 300A as a facility-grain
   row, flagged `already_facility_attached = 1`.

**The coverage argument for pooling them** is the clearest case in the project
for judging a threshold on the harmonised measure rather than on each input.
Against the 284 tribes that operate a gaming facility: **DOL Form 5500 reaches
140 tribes (46%), OSHA ITA reaches 86 (30%), and the pooled table reaches 243
(86%).** No single source clears half; the union clears six sevenths. Dropping
OSHA at 30% would remove tribes Form 5500 never sees.

---

## 5. What a buyer may total

| table | additive? | what double-counts |
|---|---|---|
| `gaming_capacity_official.csv` (6,649) | yes, **within one `measurement_status`** | **never pool `reported_revenue`, `reported_measurement` and `authorization`.** An authorization is a compact **ceiling** — what a tribe *may* operate — and summing it with counts of what exists produces a number that describes nothing. Metric names carry `_authorized_max` so the distinction survives any filter |
| `gaming_property_self_published_claims.csv` (270) | **NO** | **a machine count a casino advertises is a claim, not a measurement.** 162 of the 270 are BOUNDS ("more than 1,000 slots"), not counts. 9 rows also appear in `gaming_property_site_observations.csv` and are FLAGGED, not dropped |
| `gaming_property_self_published_assertions.csv` (622) | **NO** | never against `gaming_capacity_official`, `nigc_regional_ggr`, `nigc_revenue_bands`, `state_gaming_observations`, `wa_machine_allocations`, or the vendor panel. **A self-published count and a regulator count of the same floor are two claims about one thing** — adding them doubles the floor, and preferring the larger is how a marketing number becomes a statistic |
| `nigc_document_surface.csv` (7,930) | it is a count of **memberships**, not of documents | 7,930 (category, document) memberships over **4,071 distinct documents**. Never sum it against `nigc_ordinances.csv` (1,155) or `nigc_declination_letters.csv` (327) — those are instrument tables and this is the index that measures them. Count with `COUNT(DISTINCT document_slug)` |
| `nigc_enforcement_actions.csv` (362) | one row = one **document** | Not one row per violation. One matter routinely yields a Notice of Violation *and* a settlement agreement — Squaxin Island NOV-06-07 and SA-06-07 are two rows about one event |
| `gaming_property_capacity_history.csv` · `gaming_facility_metrics.csv` | **licensed, never published** | the Casino City vendor panel; internal fact-checking only |
| `fac_audit_sefa_gaming_programs.csv` (1 row) | — | its `amount_expended` is a **federal award expenditure** and is not gaming revenue of any kind |

### The three FAC measures that never sum

Named because ten hand-typed Nevada, North Dakota and Kansas figures span all
three, and totalling them triple-counts the same dollar:

| measure | what it is | why it is not the others |
|---|---|---|
| `CASINO_ENTERPRISE_FUND_REVENUE` | what the gaming enterprise **earned** in the period | gross to the enterprise, before anything moves |
| `CASINO_DISTRIBUTION_TO_TRIBE` | cash actually **transferred** to the tribal government | a subset of revenue, already counted inside it |
| `CASINO_PAYABLE_TO_TRIBE` | an obligation **recorded** and not yet paid | a balance-sheet position, not a flow — adding it to a distribution counts the same dollar in the year it was owed and again in the year it was paid |

**Sum at most one of the three, and say which.** A single tribe-year can carry
all three legitimately.

**And the grain of a self-published claim is a claim OCCURRENCE, not a fact:**
two sentences on one page stating the same number about two different ballrooms
are two rows, and collapsing them deletes a ballroom. 229 of the 270 claims
were **recovered from a refusal pile** by `code/383` and are published because
a refusal that hides the claim is worse than one that labels it — not because
they got better.

---

## 6. What was excluded on purpose

> **SUPERSEDED 2026-09-02 by owner ruling** (`docs/PUBLICATION_POLICY.md`, `TERMS-OWNER-RULING-2026-09-02`): a tribal website's terms language no longer blocks harvest, and all eight are released for harvest of **their own public pages**. The exclusions below are kept as the *observation* of what each publisher stated - and as the worklist the ruling creates. Still binding, none of them a terms question: technical access controls; a natural person's data apart from their public role (the business row may be harvested, `owner_name_raw` / `email` / `phone` / `address_raw` may not be published); EMMA/MSRB + CUSIP Global Services, a third-party licensor; Casino City and D-U-N-S. The two-layer enforcement described below still stands as
> **machinery**; what changed is which hosts it holds.

~~Sources marked `TERMS_STATED_RESTRICTIVE` are excluded by **every** route,~~
including a harmonised derivative. Enforcement is two-layered: a
`NAMED_RESTRICTIVE` host list in `code/701_enterprise_and_business_list_sweep.py`
(mirrored in `code/690`), which is **unioned into** the registry verdicts and
never consulted alone — *so that a registry row losing its verdict cannot
silently re-open a refused publisher* — and the registry of record,
`review/tribal_vendor_list_registry_2026-08-26.csv`: **359 rows, with
`source_terms_status = TERMS_STATED_RESTRICTIVE` on exactly 9**, each carrying
the verbatim quote that justifies it. `consent_status = UNRESOLVED` on all 359.
[measured] The gate is
`code/321_gate_tribal_source_restriction.py`, whose governing line is
**"SILENCE IS UNRESOLVED, NEVER PERMISSION."**

The nine: **Navajo**, **Confederated Colville**, **Confederated Yakama**,
**CTUIR / Umatilla**, **The Chickasaw Nation** (terms naming company
directories specifically), **Forest County Potawatomi**, **Southern Ute**,
**NANA Regional** (*"copied, reproduced, aggregated, republished … or otherwise
exploited"* — a sitemap enumeration was **stopped mid-run** when the terms were
read), **Stillaguamish**.

**The exclusion is SOURCE-scoped, not ENTITY-scoped, and that matters here.**
All eight nations remain fully present in gaming, because their gaming rows
come from federal and state records that are public by statute. [measured]

| | facilities | ordinances | compacts | capacity |
|---|---:|---:|---:|---:|
| Chickasaw | 28 | 1 | 4 | 41 |
| Colville | 4 | 4 | 1 | 12 |
| Stillaguamish | 2 | 6 | 1 | 7 |
| Umatilla | 2 | 6 | 1 | 10 |
| Forest County Potawatomi | 3 | 4 | 5 | 1 |
| Yakama | 1 | 4 | 1 | 6 |
| Southern Ute | 1 | 5 | 2 | 0 |

**Asking is the route back in; a cleverer scrape is not.**

---

## 7. Known limits

| limit | measured |
|---|---|
| Vendor-minted property ids | **610 of 787 (77.5%)** |
| Vendor provenance still in the shipped tables | `coords_basis` names Casino City on **430 of 784**; `open_date_basis` on **447 of 787** |
| `gaming_property_locations.csv` is not shipped | absent from `dist/cedar_press.db` |
| Ordinance tribe identity | 1,155 rows → **301 distinct `tribe_id`, 48 blank, 314 distinct `tribe_name`**. NIGC's "321" is the count of `ORIGINAL_ORDINANCE` rows, **not of tribes** — anyone building a per-tribe denominator off it overstates by about 7% |
| `property_status` | current **451** · **blank 334 (42.4%)** · approved 1 · closed 1. A reader of the shipped sample concludes the directory is a live-facility list; it is 57% status-known |
| `open_date` precision | year 288 · day 188 · month 159 · **blank 151** · decade 1. `open_date_class`: exact 635 · bounded 90 · **absent 62** |
| Facility source URLs | `open_date_source_url` on **192 of 787** |
| Per-facility revenue | **does not exist publicly.** The best available is 13,803 bounds over **694 of 787 rows**, and **0 region-years reduce to a single unknown operation** |
| Region is not state | NIGC's Washington DC region spans AL, CT, FL, LA, MS, NC and NY. Connecticut is 2 of 46 operations in FY2025 |
| Two NIGC universes disagree | 490 mapped locations against **545 FY2025 audited-statement operations** — one submitter can cover several properties, so a 1:1 correspondence is unreachable |
| Geocoding on tribal land fails at ten times the national rate | **263 of 639 free-sourced addresses returned `No_Match` — 41%**, against single-digit national norms. A ZIP-only retry recovered **1 of 261** |
| Vendor comparison, n = 30 | **17 of 30 (56.7%) agree within 5%.** Median absolute difference by metric: hotel rooms 0.0% · gaming machines 4.5% · **parking spaces 43.1%** |
| `wa_machine_transfers` | **0 rows, by design** — WSGC receives only a *count* of Appendix D transfers since 2007, never the documents. The highest-value unfetched state item |
| `gaming_property_federal_traces` | **774 rows against a 787-row facility universe** — not rebuilt after the 2026-08-26 appends |
| `digital_gaming_revenue` | clean **10,766**, dist **10,661** — the shipped copy is **105 rows behind** |
| No gaming class on the facility record | Class II against Class III is the first regulatory fact about a tribal casino and there is no class column. `gaming_ordinances.csv` carries `class_ii_authorized` / `class_iii_authorized` for 301 tribes, and **263 of the 284 facility-bearing tribes (93%) have one** — tribe-grain, so it is a stated-caveat join, not a free one |
| A column that cannot say what it needs to | `property_status = current` beside `close_date = 2006-04`. **113 of 787 rows are in that state and every one is factually right** — the column simply cannot express "was current at the observation date" |

---

## 8. Refresh

| source | cadence | Cedar holds | what breaks if not re-pulled |
|---|---|---|---|
| NIGC GGR by region | **annual, ~10-month lag** (FY closes 30 Sep, report about mid-following-year) | FY2025 — the newest published; **nothing owed until mid-2027** | the revenue-bound ceilings freeze. Its `fiscal_year` is a **bare year** and must never be written as `2025-12-31` |
| NIGC document surface | irregular, as issued | index read 2026-09-01. **The refresh signal is the index's own counts — 1,162 ordinances and 329 declinations against Cedar's 1,155 and 327, i.e. +7 and +2** | the five `nigc_*` tables and their contracts |
| NIGC ordinances | irregular | index last read 2026-08-12; Cedar's edge is `document_approval_date` 2026-06-02 | the OCR merge must re-run. **Never re-run `118 parse` after a merge — it rebuilds from the PDFs and discards the OCR** |
| CT DCP monthly casino win | **monthly — the only true monthly gaming series Cedar holds** | 2025-12-31, which is every casino-month the source serves. **The 238-day lag is Connecticut's, re-proved live** | nothing. The "cheapest win" reading of that gap was wrong |
| CA CGCC RSTF | quarterly | 2026-06-30 | `ca_gaming_facilities_official`. **Do not re-fetch the 95th and 97th reports** — they are `CAPTURED_NOT_PARSED` with a measured footing discrepancy |
| MI MGCB | monthly, ~3-week lag | 2026-07-31 | `digital_gaming_relationships` entity links |
| NM GCB | quarterly | 2026-06-30 | `gaming_capacity_official` row conservation. **New Mexico was never a fetch problem** — it was a promotion job recorded as an acquisition task |
| AZ ADG | quarterly device reports, annual aggregate | 2026-07-01 | nothing |
| Other state regulators (WI, NY, WA, FL) | annual, mostly; **Florida is on a compact schedule and is forward-dated** | 2025-06-30 | **`fl_gaming_payments.period_end` runs to 2031-06-30. Those are forward-dated compact SCHEDULE rows, not observations. Never read them as freshness** |
| DOL Form 5500 + OSHA ITA | annual | both corpora held through CY2025; nothing newer published | **NOT A PULL** — `code/158_merge_staged_labor_employment.py`, and it is blocked on two owner rulings, not on a fetch. **A Form 5500 row keys to an EIN, never to a facility** — merging it as a property observation would be a grain error |
| FAC SEFA (gaming programs) | continuous acceptance, median 271-day lag | 2021 | `fac_audit_gaming_disclosures.csv` |

[measured — `docs/REFRESH_CADENCE.json`, regenerated 2026-09-02]

**Read the "published and not pulled" state against "pulled and not promoted"
before planning any session.** They look identical in a staleness column and
are completely different work. Three times this project has recorded a
promotion job as a fetch and sent the next agent to re-download something
already on disk: California RSTF, New Mexico FY2023–2026Q2, and the staged NIGC
set. **All three were promotions. None was ever a fetch.**

---

## Stale claims found while writing this

1. **`docs/DOC_CONTRADICTIONS_2026-08-26.md` item C5 is itself wrong, and it
   put a do-not-quote banner on a correct line.** The register says
   `GAMING_LOCATION_LAYER.md`'s *"Tier distribution of publishable rows: A 689
   · B 101 · C 681"* **"cannot be what it says"** and is *"undecidable from the
   files."* **Measured over `publishable = Y` rows only: A 689 · C 681 · B 101
   — exactly right, reproducing to the row.** The sum 1,471 *is* the
   `publishable = Y` count; the `N` rows split X 592 / C 149. The two questions
   being confused were *publishable* (1,471) and *publishable with coordinates*
   (1,068). **The banner is now propagated into `GAMING_LOCATION_LAYER.md` in
   two places and should be retracted** — this is the arbiter itself creating a
   contradiction rather than settling one.
2. **`gaming_employment_observations.csv` now has FOUR live values in the
   docs**: 769 (`GAMING_EMPLOYMENT_LOG.md`, `GAMING_FACILITY_HUB_LINKAGE`,
   `GAMING_SOURCE_AUDIT` seven times, `LABOR_SOURCES_FOR_GAMING` throughout),
   3,300 (`ASSUMPTIONS_AND_LIMITATIONS.md` — a *planned* figure never counted
   from the file), 3,246 (the contradictions register's evening addendum), and
   **3,421 measured**. Only `docs/PUBLICATION_POLICY.md` is right. Sub-counts
   are stale too: the addendum's `FORM5500_ACTIVE_PARTICIPANTS` 1,975 and
   `OSHA_TRIBE_LEVEL_REPORTED` 502 measure to **1,956 / 696**, and the tribe
   count 239 measures to **243 distinct `tribe_id`, 36 blank**.
3. **Ordinance tribe identity has four values in the docs and none is
   current**: 321 (`START_HERE.md`, `GAMING_SPEC_RECONCILIATION`), 305
   (`GAMING_ORDINANCE_BUILD_LOG`), 299 (arbiter, 2026-08-26), 302 (arbiter
   re-measure, 2026-09-01). **Measured: 301 distinct `tribe_id`, 48 blank, 314
   distinct `tribe_name`.** The row arithmetic (321 + 834 = 1,155) is right
   everywhere. Note also that the OCR merge log's provision "tribe" counts
   (310 / 307 / 317) are counts of **`tribe_name`** — measured 303 / 302 / 310
   today, and 291 / 291 / 298 by `tribe_id`. **State the key.**
4. **`docs/datasets/gaming_sources.md` contradicts itself inside one file.**
   Its §1B table says `ca_gaming_payments` **40,164**; its own §1E and its
   generated coverage block say **41,758**. Measured 41,758. Same shape for
   `gaming_capacity_official`: `GAMING_CAPACITY_OFFICIAL_LOG.md` says 6,461
   against a measured **6,649** (the +188 New Mexico promotion).
5. **`docs/WHAT_IS_MISSING.md` says `gaming_property_locations.csv` carries
   county for 1,067 observations** and describes the facility file's coverage
   accurately, but several of its gaming figures move with the file. Prefer a
   fresh measurement.
6. **`docs/GAMING_UNIVERSE_REBUILD_2026-08-26.md` and
   `docs/GAMING_LOCATION_LAYER.md` say "610 of 774."** Measured **610 of
   787** — the vendor count is unchanged and the denominator grew. Wherever
   "774 properties" appears as the universe: `gaming_facilities` is **787**,
   `gaming_properties` **784**, and **`gaming_property_federal_traces` is still
   774**, never rebuilt after the appends.
7. **`docs/FACT_CHECK_2026-08-06.md` and `docs/COVERAGE_AUDIT.md` give the
   open-date distribution as exact 635 / bounded 90 / absent 49.** Measured
   exact 635 / bounded 90 / **absent 62** — the denominator moved 774 → 787.
8. **`docs/GAMING_SPEC_RECONCILIATION.md`'s own banner has gone stale.** It
   carries the superseded 299/55 ordinance figures and the FAC pair
   6,774 / 2,046 (correct: **6,780 / 2,052**) — a banner added to fix stale
   numbers, now stale itself.
9. **`dist/` lags `data/clean/` on one gaming table**: `digital_gaming_revenue`
   is **10,766 in clean and 10,661 in dist** — the 105-row 2026-09-01 Arizona
   and Michigan append never shipped. Every other gaming table checked matched.
10. **Generations of `docs/datasets/gaming*.md` from 2026-09-01 report gaming
    BLOCKED** on C1 (grain unstated on 7 of 52 tables), C2 and C5 (row
    conservation 1/52). **The scoreboard regenerated 2026-09-02 rates gaming
    READY at 54/54 on grain and keys.** One day stale.
