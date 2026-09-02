# Deals Build Log — base-ledger merge + August 2026 collection, 2026-08-26

Dataset 1 (Indian Country Deals). Two jobs: repair a three-week-old input defect,
then sweep the window it had been hiding.

**Result: `deals_classified.csv` 790 → 935 rows, 886 entity-linked (94.8%).
`62_no_regression_check.py` clean, no FELL lines.**

---

## 1. THE DEFECT: an additions file is meaningless without the base it adds to

`88_build_deals_taxonomy.py` built the master from exactly one input:

```python
glob(data/clean/deals_*_additions.csv)
```

Checked by Deal_ID, not assumed. **All eight additions files were already fully
merged** — 594 + 42 + 40 + 34 + 30 + 28 + 16 + 6 = **790, the entire master.**
Not one row of the two ROOT ledgers was in it:

| file | rows | in master |
|---|---:|---:|
| `deals_2026_ytd.csv` | 76 | **0** |
| `deals_historical_2020_2025.csv` | 56 | **0** |

That is why a 790-row deals ledger carried **one** row dated 2026 — `ANCSA2-2026-001`,
which arrived through the ANCSA portal harvest, not through the 2026 YTD file.

`docs/FACT_CHECK_2026-08-06.md` finding **B-1** named this exact miscount three weeks
earlier. It kept propagating because nothing connected the fact-check to the code.

**The glob is now fixed in all three places it appears**, which is the only thing that
stops it recurring:

| script | was | now |
|---|---|---|
| `88_build_deals_taxonomy.py` | additions only | base ledgers **+** additions |
| `57_autoresolve_deal_parties.py` | additions only | base ledgers **+** additions |
| `41_build_codebooks.py` (`01_deals`) | additions only | `deals_classified.csv` |

`88` also now honours `review/deals_withdrawn_duplicates.csv`. Script 54 deliberately
leaves a withdrawn row in its source file, so **every consumer must skip it or the
double count returns on the next rebuild**. `MA2020-008` is live in
`deals_historical_2020_2025.csv` right now and would have come straight back.

### The merge — `153_merge_base_ledgers_into_classified.py`

131 of 132 rows merged. Backed up first, `.part` then rename.

**One row withdrawn, not merged: `MA2020-008`.** Same Calista Corporation / Nordic Well
Servicing transaction, same 2020-01-01 effective date, as `ANCSA2-2020-004` already in
the master. It was already sitting unruled in `review/deals_duplicate_candidates.csv`
row 3. The survivor is the audited one — Calista's annual report filed with the Alaska
Division of Banking and Securities, stating consideration of **$58,355,884**; MA2020-008
is a newsroom release with no value at all. Audited filing outranks newsroom release on
dating and value, the precedent script 54 set on Northbank. The withdrawn row went whole
to `review/deals_withdrawn_duplicates.csv` and **its newsroom URL was carried onto the
survivor's blank `Source_2`**, so nothing retrieved was lost.

Only one field was derived: `Event_Quarter`, which `deals_2026_ytd.csv` does not have
and which follows from `Event_Date` with no judgement. No value, date or identifier was
transformed — including the 52 float-formatted `Announced_Value_USD` strings, because
the master already carries 521 of them and "normalising" would be a change with no reader.

---

## 2. RE-RUNNING THE RESOLVER TO WIDEN ITS INPUT LOSES WORK. IT WAS REJECTED.

The obvious follow-up to fixing 57's glob is to re-run 57. **Measured, it regresses.**
57 rebuilds its whole output from the CURRENT spine, and the spine has grown 952 → 1,310
since 57 last ran on 2026-08-06:

```
Confederated Salish and Kootenai Tribes  TRBF-CSKTFR-00 -> TCU-SLSHKT-00
Confederated Tribes of Warm Springs      TRBF-FSCWSA-00 -> TRBF-WRMSPR-00
Keweenaw Bay Indian Community            TRBF-KWNWBY-00 -> TCU-KWNWB1-00
United South & Eastern Tribes, Inc.      TRBS-ECSIUT-00 -> ITO-NTDSTH-00

4 parties LOST outright, 4 silently repointed —
two of them from a tribal government onto that tribe's COLLEGE.
```

Same shape as the `09_import_rulings.py` hazard, arriving through a third script. The
run is kept as evidence at
`data/clean/deals_party_autoresolved.csv.rerun57_2026-08-26_REJECTED` and merged
**additively** by `154_extend_autoresolved_parties_additive.py`, which may only ADD a
party the authoritative file does not already hold and asserts a guard afterwards:
`lost: 0  repointed: 0`.

### Four proposals refused by hand — `review/deals_party_refused_2026-08-26.csv`

Every new proposal was read one at a time against the raw spine. Four are the containment
defect:

| party | proposed | why refused |
|---|---|---|
| Riverside San Bernardino County Indian Health Inc | `UIO-HEALTH-00` | that is **"Native Health", Arizona**; the party is Californian. The exact "Denver Indian Health → Native Health" failure in AGENTS.md |
| Department of Hawaiian Home Lands | `NHO-HAWAII-00` | DHHL is a **department of the State of Hawaii**; NHO-HAWAII-00 is "Hawaiian Native Corporation" |
| "Nine tribal applicants incl. Dena' Nena' Henash, Cheyenne & Arapaho Tribes, Barona Band" | `TRBF-CHYARP-00` | an **aggregate of nine applicants** keyed to one of them |
| "Federally recognized tribes and tribal health organisations (aggregate, 8 projects)" | `UIO-HEALTH-00` | matched on the generic phrase **"health organisations"**, and is an eight-recipient aggregate |

**Standing rule earned: an AGGREGATE party string must never resolve to a single entity.**
Two of the four failures are that, and both would have booked a multi-recipient federal
round onto one tribe. Containment gives no warning because an aggregate string usually
contains a real tribe's name by construction.

---

## 3. AUGUST 2026 COLLECTION — `155_collect_deals_2026_08.py`

Window swept: **2026-07-28 to 2026-08-26**. The ledger's last 2026 row was 2026-07-27.

**Channels.** `tribalbusinessnews.com` — all 15 section indexes enumerated, then every
candidate article retrieved and read individually (article ids 15697 Jul 24 → 15742
Aug 22; nothing published after Aug 22 as of this run). `500nations.com` 2026 news hub,
July + August. `naskila.com`, `hwy331.com`, `nativeforward.org` for primaries. Several
acquisition-specific web searches.

**14 rows added.** 12 August, 1 July (Jul 31), 1 June (Jun 30, by the strict
transaction-date rule). 10 of 14 carry a disclosed value, totalling **$1,322,000,000**.

### THE FINDING FOR THE MIX: zero acquisitions in the window

Every one of the twelve August rows is a capital project, a commitment, a financing, a
settlement or a joint venture. **No acquisition closed or was announced in Indian Country
between 2026-07-28 and 2026-08-26 that any swept channel reports.** Recorded as found,
not nudged toward the acquisition column.

August is also thin on federal AWARDS — one grant-round row. Most agency activity in the
window is notices of funding **opportunity** (ANA $27.5M, SBA $10M for tribal colleges,
EPA $25.5M wastewater, IHS Tribal Management Grants). A NOFO names no recipient, carries
no award date and attributes no dollar. None were written.

| Deal_Category | rows |
|---|---:|
| Capital project | 7 |
| Capital contribution | 2 |
| Grant / public financing | 1 |
| Settlement | 1 |
| Financing | 1 |
| Joint venture | 1 |
| Real estate / land acquisition | 1 |

### The rows

| ID | date | row | value |
|---|---|---|---:|
| ND-2026-078 | 2026-07-31 | Chickasaw Nation breaks ground, Newcastle medical campus | $1,000,000,000 |
| ND-2026-079 | 2026-08-05 | Native Forward commits to a permanent endowment | $40,000,000 |
| ND-2026-080 | 2026-08-07 | Cherokee Nation opens Tahlequah wellness center | $30,000,000 |
| ND-2026-081 | 2026-08-10 | Hoopa Valley Tribe opens Acorn Connected data center | undisclosed |
| ND-2026-082 | 2026-08-14 | Middletown Rancheria solar project → tribal utility | $3,700,000 |
| ND-2026-083 | 2026-08-18 | IHS Quarters Program round, 8 projects | $15,300,000 |
| ND-2026-084 | 2026-08-18 | Walker River Paiute / NV Energy settlement + 5 ROWs | undisclosed |
| ND-2026-085 | 2026-08-18 | Gila River Health Care → UA College of Medicine branch | $25,000,000 |
| ND-2026-086 | 2026-08-19 | Shakopee Mdewakanton debt financing to Niron Magnetics | $150,000,000 |
| ND-2026-087 | 2026-08-19 | Havasupai broadband buildout begins | $7,000,000 |
| ND-2026-088 | 2026-08-19 | Seneca Niagara hotel renovation planned | $47,000,000 |
| ND-2026-089 | 2026-08-20 | Poarch Creek road project phase 1 begins | $4,000,000 |
| ND-2026-090 | 2026-08-20 | Rappahannock Enterprises + Netmaker 8(a) JV | undisclosed |
| ND-2026-091 | 2026-06-30 | Save the Redwoods League conveys 'O Rew to Yurok | undisclosed |

`ND-2026-077` was **not** reused — it is withdrawn, and reusing a withdrawn identifier
would make the withdrawal unreadable. New IDs start at 078.

### Value traps caught, all excluded from every value field

1. **Hoopa Valley data center.** The $65M in the article is a **2022** NTIA award — not a
   2026 one, not this facility's cost. Row carries no value.
2. **Poarch Creek roads.** The $24.1M FHWA award was made **in 2024 using FY2023
   funding**; the source says so outright. Only the ~$4M first phase actually begun in
   2026 is in `Announced_Value_USD`; $24.1M sits in `Project_Total_Value_USD`.
3. **Middletown Rancheria.** The $3M California Energy Commission loan was **approved in
   2024**. The 2026 event is construction.
4. **Rappahannock JV.** The ~$7.9M HigherGov figure is the **partner's** past federal
   awards, not the venture's value.
5. **Native Forward.** The $50M MacKenzie Scott gift is dated **2025-09-24**. Only the
   2026 allocation is recorded, and the $50M is parked in `Project_Total_Value_USD` so it
   cannot be double-counted against a future 2025 row.
6. **IHS Quarters Program.** The Karuk Tribe's $1.505M is a **component** of the $15.3M
   round and is already in the ledger as `ND-2026-058`. Flagged on the row: never sum.
7. **Cherokee Nation / Rogers State MOU.** The $4M is a **2024** commitment and the source
   states *"No money will change hands under the new agreement."* **Skipped entirely.**

### Dates: nothing invented

Where a source gives a transaction date it is used — Chickasaw groundbreaking **Jul 31**,
Yurok conveyance **Jun 30**. Where it gives only "early August" (Walker River) or nothing
(seven rows), `Event_Date` is the trade-press publication date and `Date_Basis` says so in
as many words. **No mid-month placeholder was needed and no day was guessed.**

**One strict-window case.** The Yurok 'O Rew row is published Aug 2 and opened to the
public Aug 1, but the source states the land was **conveyed on June 30**, so it files in
**June**. Same rule that filed the Hot 'n Now deal in 2024.

### One trap the search engine set

A search summary presented **Paskenta Band of Nomlaki Indians acquires Mad River Brewery
from the Yurok Tribe** as August 2026 news. The retrieved coverage dates it to
**March 2024**. Had the summary been trusted it would have been the window's only
acquisition — and wrong by two and a half years. Same class as the Blue North exclusion in
the 2026-08-05 log.

---

## 4. SKIPPED LEADS — `review/deals_skipped_leads_2026-08-26.csv` (8)

Two worth chasing:

- **Miccosukee Tribe, 25 acres in Walton County FL, ~$2.25M** (`no_date`). The retrieved
  page dates it only to "early 2026". A search summary asserted a recording date of
  Jan 5, 2026, but `mypanhandle.com` returns **403** and an unretrieved date is not
  evidence. **A real January 2026 land acquisition the ledger is missing** — resolvable
  from the Walton County deed record.
- **Native Forward's $50M MacKenzie Scott gift, 2025-09-24** (`out_of_window`). Firmly
  dated by the recipient's own release, and the largest single philanthropic award to
  Indian Country on that account. **The ledger has no row for it.** High-value 2025
  backfill.

Also skipped: Dartmouth's $5M Tribal Sovereignty Institute gift (**no Native party** —
donors are alumni, recipient is Dartmouth); Naskila Casino Resort groundbreaking, firmly
dated Jun 18 2026 but **no cost published anywhere retrieved**, so it cannot clear the
$1M threshold on evidence.

## 5. STATUS CORRECTION FOR RULING — `review/deals_status_corrections_2026-08-26.csv`

**`ND-2026-040` (Scotts Valley Band, Vallejo, $700M) is overtaken by events.** Interior
withdrew the gaming determination on **Friday 2026-07-31**, meeting a court-ordered
end-of-July deadline; Assistant Secretary William H. Kirkland III concluded on
reconsideration that *"the Band has not established a significant historical connection to
the Parcel."* The temporary Class II preview casino, opened about a week earlier, is
suspended. The tribe says it will sue.

**No deal row was written for it.** A regulatory reversal is not a transaction between
parties, and a row carrying the $700M project value would double-count `ND-2026-040`. It
is a **status** fact about an existing row. It is not applied automatically either,
because the `Status` vocabulary has no agreed term for a withdrawn federal determination
and inventing one silently drops the row from the fixed-label rollups.

## 6. CROSS-SOURCE VERIFICATION GAINED

`ND-2026-068` (Quartz Valley, $25M) had one source. Trade-press coverage of the same
California State Water Resources Control Board action was found and written into its
**blank** `Source_2` — additive only, never over an existing one. Two sources that agree
is a verification under `docs/CROSS_SOURCE_VERIFICATION.md`. The second source adds that
a final land price has not been determined and that the Trust for Public Land buys from
EFM and deeds to the tribe, which is why `Announced_Value_USD` stays the **loan**, not a
price.

---

## 7. RESULTING 2026 MONTHLY DISTRIBUTION

| month | rows | | month | rows |
|---|---:|---|---|---:|
| 2026-01 | 7 | | 2026-05 | 13 |
| 2026-02 | 8 | | 2026-06 | 7 |
| 2026-03 | 6 | | 2026-07 | 12 |
| 2026-04 | 26 | | 2026-08 | 12 |

**91 rows dated 2026, from 1.** April's 26 is not a real spike — 18 of them are the
one-per-award USDOT RTA round of 2026-04-06.

## 8. WHAT WAS DELIBERATELY NOT DONE

- **`88_build_deals_taxonomy.py` was NOT run.** Its glob is fixed for the next reader, but
  it is a full rebuild that drops the seven `native_party_*` columns script 126 writes in
  place. A warning to that effect is now in its docstring. Rows were added by 153 and 155
  instead, which merge rather than rebuild.
- **`41_build_codebooks.py` was NOT run** for the same reason — it rebuilds every dataset's
  codebook at once, on other agents' timing. `156_refresh_deals_codebook_fragment.py`
  re-measured `data/clean/codebook/01_deals.csv` alone (790 → 935 rows), touching only the
  three columns that are measurements and leaving every written description intact. It
  reports the **19 ledger columns that have no codebook entry** — the classification and
  attribution columns — which need a written description and a publish ruling from 41.
- `09_import_rulings.py` and `01_build_entity_spine.py` were not run.

## 9. OPEN

- **45 unmatched deal parties** (`review/deals_party_unmatched_2026-08-26.csv`). Of the 14
  rows added today, 12 linked; the 2 that did not are the deliberately refused IHS
  aggregate and **Native Forward Scholars Fund, which has no spine entry at all** — a
  national Native nonprofit that probably should have one.
- The 4 refusals in `review/deals_party_refused_2026-08-26.csv` need rulings.
- `docs/COVERAGE_AUDIT.md` still says 790 in two places.
