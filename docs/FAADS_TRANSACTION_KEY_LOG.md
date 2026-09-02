# The FAADS transaction key — the queued re-extract, run

*Workstream FAADS, 2026-09-01. Every number here is produced by
`py -3 code/791_faads_transaction_key_and_repoint.py measure` /
`seam` and `py -3 code/30_funding_pre2008.py build`. Regenerate; do not
hand-edit (standing rule 10).*

---

## 1. What was queued, and why nobody had run it

`funding` carried four blockers — C1 grain unstated, C2 no validated key, C3
literal duplicates, C7 unsafe to total — and on both faads tables all four had
one cause. The source publishes `assistance_transaction_unique_key` and
`30_funding_pre2008.to_out_row` dropped it. 30 was taught to carry it on
2026-08-29; the re-extract was left queued because it is dangerous in a
specific, named way:

> `faads_entity_attribution.csv` keys **29,594 attributions to `faads_row_id`,
> which is the ROW POSITION** in `faads_transactions_all_agencies.csv`
> (`73_faads_name_attribution.py:544`, `for i, r in enumerate(rd)`). A
> re-extract re-orders that file and silently re-points every one of them.
> Nothing errors. No gate fails. The numbers stay plausible.

GRAIN-WS1 and GRAIN-WS4 both diagnosed it and neither could act.

## 2. What ran, in order

| step | command | effect |
|---|---|---|
| 1 | `791 interior --apply` | keyed the 60,661-row Interior slice from the seven full-column DOI seam zips |
| 2 | `791 snapshot` | fingerprinted all 29,594 pointer targets **before** the rebuild |
| 3 | `30_funding_pre2008.py build` | the re-extract |
| 4 | `791 repoint --apply` | re-found and re-pointed all 29,594, verified content-identical |
| 5 | `791 seam` | the FY2007 overlap, as a set |

`.bak_2026-09-01_pre791` was taken beside every table touched.

## 3. Rows and columns, before and after

| table | rows before | rows after | cols before | cols after | columns dropped |
|---|---:|---:|---:|---:|---|
| `faads_transactions.csv` | 60,661 | **60,661** | 25 | 27 | **none** |
| `faads_transactions_all_agencies.csv` | 2,769,748 | **2,769,748** | 25 | 27 | **none** |
| `faads_entity_attribution.csv` | 29,594 | **29,594** | 28 | 31 | **none** |
| `faads_identifier_coverage_by_agency_year.csv` | 77 | 77 | 11 | 11 | **none** |

The two added transaction columns sit **after** the existing 25, so the old
header is a byte-identical prefix of the new one. No row was deleted and no
dollar moved.

## 4. All 29,594 attributions still point at the same transaction

This is the claim the whole pass exists to be able to make, so here is how it
is evidenced rather than asserted. `repoint` does **not** assume the rebuild
preserved order, and does **not** match on the attribution row's own copy of
the transaction fields (those are lossy — `recipient_name` is upper-cased
there and `obligated_usd` is a float repr, not the source's 2dp string). It
matches on the transaction:

1. fingerprint the **24 published source columns** at each of the 29,594
   target positions in the **pre-rebuild** file;
2. give every occurrence of each fingerprint an **ordinal**, so a target
   inside a group of identical rows is "the n-th row with this content", not
   "some row like this" — **176 of the 29,594 sit in such a group**;
3. rebuild the same index over the **post-rebuild** file and map through it.

```
repoint: 29,594 of 29,594 positions re-found by content
repoint: 29,594 landed on the SAME position, 0 moved
```

The build turned out to be order-stable — but that is now a **measurement**,
not a hope, and `repoint` refuses rather than guesses if any fingerprint group
changes size.

`faads_row_id` is **KEPT**: it is the true record of what the 2026 build saw
and the only evidence of how the current attributions were made. Three columns
were added beside it — `faads_row_id_2026_09_01`,
`assistance_transaction_unique_key` (populated on 4,854 of 29,594) and
`faads_repoint_basis`. `faads_attribution_key`, minted by `710`, is untouched.

## 5. The duplicate allegation collapsed — with nothing deleted

| table | whole-row duplicates before | after |
|---|---:|---:|
| `faads_transactions.csv` | 1,001 | **0** |
| `faads_transactions_all_agencies.csv` | 179,259 | **3,441** |

**175,818 apparent duplicates disappeared because an identity column came
back, not because a row went away.** They were never duplicates; the mapper
had made distinct source transactions indistinguishable. A de-dupe would have
destroyed **$8,291,124,113** of real obligations.

All 3,441 survivors are in the FY2001–2006 non-Interior region — see §6.

## 6. WHAT THE DROPPED COLUMN HAD BEEN HIDING

**The three retained source groups are not the same object, and only two of
them contain the key at all.**

| staged objects | columns | key present |
|---|---:|---|
| 7 × `seam/doi_fy20{01..07}.zip` (Interior, FY2001–2007) | 112 | **yes** |
| 10 × `agencies/*_fy2007_archive.zip` | 112 | **yes** |
| 60 × `agencies/<agency>_fy200{1..6}.zip` | **20** | **no** |

The third group is **not a mapper bug a re-extract fixes**. `30.COLUMNS`
requested a 20-column subset from the bulk-download API and the key was not in
it, so the bytes on disk do not contain it. The only 112-column route for
those years is the USAspending Award Data Archive, and its own listing —
4,631 keys, `data/raw/usaspending_archive_2026-08-07/_archive_listing.csv` —
**begins at FY2007**. There is no FY2001–2006 full-column object to fetch.

Result: `assistance_transaction_unique_key` on **825,754 of 2,769,748 rows
(29.8%)** — every FY2007 row and every Interior row, unique with zero
collisions — and blank on the 1,943,994 FY2001–2006 rows of the other nine
agencies.

**`30.COLUMNS` now requests `assistance_transaction_unique_key` and
`modification_number`, so this cannot recur.**

### Re-pulling FY2001–2006 was decided against, not skipped

Every one of the 29,594 attributions lands on an FY2001–2006 row (`73` runs
`FY_MIN..FY_MAX` = 2001..2006). A re-pull would replace **exactly the rows the
attributions point at**, with live data that has restated since 2026-08-05,
and would destroy the ability to prove they still point at the same
transaction. Buying a key column at the price of the audit trail on every
attribution in the table is the wrong trade. The payoff is also
all-or-nothing: a primary key blank on even one row collides with the other
blanks, so a 99%-successful merge buys nothing.

**If an owner wants it:** re-pull the 54 non-Interior FY2001–2006 agency-years
through `30_funding_pre2008.py pull` (COLUMNS now asks for the key), then
**merge the key onto the existing rows by content** — never replace them —
and re-run `791 repoint` to re-prove the pointers. Read
`docs/PULL_DISCIPLINE.md` first: one poller per host, and `ps aux` cannot see
command lines on Windows.

## 7. Grain, declared and refused

* **`faads_transactions.csv` — DECLARED**, in `512.GRAIN_FAADS`, on
  `assistance_transaction_unique_key`: 60,661 of 60,661, 0 collisions, 0
  blanks. Every row was verified field-by-field against the seam object it was
  keyed from **before** the column was written.
* **`faads_transactions_all_agencies.csv` — REFUSED**, and the refusal is the
  finding. A primary key blank on 70% of a file is not a primary key. The
  widest honest alternative also fails by a knowable amount: 3,441 rows are
  byte-identical to another row across all 27 columns. Minting an occurrence
  ordinal would produce a unique column and is declined — a surrogate ordinal
  on a source-mirror table is how `faads_row_id` rotted in the first place.

## 8. The FY2007 seam, exact

| | rows | obligations |
|---|---:|---:|
| archive table FY2007 | 774,755 (100% keyed) | $475,359,703,131.83 |
| modern table FY2007 | 11,443 | $2,189,838,445.60 |
| **overlap — the same transaction on both sides** | **11,063** | **$2,165,856,968.60** |
| modern-only | 380 | $23,981,477.00 |

WS4's 98.9% dollar estimate was right to the cent; it is now **11,063
identified rows** rather than a ratio. Enforced by
`791 seam --verify` against `docs/schema/faads_fy2007_seam.json`. The rule and
what it can and cannot enforce are in `docs/MONEY_TOTALLING_RULES.md` between
the FAADS markers.

## 9. `funding` did not change status, and here is exactly why

The two faads tables are one of **three** tables the scoreboard names for
`funding`. The third is **`native_passthrough.csv`** (WS1/WS4's, derived from
`subawards.csv`), and it is independently unstated, carries 116 literal
duplicates and is money-unsafe. `funding` stays BLOCKED on C1/C2/C3/C7 for
`native_passthrough.csv` and `faads_transactions_all_agencies.csv` however
much the faads pair improves. The brief's premise that "all four blockers wait
on one thing" holds for the faads pair only.

---

# APPENDIX — the `canonical_name` defect on `federal_funding_transactions.csv`

*Measured 2026-09-01 by workstream FAADS at the coordinator's request, after
Codex flagged a hub/sub-hub inversion on a ten-row sample and a repair
attempt was withdrawn. **Measurement only. Nothing was repaired** —
`federal_funding_transactions.csv` is not this workstream's table and C4
identity resolution is explicitly out of scope.*

## Q1 — what is `canonical_name` in that table keyed to?

**Two different vocabularies, chosen per row by that row's own id scheme.**

| rows | `tribe_id_scheme` | `tribe_id` looks like | `canonical_name` comes from |
|---:|---|---|---|
| 183,491 | *(blank)* | `TRBF-ACOMAP-00` | the Cedar spine — agrees on **183,478 of 183,491** (13 exceptions, all one typo, `Warms Springs`) |
| 365,535 | `lineageA_dofile_integer` | `234` | **`data/raw/external/federal_funding/lineageA_dta_corrtd_tribe_key.csv`, the legacy Stata do-file's own `Tribe` label**, copied verbatim by `24_funding_merge.load_tribe_names()` |
| 152,929 | — | *(blank)* | unattributed |

That legacy key is the source of `haaku community academy` (it literally holds
`{tribe_id: 234, Tribe: 'haaku community academy', state: NM}`), and of
`navajo nation tribal government, the`, `oglala sioux tribe`, and the other
330 values that are not in the identity register. **`canonical_name` on those
365,535 rows is not a Cedar name at all.**

## Q2 — is the attribution wrong in the keyed columns, or only in the display name?

**Only in the display name. The keyed identity is correct in every case
Codex named.**

| recipient | `canonical_name` | `cedar_uid` | register says that uid is |
|---|---|---|---|
| `PUEBLO OF ACOMA (INC)` ×1,097 | `haaku community academy` | `CE-0011W-HN` | **Pueblo of Acoma**, Federally recognized tribe |
| `BLACKFEET …` ×3,831 | `blackfeet community college` | `CE-0012G-ES` | **Blackfeet** |
| `RED LAKE …` ×2,846 | `red lake nation college` | `CE-00197-V8` | **Red Lake** |
| `THREE AFFILIATED …` ×1,850 | `twin buttes elementary school` | `CE-0016W-A5` | **Three Affiliated** |
| `SAGINAW CHIPPEWA …` ×1,252 | `saginaw chippewa tribal college` | `CE-0019W-SN` | **Saginaw Chippewa** |

The register even records the reconciliation explicitly:
`CE-0011W-HN … same_as_legacy_cicd = '234'`. And it holds the **real**
sub-hubs as separate uids that the table uses correctly when the recipient
really is the school — `Blackfeet Community College` = `CE-0010N-2P` (312
rows), `Red Lake Nation College` = `CE-0011E-XQ` (202), `Saginaw Chippewa
Tribal College` = `CE-0011F-3G` (119).

At scale: of 552,602 rows carrying a `cedar_uid`, 345,108 have a
`canonical_name` that differs from the register's name for that uid, and
**339,129 of those (98.3%, $93,996,956,277) are explained entirely by the
legacy-CICD reconciliation** — the keyed identity is right, the label is
stale. Of the 5,979 unexplained, **3,620 have a blank `canonical_name` with a
uid present** (a missing label, not a wrong one).

**So entity-level grouping on `cedar_uid` — the hub key ADR-009 mandates —
credits the tribe, not the school. Only grouping on the legacy display name
credits the school.** That is why the withdrawn repair repointed 5,693 rows
and withdrew 3,265: it was correcting rows that were already correct.

## Q3 — where the real defect is, and it is not the one that was reported

Only **2,359 rows** have a non-blank `canonical_name` unexplained by the
legacy reconciliation, and sweeping the register for uids carrying more than
one legacy CICD id finds **exactly three**:

| cedar_uid | register name | legacy ids | legacy names | verdict |
|---|---|---|---|---|
| `CE-00134-BX` | Cherokee Nation | `347`, `43` | *united keetoowah band of cherokee*, *cherokee nation* | **WRONG — two distinct federally recognized tribes merged into one uid** |
| `CE-0015N-V6` | Kashia | `131`, `313` | *kashia band of pomo …*, *stewarts point rancheria* | correct — same tribe, two names |
| `CE-0014H-YJ` | Forest County | `186`, `92` | *(186 unused in the key)*, *forest county potawatomi community* | name-quality only |

**`CE-00134-BX` is a real misattribution: 820 rows and $181,881,441 of United
Keetoowah Band obligations are credited to Cherokee Nation.** The register
holds United Keetoowah Band of Cherokee Indians in Oklahoma as its own entity
(`CE-001BS-HA` / `TRBF-UKEETW-00`, T-0538, federally recognized), so this is
unambiguous — and it is the exact error `73_faads_name_attribution.py` guard 9
documents as "the worst error in the file", in the opposite direction.

**Owners.** The stale label is `24_funding_merge.load_tribe_names()`, which
copies the legacy do-file's `Tribe` string into `canonical_name`; the fix is a
relabel from the register wherever `cedar_uid` is present, and it changes no
attribution. The Keetoowah/Cherokee merge is a **register** defect in
`503_identity.py`'s reconcile phase (`same_as_legacy_cicd = '347,43'`) and
must be fixed there, not patched over the output.
