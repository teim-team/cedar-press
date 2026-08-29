# The lobbying REGISTRANT as a first-class hub

*Built 2026-08-26 by `code/180_build_lobbying_registrant_hub.py`,
`code/181_enrich_lobbying_registrant_identifiers.py`,
`code/182_rule_lobbying_registrant_native_ownership.py` and
`code/183_register_lobbying_registrant_layer.py`. Zero network calls in all
four. Every number below is measured at run time; regenerate rather than
hand-edit. `62_no_regression_check.py` GREEN before and GREEN after.*

The brief, from the project owner:

> "for lobbying, it's probably worth adding the firm that was hired to lobby,
> and maybe we can get more info on them from IRS 990 or other sources. The
> non-Native lobbying firm who isn't a tribe will have more data than the
> tribe, and we can link them to Native entities."

**The first half was already on disk and unbuilt. The second half is
measurably false of the IRS data, and that measurement is the more useful
finding.**

---

## WHAT WAS BUILT

| file (`data/clean/`) | rows | grain |
|---|---:|---|
| `lobbying_registrants.csv` | **653** | one row per Senate LDA `registrant_id` |
| `lobbying_registrant_client_relationships.csv` | **1,309** | one row per (registrant, client) |
| `lobbying_registrant_identifiers.csv` | **525** | one row per identifier assertion, with its asserter |
| `lobbying_registrant_native_ownership_evidence.csv` | **27** | one row per evidence route |
| `lobbying_registrant_concentration.csv` | **36** | one row per scope |

Plus three review files and five codebook fragments (`18a`–`18e`), five notes
contracts in `dist/04_lobbying/`, and additive entries in `25`'s `TABLES` and
`27`'s `SPEC`.

**`registrant_id` is the key, never the name.** Three registrant_ids in this
corpus carry more than one name over time — a rename is not a new firm — and
keying on the name splits PACE, LLP across two rows and undercounts it by 27
filings.

---

## THE HEADLINE CONCENTRATION FIGURES — nobody has computed these before

Over **26,955 filings, 1999–2026**, whose client keys to a Native entity:

| | |
|---|---:|
| registrants representing Native clients | **406** |
| Native entities represented | **300** |
| registrant–client engagements | **1,309** |
| reported lobbying spend (deduplicated) | **$645.1M** |

| share of… | filings | reported spend |
|---|---:|---:|
| top 1 firm | **6.9%** | 13.9% |
| top 3 | 17.7% | — |
| top 5 | **23.6%** | 29.8% |
| top 10 | **35.3%** | **43.1%** |
| top 20 | 48.8% | 57.1% |
| top 50 | **68.3%** | — |
| **HHI** | **190** | **331** |

**The answer to "do a handful of firms represent most of Indian Country?" is
NO, and that is the finding.** Fifty firms of 406 carry 68% of the filings, but
the largest single firm carries under 7% and the HHI is 190 on a 0–10,000
scale. By the yardstick people reach for — the DOJ/FTC merger thresholds of
1,500 and 2,500 — this is an unconcentrated market. *(That yardstick is quoted
because it is familiar. A market for federal lobbying representation is not a
merger market and no antitrust conclusion is asserted; the caveat travels on
every row of the table.)*

### And it is getting LESS concentrated, monotonically

| filing year | registrants active | top-5 share of filings | HHI | entities represented |
|---|---:|---:|---:|---:|
| 1999 | 76 | **35.9%** | 391 | 124 |
| 2004 | 99 | 32.0% | 309 | 171 |
| 2009 | 111 | 33.2% | 315 | 178 |
| 2014 | 107 | 31.0% | 330 | 187 |
| 2019 | 105 | 27.0% | 253 | 196 |
| 2024 | 109 | **24.6%** | **224** | 202 |

More Native entities are represented each year by roughly the same number of
firms, and the leaders' share of the work falls throughout. **A per-year series
crosses the 2008 semi-annual→quarterly reporting change**, so filing COUNTS are
not comparable across it; the SHARES are, because the change hits every firm in
a year identically.

### The concentration that is real is inside the entity classes

| Native entity class | registrants | entities | top-5 filings | HHI |
|---|---:|---:|---:|---:|
| Federally recognized tribe | 362 | 267 | 23.5% | **196** |
| Alaska Native Regional Corporation | 66 | 12 | 41.2% | 561 |
| Federally recognized Alaska Native Village | 11 | 10 | **90.8%** | **2,482** |
| Federal-level self-governance consortium | 7 | 3 | 96.2% | 2,709 |
| State-recognized tribe | 15 | 4 | 58.0% | 944 |

**The market for representing tribal governments is competitive; the market for
representing everyone else is not.** Ten Alaska Native villages are served by
eleven registrants and five of them do 91% of the work.

### The reverse measure — how many firms does one entity use?

Median **3**. Maximum **16**. **65 of 300 entities use exactly one firm**, and
**119 use five or more.** A tribe with one firm and a tribe with sixteen are
running different strategies, and until now neither was countable.

### Who they are — by filings on Native clients

| registrant | filings | Native clients | entities | reported $M |
|---|---:|---:|---:|---:|
| SONOSKY, CHAMBERS, SACHSE, ENDRESON & PERRY, LLP | 1,858 | 55 | 55 | 12.5 |
| HOBBS, STRAUS, DEAN & WALKER, LLP | 1,603 | 36 | 36 | 7.3 |
| HOLLAND & KNIGHT LLP | 1,298 | 52 | 49 | 22.2 |
| PACE, LLP | 793 | 21 | 21 | 29.2 |
| IETAN CONSULTING, LLC | 800 | 30 | 30 | 27.8 |
| SPIRIT ROCK CONSULTING | 741 | 24 | 22 | 23.3 |
| AKIN GUMP STRAUSS HAUER & FELD | 689 | 26 | 25 | **89.5** |
| PEEBLES BERGIN FKA PEEBLES KIDDER | 614 | 18 | 17 | 2.9 |
| MAPETSI POLICY GROUP | 577 | 11 | 11 | 15.3 |
| SENSE INCORPORATED | 538 | 13 | 12 | **0.0** |

**Filings and dollars rank differently and the gap is the finding.** Sonosky
files three times as much as Akin Gump for four times as many nations and
reports one-seventh the money.

**Sense Incorporated is the worked example of why the dedup rule matters.** It
files 538 times for 12 Native entities. **534 of those 538 filings report no
dollar figure at all**; the remaining four sit in period cells where a later
amendment superseded the original with a nil return. So its published
`spend_reported_usd` is **$0.00** while its sensitivity columns read
**$20,000** on both the per-cell-maximum and naive bases. Neither number says
the firm worked for free. One says *"the last thing filed for every period was
a nil return"* and the other says *"a nil return replaced something"*, and the
table carries both so the reader can tell which question they are asking.

---

## THE SPEND FIGURE IS DEDUPLICATED, AND THE NAIVE SUM IS 6.3% TOO BIG

An LDA amendment RESTATES the quarter it amends; a termination report covers
the final quarter. Summing `spend_usd` over filings therefore counts the same
money twice on **2,269 of 24,384** (registrant, client, year, period) cells.

| basis | total |
|---|---:|
| naive sum over filings | $685.8M |
| per-cell maximum | $650.4M |
| **per-cell latest-posted filing — PUBLISHED** | **$645.1M** |

The published figure takes the value from the filing with the latest
`dt_posted` in each cell, because an amendment supersedes what it amends. All
three are on every row of the hub and the relationship table, so the choice is
visible and reversible.

Caveats that travel with every dollar in this layer, and they are not small:

- LDA income/expenses is a good-faith estimate **rounded to $10,000**.
- **11,145 of 26,955 keyed filings (41.3%) report no dollar at all** and are
  carried as 0. **A zero here means "reported nothing", not "spent nothing".**
- Income and expenses are either/or. 122 expense rows against 15,688 income
  rows is correct, not a gap.

---

## THE IRS HYPOTHESIS, TESTED AGAINST THE WHOLE BUSINESS MASTER FILE

The owner's premise — *"the non-Native lobbying firm will have more data than
the tribe"* — is true of the world and **specifically false of the IRS data
this project holds.** Measured, not estimated:

| | |
|---|---:|
| IRS exempt organisations scanned (`bmf_full_2026-08-12/eo*.csv`) | **1,957,340** |
| LDA registrants tested | **653** |
| registrant names hitting the BMF at all | **6** |
| …with state agreement | **5** |
| **share of registrants reachable through the 990 universe** | **0.8%** |

**A DC lobbying LLP or a law-firm partnership is a for-profit partnership. It
files no Form 990 and is ABSENT FROM THE 990 UNIVERSE BY CONSTRUCTION.** This
is the same shape as `docs/IDENTIFIER_GRAPH_BUILD_LOG.md`'s finding that
EIN↔UEI overlap is 0.22% — and it is the same lesson: **measure the
intersection, not the schema.** Where a lobbying firm's data actually lives is
SAM entity management (blocked on the pending 10/day→1,000/day role request),
state corporate registries, and LDA itself.

### What DID land, and the route nobody would have predicted

| identifier type | assertions | registrants | tiers |
|---|---:|---:|---|
| `HOUSE_REGISTRANT_ID` | **482** | **482** | A |
| `UEI` | 25 | 10 | B 16 · C 9 |
| `EIN` | 12 | 8 | B 10 · C 2 |
| `CAGE` | 6 | 5 | B 2 · C 4 |
| **total** | **525** | **488 of 653 (74.7%)** | A 482 · B 26 · C 17 |

**The single biggest identifier win was already in the file and nobody had
read it.** The Senate LDA registrant record CARRIES the Clerk of the House
registrant id as a field. That is not a match — it is a second federal
identifier stated by the registrar itself, which is why it is the only tier-A
row in the table, and it covers **482 of 653 registrants**. The keyed
disclosure CSV drops it, along with the registrant's address, its
self-description, its contact and its lobbyist roster.

**The unpredicted route: Johns Hopkins University's own Form 990 Schedule I.**
Cedar's Schedule I table names *VAN SCOYOC ASSOCIATES INC, EIN 52-1710923,
Washington DC* and *CLARK HILL PLC, EIN 38-0425840, Detroit MI* as sub-award
recipients on JHU's TY2016/TY2017 returns. **That is an EIN for a for-profit
lobbying firm, obtained from an IRS filing the firm did not make.** It is the
owner's hypothesis working, by a mechanism the hypothesis did not name: you do
not need the firm to file a 990, you need somebody who paid it to. Clark Hill
sits at tier C only because its BMF-side state (MI, its Detroit headquarters)
disagrees with its LDA registrant address (DC, its Washington office) — the
match is almost certainly right and the tier says what the evidence says.

Five of the twelve EIN rows carry a 990 financial record. **The caveat that
must travel with any of it: 6,453 of 12,764 organisations in `np_orgs` are
990-N filers reporting no financial detail — a zero there is the filing regime,
not a finding.** And LDA spend and 990 lobbying are different measures on
different definitions and are never summed.

### The trap the guard caught, before it shipped

The BMF holds **SPIRIT ROCK MEDITATION CENTER, EIN 94-2971001, Woodacre,
California** — a Buddhist retreat centre. **SPIRIT ROCK CONSULTING is a
government-affairs firm in Alexandria, Virginia** with 741 filings for 22
Native entities. A fuzzy or containment match joins them and puts a 990 on a
lobbying firm. The name-exact-plus-state guard refuses it and the refusal is
written to `review/`, not dropped.

Also refused, by name: `ENGAGE, LLC` (VA) against two unrelated `ENGAGE` orgs
in MI and CA; four malformed CAGE codes, including the literal string `NAN`
carried in `prime_contracts.cage_code` — a pandas NaN written out as text,
which passes every non-empty test and is not a CAGE; and **two DUNS**, refused
at source because `cedar_domain` lists DUNS in `LICENSED_IDENTIFIER_TYPES` and
D&B Open Data never publishes. **Refusing the type is stronger than stripping
the column later: a published table should not be the place that question first
gets asked.**

### Tiers here are DECLARED, and the reason is written down

No source in this project asserts *"this LDA registrant is that EIN"*. There is
no row to inherit a tier from, so the tier is declared once, in `SOURCE_TIER`,
and **never above B** — the same tier and the same method name
(`normalized_name_plus_state_exact`) that all 28 rows of `np_ein_uei_bridge.csv`
carry. `n_asserting_sources` records corroboration (NARF's EIN is asserted by
three independent local sources) and **never promotes a tier**, because two-leg
promotion is a ledger method and not a consumer's to mint.

---

## WHICH REGISTRANTS ARE THEMSELVES NATIVE — 13 of 653, with evidence

**11 `NATIVE_ENTITY` · 2 `NATIVE_OWNED` · 640 `NO_CLAIM_FOUND`.**

| registrant | entity | tier | routes |
|---|---|---|---|
| CALISTA CORPORATION | `ANRC-CALSTA-00` | B | R1 + R3 |
| CHUGACH ALASKA CORPORATION | `ANRC-CHGCCO-00` | B | R1 + R3 |
| NANA REGIONAL CORPORATION | `ANRC-NANARC-00` | B | R1 + R5 |
| NANA DEVELOPMENT CORPORATION | `ANRC-NANARC-00` | B | R5 |
| ARCTIC SLOPE REGIONAL CORP | `ANRC-ARCSLO-00` | B | R1 + R5 |
| COOK INLET REGION INC. | `ANRC-CKINLT-00` | B | R1 |
| AFOGNAK NATIVE CORPORATION | **held for a ruling** | B | R1 + R3 |
| ALUTIIQ, LLC | `AKNF-AFGNAK-00-KONIAG` | B | R1 |
| MICCOSUKEE TRIBE OF INDIANS OF FLORIDA | `TRBF-MCSKEE-00` | B | R1 + R5 |
| NANTICOKE LENNI-LENAPE TRIBAL NATION | `TRBS-NANTCK-00` | B | R1 + R3 |
| NATIVE AMERICAN RIGHTS FUND | `ITO-RGHTSF-00` | B | R3 |
| NATIONAL AMERICAN INDIAN HOUSING COUNCIL | `ITO-HOUSIN-00` | B | R3 |
| NATIONAL INDIAN GAMING ASSOCIATION | `ITO-GAMING-00` | B | R3 |

**The strongest evidence in LDA is a firm filing on its own behalf.** When
registrant and client are the same organisation on the face of the filing, the
registration is the firm's own sworn statement of who it is. Ten registrants
self-file; **nine of the ten are Native entities.** The tenth is SALT RIVER
PROJECT, an Arizona public power and irrigation district with 333 filings,
already withdrawn by `65_lobbying_organization_type_guard.py` — *"NOT the Salt
River Pima-Maricopa Indian Community"*, in the guard's own words. That guard
is the reason this route is safe to use.

### The trap this build paid for, before it shipped

The obvious spine route — normalize the registrant's name and look it up —
matches **`ALUTIIQ, LLC` to `AKNF-ALTIIQ-00-KONIAG`, the Native Village of
Alutiiq, a village GOVERNMENT.** Alutiiq LLC is a subsidiary of Afognak Native
Corporation. That is AGENTS.md's containment defect, **direction 2** — *"NATIVE
VILLAGE OF ELIM → Elim Native Corporation"* — arriving through a brand new door,
because normalization had stripped `LLC` and the shortest spine name won.

**The guard: the spine route preserves corporate-form tokens.** `ALUTIIQ, LLC`
and `Alutiiq` are not the same string once `LLC` survives normalization.
`CALISTA CORPORATION` and `Calista Corporation` still agree. **The guard costs
zero correct matches and forecloses the whole class.**

### And the family it exposed, again

**AFOGNAK NATIVE CORPORATION carries a blank entity id, deliberately.** Two
equally strong routes name different entities: the self-filed route (inherited
from the disclosure file) says `AKNF-AFGNAK-00-KONIAG`, the Afognak *village*;
the spine route says `ANVC-AFOGNA-00`, Afognak Native *Corporation*. **When two
equally strong routes disagree, this build does not pick.** The id is blank,
the disagreement is on the row, and it is queued.

This is the `ALASKA_VILLAGE_GOVERNMENT_VS_VILLAGE_CORPORATION` family from
`docs/IDENTIFIER_GRAPH_BUILD_LOG.md` — **334 identifiers, $24.52B, one
ruling** — turning up in the lobbying data. `ALUTIIQ, LLC` carries the same
flag on its basis text: the claim is inherited from the source and only a
ruling may change it. **One ruling settles all of them.**

### Ietan, Spirit Rock and Mapetsi: NO_CLAIM_FOUND, and what that means

The brief named these three as plausible candidates. **All three come out
`NO_CLAIM_FOUND`, and none of them comes out NOT_NATIVE — there is deliberately
no such value in this layer.**

What is on the record for them, and is NOT evidence of ownership:

| registrant | LDA self-description, verbatim | office | LDA contact |
|---|---|---|---|
| IETAN CONSULTING, LLC | `consulting` | Tulsa, OK | WILSON PIPESTEM |
| SPIRIT ROCK CONSULTING | `Government Affairs.` | Alexandria, VA | AURENE MARTIN |
| MAPETSI POLICY GROUP | `government affairs` | Washington, DC | DEBBIE HO |
| SENSE INCORPORATED | `Provides technical,representative and support services American Indians&Alaska Native Trib` | Washington, DC | C. JULIET PITTMAN |
| PEEBLES BERGIN FKA PEEBLES KIDDER | `Law firm dedicated to federal Indian law.` | Washington, DC | CORA STEVENS |

**Every one of those strings describes what the firm DOES. Not one describes
who OWNS it.** Sense Incorporated's is the clearest case: *"provides … services
American Indians & Alaska Native Trib[es]"* is `serves_native_entities`, and
`serves_native_entities` is not `parent_native_entity`, here as everywhere else
in this project. A contact name is not ownership evidence either — this is the
project that already turned National Education Association into National Indian
Education Association by treating a word as a fact.

**The route that settles it was NOT_CHECKED and the reason is on every affected
row:** R6, the firm's own published statement of ownership quoted verbatim with
its URL — the standard AGENTS.md sets for the individually Native-owned class.
The session's web-search budget was exhausted (200/200) before it could run, and
two guessed domains failed DNS. Rather than thrash a host, the work is staged:
**`review/lobbying_registrant_native_ownership_queue_2026-08-26.csv` holds 41
questions**, the 40 highest-volume `NO_CLAIM_FOUND` registrants ranked by
filings on Native clients plus the Afognak disagreement, each carrying the LDA
self-description, city, contact and volume, and each naming exactly what would
settle it: *the firm's own published ownership statement, an SBA certification
record, or a state corporate filing naming the owner.* That is a session's work
of ~40 fetches.

One live lead is already in the ledger: **DANCING RABBIT TRIBAL CONSULTING LLC,
CAGE `9Y2N6`, Durant OK, `entity_class = TRIBAL_UNCROSSWALKED_SBA`, evidence
`https://search.certifications.sba.gov/`** — tier C via `need_v6`, so it does
not publish, but it names a source that would settle it.

### A RULED method is not a POSITIVE ruling

`148_resolve_schedule_i_recipients.py` carries a live bug promoting 42 tier-X
NEGATIVE rulings to tier A, because it tested that a ruling EXISTED and not
what the ruling SAID. **This build tests the value:**

| value | treatment |
|---|---|
| `native_controlled`, `tribally_controlled` | POSITIVE — a claim |
| `place_name_coincidence`, any tier-X ledger row | NEGATIVE — **blocks**, and no weaker positive overrides it |
| `native_serving` | **neither** — recorded in its own column, never touches the ownership status |
| `UNRULED` | neither — 12,393 of 12,764 `np_orgs` rows |

---

## WHAT WAS DELIBERATELY NOT BUILT

- **`position_on_native_issue`, or any characterisation of a firm's stance.**
  `docs/LOBBYING_EXPANSION_RECONCILIATION.md` settled this: it is a verdict we
  would be authoring about a named organisation, it is the most legally exposed
  field in the product, and the prime directive is that this project never
  falsely attributes. Nothing in these five tables says a firm is for or
  against anything.
- **Any name matcher against a registrant name to find a tribe.** Sweeping 653
  firm names for tribes is DETECTION, which AGENTS.md forbids containment for.
  Every Native-entity link on every relationship row is INHERITED verbatim from
  the keyed disclosure row that already carried it, with that row's
  `attribution_method`, and the relationship carries the **weakest** confidence
  seen on any filing in the pair.
- **A person-level lobbyist register.** The corpus holds **129,730 lobbyist
  rows over 3,281 distinct individuals, 23,548 of them declaring a covered
  federal position.** That is the revolving door in the filers' own words —
  *"Acting Assistant Secretary - Indian Affairs"* appears **1,030 times**,
  *"Chief Counsel, Senate Committee on Indian Affairs"* 205, *"Staff Director
  and Chief Counsel for the Senate Committee on Indian Affairs"* 138. It is
  aggregated to the FIRM in `n_distinct_lobbyists_corpus`,
  `n_lobbyist_rows_with_covered_position` and
  `covered_positions_verbatim_top`; **no individual is named.** A person-level
  table is a real dataset and a separate decision.
- **`reported_native_preference` as evidence of anything.** It is not used
  anywhere in this layer. It is the union INCLUDING 8(a), which is open to any
  disadvantaged owner; the genuinely Native-specific set-asides are $1.92B,
  0.78% of attributed dollars. And 57.2% of attributed dollars sit on awards
  with no Native set-aside at all — **absence of a flag says almost nothing**,
  which is the same discipline as `NO_CLAIM_FOUND` never being `NOT_NATIVE`.

---

## READING THE COUNTS — the denominator, every time

**Every count whose column name lacks `native` is a FLOOR on the firm's
practice.** The corpus behind this layer is a Native-KEYWORD pull of the LDA
(39,448 filings pulled, 27,796 matched), not the LDA and not any firm's book of
business. Holland & Knight has 1,298 filings here and thousands more in LDA.
`n_clients_corpus` is not the firm's client count and the column name says
`_corpus` for that reason.

And the denominator warning already on
`docs/LOBBYING_EXPANSION_RECONCILIATION.md` applies unchanged: **97.0% keyed is
26,955 of 27,796 — the post-match file.** Coverage of the pulled universe is
**68.3%**. Both are true of different things. Say which you mean.

`review/lobbying_registrant_data_quality_2026-08-26.csv` flags **47
registrations that must not be read as ordinary hired firms** — self-filers
whose only client is themselves, registrants whose every filing was withdrawn
by the org-type guard, and single-filing registrations. Among them are three
Fort Lauderdale registrations — *NATIVE AMERICANS TRIBE*, *ALASKA NATIVES
TRIBE*, *AMERICAN INDIANS TRIBE*, all describing themselves as `TRIBAL
GOVERNMENT`, all with the same contact. **A flag there is a property of the
registration, not a judgement about the registrant.**

---

## THE GATE

`62_no_regression_check.py` was GREEN before this work and is GREEN after.

It failed in between, on exactly the metrics it exists for — `ship_tables_at_zero`
205→210, `tables_missing_codebook_block` 144→145, `..._25_TABLES` 234→239,
`..._27_SPEC` 249→254, `..._notes_contract` 206→211 — because five tables landed
in `data/clean` unregistered. That is the last-mile failure the gate was built
to catch, and it caught it within minutes of the tables landing. Closed by
`code/183`:

- five codebook **fragments** (`18a`–`18e`), **0 undescribed variables**; the
  master is never written, per the 2026-08-07 lost-update fix
- five notes contracts in `dist/04_lobbying/`, in `87`'s exact schema with its
  `TERMS`, `READING` and `RESEARCH_READY` blocks **imported, not copied**
- five additive entries in `25`'s `TABLES` and five authored entries in `27`'s
  `SPEC`, edited by hand because a script that rewrites another agent's script
  is worse than a reviewable diff

**The full `SHIPPING_RUNBOOK` chain was NOT run**, and that was deliberate. Its
own opening line says it is *staged, not run*; `87` rewrites EVERY dataset's
notes contract, and `START_HERE.md` records `dist/` as stale against the archive
backfill, so a blanket refresh would publish contracts asserting that 1.2M prime
rows ship when the export behind them is a 617,142-row vintage. **A notes
contract asserting a row count that has not shipped is a false claim, and this
project does not make one to satisfy a metric.**

After: all five metrics back to baseline exactly (205 / 140 / 234 / 249 / 206),
`ship_dist_rows` **rose** 5,227,896 → 5,230,446 (exactly the 2,550 rows of the
five new tables), `ship_tables_shipping` 49 → 54, `tables_missing_codebook_block`
**fell** 144 → 140, and the three trap metrics remain 0.

---

## FILES

| file | rows | note |
|---|---:|---|
| `data/clean/lobbying_registrants.csv` | 653 | the hub |
| `data/clean/lobbying_registrant_client_relationships.csv` | 1,309 | who represents whom |
| `data/clean/lobbying_registrant_identifiers.csv` | 525 | every identifier, with its asserter |
| `data/clean/lobbying_registrant_native_ownership_evidence.csv` | 27 | one row per evidence route |
| `data/clean/lobbying_registrant_concentration.csv` | 36 | ALL · 28 filing years · 7 entity classes |
| `review/lobbying_registrant_native_ownership_queue_2026-08-26.csv` | 41 | what a web pass would settle |
| `review/lobbying_registrant_identifier_refusals_2026-08-26.csv` | 12 | every candidate NOT written, with the reason |
| `review/lobbying_registrant_data_quality_2026-08-26.csv` | 47 | registrations that are not ordinary firms |
| `data/clean/codebook/18a`–`18e_*.csv` | 184 vars | fragments only; the master is never written |
| `dist/04_lobbying/lobbying_registrant*.notes.json` / `.NOTES.md` | 5 each | the notes contract |

**Nothing shared was rewritten.** `native_entity_lobbying_disclosures.csv`, the
spine, the ledger, `prime_contracts.csv` and the nonprofit tables were read and
not touched. `lobbying_registrants.csv` is written by 180 and patched in place
by 182 on the eight ownership columns 180 declares — the enricher runs last,
which is the ordering rule the FERC collisions earned.

---

## THE RULE THIS BUILD EARNS

**"The counterparty has more data" is a claim about the world, not about your
disk — and it is routinely mistaken for one.**

The owner was right that a DC lobbying firm is better documented than most
tribal clients. It is: state incorporation records, bar registrations, SAM
entity management, LDA's own registrant record. **None of that is what Cedar
holds.** Cedar holds a Native-scoped nonprofit universe and a Native-scoped
spending corpus, and a for-profit lobbying partnership is outside both by
construction — 5 of 653 reachable through 1.96 million IRS organisations.

The enrichment that DID work came from two places nobody proposed: **the source
file we already had and had not fully read** (the House registrant id, on 482 of
653, sitting unread in the raw LDA record while the keyed CSV dropped it), and
**somebody else's filing about the firm** (Johns Hopkins' Schedule I, naming a
lobbying firm's EIN on a return the firm never filed).

**Before planning enrichment from an external source, measure the intersection
with what you hold — and read the source you already have to the bottom first.**
