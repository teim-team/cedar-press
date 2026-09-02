# The individually Native-owned business class — design proposal

*Written 2026-08-26 from the SAM FY2000–2007 backfill (script
`code/163_load_sam_contract_awards.py`). **This is a proposal. No spine rows were
created.** A concurrent agent is appending NHOs to the spine and separately
assessing this class; this document is the coordination surface, not the code.*

**Status: AWAITING OWNER RULING.** Nothing below is settled. Three things need
Elijah's decision and are marked **[RULE NEEDED]**.

---

## Why this class exists, and what already exists for it

Elijah, 2026-08-07, ruling on Hidden Water Inc:

> *"individual Native American owned — to the extent we identify individual
> native owned businesses might as well add them as a category, and if people
> want to be added gives them a centralized source to do so."*

That ruling is already in `AGENTS.md`. What has been built against it since:

| artefact | rows | what it is |
|---|---:|---|
| `data/clean/individual_native_prior_rulings.csv` | **45** | Elijah's per-UEI rulings, extracted from `hci_analysis.do`. `ruling_class = INDIVIDUAL_NATIVE`. **These are tier A already** — `elijah_ruling` is in `RULED_METHODS`. |
| `data/clean/individual_native_verification_candidates.csv` (script 165) | **305** | Unattributed high-obligation UEIs carrying a SAM self-certification, staged for verification. 11 already carry a prior ruling. $36.02B of obligations sits on the candidate set — **that figure is the size of the QUESTION, not of the class.** |
| `data/spine/cedar_entity_spine.csv` | **0** | The spine has no class for them. That is the gap. |

**The spine has 1,310 entities in 16 classes and not one of them can hold these
firms.** Putting an individually Native-owned firm into any existing class is
worse than leaving it out: `Federally recognized tribe` is false, and any tribal
class creates a roll-up edge that moves the firm's dollars onto a tribal
government that does not own it. That is the containment defect with a
respectable-looking label on it.

---

## 1. The class, named

    entity_class = "Individually Native-owned business"

**[RULE NEEDED #1 — the ID prefix.** The spine's existing prefixes are
grandfathered four-character strings (`TRBF`, `ANVC`, `NHO`, `UIO`, `CDFI`,
`BIE`, `TCU`…). This class needs one, registered in `code/cedar_ids.py::PREFIXES`
**before** a single row is minted. Proposed: **`INDV`**, giving
`INDV-XXXXXX-00`. The alternative is the minting service's `CEDAR-ENT-000123`,
which is uglier and better — see §5, where the surrogate ID turns out to be a
privacy control, not a cosmetic choice.**]**

`cedar_ids.py`'s own rule applies and is load-bearing here: **type lives in a
column, never inferred from the prefix.** A firm ruled individually-owned today
can be acquired by a tribe tomorrow; the ID must survive that.

---

## 2. What the class must CARRY

The spine's 33 existing columns, plus these. Every one of them exists because
omitting it produces a specific known failure.

### 2a. The three fields that keep tribal attribution correct

| field | value | why |
|---|---|---|
| `parent_native_entity` | **permanently NULL** | There is no tribal owner. Inventing one is the containment defect (AGENTS.md, five failures in one day). |
| `ultimate_parent_entity_id` | **the entity's own ID** | Never a tribe, never an ANC, never an NHO. |
| `ownership_basis` | `INDIVIDUAL_NATIVE_OWNER_NOT_A_TRIBAL_ENTITY` | Says the blank is a *ruling*, not unfinished research — the same distinction the 56 federally operated BIE schools needed. |

### 2b. The affiliation field, and the trap inside it

| field | example |
|---|---|
| `owner_tribal_affiliation_named` | `Cherokee Nation` |
| `owner_tribal_affiliation_source` | URL + verbatim quote |
| `owner_tribal_affiliation_basis` | `SELF_STATED` / `ENROLLMENT_DOCUMENTED` / `NOT_CHECKED` |

**This is an attribute of a PERSON. It is not an edge of the firm, and it must
never be keyed to a `tribe_id`.**

Thirty-eight of Elijah's 45 prior rulings read *"owned by individual Cherokees."*
The temptation to write `tribe_id = TRBF-CHRKEE-00` on those rows is enormous and
it is wrong twice over: the Cherokee Nation does not own the firm, and the
affiliation string "Cherokee" does not even resolve — there are three federally
recognised Cherokee tribes and a long tail of unrecognised groups using the name.
`core()` already proved that folding a distinguishing word destroys identity
(National Education Association → National Indian Education Association).

**[RULE NEEDED #2 — may `owner_tribal_affiliation_named` hold a free-text string
that resolves to no spine entity?** Recommendation: **yes**, and it stays
free-text forever. Resolving it is what would break it.**]**

If a relationship row is ever wanted, it must use a NEW type added to
`cedar_domain.NEVER_OWNERSHIP`:

    owner_self_identifies_with     # person -> tribe. Carries NO money. Ever.

It must not go in `CORPORATE_RELATIONSHIPS` and must not appear in
`OWNERSHIP_BEARING`. $27.59B was once booked wrong on exactly this confusion
between an association and an ownership edge.

### 2c. The evidence fields

Per AGENTS.md: *"Evidence is the firm's own statement of Native ownership,
quoted verbatim with its URL."*

    native_ownership_evidence_type      SELF_STATEMENT | THIRD_PARTY | RULING | REGISTRY
    native_ownership_evidence_quote     verbatim, e.g. "Being Of Cherokee Indian descent..."
    native_ownership_evidence_url
    native_ownership_evidence_date      the FETCH date, not today
    native_ownership_evidence_n_legs    1 or 2

`native_ownership_evidence_date` is separate from `built_date` because of the
2026-08-06 withdrawal of three gaming rulings: **a 2026 page cannot testify about
a 2003 firm.** These SAM rows are FY2000–2007. A website read in 2026 establishes
ownership in 2026 and says nothing about who owned the firm when the contract was
signed. Every row therefore also carries:

    ownership_asserted_as_of            the date the evidence speaks to
    temporal_gap_years                  ownership_asserted_as_of - fiscal_year

### 2d. The privacy fields — see §5 for why they are not optional

    firm_legal_name_is_person           1 | 0 | UNKNOWN
    consent_status                      OPTED_IN | NOT_ASKED | DECLINED | WITHDRAWN
    consent_date
    consent_source
    publish_name                        1 only when consent_status = OPTED_IN
    publish_surrogate_id_only           1 by default

---

## 3. How it differs from a tribal or ANC entity

| | Tribal government / tribal enterprise | ANC / village corporation | NHO | **Individually Native-owned business** |
|---|---|---|---|---|
| **legal person** | sovereign government or its chartered arm | state-chartered corporation under ANCSA | non-profit under HI/federal law | an ordinary firm — LLC, S-corp, sole proprietorship |
| **owner** | a nation | ~13,000 shareholders by birthright | a community | **one private individual or a family** |
| **name is** | a matter of public record (Federal Register) | public corporate registration | public | **frequently a PERSON'S NAME** |
| **rolls up to** | its tribe | its ANCSA region *(as geography, not ownership)* | its NHO parent | **NOTHING. `bears_ownership()` has no edge to carry.** |
| **appears in tribal totals** | yes | separately, never summed with tribes | separately | **NEVER. It was never in them and every published tribal total stays unchanged.** |
| **status is** | adjudicated (federal recognition) | statutory (ANCSA) | organisational | **an assertion about a person's ancestry** |
| **who can correct the record** | the tribe | the corporation | the organisation | **the individual — and only they** |
| **counting it as tribal** | correct | wrong | wrong | **overstates tribal economic activity, which is the single easiest way to discredit this dataset** |

The last row is the reason the two SAM classes are held apart on every row of
`sam_prime_contracts_fy2000_2007.csv` and the reason `summary()` in script 163
emits **no combined total**.

The measured stakes, from AGENTS.md's first 15 rulings:

> tribally/ANC owned **7,329 rows / $2.76B** · individually Native-owned
> **14,029 rows / $0.98B**

The individual class is **larger by row count and smaller by dollars**. Summing
them would move both numbers in opposite directions from the truth.

---

## 4. How it interacts with the tier system

**The governing rule is already standing and it is not negotiable here: a tier is
INHERITED from the source row, never assigned by the consumer.** Only a method in
`RULED_METHODS` earns A.

| evidence | tier | may publish alone? |
|---|---|---|
| SAM socio-economic flag alone (`americanIndianOwned = YES`) | **C** | **no** |
| SAM flag + `awardeeBusinessTypeName` variant hit | **C** | **no** |
| Firm's own statement of Native ownership, verbatim + URL (`agent_research_one_leg`) | **B** | no |
| Firm statement + independent third party (`agent_research_two_leg`) | **A** | yes |
| Elijah ruling (`elijah_ruling`) — the 45 already held | **A** | yes |

### Why the SAM flag can never be better than C for THIS class

Three measurements, all from the extract that landed today:

1. **The flags do not distinguish the two classes at all.** `americanIndianOwned
   = YES` on **2,846 of 8,273** rows of the *TRIBAL* extract — rows that are
   tribal enterprises. Chugach, ASRC, Chickasaw Nation Industries. Reading
   `americanIndianOwned = YES` as "individually owned" would reclassify Alaska
   Native corporations as sole proprietors.
2. **The flags are internally inconsistent.** Goldbelt Raven LLC, an ANC
   subsidiary, certifies `alaskanNativeCorporationOwnedFirm = NO`,
   `triballyOwnedFirm = NO`, `americanIndianOwned = YES`. A firm's
   self-certification is not an adjudication.
3. **The business-type filter is a partial string match and it lets in entities
   with no Native attribute at all.** 87 rows / 11 UEIs / $710,492 of the TRIBAL
   extract are there because the business type **"HOUSING AUTHORITIES
   PUBLIC/TRIBAL"** contains the string **"TRIBAL"** — City of Wichita, City of
   Dodge, the Housing Authority of the City of Los Angeles, Scott Electric
   Company. They carry `include_in_native_universe = 0`.

**So the AMERICAN INDIAN and NATIVE AMERICAN extracts arriving tomorrow are a
candidate list, not a class.** Every row lands at tier C and stays there until
something a human ruled touches it.

### The `soleProprietorship` column: useless as a classifier, valuable as a tripwire

The task named
`awardDetails.awardeeData.awardeeBusinessTypes.businessOrOrganization.soleProprietorship`
as directly relevant. It is — but not in the direction it looks.

**Measured on the TRIBAL extract: 4 rows carry `soleProprietorship = YES`, and
all four are tribally owned.**

| firm | soleProprietorship | triballyOwnedFirm | ultimate parent |
|---|---|---|---|
| **CNI ADMINISTRATION SERVICES LLC** | **YES** | YES | **CHICKASAW NATION** |
| **CNI MANUFACTURING LLC** | **YES** | YES | INNOVATION ONE, LLC |
| ALL POINTS LOGISTICS, INC. | YES | YES | self |
| FIBER NET | YES | YES | self |

An **LLC** wholly owned by the **Chickasaw Nation**, coded
`organizationType = SOLE PROPRIETORSHIP`. The field is a registration artefact of
this vintage, and it errs in both directions: it is YES on tribal subsidiaries,
and it will be NO on the great majority of genuinely individually-owned firms,
which are LLCs and S-corps rather than sole proprietorships. **It cannot define
the class and must never be used to.**

What it *is* good for: **`soleProprietorship = YES` sets
`firm_legal_name_is_person = UNKNOWN` and forces the name through the privacy
gate**, whatever class the firm eventually lands in. A field that is a bad
classifier can still be a good alarm.

---

## 5. The privacy problem, stated squarely

> **Naming a private individual in a shipping dataset is a privacy exposure a
> tribal government's name is not.**

This is not a softer version of the D&B question. It is a **second, independent**
restriction that stacks on top of it, and it survives every answer to the D&B
question. If SAM's licence were lifted tomorrow, this section would be unchanged.

### The exposures are different in kind

Publishing *"The Chickasaw Nation owns Chickasaw Nation Industries"* discloses a
fact about a **sovereign government's** commercial activity. The Chickasaw Nation
is on the Federal Register list; its enterprises are a matter of public interest;
it has a press office.

Publishing *"Robert Ganje, of [address], is a Native American business owner who
received $X in federal contracts"* does three things at once, and only the first
is ordinary:

1. discloses **contract facts** — public, fine;
2. names a **private individual** and their home or business address;
3. asserts that individual's **race and ancestry**.

The third is the one with no analogue on the tribal side. Cedar Press is not in a
position to adjudicate anyone's Native identity, and the identification
literature this project already relies on is emphatic that self-identification is
unstable and contested. An assertion of Native ancestry attached to a named
private person, published at scale, is a claim we cannot stand behind about an
individual who never asked to be in the file.

### It is already concrete, not hypothetical

**In the TRIBAL extract — the *entity* class, where this problem was not supposed
to appear — 8 of 402 distinct UEIs carry a legal business name that is
unambiguously a person's name:**

    ROBYN NELSON · GANJE ROBERT · MENDIETA, RENATA N · FRANK ROSS
    TULLY GENEVIEVE · STANLEY NICHOLE · PAVELOVA EVA · COOPER GERALD

Every one of them carries a street address and ZIP in the same row. **The
AMERICAN INDIAN and NATIVE AMERICAN extracts land tomorrow and the share will be
far higher, because that is exactly what those variants select for.**

### What MAY publish

Everything that is a fact about a contract or about the segment, with no natural
person in it:

- **All contract facts** — PIID, modification number, date signed, fiscal year,
  obligated amount, NAICS, PSC, agency, office, set-aside, extent competed,
  place of performance.
- **Federal identifiers where the entity is a firm, not a person** — see the
  carve-out below.
- **The existence and size of the class.** Row counts, dollar totals, the fiscal
  year series, NAICS and agency distributions, the state distribution at a level
  that does not resolve to one firm. *"Individually Native-owned firms won $N in
  FY2005"* is exactly the kind of finding nobody has assembled, and it publishes.
- **Comparisons against the tribal class**, side by side, never summed.

### What MAY NOT publish — in bulk **or** singly, absent consent

- The firm's **legal business name**, `awardeeName`, or DBA name.
- The **owner's** name, wherever it appears.
- **Street, city, ZIP** — and, for a single-firm cell, state.
- **Any pairing of a named person with an assertion of Native identity.**
- **The UEI or CAGE, where `firm_legal_name_is_person` is 1 or UNKNOWN.** This is
  the carve-out and it is deliberate: SAM's own public entity search resolves a
  UEI to a name and an address. For an incorporated firm the UEI is an
  identifier; **for a sole proprietor it is a pointer to a person's front door.**
  Publishing it publishes the name by one hop.

**Consequence for the schema: the publishable individual-native table keys on a
Cedar-minted surrogate ID, and the surrogate ↔ UEI crosswalk stays internal.**
This is the real argument for `CEDAR-ENT-000123` over `INDV-GANJEROB-00` in
**[RULE NEEDED #1]** — a mnemonic slug built from a person's name *is* the
disclosure, minted right into the primary key of every downstream join.

### Small-cell suppression

Any published aggregate cell resolving to **fewer than 3 firms** is suppressed.
"Individually Native-owned firms in Wyoming, NAICS 236220, FY2004 — 1 firm,
$412,000" is a person's name written in a different alphabet. Report the
suppression (`value_suppressed_small_cell`), never silently drop the row — the
CGCC precedent in AGENTS.md is the model.

### The register, and why consent is the whole mechanism

Elijah's ruling includes the product idea:

> *"if people want to be added gives them a centralized source to do so."*

**Read it exactly as written: people ASK to be added.** That is opt-in, and it is
what makes the register publishable when the research file is not.

- Names publish **only** where `consent_status = OPTED_IN`, with a date and a
  recorded source.
- Consent is **per firm, revocable**, and `WITHDRAWN` removes the name from the
  next build. Consent to appear is not consent to appear forever.
- **Consent is never inferred from the firm's own website.** A firm writing
  *"Being Of Cherokee Indian descent…"* on its homepage has consented to that
  sentence being on its homepage. It has not consented to being enumerated,
  ranked by federal obligations, and distributed in a subscription dataset. That
  self-statement is our **evidence**; it is not their **permission**. Conflating
  the two is the fastest route from a good product to a complaint.
- The research file and the register are therefore **two different tables with
  two different publication rules**, built from one internal spine.

**[RULE NEEDED #3 — does the opt-in register ship at the $499 portal tier, the
$2,500 Grove tier, or free?** Recommendation: **free and public.** A register
only works if the firms it lists can see themselves in it, and a paywalled
opt-in register collects consent it cannot honour with visibility.**]**

---

## 6. What this proposal does NOT do

- **It creates no spine rows.** A concurrent agent is appending NHOs to
  `cedar_entity_spine.csv` and is separately assessing this class. Two agents
  appending entity rows to one file is how the Sequoyah/CDFI collision happened.
- **It changes no existing total.** Every tribal, ANC and NHO figure Cedar Press
  has published is unaffected — these firms were never in them.
- **It writes nothing to `cedar_identifier_ledger_final.csv`.**
- **It does not run** `01_build_entity_spine.py`, `09_import_rulings.py`,
  `41_build_codebooks.py` or `88_build_deals_taxonomy.py`.

## 7. The order of work, if this is approved

1. Register the prefix in `code/cedar_ids.py::PREFIXES` — **[RULE NEEDED #1]**.
2. Add `owner_self_identifies_with` to `cedar_domain.NEVER_OWNERSHIP`. Add
   nothing to `OWNERSHIP_BEARING`.
3. Seed from the **45 tier-A rulings**, not from the 305 candidates and not from
   the SAM flags. A ruled seed makes the first version of the class 100%
   defensible and small, which is the correct trade.
4. Promote candidates only on ruled or two-leg evidence, through
   `124_apply_rulings_in_place.py` — never `09_import_rulings.py`.
5. Set `firm_legal_name_is_person` on every row before any of it is queryable,
   not after.
6. Build the register as a **separate opt-in table**. Do not filter the research
   file into a register; build the register from consent.

---

## Appendix — coordination

| file | owner | do not |
|---|---|---|
| `data/clean/individual_native_prior_rulings.csv` | script 165 agent | rewrite |
| `data/clean/individual_native_verification_candidates.csv` | script 165 agent | rewrite |
| `data/spine/cedar_entity_spine.csv` | NHO agent, in progress | append concurrently |
| `data/clean/sam_prime_contracts_fy2000_2007.csv` | script 163 (this build) | — |
| `docs/INDIVIDUAL_NATIVE_CLASS_PROPOSAL.md` | this document | — |

Script 163 already carries the two class labels on every row and refuses to sum
them. When the AMERICAN INDIAN and NATIVE AMERICAN extracts land, the
`INDIVIDUAL_NATIVE_OWNED` rows appear in that file **as candidates at tier C**,
correctly separated and correctly restricted, with no spine row created and no
name published. That is the safe resting state until this proposal is ruled on.

---

# THE FEDERAL POPULATION ARRIVED. MEASURED 2026-08-26, ~20:30.

*Written by `code/358_measure_sam_individual_native_class_delta.py` against the
completed six-variant SAM load. The appendix above says the AMERICAN INDIAN and
NATIVE AMERICAN rows would appear **"as candidates at tier C, correctly
separated and correctly restricted, with no spine row created and no name
published."* That is exactly what happened, and the numbers are below.*

**Nothing here creates a spine row, writes to the ledger, or changes a total.
The class still holds 45 firms.**

## The delta

| | firms | obligation (INDIVIDUAL_NATIVE_OWNED rows only) |
|---|---:|---:|
| the class register, before | **45** | — |
| candidate firms in the two individual variants | **2,912** | **$22,789,700,023** |
| …already in the class (register or a non-X ledger row) | 17 | $242,194,333 |
| …**already bound to a tribe / ANC / NHO in the ledger** | **606** | **$15,721,934,154** |
| …**NEW to the register AND to the ledger** | **2,289** | **$6,825,571,535** (45,456 rows) |

The three rows sum to the class total exactly, which is the check that the
scoping is right.

### THE FINDING: 69% OF THIS CLASS'S SAM DOLLARS ARE NOT THIS CLASS'S MONEY

**$15.72 billion of the $22.79 billion sits on 606 UEIs the identifier ledger
already binds to a tribal government, an ANC, an NHO or another entity.** They
are in the individual class here only because the `NATIVE AMERICAN` business-type
query returned them and no entity variant did.

That is the single most important number in this measurement, because the
obvious reading of *"the INDIVIDUAL_NATIVE_OWNED class is $22.79B"* is wrong by a
factor of three, and it is wrong in the direction this project has already
identified as the one that discredits the dataset — **counting entity-owned
activity as individual activity**. Section 3's table above says the individual
class is *"larger by row count and smaller by dollars"* than the tribal class.
The raw SAM class column says the opposite. **The ledger is right and the
business-type query is not**, which is section 4's rule arriving with a price
tag: a SAM socio-economic flag is a self-certification and its ceiling is
**tier C**.

### The discovery, stated at the size it actually is

**2,289 firms, $6.83 billion, 45,456 transactions, unknown to both the 45-firm
register and the identifier ledger.** Every one is `spine_action =
UNRULED_CANDIDATE` at tier C. Against a class that today holds 45 firms carrying
$2.34B, that is a candidate population **51x larger by firm count** — and it is a
candidate population, not a class.

This is also the direct evidence for the class's own headline finding. These
firms are the ones flag-based discovery misses: the class's dollars are
**76.7% without any Native set-aside** against 57.2% project-wide, and a firm
that never takes a set-aside is invisible to every discovery route this project
had before this pull. *(The set-aside share reported by `358` is a different
metric — ANY set-aside, not a NATIVE one — and is deliberately named
`share_of_dollars_with_no_setaside_OF_ANY_KIND_pct` so the two cannot be
confused. The full set-aside-name distribution publishes per class, so any
definition can be applied to it rather than one being invented here.)*

## RULE NEEDED #1 IS NO LONGER HYPOTHETICAL — the surrogate is required

Section 5 argued for `CEDAR-ENT-000123` over `INDV-GANJEROB-00` on the grounds
that a mnemonic slug built from a person's name mints the disclosure into the
primary key. The measurement now forces the point:

| class | UEIs whose legal name **reads as a person's name** | of |
|---|---:|---:|
| INDIVIDUAL_NATIVE_OWNED | **740** | 2,912 (25.4%) |
| ENTITY_OWNED | **1,854** | 6,346 (29.2%) |

**2,594 firms, against the 8 that section 5 was written from.** A slug scheme
would have minted 2,594 private individuals' names into join keys.

And the carve-out bites exactly as predicted: **for all 2,594 the UEI is
withheld too**, because SAM's public entity search resolves it to the name and
address. `publish_name = 0`, `publish_uei = 0`, `consent_status = NOT_ASKED`,
`firm_legal_name_is_person = UNKNOWN` — carried per firm in
`review/sam_individual_native_candidates_<date>.csv`.

**The classifier is imported from `171_build_individual_native_verification.py`,
not re-implemented.** A second copy of a privacy classifier drifts, and a
drifted privacy classifier fails OPEN — the direction that costs a person.

## What publishes, and what does not

**Publishes:** `review/sam_class_distributions_PUBLISHABLE_<date>.csv` — per
class, by fiscal year, funding department, NAICS-2 and set-aside name. No name,
no address, no identifier. **143 cells published, 33 suppressed** at the
under-3-firms floor, and every suppressed cell keeps its label and reports
`value_suppressed_small_cell = 1` with the rule in words. That is the CGCC
precedent applied: report the suppression, never silently drop the row.

**Does not publish, in bulk or singly:** the per-firm file, any legal/DBA/owner
name, any address, any pairing of a named person with an assertion of Native
ancestry, and the UEI or CAGE of the 2,594. **There is deliberately no
surrogate-keyed per-firm publishable view** — a digest of a UEI is reversible by
enumerating SAM's own entity space, so a "de-identified" per-firm file would be a
disclosure with an extra step. Per-firm publication runs through the opt-in
register or not at all.

Absence remains `NO_CLAIM_FOUND`. **There is no `NOT_NATIVE` anywhere in this
measurement.**

## A NEW PROBLEM FOR THIS CLASS, AND IT NEEDS A RULING

`AMERICAN INDIAN` turned out to be a **strict subset of `INDIAN`** — all 52,714
of its rows — because the business type "American Indian Owned" also contains the
string "INDIAN". So `INDIAN`, an ENTITY variant, claims rows whose only
business-type evidence is an assertion about a **person**, and the merge rule
*"ENTITY_OWNED wins a contested transaction"* then moves them out of this class.

| what the ENTITY_OWNED assignment rests on | rows | UEIs | obligation |
|---|---:|---:|---:|
| a tribal / ANC / NHO / tribal-college ownership flag is YES | 7,474 | 285 | $1,365,604,584 |
| **NO ownership flag — assigned by the SUBSTRING alone** | **49,792** | **2,272** | **$4,448,849,761** |

**Those 49,792 transactions are candidates for THIS class that the merge rule
currently books as entity-owned, on no evidence.** They are staged unruled at
`review/sam_class_conflicts_<date>.csv` with `entity_claim_basis` naming which
situation each is in. **The merge rule was not changed** — that is an owner-level
decision about what the class means, not a loader detail — but it must not be
left to decide 49,792 rows by substring.

**[RULE NEEDED #4 — when an entity variant's ONLY claim on a transaction is the
`INDIAN` substring matching the business type "American Indian Owned", and no
tribal/ANC/NHO ownership flag is present, does the transaction belong to
ENTITY_OWNED or to INDIVIDUAL_NATIVE_OWNED?** Recommendation: **neither
automatically** — add a third value, `CLASS_UNDETERMINED`, rather than let a
substring decide $4.45B. The current behaviour books all of it as ENTITY_OWNED,
which is the safer of the two errors for tribal totals (it keeps money OUT of the
individual class) and the worse one for this class's completeness.**]**
