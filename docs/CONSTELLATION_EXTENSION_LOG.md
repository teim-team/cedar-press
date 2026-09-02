# CONSTELLATION EXTENSION LOG — workstream INT, 2026-09-02

What `code/852_extend_constellation_edges.py` did to the ADR-014 `serves`
layer that `code/851_build_constellation_edges.py` built on 2026-09-01, why,
and what it found wrong on the way. Every number here was measured with
`csv.reader` against the files on disk, not quoted from a docstring.

    build     py -3 code/852_extend_constellation_edges.py
    verify    py -3 code/852_extend_constellation_edges.py verify   -> 0
              py -3 code/851_build_constellation_edges.py  verify   -> 0

851 is still the library and still a valid verifier. It is no longer the build
entrypoint: run 852, which imports 851, runs every one of its source functions
unchanged, and adds four more.

---

## 1. The headline

| | 851, as shipped 2026-09-01 | 852, 2026-09-02 |
|---|---:|---:|
| edges | 2,435 | **3,153** |
| `chartered_by` | 21 | **44** |
| `managed_under_contract` | 63 | **78** |
| `registered_with` | 2,216 | **2,365** |
| `declares_service_to` | 59 | **588** |
| `located_within` | 76 | **78** |
| `sole_entity_in_area` | 0 | **0** |
| `tier_is_adr014 = N` | 2,216 | **0** |
| distinct hubs reached | 75 | **253** |
| unresolved rows converted | 2,248 | **2,449** |
| geography-vs-self-declaration conflicts | 1 | **0 (adjudicated)** |
| refusals | 4,394 | 5,243 |

Six of 851's edges are gone and 724 are new. Five of the six losses are 851's
own output catching up with a spine refresh that happened after it last ran —
rebuilding 851 alone produces the same five — and they are all corrections:
`FORT APACHE HERITAGE FOUNDATION INC` moves from **Apache Tribe of Oklahoma**
to **White Mountain**, `APACHE STRONGHOLD` from Apache Tribe of Oklahoma to
**San Carlos**, `APACHE YOUTH MINISTRIES` to **White Mountain**. The sixth is
the Blackwater revocation in section 4.

Row conservation holds per source. Every source row is either an edge or a
refusal, and the build prints the table:

    native_owned_businesses            2,365 edges +    28 refusals = 2,393
    shard_f/ihs_selfgov_compacts           4 edges +   143 refusals =   147
    shard_f/ihs_uio_register               0 edges +    45 refusals =    45
    tcu_cdfi/aihec_tcu_roster             22 edges +    15 refusals =    37
    org_membership/shard_f               531 edges +   453 refusals =   984
                                         (531 edges fold 550 roster rows;
                                          453 + 550 = 1,003 named rows)

Column diff on both output files: **gained [], lost []**. The schema is
unchanged; only rows were added.

---

## 2. ADR-014 Amendment 1 — `registered_with` adopted at rank 3

Written into `docs/ARCHITECTURE_DECISIONS.md` between the `<!-- BEGIN ADR-014
-->` / `<!-- END ADR-014 -->` markers; nothing outside the markers was
touched. `EXTENSION_TIERS` in 851 is now empty and the mechanism is kept, not
deleted, so the next tier that arrives from implementation is flagged
`tier_is_adr014 = N` until it is argued in rather than smuggled in.

**Rank 3, between `managed_under_contract` and `declares_service_to`.** Below
a 638 contract or self-governance compact, because that is a *federal*
instrument transferring the operation of a programme and this is a *tribal*
instrument recognising a relationship. Above the entity's own account of
itself, because a TERO listing is the sovereign talking about the entity and a
990 mission statement is the entity talking about itself — the owner's
"affiliated with is better".

A new invariant, `check_registered_with_adopted()`, fails the build if any
`registered_with` edge carries `tier_is_adr014 = N`, so the amendment cannot
silently un-land.

---

## 3. What was added, and what each rung is

### 3a. Finding A — 149 `registered_with` edges 851 refused on a blank column

851 keys the certifying nation off `certifying_authority_entity_id` and
refuses the row when it is blank — 149 rows. On **all 149** the sibling column
`certifying_authority_name` is populated: 81 "Confederated Tribes of Grand
Ronde" (TERO Indian Owned Business list) and 68 "Pokagon Band of Potawatomi
Indians" (Mno-Bmadsen vendor directory). Both names resolve to exactly one
Cedar hub. **+149 edges, +149 unresolved rows converted.** The 149 stale
refusals are dropped by `supersede_refusals_resolved_by_a_later_rung()`,
which is why `native_owned_businesses` now conserves exactly.

### 3b. Finding B — `chartered_by` 21 → 44, mostly from AIHEC

`served_entity_crosswalk.csv` carries 26 pre-extracted charter sentences
covering 13 distinct pairs. The page they came from is cached in full at
`data/raw/external/tcu_cdfi/aihec_tcu_roster_2026-08-06.txt`, one ~1,200-char
narrative profile per TCU. Re-reading all 37 profiles with an **agent
pattern** — the charter verb plus the actor that performed it — yields 22.

Anchoring matters and was measured to matter: several college names recur in a
locations list lower down the page, so anchoring on the bare name with
`rfind` put the Bay Mills charter sentence inside the Aaniiih Nakoda block and
lost it. Blocks are anchored on `Name (ACRONYM)`.

Requiring an ACTOR, not just a nation near a verb, is what keeps this honest.
Aaniiih Nakoda's profile says *"In 1984 they established Fort Belknap
College"* — the nation is in the **college's own name**, which is exactly
ENTITY_MATCH_RULES rule 7's Turtle Mountain trap. No actor, no edge, correctly.

22 awarded / 15 refused / 37 profiles. The 22:

    Bay Mills CC -> Bay Mills                Nueta Hidatsa Sahnish -> Three Affiliated
    California Indian Nations -> Twenty-Nine Palms   Oglala Lakota -> Oglala Sioux
    Cankdeska Cikana -> Spirit Lake          Red Lake Nation -> Red Lake
    Chief Dull Knife -> Northern Cheyenne    Salish Kootenai -> Confederated Salish
    College of Menominee Nation -> Menominee Sisseton Wahpeton -> Sisseton-Wahpeton
    College of the Muscogee Nation -> Muscogee   Sitting Bull -> Standing Rock
    Diné College -> Navajo                   Stone Child -> Chippewa-Cree
    Fort Peck CC -> Assiniboine and Sioux    Tohono O'odham CC -> Tohono O'odham
    Keweenaw Bay Ojibwa CC -> Keweenaw       Turtle Mountain College -> Turtle Mountain
    Little Big Horn -> Crow                  Navajo Technical University -> Navajo
    Little Priest -> Winnebago               Northwest Indian College -> Lummi

### 3c. `managed_under_contract` — the IHS Title V register, finally read

`data/staging/tribe_harvest/shard_f/ihs_selfgov_compacts.jsonl`, 147 holders
of an ISDEAA Title V self-governance compact with IHS, each with its compact
year. Three dispositions, and they add to 147:

* **4 edges.** IHS prints some entries as `Nation – Programme`
  ("Pit River Tribe – Pit River Health Service, Inc."). That single line is
  the instrument naming both the compacting nation and the facility operated
  under it — ADR-014's rank-2 basis, verbatim.
* **88 refused, `self_edge_compactor_is_the_nation_itself`.** The entry is the
  nation. A nation does not hold a `serves` edge to itself. A new invariant,
  `check_no_self_edge()`, enforces it.
* **55 refused, `compact_register_names_no_member_nation`.** The entry is an
  organisation and the register names no nation it compacts on behalf of.
  Only the organisation's own roster can supply that — see 3d.

**The Urban Indian Organization register (45 rows) yields nothing, and that is
the right answer, recorded as 45 refusals rather than as silence.** IHS's own
sentence says the Title V contract is between the UIO and the **Indian Health
Service**. The register names a city and an IHS area; it names no nation.
Cedar's spine already says the same thing in the organisations' own words,
which 851 refuses as `entity_declares_no_single_hub` (43 rows).

### 3d. `declares_service_to` 59 → 588 — published membership rosters

`data/staging/org_membership/shard_f.jsonl`, 1,047 rows across 85
organisations, never read by 851. An intertribal council's own membership page
naming a nation is the entity's own words about who it serves. 531 edges over
25 organisations and 232 hubs, one edge per (organisation, nation) pair rather
than per spelling. 10 of the 531 are at `managed_under_contract` because the
organisation also appears in the IHS Title V compact register; both sources
are in the excerpt and the tier is separable with one filter on
`evidence_basis`.

Two guards, and without either one the route produces confident nonsense.

**The page guard.** Shard F's 40%-of-strings-match page test is necessary and
not sufficient. It passed `narf.org/resources/tribes-oppose-line-5-pipeline/`
at 57%, because a page listing the tribes that filed an amicus brief against
a pipeline is tribe-dense and is not a membership roster; 21 rows would have
asserted that the Native American Rights Fund *serves* Bay Mills, Grand
Traverse and Sault Ste. Marie. It also passed a Great Plains Tribal Leaders
Health Board **news** page about a syphilis response effort (14 rows). So the
source page's own URL must name membership: some path segment must be
`members`, `member-tribes`, `membership`, `tribes`, `tribes-served`,
`who-we-serve`, `tribal-councils`, `our-communities` or a close relative, and
the final segment must not read as a headline. **81 rows refused**, including
NARF's 21, the Great Plains news page's 14, `/meeting-notes/`,
`/who-we-are/`, `/benefitting-arizona/`, `/tribes-and-climate-change/`,
`/board-of-directors/`, `/itf` and every `/wp-json/wp/v2/` API root.

**The residue guard (ENTITY_MATCH_RULES rule 7).** Shard F labels 507 of its
rows `containment`, and rule 9 says containment never accepts alone.
Independently re-resolving every published string through 851's HubIndex
agrees with shard F on 492 rows and disagrees on 7 — and **on all 7 the shard
is wrong**: `Flandreau Santee Sioux Tribe` → Santee Sioux, `Catawba Indian
Nation` → Piscataway, `Mashpee Wampanoag Tribe` → Wampanoag. Agreement is
therefore a real second observation. But the HubIndex alone, with no state to
gate on, awarded `Grand Portage Band of Lake Superior Chippewa` to **Portage
Creek, Alaska** and `Southern Indian Health Council, Inc.` to **Southern Ute,
Colorado**, both on a one-token prefix. So every award must also leave an
EMPTY residue against the hub's own name union — Southern Ute leaves `health`,
Portage Creek leaves `superior chippewa` — and an institution-form word
anywhere in the string is a separate veto. **53 + 76 rows refused.** Where the
two matchers genuinely disagree the row is HELD, not decided:
`two_matchers_disagree_on_the_hub`, 2 rows, both Mashpee Wampanoag.

The regional coherence of the result is the best available external check on
it: Northwest Portland Area Indian Health Board resolves to 25 WA + 7 OR + 4
ID; Southern Plains Tribal Health Board to 23 OK and nothing else; Southern
California Tribal Chairmen's Association to 13 CA; Inter-Tribal Council of
Michigan to 11 MI; Rocky Mountain Tribal Leaders Council to 7 MT + 2 WY + 1 ID.

---

## 4. RULING 852-1 — Blackwater Community School

851 shipped exactly one `geography_selfdeclaration_conflict = Y`:

    Blackwater Community School -> Navajo      managed_under_contract
                                -> Gila River  located_within   (flagged)

**Held for the geography. The Navajo edge is REVOKED.**

ENTITY_MATCH_RULES rule 7 says the record's own words outrank the polygon it
sits inside. The question is *whose* words, and the answer here is nobody's.
The Navajo edge rests on one coded administrative field in a third-party
directory — `Navajo_Operation = 'Tribally-Controlled (Navajo)'`. That is not
the school's account of itself, and the **same directory row contradicts it
three times**:

* street address `3652 E. Blackwater School Road, Coolidge, Arizona 85128`;
* published coordinates (33.0316, −111.5798) fall inside the **Gila River
  Indian Reservation** polygon (GEOID 1310R);
* `Education_Resource_Center = Albuquerque, NM`, not one of the five
  Navajo-region ERCs.

Rule 7 ranks a coded third-party flag **below** both a geocode and the
record's own printed text. Blackwater is a Gila River Indian Community school
and the field is a data error.

**Blackwater is NOT promoted to `managed_under_contract` on the strength of
`Operation_Type = Tribally-Controlled` plus a polygon naming one nation.**
ADR-014 says nothing is promoted a tier by resemblance: the instrument names
no nation and the polygon is `located_within`-grade evidence. The edge stays
at `located_within`, and its conflict flag is cleared because the thing it
conflicted with no longer exists.

### The search for others of the same shape

The detector is internal to the source and needs no outside knowledge:
`Navajo_Operation` claims Navajo — does `Education_Resource_Center` route the
school to a Navajo-region ERC (Shiprock, Tuba City, Crownpoint, Chinle, Window
Rock)? Over 187 schools the two fields agree **185** times. Two exceptions,
and the geocode splits them in opposite directions:

| school | ERC | polygon | ruling |
|---|---|---|---|
| Blackwater Community School | Albuquerque | **Gila River Indian Reservation** | REVOKE |
| Pine Hill Schools | Albuquerque | **Navajo Nation Off-Reservation Trust Land** | CONFIRM |

Pine Hill is Ramah Navajo — its own published website is
`phswarriors.rnsb.k12.nm.us`, the **R**amah **N**avajo **S**chool **B**oard —
and Ramah is a non-contiguous part of the Navajo Nation administered out of
Albuquerque. Two of three signals agree; no conflict; the edge stands.

A wider sweep (Navajo_Operation says Navajo, point is in no Navajo Nation
polygon) returns 12 schools. Eleven are the off-reservation dormitory and
border-town system — Flagstaff Bordertown Dormitory, Winslow Residential Hall,
Richfield UT, T'iisyaakin at Holbrook, Navajo Preparatory at Farmington — or
the Eastern Navajo checkerboard — Lake Valley, Pueblo Pintado, Wingate
Elementary and High, Dzilth-Na-O-Dith-Hle, Kinteel. Those land in **no**
polygon at all, so 851's geographic route already refused them
(`point_outside_every_aiannh_area`, 22 rows) and no edge ever rested on the
disagreement. **Only Blackwater lands inside a different nation's
reservation.** One conflict was the right count.

The ruling is generalised in code, not hand-patched:
`adjudicate_bie_navajo_field()` revokes whenever both corroborators point
away, and `reconcile_conflict_flags()` recomputes every conflict flag from the
surviving rows each run. `check_conflict_flag_is_earned()` fails the build if
a flag survives with nothing left to conflict with.

---

## 5. One route built, measured, and refused

*(**Re-measured 2026-09-02:** the table now holds 29,149 rows and **25,522** carry `record_scope = unresolved`. 5,561 is stale; the shape of the problem is not.)*

The obvious way to convert more of the unresolved Schedule C rows is the
filer's **own legal name** — `declares_service_to` says "the entity's own
words name the nation", and a 990 filer's name is its own words. It was built
and measured. It resolves **281 EINs covering 641 Schedule C rows**, and the
awards are:

    ONONDAGA GOLF AND COUNTRY CLUB          CAYUGA WINE TRAIL INC
    WEST SENECA SOCCER CLUB                 ONEIDA-MADISON ELECTRIC COOPERATIVE
    ROTARY CLUB OF SEMINOLE CHARITABLE FUND MEDICAL SOCIETY OF THE COUNTY OF ONEIDA
    ONONDAGA FREE LIBRARY                   CAYUGA CREMATORIUM INC

In upstate New York, Oklahoma and Florida the nation's name is also the
county's name, and a legal name cannot separate them. The route is refused
**wholesale**, and all 281 are written to
`cedar_constellation_refusals.csv` as
`filer_name_route_refused_placename_indistinguishable` so the next agent sees
the evidence instead of repeating the experiment. This independently confirms
851's finding on the same pile from the other direction: **no name-based route
converts the Schedule C backlog.** Its 3,706 `no_nation_named_with_a_service_
statement` refusals are the honest answer, not a gap.

---

## 6. Defects found in 851 and in ADR-014

**Fixed here (inside 852's own resolver, so 851's routes keep their exact
prior outcomes):**

* **A blank state was treated as a state MISMATCH.** `HubIndex.state_ok()`
  documents the right rule — *"Blank state cannot agree or disagree; say so
  rather than guessing"* — and `resolve()` never calls it, comparing
  `hubs[uid]["state"] == ""` instead. This is what hid finding A: Grand Ronde
  and Pokagon are both nationally unique and both were refused for disagreeing
  with a state that was never stated.
* **`HubIndex.states` is built and never read.** The class docstring explains
  at length that *"a hub has a SET of states, not one"* and that a
  single-state gate refused true matches for every reservation that spans a
  line — then `resolve()` compares the single spine value anyway. Navajo
  Technical University, Crownpoint NM, was refused against Navajo (spine state
  AZ). 852 accepts when the requested state is in the hub's own state set.
* **A four-letter nation is unreachable by name.** The ≥5-character
  single-token guard means `Crow` has no index entry at all, so *"LBHC is a
  public two-year community college chartered by the Crow Tribe of Indians in
  1980"* resolved to nothing. The guard is not loosened — it is what stops
  `bay` and `lake` — but a rule-7 residue rung sits beneath it: among hubs in
  the same state, accept the one whose own name union leaves an empty residue,
  if exactly one does.
* **`count_unresolved_universe()` counted backup files.** It globs
  `data/clean/*.csv`, which now matches
  `native_owned_businesses.bak_2026-09-02_010526.csv` and its twin, left by a
  concurrent workstream. That triple-counted 2,389 rows and reported the
  universe as **12,916** instead of **8,138**, deflating 851's own headline
  percentage. Patched in 851 itself.

**Reported, NOT fixed — these are owner decisions:**

* **`HUB_CLASSES` excludes nations that charter things.** It admits six spine
  classes and not `Federal-level constituency entity`, of which Cedar holds
  22: the six component bands of the Minnesota Chippewa Tribe (White Earth,
  Leech Lake, Bois Forte, Fond du Lac, Grand Portage, Mille Lacs), Ramah
  Navajo Chapter, the five Paiute Indian Tribe of Utah bands, four Te-Moak
  bands, both Passamaquoddy reservations, two Shoshone-Bannock bands. Each has
  its own council. AIHEC prints *"The White Earth Reservation Tribal Council
  established the White Earth Tribal and Community College in 1997"* — the
  strongest evidence ADR-014 defines — and the edge cannot be written.
  Refused and counted as `hub_class_excludes_constituency_entity` (1 row so
  far) rather than quietly widened, because widening touches every route
  including the 2,365 `registered_with` resolutions. **This is the single
  highest-value open decision in the layer.**
* **`sole_entity_in_area` should be demoted from tier to corroborator.** Two
  builds have now computed it: **27 edges cite it, 0 rest on it.** Listing it
  as a tier invites someone to try to use it as one. Recorded in ADR-014
  Amendment 1a.

---

## 7. Invariants

`851 verify` and `852 verify` both exit 0 on the shipped file. 852 runs 851's
full check set plus three new ones, and every detector was proven to fire by
injecting a synthetic violating row into the **real** shipped file and
confirming a non-zero exit:

| detector | synthetic violation | result |
|---|---|---|
| `check_no_self_edge` | edge whose `from_cedar_uid == to_hub_cedar_uid` | FAIL, exit 1 |
| `check_conflict_flag_is_earned` | conflict flag with no opposing stronger edge | FAIL, exit 1 |
| `check_registered_with_adopted` | `registered_with` with `tier_is_adr014 = N` | FAIL, exit 1 |
| `check_sole_entity_never_alone` (851) | rank-6 edge with empty corroboration | FAIL, exit 1 |
| `check_tiers_and_money` (851) | `money_rolls_through = Y` | FAIL, exit 1 |
| — | file restored untouched | PASS, exit 0 |

Rule 1 holds mechanically on all 3,153 rows: `is_ownership_claim = N`,
`money_rolls_through = N`, and no column in the schema can hold a dollar. A
tribe holding an ISDEAA Title V compact for a health corporation does not
thereby book that corporation's revenue, and an intertribal council's
membership list is not a list of its subsidiaries.

---

## 8. Scope boundary with the geography workstream (870–889)

852 built no competing AIANNH crosswalk. It re-uses the **same** cached Census
TIGER/Line 2024 file 851 used, `tl_2024_us_aiannh.zip`, whose 864 areas match
the geography workstream's published `geo_aiannh_dim.csv` row for row and
whose method matches their `assignment_basis =
point_in_polygon_tiger2024_aiannh`. Their published
`geo_point_aiannh_assignment.csv` covers gaming properties, gaming facilities
and NEPA projects (2,895 points) and carries **no BIE school points**, which
is why the point-in-polygon for the 187 BIE schools is computed locally. If
that workstream extends the assignment table to BIE schools, 851's
`src_geocode_aiannh()` and 852's `bie_navajo_field_audit()` should read it
instead. Flagged for them; not built here.

---

## 9. Files

Written:

    code/852_extend_constellation_edges.py            new
    docs/CONSTELLATION_EXTENSION_LOG.md               new (this file)
    docs/ARCHITECTURE_DECISIONS.md                    ADR-014 block only
    code/851_build_constellation_edges.py             tier table + universe fix
    data/clean/cedar_constellation_edges.csv          3,153 rows, 27 cols
    data/clean/cedar_constellation_refusals.csv       5,243 rows, 14 cols

Backups (nothing overwritten without one):

    data/clean/_bak852/cedar_constellation_edges.csv.bak_2026-09-02_pre852
    data/clean/_bak852/cedar_constellation_refusals.csv.bak_2026-09-02_pre852
    data/clean/cedar_constellation_edges.csv.bak_2026-09-02_pre852
    data/clean/cedar_constellation_refusals.csv.bak_2026-09-02_pre852
    docs/ARCHITECTURE_DECISIONS.md.bak_2026-09-02_pre852
    code/851_build_constellation_edges.py.bak_2026-09-02_pre852

Nothing was committed.

---

## UPDATE 2026-09-02 — do NOT mint the 2,408 unkeyed from-sides. Measured.

*Measured by the `_entity_layer` deepening pass; the decision is **ADR-020** in
`docs/ARCHITECTURE_DECISIONS.md`.*

2,408 of 3,153 edges (76.4%) have a name-only from-side, and the standing
proposal is to mint them because it "would most extend the deals and ownership
sweeps." Three measurements say otherwise:

1. **They are already identified.** 2,365 of the 2,408 come from
   `native_owned_businesses` at tier `registered_with` (TERO certification), and
   **all 2,365 join to `native_owned_businesses.business_source_id` through the
   `from_record_key` already on the edge.** A stable directory-row key is not a
   missing identity.
2. **The sweep was extended by minting nothing.** After `code/1100` promoted the
   `1001` crosswalk onto the directory, **186 of those from-sides now carry a
   published federal UEI**. Carrying `from_record_key` and the federal link is
   the whole extension.
3. **278 of them carry `business_name_is_person_name = 1`.** Minting a
   `cedar_uid` per unkeyed from-side would put **278 natural persons into the
   entity register**, which `docs/PUBLICATION_POLICY.md` forbids outright.

The remaining 43 are `np_mission` (39) and IHS self-governance compacts (4).

**If a class of these is ever minted it is the `CEDAR-ENT-` individually
Native-owned class, one reviewed row at a time, and never the 278.**
