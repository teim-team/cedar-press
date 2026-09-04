# Nonprofit financial layer (Dataset 6) — build log, 2026-08-05

Build script: `code/33_nonprofit_financials.py` (one script, `--steps pull,build,report`)
Run log: `logs/33_nonprofit_financials.log`
Raw cache: `data/raw/external/propublica_990/` (1,157 JSON files + `_fetch_log.csv` + `_SOURCE_MANIFEST.csv`)
Plan: `docs/plans/NONPROFIT_DATASET_PLAN.md` · Prior build: `docs/NONPROFIT_BUILD_LOG_2026-08-05.md`

**Source, on every row:** ProPublica Nonprofit Explorer API v2,
`https://projects.propublica.org/nonprofits/api/v2/organizations/{ein}.json`,
free and keyless. ProPublica republishes the IRS SOI e-file extracts.
**Vintage: retrieved 2026-08-05.** Organization records in the responses carry
`data_source = current_2026_07_21` (the IRS BMF snapshot ProPublica was serving).

Every figure in `np_financials.csv` and `np_org_scale.csv` is copied from a
response body that is on disk in the cache above. Nothing is estimated,
imputed, interpolated, deflated or back-filled. Where the API returned no
value, the cell is blank and the org's `scale_band` is `none`.

## What shipped

| File | Rows | What it is |
|---|---:|---|
| `data/clean/np_financials.csv` | 8,507 | One row per EIN-filing-period. 662 unique EINs. |
| `data/clean/np_org_scale.csv` | 1,157 | One row per pulled EIN, latest year + `scale_band`. |
| `data/raw/external/propublica_990/` | 1,157 JSON | Verbatim API responses, the audit trail. |

Nothing under `data/spine/`, `data/clean/cedar_*`, `review/cedar_review*.html`
or `np_orgs.csv` was modified. `np_orgs.csv` was read only.

## 1. Scope pulled

| Set | EINs | Source |
|---|---:|---|
| `confidence_tier = A` | 1,090 | `data/clean/np_orgs.csv` |
| `recheck_candidate = 1` | 67 | `data/spine/nonprofit_exclusion_rulings.csv` |
| place-name risk queue | 412 | `review/np_placename_risk_2026-08-05.csv` |
| **union pulled** | **1,157** | |

The 412 place-name rows overlap tier A almost entirely; the union is 1,157, not
1,569. The remaining 11,607 rows of `np_orgs.csv` were deliberately not pulled.

**API result: 1,157 of 1,157 requests returned HTTP 200. Zero failures, zero
404s, zero retries consumed.** Throttled at 1.05 s between requests; the full
pull took 1,353 s (~22.5 min). Resumable: `--steps pull` skips any EIN already
cached, so a stall costs only the in-flight request.

## 2. THE PLACE-NAME PROBLEM, PRICED

This is the finding that matters for the review queue. The 412 organizations on
the place-name risk list are not evenly consequential — **the top 5 carry 80.3%
of the money, and half the list has no financial record at all.**

### Place-name-risk organizations ranked by latest-year total revenue

| # | Organization | St | Year | Total revenue | Risk |
|---:|---|---|---|---:|---|
| 1 | Umatilla Electric Cooperative Association | OR | 2023 | $603,100,445 | HIGH |
| 2 | Yavapai Community Hospital Association | AZ | 2023 | $464,055,792 | HIGH |
| 3 | Lumbee River Electric Membership Corporation | NC | 2023 | $158,192,273 | HIGH |
| 4 | Jemez Mountains Electric Cooperative Inc | NM | 2023 | $56,355,734 | HIGH |
| 5 | Lumbee Land Development Inc | NC | 2023 | $50,533,617 | REVIEW |
| 6 | West Yavapai Guidance Clinic | AZ | 2023 | $39,380,385 | REVIEW |
| 7 | Douglas-Cherokee Economic Authority Inc | TN | 2023 | $30,366,317 | REVIEW |
| 8 | Kickapoo Springs Foundation | TX | 2023 | $24,258,103 | REVIEW |
| 9 | Sac Osage Electric Cooperative Inc | MO | 2023 | $24,086,589 | HIGH |
| 10 | Tuscarora Intermediate Unit Capital Insurance Trust | PA | 2023 | $22,511,780 | REVIEW |
| 11 | Pawnee Valley Community Hospital Inc | KS | 2023 | $21,487,951 | HIGH |
| 12 | Umatilla-Morrow County Head Start Inc | OR | 2023 | $14,115,888 | HIGH |
| 13 | College Of The Menominee Nation | WI | 2023 | $13,881,692 | REVIEW |
| 14 | Rosebud Community Hospital Inc | MT | 2023 | $11,432,053 | HIGH |
| 15 | Rosebud Electric Cooperative Inc | SD | 2023 | $10,015,700 | HIGH |
| 16 | Legacy Traditional School-Peoria | AZ | 2023 | $8,059,439 | REVIEW |
| 17 | Ascension Living Via Christi Village Ponca City | MO | 2023 | $7,225,231 | REVIEW |
| 18 | Society Of St Vincent De Paul Peoria Council | IL | 2023 | $6,954,358 | REVIEW |
| 19 | Onondaga Case Management Services Inc | NY | 2023 | $6,897,956 | REVIEW |
| 20 | Onondaga Community College Foundation Inc | NY | 2023 | $6,430,764 | REVIEW |
| 21 | Onondaga Golf And Country Club | NY | 2023 | $5,386,340 | REVIEW |
| 22 | Yavapai College Foundation | AZ | 2023 | $5,248,730 | REVIEW |
| 23 | Onondaga Community College Housing Development Corp | NY | 2023 | $4,720,458 | REVIEW |
| 24 | St Lukes Health Foundation Of Sioux City Iowa | IA | 2023 | $3,979,755 | REVIEW |
| 25 | Akwesasne Boys & Girls Club St Regis Mohawk Tribe | NY | 2022 | $2,842,147 | REVIEW |

Full ranking of all 40 revenue-bearing leaders is in `logs/33_nonprofit_financials.log`.
Ranked by `total_revenue` in `np_org_scale.csv`, filtered on `in_placename_risk = 1`.

### Concentration

| Cut | Latest-year revenue | Share of the 412-org total |
|---|---:|---:|
| top 1 | $603,100,445 | 36.4% |
| top 5 | $1,332,237,861 | 80.3% |
| top 10 | $1,472,841,035 | 88.8% |
| top 25 | $1,601,519,497 | 96.6% |
| all 203 with revenue | $1,658,535,958 | 100% |

### Scale distribution of the 412

| Band | Orgs |
|---|---:|
| `none` (no financials returned at all) | 209 |
| `under_50k` | 61 |
| `50k_1m` | 99 |
| `1m_10m` | 28 |
| `10m_100m` | 12 |
| `over_100m` | 3 |

**Operational read: 270 of 412 (65.5%) are either invisible to the API or under
$50k. Ruling on them changes no aggregate.** The queue should be worked
top-down; roughly 15 rulings settle 90% of the exposure.

### What it costs the tier-A aggregate

| | |
|---|---:|
| Tier-A orgs with any latest-year revenue figure | 523 of 1,090 |
| Tier-A latest-year revenue, as pulled | $2,393,227,681 |
| of which sits in place-name-risk orgs | **$1,658,535,958 (69.3%)** |
| remainder, still unruled | $734,691,723 |

This confirms and sharpens the prior build's warning. **Neither number is
publishable as Native nonprofit revenue** — tier A is an unruled screened
candidate set, and the $734.7M remainder is not "the clean part," it is merely
the part the place-name flag did not catch. It is quoted here only to size the
contamination.

### The risk list itself has false positives — read the ranking as triage, not verdict

At least four entries in the top 40 look like genuine Native institutions
mis-swept by the place-name flag, and they are the ones a ruling would *promote*
rather than exclude:

- **College Of The Menominee Nation** (WI, $13.9M) — an AIHEC tribal college.
- **Akwesasne Boys & Girls Club St Regis Mohawk Tribe** (NY, $2.8M) — names the tribe in its own title.
- **United Houma Nation Inc** (LA, $1.4M) — a state-recognized tribal body.
- **Lumbee Regional Development Association Inc** (NC, $1.9M) — Lumbee-affiliated; distinct from Lumbee River Electric (#3), which is a rural co-op.

The flag fired on tokens, so it is symmetric: it catches co-ops named for a
tribe *and* tribal institutions named for their place. Revenue does not settle
which is which; it only says which mistake is expensive.

## 3. LOBBYING DISCLOSURE — the cross-check does not clear from this source

**Non-zero lobbying expenditures found: 0. Not because organizations reported
zero, but because the ProPublica Nonprofit Explorer API v2 does not carry a
lobbying dollar field at all.** Stated plainly so it is never mistaken for a
measured zero.

Verified exhaustively, not sampled. Across all **5,108** filings with parsed
financials in the cache, the union of response keys is **207 distinct fields**,
and the complete set of lobbying-related fields is:

| Field | Form | Present on | Values observed |
|---|---|---:|---|
| `infleg` (influencing legislation) | 990-PF only | 233 filings | `N` on 233 of 233 |
| `propgndacd` (propaganda / legislation activity) | 990-PF only | 233 filings | `N` on 233 of 233 |

Neither is a dollar amount; both are Y/N indicators, and both are `N` on every
990-PF filing pulled. There is **no `lobb*`-named field anywhere in the
corpus** — no Schedule C Part II-A/II-B totals, no §501(h) election amounts, no
grassroots-vs-direct split, for any form type.

`lobbying_expenditure` is therefore **blank on all 8,507 rows**, with
`lobbying_field_basis` recording why per row (`990pf_infleg_indicator_only` on
990-PF rows, `not_exposed_by_api` elsewhere). Blank means not observed. It does
not mean zero, and the column must never be summed or treated as a measured
value.

**The same applies to `n_employees`** (Form 990 Part I line 5): no employee-count
field exists in the extract. Blank on all rows, `n_employees_basis = not_exposed_by_api`.

### What this means for the Dataset 4 cross-check

The 990-vs-LDA independent measurement described in `docs/plans/NONPROFIT_DATASET_PLAN.md`
**cannot be built from this API.** It is not blocked by coverage or by cost — the
field simply is not in the SOI extract ProPublica republishes. Schedule C lives
only in the IRS 990 e-file **XML**.

Routes tested and their status:

- **IRS e-file XML via `latest_object_id` → S3.** The org record exposes
  `latest_object_id` (e.g. `202541969349302779` for Oglala Lakota College).
  Both `https://s3.amazonaws.com/irs-form-990/{id}_public.xml` and the
  `apps.irs.gov/pub/epostcard/cor/` path return **HTTP 404**. The per-object S3
  fetch that used to make this a one-request-per-org job is dead.
- **IRS bulk 990 XML ZIPs** (`apps.irs.gov/pub/epostcard/990/xml/{year}/`) remain
  the live path, and Schedule C (`IRS990ScheduleC`, `TotalLobbyingExpendituresAmt`,
  `LobbyingNontaxableAmt`) is in them. That is a multi-GB staged download, which
  is exactly the "990 XML financial panel" already scheduled as phase 2 in
  `docs/plans/NONPROFIT_DATASET_PLAN.md` and listed as not-done in the prior build log.

Recommendation: keep the lobbying cross-check on the phase-2 XML ticket and do
not re-attempt it through the API. `np_financials.csv` already carries the
`lobbying_expenditure` and `n_employees` columns so the XML pass can populate
them in place without a schema change.

## 4. Coverage

### Did the API return anything?

| Outcome | EINs |
|---|---:|
| HTTP 200 | 1,157 (100%) |
| returned at least one filing record | 662 |
| returned at least one filing **with parsed financials** | 573 |
| returned zero filings of any kind | 495 |

### Scale bands

| Band | All 1,157 | Tier A (1,090) | Recheck (67) | Place-name (412) |
|---|---:|---:|---:|---:|
| `none` | 584 | 567 | 17 | 209 |
| `under_50k` | 178 | 164 | 14 | 61 |
| `50k_1m` | 284 | 262 | 22 | 99 |
| `1m_10m` | 77 | 64 | 13 | 28 |
| `10m_100m` | 30 | 29 | 1 | 12 |
| `over_100m` | 4 | 4 | 0 | 3 |

`scale_band` is computed from `total_revenue` on the **latest filing that has
parsed financials**, and `scale_band_basis` names that filing's tax period and
form on every row. `none` means the API returned no parsed revenue figure —
never that revenue is zero.

### Filings by form type

| Form | Filings | with financials | PDF-only |
|---|---:|---:|---:|
| 990 | 5,395 | 3,221 | 2,174 |
| 990EZ | 2,678 | 1,654 | 1,024 |
| 990PF | 434 | 233 | 201 |
| 990N | 0 | 0 | 0 |

**990-N never appears.** ProPublica's filing arrays do not include e-Postcard
records, so the 572 tier-A organizations the BMF marks `990_N` can only ever
come back empty here. That is a source limitation, not evidence about the orgs.

`form_type` is normalized from the response's integer `formtype` (0/1/2). The
raw `formtype_str` values carry ProPublica PDF annotations (`990O`, `990R`,
`990EOR`, …, where O = filed with Schedule O and R = restated) and are preserved
verbatim in `form_type_raw`.

### The BMF tier prediction holds up

| BMF `tier` | API returned financials | did not |
|---|---:|---:|
| `full_990` | 269 | 4 |
| `990_EZ` | 102 | 8 |
| `990_N` | 160 | 438 |
| `not_required_to_file` | 42 | 123 |
| `UNKNOWN` | 0 | 11 |

98.5% of `full_990` orgs returned financials; 73% of `990_N` orgs returned
nothing. The 160 `990_N` orgs that *did* return financials are organizations
that filed a full 990 or 990-EZ in an earlier year and have since dropped to
postcard status — the filing history is real, the current-year tier is also
real, and both are recorded.

### Years

Tax years span **1996 to 2025**. 18 rows carry `pre_2000_flag = 1` per the
house temporal floor. Latest filing year among orgs with financials: 2023 for
371 orgs, 2024 for 51. **The filing lag is visible in the data** — as of a
2026-08-05 pull, 2023 is the modal current year, so the "latest" figure in
`np_org_scale.csv` is two to three years trailing for most organizations, and
`latest_year` is on the row so no table can hide it.

## 5. Recheck candidates ranked by revenue

Financial scale for the 67 excluded-but-flagged EINs. Top of the list:

| # | Organization | St | Year | Total revenue |
|---:|---|---|---|---:|
| 1 | Navajo Technical College | NM | 2023 | $48,458,305 |
| 2 | Klamath Family Head Start | OR | 2023 | $9,709,735 |
| 3 | Indian Pueblo Cultural Center Inc | NM | 2023 | $7,697,547 |
| 4 | Pueblo Community College Foundation | CO | 2023 | $7,154,680 |
| 5 | Maricopa County Community College District Foundation | AZ | 2023 | $6,814,984 |
| 6 | Pima Community College Foundation Inc | AZ | 2023 | $4,203,453 |
| 7 | The Cayuga County Community College Foundation Inc | NY | 2023 | $3,753,241 |
| 8 | Mohawk Valley Community College Dormitory Corp | NY | 2023 | $2,593,395 |
| 9 | Faculty Student Assoc Of Cayuga County Community College | NY | 2023 | $2,378,520 |
| 10 | Chippewa Valley Technical College Foundation Inc | WI | 2024 | $1,775,272 |

**`NAVAJO TECHNICAL COLLEGE` (EIN 850303705) is $48.5M and by a factor of five
the largest recheck candidate.** The prior build log flagged it as a probable
false *exclusion* — Navajo Technical University is a real tribally chartered
institution, yet the 2026-04-30 v2 strict pass ruled it out on the ambiguous
"Navajo" token, while `cedar_identifier_ledger_final.csv` carries it as
`entity_class = TRIBAL_COLLEGE`. The financial layer says that ruling conflict
is worth $48.5M/yr, more than every other recheck candidate combined. It should
lead the next reconcile-queue cycle.

The rest of the list splits cleanly: `Indian Pueblo Cultural Center` and
`Klamath Family Head Start` read as genuine Native institutions; the community
college foundations (Pueblo CO, Maricopa, Pima, Cayuga, Mohawk Valley, Chippewa
Valley) read as the place-name trap the exclusion was built to catch. 31 of 67
are `under_50k` or `none` and are not financially consequential either way.

## 6. Schema

### `np_financials.csv` — 8,507 rows, one per EIN-filing-period

Requested columns, all present: `ein, org_name, tax_year, form_type,
total_revenue, total_expenses, total_assets, total_liabilities,
program_service_revenue, contributions_grants, lobbying_expenditure,
n_employees, pdf_url, source_url, retrieved_date`.

Added for provenance and joining: `tax_period, form_type_raw,
has_financial_data, pre_2000_flag, lobbying_indicator_990pf,
propaganda_indicator_990pf, lobbying_field_basis, n_employees_basis,
net_assets_end, officer_compensation, state, confidence_tier, bmf_990_tier,
in_tier_a, in_recheck_candidate, in_placename_risk, source_dataset,
filing_updated`.

**Field mapping differs by form and no value is ever synthesised across forms:**

| Output column | 990 | 990-EZ | 990-PF |
|---|---|---|---|
| `total_revenue` | `totrevenue` | `totrevenue` / `totrevnue` | `totrevenue` / `totrcptperbks` |
| `total_expenses` | `totfuncexpns` | `totfuncexpns` / `totexpns` | `totfuncexpns` / `totexpnspbks` |
| `total_assets` | `totassetsend` | `totassetsend` | `totassetsend` |
| `total_liabilities` | `totliabend` | `totliabend` | `totliabend` |
| `program_service_revenue` | `totprgmrevnue` | `prgmservrev` | *(no such line on 990-PF; blank)* |
| `contributions_grants` | `totcntrbgfts` | `totcntrbs` | `grscontrgifts` |

`has_financial_data = 0` rows come from the response's `filings_without_data`
array: ProPublica holds the PDF but not a parsed extract. They carry a
`pdf_url` and nothing else, and every financial column is blank. They are kept
because they are evidence the filing exists.

### `np_org_scale.csv` — 1,157 rows, one per pulled EIN

`ein, org_name, state, confidence_tier, bmf_990_tier, in_tier_a,
in_recheck_candidate, in_placename_risk, api_status, n_filings_returned,
n_filings_with_financials, first_filing_year, latest_filing_year, latest_year,
latest_form_type, total_revenue, total_expenses, total_assets,
total_liabilities, program_service_revenue, contributions_grants, scale_band,
scale_band_basis, bmf_revenue_amt, ntee_code, review_flag, propublica_url,
source_dataset, source_url, retrieved_date`.

`bmf_revenue_amt` is carried alongside for comparison and is a *different
vintage and often a different year* than `total_revenue` — Umatilla Electric
reads $592,498,408 in the 2026-04-29 BMF and $603,100,445 in its FY2023 filing.
They are not interchangeable; use `total_revenue` with `latest_year` attached.

## 7. Caveats that travel with any table built on these files

1. **Tribal instrumentalities largely do not file 990s (IRC §7871).** The
   largest tribal institutions can be entirely absent. A tribe with no row here
   is evidence about IRS filing obligations, never about its nonprofit sector.
2. **990-N postcard filers yield existence only** — and ProPublica returns no
   990-N records at all, so 438 of 598 BMF-`990_N` orgs came back empty.
3. **`scale_band = none` means unobserved, not zero.** 584 of 1,157.
4. **Blank is not zero anywhere in these files** — most consequentially
   `lobbying_expenditure` and `n_employees`, which are blank on 100% of rows
   because the API does not expose them (§3).
5. **Filing lag is real and visible.** 2023 is the modal latest year on a
   2026-08-05 pull.
6. **Tier A is an unruled screened candidate set.** Its revenue aggregate is
   69.3% place-name-risk organizations. Do not quote it, before or after
   subtracting them.
7. **The place-name risk flag is symmetric** and sweeps in real tribal
   institutions (College of the Menominee Nation, United Houma Nation). Revenue
   ranks the stakes; it does not decide the ruling.
8. **`in_tier_a` / `in_recheck_candidate` / `in_placename_risk` are membership
   flags, not classifications.** No `classification_ruling` was minted in this
   build. The organizations here are still `UNRULED`.

## 8. Failures and things not done

- **API failures: none.** 1,157/1,157 HTTP 200. No retries were consumed, no
  rate limiting was observed at 1.05 s spacing, no EIN produced a 404.
- **Lobbying dollar amounts: not obtainable from this source** (§3). Deferred to
  the phase-2 990 XML pass, which now has an explicit named target
  (`IRS990ScheduleC`) and a confirmed-dead shortcut (per-object S3 → 404).
- **Employee counts: not obtainable from this source.** Same deferral.
- **The remaining 11,607 `np_orgs` rows were not pulled** — out of scope by
  instruction. At 1.05 s/request that is roughly 3.4 hours if it is ever wanted;
  the script needs no change, only the target set widened.
- **Schedules I / R / J / O** — not in this API; phase-2 XML.
- **No classification rulings minted, no spine linking, no `entity_id`
  populated.** Unchanged from the prior build.

## 9. Next steps, ranked

1. **Rule the top 15 place-name-risk organizations.** That settles ~90% of the
   contaminated revenue. Start with Umatilla Electric, Yavapai Community
   Hospital and Lumbee River Electric (exclude), and College of the Menominee
   Nation, Akwesasne Boys & Girls Club and United Houma Nation (likely promote).
2. **Settle Navajo Technical College** (EIN 850303705). $48.5M and an open
   conflict between the exclusion ruling and the identifier ledger.
3. **Do not re-attempt the lobbying cross-check via the API.** Fold it into the
   phase-2 IRS 990 XML pull, targeting Schedule C.
4. Once rulings exist, re-run `--steps build,report`; the cache is on disk so
   only ruled-set membership changes and no refetch is needed.
