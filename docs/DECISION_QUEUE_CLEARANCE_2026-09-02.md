# Clearing the owner decision queue — rulings, evidence, and what is left

*Written 2026-09-02 by workstream **DQC** (`code/1103_decision_queue_clearance.py`).
Under the owner's standing rule of 2026-09-01, repeated five times: "I'm not
deciding anything except adjudicating Native entities — you are doing it. Stop
asking, and make corrections and updates and findings." And, for entity
questions: "you can review websites and SAM or annual reports as long as you
document the decisions and learn from them."*

**Nothing in this pass touched `cedar_identifier_ledger_final.csv`,
`cedar_entity_spine.csv`, `entity_aliases.csv` or a shipping money table.** Nine
other workstreams are live. Everything that needs one of those files is handed
over by name at the bottom.

Reproduce, in order:

```
py -3 code/1103_decision_queue_clearance.py measure    # read-only
py -3 code/1103_decision_queue_clearance.py apply      # in place, additive
py -3 code/1103_decision_queue_clearance.py verify     # exits 1 on breach
py -3 code/1103_decision_queue_clearance.py selftest   # proves verify FIRES
```

`verify` **PASS — 11 tables, 0 breaches.** `selftest` **PASS** — a deleted row, a
$1 change and a dropped column each detected, then restored.

---

## THE FINDING THAT REFRAMES THE WHOLE QUEUE

**The decision queue is not a backlog of undecided questions. It is largely a
backlog of decisions that were made and never written down where the queue
could see them.**

Measured across every item worked today:

| item | the queue says | what is actually true |
|---|---|---|
| **16.6** master queue, 6,559 rows / $82.1B | "never opened … `YOUR_RULING` filled on ZERO" | the top 50 by dollars were adjudicated 2026-09-01 by `604`, and **1,115 further rows carrying $42.3B — more than half the money in the file — had already been answered by the pipeline**, in the ledger or in the live assistance table |
| **16.7 / 16.8 / 16.9 / 16.10** | four open questions, 15,162 rows | **all four were decided on 2026-09-01** by int-3 and sit in `data/staging/review_backlog_class_dispositions.csv`, unread by the files they rule |
| **16.5** OSHA, 711 establishments | "`YOUR_RULING` filled on **zero** of 711" | all 711 were ruled on 2026-09-01 by `589_adjudicate_osha_711.py` into a **sibling file**; the file the queue names was never updated |
| **16.4** text mentions | recommends shipping a `mentions` measure | `regulations_gov_entity_coverage.csv` has carried `text_mention_rows` since it was built |

The mechanism is always the same and it is the one this repo already writes down
about numbers: **a decision goes stale in place.** A ruling recorded in a new
file, a staging table, or a differently-named sibling does not reach the queue
row that asked for it, and the queue keeps presenting a settled question as
open. That is what this pass fixed: **every ruling is now written onto the row
that asked for it**, with its evidence, its rule and its date.

**The general rule this earns, and it belongs beside "numbers go stale in
place":**

> **A DECISION MUST BE WRITTEN ONTO THE ROW THAT ASKED FOR IT.** A ruling in a
> sibling file, a staging table or a summary doc is invisible to the queue, and
> an invisible ruling is re-asked. If a pass cannot write back to the asking
> row, it has not finished.

---

## 16.6 — THE MASTER QUEUE. All 6,559 rows adjudicated, $82,062,786,029 accounted for

**It is not one queue.** It is 27 source files piled into one on 2026-08-07, and
the honest unit of decision is the **class**, not the row. Every class is ruled
once against live data; the ruling, its rule and its reasoning are written onto
every row it covers. Row count and dollars are conserved exactly.

| disposition | rows | dollars |
|---|---:|---:|
| `AFFIRM_TIER_B` | 1,353 | $4.53B |
| `FLOOR` | 1,215 | $31.96B |
| `DEFECT` | 1,196 | $2.62B |
| **`ALREADY_APPLIED`** | **1,115** | **$42.33B** |
| `ROUTED` | 893 | — |
| `HOLD` | 395 | $0.7M |
| `REFUSE` | 361 | — |
| `ACCEPT` | 14 | — |
| `AFFIRM_WITHDRAWAL` | 12 | $38.0M |
| `ALREADY_RULED` | 5 | $0.58B |
| **total** | **6,559** | **$82.06B** |

Per-row: `data/staging/decision_queue_1103/master_queue_dispositions_2026-09-02.csv`.

### The three measurements that did the work

**1. `funding_tribe_candidates` — 541 rows, $32.66B — is 99.6% already applied.**
The row asks *"Lineage A attributes UEI X to hand-checked tribe_id N. Candidate
NEID is Y. Is that right?"* Measured against the live
`federal_funding_transactions.csv`: those 367 UEIs carry **184,194 live rows, of
which 181,340 are `attribution_status = cedar_neid`**, and of the 367 UEIs whose
candidate NEID survives the queue's truncation, **314 carry exactly the proposed
id**. Two rows are genuinely unattributed and are the only HOLDs in the class.
The scheme the question was written against — the Lineage-A integer `tribe_id` —
**was retired on 2026-09-01 by `843_retire_cicd_scheme.py`, and there are no
`lineageA_dofile_integer` rows left**, so the two-scheme hazard the question
describes no longer exists.

**2. `contract_new_ueis_fy2023_2026` — 576 of 1,198 rows are stale.** The row
says the identifier is *"absent from both `prime_contracts.csv` and the
ledger"*. Re-measured today: **576 of them are IN the ledger** (471 tier C, 105
tier B), carrying $9.67B. The remaining 622 close under 16.3's confirmed
self-certification ceiling — tier C, a stated universe floor, never a queue.

**3. `review_queue_2026-08-05` — 1,338 rows, none of them open.** Every row asks
*"is firm X genuinely owned by nation Y?"* All 1,338 identifiers are already in
the ledger: **1,333 at tier A/B and 5 at tier X**. The tier-X five are negative
rulings that already stand, and they include **Kluti Kaah, $583M — whose true
owner, the Native Village of Eyak, is NOT IN THE SPINE.** *(**SUPERSEDED 2026-09-02** — it is: `CE-0004H-T9`, canonical name `Eyak`, class `Federally recognized Alaska Native Village`. The gap this paragraph is reasoning about is closed and 4,272 prime rows are attributed on it by `ruling_applied`.)* That gap is worth its
own pass and is escalated below.

### The queue's own two defects, both worth keeping

- **The `question` column is truncated at 200 characters.** That is why the
  candidate NEID reads as `TRB` on the Shoshone-Bannock row and is unreadable on
  174 others. The identifier is not missing; the sentence carrying it was cut.
- **`identifier` is blank on 2,443 of 6,559 rows** and holds a **CAGE**, not a
  UEI, on the 1,198-row contract class. Joining on it is what made an earlier
  pass report the overlap with already-ruled rows as "exactly 1" when it is 223.

### Two classes ruled on their own evidence, not by doctrine

- **`corrupt_cage_codes` (8 rows) — DEFECT, and NOT repaired.** Seven lost a
  leading zero to Excel (`6085` for `06085`); one, Tetra Tech's `7.80E+09`, was
  rendered in scientific notation and **its digits are gone**. None of the eight
  is a Native entity — they are BAE, Lockheed, Boeing, Raytheon, General
  Dynamics — so no attribution and no dollar depends on the repair. The correct
  action is not to reconstruct the string but to **refuse the join**: a
  four-character CAGE is malformed on its face and must never key anything.
  Re-derive from the source extract, never from the damaged cell.
- **`lobbying_withdrawn_by_org_type` (12 rows, $38.0M) — the withdrawal is
  AFFIRMED.** SALT RIVER PROJECT is Arizona's public power and irrigation
  district, not the Salt River Pima-Maricopa Indian Community; COEUR D'ALENE
  MINES is a mining company named for a lake; CITY OF SANTA ROSA and THE
  METROPOLITAN WATER DISTRICT OF SALT LAKE & SANDY are municipal bodies. Every
  one is the Umatilla Electric shape.

### `funding_new_period_new_ueis` — 1,188 rows, $2.62B — is a BUILDER defect

These rows carry a recipient name and a dollar figure and **nothing else**: no
identifier, no question text, no evidence URL. A queue row with no question is
not a decision the owner declined to make; it is a row the queue builder never
finished. The names show the class is mixed and answerable elsewhere — BUREAU OF
INDIAN EDUCATION ($499.8M) is a federal agency, FLORIDA DEPARTMENT OF CHILDREN
AND FAMILIES and NEW YORK STATE THRUWAY AUTHORITY are state bodies, while
TOHAJIILEE COMMUNITY SCHOOL BOARD OF EDUCATION and YELLOWHAWK TRIBAL HEALTH
CENTER are plainly tribal institutions. Every one now carries an
`attribution_status` in `federal_funding_transactions.csv`, which is where the
answer lives. Closed as a defect; **re-derive from the live table, do not
re-ask.**

---

## 16.7 · 16.8 · 16.9 · 16.10 — the 2026-09-01 dispositions, now written onto the rows

15,162 rows across four files. Each file's applied distribution **reproduces
int-3's exactly** — that equality is the check, and it is asserted in the run.

| file | rows | applied distribution |
|---|---:|---|
| `earmark_unresolved_2026-08-07.csv` | 6,796 | FLOOR 5,111 · REFUSE 939 · DEFECT 637 · HOLD 109 |
| `subaward_api_unresolved_2026-08-28.csv` | 6,094 | FLOOR 6,000 · ACCEPT 57 · REFUSE 19 · HOLD 18 |
| `entity_key_tierB_promotion_queue_2026-08-06.csv` | 1,223 | REFUSE 552 · AFFIRM_TIER_B 484 · HOLD 187 — **zero promotions to tier A** |
| `nagpra_alias_proposals.csv` | 1,049 | REFUSE 670 · ACCEPT 211 · HOLD 168 — rule 10, three independent notices |

**16.7 is worth restating because it is counter-intuitive: the correct number of
tier B → tier A promotions is ZERO.** Tier A is an *identifier* grade and not
one of the 1,223 carries an identifier. Affirming 484 of them at tier B is not a
failure to promote; it is the right home for an exact name span with a tribal
designator and no identifier behind it.

### The join defect this pass committed, and how it was caught

The first run joined the earmark dispositions on `recipient_name` and left
**477 rows unruled — exactly the 477 whose recipient cell is empty in the
source.** The dispositions carried a unique `earmark_id` the whole time. A
second run joined subawards on the bare name and collided 362 rows onto a
sibling's disposition. **A blank or collided join key is this repo's signature
defect and it caught this script twice in one hour.** The fix is in the code: the
joiner now tries several candidate keys, including composites, reports *which*
one it used, holds any row whose key carries more than one disposition rather
than guessing, and refuses to write a file that would look ruled and not be.

---

## 16.5 — OSHA. Ruled 2026-09-01; the file the queue names never heard about it

- `employment_osha_unmatched_2026-08-07.csv` — **711 of 711 rows now carry the
  ruling**: 47 keyed to a tribe, 664 an explicit coverage FLOOR.
- `osha_gambling_unresolved_2026-08-26.csv` — 4,560 rows: **PROMOTE 79 · HOLD 81
  · REFUSE 2,551 · FLOOR 1,849.** The 2,551 already carried a blocking verdict
  before the file ever reached the queue, which is why the "4,560 open" headline
  was 56% stale.

**FLOOR is the expected majority outcome here and must not be read as a miss.**
NAICS 7132xx and 7211xx are the gambling industry *as a whole* and most of it is
not tribal.

---

## Item C — a UEI on a firm named after a person. The owner's ruling, APPLIED

> *"If a site is publicly accessible it is part of the public domain. If they
> have their names, that's fine — it's not PII, it's not Social Security
> numbers. The firm is named after the owner; it's the name of the firm, and of
> course we're going to include that."*

Applied as three lines:

1. **The firm name ships.** A firm's legal name is the firm's name.
2. **CAGE and UEI ship.** They are public federal identifiers. **607 rows** in
   `native_business_contract_links.csv` and **33** in
   `native_business_identifier_crosswalk.csv` moved from
   `WITHHOLD_PENDING_RULING` to `PUBLISH`. That includes the 327 rows that were
   failing closed on `business_name_is_person_name = -1` (unknown) — the ruling
   removes the reason for failing closed, because the person-name status no
   longer gates the identifier.
3. **D-U-N-S is internal only.** The 4 DUNS rows are now
   `gate=INTERNAL_ONLY_PROPRIETARY`. This is **not** a publication judgement
   about those firms — it is D&B's licence. `START_HERE.md` LICENSING: D&B Open
   Data may not be disseminated in bulk.

What still never ships is unchanged: a natural person's data held apart from
their public role — home address, personal email or phone, DOB, SSN/TIN.

---

## Items A and B — the business block, adjudicated OFFLINE on the owner's own ladder

**No browser was opened.** The two signals that settled these were already on
disk: `prime_contracts.csv` for rung 1 (the address, and the *place of
performance*) and `fpds_uei_edges.csv` for **ENTITY_MATCH_RULES rule 11's
declared parent UEI** — an identifier the registrant filed about itself, which
beats every name method.

**12 of the 16 A/B holds are now settled: 8 ACCEPT, 5 REFUSE, 1 SPLIT, 2 HOLD.**

### The one that mattered most — `Arctic Slope Technical Services, Inc.`

The queue called it "the biggest single item: 5 UEIs, the largest carrying
$12.0B". **The answer is not one UEI. The name is held by two different ANC
families, and the declared parents separate them cleanly:**

| UEI | city | declares as parent | observations |
|---|---|---|---:|
| `SGK5EGB9VQM8` | Beltsville MD | **ARCTIC SLOPE REGIONAL CORPORATION** | 3,290 |
| `JRCDHBZD87J1` | Huntsville AL | **ARCTIC SLOPE REGIONAL CORPORATION** | 14 |
| `EB42FC6C9N64` | Albuquerque NM *(trades as SIVUNIQ, INC.)* | **NANA REGIONAL CORPORATION** | 539 |
| `WWJXZJT6VKK9` | Anchorage AK | **NANA REGIONAL CORPORATION** | 24 |
| `JW45GQBY26N3` | Lakewood CO | **NANA REGIONAL CORPORATION** | 10 |

The directory row is certified by Arctic Slope Regional Corporation, so it takes
the **two ASRC-parented UEIs only**. The three NANA-parented UEIs must not be
keyed to ASRC. A naive one-name-one-UEI merge here was the most expensive wrong
attribution available anywhere in the crosswalk.

### The other rulings, in one line each

| proposal | ruling | why |
|---|---|---|
| All-Ways Excavating USA | **ACCEPT** `EL61DKNUMNC3` | declares `NJH6ZLRJGGA7` 385×; both Oregon, as is Grand Ronde. One firm, two registrations |
| RJS Construction | **ACCEPT** `CNK9KG2BZHV7` | the other two declare it 98× and 166×; all above rule 11's floor |
| White Shield | **ACCEPT** `L3J8NHGQEJX4` | the sibling declares it only **10×**, *below* rule 11's floor, so the thin edge does not fold it in |
| Corporate Image dba Eagle Wing | **REFUSE** | Paola KS vs Avon IN, no parent edge, neither in Oklahoma. Rung 6 |
| Firelake Construction | **ACCEPT** `VNKJEMRCA424` | declared 299×. **Caution: "FireLake" is the Citizen Potawatomi brand and the certifier here is Cherokee — the identifier is settled, the nation is not** |
| Tel-Star Technologies | **ACCEPT** `QCACMBNDEDH8` | **rung 1 alone**: Tulsa, Oklahoma — Cherokee Nation's own state |
| Wells Technology | **ACCEPT** `V16EE96VFE36` | all four declare it (773 / 115 / 2×). But the firm is Bemidji **Minnesota** and the certifier is the Cherokee Nation — that is a `vendor_relationship`, **not ownership** |
| KFowler Construction | **ACCEPT** `V9YMXJT64BQ1` | **the state "conflict" is not one** — see below |
| NTUA Wireless | **ACCEPT** `GA1QJMK13V85` | Atlanta is a mailing address; **place of performance is Arizona on 12 of 13 rows** |
| Arrowhead Contractors | **REFUSE** | Cherokee NC vs Simpson **Louisiana**, performing in LA on all 19 rows |
| The Satellite Guy | **REFUSE** | Anchorage AK vs Honolulu **Hawaii**, 11 of 13 performed in HI |
| Blue Star Integrative Studio | **REFUSE** | Tulsa OK vs **Dowagiac Michigan** — the seat of the *Pokagon Band of Potawatomi*, a different nation |
| Comanche Construction | **REFUSE** | Purcell OK vs Montgomery **Alabama**. An Oklahoma nation's name on an Alabama firm |
| Eastern Shawnee Professional Services | **HOLD**, with a correction | see below |
| Kaiva Services | **HOLD** | recipient Ivins **Utah**, but performance is Oklahoma on the plurality. One CAGE lookup from settled |

### Two findings from this block worth more than the rulings

**1. A NEW RULE: a state-equality gate is the wrong shape for a nation whose
territory crosses state lines.** `KFowler Construction` was refused on
`state_conflict: directory=AZ, federal=NM`. **The Navajo Nation is a tri-state
nation — Arizona, New Mexico and Utah — so an AZ/NM disagreement is agreement at
the level that matters.** This is the first measured instance of a state gate
costing Cedar a correct link, and the same shape will recur wherever a nation's
service area crosses a border. Proposed as **ENTITY_MATCH_RULES rule 16** and
handed to that file's owner.

**2. The directory's certifier and the firm's own name can disagree, and the
name is usually right.** `Eastern Shawnee Professional Services, LLC` is listed
as certified by the **Muscogee (Creek) Nation**, with directory city
**Wyandotte, Oklahoma** — which is the seat of the **Eastern Shawnee Tribe of
Oklahoma**, not of the Muscogee. Held, with the likely affiliation flagged. **Do
not key it to Muscogee on this record.**

### Item A — 59 tier-C/X rows: the DOLLAR-BAND recommendation is REFUSED

The queue recommended ruling this class by dollar band — accept the 30 under
$250K because an error there is cheap.

**That is refused, and deliberately. A dollar band measures the COST of being
wrong, not the EVIDENCE for being right.** The house rule is that missing
coverage is expandable and a wrong attribution is not. Ruling 30 links in on the
ground that they are small would put 30 unevidenced attributions into a shipped
table with no way to tell them apart afterwards, and START_HERE's standing rule
1 is that a laundered tier can never be un-laundered.

All 59 are held at their current tier as `HOLD_PENDING_GEOGRAPHY`. The route
that settles them is one `cage.dla.mil` lookup each, then the registered address
against the certifying nation's service area — and the reason the 12 A/B holds
above could be settled *without* a browser while these cannot is precise: **they
had a declared parent UEI and these do not.**

---

## 10f — `anc_ceiling_roster.csv`. Labelled, nothing deleted

The mandate is explicit: flag, never delete. Applied as four new columns on all
196 rows.

- **4 rows are `SCRAPER_ARTEFACT`** — a strapline, two headings and the page
  title, scraped from `https://ancsa.lbblawyers.com/native-corporations.htm`.
  `row_is_a_corporation = N`. They falsify the table's declared grain, so the
  basis says **exclude them from any per-ANC denominator**.
- **1 row is `DUPLICATE_OF_THIRTEENTH_REGIONAL`**; the other is
  `CANONICAL_THIRTEENTH_REGIONAL`. Count the canonical one only.
- **191 rows are `CORPORATION`.**

A deleted row asserts nothing; a labelled row says what was refused and why, and
can be reversed. **The mint of The Thirteenth Regional Corporation into the spine
is proposed, not done** — the spine belongs to another workstream, it holds 12
`ANRC` handles and this is not among them, and 0 rows in
`ancsa_filings_index.csv` depend on it, so the mint is low-risk and can wait.

---

## The items decided as POLICY, without touching a row

### 16.4 — does a text mention make it that entity's comment? **NO. Confirmed and closed.**

Already ruled by int-3 and **already implemented**:
`regulations_gov_entity_coverage.csv` carries `text_mention_rows`, so the
information ships as a coverage measure while `regulations_gov_comments.csv`
keeps its 172-row title-match universe. The unit of analysis is *the tribe
speaking*; a comment criticising a nation mentions it exactly as loudly as one
the nation filed. No further work — the item is closed, not pending.

### 10e — nonprofit → spine links: **option 3. Mint the class, populate it only from RULED rows.**

Recorded as a decision, not executed: minting is the spine owner's act.

- **Not option 1** (mint all ~11,300). 4,362 candidates exist mechanically
  because every unkeyed `tribe_id_token_match` resolves to a spine handle — and
  of the candidates where a website could be read, **434 were CONTRADICTED by
  the organisation's own site and 6 corroborated.** A 72:1 refutation rate is
  not a linking opportunity. Importing it would swamp 1,555 governmental
  entities 8:1 with place-name false positives, and standing rule 1 says a
  laundered tier can never be un-laundered.
- **Not option 2** (mint nothing). The bridge is 28 rows, so the nonprofit
  economy would stay outside the entity layer permanently.
- **Option 3.** Create the class so the dataset has somewhere to key, and
  populate it *only* from ruled rows: the 89 promotions in
  `NONPROFIT_CLASSIFICATION_RESEARCH_LOG.md`, the 4 `native_entity` rows shard I
  evidenced from the organisations' own pages, the **51 `filing_req_cd = 14`
  governmental instrumentalities** (San Carlos Apache College, Seneca Nation
  Library, Kickapoo Nation School, Quileute Tribal School — the densest
  concentration of genuine tribal institutions in the dataset), and whatever
  shard J's mission-text pass promotes. Everything else stays a candidate in
  staging, keyed by `inclusion_basis` under ADR-013.

### 16.3, 16.1, 16.2 — confirmed as already ruled, no re-litigation

Tier C is a hard ceiling on a SAM self-certification; the identifier-graph
doctrine is three lines and disposes of 90,193 nodes at line 3; the
adjudication-hub method is tier B with name-exact **and** state agreement, and
`168_resource_revenue_ceiling`'s 5 rows are the fixture to run first.

---

## WHAT GENUINELY NEEDS THE OWNER — five things, and four of them are one sentence

Everything else in the 91-item queue is now ruled, applied, or handed to a named
workstream.

1. **16.11 — the 62-tribe vendor-list consent question.** All 62 rows
   `publishable = N`, `consent_status = UNRESOLVED`; 8 `TERMS_STATED_RESTRICTIVE`,
   2 `ROBOTS_DISALLOW`. **This is not a method question and no agent should
   decide it.** It is about Cedar's relationship with the nations whose lists
   these are — the one failure mode that damages this project's standing rather
   than its accuracy. Standing recommendation unchanged: publish the *verdict*
   and the *URL* (facts about a public page); publish no harvested contents
   without written consent. Asking is the route back in.

2. ~~**The Native Village of Eyak is not in the spine, and $583M turns on it.**~~
   **CLOSED 2026-09-02.** The Native Village of Eyak **is in the spine** - `CE-0004H-T9`, `Eyak`, `Federally recognized Alaska Native Village` - so any document still saying it is not is stale, and any decision still queued on that gap is answered. Copper River in `prime_contracts.csv`: **4276 rows, $1,508,042,187.53**, of which **4272 carry `tribe_id = AKNF-NVEYAK-00-CHGCCO-CHGCMT`** by `attribution_method` = `ruling_applied` 4272, `unattributed` 4. **The ruling landed on the row that asked for it** - which is the whole point: a decision recorded only in a sibling file is a decision that gets asked again.
   Kluti Kaah / Copper River Information Technology already carries a tier-X
   negative ruling naming Eyak as the true owner. Cedar cannot record the
   correct answer because the entity does not exist in the register. **Mint it,
   or accept that $583M stays unattributable.** This is an entity-identity
   question, which is the one class the owner reserved.

3. **NEST-1, the Ho-Chunk ledger rows.** Your own ruling already answers it
   ("Ho-Chunk means a sub-hub… the hub is Winnebago Tribe") and the integrator
   applied it to `prime_contracts.csv` on 2026-09-02 — 21 rows moved, with
   `recipient_city_name = WINNEBAGO` asserted as a precondition. **Still open:
   the ledger rows themselves and the tier-A `Ho-Chunk Nation` CAGE `3VFL3` row
   keyed to Winnebago, which looks like the same collision inverted.** The
   ledger is the integrator's file and DQC did not touch it. Rung 1 settles it:
   Ho-Chunk, Inc. is Winnebago, Nebraska; the Ho-Chunk Nation is Black River
   Falls, Wisconsin.

4. **Two firms one CAGE lookup from settled** — `Kaiva Services` (recipient
   Ivins UT, performance Oklahoma on the plurality) and `Eastern Shawnee
   Professional Services` (Mission KS; the name says Eastern Shawnee, the
   directory says Muscogee). Your `cage.dla.mil` spiderweb, last hop tribe-side.
   Both proposals carry the UEI and the expected answer.

5. **Item A's 59 rows**, if you want them keyed at all — 59 CAGE lookups, or
   leave them as a stated floor. Cedar loses nothing by leaving them; it loses
   correctness by guessing them.

---

## HANDOVERS — named, because nine workstreams are live and none of these files is DQC's

| what | to whom | why |
|---|---|---|
| **Rule 16 — a state gate is wrong for a multi-state nation** (Navajo AZ/NM/UT) | owner of `docs/ENTITY_MATCH_RULES.md` | a general rule, measured on `KFowler Construction`; belongs numbered beside rules 7–15 |
| **211 accepted NAGPRA aliases** (3+ independent notices) | owner of `data/spine/entity_aliases.csv` | an alias is an identity assertion; writing it is a spine act. And **12c is unresolved: 104 `alias_type='brand'` rows are single English words** (`cultural` → Southern Ute, `indigenous` → Delaware Nation) and any matcher reading that layer will key half a corpus |
| **57 ACCEPT subaward parties + 8 ACCEPT / 1 SPLIT business UEIs** | integrator (`cedar_identifier_ledger_final.csv`) | a disposition is not a repoint |
| **The Thirteenth Regional Corporation** — mint | spine owner | ANCSA regional, 0 dependent rows, low risk |
| **95 `tdhe_not_on_entity_spine` + 46 `no_spine_match`** from `admin_region_unresolved` | spine owner | a mint candidate list, already measured |
| **715 gaming property triage rows + 4 facility/capacity files** | gaming workstream | coverage states, not entity questions; the Casino City rows are read-for-QA only and never publish |
| **71 `FA-NTIA-####` backfill rows** | funding workstream | `ON_DISK_NOT_PROMOTED` — a join, not a fetch |
| **63 `unreconciled_entities` rows carrying a `cedar_uid`** | spine owner | "BLOCKING a dataset", no question text |
| **10a — the hardcoded `412`** in `code/24_generate_dataset_docs.py` ~line 506 | REGEN workstream (ADR-017) | it is a string literal, the live figure is **697**, and a hardcoded count in a maintenance doc cannot be wrong loudly — only quietly |
| **The `503` loose-path shape rule (12e)** | owner of `code/503_identity.py` | `UMATILLA ELECTRIC COOPERATIVE` still resolves to `TRBF-UMATLL-00` today. 66 measured contradictions over 25 entities. Recommendation stands: let the organisation's own 990 beat the name match |

---

## What this pass wrote

| file | change |
|---|---|
| `review/MASTER_QUEUE_2026-08-07.csv` | 6,559 rows ruled; 5 columns added; $82.06B conserved |
| `review/earmark_unresolved_2026-08-07.csv` | 6,796 ruled; $751.36M conserved |
| `review/subaward_api_unresolved_2026-08-28.csv` | 6,094 ruled; $535.18B conserved |
| `review/entity_key_tierB_promotion_queue_2026-08-06.csv` | 1,223 ruled |
| `review/nagpra_alias_proposals.csv` | 1,049 ruled |
| `review/employment_osha_unmatched_2026-08-07.csv` | 711 ruled |
| `review/osha_gambling_unresolved_2026-08-26.csv` | 4,560 ruled |
| `review/native_business_identifier_proposals_2026-09-02.csv` | 75 ruled |
| `data/clean/native_business_contract_links.csv` | 607 rows released to PUBLISH |
| `data/clean/native_business_identifier_crosswalk.csv` | 33 released, 4 DUNS held internal |
| `data/clean/anc_ceiling_roster.csv` | 196 rows labelled, 0 deleted |
| `data/staging/decision_queue_1103/` | per-row dispositions, measure summary, apply result |

Every one has a `.bak_2026-09-02_pre_1103_decision_queue_clearance` beside it.

**27,067 queue rows carry a ruling they did not carry this morning**
(6,559 + 6,796 + 6,094 + 1,223 + 1,049 + 711 + 4,560 + 75), plus 640 publish
gates released, 4 held internal, and 196 roster rows labelled.

*One small stale figure, corrected while applying it: the queue's item C says
**35** crosswalk rows sit at `WITHHOLD_PENDING_RULING`. The file holds **33**.
The links table's 607 is right.*
