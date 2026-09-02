# NIGC Declination Letters — build log

*Built 2026-08-06. Scripts: `code/90_fetch_nigc_declinations.py` (retrieval),
`code/91_build_nigc_declinations.py` (extraction and matching). Cedar Press.*

> **COMPLETED 2026-08-07 by `code/100_finish_declinations_and_employment.py`.**
> **Sections 13–18 at the end of this file are the current state.** The 08-06
> sections are kept because their *findings and rules* remain true and were
> paid for; their *counts* are superseded. Specifically: **§2 (the 160
> image-only letters), §3.3 (findings), §7 (145 financing events) and §8
> (against the deals ledger) are superseded by §13, §14, §15 and §16.**
> The image-only ceiling that §2 describes has been **closed**: all 158
> retrievable scans were OCR'd and read.

*(A source brief circulated for this work names the venture "Cedar Grove". It is
Cedar **Press**. Noted so the mistake does not propagate — the NIGC region build
log records the same correction.)*

---

## 0. The one thing to carry away

**A declination letter proves NIGC reviewed submitted, unexecuted documents and
reached a legal conclusion. It proves nothing else.**

That is not our caution, it is the agency's own description, printed on the
index page this build scraped:

> "Documents should be submitted prior to their execution (unsigned) as the
> General Counsel will not provide a declination letter for executed documents."

> "This review is neither required by the Indian Gaming Regulatory Act nor the
> NIGC regulations and is offered by the OGC as a courtesy."

So a letter is **not** evidence that the transaction closed, that any agreement
was executed, that the property opened or still operates, or that land is in
trust or gaming-eligible. For land status and federal approval, cite the Federal
Register or BIA. Both sentences are carried on every row of
`nigc_declination_letters.csv` in `evidence_meaning`, and every financing event
carries `execution_status = UNEXECUTED_DRAFTS_REVIEWED` with the quote that
supports it (152 of 167 readable letters carry that quote in their own words).

**And absence proves nothing.** Review is voluntary and posting happens only
after NIGC's FOIA Officer clears the file. A property with no letter is not a
property with no financing. `absence_meaning` says so on every row, and the
tribe roster diff repeats it on every row of its own.

---

## 1. What was retrieved

| | |
|---|---:|
| Index rows (NIGC's own `tablepress-2` table) | **327** |
| PDFs retrieved, HTTP 200 | **326** |
| Distinct md5s | **325** |
| Date range | **2013-07-30 … 2026-04-14** |
| Archive size | 106 MB, 328 manifest rows |

Held at `data/raw/external/nigc_declinations/` — `pdf/` (325 objects),
`_index/` (the scraped HTML and the parsed CSV), `_SOURCE_MANIFEST.csv` with an
md5 on every object, and `_fetch_state.json`.

Letters per year: 2013 **14** · 2014 **17** · 2015 **33** · 2016 **38** · 2017
**18** · 2018 **23** · 2019 **37** · 2020 **44** · 2021 **42** · 2022 **14** ·
2023 **10** · 2024 **17** · 2025 **17** · 2026 **3**.

### 1.1 The download trap, in a new form

`docs/NIGC_REGION_BUILD_LOG.md` §15 records that every `nigc.gov/download/<slug>/`
page carries a sidebar WPDM link with the same `wpdmdl=3974`, so matching the
first `wpdmdl=` returns the identical PDF every time, all the same byte length,
looking like success.

The declination index links WPDM ids **directly from the table**, so the trap
presents differently and it bit twice:

1. **The page's first two `wpdmdl=` links are not letters.** `wpdmdl=3974` is
   the sidebar and `wpdmdl=7374` is *Helpful Hints for Submitting a Request for
   an Opinion Letter*. A scraper taking links from the page rather than from
   inside the table starts with two non-letters. The fetcher takes links only
   from `<table id="tablepress-2">` and refuses those two ids by name.

2. **The collision is on `ind=`, not on `wpdmdl=`.** Two index rows —
   2021-04-12 Yavapai-Apache / BOKF N.A. and 2021-04-13 Tunica Biloxi / First
   Guaranty Bank — carry **different** `wpdmdl` values (3173 and 3175) and the
   **same** `ind=3176`, and both 302-redirect to the identical object
   `20210412Yavapai-Apache-BOKFNA.pdf`. Distinct URLs, identical md5.

   This is why the fetcher verifies md5s rather than trusting distinct URLs, and
   it is a genuine defect **in the published archive**: one of those two links
   serves the other letter's document. Reading findings out of that PDF for both
   rows would have attributed a Yavapai-Apache opinion to the Tunica-Biloxi
   Tribe.

   **The rule applied, stated so it generalises:** where n index rows resolve to
   one md5, the PDF is attributed to the row whose own index date appears in the
   resolved filename, and to no row at all if that test is not decisive. The
   loser is retained with `retrieval_status =
   pdf_link_serves_another_letters_document` and **nothing is read out of it**.

3. **One HTTP 404.** `NIGC-DL-20140519-01` (Kalispel Tribe of Indians / Wells
   Fargo Bank N.A., 2014-05-19) is listed in NIGC's own index and its PDF is not
   served. Recorded as `not_retrieved_http_404`, not dropped — a listed letter
   that the agency does not serve is a fact about the archive.

### 1.2 Pull discipline

One poller, one host. `logs/_HOSTLOCK_www.nigc.gov.json` was claimed before the
first request and released on completion; requests sequential with a 2 s floor
gap and exponential backoff; 327 requests, 326 × HTTP 200, one 404, no
throttling. `code/89_nigc_map_wayback_universe.py` was running and holds
`web.archive.org`; no second poller was started against that host and no
Wayback request was made by this build.

---

## 2. The ceiling that decides how much of this archive is usable

**Roughly half the archive has no text layer at all.**

| Year | letters with no text layer / total |
|---|---|
| 2013 | 6 / 14 |
| 2014 | 4 / 17 |
| **2015** | **30 / 33** |
| **2016** | **37 / 38** |
| **2017** | **17 / 18** |
| **2018** | **23 / 23** |
| **2019** | **33 / 37** |
| 2020 | 8 / 44 |
| 2021 | 1 / 42 |
| 2022–2026 | 1 / 61 |

**160 of 327 letters** are image-only scans. This was verified two ways — both
PyMuPDF and `pdftotext -layout` return **zero characters**, and the PDFs contain
only page images — so it is a property of NIGC's scanning practice, not of our
extractor.

The consequence is exact and should be stated to a subscriber rather than left
to inference: **every finding, party and property in this layer comes from the
167 machine-readable letters.** FY2015–FY2019 is 140 letters of which 5 are
readable. A count of "letters finding no management contract by year" charted
off this file is charting NIGC's scanner.

**This is a bounded, cheap gap, not a research failure.** The PDFs are held,
they are legible to a human, and an OCR pass would recover them. No OCR engine
is installed in this environment (`tesseract` absent), so the work was not
attempted rather than half-attempted. That is the highest-value next action on
this layer.

### 2.1 Where a text layer exists but is degraded, and why that is dangerous

The 2013–2014 scans **do** carry OCR text and it is bad. Measured examples from
the corpus: *"it does **noi:** violate IGRA's sole proprietary interest
requirement"* (Shingle Springs, 2013-12-23), *"do not **requit\"c** the
approval"* (Poarch, 2013-11-19), *"dues **no! rcquir~** the approval of !he
Chairwoman"* (Mohegan, 2013-07-30).

**A negation eaten by OCR inverts the finding.** The first of those published as
`VIOLATION_FOUND` — the exact opposite of what the agency wrote — until the
negation tests were made OCR-tolerant (a token beginning `no` immediately before
the operative verb, plus any negation word within 90 characters before the
operative noun). All three now read correctly.

---

## 3. Findings — read only from the agency's own conclusion sentence

### 3.1 The mistake this rule exists to prevent

A first pass matched `management contract` anywhere in the letter and produced
**86 AMBIGUOUS and 11 "YES, it IS a management contract"** findings. **All
eleven were false**, and false the same way: the match was on the letter's
**question**, not its **answer** —

> "Specifically, you have asked for my opinion **whether** the Agreement **is a
> management contract** requiring the NIGC Chair's approval…"

— or on the footnoted legal standard, which states the rule affirmatively:

> "If a contract requires or permits the performance of any management activity
> …, the contract **is a management contract** within the meaning of IGRA and
> requires the Chair's approval."

Neither sentence is a finding. A finding is now read **only** from a sentence
carrying an explicit opinion marker (*"it is my opinion that"*, *"I conclude"*,
*"in my opinion"*) and **not** carrying a question marker (*whether*, *you have
asked*, *the request asks*) or a legal-standard marker (*within the meaning of
IGRA*, *C.F.R.*, *defines*).

### 3.2 Running headers invert negations across a page break

A second, quieter defect. Every page after the first repeats
`Letter to <name> / Re: <subject> / <date> / Page 2 of 2`, and a conclusion
sentence that straddles the page break extracts as

> "it is my opinion that the 2022 Loan Documents do not **Letter to Eric Dorsky
> Re: Review of Credit Agreement for Seminole Tribe of Florida May 5, 2022 Page
> 2 of 2** constitute a management contract"

A negation test for *"do not constitute a management contract"* fails and an
affirmative test for *"constitute a management contract"* succeeds. That single
defect published **two** letters — Seminole Tribe of Florida and Choctaw Nation
of Oklahoma — as finding that the agreement **is** a management contract when
both say the opposite. Running matter is now stripped before any sentence is
read.

### 3.3 What the findings say

| Question | Value | n |
|---|---|---:|
| Is it a management contract? | `NO_NOT_A_MANAGEMENT_CONTRACT` | **154** |
| | `NOT_STATED_IN_TEXT_LAYER` | 13 |
| | `NOT_EXTRACTABLE` (no text layer) | 160 |
| Chair approval required? | `NO` | **157** |
| | `NOT_STATED_IN_TEXT_LAYER` | 10 |
| | `NOT_EXTRACTABLE` | 160 |
| Sole proprietary interest | `NO_VIOLATION_FOUND` | **148** |
| | `VIOLATION_FOUND` | **1** |
| | `ADDRESSED_BUT_NOT_IN_A_CONCLUSION_SENTENCE` | 14 |
| | `NOT_ADDRESSED_IN_TEXT_LAYER` | 4 |
| | `NOT_EXTRACTABLE` | 160 |

**Zero affirmative management-contract findings survive scrutiny.** That is the
expected shape — the archive is called *declination* letters — and it is now a
measured result rather than an assumption.

**The one violation finding is real and it is conditional.** `NIGC-DL-20201020-01`,
Mashantucket Pequot Tribal Nation, the DraftKings / Crown CT Gaming sports book
agreement:

> "Upon review of these three criteria — term, compensation, and control — it is
> my opinion that **if gaming activity occurs on the Nation's Indian lands under
> the Agreement, then the Agreement violates IGRA's requirement that the Tribe
> maintain the sole proprietary interest in its gaming operation.**"

`finding_is_conditional = 1` on that row. A conditional conclusion is a
different asset from an unconditional one and must not be quoted as though the
condition were established.

**Every affirmative or unparsed finding is staged for a human** in
`review/nigc_declination_affirmative_findings_2026-08-06.csv` (1 row) with its
quote, because an affirmative finding is rare, consequential, and exactly what
an eaten negation produces by accident. Same jurisprudence as the per-UEI
ownership drops.

### 3.4 Other columns worth knowing about

- `material_change_warning = 1` on **124** of 167 readable letters, with the
  quote. The opinion lapses if the documents change materially before closing —
  which is another reason a letter is not evidence of what was executed.
- `scope_limitation_quote` on **153** letters ("this opinion is limited to …
  does not include or extend to any other agreements not submitted for review").
- `documents_unexecuted_quote` on **152**.
- Signers: Michael Hoenig **91**, Rea Cisneros **44**, Femila Ervin 2, Eric
  Shepard 1.

---

## 4. Claims, not overwrites

`data/clean/gaming_source_claims.csv` — **113 rows**, each linked to the
canonical entity and each carrying the **verbatim** language that supports it.
`supporting_text` is empty on **zero** rows, and `source_page` is populated on
**all 113**. Whitespace is collapsed; nothing else is altered.

| predicate | n |
|---|---:|
| `party_to_reviewed_agreement` | 49 |
| `administrative_agent_for` | 16 |
| `borrower_in` | 15 |
| `lender_in` | 11 |
| `wholly_owned_by` | 10 |
| `instrumentality_of` | 4 |
| `collateral_agent_for` | 2 |
| `guarantor_of` | 2 |
| `subsidiary_of` | 2 |
| `vendor_to` | 1 |
| `developer_of` | 1 |

### 4.1 Predicates added beyond the requested list, and why

- **`instrumentality_of`** — an unincorporated instrumentality of a tribe is not
  a wholly owned subsidiary. Collapsing them into `wholly_owned_by` would erase
  the legal form the letter states in words. This is the five-legal-persons rule
  operating at the predicate level.
- **`collateral_agent_for`**, **`trustee_for`** — distinct defined roles in the
  reviewed documents; folding them into `administrative_agent_for` loses which
  party holds the security.
- **`party_to_reviewed_agreement`** — records only that a party is named as a
  party to the submitted documents. It asserts no ownership, no service and no
  transaction. It is what this archive can establish and frequently the only
  public source that does.

### 4.2 What the claims preserve

`wholly_owned_by || Acoma Business Enterprises dba Sky City Casino → Pueblo of
Acoma` is the whole point of the design. The tribe, the enterprise, the dba and
the casino brand are four things, and the letter is the source that distinguishes
them.

### 4.3 `collateral` is a homonym, and the wrong sense is the common one

25 C.F.R. 502.5 defines a **"collateral agreement"** as a contract related to a
gaming operation — nothing to do with security for a loan — and the letters quote
that definition when analysing whether an arrangement is a management contract.
A bare search for `collateral` produced two `collateral_for` claims **out of the
regulatory definition**, attaching Harrah's Cherokee Casino and Harrah's Cherokee
Valley River Casino to a financing the sentence never mentions. The test now
names the security sense (`secured by`, `pledge`, `mortgage`, `leasehold deed of
trust`, `security interest in`, `as collateral for`) and rules out any sentence
carrying the regulatory sense. **Both claims were withdrawn; `collateral_for` now
has zero rows, which is the correct count.**

### 4.4 Entity resolution — 10 of 113 claim subjects resolved, on purpose

`resolve_entity` from `code/33_apply_party_rulings.py` is the only name matcher
in this build. **Containment is refused outright for a claim party.** A claim
subject is usually an enterprise, authority or property-owning subsidiary, and
containment would resolve *Twenty-Nine Palms Enterprises Corporation* onto the
tribe *Twenty-Nine Palms* — collapsing two legal persons into one, which is the
flattening this layer exists to prevent. Only exact, core and alias resolutions
are accepted; the remaining 103 subjects (banks, agents, vendors, tribal
enterprises) carry a stable `NIGCP-` party id and their verbatim name, and 106
distinct names are staged in
`review/nigc_declination_entities_held_2026-08-06.csv` with a blank
`YOUR_RULING`.

---

## 5. The containment defect, measured on this archive

AGENTS.md: *"containment may be used only to resolve an owner already named in
evidence — never to detect a match, and never to key a dollar."* Script 33 is
shared and was **not** modified; the guards live at this build's call site.

Before the guards, on NIGC's own tribe column:

| NIGC index string | containment resolved it to | class |
|---|---|---|
| `Keweenaw Bay Indian Community` | **Keweenaw Bay Ojibwa Community *College*** | Tribal College or University |
| `N/A` | **Native American *Bank*, N.A.** | Native CDFI |
| `Cherokee Nation of Oklahoma` | **United Keetoowah Band of Cherokee Indians in Oklahoma** | a *different* federally recognised tribe |
| `San Carlos Apache Tribe` | ambiguous — San Carlos Apache *College* vs a relending enterprise | (refused by script 33 itself) |

`core("N/A") = {n, a}`, which is contained in the token set of *Native American
Bank, N.A.* That is the defect in its purest form: a placeholder string
resolving to a bank.

**Two guards, because two call sites need opposite things.**

- **Tribe guard.** NIGC's `Tribe` column is a tribal government by construction,
  so a containment hit is accepted only when (a) the matched spine row is a
  government class and (b) the spine name's tokens are a **subset** of the
  record's — the direction in which containment is defensible, because the spine
  stores short canonical names (*Ione*, *Scotts Valley*) and NIGC writes the long
  official one. The subset test is what catches Cherokee Nation → United
  Keetoowah.
- **Party guard.** Containment refused outright (§4.4).

**The government classes include the constituency classes, and excluding them
cost three right answers.** *White Earth Band of Chippewa*, *Leech Lake Band of
Chippewa Indians* and *Viejas Band of Kumeyaay Indians* resolve to spine rows
classed `Federal-level constituency entity` — because that **is** their federal
status as constituent bands of the Minnesota Chippewa Tribe and the Capitan
Grande Band. The direction guard still applies and is what keeps the class from
being a loophole.

Result: **307 of 327** letters resolve to a spine entity (**140 distinct
tribes**); **20 held**. The holds are worth reading — most are NIGC's own
spellings: *San Manual*, *Cahuillla*, *Lac Court Oreilles*, *Milton Rancheria*,
*Temecula Band of Luiseno Mission*, *Kickapoo Tribe of OK*, *Shoshone – Bannock*
(en dash). A hand-ruling pass on 20 names is cheap; guessing them is not.

---

## 6. Property matching — 29 candidates, and most of the work was refusing

**A name in a letter is not a property.** Outcomes:

| outcome | n |
|---|---:|
| `EXISTING_PROPERTY_CONFIRMED` | **15** |
| `UNRESOLVED_PROPERTY_REFERENCE` | **11** |
| `POTENTIAL_NEW_PROPERTY` | **3** |
| `PROPOSED_PROPERTY` · `NON_GAMING_RELATED_ASSET` · `GAMING_ENTERPRISE_ONLY` · `EXISTING_PROPERTY_ALIAS_FOUND` | 0 |

**A match requires exact normalised name equality AND tribe agreement.** No
fuzzy matching, no containment, no coordinate proximity. Confirmed matches
include Nooksack Northwood Casino, Little River Casino Resort, Turning Stone
Resort Casino, Foxwoods Casino and Foxwoods Resort Casino, Harrah's Cherokee
Casino Resort, Harrah's Cherokee Valley River Casino, Shooting Star Casino,
Leelanau Sands Casino, Island Resort & Casino, Graton Resort & Casino,
Blackbird Bend Casino, Red Hawk Casino.

Three refusals worth recording:

1. **Generic references are not names.** *"the Tribal Casino"*, *"the Tribe's
   Casino"*, *"Operator's Casino"*, *"Tribal Bingo"* are how a letter refers to a
   property it has already named. Creating a property from one is the containment
   defect in a different guise. Dropped by a head-token rule.
2. **Title and address noise is not a name.** *"Acting General Manager Northern
   Winz Casino"*, *"Assistant General Manager Soboba Casino Resort"*, *"Statement
   Regarding Total Hotel"*.
3. **`POTENTIAL_NEW_PROPERTY` was over-claiming and was narrowed.** A name that
   does not match exactly, for a tribe that **does** hold Cedar facilities, is far
   more likely an alias of one of them — *Sky City Casino* against *Sky City
   Casino Hotel* — than a property Cedar has never heard of. Those 11 rows are
   now `UNRESOLVED_PROPERTY_REFERENCE`, and each carries that tribe's own Cedar
   facility list in `tribe_facilities_in_cedar` so a human can rule it at a
   glance. `POTENTIAL_NEW_PROPERTY` is reserved for the 3 cases where the tribe
   resolves and has **no** facility in `gaming_facilities.csv` at all.

**A letter is never attached to a property because the enterprise owns it.**
Every row carries `attachment_caution` saying so, the relation is many-to-many,
and `collateral_properties` on a financing event carries
`collateral_properties_basis` stating that a matched property is a *named* one,
not a statement about what secures the financing.

`data/clean/gaming_facilities.csv` was **not** touched — another agent owns it.
Staged output only.

---

## 7. Financing events and the double-count risk

`data/clean/gaming_financing_events.csv` — **145 events**, one per letter whose
agreement type includes a loan/credit, note/indenture/bond, or
security/collateral agreement.

| role column | events populated |
|---|---:|
| administrative agent | 16 |
| borrower | 15 |
| lender | 11 |
| collateral agent | 2 |
| guarantor | 2 |
| collateral properties (matched) | 8 |
| amendment number | 28 |
| prior-financing reference | 99 |

Agreement types across all letters: loan/credit **133**, security/collateral
**116**, amendment or restatement **68**, development/construction **24**,
technology or systems **18**, consulting/services **17**, lease **9**,
note/indenture/bond **6**, equipment or gaming-machine **4**.

**No dollar amount is published.** `principal_amount_basis` says why: loan
amounts live in the reviewed drafts, not reliably in the opinion letter, and the
drafts are unexecuted. And no property-level gaming revenue appears anywhere in
this layer, per `docs/NIGC_REGION_BUILD_LOG.md`.

### 7.1 Lineage — 25 letters are 11 relationships

**One long-running financing relationship must not be counted as several
unrelated deals.** Grouping on the whole counterparty string under-detects badly,
because NIGC's own index writes the same lender as `PNC` on one row and
`PNC Bank N.A.` on another. Events are grouped by (tribe, any *significant*
token of the counterparty string), unioned transitively, with the tokens that
are generic across the whole banking industry removed — otherwise *First Guaranty
Bank* and *First National Bank of Santa Fe* merge on "first" and two unrelated
tribes' financings become one deal.

**25 events fall into 11 chains**, each labelled
`POSSIBLE_SAME_TRANSACTION` with the span and a note that counting them as
separate deals double-counts:

| tribe / counterparty | letters | relation in text |
|---|---:|---|
| Twenty-Nine Palms / PNC Bank N.A. | 4 | FINANCING_FOR |
| Eastern Cherokee / Wells Fargo N.A. | 3 | AMENDS |
| Paskenta / Wells Fargo Bank N.A. | 2 | RESTATES |
| Pueblo of Nambe / First National Bank of Santa Fe | 2 | FINANCING_FOR |
| Poarch / PCI Gaming Authority | 2 | FINANCING_FOR |
| Sycuan / Bank of America | 2 | AMENDS |
| Wichita / Arvest Bank | 2 | FINANCING_FOR |
| Pascua Yaqui / Bank of America, N.A. | 2 | AMENDS |
| Pauma / Pauma & Yuima | 2 | AMENDS |
| Yavapai-Apache / BOKF N.A. | 2 | RESTATES |
| Pueblo of Laguna / BOKF, N.A. | 2 | FINANCING_FOR |

Relations detected in the letters' own words: `AMENDS`, `RESTATES`,
`REFINANCES`, `EXTENDS`, `SUPERSEDES`, with `FINANCING_FOR` as the fallback for
a chain that names no relation.

### 7.2 Distinct counterparties

**91 distinct counterparty strings** on financing events, **70** after
normalising the industry-generic tokens — the gap is entirely NIGC's own spelling
(`Wells Fargo N.A.` / `Wells Fargo, N.A.` / `Wells Fargo`, `U.S. Bank N.A.` /
`US Bank N.A.`). Across all 327 letters, **138** normalised counterparties. The
concentration is real and is one of the more saleable facts in this layer:
Wells Fargo 20, Bank of America 13, PNC 7, KeyBank 7, U.S. Bank 12 across two
spellings, BOKF 6, Umpqua 4, Western Alliance 3, Capital One 3.

---

## 8. Against the deals ledger — and the CONTRADICTED that isn't

`review/nigc_declination_vs_deals_2026-08-06.csv` — **30 candidate pairs**, all
`POSSIBLE_SAME_TRANSACTION`. **Zero rulings of `CONFIRMED_BY_NIGC_DOCUMENT`,
`PARTIALLY_CONFIRMED`, `CONSISTENT_BUT_EXECUTION_UNCONFIRMED` or `CONTRADICTED`
are published**, because none can be established by name overlap and date
proximity alone.

**One contradiction candidate was found, and it does not survive inspection.
That is worth more than shipping it would have been.**

`ND-2013-003` records Shingle Springs paying **$57.1M to extinguish Lakes
Entertainment debt and end the Red Hawk Casino management agreement**
(2013-08-29). `NIGC-DL-20130801-01` finds the Tribe's amended agreement with
Lakes KAR-Shingle Springs **is not a management contract and does not require
the Chair's approval** (2013-08-01). Those read as a contradiction and are not
one: the letter is about the **amended** agreement that replaced the management
contract, and it is dated four weeks **before** the payoff. A tribe can have had
an approved management contract *and* a later amended agreement that is not one —
that is the ordinary way such relationships wind down.

So `CONTRADICTED` is left for a human. The row carries
`contradiction_candidate = 1` and a `contradiction_assessment` stating what would
have to be shown — that both describe the **same** agreement — before the ruling
can be made. Publishing it as CONTRADICTED would have been a false and very
quotable claim.

---

## 9. Feeding the property triage

`review/nigc_declination_traces_2026-08-06.csv` — **13 facilities**, for the
concurrent build of `data/clean/gaming_property_federal_traces.csv`. That file
was **not** touched.

Columns: `facility_id`, `trace_nigc_declination_letter`,
`nigc_declination_opinion_count`, `nigc_declination_first_opinion_date`,
`nigc_declination_latest_opinion_date`, `nigc_declination_opinion_ids`,
`match_rule`, `trace_meaning`.

Two facilities carry more than one opinion: `CCP-335600` (2020-06-02 …
2025-05-14) and `CCP-44400` (2019-04-23 … 2024-01-19).

**A declination letter is an independent federal trace that NIGC OGC reviewed
submitted documents naming this property. It is not evidence the property opened
or operates**, and `trace_meaning` says so on every row so the sentence travels
with the join.

---

## 10. Roster diff — tribes in NIGC's archive, against ours

`review/nigc_declination_tribe_roster_diff_2026-08-06.csv`, 156 rows.

| outcome | n |
|---|---:|
| `MATCHED` | 133 |
| `IN_SOURCE_NOT_IN_CEDAR` | **7** |
| `TRIBE_NOT_RESOLVED_TO_SPINE` | 16 |

The seven leads — tribes NIGC OGC reviewed gaming documents for, where Cedar
holds no gaming facility:

| tribe | letters | span |
|---|---:|---|
| **Catawba Indian Nation** | **7** | 2019-02-19 … 2025-05-29 |
| Ione Band of Miwok Indians | 2 | 2020-03-18 … 2024-09-12 |
| Pamunkey Indian Tribe | 1 | 2017-04-05 |
| Scotts Valley Band of Pomo Indians | 1 | 2016-06-16 |
| Shawnee Tribe | 1 | 2023-06-22 |
| Tejon Indian Tribe | 1 | 2024-06-20 |
| Timbisha Shoshone Tribe | 1 | 2013-08-27 |

Catawba at seven letters over six years is the strongest single lead this build
produced — Two Kings Casino in Kings Mountain, North Carolina, financed and
developed through Delaware North and Kings Mountain entities, with no Cedar
facility row. Every row carries the ceiling note: OGC review is voluntary and
its archive is not a gaming census, so absence from it is not evidence of
absence.

---

## 11. Files written

| Path | Rows |
|---|---:|
| `data/clean/nigc_declination_letters.csv` | 327 |
| `data/clean/gaming_source_claims.csv` | 113 |
| `data/clean/gaming_financing_events.csv` | 145 |
| `review/nigc_declination_property_matches_2026-08-06.csv` | 29 |
| `review/nigc_declination_traces_2026-08-06.csv` | 13 |
| `review/nigc_declination_vs_deals_2026-08-06.csv` | 30 |
| `review/nigc_declination_tribe_roster_diff_2026-08-06.csv` | 156 |
| `review/nigc_declination_affirmative_findings_2026-08-06.csv` | 1 |
| `review/nigc_declination_entities_held_2026-08-06.csv` | 106 |
| `data/raw/external/nigc_declinations/` | index + 325 PDFs + manifest |

**Not touched, by rule:** `gaming_facilities.csv`, `nigc_regional_ggr.csv`,
`nigc_region_assignments.csv`, `admin_region*`, `resource_*`,
`series_breaks.csv`, `gaming_property_federal_traces.csv`, the entity spine.
`code/01_build_entity_spine.py` was not run.

`code/62_no_regression_check.py` reports one regression, `tier_A 2,149 → 2,148`,
originating in `cedar_identifier_ledger_tiered.csv` (mtime 17:27, before this
session's first write at 18:24). It is another build's and is reported here
rather than chased.

---

## 12. Taken on faith, and what this archive structurally cannot tell us

1. **It is not a census.** OGC review is voluntary, it is offered as a courtesy,
   and posting requires a FOIA release determination. The 327 letters are the
   subset of reviewed agreements that reached publication. **No count from this
   file is a count of tribal gaming agreements**, and no tribe's absence means
   anything.
2. **Nothing here was executed.** Every reviewed document is a draft. This layer
   can never confirm a transaction closed; that needs a different source.
3. **No dollars.** Loan amounts are in the drafts, not the letters. No amount is
   published and none should be inferred.
4. **Half of it is unread.** 160 image-only letters, concentrated in 2015–2019,
   whose findings, parties and properties are absent from every count above.
   Recoverable by OCR; not attempted here for want of an engine.
5. **Two letters are missing or wrong at the source.** One 404, and one link that
   serves another letter's PDF.
6. **The index tribe column is NIGC's, with NIGC's spellings**, and it is the
   only tribe attribution used. Where a letter's body names a different or more
   precise entity, that appears as a *claim*, never as a correction to the
   index — this build does not overwrite one source with another.
7. **Findings are as good as the sentence detector.** It reads only the agency's
   conclusion sentence; 13 readable letters state a conclusion it could not
   parse, and they are labelled `NOT_STATED_IN_TEXT_LAYER` rather than guessed.
8. **The approval-negation rule has a known blind spot.** "Any negation word
   within 90 characters before the operative noun" would misread a hypothetical
   *"is not a management contract but requires the Chair's approval"*. That
   construction does not occur in this archive — an arrangement that is not a
   management contract needs no approval by definition — but it is an assumption
   and it is recorded as one.

---
---

# COMPLETION PASS — 2026-08-07

*Script: `code/100_finish_declinations_and_employment.py`. Steps `index`, `ocr`,
`build`. Everything below supersedes the counts above where they conflict.*

## 13. Verification, before anything was changed

Fourteen checks, all **PASS**, recorded in
`review/declination_verification_2026-08-07.csv`:

| check | result |
|---|---|
| 327 letters, ids unique | PASS |
| **325 PDF objects re-hashed on disk and matched their recorded md5** — 0 differ, 0 absent | PASS |
| exactly 1 duplicated md5, and it is the disclosed Yavapai-Apache / Tunica Biloxi collision | PASS |
| 113 claims, every one with verbatim `supporting_text` and a `source_url`, 0 orphans | PASS |
| 145 financing events, 0 orphans | PASS |
| **no dollar amount published on any event** | PASS |
| `execution_status` takes exactly one value, `UNEXECUTED_DRAFTS_REVIEWED` | PASS |
| **no revenue-named column anywhere in the layer** | PASS |
| NIGC's index re-fetched today still publishes **327** rows, **0** not already held | PASS |

**Coverage is complete at the index level.** The archive published nothing new
between 2026-08-06 and 2026-08-07, and the 2026-04-14 letter remains the most
recent one NIGC has posted. The refresh writes
`_index/index_refresh_2026-08-07.{csv,json}` so the check is repeatable rather
than remembered.

The download trap was re-applied and not re-triggered: links taken only from
inside `<table id="tablepress-2">`, the two non-letter WPDM ids (`3974`
sidebar, `7374` *Helpful Hints*) refused by name, each 302 resolved so the real
**`filename=`** is known before an object is written, and every md5 compared
against everything already held. **A distinct URL is not evidence of a distinct
document; a distinct md5 is.**

## 14. The image-only ceiling is closed

Section 2 above records the binding limit on this layer: **160 of 327 letters
were image-only scans**, concentrated in FY2015–FY2019 (140 letters, 5
readable), so *every* finding, party and property came from the other 167. It
named OCR as the highest-value next action and did not attempt it, because no
OCR engine was installed.

`rapidocr-onnxruntime` is a pip-installable ONNX engine needing no system
binary. All **158** retrievable scans were rendered at 220 dpi and read, into a
cache at `data/raw/external/nigc_declinations/_ocr/` (one JSON per letter,
carrying engine, dpi, date and page text, so nothing is ever re-OCR'd).

| text layer | letters |
|---|---:|
| publisher text layer | 158 |
| **`ocr_recovered_rapidocr`** | **158** |
| text present, standard language not recovered | 9 |
| `no_text_layer` remaining | **2** |

The two that remain are the two the agency itself cannot serve: the **HTTP 404**
letter (Kalispel / Wells Fargo, 2014-05-19) and the letter whose link **serves
another letter's PDF** (Tunica Biloxi). Nothing is read out of either, by rule.

Recovered by year: 2015 **30**, 2016 **37**, 2019 **33**, 2018 **23**, 2017
**17**, 2020 **8**, 2013 **6**, 2014 **3**, 2025 **1**. Median 3,840 characters
per letter, median common-word ratio 0.45 — that is ordinary English prose, not
scanner noise.

### 14.1 What that recovered — this supersedes 3.3

| question | value | 08-06 | **08-07** |
|---|---|---:|---:|
| Is it a management contract? | `NO_NOT_A_MANAGEMENT_CONTRACT` | 154 | **284** |
| | not stated in the readable text | 13 | 41 |
| | `NOT_EXTRACTABLE` | 160 | **2** |
| Chair approval required? | `NO` | 157 | **286** |
| Sole proprietary interest | `NO_VIOLATION_FOUND` | 148 | **284** |
| | `VIOLATION_FOUND` | 1 | **1** |

**Still exactly one violation finding, and it is still the conditional
Mashantucket Pequot / DraftKings sports-book opinion.** Doubling the read corpus
did not produce a second one. That is the expected shape of a *declination*
archive and it is now measured across the whole of it rather than across half.

**Zero affirmative management-contract findings survived from OCR text.** Every
affirmative would have been staged in
`review/nigc_declination_ocr_affirmative_2026-08-07.csv`; the file is absent
because there were none.

Also recovered from the 158: **137** carry the agency's own
`documents_unexecuted` sentence in their own words, **123** carry the
material-change warning, **118** carry the scope limitation.

### 14.2 OCR text is marked as OCR text, permanently

Section 2.1 records that OCR ate a negation on the 2013 Shingle Springs letter
and published `VIOLATION_FOUND` — the exact inverse of what the agency wrote.
That risk does not go away by scaling OCR up; it scales with it. So every
recovered row carries `text_recovery_status`, `ocr_engine`, `ocr_dpi`,
`ocr_date`, `ocr_text_chars`, `ocr_common_word_ratio`, `finding_evidence_basis =
OCR_RECOVERED`, and an `ocr_caution` saying in words that a quote from the row
should be checked against the PDF before it is published as the agency's.

The findings themselves are read with **script 91's own readers, imported, not
reimplemented** — the OCR-tolerant negation tests, the running-header stripper,
and the rule that a finding comes only from a sentence carrying an opinion
marker and *not* a question or legal-standard marker. A second extractor would
be a second definition of what a finding is.

Party **claims** were *not* merged from OCR text. Names are the fragile part of
a scan and a garbled name is a false attribution, so the 6 candidates are staged
in `review/nigc_declination_ocr_claims_2026-08-07.csv` with a blank
`YOUR_RULING`. `gaming_source_claims.csv` stays at **113** verbatim-supported
rows.

## 15. Financing events: 145 to 293

The 160 image-only letters produced **zero** financing events, because a
financing event is typed off the agreement language and there was none to read.
With the text recovered, **148 new events** were derived and appended, each
carrying `text_basis = OCR_RECOVERED`.

`gaming_financing_events.csv` is now **293 rows**. Agreement types across them:
loan/credit **137**, security/collateral **131**, amendment or restatement
**49**, development/construction **26**, note/indenture/bond **19**,
consulting/services **11**.

**No dollar amount is published on any of them**, for the same reason as before:
loan amounts live in the reviewed drafts, and the drafts are unexecuted.

## 16. The evidentiary ladder is now a COLUMN

The ladder was previously a sentence in this document. A sentence in a document
does not survive a join. It is now written on every row of all three files:

```text
NIGC_REVIEWED -> EXECUTION_UNCONFIRMED -> EXECUTED_CONFIRMED
              -> CLOSED_CONFIRMED -> SUPERSEDED / TERMINATED
```

- **Letters** carry `evidentiary_stage = NIGC_REVIEWED`, plus
  `evidentiary_stage_basis` (the agency's own sentence),
  `what_this_does_not_establish` (execution, closing, construction, opening,
  continued operation, land status, gaming eligibility) and
  `what_would_advance_the_stage` (which document class moves it up a rung).
- **Financing events** carry `evidentiary_stage = EXECUTION_UNCONFIRMED` and
  `property_attachment_caution`: a financing is **never** attached to a property
  because the enterprise owns that property. Financings routinely cover several
  properties, the whole enterprise, unrestricted assets, or a project that does
  not exist yet. The relation is many-to-many and a matched property means only
  that the property was **named**.
- **Claims** carry `evidentiary_stage = NIGC_REVIEWED` and
  `claim_scope_caution`: tribe, gaming authority, gaming enterprise,
  property-owning subsidiary and operating company are **five different legal
  persons** and are not interchangeable.

**This build can only ever establish the first two rungs.** Anything past
`EXECUTION_UNCONFIRMED` needs a different source, and the column that says so
travels with the row.

## 17. Against the deals ledger

`review/declination_contradictions_2026-08-07.csv`, 150 rows, in two clearly
separated sections (`comparison_side`).

### 17.1 The deals-ledger comparison — 69 rows

| ruling | n |
|---|---:|
| `POSSIBLE_SAME_TRANSACTION` | 31 |
| `CONSISTENT_BUT_EXECUTION_UNCONFIRMED` | 22 |
| `NOT_ESTABLISHED` | 9 |
| **`PARTIALLY_CONFIRMED`** | **7** |
| **`CONTRADICTED`** | **0** |
| `CONFIRMED_BY_NIGC_DOCUMENT` | 0 |

**`PARTIALLY_CONFIRMED` is the ruling this layer can actually earn**, and it
means something precise: a federal legal opinion independently establishes that
these parties negotiated this financing and that NIGC reviewed its documents in
this window. It does **not** establish that the financing closed on the ledger's
date or terms.

The best of the seven exists **only because of the OCR pass**:

> `ND-2025-004` — *Ho-Chunk Nation closes $610M financing for Beloit casino
> resort*, 2025-09-26, counterparty *"Bank syndicate led by KeyBanc Capital
> Markets"*, sourced to a trade-press article.
>
> `NIGC-DL-20250820-01` — an image-only scan, unread until 2026-08-07, whose
> recovered subject line is *"Review of Financing Agreements for New Casino
> Resort in Beloit Wisconsin"* and whose text describes *"financing documents
> between the Ho-Chunk Nation and a syndicate of lenders to finance the
> development and construction of a new casino resort facility in Beloit,
> Wisconsin"* — **37 days before the reported close.**

The lender strings agree on nothing (`Lender` against `KeyBanc`). The **place**
agrees, and the place is the more specific token. That is why the matcher tests
project tokens as well as counterparty tokens.

### 17.2 Zero `CONTRADICTED`, and the three false ones that were refused

The brief's highest-value output is a case where the deals ledger calls a
company a casino manager and the NIGC letter establishes the reviewed
arrangement was **not** a management contract. **None survives, and three
candidates were refused for stated reasons. Each refusal is a rule now in the
code.**

1. **Overlap manufactured out of the tribe's own name.** An early pass computed
   counterparty overlap against the letter's `Re:` line — which contains the
   tribe name — so *Shingle Springs* matched *Shingle Springs* and a
   counterparty match appeared from nothing. Overlap is now computed on the
   counterparty strings only, with the tribe's tokens removed from both sides.
2. **A wind-down is not a contradiction.** `ND-2013-003` records Shingle Springs
   paying $57.1M to extinguish Lakes Entertainment debt and **end** the Red Hawk
   management agreement; `NIGC-DL-20130801-01` finds the **amended** agreement is
   not a management contract, four weeks earlier. Same parties, and it reads as a
   flat contradiction. It is not one — a tribe can have had a Chair-approved
   management contract *and* a later amending or terminating instrument that is
   not one, and the ledger row says so in its own words (*"approved by the
   National Indian Gaming Commission on July 19, 2004 — were terminated"*).
   The 08-06 build reached the same conclusion by hand; it is now a coded rule,
   and the row publishes as `CONSISTENT_BUT_EXECUTION_UNCONFIRMED` with
   `contradiction_candidate = 1` so a human still sees it.
3. **A lender is never the alleged casino manager.** `ND-2016-003` records
   Jamul's $460M credit facilities and, in the same row, describes Penn
   National's development, management and branding role. The matching letter's
   counterparty is **Citizens Bank**. Token overlap on `citizens` plus manager
   language *somewhere in the row* produced a `CONTRADICTED` — against a bank,
   about a role a different company was said to hold. Two guards now apply: the
   matched counterparty may not be a lender, and the manager language must sit
   **within 250 characters of that company's name**, not merely in the same row.

A fourth guard was needed after OCR: a shared *project* word may support
`PARTIALLY_CONFIRMED` but **never** `CONTRADICTED`, because a contradiction is a
claim about a named company's legal role and has to be established on the party
names. The word that exposed this was `certain`, shared between an OCR'd letter
and a deal description.

### 17.3 Why the ledger yields no contradiction, and where the next one comes from

**This is a coverage property of the deals ledger, not a limit of the letters.**
The ledger's 77 gaming rows are almost entirely **finance** — credit facilities,
notes, refinancings — because that is where SEC and EMMA filings are. Across all
1,712 deal rows there are **four** with manager language and **two** carrying the
phrase *management contract*, and neither of those two is a gaming row.

There is also a structural asymmetry worth stating plainly, because it is what
makes `CONTRADICTED` both rare and valuable:

> **A document that IS a management contract goes to the NIGC *Chair* for
> approval under 25 U.S.C. 2711. A document a tribe hopes is NOT one goes to
> *OGC* for a declination.** So this archive is, by construction, the set of
> arrangements the agency found were **not** management contracts. It can
> therefore never *confirm* a management contract — which is why `ND-2017-002`,
> the Cowlitz / Salishan-Mohegan management agreement for ilani that NIGC
> **approved**, correctly rules `NOT_ESTABLISHED` here — and it **can**
> contradict a press description that calls a counterparty the casino's manager.

So the second section of the file builds the surface where that contradiction
will land.

### 17.4 The contradiction-ready surface — 81 rows

For every letter whose counterparty is an **operator-type** company rather than
a lender — a consultant, developer, sportsbook, gaming-services firm, or another
tribe's enterprise — a row is emitted carrying the agency's answer, ruled
`NOT_ESTABLISHED`, with a `public_characterisation_to_check` naming the company
and the tribe. **For each of these the agency has already answered, in writing,
the exact question that a description of "the casino's manager" implicitly
asserts.**

They include Catawba / **DNC Gaming**, Spokane / **WG Airway Heights**, North
Fork Rancheria / **SC Madera Development**, Chippewa Cree / **Century Gaming**,
Chehalis / **The Hartman Gaming Group**, Pamunkey / **Golden Eagle Consulting
II**, Kaw Gaming / **Cherokee Nation Hospitality Consulting**, Buena Vista /
**Warner BV AR Consulting**, Elk Valley / **Performance Equity Partners**,
Little River / **GCG Superior**, Oneida / **Turning Stone Resort Casino LLC and
Caesars Entertainment Services**. **This is the highest-value list this build
produced** and it is where the next quarter's deals capture should aim.

## 18. What this archive still structurally cannot tell us

The 08-06 section 12 list stands, with one item closed and one added.

1. **It is not a census.** OGC review is voluntary, offered as a courtesy, and
   posting requires a FOIA release determination. **No count from this file is a
   count of tribal gaming agreements, and no tribe's absence means anything.**
2. **Nothing here was executed.** Every reviewed document is a draft. This layer
   can never confirm a transaction closed.
3. **No dollars.** Loan amounts are in the drafts, not the letters.
4. ~~Half of it is unread.~~ **CLOSED.** 158 of 160 recovered; the 2 that remain
   are the agency's own 404 and its own mis-served link.
5. **Two letters are missing or wrong at the source**, and that is the agency's
   defect, recorded not repaired.
6. **The index tribe column is NIGC's, with NIGC's spellings**, and it is the
   only tribe attribution used. A more precise entity in a letter's body appears
   as a **claim**, never as a correction to the index.
7. **Findings are as good as the sentence detector**, and 41 readable letters
   state a conclusion it could not parse. They are labelled, not guessed.
8. **The approval-negation rule has a known blind spot** — *"is not a management
   contract but requires the Chair's approval"* would misread. That construction
   does not occur here, and it is recorded as an assumption rather than a fact.
9. **NEW: OCR-recovered findings are one remove further from the agency's own
   words than text-layer findings.** They are marked as such on every row and
   should not be quoted verbatim as the agency's language without a glance at
   the PDF. 284 findings now rest partly on a scanner and an ONNX model; 154 of
   them rest on a publisher text layer. **The two are distinguishable in the
   data, and that is the point.**

## 19. Files written 2026-08-07

| path | rows |
|---|---:|
| `data/clean/nigc_declination_letters.csv` | 327 (12 new columns) |
| `data/clean/gaming_financing_events.csv` | **293** (was 145) |
| `data/clean/gaming_source_claims.csv` | 113 (3 new columns) |
| `review/declination_contradictions_2026-08-07.csv` | 150 |
| `review/declination_verification_2026-08-07.csv` | 14 |
| `review/nigc_declination_ocr_claims_2026-08-07.csv` | 6 |
| `data/raw/external/nigc_declinations/_ocr/` | 158 JSON |
| `docs/codebooks/07d_nigc_declination_variables.md` | variables |

`.bak_2026-08-07_pre100` snapshots were taken of all three clean files, and the
build **restores from them on every run** so a rerun is deterministic rather
than layering a second pass on the first.

**Not touched, by rule:** `gaming_facilities.csv`, `gaming_capacity_official.csv`,
`compact_*`, `nigc_regional_ggr.csv`, `nigc_region_assignments.csv`,
`subawards.csv`, `consultation_*`, `oira_meetings.csv`,
`hearing_appearances.csv`, `earmarks.csv`, `np_financials.csv`, `nagpra_*`,
`federal_recognition_*`, `entity_aliases.csv`, `entity_relationships.csv`, the
entity spine. **`code/01_build_entity_spine.py` was not run.**

### 19.1 A codebook append does not survive a concurrent agent

The new variables were first appended to `docs/codebooks/07_gaming.md`. That
file is **regenerated by `code/24_generate_dataset_docs.py`**, and a concurrent
agent regenerated it within the hour - the append was made, verified on disk,
and gone twenty minutes later. It now writes
`docs/codebooks/07d_nigc_declination_variables.md`, a file this build owns.
**Generated files are not a place to record hand-written knowledge**, and that
is worth a line in whichever standing doc collects cross-agent rules.

`code/62_no_regression_check.py` reports one regression,
`codebook_undocumented_public = 10`. All ten are in `06_nonprofit` (nine
Schedule C / Form 990-PF lobbying variables) and `12_resources`
(`source_system`), in a `codebook_master.csv` regenerated at 18:40 by another
build. It is reported here rather than chased, on the same footing as the
`tier_A 2,149 -> 2,148` note in the 08-06 section.

## 20. Pull discipline

One host, one poller: `logs/_HOSTLOCK_www.nigc.gov.json` claimed before the
index refresh and released on completion. One HTTP request was issued against
nigc.gov this session (the index), status 200, no PDF re-fetched because nothing
new was published. The OCR pass is entirely local and issued **zero** network
requests. **`api.usaspending.gov` was not touched** — it is edge-blocking us and
another agent holds its lock.

---

## 21. The codebook block is complete — 2026-08-26

`code/62_no_regression_check.py` had been failing on
`codebook_undocumented_public = 45` since this layer was registered, and **all
45 were this block.** Six agent sessions reported it as "pre-existing, not
mine" and moved on, which meant every other regression that gate could have
raised was hidden behind it.

The cause was specific, not general neglect. §19 records that script 100 wrote
`docs/codebooks/07d_nigc_declination_variables.md` — and that file covers
**only the 13 columns script 100 added**. The other 47, all from
`code/91_build_nigc_declinations.py`, had no machine-readable definition
anywhere. 45 of the 47 are `published = 1`, so the gate counted exactly those.

`code/174_document_nigc_declination_codebook.py` wrote all 47 — the two
`internal` ones too — into both `data/clean/codebook/07o_nigc_declinations.csv`
and the `07o` rows of `codebook_master.csv`. **Every definition is traceable and
carries its source in the script beside it**: the assignment in 91 or 100 that
writes the column, the section of THIS log that explains what it is for, and the
value distribution measured across the 327 rows. Several definitions are worth
more than a gloss because the column exists to stop a specific defect —
`n_conclusion_sentences` carries the 11-false-affirmatives finding from §3.1,
`text_chars` carries the 400-character scan threshold from §2,
`sole_proprietary_interest_quote` carries the "Nor, in my opinion, do they
violate" negation from §3.3, and `re_line` carries the reason counterparty
overlap is never computed against it (§17.2.1).

**Nothing was invented to clear the counter.** One column was tiered `internal`
rather than published: `pdf_path`, because its value is a working path under
`data/raw/` on the build machine and not a citation — `resolved_pdf_url` and
`index_url` are the public references to the same object. It still carries its
definition.

`cedar_codebook.py build` was **not** used. `check` reports a rebuild would LOSE
28 rows (the four `cedar_filer_entity_*` columns on two `04e_schedule_i_*`
blocks), which is the shrinking-codebook bug that module exists to prevent. Both
files were patched in place, `.part` then rename, with a `.bak_2026-08-26_pre174`
beside each. Descriptions were filled **only where blank**, so no hand-written
description was overwritten.

Gate result: `codebook_undocumented_public` **45 → 0**, and the whole gate green.
