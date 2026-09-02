# Compacts dataset — build log, 2026-08-05

Build of the Cedar Press **Tribal-State Gaming Compacts** dataset per
`COMPACT_DATASET_PLAN.md`. Run log: `logs/15_compacts_2026-08-05.log`.
Code: `code/15a_compacts_inventory.py`, `15b_build_compact_index.py`,
`15c_terms_pilot.py`, `15d_terms_extract.py`, `15e_finalize_terms.py`.
Sources: `data/raw/external/compacts/` (+ `SOURCE_MANIFEST.md`).
Outputs: `data/clean/compacts.csv`, `compact_versions.csv`, `compact_terms.csv`,
`compact_events.csv`.

Nothing in `data/spine/`, `data/clean/cedar_*` or `review/` was touched.
`C:\Users\esm247\Desktop\votingpatterns\` was read only; all sources were copied
out before use and the build reads exclusively from the local copies.

---

## 1. PDF inventory and filename parse rate

| | |
|---|---|
| PDFs copied to `data/raw/external/compacts/pdf/` | **1,187** (2.0 GB) |
| Text sidecars copied to `text/` | 1,187 |
| BIA index rows in `index/bia_compact_index.csv` | 1,189 |

**Filename parse (`15a`).** Filenames follow six prefix variants
(`508_compliant_`, `508 Compliant `, `508 Compliant.`, `508 Compliant` with no
separator, doubled spaces, `508 C `) and two date orders (`YYYY.MM.DD`,
`MM.DD.YYYY`; both unambiguous because the four-digit year anchors the order).

| Outcome | n | share |
|---|---:|---:|
| Full date parsed | 1,145 | 96.46 % |
| — `YYYY.MM.DD` | 1,130 | |
| — `MM.DD.YYYY` | 15 | |
| **Year only — recorded as a year, never promoted to a date** | 15 | 1.26 % |
| **No date token at all** | 27 | 2.27 % |
| **Does not parse to a date** | **42** | **3.54 %** |
| Non-empty tribe token | 1,187 | 100 % |
| Clean parse (date *and* tribe) | 1,145 | 96.46 % |

The 42 non-parsing filenames are listed verbatim in the run log. They include
malformed dates that were deliberately **rejected rather than repaired** —
`2106.03.10` (year out of range), `202.11.17` (truncated year), `2023.22.01`
(month 22), `2023.12,22` (comma), `2025.02.206` — plus month-only stamps
(`2024.01`, `2024.04`), year-only stamps, and 22 files with no date at all
(`Fifth Amendment.pdf`, `idc-038311.pdf`, `Lower Sioux Indian Community Compact
Amendment Blackjack.pdf`, several `… Secretarial Procedures.pdf`).

**Filenames are not used to date anything in the outputs.** Against the BIA
index date, filename-parsed dates agree on 1,112 and **disagree on 32**
(e.g. `508 Compliant 2019.05.08 Hopi Tribe …` carries 2019 in the name and
2018-05-08 in the index; the eight Lower Sioux amendment files carry their
own execution years while BIA dates the whole batch 2023-10-04). Dates come
from the BIA index and, preferentially, from the Federal Register notice URL.

**Effective-date basis.** Where BIA supplies an FR notice URL, the date embedded
in that URL matches the BIA index date on 999 of 1,007 rows (99.2 %). A compact
takes effect on FR publication (25 U.S.C. 2710(d)(3)(B)), so
`original_effective_date` uses the FR publication date where available
(575 compacts) and the BIA index decision date otherwise (133 compacts), with
`original_effective_date_basis` recorded per row.

**Reconciliation.** 25 index rows store the filename without its `.pdf`
extension; after normalizing, every index row but one resolves to a local PDF.
Two index rows carry `pdf_filename = "Federal Register Link"` (BIA linked a
govinfo FR PDF instead of the compact) and one carries a blank filename.

---

## 2. Prior-extraction assessment (honest)

Both prior products were re-measured from scratch rather than trusted.

### `bia_compact_content_v2.csv` — 1,188 rows × 55 columns
A broad regex sweep. The **index fields are solid** (state / tribe / title /
decision / date / FR url ≥ 85 % populated). The **term fields are thin**, and
the coverage report shipped alongside it is accurate:

| field | substantively populated |
|---|---:|
| `slot_cap` | 26 (2.19 %) |
| `term_years` | 46 (3.87 %) |
| `revenue_share_flat_fee_annual` | 43 (3.62 %) |
| `has_mfn_clause` | 42 (3.54 %) |
| `revenue_share_tiers_json` | 73 (6.14 %) |
| `revenue_share_pct` | 246 (20.71 %) |
| `has_exclusivity` | 229 (19.28 %) |
| `effective_date_extracted` | 7 (0.59 %) |

Structural limitations for this build's purposes: **no page citation on any
field**, and no verbatim quote for most fields — so a term cannot be traced to
where it was said, which the plan requires (`source_page`, and "every term
carrying source and page"). It also has no `applies_to` concept, so a
facility-specific cap and a tribewide cap are indistinguishable. Text quality
is reasonable: median 48,868 characters, 5th-percentile alpha ratio 0.887,
47 rows self-flagged `needs_reocr`, 60 texts under 2,000 characters.

### `bia_compact_term_v3.csv` — 1,189 rows
A dedicated term-length pass, better documented than v2 (`…_REPORT.md` lists
its false-positive scrubs). **204 hits (17.16 %)**, confidence 0.70–0.95, eight
phrasing families. Cross-checked against v2: on the 39 rows where both fire the
values are **identical, 0 conflicts** — v3 is a strict superset of v2 on term
length and the two passes corroborate each other.

### Verdict
Both are credible for what they claim and were **kept for audit** in
`data/raw/external/compacts/prior_extractions/`, but **neither was used as an
input** to this build's terms layer, for two reasons: no page citations, and no
`applies_to`. The index layer here is rebuilt from `bia_compact_index.csv` and
the archived raw HTML; the terms layer is re-extracted page-wise from the PDFs.

**A note on the `text/` sidecars:** they contain no page delimiters (0 form
feeds). They cannot support `source_page`, which is why every term in this
build is re-extracted from the PDFs with PyMuPDF.

---

## 3. Defect found in the primary source

**The BIA index page's `Tribes` column is misaligned with its `Title` column on
61 of 1,189 rows (5.1 %).** The tribe name slips down the alphabetical tribe
list while the Title and the linked PDF stay correct:

| BIA "Tribes" column | The linked document actually is |
|---|---|
| Mississippi Band of Choctaw Indians (CT) | Mohegan Tribe of Indians compact |
| Mashantucket Pequot Indian Tribe (MA) | Mashpee Wampanoag Tribe compact |
| Narragansett Indian Tribe (NY) | Oneida Indian Nation compact |
| Nansemond Indian Nation (RI) | Narragansett Indian Tribe compact |
| Lumbee Tribe of North Carolina (CT) | Mashantucket Pequot secretarial procedures |
| Kialegee Tribal Town (OK) | Miami Tribe compact |
| Miami Tribe of Oklahoma (OK) | Modoc Tribe compact |
| Yocha Dehe Wintun Nation (CA) | Yurok Tribe compact |
| Middletown Rancheria (CA) | Mooretown Rancheria compact |

Conflicts cluster in Oklahoma (22), California (12), Oregon (10) and
Washington (9). This was verified against the **archived raw HTML**
(`index/bia_html/`) — the misalignment is BIA's, not a scraping artefact, and it
is inherited unflagged by every prior extraction built on this index.

**Resolution.** When the two columns share no distinctive token and the Title
agrees with the PDF filename, the tribe is taken from the Title. The BIA value
is preserved verbatim in `bia_tribes_column`, the basis in `tribe_name_basis`,
and `bia_tribes_column_conflict` flags every affected row. Nothing is silently
repaired.

---

## 4. Index layer: compacts, versions, events

All 1,189 BIA index rows are consumed, none dropped.

Derivation rules (deterministic, each recorded in a `_basis` column):

- **R1** `is_amendment = 0` with decision in {Approve, Deemed Approved,
  Secretarial Procedures, blank} opens a **new base instrument** → one row in
  `compacts.csv` plus its version 1.
- **R2** every other non-disapproval row attaches as a **version** of the most
  recent preceding base instrument for the same state + tribe.
- **R3** `Disapproved` emits a **`compact_events.csv` row, never a deletion**.
- **R4** `approval_type`: Approve → `secretarial`; Deemed Approved →
  `deemed-approved`; Secretarial Procedures → `secretarial-procedures`;
  blank → `unknown`.
- **R7** `amendment_number` only from an explicit ordinal in the BIA title
  (Roman / ordinal word / "Nth"); blank otherwise. `version_seq` is the derived
  chronological position and is labeled as such.
- Tribes are grouped on state + the *set* of distinctive name tokens, so
  spelling variants do not split a history ("Mohegan Indian Tribe" /
  "Mohegan Tribe of Indians"; "Otoe-Missouria" / "Otoe-Missouria Tribe").
  Only two groups merge; "Pueblo of Santa Ana" and "Pueblo of Santa Clara"
  keep distinct keys.

### Schema note
The plan's columns are emitted **first and unchanged**, followed by explicitly
named provenance/derivation columns. Two deliberate departures, both to avoid
asserting something the sources do not say:

1. `approval_type` carries a fourth value, **`secretarial-procedures`** (22
   compacts). Procedures prescribed by the Secretary under 25 U.S.C.
   2710(d)(7)(B)(vii) are a distinct legal path; folding them into
   `secretarial` would misdescribe them and folding them into `unknown` would
   discard a fact the source states plainly.
2. `compact_events.csv` (also in the plan) is produced so that disapprovals stay
   **events rather than deletions**, as the plan's rule 5 requires.

---

## 5. Terms extraction: pilot, iteration, and what shipped

The plan and the task both require a pilot before any scaling. Four passes were
run on a stratified pilot and **every candidate was read and adjudicated by
hand** before scaling.

### Pilot design
30–34 documents spanning **16 states, four eras** (1990s / 2000s / 2010s /
2020s) and **all three approval types** (18 secretarial, 8 deemed-approved,
3 secretarial-procedures), including 5 amendments as well as original
instruments. Terms are extracted **page-wise from the PDFs**, so every candidate
carries its 1-based PDF page.

### v1 → v4: measured failure modes and fixes

| # | Failure mode found in the pilot | Fix |
|---|---|---|
| FM1 | Table-of-contents lines matched as provisions (dominated `dispute_provision`, `game_scope`) | dot-leader / page-number / TOC-page guard |
| FM2 | Theoretical **payout** percentages ("shall pay out a minimum of 80 percent of the amount wagered") read as revenue-share rates — the single largest v1 error | rate now requires a payment-to-state anchor and rejects payout/jackpot/withholding/odds windows |
| FM3 | "two and one-half percent (2-1/2%)" captured as `2` | parenthesised numeral preferred; `n-1/2` normalized |
| FM4 | Machine-cap regex caught **transfer limits** and **revenue-tier thresholds** ("so long as the Tribe operates no more than 750 Gaming Devices … its payments shall be based on the following schedule") | cap requires an authorisation anchor; transfer/payment windows rejected |
| FM5 | Quotes lifted from the Secretary's approval letter bundled at the front of the PDF were indistinguishable from compact text. **On Pueblo of Santa Ana 1997 the letter says the compact does *not* provide substantial exclusivity — v1 would have recorded exclusivity as present.** | every row carries `doc_zone` (`approval_letter` / `instrument_text`); exclusivity rejects negated windows |
| FM6 | `tier_structure` never fired | rewritten around "N % of the first/next $X" — **still zero recall, see gaps** |
| FM7 | Limits on **non-tribal** operators read as the tribe's cap (Tesuque 2015: "racinos may operate a maximum of 750 slot machines") | non-tribal / racino / cardroom windows rejected |
| FM8 | Recitals describing a **prior** instrument read as current terms (Chemehuevi 2021 procedures reciting the 1999 Compact's 2,000 devices) | `WHEREAS` / "<year> Compact" windows rejected |
| FM9 | Cap sentences whose subject was not the tribe | explicit tribe-as-operator requirement |
| FM10 | Derived / directional / installment percentages (Seminole "Monthly Payment shall be 8.333 % **of the estimated Revenue Share Payment**"; "reduced by 10 percent"; Fort Sill "payment **from the State** to eligible tribes of 50 %") | those constructions rejected |
| FM11 | v2's loosened duration verb swept in the Washington **three-year amendment moratorium** — Skokomish, Tulalip and Upper Skagit all returned a 3-year "term" | duration verb must attach to the Compact; `moratorium` rejected |
| FM12 | Rincon 2016: terminates 12/31/2037 but auto-extends to 6/30/2039 — v2 returned the extension | conditional-extension dates rejected |
| FM13 | "Eight Percent (8.00 %) of the Adjusted Net Win" missed on the closing paren (Otoe-Missouria 2020) | paren tolerated |
| FM14 | Standing Rock 2020: "a total of 1,000 slot machines **in a tribal establishment located in the SE¼ of Section 35**" scored statewide — a facility-specific cap about to be propagated tribewide, exactly what the plan forbids | single-site language forces `applies_to = facility`; genuinely ambiguous windows are left **UNSET rather than guessed** |

### Measured pilot accuracy

v1 (before fixes), hand-adjudicated: `machine_cap` 4/7 correct values and 2/4
correct `applies_to`; `revenue_share_rate` ≈ 13/24; `_term_years` 6/6;
`game_scope` and `dispute_provision` dominated by table-of-contents noise.
v2 regressed `_term_years` to 1/4 (the moratorium bug) and `machine_cap` to 1/3.

**v4 (shipped), all 63 pilot candidates read:**

| term_type | pilot candidates | correct | notes |
|---|---:|---|---|
| `machine_cap` | 1 | 1/1 | value and `applies_to` both correct |
| `revenue_share_rate` | 4 | 4/4 | |
| `revenue_share_base` | 19 | 14/14 sampled | correct as *defined term*; over-claims where an instrument defines "Net Win" but shares no revenue |
| `exclusivity` | 10 | 12/12 sampled pre-dedup | |
| `dispute_provision` | 8 | 8/8 | |
| `game_scope` | 6 | 6/6 | locates the authorised-games section; does **not** enumerate the games |
| `tier_structure` | 0 | — | **no recall** |
| `local_share` | 0 | — | **no recall** |
| *(duration, not a plan term_type)* | | | |
| `_term_years` | 3 | 3/3 | |
| `_term_end_date` | 1 | 1/1 | |
| `_renewal` | 11 | 11/11 | |

**Zero false positives across all 63 v4 pilot candidates.** Precision is high;
**recall is the honest weakness** and is not concealed — see §7.

Only after this adjudication were the extractors run across the corpus.

---

### Corpus-scale re-check (the pilot was not the last word)

Scaling to 1,078 documents produced 2,542 raw candidates, deduplicated to 1,885.
Two term types that **never fired in the 34-document pilot did fire at corpus
scale**, so they were sampled and adjudicated separately rather than shipped on
zero evidence:

- `tier_structure` — 21 rows, 10 sampled, **8/10 correct content** (the New Mexico
  Pueblo "3 % of the first $5 million" chart, the Arizona 2003 bracket schedule,
  Shingle Springs' $0–200 m / over-$200 m table). Its raw regex groups were
  unusable as a value, so `value` now holds the **located schedule text** and
  `unit = schedule_text_located`. **Brackets are not parsed.**
- `local_share` — 87 rows, 10 sampled, **9/10 correct** as a located provision
  (Skagit and Kitsap County Sheriff allocations, California Impact Mitigation
  Funds, Michigan's Local Revenue Sharing Board).

A 12-row random spot check per type also showed **`revenue_share_rate` degrading
outside the pilot** — 7/12 clearly correct, 2/12 wrong, 3/12 unverifiable from
the retained quote. Cause: the "pay … N percent" form allowed 140 characters
between the verb and the numeral, so it collected numbers from a neighbouring
clause (Little Traverse Bay 2010 returned 10 from a sentence stating 8 %;
Pokagon returned 2 from a heading about payments to *local* units of government).
`machine_cap` likewise re-admitted one recital of a prior compact whose
`WHEREAS` fell outside the match window (Cahuilla, 2,000 devices).

**Response:** every candidate is re-verified in `15e` against its own retained
quote with a strict pattern — the numeral must sit within 60 characters of a
payment verb **or** be immediately qualified by the revenue base — and rows that
cannot be re-derived from their quote are **dropped, not downgraded**. This
removed 23 `revenue_share_rate` rows and 6 `machine_cap` rows. A re-sample of 12
survivors: **10 clearly correct, 1 ambiguous, 1 wrong** (a Pokagon
local-government payment still typed as a state revenue share). `machine_cap`
values re-sampled at 11/12; its `applies_to` errs toward UNSET rather than
toward a wrong scope, which is the safe direction given the plan's rule that a
facility-specific term must never be propagated tribewide.

---

## 6. Outputs

`data/clean/` — all four files carry the plan's columns first, then named
provenance/derivation columns.

| File | Rows | Cols |
|---|---:|---:|
| `compacts.csv` | **707** | 25 |
| `compact_versions.csv` | **1,158** | 23 |
| `compact_terms.csv` | **1,311** | 14 |
| `compact_events.csv` | **31** | 12 |

All 1,189 BIA index rows are accounted for: 1,158 versions + 31 disapproval
events. Referential integrity is clean — 0 orphan foreign keys, 0 duplicate
`compact_id` or `version_id`, 0 dangling `successor_compact_id`,
`entity_id` blank on every row, `term_type` entirely within the plan enum,
`applies_to` only `statewide` / `facility` / blank, and **every term row carries
both a verbatim quote and a PDF page**.

**`compacts.csv`**

| | |
|---|---:|
| distinct tribes | 286 |
| distinct states | 28 |
| `approval_type = secretarial` | 518 |
| `approval_type = deemed-approved` | **165** |
| `approval_type = secretarial-procedures` | 22 |
| `approval_type = unknown` | 2 |
| `instrument_type = compact` | 684 |
| `original_effective_date` from FR notice URL | 574 |
| `original_effective_date` from BIA decision date | 133 |
| `term_end` populated | **174** (99 explicit instrument date, 68 computed from a stated term tied to the effective date, 7 from an explicit BIA extension title) |
| `renewal_provisions` populated (verbatim quote) | 170 |
| `status`: renegotiated / unknown / active / expired | 412 / 233 / 46 / 16 |
| rows where the BIA tribes column conflicted | 41 |

**`compact_versions.csv`**

| | |
|---|---:|
| `version_role = original-instrument` | 706 |
| `version_role = amendment` | 334 |
| `version_role = extension` | 118 |
| `has_text = 1` | 1,078 (93.1 %) |
| `amendment_number` from an explicit ordinal | 231 of 334 amendment rows |
| `FR_citation` populated | 1,007 |
| `what_changed`: original / unknown / term / amended-and-restated / scope | 706 / 302 / 118 / 22 / 10 |

**Amendments are versioned rows, never collapsed.** There is no stored "current
terms" anywhere in the outputs; it remains a computed view over
`compact_versions` × `compact_terms`.

**`compact_terms.csv`**

| term_type | rows |
|---|---:|
| `revenue_share_base` | 413 |
| `game_scope` | 235 |
| `exclusivity` | 208 |
| `revenue_share_rate` | 166 |
| `dispute_provision` | 118 |
| `local_share` | 87 |
| `machine_cap` | 63 |
| `tier_structure` | 21 |

Covering 618 of 1,158 versions and 500 of 707 compacts.
`doc_zone`: 1,132 instrument text / 179 approval letter.
`applies_to`: 136 statewide, 49 facility, **1,126 deliberately unset**.
Each row also carries `pilot_validated_type`, recording the measured accuracy of
its extractor so a downstream user can weight it.

**`compact_events.csv`** — 31 secretarial disapprovals, each with the BIA title,
date, FR notice and source PDF. Disapproved submissions produce **no** compact
and **no** version row; they are events attached to the tribe-state and, where
one exists, to the then-current compact.

---

## 7. What could not be extracted

1. **Tier brackets are located, not parsed.** Graduated schedules ("1 % of the
   first $25 million, 3 % of the next $50 million, 6 % of the next $25 million,
   8 % above $100 million" — the Arizona 2003 form) are laid out as tables and
   multi-clause lists. 21 of them are located with a page cite and the schedule
   text, but **no row decomposes a schedule into bracket boundaries and rates**,
   because a partial bracket would read as a flat rate. This is the single
   highest-value remaining curation target.
2. **`local_share` distinguishes poorly from state revenue sharing.** 87 rows are
   located at ~90 % precision, but one known confusion survives in the opposite
   direction: a Pokagon payment to local units of government is still typed
   `revenue_share_rate`. Tribe-to-tribe sharing (California's Revenue Sharing
   Trust Fund) and tribe-to-local sharing are not cleanly separated.
3. **Recall generally — the dataset's main limitation.** Precision was
   prioritized over coverage throughout. `compact_terms.csv` reaches only
   **618 of 1,158 versions (53 %) and 500 of 707 compacts (71 %)**, and within
   those, only 63 machine caps and 166 revenue-share rates across a corpus where
   far more exist. `term_end` is known for 174 of 707 compacts (25 %);
   `renewal_provisions` for 170. `status` is `unknown` for 233 compacts.
   **Terms absent from `compact_terms.csv` are unextracted, not absent from the
   compact** — no row should be read as evidence that a compact lacks a term.
4. **`game_scope` values are locations, not lists.** Rows point at the
   authorised-games section with a page cite; they do not enumerate the games.
5. **Text availability.** 1,078 of 1,158 versions (93.1 %) carry text classified
   as instrument text; 42 are stubs, 32 are letters or short documents, 1 has no
   local PDF, 1 extracts empty (`Oneida Nation Letter to Tribe, Fourth Compact
   Amendment, Deemed Approved.pdf`). 47 documents were flagged `needs_reocr` by
   the prior pass. Compacts BIA does not post (state gaming agency, governor and
   legislature sites) have **not** been swept.
6. **`term_end` is mostly blank, by design.** It is populated only from an
   explicit end date in the instrument, an explicit end date in a BIA extension
   title, or arithmetic on a stated term length that the text itself ties to the
   effective date. No term end is inferred from convention.
7. **`FR_citation` carries the FR document number and the notice URL, not a
   volume-and-page citation.** BIA publishes only the notice link; a "68 FR ####"
   citation would have to be invented.
8. **`entity_id` is blank throughout**, as instructed — spine linking is out of
   scope for this build.
9. **`state_payments.csv` is not produced.** No state tribal-contribution report
   has been acquired, so the plan's observation channel is not yet open.
10. **`compact_events.csv` covers secretarial disapprovals only.** Litigation
    events (the Seminole 2021 compact litigation is the obvious case) and
    renegotiation-window events are not yet sourced.
11. **`successor_compact_id` and `status = renegotiated`** rest on a stated rule
    — "a later base instrument for the same state + tribe appears in the BIA
    index" — not on a document saying one compact replaced another. The rule is
    written into `status_basis` on every row.
12. **Two BIA index rows point at Federal Register PDFs** rather than compact
    documents (`pdf_filename = "Federal Register Link"`), and one row has a blank
    decision (Pueblo of Sandia, 1995-03-22) which becomes
    `approval_type = unknown`.
