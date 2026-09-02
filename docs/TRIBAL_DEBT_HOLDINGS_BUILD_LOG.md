# Tribal Debt — who lends, who buys the paper, and what the borrower discloses

*Built 2026-09-02 by `code/1082_tribal_debt_holdings_disclosure.py`. Companion
to `docs/TRIBAL_DEBT_BUILD_LOG.md` (2026-08-05, the Moody's / EMMA discovery
run) — that log established the ISSUER UNIVERSE; this one opens a RETRIEVAL
channel it did not have. Neither supersedes the other.*

**Do not commit.** Everything below is staged in `data/staging/` and `review/`.
Nothing in `data/clean/` was edited.

---
> **GAMING-DENOMINATOR-2026-09-02 — the gaming denominator, re-derived from the live files.**
> **`gaming_facilities.csv` holds 787 ROWS, and a row is not a facility.** The ladder, owned and gated by `code/846_session_audit.py::_denom`:
> 
> ```
> 787   rows in gaming_facilities.csv
> -16   whose NAME says no casino - 7 exactly "No casino", plus 9 more like
>       "Grand Canyon West - no casino", "Tribal admin only - no casino"
> =771   facility rows
> -57   extra rows across the same-tribe duplicate groups
> =714   distinct properties
> ```
> 
> **FIVE denominators circulated on 2026-09-02 and all five were quoted as settled: 787, 780, 734, 727, 714.** Each came from a different definition of "facility" and none said which. 787 is raw rows; 780 removes only the 7 EXACT placeholders and misses the 9 that say it in a longer name; 734 is 787 minus duplicates with every placeholder left in; 727 is 780 minus a duplicate count of 53. **None of them is wrong about the piece it measured, and four of them are wrong as a denominator.** No verdict is applied in the table itself - `duplicate_of_facility_id` is populated on 10 rows, not 57 - so 714 is a measurement, not a state of the file. Note also that the duplicate register carries `DIFFERENT_TRIBES_CHECK_BOTH` groups that are **not** duplicates: Stables Casino pairs the Miami Tribe with Modoc Nation, which is a joint operation. Dividing by 787 inflates the denominator by 10.2% and understates every gaming coverage percentage by about 9.3%.
>
> Authority: `code/846_session_audit.py::_denom`, which gates this ladder.
> Re-derive rather than quote: `py -3 code/1116_ruling_propagation_2026_09_02.py derive`.
> `py -3 code/1116_ruling_propagation_2026_09_02.py verify` exits 1 while any
> document in `docs/` or `review/` still states a superseded figure unmarked.
>
> Re-derive rather than quote: `py -3 code/1116_ruling_propagation_2026_09_02.py derive`.
> `py -3 code/1116_ruling_propagation_2026_09_02.py verify` exits 1 while any
> document in `docs/` or `review/` still states a superseded figure unmarked.

## The owner's question, and why the answer generalises

> *"there's these vulture capital funds that will basically buy bad debt from
> tribes. I imagine there's ways to understand tribal financing in those terms,
> and whether it was used for gaming. If you can invest in these, then they're
> probably available."*

The inference is right, and it is stronger than it looks: **an instrument that
can be bought must be disclosed — by the buyer.** A US registered investment
company holding a tribal term loan or a tribal bond must print it in its
portfolio schedule with the borrower's name, the principal balance, the coupon,
the maturity and the fair value. In Form N-PORT it does so in a machine-readable
XML block that also carries `isDefault` and `areIntrstPmntsInArrs`.

That disclosure is filed **by the fund**, not by the tribe. Under
`docs/PUBLICATION_POLICY.md` (`TERMS-SCOPE`, *"the distinction is authorship, not
subject matter"*) no tribal source's terms of use reach it, and the eight
hard-listed sources are unaffected.

## The seam was already on disk, and had been correctly discarded

`code/1030_sec_edgar_native_transactions.py` swept EDGAR for Native-entity
**transactions** and classed **13,115 hits across 1,864 accessions** as NOISE —
*"registered investment company holdings reports, which name tribal bond issuers
but disclose no transaction."*

That triage was right for 1030's question and wrong to reuse for this one. **A
holding is not a transaction, but for "who holds tribal debt, on what terms" the
holding IS the observation.** 1030 had gone as far as extracting 37 issuer
*names* (`review/sec_edgar_1030_tribal_debt_issuers.csv`) with no amount, rate,
maturity or default flag. This build takes that from a name list to an
instrument-level register.

---

## What was built

| output | rows | grain |
|---|---:|---|
| `data/staging/tribal_debt_holdings.csv` | **1,585** | ONE FUND'S POSITION in one instrument at one `report_period_end` |
| `data/staging/tribal_debt_obligors.csv` | **14** | one obligor |
| `data/staging/tribal_debt_distress_events.csv` | **0** | one as-filed default/arrears flag |
| `data/staging/tribal_obligor_property_revenue.csv` | **8** | one property-fiscal-year |
| `review/1082_fetch_queue.csv` / `_fetch_manifest.csv` | 1,864 / **1,252** | the queue and every request made |
| `review/1082_unmatched_issuer_names.csv` | **38,655** | every issuer name REFUSED or unmatched, with the reason |
| `review/1082_source_dispositions.csv` | 2 | EMMA and EDGAR, dispositioned |
| `data/raw/external/tribal_debt_1082/*.xml.gz` | 1,252 | the cache; every figure is re-readable |

Stages: `plan` → `fetch` → `mine` → `revenue` → `emma` → `verify` → `selftest`.

**The fetch: 1,252 of 1,252 NPORT documents at HTTP 200**, one host lock on
`www.sec.gov`, >=0.20s gap, declared User-Agent with contact, manifest flushed
after every request. Nine transient `503`s on the first pass were re-fetched
and cleared. `mine` parsed all 1,252 with **0 parse failures**.

### The register, measured

| | |
|---|---:|
| fund-holding observations | **1,585** |
| distinct obligors | **14** |
| distinct Cedar entities reached | **13** (Downstream and Quapaw Nation are one nation under two obligor names) |
| distinct registered funds holding tribal paper | **199** |
| distinct CUSIPs | **28** |
| report periods covered | **2019-09-30 to 2026-06-30** |
| bonds (`DBT`) / loans (`LON`) | 1,336 / 249 |
| rows flagged `isRestrictedSec = Y` (144A paper) | **300** |
| rows with an as-filed default or arrears flag | **0** |

| obligor | observations | funds holding it | Cedar entity | tier |
|---|---:|---:|---|---|
| Mohegan Tribal Gaming Authority | 1,382 | 188 | `CE-0016X-GY` | B |
| PCI Gaming Authority (Poarch Band of Creek Indians) | 59 | 15 | `CE-0018H-JJ` | B |
| Southern Ute Indian Tribe | 46 | 14 | `CE-001AX-4Y` | B |
| River Rock Entertainment Authority | 22 | 7 | `CE-00143-AM` | B |
| Catawba Nation Gaming Authority | 19 | 10 | `CE-0012V-GC` | B |
| Navajo Nation | 13 | 4 | `CE-0017F-1G` | B |
| Inn of the Mountain Gods Resort and Casino | 8 | 2 | `CE-0017A-3K` | B |
| Mashantucket (Western) Pequot Tribe | 8 | 1 | `CE-0017C-F5` | B |
| Oneida Indian Nation of New York | 8 | 3 | `CE-0017X-NE` | B |
| Seminole Tribe of Florida | 8 | 3 | `CE-001A9-CA` | A |
| Cabazon Band of Mission Indians | 5 | 1 | `CE-0012P-JF` | B |
| Downstream Development Authority | 4 | 2 | `CE-0018Z-6G` | B |
| Quapaw Nation | 2 | 1 | `CE-0018Z-6G` | A |
| Oglala Sioux Tribe | 1 | 1 | `CE-0017T-33` | A |

**300 rows are 144A restricted paper.** That is the direct answer to the
question `docs/DEALS_SEC_2010_2017_BUILD_LOG.md` left open: Rule 144A tribal
debt is *"invisible to EDGAR by construction"* from the ISSUER side, and it is
perfectly visible from the HOLDER side, because the fund that bought it has its
own disclosure obligation. **The instrument does not have to be registered for
the position in it to be reported.**

---

## The obligors, and how many resolve to a Cedar entity

**14 of 14 obligors resolve to a Cedar entity** (13 distinct entities). Four
resolution passes, each
weaker than the last and each labelled on the row:

1. `exact_canonical_name` → tier **A**
2. `spine_name_is_a_whole_token_run_inside_obligor_name` → tier **B**
3. `named_obligor_token_..._CONTAINMENT_descriptive_only_never_keys_a_dollar`
   → tier **B**
4. `stated_enterprise_of_nation: <the source that states it>` → tier **B**

Pass 4 exists because **no string match can bridge "Downstream Development
Authority" and "Quapaw"**. Those links are stated relationships carrying the
source that states them, never inferences from a name. In Downstream's case the
fund itself prints the full legal name *"Downstream Development Authority of the
Quapaw Tribe of Oklahoma"* — the relationship is in the disclosure.

**Tier is inherited from the strength of the EVIDENCE, not the exactness of the
key** (`START_HERE.md` trap 1). Passes 3 and 4 are containment matches and
`AGENTS.md` forbids containment from keying a dollar. It does not key one here:
the money on these rows belongs to the **fund**, and is attributed to the fund.
The entity link is descriptive.

---

## The money fence

Recorded in `docs/MONEY_TOTALLING_RULES.md` inside a marked `TRIBAL-DEBT` block
so `574`'s wholesale rewrite preserves it. The short version:

**There is no additive measure in any of these tables.**

`principal_usd` is the most dangerous column in the set, because it is a real,
audited, machine-readable dollar figure that is **a fraction of an instrument,
not the instrument**. Dozens of funds report a position in the same obligor's
paper; adding their balances produces a number that is not the par of anything.
Three prohibitions, each of which would produce a plausible wrong number:

1. Never sum across funds.
2. Never sum across `report_period_end` — the same position held for eight
   quarters is one position, not eight.
3. Never add to `deals_classified.Announced_Value_USD` or
   `tribal_bond_issuances.par_amount`. Those describe the WHOLE instrument at
   issuance; a holdings balance is a slice of it years later. The correct
   relation is `<=`, not `+`.

Every row carries `not_summable_with` naming the specific columns. Invariant
`I3` fails the build if any row loses it.

### `is_default_as_filed` is not a default

The flag is Form N-PORT Item C.9, reported by **the fund**, about the security.
It is that fund's characterisation for portfolio-reporting purposes. It is not a
court finding, not an acceleration, and not a corporate insolvency — **a tribal
obligor is a sovereign and a tribal default is not a corporate default.** Every
distress row carries `sovereign_immunity_caution` saying exactly that.

**Measured result: zero distress events across all 1,585 holdings.**
`isDefault` and `areIntrstPmntsInArrs` are `N` on every row. That is a finding, not an empty
table: on this evidence, **no registered fund reported a tribal instrument in
default or in arrears in the period covered**. It does not mean no tribal
obligor has ever been distressed — the well-documented restructurings
(Mashantucket, Chukchansi, Lake of the Torches, Santa Ysabel, River Rock)
predate Form N-PORT, which begins in 2019. **The channel is younger than the
distress.** Court dockets remain the route to those, and are untouched here.

---

## Facility-level gaming revenue: what actually moved, honestly

The mandate asked which facilities gained a revenue figure from an audited
disclosure. The honest answer has two halves.

### The NPORT seam produced ZERO revenue figures, by construction

It is a debt register. It answers *who holds the paper and on what terms*, never
*what the property earns*. Anyone joining it to `gaming_facility_metrics` must
carry that in the join, not in a footnote.

### A different, terms-clean channel produced 8 — and it exists because of the debt

A tribal gaming authority that sold 144A notes **with registration rights** ends
up an SEC reporting company, and then files audited financial statements whose
MD&A discusses each property by name. That is facility-level revenue for an
operation NIGC will only report inside a regional aggregate, and it is a
consequence of the financing.

`code/1082 revenue` reads the **33 obligor filings already cached** by 1030
(`ON_DISK_NOT_PROMOTED`, not a fetch) and extracts:

| property | FY | net revenues | Cedar facility |
|---|---|---:|---|
| Mohegan Sun | 2018 | $1,069,000,000 | `CCP-45100` |
| Mohegan Sun | 2019 | $992,000,000 | `CCP-45100` |
| Mohegan Sun | 2021 | $816,400,000 | `CCP-45100` |
| Mohegan Sun Pocono | 2017 | $278,900,000 | `VP-0034` |
| Mohegan Sun Pocono | 2018 | $265,700,000 | `VP-0034` (2 filings) |
| Mohegan Sun Pocono | 2019 | $251,100,000 | `VP-0034` |
| Mohegan Sun Pocono | 2021 | $221,500,000 | `VP-0034` |
| MGE Niagara Resorts | 2021 | $99,200,000 | none — Ontario, outside Cedar's universe |

**Against the 787-facility denominator this reaches 2 facilities.** Of those,
`CCP-45100` (Mohegan Sun) already carried `REPORTED_PROPERTY_REVENUE` and gains
additional fiscal years at a stronger evidence class; **`VP-0034` (Mohegan
Pennsylvania) had `revenue_bound_strongest_status` BLANK and gains its first
per-property figure.** So the honest headline is **one new facility, one
strengthened** — against a baseline of 11 of 787. It is a small number and it
should be reported as a small number.

`Mohegan Sun Pocono FY2018 = $265.7M` appears in **two independently filed
10-Ks** (the FY2018 and FY2019 reports). That is a genuine corroboration and it
is recorded in `n_independent_filings`, not silently collapsed.

### It is NET REVENUES, not gaming revenue

The filing's own word is *"net revenues"* — total property revenue **including**
hotel, food, beverage, entertainment and retail. NIGC gross gaming revenue is
gaming win only. `measurement_type` is
`PROPERTY_NET_REVENUE_INCLUDES_NON_GAMING` on every row and the two must never
be compared as like for like.

### A third evidence class, and the ceiling it must never be added to

`assertion_class = AUDITED_OBLIGOR_SEC_DISCLOSURE`: the obligor's own mandatory,
audited federal securities filing. Stronger than a casino's marketing page,
different in kind from an NIGC figure. **It must never be summed against an NIGC
regional ceiling** — `gaming_revenue_bounds` records a `REGIONAL_GGR_CEILING` as
an *upper bound on this very property*, so adding the two adds a part to its own
whole.

### The extractor's guard, and the bug it was written to stop

The pattern requires a **direction verb** before the figure:
`Net revenues (increased|declined|...) ... to $X million for the year ended ...`.

Without the verb the first draft matched *"the acquisition of the MGE Niagara
Resorts, which contributed $112.5 million **to** net revenues"* and would have
booked a **contribution** as a property total, attributed to the wrong property
by nearest-heading proximity. One wrong row out of one — a 100% error rate,
caught in prototype because the output was printed next to the source sentence
before anything was written. **The verb is the whole guard. Do not relax it.**
Every row carries the `verbatim_quote` so the figure is re-readable.

### Four obligor CIKs are NOT_ACQUIRED — a real fetch task

`1141344` Choctaw Resort Development Enterprise, `1430349` Cheyenne River Sioux
Tribal Finance Corp, `1296784` Seneca Niagara Falls Gaming Corp, `1296786`
Seneca Erie Gaming Corp. **Choctaw Resort Development Enterprise is the highest
value of these** — it is the Mississippi Band of Choctaw Indians' gaming
enterprise (Pearl River Resort), it already appears twice in
`data/clean/deals_tribal_debt_additions.csv`, and its 10-Ks would carry audited
property revenue. Seneca's per-property subsidiary registrants are the only
place a Seneca property figure could come from; Seneca's own 10-Ks put revenue
in tables rather than the MD&A sentence form, so the current extractor returns
**zero** for Seneca — a measured non-yield, not a gap.

---

## MSRB EMMA: CONSTRAINED, and more firmly than the record said

EMMA remains the single largest unexploited source for this material, and it
remains closed. `docs/TRIBAL_DEBT_BUILD_LOG.md` recorded the refusal as
`SK-TD-001` on 2026-08-05. **Re-read verbatim 2026-09-02** from
`https://emma.msrb.org/AboutEmma/UserAgreement` (cached at
`data/raw/external/tribal_debt_1082/emma_user_agreement_2026-09-02.html`).
Three independently sufficient clauses:

**1. The clause bars the OUTPUT, not only the method.**
> *"You agree that you will not: use Content or Services to develop or create a
> database to be sold, leased, furnished, licensed or otherwise exploited or
> made available (either commercially or free of charge)."*

Cedar Press is a paid product — and note the parenthetical reaches a **free**
release too, so "publish it for nothing" is not a way round it.

**2. The clause names MANUAL collection. This is new against the record.**
> *"use or allow others to use any data mining, crawling, 'scraping', robot or
> similar automated or data gathering or extraction method, **or any manual
> process**, to access, acquire, monitor or copy any portion of the Website,
> Content or Services, or otherwise systematically download or store Content."*

The 2026-08-05 log quoted only the automated half, and its ranked
recommendations left the impression that a human could read the documents in the
meantime. **There is no hand-collection workaround.**

**3. A second licensor sits on top.**
> *"The CUSIP Database … is and shall remain valuable intellectual property
> owned by, or licensed to, CUSIP Global Services ('CGS') and the American
> Bankers Association ('ABA') … Any use by you outside of the clearing and
> settlement of transactions requires a license from CGS, along with an
> associated fee based on usage."*

EMMA's footer also credits ICE Data Pricing & Reference Data, LLC. **An MSRB
licence alone would not clear CUSIPs.** Anyone costing this must cost both.

**robots.txt is not the blocker and must not be read as permission.**
Re-measured 2026-09-02, unchanged: `User-agent: *` / `Disallow: /*.pdf$`. Only
PDFs. The Terms of Use are the binding instrument and are far broader.

### The three routes back in

1. **Ask.** The agreement states its own exception — *"unless otherwise
   authorized by the MSRB"* — and names where to write: MSRB, 1300 I Street NW,
   Suite 1000, Washington, DC 20005, Attention: External Relations. Cedar's
   standing principle is that **asking is the route back in and a cleverer
   scrape is not.**
2. **Buy.** MSRB sells subscription feeds. Price CGS beside it.
3. **Go round it by AUTHOR, not by route.** The same official statements and
   continuing disclosures are authored by the issuer, the conduit issuer and the
   underwriter. A document obtained from one of *those* publishers is that
   publisher's, and MSRB's terms over its own website do not reach it. **The
   caveat cuts the other way here:** because a continuing-disclosure document is
   filed *by the obligor*, ~~for the eight hard-listed sources their own filings
   stay excluded by that same ruling.~~ **that ceased to bind on 2026-09-02**
   (`PUBLICATION_POLICY.md`, `TERMS-OWNER-RULING-2026-09-02`) — the eight are
   released for their own publications. **It changes nothing here**, and the
   reason is worth being exact about: EMMA is refused by a *third-party
   licensor* (MSRB, with CUSIP Global Services), which the ruling explicitly
   left standing. The obligor's terms were never the operative bar on this
   route; MSRB's are, and they still are.

**What the refusal costs, stated so it can be priced.** The 2026-08-05 run
enumerated ~95 tribal issuer records across ~70 distinct tribal governments on
EMMA. For the gaming-authority subset, the annual audited financials would carry
facility-level gaming revenue — the figure `gaming` records as
`SOURCE_DOES_NOT_PUBLISH` on 776 of 787 rows *(**GAMING-DENOMINATOR-2026-09-02:** `gaming_facilities.csv` holds **787 ROWS, not 787 facilities** — 16 rows' NAMES say no casino (7 exactly, 9 like `Grand Canyon West - no casino`) and 57 extra rows sit across the same-tribe duplicate groups, so **771 facility rows and 714 distinct properties**. Five denominators circulated on 2026-09-02 — 787, 780, 734, 727, 714 — and only the last is the property count. Authority: `code/846_session_audit.py::_denom`; derive it with `py -3 code/1116_ruling_propagation_2026_09_02.py derive`.)*. **This is an owner
procurement decision, not a research problem**, and it is the single highest-value
open item in this workstream.

---

## Honest coverage

| denominator | reached | how |
|---|---:|---|
| 787 gaming facilities | **2** (one new, one strengthened) | audited obligor SEC filings |
| 787 gaming facilities | **0** | the NPORT holdings seam — it carries no revenue at all |
| ~574 nations | **13 distinct Cedar entities**, 14 obligors | a registered fund holds their paper |
| 284 gaming-operating tribes | **9** | obligors whose instrument is a gaming instrument |
| 11 facilities with an honest per-property number | **12 after this build** | +1 (`VP-0034`) |

**This reaches a very small fraction of Indian Country and that is the correct
result, not a shortfall.** Only a handful of tribal obligors have ever placed
paper that a US registered fund holds, and `docs/TRIBAL_DEBT_BUILD_LOG.md`
already established the structural reason: tribal municipal issuance is
overwhelmingly **not** gaming debt — housing authorities, health facilities,
water and sewer, sales-tax revenue — and most of it never reaches a mutual
fund's schedule of investments. A number near 8 is what this channel contains.

---

## Precision of the matcher, measured rather than asserted

Every issuer name the parser saw and did not accept is written to
`review/1082_unmatched_issuer_names.csv` with its verdict and reason — refusals
are recorded, never silently dropped.

Auditing those unmatched names against the Moody's tribal issuer census and the
EMMA roster in `docs/TRIBAL_DEBT_BUILD_LOG.md` found **exactly one real miss**:
**PCI Gaming Authority** (51 observations), the Poarch Band of Creek Indians'
gaming authority — an initialism containing no tribal word. It was added, with
the reason recorded inline. Everything else the audit surfaced was noise
(`National Association`, `International`, `Indiana`).

Names are **refused** against the measured false-positive classes
`docs/TRIBAL_DEBT_BUILD_LOG.md` established against Moody's sitemaps:
`INDIANA MICHIGAN POWER CO`, `DUKE ENERGY INDIANA LLC`, `INDIANAPOLIS PWR &
LIGHT`, `MOHAWK INDUSTRIES INC`, `Hard Rock Indiana Casino`. Invariant `I4`
fails the build if any of them ever reaches the holdings table.

### One false positive got through the guard, and it is worth the space

The full-corpus run admitted **South Carolina Jobs-Economic Development
Authority, International Paper Co. Project, Series 2023A** as a tribal obligor.

The generic token `economic development authority` is only accepted when a
tribal word appears in the same string, and the guard tested that with plain
containment. `"nation"` is a substring of `"INTERnationAL"`. **The containment
defect `AGENTS.md` forbids, committed inside the guard written to prevent it.**

Caught by *reading the fourteen-row obligor list*, not by any check — a state
conduit issuer financing a paper mill is obvious to a human and invisible to a
count. Fixed with a word-boundary regex (`TRIBAL_WORD`), and the conduit-issuer
family added to the refusal list. **The lesson is the review, not the regex:
this table is small enough to read end to end, so read it.**

---

## The gates

```
py -3 code/1082_tribal_debt_holdings_disclosure.py verify     # exit 1 on breach
py -3 code/1082_tribal_debt_holdings_disclosure.py selftest   # proves it fires
```

Seven invariants, and **`selftest` proves every one of them fires on its own
synthetic violation**, then restores the table byte-for-byte and re-asserts
green:

```
I1_every_holding_names_an_obligor                          FIRES
I2_every_holding_carries_a_source_url                      FIRES
I3_no_holding_asserts_a_summable_total                     FIRES
I4_no_refused_false_positive_reached_the_holdings_table    FIRES
I5_entity_tier_is_blank_when_there_is_no_entity_link       FIRES
I6_every_distress_row_is_backed_by_an_as_filed_flag        FIRES
I7_no_fabricated_money_every_amount_is_blank_or_numeric    FIRES
```

`selftest` refuses to run against an already-red table, which is what it should
do — a violation injected into a broken baseline proves nothing.

---

## Three defects committed and caught during this build, all of one shape

`docs/AGENT_FIELD_GUIDE.md` section 3 names this repo's signature defect: *a
check that does not measure its own name.* All three of today's are instances,
and two were committed **inside the machinery written to prevent it.**

**1. The selftest's own detector reported a working invariant as broken.**
It tested `"BREACH" in verify_output.split(name, 1)[1][:12]`. The verify line is
`"%-58s %s" % (name, verdict)`, so for a 50-character invariant name the verdict
begins at offset 59 — outside the 12-character window. `I6` fired correctly and
the selftest printed **`DID NOT FIRE`**, which would have sent the next reader to
debug a working check. Fixed by reconstructing the exact line verify prints
(`_named_invariant_fired`), so there is no string arithmetic left to get wrong.

**2. A patch script printed `patched` without patching.** Two `str.replace`
calls silently no-opped on a whitespace mismatch and the script reported success
both times, so a resolution pass that had never been installed was debugged as
though it were failing. **A mutation without an assertion is a claim, not a
change.** Every later patch in this build asserts the target text is present
before replacing it.

**3. The revenue extractor's first draft had a 100% error rate.** It matched
*"contributed $112.5 million to net revenues"* and attributed a contribution to
the nearest heading. Caught only because the prototype **printed the extracted
figure next to the source sentence before anything was written to a file** —
which is field-guide habit 3, and it is the reason the error cost five minutes
instead of appearing as a plausible number in a shipped table.

A fourth is the `nation`-inside-`International` containment bug above.

A fifth, smaller: the fetch's circuit breaker counted `404` as a refusal and
stopped after five. `404` is a **fact about the object** (`START_HERE.md`
standing rule), not the host turning us away — here it meant `NPORT-EX` ships an
HTML exhibit rather than `primary_doc.xml`, measured against `index.json` rather
than guessed. `404` and `403` no longer trip the breaker.

---

## What to do next, ranked

1. **Resolve the EMMA licence.** Owner decision. It is simultaneously the
   completion of the tribal-debt dataset and the only route to facility-level
   gaming revenue for the ~70-issuer roster. Cost both MSRB and CGS.
2. **Fetch the four missing obligor CIKs**, Choctaw Resort Development
   Enterprise first. Audited property revenue for Pearl River Resort is a real
   possibility and it is four `data.sec.gov` submission lookups plus a handful of
   documents.
3. **Teach `revenue` to read the segment-reporting TABLE**, not only the MD&A
   sentence. Seneca puts its per-property figures in tables and currently yields
   zero. This is where the next several facilities are.
4. **Court dockets for the distress the N-PORT era cannot see.** Lake of the
   Torches, Santa Ysabel, River Rock, Chukchansi, Mashantucket — all predate Form
   N-PORT. `COURTLISTENER_API_TOKEN` is live and
   `code/366_courtlistener_ownership_adjudication.py` already holds a polite
   client. **Keep the sovereign-immunity caution: quote the instrument.**
5. **Fetch the 612 priority-2 documents** (`N-Q`, `N-CSR`, `N-MFP`) and teach
   `mine` to read HTML schedules. These are the pre-2019 years — the N-PORT XML
   only begins in 2019, and the pre-2019 holdings are where a distressed tribal
   instrument would actually appear.
6. **The 7 `T-3` accessions** in the candidate index. Form T-3 is a Trust
   Indenture Act application filed for debt **not registered** under the
   Securities Act — precisely the Rule 144A tribal paper
   `docs/DEALS_SEC_2010_2017_BUILD_LOG.md` called invisible to EDGAR by
   construction. Seven documents, and each one carries an indenture.

<!-- BEGIN GAMING-DENOMINATOR-717-CORRECTION -->

## CORRECTION 2026-09-02 — the gaming property denominator is 717, not 714

Appended by `code/1142_gaming_denominator_doc_sweep.py`. **No prose above this
line was edited**, per the rule the `GAMING-DENOMINATOR-2026-09-02` banner set
for itself.

Any figure in this document that uses **714** as the count of distinct gaming
properties is superseded. The settled figure is **717**:

```
787   rows in gaming_facilities.csv
-16   carrying cedar_place_id_absent_reason = NOT_A_PLACE
=771   rows that are a place
-54   extras collapsed by the 53 ADJUDICATED merge groups
=717   distinct properties        <- COUNT(DISTINCT cedar_place_id)
```

**Why the old ladder gave 714.** It subtracted **57** duplicate extras found by
name normalisation. The adjudication found **54**. The three-property
difference is three groups a mechanical duplicate test called the same property
and a human verdict did not:

| group | why it is two properties |
|---|---|
| `THREE RIVERS` (OR) | Coos Bay 97420 and Florence 97439 — **67 km apart**, two casinos |
| `GLACIER PEAKS` (MT) | a casino and its hotel |
| `CITIES OF GOLD` (NM) | a casino and its hotel |

A duplicate count is an upper bound on merges; an adjudication is the answer.

**Two groups remain genuinely open** and either ruling moves 717: `THE STABLES`
(a real Miami/Modoc joint operation — one property, two sovereigns) and
`7 CLANS FIRST COUNCIL` (OK). Both are in
`review/OWNER_DECISION_QUEUE.md` as GP-1 and GP-2.

**Do not re-derive this number.** Seven values circulated for it — 787, 780,
734, 727, 725, 717, 714 — each from a correct-looking rule applied to an
undefined question. `gaming_facilities.csv` now answers it itself: the 16
non-places carry a reason column, and the merged properties share a
`cedar_place_id`. Read `COUNT(DISTINCT cedar_place_id)`.

<!-- END GAMING-DENOMINATOR-717-CORRECTION -->
