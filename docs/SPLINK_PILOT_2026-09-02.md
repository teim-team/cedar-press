# The splink pilot — contractor → nation attribution, measured against the incumbent

*Run 2026-09-02. Script: `code/1060_splink_pilot.py` (number claimed atomically
via `1050_preflight.py claim --band 1060-1069`). Every number here is
reproducible with the six subcommands in that script's docstring. Nothing was
written to `data/clean`, `data/spine`, the ledger or the register; nothing was
committed.*

## Verdict, first

**REJECT splink as a replacement for `503_identity.resolve`. ADOPT NARROWLY as a
scorer that feeds the owner adjudication queue on the rows the incumbent
declines. The auto-accept band is empty and that is a measurement, not a
default.**

The pilot's most valuable output is not the model. It is **two live
collision-class defects it found in `entity_aliases.csv`**, both of which the
incumbent matcher acts on today, and both of which splink refused. Those are
items 16 and 17 in `review/OWNER_DECISION_QUEUE.md`.

## What was installed

| package | version | note |
|---|---|---|
| `splink` | **4.0.16** | `py -3 -m pip install splink` |
| `usaddress` | **0.5.16** | installed; **not used** — see "what usaddress was not needed for" |
| `duckdb` | 1.5.5 | already present |

## Which backlog, and why

Three were offered. The pick is **contractor → nation attribution**.

**`resource_revenue` was ruled out on measurement, and the brief describing it
is stale.** The brief says *"586 rows naming an entity with no `cedar_uid`
(Three Affiliated 492, Crow 32, Hopi 32, Navajo 30)"*. Measured in the live file
(11,305 rows, 2026-09-02): 492 / 32 / 32 / 30 are the counts of rows that **do**
carry a `cedar_uid` — `CE-0016W-A5`, `CE-00153-F4`, `CE-0013W-VN`, `CE-0017F-1G`.
The rows that name an entity and carry no uid number **760**, and they are
**eight distinct names**, of which five are not entities at all:

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

These are aggregate-party and policy questions — the class `57_autoresolve_deal_parties`
was already refused for on 2026-08-26 ("an aggregate party must never resolve to
one entity"). There is no record-linkage problem here and a probabilistic linker
would have nothing to learn. **A pilot on this backlog would have proved
nothing.**

**The nonprofit funnel** has the richest error history but its truth set is
mostly *refusals* (the 53 containment links, the 104 brand aliases), which
measures precision and cannot measure recall.

**Contracting** was picked because it is the only one of the three with all
four of: a real held-out truth set (the owner's own tier-A ruled rulings), a
real negative set (tier X), the three named collision cases living inside it,
and enough scale to answer the runtime question. `ENTITY_MATCH_RULES` rule 15
says the same thing from the other end.

## Ground truth

| set | definition | n |
|---|---|---:|
| POSITIVE | `cedar_identifier_ledger_final.csv`, `identifier_type=UEI`, `confidence_tier=A`, `attribution_method` in {hand, bgov_manual, elijah_ruling, elijah_ruling_redirect, web_verified}, non-blank `cedar_uid`, present in `prime_contracts` | **690** |
| — held out | 50/50 split, seed 20260902, split by UEI | 345 train / **345 test** |
| NEGATIVE | tier **X** UEI rows — START_HERE 1b: tier X is a NEGATIVE ruling | **117** (116 in prime) |

`verify` asserts no test UEI reaches the m-training labels, and the fixture
proves that assertion fires.

## The ceiling, measured before any model was built

Of the 690 truth pairs, **596 (86.4%) share at least one distinctive token**
with some name their owner carries in the spine. **94 (13.6%) share none** —
`PCI GOVERNMENT SERVICES`, `RIVERTECH`, `TALU`, `TUKNIK GOVERNMENT SERVICES`,
`CNI CONSTRUCTION`, `PADUCAH REMEDIATION SERVICES`, `ALL NATIVE SYSTEMS`,
`KAULA AE`. That is the ASRC-files-as-BROADLEAF class. **No name-similarity
method can reach it, splink included.**

Under the pilot's own (deliberately larger) stoplist, the reachable set narrows
further: the true owner appears **anywhere** in splink's candidate list for only
**249 of 345 (72.2%)** held-out contractors. The extra ~14 points are the price
of stripping `SERVICES`, `TECHNOLOGY`, `FEDERAL` etc. from the token set —
which is what stops `FEDERAL` from blocking half the corpus together.

## The model

`link_only`, two tables: 12,491 contractor records (one per `awardee_uei`,
modal name/city/state) against 7,186 entity **name** records over 1,555
`cedar_uid` (canonical + `fr_official_name` + spine aliases + `entity_aliases`,
single-token `alias_type='brand'` rows refused as 503 refuses them).

Comparisons: a seven-level name comparison (exact with TF adjustment →
Jaro-Winkler 0.95 → entity-tokens-subset-of-filed → JW 0.88 → ≥2 shared
distinctive tokens → exactly 1 shared token → else) and a three-level state
comparison. Blocking: exact `name_norm` plus an **exploding** rule on the
distinctive-token array.

**Two things went wrong in the first draft and both are worth recording**,
because both produced plausible numbers:

1. `estimate_probability_two_random_records_match([block_on("name_norm")],
   recall=0.5)` returned **8.69e-06**. It assumes exact-name blocking catches
   half the true matches; a subsidiary almost never files under its owner's
   exact name, which is the entire reason the backlog exists. The
   under-estimate crushed every posterior — **nothing scored above 0.95 and the
   top band was empty for the wrong reason**. Replaced with a prior computed
   from the data (3,216 attributed UEIs → 16,658 expected true record pairs over
   89,760,326 = 1.856e-04, one in 5,388).
2. Labelling the contractor against **every** name its owner carries taught
   `estimate_m_from_pairwise_labels` that "no distinctive token in common" is a
   frequent signature of a true match. It is a signature of an alias the filer
   did not use. Fixed: one label per (uei, owner), on the name record the filer
   actually resembles.

**And one in my own SQL, caught by a conservation check and not by anything
else:** the contractor aggregate got `fiscal_year` from a self-join, which
fanned out `sum(total_obligations)` by `n_rows`. The queue reported **$2,880.88B**
of prime obligations against a table whose entire content is **$310.01B** — a
9.3× overstatement that looked like a plausible big number until it was put
next to the total. `prep` now asserts dollar conservation against the source and
returns 1 if it breaks. This is `AGENT_FIELD_GUIDE` §3 exactly, committed by the
agent writing about §3.

### Learned weights (Bayes factor per level)

| comparison | level | m | u | BF |
|---|---|---:|---:|---:|
| name | exact `name_norm` | 0.2145 | 3.90e-06 | 55,038 |
| name | entity tokens ⊆ filed, ≥2 tokens | 0.1304 | 2.05e-05 | 6,375 |
| name | Jaro-Winkler ≥ 0.95 | 0.0087 | 3.12e-06 | 2,789 |
| name | ≥2 distinctive tokens shared | 0.0435 | 4.74e-05 | 918 |
| name | Jaro-Winkler ≥ 0.88 | 0.0319 | 4.03e-05 | 791 |
| name | **exactly 1 distinctive token shared** | 0.2580 | 0.00217 | **119** |
| name | else | 0.3130 | 0.9977 | 0.3 |
| state | exact | 0.8058 | 0.0521 | **15.5** |

Two readings matter. **`m` for the "else" level is 0.313** — the model has
correctly learned, from the owner's own rulings, that a third of true links look
like nothing. And **one shared distinctive token carries BF 119**, which on this
prior is not enough to convict on its own but is enough that a second weak
signal tips it over 0.5. That is the UKB/Cherokee mechanism, priced.

## Precision and recall, held-out test (n=345)

| threshold | tp | fp | no-call | precision | recall |
|---:|---:|---:|---:|---:|---:|
| 0.99 | 9 | 0 | 336 | **100.0%** | 2.6% |
| 0.95 | 54 | 7 | 284 | 88.5% | 15.7% |
| 0.90 | 82 | 9 | 254 | 90.1% | 23.8% |
| 0.50 | 142 | 16 | 187 | 89.9% | 41.2% |
| 0.30 | 157 | 26 | 162 | 85.8% | 45.5% |
| 0.10 | 176 | 54 | 115 | 76.5% | 51.0% |
| 0.001 | 191 | 75 | 79 | 71.8% | **55.4%** |

**Incumbent `503_identity.resolve` on the identical 345 rows: 205 proposals,
186 correct — precision 90.7%, recall 53.9%, in 0.0 seconds.**

Splink does not beat it at any operating point. At equal recall its precision is
~19 points worse; at equal precision its recall is ~30 points worse.

Adding a **margin over the runner-up** helps and still does not close it. Best
precision found anywhere in the (threshold × margin) grid: **93.2% at p≥0.5 and
margin ≥0.2, recall 31.6%**.

## What splink does with the owner's NEGATIVE rulings

| threshold | links a tier-X UEI anyway |
|---:|---|
| 0.99 | **0 / 116 (0.0%)** |
| 0.95 | 7 / 116 (6.0%) |
| 0.50 | 28 / 116 (24.1%) |
| 0.10 | 49 / 116 (42.2%) |

**The incumbent links 49 of 117 (41.9%)** — it has no threshold to trade. This
is splink's one clear structural advantage: it can be told to shut up, and 503
cannot.

## Splink as a supplement, not a replacement — the only configuration that could earn a place

Scored **only on the 140 held-out rows the incumbent declined** (503 proposed
205 of 345, was wrong on 19, and said nothing on 140):

| threshold | proposed | correct | precision | recall added over 503 |
|---:|---:|---:|---:|---:|
| 0.9 | 3 | 1 | 33.3% | +0.3 pp |
| **0.5** | **13** | **9** | **69.2%** | **+2.6 pp** |
| 0.3 | 25 | 12 | 48.0% | +3.5 pp |
| 0.1 | 33 | 15 | 45.5% | +4.3 pp |

Two-and-a-half points of recall at 69% precision. **That is queue-grade and
nowhere near apply-grade**, and it is the strongest configuration the pilot
found.

**And splink is no use as a cross-check.** On the 19 held-out rows 503 got
*wrong*, splink at p≥0.5 agrees with the wrong answer 2 times, disagrees 5, and
is silent 12; at p≥0.1 it is 7 agree / 8 disagree. It cannot be used to audit
the incumbent because it is roughly a coin flip on exactly the rows where the
incumbent fails.

## Top-k recall — the metric the reframe actually asks for

| k | true owner in top-k |
|---|---|
| 1 | 55.4% |
| 2 | 62.9% |
| 3 | 64.6% |
| 5 | 67.0% |
| 10 | 68.4% |
| anywhere in the candidate set | **72.2%** ← the blocking ceiling |

The 7.5-point jump from top-1 to top-2 is the whole story of the false
positives: **the true owner is usually the runner-up**. Of the 16 top-1 false
positives at p≥0.5, **11 have the truth at rank 2 or 3**. A queue that shows the
owner three candidates is doing far better than a matcher that must pick one.

## The false positives, in full, because a precision number cannot show their character

```
p=0.9817  Grand Portage Reservation Tribal Council  MN -> Grand Portage Band            (truth rank 2)
p=0.9817  MINNESOTA CHIPPEWA TRIBE - WHITE EARTH B  MN -> Minnesota Chippewa Nation     (truth rank 2)
p=0.9793  Standing Rock Sioux Tribe                 ND -> Standing Rock Community Inc   (truth rank 2)
p=0.9770  UTAH NAVAJO HEALTH SYSTEM INC             UT -> Utah Navaho Health System Inc (truth rank 13)
p=0.9656  College Of Menominee Nations              WI -> College of Menominee Nation   (truth rank 2)
p=0.9564  INDIAN TOWNSHIP TRIBAL GOVERNMENT         ME -> Indian Township Board, Inc.   (truth rank 2)
p=0.9507  HO-CHUNK SHARED SERVICES COMPANY          NE -> Ho-Chunk Community Capital    (truth rank ABSENT)
p=0.9318  Citizen Potawatomi Nation Inco            OK -> Citizen Potawatomi Community  (truth rank 2)
p=0.9139  SANTA ROSA BAND OF CAHUILLA INDIANS       CA -> Santa Rosa Tribe              (truth rank 2)
p=0.8856  SHAKOPEE MDEWAKANTON SIOUX COMMUNITY      MN -> Prairie Island Indian Comm.   (truth rank 2)
p=0.8811  Cherokee Enterprises Inc                  NC -> Cherokee Central High Inc     (truth rank 3)
p=0.7931  FORT PECK MANUFACTURING INC & WEST ELECT  MT -> Fort Peck Community College   (truth rank 2)
p=0.7924  FLANDREAU SANTEE SIOUX TRIBE              SD -> Flandreau Santee Sioux T      (truth rank 10)
p=0.7039  CHOCTAW IKHANA, INC.                      MS -> Choctaw Central Middle Inc    (truth rank 3)
p=0.6360  SENECA STRATEGIC PARTNERS, LLC            NY -> Seneca Nation Economic ...    (truth rank 2)
p=0.5683  KARUK TRIBE OF CALIFORNIA                 CA -> Pauma Tribe of California     (truth rank 4)
```

Three classes:

1. **Sibling confusion inside one nation's family** — the tribe vs its college,
   its school board, its economic-development arm, its CDFI. `Fort Peck
   Manufacturing → Fort Peck Community College`, `College of Menominee Nations →
   College of Menominee Nation`. This is `ENTITY_MATCH_RULES` rule 7 (residue =
   an institution form → HOLD) and **splink has nowhere to put that rule**: it
   is a statement about one record's class, not a comparison between two.
2. **Two distinct federally recognized tribes merged** — `SHAKOPEE MDEWAKANTON
   SIOUX COMMUNITY → Prairie Island Indian Community`, at p=0.8856. **This is a
   UKB/Cherokee-class error and it is the one the brief said would kill the
   recommendation if it landed in the auto-accept band.** It does not — the
   auto-accept band is empty — but any team setting the cut at 0.8 would merge
   two Minnesota Dakota communities.
3. **A genuine near-duplicate in Cedar's own spine** — `UTAH NAVAJO HEALTH
   SYSTEM INC → "Utah Navaho Health System, Inc."` scored 0.977 against a
   truth at rank 13. Two spellings of one organisation both hold spine rows.
   Splink found a Cedar defect and was scored wrong for it.

## The three named collision cases

Full table: `data/interim/splink_pilot/collisions.csv` (103 rows).

| case | splink | incumbent 503 |
|---|---|---|
| **Ho-Chunk Inc (NE) vs Ho-Chunk Nation of Wisconsin** | `HO-CHUNK, INC.` (NE) → `Ho-Chunk Community Capital Inc.` (NE) p=0.9507; **Ho-Chunk Nation of Wisconsin `CE-00150-XS` scored p=0.1878** and lost on state | **FAILS.** `HO CHUNK INC` → `TRBF-HOCHNK-00` (**Wisconsin**), reason *"exact normalized name/alias, unique"* — its strongest evidence class |
| **Eastern Band Cherokee (NC) vs Cherokee Nation (OK) vs UKB (OK)** | never auto-accepts; `CHEROKEE NATION …` companies put **Cherokee Nation and the United Keetoowah Band as top-2 at p≈0.63/0.20** — genuinely uncertain, correctly routed | proposes `TRBF-CHKNAT-00` confidently by *"gov-class distinctive-token match on 'Cherokee Nation'"*; it happens to be right for the CNB subsidiaries and has no way to be uncertain |
| **Seminole of Oklahoma vs Seminole of Florida** | `SEMINOLE NATION SERVICES, LLC` (OK) → **The Seminole Nation of Oklahoma** p=0.2029, with Florida at 0.0299. Direction correct | **FAILS.** → `TRBF-SMNLFL-00` (**Florida**), by *"gov-class distinctive-token match on 'Seminole'"* |

**Splink passes all three under the reframe** (uncertain → queue, never merge).
**The incumbent fails two of the three, confidently.** That is not an argument
for adopting splink — its precision is worse everywhere — but it is the
strongest thing found in this pilot and it points at the real cause below.

## The two live defects this pilot found

Both are in `data/clean/entity_aliases.csv`. Both are realised in
`data/clean/prime_contracts.csv` today. Dollars are small; the class is not.

**D1 — `Ho Chunk Inc` is an alias of the WRONG nation.**

```
entity_id        TRBF-HOCHNK-00   (Ho-Chunk Nation of Wisconsin, CE-00150-XS)
alias_name       Ho Chunk Inc
alias_type       legal
source_system    UEI
```

Ho-Chunk Inc is the **Winnebago Tribe of Nebraska's** holding company
(`TRBF-WNNBGO-00`, `CE-001C8-GH`), and Cedar knows this — every other Ho-Chunk
company is keyed to Winnebago. Live consequence in `prime_contracts`:

| contractor | city | state | current `cedar_uid` | obligations |
|---|---|---|---|---:|
| HO-CHUNK CONSTRUCTION MANAGEMENT SERVICES COMPANY | WINNEBAGO | NE | **CE-00150-XS (WI)** | $0.60M |
| HO CHUNK INC | WINNEBAGO | NE | **CE-00150-XS (WI)** | $0.02M |

**D2 — `Seminole Nation` is an alias of the Seminole Tribe of FLORIDA.**

```
entity_id        TRBF-SMNLFL-00   (Seminole Tribe of Florida, CE-001A9-CA)
alias_name       Seminole Nation
alias_type       full_form_federal_filing
source_system    cedar_generated
```

"Seminole Nation" is the **Oklahoma** tribe's name (`TRBF-SMNLOK-00`,
`CE-001AA-J3`). The spine's own `aliases` column additionally gives the Florida
tribe the bare single token `Seminole`. Live consequence:

| contractor | state | current `cedar_uid` | obligations |
|---|---|---|---:|
| SEMINOLE NATION SERVICES, LLC | OK | **CE-001A9-CA (FL)** | $0.02M |
| HARD ROCK HOTEL AND CASINO TULSA | OK | **CE-001A9-CA (FL)** | $0.00M |

(The Tulsa row is the brand-vs-owner error: Hard Rock is the Florida tribe's
brand, the Tulsa property is Cherokee Nation's.)

**D3 — the structural cause: 503's single-token alias guard is scoped to one
`alias_type`.** `build_index()` refuses a single-token alias only when
`alias_type == 'brand'` — 104 rows. Measured across `entity_aliases.csv`:

| alias_type | single-token rows | guarded? |
|---|---:|---|
| common | 328 | **no** |
| acronym | 141 | **no** |
| brand | 104 | yes |
| shortened | 3 | **no** |
| legal | 3 | **no** |
| | **579 total, 475 unguarded** | |

A blanket refusal would be wrong — `Afognak`, `Ahtna`, `Akutan`, `Akiachak` are
genuine single-word names and `ENTITY_MATCH_RULES` rule 14 says that
orthography is a *positive* signal. The structural predicate is narrower:
**101 single-token index keys are owned outright by one spine entity while the
same token is also a distinctive token of a different one** — `BEAVER`,
`BLACKFEET`, `BRISTOL`, `CADDO`, `CAHUILLA`, `CHEHALIS`, `CHITIMACHA`, `CHUNK`.
Each is a name-only match waiting to fire on the wrong entity.

## Runtime, and whether the DuckDB backend is workable

| operation | scale | wall clock |
|---|---|---|
| full scan + aggregate of `prime_contracts.csv` | **1,217,768 rows / 1.4 GB** | **2.9 s** |
| `prep` end to end (contractors, entities, truth, negatives) | same | **3.8 s** |
| splink u-estimation, 5M sampled pairs | 89.8M possible | 1.7 s |
| splink m-estimation from 345 labels | — | 0.1 s |
| splink `predict` | 209,855 scored pairs from the blocked space | **1.8 s** |
| **splink total, train + predict** | | **6.9 s** |
| incumbent 503 index build + 690 resolves | | **0.1 s** |

**The DuckDB backend is comfortably workable at this scale and would remain so
at 2.8M rows.** Runtime is not a reason to reject splink. Note also that the
1.2M-row table is *not* the linkage input — it collapses to 12,491 distinct
UEIs before any pair is formed. The pair space is set by the entity table, not
the transaction table, and that is true of `faads_transactions_all_agencies`
(2.77M rows) too.

Worth recording separately: **`duckdb` is used by 0 of 515 scripts in this
repo and it read a 1.4 GB CSV in 2.9 seconds.** That finding is independent of
splink and is the larger one.

## The confidence bands, and why the top one is empty

`data/interim/splink_pilot/bands.json`:

```
auto-accept  p >= 0.999     ->  EMPTY BY MEASUREMENT
adjudicate   0.1 <= p < 0.999
auto-reject  p < 0.1
```

**Why 0.999 and not 0.95.** The cut points are taken from the held-out curve,
not chosen round. Precision by band: 100% at p≥0.99 but on **9 rows** (2.6%
recall); 88.5% at p≥0.95; 89.9% at p≥0.5. The best precision available anywhere
in the threshold × margin grid is **93.2%**. Cedar's standing rule is that a
wrong attribution is not expandable while missing coverage is — and one wrong
link in fourteen, applied without a human, is how the $181.9M UKB merge
happened. **There is no auto-accept band on this task at this model quality.
Setting one would be performing confidence rather than measuring it.**

**Why 0.1 for auto-reject.** Recall moves 51.0% → 55.4% between p=0.1 and
p=0.001, so the bottom band discards 4.4 points of true links to remove 21 of
75 false ones and 21 of 49 tier-X violations. That is the trade the owner's
reframe asks for stated numerically; it is a dial, and it is in `bands.json`.

## The adjudication queue

`review/splink_pilot_adjudication_queue_2026-09-02.csv` — **710 rows, $6.39B of
prime obligations**, all in the ADJUDICATE band (auto-accept is empty), sorted
by dollars. Rows already ruled (positive or tier X) and rows already attributed
in `prime_contracts` are excluded; these are open questions only.

Each row carries what the owner's ladder needs, so rung 1–4 need no research:

| column | ladder rung |
|---|---|
| `contractor_city`, `contractor_state`, `proposed_entity_state`, `state_agrees` | **1. the address** |
| `rung2_entity_website` | **2. the website says which tribe** |
| `rung3_other_ueis_at_this_address`, `rung3_already_keyed_at_this_address` | **3. search the address, see what else is there** — the co-located UEIs, and which of them are already keyed |
| `cage_code`, `declared_parent_name`, `declared_parent_uei` | **4. CAGE as a pointer** |
| `match_probability`, `runner_up`, `margin_over_runner_up` | which comparison drove it, and how close the second answer was |
| `owner_ruling` = `ACCEPT \| REFUSE \| REPOINT:<cedar_uid> \| UNRESOLVED` | **6. STOP is a legitimate answer and the form says so** |

`margin_over_runner_up` is the column to sort by after dollars: the false-positive
table above shows the truth is usually the runner-up, so a small margin is not
noise, it is the signal that the queue is asking a real question.

## What usaddress was not needed for

Installed as instructed and then not used. The owner's ladder starts at the
address, but `prime_contracts` already carries `recipient_city_name` and
`recipient_state_code` as **separate parsed columns** — there is no free-text
address string on the contracting side to parse. `usaddress` would earn its
place on the OSHA 300A establishment file (street + ZIP on 100% of rows,
`ENTITY_MATCH_RULES` rule 7 rung 2) or on 990 filer addresses. Not here.

## Honest limitations of this pilot

- **One backlog, one dataset.** Nothing here says what splink would do on the
  nonprofit funnel or on FAADS.
- **The truth set is the owner's own rulings, so it inherits their coverage.**
  302 distinct owners over 690 UEIs; the ANC/ANCSA families are over-represented
  because that is where the dollars and the rulings are.
- **The split is by UEI, not by owner.** An owner can appear on both sides. The
  owner-disjoint split is carried in `truth.csv` as `owner_split` and was not
  scored — splink learns global m/u rather than per-entity parameters, so the
  leakage risk is low, but it is unmeasured.
- **No auto-accept band was validated**, so the "precision within each band"
  the reframe asked for exists for exactly two bands, not three.
- **The 503 baseline is not a fixed target.** It has a hand-built
  `RESOLUTIONS` dictionary, `ADMIN_GEOGRAPHY` / `CIVIC_FORM` / `CIVIC_UTILITY`
  refusals, a leading-token rule, a coverage rule and a parent/constituent rule
  — six domain rules accumulated over a month. Splink was given a week's worth
  of feature engineering. A fair reading is that **the incumbent's advantage is
  the domain rules, not the algorithm**, and those rules have no natural home in
  a Fellegi-Sunter model.

## Files written

```
code/1060_splink_pilot.py                                 the pilot
docs/SPLINK_PILOT_2026-09-02.md                           this report
review/splink_pilot_adjudication_queue_2026-09-02.csv     710 rows, the queue
review/OWNER_DECISION_QUEUE.md                            items 16 and 17 appended
data/interim/splink_pilot/contractors.csv                 12,491
data/interim/splink_pilot/entities.csv                    7,186
data/interim/splink_pilot/truth.csv                       690 + split
data/interim/splink_pilot/negatives.csv                   117
data/interim/splink_pilot/labels_train.csv                345
data/interim/splink_pilot/model.json                      trained m/u
data/interim/splink_pilot/scored_pairs.csv                56,580 candidate pairs
data/interim/splink_pilot/eval.json                       every curve above
data/interim/splink_pilot/false_positives.csv             16
data/interim/splink_pilot/collisions.csv                  103
data/interim/splink_pilot/baseline_truth.csv              690, incumbent's answers
data/interim/splink_pilot/baseline_negatives.csv          117
data/interim/splink_pilot/bands.json                      the cut points
```

Nothing in `data/clean`, `data/spine` or `dist`. Nothing committed.
`py -3 code/1060_splink_pilot.py verify --selftest` passes, and proves both I2
(test leakage) and I4 (collision auto-accept) fire on injected violations and
clear on restore.
