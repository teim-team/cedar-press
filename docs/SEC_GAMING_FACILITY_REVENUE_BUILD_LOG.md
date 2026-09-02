# SEC-filed per-facility tribal gaming money — build log

*Written 2026-09-02 by workstream **SEC-GAMING**, `code/1080_sec_gaming_facility_revenue.py`.
Every figure in this document was re-counted from the live files on that date. Nothing was
fetched: the corpus was already on disk.*

**Companion documents.** The totalling rules are in `docs/MONEY_TOTALLING_RULES.md` under
`<!-- BEGIN SEC-GAMING -->`; the grain and primary keys are declared in
`code/512_build_dataset_contracts.py` as `GRAIN_SEC_GAMING`; the corpus and its fetch
discipline belong to `code/1030_sec_edgar_native_transactions.py`.

---

## What this answers, and what it does not

`docs/methodology/gaming.md` opens with a claim that is true and stays true:

> **Per-facility gaming revenue does not exist publicly, and no amount of collection effort
> will produce it.**

NIGC publishes gross gaming revenue by region and in bands, never per operation. Cedar
records that as `SOURCE_DOES_NOT_PUBLISH`. **13,494 of the 13,803 rows in
`gaming_revenue_bounds.csv` are a `REGIONAL_GGR_CEILING`** — one ceiling for a whole NIGC
region, repeated on every property in it — and only 176 rows across **11 of 787 rows**
are an honest per-property figure.

There is one route around the regulator, and it is narrow: **a company that manages,
develops or operates a tribal casino and files with the SEC must disclose the economics of
that contract.** Where the tribal gaming authority is itself the registrant, it reports the
property's revenues directly. Where a public manager holds the contract, it reports its fee.

This build worked that route to its end on the cached corpus and reached **7 distinct
Indian-lands properties — 0.9% of 787 ROWS, 0.98% of the 714 distinct properties.** *(**GAMING-DENOMINATOR-2026-09-02:** `gaming_facilities.csv` holds **787 ROWS, not 787 facilities** — 16 rows' NAMES say no casino (7 exactly, 9 like `Grand Canyon West - no casino`) and 57 extra rows sit across the same-tribe duplicate groups, so **771 facility rows and 714 distinct properties**. Five denominators circulated on 2026-09-02 — 787, 780, 734, 727, 714 — and only the last is the property count. Authority: `code/846_session_audit.py::_denom`; derive it with `py -3 code/1116_ruling_propagation_2026_09_02.py derive`.)* That is the honest headline. What it adds is not
breadth but **duration and evidentiary weight**: Mohegan Sun across 15 distinct fiscal years,
each figure filed under federal securities law with an accession number and a verbatim quote.

---

## The corpus, and why nothing was fetched

`code/1030` had already cached **1,172 filings (1.1 GB)** at
`data/raw/external/sec_edgar_1030/` and mined 3,674 passages naming 95 Native entities. Its
own report named the largest thing left on the table — over a thousand Lakes Entertainment
passages, mined but unread.

`1080 mine` reads **1,169 of those documents that are present on disk**, keeps the
**609** filed by one of **16 curated gaming registrants** (`code/_1080_facility_aliases.py`),
converts each to text and applies five anchored patterns. Zero network calls in any stage.

| registrant | CIK | role | cached docs |
|---|---|---|---:|
| Lakes Entertainment, Inc. | 1071255 | developer/manager | 140 |
| Nevada Gold & Casinos, Inc. | 277058 | developer/manager | 102 |
| Mohegan Tribal Gaming Authority | 1005276 | **tribal instrumentality, own registrant** | 92 |
| Full House Resorts, Inc. | 891482 | manager | 78 |
| Empire Resorts, Inc. | 906780 | developer/manager | 77 |
| Red Rock Resorts (Station Casinos) | 1653653 | manager | 26 |
| Butler National Corporation | 15847 | manager | 25 |
| Waterford Gaming, L.L.C. | 1028911 | relinquishment-interest holder | 22 |
| Seneca Gaming Corporation (+3 subsidiaries) | 1296785, 1296783/4/6 | **tribal instrumentality, own registrant** | 19 |
| Venture Catalyst Incorporated | 318291 | manager | 15 |
| Century Casinos · Caesars (2 CIKs) | 911147, 858339, 1590895 | manager | 23 |

---

## What came out

**`data/clean/sec_gaming_financial_disclosures.csv` — 67 rows.**
**`data/clean/sec_gaming_management_contract_terms.csv` — 7 rows.**

| property (`gaming_facilities.csv`) | tribe | state | years | what is known |
|---|---|---|---|---|
| **Mohegan Sun** `CCP-45100` | Mohegan Tribe | CT | **2000–2022, 15 distinct years** | FY2015–FY2022 net revenues from MTGA's own 10-K segment tables; CY2000–CY2006 gross revenues *derived* from the 5% relinquishment fee |
| **Graton Resort & Casino** `CCP-638700` | Federated Indians of Graton Rancheria | CA | 2018–2022 | Red Rock's management fee, plus net income *derived* at the stated 27% for 2018–2020 |
| **Seneca Allegany Casino & Hotel** `CCP-635600` | Seneca Nation of Indians | NY | 2005–2007 | net revenues FY2005, FY2006, nine months to 2007-06-30; net gaming revenue for two quarters |
| **Seneca Niagara Casino & Hotel** `CCP-565900` | Seneca Nation of Indians | NY | 2005–2006 | net revenues FY2005, FY2006 |
| **Gun Lake Casino** `CCP-637500` | Match-e-be-nash-she-wish Band | MI | 2017–2018 | MPM's management fee, excluding reimbursables |
| **Red Hawk Casino** `CCP-743100` | Shingle Springs Band of Miwok Indians | CA | 2012–2013 | Lakes' management fee, sole-sourced to this property by the filer |
| **FireKeepers Casino Hotel** `CCP-658400` | Nottawaseppi Huron Band of Potawatomi | MI | 2009 | Full House's management fee, nine months |
| *Mohegan Sun Pocono* `VP-0034` | Mohegan Tribe | PA | 2015–2021 | **not Indian-lands gaming** — a Pennsylvania racino MTGA owns. Kept and flagged `facility_is_on_indian_lands = N` |

Six tribes. Seven Indian-lands properties. `MGE Niagara Resorts` (Ontario) was mined,
rejected as out of universe, and the rejection is recorded rather than silent, so a reader
of MTGA's segment table can see why the segment lines do not add to the tribal properties.

---

## The best single find: a stated rate over a stated base

**Waterford Gaming, L.L.C. (CIK 1028911) files 10-Ks carrying Trading Cove Associates'
audited financial statements, and those state, to the dollar, the 5% relinquishment fee TCA
earned on Mohegan Sun's revenues for every year 2000–2006.** The same filings define the
base:

> the Authority agreed to pay to TCA a fee (the "RELINQUISHMENT FEES") **equal to 5 percent
> of Revenues, as defined in the Relinquishment Agreement, generated by the Mohegan Sun**
> … Revenues [is] defined in the Relinquishment Agreement as **gross gaming revenues (other
> than Class II gaming revenue) and all other facility revenues**

| filer's label | fee earned, as filed | ÷ 0.05 → Mohegan Sun Revenues as defined |
|---|---:|---:|
| 2000 | $41,003,849 | $820,076,980 |
| 2001 | $45,715,318 | $914,306,360 |
| 2002 | $58,508,703 | $1,170,174,060 |
| 2003 | $65,099,553 | $1,301,991,060 |
| 2004 | $69,101,491 | $1,382,029,820 |
| 2005 | $72,964,466 | $1,459,289,320 |
| 2006 | $76,258,408 | $1,525,168,160 |

Three cautions travel with every one of those rows and are written into
`derivation_caveat`:

1. **This is a gross measure, not MTGA's reported net revenues.** It is before promotional
   allowances and excludes Class II. It must not be plotted as one series with the
   `FACILITY_NET_REVENUES` rows for the same property from MTGA's own 10-Ks.
2. **The period label is the filer's.** Each total is labelled *"Relinquishment Fees earned
   `<year>`"* and tabulated against four payment dates running April of that year to January
   of the next; the fee splits into senior and junior halves of 2.5% each and is paid in
   arrears. The twelve months of trading the total is 5% *of* is not necessarily the calendar
   year named. Cedar records the label and does not re-date it.
3. **Two figures are typed two ways inside the corpus.** The 2004-03-26 10-K writes
   $65,099,5**3**3 in one sentence and $65,099,5**5**3 in another; the 2007-03-21 10-K writes
   $72,964,4**4**6 and $72,964,4**6**6. In both cases the tabulation and the later filings
   agree on the second spelling, which is what is recorded — and the variant is noted on the
   row rather than quietly resolved.

---

## The correction this workstream owes its own premise

The mandate said *"under IGRA a management contract caps fees at a share of net revenues, so
the fee frequently implies the revenue."* The first half is right. **The second half is
wrong, and it is wrong in a way that would have produced confident, badly mislabelled
numbers.**

IGRA defines "net revenues" at **25 U.S.C. § 2703(9)** as gross gaming revenues *less*
amounts paid out as prizes and *less* total gaming-related operating expenses, excluding
management fees. That is much closer to **operating profit** than to revenue. And the
contracts here do not share one base:

* Lakes / Shingle Springs, Red Hawk: *"a management fee equal to 30% of net revenue (as
  defined by the development and management agreement)"*
* Red Rock / Graton: *"24% of Graton Resort's **net income** (as defined in the management
  agreement) in years 1 through 4 … 27% … in years 5 through 7"*
* Lakes / Pokagon, Four Winds: *"24% of net income up to a certain threshold and 19% on net
  income over that threshold"*
* Lakes / Iowa Tribe, Cimarron: *"30% of net income from operations **in excess of $4
  million**"*
* Waterford / TCA, Mohegan Sun: *"5% of Revenues"*, where Revenues is defined as the
  property's gross gaming plus all other facility revenue

Dividing a fee by its rate recovers **that contract's own base and nothing else**. So the
derived rows are typed `DERIVED_FACILITY_GROSS_REVENUES_AS_DEFINED` and
`DERIVED_FACILITY_NET_INCOME_AS_DEFINED`, never plain "revenue", and `1080 verify` V10 exits
1 if a derived figure is given a reported figure's type.

**Of the 8 distinct (property, rate) formulas found across 51 statements, only two supported
a derivation.** The other six were refused and the refusals are in the adjudication file:
Four Winds' threshold is undisclosed; Cimarron's fee sits above a $4m floor; Buena Vista's
casino never opened under that agreement; Gun Lake's rate is *never stated* — the "30% of
the facility's net income" in the same Red Rock 10-K belongs to the **North Fork** project;
and one apparent FireKeepers term is the **statutory NIGC ceiling** recited in a
regulatory-background section, not that contract's fee.

---

## What the patterns got wrong, and how it was caught

Every candidate was read against its own quote before it was accepted. **69 of 143
adjudications are refusals**, and the refusal reasons are the useful part of this log.

| refusal | n | what happened |
|---|---:|---|
| `REJECT_RESTATEMENT_SAME_EVIDENCE_FAMILY` | 47 | the same figure or the same contract term repeated in a later filing by the same registrant. A copy is not a corroboration (`docs/ASSERTION_LAYER.md`) |
| `REJECT_NOT_A_US_TRIBAL_FACILITY` | 9 | MGE Niagara Resorts, Ontario |
| `REJECT_WRONG_PROPERTY` | 4 | Full House distributions from the **Delaware** racino (Harrington), captured because "FireKeepers" appeared in the preceding sentence. This is the containment defect in a new dress |
| `REJECT_INTRA_FILING_DUPLICATE` | 3 | Red Rock states the Graton fees twice in one 10-K, once in a risk factor and once in the revenue note |
| `REJECT_WRONG_KIND_OF_FEE` | 2 | **construction** management fees *paid by* the Seneca gaming corporations to a contractor. The words "management fee" were doing all the work |
| `REJECT_DELTA_NOT_LEVEL` | 1 | Lakes' Grand Casino Avoyelles fee *"increased approximately $5.6 million"* — a year-over-year change booked as if it were a level |
| `REJECT_WRONG_NUMBER_IN_SENTENCE` | 1 | the pattern took $302,141, which is a **food-and-beverage decrease**, from a sentence whose real FireKeepers figure was $5.8 million. Re-entered by hand as `MANUAL-0003` |
| `REJECT_PERIOD_MISREAD` | 1 | the period lookback reached forward into the *next* sentence and stamped 2019 on a 2018 Gun Lake figure |
| `REJECT_STATUTORY_CEILING_NOT_A_CONTRACT_TERM` | 1 | "30% of net revenues" recited from 25 U.S.C. 2711, read as if it were the contract's fee |

### Four parser defects worth keeping, all of the house pattern

`docs/AGENT_FIELD_GUIDE.md` §3 names this repo's signature defect: *a check that does not
measure its own name*. Four instances happened here, and each is now a comment at the site.

1. **`[^.]` cannot read a financial statement.** The MD&A pattern used `[^.]{0,140}` to stay
   inside a sentence and matched **nothing across 609 documents**, because every figure in
   this prose carries a decimal point — *"declined by $77.0 million, or 7.2%, to $992.0
   million"*. It was producing zero rows and looking like a corpus with no MD&A in it.
2. **A year header is not a period.** The first segment-table parser accepted any line
   holding two four-digit years. On a 10-Q the columns are *"Three Months Ended June 30,
   2017 / 2016"* and *"Nine Months Ended…"*, and it stamped every one of them `fiscal year
   2017` — **102 of 132 rows were quarterly figures wearing an annual label**, and one was
   `11,200`, a percentage cell read as dollars. The parser is now 10-K only and the header
   must *say* "Years Ended `<Month> <Day>`". It refuses 17 tables for that reason and prints
   the count.
3. **A quote that contains no number is not evidence.** The segment quote pasted six
   preceding lines and truncated at 1,600 characters; on two Mohegan 10-Ks those six lines
   were MD&A prose and the figure fell off the end. The quote is now exactly the four lines
   that decided the reading — period header, year header, section header, property row.
4. **An optional prefix moved the anchor.** The narrative pattern optionally consumed
   *"For Fiscal 2006, "*, which pushed `m.start()` past the only period cue in range, so six
   Seneca rows came out with a figure and no fiscal year.

A fifth was a performance defect with the same shape: the "…respectively" pattern led with
`.{0,320}?`, which made the engine try 320 prefix lengths at every offset and pushed the
mine stage past ten minutes on one filer. It now anchors on the word `respectively` and
reads a fixed window backwards — same 22 rows, one pass.

---

## A finding about the denominator, handed to the gaming owner

Keying eight properties to `gaming_facilities.csv` surfaced something that
affects every "of 787" percentage in the gaming dataset, this document's
included.

**`gaming_facilities.csv` carries the same property twice for a large number of
properties, and `duplicate_of_facility_id` is blank on both rows.** Measured
2026-09-02 on the live file, grouping on (facility name with `casino`, `resort`,
`hotel` stripped, state):

| | |
|---|---:|
| name+state groups holding more than one row | **58** |
| rows in those groups | **119** |
| groups where `duplicate_of_facility_id` is blank on **every** row | **54** |
| rows in those groups carrying `duplicate_risk = 1` | 60 |

The pattern is consistent: a `CCP-` row from Casino City beside a `VP-` row from
the voting-patterns canonical list - `CCP-565900` / `VP-0029` for Seneca
Niagara, `CCP-635600` / `VP-0030` for Seneca Allegany, `CCP-639000` / `VP-0295`
/ `CEDAR-FAC-000013` for Four Winds New Buffalo, `CCP-305300` / `VP-0153` for
The Stables. `duplicate_risk` already flags 60 of the 119 rows, so the signal
exists; what is missing is the pointer that would let a consumer collapse them.

**Nothing here was written to `gaming_facilities.csv`** - that table belongs to
the gaming universe workstream. This build keys to the `CCP-` row wherever one
exists, because that is the row carrying `has_revenue_bound` and the capacity
observations, and it lists the near-duplicates it knows about in
`NEAR_DUPLICATE_IDS` in `code/_1080_facility_aliases.py` so no consumer counts
one property as two.

**Effect on this document's own headline:** if the true property universe is
nearer 729 than 787, the 7 properties reached are **0.96%** rather than 0.9%.
The claim does not move. It is stated here because a percentage whose
denominator is under suspicion should say so.

---

## Gates

```
py -3 code/1080_sec_gaming_facility_revenue.py mine      # zero network, ~4 min over 609 docs
py -3 code/1080_sec_gaming_facility_revenue.py build     # joins review/sec_gaming_1080_adjudication.csv
py -3 code/1080_sec_gaming_facility_revenue.py codebook  # writes the two fragments
py -3 code/1080_sec_gaming_facility_revenue.py verify    # exits 1 on breach
py -3 code/1080_sec_gaming_facility_revenue.py selftest  # proves verify FIRES
```

`verify` holds sixteen named invariants (`V0`-`V15`; `V13` and `V15` each carry a measurement arm and a breach arm). `selftest` injects a violation of four of them
(`V3_FENCE_DECLARED`, `V4_FIGURE_TYPE_VOCAB`, `V5_QUOTE_PRESENT`, `V10_DERIVED_LABELLED`),
asserts exit 1 **and** that the named invariant is what fired, restores, and asserts exit 0.
All four pass. Two invariants are measurements rather than pass/fail:

* **V13** counts the facilities carrying both an SEC figure here and a `REGIONAL_GGR_CEILING`
  bound — **7 of 8**. That overlap is expected and is precisely why `not_summable_with` names
  `gaming_revenue_bounds.csv`.
* **V15** counts restated facts and whether they agree — **32 restatements, 0 disagreements**.
  That is the only genuine internal corroboration this table has, and it is worth more than
  any of the flags: three separate Mohegan 10-Ks state the same FY2017 figure to the dollar.

---

## Gate 62, honestly

`py -3 code/62_no_regression_check.py` was RED when this pass finished, with
twenty-odd regressions. **Standing rule 15 says do not record that as
"pre-existing, not mine" and walk on**, so here is the attribution, measured.

**Not this workstream's.** Every `lint_class*` rise was checked against
`293_lint_bug_classes.py` output filtered to `1080` and `_1080`: **no class
carries an instance from any file this pass wrote.** The one class-7 instance
1080 *did* create - a positional `candidate_id` - was found by 293 during the
pass and fixed before the tables shipped (the id is now a content digest; see
the comment at the site). `rulings_unapplied` 1,215 -> 2,894,
`advocacy_passthrough_2026-08-07.csv` disappearing from `data/clean`, and the
`hearing_bill_links` / `native_bills_subject_sweep` shipping drops belong to
other workstreams running the same night and are untouched here.

**This workstream's, and what closes them.** Two new tables in `data/clean`
count against the codebook family of ratchets until the master learns about
them:

* `tables_undocumented_in_codebook`, `tables_missing_codebook_block`,
  `tables_missing_notes_contract`, `ship_tables_at_zero`,
  `tables_missing_from_25_TABLES`, `tables_missing_from_27_SPEC` - **2 of each
  rise is ours.** `1080 codebook` has written the two fragments
  (`07zq_sec_gaming_financial_disclosures`, `07zr_sec_gaming_management_contract_terms`,
  51 and 31 variables, every column described). **The fold into
  `codebook_master.csv` is `py -3 code/cedar_codebook.py build` and is the
  integrator's call**, because it folds every agent's in-flight fragment at
  once and `build()` refuses to shrink.
* `contract_orphan_shippable` - both tables would have been orphans, because
  they deliberately do not wear the `gaming_` prefix. `sec_gaming_` was added to
  the `gaming` collection's table regex in `500_build_architecture_map.py`.

Nothing was re-baselined. `--baseline` is a floor, not an acknowledgement button.

---

## Publication basis

Every row is `record_scope = PUBLISHABLE` on one ruling:
`docs/PUBLICATION_POLICY.md` `<!-- BEGIN TERMS-SCOPE -->` — *"a terms restriction attaches to
the source that stated it"*, and an SEC filing is the **registrant's** publication, made under
a federal disclosure obligation, not the tribe's. No hard-listed source's own publication was
read for this build.

---

## What is left

* **Empire Resorts (77 cached docs) and Nevada Gold (102) yielded no per-facility figure**,
  and that is a fact about them rather than a gap: both were developers of projects that had
  not opened. Nevada Gold's Buena Vista agreement is in the terms table with no dollars
  against it, correctly.
* **Butler National (25 docs) manages The Stables for the Modoc and Miami Tribes and never
  states a property revenue or a fee dollar** in the cached filings — read and confirmed, not
  assumed.
* **Venture Catalyst's Barona consulting fee is a formula over gross monthly revenues less
  expenses and tribal draws, with the components undisclosed.** Not derivable. The filings do
  describe Barona's economics in prose and are worth a slower read than this pass gave them.
* **Mohegan's own 10-Ks are cached only for FY2017, FY2018, FY2019, FY2021 and FY2022**
  (the 2020-12-29 item in the cache is an exhibit, not the FY2020 annual report). FY2015,
  FY2016 and FY2020 are covered anyway, because each 10-K restates its two prior fiscal
  years - the same mechanism that makes 32 of the 67 rows restatements. **FY2023 onward,
  and everything before FY2015, are genuinely absent** and are one targeted fetch away.
* **Seneca Gaming filed 10-Ks through 2010 and the cache holds only three of them.** Seneca
  Buffalo Creek opened in 2007 and has no revenue figure here at all.
* **Municipal disclosure is the parallel route and is not ours.** Tribal gaming authorities
  that issued public debt file continuing-disclosure reports on EMMA carrying property-level
  operating data — often for tribes that never touched EDGAR. That route is owned by the
  tribal-debt workstream; this build stopped at the SEC boundary deliberately.
