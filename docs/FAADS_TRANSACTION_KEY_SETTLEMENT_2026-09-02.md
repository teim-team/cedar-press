# The FAADS transaction-key ceiling, settled by measuring the zips

*2026-09-02. Every figure below was measured that day by
`code/1083_faads_zip_column_census.py` (read-only; opens each staged zip and
reads only the header bytes of each CSV member) and cross-checked against the
live `data/clean/faads_transactions_all_agencies.csv`. Regenerate rather than
trust: `py -3 code/1083_faads_zip_column_census.py --json docs/FAADS_ZIP_COLUMN_CENSUS.json`.*

---

## The dispute

`assistance_transaction_unique_key` is present on **825,754 of 2,769,748 rows
(29.81%)** of `faads_transactions_all_agencies.csv`. Two workstreams recorded
incompatible explanations, and neither said which OBJECTS it was talking about:

| | claim | where it is written |
|---|---|---|
| **A** | The 60 `<agency>_fy200{1..6}.zip` objects are **20-column** objects because `30_funding_pre2008.COLUMNS` requested a 20-of-112 subset. *"This is not a mapper bug that a re-extract fixes — the data was never downloaded."* | `docs/methodology/funding.md` §4b |
| **B** | *"the staged zip carries `assistance_transaction_unique_key` and `modification_number` among its 112 columns, and this function took neither"* — so a re-extract recovers it, and it is queued and unrun. | `code/30_funding_pre2008.py :: to_out_row` docstring; `review/OWNER_DECISION_QUEUE.md` §8b |

§8b's standing recommendation is **"run that rebuild"**.

## The measurement

83 CSV members across 77 staged objects. **Zero unmeasured.**

| | members | columns | `assistance_transaction_unique_key` |
|---|---:|---:|---|
| `seam/doi_fy20{01..11}.zip` + `agencies/*_fy2007_archive.zip` | **23** | **112** | **PRESENT** |
| `agencies/<agency>_fy200{1..6}.zip` | **60** | **20** | **ABSENT** |

The 60 narrow members share **one** header signature — byte-identical column
lists, no variation:

```
action_date_fiscal_year  action_date  cfda_number  cfda_title
awarding_agency_name  awarding_sub_agency_name  recipient_name
recipient_city_name  recipient_state_code  recipient_zip_code
recipient_duns  recipient_uei  business_types_code
business_types_description  federal_action_obligation
assistance_type_code  assistance_type_description  award_id_fain
record_type_code  usaspending_permalink
```

Cross-checked against the live table's own `source_file`, **77 of 77 with no
exception in either direction**:

| | source objects | rows | keyed in the clean table |
|---|---:|---:|---|
| 112-column on disk | **17** | 825,754 | **100.0% each** |
| 20-column on disk | **60** | 1,943,994 | **0.0% each** |

No keyed object is narrow. No unkeyed object is wide. 825,754 + 1,943,994 =
2,769,748.

## The verdict

**Both claims are true, about different objects, and that is why they looked
like a contradiction.**

- **Claim A is correct and it fully explains the 29.81%.** The ceiling is the
  60 twenty-column objects and it is physical. The bytes do not contain the
  column, and `_All_Assistance_Full_` in the award archive begins at FY2007, so
  there is no full-column source for those years to re-extract from.

- **Claim B is correct about the objects it was looking at** —
  `ed_fy2007_archive.zip` genuinely is 112 columns and genuinely does carry the
  key — **but the re-extract it queues would recover ZERO new keys**, because
  all 17 wide objects are already 100% keyed in the live table.
  `code/791_faads_transaction_key_and_repoint.py` did that work on 2026-09-01,
  by content merge rather than rebuild, and took the duplicate count from
  179,259 to 3,441 without deleting a row or a dollar.

**So `review/OWNER_DECISION_QUEUE.md` §8b's recommendation to run
`30_funding_pre2008.py build` is now wrong on both premises, and running it
would cost something.** A full re-extract re-points `faads_row_id`, which is a
ROW POSITION and is the anchor for all 29,594 attributions in
`faads_entity_attribution.csv` — the exact hazard `791` spent a fingerprint-
and-ordinal pass defending against. **The upside is zero and the downside is
the audit trail.**

**Derivation is also closed, not merely the download.** The key's format is
`{awarding_sub_agency_code}_{fain}_{uri}_{cfda}_{modification_number}` —
verified on `doi_fy2003.zip`: `1434_9005CS0007_-NONE-_15.808_7`. Of its five
components the 20-column objects carry `cfda_number` and `award_id_fain` and
**not** `awarding_sub_agency_code` and **not** `modification_number`. Two of
five are physically absent, and `modification_number` is precisely the
component that separates transactions on one award. There is no route.

## What CAN be recovered from those 60 objects, and was

The 20-column objects carry `usaspending_permalink` on **1,943,994 of
1,943,994 rows**, and its last path segment is the published
**`assistance_award_unique_key`**:

```
https://www.usaspending.gov/award/ASST_NON_V%2099956301B_068/
                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^
```

That is an AWARD-level identifier published by the source, not a surrogate.
`code/1086_faads_award_key_promote.py` promoted it:

| | |
|---|---:|
| rows | 2,769,748 → 2,769,748 **conserved** |
| obligations | $1,830,639,317,707.66 → $1,830,639,317,707.66 **conserved to the cent** |
| `assistance_award_unique_key` filled | **2,769,748 (100.0%)** |
| — from the 112-column objects' own column | 825,754 |
| — derived from `usaspending_permalink` | 1,943,994 |
| ambiguous groups (refused, not guessed) | **0** |
| rows with no permalink | **0** |
| `verify` | exit 0 |

Join safety was proved before anything was written: over the narrow objects the
key `(source_file, award_id_fain, record_type)` resolves to **1,493,774 groups,
every one of which maps to exactly one award key.** A group with more than one
would have been refused.

**This is award grain, not transaction grain, and it makes no grain claim.**
`faads_transactions_all_agencies.csv` still has **no validated primary key and
an UNSTATED grain**, and the 3,441 remaining byte-identical rows are still
there, still flagged, still inside the unkeyed FY2001–2006 region. What the
column buys is that a pre-2008 award can now be followed forward into
`federal_funding_transactions.csv`, which carries the same identifier from
FY2007 on.

## A premise that did not survive contact

The transaction key was described as *"the largest single ceiling on the
funding dataset's geography and identity."* Measured on the live table, it is
neither:

| column | rows | fill |
|---|---:|---:|
| `recipient_zip` | 2,393,275 | **86.4%** |
| `geo_recipient_county_fips` | 2,402,032 | **86.7%** |
| `recipient_duns` | 677,035 | 24.4% |
| `recipient_uei` | 604,653 | 21.8% |
| `assistance_transaction_unique_key` | 825,754 | 29.8% |

`recipient_zip_code` and `recipient_city_name` are **both among the 20 columns
that were downloaded**, so geography never depended on the key. And identity
was never going to come from it either: `tribe_id` and `cedar_uid` are blank on
all 2,769,748 rows *by design* — neither `faads_*` table is a Native table, and
the Native attribution for those years lives outside both files in
`faads_entity_attribution.csv`.

**What the transaction key is actually the ceiling on is GRAIN** — the ability
to declare a primary key and let a buyer aggregate safely. That is worth
stating plainly, because it is the one thing no promotion here can fix.

## Standing consequences

1. **`review/OWNER_DECISION_QUEUE.md` §8b is superseded.** A dated correction
   was appended there rather than the item being rewritten.
2. **`code/30_funding_pre2008.py :: to_out_row`'s docstring is right about
   FY2007 and misleading about the file as a whole.** Its `COLUMNS` fix is
   still correct and still matters — for any FUTURE pull, not for these bytes.
3. **`code/1086_faads_award_key_promote.py` is an IN-PLACE ENRICHER.** A
   rebuild of `faads_transactions_all_agencies.csv` by
   `30_funding_pre2008.py build` reverts it. The signal is
   `faads_transactions_all_agencies.csv.bak_*_pre_1086_faads_award_key_promote`
   sitting beside the table. Re-run 1086 after any rebuild, and after `872`,
   which is the other in-place enricher on this file.
4. **The 60 narrow objects are the whole ceiling, and they are named.** Nobody
   needs to re-open this by sampling. `docs/FAADS_ZIP_COLUMN_CENSUS.json` lists
   every member, its column count and its key presence.

---

## RE-MEASURED AND CONFIRMED, 2026-09-02T15:40Z — with two corrections to this page

`code/1083_faads_zip_column_census.py` was re-run independently and reproduces
this page exactly: **83 members over 77 objects, 0 unmeasured; 23 members at 112
columns with the key PRESENT; 60 members at 20 columns with the key ABSENT; one
single header signature across all 60.** Cross-checked against the live table
the same minute: `assistance_transaction_unique_key` on **825,754 of 2,769,748
rows (29.81%)**, `assistance_award_unique_key` on **2,769,748 (100.0%)**, and
`count(distinct source_file)` splits **60 unkeyed / 17 keyed** with nothing in
between. **Claim A is settled: no re-extract of the bytes on disk can recover
the key.**

Two things this page and `docs/methodology/funding.md` §4b state that the census
does not support.

**1. It is 60 agency-years, not 54.** §4b's recovery path says *"re-pull the 54
non-Interior FY2001–2006 agency-years."* The narrow objects are
`{doc, doe, doj, dol, dot, ed, epa, hhs, hud, usda}` × `fy2001..fy2006` —
**10 × 6 = 60**, and the live table carries exactly 60 distinct unkeyed
`source_file` values. Interior is not among them; it is the seam corpus. 54 is
not reproducible from any file here.

**2. "There is no full-column source for those years to re-extract from" is
false, and this page's own census disproves it.**

| object | member | date pulled | columns | key |
|---|---|---|---:|---|
| `seam/doi_fy2001.zip` | `All_Assistance_PrimeTransactions_2026-08-05_H19M06S27_1.csv` | 2026-08-05 **19:06Z** | **112** | **PRESENT** |
| `agencies/ed_fy2001.zip` | `All_Assistance_PrimeTransactions_2026-08-05_H20M25S30_1.csv` | 2026-08-05 **20:25Z** | **20** | ABSENT |

Same fiscal year, same endpoint — `POST api.usaspending.gov/api/v2/bulk_download/awards/`
— same day, **79 minutes apart**, and the SERVER's own job record states the
width in both cases: `data/raw/external/faads/seam/_meta.json` → `"2001"` has
`"total_columns": 112` (build time **10.1 seconds**, 6,951 rows) and
`data/raw/external/faads/agencies/_state.json` → `jobs.ed_fy2001` has
`"total_columns": 20`. Identical record schema, identical
`All_PrimeTransactions_2026-08-05_*.zip` naming. The only difference between
the two payloads is the `columns` key: `30_funding_pre2008.build_payload` sends
`COLUMNS` (20 of 112), and the seam job omitted it.

The archive listing beginning at FY2007 is true and is beside the point: the
narrow objects never came from the archive. **The bulk-download API serves
FY2001 assistance at the full 112 columns today and has already done so for
Interior.**

**So the honest disposition of the 1,943,994 unkeyed rows is `NOT_ACQUIRED`,
not `SOURCE_DOES_NOT_PUBLISH`** — the two states
`docs/AGENT_FIELD_GUIDE.md` §5 exists to keep apart. The answer to *"can 2.77M
rows ever be keyed?"* is **yes**: by a fresh 112-column pull of those 60
agency-years, merged onto existing rows **by content**, exactly the route §4b
already writes down. Nothing about that changes §4b's reason **3** for not doing
it — all 29,594 attributions in `faads_entity_attribution.csv` are keyed to
`faads_row_id`, a ROW POSITION, and a merge-by-content pass is what protects
them — and it remains an owner decision, not an agent's.

**What is genuinely closed is DERIVATION, not acquisition.** Two of the key's
five components (`awarding_sub_agency_code`, `modification_number`) are
physically absent from the 20 columns, and `modification_number` is the one
that separates transactions on a single award. No arrangement of the bytes on
disk produces the key. That part of this page stands unchanged.

**The re-pull was NOT run in this pass and the reason is stated rather than
implied:** `api.usaspending.gov` allows one poller at a time, it was held by the
`fy2023_q4` subaward re-pull, and 60 sequential bulk-download jobs is a
multi-hour commitment against a rule-3 hazard the owner has not lifted.
