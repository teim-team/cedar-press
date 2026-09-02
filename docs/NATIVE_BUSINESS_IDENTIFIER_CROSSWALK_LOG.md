# Native-owned business ↔ federal contracting: the identifier crosswalk

*Built 2026-09-02. Scripts `code/1000_harvest_business_identifiers.py` and
`code/1001_link_businesses_to_contracting.py`. Band 1000–1009.*

**The mandate:** harvest CAGE / UEI / DUNS from Native business websites and use
them to join `data/clean/native_owned_businesses.csv` (2,393 firms, 18
certifying authorities) to the federal contracting tables.
`business_entity_id` was populated on **4 of 2,393 rows** and the two datasets
could not be joined to each other.

---

## THE HEADLINE, AND THE THING THAT SURPRISED US

**203 of 2,393 directory rows are now linked to a federal contracting record**
at tier A or B — **169 distinct UEIs**. What that join exposes:

| measure | all linked | rows the directory marks publishable |
|---|---:|---:|
| prime obligations | **$13.43B** | $12.69B |
| …of which **already attributed** to a Cedar entity | $11.67B | — |
| …of which **previously unattributed** | **$1.76B** | — |
| SAM FY2000–07 backfill, net-new only | $71.3M | $57.3M |
| subaward value | **$2.16B** | $2.15B |
| distinct UEIs | 169 | 127 |
| directory rows | 203 | 152 |

**Read the $13.43B honestly.** $11.67B of it was already attributed to a Cedar
entity — mostly Arctic Slope, through `prime_contracts.tribe_id`. That money is
not newly discovered; it is newly visible *through the firm and the nation that
certified it*, which is a different and still valuable thing. The genuinely new
attribution surface is the **$1.76B that had no Cedar entity at all** and now
has a named certified firm and a certifying authority. A build that reported
$13.43B without that split would be technically true and misleading.

A further **45 tier-C** and **14 tier-X proposals** and **8 ambiguous holds**
are staged for a ruling rather than published.

**But almost none of it came from the route the mandate expected**, and that is
the finding worth carrying forward:

> **The tribal certification directories publish no federal identifiers at all.**

Measured, not assumed. `1000 sweep` reads all **249** objects Cedar already
holds for these 18 sources — every raw HTML snapshot, every PDF, every OCR
sidecar, every staging JSONL — and looks for a labelled CAGE, UEI or DUNS in
rendered text **and** in JSON-LD, `<meta>` tags, `data-*` attributes and HTML
comments (`docs/HIDDEN_DATA_TECHNIQUES.md` techniques 1, 6, 7, 12). Result:
**zero**. The identifiers were never present. They were not captured and
dropped.

So the join could not be identifier-first *from the directory side*. It is
identifier-first from the **federal** side instead: `1001` assembles every
(name → UEI/CAGE) observation Cedar holds across `prime_contracts.csv`,
`subawards.csv`, `fpds_uei_cage_map.csv` and `sam_prime_contracts_fy2000_2007.csv`
— **31,301 UEIs, 34,740 distinct normalized names** — and matches the directory
into it by exact name, then climbs the owner's corroboration ladder.

---

## What the ladder is, rung by rung

The owner's order — *address → website → search the address for other owned
entities → CAGE as a pointer to the next name → news article → stop* — becomes,
for this join:

| rung | evidence | tier | rows |
|---|---|---|---:|
| **−1** | the firm **published its own UEI or CAGE**, and it resolves in Cedar's contracting tables | A | 3 |
| **0a** | the directory **printed a federal contract number** resolving to exactly one UEI | A | 15 |
| **0b** | a printed contract number **intersects** the name match at exactly one UEI | A | 2 |
| 1 | exact name + **city and state** both agree | A | 89 |
| 1b | exact name + **city** agrees, state silent | B | 0 |
| 2 | exact name + **state** agrees | A | 22 |
| 2b | exact name + state agrees, recorded state was **truncated** | B | 0 |
| 3 | exact name + the **certifying nation's own service area** | B | 72 |
| 4 | exact name, **unique** in the federal universe, no geography | C | 45 |
| 5 | stop | X | 22 (14 proposed, 8 held) |

Rungs 1b and 2b fired zero times on this run and are kept anyway: every Navajo
row whose state was truncated also carried a city that matched, so the stronger
rung took it. A rung with no rows is evidence the ladder is ordered correctly,
not dead code.

Refusals and holds, both written down rather than dropped:

| outcome | rows | meaning |
|---|---:|---|
| `NO_MATCH` no federal recipient of this name | 2,005 | the honest majority |
| `NO_MATCH` name cannot found a match (rule 1) | 110 | 103 single-token, 7 all-generic |
| `REFUSED` state conflict | 8 | the veto fired |
| `HOLD_AMBIGUOUS` | 8 | one name, several federal entities |

`review/native_business_identifier_proposals_2026-09-02.csv` carries **75
proposals** in the owner's inbox format (8 holds, 8 conflicts, 59 tier-C/X),
each with the candidate UEIs, the dollars at stake, `code/953`'s independent
proposal where it has one, and the `cage.dla.mil` verification protocol.

---

## THE ROUTE THAT ACTUALLY WORKED — a contract number is an identifier

The single largest addition to this build came from a column nobody had used:
**`federal_contract_number`, populated on 20 directory rows**, all from ASRC
Federal's own contract-vehicles page. Split it into PIID tokens, look each up
in `prime_contracts.csv`, and accept only tokens resolving to **exactly one
UEI**:

| firm as the directory names it | UEI | prime obligations |
|---|---|---:|
| Analytical Services Inc. | K5Y3MDHD2MB5 | $4.18B |
| ASRC Federal System Solutions, LLC | FD7JDCJ4AMF9 | $1.42B |
| **InuTeq** | NBEWZB8LQ8Z5 | $1.28B |
| ASRC Research and Technology Solutions | VF2ANJQHJ1N7 | $1.15B |
| Agile Decision Sciences, LLC | C6EMRJ67V4M3 | $948.3M |
| **Vistronix** | XPRKVQ956WB4 | $701.6M |
| ASRC Federal Data Solutions | K5L5KR3MZ538 | $684.5M |
| **Broadleaf, Inc.** | DGA4AQ4DJYY9 | $671.5M |
| NetCentric Technology | T65LCYKJCW58 | $661.3M |
| …7 more | | |

**BROADLEAF, INUTEQ and VISTRONIX are the three names the mandate itself
singles out** as impossible for a name matcher, because they share no token
with "Arctic Slope." All three were `NO_MATCH` before this rung and are tier A
after it. A published contract number is an identifier; treating it as one is
what "identifier-first matching" means when the directory prints no UEI.

**Uniqueness is not optional.** `HC104719D2034` is a multi-award IDV carrying
two awardees and `W15P7T-17-D-0104` resolves to none; taking the largest would
have been a guess dressed as evidence. Rung 0a also requires ≥2 transaction
rows, because a single stray row under a shared IDV looks unique and is not.

## Five things this build learned that outlive it

### 1. `I` and `O` are never used in a CAGE code or a UEI — and that is a *matcher*, not a footnote

The local sweep's one and only "hit" was **CAGE = `JONES`**, extracted from
`Cage Jones, MT Assistant Supervisor` in the Eastern Band vendor list. A
person's name, read as a federal identifier — simultaneously a fabricated
identifier and exactly the natural-person data this project must never publish.

DLA and GSA both exclude `I` and `O` from CAGE codes and UEIs so they cannot be
confused with `1` and `0`, and a UEI never begins with `0`. **Verified against
Cedar's own data before being relied on**: 8,886 well-formed CAGE codes and
34,601 UEIs in `fpds_uei_cage_map.csv`, **none** containing `I` or `O`, **none**
starting `0`. The rule is now in the validators of both scripts. No denylist
would have caught `JONES`; one structural predicate does — which is the same
lesson `ENTITY_MATCH_RULES` teaches about generic names.

### 2. An empty field is not a disagreement

The first run refused 16 matches for "state conflict". **Eight of them had no
federal state at all** — the candidate was known only from
`fpds_uei_cage_map.csv`, which carries no geography. An absent value read as a
contradiction silently destroyed eight real links, and every one of them looked
like the veto working correctly. The veto now fires only against a **recorded
and different** state; a geography-silent candidate falls to a lower rung.

### 3. Successor entities are one firm, not an ambiguity

`Elite Laundry & Dry Cleaners` holds two UEIs, both in Gallup NM, $11.2M and
$19.0M. Held as "ambiguous" that is $30.2M of a firm Cedar can see perfectly
well, thrown away. `cedar_ids.mapping_is_defect` already says many identifiers
per entity is *expected* — "the 8(a) nine-year term mints successor entities
sharing a name and an address." So candidates that share **both a city and a
state** are merged into one link carrying every UEI; candidates that do not —
`Arctic Slope Technical Services` across NM, CO, AK, AL and MD — stay held.

### 4. A truncated state must widen, never be guessed

`TBD-041` (Navajo) clips its state column in the source PDF: `Ariz`, `Uta`,
`Alas`, and **`Ne` on 14 rows whose cities are Gallup, Shiprock, Crownpoint and
Albuquerque** — New Mexico. Read `Ne` as the Nebraska abbreviation and all 14
produce a false state conflict. Read it as New Mexico and you have guessed. So
neither: `plausible_states()` returns `{NE, NV, NH, NJ, NM, NY}` and
corroboration on any member counts, **at tier B**, with the ambiguity recorded
on the row. Six candidate states is still a strong veto (it refuses Oklahoma)
and a weak award. Which sources clip is **measured** from the data
(`source_state_column_is_truncated`), not listed.

### 5. Dollars are summed per UEI, never per directory row

Tiger Natural Gas is certified by **both** Cherokee Nation and Muscogee (Creek)
Nation; `iina' ba', Inc` appears three times in the Navajo list under three
spellings. Summing rows reported $908M twice and $19.7M three times — a
double-count invisible in a total and obvious in a per-UEI ledger. The headline
figure fell from $7.46B to **$6.32B** when this was fixed, and the corrected one
is the real number.

---

## Per certifying authority

`data/clean/native_business_contracting_by_nation.csv`, generated.

| nation | firms | linked | UEIs | prime obligations | SAM 00–07 net-new | subawards |
|---|---:|---:|---:|---:|---:|---:|
| Arctic Slope Regional Corporation | 20 | 17 | 17 | $10.44B | $49.5M | $1.72B |
| Muscogee (Creek) Nation | 337 | 37 | 37 | $1.24B | $368.2K | $52.2M |
| Cherokee Nation | 836 | 66 | 66 | $1.08B | $266.2K | $385.9M |
| Navajo Nation *(not publishable)* | 346 | 51 | 44 | $760.3M | $13.9M | $7.2M |
| Tohono O'odham Nation | 17 | 3 | 3 | $166.4M | $7.4M | – |
| Poarch Band of Creek Indians | 13 | 4 | 3 | $146.5M | – | – |
| Confederated Salish & Kootenai Tribes | 116 | 13 | 12 | $30.1M | $5.1K | – |
| Three Affiliated Tribes (MHA Nation) | 133 | 1 | 1 | $10.2M | – | – |
| Confederated Tribes of Grand Ronde | 81 | 4 | 4 | $1.6M | – | $46.5K |
| Eastern Band of Cherokee Indians | 68 | 2 | 2 | $565.9K | – | – |
| Oneida Nation (Wisconsin) | 34 | 2 | 2 | $121.5K | – | – |
| Tulalip Tribes | 49 | 2 | 2 | $53.5K | – | – |
| Lummi Nation | 140 | 1 | 1 | – | – | $100.0K |
| Blackfeet Nation · Menominee Indian Tribe of Wisconsin · Calista Corporation · Doyon, Limited · Pokagon Band of Potawatomi Indians | 203 | 0 | 0 | – | – | – |

**Read the zeroes correctly.** Calista's 98 shareholder businesses and Pokagon's
68 are village artists, caterers and single-truck haulers. A 0% federal-link
rate there is a fact about what a shareholder business directory *is*, not a
coverage gap. The overall **8.5% link rate is the finding**: a TERO certification
is overwhelmingly a *local subcontracting* credential, and only a thin top slice
of each list touches federal prime work.

---

## The denominator, stated plainly

`prime_contracts.csv` is Cedar's **Native-relevant slice** of FPDS, not all of
FPDS — 15,964 distinct awardee names over 1.2M rows. So `NO_MATCH` means *"not
in Cedar's Native federal contracting universe."* A certified firm holding a
federal contract that Cedar's universe does not cover would land in the 2,007
and look identical to a firm with no federal work at all. **Those two cases are
not separated by this build**, and the honest statement of the result depends on
saying so.

What *was* ruled out is a normalisation failure: a token-set-equality re-match
over all 2,007 no-match rows, corroborated by city or state, found **2**
additional candidates. Name-order and spacing variants are not hiding a
population.

---

## The web probe

`1000 web` probes the 99 hosts the directory itself published a website for
(105 directory rows, restricted sources excluded before the host list is
built), applying
the machine-readable routes first, honouring `robots.txt` fetched with our own
user agent, one request per second, hard request cap.

This is the narrowest part of the mandate and the reason is structural: the
directory publishes a website for **316 of 3,364** staging rows and **151** of
the 2,393 promoted ones, and those 151 collapse to **99 distinct hosts covering
105 rows** once malformed and duplicate URLs are dropped. An earlier pass (`TBD-L00_business_identifiers.jsonl`,
shard L) probed 74 businesses over 576 requests and returned **one** hit, which
was a false positive on `myspace.com`. This pass made **1,779 requests across all 99 hosts** (379 × 200, 1,162 × 404,
144 transport failures, 54 × 202, 18 × 400, 18 × 500, 2 × 429, honoured) and
found a labelled identifier on **5 hosts**: 13 CAGE, 5 UEI, 9 DUNS observations,
deduplicating to **12 crosswalk rows on 6 firms** —

| host | harvested |
|---|---|
| `losipro.com` | CAGE 04V88, UEI KSYNUXJ92J17 |
| `pci-ss.com` | CAGE 7TAW5, DUNS (withheld) |
| `whitebuffalotrucking.com` | CAGE 8HKQ1 |
| `www.meltzindustries.com` | CAGE 8JRR2, UEI YY3BELMTQ6R9, DUNS (withheld) |
| `www.thec3group.net` | CAGE 4DD38, DUNS (withheld) |

**3 of those resolved in Cedar's contracting tables and became rung −1 links** —
the only genuinely identifier-first links in the build. A **5.1% host hit rate**
is the honest measure of the route the mandate expected, and it is worth having
measured rather than assumed: it is not zero, and it is not the main road.

**A firm small enough to be on a TERO list is usually too small to publish a
capabilities statement.** The capability-statement pattern the mandate
describes is real, but it belongs to the 8(a) and ANC-subsidiary tier — and
those firms are already in `prime_contracts.csv` with their UEI attached, which
is why the federal-side join found them and the web probe did not need to.

---

## Files this build owns

| path | what |
|---|---|
| `code/1000_harvest_business_identifiers.py` | `sweep` / `web` / `verify` |
| `code/1001_link_businesses_to_contracting.py` | `build` / `verify` |
| `data/clean/native_business_contract_links.csv` | **one row per directory row**, 2,393 — status, tier, rung, UEI, CAGE, money |
| `data/clean/native_business_identifier_crosswalk.csv` | one row per (business, identifier), with `may_publish` |
| `data/clean/native_business_contracting_by_nation.csv` | the rollup above |
| `data/staging/business_registry/1000_local_corpus_sweep.json` | the measured negative |
| `data/staging/business_registry/1000_web_probe.jsonl` | one record per request |
| `review/native_business_link_holds_2026-09-02.csv` | every held or refused row |
| `review/native_business_identifier_proposals_2026-09-02.csv` | 71 owner proposals |
| `data/clean/_1001_summary.json` | the run's own numbers |

**Nothing rewrites `native_owned_businesses.csv`.** The 950–959 agent owns that
file's columns; this build reports what should be merged and writes it
elsewhere.

### The shared crosswalk is written by two scripts, safely

Both 1000 and 1001 write `native_business_identifier_crosswalk.csv`. A plain
append duplicates on re-run; a plain overwrite lets whichever ran last delete
the other's work — the rebuild-reverts-the-enricher trap `START_HERE` records
four separate times. `open_crosswalk(built_by)` rewrites the file keeping every
row it did not author, so **either script may be re-run in any order**.

---

## The one policy tension, flagged rather than resolved

`business_name_is_person_name` is `1` on 280 rows and `-1` (unknown) on 327.

* The **owner's rule** is that a firm's name is not PII even when the firm is
  named after its owner, and a prior pass wrongly withheld 521 rows on that
  ground.
* **Cedar's coded policy** (`cedar_domain.INDIVIDUAL_NATIVE_WITHHELD_FIELDS`) is
  narrower and is about the **identifier**, not the name: SAM's public entity
  search resolves a UEI to a name *and a street address*, so for a firm whose
  legal name is a person's, the UEI is a pointer to that person's front door.

Both can be true. Every row therefore carries its identifier plus
`identifier_publish_gate` ∈ {`PUBLISH`, `WITHHOLD_PENDING_RULING`} and the basis,
so this is a finding the owner can rule on rather than a deletion nobody can
see. **29 crosswalk rows** are gated this way today, on **16 linked directory rows**.

## Licensing and consent, as applied

* **DUNS** is harvested where a site prints it (it is evidence) and written with
  `may_publish = N`. `verify` fails the build if a DUNS row is ever marked
  publishable, and the synthetic test proves that check fires.
* **`sam_prime_contracts_fy2000_2007.csv` names are D&B Open Data** and were
  used as match evidence only. `evidence_licence` flags any link resting solely
  on them; on this run that is **0 of 257** — every link is corroborated by an
  open-source name as well.
* **`TERMS_STATED_RESTRICTIVE`** sources are excluded from the web host list
  before it is built, and `verify` asserts that no crosswalk row from such a
  source is ever `may_publish = Y`. Navajo Nation's 346 rows are linked and
  measured, and every one is `may_publish = N`.
