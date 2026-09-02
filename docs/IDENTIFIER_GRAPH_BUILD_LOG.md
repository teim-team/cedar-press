# The cross-identifier graph — UEI ↔ CAGE ↔ EIN ↔ DUNS ↔ tribe_id

*Built 2026-08-26 by `code/169_build_identifier_graph.py`. Zero network calls.
Every number below is measured at run time; regenerate rather than hand-edit.
The run's own stdout is at `docs/IDENTIFIER_GRAPH_RUN.txt`, the machine copy at
`docs/IDENTIFIER_GRAPH_SUMMARY.json`.*

This answers work-queue item 2 and tests the project owner's hypothesis:

> "federal spending, prime and subcontracting datasets have a lot of overlap
> since they all use the same id system — UEI and CAGE code. It could be
> possible the IRS data links to these as well, particularly federal spending,
> so we have their EIN and CAGE code, UEI."

**Half of it is right and half of it is measurably wrong, and the wrong half is
the more useful finding.** The spending datasets do share an identifier system.
The IRS data does not join to it at all. And the shared system does not reach
the unattributed tail, because the unattributed tail has no second identifier.

---

## THE HEADLINE, IN ONE TABLE

| | |
|---|---:|
| Prime rows unattributed (`attributed_flag = 0`) | **328,965** |
| Prime UEIs carrying ≥1 tier-C row | **9,386** |
| Prime UEIs with **zero** attributed rows | **9,277** |
| Dollars on the unattributed rows | **$65.24B** |
| **…that propagation resolves with no new human ruling** | **57 UEIs · $0.42B · 0.6%** |
| **…that propagation resolves at a PUBLISHABLE tier (A)** | **0 UEIs · $0.00B** |

The 9,386 / 328,965 / $65.2B figures in the task brief reproduce exactly.
9,386 counts UEIs with at least one tier-C row; 9,277 is the subset with no
attributed row at all. Both are correct about different things — say which.

### Why 0.6% and not more — the whole answer in five lines

| status of the 9,277 unattributed prime UEIs | UEIs | share | dollars |
|---|---:|---:|---:|
| **isolated** — no CAGE, no DUNS, no EIN, in no other dataset | **5,405** | 58.3% | $10.16B |
| has an identity edge, but nothing on the far end is attributed | **3,691** | 39.8% | **$51.06B** |
| blocked by a tier-X negative ruling | 111 | 1.2% | $1.33B |
| **resolved by propagation** | **57** | 0.6% | $0.42B |
| one identifier, several entities — refused, sent to review | 13 | 0.1% | $0.00B |

**The identifier system is shared. The identifiers are not.** Of the 9,277
unattributed prime UEIs, only **162** appear anywhere in assistance and **245**
in subawards, and of those only **25** and **51** carry an attribution on the
other side. The cross-dataset overlap is real but it sits almost entirely on
the *already attributed* head of the distribution: 786 UEIs are shared between
prime and assistance in total.

**This is a coverage ceiling, not a build defect.** $51.06B of unattributed
prime money sits on UEIs that DO carry a CAGE — the CAGE simply leads nowhere,
because nothing at the other end of it has ever been attributed either. No
amount of graph work moves that. It moves when a human rules, or when a
name/entity route is built. Identifier propagation is finished at $0.42B.

---

## LIFT PER DATASET

Measured as: identifiers that are **wholly unattributed in that dataset** and
that the graph resolves to exactly one entity **from a source other than that
dataset's own rows**.

| dataset | ids | unattributed ids | **propagated** | unattributed $ | **propagated $** | tier A | tier B |
|---|---:|---:|---:|---:|---:|---:|---:|
| `prime_contracts` (UEI) | 12,491 | 9,277 | **57** | $65.24B | **$0.42B** | 0 | 57 |
| `federal_funding` (UEI) | 6,372 | 4,870 | **207** | $48.18B | **$6.04B** | 22 | 185 |
| `subawards` (UEI) | 8,829 | 7,504 | **31** | $14.09B | **$0.11B** | 8 | 23 |
| `faads` (DUNS) | 70,481 | 70,481 | **862** | $415.07B | **$2.06B** | 0 | 862 |
| **total** | | | **1,157** | | **$8.63B** | **30** | **1,127** |

**$0.084B of that is tier A and may publish. $8.55B is tier B and never
publishes alone.** Writing the tier-B rows back into a source table as though
they were settled would be the exact bug this project already shipped once.

### Where the real lift is: assistance, not prime

Assistance gains **$6.04B on 207 recipients**, and the top of that list is
plainly correct on inspection — registrations that one dataset had already
resolved and another had not:

| UEI | name in assistance | resolved to | $ unattributed | route |
|---|---|---|---:|---|
| `D37SXRJ5HMJ1` | DENA NENA HENASH | `SGVF-TNNACH-00` Tanana Chiefs Conference | $1,782.7M | subawards |
| `DT3GJW3JNMN5` | GREAT PLAINS TRIBAL LEADERS HEALTH BOARD | `ITO-GRTPL1-00` | $646.6M | subawards |
| `C471YH1GMPX7` | NORTHWEST INDIAN FISHERIES COMMISSION | `ITO-NRTHWS-00` | $287.9M | subawards |
| `G81MSXW3MJR3` | UNITED TRIBES TECHNICAL COLLEGE | `TCU-NTDTRB-00` | $277.1M | prime |
| `ZNHWRF8EAJJ9` | NW PORTLAND AREA INDIAN HEALTH BOARD | `ITO-NRTHW2-00` | $250.2M | subawards |

*Dena Nena Henash* is the Athabascan name of Tanana Chiefs Conference — a link
no name matcher was going to make, and the identifier made it for free.

### FAADS: 0% → 862 DUNS, and a hard ceiling above it

FAADS was 0% linked. It now has **862 DUNS resolved, $2.06B**, entirely through
the UEI↔DUNS co-observations that the assistance file carries across the April
2022 DUNS→UEI transition.

**Its ceiling is 24.4% of rows, and that is a property of the source.**
2,092,713 of 2,769,748 FAADS rows carry **no identifier at all** — no DUNS, no
UEI, $1,415.6B of the $1,830.6B total. Only 676,035 rows (70,481 DUNS) can ever
be reached by an identifier route. The rest is a name-and-state problem, which
is the tier-B name floor already recorded in AGENTS.md, not this graph.

---

## THE IRS HYPOTHESIS — TESTED, AND THE ANSWER IS ESSENTIALLY ZERO

A measured zero is a finding. Every line below is counted, not estimated.

### (a) No spending dataset carries an EIN column at all

| file | EIN columns |
|---|---|
| `prime_contracts.csv` | **NONE** |
| `federal_funding_transactions.csv` | **NONE** |
| `subawards.csv` | **NONE** |
| `faads_transactions_all_agencies.csv` | **NONE** |

`funding_identifier_harvest.csv` *has* a `recipient_ein` column. It is
**0-populated on all 37,704 rows.** The column exists; the data never did.

So there is no direct join. UEI/CAGE is a SAM registration namespace, EIN is an
IRS namespace, and no federal spending file republishes the second.

### (b) Through every identity edge in the graph, 3 hops, hub guard on

| | |
|---|---:|
| `np_orgs` distinct EINs | 12,764 |
| …with a Native classification ruling | 89 |
| Schedule I distinct filer EINs | 627 |
| Schedule I distinct recipient EINs | 18,708 |
| distinct UEIs across prime + assistance + subawards | 25,419 |
| **EINs with ANY identity edge to a UEI, anywhere in the corpus** | **28** |
| **`np_orgs` EINs reaching a spending UEI** | **28 of 12,764 — 0.22%** |
| Schedule I **filer** EINs reaching a spending UEI | **4 of 627** |
| Schedule I **recipient** EINs reaching a spending UEI | **12 of 18,708 — 0.06%** |
| spending UEIs reached | 28 |
| dollars on those 28 UEIs | $2.967B |
| **reverse: spending UEIs with ANY EIN edge** | **28 of 25,419 — 0.11%** |

### (c) Why it is 28, and why 28 is the whole ceiling of the existing bridges

**`np_ein_uei_bridge.csv` has 28 rows.** The task brief lists it among the
existing bridges to reuse, alongside files of 24,977 and 20,559 rows. It is 28
rows, all tier B, all `normalized_name_plus_state_exact`. Every EIN→UEI link in
this project runs through those 28 rows.

And the one file that *could* have carried more does not:

    need_v6_geocoded.csv rows with BOTH an EIN and a UEI     0
    need_v6_geocoded.csv rows with an EIN and no UEI     1,104

**The project's own enterprise table never once puts an EIN and a UEI on the
same row.** Those 1,104 EIN-only rows are precisely the ledger's 1,104 EIN
rows — the ones that are 6.5%-accurate `need_v6` and that produced UNITED WAY
OF THE GREATER CHIPPEWA VALLEY → United Auburn. The EIN leg and the UEI leg of
this project are **disjoint populations that have never been joined by an
identifier.**

### What this means for the hypothesis

The hypothesis was *"we have their EIN and CAGE code, UEI"*. Measured: for a
nonprofit we have an EIN and nothing else; for a contractor we have a UEI and a
CAGE and nothing else. **0.22% of the IRS population and 0.11% of the spending
population have both.**

Closing that gap is a **new build**, not a propagation:

1. **The only exact route that exists is SAM.** A SAM entity registration
   carries the registrant's TIN/EIN. `api.sam.gov` extracts are already wired
   (`code/141`), and the entity-management extract — not the contract-award
   extract used for FY2000–07 — is where an EIN would come from. This is the
   single highest-value unworked identifier source in the project, and it is
   blocked on the same 10/day → 1,000/day role request that blocks subawards.
2. **Everything else is a name match**, which is `need_v6`'s method at 6.5%
   accuracy. It may be built as a **candidate** file at tier B or C; it must
   never be tiered A on the strength of the EIN being exact. The exactness of
   the key says nothing about the correctness of the link.
3. **A 990 filing fact still says nothing about Native status** (AGENTS.md, the
   New Venture Fund case). An EIN↔UEI identity edge is a claim about one legal
   person holding two identifiers — never a claim that the person is Native.

---

## HOW THE GRAPH IS BUILT

Nodes are identifiers (`UEI:`, `CAGE:`, `EIN:`, `DUNS:`) and entities
(`ENTITY:<tribe_id>`). Edges come in three kinds.

| kind | meaning | assertions read | distinct edges written |
|---|---|---:|---:|
| `IDENTITY` | two identifiers name one registrant | 35,856 | **15,608** |
| `ATTRIBUTION` | an identifier belongs to a Native entity | 18,471 | **18,307** |
| `BLOCK` | a tier-X negative ruling on the identifier | 12,136 | **12,136** |

Identity edges by pair type: **CAGE↔UEI 9,665 · DUNS↔UEI 5,915 · EIN↔UEI 28.**
Every one of them is tier B — no source in this project asserts an
identifier-to-identifier identity at a ruled tier. **11,451 of the 15,608 are
asserted by more than one source**; `n_asserting_sources` records that and it
**never promotes the tier**, because two-leg promotion is a ledger method and
not a consumer's to mint. Attribution edges: 4,856 tier A, 13,428 tier B, 23
tier C.

Written to `data/clean/cedar_identifier_graph_edges.csv` (46,051 rows),
`data/clean/cedar_identifier_graph_nodes.csv` (115,471 nodes) and
`data/clean/cedar_identifier_propagation.csv` (1,157 proposed links).

### Sources, and where each edge's tier comes from

| source | edges | tier comes from |
|---|---:|---|
| `cedar_identifier_ledger_final.csv` | 7,890 attr + 197 blocks | row column `confidence_tier` |
| `cross_dataset_ruling_map.csv` | 7,228 blocks | `ruling` = `BLOCKED: …` |
| `fpds_uei_cage_map.csv` | 7,456 UEI↔CAGE | **`SOURCE_TIER` declaration, B** |
| `cedar_cage_backfill.csv` | 4,361 UEI↔CAGE | **`SOURCE_TIER` declaration, B** |
| `need_v6_geocoded.csv` | 4,059 UEI↔CAGE | **`SOURCE_TIER` declaration, B** |
| `funding_identifier_harvest.csv` | 7,905 UEI↔DUNS | **`SOURCE_TIER` declaration, B** |
| `subaward_identifier_harvest.csv` | 271 UEI↔CAGE | **`SOURCE_TIER` declaration, B** |
| `np_ein_uei_bridge.csv` | 28 EIN↔UEI | row column `confidence_tier` |
| `np_ein_entity_hub.csv` | 2,303 EIN→ENTITY | row column `link_tier` |
| `np_orgs.csv` | 1,456 EIN→ENTITY + 4,711 blocks | row column `cedar_link_tier` |
| `bie_uio_identifier_links.csv` | 217 → ENTITY | row column `confidence_tier` |
| `prime_contracts.csv` | 3,218 attr + UEI↔CAGE | row column `confidence_tier` |
| `federal_funding_transactions.csv` | 1,707 attr + UEI↔DUNS | row column `confidence_tier`, capped by the crosswalk hop |
| `subawards.csv` | 1,516 attr + UEI↔CAGE | row columns `sub_native_tier` / `prime_native_tier` |

**A tier is INHERITED, never assigned by the consumer.** Where the source has a
tier column the value is copied verbatim and `edge_tier_source` names the
column. Where it has none, the tier is declared **once**, in `SOURCE_TIER` in
the script, with a written reason — and none of those declarations is above B,
because a co-observation of two identifiers on one transaction is a filer's
declaration, not a ruling.

**A propagated link is never stronger than its weakest edge.** `derived_tier =
min(tier of every edge traversed)`. The full path is on the row, and the
weakest link is named in `weakest_edge_source`.

A tier-C attribution is the string "unattributed" — it propagates nothing. A
tier-X row blocks the node and is never overridden by a lower-tier positive.

### The assistance vocabulary hop, and why it caps a path

`federal_funding_transactions.csv` keys 1,043 of its recipients to a **legacy
integer** `tribe_id` from the do-file, not to a spine id. Translating it takes
`assistance_tribe_id_crosswalk.csv`, whose own rows state tier B ("a resolver
match is tier B"). So a tier-A assistance attribution on a legacy id emerges as
**tier B** after the hop, and the row says so in words. 333,382 assistance rows
took the hop; 13,208 found no legacy id in the crosswalk.

### THE HUB GUARD — the guard that stops this becoming the old bug

A CAGE, DUNS or EIN sitting on ONE UEI is an identity. The same string sitting
on SEVERAL UEIs is a **hub**, and walking through it is how
one-identifier-many-entities turns into an attribution:

    UEI-A → CAGE-X → UEI-B → UEI-B's tribe

**16 CAGEs are shared by more than one UEI.** A hub is *reachable* — its own
attributions are inherited by every UEI that carries it, because
many-identifiers-to-one-entity is expected — but it is **never expanded
through** to another UEI. The permissive answer was measured too: allowing hub
traversal adds exactly **1** identifier, which is written to review rather than
counted. The guard costs nothing and forecloses the whole failure class.

### What was deliberately NOT used

- **`parent_uei` / `ultimate_parent_uei` is not an identity edge.** A parent is
  a different legal person, and AGENTS.md is explicit that FPDS hierarchy is
  evidence, not authority, and does not update retroactively on an ownership
  change. Measured anyway: **20 unattributed identifiers, $0.926B**, have a
  parent that resolves to a Native entity. They are in the review file as
  `PARENT_UEI_CANDIDATE_NOT_AN_IDENTITY` and need a ruling that the subsidiary
  is *owned by*, not merely *reported under*, that parent.
- **SAM socio-economic flags.** `americanIndianOwned = YES` appears on 2,846 of
  8,273 rows of the TRIBAL extract. A self-certification does not separate
  classes and is not used as a discriminator anywhere in this build.
- **Name matching.** Not attempted. It is `need_v6`'s method, measured at 6.5%.

---

## ONE-TO-MANY DEFECTS — 874 identifiers, and they sort into four named families

Many identifiers → one entity is expected: the 8(a) nine-year term drives
tribes and ANCs to spin up successor firms, and 267 name-clusters covering 623
unattributed UEIs and $14.98B already show it. **Nothing in this build flags
that direction.**

One identifier → many entities is a defect. 874 were found. **No attribution
was made on any of them**; all are in
`review/identifier_one_to_many_defects_2026-08-26.csv` with both paths and both
asserting sources.

| family | n | $ observed | what it is |
|---|---:|---:|---|
| **`ALASKA_VILLAGE_GOVERNMENT_VS_VILLAGE_CORPORATION`** | **334** | **$24.52B** | `AKNF-CHNEGA-00-CHGCCO-CHGCMT` (Chenega, the village government) vs `ANVC-CHENEG-00` (Chenega Corporation). Both are real spine rows. This is the containment defect's direction-2 case — "NATIVE VILLAGE OF ELIM → Elim Native **Corporation**" — arriving through the identifier path instead of the name path. |
| `MIXED_CLASS` | 301 | $9.01B | entities of different classes on one identifier |
| **`TWO_DIFFERENT_TRIBES_ON_ONE_IDENTIFIER`** | **188** | **$10.36B** | a genuine dispute, or a spine short-name collision |
| `CONSTITUENT_BAND_VS_UMBRELLA_TRIBE` | 42 | $1.30B | `CNSF-MINNCH-WE` White Earth vs `TRBF-MINNCH-00` Minnesota Chippewa |
| `INTERTRIBAL_ORGANISATION_VS_MEMBER_TRIBE` | 9 | $0.66B | a consortium's registration booked to one member |

Plus 20 `PARENT_UEI_CANDIDATE_NOT_AN_IDENTITY`, 16
`ONE_IDENTIFIER_SHARED_BY_MANY_UEIS` and 1
`REACHABLE_ONLY_THROUGH_AN_AMBIGUOUS_HUB`. **911 rows total.**

### The dollars are a quality risk, not a coverage gap — say which

**Only 13 of the 874 defects sit on an unattributed prime UEI ($1.14B). 252 sit
on an ALREADY-ATTRIBUTED prime UEI, carrying $38.57B.** That money is already
booked to one of the two disputed entities. These are not rows waiting to be
filled in; they are rows already filled in where a second source disagrees.

### The five biggest, each of which is a named trap this project already knows

| UEI | name | disputed between | $ observed |
|---|---|---|---:|
| `WVJKC2L1ZN11` | S And K Aerospace | `TRBF-CSKTFR-00` Confederated Salish and Kootenai **vs** `TRBF-KTNIID-00` Kootenai Tribe of Idaho | **$2,591.6M** |
| `HZ8CHGL3B3S6` | ONEIDA NATION | `TRBF-ONDANY-00` **vs** `TRBF-ONDAWI-00` | $1,110.8M |
| `M8X2FJFF9DN8` | Chenega Technology Services | village government **vs** village corporation | $1,032.4M |
| `WLMABW85RSW9` | Alutiiq International Solutions | `AKNF-AFGNAK-00-KONIAG` **vs** `ANVC-AFOGNA-00` | $796.9M |
| `HLTFBD3FTDG8` | Confederated Tribes of Warm Springs | `TRBF-FSCWSA-00` Fort Sill-Chiricahua-**Warm Springs**-Apache (OK) **vs** `TRBF-WRMSPR-00` Warm Springs (OR) | $597.4M |

The first is the **Kootenai regression** already named in AGENTS.md. The second
is `cedar_domain.STANDING_DISAMBIGUATIONS` entry 1, in the data, on $1.1B. The
last is a new one: **"warm springs" is a tribe name that is also part of a
different tribe's name**, and it belongs in `NAME_TRAPS` alongside `wichita`.

**One ruling settles 334 of these.** The Alaska family asks one question — when
an 8(a) operating company registers, does the registration belong to the
village government or the village corporation? — and the answer applies to
every row in the family.

---

## THE MEASUREMENT THAT SHOULD CHANGE WHAT GETS BUILT NEXT

Ranked by dollars per unit of human effort:

1. **334 Alaska village-government-vs-corporation defects, $24.52B, ONE
   ruling.** Highest ratio in the project by a wide margin.
2. **188 two-tribes-on-one-identifier defects, $10.36B.** Test each against the
   RAW spine first — AGENTS.md records two independent builds that reported a
   resolver defect where the resolver was right and the spine name collided.
3. **The SAM entity-management extract**, for the EIN. It is the only exact
   EIN↔UEI route that exists, and it turns a 0.22% overlap into a real one.
   Blocked on the same role request as subawards FY2021–24.
4. **$51.06B of unattributed prime money on UEIs that have a CAGE that leads
   nowhere.** Not reachable by any graph work. It needs the name/entity route
   or a human.
5. **1,157 propagated links are sitting in
   `data/clean/cedar_identifier_propagation.csv` and nothing consumes them.**
   Built is not done. The 30 tier-A rows may be written back to source with the
   `124_apply_rulings_in_place.py` pattern; the 1,127 tier-B rows may not.

---

## FILES

| file | rows | note |
|---|---:|---|
| `data/clean/cedar_identifier_graph_edges.csv` | 46,051 | every edge with its evidence, source and inherited tier |
| `data/clean/cedar_identifier_graph_nodes.csv` | 115,471 | one row per identifier, with its resolution and its block |
| `data/clean/cedar_identifier_propagation.csv` | 1,157 | PROPOSED links. 30 tier A, 1,127 tier B. Not written back. |
| `review/identifier_one_to_many_defects_2026-08-26.csv` | 911 | every refusal, with both paths |
| `data/clean/codebook/05b_identifier_graph.csv` | 46 | fragment only; the master is never written |

**Nothing shared was rewritten.** `prime_contracts.csv`, the spine, the ledger
and the nonprofit tables were read and not touched — other agents are live on
all four. `62_no_regression_check.py` after the run: **no regressions**, and
`tables_missing_codebook_block` fell 144 → 141.

**Concurrency note — the sources moved DURING this run, and by how much is
recorded rather than smoothed over.** `cedar_identifier_ledger_final.csv` held
**20,577** rows at read time, not the 20,559 in `START_HERE.md`; a concurrent
agent is applying rulings to it and to `prime_contracts.csv` (both rewritten at
17:57, the same minute as these outputs). Re-measured against the file as it
stood after that write:

| | at extract | after the concurrent write |
|---|---:|---:|
| prime unattributed rows | 328,965 | **328,906** |
| prime fully-unattributed UEIs | 9,277 | **9,276** |
| prime unattributed dollars | $65.240B | **$65.240B** |
| tier A rows | 586,185 | 586,244 |

59 rows moved C → A while this ran. **The dollar figure is unchanged to three
decimals and no conclusion here turns on the difference.** Re-run 169 after the
ruling agent lands; it is idempotent, reads everything and rewrites nothing but
its own outputs.

---

## THE RULE THIS BUILD EARNS

**Two datasets sharing an identifier SYSTEM is not the same fact as two
datasets sharing IDENTIFIERS, and the first is routinely mistaken for the
second.**

Prime, assistance and subawards all key on UEI and CAGE. That made the overlap
sound like a coverage answer. Measured, the overlap is 786 UEIs between prime
and assistance — and only 162 of the 9,277 unattributed prime UEIs appear in
assistance at all. **58.3% of the unattributed tail holds exactly one
identifier and nothing else, in any file, anywhere in the corpus.** A shared
namespace guarantees that two rows *can* be joined; it says nothing about
whether the same actor ever appears in both.

The corollary for the IRS question: EIN and UEI are not a shared system at all,
they are two namespaces with no republished join, and the measured overlap is
0.22% / 0.11%. **Before planning work on an identifier join, measure the
intersection, not the schema.**


---

## UPDATE 2026-08-26 - the 334 Alaska defects are RULED and APPLIED

The line above - *"One ruling settles 334 of these"* - was right, and the ruling
landed the same day. See `docs/ANCSA_OWNERSHIP_RULING.md` for the rule and the
full application record.

| | |
|---|---:|
| resolved to the VILLAGE CORPORATION (rule 1) | **322** ($24,384.6M) |
| resolved to a village GOVERNMENT (rule 3, evidenced) | **0** |
| still need a human (rule-3 candidate 2, held 2, unverified corp 8) | **12** ($133.2M) |
| government-side legs REFUSED under rule 2 | **334** |
| individual attributions repointed across 3 tables | **3,883** |
| tiers changed | **0** |

`links_on_village_corporations` in `62_no_regression_check.py` rose
**911 -> 963** and the gate is green with no regressions.

**Three things this build log should carry forward:**

1. **The family note was right about the direction and wrong about nothing.**
   This really was the containment defect's direction-2 case arriving through
   the identifier path. 238 of the 334 nodes already carried a SETTLED human
   ruling and **not one named a village government**.
2. **`status` is not `outcome`.** A first pass read `status = SETTLED` as
   confirmation and resolved `UEI:VJ4MGKFTMVJ8` onto a ruling whose `outcome`
   was `HOLD_OVER_OWNER` and whose text said *"HOLD - RETRACTION REQUIRED"*.
   Any consumer of `cedar_ruling_ledger_consolidated.csv` must filter
   `outcome = ENTITY`; `status` only says the ruling was processed.
3. **`MIXED_CLASS` is NOT this question in disguise** - measured, 4 of 301 rows
   are even touched, and those are CONSTRAINED by rule 5 rather than settled.
   `review/ancsa_adjacent_family_scan_2026-08-26.csv` has the per-row verdict.

**Re-run `169_build_identifier_graph.py` now.** It is idempotent, reads
everything and rewrites only its own outputs, and 3,883 attributions moved
underneath it - so the 911-row defect file it produced is stale for this
family by construction.
