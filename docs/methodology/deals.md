# Methodology — Indian Country Deals

**`deals`. `data/clean/deals_classified.csv`, 1,073 rows, 959 entity-linked
(89.4%).** [measured 2026-09-02, after the staged merge in section 5b]

> The figure was **935 rows / 886 linked (94.8%)** earlier the same day, and
> that number appears throughout sections 1-5 below because those sections
> describe how those 935 rows were made. `code/1088_merge_staged_deals.py`
> added 138. **The link RATE fell while the link COUNT rose** - most of the new
> parties resolve to the spine and a minority do not, which is what a new
> channel looks like before its parties are ruled.
> `review/deals_party_unmatched_2026-09-02.csv` holds the 87 distinct unmatched
> parties.
>
> **1,079 appears in `AGENTS.md` and in `docs/MONEY_TOTALLING_RULES.md` and is
> the figure BEFORE gate G11 was added.** Six rows merged before G11 existed
> were withdrawn WHOLE to `review/deals_withdrawn_duplicates.csv` (3 -> 9 rows)
> rather than deleted, and they carried **$0** — so `Announced_Value_USD` is
> unchanged at $47,880,355,533 either way. Named individually: `NLTR-2016-003`,
> `NLTR-2018-009`, `NLTR-2020-003`, `NLTR-2021-008`, `NLTR-2024-010`,
> `NLTR-2026-013`.

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

**Readiness: READY.** [measured — `docs/DATASET_READINESS.md`, regenerated
2026-09-02: 14 tables, 14/14 grain, 14/14 keys, duplicates clean, 0
aggregation-unsafe, rebuild declared]

---

## What makes this dataset different from the other twelve

**Cedar originates this one rather than collating it.** Nobody else assembles
a transaction ledger for Indian Country, which is the reason it exists — and
it is also why it is *"the only dataset built from press rather than an API,
and therefore the highest fabrication risk in the project."*

Two consequences run through everything below. First, **every row carries a
source link**: measured on all 935 rows, 651 (69.6%) carry two independent
source URLs, 284 (30.4%) carry one, and **0 carry none**. [measured] Second,
the inclusion bar is written down and enforced per row rather than left to
judgement:

- **$1M threshold by default.** A sub-$1M row needs `Threshold_Exception = Yes`
  plus a rationale. 160 of 935 rows carry `Yes`. [measured]
- **Never write a row whose DATE is not in retrieved evidence.** Skip and log.
- **Never write a dollar figure you cannot re-read in retrieved text.** No
  figure may come from a search summary.
- **Never file a deal by announcement year when the transaction year differs.**
- Date precedence: transaction/closing > official announcement > publication.
  Month-level is allowed with a mid-month placeholder **only** if `Date_Basis`
  discloses it. **Never invent a day silently.**
- Aggregates: a formula round (IHBG) is one portfolio row; a competitive round
  with a published recipient list is one row per award.

---

## 1. Sources — four channels, each with its own access story

### Channel 1 — entity newsroom sweep

`code/22`, logged in `docs/DEALS_BUILD_LOG_2026-08-05.md`. Twelve tribal
corporations swept; 31 rows.

**Capture rate is driven by newsroom structure, not deal volume.** Waséyabek
and Cherokee Nation Industries produced 16 of 31 rows because they publish
dated permalinks. Doyon is far more acquisitive and produced fewer. **A
newsroom-derived series measures publishing habits before it measures
activity.** Blocked at 403 or paywall: `nana.com`, `ahtna.com`,
`crainsgrandrapids.com`, `journalstar.com`.

### Channel 2 — SEC EDGAR, two passes

`docs/DEALS_2000_2019_BUILD_LOG.md` (24 rows) and
`docs/DEALS_SEC_2010_2017_BUILD_LOG.md` (16 rows).

**Access:** WebFetch 403s on sec.gov; curl or urllib with a declared
User-Agent (name plus contact email) returns 200. Three endpoints:
`Archives/edgar/full-index/<year>/<QTR>/company.idx` (all 32 files for
2010–2017, 1.2 GB — this *"converts registrant discovery from a guessing game
into a census"*), `data.sec.gov/submissions/CIK##########.json` for 8-K items
1.01/2.01/2.03 (item tagging exists only from **August 2004**), and
`efts.sec.gov` full-text (**2001 onward only**).

**A dating technique for the pre-2004 window:** S-4 exchange-offer prospectuses
restate the original private-placement date and amount in plain text, often
three times.

**The census settled a question rather than just adding rows.** The prior run's
seven name-guessed registrants became a complete list of eleven, and **three of
the six new ones are not gaming authorities**: tribes appear on EDGAR as debt
issuers, as **Form D exempt-offering issuers** (Coos, Oglala) and as **13D/13G
and Section 16 equity holders** (ASRC, Chumash, CNI, the BBNC Foundation).

**Registrants confirmed ABSENT — do not re-search:** San Manuel, Morongo,
Pechanga, Quapaw/Downstream, Wind Creek/PCI, Tulalip, Muckleshoot, Gila River,
Salt River, Choctaw Nation, Citizen Potawatomi, Osage, Ho-Chunk, Oneida, Forest
County Potawatomi, Saginaw Chippewa, Mashantucket Pequot and about fifteen
more. **The reason is structural, not a coverage failure: these tribes finance
through Rule 144A private placements, which are never registered and leave no
EDGAR trail.** "Extend the SEC channel" is closed as a line of work.

### Channel 3 — ANC annual reports

`docs/DEALS_ANC_REPORTS_BUILD_LOG.md`, 28 rows, FY2000–2015.

The prior run had recorded *"No ANC annual-report PDF was successfully located
and read."* **43 reports across nine corporations were located and read.** The
access finding: the **Internet Archive Wayback CDX API is a complete queryable
index of every PDF an ANC ever published**, and
`web.archive.org/web/<timestamp>id_/<url>` fetches the file past a live-site
block. Run against 25 domains it returned **6,058 archived PDF snapshots**, 124
of them annual or shareholder reports. It reached documents that no longer
exist anywhere — Sealaska's 2000 report, eight PDFs, off the live web for
twenty years.

Pipeline: CDX query → curl with a declared UA → `pdftotext -layout` → keyword
scan for transaction verbs co-occurring with month names and dollar figures →
**read every hit in its own paragraph before writing anything.**

ASRC is the best-behaved filer: a numbered **NOTE 3 – ACQUISITIONS** every
year, with dates to the day, prices and purchase-price allocations, and it
restates prior-year acquisitions. Sealaska carries a **"Divestitures of
Subsidiaries"** note, which is unusual and valuable — divestitures are the
hardest event class to date.

Two archive-side caps cost rows: BBNC's 2007/2013/2017 snapshots truncate at
exactly **1,048,576 bytes** (a 1 MiB Wayback cap), and NANA's 2006/2007
truncate across twelve alternate timestamps.

**Fiscal-year alignment governed admission.** ASRC's fiscal year is the
calendar year, so two year-level ASRC statements were admitted as rows; NANA's
ends in late September, so its equivalents were not — costing a clean $4.8M
transaction, which is logged as skipped rather than quietly dropped.

### Channel 4 — the 2000–2019 wave, and one honest negative

`code/25`, 40 rows. The finding worth keeping is the channel that produced
nothing: **the Federal Register produced ZERO deal rows.** 97,857 FR documents
sit in the window, including 509 `ancsa_conveyance`, 356
`tribal_state_compact`, 199 `land_into_trust`, 88 `gaming_land_decision` and 81
`reservation_proclamation`, all authoritatively dated. But they are **NEPA
process notices, proclamations and statutory conveyances: they date projects
and federal actions, not transactions**, and they carry no counterparty and no
consideration. The planning brief had called this channel *"highest-value and
cheapest"*; it is the cheapest, and its direct conversion rate to deal rows in
2000–2019 is zero. **Use it as a lead index only.**

### The largest channel by row count — published federal award lists

`deals_federal_awards_additions.csv`, **594 rows**, from NTIA TBCP, HUD
ONAP/ICDBG, EDA ARPA, DOE and USDOT RTA award lists. Host distribution across
both source columns: `broadbandusa.ntia.gov` 494 · `hud.gov` 224 ·
`eda.gov` 102 · `energy.gov` 98 · `sec.gov` 54 · `transportation.gov` 18.
[measured]

### The dating precedence rule, and why it is load-bearing

**An audited financial statement outranks a newsroom release, for both date and
value.** Two reasons, and the second is the one that bites:

1. The audited date is when control transferred — the filing consolidates the
   target from it.
2. **Newsroom dates in this corpus ran LATER than audited dates in every case
   checked, by 2 to 16 days. A one-directional bias, never earlier.**

Near a year boundary that silently moves a transaction into the wrong year:
UIC/Northbank was announced 2026-01-16 and audited at 2025-12-31, so the press
date would have filed a 2025 transaction into 2026. Applied by
`code/54_reconcile_deals_duplicates.py`.

---

## 2. How the rows were made

> ⚠ **Script numbers are not unique in this project.** `ls code/153_*` returns
> both `153_merge_base_ledgers_into_classified.py` and
> `153_merge_ordinance_ocr.py`; `154_*`, `155_*`, `88_*`, `33_*`, `41_*` and
> `156_*` also collide. Cite the filename.

1. **`code/88_build_deals_taxonomy.py`** — the taxonomy and the promoted
   ledger. Its structural finding is stated up front and is the most
   consequential decision in the dataset: **594 of 790 rows (75.2%) were
   federal grant awards. A grant award is not a deal in the transactional
   sense, and publishing "790 deals" would be publishing "196 deals and 594
   grants" without saying so.** So `record_class` (`TRANSACTION` /
   `PUBLIC_AWARD`) is the first cut, and there are **five axes, not one
   column** — `record_class`, `sector`, `transaction_type`, `capital_source`,
   `native_party_role` — because "gaming deals", "acquisitions" and "federally
   funded" are three different questions. **Every original string is preserved
   in a `*_raw` column**, and anything the rules cannot classify goes to
   `review/` as `UNCLASSIFIED` rather than being forced into the nearest
   bucket. Before the taxonomy, `Industry` had 156 distinct free-text values,
   `Value_Type` 161, `Event_Type` 101, and `Deal_Category` put 594 of 790 rows
   in one bucket.
2. **`code/54_reconcile_deals_duplicates.py`** — applies the dating rule and
   writes withdrawals **whole** to `review/deals_withdrawn_duplicates.csv`.
3. **`code/57_autoresolve_deal_parties.py`** — resolves *which* entity, never
   *whether* Native. The ledger already answered that: *a row is only in the
   deals ledger BECAUSE it was already identified as an Indian Country deal.*
4. **`code/33_apply_party_rulings.py`** and
   **`code/53_apply_agent_deals_rulings.py`** — apply the owner's and the
   agent's rulings.
5. **`code/126_apply_deal_party_attribution.py`** — writes the seven
   `native_party_*` columns **in place**.
6. **`code/153_merge_base_ledgers_into_classified.py`** — merges the two root
   ledgers, 131 of 132 rows.
7. **`code/154_extend_autoresolved_parties_additive.py`** — merges the rejected
   57 re-run **additively**, asserting `lost: 0  repointed: 0` afterwards.
8. **`code/155_collect_deals_2026_08.py`** — the August 2026 sweep, +14 rows.
9. **`code/156_refresh_deals_codebook_fragment.py`** — re-measures the deals
   codebook fragment alone.
10. **`code/505`** — writes `cedar_uid`.

### The miscount that produced "790 deals", and its arithmetic

```
 790  the eight non-empty deals_*_additions.csv files (594+42+40+34+30+28+16+6)
      -> 790 of 790 already carry a Deal_ID the classified ledger holds (100%)
+131  merged from the two ROOT ledgers by 153 (132 rows, minus 1 withdrawn)
= 921  the state measured 2026-08-26 (921 rows / 874 linked)
 +14  added by 155 in the August 2026 sweep
= 935  [measured 2026-09-02]
```

**The defect:** `88_build_deals_taxonomy.py` built the master from exactly one
input — `glob(data/clean/deals_*_additions.csv)`. That glob captured every
additions file and **never the two BASE ledgers those additions were additions
to**. The symptom that surfaced it: a 790-row ledger carrying **one** row dated
2026 while **76 verified 2026 rows sat in the project root.**
`docs/FACT_CHECK_2026-08-06.md` finding B-1 had named this exact miscount three
weeks earlier; *it kept propagating because nothing connected the fact-check to
the code.*

The glob was fixed in all three places it appears —
`88_build_deals_taxonomy.py`, `57_autoresolve_deal_parties.py` (which now reads
the promoted table) and `41_build_codebooks.py`'s `01_deals` entry. A
complete-cover check re-measured today: **0 classified rows are in neither a
staging slice nor a root ledger**, so a rebuild reading both surfaces loses no
row. [measured]

`_source_file` shows the root ledgers as first-class contributors:
`deals_2026_ytd.csv` 90 rows and `deals_historical_2020_2025.csv` 55 (56 minus
the withdrawn `MA2020-008`). [measured]

### Sibling tables

| table | rows |
|---|---:|
| `deals_classified.csv` | **935** (935 distinct `Deal_ID`) |
| nine `deals_*_additions.csv` | 790 total (`deals_2026_ytd_additions.csv` is header only) |
| `deals_2026_ytd.csv` (repo root) | 90 |
| `deals_historical_2020_2025.csv` (repo root) | 56 |
| `deals_party_attribution.csv` (owner rulings) | 56 |
| `deals_party_attribution_agent.csv` | 530 |
| `deals_party_autoresolved.csv` | 502 |
| `deals_party_matches.csv` | 481 |
| `deals_source_index.csv` | 533 |
| `deals_taxonomy.csv` | 48 |
| `ownership_events.csv` | 98 |
| `seminole_bond_disclosures.csv` | 29 |
| `tribal_resolution_financings.csv` | 1 |

[measured]

---

## 3. How entities were attributed

Attribution method on 935 rows [measured]:

| method family | rows |
|---|---:|
| `agent_ruling` — alias 246 / core 216 / exact 200 / containment 93 | **755** |
| `elijah_ruling` — exact 25 / core 24 / containment 24 / alias 6 | **79** |
| `deterministic_` — containment 25 / core 16 / exact 9 | **50** |
| blank | 49 |

Tier: **A 716 · B 170 · blank 49.** `native_party_value_caution` is populated
on 834 rows. [measured]

**The agent ruling pass** (`docs/DEALS_PARTY_RESEARCH_LOG.md`, 549 rulings, 25
left UNRESOLVED) used three evidence routes, in order:

1. **The Federal Register recognised-tribes notice as a quotable census** — 91
   FR 4102, 2026-01-30, FR Doc. 2026-01899, 575 tribal entities, pulled as
   plain text and used as an *index*, not as a search target. **241 parties
   matched verbatim; 91 more resolved as documented name variants**, each
   variant target itself verified in the notice first. The notice's
   parentheticals date renames directly: *Mi'kmaq Nation (previously listed as
   Aroostook Band of Micmacs)*, *Yuhaaviatam of San Manuel Nation (previously
   listed as San Manuel Band of Mission Indians)*.
   **A parse caution worth carrying: the FR text hard-wraps at about 70 columns
   and entries wrap without indentation, so a naive line parse returned 561 or
   613 against a stated 575.** The fix was to match against the
   whitespace-collapsed whole section and hand-audit the 34 matches that were
   not clean prefixes.
2. **The About-page method** — the firm's own ownership sentence: *"The company
   is a wholly owned subsidiary of Cook Inlet Region, Inc."*, *"Kituwah LLC is
   wholly owned by the Eastern Band of Cherokee Indians."*
3. **The deal row's own `Source_1`, read for ownership.**

Identifiers recovered along the way: **242 UEIs and 90 CAGE codes, all by exact
legal-name match — no fuzzy matching.**

### The instrumentality rule

`White Mountain Apache Housing Authority` contains its tribe's name, but a
housing authority is a **separate legal person** — a TDHE, not the tribal
government. The deals agent leaked 45 of these to tier A with a symmetric name
test. They are now **resolved to the tribe and recorded as an
INSTRUMENTALITY**, which reproduces the owner's own jurisprudence: he ruled
nine housing authorities to their tribes (Akwesasne, Colville, Comanche, Fort
Peck, Northern Ponca, San Ildefonso, Sault, Yakama, Northern Cheyenne), and the
two he did not (Cook Inlet, Santa Clara) both fail the prefix test anyway.

---

## 4. Decisions that shaped the data

### The rejected re-run of script 57

The obvious follow-up to fixing 57's glob is to re-run 57. **Measured, it
regresses, and it was rejected.** 57 rebuilds its whole output from the
**current** spine, and the spine had grown **952 → 1,310** since 57 last ran —
with **37 tribal colleges among the additions**:

```
Confederated Salish and Kootenai Tribes  TRBF-CSKTFR-00 -> TCU-SLSHKT-00
Confederated Tribes of Warm Springs      TRBF-FSCWSA-00 -> TRBF-WRMSPR-00
Keweenaw Bay Indian Community            TRBF-KWNWBY-00 -> TCU-KWNWB1-00
United South & Eastern Tribes, Inc.      TRBS-ECSIUT-00 -> ITO-NTDSTH-00

4 parties LOST outright, 4 silently repointed --
two of them from a tribal GOVERNMENT onto that tribe's COLLEGE.
```

This is the rebuild-from-a-changed-upstream hazard arriving through a third
script. The run is kept as evidence at
`data/clean/deals_party_autoresolved.csv.rerun57_2026-08-26_REJECTED`. The
standing posture: **the previous file is authoritative for every party it
already holds, and `154` may only ADD parties it does not hold.**

### The four autoresolver proposals refused by hand

`review/deals_party_refused_2026-08-26.csv` holds exactly four rows, all
`deterministic_containment`, all `n_deals = 1`, all still awaiting a ruling.
[measured]

| party | proposed | why refused |
|---|---|---|
| Riverside San Bernardino County Indian Health Inc | `UIO-HEALTH-00` (Native Health) | `UIO-HEALTH-00` is "Native Health", an **Arizona** urban Indian organisation; the party is **Californian**. The exact "Denver Indian Health → Native Health" cross-state failure |
| Department of Hawaiian Home Lands | `NHO-HAWAII-00` | DHHL is a **department of the State of Hawaii**. Two different legal persons sharing the word "Hawaiian" |
| "Nine tribal applicants incl. Dena' Nena' Henash, Cheyenne & Arapaho Tribes, Barona Band" | `TRBF-CHYARP-00` | an **aggregate of nine applicants** keyed to one of them |
| "Federally recognized tribes and tribal health organisations (aggregate, 8 projects)" | `UIO-HEALTH-00` | **two independent failures in one match** — a containment hit on the generic phrase "health organisations", AND an eight-recipient aggregate keyed to a single entity |

**The standing rule this earned: an AGGREGATE party string must never resolve
to a single entity.** Two of the four are that, and both would have booked a
multi-recipient federal round onto one tribe. **Containment gives no warning,
because an aggregate string usually contains a real tribe's name by
construction.**

### Withdrawn is not deleted

`MA2020-008` (Calista / Nordic Well Servicing) was withdrawn in favour of
`ANCSA2-2020-004` — same party, same counterparty, same 2020-01-01 date. The
survivor is Calista's **audited annual report filed with the Alaska Division of
Banking and Securities**, stating consideration of **$58,355,884**; MA2020-008
is a newsroom release carrying no value at all. It went **whole** to
`review/deals_withdrawn_duplicates.csv`, was **not deleted** from
`deals_historical_2020_2025.csv`, and **its newsroom URL was carried onto the
survivor's blank `Source_2`** so nothing retrieved was lost.

**The consequence a consumer must honour: every rebuild must read
`review/deals_withdrawn_duplicates.csv`, or the double count returns.** And
`ND-2026-077` was **not reused** after its withdrawal — reusing a withdrawn
identifier makes the withdrawal unreadable.

### A near-duplicate is not automatically a duplicate

`review/deals_duplicate_candidates.csv` is a review queue; nothing is
auto-merged. `ND-2013-004` ($43.6M) and `ND-2013-005` ($9.855M) are two genuine
tranches of one Coos bond exchange on one day. The NTIA TBCP pairs share an
identical `Deal_Title` because the title is built from the recipient name
alone — **the titles are the defect, not the rows.**

### Seven value traps caught in one month's sweep

All excluded from every value field, and each is a template for a class of
error:

- Hoopa Valley's $65M was a **2022** NTIA award, not the 2026 facility — the
  row carries no value.
- Poarch Creek's $24.1M FHWA award was made **in 2024 using FY2023 funding** —
  only the ~$4M 2026 phase is in `Announced_Value_USD`; the $24.1M sits in
  `Project_Total_Value_USD`.
- Middletown Rancheria's $3M CEC loan was approved **in 2024**.
- Rappahannock's ~$7.9M was **the partner's past federal awards**, not this
  transaction.
- Native Forward's $50M MacKenzie Scott gift is dated **2025-09-24** — parked
  in `Project_Total_Value_USD` so it cannot double-count a future 2025 row.
- The IHS Quarters $1.505M Karuk component is **already in the ledger** as
  `ND-2026-058`.
- The Cherokee / Rogers State MOU was **skipped entirely** because the source
  says *"No money will change hands under the new agreement."*

### Two search-summary traps caught by retrieving the primary

A summary presented **Paskenta Band acquires Mad River Brewery from the Yurok
Tribe** as August 2026 news; retrieved coverage dates it to **March 2024**. Had
it been trusted it would have been the window's only acquisition, wrong by two
and a half years. Same class as the **Blue North Fisheries** exclusion, framed
as "2025–2026" and actually effective **2019-09-30**. This is exactly why the
bar reads *never write a dollar figure or a date you cannot re-read in
retrieved text.*

### A negative finding recorded as found

**Zero acquisitions closed or announced in Indian Country between 2026-07-28
and 2026-08-26** across every swept channel. All twelve August rows are capital
projects, commitments, financings, settlements or joint ventures. Notices of
funding opportunity were **not written** — a NOFO names no recipient, carries
no award date and attributes no dollar (ANA $27.5M, SBA $10M, EPA $25.5M and
IHS TMG were all skipped).

### A status fact is not a deal row

`ND-2026-040` (Scotts Valley Band, Vallejo, $700M) was overtaken when Interior
withdrew the gaming determination on 2026-07-31. **No row was written** — a
regulatory reversal is not a transaction, and a row carrying the $700M would
double-count. It went to `review/deals_status_corrections_2026-08-26.csv` and
was **not applied automatically**, because the `Status` vocabulary has no
agreed term for a withdrawn federal determination and inventing one silently
drops the row from the fixed-label rollups.

---

## 5. What was excluded on purpose

Sources marked `TERMS_STATED_RESTRICTIVE` are excluded by **every** route,
including a harmonised derivative: **Confederated Colville**, **CTUIR /
Umatilla**, **Yakama**, **Chickasaw** (its terms name company directories
specifically, ~622 firms), **NANA / Akima** (forbids automated use, scraping
and aggregation; ~55 operating companies, the single highest-value refusal in
the project — a sitemap enumeration was **stopped mid-run** when the terms were
read), **Southern Ute** (27 firms), **Forest County Potawatomi** (18 firms),
and Navajo's NBOA directory.

Three of the eight bear on this dataset:

- **NANA / Akima** is an ANC family with an active deal history, and
  `nana.com` is *independently* blocked at 403.
- **Forest County Potawatomi** is also **confirmed absent as an EDGAR
  registrant** — a separate, independent reason it has no deal rows.
- **Chickasaw appears in the ledger anyway, via `chickasaw.com`, on 14 rows**
  [measured] — the exclusion is scoped to its **company directory**, not to the
  nation's press releases.

> **A tension worth stating rather than leaving a reader to infer.**
> `docs/PUBLICATION_POLICY.md` says a `TERMS_STATED_RESTRICTIVE` source is
> excluded by every route *"including … the Wayback Machine"*, while
> `docs/DEALS_ANC_REPORTS_BUILD_LOG.md` records the Wayback CDX route as the
> technique that reached NANA's 2001–2005 annual reports and produced three
> rows. **The reconciliation is that the restriction attaches to the
> vendor/company directory, not to the corporation's published annual reports.
> That is coherent, and it is stated in neither document.** It should be
> settled explicitly rather than relied on.

---

## 5b. THE 2026-09-02 STAGED MERGE - 138 rows admitted, 174 refused

*`code/1088_merge_staged_deals.py`. Disposition: `review/deals_1088_disposition.json`.
Every refusal is kept WHOLE, with its evidence quote and a named reason, in
`review/deals_1088_refusals.csv`. Nothing was deleted.*

Three agents staged candidates across four channels and none had been merged,
because each needed a read rather than a column mapping. **312 candidates in,
138 admitted, 174 refused, and the arithmetic is asserted in the script rather
than reported** — `admitted + refused == in` is an `assert`, not a print.

| channel | in | admitted |
|---|---:|---:|
| tribal press, tier A unique (`994` screen) | 258 | 90 |
| SEC EDGAR (`1032`) | 21 | 22 |
| ANCSA STAR portal, AS 45.55.139 (`1031`) | 24 | 24 |
| EDGAR held on the terms question | 3 | **1** |
| identifier-driven ownership changes (`1071`) | 6 | 2 |

*(EDGAR admits 22 from 21 because the terms-released NANA row is minted in the
same `SECX-` family.)*

**Ledger: 935 -> 1,073 rows. `Announced_Value_USD` $45,195,917,316 ->
$47,880,355,533, +$2,684,438,217. Conservation proved row-for-row: 0 of the 935
pre-merge `Deal_ID`s lost, 0 pre-merge values changed, 0 columns lost.**
`record_class` is now **PUBLIC_AWARD 654 / TRANSACTION 419** — the merge is
almost entirely transactions, which is the half of this dataset nobody else
publishes.

### The refusals, and why each is a rule

| reason | n | the rule |
|---|---:|---|
| `G7_DUPLICATE_INTERNAL` | 36 | one article reporting one dated event is one row |
| `G3_FEDERAL_AWARD_NOT_A_DEAL` | 35 | a federal contract award is `prime_contracts`, not a deal |
| `G5_PARTY_IS_PUBLISHER_NOT_TRANSACTOR` | 33 | the publisher is a prior, not a party |
| `G2_PARENTAGE_STATEMENT_NOT_A_TRANSACTION` | 24 | "is a wholly owned subsidiary of" is a standing fact |
| `G7_DUPLICATE_OF_LEDGER` | 17 | already in `deals_classified.csv` |
| `G11_ARTICLE_DATE_IS_NOT_THE_TRANSACTION_DATE` | 9 | the post date is not when the deal happened |
| `G4_MILESTONE_NOT_A_TRANSACTION` | 7 | a groundbreaking transfers nothing |
| `G1_DATE_NOT_IN_EVIDENCE` | 6 | the ledger's own bar |
| `G0_NOT_INDIAN_COUNTRY` | 2 | a place name is not a nation |
| `G6_INTRA_FAMILY_RELABELLING` | 2 | a move between sub-hubs of one nation |
| `G8` / `G10` / `V1 carrying amount` | 3 | no transaction disclosed; a registration correction; a balance-sheet figure |

### Four findings worth more than the rows

**1. A place name is not a nation, and the screen let two through.**
`FRIENDS OF SOUTH CONGAREE - PINE RIDGE LIBRARY` is a South Carolina library
group; `FRIENDS OF TEN MILE CREEK AND LITTLE SENECA RESERVOIR` is a Montgomery
County, Maryland watershed group published by `montgomeryplanning.org`. Both
entered a tier-A Indian Country deal queue on a token.

**2. The publisher-is-not-the-party test needs TWO conditions or it measures an
abbreviation.** A pure name test flagged 105 of 258 rows - and it was wrong
about most of them, because "ASRC Industrial Services Acquires Mavo Systems"
shares no token with "Arctic Slope Regional Corporation". The gate that works
requires the host to be a hand-classified third-party publisher AND the party
to be absent from the sentence. Twenty-one hosts were classified by hand with a
reason recorded for each. It keeps `oan.srpmic-nsn.gov` reporting Salt River's
own Pavilions acquisition and drops the statewide aggregator that attributed
Dell's $9.7B contract, Anthropic's $200M contract and the Coast Guard's $25B to
the Alaska village of **Craig**.

**3. A PRESENT-TENSE OWNERSHIP MAP INVERTS THE INTRA-FAMILY TEST ON A PAST
ACQUISITION.** This is the generalisable one. Bering Straits bought Alaska Gold
Company from NovaGold in 2012; Alaska Gold is a BSNC subsidiary today, so a
shared-hub test calls the 2012 purchase an internal relabelling and destroys
the very event that created the relationship. **A family map built from today's
ownership refuses exactly the acquisitions that succeeded.** The gate went
34 -> 24 -> 2 refusals across three versions; the 32 rows it stopped refusing
are real transactions, including eleven ASRC Industrial acquisitions,
UIC/Johansen Construction and Choggiung/Bristol Industries. The version that
looks correct and is not - "does the sentence name an organisation outside the
family?" - fails for the same reason: the target is inside the family by the
time the map is built. What works is reading what the passage DOES: a transfer
verb overrules the topology, a reorganisation verb confirms it, and an
identifier flip with no sentence has only the topology to go on.

**4. `cedar_constellation_edges.csv` IS NOT AN OWNERSHIP SOURCE.** All 3,153
rows carry `is_ownership_claim = N`; its tiers are `registered_with` (2,365),
`declares_service_to` (588), `managed_under_contract` (78), `located_within`
(78) and `chartered_by` (44). `code/1071_identifier_driven_deal_sweep.py` builds
its family closure from that file at every tier, and
`nest_enterprise_relations.csv` - the file that actually carries 3,613 ownership
edges - is not read by it at all. Within `nest`, `joint_venture` (157 edges) and
`passive_investment` (10) are also excluded from a family here, because a joint
venture between two families is the transaction this dataset exists to record.
An `affiliation` edge in `nest` reading *"Doyon, Limited publishes these as its
own operating companies"* makes **Huna Totem Corporation** - an independent
Hoonah village corporation - a member of Doyon's family, and cost five real
Doyon rows before it was caught.

### The terms release yielded ONE row, not three

`docs/PUBLICATION_POLICY.md` `TERMS-SCOPE`, 2026-09-02: a restriction binds what
the restricted entity published, not a third party's SEC filing about them. The
three held EDGAR families were released on that basis and the honest yield is
**one deal**:

- **NANA** - ADMITTED. Trilogy Metals' 10-K discloses Ambler Metals LLC, a
  50/50 joint venture completed 2020-02-11 with a South32 subscription of
  US$145,000,000. NANA's own consideration is a 1% net smelter royalty plus
  $755/acre and is **not** a dollar figure.
- **Southern Ute** - REFUSED, and not on terms. MACH Natural Resources carries a
  "Southern Ute Right of Work Agreement" at a gross **carrying amount** of
  $14,452 thousand. A carrying amount is not a purchase price and the filing
  gives no transaction date.
- **Chickasaw** - REFUSED. AP Gaming Holdco names the Nation in market context.
  There is no transaction in the filing.

**Say "three families released, one deal found."** Reporting the release as
three rows would be the error the release exists to avoid.

### The two unannounced ownership changes carry a WINDOW, not a date

`IDOBS-2021-001` **WHPacific, Inc.** (UEI `PTJATEQ7Q873`) moves from NANA
Regional Corporation to NV5 Global between FY2019 and FY2021, and
`IDOBS-2019-001` **Clarus Fluid Intelligence, LLC** (UEI `F2BEQJNKFY83`) leaves
its Koniag-side parent for Chestnut Park between FY2017 and FY2019. Neither is
in any Cedar source as an announcement. Both are admitted with:

- `Event_Date` **BLANK on purpose**, and `Date_Basis` saying
  *"FISCAL-YEAR WINDOW, NOT A DATE"*. A run boundary is a gap, and
  `code/1088 verify` exits 1 on a blank `Event_Date` whose `Date_Basis` does not
  say so.
- `Verification_Status` = *"UNVERIFIED AGAINST ANY PUBLISHED ANNOUNCEMENT -
  this is an observation Cedar made, not a claim a source published"*.
- `Announced_Value_USD` blank, `Value_Type` = *"No value published. Never
  inferred."*

A third identifier candidate was refused outright: UEI `H3Y4JTE3SRJ4` keeps its
identifier while `awardee_name` goes from **Blackfeet Utilities** to
**William Allen Talks About** - a personal name. An entity does not sell itself
to a person and keep its UEI. That is a registration correction, which
`docs/PUBLICATION_POLICY.md` already names as one of the three things a parent
change can be instead of an acquisition.

### 46 of `1071`'s 434 shared-brand rejections rest on a trade word

Re-tested and written to `review/deals_1088_intra_family_retest.csv`.
`INTRA_FAMILY_SHARED_BRAND` refused **Kansas State University -> George Mason
University** on the shared token `university`, and eight more on the same word;
`construction` (7), `international` (5), `industrial`, `services` and
`enterprises` did the same work. Those are trades, never brands - the ANCSA
stager's own note says *"services (a trade, never a name)"* and the brand test
does not apply that list. The other 388 rest on a real brand token
(`deloitte`, `honeywell`, `johnson|controls`, `bae|systems`) and are correct.
**Yield of the re-test: zero deal rows.** Not one of the 46 has a side matching
a Cedar spine entity by exact name, so the gate is defective and the
consequence today is nil. Recorded because it will not stay nil.

Two counts in `docs/DEALS_IDENTIFIER_SWEEP_2026-09-02.md` do not reproduce: it
states **544** intra-family rejections; the three intra-family refusal codes in
`review/1071_intra_family_rejections.csv` sum to **536** (`SHARED_BRAND` 434 +
`SAME_HUB` 100 + `ACRONYM` 2).

### G11 - the article date is not the transaction date

Every tribal-press row is dated by the site's own REST-API post date. **That is
the ARTICLE date**, and `docs/methodology/deals.md` has always said *never file
a deal by announcement year when the transaction year differs* - the same rule
that caught Paskenta/Mad River Brewery (presented as August 2026, actually March
2024) and Blue North Fisheries (framed as 2025-26, actually effective
2019-09-30).

Measured on the admitted set: **14 of 96 press rows carried a sentence naming a
year two or more before the year they were filed under.** But a retrospective
year is not by itself a defect - *"Chugach Commercial Holdings: Established in
2014"* inside a 2026 acquisition announcement is background, and refusing that
row would lose a real 2026 transaction over a date that is not its date.

**So the gate is narrow: it fires only when the earlier year sits within 60
characters of a TRANSFER VERB**, which is where a transaction year lives in a
sentence and where a founding year does not. It refuses 9. *"BSNC acquired the
Alaska-grown company in August of 2015"*, filed 2020, is refused. The Chugach
background year is kept, and its `Date_Basis` is extended to say the article
date is **not known to be the transaction date** and to name the other year -
so a blank is never mistaken for a confirmed date.

Six of the nine had already been merged when G11 was written. They were
**withdrawn WHOLE** to `review/deals_withdrawn_duplicates.csv`, which went 3 ->
9 rows and which `88_build_deals_taxonomy.withdrawn_ids()` honours on every
rebuild - the same route `MA2020-008` took, and for the same reason: *withdrawn
is not deleted.* They carried **$0**, so no total moved.

### The value rule, applied

`Announced_Value_USD` is for CONSIDERATION. Two staged sums named a facility
ceiling in their own `value_basis` and were **moved** to
`Project_Total_Value_USD`, totalling $58,500,000 - Lytton Rancheria's $51.0M
unsecured term facility to Cadiz Inc. and Bristol Bay Industrial's $7.5M
delayed-draw facility to Alaska Communications. The row survives; the total does
not lie. **The $151,000,000,000 IDIQ ceiling never reached the value gate at
all** - it was refused a step earlier by `G3` as a federal contract award, which
is what it is.

---

## 6. What a buyer may total

- `Announced_Value_USD` over all 935 rows = **$45,195,917,316.** [measured] It
  is additive at deal-event grain, keyed on `Deal_ID`.
- **Never sum any `deals_*_additions.csv` file alongside
  `deals_classified.csv`.** The nine staging slices carry **$22.67B of that
  same money** (790 of 935 rows). All nine are individually safe to aggregate
  and **no two of them are safe together.** This is the largest
  double-counting path in the dataset.
- **618 of 935 rows carry a `Value_Type` naming a FEDERAL award — $6.87B that
  Cedar already ships in `funding` and `contractors`.** A deal announcement and
  the obligation behind it are one dollar.
- **`Project_Total_Value_USD` sums to $11,423,670,087 and is a different
  concept.** It is where excluded and parent values are parked so they cannot
  double-count. Never add it to `Announced_Value_USD`.
- **SEC filings yield multiple events on one instrument** (issue → exchange →
  restructure). Four such pairs are flagged in the rows' Notes. **Summing
  blind overstates capital raised.**
- **`tribal_resolution_financings.csv` has no money column at all.**
  `principal_amount_text` and `pledged_revenues_text` are free text and both
  are blank on the only row; `financing_status = AUTHORIZED` on the whole
  table, because *a council resolution PERMITS a transaction, it does not close
  or fund one*. Never sum it with `nigc_declination_letters.csv`,
  `gaming_financing_events.csv` or `tribal_bond_issuances.csv` —
  `nigc_cross_reference_basis` exists precisely so that an authorisation and an
  NIGC review of one transaction are not counted as two.
- **`seminole_bond_disclosures.csv` must not be totalled.** Its 29 rows mix
  bond par with federal-awards-expended: 11 rating-agency actions, 10 Single
  Audit reporting packages (whose `amount_concept` is verbatim *"total federal
  awards expended (NOT revenue, NOT gaming; the Single Audit threshold
  measure)"*), 7 term loans or bonds named in a registered fund's holdings, and
  1 EMMA record. The $3,556,464,983 sum of those is meaningless.

---

## 7. Known limits

- **Never chart "deals by year" without splitting negotiated transactions from
  federal awards.** `record_class`: PUBLIC_AWARD 653 / TRANSACTION 282.
  `transaction_type`: Grant or Public Award 653 · Acquisition 170 · Divestiture
  19 · Debt Issuance 19 · UNCLASSIFIED 19. `capital_source`: Federal 758 /
  Private 119 / UNCLASSIFIED 56 / Philanthropic 2. [measured]
  **The federal-award share is 0% before 2010 and swings to 85% (2019), 97%
  (2022), 93% (2024) and 35% (2026). That swing tracks when TBCP and HUD ran
  competitive rounds, not Indian Country deal activity. A combined series shows
  a hockey stick that is pure source composition.**
- **Reachability tracks whether an entity had PUBLIC DEBT, not deal age.**
  2000–2005 yielded 11 rows — more than 2010–2017 managed in eight years. **The
  genuine soft spot is 2010–2017: too recent for dense SEC coverage, too old
  for newsrooms.** 2000 is the hard year (1 row). Year distribution: 2000–2009
  averages about 4 rows a year; 2019: 75, 2022: 186, 2024: 177, 2026: 91.
  [measured]
- **`Verification_Status`**: Primary verified 553 · Verified 331 · Primary +
  independent verified 18 · Independent secondary corroborated 5 · Primary
  verified (rating agency release) 5 · **Needs federal award-ID verification
  3** · Secondary corroborated 2 · Secondary verified 2. `Confidence`: High
  676 / Medium 259, **no Low rows**. [measured]
- **`Date_Basis` is honest about award-list PDFs**, and a reader should read
  it. Verbatim values include *"PDF creation date of the corrected HUD award
  list (2019-12-16). NOT an award action date."* (51 rows) and *"Announcement
  date (NTIA recommended-for-award release); award action date not published"*
  (48 rows). 223 rows are `Announcement date (NTIA release)`; only 56 are
  `Transaction/award date`. [measured]
- **`ownership_events.csv` (98 rows) is a derivative and carries the ledger's
  limits plus its own.** Acquisition 94 / divestiture 4; `entity_id` on 77,
  `tribe_id` on 93; tier A 77 / B 16 / X 2 / blank 3; 97 of 98 `source_deal_id`
  values resolve into `deals_classified.csv`; $5,345,966,000 in
  `announced_value_usd`; and **`ownership_change_type` is free text with 47
  distinct values across 98 rows** — not a controlled vocabulary. [measured]
  `docs/OWNERSHIP_CHANGE_DETECTION.md` names four things that make the
  parent-change signal lie: the observed date is **not** the transaction date
  (FPDS does not update retroactively and the lag can be years); **FY2022 is
  contaminated** — 37 transitions against a ~15/year baseline, because **DUNS
  was retired for UEI on 2022-04-04**, a mass re-identification event; a parent
  change is not a sale; and the method detects, it does not establish.
- **The floor is archival, not statutory.** Nothing forbids a 1995 row; what is
  missing is a source that reliably reports one. **This is the one dataset
  where a coverage gap and a real absence of activity are genuinely hard to
  tell apart**, which is why it carries `pre_2000_flag` rather than a hard
  cutoff.
- **Three redundant columns are shipped and three informative ones are not.**
  `Status`, `Event_Type` and `Record_Scope` overlap (`Event_Type = Awarded` /
  `Status = Awarded`), and `Record_Scope` reads `2000 commitment` — the year
  plus a word, which no buyer will guess distinguishes commitment-year from
  event-year. Meanwhile `Description` (935), `State` (805), `cedar_uid` (886)
  and `Announced_Value_USD` (835) are on the table and are not in the shipped
  sample.
- **583 of 935 rows are `Awarded` federal grant announcements** (NTIA TBCP, HUD
  ONAP). A buyer expecting an M&A ledger gets a grants list. That is a
  composition fact worth stating in the README, not a defect.

---

## 8. Refresh

| source | cadence | Cedar holds through | due |
|---|---|---|---|
| Press, trade and tribal announcements | **continuous — deals ARE discovery**; 0–14 days from announcement to findable | 2026-08-20 | source edge **not establishable** — *there is no index to probe; a deal is current when someone looked* |
| SEC EDGAR full text | continuous, same-day on acceptance | **2017-05-21** | **YES — reachable, never swept past 2017 (3,391 days)** |
| ANCSA portal + ANC annual reports | annual, 3–9 months after corporate FY end | 2026-02-09 | no |
| Tribal debt (EMMA, official statements) | continuous on issuance; continuing disclosure annual | 2021-01-26 | not re-probed |

[measured — `docs/REFRESH_CADENCE.json`, regenerated 2026-09-02]

**Operating cadence: a weekly newsroom sweep, and a quarterly deep pass with
one historical year backfilled — REVERSE-CHRONOLOGICALLY.**

**What breaks if it is not re-pulled: LINK ROT, and it is unique to this
dataset.** *This is the one collection where delay destroys evidence.* The
sourcing coverage measured above (935/935 rows sourced, 651 with two URLs) is a
**coverage fact about the ledger as it stands, not a claim that every URL still
resolves.**

**What breaks in the pipeline:** `deals_party_attribution.csv` holds the
owner's rulings, and **an upsert must never overwrite a human ruling.**
`code/126` is an in-place enricher and must run after any rebuild;
`py -3 code/build.py plan deals` prints the ordering.

**Two named, costed expansions exist and neither needs a key:** the EDGAR
full-text years either side of the 2010–2017 sweep (FY2001–2009 and
FY2018–2026), and the **ANC annual-report archive depth — the highest-value
unmeasured upstream in the dataset**, because ANC reports are the one source
that states a transaction the press did not cover.

---

## Stale claims found while writing this

1. **`docs/datasets/01_deals.md` reports the collection BLOCKED on a blocker
   that no longer exists.** It says *"C8 rebuild is DESTRUCTIVE
   (88_build_deals_taxonomy.py) — no safe documented rebuild path"* and
   *"88 is on `cedar_pipeline.NEVER_RUN`."* **`88` was fixed and removed from
   `NEVER_RUN` on 2026-09-01** (workstream C8), proven by
   `code/812_c8_rebuild_proof.py`. `cedar_pipeline.NEVER_RUN` now contains
   **only `41_build_codebooks.py`**; `88` sits in `RETIRED_FROM_NEVER_RUN`. The
   scoreboard regenerated 2026-09-02 rates `deals` **READY**.
2. **`docs/WS5_GRAIN_AND_SOURCES.md` §4 says the correct posture is *"keep it
   in `NEVER_RUN`"* for `88`.** Superseded within the same day by the C8
   workstream. Two workstreams on one day with no cross-reference.
3. **`data/clean/deals_taxonomy.csv` is a 790-row-era census that was never
   re-measured after the 153 and 155 merges.** Every one of its 48 `n_deals`
   values is low: sector Gaming 48 (now **77**), Broadband 280 (**287**),
   Housing 226 (**235**), Energy 67 (**81**), Federal Contracting 28 (**41**),
   Transportation 53 (**77**); `transaction_type` Acquisition 122 (**170**),
   Divestiture 16 (**19**), Debt Issuance 16 (**19**). Its `built_date` is
   2026-08-06.
4. **`docs/datasets/01_deals.md`'s "NEVER do these" section quotes 622 grant
   rows against 116 acquisitions.** It is **653 against 170**. The conclusion
   survives; the numbers are the 790-row era.
5. **`docs/COVERAGE_AUDIT.md` still says 790 deals in two places.** It is 935.
   Already flagged in the contradictions register and still unfixed.
6. **`docs/DEALS_BUILD_LOG_2026-08-26.md` and `code/153`'s docstring say
   `deals_2026_ytd.csv` holds 76 rows.** It holds **90** — 76 plus the 14 that
   `155` appended in the same session. A reader reconciling 76 + 56 = 132
   against a 90-row file will lose time.
7. **`code/154`'s docstring says THREE proposals were refused.** The build log
   and the file both say **four**. The docstring predates the fourth.
8. **`docs/WS5_GRAIN_AND_SOURCES.md` §3 gives 61 distinct source hosts and 662
   `.gov` rows.** Counting both source columns gives **92 hosts and 665 `.gov`
   rows**, and `broadbandusa.ntia.gov` is **494**, not 272. The difference is
   method, not error — WS5 almost certainly counted `Source_1` only — but **the
   doc does not say which column it counted, so its figures are not
   reproducible as written.**
