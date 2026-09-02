# C8 - the documented rebuild path, and why it stopped destroying things

*Workstream C8, 2026-09-01. Written by hand; the numbers come from
`code/812_c8_rebuild_proof.py`, which regenerates
`docs/schema/c8_rebuild_proof.json`. **No builder was run outside `--dry-run`
to produce anything here.***

C8 is *"ONE documented rebuild path reproduces the tables without destroying
later enrichment."* It was the last blocker on `_entity_layer` and on `deals`.
Both are now `READY` in `518_dataset_readiness.py`.

---

## 1. The defect was the write, not the computation

Three scripts sat in `cedar_pipeline.NEVER_RUN` for the same reason, and it
was never that what they computed was wrong. It was that each opened its
output in `"w"` mode and wrote only its own rows and its own hardcoded column
list, so everything that had reached the table from anywhere else - fifteen
spine enrichers, `126`'s entity attribution, `505`'s uids, an owner's
adjudications - was gone.

Measured 2026-09-01 by diffing what each script writes against the live table.
**Neither the measurement nor the proof ran any of them for real.**

| script | rebuild produced | live table | what a rerun destroyed |
|---|---|---|---|
| `01_build_entity_spine.py` | 687 rows, 12 cols | **1,555 rows, 44 cols** | 868 entities (210 NHOs, 185 BIE schools, 173 ANC village corps, 64 Native CDFIs...) and 32 columns including `cedar_uid` |
| `09_import_rulings.py` | 19,232 rows, 17 cols | **20,577 rows, 22 cols** | 1,345 rows - **18 of them tier-A owner adjudications** - and 5 columns |
| `88_build_deals_taxonomy.py` | 935 rows, 43 cols | **935 rows, 52 cols** | 9 columns: 7 `native_party_*` from `126`, `cedar_uid` from `505`, and `Event_Quarter` |

`09`'s was the sharpest: it **READ** `cedar_identifier_ledger_tiered.csv` and
**WROTE** `cedar_identifier_ledger_final.csv`. Those are not the same table.
`_final` is `_tiered` plus 1,345 rows later scripts appended, and every one of
`_tiered`'s 19,232 (key, occurrence) pairs is already in `_final` with none
missing - so the write was a pure deletion of the difference. Owner
adjudications are the one class of fact in this project that cannot be
re-derived from a source.

`88`'s `Event_Quarter` loss had not been noticed by anyone. Its header came
from `list(out[0].keys())` - the keys of the **first row**. `Event_Quarter` is
absent from `deals_2026_ytd.csv` and present in the additions files, so it
vanished from all 935 rows silently. *A header taken from one row is not a
schema.*

---

## 2. The fix: one merge, shared

`cedar_pipeline.merge_table` now backs all three writes. Its contract:

1. **No row is ever lost.** Live rows survive in their original order; a
   rebuilt row with an unseen key is appended after them.
2. **No column is ever lost.** Live column order is preserved, new columns
   append on the right, and the function *raises* rather than drop one.
3. **A builder may not silently overwrite.** On an existing row it fills
   **blank cells only**. Where the live cell is non-blank and differs, the
   **live value stands** and the pair is recorded as drift. `refresh` names
   the columns a builder genuinely owns - and naming a column there is a claim
   that nothing else writes it, which was checked by grep, not assumed.
4. **Drift is reported, never discarded**, to
   `review/{spine,ledger,deals}_merge_drift_<date>.csv`.

Non-unique keys are handled by occurrence ordinal (`cedar_pipeline.ordinal_key`):
3 rows of `cedar_identifier_ledger.csv` share the 4-column key and 86
`(identifier_type, identifier)` pairs recur in `_final`. Collapsing them would
be a row loss called deduplication - the same repair HUB applied to the ruling
map.

A fourth loss turned up while wiring this and is worth recording, because
it is the same defect at the smallest scale in the repo:
`data/raw/external/_SOURCE_MANIFEST.csv` carries 11 rows and `01`'s `INPUTS`
list declares 7, so the old replacing write would have deleted the provenance
of four staged inputs. It merges now too, keyed on `local_file`.

Every builder also gained `--dry-run`: the full computation, the full merge,
**no write**.

---

## 3. The proof, against HUB's census

`py -3 code/812_c8_rebuild_proof.py` - dry runs all three against the live
tables and checks them against `docs/schema/hub_rebuild_census.json`.

```
cedar_entity_spine.csv        1,555 -> 1,555 rows (0 lost)   44 -> 44 cols (lost none)
cedar_identifier_ledger.csv  19,232 -> 19,232 rows (0 lost)  14 -> 14 cols (lost none)
cedar_identifier_ledger_final 20,577 -> 20,577 rows (0 lost) 22 -> 22 cols (lost none)
deals_classified.csv            935 -> 935 rows (0 lost)     52 -> 52 cols (lost none)

CENSUS GATE  >= 1,555 rows and all 44 columns
  rows after merge    : 1,555   PASS
  census columns held : 44/44   PASS
```

**512 spine cells** where the rebuild disagrees with the live value were held
back rather than applied. They are worth naming, because they are the reason
fill-blanks-only is right and not merely cautious:

- **510 `aliases`** - a separator difference (`A|B` vs `A | B`) plus aliases
  `51_add_anc_acronym_aliases.py` added. Overwriting would revert 51.
- **1 `entity_class`** - the source calls Tlingit & Haida a *Federally
  recognized Alaska Native Village*; `71_fix_known_defects.py` corrected it to
  *Federally recognized tribe*. Overwriting would reinstate the defect.
- **1 `canonical_name`** - `canonical_tribe_table.csv` carries the typo
  *"Warms Springs Tribe"*. The live spine has *"Warm Springs Tribe"*.

A replace-mode rebuild applied all 512 without telling anyone.

---

## 4. A second defect the dry run found, and the fix

`09`'s first clean dry run demoted **12 rows that were already tier-A owner
adjudications** and reported **28 non-existent "spine gaps"**. Cause: the
inbox carries two review-page dialects. One names an owner
("Chenega Corporation"); the other returns a verdict from a fixed vocabulary
(`NATIVE`, `NOT_NATIVE`, `OWNER_NAMED`, `INDIVIDUAL_NATIVE`). `09` had grammar
for the first only, so a verdict was handed to the spine resolver as a company
name, failed to match, and took the *owner-not-in-spine* branch - which sets
tier X.

This is the identical defect `09`'s own `NOT_NATIVE_RE` comment describes one
dialect earlier (*"42 of them were the single phrase 'Named for a place -
demote'"*). Three changes, all in `09`:

- **verdict tokens are parsed as verdicts.** An ALL-CAPS underscored token is
  never a legal business name. `NATIVE` upholds; a token this script cannot
  act on is **held and named** to `review/ruling_verdicts_unparsed_<date>.csv`,
  never converted into a demotion.
- **`reinstate` / `restore` reinstates.** *"Tribally controlled /
  Native-controlled - reinstate"* was read as the name of a company and
  demoted the row it was meant to restore. A ruling that says reinstate must
  not end in exclusion.
- **An unresolvable string cannot demote an existing tier-A adjudication.**
  That branch is right for an unreviewed algorithmic claim. On a row already
  adjudicated by the owner, the only thing a parse failure proves is that this
  script could not read the string.

Result: 28 fake spine gaps -> **3 real ones**; 12 demotions -> **2**, and both
of those are genuine. `CAGE 9DVK5` (San Juan Services LLC) and `CAGE 9H8M8`
(Four Corner Pest Control LLC) sit at tier A with rationale *"INDIVIDUALLY
NATIVE-OWNED"* while the inbox ruling on them reads *"Not a Native entity -
individually Native-owned firm"*. That is a real disagreement between the
ruling text and `241_promote_individual_native_firms_in_place.py` about
whether an individually Native-owned firm is in scope as an *entity*. It is
**named in the log every run and nothing is dropped**; it is an adjudication
question, not a rebuild defect, and it is not this workstream's to settle.

---

## 5. The rebuild path

```
# 1. prove it is still safe (dry run, writes nothing)
py -3 code/812_c8_rebuild_proof.py

# 2. the hub
py -3 code/build.py plan _entity_layer        # 01 then the 15 enrichers
py -3 code/build.py run _entity_layer --execute

# 3. deals
py -3 code/build.py run deals --execute

# 4. gates
py -3 code/62_no_regression_check.py
py -3 code/518_dataset_readiness.py
```

The dependency-correct enricher order lives in
`cedar_pipeline.REPLAY_ORDERS["cedar_entity_spine.csv"]`, read by HUB off the
`cedar_entity_spine.csv.bak_<date>_pre<NN>` trail in mtime order. `426` mints
spine entities and must be checked against the append-only register before any
replay; `503` re-uses uids keyed on the handle (`handle == tribe_id` on all
1,555 rows) and is safe to replay.

**`41_build_codebooks.py` is still in `NEVER_RUN` and stays there.** It was
never fixed; it still deletes 21 of 43 codebook blocks. C8 was closed by
fixing three scripts, not by emptying the dict - `RETIRED_FROM_NEVER_RUN` in
`cedar_pipeline.py` records, per script, what it used to destroy, what
changed, and which proof run cleared it.

---

## 6. What is NOT proven, stated rather than papered over

`docs/schema/hub_rebuild_census.json` lists **two spine enrichers with no
checkpoint**: `08_build_review_page.py` and `115_pull_assistance_archive.py`.
Every other enricher takes a `.bak` before it writes, which is the only reason
the genealogy could be read off the trail at all. These two leave no trace, so
they contribute no stage to the census and no live column is attributed to
them.

The honest split:

- **Non-destruction - PROVEN, and they do not weaken it.** The merge is
  additive and diffs against the **live** table, whatever put a row or column
  there. If either script ever wrote to the spine, a rebuild through `01`
  preserves it.
- **Replay-from-nothing - UNEVIDENCED for 2 of 17 stages.** Nothing in the
  evidence can say whether `REPLAY_ORDERS` omitting them is correct or a hole.
  C8 asks for the first; **the second should not be claimed.** Closing it
  means making those two checkpoint like the other fifteen, and then
  re-reading the trail.

Two known stale copies of the guard list exist outside `cedar_pipeline.py` and
will now over-report: hardcoded `NEVER_RUN` sets in
`code/293_lint_bug_classes.py:166` and `code/326_triage_class7_key_risk.py:80`,
plus a hardcoded sentence about `88` in
`code/24_generate_dataset_docs.py:197`. They belong to other workstreams and
were left alone. A second list kept in sync by hand is the disease
`cedar_pipeline`'s own docstring names; all three should read `CP.NEVER_RUN`.

---

## 7. `62_no_regression_check.py` after this work - none of it is C8's

`62` was run with no `--baseline`, so the floor is untouched. **This
workstream wrote no data file at all** - every builder run was `--dry-run`,
and the mtimes on `cedar_entity_spine.csv`, `cedar_identifier_ledger.csv`,
`cedar_identifier_ledger_final.csv`, `deals_classified.csv` and
`deals_taxonomy.csv` are all older than this session. So every regression `62`
reports predates it. Named rather than stepped around, per standing rule 15:

- `rulings_unapplied ROSE 1,215 -> 2,894` - GRAIN-HUB's, already measured and
  attributed in `docs/HUB_GRAIN_AND_REBUILD.md` §3 (28 subjects HUB's, 119
  from other workstreams' files that `173` swept).
- `files_with_columns_lost_vs_backup = 1` - `entity_evidence_profile.csv`,
  already named today by WS4 and WS5. **The root cause is worth adding: two
  scripts write this table with different schemas.**
  `151_rebuild_entity_evidence_profile.py` writes 10 columns including
  `in_spine`, `rows_per_source` and `amounts_per_source_NEVER_SUM`;
  `110_build_harmonized_views.py` writes 9, replacing them with
  `total_amount_usd` and `evidence_summary`. The live file is 110's. A column
  explicitly named `..._NEVER_SUM` being replaced by a single summed total is
  a C7 money-safety inversion, not only a column loss. It is a class6
  rebuild/rebuild collision and belongs in `KNOWN_ORDERINGS`; it is not C8's
  to fix.
- `contract_orphan_shippable`, `contract_violations`,
  `lint_new_defect_instances`, the three `25_build_publication_layer.TABLES`
  counters and `SHIPPING LOST: advocacy_passthrough_2026-08-07.csv` - all from
  other workstreams' writes to `data/clean` today.

Moving the other way in the same run: `lint_bug_class_instances` 146 -> 142
and `lint_class6` 29 -> 25.
