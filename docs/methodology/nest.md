# Methodology — NEST: Native Enterprise Structures and Ties

<!-- BEGIN GENERATED:IDENTITY -->

**`nest` — NEST: Native Enterprise Structures and Ties.** Delivered as `dist/customer/nest.csv`: **4,798 rows × 91 columns, 7.9 MB**, built from the flagship table `data/clean/nest_enterprises.csv`. Shelf `pro`; sold through **Cedar Press**; on the Cedar Press storefront. Readiness **READY**. [measured 2026-09-02 from the delivered file]

> **This block and Appendix M at the foot of this paper are GENERATED** by `code/1143_methodology_papers.py` from the delivered file itself, on every build — the same reason the codebooks are generated. Do not hand-edit either; the next build overwrites them.
>
> Everything between `<!-- BEGIN EDITORIAL:nest -->` and `<!-- END EDITORIAL:nest -->` is **hand-written and preserved byte-for-byte** across rebuilds. Put prose there and nowhere else.
>
> This paper is **not** the codebook. `dist/customer/nest__CODEBOOK.md` carries the grain, the folded-in tables and the per-column fill rates, and `__NOTES.txt` carries the same for a person. This paper says how the dataset came to exist and why you should believe it.
>
> Generated 2026-09-02. `py -3 code/1143_methodology_papers.py verify` **fails** if the delivered file has moved since — see §M7.

<!-- END GENERATED:IDENTITY -->

<!-- BEGIN EDITORIAL:nest -->
**`nest`. One delivered file, `nest.csv` — 4,798 rows × 91 columns, built from
`nest_enterprises.csv` (4,798 × 68) with `nest_entity_dual_role.csv` folded in
one-to-one and `nest_enterprise_relations.csv` (8,691 rows) counted rather than
joined.** [measured 2026-09-02]

*Written 2026-09-02. This is the methodology record: what was pulled and from
where, how the rows were made, how entities were attributed, what was decided
and why, what the known limits are, and how often it has to be re-pulled. It is
not the product copy (`docs/datasets/_descriptors.json`) and not the codebook
(`dist/customer/nest__CODEBOOK.md`, which carries the grain, the folded-in
tables and the per-column fill rates and is not repeated here).*

**A note on the figures.** `[measured 2026-09-02]` means the figure was
re-counted from the delivered file, `dist/customer/nest.csv`, or from the named
staging or spine artefact, on 2026-09-02, reading the whole file rather than
sampling. `[from the record — <doc>]` means it came from a build log, a
docstring or an ADR without independent measurement, usually because it
describes a historical state, a source's behaviour, or a decision rather than a
current count. Where a doc and the data disagreed, **the data won**; the
disagreements are listed at the end.

**Readiness: READY.** [measured — `docs/DATASET_READINESS.md`, regenerated
2026-09-02: `nest` READY, 2 tables, 2/2 grain, 2/2 keys, duplicates clean, 0
aggregation-unsafe, rebuild declared. The scoreboard counts 2 tables; the
architecture map counts 3, and that is in the stale-claims list.]

---

## The one thing to understand before any number in this dataset

**Most rows in NEST do not say that anybody owns anything.** The name commits
the dataset to two relations — *Structures **and** Ties* — and after the
2026-09-02 ingest of the owner's own enterprise file the ties are the majority:

| `relation_class` | rows | share |
|---|---:|---:|
| `affiliation` — a published tie that is **not** an ownership claim | **3,286** | 68.5% |
| `ownership` — a source stated that the hub owns this enterprise | 1,512 | 31.5% |

[measured 2026-09-02]

The mechanism is one column over. `relationship` reads the literal string
`unspecified` on **3,187 rows** [measured], because the source those rows come
from — `native_entity_enterprise_dataset_v6_geocoded.csv` — has 31 columns and
**not one of them states a relationship word.** No source said "subsidiary", so
NEST does not say it. Everything else in the vocabulary is somebody's stated
word:

| `relationship` | rows | class |
|---|---:|---|
| `unspecified` | 3,187 | affiliation |
| `subsidiary` | 782 | ownership |
| `wholly_owned` | 592 | ownership |
| `joint_venture` | 87 | **affiliation** |
| `majority_owned` | 85 | ownership |
| `operating_company` | 35 | ownership |
| `holding_company` | 15 | ownership |
| `shareholding_or_ancestry` | 7 | **affiliation** |
| `declared_suborganization` | 5 | ownership |
| `division` | 3 | ownership |

[measured 2026-09-02]

> ⚠ **`assertion_class` reads `OWNERSHIP` on all 4,798 rows and is not the
> column that answers this question.** [measured] It records which staging lane
> a row came down — the `1070` sweep split its harvest into `OWNERSHIP` and
> `RELATIONSHIP` and NEST took the ownership lane — and it has been constant
> since. Filtering on it returns the whole table. **`relation_class` is the
> column that says what was claimed.**

This matters more here than the equivalent caveat matters anywhere else in
Cedar, because the builder's own docstring names the failure the dataset is
most exposed to: *an affiliation recorded as ownership.* **It has already
happened once, at scale, inside this build.** The first ingest published
**3,189 affiliations as ownership claims** — `1072.stage_build` reads
`canon_rel(x.get("relationship") or "subsidiary")`, so a blank is coerced to
`subsidiary` and lands as `relation_class = ownership`. Invariant **W3** in
`1133` caught it; the fix was to emit the literal word `unspecified` rather than
a blank. [from the record — `docs/NEST_BUILD_LOG.md`, ADR-034] Today
`relationship = unspecified` and `relation_class = ownership` co-occur on **zero
rows** [measured]. The two columns are coherent in the other direction too: 3,187
of the 3,286 affiliation rows are `unspecified`, and the other 99 carry a stated
word that is deliberately not an ownership word, chiefly `joint_venture` (87)
[measured].

**A joint venture genuinely has two parents** (`ENTITY_MATCH_RULES` rule 11), so
it is never a subsidiary however the source files it. Sources write the same
idea half a dozen ways — `joint venture`, `joint_venture`, `holding company`, a
schema.org `subOrganization` — and **anything the vocabulary does not recognise
lands in `relationship_as_recorded` (34 distinct values against `relationship`'s
10) and is classed `affiliation`, the weaker reading, because guessing upward is
the direction that fabricates.**

**So the honest one-line reading of NEST is:** 1,512 rows where a named source
asserted that a Native nation, ANCSA corporation or NHO owns a named firm, plus
3,286 rows where a named source placed a firm under a Native owner without
saying on what terms. Both are useful. They are not the same fact.

### And the second thing: this is a structure table, not a money table

**There is no money column in NEST.** Not one of the 91 delivered columns holds
a dollar figure [measured — the numeric columns are `hierarchy_level`,
`n_source_observations`, `n_distinct_sources`, `n_auto_ruled_observations`,
`first_observed_year`, `last_observed_year`, `ownership_percent_stated`,
`fpds_declared_parent_observations`, `n_nest_enterprise_relations` and the
dual-role counts]. **`nest` does not appear anywhere in
`docs/MONEY_TOTALLING_RULES.md`** [measured 2026-09-02 — grepped; every hit is
the substring inside the word *honest*]. That absence is correct, and §5 says
what follows from it.

---

## 1. Sources

Every input was already on this machine when the build ran. **`1072`, `1073`,
`1130` and `1133` make zero network requests** [from the record —
`docs/NEST_BUILD_LOG.md` and each script's docstring]. That is
`docs/PULL_DISCIPLINE.md` tier 1 — re-read what you own before you pull — which
is why the acquisition story is mostly about *earlier* passes.

Seven source families reach the delivered table and each is visible on the row:

| `source_id` | rows | assertions | what it is |
|---|---:|---:|---|
| `OWNERV6` | **3,189** | 3,770 | the owner's own enterprise research dataset, v6 |
| `AS45.55.139` | 490 | **2,168** | Alaska audited annual reports, mined by `1072 mine` |
| `ANC_TRIBE_LOOKUP` | 363 | 441 | `anc_tribal_subsidiary_lookup.csv` |
| `shard-E` | 335 | 482 | the ANC subsidiary spiderweb shard |
| `CE701` | 187 | 210 | a nation's own "Our Companies" register |
| `SWEEP1070` | 128 | 297 | the ANC/NHO business sweep's held ownership rows |
| `shard-H` | 100 | 100 | NHO parent-declared lists with SBA DSBS identifiers |
| eight `TBD-*` registries | 6 | 91 | business-registry subsidiary directories |

[measured 2026-09-02 — rows from `dist/customer/nest.csv`, assertions from
`data/clean/nest_enterprise_relations.csv`]

The ranking inverts between the two grains, and that is the AS 45.55.139 source
working as designed: one filer names the same subsidiary in every year it files,
so 490 enterprises carry 2,168 assertions.

### 1.1 The AS 45.55.139 mine — the richest source, and the one bounded by statute

**Every ANCSA corporation meeting a statutory test files an audited annual
report with the Alaska Department of Commerce, Community and Economic
Development, Division of Banking and Securities, under Alaska Statute
45.55.139.** The report's *Principles of Consolidation* note enumerates the
wholly- and majority-owned subsidiaries **by legal name, in a document an
independent auditor signed**. That is ownership asserted by the parent, about
itself, under a filing obligation — the strongest evidence class available for
this family and better than anything derivable from SAM.

**How it was acquired.** Not by scrape and not by an open API. The Division's
STAR portal granted access to the owner personally — *"the ANCSA portal is live
and you are now able to view and retrieve documents on your own"* — and
`docs/ANCSA_PORTAL_BUILD_LOG.md` records the route in full, including the dead
end worth knowing: the root page's *Search ANCSA Filings* postback lands on a
**public-records-request intake wizard**, not a document index, and nothing was
submitted through it. That harvest indexed **19,269 documents**;
`code/1031_ancsa_45_55_139_annual_reports.py` pulled the annual-report subset to
disk. [from the record — `docs/ANCSA_PORTAL_BUILD_LOG.md`]

**What `1072 mine` read.** 524 documents — 358 village-corporation PDFs in
`data/raw/external/ancsa_portal_v3/` and 166 regional-corporation texts in
`data/interim/ancsa_txt/`. Shard E had read the regional half; **nobody had read
the village half.** Per-document outcomes, from
`data/staging/nest/ancsa_mine_log.csv` [measured 2026-09-02]:

| outcome | documents |
|---|---:|
| `NOTE_NAMES_NONE` — the note is present and enumerates nothing | **256** |
| `NAMES_FOUND` | **185** |
| `NO_TEXT_LAYER` | 58 |
| `EXCLUDED_TERMS_STATED_RESTRICTIVE:name:NANA Regional` | 25 |
| **total** | **524** |

Yield: **2,168 ownership assertions, 36 distinct parents, 540 distinct
child-name strings** (512 once normalised), split `wholly_owned` 1,850 ·
`majority_owned` 235 · `joint_venture` 83 [measured 2026-09-02 —
`data/staging/nest/ancsa_consolidation_edges.jsonl`].

**`NOTE_NAMES_NONE` is a finding, not a miss.** Afognak's 2017 note reads
*"...and its majority-owned subsidiaries (collectively, the Corporation), most
of which are limited liability companies."* The corporation has subsidiaries and
the audited statement declines to name them. Recording that as "no subsidiaries"
would be a false negative. [from the record — `code/1073` docstring]

**Five parser facts separate 36 corporations from 9, and every one was found by
reading the output rather than the code.** The two structural: **you cannot split
the note into sentences**, because every second name ends in `Inc.` and a
splitter cuts the list in half at the first one — the window is taken by
character count from the trigger phrase and closed by a named terminator; and
**you cannot split the list on commas**, because `Wetaviq, Ltd.` contains one —
names are matched with a company-FORM-anchored regex *over* the window, never
split *out* of it. The three found in output: Bristol Bay's note is a numbered
list and the markers were bleeding into names (`10.CCI Mechanical, LLC`);
`Talarik Research and Restoration, LLC` emitted as `Restoration, LLC` because the
lowercase connector broke the name run, so `ENTITY_MATCH_RULES` rule 1 — **a name
whose whole distinctive token set is one generic word is not a firm** — is
applied at *extraction*, not only at matching; and page furniture bleeds in
(`1 ANNUAL REPORT The Kuskokwim, Corporation` is a running header). [from the
record — `docs/NEST_BUILD_LOG.md`]

**The anti-fabrication rule here is absolute: every emitted name is a verbatim
substring of the source document by construction, and a name that does not
survive that test is dropped rather than corrected.**

**The coverage ceiling on this source is statutory, and no amount of collection
effort moves it.** From `docs/ANCSA_PORTAL_BUILD_LOG.md`:

- Filing is **conditional, not universal**. **60 of 196 roster entries (31%)**
  appear in the portal's own corporation dropdown, and the Division said so
  before the harvest started: the remainder are largely small village
  corporations that have never been filers.
- **HB 126, Chapter 37 SLA 26, signed 2026-06-24, effective 2026-06-25, narrows
  the filer population twice over.** Section 2 deletes the $1,000,000
  total-assets test outright and **re-anchors the 500-holder test in time** —
  from 500 or more *current* holders of record to 500 or more *original
  shareholders when the corporation was originally organized*. A village
  corporation whose roll grew past 500 through inheritance since 1971 but which
  enrolled fewer than 500 originally **is no longer a filer**. Expect the
  dropdown to shrink. **That is a statutory change, not data loss.**
- **The 13th Regional Corporation is absent from the dropdown.** Twelve of
  thirteen regionals are reachable here; do not claim all thirteen.

`docs/KNOWN_ISSUES.md` **A2** closes the obvious follow-up: the annual-report
corpus **cannot** substitute for an Alaska Division of Corporations pull. The 358
village reports come from **41** corporations and exactly **one** of the 95
undated tail entities is among them, because AS 45.55.139 exempts the small
village corporations — *which is the whole tail.* **Do not re-open this as a
mining task.**

### 1.2 The owner's own v6 enterprise file, which became an INPUT

    ~/Desktop/dissertation/data/tribal_federal_spending/clean/
        native_entity_enterprise_dataset_v6_geocoded.csv

**18,110 rows, 16,632 distinct normalised enterprise names, 658 distinct
parents** [from the record — `docs/NEST_BUILD_LOG.md`, `1130`], built by the
owner on this machine months earlier and the largest `ON_DISK_NOT_PROMOTED`
asset in the project. It supplies **3,189 of the 4,798 delivered rows (66.5%)**
[measured], which makes it by a distance the largest single contributor.

**Which version is authoritative, and why the answer is not "the newest".** The
task arrived asserting *"v5 matches v6"*. They do not. v5 and v6 hold the
identical 18,110 rows and the identical name universe and differ in **four
columns only** — `hq_city`, `hq_state`, `hq_zip`, `hq_county_geoid` — and in
every one v6 is the fix. **v5's `hq_state` is not a state:** on 11,390 of its
16,638 populated cells it is a 12-character UEI, and on 11,935 it is *this row's
own* `enterprise_uei`. v6 carries a two-letter code on all 14,629 and zero UEIs.
[from the record — `docs/NEST_BUILD_LOG.md` `1130` §1; preserved as a measurement
in `data/staging/nest_owner_v6/version_comparison.csv`, with invariants I13a/I13b
exiting 1 if either half stops being true] **v6 is authoritative; v5 must not be
read for geography.**

**The defect travelled, and finding where it came from changed the diagnosis.**
`data/spine/cedar_identifier_ledger.state` holds this row's own identifier on
**12,127** rows — the identical count to `hq_state` in the owner's v1, v2 and v3.
Two counts agreeing to the row is not coincidence: Cedar's identifier ledger was
built from a pre-v6 vintage and inherited the corruption. The NEST log calls it a
**column shift**; `docs/KNOWN_ISSUES.md` Lesson 3 subsequently measured the shift
width at **zero** and named the real cause —
`sam_extracts/build_master_entity_registry.py:126`, a pandas `agg` whose
missing-column fallback substitutes `awardee_uei` for
`recipient_location_state_code`. **A shift is a parser bug you fix once; a silent
column substitution produces a full column of plausible values and recurs on the
next renamed column.** The NEST log does not yet carry the correction.

**Why it is an INPUT and not an append.** `1130` measured 4,786 net-new
enterprises and **deliberately did not append them**, because `1072 build` is a
full rebuild: an in-place append is reverted by the next run while printing a
larger row count and looking like progress. This is the FERC collision —
`code/133` rebuilding `ferc_docket_filings.csv` reverted `code/168`'s in-place
entity links four times in one day — and it is the standing hazard in
`docs/START_HERE.md`. **ADR-034** settles it: the file becomes **source 7** of
`1072.load_sources()`, staged as `data/staging/nest/owner_v6_edges.jsonl` by
`1133 apply` (**5,791 edges** [measured]), so the rows are re-derived on every
rebuild and their ids stay bound by the append-only register. **`1133` owns the
admission decisions; `1072` owns the clustering, the guards and the ids; `1133`
writes not one byte of `nest_enterprises.csv`.**

**Source 7 is loud when it is absent.** `load_sources()` prints a named warning
and records `_owner_v6_INPUT_ABSENT` in the provenance counter if the staged file
is missing or empty, because an absence must never print as a clean result.
[measured — `code/1072_tribally_owned_enterprises.py`, source 7 block]

### 1.3 The other five families

- **`data/staging/anc_subsidiaries/shard_e.jsonl`** — 482 hand-adjudicated ANC
  parent-asserted edges from `code/531_shard_e_anc_report_mine.py`, 32 with a
  published CAGE, nearly all regional corporations. Evidence class is set per
  row: `audited_annual_report_as_45_55_139` where the source type says annual
  report, `parent_self_published_company_list` otherwise.
- **`shard_h.jsonl`** — 100 NHO edges, each with an SBA DSBS identifier. The only
  source reaching the NHO population, and it is the whole of it: `owner_class =
  native_hawaiian_organization` on exactly 100 delivered rows [measured].
- **`data/staging/tribal_enterprises/enterprise_register.jsonl`** — a nation's own
  "Our Companies" page, harvested by `code/701_enterprise_and_business_list_sweep.py`.
  **Accepted rows only** (210 of 293); the rest are held navigation furniture, a
  single generic word, or the Doyon joint-venture contradiction.
- **`data/raw/external/anc_tribal_subsidiary_lookup.csv`** — 549 parent-published
  company rows, the only source reaching lower-48 tribal governments at scale
  (Cherokee Nation Businesses, Salt River, Mille Lacs). It also carries the field
  that makes the Alaska guard repairable rather than merely blocking: a
  `parent_entity_type` naming the corporation (§3.3).
- **`data/staging/business_registry/*.jsonl`** — subsidiary directories only.
  **The selection is a structural predicate, not a hand-picked file list:** a
  source qualifies when it declares `directory_type = subsidiary_directory`
  **and** an ownership `identity_scope`. That predicate keeps **Calista's
  shareholder business directory** — 98 firms owned by individual shareholders at
  `identity_scope = shareholder_descendant_or_spouse` — out of a dataset that
  would otherwise assert the corporation owns them. The glob is `*.jsonl`, not
  `TBD-*.jsonl`, and the change was made rather than waived: a prefix filter
  silently omits any harvest filed under another convention, the shape of the
  deals-additions glob that omitted 131 rows. **The selection predicate belongs
  on the row.**

### 1.4 What was deliberately not used

- **`cedar_identifier_ledger_final.csv` was refused wholesale as an identifier
  source.** Nothing in NEST is inherited from it. It carries **227,540 rows worth
  $45,932,912,319** on quarantined methods with no exclusion recorded —
  `uei_exact` 172,338 / $38,191,057,346 + `cage_exact` 14,149 / $7,252,015,101 +
  `parent_uei` 41,055 / $489,839,872, measured disjointly across all three legs
  `40_build_prime_contracts.py` actually tries. [from the record —
  `docs/QUARANTINE_EXPOSURE_LOG_2026-09-02.md`] The earlier figure of 2,142 rows
  / $38.19B is **SUPERSEDED** — it measured **one leg of a three-leg join**,
  and the CAGE leg is where
  the problem lives. **Scoping a measurement to one leg of a multi-leg join
  understates it silently, because the legs it skipped answer the same question.**
- **The literal string `NAN` is suppressed as a CAGE code.** It sits in
  `cage_code` on 2,196 upstream rows across 2,193 UEIs.
- **D&B-derived recipient addresses are not used.** `IDENTIFIER_STANDARD` §4
  forbids their bulk dissemination and they attach to every base award dated
  before 2022-04-04. A licence restriction, distinct from terms and from consent,
  and the reason NEST carries city and state and **no street address anywhere**.
- **`cedar_constellation_edges.csv` is read and never written.** ADR-014's
  constellation records **service** relationships — who serves a community,
  including `registered_with` for a TERO-certified firm. NEST records ownership.
  A TERO-certified firm is a constellation edge and is **not** a NEST row unless
  the nation also owns it; where a NEST enterprise does match one, its `edge_id`
  rides in `constellation_edge_id` so the corroboration is visible instead of the
  relationship being rebuilt under a second name — **41 rows** [measured]. **The
  near-zero overlap is the evidence that the scope split is real:** the
  constellation's unkeyed from-sides are clinics, schools and service
  organisations; NEST's are operating companies. **NEST does not close the
  constellation's name-only backlog**, and a pass that tries should know that
  before it starts.
- **`native_owned_businesses.csv` is a different relation and the two must never
  be merged.** There a row says a nation *certified or listed* this firm, with an
  `identity_scope` gradient running down to `vendor_relationship` — no ownership
  claim at all. Flattening that gradient into an ownership claim is what
  `docs/PUBLICATION_POLICY.md` refuses, and a firm on a list whose bar is
  *shareholder descendant or spouse* is not a tribally owned firm.

### 1.5 Terms of use, and the ruling that changed the answer mid-build

Sources marked `TERMS_STATED_RESTRICTIVE` were excluded from NEST **by every
route** — the publisher's page, its WordPress media API, the Wayback Machine, and
any harmonised derivative of data an earlier pass already fetched — matched on
both the asserting parent's name and the source host. The guard is
`RESTRICTED_NAME` / `RESTRICTED_HOST` in `1072 assemble` and it holds **414 rows**
[measured — `held_rows.csv`].

Three rulings in `docs/PUBLICATION_POLICY.md` bear on that, all made 2026-09-02,
the day this dataset was built.

**`TERMS-SCOPE` — a restriction is scoped to the SOURCE that stated it, not to
the nation.** The gaming harvest had excluded the entire Navajo Nation because
one Navajo host is recorded restrictive; the casinos sit on other hosts. *"That
is over-compliance, and it misrepresents the publisher."* A restriction attaches
to the **host and path** where the terms were found and does not propagate to
other hosts operated by the same entity, nor between a subdomain and its apex
unless the terms say so.

**`TERMS-METHOD` — a clause can restrict the ROUTE rather than the source or the
content.** `navajo-nsn.gov/Terms` says *"You may not obtain or attempt to obtain
any materials or information through any means not intentionally made available
or provided for through the Navajo Nation Web Sites."* That forbids neither
reading the site nor any content — it forbids the unlinked WP-REST index, the
sitemap walk and the custom-post-type sweep, and `980.METHOD_RESTRICTED_HOSTS`
honours it by dropping those routes and not the host. **Ask what the clause
restricts: the source, the content, or the method. Only the first justifies
excluding a host.**

**`TERMS-OWNER-RULING-2026-09-02` — the eight-source hard list is released.**
Confederated Colville, CTUIR/Umatilla, Yakama, Chickasaw, NANA/Akima, Southern
Ute, Forest County Potawatomi and Stillaguamish are released for harvest of
**their own public pages**; the owner ruled that a tribal website's terms
language does not block harvest and that he carries the publication risk. The
recorded quotes keep their value as the *observation* of what each publisher
stated; they are no longer the gate. **What the ruling did not touch, none of it
a terms question:** technical access controls; **a natural person's data apart
from their public role** — the business row may be harvested, `owner_name_raw` /
`email` / `phone` / `address_raw` may not be published; EMMA/MSRB with CUSIP
Global Services as a second licensor; and Casino City and D-U-N-S.

**NEST's guard predates the ruling and still enforces the old answer** — 414 held
rows on a refusal that has been lifted. §4.2.

---

## 2. How the rows were built

> ⚠ **Script numbers are not unique in this project.** Cite the filename. Every
> script named below was confirmed present in `code/` on 2026-09-02.

1. **`code/1031_ancsa_45_55_139_annual_reports.py`** — pulled the AS 45.55.139
   PDFs from the STAR portal into `data/raw/external/ancsa_portal_v3/` and
   extracted a text layer with PyMuPDF plus per-page tesseract at 300 dpi. **The
   only network-bearing step in the chain**, and it ran before NEST existed.
2. **`code/1073_ancsa_consolidation_subsidiaries.py`** — the WORKSTREAM
   NBOA-EXPAND prototype that established the *Principles of Consolidation*
   route, the `wholly_owned` / `majority_owned` / `equity_or_jv` gradient, and the
   `NOTE_PRESENT_NAMES_NOT_STATED` outcome. Origin of the parser rules in §1.1 and
   of two hard refusals in its docstring: *it will not read a name out of a URL
   slug or a filename, and it will not accept a candidate with no corporate
   suffix.*
3. **`code/1070_anc_nho_business_sweep.py`** — swept 822 entities (all 191 ANCs,
   all 210 NHOs, 365 tribal governments `701` never reached, all 56 intertribal
   organisations), staged 1,106 rows in the 58-column `native_owned_businesses`
   schema, and **held the 583 OWNERSHIP rows for NEST** while the 523
   `RELATIONSHIP` rows went to the business file. §2.1.
4. **`code/1072_tribally_owned_enterprises.py`** — the builder.
   `mine | assemble | build | codebook | conserve | verify | selfcheck`. `mine`
   reads the 524 documents, flushing per document. `assemble` runs
   `load_sources()` over all seven families, applies hub resolution and the four
   guards of §3.3, and splits the result into `ownership_edges_staged.jsonl`
   (**7,976**) and `held_rows.csv` (**1,712**) [both measured]. `build` clusters
   on `(owner_hub_cedar_uid, enterprise_name_normalized)`, mints an
   `enterprise_id` per cluster from the append-only register, and writes both
   clean tables.
5. **`code/1130_nest_owner_v6_reconcile.py`** — `versions | build | codebook |
   verify | selftest`. Established that v6 is authoritative, crosswalked the
   owner's 658 parents onto Cedar handles, and built
   **`nest_entity_dual_role.csv`** (ADR-032). **It mints zero enterprise ids and
   writes nothing into `nest_enterprises.csv`**; invariant **I6** asserts it
   appears on 0 rows of the id register.
6. **`code/1133_nest_owner_v6_builder_input.py`** — `report | apply | verify |
   selftest`. Turns the owner's file into source 7. Admission decisions in §4.
   **Zero ids minted.**
7. **`code/1102_nest_corroboration_adjudication.py`** — **the in-place enricher,
   and it runs LAST.** Adds the FPDS corroboration family (§3.4), the
   duplicate-name-variant flags, and the Chugach adjudication.
   `code/1098_entity_rel_counterparty.py` and
   `code/1081_stale_tail_dated_facts.py` also touch the file in place [from the
   record — `docs/ARCHITECTURE.md` line 374 lists all four writers].
8. **`code/1137_customer_dataset_combine.py`** — builds `dist/customer/nest.csv`
   by folding `nest_entity_dual_role.csv` in one-to-one on `cedar_uid` (22
   columns) and **counting** `nest_enterprise_relations.csv` rather than joining
   it (one column). 68 + 22 + 1 = the 91 delivered columns [measured].

**Shared files touched additively, each with a backup:** `cedar_ids.py` (one
prefix), `cedar_domain.py` (one `PROMOTED_TABLE_PRODUCERS` entry), `500`, `512`
(`GRAIN_NEST`, `GRAIN_NEST_DUAL`), `518`, `526`,
`docs/datasets/_descriptors.json`, and `codebook_master.csv` (**appended** 81 + 27
rows, never rewritten). **Nothing was written to the spine's entity register, to
`cedar_constellation_edges.csv`, or to `native_owned_businesses.csv`.**

### 2.1 The `1070` handoff was a MERGE, not an append

583 ownership rows arrived from the sweep. A plain append would have been wrong
on a third of them: the integrator measured **170 of the 583 already present in
NEST by normalised name** before splitting them, and 265 come from the *same* 358
audited reports `1072` mines itself. So they are fed through the same clustering
as every other source, and a restatement of a firm NEST already holds raises that
enterprise's `n_source_observations` instead of creating a second row.

```
held for NEST                                        583
  refused: unreviewed HTML heading/anchor scrape     229
  refused: shareholder-owned, not corporation-owned   57
  ingested                                           297
    merged onto an enterprise NEST already held      167
    net new enterprises                              128
```

[from the record — `docs/NEST_BUILD_LOG.md`. The two refusal counts reproduce
exactly against `data/staging/nest/sweep_1070_refused.csv`, 286 rows, and the 128
net-new reproduces as `source_id = SWEEP1070` on 128 delivered rows [measured]]

**Both refusals rest on the staged file's OWN declared caveat, not on a judgement
about the firm.** The 229 were flagged by the sweep itself as
`HEADING_SCRAPE_ON_A_DIRECTORY_INDEX` with a `verification_basis` ending *"not a
table; review before resolving"* — and it was right: ASRC's block alone yields
`Blank`, `No Results Found`, `Employee Resources`, `Software, Apps & Analytics`
**and seven natural persons' names scraped off a leadership page.** A natural
person's name may never enter this dataset, which makes this a hard rule rather
than a quality preference. The 57 are Bering Straits'
`shareholder-owned-businesses` directory at `identity_scope =
shareholder_descendant_or_spouse` — an ownership claim about a **person**, not
about the corporation, and identical in shape to the Calista directory the
source-selection predicate already refuses. **The same trap arriving by a second
route is why the refusal is a predicate on `identity_scope` and `directory_type`
rather than a note about one corporation.** A third guard —
`association_member` / `tribally_owned_entity_of_a_member_nation` — is written
and has not fired: USET lists *Choctaw Fresh Produce*, which **is** tribally
owned, by **Mississippi Choctaw** and not by USET, the keyed authority, and the
hub must be the owning nation or the row does not exist.

**Every refusal keeps its full 58 staged columns plus a `nest_refusal` sentence**,
so any of it can be reversed without re-harvesting. **A refusal that leaves no
trace is indistinguishable from a row nobody noticed.**

### 2.2 The gate

```
py -3 code/1072_tribally_owned_enterprises.py verify      -> exit 0, 8 invariants
py -3 code/1072_tribally_owned_enterprises.py selfcheck   -> 8/8 PASS
py -3 code/1133_nest_owner_v6_builder_input.py verify     -> exit 0, 6 invariants
py -3 code/1133_nest_owner_v6_builder_input.py selftest   -> 5/5 fixtures FIRE
py -3 code/1130_nest_owner_v6_reconcile.py verify         -> exit 0, 31 invariants
py -3 code/1102_nest_corroboration_adjudication.py verify -> 0 breaches
py -3 code/293_lint_bug_classes.py                        -> 0 findings in 1072_*, 1130_*
```

[from the record — `docs/NEST_BUILD_LOG.md`]

**Six of `1072`'s eight invariants are proved to FIRE** by injecting the
violation into a copy of the live file, asserting exit 1 *and* that the named
invariant is what fired, then restoring and asserting exit 0 again. **A check
that has never failed on purpose is not known to work.**

| | invariant | proved to fire |
|---|---|---|
| I1 | `enterprise_id` unique, valid `503_identity` check characters | ✓ |
| I2 | every owner hub is in the spine register | ✓ |
| I3 | every row carries a source — **an ownership claim with no source is the one row this dataset may not contain** | ✓ |
| I4 | no row's owner is a refused publisher | ✓ |
| I5 | level ≥ 2 implies a resolvable parent; no enterprise is its own ancestor | ✓ |
| I6 | edges and enterprises conserve in both directions | — |
| I7 | `in_federal_contracting` is `Y` or `N`, never blank | ✓ |
| I8 | no Alaska Native Village government owns an ANCSA corporation | — |

Two invariants elsewhere matter for what they assert rather than what they check.
**`1133` W2 asserts the intended DELTA on the table the consumer reads**, not a
conservation identity — at least 2,800 rows must carry `source_id = OWNERV6`,
because a staged file is not a delivered row and a conservation check passes on a
no-op. It currently reads **3,189 of 4,798** [measured]. And **`1130`'s selftest
includes a fixture in which an EMPTY reconciliation reads as FAILURE, not
success.**

### 2.3 Row conservation

```
edges kept by assemble   data/staging/nest/ownership_edges_staged.jsonl   7,976   [measured]
edges held by assemble   data/staging/nest/held_rows.csv                  1,712   [measured]
                                                                        -------
                         raw assertions reaching assemble                 9,688

relations rows built     data/clean/nest_enterprise_relations.csv         7,559   [measured]
enterprises built        data/clean/nest_enterprises.csv                  4,798   [measured]
sum of n_source_observations across the delivered file                    7,559   [measured]
```

The last line is the one to keep: **`n_source_observations` sums to exactly the
relations row count**, which is the property that makes the two grains
reconcilable. The 417-row gap between staged edges and relations rows is collapse
within `(enterprise, source, document, edition)` — the relations table's declared
grain [from the record — `docs/DATASET_CONTRACTS.md`].

On the owner's file, from `data/staging/nest/owner_v6_conservation.csv` [measured
2026-09-02]:

```
owner v6   18,110 rows in   18,110 accounted   0 unaccounted
  EMITTED                                       5,791
  refused, nine named dispositions             12,319   (itemised in §4.3)
owner v3   19,846 rows in   19,846 accounted   0 unaccounted
  v3_name_also_in_v6                           19,682
  v3_only_name_uei_present_in_v6                  160
  v3_blank_name                                     4
```

---

## 3. How entities were attributed

### 3.0 NEST does not carry a column called `attribution_method`, and that is deliberate

`docs/schema/attribution_method_vocabulary.json` states the problem in its own
`why` field: *"`attribution_method` is three different columns sharing a name — a
join method, an evidence provenance, and a name-match algorithm. Each table is
gated against its OWN vocabulary."*

| sense | example table | example terms |
|---|---|---|
| **a join method** | `prime_contracts.csv` | `uei_exact`, `cage_exact`, `parent_uei` |
| **an evidence provenance** | `cedar_assertions.csv`, `cedar_identifier_ledger.csv` | `elijah_ruling`, `web_verified`, `unmatched` |
| **a name-match algorithm** | `native_entity_lobbying_disclosures.csv` | `core_token_set`, `exact_normalized_skeleton`, `contains_canonical` |

**None of the three appears in NEST under that name.** `attribution_method` is
not among the 91 delivered columns, nor the 68 of `nest_enterprises.csv`, nor the
25 of `nest_enterprise_relations.csv`, nor the 27 of `nest_entity_dual_role.csv`
[measured 2026-09-02]. NEST splits the senses into separately named columns:
**`hub_resolution_method`** carries the *join method* (how the row reached its
owner hub), **`evidence_class`** carries the *evidence provenance* (what kind of
document asserted it) — both in §3.2 — and ten `*_basis` / `*_note` columns carry,
per field, the sentence saying which lookup answered.

**Where the third sense does bear on NEST it arrives from outside, on the owner's
file, and it arrives as a NEGATIVE.** `attribution_method = unmatched` on 8,927 of
his v6 rows is his resolver reporting that it could **not** attribute the firm to
any Native entity — the `cedar_identifier_ledger.csv` sense of the word, an
evidence provenance, where `unmatched` carries 9,569 rows. §4.3 covers what NEST
did with them.

### 3.1 `enterprise_id` is a sub-hub id, and an enterprise is never a spine entity

```
CEDAR-NEST-000123-K7
│          │      └─ two 503_identity check characters, two independent
│          │         weightings: 100% of single substitutions and 100% of
│          │         adjacent transpositions caught
│          └─ ordinal, allocated under an exclusive file lock
└─ enterprise sub-hub
```

`docs/IDENTIFIER_STANDARD.md` §2 is the model. **The entity is the hub**;
everything associated with it hangs off the Cedar ID. **Sub-hubs exist where a
thing is complex enough to deserve its own record and its own children** — a
casino is the worked example, with capacity observations, employment
observations, property locations, financing events and licences of its own *and*
a parent entity. Flattening it onto the entity would lose the level at which most
of the facts are true. The implemented sub-hubs are `facility_id`, `property_id`,
`np_ein_entity_hub`, the FERC docket filer layer, `CEDAR-PLACE-` (ADR-030) — and,
since 2026-09-02, `CEDAR-NEST-`.

**ADR-020 settles what that means for joins.** `cedar_nest_id_register.csv` is
**the enterprise level of the existing sub-hub layer, exactly as `facility_id` is
the facility level. It is not a parallel entity space, it may never be joined as
if it were one, and a `CEDAR-NEST-` id may not appear where a `cedar_uid` is
expected.** The relation to the spine is already fully expressed by
`owner_hub_cedar_uid`, populated on **all 4,798 rows** and taking **472 distinct
values, every one a spine entity** [measured]; nothing further needs minting. Two
other prefixes were rejected and the reasons are the model: a `CE-` uid would put
a non-entity into the entity namespace, and a `CEDAR-ENT-` id would file a
*tribally* owned company under the *individually* Native-owned class.

**Hierarchy is not encoded in the id, on purpose.** `IDENTIFIER_STANDARD` §2:
*"Corporate parentage is genuinely ambiguous… If you find yourself wanting to
change an entity's id because its ownership changed, you want a relationship edge
instead."* So every row carries **both** `owner_hub_cedar_uid` (the nation at the
top, always a spine entity) **and** `parent_enterprise_id` (the immediate owner,
which may itself be an enterprise). Measured: `hierarchy_level` 1 on 4,668 rows,
2 on 128, 3 on 2; `parent_is_hub = Y` on 4,668 and `N` on 130.

**The binding is append-only and that is what makes the key joinable.** The
register maps `(owner hub, normalised name)` → `enterprise_id` and the build
reads it first. Without it, `allocate()` would hand out a new ordinal on every
run and **every rebuild would silently re-key the dataset** — defect class 7 in
`293`, and the one that quietly breaks a customer's join. A second `build` minted
0 ids and produced identical keys [from the record]. The register holds **4,800
bindings** against 4,798 live rows [measured]; the two orphans are §6.

**A hub is not its own subsidiary.** `The Eyak Corporation` against the spine's
`Eyak Corporation`, and `Coushatta Tribe of Louisiana` against the spine's
deliberately short `Coushatta`, each made a company the parent of itself and
published as a level-2 chain that was really one company twice. The build now
tests the child against *every* deterministic rendering of the hub's name, and
the residue is zero. This is also why ADR-032 puts the dual role in its own table
rather than adding a self-row: a self-row would break the key.

### 3.2 How a row reached its hub, and what asserted it

| `hub_resolution_method` | rows |
|---|---:|
| `source_supplied_cedar_uid` — the source named the Cedar entity outright | **3,939** |
| `exact_normalized_name` — one, and only one, spine entity matched | 498 |
| `source_supplied_handle` — the source carried a live Cedar handle | 263 |
| `ancsa_village_government_repointed_to_corporation` — the Alaska guard, §3.3 | **83** |
| `accent_and_form_folded_name` | 15 |

| `evidence_class` | enterprises | assertions |
|---|---:|---:|
| `federal_certification_registry` | 1,399 | 1,489 |
| `owner_research_dataset_resolver_output` | 1,279 | 1,420 |
| **`audited_annual_report_as_45_55_139`** | **861** | **2,788** |
| `parent_self_published_company_list` | 504 | 970 |
| `owner_research_dataset_hand_ruling` | 420 | 440 |
| `nation_self_published_enterprise_register` | 193 | 301 |
| `parent_declared_subsidiary_list` | 100 | 100 |
| `compiled_third_party_directory` | 42 | 51 |

[both measured 2026-09-02]

**Read the two `owner_research_dataset_*` classes with care.** 1,699 delivered
rows — 35.4% — rest on a class that names a *resolver output* or a *hand ruling*
inside somebody's research file, not on an observer who saw the relationship.
That is honest labelling and it is also the largest quality gradient in the table.

**Identifiers are published, never inferred.** `uei` and `cage_code` are filled
**only where a source published them**: `uei` on 2,504 rows (2,497 distinct),
`cage_code` on 634 [measured]. A name that happens to match a UEI in an external
extract is a **candidate** and lives in `uei_candidate` — 466 rows, each carrying
a `uei_candidate_basis` saying it is an exact-name proposal into the SBA DSBS
extract and weaker than an identifier. `identifier_status` splits
`external_identifier` 2,509 / `cedar_minted_only` 2,289 [measured]. **The
exactness of the key says nothing about the correctness of the link.**

**`address_basis` had to be fixed before it could be believed, and the defect is
this repo's signature shape.** The first version labelled all 623 SBA DSBS hits
*"keyed on UEI"* because it tested membership *after* the fallback chain had run
— 623 rows claiming an identifier key when only 102 rows carried a UEI at all.
**A field that does not measure its own name.** It now reports which lookup
answered [measured 2026-09-02]:

| `address_basis` | rows |
|---|---:|
| the parent's own subsidiary listing | 1,979 |
| SBA DSBS, matched on a **candidate** UEI (an exact-name proposal) | 466 |
| SBA DSBS, matched on a **published** UEI | 16 |
| none | 2,337 |

**City and state only. No street address anywhere** — §1.4 says why.

### 3.3 The four guards

**Guard 1 — restricted publishers, refused by every route. 414 rows held**
[measured], matched on both the asserting parent's name and the source host:
NANA Regional 160 · Chickasaw 121 (plus 2 on host) · Umatilla 38 · Colville 33 ·
Yakama 31 · Forest County Potawatomi 19 · Stillaguamish 4 · Southern Ute 3, plus
3 uppercase-variant rows. **84 come from `ANC_TRIBE_LOOKUP` and 330 from the
owner's v6 file** [measured]. §4.2.

**Guard 2 — the Alaska village-government guard.** `ANCSA_OWNERSHIP_RULING` rule
2 and `cedar_domain.village_government_owns_an_anc()` (which always returns
`False`): **a Native Village *government* does not own an ANCSA corporation.**
`anc_tribal_subsidiary_lookup.csv` violates that on 45 rows and **says so
itself** — `parent_entity_type` reads `ANC_VILLAGE_UIC` while `parent_entity_id`
is `AKNF-…`, the Native Village of Barrow's *government*.

**The repoint is read out of the source's own field, never guessed.** The
corporation named in `parent_entity_type` is matched by name, then by name-prefix
among ANCSA classes **with a five-character floor so an acronym can never win
that way**, and only then against a named acronym exception (`UIC` →
`ANVC-KPVKPT-00`, Ukpeaġvik Iñupiat Corporation). **Where the corporation is not
uniquely in the spine the row is HELD, not attached to the government** —
`hub_resolution_method = ancsa_village_government_repointed_to_corporation` on
**83 delivered rows**, against `hold_class = ANCSA_VILLAGE_GOVERNMENT` on **1,281
rows across 221 distinct village governments** in `held_rows.csv` [both
measured]. Holding is the ruling's own prescription, not a cop-out: rule 1 (the
operating company belongs to the village **corporation**) is the **presumption**,
rule 3 (the government owns it directly) is *"an exception you must EVIDENCE, not
assume"*, and a village government asserted as owner of an ANC resolves to
*"nothing — the attribution is wrong … refuse, send to review."* **`held_rows.csv`
IS that review queue**, and every one of the 1,281 is in it with its reason on the
row. §4.8.

**Guard 3 — a named firm that resolves to a Cedar hub, triaged three ways.**
Reading a subsidiary list at face value converts independent entities into
somebody's subsidiaries. But the naive version of this guard **held Ho-Chunk,
Inc. and lost the row**, which is the opposite error.

- **The child resolves to a GOVERNMENT-class hub → a NAME COLLISION, not a hub
  identity.** A government is not a corporation and can never *be* somebody
  else's subsidiary. `Ho-Chunk Inc` matches the spine's `Ho-Chunk` only because
  `norm()` strips `Inc`, and `Ho-Chunk` is the **Ho-Chunk Nation of Wisconsin**
  while Ho-Chunk, Inc. is the **Winnebago Tribe of Nebraska's** holding company.
  Two tribes, one word. The edge is kept, keyed to its real publisher, and the
  collision is recorded on the row so the next reader does not re-litigate it.
- **Both sides are ANCSA corporations → DOWNGRADED to a tie, not dropped.**
  Doyon's own page names *Huna Totem Corporation*; Bristol Bay's names
  *Choggiung Limited*; Tozitna's report names *Doyon, Limited*. Rules 4/5 make
  these shareholding or ancestry, never ownership, so the row survives at
  `relation_class = affiliation` — **7 rows** [measured].
- **Anything else → the enterprise IS an existing Cedar entity**, and the row
  carries its uid in `enterprise_existing_cedar_uid` rather than pretending it is
  new. **67 rows, 64 distinct uids** [measured] — *Citizen Potawatomi Community
  Development Corporation*, *Alaska Growth Capital BIDCO*.

**Guard 4 — uniqueness is required on every name resolution.** A name matching
two spine entities resolves to neither (rule 13). That is what keeps `Cherokee` —
45 spine entities, three of them federally recognized tribes — from resolving to
anything at all.

### 3.4 Corroboration: a fourth evidence family that was already on disk

`docs/ASSERTION_LAYER.md` measured that every fact in Cedar rests on exactly one
source. NEST is one of the few places that is partly untrue:

| `n_distinct_sources` | 1 | 2 | 3 | 4 | 5 |
|---|---:|---:|---:|---:|---:|
| enterprises | **4,038** | 630 | 95 | 24 | 11 |

[measured 2026-09-02 — **760 of 4,798 (15.8%) rest on more than one source**]

**But a source count is not a family count, and `docs/KNOWN_ISSUES.md` §2 says
so:** *"`nest_enterprises.n_distinct_sources = 438` is not 438 corroborations…
The gap is one filer's AS 45.55.139 report across several fiscal years: three
documents, one observer. A buyer can reasonably read 438 as corroboration. It
should ship beside an `n_independent_families` column."* **That column does not
exist in the delivered file** [measured] and the warning stands unchanged at the
new row count.

**The fourth family needed no network call.** `1072`'s next-pass list named the
Alaska Division of Corporations — a fetch — as the cheapest genuinely independent
second family. `data/clean/fpds_uei_edges.csv` is cheaper and already local: it
records **the parent a registrant declared about itself, to the federal
government**, made by the **child** rather than the parent and therefore
independent of both the audited filing and the corporate site. Rule 11's measured
**20-observation ownership floor** applies; below it an edge is a joint venture.
**The test is not "the names match"** but *"the declared parent resolves, through
the identifier ledger, to the owner hub NEST already asserts"* — two independent
parties agreeing about the **owner**.

| `fpds_parent_corroboration` | rows | rung 1, published UEI | rung 2, exact normalised name |
|---|---:|---:|---:|
| `NO_DECLARED_PARENT` | 3,874 | — | — |
| `PARENT_UNRESOLVED` | 339 | 188 | 151 |
| **`CORROBORATED`** | **293** | 213 | 80 |
| `PARENT_BELOW_JV_FLOOR` | 270 | — | — |
| `CONTRADICTED` | 22 | 13 | 9 |

[measured 2026-09-02]

**The contradictions are mostly the LEDGER's defect, not NEST's.** At the
pre-ingest count of 8, six resolved to `AKNF-INPTAS-00-ARCSLO`, the **village
government**, which rule 2 forbids — five Bowhead/UIC rows plus Rockford and
UMIAQ — and two were collisions on the tokens `Eagle` and `Vista`. **NEST was on
the correct side of 6 of 8.** Two stayed open and neither side was repointed:
`Nisga'a Tek LLC` (NEST Tlingit & Haida vs Goldbelt, 254 observations) and
`Broadleaf, Inc` (NEST The Hawai'i Pacific Foundation vs ASRC, 325), in
`review/nest_fpds_parent_contradictions_2026-09-02.csv`. [from the record —
`docs/ENTITY_LAYER_DEEPENING_2026-09-02.md` §3] **The 22 in the delivered file
have not been re-triaged at the new row count** — a limit, not a finding.

### 3.5 The conflict register, and why `relationship` fuses three axes

**This is the first thing in NEST that *can* disagree, and getting the count
right took three versions:**

| version | reported | what it was actually measuring |
|---|---:|---|
| v1 | 37 conflicts | 35 were the filing saying `wholly_owned` where the site said `subsidiary` — **an unspecified word refined by a specific one**, not a rival claim |
| v2 | 23 conflicts | 21 were Calista's `wholly_owned` vs `operating_company` — **a SHARE and a ROLE**, which cannot disagree, because a wholly-owned company is very often an operating one |
| v3 | **2 conflicts** | two values on the *same* axis |

[from the record — `docs/NEST_BUILD_LOG.md`]

**The modelling observation is the durable part: `relationship` carries three
orthogonal axes in one column.** `wholly_owned` / `majority_owned` state the
**SHARE**. `holding_company` / `operating_company` / `division` state the
**ROLE**. `subsidiary` and `declared_suborganization` state neither. And the
third, added by the Chugach adjudication: **a consolidation note answers where an
entity SITS; a business directory answers what a firm SELLS; both render into the
same six words.** A conflict check has to compare within an axis or it
manufactures disagreements — and thirty-five manufactured ones would have buried
the two that are real.

**The two real ones** are `Chugach Government Solutions, LLC` and `Chugach
Regional Development, LLC`, where the audited filing says `holding_company` and
the web list says `operating_company`. Two facts settled it for the filing. The
web source is ONE page, `www.chugach.com/business/directory`, and **on that same
page it calls Chugach Commercial Holdings a holding company** while calling CGS
and CRD operating companies — so the site asserts a different role rather than
omitting one, and **the conflict is genuine**. And a **third** source,
`anc_tribal_subsidiary_lookup.csv`, lists CCH, CGS, CIH and CRD **identically as
`subsidiary` directly under the corporation** — four parallel siblings at one
tier, two of them named *Holdings*. **A statutory filing signed off by an auditor
outranks marketing copy**, so `holding_company` stands. [from the record —
`docs/ENTITY_LAYER_DEEPENING_2026-09-02.md` §3; those two rows are the entire
content of the pre-`1102` backup of the conflict file, measured 2026-09-02]

**The register has since regressed and it is a live defect.** It now holds **45
rows**, of which **43 are `conflict_kind = ownership_vs_affiliation` whose
`web_list_says` value is the literal string `unspecified`** [measured]. That is
the v1 error returning through the front door: an unspecified value is not a
rival claim, it is the owner's v6 file stating no relationship word at all. §6.

### 3.6 The dual role — an ANC or an NHO is both a register entity and an enterprise

> *"ANCs and NHOs are themselves entities, but they're also enterprises too."*
> — the owner, 2026-09-02

He is right and NEST's model was wrong: an ANCSA corporation was only ever an
`owner_hub_cedar_uid`, a hub that owns. **It is also a corporation that trades.**

**The obvious fix is wrong.** Adding the corporation to `nest_enterprises.csv` as
a row hubbed on itself breaks the key and makes a hub its own subsidiary — the
exact thing `1072` already refuses after `The Eyak Corporation` and `Coushatta`.
**ADR-032: the second role is RECORDED, not duplicated.**
`data/clean/nest_entity_dual_role.csv`, one row per entity keyed on `cedar_uid`,
joined to `nest_enterprises` on `owner_hub_cedar_uid`. **The register keeps ONE
row for the entity; NEST keeps ZERO rows for it.** Invariant **I12** holds the
no-self-subsidiary line.

**358 entities carry a dual role** — `REGISTER_ENTITY_AND_ENTERPRISE` 292 ·
`ANC_CORPORATION_AND_ENTERPRISE` 53 · `NHO_ORGANISATION_AND_ENTERPRISE` 13
[measured]. Three evidence rungs, recorded per row and **never collapsed into a
boolean** [measured 2026-09-02]:

| rung | what fires it | entities |
|---|---|---:|
| R1 `DECLARED_BY_OWNER_DATASET` | the owner's file carries a row whose enterprise name normalises to the parent's own name | **263** |
| R2 `ENTITY_HOLDS_ITS_OWN_IDENTIFIER` | that row carries a UEI or CAGE on the entity's own legal name | **247** |
| R3 `REGISTERED_AS_A_FIRM_IN_SBA_DSBS` | the entity's own legal name is a row in the SBA certification register, with its own UEI | **106** |

**R3 exists because the owner's file cannot evidence the NHO half of his own
correction** — it carries exactly one NHO parent, and that one (`NHO-MANUKAI-00`,
Manu Kai LLC) does not crosswalk. The SBA DSBS extract already on disk can; it is
a `federal_registry` observer rather than a restatement of his file, and rule 14
is why it works: *an NHO says it is one, because the certification is the point.*
**Uniqueness is required on both sides** — 73 register entities were refused
because their own name is not unique in the register or in DSBS. **Absence means
no evidence was found, never "it does not trade":** a row exists only where a rung
fired, and invariants **I11a–I11d** exit 1 if the table stops reaching ANCs, stops
reaching NHOs, becomes only those two, or loses R3. [from the record — ADR-032]

**In the delivered file the join is smaller than 358 suggests.** The dual-role
columns are populated on **1,701 of 4,798 rows (35.5%), covering 139 of the 472
owner hubs** [measured]; the other 219 dual-role entities are register entities
that are not NEST owner hubs. **A consumer asking "what does this ANC own" reads
the enterprise rows; asking "does this ANC itself sell" reads the dual-role
block. Neither question is answered by a row that pretends to be the other.**

---

## 4. What is NOT in it and why

Everything refused is registered with a measured reason and a full-fidelity copy
of what was declined. **Nothing was deleted.**

### 4.1 The three hold classes inside the builder — 1,712 rows

`data/staging/nest/held_rows.csv` [measured 2026-09-02]: `ANCSA_VILLAGE_GOVERNMENT`
**1,281** · `TERMS_STATED_RESTRICTIVE` **414** · `HUB_UNRESOLVED` **17**.

**The 17 unresolved hubs are honest residue and none was forced.** Named in the
file: *Confederated Salish & Kootenai* (the spine's canonical name is the
truncated `Confederated Salish`, and `Kootenai` is a separate tribe), *Central
Council of Tlingit & Haida Indian Tribes of Alaska*, and *Manu Kai LLC*, which is
not in the spine at all. `1130`'s parent crosswalk reached the first and third
independently from a different direction and classed them `UNRESOLVED_AMBIGUOUS`
and `UNRESOLVED_NOT_IN_REGISTER`. **Six intertribal organisations are spine gaps
and the cheapest register additions on this page: NAFOA, NAJA, ILTF, First
Nations Development Institute, the Five Civilized Tribes council, IHS Tribal
Self-Governance.**

### 4.2 The 84 restricted-publisher assertions, and the 414 held on a refusal since lifted

The original build refused **84 assertions** from `ANC_TRIBE_LOOKUP` on
`TERMS_STATED_RESTRICTIVE`: **NANA Regional Corporation 43, Chickasaw Nation 24,
Forest County Potawatomi 9, Yakama Nation 8** [from the record —
`docs/NEST_BUILD_LOG.md`]. The count reproduces: **84 rows of `held_rows.csv`
carry `source_id = ANC_TRIBE_LOOKUP` and a `TERMS_STATED_RESTRICTIVE` hold**
[measured]. Source 7 brought **330 more**, for **414** [measured]; the Akima
block alone — `akima.com/our-company/` — is 52 of them.

**All 414 sit on a refusal the owner has lifted.**
`TERMS-OWNER-RULING-2026-09-02` released all eight publishers for harvest of
their own public pages (§1.5). `1072`'s predicate predates the ruling and still
enforces the old answer. **This pass did not change it**, and the reason is worth
stating: a publication-policy guard on a shared builder is not an agent's
unilateral edit at the end of a pass. But it is `AGENT_FIELD_GUIDE` rule 9 exactly
— *when a refusal is reversed, the cached refusals must be retired or the
correction never takes effect* — and it is worth 414 rows to whoever owns `1072`
next. The refusal is still the right shape for what it is: **asking is the route
back in; a cleverer scrape is not.** And the four things the ruling did **not**
touch still bind here.

### 4.3 The 12,084 unhubbed rows — and they are NOT "named, never folded"

**The task that commissioned the ingest described them that way. They were
measured instead, and they are four different things.**
`data/staging/nest/owner_v6_refused.csv`, 12,319 rows in nine named dispositions
[measured 2026-09-02]:

| refusal | rows | what the owner's own file says |
|---|---:|---|
| `OWNER_FILE_SAYS_UNMATCHED` | **8,927** | `attribution_method = unmatched`, `data_sources = master_entity_registry`, `verification_source` **blank on all 8,927** |
| `SBA_CERTIFIED_BUT_NO_OWNER_NAMED` | **3,140** | `parent_entity_type = TRIBAL_ENTITY_UNCROSSWALKED_SBA` |
| `UEI_ALREADY_HELD_BY_NEST_OTHER_HUB` | 172 | §4.5 |
| `PARENT_UNRESOLVED_UNRESOLVED_NOT_IN_REGISTER` | 26 | the parent handle is in no Cedar register |
| `UEI_ALREADY_HELD_BY_NEST_SAME_HUB` | 20 | §4.5 |
| `NO_TRIBE_ID_ON_THE_ROW` | 17 | 16 AIHEC tribal colleges + 1 tribal-press row |
| `PARENT_UNRESOLVED_UNRESOLVED_AMBIGUOUS` | 12 | the handle resolves to more than one entity |
| `BLANK_ENTERPRISE_NAME` | 4 | no name to key on |
| `APPLIED_CORRECTION_FA-01` | 1 | §4.6 |

**The unhubbed block is 8,927 + 3,140 + 17 = 12,084 rows, not 12,085**, and the
`unmatched` bucket is **8,927, not 8,928** [measured].

**The 8,927 are the owner's own UNMATCHED RESIDUE and they are REFUSED.** His
file says so in its own column. They are FPDS awardees his resolver could not
attribute to any Native entity, and reading them settles it: `Merchen & Reed
Gravel Inc`, `Goldenlook Of San Antonio Inc`, `A A M C Inc` — and **natural
persons**: `Benward, Ursula`, `William Woolard`. **Nothing in the file asserts
that any of them is Native-owned.** Admitting them would be fabrication at a scale
of 8,927 rows and would publish natural persons into a business dataset. **This is
`START_HERE` §1b in a third vocabulary: `unmatched` is a NEGATIVE result.**
Inheriting the row while dropping its sign is exactly how 317 `elijah_ruling`
tier-X refusals were once published as confident attributions. Invariant **W6**
fails the build if any of these names reaches NEST — **scoped to names the emitted
set does not also carry**, because 11 of them are *also* carried by a properly
hubbed row and a bare name test called those leaks.

**The 3,140 SBA rows are real firms with no owner named.** `SALCO LLC`, `HAKU
SYSTEMS LLC`, `MAKWA GLOBAL SERVICES, LLC` — self-certified Native-owned, 8(a),
in the SBA certification register. **That is evidence.** It is not a NEST row:
NEST's grain is (owner hub, enterprise name) and **no owner nation is named on any
of them**. They are registered for `native-owned-businesses` and the
individually-Native-owned class, by name and UEI, so the promotion is **a join and
not a re-harvest**, and **the route to them is the identifier, not the name.**

### 4.4 The 160 v3-only rows — DO NOT RECOVER

`1130` staged 160 rows / 158 enterprise names present in the owner's v3 file and
absent from v6, all 160 carrying a UEI, and called them recovery candidates.
**One measurement settles that recovering them is wrong:**

```
v3-only rows whose UEI is ALSO IN v6                          160 of 160
v3-only rows whose exact name string is in v6 under that UEI    0 of 160
```

[from the record — `docs/NEST_BUILD_LOG.md` Decision 2; the 160 reproduces
exactly in `owner_v6_conservation.csv` as `v3_only_name_uei_present_in_v6: 160`
against 19,846 v3 rows in, and `data/staging/nest/owner_v3_name_variants.csv`
holds 160 rows [measured]]

Every one is the same firm, under the same federal registration, spelled
differently — `GLACIER TECHNOLOGIES LLC` against `Glacier Technologies Limited
Liability Company`, `GOLDBELT HAWK L.L.C.` against `Goldbelt Hawk Llc`, `CADDO
INDUSTRIES ENTERPRISE` against `CADDO INDUSTRIES ENTERPRISES`.

NEST clusters on the normalised **name**. `norm()` strips a trailing corporate
form but not `limited liability` in the middle of one, so `glacier technologies`
and `glacier technologies limited liability` are two keys — and rapidfuzz declines
to fuse them because the merge rule caps the length difference at 6 while theirs
is 18. **Recovering v3 would have created up to 158 duplicate enterprises**, the
exact defect the merged-not-appended design exists to stop and which has already
cost real rows once (§6). So the v3 strings are recorded as **observed name
variants keyed on UEI**, not as enterprises. **The loss the recovery list
described does not exist**; what exists is 160 extra renderings of names Cedar
already holds, worth having and worth nothing as rows. **And the loss had to be
measured after normalisation, not before** — under a raw name compare it looks
like 598 rows, 438 of which are renderings v6 still holds.

### 4.5 A UEI Cedar already holds is a corroboration, not a new firm

A UEI is one federal registration for one firm, so an owner row carrying a UEI a
live NEST row already holds **is that firm again**. **But the collision only
matters when the row would create a NEW cluster.** Where NEST already holds
`(this hub, this normalised name)` the row MERGES and raises the observation
count, which is the entire point of putting the file through the builder's
clustering. Refusing on the UEI alone discarded **173** of exactly those, so the
rule tests the clustering key first. What is refused: **20** same-hub and **172**
cross-hub rows that would have created a second enterprise for a firm Cedar
already registers [measured; the build log says 21 same-hub]. Registered in
`data/staging/nest/owner_v6_uei_already_held.csv`, 192 rows [measured]. **The
cross-hub ones are an ownership disagreement needing adjudication, and they must
not be settled by whichever pass ran last.**

### 4.6 An old file is a time machine, and it put a refuted link back

**`62_no_regression_check.py` caught this on the first run after the ingest, and
it is the most important refusal in this section.** The first build put

```
nest_enterprises.csv  1 row(s) still key ANRC-BRBYCO-00 to
                      'BRISTOL BAY AREA HEALTH CORPORATION'   [FA-01]
```

FA-01 is settled. Bristol Bay Area Health Corporation is a **separate** tribal
health organisation, `SGVF-BRSTLB-00`; the link to Bristol Bay Native Corporation
was a `cluster_v3` name-cluster error; 742 rows were unlinked on 2026-08-26; the
ledgers were marked **tier X** so the refutation is permanent; and `510`
harvested it as deny assertion #332. **The owner's v6 file predates the
correction, so it still asserts it. Any pass that imports a dataset built before
a correction will re-assert what the correction withdrew — and it will arrive
looking exactly like coverage.**

`1133` now reads `data/clean/cedar_correction_register.csv` (written by
`code/354_correction_register.py`) and refuses any edge whose `(entity,
normalised name)` is an applied withdrawal. It catches exactly one row,
`APPLIED_CORRECTION_FA-01`, registered with the correction's own reason text.
Invariant **W7** fails the build if a withdrawn link reaches NEST, and its fixture
injects one and proves it fires. **The point of checking it in `1133` rather than
relying on `62` is timing: a red `62` is found *after* the rebuild, and `W7` is
found before it.** The register holds **178 rows, 130 distinct `(entity_id,
withdrawn_key)` pairs, 260 once the `cedar_uid` leg is counted as
`load_corrections()` counts it** [measured 2026-09-02].

### 4.7 What the ANCSA mine itself did not reach

**256 documents have a text layer and name no subsidiary** — some genuinely
enumerate nothing, others use a shape the two triggers do not reach; ten minutes
with `ancsa_mine_log.csv` sorted by `outcome` would say which. **58 documents have
no text layer** — `code/1031` has an OCR fallback that decides per PAGE and it has
not been run over these. **25 documents were excluded on NANA Regional's terms**,
released by the owner ruling and not yet re-read. [all measured 2026-09-02; the
build log gives 273 / 66, both stale]

### 4.8 The largest single open item — 1,281 rows, not 212

`1130` measured 223 hub disagreements between the owner's file and NEST, of which
**212 hub an ANCSA subsidiary on the Native Village GOVERNMENT** while NEST hubs
it on the corporation. That was a count of net-new **clusters**. Put the whole raw
file through `1072 assemble` and the count of **rows** the guard has to hold is
**1,281 across 221 distinct village governments** — Chenega 128, Barrow 123,
Pribilof Islands 98, Eagle 78, Afognak 53, Tyonek 51 [measured 2026-09-02].
**986 of the firms named on them are in NEST under no hub at all**, so this is not
a rounding difference: **it is the single largest block of Alaska Native corporate
structure still outside the dataset.**

**No new guard was written, because `1072` already implements the owner's own
ruling and is applying it correctly.** What would close it is a source that names
the **corporation** per row. `anc_tribal_subsidiary_lookup.csv` does exactly that
in `parent_entity_type`, which is why `1072` can repoint its 549 rows and cannot
repoint these. **The correction belongs in the owner's file, with the ruling
attached.**

This is the `ALASKA_VILLAGE_GOVERNMENT_VS_VILLAGE_CORPORATION` defect family —
334 defects, $24.52B — and NEST has reached it from **six independent
directions**: the lookup file's self-contradicting columns, the FPDS
declared-parent contradictions, the owner-file hub disagreements, the raw-row
assemble count, the 83 successful repoints, and the ledger resolutions of §3.4.
**NEST is on the correct side of every one.**

---

## 5. Money

**NEST has no money column, and the right thing to do with that is to say it
rather than imply a total exists.** Not one of the 91 delivered columns holds a
dollar figure, and `nest` appears nowhere in `docs/MONEY_TOTALLING_RULES.md`
[both measured 2026-09-02]. That file governs the money tables and NEST is not
one of them.

**A structure table is not a money table**, and the temptation it creates is easy
to name. NEST tells you that a nation owns a firm. It does **not** tell you what
that firm earned, obligated, expended or distributed. The dollars attached to
these firms live in `prime_contracts.csv`, `federal_funding_transactions.csv`,
the subaward tables, `fac_tribal_single_audits.csv` and the gaming tables, each
with its own totalling rules, denominator and double-count hazards. **Joining
NEST to any of them to produce a "tribally owned enterprise revenue" figure is a
join this dataset does not license**, for three independently sufficient reasons:
68.5% of NEST rows assert affiliation rather than ownership; `uei` is populated on
52.2% of rows, so the join is partial in a way that is not random; and NEST's
grain is `(owner hub, enterprise)`, so a joint venture is correctly two rows, one
per parent, and a naive money join double-counts it.

### What may and may not be summed in this file

**May be summed:**

- **`n_source_observations`** — one row per enterprise, summing to **7,559**,
  exactly the row count of `nest_enterprise_relations.csv` [measured both sides].
  This is the file's one honest total.
- **Row counts under any single-valued filter** — `relation_class`, `owner_class`,
  `in_federal_contracting`, `evidence_class`, `source_id`, each populated on all
  4,798 rows with one value per row [measured].

**May NOT be summed:**

- **`n_nest_enterprise_relations` is a fan-out count carried at the WRONG grain.**
  It is computed per `cedar_uid` — per **owner hub** — and replicated onto every
  enterprise row of that hub. Summing it across the file gives **352,617** against
  a true relations count of **7,559**, a **46.6× overstatement** [measured]. The
  correct de-duplication is `sum(max(...) GROUP BY owner_hub_cedar_uid)`, which
  returns 7,559 exactly [measured]. The codebook's closing note warns that a raw
  column sum is not the dataset's answer; **this is the column it is warning
  about.**
- **Every `nest_entity_dual_role__*` count**, for the same reason: the block is
  folded one-to-one on `cedar_uid` and repeats on every enterprise row of that
  hub. `nest_entity_dual_role__n_nest_enterprises_owned` sums to **68,021** across
  rows and **1,701** de-duplicated by hub [measured] — and even the de-duplicated
  figure counts *rows*, not entities, because only 139 of the 358 dual-role
  entities appear here.
- **`hierarchy_level`** sums to 4,930 and means nothing.
- **`fpds_declared_parent_observations`** is an FPDS transaction count belonging
  to the **declared parent**, not to this enterprise. It is a threshold input for
  rule 11's 20-observation floor, not a quantity.
- **`ownership_percent_stated`** is populated on **13 rows** — `100` on 12 and
  `60` on 1 [measured]. It is a stated share on the rare row where a source stated
  one. It is not a weight, it is not imputable to the other 4,785 rows, and
  nothing may be multiplied by it.

### One denominator that is not money but behaves like one

**`in_federal_contracting = N` on 2,438 of 4,798 rows (50.8%)** [measured] —
enterprises with a named owner, a named source and a permanent Cedar identifier
that **no federal procurement record contains**. That is the number the dataset
exists to produce, and it must be read as a **floor**:

| owner class | enterprises | absent from FPDS | share |
|---|---:|---:|---:|
| Tribal government | 3,282 | 1,664 | 50.7% |
| Alaska Native corporation | 1,416 | 732 | 51.7% |
| Native Hawaiian organization | 100 | 42 | 42.0% |
| **total** | **4,798** | **2,438** | **50.8%** |

[measured 2026-09-02]

**Why a floor and not a point estimate.** The presence test is *exact normalised
name OR published UEI OR published CAGE* against the FPDS universe, and the basis
is on the row: of the 2,360 rows marked present, **1,931 matched on a published
identifier and 429 on an exact normalised legal name only** [measured]. **A name
collision makes an enterprise look present**, so the error runs against the absent
count. The 429 name-only rows are the exposed set.

---

## 6. Known limits, stated plainly

**A permanent id stopped resolving, and it is an open defect in `1072`.** The
append-only register holds **4,800 bindings** while NEST settles at **4,798**, so
**two bindings no longer resolve** [measured 2026-09-02]:

| orphaned binding | key | why |
|---|---|---|
| `CEDAR-NEST-001736-2H` | `(CE-0007A-ZA, "bristol bay area health")` | a withdrawal made **on purpose** — the FA-01 applied correction, §4.6 |
| **`CEDAR-NEST-000004-R4`** | **`(CE-0006B-0K, "cp leasing")`** | **the defect** |

Nothing was lost. The owner's file carries the same firm as `C P Leasing, Inc`,
which normalises to `c p leasing`; rapidfuzz **correctly** fused the two
renderings; the fused cluster's canonical key became `c p leasing`; and `1072`
minted a new id for a company that already had one. The firm is in NEST today as
`CEDAR-NEST-001611-0W`, `C P Leasing, Inc`, with `CP Leasing` in
`name_variants_observed` [measured]. **But `enterprise_id` is permanent, and a
customer who joined on `CEDAR-NEST-000004-R4` now gets nothing.** The cause is
structural: `1072` binds the id to the cluster's **canonical** name, so the
arrival of a name **variant** can move the key. **It happened once in 3,190 mints
and it will happen again.** Retiring or repointing an id needs evidence and an
owner ruling, so neither was done. What *was* done is the part worth copying:
**`1130`'s invariant I6b asserted `len(register) == len(NEST)`, which is not what
its name says** — an append-only register exceeds the live table the first time
any cluster key changes, which is the register *working*. I6b now asserts what it
is called and **reports the orphan count beside it**. `docs/WORK_QUEUE.md`
carries the defect.

**The staged edge count wobbles by 2 and the table does not.** `1133` asks "does
NEST already hold this firm" to avoid minting a second enterprise for one company
— and after the first ingest **NEST holds this script's own rows**, which is
`AGENT_FIELD_GUIDE` rule 10 (five instruments in this repo have scanned their own
output). Rows whose `source_id` is `OWNERV6` are excluded from that context, but
the exclusion is not perfectly stable, because `source_id` is the *best* source of
a cluster and a cluster mixing this file with another can flip. Measured over four
`apply → assemble → build` cycles:

```
staged edges       5,791  ->  5,789  ->  5,791  ->  5,789
nest_enterprises   4,798      4,798      4,798      4,798
ids minted             0          0          0          0
```

[from the record — `docs/NEST_BUILD_LOG.md`; the staged file holds **5,791** edges
today [measured]]

**The enterprise table and the id register are a fixed point; only the staged edge
count moves, by 2 rows in 5,791 (0.03%), and only in the direction of admitting
more.** It is recorded rather than hidden. The stable fix is to run the
UEI-duplicate test against the **staged edge set** inside `1072`, where the other
sources' UEIs are visible before anything is clustered, rather than against the
built table. That is a `1072` change and has not been made.

**The conflict register has regressed and now measures something other than its
own name, on 43 of 45 rows.** §3.5. An unspecified value is the absence of a
claim, not a rival one. **Relatedly, `1102` stamped its Chugach adjudication
columns — `third_source`, `third_source_says`, `adjudication`, `adjudicated_by`,
`adjudicated_date` — onto all 45 rows uniformly** [measured], so 43 rows about
Ahtna, Bering Straits, Doyon, Koniag and Sealaska carry a `third_source_says`
sentence describing Chugach Commercial Holdings. **The adjudication was broadcast
rather than joined.**

**NEST holds companies twice, and the count has grown.** Clustering is on
`(owner hub, normalised name)` and **a trailing parenthetical survives
normalisation**:

```
CEDAR-NEST-000001-6S  Aan Hít                       NESTDUP-0001
CEDAR-NEST-000002-CJ  Aan Hít (Village House)       NESTDUP-0001
CEDAR-NEST-000012-8C  Goldbelt Hawk LLC (GbHawk)    NESTDUP-0002
CEDAR-NEST-001630-JQ  Goldbelt Hawk Llc             NESTDUP-0002
```

`1102` found **25 groups / 50 rows** at 1,610 enterprises; the delivered file
carries **62 groups / 126 rows** [measured]. The cost is double — rows of
overstatement **and** lost corroborations, because a restatement that fails to
cluster raises nobody's source count, which is precisely what the
merged-not-appended design exists to do. **FLAGGED, NOT MERGED:** merging retires
ids out of an append-only register, `IDENTIFIER_STANDARD` forbids retiring an id
as a side effect, and `AGENT_FIELD_GUIDE` §4 says measure duplicates before
collapsing them. Register:
`review/nest_name_variant_duplicates_2026-09-02.csv`. **The absent-from-FPDS share
is unaffected**: the duplicates are ANC subsidiaries that *are* present in
contracting, so collapsing them would raise the absent share, not lower it. **The
floor stays a floor.**

**More than a third of the file rests on a resolver, not an observer.** 1,699 of
4,798 rows carry `evidence_class = owner_research_dataset_resolver_output` or
`owner_research_dataset_hand_ruling`; `evidence_human_reviewed = N` on **2,875 of
4,798 (59.9%)**; and at assertion grain `source_review_status =
auto_ruled_not_human_reviewed` on **3,588 of 7,559** [all measured]. Both columns
exist so a reader can filter to the evidence a person has actually looked at.

**Corroboration is thinner than `n_distinct_sources` makes it look.** 760 of 4,798
rows (15.8%) rest on more than one source [measured], but the same source family
across several fiscal years counts as several sources. `KNOWN_ISSUES` §2 names the
missing column — `n_independent_families` — and it has not been built. Relatedly,
**the 22 FPDS contradictions have not been re-triaged at the new row count**: the
8 that existed at 1,610 rows were adjudicated in full and NEST was correct on 6,
and nothing states which of the extra 14 are the ledger's village-government
defect and which are real.

**Street-level address is the honest gap.** City on 2,461 rows and state on 2,488
(51.3% / 51.9%); street on none [measured]. The routes that do not touch D&B:
JSON-LD `PostalAddress` on pages already in `data/staging/*/raw/` (zero network —
11 of shard E's 118 stored pages carry one), the Alaska Division of Corporations
entity search, and `usaddress` over the address prose already sitting in the
annual reports — *Kootznoowoo: "Favorite Bay, LLC: Owns the Newport IX building
located at 2201 Buena Vista Drive, Albuquerque, New Mexico."*

**Tribal governments are now the majority of rows and the thinnest evidence.**
3,282 of 4,798 rows carry `owner_class = tribal_government` [measured], but the
overwhelming majority arrived through source 7, which states no relationship word.
The ANCSA route is exhausted by statute (§1.1); the lower-48 route is a nation's
own "Our Companies" page, and `code/701`'s TERO-free vocabulary sweep found
**10.0% of hosts publish one** [from the record].

**The dataset covers 472 of Cedar's ~1,555 spine entities** [measured].
**Absence of a nation from this file means no source Cedar holds names an
enterprise it owns. It does not mean the nation owns none.**

**Smaller limits, each measured 2026-09-02.** `sector` is populated on 1,631 rows
(34.0%). `status` is `unknown` or `last_seen_earlier` on 488.
`first_observed_year` / `last_observed_year` span 2016–2026 and are blank on 213
rows; they are derived from the run of years in the relations table, so an
enterprise named in one document has a one-year window that says nothing about
when the relationship began or ended. `record_scope = BUSINESS` and `publishable =
Y` on all 4,798 rows — declarations of the population, not discriminators.

---

## 7. Refresh

**`nest` is not in the refresh register at all.** `docs/REFRESH_CADENCE.json`
(regenerated 2026-09-02 by `code/630_refresh_cadence.py`) tracks **55 sources
across 13 datasets, and `nest` is not one of them** [measured 2026-09-02].

| source | cadence | what a re-pull changes | route |
|---|---|---|---|
| **AS 45.55.139 annual reports** | annual per corporation, plus a **10-business-day filing queue** the Division warns about explicitly | new fiscal years extend `last_observed_year` and add or drop subsidiaries; **the filer population itself shrinks under HB126** | the Division's STAR portal, access granted to the owner personally. Not an API. **Re-capture the corporation dropdown every run and diff it** — this run's list is preserved in `code/ancsa_portal/corps.json` |
| the owner's v6 file | irregular; it is a research artefact | 66.5% of the rows, so a new vintage moves the dataset more than any other input | a file on this machine. **Run `1130 versions` before trusting a new one** — v5 looked identical to v6 and was broken in four columns |
| a nation's own "Our Companies" page | irregular | the lower-48 route, and the only one not statute-bound | `code/701` / `code/1070` |
| SBA DSBS extract | as the register updates | `uei_candidate`, addresses, the R3 dual-role rung | already on disk |
| `fpds_uei_edges.csv` | rides the FPDS pull | the corroboration family of §3.4 | already on disk |

**The cadence hazard specific to this dataset: re-pulling the ANCSA portal will
make the source look like it is shrinking, and it is not.** HB126 took effect
2026-06-25 and narrows who must file. A village corporation with 2016–2025 filings
that stops appearing has not gone dark; it has stopped being a filer. **Any
coverage statement built on this source for periods after 2026-06-25 is coverage
of the post-HB126 filer population**, which is smaller than the pre-HB126
population and much smaller than the 196-entry roster. Do not express portal
coverage as a fraction of the roster without saying this.

**Rebuild ordering, and the manifest is wrong about it.** The correct order is

```
1133 apply  ->  1072 assemble  ->  1072 build  ->  1102
```

`1072 build` is a **full rebuild**; `1102` is an **in-place enricher on the same
file** and must run **last**, or its corroboration, duplicate flags and
adjudication are reverted while the row count still looks right.
`py -3 code/build.py plan nest` currently prints **0 full rebuilds**, files
`1072`, `1102` and `1130` all under in-place enrichers, and **does not list
`1133` at all** [measured 2026-09-02, run]. It also reports enricher backups
present on both tables with *"re-run unknown"*, which is the manifest failing to
name what to re-run.

**What breaks if it is never re-pulled.** The AS 45.55.139 leg is the only
observer-grade ownership evidence in the dataset — the only source where a parent
asserts ownership about itself under a filing obligation, with an auditor's
signature on the page. Everything else is a corporate website, a compiled
directory, or a resolver output. **If that leg ages, NEST does not get less
complete; it gets less credible**, because the share of rows resting on an audited
filing falls while the row count holds.

---

## Stale claims found while writing this

Ordered by how much damage acting on the wrong value would do.

1. **`docs/NEST_BUILD_LOG.md`'s `relation_class` split is inverted relative to the
   delivered file.** The log reads `ownership 1,512 / affiliation 98`. Measured:
   **`affiliation` 3,286 / `ownership` 1,512** [measured 2026-09-02]. The
   *ownership* count is exactly right and unchanged; affiliation grew by 3,188
   with the owner-file ingest, and the log's own later block explains why without
   updating the earlier table. **This is the highest-damage stale figure in the
   document**: a reader who takes the first table at face value concludes 94% of
   NEST is an ownership claim when it is 31.5%.

2. **The build log states the delivered row count as 4,799 in the ingest section
   and 4,798 in the results table of the same block.** The delivered file holds
   **4,798**, `data/clean/nest_enterprises.csv` holds **4,798**, and
   `dist/customer/MANIFEST.csv` says **4,798** [measured]. **4,798 is right.** The
   same sentence gives `source_id = OWNERV6` as *"3,190 of 4,799"*; it is **3,189
   of 4,798** [measured]. 3,190 is the *ids minted* count (register 1,610 →
   4,800), a different quantity, and the two are conflated in one line.

3. **The 60.7% headline is stale by construction and no document carries its
   replacement.** *"977 of 1,610 enterprises (60.7%) … do not appear in federal
   contracting at all"* opens the build log and is repeated in
   `docs/ENTITY_LAYER_DEEPENING_2026-09-02.md` §3. ADR-034 records the movement
   (977 → 2,438) but states no new percentage. Measured: **2,438 of 4,798, 50.8%**
   [measured]. The owner-class table under the headline is stale in both
   directions — ANC 1,188 → **1,416**, tribal 322 → **3,282**, NHO 100 → 100.
   **A buyer quoting "60.7%" is nine points high and describing a table a third
   the size.**

4. **`docs/NEST_BUILD_LOG.md` Decision 1 gives the unhubbed block as 12,085 rows
   with an `unmatched` bucket of 8,928.** Measured from `owner_v6_refused.csv` and
   `owner_v6_conservation.csv`: **12,084** and **8,927**. ADR-034 already says
   8,927, so the log is inconsistent with the ADR written from the same pass. The
   four-way split is stated as 8,928 / 3,140 / 16 / 1; measured it is **8,927 /
   3,140 / 17**, where the 17 is one disposition (`NO_TRIBE_ID_ON_THE_ROW`)
   holding 16 AIHEC tribal colleges and 1 tribal-press row.

5. **`docs/KNOWN_ISSUES.md` Lesson 3 supersedes the build log's diagnosis of the
   owner-file defect, and the build log does not know.** The log calls it a
   *"column-shift defect"*. Lesson 3 measured the shift width at **zero** across
   all 26 columns on 11,392 matched rows and named the real cause: a pandas `agg`
   missing-column fallback in `sam_extracts/build_master_entity_registry.py:126`
   substituting `awardee_uei` for `recipient_location_state_code`. **A shift is a
   parser bug you fix once; a silent column substitution recurs on the next
   renamed column.** Anyone reading the NEST log alone will look for the wrong bug.

6. **The whole FILES block of the build log predates the ingest, and six of its
   artefact sizes are wrong.** Measured 2026-09-02:

   | artefact | the log says | measured |
   |---|---:|---:|
   | `nest_enterprises.csv` | 1,610 rows, 59 columns | **4,798 rows, 68 columns** |
   | `nest_enterprise_relations.csv` | 3,789 rows | **7,559 rows** (25 columns ✓) |
   | `cedar_nest_id_register.csv` | 1,610 bindings | **4,800** |
   | `ownership_edges_staged.jsonl` | 3,499 | **7,976** |
   | `held_rows.csv` | 101 refusals | **1,712** |
   | `evidence_conflicts.csv` | 2 conflicts | **45** |
   | `codebook/18a_nest_enterprises.csv` | 59 variables | **68** |
   | `ancsa_consolidation_edges.jsonl` 2,168 · `sweep_1070_refused.csv` 286 · `ancsa_mine_log.csv` 524 · `18b` 25 | | all ✓ |

   **`held_rows.csv` at 101 → 1,712 is the one that matters**, because that file
   is the review queue `ANCSA_OWNERSHIP_RULING` prescribes and its size is the
   measure of the open work. A reader taking the FILES block at face value
   under-reads the queue by a factor of seventeen.

7. **`py -3 code/build.py plan nest` is wrong about the pipeline it describes.**
   It prints **0 full rebuilds** and files `1072` under in-place enrichers when
   `1072 build` is the full rebuild and `1102` is the enricher that must follow
   it; and **it does not mention `1133` at all** [measured 2026-09-02, run]. The
   build log flags the first half. **The missing `1133` is not flagged anywhere**,
   and it is the more dangerous omission: a rebuild run from the plan alone omits
   5,791 staged edges and 3,189 delivered rows, and `1072` prints its named
   `_owner_v6_INPUT_ABSENT` warning into a log nobody is reading.

8. **`docs/ENTITY_LAYER_DEEPENING_2026-09-02.md` §3 gives the FPDS corroboration
   as CORROBORATED 87 / CONTRADICTED 8 / PARENT_UNRESOLVED 177 /
   PARENT_BELOW_JV_FLOOR 71 / NO_DECLARED_PARENT 1,267.** Those were measured at
   1,610 enterprises and `1102` has since been re-run against 4,798. Measured:
   **293 / 22 / 339 / 270 / 3,874**. The prose claim *"87 > 60, and it is a
   different 87"* is still true about the method and false as a count.

9. **`evidence_conflicts.csv` is described everywhere as "2 real audited-vs-web
   conflicts". It holds 45** [measured], and the pre-`1102` backup holds exactly
   the documented 2, so the growth is post-ingest and undocumented. **43 of the 45
   are the v1 error the build log says was fixed** — an `unspecified` value scored
   as a rival claim — and all 45 carry `1102`'s Chugach-specific adjudication text.

10. **The build log says NEST holds "25 companies twice, 25 groups, 50 rows".**
    The delivered file carries **62 `duplicate_name_variant_group` values across
    126 rows** [measured]. The reasoning is unchanged and correct; the count is
    2.5× stale, and it is the count a reader would use to size the clean-up.

11. **The ANCSA mine's next-pass list is stale on both document counts.** The log
    says *"the 273 documents that have a text layer and name no subsidiary"* and
    *"66 documents with no text layer"*; `ancsa_mine_log.csv` measures **256** and
    **58**, and its *"with a text layer 458"* should be 524 − 58 = **466**. Its
    *"distinct firms 511"* does reproduce — 512 under a re-implementation of
    `norm()`, against **540** distinct raw child-name strings — but nothing says it
    is a normalised count, so a reader comparing it to the raw file will think it
    is 29 short.

12. **A correction the build log wrote is itself now stale.** The *"223 hub
    disagreements"* table reads 212 / 20 / 14; a later block correctly notes those
    sum to 246 and gives the live file as 196 / 14 / 13 = 223. Re-measured after
    the ingest, `1130` having been re-run,
    `data/staging/nest_owner_v6/enterprise_reconciliation.csv` reads
    `ALASKA_VILLAGE_GOVERNMENT_VS_VILLAGE_CORPORATION` **185** ·
    `UNADJUDICATED_HUB_DISAGREEMENT` **19** · `ANC_TIER_DISAGREEMENT` **9** =
    **213** [measured]. **Neither the original table nor its correction matches the
    file today.** The number that matters — the raw-row count the guard actually
    has to hold — **is 1,281** (§4.8).

13. **The build log and ADR-034 both give `cedar_correction_register.csv` as "254
    applied (entity, withdrawn_key) pairs".** The file holds **178 rows, 130
    distinct pairs, 260 once the `cedar_uid` leg is counted the way `1133`'s
    `load_corrections()` counts it** [measured]. **`1133`'s own docstring says
    178** and is right, so the log and the ADR disagree with the script they
    describe. Low damage — W7 checks membership, not cardinality.

14. **`docs/DATASET_READINESS.md` reports `nest` at 2 tables;
    `docs/ARCHITECTURE.md` line 375 lists 3.** The third is
    `nest_entity_dual_role.csv` (358 rows), which the build log records as
    *"already done"* on the strength of `500`'s `^nest_` regex claiming it. The
    map does claim it; **the scoreboard still counts 2** [measured, both files as
    regenerated]. The consequence is the reason the build log gave for leaving the
    line undone: **a new table entering a collection can only move a READY score
    down**, and this one has entered the map without entering the scoreboard.

15. **`docs/methodology/README.md` says "Scoreboard, 2026-09-02: READY 9 / 13" and
    names four BLOCKED datasets.** `docs/DATASET_READINESS.md`, regenerated the
    same day, says **READY 15 / 15, BLOCKED 0, NOT_TESTED 0** [measured]. Not a
    NEST figure, but it is the header every reader of these papers meets first.

16. **Two small-print counts that did not reproduce, both low damage.** `1133`'s
    UEI-collision refusals are given as *"21 same-hub and 172 cross-hub"*;
    measured **20 and 172**. And `1072`'s own source-6a comment says *"61 rows are
    Bering Straits' shareholder-owned-businesses directory"* while the build log,
    the conservation block and the refusal file all say **57**; **57 reproduces**.
    The code comment is the one that is wrong, which is the worse place for it.
<!-- END EDITORIAL:nest -->

<!-- BEGIN GENERATED:MEASURED -->

---

# Appendix M — measured from the delivered file

*Generated 2026-09-02 by `code/1143_methodology_papers.py` from `dist/customer/nest.csv`, read whole with duckdb and never sampled. Not from `data/clean/`, not from a build log, not from `MANIFEST.csv`. Where this appendix and a document disagree, **the delivered file is right** and `verify` prints the disagreement rather than smoothing it over.*

*Grain, folded-in tables and per-column fill rates are in `dist/customer/nest__CODEBOOK.md` and are deliberately not repeated here.*

## M1 · Sources, as the delivered rows themselves record them

**`source_document`** — 4,014 of 4,798 rows populated, 123 distinct values, 15 most common shown:

| value | rows |
|---|---:|
| `native_entity_enterprise_dataset_v6_geocoded.csv (the owner's research dataset, on this machine at ~/Desktop/dissertation/data/tribal_federal_spending/clean/)` | 1,753 |
| `native_entity_enterprise_dataset_v6_geocoded.csv (the owner's research dataset, on this machine at ~/Desktop/dissertation/data/tribal_federal_spending/clean/) :: https://www.irs.gov/charities-non-profits/exempt-organizations-business-master-file-extract-eo-bmf` | 932 |
| `native_entity_enterprise_dataset_v6_geocoded.csv (the owner's research dataset, on this machine at ~/Desktop/dissertation/data/tribal_federal_spending/clean/) :: https://search.certifications.sba.gov/` | 467 |
| `2025__Bristol_Bay_Native_Corporation__2025_Bristol_Bay_Native_Corporation_Annual_Report_8-14-2025__84be0cbe.txt` | 152 |
| `2025__Ahtna_Inc.__2025_Ahtna_Inc._Annual_Report_4-28-2026__caf1c725.txt` | 63 |
| `2025__Goldbelt_Incorporated__2025_Goldbelt_Incorporated_Annual_Report_7-8-2026__fa259de5.txt` | 37 |
| `2020__Calista_Corporation__2020_Calista_Annual_Report_5-21-21__b0419760.txt` | 36 |
| `Ouzinkie_Native_Corporation_2024__6241071a.pdf` | 35 |
| `The_Kuskokwim_Corporation_2025__47b638bc.pdf` | 34 |
| `2024__Bering_Straits_Native_Corporation__2024_Bering_Straits_Annual_Report_8-12-24__9b57c8fd.txt` | 26 |
| `uicalaska_com_073d6228.html` | 23 |
| `www_asrcfederal_com_7e9a6106.html` | 23 |
| `Tanadgusix_Corporation_2025__85e33893.pdf` | 23 |
| `2025__Huna_Totem_Corporation__2025_Huna_Totem_Corporation_Annual_Report_5-1-2026__584daba7.txt` | 19 |
| `Leisnoi_Incorporated_2025__c4ab7291.pdf` | 17 |

**`source_edition_date`** — 4,224 of 4,798 rows populated, 48 distinct values:

| value | rows |
|---|---:|
| `2026-04-27` | 1,691 |
| `2026-04-30` | 1,399 |
| `2026-04-29` | 400 |
| `2025-12-31` | 206 |
| `2024-12-31` | 115 |
| `2026-05-01` | 62 |
| `2020-12-31` | 51 |
| `2021-12-31` | 31 |
| `2016` | 27 |
| `2023-12-31` | 26 |
| `2018-12-31` | 18 |
| `2017-12-31` | 15 |
| `2025` | 14 |
| `2019-12-31` | 12 |
| `2023-12-04` | 12 |
| `2017` | 12 |
| `2019` | 11 |
| `2023` | 11 |
| `2022-12-31` | 10 |
| `2025-03-25` | 9 |
| `2025-02-20` | 8 |
| `2024` | 8 |
| `2022` | 6 |
| `2016-12-31` | 6 |
| `2025-03-24` | 6 |
| `2024-10-23` | 5 |
| `2018` | 5 |
| `2021-03-22` | 5 |
| `2020` | 4 |
| `2025-01-23` | 4 |
| `2021-12-21` | 4 |
| `2026-04-17` | 4 |
| `2021-03-31` | 3 |
| `2021` | 3 |
| `2026-04-22` | 3 |
| `2026-08-03` | 3 |
| `2021-12-29` | 2 |
| `2026-06-25` | 2 |
| `2024-08-27` | 2 |
| `2025-10-24` | 1 |
| `2025-02-21` | 1 |
| `2025-03-21` | 1 |
| `2025-03-07` | 1 |
| `2022-06-17` | 1 |
| `2025-03-27` | 1 |
| `2025-03-11` | 1 |
| `2021-12-23` | 1 |
| `2026-01-19` | 1 |

**`source_url`** — 3,045 of 4,798 rows carry one. Hosts, by row count:

| host | rows |
|---|---:|
| `www.irs.gov` | 932 |
| `portal.akdbsstar.us` | 861 |
| `search.certifications.sba.gov` | 467 |
| `www.asrcfederal.com` | 46 |
| `cherokeenationbusinesses.com` | 40 |
| `web.archive.org` | 38 |
| `www.bowhead.com` | 34 |
| `www.koniag-gs.com` | 28 |
| `uicalaska.com` | 27 |
| `www.potawatomi.org` | 27 |
| `www.goldbelt.com` | 25 |
| `yulista.com` | 23 |
| `chenegamios.com` | 22 |
| `www.calistacorp.com` | 19 |
| `www.doyon.com` | 16 |
| `tlingitandhaida.gov` | 15 |
| `saltriverbd.com` | 14 |
| `www.sealaska.com` | 14 |
| `www.chugach.com` | 13 |
| `shakopeedakota.org` | 13 |

**`retrieved_date`** — 4,798 of 4,798 rows populated, 1 distinct value:

| value | rows |
|---|---:|
| `2026-09-02` | 4,798 |

### The terms rulings that bind this dataset

Quoted from `docs/PUBLICATION_POLICY.md`, which holds the rulings; this paper does not restate them from memory.

- **Owner ruling, 2026-09-02** (`<!-- BEGIN TERMS-OWNER-RULING-2026-09-02 -->`): *"So tribal websites, I actually don't care if they say it does scrape. Because if it's publicly available and you can scrape it, scrape it."* A tribal entity's own public pages may be harvested regardless of a terms statement. `source_terms_status = TERMS_STATED_RESTRICTIVE` on a Native entity's own site is now **a recorded observation, not a gate**.
- **Four things that ruling does NOT touch, and none is a terms question:** (1) technical access controls — nothing login-gated, no admin or staging paths, no exploiting a misconfiguration; (2) a natural person's data held apart from their public role — home address, personal email or phone, DOB, SSN/TIN; (3) non-tribal licensors — EMMA/MSRB bars redistribution of its output "sold or free of charge" and names "any manual process", with CUSIP Global Services as a second licensor; (4) proprietary identifiers — Casino City, D-U-N-S — held internally, never shipped.
- **A terms restriction is scoped to the SOURCE that stated it, not to the nation** (`<!-- BEGIN TERMS-SCOPE -->`), and it does not bind a third party's filing of the same fact.

## M2 · How the rows were built — the pipeline, in order

**One documented rebuild:** `py -3 code/build.py run nest --execute`. `py -3 code/build.py plan nest` prints the ordering below live; it is reproduced here so the paper stands alone.

The collection holds **3 tables**. Those with a named build stage, flagship first:

| table | rebuilt by | then enriched by (must run LAST) | status |
|---|---|---|---|
| `nest_enterprises.csv` **(flagship)** | — | — | shippable |

**A full rebuild and an in-place enricher on one file need an ordering, and the enricher must run LAST.** A `.bak_*_pre<script>` file sitting beside a table is the signal that an enricher has touched it since the last build. This has cost this project four reverts of one file in a single day.

The delivered spreadsheet is then assembled by `code/1137_customer_dataset_combine.py`, which folds supporting tables onto the flagship **only where the measured cardinality on the shared key is one**, reverts any join that moved the row count, and prefixes every joined column with its source table's stem. One-to-many tables contribute a count column instead of rows, so a money total cannot be multiplied by a join.

## M3 · How entities were attributed

Cedar keys every dataset to one identity layer. `cedar_uid` is permanent and never reused; the human-readable handle retires when an entity is reclassified, so **join on `cedar_uid`, never on the handle**. A compound handle is canonical, not broken — stripping a suffix to make a join work turns joinable rows into unjoinable ones while looking like a normalisation.

**Entity attachment in the delivered file:**

| key column | rows carrying one | distinct values | coverage |
|---|---:|---:|---:|
| `cedar_uid` | 4,798 | 472 | 100.0% |
| `owner_hub_cedar_uid` | 4,798 | 472 | 100.0% |

**An unkeyed row is often the right answer, not a defect.** ADR-010 separates *"we could not identify the entity"* — a defect — from *"there is no single entity to identify"* — the correct representation. Coverage is measured against the *resolvable* denominator, not the row count.

### What `attribution_method` means **in this dataset**

`docs/schema/attribution_method_vocabulary.json`, declared 2026-09-02: *"`attribution_method` is three different columns sharing a name — a join method, an evidence provenance, and a name-match algorithm. Each table is gated against its OWN vocabulary."* Reading one table's sense into another is how a containment match came to key a dollar.

**This dataset carries no `attribution_method` column.** The identity evidence it does carry is measured below. Do not import another dataset's term list to interpret it.

**And a RULED METHOD IS NOT A POSITIVE RULING.** `attribution_method` says WHO decided; `confidence_tier` says WHAT was decided. All 317 `elijah_ruling` EIN rows in the ledger are tier **X** — *negative* — and a script that read "the method is in the RULED set" as "the answer was yes" published 317 owner *exclusions* as confident attributions. Standing detector: `py -3 code/293_lint_bug_classes.py`. [from the record — `START_HERE.md`, defect class 1b]

### Every identity, tier and method column, measured

- **`assertion_class`** — 1 distinct value: `OWNERSHIP` 4,798
- **`evidence_class`** — 8 distinct values: `federal_certification_registry` 1,399 · `owner_research_dataset_resolver_output` 1,279 · `audited_annual_report_as_45_55_139` 861 · `parent_self_published_company_list` 504 · `owner_research_dataset_hand_ruling` 420 · `nation_self_published_enterprise_register` 193 · `parent_declared_subsidiary_list` 100 · `compiled_third_party_directory` 42
- **`hub_resolution_method`** — 5 distinct values: `source_supplied_cedar_uid` 3,939 · `exact_normalized_name` 498 · `source_supplied_handle` 263 · `ancsa_village_government_repointed_to_corporation` 83 · `accent_and_form_folded_name` 15
- **`identifier_status`** — 2 distinct values: `external_identifier` 2,509 · `cedar_minted_only` 2,289
- **`identity_scope`** — 3 distinct values: `owner_research_dataset_named_enterprise` 3,189 · `parent_asserted_subsidiary` 1,444 · `tribally_owned_entity` 165
- **`record_scope`** — 1 distinct value: `BUSINESS` 4,798

### The evidence tiers

| tier | what it means |
|---|---|
| **A** | an identifier (UEI, CAGE, EIN, declared parent UEI), or a human ruling. The only grade a dollar may be keyed on without corroboration |
| **B** | a strong name method with an independent corroborator, or inheritance from a tier-A parent |
| **C** | a weak method — containment, token subset — held as a candidate, not published as a fact |
| **X** | **refused.** A negative ruling. Never read as a confirmation |

**A tier is INHERITED from the source row, never assigned by the consumer.** The exactness of the KEY says nothing about the correctness of the LINK: 873 of 1,104 EIN rows in the ledger sit on 52 entities carrying five or more EINs each, and 821 are tier B via `need_v6`, which is 6.5% accurate and never publishes alone. [from the record — `START_HERE.md`, defect class 1]

## M4 · What is **not** in it, and why

**No row was withheld from this delivery.** Every row that passed the collection's own inclusion test is in the spreadsheet. [measured — `dist/customer/MANIFEST.csv`, `rows_withheld = 0`]

The row gate is `code/cedar_publication.row_ok`, applied identically by every publisher: a row is withheld if `publishable` is set to anything outside `{Y, y, 1, true, TRUE, blank}`, or if `source_terms_status` is outside `{SILENT, TERMS_STATED_NO_REUSE_RESTRICTION, blank}`. **A blank gate column means the gate was never evaluated for that row, not that it failed.**

Two families are refused as **COLUMNS** rather than as rows, by `cedar_publication.publishable_columns`, because the row is ours and the field is not: the proprietary identifiers (`casino_city_id` — Casino City Press; the D-U-N-S family — Dun & Bradstreet), and personal data held apart from a public role (`owner_name_raw`, `email`, `phone`, `home_address`, `personal_email`, `ssn`, `tin`, `date_of_birth`, `officer_name`, `contact_name`).

**The personal-data family became a column drop on 2026-09-02, and the change is worth understanding.** Until then it was a row gate only, and measured against the live tree that published **5 of the 587 rows** of `bia_tribal_leaders_directory.csv` — every row carrying a phone or an email was withheld whole — *and shipped the `phone` and `email` headers anyway on the five survivors*. Both halves of that were wrong. A tribal leader's name and office is a PUBLIC ROLE and belongs in the dataset; the phone number is the thing that must not travel. Dropping the field keeps 587 rows and publishes no contact data, where the row gate kept 5 rows and still advertised two contact columns. `row_ok` keeps its check as a **backstop**, for a personal field arriving under a name the list does not yet know. [from the record — the docstring of `cedar_publication.publishable_columns`, 2026-09-02]

## M5 · The money rules — which columns may be summed

**This dataset carries no numeric money column.** Nothing in it may be presented as a dollar total, and a reader who needs one has to go to the money dataset that holds it. A structure or directory table with no money column is not an incomplete money table.

### The fence, quoted verbatim from `docs/MONEY_TOTALLING_RULES.md`

That document is authoritative on which columns may be summed. It is **quoted here, never re-derived** — re-deriving a totalling rule from the data is precisely the error it exists to prevent.

**`docs/MONEY_TOTALLING_RULES.md` states no one-line rule for `nest_enterprises.csv`.** Where this dataset carries a money column and the rules document does not fence it, treat that as an open item, not as permission.

### Time span, measured

| year column | min | max | rows with no parseable year |
|---|---:|---:|---:|
| `first_observed_year` | 2016 | 2026 | 213 |
| `last_observed_year` | 2016 | 2026 | 213 |

**Read a trend against the reporting regime, not as behaviour.** `docs/ASSUMPTIONS_AND_LIMITATIONS.md` registers the breaks; a rise that begins at a rule change is the rule operating.

## M6 · Known limits, stated plainly

**Readiness: READY.** [measured — `docs/DATASET_READINESS.md`, regenerated by `py -3 code/518_dataset_readiness.py`]

| tables | grain | keys | duplicates | agg-unsafe | rebuild |
|---|---|---|---|---|---|
| 2 | 2/2 | 2/2 | clean | 0 | declared  |

The twelve-point contract a dataset is held to — grain declared and validated; keys and cardinality measured, not guessed; duplicates removed or the distinguishing dimension declared; entity attachment where the subject is an entity; every harvested row in a named disposition bucket; unresolved identity conflicts never shipping as definite facts; no double-counting path; one documented rebuild that does not destroy later enrichment; an update runbook another session can execute from the document alone; regression and semantic-diff gates over the outputs; column hygiene; and an inclusion basis on every row.

**Do not sell past the evidence.** Where this paper states a figure it was measured on the date stamped beside it, from the file named beside it. Where it states a decision it names who made it. Anything not stated here is not known.

## M7 · Fingerprint — what makes this paper stale

`verify` re-measures the four values below against `dist/customer/nest.csv` and **exits 1 if any has moved**. A methodology paper is stale the moment its dataset is rebuilt, and a stale paper that cannot say so is worse than no paper.

```json
{
  "dataset": "nest",
  "file": "dist/customer/nest.csv",
  "bytes": 7904594,
  "rows": 4798,
  "columns": 91,
  "header_sha256": "68ed932424236f2845e62ca97759603ab84ae3bbec11d7e22d0a1496d9fb526c",
  "measured": "2026-09-02"
}
```

Cross-check against `dist/customer/MANIFEST.csv`, which `code/1137_customer_dataset_combine.py` wrote at build time: it records **4798 rows × 91 columns**. The two agree.

<!-- END GENERATED:MEASURED -->
