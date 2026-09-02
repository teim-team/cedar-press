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

**186 of 2,393 directory rows are now linked to a federal contracting record**
at tier A or B — **153 distinct UEIs**, exposing **$6.32B in prime obligations**
and **$474.7M in subaward value**. Restricted to rows the directory itself marks
publishable: **135 rows, 111 UEIs, $5.33B prime and $467.5M subawards**.
A further **55 tier-C proposals** and **8 ambiguous holds** are staged for a
ruling rather than published.

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
| 1 | exact name + **city and state** both agree | A | 89 |
| 1b | exact name + **city** agrees, state silent | B | 0 |
| 2 | exact name + **state** agrees | A | 23 |
| 2b | exact name + state agrees, but the recorded state was **truncated** | B | 0 |
| 3 | exact name + the **certifying nation's own service area** | B | 74 |
| 4 | exact name, **unique** in the federal universe, no geography | C | 55 |
| 5 | stop | X | 24 (16 proposed, 8 held) |

Rungs 1b and 2b fired zero times on this run and are kept anyway: every Navajo
row whose state was truncated also carried a city that matched, so the stronger
rung took it. A rung with no rows is evidence the ladder is ordered correctly,
not dead code.

Refusals and holds, both written down rather than dropped:

| outcome | rows | meaning |
|---|---:|---|
| `NO_MATCH` no federal recipient of this name | 2,007 | the honest majority |
| `NO_MATCH` name cannot found a match (rule 1) | 113 | 106 single-token, 7 all-generic |
| `REFUSED` state conflict | 8 | the veto fired |
| `HOLD_AMBIGUOUS` | 8 | one name, several federal entities |

`review/native_business_identifier_proposals_2026-09-02.csv` carries **71
proposals** in the owner's inbox format (8 holds, 8 conflicts, 55 tier-C), each
with the candidate UEIs and the `cage.dla.mil` verification protocol attached.

---

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

| nation | firms | linked | UEIs | prime obligations | subawards |
|---|---:|---:|---:|---:|---:|
| Muscogee (Creek) Nation | 337 | 37 | 37 | $2.55B | $52.2M |
| Cherokee Nation | 836 | 66 | 66 | $1.75B | $385.9M |
| Arctic Slope Regional Corporation | 20 | 1 | 1 | $1.15B | $29.3M |
| Navajo Nation *(not publishable)* | 346 | 51 | 44 | $1.01B | $7.2M |
| Tohono O'odham Nation | 17 | 3 | 3 | $752.2M | – |
| Poarch Band of Creek Indians | 13 | 3 | 3 | $146.5M | – |
| Three Affiliated Tribes (MHA) | 133 | 1 | 1 | $39.6M | – |
| Confederated Salish & Kootenai | 116 | 13 | 12 | $33.1M | – |
| Eastern Band of Cherokee Indians | 68 | 2 | 2 | $4.0M | – |
| Confederated Tribes of Grand Ronde | 81 | 4 | 4 | $1.6M | $46.5K |
| Oneida Nation (Wisconsin) | 34 | 2 | 2 | $372.3K | – |
| Tulalip Tribes | 49 | 2 | 2 | $74.8K | – |
| Lummi Nation | 140 | 1 | 1 | – | $100.0K |
| Blackfeet · Menominee · Calista · Doyon · Pokagon | 203 | 0 | 0 | – | – |

**Read the zeroes correctly.** Calista's 98 shareholder businesses and Pokagon's
68 are village artists, caterers and single-truck haulers. A 0% federal-link
rate there is a fact about what a shareholder business directory *is*, not a
coverage gap. The overall **7.8% link rate is the finding**: a TERO certification
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
(151 rows, restricted sources excluded before the host list is built), applying
the machine-readable routes first, honouring `robots.txt` fetched with our own
user agent, one request per second, hard request cap.

This is the narrowest part of the mandate and the reason is structural: the
directory publishes a website for **316 of 3,364** staging rows and **151** of
the 2,393 promoted ones. An earlier pass (`TBD-L00_business_identifiers.jsonl`,
shard L) probed 74 businesses over 576 requests and returned **one** hit, which
was a false positive on `myspace.com`. This pass finds
`__WEB_RESULT__`.

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
