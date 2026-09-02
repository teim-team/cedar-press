# The `review/` backlog — rulings, with the evidence each rests on

*Decided 2026-09-01 by `int-3-review` under the owner's standing rule of the same day: "you decide how to fix them ... as long as you document the decisions and learn from them." Machine-readable: `data/staging/review_backlog_class_dispositions.csv`. Triage that produced the questions: `docs/REVIEW_BACKLOG.md`.*

**Two of the eleven are deliberately NOT decided here.** 16.11 (tribal vendor-list consent) is held for the owner because it is a question about Cedar's relationship with the nations whose lists those are, not a method question. 16.5 (OSHA) belongs to INT-1.

## What was decided, in one table

| ruling | rows | decision in one line |
|---|---:|---|
| **16.1** The identifier-graph scoping doctrine | 102,051 rows across eight 523_* files | THREE LINES, adopted |
| **16.2** The adjudication-hub party method | 15,999 rows across seven files | ADOPTED AT TIER B, with two conditions that must BOTH hold: the party name matches a spine canonical or official name exactly after normalisation, AND the docke |
| **16.3** The SAM self-certification ceiling | 15,557 rows (12,645 + 2,912) | CONFIRMED AS A HARD CEILING |
| **16.4** Does a text mention make it that entity's comment | 4,806 rows | NO |
| **16.5** OSHA establishments - NOT DECIDED HERE | 711 establishments / 1,879 filings - INT-1 | OWNED BY INT-1, who holds the labor promotion and was handed both files with the token-match evidence |
| **16.6** Lineage reconciliation: which Cedar entity does this UEI belong to | 749 | Decide by the UEI's OWN declared name, tested against the candidate entity's OFFICIAL name in the spine |
| **16.7** 1,223 proposed tier B -> tier A promotions | 1223 | Rule by BASIS, not by row |
| **16.8** 1,049 proposed NAGPRA aliases | 1049 | Accept an alias seen in 3 or more independent Federal Register notices; refuse a single-notice spelling; hold two |
| **16.9** 6,796 unresolved congressional earmark recipients | 6796 | Same doctrine as 16.2 - name + state exact or nothing |
| **16.10** 6,094 unresolved subaward parties | 6094 | Rule by `resolver_how` |
| **16.11** Tribal vendor-list consent - NOT DECIDED HERE | 62 rows - owner | HELD FOR THE OWNER, deliberately |

## Dispositions applied

| disposition | rows |
|---|---:|
| `FLOOR` | 11,356 |
| `REFUSE` | 2,182 |
| `HOLD` | 706 |
| `DEFECT` | 637 |
| `ACCEPT` | 546 |
| `AFFIRM_TIER_B` | 484 |
| **total** | **15,911** |

Every row now carries a NAMED disposition, which is contract point **C5**. `FLOOR` and `HOLD` are honest outcomes: ADR-010 makes `unresolved` a legitimate record scope, and a wrong key is worse than no key.

---

## 16.1 — The identifier-graph scoping doctrine

**Scope:** 102,051 rows across eight 523_* files

**Decision.** THREE LINES, adopted. (1) Cedar keys the top 100 unkeyed identifier nodes by observed dollars, BY HAND, with an identifier or the entity's own statement as evidence. (2) Nothing below n_datasets >= 2 is ever auto-keyed: one dataset seeing an identifier is one source's spelling, not corroboration. (3) Everything else is a PUBLISHED COVERAGE FLOOR, stated in the codebook as 'N identifiers observed and not keyed', never as an implied zero. Measured basis: of 90,539 nodes, only 346 reach n_datasets >= 2 and 22 reach 3; the top 100 carry $17.4B of the $506.5B observed. The doctrine therefore disposes of 90,193 nodes at line 3 without a single name match.

---

## 16.2 — The adjudication-hub party method

**Scope:** 15,999 rows across seven files

**Decision.** ADOPTED AT TIER B, with two conditions that must BOTH hold: the party name matches a spine canonical or official name exactly after normalisation, AND the docket's state agrees with the entity's state. A docket party is a legal filing, so the name is the party's own - that is what lifts it above a scraped string - but it is still a name, and `UMATILLA ELECTRIC COOPERATIVE` reached a tribe by this exact route until a guard landed in 503 today. Sequencing is part of the ruling: run `168_resource_revenue_ceiling` (5 rows) FIRST as the fixture, confirm the method by hand on all five, then generalise. A method proven on five rows costs an afternoon; a method assumed over 15,999 costs a retraction.

---

## 16.3 — The SAM self-certification ceiling

**Scope:** 15,557 rows (12,645 + 2,912)

**Decision.** CONFIRMED AS A HARD CEILING. A SAM `awardeeBusinessTypeName` Native flag never, on its own, puts a firm in the Cedar universe above tier C, and tier C never publishes alone. Both files close as a STATED FLOOR rather than as a queue. The reasoning is the project's premise: a self-certification is the registrant's claim about itself, and Cedar does not republish claims as facts. The value in these 15,557 rows was never the per-firm attribution - it is the AGGREGATE, and that is now shipped: `data/clean/sam_native_class_distributions.csv`, 176 cells, small-cell suppressed, promoted 2026-09-01.

---

## 16.4 — Does a text mention make it that entity's comment

**Scope:** 4,806 rows

**Decision.** NO. `regulations_gov_comments.csv` keeps its title-match universe and the 4,806 text-only mentions stay out of it. The table's unit of analysis is THE TRIBE SPEAKING; a comment that criticises a nation mentions it exactly as loudly as one the nation filed, so admitting the class would silently change what the table measures. The information is not discarded: it ships as a `mentions` count on `regulations_gov_entity_coverage.csv`, which is a coverage table and can carry it honestly.

---

## 16.5 — OSHA establishments - NOT DECIDED HERE

**Scope:** 711 establishments / 1,879 filings - INT-1

**Decision.** OWNED BY INT-1, who holds the labor promotion and was handed both files with the token-match evidence. Not touched here.

---

## 16.6 — Lineage reconciliation: which Cedar entity does this UEI belong to

**Scope:** 749 rows, $68.5B of federal assistance

**Decision.** Decide by the UEI's OWN declared name, tested against the candidate entity's OFFICIAL name in the spine. Neither lineage's label is evidence about the other.

| disposition | rows | dollars |
|---|---:|---:|
| `ACCEPT` | 278 | $58.66B |
| `FLOOR` | 245 | $4.32B |
| `HOLD` | 224 | $6.48B |
| `REFUSE` | 2 | $0.0M |

<details><summary>Worked examples, one per disposition</summary>

- **`ACCEPT`** — `NAVAJO NATION TRIBAL GOVERNMENT, THE` → `TRBF-NAVAJO-00`<br>Both lineages resolve to the same entity and every distinctive token of the filed name appears in that entity's own official name.
- **`FLOOR`** — `NORTHERN ARAPAHO TRIBE`<br>No candidate entity was ever proposed for this UEI. Published as stated coverage, not as a zero.
- **`HOLD`** — `NAVAJO HOUSING AUTHORITY` → `TRBF-NAVAJO-00`<br>The registrant's filed name adds an institution-form token the entity's own official name does not carry: AUTHORITY,HOUSING. A body the nation created is not the nation.
- **`REFUSE`** — `CHEYENNE RIVER CHAMBER OF COMMERCE` → `TRBF-CHYNRV-00`<br>503 loose-path guard fired: REFUSED_CIVIC_FORM:CHAMBER - a civic organisation carrying a place name

</details>

---

## 16.7 — 1,223 proposed tier B -> tier A promotions

**Scope:** 1,223 rows

**Decision.** Rule by BASIS, not by row. ZERO promotions to tier A: not one of the 1,223 carries an identifier, and tier A is an identifier grade. Refuse the two name-only classes outright, affirm the moderate ones at B, hold the conflicted ones.

| disposition | rows | dollars |
|---|---:|---:|
| `REFUSE` | 552 | — |
| `AFFIRM_TIER_B` | 484 | — |
| `HOLD` | 187 | — |

<details><summary>Worked examples, one per disposition</summary>

- **`REFUSE`** — `San Juan` → `TRBF-SNJUAN-00`<br>basis=no_tribal_designator_in_context - The context carries no word placing the subject in Indian Country. This is the exact shape of UMATILLA ELECTRIC COOPERATIVE: the tribe's distinctive token is a place name every local body in the county carries. A name-only match with no designator may never reach tier A.
- **`AFFIRM_TIER_B`** — `Calista Corporation` → `ANRC-CALSTA-00`<br>basis=exact_span_with_tribal_designator_in_context;matched_in_abstract_not_t - An exact name span WITH a tribal designator is real evidence, but the match landed in an abstract rather than a title, and no identifier corroborates it. Tier B is the correct home; it is not a defect.
- **`HOLD`** — `White Earth Band of Chippewa Indians` → `CNSF-MINNCH-WE`<br>basis=resolver_containment - Containment is explicitly a WEAK evidence class (ENTITY_MATCH_RULES checklist step 2) and needs a second independent signal. None is attached, so it stays at B and is not refused.

</details>

---

## 16.8 — 1,049 proposed NAGPRA aliases

**Scope:** 1,049 rows

**Decision.** Accept an alias seen in 3 or more independent Federal Register notices; refuse a single-notice spelling; hold two. The threshold is calibrated, not chosen: the earlier recognition-alias pass rejected 76 of 228 proposals on review, a 33% error rate, which is far too high to auto-apply at n=1.

| disposition | rows | dollars |
|---|---:|---:|
| `REFUSE` | 670 | — |
| `ACCEPT` | 211 | — |
| `HOLD` | 168 | — |

<details><summary>Worked examples, one per disposition</summary>

- **`ACCEPT`** — `Arapahoe Tribe of the Wind River Reservation, Wyoming`<br>Seen in 76 independent notices. Three separate federal publications spelling a name the same way is corroboration, not a typesetter.
- **`HOLD`** — `Wabanaki Tribes of Maine`<br>Two notices. Federal Register notices are often reissued or copied forward, so n=2 is not two independent observations.
- **`REFUSE`** — `Kaua'i/Nihan`<br>A single notice. An alias is an identity assertion about a nation and one occurrence cannot carry it.

</details>

---

## 16.9 — 6,796 unresolved congressional earmark recipients

**Scope:** 6,796 rows

**Decision.** Same doctrine as 16.2 - name + state exact or nothing. The measurement reframes the file: 5,111 have NO spine match at all and 463 have no name to match, so 82% is a coverage floor. The actionable finding is not an attribution: 174 rows are a PARSER DEFECT, a wrapped table cell read as a recipient name.

| disposition | rows | dollars |
|---|---:|---:|
| `FLOOR` | 5,111 | $17.43B |
| `REFUSE` | 939 | $2.22B |
| `DEFECT` | 637 | $1.37B |
| `HOLD` | 109 | $437.9M |

<details><summary>Worked examples, one per disposition</summary>

- **`DEFECT`** — ``<br>blank_name - The recipient cell is empty in the source. Nothing can be matched and nothing should be inferred.
- **`HOLD`** — `N/A`<br>containment_record_less_specific_than_entity:Native American - reason=containment_record_less_specific_than_entity:Native American Bank, N.A.
- **`FLOOR`** — `Bureau of Reclamation`<br>no_spine_match - No spine entity matched. Published as a stated coverage floor; an earmark to a non-Native recipient is the normal case in this file, not a miss.
- **`REFUSE`** — `Te-Moak Tribe of Western Shoshone`<br>ambiguous_containment:4:Te-Moak Tribe of Western Shoshone In - Resolves to more than one entity; C6 forbids shipping an unresolved identity conflict as a definite fact.

</details>

---

## 16.10 — 6,094 unresolved subaward parties

**Scope:** 6,094 rows

**Decision.** Rule by `resolver_how`. The measurement that settles it: resolver_how is EMPTY on 6,000 of the 6,094 - they never had a candidate at all and are a coverage floor, not a queue. Only 94 rows are a real decision.

| disposition | rows | dollars |
|---|---:|---:|
| `FLOOR` | 6,000 | — |
| `ACCEPT` | 57 | — |
| `REFUSE` | 19 | — |
| `HOLD` | 18 | — |

<details><summary>Worked examples, one per disposition</summary>

- **`ACCEPT`** — `ASRC CONSULTING & ENVIRONMENTAL SERVICES, LLC` → `ANRC-ARCSLO-00`<br>resolver_how=declared_parent_uei - Resolved through a DECLARED PARENT UEI - an identifier the registrant filed about itself. An identifier beats every name method (ENTITY_MATCH_RULES step 4).
- **`HOLD`** — `ALASKA FEDERATION OF NATIVES, INC.` → `ITO-LSKFDR-00`<br>resolver_how=core - Core-name match is moderate and uncorroborated here.
- **`REFUSE`** — `SANTA FE HIGH SCHOOL` → `BIE-SANTAF-00`<br>resolver_how=containment - Containment with no second signal. This is the class that produced 41 wrong links onto Council Native Corporation.
- **`FLOOR`** — `MARINETTE MARINE CORPORATION`<br>resolver_how=(none) - No resolver produced any candidate for this party. It is unresolved because nothing matched, not because a match is waiting on a decision.

</details>

---

## 16.11 — Tribal vendor-list consent - NOT DECIDED HERE

**Scope:** 62 rows - owner

**Decision.** HELD FOR THE OWNER, deliberately. All 62 rows carry publishable = N and consent_status = UNRESOLVED; 8 are TERMS_STATED_RESTRICTIVE and 2 are ROBOTS_DISALLOW. This is not a method question - it is a decision about Cedar's relationship with the nations whose lists these are, and it is the one failure mode that would damage this project's standing rather than its accuracy. Standing recommendation unchanged: publish the verdict and the URL, which are facts about a public page; publish no harvested contents without consent. This file changes none of those 62 rows.

---

## 16.6, worked by identifier — the three findings that came out of it

`code/604_adjudicate_master_queue_by_identifier.py` took item 16.6 at its word and never opened a browser, because the strongest identifier evidence was already on disk: **5,167 parent/child UEI relationships the registrant declared about itself in SAM** (`data/clean/fpds_uei_edges.csv`). All 50 of the MASTER QUEUE's top rows by dollars are now decided — **23 ACCEPT, 18 REFUSE, 6 ALREADY_RULED, 2 HOLD, 1 FLOOR, none left open**. Three findings are worth more than the dispositions:

**1. A contradiction sweep must classify before it acts.** Every tier A/B UEI in the ledger was tested against its declared parent. 129 disagreed, on $2.82B — a number that reads like 129 wrong attributions and is not. **54 rows, $2.39B, are a defect in the PARENT row, not the child:** every Bowhead subsidiary is correctly keyed to `ANVC-KPVKPT-00`, Ukpeaġvik Iñupiat Corporation, while the corporation's own UEI is keyed to `AKNF-INPTAS-00-ARCSLO`, the Native Village — a link `ANCSA_OWNERSHIP_RULING` RULE 2 and `cedar_domain.village_government_owns_an_anc()` (always `False`) say cannot exist. One bad row makes 54 good ones look wrong. **72 rows, $0.40B, are joint ventures** — thin edges (`WHH Nisqually Federal Services` declares TDX Quality exactly once) against hand tier-A rulings, so the ledger stands. **3 are genuine**, and the only non-ANCSA one is `Tikigaq Technology Services`, keyed to **Paiute of Utah** while declaring **Tikigaq Corporation of Point Hope, Alaska** as its parent **258 times**. Acting on the raw 129 would have repointed 126 correct rows to chase 3 wrong ones.

**2. The MASTER QUEUE is partly stale and does not say so.** **223 of its 6,559 rows — $10.8B of the $82.1B — are already ruled**, including six of the top fifty by dollars (`SAN CARLOS APACHE TRIBAL COUNCIL` $847M, `LUMMI INDIAN BUSINESS COUNCIL` $696M, `HOOPA VALLEY TRIBE` $495M), all removed from the live queue on 2026-08-26 and all still sitting here with an empty `YOUR_RULING`. `Kluti Kaah` ($583M) already carries a tier-X NEGATIVE ruling naming the true owner as the Native Village of Eyak — **which is not in the spine**, a gap worth its own pass.

**3. This measurement corrects an earlier figure of my own.** The first pass reported the already-ruled overlap as "exactly 1" and it was wrong, for the reason this project keeps writing down: **the join key was blank.** 2,443 of the 6,559 rows carry an empty `identifier` column, so a join on it matched almost nothing and reported a queue as wholly unseen. The UEI was there the whole time, inside the free-text `question`.

---

## What was learned, and where it is written down

Four rules generalise beyond this backlog and are appended to `docs/ENTITY_MATCH_RULES.md` as numbered rules 7–10, so the next thousand rows are cheap:

7. **An entity's own official name is the arbiter of its own boundary.**
8. **A ruled METHOD is not a positive ruling, and an agent ruling may not mint tier A.**
9. **Containment never accepts alone.**
10. **An alias needs three independent observations.**
11. **A declared parent UEI outranks a name, and 20 observations is the floor between ownership and a joint venture.**
12. **When a declared parent contradicts an attribution, suspect the PARENT row first.**

