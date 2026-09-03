# NEST — Native Enterprise Structures and Ties

*Built 2026-09-02 by workstream `nest`. Script:
`code/1072_tribally_owned_enterprises.py`. Collection id **`nest`**, the 14th
dataset. Every figure below is recomputable from the two tables and the staging
directory they name; nothing here is copied from a prior report.*

> **NEST — Native Enterprise Structures and Ties**
> Enterprise ownership and affiliation across tribes, Alaska Native
> corporations, Native Hawaiian organizations, and state-recognized Native
> entities.
> — the owner, 2026-09-02

---

## THE HEADLINE

**977 of 1,610 enterprises (60.7%) that a Native nation, ANCSA corporation or
NHO owns do not appear in federal contracting at all.**

That number is the reason the dataset exists. FPDS only ever sees the
enterprises that pursue federal work; a nation's propane utility, gas stations,
farm, radio station, casino management company and holding company are invisible
to it. 977 rows here are firms with a named owner, a named source and a
permanent Cedar identifier that no federal procurement record contains.

**Read it as a floor, not a point estimate.** The presence test is exact
normalised name OR published UEI OR published CAGE against 22,031 FPDS awardee
names, 19,475 UEIs and 6,843 CAGE codes. A name collision makes an enterprise
look *present*, so the error runs against the count.

| owner class | enterprises | absent from FPDS |
|---|---:|---:|
| Alaska Native corporation | 1,188 | 688 |
| Tribal government | 322 | 247 |
| Native Hawaiian organization | 100 | 42 |
| **total** | **1,610** | **977 (60.7%)** |

---

## WHAT THIS DATASET IS, AND WHAT IT IS NOT

It is **not** a bigger `native-owned-businesses`. It is a different relation.

| | `native-owned-businesses` | `nest` |
|---|---|---|
| what a row says | a nation **certified or listed** this firm | a nation **owns** this enterprise, or published a **tie** to it |
| relation published | `affiliated_with` | `owned_by` / `affiliated_with`, declared per row |
| scope gradient | down to `vendor_relationship` — no ownership claim at all | `tribally_owned_entity` / `parent_asserted_subsidiary` only |
| rows | 2,393 | 1,610 |

The two must never be merged. Flattening `native_owned_businesses`'
`identity_scope` gradient into an ownership claim is what
`docs/PUBLICATION_POLICY.md` refuses, and a firm on a list whose bar is
*shareholder descendant or spouse* is not a tribally owned firm.

**And it is not the constellation.** `data/clean/cedar_constellation_edges.csv`
(ADR-014) records **service** relationships — who serves a community, including
`registered_with` for a TERO-certified firm. NEST records **ownership and
corporate affiliation of enterprises**. A TERO-certified firm is a constellation
edge and is **not** a NEST row unless the nation also owns it. That file is
**read and never written** by this build, and where a NEST enterprise matches a
constellation edge its `edge_id` is carried in `constellation_edge_id` so the
corroboration is visible instead of the relationship being rebuilt under a
second name.

*Measured: the overlap is **1 row**.* Of 2,268 constellation from-sides that
carry no `cedar_uid`, exactly one (`Rolling Hills Clinic`) is also a NEST
enterprise. **That near-zero overlap is the evidence that the scope split is
real**: the constellation's unkeyed names are clinics, schools and service
organisations, and NEST's are operating companies. NEST therefore does *not*
close the constellation's 2,268-name backlog, and a pass that tries to should
know that before it starts.

---

## STRUCTURES **AND** TIES — two relations, declared per row

The name commits the dataset to two relations and the row has to say which it
is. **An affiliation recorded as ownership is the defect this dataset is most
exposed to.**

```
relation_class = ownership     1,512   the corporate chain
relation_class = affiliation      98   published, real, and NOT ownership
```

| relationship | n | class |
|---|---:|---|
| `subsidiary` | 749 | ownership |
| `wholly_owned` | 523 | ownership |
| `majority_owned` | 76 | ownership |
| `operating_company` | 35 | ownership |
| `holding_company` | 15 | ownership |
| `declared_suborganization` | 5 | ownership |
| `division` | 3 | ownership |
| `joint_venture` | 72 | **affiliation** |
| `shareholding_or_ancestry` | 4 | **affiliation** |

A joint venture genuinely has two parents (`ENTITY_MATCH_RULES` rule 11), so it
is never a subsidiary however the source files it. Sources write the same idea
half a dozen ways — `joint venture`, `joint_venture`, `holding company`, a
schema.org `subOrganization` — and anything the vocabulary does not recognise
lands in `relationship_as_recorded` and is classed **`affiliation`**, the weaker
reading, because guessing upward is the direction that fabricates.

---

## THE HIERARCHY IS THE PRODUCT

```
HUB       Winnebago Tribe of Nebraska        TRBF-WNNBGO-00   (a spine entity)
  L1      Ho-Chunk, Inc.                     CEDAR-NEST-…     (a SUB-HUB)
  L1      Ho-Chunk Farms
  L1      Ho-Chunk Trading Group

HUB       Arctic Slope Regional Corporation  ANRC-ARCSLO-00
  L1      ASRC Federal Holding Company, LLC
    L2      ASRC Federal Broadleaf
    L2      ASRC Federal Vistronix
    L2      ... 30 more operating companies
  L1      ASRC Industrial
    L2      RSI EnTech, LLC
      L3      Sigma Science, Inc
```

`hierarchy_level` 1 = 1,542 · 2 = 66 · 3 = 2. A sub-hub is never a peer of its
hub (`docs/IDENTIFIER_STANDARD.md` §2), so every row carries **both**
`owner_hub_cedar_uid` — the nation at the top, always a spine entity — and
`parent_enterprise_id`, the immediate owner, which may itself be an enterprise.

**A hub is not its own subsidiary.** `The Eyak Corporation` against the spine's
`Eyak Corporation`, and `Coushatta Tribe of Louisiana` against the spine's
deliberately short `Coushatta`, each made a company the parent of itself and
published as a level-2 chain that was really one company twice. The build now
tests the child against *every* deterministic rendering of the hub's name, and
the residue is zero.

---

## WHERE THE ROWS COME FROM

**Zero network requests.** Every input was already on this machine.
`PULL_DISCIPLINE.md` tier 1: re-read what you own before you pull.

| evidence class | enterprises | assertions |
|---|---:|---:|
| `audited_annual_report_as_45_55_139` | 861 | 2,788 |
| `parent_self_published_company_list` | 456 | 600 |
| `nation_self_published_enterprise_register` | 193 | 301 |
| `parent_declared_subsidiary_list` (NHO) | 100 | 100 |

### The AS 45.55.139 mine — the new vein, and the biggest single contribution

Every ANCSA corporation with 500+ shareholders files an audited annual report
with the Alaska Division of Banking and Securities under **Alaska Statute
45.55.139**, and its *Principles of Consolidation* note **enumerates the
wholly- and majority-owned subsidiaries by legal name, signed off by an
auditor**. That is ownership asserted by the parent, about itself, under a
statutory filing obligation — the strongest evidence class available for this
family and better than anything derivable from SAM.

**524 such documents were already on disk** — 358 village-corporation PDFs in
`data/raw/external/ancsa_portal_v3/` fetched by `code/1031`, and 166
regional-corporation texts in `data/interim/ancsa_txt/`. Shard E had read the
regional ones for its 482 edges; nobody had read the village half.

```
documents on disk         524
with a text layer         458
naming 1+ subsidiary      185
excluded on terms          25
--------------------------------
ownership assertions    2,168
distinct parents           36
distinct firms            511
```

**Two parser facts, both measured rather than assumed, and each one was the
difference between 9 corporations and 36:**

1. **You cannot split the note into sentences.** Every second subsidiary name
   ends in `Inc.` and a sentence splitter cuts the list in half at the first
   one. The window is taken by character count from the trigger phrase and
   closed by a named terminator instead.
2. **You cannot split the list on commas.** `Wetaviq, Ltd.` contains one, and
   splitting produced `Wetaviq` and `Ltd` as two firms. Names are matched with
   a company-FORM anchored regex *over* the window, never split *out* of it.

Three more, each found by reading the output rather than the code:

- **Bristol Bay's note is a numbered list**, and the numbers were being read as
  part of the next firm's name (`10.CCI Mechanical, LLC`) and letting one
  greedy match run across two list items
  (`Aerostar SES LLC 17. Herman Construction Group, Inc`). List markers are now
  separators before any name is matched.
- **A name whose whole distinctive token set is one generic word is not a
  firm.** `Talarik Research and Restoration, LLC` was being emitted as
  `Restoration, LLC` because the connector `and` is lowercase and broke the
  name run. `ENTITY_MATCH_RULES` rule 1 is applied at *extraction*, not only at
  matching, because a bad row is worse than an absent one here.
- **Page furniture bleeds into the window.** `1 ANNUAL REPORT The Kuskokwim,
  Corporation` and `Alaska. Kuskokwim Properties, LLC` are a running header and
  a sentence boundary respectively.

**Anti-fabrication:** every emitted name appears **verbatim** in the source
document — it is a substring of it by construction, and a name that does not
survive that test is dropped rather than corrected.

### The other five sources

`data/staging/anc_subsidiaries/shard_e.jsonl` (482 ANC edges, 32 with a
published CAGE) · `shard_h.jsonl` (100 NHO edges with SBA DSBS identifiers) ·
`data/staging/tribal_enterprises/enterprise_register.jsonl` (210 accepted
rows — a nation's own "Our Companies" register) ·
`data/raw/external/anc_tribal_subsidiary_lookup.csv` (549 rows, the only source
here that reaches lower-48 tribal governments at scale) ·
`data/staging/business_registry/*.jsonl`.

**The business-registry selection is a structural predicate, not a hand-picked
file list:** a source qualifies when it declares
`directory_type = subsidiary_directory` **and** an ownership `identity_scope`.
That is what keeps **Calista's shareholder business directory** — 98 firms owned
by individual shareholders, `shareholder_descendant_or_spouse` — out of a
dataset that would otherwise assert the corporation owns them.

---

## THE 1070 HANDOFF — 583 held OWNERSHIP rows, merged not appended

`code/1070_anc_nho_business_sweep.py` swept 822 entities — all 191 ANCs, all
210 NHOs, 365 tribal governments script 701 never reached, and all 56
intertribal organisations — and staged 1,106 rows in the 58-column
`native_owned_businesses` schema. The integrator merged the 523
`assertion_class = RELATIONSHIP` rows into that file and **held the 583
OWNERSHIP rows for NEST**, because the `relation_class` split puts ownership
here. The integrator measured **170 of the 583 already present in NEST by
normalised name** before splitting them, so a plain append would have
duplicated a third of the batch.

**It was merged, not appended.** The rows are fed through the *same*
(owner hub, normalised name) clustering as every other source, so a
restatement of a firm NEST already holds raises that enterprise's
`n_source_observations` instead of creating a second row for one company.

```
held for NEST                                        583
  refused: unreviewed HTML heading/anchor scrape     229
  refused: shareholder-owned, not corporation-owned   57
  ingested                                           297
    merged onto an enterprise NEST already held      167
    net new enterprises                              128
```

`1,482 -> 1,610 enterprises`, `3,492 -> 3,789 assertions`. Every refusal keeps
its full 58 staged columns plus a `nest_refusal` sentence in
`data/staging/nest/sweep_1070_refused.csv`, so the integrator can see exactly
what was declined and reverse any of it without re-harvesting. **A refusal that
leaves no trace is indistinguishable from a row nobody noticed.**

### The two refusals, each on the staged file's OWN declared caveat

**229 unreviewed prose scrapes.** The sweep flagged them itself —
`HEADING_SCRAPE_ON_A_DIRECTORY_INDEX`, with a `verification_basis` ending
*"not a table; review before resolving"* — and it was right to. ASRC's block
alone yields `Blank`, `No Results Found`, `Employee Resources`,
`Software, Apps & Analytics`, `Infrastructure Ops` … **and seven natural
persons' names scraped off a leadership page**. A natural person's name may
never enter this dataset, so this is a hard rule rather than a quality
preference, and it is the same prose-scrape defect
`ENTERPRISE_REGISTER_BUILD_LOG.md` records for Doyon
(*"Enjoy lunch at Kantishna Roadhouse"*).

**57 shareholder-owned businesses.** Bering Straits'
`shareholder-owned-businesses` directory, `identity_scope =
shareholder_descendant_or_spouse`. That scope is an ownership claim about a
**person**, not about the corporation, and admitting it would have NEST assert
that Bering Straits owns its shareholders' printing shops and flooring
businesses. Identical in shape to Calista's shareholder directory, which this
build already refuses at source selection — the same trap arriving by a second
route, which is why the refusal is written as a predicate on `identity_scope`
and `directory_type` rather than as a note about one corporation.

**A third guard is written and did not fire.** `association_member` and
`tribally_owned_entity_of_a_member_nation` are legitimate new scopes the sweep
declared, and neither appears in the 583 held today. USET lists *Choctaw Fresh
Produce*, which **is** tribally owned — by **Mississippi Choctaw**, not by USET,
the keyed authority. The guard refuses any such row outright, because the hub
must be the owning nation and a row that does not name it cannot be repointed
to one by guessing.

### Auto-ruled evidence is carried on the row, not dropped

Every one of the 583 is `AUTO_RULED_NOT_HUMAN_REVIEWED`. That belongs on the
row rather than in a build log, so `nest_enterprises.csv` gained
**`evidence_human_reviewed`** and **`n_auto_ruled_observations`**, and the
relations table gained `source_review_status`. Measured: **1,482 Y / 128 N** —
the 128 that rest solely on auto-ruled evidence are exactly the net-new
enterprises, which is the honest result and is filterable.

### The relation was translated, not inherited

`certification_tier` is deliberately empty in the staged file — in the live
business file it holds a TERO preference priority and the sweep refused to
overload it. The ANCSA relation rides in `validation_flags` as
`RELATION=wholly_owned|majority_owned|equity_or_jv|subsidiary_unspecified`.
Translated into this dataset's vocabulary rather than carried as a flag string,
and **`equity_or_jv` maps to `joint_venture`, which `canon_rel` classes as
AFFILIATION, not ownership** — an equity stake is not a subsidiary.

---

## WHERE THE WEB LIST DISAGREES WITH THE AUDITED FILING — 2 rows, after two false answers

This is the first thing in NEST that *can* disagree.
`docs/ASSERTION_LAYER.md` measured that every fact in Cedar rests on exactly one
source; **60 enterprises are now corroborated by two genuinely independent
evidence families** — an audited AS 45.55.139 filing and the parent's own
website — and 438 of 1,610 rest on more than one distinct source, up from 273.

**Two versions of the conflict check produced a number that was about something
other than its own name, and both would have shipped.**

| version | reported | what it was actually measuring |
|---|---:|---|
| v1 | 37 conflicts | 35 were the filing saying `wholly_owned` where the site said `subsidiary` — **an unspecified word being refined by a specific one**, not a rival claim |
| v2 | 23 conflicts | 21 were Calista's `wholly_owned` vs `operating_company` — **a SHARE and a ROLE**, which cannot disagree, because a wholly-owned company is very often an operating one |
| v3 | **2 conflicts** | two values on the *same* axis |

The fix is a modelling observation worth keeping: **`relationship` carries two
orthogonal axes in one column.** `wholly_owned` / `majority_owned` state the
SHARE; `holding_company` / `operating_company` / `division` state the ROLE;
`subsidiary` and `declared_suborganization` state neither. A conflict check has
to compare within an axis or it manufactures disagreements — and thirty-five
manufactured ones would have buried the two that are real.

The two that survive:

| enterprise | owner | audited filing | web list | published |
|---|---|---|---|---|
| Chugach Government Solutions, LLC | Chugach Alaska Corporation | `holding_company` | `operating_company` | `holding_company` |
| Chugach Regional Development, LLC | Chugach Alaska Corporation | `holding_company` | `operating_company` | `holding_company` |

**The audited filing wins**, and `data/staging/nest/evidence_conflicts.csv`
says so on the row: a statutory filing signed off by an auditor outranks
marketing copy. Both are real and both are worth an owner's eye — a firm the
filing treats as a holding company and the site presents as an operating one is
either mid-reorganisation or two levels collapsed into one on the website.

---

## THE FOUR GUARDS, AND WHAT EACH CAUGHT

### 1. Restricted publishers, refused by every route — **84 assertions**

`TERMS_STATED_RESTRICTIVE` sources are excluded including in a harmonised
derivative of data an earlier pass already fetched, matched on both the
asserting parent's name and the source host. Refused here: **NANA Regional
Corporation (43), Chickasaw Nation (24), Forest County Potawatomi (9), Yakama
Nation (8)**. Asking is the route back in; a cleverer scrape is not.

### 2. The Alaska village-government guard — **45 assertions repointed**

`ANCSA_OWNERSHIP_RULING` rule 2 and `cedar_domain.village_government_owns_an_anc()`
(always `False`): a Native Village **government** does not own an ANCSA
corporation. `anc_tribal_subsidiary_lookup.csv` violates that on 45 rows — and
says so itself, because `parent_entity_type` reads `ANC_VILLAGE_UIC` while
`parent_entity_id` is `AKNF-…`, the Native Village of Barrow's **government**.

The repoint is **read out of the source's own field**, never guessed: the
corporation named in `parent_entity_type` is matched by name, then by
name-prefix among ANCSA classes with a five-character floor so an acronym can
never win that way, and only then against a **named acronym exception**
(`UIC → ANVC-KPVKPT-00`, Ukpeaġvik Iñupiat Corporation). Where the corporation
is not uniquely in the spine the row is **held**, not attached to the
government.

Repointed: **Barrow → UIC (34), Tatitlek (8), Afognak (3)**. This is the
`ALASKA_VILLAGE_GOVERNMENT_VS_VILLAGE_CORPORATION` family (334 defects,
$24.52B) reached from a fourth direction.

### 3. A named firm that resolves to a Cedar hub — triaged three ways

Reading a subsidiary list at face value converts independent entities into
somebody's subsidiaries. But the naive version of this guard **held Ho-Chunk,
Inc. and lost the row**, which is the opposite error. The triage:

- **The child resolves to a GOVERNMENT-class hub → a NAME COLLISION, not a hub
  identity.** A government is not a corporation and can never BE somebody
  else's subsidiary. `Ho-Chunk Inc` matches the spine's `Ho-Chunk` only because
  `norm()` strips `Inc`, and `Ho-Chunk` is the **Ho-Chunk Nation of Wisconsin**
  while Ho-Chunk, Inc. is the **Winnebago Tribe of Nebraska's** holding company.
  Two tribes, one word. The edge is kept, keyed to its real publisher, and the
  collision is recorded on the row so the next reader does not re-litigate it.
- **Both sides are ANCSA corporations → DOWNGRADED to a tie**, not dropped.
  Doyon's own page names *Huna Totem Corporation* and *Klawock Heenya
  Corporation*; Bristol Bay's names *Choggiung Limited*; Tozitna's report names
  *Doyon, Limited*. `ANCSA_OWNERSHIP_RULING` rules 4/5 make these shareholding
  or ancestry, never ownership, so the row survives with
  `relation_class = affiliation`.
- **Anything else → the enterprise IS an existing Cedar entity**, and the row
  carries its uid in `enterprise_existing_cedar_uid` rather than pretending it
  is new. 8 rows: *Citizen Potawatomi Community Development Corporation*,
  *HoChunk Community Capital (CDFI)*, *Alaska Growth Capital BIDCO*.

### 4. Uniqueness is required on every name resolution

A name matching two spine entities resolves to neither. That is what keeps
`Cherokee` — 45 entities, three of them federally recognized tribes — from
resolving to anything at all (`ENTITY_MATCH_RULES` rule 13).

---

## IDENTIFIERS — 107 external, 1,503 Cedar-minted

**An identifier appears in `uei` or `cage_code` only where a source PUBLISHED
it.** A name that happens to match a UEI in FPDS is a *candidate* and lives in
`uei_candidate` with a basis saying why it is only that. The exactness of the
key says nothing about the correctness of the link.

```
external_identifier   107     CAGE 107 · UEI 102
cedar_minted_only   1,503
uei_candidate         597     exact normalized name into the SBA DSBS extract
```

**Nothing was inherited from `cedar_identifier_ledger_final.csv`.** That ledger
carries ~~2,142 UEI rows worth $38.19B~~ **227,540 rows worth $45.93B** (**CORRECTED 2026-09-02 — that measured ONE JOIN LEG of three.** `40_build_prime_contracts.py` keys on `uei_exact`, `cage_exact` and `parent_uei` and tries all three in order. Re-measured disjointly on the live files: `uei_exact` 172,338 rows / $38,191,057,346 + `cage_exact` 14,149 / $7,252,015,101 + `parent_uei` 41,055 / $489,839,872 = **227,540 rows / $45,932,912,319**. The CAGE leg is where `need_v6` actually lives — 838 tier-B CAGE rows, 60+ CAGE codes on `TRBF-LUMBEE-00` via the token `north` — and nobody had looked at it. **Scoping a measurement to one leg of a multi-leg join understates it silently, because the legs it skipped answer the same question.** Full derivation: `docs/QUARANTINE_EXPOSURE_LOG_2026-09-02.md`.)
on quarantined methods with no exclusion recorded, and `attribution_method` says who decided while `confidence_tier` says
what was decided. This build reads published CAGE codes, the SBA DSBS extract
and `fpds_uei_cage_map.csv` (a name/identifier map, not an attribution) — and
suppresses the literal string `NAN`, which sits in `cage_code` on 2,196 rows
across 2,193 UEIs.

### The Cedar identifier, and why it is not a `CE-` uid

An owned enterprise is a **sub-hub**, and sub-hubs are never spine rows. Giving
one a `CE-` uid would put a non-entity into the entity namespace; giving it a
`CEDAR-ENT-` id would file a tribally owned company under the *individually*
Native-owned class. So `code/cedar_ids.py` gained one prefix:

```
CEDAR-NEST-000123-K7
│          │      └─ two 503_identity check characters, two independent
│          │         weightings: 100% of single substitutions and 100% of
│          │         adjacent transpositions caught
│          └─ ordinal, allocated under an exclusive file lock
└─ enterprise sub-hub
```

**The binding is append-only.** `data/spine/cedar_nest_id_register.csv` maps
(owner hub, normalised name) → `enterprise_id`, and the build reads it first.
Without it, `allocate()` would hand out a new ordinal on every run and every
rebuild would silently re-key the dataset — defect class 7 in `293`, and the one
that quietly breaks a customer's join. **Measured: a second `build` minted 0
ids and produced identical keys.**

`CEDAR-HOLD` appears in `cedar_ids.PREFIXES` marked retired and unissued. It was
this collection's prefix under its working name `holdings` for a few hours
before the owner named it NEST; its counter stands at 1,483 and not one of those
ids was written to any table. A prefix is never reused.

---

## ADDRESSES — 722 of 1,610 (44.8%), and the basis says which lookup answered

| basis | n |
|---|---:|
| SBA DSBS, matched on a **candidate** UEI (an exact-name proposal) | 603 |
| the parent's own subsidiary listing | 93 |
| SBA DSBS, matched on a **published** UEI | 26 |
| none | 888 |

**City and state only. No street address.** And the basis column had to be
fixed before it could be believed: the first version labelled all 623 DSBS hits
*"keyed on UEI"* because it tested membership *after* the fallback chain had
run — 623 rows claiming an identifier key when only 102 rows carry a UEI at all.
That is this repo's signature defect, a field that does not measure its own
name, and it is now the only thing the column reports.

**D&B-derived recipient addresses in the contracting tables are deliberately not
used.** `IDENTIFIER_STANDARD` §4 forbids their bulk dissemination and they
attach to every base award dated before 2022-04-04. **Street-level address is
the honest gap in this dataset** — see the next-pass list.

---

## ROW CONSERVATION

```
data/staging/nest/raw_ownership_assertions          3,897 in
  emitted: kept with a resolved owner and a named source   3,796   97.41%
  refused: TERMS_STATED_RESTRICTIVE                           84    2.16%
  refused: hub unresolved                                     17    0.44%

.../native_business_sweep_1070/held_for_nest_ownership.csv  583 in
  emitted: ingested into NEST via the shared clustering       297   50.94%
  refused: unreviewed HTML heading/anchor scrape              229   39.28%
  refused: shareholder-owned, not corporation-owned            57    9.78%

data/clean/nest_enterprises.csv                     1,610 in
  emitted: ownership asserted by the owner itself           1,512   93.91%
  emitted: a published tie that is NOT ownership               98    6.09%
  rejected: ownership claim with no source                      0    0.00%
```

The last line is structurally impossible: `verify` **I3** exits 1 on any such
row and `selfcheck` proves that check fires.

The 17 unresolved hubs are honest residue and are named in
`data/staging/nest/held_rows.csv`: *Confederated Salish & Kootenai* (the spine's
canonical name is the truncated `Confederated Salish`), *Central Council of
Tlingit & Haida Indian Tribes of Alaska*, and *Manu Kai LLC*, which is not in
the spine at all. None was forced to a match.

---

## THE GATE

```
py -3 code/1072_tribally_owned_enterprises.py verify      -> exit 0
py -3 code/1072_tribally_owned_enterprises.py selfcheck   -> 8/8 PASS
py -3 code/518_dataset_readiness.py                       -> READY 14 / 14
```

Eight invariants, and **six are proved to FIRE** by injecting the violation into
a copy of the live file, asserting exit 1 *and* that the named invariant is what
fired, then restoring and asserting exit 0 again. A check that has never failed
on purpose is not known to work.

| | invariant | fires |
|---|---|---|
| I1 | `enterprise_id` unique, with valid 503 check characters | ✓ |
| I2 | every owner hub is in the spine register | ✓ |
| I3 | every row carries a source — **an ownership claim with no source is the one row this dataset may not contain** | ✓ |
| I4 | no row's owner is a refused publisher | ✓ |
| I5 | level ≥ 2 implies a resolvable parent; no enterprise is its own ancestor | ✓ |
| I6 | edges and enterprises conserve in both directions | — |
| I7 | `in_federal_contracting` is Y or N, never blank | ✓ |
| I8 | no Alaska Native Village government owns an ANCSA corporation | — |

`293_lint_bug_classes.py`: **zero findings in `1072_*` across all seven
classes.** One class-1 finding was raised and **fixed rather than waived** — the
business-registry loop globbed `TBD-*.jsonl`, a prefix filter that would
silently omit a harvest filed under any other convention, exactly the shape of
the deals additions glob that omitted 131 rows. It now enumerates `*.jsonl` and
selects on the row. `1072` is declared in
`cedar_domain.PROMOTED_TABLE_PRODUCERS`, because reading the staged parts is its
job and it reads every one.

---

## WHAT THE NEXT PASS SHOULD DO, in order of value per hour

1. **Street addresses.** 47% of rows carry city and state, none carries a
   street. The routes that do not touch D&B: JSON-LD `PostalAddress` on pages
   already in `data/staging/*/raw/` (zero network — 11 of shard E's 118 stored
   pages carry one), the Alaska Division of Corporations entity search, and
   `usaddress` over the address prose already sitting in the annual reports
   (*Kootznoowoo: "Favorite Bay, LLC: Owns the Newport IX building located at
   2201 Buena Vista Drive, Albuquerque, New Mexico"*).
2. **438 of 1,610 enterprises rest on more than one distinct source, and 1,172
   rest on one**, and 60 are now corroborated by two genuinely independent
   evidence FAMILIES (an audited filing and a corporate site). `docs/ASSERTION_LAYER.md`'s finding — every fact in Cedar
   rests on exactly one source — is only partly untrue here. The cheapest second
   family is the Alaska Division of Corporations registry, which is genuinely
   independent of both the annual report and the corporate site.
3. **The 273 documents that have a text layer and name no subsidiary.** Some
   genuinely enumerate nothing ("its majority-owned subsidiaries, most of which
   are limited liability companies"); others use a shape the two triggers do not
   reach. Ten minutes with `ancsa_mine_log.csv` sorted by `outcome` would say
   which.
4. **66 documents with no text layer.** `code/1031` has an OCR fallback that
   decides per PAGE; it has not been run over these.
5. **Tribal governments are the thin side: 41 hubs of ~580.** The ANCSA route
   is exhausted and the lower-48 route is a nation's own "Our Companies" page.
   `code/701`'s TERO-free vocabulary sweep found 10.0% of hosts publish one;
   `1070` is sweeping now.

---

## FILES

```
code/1072_tribally_owned_enterprises.py         mine | assemble | build |
                                                codebook | conserve | verify |
                                                selfcheck
data/clean/nest_enterprises.csv                 1,610 rows, 59 columns
data/clean/nest_enterprise_relations.csv        3,789 rows, 25 columns
data/spine/cedar_nest_id_register.csv           1,610 append-only id bindings
data/clean/codebook/18a_nest_enterprises.csv    59 variables documented
data/clean/codebook/18b_nest_enterprise_relations.csv   25 variables
data/staging/nest/ancsa_consolidation_edges.jsonl   2,168 mined assertions
data/staging/nest/sweep_1070_refused.csv        286 refusals, full 58 columns
data/staging/nest/evidence_conflicts.csv        2 real audited-vs-web conflicts
data/staging/nest/ancsa_mine_log.csv            524 documents, per-doc outcome
data/staging/nest/ownership_edges_staged.jsonl  3,499 normalised assertions
data/staging/nest/held_rows.csv                 101 refusals, each with a reason
data/interim/ancsa_txt_1072/                    358 extracted PDF text layers
```

Shared files touched, each additively and each with a backup:
`code/cedar_ids.py` (one new prefix) · `code/cedar_domain.py` (one producer) ·
`code/500_build_architecture_map.py` (one collection) ·
`code/512_build_dataset_contracts.py` (own `GRAIN_NEST` dict) ·
`code/518_dataset_readiness.py` and `code/526_dataset_standard.py` (one entry
each) · `docs/datasets/_descriptors.json` (one descriptor) ·
`data/clean/codebook_master.csv` (**appended** 81 rows, never rewritten) ·
`data/clean/cedar_harvest_conservation.csv` (10 rows).

**Nothing was written to the spine's entity register, to
`cedar_constellation_edges.csv`, or to `native_owned_businesses.csv`. Nothing
was committed.**

---

## UPDATE 2026-09-02 — a fourth evidence family, the Chugach adjudication, and 25 companies held twice

*`code/1102_nest_corroboration_adjudication.py`. Full write-up:
**`docs/ENTITY_LAYER_DEEPENING_2026-09-02.md`** §3. Nothing above is superseded
except where struck here.*

**1. The second-source problem has an answer that needed no network call.**
This log's next-pass item 2 named the Alaska Division of Corporations as the
cheapest genuinely independent family. `data/clean/fpds_uei_edges.csv` is a
cheaper one and it is already on disk: the parent a registrant declared **about
itself** to the federal government, independent of both the parent's audited
filing and the parent's website. Applying rule 11's measured 20-observation
ownership floor, and requiring the declared parent to resolve through the
identifier ledger to **the owner hub NEST already asserts**:

```
CORROBORATED             87      <- ~~60~~ two-family corroborations
CONTRADICTED              8
PARENT_UNRESOLVED       177
PARENT_BELOW_JV_FLOOR    71
NO_DECLARED_PARENT    1,267
```

Six of the eight contradictions are the LEDGER's defect, not NEST's — five
Bowhead/UIC rows plus Rockford and UMIAQ resolve to
`AKNF-INPTAS-00-ARCSLO`, the **village government**, which
`ANCSA_OWNERSHIP_RULING` rule 2 forbids; `Goldbelt Eagle` and
`Vista Defense Technologies` are collisions on `Eagle` and `Vista`. This is the
`ALASKA_VILLAGE_GOVERNMENT_VS_VILLAGE_CORPORATION` family reached from a fifth
direction, with NEST on the correct side. Two stay open — `Nisga'a Tek LLC` and
`Broadleaf, Inc` — in
`review/nest_fpds_parent_contradictions_2026-09-02.csv`.

**2. Chugach: the audited filing UPHELD, now on two of three sources.** Two
facts this log did not have. (a) The web source is ONE page,
`www.chugach.com/business/directory`, and on that same page it calls **Chugach
Commercial Holdings a holding company** while calling CGS and CRD operating
companies — so the site asserts a different role rather than omitting one, and
the conflict is genuine. (b) A **third** source,
`anc_tribal_subsidiary_lookup.csv`, lists CCH, CGS, CIH and CRD **identically**
as `subsidiary` directly under the corporation: four parallel siblings at one
tier, two of them named *Holdings*.

**And `relationship` fuses THREE axes, not two.** This log found SHARE
(`wholly_owned`) vs ROLE (`holding_company`). The third: a **consolidation note
answers where an entity SITS**, a **business directory answers what a firm
SELLS**, and both render into the same six words. The audited filing answers the
question the column is asking. The adjudication is written onto
`data/staging/nest/evidence_conflicts.csv` itself, in five new columns.

**3. NEST holds 25 companies twice.** Clustering is on (owner hub, normalised
name) and **a trailing parenthetical survives normalisation**:

```
CEDAR-NEST-000473-WH  Chugach Government Solutions, LLC    2 observations
CEDAR-NEST-000474-2A  Chugach Government Solutions (CGS)   1 observation
```

**25 groups, 50 rows.** 24 are an acronym (`Ahtna Global LLC (AGL)`,
`Yulista Aviation (YAI)`, `Eyak Technology LLC (EyakTek)`,
`Bristol Bay Construction Holdings LLC (BBCH)`) and in every one of the 24 the
acronym twin is the `ANC_TRIBE_LOOKUP` row at `n_distinct_sources = 1` while the
plain row already carries 2 or 3; the 25th is a gloss, `Aan Hít (Village House)`.
The cost is double — 25 rows of overstatement **and 25 lost corroborations**,
because a restatement that fails to cluster raises nobody's source count, which
is precisely what the "merged, not appended" design exists to do.

**FLAGGED, NOT MERGED**: merging retires 25 ids out of an append-only register.
`review/nest_name_variant_duplicates_2026-09-02.csv`.

**The 60.7% headline does not move.** The 25 duplicates are ANC subsidiaries
that ARE present in federal contracting, so collapsing them would raise the
absent share, not lower it. The floor stays a floor.

---

<!-- BEGIN NEST-OWNER-V6-2026-09-02 -->
## UPDATE 2026-09-02 — THE OWNER'S OWN ENTERPRISE DATASET, RECONCILED

*`code/1130_nest_owner_v6_reconcile.py`. `versions | build | codebook | verify |
selftest`. Zero network requests. **Zero Cedar enterprise ids minted.** Nothing
written into `nest_enterprises.csv`. Nothing committed. Every figure below is
re-derivable with `py -3 code/1130_nest_owner_v6_reconcile.py build`.*

The owner built an enterprise dataset on this machine months ago and nobody in
this project had read it:

    ~/Desktop/dissertation/data/tribal_federal_spending/clean/
        native_entity_enterprise_dataset_v6_geocoded.csv

**18,110 rows, 16,632 distinct normalised enterprise names, 658 distinct
parents.** The largest `ON_DISK_NOT_PROMOTED` asset in the project
(`AGENT_FIELD_GUIDE` section 5).

### 1. WHICH FILE IS AUTHORITATIVE — v6, and the other four are BROKEN

The task arrived saying *"v5 matches v6; compare all three rather than
assuming."* They do not match, and the difference is a **column-shift defect**.

| version | rows | distinct normalised names | parents | `hq_state` populated | `hq_state` cell **equals this row's own UEI** |
|---|---:|---:|---:|---:|---:|
| v1 | 19,763 | 16,718 | 641 | 18,291 | **12,127** |
| v2 | 19,809 | 16,762 | 641 | 18,337 | **12,127** |
| v3 | 19,846 | 16,774 | 641 | 18,374 | **12,127** |
| v5 | 18,110 | 16,632 | 658 | 16,638 | **11,390** |
| **v6** | **18,110** | **16,632** | **658** | **14,629** | **0** |

v5 and v6 hold the identical 18,110 rows and the identical name universe. They
differ in **four columns and only four** — `hq_city`, `hq_state`, `hq_zip`,
`hq_county_geoid` — and in every one of them **v6 is the fix**. v5's `hq_state`
is not a state: on 11,390 of its 16,638 populated cells it is a 12-character
UEI, and on 11,935 it is *this row's own* `enterprise_uei`. v6 carries a
two-letter code on all 14,629, adds `hq_zip` (5,074) and `hq_address_line`
(12,114), and lifts `hq_city` from 5,178 to 15,556.

**v6 is authoritative. v5 must not be read for geography.** Recorded as a
measurement, not an assertion:
`data/staging/nest_owner_v6/version_comparison.csv`, and invariants **I13a /
I13b** exit 1 if either half stops being true.

**But v6 is NOT a superset of v3, and that matters.** Under NEST's own `norm()`,
**160 rows / 158 enterprise names present in v3 are absent from v6** — all 160
carry a UEI, 84 from SBA DSBS and 76 from the master registry (`BOWHEAD
PROTECTION & SECURITY SERVICES LLC`, `AKIMA FACILITIES MANAGEMENT, LLC`, `UMIAQ
DESIGN, LLC`, `CHEROKEE SERVICES GROUP LLC`). Under a raw name compare it looks
like 598 rows, and 438 of those are rendering variants v6 still holds — **which
is why the loss has to be measured after normalisation and not before.** The 160
are a recovery-candidate list, flagged and never deleted:
`data/staging/nest_owner_v6/v3_recovery_candidates.csv`.

### 2. THE THREE RECONCILIATION COUNTS

His rows were put through **NEST's own clustering** — `(owner hub cedar_uid,
normalised name)` — not appended. `norm()` is copied verbatim from `1072` and
invariant **I0b** re-derives `enterprise_name_normalized` for all 1,610 live
NEST rows on every verify, because two normalisers that drift are two
clusterings and the comparison would be measuring the drift instead of the data.

```
owner enterprise clusters, hubbed                    5,226
  1. ALREADY IN NEST                                   440
  2. NET NEW TO NEST                                 4,786
       of which a HUB DISAGREEMENT                     223
  3. NEST HOLDS AND HIS FILE DOES NOT                1,170
       absent from his file entirely                   614
       present, but on a different hub or key          556

owner rows that CANNOT be clustered (named, never folded in):
  no tribe_id on the row                            12,084
  tribe_id present but uncrosswalked                    38
```

**The third number is the one that says what our scraping added.** 614 NEST
enterprises are in no form in his file: **462 ANC subsidiaries, 130 tribal, 22
NHO**; 570 ownership and 44 affiliation; **592 of the 614 are absent from
federal contracting altogether**, which is the 60.7% headline restated from the
other side. 414 come from the AS 45.55.139 audited annual reports and 142 from a
nation's own enterprise register — Tlingit and Haida's *One Stop Auto Shop*,
*Smokehouse Catering*, *The Driftwood Lodge*, *Two Coppers Casino*. **A firm
that never pursued a federal contract is invisible to every source his file is
built from, and that is precisely the vein the ANCSA mine and the "Our
Companies" sweep opened.**

**What the 4,786 net-new bring:** 3,576 carry a UEI, 775 a CAGE, 775 are
8(a)-certified, 2,632 carry a city and a state, 1,113 are nonprofits, and all
4,786 carry a `verification_source`. Their evidence families are **2,338
`cedar_inference`, 1,855 `federal_registry`, 474 `human_ruling`, 257
`entity_self_published`, 46 `compiled_directory`** — so roughly half of the
expansion rests on a resolver output rather than on an observer, and that has to
survive into whatever ingests it.

**The 440 already held are the corroboration**, not overlap to discard: 425 are
`ownership` in NEST and 15 `affiliation`, 208 arrive with a UEI and 201 with a
city and state NEST does not have.

### 3. THE 223 HUB DISAGREEMENTS ARE MOSTLY ONE KNOWN DEFECT — IN HIS FILE

A normalised name NEST holds under a *different* hub is not an absence, and
classing them was the most valuable thing in this pass:

```
ALASKA_VILLAGE_GOVERNMENT_VS_VILLAGE_CORPORATION   212
ANC_TIER_DISAGREEMENT                               20
UNADJUDICATED_HUB_DISAGREEMENT                      14
```

**212 of 223** hub the firm on an Alaska Native Village **government** while
NEST hubs it on the ANCSA **corporation** — `Alutiiq LLC` and *Afognak
Diversified Services* under `AKNF-AFGNAK-00-KONIAG` (the Native Village) rather
than the Afognak Native Corporation; the same at Aleknagik, Agdaagux and Arctic
Village. `ANCSA_OWNERSHIP_RULING` rule 2 and
`cedar_domain.village_government_owns_an_anc()` (always `False`) settle every
one, and **NEST is on the correct side of all 212**. This is the
`ALASKA_VILLAGE_GOVERNMENT_VS_VILLAGE_CORPORATION` family (334 defects, $24.52B)
reached from a **sixth** independent direction. The correction belongs in his
file, not in ours.

### 4. THE PARENT CROSSWALK — 650 of 658, and his `tribe_id` IS a Cedar handle

`tribe_id` is the same handle scheme at an earlier vintage, so no name matching
was needed for 96% of it:

| method | parents |
|---|---:|
| `handle_exact` — the id IS a live Cedar handle | **632** |
| `name_tokens_class_gated_unique` | 17 |
| `handle_stem_unique` | 1 |
| `UNRESOLVED_NOT_IN_REGISTER` | 7 |
| `UNRESOLVED_AMBIGUOUS` | 1 |

The 17 are handles Cedar has since re-minted under a different mnemonic —
`TRBF-CHKSAW-00` to `TRBF-CHKSWN-00` (The Chickasaw Nation), `TRBF-WBGNON-00` to
`TRBF-WNNBGO-00` (Winnebago), `TRBF-PRCHCK-00` to `TRBF-POARCH-00`, plus twelve
intertribal organisations. Each was resolved by **maximal distinctive-token
subset, gated on the entity class the owner's own handle prefix declares, and
required to be unique at that maximum** — the class gate is what keeps
`INTERTRIBAL-ITCA-00` off `AKNF-COUNCL-00`, the Alaska Native Village of
**Council**, which token-matches every "Inter-Tribal Council" in the file. The
one stem route is `SGVF-TLNGHD-00` to `AKNF-TLNGHD-00-SEALSK`: Cedar's own
mnemonic, unique in position 2 of the register, not a name guess.

**The 8 unresolved are an honest outcome (ADR-010) and were not forced.**
`TRBF-CSAKT-00` *Confederated Salish and Kootenai* is `UNRESOLVED_AMBIGUOUS`
because Cedar's canonical name is the truncated `Confederated Salish` and
`Kootenai` is a separate tribe — **the same entity `held_rows.csv` already
names**, arrived at independently. `NHO-MANUKAI-00` *Manu Kai LLC* is also
already in `held_rows.csv`. Six intertribal organisations (NAFOA, NAJA, ILTF,
First Nations Development Institute, the Five Civilized Tribes council, IHS
Tribal Self-Governance) are **spine gaps** and are the cheapest register
additions on this page.

### 5. HIS IDENTIFIERS ARE MOSTLY NOT A SECOND SOURCE — THEY ARE ALREADY OURS

The brief said *"every Cedar UEI came from the federal side"*, so a UEI he
verified independently would corroborate. **Measured before believing it
(`AGENT_FIELD_GUIDE` rule 2), and it is not true.**

`data/spine/cedar_identifier_ledger.csv` holds 19,232 rows. **13,191 of them
come from `master_tribal_entity_registry.csv`, and 13,070 of those 13,191 UEIs
are in his v6.** Cedar's identifier ledger *is* an earlier vintage of his own
file. **A copy of a source sitting in our table does not corroborate that
source** — exactly what `START_HERE` item 0 records about the Federal Register
roster, arriving by a second route.

**The proof is a defect that travelled with it.**
`cedar_identifier_ledger.state` holds this row's own identifier on **12,127** of
16,487 populated rows — the *identical* count to `hq_state` in his v1, v2 and
v3. Two counts agreeing to the row is not a coincidence: **the ledger was built
from a pre-v6 vintage and inherited the column shift.** Only 3,481 of 16,487
`state` values are a real two-letter code. **Do not read `state` on that table
as a state.** Flagged, not edited — the ledger is not this pass's to write:
`data/staging/nest_owner_v6/ledger_shared_upstream_findings.csv`.

**696 identifier pairs were handed to the corroboration workstream** in
`1118.Store.observe()`'s exact keyword shape, so adopting them as a `P7` pair is
a loop and not a translation
(`data/staging/nest_owner_v6/corroboration_pairs.csv`). Both sides are emitted
and the echo is flagged rather than booked:

```
ECHO  same SBA DSBS extract on both sides (1118 R-A)        388
ECHO  UEI already in our ledger, from HIS own files         275
INDEPENDENT  federal_registry against a self-published UEI   33
```

**33, not 696.** The 33 are NEST rows whose UEI the *parent published on its own
site* and which the SBA certification register independently binds to the same
firm — `entity_self_published` plus `federal_registry`, two observers. `1118`
owns the arbitration; `1130` does not build a parallel layer and does not edit
`1118`.

**3,306 of his UEIs are in no Cedar table at all** — that, not corroboration, is
the identifier value in his file.

### 6. THE ANC/NHO DUAL ROLE — `data/clean/nest_entity_dual_role.csv`, 358 rows

> *"ANCs and NHOs are themselves entities, but they're also enterprises too."*
> — the owner

He is right and NEST's model was wrong: an ANCSA corporation was only ever an
`owner_hub_cedar_uid`, a hub that owns. It is also a corporation that **trades**.

**It is RECORDED, not duplicated.** NEST's key is (owner hub, normalised name);
a self-row would make the hub its own subsidiary — the exact thing the 1072
build already refuses by testing the child against every deterministic rendering
of the hub's name, after `The Eyak Corporation` and `Coushatta` each published
as a two-level chain that was one company twice. So the second role lives in its
own table keyed to `cedar_uid`, one row per entity, and a consumer joins it to
`nest_enterprises` on `owner_hub_cedar_uid`. Invariant **I12** holds the
no-self-subsidiary line.

Three evidence rungs, recorded per row:

| rung | what fires it | rows |
|---|---|---:|
| R1 `DECLARED_BY_OWNER_DATASET` | his file carries a row whose `enterprise_name` normalises to the parent's own name | 263 |
| R2 `ENTITY_HOLDS_ITS_OWN_IDENTIFIER` | that row carries a UEI or CAGE on the entity's own legal name | 247 |
| R3 `REGISTERED_AS_A_FIRM_IN_SBA_DSBS` | the entity's own legal name is a row in the SBA certification register, with its own UEI | 106 |

**R3 exists because his file cannot evidence the NHO half of his own
correction** — it carries exactly one NHO parent, and that one
(`NHO-MANUKAI-00`) does not crosswalk. The SBA DSBS extract already on disk can,
it is a `federal_registry` observer rather than a restatement of his file, and
rule 14 is why it works: *an NHO says it is one, because the certification is
the point.* Uniqueness is required on **both** sides — 73 register entities were
refused because their own name is not unique in the register or in DSBS.

```
Federally recognized Alaska Native Village   127     Tribal College or University          9
Federally recognized tribe                   105     Alaska Native Regional Corporation    8
Alaska Native Village Corporation             45     Native CDFI                           8
Intertribal Organization                      16     State-recognized tribe                8
Native Hawaiian Organization                  13     other                                19
Federal-level self-governance consortium      10
```

**All 8 ANCSA regional corporations his file reaches hold their own UEI and
their own federal-contractor status** — Ahtna (`HM1PS6FAK6U7`, and 83 NEST
subsidiaries beneath it), Arctic Slope (53), Calista (75, 8(a)), Chugach (17,
8(a)), Bering Straits (41, 8(a)), Doyon (23), Sealaska (25), NANA. **53 ANCs and
13 NHOs in total.** Invariants **I11a to I11d** exit 1 if the table stops
reaching ANCs, stops reaching NHOs, becomes only those two, or loses the R3
rung.

### 7. WHAT THIS PASS DELIBERATELY DID NOT DO

* **It did not append to NEST.** `1072 build` is a full rebuild; an in-place
  append would be reverted by it while printing a larger row count and looking
  like progress — the FERC collision, four times over. The 4,786 are a
  **proposal for `1072` to ingest through its own clustering**, so the
  append-only `cedar_nest_id_register.csv` stays the only place an id is minted.
  Invariant **I6**: this script appears on **0** register rows.
* **It proposed no `relation_class`.** His file states no relationship word, so
  neither `structures` nor `ties` can be read off it. `relation_class_proposed`
  is blank on all 5,226 rows and invariant **I7** exits 1 if any row fills it or
  drops the `NO - provenance only` flag. **An affiliation recorded as ownership
  is the defect this dataset is most exposed to**, and guessing upward
  fabricates.
* **It laundered no ownership.** `verification_source` is carried per row; where
  it is blank (8,929 of 18,110 rows) there is no evidence, and that is what the
  row says.

### THE GATE

```
py -3 code/1130_nest_owner_v6_reconcile.py verify     -> exit 0, 31 invariants
py -3 code/1130_nest_owner_v6_reconcile.py selftest   -> 6/6 fixtures FIRE
py -3 code/293_lint_bug_classes.py                    -> 0 findings in 1130_*
```

Six invariants are proved to fire by injecting the violation into a copy of the
live file, asserting exit 1, restoring, and asserting exit 0 again — including
the one that matters most here: **an empty reconciliation reads as FAILURE, not
success.** Every input table is accounted row-for-row in
`data/staging/nest_owner_v6/conservation.csv`; **9 of 9 accounting rows balance
to zero unaccounted.**

Shared files touched, each additively and each with a backup:
`code/512_build_dataset_contracts.py` (own `GRAIN_NEST_DUAL` dict) and
`data/clean/codebook_master.csv` (**appended** 27 rows as
`18c_nest_entity_dual_role`, never rewritten), plus this log inside its own
marker. **Nothing was written to `nest_enterprises.csv`, to
`nest_enterprise_relations.csv`, to the id register, to the spine, or to the
identifier ledger. Nothing was committed.**

### NEXT, IN ORDER OF VALUE PER HOUR

1. **`1072` ingests the 4,786 through its own clustering** and mints their ids
   from the register. Carry `verification_source` per row and set
   `relation_class = affiliation` unless a source states ownership.
2. **12,084 of his rows carry no `tribe_id`** — 3,140 typed
   `TRIBAL_ENTITY_UNCROSSWALKED_SBA` and 8,928 blank, 12,068 of them carrying a
   UEI. They are the SBA-derived rows Cedar has been trying to reach, and the
   largest single block of unhubbed enterprise identity on this machine. The
   route is the identifier, not the name.
3. **The 212 village-government hubs** are a correction to hand back to the
   owner with the ruling attached.
4. **Six intertribal organisations are spine gaps.** Cheap.
5. **`cedar_identifier_ledger.state` holds an identifier on 12,127 rows.** Not
   this pass's table; it needs an owner.

**One integrator step is deliberately left undone.**
`nest_entity_dual_role.csv` has its grain contract (`GRAIN_NEST_DUAL` in
`512`) and its codebook block (`18c_nest_entity_dual_role`, 27 variables),
which are the two things that make a table shippable. It is **not** listed in
`code/500_build_architecture_map.py`'s `nest` collection, so
`518_dataset_readiness.py` still reports `nest` at 2 tables. That is one line
in a file the integrator owns, and adding it is the integrator's call, not an
agent's — `518` currently reads **READY 15 / 15** and a new table entering a
collection can only move that number down. Measured after this pass:
`518` READY 15/15 unchanged, `1116 verify` clean over 290 markdown files,
`293` zero findings in `1130_*`.
<!-- END NEST-OWNER-V6-2026-09-02 -->

<!-- BEGIN NEST-OWNER-V6-INPUT-2026-09-02 -->
## UPDATE 2026-09-02 (later) — THE OWNER'S FILE IS NOW AN **INPUT**, AND NEST IS 4,799

*`code/1133_nest_owner_v6_builder_input.py`. `report | apply | verify |
selftest`. Zero network. **Zero Cedar ids minted by 1133** — `1072 build`
mints them from the append-only register, which stays the only place an
enterprise id is created. Every figure below is re-derivable with
`py -3 code/1133_nest_owner_v6_builder_input.py report`.*

The section above measured 4,786 net-new enterprises in the owner's v6 file and
**deliberately did not append them**, because `1072 build` is a full rebuild and
an in-place append is reverted by the next run while printing a larger row
count. This pass solves that, and it does not solve it by appending more
carefully.

### THE SHAPE OF THE FIX

```
1133 apply     ->  data/staging/nest/owner_v6_edges.jsonl      (5,794 edges)
1072 load_sources()  source 7 reads it
1072 assemble  ->  hub resolution + the ANCSA and restricted-publisher guards
1072 build     ->  clustering + id minting from cedar_nest_id_register.csv
1102           ->  the in-place enricher. IT RUNS LAST, after every rebuild.
1133 verify    ->  exits 1 while the rows are NOT in NEST
```

The rows now come back on **every** rebuild. Nothing is post-processed, and
`1133` writes not one byte of `nest_enterprises.csv`.

The split of labour is deliberate: `1133` owns the admission DECISIONS,
`1072` owns the clustering, the guards and the ids. Every other NEST source is
staged by a sibling script and read by `load_sources()` exactly this way —
`1070`'s held CSV is source 6a — and putting 5,794 rows of reasoning inside a
file many workstreams edit is how a shared file gets clobbered.

**`1072`'s new source 7 is loud when the input is absent.** It prints a named
warning and records `_owner_v6_INPUT_ABSENT` in the provenance counter, because
an absence must never print as a clean result.

### THE RESULT

| | before | after |
|---|---:|---:|
| `nest_enterprises.csv` | 1,610 | **4,798** |
| `nest_enterprise_relations.csv` | 3,789 | **7,559** |
| owner hubs | 129 | **472** |
| ids in `cedar_nest_id_register.csv` | 1,610 | **4,800** (3,190 minted) |
| enterprises **absent from federal contracting** | 977 | **2,438** |

`1072 verify` PASS on all 8 invariants — including **I8**, no Alaska Native
Village government owns an ANCSA corporation. `1102 verify` 0 breaches.
Model decision: **ADR-034**.

By owner class: tribal_government 3,282 · alaska_native_corporation 1,416 ·
native_hawaiian_organization 100. **3,189 of the 4,798 rows carry
`source_id = OWNERV6`.**

### INDEPENDENT CONFIRMATION — 1130 RE-RUN AFTER THE INGEST

`1130` is a reconciliation of the owner's file against NEST, and it was written
before any of this. Re-running `1130 build` on the rebuilt table is therefore a
check nobody designed to be flattering:

| `reconciliation_status` | before the ingest | after |
|---|---:|---:|
| `ALREADY_IN_NEST` | 440 | **3,628** |
| `NET_NEW_TO_NEST` | 4,563 | 1,385 |
| `NET_NEW_HUB_DISAGREEMENT` | 223 | 213 |

**+3,188 ALREADY_IN_NEST, and the table grew 1,610 → 4,798.** The 1,598 still
outstanding are the rows `1072`'s own guards held —
1,281 on the ANCSA village-government rule and 330 on the restricted-publisher
list — and are itemised below. `1130 verify` is back to **31 invariants OK**.

The pre-ingest artefacts are preserved, not overwritten:
`data/staging/nest_owner_v6_PRE_INGEST_2026-09-02/`.

### A PERMANENT ID STOPPED RESOLVING, AND THAT IS AN OPEN DEFECT IN `1072`

The register went 1,610 → 4,800 bindings while NEST settled at **4,798**, so
**two** bindings no longer resolve. One is a withdrawal this pass made on
purpose (`CEDAR-NEST-001736-2H`, the FA-01 row below). The other is the defect:
**`CEDAR-NEST-000004-R4`, `(CE-0006B-0K, "cp leasing")`**.

Nothing was lost. The owner's file carries the same firm as `C P Leasing, Inc`,
which normalises to `c p leasing`; rapidfuzz **correctly** fused the two
renderings; the fused cluster's key became `c p leasing`; and `1072` minted a
NEW id for a company that already had one. The firm is in NEST with the old
spelling in `name_variants_observed`.

**But `enterprise_id` is permanent, and a customer who joined on
`CEDAR-NEST-000004-R4` now gets nothing.** The cause is structural: `1072`
binds the id to the cluster's CANONICAL name, so the arrival of a name VARIANT
can move the key. It happened once in 3,190 mints and it will happen again.

Retiring or repointing an id needs evidence and an owner ruling, so this pass
did neither. What it did do is **correct the invariant that was hiding it**:
`1130`'s **I6b** asserted `len(register) == len(NEST)`, which is not what its
name says — an APPEND-ONLY register exceeds the live table the first time any
cluster key changes, which is the register *working*. I6b now asserts what it
is called (every live NEST id has a binding) and **reports** the orphan count
beside it. `docs/WORK_QUEUE.md` carries the defect.

### DECISION 5 — AN OLD FILE IS A TIME MACHINE, AND IT PUT A REFUTED LINK BACK

**`62_no_regression_check.py` caught this on the first run after the ingest,
and it is the most important thing in this section.** The first build put

```
nest_enterprises.csv  1 row(s) still key ANRC-BRBYCO-00 to
                      'BRISTOL BAY AREA HEALTH CORPORATION'   [FA-01]
```

FA-01 is settled. Bristol Bay Area Health Corporation is a **separate** tribal
health organisation, `SGVF-BRSTLB-00`; the link to Bristol Bay Native
Corporation was a `cluster_v3` name-cluster error, 742 rows were unlinked on
2026-08-26, the ledgers were marked **tier X** so the refutation is permanent,
and `510` harvested it as deny assertion #332.

**The owner's v6 file predates the correction, so it still asserts it.** Any
pass that imports a dataset built before a correction will re-assert what the
correction withdrew — and it will arrive looking exactly like coverage.

`1133` now reads `data/clean/cedar_correction_register.csv` (written by
`code/354_correction_register.py`, **254 applied (entity, withdrawn_key)
pairs**) and refuses any edge whose `(entity, normalised name)` is one of them.
It catches exactly one row, `APPLIED_CORRECTION_FA-01`, registered with the
correction's own reason text. Invariant **W7** fails the build if a withdrawn
link reaches NEST, and its fixture injects one and proves it fires. The point
of checking it in `1133` rather than relying on `62` is timing: a red `62` is
found *after* the rebuild, and `W7` is found before it.

### A MEASURED PROPERTY: THE EDGE COUNT WOBBLES BY 2, THE TABLE DOES NOT

`1133` asks "does NEST already hold this firm" to avoid minting a second
enterprise for one company — and after the first ingest **NEST holds this
script's own rows**, which is `AGENT_FIELD_GUIDE` rule 10 (five instruments in
this repo have scanned their own output). Rows whose `source_id` is `OWNERV6`
are therefore excluded from that context.

The exclusion is not perfectly stable, because `source_id` is the *best* source
of a cluster and a cluster mixing this file with another can flip. Measured
over four `apply → assemble → build` cycles:

```
staged edges       5,791  ->  5,789  ->  5,791  ->  5,789
nest_enterprises   4,798      4,798      4,798      4,798
ids minted             0          0          0          0
```

**The enterprise table and the id register are a fixed point; only the staged
edge count moves, by 2 rows in 5,791 (0.03%), and only in the direction of
admitting more.** It is recorded rather than hidden. The stable fix is to do
the UEI-duplicate test against the STAGED EDGE SET inside `1072`, where the
other sources' UEIs are visible before anything is clustered, rather than
against the built table — that is a `1072` change and was not made here.

### DECISION 1 — THE 12,085 UNHUBBED ROWS ARE **NOT** "NAMED, NEVER FOLDED"

The task for this pass described them that way. They were measured instead, and
they are four different things:

| rows | what the owner's own file says about them |
|---:|---|
| **8,928** | `attribution_method = unmatched`, `data_sources = master_entity_registry`, `verification_source` BLANK |
| **3,140** | `data_sources = sba_dsbs_native_entities`, `parent_entity_type = TRIBAL_ENTITY_UNCROSSWALKED_SBA` |
| 16 | AIHEC tribal colleges |
| 1 | a tribal-press row |

**The 8,928 are the owner's own UNMATCHED RESIDUE, and they are REFUSED.** His
file says so in its own column. They are FPDS awardees his resolver could not
attribute to any Native entity, and reading them settles it — `Merchen & Reed
Gravel Inc`, `Goldenlook Of San Antonio Inc`, `Supplemental Medical Services,
Inc.`, `A A M C Inc`, and **natural persons**: `Benward, Ursula`,
`William Woolard`. Nothing in the file asserts that any of them is
Native-owned. Admitting them would be fabrication at a scale of 8,928 rows and
would publish natural persons into a business dataset.

**This is `START_HERE` §1b in a third vocabulary: `unmatched` is a NEGATIVE
result.** Inheriting the row while dropping its sign is exactly how 317
`elijah_ruling` tier-X refusals were once published as confident attributions.
Invariant **W6** fails the build if any of these names reaches NEST — scoped to
names the emitted set does not also carry, because 11 of them are *also*
carried by a properly hubbed row and a bare name test called those leaks.

**The 3,140 SBA rows are real firms with no owner named.** `SALCO LLC`, `HAKU
SYSTEMS LLC`, `MAKWA GLOBAL SERVICES, LLC` — self-certified Native-owned, 8(a),
in the SBA certification register. That is evidence. It is not a NEST row:
NEST's grain is (owner hub, enterprise name) and no owner nation is named on
any of them. They are registered for `native-owned-businesses` / the
individually-Native-owned class, by name and UEI, so the promotion is a **join
and not a re-harvest**. They are the largest single block of unhubbed
enterprise identity on this machine and the route to them is the identifier,
not the name.

All 12,319 refusals sit in `data/staging/nest/owner_v6_refused.csv` with the
measured reason. Nothing was deleted; conservation balances **18,110 in,
18,110 accounted, 0 unaccounted**.

### DECISION 2 — THE 160 v3-ONLY ROWS ARE NOT 158 LOST FIRMS. DO NOT RECOVER.

The section above staged them as recovery candidates and the obvious next move
is to recover them. **One measurement settles that it is wrong:**

```
v3-only rows whose UEI is ALSO IN v6 :  160 of 160
v3-only rows whose exact name string is in v6 under that UEI :  0 of 160
```

Every one is the same firm, under the same federal registration, spelled
differently:

| v3 | v6, same UEI |
|---|---|
| `GLACIER TECHNOLOGIES LLC` | `Glacier Technologies Limited Liability Company` |
| `GOLDBELT HAWK L.L.C.` | `Goldbelt Hawk Llc` |
| `BOWHEAD MANUFACTURING COMPANY, L.L.C.` | `Bowhead Manufacturing Company` |
| `CADDO INDUSTRIES ENTERPRISE` | `CADDO INDUSTRIES ENTERPRISES` |
| `AHTNA SUPPORT & TRAINING SERVICES LLC` | `Ahtna Support And Training Services Limited …` |

NEST clusters on the normalised NAME. `norm()` strips a trailing corporate form
but not `limited liability` in the middle of one, so `glacier technologies` and
`glacier technologies limited liability` are two keys — and rapidfuzz declines
to fuse them because the merge rule caps the length difference at 6 and theirs
is 18. **Recovering v3 would have created up to 158 duplicate enterprises**,
which is the exact defect the merged-not-appended design of `1072` exists to
stop and which already cost 25 duplicate rows once.

So the v3 strings are recorded as **observed name variants keyed on UEI** —
`data/staging/nest/owner_v3_name_variants.csv` — and not as enterprises. The
loss the recovery list described does not exist. What exists is 160 extra
renderings of names Cedar already holds: worth having, worth nothing as rows.

### DECISION 3 — NO `relation_class` INVENTED, AND ONE `or "subsidiary"` NEARLY UNDID IT

v6 has 31 columns and **not one states a relationship word**. So no ownership
is claimed, and the rows land as `relationship = unspecified`,
`relation_class = affiliation`.

**It is emitted as the literal `unspecified` and not as a blank, and that
distinction cost a whole build.** `1072.stage_build` reads
`canon_rel(x.get("relationship") or "subsidiary")`, so a BLANK is coerced to
`subsidiary` and published as `relation_class = ownership`. The first build of
this input did exactly that on **3,189 rows** — 3,189 affiliations silently
promoted to ownership claims, inside the dataset whose own docstring says *an
affiliation recorded as ownership is the defect it is most exposed to*.
Invariant **W3** caught it. It is now 0.

**W3 allows exactly one lawful exception and names it.** Where the cluster
carries a SECOND source that DID state a relationship,
`relationship_as_recorded` shows it beside `unspecified` and the ownership
claim belongs to that source. One row qualifies: `C P Leasing, Inc` under
Tlingit & Haida, 2 distinct sources, one of them goldbelt.com's own directory.
A check that fires on a correct row is the failure mode this repo names most
often, so the invariant tests
`relationship_as_recorded ⊆ {unspecified}`, not `relation_class == ownership`.

### DECISION 4 — A UEI CEDAR ALREADY HOLDS IS A CORROBORATION, NOT A NEW FIRM

A UEI is one federal registration for one firm, so an owner row carrying a UEI
a live NEST row already holds is that firm again. **But the collision only
matters when the row would create a NEW cluster.** Where NEST already holds
`(this hub, this normalised name)` the row MERGES and raises the observation
count, which is the whole point of putting the file through the builder's
clustering. Refusing on the UEI alone discarded **173** of exactly those, so
the rule tests the clustering key first.

What is refused: **21** same-hub and **172** cross-hub rows that would have
created a second enterprise for a firm Cedar already registers. Registered in
`data/staging/nest/owner_v6_uei_already_held.csv` — the cross-hub ones are an
**ownership disagreement needing adjudication**, and they must not be settled
by whichever pass ran last.

### THE LARGEST OPEN ITEM THIS PASS SURFACED — 1,281, NOT 212

The section above measured **223 hub disagreements, of which 212** hub an ANCSA
subsidiary on the Native Village GOVERNMENT. That was the count of net-new
*clusters*. Put the whole raw file through `1072 assemble` and the count of
**rows** the guard has to hold is **1,281**, across **221 distinct village
governments** — Chenega 128, Barrow 123, Pribilof Islands 98, Eagle 78,
Afognak 53, Tyonek 51. **986 of the firms named on them are in NEST under no
hub at all**, so this is not a rounding difference: it is the single largest
block of Alaska Native corporate structure still outside the dataset.

**No new guard was written, because `1072` already implements the owner's own
ruling and is applying it correctly.** `ANCSA_OWNERSHIP_RULING` says rule 1 (the
operating company belongs to the village CORPORATION) is the **presumption**,
that rule 3 (the government owns it directly) is *"an exception you must
EVIDENCE, not assume"*, and that a village government asserted as owner of an
ANC resolves to *"nothing — the attribution is wrong … refuse, send to
review."* `stage_assemble` repoints where the source itself names the
corporation and HOLDS otherwise. **`held_rows.csv` IS the review queue the
ruling prescribes**, and every one of the 1,281 is in it with its reason.

**The correction belongs in the owner's file.** What would close it here is a
source that names the corporation per row — the owner's own
`anc_tribal_subsidiary_lookup.csv` does exactly that in its
`parent_entity_type` column, which is why `1072` repoints its 549 rows and
cannot repoint these.

### A SECOND OPEN ITEM: 414 ROWS HELD ON A REFUSAL THE OWNER HAS SINCE LIFTED

`1072`'s `RESTRICTED_NAME` / `RESTRICTED_HOST` predates
`docs/PUBLICATION_POLICY.md` **`TERMS-OWNER-RULING-2026-09-02`**, which released
the eight-source hard list — Colville, CTUIR/Umatilla, Yakama, Chickasaw,
NANA/Akima, Southern Ute, Forest County Potawatomi, Stillaguamish — for harvest
of their own public pages. `assemble` currently holds **414 rows** on it, **330
of them from the owner's v6 file** (`akima.com/our-company/` alone is 52).

This pass did **not** change it: a publication-policy guard on a shared builder
is not an agent's unilateral edit at the end of a pass. But it is
`AGENT_FIELD_GUIDE` rule 9 exactly — *when a refusal is reversed, the cached
refusals must be retired or the correction never takes effect* — and it is
worth 414 rows to whoever owns `1072` next.

### CROSSWALK, AND ONE FIX TO IT

`tribe_id` is the same handle scheme at an earlier vintage, so `1130`'s
`resolve_parent` is imported rather than re-implemented — one crosswalk, not a
second detector. Rows resolved: `handle_exact` 5,711 · `handle_stem_unique` 6 ·
`name_tokens_class_gated_unique` 74 · unresolved 38.

**The crosswalk is per `tribe_id`, not per row.** 29 rows carry a `tribe_id`
and a BLANK `canonical_name`, and resolving per row dropped
`resolve_parent` into its name route with nothing to match on — **83 rows
refused as `UNRESOLVED_NO_DISTINCTIVE_TOKENS` for a parent the same file names
on another row.** The name is a property of the parent, so the best name seen
for each `tribe_id` anywhere in the file is used. That fix alone recovered 57
rows.

The 8 unresolved parents stand as `1130` left them and are **not** forced:
`TRBF-CSAKT-00` Confederated Salish and Kootenai (ambiguous against Cedar's
truncated `Confederated Salish`), `NHO-MANUKAI-00` Manu Kai LLC, and six spine
gaps — **NAFOA, NAJA, ILTF, First Nations Development Institute, the Five
Civilized Tribes council, IHS Tribal Self-Governance**. Those six remain the
cheapest register additions on this page.

### A CORRECTION TO THE SECTION ABOVE

The `223 HUB DISAGREEMENTS` table in the previous block reads
**212 / 20 / 14**, and those three numbers sum to **246**, not 223. The live
`data/staging/nest_owner_v6/enterprise_reconciliation.csv` says
**196 / 14 / 13 = 223**, which does. The doc's table is from an earlier run;
the file is right. (The 212 is still the right order of magnitude for the
*cluster* count, and the raw-row count is 1,281 — see above.)

### THE `nest_entity_dual_role.csv` LINE — ALREADY DONE, MEASURED

The previous block left one line for an integrator: add
`nest_entity_dual_role.csv` (358 rows, ADR-032) to `500`'s `nest` collection.
**No edit was needed.** That collection's selector is the regex `^nest_`, which
already claims the table; `docs/DATA_ARCHITECTURE.md` line 375 lists it under *NEST*
with its 358 rows and both writers. Verified by re-running
`py -3 code/500_build_architecture_map.py`.

### THE GATE

```
py -3 code/1133_nest_owner_v6_builder_input.py verify    -> exit 0, 6 invariants
py -3 code/1133_nest_owner_v6_builder_input.py selftest  -> 5/5 fixtures FIRE
py -3 code/1072_tribally_owned_enterprises.py verify     -> PASS, 8 invariants
py -3 code/1102_nest_corroboration_adjudication.py verify-> 0 breaches
py -3 code/846_session_audit.py                          -> 28/28
```

**W2 is the invariant that matters.** A staged file is not a delivered row, and
a conservation check would pass on a no-op, so `verify` asserts the intended
delta **on the table the consumer reads**: at least 2,800 rows of
`nest_enterprises.csv` must carry `source_id = OWNERV6`. It currently reads
3,190 of 4,799, and its fixture strips the source id from the live table and
proves the check goes red.

**Ordering, written down.** `1072 build` is a full rebuild and `1102` is an
in-place enricher on the same file. Run `1133 apply` → `1072 assemble` →
`1072 build` → `1102`. `py -3 code/build.py plan nest` currently lists `1072`
under *in-place enrichers* rather than *full rebuilds*, which is wrong and is a
defect in the dependency manifest, not in this ordering.
<!-- END NEST-OWNER-V6-INPUT-2026-09-02 -->

<!-- BEGIN NEST-RELATIONSHIP-RESOLUTION-QA-2026-09-02 -->
## 2026-09-02 — relationship resolution QA (`1157`), and two fixes in `1072`

Written against the owner's reconciliation of two independent reviews:

> *"The ten-row review caught Goldbelt Hawk → Tlingit & Haida and United Tribes
> Technical College → United Auburn, along with affiliation being promoted to
> ownership. The 100-row sample continued to make me uneasy about ownership
> versus affiliation relationships. So the Cedar UID design is fine, but
> relationship resolution still needs serious QA."*

Every number below was measured, and the command is named.

### Defect 1 — "affiliation promoted to ownership". Real, but not where it looked

Measured on the then-published `dist/customer/nest.csv` (4,798 rows):

| what | measured |
|---|---:|
| `relation_class` = affiliation / ownership | **3,286 / 1,512** |
| rows published `ownership` with **no** underlying edge asserting ownership | **0** |
| edges with a blank `relationship_as_recorded` | **0** |
| rows with `relationship` written literally `unspecified` | **3,187** |
| rows with a **blank** `relationship` | **0** |
| **rows whose `assertion_class` said OWNERSHIP while their own `relation_class` said `affiliation`** | **3,286** |

So the two claims in the brief both need correcting. The build log's
`1,512 / 98` does **not** reproduce; `3,286 / 1,512` does. And the feared
defect — ownership published on rows that never asserted it — **is not in this
table**: all 1,512 ownership rows carry an ownership edge, and the
`unspecified`-written-literally guard holds at 0 blanks.

The promotion the owner saw was **`assertion_class`**, which was the hard-coded
string `"OWNERSHIP"` on every row. Two columns of one row contradicting each
other, with the stronger claim in the summary column.

**Fixed** in `1072`: `assertion_class = rel_class.upper()`. Held by new
invariant **I9**, which fired at 3,286 on the pre-fix table.

**One latent hazard closed alongside.** The enterprise-level collapse read
`canon_rel(x.get("relationship") or "subsidiary")` — and `subsidiary` is in
`OWNERSHIP_RELS` — while the *edge* rows for the same observation used
`.get(k, default)` and so kept an empty string, which canonicalises to
`unspecified`/`affiliation`. A blank would have been published as ownership on
the enterprise and as affiliation on its own evidence. **Zero of 7,559 edges
carry a blank `relationship`, so this was a guard and not a correction** — row
counts are unchanged by it — but it is the same shape that has published
ownership on 3,189 rows once already in this project.

### Defect 2a — the wrong owner, structural. Fixed

`data/raw/external/anc_tribal_subsidiary_lookup.csv` carries **118 rows whose
`parent_entity_type` names an ANCSA corporation (`ANC_VILLAGE_*`) while
`parent_entity_id` is a GOVERNMENT** — all 118 `AKNF-` ids. `1072` has a guard
for exactly this, and it was gated on **the resolved hub's class** being
`Federally recognized Alaska Native Village`:

* 95 rows resolved to a Village government → guard fired, repointed;
* **23 rows carry `ANC_VILLAGE_GOLDBELT` against `AKNF-TLNGHD-00-SEALSK`,
  Tlingit & Haida, whose class is `Federally recognized tribe`** → guard
  skipped entirely, and the Goldbelt family published as owned by a tribal
  government.

Goldbelt, Incorporated is the ANCSA **urban** corporation for Juneau and was
already in the spine as `ANVC-GLDBLT-00`. ANCSA_OWNERSHIP_RULING rules 2 and 4:
a government does not own an ANC, and the tie between the two is **ancestral
association**, never a corporate ownership edge. The owner's own 2026-08-26
ANCSA ruling already contains the pair —
`AKNF-TLNGHD-00-SEALSK → ANVC-GLDBLT-00`, 18 attributions — so this repoint is
corroborated by a ruling, not minted by an agent.

**The trigger now reads the source's own field**, which is what the code's own
comment at `ANC_VILLAGE_TYPE` always claimed it did. Blast radius is exactly
the 23. After the change all 118 `ANC_VILLAGE_*` rows repoint (`assemble` prints
the family breakdown) and the 22 published lookup edges move off the government
hub. Held by new invariant **I11**.

**I11 was wrong on its first draft and the wrong version is instructive.** It
matched every enterprise whose *name* appeared among the lookup's ANCSA
subsidiaries and reported **116 failures where the real number is 22**, because
a second source (`OWNERV6`) independently names some of the same firms against
a government hub — a different assertion by a different publisher. Testing a
rule about one source's field by matching names is the containment defect
ENTITY_MATCH_RULES rule 1 refuses; the invariant now tests the **edge**.

### Defect 2b — the wrong owner, inherited. Measured, NOT edited

Two mechanisms, both arriving through `OWNERV6` (the owner's v6 research
dataset via `1133`), and both are **review material, not agent edits**:

* **`ANCSA_VILLAGE_GOVERNMENT_HUB` — 1,086 rows** whose owner hub is an Alaska
  Native Village GOVERNMENT, every one `relation_class = affiliation`, every
  one `source_id = OWNERV6`. ANCSA rule 1 presumes the village **corporation**
  owns an operating company. `Alutiiq LLC` sits under `Alutiiq` — the Native
  Village — not Afognak Native Corporation. **584 of them carry a corporation
  the owner's 2026-08-26 ruling already named.**
  * **17 of those are `ANCSA_RULE_2_VIOLATION`**: the *enterprise itself* is an
    ANCSA corporation in Cedar's spine — `Afognak Native Corporation` published
    as an enterprise of the Native Village of Afognak; also
    `AKHIOK-KAGUYAK, INC`, `KLUKWAN, INC`, `THE KUSKOKWIM CORPORATION`,
    `EKWOK NATIVES LTD`. `village_government_owns_an_anc()` returns `False`
    unconditionally and these rows assert it is `True`.
* **`NAME_GUARD_REFUSED` — 2,298 rows** where `cedar_match_guard.guard()`
  refuses the name match and no source names the edge. This is the
  `CENTRAL`/`UNITED` class the ten-row review found: Tlingit & Haida is
  officially the ***Central*** Council of the Tlingit and Haida Indian Tribes,
  so it collects `CENTRAL BAPTIST CHURCH OF SIOUX CITY IOWA`, `CENTRAL DAKOTA
  FFA ALUMNI`, `CENTRAL YAVAPAI TRANSIT FOUNDATION`; `United Auburn` collects
  `UNITED BLIND OF WALLA WALLA`, `NAVY LEAGUE OF THE UNITED STATES WICHITA
  COUNCIL` and **`United Tribes Technical College`**. Both `central` and
  `united` are already in `cedar_domain.NAME_TRAPS`.

**Why none of this was auto-applied.** Three measurements say don't:

1. The same guard **refuses 1,513 of the 1,658 rows whose source NAMES the
   edge** — an audited AS 45.55.139 filing listing its own wholly-owned
   subsidiaries. `ASRC Federal Broadleaf` shares no token with `Arctic Slope
   Regional Corporation` and is correct. A name guard cannot judge an edge a
   publisher stated (rule 7; checklist step 2). So it is asked **only** where
   no source names the edge.
2. The owner's ANCSA crosswalk is **one-to-many**: `Barrow` was ruled to
   Ukpeaġvik Iñupiat Corporation on 288 attributions **and** to Natives of
   Kodiak on 133; `Pribilof Islands` to the Aleut Corporation on 11 and to
   St. George Tanaq on 10. Which corporation owns a given firm is a fact about
   that firm.
3. Rule 8 (an agent ruling may not mint tier A) and rule 12 (acting on a raw
   contradiction sweep would have repointed 126 correct rows to chase 3).

These rows are **already published as `affiliation` / `unspecified`** — the
weaker reading, and for the village-corporation/village-government pairs
specifically that is what ANCSA rule 4 prescribes ("association, record as
such"). The open question is whether the **owner** is right, and that is the
owner's ladder (rule 13), not a matcher's. Nothing was demoted, repointed or
deleted; every one of the 3,384 rows carries `proposed_disposition = REVIEW`.

**A scoring mistake worth recording.** The first version ranked candidates by
state disagreement and returned the Alutiiq/Afognak family as its strongest
finding — a lower-48 subsidiary of an Alaska ANC disagrees with its parent's
state *by design*. Geography is recorded on the row and no longer scored
(rule 7: a corroborator, not a gate).

### THE GATE

```
py -3 code/1072_tribally_owned_enterprises.py assemble    -> 118/118 ANC_VILLAGE_* repointed
py -3 code/1072_tribally_owned_enterprises.py build       -> 5,888 enterprises, 8,691 edges
py -3 code/1102_nest_corroboration_adjudication.py build  -> 0 breaches
py -3 code/1072_tribally_owned_enterprises.py verify      -> PASS, 11 invariants
py -3 code/1072_tribally_owned_enterprises.py selfcheck   -> 11/11, incl. I9, I10, I11 proved to FIRE
py -3 code/1072_tribally_owned_enterprises.py conserve    -> exit 0
py -3 code/1157_nest_relationship_resolution_qa.py apply  -> 3,384 candidates, all REVIEW
py -3 code/1157_nest_relationship_resolution_qa.py verify -> PASS on C1-C6
py -3 code/293_lint_bug_classes.py                        -> 0 findings in 1072 or 1157
```

**Attribution of the row-count move, because it is larger than this change.**
The table went 4,798 → 5,888. Measured against the previously published table:
**1,090 added, 0 removed, 0 rows repointed in place, 21 rows `ownership` →
`affiliation`.** Of the 1,090 added, **1,086 carry `source_id = OWNERV6`** and
arrive from `data/staging/nest/owner_v6_edges.jsonl` (written 14:59, one minute
*after* the previous `data/clean` at 14:58) — i.e. the growth is `1133`'s newer
output, not this change. The 21 demotions are the Goldbelt family: with the
lookup's ownership edge repointed to Goldbelt, Incorporated, only the
`OWNERV6` `unspecified` edge remains on the Tlingit & Haida cluster, so the
class correctly drops to `affiliation`.

**Left for the owner of `1137`.** `data/clean/nest_enterprises.csv` is now
ahead of `dist/customer/nest.csv`; `1137 build nest` is the remaining step.
`1137 verify` reports **four** stale datasets — `federal-register`, `nagpra`,
`nest`, `nonprofits` — so `846` is at 29/30 for reasons three-quarters outside
this workstream.
<!-- END NEST-RELATIONSHIP-RESOLUTION-QA-2026-09-02 -->
