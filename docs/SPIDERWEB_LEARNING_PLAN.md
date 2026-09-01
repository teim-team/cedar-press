# Learning the spiderweb — a plan to mine what we already hold

*Written 2026-09-01. Every number measured today. Do this BEFORE the next
round of dataset building: it raises identity coverage everywhere at once, and
several datasets are blocked on exactly the knowledge it would produce.*

---

## The premise

Cedar has been *storing* relationships and only lightly *reading* them. The
owner's framing — "I don't think you've actually learned as much as you could
about the linkages" — is correct, and it is measurable.

| table | rows | what we do with it today |
|---|---:|---|
| `cedar_identifier_graph_nodes` | **115,471** | built, essentially unmined |
| `cedar_identifier_graph_edges` | **46,051** | built, essentially unmined |
| `fpds_uei_edges` | 2,901 | read for parent lookups only |
| `entity_relationships` | 2,292 | read for hierarchy display |
| `entity_hierarchy` | 952 | read for rollups |
| `prime_sub_network` | 220 | barely read |
| `cedar_spiderweb_v2` | 79 | superseded |

## The single sharpest number

Of 2,901 declared ownership edges:

| | edges |
|---|---:|
| both ends keyed to a Cedar entity | 712 |
| **exactly one end keyed** | **1,097** |
| neither end keyed | 1,092 |

**Those 1,097 are the harvest.** Each is a *named firm* that a registrant
declared into the corporate family of an entity we already know. It is not a
name-match guess — it is a FAR-declared relationship, the strongest
non-proprietary ownership evidence available, and we are throwing away the
identification it hands us.

Known parents with the most unkeyed children today: Arctic Slope Regional
Corporation (4), Sealaska (4), Cherokee Nation (2), Eastern Band of Cherokee
(2), plus intermediate holdcos like APM LLC (6) and Hal Hays Construction (4)
that are themselves unkeyed and sit between a tribe and its subsidiaries.

---

## Phase 1 — harvest the one-ended edges (highest value, lowest risk)

For each of the 1,097, the keyed end gives the family and the unkeyed end
gives a name and a UEI. Produce a **candidate** row per edge — never an
automatic spine entity — carrying:

- the declared relationship and its direction,
- the keyed end's `cedar_uid`,
- the unkeyed end's UEI, CAGE, legal name, state,
- an **attachment class**: `subsidiary_of` / `intermediate_holdco` /
  `sibling_under_same_parent` / `unclear`,
- and the tier: **B, never A** — a declaration is evidence of a connection,
  not proof of Native ownership. `docs/NATIVE_ENTITY_NUANCES.md` already
  records why: the declared highest owner is often the highest *incorporated*
  owner, and the last hop to the tribe is ours, not SAM's.

**Transitive closure is explicitly out of scope.** If A→B and B→C are both
declared, we do NOT assert A→C. Chains break at holdcos, and inventing the
closure is how a spiderweb becomes a fabrication.

Expected: several hundred firms newly attributable, and a measurable rise in
the 48% global keyed rate.

## Phase 2 — mine the 46,051-edge identifier graph

Untouched. It links identifiers to observed names across datasets, which is
precisely the evidence needed for the four questions we keep answering by hand:

1. **Which unkeyed identifiers co-occur with keyed ones** on the same
   document, award or filing? Co-occurrence is weak evidence alone but strong
   when combined with a declared edge.
2. **Which observed names cluster to one identifier?** That is the alias
   layer's raw material, and the Delaware contamination (a CAGE legal name
   equating two distinct tribes) proves the clustering must be *reviewed*, not
   applied.
3. **Which identifiers appear in many datasets but carry no entity?** Ranked by
   dataset count, that is a prioritised work queue instead of a flat list.
4. **Where does one entity hold identifiers that never co-occur?** A possible
   sign of two entities merged under one uid — the inverse of the duplicate
   problem, and currently invisible.

## Phase 3 — multi-party as a first-class shape

The owner is right that this is broader than deals. Measured today:

| dataset | reality | what we store |
|---|---|---|
| **subawards** | prime + sub is **necessarily** ≥2 parties | prime/sub columns — usable, but no shared party bridge |
| **deals** | joint ventures, multi-tribe consortia | `native_party_entity_id` — **singular, cannot represent it** |
| **admin appeals** | multiple appellants | plural column that never holds >1 |
| **federal funding** | joint/consortium awards possible | unmeasured — needs checking |
| **nagpra** | many consulted + affiliated tribes | **done right**: three plural id columns |

**Adopt the nagpra shape everywhere**: a party bridge at
`(record_id, cedar_uid, role)` grain. Roles matter — prime vs sub, acquirer vs
acquired, appellant vs respondent, consulted vs affiliated are not
interchangeable, and a role-less bridge loses the thing that makes it useful.

## Phase 4 — ownership continuity (old owner vs new owner)

The owner's example is exactly right: when a federal contractor changes hands
we should record *both* owners with their dates, not overwrite.

The machinery already exists and is unused for this — `515_temporal.py` gives
`valid_from` / `valid_to` per claim, and the as-of resolver already answers
"who owned this on the transaction date". What is missing is the **event**:

```
ownership_change(uei, from_uid, to_uid, effective_date, evidence, basis)
```

Today only **84 of 189 dated ownership deals state a real effective date**,
and 5 explicitly disclaim their own closing date in prose. So this phase is
evidence-bound: build the event table, populate what is genuinely dated, and
leave the rest UNKNOWN. Never infer a transition date from when we first
observed the new owner — that is observation time wearing validity's clothes,
and `docs/TEMPORAL_MODEL.md` already forbids it.

Payoff: the 9,402 transactions ($2.1B) where the temporal layer *contradicts*
the shipped owner become adjudicable instead of merely flagged.

## Phase 5 — turn what we learn into rules

The owner's actual ask: *"at some point you should be able to surpass me."*
That happens only if each adjudication leaves behind a rule rather than a row.

After each batch of rulings, extract:

- **the discriminating feature** — what actually separated the right answer
  from the wrong one (place-name suffix, gov-class, state token, in-language
  enterprise name, foundation-vs-parent);
- **the counter-example** that makes it a rule and not a habit;
- **where it belongs** — a guard in `503`, a nuance in
  `NATIVE_ENTITY_NUANCES.md`, or a lint class if code keeps re-committing it.

The precedents already in the file are the model: the Elim gov-class
restriction, "a place named for a tribe is not the tribe" (Tuscarawas), state
tokens never stripped (Oneida NY/WI), in-language enterprise names
(Suh'dutsing), and — new this week — *the filer is not always the entity*
(Chugachmiut's EIN files as a language nonprofit in Indiana).

**Measure the learning, not the effort:** rulings needed per 100 new
identifications should fall pass over pass. If it does not, we are doing
casework, not learning.

---

## A finding that belongs here: the NHO universe

The owner asked whether the 210 NHOs come from the DOI list. **Yes — 179 of
210 carry `verification_route = doi_onhr_notification_list`, grade
`doi_roster_only`.** The rest are NHOA directory members, self-statements and
one owner ruling.

The contracting overlap is much smaller than the roster:

| | |
|---|---:|
| NHOs in the spine | 210 |
| with ANY federal identifier (UEI/CAGE/EIN) | **15** |
| with prime contract dollars > 0 | **6** |

So 210 is the right number for *the DOI universe* and 6 is the right number
for *NHOs visible in federal contracting* — both true, different questions.
At **7% identifier coverage this is the largest proportional identity gap in
the master list**, and it is a good Phase 1/2 target: NHO subsidiaries and
8(a) entities are exactly the kind of thing declared edges reveal.

---

## Order and exit criteria

1. **Phase 1** — one-ended edges → candidates. *Exit:* global keyed rate
   measurably up; every candidate tier-B with its declared evidence.
2. **Phase 3** — party bridges for subawards and deals. *Exit:* a multi-party
   deal representable, and the 12 known ones represented.
3. **Phase 2** — identifier-graph mining. *Exit:* a ranked work queue
   replacing the flat unkeyed list.
4. **Phase 4** — ownership events. *Exit:* the $2.1B contradiction bucket
   adjudicable.
5. **Phase 5** runs continuously, after every batch.

Nothing here mints a spine entity automatically. Everything lands as an
evidenced candidate, and the ruling stays a ruling.
