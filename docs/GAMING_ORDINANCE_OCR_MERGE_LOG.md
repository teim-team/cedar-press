# Ordinance OCR — merge and integration log

*Run 2026-08-26. Code: `code/153_merge_ordinance_ocr.py` (`merge` / `integrate`
/ `codebook`). Companion to `docs/GAMING_ORDINANCE_BUILD_LOG.md`, which this
supersedes on every count it restates.*

Numbers here are reproduced from `data/interim/153_run_summary.txt`, which the
script writes on every run. Re-run the script rather than editing a figure.

---

## 0. What was sitting unconsumed

The overnight OCR run completed **2026-08-13**: 263 of 263 OCR-able image-only
NIGC ordinance scans, 0 low-confidence, 0 all-blank documents. It left

    data/raw/external/nigc_ordinances/ocr/*.txt      263 verbatim OCR files
    data/interim/ocr_shards/ocr_shard_0..7.csv       233 metadata rows

and **nothing read either one for thirteen days.** `gaming_ordinances.csv` still
carried `text_layer_status = IMAGE_ONLY_SCAN_NO_TEXT_LAYER` and blank provisions
on all 264 of those rows — 23% of the archive, and the largest single ceiling
recorded in the build log (§8.5).

Writes: `data/clean/gaming_ordinance_ocr.csv`,
`data/clean/gaming_ordinances.csv`,
`data/clean/codebook/07f_gaming_ordinances.csv`,
`review/ordinance_compact_diff_2026-08-26.csv`,
`data/interim/153_run_summary.txt`.

Backups taken before any overwrite:
`gaming_ordinance_ocr.csv.bak_2026-08-26_pre153_merge`,
`gaming_ordinances.csv.bak_2026-08-26_pre153_ocr_merge`. Every output was
written `.part` then renamed. `code/62_no_regression_check.py` passed before and
after, no regressions. `09_import_rulings.py` and `01_build_entity_spine.py`
were not run. `118_build_gaming_ordinances.py` was **imported** for its
extractors and run only in `reconcile` mode, which writes to `review/` alone —
`parse` was never run, because it rebuilds `gaming_ordinances.csv` from the PDFs
and would have discarded this work. No network call was made.

---

## 1. 263 .txt against 233 shard rows is the INTERRUPTION shape, not a loss

`122_ocr_ordinance_scans.py` writes each `.txt` the moment a document finishes,
but writes its shard CSV **only at the end of the shard**. An earlier run of the
same shards was killed mid-flight — START_HERE records "27 of 263" before the
overnight attempt — so 28 documents have text on disk and no metadata row, and 2
more sit in the 300-dpi smoke-test output.

AGENTS.md records *"an interruption must not look like a completion."* The
mirror of that rule applies here: **an interruption must not look like a
deletion either.** The directory, not the CSV, is the ground truth for what was
OCR'd.

| source | rows |
|---|---:|
| `ocr_shard_0..7.csv` | 233 |
| prior `data/clean/gaming_ordinance_ocr.csv` (300 dpi smoke test) | 2 |
| **reconstructed from `.txt`, no shard row** | **28** |
| **merged** | **263** |

- **Duplicate `ordinance_id` across sources: 0.** The sharding is `i % n` over
  one ordered list, so it cannot overlap; the check is kept anyway rather than
  assumed.
- **Metadata rows with no `.txt`: 0. `ocr_chars` disagreeing with the file on
  disk: 0.** Every row was verified against its file.
- Every reconstructed row carries
  `ocr_metadata_basis = reconstructed_from_txt_no_shard_row`, and its
  `ocr_mean_confidence` is left **BLANK, never 0.0**. A per-line confidence that
  was never recorded is not a document that OCR'd badly, and a 0 there would
  have looked like 28 failures.

Quality of the 235 documents that do carry a measured confidence: mean
**0.8710**, min **0.7556**, **none below 0.70**, **no document with all pages
blank**, **no zero-length file**. 7,021 pages, 14,295,148 characters, spanning
**1993-10-12 to 2022-06-02** across **141 tribes** (225 amendments, 38 original
ordinances; 2000s 125 · 2010s 82 · 1990s 53 · 2020s 3).

---

## 2. Evidence grade is preserved, not laundered

| | before | after |
|---|---:|---:|
| `TEXT_LAYER_PRESENT` | 886 | 886 |
| **`OCR_RECOVERED`** | 0 | **263** |
| `IMAGE_ONLY_SCAN_NO_TEXT_LAYER` | 264 | **1** |
| `NO_DOCUMENT_LINKED_ON_INDEX` / `NOT_RETRIEVED` / blank | 5 | 5 |

- `text_layer_status` becomes `OCR_RECOVERED` and **never** `TEXT_LAYER_PRESENT`;
  the prior value is kept in the new `text_layer_status_prior`, which reads
  `IMAGE_ONLY_SCAN_NO_TEXT_LAYER` on all 263.
- `confidence` becomes `document_ocr_recovered` — a fourth basis, so the file
  now reads `document_parsed` 886 · `document_ocr_recovered` 263 ·
  `index_only` 4 · `document_served_belongs_to_another_tribe` 1 ·
  `document_no_text_layer` 1.
- `provisions_basis = OCR_RECOVERED_TEXT` names the text every provision on the
  row was read from.
- **`pdf_chars` was not overwritten.** It stays at the near-zero PDF text layer
  that made the row a scan; the OCR length is the new `ocr_chars`. The two facts
  must not be blurred.
- New columns: `text_layer_status_prior`, `provisions_basis`,
  `document_names_tribe_basis`, `ocr_txt_path`, `ocr_chars`, `ocr_pages`,
  `ocr_pages_blank`, `ocr_mean_confidence`, `ocr_engine`, `ocr_dpi`, `ocr_date`,
  `ocr_metadata_basis`.

**The 264th image-only row stays refused.** Kialegee Tribal Town's amendment
link serves a file byte-identical to Kalispel's; it was never OCR'd and the
script asserts that no row carrying `md5_duplicate_of` or
`confidence = document_served_belongs_to_another_tribe` gains content.

Extractors were **imported** from `118_build_gaming_ordinances.py`, never
re-implemented (standing rule 8). The one resolver was not re-run: entity keying
is a property of the NIGC index tribe **name**, which OCR does not change.

---

## 3. What the ordinance layer gained

| field | rows before | rows after | tribes before | tribes after |
|---|---:|---:|---:|---:|
| `classes_authorized` populated | 653 | **827** | 286 | **310** |
| `class_ii_authorized = 1` | 530 | **670** | 266 | **293** |
| `class_iii_authorized = 1` | 502 | **644** | 249 | **275** |
| `tribal_gaming_agency_named` | 741 | **973** | 284 | **307** |
| `revenue_allocation_plan_referenced = REFERENCED` | 343 | **445** | 196 | **220** |
| any per-capita finding | 466 | **586** | 237 | **260** |
| `PER_CAPITA_PLAN_ASSERTED` | 19 | **31** | **15** | **22** |
| `PER_CAPITA_PROHIBITED` | 33 | **38** | 20 | **22** |
| `licensing_provisions` | 728 | **932** | 296 | **317** |
| `minimum_internal_control_reference` | 254 | **355** | 149 | **177** |
| `chair_or_designee` | 395 | **596** | 185 | **253** |
| `document_approval_date` | 334 | **542** | 186 | **241** |
| `effective_date` | 26 | **34** | 19 | **23** |
| `supersedes_quote` | 146 | **202** | 93 | **116** |

`classes_basis` no longer has a 269-row hole: `authorisation_section_heading`
392 → **508**, `authorising_verb_window` 134 → **168**,
`no_authorising_language_found` 233 → 322 (the amendment approval letters that
genuinely contain no ordinance text).

### 3.1 The headline the build log could not close

**Tribes with an ordinance and no compact — the class II universe — is still 40.**
OCR does not add tribes; NIGC's index did not change. What changed is how many
of them we can say anything about:

| | 2026-08-12 | now |
|---|---:|---:|
| of the 40, class II authorised **in the text of an instrument** | 29 | **34** |
| keyed ordinance tribes with **no class determinable from any instrument** | **32** | **10** |

Newly readable in that 40: Kashia, Lytton, Round Valley, Santee Sioux, Scotts
Valley, and Wampanoag/Ysleta del Sur confirmed. The ten still unreadable are
Absentee-Shawnee, Crow Creek, Metlakatla, Pueblo of Jemez, Red Lake,
Reno-Sparks, Shakopee, Shinnecock, Tlingit & Haida and Tohono O'odham — every
one of them a tribe whose instruments are all amendment approval letters
carrying no ordinance text. That is a property of what NIGC posts, not an OCR
backlog, and it is now the honest floor.

### 3.2 Seven new tribes on the strongest per-capita lead

The build log's real lead was the small set of tribes whose ordinance states in
the indicative that per capita payments **have been elected or a plan approved**,
as against the 160 tribes reciting the conditional statutory clause. That set
grows **15 → 22**:

Coquille Tribe of Oregon · Forest County Potawatomi Community · Otoe-Missouria
Tribe of Indians · Quileute Tribe of the Quileute Reservation · Round Valley
Indian Tribes · Sac & Fox Nation of Oklahoma · Tulalip Tribes of the Tulalip
Reservation.

Two tribes join the **prohibits per capita outright** set (20 → 22): Santee
Sioux Nation and Seneca-Cayuga Tribe of Oklahoma.

### 3.3 The tribal gaming agency register

741 → **973 rows**, 284 → **307 tribes**, tribe-specific names 535 → **715
rows**, distinct strings 397 → 469. **66 tribe-specific bodies appear that the
born-digital corpus never named** — Osage Nation Gaming Commission, Navajo
Nation Gaming Regulatory Office, Miccosukee Gaming Agency, Nisqually Tribal
Gaming Commission, Mashpee Wampanoag Tribal Gaming Commission, Coquille Tribal
Gaming Commission, Isleta Gaming Commission, Nambe Gaming Commission,
Otoe-Missouria Tribal Gaming Commission, Bad River Tribal Gaming Commission,
Crow Gaming Commission, Quechan Tribal Gaming Commission, Southern Ute Indian
Tribal Gaming Commission and others.

### 3.4 Three supersession chains upgraded

`supersedes_basis = stated_in_document_date_matched` rises **2 → 5**. On three
more instruments the approval letter now names the superseded ordinance and its
date, and that date matches another instrument of the same tribe on the index.
The chronological chain is otherwise untouched — it is index-derived and OCR
says nothing about it.

---

## 4. Four guards earned on this corpus

### (a) A date read off an OCR'd letterhead never accuses the index

The build log §4 records **117 false date disagreements** on the born-digital
pass, caused by NIGC's letterhead date being a scanned stamp (`NOV 1 5 1993`,
`APR 13 2C05`). This corpus is *entirely* such letters. So where an OCR date
disagrees with NIGC's index, this writes **`DISAGREE_UNVERIFIED_OCR_DATE`**,
never the born-digital `DISAGREE_DOCUMENT_IS_ANOTHER_INSTRUMENT`. The weaker
text gets the weaker claim.

On the 263 recovered rows: `AGREE` **197** · `LETTER_DATE_NOT_FOUND` 55 ·
`DISAGREE_UNVERIFIED_OCR_DATE` **8** · `AGREE_WITHIN_45_DAYS` 3.

**197 independent confirmations of NIGC's own index date** is the more valuable
half of that result. The eight disagreements are Muckleshoot 1996-06-21/1994-03-21,
Nez Perce 1996-08-23/1995-01-09, Omaha 1997-04-07/1995-08-25, Pascua Yaqui
1994-06-13/1994-04-28, Sac & Fox of Mississippi in Iowa 2008-12-08/2008-10-08,
Shoalwater Bay 2001-12-03/2001-10-09, Torres Martinez 2008-09-22/2008-07-25 and
Yankton Sioux 2008-03-24/2007-10-31. Every one reads like a letter quoting the
tribe's earlier submission; none is strong enough to call an index defect.

### (b) A STATE-LED BODY IS A STATE AGENCY

**`Arizona Gaming Commission`, `Arizona Department of Gaming and the Tribal
Gaming Office` and `Iowa Racing and Gaming Commission` were written into
`tribal_gaming_agency_named`** on the first integration pass. That inverts the
exact fact the column exists to record — the same failure as the NIGC lookalike
(*"NeHonel Indian Gaming Commission"*), in a new form. 118's `AGENCY_REJECT`
catches `state gaming` and `state of ` but not a **state's name**.

Refused unless the tribe's own name **starts** with that state token, because a
leading state token is usually the tribe's own name — `Delaware Nation`,
`Iowa Tribe of Kansas and Nebraska`, the trap `states_from_name` already
records. The refused string is kept in `tribal_gaming_agency_basis` as
`refused_state_named_body:<string>`, so the receipt survives the refusal. This
also refuses the truncation `Texas Gaming Regulatory Authority` the build log
names.

### (c) OCR loses word boundaries, and the tribe-naming test is spaced

`document_names_tribe` is the column that separates a mislinked file from a
correct one. On OCR text it produced a **false 0** — RapidOCR collapses the
spaces in a letterhead block, so Wyandotte Nation's 2007 approval letter reads
`LeafordBearskin, Chief / WyandotteNation` and the spaced token test fails on a
document that names the tribe four times.

Two fixes, both narrow:

1. A failed spaced test falls back to the **space-stripped** text, requiring a
   token of **6+ characters** — substring matching on a short token is the
   containment defect in miniature (`elim` sits inside `eliminate`).
2. **A state name is not a distinctive token either.** `wyandotte` is itself in
   `NAME_TRAPS` (Wyandotte County, Kansas), so `Wyandotte Nation, Oklahoma`
   reduces to `{oklahoma}` — and the letter does not contain the word Oklahoma.
   With nothing distinctive left the answer is **blank, "not testable", never
   0**. The reconcile step already excludes state names from its candidate test
   for exactly this reason.

Result on the 263 rows: `1` **239** (all `spaced_token_match`), blank 24
(`only_trap_or_state_tokens_in_name`), **`0`: none**. Before fix (2): 257 ones,
of which 18 rested on nothing but a state name appearing in a letter.

**This defect is also live in the base build**, which this run did not change:
one born-digital row — Shawnee Tribe of Oklahoma — carries a
`document_names_tribe = 0` that rests only on a state token. It is a lead for a
`118` fix, not a fact about that document.

### (d) The integration is idempotent

Re-running `integrate` on an already-integrated file must not overwrite
`text_layer_status_prior` with `OCR_RECOVERED` and erase the fact that the row
was a scan. It is guarded, and the run above was executed three times from the
restored backup while the guards in (b) and (c) were added.

---

## 5. What is still wrong, stated plainly

1. **`chair_or_designee` is not normalised, and OCR multiplies the same
   person.** Distinct strings rise 69 → 111, but `Harold A. Monteau`,
   `Hafold A. Monteau`, `Haroxd A. Monteau` and `HaroldVA. Monteau` are one NIGC
   chairman; likewise `George T. Skibine` / `Gedrge Skibine` and
   `Jonodev O. Chaudhuri` / `Jbnodev O. Chaudhuri`. **A distinct count over this
   column is not a count of people.** The codebook now says so. Normalising it
   needs a person matcher, which is not `resolve_entity`'s job and was not
   built here.
2. **The agency register still carries glued contact-block text.**
   `E-mail Commissioner Paul Tate Delaware Nation Gaming Commission`,
   `Facsimile Anthony Montague Chairman Quechan Tribal Gaming Commission`,
   `Creation of Tribal Gaming Commission`, and `Maric` / `Marie Tribal Gaming
   Authority` (both Sault Ste. Marie). The body is right; the string has a
   person or a heading welded to it. **The register is a lead list, not a
   normalised roster**, and the distinct-name count is inflated by these.
3. **Ten keyed tribes still have no class determinable** (§3.1). Not an OCR
   backlog — their instruments are approval letters with no ordinance text.
4. **28 documents have no recorded OCR confidence** and never will; their shard
   died before writing it. Re-OCR would recover it and is not worth 28 documents
   of CPU.
5. **`ocr_dpi` is blank on those same 28.** The killed run did not record
   whether it rendered at 220 or 300.
6. **Nothing here changes what an ordinance can prove.** Every recovered row
   still carries `authorisation_measurement_type =
   LEGAL_AUTHORISATION_NOT_A_COUNT`, still says nothing about which class is
   operated or whether anything operates at all, and 160 tribes' per-capita
   language remains the conditional statutory recitation. §8 of the build log
   stands unchanged except for item 5, which this run closes.
7. **Every row is still `tier = B`.** These are algorithmic extractions with
   receipts, run over a *lower-grade text*, and nothing here publishes without a
   review pass.

---

## 6. Reproduce

    py -3 code/153_merge_ordinance_ocr.py merge       # 8 shards + dir -> one table
    py -3 code/153_merge_ordinance_ocr.py integrate   # -> gaming_ordinances.csv
    py -3 code/153_merge_ordinance_ocr.py codebook    # fragment only
    py -3 code/118_build_gaming_ordinances.py reconcile   # review/ only
    py -3 code/62_no_regression_check.py

Never `py -3 code/118_build_gaming_ordinances.py parse` — it rebuilds
`gaming_ordinances.csv` from the PDFs and discards everything above.
