# Methodology — NAGPRA

<!-- BEGIN GENERATED:IDENTITY -->

**`nagpra` — NAGPRA.** Delivered as `dist/customer/nagpra.csv`: **6,792 rows × 67 columns, 10.8 MB**, built from the flagship table `data/clean/nagpra_notices.csv`. Shelf `standard`; sold through **Cedar Press**; on the Cedar Press storefront. Readiness **READY**. [measured 2026-09-02 from the delivered file]

> **This block and Appendix M at the foot of this paper are GENERATED** by `code/1143_methodology_papers.py` from the delivered file itself, on every build — the same reason the codebooks are generated. Do not hand-edit either; the next build overwrites them.
>
> Everything between `<!-- BEGIN EDITORIAL:nagpra -->` and `<!-- END EDITORIAL:nagpra -->` is **hand-written and preserved byte-for-byte** across rebuilds. Put prose there and nowhere else.
>
> This paper is **not** the codebook. `dist/customer/nagpra__CODEBOOK.md` carries the grain, the folded-in tables and the per-column fill rates, and `__NOTES.txt` carries the same for a person. This paper says how the dataset came to exist and why you should believe it.
>
> Generated 2026-09-02. `py -3 code/1143_methodology_papers.py verify` **fails** if the delivered file has moved since — see §M7.

<!-- END GENERATED:IDENTITY -->

<!-- BEGIN EDITORIAL:nagpra -->
**`nagpra`. `data/clean/nagpra_notices.csv`, 6,792 Federal Register notices,
1994–2026, with `nagpra_notice_entity_bridge.csv` carrying 51,579 notice-to-party
links, 48,111 of them resolved to a Cedar entity (93.3%).** [measured
2026-09-02]

*Written 2026-09-02. This is the methodology record: what was pulled and from
where, how the rows were made, how entities were attributed, what was decided
and why, what the known limits are, and how often it has to be re-pulled. It is
not the product copy (`docs/datasets/_descriptors.json`) and not the codebook
(`docs/codebooks/`).*

**A note on the figures.** `[measured]` means the figure was re-counted from
the live file with `csv.reader` on 2026-09-02. `[from the record]` means it
came from a build log or docstring without independent measurement. Where a doc
and the data disagreed, the measurement won; the disagreements are listed at
the end.

**Readiness: READY** — one of the two datasets that cleared the line first, and
the only one in its family with replay captured. [measured —
`docs/DATASET_READINESS.md`, regenerated 2026-09-02: 4 tables, 4/4 grain, 4/4
keys, duplicates clean, C4 **93% keyed [entity]**, **C5 row conservation
4/4**]

---

## Two things that must travel with any number from this dataset

### 1. The post-2023 rise is a bounded REGIME CHANGE, not behaviour

Revised 43 CFR 10 took effect **2024-01-12**. It made the notice trigger
unconditional — *"for all human remains … in the inventory"* — deleted the
culturally-unidentifiable section, and, at **43 CFR 10.10(d)(3), set a
2029-01-10 deadline** that compresses a decades-old backlog into five years.

Notices per year [measured]: 2022 **244** → 2023 **496** → 2024 **707** → 2025
**900** → 2026 **633 through 08-31**.

**Elevated counts through 2029 are the rule operating, and they must fall after
it.** Never publish the rise as a change in institutional behaviour. It is
registered as `NAGPRA_2024_RULE` in `docs/ASSUMPTIONS_AND_LIMITATIONS.md` and
in `series_breaks.csv`.

### 2. `mni_total_stated` MUST NEVER BE SUMMED

`mni_basis` [measured]: `determinations_finding` 4,080 · `no_mni_stated`
2,357 · `single_description_statement` 193 ·
`multiple_statements_not_summed` 162. So **4,273 notices state a total and
2,519 deliberately do not**, with every enumerated figure preserved verbatim in
`mni_statements`.

**Adding them up would be arithmetic on people, performed by a machine that has
not read the notice.**

The build's own console log prints a diagnostic sum — *"total individuals,
summed over notices that state one: 158,583"* — and **that is a line in a run
log. It is not a column in any shipped table, and nothing downstream may
reproduce it.**

---

## 1. Sources, and the universe rule

**This is not a separate pull.** It is a **title-anchored cut** out of
`federal_actions.csv` (the Federal Register corpus, 156,897 documents), after
which the full text of each notice is fetched from
`https://www.federalregister.gov/documents/full_text/text/{y}/{m}/{d}/{document_number}.txt`
and cached gzipped **with GPO markup intact** under
`data/raw/federal_register/nagpra_fulltext/`.

**Title-anchored, and the reason is stated:** *"the title of a NAGPRA notice is
a controlled string. A full-text keyword net would sweep in the Review
Committee's meeting notices and the rulemakings, which are about NAGPRA but are
not repatriation notices and have no institution, no MNI and no affiliation
finding."*

Four title regexes, three notice types, three statutory stages [measured]:

| `notice_type` | rows | statutory stage |
|---|---:|---|
| `inventory_completion` | **4,801** | 25 U.S.C. 3003 — inventory and cultural affiliation |
| `intent_to_repatriate` | **1,861** | 25 U.S.C. 3004 — summary and cultural items |
| `intended_disposition` | **130** | 43 CFR 10.7 — disposition of unclaimed remains |

**Two merge decisions, both argued rather than assumed:**

- The 2023 rule **renamed** the §3004 notice from *"Intent To Repatriate"* to
  *"Intended Repatriation"*. Same legal stage, so `notice_type` is shared and
  `notice_title_form` records **which wording the document used** — *"merging
  the STAGE is correct; pretending the wording was the same would not be."*
- **`intended_disposition` is NOT merged.** It is a genuinely distinct third
  stage, where **no affiliation was determined** and disposition runs by
  statutory priority.

### Universe accounting, from the run log

Two runs on 2026-09-01. The first read a 156,772-row corpus → universe 6,774 →
6,772 built. The second, after the FR incremental added 125 documents, read
**156,897** → **universe 6,794**, fetched 22 new texts, and hit **2 permanent
HTTP 404s** — documents `96-9758-2` and `97-18431-2`, 1996 and 1997 documents
with no plain-text rendition. **They are recorded in
`logs/77_nagpra_fetch_problems_2026-09-01.csv`, not retried, and not inferred
into absence.** Final: **6,792 notices, 51,579 bridge rows.**

**Row conservation**: 156,897 rows read, 149,998+ rejected as
`federal_register_title_is_not_one_of_the_four_NAGPRA_notice_headings_prescribed_by_43_CFR_10`,
2 rejected `no_cached_full_text`, **6,792 emitted.**

### What was deliberately not used

- **A full-text keyword net** — see above.
- **Cultural detail beyond what the notice publishes.** No inference is made
  about ancestral remains or objects beyond the notice's own words.
- **Terms-restricted tribal sources** are irrelevant here: every row is a
  Federal Register publication. **The one nation absent from the bridge —
  Forest County Potawatomi — is absent because of a guard bug (§4), not because
  of terms.** Do not conflate the two absences.

---

## 2. How the rows were made

**`code/77_build_nagpra_dataset.py`**, stages `fetch` / `build` /
`conservation` / `conservation verify`. (Note `code/77_philanthropy_review_queue.py`
collides on the number.)

`code/78_content_analysis.py --nagpra-only` writes
`fr_nagpra_title_index.csv`, promoted by `code/751_fr_refresh_promote.py`.

**A `77` defect had to be fixed before the 2026-08-26 fetch was possible at
all**: `claim_host()` read `prev["pid"] > 0` and treated any lock naming a pid
as held, so `77` could never claim a host a well-behaved poller had used
previously. Held now means `active` **and** no `released` stamp.

### The tables

| table | rows | one row = |
|---|---:|---|
| `nagpra_notices.csv` | **6,792** (67 columns) | one NAGPRA notice |
| `nagpra_notice_entity_bridge.csv` | **51,579** | one (notice, named party, relationship) |
| `fr_nagpra_title_index.csv` | **6,664** | one notice, title-only index — **not a copy of the above; see §6** |
| `fr_nagpra_title_index_year.csv` | 33 | one publication year |

[measured]

---

## 3. How affiliated tribes are extracted — the precision argument

> *"NAGPRA notices are FULL of county names, and counties in this corpus are
> named Cherokee, Creek, Shawnee, Apache, Oneida, Eagle, Rio Arriba, Santa
> Barbara. A document-wide name search would attribute Cherokee County, Iowa to
> the Cherokee Nation."*

**So no name is ever searched for across the document.** The pipeline is:

1. **Locate the SPANS** that are, by the Federal Register's own drafting
   convention, lists of tribes — the consultation sentence, the shared-group-
   identity sentence, and the post-2024 bulleted "Determinations" list.
2. **Split INSIDE a span on the FR's own delimiters** — semicolons in prose,
   because **official names contain commas** (*"Pit River Tribe,
   California"*) — and newline bullets in the post-2024 layout.
3. **Hand each verbatim string to `resolve_entity`, imported from
   `code/33_apply_party_rulings.py` — the project's one resolver. No matching
   is reimplemented here.**
4. **A hard refuse-list backstops it**: a fragment that is only `creek`,
   `cherokee`, `colorado`, `ojibwe`, `shawnee`, `oneida`, `apache`, `central`,
   `eagle`, `river`, `mountain` or `santa` never resolves, whatever the
   resolver says.

**Span provenance is recorded on all 51,579 bridge rows** [measured —
`source_span_label`]: `affiliation_finding` 20,101 · `consultation_section`
10,189 · `body_sentence` 8,758 · `repatriation_sentence` 5,323 ·
`aboriginal_land_finding` 4,332 · `disposition_finding` 2,868 · two
letters-of-support combinations 8.

### Attribution and tiers

**51,579 bridge rows, 48,111 resolved (93.28%) to 568 distinct spine
entities**; 2,605 unresolved; 863 generic references. [measured]

`relationship`: `culturally_affiliated` **20,101** · `consulted` **18,947** ·
`repatriation_recipient` 5,323 · `aboriginal_land` 4,332 ·
`disposition_priority` 2,868 · `letter_of_support` 8.

`resolve_method`: alias 26,126 · containment 11,021 · core 5,461 · exact 4,007
· no_spine_match 2,383 · generic_reference 863 · conjunction_split+alias 620 ·
+containment 391 · +core 356 · **ambiguous_containment 219**.

`confidence_tier`: **B 30,133 · C 17,978 · X 863 · blank 2,605. Tier A is never
used** — *nothing in this bridge is hand-ruled, and the build correctly refuses
to claim publishable tier for an algorithmic match.*

**The rule that governs the whole bridge:** *"`party_name_verbatim` is
authoritative for what was published; `tribe_id` is not."* Every named party
gets a row with its verbatim string; `tribe_id` fills **only when the resolver
is certain**. Every one of the roughly 219 genuinely ambiguous rows carries a
**blank `tribe_id` and a `resolve_method` naming every candidate it refused to
choose between** —
`ambiguous_containment:5:Big Pine Reservation, Big Valley Rancheria, California
Valley`. **There is no row where an ambiguity was resolved by picking one.**

Cross-checks, all zero: unresolved rows carrying a `tribe_id`; resolved rows
with no `tribe_id`; a `tribe_id` absent from the spine; a bridge
`document_number` absent from the notices file.

> **A semantic caveat the log itself raises.** Tier **X** is being used for the
> 863 generic references (*"the appropriate Indian tribes"*), but
> `cedar_domain.Tier.X` means *ruled out, negative rule, never resurfaces*. A
> notice that named nobody is not a ruled-out entity. It is harmless — those
> rows carry no `tribe_id` — but the tier means something else, and a consumer
> reading X as a refusal would be misreading it.

### An alias needs three independent notices

One Federal Register notice spelling a name a particular way is a typesetter.
Two is often the same notice reissued. **Three or more independent notices is
corroboration.** The calibration is empirical: an earlier recognition-alias
pass was rejected on review at **76 of 228 proposals — a 33% error rate**, far
too high to auto-apply at n=1. Applied to **1,049 NAGPRA alias proposals: 211
accept, 168 hold, 670 refuse.**

---

## 4. Measured defects — these must travel with any number

### The hand audit, and its own stated limit

A seeded random sample (`random.seed(20260807)`), **40 rows read against the
cached FR text of their own notice**: **0 of 40 wrong entity, 0 of 40
relationship mislabelled, 2 of 40 (5.0%) coarsening** — White Earth Band and
Fond du Lac Band resolved to `TRBF-MINNCH-00`, the Minnesota Chippewa Tribe,
which is the entity on the federal list, with the band preserved in
`party_name_verbatim`. (594 rows resolve to that entity and 541 name a
component band.)

**The audit states its own limit**: a 40-row sample cannot detect a 0.4%
defect — *and the targeted scan below found exactly such a defect.*

### 212 rows confirmed misattributed (0.41%), by a state-agreement scan

38,934 resolved rows name a state; 708 disagree; **4 of those disagreements are
real**, covering 212 rows:

- **`Pueblo of San Juan` → San Juan Southern Paiute Tribe of Arizona — 105 rows
  across 49 notices, 33 of them `culturally_affiliated`.** The Pueblo was
  renamed **Ohkay Owingeh in 2005**.
- **Bishop and Lone Pine (California) → Paiute-Shoshone Tribe of the Fallon
  Reservation (Nevada) — 97 rows across 30 notices, 25
  `culturally_affiliated`.** And the mechanism here is the sharpest lesson in
  the file: under containment, Fallon's core `{paiute, shoshone}` and Bishop's
  `{bishop, paiute}` **both score 2**, so a word-order tie-break decides, and
  it prefers the candidate whose name *leads* the string. The fragment begins
  "Paiute-Shoshone" — **so the tie-break that exists to separate Shoshone-Paiute
  from Paiute-Shoshone is the very thing that selects the wrong tribe.**
- **`Kootenai Tribes of the Flathead Reservation, Montana` → Kootenai Tribe of
  Idaho, 7 rows** — re-committing the exact conflation
  `62_no_regression_check.py`'s invariant 2 exists to prevent. **The guard
  could not see it, because it reads the ledger and
  `prime_contracts_entity_year`, not this bridge.**
- `Sac and Fox Nation in Kansas and Nebraska` → Sac and Fox Nation, Oklahoma,
  3 rows.

**212 is a measured floor, not a ceiling** — the detector only covers the 82%
of resolved rows whose verbatim string names a state.

### The county guard erases one nation entirely

`refuses_alone()` refuses **any fragment containing `county`, unconditionally**
— and the spine's own `fr_official_name` for `TRBF-FSTCTY-00` is verbatim
**"Forest County Potawatomi Community, Wisconsin."**

347 refused fragments contain "County", and **328 of them are Forest County
Potawatomi under six spellings, across 271 notices.** Lost: 135 `consulted`,
**110 `culturally_affiliated`**, 70 `aboriginal_land`, 26
`disposition_priority`, 6 `repatriation_recipient`.

**Verified still live: "Forest County Potawatomi" appears 0 times in
`nagpra_notice_entity_bridge.csv` today**, against 273 rows in the lobbying
disclosures. [measured]

**No consumer should conclude anything about the Forest County Potawatomi
Community from this dataset until this is fixed.**

### 82 unparsed notices carry an unextracted 2023-rule affiliation finding

`AFFIL_LEADINS` requires the article in *"There is a connection between … and
**the** X"*, and post-2024 notices increasingly drop it or insert an adjective:
*"…and Northway Village"* (2025-04618), *"a **clear** connection…and The Osage
Nation"* (2025-10132), *"a **reasonable** connection…and Hui Iwi Kuamoʻo"*
(2025-17012). All three were tested against the live pattern: **no match.**

**And it is concentrated in the most commercially useful years** — 182 of the
371 unparsed notices are 2024–2026, and 189 carry `parse_template =
C_2024_rule`.

### 44 notices lose every party without being recorded anywhere

The parser found parties, the trap guard dropped all of them, and the guard
writes to `nagpra_refused_fragments.csv` **without adding the notice back to
`nagpra_unparsed.csv`.** So *"notices naming nobody"*, counted from the
unparsed file, **understates by 44.**

### The rest of the unparsed set is genuinely party-less

**289 of the 371 are affirmative determinations of *no* affiliation**, correctly
naming nobody. And 615 notices carry `culturally_unidentifiable = 1`
[measured], of which **0 also assert a cultural affiliation** — the two are
mutually exclusive in the data, as they should be.

### Historical names: mostly handled, and one instructive failure

2,120 bridge rows carry a name the FR itself marks *"previously listed as …"*
across 378 distinct strings, and **2,038 resolve.** The terminated-and-restored
nations all landed: Menominee 202, Klamath 60, Siletz 42, Alabama-Coushatta 72,
Ponca of Nebraska 148. **The Oneida trap is handled in both directions with no
leakage** — *Oneida Tribe of Indians of Wisconsin* → Oneida Nation WI (51),
*Oneida Nation of New York* → Oneida NY (53).

**And note that the Pueblo of San Juan case above is the same rename handled
correctly under its new name and incorrectly under its old one, in the same
dataset.**

### Section headings captured as parties

87 bridge rows are section headings read as party names — `Aboriginal Land
Tribes` 49, `Consulted and Invited Tribes` 22, `Invited and Consulted Tribes`
16. All are correctly unresolved, **but they are put in front of a human as
proposed aliases**, which is where the three-notice rule earns its keep.

---

## 5. What a buyer may total

- **Notices, and party links, and nothing else.** There is no money column.
- **`mni_total_stated` must never be summed.** See the top of this paper.
- **Never collapse `consulted` into `culturally_affiliated`.** They are
  different statutory acts under 25 U.S.C. 3003–3005: the Peabody Museum's 2001
  notice 01-8170 **consulted 32 nations and found affiliation with 15.**
- **`aboriginal_land` is a judicial fact about territory, not about ancestry.**
- **`disposition_priority` under 43 CFR 10.11 applies precisely where NO
  affiliation was found** — it is not a weaker affiliation.
- **Exclude `is_correction = 1`** — 286 of 6,792 rows. [measured]
- **Never read `removal_counties` as an affiliation signal.**
- **Never treat `resolve_status = unresolved` as an absent party** — the party
  was named; Cedar could not key it.
- **`nagpra_notice_entity_bridge.csv` is one row per (notice, party,
  relationship)** — counting rows counts *mentions*, not notices and not
  tribes.

---

## 6. `fr_nagpra_title_index.csv` — what it is, and why it disagrees on purpose

**6,664 rows** [measured], written by `code/78_content_analysis.py
--nagpra-only`. It is a **title-only index of the corpus, not the parsed notice
table**, and it deliberately differs in three ways:

- **It excludes `intended_disposition` entirely.** `notice_kind` =
  `inventory_completion` **4,803** + `intent_to_repatriate` **1,861** = 6,664,
  with no third value. 6,664 + 130 = 6,794 = the title-anchored universe.
- `inventory_completion` is 4,803 here against 4,801 in `nagpra_notices.csv` —
  a different two-row selection, not a copy.
- **Its purpose is to prove that the relevance-tier rule under-classifies
  NAGPRA.** `missed_by_tier_rule = 1` on **1,249 of 6,664 (18.7%)**;
  `relevance_tier_from_tier_rule` = `abstract_subject` 4,487 ·
  `body_only_unverifiable` **1,245** · `title_subject` 928 · `weak_term_only`
  4. Every row's `basis` is the same sentence: *"FR standardised notice title
  prescribed by 43 CFR 10; does not depend on abstract availability."* **That
  is the argument: the title is a controlled string, so a NAGPRA notice is
  identifiable even when the FR published no abstract** — and
  `fr_nagpra_title_index_year.csv` carries `share_with_abstract = 0.0` for
  1994–1997.

> **The shipped sample points at this table, and that is the wrong choice.**
> `FLAGSHIP["nagpra"]` selects the title index — ten columns of document
> metadata — while the dataset's own descriptor promises notices *"with the
> institutions and affiliated tribes named in each."* Neither is in the sample,
> and both are on disk: `nagpra_notices.csv` carries `institution_name` on
> 6,792, `institution_state` 6,680, `mni_total_stated` 4,273,
> `affiliated_entity_ids` 5,022, `removal_states` 4,433 and
> `repatriation_eligible_date` 2,782, and the bridge carries 48,111 resolved
> notice-to-tribe links. **The buyer's first question — "which notices name my
> tribe?" — has 48,111 answers on disk and the sample cannot ask it. Changing
> one line of `FLAGSHIP` is the entire fix.**

Other measured facts about the corpus: **2,085 distinct institutions**, 369
jointly issued notices; by derived type university 2,941 · museum 1,522 ·
federal agency 1,256 · other 546 · state agency 271 · historical society 219 ·
**tribal 17**. Top issuers: Peabody/Harvard 316 · American Museum of Natural
History 96 · Interior/BIA 72 · Arizona State Museum 68 · Burke Museum 68 · TVA
65. `parse_template`: `B_nps_template` 3,973 · `C_2024_rule` 2,647 ·
`A_early_freeform` 139 · `correction_unheaded` 33. **`has_resolved_entity = 1`
on 6,169 of 6,792 (90.8%).** 26 notices carry a lineal-descendant finding.

---

## 7. Refresh

| source | cadence | Cedar holds | source has |
|---|---|---|---|
| NAGPRA notices (Federal Register) | **every federal business day**, event-driven arrival | 2026-08-31 | 2026-09-01 |

[measured — `docs/REFRESH_CADENCE.json`, regenerated 2026-09-02. **NAGPRA is
the only Cedar dataset on a one-day cadence.**]

**Commands:** `py -3 code/77_build_nagpra_dataset.py fetch` then `… build`.

**What breaks on refresh: the whole bridge is rebuilt.** The universe is
title-anchored on `federal_actions.csv`, **so it moves whenever the parent
does — it moved twice on 2026-09-01 alone.** `nagpra_notice_entity_bridge.csv`
is 51,579 rows and is regenerated in full.

**And one cross-script hazard, named because it is a real deletion, not a
hypothetical:** `510_assertions.py all --apply` **rewrites
`cedar_harvest_conservation.csv` from its own ledgers and deletes NAGPRA's four
row-groups** — a plain `write_csv` in `510`. That is why a durable copy lives
at `review/nagpra_row_conservation.csv` and why the cheap repair
`py -3 code/77_build_nagpra_dataset.py conservation` exists. **Run it whenever
`62` reports `harvest_rows_unaccounted` or the scoreboard puts `nagpra` back to
BLOCKED on C5.**

---

## 8. What READY required, and why this dataset cleared it

The scoreboard emits three statuses and no fourth, against a ten-point
contract. `nagpra` and `federal-register` cleared it first, on the same point:
**C5, row conservation** — the place where most collections die, and the only
two at 100%.

`code/77 … conservation` writes a durable per-dataset ledger reconciling
`rows_in == sum(dispositions)` within one key, and **a reason of `other`,
`unknown` or `misc` is refused by name, because an unnamed rejection is exactly
the defect the ledger exists to catch.** NAGPRA's ledger is keyed by the
**output** table rather than by the source, because a NAGPRA output has no
single source table. It is gated by `510_assertions.py` invariant I13 and by
`62_no_regression_check.py`'s `harvest_rows_unaccounted`, which must be zero.

**`nagpra` is also the only dataset in its family with `replay_status =
captured`**, and it carries the family's highest identity score — **C4 at 93%
keyed at scope `entity`**, against `federal-register`'s 88% [mixed] and
`lobbying`'s 41% [mixed]. That is a property of the source: a NAGPRA notice
names its tribes, which most Federal Register documents do not.

---

## Stale claims found while writing this

1. **Every document quoting `nagpra_notices.csv` at 6,772 rows is one refresh
   behind** — including `docs/DOC_CONTRADICTIONS_2026-08-26.md`'s evening
   addendum, which was written *to correct* the build log's 6,729. Measured
   **6,792**. The bridge is **51,579**, not the register's 51,521, and
   `fr_nagpra_title_index.csv` is **6,664**, not `docs/datasets/nagpra.md`'s
   6,644.
2. **`docs/NAGPRA_BUILD_LOG.md`'s provenance section gives the parent universe
   as 156,452 Federal Register documents.** It is **156,897**, and because the
   NAGPRA universe is title-anchored on that file, every count in the log moves
   with it.
3. **`docs/WHAT_IS_MISSING.md`'s NAGPRA figures — 6,792 / 51,579 / 48,111 /
   6,664 — are current to the row**, which is worth recording in the opposite
   direction: it is the one document in this family that is not stale.
4. **The tier-X usage for generic references is a semantic mismatch, not a
   staleness**, and it is recorded in §3 because a consumer reading
   `cedar_domain.Tier.X` as "ruled out" would misread 863 rows that simply
   named nobody.
5. **The Forest County Potawatomi county-guard defect is live**, not
   historical: 0 rows in the bridge today. It is described in
   `docs/NAGPRA_BUILD_LOG.md` and has not been fixed.
<!-- END EDITORIAL:nagpra -->

<!-- BEGIN GENERATED:MEASURED -->

---

# Appendix M — measured from the delivered file

*Generated 2026-09-02 by `code/1143_methodology_papers.py` from `dist/customer/nagpra.csv`, read whole with duckdb and never sampled. Not from `data/clean/`, not from a build log, not from `MANIFEST.csv`. Where this appendix and a document disagree, **the delivered file is right** and `verify` prints the disagreement rather than smoothing it over.*

*Grain, folded-in tables and per-column fill rates are in `dist/customer/nagpra__CODEBOOK.md` and are deliberately not repeated here.*

## M1 · Sources, as the delivered rows themselves record them

**`source_url`** — 6,792 of 6,792 rows carry one. Hosts, by row count:

| host | rows |
|---|---:|
| `www.federalregister.gov` | 6,792 |

**`fetched_date`** — present in the schema and **blank on every one of the 6,792 delivered rows**. That is a coverage fact, not a formatting one: this dataset does not record that piece of provenance per row. The column is kept rather than dropped so the schema does not depend on which rows shipped.

### The terms rulings that bind this dataset

Quoted from `docs/PUBLICATION_POLICY.md`, which holds the rulings; this paper does not restate them from memory.

- **Owner ruling, 2026-09-02** (`<!-- BEGIN TERMS-OWNER-RULING-2026-09-02 -->`): *"So tribal websites, I actually don't care if they say it does scrape. Because if it's publicly available and you can scrape it, scrape it."* A tribal entity's own public pages may be harvested regardless of a terms statement. `source_terms_status = TERMS_STATED_RESTRICTIVE` on a Native entity's own site is now **a recorded observation, not a gate**.
- **Four things that ruling does NOT touch, and none is a terms question:** (1) technical access controls — nothing login-gated, no admin or staging paths, no exploiting a misconfiguration; (2) a natural person's data held apart from their public role — home address, personal email or phone, DOB, SSN/TIN; (3) non-tribal licensors — EMMA/MSRB bars redistribution of its output "sold or free of charge" and names "any manual process", with CUSIP Global Services as a second licensor; (4) proprietary identifiers — Casino City, D-U-N-S — held internally, never shipped.
- **A terms restriction is scoped to the SOURCE that stated it, not to the nation** (`<!-- BEGIN TERMS-SCOPE -->`), and it does not bind a third party's filing of the same fact.

## M2 · How the rows were built — the pipeline, in order

**One documented rebuild:** `py -3 code/build.py run nagpra --execute`. `py -3 code/build.py plan nagpra` prints the ordering below live; it is reproduced here so the paper stands alone.

The collection holds **5 tables**. Those with a named build stage, flagship first:

| table | rebuilt by | then enriched by (must run LAST) | status |
|---|---|---|---|
| `nagpra_notices.csv` **(flagship)** | `77_build_nagpra_dataset.py` | `1077_nagpra_institution_grain.py` | shippable |
| `nagpra_notice_entity_bridge.csv` | `77_build_nagpra_dataset.py` | `503_identity.py` | shippable |
| `nagpra_notice_institutions.csv` | `1077_nagpra_institution_grain.py` | `1084_nagpra_split_artefact_audit.py` | shippable |

**A full rebuild and an in-place enricher on one file need an ordering, and the enricher must run LAST.** A `.bak_*_pre<script>` file sitting beside a table is the signal that an enricher has touched it since the last build. This has cost this project four reverts of one file in a single day.

The delivered spreadsheet is then assembled by `code/1137_customer_dataset_combine.py`, which folds supporting tables onto the flagship **only where the measured cardinality on the shared key is one**, reverts any join that moved the row count, and prefixes every joined column with its source table's stem. One-to-many tables contribute a count column instead of rows, so a money total cannot be multiplied by a join.

## M3 · How entities were attributed

Cedar keys every dataset to one identity layer. `cedar_uid` is permanent and never reused; the human-readable handle retires when an entity is reclassified, so **join on `cedar_uid`, never on the handle**. A compound handle is canonical, not broken — stripping a suffix to make a join work turns joinable rows into unjoinable ones while looking like a normalisation.

**The delivered file carries no `cedar_uid`, `tribe_id` or `owner_hub_cedar_uid` column.** Where a dataset names parties but keys none of them on the row, the link lives in a bridge table and the codebook says which. A pipe-delimited list of ids in a cell is **not** a join key; join through the bridge.

### What `attribution_method` means **in this dataset**

`docs/schema/attribution_method_vocabulary.json`, declared 2026-09-02: *"`attribution_method` is three different columns sharing a name — a join method, an evidence provenance, and a name-match algorithm. Each table is gated against its OWN vocabulary."* Reading one table's sense into another is how a containment match came to key a dollar.

**This dataset carries no `attribution_method` column and no tier or method column of any kind.** Its rows are not entity attributions — they are records of a published event, and the entity link, where there is one, is made through a bridge table rather than carried on the row. Do not import another dataset's term list to interpret it.

**And a RULED METHOD IS NOT A POSITIVE RULING.** `attribution_method` says WHO decided; `confidence_tier` says WHAT was decided. All 317 `elijah_ruling` EIN rows in the ledger are tier **X** — *negative* — and a script that read "the method is in the RULED set" as "the answer was yes" published 317 owner *exclusions* as confident attributions. Standing detector: `py -3 code/293_lint_bug_classes.py`. [from the record — `START_HERE.md`, defect class 1b]

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

The gate itself is `code/cedar_publication.row_ok`, applied identically by every publisher: a row is withheld if `publishable` is set to anything outside `{Y, y, 1, true, TRUE, blank}`, or if `source_terms_status` is outside `{SILENT, TERMS_STATED_NO_REUSE_RESTRICTION, blank}`. **A blank gate column means the gate was never evaluated for that row, not that it failed.** Separately, ten column names are refused outright wherever they appear — `owner_name_raw`, `email`, `phone`, `home_address`, `personal_email`, `ssn`, `tin`, `date_of_birth`, `officer_name`, `contact_name` — and the proprietary identifier families (Casino City, D-U-N-S) drop as **columns**, not rows: the row is ours, the identifier is not.

### Known gaps — every line in `docs/WHAT_IS_MISSING.md` that names this dataset or its flagship

- **L107** *(under “THE FOUR THINGS THAT WOULD EMBARRASS US IN FRONT OF A CUSTOMER”)* — > `nagpra_notices.csv` left the old `SHOW` list behind and the sample fell to
- **L520** *(under “`federal-register` — `consultation_events.csv`, 11,402 rows”)* — **1. This is a NAGPRA table wearing a consultation label.** — CLOSED 2026-09-02 by workstream FR-DTLL: the ROW share is right and the *duplicate* reading is wrong — **1,831 distinct notices here against 6,792 in `nagpra_notices.csv`, with 4,961 NAGPRA notic...
- **L548** *(under “`nagpra` — sample flagship `fr_nagpra_title_index.csv`, 6,664 rows, 6 columns”)* — ## `nagpra` — sample flagship `fr_nagpra_title_index.csv`, 6,664 rows, 6 columns
- **L558** *(under “`nagpra` — sample flagship `fr_nagpra_title_index.csv`, 6,664 rows, 6 columns”)* — | `nagpra_notices.csv` | 6,792 (**67 columns**) | `institution_name` 6,792 · `institution_state` 6,680 · `mni_total_stated` **4,273** · `affiliated_entity_ids` 5,022 · `removal_states` 4,433 · `repatriation_eligible_date` 2,782 · `html_url` 6,792 |
- **L744** *(under “THE SHORT LIST — what this week can fix without a single download”)* — | 2 | `nagpra` | point `FLAGSHIP` at `nagpra_notices.csv` | 6,792 rows × 67 cols; bridge = 51,579 links |

### Open issues — every line in `docs/KNOWN_ISSUES.md` that names this dataset or its flagship

- **L292** *(under “A11 · S3 · `START_HERE.md` said READY 0 / 13”)* — Live: **READY 2 / 13** (`nagpra`, `federal-register`). The line sat inside the
- **L358** *(under “A17 · S1 · A validated grain proof can silently expire, and four have”)* — `fr_nagpra_title_index.csv` is in `nagpra`, one of the two **READY** datasets.
- **L620** *(under “E. Standing conditions — true, known, not defects”)* — list --unverified`) — `nagpra` closure, `federal-register` closure, the

## M5 · The money rules — which columns may be summed

**This dataset carries no numeric money column.** Nothing in it may be presented as a dollar total, and a reader who needs one has to go to the money dataset that holds it. A structure or directory table with no money column is not an incomplete money table.

### The fence, quoted verbatim from `docs/MONEY_TOTALLING_RULES.md`

That document is authoritative on which columns may be summed. It is **quoted here, never re-derived** — re-deriving a totalling rule from the data is precisely the error it exists to prevent.

**`docs/MONEY_TOTALLING_RULES.md` states no one-line rule for `nagpra_notices.csv`.** Where this dataset carries a money column and the rules document does not fence it, treat that as an open item, not as permission.

## M6 · Known limits, stated plainly

**Readiness: READY.** [measured — `docs/DATASET_READINESS.md`, regenerated by `py -3 code/518_dataset_readiness.py`]

| tables | grain | keys | duplicates | agg-unsafe | rebuild |
|---|---|---|---|---|---|
| 5 | 5/5 | 5/5 | clean | 0 | declared  |

The twelve-point contract a dataset is held to — grain declared and validated; keys and cardinality measured, not guessed; duplicates removed or the distinguishing dimension declared; entity attachment where the subject is an entity; every harvested row in a named disposition bucket; unresolved identity conflicts never shipping as definite facts; no double-counting path; one documented rebuild that does not destroy later enrichment; an update runbook another session can execute from the document alone; regression and semantic-diff gates over the outputs; column hygiene; and an inclusion basis on every row.

**1 column is blank on every delivered row** and is kept deliberately. Dropping them would make the schema depend on which rows shipped, and a buyer diffing two deliveries would watch columns appear and vanish. Sparsity is a coverage fact. They are named in the codebook.

**Do not sell past the evidence.** Where this paper states a figure it was measured on the date stamped beside it, from the file named beside it. Where it states a decision it names who made it. Anything not stated here is not known.

## M7 · Fingerprint — what makes this paper stale

`verify` re-measures the four values below against `dist/customer/nagpra.csv` and **exits 1 if any has moved**. A methodology paper is stale the moment its dataset is rebuilt, and a stale paper that cannot say so is worse than no paper.

```json
{
  "dataset": "nagpra",
  "file": "dist/customer/nagpra.csv",
  "bytes": 10843752,
  "rows": 6792,
  "columns": 67,
  "header_sha256": "9c684d1df67f6b56d5b0816233206ab1f079df6c9a072228ab47312056eeaab8",
  "measured": "2026-09-02"
}
```

Cross-check against `dist/customer/MANIFEST.csv`, which `code/1137_customer_dataset_combine.py` wrote at build time: it records **6792 rows × 67 columns**. The two agree.

<!-- END GENERATED:MEASURED -->
