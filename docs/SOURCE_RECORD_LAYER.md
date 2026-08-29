# The source-record layer — authority stops crossing the match

*Built 2026-08-29 as workstream A of the post-review pass. Implements
`docs/ARCHITECTURE_DECISIONS.md` ADR-001 and closes external review finding
**F1**, the deepest in that review. Code: `code/514_source_records.py`. Read
with `docs/ASSERTION_LAYER.md` (what Cedar claims) and
`docs/IDENTIFIER_STANDARD.md` (who an entity is) — this document is about the
join between them, which until now was not written down anywhere.*

```
py -3 code/514_source_records.py all --apply     # records -> links -> verify
py -3 code/514_source_records.py verify          # 10 invariants, exit 1 on breach
py -3 code/514_source_records.py fixtures        # PROVE each invariant fires
py -3 code/514_source_records.py determinism     # PROVE a re-run re-mints nothing
py -3 code/514_source_records.py audit           # before/after vs the old path
```

---

## What was wrong

`510_assertions.py` starts *after* a source row has been resolved to a
`cedar_uid`. Its Federal Register harvester, in full:

```python
tid, how = mod.resolve(name, exact, gov, state_of)
if not tid:
    continue                                        # <- leaves no trace
uid = tid_uid.get(tid, "")
_emit(out, uid, "entity.fr_official_name", name, "fr_tribal_list", tier="A")
_emit(out, uid, "entity.is_federally_recognized", "yes", "fr_tribal_list", tier="A")
```

Two different claims leave that function as one row:

```
the Federal Register says this line is a federally recognized entity   <- the FR's claim
this Federal Register line means cedar_uid CE-xxxxx-xx                 <- OUR claim
```

`fr_tribal_list` is declared `authority_for` both predicates, so R02 AUTHORITY
publishes the fused result at tier A with `support_status = authoritative`.
**The Federal Register is authoritative about its own line and has said
nothing whatever about our uid.** A bad match is laundered into an
authoritative Cedar fact, and the store cannot refute the wrong half without
also refuting the right one.

The reviewer's words: *"an authoritative source fact can become a wrong
authoritative Cedar fact via a bad match, because authority attaches after
resolution."*

### It had already happened, in the shipped resolved view

Measured against the live tables (`514 audit` reprints all of this):

| | |
|---|---:|
| `entity.fr_official_name` facts sourced to `fr_tribal_list` | 569 |
| …**on an entity class the FR roster cannot name** | **6** |
| …whose value appears **nowhere in the roster file at all** | **2** |
| `entity.is_federally_recognized` facts from the roster harvest | 565 |
| …**asserted of an entity class that cannot hold it** | **3** |

The three are the sharpest, because `entity.is_federally_recognized` reaches
the store **only** through `harvest_fr_roster` — the exact code path F1 names.
They are not legacy spine residue:

```
CE-000AW-TW  The English Bay Corporation          Alaska Native Village Corporation
CE-000BP-VP  Russian Mission Native Corporation   Alaska Native Village Corporation
CE-000CB-YK  St. Mary's Native Corporation        Alaska Native Village Corporation
```

`support_status = authoritative`, `winning_tier = A`. **Cedar told a buyer,
with the Federal Register's authority behind it, that three ANCSA village
corporations are federally recognized tribes.** They are corporations
chartered under ANCSA; the distinction between an ANCSA corporation and a
tribal government is the first thing `docs/NATIVE_ENTITY_NUANCES.md`
establishes and the thing this dataset is bought for.

Two more (`CE-0008S-YH` Elim Native Corporation, `CE-000BZ-HQ` Shishmaref
Native Corporation) carry the FR *official name* but escaped the recognition
assertion only by luck — 503 happened to return `AMBIGUOUS` on those two
names, so `continue` fired.

### How the wrong match was made

Not by a fuzzy matcher being sloppy. By the FR string having been written
into the ANCSA corporation's spine row, as both `fr_official_name` and an
alias:

```
CE-0003Q-SF  AKNF-NANWLK-...  Federally recognized Alaska Native Village
             canonical: Nanwalek        aliases: English Bay | Nanwalek | Native Village of Nanwalek
CE-000AW-TW  ANVC-NGLSHB-00   Alaska Native Village Corporation
             canonical: The English Bay Corporation
             fr_official_name: Native Village of Nanwalek (aka English Bay)
             aliases: The English Bay Corporation | Native Village of Nanwalek (aka English Bay)
```

`503.resolve("Native Village of Nanwalek (aka English Bay)")` therefore returns
the **corporation**, *uniquely* — `exact normalized name/alias, unique`. There
was no ambiguity to warn anyone, no coin flip, no conflict row. The old model
had no place to record "the name matches but the *kind of thing* is wrong",
because it had no row for the match at all.

---

## What replaced it

A source record is a **node**. What it says and who it means are two tables.

```
source record R  says      official_name = N        <- authority applies HERE
source record R  says      recognition   = yes      <- authority applies HERE
source record R  refers_to candidate uid G          <- authority NEVER applies
```

```
data/spine/cedar_source_records.csv         575   one node per source row, verbatim
data/spine/cedar_source_record_links.csv    585   refers_to, evidenced and refutable
```

**The node table has no `cedar_uid` column.** That is the design, not an
omission: a source record cannot mention a Cedar entity, so there is nowhere
for a match to hide inside a statement of fact. Every uid in this layer lives
on a link row that carries its own route, its own evidence, its own candidate
set, its own status and its own `authority_basis`.

Both files live in `data/spine/` beside `cedar_source_registry.csv` and
`cedar_resolution_rules.csv`, which 510 writes there for the same reason: they
are identity infrastructure, not product. Like those two they are content and
so are untracked by git per `.gitignore`'s stated rule — regenerable from
`code/514_source_records.py` plus `data/clean/fr_recognized_entities.csv`, and
byte-identical on a re-run (proved below).

### The link statuses

| status | meaning | count |
|---|---|---:|
| `verified` | a researched human equivalence with a written reason | 1 |
| `proposed` | a machine match. Not confirmed by anything | 570 |
| `contested` | more than one eligible candidate, **nothing accepted** | 7 |
| `denied` | a refutation of a mapping, kept in the table by name | 5 |
| `unresolved` | no eligible Cedar entity; recorded, not dropped | 2 |

Only `verified` and `proposed` are **accepted** — the statuses a consumer may
join on: 571 of the 585 link rows, 570 of them machine proposals that say so.
Calling them "verified" is what the old model did implicitly by having no word
for the difference.

### The link roles

`identifies` — this record names this entity.
`cross_reference` — this record is a *pointer printed in the roster* to that
entity. The FR prints `Arctic Village (See Native Village of Venetie Tribal
Government)`. That line refers to Venetie and asserts nothing about a tribe
called Arctic Village. The old harvest skipped all five such rows at
`continue`; here they are links with a role that forbids them carrying the
roster's facts.

### The field that did not exist before: dataset class eligibility

```python
"fr_recognized_entities": dict(
    eligible_entity_classes=("Federally recognized tribe",
                             "Federally recognized Alaska Native Village",
                             "Federal-level constituency entity",
                             "Federal-level self-governance consortium"),
    ...)
```

**The Federal Register's list of federally recognized tribal entities
enumerates governments.** It cannot list an ANCSA corporation, a school or a
nonprofit. That is a property of the *dataset* — not of the resolver, not of
the entity — and until there was a link row there was nowhere to put it.

With it, `Native Village of Elim` stops being an unresolvable ambiguity: the
corporation is refuted **by name, with a reason, as a row that stays**, and
the village government carries the surviving proposal.

```
denied    CE-0008S-YH  "Alaska Native Village Corporation"
          REFUTED: The Federal Register list of federally recognized tribal
          entities enumerates GOVERNMENTS...
proposed  CE-0004G-MG  Elim IRA
          503 returned AMBIGUOUS_EXACT:...; the dataset's class rule
          eliminated 1 candidate, leaving one
```

### The retry, and a defect in a file this workstream does not own

For Nanwalek, Algaaciq and Chuathbaluk the unrestricted resolve is *unique*
and *wrong*, so eliminating the corporation leaves nothing. The layer then
re-runs **503's own `resolve()`** over an index narrowed to the eligible
classes — the same algorithm, the same researched equivalences, the same
guards, a smaller universe — and recovers the correct village government. It
is adopted only when it lands on an eligible entity and never overrules a
unique eligible hit.

Narrowing the index requires repairing a class field, and that exposed a
defect in `503_identity.py`:

```python
# build_index(), reading data/clean/entity_aliases.csv
exact.setdefault(k, set()).add((tid, r.get("entity_class", "")))
```

`entity_aliases.csv` **has no `entity_class` column.** Every alias-sourced
candidate therefore arrives class-less, and the gov-class tiebreak inside
`resolve` —

```python
g = {t for t, cl in c if cl in GOV}
if len(g) == 1:
    return next(iter(g)), "exact normalized, unique among government-class"
```

— can never fire on one. "Native Village of Elim" is an *alias* of the IRA, so
the one rule that would have decided it correctly never ran, and the resolve
fell through to `AMBIGUOUS_EXACT`. 514 repairs the class from the spine for
its own restricted index. **`503_identity.py` is workstream D's file this pass
and was not edited**; the fix is filed as a change request in the handoff.

---

## The before/after audit

`py -3 code/514_source_records.py audit`

```
  source rows                                    575
  BEFORE  uid links made by 510 harvest_fr_roster     565
  BEFORE  rows that produced NOTHING and no row        10
  AFTER   source-record nodes                         575
  AFTER   accepted `identifies` links                 567
  AFTER   accepted `cross_reference` links              4
  AFTER   denied (refuted) mappings                     5
  AFTER   contested (>1 eligible candidate)             7
  AFTER   unresolved, recorded as such                  2
```

Every source row is now represented. Under the old path 10 rows produced
nothing at all — not a null, not a queue entry, nothing — and a buyer could
not tell an unmatched row from a row that was never there.

### Where they disagree

Disagreements are findings, and all of them are in the new layer's favour.

**0 links were lost.** Nothing the old path matched is dropped.

**2 accepted here, invisible before** — the two the resolver called ambiguous:

```
CE-0004G-MG  'Native Village of Elim'          (Elim IRA)
CE-0005X-75  'Native Village of Shishmaref'    (Shishmaref IRA)
```

**3 same record, different entity** — the repointings, each from an ANCSA
corporation to the federally recognized village government the roster is
actually naming:

| record | before | after |
|---|---|---|
| `Algaaciq Native Village (St. Mary's)` | CE-000CB-YK *ANV Corporation* | CE-0000B-2K *Fed. rec. AK Native Village* |
| `Native Village of Chuathbaluk (Russian Mission…)` | CE-000BP-VP *ANV Corporation* | CE-00017-FZ *Fed. rec. AK Native Village* |
| `Native Village of Nanwalek (aka English Bay)` | CE-000AW-TW *ANV Corporation* | CE-0003Q-SF *Fed. rec. AK Native Village* |

**The 10 rows the old path dropped without a trace**, now rows:

```
[contested  ] 'Capitan Grande Band of Diegueno Mission Indians of C…'  AMBIGUOUS_TOKEN: 3 candidates
[contested  ] 'Te-Moak Tribe of Western Shoshone Indians of Nevada…'   AMBIGUOUS_TOKEN: 4 candidates
[proposed   ] 'Aleut Community of St. Paul Island  )'   cross_reference -> CE-00053-BV
[proposed   ] 'St. George Island'                       cross_reference -> CE-00053-BV
[proposed   ] 'Arctic Village'                          cross_reference -> CE-0006T-TA
[proposed   ] 'Village of Venetie'                      cross_reference -> CE-0006T-TA
[denied     ] 'Native Village of Elim'         + proposed -> CE-0004G-MG
[denied     ] 'Native Village of Shishmaref'   + proposed -> CE-0005X-75
[unresolved ] 'Lumbee Tribe of North Carolina'         see_instead is prose, not an entity
[unresolved ] 'Native Entities Within the State of Alaska Recognize…'  not an entity at all
```

Two of those deserve naming.

- The **Capitan Grande** and **Te-Moak** rows are FR *combined listings* — a
  parent tribe printed with its constituent bands in parentheses. Three and
  four eligible candidates respectively, and no rule separates them. They are
  `contested` with every candidate recorded and **nothing accepted**. That is
  the correct answer and it was previously a silent skip.
- `Native Entities Within the State of Alaska Recognized by and Eligible To
  Receive Services From the United States Bureau of Indian Affairs` is the
  **section heading of the Alaska list**, carried in
  `fr_recognized_entities.csv` as `kind = entity`. It is a parser artefact in
  the upstream table, and the source-record layer is the first place in the
  pipeline where it is visible instead of absent.

### What the audit does not claim

- The three repointings are **not applied** to any shipped table. This layer
  proposes and evidences; nothing here rewrites `cedar_assertions.csv`,
  `cedar_resolved_facts.csv` or the spine. Consuming it is a change to `510`,
  which this workstream does not own.
- `Bristol Bay Housing Authority` and `Bristol Bay Area Health Corporation`
  carry `fr_official_name` values found **nowhere in the roster file**. They
  are not FR facts and are not this dataset's records, so 514 cannot refute
  them; they are reported and left for the spine's owner.
- 570 of 578 mappings are `proposed`, not verified. A single independent
  confirmation route does not exist for this dataset. Agreement between 503
  and the spine's own `fr_official_name` column would be an echo — Cedar's
  prior decision agreeing with Cedar's current one — for the same reason
  `LR_CICD` cannot corroborate `LR_FEDERAL_REGISTER`.

---

## The invariants, and the proof that each one fires

`verify` runs ten invariants and exits 1 on any breach.

| id | what it refuses |
|---|---|
| **SR1** | a link naming a non-existent record; **a record with no link at all** — the old `continue` |
| **SR2** | an id that does not recompute from its own content |
| **SR3** | a duplicate `source_record_id` or `link_id` |
| **SR4** | a link pointing at a uid that was never minted |
| **SR5** | one source record **accepted onto two entities** |
| **SR6** | status/uid incoherence (an `unresolved` link carrying a uid, an accepted one without) |
| **SR7** | **source authority crossing into the match** — the F1 rule, made mechanical |
| **SR8** | an accepted link onto an entity class the source cannot mean — the measured F1 scenario |
| **SR9** | a refutation with no reason, a deny beside an accepted link it contradicts, a dangling supersede |
| **SR10** | a source row that never became a node |

**SR5 is directional and deliberately so.** One record means one entity.
*Many records naming one entity is legal* — the roster lists Venetie once and
cross-references it twice — and a check that flagged that would be wrong. It
is asserted as a **must-not-fire** fixture so nobody adds it later.

### Fixtures

Following the lesson recorded in `284_audit_nondeterministic_keys.py`: the
real instances are the historical record, the fixtures are the test. Each
mutation is applied to a **copy** of the live tables in a temp directory, so
the defect is synthetic and cannot be fixed out from under the check by
tomorrow's harvest. `verify --dir <copy>` runs as a subprocess, so the exit
codes below are real process exits.

`py -3 code/514_source_records.py fixtures`

```
  BASELINE (untouched copy)                exit 0
  inv    injected violation                                         exit fired                  restored
  PASS SR1   point a link at a source record that does not exist           1 SR1,SR2                       0
  PASS SR1   delete every link of SR-A14D58F33A9AEACB (a record with       1 SR1                           0
  PASS SR2   change a link's route without re-deriving its content-ad      1 SR2                           0
  PASS SR3   append a byte-identical duplicate link row                    1 SR3                           0
  PASS SR4   point an accepted link at a uid that was never minted         1 SR2,SR4,SR8                   0
  PASS SR5   accept ONE source record onto TWO entities                    1 SR5                           0
  PASS SR6   give an UNRESOLVED link a uid anyway                          1 SR2,SR6                       0
  PASS SR7   let the source's AUTHORITY be the basis of the match (F1      1 SR7                           0
  PASS SR8   attach an FR roster record to Elim Native CORPORATION (t      1 SR2,SR8                       0
  PASS SR9   refute a mapping and record no reason                         1 SR9                           0
  PASS SR9   supersede a link that does not exist                          1 SR9                           0
  PASS SR10  drop the source-record node for 'Aleut Community of St.       1 SR1,SR10                      0
  PASS (none) TWO source records accepted onto ONE entity - legal, and      0                               0

  13 fixture(s), 13 behaved as specified
```

Several mutations trip more than one invariant — changing a uid also changes
the content address, so SR2 co-fires with SR4 and SR8. That is correct
behaviour and is reported rather than filtered: the fixture passes when the
**target** invariant is among those that fired, the exit code is 1, and the
restored copy returns to exit 0.

The **`restored` column is the other half of the proof.** A check that stays
red after the defect is removed is as useless as one that never goes red. Each
fixture restores the clean copy and re-runs `verify` in a fresh subprocess:
every one returns 0.

### The required cases, and where each is demonstrated

| required case | demonstration |
|---|---|
| one source record proposed for two Cedar UIDs | **real**: `Native Village of Elim`, `Native Village of Shishmaref` — candidates `CE-0004G-MG\|CE-0008S-YH`, one denied on class. Fixture `SR5` proves the check fires if both were ever *accepted*. |
| two source records referring to the same Cedar UID (legal) | **real**: `CE-0006T-TA` Venetie ← 2 records; `CE-00053-BV` Pribilof ← 3 records. Must-not-fire fixture proves `verify` stays at exit 0. |
| a bad match attached to an authoritative fact (F1 itself) | **real and live**: 3 ANCSA corporations carrying `entity.is_federally_recognized = yes` at tier A, `authoritative`. Fixture `SR8` proves the check fires. |
| a deny / refutation of a previous match | **real**: 5 `denied` rows refuting the spine's prior `fr_official_name` mapping onto ANCSA corporations, each naming the candidate and the reason. Fixtures `SR9`/`SR9b` prove reason and supersede integrity. |
| unresolved competing candidates | **real**: `Capitan Grande` (3 candidates) and `Te-Moak` (4), `contested`, nothing accepted. |
| re-running without re-minting or duplicating | `determinism` mode, below. |

### Determinism

`py -3 code/514_source_records.py determinism`

```
  determinism  575 node(s) on disk; this run would mint 0 new and re-date 0
  determinism  run A 575 nodes / 585 links; run B 575 nodes / 585 links
  determinism  OK - identical ids, identical order, nothing re-minted
```

`source_record_id = SR-<sha1(dataset|locator)[:16]>` and
`link_id = SL-<sha1(record|role|uid|route|polarity)[:16]>` — content-addressed,
never positional, never rank-derived (class 7). `first_observed_date` is
carried forward from the table on disk and only a never-seen node takes
today's date, so a node cannot silently forget when it was first seen; the
determinism check tests for exactly that.

Independently confirmed by byte comparison: a second `all --apply` produces
files identical to the first.

---

## Where this stands, honestly

Stated plainly, because the spec forbids claiming unverified behaviour.

- **One dataset.** `fr_recognized_entities.csv`, 575 rows, chosen because it
  is the one source Cedar declares `authority_for` anything — which is exactly
  the condition under which a bad match does the most damage. The other
  harvesters in 510 are untouched and still fuse the two claims.
- **The three wrong recognition facts are still in
  `cedar_resolved_facts.csv`.** 514 measures and evidences them; applying the
  correction means changing `510_assertions.py`, which is workstream D's file
  this pass. Filed in the handoff, not done here.
- **`verified` is 1 of 571 accepted links.** There is no second mapping route
  for this dataset that is genuinely independent, so almost every link is an
  honest `proposed`.
  Adding a route that is an echo of the first would raise that number and mean
  nothing.
- **The eligibility rule is declared per dataset, by hand.** It is a judgement
  ("a federal roster of recognized entities names governments"), written down
  with its reason in `SOURCE_DATASETS[...]["eligibility_reason"]` so a buyer
  can disagree with it in the open. It is not derived from anything.
- **`kind = entity` is trusted from the upstream parser.** The Alaska section
  heading shows that parser is not perfect. The layer surfaces the row; it
  does not repair `fr_recognized_entities.csv`.
- **Nothing downstream consumes these tables yet.** They are new, internal,
  and not registered in `cedar_codebook.INTERNAL_TABLES` — living in
  `data/spine/` they are outside the shipping scan, so no gate reports them as
  an unregistered table. Registration is workstream D's call and is requested
  in the handoff.

## Adding a source dataset

1. Add a `SOURCE_DATASETS` entry naming its `origin_table`, its 510
   `source_id`, and — the decision that does the work — its
   `eligible_entity_classes` **with a written `eligibility_reason`**. Getting
   this wrong is how a roster of governments comes to name a corporation.
2. Extend `build_records` to read that table's columns into
   `record_says_*` fields. **Verbatim. No uid may enter the node table.**
3. Extend `_propose` if the dataset needs a route the four declared ones do
   not cover. Reuse `503.resolve`; do not write a matcher.
4. Run `all --apply`, then `fixtures`, then `determinism`. `verify` will tell
   you if a record lost its link, if an id stopped recomputing, or if a match
   started citing the source's authority as its own basis.
