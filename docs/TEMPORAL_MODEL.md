# The temporal model — facts stop being timeless, and re-checking stops being impossible

*Built 2026-08-29 as workstream B of the post-review pass. Answers external
review findings **F5** (bitemporality) and **F11** (re-observation), and
implements **ADR-002** and **ADR-003** in `docs/ARCHITECTURE_DECISIONS.md`.
Code: `code/515_temporal.py`. Read with `docs/ASSERTION_LAYER.md` — that
document is about **what** Cedar claims and who said it; this one is about
**when it was true**, **when the source says it started**, and **when we
looked**.*

```
py -3 code/515_temporal.py all --apply     # policy -> facts -> observations -> verify
py -3 code/515_temporal.py asof --apply    # the worked ownership example
py -3 code/515_temporal.py verify          # 10 invariants, read-only, exit 1 on breach
py -3 code/515_temporal.py fixtures        # PROVE each of the 10 fires
```

---

## What was wrong

### F5 — Cedar treats current truth as timeless truth

The review put it as a hypothetical: *a subsidiary owned by ASRC in 2024 and
sold in 2027 has one timeless edge, so either the old owner receives post-sale
awards or the new owner receives pre-sale awards.*

It is not a hypothetical. It has already happened, in a shipped table, and
**Cedar holds the date that corrects it.**

| | |
|---|---|
| UEI `XPRKVQ956WB4` (VISTRONIX) → `CE-00078-KR` (Arctic Slope Regional Corporation) | `cedar_identifier_ledger_final.csv`, `attribution_method = uei_exact`, **no time bounds** |
| ASRC completed the acquisition of Vistronix | **2016-08-16** |
| where that date already lives | `deals_classified.csv` row `ANCSA-2016-004` |
| its source | an ANCSA corporation annual report filed with the Alaska Division of Banking and Securities |
| its `Date_Basis` | *"Completion date stated in the annual report management discussion: 'on August 16, 2016, ASRC Federal completed the acqui…'"* |
| `prime_contracts.csv` transactions on that UEI | **1,249**, worth **$652,068,270**, every one credited to `CE-00078-KR` |
| …in fiscal years that **ended before ASRC bought the company** | **608**, worth **$333,193,135** |

So the failure is not missing data. It is a schema with nowhere to put the data
we already have: a primary-sourced completion date sits forty columns away from
the fact it corrects, and nothing joins them.

The same disease shows up in the **name** field, from a direction that is easy
to miss. `prime_contracts.csv` carries `awardee_name = "ASRC FEDERAL TECHNOLOGY
SOLUTIONS, LLC"` on **all 732 rows** of UEI `CA11RWJPADV6` — *including FY2008*
— because those extracts were pulled in 2026 and USAspending serves the
**current** recipient name for a historical transaction. Cedar's own
2023-vintage extract records the same UEI as `TECHNOLOGY ASSOCIATES INTERNAT…`.
Two vintages, two names, one row. A rename Cedar can already **see** and could
not **store**.

### F11 — an assertion id is content-addressed, so re-checking cannot be recorded

`510_assertions.aid()` hashes `(subject, predicate, object, source, polarity)`.
Re-reading a source that still says the same thing therefore produces **the
same id**. An append-only table then has three options and all three are wrong:
mutate a row, keep a stale date, or write a duplicate id.

`verified_date` compounds it by conflating three different clocks in one cell:

```
when we retrieved it | when the source says it took effect | when it became true
```

Measured: of 32,872 assertions, **11,972 carry a `verified_date` and 20,900 do
not**. In the timeless model those 20,900 are indistinguishable from "never
checked" and from "checked, unchanged, nothing to write." (The assertion count
moved three times during this session — workstream D rebuilds that store — which
is itself a fact this layer had to be designed around; see *Derived rows and
event rows* below.)

---

## What replaced it

Three things, and the split between them is the whole design.

**A claim is immutable and semantic.** Who says what, about whom, from where,
affirming or denying. It never carries a clock reading and its id never moves.
`515` mints claim ids by **importing** `510_assertions.aid()` rather than
copying it, so the two layers cannot drift — and invariant **T4** fails on the
next run if they ever do.

**An observation is an event.** `(claim_id, retrieved_at, source_snapshot,
verifier, result)`. Re-observing appends an event and touches nothing else.

**A temporal fact is a claim plus an interval**, and the interval carries three
clocks in three separate columns, never one:

| column | meaning | may be unknown |
|---|---|---|
| `valid_from` / `valid_to` | when the fact was true **of the world** | **yes**, and usually is |
| `source_effective_date` | when the **source says** it took effect | yes |
| `earliest_observed` / `latest_observed` | when **Cedar saw it** — evidence, never validity | yes |

### The tables

```
data/spine/cedar_temporal_facts.csv    2,867   claims with intervals
data/spine/cedar_observations.csv     35,740   observation events
data/spine/cedar_temporal_policy.csv      10   the conventions, as data
review/temporal_asof_ownership.csv    14,823   the worked example, resolved
```

They live in `data/spine/` beside 510's source and rule registries, for the
same reason: they are Cedar's process, not the world. `data/clean` is the
shipping surface and putting them there would raise
`tables_undocumented_in_codebook` in the 62 gate for no gain to a buyer.

| | |
|---|---:|
| temporal facts | **2,867** |
| …`entity.ultimate_parent_uei` | 1,892 |
| …`entity.parent_uei` | 793 |
| …`entity.ownership_change` (dated deal events) | 182 |
| facts whose `valid_from` is **KNOWN** | **85** |
| facts whose `valid_from` is recorded **UNKNOWN** rather than guessed | **2,782** |
| observations | **35,740** |
| …seeded from the existing claim store | 32,872 |
| …source-file reads behind the temporal facts | 2,867 |
| …live re-checks | 1 |

**85 of 2,867 is the honest number and it is meant to be uncomfortable.** Cedar
knows when 3% of its ownership facts started. The other 97% are recorded as
unknown, with a basis saying *why*, and they are not filled in from an
observation window to make the table look finished.

---

## The rule that shapes every column: never invent a date

`docs/OWNERSHIP_CHANGE_DETECTION.md` already measured the distance between
"when we saw it" and "when it was true":

> **The observed date is not the transaction date.** Because FPDS does not
> update retroactively, the new parent appears only on transactions issued
> after the SAM registration was updated. That lag can be years.

Copying `first_year` into `valid_from` would encode that lag as fact. So the
observation window goes into `earliest_observed` / `latest_observed`, the
validity columns stay empty, and `valid_from_known = 0` says so in a field a
query can filter on. Invariant **T5** makes it impossible to write a date into
a cell flagged unknown, or to claim known with an empty cell — the policy is
enforced by the verifier, not by discipline.

Three places where this rule cost us a date we could easily have taken:

- **2,684 FPDS ownership edges** have a first and last observed fiscal year and
  no validity date at all. Basis:
  `unknown_observation_window_is_not_a_start_date`.
- **37 dated deal rows say "MONTH-LEVEL ONLY" or "Year-level only"** in their
  own `Date_Basis` while carrying a full `YYYY-MM-DD` `Event_Date`, because the
  ledger needs a sortable day. That day is a ledger convention, not a fact
  about the world. Basis: `unknown_source_states_month_or_year_only`, with the
  ledger's date preserved in the `note` and explicitly not promoted.
- **5 rows disclaim their own date in prose.** *"the release states no separate
  closing date"*; *"The CLOSING date was NOT located in any retrieved text and
  is not asserted anywhere in this row."* A keyword match on "closing" reads
  every one of those as a stated closing date. The disclaimer is matched
  **first** and wins. Basis:
  `unknown_source_explicitly_disclaims_the_effective_date`.

That last one is the reason a regex over `Date_Basis` is written the way it is
and commented at length in the code. Careful prose negates, and a classifier
that cannot read a negation turns a source's honesty into our error.

---

## The written policy

Ten conventions, each with the question it answers — *what do we write in the
date cell?* — and each shipped as a row in
`data/spine/cedar_temporal_policy.csv` so it is readable without reading code.

| # | topic | what gets written |
|---|---|---|
| **P01** | **unknown dates** | Empty cell, `*_known = 0`, and a `*_basis` naming why. Never filled from an observation window, a neighbouring interval, or a round number. Enforced by T5. |
| **P02** | **partial / open intervals** | Open ≠ unknown. `open_no_end_recorded` = still present in the most recent vintage of its source. `unknown_last_observed_earlier` = the source stopped mentioning it and we do not know whether it ended. A single NULL would merge two opposite epistemic states. |
| **P03** | **source effective date** | `source_effective_date` holds a date **the source states**. An announcement date is not an effective date: it goes to `announced_date` with basis `announcement_only_effective_date_not_stated`, and `valid_from` stays unknown. A deal announced in December and closed in March has three months of transactions that belong to the seller. |
| **P04** | **historical names** | A rename is a **new interval on the same subject** — never a new subject, never an edit. Both names stay resolvable as-of their own dates. `docs/NATIVE_ENTITY_NUANCES.md` lists six live cases; a 2011 filing is not wrong about 2011. |
| **P05** | **mergers** | Close the absorbed entity's intervals at the stated effective date; open a successor interval on the survivor; add a dated `entity.succeeded_by` fact. The absorbed `subject_id` is **never deleted and never reused**. Repointing historical transactions to the survivor is the timeless model wearing a new hat. |
| **P06** | **splits** | Open an interval on **each** resulting subject at the stated date and close the predecessor's. Where the source does not say which successor took a given asset, the link is left unresolved rather than assigned to the larger one — the same refusal 510's `UNRESOLVED_TIE` makes in the value dimension. |
| **P07** | **successors** | Succession is its own dated fact between two subjects. It is **not** implied by name similarity, a shared identifier, or a shared address. The DUNS→UEI cutover of 2022-04-04 manufactured 37 apparent parent changes against a ~15/year baseline: an identifier event is not a world event. |
| **P08** | **dissolved entities** | Close every open interval at the stated dissolution date and add a dated `entity.dissolved` fact. **The subject row is never deleted** — a dissolved entity still held every contract it held. A tombstone is a fact; a deletion is a lie by omission. With no stated date, P01 applies and nothing is closed. |
| **P09** | **mistaken duplicates** | **Retract, do not time-bound.** A deny claim (510 `polarity = deny`) plus, if it ever shipped, a `cedar_correction_register.csv` entry. Closing an interval says "this was true and then stopped"; a mistaken duplicate was *never* true, and dating its end asserts a world event that did not happen. |
| **P10** | **granularity** | Compare at the **coarsest** granularity either side offers and record which was used. Where a stated date falls inside the query's own span, the answer is `AMBIGUOUS_GRANULARITY`, not a pick. |

---

## The worked ownership example

Ownership, because the failure is easy to reason about, and on real edges from
`data/clean/fpds_uei_edges.csv` (2,901 declared child→parent edges; 2,684 are
ownership, the other 217 are `prime_to_sub` and are named and dropped).

### The chain

```
TECHNOLOGY ASSOCIATES INTERNATIONAL      CA11RWJPADV6
        |  ultimate_parent, observed FY2014-FY2015
        v
VISTRONIX                                XPRKVQ956WB4
        |  ultimate_parent, STATED 2016-08-16 (deal ANCSA-2016-004,
        |  ANCSA annual report, "completion date")
        v
ARCTIC SLOPE REGIONAL CORPORATION        CY16XXPHX213   -> cedar_uid CE-00078-KR
```

All three UEIs currently resolve to `CE-00078-KR` in
`cedar_identifier_ledger_final.csv`, timelessly, for every year they ever
existed.

### Case A — a transaction before a change resolves through owner A; after, through owner B

`CA11RWJPADV6`, predicate `entity.ultimate_parent_uei`. Two temporal facts,
both with **unknown** validity bounds and known observation windows, so the
as-of resolution runs at fiscal-year granularity (P10):

| fiscal year | transactions | obligations | as-of status | resolves to | basis | Cedar ships |
|---|---:|---:|---|---|---|---|
| FY2008–FY2013 | 401 | $110,849,735 | `UNKNOWN_OUTSIDE_EVIDENCE` | — | | `CE-00078-KR` |
| **FY2014** | 28 | $10,936,292 | **`RESOLVED`** | **`XPRKVQ956WB4` Vistronix** | observation_bounded | `CE-00078-KR` |
| **FY2015** | 24 | $486,832 | **`RESOLVED`** | **`XPRKVQ956WB4` Vistronix** | observation_bounded | `CE-00078-KR` |
| FY2016–FY2018 | 7 | $0 | `UNKNOWN_OUTSIDE_EVIDENCE` | — | | `CE-00078-KR` |
| **FY2019** | 3 | −$15,370 | **`RESOLVED`** | **`CY16XXPHX213` ASRC** | observation_bounded | `CE-00078-KR` |
| **FY2022–FY2026** | 269 | $275,743,066 | **`RESOLVED`** | **`CY16XXPHX213` ASRC** | observation_bounded | `CE-00078-KR` |

That is the requirement, met on real data: **FY2015 resolves through owner A
(Vistronix), FY2023 resolves through owner B (ASRC).** And the FY2008–FY2013
block is the finding — **401 transactions and $110,849,735 credited to an
Alaska Native regional corporation for years in which Cedar has no evidence
that it, or anyone, owned the firm.** The temporal layer says
`UNKNOWN_OUTSIDE_EVIDENCE`. The shipped table says `CE-00078-KR`.

### Case B — a stated date, and what it buys

`XPRKVQ956WB4` (Vistronix). Here the curated bridge attaches the deal's stated
completion date to the edge, so `valid_from` is **known**:

| fiscal year | transactions | obligations | as-of status | resolves to | basis |
|---|---:|---:|---|---|---|
| **FY2008–FY2015** | **608** | **$333,193,135** | **`NO_COVERING_FACT`** | — | the stated date rules it out |
| **FY2016** | **75** | **$65,850,795** | **`AMBIGUOUS_GRANULARITY`** | — | 2016-08-16 falls **inside** FY2016 |
| FY2017–FY2026 | 566 | $253,024,340 | `RESOLVED` | `CY16XXPHX213` ASRC | **`stated_by_source`** |

Three different answers, and the middle one is the most important. FY2016 runs
2015-10-01 to 2016-09-30 and the acquisition closed on 2016-08-16. Seventy-five
transactions worth $65,850,795 genuinely **cannot** be assigned to a side from
what Cedar holds, because `prime_contracts.csv` dates transactions to a fiscal
year and nothing finer. Splitting them by any rule would manufacture precision
the source never had. P10 says so, and the resolver returns
`AMBIGUOUS_GRANULARITY` instead of a pick.

### The blast radius, measured

`asof` resolves every `prime_contracts.csv` transaction on every UEI that
carries an ownership fact — one streaming pass over 1,217,768 rows:

```
resolved 622,954 transactions on 2,315 UEIs

  RESOLVED                     498,410 tx    $141,044,709,858
  UNKNOWN_OUTSIDE_EVIDENCE      72,369 tx     $22,917,136,552
  AMBIGUOUS_OVERLAP             41,991 tx     $10,504,273,378
  NO_FACT_ON_SUBJECT             9,501 tx      $2,938,917,719
  NO_COVERING_FACT                 608 tx       $333,193,135
  AMBIGUOUS_GRANULARITY             75 tx        $65,850,795

  as-of owner DISAGREES with the shipped cedar_uid
                                 9,402 tx      $2,119,742,435
  Cedar ships an owner but the temporal layer cannot confirm one at that date
                               110,705 tx     $32,147,669,996
```

**Integrator reconciliation, 2026-08-30.** An independent recount over the
shipped artifact gave 124,544 tx / $36.76B and was briefly recorded as a
discrepancy against the 110,705 / $32.15B above. Both are right at different
scopes: 124,544 = ALL non-RESOLVED; of those, 110,705 ship an owner the layer
cannot confirm ($32.1B), **9,402 ship an owner the layer actively CONTRADICTS
($2.1B — the sharpest bucket)**, and ~4,437 ship no owner at all (~$2.5B, no
exposure). 110,705 + 9,402 + 4,437 = 124,544. Discrepancy closed.

Read the last line carefully. **$32.1 billion of obligations are attributed to
an owner Cedar cannot demonstrate held the firm on the transaction date.**
Those are not 110,705 errors — most of them are probably right. They are the
size of the question the timeless model was answering by assumption, made
countable for the first time.

`AMBIGUOUS_OVERLAP` at 41,991 transactions is its own queue: two declared
owners observed in the same fiscal year for one child. Verify reports the same
thing from the other side as warning **T2w**, at **176 fact pairs**. Overlapping
*observation* windows are expected — declaration lag guarantees them — which is
why T2w warns and only a **provable** overlap of two closed intervals fails.

### One contradiction the layer surfaced and did not resolve

`fpds_uei_edges.csv` carries a `parent_uei` edge `XPRKVQ956WB4 → CY16XXPHX213`
with `first_year = last_year = 2014` and **`n_observations = 1`** — one FPDS
record declaring ASRC as Vistronix's parent two years before the acquisition
closed. Declaration lag runs forwards, not backwards, so that single record
contradicts a primary-sourced completion date. It is left standing, on a
different predicate, unresolved, and named here. Inventing a reconciliation
would be the same error in a new place.

---

## Re-observation, demonstrated

The F11 fix, run for real on the curated Vistronix claim:

```
$ md5sum data/spine/cedar_temporal_facts.csv
9b2b287bef47f956b38b047186c82fd8

$ py -3 code/515_temporal.py reobserve --claim CA-950FB65FECDB1655 \
      --result confirmed --verifier "workstream-B 2026-08-29" \
      --snapshot "https://portal.akdbsstar.us/..." --snapshot-kind url \
      --detail "re-read the ANCSA annual report page cited by ANCSA-2016-004;
                still states completion on August 16, 2016" --apply
  reobserve  claim_id CA-950FB65FECDB1655 UNCHANGED; observation
             OBS-d851ec0c58b54242 appended (2 observations now stand behind
             this claim)

$ (the same command again)
  reobserve  an identical observation (OBS-d851ec0c58b54242) is already on
             file - same claim, same clock reading, same snapshot, same
             verifier, same result. Nothing appended.

$ md5sum data/spine/cedar_temporal_facts.csv
9b2b287bef47f956b38b047186c82fd8      <- byte-identical
```

The claim id did not move. The claim table did not change by one byte. A second
observation exists. A third, identical one is refused rather than duplicated,
because an observation id is content-addressed over
`(claim_id, layer, retrieved_at, snapshot, verifier, result)` — a genuinely
new re-check has a new clock reading and gets a new id.

A rebuild does not undo it. The build is idempotent by construction —
content-addressed ids — not by an "already done" short-circuit, and a re-run
reports `35,740 observation events (35,739 derived from the claim stores, 1
retrieval events carried forward)`.

### Derived rows and event rows

The observation table holds two kinds of row and they are treated differently
on purpose.

A **derived** observation (`seeded_from_claim_store`, `source_file_read`) is a
*projection* of a claim store this script does not own. It is rebuilt from that
store on every run.

An **event** observation — `live_retrieval` from `reobserve`, and anything else
a person or process records — says that someone went and looked. It is never
rebuilt and never dropped, because deleting the record of a retrieval is
deleting evidence.

That distinction was not designed in the abstract. `510_assertions.py` belongs
to workstream D and was rebuilt repeatedly during this pass: between two runs
of `verify` it moved **four** `entity.is_federally_recognized` claim ids while
the row count stayed at 32,878, and a later rebuild moved **15,291**. Every
seeded observation pointing at an old id was instantly a dangling reference.

So the rule is: derived rows are regenerated, and **every one dropped is
counted and named** —

```
DROPPED 10 stale DERIVED observation(s) whose claim id no longer exists in the
store they project - the claim was re-keyed or withdrawn upstream:
OBS-911e90a64d1e5783->CA-472C8E2659BCF1BF (CE-000CB-YK entity.fr_official_name);
OBS-ca119b0aa6d8c499->CA-4F8AEFB14998CEC6 (CE-000AW-TW entity.is_federally_recognized); ...
```

— and **T3 splits to match**. A *retrieval* observation pointing at a
nonexistent claim is a hard FAIL: we hold a record of looking at nothing. A
*derived* one is a loud warning (`T3s`) that names its remedy and self-heals on
the next `observe --apply`, because a hard fail there would make this gate red
for an edit made in another workstream's file and unfixable except by
re-running the build — the "gate that cannot be cleared" problem 62 had to
solve for handoffs, in a new place.

**This is also an unplanned live demonstration of why the layer exists.** A
rebuild silently re-keyed claims; the row count did not move; nothing in the
assertion layer noticed. The observation layer noticed, because a claim id is a
reference and references can dangle.

---

## The invariants, and the proof that each one fires

Ten invariants. `verify` is read-only and exits 1 on any breach.

| | catches |
|---|---|
| **T1** | an interval whose `valid_to` precedes its `valid_from` |
| **T2** | two **provably** overlapping closed intervals on one single-valued fact (`T2w` warns on overlapping *observation* windows, which are expected) |
| **T3** | a **retrieval** observation referencing a claim that exists in neither `cedar_assertions.csv` nor `cedar_temporal_facts.csv` — a record of looking at nothing. The same dangling reference from a *derived* row warns as `T3s` and self-heals (see *Derived rows and event rows*). |
| **T4** | an id that does not recompute from its own row, or a duplicate id — including a `claim_id` that no longer recomputes under `510_assertions.aid()`, which is how **drift from the assertion layer** gets caught |
| **T5** | a date written into a cell flagged unknown, a `*_known = 1` with an empty cell, or a non-ISO date. **This is P01 made unbreakable.** |
| **T6** | a boundary flagged `stated_by_source` that cites no statement |
| **T7** | a clock reading in the future — the review caught exactly this in our own packet header, so it gets an invariant |
| **T8** | a `claim_id` carrying more than one semantic core, i.e. a claim **mutated** instead of re-observed; observations of one claim disagreeing about what it says; a `result` outside the vocabulary. **This is F11's invariant.** |
| **T9** | an evidence window running backwards |
| **T10** | a hand-curated dated boundary that no longer matches the deal row or the edges it cites |

A check nobody has seen fail is a claim, not a check. `fixtures` injects one
violating row per invariant into the real table, runs `verify`, asserts **that
specific invariant** fired, restores the bytes in a `finally`, and re-verifies:

```
$ py -3 code/515_temporal.py fixtures
  fixtures     baseline verify exit 0
    T1   PASS  injected: exit 1, T1 fired=yes; restored: exit 0
    T2   PASS  injected: exit 1, T2 fired=yes; restored: exit 0
    T3   PASS  injected: exit 1, T3 fired=yes; restored: exit 0
    T4   PASS  injected: exit 1, T4 fired=yes; restored: exit 0
    T5   PASS  injected: exit 1, T5 fired=yes; restored: exit 0
    T6   PASS  injected: exit 1, T6 fired=yes; restored: exit 0
    T7   PASS  injected: exit 1, T7 fired=yes; restored: exit 0
    T8   PASS  injected: exit 1, T8 fired=yes; restored: exit 0
    T9   PASS  injected: exit 1, T9 fired=yes; restored: exit 0
    T10  PASS  injected: exit 1, T10 fired=yes; restored: exit 0
  fixtures     all 10 invariants fire on injection and clear on restore;
               tables restored, verify exit 0
```

Checking the **exit code alone** is not enough — an injection that trips some
*other* invariant would still exit 1 and look like a pass. The fixture asserts
the named invariant appears in the failure list. T10's fixture drifts the
curated constant **in memory only**; it never writes to
`data/clean/deals_classified.csv`, which belongs to another workstream, because
a fixture that can corrupt a shipped table if the process dies is not a safe
fixture.

---

## Where this stands, honestly

Stated plainly, because the mission spec forbids claiming unverified behaviour.

**The real data lacks a dated ownership change linked to the ownership graph —
and that is itself a finding.** Cedar holds:

- **189 dated ownership events** in `deals_classified.csv` (`Acquisition` /
  `Divestiture`), 185 with an `Event_Date`, 84 of them with a genuinely stated
  effective or closing date;
- **2,684 UEI ownership edges** in `fpds_uei_edges.csv`;
- and **nothing that joins them.**

A strict automated bridge was built and **rejected on measurement**: matching a
deal's `cedar_uid` to the ledger's `cedar_uid` for an edge's *parent* UEI, plus
a ≥6-character distinctive token of the edge's *child* name appearing in the
deal title, produced **480 candidate links**, and inspection showed the token
was matching the **acquirer's tribal name**, not the acquired firm — `SEMINOLE`
in a Seminole Tribe deal title matching `SEMINOLE NATION OF OKLAHOMA` as a
"child". Precision was unacceptable and the rule is not used. Joining these two
tables needs the entity-resolution layer workstream A is building
(`refers_to` as a first-class, evidenced link), not a name matcher.

So the bridge is curated **one row at a time, each with its citation**, exactly
as this project handles rulings. Today it holds **one** row —
`TOB-2016-ASRC-VISTRONIX` — and T10 re-checks it against the deal row and the
edges on every run so a hand-made link cannot rot silently. The single row is
enough to demonstrate the stated-date path end to end; it is not enough to
claim coverage, and this document does not.

Also open:

- **0 of 2,867 temporal-fact claim ids exist in `cedar_assertions.csv`.** The
  ownership graph lives at **UEI grain** and 510 harvests at **cedar_uid
  grain**, so the claim ids are minted with the same recipe over a namespaced
  subject (`uei:<UEI>`) and are flagged `claim_in_assertion_layer = 0`. They
  should become first-class assertions; that is a change inside
  `510_assertions.py`, which workstream B does not own. Requested in the
  handoff.
- **`510_assertions.SOURCES` has no id for a state regulatory filing.** The
  ANCSA annual reports on the Alaska STAR portal are mapped to
  `org_self_statement` (LR_SELF) — defensible, since an annual report *is* the
  entity's own statement, but it undersells a filing made under a state
  reporting obligation. 127 facts here carry that source id. Requested in the
  handoff.
- **78 of 2,684 ownership edges name a blocklisted parent.** They are kept,
  with the blocklist reason carried into the fact's `note`, and they are not
  excluded from as-of resolution. Deciding whether a blocklisted parent may win
  an as-of query is an owner ruling, not a coding choice.
- **`AMBIGUOUS_OVERLAP` on 41,991 transactions / $10.5B** and **176 fact pairs
  with overlapping observation windows** are a queue, not a result. Each needs
  either a stated date or an owner ruling.
- **The FY2016 straddle is not solvable in this layer.** It needs
  transaction-level action dates, which `prime_contracts.csv` does not carry.
  `action_date` exists in the raw USAspending extracts; promoting it is a
  change to the contracts build, which workstream B does not own.
- **One live re-observation exists.** The re-observation *machinery* is proven;
  a re-observation *cadence* — what gets re-checked, how often, by what — is not
  built. `docs/REFRESH_CADENCE.md` is where that belongs.

## Adding a temporal fact

1. Decide what the source actually **states**. If it states an effective or
   closing date, that date is `valid_from` with basis `stated_by_source`, and
   `source_effective_date` and `effective_date_stated_by` must both be filled —
   T6 refuses the claim otherwise.
2. If it does not, leave the date cell **empty**, set `*_known = 0`, and pick
   the basis that says why. There are five in use and adding a sixth is
   cheaper than inventing a date. T5 enforces this.
3. Put the evidence window in `earliest_observed` / `latest_observed` with its
   granularity. It is never validity.
4. Run `all --apply`, then `fixtures`. `verify` will tell you if an id stopped
   recomputing, if a claim was mutated instead of re-observed, or if a curated
   boundary drifted from the row it cites.

---

## Requests recorded for the integrator

Workstream B owns `code/515_temporal.py`, `docs/TEMPORAL_MODEL.md` and the
three tables above, and edited nothing else. Four changes are needed in files
it does not own; none was made.

1. **`510_assertions.py` — harvest the UEI ownership graph as assertions.**
   All 2,867 temporal-fact claim ids carry `claim_in_assertion_layer = 0`
   because 510 harvests at `cedar_uid` grain and the ownership graph lives at
   **UEI** grain, which is the grain a transaction actually joins on. 515
   mints those claim ids with 510's own recipe over a namespaced subject
   (`uei:<UEI>`), so a `harvest_uei_edges` in 510 would produce **the same
   ids** and the two layers would meet with no migration. Owner: workstream D.

2. **`510_assertions.SOURCES` — add a source id for a state regulatory
   filing.** The ANCSA annual reports on the Alaska STAR portal are currently
   mapped to `org_self_statement` (LR_SELF). Defensible — an annual report *is*
   the entity's own statement — but it undersells a filing made under a state
   reporting obligation, and 127 facts here carry that id. Owner: workstream D.

3. **The contracts build — promote `action_date` into `prime_contracts.csv`.**
   The table dates transactions to a fiscal year and nothing finer, which is
   the sole cause of `AMBIGUOUS_GRANULARITY` (75 transactions, $65,850,795 on
   the Vistronix subject alone). `action_date` exists in the raw USAspending
   extracts. Owner: whoever owns `40_build_prime_contracts.py`.

4. **An owner ruling on blocklisted parents in as-of resolution.** 78 of 2,684
   ownership edges name a blocklisted parent. They are kept, with the blocklist
   reason carried into the fact's `note`, and they are **not** excluded from
   as-of resolution. Whether a blocklisted parent may win an as-of query is a
   judgement, not a coding choice.
