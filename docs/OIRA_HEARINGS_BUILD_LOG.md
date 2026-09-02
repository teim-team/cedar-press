# OIRA EO 12866 meetings and congressional hearings — build log

*Script `code/98_build_oira_and_hearings.py`. Phase 1 items 2 and 3 of the
government-relations expansion (`docs/LOBBYING_EXPANSION_RECONCILIATION.md`;
SPEC v2 §9.5). Built 2026-08-07.*

Channels: `OIRA_MEETING` and `HEARING_TESTIMONY`, both from
`cedar_domain.AdvocacyChannel`. Consultation and the `fr_consultation_*` files
belong to a concurrent build and are untouched here.

---

## Why these two channels exist

LDA is a filing regime, and a filing regime only tells you who filed. A tribe
that never registers under the Lobbying Disclosure Act may still sit down with
OIRA about a BIA rule, or send its chairman to testify before House
Appropriations. Both leave a public record. Neither leaves an LDA filing.

- **OIRA meetings** capture *regulatory* advocacy. Under EO 12866 §6(b)(4),
  while OMB's Office of Information and Regulatory Affairs reviews a
  significant rule, outside parties may request a meeting and OIRA publishes
  the record: date, RIN, rule title, requesting organisation, every named
  attendee on both sides, and any materials lodged. The RIN joins straight into
  `federal_actions.csv` — the regulatory parallel to the bill↔vote chain.
- **Hearings** capture *legislative* advocacy at the witness table, and link to
  `native_bills.csv` through the committee meeting's own related-bill items.

---

## Sources, and exactly what each one serves

| Source | Endpoint | What it gives | Coverage |
|---|---|---|---|
| reginfo.gov | `/public/do/eom12866SearchResults`, `/public/do/viewEO12866Meeting` | meeting date, RIN, rule title, agency, rule stage, **Requestor**, requestor's name, documents, **every attendee with affiliation and participation mode** | **2014-01 onward** (measured, see below) |
| Congress.gov | `/v3/committee-meeting/{congress}/{chamber}/{eventId}` | committee, title, date, **witnesses (name / position / organisation)**, witness statements, related bills | **112th Congress onward, HOUSE ONLY for witnesses** |
| govinfo (GPO) | `/search` on `witness:`, then package **MODS** | `<witness>` lines, `<congCommittee>`, `<heldDate>`, `<eventId>`, `<jacketId>` | CHRG collection; supplies the **Senate** and the pre-112th backfill |

### Three coverage floors, all measured rather than assumed

**reginfo returns nothing before 2014.** Half-year probes across 1994–2026
return a rendered result count only from 2014-01-01 forward. Month-level probes
for January 2005, January and May 2012, and January and October 2013 all return
the search form with no records. One 2011 record surfaces (a meeting logged
against a review still open in the system). Any claim about OIRA meetings
before 2014 is outside what this source will serve.

**A full calendar year silently fails.** `01/01/2024–12/31/2024` returns the
search form, not results; `01/01/2024–06/30/2024` returns 839. The sweep
therefore runs in half-year windows, and a window that returns no count is
recorded as such rather than read as zero.

**Congress.gov has no Senate witnesses.** Across all 17,859 committee meetings
for the 112th–119th Congresses, every `witnesses` array belongs to a House
meeting. Senate meetings carry title, committee, date and related bills and no
witness list at all. Shipping only Congress.gov would have produced a hearings
dataset in which the **Senate Committee on Indian Affairs — the densest single
source of Native testimony in Congress — does not appear once.** That is what
the govinfo MODS layer exists to fix.

---

## What is published, and what is only read

Both sweeps are deliberately **universe-wide**: every OIRA meeting since 2014,
every House and Senate committee meeting since the 112th Congress. That is the
only way to find the Native slice — a committee-restricted or issue-restricted
pull would reproduce the set-aside-filter error in a new place, and
`docs/PULL_DISCIPLINE.md` already records what that costs.

But the corpus is **not** the product.

```
data/clean/oira_meetings.csv                 PUBLISHED - Native slice
data/clean/hearing_appearances.csv           PUBLISHED - Native slice
data/clean/oira_meeting_participants.csv     PUBLISHED - attendees of slice meetings
data/clean/oira_federal_action_links.csv     PUBLISHED - RIN joins for slice meetings
data/clean/hearing_bill_links.csv            PUBLISHED - Native-scoped by construction
data/interim/*_corpus.csv                    RETAINED CONTEXT, not a product
review/advocacy_unresolved_<date>.csv        for rulings
data/raw/advocacy/*.jsonl                    retrieved records, cached
```

`native_slice_basis` says why each published row is in the slice:
`REQUESTOR_RESOLVED`, `REQUESTOR_NATIVE_MARKER`, `ATTENDEE_RESOLVED`,
`ATTENDEE_NATIVE_MARKER`, `WITNESS_ORG_RESOLVED`, `WITNESS_ORG_NATIVE_MARKER`.
The corpus size is stated in every run report so the denominator is never lost.

`hearing_bill_links.csv` is Native-scoped by construction: every bill in it is a
row of `native_bills.csv`, so a hearing appears because it concerns a bill
affecting tribes, whether or not a Native witness testified.

---

## Resolution: the organisation only, and never on a name alone

`resolve_entity` is **imported** from `code/33_apply_party_rulings.py`. No
second matcher was written. Its two pure string helpers, `norm` and `core`, are
memoised on the module object — that is a speed change, not a logic change.

**A person is not an entity.** Attendee and witness names are kept as strings.
Only the *organisation* is resolved. No spine entity is minted for a human
being, ever.

Four guards sit on top of `resolve_entity`:

**1 — specificity.** Every identifying token of the spine name must appear in
the record name. This is the direction that broke on `NATIVE VILLAGE OF ELIM` →
*Elim Native **Corporation***, where containment rewards the shorter spine name.

**2 — containment must be corroborated by the spine's own official name.**
AGENTS.md is explicit that containment may resolve an owner already named in
evidence but may never *detect* a match. A witness organisation is detection.
Measured on the first 400 hearing records with containment allowed, three of
four resolutions were wrong:

| Record | Would have resolved to | Verdict |
|---|---|---|
| Third Sector Capital Partners | a Native CDFI | wrong |
| American Enterprise Institute | a tribal enterprise | wrong |
| SCAN Health Plans | an Urban Indian Organization | wrong |

But a blanket refusal was measured too, and it threw away **Standing Rock Sioux
Tribe, Salt River Pima-Maricopa Indian Community and the Ute Indian Tribe** —
because the spine stores a short canonical name (`Standing Rock`) plus the long
federal-filing form as an alias (`Standing Rock Sioux Tribe of North & South
Dakota`), and a witness writes neither.

The rule that keeps those and still refuses the failures: **the record name must
sit between the canonical name and an official name the spine already holds** —
formally, `core(canonical) ⊆ core(record) ⊆ core(some alias)`. That is
corroboration from retrieved evidence, not a new similarity heuristic. It also
refuses `Cherokee Nation Businesses` and `Chickasaw Children's Village`, which
is correct: a tribe's business arm and a tribe's school are different legal
persons from the tribe, and booking either onto the government is the failure
that cost $13.4B on the contracts side.

**3 — state agreement** wherever both sides carry a state. Neither reginfo nor
Congress.gov publishes a state for a requestor or a witness, so in practice this
guard has nothing to test — which is precisely why nothing here reaches Tier A
automatically.

**4 — trap tokens** on partial overlaps only. It deliberately does *not* fire on
exact or core-equal matches: refusing `Cherokee Nation` against spine
`Cherokee Nation` because `cherokee` is a trap word dropped one of the largest
tribes in the country out of the dataset on the first pass.

### Everything automated lands at Tier B

Tier A here requires two legs — name **and** an agreeing state. No source in
either channel publishes a state for an organisation, so **every automated match
in this build is Tier B and goes to `review/` for a ruling.** That is the
designed outcome, not a shortfall: SPEC v2 §10.1 says automated results land at
B/C pending review and nothing enters Tier A without one.

### Classification records what was found, and never characterises

`organization_class` takes five values: `NATIVE_ENTITY_SPINE`,
`UNRESOLVED_NATIVE_MARKER`, `UNRESOLVED_NO_NATIVE_MARKER`, `GOVERNMENT`,
`UNCLASSIFIED`. **There is deliberately no `NON_NATIVE` value.** An earlier pass
had one, and it labelled *Southcentral Foundation* — an Alaska Native tribal
health organisation whose name contains no Native marker — as non-Native
because the matcher missed it. That is an authored characterisation of a named
organisation, which is the field §9.5 rejects. Silence is now recorded as
silence.

Native markers are matched on **word boundaries**. With substring matching,
`nation` fired inside `National`, and the National Women's Law Center and the
National Cattlemen's Beef Association were both queued as possibly-Native.

The government side of an OIRA meeting is written as a bare agency acronym —
`USDA/OBPA`, `HHS/CMS`, `DOI/Indian Affairs`. That set is **derived from
reginfo's own agency codes on the meetings themselves** rather than hand-listed,
and a known department acronym in leading position settles the classification —
without which `DOI/Indian Affairs` is the Bureau of Indian Affairs filed as a
tribe.

---

## Zero fabrication

Every row carries `source_url` and a verbatim `source_quote`. OIRA quotes are
the Requestor line and the attendee list as reginfo prints them; Congress.gov
quotes are the witness name, position and organisation with the hearing title;
govinfo quotes are the `<witness>` line exactly as GPO wrote it. Whitespace is
collapsed and long quotes are truncated with an ellipsis. No word is changed.

**No causation is asserted anywhere.** `oira_federal_action_links.csv` carries
`relationship = co_occurrence_meeting_and_rule` and
`hearing_bill_links.csv` carries `relationship = hearing_concerns_bill`. Both
record that two things happened, with their dates. The correlation is the
reader's to draw.

---

## Pull discipline

`logs/_HOSTLOCK_www.reginfo.gov.json`, `_HOSTLOCK_api.congress.gov.json` and
`_HOSTLOCK_api.govinfo.gov.json` are claimed before the first request of each
stage and released after. A stage that finds another script holding a lock
appends its work to that lock's `queue` and exits rather than starting a second
poller. `api.usaspending.gov` was not touched.

Every stage checkpoints **before** its first request — completed search windows
in `_oira_index_state.json` and `_chrg_search_state.json`, completed records in
the JSONL caches — so a killed run loses nothing and resumes on the same
command. That property was used repeatedly: detached pullers were terminated
several times during this build by external process pressure and every restart
picked up exactly where it stopped.

Failures are separated by shape, per `docs/PULL_DISCIPLINE.md`: an instant
disconnect under one second stops the stage as an edge block; HTTP 429 honours
`Retry-After`; a timeout at 30s+ retries with 60s doubling to 30 minutes.

**Concurrency.** Serially, the Congress.gov detail stage measured 0.79
records/sec — 6.7 hours for 17,859 meetings, all of it server latency. The key's
own `X-Ratelimit-Limit` header reports 20,000 requests/hour. Four workers land
near 3/sec ≈ 10,800/hour, inside the published quota, and **one process still
holds the host lock** — this is one poller with a small pool, not four pollers.
reginfo, which publishes no quota, gets two workers each pacing itself so the
site sees about one request per second.

---

## Measured defects found and fixed during the build

| Defect | Effect | Fix |
|---|---|---|
| Containment used for detection | `American Enterprise Institute` → a tribal enterprise; 3 of 4 first resolutions wrong | official-name corroboration rule |
| Native markers matched as substrings | `nation` fired inside `National`; two trade associations queued as possibly-Native | word-boundary regex |
| Trap guard fired on exact matches | `Cherokee Nation` refused against spine `Cherokee Nation` | trap test restricted to partial overlaps |
| `NON_NATIVE_ORGANIZATION` as a value | asserted non-Native for Southcentral Foundation | replaced with `UNRESOLVED_NO_NATIVE_MARKER` |
| Witness guard placed above the bill-link block | markups have no witnesses and markups are where bills live; **363 real bill links reported as 67** | bill links emitted for every meeting |
| 5,685 Congress.gov committee entries carry a `systemCode` and no name | 13,159 appearance rows with a blank `committee` | `systemCode` → name lookup, cached |
| Bare agency acronyms not read as government | `DOI/Indian Affairs` queued as possibly-Native | acronym set derived from reginfo's own agency codes |
| One row per attendee organisation in `oira_meetings.csv` | put a merely-attending organisation into a column named *requesting* | one row per meeting; attendance moved to `oira_meeting_participants.csv` |
| `witness:"Craig"` in the govinfo net | the Alaska village name is a common surname; 336 irrelevant hearings | single-token spine names admitted only at length ≥ 8 and not in `NAME_TRAPS` |
| Corpus published as the dataset | 2,146 OIRA meetings read as 2,146 Native meetings | Native slice to `data/clean`, corpus to `data/interim` |

---

| `_parse_mods_witness` stripped the trailing state but not the city before it | `Org, City, ST` left the CITY as the organisation: Georgetown → an Alaska Native village, Manchester and Middletown → California rancherias; a police department, a poultry company and a university filed as tribal testimony | drop the city too, and **return the state** as a second leg of evidence |
| MODS carries one `<heldDate>` per date its parser finds, including dates in the title | a 2009 Senate Indian Affairs hearing on a bill amending "the Act of March 1, 1933" was dated **1933-03-01**; 10 records affected | pick the `heldDate` falling in the years that Congress actually sat |
| `core()` folds `indian` away as structural | **National Education Association → National Indian Education Association**; five OIRA meetings filed as Native advocacy | guard 5: refuse where the SPINE name carries a Native identity word the record lacks (the reverse direction, `Navajo Nation` → spine `Navajo`, is left alone) |
| `core()` folds corporate forms away | `Enterprise Holdings, Inc.` → Enterprise Rancheria; `Ho-Chunk, Inc.` → the Ho-Chunk Nation | guard 6: a corporate form the spine name does not share bars a match to a government-class entity. ANCs and village corporations are companies by statute and are unaffected |

---

## Run of 2026-08-07 — results

Full report: `logs/98_build_report_2026-08-07.txt`.

| | corpus read | published Native slice |
|---|---:|---:|
| OIRA meetings | **8,227** (2014-04-01 → 2026-09-08, 130 agency codes) | **72** (0.88%) |
| Hearing appearances | **70,380** (1997-02-05 → 2026-07-24) | **2,667** (3.79%), over **971 hearings** |
| OIRA named attendees | 95,529 (41,303 external / 54,226 government) | 1,128 |

- **RIN present on 100% of OIRA meetings.** The RIN joins `federal_actions.csv`
  for **7,164 of 8,227 corpus meetings (87.1%)** and **63 of 72 slice meetings**
  → `oira_federal_action_links.csv`, 145 published links.
- **Bill links: 465** over **325 bills** and **232 hearings** in
  `native_bills.csv`.
- **327 spine entities reached** — 16 as OIRA requesters, 29 as OIRA attendees,
  317 as hearing witnesses.
- **124 of those 327 (37.9%) have no row in
  `native_entity_lobbying_disclosures.csv`.** At organisation-name level, 79 of
  94 slice organisation names on the OIRA side and 789 of 1,032 on the hearings
  side appear nowhere in LDA as a client, a registrant, or a matched entity.
- **3,281 distinct organisations queued** in
  `review/advocacy_unresolved_2026-08-07.csv`, each with the candidate entity
  named and a blank `YOUR_RULING`.
- Tier: 183 hearing rows reach **A** (name plus an agreeing state from a MODS
  witness line); the rest are **B**, pending rulings.

### Committee coverage — the point of not restricting the pull

Native-slice appearances by committee: Indian Affairs committees account for
**799 of 2,667 (30.0%)**. The other **70%** sit at House Appropriations (504),
Natural Resources under its three historical names (694), Financial Services,
Environment and Public Works, Commerce, Energy and Natural Resources, Banking,
Homeland Security, Foreign Affairs, Veterans' Affairs, Education, Judiciary,
Small Business and Agriculture. **A pull restricted to the Indian Affairs
committees would have missed seven Native witnesses in ten.**

### The OIRA finding, with the alternative explanation ruled out

**72 of 8,227 OIRA meetings on rules under EO 12866 review, 2014–2026, involved
a Native entity — 0.88%.** Nineteen of those had a Native entity as the
*requester*.

That number is small enough that the first question must be whether the matcher
is failing rather than the phenomenon being rare. It was tested directly against
the raw corpus, and it is not the matcher:

- Of **8,227** requesting-organisation strings, only **a handful** contain any
  of `tribe|tribal|indian|native|pueblo|nation|rancheria` at all, and nearly all
  of those resolved. The named requesters that did resolve are exactly what one
  would expect and are individually checkable: **Moapa Band of Paiute Indians**
  on the EPA coal-combustion-residuals rule, **Morongo Band of Mission Indians**
  on the federal-acknowledgment procedures rule, **Crow Nation / Crow Tribe** on
  the Stream Protection Rule, **Ute Indian Tribe** on the oil-and-gas federal
  implementation plan, **Penobscot Nation and Houlton Band of Maliseet Indians**
  on the Maine water-quality standards.
- Of **41,303** external attendee affiliations, only **16** carry a Native
  marker word, and 12 of those resolved. The remainder are a genuine gap in the
  spine (`National Tribal Air Association`), an abbreviation
  (`Southern Ute Ind Tribe`), and one government string now classified as such
  (`DOI/Indian Affairs`).
- Indian-law and lobbying firms appearing *for* clients were checked separately:
  60 attendee rows are Holland & Knight, Akin Gump, Van Ness Feldman, Greenberg
  Traurig, Dentons or Dorsey & Whitney. **Which client they were there for is
  not stated on the meeting record**, so those rows are recorded as the firms
  they name and are not attributed to any tribe.

So the low rate is a property of the channel, not of the matcher. The reading
that fits the evidence — and it is a reading, offered as such — is that tribal
input into federal rulemaking runs through **consultation**, the statutory
government-to-government channel, rather than through the EO 12866 meeting
request, which is the route available to an outside interest with no
consultation right. A concurrent Cedar build reports 128 tribes appearing in
consultation records that have never filed an LDA report, which is consistent
with that. **This build does not assert it.** What it records is that across
8,227 published OIRA meetings, a Native entity was present at 72.

### Known limits of this run

- **reginfo serves nothing before 2014.** OIRA meetings 1994–2013 are outside
  the source, not absent from history.
- **The hearings floor is uneven by design.** Congress.gov gives a complete
  witness universe for the House from the 112th Congress; govinfo supplies the
  Senate and the pre-112th backfill through a *witness-field net*, so hearings
  before 2013 and Senate hearings throughout are reached by net rather than by
  census. A Native witness whose organisation name carries no marker word and
  is not on the spine can be missed there. The corpus files retain everything
  read, so the gap is measurable rather than invisible.
- **GPO occasionally packs several witnesses into one `<witness>` element**
  ("accompanied by …"). Those parse to an unusable organisation, resolve to
  nothing, and keep their raw text as the source quote.
- **Everything automated is Tier B or C.** 3,281 organisations await rulings.

## Run report

The authoritative counts for any run are written to
`logs/98_build_report_<date>.txt` by the `build` stage, which prints the corpus
size and the Native slice side by side for both channels, the RIN and bill link
rates, the committee distribution of Native-slice appearances, the spine
entities reached, and how many of those entities never appear in
`native_entity_lobbying_disclosures.csv`.
