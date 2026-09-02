# What is missing

*Written 2026-09-01 by workstream `missing`. Every number is produced by
`py -3 code/841_missing_probe.py` (zero network requests; `--json` writes
`docs/WHAT_IS_MISSING.json`). Nothing here was fixed — this workstream is a
read.*

> **The owner's framing:** *"I think the dataset mockup is a good opportunity
> to say what's missing. And I think we have everything on disk if we don't
> download it — besides stuff that's constrained, like SAM, we should be able
> to have a lot more of this stuff."*

**The owner is right, and the measurement is more lopsided than expected.**
Of 39 ranked absences across thirteen datasets:

| label | count | what it costs |
|---|---:|---|
| **ON_DISK_NOT_PROMOTED** | **27** | a column list or a join. No fetch. |
| NOT_ACQUIRED | 6 | a real acquisition task |
| SOURCE_DOES_NOT_PUBLISH | 5 | nothing. A fact about the world. |
| CONSTRAINED | 1 | nothing. Terms forbid it. |

Sixty-nine percent of what a buyer would call missing is already on this
machine. Not one of the 27 needs a download.

One item straddles two buckets and is counted once, under `NOT_ACQUIRED`,
because most of it is: FPDS product/service codes and award descriptions are
**already local for 247,987 of 1,217,768 contracting rows (20.4%)** and a
re-pull for the other 79.6%. See `contractors` #2.

---

## READ THIS FIRST — the sample is a hand-curated column list, and that is where most of the loss happens

`code/770_sample_extracts.py` carries a `SHOW` dict: a per-dataset list of the
columns a sample displays. Everything not listed is dropped **from the sample
only**. The curation is deliberate and mostly right — `gaming_facilities.csv`
has 105 columns and every metric repeats four times as
value/basis/status/date; opening a buyer on that would be worse.

But the same mechanism silently drops the columns a buyer came for. Three
specimens, all measured:

- **`deals` shows no dollar value.** `Announced_Value_USD` is populated on
  **835 of 935 rows** and is not in `SHOW["deals"]`. The product descriptor
  for this dataset promises *"the parties, the instrument and the announced
  value where one was published."* The sample delivers the first two.
- **`lobbying` shows no money.** `spend_reported_usd` is on the table for all
  653 registrants (406 non-zero, **$645.1M** total) and is not in
  `SHOW["lobbying"]`. A lobbying sample with no dollars invites exactly one
  conclusion.
- **`subcontracting` shows no `description`.** Populated on **76,813 of
  76,859** rows — what the subaward was actually for — not in `SHOW`.

There is also a failure mode nobody has recorded: **`SHOW` asks for columns
that then vanish.** Line 215 of 770 drops any requested column that is blank
across all ten sampled rows. `SHOW["native-owned-businesses"]` asks for
`naics` (filled on 34 of 2,393 rows) and `SHOW["federal-register"]` asks for
`format` (180 of 11,402). Both were requested; neither appears in the shipped
sample. **The sample's column set is therefore not stable across rebuilds** —
a different ten rows produces a different schema. A buyer who diffs two
samples will see columns appear and disappear.

---

## THE FOUR THINGS THAT WOULD EMBARRASS US IN FRONT OF A CUSTOMER

Ranked. All four were in the shipped samples when this was written.

> ### STATUS 2026-09-02 — all four are out of the samples, and one is only half fixed
>
> Done by the `codex` workstream, pushed to `cedar-data-samples`:
>
> | # | what shipped | what changed |
> |---|---|---|
> | 1 | nonprofits looked like an unchecked keyword search | `funnel_stage`, `placename_risk_flag` and `canonical_name_token_match` now ship. **The display is fixed; the matcher is not** — see the new measurement below. |
> | 2 | Acoma credited to a school | `cedar_uid` now ships beside `canonical_name`, so the buyer sees the key and not only the label. The correction to the severity claim is in the branch README. |
> | 3 | `0098` as a contract number | `parent_contract_number` now ships first, and clearing it turned up 262,773 rows of literal `nan`. |
> | 4 | six date formats | ISO at 330's write point and applied to the live file by `771`. |
>
> Plus the unrecorded failure mode in the paragraph above: 770 no longer drops
> blank columns, blank ones are named in the sample README, and a `SHOW` entry
> for a column the table does not carry is now a hard `verify` failure. It
> caught a live one within the hour — the nagpra flagship swap to
> `nagpra_notices.csv` left the old `SHOW` list behind and the sample fell to
> four columns.
>
> **The one that is only half fixed is #1.** All 44 rows keyed to
> `Chickahominy Indians-Eastern Division` turn on the token `EASTERN`, and not
> one of them is in Virginia: 40 are Order of the Eastern Star chapters in SD
> and ND, the rest are two ELCA synod bodies, a Meals on Wheels, a university
> seed-stock foundation and an Eastern Star retirement home. **But a blanket
> exclusion of the class would be wrong**, and that is the reason it was not
> applied here: three of the rows carrying that token match are real Native
> organisations keyed to the *wrong* tribe — `WIQUAPAUG EASTERN PEQUOT INDIAN
> TRIBE` (RI), `EASTERN BAND OF CHICKASAW INDIANS FOUNDATION INC` (TN) and
> `EASTERN CHEROKEE SOUTHERN IROQUOIS AND UNITED TRIBES OF SOUTH CAROLINA`
> (SC, already ruled `native_controlled`). Excluding on the token would bury a
> misattribution rather than fix it, and the redirect grammar
> (`elijah_ruling_redirect`) is the correct instrument, not the block. Handed
> to the nonprofits workstream with the 44 rows named.

### 1. The nonprofits sample looks like a keyword search that nobody checked

Ten rows. Four of them are visibly not Native organisations:

```
AARAMBH - INDIAN DANCE SCHOOL INC        Waukesha WI
PEORIA AREA TELUGU ASSOCIATION           Dunlap   IL
PINK POOL LEAGUE OF SIOUX FALLS          Sioux Falls SD
ORDER OF THE EASTERN STAR OF NORTH DAKOTA Fargo   ND
```

Every one reads `classification_ruling = UNRULED`. The product descriptor for
this dataset says place-named non-Native organisations *"are actively
identified and excluded rather than left to inflate the totals."* The sample
is the direct contradiction of the claim printed beside it.

**And the exclusions have in fact happened.** They are just not in the column
the sample chose to show:

| row | `classification_ruling` | `funnel_stage` | `confidence_tier` |
|---|---|---|---|
| PEORIA AREA TELUGU ASSOCIATION | UNRULED | `excluded_by_prior_ruling` | X |
| PINK POOL LEAGUE OF SIOUX FALLS | UNRULED | `excluded_by_prior_ruling` | X |
| FIELD INSTITUTE OF TAOS | UNRULED | `excluded_by_prior_ruling` | X |

**4,651 rows are `excluded_by_prior_ruling` and still read `UNRULED`. 697 are
`verified_strict` and still read `UNRULED`.** The column named
`classification_ruling` carries a ruling for 398 of 12,764 rows (3.1%); the
disposition for the other 96.9% lives in `funnel_stage`, `evidence` and
`placename_risk_flag`, none of which the sample shows. This is the single
worst column choice in the thirteen.

One row here is a **live false positive, not a display problem**: `ORDER OF
THE EASTERN STAR OF NORTH DAKOTA` sits at `funnel_stage =
canonical_name_match` with evidence *"BMF name matched canonical tribe
TRBF-CHCKHE-00 (Chickahominy)"* — matched on the token **EASTERN**, from
*Chickahominy Indian Tribe — Eastern Division*. It is not excluded. 1,831 rows
sit at `canonical_name_match` unruled; this one shows what some fraction of
them are.

### 2. `PUEBLO OF ACOMA (INC)` credited to a school — and the earlier reading of it was wrong in Cedar's favour

Codex found this in the funding sample and measured it at 2,434 rows /
$1.008B. **Traced to the row, the attribution is correct and the display is
not.** All 1,600 Acoma-family rows carry `cedar_uid = CE-0011W-HN`, which the
register resolves to **Pueblo of Acoma**. What is wrong is only the
free-text `canonical_name` column, which carries the alias that won the match
rather than the register's name for the entity the row was assigned to.

This is not confined to Acoma. **341,486 of 548,980 funding rows (62.2%,
$94.4B) have a `canonical_name` that disagrees with the entity register's name
for that row's own `cedar_uid`.** Most are harmless
(`navajo nation tribal government, the` where the register says `Navajo`);
some are the wrong subject entirely (`blackfeet community college` → `Blackfeet`,
`northwest indian college foundation` → `Lummi`). The sample shows
`canonical_name` and hides `cedar_uid`, so the buyer is shown only the
unreliable half of a correctly attributed row.

### 3. Four of ten contracting rows show a "contract number" that is not one

The sample's `contract_number` values include `0098`, `0006`, `0003` and
`SBA0001`. These are FPDS modification PIIDs, meaningless without the
referencing IDV. **`0001` alone appears on 11,700 rows; 290,525 rows (23.9%)
carry a `contract_number` of six characters or fewer.**
`parent_contract_number` is populated on **all 1,217,768 rows** and is not in
the sample. A buyer will treat the first column as a key, and it is not one.

### 4. `certification_expiration` in six different date formats

`native-owned-businesses` ships `04/29/2027` and `4/16/2027` two rows apart.
Across the table, 623 populated values in **six distinct formats**:
`####-##-##` (346), `##/##/####` (144), `#/##/####` (86), `#/#/####` (33),
`##/#/####` (13), `#/##/##` (1). Nothing sorts, nothing parses, and the ISO
plurality belongs to the 346 rows that are `publishable = N` and never ship.
**Every date that reaches a customer is in an un-normalised US format.**

Honourable mention, already known and correctly diagnosed elsewhere: the
gaming sample's `property_status = current` beside `close_date = 2006-04`.
113 of 787 facilities are in that state and every one is factually right. The
sample is where a reader learns that one column cannot say it.

---

# PER DATASET — the three most consequential absences, ranked

---

## `_entity_layer` — `cedar_identity_register.csv`, 1,555 rows, 6 columns shown

**1. The register's `canonical_name` is a colloquial stub, not the entity's legal name.** — `ON_DISK_NOT_PROMOTED`
The sample offers `Little River`, `Table Mountain`, `Pedro Bay`,
`Asa'carsarmiut`. A buyer searching for *Little River Band of Ottawa Indians*
or *Table Mountain Rancheria* finds nothing. **536 register entities have their
legally operative Federal Register name on disk in
`data/clean/federal_recognition_roster.csv`, keyed by `cedar_uid` — and 509 of
the 536 differ from what the register shows.** (`Noatak` → *Native Village of
Noatak*; `Lovelock` → *Lovelock Paiute Tribe of the Lovelock Indian Colony,
Nevada*.) The FR list is the legally operative name and it is one join away.

**2. Two of the six columns shown carry no information at all.** — `ON_DISK_NOT_PROMOTED`
`minted` is `2026-09-01` on **all 1,555 rows** — it records the register
rebuild, not when the entity was minted, so the column means the opposite of
what its name promises. `register_status` is `active` on all 1,555. A third,
`handle` (`AKNF-ACSRMT-00-CALSTA-ASVCPR`), is an internal key no buyer can
read. **Half the sample is noise.** What a buyer wants instead is on disk:
state, identifiers (`cedar_identifier_ledger_final.csv`), parent/child
(`entity_hierarchy.csv`), aliases (`entity_aliases.csv`, 6,298 rows), and
per-entity dataset coverage (`entity_year_coverage.csv`).

**3. No recognition status or date on the row.** — `ON_DISK_NOT_PROMOTED`
Seventeen entity classes are shown with no way to tell a federally recognised
tribe's recognition date, a terminated-and-restored tribe, or a state-only
tribe apart from the class label. `federal_recognition_events.csv` and the
17,058-row roster (1995→) hold it.

*Also true and correctly absent:* the sample README states this dataset's grain
as **UNSTATED**. Three of thirteen datasets do not tell a buyer what one row
is (`_entity_layer`, `native-owned-businesses`, `subcontracting`).

---

## `contractors` — `prime_contracts.csv`, 1,217,768 rows

**1. No NAICS. This is the first column a contracting buyer filters on.** — `ON_DISK_NOT_PROMOTED`
`prime_contracts.csv` has no NAICS column at all; it carries `sector`, the
**2-digit** NAICS prefix. The 6-digit code is already on this machine:
`data/raw/contracts/usaspending_archive_2026-08-07/filtered/FY*_ledger_rows.csv`
holds **904,282 rows and every one of them carries `naics_code`**. The same
files carry `action_date` (the exact award date — the clean table has only
`fiscal_year`), `modification_number`, `award_type` and
`contract_award_unique_key`. `code/114_pull_prime_archive.py` already lists
`naics_code` in `KEEP`; the build simply collapses it to two digits and
discards the rest. **No fetch. A column-mapping change.**

**2. No description of what was bought, and no PSC.** — `NOT_ACQUIRED` **for 79.6% of rows; `ON_DISK_NOT_PROMOTED` for the other 20.4%**
FPDS publishes `prime_award_base_transaction_description`,
`product_or_service_code` and `product_or_service_code_description`. None is in
`KEEP`, so none reached the FY2008–FY2026 archive extract. **But they are
already local for a fifth of the table.** The gapfill zips at
`data/raw/contracts/usaspending_gapfill_2026-08-05/` hold **1,094,582
prime-award rows carrying PSC, award description and NAICS on essentially every
row** (1,094,581 / 1,094,582 / 1,094,581), across **1,041,147 distinct
`contract_award_unique_key`s. Joined through the archive extract's
transaction→award bridge, 247,987 of prime_contracts' 1,217,768 rows (20.4%)
can be given PSC and a description with no download at all.** The remaining
969,781 rows (79.6%) are a genuine re-pull.

That split is measured, not assumed. `code/114_pull_prime_archive.py ::
release()` **deletes each `FY*_All_Contracts_Full_*.zip` after filtering it**,
by design, to keep disk free for concurrent agents — and a filesystem sweep of
this machine on 2026-09-01 found no such file anywhere. The archive route is
live and re-fetchable (url, http_status, bytes, md5 and S3 etag are all
recorded), so this is a re-pull rather than a loss.

**3. The sample shows obligations without the ceiling.** — `ON_DISK_NOT_PROMOTED`
`total_award_value` is populated on **all 1,217,768 rows** and is not in the
sample, so a buyer cannot distinguish a $209 order against a $4B IDIQ from a
$209 contract. Two rows in the ten sampled — ASRC at `$209.20` and Carl Potter
at `$0.00` — are unreadable without it. **265,491 rows (21.8%) obligate $0**;
those are real actions that moved no money, and the sample gives no column
that says so.

*Correctly absent:* pre-FY2000 coverage. Native identification does not exist
in the pre-2000 federal record — `SOURCE_DOES_NOT_PUBLISH`, and the descriptor
already says so.

---

## `funding` — `federal_funding_transactions.csv`, 701,955 rows

**1. The sample gives no joinable entity key.** — `ON_DISK_NOT_PROMOTED`
The only entity column shown is `canonical_name`, lowercase free text, and
inconsistent inside the ten rows themselves (`southern ute indian tribe`,
`Standing Rock`, `Ponca of Nebraska`, one blank). Meanwhile `cedar_uid` is
populated on **552,602 rows (78.7%)** and `recipient_uei` on **668,347 (95.2%)**
— neither is in the sample. Contractors shows `cedar_uid`; funding does not.
See embarrassment #2 above for what the string column does when it is the only
one shown.

**2. Nothing marks a deobligation or a zero.** — `ON_DISK_NOT_PROMOTED`
The first row in the sample is **−$997,895** with no indication that a negative
is a correct deobligation rather than a data error. **43,866 rows are negative
and 99,786 are $0.** `docs/MONEY_TOTALLING_RULES.md` explains it; the sample
does not, and the sample is what gets opened first.

**3. `assistance_type_description` is blank on 4 of 10 rows, and on 299,367 of 701,955 (42.6%).** — `ON_DISK_NOT_PROMOTED`
The coded sibling `assistance_type` is on the table and not in the sample, so a
blank looks like absent data when the code may be present. This is the
difference between a grant, a cooperative agreement and a direct payment — the
distinction the descriptor's method note leads with.

*Structural, and the sample renders it faithfully:* **152,448 rows (21.7%) have
no `canonical_name` at all.** A fifth of "Federal Funding to Indian Country" is
attributed to no named entity, and the sampled `ILIAMNA VILLAGE COUNCIL` row
shows it honestly.

---

## `gaming` — `gaming_facilities.csv`, 787 rows

**1. No revenue — but Cedar has per-facility revenue bounds and does not show them.** — `ON_DISK_NOT_PROMOTED`
Per-facility gross gaming revenue is `SOURCE_DOES_NOT_PUBLISH`: NIGC publishes
regional GGR and revenue bands, never per-operation, and five states seal
per-tribe revenue by statute or compact. **Cedar answered that correctly and
then hid the answer.** `gaming_revenue_bounds.csv` holds **13,803 bound rows
covering 694 of the 787 facilities (88%)**, with lower bound, upper bound,
basis and assumption note. `nigc_regional_ggr.csv` (198 rows),
`nigc_revenue_bands.csv`, `ca_gaming_payments.csv`, `fl_gaming_payments.csv`
and `digital_gaming_revenue.csv` (10,661 rows) are all on disk. The sample and
its README mention none of them. **A buyer's single most likely question has a
good answer and no path to it.**

**2. No gaming class.** — `ON_DISK_NOT_PROMOTED`
Class II versus Class III is the first regulatory fact about a tribal gaming
facility and there is no class column on the facility record.
`gaming_ordinances.csv` carries `class_ii_authorized` / `class_iii_authorized`
for 301 tribes, and **263 of the 284 facility-bearing tribes (93%) have one**.
Tribe-grain, not facility-grain — so it is a stated-caveat join, not a free
one, but it is a join.

**3. `property_status` is blank on 334 of 787 rows (42.4%) and the sample shows ten `current`.** — `ON_DISK_NOT_PROMOTED`
The distribution is `current` 451, **blank 334**, `approved` 1, `closed` 1. A
buyer reading the sample concludes the directory is a live-facility list; it is
57% status-known. Sampling prefers complete rows, which is right for
readability and wrong here — it hides the dataset's largest single gap.
`gaming_property_universe_events.csv` and
`gaming_property_site_observations.csv` hold the evidence for the blanks.

*Two more the sample surfaces well and should keep surfacing:* `open_date` mixes
`1994`, `1998-12` and `2016-10-10` in one column (288 year / 159 month / 188
day / 151 absent) — `open_date_precision` exists on the table and is not shown;
and 62 facilities have no city, with `gaming_property_locations.csv` carrying
county for 1,067 observations and `gaming_facilities` carrying lat/long for 689
but no county.

---

## `legislation` — `bill_votes.csv`, 423 rows

> ### CLOSED 2026-09-02 — items 1 and 2, by `code/890_bill_votes_threshold_and_titles.py`
>
> *Workstream GRAIN-LEGISLATION. Both are now columns on `bill_votes.csv`
> (60 → 68 columns, 423 → 423 rows) and both are in the sample's `SHOW` list.
> The read below is left exactly as written; this box says what changed.*
>
> **Item 1 — `bill_title` and `bill_title_source`.** **398 of 423**, verbatim
> from `native_bills.csv`. `890 verify` refuses any title that is not
> byte-identical to the `native_bills.csv` value it cites.
>
> > **UPDATED 2026-09-02 by `code/1092_bill_titles_residue_and_scope.py`.**
> > This read **390 of 423** with 8 rows at
> > `TITLE_BLANK_IN_native_bills.csv`. **All eight are closed and that
> > category is now 0.** They were not a source gap: every canonical
> > congress.gov bill_type slug in `native_bills.csv` is 100% titled and
> > every NON-canonical slug was 0% (`hre` 0/2, `hjr` 0/1, `treatydoc` 0/2,
> > `treatydocno` 0/3), because `14_pull_cosponsors.py` hard-codes an
> > `ok_types` allow-list that Voteview's `hre`/`hjr` abbreviations fail and
> > treaty documents are not on `/bill` at all. 18 GETs, all HTTP 200 first
> > time. Two treaty identifiers were ambiguous (`TREATYDOC1134`,
> > `TREATYDOC1173` — Voteview writes them with no separator) and were
> > settled by requiring a Senate action on the roll call's own date AND
> > `congressConsidered` equal to the vote's Congress: Treaty Doc. **113-4**
> > (Spain tax protocol) and **117-3** (Finland/Sweden NATO accession).
> >
> > **The honest floor on the remaining 25: 22 are facts about the world.**
> > All 25 carry no `bill_id` and Voteview records no bill number for any of
> > them. 22 are votes on reservations to a resolution of ratification — 17
> > Panama Canal Treaty, 4 Neutrality Treaty, 1 US-UK tax treaty — no bill,
> > therefore no bill title: `SOURCE_DOES_NOT_PUBLISH`. **3 name a numbered
> > measure inside their own question text** (`H100-0888` H.Con.Res. 331,
> > `S100-0452` S.Res. 386, `S100-0417` six S.Res. en bloc) and are
> > `NOT_ACQUIRED` → now **`ON_DISK_NOT_PROMOTED`**: their eight titles are
> > staged at
> > `data/raw/external/congress_gov/1092_title_residue_unlinked.csv` and
> > deliberately not promoted, because promoting one means minting a
> > `bill_id` and a `native_bills.csv` row — a decision for
> > `14_build_bills_votes.py`, not an enrichment.
>
> **Item 2 — `threshold_required`, plus six provenance columns.** Two
> corrections to the read below, both measured:
>
> - **It is sixteen votes, not nine.** The nine named are the House
>   suspensions. The other seven are Senate: five cloture motions rejected at
>   54–58 yea (Rule XXII needs 60), and `S108-0356` and `S114-0351`, which are
>   the interesting pair.
> - **"Derivable from `question`" is true for the House and FALSE for the
>   Senate.** `bill_votes_official_verification.csv` has carried the official
>   threshold since 2026-08-06 and nothing had joined it: `official_vote_type`,
>   from clerk.house.gov (213) and senate.gov (92), on 305 of 423 votes. It is
>   an independent evidence family from `question` (Voteview/ICPSR), so the two
>   can be checked against each other — and they were: **293 agree, 12
>   disagree, all twelve Senate.** Every one is a `3/5` requirement the
>   question string ("On the Motion", "On the Amendment") gives no trace of — a
>   unanimous-consent 60-vote agreement or a Congressional Budget Act point of
>   order. `S108-0356` and `S114-0351` are two of the twelve, which is exactly
>   why a question-only derivation would have left them looking like errors.
>
>   So the official record wins where it exists (305 rows) and the derivation
>   fills in where it does not (118 rows, all predating the electronic record),
>   with `threshold_required_source` saying which on every row and a derived
>   Senate simple majority explicitly labelled a floor.
>
> **All 351 votes with a recorded result now reconcile** — the tally judged
> against `threshold_required` reproduces the recorded result, 351 for 351,
> with 72 NOT_TESTABLE (blank `result`). `890 verify` exits 1 on a single
> failure; `890 selftest` proves all five of its checks fire on synthetic
> violations, including flipping H105-0482 back to a simple majority.
>
> **Item 3 (the party split) is NOT closed** and remains as written below.
>
> ### ADDENDUM 2026-09-02 — `code/1093_bill_votes_majority_anomaly.py`
>
> The sixteen were explained by `threshold_required` and then became
> **invisible**: `result_reconciles_with_threshold` reads `Y` on all 351
> testable rows and `N` on none, so nothing on the row told a buyer WHICH
> sixteen would look like data-entry errors. `bill_votes.csv` 68 → **71**
> columns, 423 → 423 rows:
>
> `result_contradicts_simple_majority` — `MAJORITY_YEA_BUT_REJECTED` **16**,
> `MINORITY_YEA_BUT_AGREED` **0**, `N` 335, `NOT_TESTABLE_NO_RESULT` 72.
> `result_anomaly_class` — `HOUSE_SUSPENSION_TWO_THIRDS` **9**,
> `SENATE_CLOTURE_THREE_FIFTHS` **5**,
> `SENATE_THREE_FIFTHS_NOT_IN_QUESTION_TEXT` **2**. **9 + 5 + 2 = 16.**
> `result_anomaly_basis` carries the rule cited and the arithmetic worked,
> per row.
>
> The classes are derived from ROW PROPERTIES — chamber, `threshold_required`,
> question text, `threshold_agrees_with_official` — never from a list of vote
> ids, so a rebuild that adds a Congress is classified rather than
> mislabelled. **An anomaly outside the three classes, or one whose result
> does not reconcile under the stated threshold, is a refusal to write.** All
> ten checks across `1092` and `1093` were proven to fire against the live
> CSV: inject, assert exit 1 and that the named invariant appears, restore
> from a literal path, assert exit 0.

**1. No bill title. The buyer cannot tell what was voted on.** — `ON_DISK_NOT_PROMOTED`
The sample offers `114-hr-360` and *"On Motion to Suspend the Rules and Pass,
as Amended"*. **`native_bills.csv` holds a title for 390 of the 423 votes
(92%), joinable on `bill_id`.** It also holds `outcome` (196 of 423),
`sponsor`, `policy_area` and `cosponsor_count`. This is the cheapest
high-value join in the thirteen datasets.

**2. Nine votes read `Failed` with more yea than nay, and no column explains why.** — CLOSED; the count was **sixteen**, and "derivable from `question`" is FALSE for the Senate — see the box above
The sample contains one: `H105-0482`, 229 yea to 176 nay, **Failed** — correct,
because suspension of the rules requires two-thirds. There are **nine such rows
in the table** (`H097-0770`, `H099-0529`, `H100-0889`, `H101-0788`, `H105-0482`,
`H105-0568`, `H108-0229`, `H109-1107`, `H112-1442`) and **no
`threshold_required` column exists**. A buyer will file it as a bug. The
threshold is derivable from `question` (87 votes contain "suspend") and belongs
on the row.

**3. The party split is on the table and not in the sample.** — `ON_DISK_NOT_PROMOTED`
`D_yea`, `D_nay`, `R_yea`, `R_nay`, `present`, `not_voting` are populated on
**all 423 rows**, as are `republican_yea_share` and `pro_tribal_is_yea` (240).
For a political-research buyer this is the reason to buy the dataset and the
sample shows a bare tally instead.

*Correctly absent:* member-level votes. `member_positions.csv` exists; whether
it belongs in the product is a scope call, not a gap.

---

## `lobbying` — `lobbying_registrants.csv`, 653 rows

**1. No money in a lobbying sample.** — `ON_DISK_NOT_PROMOTED`
`spend_reported_usd` is on the table for all 653 registrants (406 non-zero,
**$645.1M**), with `spend_sensitivity_percell_max_usd`,
`spend_sensitivity_naive_sum_usd` and `n_filings_reporting_no_dollar` beside it
— the honest treatment of LDA's period-band reporting, and exactly the care a
buyer pays for. None of the four is in the sample.

**2. No issues and no targets.** — `ON_DISK_NOT_PROMOTED`
`issue_codes` (405 registrants), `n_distinct_issue_codes`,
`share_filings_issue_IND_pct` and `government_entities_lobbied` (388) are on the
table. *Who* lobbied *whom* about *what* is the product; the sample shows only
how many times.

**3. Three count columns the buyer cannot tell apart.** — `ON_DISK_NOT_PROMOTED`
`n_filings_native_clients`, `n_native_clients` and
`n_distinct_native_entities` sit side by side, and the last two are **identical
on 631 of 653 rows**. Nothing in the sample says a client is an LDA filing
entity while a Native entity is a Cedar spine entity, or which of the two to
count. `docs/METHODOLOGY_LOBBYING.md` says it; the sample ships without a
column note.

*Worth stating positively:* the descriptor's twenty-channel claim is real —
`native_entity_lobbying_disclosures.csv` (43,963 filing-grain rows with
`income_usd`/`expenses_usd`) and `tribe_year_lobbying_panel.csv` are on disk.
The sample chose the registrant rollup, which is the least buyer-facing of the
three.

---

## `federal-register` — `consultation_events.csv`, 11,402 rows

**1. This is a NAGPRA table wearing a consultation label.** — `NOT_ACQUIRED`
All ten sampled rows are `NAGPRA_consultation_reported`, and that is a fair
draw: **10,888 of 11,402 rows (95.5%)** are. Actual policy consultation is
`consultation_session` 212, `consultation_notice` 180, `listening_session` 37,
`NHPA_section_106` 20, `negotiated_rulemaking` 14 and
**`dear_tribal_leader_letter` 6**. Six Dear Tribal Leader letters across the
whole federal government since 1994 is not the record; DOI alone posts dozens a
year outside the Federal Register. Agency spread says the same:
**Interior 11,068, HHS 99, EPA 43, Commerce 30, Energy 23** — every cabinet
department has an EO 13175 consultation policy. **The federal-register dataset
is READY and its consultation table is 95% one notice type.**

**2. No date and no place for the consultation itself.** — `NOT_ACQUIRED`
`notice_date` is when the notice published. `event_start_date` is filled on
**93 of 11,402 rows** and `location` on **60**. A buyer asking "when and where
is the consultation" cannot be answered for 99.2% of rows. The FR notice text
usually states both; the parse takes the notice metadata and stops.

**3. `participant_role` is an inference and the sample presents it as a fact.** — `ON_DISK_NOT_PROMOTED`
`consulted` (9,110), `invited_did_not_participate` (1,211), `not_enumerated`
(1,006), `invited` (75) — a real and useful distinction, derived from notice
language. The table carries `match_method`, `confidence`, `tier`, `source_url`
and `source_quote`; the sample shows the conclusion and none of the four
columns that support it. `invited_did_not_participate` is a claim about a
named tribe's conduct. It should never ship without its quote.

---

## `nagpra` — sample flagship `fr_nagpra_title_index.csv`, 6,664 rows, 6 columns

**1. The sample opens on the weakest of the four NAGPRA tables.** — `ON_DISK_NOT_PROMOTED`
`FLAGSHIP["nagpra"]` selects the **title index** — a 10-column list of document
numbers and headline strings. The dataset descriptor promises notices *"with
the institutions and affiliated tribes named in each."* Neither is in the
sample. Both are on disk:

| on disk | rows | carries |
|---|---:|---|
| `nagpra_notices.csv` | 6,792 (**67 columns**) | `institution_name` 6,792 · `institution_state` 6,680 · `mni_total_stated` **4,273** · `affiliated_entity_ids` 5,022 · `removal_states` 4,433 · `repatriation_eligible_date` 2,782 · `html_url` 6,792 |
| `nagpra_notice_entity_bridge.csv` | **51,579** | notice→tribe links, **48,111 resolved to a Cedar entity (93%)** |

**The buyer's first question — "which notices name my tribe?" — has 48,111
resolved answers on disk and the sample cannot ask it.** Changing one line of
`FLAGSHIP` is the entire fix.

**2. No institution, no state, no counts in the shown columns.** — `ON_DISK_NOT_PROMOTED`
Everything a NAGPRA buyer needs is buried inside the `title` string: *"Notice
of Inventory Completion: University of California, Riverside, Riverside, CA"*.
Parsed out, keyed, and on disk (above). Shipped as prose.

**3. `relevance_tier_from_tier_rule` is unreadable without the codebook.** — `ON_DISK_NOT_PROMOTED`
`abstract_subject` (4,487), `body_only_unverifiable` (1,245), `title_subject`
(928), `weak_term_only` (4). No buyer can guess whether
`body_only_unverifiable` means "probably irrelevant" or "we could not check".
The `basis` column that explains it is on the table and is not shown.

---

## `native-owned-businesses` — `native_owned_businesses.csv`, 2,393 rows

**1. No indication of what any of these firms do.** — `ON_DISK_NOT_PROMOTED`
`naics` is filled on **34 of 2,393 rows (1.4%)** — which is why it was requested
by `SHOW` and then dropped as all-blank. But `service_category_raw` is filled on
**2,043 rows (85%)** and was never requested. A buyer opening a Native-owned
business directory is looking for a supplier; the sample offers a name, a
certifying nation and a programme title.

**2. No entity key, and no cedar_uid column at all.** — `ON_DISK_NOT_PROMOTED`
`business_entity_id` is filled on **4 of 2,393 rows** and the table has no
`cedar_uid` column, so this dataset cannot be joined to Cedar's contracting,
funding or subcontracting record. The certifying *authority* is keyed
(`certifying_authority_entity_id`); the *business* is not. That is the whole
commercial value of the dataset — "this TERO-certified firm also holds
$X in federal primes" — and it is unreachable.

**3. Certification dates are unusable and the snapshot has no date.** — `ON_DISK_NOT_PROMOTED`
Six date formats (embarrassment #4 above). `certification_start` on **72 of
2,393**, so a buyer cannot tell a new certification from a decade-old one.
`source_last_updated` on **1,127 (47%)** and not shown, so half the directory
has no statement of when the nation last published it — for a list of
certifications that expire, that is the difference between a live register and
a rumour.

*Correctly absent and correctly labelled:* Navajo's NBOA list, Colville, CTUIR
and five others — **346 rows, `TERMS_STATED_RESTRICTIVE`, `publishable = N`** —
are excluded by every route. `CONSTRAINED`, and the sample README names them.
Owner and contact names are withheld as personal data; also correct.

---

## `natural-resources` — `resource_revenue.csv`, 11,305 rows

**1. Eight of the ten sampled rows name no tribe, and that is the dataset, not the sample.** — `SOURCE_DOES_NOT_PUBLISH`
**9,791 of 11,305 rows (86.6%) are `national_aggregate`**; only 779 are
`entity_specific`. Interior suppresses the entity by law on ONRR monthly
revenue, so this is a property of the record and the descriptor says so. **But
the sample is the worst possible presentation of a true fact**: a buyer of
"Tribal Natural Resource Revenue" opens ten rows, sees eight blank recipients,
and closes the file. Either the sample should draw disproportionately from the
1,465 rows that name a recipient, or the README should lead with the 87%.

**2. Almost nothing is keyed to the entity layer.** — `ON_DISK_NOT_PROMOTED`
`cedar_uid` is filled on **119 of 11,305 rows (1.1%)** and
`recipient_entity_id` on 705. Even restricted to the 1,465 rows that name a
recipient, 760 are unkeyed. The descriptor's own blocker admits it (C4, "25% of
entity-bearing rows carry a Cedar id... unresolved work, not scope").
`resource_parties.csv` exists for exactly this.

**3. No volume, no price — revenue with no denominator.** — `SOURCE_DOES_NOT_PUBLISH` *(partly)*
The table has `commodity`, `product` and `amount_usd` but no production volume
and no price. ONRR publishes monthly **production volumes** alongside revenue
in the same NRRD system; they were not pulled. A royalty figure with no volume
cannot distinguish a price collapse from a production collapse — the first
question an energy analyst asks. Volume is `NOT_ACQUIRED` from a source already
in use; unit price is genuinely not published.

*Also:* `period_start` is blank on 492 rows (the whole ND severance series in
the sample included), and `aggregation_level` mixes five grains in one table
with no guard against summing across them.

---

## `nonprofits` — `np_orgs.csv`, 12,764 rows

**1. The ruling column carries no ruling.** — `ON_DISK_NOT_PROMOTED`
See embarrassment #1. **12,366 of 12,764 rows (96.9%) read `UNRULED`**, including
4,651 that are excluded and 697 that are verified. `funnel_stage`, `evidence`,
`placename_risk_flag` (2,401 REVIEW + 1,360 HIGH) and `confidence_tier` carry
the actual disposition and none is in the sample.

**2. No 990 financials beyond one BMF field.** — `ON_DISK_NOT_PROMOTED`
`bmf_revenue_amt` alone, `0` for all 6,453 `990_N` filers (correct — the
e-Postcard reports no financials — but it reads as missing data). Assets,
expenses, programme spend and fiscal year are on disk in `np_financials.csv`,
`np_org_scale.csv` and `np_grantee_financials.csv`. `ntee_code` is on
**9,251 rows (72.5%)** of `np_orgs.csv` itself and is not shown.

**3. Only 1,423 of 12,764 rows (11.1%) carry a `cedar_uid`.** — `ON_DISK_NOT_PROMOTED`
The sample shows the column, blank on 8 of 10 rows, which is a faithful picture
of an 11% link rate. `np_ein_entity_hub.csv` and `np_ein_uei_bridge.csv` exist
to close it.

*Correctly absent and well stated:* tribal instrumentalities largely do not file
990s under IRC §7871, so the largest tribal institutions are absent **by law**.
`SOURCE_DOES_NOT_PUBLISH`, and the descriptor already leads with it.

---

## `subcontracting` — `subawards.csv`, 76,859 rows

**1. `description` — what the subaward bought — is on 76,813 of 76,859 rows and is not in the sample.** — `ON_DISK_NOT_PROMOTED`
99.94% fill on the single most informative column in the table. Also omitted:
`prime_award_id` (100%), `prime_award_amount` (73,057), `source_url` (100%) and
`subaward_to_prime_ratio`. A buyer cannot see what fraction of the prime the
sub represents, which is the whole question in subcontracting.

**2. The grain is UNSTATED, in a table with 18,128 non-primary rows.** — `ON_DISK_NOT_PROMOTED`
`duplicate_status` is `primary` 58,731, `exact_repeat_within_source` 17,282,
`superseded_by_primary_source` 846 — **23.6% of rows are not primary**, and the
sample shows the column with no statement of what one row is.

And the two shipped documents quote the same error two different ways with no
denominator stated. The sample README: *"$45.62B against a correct $24.41B — a
**46.5%** overstatement."* The dataset descriptor: *"summing without that filter
overstates the total by **86.9%**."* Both are arithmetically right —
(45.62−24.41)/45.62 = 46.5%, (45.62−24.41)/24.41 = 86.9% — and neither says
which denominator it used. **A buyer who reads both concludes one of them is
wrong.** `docs/MONEY_TOTALLING_RULES.md` should be the only place the figure
lives, and it should state the base.

**3. Only 33,503 of 76,859 rows (43.6%) carry a `cedar_uid`, and the sample shows a different key.** — `ON_DISK_NOT_PROMOTED`
The sample displays `prime_native_tribe_id` / `sub_native_tribe_id`
(`ANRC-CKINLT-00`) — the legacy handle, not the permanent `cedar_uid` the rest
of the collection joins on. `cedar_uid` is on the table. Showing the retiring
key and hiding the permanent one teaches the buyer the wrong join.

---

## `deals` — `deals_classified.csv`, 935 rows

**1. No dollar value, in the one dataset that exists nowhere else.** — `ON_DISK_NOT_PROMOTED`
`Announced_Value_USD` on **835 of 935 rows (89%)**, `Value_Type` on 935,
`Project_Total_Value_USD` on 139. None is in the sample. The sampled Mohegan
row states *"raising bank credit facility to $500.0 million"* **inside the
title string**, which tells a buyer the value exists and Cedar did not
structure it — the opposite of the truth. The descriptor promises announced
value explicitly. This is the highest-value single-line fix in the report.

**2. No source link, in the dataset whose method note is "every row carries a source link."** — `ON_DISK_NOT_PROMOTED`
`Source_1` on **931 of 935**, `Source_1_Type`, `Source_2`, and
`Verification_Status` / `Confidence` on all 935. The sample shows none of them.
For a hand-built deals ledger competing against nothing, the citation *is* the
product.

**3. `Status`, `Event_Type` and `Record_Scope` overlap, and one is opaque.** — `ON_DISK_NOT_PROMOTED`
Three of the ten shown columns say nearly the same thing: `Event_Type =
Awarded` / `Status = Awarded`, `Event_Type = Signed` / `Status = Signed`.
`Record_Scope` reads `2000 commitment`, `2023 commitment` — it is the year plus
a word, and no buyer will guess it distinguishes commitment-year from
event-year. Meanwhile `Description` (935), `State` (805) and `cedar_uid` (886)
are on the table and not shown. **Three redundant columns are displayed and
three informative ones are not.**

*Also:* 583 of 935 rows are `Awarded` federal grant announcements
(NTIA TBCP, HUD ONAP), and 5 of the 10 sampled rows are. A buyer expecting an
M&A ledger gets a grants list. That is a composition fact worth stating in the
README, not a defect.

---

# THE SHORT LIST — what this week can fix without a single download

Ranked by buyer impact per unit of work. All twelve are `ON_DISK_NOT_PROMOTED`.

| # | dataset | change | evidence on disk |
|---:|---|---|---|
| 1 | `deals` | add `Announced_Value_USD`, `Value_Type`, `Source_1`, `Description`, `cedar_uid` to `SHOW` | 835 / 935 / 931 / 935 / 886 rows |
| 2 | `nagpra` | point `FLAGSHIP` at `nagpra_notices.csv` | 6,792 rows × 67 cols; bridge = 51,579 links |
| 3 | `nonprofits` | show `funnel_stage` + `evidence` beside `classification_ruling`, or populate the ruling | 4,651 excluded rows read UNRULED |
| 4 | `lobbying` | add `spend_reported_usd`, `issue_codes`, `government_entities_lobbied` | $645.1M, 405, 388 |
| 5 | `subcontracting` | add `description`, `prime_award_amount`; swap tribe handle → `cedar_uid` | 76,813 / 73,057 / 33,503 |
| 6 | `gaming` | join `gaming_revenue_bounds` and ordinance class onto the facility | 694 of 787 facilities; 263 of 284 tribes |
| 7 | `legislation` | join `native_bills.title` and `.outcome` on `bill_id` | DONE — 398 of 423 titles (was 390; `code/890` made the join, `code/1092` closed the last 8) |
| 8 | `contractors` | promote 6-digit `naics_code` + `action_date` from the archive extract | 904,282 rows already local |
| 9 | `funding` | add `cedar_uid` and `recipient_uei`; rebuild `canonical_name` from the register | 552,602 / 668,347; 341,486 drifted |
| 10 | `_entity_layer` | swap `minted`/`register_status` for the FR legal name and state | 536 legal names, 509 differ |
| 11 | `contractors` | add `parent_contract_number` and `total_award_value` | both 100% filled |
| 12 | `native-owned-businesses` | show `service_category_raw`; normalise dates to ISO | 2,043 rows; 6 formats |
| 13 | `contractors` | join local gapfill PSC + award description through the archive bridge | 247,987 rows reachable, 0 downloads |

**What is a real acquisition task (6):** non-NAGPRA tribal consultation across
the cabinet departments; consultation event dates and locations; FPDS
`product_or_service_code` and award description **for the 79.6% of contracting
rows not reachable locally**; ONRR production volumes; a `threshold_required`
derivation for the nine anomalous votes; `certification_start` for the TERO
directories.

**What is not our problem (6):** per-facility gaming revenue; pre-2000 Native
identification in FPDS; §7871 tribal instrumentalities absent from the 990
corpus; entity-suppressed ONRR aggregates; unit resource prices; the 346
restrictive-terms business rows.

---

## Method and limits

- Every count above is from `code/841_missing_probe.py`, run 2026-09-01 against
  `data/clean/`, `data/spine/` and `data/raw/`. No network requests. Re-run it
  before quoting any figure — nine agents are live on this tree.
- **Nothing was checked against a source website.** Where this document says a
  source does or does not publish a field, it is from the existing build logs
  and from the raw extracts on disk, not from a fresh look at the publisher. The
  claims about ONRR production volumes and FPDS PSC are grounded in raw column
  lists already local (`contracts_w1.zip`, 286 columns); the claim about DOI
  Dear Tribal Leader letters is an inference from a count of 6 and is the
  weakest assertion in this document.
- **One `NOT_ACQUIRED` label survived a challenge and one was corrected.** A
  filesystem sweep for `FY*_All_Contracts_Full*` returned nothing, confirming
  that `114_pull_prime_archive.py :: release()` deletes each archive zip after
  filtering — so FPDS PSC and award description genuinely require a re-pull.
  Measuring the local gapfill zips against that conclusion then showed **20.4%
  of the table is reachable without one**, and the label was split rather than
  left whole. Both halves are in `probe_psc_reach()`.
- The sample draws ten rows preferring complete ones and spreading across the
  file. That is right for readability and it systematically **understates blank
  rates** — `gaming.property_status` (42% blank) and `nonprofits.cedar_uid` (89%
  blank) are the two places it matters most.
- This workstream fixed nothing and touched no table. `docs/WHAT_IS_MISSING.md`,
  `docs/WHAT_IS_MISSING.json` and `code/841_missing_probe.py` are its only
  outputs.
