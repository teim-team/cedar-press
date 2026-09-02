# Methodology — Native Nonprofits

<!-- BEGIN GENERATED:IDENTITY -->

**`nonprofits` — Native Nonprofits.** Delivered as `dist/customer/nonprofits.csv`: **12,764 rows × 70 columns, 13.9 MB**, built from the flagship table `data/clean/np_orgs.csv`. Shelf `pro`; sold through **Cedar Press**; on the Cedar Press storefront. Readiness **READY**. [measured 2026-09-02 from the delivered file]

> **This block and Appendix M at the foot of this paper are GENERATED** by `code/1143_methodology_papers.py` from the delivered file itself, on every build — the same reason the codebooks are generated. Do not hand-edit either; the next build overwrites them.
>
> Everything between `<!-- BEGIN EDITORIAL:nonprofits -->` and `<!-- END EDITORIAL:nonprofits -->` is **hand-written and preserved byte-for-byte** across rebuilds. Put prose there and nowhere else.
>
> This paper is **not** the codebook. `dist/customer/nonprofits__CODEBOOK.md` carries the grain, the folded-in tables and the per-column fill rates, and `__NOTES.txt` carries the same for a person. This paper says how the dataset came to exist and why you should believe it.
>
> Generated 2026-09-02. `py -3 code/1143_methodology_papers.py verify` **fails** if the delivered file has moved since — see §M7.

<!-- END GENERATED:IDENTITY -->

<!-- BEGIN EDITORIAL:nonprofits -->
**`nonprofits`. Twelve tables; the headline ones are `np_orgs.csv` (12,764
rows), `np_schedule_i_grants.csv` (58,685), `grantmaker_funding_flows.csv`
(18,656) and `fac_tribal_single_audits.csv` (6,780).** [measured 2026-09-02]

*Written 2026-09-02. This is the methodology record: what was pulled and from
where, how the rows were made, how entities were attributed, what was decided
and why, what the known limits are, and how often it has to be re-pulled. It is
not the product copy (`docs/datasets/_descriptors.json`) and not the codebook
(`docs/codebooks/`).*

**A note on the figures.** `[measured]` means the figure was re-counted from
the live file with `csv.reader` on 2026-09-02, streaming the whole file.
`[from the record]` means it came from a build log, docstring or ADR without
independent measurement. Where a doc and the data disagreed, the measurement
won; the disagreements are listed at the end.

**Readiness: READY.** [measured — `docs/DATASET_READINESS.md`, regenerated
2026-09-02: 10 tables, 10/10 grain, 10/10 keys, duplicates clean, 0
aggregation-unsafe, rebuild declared]

---

## The one thing to understand before any number in this dataset

**Tribal instrumentalities largely do not file Form 990, and that is a matter
of law, not of coverage.** The largest institutions in Indian Country can be
absent from this dataset entirely, and no amount of collection effort will
change it.

The statutory chain, in four steps:

1. **26 U.S.C. §7871(a)** (Pub. L. 97-473 §202(a), 1983-01-14) opens *"An
   Indian tribal government shall be treated as a State—"* followed by a
   **closed enumeration of seven purposes**. §501(a), §501(c)(3) and §6033 are
   **not on that list**.
2. **Rev. Rul. 67-284, 1967-2 C.B. 55**: *"Income tax statutes do not tax
   Indian tribes. The tribe is not a taxable entity."*
3. The Form 990 filing duty is textually keyed to §501(a) —
   **26 CFR 1.6033-2(a)(1)**: *"every organization exempt from taxation under
   section 501(a) shall file an annual information return…"*
4. **Therefore a tribe is not an exception to the 990 regime — it is outside
   it.**

> ⚠ The sentence *"tribal governments are exempt from filing Form 990"* is
> **legally wrong**, and no IRS document says it. The correct and stronger
> sentence is: *the Form 990 filing duty attaches only to organisations exempt
> under §501(a); a tribal government is not one.*

**A three-way distinction the whole coverage statement rests on:**

| | in the EO BMF? | files a 990? |
|---|---|---|
| (a) the tribe itself | no | no |
| (b) its political subdivisions | no | no |
| **(c) tribally chartered 501(c)(3) nonprofits** | **yes** (`SUBSECTION = 03`) | **yes** |

Tribal housing authorities, colleges, health boards and charitable foundations
commonly fall in (c). **A 990/BMF measure of "nonprofit activity in Indian
Country" captures only category (c).** Cross-tribal or reservation-vs-non-
reservation comparisons built on 990 counts or revenue are therefore measuring
**organisational form choice, not underlying activity**. Compounding it, BMF
`STATE` is a mailing address, not a place of operation.

**What that looks like in the data.** Of Schedule I grant rows,
`recipient_bmf_status` splits:

| status | rows | distinct EINs | $ (cash + noncash) |
|---|---:|---:|---:|
| `in_full_irs_bmf` | 39,178 | 12,491 | $11.636B |
| **`absent_from_full_irs_bmf`** | **16,344** | **6,217** | **$4.958B** |
| `no_ein_reported_on_schedule` | 3,163 | — | $0.724B |

[measured] Corroboration from what filers write in `irc_section_as_filed`:
`TRIBE` 1,069 rows, `GOVERNMENT` 1,158, `115` 945, `GOV'T` 905, `GOV` 763.
`recipient_outside_990_universe_signal = 1` on 16,619 rows. [measured]

**Two guardrails on that measurement, and they matter:**

- **The 6,217 is an UPPER BOUND on the §7871 population.** Automatic revocation
  is a second, independent reason an EIN can be absent from the BMF — roughly
  275,000 organisations left the exempt population in a single act on
  **2011-06-08**. That separation has not been done. Say **"absent from the
  BMF"** (measured), never **"tribal governments"** (inferred).
- **The first cut of this test was wrong.** It tested recipient EINs against
  the 12,764-row Native-connected slice rather than the full BMF, and labelled
  **17,848 ordinary charities** with the §7871 signature. Any re-derivation
  must use the full BMF.

---

## 1. Sources

**IRS Exempt Organization Business Master File** —
`irs.gov/pub/irs-soi/eo{1,2,3,4}.csv`. Two vintages live side by side: the
12,764-row candidate slice derived **2026-04-29** (`bmf_vintage_fetched` is
that date on all 12,764 `np_orgs` rows [measured]) and the **full BMF,
1,957,340 organisations, 325 MB, fetched 2026-08-12** [from the record], used
for the absence test above.

**IRS Form 990 e-file XML bulk archives** — not ProPublica — for Schedule I and
Schedule C. Every grant row carries `source_url` =
`https://apps.irs.gov/pub/epostcard/990/xml/{YYYY}/download990xml_{YYYY}_{N}.zip`,
`zip_member` = the return XML filename, and `irs_downloads_page` =
`https://www.irs.gov/charities-non-profits/form-990-series-downloads`.
[measured]

**ProPublica Nonprofit Explorer API v2** — used **only** for `np_financials.csv`
and `np_org_scale.csv`. `source_dataset = 'ProPublica Nonprofit Explorer API
v2'` on all 8,507 financial rows [measured]; 1,157 of 1,157 requests returned
200.

**Federal Audit Clearinghouse dissemination API** (`api.fac.gov`) for
`fac_tribal_single_audits.csv`. `source_authority = 'Federal Audit Clearinghouse
(GSA), dissemination API'` on all 6,780 rows. [measured]

**Grantmaker 990-PF and 990 returns** for the funder-side layer — 14
foundations, see §5.

### What was deliberately not used, and why

- **The bulk 990 XML year archives were never downloaded whole.** A single year
  exceeds free disk (6.87 GB free at the time). Retrieval was by **HTTP range
  read into the published ZIPs — 1,449 MB instead of ~30 GB.** The exception:
  four archives written with **DEFLATE64** (compression method 9), which
  CPython's `zipfile` cannot decode. Those were downloaded one at a time
  (0.37–0.50 GB each), extracted with system 7-Zip, and deleted before the next.
- **44 Form 990-T returns were deliberately not read** in the grantmaker build.
  990-T is the unrelated-business-income return and carries no grants schedule.
  Recorded per funder in the coverage file rather than left as absence.
- **NTEE codes were never used to establish Native status.** They were one of
  five mechanical screening votes upstream. **The NTEE taxonomy has no Native
  category**, so it cannot carry the claim.
- **The identifier ledger's EIN leg was refused wholesale as a link source.**
  All 1,104 rows: measured **6.5% accurate, zero tier-A rows**, and every hand
  ruling on that leg is a negative. Only its 56 tier-X rows entered, as
  exclusions. What it proposed: `ONONDAGA GOLF AND COUNTRY CLUB` → Onondaga
  Nation, `TUSCARORA GOLF CLUB INC` → Tuscarora Nation, `LENAPE VALLEY SOCCER
  CLUB` → Lenape Indian Tribe of Delaware.
- **Two organisations refused as IRS-index name traps** in the grantmaker
  build: `JM FOUNDATION` EIN 38-4322070 (Lafayette CA — not the conservative JM
  Foundation, 13-6068340) and `DONORS TRUST` EIN 26-2515785 (Nebraska — not
  DonorsTrust Inc of Alexandria VA, 52-2166327). Both are recorded in
  `review/grantmaker_name_trap_exclusions_2026-08-12.csv`.
- ~~**Sources whose terms forbid reuse are excluded by every route** — Colville,
  CTUIR/Umatilla, Yakama, Chickasaw, NANA/Akima, Southern Ute, Forest County
  Potawatomi.~~ **RELEASED 2026-09-02.** **SUPERSEDED 2026-09-02 by owner ruling** (`docs/PUBLICATION_POLICY.md`, `TERMS-OWNER-RULING-2026-09-02`): a tribal website's terms language no longer blocks harvest, and all eight are released for harvest of **their own public pages**. The exclusions below are kept as the *observation* of what each publisher stated - and as the worklist the ruling creates. Still binding, none of them a terms question: technical access controls; a natural person's data apart from their public role (the business row may be harvested, `owner_name_raw` / `email` / `phone` / `address_raw` may not be published); EMMA/MSRB + CUSIP Global Services, a third-party licensor; Casino City and D-U-N-S. The second half of
  the struck sentence is still true and is why the ruling was the owner's to
  make: harmonising changes what Cedar publishes, not what Cedar was allowed to
  take — so the permission question had to be answered, not designed around.

---

## 2. How the rows were made

> ⚠ **Script numbers are not unique in this project.** `ls code/33_*` returns
> both `33_apply_party_rulings.py` and `33_nonprofit_financials.py`; `70_*`,
> `41_*`, `76_*`, `77_*` and `156_*` also collide. Cite the filename.

1. **`code/17_build_nonprofit_990.py`** — streams the BMF in 200k-row chunks
   (`dtype=str`, never loaded whole: 1,952,238 rows at the 2026-04-29 vintage),
   applies the tribal-token funnel, and writes `np_orgs.csv` (12,764),
   `np_ein_uei_bridge.csv` (28) and
   `data/spine/nonprofit_exclusion_rulings.csv` (4,656).
2. **`code/33_nonprofit_financials.py`** — pulls ProPublica v2 for a union of
   **1,157 EINs** (1,090 tier A + 67 recheck candidates + 412 place-name risk;
   the overlap is why it is 1,157 and not 1,569). Writes `np_financials.csv`
   (8,507) and `np_org_scale.csv` (1,157). **The remaining 11,607 `np_orgs`
   rows were deliberately not pulled.**
3. **`code/38_*`** — the classification research pass →
   `review/rulings_inbox_2026-08-05_agent_nonprofit.csv`, 375 EINs ruled
   (`docs/NONPROFIT_CLASSIFICATION_RESEARCH_LOG.md`).
4. **`code/99_build_earmarks_and_schedc.py`** — built the `HttpRangeFile` /
   `zip_manifest` / `parse_schedule_c` machinery and the Schedule C XML cache.
5. **`code/75_philanthropy_schedule_i.py` → `76_philanthropy_classify.py` →
   `77_philanthropy_review_queue.py`** — Schedule I of seven Native
   grantmakers: 1,053 rows, $99,756,433, **601 distinct grantee EINs, of which
   491 — four in five — are absent from `np_orgs.csv` entirely.** Names like
   *Nkwusm*, *Ukwakhwa*, *Hui o Kuapā*, *Manidoo Ogitigaan*. **A name scan
   cannot find them**, which is the argument for the EIN route.
6. **`code/112_pull_grantee_990s.py`** — points 99's machinery at that grantee
   EIN list. **927 EINs worked** (601 named + 326 already in the local cache).
   Retrieval **97.0% against 34.3%** for script 99 — recorded in the log as
   *"not an improvement in method; an improvement in coverage of the queue."*
   Writes `np_grantee_financials.csv` (4,058).
7. **`code/132_build_schedule_i_layer.py`** (`--steps
   bmf,parse,build,drift,review,codebook,report`) — parses Schedule I out of
   XMLs **already on disk. Zero network requests for return XML.** Writes
   `np_schedule_i_grants.csv` and `np_schedule_i_filers.csv`. `--steps drift`
   reproduces `111.parse_local_schedule_i()` row for row.
8. **`code/140_build_grantmaker_funding_flows.py`** (`--steps
   eins,index,probe,xml,deflate64,parse,overlap,coverage,codebook,report`) —
   writes all three grantmaker tables.
9. **`code/147_build_fac_single_audits.py`** — writes
   `fac_tribal_single_audits.csv`.
10. **`code/167_link_nonprofit_family_via_ein_hub.py`** — builds
    `np_ein_entity_hub.csv` and propagates it. *(Written as `163_`, renumbered
    mid-session because three other agents claimed 163 concurrently.)*
11. **`code/781_upstream_grain_columns.py`** — adds `schedule_i_line_seq` in
    place, 2026-09-01.
12. **`code/505`** — writes `cedar_uid`.
13. **`code/731_ws5_grain_contractors_nonprofits_deals.py`** — the grain and
    source declaration pass (`docs/WS5_GRAIN_AND_SOURCES.md`).

### What one row is

| table | rows | one row = |
|---|---:|---|
| `np_orgs.csv` | 12,764 | one EIN **considered for** the Native nonprofit universe |
| `np_schedule_i_filers.csv` | 10,314 | one parsed 990 return (10,314 distinct `object_id`; 4,730 distinct `filer_ein`) |
| `np_schedule_i_grants.csv` | 58,685 | one Schedule I Part II recipient **line** |
| `np_financials.csv` | 8,507 | one (EIN, filing period); 662 unique EINs |
| `np_grantee_financials.csv` | 4,058 | one (EIN, year); 927 unique EINs |
| `np_org_scale.csv` | 1,157 | one pulled EIN, latest year |
| `np_ein_entity_hub.csv` | 2,303 | one EIN linked to a Cedar entity |
| `np_ein_uei_bridge.csv` | 28 | one EIN↔UEI pair |
| `grantmaker_funding_flows.csv` | 18,656 | one named grant recipient on a grantmaker's own return |
| `grantmaker_funding_coverage.csv` | 27 | 14 funder rows + 13 `RECIPIENT:` rows |
| `grantmaker_funding_overlap.csv` | 69 | one (funder, resolved target) cell |
| `fac_tribal_single_audits.csv` | 6,780 | one Single Audit report for a tribal auditee |

[measured]

---

## 3. How entities were attributed

**The EIN is the hub, and nobody had joined on it until 2026-08-26.**
`np_ein_entity_hub.csv` holds **2,303 EINs, tier A 504 / tier B 1,799**
[measured]. By class: tribe 1,760 · Native organisation 381 · ANC 88 · NHO 74.

What it did to link rates:

| table | before | after |
|---|---:|---:|
| `np_orgs` (`cedar_spine_entity_id`) | 54 | **1,456** |
| `np_orgs` (`entity_id`, the publishable key) | 54 | **84** |
| `np_schedule_i_filers` | 1,652 | **2,051** |
| `np_schedule_i_grants` recipient | 552 | **3,505** |
| `np_schedule_i_grants` filer | 0 | **2,872** |
| `np_financials` | 0 | **2,815** |
| `grantmaker_funding_flows` funder / recipient | 0 | **0** |

[measured]

Hub sources: `np_orgs` 1,398 · `fac_single_audits` 798 · `nho_register` 57 ·
`advocacy_passthrough` 32 · `bie_uio_identifier_links` 11 ·
`intertribal_register` 4 · `ein_uei_bridge_to_ledger` 3. [measured]

**208 EINs are corroborated by two or more independent Cedar tables, and that
does NOT raise the tier.** Two-leg promotion is a *ledger* method
(`agent_research_two_leg`); it is not a consumer's to mint.

**The strongest Native-status evidence in the whole family is
`fac_tribal_single_audits`**: the auditee told the federal government it is an
Indian tribe or tribal organisation, and the EIN on the filing is its own. It
reached 27 `np_orgs` rows no name pass had found — Little Priest Tribal
College, Oglala Lakota College, Marty Indian School Board, Nebraska Urban
Indian Health Coalition, the Lakota Fund, Native American Lifelines.

**Inside Schedule I, tier is defined by how many independent legs agree:**
recipient Native-evidence tier **A 342** (an EIN join *and* a guarded name
match agree), **B 4,127** (one leg alone), none 54,216. [measured] **A name
match is never tier A.** `resolve_entity` is imported from
`33_apply_party_rulings.py` and the eight containment guards from
`111_build_advocacy_passthrough.py`; **no second matcher was written**, on
purpose — two matchers for one job drift, and a drifted matcher is worse than
none because it is trusted.

Result: Schedule I cash grants naming a linked Native recipient rose
**$144.2M → $411.5M.**

### The matching rules that produced those tiers

**An entity whose entire distinctive token set is generic may not win a match
that rests only on the name.** This dataset is where the rule was earned: 53
containment links in `np_ein_entity_hub.csv`, **41 of them onto *Council Native
Corporation*** and five onto *Council*, a real Alaska Native village.

**A denylist is not the fix.** `cedar_domain.NAME_TRAPS` held 51 words and did
not hold `council`, `health` or `native`. A denylist refuses only a word
somebody already listed.

**State agreement is not the fix either.** Tested on this exact case: it kills
all five `Council` links (Philadelphia, Brooklyn — none in Alaska) and **none**
of the `Native Health` links, because Winslow AZ, Fort Defiance AZ and Native
Health are all in Arizona.

**Flagging is not a claim that the organisation is not Native.** Among the 53
refused: Cook Inlet Tribal Council, International Indian Treaty Council,
National Indian Council on Aging, Indian Action Council of Northwestern
California, Inter-Tribal Council of Louisiana. Every one is genuinely Native.
The refusal says only **this is not THAT entity**, and the repair **flags and
never deletes**.

**`INDIAN` is no signal at all.** The same sweep caught `COUNCIL OF INDIAN
ORTHODOX CHURCHES INC` (the Malankara Orthodox Church), `NATIONAL COUNCIL OF
ASIAN INDIAN ASSOCIATIONS`, `COUNCIL FOR WEST INDIAN PLANNING & DEVELOPMENT`,
`CULTURAL COUNCIL OF INDIAN RIVER COUNTY` and `INDIAN ORCHARD CITIZENS
COUNCIL`.

---

## 4. The duplicate allegation that dissolved

`np_schedule_i_grants.csv` was flagged with **101 literal duplicate rows in 90
groups**. Measured:

```
rows                                                          58,685
whole-row duplicates, all 65 columns                               0   [measured]
the same test EXCLUDING `schedule_i_line_seq`                    101   in 90 groups, 191 rows
distinct object_id carrying a collision                           11
of those 11, how many appear >1x in np_schedule_i_filers.csv       0
cash a de-dupe would have deleted                         $2,089,185
```

**The measurement that dissolved it:** every colliding group sits inside **one
return that `np_schedule_i_filers.csv` holds exactly once**. The return was
parsed once; the **filer listed the line twice**. Form 990 Schedule I Part II
is a repeating `RecipientTable`, and listing one recipient twice is what it is
for. The worked case: **First Nations Development Institute lists two $20,000
Economic Development grants to the Seneca Nation of Indians on its FY2017
return, and both are real.**

**The fix was a LINE ORDINAL, not a DELETE.** `schedule_i_line_seq`, 1..n
within `object_id` in document order, making `(object_id,
schedule_i_line_seq)` a validated primary key. Added **in place** by
`code/781_upstream_grain_columns.py`, which refuses to write if a column would
go missing or if any colliding group turned out to span a return the filers
table holds more than once. `132` was fixed in the same pass so a rebuild
reproduces the column.

Result: rows 58,685 → 58,685 · whole-row duplicates 101 → 0 · **$0 deleted** ·
`517` export class **ROW_LEVEL_ONLY → SAFE_TO_AGGREGATE**.

**This is the fifth duplicate allegation in the project and the fourth to
dissolve.** The others: `prime_contracts` 80,778 → 0,
`prime_contracts_archive_backfill` 60,919 → 0, and `faads_*` 180,260 → 3,441 —
where a de-dupe would have destroyed **$8,291,124,113** of real obligations.
Only the identity hub's 11,981 were real, and those were distinct events
rendered identical by a lossy projection.

**One nuance worth preserving, because it is different from the others.** The
Schedule I case is *not* "a lossy projection rendered distinct events
identical." The 90 groups are genuinely identical **on every recorded field** —
the two First Nations grants really do carry the same filer, recipient, EIN,
purpose text and amount. What separated them was not a lost field but the
**position of the line on the form**. `schedule_i_line_seq` is therefore a
*manufactured* discriminator, and the record says so: on the five returns where
a recipient line names nobody and is held out to `review/`, the sequence is
"a dense position among what ships rather than the printed form line."

**The rule earned across all five: a duplicate is proved against the source,
never inferred from the output.** An identical-looking row is evidence that the
projection is lossy.

---

## 5. Decisions that shaped the data

### `np_orgs.csv` is a candidate funnel, not an adjudication

The first Schedule I cut flat-flagged every filer present in `np_orgs` as
"Native-connected" and reported **$1.01B of Native grantmaking**. The top
grantmaker came back as **SEMINOLE BOOSTERS INC, EIN 59-1561180, $58,307,004**
— Florida State University's athletics booster club, already
`confidence_tier = X`, `funnel_stage = excluded_by_prior_ruling`. Behind it:
South Dakota State University Foundation, Cayuga Medical Center, Sioux Falls
Area Community Foundation, North Dakota Community Foundation.

A flat flag **resurfaced 217 tier-X rows**, and *an X-tier row is a negative
ruling and must never resurface.* The fix was to tier `filer_population` and
name the exclusions in band:

| `filer_population` | filers | rows |
|---|---:|---:|
| `not_in_np_orgs_universe_native_status_not_established` | 137 | 50,909 |
| `np_orgs_EXCLUDED_by_prior_ruling` | 217 | 4,341 |
| `np_orgs_candidate_tier_B_unruled` | 248 | 3,212 |
| `np_orgs_candidate_tier_A_unruled` | 22 | 163 |
| `np_orgs_ruled_tribally_controlled` | 2 | 52 |
| `np_orgs_ruled_native_serving` | 1 | 8 |

[measured] **Not one line of that table is a publishable "Native grantmaking"
total.** The 137 outside filers are grantees of Native funders, led by Johns
Hopkins ($3.9B), Mayo Clinic ($3.8B) and New Venture Fund ($2.4B) — but the
same bucket holds **Southcentral Foundation ($117M)**, which plainly is Native.
`UNESTABLISHED` runs in both directions.

### `classification_ruling` was left UNRULED on purpose

The BMF carries no control-status field, and minting `tribally_controlled` from
a name match is fabrication. **12,366 of 12,764 rows (96.9%) are still
`UNRULED`**; 398 are ruled — `place_name_coincidence` 309, `native_controlled`
71, `tribally_controlled` 11, `native_serving` 7. [measured]

**The disposition of a row lives in `funnel_stage`, not in
`classification_ruling`**, and that is the single worst column choice in the
thirteen datasets: 4,651 rows are `excluded_by_prior_ruling` and *still read
`UNRULED`*, and 697 are `verified_strict` and still read `UNRULED`. A reader
who takes the ruling column at face value concludes nothing has been decided.

### Two rules that kept large false positives out

- **Native control was never inferred from a tribe-named place.**
- **Native control was never inferred from a reservation service area alone** —
  that is `native_serving` at most.

Those two kept Jemez Mountains Electric ($56.4M) and Lumbee River EMC
($158.2M) out. The decisive evidence on LREMC was the **Lumbee Tribe's own
press release treating it as an outside partner and donor** — a tribal
instrumentality does not donate to its own tribe. The surname pattern on its
board (Locklear, Oxendine, Chavis) was **explicitly not treated as evidence**
and the row was flagged for a human.

### Intercoder reliability is a screening device, not a validation

Five mechanical coders vote; three or more agreeing is "high confidence".
**Pairwise Cohen's κ is below 0.05 for every pair except B–E (0.143).** The
"≥3 of 5" line is a *coverage* threshold, not a reliability-validated ruling,
and the log says so.

### The BMF-presence check is circular

All 12,764 EINs appear in the BMF slice because the universe was derived from
that snapshot. It is not a revocation check and must not be read as one.

### Tier A is a screened candidate set, not a Native organisation list

Its three largest organisations by BMF revenue are Umatilla Electric
Cooperative ($592.5M), Yavapai Community Hospital ($497.2M) and Lumbee River
EMC ($169.6M). **The "$2.51B tier-A BMF revenue" aggregate is not publishable
and the build log says so in as many words.**

### XML beats the ProPublica scrape, and it was measured rather than assumed

Seven returns overlap between script `75`'s ProPublica HTML scrape and `132`'s
XML parse. Two agree to the cent; **five disagree, always in the same
direction** — the scrape drops rows and zeroes amounts. Across the seven:
ProPublica **$51,493,576** against XML **$54,482,314**, understating by
**$2,988,738 (5.5%)**, with 18 grant amounts rendered as $0 and 28 rows
missing. One recipient (The Nature Conservancy, $962,500 from Seventh
Generation Fund) vanished entirely.

**But ProPublica reached seven `object_id`s the local XML cache does not
hold.** The two are complementary, not redundant, and both are kept.

### The grantmaker layer: selection is a hypothesis test, not a sample

`grantmaker_funding_flows.csv` holds exactly **14 funders** [measured]:
Bradley, Coors, Donors Capital, DonorsTrust, JM, Kirby, Charles Koch
Foundation, Charles Koch Foundation II, Charles Koch Institute, Scaife, Searle,
Diana Davis Spencer, Templeton, Ed Uihlein.

**Why those fourteen.** The layer descends from
`code/139_build_litigation_positions.py`, which tested whether the Hoover
Institution and George Mason took *institutional* positions against ICWA.
**They did not** — both appear in `native_issue_litigation_positions.csv` only
as `B_AFFILIATED_INDIVIDUAL` (a scholar signed an amicus), never
`C_INSTITUTIONAL_ACTION`. That hypothesis failed and stays failed. The refined
claim — that the foundations funding the anti-ICWA litigators also fund Hoover
and Mercatus — is what these fourteen were chosen to test. Twelve are the
conservative-movement grantmakers named in that brief; two are identity
discoveries (Charles Koch Institute = EIN 27-4967732, which the current BMF
carries as *Stand Together Fellowship*; Charles Koch Foundation II = EIN
85-4058882, filing as *Charles Koch Charitable Fund*).

**Why the existing Schedule I layer could not answer it:**
`np_schedule_i_grants` holds only the filers scripts 99 and 112 had cached. *A
conservative foundation is absent from that file by construction. Absence there
is absence in a sample, not in the world.*

**This population is deliberately NOT Native.** It is a funder-side layer, and
`carries_institutional_position = 0` and `evidence_class = FUNDER_ACTIVITY` on
**all 18,656 rows** [measured]. Every row carries, verbatim: *"A shared funder
is not a shared position."*

**The unit-identification split, and it is the whole methodological point.** A
search of the full 1,957,340-organisation BMF for "HOOVER INSTITUTION" returns
**zero rows** — Hoover is a unit of Stanford, not a legal person. So
`recipient_unit_identified` has two tiers that are **never summed**:
`UNIT_IDENTIFIED` (the filed return names Hoover or Mercatus) against
`INSTITUTION_LEVEL` (the recipient is Stanford or the GMU Foundation, no unit
named). Measured: `STANFORD_UNIT_NOT_IDENTIFIED` 89 ·
`GMU_UNIT_NOT_IDENTIFIED` 95 · `HOOVER_NAMED_IN_TEXT` 40 ·
`GMU_LAW_NAMED_IN_TEXT` 31 · `NOT_APPLICABLE_SINGLE_LEGAL_PERSON` 361.
**Read as Mercatus money, the Charles Koch Foundation's $123.9M
institution-level column would be off by more than two orders of magnitude
against the $0 the returns actually support for Mercatus.**

Results, reported including the negatives: **8 of the 14 gave both to a
documented anti-ICWA institutional actor and to a grant naming Hoover or
Mercatus** — two of the eight are donor-advised funds and are separated out.
**F M Kirby matched no target on either side across 1,261 grant rows.** The
Charles Koch Institute matched no Hoover, Mercatus or GMU recipient at all
across 477 rows, while giving $11.7M to the anti-ICWA side.

New `cedar_domain.NAME_TRAPS` entries were added with the count of BMF
organisations containing each word: `mason 697 · bradley 262 · spencer 261 ·
hoover 127 · stanford 105 · kirby 74 · koch 52 · templeton 51 · cato 17 ·
coors 7 · scaife 6 · goldwater 5`. **`mercatus` returns 1 and was NOT added** —
it is genuinely distinctive.

### The FAC "dead end" was a generalisation from one auditee

Cedar's standing documents recorded tribal Single Audits as a documented dead
end, on the strength of the Florida build: *"Seminole Tribe of Florida (EIN
59-1415030) … all ten filings FY2016–FY2025 are `is_public: false` under 2 CFR
200.512(b)(2)."* Every word of that is true **about the Seminole Tribe of
Florida**. Generalised to Indian Country it is false.

**2 CFR 200.512(b)(2) is an auditee OPT-OUT, not a bar** — an auditee that is
an Indian tribe or tribal organisation *may elect* not to authorise the FAC to
make the reporting package publicly available. Measured:

```
fac_tribal_single_audits.csv                6,780 rows      [measured]
  is_public = 1                             2,052  (30.3%)
  is_public = 0                             4,728  (69.7%)
  audit years                               2016-2026
  distinct auditee_ein 1,075 - distinct entity_id 638
  entity_id populated on 5,530 (81.6%); tier A 2,794 / B 2,737 / blank 1,249
  total_amount_expended                     $122,607,861,415
  entity_has_gaming_facility = 1            3,311
```

`availability_basis` carries the statute verbatim on all 4,728 withheld rows.
**The wrong generalisation cost the project its highest-value gaming financial
source for five days.**

**The withholding is per-endpoint, and that was measured on two matched samples
of the 25 largest tribal filings:**

| API table | public auditee | non-public auditee |
|---|---:|---:|
| `notes_to_sefa` | 25/25 | **0/25** |
| `findings_text` | 11/25 | **0/25** |
| `corrective_action_plans` | 11/25 | **0/25** |
| **`federal_awards` (SEFA)** | **25/25** | **25/25** |
| reporting-package PDF | HTTP 200 | **HTTP 403** |

**The SEFA survives the withholding; the reporting package does not.** Seminole
FY2022 returns 127 `federal_awards` rows, program by program with dollars,
while its PDF 403s. That is a usable line into 4,728 otherwise-closed filings.
**No API table carries the financial statements at all** — component-unit
statements, transfers to the tribe and machine participation expense exist only
in the PDF, which is why the PDF layer had to be built.

**The generalisable lesson: a source's refusal on one record is a fact about
that record.** The same error shape as "broken search ≠ absence" — a property
of one record read as a property of the whole system. A dead end recorded from
one entity's behaviour needs a second entity before it is written down.

---

## 6. What a buyer may total

- **`np_schedule_i_grants.cash_grant_usd` totals $16,439,532,633** and
  reconciles to `np_schedule_i_filers.part2_cash_grant_total_usd` at
  **$16,439,532,633** — the same money at two grains, to the dollar, with **all
  10,314 returns reconciling individually**. [measured both sides] Never add
  them.
- **Noncash is a different dollar: $878,481,598.** Never add cash and noncash
  and then add the result to anything.
- **Never add Schedule I to `federal_funding_transactions.csv`, `faads_*` or
  `native_passthrough.csv`.** A Schedule I grant is money the FILER granted
  out; where the filer received a federal award and re-granted it, that dollar
  is in the funding dataset *and* here. Cedar's shape for that is
  `native_passthrough.csv`'s directed edge plus its `amount_countable` flag,
  and **Schedule I carries no such flag**.
- **Total it as GRANTS MADE BY NONPROFITS.** Never as "money reaching Indian
  Country."
- **Grantmaker flows total $4,358,173,488 cash** [measured] and are a
  *funder-side, non-Native* population. They are not Native grantmaking and are
  not additive with anything else here.
- **`fac_tribal_single_audits.total_amount_expended` is federal awards
  EXPENDED**, the Single Audit threshold measure. It is neither revenue nor
  gaming revenue, and it may not be summed with any money column in any other
  Cedar dataset.

---

## 7. Known limits

- **Coverage on Schedule I is a FLOOR, not the universe.** It reads only what
  scripts 99 and 112 had already retrieved for Schedule C purposes.
- **Tax years 2015–2025**, rows: 2015:5 · 2016:4,214 · 2017:4,825 · 2018:5,284
  · **2019:4,257** · 2020:6,098 · 2021:6,528 · 2022:6,375 · 2023:6,706 ·
  2024:9,779 · 2025:4,614. `tax_period_end` spans 2015-06-30 → 2025-12-31.
  `return_type = '990'` on **all 58,685 rows** — no 990-EZ, no 990-PF here.
  [measured]
- **E-file coverage is PARTIAL before tax year 2019.** Mandatory e-filing
  arrived with the Taxpayer First Act; paper filers 2011–2018 are absent from
  the XML entirely, and the IRS e-file index begins at submission year 2017.
  **The 2019 dip is a cache artefact, not a drop in grantmaking. Never read
  absence as "the organisation did not file."**
- **Schedule I Part II has a $5,000 floor.** Smaller grants are absent by
  design.
- **Part III grants to individuals carry no names — the form does not ask.**
  **1,264 returns report $7,318,402,903 this way**, unattributable by
  construction. [measured]
- **Fiscally sponsored projects file under the sponsor's EIN.** New Venture
  Fund files for Native sponsored projects: the project is Native, the filer is
  not.
- **Half of `np_orgs` can never have financials.** 6,453 of 12,764 (50.6%) are
  the 990-N e-Postcard tier (`bmf_filing_req_cd = 02`) — existence only: name,
  EIN, state. Another 1,491 (11.7%) are churches (`06`) and 2,060 (16.1%) carry
  a not-required code overall. The financial layer will only ever cover
  `full_990` (2,806) + `990_EZ` (1,316). [measured]
- **Place-name leakage is priced, not eliminated.** `placename_risk_flag`:
  2,401 `REVIEW` + 1,360 `HIGH` [measured]. The top 5 of the 412-organisation
  risk queue carry **80.3%** of the money, and **270 of 412 (65.5%) are
  invisible to the API or under $50k — ruling on them changes no aggregate.**
  One live false positive is on the record: `ORDER OF THE EASTERN STAR OF NORTH
  DAKOTA` sits at `funnel_stage = canonical_name_match` with evidence *"BMF
  name matched canonical tribe TRBF-CHCKHE-00 (Chickahominy)"* — matched on the
  token **EASTERN**, from *Chickahominy Indian Tribe — Eastern Division*. 1,831
  rows sit at `canonical_name_match` unruled.
- **Grantmaker 990-PF has no recipient EIN.** Form 990-PF Part XV does not ask.
  **14,320 of 18,656 rows are 990-PF** and carry no recipient identifier; only
  4,295 rows carry any `recipient_ein`. [measured] `recipient_match_basis`: 166
  rows matched on an EIN printed on a Schedule I, 450 on a guarded multi-word
  name phrase, 18,040 blank. **Matching is multi-word phrases only** — a single
  token can never match, which is what stops "Stanford", "Mason", "Cato" and
  "Hoover" linking on their own.
- **DonorsTrust and Donors Capital anonymise the donor by design.**
  `funder_is_donor_advised_fund = 1` on 3,859 rows [measured]. DonorsTrust is
  the largest anti-ICWA-side funder at $23.5M and the one about which the least
  can be said. **This is a hard wall and the file never infers past it.**
- **Grantmaker e-file coverage is uneven.** Eight of fourteen funders have
  TY2020–TY2024 only; Templeton and the two Koch entities additionally reach
  TY2016–TY2018. **Three indexed returns could not be retrieved** (Templeton
  TY2015, Koch Institute TY2015, Koch Foundation TY2015) and are recorded as
  `PARTIAL_SOME_RETURNS_INDEXED_NOT_RETRIEVED` — not as absence.
- **The IRS download page under-lists 2022 by one archive.**
  `2022_TEOS_XML_02A.zip` (1.41 GB, 222,974 members) serves HTTP 200 and is
  listed nowhere. It held 11 TY2021 grantmaker returns and 178 grantee returns.
  It was admitted **on the status code, never on URL plausibility**, with
  `basis = probe_verified_http_200_not_page_listed`. **Walk the numeric part of
  the archive name continuously and treat the letter suffix separately** — a
  first probe interleaved A/B/C/D and burned its miss budget before reaching
  `02A`.
- **The pass-through signal, at exactly its strength.** 532 grant rows / 58
  recipients / 58 funders / **$244,798,757** where the recipient reports
  lobbying above zero **on its own 990**. Restricted to `np_orgs` filers: 92
  rows / $33,579,722. [measured] *This is a co-occurrence of two filing facts.*
  Whether a grant was restricted is **unobservable here**. Every row carries
  `grant_caveat`, and `native_status_caveat` reads *"Schedule I is an EIN-keyed
  filing fact and asserts nothing about the Native status of either the filer
  or the recipient."*
- **Only 1,423 of 12,764 `np_orgs` rows (11.1%) carry a `cedar_uid`.**
  [measured] `np_ein_entity_hub.csv` and `np_ein_uei_bridge.csv` exist to close
  it and have not.
- **No 990 financials in the flagship view.** Assets, expenses, programme spend
  and fiscal year are on disk in `np_financials.csv`, `np_org_scale.csv` and
  `np_grantee_financials.csv`; `ntee_code` is on 9,251 `np_orgs` rows (72.5%).

---

## 8. Refresh

This is Cedar's clearest case of **one dataset with two clocks**.

| source | cadence | Cedar holds through | last pulled | due |
|---|---|---|---|---|
| IRS 990 e-file returns + index | **semiannual (Feb / Aug)**; ~18-month structural lag, p10 = **584 days** from FY end (n=58,355) | 2025-12-31 | 2026-08-07 | no |
| IRS EO BMF | **monthly**, ~1-month lag | 202603 | 2026-08-12 | source edge not established |
| FAC `api.fac.gov` | continuous acceptance; median **271d**, p90 **569d**, **30.93% land LATE**, max 3,464d | 2026-08-12 | 2026-08-12 | source edge not established |
| Grantmaker 990-PF / 990 | rides the 990 pull | 2025-11-30 | 2026-08-12 | no |

[measured — `docs/REFRESH_CADENCE.json`, regenerated 2026-09-02]

**A quarterly cadence on an 18-month lag manufactures churn.** Calendar-2025
fiscal-year ends currently sit at **12% of a December plateau**, because the
extended deadline is 2026-11-15; maturity is around mid-2027. Re-pulling
quarterly produces a series that looks like collapsing grantmaking and is
nothing of the kind.

**FAC must be re-pulled with a TWO-YEAR trailing window, every time.** *A
deadline the median hits and a third of filers miss is not a cadence.*

**What breaks if it is not re-pulled.** The 990 leg is the only route to new
Schedule I lines, and nothing else in Cedar observes money moving between two
named legal persons. The BMF leg silently ages the revocation and
filing-requirement fields — and since the BMF-presence check is already
circular, an aged BMF makes it *more* circular, not less.

**Rebuild commands.** `py -3 code/build.py plan nonprofits` prints the ordered
rebuilds-then-enrichers; `run nonprofits --execute` runs it. Note that
`code/781_upstream_grain_columns.py` is an **in-place enricher** and must run
last — a rebuild of `np_schedule_i_grants.csv` reverts `schedule_i_line_seq`
and the 101 phantom duplicates come back.

---

## Stale claims found while writing this

Ordered by how much damage acting on the wrong value would do.

1. **`docs/DATASET_CONTRACTS.md` and `docs/MONEY_TOTALLING_RULES.md` both say
   `132` cannot be run because its two XML caches "hold zero files."** They do
   not. `data/raw/external/irs990_schedc/xml` holds **28,677 XML files
   (971 MB)** and `irs990_grantee/xml` holds **3,697 (193 MB)** — 32,374 files,
   1.16 GB. This is the stated reason `781` had to patch in place instead of
   rebuilding, and the caches have **grown roughly fourfold since `132`'s build
   log recorded 6,870 Schedule C returns**. A `132` re-run today would produce
   *more* than 58,685 rows, not an empty table. **The stated blocker is gone
   and the opportunity is unrecorded.**
2. **`docs/DOC_CONTRADICTIONS_2026-08-26.md` — the arbiter's own ground-truth
   table, re-measured 2026-09-01 — still says `np_schedule_i_grants.csv` has
   "101 literal duplicates."** It has **0**. `781` fixed it the same day and
   the ground-truth row was not updated. This is the register's own documented
   failure mode, for at least the third time, in the one document the project
   instructs everyone to believe over the build logs.
3. **`docs/NONPROFIT_BUILD_LOG_2026-08-05.md` reports confidence tiers as
   A 1,090 / B 7,018 / X 4,656.** Measured: **A 712 / B 7,092 / X 4,960**.
   **Tier A fell 1,090 → 712** as the classification pass demoted place-name
   leakage. Anyone quoting "1,090 tier-A Native nonprofits" is 378 too high.
   (The same log's 990-tier table — 990_N 6,453 / full_990 2,806 / not_required
   2,060 / 990_EZ 1,316 / UNKNOWN 129 — is exactly right.)
4. **`docs/SCHEDULE_I_BUILD_LOG.md` says 628 distinct filers; there are 627.**
   Already recorded as contradiction B10. **A second, parallel off-by-one in
   the same log is recorded nowhere: it says "1,432 returns" and the file holds
   1,431 distinct `object_id`.**
5. **The same log says 1,372 returns report Part III individual grants; it is
   1,264.** The dollar figure beside it — **$7,318,402,903** — is exactly
   right, and that is the quotable number.
6. **The same log's output table gives `np_schedule_i_grants.csv` as 44
   columns; it has 65** (later enrichment by 167, 505 and 781). Expected drift,
   but a reader sizing the schema will be wrong by 21 columns.
7. **`docs/NONPROFIT_ENTITY_LINKAGE_BUILD_LOG.md`**: Schedule I recipient links
   are **3,505**, not 3,508; hub sources are `fac_single_audits` **798** (not
   786), `nho_register` **57** (not 53), `bie_uio` **11** (not 9). Every other
   figure in that log verified exactly.
8. **`docs/NONPROFIT_CLASSIFICATION_RESEARCH_LOG.md`** gives
   `place_name_coincidence` as 282 of a 375-row queue; `np_orgs` now holds
   **309**, and 398 rulings in total against the log's 371. Twenty-seven
   further place-name rulings were applied after the log was written.
9. **`docs/GRANTMAKER_FUNDING_FLOWS_BUILD_LOG.md` describes a
   `MERCATUS_NAMED_IN_TEXT` value that does not occur** — Mercatus Center Inc
   is its own legal person, so its 54 rows carry
   `NOT_APPLICABLE_SINGLE_LEGAL_PERSON`. **And a live trap the doc does not
   flag:** `grantmaker_funding_coverage.csv` counts by *recipient string*
   (`STANFORD` 111 + `HOOVER_NAMED` 18 = 129) while
   `grantmaker_funding_flows.csv` counts by *resolved target* (`STANFORD` 89 +
   `HOOVER_UNIT_IDENTIFIED` 40 = 129). **The two give different splits of the
   same 129 rows with nothing saying so**, and a reader joining them will
   conclude one is wrong. GMU is internally consistent (87 + 29 = 116 both
   ways).
10. **`docs/GAMING_FINANCIAL_EXHAUST_BUILD_LOG.md`,
    `docs/GAMING_SPEC_RECONCILIATION.md` and `code/147`'s own docstring all
    give FAC as 6,774 / 2,046 (30.2%).** It is **6,780 / 2,052 (30.3%)**.
    Already recorded as contradiction B6 — but the arbiter does not mention
    that `147`'s docstring carries the superseded pair, which is where the next
    reader will find it.
<!-- END EDITORIAL:nonprofits -->

<!-- BEGIN GENERATED:MEASURED -->

---

# Appendix M — measured from the delivered file

*Generated 2026-09-02 by `code/1143_methodology_papers.py` from `dist/customer/nonprofits.csv`, read whole with duckdb and never sampled. Not from `data/clean/`, not from a build log, not from `MANIFEST.csv`. Where this appendix and a document disagree, **the delivered file is right** and `verify` prints the disagreement rather than smoothing it over.*

*Grain, folded-in tables and per-column fill rates are in `dist/customer/nonprofits__CODEBOOK.md` and are deliberately not repeated here.*

## M1 · Sources, as the delivered rows themselves record them

**`source_dataset`** — 12,764 of 12,764 rows populated, 1 distinct value:

| value | rows |
|---|---:|
| `IRS Exempt Organizations Business Master File (eo1-eo4)` | 12,764 |

**`source_url`** — 12,764 of 12,764 rows carry one. Hosts, by row count:

| host | rows |
|---|---:|
| `www.irs.gov` | 12,764 |

### The terms rulings that bind this dataset

Quoted from `docs/PUBLICATION_POLICY.md`, which holds the rulings; this paper does not restate them from memory.

- **Owner ruling, 2026-09-02** (`<!-- BEGIN TERMS-OWNER-RULING-2026-09-02 -->`): *"So tribal websites, I actually don't care if they say it does scrape. Because if it's publicly available and you can scrape it, scrape it."* A tribal entity's own public pages may be harvested regardless of a terms statement. `source_terms_status = TERMS_STATED_RESTRICTIVE` on a Native entity's own site is now **a recorded observation, not a gate**.
- **Four things that ruling does NOT touch, and none is a terms question:** (1) technical access controls — nothing login-gated, no admin or staging paths, no exploiting a misconfiguration; (2) a natural person's data held apart from their public role — home address, personal email or phone, DOB, SSN/TIN; (3) non-tribal licensors — EMMA/MSRB bars redistribution of its output "sold or free of charge" and names "any manual process", with CUSIP Global Services as a second licensor; (4) proprietary identifiers — Casino City, D-U-N-S — held internally, never shipped.
- **A terms restriction is scoped to the SOURCE that stated it, not to the nation** (`<!-- BEGIN TERMS-SCOPE -->`), and it does not bind a third party's filing of the same fact.

## M2 · How the rows were built — the pipeline, in order

**One documented rebuild:** `py -3 code/build.py run nonprofits --execute`. `py -3 code/build.py plan nonprofits` prints the ordering below live; it is reproduced here so the paper stands alone.

The collection holds **12 tables**. Those with a named build stage, flagship first:

| table | rebuilt by | then enriched by (must run LAST) | status |
|---|---|---|---|
| `np_orgs.csv` **(flagship)** | — | — | shippable |

**A full rebuild and an in-place enricher on one file need an ordering, and the enricher must run LAST.** A `.bak_*_pre<script>` file sitting beside a table is the signal that an enricher has touched it since the last build. This has cost this project four reverts of one file in a single day.

The delivered spreadsheet is then assembled by `code/1137_customer_dataset_combine.py`, which folds supporting tables onto the flagship **only where the measured cardinality on the shared key is one**, reverts any join that moved the row count, and prefixes every joined column with its source table's stem. One-to-many tables contribute a count column instead of rows, so a money total cannot be multiplied by a join.

## M3 · How entities were attributed

Cedar keys every dataset to one identity layer. `cedar_uid` is permanent and never reused; the human-readable handle retires when an entity is reclassified, so **join on `cedar_uid`, never on the handle**. A compound handle is canonical, not broken — stripping a suffix to make a join work turns joinable rows into unjoinable ones while looking like a normalisation.

**Entity attachment in the delivered file:**

| key column | rows carrying one | distinct values | coverage |
|---|---:|---:|---:|
| `cedar_uid` | 1,423 | 238 | 11.1% |
| `tribe_id` | 1,423 | 238 | 11.1% |

**An unkeyed row is often the right answer, not a defect.** ADR-010 separates *"we could not identify the entity"* — a defect — from *"there is no single entity to identify"* — the correct representation. Coverage is measured against the *resolvable* denominator, not the row count.

### What `attribution_method` means **in this dataset**

`docs/schema/attribution_method_vocabulary.json`, declared 2026-09-02: *"`attribution_method` is three different columns sharing a name — a join method, an evidence provenance, and a name-match algorithm. Each table is gated against its OWN vocabulary."* Reading one table's sense into another is how a containment match came to key a dollar.

**This dataset carries no `attribution_method` column.** The identity evidence it does carry is measured below. Do not import another dataset's term list to interpret it.

**And a RULED METHOD IS NOT A POSITIVE RULING.** `attribution_method` says WHO decided; `confidence_tier` says WHAT was decided. All 317 `elijah_ruling` EIN rows in the ledger are tier **X** — *negative* — and a script that read "the method is in the RULED set" as "the answer was yes" published 317 owner *exclusions* as confident attributions. Standing detector: `py -3 code/293_lint_bug_classes.py`. [from the record — `START_HERE.md`, defect class 1b]

### Every identity, tier and method column, measured

- **`cedar_link_tier`** — 3 distinct values: `(blank)` 6,597 · `X` 4,711 · `B` 1,372 · `A` 84
- **`confidence_tier`** — 3 distinct values: `B` 7,092 · `X` 4,960 · `A` 712
- **`disposition`** — 10 distinct values: `CANDIDATE_NAME_ONLY` 5,082 · `EXCLUDED_PRIOR_RULING` 4,681 · `CANDIDATE_NAME_MATCH_UNVERIFIED` 1,573 · `NATIVE_VERIFIED_STRICT` 697 · `EXCLUDED_PLACE_NAME_COINCIDENCE` 279 · `CANDIDATE_NAME_MATCH_GENERIC_TOKEN_ONLY` 258 · `CANDIDATE_STATE_VALIDATED` 105 · `NATIVE_PROPOSED_AWAITING_OWNER_RULING` 73 · `NATIVE_RULED_VERIFIED` 14 · `CONFLICT_EXCLUDED_AND_RULED_NATIVE` 2
- **`entity_match_method`** — 5 distinct values: `(blank)` 11,314 · `containment` 1,344 · `exact` 48 · `ruled_not_a_native_entity` 27 · `core` 23 · `alias` 8
- **`entity_tier`** — 3 distinct values: `(blank)` 6,379 · `X` 4,962 · `B` 1,369 · `A` 54

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

- **L649** *(under “`nonprofits` — `np_orgs.csv`, 12,764 rows”)* — ## `nonprofits` — `np_orgs.csv`, 12,764 rows
- **L662** *(under “`nonprofits` — `np_orgs.csv`, 12,764 rows”)* — **9,251 rows (72.5%)** of `np_orgs.csv` itself and is not shown.
- **L745** *(under “THE SHORT LIST — what this week can fix without a single download”)* — | 3 | `nonprofits` | show `funnel_stage` + `evidence` beside `classification_ruling`, or populate the ruling | 4,651 excluded rows read UNRULED |

## M5 · The money rules — which columns may be summed

Measured over the delivered file. **A sum printed here is the unfiltered arithmetic sum of the column and is NOT necessarily a figure a buyer may quote** — the fence below says which are and which are not.

| column | rows populated | distinct values | sum (unfiltered) | min | max |
|---|---:|---:|---:|---:|---:|
| `bmf_asset_amt` | 10,328 | 4,973 | $46,834,845,362.00 | $0.00 | $3,917,637,466.00 |
| `bmf_income_amt` | 10,328 | 4,960 | $24,712,097,325.00 | $0.00 | $1,455,214,831.00 |
| `bmf_revenue_amt` | 9,992 | 4,660 | $19,907,723,984.00 | $-27,377.00 | $1,092,849,379.00 |

### The fence, quoted verbatim from `docs/MONEY_TOTALLING_RULES.md`

That document is authoritative on which columns may be summed. It is **quoted here, never re-derived** — re-deriving a totalling rule from the data is precisely the error it exists to prevent.

**`docs/MONEY_TOTALLING_RULES.md` states no one-line rule for `np_orgs.csv`.** Where this dataset carries a money column and the rules document does not fence it, treat that as an open item, not as permission.

## M6 · Known limits, stated plainly

**Readiness: READY.** [measured — `docs/DATASET_READINESS.md`, regenerated by `py -3 code/518_dataset_readiness.py`]

| tables | grain | keys | duplicates | agg-unsafe | rebuild |
|---|---|---|---|---|---|
| 10 | 10/10 | 10/10 | clean | 0 | declared  |

The twelve-point contract a dataset is held to — grain declared and validated; keys and cardinality measured, not guessed; duplicates removed or the distinguishing dimension declared; entity attachment where the subject is an entity; every harvested row in a named disposition bucket; unresolved identity conflicts never shipping as definite facts; no double-counting path; one documented rebuild that does not destroy later enrichment; an update runbook another session can execute from the document alone; regression and semantic-diff gates over the outputs; column hygiene; and an inclusion basis on every row.

**Do not sell past the evidence.** Where this paper states a figure it was measured on the date stamped beside it, from the file named beside it. Where it states a decision it names who made it. Anything not stated here is not known.

## M7 · Fingerprint — what makes this paper stale

`verify` re-measures the four values below against `dist/customer/nonprofits.csv` and **exits 1 if any has moved**. A methodology paper is stale the moment its dataset is rebuilt, and a stale paper that cannot say so is worse than no paper.

```json
{
  "dataset": "nonprofits",
  "file": "dist/customer/nonprofits.csv",
  "bytes": 13942964,
  "rows": 12764,
  "columns": 70,
  "header_sha256": "5de8b8b57ff661e719fac2c9b63a9488047e6ee41bd398935df6ab31055ae923",
  "measured": "2026-09-02"
}
```

Cross-check against `dist/customer/MANIFEST.csv`, which `code/1137_customer_dataset_combine.py` wrote at build time: it records **12764 rows × 70 columns**. The two agree.

<!-- END GENERATED:MEASURED -->
