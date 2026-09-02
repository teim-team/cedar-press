# Methodology — the Cedar entity layer

**Dataset 13. `data/spine/cedar_identity_register.csv`, 1,555 entities across
17 classes.** [measured 2026-09-02]

*Written 2026-09-02. This is the methodology record: what was pulled and from
where, how the rows were made, how identity was decided, what was decided and
why, what the known limits are, and how often it has to be re-pulled. It is not
the product copy (`docs/datasets/_descriptors.json`) and not the codebook
(`docs/codebooks/`).*

**A note on the figures.** `[measured]` means this document re-counted the
figure from the live file with `csv.reader` on 2026-09-02, streaming the whole
file. `[from the record]` means it was taken from a build log, docstring or ADR
without independent measurement. Where a doc and the data disagreed, the
measurement won; the disagreements are listed at the end.

---

## Why this is dataset 13 and not "infrastructure"

Cedar grew dataset-first. Each collection learned to recognise Native entities
on its own, and the shared spine arrived afterwards to reconcile what they had
each already decided. The symptoms were all over the repository: 42 tables
under 75% keyed; three ANCSA corporations carrying "federally recognized"
because one harvester resolved on its own; a CAGE alias equating two distinct
Delaware sovereigns because an alias layer was fed without review; `deals` able
to name only one Native party because nothing required it to speak a shared
many-to-many shape.

Every one of those is the same defect: **twelve datasets each doing their own
identification and not talking to each other.**

ADR-009 (2026-09-01) made the entity layer a first-class dataset with a grain,
a contract, a readiness status and a runbook, exactly like the other twelve.
Three consequences with teeth:

1. **Consumption, not re-derivation.** A dataset does not resolve entities. It
   attaches to `cedar_uid` through the identity layer, and where it cannot, it
   records a *candidate* — it does not invent a local answer.
2. **Readiness is capped by the hub.** A spoke cannot be more READY on identity
   than the hub it stands on.
3. **The shared shapes live in the hub.** Multi-party bridges at
   `(record, cedar_uid, role)`, ownership-change events with validity
   intervals, alias history, handle history. Twelve local implementations of
   many-to-many is how `nagpra` ended up correct and `deals` ended up singular.

What this does *not* mean: the hub does not absorb domain tables. Gaming
facilities stay in gaming. It owns *identity and the relationships between
identities* — who exists, what they are called, what they are, who owns whom,
and when each of those was true.

---

## 1. Sources

The spine is assembled from public registers, each of which is authoritative
about a different class of entity. No single source enumerates "Native
entities"; the class list is the reason the spine exists.

| class | count | source |
|---|---:|---|
| Federally recognized tribe | 349 | Interior's annual *Federally Recognized Indian Tribes* notice in the Federal Register (91 FR 4102, 2026-01-30) |
| Federally recognized Alaska Native Village | 228 | the same FR notice |
| Native Hawaiian Organization | 210 | DOI NHO notification roster |
| BIE School | 185 | Bureau of Indian Education school register |
| Alaska Native Village Corporation | 173 | ANCSA corporate registers, ANCSA Regional Association portal |
| State-recognized tribe | 64 | state statutes and state recognition registers |
| Native Community Development Financial Institution | 64 | CDFI Fund certified-institution list |
| Intertribal Organization | 56 | organisational self-publication, IRS BMF |
| Individually Native-owned business | 45 | Cedar rulings — see `native-owned-businesses` |
| Urban Indian Organization | 43 | IHS UIO register |
| Tribal College or University | 37 | AIHEC / NCES / IPEDS |
| Federal-level self-governance consortium | 29 | ISDEAA Title IV / V compact records |
| Native Financial Institution | 29 | CDFI Fund and Treasury registers |
| Federal-level constituency entity | 22 | FR notice parentheticals and constituency filings |
| Alaska Native Regional Corporation | 12 | ANCSA §7 |
| ANCSA Group Corporation | 6 | ANCSA §14(h)(3) |
| State-level constituency entity | 3 | state records |

[measured — 1,555 rows, `entity_class` distribution above]

Identifiers attached to those entities come from **SAM and FPDS** (UEI, CAGE),
the **IRS Business Master File** (EIN), and **parent-published subsidiary
disclosures**, including ANCSA audited filings under **Alaska Statute
45.55.139**, whose *Principles of Consolidation* note enumerates subsidiaries
by legal name.

### What was deliberately not used

- **The CICD / lineage-A integer scheme is retired as an identity** (see §4).
- **A SAM socio-economic flag is not evidence of class.** It is
  self-certification: Goldbelt Raven, an ANC subsidiary, certifies
  `alaskanNativeCorporationOwnedFirm = NO`, and SAM's
  `native_hawaiian_organization_owned_firm` means owned *by* an NHO, not that
  the firm *is* one — two for-profit LLCs carry it. [from the record]
- **NTEE codes are never used to establish Native status.** See `nonprofits`.
- **DUNS / D&B fields are held internally and never redistributed.**
- **Sources whose terms forbid reuse are excluded by every route** — Colville,
  CTUIR/Umatilla, Yakama, Chickasaw, NANA/Akima, Southern Ute, Forest County
  Potawatomi, and Navajo's NBOA directory. See §5.

---

## 2. How the rows were made

**The spine.** `code/01_build_entity_spine.py` builds
`data/spine/cedar_entity_spine.csv` (1,555 rows, 44 columns) from the canonical
tribe table, then class harvesters append: `code/05` and `code/591` / `code/592`
for the NHO, TCU, CDFI and BIE populations (`docs/NHO_SPINE_MERGE_LOG.md`,
`docs/TCU_CDFI_BUILD_LOG.md`, `docs/BIE_UIO_BUILD_LOG.md`).

**The permanent identity.** `code/503_identity.py mint` writes
`data/spine/cedar_identity_register.csv` — 1,555 rows, one per entity —
and `503_identity.py stamp` materialises `cedar_uid` onto every dataset.

**The identifier ledger.** `data/clean/cedar_identifier_ledger_final.csv`,
**20,577 rows** [measured], one row per `(identifier_type, identifier,
tribe_id)` with a tier and a method. It is a long table, not a wide one, on
purpose: adding a new identifier type — a Washington UBI, an NIGC id, a tribal
charter number — requires a new `identifier_type` value and a tier rationale,
not a schema change.

**Aliases.** `data/clean/entity_aliases.csv`, **6,298 rows** [measured], typed:
`common` 2,904 · `full_form_federal_filing` 1,799 · `legal` 873 · `shortened`
227 · `former_legal` 168 · `acronym` 143 · `brand` 104 · `diacritic_folded` 57
· `source_specific` 23.

**Recognition history.** `data/clean/federal_recognition_roster.csv`, **17,058
rows** (the FR list as published, 1995→, one row per entity per edition), and
`federal_recognition_events.csv`, **366 events**: `RENAMED` 319 · `ADDED` 35 ·
`REMOVED` 11 · `RESTORED` 1. [measured] Two build logs cover this and neither
supersedes the other — `RECOGNITION_HISTORY_LOG.md` is the parsing method,
`RECOGNITION_HISTORY_BUILD_LOG.md` is the verification and defect record.

**Hierarchy.** `data/clean/entity_hierarchy.csv`, 952 edges [measured], plus
`fpds_uei_edges.csv` for declared parent/child UEI relationships and shard E's
482 ANC subsidiary edges (404 at depth 1, 78 at depth 2, **355 of them from
audited filings**).

**The assertion layer.** `code/510_assertions.py` records who asserted each
fact, with evidence lineage. `data/spine/cedar_source_registry.csv` (17
sources) and `cedar_resolution_rules.csv` (9 ordered rules) ship as data rather
than as code.

**Corrections.** `data/clean/cedar_correction_register.csv`, 178 rows
[measured]. A correction is a row, not an overwrite;
`code/354_correction_register.py --apply` propagates a ruling to every stale
table in one pass.

**Rulings.** `code/124_apply_rulings_in_place.py` is the only correct tool for
importing an owner ruling. A ruling is the only promotion path above tier A,
and an upsert must never overwrite one.

---

## 3. Identity, in detail

This is the dataset whose *subject* is identity, so the identity rules are not
background here — they are the product.

### `cedar_uid` is the identity. The handle is an attribute.

```
CE-1A7K3-MQ
│  │     └─ TWO check characters, from two independent weightings
│  └─ 5 chars, Crockford base32 (I, L, O and U are NOT in the alphabet)
└─ namespace
```

**It encodes nothing, on purpose.** Everything about an entity can change
except its identity. A state-recognized tribe that wins federal recognition
changes class and changes handle (`TRBS-…` → `TRBF-…`) — **`cedar_uid` does
not**, so any time series keyed on the uid survives the event unbroken. An
identifier that encodes class must be rewritten the day the class changes, and
rewriting an identity is the one unforgivable act in an identity system.

**The check characters are not decoration.** `O`, `I`, `L` and `U` cannot
appear, so the `BANN 0 YEEL KON` class of transcription error is
*unrepresentable*, not merely detectable. The two trailing characters come from
one linear and one quadratic weighting, so an error in the null space of the
first is caught by the second:

| error class | one check char | two check chars |
|---|---:|---:|
| single substitution | 95.5% (382/400) | **100% (1000/1000)** |
| adjacent transposition | partial | **100% (579/579)** |

[from the record — `503_identity.py` self-test asserts these on every run]

The single-character version was built first and replaced the same hour, before
anything shipped. 95.5% is what a mod-32 character gives you and it is not good
enough for an identifier a customer transcribes. **The reason to decide it then
was that it was free then and expensive later.**

### The reclassification rule

1. **`cedar_uid` never changes.** Not for any reason. Ever.
2. The **old handle is retired to an alias** with `valid_to` set. It keeps
   resolving — historical filings use it.
3. A **new handle is minted** in the new class, with `valid_from`.
4. `entity_class` and `class_since_basis` are updated with the citation (FR
   notice, court order) in the basis.
5. **No row in any dataset is rewritten.** They carry `cedar_uid`; they are
   already correct.

A uid is **never reused**, even after an entity is retired.

**This was policy the code did not implement until 2026-08-30**, and that gap
is worth recording because it is the kind of defect an identity system cannot
detect after the fact. `503_identity.py phase_mint` keyed its existing-uid
lookup on the *handle*, so a reclassification missed, **minted a second uid for
an entity that already had one**, and dropped the old handle from a register
documented as append-only. A buyer who had joined on a handle would have lost
their historical rows with no way to discover it.

`data/spine/cedar_handle_history.csv` now retains every binding ever issued
(`handle, cedar_uid, valid_from, valid_to, status, change_reason,
recorded_date`), the history is read *first* so the current register can only
confirm it, and **a retired handle pointing at a different entity raises
`HandleReuse`** — not a warning, because a reused handle resolves to the wrong
entity in every downstream join and nothing later can detect it.
`503_identity.py verify` checks H1–H5; `62_no_regression_check.py` carries
`handles_reused_or_double_bound` (MUST_BE_ZERO) and
`sem_entities_uid_reassigned` (MUST_BE_ZERO).

### A compound handle is not a broken one

`AKNF-MTLKTL-00-TLNGHD` and `CNSF-MINNCH-LL` are canonical. The apparent "base"
`AKNF-MTLKTL-00` is **not in the spine at all**. Stripping the suffix to make a
join work turns 21,693 joinable rows into unjoinable ones while looking like a
normalisation. [from the record]

### The hub model

```
external identifiers  ─┐
(UEI, CAGE, EIN, UBI)  │
                       ▼
  sub-hub  ────────►  ENTITY  ◄────────  collection rows
(facility, property,  (cedar_uid)        (contracts, grants,
 docket, EIN filer)                       filings, deals …)
```

**Sub-hubs exist where a thing is complex enough to deserve its own record and
its own children.** A casino is the worked example: a facility has capacity
observations, employment observations, property locations, financing events and
licences of its own, *and* it belongs to an entity. Flattening it onto the
entity would lose the level at which most gaming facts are actually true.
Implemented sub-hubs: `facility_id`, `property_id` (itself parent to
`location_observation_id`), `np_ein_entity_hub`, and the FERC docket filer
layer.

**Hierarchy is a relationship, not an identity.** Corporate parentage is
genuinely ambiguous — a subsidiary is sometimes operated as a parent, ANCSA
corporations invert the usual shape, and the same firm appears as both in
different sources. So parentage lives in `entity_hierarchy` /
`parent_entity_id` as a typed, evidenced, revisable claim. **If you want to
change an entity's id because its ownership changed, you want an edge.**

### Tiers

| tier | means | ledger rows |
|---|---|---:|
| **A** | an identifier, or a human ruling | 2,286 |
| **B** | a strong name method with an independent corroborator, or inheritance from a tier-A parent | 5,443 |
| **C** | a weak method held as a candidate, not published as a fact | 12,380 |
| **X** | **refused** — a negative ruling, never a confirmation | 468 |

[measured]

Top attribution methods: `unmatched` 9,407 · `need_v6` 4,650 · `cluster_v3`
2,007 · `cross_dataset_propagation:contracting` 1,028 · `bgov_manual` 837 ·
`elijah_ruling` 547 · `hand` 522 · `agent_research_two_leg` 506. [measured]

`tier_A_ruled` — tier-A rows whose method is in the RULED set defined in
`code/62_no_regression_check.py` — is a **different metric from tier A** and
the distinction is the whole point of it. Computing that definition on the live
file gives **1,676**, against a tier-A total of 2,286, with
`tierA_without_entity = 0`. [measured] Quoting the tier-A total as "ruled"
erases the distinction.

By identifier type the ledger is **UEI 13,507 · CAGE 5,966 · EIN 1,104**,
across **808 distinct entities**, with `is_authority = YES` on 1,892 rows and
121 rows carrying an `exclusion_id`. [measured]

### What may be published, and it is a separate table on purpose

**`cedar_publishable_identifiers.csv` — 1,577 rows: CAGE 878 + UEI 699, with
`confidence_tier = A` on every single row.** [measured]

**EIN is deliberately excluded.** *"An EIN identifies a filer and reaches
further into an organization's affairs than a procurement id does."*

**Publish from that table. Do not re-derive a publishable set by filtering the
full ledger** — the filter *is* the policy, and a second copy of it will drift.

A further **42 crosswalk rows are hard-withheld** under
`cedar_domain.may_publish_individual_native_field`: for a firm whose legal name
IS a person's name, publishing the identifier publishes the person **by one
hop**, through SAM's public entity search. **And a digest is not a fix** —
SAM's entity space is enumerable, so a hashed UEI is reversible by hashing
every UEI and comparing. 1,009 `ENTITY_MASTER` and 344 legacy-integer crosswalk
rows are marked non-publishing as internal keys.

### The other identity artefacts, measured

| table | rows | note |
|---|---:|---|
| `cedar_ruling_ledger_consolidated.csv` | **43,321** over 59 source files | `verdict_kind` ENTITY 17,524 · CLASS 12,488 · NEGATIVE 10,344 · HOLD 2,965; `status` SETTLED 40,427 / **CONFLICT_NOT_APPLIED 2,894**; tier X on 10,106 |
| `cross_dataset_ruling_map.csv` | **22,936** | **federal funding is the largest consumer at 9,436**; channels IDENTITY 14,939 / EXCLUSION 7,997 |
| `data/spine/cedar_exclusion_rulings.csv` | 123 | all UEI; evidenced by CAGE registry lookup 76, narrative note 22, company website 18, OpenCorporates 3, archived site 3, GAO decision 1 |
| `cedar_entity_identity_crosswalk.csv` | **10,107** | schemes UEI 4,074 · CAGE 2,905 · EIN 1,088 · ENTITY_MASTER 1,009 · CICD_NEID 687 · LEGACY_ASSISTANCE_INT 344. Status APPLIED 9,432 · **PROPOSED_NOT_APPLIED 344** · **NEGATIVE_RULING_DO_NOT_ATTRIBUTE 331** |
| `cedar_identifier_ledger_tiered.csv` | 19,232 | A 1,575 · B 4,793 · C 12,721 · X 143. **19,232 is the documented signature of the unsafe `09` rebuild that destroyed 1,327 rows.** It ships as internal-by-decision |
| identifier graph | 115,471 nodes / 46,820 edges | nodes DUNS 73,442 · UEI 29,212 · CAGE 9,903 · EIN 2,914; 149 blocked; **874 flagged `one_to_many_defect`**. Edges ATTRIBUTION 18,307 · IDENTITY 15,608 · **BLOCK 12,905** |

[measured]

### Relationships are typed, and the typing is worth $57 billion

`entity_relationships.csv` — **2,292 rows** [measured]: `owned_by` 1,462 ·
`associated_with_region` 391 · `affiliated_with` 148 · `brand_of` 106 ·
`village_corporation_for` 77 · `operated_by` 56 · `chartered_by` 30 ·
`constituent_band_of` 22. Tiers A 2,121 / B 169 / C 2; 2,271 direct, 21
inferred.

**The measured size of the thing this prevents: 174 non-ownership edges sit on
entities holding $57,043,179,871 of prime obligations that a flat parent column
would have rolled upward** — $32.87B along `associated_with_region`, $23.91B
along `village_corporation_for`, $264M along `constituent_band_of`. **Zero
dollars travel along any of them now, structurally**, because roll-up is
defined as the sum over ownership-bearing edges only
(`cedar_domain.bears_ownership()`).

### The spiderweb counting trap

`fpds_uei_edges.csv` holds 5,167 rows and **that is not the ownership figure**:
`parent_uei` 2,726 + `ultimate_parent_uei` 1,891 = **4,617 ownership edges over
2,725 registrants**, while `prime_to_sub` 550 is a *contracting* relationship
and 99 rows carry `blocklisted_parent = 1`. **Quoting 5,167 books 550
subcontracts as corporate parentage.**

And the caveat that makes the spine necessary at all: **the declared
highest-level owner in a federal database is the highest *incorporated* owner —
Ho-Chunk, Inc., not the Winnebago Tribe of Nebraska. That last hop is Cedar's
own edge, and no federal database supplies it.**

---

## 4. Decisions that shaped the data

### An identifier beats every name method

Shard E linked seven ASRC subsidiaries — **$5.43B, none of them sharing a
single token with "Arctic Slope"** — through published CAGE codes. That is why
the parent's own subsidiary list is the preferred route and why an ANCSA
corporation's audited filing is worth more than any matcher.

**But an identifier is not a link.** The exactness of the KEY says nothing
about the correctness of the LINK. An EIN is an exact string and 821 EIN rows
still sit at tier B. The worked failure: a UNITED WAY chapter in Wisconsin
attributed at tier A to United Auburn Indian Community in California, because
the *key* was exact.

**And a join key can be poison.** `fpds_uei_cage_map.csv` carries the literal
string `NAN` in `cage_code` on **2,196 rows across 2,193 distinct UEIs** — a
pandas null stringified on export. Joining on `cage_code` without excluding it
fuses 2,193 unrelated entities into one. Excluding it, the route is near-exact:
of 6,843 real CAGE codes only 15 map to more than one UEI and none maps to more
than two. [from the record]

### An entity whose distinctive token set is generic may not win a name-only match

Three independent defects on 2026-09-01 were one defect: 104 single-token
`brand` aliases (`cultural` → Southern Ute, `indigenous` → Delaware Nation,
`colorado`, `broadband`, `advantage`); `UMATILLA ELECTRIC COOPERATIVE` →
Umatilla Tribe, `SENECA HOSE CO NO 1` → Seneca Nation, `TAOS VOLUNTEER FIRE
DEPARTMENT` → Pueblo of Taos; and 53 containment links in
`np_ein_entity_hub.csv`, 41 of them onto *Council Native Corporation*.

**A denylist is not the fix.** `cedar_domain.NAME_TRAPS` holds 51 words and did
not hold `council`, `health` or `native`. A denylist refuses only a word
somebody already listed: it catches `FOND DU LAC YACHT CLUB` and never
`ENVISION GREATER FOND DU LAC`. **Write the structural predicate, then use a
denylist for named exceptions.**

**State agreement is not the fix either.** Tested on the same case: it kills all
five `Council` links (Philadelphia, Brooklyn — none in Alaska) and **none** of
the `Native Health` links, because Winslow AZ, Fort Defiance AZ and Native
Health are all in Arizona. Geography is a strong corroborator and a poor gate.

### Flagging is not a claim that the organisation is not Native

Among the 53 refused links: Cook Inlet Tribal Council, International Indian
Treaty Council, National Indian Council on Aging, Indian Action Council of
Northwestern California, Inter-Tribal Council of Louisiana. Every one is a
genuine Native organisation. **The refusal says only: this is not THAT
entity.** They are now correctly unkeyed — `record_scope = unresolved` — and
several plainly deserve a spine row of their own. The repair **flags and never
deletes**: a deleted row asserts nothing; a flagged row says what was refused
and why, and can be reversed.

### `INDIAN` is ambiguous and Cedar is only ever about one meaning

Caught in the same 53: `COUNCIL OF INDIAN ORTHODOX CHURCHES INC` (the
Malankara Orthodox Church), `NATIONAL COUNCIL OF ASIAN INDIAN ASSOCIATIONS`,
`COUNCIL FOR WEST INDIAN PLANNING & DEVELOPMENT`, `CULTURAL COUNCIL OF INDIAN
RIVER COUNTY`, `INDIAN ORCHARD CITIZENS COUNCIL`. **Treat the token as no
signal at all** unless something else in the record carries the meaning.

### The residue rule, not equality and not containment

When a filed name is compared to a spine entity, the question is not "do they
share tokens" but *"is every distinctive word in the filed name accounted for
by that entity's own official name?"* Take the union of `canonical_name`,
`fr_official_name` and aliases, subtract it from the filed name's distinctive
tokens, and the **residue** decides: empty or a place/spelling variant →
accept; an institution form (`SCHOOL`, `AUTHORITY`, `COLLEGE`, `UTILITY`,
`HOUSING`) or four-plus distinctive words → hold.

Equality fails because Cedar's canonical names are deliberately short
(`Rosebud` for the Rosebud Sioux Tribe) — requiring it holds 280 correct rows
worth $23.4B. Containment fails because it accepts `TURTLE MOUNTAIN COMMUNITY
COLLEGE` as the Turtle Mountain Band and `NAVAJO TRIBAL UTILITY AUTHORITY` as
the Navajo Nation. A tribal college and a utility are real entities and they
are not the nation.

**The residue cap is empirical.** Over 281 accepts the largest residue on a
correct one is three (`NAMBE PUEBLO GOVERNOR'S OFFICE`), and exactly one wrong
accept carried no institution-form word: `LEECH LAKE BAND OF OJIBWE NATURAL
WILD RICE`, residue `NATURAL, OJIBWE, RICE, WILD`. No denylist could have
caught it — `RICE` is not an organisational form — and the structural fact that
it adds four distinctive words is what separates it.

### An alias needs three independent observations

One Federal Register notice spelling a name a particular way is a typesetter.
Two is often the same notice reissued. **Three or more independent notices is
corroboration.** The calibration is empirical: an earlier recognition-alias
pass was rejected on review at **76 of 228 proposals (33%)** — far too high to
auto-apply at n=1. Applied to 1,049 NAGPRA alias proposals: 211 accept, 168
hold, 670 refuse.

### A declared parent UEI outranks a name, and 20 observations is the floor

`fpds_uei_edges.csv` carries parent/child relationships **the registrant filed
about itself** — identifier evidence, already on disk, no browser needed. Two
thresholds make it usable:

- **An edge observed 20+ times is ownership.** Below that it is a joint venture
  or a co-award, and a JV genuinely has two parents. Measured: all 72 ledger
  rows whose declared parent disagrees on a sub-20 edge are JVs (*WHH Nisqually
  Federal Services* declares TDX Quality exactly **once**), while every real
  ownership case is observed 100+ times.
- **The parent's tier does not transfer.** A link resolved through a tier-A
  parent is proposed at **tier B**. A tier is inherited from the source row,
  never assigned by the consumer.

### When a declared parent contradicts an attribution, suspect the PARENT row

The most valuable rule in the set and the least obvious. Sweeping every tier
A/B UEI against its declared parent produced **129 contradictions on $2.82B** —
which reads like 129 wrong attributions and is not:

- **54 rows, $2.39B — the PARENT row is the defect.** Every Bowhead subsidiary
  is correctly keyed to `ANVC-KPVKPT-00`, Ukpeaġvik Iñupiat Corporation, while
  **the corporation's own UEI was keyed to the Native Village**. The ANCSA
  ownership ruling and `cedar_domain.village_government_owns_an_anc()` (always
  `False`) say that link cannot exist. One bad parent row makes 54 good child
  rows look wrong. Same shape at Olgoonik/Wainwright and St. George
  Tanaq/Pribilof — the known
  `ALASKA_VILLAGE_GOVERNMENT_VS_VILLAGE_CORPORATION` family, 334 defects,
  $24.52B, reached by an independent route.
- **72 rows, $0.40B — the JV floor.** Ledger stands.
- **3 rows, $0.03B — genuine.**

**A contradiction sweep must classify before it acts.** Acting on the raw 129
would have repointed 126 correct rows to chase 3 wrong ones.

### The ANCSA rule: a village government does not own a village corporation

ANCSA created village *corporations* as separate legal persons from the
federally recognised village *governments*. Cedar encodes this as a hard
predicate rather than a heuristic, because the two carry near-identical names
and the confusion is worth $24.52B across 334 defects.

### ANCs and NHOs are the easy class, for two structural reasons

**The incentive runs toward self-declaration.** An NHO or ANC subsidiary gets
sole-source and 8(a) advantages *by being one* and must say so to claim them.
Self-declaration is normally weak evidence; here the incentive structure makes
it strong, and silence is informative.

**The names carry language.** Ukpeaġvik, Kuukpik, Olgoonik, Tikigaq, Afognak,
Koniag, Chenega, Calista, Ahtna, Sealaska; Papa Ola Lokahi, Hui Mālama Ola Nā
ʻŌiwi, Ke Ola Mamo, Hoʻōla Lāhui Hawaiʻi. **Iñupiaq, Yupʻik, Alutiiq, Tlingit
and Hawaiian orthography — the ʻokina, the macron, `ġ`, `ḵ` — is a positive
identifying signal**, and one no generic-token guard would find. It cuts the
other way too: a subsidiary named BROADLEAF or VISTRONIX carries no signal at
all, which is exactly why the parent's own subsidiary list is the route.

### The name-collision ladder, in the owner's order

The exposure is larger than the famous pairs. Measured in the register:
**Cherokee 45 entities** — three federally recognised tribes (Cherokee Nation,
Eastern Band, United Keetoowah Band), six state-recognized Cherokee groups in
Alabama and Georgia, and ~30 businesses named `Cherokee <something>`. Creek 20,
Choctaw 11, Seminole 2, Ho-Chunk 2 (Ho-Chunk Inc is the **Winnebago Tribe of
Nebraska's** holding company).

**A token match on `Cherokee` is not weak evidence. It is no evidence.** The
procedure, stopping at the first rung that answers: (1) the address — state
alone separates most pairs and is already on the FPDS, SAM and 990 record;
(2) the organisation's own website stating its affiliation; (3) **search the
address itself** and see what else is there — a shared address with a known
entity of the family is strong, an address on the reservation close to
decisive; (4) CAGE as a *pointer* to the next name to look up, never as an
answer; (5) a news article; (6) **stop** — unresolved is a legitimate outcome
and a wrong key is worse than no key.

### The CICD / lineage-A integer scheme was retired on 2026-09-01

`code/843_retire_cicd_scheme.py`. The scheme was a Stata do-file integer
(`fed_funding_do_file_corrtd.do`) reconciled onto Cedar identity by `code/152`
and carried since as `same_as_legacy_cicd`. Its reconciliation used a
gov-class distinctive-token match, and that matcher:

- **merged two federally recognised tribes** — legacy `347`, *United Keetoowah
  Band of Cherokee*, onto **Cherokee Nation**, on the token `Cherokee`:
  **820 rows, $181,881,441.37**;
- **filed county housing authorities as tribes** — legacy `344`, *Tuscarawas
  Metropolitan Housing* (Ohio), as `tuscarora tribe`; legacy `186`, *Montgomery
  County Housing Authority*, as Forest County, on the token `COUNTY`.

**Retirement was safe and was measured before anything was written.** Of the
365,535 rows keyed by a CICD integer, 365,491 (99.99%) already carried a
`cedar_uid`; the rows with an integer and no uid also had no handle, so
dropping the integer cost exactly **44 rows of identity — all 44 the county
housing authorities**, which are not Native entities and should never have been
keyed to one. This was not a migration: the identity was already Cedar's, and
the CICD column was a second, worse answer sitting beside the right one.

Two columns named after the dead scheme held facts worth keeping and were
renamed rather than dropped: `tribe_id_scheme_resolved` → **`attribution_status`**
and `tribe_id_scheme_resolved_basis` → **`attribution_basis`**.

**The crosswalk itself was kept on disk and moved out of the shipped tree**, to
`data/spine/legacy/`. Deleting the scaffolding after the building stands would
make the rebuild (C8) unreproducible.

One misattribution repaired in the same pass is explicitly **not** claimed as
CICD's fault: 72 rows of *Sonoma County Indian Health Project* credited to
Forest County Potawatomi arrived as a stray handle, not through the integer
scheme, and are recorded as their own defect.

### Every fact in Cedar rests on exactly one source, and that was measured

The assertion layer works and, when first run, had nothing to arbitrate. Across
**8,975 single-valued facts: 0** had a second source, **0** disagreed, and
**2** had more than one independent evidence family. [from the record]

**Do not read that as "the data agrees with itself."** It means nothing had
ever checked it.

The first attempt at a second source is instructive. Harvesting the Federal
Register roster directly matched 565 of 575 entries to the spine — and the
corroborated count **stayed at 2**, correctly, because *a copy of the FR
sitting in the spine and the FR itself are the same evidence family*. **Copying
a source into your own table does not corroborate it.** A warehouse without
lineage would have booked 565 new confirmations.

`unattributed_legacy` assertions were 11,676 of 23,310 (50.1%) and are now
**5,428 of 34,615 (15.7%)** [from the record, re-measured 2026-09-01], so "half
the store carries no evidence" is no longer true.

---

## 5. What was excluded on purpose

**Terms of use.** Sources marked `TERMS_STATED_RESTRICTIVE` are excluded by
**every** route — the publisher's page, its WordPress media API, the Wayback
Machine, and any harmonised derivative. Harmonising changes what Cedar
publishes; it does not change what Cedar was allowed to take.

Named: **Confederated Colville**, **CTUIR / Umatilla**, **Yakama**,
**Chickasaw** (terms name company directories specifically, ~622 firms),
**NANA / Akima** (forbids automated use, scraping and aggregation — ~55
operating companies carrying UEI, CAGE, DUNS, NAICS and 8(a) status, the single
highest-value refusal in the project; a sitemap enumeration was **stopped
mid-run** when the terms were read), **Southern Ute** (27 firms), **Forest
County Potawatomi** (18 firms), and Navajo's NBOA directory. Each is recorded
with the quote that justifies it. **Asking is the route back in; a cleverer
scrape is not.**

**Proprietary identifiers are held internally and never published.** DUNS and
D&B fields attach to every base award dated before 2022-04-04.

---

## 6. Known limits

- **`canonical_name` in the register is a colloquial stub, not a legal name.**
  `Little River`, `Table Mountain`, `Pedro Bay`, `Asa'carsarmiut`. **536
  register entities have their legally operative Federal Register name on disk
  in `federal_recognition_roster.csv`, keyed by `cedar_uid`, and 509 of the 536
  differ from what the register shows** (`Noatak` → *Native Village of
  Noatak*). A buyer searching for *Little River Band of Ottawa Indians* finds
  nothing. It is one join away and has not been done. [from the record]

- **This drift reaches downstream.** 341,486 of 548,980 funding rows (62.2%,
  $94.4B) carry a `canonical_name` that disagrees with the register's name for
  that row's own `cedar_uid`. Most are harmless (`navajo nation tribal
  government, the` vs `Navajo`); some are the wrong subject entirely
  (`blackfeet community college` → `Blackfeet`). **The attribution is correct;
  the free-text column is not.** Join on `cedar_uid`, never on
  `canonical_name`. [from the record]

- **Two register columns carry no information.** `minted` is `2026-09-01` on
  all 1,555 rows — it records the register *rebuild*, not when the entity was
  minted, so the column means the opposite of what its name promises.
  `register_status` is `active` on all 1,555. [from the record]

- **`entity_aliases.alias_id` is not unique** — 1 duplicate of 6,298, a blank.
  It is a declared primary key the data currently breaks, and it is the one
  open contract violation in this dataset. [measured — 6,296 of 6,298 non-blank]

- **`entity.is_federally_recognized` has no negative case** in the assertion
  layer, so the predicate has never been tested against a refutation.
  [from the record]

- **`gaming_source_claims` contributes 9 assertions and still has no
  `cedar_uid`** across 113 rows. [from the record]

- **1,279 of 1,555 spine rows (82.3%) carry no `verification_route` and no
  `evidence_tier`.** [measured — spine `evidence_tier`: blank 1,279 · C 179 ·
  A 81 · B 16] The numerator has not moved; the denominator grew.

- **Corroboration is effectively absent, and it is measured rather than
  assumed.** `n_independent_families` on resolved facts: **1 → 21,762 · 0 →
  12,509 · 2 → only 4.** [measured] `entity.city` is populated on **229 of
  1,555 rows (14.7%)** and is therefore effectively single-sourced.

- **DISCOVERY DRIFT, not refresh lag, is this dataset's real failure mode.**
  *"A refresh that runs too slowly gives you stale numbers, which every reader
  can see; a discovery pass that runs too slowly gives you confidently wrong
  numbers, which no reader can see, because a missing entity leaves no hole in
  the table."* Measured by `code/276_measure_discovery_gap.py` — the share of
  rows a UEI-only pull would lose: FY2015 0.23% · FY2019 6.24% · FY2023 7.49% ·
  FY2024 8.74% · **FY2025 12.66%, up 3.9 points in one year** against a prior
  drift of about 1 point a year. And **9,719 entities carry a Native
  business-type flag in FPDS prime data that the identifier route has never
  seen — 76.9% of all flagged entities, $70.96B.** Discovery is a **quarterly**
  job and is a different job from a refresh.

- **An open, measurable defect this paper found, recorded in no document.** The
  United Keetoowah Band / Cherokee Nation merge is **still live in
  `federal_funding_transactions.csv`**: **820 rows carrying `cedar_uid =
  CE-00134-BX` (Cherokee Nation) with `canonical_name = "united keetoowah band
  of cherokee"`, summing to $181,881,441.37 exactly**, FY2008 onward.
  [measured] The register already holds UKB separately as `CE-001BS-HA` /
  `TRBF-UKEETW-00`, and the crosswalk was corrected on 2026-09-01 — **but
  `code/843` did not repoint the transaction rows.** A further 407
  Keetoowah-named rows *are* correctly keyed. **Any per-entity cut of federal
  funding today over-credits Cherokee Nation and zeroes UKB by that amount.**
  The register half of the defect is fixed; the data half is not.

- **`code/503`'s zero-loss guarantee was measured against a 1,536-row spine**
  and has not been re-measured against the 19 entities added since.

- **The spine size moves, sometimes mid-session.** It went 1,536 → 1,555 while
  three workstreams were running on 2026-09-01. **Never quote the spine size
  from a document**; read `data/spine/cedar_identity_register.csv`, which is
  the one table git tracks.

- **`data/spine/cedar_entity_spine.csv` is NOT in git.** The register is. A
  rebuild of the spine from a stale upstream is the largest single destructive
  risk in the project — see §7.

---

## 7. Refresh

| source | cadence | Cedar holds | state |
|---|---|---|---|
| Interior's *Federally Recognized Indian Tribes* notice | **annual, late January** (91 FR 4102 was 2026-01-30) | 2026-01-30 | current; source has not published again |
| DOI NHO roster · IHS UIO register · TCU and Native CDFI rosters | irregular — DOI posts NHO notifications as filed; the TCU and CDFI rosters change a few times a year | 2026-08-05 | source edge not established |
| Owner adjudications | event-driven | — | closed by design |

[measured — `docs/REFRESH_CADENCE.json`, regenerated 2026-09-02]

**Trigger the spine rebuild from the notice, not from a timer.** The daily
Federal Register pull is what sees it.

**What breaks if the recognition notice is not picked up:** everything. A newly
recognised tribe has no spine row, so every dataset that meets it records an
`unresolved` scope, and a renamed nation's filings stop matching.

### The rebuild path, and the hazard in it

`py -3 code/build.py plan _entity_layer` prints the ordered
rebuilds-then-enrichers; `run _entity_layer --execute` runs it.
`code/cedar_pipeline.NEVER_RUN` names what may not be run at all.

`01_build_entity_spine.py` and `09_import_rulings.py` were on that list until
2026-09-01 and their history is the reason the ordering discipline exists:

- `01` built from `canonical_tribe_table.csv` alone (687 rows, 12 columns) over
  a live hub of 1,555 rows and 44 columns, **dropping 868 entities and 32
  columns including `cedar_uid`**.
- `09` read `cedar_identifier_ledger_tiered.csv` (19,232 rows) and wrote
  `cedar_identifier_ledger_final.csv` (20,577). Those are not the same table —
  `_final` is `_tiered` plus 1,345 rows later scripts appended, **18 of them
  tier-A owner adjudications, the one class of fact that cannot be
  re-derived** — and a hardcoded 17-column header dropped five more columns.

Both came off the list only after they were rewritten to write through
`merge_table` (which cannot drop a row and raises rather than drop a column)
**and** after `code/812_c8_rebuild_proof.py` proved by dry run against the live
tables that each reproduces the census with zero rows and zero columns lost:
`01` 1,555 → 1,555 rows, 44 → 44 columns, 512 drift cells held back for review;
`09` 20,577 → 20,577 rows, 22 → 22 columns.

**The order of that is the point.** The C8 gate could have been turned green at
any point in the previous month by deleting three dictionary entries, and doing
so would have made `build.py run _entity_layer --execute` genuinely delete 868
of 1,555 entities. The guard came off after the proof, not before it.

`124_apply_rulings_in_place.py` must run after **any** refresh. An upsert must
never overwrite a human ruling.

---

## Stale claims found while writing this

- **`docs/DOC_CONTRADICTIONS_2026-08-26.md` "Ground truth" row for the
  identifier ledger** gives `20,577 rows · A 2,286 · X 468 · tier_A_ruled
  1,676` and omits B and C. Measured 2026-09-02: **20,577 · A 2,286 · B 5,443 ·
  C 12,380 · X 468.** The register's own 2026-08-26 column (`20,559 · A 2,148 ·
  B 5,690 · C 12,524 · X 197`) and the identical figures in `START_HERE.md` are
  both dead.
- **`START_HERE.md` says the spine holds 1,310 entities in 16 classes.** It
  holds **1,555 in 17**. The contradictions register already caught this and
  `START_HERE` was not updated.
- **`START_HERE.md`'s "TWO IDENTIFIER SCHEMES IN `tribe_id`, worth $107.50B"
  section is now historical.** `code/843_retire_cicd_scheme.py` was applied:
  `federal_funding_transactions.csv` no longer carries `tribe_id` or
  `tribe_id_scheme` at all, and `tribe_id_scheme_resolved` has been renamed
  `attribution_status`. The warning is still worth reading for the *reason*;
  its instructions no longer apply to any live column.
- **`docs/DATASET_CONTRACTS.md` still lists `tribe_id` as a declared key on
  `federal_funding_transactions.csv`.** That column no longer exists. The
  contract file is generated (`code/512`) and was last generated 2026-09-01,
  before 843 was applied; regenerating it will fix this.
- **`docs/DATASET_READINESS.md` in `START_HERE.md` is quoted as "READY 2 / 13".**
  The scoreboard regenerated 2026-09-02 reads **READY 9 / 13**, with
  `_entity_layer` READY.
- **`docs/datasets/_entity_layer.md`, generated 2026-09-01, reports this
  collection BLOCKED** — 35 customer tables, C1 grain unstated on 6, C2 no
  validated primary key on 6, C3 10,985 duplicate rows. The scoreboard
  regenerated 2026-09-02 reports **READY, 35 tables, 35/35 grain, 35/35 keys,
  duplicates clean.** One day stale.
- **The same generated doc's coverage table is stale on four rows**:
  `cedar_ruling_ledger_consolidated.csv` 15,587 → measured **43,321**;
  `cross_dataset_ruling_map.csv` 7,507 → **22,936**;
  `cedar_identifier_graph_edges.csv` 46,051 → **46,820**;
  `foia_request_index.csv` 9,481 → **20,102**.
- **`code/62_no_regression_check.py` gates `identity_facts_legacy_only` in the
  wrong direction** — it sits under `MUST_NOT_FALL` and should be
  `MUST_NOT_RISE`. A metric that is supposed to shrink is currently protected
  against shrinking.

---

## Two rules that are easy to state and easy to break

**Never treat an absent negative as a negative.**
`entity.is_federally_recognized` asserts `yes` on the roster and asserts
**nothing** off it. Absence from the roster is not a refutation.

**Never re-mint a `cedar_uid`, never edit an assertion, never resolve a name
outside `503.resolve()`, and never run `01` or `09` casually.** The first three
corrupt identity silently; the fourth is the only one that announces itself,
and only if someone is watching the row count.
