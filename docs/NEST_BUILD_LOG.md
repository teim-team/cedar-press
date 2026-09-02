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
carries 2,142 UEI rows worth $38.19B on quarantined methods with no exclusion
recorded, and `attribution_method` says who decided while `confidence_tier` says
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
