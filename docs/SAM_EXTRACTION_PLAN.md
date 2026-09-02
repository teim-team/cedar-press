# SAM.gov extraction plan

*Written 2026-08-12, immediately after the key went live and all five endpoints
returned HTTP 200. This is the plan for today and tomorrow.*

---

## WHAT WE CONFIRMED (not assumed)

| endpoint | `totalRecords` | meaning |
|---|---:|---|
| `entity-information/v3/entities` | 1 | key is valid |
| `contract-awards/v1/search?fiscalYear=2007` | **4,112,136** | **the historical universe exists** |
| `contract-awards/v1/search?fiscalYear=2000` | **591,754** | FY2000 exists |
| `prod/contract/v1/subcontracts/search` | **2,733,178** | procurement subawards |
| `prod/assistance/v1/subawards/search` | **7,358,406** | assistance subawards |

Two consequences, both large:

1. **Stop developing any FPDS-NG ATOM crawler.** FY2000 and FY2007 are both
   served here. The hardest gap in the project has a route.
2. **SAM is now a second source system**, not a fallback. USAspending's
   `bulk_download` failing is no longer a blocker for anything.

---

## THE CONSTRAINT THAT DECIDES EVERYTHING: which rate tier are we on?

| account state | daily limit |
|---|---|
| non-federal user, **no role** in SAM.gov | **10 requests/day** |
| non-federal user **with a role** | **1,000/day** |
| non-federal **System Account** | 1,000/day |

**We do not yet know which tier this key is on.** The profile has a `Roles` tab
and the workspace showed a `Request A Role` widget, which suggests no role - the
10/day tier.

**Five requests were already spent today** on the probes above. If we are on
10/day, roughly **five remain**.

### Why the tier matters more than anything else in this document

The two endpoint families behave completely differently:

| family | mode | implication |
|---|---|---|
| **Contract Awards** | async **extract**, up to **1,000,000 records per call** | a whole fiscal year in 1-5 calls |
| **Subawards** (both) | **paginated** - response carries `totalPages`, `pageNumber`, `nextPageLink` | 1,000 records/page = **one request per 1,000 rows** |

Subawards at 2.73M procurement records is **~2,733 requests** at `pageSize=1000`.

- At 10/day that is **273 days**. Not viable.
- At 1,000/day it is **under 3 days**. Viable.

> **ACTION ITEM, higher priority than any pull: request a role in SAM.gov.**
> Profile > Roles, or the "Request A Role" widget on Workspace. This is the
> difference between the subaward gap closing this week and not closing at all.
> It costs zero API calls.

---

## TODAY - spend the remaining calls on the highest value per call

Everything today goes to **Contract Awards**, because its extract mode returns up
to 1M records per request. Subawards are paginated and would waste the quota.

### Call 1 (diagnostic, cheap, decides the whole strategy)

Test whether the **Native socioeconomic flags filter server-side**. The response
schema carries:

```
alaskanNativeCorporationOwnedFirm
americanIndianOwned
indianTribeFederallyRecognized
nativeHawaiianOrganizationOwnedFirm
triballyOwnedFirm
```

Request `fiscalYear=2007` plus one flag, `limit=1`, and read `totalRecords`.

- **If `totalRecords` drops sharply** (4.1M -> tens of thousands), the flags are
  filters. FY2000-2007 Native contracts then fit in **one or two extracts
  total**, and the entire backfill is done today.
- **If `totalRecords` stays 4,112,136**, the flag was ignored as a filter and we
  must pull full years and filter locally - 4.1M records for FY2007 alone means
  **5 extract calls for that year** at the 1M ceiling.

This single call determines whether the job costs 2 calls or 20.

### Calls 2-5 (whichever branch we are on)

**If flags filter:** extract FY2000-2007 Native-flagged awards, `format=csv`.
Partition by fiscal year. Likely 1-2 calls for the whole 8-year span.

**If flags do not filter:** start at **FY2000 (591,754 records)** - it is under
the 1M ceiling, so it is exactly one call, and it is the year the archive can
never reach. Then FY2001, FY2002 ascending; the early years are smallest and buy
the most irreplaceable coverage per call.

**Do not start with FY2007.** At 4.1M records it needs 5 partitioned calls and
would consume the entire remaining daily quota for one year.

---

## TOMORROW - and the standing order of work

1. **Confirm the tier.** If the role came through, everything below is days
   rather than months.
2. **Finish Contract Awards FY2000-2007.** This is the unique-to-SAM prize:
   nothing else serves these years.
3. **Then subawards FY2021-24** via `prod/contract/v1/subcontracts/search`,
   paginated at `pageSize=1000`, one sequential poller.
4. **Then assistance subawards** (7.36M records) - lowest priority, since our
   assistance coverage is already complete FY2007-2026.

### Calibration before trusting any of it

Pull **FY2019 and FY2020** subawards from SAM and reconcile against the FSRS rows
we already hold from USAspending. If counts, IDs and amounts agree on years we
already trust, SAM is validated as a substitute for FY2021-24. If they do not
agree, we have learned something important before contaminating the panel.

Same discipline for contracts: pull one archive-covered year (FY2012, where we
hold 42,322 full-universe rows) and reconcile before trusting FY2000-2007.

---

## RULES FOR THE PULL

- **Partition every extract to stay under 1,000,000 records.** Exceeding it
  returns a 400 with `"Count Exceeded Error"`, not a truncated file - so an
  over-large request wastes a call and returns nothing.
- **The extract returns a download URL containing the literal string
  `REPLACE_WITH_API_KEY`.** Substitute the key, then GET it. If the file is not
  ready the API says so; poll with a deadline, do not resubmit.
- **One poller. Sequential.** Never parallelise against SAM. A 429 or a block
  costs the whole day's quota.
- **Checkpoint the token before the first poll**, exactly as the USAspending
  runner does. An accepted job whose token is lost is a wasted call.
- **Count every request.** At 10/day the quota is the scarcest resource in the
  project. Log each call with its purpose so the day's spend is auditable.
- **Partition on `dateSigned` / `fiscalYear`, but derive our fiscal year from the
  record's own date field**, never from the request window. The subaward APIs
  filter on submission date, which is NOT the same as `subAwardDate`.

---

## THE LICENSING RULE THIS PULL MUST HONOUR

Recorded in full in `AGENTS.md`. In short:

**D&B Open Data** - legal business name, street, city, state, ZIP, country - may
not be disseminated **in bulk**, and it attaches to **all base award notices with
an award date before 2022-04-04**. That is 100% of the FY2000-2007 backfill.

| field class | example | publish? |
|---|---|---|
| contract fact | PIID, action date, obligation, NAICS, agency, socio-economic flags | **yes** |
| D&B Open Data | legal business name, street, city, state, ZIP | **not in bulk** |

**Every SAM-sourced row must carry a provenance flag naming SAM**, so this is
answerable per field later rather than making a whole file unshippable.

Verified 2026-08-12: nothing currently shipped is affected - zero of 20,555
ledger rows with a `legal_business_name` came from a SAM source.

---

## THE SECOND PRIZE, WHICH IS NOT A BACKFILL

The Contract Awards response carries `indianTribeFederallyRecognized`,
`triballyOwnedFirm`, `alaskanNativeCorporationOwnedFirm`,
`nativeHawaiianOrganizationOwnedFirm` and `americanIndianOwned` **as fields on
the award**, alongside UEI and CAGE.

The BGOV failure we measured was **missing entities**, not wrong dollars - 20
Native entities present in the full FY2022 universe and absent from the filtered
file. These flags are a **federal self-certification** of Native ownership on
every contract action back to FY2000.

So this pull is also an **entity-discovery pass**: it can surface Native entities
our crosswalk has never seen, across 26 fiscal years. That is worth more than the
transactions.

**Caveat to carry:** a self-certification is a claim by the firm, not an
adjudication. It is evidence toward tier B, never an automatic tier A, and it
does not distinguish tribally *owned* from individually Native-owned - a
distinction Cedar Press keeps strictly separate.


---

# MEASURED 2026-08-12 — the plan above is superseded on two points

## 1. The Native filter EXISTS, and it changes the cost by 5x

The socioeconomic flags (`indianTribeFederallyRecognized`, `triballyOwnedFirm`,
etc.) are **output fields only** — both return HTTP 400
`"The search parameter(s) does not exist"`. But the docs' real parameter list
carries something better:

```
awardeeBusinessTypeName=INDIAN   ->  57,537 of 4,112,136   (1.40% of FY2007)
```

**A whole fiscal year of Native contracts fits in ONE extract call**, far under
the 1,000,000-record ceiling. The plan above assumed 5 partitioned calls for
FY2007. It is one.

Other filters worth using, all confirmed present in the parameter list:

| parameter | why it matters |
|---|---|
| `awardeeBusinessTypeName` | partial match — the Native filter |
| `typeOfSetAsideName` | docs' own example is `BUY INDIAN` (untested — quota) |
| `awardeeUniqueEntityId` | up to **100 UEIs** per query — targeted reconciliation |
| `ultimateParentUniqueEntityId` | up to 100 — pull an entire ANC family at once |
| `fiscalYear`, `dateSigned` | partitioning |
| `format=csv` + `emailId` | the async extract |

**Untested and important:** `awardeeBusinessTypeName=INDIAN` is a partial match,
so it will catch "Indian Tribe" and similar, but may MISS Alaska Native
corporations and Native Hawaiian organisations whose business-type strings do not
contain "INDIAN". **Test `ALASKAN NATIVE`, `NATIVE HAWAIIAN`, and `TRIBAL` as
separate queries before treating any year as complete.** Four variants per year,
deduplicated on PIID + modification number.

## 2. We are on the 10/day tier, confirmed

```
HTTP 429  {"code":"900804","message":"Message throttled out",
           "description":"You have exceeded your quota .
            You can access API after 2026-Aug-13 00:00:00+0000 UTC"}
```

Quota resets **00:00 UTC**, i.e. 8pm ET. Ten requests bought: five endpoint
probes, two rejected-parameter tests, two filter tests, one throttle.

### The arithmetic that makes the role non-optional

Contract Awards, 4 business-type variants x 27 fiscal years (FY2000–2026) =
**~108 calls**.

| tier | time to finish contracts |
|---|---|
| 10/day | **11 days** |
| 1,000/day | **one afternoon** |

And subawards are *paginated*, not extracted — 2.73M procurement rows at
`pageSize=1000` is **~2,733 calls**: 273 days at 10/day, under 3 days at 1,000.

> **Requesting a role is worth more than any single day's pulling.**
> Profile > Roles, or "Request A Role" on Workspace. Costs zero API calls.

---

## THE ORDER OF WORK, given 10 calls/day

**Tonight after 00:00 UTC — 10 calls, highest irreplaceable value first:**

1. `awardeeBusinessTypeName` variant test on ONE year (3 calls: ALASKAN NATIVE,
   NATIVE HAWAIIAN, TRIBAL). Establishes whether one query per year is enough or
   four are. **Everything downstream depends on this.**
2. FY2000 extract, `format=csv` (1 call). Smallest year, and the archive can
   never reach it.
3. FY2001–FY2006 extracts (6 calls).

That is FY2000–2006 substantially complete in one day — **the gap USAspending
structurally cannot fill.**

**Tomorrow:** FY2007 onward, then the calibration pass — pull FY2012 (where we
already hold 42,322 verified full-universe rows) and reconcile before trusting
any of FY2000–2007.

**Subawards wait for the role.** At 10/day they are not attemptable.

---

## THE ENTITY-DISCOVERY PRIZE, and its limit

Confirmed present on every award record:

```
awardeeUltimateParentUniqueEntityId   P9QQX7RT8E98
awardeeUltimateParentName             GOLDBELT INCORPORATED
usTribalGovernment / housingAuthoritiesPublicTribal / tribalCollege
alaskanNativeServicingInstitution / nativeHawaiianServicingInstitution
```

**The parent-subsidiary link is served directly.** Cedar Press's hierarchy rule —
publish `ultimate_parent_entity_id`, treat intermediate levels as tier B — can be
populated from the federal record instead of inferred, across 27 fiscal years.

**The limit, measured on the very first record returned:** Goldbelt Raven LLC is
an Alaska Native corporation subsidiary, and its own certification reads
`alaskanNativeCorporationOwnedFirm = NO`, `triballyOwnedFirm = NO`,
`americanIndianOwned = YES`. The flags are internally inconsistent because they
are a **firm's self-certification, not an adjudication**.

**Rule: a SAM socioeconomic flag is evidence toward tier B. It is never an
automatic tier A, and it does not distinguish tribally owned from individually
Native-owned** — a distinction Cedar Press keeps strictly separate. The
`awardeeUltimateParentUniqueEntityId` is a far stronger signal than any flag.

---

# THE RUNBOOK — written 2026-08-26 after the first extract landed

*Everything above this line is the PULL plan. This section is the LOAD runbook:
what to do when an extract is on disk. It was written with one of six extracts
in hand and the other five pending, and it is the whole procedure for those
five. **It requires no new engineering.***

## The two scripts, and the line between them

| script | does | costs quota |
|---|---|---|
| `code/141_pull_sam_contract_awards.py` | submits extracts, downloads them | **yes** |
| `code/163_load_sam_contract_awards.py` | normalises, dedupes, reconciles, writes | **no — makes no network calls at all** |

That line is deliberate. 141 spends an irreplaceable resource and must be run
with the budget in mind. 163 reads files and can be run twenty times in a row.

## TOMORROW, AFTER 00:00 UTC — the exact sequence

```
py -3 code/62_no_regression_check.py                     # baseline, before
py -3 code/141_pull_sam_contract_awards.py status        # 0 calls
py -3 code/141_pull_sam_contract_awards.py download      # <= 5 calls, the five tokens
py -3 code/163_load_sam_contract_awards.py load          # 0 calls
py -3 code/62_no_regression_check.py                     # after
```

**Spend the first five calls on `download` and nothing else.** The submissions
are done and are the irreplaceable half; the tokens `EANGlhSctK` (INDIAN),
`fdgGBhrCjJ` (ALASKAN NATIVE), `YkWOTVSRHn` (NATIVE HAWAIIAN), `xAjEAaGtTI`
(AMERICAN INDIAN) and `PTdhhaQztU` (NATIVE AMERICAN) are already paid for and
are checkpointed in `data/raw/contracts/sam_contract_awards/_export_tokens.json`.
A download is retryable; a submission is not.

**Do not re-run `canary` or `extract`.** `TRIBAL` (`zrlwsqiydG`) is already
downloaded and loaded. Re-submitting a variant that already has a token discards
accepted server-side work and spends a call to do it.

### The download trap, restated because it will cost a token

A file still generating answers:

```
HTTP 303  "Cannot proceed with download: The specified key does not exist.
           (Service: S3, Status Code: 404 ...)"
```

**That 404 is S3's, about an object not yet WRITTEN.** It is not `api.sam.gov`
saying anything about the request. `download()` recognises the string and keeps
the token. Read literally it says "the export does not exist" and gets a live
token thrown away.

## What 163 accepts, and what it refuses

It scans `data/raw/contracts/sam_contract_awards/` for:

```
sam_extract_<TOKEN>.zip          <- what a browser/API download produces
sam_extract_<TOKEN>.csv
sam_fy2000_2007_<class>_<variant>.csv    <- what 141 download() writes
```

A `.zip` is read in place; the single CSV member is streamed out. A zip with
more than one CSV member is **refused and named**, never guessed at.

**Token to variant to class is resolved from `_export_tokens.json`, which 141
wrote when the submissions were accepted. A file whose token is not in that
manifest is REFUSED and printed, not guessed at.** Guessing would put
`INDIVIDUAL_NATIVE_OWNED` rows into the `ENTITY_OWNED` class silently, which is
the one error this dataset cannot survive. Measured refusal message:

```
REFUSED  sam_extract_BOGUS9999.zip: token 'BOGUS9999' not in _export_tokens.json
```

For the `sam_fy2000_2007_*` filename form, the **class comes from
`VARIANT_CLASS`, not from the filename** — renaming a file cannot reclassify a
row.

## Resumability, and what "already processed" means

State lives in `data/raw/contracts/sam_contract_awards/_loader_state.json`, keyed
by export token, and records the file, its SHA-256 prefix, rows in, rows added,
rows already present, and the UTC timestamp. A processed token is skipped.
`load --force` re-processes everything; because the merge is keyed, re-processing
is idempotent rather than duplicative.

`status` prints, with zero cost:

```
  extracts on disk : 1
    TRIBAL           [ENTITY_OWNED           ] sam_extract_zrlwsqiydG.zip  LOADED 8273 rows
  awaiting download : ['INDIAN', 'ALASKAN NATIVE', 'NATIVE HAWAIIAN', 'AMERICAN INDIAN', 'NATIVE AMERICAN']
```

## THE DEDUPLICATION KEY — measured, five parts, and four of them are not enough

The variants overlap heavily: a tribally owned firm that also self-certifies
`americanIndianOwned` is returned by both `TRIBAL` and `AMERICAN INDIAN`. The
transaction must be stored **once**.

Measured on the 8,273-row TRIBAL extract:

| key | distinct |
|---|---:|
| `piid + mod` | 7,633 |
| `piid + mod + txn` | 7,638 |
| `subtier + piid + mod + txn` | 7,654 |
| **`subtier + piid + mod + txn + referencedIDVPiid`** | **8,273 = unique** |

**A delivery order's PIID is unique only within its parent IDV**, so the
referenced IDV PIID is part of the identity, not decoration. `dateSigned` is
deliberately NOT in the key: a re-download must dedupe against what is already
loaded, and a date is a fact about the row, not a component of its name.

On a collision the row is kept once, `matched_variants` accumulates
(`AMERICAN INDIAN;TRIBAL`), and:

- `variant_class` = `ENTITY_OWNED` if **any** entity variant claimed it — a
  tribally owned firm whose owner also self-certifies as an individual American
  Indian is a tribal enterprise, not an individual;
- `class_conflict = 1` records that both classes claimed it, so the case can be
  **ruled** rather than silently resolved.

**Rehearsed 2026-08-26** in an isolated copy, with a synthetic
`AMERICAN INDIAN` extract sharing 300 transactions with the TRIBAL one: 500 rows
in, **+200 new / 300 already present**, 300 rows carrying
`matched_variants = AMERICAN INDIAN;TRIBAL` and `class_conflict = 1`, all keys
unique, and no combined total emitted anywhere.

## THE TWO CLASSES ARE NEVER SUMMED

    ENTITY_OWNED             INDIAN, ALASKAN NATIVE, NATIVE HAWAIIAN, TRIBAL
    INDIVIDUAL_NATIVE_OWNED  AMERICAN INDIAN, NATIVE AMERICAN

Already recorded in `LICENSING.md` and in 141. 163 enforces it structurally:
`summary()` and the reconciliation report iterate the two classes and **emit no
total row**. There is nothing to accidentally quote.

Design rationale is in `docs/INDIVIDUAL_NATIVE_CLASS_PROPOSAL.md`.

## THE PARTIAL-MATCH TRAP — a variant hit is NOT evidence of Native status

`awardeeBusinessTypeName` is a **partial string match**, and the business type
**"HOUSING AUTHORITIES PUBLIC/TRIBAL" contains the string "TRIBAL"**.

**Measured on the TRIBAL extract: 87 rows, 11 UEIs, $710,492 carry ZERO Native
flag of any kind.** They are City of Wichita, City of Dodge, the Housing
Authority of the City of Los Angeles, Scott Electric Company, City of Laredo,
City of Lakeland, City of Monroe, Southeastern Newspapers, Arrington
Enterprises, K C Electronic Distributors and Commercial Interior Design. Each
one has `housingAuthoritiesPublicTribal = YES` and nothing else.

They are **kept** — the raw is the raw — and marked:

```
variant_match_basis        = HOUSING_AUTHORITY_PUBLIC_TRIBAL_ONLY
native_flag_any            = 0
include_in_native_universe = 0
```

**Filter on `include_in_native_universe = 1` for any Native count.** Expect the
same shape on the other five variants and check it every time: the `INDIAN`
variant will match `INDIAN TRIBE` and also anything else containing the
substring, and the `NATIVE AMERICAN` variant is a substring of a great many
business-type strings.

## RECONCILIATION — establish what is NEW without double-counting

**The two files are not the same grain and no key makes them so.**
`prime_contracts.csv` FY2000–2007 comes from `master prime file.dta` at
**award-year-vendor** grain (1.26 rows per contract-year). SAM is at
**transaction** grain. Comparing row counts across that seam manufactures a
number that means nothing, which is the same error shape as the BGOV/archive
merge on 2026-08-12.

So the reconciliation is reported at **PIID** and **PIID x fiscal year**, and
every row carries:

| column | meaning |
|---|---|
| `recon_piid_held` | the contract number exists somewhere in `prime_contracts.csv` |
| `recon_piid_fy_held` | this contract-year exists |
| `recon_uei_held` | this awardee UEI exists |
| `novelty` | `PIID_FY_HELD` / `PIID_HELD_NEW_FY` / `PIID_NEW` |
| `double_count_risk` | 1 where `novelty = PIID_FY_HELD` |

**Never add this file's `action_obligation` to `prime_contracts.csv`'s
`total_obligations` without excluding `double_count_risk = 1`.**

### Measured, TRIBAL variant, against 1,217,768 prime rows

| | rows | PIID | PIID x FY | $ obligation |
|---|---:|---:|---:|---:|
| `PIID_FY_HELD` — already held | **7,622** | 4,739 | 5,816 | $1,215,228,639 |
| `PIID_HELD_NEW_FY` | 171 | 35 | 68 | $7,923,601 |
| `PIID_NEW` | **480** | **203** | 241 | $17,139,716 |
| **total in file** | 8,273 | 4,973 | 6,125 | $1,239,581,464 |

**92.1% of the TRIBAL extract is already held.** The genuinely new material is
**651 rows on 309 contract-years, $25.06M**, plus **18 UEIs
`prime_contracts.csv` has never seen** — staged to
`review/sam_fy2000_2007_new_entities_<date>.csv`, unruled.

**That low novelty rate is the finding, and it is good news.** It is the
calibration this plan asked for and did not have: the BGOV-sourced FY2000–2007
years reproduce SAM's own record on 4,739 of 4,973 contract numbers. The
FY2000–2007 block is far more complete than the "filtered at download time"
warning implied — for the TRIBAL slice. The other five variants are exactly
where the missing entities would be, which is why they are worth the calls.

Note also the fiscal-year skew: FY2000 34 rows, FY2001 66, FY2002 137, FY2003
450, then FY2004 1,660, FY2005 1,861, FY2006 2,043, FY2007 2,022. **SAM's
own coverage of the early years is thin.** Do not read a small FY2000 count as a
pull failure; read it as the source's floor, and say so in any coverage table.

## LICENSING — four independent marks, because one gets lost

Every row is a base award dated before 2022-04-04, so **D&B Open Data attaches
to 100% of this backfill.** The restriction is marked in four places:

1. **Column naming.** Every restricted field is prefixed `dnb_` —
   `dnb_awardee_legal_name`, `dnb_awardee_name`, `dnb_awardee_dba_name`,
   `dnb_ultimate_parent_name`, `dnb_awardee_street1/2`, `dnb_awardee_city`,
   `dnb_awardee_state`, `dnb_awardee_zip`, `dnb_awardee_country`. A `SELECT *`
   cannot pretend not to know.
2. **A row-level flag.** `dnb_open_data_restricted = 1`, present in the
   publishable view too, so a derived table inherits the mark.
3. **The codebook fragment.** `data/clean/codebook/02e_sam_contract_awards.csv`
   marks every `dnb_` variable `published = 0`, `access_tier = internal`, with
   the restriction spelled out in the description.
4. **A physical view without them.**
   `data/clean/sam_prime_contracts_fy2000_2007_PUBLISHABLE.csv` — 78 columns
   instead of 88, the ten D&B columns simply absent. That is the file that can
   ship. A machine-readable manifest sits at
   `data/clean/sam_prime_contracts_fy2000_2007._LICENSING_MANIFEST.json`.

**UEI, CAGE and `ultimate_parent_uei` are federal identifiers, not D&B Open
Data, and they publish** — with one carve-out that bites on the individual
class: where the legal name is a person's, the UEI resolves to that person via
SAM's own public entity search, so it is a pointer to a name. See
`docs/INDIVIDUAL_NATIVE_CLASS_PROPOSAL.md` section 5.

**This bites hardest on the individual-native rows, where the legal name IS a
person.** Even in the *TRIBAL* extract, **8 of 402 UEIs carry a legal business
name that is unambiguously a personal name** — `ROBYN NELSON`, `GANJE ROBERT`,
`MENDIETA, RENATA N`, `FRANK ROSS`, `TULLY GENEVIEVE`, `STANLEY NICHOLE`,
`PAVELOVA EVA`, `COOPER GERALD` — each with a street address in the same row.
The AMERICAN INDIAN and NATIVE AMERICAN extracts select for exactly that, so the
share will be higher. That is a privacy exposure a tribal government's name is
not, and it is a **second restriction independent of the D&B licence**: it
survives any answer to the licensing question.

## SELF-CERTIFICATION — carried on every row

`socio_econ_basis = SELF_CERTIFICATION`, always. A SAM socio-economic flag is
the firm's own assertion, not an adjudication. **Goldbelt Raven LLC, an Alaska
Native Corporation subsidiary, certifies `alaskanNativeCorporationOwnedFirm =
NO`, `triballyOwnedFirm = NO`, `americanIndianOwned = YES`.** Evidence toward
tier B; never an automatic tier A. `awardeeUltimateParentUniqueEntityId` is a
far stronger signal than any flag — populated on 8,232 of 8,273 rows here.

And the flags do not separate the two classes: `americanIndianOwned = YES` on
**2,846 of 8,273 rows of the TRIBAL extract**, all tribal enterprises.

## OUTPUTS

| path | what |
|---|---|
| `data/clean/sam_prime_contracts_fy2000_2007.csv` | 88 columns, all rows, D&B fields present and marked |
| `data/clean/sam_prime_contracts_fy2000_2007_PUBLISHABLE.csv` | 78 columns, D&B fields absent |
| `data/clean/sam_prime_contracts_fy2000_2007_reconciliation.csv` | per class x novelty, no cross-class total |
| `data/clean/sam_prime_contracts_fy2000_2007._LICENSING_MANIFEST.json` | machine-readable restriction |
| `data/clean/codebook/02e_sam_contract_awards.csv` | the per-dataset FRAGMENT — never `codebook_master.csv` |
| `review/sam_fy2000_2007_new_entities_<date>.csv` | UEIs absent from `prime_contracts.csv`, unruled |
| `data/raw/.../_loader_state.json` | resume checkpoint |

Every write is `.part` then rename, and any pre-existing output is backed up to
`.bak_<date>_pre163` first.

**163 does not merge into `prime_contracts.csv` and must not be made to.** The
merge is a separate, reviewed decision that needs the double-count exclusion
applied and all six variants in hand. `131_merge_archive_backfill.py` is the
precedent for how that is done and what it costs to get wrong.

## Housekeeping

- **Script number 163 has four files on it** (`163_link_adjudication_hubs.py`,
  `163_link_nonprofit_family_via_ein_hub.py`,
  `163_promote_nho_universe_in_place.py`, `163_load_sam_contract_awards.py`).
  The prefix has not implied step order for weeks; concurrent agents claim
  numbers simultaneously. Check `ls code/<n>_*` and pick a distinct **name**,
  not a distinct number.
- **`62_no_regression_check.py` reports one pre-existing failure**,
  `codebook_undocumented_public = 45`, on both the before and after runs of
  2026-08-26. It predates this build and is not caused by it. Do not read it as
  a regression from the SAM load; do check the count has not grown.

---

# THE LOAD HAPPENED. ALL SIX EXTRACTS ARE ON DISK AND LOADED (2026-08-26, ~20:30)

*Everything above this line was written with ONE of six extracts in hand. This
section is what the other five actually contained. Where a figure above
describes the TRIBAL slice, it is still true of that slice and is no longer
representative of the pull.*

    py -3 code/163_load_sam_contract_awards.py load --force     # 0 network calls
    py -3 code/358_measure_sam_individual_native_class_delta.py # 0 network calls

## What landed

| variant | class | rows in | new | already held by another variant | absent source columns |
|---|---|---:|---:|---:|---|
| NATIVE AMERICAN | INDIVIDUAL_NATIVE_OWNED | 158,199 | 106,740 | 51,459 | — |
| INDIAN | ENTITY_OWNED | 157,093 | 157,093 | 0 | — |
| AMERICAN INDIAN | INDIVIDUAL_NATIVE_OWNED | 52,714 | **0** | 52,714 | — |
| TRIBAL | ENTITY_OWNED | 8,273 | 1,730 | 6,543 | — |
| ALASKAN NATIVE | ENTITY_OWNED | 3,716 | 3,384 | 332 | `streetAddress2` |
| NATIVE HAWAIIAN | ENTITY_OWNED | 379 | 365 | 14 | `streetAddress2`, **`cageCode`** |
| **union** | | **380,374** | **269,312** | | |

**The TRIBAL row is not the same as the first load's.** On its own it added
8,273; loaded after the other five it adds **1,730**, because 6,543 of its
transactions were already carried in by INDIAN, ALASKAN NATIVE or NATIVE
AMERICAN. That is the dedup working, and it is why an "extract row count" and a
"rows contributed" are two different numbers.

## THE DEDUP KEY HOLDS AT SCALE — measured on all six, not extrapolated

`subtier|piid|mod|txn|referencedIDVPiid` is **unique on 380,374 of 380,374
rows**, with **zero intra-file collisions in any of the six extracts**. The
warning in the runbook above is now quantified: `piid + mod` alone would have
collapsed the NATIVE AMERICAN extract from 158,199 to **115,403**, silently
destroying **42,796 distinct transactions** in one file.

## THE FINDING: 65% OF THE INDIAN EXTRACT IS NOT NATIVE, AND IT IS $11.1 BILLION

The runbook above says *"expect the same shape on the other five variants and
check it every time"*. Checked. The shape is the same and the scale is three
orders of magnitude larger:

> **"Subcontinent Asian (Asian-INDIAN) American Owned Business" contains the
> string "INDIAN".**

`awardeeBusinessTypeName=INDIAN` is a PARTIAL match, so it returns
Asian-Indian-American-owned firms. Measured on the INDIAN extract:

| basis | rows | UEIs | obligation |
|---|---:|---:|---:|
| **SUBCONTINENT_ASIAN_INDIAN_AMERICAN_ONLY** | **102,587** | **3,774** | **$11,129,475,544** |
| NATIVE_FLAG | 54,505 | 2,404 | $5,055,122,424 |
| NO_NATIVE_FLAG_UNEXPLAINED | 1 | 1 | $0 |

**65.3% of the largest ENTITY_OWNED variant has no Native attribute of any
kind.** Anyone counting "Native contracting FY2000–2007" off a raw variant hit
overstates it by **$11.1B**. All of it is KEPT — the raw is the raw — every row
carries `variant_match_basis` naming the reason, and every row carries
`include_in_native_universe = 0`. **The housing-authority trap that produced 87
rows and $710,492 on TRIBAL is the same defect at 1/1000th the scale.**

The `flag_subcontinent_asian_indian_american_owned` column now travels on every
row so the exclusion can be audited rather than trusted.

## THE VARIANT OVERLAP MATRIX — and the variant that contributed nothing

Rows shared, computed from `matched_variants` on the merged table:

|  | INDIAN | ALASKAN NATIVE | NATIVE HAWAIIAN | TRIBAL | AMERICAN INDIAN | NATIVE AMERICAN |
|---|---:|---:|---:|---:|---:|---:|
| **INDIAN** | 157,093 | 332 | 0 | 4,615 | **52,714** | 48,276 |
| **ALASKAN NATIVE** | 332 | 3,716 | 0 | 1,002 | 319 | 3,515 |
| **NATIVE HAWAIIAN** | 0 | 0 | 379 | 0 | 0 | 14 |
| **TRIBAL** | 4,615 | 1,002 | 0 | 8,273 | 2,846 | 4,323 |
| **AMERICAN INDIAN** | 52,714 | 319 | 0 | 2,846 | 52,714 | 48,130 |
| **NATIVE AMERICAN** | 48,276 | 3,515 | 14 | 4,323 | 48,130 | 158,199 |

Rows matched by that variant **alone**: INDIAN 102,591 · NATIVE AMERICAN 105,517
· TRIBAL 1,730 · NATIVE HAWAIIAN 365 · ALASKAN NATIVE 184 · **AMERICAN INDIAN 0**.

**`AMERICAN INDIAN` is a strict subset of `INDIAN`** — all 52,714 of its rows —
because "American Indian Owned" also contains the string "INDIAN". It cost a
call and contributed **zero unique transactions**. That is not a wasted call: it
is the measurement that proves the two queries are nested, which nothing short
of running both could establish. **Do not re-submit it.**

## AND THAT NESTING BREAKS THE CLASS ASSIGNMENT — 49,792 rows need a ruling

The merge rule is *"ENTITY_OWNED wins if any entity variant claimed the row"*.
That rule is sound when the entity variant's claim means something. Here it
frequently does not, because the entity variant `INDIAN` claims rows whose
business type is **"American Indian Owned"** — an assertion about a **PERSON**.

Measured across the 57,266 contested transactions:

| what the ENTITY_OWNED assignment rests on | rows | UEIs | obligation |
|---|---:|---:|---:|
| an entity-ownership flag is YES (tribal govt / tribally owned / federally recognized / ANC / NHO / tribal college) | 7,474 | 285 | $1,365,604,584 |
| **NO entity-ownership flag — assigned by the SUBSTRING alone** | **49,792** | **2,272** | **$4,448,849,761** |

**Neither the variant nor the flags separate the two classes.** The flags were
already known not to (`americanIndianOwned = YES` on 2,846 of 8,273 TRIBAL
rows); now the variants are known not to either. **`variant_class` is
PROVISIONAL on those 49,792 rows and they are staged, unruled, at
`review/sam_class_conflicts_<date>.csv` with `entity_claim_basis` naming which
of the two situations each one is in.** Nothing was resolved silently.

## PER CLASS — and there is still no total line

| | rows | in native universe | UEIs | PIIDs | obligation (native universe) |
|---|---:|---:|---:|---:|---:|
| ENTITY_OWNED | 163,795 | 61,120 | 6,346 | 96,330 | $6,441,905,593 |
| INDIVIDUAL_NATIVE_OWNED | 105,517 | 105,517 | 2,912 | 30,706 | $22,789,700,023 |

**883 of the 8,375 distinct UEIs carry transactions in BOTH classes.** A
per-firm total that pooled them would book tribal-enterprise dollars onto the
individual class; `358` holds every per-firm figure per class for that reason.

## RECONCILIATION vs `prime_contracts.csv` — the novelty rate COLLAPSED

The TRIBAL slice was 92.1% already held. The full pull is not:

| class | novelty | rows | PIID | PIID x FY | obligation |
|---|---|---:|---:|---:|---:|
| ENTITY_OWNED | PIID_FY_HELD | 77,703 | 37,263 | 43,341 | $9,074,957,943 |
| ENTITY_OWNED | PIID_HELD_NEW_FY | 4,048 | 1,905 | 2,394 | $426,033,136 |
| ENTITY_OWNED | **PIID_NEW** | **82,044** | **57,660** | 63,985 | $8,071,100,550 |
| INDIVIDUAL_NATIVE_OWNED | PIID_FY_HELD | 101,347 | 28,928 | 42,219 | $22,391,603,498 |
| INDIVIDUAL_NATIVE_OWNED | PIID_HELD_NEW_FY | 1,481 | 383 | 600 | $242,751,230 |
| INDIVIDUAL_NATIVE_OWNED | **PIID_NEW** | **2,689** | **1,406** | 1,817 | $155,345,295 |

**50.1% of ENTITY_OWNED rows carry a contract number `prime_contracts.csv` has
never seen** — against 5.8% on the TRIBAL slice alone. Most of that novelty is
the Asian-Indian population, which is new to us because it is not Native and was
never in scope; **read `PIID_NEW` next to `include_in_native_universe`, never on
its own.** The measurement that matters is that the TRIBAL-slice conclusion
*"the FY2000–2007 block is far more complete than the warning implied"* **does
not generalise** — it was a property of the tribal slice.

**`double_count_risk = 1` on 179,050 rows.** Never add this file's
`action_obligation` to `prime_contracts.total_obligations` without excluding
them.

## 3,558 UEIs `prime_contracts.csv` HAS NEVER HELD

Staged unruled to `review/sam_fy2000_2007_new_entities_2026-08-26.csv`, against
18 from the TRIBAL slice. **A SAM socio-economic flag is a self-certification
and none of these is a spine row.**

## TWO LOADER CHANGES THIS MADE NECESSARY, both recorded in `163`'s docstring

1. **The extracts do not share a column set** — 322 to 379 columns. SAM omits a
   column that is empty across a whole result set, so an ABSENT column and a
   PRESENT-BUT-BLANK column render identically through `row.get(col) or ""`.
   That is named defect class **2b**. `cageCode` is absent from the NATIVE
   HAWAIIAN extract, so those 379 rows would have published a blank CAGE that
   read as a fact about the firms. Every file's header is now audited: a missing
   CRITICAL column (any part of the dedup key, fiscal year, date signed,
   obligation, UEI) **refuses the file by name**, and any other absence is
   recorded per row in the new `source_columns_absent` column.
2. **It does not fit in memory as a list.** `read_extract` returned
   `list(csv.DictReader(...))`; the INDIAN extract alone is 157,093 rows x 379
   columns and costs roughly 3.5 GB that way. It is now `iter_extract()`, a
   generator, with pooled values — measured 6,857 -> 3,904 bytes per stored row.
   Merge semantics are unchanged and the load is idempotent: a second
   `--force` run reproduced every output byte for byte.

## THE INDIVIDUALLY NATIVE-OWNED CLASS — the delta, measured

`code/358_measure_sam_individual_native_class_delta.py`. Full numbers and the
publication accounting are in `docs/INDIVIDUAL_NATIVE_CLASS_PROPOSAL.md`, and
the headline is that **69% of the class's SAM dollars belong to firms the ledger
already binds to a tribal, ANC or NHO entity** — so the individual class's
$22.79B is not the individual class's money.

---

# 2026-08-28 — THE ROLE DID NOT LAND, AND THE PRIZE IS NOT REACHABLE ANYWAY

*Measured, not reported. Every number below came off the wire today and the
response bodies are on disk at `data/raw/external/sam_entity_management/`.*

## 1. THE MEASURED RATE LIMIT: 10/day. We are still on the no-role tier.

Eleven sequential calls to `api.sam.gov/entity-information/v4/entities`,
2026-08-28 18:17–18:18 UTC, one poller, lock held at
`logs/_HOSTLOCK_api.sam.gov.json`, every call logged to
`logs/sam_entity_calls.jsonl`:

    calls 1-10   HTTP 200
    call 11      HTTP 429
                 {"code":"900804","message":"Message throttled out",
                  "description":"You have exceeded your quota .You can access
                  API after 2026-Aug-29 00:00:00+0000 UTC",
                  "nextAccessTime":"2026-Aug-29 00:00:00+0000 UTC"}

**Exactly ten. The org role request has NOT been granted.** The 2026-08-12
measurement stands unchanged sixteen days later. Reset is 00:00 UTC as before.

Note the shape: this is the **WSO2** throttle (`900804`), not the api.data.gov
gateway's `OVER_RATE_LIMIT`. Both are stop-work; a detector that only looks for
`OVER_RATE_LIMIT`, or only for HTTP 429, will miss one of them.

## 2. THE EIN-UEI ROUTE IS NOT RATE-LIMITED. IT IS PERMISSION-GATED, AND THE ROLE REQUEST WOULD NOT OPEN IT.

`docs/IDENTIFIER_GRAPH_BUILD_LOG.md` records the standing plan: *"A SAM entity
registration carries the registrant's TIN/EIN … blocked on the same 10/day →
1,000/day role request that blocks subawards."* **The first half is true; the
second half is wrong, and it has been directing effort at the wrong obstacle.**

Verbatim from the Entity Management API manual
(`GSA/open-gsa-redesign`, `_apidocs/entity-api.md`):

> **Sensitive Data Access** — "This constitutes both the publicly available
> entities and the entities that have opted out of public display with their CUI
> data such as banking information and **SSN/TIN/EIN**."

> **FOUO Data Access** — "…their CUI data such as **hierarchy**, company and
> employee security levels and points of contact email address, phone, and fax
> numbers."

And the access matrix:

| level | who may read it |
|---|---|
| Public | non-federal or federal personal/system account, "Read Public" |
| FOUO (CUI) | **Federal System Account** with "Read FOUO" |
| Sensitive (CUI) | **Federal System Account** with "Read Sensitive", POST only |

`taxpayerIdentificationNumber` appears **only** in the Sensitive section of the
query-parameter table (v1-v4).

**Cedar Press is a non-federal registrant. There is no role, org role, or system
account available to us that reaches Sensitive.** The pending role request buys
**throughput only** — 10/day → 1,000/day — and moves us from "Read Public" to
"Read Public, faster."

**Consequences, and they are load-bearing:**

- **SAM is NOT an EIN-UEI route for us.** The identifier-graph plan's item 1
  should be struck, not rescheduled. The 28 EIN-UEI edges we hold remain the
  whole of it, and closing that gap needs a different source — not more quota.
- **SAM is NOT a hierarchy route for us either.** Immediate/highest owner is
  FOUO. `code/67_sam_entity_harvest.py`'s docstring already said this ("**it is
  FOUO, not public** … Do not plan around it until proven"). It is now proven
  from the manual. What IS public and IS already ours: the contract-award file's
  `awardeeUltimateParentUniqueEntityId`, populated on 8,232 of 8,273 rows on the
  TRIBAL slice.
- **What the role WOULD still buy: subawards.** Those are paginated *public*
  data (~2,733 calls for procurement alone) and are genuinely quota-blocked. The
  role request stays worth making — for subawards, not for EIN.

## 3. WHAT THE TEN CALLS BOUGHT — the recall net, sized

`data/raw/external/sam_entity_management/sam_business_type_counts_2026-08-28.csv`,
computed from the saved response bodies, not typed:

| code | business type | SAM registrants |
|---|---|---:|
| `NB` | Native American Owned | **20,798** |
| `OW` | American Indian Owned | **17,962** |
| `XY` | Indian Tribe (Federally Recognized) | 4,014 |
| `1E` | Indian Economic Enterprise | 3,633 |
| `1B` | Tribally Owned Firm | 3,434 |
| `1S` | Indian Small Business Economic Enterprise | 3,167 |
| `05` | Alaskan Native Corporation Owned Firm | 3,111 |
| `8U` | Native Hawaiian Organization Owned Firm | 2,285 |
| `3I` | Tribal Government | 1,635 |
| `HS` | Tribal College | **NOT MEASURED** — 429 |
| `8B` | Housing Authorities Public/Tribal | **NOT MEASURED** — no call left |

**Read these as a RECALL NET, never as a count of Native firms.** Every one is a
self-certification. The first record returned for `05` ("Alaskan Native
Corporation Owned Firm") is *BLOCX LLC, dba BlocX Health* — the owner's position
about these labels arriving on the very first row.

**Three caveats that must travel with these numbers:**

1. **They include INACTIVE registrations.** The `05` sample row is
   `registrationStatus: "Inactive"`, expired 2021-03-27. These are all-time
   registrants, not the active universe. Whether `registrationStatus` filters
   server-side is **unmeasured**.
2. **They overlap heavily and MUST NOT be summed.** `OW` "American Indian Owned"
   and `NB` "Native American Owned" are near-synonyms with no documented
   disambiguation, and the contract-award pull already measured `AMERICAN INDIAN`
   as a strict subset of `INDIAN`. Union, never add.
3. **`businessTypeCode` matching semantics are undocumented.** Every code is
   exactly two characters, so a two-character query cannot substring-match a
   different code — but that was *reasoned*, not measured, and
   `awardeeBusinessTypeName=INDIAN` ($11.1B of Subcontinent-Asian-owned firms)
   is what unanchored matching looks like when nobody checks.

## 4. TWO DEFECTS REPAIRED AT ZERO QUOTA COST

**`Cedar Press/.env.local` carried BOTH documented env-file defects at once** — a
UTF-8 BOM *and* two variables concatenated onto one physical line with no
newline:

    SAM_API_KEY=SAM-<40 chars>COURTLISTENER_API_TOKEN=<40 chars>

Anything doing `startswith("SAM_API_KEY=")` on that file gets a **104-character**
key and a 401 that reads exactly like another rotation — and
`COURTLISTENER_API_TOKEN` is simply unreachable. This is the identical failure
`docs/API_KEYS.md` records being repaired in `dissertation/.env.local` on
2026-08-26; nobody checked Cedar Press's own copy.

Repaired: UTF-8 **without** BOM, one variable per line, backup at
`.env.local.bak_2026-08-28_pre_repair`. `code/434` reads env files with
`utf-8-sig` and **refuses any key that is not exactly 40 characters**, naming
this defect, before spending a call.

## 5. THE TOOL

`code/434_pull_sam_entity_management.py` — **one call per invocation**, by
design. At 10/day an automated loop is a way to lose a day.

    py -3 code/434_pull_sam_entity_management.py status                # 0 calls
    py -3 code/434_pull_sam_entity_management.py get <PATH> k=v ...    # exactly 1
    py -3 code/434_pull_sam_entity_management.py download <URL> <NAME>

It claims `logs/_HOSTLOCK_api.sam.gov.json` and checks the holder is alive before
refusing; **branches on the response body's `error.code`, not the HTTP status**;
stops dead on 429/900804; rejects a non-YES/NO `emailId` pre-flight at zero cost;
substitutes `REPLACE_WITH_API_KEY` on download; writes `.part` then renames; and
**saves every response body to disk** — a truncated console print lost call 1's
body today and that will not happen again.

## 6. NEXT QUOTA WINDOW (after 2026-08-29 00:00 UTC), ranked

1. **`HS` and `8B` counts** (2 calls) — finishes the net. Expect `8B` to be
   mostly non-tribal housing authorities; it is the `TRIBAL`-substring trap in
   its native habitat.
2. **One `format=csv&emailId=YES` extract submission on the largest code**, to
   establish that the entity extract route works for us at all and what its CSV
   header actually contains. Extracts omit all-empty columns — **parse by header
   name, never by index**. 1 call to submit, 1+ to download.
3. **Do not spend calls chasing TIN.** See section 2.
4. **Do not spend calls on Federal Hierarchy** — separate quota regime, 10/day
   for non-federal with no documented role exception, and hierarchy is FOUO.

**Licensing, unchanged:** any registration with `lastUpdateDate` earlier than
2022-04-04 carries D&B Open Data (legal name, street, city, state/province, ZIP,
county, country). Written attribution to D&B is required and **bulk
dissemination is prohibited**. The registration's `evsSource` field names the
validator (`"D&B"` vs `"E&Y"`) and should be carried on every row we keep.
