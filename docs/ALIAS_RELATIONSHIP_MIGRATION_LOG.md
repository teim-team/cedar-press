# Alias table and typed relationships — migration log

Built 2026-08-07 by `code/97_build_aliases_and_relationships.py`.
Spec: `SPEC_v2_ENTITY_EVENT_INTELLIGENCE.md` §5.3 (aliases) and §5.4
(relationships). Every number below is recomputed by the script and mirrored in
`data/clean/_97_summary.json`; none of it is hand-typed (regression rule 10).

Outputs:

| File | Rows |
|---|---:|
| `data/clean/entity_aliases.csv` | 5,943 |
| `data/clean/entity_relationships.csv` | 2,292 |
| `review/relationship_migration_issues_2026-08-07.csv` | 480 |
| `data/clean/codebook_master.csv` | +23 variables |

IDs come from `cedar_ids.allocate("CEDAR-ALIAS"/"CEDAR-REL", n)`. No ID is
constructed inline anywhere in the script. Enums come from `cedar_domain`;
nothing it defines is re-declared. Name normalisation is
`33_apply_party_rulings.norm`, imported (regression rule 8).

---

## Why the flat file had to go

`entity_hierarchy.csv` is one row per entity with `parent_entity_id`,
`ultimate_parent_entity_id` and `ancsa_region_entity_id` in adjacent columns.
Adjacency is the defect. A parent is an owner and a region is a place, and a
column layout cannot tell a reader — or a roll-up — which is which. In the typed
table the **type answers that by itself**: `cedar_domain.bears_ownership()`
returns `False` for `associated_with_region`, and the script asserts that
before it writes a single row.

The measured size of the thing being prevented: **174 non-ownership edges sit on
entities holding $57,043,179,871 of prime obligations that a flat parent column
would have moved upward** — $32.87B along `associated_with_region`, $23.91B
along `village_corporation_for`, $264M along `constituent_band_of`. Zero dollars
travel along any of them now, structurally, because the roll-up is defined as
the sum over ownership-bearing edges only.

---

## Task A — aliases (5,943 rows, all 1,310 entities covered)

| `alias_type` | Rows | Where from |
|---|---:|---|
| `common` | 2,901 | spine `canonical_name` and `aliases` |
| `full_form_federal_filing` | 1,799 | generated (below) |
| `legal` | 691 | `fr_official_name`; ledger `legal_business_name` variants |
| `shortened` | 226 | spine `aliases` shorter than the canonical name |
| `acronym` | 142 | spine `aliases` (script 51's ANC acronyms) |
| `brand` | 104 | `brand_family_registry.csv`, Tier A |
| `diacritic_folded` | 57 | ASCII fold of names carrying real orthography |
| `source_specific` | 23 | ASCII fold of names whose only non-ASCII is a dash |

Tier A 4,015 / Tier B 1,928.

### Generated federal long forms

The spine stores SHORT names; federal systems file LONG ones. Generation is
**class-gated** — `Native Village of X` / `Village of X` / `X Tribe` for Alaska
Native village governments, and `X Tribe` / `X Tribe of <state>` /
`X Indian Tribe` / `X Nation` for tribes. `Confederated Tribes of X` is
generated **only** where the entity's own official names already contain
"Confederated"; generated for every tribe it would have invented "Confederated
Tribes of Chickasaw", which is not a name anyone files.

A second guard drops any variant that would double a governmental unit word:
"Accohannock Indian Tribe" + `X Nation` produced *"Accohannock Indian Tribe
Nation"* on the first pass. A bad alias is worse than no alias.

Generated variants are **Tier B, confidence 0.60** — they are unconfirmed by
construction, since any variant that matched an official name was deduplicated
against the real alias instead.

### Municipal look-alike guard — 330 variants held at confidence 0.40

"Village of X" can land on a municipality. A variant is guarded when its
identifying word is a `cedar_domain.NAME_TRAPS` entry, or when the name is a
municipality in two or more states, or in a state other than the entity's own.
Those 330 are **confidence 0.40, Tier B** and can never auto-link; each is a row
in the review file.

The municipality list is a **proxy and is labelled as one**: 5,710 distinct city
names taken from `recipient_city_name` and `place_of_perform_city` in
`prime_contracts.csv`, plus the spine's own `city` column, cached to
`data/interim/_place_names.json`. No gazetteer was fetched
(`docs/PULL_DISCIPLINE.md`).

### The fold folds; it does not split

`Ukpeaġvik` → `Ukpeagvik`, never `ukpea vik`. `ġ`, `ł`, `ʻokina`, kahakō, `ñ`,
`ḷ` and curly quotes are all handled; the fold never inserts a space. Two forms
are stored where they differ, because the IRS dropped the ʻokina entirely
("Hui O Kuapa") while other systems keep an ASCII apostrophe ("Tohono
O'odham"). Folded rows deduplicate on the **literal string**, not the
normalised one — a correct fold normalises identically to its accented source,
so a normalised dedupe would silently delete the entire family. That bug was
live in the first run of this script and cost 26 of the 57 rows.

---

## Task B — typed relationships (2,292 rows, 8 of the 51 types)

| `relationship_type` | Rows | Bears ownership | Source |
|---|---:|:--:|---|
| `owned_by` | 1,462 | yes | identifier ledger, Tier A / ruled |
| `associated_with_region` | 391 | **no** | `ancsa_region_entity_id` |
| `affiliated_with` | 148 | no | HUD ONAP TDHE list |
| `brand_of` | 106 | no | `brand_family_registry.csv`, Tier A |
| `village_corporation_for` | 77 | **no** | `village_corp_namesake_pairs.csv` |
| `operated_by` | 56 | no | federally operated BIE schools |
| `chartered_by` | 30 | **no** | TCU / CDFI `parent_entity_id` |
| `constituent_band_of` | 22 | **no** | constituency `parent_entity_id` |

Tier A 2,123 / Tier B 169.

### Deviation 1 — `parent_entity_id` was NOT mapped wholesale to `subsidiary_of`

Applied literally, that mapping would declare 22 constituent **bands** to be
corporate subsidiaries of their umbrella tribe. `subsidiary_of` is
ownership-bearing, so Bois Forte, Fond du Lac, Leech Lake, Mille Lacs, White
Earth and Grand Portage would have rolled up into the Minnesota Chippewa, and
the five Paiute of Utah bands, the four Te-Moak bands and the two Passamaquoddy
communities likewise — $264M of prime obligations moving on a column layout.

A band is a government, not a subsidiary. Typing is class-aware:
constituency entities → `constituent_band_of`; tribal colleges and CDFIs →
`chartered_by` (their `ownership_basis` says *chartered*, not *owned*), Tier B
where that basis was resolved by containment and Tier A where it was resolved by
core or alias match. **Zero `subsidiary_of` edges exist**, because the flat
parent column contained no corporate subsidiary relationship at all.

### Deviation 2 — ledger `legal_business_name` is not always an alias

The instruction to seed aliases from `legal_business_name` where it differs from
the canonical name would make *"Petro Star, Inc."* an alias of Arctic Slope
Regional Corporation. Petro Star is a **subsidiary**, and calling it an alias
merges a company into its owner. The split applied:

* 199 rows where the registered name is a variant of the same legal person →
  alias, type `legal`.
* 7,088 ledger rows naming a **distinct firm** → not aliases. The Tier-A and
  ruled subset became 1,462 `owned_by` edges; the rest stay in the ledger and
  were not promoted here.

Tier X ledger rows were excluded everywhere. Tier X never resurfaces.

### `ancsa_region_entity_id` → `associated_with_region`, 391 edges

Never a parent, never an ownership edge. Asserted before writing.

### Brands — 106 `brand_of` edges at Tier A

A brand family has no spine entity, because a brand is a name family and not a
legal person. `source_entity_id` is null, the brand name and its `alias_id` are
in `notes`, and the ruling that produced it is in `evidence_text`.

### Direct tribe → company ownership — 1,462 edges, no invented layer

The Chickasaw Nation Industries pattern. The firm is `owned_by` the tribe
directly; no intermediate holding company is invented, per AGENTS.md — below the
top level only the tribe can verify the structure. `source_entity_id` is null
(the firm has no spine entity) and the firm name, identifier type and identifier
are in `notes`.

### 56 federally operated BIE schools — `operated_by`, `ultimate_native_owner` NULL

Native-serving is not tribally owned. A BIE-operated school may serve a tribe's
children and sit on its land and it is still not the tribe's. `target_entity_id`
is null because Cedar holds no entity for the federal government; the operator
is named in `notes`. **They are not rolled up to anyone.** The 129
tribally-controlled BIE schools got no ownership edge either — the spine records
no parent for a single one of the 185 BIE schools, and inventing one from the
school's name is precisely the containment defect.

### 148 TDHEs — recorded by name, never resolved

Every one of the 148 previously "resolved" onto its own tribe, which asserts
that the grantee and the government are one legal person — exactly what HUD's
own list is careful to avoid. Each TDHE now gets one edge carrying **no
`target_entity_id`**, with the published name, the tribe HUD prints it beneath,
and the reason, in `notes`. All 148 are staged in the review file.

**Vocabulary finding:** the precise relationship is *\<TDHE\> `authority_of`
\<tribe\>*, but the TDHE is the side with no entity id, and the 51-type
vocabulary has **no reciprocal of `authority_of`** — every governmental type is
source-centric. The tribe-side edge is therefore recorded as `affiliated_with`
(non-ownership) with the exact semantic spelled out in `notes`. If a reciprocal
type is ever added, these 148 rows are the migration.

Seven of the 148 have no resolvable tribe either, so both endpoints are null and
only the names survive. That is the honest state of the data.

---

## Verification — all six assertions pass

| Assertion | Result |
|---|---|
| Every `relationship_type` in `ALL_RELATIONSHIPS` | **PASS** — 8 distinct types used, 0 out of vocabulary |
| No generic `related_to` | **PASS** — 0 rows |
| No non-ownership edge carries a roll-up dollar | **PASS** — $0 rolled; 174 such edges sit on $57.04B a flat column would have moved |
| No ANCSA region appears as a parent | **PASS** — 0 typed edges, 0 flat cells (excluding self-references) |
| No village corporation ↔ namesake village government parent edge | **PASS** — 0 violations across all 77 pairs |
| Round trip on `ultimate_parent_entity_id` | **PASS** — 930 self-parent, 22 reachable through typed edges, 0 unreachable |

### The ANCSA assertion failed first, and the reason is a finding

The first run reported 268 violations. They were not violations. `ANRC-ARCSLO-00`
is **two things at once**: Arctic Slope Regional Corporation, a company that
really does own Petro Star, and the Arctic Slope ANCSA region, a place that 17
village corporations sit in and that owns none of them. One id, two roles, and
only the edge type plus the source entity's class tells them apart.

The check was narrowed to what it should always have meant: an ownership edge
pointing at an ANRC **from an entity for which that ANRC is the region**. That
is 0. Ownership edges pointing at an ANRC *as a corporation owning a firm* are
268 and are correct. The flat file's 12 apparent region-as-parent cells were the
12 ANRC rows naming themselves as their own ultimate parent — self-references,
not parents. Logged as `anrc_id_plays_two_roles` in the review file.

### What the round trip actually shows

`ultimate_parent_entity_id` is **self-referential on 930 of 952 rows** and equal
to `parent_entity_id` on the other 22. It encodes no ownership chain anywhere.
**Zero `owned_by` edges came out of it.** Every real tribe→company ownership
fact in this project lives in the identifier ledger, not in the hierarchy file —
which is worth knowing before anyone builds a roll-up on the hierarchy file
again.

---

## Other findings

* **`entity_hierarchy.csv` is stale.** 952 rows against a 1,310-entity spine:
  185 BIE schools, 64 CDFIs, 43 UIOs, 37 TCUs and 29 Native financial
  institutions have no row in it at all. Hierarchy columns for those 358 were
  read from the spine instead, and every edge records in `source_id` which file
  it came from. The flat file was never rebuilt after scripts 52/61/73/75
  appended those classes.
* **The spine's `aliases` column carries generated permutation junk** on BIE
  schools — `Atsá Biyáázh Community School School Board, Inc.`,
  `Hanáádli Community School/Dormitory Inc. Inc`. These are pre-existing spine
  rows, not produced here, and the spine is not this PR's to modify. They flow
  into the alias table as `common` and should be cleaned at the source.
* **2 of the 106 brand names were already on file as another alias type**, so
  the alias table holds 104 `brand` rows while all 106 `brand_of` edges resolve
  to a real `alias_id`.

---

## Re-running

Idempotent. Re-running rewrites both CSVs, refreshes only its own 23 codebook
variables, and keeps `codebook_undocumented_public` at 0. New `alias_id` /
`relationship_id` values are minted on each run (the counter never rewinds);
nothing downstream keys on them yet.

`code/62_no_regression_check.py`, before and after: **no regressions** both
times.

---

## UPDATE 2026-09-02 — the 1,772 blank endpoints, promoted from prose

*`code/1098_entity_rel_counterparty.py`. Full write-up:
**`docs/ENTITY_LAYER_DEEPENING_2026-09-02.md`** section 1; the model decision is
**ADR-020** in `docs/ARCHITECTURE_DECISIONS.md`.*

1,772 of `entity_relationships.csv`'s 2,292 rows (77.3%) carry a blank endpoint.
**Not one of them is unrecoverable**, and the standing read —
*"996 recover a UEI only from prose; 466 recover nothing"* — is wrong on the
466: **they recover a CAGE code.** All 1,462 `owned_by` rows parse on one
anchored pattern, 996 UEI + 466 CAGE, 0 unparsed.

The blank is CORRECT, and the rows say so: *"No spine entity for the firm and no
intermediate holding layer invented."* A UEI or CAGE identifies a
**registration**, and `IDENTIFIER_STANDARD` section 2 makes a registration a
sub-hub, never a spine row. Minting would put 1,462 non-entities in the entity
namespace.

Nine columns now carry what the sentence carried —
`counterparty_kind` (`firm_registration` 1,462, `tribal_designated_housing_entity`
148, `brand_family` 106, `federal_government` 56),
`counterparty_name_as_recorded`, `counterparty_identifier_type` and
`_identifier`, `counterparty_identity_state`, and a
`counterparty_nest_enterprise_id` bridge — under an **anti-fabrication
invariant: every promoted value is a verbatim substring of that row's own
`notes`**, proved to fire.

262 of 1,462 firms (17.9%) bridge to a NEST enterprise sub-hub, and only where
both sides agree on the owner (published UEI 29, published CAGE 0, unique name
under the same hub 233). 23 more would resolve through NEST's own
`uei_candidate` and are refused: a candidate on one side plus a candidate on the
other is not evidence. Every unresolved row now records WHY.

**One resolved on the identifier and disagreed about the owner** — the entity
layer's first cross-source ownership disagreement. `Laulima Government
Solutions, LLC` (UEI `QTJZT9K41S61`) is Bering Straits here at tier A and
Alakaina Foundation in NEST, sourced from `beringalakaina.com` — a host naming
both parents. Rule 11: a joint venture genuinely has two. **Refused, not
reconciled.** `review/entity_rel_nest_owner_conflicts_2026-09-02.csv`, owner
queue **EL-2**.
