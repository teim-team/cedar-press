# NAGPRA Repatriation Notice Dataset — Build Log

*Build: `code/77_build_nagpra_dataset.py`. Data written 2026-08-06 19:01.
Verified and closed out 2026-08-07. Every number below was recomputed from the
files on disk; none is carried over from the build's own run report.*

The build finished its data and died on an API spend limit before it wrote this
log or ran the regression gate. This document is that close-out: what is on
disk, what was verified, what is wrong with it, and what a consumer must not do
with it.

---

## What this is

Every Notice of Inventory Completion, Notice of Intent to Repatriate / Intended
Repatriation, and Notice of Intended Disposition published in the Federal
Register 1994–2026, cut out of the 156,452-document Dataset 9 corpus and parsed
into structure. ~~`docs/SUBSET_DATASETS.md` records that no structured public
database of this exists; that is still true. The National NAGPRA Program
publishes a notice *search*, not the notices as data.~~

> **SUPERSEDED 2026-09-02 — and this sentence is why nobody looked for
> twenty-seven days.** The "search" at `apps.cr.nps.gov/nagprapublic` is a
> server-side DataTables grid, and its JSON endpoints return the Program's
> register **as data**, with the Program's own `TotalMNI` and `TotalAFO` on
> each notice. `code/1148_nagpra_nps_databases.py` harvested six of those
> databases — **28,499 rows** — and the notice half is now the FIRST genuinely
> independent second source in Cedar: **3,950 notices AGREE with this file's
> `mni_total_stated`, 315 DISAGREE, and 49 FR document numbers are in the
> Program's register and not in this file.** Neither value is overwritten and
> no disagreement was resolved.
> `docs/NAGPRA_NPS_DATABASES_BUILD_LOG_2026-09-02.md`; decisions in ADR-040.
>
> **The rest of this document is unaffected and still current.** Everything
> below describes `nagpra_notices.csv`, which is parsed from the Federal
> Register text and is a **different observer** from the NPS register, not a
> worse copy of it. That is exactly what makes the comparison worth anything.

**These records are about ancestral human remains and funerary objects.** A
wrong tribe on a row is not a mismatch; it is a false claim about whose
ancestors those are. Every finding below is graded on that standard rather than
on ordinary data-quality standards.

## Files on disk

| File | Rows | Grain |
|---|---:|---|
| `data/clean/nagpra_notices.csv` | 6,729 | one row per notice |
| `data/clean/nagpra_notice_entity_bridge.csv` | 51,338 | one row per (notice, relationship, named party) |
| `review/nagpra_alias_proposals.csv` | 1,106 | distinct unresolved party names |
| `review/nagpra_refused_fragments.csv` | 1,089 | fragments the trap guard refused |
| `review/nagpra_unparsed.csv` | 371 | notices that yielded no party |
| `docs/codebooks/11_nagpra.md` | 76 variables | codebook |

Cached full text: 6,729 `.txt.gz` files under
`data/raw/federal_register/nagpra_fulltext/`, exactly matching the parsed
notice count. The build's closing status — *"6,729 of 6,731 fetched, 0
failures, only 2 genuine 404s"* — reconciles: `nagpra_unparsed.csv` carries
those 2 as `no_cached_full_text`, and the other 369 rows are notices whose text
was cached but named no party.

---

## Internal consistency — verified

Every check below was run against both CSVs and the spine.

| Check | Result |
|---|---|
| Bridge `document_number` values absent from the notices file | **0** |
| Duplicate `document_number` in the notices file | **0** |
| Bridge rows whose `tribe_id` is not in `cedar_entity_spine.csv` | **0** |
| Bridge `canonical_name` disagreeing with the spine for that `tribe_id` | **0** |
| Notice-level rollups (`n_*_named`, `n_*_resolved`, `*_entity_ids`, `n_parties_named`, `n_entities_resolved`, `has_resolved_entity`) recomputed from the bridge | **0 mismatches across all 6,729 notices** |
| Duplicate `(document_number, relationship, party_name_verbatim)` keys | **0** |
| Rows with `resolve_status='resolved'` but no `tribe_id` | **0** |
| Rows with a `tribe_id` but `resolve_status != 'resolved'` | **0** |
| Notices missing `source_url` / `full_text_url` | **0 / 0** |
| Codebook variables vs. data columns | **76 / 76, exact match both ways** |
| Codebook rows marked `published=1` with no description | **0** |

**The two central NAGPRA invariants hold.** 615 notices carry
`culturally_unidentifiable = 1`; **0** of them also assert a cultural
affiliation. And `mni_total_stated` is empty on every one of the 2,477 notices
whose `mni_basis` is `no_mni_stated` or `multiple_statements_not_summed` — MNI
is stated, never inferred, exactly as designed.

Resolution: 47,688 of 51,338 bridge rows (92.9%) resolve, reaching 542 distinct
spine entities. Relationships: `culturally_affiliated` 19,874 · `consulted`
18,946 · `repatriation_recipient` 5,322 · `aboriginal_land` 4,332 ·
`disposition_priority` 2,856 · `letter_of_support` 8.

---

## The hand audit of the bridge

51,338 rows is the largest entity-linkage table in the project. An unmeasured
error rate on a table that size is a liability, so it was measured the way the
FAADS build measured its own (which reported 5.0%).

**Method.** Seeded random sample, `random.seed(20260807)`, 40 rows drawn from
all 51,338. Each row was read against the cached Federal Register text of its
own notice: does the party name appear, is the recorded `relationship` the
finding the notice actually makes, and is the resolved entity the right one?
Where the same tribe list appears several times in one notice — it usually
does, under Consultation, under the aboriginal-land finding, and under the
disposition finding — the parser's own span rules were re-run against the
notice to establish which occurrence produced the row, rather than trusting the
first textual match.

**Result, as found:**

| Category | Count | Rate |
|---|---:|---:|
| Party attributed to the **wrong entity** (a namesake or unrelated nation) | 0 | **0.0%** |
| **Relationship mislabelled** (a consultation recorded as an affiliation, etc.) | 0 | **0.0%** |
| Verbatim name a mutilated fragment | 0 | 0.0% |
| Named **component band resolved to its parent** federally recognised tribe | 2 | **5.0%** |
| **Total defect rate (strict, counting the coarsening)** | **2 / 40** | **5.0%** |
| **False-attribution rate** | **0 / 40** | **0.0%** |

The two flagged rows are `White Earth Band of the Minnesota Chippewa Tribe,
Minnesota` and `Fond du Lac Band of the Minnesota Chippewa Tribe, Minnesota`,
both resolved to `TRBF-MINNCH-00` (Minnesota Chippewa Tribe). This is a
coarsening rather than a false claim — the Minnesota Chippewa Tribe is the
entity on the federal list and the bands are its component reservations — and
`party_name_verbatim` preserves which band the notice named. It is reported as
a defect because a consumer joining on `tribe_id` alone loses the band.
Across the whole bridge, 594 rows resolve to `TRBF-MINNCH-00` and 541 of them
name a component band rather than the umbrella.

Six rows were adjudicated in detail before being passed: 2018-09177
(affiliation), 2013-21251 and 2022-08351 and 2023-01840 (aboriginal land),
2020-20294 and 2020-20295 and 2021-01900 and 2021-23490 (disposition
priority), 00-31658 and 04-22827 and 03-6217 (repatriation sentence), and
01-11142 (affiliation). Every one was confirmed correct against the statutory
lead-in that produced it.

**The audit's limit, stated plainly.** A 40-row sample cannot detect a defect
that affects 0.4% of rows. The targeted scan below found exactly such a
defect — 212 rows — and a random 40 would be expected to contain 0.18 of them.
**The 0.0% false-attribution rate is the as-found rate of the table at large;
it is not a statement that the table has no misattributions.** It does. They
are concentrated, and they are named below.

---

## What this build got wrong

### 1. Two namesake misattributions, 202 bridge rows — the largest defect

A targeted scan compared the state named inside each party's verbatim string
against the state of the spine entity it resolved to. 38,934 resolved rows name
a state; 708 (1.82%) disagree. Most disagreements are artefacts of the test
(`Delaware Tribe of Indians` is not in Delaware; `Standing Rock Sioux Tribe of
North & South Dakota` is coded ND). Four are real:

**(a) `Pueblo of San Juan` → San Juan Southern Paiute Tribe of Arizona —
105 rows, 49 notices.** The Pueblo of San Juan, New Mexico was renamed Ohkay
Owingeh in 2005 and is in the spine as `TRBF-OKYOWG-00` (NM). The notices
resolved instead to `TRBF-SNJUAN-00`, whose `fr_official_name` is *San Juan
Southern Paiute Tribe of Arizona* — a different nation in a different state.
33 of the 105 rows carry `relationship = culturally_affiliated`, the legal
finding under 25 U.S.C. 3001(2). This is the exact failure the build was
designed to prevent: a historical name landing on a namesake.

**(b) California Bishop and Lone Pine → Paiute-Shoshone Tribe of the Fallon
Reservation, Nevada — 97 rows, 30 notices.** `Paiute-Shoshone Indians of the
Bishop Community of the Bishop Colony, California` and the Lone Pine equivalent
resolved to `TRBF-FALLON-00` (NV). Both correct entities exist in the spine:
`TRBF-BISHOP-00` (Bishop Paiute, CA) and `TRBF-LNPINE-00` (Lone Pine, CA).
25 of the 97 rows are `culturally_affiliated`.

The mechanism is precise and worth recording. Under containment, Fallon's core
`{paiute, shoshone}` and Bishop's core `{bishop, paiute}` both sit inside the
fragment and both score 2, so the word-order tie-break in `resolve_entity`
decides — and it prefers the candidate whose name *leads* the string. The
fragment begins "Paiute-Shoshone", so Fallon wins. **The tie-break that exists
to separate Shoshone-Paiute from Paiute-Shoshone
(`cedar_domain.STANDING_DISAMBIGUATIONS`) is the thing that selects the wrong
tribe here.** `accept()` in script 77 cannot catch it, because Fallon's core is
not a subset of `NON_DISTINCTIVE`.

**(c) `Kootenai Tribes of the Flathead Reservation, Montana` → Kootenai Tribe
of Idaho — 7 rows.** The Flathead Reservation is the Confederated Salish and
Kootenai Tribes, `TRBF-CSKTFR-00` (MT), which is in the spine. This
re-commits the Kootenai/CSKT conflation that invariant 2 of
`code/62_no_regression_check.py` exists to prevent. **The guard could not see
it**: it measures `cedar_identifier_ledger_final.csv` and
`prime_contracts_entity_year.csv`, not this bridge.

**(d) `Sac and Fox Nation in Kansas and Nebraska` → Sac and Fox Nation,
Oklahoma — 3 rows.** Should be `TRBF-SCFXMO-00`.

**Total confirmed misattributed rows: 212 of 51,338 (0.41%), or 0.44% of the
47,688 resolved rows.** The detector only covers rows whose verbatim string
names a state — 82% of resolved rows — so 212 is a measured floor, not a
ceiling.

### 2. The county guard silently erases the Forest County Potawatomi Community — 328 party mentions

`refuses_alone()` refuses any fragment containing the token `county`,
unconditionally and at any length. The spine's own `fr_official_name` for
`TRBF-FSTCTY-00` is, verbatim, **`Forest County Potawatomi Community,
Wisconsin`**. The guard therefore refuses a name the spine holds exactly, and
the tribe's consultations and affiliations never enter the bridge.

- 347 refused fragments contain `County`; **328 of them are the Forest County
  Potawatomi Community** under six spellings.
- 271 distinct notices affected.
- Lost by relationship: 135 `consulted`, **110 `culturally_affiliated`**,
  70 `aboriginal_land`, 26 `disposition_priority`, 6 `repatriation_recipient`.
- Every one of them resolves correctly to `TRBF-FSTCTY-00` when the guard is
  bypassed (`alias` and `containment` matches, confirmed).

This is the Narragansett/"island" failure the function's own docstring warns
about, in the one case the narrow fix did not cover — a guard against false
attribution that instead erases a nation's consultation record. The remaining
19 county-bearing refusals are genuine (`Saguache County`, `Siskiyou County,
CA`, `Lyon County`) and should stay refused.

**No consumer should conclude anything about the Forest County Potawatomi
Community from this dataset until this is fixed.**

### 3. The 2023-rule affiliation sentence is missed when the nation takes no article — 82 notices

`AFFIL_LEADINS` matches `There is a connection between … and **the** X`, with
the article required. Notices published under the 2023 rule (43 CFR 10, eff.
2024-01-12) increasingly write the finding without one, or with an adjective
the pattern does not allow:

- `There is a connection between the human remains and associated funerary
  objects described in this notice and **Northway Village**.` (2025-04618)
- `There is a **clear** connection between … and The Osage Nation.` (2025-10132)
- `There is a **reasonable** connection between the cultural item described in
  this notice and Hui Iwi Kuamoʻo.` (2025-17012)

All three were tested against the live `AFFIL_LEADINS` list: **no match**.

**82 of the 371 unparsed notices carry a `There is a … connection between … and
X` finding that the parser did not extract.** The loss is concentrated in the
newest and most commercially useful years: 182 of the 371 unparsed notices are
2024–2026, and 189 of them are `parse_template = C_2024_rule`. Recovered
examples include the Ponca Tribe of Nebraska (4 notices), The Osage Nation,
the Pawnee Nation of Oklahoma, Onondaga Nation, Wilton Rancheria, the Native
Village of Kotzebue, and the Eastern Shoshone Tribe.

The remaining 289 unparsed notices are genuinely party-less on inspection:
sampled 2023–2025 notices state *"there is no lineal descendant and no Indian
Tribe or Native Hawaiian organization with cultural affiliation"* or *"there is
no cultural affiliation between the human remains … and any Indian Tribe"* —
affirmative determinations of no affiliation, correctly naming nobody.

### 4. Forty-four notices lose every party without being recorded anywhere

413 notices have no bridge row. 369 are listed in `nagpra_unparsed.csv`.
**44 are listed nowhere.** These are notices where the parser *did* find
parties but every one was later dropped by the trap guard, which writes to
`nagpra_refused_fragments.csv` (all 44 appear there) but does not add the
notice back to the unparsed file. A consumer counting "notices naming nobody"
from `nagpra_unparsed.csv` understates it by 44. Several are Forest County
Potawatomi cases (2022-17287, 2022-25127).

### 5. Section headings captured as party names — 87 bridge rows

`Aboriginal Land Tribes` (49 rows), `Consulted and Invited Tribes` (22),
`Invited and Consulted Tribes` (16) are headings in the notice layout, not
nations. All 87 are correctly unresolved, so no false attribution results, but
they are phantom party rows and they are put in front of a human as proposed
tribe aliases in `nagpra_alias_proposals.csv`.

### 6. The codebook's row count is stale

`docs/codebooks/11_nagpra.md` and the 76 `nagpra` rows in
`data/clean/codebook_master.csv` were generated 2026-08-06 **18:27**; the data
was written **19:01**. They record **47,460 rows across 2 files**. The true
figure is **58,067** (6,729 notices + 51,338 bridge rows).

The variable list is unaffected — all 76 columns match the data exactly in both
directions, and `codebook_undocumented_public` remains **0**. Only the row
count and the `pct_filled` percentages are stale. `code/41_build_codebooks.py`
was **not** re-run as part of this close-out: it regenerates every dataset's
codebook, and four other agents have written to `data/clean/` since 18:27, so
re-running it here would fold their in-flight work into a documentation
artefact and risk the guard. It should be re-run once the concurrent builds
land.

---

## Things that are right, and that a reader might mistake for defects

- **`resolve_method` values like `ambiguous_containment:2:Delaware Nation,
  Delaware Tribe of Indians` are correct behaviour.** The resolver refused to
  choose between two real candidates and left `tribe_id` empty. The party is
  still recorded with its verbatim name. This is the design working.
- **1,106 alias proposals / 2,794 mentions are not failures.** They are
  historical names, non-federally-recognised groups, and Native organisations
  that are not spine entities: the Office of Hawaiian Affairs (99), the
  Arapahoe/Arapaho Tribe of the Wind River Reservation (138 across two
  spellings), Hui Mālama I Nā Kūpuna ʻO Hawaiʻi Nei (64), the Wanapum Band
  (63, explicitly *"a non-Federally recognized Indian group"* in the FR's own
  words), the Kumeyaay Cultural Repatriation Committee (20). Recording them
  unresolved is the correct treatment; dropping them would erase consultations
  that happened.
- **The refused-prose fragments are correct refusals.** 733 of the 1,089 are
  `prose_not_a_name`, and the top entries are boilerplate — *"has determined
  that the cultural items listed in this notice meet the definition of
  unassociated funerary objects"* (142 times). These are span over-reaches
  caught before they became data, which is what the guard is for.
- **`confidence_tier` is never `A`.** Nothing in this bridge is hand-ruled, and
  the build correctly refuses to claim publishable tier for an algorithmic
  match. Tiers present: `B` 29,821 (exact/alias), `C` 17,867
  (core/containment/split), `X` 863 (generic reference), blank 2,787
  (unresolved).

**One semantic caveat:** the build uses tier `X` for the 863 generic references
(*"the appropriate Indian tribes"*). `cedar_domain.Tier.X` means *"ruled out,
negative rule, never resurfaces"*. A notice that named nobody is not a
ruled-out entity. The rows are harmless — they carry no `tribe_id` — but the
tier is being used for a meaning it does not have.

## Historical names — the three-decade problem

This was the build's stated hard case and it is, with the exceptions named
above, handled well. 2,120 bridge rows carry a name the Federal Register itself
marks as a rename (`previously listed as …`), across 378 distinct strings;
2,038 of them resolve.

Terminated-then-restored nations all landed correctly: **Menominee** (202
rows), **Klamath** (60), **Confederated Tribes of Siletz Indians** (42),
**Alabama-Coushatta** (72), **Ponca Tribe of Nebraska** (148). Renames landed
correctly: Devils Lake Sioux → **Spirit Lake**, Cheyenne-Arapaho Tribes of
Oklahoma → **Cheyenne and Arapaho Tribes** (118), Pueblo of San Juan →
**Ohkay Owingeh** where the modern name is used (44), Huron Potawatomi →
**Nottawaseppi** (116), Mashpee Wampanoag Indian Tribal Council → **Mashpee**
(29), Sisseton-Wahpeton Sioux → **Sisseton-Wahpeton Oyate** (33).

The Oneida trap is handled in both directions: `Oneida Tribe of Indians of
Wisconsin` → Oneida Nation (Wisconsin) (51 rows), `Oneida Nation of New York`
→ Oneida (NY) (53 rows). No leakage between them.

The failures are the four in §1 — and note that the Pueblo of San Juan case is
the *same* rename handled correctly under its new name and incorrectly under
its old one, in the same dataset.

## How to use this dataset

- **`party_name_verbatim` is authoritative for what was published;
  `tribe_id` is not.** The codebook says so and this audit confirms why.
- **Never collapse `relationship`.** `consulted` and `culturally_affiliated`
  are different legal findings under 25 U.S.C. 3003–3005. A notice routinely
  consults many more nations than it finds affiliated with. `aboriginal_land`
  is a judicial fact about territory, not about ancestry; `disposition_priority`
  under 43 CFR 10.11 applies *precisely where no affiliation was found*.
- **Never sum `mni_total_stated` as a population figure.** It is populated only
  where the notice states one total for itself (4,252 notices); 2,477 notices
  state none or state several, and those are deliberately empty.
- **Exclude `is_correction = 1`** when counting repatriation activity.
- **Do not use the Forest County Potawatomi Community, the Bishop Paiute Tribe,
  the Lone Pine Paiute-Shoshone Tribe, Ohkay Owingeh, the San Juan Southern
  Paiute Tribe, the Fallon Paiute-Shoshone Tribe, the Kootenai Tribe of Idaho,
  or CSKT from this dataset until §1 and §2 are fixed.**

## Open items, in priority order

1. Fix the four namesake misattributions (§1). 212 rows. The Bishop/Fallon case
   needs a state-agreement condition on the containment tie-break, not a new
   guard — `cedar_domain.STANDING_DISAMBIGUATIONS` already names the pair.
2. Narrow the `county` rule in `refuses_alone()` to fragments that are *only* a
   county reference (§2). 328 mentions, 271 notices, one federally recognised
   tribe currently invisible.
3. Add the article-optional and adjective-tolerant 2023-rule connection pattern
   to `AFFIL_LEADINS` (§3). Recovers 82 notices, concentrated in 2024–2026.
4. Record the 44 all-refused notices in `nagpra_unparsed.csv` (§4).
5. Refuse the three section headings as generic references (§5).
6. Re-run `code/41_build_codebooks.py` once concurrent writes to
   `data/clean/` have landed (§6).
7. Consider extending `code/62_no_regression_check.py` to watch this bridge —
   the Kootenai/CSKT conflation returned in a file the guard does not read.

## Provenance

- Universe: title-anchored selection from `data/clean/federal_actions.csv`
  (Cedar Press Dataset 9), 156,452 Federal Register documents.
- Full text: `https://www.federalregister.gov/documents/full_text/text/{y}/{m}/{d}/{document_number}.txt`,
  cached raw with GPO markup intact under
  `data/raw/federal_register/nagpra_fulltext/`. Every notice row carries
  `source_url`, `html_url`, `pdf_url` and `full_text_url`.
- Entity resolution: `resolve_entity` from `code/33_apply_party_rulings.py`,
  the project's one resolver (standing rule 8). `data/spine/` was read-only
  throughout; no spine row was written by this build.

---

## REFRESH 2026-08-26

**6,729 → 6,772 notices (+43); bridge 51,521 rows. Newest `publication_date`
2026-08-24, i.e. 2 days back, which is the source's own gap since the last
notice — not ours.** Before/after measurement: **`docs/REFRESH_CADENCE.md`
PART 5**, which is where these numbers are maintained.

The universe is title-anchored on `federal_actions.csv`, so it moved when the
parent corpus did (`code/342_pull_federal_register_incremental.py`, +320 FR
documents the same evening). Universe 6,774; 43 texts fetched; **2 returned
HTTP 404** — `96-9758-2` and `97-18431-2`, 1996/1997 documents with no
plain-text rendition. That is a fact about those two objects, recorded in
`logs/77_nagpra_fetch_problems_2026-08-26.csv`, not retried and not inferred
into absence. 6,774 − 2 = the 6,772 built.

**The `provenance` note above still says 156,452 FR documents. It is now
156,772.** The universe count is what matters and it is restated here.

**A `77` defect fixed to make the fetch possible.** `claim_host()` read
`prev["pid"] > 0` alone and treated any lock naming a pid as held. A lock keeps
its holder's pid forever; a poller that releases correctly leaves
`active: false` and a `released` stamp behind it. So 77 could never claim a host
that a well-behaved poller had used — it queued behind a lock released nine
seconds earlier and exited having fetched nothing. Held now means `active` AND
no `released` stamp. Backup: `code/77_build_nagpra_dataset.py.bak_2026-08-26_pre_342_pull_federal_register_incremental`.

### TWO THINGS THAT MUST TRAVEL WITH ANY NUMBER OUT OF THIS DATASET

**1. The post-2023 rise is a REGIME CHANGE and is BOUNDED.** Revised **43 CFR
10 took effect 2024-01-12**: the notice trigger became unconditional (*"for all
human remains … in the inventory"*), the culturally-unidentifiable section was
deleted, and **43 CFR 10.10(d)(3) sets a 2029-01-10 deadline** compressing a
decades-old backlog into a five-year window. Notices/year: 244 (2022) → 496
(2023) → 707 (2024) → 900 (2025). **Elevated counts through 2029 are the rule,
and they must fall after it.** Never publish the rise as a change in
institutional behaviour. Already recorded as `NAGPRA_2024_RULE` in
`docs/ASSUMPTIONS_AND_LIMITATIONS.md` and in `series_breaks.csv` — do not
re-derive it.

**2. `mni_total_stated` MUST NEVER BE SUMMED.** Those are counts of human
beings. **This build's own console log prints a sum** — *"total individuals,
summed over notices that state one: 158,327"*. That is a diagnostic in a run
log; it is not a column in any shipped table and nothing downstream may
reproduce it.


---

## 2026-09-02 — THE INSTITUTION PARSER FABRICATED AN AGENCY, AND THE GATE THAT WATCHED IT READ ONE COLUMN OF SIX

*Pass: `code/1154_nagpra_fr_grain_audit.py report` (measurement), the split rule
in `code/cedar_nagpra_split.py`, applied through `code/1077_nagpra_institution_grain.py`.
Every figure below is a full census of `data/clean/nagpra_notices.csv`
(6,792 rows) or `nagpra_notice_institutions.csv`; nothing is sampled.*

### What was shipping

`02-7009`, title verbatim:

> ... in the Possession of the **Louisiana Department of Culture, Recreation,
> and Tourism, Division of Archaeology**, Baton Rouge, LA

shipped as:

| column | value |
|---|---|
| `institution_name` | `Louisiana Department of Culture, Recreation; Tourism, Division of Archaeology` |
| `institution_primary` | `Louisiana Department of Culture, Recreation` |
| `institution_count` | `2` |
| `institution_city` | *(blank)* |
| `institution_state` | *(blank)* |
| `institution_names_all` | `Louisiana Department of Culture, Recreation and Tourism, Division of Archaeology` |

`Louisiana Department of Culture, Recreation` is not an agency that exists, and
**Baton Rouge went to the half that is not one either** — which is why the
notice ships with no city at all.

### The reason it survived a gate named after it

`code/846_session_audit.py::_split` is called *"no institution name is split
mid-name in NAGPRA notices"*. **It read `institution_names_all` and nothing
else.** The 2026-09-02 repair had been applied to that one column, so the gate
passed while `institution_name`, `institution_primary`, `institution_count`,
`institution_city` and `institution_state` all carried the fabrication — and
`institution_primary` is the column a buyer actually keys on. This is
`docs/AGENT_FIELD_GUIDE.md` rule 6 (*write to the columns the CONSUMER reads*)
and the signature defect (*a check that does not measure its own name*) in one
row. `code/1084_nagpra_split_artefact_audit.py` had already printed the debt —
`nagpra_notices_rows_carrying_the_same_fabrication: 51` — and said the fix
belonged in the parser. It does, and it is there now.

### The fix: ONE split rule, in one file, imported three times

`code/cedar_nagpra_split.py` is the only copy. `77_build_nagpra_dataset.py`
(`institution_parts`), `1077_nagpra_institution_grain.py`
(`split_institutions`) and `1084_nagpra_split_artefact_audit.py` (detector A1,
which imports `KW` and `POSTAL` from it) now share it. Two ladders for one
number is what drifted here.

The `, and ` split is **provisional**. It is undone, and the fragments rejoined
into the one contiguous substring of the title that spans them, only when all
four hold: the left fragment's last comma-segment is a bare enumerated noun
(no institution keyword, not a postal state); the right fragment's first
comma-segment is at most three words; the two share no token; and the pair is
not one link of a longer `, and ` chain.

### Measured, before and after

| | before | after |
|---|---|---|
| titles carrying a semicolon | 64 | 64 |
| titles on the legacy `, and ` path | 6,728 | 6,728 |
| — of those, the legacy rule split | 328 | 328 |
| adjacent pairs tripping the bare-noun test | 19 | 19 |
| — rejoined | 0 | **15** |
| — left split **and flagged with a reason** | — | **4** |
| bridge rows (`nagpra_notice_institutions.csv`) | 7,234 | **7,219** |
| notices naming more than one institution | 392 | **377** |
| notices with a blank `institution_state` | 119 | **104** |
| 1084 rows flagged as a splitting artefact | 77 | **47** |
| 1084 detector A1 | 38 rows / 19 notices | **8 rows / 4 notices** |
| `nagpra_notices` rows carrying the same fabrication (1084's own count) | 51 | **36** |
| genuine `institution_name` defects (1154) | — | **10 of 6,792 (0.15%)** |
| `institution_state` values that are not a USPS state | 0 | 0 |
| `institution_count` disagreeing with `institution_names_all` | 14 | **0** |

`02-7009` now reads one institution, `Louisiana Department of Culture,
Recreation, and Tourism, Division of Archaeology`, in Baton Rouge, LA.
So do `2021-17065` (New York State Office of Parks, Recreation, and Historic
Preservation) and thirteen others.

### FLAGGED, NEVER GUESSED — the four that were left alone

Two new columns on `nagpra_notices.csv`, `institution_split_flag` and
`institution_split_basis`, carry the reason with the row:

* `E7-9453`, `E7-10715` — `ambiguous_oxford_chain`. *"Augusta State University,
  Department of History, and Anthropology, and Philosophy, Archaeology
  Laboratory"* joins three fragments with `, and `; which of them form one
  institution is not decidable from the text.
* `2014-21477`, `2014-21482` — `right_side_is_its_own_name`. *"California State
  University, Long Beach, and California State University, Sacramento, CA"*
  trips the bare-noun test on *Long Beach* and **is two real campuses**.
  Merging it would fabricate a merger — the same error inverted.

### Checks that are proven to fire

* `1077` gained **I8**, a FLOOR on the intended delta (`merged_pairs >= 15`),
  not a conservation check — field guide rule 5. Proven by a fixture that
  neuters `apply_merges`: exit 1, and `I8` is the named invariant that fires.
  `1077 verify` also exits 1 against the pre-fix table.
* `846::_split` now reads **three** name columns and re-derives from the
  notice's own title, and additionally requires that a **single-holder** notice
  whose title ends in `, City, ST` carries that city on its primary
  institution. Proven both ways: it returns FAIL on the pre-fix table
  (3 notices) and PASS on the fixed one; the city half was proven by injecting
  a stranded city into a real single-holder row (`94-17582`).
  *A first draft of the city test did not condition on `institution_count` and
  fired on 15 legitimately joint notices — the two CSU campuses, the three
  Baylor museum names, USACE Omaha + the Hood Museum. That is this repo's
  signature defect committed inside the check written to catch it, and it is
  recorded here rather than quietly corrected.*

### A wart removed on the way

`1077.patch_builder` tested `if BAD_SPLIT in new:` **before**
`elif "INST_SEMI_RE" in new:`, and `BAD_SPLIT` is the literal `INST_SPLIT_RE`
definition, which survives the patch. So every 1077 run prepended its comment
block to `77` again: **four identical copies of
`INST_SEMI_RE = re.compile(r";")`** were in the file. Collapsed to one; the
already-present test now comes first.

### WHAT IS STILL OWED — measured, not implied

* **36 `nagpra_notices` rows still carry a fabrication that 1084 repairs only
  in the bridge** (down from 51). They are detectors A2 (a delimiter inside a
  parenthetical, 14 rows), A3 (a Federal Register status word such as
  `Republication` shipped as a holder, 10), A4 (a fragment beginning
  mid-sentence, 18), A5 (the possession locution retained so the real holder is
  downstream, 13) and A7 (1). Each is repaired verbatim in
  `nagpra_notice_institutions.institution_name_repaired` and each is a
  candidate for the same treatment the `, and ` rule just got: move the
  decision to the moment of the split.
* **`dist/customer/nagpra.csv` is stale by 17 rows against
  `data/clean/nagpra_notices.csv`** and `846` reports
  `1137 verify rc=1 - nagpra: STALE`. Re-publishing is not this lane's to do:
  run `py -3 code/1137_*.py build nagpra`.
