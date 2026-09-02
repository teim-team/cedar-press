# Federal recognition history — build log

> **TWO DOCUMENTS COVER THIS BUILD. THEY ARE COMPANIONS, NOT RIVALS — read both.**
> *Cross-link added 2026-08-28 during doc consolidation. Neither supersedes the
> other; they were written by two agents about the same run and they cover
> different halves. Checked for supersession and found none, so neither was
> retired.*
>
> - **This file** — the **METHOD**: notice selection, de-wrapping the GPO text,
>   the four meanings of a parenthesis, entity identity across notices, the
>   118-rename bridging pass, the 10 repaired two-tribe source lines.
> - **`docs/RECOGNITION_HISTORY_BUILD_LOG.md`** — the **VERIFICATION AND THE
>   DEFECTS**: internal-consistency checks, the alias-proposal safety gap, the
>   selected notice that produced no roster rows, `event_type` over-stating
>   recognitions, the 1,336 rows dead-ending on `ambiguous_core`.
>
> Where the two restate the same count they agree (366 events, 17,058 roster
> rows, 341 entity-keyed events).

*`code/76_build_recognition_history.py`, run 2026-08-06. Every number here is recomputed from the data on each run; none is hand-edited (standing rule 10).*

## What this is

The BIA has been required to publish the list of federally recognized tribes annually since the Federally Recognized Indian Tribe List Act of 1994 (Pub. L. 103-454). Each notice is a snapshot; the difference between consecutive snapshots is an event. Two files come out of that:

- `data/clean/federal_recognition_roster.csv` — 17,058 rows, one per listed entry per notice, 1995–2026.
- `data/clean/federal_recognition_events.csv` — 366 events, 341 of them carrying a spine `tribe_id`.

## Which notices were retrievable

Source: Federal Register API v1 (`federalregister.gov/api/v1/documents.json`) — free, GET, no key. A full-text search for `"Indian Entities Recognized"` returns every document that *mentions* the list; selection is on the **title**, because a document that cites the list is not the list. Accepted and rejected candidates are both in `data/raw/external/fr_recognized/_notice_manifest.csv`.

- **32 documents selected by title**, **30 of them full rosters**, 1995–2026.
- **2 selected documents are not rosters**: `2010-27138`, `2021-06723`. One is the 2010 supplement adding the Shinnecock Indian Nation, one the 2021 correction of three names. Both carry real events and are parsed for them separately.
- **Nothing was unretrievable.** Every selected notice returned its raw text on the first request.

### Calendar years with no annual notice

The List Act says annually; in practice the BIA has missed years and doubled up in others. Years in 1994–2026 with no notice: 1994, 1999, 2001, 2004, 2006, 2011, 2025.

Two of those absences are findings rather than gaps in this build:

- **1994.** The previous list was published 1993-10-21 (58 FR 54364), before the Federal Register API's 1994 floor. The 1995 notice says so itself: *"The list is updated from the last such list published October 21, 1993 (58 FR 54364)"*. The window therefore opens at 1995-02-16 and no pre-1995 diff is possible from this source.
- **2025.** No annual list was published in calendar 2025. The 2024-12-11 notice (89 FR 99899) governs through 2025 and the next is 2026-01-30 (91 FR 4102). A BIA-agency search across 2025 returns no list document — the absence was checked, not assumed.

## Method

### De-wrapping the GPO text

1. A wrapped line ends with a trailing space; a complete entry does not.
2. A line that leaves a bracket **open** is also a wrap. GPO breaks at a hyphen (`Alabama-` / `Coushatta Tribes of Texas]`) and once mid-phrase (`... St. Regis Band of Mohawk Indians` / `of New York)`); rule 1 alone splits those into phantom tribes.
3. Rule 2 **backs out** if four further lines do not close the bracket. The 2014 notice contains an unclosed paren in the source — `Northwestern Band of Shoshoni Nation of Utah (Washakie` — and an unbounded rule 2 swallowed the remaining 90 tribes into one 6,016-character row.
4. `[[Page NNNN]]` markers are removed **with the blank lines around them**. Inline, the marker appends a trailing space and makes a complete entry look wrapped. Standalone, it arrives as blank/marker/blank dropped into the middle of an entry — that is how the 2003 notice splits the Sisseton-Wahpeton Oyate's former name into a phantom `Sioux Tribe of the Lake Traverse Reservation)`.

### Four meanings of a parenthesis, kept apart

| Form | Meaning | Treatment |
|---|---|---|
| `(previously listed as X)`, `[previously listed as X]`, `(formerly X)` | RENAME | X becomes an alias of the same entity |
| `(See Y)` | CROSS-REFERENCE | a listed tribe whose affairs Y conducts; recorded in `see_instead` and **never merged into Y** |
| `(See Supplementary Information ...)` | pointer to the preamble | **not** a cross-reference — the 2026 Lumbee entry uses one, and a naive `(See` rule turns the most important event in the dataset into a pointer |
| `(A; B)`, or a trailing colon with indented lines | CONSTITUENT parts | recorded in `constituents` / `parent_fr_name`, excluded from counts |

`(aka X)` is stripped into `also_known_as`: it is an alias, not part of the name, and leaving it attached makes `Native Village of Chenega (aka Chanega)` and `Native Village of Chenega` look like two tribes across the 2026 notice.

### Entity identity across notices

A name-level diff is meaningless here — the 2012 notice alone restyles about a hundred entries, and diffing raw names reports ~100 additions and ~98 removals for that year alone. Identity is union-find over four signals, in descending authority:

1. the notice's own `previously listed as` — the BIA saying these are one nation. The declared old name is **fuzzy-matched to the name actually listed in an earlier notice**, because the BIA writes it from memory: 1998 says *"(formerly the Coast Indian Community of Yurok Indians of the Resighini Rancheria)"* while the 1997 list reads `... Resighini Rancheria, California`.
2. a shared spine `tribe_id`, **but only from `exact` and `alias` resolution**. `containment` is good enough to attribute a contract and far too loose to assert that two listings are one nation: measured on this corpus it sent *Alturas Indian Rancheria of Pit River Indians of California* to the **Pit River Tribe**, *Cherokee Nation, Oklahoma* to the **United Keetoowah Band**, and *Jena Band of Choctaw Indians, Louisiana* to a **state-recognized** Louisiana Choctaw band. Each merge then *masks* a real event.
3. normalised name equality (`St.` expanded to `Saint`).
4. a bridging pass over what is left, described next.

Result: **705 distinct entities** across the window.

Entity resolution itself is `resolve_entity` from `code/33_apply_party_rulings.py`. No matching logic is re-implemented here (standing rule 8).

### The bridging pass — 118 unmarked renames

Only names left over after exact and declared-rename matching, only between **consecutive** notices, only one-to-one, best pair first. Two rules:

- **typographic_variant** — difflib ratio >= 0.90. The notices carry real drift: `Qawalingin`/`Qawalangin`, `San Manual`/`San Manuel`, `Sokoagon`/`Sokaogon`, `Chuatbaluk`/`Chuathbaluk`, `Muskogee`/`Muscogee`, `Artic Village`/`Arctic Village`. Each pair is one nation; publishing it as a removal plus an addition would assert that a tribe lost and regained federal recognition.
- **bia_shortened_the_listed_name** — the shorter name's identifying tokens are all inside the longer's, they are at least half of the longer's, **and both names lead with the same identifying word**. The leading-word test is load-bearing: `core` is a set and discards word order, and without it the rule paired the Wichita and Affiliated Tribes with the White Mountain Apache Tribe, the Potter Valley Rancheria with the Port Gamble Indian Community, and the Muscogee (Creek) Nation with the Muckleshoot Indian Tribe.

It refuses `Chickahominy Indian Tribe` against `Chickahominy Indian Tribe--Eastern Division` — two different tribes, both recognised in 2018 by the same Act.

| rule | n |
|---|---:|
| typographic_variant | 60 |
| bia_shortened_the_listed_name | 58 |

### Source lines carrying two tribes — 10 repaired

Some entries arrive with the separator lost. The 2015 notice prints `Eklutna Native VillageEmmonak Village` as one line; the 2018 notice runs `... Rancheria of California) Tejon Indian Tribe` together. Left alone, both tribes vanish from that year and the dataset publishes them as removed from federal recognition and then restored.

The split fires only where **both halves are names other notices carry** (a real listing recurs; a glue artefact appears once), the left half has balanced brackets, and both halves are at least 12 characters. The original string is kept in `entry_raw_source` on both rows.

- `Arctic Village (See Native Village of Venetie Tribal Government) Native Village of Atka` -> `Arctic Village (See Native Village of Veneti` + `Native Village of Atka`
- `Arctic Village (See Native Village of Venetie Tribal Government) Native Village of Atka` -> `Arctic Village (See Native Village of Veneti` + `Native Village of Atka`
- `White Mountain Apache Tribe of the Fort Apache Reservation, Arizona Wichita and Affiliated Tribe` -> `White Mountain Apache Tribe of the Fort Apac` + `Wichita and Affiliated Tribes (Wichita, Keec`
- `Port Gamble Indian Community of the Port Gamble Reservation, Washington Potter Valley Rancheria ` -> `Port Gamble Indian Community of the Port Gam` + `Potter Valley Rancheria of Pomo Indians of C`
- `Muckleshoot Indian Tribe of the Muckleshoot Reservation, Washington Muscogee (Creek) Nation, Okl` -> `Muckleshoot Indian Tribe of the Muckleshoot ` + `Muscogee (Creek) Nation, Oklahoma`
- `Capitan Grande Band of Diegueno Mission Indians of California: Barona Group of Capitan Grande Ba` -> `Capitan Grande Band of Diegueno Mission Indi` + `Viejas (Baron Long) Group of Capitan Grande `
- `Eklutna Native VillageEmmonak Village` -> `Eklutna Native Village` + `Emmonak Village`
- `Pala Band of Mission Indians (previously listed as the Pala Band of Luiseno Mission Indians of t` -> `Pala Band of Mission Indians (previously lis` + `Pascua Yaqui Tribe of Arizona`
- `Table Mountain Rancheria (previously listed as the Table Mountain Rancheria of California) Tejon` -> `Table Mountain Rancheria (previously listed ` + `Tejon Indian Tribe`
- `Qagan Tayagungin Tribe of Sand Point (previously listed as Qagan Tayagungin Tribe of Sand Point ` -> `Qagan Tayagungin Tribe of Sand Point (previo` + `Qawalangin Tribe of Unalaska`

## Parsed count vs the count each notice states about itself

Every notice declares its own total in the SUMMARY, and the 2022 notice also prints bracketed per-section counts. That is a free, independent check on the parse — reported here, not reconciled away.

| document | published | parsed listed | notice states | diff |
|---|---|---:|---:|---:|
| `95-3839` | 1995-02-16 | 552 | — | — |
| `96-28935` | 1996-11-13 | 556 | — | — |
| `97-28018` | 1997-10-23 | 556 | — | — |
| `98-34476` | 1998-12-30 | 556 | — | — |
| `00-6064` | 2000-03-13 | 558 | 556 | 2 |
| `02-17508` | 2002-07-12 | 564 | 562 | 2 |
| `03-30244` | 2003-12-05 | 564 | 562 | 2 |
| `05-23268` | 2005-11-25 | 563 | 561 | 2 |
| `E7-5220` | 2007-03-22 | 563 | 561 | 2 |
| `E8-6968` | 2008-04-04 | 564 | 562 | 2 |
| `E9-19124` | 2009-08-11 | 566 | 564 | 2 |
| `2010-24640` | 2010-10-01 | 566 | 564 | 2 |
| `2012-19588` | 2012-08-10 | 568 | 566 | 2 |
| `2013-10649` | 2013-05-06 | 568 | 566 | 2 |
| `2014-01683` | 2014-01-29 | 568 | 566 | 2 |
| `2015-00509` | 2015-01-14 | 569 | 566 | 3 |
| `2016-01769` | 2016-01-29 | 568 | 566 | 2 |
| `2016-10408` | 2016-05-04 | 569 | 567 | 2 |
| `2017-00912` | 2017-01-17 | 569 | 567 | 2 |
| `2018-01907` | 2018-01-30 | 569 | 567 | 2 |
| `2018-15679` | 2018-07-23 | 575 | 573 | 2 |
| `2019-00897` | 2019-02-01 | 575 | 573 | 2 |
| `2020-01707` | 2020-01-30 | 576 | 574 | 2 |
| `2021-01606` | 2021-01-29 | 576 | 574 | 2 |
| `2022-01789` | 2022-01-28 | 574 | 574 | 0 |
| `2023-00504` | 2023-01-12 | 574 | 574 | 0 |
| `2023-17195` | 2023-08-11 | 576 | 574 | 2 |
| `2024-00109` | 2024-01-08 | 576 | 574 | 2 |
| `2024-29005` | 2024-12-11 | 576 | 574 | 2 |
| `2026-01899` | 2026-01-30 | 577 | 575 | 2 |

**Reading the residuals.** The 2022 notice is the only one that prints its own per-section counts, `[347 ...]` and `[227 ...]`; the parse reproduces both exactly, and 347 + 227 = 574 is its stated total. Elsewhere the parse runs **+2**, and the +2 has a name: the Native Village of Venetie Tribal Government and the Pribilof Islands Aleut Communities, which the BIA excludes from its own count. The 2022 and 2023-01 notices say so explicitly, in a *Clarification* section reading *"is not included in the official count of 574 federally recognized Indian Tribes but is recognized as an entity authorized to act on behalf of ..."* — and those are exactly the two years the residual is 0, because there the two sit in that section rather than in the lists.

The 2015 notice is +3. Its extra row is real and is the BIA's: that notice lists **both** `Native Village of Old Harbor (previously listed as Village of Old Harbor)` **and** `Village of Old Harbor`, having left the superseded entry in place.

## Events

| event type | n |
|---|---:|
| RENAMED | 319 |
| ADDED | 35 |
| REMOVED | 11 |
| RESTORED | 1 |

Of the 319 renames, **186 are marked by the notice itself** with `previously listed as` / `formerly`; the rest are unmarked changes bridged by the pass above, each carrying its rule and score in `mechanism_basis`.

**A removal is not a termination.** Removals are as often a merge into another listing, an unmarked rename, or a correction. `mechanism` stays blank and `mechanism_basis` reads `not_stated_in_record; a removal is not evidence of termination` unless a Federal Register document says otherwise. The one removal in this window with a stated legal reason is the **Delaware Tribe of Indians**, removed in the 2005-11-25 notice *"in response to a final judgment and order sought by the Cherokee Nation of Oklahoma in the United States District Court"* and restored in 2009 after reorganising under the Oklahoma Indian Welfare Act.

`review_flag = possible_unmarked_rename` is set on **16** ADDED/REMOVED rows that have a same-notice look-alike above 0.60 similarity but did not clear the bridging bar — `Narragansett Indian Tribe of Rhode Island` -> `Narragansett Indian Tribe` is the shape. They are flagged, not asserted; `possible_rename_counterpart` names the other row.

### Mechanism, where the record states one

| mechanism | n |
|---|---:|
| name_change_listed_by_bia | 319 |
| (not stated in the record) | 24 |
| act_of_congress | 10 |
| administrative_acknowledgment_25cfr83 | 7 |
| administrative_reaffirmation | 3 |
| court_order | 2 |
| administrative_appeal_order_ibia | 1 |

The mechanism is read from the **quote** first and only then from the sentences around it, and `mechanism_basis` says which. Reading the window first put `administrative_reaffirmation` on the Cowlitz Indian Tribe because the *next* sentence reaffirms three Alaska tribes; Cowlitz's own sentence says it *"was acknowledged under 25 CFR part 83."*

### Where each quote comes from

Every event carries a verbatim quote and a `quote_basis` naming the document it was taken from, so a quote can never be mistaken for an inference. `quote_context` holds the surrounding sentences when the quote came from a notice preamble.

| quote_basis | n |
|---|---:|
| roster_line | 199 |
| roster_lines_both_notices | 130 |
| notice_preamble | 21 |
| roster_line_of_prior_notice | 10 |
| related_fr_document | 3 |
| correction_notice | 3 |

## Recognition tied to legislation

Three links, descending in certainty, never mixed:

- **`public_law_cited`** — 3 events carry a public law number taken from the Federal Register text that evidences that event.
- **`statute_named`** — 8 carry the Act's title exactly as the notice writes it, for the statutes the BIA names without a number.
- **`bill_ids`** — 11 join to `data/clean/native_bills.csv`. `bill_link_basis` distinguishes `enacted_public_law_number_matches_native_bills_latest_action` (the bill became that law) from `bill_title_names_the_tribe_and_recognition` (a recognition bill for that tribe, introduced within 12 years before the listing — **explicitly not evidence that it caused the listing**). The window matters: without it the Samish Indian Tribe's 1996 acknowledgment was linked to House bills from 2019, 2021 and 2023.

`native_bills.csv` and `bill_votes.csv` are **read, never written** — a bills-and-votes agent owns them. The join key is written onto our rows.

### The worked example

**Lumbee Tribe of North Carolina**, ADDED 2026-01-30, 91 FR 4102:

> This list includes the addition of the Lumbee Tribe of North Carolina following the enactment of the National Defense Authorization Act for Fiscal Year 2026 on December 18, 2025.

`mechanism` = `act_of_congress` · `public_law_cited` = `Pub. L. 119-60` · `statute_named` = `National Defense Authorization Act` · `bill_ids` = `116-hr-1964; 117-s-1364`

The public law number sits one sentence past the quote — *"See Public Law 119-60, section 8803."* — with the hyphen carrying a line break, so the citation reads `119- 60` in the raw text. That is why the statute pattern tolerates whitespace around the dash.

## Historical names for the spine

`review/recognition_alias_proposals.csv` — **298 names** across **229 entities** that appear in a Federal Register recognition notice and are not already in the spine's `canonical_name`, `aliases` or `fr_official_name`. Each row carries the FR document, its citation, its publication date and the verbatim entry the name came from, plus an empty `YOUR_RULING` column.

**This is the product benefit Elijah named.** A tribe listed in 2005 under one name and renamed in 2015 appears in the contracting and funding rows of that era under the old name. Feeding these names into `aliases` is what makes those rows resolve.

Each row carries `resolve_confidence`: **high** where the FR name resolved to the spine exactly or through an existing alias, **medium** on identifying-token equality, **low** on containment. The file sorts high first.

**20 candidate aliases were dropped, not proposed**, and are in `review/recognition_alias_dropped.csv` with their reason. Each is a containment match whose leading identifying word differs from the spine entity it landed on, and the three worst show why the guard exists: *Cherokee Nation of Oklahoma* resolved to the **United Keetoowah Band**, *Alturas Indian Rancheria of Pit River Indians of California* to the **Pit River Tribe**, and *Hoopa Valley Tribe of the Hoopa Valley Reservation, California* to the **California Valley Miwok Tribe**. Merging any of those would send one nation's entire 1990s-2000s contracting history to another. The guard also drops a few correct ones — *Covelo Indian Community* really is the Round Valley Indian Tribes' former name — which is why they are written out for a ruling instead of discarded.

The file is a **proposal, not an edit**. Four agents are concurrently adding `TCU-`, `CDFI-`, `BIE-` and `UIO-` entities to `data/spine/cedar_entity_spine.csv`; this script never opens it for writing.

## Scope

State-recognized tribes are not on this federal roster and their absence from it is not evidence of anything. Cedar Press carries 64 of them from the CICD roster under `TRBS-`. One of them, a Louisiana Choctaw band, is also the entity a loose containment match confused with the federally recognized Jena Band — which is why `TRBS-` rows can never supply identity in this build.

