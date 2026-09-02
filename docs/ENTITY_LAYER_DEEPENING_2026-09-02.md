# The entity layer, `nest`, `native-owned-businesses` and `nonprofits` — deepening pass, 2026-09-02

*Five scripts, `code/1098`–`code/1102`, each with `verify` (exit 1 on breach)
and `selftest` (the violation injected into a copy, exit 1 asserted, the copy
restored and exit 0 asserted). **28 invariants across the five, 28 proved to
fire.** `293_lint_bug_classes.py`: **zero findings in any of the five across all
seven classes.** Nothing was committed.*

**Every number below was measured on the live files that day and the command
that measures it is named.** Where a standing figure was found wrong it is
struck and the correction is stated, per `docs/DOC_CONTRADICTIONS_2026-08-26.md`.

---

## THE ONE-LINE SUMMARY PER DATASET

| dataset | what changed | the measurement that mattered |
|---|---|---|
| `_entity_layer` | 1,772 blank endpoints promoted from prose into 9 declared columns, 262 bridged to NEST | **the "466 recover nothing" rows recover a CAGE. Recovery is 1,462/1,462, 100%** |
| `_entity_layer` | 13 ledger rows flagged where the legal name is another sovereign's official name | **$3.55M on ONE row, 285 of 285 awards in the wrong state, tier A, published** |
| `nest` | a fourth evidence family, on disk, unused | **87 ownership assertions independently corroborated, up from 60** |
| `nest` | Chugach adjudicated; a duplicate class found | **25 companies are held twice; 8 of the 50 rows are Chugach** |
| `native-owned-businesses` | the crosswalk promoted onto the table | **178 published "business names" are natural persons** |
| `nonprofits` | `keyed_name_match_*`, and 13 redirects | **461 of 1,423 live keys are place-name collisions; the existing flag reaches 160** |

---

## 1. `_entity_layer` — the blank endpoint is not missing data

`code/1098_entity_rel_counterparty.py`

### The standing number is wrong on 466 rows

`AGENTS.md` names `entity_relationships.csv` as the ownership source of truth.
1,772 of its 2,292 rows (77.3%) carry a blank endpoint, and the standing read
was *"996 recover a UEI only from prose; 466 recover nothing."*

~~466 recover nothing.~~ **They recover a CAGE code.** Every one of the 1,462
`owned_by` rows parses on one anchored pattern:

```
firm '<LEGAL NAME>' (UEI <12 chars>)  is owned by ...      996
firm '<LEGAL NAME>' (CAGE <5 chars>)  is owned by ...      466
unparsed                                                     0
```

**1,462 of 1,462 — 100% — carry a firm name AND a published federal
identifier.** Nothing here was unrecoverable; it was unREADABLE, which is a
different defect with a much cheaper fix. The other three families are the same
shape and also parse at 100%:

| relation | rows | blank side | what the prose holds |
|---|---:|---|---|
| `owned_by` | 1,462 | source | firm legal name + UEI or CAGE |
| `affiliated_with` | 148 | target | the TDHE's published name (7 also blank on the source side) |
| `brand_of` | 106 | source | brand family + its `CEDAR-ALIAS-` id |
| `operated_by` | 56 | target | "the United States (Dept of the Interior, BIE)" |

### Why the fix is not "mint the missing entities"

`docs/IDENTIFIER_STANDARD.md` §2 settles it: a UEI or CAGE identifies a
**registration**, and a registration is a **sub-hub, never a spine row**. The
blank `source_entity_id` is therefore correct — the rows say so themselves
(*"No spine entity for the firm and no intermediate holding layer invented"*).
Minting 1,462 spine entities would put 1,462 non-entities into the entity
namespace and invert the hub model.

Nine columns now carry what the sentence carried, with an **anti-fabrication
invariant (I2): every promoted value is a verbatim substring of that row's own
`notes`.** A value that does not survive that test is not written.

### The NEST bridge, and the register question — see ADR-020

`data/spine/cedar_nest_id_register.csv` is **the enterprise level of the
existing sub-hub layer**, exactly as `facility_id` is the facility level. Not a
parallel entity space; a `CEDAR-NEST-` id may never stand where a `cedar_uid`
is expected. Full decision, with the table of registers, in **ADR-020**.

262 of 1,462 `owned_by` firms (17.9%) resolve to a NEST enterprise, and only
when **both sides agree about the owner**:

```
rung 1  published UEI equals a NEST published UEI          29
rung 2  published CAGE equals a NEST published CAGE         0
rung 3  normalised name unique among the enterprises of
        this same owner hub                               233
refused, owner disagreement                                 1
unresolved                                              1,200
(23 more would resolve through NEST's own uei_candidate
 and are REFUSED - a candidate on one side plus a
 candidate on the other is not evidence)
```

**Every unresolved row now says why**, in `counterparty_nest_basis`. A counter
that does not name what it dropped is `293` class 2c.

### The first cross-source ownership disagreement the entity layer has produced

```
Laulima Government Solutions, LLC        UEI QTJZT9K41S61
  entity_relationships  ->  Bering Straits Native Corporation   ANRC-BERSTR-00
                            tier A, "Ruled by Elijah 2026-08-06: re-attributed
                            ... the earlier claim was wrong"
  nest / shard-H        ->  Alaka'ina Foundation                NHO-ALAKAI-00
                            parent_declared_subsidiary_list,
                            source http://beringalakaina.com/
```

**The source host names both parents.** `ENTITY_MATCH_RULES` rule 11: a joint
venture genuinely has two. **Refused, not reconciled**; no link written, neither
side altered. `review/entity_rel_nest_owner_conflicts_2026-09-02.csv`, and
owner queue item **EL-2**.

---

## 2. `_entity_layer` — the Ho-Chunk collision inverted, and it is a class

`code/1099_crosstribe_legalname_audit.py`

### The case

`cedar_identifier_ledger_final.csv`, tier A, `is_authority = YES`, and **in
`cedar_publishable_identifiers.csv`**:

```
CAGE 3VFL3  tribe_id TRBF-WNNBGO-00  Winnebago Tribe of Nebraska
            legal_business_name      "Ho-Chunk Nation"
            state                    WI
```

`TRBF-HOCHNK-00` is the Ho-Chunk Nation of Wisconsin, `state = WI`. The source
row (`entity_crosswalk_bgov.csv`, XW-0729) settles it with no network request:
`Performing_Vendor = Ho-Chunk Nation`, `Vendor_States = **Wisconsin**` — the
only Wisconsin row among Winnebago's 27, every other one Nebraska — and
`Subsidiary_Flag = 1`.

**And the structural argument, which is the one worth keeping: a federally
recognized tribe cannot be a subsidiary of another federally recognized tribe.**
Same shape as `cedar_domain.village_government_owns_an_anc()`, always `False`.

`cedar_resolved_facts.csv` already held the contradiction machine-readably and
nothing had read it: `CE-001C8-GH` (Winnebago) carries
`entity.registration_state = WI` and `entity.legal_business_name = Ho-Chunk
Nation` on `CAGE:3VFL3`.

### The predicate, and the guard that makes it work

The naive normaliser strips `Inc` — which folds `Ho-Chunk, Inc.` into `Ho-Chunk`
and so finds the **correct** rows and misses this one. `Inc` is the whole
discriminator: a sovereign government's official name never carries a legal
form. So the detector requires **no legal-form token in the name** (I2, proved
to fire), plus a non-empty residue against the keyed entity, plus exactly one
other government whose official names account for the whole name.

Without the incumbent check the detector reported 35 and most were noise —
`Red Lake Band of Chippewa Indians` is a strict subset of *Red Cliff Band of
Lake Superior Chippewa*, so a subset test with no incumbent check reports every
nation whose name sits inside a longer one.

### 13 collisions, $5.72M of prime obligations on 415 rows

```
government-keyed ledger rows scanned            5,836
skipped, a legal form in the name (I2 guard)    2,771
skipped, the KEYED entity explains the name       857
skipped, the name reaches >1 government             0
-----------------------------------------------------
cross-government name collisions                   13   9 tier A, 4 tier B
  of which in cedar_publishable_identifiers.csv     8
```

**The loudest is not the Ho-Chunk row:**

> `UEI HLTFBD3FTDG8`, tier A, `attribution_method = hand`, keyed to **Fort
> Sill-Chiricahua-Warm Springs-Apache Tribe (Oklahoma)**, legal business name
> **"Confederated Tribes Of Warm Springs Reservation Of Oregon"**.
> **285 `prime_contracts` rows, $3,552,567, `recipient_state_code = OR` on
> 285 of 285.** The collision token is *Warm Springs*. Rung 1 of the owner's own
> ladder — the address — answers it 285 times over, and nothing had asked.

Also: `CAGE 4XH62`, tier A, published — legal name *"Chignik Lagoon, Native
Village Of"*, `state = AK`, keyed to the **Yavapai-Apache Nation, Arizona**.

### A rename with no alias is indistinguishable from a collision until you look at the address

`UEI H1ZEEZK2D6B3`, *"San Juan Pueblo Tribal Council"*, keyed to **Ohkay
Owingeh (NM) — and that is CORRECT.** Ohkay Owingeh *is* the renamed San Juan
Pueblo; 113 of 113 awards are in New Mexico; the apparent rival
`TRBF-SNJUAN-00` is the San Juan **Southern Paiute** Tribe of **Arizona**.
The spine simply does not carry `San Juan Pueblo` in Ohkay Owingeh's `aliases`.

Disposition `TRANSACTION_STATE_AGREES_WITH_KEYED_ENTITY`, **no repoint
proposed** — which is why rung 1 is run on the transaction record as well as on
the registration.

**Nothing was repointed.** The ledger gained a `crossgov_name_collision_*` flag
family; no `tribe_id`, tier or method moved, asserted by an md5 over all 22 base
fields. `ENTITY_MATCH_RULES` rule 8 (an agent ruling may not mint tier A) and
the Bristol Bay precedent (a repoint that keys a dollar awaits the owner).
Owner queue item **EL-1**; register
`review/ledger_crossgov_name_collisions_2026-09-02.csv`.

---

## 3. `nest` — a fourth evidence family that was already on this machine

`code/1102_nest_corroboration_adjudication.py`

`docs/ASSERTION_LAYER.md`: every fact in Cedar rests on exactly one source.
NEST had 60 enterprises on two independent families (an audited AS 45.55.139
filing and the parent's own website) and its next-pass list named the Alaska
Division of Corporations — a network fetch — as the cheapest third.

**`data/clean/fpds_uei_edges.csv` is a fourth family and it is local.** It
records the parent a registrant declared **about itself**, to the federal
government: identifier-grade (rule 11), made by the CHILD, and therefore
independent of both families NEST already has. Rule 11's measured
**20-observation ownership floor** applies; below it an edge is a joint venture.

The test is not "the names match" but **"the declared parent resolves, through
the identifier ledger, to the owner hub NEST already asserts"** — two
independent parties agreeing about the OWNER.

```
reached an FPDS edge at or above the 20-observation floor      272
  rung 1, published UEI                                         28
  rung 2, exact normalised name                                244
CORROBORATED - the declared parent lands on NEST's own owner     87
CONTRADICTED - it lands on a different Cedar entity                8
PARENT_UNRESOLVED - the parent UEI is in no ledger row           177
PARENT_BELOW_JV_FLOOR - an edge exists but under 20 obs           71
NO_DECLARED_PARENT                                             1,267
```

**87 > 60, and it is a different 87.**

### The 8 contradictions are mostly the ledger's fault — rule 12, from a fifth direction

| enterprise | NEST says | the ledger resolves the declared parent to |
|---|---|---|
| Bowhead Manufacturing / Professional Solutions / Transportation, Rockford Corporation, UMIAQ Environmental | Ukpeaġvik Iñupiat **Corporation** | `AKNF-INPTAS-00-ARCSLO`, the **village government** |
| Goldbelt Eagle, LLC | Goldbelt, Incorporated | `AKNF-VEAGLE-00-…`, the Native Village of **Eagle** |
| Vista Defense Technologies, LLC | Bristol Bay Native Corporation | `TRBF-BNVSTA-00`, Buena **Vista** Rancheria |

`ANCSA_OWNERSHIP_RULING` rule 2 says the first five cannot be what the ledger
says; the other two are collisions on `Eagle` and `Vista`. **NEST is the correct
side on 6 of 8.** This is the `ALASKA_VILLAGE_GOVERNMENT_VS_VILLAGE_CORPORATION`
family (334 defects, $24.52B) reached from a fifth direction. Two stay open:
`Nisga'a Tek LLC` (NEST Tlingit & Haida vs Goldbelt, 254 obs) and
`Broadleaf, Inc` (NEST The Hawai'i Pacific Foundation vs ASRC, 325 obs).
Neither side was repointed —
`review/nest_fpds_parent_contradictions_2026-09-02.csv`.

### Chugach, adjudicated: the audited filing UPHELD, now on two of three sources

The two surviving conflicts are `Chugach Government Solutions, LLC` and
`Chugach Regional Development, LLC`. Reading the relations rows adds two facts
the conflict register did not state:

1. The web source is **one page**, `www.chugach.com/business/directory`, and on
   that same page it calls **Chugach Commercial Holdings a *holding company***
   while calling CGS and CRD operating companies. The site is asserting a
   different role, not omitting one — **the conflict is genuine.**
2. A **third source**, `anc_tribal_subsidiary_lookup.csv`, lists all four —
   CCH, CGS, CIH, CRD — **identically as `subsidiary` directly under the
   corporation**. Four parallel siblings at one tier, two of them named
   *Holdings*.

**`relationship` does not fuse two axes, it fuses three.** NEST already found
SHARE (`wholly_owned`) vs ROLE (`holding_company`). This pair adds the third: a
**consolidation note answers where an entity SITS**; a **business directory
answers what a firm SELLS**; both render into the same six words. The audited
filing answers the question the column is asking. `holding_company` stands, and
the adjudication is written onto `data/staging/nest/evidence_conflicts.csv`
itself.

### NEST holds 25 companies twice, and it costs a corroboration each

Found while reading the Chugach rows. NEST clusters on (owner hub, normalised
name) and **a trailing parenthetical survives normalisation**:

```
CEDAR-NEST-000473-WH  Chugach Government Solutions, LLC    2 observations
CEDAR-NEST-000474-2A  Chugach Government Solutions (CGS)   1 observation
```

**25 groups, 50 rows.** 24 are an acronym — `Ahtna Global LLC (AGL)`,
`Yulista Aviation (YAI)`, `Eyak Technology LLC (EyakTek)`,
`Bristol Bay Construction Holdings LLC (BBCH)` — and in every one of the 24 the
acronym twin is the `ANC_TRIBE_LOOKUP` row at `n_distinct_sources = 1` while the
plain row already carries 2 or 3. The 25th is a **gloss**, not an acronym:
`Aan Hít` / `Aan Hít (Village House)`.

The cost is double: **25 rows of overstatement in a 1,610-row headline, and 25
lost corroborations**, because a restatement that fails to cluster raises
nobody's source count — which is exactly what NEST's merge exists to do.

**FLAGGED, NOT MERGED.** Merging retires 25 `CEDAR-NEST-` ids out of an
append-only register; `docs/IDENTIFIER_STANDARD.md` forbids retiring an id as a
side effect and `docs/AGENT_FIELD_GUIDE.md` §4 says measure duplicates before
collapsing them. Register: `review/nest_name_variant_duplicates_2026-09-02.csv`.

### The headline is unaffected and here is why that is worth saying

**977 of 1,610 absent from federal contracting (60.7%)** does not move: the 25
duplicate rows are ANC subsidiaries that are *present* in contracting, so
collapsing them would raise the percentage, not lower it. The floor stays a
floor.

---

## 4. `native-owned-businesses` — the crosswalk promoted, and a refusal applied to the other half of a split

`code/1100_nob_crosswalk_promotion.py`

### Part one: the crosswalk

`native_business_contract_links.csv` held the resolved federal identity of a
directory row; `native_owned_businesses.csv` could not see it
(`business_entity_id` reaches 4 of 2,916). Promoted into twelve declared
`federal_link_*` columns:

```
federal_link_status   NO_MATCH 2,115 · NOT_ATTEMPTED 523 · LINKED 203
                      PROPOSED 59 · HOLD_AMBIGUOUS 8 · REFUSED 8
UEI written  203      CAGE written 156     (LINKED + gate=PUBLISH only)
distinct UEIs 168     ~~169~~ - measured 168 on the live file
```

Three rules held, each with an invariant:

- **A UEI is not a `business_entity_id`.** §2 of the identifier standard: a UEI
  identifies a registration, a registration is a sub-hub. Writing one into an
  entity column would make 203 registrations look like 203 entities.
- **The gate is a policy, not a re-derivation.** A UEI is written only where the
  crosswalk's own `identifier_publish_gate` is `PUBLISH` (I2).
- **The certification gradient is untouched** and the published relation stays
  **affiliation** — `federal_link_relation` says so on every row.
  **No dollar was written onto a directory row**; `federal_link_detail_file`
  points at the sidecar, because a dollar on an affiliation row invites a
  roll-up across the gradient.

The two writers agree and it is now checked, not assumed: on the 140 rows where
both `federal_uei_candidate` (from `code/953`) and `federal_uei_linked` are
populated, **140 of 140 are the same string**, and I3 fails if that stops being
true.

The 523 rows with no crosswalk row get **`NOT_ATTEMPTED`**, named as such —
`code/1001` ran before they were merged. That is an honest state (ADR-010), not
a no-match.

### Part two: 178 published "business names" are natural persons

`code/1070`'s sweep staged 1,106 rows. The 583 OWNERSHIP rows went to NEST,
which **refused 229 of them** as *"unreviewed HTML heading/anchor scrape"* —
the block yields page furniture and **natural persons' names**, which
`docs/NEST_BUILD_LOG.md` makes a hard rule. The 523 RELATIONSHIP rows were
merged into this table and **the same refusal was never applied to them.**

Measured on the live table before this pass:

```
carrying "HTML heading/anchor scrape - not a table; review before resolving"  523
of those, business_name_is_person_name = -1 (UNDECIDABLE)                     523
   -> 1070 HARD-CODES it. The detector in code/330 was never run on them.
of those, publishable = Y                                                     523
```

Three of the first three inspected: `"Tribal Enterprise Directory"` (the page's
own heading), `"Rebecca Naragon"` (a person), `"Akwesasne Farmers Market"` (a
real enterprise).

`looks_like_person()` was imported from `code/330` and run on exactly those 523
— never on a row `330` itself decided:

```
IS a natural person's name   178
is not                        87
undecidable                  258
publishable  Y -> N          523
```

`publish_hold = Y` with a basis naming NEST's identical refusal; the prior value
preserved verbatim in `publishable_before_1100`, so the hold reverses with one
column copy. **Written once** — a second run would otherwise capture the value
this script just changed and lose the original `Y`; the preserved-value column
is the one thing that must not be recomputed.

Owner queue item **EL-3**.

### The largest remaining gap is unchanged and is not a Cedar deficiency

NHO coverage on member websites remains `SOURCE_DOES_NOT_PUBLISH` — 210 probed,
4 lists, all navigation furniture. The record is in the **SBA 8(a) register**
and the **NHOA directory**, and that acquisition is `NOT_ACQUIRED`, not
`ON_DISK_NOT_PROMOTED`. Nothing in this pass touched it. The 221 candidates in
`candidates_for_review_2026-09-02.csv` are also untouched.

---

## 5. `nonprofits` — the flag was pointing at the wrong tribe

`code/1101_np_keyed_name_support.py`

### A check that does not measure its own name. The fourteenth.

`code/952` documents `name_match_support` as *"the match shares NO token with
the canonical name shown"*, and computes it as
`support(org_name, canonical_name_token_match)`. **`canonical_name_token_match`
is the candidate the token-match funnel proposed. It is not the tribe the row is
keyed to.**

```
EIN 873791650  CAHUILLA ELEMENTARY PARENT TEACHER ORGANIZATION
  tribe_id                    TRBF-CHLLAB-00   Cahuilla
  canonical_name_token_match  Agua Caliente       <- scored against THIS
  name_match_support          no_shared_token_with_canonical_name
```

Over the 1,423 rows carrying a live `tribe_id`: `canonical_name_token_match` is
**blank on 585** (so the column says `not_a_name_match` about a row that has a
key) and **names a different tribe on 288**. Recomputed against the tribe
actually cited, **1,421 of 1,423 share a token; 2 do not.**

So ~~"2,268 rows share no token at all with the canonical name they cite (541
live)"~~ is right about the funnel and wrong about the live attributions: of the
2,268, **1,594 are already `excluded_by_prior_ruling` and only 71 carry a live
key**, and on 71 of those 71 the name DOES share a token with the tribe it is
keyed to. The "541 live" is the `funnel_stage = canonical_name_match` slice,
where the column is measuring the right thing — those rows are candidates, not
keys.

**952's column is not overwritten.** It is correct within its own slice and is
the evidence of what the funnel proposed. A mis-aimed check is repaired by
naming its aim: the new `name_match_support_measured_against` records, on the
row, which name the older column was scored on.

### The 71 are not vindicated — they fail a different test

All 71 share a distinctive token with the keyed tribe and the token is a **place
name**: `OLD PROS OF LAGUNA WOODS VILLAGE` → Pueblo of Laguna,
`FIRST NATIONAL BANK IN WICHITA CHARITABLE TRUST` → Wichita,
`WESTERN DAKOTA ESTATE PLANNING COUNCIL INC` → Council Native Corporation.
**The recorded flag found the wrong rows for the wrong reason, and the rows it
should have found were labelled `distinctive_token`, which reads as supported.**

### 461 of 1,423 live keys are the Umatilla defect

```
SUPPORTED                     888   62.4%
HELD_STATE_DISAGREES          461   32.4%
REFUSED_GENERIC_TOKEN_ONLY     61    4.3%
REDIRECT_PROPOSED              13    0.9%
```

`HELD_STATE_DISAGREES` — the nation's name is contained in the organisation's,
the states disagree, and 2+ distinctive words are unaccounted for:

```
ISLAMIC ASSOCIATION OF MID KANSAS AT WICHITA KANSAS  KS -> Wichita (OK)
WINNEBAGO PORK PRODUCERS                             IL -> Winnebago (NE)
IRON CROW THEATRE COMPANY INC                        MD -> Crow (MT)
LAGUNA BEACH FIREFIGHTERS ASSOCIATION                CA -> Pueblo of Laguna
SANTAS CLOSET OF WINNEBAGO COUNTY INC                WI -> Winnebago (NE)
WHITE POINT CEMETERY OF COMANCHE COUNTY CORPORATION  TX -> Comanche (OK)
```

Concentrated on six nations whose names are also American place names: Crow 63,
Pueblo of Laguna 61, Fond du Lac 58, Seneca 53, Winnebago 26, Wichita 22.
**50 of the 461 carry `disposition = NATIVE_VERIFIED_STRICT`.**

The existing `placename_risk_flag` reaches **160 of the 461**, so **301 are
newly flagged** — and it also fires on 202 rows this pass calls SUPPORTED, so
the two measure different things and neither supersedes the other.

### The remedy for EASTERN is a redirect, and it found 13

A blanket token exclusion would have buried the thing worth finding.
`REDIRECT_PROPOSED` requires: the keyed entity leaves a residue; exactly one
OTHER spine entity in the organisation's own state accounts for the filed name
**bidirectionally**; truncation is tolerated in both directions, which is
`ENTITY_MATCH_RULES` rule 7's own `RESERVATI` allowance.

```
EASTERN CHEROKEE SOUTHERN IROQUOIS AND UNITED TRIBES OF SOUTH CAROLIN  (SC)
    United South and Eastern Tribes (TN)   ->   TRBS-ECSIUT-00 (SC)
    - the filing's own truncation `CAROLIN` is what needed the tolerance
AMERICAN INDIAN COUNCIL ON ALCOHOLISM INC
    Council Native Corporation (Alaska!)   ->   its own spine entity
MAKAHA HAWAIIAN CIVIC CLUB · NATIVE HAWAIIAN EDUCATION ASSOCIATION ·
NATIVE HAWAIIAN HOSPITALITY ASSOCIATION · NATIVE HAWAIIAN LEGAL CORPORATION ·
NATIVE HAWAIIAN PHILANTHROPY
    all five keyed to `Hawaiian Native Corporation`  ->  their own entities
YUROK ALLIANCE FOR NORTHERN CALIFORNIA HOUSING · SENECA NATION OF INDIANS
ECONOMIC DEVELOPMENT COMPANY · CHEHALIS TRIBAL LOAN FUND · INDIAN HEALTH
CENTER OF SANTA CLARA VALLEY · LEECH LAKE FINANCIAL SERVICES ·
WHITE EARTH INVESTMENT INITIATIVE
    each keyed to its NATION  ->  its own spine entity
```

That last group is rule 7 exactly: *a tribal college, a loan fund and a clinic
are real entities and they are not the nation.*

The other two EASTERN rows the mandate names are **HELD, with the spine gap
stated**, because no alternative exists in their state:
`WIQUAPAUG EASTERN PEQUOT INDIAN TRIBE` (RI, keyed to Eastern Pequot Tribal
Nation of **CT**, residue `WIQUAPAUG`) and `EASTERN BAND OF CHICKASAW INDIANS
FOUNDATION INC` (TN, keyed to The Chickasaw Nation of **OK**, residue
`EASTERN|FOUNDATION`). Both keep their Native status: **a refusal says only
"this is not THAT entity."**

### The version that would have shipped

The first redirect rule proposed **37** and six were wrong the same way —
one-way containment onto a longer name: `LUMBEE NATIONS INC` → Lumbee Guaranty
Bank, `JEMEZ SPRINGS COMMUNITY FOUNDATION` → Jemez Day School,
`THE CHEHALIS FOUNDATION` → Chehalis Tribal Loan Fund,
`ALASKA NATIVE TRIBAL HEALTH CONSORTIUM` → Southeast Alaska Regional Health
Consortium, and two more. **Requiring the match to hold in both directions
killed all six and cost none of the 13.** Containment is not identity, in
whichever direction you run it.

Nothing was blanked, following `code/610`: `tribe_id`, `cedar_uid` and
`disposition` are untouched, asserted by an md5 over all 57 base fields.
Register: `review/np_live_key_review_2026-09-02.csv`.

---

## WHAT REMAINS IN THE ENTITY LAYER, WITH ITS MEASURED SIZE

| hole | size, measured 2026-09-02 | why it is still open |
|---|---:|---|
| `owned_by` firms with no NEST sub-hub | **1,200 of 1,462 (82.1%)** | each carries a published UEI or CAGE and is a registration sub-hub Cedar has not otherwise recorded. Closing it means harvesting more subsidiary lists, not minting ids |
| constellation from-sides with no `cedar_uid` | **2,408 of 3,153 (76.4%)** | **not a hole.** All 2,365 TERO ones join to `native_owned_businesses` on `from_record_key`; 186 now carry a federal UEI; **278 are natural persons' names and must never be minted.** ADR-020 |
| ledger cross-government collisions | **13 rows, $5.72M, 8 published** | awaiting owner ruling EL-1. Flagged, nothing repointed |
| the Laulima two-owner disagreement | **1 row** | awaiting owner ruling EL-2 |
| `Ohkay Owingeh` missing the alias `San Juan Pueblo` | **1 spine row** | a one-line spine edit, deliberately not made by this pass |
| NEST enterprises on one source | **1,172 of 1,610 (72.8%)** | 87 now have an independent second family; the next cheapest is the Alaska Division of Corporations and it needs the network |
| NEST duplicate name variants | **25 groups, 50 rows** | flagged; merging retires ids and is an owner decision |
| NEST open parent contradictions | **2 rows** | Nisga'a Tek, Broadleaf |
| `native_owned_businesses.business_entity_id` | **still 4 of 2,916** | correctly so — a UEI is not an entity id. What was missing was the federal-link family, now present on all 2,916 |
| NHO directory coverage | **`SOURCE_DOES_NOT_PUBLISH`, 210 probed, 4 lists** | the record is the SBA 8(a) register and the NHOA directory. `NOT_ACQUIRED` |
| nonprofits held on a state disagreement | **461 of 1,423 live keys (32.4%)** | flagged, not withdrawn; 50 of them read `NATIVE_VERIFIED_STRICT` |
| nonprofits refused on a generic token | **61 of 1,423** | flagged, key left live per `code/610`'s convention |
| nonprofit spine gaps named by this pass | **2** | Wiquapaug Eastern Pequot (RI), Eastern Band of Chickasaw Indians (TN) |

---

## FILES

```
code/1098_entity_rel_counterparty.py        build | dry | verify | selftest
code/1099_crosstribe_legalname_audit.py     build | dry | verify | selftest
code/1100_nob_crosswalk_promotion.py        build | dry | verify | selftest
code/1101_np_keyed_name_support.py          build | dry | verify | selftest
code/1102_nest_corroboration_adjudication.py build | dry | verify | selftest

data/clean/entity_relationships.csv          +9 columns   2,292 rows unchanged
data/clean/cedar_identifier_ledger_final.csv +4 columns  20,577 rows unchanged
data/clean/native_owned_businesses.csv      +16 columns   2,916 rows unchanged
data/clean/np_orgs.csv                       +9 columns  12,764 rows unchanged
data/clean/nest_enterprises.csv              +9 columns   1,610 rows unchanged
data/staging/nest/evidence_conflicts.csv     +5 columns       2 rows unchanged

review/entity_rel_nest_owner_conflicts_2026-09-02.csv        1
review/ledger_crossgov_name_collisions_2026-09-02.csv       13
review/nest_fpds_parent_contradictions_2026-09-02.csv        8
review/nest_name_variant_duplicates_2026-09-02.csv          50
review/np_live_key_review_2026-09-02.csv                   535
review/OWNER_DECISION_QUEUE.md                  APPENDED EL-1, EL-2, EL-3

docs/ARCHITECTURE_DECISIONS.md   APPENDED inside <!-- BEGIN ADR-020-SUBHUB-REGISTERS -->
docs/ENTITY_REL_COUNTERPARTY.json · docs/CROSSTRIBE_LEGALNAME_AUDIT.json ·
docs/NOB_CROSSWALK_PROMOTION.json · docs/NP_KEYED_NAME_SUPPORT.json ·
docs/NEST_CORROBORATION.json
```

**Every table was written with a `.bak_2026-09-02_pre_<stem>` backup** — the
stem, never the bare number (the 163 incident). **All five are IN-PLACE
ENRICHERS: a rebuild of any of those five tables reverts their columns and the
enricher must be re-run**, which is the collision `docs/DEPENDENCY_MANIFEST.md`
exists to record.

**Nothing was committed.**
