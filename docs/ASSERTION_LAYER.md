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
data/clean/cedar_assertions.csv        23,310   every claim, with who and why
data/clean/cedar_resolved_facts.csv    22,984   the winner + WHICH RULE decided
data/clean/cedar_fact_conflicts.csv         0   every losing value, kept
data/spine/cedar_source_registry.csv       15   sources + evidence lineage
data/spine/cedar_resolution_rules.csv       8   the rules, as data
```

All three `data/clean` tables are **internal by decision** — see the reason
recorded in `cedar_codebook.INTERNAL_TABLES`, and *Where this is honestly weak*
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

## Where this is honestly weak

Stated plainly, because the mission spec forbids claiming unverified behaviour,
and because these numbers are the actual result of Phase 3.

**Every fact in Cedar rests on exactly one source.** Measured over 8,975
single-valued facts:

| | |
|---|---|
| facts with **more than one source** weighing in | **0** |
| facts with more than one **independent** evidence family | **2** |
| genuine disagreements found | **0** |
| conflicts preserved | **0** |

This is not a bug in the layer and the zeros are not a failure to find
conflicts — they are the measured state of the evidence base, and the layer is
what makes it visible. **An arbitration layer with one source per fact is
correct and idle.** Its value begins the moment a second genuinely independent
source is harvested for the same predicate.

Harvesting the Federal Register roster directly was the first attempt at that
and it demonstrates the model working rather than the corroboration growing:
565 of 575 roster entries matched the spine, and the count of independently
corroborated facts stayed at 2. Correct — a copy of the FR sitting in the spine
and the FR itself are the **same family**. Copying a source into your own table
does not corroborate it. Most warehouses would have scored that as 565 new
confirmations.

Also open:

- **`gaming_source_claims` contributes 0 assertions.** It has no `cedar_uid`
  column and only 10 of its 113 rows have a resolved subject.
- **11,676 of 23,310 assertions are `unattributed_legacy`** — half the store
  carries no evidence because the row it came from never recorded any.
- **Two dead authorities**, above, are declared but never assert.
- **`entity.is_federally_recognized` has no negative case.** The roster asserts
  `yes` for those on it; nothing asserts `no` for those off it.

## Adding a source

1. Add a `LINEAGE_ROOTS` entry. If its content derives from an existing family,
   set `derives_from` — this is the decision that keeps corroboration honest,
   and getting it wrong is how a warehouse ends up believing its own echo.
2. Add a `SOURCES` entry with a `tier_ceiling` and a **narrow** `authority_for`.
   A roster that lists tribes is not an authority on their websites.
3. Write a `harvest_*` function that cites the row it read in `origin_table`.
4. Run `all --apply`. `verify` will tell you if you declared an authority that
   never asserts, or claimed corroboration you do not have.
