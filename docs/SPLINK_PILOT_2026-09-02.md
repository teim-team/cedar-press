# The splink pilot — contractor → nation attribution, measured against the incumbent

*Run 2026-09-02. Script: `code/1060_splink_pilot.py`, number claimed atomically
via `1050_preflight.py claim splink_pilot --band 1060-1069`. Every number below
is reproducible from the six subcommands in that script's docstring. Nothing was
written to `data/clean`, `data/spine`, `dist/`, the ledger or the register.
Nothing was committed.*

## Verdict

**REJECT splink as a matcher for this task.** It is dominated by the incumbent
`503_identity.resolve` at every operating point, it cannot express the domain
rules that are Cedar's actual defence against the UKB/Cherokee error class, and
its `match_probability` is not reproducible run to run — so a fixed confidence
band does not mean the same thing tomorrow as today.

**Adopt, narrowly and with a caveat, only this:** the graded score is useful for
*ordering an adjudication queue* on rows the incumbent declines. That is a
triage aid worth ~1.7 points of held-out recall at 67% precision. It is not
worth a pipeline dependency, and it must never apply a link.

**The pilot's most valuable output is not the model.** It is **two live
collision-class defects it found in `entity_aliases.csv`** — one sending
Ho-Chunk Inc to the Wisconsin nation, one sending Seminole Nation Services to
Florida — both realised in `prime_contracts.csv` today, and both refused by
splink while the incumbent commits them at its highest confidence class. Those
are items 16–18 in `review/OWNER_DECISION_QUEUE.md`.

## What was installed

| package | version | used? |
|---|---|---|
| `splink` | **4.0.16** | yes |
| `usaddress` | **0.5.16** | **no** — see "what usaddress was not needed for" |
| `duckdb` | 1.5.5 | already present; used heavily |

## Which backlog, and why

**Picked: contractor → nation attribution.** It is the only one of the three
offered with all four of a real held-out truth set (the owner's own tier-A
rulings), a real negative set (tier X), the three named collision cases living
inside it, and enough scale to answer the runtime question.
`docs/ENTITY_MATCH_RULES.md` rule 15 argues the same from the other end.

**`resource_revenue` was ruled out on measurement, and the brief describing it
is stale.** The brief says *"586 rows naming an entity with no `cedar_uid`
(Three Affiliated 492, Crow 32, Hopi 32, Navajo 30)"*. Measured in the live file
(11,305 rows): 492 / 32 / 32 / 30 are the counts of rows that **do** carry a
`cedar_uid` — `CE-0016W-A5`, `CE-00153-F4`, `CE-0013W-VN`, `CE-0017F-1G`. The
rows that name an entity and carry no uid number **760** and are **eight
distinct names**, five of which are not entities:

```
Holders of Osage headrights (individuals)                                508
Osage Mineral Estate                                                      61
Uintah Basin Revitalization Fund                                          60
Navajo Revitalization Fund                                                58
Village corporations and at-large shareholders ... not individually named 35
The other ANCSA regional corporations, not individually named             24
Other ANCSA regional corporations, village corporations ...                7
State of Oklahoma                                                          7
```

These are aggregate-party and policy questions — the class the deals
autoresolver was refused for on 2026-08-26 (*"an aggregate party must never
resolve to one entity"*). There is no record-linkage problem here and **a pilot
on this backlog would have proved nothing.**

**The nonprofit funnel** has the richest error history but its truth is mostly
*refusals* (the 53 containment links, the 104 brand aliases). That measures
precision and cannot measure recall.

## Ground truth

| set | definition | n |
|---|---|---:|
| POSITIVE | `cedar_identifier_ledger_final.csv`: `identifier_type=UEI`, `confidence_tier=A`, `attribution_method` ∈ {hand, bgov_manual, elijah_ruling, elijah_ruling_redirect, web_verified}, non-blank `cedar_uid`, present in `prime_contracts` | **690** |
| — split | by UEI, 50/50, seed 20260902 | 345 train / **345 test** |
| NEGATIVE | `confidence_tier=X` UEI rows. START_HERE 1b: tier X is a NEGATIVE ruling | **117** (116 in prime) |

`verify` asserts no test UEI reaches the m-training labels; the fixture proves
that assertion fires on an injected leak and clears on restore.

## The ceiling, measured before any model was built

Of the 690 truth pairs, **596 (86.4%) share at least one distinctive token**
with a name their owner carries in the spine. **94 (13.6%) share none** —
`PCI GOVERNMENT SERVICES`, `RIVERTECH`, `TALU`, `TUKNIK GOVERNMENT SERVICES`,
`CNI CONSTRUCTION`, `PADUCAH REMEDIATION SERVICES`, `ALL NATIVE SYSTEMS`,
`KAULA AE`. That is the ASRC-files-as-BROADLEAF class and **no name-similarity
method can reach it, splink included.**

Under this pilot's own larger stoplist the reachable set narrows further: the
true owner appears **anywhere** in splink's candidate list for only
**230 of 345 (66.7%)** held-out contractors. The ~20 points between 86.4% and
66.7% is what stripping `SERVICES` / `TECHNOLOGY` / `FEDERAL` from the token set
costs in reachability — and buys in not blocking half the corpus together.

## The model

`link_only`. 12,491 contractor records (one per `awardee_uei`) against 7,186
entity **name** records over 1,555 `cedar_uid` (canonical + `fr_official_name`
+ spine aliases + `entity_aliases`, single-token `alias_type='brand'` rows
refused as 503 refuses them).

Comparisons: seven-level name (exact w/ TF adjustment → JW ≥0.95 →
entity-tokens ⊆ filed with ≥2 tokens → JW ≥0.88 → ≥2 shared distinctive tokens
→ exactly 1 shared token → else) and three-level state. Blocking: exact
`name_norm` plus an **exploding** rule on the distinctive-token array.

### Learned weights (canonical run)

| comparison | level | m | u | BF |
|---|---|---:|---:|---:|
| name | exact `name_norm` | 0.2145 | 3.90e-06 | 55,038 |
| name | entity tokens ⊆ filed, ≥2 | 0.1304 | 2.05e-05 | 6,375 |
| name | Jaro-Winkler ≥ 0.95 | 0.0087 | 3.12e-06 | 2,789 |
| name | ≥2 distinctive tokens shared | 0.0435 | 4.74e-05 | 918 |
| name | Jaro-Winkler ≥ 0.88 | 0.0319 | 4.03e-05 | 791 |
| name | **exactly 1 distinctive token** | 0.2580 | 0.00217 | **119** |
| name | else | 0.3130 | 0.9977 | 0.3 |
| state | exact | 0.8058 | 0.0521 | **15.5** |

`m` for the "else" level is **0.313** — the model correctly learned, from the
owner's own rulings, that a third of true links look like nothing. And one
shared distinctive token carries **BF 119**, not enough to convict alone but
enough that a second weak signal tips it past 0.5. That is the UKB/Cherokee
mechanism, priced.

## Four defects found in building this, all of which produced plausible numbers

Recorded because each is `AGENT_FIELD_GUIDE` §3 — *the number was produced, it
was plausible, and it was about something else* — and three of the four are mine.

1. **`estimate_probability_two_random_records_match([block_on("name_norm")],
   recall=0.5)` returned 8.69e-06.** It assumes exact-name blocking catches half
   the true matches; a subsidiary almost never files under its owner's exact
   name, which is the entire reason the backlog exists. The under-estimate
   crushed every posterior — **nothing scored above 0.95 and the top band was
   empty for the wrong reason.** Replaced with a prior computed from the data
   (3,216 attributed UEIs → 16,658 expected true record pairs over 89,760,326 =
   **1.856e-04**, one in 5,388).
2. **Labelling the contractor against every name its owner carries** taught
   `estimate_m_from_pairwise_labels` that "no distinctive token in common" is a
   frequent signature of a true match. It is a signature of an alias the filer
   did not use. Fixed to one label per (uei, owner), on the name the filer
   actually resembles.
3. **A self-join fanout in my own SQL.** The contractor aggregate took
   `fiscal_year` from `left join (select awardee_uei, fiscal_year from pc)`,
   which duplicated every row `n_rows` times and multiplied `sum(obligations)`
   by the same factor. The queue reported **$2,880.88B** of prime obligations
   against a table whose entire content is **$310.01B** — 9.3× — and it looked
   like a plausible big number until it was set beside the total. `prep` now
   asserts dollar conservation against the source and returns 1 if it breaks.
4. **A seeded shuffle over an unordered input is not reproducible; it only looks
   it.** `kept.shuffle()` ran on rows in whatever order DuckDB's parallel hash
   aggregate emitted, so the train/test partition differed every run and *the
   incumbent's own held-out score moved with it* (205/183, 210/195, 208/191 on
   identical bytes). Same class in the same function: `mode()` breaks ties
   non-deterministically, so the modal `awardee_name` — the string 503 is asked
   to resolve — also drifted. Both fixed: sort before shuffle, and
   `array_agg(x order by count desc, x)[1]` in place of `mode()`. This is
   `293_lint_bug_classes.py` class 7 (non-deterministic key) reached by a new
   route.

**After the fixes the incumbent baseline is bit-stable across runs. Splink's
scores are not, and that is a property of splink, not of this script** — see
"Reproducibility" below.

## Precision and recall, held-out test (n = 345)

**Canonical run** (seed 20260902, `u` sampled over 5M of 89.76M pairs):

| threshold | tp | fp | no-call | precision | recall |
|---:|---:|---:|---:|---:|---:|
| 0.999 | 0 | 0 | 345 | — | 0.0% |
| 0.99 | 4 | 0 | 341 | **100.0%** | 1.2% |
| 0.95 | 42 | 10 | 293 | 80.8% | 12.2% |
| 0.90 | 70 | 13 | 262 | 84.3% | 20.3% |
| 0.70 | 95 | 17 | 233 | 84.8% | 27.5% |
| **0.50** | **133** | **19** | **193** | **87.5%** | **38.6%** |
| 0.30 | 147 | 40 | 158 | 78.6% | 42.6% |
| 0.10 | 171 | 61 | 113 | 73.7% | 49.6% |
| 0.001 | 177 | 80 | 88 | 68.9% | 51.3% |

**Incumbent `503_identity.resolve` on the identical 345 rows, deterministic:
205 proposals, 183 correct — precision 89.3%, recall 53.0%.** Over all 690:
416 / 377 → 90.6% / 54.6%.

**Splink is dominated.** Its best precision band (p≥0.5, 87.5%) is *below* the
incumbent's 89.3% while reaching only 38.6% recall against 53.0%. Adding a
margin-over-runner-up constraint raises precision to at best **93.2%** (p≥0.5,
margin ≥0.2) at 31.6% recall — still not an auto-accept grade, and at half the
recall.

## Reproducibility — the finding that settles it

`match_probability` is **not stable across runs on byte-identical input**, and
enlarging the `u` sample does not fix it.

| `max_pairs` | runs | precision at p≥0.95 | top-1 recall |
|---|---:|---|---|
| 5,000,000 | 4 | **80.8 – 88.5%** | 50.4 – 51.6% |
| 100,000,000 | 3 | **82.2 – 91.1%** | 51.6 – 53.6% |

1e8 exceeds the 89,760,326 pairs that exist, so "sample the whole space" is not
reachable through this API — `estimate_u_using_random_sampling` still samples,
and `seed=` does not determinise it. Cost of the larger sample: `u` estimation
1.7 s → 45 s, for no reduction in spread.

**A confidence band cut on raw `match_probability` therefore inherits a
several-point swing that has nothing to do with the data.** For a system whose
standing rule is that a wrong attribution is not expandable, that is
disqualifying on its own, independent of the precision numbers.

## What splink does with the owner's NEGATIVE rulings

| threshold | links a tier-X UEI anyway |
|---:|---|
| 0.99 | **0 / 116 (0.0%)** |
| 0.95 | 7 / 116 (6.0%) |
| 0.90 | 9 / 116 (7.8%) |
| 0.50 | 28 / 116 (24.1%) |
| 0.10 | 49 / 116 (42.2%) |

**The incumbent links 49 of 117 (41.9%) and has no threshold to trade.** This is
splink's one clear structural advantage: it can be told to shut up.

## Top-k recall — the metric the reframe actually asks for

| k | true owner in top-k |
|---|---|
| 1 | 51.3% |
| 2 | 60.9% |
| 3 | 62.6% |
| 5 | 64.6% |
| 10 | 66.1% |
| anywhere in the candidate set | **66.7%** ← the blocking ceiling |

The 9.6-point jump from top-1 to top-2 is the whole story of the errors: **the
true owner is usually the runner-up.** Of the 19 top-1 false positives at p≥0.5,
**15 have the truth at rank 2 or 3.** A queue showing three candidates asks a
far cheaper question than a matcher forced to pick one — which is exactly the
owner's point, and the one thing splink's output shape does better than 503's.

## The false positives, in full, because a precision number cannot show their character

```
p=0.9856 CONFEDERATED TRIBES OF WARM SPRINGS RESE OR -> Confederated Tribes of the Warm Sp  (truth rank 11)
p=0.9825 LEECH LAKE BAND OF OJIBWE                MN ->  Leech Lake Band                    (truth rank 2)
p=0.9825 LEECH LAKE BAND OF OJIBWE NATURAL WILD R MN ->  Leech Lake Band                    (truth rank 2)
p=0.9796 College Of Menominee Nations             WI -> College of Menominee Nation         (truth rank 3)
p=0.9680 San Juan Pueblo Tribal Council           NM -> SAN JUAN SERVICES LLC               (truth rank 2)
p=0.9654 NORTHERN CHEYENNE TRIBE                  MT -> Northern Cheyenne Tribal Inc        (truth rank 2)
p=0.9654 NORTHERN CHEYENNE SOLID WASTE MANAGEMENT MT -> Northern Cheyenne Tribal Inc        (truth rank 2)
p=0.9652 OGLALA SIOUX TRIBE OF PINE RIDGE INDIAN  SD -> Pine Ridge Inc                      (truth rank 2)
p=0.9652 Lower Brule Sioux Tribe                  SD -> Lower Brule Inc                     (truth rank 2)
p=0.9521 FORT PECK COMMUNITY COLLEGE              MT -> Fort Peck Community College|FPCC    (truth rank 2)
p=0.9406 HO-CHUNK BUILDERS COMPANY                NE -> Ho-Chunk Community Capital Inc.     (truth rank ABSENT)
p=0.9372 RAMAH NAVAJO CHAPTER                     NM -> Ramah Navajo Chapter Nation         (truth rank 6)
p=0.9348 Citizen Potawatomi Nation Inco           OK -> Citizen Potawatomi Community Devel  (truth rank 2)
p=0.8923 Cherokee Mechanical Inc                  NC -> Cherokee Central Middle Board, Inc  (truth rank 3)
p=0.7587 FORT PECK JOURNAL, THE                   MT -> Fort Peck Community College         (truth rank 2)
p=0.7587 FORT PECK MANUFACTURING INC & WEST ELECT MT -> Fort Peck Community College|FPCC    (truth rank 2)
p=0.7109 CHOCTAW IKHANA, INC.                     MS -> Choctaw Central High Schools        (truth rank 2)
p=0.6638 LAGUNA DEVELOPMENT CORPORATION           NM -> Laguna Elementary Inc               (truth rank 4)
p=0.6177 Bank Of Cherokee County                  OK -> Local Bank (formerly Bank of Chero  (truth rank 2)
```

**Almost every one is the same error: the nation against one of its own
institutions.** Pine Ridge Inc, Lower Brule Inc, Northern Cheyenne Tribal Inc,
Fort Peck Community College, Choctaw Central High Schools, Laguna Elementary
Inc, Cherokee Central Middle Board, College of Menominee Nation.
`ENTITY_MATCH_RULES` rule 7 already decides this class — *residue is an
institution form → HOLD; a tribal college, a school district and a utility are
real entities and they are not the nation* — and **splink has nowhere to put
that rule.** It is a statement about one record's class, not a comparison
between two, and Fellegi-Sunter has no slot for it. That is the structural
reason the incumbent wins: 503's advantage is its six accumulated domain rules
(`RESOLUTIONS`, `ADMIN_GEOGRAPHY`, `CIVIC_FORM`, `CIVIC_UTILITY`, the
leading-token rule, the coverage rule, the parent/constituent rule), not its
algorithm.

Two other classes appear: **two distinct federally recognized tribes merged** —
in an earlier run, `SHAKOPEE MDEWAKANTON SIOUX COMMUNITY → Prairie Island Indian
Community` at p=0.886, which is a genuine UKB/Cherokee-class error and would be
disqualifying in an auto-accept band; and **a near-duplicate in Cedar's own
spine** — `UTAH NAVAJO HEALTH SYSTEM INC` vs `"Utah Navaho Health System, Inc."`
both holding spine rows, where splink found a Cedar defect and was scored wrong
for it.

## Splink as a supplement rather than a replacement

Scored **only on the 140 held-out rows the incumbent declined**:

| threshold | proposed | correct | precision | recall added over 503 |
|---:|---:|---:|---:|---:|
| 0.9 | 1 | 1 | 100.0% | +0.3 pp |
| **0.5** | **9** | **6** | **66.7%** | **+1.7 pp** |
| 0.3 | 24 | 12 | 50.0% | +3.5 pp |
| 0.1 | 33 | 17 | 51.5% | +4.9 pp |

And in head-to-head at p≥0.5 splink **rescues 6 rows 503 declined while breaking
11 rows 503 got right**. As a replacement it is negative-sum.

**It is also useless as a cross-check.** On the 22 held-out rows 503 got
*wrong*, splink at p≥0.5 agrees with the wrong answer 3 times, disagrees 4, is
silent 15; at p≥0.1 it is 9 agree / 10 disagree. A coin flip on exactly the rows
where the incumbent fails.

## The three named collision cases

Full table: `data/interim/splink_pilot/collisions.csv` (103 rows).

| case | splink | incumbent 503 |
|---|---|---|
| **Ho-Chunk Inc (NE) vs Ho-Chunk Nation of Wisconsin** | `HO-CHUNK, INC.` (NE) → a Nebraska entity at p≈0.94; **Ho-Chunk Nation of Wisconsin `CE-00150-XS` scored p=0.188** and lost on state. **PASS** | **FAILS.** `HO CHUNK INC` → `TRBF-HOCHNK-00` (**Wisconsin**), reason *"exact normalized name/alias, unique"* — its strongest evidence class |
| **Eastern Band Cherokee (NC) vs Cherokee Nation (OK) vs UKB (OK)** | never auto-accepts. `CHEROKEE NATION …` companies put **Cherokee Nation and the United Keetoowah Band as top-2** at p≈0.65/0.21 — genuinely uncertain, correctly routed to adjudication. **PASS under the reframe** | proposes `TRBF-CHKNAT-00` confidently by *"gov-class distinctive-token match on 'Cherokee Nation'"*. Right for the CNB subsidiaries, but it has no way to be uncertain, which is how the UKB merge happened |
| **Seminole of Oklahoma vs Seminole of Florida** | `SEMINOLE NATION SERVICES, LLC` (OK) → **The Seminole Nation of Oklahoma** p=0.21, Florida at 0.03. Direction correct. **PASS** | **FAILS.** → `TRBF-SMNLFL-00` (**Florida**) by *"gov-class distinctive-token match on 'Seminole'"* |

**Splink passes all three under the reframe. The incumbent fails two of three,
confidently.** That is not an argument for adopting splink — its precision is
worse everywhere — but it is the strongest thing this pilot found, and it points
at the cause below.

## The two live defects this pilot found

Both in `data/clean/entity_aliases.csv`; both realised in `prime_contracts.csv`
today. Dollars are small. The class is not — it is the shape of the
$181,881,441.37 UKB merge.

**D1 — `Ho Chunk Inc` is an alias of the wrong nation.**

```
entity_id     TRBF-HOCHNK-00   (Ho-Chunk Nation of Wisconsin, CE-00150-XS)
alias_name    Ho Chunk Inc
alias_type    legal            source_system  UEI
```

Ho-Chunk Inc is the **Winnebago Tribe of Nebraska's** holding company
(`TRBF-WNNBGO-00` / `CE-001C8-GH`), and Cedar knows it — Ho-Chunk Builders,
Ho-Chunk Shared Services and HCI Winnebago are all keyed to Winnebago.

| contractor | city, state | keyed to | obligations |
|---|---|---|---:|
| HO-CHUNK CONSTRUCTION MANAGEMENT SERVICES COMPANY | Winnebago, **NE** | **CE-00150-XS (WI)** | $0.60M |
| HO CHUNK INC | Winnebago, **NE** | **CE-00150-XS (WI)** | $0.02M |

**D2 — `Seminole Nation` is an alias of the Seminole Tribe of FLORIDA.**

```
entity_id     TRBF-SMNLFL-00   (Seminole Tribe of Florida, CE-001A9-CA)
alias_name    Seminole Nation
alias_type    full_form_federal_filing    source_system  cedar_generated
```

"Seminole Nation" is the **Oklahoma** tribe (`TRBF-SMNLOK-00` / `CE-001AA-J3`).
The spine `aliases` column additionally gives the Florida tribe the bare single
token `Seminole`.

| contractor | state | keyed to | obligations |
|---|---|---|---:|
| SEMINOLE NATION SERVICES, LLC | **OK** | **CE-001A9-CA (FL)** | $0.02M |
| HARD ROCK HOTEL AND CASINO TULSA | **OK** | **CE-001A9-CA (FL)** | $0.00M |

(The Tulsa row is a brand-vs-owner error: Hard Rock is the Florida tribe's
brand, the Tulsa property is Cherokee Nation's.)

**D3 — the structural cause. 503's single-token alias guard is scoped to one
`alias_type`.** `build_index()` refuses a single-token alias only when
`alias_type == 'brand'`. Across all 6,298 rows of `entity_aliases.csv`:

| alias_type | single-token rows | guarded? |
|---|---:|---|
| common | 328 | **no** |
| acronym | 141 | **no** |
| brand | 104 | yes |
| shortened | 3 | **no** |
| legal | 3 | **no** |
| **total** | **579** | **104 (475 unguarded)** |

A blanket refusal would be wrong — `Afognak`, `Ahtna`, `Akutan`, `Chevak` are
genuine single-word names and rule 14 says that orthography is a *positive*
signal. The structural predicate is narrower and measurable: **101 single-token
index keys are owned outright by one spine entity while the same token is also a
distinctive token of a different one** — `BEAVER`, `BLACKFEET`, `BRISTOL`,
`CADDO`, `CAHUILLA`, `CHEHALIS`, `CHITIMACHA`, `CHUNK`. Each is a name-only win
waiting to land on the wrong entity, and D1 and D2 are two that already have.

## Runtime, and whether the DuckDB backend is workable

| operation | scale | wall clock |
|---|---|---|
| full scan + aggregate of `prime_contracts.csv` | **1,217,768 rows / 1.4 GB** | **2.9 s** |
| `prep` end to end, incl. windowed modal selection | same | **11.8 s** |
| splink `u` estimation, 5M sampled pairs | 89.76M possible | 1.7 s |
| splink `m` from 345 labels | — | 0.1 s |
| splink `predict` | 210,093 scored pairs | **1.9 s** |
| **splink total, train + predict** | | **6.4 s** |
| incumbent 503, index + 690 resolves | | **0.1 s** |

**The DuckDB backend is comfortably workable and would remain so at 2.8M rows.
Runtime is not a reason to reject splink.** Note the 1.2M-row table is not the
linkage input — it collapses to 12,491 distinct UEIs before any pair is formed,
and the pair space is set by the entity table. The same is true of
`faads_transactions_all_agencies` (2.77M rows).

**Recorded separately, and larger than the splink question: `duckdb` is imported
by 0 of 515 scripts in this repo and it read a 1.4 GB CSV in 2.9 seconds.**

## The confidence bands, and why the top one is empty

`data/interim/splink_pilot/bands.json`:

```
auto-accept   p >= 0.999    ->  EMPTY BY MEASUREMENT
adjudicate    0.5 <= p < 0.999
auto-reject   p < 0.5
```

**Why the auto-accept band is empty.** Precision by band on held-out data:
100% at p≥0.99 but on **4 rows** (1.2% recall); 80.8% at p≥0.95; 87.5% at p≥0.5.
The best precision anywhere in the threshold × margin grid is **93.2%**. And the
scores move 80.8–88.5% at p≥0.95 between runs on identical input. One wrong link
in eight, applied without a human, on a threshold that shifts week to week, is
how the $181.9M UKB merge happened. **There is no auto-accept band on this task
at this model quality. Setting one would be performing confidence rather than
measuring it.**

**Why 0.5 and not 0.1 for the bottom cut.** 0.1 was tried first, from the recall
curve: it recovers 49.6% against 38.6% and looks like the right call under
"easier to call stuff than miss things". It is not, and the queue itself is the
evidence — at 0.1 the queue is **1,273 rows / $10.06B** and its *highest-dollar*
rows are noise: `All Cities Enterprises` → *All Pueblo Council of Governors*
(shared token `ALL`), `Environmental Management Resources` → *Midwest Tribal
Energy Resources* (shared token `RESOURCES`). A queue whose top of list is
garbage fails the purpose of a queue. At 0.5 it is **252 rows / $0.96B** and the
top of the list is answerable: `Hui Huliau Technology Services Llc → Hui
Huliau`, `First Nations Community Health Source → First Nations
CommunityHealthSource`, `Dallas Inter-Tribal Center → Urban Inter-Tribal Center
of Texas`, and a visible error to refuse — `Lake Michigan Contractors → Lac
Vieux Desert Band of Lake Superior`.

Both cuts are one line in `bands.json`; the 0.1 variant is regenerable with
`queue --reject 0.1`.

## The adjudication queue

`review/splink_pilot_adjudication_queue_2026-09-02.csv` — **252 rows, $0.96B**,
all ADJUDICATE, sorted by dollars. Rows already ruled (positive or tier X) and
rows already attributed in `prime_contracts` are excluded; these are open
questions only.

Each row carries what the owner's ladder needs, so rungs 1–4 need no research:

| column | ladder rung |
|---|---|
| `contractor_city`, `contractor_state`, `proposed_entity_state`, `state_agrees` | **1. the address** |
| `rung2_entity_website` | **2. the website says which tribe** |
| `rung3_other_ueis_at_this_address`, `rung3_already_keyed_at_this_address` | **3. search the address, see what else is there** — the co-located UEIs, and which are already keyed |
| `cage_code`, `declared_parent_name`, `declared_parent_uei` | **4. CAGE as a pointer to the next name** |
| `match_probability`, `runner_up`, `margin_over_runner_up` | the score and how close the second answer was |
| `owner_ruling` = `ACCEPT \| REFUSE \| REPOINT:<cedar_uid> \| UNRESOLVED` | **6. STOP is a legitimate answer, and the form says so** |

**Sort by `margin_over_runner_up` after dollars.** 15 of the 19 top-1 false
positives have the truth at rank 2 or 3, so a small margin is not noise — it is
the signal that the row is asking a real question.

## What usaddress was not needed for

Installed as instructed, then not used. The owner's ladder starts at the address,
but `prime_contracts` already carries `recipient_city_name` and
`recipient_state_code` as **separate parsed columns** — there is no free-text
address on the contracting side to parse. `usaddress` would earn its place on
the OSHA 300A establishment file (street + ZIP on 100% of rows,
`ENTITY_MATCH_RULES` rule 7 rung 2) or on 990 filer addresses. Not here.

## Honest limitations

- **One backlog, one dataset.** Nothing here says what splink would do on the
  nonprofit funnel or on FAADS.
- **The truth set inherits the owner's coverage.** 302 distinct owners over 690
  UEIs, with the ANC/ANCSA families over-represented because that is where the
  dollars and the rulings are.
- **The split is by UEI, not by owner.** An owner can appear on both sides. The
  owner-disjoint variant rides in `truth.csv` as `owner_split` and was **not
  scored**. Splink learns global m/u rather than per-entity parameters so the
  leakage risk is low, but it is unmeasured and it is the obvious next check.
- **Only two of the three bands have a measured precision**, because the third
  is empty.
- **The baseline is a moving target in the other direction.** 503 has a month of
  accumulated domain rules. A fair reading of this pilot is *"the domain rules
  are the asset"*, not *"Fellegi-Sunter is bad"* — and those rules have no
  natural home in a probabilistic linker.
- **Splink's own defaults were the largest single source of error here**, twice
  (the prior, the label construction). A team adopting it without a held-out set
  would have shipped both and never known.

## Files written

```
code/1060_splink_pilot.py                              the pilot (verify --selftest passes)
docs/SPLINK_PILOT_2026-09-02.md                        this report
review/splink_pilot_adjudication_queue_2026-09-02.csv  252 rows, the queue
review/OWNER_DECISION_QUEUE.md                         items 16, 17, 18 appended in a marked block
data/interim/splink_pilot/contractors.csv              12,491
data/interim/splink_pilot/entities.csv                 7,186
data/interim/splink_pilot/truth.csv                    690 + split + owner_split
data/interim/splink_pilot/negatives.csv                117
data/interim/splink_pilot/labels_train.csv             345
data/interim/splink_pilot/model.json                   trained m/u
data/interim/splink_pilot/scored_pairs.csv             56,677 candidate pairs
data/interim/splink_pilot/eval.json                    every curve above
data/interim/splink_pilot/false_positives.csv          19
data/interim/splink_pilot/collisions.csv               103
data/interim/splink_pilot/baseline_truth.csv           690, the incumbent's answers
data/interim/splink_pilot/baseline_negatives.csv       117
data/interim/splink_pilot/bands.json                   the cut points
```

Nothing in `data/clean`, `data/spine` or `dist/`. Nothing committed.
`py -3 code/1060_splink_pilot.py verify --selftest` exits 0 and proves both
**I2** (held-out leakage into the m-training labels) and **I4** (an auto-accept
link across a named collision pair) fire on injected violations and clear on
restore.
