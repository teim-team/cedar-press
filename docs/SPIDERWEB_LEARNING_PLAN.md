# Learning the spiderweb — a plan to mine what we already hold

*Written 2026-09-01. Every number measured today. Do this BEFORE the next
round of dataset building: it raises identity coverage everywhere at once, and
several datasets are blocked on exactly the knowledge it would produce.*

---

## STATUS 2026-09-01 — phases 1 and 2 are BUILT, and this page's own headline number was wrong

`code/523_spiderweb_harvest.py` (workstream J) implements phases 1 and 2. Run
`py -3 code/523_spiderweb_harvest.py all`.

The premise this plan opened with was right - Cedar stores relationships and
barely reads them - and phases 3, 4 and 5 below still stand as written. But
three of the numbers phases 1 and 2 rested on did not survive contact with the
data, so the original phase-1/phase-2 sections are REPLACED by what follows
rather than left standing beside their corrections. The premise table is kept
here for the record:

| table | rows | what we do with it today |
|---|---:|---|
| `cedar_identifier_graph_nodes` | 115,471 | mined by 523 phase 2 |
| `cedar_identifier_graph_edges` | 46,051 | mined by 523 phase 2 |
| `fpds_uei_edges` | **5,167** (was 2,901) | harvested by 523 phase 1 |
| `entity_relationships` | 2,292 | read for hierarchy display |
| `entity_hierarchy` | 952 | read for rollups |
| `prime_sub_network` | 220 | barely read |
| `cedar_spiderweb_v2` | 79 | superseded |

### Correction 1 — the ingest was reading 6 of the 40 files on disk

This plan's sharpest number - **1,097 one-ended edges of 2,901** - was computed
against an edge list that did not yet exist in full. A scan of every CSV under
`data/raw` for a column matching `/parent.*uei/` found **40 files carrying one,
and `13_build_fpds_hierarchy.py` opened 6.** The unread 34 are the
FY2007-FY2026 USAspending contract archive, the 2023-2026 assistance pulls, the
assistance subawards and the gapfill recipient universe. They are already
filtered to the Cedar universe, they total under 900 MB, and they stream in
about ten seconds.

    declared edges        2,901  ->  5,167     (+78%)
    new ownership pairs                1,621
    CAGE triples         29,981  ->  34,601
    network calls                          0
    wall clock                       1.2 min

The largest additions are the ANC families this project cares most about —
ASRC Federal Facilities Logistics under Arctic Slope (38,821 observations),
FSS Alutiiq under Afognak, Affigent under NANA, five Chugach subsidiaries,
Goldbelt Raven under Goldbelt. **This is the second time the same defect was
found** — 2026-08-30 added one assistance file for +611 edges and stopped
there. The file list is now GLOBBED, not enumerated, because enumeration is how
the gap opened.

Two smaller ingest defects were fixed in the same pass. The literal string
`NAN` was being emitted as a parent UEI for 12 children spanning 11 different
Cedar entities — a UEI is twelve characters, and malformed values were being
counted for the report but still written. And **five** registrants record as
GOVERNMENT OF THE UNITED STATES while the `blocklisted_parent` column flags
one, so the roll-up set is now derived from the recorded name on every run.

### Correction 2 — "keyed" has two definitions and they differ by 1,222 UEIs

| surface | UEIs keyed |
|---|---:|
| `cedar_identifier_ledger_final.csv` | 4,074 |
| `cedar_identifier_graph_nodes.csv` (`resolved_entity`) | 4,904 |
| union | 5,296 |

Asking only the ledger reports roughly twice the harvest that exists: 856 edges
have an "unkeyed" end the identifier graph already resolves. Those are a
**ledger backfill**, not new identification, and they land in their own named
decline bucket. Any future count of "unkeyed" must say which surface it asked.

### Correction 3 — most one-ended edges point UP, not down

This page reads as though each one-ended edge hands us a new subsidiary. It
does not. Measured: **56 entities gained a declared PARENT, 34 gained a
declared subsidiary.** The dominant shape is a holding company sitting *above*
an entity we already hold — the Ho-Chunk caveat in `NATIVE_ENTITY_NUANCES.md`
seen from the other side.

---

## What phase 1 produces now

    source edges                                             5,167
    ACCEPTED one-ended ownership edges                         268
    candidate rows (incl. 32 sibling)                          300
        intermediate_holdco   165     subsidiary_of              65
        unclear                38     sibling_under_same_parent  32
    distinct candidate firms                                   159
    Cedar entities touched                                      86
    identifier-backfill candidates     258 rows / 246 UEIs / 7 disputed
    suspect keyed anchors REFUSED       73 links over 43 entities

Every declined edge sits in a named bucket and the buckets sum to 5,167
(`523_spiderweb_declines.csv`, enforced as invariant I5).

| output | what it is |
|---|---|
| `review/523_spiderweb_ownership_candidates.csv` | ranked tier-B candidates; `unambiguous = Y` is the rule-first slice |
| `review/523_spiderweb_candidate_firms.csv` | firm-level rollup with conflict flags |
| `review/523_identifier_backfill_candidates.csv` | UEIs that ARE entities we already hold |
| `review/523_suspect_keyed_anchors.csv` | existing ledger links the harvest refused to build on |
| `review/523_spiderweb_declines.csv` | the full accounting |
| `review/523_idgraph_q1..q4_*.csv` | the four phase-2 queues |

All three actionable batches are written up in `review/OWNER_DECISION_QUEUE.md`
item 9, with the consequence of each answer stated.

## The hand validation, and what it cost to be honest about it

A random sample of 20 candidates (seed 20260901) was checked by hand against
the spine, the ledger and the source edge. **The first pass stood up 8 times
out of 20.** Nothing was fabricated — every row cited a real declared edge —
but the classification was wrong 11 times, always the same way: one registrant
holding two UEIs, published as an intermediate holding company.

    KOMAN CONSTRUCTION, LLC      ->  KOMAN CONSTRUCTION LLC
    GILA RIVER INDIAN COMMUNITY  ->  GILA RIVER INDIAN COMMUNITY
    TATITLEK TECHNOLOGIES        ->  TATITLEK CORPORATION  (= the entity itself)

The generator was fixed rather than the rate reported. Six discriminating rules
came out of it, each carrying the counter-example that bounds it:

1. **Identical declared names on the same edge are one registrant, not two.**
   Within-row string equality — no spine lookup, so no Bristol Bay exposure.
2. **The entity's own name, longer.** The spine stores "Gila River"; the
   registrant files "GILA RIVER INDIAN COMMUNITY". Same entity when the
   entity's distinctive tokens are all present and every extra is a class word.
   *Counter-example that forces a uniqueness test:* `Delaware Nation` and
   `Delaware Tribe of Indians` are two sovereigns and both reduce to
   {DELAWARE}, so the rule fires only when that token set belongs to ONE spine
   entity.
3. **`LIMITED LIABILITY COMPANY` is a legal form, not a name.**
   *Counter-example:* `TEPA EC, LLC` and `TEPA LLC` differ by {EC}, which is
   not a class word — a real subsidiary and its real parent. A plain prefix
   test merges them; a class-words-only difference does not.
4. **Fold diacritics before stripping non-ASCII.** Ukpeagvik Inupiat
   Corporation is written with a dotted g in the spine; blanking it split the
   token, so the corporation failed to match itself and was published as a
   holding company above itself.
5. **An unreviewed name cluster is not an anchor.** Barrow holds 103 UEIs, 58
   of them `cluster_v3` "Algorithmic name clustering, unreviewed", clustered on
   the word GOVERNMENT — its real subsidiary is UIC **Government** Services
   LLC, and the cluster swept in Computer Sciences Corporation and General
   Dynamics IT. If a link's legal name shares no distinctive token with its
   entity, nothing may hang from it.
6. **A place named for a tribe is not the tribe** (the Tuscarawas precedent,
   met twice here). `KLAMATH 9-1-1 EMERGENCY COMMUNICATIONS DISTRICT` and
   `COUNTY OF MOULTRIE` (Illinois) each share a token with the tribe they were
   keyed to. A local-government form word in the name means the shared place
   name is the whole of the evidence, and that is not enough.

Also learned, and applied to the ranking rather than to a filter: **one
observation is a filing, not a pattern.** OKLAHOMA STATE UNIVERSITY MEDICAL
AUTHORITY declares CHOCTAW NATION OF OKLAHOMA as its parent on exactly one 2026
row. Real data, wrong conclusion. Single-observation edges stay as candidates
and are excluded from `unambiguous`.

**After the fixes, the same-seed sample stands up 18 of 20.** Both remaining
failures are inherited rather than generated: the keyed end is itself keyed to
the wrong Native entity in the ledger (`Qivliq Commercial Group` under NANA,
`FSI Holdings` under Koniag). Neither is a fabricated relationship, and both
are the same disease as section 9c of the owner queue.

## Phase 2 — the four queues, measured

| # | question | answer | file |
|---|---|---|---|
| 1 | unkeyed identifiers co-occurring with keyed ones | **200**, all unambiguous. Cherokee Boys Club ($315M), Cherokee General ($263M), Miccosukee Corporation ($246M) lead. Most co-occurrence was already consumed by `169`; this is the residue, and it is the high-dollar residue. | `523_idgraph_q1_cooccurrence.csv` |
| 2 | names clustering to identifiers | **9,814** clusters: **154 CONTAMINATION_RISK** (one name, two entities) and **614 alias material**. Review, never auto-apply. | `523_idgraph_q2_name_clusters.csv` |
| 3 | identifiers in many datasets carrying no entity | **90,539**, ranked by dataset count then dollars. **346 in two or more datasets**, **$506B** observed. The head is not obscure: Southcentral Foundation $3.1B, Norton Sound Health $952M, White Earth $652M, Warm Springs $597M, CRIHB $571M, Seminole Nation of Oklahoma $440M. | `523_idgraph_q3_unkeyed_by_dataset_count.csv` |
| 4 | one entity holding identifiers that never co-occur | **708** entities; **52** where two dollar-bearing islands share no name stem. `TRBF-DELAWN-00` ranks fifth with 14 identifiers in 9 components, one stemmed UNAMI — the Delaware contamination, found independently by this method. | `523_idgraph_q4_split_entity_suspects.csv` |

Q3 first reported 90,889 and ranked ONEIDA NATION ($1.1B) second while it sat
in the ledger the whole time, because it asked only the graph. Corrected to the
union. A work queue that sends a reviewer at finished work is worse than no
queue.

Q4 is a REVIEW queue and its verdict says so: a tribe legitimately holds
differently-named subsidiaries, so the shape is not itself a defect. The rank
says where a two-entities-merged-under-one-uid error is most findable.

## Guards, and the proof they fire

`523 verify` checks six invariants; `523 fixtures` injects a violation of each,
asserts exit 1, restores in a `finally` and asserts exit 0.

    I1 tier B, never A            I2 no transitive closure
    I3 federal roll-ups blocked   I4 prime_to_sub is not ownership
    I5 every edge in a NAMED bucket, summing to the source count
    I0 a hops-1 candidate's unkeyed end is not in fact keyed

## What phase 1 deliberately did NOT do

No spine entity was minted, `510 --apply` was not run, and the identifier
ledger was not edited. Two things are queued for whoever owns them:

* **`169_build_identifier_graph.py` should be re-run.** It was built against
  2,901 edges and there are now 5,167. Q1 and Q3 will both improve.
* **The 73 suspect anchors need rulings.** They are already carrying dollars in
  shipped tables; the harvest refusing to build on them does not unwind them.

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
