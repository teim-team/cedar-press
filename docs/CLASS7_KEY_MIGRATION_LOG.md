# CLASS 7 — POSITIONAL / NON-DETERMINISTIC PRIMARY KEYS

*Triaged, migrated and blocked 2026-08-26. Scripts 326–328.*

**Read this before touching any `*_id` column.** It is the working record for
the largest defect class the linter finds, and it names both what was fixed and
what was deliberately left alone and why.

---

## THE RULE, STATED ONCE

> A primary key is either a **NATURAL key stated by the source**, or a
> **deterministic digest of stated columns**. Never a position. Never `hash()`.

The digest is `cedar_keys.surrogate_id(prefix, row, columns)` — blake2b over
NFKC-normalised, case-folded, whitespace-collapsed parts joined by ASCII `0x1F`.
Same answer in every process, every build, every machine. `hash()` does not have
that property: **Python randomises string hashing per process**, which is the
whole of the `ferc_filing_id` defect.

**Every migrated key names its composing columns in a `*_KEY_COLUMNS` constant
at the top of its producing script, with a comment saying why those columns.**
`328_audit_id_service_bypass.py` checks that constant against
`327_migrate_class7_keys_to_digests.py`'s spec on every run, so the producer and
the migrated data cannot drift apart. That check is the reason a rebuild
reproduces the ids rather than silently re-keying the table.

---

## WHY TRIAGE BY RISK AND NOT BY COUNT

`293_lint_bug_classes.py` reported **76** class-7 findings. Three had caused
measured damage; a dozen were `id(obj)` used as a within-process dict key, which
is not a primary key at all. Sorting by count would have spent the session on
the harmless ones.

`326_triage_class7_key_risk.py` ranks them on **evidence**, not on the finding
text — for each one it asks three questions and answers them by measurement:

| test | how it is answered |
|---|---|
| **(a) is it written into a table?** | a value scan: does any column of any `data/clean` or `data/spine` table actually carry the literal prefix this line mints? Not "the producing script declares it writes a table" — a declared-writes join misses the 157-stages / 158-merges case, which 284 already recorded. |
| **(b) does anything join on it?** | the prefix appearing under a **differently named** column is a foreign key; so is the same column name in a second table. Plus: which other scripts name the column. |
| **(c) is the producer re-runnable against changing input?** | a fixed local corpus and a live table another agent rewrites are not the same risk. |

**One band exists because a measurement was impossible, and it is not "low".**
An f-string that begins with a formatted value — `f"{did}-E{n:02d}"`,
`f"{oid}-{i:05d}"` — has no literal prefix, so there is nothing to search the
data for. Those are reported as **UNTRACEABLE / `NO_LITERAL_PREFIX_TO_TRACE`**
and they need a human to read the producing line. Printing them as LOW would be
the 102 defect wearing a new costume: an absent measurement rendered as a zero.

**Bands, measured before the migration:** 12 HIGH · 25 MEDIUM · 39 LOW over 76
findings. **After it:** 9 HIGH · 15 MEDIUM · 5 UNTRACEABLE · 28 LOW over 57
findings that 284 still reports, and `293`'s unwaived `class7` count fell
**74 -> 42**.

Two of the five UNTRACEABLE were read by hand and are benign — `143:376` is the
form boundary waived below, and `227:1038` is within-run duplicate detection.
**Three genuinely need a human to read the producing line:**
`140_build_grantmaker_funding_flows.py:1317` (`flow_id`),
`23b_build_gaming_land_decisions.py:380` (`event_id`) and
`83_build_resource_ledger.py:524` (`source_record_id`).

Full machine-readable triage: `docs/CLASS7_KEY_TRIAGE.json`.

---

## WHAT WAS MIGRATED

`327_migrate_class7_keys_to_digests.py` — dry run by default, `--apply` to
write. Backups tagged with the **script name**
(`.bak_<date>_pre_327_migrate_class7_keys`), `.part`-then-rename, and **every
written file is verified by RE-READING it**: header unchanged, row count
unchanged, zero old values remaining.

| key | producer | was | now keyed on |
|---|---|---|---|
| `ferc_filing_id` | `133:1832` | `abs(hash(filer_org)) % 10000` | docket_number, subdocket, accession_number, filer_organization_as_recorded, document_description_verbatim |
| `earmark_id` | `99:1626/1661/1887` | positional ×2 **and `abs(hash(p.stem))`** | fiscal_year, chamber, requesting_member, recipient_name, project_title, amount_enacted, source_url, source_quote |
| `anc_id` | `07:163` | `ANC-{i:04d}` after a name sort | corporation_name, anc_class |
| `allocation_id` | `104:629` | counter across all tribes | tribe_name, effective_start, measurement_type |
| `band_id` | `106:308` | `{fy}-{i+1}` | fiscal_year, band_ordinal, band_label |
| `fact_id` | `117:576+623` | minted, then **re-numbered after a sort** | manufacturer, fact_type, device_class, geography, period_end |
| `party_id` (S106) | `130:830` | `len(parties)` — position in the **whole run** | document_number, party_name_as_published, party_role |
| `consultation_event_id` | `130:974` | index into a sorted dict of matched tribes | document_number, participant_name_as_published, participant_role |
| `event_id` (compacts) | `15b:262` | `…-{len(events)+1:04d}` | compact_id, event_date, event_type |
| `event_id` (NHO ownership) | `61:496` | position in a `\|`-split subsidiary string | effective_month, acquirer_entity, target_entity, direction |
| `observation_id` (admin) | `85:743` | the call order of `add_obs()` | region_system_code, administrative_region_id, observation_name, observation_year |

The complete old → new map is `docs/schema/class7_key_migration_map.json`, so an
id quoted in an older document can still be resolved.

### THE MIGRATION IS THE HARD PART, AND IT IS ENFORCED

Changing an id in a table other tables reference breaks those references
**silently** — no error, no missing file, just a join that returns nothing. So
327 refuses to migrate until it has *proved* where every reference lives:

1. a **FULL scan** — every `data/clean/**/*.csv` and `data/spine/*.csv`, cell by
   cell, including inside `,`/`;`/`|`-separated lists;
2. every found location the spec **declares** is migrated in the same pass;
3. **one found location the spec does not declare aborts the whole spec**, which
   is then reported as BLOCKED-ON-CONSUMERS with the location named.

A half-migrated key is worse than a bad key — the bad key at least fails
uniformly. That is why an undeclared consumer is a hard stop and not a warning.

The scan is also what produced the useful negatives: it proved that
`ferc_filing_id` appears in **exactly one place** (its own column), confirming by
measurement what `START_HERE.md` had only asserted, and that `earmark_id` is
referenced by nothing at all.

### `ferc_filing_id` — STATED, NOT PAPERED OVER

The new key is **not unique**. **769 groups covering 1,758 rows collide — 989
excess rows.** Every one of them is identical to its twin on *every other column
of the table* up to case and whitespace: the same eLibrary document recorded
twice. The old process hash was **masking** that duplication behind 855
collisions of its own.

So the column is now a stable **content identity**, and
`ferc_docket_filings.csv` stays what `284_audit_nondeterministic_keys.py`
already calls it — **BLOCKED for a primary key** until the duplicates are
resolved. Do not make it a foreign-key target.

Because the old column was itself ambiguous, 327 handles this one in
**RECOMPUTE** mode: the id is rebuilt row by row from that row's own stated
columns rather than substituted through an `old → new` map. Recompute mode is
only legal when the full scan proves the old values appear nowhere else.

---

## BLOCKED — recorded with the consumer list, deliberately not touched

| key | producer | why |
|---|---|---|
| `verification_id` (`INV-`) | `170:482` | **LIVE AGENT.** One of the three measured-damage instances, and the one that must not be fixed right now. `individual_native_firm_register.csv` was written at 19:22 today, `170`/`171` at 18:00–18:01, `241`–`244` at 18:58. Editing it races its author. The fix is already specified in `cedar_keys.PRIVACY_SURROGATE` — `surrogate_id('INF', row, ['awardee_uei'])`, because SAM resolves a UEI to a person's name and address for a firm whose legal name **is** a person's name. Measured here: `awardee_uei` is unique and non-blank over all 335 rows, so it is ready to mint. Three columns to migrate, one of them the self-FK `web_pass_verification_id`. |
| `exclusion_id` (`EXCL-`) | `02:116` | Four tables including **both identifier ledgers**, and `09_import_rulings.py` — a consumer — is on the NEVER-RUN list. `data/spine/cedar_rulings.csv.supersedes` holds `EXCL-0116`, a value **a person wrote down**. |
| `nho_id` (`NHO-DOI-`) | `05:90` | One ruling row away from safe. The roster migrates cleanly — `(organization_name, list_type, doi_list_page)` is unique over all 190 rows — but `cedar_rulings.csv.identifier` cites `NHO-DOI-0132` in a hand-authored `DO_NOT_CONFLATE` ruling. **WHAT HAS TO HAPPEN:** decide whether a migration may rewrite a human ruling, or give `cedar_rulings.csv` an `identifier_as_ruled` column that preserves what the person actually wrote. |
| `cedar_opinion_id` | `90:209` | Four columns in three tables, one **multi-valued** (`lineage_related_opinion_ids`) and one **differently named** (`gaming_source_claims.source_record_id`). `119` is a consumer and is NEVER-RUN. |
| `resource_revenue_event_id` / `resource_asset_id` | `83:441/515/524/2574` | Seven consuming scripts; `41_build_codebooks.py` is NEVER-RUN and `227_anomaly_sweep.py` was **running** during this session. `resource_asset_id` also mints under the bare literal `CEDAR-`, which collides with every other `CEDAR-*` id for the purposes of a value scan, so the reference set cannot be enumerated by prefix at all. |
| `ordinance_id` | `118:295` | A **self-FK** (`superseded_by_ordinance_id`, 834 rows) plus two other tables plus an OCR merge stage that joins back on the id. Partly natural already (built from the NIGC index date), so the win is small against the blast radius. |
| `review_id` (`RV-`) | `01:269` | `01_build_entity_spine.py` is **NEVER-RUN** — a rebuild drops every appended entity. The id is LOW risk anyway (a review-queue row number that reaches no table), so editing 01 would buy nothing and put a hand on a file that must not be touched casually. |

---

## THE ID SERVICE, AND HOW A BYPASS IS NOW DETECTED

`cedar_ids.allocate` takes an exclusive file lock and re-reads the counter from
disk, so two agents cannot mint the same id. **An f-string does neither.**

`284`'s existing `BYPASSED_ID_SERVICE` rule is *"the file does not mention
`cedar_ids`"* — which means the finding disappears the moment somebody imports
the module for an unrelated reason. `328_audit_id_service_bypass.py` is stricter
and is about **declaration**, not mention: a script writing a literal
`PREFIX-{…}` for a prefix the service mints must either call
`cedar_ids.allocate`, or call **`cedar_ids.declare_static_block(prefix, lo, hi,
owner, why)`**. Anything else is reported by file and line.

**Found by exactly that rule, and it was real.** `84_build_nigc_regions.py` and
`85_build_admin_region_crosswalk.py` between them minted **six** contiguous
`CEDAR-ADMREG` blocks by f-string, and `cedar_ids.RESERVED_BLOCKS` knew about
**exactly one** of the six. `allocate("CEDAR-ADMREG")` could have walked straight
into `BIA_REGION`. Both now declare their blocks; `declare_static_block` refuses
an overlap with a different owner and `allocate` steps over all of them.

A static block is a **legitimate** bypass — a build sometimes needs a
contiguous pre-assigned range so a given region's id is the same number on every
machine, which `allocate` cannot give. An **undeclared** one is not.

---

## WAIVED, WITH THE REASON ON THE LINE

Waivers are counted and listed by `293` on every run, never hidden.

- **13 × `id(obj)`** in `103`, `84`, `85`, `99` — Python **object identity** for
  an in-memory object, used as a key in a dict or set that lives and dies inside
  one function. Never written to a file, nothing joins on it, not a primary key.
  `293` waives the same shape in its own source.
- **1 × `uuid.uuid4()`** in `143:372` — a **multipart form boundary** for an HTTP
  POST to the Census batch geocoder. It must be unique per request and must
  never be reused; a deterministic value would be the defect there.

## NAMED, NOT TOUCHED — live work

- `227_anomaly_sweep.py:1038` — `hash(tuple(...))` for **within-run duplicate
  detection**. Consistent inside one process, never written down, so it is LOW.
  Not edited: the process was **running** during this session.
- `171_build_individual_native_verification.py:486` — `used_web.add(id(w))`,
  object identity, LOW. Not edited: it belongs to the live individual-Native
  agent (see BLOCKED above).

Both should get a `# lint-ok: class7 - …` waiver from their owners.

---

## GATE STATE, AND WHAT WAS AND WAS NOT RE-BASELINED

`293_lint_bug_classes.py`, before and after:

    class1 0 · class2a 0 · class2b 0 · class2c 60 · class3 0
    class4 9 · class5 6 · class6 33 · class7 74 -> 42
    lint_new_defect_instances 0 · total 182 -> 150 · --selftest PASS

**No class rose.** 16 waivers, each with its reason on the line.

**`293 --baseline` WAS run**, lowering the class-7 floor from 74 to 42. That is
what a floor is for: without it `class7` could climb back to 74 undetected. It
was safe to run because every other class was identical to the existing
baseline, so no other agent's in-flight finding was silently accepted. The old
baseline is kept at
`docs/lint_bug_classes_baseline.json.bak_2026-08-26_pre_327_migrate_class7_keys`.

**`62 --baseline` was deliberately NOT run.** `62` fails on five registry
metrics and on `tribe_year_lobbying_panel.csv` shrinking 5,051 -> 4,997, and
those belong to the lobbying/FOIA correction pass (scripts 350-358, written
20:14-20:15) — already named three times in `AGENTS.md`. Re-baselining would
have made somebody else's open failure disappear, which is the one thing
`--baseline` must never be used for. The three trap metrics
(`files_with_columns_lost_vs_backup`, `units_short_of_source_reported_total`,
`coverage_columns_that_do_not_exist`) are all **0** and `ship_dist_rows` rose.

## HOW TO VERIFY ANY OF THIS WITHOUT TRUSTING THIS DOCUMENT

    py -3 code/326_triage_class7_key_risk.py     # re-derive the triage
    py -3 code/327_migrate_class7_keys_to_digests.py   # DRY RUN, writes nothing
    py -3 code/328_audit_id_service_bypass.py    # bypass + key-contract check
    py -3 code/293_lint_bug_classes.py --selftest

327's dry run re-computes every digest from the live tables and reports
`cells_would_change`. **If the migration held, all 14 counts are 0** — measured
2026-08-26 after the fix below, and that is the whole check.

### THE COUNTER SAID "CHANGED" AND MEANT "TOUCHED"

Worth keeping, because it was caught by running the verification this document
recommends and finding it could never pass. `rewrite()`'s dry-run counter
incremented on every cell whose value was IN the old→new map — which, on an
already-migrated table, is *every* cell, because each id maps to itself. The
second dry run reported `earmarks.csv 1,002 cell(s)` on a file where nothing
would move, while `ferc_docket_filings.csv` correctly reported 0 because the
recompute path had always compared old against new.

Nothing was wrong with the data. What was wrong is that **a counter named
`cells_would_change` was reporting cells TOUCHED**, so the only end-to-end check
of the migration was unreadable — and a reader following this document would
have seen thousands of "changes" and concluded the migration had not held.

> **A counter's name is a claim about what it counts. If the number does not
> mean what the name says, the number is worse than no number** — it is the
> `87` defect wearing a different label, and here it would have discredited a
> correct result.

Both paths now compare, and all 14 counts read 0.
