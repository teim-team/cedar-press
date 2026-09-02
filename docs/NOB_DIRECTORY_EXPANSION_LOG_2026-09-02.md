# Native-owned businesses — the directory expansion, 2026-09-02

*Workstream `NOB-DIRECTORIES-2026-09-02`. Two scripts,
`code/1146_shard_directory_admission.py` (zero network) and
`code/1147_released_host_directories.py` (six hosts, 75 requests). Every number
below was measured on this machine after the work landed; re-derive any of them
with the `verify` subcommand named beside it.*

```
py -3 code/1146_shard_directory_admission.py report | apply | codebook | verify | selftest
py -3 code/1147_released_host_directories.py plan | probe | fetch | parse | apply | verify | selftest
```

---

## THE HEADLINE

| | before | after |
|---|---:|---:|
| `data/clean/native_owned_businesses.csv` rows | 2,916 | **4,273** |
| certifying authorities | 21 | **42** |
| source ids | 21 | **42** |
| distinct normalised firm names | — | 4,024 |

**+1,357 rows and the authority count exactly doubled.** 614 of those rows cost
zero network requests; 744 came off six hosts that were refused until the owner's
2026-09-02 terms ruling released them.

The two halves are different kinds of work and are worth keeping apart:

| | rows | authorities | network |
|---|---:|---:|---|
| `1146` — already harvested, never promoted | **614** | 15 | **none** |
| `1147` — released hosts, harvested here | **744** | 6 | 75 requests |

---

## PART 1 — 614 rows that were already on this disk

`docs/AGENT_FIELD_GUIDE.md` §5: *"missing" has four causes and only one is a
download.* This is `ON_DISK_NOT_PROMOTED`, and it is the largest instance found
so far in this dataset.

`data/staging/business_registry/` holds 36 harvested directory files. Fifteen
had never reached `data/clean`, and **not because anything was wrong with
them.** `330_build_native_owned_businesses.py promote` refuses any staging file
whose source id is absent from its `SOURCES` / `PRIOR` / `SIBLING` dicts:

> `!! TBD-L01_....jsonl: unknown source id TBD-L01 - NOT PROMOTED. A staging
> file whose certifying authority, assertion class and terms status this script
> cannot state is a file it must not promote.`

**That refusal is correct and should stay.** But 330's `SIBLING` dict was
written on 2026-09-01, and `570_shard_l_vendor_list_hunt.py` (TBD-L01…L11),
shard_m (TBD-M01…M03) and shard_c (TBD-C03) wrote into that directory
afterwards. Fifteen nations' directories — harvested, parsed, provenanced, with
their terms status and claim text already recorded on every row — were invisible
to the dataset because nobody had written down the one adjudication 330 needs.

`1146` writes it. Per source: the certifying authority's spine id (all fifteen
confirmed present in `cedar_entity_spine.csv`), the programme name, and the
`assertion_class` where the staged rows carry none. Everything else is read off
the staged row and never re-derived.

| source | authority | rows |
|---|---|---:|
| TBD-L01 | Hoopa Valley Tribe | 136 |
| TBD-L04 | Wampanoag Tribe of Gay Head (Aquinnah) | 101 |
| TBD-C03 | Puyallup Tribe of Indians | 88 |
| TBD-M03 | Pyramid Lake Paiute Tribe | 74 |
| TBD-M02 | Sisseton-Wahpeton Oyate | 45 |
| TBD-L02 | Bad River Band | 39 |
| TBD-L03 | Little Traverse Bay Bands of Odawa Indians | 35 |
| TBD-L08 | Citizen Potawatomi Nation | 27 |
| TBD-M01 | Spokane Tribe of Indians | 23 |
| TBD-L11 | Kalispel Tribe of Indians | 12 |
| TBD-L07 | Confederated Tribes of the Chehalis Reservation | 10 |
| TBD-L09 | Shoshone-Bannock Tribes | 10 |
| TBD-L10 | Chitimacha Tribe of Louisiana | 7 |
| TBD-L05 | Delaware Tribe of Indians | 4 |
| TBD-L06 | California Valley Miwok Tribe | 3 |

Two staging files are **HELD**, with the reason recorded rather than left to be
rediscovered: `TBD-C01` is the same 337 rows as `TBD-079` (Muscogee Creek CESO
list) and 330 already refuses it as a duplicate; `TBD-L00` is the identifier
crosswalk built by `1000`/`1001`, not a certifying authority's directory.

---

## PART 2 — the six directories the terms ruling released

`docs/PUBLICATION_POLICY.md` `TERMS-OWNER-RULING-2026-09-02` released an
eight-source hard list. **Nothing had been harvested off it.** Before this pass
`native_owned_businesses.csv` carried 21 certifying authorities and **none of
the eight**. `code/1114_capability_statement_harvest.py` reached several of
those hosts the same day, but it was hunting CAGE/UEI strings, it promoted
nothing into `data/clean`, and a certifying authority's vendor directory is a
different object from a capability statement.

| source | authority | rows | route |
|---|---|---:|---|
| TBD-R01 | The Chickasaw Nation | **602** | 17 category pages, `?catID=1…17` |
| TBD-R06 | NANA Regional Corporation (Akima) | 50 | `opco-sitemap.xml` → 50 opco pages |
| TBD-R02 | Confederated Tribes of the Colville Reservation | 44 | `/tero` → `ContractorListJune26-cm9y.pdf` |
| TBD-R05 | Southern Ute Indian Tribe | 18 | TERO page → `2026-Indian-Own-Business-List.pdf` |
| TBD-R04 | Forest County Potawatomi Community | 16 | `shop.fcpotawatomi.com/businesses/` |
| TBD-R03 | CTUIR / Umatilla | 14 | TERO → Certified IOB Directory → `.docx` |

**Terms status per source: all six were `TERMS_STATED_RESTRICTIVE`, and all six
still say so on every row.** The ruling made that a recorded observation rather
than a gate. `615_set_publishable_native_owned_businesses.PERMISSION_OK` is an
allow-list that does not include it, so **all 744 rows land `publishable = N`**
and the publication question is 615's to answer, not this pass's. See the owner
item below.

**Politeness.** One poller, one host at a time, 4s per-host delay, honest
declared User-Agent naming the project and the owner's contact address,
exponential backoff on 429/503, a 120-request cap that prints a named warning
and returns non-zero rather than silently truncating, and every request's
status, bytes and elapsed time appended to
`data/staging/business_registry/raw/_1147_fetch_log.jsonl` **before** the next
one is made. `fetch` is idempotent: a snapshot already on disk costs zero
requests. **75 requests total, 0 non-200s, 0 backoffs.**

**robots.txt, measured per host:** `www.colvilletribes.com`,
`shop.fcpotawatomi.com`, `www.southernute-nsn.gov` and `www.akima.com` serve a
robots file and it permits these paths. `www.chickasawbusinessnetwork.com` and
`ctuir.org` do not serve one — recorded as *"robots.txt not served; absence is
not a prohibition"*, which is the `PULL_DISCIPLINE` correction: a 403 or a
missing robots file is not a `Disallow`.

**Still refused, and none of it is a terms question:** technical access controls
(no login-gated content, no admin or staging path — `REFUSED_PATH` in `1147`
rejects `/wp-admin`, `/Stagingsite/`, `/login` and friends before a request is
made); a natural person's data held apart from their public role; proprietary
identifiers.

---

## THE PII LINE, AND WHERE IT ACTUALLY SITS

Forest County Potawatomi, Chickasaw, Colville, Southern Ute and the Hoopa
register all publish an owner's personal name, email address, mobile number and
in several cases a home address beside each firm.

**None of those five columns exists in `native_owned_businesses.csv`, and
neither script creates one.** Both `build_rows` functions raise rather than
emit a column the live table does not already hold, and both assert
`set(330.WITHHELD) & emitted == {}` before writing a byte. The contact channel
stays in the staging JSONL; what ships is `owner_name_present` (1,421 rows),
`n_owners_named`, and `withheld_fields` naming exactly what was held (3,284
rows).

A firm's name is the firm's name — that is settled, and the 2026-09-02 owner
correction in `615` is right that suppressing "Jane Doe Construction" protects
nobody. A person's home phone is a different object.

---

## FOUR PARSERS WERE WRONG BEFORE THEY WERE RIGHT, AND ALL FOUR ARE THE SAME DEFECT

`AGENT_FIELD_GUIDE` §3: *the number was produced, it was plausible, and it was
about something else.* Every one of these was caught by printing rows next to
the count, and none of them shipped.

| parser | first cut said | what it was actually reading |
|---|---:|---|
| Colville | **262 firms** | a line sweep over a PDF **table**. The first twenty-two "firms" were the column headers (`Contractor Name`, `Primary Contact`, `Zip`, `Email`) and the work-category codes (`01 Roads & Bridges (small)`, `70 Long Log Logging Trucks`). Read as a table with `pdfplumber`, column 1 only: **44** |
| CTUIR | **75 firms** | every paragraph of a prose `.docx`, including the office's own phone number, its four named staff and the five-member TERO Commission — **publishing named individuals as firms**. Anchored on the `Certificate Valid …` line that follows each real entry: **14**, which matches the registry's independently recorded count exactly |
| Southern Ute | **172 firms** | the document title, the TERO's PO box, the office fax number, `Vernon Etsitty` (a person), and four lines of a services paragraph. Read as laid-out records — split on the underscore rule, firm/owner split at the widest horizontal gap on the record's first line: **18**, against 17 underscore rules in the file |
| Akima | 50 rows named `Aet`, `Afl`, `Agl`, `Protective Services`, `Mission Support` | the `/opcos/` index is a grid of **logo images with `alt=""`** — there is no text to read — and a three-letter slug is an acronym, not a legal name. Reading each opco page's `<title>`: **50 real company names** |

Two smaller ones, same shape:

- **The Southern Ute list URL was discovered as a FORM.** The first cut matched
  `Indian Owned Business Annual Update Form` (a blank application, 2023) before
  `2026 Indian Owned Business Listing`, parsed 0 rows, and would have reported
  the source as empty. Anchor text is now scored and anything naming itself a
  form, an application, an amendment or a code is refused by name.
- **A `ti` ligature in the Colville PDF renders as `H`** — `ConstrucHon`,
  `RefrigeraHon`, `ConsulHng`. A capital `H` between two lowercase letters does
  not occur in English, so the repair is narrow; the raw rendering is kept
  verbatim in `validation_flags` on every row it touched, so it is reversible.

---

## THE PRIMARY KEY WAS NOT UNIQUE, AND THE ROWS WERE FINE

`business_source_id` is this table's declared primary key. On first apply it
was **not unique**: six keys covered eighteen Pyramid Lake rows.

`AGENT_FIELD_GUIDE` §4 — four of five duplicate allegations in this repo were
phantom, and this is a sixth. **Nothing is duplicated.** shard_m keys a row on
a hash of the FIRM NAME, and the Pyramid Lake Paiute Tribe issues one licence
per *activity*:

```
I80 Smoke Shop   PL 2025-029   Convenience Store
I80 Smoke Shop   PL S2025-005  Liquor Retails Sales
I80 Smoke Shop   PL 2025-030   Convenience Store
I80 Smoke Shop   PL S2025-006  Food Services Business
I80 Smoke Shop   PL S2025-007  Liquor Retails Sales
```

Collapsing those would delete four real licences. The **rows** are right; the
**key** is wrong. It is widened with the discriminator the source itself
prints — `business_license_number` — and only where it collides, so no existing
key changed.

**The first fix was itself a defect.** Where the source printed no licence
number the fallback was an ORDINAL (`#n1`, `#n2`), which is defect class 7: an
id minted from a row's POSITION, stable only while the file's row order is.
`293` caught it. It is now a digest of the columns that actually differ between
the colliding rows, so the id is a function of the record and nothing else, and
the one row that had taken an ordinal was re-keyed. **Invariant V7 in `1146
verify` fails the build if `business_source_id` is ever non-unique again.**

Measured now: **4,273 rows, 4,273 distinct `business_source_id`, 0 blank, 0
literal duplicate rows, and 0 sources where the live count differs from the
staging count in either direction.**

**The migration to that key left one row too many, and V1 could not see it.**
Stripping the retired ordinal suffixes produced a BARE key, which
`_repair_live_keys` then read as un-collided and left alone, so the merge
appended the correctly-keyed row beside it: `TBD-M03` stood at 74 rows against
73 in staging while every floor was green. **A floor cannot see a row too
many.** `_retire_superseded_keys` removes a row only when all four of
(admitted source, key this build does not emit, an identical row under a key it
does, identical in every column but the key and the flags) hold - anything
else is printed and KEPT - and the retired row is written to
`review/native_owned_businesses_1146_retired_key_rows.csv` before the table is
rewritten. **V8 is the ceiling V1 is the floor of**, and it fired on this exact
row before the fix.

---

## WHY THIS APPENDS INSTEAD OF REBUILDING, AND THE HALF THAT IS EASY TO FORGET

`330 promote` is a FULL REBUILD, and five in-place enrichers have touched this
table since the last one — the `.bak_*` files beside it name them: `_pre615`,
`_pre_1070merge`, `_pre_953_nob_federal_identifier_candidates`, `_pre_doyon`,
`_pre_1100_nob_crosswalk_promotion`. `330 promote` writes with `restval=""`, so
a rebuild today would carry the enrichment COLUMNS and blank their VALUES: the
rebuild/in-place collision `START_HERE.md` records four separate times.

So both passes write through `cedar_pipeline.merge_table`, which preserves every
live row and every live cell and raises rather than drop a column.

**And both write their adjudication to a file `330 promote` now READS** —
`data/staging/business_registry/_shard_admission_dispositions.json` and
`_released_host_dispositions.json`, merged into 330's `SIBLING` dict by a new
hook that never overrides a decision made in code. Without that hook the next
rebuild drops all twenty-one sources again and prints nothing but its own
progress. `1146`'s **V6** and `1147`'s **V5** fail while the hook is absent.

When no disposition file is present, 330 now prints a named warning naming the
two commands that produce them — an absence must never print as a clean result.

---

## THREE THINGS FIXED THAT WERE NOT THIS PASS'S WORK

1. **`native_owned_businesses.csv` was an ORPHAN in its own collection.**
   `512` had been reporting *"ORPHAN shippable table: native_owned_businesses.csv
   — registered in the codebook but claimed by NO collection"*: the flagship
   table of the `native-owned-businesses` collection was not in that
   collection's `tables` pattern in `500_build_architecture_map.COLLECTIONS`,
   which read `^(individual_native|tribal_certification)`. Fixed, anchored so it
   claims exactly one file. `512`: orphans 9 → 8, violations 16 → 15, tables
   claimed 303 → 304, grain-stated shippable 246 → 247.

2. **A `cedar_codebook build` was silently dropping 20 rows of this table's
   codebook — and it did so DURING this session.** `330 codebook` writes a
   fragment describing its own 53 `CLEAN_COLUMNS`; the live table has 74,
   because 953, 1070 and 1100 wrote their 21 columns straight into
   `codebook_master.csv` and never into a fragment. `cedar_codebook build` is
   fragment-driven, and the global shrink guard cannot see a 21-row loss inside
   a 6,000-row file. The divergence was written into `1146`'s docstring at
   ~17:2x and the loss happened at 17:38, fifteen minutes later. **Reporting it
   was not enough.** `1146 codebook` now recovers the dropped rows from the
   newest master backup that still holds them — description verbatim — and
   writes the FULL 74-variable block to the fragment, so a rebuild reproduces
   it. `py -3 code/cedar_codebook.py check` now says **SAFE — a rebuild loses
   nothing** (was: 20 would be LOST).

3. **`publishable_basis` shipped with no codebook row at all.** Added, described
   from the code that writes it (615's allow-list), not invented.

---

## FOR THE OWNER — one decision, and it is narrow

**Three terms statuses now in this table fall outside
`615.PERMISSION_OK` and hold 1,126 rows back from publication:**

| status | rows | what it means |
|---|---:|---|
| `TERMS_STATED_RESTRICTIVE` | 1,090 | includes all 744 rows from the six sources **the owner's own 2026-09-02 ruling released**. The ruling moved the harvest gate; nobody has moved the publication gate |
| `NOT_CHECKED` | 19 | Chitimacha and Kalispel — the terms page was never opened. Not a refusal, an unmeasured state |
| `TERMS_STATED_COPYRIGHT_ONLY` | 17 | Delaware Tribe, California Valley Miwok, Chehalis. **A copyright notice is not a reuse restriction**, and holding these is almost certainly over-exclusion — the defect the field guide calls *wrong in the quieter direction* |

Widening that allow-list is `615`'s decision and this pass did not take it. The
rows are admitted and held, so the answer is a one-line change and a re-run
rather than a re-harvest.

---

## WHAT WAS NOT DONE

- **Yakama and Stillaguamish** are the two of the eight released sources not
  harvested here. Both hosts answer 200 (probed 2026-09-02) but neither
  publishes a business directory at a route this pass located, and
  `review/tribal_vendor_list_registry_2026-08-26.csv` records no `list_url` for
  either. That is `ROUTE_NOT_FOUND`, not `CHECKED_ABSENT`, and it is a
  discovery task.
- **Nothing here touched NEST.** The 50 Akima operating companies are admitted
  as a `subsidiary_directory` / `parent_asserted_subsidiary` business-directory
  source, exactly as ASRC Federal (TBD-056) and Doyon (TBD-059) already are.
  Whether they should ALSO become `nest_enterprises` rows is `1072`'s decision
  and its `load_sources()` is the place for it — this pass did not open that
  file.
- **The two `native_owned_businesses.bak_*.csv` files in `data/clean` are still
  reported as orphan shippable tables.** They are backups written with `.bak`
  INFIXED rather than suffixed, so `512`'s codebook-side scan reads them as
  tables. Renaming them to the project's `.csv.bak_<tag>` convention would
  close two more violations; it was left alone because another agent's script
  wrote them this session and a rename mid-session is a collision risk.
