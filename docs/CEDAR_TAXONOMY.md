# CEDAR_TAXONOMY — every controlled vocabulary Cedar Press uses, in one place

*Consolidated 2026-08-26 by `code/374_build_cedar_taxonomy_export.py`. The
machine-readable half is **`docs/CEDAR_TAXONOMY.json`** — 15 layers, regenerated
from `code/` and `data/` on every run, never hand-typed. Reproduce with*

    py -3 code/374_build_cedar_taxonomy_export.py --check    # no write
    py -3 code/374_build_cedar_taxonomy_export.py

---

## WHY THIS FILE EXISTS

The owner asked for *"a taxonomy of our own with more data."*

**A taxonomy already exists.** It is spread across `cedar_domain.py`, the spine's
`entity_class` column, four registry CSVs, a staged tribal-certification layer,
the federal set-aside flags and the ANCSA statute — and **no single artefact
holds it**, so a subscriber cannot read it and the next agent cannot import it.
This file consolidates what is there, derives the one layer that was missing, and
names every place two vocabularies disagree.

**Nothing here invents a parallel scheme.** Where a value already exists in the
data, it is quoted verbatim, including its capitalisation, because a class name
retyped with a different case is a guard that silently fails open — and this
document records four scripts where that already happened.

---

## THE GOVERNING PRINCIPLE — DESCRIPTIVE, NEVER PRESCRIPTIVE

> **Cedar Press builds the fact. It never builds the verdict.**

Cedar Press may publish *"Colville's Title 10 certification does not require an
ownership percentage — the list carries firms at `INDIAN PERCENT OWNED = 0` with
`CERTIFIED TITLE 10 = Yes`."* That is a retrieved fact with a URL and a capture
date.

Cedar Press may **not** publish *"…therefore that firm is not really
Native-owned."* **A tribe's determination of who counts as a Native-owned
business is an exercise of sovereignty**, and adjudicating it is not ours to do.
The taxonomy exists precisely so a subscriber can apply **their own** threshold,
which is why the owner asked for the rules to be published alongside the lists.

This is the same discipline as `docs/LOBBYING_EXPANSION_RECONCILIATION.md`
refusing to author `position_on_native_issue`, and it is enforced rather than
asserted: `374`'s `FORBIDDEN_TAXONOMY_KEYS` refuses to write any layer carrying a
field such as `native_enough`, `counts_as_native`, `meets_threshold` or
`our_determination`, and `main()` walks the exported dict keys and aborts.

The same refusal already lives in `cedar_domain.FORBIDDEN_ABSENCE_VALUES` —
there is no `NOT_NATIVE` value in this schema and there never will be one.

---

## LAYER 0 — THE THREE RULES EVERY OTHER LAYER DEPENDS ON

**1. A tier is INHERITED from the source row, never assigned by the consumer.**
The exactness of the KEY says nothing about the correctness of the LINK. Class
membership confers no tier: being a `Federally recognized tribe` does not make a
link to that tribe tier A.

**2. A RULED method says a HUMAN DECIDED. It never says the answer was YES.**
All 317 `elijah_ruling` EIN rows in the ledger are tier X — negative rulings.
`attribution_method` says WHO decided; `confidence_tier` says WHAT was decided.
Read the SIGN before you inherit the AUTHORITY.

**3. A consumer that COPIES a tier owes the source a re-read.** An inherited tier
is correct only as of the moment it was copied, and a stale copy is
indistinguishable from a correct one.

---

# PART I — ENTITY CLASSES

`data/spine/cedar_entity_spine.csv`, **1,534 rows, 17 classes, no blanks and no
spelling variants inside the file.** Counts below are recomputed at build time.

| n | `entity_class` | prefix(es) | in `cedar_domain`? | `verification_route` filled |
|---:|---|---|---|---:|
| 349 | `Federally recognized tribe` | TRBF, AKNF×1 | — | 0 |
| 228 | `Federally recognized Alaska Native Village` | AKNF | **yes** | 0 |
| 210 | `Native Hawaiian Organization` | NHO | — | 210 |
| 185 | `BIE School` | BIE | — | 0 |
| 173 | `Alaska Native Village Corporation` | ANVC | **yes** | 0 |
| 64 | `State-recognized tribe` | TRBS | — | 0 |
| 64 | `Native Community Development Financial Institution` | CDFI | — | 0 |
| 55 | `Intertribal Organization` | ITO | — | 0 |
| 45 | `Individually Native-owned business` | CEDAR | **yes** | 45 |
| 43 | `Urban Indian Organization` | UIO | — | 0 |
| 37 | `Tribal College or University` | TCU | — | 0 |
| 29 | `Native Financial Institution` | CDFI | — | 0 |
| 22 | `Federal-level constituency entity` | CNSF | — | 0 |
| 12 | `Alaska Native Regional Corporation` | ANRC | **yes** | 0 |
| 9 | `Federal-level self-governance consortium` | SGVF | — | 0 |
| 6 | `ANCSA Group Corporation` | ANVC | **yes** | 0 |
| 3 | `State-level constituency entity` | CNSS | — | 0 |

**Two things this table says that a reader will otherwise get wrong.**

- **`Federally recognized tribe` is NOT the federally recognized universe.** 349
  here plus 228 Alaska Native villages is **577**. The split is geographic, not
  legal. Quoting 349 as "the federally recognized tribes" understates it by 40%.
  The one AKNF-prefixed row in this class is **Tlingit & Haida**, a regional
  tribal government rather than a village — a documented exception, not a defect.
- **THE PREFIX DOES NOT IDENTIFY THE CLASS.** `ANVC` carries both village and
  group corporations; `CDFI` carries both Native CDFIs and Native Financial
  Institutions. `cedar_ids.py`'s own rule is load-bearing here: *type lives in a
  column and is read from the registry; it is never inferred from the prefix*,
  because a prefix is history and an entity's class can change. Two scripts
  nonetheless hard-code a 1:1 prefix→class map — see Gap 5.

### The full definition of each class

Definition, what it is **not**, how membership is evidenced, tier implication and
enforcement site for all 17 classes are carried in
**`docs/CEDAR_TAXONOMY.json` → `layers.entity_class`**, one object per class, so
the product can render them and a future agent can import them. The five that
carry the most load are restated here because they are the five most often got
wrong.

**`Federally recognized Alaska Native Village`** — the village GOVERNMENT. It may
own an enterprise directly (ANCSA ruling **rule 3**), and then that enterprise is
an ordinary tribal enterprise. It is **NOT** an ANCSA corporation in either
direction: a village government never owns an ANC (**rule 2**) and an ANC never
owns the village government (**rule 4**). The two share a name and a place **by
statute**, so a shared name is not weak evidence of one owner — *it is no
evidence at all*. Rule 3 is an exception that must be EVIDENCED per identifier,
never assumed from a name: the Native Village of Eyak carries **both** shapes at
once, Copper River Family of Companies under rule 3 and EyakTek under rule 1.

**`Alaska Native Village Corporation`** — organised under ANCSA §8, 43 U.S.C.
1607. **NOT** a subsidiary of its regional corporation: rule 5, two corporations
with an overlapping shareholder base. **And today, not only village
corporations** — the four ANCSA **Urban** Corporations sit in this class because
Cedar has no class for them. See Gap 6.

**`Individually Native-owned business`** — an ordinary firm whose owner is an
individual Native person. **NOT** a false positive and **NOT** excluded from the
product; it simply never rolls up. `parent_native_entity` is permanently NULL and
**that blank is a RULING**, the same distinction the 56 federally operated BIE
schools needed. **Read the ruling text before you read the ruling:** five of the
45 read *"Not a Native entity — individually Native-owned firm"*, which refuses
the TRIBAL LINK and AFFIRMS Native ownership. Read literally as "not Native" it
inverts the owner's meaning, and it already has — CAGE `9DVK5` sits in the ledger
at tier X bound to a tribe that does not own it. Ask
`is_tribal_link_refusal_not_native_refusal()`; never match the words.
`elijah_ruling` makes these tier A **as attributions**; it does not make them
publishable **as names** — `may_publish_individual_native_field()` withholds
every name, address and, for a firm whose legal name is a person's, the UEI and
CAGE, absent recorded `OPTED_IN` consent.

**`BIE School`** — **NOT tribally owned by default.** 56 of 185 are FEDERALLY
operated and their blank parent is a ruling. `Navajo_Operation` in BIE data is an
administrative grouping, not ownership; trusting it books 35 schools to the
Navajo Nation.

**`Tribal College or University`** — **NOT its chartering tribe.** The edge
written is `chartered_by`, which is not in `OWNERSHIP_BEARING`: a tribe
chartering a college does not own it and the college's federal dollars are not
the tribe's. Before this class existed, containment resolved *Bay Mills Community
College* onto the Bay Mills Indian Community and *United Tribes Technical
College* onto United Auburn Rancheria.

---

# PART II — THE VOCABULARIES THAT LIVE IN `cedar_domain.py`

All imported by `374` rather than transcribed, so this section cannot drift from
the module.

## Tier — what may be done with a record

| value | meaning | publishes |
|---|---|---|
| `A` | Verified or human-ruled | **yes** |
| `B` | Visible internally and to analysis | never |
| `C` | Unattributed; in the corpus, not linked | never |
| `X` | Ruled out. Never resurfaces | never |

## Attribution method — WHO made the link

| family | members | reading |
|---|---|---|
| **RULED** | `hand` · `bgov_manual` · `elijah_ruling` · `elijah_ruling_redirect` · `ruling` · `web_verified` | a HUMAN decided. **Not** that the answer was yes |
| **TWO_LEG** | `agent_research_two_leg` | two independent legs → tier A |
| **ALGORITHMIC** | `need_v6` · `cluster_v3` · `subsidiary_lookup` · `sam_namematch_2026_05_06` · `cross_dataset_propagation` · `agent_research_one_leg` · `unmatched` | machine-proposed; never tier A alone |

**Measured accuracy against the owner's own rulings — a real calibration, and a
rare one:** `need_v6` **6.5%**, `cluster_v3` **97.7%**. The algorithmic methods
are not interchangeable with each other and must never be pooled into one
"automated" bucket.

## Identifier type

`UEI` · `CAGE` · `EIN` · `DUNS` · `SAM` · `IRS` · `STATE_CORP` · `TRIBAL_CHARTER`
· `SEC` · `LDA_REGISTRANT` · `LDA_CLIENT` · `SOURCE_NATIVE` · `CEDAR_INTERNAL`.

**`DUNS` is D&B-licensed and never publishes at any tier** — the publish-path
serialiser asserts on it. `CEDAR_INTERNAL` is never presented as an official
identifier.

## Relationship type — 54 declared across six families

| family | n declared | n with rows |
|---|---:|---:|
| CORPORATE | 18 | 3 |
| GOVERNMENTAL | 13 | 1 |
| ALASKA_GEOGRAPHIC | 9 | 2 |
| INSTITUTIONAL | 7 | 2 |
| HISTORICAL | 6 | 0 |
| INDIVIDUAL_NATIVE | 1 | 0 |

**`OWNERSHIP_BEARING` carries money upward in a roll-up. `NEVER_OWNERSHIP` does
not, and association is never upgraded without evidence.** Governmental and
geographic ties carry nothing: a constituent band's contracts are not the
umbrella's, and an ANCSA region is a place, not an owner. **$27.59B was booked
wrong on that confusion**, and typing the flat parent column measured the payoff:
$0 rolled through non-ownership edges against **174 such edges sitting on
entities holding $57.04B** that a flat column would have moved.

`owner_self_identifies_with` is the sole `INDIVIDUAL_NATIVE` type. It records
that the PERSON who owns a firm says they are of a tribe. It is an attribute of a
PERSON, never an edge of the FIRM, is never keyed to a `tribe_id`, and carries no
money ever. Thirty-eight of the 45 individual-Native rulings read *"owned by
individual Cherokees"* — and "Cherokee" resolves to three federally recognised
tribes and a long tail of unrecognised groups, so it does not resolve at all.

## The other imported vocabularies

`MeasurementType` (17 values, with `is_observed` and `NEVER_PROMOTES_TO_ACTIVE`)
· `InstrumentFamily` (4, with `obligations_are_summable` — **CREDIT reports $0
obligation by design**) · `EventClass` (3) · `AdvocacyChannel` (15, each carrying
its event class and `is_lobbying`) · `Position` (4, plus the three-leg
`POSITION_KEY`) · `EvidenceClass` (3) · `ALIAS_TYPES` (17) · `REVENUE_EVIDENCE`
(7, ordered best to worst) · `NP_CLASSIFICATION` (positive / negative /
undecided) · `LOBBYING_WITHDRAWAL_MARKS` · `NAME_TRAPS` (51) · `PLACE_SUFFIXES`
(21) · `PROMOTED_TABLES`. All exported in full to the JSON.

Three of these encode a refusal that has already been paid for:

- **`AdvocacyChannel.is_lobbying` is NARROWER than `EventClass.ADVOCACY`.** An
  administrative comment or an amicus brief is advocacy and is not LOBBYING, and
  calling it lobbying would be wrong in a way that matters legally. Tribal
  consultation is a statutory government-to-government obligation and is
  `GOVERNMENT_ENGAGEMENT`; filing it under lobbying would characterise a
  sovereign relationship as influence-buying.
- **`may_promote_event_class` — an ACCESS event NEVER becomes an ADVOCACY
  event.** A visitor log says a person entered a building.
- **`NP_CLASSIFICATION` is an ALLOW-LIST OF POSITIVES.** An unrecognised token is
  NOT Native. The inverted polarity — anything that is not a known negative is a
  positive — read `not_a_native_entity` as *ruled Native*.

---

# PART III — THE ABSENCE VOCABULARIES. THERE ARE FOUR

Absence is where our own defects most often get published as facts about the
world, so every blank is typed. **`NOT_CHECKED` is the only token common to all
four vocabularies.**

| declared in | values | scope |
|---|---|---|
| `code/288_build_collection_descriptors.py::ABSENCE_VOCABULARY` | `NOT_IN_SOURCE` · `BELOW_REPORTING_THRESHOLD` · `OUT_OF_SCOPE_BY_CONSTRUCTION` · `SUPPRESSED` · `REPORTED_EMPTY` · `NOT_CHECKED` | product-wide; shipped in every collection descriptor |
| `code/cedar_domain.py::ABSENCE_VALUES` | `NO_CLAIM_FOUND` · `NO_SITE_FOUND` · `SITE_UNREACHABLE` · `NOT_CHECKED` · `UNDETERMINED` | individual-Native ownership evidence only |
| `AGENTS.md`, source-coverage | `PUBLISHES` · `WITHHOLDS` · `NOT_FOUND` · `NOT_CHECKED` | whether a SOURCE publishes a fact |
| `review/tribal_vendor_list_registry_*.csv::verdict` | `LIST_FOUND_MACHINE_READABLE` · `LIST_FOUND_PDF` · `LIST_FOUND_HTML` · `LIST_BEHIND_LOGIN` · `LIST_REFERENCED_NOT_PUBLISHED` · `NO_LIST_FOUND` · `SITE_UNREACHABLE` · `NOT_CHECKED` | whether a tribal AUTHORITY publishes a list |

**The first two are deliberately NOT merged, and 288 says so in its own source:**
collapsing them would let *"we did not sweep this firm's website"* be read as
*"the source reported nothing"*. That separation is correct and is recorded here
rather than reconciled away.

**The third and fourth are not declared in code at all.** See Gap 8.

`FORBIDDEN_ABSENCE_VALUES` — `NOT_NATIVE`, `NON_NATIVE`, `NOT_INDIAN`,
`FALSE_CLAIM`, `NOT_VERIFIED_NATIVE` — must never appear anywhere. Each asserts a
negative about a private individual's ancestry that no source establishes.

---

# PART IV — THE COMPARATIVE CERTIFICATION TAXONOMY, DERIVED

*Source: `data/staging/tribal_vendor_lists/tribal_certification_rules_2026-08-26.csv`
(14 authorities) built by `code/323_build_tribal_certification_rules.py`, beside
the 30-entity discovery registry. **STAGED, NOT SHIPPED**: every row is
`consent_status = UNRESOLVED`, `publishable = N`, and
`code/321_gate_tribal_source_restriction.py` fails any build that tries.
**Silence is UNRESOLVED, never permission.***

**The categories below were not pre-specified and then fitted to tribes.** Each
axis was tested against the 14 rules and kept, reframed or discarded on what the
tribes actually do. **The sample is 14 authorities, over-sampled toward large
contractors and known TERO offices; nothing here is a rate.**

## Scope, first — the two binaries that are not one binary

**A tribe can publish the RULE without the LIST, or the LIST without the RULE,
and a taxonomy keyed on "does this tribe certify" conflates them.**

| | list published | list not published |
|---|---|---|
| **rule published** | 13 | **1 — Seneca Nation** |
| **rule not published** | **1 — Cherokee Nation** | (not measurable from here) |

Seneca publishes the most complete criteria in the study — a four-rung ladder,
*"51% or more Indian-owned and controlled"*, *"significant Indian management"* —
and **no list at all**. Cherokee publishes the largest list in the study — *"Over
700 Certified Indian-Owned Businesses"* — and **no criterion whatsoever**.

**And not one of the 14 is `RULE_FOUND`.** 13 are `RULE_PARTIAL`, 1 is
`RULE_NOT_PUBLISHED`. **No tribe in the study publishes a complete rule.** That
is the single most important number in this layer and it bounds every use of it.

## The axes, as derived

### AXIS 1 — Is an ownership percentage required at all? **KEPT, and it is mostly unanswerable**

| value | n |
|---|---:|
| `NOT_STATED` | 10 |
| `YES` | 3 — Navajo, Seneca, Poarch |
| `NO` | **1 — Colville** |

The axis survives, and the finding is that **it is answered by only 4 of 14**. A
subscriber wanting to apply their own 51% threshold can do so for four
authorities and for no others.

**Colville is the case that justifies the whole layer.** The contractor list
carries a numeric `INDIAN PERCENT OWNED` column *and* a separate `CERTIFIED TITLE
10` flag, and **firms appear at 0% Indian ownership still flagged certified**.
Cedar Press publishes the rule and the percentage. It does not decide whether
that counts.

### AXIS 2 — Is the certification GRADED? **KEPT, and it is ORTHOGONAL to Axis 1**

`is_graded`: **Y 7 · N 7.** The cleanest split in the table — and the derived
finding is that **gradedness and percentage are two different axes and must not
be collapsed**:

- **Graded on HOW MUCH** — Navajo (*100% Navajo-owned and controlled* vs *51–99%
  Navajo-owned*), Seneca, Poarch.
- **Graded on WHO, with no percentage anywhere** — CSKT (*PREFERENCE 1 = CSKT
  TRIBAL MEMBER · PREFERENCE 2 = MEMBER FROM A FEDERALLY RECOGNIZED TRIBE*),
  Colville, EBCI.
- **Graded on OPERATIONAL CONDUCT** — MHA. See Axis 6.

A taxonomy with a single "threshold" field would have flattened the second group
to `NOT_STATED` and lost the ladder entirely.

### AXIS 3 — WHOSE ownership? **KEPT, and the hypothesis of three populations is WRONG — there are five, and two of them are not populations**

The brief's hypothesis was three: a member of THAT tribe / any tribe / any Native
person. The data shows five values, and the two most common are not
person-populations at all.

| value | n | what it actually is |
|---|---:|---|
| `MIXED_SEE_TIERS` | 6 | a LADDER, not a population — see below |
| `NOT_STATED` | 3 | Cherokee, CTUIR, Oneida |
| `PARENT_CORPORATION` | 3 | **not a population**: an ANC naming its own subsidiary |
| `THIS_TRIBE_MEMBER` | 1 | EBCI |
| `SHAREHOLDER_OR_DESCENDANT_OR_SPOUSE` | 1 | **a fourth population nobody anticipated** |

**Finding 3a — the graded schemes are all the same ladder, and it runs from THIS
tribe outward.** Every one of the six `MIXED_SEE_TIERS` authorities ranks its own
members first and members of other federally recognised tribes last:

    Navajo    #1 100% Navajo-owned and controlled
              #2 51–99% Navajo-owned, OR 51–100% owned by members of other
                 federally recognised tribes
    CSKT      P1 CSKT tribal member          P2 member from any federally recognised tribe
    Colville  Tribal Member · Colville Family Business Enterprise ·
              Other Federally Recognized Tribal Member · Indian Business Enterprise
    Seneca    100% Seneca · 100% Indian-Majority Seneca · Majority Seneca ·
              Commission-certified 51%+ Indian-owned and controlled
    MHA       L1–L3 certified Indian contractors · L4 members of other federally
              recognised tribes

**So "certified Indian-owned" is not one population. It is an ordered set of
populations, and the ordering is the tribe's policy.** A reader who assumes the
first rung is what a certification means will be right about the top of every
list and wrong about the rest of it.

**Finding 3b — ANCSA adds a population outside the tribal frame entirely, and it
confirms the ANCSA ruling from a tribal source.** Calista's Calivika directory
lists businesses owned by *"Calista Shareholders, descendants, or spouses"*. A
**spouse** need not be Native at all, and `ownership_pct_threshold` reads *"NONE
STATED — and the absence is the point: eligibility runs on WHO owns, not HOW
MUCH."* This is `docs/ANCSA_OWNERSHIP_RULING.md` rule 4 — *a shareholder is not
necessarily enrolled in the tribe; a shareholder necessarily has ancestry* —
arriving independently from a corporation's own directory. All three ANCSA
authorities record `enrollment_requirement = NOT_APPLICABLE — ANCSA corporation`.

**Finding 3c — `PARENT_CORPORATION` is a different KIND of assertion and should
eventually leave this axis.** ASRC, NANA and Doyon are not certifying persons.
They are a parent naming its own subsidiary, and their `control_requirement` says
so: *"Stated as a parent-subsidiary relationship rather than a percentage."* It
is the **strongest evidence in the layer** — the parent publishes the
subsidiary's CAGE, UEI and DUNS beside its own, so no name matching is needed —
and it is not a certification programme. Filing it in a "whose ownership" column
mixes a corporate-control fact with a population fact.

### AXIS 4 — Enrollment / residency / on-reservation. **RESIDENCY DISCARDED AS AN ELIGIBILITY AXIS; RETAINED AS AN ATTRIBUTE**

`residency_or_onreservation_requirement`: `NOT_STATED` 9 · `NOT_APPLICABLE` 3,
and **two informative rows, neither of which is a requirement**:

- **Navajo — `NOT REQUIRED`**, and the listing proves it: certified firms in
  Phoenix, Tempe and Chandler, all off-reservation.
- **Colville — `NOT a criterion, but RECORDED`**: the list carries
  on-reservation / near-reservation / off-reservation flags per firm.

**Zero of 14 make location an eligibility condition.** The axis as posed —
*"is residency required"* — has one answer everywhere it is answered, so it
carries no information. Reframed as **"is location recorded"** it separates
exactly one authority and becomes useful. Enrollment survives as an axis
(4 authorities state it, 3 declare it inapplicable) but is nowhere a
free-standing criterion — it is the thing the tier ladders in Axis 3 are ranking.

### AXIS 5 — Verification method. **THE THREE-WAY HYPOTHESIS IS DISCARDED; THE DATA SUPPORTS A DIFFERENT THREE**

The hypothesis was *documents, site visit, or self-attestation*. Measured:

- **Site visit: ZERO observations.** Nothing in the 14 describes an inspection.
- **Self-attestation: ZERO, strictly.** Calista's is the closest — *"a
  self-service 'Submit Your Business' form is the visible intake and no
  verification step is described"* — and that is `NOT_STATED`, an **absence of a
  described step**, not an authority saying it accepts self-attestation.
  Recording it as self-attestation would be our own scope limit published as a
  fact about the source, which is defect class 2.

What the data supports instead:

| derived value | n | evidence |
|---|---:|---|
| `ADJUDICATED_BY_A_TRIBAL_BODY` | 6 | *"certified by the … TERO Manager against Chapter 5 of the CTUIR TERO Code"* · *"Certification by the TERO Commission"* · *"vetted by the TERO office"* · Poarch under Ordinance Title 33 |
| `APPLICATION_ON_FILE` | 2 | Navajo's NBOA certification package; Oneida's IP Vendor Application |
| `PARENT_ASSERTION_WITH_IDENTIFIERS` | 3 | the ANC directories, publishing CAGE + UEI + DUNS |
| `NOT_STATED` | 3 | |

**The distinction that matters for the evidence layer is `evidence_leg`, not
`verification_method`.** Tier A requires *a leg that is not the firm*. A tribal
government certifying a business **is** a third party with authority over the
question; a SAM socio-economic flag is the firm certifying itself.

### AXIS 6 — Operational control, graded separately from ownership. **NEW — the data forced it**

Not in the brief, and it is present at 3 of 14:

- **MHA Nation** publishes **Preference Level 1 = certified Indian contractors
  SELF-PERFORMING**, Level 2 = with mentorship agreements, **Level 3 = CERTIFIED
  INDIAN CONTRACTORS ACTING AS BROKERS**, Level 4 = members of other federally
  recognised tribes. *A tribal government publicly flagging which of its own
  certified firms operate as pass-throughs.* If Cedar Press ever touches
  pass-through structure, that is a primary source and it is already public.
- **Seneca** — *"owned AND CONTROLLED"* at Sec. 4A.A and *"significant Indian
  management"* at Sec. 2.J.
- **Navajo** — a numeric per-record `Ownership Control: NN %` field, separate from
  the ownership percentage.

**Ownership and control are two axes and three authorities grade them
separately.** Collapsing them would lose the only public data anywhere on tribal
pass-through structure.

### AXIS 7 — The entity/individual split, INSIDE the tribes' own schemes. **NEW, and it validates a Cedar class**

Cedar Press had to invent the line between a tribally owned entity and an
individually Native-owned firm. **At least two tribes draw it themselves, and
print it as headings on one list:**

- **Poarch Creek** — `TRIBAL BUSINESSES` (tribally owned — PCI Manufacturing, PCI
  Printing, PCI Support Services) versus `100% TRIBAL MEMBER OWNED BUSINESSES`
  (individual member-owned). `ownership_pct_threshold` records it exactly:
  *"100% for the individual-member segment; the tribally owned segment is
  entity-owned rather than percentage-based."*
- **Colville** — `Tribal Member` and `Colville Family Business Enterprise` sit
  beside `Indian Business Enterprise`.
- **Navajo** — Priority #2 mixes a percentage band with a membership class in one
  rung.

**`Individually Native-owned business` is not a Cedar invention. It is a
distinction tribes already make, in their own certification ladders.** That is
the strongest external support the class has, and it arrived from the tribes
rather than from us.

### AXIS 8 — What the certification is FOR. **DISCARDED FOR NOW — it does not vary, and saying otherwise would be our scope limit published as a fact**

All 14 are `assertion_class = OWNERSHIP`. Every one runs under an *employment
rights* ordinance (TERO = Tribal Employment Rights Office) and every artefact is
a *contractor list used for procurement preference*. The purpose axis therefore
has one observed value and cannot be derived from this sample. **Licensing** is a
genuinely separate product — 4 of 6 checked authorities have a business-licence
regime and **none publishes a registry** — and is parked, not measured.

### AXIS 9 — Currency. **KEPT — it varies more than anything else and it is what makes a time series possible**

Monthly by statute (Navajo, the only one) · weekly, stated (Oneida — *"This list
is updated on Friday Evenings"*) · bimonthly (EBCI) · annual (Colville, Poarch) ·
two-year certificates (CTUIR) · dated-list-supersedes (Poarch — *"the most
current date shall be used"*) · date-stamped filenames (MHA) · `NOT_STATED` 6.

`certification_status` is deliberately narrow: **a single capture can only
support `ASSERTED_AS_OF_CAPTURE`. `LAPSED_BY_CAPTURE` requires two captures.**

### AXIS 10 — Does the list contradict its own rule? **NEW, and it is the axis the whole layer exists for**

`rule_list_mismatch`, 2 of 14 non-`NO`:

- **Colville** — firms at `INDIAN PERCENT OWNED = 0` flagged `CERTIFIED TITLE 10
  = Yes`. **Presence on this list is therefore not by itself an ownership
  claim.** Cedar Press publishes the rule and the percentage and lets the
  subscriber filter.
- **Seneca** — the inverse: the rule is published and the list is not.

**"Being on a TERO list is an ownership claim" is false, and this column is how
we say so without arguing with a sovereign.**

## Axes offered and discarded, with the reason

| axis | disposition |
|---|---|
| ownership percentage required | **KEPT** — but answered by only 4 of 14 |
| whose ownership: three populations | **KEPT, REFRAMED** — five values, two of which are not populations; the graded schemes are one ladder, not a category |
| enrollment condition | **KEPT** — never free-standing; it is what the ladders rank |
| residency / on-reservation condition | **DISCARDED as eligibility** (0 of 14), **KEPT as an attribute** (1 of 14 records location) |
| verification: documents / site visit / self-attestation | **DISCARDED as posed.** Zero site visits, zero stated self-attestations. Replaced by adjudicated / application-on-file / parent-assertion |
| purpose: procurement / employment / licensing | **DISCARDED as unmeasured** — one observed value across 14 |
| *graded vs binary, independent of percentage* | **DERIVED** — 7/7, orthogonal to the percentage axis |
| *operational control graded separately* | **DERIVED** — 3 of 14, incl. MHA's public broker flag |
| *entity vs individual inside the tribe's own scheme* | **DERIVED** — validates `Individually Native-owned business` |
| *rule published without list, and the reverse* | **DERIVED** — two independent binaries |
| *list contradicts its own rule* | **DERIVED** — the Colville case |

---

# PART V — THE FEDERAL CATEGORIES, AND WHERE THEY DIVERGE FROM THE TRIBAL ONES

## Measured, `data/clean/prime_contracts.csv`, 1,217,768 rows, $244.77B attributed

| category | column | rows | attributed $ | share | Native-specific? |
|---|---|---:|---:|---:|---|
| 8(a) | `reported_8a` | 364,150 | **$97.327B** | 39.76% | **NO** |
| Buy Indian | `reported_buy_indian` | 9,498 | $0.494B | 0.20% | yes |
| Indian Business | `reported_indian_business` | 9,934 | $0.707B | 0.29% | yes |
| **union** | `reported_native_preference` | **383,582** | **$98.528B** | 40.25% | **misleadingly named** |

`setaside` is single-valued and mutually exclusive: *None reported* 598,321 ·
*8(a)* 364,150 · *Small Business* 163,064 · *Other* 55,439 · *HUBZone* 17,362 ·
*Indian Business* 9,934 · *Buy Indian* 9,498.

**The union is exact**: 364,150 + 9,934 + 9,498 = 383,582, verified at build
time. **Genuinely Native-specific set-asides are $1.2005B — 0.4905% of attributed
dollars.**

**Three things that must always travel with these numbers.**

1. **`reported_native_preference` is the union INCLUDING 8(a), and 98.8% of its
   dollars are 8(a).** Anyone filtering on that column to find Native
   set-asides gets the 8(a) programme. **8(a) is open to any socially and
   economically disadvantaged owner and carries no Native signal.**
2. **Buy Indian and Indian Business are ONE instrument under TWO codes and must
   always be summed.** `Indian Business` is zero in every year FY2000–2013 and
   overtakes `Buy Indian` in FY2016, because the DOI Buy Indian rule of
   2013-07-08 created a second tier. Read alone, `Buy Indian` says Native
   set-asides collapsed 62% after 2015; summed, they rose 44%.
3. **A set-aside is a property of the AWARD, not of each modification.** Fill it
   forward from `contract_award_unique_key` before computing any preference
   share, or the figure moves on a definition change and looks like a discovery.

## The six SAM business-type variants

`data/clean/sam_prime_contracts_fy2000_2007.csv`, 269,312 rows.

| variant | Cedar class | rows | in Native universe | `americanIndianOwned = YES` |
|---|---|---:|---:|---:|
| `INDIAN` | ENTITY_OWNED | 157,093 | **54,505 (34.7%)** | 52,713 |
| `TRIBAL` | ENTITY_OWNED | 8,273 | 8,186 | **2,846** |
| `ALASKAN NATIVE` | ENTITY_OWNED | 3,716 | 3,716 | 319 |
| `NATIVE HAWAIIAN` | ENTITY_OWNED | 379 | 379 | 0 |
| `NATIVE AMERICAN` | INDIVIDUAL_NATIVE_OWNED | 158,199 | 158,198 | 48,129 |
| `AMERICAN INDIAN` | INDIVIDUAL_NATIVE_OWNED | 52,714 | 52,713 | 52,713 |

**Three measured facts, each of which breaks a natural assumption.**

- **The `INDIAN` variant is majority noise.** 102,588 of its 157,093 rows are
  Subcontinent Asian Indian American owned firms, carried
  `include_in_native_universe = 0`. `indian` is in `NAME_TRAPS` for exactly this
  reason — *"Indian Aerospace, Inc."*
- **The two classes DO NOT PARTITION. 57,266 of 163,795 ENTITY_OWNED rows (35%)
  carry `class_conflict = 1`** — matched by an entity variant and an individual
  variant at once. The two classes are held apart on every row and **never summed
  into one "Native" total**.
- **`americanIndianOwned = YES` on 2,846 of 8,273 rows of the TRIBAL extract** —
  rows that are tribal enterprises: Chugach, ASRC, Chickasaw Nation Industries.
  **The flag does not separate individual from entity ownership.**

**And self-certification cuts both ways.** Goldbelt Raven, an ANC subsidiary,
certifies `alaskanNativeCorporationOwnedFirm = NO`, and 22 of the owner's 40
prior-ruled firms carry zero Native flags across every contract row — the
largest, Frontier Electronic Systems, on 998 rows and $204,225,019. **Absence of
a flag is not evidence against; presence of one is not evidence for.**

> ### THE "NO NATIVE PREFERENCE" SHARE IS RECORDED THREE DIFFERENT WAYS AND NONE OF THEM MATCHES THE FILE
>
> | source | figure | base |
> |---|---|---|
> | `AGENTS.md` (twice) | **60.9% / $86.19B** | a pre-backfill attributed base of ~$141.5B |
> | `cedar_domain.SELF_CERTIFICATION_IS_NOT_A_VERDICT` | **57.2% / $140.00B** | $244.77B |
> | **measured 2026-08-26 by `374`** | **59.75% / $146.238B** | $244.77B, 888,862 attributed rows |
>
> The `cedar_domain` figure and the measurement share a base and still differ by
> **$6.24B and 2.55 pp**. The `AGENTS.md` figure is a different, older base
> entirely and its percentage is the highest of the three, so **the three cannot
> be reconciled by picking one.**
>
> **And the measured figure is itself an UPPER BOUND, for a stated reason.** It
> reads `reported_native_preference` as recorded, and AGENTS.md's standing rule
> is that **a set-aside is a property of the AWARD, not of each modification** —
> the archive leaves it blank on 56% of rows and the two sources disagree on
> 59.6% of shared contracts. Filling forward from `contract_award_unique_key`
> would move rows OUT of "no preference" and lower this share. **Do not quote any
> of the four numbers as the no-preference share until the fill has been run;
> quote the Native-specific $1.2005B instead, which is a floor and does not move
> on this question.** Register this in `docs/DOC_CONTRADICTIONS_2026-08-26.md`.

## ANCSA's own categories

| statutory category | authority | Cedar class |
|---|---|---|
| Regional Corporation | ANCSA §7, 43 U.S.C. 1606 | `Alaska Native Regional Corporation` |
| Village Corporation | ANCSA §8, 43 U.S.C. 1607 | `Alaska Native Village Corporation` |
| **Urban Corporation** | named in 43 U.S.C. 1607(c) | **none — see Gap 6** |
| Group Corporation | named in 43 U.S.C. 1607(c) | `ANCSA Group Corporation` |

## WHERE THE TRIBAL AND FEDERAL DEFINITIONS DIVERGE

**Nobody has published this comparison. Each row is a measured divergence, not an
opinion about which side is right.**

**1. The federal flag asks WHETHER. The tribal rule asks WHOSE and HOW MUCH.**
`americanIndianOwned` is a boolean with no percentage and no tribe named. Navajo
grades 100% against 51–99%; Seneca runs a four-rung ladder; Colville records a
numeric percent per firm. **A subscriber can apply a 51% threshold to a tribal
certification. They cannot apply any threshold to a federal flag, because the
federal record carries no number.**

**2. The federal "whose" is always "any Native". The tribal "whose" is usually "a
member of THIS tribe", ranked.** No federal flag distinguishes a Navajo-owned
firm from a Cherokee-owned one. Every graded tribal scheme observed puts its own
members first and members of other tribes on a lower rung.

**3. The one federal flag that discriminates carries 0.49% of the dollars.** Buy
Indian + Indian Business is $1.2005B. The column named
`reported_native_preference` is 98.8% 8(a), a programme with no Native content.

**4. The federal record separates entity from individual badly; tribes separate
it explicitly.** SAM's six variants leave 57,266 rows in both classes at once.
Poarch prints the two segments as headings on one list.

**5. A federal set-aside is definitionally an ownership threshold. A tribal
certification need not be one.** Colville certifies at 0% Indian ownership. **No
federal category can express that**, because the federal categories have no cell
for a certification that is not about ownership share.

**6. ANCSA shareholding is neither federal Native ownership nor tribal
enrollment.** Calista certifies shareholders, descendants **and spouses** — and a
spouse need not be Native. §1602(r) defines the shareholder-eligible class by
lineal descent or qualifying minor adoption with **no reference to tribal
enrollment anywhere**, and §1606(h)(2) admits non-Natives **by inheritance**,
holding non-voting stock the corporation may buy back at fair value. The
shareholder roll is neither a subset nor a superset of the enrollment roll.

**7. The federal surface has ONE assertion class; the tribal surface has THREE.**
Federal records assert OWNERSHIP only. Tribal publications assert `OWNERSHIP`
(certification), `RELATIONSHIP` (a vendor or supplier list — *"does business
with"*) and `OPERATING_ON_LAND` (a business-licence registry). **Reading a
RELATIONSHIP row as OWNERSHIP is the single failure mode that would discredit
this layer**, and many of its entries will be Home Depot.

**8. The federal flag is SELF-certification. The tribal certification is
THIRD-PARTY adjudication.** That asymmetry is the entire product case: tier A
requires a leg that is not the firm, and a tribal government certifying a
business is a third party with authority over the question. The 13 publishing
entities carry **390 tier-B ledger rows on $41.10B**, including **37 rows whose
method is literally `agent_research_one_leg`** — one leg short, carrying $3.73B,
and a tribal certification is that leg.

---

# PART VI — GAPS AND CONTRADICTIONS

**Named, not silently reconciled.** All **nine** are detected by `374` and carried
in `docs/CEDAR_TAXONOMY.json → gaps_and_contradictions`, so they are re-measured
on every run rather than going stale in prose. **Nothing below has been changed;
each carries a proposal.**

The ninth is
**`NO_NATIVE_PREFERENCE_SHARE_DISAGREES_ACROSS_THREE_SOURCES`** and it is written
up in Part V, beside the numbers it contradicts, because that is where somebody
is about to quote one of them.

### GAP 1 — `ANCSA_CLASS_GUARD_UNCALLED`. The $24.52B rules are encoded and never invoked

`cedar_domain.bears_ownership(rel, owner_class, owned_class)` fires ANCSA **RULE
2** (a village government never owns an ANC) and **RULE 4** (nor the reverse)
**only when both class arguments are passed.**

Measured: `ANCSA_CORPORATION_CLASSES`, `ALASKA_VILLAGE_GOVERNMENT_CLASSES`,
`ancsa_refusal_reason()` and `village_government_owns_an_anc()` have **zero
importers outside `cedar_domain.py`**. The one production caller that walks a real
edge table is `97_build_aliases_and_relationships.py:829`, and it calls
`D.bears_ownership(r["relationship_type"])` — class-blind. Every other call site
(111, 112, 132, 94) is a module-load assertion on a constant. The only calls that
pass classes are `241`'s own self-test.

**This is not a claim that the ruling went unapplied.** It was applied, to all
334 defects, by `191_apply_ancsa_ownership_ruling.py` — **using its own local copy
of the class sets** (`CORPORATION_CLASSES`, line 135). **The ruling was enforced
and the reusable guard was not**, which is precisely the shape AGENTS.md names:
*a defect fixed in one place leaves no trace in the other nine.*

**Proposal.** Change `97:829` to pass the source and target classes. It cannot
fire today anyway — see Gap 2 — so fixing Gap 2 without this one would leave the
guard blind at exactly the moment the edges become checkable. Do them together,
and add a `--selftest` fixture that fails if any caller of `bears_ownership` on a
real edge table passes fewer than three arguments.

### GAP 2 — `owned_by` edges cannot be class-checked at all

**1,575 of 2,292 rows (68.7%) of `entity_relationships.csv` have a blank
`source_entity_id`, including ALL 1,462 `owned_by` rows and all 106 `brand_of`.**
`97:826-827` skips any row with a blank endpoint, so the roll-up guard at `:829`
never evaluates a single ownership edge. Nine `owned_by` edges point at a village
government — exactly the RULE-2/RULE-4 shape — and are unauditable without a
source class.

The blanks are often correct and documented (*"brand family 'aanikoosing' has no
spine entity — a brand is a name family, not a legal person"*). The problem is
that a legitimate blank and an unresolved one are the same value.

**Proposal.** Type the blank: `NO_SPINE_ENTITY_BY_RULING` versus `UNRESOLVED`.
Then the 9 village-government `owned_by` edges become a queue instead of a
silence.

### GAP 3 — `SPINE_CLASS_ABSENT_FROM_CEDAR_DOMAIN`. 12 of 17 classes, 1,070 of 1,534 rows

Only 5 classes appear anywhere in `cedar_domain.py`. **The largest class in the
spine — `Federally recognized tribe`, 349 rows — is not in the shared domain
module at all**, so no shared predicate can branch on it.

**Consequence, measured: the entity-class vocabulary is re-typed in 42 build
scripts**, under at least three variable names per concept
(`GOVERNMENT_CLASSES` / `GOV_CLASSES` / `GOVERNMENT_ENTITY_CLASSES`), **with
member sets that genuinely disagree.** `96_build_consultation_events.py` uses a
7-member set; `111_build_advocacy_passthrough.py` uses 3 and deliberately
excludes the two constituency classes. **Both carry a written justification and
neither can see the other**, because there is no shared declaration where they
could be reconciled or even placed side by side. The fullest enumeration in the
repo — 16 members — sits in
`358_measure_sam_individual_native_class_delta.py:87`, a one-off measurement
script.

**Proposal.** Promote a canonical `ENTITY_CLASSES` frozenset into `cedar_domain`,
seeded from the spine itself, plus the named subsets the scripts actually need
(`GOVERNMENT_CLASSES`, `ANCSA_CORPORATION_CLASSES`, `INSTITUTION_CLASSES`,
`MEMBERSHIP_CLASSES`). **Do not silently unify the disagreeing member sets** —
each divergence is a decision somebody made with a reason; carry the reason into
the shared module as a named subset so both readings survive and become visible
to each other.

### GAP 4 — `CODE_USES_A_CLASS_STRING_THE_SPINE_DOES_NOT_HAVE`. Seven instances, and they are NOT all the same severity

| file | uses | spine actually says | what it is |
|---|---|---|---|
| `103_build_california_gaming.py` | `Native CDFI` | `Native Community Development Financial Institution` | **dead guard** |
| `103_build_california_gaming.py` | `Native financial institution` | `Native Financial Institution` | **dead guard** |
| `105_build_florida_gaming.py` | `Native CDFI` | *(same)* | **dead guard** |
| `105_build_florida_gaming.py` | `Native financial institution` | *(same)* | **dead guard** |
| `cedar_match_guard.py` | `Native CDFI` | *(same)* | **vacuous fixture** |
| `73_bills_votes_completion.py` | `Alaska Native Village Government` | `Federally recognized Alaska Native Village` | display label |
| `73_bills_votes_completion.py` | `Federally Recognized Tribe` | `Federally recognized tribe` | display label |

**Read the call site before treating an instance as a defect** — the detector
finds the string, not the intent.

`103` and `105` each declare `REFUSED_ENTITY_CLASSES` — the Chickasaw Children's
Village refusal applied to gaming payments — and **two of the five entries in
each refuse a string that is not in the spine.** 93 spine entities (64 NCDFI + 29
NFI) are not refused by the California and Florida gaming builds.
`107_pull_remaining_states.py` gets it right, with the long forms, which is how we
know the rename happened and these two were not brought along. And
`cedar_match_guard.py`'s `MUST_REFUSE` fixture asserts on `Native CDFI` — **a
fixture that passes vacuously is a fixture that proves nothing**, which is the
`--selftest` reasoning in 293 read backwards.

**`73_bills_votes_completion.py` is NOT a dead guard and must not be reported as
one.** Its `CLASS_MAP` maps a bill-subject category to `(prefix, label)` pairs,
and the two strings are **display labels**, not membership tests. Nothing filters
on them. The cost is presentational — the product prints a class name the data
does not use — and it is worth fixing for that reason alone, at a different
priority from the four dead guards.

**Proposal.** Replace all seven literals with an import from the canonical set
proposed in Gap 3, and add the near-miss scan in
`374::scan_code_for_entity_class_literals` to `293_lint_bug_classes.py` as a new
class — a guard written against a name that does not exist is a distinct defect
shape and it is currently detected by nothing.

### GAP 5 — the prefix is treated as the class in two places, and it is not

`ANVC` carries both `Alaska Native Village Corporation` (173) and `ANCSA Group
Corporation` (6). `CDFI` carries both `Native Community Development Financial
Institution` (64) and `Native Financial Institution` (29).

- **`41_build_codebooks.py:1338-1340`** documents `entity_id_prefix` as *"The
  spine tribe_id prefix identifying the class (ANVC-, ANRC-, NHO-, ITO-, AKNF-,
  TRBF-). **Join to the spine on this prefix.**"* That instruction is wrong for
  `ANVC-`, which spans two classes — and the enumeration itself omits `CDFI`,
  `BIE`, `UIO`, `TCU`, `TRBS`, `CNSF`, `CNSS` and `SGVF`, so a reader following
  it reaches 8 of 17 classes.
- **`73_bills_votes_completion.py:1417-1432`** maps each bill subject to
  `(prefix, label)` pairs and labels `ANVC-` as `Alaska Native Village
  Corporation` outright, so the 6 ANCSA Group Corporations are labelled as
  village corporations wherever that subject fires.

Together these cover **272 entities** across the two ambiguous prefixes.

`cedar_ids.py`'s own rule already says why: *type lives in a column and is read
from the registry; it is never inferred from the prefix.* **The rule is right and
two consumers do not follow it.**

**Proposal.** Read `entity_class` from the spine. Neither site needs the shortcut.

### GAP 6 — `ANCSA_STATUTORY_CATEGORY_HAS_NO_CEDAR_CLASS`. The Urban Corporations

43 U.S.C. §1607(c) names *"Village Corporations, Urban Corporations, and Group
Corporations"*. Cedar has a class for two of the three. **Goldbelt (Juneau), Shee
Atika (Sitka), Natives of Kodiak and Kenai Natives Association are Urban
Corporations sitting in `Alaska Native Village Corporation`.**

**This is a LABEL defect, not an ownership defect**, and the distinction matters:
§1607(c) applies §1606(g), (h) and (o) **identically** to all three forms, so
every ownership and share-transfer conclusion in
`docs/ANCSA_OWNERSHIP_RULING.md` holds unchanged. What breaks is naming — an
analyst filtering "village corporations" gets four entities that are not, and a
future `Alaska Native Urban Corporation` class would not be in
`ANCSA_CORPORATION_CLASSES` unless somebody remembers to add it.

**Proposal.** Add `ancsa_corporation_form` as a COLUMN
(`VILLAGE` / `URBAN` / `GROUP` / `REGIONAL`) rather than splitting the class —
the class governs a guard and the form is a statutory fact, and separating them
means adding the fourth form cannot silently drop four entities out of a
membership test.

### GAP 7 — `LEDGER_ENTITY_CLASS_IS_A_SECOND_VOCABULARY`. 21 values, two schemes, and the largest is not a class

`cedar_identifier_ledger_final.csv` (20,577 rows) carries its own `entity_class`:
10,908 blank, **4,143 rows in the spine's prose vocabulary, and 6,005 rows in an
UPPER_SNAKE vocabulary that exists nowhere in the spine.**

    TRIBAL_UNCROSSWALKED_SBA 3,133 · FEDERAL_TRIBE_LOWER48 1,370 ·
    BGOV tribal vendor 878 · FEDERAL_AK_VILLAGE 341 · ANC_REGIONAL 140 ·
    STATE_TRIBE 96 · STATE_TRIBE_CONSTITUENCY 19 · TRIBAL_COLLEGE 15 ·
    FEDERAL_TRIBE_CONSTITUENCY 9 · INTERTRIBAL_ORG_AK_CONSORTIUM 4

Eight of the ten map cleanly onto a spine class. **Two do not, and they are the
two largest: `TRIBAL_UNCROSSWALKED_SBA` (3,133) and `BGOV tribal vendor` (878)
are PROVENANCE, not class** — they say where a row came from. **The most
populated value in a column named `entity_class` is not an entity class.**

`FEDERAL_TRIBE_LOWER48` is separately named in `cedar_domain.py:411` as an
artefact of a known defect: CAGE `9DVK5` carries it while bound to a tribe that
does not own it.

**Proposal.** Do not remap in place — a rebuild would revert it and the blank
10,908 would still be blank. Add `entity_class_scheme`
(`SPINE` / `LEGACY_UPPER_SNAKE` / `PROVENANCE_NOT_A_CLASS` / `BLANK`) beside it,
the same shape as `tribe_id_scheme_resolved` in the assistance table, so a
consumer can see the seam instead of discovering it.

### GAP 8 — four absence vocabularies, two of them undeclared

Part III has the table. The `cedar_domain` / `288` pair is deliberately separate
and 288 documents why. **The AGENTS.md source-coverage vocabulary
(`PUBLISHES` / `WITHHOLDS` / `NOT_FOUND` / `NOT_CHECKED`) and the tribal registry
`verdict` vocabulary are declared in prose and in a CSV respectively, and in no
module** — so nothing can validate a value and a typo becomes a new category.

**Proposal.** Declare both in `cedar_domain` beside `ABSENCE_VALUES`, each with a
scope docstring saying which question it answers, and keep all four separate.
**Do not merge them.** The distinctions are load-bearing: *"we did not sweep this
firm's website"*, *"the source reported nothing"*, *"the authority withholds by
statute"* and *"the list is behind a login"* are four different facts that look
identical as a blank.

### Also recorded, and NOT auto-detected

- **`OWNERSHIP_BEARING_TYPES_WITH_ZERO_ROWS`** — 9 of the 10 ownership-bearing
  relationship types carry no edge; `owned_by` alone carries 100%. Likewise all 6
  `HISTORICAL_RELATIONSHIPS`, `owner_self_identifies_with`, and both ANCSA edges
  added with the 2026-08-26 ruling. **46 of 54 declared types (85%) are unused.**
  Not a defect — a declared vocabulary is meant to run ahead of the data — but a
  reader should not infer from `ALL_RELATIONSHIPS` that Cedar Press holds a
  corporate org chart. It holds `owned_by` and seven other edges.
- **`verification_status` in `entity_relationships.csv`** carries 6 values
  (`RULED` 1,153 · `TIER_A` 546 · `STATUTORY` 391 · `OFFICIAL_UNLINKED` 148 ·
  `MIGRATED` 52 · `RULED_TIER_C` 2), **none declared anywhere in code.**
- **`ENTITY_CLASS_WITH_NO_STATED_VERIFICATION_ROUTE`** — 15 of 17 classes, 1,279
  of 1,534 rows, carry no `verification_route`. **How membership was established
  is answerable from the file for only `Native Hawaiian Organization` and
  `Individually Native-owned business`.** For the other 15 this document had to
  reconstruct it from build-script docstrings, and it says so per class in the
  JSON.
- **`cedar_keys.py`'s usage docstring advertises `key_for` and `KeyError_`,
  neither of which exists** — the real names are `publishable_key_for` and
  `UnstableKey`. A stale docstring on the module that governs primary keys.
- **No individual-Native ID prefix exists in `cedar_ids.PREFIXES`.** The class is
  in `cedar_domain`, the privacy-surrogate prefix `INF` is in `cedar_keys`, the
  live `INV-{rank:04d}` column is minted by a numbered script as a bare f-string
  — and `cedar_ids`, whose docstring says *"all internal IDs from one shared
  service"*, knows about none of them. `INV-0307` has already silently acquired
  another firm's ownership sentence.

---

# PART VII — HOW TO USE THIS

**A subscriber** reads Parts I, IV and V. The certification layer is the one that
lets them apply their own threshold; Part V is where they learn that the federal
flag cannot support one.

**A future agent** imports `docs/CEDAR_TAXONOMY.json`. Regenerate it after any
change to `cedar_domain.py`, the spine, or the certification layer — `--check`
tells you whether it would change without writing.

**The product** renders `layers` behind the collections' `method` field.
`374` writes only `docs/CEDAR_TAXONOMY.json` and nothing in `data/clean/` or
`dist/`, so it moves no shipping metric and no rebuild can revert it.

**A rule for adding to this taxonomy.** A new class, vocabulary or axis is added
with: a definition, what it is NOT, how membership is evidenced, its tier
implication, and where it is enforced in code. **A value with no enforcement site
is recorded as unenforced rather than left to look enforced** — Gap 4 is what
happens otherwise.
