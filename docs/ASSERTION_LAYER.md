# The assertion layer — how Cedar stops overwriting facts

*Built 2026-08-29 as mission Phase 3, the ranked #1 finding in
`docs/FOUNDATION_AUDIT.md`. Code: `code/510_assertions.py`. Read with
`docs/IDENTIFIER_STANDARD.md` (who an entity is) — this document is about what
we claim about that entity, who said it, and what happens when two sources
disagree.*

```
py -3 code/510_assertions.py all --apply
```

---

## What was wrong

`cedar_entity_spine.csv` has one `state` column. When a second script learned a
better state it destroyed the first answer **and the reason for it**. Nothing
recorded that a disagreement had ever existed.

The spine's own schema is the confession. It carries **two parallel evidence
column pairs** — `evidence_url`/`source_url` and
`source_quote`/`entity_source_quote`. That is what happens when a second writer
needs evidence fields and the first ones are already taken. There is no third
pair only because nobody has needed one yet.

Measured before the layer existed:

| | |
|---|---|
| spine rows with **no** `verification_route` and **no** `evidence_tier` | **1,279 of 1,536 (83.3%)** |
| `.bak_*` copies of the spine in `data/spine/` | **20** — the de facto fact history, and unusable |
| rows graded `TWO_INDEPENDENT_FEDERAL_SOURCES` | **2** |

That last number is the point. The independence idea was already right. It had
just never been generalised past two rows.

## What replaced it

An **append-only** assertion table. A fact is never edited — it is asserted
again by someone else — and the value Cedar stands behind is **computed** from
ordered, public rules.

```
data/clean/cedar_assertions.csv        29,718   every claim, with who and why
data/clean/cedar_resolved_facts.csv    29,356   the winner + WHICH RULE decided
data/clean/cedar_fact_conflicts.csv         0   every losing value, kept
data/spine/cedar_source_registry.csv       15   sources + evidence lineage
data/spine/cedar_resolution_rules.csv       8   the rules, as data
```

All three `data/clean` tables are **internal by decision** — see the reason
recorded in `cedar_codebook.INTERNAL_TABLES`, and *Where this stands, honestly*
below.

### Nothing here was invented

Cedar already had two working assertion tables. This generalises them.

- **`cedar_identifier_ledger_final.csv`** — 20,577 rows, of which **461 sit at
  tier X**, which are *negative* rulings: *this UEI is not this tribe*. A table
  that stores refutations is already an assertion store. Its only limit was
  that it could only ever talk about identifiers. Here **tier X becomes the
  general `polarity = deny`**, so any fact can be refuted, not just an
  identifier. 331 refutations survived the harvest.
- **`gaming_source_claims.csv`** — 113 rows of real subject/predicate/object
  with quoted supporting text, source page, and an explicit evidentiary ladder.
  Already the right shape; it covered one source type.

## Lineage: why a source cannot confirm itself

Two sources agreeing means nothing if they are the same evidence wearing two
hats. If a compiled directory copied the Federal Register list, then "the FR
and the directory agree" is **one fact counted twice** — and a corroboration
rule that cannot see this will promote a lone federal notice to tier A on the
strength of its own echo.

So every source declares a `lineage_root_id`, roots form a tree through
`derives_from`, and two assertions are independent **only when their root
ancestry sets are disjoint** — not merely when their source ids differ.

```
LR_FEDERAL_REGISTER
├── LR_BIA_DIRECTORY     the tribal leaders directory republishes the roster
└── LR_CICD              a compiled product whose universe came from the roster
LR_SAM
└── LR_USASPENDING       recipient identity fields are copied from the registration
```

`LR_CICD → LR_FEDERAL_REGISTER` is the single most important edge in the file.
Without it, *"CICD and the Federal Register agree"* would read as two-source
corroboration on almost every tribe in the spine.

Cedar had already been writing these chains **by hand**, in
`verification_route`:

```
CAGE registry lookup <- data/spine/cedar_exclusion_rulings.csv <- hci_analysis.do
```

That is a lineage path in a string a human has to read. It is now a field.

**Three roots are marked `independence_is_unverified = 1` and cannot vote in
corroboration at all:**

- `LR_AGENT_WEB` — we do not know what page an agent read. If it read the FR
  list, its "independent" agreement with the FR list is an echo we cannot
  detect.
- `LR_CICD` — compiled, with unknown provenance on its non-roster fields.
- `LR_UNATTRIBUTED` — the 1,279 rows with no recorded provenance. Not a source:
  the *absence* of one, made countable so it can be paid down.

## The rules, in precedence order

They live in `data/spine/cedar_resolution_rules.csv`, each with its reasoning,
so the resolution is auditable by a buyer and not just by us.

| # | rule | what it does |
|---|---|---|
| R00 | `MULTI_VALUED_NO_CONTEST` | distinct values of a multi-valued predicate do not compete |
| R01 | `DENY_VETO` | a refutation at equal-or-higher tier removes the value it names |
| R02 | `AUTHORITY` | a source declared `authority_for` this predicate wins outright |
| R03 | `HUMAN_OVER_MACHINE` | an owner ruling beats any machine source |
| R04 | `TIER` | A > B > C, after capping at the source's ceiling |
| R05 | `CORROBORATION` | more **independent** evidence families wins |
| R06 | `RECENCY` | later `verified_date` wins — deliberately near-last |
| R07 | `DETERMINISTIC_TIEBREAK` | lowest sha1, **and flagged `decided_by_coinflip`** |

Two of these earned their placement the hard way.

**R00 exists because the first version of this resolver was wrong.** It treated
every predicate as single-valued. One entity — `CE-0017F-1G` — holds **90
UEIs**, a tribe with 90 registered enterprises, all of them real. The resolver
read that as 90 competing answers to one question, picked a winner, and filed
the other 89 as "losing values." **443 entities hold more than one UEI.** It
manufactured 6,327 conflicts that were not conflicts and 616 coin flips that
were not ties. An entity has one legal class and many UEIs; only the first kind
can be contradicted by a second value. Getting this wrong does not merely
miscount — it **silently discards true data while reporting that it is
preserving it**, which is worse than the overwrite model it replaces.

**R06 sits near last on purpose.** Entities rename — San Manuel became
Yuhaaviatam of San Manuel Nation — so recency has to matter. But if recency
ranked high, a fresh guess would overwrite an old federal record, which is the
original disease.

**R07 is flagged rather than silent.** A coin flip is not a decision. It is a
queue of facts that need a human or a better source.

## Verification

`verify` runs nine invariants and exits non-zero on any breach. The ones worth
naming:

- **I3** recomputes every `assertion_id` from its own content. If the table is
  not reproducible, this fails. It is what makes the store diffable in git.
- **I6** is the circular-corroboration check: no fact may claim more
  independent families than its assertions actually support. This is the check
  the entire lineage tree exists to make possible.
- **I8** proves nothing was silently dropped — every losing value must appear
  in the conflict table. This is the defect the layer exists to fix, so it is
  checked rather than assumed.
- **I7** catches *dead authority*: a source declared `authority_for` a predicate
  it never asserts. It fired immediately on `bia_directory`/`entity.bia_region`
  and `org_self_statement`/`entity.website` — both still open, both listed
  below.

## The second source, and the trap it sprang

*Added 2026-08-29, the same day. This is the most useful section in this
document, because it records an error the layer caught before it shipped.*

The layer's first result was that **every fact in Cedar rested on exactly one
source** — 0 of 8,975 single-valued facts had a second, and only 2 had more than
one independent evidence family. So the next move was to find a second source,
and the identifier ledger looked ideal: each row carries the `state` and
`legal_business_name` that came with the **registration** — a SAM or IRS record,
genuinely a different evidence family from anything the spine says.

**First the column turned out to be corrupt.** `state` in
`cedar_identifier_ledger_final.csv` — a table that **ships** — held *that row's
own UEI* in 12,127 of 20,577 rows:

| `state` contained | rows | |
|---|---:|---|
| a UEI | 12,127 | 59.0% — in every case the row's own, character for character |
| empty | 4,072 | |
| a valid state | 3,481 | 16.9% |
| other text | 849 | full state names, `-` |
| multi-state strings | 48 | `ARIZONA; CALIFORNIA; COLORADO` |

The builder was not at fault: `01_build_entity_spine.py` reads `physical_state`,
which is correct. The corruption is **inherited** — in
`data/raw/external/master_tribal_entity_registry.csv`, `physical_state` equals
the row's own `uei` in 12,127 of 13,191 rows (92%). A buyer filtering the ledger
by state got silence for 59% of it and no way to learn why. Fixed by
`71_fix_known_defects.py` defect 5, which also normalised 846 full state names,
leaving **4,327 rows with a usable state** (up from 3,481). The validator now
lives in `cedar_pipeline.clean_state` so `01` and `71` cannot drift, and `01`
refuses the bad value if anyone ever overrides its `NEVER_RUN`.

**Then the real trap.** With a clean column, the harvester asserted it as
`entity.state`. The resolver did exactly as instructed:

| entity | spine | resolved | why |
|---|---|---|---|
| Akiak | AK | **VA** | an enterprise registered in Virginia |
| Alutiiq | AK | **CA** | |
| Anaktuvuk Pass | AK | **FL** | |
| Arctic Village | AK | **VA** | |
| Beaver | AK | **OK** | |

**Alaska Native village governments were being relocated to the lower 48**,
across 100+ entities, because an enterprise of theirs filed a mailing address
there. The resolved view came out *worse* than the spine it was built to check.

A registration address belongs to the **registrant** — usually a tribally owned
enterprise — not to the tribe. This is the containment error the project already
bars elsewhere, wearing a new hat: **a property of a thing an entity owns is not
a property of the entity.** Under the hub model in `IDENTIFIER_STANDARD.md`, a
registration is a sub-hub and its address is a fact about the sub-hub.

The fix was not to weight a rule differently. It was to **stop asserting it about
the wrong subject**. It is now `entity.registration_state`, multi-valued — *this
entity has registrations filed in AK, VA and OK* is true, useful, and can never
compete with where the entity actually is.

**What it cost and what it bought.** `entity.state` still has exactly one source;
the obvious second source was never a second opinion about the same thing.
Without this layer, someone would eventually have "enriched" the spine's `state`
from SAM and moved a hundred Alaska villages to Virginia silently, keeping no
losing value and no record of why.

**A third bug, caught by an invariant.** With real competition to arbitrate for
the first time, **I8 failed**: 98 losing values were dropped without reaching the
conflict table. When R07 breaks a tie it reorders the candidates, so the winner
is not necessarily `ranked[0]` — and taking `ranked[1:]` as the losers filed *the
winner* as a losing value and dropped the real loser. `CE-00006-4P` resolved to
VA, recorded VA as its own conflict, and lost AK entirely. Losers are now derived
from the winner rather than from the sort order.

Three times in one session a plausible line in this script silently destroyed
data it was written to preserve — the 90-UEI cardinality bug, this one, and the
wrong-subject assertion. Each was caught by a check written before it happened.
That is the argument for the invariants, and it is not hypothetical.

## Where this stands, honestly

Stated plainly, because the mission spec forbids claiming unverified behaviour.

```
29,718 assertions   29,356 resolved facts   331 refutations   0 conflicts
```

| | |
|---|---|
| single-valued facts with **more than one source** | **0** |
| facts with more than one **independent** evidence family | **38** (was 2) |
| genuine disagreements between sources | **0** |

The layer still has little to arbitrate, and that is the measured state of the
evidence base rather than a failure to look. `entity.state`, `entity.class`,
`entity.city` and every other single-valued entity field remain single-sourced.

Harvesting the Federal Register roster demonstrates the model rather than growing
the corroboration: 565 of 575 roster entries matched the spine and the
corroborated count did **not** move, because a copy of the FR living in the spine
and the FR itself are the **same family**. Most warehouses would have booked that
as 565 new confirmations.

Also open:

- **`gaming_source_claims` contributes 0 assertions.** No `cedar_uid` column, and
  only 10 of its 113 rows have a resolved subject.
- **11,676 of 29,718 assertions are `unattributed_legacy`** — the row they came
  from never recorded any evidence.
- **Two dead authorities** — `bia_directory`/`entity.bia_region` and
  `org_self_statement`/`entity.website` — declared but never asserting, flagged
  by the layer's own I7 check on every run.
- **`entity.is_federally_recognized` has no negative case.** The roster asserts
  `yes` for those on it; nothing asserts `no` for those off it.
- ~~**`ANRC-BRBYCO-00`** still keyed to "BRISTOL BAY AREA HEALTH CORPORATION"~~
  **CLOSED 2026-08-29** — `354 --apply` propagated the ruling to all 10 tables
  (742 rows); the ledgers carry it as tier X, harvested here as deny assertion
  #332. The repoint to `SGVF-BRSTLB-00` awaits an owner ruling (it keys
  dollars) — `review/rulings_inbox_2026-08-29_agent.csv`.

## Adding a source

1. Add a `LINEAGE_ROOTS` entry. If its content derives from an existing family,
   set `derives_from` — this is the decision that keeps corroboration honest,
   and getting it wrong is how a warehouse ends up believing its own echo.
2. Add a `SOURCES` entry with a `tier_ceiling` and a **narrow** `authority_for`.
   A roster that lists tribes is not an authority on their websites.
3. Write a `harvest_*` function that cites the row it read in `origin_table`.
4. Run `all --apply`. `verify` will tell you if you declared an authority that
   never asserts, or claimed corroboration you do not have.

---

## Per-predicate resolution policy — the 2026-08-30 pass

*External review F10, plus source-row conservation and two new invariants.
Everything below is measured from the live tables, not restated.*

### The rule order is the predicate's, not the file's

`R01 DENY_VETO` ran **before** `R02 AUTHORITY`. An equal-tier deny from a
source with no authority over the predicate therefore removed an
authoritative Federal Register affirmation before authority was ever
consulted. Fixing the order alone would have been another global special
case; the reviewer's point is that one universal order cannot serve stable
legal status, current leadership, addresses and ownership at once.

Six policies now live in `data/spine/cedar_resolution_policies.csv`:

| policy | rank order | deny may veto an authority | deny may predate the affirm | corroboration horizon |
|---|---|---|---|---|
| `STABLE_LEGAL_STATUS` | authority > human > tier > families > recency | no | yes | none |
| `CURRENT_LEADERSHIP` | authority > human > **recency** > tier > families | yes | no | 730d |
| `CONTACT_LOCATION` | authority > human > **recency** > tier > families | yes | no | 1095d |
| `OWNERSHIP_AND_STRUCTURE` | authority > human > tier > families > recency | no | no | none |
| `IDENTIFIER_BINDING` | authority > human > tier > families > recency | yes | yes | none |
| `DEFAULT` | authority > human > tier > families > recency | no | yes | none |

Three failure modes, three policy dimensions rather than three branches:

- **an equal-tier non-authority deny deleting an authoritative fact** —
  `deny_may_veto_authority`. The authority *retracting itself* still can: a
  Federal Register delisting is a real deny.
- **an old deny permanently suppressing a newer affirmation** —
  `deny_may_be_older_than_affirm`. R06 RECENCY sits near last and is never
  reached once a value is out of contention, so without this the refutation
  is permanent.
- **three stale directories beating one current source** —
  `corroboration_horizon_days`. Applied to *ranking* only; the honest full
  family count is still what the row reports, so I6 and `support_status` are
  unaffected.

**A blocked deny is not discarded.** It is written to the conflict table as
`R01-BLOCKED` with the reason named, and it wins the day its source gains
authority over the predicate.

### R08 UNCONTESTED, and what it replaced

The resolver labelled a lone uncontested value `R02 AUTHORITY` when its one
source happened to be an authority and `R04 TIER` otherwise. Both read as
though a contest had been won. Measured after the change:

```
R00 MULTI_VALUED_NO_CONTEST  23,554
R08 UNCONTESTED               8,975      <- every single-valued fact in Cedar
R01 DENY_VETO                    22
R02..R07                          0
```

**Every single-valued fact in Cedar is uncontested.** That was always true —
the previous labels hid it behind rule names. What the one piece of evidence
is worth is carried by `support_status`, which is the field built to carry it.

### Source-row conservation

Every row of every harvested table now lands in exactly one **named** bucket
in `data/clean/cedar_harvest_conservation.csv`. Invariant **I13** fails the
build if `rows_in != sum(dispositions)`, and refuses a reason of `other`,
`unknown`, `misc` or `n/a` by name. Measured on the first run:

```
83,676 source rows read      0 UNACCOUNTED     25,434 rejected, all named
```

The number the accounting surfaced immediately:

| source | rows in | emitted | named rejection |
|---|---:|---:|---|
| identifier ledger (links) | 20,577 | 8,088 | **12,489 have no `cedar_uid`** |
| identifier ledger (registration attrs) | 20,577 | 7,753 | 12,489 no uid; 332 tier X; 3 no usable value |
| FR roster | 575 | 563 | 5 see-instead pointers, 4 unmatched, **3 non-government class** |
| gaming claims | 113 | 10 | 71 not a Native entity, 32 already refused in source |

**60.7% of the identifier ledger never reaches the assertion layer**, and
until this table existed nothing counted it.

### The Federal Register cannot name a corporation — I14

Found live by workstream A, and it is review finding F1 arriving by a route
no existing guard could see. Three ANCSA village **corporations** carried
`entity.is_federally_recognized = yes` at tier A with
`support_status = authoritative` and `winning_source = fr_tribal_list`:

```
CE-000AW-TW  The English Bay Corporation
CE-000BP-VP  Russian Mission Native Corporation
CE-000CB-YK  St. Mary's Native Corporation
```

The FR **government** name had been written onto the corporation's spine row
as an alias, so `503.resolve()` returned it **uniquely** — no ambiguity, so
the gov-class tiebreak never ran, no conflict row was written, and nothing in
the pipeline could see it. Cedar was attesting that a federal authority
vouched for a claim that authority never made.

Two fixes and one invariant:

1. `harvest_fr_roster` refuses any match whose spine class is not a
   government class, however confidently the name matched. **3 refused.**
2. `harvest_spine` refuses the `fr_official_name` column on a non-government
   row. There is no honest source to assert it under, so it is refused and
   named rather than re-labelled — re-labelling would be inventing
   provenance to keep a value. **6 refused**, including
   `ANVC-ELIMXX-00: Native Village of Elim` and
   `ITO-BRSTL1-00: Bristol Bay Housing Authority`.
3. **I14**: no `entity.is_federally_recognized = yes` may stand on a
   non-government class, **and** no assertion citing `fr_tribal_list` may
   attach to one. The second clause exists because the first would have
   missed the official-name route entirely.

The underlying mechanism was in `503.build_index`: alias candidates were
added as `(tid, r.get("entity_class", ""))` from `entity_aliases.csv`, **which
has no `entity_class` column**, so every alias-sourced candidate arrived
class-less and no class guard could ever fire on one. The class now comes
from the spine, keyed by `tribe_id`. `Native Village of Elim` resolves again:

```
before  AMBIGUOUS_EXACT
after   AKNF-NVELIM-00-BERSTR-KAWRAK   "exact normalized, unique among government-class"
```

Resolved facts fell **32,551 → 32,545**: 9 facts wearing Federal Register
authority that the Federal Register never issued.

### Invariants added this pass

| | |
|---|---|
| **I11** | no deny may veto a value its predicate's policy protects |
| **I12** | every declared policy governs something (warning) |
| **I13** | source-row conservation, with named reasons only |
| **I14** | federal recognition, and FR-sourced facts, only on governments |

Each is proven by a fixture that injects the violation, shows `verify` exits
1, restores, and shows it exits 0 — `review/fixtures_D/`.

---

## The F1 rollout and the second evidence family — the 2026-08-31 pass

*Workstream F. Two changes to one file: the Federal Register harvest stops
resolving entities itself, and the IRS becomes the first source that can
disagree with the spine about the same thing. Every number below is measured
from the live tables.*

### The roster harvest now consumes the link layer

`harvest_fr_roster` used to call `503.resolve()` and emit onto whatever came
back. ADR-001 split the source's claim from Cedar's match into two tables in
`data/spine/`; until this pass **nothing consumed them**. It does now:

```
cedar_source_records.csv        what the record SAYS   -> the facts
cedar_source_record_links.csv   which entity it MEANS  -> the match
```

An assertion is emitted only from a link with `link_role = identifies` and
`link_status ∈ (verified, proposed)`. Every other record lands in a named
bucket in `cedar_harvest_conservation.csv`, at the grain of the source-record
node rather than the raw roster row.

| | before | after |
|---|---:|---:|
| roster records that produced facts | 563 | **566** |
| refused, `cross_reference` pointer (not a listing) | 5 *(unnamed `continue`)* | 5 |
| refused, `contested` — >1 eligible candidate, nothing accepted | 4 *(as "did not match")* | 3 |
| refused, `unresolved` — no eligible Cedar entity | — | 1 |
| refused at harvest on non-government class | 3 | **0** — the link layer denies them first |
| facts lost | — | **0** |

**+3 records, 0 lost, 0 repointed.** The three gained are the ones the class
guard had to refuse before, because the only match on offer was an ANCSA
corporation. The link layer's class-restricted retry recovers the government
the roster is actually naming, so the fact lands on the right entity instead
of being dropped:

| record | before | after |
|---|---|---|
| `Algaaciq Native Village (St. Mary's)` | refused (ANV **Corporation**) | `CE-0000B-2K` Fed. rec. AK Native Village |
| `Native Village of Chuathbaluk (Russian Mission…)` | refused (ANV **Corporation**) | `CE-00017-FZ` Fed. rec. AK Native Village |
| `Native Village of Nanwalek (aka English Bay)` | refused (ANV **Corporation**) | `CE-0003Q-SF` Fed. rec. AK Native Village |

**The nine wrong facts stay gone.** Re-checked on every run and by fixture:
all five ANCSA corporations that ever carried a roster fact
(`CE-000AW-TW`, `CE-000BP-VP`, `CE-000CB-YK`, `CE-0008S-YH`, `CE-000BZ-HQ`)
hold **0** `fr_tribal_list` assertions and **0** resolved recognition or
official-name facts, and **0** roster-sourced assertions in the whole store
sit on a non-government class.

**A defect the rewiring surfaced.** `cedar_source_record_links.csv` on disk
had been built before workstream D repaired `503.build_index`, and a re-run
was no longer byte-identical — the layer's own regenerability claim had
quietly stopped being true. Rebuilt (`514 all --apply`, `verify` and all 13
fixtures green), and one record changed answer:

```
Delaware Tribe of Indians   proposed -> CE-00142-4V      became CONTESTED
```

The cause is in `data/clean/entity_aliases.csv`, not in either script:
**`Delaware Tribe of Indians` is carried as a CAGE-derived legal alias of
`CE-00141-Y2` Delaware *Nation***. They are two different federally
recognized tribes. With the class field repaired, both candidates are now
government-class, the gov-class tiebreak can no longer separate them, and
`503` returns `AMBIGUOUS_EXACT`. The honest outcome is a contested record with
both candidates kept; the fix is to withdraw the alias, which is not this
file's to make. Filed in the handoff.

### The IRS, and the grain decision it forced

`LR_IRS` had been in the lineage tree since the layer was built and asserted
almost nothing: an EIN and the legal name copied out of Cedar's own ledger.
It is a real second family — its root derives from nothing, so an IRS address
agreeing with the spine is not an echo.

**An IRS filing address belongs to the FILING ORGANISATION.** Whether that is
a fact about the Cedar entity depends entirely on what the entity is, so the
decision is made **per class and written into the code** with its reason:

| grain | classes | predicate |
|---|---|---|
| **entity** | Tribal College or University · Native CDFI · Native Financial Institution · Urban Indian Organization · Intertribal Organization · Native Hawaiian Organization · Federal-level self-governance consortium | `entity.state`, `entity.city` |
| **registration** | everything else — tribes, AK village governments, state-recognized tribes, ANCSA corporations, constituency entities, BIE schools | `entity.registration_state`, `entity.registration_city`, qualified `EIN:<ein>` |

A tribe is a government; a government does not file a Form 990. The EIN bound
to one in Cedar's ledger belongs to *some organisation that files* — and the
live data says exactly that. EIN `16015647` on the Penobscot Nation is
**`PENOBSCOT MARINE MUSEUM`**; EIN `391795874` on the Rosebud Sioux Tribe of
South Dakota is **`ROSEBUD INC` of Cambridge, WISCONSIN**. Asserting either as
`entity.state` is the Alaska-villages-moved-to-Virginia mistake arriving from
a second source, and `entity.legal_business_name` is therefore *always*
registration grade too — collapsing filed names onto the entity is what
manufactured the 36 phantom corroborations F7 removed.

**The class rule is necessary and not sufficient.** Three of fifteen
tribal-college EIN links point at a *different organisation*, so an
entity-grade fact additionally requires the **filed name to identify the
entity** — equal to its canonical name or a recorded alias after folding
corporate suffixes, and distinctive (≥2 tokens, ≥14 folded characters,
because `ROSEBUD` matched a canonical name exactly and is a Wisconsin
company). That test is not entity resolution: the EIN→entity link is read
from Cedar's ledger and never made here. It answers the different question of
whether the filer and the entity are **one legal person**, which is what the
grain turns on.

Two link routes, both read, neither invented here:

1. `cedar_identifier_ledger_final.csv`, EIN rows at tier ≠ X — Cedar's
   adjudicated register. Tier X is a refutation of the link, so the address
   filed under it cannot describe the entity. **319 rows excluded on that
   ground alone.**
2. `np_orgs.csv`'s own `cedar_uid`. Not adjudicated in the ledger, so used
   **only** where the strongest guard also passes — self-filing class *and*
   filed-name identity — and never for a registration-grade fact.

`tribal_irs990_verified_strict.csv` is read, measured and **emits nothing**:
1,090 of 1,090 EINs are already in `np_orgs`, with **0** filed-name and **0**
state differences. It is the same BMF extract, narrowed. Harvesting it would
book one fact twice inside one family — the `LR_CICD` mistake with a different
table — so all 1,090 rows land in a named `ECHO` bucket. The measurement is
the product.

### The first real corroboration numbers

| | before | after |
|---|---:|---:|
| single-valued facts with **more than one source** | **0** | **13** |
| …of those, **AGREE** | — | **13** |
| …of those, **DISAGREE** | — | **0** |
| facts with >1 **independent** evidence family (`corroborated`) | 2 | **4** |
| `legacy_only` | 11,661 | **11,650** |
| `identity_facts_legacy_only` | 4,100 | **4,089** |
| resolved facts | 32,545 | 34,185 |
| conflicts | 0 | 0 |

**Do not read that as a big result.** All 13 are `entity.state`, and only two
reach `corroborated`, because a second source can only *corroborate* when the
first one is a family whose independence we can vouch for:

```
CE-000W1-JS  Native Hawaiian Organization Charity   HI   elijah_ruling        + irs_bmf
CE-000YE-AY  Makaha Cultural Learning Center        HI   nhoa_member_directory + irs_bmf
```

The other 11 pair the IRS with `unattributed_legacy`, which by design votes
for nothing. They still move — `legacy_only → traceable_single_source` — and
that is the whole of the 11-row fall in the exposure metric. **Eleven rows of
a 4,100-row debt is a demonstration, not a payment.**

The IRS also added **38 `entity.state` and 51 `entity.city` facts where Cedar
had none at all** — mostly intertribal organisations, which had no state in
the spine. Coverage, not corroboration, and counted separately for that
reason.

### What actually disagreed — and it is not the addresses

Zero disagreements at entity grain is a consequence of the guards, not of the
data being clean. The disagreements the IRS family found are about **links**,
and they are written to `review/irs_ein_link_queue_<date>.csv` for an owner
ruling rather than acted on here — `cedar_identifier_ledger_final.csv` is not
this file's to change.

**6 EIN links on entities that *do* file their own returns, filed under a
different organisation's name:**

| entity | EIN filed as |
|---|---|
| Institute of American Indian Arts | INSTITUTE OF AMERICAN INDIAN ARTS **FOUNDATION** |
| White Earth Tribal and Community College | …COLLEGE **FOUNDATION** |
| Northwest Indian College (**WA**) | NORTHWEST INDIAN COMMUNITY DEVELOPMENT CENTER (**MN**) |
| Nebraska Indian Community College | NEBRASKA INDIAN **CHILD WELFARE COALITION** |
| Council of Athabascan Tribal Governments | ATHABASCAN **FIDDLERS ASSOCIATION** |
| Chugachmiut (**AK**) | **LAKOTA LANGUAGE CONSORTIUM** (**IN**) |

A college's foundation is a real organisation with its own address. Publishing
its city as the college's is the containment error at a smaller scale, and the
name test is what stops it.

**328 live (non-tier-X) EIN links file in a different state from the entity.**
Not a fact conflict — different subjects, and registration grade can never
compete with `entity.state` — but the cheapest wrong-link signal there is:

```
CE-0016E-P7  Lumbee (NC)                        <- NORTH EASTERN BAND OF CHEROKEE (NY)
CE-001AB-RW  Seneca-Cayuga Nation (OK)          <- SENECA NATION LIBRARY (NY)
CE-0019R-1H  St. Croix Chippewa (WI)            <- AKWESASNE BOYS & GIRLS CLUB (NY)
CE-001DJ-HV  Lenape Indian Tribe of Delaware    <- LENAPE VALLEY SOCCER CLUB INC (NJ)
                                                  …and 5 more Lenape Valley
                                                  school-sports charities in NJ
```

`Lenape Valley` is a New Jersey **place name**, and the housing-authority
lesson in `NATIVE_ENTITY_NUANCES.md` — "TUSCARAWAS METROPOLITAN HOUSING is an
Ohio county housing authority" — is the same rule these rows break.

### Invariants added this pass

| | |
|---|---|
| **I16** | an IRS address may be an *entity* fact only on a class that files its own return, and every IRS registration fact must carry its `EIN:` qualifier |
| **I17** | the Federal Register harvest may assert only through an **accepted** source-record link, and every accepted link must produce its assertion |

Both are proven by fixtures that inject the violation, show `verify` exits 1,
restore, and show it exits 0 — `review/fixtures_F/`. I17's second clause is
the old bare `continue` made illegal: an accepted link that emits nothing now
fails the build.

### Open

- **`identity_facts_legacy_only` is gated in the wrong direction.** It sits in
  `62_no_regression_check.MUST_NOT_FALL` under a comment reading *"This may
  only fall"*, and `docs/EXTERNAL_REVIEW_RESPONSE.md` records it as
  MUST_NOT_RISE. As installed, the ratchet fails the build for every payment
  against the exposure the external review asked for — it failed on this one.
  `62` is the integrator's file this pass; filed as a one-line change request.
- **11 of 4,100.** The overlap between the IRS family and the spine's
  identity-critical fields is small and will stay small until a second source
  exists for `entity.class` and `entity.canonical_name`, which is where the
  4,089 actually sit.
- **`entity.city` is still effectively single-sourced.** The spine holds a
  city on 229 of 1,536 rows, so the IRS mostly had nothing to agree or
  disagree with.
- The **Delaware alias** and the **334 IRS link findings** are queue items,
  not corrections. Nothing in `cedar_identifier_ledger_final.csv` or
  `entity_aliases.csv` was changed.
