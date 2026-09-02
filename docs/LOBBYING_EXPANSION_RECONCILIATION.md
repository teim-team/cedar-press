# Lobbying Expansion — what exists, what to build, what to refuse

> ## ⚠ ONE FIGURE IN THIS DOCUMENT MUST NOT BE QUOTED IN A SALES CONTEXT
> *Banner added 2026-08-28 during doc consolidation. Source:
> `docs/DOC_CONTRADICTIONS_2026-08-26.md` item **A6**. Nothing else in this
> document is disputed, and its substance is unchanged.*
>
> The headline **"27,796 filings, 97.0% keyed — the highest keyed rate of any
> Cedar dataset"** is computed on the **post-match** file. It is arithmetically
> correct and it answers the wrong question.
>
> | | |
> |---|---:|
> | filings scored in the raw pull | **39,448** |
> | filings matched | 27,796 (70.5%) |
> | did not match | 11,652 |
> | **true coverage of the pulled universe** | **26,955 / 39,448 = 68.3%** |
>
> **"97% keyed, highest of any dataset" is off by 29 points** against the
> universe a buyer would assume. Source for the denominator:
> `docs/LOBBYING_BUILD_LOG_2026-08-05.md:44-47,220`.

*Spec received 2026-08-07: evolve the LDA dataset into a Native Government
Relations & Advocacy dataset. This grounds that spec against what is already on
disk and flags the one item that should not be built as written.*

---

## THE ITEM TO RESOLVE BEFORE BUILDING: `position_on_native_issue`

The spec proposes tracking **"Organizations Lobbying AGAINST Tribal Interests"**
with `position_on_native_issue ∈ {Support, Oppose, Mixed, Unknown}`, and gives
examples including *"anti-sovereignty organizations"*, local governments, energy
companies, water users and property owners.

**This is the highest-risk item in the spec, and it is not a data problem.**

Every other field in Cedar Press is a *retrieved fact* — a filing said X, a
document stated Y. `position_on_native_issue = Oppose` is a **characterisation
we would be authoring**, published under our name, about a named organisation.
Labelling a county government or a company "anti-sovereignty" is an editorial
judgment, and the prime directive of this project is that we never falsely
attribute.

It is also the single most legally exposed field we would ship. A wrong
`Oppose` on a named party is defamatory in a way a wrong CAGE code is not.

**Build the fact, not the verdict.** What is defensible and just as useful:

```
lda_position_reported      the filing's own "position" text, verbatim
bill_id                    what they lobbied on
tribal_position_on_bill    where a tribe or intertribal org publicly stated one
alignment                  DERIVED, per (org, bill): does the org's stated
                           position match the tribal position on that bill?
                           values: SAME | OPPOSED | NO_TRIBAL_POSITION_FOUND
```

`alignment` is computed per bill from two sourced positions. It is falsifiable,
it carries its evidence, and it never asserts an organisation's motives or its
general stance toward tribes. A ballot committee formally registered to oppose a
tribal gaming measure is a **registration fact** and may be recorded as such —
that is a filing, not a characterisation.

If a general-stance label is still wanted later, it should be a **hand ruling by
Elijah**, tiered like every other ruling, never algorithmic and never inferred
from industry.

---

## ALREADY BUILT — do not rebuild

> **⚠ THE "97.0% KEYED" DENOMINATOR IS THE POST-MATCH FILE. Flagged 2026-08-26.**
>
> Nothing below is arithmetically wrong, but the headline is measured against the wrong
> universe for the claim it makes. **97.0% is 26,955 of 27,796 — and 27,796 is what
> *survived matching*, not what was pulled.**
>
> `docs/LOBBYING_BUILD_LOG_2026-08-05.md:44-47` and `:595`: **39,448 filings were scored,
> 27,796 matched (70.5%), 11,652 did not.** So coverage of the pulled universe is
> **26,955 / 39,448 = 68.3%**, not 97.0%.
>
> Both figures are true of different things and both are worth having — 97.0% is a real
> statement about *the quality of the matched file*, and it is the right number for a
> reliability claim about rows that are in the dataset. It is the wrong number for a
> **coverage** claim, and *"the highest keyed rate of any Cedar dataset"* reads as a coverage
> claim. **Quoted in a sales context it is off by 29 points**, against a buyer who can pull
> the LDA API and check.
>
> Say which denominator you mean, every time.

| Spec item | Status |
|---|---|
| Federal LDA + Native crosswalk | **27,796 filings, 97.0% keyed** — ~~the highest keyed rate of any Cedar dataset~~ **⚠ see the denominator note below before quoting this** |
| Tribe-year lobbying panel | 5,051 rows |
| Lobbying target entities | 116 |
| **Tribal consultation records (#2)** | **partly built** — 484 consultation notices, 1,829 referenced records, by-agency and by-year rollups, from the Federal Register |
| **IRS 990 lobbying (Schedule C)** | **partly built** — `lobbying_expenditure` already in `np_financials.csv` (8,507 rows), with `lobbying_field_basis` recording where it came from |
| Bills, votes, member positions | 3,069 bills · 423 roll calls · 136,119 member positions |
| Bill ↔ entity bridge | 676 links over 154 entities |

Two things follow. **Consultation is not a new build**, it is an extension from
Federal Register notices to agency-published agendas, attendance and summaries.
And **Schedule C is a field-level gap, not a dataset gap** — we hold the 990
universe already.

A caveat that must travel with any 990-based lobbying figure: **6,453 of 12,764
organisations are 990-N filers** and report no financial detail at all. Zero
lobbying expenditure there is the filing regime, not a finding.

---

## RANKED BY VALUE PER UNIT OF WORK

**1. Tribal consultation, extended.** Already begun, and it captures
government-to-government interaction that **never appears in LDA at all**. A
tribe that never files an LDA report may consult constantly. This is the single
biggest blind spot in the current dataset and we are already partway in.

**2. OIRA EO 12866 meetings.** Free, structured, names attendees and the RIN.
Captures *regulatory* advocacy, which LDA barely reflects. Clean join to
Federal Register rules we already hold.

**3. Congressional hearings.** Witness, organisation, tribe, committee, date.
Free from GPO/Congress.gov. Joins to the bills dataset already built.

**4. Community Project Funding / earmarks.** An observable *outcome*, tied to a
named member of Congress. This is the missing right-hand side of the influence
chain — lobbying → target → outcome.

**5. DOI leadership calendars.** High value where published, but coverage is
uneven and often FOIA-dependent. Expect gaps, and record the absence rather
than implying the meetings did not happen.

**6. State lobbying.** Genuinely richer than federal — many states disclose
individual officials contacted. But it is **eight separate systems with eight
schemas**, so it is Phase 2 by cost, not by value. WA, CA, OK, AZ, NM, MN, NY,
AK first, gaming-ranked.

**7. FACA committees.** Small, stable, cheap. Good long-run engagement signal.

**8. Sponsored travel.** Free from House/Senate disclosure. Small but a real
observable relationship.

**Campaign finance stays in Phase 3** and should be approached carefully. It is
the field most likely to be read as an accusation, and tribal PAC contributions
are already politically contested territory.

---

## RULES FOR THIS BUILD

- **A meeting is not lobbying.** Consultation is a statutory
  government-to-government obligation. Filing it under "lobbying" would
  mischaracterise a sovereign relationship as influence-buying. Keep
  `channel` explicit: `LDA_FILING | CONSULTATION | OIRA_MEETING |
  HEARING_TESTIMONY | FACA | AGENCY_CALENDAR | STATE_FILING`.
- **Absence of an LDA filing is not absence of advocacy.** Same rule as the
  set-aside fields: 60.9% of Native contracting dollars report no Native
  preference. A filter answers "did this self-report," never "did this happen."
- LDA spend is a **good-faith estimate rounded to $10,000**. Never print it to
  the dollar.
- Income and expenses are **either/or** — outside registrants report income,
  self-filers report expenses. One being 0.9% filled is correct.
- A `spend_usd` of 0 is usually **truthful** — a quarterly report with no
  reportable activity.
- **Never assert an outcome was caused by advocacy.** Record that both
  occurred, with dates. Correlation is the reader's to draw.
- Organisations lobbying *on* Native issues are not necessarily Native.
  `serves_native_entities` ≠ `parent_native_entity`, as everywhere else.


---

# ROUND 2 SPEC, 2026-08-12 — reconciled against what is built

## THE CONCEPTUAL CHANGE, AND IT IS NOW ENFORCED IN CODE

The spec's most valuable contribution is not a source. It is the **three-way
split** between affirmative influence, sovereign engagement, and mere proximity.
That is now `EventClass` in `code/cedar_domain.py`, and `AdvocacyChannel` grew
**7 -> 15 channels**, each mapping to exactly one class:

| class | channels |
|---|---|
| **ADVOCACY** (8) | LDA_FILING, STATE_FILING, OIRA_MEETING, CONGRESSIONAL_CORRESPONDENCE, REGULATORY_EX_PARTE, ADMINISTRATIVE_COMMENT, ADMINISTRATIVE_APPEAL, LITIGATION_BRIEF |
| **GOVERNMENT_ENGAGEMENT** (4) | CONSULTATION, SECTION_106_CONSULTATION, HEARING_TESTIMONY, FACA |
| **ACCESS** (3) | AGENCY_CALENDAR, VISITOR_RECORD, SPONSORED_TRAVEL |

**`may_promote_event_class()` refuses ACCESS -> ADVOCACY.** Same shape as
`AUTHORIZED_MAXIMUM` never becoming `ACTIVE_FLOOR_COUNT`: the weaker fact looks
exactly like the stronger one once the type is lost. A visitor log says a person
entered a building. It does not say a meeting happened, that it concerned our
matter, or that anyone was influenced. Corroboration by a separate source of the
stronger class is what upgrades a claim - and then **that** source is the
evidence, not the access record.

**A second distinction the spec implies and the code now states:**
`is_lobbying` is NARROWER than `EventClass.ADVOCACY`. An administrative comment
or an amicus brief is advocacy and is **not lobbying**. Conflating them would be
wrong in a way that matters legally, not just analytically.

## WHAT IS ALREADY BUILT — do not re-plan these

| | rows |
|---|---:|
| `native_entity_lobbying_disclosures.csv` | 27,796 (26,955 entity-attributed, 97%) |
| `consultation_events.csv` | 11,402 |
| `federal_actions.csv` | 156,452 |
| `lobbying_target_entities.csv` | 116 |

## THE MEASUREMENT THAT VALIDATES THE SPEC'S #11

`consultation_events.csv` looks healthy at 11,402 rows. It is not, for this
purpose:

| consultation_type | rows |
|---|---:|
| NAGPRA_consultation_report | **10,888** |
| consultation_session | 212 |
| consultation_notice | 180 |
| NAGPRA | 38 |
| listening_session | 37 |
| **NHPA_section_106** | **20** |

**95.5% is NAGPRA. Section 106 is twenty rows.** And 11,068 of 11,402 come from
a single agency (Interior). So the spec's instinct to break Section 106 out as
its own project-level source is correct and the gap is larger than it looks from
the row count. A healthy total concealing a single-source monoculture is exactly
the kind of thing a coverage table hides.

## RANKED, AGAINST WHAT WE ALREADY HAVE

**Tier 1 - genuinely new and high value**

1. **Congressional correspondence / legislative-affairs logs.** The spec is right
   that this inverts the problem: Congress does not centrally report its
   contacts, but the *agency on the receiving end* logs them. Named systems to
   search for - `Congressional Correspondence Log`, `Controlled Correspondence`,
   `Executive Secretariat`, EPA's `Quill` - matter more than any portal, because
   the system can exist with no public face. **Pull the LOG first, then request
   underlying documents selectively.** That inverts the FOIA cost curve.
2. **Section 106 project consultation** - 20 rows today. Project-level, and it
   exposes the private-sector side: developer -> tribe -> THPO -> agency.
3. **FOIA logs as a discovery index, not a request mechanism.** Crawl what
   others already asked for before filing anything.

**Tier 2 - new, sector-specific**

4. **FERC eLibrary** - ex parte rules force communications onto the record.
5. **NEPA / BLM ePlanning** - the opposition layer, where a county or industry
   group that never registers under LDA still leaves a position.
6. **NRC public meeting database** (searchable to 2003-10-01, by external
   participant) - narrow but unusually clean.

**Tier 3 - outcome layer**

7. **IBIA / IBLA** (1970-present) and **litigation / amicus coalitions.** These
   answer "who opposed, through which institution, and did it work."

**Deprioritised: Presidential daily diary.** Archival lag makes it useless for
the 2025-26 question; keep for historical work only.

## THE CAUTION THAT MUST TRAVEL WITH THE VISITOR RECORDS

The spec states it and it deserves to be a hard rule: **building entry is
evidence of access, not of lobbying or even of a completed meeting.** WAVES
records are genuinely rich - visitor, visitee, appointment window, arrival and
departure, room, description - and that richness is exactly what will tempt a
downstream join into asserting a meeting occurred. It is `EventClass.ACCESS`,
permanently, and the code will not promote it.

---

# ROUND 2 BUILD LOG — items 10, 14, 15 built 2026-08-12

The three ROUND 2 items that had never been started. Scripts, in the order
their value was judged: **`code/144_build_admin_appeals.py`** (IBIA/IBLA),
**`code/145_build_nrc_public_meetings.py`** (NRC), and
**`code/146_build_visitor_access_records.py`** (WAVES).

`code/62_no_regression_check.py` clean before and after.

**A note on the script numbers.** They were taken as 141/142/143 per the spec
and renumbered mid-session to 144/145/146, because a concurrent agent claimed
141, 142 and 143 for other work while these were running. AGENTS.md already
records that *"the numeric script prefix no longer guarantees a unique step"*;
this is the same failure again, and `ls code/<n>_*` at the start of a session is
not sufficient when another agent is live.

## Item 15 — IBIA / IBLA administrative appeals (the outcome layer)

`admin_appeal_decisions.csv` · `admin_appeal_parties.csv` ·
`admin_appeal_positions.csv` · `source_coverage_admin_appeals.csv`

| | |
|---|---:|
| decisions, calendar 1970–2026 | **15,613** (IBIA 4,855 · IBLA 10,758) |
| year indices retrieved | **114 of 114** — no gap, no NOT_CHECKED |
| party rows | 20,027 |
| decisions linked to a spine entity | **397** (2.5%), **180 distinct entities** |
| entity links HELD for a ruling | 600 party rows / 458 distinct pairs |
| position rows | **1** |

Source: the Office of Hearings and Appeals chronological indices, one HTML page
per board per calendar year, each a three-column table (case name, date decided,
citation hyperlinked to the decision PDF on `www.oha.doi.gov`). Every published
field is transcribed from that table. `www.oha.doi.gov` was **not fetched** —
the PDF URL is recorded as published.

**Containment is not allowed to key a link here, and that cost 60% of the
matches.** On the first pass 602 of 1,000 resolved party rows came from
`resolve_entity`'s containment tier, and reading them shows good and bad in one
list: *White Mountain Apache Tribe → White Mountain* and *Turtle Mountain Band →
Turtle Mountain* alongside *Jackson County, Kansas → Jackson*, *Western
Watersheds Project → The NATIVE Project*, *READ & STEVENS, INC. → Stevens
Village*, *Eagle Butte, South Dakota, City of → Eagle*. AGENTS.md restricts
containment to resolving an owner already named in evidence, never to detecting
a match; sweeping 20,027 captions for tribes is detection. All 600 are HELD in
`review/admin_appeal_entity_link_candidates.csv` with the candidate attached, so
tribe-linked decisions fell 997 → 397. The 397 are exact/core/alias only.

**One position row, and that is the finding.** `position_is_addressable()`
needs organisation + matter + native entity, and an IBIA caption is almost
always *tribe or individual v. a BIA official* — the Interior official is not an
outside organisation with a stance, and an entity has no position on itself.
Exactly one decision in 15,613 pairs a resolved Native entity with a non-Native,
non-agency organisation in the caption: **12 IBLA 001, State of Utah, appellee,
Navajo**, and its `position` is `UNDETERMINED` because the caption establishes
who appealed and never establishes whether the action favoured or harmed the
tribe.

**Where the opposition layer actually hides: 24 compound captions.** A caption
cell that names two parties in one string — *"Albuquerque Area Director and
Meridian Oil Inc. and San Juan Basin Drilling"*, *"Muskogee Area Director and
Toklan Oil and Gas Corp"*, *"Portland Area Director and Mayr Brothers Logging
Co."* — types as the agency and loses the company. Splitting on " and " would
break *Assiniboine and Sioux Tribes*, so these carry
`compound_party_caption = Y` for a human instead of being guessed. That is where
the private-industry counterparties are.

**The 4,289-row "unresolved organisations" file is not a failure list, it is
the opposition layer.** It is every distinct organisational party in an
Interior appeal that is not a Native entity, ranked by appearances: STATE OF
ALASKA (80), SOUTHERN UTAH WILDERNESS ALLIANCE (33+10), AMOCO PRODUCTION
COMPANY (16+13), GEOSEARCH (16), TURNER BROTHERS (16), CONOCO (14), EXXON
COMPANY U.S.A. (11), OREGON NATURAL RESOURCES COUNCIL (11), COLORADO
ENVIRONMENTAL COALITION (10). That is the answer to "who formally challenged an
Interior action, through which institution," 1970-2026.

**No dataset about private individuals.** 10,077 party rows are natural persons
and carry a blank `party_name` with the reason stated; 9,665 captions publish in
redacted form. Nothing is lost for verification — the reporter citation is the
record identifier and the PDF URL is keyed by citation, not by name. Named
individuals survive only in a public professional capacity: agency officials by
title, and persons trading under a business name (`d/b/a`).

## Item 14 — NRC public meeting schedule

`nrc_public_meetings.csv` · `nrc_meeting_participants.csv` ·
`source_coverage_nrc_meetings.csv` · `review/nrc_entity_link_candidates.csv`

| | |
|---|---:|
| meetings recovered, 2013-2026 | **251** (9 cancelled, recorded as such) |
| detail pages fetched | 175 of 251 |
| external-participant field populated | **134** |
| docket / facility / ADAMS accession populated | 121 / 121 / 157 |
| participant rows | 407 (123 organisations · 274 individuals withheld · 10 "Public") |
| participants resolved to the spine | **10 tribes** |
| entity links held for a ruling | 17 rows / 13 pairs |
| classification | 240 REGULATORY_EX_PARTE · 9 SECTION_106_CONSULTATION · 2 CONSULTATION |
| host | 134 requests served, 35 refused |

**The spec's premise needs one correction.** ROUND 2 describes a search "by
EXTERNAL participant". That describes the LEGACY system. The current Drupal
PMNS view exposes exactly four filters — `keywords` ("Title or purpose
contains"), `field_meeting_number`, and a date range — and **no
external-participant filter**. The archive itself is intact: setting
`field_dates[min]=2003-10-01` returns meetings from the published floor.

So this build is a **keyword sweep**, and every term is written to the coverage
table with its yield. A meeting whose title uses none of these words is not in
this dataset and is not thereby absent from the NRC schedule — the same
distinction that produced the set-aside-filter error.

**`www.nrc.gov` returns HTTP 403 intermittently and at random.** Measured: six
sequential keyword queries at a 12 s gap returned 403/403/403/200/200/403 for
identical request shapes. A single 403 here is therefore not the permanent edge
block AGENTS.md's stop-work rule is written for — the 200s that follow disprove
it. The stop rule used is **four CONSECUTIVE refusals** with exponential
backoff, which is a stronger test than "stop on the first", and it is stated
because it is a deliberate departure. Also measured: **a browser-shaped
User-Agent was refused where the honest `CedarPress-research/1.0` string was
served.** Do not "fix" this by pretending to be Chrome.

**THE KEYWORD INDEX FLOOR IS NOT THE SCHEDULE FLOOR.** NRC publishes the
schedule from 2003-10-01 and a date-range query does return 2003 meetings --
but the earliest meeting ANY of the 36 terms recovered is **2013**. Verified on
meeting `20030710`: a 2003 detail page prints date, contact, participation
level and the NRC office, and carries **no Purpose and no title text at all**,
so a filter documented as "Title or purpose contains" cannot match it at any
term. A year histogram of this dataset therefore shows the FILTER's floor, and
it looks exactly like the source's. The distinction is written into
`source_coverage_nrc_meetings.csv` as its own row.

**Named individuals are withheld here too.** The External Participants block
mixes companies with people: Xcel Energy (20 rows) and Uranerz Energy (7)
alongside 274 rows carrying a bare personal name, plus 10 rows reading simply
"Public". A personal name in an attendance list does not establish a public
professional capacity -- it may be a company representative, an NRC project
manager, or a member of the public who signed up -- so the name is withheld and
the row kept, which leaves the individual-vs-organisational split measurable
without publishing a register of people.

**Containment is held here for the same reason as item 15**, and the measured
misfires make the case: `"05000282 - Prairie Island 1"` (a DOCKET line) and
`"C. Jackson"` both resolved onto spine entities, and
`"CONFEDERATED SALISH AND KOOTENAI TRIBE"` resolved to **Salish Kootenai
College** -- a tribal government matched to its tribal college, two different
legal persons. The 10 links that survive are exact/core/alias: Blackfeet,
Chippewa-Cree, Crow, Eastern Shoshone, Northern Arapaho, Northern Cheyenne,
Santee Sioux, Three Affiliated, Turtle Mountain, Prairie Island Indian
Community.

Classification is read from the purpose text, with the matched phrase carried
verbatim: Section 106 → `SECTION_106_CONSULTATION`, government-to-government →
`CONSULTATION` (both `GOVERNMENT_ENGAGEMENT`), otherwise
`REGULATORY_EX_PARTE` / `ADVOCACY`. **`channel_note` travels on every ex parte
row** saying that an NRC public meeting is publicly noticed and the channel name
denotes the family, not concealment.

## Item 10 — visitor / building access records

`visitor_access_events.csv` · `visitor_record_foia_requests.csv` ·
`source_coverage_visitor_records.csv`

| | |
|---|---:|
| WAVES visitor records read, 8 releases 2009–2016 | **6,210,115** |
| blank `Description` | **2,103,255 (33.9%)** — a property of the release |
| matched a Native term | 368 |
| appointment-grain events published | **20** |
| **visitor names published** | **0** |
| **position rows** | **0** |
| prior FOIA requests for calendars/visitor records | **667** (DOI 465 · BIA 176 · IHS 26) |

`EventClass.ACCESS`, permanently. The script asserts
`may_promote_event_class(ACCESS, ADVOCACY) is False` before writing a byte, and
asserts that zero rows satisfy `position_is_addressable()`.

**The grain is the appointment, not the person.** WAVES is person-level, names
ordinary members of the public, and carries **no organisation field for the
visitor** — so "restrict to visits linkable to an organisation or an official
capacity" cannot be satisfied at the person grain, and the aggregation to
(appointment start, visitee, location, room, description) is what makes the
source publishable at all. Each row carries `n_visitor_records` and no visitor
name. The **visitee** is named, because a WAVES visitee is EOP staff receiving
visitors in an official capacity — Jodi Gillette, Kimberly Teehee, Tracy
Goodluck. 16 of the 20 events are in the **OEOB**, which is where OMB and the
EOP policy offices sit; the building is recorded and no component is inferred
from it.

**`resolve_entity` is deliberately NOT run against `Description`.** Its
containment tier is the one that put $2.8B on a school, and a free-text meeting
description is the worst possible input to it. `native_entity_id` is blank on
every row with `native_entity_link_basis = NOT_ATTEMPTED_BY_RULE` — a stated
refusal, not unfinished work. That is also why there are no position rows: this
source supplies none of the three legs.

**MEASURED: "INDIAN TREATY ROOM" is a room, not a subject.** The 2013 release
has 199,239 non-blank descriptions. Searching them for bare
TRIBAL/TRIBE/NAVAJO/INDIAN/NATIVE AMERICAN returns **509 hits and every single
one is the phrase "Indian Treaty Room"** — a room in the Eisenhower Executive
Office Building booked for meetings on every subject there is. The term list
excludes bare "INDIAN" for the reason `cedar_domain.NAME_TRAPS` lists it, so all
509 correctly matched nothing and 2011b/2012/2013 correctly report **zero**.
Had "INDIAN" been a term, this dataset would have shipped 509 rows of room
bookings as Native access to the EOP. `meeting_room` must never be swept for
relevance.

**The FOIA index was read before anything was pulled**, per ROUND 2 item 3.
667 prior requests for calendars or visitor records are emitted with the
requesting organisation and the verbatim request text — what has already been
asked of whom, before filing anything. Interior, Indian Affairs and IHS are all
recorded `NOT_FOUND` rather than `WITHHOLDS`: no proactive publication was
located and **no agency statement of refusal was retrieved either**, and those
are different findings.
