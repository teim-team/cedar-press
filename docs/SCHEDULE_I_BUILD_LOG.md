# Form 990 Schedule I layer — build log, 2026-08-12

Build script: `code/132_build_schedule_i_layer.py`
(`--steps bmf,parse,build,drift,review,codebook,report`)

Outputs
| Path | What |
|---|---|
| `data/clean/np_schedule_i_grants.csv` | **58,685 rows**, 44 cols — one row per named grant recipient |
| `data/clean/np_schedule_i_filers.csv` | **10,314 rows** — one row per parsed return |
| `review/np_schedule_i_recipients_2026-08-12.csv` | 2,138 recipients needing a ruling |
| `review/np_schedule_i_unnamed_recipient_rows_2026-08-12.csv` | 26 rows naming no organisation |
| `data/raw/external/irs990/bmf_full_2026-08-12/` | the **full** IRS EO BMF, 1,957,340 orgs, 325 MB |
| `logs/132_build_report_2026-08-12.txt` | the run report |

---

## The task premise was three-quarters wrong, and that is the first finding

The brief said `np_orgs.csv` holds 12,764 nonprofits **with zero financials**,
that Schedule C is **0 of 8,507**, and that the IRS bulk XML is the unbuilt
frontier. Measured before writing any code:

| Claim | Measured |
|---|---|
| "zero financials" | `np_orgs.csv` carries `bmf_revenue_amt`, `bmf_asset_amt`, `bmf_income_amt`, `bmf_filing_req_cd`, NTEE and ruling date on all 12,764 rows. **BMF matching was already done.** |
| "Schedule C is 0 of 8,507" | **2,195 returns parsed**: 93 filed a Schedule C, 2,102 confirmed they filed none. `schedc_basis` is populated on all 8,507 rows. |
| ProPublica does not expose Schedule C | **True**, and already recorded. |
| IRS bulk XML is tens of GB | True of the archives, **irrelevant to the method** — scripts 99 and 112 read individual ZIP members by HTTP **range read**, 1,449 MB instead of ~30 GB. |

So priorities 1 and 2 of the brief were complete before this session. The
marginal value was entirely in the schedules — and specifically in the one
nobody had touched.

## The actual gap: 10,567 return XMLs on disk, Schedule I never parsed

```
data/raw/external/irs990_schedc/xml     6,870 returns   236 MB   (script 99)
data/raw/external/irs990_grantee/xml    3,697 returns   197 MB   (script 112)
```

Both builds parsed **Schedule C** and neither parsed **Schedule I**. Sampling
showed `RecipientTable` in 11–20% of them. Schedule C says whether an
organisation lobbied; **Schedule I Part II names the organisations it PAID,
with their EINs** — the only place in the Form 990 where money is observed
moving between two named legal persons, and therefore the only one that can
speak to Elijah's pass-through question.

**This build issued zero requests for return XML.** It re-read what was
already here.

## What came out

**58,685 recipient grant rows** across **1,432 returns**, **628 filers**,
**18,708 distinct recipient EINs**, tax years 2015–2025.
$16,439,532,633 cash and $878,481,598 non-cash (never added together).

`111.parse_local_schedule_i()` is the narrower ancestor of this parser — one
directory, eight of the fourteen elements. **It was not modified**;
`advocacy_passthrough` depends on it. `--steps drift` reproduces it row-for-row
instead: **0 rows differ wherever a recipient is actually named.** The only
disagreement is 5 rows that name nobody, which 111 keeps and 132 holds out.

---

## THE ERROR THIS BUILD MADE AND CAUGHT — np_orgs membership is not a Native ruling

The first cut labelled every filer in `np_orgs.csv` "Native-connected" and
reported **$1.01B of Native grantmaking**. The top grantmaker came back:

```
$58,307,004   SEMINOLE BOOSTERS INC        EIN 591561180
              confidence_tier  = X
              funnel_stage     = excluded_by_prior_ruling
```

Florida State University's athletics booster club. Behind it: South Dakota
State University Foundation, Cayuga Medical Center at Ithaca, Sioux Falls Area
Community Foundation, North Dakota Community Foundation — a clean sweep of the
place-name and institution-word failures this project already documents.

**`np_orgs.csv` is a candidate funnel, not an adjudication.** 12,393 of its
12,764 rows are `UNRULED`; **4,933 are `confidence_tier` X, which is a NEGATIVE
ruling.** AGENTS.md is explicit: *"An X-tier row is a negative ruling and must
never resurface."* A flat `filer_in_np_orgs` flag resurfaced 217 of them.

`filer_population` is now tiered, and the X rows are **named as excluded**
rather than quietly counted:

| population | filers | rows | cash |
|---|---:|---:|---:|
| `not_in_np_orgs_universe_native_status_not_established` | 137 | 50,909 | $15,425,796,948 |
| `np_orgs_EXCLUDED_by_prior_ruling` | 217 | 4,341 | $566,340,541 |
| `np_orgs_candidate_tier_B_unruled` | 248 | 3,212 | $416,398,351 |
| `np_orgs_candidate_tier_A_unruled` | 22 | 163 | $25,102,781 |
| `np_orgs_ruled_tribally_controlled` | 2 | 52 | $5,742,647 |
| `np_orgs_ruled_native_serving` | 1 | 8 | $151,365 |

**Not one line is a publishable "Native grantmaking" total.** Only the
`np_orgs_ruled_*` rows rest on a ruling, and they are small. That is the honest
state of the layer.

### The other half of the same trap

The 137 filers outside `np_orgs` are there because script 112 fetched the
returns of the **GRANTEES of Native funders**. Their presence says they
*received* money from a Native funder and nothing else. The population is led
by **Johns Hopkins ($3.9B), Mayo Clinic ($3.8B) and New Venture Fund ($2.4B)** —
the fiscal sponsor already recorded in `docs/GRANTEE_990_LOG.md` as not Native.
It also contains **Southcentral Foundation ($117M)**, which plainly is. It is
`UNESTABLISHED` in both directions and must not be read either way.

---

## THE 7871 TEST WAS WRONG UNTIL THE FULL BMF WAS FETCHED

The only BMF on disk was
`irs_bmf_slice_universe_2026-08-05.csv` — **the 12,764-row Native-connected
slice, not the BMF.** Testing a recipient EIN against it answers *"is this
recipient in our Native subset"* and **cannot** answer *"does this EIN file a
Form 990 at all."* The first cut conflated them and labelled **17,848 ordinary
charities with the IRC 7871 signature.**

The full BMF is four small CSVs. Fetched under a disk guard (below):
**1,957,340 organisations, 325 MB.** With the real denominator:

| recipient BMF status | rows |
|---|---:|
| `in_full_irs_bmf` | 39,178 |
| `absent_from_full_irs_bmf` | 16,344 |
| `no_ein_reported_on_schedule` | 3,163 |

**6,217 distinct recipient EINs are printed on a filed Schedule I and absent
from the entire BMF.** *That* is the 7871 signature — an entity outside the
Form 990 universe, most often a tribal government. It files no return. **This
is not a gap and is not queued as one.** A further 1,069 rows have the filer
writing `TRIBE` in the IRC section, naming the case in its own words.

This independently reproduces `docs/PHILANTHROPY_DISCOVERY_LOG.md` and
`docs/GRANTEE_990_LOG.md`, which reached the same conclusion from 153 of 601
grantee EINs. Three builds, one finding.

---

## CROSS-SOURCE VERIFICATION — the XML beats the ProPublica scrape

`docs/CROSS_SOURCE_VERIFICATION.md`: one source is a claim, two that agree is a
verification, two that disagree is a finding. Script 75 built Schedule I for 7
Native funders by scraping **ProPublica HTML**; this build reads the **filed
XML**. Seven returns overlap.

| return | funder | ProPublica | XML |
|---|---|---:|---:|
| 202513519349300916 | First Nations Development Institute | 279 rows · $14,635,648 | **identical** |
| 202533079349301933 | American Indian College Fund | 38 rows · $13,887,686 | **identical** |
| 202503459349301300 | Native Americans in Philanthropy | 17 rows · $2,922,229 · **5 zeroed** | 18 rows · $4,434,729 · 0 zeroed |
| 202511359349314541 | Seventh Generation Fund | 108 rows · $3,425,168 · **10 zeroed** | 129 rows · $4,396,998 · 0 zeroed |
| 202533219349321098 | Seventh Generation Fund | 15 rows · $510,000 · **3 zeroed** | 16 rows · $790,000 · 0 zeroed |
| 202510659349300341 | First Nations Development Institute | 296 rows · $14,578,358 | 300 rows · $14,790,913 |
| 202533189349304618 | Indian Land Tenure Foundation | 12 rows · $1,534,487 | 13 rows · $1,546,340 |

**Two returns agree to the cent** — that verifies the XML parser against an
independent source. **Five disagree, always in the same direction:** the HTML
scrape drops rows and zeroes amounts. Across the seven,
ProPublica reports **$51,493,576** against the XML's **$54,482,314** —
understating the funders' own grantmaking by **$2,988,738 (5.5%)**, with **18
grant amounts rendered as $0** and 28 rows missing entirely.

**The XML is the filed return; ProPublica renders it.** The XML wins.
One recipient organisation was lost from the grantee universe altogether —
The Nature Conservancy, $962,500 from Seventh Generation Fund.

Note also that ProPublica reached **7 object_ids the local XML cache does not
hold**, so the two sources are complementary, not redundant.

---

## THE PASS-THROUGH SIGNAL — stated at exactly its strength

**532 grant rows, 58 recipients, 58 funders, $244,798,757**, where the
recipient reports lobbying above zero on **its own** filed 990. Restricted to
filers inside `np_orgs`: **92 rows, 36 recipients, 27 funders, $33,579,722**.

**This is a co-occurrence of two filing facts.** It does not state that any
grant paid for any lobbying, and no column supports that reading. Money is
fungible, most grants are restricted to program work, and Schedule I gives a
purpose line rather than the grant agreement — whether a grant was restricted
is **unobservable here**. Every row carries that sentence in `grant_caveat`.

990 lobbying is lawful, disclosed activity; many organisations elect 501(h)
precisely to report it transparently. Nothing in this file carries a pejorative
framing.

Recipient Native-evidence tiers: **A 342** (EIN join *and* guarded name match
agree) · **B 4,127** (one leg alone) · none 54,216. A name match is never Tier A.
`resolve_entity` is imported from script 33 and the eight containment guards
from script 111; no second matcher was written.

---

## COVERAGE CAVEATS BY YEAR

| tax year | returns | rows | cash |
|---:|---:|---:|---:|
| 2015 | 2 | 5 | $118,735 |
| 2016 | 68 | 4,214 | $995,616,988 |
| 2017 | 95 | 4,825 | $1,710,604,257 |
| 2018 | 104 | 5,284 | $1,132,791,567 |
| 2019 | 72 | 4,257 | $870,458,916 |
| 2020 | 107 | 6,098 | $1,823,453,263 |
| 2021 | 115 | 6,528 | $1,772,372,277 |
| 2022 | 117 | 6,375 | $1,784,798,692 |
| 2023 | 146 | 6,706 | $2,542,948,424 |
| 2024 | 355 | 9,779 | $2,660,789,795 |
| 2025 | 251 | 4,614 | $1,145,579,719 |

- **E-file coverage is PARTIAL before tax year 2019.** Mandatory e-filing arrived
  with the **Taxpayer First Act**; paper filers 2011–2018 are **absent from the
  XML entirely**. An organisation with no return here may simply have filed on
  paper. **Never read absence as "the org did not file."** The 2019 dip (72
  returns) is a coverage artefact of the cache, not a drop in grantmaking.
- **The IRS e-file index begins at submission year 2017**, so tax years before
  roughly 2015 have no machine-readable return at any URL.
- **Schedule I Part II has a $5,000 floor.** Smaller grants are absent by design.
- **Part III grants to individuals carry no names** — the form does not ask.
  1,372 returns report **$7,318,402,903** this way, unattributable by
  construction, counted only to give the invisible channel a size.
- **Fiscally sponsored projects file under the sponsor's EIN**, so the
  organisation named is not always the legal person paid.
- **Tribal governments are outside the Form 990 universe under IRC 7871.**
- **This is a FLOOR on Schedule I, not the universe.** It reads only what
  scripts 99 and 112 had already retrieved for their own Schedule C purposes.

---

## DISK — the binding constraint, and what was refused

Free space on C: was **6.87 GB** at the start. The tens-of-GB bulk XML pull the
brief contemplated was **not attempted, and would have been refused**: a single
year's archives exceed the entire free space, and scripts 99/112 already
established that range reads make the download unnecessary.

What was fetched: the four EO BMF extracts, **325 MB**, streamed under a hard
guard — `.part` then rename so an interruption cannot look like a completion, a
400 MB per-file fuse, and a **2 GB floor checked on every 1 MB chunk**.

```
200  eo1.csv   48.6 MB
200  eo2.csv  125.7 MB
200  eo3.csv  164.6 MB
200  eo4.csv    0.9 MB
lowest free space during the BMF fetch: 6.43 GB
```

**Disk high-water mark (lowest free space observed): 5.86 GB**, measured after
the build with other agents also writing. The 2 GB floor was never approached.
Total footprint added by this build: **~390 MB** (325 MB BMF + 66 MB CSVs).

`www.irs.gov` was claimed in `logs/_HOSTLOCK_www.irs.gov.json` before the fetch
and released after; sequential, 2 s spacing, four requests, zero refusals. A
transport failure would have been recorded as `http_status=0` with the reading
spelled out, never as a 404 — but none occurred.

## Regression check

`code/62_no_regression_check.py` before: **no regressions**, 39 metrics.
After: **no regressions**. `codebook_variables` 1,424 → 1,454,
`codebook_undocumented_public` 0. `codebook_master.csv` was backed up to
`.bak_2026-08-12_pre132` and only rows whose `dataset` is
`04e_schedule_i_grants` were replaced. **No existing file was overwritten** —
`np_orgs.csv`, `np_financials.csv`, `np_grantee_financials.csv`,
`advocacy_passthrough.csv`, `schedule_i_grantees_2026-08-06.csv`, the spine and
script 111 are all byte-identical after the run.

Script numbering: `130` was taken by another agent's
`130_build_section_106_consultation.py` mid-session and `131` by
`131_merge_archive_backfill.py`; this build moved to **132**. AGENTS.md is right
that the numeric prefix no longer guarantees a unique step — check immediately
before writing, not once at the start.

## What would move this furthest next

1. **Rule the 2,138 recipients** in `review/np_schedule_i_recipients_2026-08-12.csv`.
   Every Tier B row is one ruling away from being publishable, and the file is
   sorted by dollars so the top of it is where the value is.
2. **Extend the retrieval queue to the whole `np_orgs` Schedule-I-possible
   universe.** `docs/GRANTEE_990_LOG.md` proved the retrieval rate is a function
   of queue completeness, not access (34.3% → 97.0%). Range reads cost ~50 KB per
   return, so this is disk-cheap even now.
3. **Re-run script 75's ProPublica grantee pull against the XML** for the 7
   object_ids the cache lacks, and correct the 601-grantee list for the 18 zeroed
   amounts found above.
4. **The 6,217 no-BMF recipient EINs are the most Native-dense group in the
   file** — the 7871 population, receiving money and invisible to every 990-based
   dataset. Resolving their names against the spine is entity discovery, not
   gap-filling.
5. **Native American Agriculture Fund 990-PF Part XV** — still the highest-value
   unworked funder, unchanged from the last three logs.
