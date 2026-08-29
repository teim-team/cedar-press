# FR EX PARTE NOTICES — BUILD LOG

*Built 2026-08-26. `code/154_build_fr_ex_parte_notices.py`.*
*Host: `www.federalregister.gov`, one poller, lock held and released in
`logs/_HOSTLOCK_www.federalregister.gov.json`.*

---

## THE HEADLINE: THE "641" WAS ALREADY PULLED, AND IT WAS NEVER 641 NOTICES

`START_HERE.md` item 5 reads *"641 FR ex parte notices — the only place
communicating parties are named"*, listed as tomorrow's work. Both halves of
that line need correcting.

**It was done, fourteen days before this run.** The 641 is the count of one
query that `code/133_build_ferc_advocacy.py` ran on 2026-08-12 —
`conditions[agencies][]=federal-energy-regulatory-commission` &
`conditions[term]="off-the-record communications"` — and 133 retrieved all 641
documents, typed 609 of them as the notice series, and transcribed **4,248
communications** into `data/clean/ferc_ex_parte_parties.csv`. The evidence is
`data/raw/advocacy/ferc/_fr_state.json`, `logs/133_ferc_fr_leg_2026-08-12.log`,
and the released host lock, whose own `note` field says so. START_HERE was
rewritten "at the close of 2026-08-12" and the FERC files are stamped 21:25
that evening; the queue entry simply predates the work by a few hours.

**And 133's own docstring already says the 641 is not 641 notices.** It is a
full-text term search, so it returns Order No. 607 (the 1999 rule that created
the ex parte regime), Sunshine Act meeting notices, a 1994 marketing-affiliate
rehearing order, and the 2003 Policy Statement on Consultation With Indian
Tribes. 609 of the 641 are the series.

So the item is not "pull 641 notices." **The live question is the one nobody
had asked: FERC is ONE agency — where else does the Federal Register name a
party who communicated ex parte?** That is what this build answers.

---

## THE MEASUREMENT, IN THE ORDER IT WAS TAKEN

Everything below is one API request unless stated. The FR API exposes
`/api/v1/documents/facets/agency`, which returns a per-agency count for a
query in a single call — so "which agencies publish this?" costs one request,
not one per agency.

### 1. The recall sweep — how big is the surface

| query | result |
|---|---|
| `term="ex parte"`, `type=NOTICE` | **2,712 agency-hits over 74 agencies** |
| 133's exact query, no type filter | **642 today** (641 on 2026-08-12) |

Top of the "ex parte" facet: FCC 443 · Transportation 438 · Commerce 411 ·
**Surface Transportation Board 399** · BIS 151 · ITA 119 · PTO 114 · Energy
103 · SEC 77 · FERC 51 · Justice 42 · Bonneville 38.

**A FACET TOTAL IS A SUM OVER AGENCIES AND NEVER A DOCUMENT COUNT.** The
`off-the-record communications` facet prints 623 for
`federal-energy-regulatory-commission` and 623 for `energy-department` — the
*same* 623 documents, counted twice, because FERC is carried as a child of
Energy. Reading 1,246 off that facet would have doubled the series.

Indexing both terms in full gave **7,818 distinct FR documents**: Proposed
Rule 4,003 · Rule 1,165 · Notice 2,351 · Uncategorized 286 · Sunshine Act 8 ·
Correction 3 · Presidential 2.

### 2. The precision sweep — the body test, run SERVER-SIDE

Fetching 7,818 bodies to discover that most of them name nobody would have
cost two hours of a host's patience. `conditions[term]` is a **full-text**
search, so the body test can be asked of the API directly: a phrase that only
occurs where a party is named costs one request to test across the entire
corpus.

| phrase | where it lands |
|---|---|
| `"Presenter or requester"` | **538 FERC**, +1 NOAA |
| `"ex parte meeting with"` | **45 ITA** · 9 NHTSA · 4 Copyright Office · 3 Energy · 2 FAA · 2 CFPB · 1 FCC |
| `"ex parte communication with"` | 28 EPA · 5 DOT · 5 SEC · 3 Energy · 2 STB · 2 OPM · 2 OSHRC · 2 DOJ · 2 HUD |
| `"ex parte communications received"` | **19 NLRB** · 2 STB · 1 each PRC, NRC, FMC, FCC, ACUS |
| `"oral ex parte communication"` | 2 HHS · 2 FDA · 2 FCC · 1 STB · 1 NLRB · 1 CPSC |
| `"notice of ex parte communication"` | 3 Copyright Office · 3 FCC |
| `"ex parte communication from"` | 3 FERC · 1 each RUS, RHS, NRCS, DOJ, FSA, DEA |
| `"ex parte contact with"` | 3 HHS · 2 CMS |
| `"ex parte presentation by"` | 3 FCC |
| `"summary of ex parte"` | 2 STB |
| `"records of ex parte communications"` | 1 Copyright Office · 1 FTC |
| `"the following ex parte communications"` | **0** |
| `"memorandum of ex parte"` | **0** |
| `"written ex parte communication from"` | **0** |

Union: **708 documents**, plus **7 FERC off-the-record documents absent from
133's cache** = 713 bodies fetched. Zero refusals, zero 404s.

---

## WHAT THE BODIES SAY: FOUR THINGS WEAR THE SAME WORDS

Typing them apart *is* the dataset. `series` is assigned from each document's
own body, never from its title — 133 learned that expensively when the FR
titled two real notices "Regulations Governing Off-the-**ROAD**
Communications".

| `series` | rows | what it is |
|---|---:|---|
| `NO_PARTY_NAMING_PHRASE_IN_FULL_TEXT` | 7,107 | carries an ex parte phrase; the FR's own full-text search returns it for none of the 14 party-naming phrases |
| `FERC_OFF_THE_RECORD_NOTICE` | 538 | the biweekly series — 536 already owned by 133, **2 new** |
| `MENTIONS_EX_PARTE_NAMES_NOBODY` | 86 | phrase present, no party readable. A parse limit, **not** a claim that nobody communicated |
| `AGENCY_EX_PARTE_DISCLOSURE` | **69** | a non-FERC agency naming who talked to it |
| `PROCEDURAL_RECITAL_ONLY` | 20 | "permit-but-disclose", or the ex parte rules themselves |

### The 69 real non-FERC disclosures, and where they live

ITA 40 · NHTSA 7 · FCC 4 · FAA 3 · Energy 3 · Copyright Office 3 · SEC 2 ·
Commerce 1 · DEA 1 · FMCSA 1 · CFPB 1 · CFTC 1 · (2 with no child agency).
1994-05-09 through 2026-06-03.

**Commerce/ITA is the second real series.** Antidumping and countervailing-duty
determinations disclose the meeting in the narrative, verbatim:

> "the Department held an ex parte meeting with **representatives of the
> Government of Argentina and Siderar**" — FR 03-12313

> Memorandum … "**Ex Parte Meeting with Counsel for PAM S.r.l.** in the
> Antidumping Duty Administrative Review of Certain Pasta from Italy" —
> FR 02-127

### Three things that look like the series and are not

**1. THE FCC'S BOILERPLATE.** 4,430 of the 7,818 indexed documents are FCC,
because the Commission recites in nearly every rulemaking that the proceeding
"shall be treated as a permit-but-disclose proceeding in accordance with the
Commission's ex parte rules." The FCC's actual ex parte filings live in ECFS,
not the Federal Register. **An agency with the strongest ex parte disclosure
regime in government contributes almost nothing to an FR-based dataset**, and
its 4,430 documents make it look like the opposite.

**2. "EX PARTE" IS A DOCKET NUMBER AT THE SURFACE TRANSPORTATION BOARD.** STB
numbers its rulemakings of general applicability *Ex Parte No. 290*, *Ex Parte
No. 733*; 616 indexed documents are STB or its ICC predecessor. The string is
present and no communication is disclosed. Typing those as ex parte
communications because the substring matched is the same error shape as
reading the Wichita Tribe out of "Boys & Girls Clubs of Wichita Falls".

**3. THE NLRB'S 19.** Every one is the recital *"ex parte communications
received by the Board will be made part of the rulemaking record"* — a
statement about how comments will be handled, not a disclosure of any.

---

## FOUR PARSER FAILURES, ALL OF WHICH FAILED CLOSED

Each printed a zero and no error. That is the shape AGENTS.md keeps
recording: a matcher that fails closed looks exactly like a finding about the
source.

**1. THE FEDERAL REGISTER HARD-WRAPS ITS TEXT, SO THE PHRASE ITSELF SPLITS.**
The first parser preserved newlines. `re.finditer(r"ex parte", text)` then
reported **zero** occurrences in documents the FR's own full-text search had
just returned for `"ex parte meeting with"` — the body says `ex parte\nmeeting`.
And `.` does not match a newline without `re.S`, so any capture spanning a
wrap died at the break. Two independent causes, same symptom: the largest
non-FERC series returned nothing. Fixed by flattening to one line — but only
on the generic path. **The FERC path still uses 133's `_fr_plain`, which
preserves the fixed-width column geometry its table parser reads.**

**2. THE FR PRINTS "Ex-parte" HYPHENATED.** FR 03-30261: *"Ex-parte meeting
with Counsel for Petitioners"*. The FR's search index folds the hyphen; a
pattern with a literal space does not. Every phrase pattern is now
`ex[\s\-]+parte`.

**3. A CLASS OF PERSONS IS NOT A PARTY — 62 of the first pass's 185 rows.**
The pattern `ex parte communication with X` fires on the *prohibition* clause,
where X is the tribunal:

```
trial staff or any other interested person not employed by EPA
any employee of the Library of Congress
a BIA deciding official and the contact persons for inquiries
the Administrative Procedure Act (APA) (5 U.S.C
USDA personnel prior to and after the Department's decision
```

Published as parties, that would have recorded **EPA's own trial staff as
having lobbied EPA**. The generic-head test was anchored `^…$` and only caught
captures that were *entirely* a generic word; these are longer than that. They
now type `AGENCY_SIDE_OR_CLASS_OF_PERSONS`, assert nothing, link to nothing,
and are kept with their quote in `review/fr_ex_parte_refused_captures.csv` so
every refusal is auditable rather than silent. 113 captures refused in total
(71 class-of-persons, 42 generic).

**4. A LITIGATION ROLE IS NOT A NAME, AND IT IS NOT NOTHING EITHER.** Commerce
writes *"Ex-parte meeting with Counsel for Petitioners"*. A communication was
disclosed and dated; the party is identified only by its role. Dropping it
erases a real disclosure; writing "Petitioners" as a party invents an
organisation. It gets its own class, `ROLE_NOT_A_NAME` (12 rows), and is never
offered to the resolver.

Also fixed: captures that swallowed the predicate ("GM indicated that clipping
can occur…"), which both corrupted the name and split one party into two rows.
The capture now stops at the first finite verb, at a sentence boundary — with
an abbreviation exception list, because "Heze Huayi Chemical **Co.** Ltd." and
"PAM **S.r.l.**" end clauses in periods — and at the FR's hyphen rule-lines.

---

## THE PLACE-SUFFIX GUARD WAS BUILT WRONG AND NARROWED THE MOMENT IT WAS MEASURED

Written broadly — refuse any record containing a place word — it fired on

    Columbia River Inter-Tribal Fish Commission

and threw away a link the resolver had made on the **exact canonical name**.
"River" is a place word; the Columbia River Inter-Tribal Fish Commission is
not a place.

AGENTS.md records two guards built, measured and **removed** because each lost
far more correct rows than it saved. This one survives only in the narrow form
the standing rule actually describes: *"Boys & Girls Clubs of Wichita Falls"*
is a place because the place word sits **immediately after** the token that
carried the match. So the veto now requires adjacency to a matched token, and
it never overrides an exact / canonical / alias / official-name tier — a
record whose whole name IS the entity's name is not a place.

Verified after narrowing, against the known traps:

| record | result |
|---|---|
| Columbia River Inter-Tribal Fish Commission | **linked** `ITO-CLMBRV-00`, `exact_canonical` |
| Boys & Girls Clubs of Wichita Falls | refused, `no_native_token_in_name` |
| Wichita Falls Indian Center | refused, `only_trap_tokens_shared:['wichita']` |
| Denver Indian Health and Family Services | refused, `non_government_class` |
| Yurok Tribe | **linked** `TRBF-YUROKT-00` |

---

## LINKAGE

The **one resolver** — `33::resolve_entity` through
`96_build_consultation_events.py::Resolver`, with `cedar_match_guard` applied
only to the containment/core tiers it was written for. No new name matcher was
written.

The linkage pass reads 133's `ferc_ex_parte_parties.csv` **read-only** and
writes a separate join file. 133 owns that CSV; a build that wrote into it
would be clobbered by the next `133 build`, and would clobber it in turn.

| | |
|---|---:|
| FERC party rows read | 4,246 |
| this build's own party rows | 112 |
| **linked to a Native entity** | **9** |
| unresolved candidates staged for a ruling | 6 |

The nine: United South and Eastern Tribes ×2 · Kickapoo of Texas ×2 ·
Columbia River Inter-Tribal Fish Commission · Yavapai-Apache · Upper Skagit ·
Seneca · Yurok.

**Nine of 4,358 is the right answer, not a failure.** FERC's off-the-record
docket is pipelines, hydro and interconnection; the parties are utilities,
landowners, state agencies and members of Congress. Only ~50 rows in the whole
corpus carry a Native-looking string at all, and the resolver linked the ones
that are entities.

### What was left UNRESOLVED, and why (`review/fr_ex_parte_unresolved_candidates.csv`)

| party as printed | refusal |
|---|---|
| Quapaw Tribe of Oklahoma | `entity_name_does_not_lead_record:Quapaw Nation` — the nation renamed; the spine carries the current name |
| Confederated Tribes of Coos, Lower Umqua and Siuslaw Indians | `entity_name_does_not_lead_record:Confederated Coos` |
| Confederated Tribes of Coos Lower Umpua and Siuslaw Indians Chairman Mark Ingersoll | same, and the string also carries an officer's name |
| Confederated Tribes of Siuslaw Indians | `no_spine_match` — a partial rendering of the above |
| The Hobi Tribe | `no_spine_match` — probably a Federal Register typo for Hopi, and a *probably* is not a link |
| Native American community | `ambiguous_containment:25` — not an entity |

Every one of these is a **recorded finding with a reason**, not a blank. Three
of the six look correctable by a human in seconds; none is correctable by a
matcher without inventing the correction.

---

## OUTPUTS

| file | rows |
|---|---:|
| `data/clean/fr_ex_parte_notices.csv` | **7,820** |
| `data/clean/fr_ex_parte_parties.csv` | **112** |
| `data/clean/fr_ex_parte_party_entity_links.csv` | 9 |
| `review/fr_ex_parte_unresolved_candidates.csv` | 6 |
| `review/fr_ex_parte_refused_captures.csv` | 113 |
| `data/clean/codebook/04d_fr_ex_parte_notices.csv` | fragment |
| `data/clean/codebook/04d_fr_ex_parte_parties.csv` | fragment |
| `data/clean/codebook/04d_fr_ex_parte_links.csv` | fragment |

Raw: `data/raw/fr_ex_parte/` — 713 full-text bodies, `_index.json`,
`_candidates.json`, `_probe_agency_facets.json`,
`_probe_precision_facets.json`, `_fetch_state.json`.

**`codebook_master.csv` was NOT written by this build.** Fragments only, per
`cedar_codebook.py`. The master was regenerated afterwards with
`py -3 code/cedar_codebook.py build` (backed up first to
`codebook_master.csv.bak_2026-08-26_pre154`), which is the sanctioned tool and
refuses to shrink.

`event_class = ADVOCACY`, `channel = REGULATORY_EX_PARTE`, `is_lobbying = 0`
on every row, asserted against `cedar_domain` before a byte was written. An ex
parte disclosure is advocacy and is **not** LDA lobbying.

`position_relative_to_native_interest` is blank on every row by construction.
A disclosure records that a named party communicated about a named proceeding
on a named date. It records no position and no money.

---

## HOST DISCIPLINE, INCLUDING WHAT THIS RUN COST

One poller throughout, `>=0.9s` gap plus jitter, exponential backoff
45s→360s, stop after 4 consecutive refusals, 100-minute wall-clock deadline.
Lock claimed and released per stage. **`www.federalregister.gov` refused
nothing: 8 + 2 + 14 + 14 index/facet calls and 713 bodies, zero 403s, zero
404s, zero transport errors.**

**Self-reported waste, because an unattributed block gets re-triggered by the
next agent.** The fetch stage looked for 133's FERC body cache at
`data/raw/fr_off_the_record_notices/` when it actually lives at
`data/raw/advocacy/ferc/fr_off_the_record_notices/`. It found nothing to
reuse and re-pulled **538 FERC bodies this build did not need** — 14 minutes of
requests for objects already on disk. The path is corrected in the script. The
lock's `reused_from_133_cache: 0` is recorded honestly rather than quietly,
because a zero there is otherwise indistinguishable from "there was nothing to
reuse."

Note for whoever runs 133 next: `code/133_build_ferc_advocacy.py fetch` was
running against `elibrary.ferc.gov` throughout this build. Different host,
different lock, no interaction.

---

## WHAT THIS CHANGES ABOUT THE QUEUE

- **START_HERE item 5 is complete and should be struck**, with the correction
  that 133 did the FERC leg on 2026-08-12 and this build did the rest.
- **The 2 new FERC notices should be folded into `ferc_ex_parte_parties.csv`
  by 133, not by this script.** `01-1578` (2001-01-22, 10 communications —
  including *The Honorable Jack Reed*) is a notice 133's run missed;
  `2026-16634` (2026-08-14, 3 communications) was published after it. Their
  13 party rows are in `fr_ex_parte_parties.csv` and flagged by an empty
  `already_parsed_by`.
- **`ferc_ex_parte_parties.csv` should carry a `resolved_native_entity_id` for
  the nine linked rows.** The join file exists so 133 can adopt them without a
  second matcher.
- **Outside FERC, the whole Federal Register yields 69 disclosure documents
  and 112 party rows across 32 years — and that is the finding, not a
  shortfall.** The volume is in ECFS (FCC) and in
  agency dockets (EPA, NRC, STB), not in the Federal Register. Anyone wanting
  a real ex parte corpus for Indian Country should go to FERC eLibrary — which
  Cedar Press already holds — and to ECFS, not to more FR queries.

## OPEN, NOT FIXED HERE

`62_no_regression_check.py` still fails on
`codebook_undocumented_public = 45`. **All 45 belong to
`07o_nigc_declinations`** and predate this build; this build's own 20
undocumented rows were fixed. Writing descriptions into another build's
codebook fragment would be documenting a dataset this agent has not read, so
it is reported instead.
