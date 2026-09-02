# Linkage close — 2026-09-02, workstream LINKAGE

*`code/1139_linkage_coverage.py` (measure + gate) · `code/1140_linkage_close.py`
(close the gap). Model decision: **ADR-037**. Coverage table:
`docs/LINKAGE_COVERAGE.md`, generated, do not hand-edit.*

Owner mandate, 2026-09-02: *"try to link native entities to the things more.
fact check, anything you're uncertain about, you have the ability to reconcile
unless it's something super obscure… don't focus on building more, focus on
making everything we have good."*

---

## What moved

| dataset | LINKED before | LINKED after | what changed |
|---|---:|---:|---|
| `legislation` | **no entity column existed** | 591 of 3,069 (19.26%) | the bridge was on disk and unreachable |
| `contractors` | 789,360 (64.82%) | 791,839 (65.02%) | +2,034 rows / **$803,507,507** (a ruling stamped and never keyed), +318 / $87,926,027 (declared ultimate parent), +127 / $15,015,304 (sibling registrations) |
| `funding` | 552,602 / 553,106 / 549,530 *(three columns, three answers)* | 549,136 (78.23%) | +154 McGrath rows; −504 rows that claimed an attribution they did not have |
| identifier ledger | — | +163 rows | `fpds_uei_cage_map.csv` bridged, tier inherited |

Every figure re-derivable: `py -3 code/1139_linkage_coverage.py report` and
`py -3 code/1140_linkage_close.py verify`.

---

## T1 — `legislation` shipped with no way to reach a Native entity

`dist/customer/legislation.csv` carried `sponsor_bioguide_id` — a member of
Congress — and nothing else. `affected_entities` is present and **blank on all
3,069 rows**.

`data/clean/native_bills_entity_bridge.csv` held **676 named-entity links over
591 bills** the whole time. It is one-to-many on `bill_id`, so
`1137_customer_dataset_combine.py` correctly refused to LEFT JOIN it — that
multiplies the flagship, and a bill naming five tribes must not become five
bills. The fix is the shape `nagpra_notices` already ships: collapse to one row
per bill, pipe-delimited, with a count and a basis.

Ten columns added: `has_resolved_entity`, `n_entities_resolved`,
`entity_tribe_ids`, `entity_cedar_uids`, `entity_names`, `entity_link_tiers`,
`entity_link_basis`, plus three for the class layer below. Tiers are inherited
from the bridge row (560 A / 116 B) and are not upgraded.

### `native_bills_entity_class.csv` is NOT that bridge and must never be used as one

It is 2,694 rows over 2,456 bills and its own `class_match_basis` column says,
on every row:

> *"This is a CLASS-level fact, NOT a claim about any individual entity — no
> tribe_id is asserted."*

`n_spine_entities_in_class` is **348**. Reading it as entity linkage would
attribute the Indian Health Care Improvement Act to 348 tribes individually.
It was promoted anyway, because it is genuinely useful to a customer, into
**separately named columns that say what they are** —
`entity_class_scope` / `n_entity_classes` / `entity_class_scope_basis`, whose
basis text begins *"CLASS-LEVEL SCOPE, NOT AN ENTITY LINK"* — and it is
excluded from the linked numerator. Two different facts, two different
columns, and a customer can tell them apart.

---

## T2 — McGrath Native Village Council, 154 rows / $11,384,182.32

`docs/KNOWN_ISSUES.md` `ESCAPE-COLLAPSE-1136-RESOLUTION` left this as an
explicit proposal: a collapsed regex escape in `503_identity.py` meant
`MC GRATH NATIVE VILLAGE COUNCIL` did not fold to `MCGRATH`, and the prior
agent repaired the code but declined to key the dollars, because keying a
dollar is a ruling. Adjudicated here, against the owner's own ladder
(`ENTITY_MATCH_RULES` rule 13) rather than against the name fold, which is
weaker evidence than what was already on the row:

| rung | evidence |
|---|---|
| **1 · address** | recipient city `MC GRATH` / `MCGRATH`, state `AK`. Exactly one Cedar entity sits in McGrath, Alaska: `AKNF-MCGRTH-00-DOYONL-TNNACH`, `fr_official_name` "McGrath Native Village", aliases "McGrath Native Village\|Mcgrath". |
| **3 · the record's own words** | filed name `MC GRATH NATIVE VILLAGE COUNCIL`. Residue against the hub's canonical + FR-official + alias names is `{COUNCIL}` — a governmental word, not an institution form. For an Alaska Native village the council **is** the governing body. |
| corroboration | 150 of the 154 rows carry one recipient UEI, `KC9WGEJJHED3`. The awarding agencies' own `business_types_description` reads `INDIAN/NATIVE AMERICAN TRIBAL GOVERNMENT (FEDERALLY-RECOGNIZED)` on 22 rows, over CFDA programmes open only to federally recognized tribes: Consolidated Tribal Government, Indian Education Assistance to Schools, EPA GAP, Coronavirus Relief Fund, Coronavirus Capital Projects Fund. |

**That corroboration is the same evidence family as the row itself**
(USAspending), so this is **one leg, not two** — `docs/ASSERTION_LAYER.md`, and
copying a source into a second column does not corroborate it. Written at
**tier B**, method `agent_research_one_leg`, matching the house precedent in
`review/agent_identifier_rulings_applied.csv`. Rule 8: an agent ruling may not
mint tier A.

**The published figure was 151 rows / $11,358,100.32 and the true one is 154 /
$11,384,182.32.** The difference is three rows already spelled `MCGRATH`
without the space ($26,082.00) — the same recipient, the same UEI-less filings,
and outside a count built from the broken-fold spelling. A count derived from
the shape of a bug measures the bug.

### And the thing the fold would have missed

The ledger holds **four** UEIs on `AKNF-MCGRTH-00-DOYONL-TNNACH`, all tier B
`cluster_v3`, all quarantined — `Mcgrath Contractors Llc` ($316.7M prime),
`Northwest Mcgrath Jv`, `Htl Mcgrath B & B Llc`, `Mcgrath Light And Power` —
and **not one of them is `KC9WGEJJHED3`, the tribal government's own UEI**.
Cedar held four surname matches on a one-word hub name and did not hold the
entity's own registration. `Mcgrath Contractors Llc` sits at
`quarantine_disposition = KEEP` on "rule 7: residue empty", which is what rule
7 does when the hub's canonical name is a single common surname; it is left
alone here and flagged in `docs/KNOWN_ISSUES.md`.

**`HOTEL MCGRATH, LLC` is also keyed to the village government today**
(`uei_exact_archive`, from the quarantine-HOLD `Htl Mcgrath B & B Llc` row).
Net obligation is $0.00 — an offsetting pair — so there is no money exposure,
and HOLD is the honest state. Not touched.

---

## T3 — a ruling that was stamped and never written onto the row

**2,034 prime rows / $803,507,507 / 10 firms** carried
`ruling_status = RULED_ATTRIBUTED`, `ruling_applied_date = 2026-08-26`, and a
**blank `tribe_id`, blank `cedar_uid`, `attributed_flag = 0`**.

The rulings are real, documented, and live. `review/agent_identifier_rulings_
applied.csv` and `review/agent_rulings_conflicts_2026-08-06.csv` each carry a
retrieved-document leg and an explicit `resolve_entity ->` verdict, and the
CAGE rows they produced are in `cedar_identifier_ledger_final.csv` **today**,
tier A/B, unquarantined:

| CAGE | firm | ruled to | tier | leg |
|---|---|---|---|---|
| `6TVR9` | Four Tribes Construction Services LLC | Susanville | **A** | two-leg: declared parent UEI n=100 + fourtribes.com |
| `63Y57`, `7WA41`, `7VT93` | Four Tribes Construction / Enterprises / Air JV | Susanville | B | fourtribes.com, *"the Susanville Indian Rancheria community"* |
| `6LBT0` | ATI Government Solutions LLC | Susanville | B | tribalbusinessnews.com suspension notice |
| `4LVM3` | A+ Government Solutions | The Chickasaw Nation | **A** | two-leg: the firm's own SAM Corporate URL is chickasawfederal.com/aplus |
| `3V7E1` | Red Cedar Enterprises Inc | Modoc Nation | B | modocnation.one business list |
| `0VPR2`, `5UD76` | Muskogee Metal Works / Muskogee Technology | Poarch | B | SAM: 601 Muskogee Blvd, Atmore AL |
| `48AX7` | First Mesa Consolidated Villages | Hopi | B | SAM: Polacca AZ, `3I - Tribal Government` |

**What happened is `AGENT_FIELD_GUIDE` rule 6 at $803M.** The UEI leg was
WITHDRAWN by the quarantine sweep — correctly, because those UEIs pointed at
Te-Moak, Barrow, Enterprise and Paiute of Utah, which the rulings refute — and
the CAGE leg that carries the adjudication was never re-applied to the row.
The decision was written into a sibling file and into a `ruling_status`
string; it was never written into the columns `40_build_prime_contracts.py`
branches on.

Applied: `tribe_id`, `cedar_uid`, `canonical_name`, `attributed_flag = 1`,
`attribution_method = ruling_applied` (an existing value in that column's
vocabulary, 4,331 rows before this pass), `confidence_tier` **inherited from
the ledger row**. Prior values for all 2,034 rows are in
`review/linkage_close_prime_prior_values_2026-09-02.csv`.

Every prime row's `cage_code` matches the CAGE named in the ruling exactly.
`ruled_but_unreachable` is **0** — no `RULED_ATTRIBUTED` row was left without
a live ledger identifier.

---

## T4 — what `fpds_uei_cage_map.csv` is actually worth, gated

This source was carried into the session as *"the highest-yield unused source
measured"*. It is not, and the reason is worth more than the rows.

A registrant's UEI and its CAGE name one registration, so holding the pair and
one side yields the other. Swept against the ledger that is **130 new CAGE
rows and 33 new UEI rows** — 163 identifiers Cedar can now resolve. Written,
tier inherited, method `fpds_uei_cage_bridge`, literal `NAN` cage codes
(2,196 rows / 2,193 UEIs) excluded before the join.

**And it attributes nothing in `prime_contracts` or
`federal_funding_transactions` today.** The ungated sweep looks like a
windfall:

| gate | new prime rows | USD |
|---|---:|---:|
| none | 25,372 | $4.19B |
| + the identifier maps to exactly one entity | 20,459 | $3.50B |
| + drop tier X source rows | 457 | $334.75M |
| + drop quarantined / WITHDRAW / HOLD sources | 457 | $334.75M |
| + drop tier C source rows | **0** | **$0** |

**20,002 rows and $3.17B of the apparent yield is propagation out of tier X
ledger rows — NEGATIVE rulings.** That is `START_HERE` trap 1b arriving
through a new door: the exactness of the key says nothing about the
correctness of the link, and a tier is inherited from the source row, never
assigned by the consumer. The remaining 457 rows rest on tier C sources
(`web_verified`, `subsidiary_lookup`) and tier C does not key a dollar.

---

## T7 — the declared ULTIMATE parent, which was on disk the whole time

`data/clean/fpds_uei_edges.csv` carries parent/child UEI relationships **the
registrant filed about itself** — the identifier evidence rule 4 asks for.
Rule 11 sets the thresholds: an edge observed 20+ times is ownership, and
**the parent's tier does not transfer**, so every row here is written at tier
B even where the parent's ledger row is tier A.

**318 rows / $87,926,026.94, three entities.**

| firm | declared ultimate parent | observations | rows | amount |
|---|---|---:|---:|---:|
| Sage Systems Technologies (2 name renderings) | OLD HARBOR NATIVE CORPORATION → `ANVC-LDHRBR-00` | 1,204 | 283 | $65,231,689 |
| Hal Hays Construction, Inc. (3 registrations) | HAL HAYS CONSTRUCTION, INC. → `CEDAR-ENT-000084` | 26–37 | 24 | $18,407,525 |
| Polu Kai Services, Llc | POLU KAI SERVICES, LLC → `CEDAR-ENT-000085` | 34 | 11 | $4,286,813 |

Two of the three are the multiple-registration case the owner describes:
*"they'll get a new CAGE technically as a new company for the 8(a)
pass-through stuff, but it's literally the same company."*

### The refusal is the interesting half

**`Nisga'A Tek, LLC` — 64 rows, $167,829,000, the largest candidate by a
factor of two — is refused.** It declares `GOLDBELT HAWK L.L.C.` as its
parent **70 times**, comfortably over rule 11's floor, and Goldbelt Hawk is a
tier-A Goldbelt registration. It is refused because that edge is
`parent_uei`, not `ultimate_parent_uei`, and **the immediate level is exactly
where an 8(a) mentor-protégé JOINT VENTURE declares its managing venturer.**
The Nisga'a are a British Columbia First Nation, so the firm reads as a
cross-border JV, and an aggregate party must never resolve to one entity.

Requiring the ULTIMATE edge excludes it **structurally**, not by hand — which
is the difference between a rule and a list. The gate is also `n_observations
>= 20`, `blocklisted_parent` unset (78 of 2,684 edges are roll-ups like
GOVERNMENT OF THE UNITED STATES), the parent resolving to exactly one live
entity, and the child declaring exactly one ultimate parent, because two is a
joint venture.

---

## T5 — 504 rows / $494,305,407.20 that said they were keyed and were not

`attribution_status = 'cedar_neid'`, `attributed_flag = '1'`,
`canonical_name = 'Bristol Bay Native Corporation'`, and `tribe_id_neid` and
`cedar_uid` **blank**. The second half of the FA-01 unlink: the keys were
cleared, the status columns were not.

Measured across the whole table, **0 of 146,717 honestly-`unattributed` rows
carry a `canonical_name`**, so the table's own convention is unambiguous and
these 504 breach it. Set to `unattributed` / `attributed_flag = 0` /
`canonical_name` cleared, with the withdrawn name preserved verbatim in
`attribution_basis`. **This does not pre-empt the pending BBAHC repoint**
(`review/OWNER_DECISION_QUEUE.md` item 1): it makes the row say what is true
today, which is that nothing is keyed.

---

## WHAT THIS PASS REFUSED, and why the refusal is the finding

**12,058 prime rows / $3.26B / 49 entities** are unattributed, unruled, and
reachable by an identifier already in the ledger at tier A/B, unquarantined,
resolving to exactly one entity. Every single one is
`attribution_method = cross_dataset_propagation:contracting`, and the residue
is the token defect the field guide names:

```
BLUE SKIES FURNITURE LLC        -> Blue Lake Rancheria     $100.9M   token `blue`
CREEK GOVERNMENT SERVICES CO.   -> Barrow                  $1,097M
EAGLE ENGINEERING & LAND DEV.   -> Village of Eagle        $1,088M
EARTH FRIENDLY CHEMICALS, INC.  -> Minnesota Chippewa
ROCKY MT SPORT OFFICIALS INC    -> Rocky Boy
MUDDY CREEK OIL & GAS, INC.     -> Big Pine
JACKSON D SUMMERS               -> a natural person
PORTALATIN, MICHAEL             -> a natural person
```

The pipeline already declines these and it is right to. **A gap is not always
evidence waiting to be used**, and an unlinked row is an honest outcome
(ADR-010) in a way a wrong key never is.

---

## Figures carried into this session that do NOT reproduce

Each re-measured 2026-09-02 against the live files. Recorded so the next reader
does not re-derive them.

| carried as | measured today | where |
|---|---|---|
| "509 entities have never been checked for a CAGE or UEI at all" | **1,439 of 1,555** entities are `NEVER_CHECKED` for `identifiers`; 85 HARVESTED, 17 FOUND_NOT_EXTRACTED, 11 REFUSED, 3 CHECKED_ABSENT | `data/clean/cedar_harvest_coverage_matrix.csv`. Agrees with `AGENT_FIELD_GUIDE` §7's "1,439 of 1,555 (92.5%)" and not with 509 |
| "1,088 `FOUND_NOT_EXTRACTED` surfaces" | **280 matrix cells** over 246 entities, or **7,538 evidence rows** — neither is 1,088 | `cedar_harvest_coverage_matrix.csv` / `..._evidence.csv` |
| "`fpds_uei_cage_map.csv` reaches 666 of 1,555 spine entities — the highest-yield unused source" | 6,858 distinct real (UEI, CAGE) pairs; gated yield **163 identifiers and 0 attributed rows** — see T4 | `code/1140_linkage_close.py report --only ledger` |
| "151 rows / $11,358,100.32" of McGrath assistance | **154 rows / $11,384,182.32** — see T2 | `docs/KNOWN_ISSUES.md` ESCAPE-COLLAPSE-1136-RESOLUTION |
| "`subcontracting` 44.8% — the lowest rate of any large dataset" | **97.59%.** `cedar_uid` on `subawards` is the PRIME leg — it equals `prime_cedar_uid` on 39,567 of its 40,201 non-blank values — and it is **blank by design** on the majority population, where the Native party is the SUBAWARDEE. 44.77% is that column's fill rate, not coverage. **Nothing was written at those rows**, and writing a subawardee id into `cedar_uid` would make one column mean two things | `code/1139_linkage_coverage.py`, the `subcontracting` role sentence |
| a coverage scan reporting `nagpra`, `legislation` and `native-owned-businesses` as having **no entity key** | only `legislation` was true. `nagpra` is 90.83% linked through six LIST-VALUED role columns; `native-owned-businesses` is 94.89% linked through the certifying nation | ADR-037 §2, §3 |

**"3,306 of the owner's v6 UEIs are in no Cedar table at all" was NOT
re-measured here** and is not disputed. `data/staging/nest_owner_v6/` was being
written by another workstream during this pass (14:59) and was left alone.

---

## Ordering — this is an IN-PLACE enricher on three flagships

Declared in `cedar_pipeline.KNOWN_ORDERINGS` (three pairs, added by this pass):

```
14_build_bills_votes.py   -> 1140_linkage_close.py   native_bills.csv
24_funding_merge.py       -> 1140_linkage_close.py   federal_funding_transactions.csv
40_build_prime_contracts.py -> 1140_linkage_close.py prime_contracts.csv
```

A rebuild REVERTS this pass and will look like pure progress while it happens.
`py -3 code/1140_linkage_close.py verify` exits 1 when it has been reverted.
On `prime_contracts`, 1140 must run **after** 1079 — 1079's withdrawals are
what stranded the rulings in the first place.

### The ratchet fired within the hour, on a rebuild, and that taught it something

The first shape of `linkage_<dataset>_rows` was a ZERO-TOLERANCE floor on the
absolute count of linked rows, argued for on the grounds that a fall in links
must never hide inside a ratio's tolerance. That is right. It is also
insufficient on a flagship nine agents are rebuilding.

Ninety seconds after the baseline was recorded, `verify` failed:

```
linkage_native_owned_businesses_rows = 4,124, below its floor of 4,125
linkage_linked_rows_total            = 1,485,083, below its floor of 1,485,084
```

Measured: `native_owned_businesses.csv` was rewritten at 18:09 by another
workstream, **4,274 -> 4,273 rows and 4,125 -> 4,124 links**. One row left the
table and took its link with it. **That is not a linkage regression and the
check could not say so**, because it watched the numerator with no sight of
the denominator.

**The fix is not a tolerance.** A blanket 0.1% slack would have been 791 rows
on `prime_contracts`, which is exactly the hiding place the zero-tolerance
argument was made against. The denominator now travels with the numerator as
`linkage_<dataset>_denom`, and the rule is:

> **A link may fall by as many rows as the table itself lost, and not one
> more.** A link cannot survive a row that does not exist; a link lost from a
> row that DOES still exist is the defect, and it fails with no tolerance at
> all.

`selftest` proves both halves: floor + 1 link with the denominator held
FAILS; floor + 1 link with the denominator also + 1 PASSES; floor + 2 links
with the denominator + 1 FAILS and names the one link that left a row which
still exists.

The baseline was re-recorded to carry the denominators, which is what the new
shape needs to work at all. **It was not re-recorded to clear a red light** —
the red light was measured first, its cause named and dated, and it is written
down here rather than absorbed.

### One thing the verify got wrong before it shipped

The first draft of `verify` asserted
`ruling_status='RULED_ATTRIBUTED' AND attributed_flag='1' AND tribe_id<>''` with
a floor of 2,034. **456,514 rows already satisfied that predicate before the
pass ran**, so it would have printed PASS beside a table where nothing had been
written — `AGENT_FIELD_GUIDE` rule 5 exactly, and it was caught only by
printing the pre-state. The floor is now on
`attribution_method = 'ruling_applied'` at 4,331 + 2,034 = 6,365, which can
only be met by the write happening. `1140 selftest` raises each floor to
live + 1 and asserts exit 1 on every one.

### One thing Windows got wrong during it

`os.replace` on `prime_contracts.csv` (1.57 GB) raised
`PermissionError [WinError 5]` after a complete and correct `.part` had been
written — another of the nine concurrent agents held a handle. The live table
was untouched. `rewrite()` now retries for 60 seconds and RAISES rather than
leave a `.part` a later reader could mistake for the table.
