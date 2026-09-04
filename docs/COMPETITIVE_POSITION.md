# Competitive Position

*Written 2026-08-06. Ambition under assessment: Cedar Press as the Bloomberg Government
of the Native economy.*

*Every Cedar Press number in this document was measured from the files in this folder on
2026-08-06, not copied from `docs/handoffs/STATE_OF_BUILD.md`. Where a measurement disagrees with the
state document it is flagged. Incumbent facts are marked by source strength: **[verified]**
on the vendor's own page, **[reported]** third-party, **[unknown]** where nobody publishes it.*

---

## ⚠ CORRECTION 2026-08-26 — TWO LOAD-BEARING CLAIMS IN THIS DOCUMENT ARE FALSE

**Read this before quoting any coverage number below.** This document was written
2026-08-06. Two things happened after it that it never learned about: the **prime archive
backfill of 2026-08-12** and the **subaward promotion of 2026-08-06** (which landed the
same afternoon this file was being written). Every strategic conclusion in sections 1, 3
and 5 that rests on either claim is built on a fact that is no longer true.

The claims are struck in place rather than deleted, because *why* they were wrong is worth
as much as the fix.

### FALSE CLAIM 1 — "Prime contracting ends FY2022"

Asserted in this document at §0 Finding 5, §1 item 8, §2, §3 (the moat limit), §3.1 (the
profile-page table, the demo-year paragraph, the chart terminator), §3.3 (the alert
decision), §4 Read 1, and §5 addition 2. **It is false.**

Measured from `data/clean/prime_contracts.csv` on 2026-08-26:

| | this document (2026-08-06) | measured 2026-08-26 |
|---|---:|---:|
| rows | 617,142 | **1,217,768** |
| fiscal years | 2000–2022 | **2000–2026** |
| total obligations | — | **$310.01B** |
| attributed | — | **$244.77B (79.0%)**, 498 entities |
| FY2023 | 0 | **45,747** |
| FY2024 | 0 | **53,056** |
| FY2025 | 0 | **48,879** |
| FY2026 | 0 | **61,813** |

The gap was closed by the archive backfill logged in `docs/PRIME_ARCHIVE_PULL_LOG.md`
(2026-08-12), which contributed `prime_contracts_archive_backfill.csv`, 631,507 rows.
FY2007 and a handful of assistance years remain host-blocked; **the recent end does not.**

**What this changes strategically.** §5's "addition 2: close the recent-years hole in
prime contracting, FY2023–FY2026" is **done**. The single largest substantive gap
identified against BGOV is closed. §4's read that "a federal-contracting buyer comparing
them sees a product with FY2022 data" no longer describes the product. §3.1's "the demo
year is FY2022" reasoning — *last year in which prime, assistance and lobbying are all in
source window* — should be re-derived against the current windows before any screenshot is
built on it. §3.3's refusal to ship a "new contract award" alert was reasoned entirely
from the FY2022 terminator and should be re-decided, not inherited.

**Why it went stale silently.** The claim was true when written and there is no version
control here, so nothing forced a re-read when the backfill landed six days later. That is
the whole argument for dating a claim rather than stating it. Two figures elsewhere carry
the same staleness and are **not** to be quoted: `dist/notes_index.json` and
`dist/02_prime_contracting/prime_contracts.notes.json` both still record prime at 617,142
rows / 2000–2022 / 470 entities, vintage 2026-08-06. `dist/` has not been rebuilt since.

### FALSE CLAIM 2 — "the promoted file is 998 rows; the 345,090-row pull is staged, not promoted"

Asserted at §0 Finding 5, §3.1 (the profile-page table, "Subcontracting — thin"), and §5
addition 2. **Both halves are false, and the second half is false in a way worth
recording, because the number is not a subaward count at all.**

Measured 2026-08-26:

| | this document | measured |
|---|---:|---:|
| promoted `data/clean/subawards.csv` | 998 | **63,548** |
| promotion status | "staged, not promoted" | **completed 2026-08-06** |

The arithmetic closes exactly: `_PROMOTION_SUMMARY.json` records **55,035** rows retained
by `code/45_promote_subawards.py`, and the raw-match pass of 2026-08-07 added **8,513**.
55,035 + 8,513 = **63,548**. Every staged row was checked for membership against the clean
file on `(subaward_number, prime_award_unique_key, subaward_amount)` on 2026-08-26 — **zero
staged rows are uncovered**. There is nothing left to promote.

**998 is not the promoted file.** It is one of three *source datasets inside* it — the 2023
HigherGov export. `_PROMOTION_SUMMARY.json`: `usaspending_fsrs_pull` 53,429 ·
`highergov_2023_export` 998 · `funding_forward_fill` 608.

**345,090 was never a count of Native subaward rows.** It is the raw all-recipient row
count of the **first 11 of 26 fiscal years** of the bulk pull — the whole federal subaward
universe with no recipient filter, of which only **1,798 rows were Native-linked** at that
point. `docs/SUBCONTRACTING_USASPENDING_PULL_2026-08-05.md` §1 states this plainly, and its
own PROMOTION section — appended the same day — **supersedes §1**: 22 fiscal years on disk,
**6,613,471 raw rows**, 53,429 Native-linked. This document quoted the superseded §1
figure, and `_SOURCE.md` in the raw folder is stale in the identical way
(`docs/SUBAWARD_RAW_MATCH_LOG.md` line 328 already flagged it).

Two adjacent numbers inherit the error:

- **"51,396 net-new UEIs"** (§5 addition 2, twice) is the same superseded 11-FY figure. The
  promotion section states **251,814**; the staged
  `subaward_uei_netnew_2026-08-05.csv` holds **252,078 rows**.
- That 252,078-row file is a **UEI dimension table — one row per UEI, 8 columns**. It is
  **not subawards.** Adding it to a subaward row count produces a phantom ~317k figure,
  and it has fooled at least one reader. Do not sum it into anything.

**What this changes strategically.** §3.1's "Subcontracting — thin, promoted file is 998
rows, 42 entities" is wrong by a factor of 64 on rows. The current file carries
`prime_native_tribe_id` on 26,430 rows and `sub_native_tribe_id` on 38,336, and **either is
populated on 63,504 of 63,548 — 99.9%.** §5 addition 2's instruction to "resume it with
`code/43_resume_subaward_pull.sh`" is **superseded**: the live route is
`code/121_pull_subawards_api.py canary`, then `pull --sequential`, then re-run 41 and 45.
Never raise `MAX_INFLIGHT` above 1.

### What remains TRUE in the coverage limits list

Re-checked 2026-08-26 and unchanged: the pre-FY2007 recipient-identifier floor on
assistance; the FSRS 2010 floor on subawards; the gaming open-date and revenue limits; the
compact-recall figure; and the 14.2% Federal Actions title/abstract hit rate. The
FY2021–FY2024 subaward hole (173/89/120/166 rows) is also still real, but it is **upstream**
— `data/raw/subcontracts/usaspending_2026-08-12/_state.json` shows those four years each
`status: failed`, `total_rows: 0`, from a service-wide bulk_download outage proven by a
prime-award control and an FY2015 replay. It is not a Cedar Press gap.

### Numbers in §0 that are stale but were NOT re-derived here

§0's ground-truth table (spine 866, ledger 19,232 links, tier A 1,705) is a 2026-08-06
measurement and is superseded — the ledger now holds **20,559 rows**, tiers **A 2,148 · B
5,690 · C 12,524 · X 197**, with **`tier_A_ruled` = 1,538**. §0's own note that the ledger
is a live file and must be re-measured before external quotation is the right instinct and
still applies. Every Finding-1-through-4 percentage below is computed off the 08-06
denominators; treat the *shape* of those findings as live and the *percentages* as dated.

---

## 0. Ground truth before the comparison

A competitive claim that outruns the data is worthless, so start with what is
actually on disk.

> **⚠ THIS TABLE IS TWO GENERATIONS STALE. Flagged 2026-08-26.** The right-hand column is a
> 2026-08-06 measurement of a ledger that has since been rebuilt and a spine that has since
> grown twice. **This document is now mixed-vintage** — its prime-contracting figures were
> corrected today and read as current, while this table does not. Do not quote it.

| Measured | Value **as written 2026-08-06** | **Measured 2026-08-26** |
|---|---|---|
| Spine entities | ~~**866**~~ (348 federally recognized tribes · 229 federally recognized Alaska Native villages · 173 ANC village corps · 64 state-recognized · 22 federal constituency orgs · 12 ANRCs · 9 self-governance consortia · 6 ANCSA group corps · 3 state constituency) | **1,310** — 349 federally recognized tribes · 228 Alaska Native villages · **185 BIE schools** · 173 ANC village corps · 64 state-recognized · **64 Native CDFIs** · **55 intertribal orgs** · **43 UIOs** · **37 TCUs** · **31 NHOs** · **29 Native financial institutions** · 22 federal constituency · 12 ANRCs · 9 consortia · 6 group corps · 3 state constituency |
| Identifier links | ~~**19,232**~~ (13,191 UEI · 4,937 CAGE · 1,104 EIN) | **20,559** |
| Confidence tiers | ~~A **1,705** · B 4,637 · C 12,711 · X 179~~ | **A 2,148 · B 5,690 · C 12,524 · X 197**, of which **`tier_A_ruled` = 1,538** |
| Entities carrying at least one tier-A link | ~~**265 of 866 (31%)**~~ | not re-derived; the denominator alone moves it from 31% to ~20% |
| Entity-year panel | 11,865 rows, **626 entities**, 1999–2026 | not re-derived |
| Elijah rulings on file | 164 | not re-derived |

**The spine finding below is REVERSED, and that is the most consequential thing on this
page.** The 2026-08-06 text says the spine *"contains **no NHO class, no intertribal class
and no nonprofit class at all**"* and concludes that *"the gap is entirely NHOs and Native
organizations."* **That gap is closed.** The spine now carries 31 NHOs, 55 intertribal
organizations, 64 Native CDFIs, 43 UIOs, 37 TCUs, 185 BIE schools and 29 Native financial
institutions as first-class `entity_class` values — the merges are logged in
`docs/TCU_CDFI_BUILD_LOG.md` (952 → 1,082) and `docs/BIE_UIO_BUILD_LOG.md` (1,082 → 1,310).

**A specific trap in this document.** Further down, this file *corrects* an earlier "687
entities" figure up to 866 in an authoritative voice. That correction was right in
August and is now itself two generations stale — which makes 866 look **adjudicated** when
it is merely old. Four values for the spine count are in circulation across `docs/`
(687 · 866 · 952 · 1,310) and **only 1,310 is current**, verified against
`data/spine/cedar_entity_spine.csv` on 2026-08-26. See
`docs/DOC_CONTRADICTIONS_2026-08-26.md`.

**The spine is narrower than the pitch.** It is described internally as covering tribes,
ANCs, NHOs, intertribal orgs and Native nonprofits. Measured, it contains **no NHO class,
no intertribal class and no nonprofit class at all** — the nine `entity_class` values are
tribes, Alaska Native villages, village/regional/group corporations, state-recognized
tribes and constituency/consortium entities. NHOs live in `nho_register.csv` (218 rows,
12 rulings-verified against a 190-name DOI roster), intertribal orgs in
`intertribal_orgs.csv` (57), nonprofits in `np_orgs.csv` (12,764, of which 739 are
tier A and 4,933 already excluded). Two ledger rows point at `NHO-` IDs that do not exist
in the spine.

Against the stated ceilings the tribal side is essentially complete — 348 tribes plus 229
Alaska Native villages is 577 against a 575-entity federal list — and the ANC side is
**191 of 196**. The gap is entirely NHOs and Native organizations, and it is a *spine*
gap, not a data gap: the rosters exist, they are just not in the entity table the product
is keyed on.

Five findings from that table matter more than anything the incumbents do.

*The identifier ledger is a live file — tier A read 1,699 at 14:13, 1,705 at 14:22 and
1,708 at 14:44 on 2026-08-06, while another session was rebuilding it. All figures below
are as of the 14:22 build. The drift is a few rows in 19,232 and changes no conclusion,
but it is a reason to re-run the measurements before quoting any of them externally.*

**Finding 1 — 878 of the 1,705 tier-A links (52%) carry no spine ID.** Every one is
`attribution_method = bgov_manual`: the BGOV crosswalk, the single richest hand-verified
asset in the project, resolves to a *name string* (241 distinct) and not to a `tribe_id`.
Measured directly:

```
tierA 1705 · with BLANK tribe_id: 878 (52%) · all bgov_manual
tierA links resolved to a spine ID: 827, covering 265 entities of 866
```

An entity profile page is keyed on the entity. Half the best evidence cannot currently
reach one.

**Finding 2 (2026-08-06) — six of the ten datasets have a zero-percent-populated
entity key.** Not "sparse." Zero.

> **CLOSED 2026-09-01. Finding 2 is no longer true of any dataset.** Every
> zero above is now populated; the weakest is nonprofits at 11.1%. The finding
> was correct when written and it drove the identity work that fixed it — which
> is why it is kept rather than deleted.

*Denominators corrected 2026-08-26 where the underlying file has since grown. The
2026-08-06 numerators were floors, not current values.*

**RE-MEASURED 2026-09-01 (workstream H), and the five bolded zeros are no longer
zero.** They were the sharpest claim in this section — *"Not 'sparse.' Zero."* —
and every one of them has been closed since. Leaving them in a
competitive-position document understates the product by the exact amount of
work that has been done on it. Keyed counts below are non-empty `cedar_uid`,
measured by `code/521_inventory.py`; per-table figures in `docs/INVENTORY.md`.

| Dataset | Entity key | Populated (2026-08-06) | Live 2026-09-01 |
|---|---|---|---|
| Prime contracting | `cedar_uid` | 279,432 / ~~617,142~~ (45%), 424 distinct | **888,958 / 1,217,768 (73.0%)**, 498 distinct entities, $244.77B attributed |
| Federal funding | `cedar_uid` | 365,535 / ~~476,924~~ (77%), 361 distinct | **552,602 / 701,955 (78.7%)** |
| Lobbying | `cedar_uid` | 27,796 / 27,796 (100%), 300 distinct | 26,484 / 27,796 (95.3%) — *fell because 353 WITHDREW entity ids a correction disproved; a lower number here is the correction working* |
| Subcontracting | `cedar_uid` | ~~998 / 998 (100%), 92 distinct~~ | **31,483 / 72,837 (43.2%)** on the sub side; the file grew 63,548 → 72,837 |
| **Compacts** | `cedar_uid` | **0 / 707** | **702 / 707 (99.3%)** |
| **Gaming facilities** | `cedar_uid` | **0 / 774** | **785 / 787 (99.7%)** |
| **Nonprofits** | `cedar_uid` | **0 / 12,764** | **1,423 / 12,764 (11.1%)** — closed, but the weakest of the five |
| **Bills** | bridge table | **0 / 3,037** | **676** rows in `native_bills_entity_bridge.csv`, all keyed |
| **Federal Actions** | bridge table | **0 / 156,452** | **5,786** rows in `federal_actions_entity_bridge.csv`, all keyed |

**Bills and Federal Actions changed shape, not just count.** Neither carries an
entity column on the fact table any more; both key through a **bridge**, which
is the correct many-to-many shape and the one `nagpra` already runs at 51,521
rows. Quoting "0 / 156,452" against a table that was never going to hold the
key is the wrong denominator as well as the wrong numerator.
| **Ownership events** | `native_entity_neid` | **0 / 98** |

"Cross-dataset linkage" is the product thesis. Today it is true of four datasets and
false of six. This is the gap between the pitch and the build, and it is the thing to
fix before anything is sold.

**Finding 3 — the tier-A prime dollar totals do not reconcile, and the published one is
the smallest.** Four routes to nominally the same quantity:

| Route | Value |
|---|---:|
| `prime_dollars_M` summed over all tier-A ledger rows | $90.8B |
| `prime_dollars_M` summed over `cedar_publishable_identifiers.csv` | **$42.2B** |
| `prime_contracts.csv` tier-A rows, summed raw | $82.8B |
| the same, deduplicated on `(contract_number, fiscal_year, awardee_uei)` | $79.4B |
| the same, restricted to the 699 publishable UEIs | $34.6B |

Two of these are now explained and one is not. The **$42.6B "publishable prime dollars"**
in `docs/handoffs/STATE_OF_BUILD.md` is route 2 — the sum of `prime_dollars_M` over the 1,577-row
publishable set, and it is *not* double counting: the 878 CAGE rows carry $0 and all
$42.2B sits on the 699 UEI rows (687 of them non-zero). Good.

What is unexplained is that recomputing the same quantity **from the contract records
themselves**, through those same 699 UEIs, gives **$34.6B** — an 18% shortfall.
`prime_dollars_M` is therefore carried from a different source than `prime_contracts.csv`
(most likely the BGOV totals) and the two have never been reconciled. **Designate one
definition, publish the reconciliation, and quote only the recomputable figure.** A
subscriber who sums the export and gets a different number than the marketing page is the
fastest available way to lose the "never falsely attribute" reputation the whole product
rests on — and this is the one place in the build where that is currently possible.

**Finding 4 — there is a live false attribution in a launch-tier dataset, and I found it
by accident.** Dataset 4 (Lobbying, Portal tier) attributes **340 filings and $28.7M of
lobbying spend from SALT RIVER PROJECT to the Salt River Pima-Maricopa Indian Community**
(`TRBF-SRPMCP-00`), on a `medium` confidence token match against the alias `river salt`.
Salt River Project Agricultural Improvement and Power District is an Arizona public power
utility and a political subdivision of the State of Arizona. It is not a tribe, it is not
tribally owned, and it is the single largest "Native" lobbying client in the file.

It is not alone. The largest medium-confidence attributions in the dataset:

| Client as filed | Attributed to | Alias matched | Spend |
|---|---|---|---:|
| **SALT RIVER PROJECT** | Salt River [Pima-Maricopa] | `river salt` | **$28.71M** |
| SANTA YNEZ BAND OF CHUMASH INDIANS | Santa Ynez | `santa ynez` | $5.75M — correct |
| FOREST COUNTY POTAWATOMI … LEGAL DEPT | Forest County | full name | $4.61M — correct |
| HO-CHUNK NATION LEGISLATURE | Ho-Chunk | `chunk ho` | $3.51M — correct |
| **COEUR D'ALENE MINES** | Coeur d'Alene | `coeur dalene` | **$2.96M** |
| **CITY OF SANTA ROSA** | Santa Rosa | `rosa santa` | **$2.31M** |
| **BRISTOL BAY ECONOMIC DEVELOPMENT CORP** | Bristol Bay Native Corporation | `bay bristol corp` | **$2.00M** |

A mining company, a California city, a state power district, and a CDQ group conflated
with the ANC that shares its watershed name. That is roughly **$36M of false or
questionable attribution in the top twelve rows alone**. Across the file, medium-confidence
matches carry **$97.6M of $725.2M (13%)** of all attributed lobbying spend.

This is the exact failure the project's own name-trap register was built to prevent —
`creek`, `cherokee`, `colorado`, `ojibwe` are all recorded there — and it is sitting in a
$499-tier dataset. **Nothing in Dataset 4 should publish at `medium` confidence.** The
remedy is the one the project already uses: demote every medium match to tier B, queue the
distinct client names for rulings, and publish only what survives. It is a few hundred
names, not 4,055 filings. Fix this before anything else in section 5, because a competitor
who finds it first can dismiss the entire "never falsely attribute" premise with one
screenshot.

**Finding 5 — coverage limits that constrain every product claim below.** These are
documented and not negotiable:

- Deals: 2000–2026, but **2–7 rows/year 2000–2009** against 183 in 2022. And of ~~790~~
  **921** rows, **594 are "Grant / public financing" versus 120 acquisitions** — the year curve
  tracks when TBCP and HUD ran competitive rounds, not deal activity.
  *(Denominator corrected 2026-08-26. 790 counts only the nine `deals_*_additions.csv`
  files and silently drops the 131 rows that come from the two root ledgers
  `deals_2026_ytd.csv` and `deals_historical_2020_2025.csv`. `deals_classified.csv` holds
  921. `docs/FACT_CHECK_2026-08-06.md` finding B-1 identified this exact error the same
  week; it went on being repeated because nothing linked the two documents.
  The 594/120 split is a real feature of the additions and the shape of the point stands.)*
- Per-entity federal assistance **cannot begin before FY2007**: FAADS carries a recipient
  identifier on 0.0% of rows FY2001–06, confirmed through two independent routes. Pre-2007
  supports programme-level totals only.

  *Worth knowing that this is Cedar Press's own finding and cannot be cited to anyone
  else.* An independent sweep of USAspending's About-the-Data corpus, the Treasury
  guidance pages and four GAO reports (GAO-18-138, GAO-20-75, GAO-22-104702, GAO-10-365)
  **found no authoritative statement of a pre-FY2007 recipient-identifier gap**. What is
  documented is adjacent: Advanced Search begins FY2008 while Custom Award Data Download
  reaches FY2001, OMB has changed which elements are required since 2010, and Census's
  FAADS page now redirects into usaspending.gov. So the limit is real and measured here,
  but the citation is Cedar Press's own build log. Treat that as an asset — it is a
  documented fact about federal data that the federal data does not document — and cite
  it as a Cedar Press finding rather than implying an external source.
- ~~Prime contracting **ends FY2022**; BGOV-sourced history ends 2020. A four-to-six year
  hole at the recent end, which is the end buyers care about.~~ **FALSE as of the archive
  backfill — see the correction block at the head of this document, 2026-08-26.** Prime
  runs **FY2000–FY2026**, 1,217,768 rows, and FY2026 alone is 61,813.
- Subcontracting **cannot reach 2000** (FSRS began under FFATA in 2010). ~~and the promoted
  file is 998 rows; the 345,090-row pull is staged, not promoted.~~ **FALSE — the promoted
  file is 63,548 rows and promotion completed 2026-08-06. See the correction block,
  2026-08-26.**
- Gaming openings: 618 facilities carry an `open_date`, but only **7 fall in 2019–2022**
  and the inherited Casino City column effectively stops at 2018. Two thirds of the ISO
  dates are placeholders wearing day precision (150 on day 31, 148 on day 15).
- Gaming revenue: **126 of 592 observations (21%) are reported revenue**; the rest are
  derived or inverted from compact rates.
- Compact term recall **53%**; the BIA index is defective on 61 of 1,189 rows at source.
- Federal Actions: only **14.2%** of the 156,452-row corpus names a tribal term in its own
  title or abstract. Only the 2,794 named-bucket rows are 82–100% precise.

---

## 1. What BGOV and PitchBook do that Cedar Press does not

*Ranked by cost to close, cheapest first. Cost is engineering plus editorial, not licence fees.*

### What each of them actually sells

**BGOV sells one all-inclusive per-user subscription to a single platform.** There is no
module-by-module SKU list; BGOV markets that as the differentiator, with a comparison page
carrying a row literally labelled "All-inclusive pricing — Subscriptions include AI tools,
source materials, dockets, news," checked for BGOV and X'd for competitors **[verified,
about.bgov.com/bloomberg-government-vs-competitors-see-the-difference/]**. The modules are
Public Affairs Intelligence, News & Analysis, Federal & State Tracking (+ Transcripts),
Directories, Workflow Tools, Federal Budget & Spending, Elections Intelligence, and AI
Solutions. Inside Federal Budget & Spending: Federal Funding Flow, Appropriations Tracker,
Line Items Table, Agency Spend Table, Historical Spend, Upcoming Opportunities. Claimed
coverage: "3.9M+ solicitations, 47M+ task orders, and 15M+ contracts" **[verified]**. The
only separately sold thing is **Data Licensing** — a bulk/feed product whose format,
datasets, terms and price are all undisclosed **[unknown]**. Report SKUs (BGOV200, Market
Profiles, Top-Performing Lobbying Firms) are lead-gen, not priced.

**PitchBook sells the named licensed seat.** Morningstar's FY2025 10-K states it: "Pricing
for the PitchBook platform is primarily based on the number of licensed users"
**[verified, SEC]**. Free with every seat: the Excel, PowerPoint and Chrome plugins.
Explicitly labelled "Paid add-ons" on `/products`: **Direct Data** (API + scheduled
`.dat`/`.csv`/Parquet feed), **CRM Integration**, and **Lumonic**. Their own FAQ gives the
price architecture in one sentence: those add-ons are "priced according to seats and firm
type" **[verified]**.

The instructive contrast is the lock-in mechanism. **BGOV's is habit** — alerts, trackers,
notes and tags, daily newsletters, and adjacency to a Bloomberg Terminal entitlement
(`BGOV<GO>`). It markets **no Excel plugin, no CRM sync, no Salesforce listing** anywhere.
**PitchBook's is embedded dependency** — live-linked Excel cells that auto-refresh inside
customer LBO models, PowerPoint chained to those cells so client decks silently depend on
the subscription, and CRM records carrying PitchBook entity IDs. Cancel PitchBook and your
models break. Cancel BGOV and you stop getting emails. PitchBook's renewal rate is ~103%
**[verified, 10-K]**.

And PitchBook's real moat is contractual, not technical. Terms of Use §3.2 permits derived
work only if it "has no independent commercial value and is not separately marketable by
PitchBook" and is "not published to more than 500 individuals"; §3.3 caps downloads at
"the amount of Content authorized in the Order only" and forbids compiling "more than an
insubstantial portion of the PitchBook database"; §4.1 forbids use toward a "Competitive
Product" *and* competitive analysis of PitchBook itself **[verified,
pitchbook.com/terms-of-use]**. Stanford's academic licence is capped at 10 Excel rows per
day **[verified, libguides.stanford.edu]**. Because the quantity caps live in a private
Order Form, PitchBook sustains roughly 2× price dispersion between comparable buyers.

### The ranked gap list

**Cheap — weeks, and mostly already latent in the build**

1. **Saved searches, watchlists and alerts as first-class saved objects.** BGOV's entire
   habit loop is alerts + trackers; PitchBook sells saved dynamic searches, static lists
   and custom alerts on every entity type. Cedar Press has the streams (24 FR
   documents/week, 25 lobbying filings/week) and no saved object. This is the cheapest
   thing on the list and the largest behavioural gap.
2. **Exportable screener results carrying a citation string.** PitchBook requires "Source:
   PitchBook Data, Inc." on derived work; Cedar Press should *want* that — an export that
   carries its tier composition and a citation is a marketing asset, not a restriction.
3. **Published, crawlable profile pages with a visible schema.** PitchBook publishes
   ~1.46M SEO teaser profiles — field names visible, values gated. It is simultaneously
   the product surface and the entire top-of-funnel. Cedar Press has 866 entities; 866
   public teaser pages is a weekend of work and the only distribution channel it can
   afford.
4. **Peer-set benchmarking with quartile rank and an as-of date.** PitchBook's fund
   Benchmark block is exactly this. Cedar Press's compact terms (413 revenue-share bases,
   166 rates, 208 exclusivity provisions) support the same primitive, and it is the single
   feature a tribe entering compact renegotiation would pay for unprompted.

**Moderate — a quarter of engineering**

5. **A directory/people layer.** BGOV's most distinctive field claim is a searchable
   database of federal decision-makers "with the opportunities they manage and their
   contact information… You can export lists by agency, name or job title" **[verified]**.
   Cedar Press has no people at all. It does hold 429 lobbying registrants, bill sponsors
   and cosponsors, and BIA/IHS awarding offices — the raw material for a *Native-facing*
   directory, which is a different and smaller product than BGOV's.
6. **An Excel add-in with live links.** This is PitchBook's hardest lock-in and it is a
   real engineering project, but it is the difference between a data product and a
   download. Note the asymmetry: for Cedar Press's buyers (tribal finance offices, law
   firms), Excel is the working surface, not a nice-to-have.
7. **A Direct Data equivalent — API plus scheduled feed.** Both incumbents sell one;
   BGOV's is its only separate SKU. Premature until the entity keys are populated, but it
   is the natural Grove-tier upsell and it is how a data product becomes infrastructure.

**Expensive — and two of these should probably never be closed**

8. **Recency and completeness of the contracting record.** BGOV covers "every transaction,
   modification, and task order that has been reported on a contract," continuously
   refreshed, and handles FPDS's five-year retroactive restatements. ~~Cedar Press ends
   FY2022. This is the single largest substantive gap and the only one on the list that
   is *table stakes* rather than differentiation — see addition 2 in section 5.~~
   **STALE 2026-08-26 — Cedar Press now runs FY2000–FY2026 (1,217,768 rows). This gap is
   CLOSED; see the correction block at the head of this file. What survives of the item is
   the narrower point that BGOV refreshes continuously and handles FPDS's retroactive
   restatements, and Cedar Press refreshes on a cadence — a vintage discipline question,
   not a coverage hole.**
9. **Forward-looking pipeline: solicitations, forecasts, recompete windows.** BGOV sells
   "Upcoming Opportunities"; GovWin's whole thesis is pre-RFP intelligence. Cedar Press
   has no forward-looking data of any kind and closing this means a new source and
   permanent operations. **Recommend not closing it** — it is a different business
   (business development tooling) with a different buyer and a well-defended incumbent.
10. **Adjacent content breadth: news, hearing transcripts, AI summarisation, congressional
    tracking, 35,000+ news sources.** BGOV's bulk. **Recommend not closing it.** Competing
    on breadth against Bloomberg is unwinnable, and the ten Cedar Press datasets are
    already broader *within Indian Country* than anything BGOV holds.

### The nearest thing to a direct competitor is HigherGov, and it is worth studying closely

HigherGov is not in the original brief but it is the product Cedar Press will actually be
compared against — same price points, same buyer, and an entity profile that is a genuine
peer to the one specced in section 3. Its Awardee page carries, verbatim from the live
site: name, **UEI, CAGE**, awardee type with child count (`Parent (366 children)`),
alternative names, ownership status, SBA certifications, self-certifications, entity
structure, registration and **expiration** dates, employee band, per-NAICS size flag,
GSA schedules with ceiling and obligated dollars and downloadable price lists, **teaming
partners** (disclosed sub↔prime relationships), **mentor-protégé** relationships, **joint
ventures**, top contracting officers buying from the awardee, and **federal contracts
recompeting soon**. Its API exposes 39 fields on the awardee object.

Three of its design decisions are worth copying and one is worth avoiding:

- **Copy the meter.** HigherGov sells a **seat cap plus an export-row cap per search**
  (1,000 / 20,000 / 100,000), and **explicitly refuses to meter alerts or saved searches
  on any tier**. The API is included free at every tier at 10,000 records/month. Metering
  throughput rather than access is the right shape for Cedar Press too — the thing worth
  charging for is bulk extraction of the crosswalk, not the ability to look at a page.
- **Copy the lock-in primitive.** Every HigherGov UI search carries a `searchID`, and that
  same token is the `search_id` parameter on the API. **A customer's integration is
  parameterised by saved searches built inside their UI**, so the query cannot be
  reproduced outside the product. That is elegant, cheap, and far more durable than an
  export restriction.
- **Copy the agent distribution play.** HigherGov ships a remote MCP server at
  `highergov.com/mcp/` with documented setup for Claude, the OpenAI Responses API and the
  Gemini CLI, drawing on the same 10K/month pool. For a small publisher this is the
  cheapest distribution channel that exists in 2026, and Cedar Press's data — small,
  entity-keyed, heavily documented — is unusually well shaped for it.
- **Avoid their documentation drift.** HigherGov's pricing page and its docs contradict
  each other on four features, and the docs reference a "Leader plan" 14 times that the
  pricing page no longer sells. A $500 Starter buyer does not get what the grid shows.
  Cedar Press's whole premise is that its documentation is trustworthy; this is a
  reputational failure mode to design against from day one.

**One genuine open gap in both markets, noted for completeness:** recompete and expiration
are implemented everywhere as *filters* (`Recompete Opportunities`, `Date Potential End`,
`8(a) Exit Date`, `Vulnerable 8(a)/SB/SDVOSB`) and **nowhere as a first-class event**.
"This contract expires in 180 days and here is the incumbent" as an alert is unclaimed.
~~Cedar Press cannot build it today — the prime series ends FY2022 and there is no
solicitation feed —~~ **STALE 2026-08-26: the prime series now reaches FY2026, so half of
this objection is gone. The remaining blocker is the absence of a solicitation feed, which
is real.** It is the single most valuable thing addition 2 would unlock, and
worth recording as a target rather than discovering later.

### The finding that matters most from this research

**BGOV has no tribal-specific product, module, directory or coverage area.** Its
directories cover members of Congress, congressional staffers and committees, federal
agency leadership, state legislators and governors across all 50 states and DC. Tribal
governments, tribal legislatures and tribal officials appear nowhere; the
associations-and-nonprofits persona page contains no reference to tribes at all
**[verified, about.bgov.com solutions and directory pages]**.

Tribal and ANC entities exist in BGOV **only as FPDS-derived vendors**. Its own flagship
BGOV200 ranking places nine Alaska Native Corporations in the top 200 federal contractors
— Arctic Slope #54 ($1.88B), Bristol Bay #94, Chenega #101, Calista #103, Koniag #133,
Bering Straits #149, Afognak #174, Ukpeaġvik Iñupiat #188, Cook Inlet Region #200
**[verified, 2023 BGOV200 PDF]**. And BGOV's 8(a) analysis capability is inherited from
FPDS set-aside flags, not built.

So the incumbent that Cedar Press is being measured against **ranks Afognak Native
Corporation at #174 by the contract dollars its subsidiaries win, and cannot tell you that
Alutiiq Pacific is one of them.** BGOV sees the parent because ASRC and Afognak are
themselves registered entities; it does not maintain the ownership crosswalk that connects
the operating subsidiaries. That is the white space, stated as narrowly as the evidence
supports.

One further structural note: BGOV appears to be **de-emphasising standalone federal
contracting**. There is no longer a `/products/government-contracting/` page; contracting
now sits folded inside Federal Budget & Spending, the last BGOV200 edition traceable is the
12th annual (2023, FY2022 data), and Bloomberg Industry Group's June 2026 Regology
acquisition was paired with Bloomberg *Law*, not BGOV **[verified,
about.bgov.com/insights/company-news/bloomberg-government-regology/]**. The incumbent is
drifting toward policy and compliance and away from GovCon. That is favourable timing.

---

## 2. What Cedar Press can do that they structurally cannot

### The crosswalk is a moat, not a feature. Here is the measurement.

Take the 1,699 tier-A links. For each, compare the distinctive tokens of the vendor's
`legal_business_name` against the distinctive tokens of the Native entity's
`canonical_name` (stopwords removed: *tribe, nation, band, indian, pueblo, rancheria,
village, corporation, inc, llc, native, alaska, enterprises, holdings, group*, etc.).

```
tier-A links total          1,705
name tokens overlap           904  (a good name-matcher could plausibly find these)
NO token overlap              801  (47% — no name-based method can ever find these)
```

Now weight by money. Tier-A prime contract obligations, deduplicated on
`(contract_number, fiscal_year, awardee_uei)`:

```
total tier-A obligations                                   $79.4B
of which, via UEIs whose legal name shares NOTHING
with the owning entity's name                              $53.0B  = 66.7%
```

**Two thirds of the attributable federal contracting dollars in Indian Country flow
through vendors whose names do not contain the owner's name.** Verified in the ledger:
Afognak Native Corporation carries 9 tier-A links, every one an `elijah_ruling_redirect`,
and every one named *Alutiiq* — Alutiiq Pacific LLC (`CKB4JDLXQ9M3`), Alutiiq Global
Solutions, Alutiiq Information Management, Alutiiq 3SG, Alutiiq Diversified Services and
four more. Nothing in any federal record connects the string "Alutiiq Pacific" to the
string "Afognak." Wincomp LLC dba All Native does not say Ho-Chunk. Every competitor's
attribution is a name match or a self-certification flag, and both miss this money by
construction.

The error runs the other way too, and it is worse. `docs/CROSS_DATASET_LEARNING.md`
records name traps that were each paid for once: **Cherokee General Corp is Doyon-owned,
not Cherokee Nation**; Colorado Professional Resources is not Colorado River; Ojibwe
Hazardous Abatement is not Mille Lacs; Absentee Shawnee and Shawnee Tribe are three
distinct governments that a matcher collapsed into one; Oneida NY and Oneida WI had
$716M mis-split between them. A name-matching competitor does not merely under-report —
it assigns one nation's revenue to another. For a customer who is a tribal government,
that is not a data-quality issue, it is a reason to stop using the product.

### Why the incumbents cannot simply buy or build it

1. **The signal is absent from their sources, not merely unextracted.** FPDS has
   `immediate_parent_uei` and `domestic_parent_uei` populated on **0 of 2,279,891 rows**
   in this project's extract. There is no corporate tree to read. USAspending assistance
   carries no EIN and no CAGE at all. A vendor with the world's best pipeline still has
   nothing to run it on.

   **USAspending's own recipient identity logic makes this concrete.** Its ETL source
   computes `recipient_hash` as an MD5 of `'uei-'||UEI`, falling back to `'duns-'||DUNS`,
   falling back to `'name-'||UPPER(legal_name)`. **The only normalisation is `UPPER()`** —
   no punctuation stripping, no fuzzy or probabilistic matching, no crosswalk of any kind.
   "ACME CORP" and "ACME CORP." are two permanently distinct recipients. The consequence
   is visible in their live API: the Lockheed Martin parent profile carries **26
   `alternate_names`**, including Sikorsky, Zeta Associates, Derco Aerospace, and three
   different spellings of LifePort LLC (`LIFEPORT   LLC`, `LIFEPORT , LLC`, `LIFEPORT
   LLC`) — distinct legal entities and typographic variants collapsed onto one UEI because
   agencies typed different strings against the same registration — while
   `/recipient/children/` for that UEI returns **216 children**. Parent-child structure
   comes from SAM's *current self-reported* `ultimate_parent_uei`, not from the structure
   at time of award, and an entity that lapses out of SAM loses the linkage entirely.

   That is the state of the art at the authoritative free source, and every commercial
   product downstream inherits it. **Identity resolution is the unsolved problem in this
   entire market**, not just in Indian Country. Cedar Press's crosswalk is a solved
   instance of it for one vertical.
2. **Self-certification undercounts and cannot be corrected downstream.** FPDS
   socioeconomic flags found **241 contracting tribes against 588 recognized entities**.
   A firm that never checked the box is invisible to a flag-based method forever; only
   an independently built ownership crosswalk recovers it.

   The dollar version of this is the single most persuasive number in the file. Tier-A
   prime obligations by set-aside, deduplicated:

   | Set-aside | $B | share |
   |---|---:|---:|
   | 8(a) | 27.57 | 34.7% |
   | **None reported** | **19.96** | **25.1%** |
   | Other | 16.47 | 20.7% |
   | Small Business | 14.19 | 17.9% |
   | HUBZone | 0.80 | 1.0% |
   | **Buy Indian** | **0.24** | **0.3%** |
   | **Indian Business** | **0.19** | **0.2%** |

   **The two Native-specific set-asides together account for 0.5% of the dollars.** A
   product built on "filter FPDS to the Indian set-asides" — which is what every
   off-the-shelf approach reduces to — would see $0.43B of a $79.4B universe. Even 8(a),
   the broadest proxy, sees a third, and 8(a) admits individually-owned firms that are not
   entity revenue at all. A quarter of the money arrives with **no set-aside reported**,
   which is to say through full and open competition, which is to say invisible to every
   method except ownership attribution.

   The assistance side gives the same answer independently. Of **$107.5B** in attributed
   federal assistance (consistent with the regression-tested $107,047,741,074.94 do-file
   figure), only **51.9% flows through a programme whose CFDA title contains a tribal
   word**. The other **$51.7B** arrives through Coronavirus State and Local Fiscal
   Recovery Funds ($18.5B), the Coronavirus Relief Fund ($7.2B), Head Start ($2.9B),
   Highway Planning and Construction ($2.9B), CCDBG, TANF and Performance Partnership
   Grants. Filter the federal money to programmes with "Indian" in the name and you lose
   half of it. Two independent datasets, two different mechanisms, the same conclusion:
   **the Native economy is not identifiable from the labels the federal government
   attaches to its own transactions.**
3. **The distinction that matters is not in any database.** *Tribally owned* versus
   *individually Native-owned* is the difference between an entity's revenue and a
   citizen's revenue. `hci_analysis.do` carries dozens of per-UEI drops — "owned by
   individual Cherokees" — each with a citation to cage.dla.mil, a GAO decision, an
   OpenCorporates record or an archived site. That work is adjudication, not extraction.
   It is also the reason 8(a) status proves nothing: HALOA Construction is 8(a) and
   family-owned, which is why script 06's 36 "NHO-verified" firms collapsed to the 12
   Elijah actually ruled.
4. **Ownership changes and the records do not.** FPDS does not update retroactively when
   a company is sold, and no reliable corporate-hierarchy-over-time source exists — a
   point Elijah established in his own correspondence with Dippel. So an ownership
   crosswalk is only correct *as of a date*, and the only way to make it time-aware is to
   maintain an M&A event stream. Cedar Press has 98 dated ownership events; the incumbents
   have none for this universe, because covering it is not worth their while.
5. **The economics are wrong for them.** BGOV and PitchBook are horizontal. The marginal
   revenue from correctly attributing 866 Native entities does not justify a manual
   adjudication programme at any staffing level they would approve. This is the classic
   defensible-niche condition: the work is high-effort, low-glamour, and only valuable to
   someone who already cares.

### The honest limit on the moat claim

The moat is real and it is currently **31% deployed**. 265 of 866 entities have a
publishable link; 878 of the best links do not reach an entity ID at all. The moat also
does not extend to *coverage* — where BGOV has every federal contract through last week,
~~Cedar Press has through FY2022~~ **Cedar Press has through FY2026 as of the 2026-08-12
backfill; the residual difference is refresh cadence and FPDS restatement handling, not
years.** The claim to make is narrow and true: **nobody else can
tell you whose it is.** Not: nobody else has the data.

### The second structural asset: the jurisprudence model

Every attribution carries a tier, a rationale, an authority and an audit trail, and the
authority order is explicit (Elijah's hand-checked work outranks any automated method;
on conflict the automated claim is demoted). Exclusions are typed — *ownership* exclusions
block globally, *scope* exclusions must not, and conflating them once falsely voided a
$302.5M Doyon attribution. No incumbent publishes a per-record provenance model of this
shape, because no incumbent's customers ask them to defend an individual row in front of
a tribal council or a federal grant reviewer. Cedar Press's customers will. That is a
differentiator with a buyer attached.

---

## 3. The product surface

### 3.1 The entity profile page

One page per spine entity, at a stable URL keyed on `tribe_id`
(`/entity/TRBF-CHKNAT-00`). This is the atomic unit of the product; everything else is a
route into it.

**Header.** Canonical name · entity class (with the taxonomy spelled out, e.g. "Alaska
Native Village Corporation") · state · BIA region · self-governance status · aliases ·
`cedar_entity_id`. A **coverage strip** showing, per dataset, observed / in-window /
not-in-window — read straight from `entity_year_coverage.csv`. A profile that silently
shows a blank where a source window does not reach is a lie by omission; the strip is
what makes the page trustworthy.

**Identity panel** — *the differentiated section, put it above the fold.*
Every UEI, CAGE and EIN attributed to this entity, each row carrying:
`identifier_type · identifier · legal_business_name · attribution_method ·
confidence_tier · tier_rationale · evidence_url · verified_date`. Tier A rows render
normally; tier B rows render greyed with "not yet verified"; tier C never appears; tier X
appears only in an internal view. Counts come from the spine's own
`n_uei_tierA / n_uei_tierB / n_cage / n_ein`.
**No competitor has this panel. It should be the first thing a visitor sees.**

One design constraint, measured: `tier_rationale` and `is_authority` are populated on
**100%** of tier-A rows, but `evidence_url` and `verified_date` on only **819 of 1,705
(48%)** — the 868 BGOV-crosswalk rows carry the rationale "Elijah's manual BGOV
tribe→vendor crosswalk" and no URL. The panel must therefore render *rationale plus
authority* as the primary evidence and treat the URL as an optional enrichment. Do not
build a UI that implies a missing link means missing verification; that would misdescribe
the project's own best work, which is hand adjudication rather than link collection.

**Ownership timeline.** Dated acquisitions, divestitures and reorganisations from
`ownership_events.csv` — `effective_date · direction · counterparty · asset_class ·
announced_value_usd · date_basis · source_url`. 98 events today. Show `date_basis`
inline: audited financial statements outrank newsroom releases on date and value, and
newsroom dates ran 2–16 days late in every ANCSA case checked. Where
`date_usable_for_attribution` is false, say so on the row. Source quality here is
genuinely high and worth surfacing: of 533 indexed deal parties, **491 have a primary
source of kind `AUTHORITY`** (SEC filing, audited ANCSA statement, `.gov` notice) and 38
`AUTHORITY_OR_PARTY`, against a single wire item. Displaying the source kind on each row
is a stronger trust signal than any volume claim the ledger can make.

**Federal contracting (prime).** Obligations by fiscal year from
`prime_contracts_entity_year.csv`, ~~with an explicit "series ends FY2022" terminator on
the chart~~ **— STALE 2026-08-26: the series now runs to FY2026, so the terminator should
state the vintage date of the last pull rather than a truncation year. Note that
`prime_contracts_entity_year.csv` is itself a derived rollup and may predate the backfill;
re-derive it before charting.** Below it: top awarding agencies, set-aside mix, sector mix, competition mix,
place-of-performance states. Award-level table with `contract_number · fiscal_year ·
awardee_name · awardee_uei · setaside · funding_agency · total_obligations`, filterable,
tier-A rows only by default with a toggle to reveal tier-B under a warning banner.

**Federal assistance.** Obligations by fiscal year, ~~FY2007–2023~~ **FY2007–FY2026
(corrected 2026-08-26; the file carries 684,923 rows and reaches FY2026)**, with the floor stated on
the axis, not in a footnote. Top CFDA programmes (Tribal Self-Governance, Indian
Self-Determination, IHS compacts, CCDF, Pell, FDPIR are the actual volume leaders).
Awarding agency and sub-agency mix. **Programme-level pre-2007 totals may appear in a
separate, labelled block; per-entity pre-2007 must never render.**

**Subcontracting, both directions.** As-sub (revenue the prime data misses entirely) and
as-prime (who this entity hires — direct input-output linkage evidence). Every dollar
figure must pass `subaward_exceeds_prime_flag`; 1.7% of raw rows report a subaward larger
than its own prime award, totalling $68.7B, and among Native-linked rows 17 rows carry
54.6% of the dollars. Show `subaward_to_prime_ratio` on any row above 1.

**Influence.** Lobbying spend by year, registrants retained, self-filed versus retained,
top issue codes, top government entities lobbied, and the filings themselves with
`filing_url`. 27,796 disclosures across 300 entities, all carrying a match confidence —
render `medium` confidence distinctly from `high` (23,741 high, 4,055 medium). Measured
facets: issue codes IND 18,403 · BUD 3,992 · **GAM 2,450** · NAT 2,340 · TAX 1,692;
government entities House 19,568 · Senate 19,542 · DOI 9,757 · **BIA 5,099**. Only **305
of 27,796 filings are self-filed** — Native entities overwhelmingly retain registrants,
so "who lobbies for whom" is a real and populated graph, and it is the closest thing in
the build to BGOV's influence chain. **429 distinct registrants** appear; the top ten are
Sonosky Chambers (1,858 filings), Hobbs Straus (1,603), Holland & Knight (1,298), Ietan
Consulting (800), PACE, Spirit Rock, Akin Gump, Peebles Kidder, Mapetsi and Sense
Incorporated. `lobbying_client_attribution.csv` carries **261 tier-A clients and 197
ruled-out clients** against **$236.5M** of attributed spend — the exclusions are as much
of the asset as the inclusions.

**Gaming** (Grove). The underrated asset here is `gaming_facility_metrics.csv`: **65,223
dated observations across 434 facilities, 2001–2023, median 126 observations per
facility** — a capacity panel (machines, tables, employees, hotel rooms, gaming square
feet), not a snapshot. A per-facility capacity trend line is a chart no free source
produces. But note the composition honestly: **64,181 of the 65,223 observations are
capacity; only 592 are gaming revenue and 450 are payments to government.** This is a
capacity panel that occasionally sees money, not a revenue database, and it must never be
sold as the latter.

Facilities with `observation_status` and `property_status` shown
before any capacity number, because 1,108 capacity observations are proposal- or
construction-stage. `open_date` displayed at its true precision using
`open_date_precision` and the `open_date_not_before` / `open_date_not_after` interval, and
suppressed entirely where `open_date_postdates_observation = 1`. Revenue observations
labelled with `value_basis`; only the 21% that are reported revenue may be called revenue.

**Compacts** (Grove). Versions, effective dates, term ends, renewal provisions, status,
FR citation, and the extracted terms. The 1,311 extracted terms are the commercially
sharpest content in the whole product — `revenue_share_base` 413 · `game_scope` 235 ·
`exclusivity` 208 · `revenue_share_rate` 166 · `dispute_provision` 118 · `local_share` 87
· `machine_cap` 63 · `tier_structure` 21. A comparable-terms view across compacts (what
rate did neighbouring states settle at, what exclusivity did they grant) is the one
screener a gaming banker or a tribe entering renegotiation would pay for on its own.
Ship it with "term recall is 53%; an absent term is
unextracted, not absent from the compact" stated on the panel, and
`bia_tribes_column_conflict` surfaced on the 61 defective rows.

**Federal actions.** Federal Register documents naming this entity, filtered to
`title_abstract_term_hit`, with document number, type, agency, publication date, comment
URL and a link to the FR page.

**Bills** (Grove). Bills affecting this entity, sponsor, cosponsor count, latest action,
outcome, and roll-call positions where they exist. **Blocked until `affected_entities`
is populated — today it is empty on all 3,037 rows.** The tractable subset is visible in
the data: **484 bills are already typed `bill_scope = tribe-specific`**, and a
tribe-specific bill names its tribe in the title. Extracting entities from those 484 gets
a working bills panel without touching the 2,417 general-scope bills. Outcomes for
context: 2,209 died in committee, 229 enacted, 170 passed one chamber; 283 carry a roll
call.

**Provenance footer.** Build date, source files, and a "how this page was attributed"
link into the codebook. Non-negotiable; it is the product.

**Build readiness of the profile page, measured.** This is what a profile would render
today if it were built this afternoon:

| Panel | Buildable now? | Entities covered |
|---|---|---|
| Header + coverage strip | yes | 866 |
| Identity panel | yes, but on 827 of 1,705 tier-A links | **265** |
| Federal contracting | yes, ~~ends FY2022~~ **FY2000–FY2026** | 413 (424 with any tier) · **498 on the current file** |
| Federal assistance | yes, ~~FY2007–2023~~ **FY2007–FY2026** | 578 |
| Influence / lobbying | yes | 300 |
| Subcontracting | ~~thin — promoted file is 998 rows~~ **promoted, 63,548 rows, 99.9% carrying a Native entity on one side or the other** | ~~**42**~~ **re-measure** |

*Table corrected 2026-08-26 on the two coverage cells. The entity-coverage column is a
2026-08-06 measurement and was not re-derived; treat it as a floor. "Five of eleven panels
render" was true on 08-06 and understates the position now.*
| Ownership timeline | **needs the join** (94 of 98 resolvable today) | 0 |
| Gaming | **needs the join** (31% name-match today) | 0 |
| Compacts | **needs the join** (89% name-match today) | 0 |
| Bills | **needs extraction** (484 tribe-specific are the tractable subset) | 0 |
| Federal actions | **needs the join** | 0 |

Five of eleven panels render. That is the launch question in one table.

~~**The demo year is FY2022**~~ **RE-DERIVE, 2026-08-26.** The reasoning was sound — pick
the last year in which prime, assistance and lobbying are *all* in source window — but the
windows moved. Prime now reaches FY2026 and assistance FY2007–FY2026, so FY2022 is no
longer the binding year and the argument's conclusion no longer follows from its premise.
The 08-06 measurement is kept for reference: FY2022 carried **609 entity rows — 574 with
assistance, 232 with prime, 197 with lobbying**. Re-run that count across the current
windows and pick the year the data now supports. The underlying discipline stands: state
the year on every screenshot, so a vintage reads as disclosed rather than as a hole a
visitor discovers.

### 3.2 The screener

Query the 866-entity spine, return entities, save the query, export it, alert on it.
Facets, with the values that actually exist in the data:

| Facet | Values available |
|---|---|
| Entity class | the 9 spine classes |
| State · BIA region · self-governance | direct from the spine |
| Has tier-A identifier | yes / no (265 vs 601 — brutal but honest) |
| Identifier count | `n_uei_tierA`, `n_cage`, `n_ein` ranges |
| Prime obligations | range, per fiscal year, FY2000–2022 |
| Set-aside | 8(a) 176,859 · Small Business 97,093 · HUBZone 10,227 · **Indian Business 7,245** · **Buy Indian 6,927** · None reported 223,603 |
| Awarding agency | DoD 355,610 · IHS 28,636 · VA 25,369 · PBS 23,378 · FAS 20,913 · State 16,359 · **BIA 14,422** · Forest Service 11,245 |
| Sector | Professional & Business Services 227,364 · Construction 144,743 · Manufacturing 127,142 · … |
| Extent competed | six FPDS values, including 198,301 "not available for competition" |
| Place of performance | state |
| Assistance | CFDA programme, awarding agency, ~~FY2007–2023~~ **FY2007–FY2026** range |
| Lobbying | spend range, registrant, issue code, government entity lobbied |
| Ownership activity | acquired / divested in a window; counterparty; asset class |
| Gaming (Grove) | state, facility count, `observation_status`, compact status |
| Coverage | "components observed", so a user can screen to entities where a comparison is legitimate |

Two screener rules the incumbents do not have and should be Cedar Press signatures:

- **Every result set carries its own tier composition.** A screener that returns 40
  entities says "38 tier A, 2 tier B" at the top, and the export carries the tier column.
- **Only 2011–2022 has all four panel components in window.** Any cross-component ratio
  (lobbying per contract dollar, assistance per capita) computed outside that band
  compares a measured quantity to an unmeasured one. The screener must refuse the ratio,
  not caveat it.

### 3.3 Alerts

Alerts are the recurring reason to keep paying. Measured volumes, so the cadence is real:

| Alert | Trigger | Observed rate |
|---|---|---|
| **Federal action naming a watched entity** | new FR document, `title_abstract_term_hit`, matching a saved entity or term | ~**24/week** across all entities (1,304 in 2024, 1,256 in 2025) |
| **New lobbying filing** | LDA filing where the client resolves to a watched entity | ~**25/week** (1,269 in 2024, 1,377 in 2025) |
| **Ownership change** | new row in `ownership_events` involving a watched entity, either direction | thin — 98 events total; that is precisely why it is valuable |
| **New identifier attributed** | a UEI/CAGE reaches tier A on a watched entity | **This is the alert nobody else can send.** "A firm you have never heard of is now confirmed to be owned by an entity on your list." |
| **Attribution changed or withdrawn** | a ruling moves a link between tiers, or to X | measured churn between the 2026-08-05 and 2026-08-06 builds: **78 tier changes on 18,357 shared links, of which 71 were A→C demotions**; 860 links added, 801 removed |
| **New compact or compact amendment** (Grove) | new version in `compact_versions` | episodic |
| **Bill action** (Grove) | action or roll call on a bill affecting a watched entity | blocked on `affected_entities` |

**A composition warning on the Federal Actions stream.** Of the 22,169 documents that
name a tribal term in their own title or abstract, the largest single agency is the
**National Park Service at 5,719** — ahead of Indian Affairs at 3,096. That is
overwhelmingly NAGPRA notices of inventory completion and intent to repatriate. It is the
highest-volume alertable stream in the corpus and it is also the most sensitive material
in the entire product. Decide deliberately whether repatriation notices belong in a
commercial alert feed, and if they do, route them as their own labelled stream rather
than mixing them into a procurement-flavoured digest. Shipping "5 new federal actions for
Navajo Nation this week" where four are ancestral remains notices would be a serious
editorial failure, and it is the default behaviour of the obvious implementation. Also
note `type` composition: 18,655 Notices against 1,517 Rules and 1,403 Proposed Rules — a
"rulemaking" alert and a "notice" alert are different products with different audiences.

~~Do **not** ship a "new contract award" alert. The prime series ends FY2022; an alert that
cannot fire on this week's award will be the first thing a BGOV-trained buyer tests, and
its silence would be read as a broken product rather than a documented limit.~~

**RE-DECIDE, 2026-08-26.** This recommendation was reasoned entirely from the FY2022
terminator, and that premise is gone — prime now runs to FY2026 with 61,813 FY2026 rows.
The remaining question is not coverage but **latency**: an award alert fires on a refresh
cadence, not continuously, and a buyer testing it against BGOV will measure the lag. Decide
it on the measured refresh interval (see `docs/REFRESH_CADENCE.md`), not on a coverage hole
that no longer exists. The test the paragraph anticipated is still the right test.

The subscribable object is a **watchlist** — a saved set of entities plus a saved screener
— and every alert names the entity, the tier, the evidence URL and the run that produced it.

**One consequence of that churn measurement deserves its own decision.** In a single
overnight rebuild, 71 links that were tier A — publishable — became tier C. Publishing an
entity profile is a promise that its content is stable enough to cite. Before launch,
either freeze publishable attributions into dated, versioned snapshots that a subscriber
can cite and that never silently change under them, or make the "attribution changed"
alert mandatory rather than optional so that anyone who saw the old number is told. The
jurisprudence model is the differentiator; a differentiator that revises silently is worse
than no differentiator at all.

---

## 4. Pricing

Planned: **Portal $499** (six datasets) and **Grove $2,500** (four datasets), per
`AGENTS.md` and the per-dataset docs.

### The verified comparison set

*VOS = read on the vendor's own page. PRIMARY = a federal disclosure record (FPDS, Senate
LDA, IRS 990), which is stronger evidence than a vendor page. No number below is estimated.*

| Product | Price | Basis |
|---|---|---|
| **HigherGov Starter** | **$500/yr, 1 user** | VOS |
| **HigherGov Standard** | **$2,500/yr, 10 users** | VOS |
| GovTribe Launch Plus / Growth Plus | $1,900 (1 user) / $6,000 (5 users) | VOS |
| EZGovOpps Bronze → Platinum | $2,695 / $3,695 / $4,695 / $5,995+ (+$299 setup) | VOS |
| **Casino City Press — Indian Gaming Industry Report** | $399.95 print · **$474.95 single-seat online** · $499.95 +book · $724.95 five-seat · $749.95 +book | VOS |
| Casino City — Tiller's Guide to Indian Country | $324.95 single · $549.95 three-seat | VOS |
| Casino City — bundle ladder | $474.95 → $599.95 → $1,399.95 → $1,799.95 → $3,749.95 | VOS |
| **Candid Search** (Foundation Directory + GuideStar Pro, merged) | $219/mo · $1,199/yr Premium · $1,699/yr Ultimate (a second Candid page shows $2,199 / $2,499) | VOS |
| Candid APIs | Essentials $4,800 · Premier $9,900 · Charity Check $2,750 · Grants $6,000; **Demographics and Taxonomy free** | VOS |
| Candid Nonprofit Compensation Report | $449 individual / $1,199 organizational | VOS |
| Tribal Business News | $99/yr digital | VOS |
| **GovWin IQ** | **$17,000** (NIH 2026) · $18,829 & $18,037 (HHS 2019) · $24,000 (SBA 2015) · $48,654 (FPI 2024) | PRIMARY |
| **Bloomberg Government** | **$5,940** (Treasury 2018) · $11,969 (2020) · $21,847 (2022) · $21,007 (2023) · $26,022 (NOAA 2018); also $19,170 Treasury FY24 and $63.4K/$107.6K DOL OIG over 29 months | PRIMARY |
| **PitchBook** | **$6K–$10K per seat**, triangulated three ways: ~$5,920 blended (Morningstar 10-K: $671.8M / 113,451 licensed users), **$7,000/licence exactly** on HHS PO 75P00122P00094 (13 licences, $91,000), $7,000/seat at a 5-seat minimum reported. Median account ACV **$31,875** (Vendr, n=130) | 10-K + PRIMARY + secondhand |
| **GovWin IQ** — typical single-agency subscription | **$15,715 · $16,081 · $17,000 · $18,564 · $24,000 · $36,866 (2yr) · $48,654**; renewals rise 15–20%/yr at HHS ($15.7K→$17K→$18.6K) | PRIMARY |
| GovWin IQ — bundled (Federal Advance + SLED Advance + Salesforce Connector) | **$187,733/yr** (DOJ 15UC0C22F00001350) | PRIMARY |
| Candid — Foundation Directory Professional, historical | $3,995/yr (2009–12) → $4,995/yr (2013–18) → **$7,495 for 6 licences (2021) ≈ $1,249/seat** | PRIMARY |
| Candid — GuideStar Premium per seat, historical | **$773.76/seat** (HUD 2008, 21 licences) · **$1,008/seat** (HUD 2013, 67 users) · **$1,279/seat** (DHS, 44 users) | PRIMARY |
| Candid — Foundation Directory **Enterprise** | **$29,995/yr** (State Dept; $119,980 over 2019–2023 = exactly $29,995/yr) | PRIMARY |
| Candid — bulk custom dataset | **$29,700 for 224,044 records = $0.1325/record** (USDA 12C0BZ24P0004) | PRIMARY |

**BGOV and GovWin publish no list price at all.** The widely circulated "$5,000–$15,000
per BGOV seat" figures come from competitor content-marketing pages, are mutually
contradictory, and two of them were checked and found false against live vendor pages.
The FPDS actuals above are the only defensible anchors.

### Willingness to pay, from the data Cedar Press already holds

| Signal | Value |
|---|---|
| NCAI tribal dues, sliding by tribal revenue | $150 → **$30,000** (over $30M revenue) |
| NAFOA membership | **$5,000/yr flat** |
| IGA associate dues — **law firms** | $2,500 (<$5M rev) → $5,000 → $10,000 → **$15,000** (>$20M) |
| IGA associate dues — banking/financial | $2,500 → $5,000 → $15,000 |
| IGA associate dues — **publications** | **$1,000** |
| IGA Tradeshow 2027 booth, per 100 sq ft | $4,550 non-member · $3,700 associate · $3,600 tribally owned |
| Federal lobbying retainers paid by tribes | **$10,000–$30,000 per client per quarter** (Sonosky, Hobbs Straus) |
| Cedar Press's own lobbying file: clients spending ≥$100K in 2025 | **126** |
| Cedar Press's own lobbying file: annual Native federal lobbying spend | ~$35–41M/yr, 2017–2025, rising |

### Read

**1. The $499 price collides exactly with HigherGov, and that is the wrong fight.**
HigherGov Starter is $500/yr for one user; HigherGov Standard is $2,500/yr for ten. Cedar
Press's two planned tiers land on the same two numbers. A federal-contracting buyer
comparing them sees a product with ~~FY2022 data,~~ **[STALE 2026-08-26 — the data is now
current through FY2026; strike this clause and re-weigh the read, because it was the
heaviest item in it]** no solicitations, no forecasts and no
recompete alerts against one with everything current — and Cedar Press loses that
comparison on every axis except the one that matters. **Do not let the price frame Cedar
Press as a HigherGov substitute.** Two defensible responses: price the Portal *below*
HigherGov (in the $249–$349 range) and position it explicitly as the Native-entity
resolution layer you run *alongside* HigherGov — the join key they cannot give you — or
hold $499 and never place the two side by side in any material.

**2. Against the actual incumbent, $499 is right and possibly low.** The real competitor
in this vertical is **Casino City Press**, and the comparison is favourable in a way that
should be stated internally and never as marketing copy: their Indian Gaming Industry
Report sells single-seat online at **$474.95**, and the edition on sale today carries
**calendar-year 2017 statistics**. Tiller's Guide is a third edition with gaming counts as
of 2015. A market that has been paying $325–$750 a seat for 2017 numbers is a market that
will pay $499 for a live product. Note also the correction: **Meister is not a second
competitor** — Alan Meister authors the report, Casino City publishes it. There is one
incumbent, and it is nine years stale.

**3. Grove at $2,500 is under-priced for the segment that will actually buy it.** Law
firms with Indian law practices already pay IGA **$2,500–$15,000/yr in association dues
for nothing but access**, and they amortise one seat across enormous client books —
Hobbs Straus filed 138 LDA reports in 2025, Sonosky 116, at $10K–$30K per client per
quarter. For that buyer $2,500/yr is under 3% of a single quarterly retainer. Grove could
carry $5,000–$7,500 for law and lobbying firms without resistance. Consider a third tier
rather than repricing Grove: **Portal / Grove / a firm licence** priced by practice size,
exactly as IGA and NCAI already price this market.

**4. Specify the seat count, publicly, at both tiers.** HigherGov's $2,500 buys ten users.
Cedar Press's $2,500 buys an unspecified number. That is the first question every buyer
will ask, and an unspecified answer reads as "we haven't thought about it." PitchBook's
entire pricing power comes from putting quantity limits in a private Order Form — that
strategy requires an enterprise sales motion Cedar Press will not have at launch. Publish
the seat count.

**5. Add a per-report SKU at the price this audience has already proven it pays.** Casino
City's $399.95–$749.95 single-report price point is a validated willingness to pay for a
standalone Native-market publication, and Candid sells its Nonprofit Compensation Report
standalone at $449/$1,199 on the same logic. The planned annual flagship ("Every Formal
Federal Action in Indian Country 2026") is exactly that shape. Sell it at $399–$499
standalone, bundled free into Portal. It converts the editorial calendar into revenue and
gives non-subscribers a first transaction.

**6. Do not price against PitchBook or BGOV.** Their realised contract values — PitchBook
median ACV $31,875, BGOV $5,940–$26,022, GovWin $17,000–$48,654 — reflect recency,
completeness and forward-looking pipeline that Cedar Press does not have and, per section
1, should not try to buy. Citing them as comparables invites the coverage comparison Cedar
Press cannot win.

**7. Two naming collisions to resolve before launch, both inside Lumecon.** Lumecon
already sells **Sprout $500 / Sapling $2,500 / Tree $7,500**, so Cedar Press's $499 and
$2,500 duplicate its sibling's first two price points — a customer holding both invoices
will ask which product they are actually buying. Worse, **"Cedar Grove" is already the
name of the Tree-plan organisational data library** at $7,500, and "Cedar" is already
Lumecon's AI analyst. A Cedar Press "Grove" tier at $2,500 is a third meaning for the same
word at a third price. Rename it.

**8. The cheapest distribution channel is $1,000.** The IGA associate-member
**Publications** tier is $1,000/yr and puts Cedar Press in the directory that this exact
buyer set uses. Against a $3,600–$4,550 tradeshow booth, it is the obvious first spend.

**9. Meter throughput, not access — and copy Candid's split precisely.** Nobody in this
market sells "a profile." They sell a seat with a throughput cap: HigherGov meters export
rows per search, Candid meters downloads per month (250 grants + 750 profiles at $219/mo,
1,000 grants/mo at $1,199/yr), and both leave the profile itself free to view as bait.
Candid then does the thing Cedar Press should copy exactly: **its Demographics and
Taxonomy APIs are free, and it charges $2,750–$9,900/year for the APIs that carry the
funding linkage.** Give away the identity layer, charge for the join. Translated: publish
the 866-entity spine — names, classes, states, IDs — free and open, and licence the
identifier crosswalk. That is already the instinct in `docs/handoffs/STATE_OF_BUILD.md`'s
public/subscriber/internal column tiering; Candid's price list is the proof it works.

**10. Price against the repair work, not against the raw data.** USAspending and SAM give
away FPDS, FABS, SAM and FSRS for $0, unauthenticated, with no rate-limit headers on the
response. HigherGov's $500 and GovWin's $15K–$50K both price the *repair* — identity
resolution, pre-RFP forecasts, FOIA'd documents, 500,000 contact records, 470,000 labor
prices, 150 analysts. Candid's entire existence is the same trade against the IRS, and the
proof is a single contract line: **the IRS paid GuideStar $1,202,687 for its own Form 990
and 990-PF data back, digitised** (Treasury TIRNO12K00531, 2012–2014). Cedar Press's repair
work is the crosswalk and the rulings. That is what the invoice should describe.

**The structural bet, stated plainly.** Roughly **$17.3M/year in earned revenue** already
moves through the five national Native business organisations — IGA, NCAIED, NAFOA, NCAI
and NACA — plus another ~$5.6M through the state gaming associations. Essentially none of
it is a data product; it is dues and convenings. The one firm selling data into this
vertical is selling 2017 numbers in 2026. That is the opening, and it is a real one. It is
also small: this is a market that supports a good business, not a Bloomberg.

---

## 5. The three highest-leverage additions for launch

**Zeroth, and not an addition: withdraw the medium-confidence lobbying attributions.**
Finding 4 in section 0 is a live false attribution — $28.7M of an Arizona power district's
lobbying spend published as a tribe's, plus a mining company, a city and a CDQ group — in a
$499-tier dataset. That is a *withdrawal*, not a build, it takes an afternoon, and it has
to happen before any of the three below. Everything in this document rests on the claim
that Cedar Press does not falsely attribute. That claim is currently false in Dataset 4.

### 1. Resolve every tier-A link to a spine ID, and populate the entity key on the six datasets that lack one

Cost: rulings work, which is the thing this project is already good at. Value: it is the
difference between a product and a folder of CSVs.

**Most of this is propagation, not research.** Measured on 2026-08-06:

| Fix | Size of the actual job | Evidence |
|---|---|---|
| 878 `bgov_manual` tier-A links | **241 distinct name strings**, not 878 rows | queue of 241 items recovers the richest hand-verified asset onto the profile page |
| 98 ownership events | **94 of 98 resolve today** from mappings already on disk | `deals_party_autoresolved` + `_agent` + Elijah's file give a 557-entry party→`tribe_id` map; all 323 distinct IDs in it are already in the spine. `native_entity_neid` is empty because nothing ever wrote it, not because the answer is unknown |
| Compacts (707 rows) | **89% of 286 distinct tribe names** match a spine canonical name or alias exactly; 641 of 707 rows | plus 61 known-defective BIA rows to route to review rather than to an entity |
| Gaming land decisions (138) | **95% of 95 names**, 132 of 138 rows | 3 known BIA column conflicts excluded |
| Gaming facilities (774) | **31% of 317 names**, 222 rows — this one is real work | Casino City uses its own tribe strings; needs an alias pass |
| Bills (3,037) | not testable — `affected_entities` is empty at source, so this is extraction, not matching | the only genuinely new build on the list |
| Nonprofits (12,764) | 739 tier A, 4,933 already ruled X; `ruling_authority` blank on 12,389 rows | the EIN bridge exists (`np_ein_uei_bridge.csv`) |

So four of the six unlinked datasets are a few days of propagation and one alias pass.
Ruling the ownership-event parties is named in `docs/handoffs/STATE_OF_BUILD.md` as the highest-value
single fix in the project; the measurement here says it is also nearly free.

Until this lands, the entity profile page renders four sections out of nine, the
cross-dataset linkage claim is false for six of ten datasets, and the moat is 30%
deployed. Nothing else on this list changes the product as much.

### 2. Close the recent-years hole in prime contracting: FY2023–FY2026 — ✅ DONE 2026-08-12

**This addition is complete. Do not re-plan it.** The archive backfill
(`docs/PRIME_ARCHIVE_PULL_LOG.md`, 2026-08-12) landed `prime_contracts_archive_backfill.csv`
(631,507 rows) and `data/clean/prime_contracts.csv` now holds **1,217,768 rows, FY2000–FY2026,
$310.01B**, with FY2023–FY2026 at 45,747 / 53,056 / 48,879 / **61,813**. Verified against the
file 2026-08-26.

The reasoning below is retained because it is still the right argument for keeping the
series current — only the "four years old" premise has expired.

> Cost: real but bounded — a USAspending/FPDS pull under `docs/PULL_DISCIPLINE.md`, then the
> existing attribution pipeline. Value: a data product whose newest federal contracting
> number is four years old cannot be positioned against BGOV at any price. Every buyer
> opens a profile, sees the series stop at 2022, and forms a permanent judgement.

**What is genuinely still open on prime: FY2007.** It is a host edge-block, not an absence.
Disk is no longer the constraint.

**The subcontracting paragraph that used to sit here was wrong in three ways and is struck.**

> ~~The subcontracting pull is half-done in exactly the same shape and the halves are the wrong
> way round: **345,090 raw rows and 51,396 net-new UEIs are staged for FY2001–FY2011, and
> FY2012–FY2026 — the years anyone would actually ask about — are the ones blocked at the
> USAspending rate limit.** Resume it with `code/43_resume_subaward_pull.sh`, under a single
> host lock per `docs/PULL_DISCIPLINE.md`; four agents polling the same host on 2026-08-05
> is why it is blocked.~~
>
> ~~Second-order gain, and it is large: **51,396 net-new UEIs** against a current identifier
> ledger of 19,232 links is a discovery pool nearly three times the size of everything
> attributed so far.~~

Corrected 2026-08-26:

1. **It is not half-done.** Promotion completed 2026-08-06; `data/clean/subawards.csv` holds
   **89,809** rows and zero staged rows are uncovered.
2. **345,090 is not a subaward count.** It is raw all-recipient rows across the first 11 of
   26 fiscal years, of which 1,798 were Native-linked. The same source log's PROMOTION
   section supersedes it: 22 FY on disk, **6,613,471 raw rows**, **53,429 Native-linked**.
   Likewise 51,396 net-new UEIs → **251,814**, and the staged UEI file
   (`subaward_uei_netnew_2026-08-05.csv`, 252,078 rows) is a **one-row-per-UEI dimension
   table, not subawards**. Never sum it into a row count.
3. **`code/43_resume_subaward_pull.sh` is not the live route.** The remaining hole is
   FY2021–FY2024 (173 / 89 / 120 / 166 rows) and it is **upstream**:
   `data/raw/subcontracts/usaspending_2026-08-12/_state.json` shows all four years
   `status: failed`, `total_rows: 0`, from a service-wide `bulk_download` outage proven by a
   prime-award control and an FY2015 replay. The route is
   `py -3 code/121_pull_subawards_api.py canary`, then `pull --sequential`, then re-run
   scripts 41 and 45 (both idempotent). **Never raise `MAX_INFLIGHT` above 1.**

The second-order gain is still real and now larger: **251,814 net-new UEIs** against an
identifier ledger of **20,559 links** is a discovery pool more than twelve times the size of
everything attributed so far. It feeds directly into addition 1, and it is the mechanism by
which the crosswalk moat gets wider rather than merely deeper.

### 3. Ship the identity panel and the "new identifier attributed" alert as the visible product

Cost: lowest of the three, mostly front-end. Value: highest per dollar, because it is the
only part of the surface no competitor can imitate. Every other section of the profile
page is a nicer rendering of data a determined analyst could assemble. The identity panel
is the answer to a question USAspending, BGOV and HigherGov structurally cannot answer,
and the alert turns that answer into a subscription rather than a download.

Sequencing note: 3 depends on 1 for content and is worthless without it; 2 is
independent and can run in parallel under a single host lock. The zeroth item gates all
three.

**What addition 2 unlocks that is worth naming now.** Recompete and expiration exist as
*filters* in every competing product and as a first-class *alert* in none — "this contract
expires in 180 days and here is the incumbent" is unclaimed in both the govcon and the
private-markets vertical. It requires a current contracting series, which is exactly what
addition 2 restores. It is the strongest reason to do addition 2 beyond simple credibility.

**Deliberately not on this list:** a public API (nothing to serve until 1 lands), CRM
integration (no pipeline workflow to integrate with yet), and any deal-flow or M&A
positioning. Measured, the M&A-shaped population is **141 rows** (120 acquisitions, 15
divestitures, 5 equity investments, 1 JV) across 26 years, of which **108 carry a
disclosed value**, at 2–7 rows/year before 2010. That is a genuine and unique record — no
one else keeps it — and it is nowhere near a PitchBook-shaped promise. Sell it as an
**ownership-change ledger** feeding time-aware attribution, which is what it actually is
and what makes the crosswalk correct-as-of-a-date. Do not sell it as deal flow or comps.

---

## Appendix A — the Cedar Press mockup: what the search actually found

**No Cedar Press mockup was found.** Reporting this plainly rather than describing
something I did not read.

- `gh` is **not installed** on this machine, so all GitHub access was via the public REST
  API and an existing local clone.
- **`teim-team` exists and has exactly one public repository: `teim-team/lumecon-website`.**
  Its branches are `main`, `pricing/sprout-annual-1000`, `pricing/sprout-annual-1000-v2`,
  a dependabot branch, and five `claude/*` branches. **The string "Cedar Press" does not
  appear on any of the nine branches.** "Cedar" there is `src/components/CedarChat.astro`
  and `scripts/cedar-eval.ts` — the Lumecon AI analyst, not a data portal.
- **`teim-team/lumecon-studios` is not publicly visible** (API returns 404), but a local
  clone exists at `C:\Users\esm247\Desktop\lumecon_reservation_industry_mix\lumecon-studios`
  with working credentials. Its ten remote branches include
  **`claude/cedar-grove-hardening-kxdpft`** — fetched and read. In that repo *Cedar* is
  Lumecon's data product and training corpus (`docs/CEDAR_CORPUS.md`), and *Cedar Grove*
  is (a) the demo client name used across every template sample and (b) the Tree-plan
  organizational data library. **"Cedar Press" appears nowhere in that repo either.**
- No other GitHub org matching "teim" holds a relevant repository.

**Conclusion:** if a Cedar Press mockup exists it is in a private repository not reachable
from this machine, or under a name not containing the string. The closest artefacts that
do exist are `review/cedar_review.html` (the attribution review page — a working QA
interface, not a subscriber-facing product) and `docs/ANCSA_PORTAL_BUILD_LOG.md` (a
harvest log for the Alaska DBS portal, not a Cedar Press design).

**A naming conflict worth resolving before launch:** in Lumecon's shipped product,
*Cedar* is the AI economic analyst and *Cedar Grove* is the Tree-plan data library at
$7,500/year. Cedar Press's planned "Grove" tier at $2,500 collides with both the name and
the price point of a different product from the same company.

---

## Appendix B — corrections to `docs/handoffs/STATE_OF_BUILD.md` found while measuring

1. **Tier A is 1,705, not 1,581**, and the spine is 866, not 687. The 687 figure is the
   NEID backbone; the spine has grown past it. The state document's "Spine status" table
   is stale on both rows (it also reports "Elijah rulings on file: 25" three lines below a
   line saying 164).
2. **The $42.6B publishable prime figure is traceable** — it is `prime_dollars_M` summed
   over `cedar_publishable_identifiers.csv`, now $42.2B, and it does not double count.
   But it **does not reproduce from `prime_contracts.csv`**: the same 699 publishable UEIs
   sum to $34.6B there, an 18% gap. Two different sources are being called the same thing.
   Add the definition and the reconciliation to the state document.
3. **Tier-A entity coverage is 265 of 866 (31%)** — a number the state document does not
   report anywhere, and the single most important number for judging launch readiness.
   Depth is thinner still: within the only window where all four panel components are in
   source range (2011–2022), **25 entities ever reach four components in a single year,
   156 reach three, and 241 reach exactly one**.
4. **The gaming-openings ceiling is stated as 2018** but 7 rows fall in 2019–2022. The
   substance of the warning holds (post-2018 is unusable as a trend); the year should be
   restated as "effectively 2018; 7 thin rows after."
5. **`ownership_events.native_entity_neid` is empty on all 98 rows**, so the file is not
   only carrying the withdrawn `ND-2026-077` as noted — it has never been joined to the
   spine at all. 94 of the 98 are resolvable today from mappings already on disk.
6. **Quarantined methods still carry tier-A rows.** `need_v6` is quarantined (9 rulings
   against, 0 for) and `cluster_v3` is listed as quarantined in
   `docs/CROSS_DATASET_LEARNING.md`, yet **8 tier-A links rest on `need_v6` and 43 on
   `cluster_v3`**. Tier A means publishable. A publishable row resting on a discredited
   method is the exact failure mode the tier system exists to prevent, and 51 rows is a
   small enough number to adjudicate before launch rather than after.
7. **`TRBF-KTNIID-00` conflates the Kootenai Tribe of Idaho with the Confederated Salish
   and Kootenai Tribes** — already a live warning in the state document, and it surfaces
   in the top-15 entity ranking as "Confederated Salish, $2.79B." Any launch demo that
   shows a leaderboard will show this row. Rule it before the first screenshot.
