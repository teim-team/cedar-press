# FAADS pre-FY2007 name attribution

*Built 2026-08-06 by `code/73_faads_name_attribution.py`. Every figure here is
recomputed from `data/clean/faads_attribution_summary.json` or from a recount
of the output files; nothing is hand-entered (standing rule 10).*

## The claim this replaces

`docs/COVERAGE_AUDIT.md` said:

> **Attributable floor: FY2007.** Any per-entity series must start there.
> Pre-2007 rows are retained and support programme-level totals only.

The evidence behind it was correct. Across all 66 pre-2007 agency-years,
`pct_with_duns` is 0.0% with a maximum of 0.0%; of the 1,994,993 rows in
FY2001–FY2006, **65 carry a DUNS and 54 carry a UEI**.

The conclusion was wrong, because it answered a question nobody asked. Elijah
asked the right one: *do those rows have recipient NAMES?* Measured:

| field | populated, FY2001–2006 |
|---|---|
| `recipient_name` | 1,994,948 / 1,994,993 (100.0%) |
| `recipient_type` | 100.0% |
| `recipient_type_description` | 100.0% |
| `recipient_state` | 100.0% |
| `recipient_city` | 84.5% |
| `recipient_zip` | 81.2% |
| `recipient_duns` | 0.003% |

Name-based attribution is what every other dataset in this project already
does. "No identifier" therefore means a **weaker** attribution, not an
impossible one — a tier, not a wall. `docs/COVERAGE_AUDIT.md` now reports two
floors: an identifier floor (tier A) of FY2007, and a name floor (tier B) of
FY2001.

## Result

| | |
|---|---|
| transactions attributed | **29,594** |
| gross obligations | **$4,951,906,323** |
| net of deobligations | **$4,721,685,550** |
| distinct entities reached | **686** |
| fiscal years now covered | **FY2001 – FY2006** |
| distinct recipient names matched | 2,287 |
| confidence tier | **B on all 29,594 rows** |
| state check passed | **29,594 / 29,594** |

**Obligations are signed.** 186,916 rows in the window are negative
deobligations and 2,318 of the attributed rows are. Gross counts positive
obligations only; net subtracts deobligations. The $230.2M gap between the two
is money obligated and then taken back, and any figure quoted from this
dataset must say which of the two it is.

| FY | rows | gross | net of deobligations |
|---|---:|---:|---:|
| 2001 | 5,049 | $807,527,939 | $790,335,923 |
| 2002 | 4,476 | $897,669,773 | $889,602,233 |
| 2003 | 5,662 | $786,666,059 | $627,150,638 |
| 2004 | 4,800 | $769,481,671 | $754,463,384 |
| 2005 | 4,912 | $734,022,166 | $715,950,725 |
| 2006 | 4,695 | $956,538,715 | $944,182,647 |

FY2003 is the year where the distinction bites hardest: $159.5M of
deobligation, 20% of that year's gross.

Entity classes reached:

| class | transactions |
|---|---:|
| Federally recognized tribe | 25,039 |
| Federally recognized Alaska Native Village | 2,149 |
| Federal-level constituency entity | 642 |
| Tribal College or University | 618 |
| Federal-level self-governance consortium | 427 |
| BIE School | 301 |
| Urban Indian Organization | 143 |
| State-recognized tribe | 101 |
| State-level constituency entity | 67 |
| Alaska Native Village Corporation | 48 |
| Alaska Native Regional Corporation | 48 |
| Native Community Development Financial Institution | 11 |

28,823 came from the primary type-`I` pool and 771 from the guarded secondary
pool.

### Spine provenance — read this before comparing runs

The spine grew from **952 to 1,310 entities while this was being built**,
as another agent added Tribal Colleges, BIE Schools, Urban Indian
Organizations and Native CDFIs. That is not a footnote: each new class changed
what the *right answer* is. A tribal college's grant stopped being something to
discard and became something to attribute to the college. The shipped numbers
were produced against:

```
data/spine/cedar_entity_spine.csv   1,310 entities
                                    519 with fr_official_name
                                    mtime 2026-08-06T17:27:15
```

recorded in `faads_attribution_summary.json`. Re-running against a later spine
should reach MORE entities, not fewer.

### Why 29,594 and not 1.99 million

The window's other $1.35 trillion is not missing Native money. Sorted by row
count, `recipient_type` for FY2001–2006 is:

| code | rows | net obligations | description | kept |
|---|---:|---:|---|---|
| A | 599,724 | $711,225,385,049 | STATE GOVERNMENT | |
| P | 376,017 | $321,765,024,989 | INDIVIDUAL | |
| H | 239,326 | $73,975,848,810 | PUBLIC/STATE CONTROLLED INSTITUTION OF HIGHER EDUCATION | |
| M | 166,107 | $54,397,064,340 | NONPROFIT WITH 501C3 IRS STATUS | |
| O | 140,729 | $39,743,713,090 | PRIVATE INSTITUTION OF HIGHER EDUCATION | |
| C | 118,967 | $35,404,132,027 | CITY OR TOWNSHIP GOVERNMENT | |
| D | 111,019 | $48,403,058,842 | SPECIAL DISTRICT GOVERNMENT | |
| Q | 70,586 | $22,654,415,034 | FOR-PROFIT ORGANIZATION (OTHER THAN SMALL BUSINESS) | |
| B | 51,033 | $17,877,517,422 | COUNTY GOVERNMENT | |
| **I** | **40,657** | **$7,333,734,061** | **INDIAN/NATIVE AMERICANTRIBAL GOVERNMENT (FEDERALLY RECOGNIZED)** | **kept** |
| R | 39,856 | $12,173,899,964 | SMALL BUSINESS | |
| G | 29,802 | $5,832,990,043 | INDEPENDENT SCHOOL DISTRICT | |
| X | 11,169 | $4,492,799,351 | OTHER | |
| T | 1 | $31,553 | HISTORICALLY BLACK COLLEGE OR UNIVERSITY | |

`I` is the only tribal category present in this vintage; the modern codes for
tribally designated organisations do not appear. **28,823 of the 40,657
type-`I` rows are attributed, 70.9%; counting the secondary pool, the file
reaches 72.8% of the type-`I` row count.**

## The recipient-type filter, and why the rest is excluded

Before settling on `I` alone, the other twelve codes were tested rather than
assumed. Every distinct non-`I` recipient name was exact-matched against the
spine's canonical names, aliases and Federal Register official names. 266 names
matched exactly one spine entity. Sorted by dollars, the top of that list is:

```
D NV   $48,623,842   WASHOE          -> Washoe Tribe
C MS    $9,263,391   JACKSON         -> a spine tribal entity
D NV    $6,047,440   LAS VEGAS       -> Las Vegas Paiute
D CA    $4,587,916   SANTA ROSA      -> Santa Rosa
D IN    $4,477,285   EVANSVILLE      -> Evansville (Alaska)
D WA    $4,296,023   SPOKANE         -> Spokane Tribe
C TX    $3,185,280   GREENVILLE      -> Greenville Rancheria
C TX    $1,835,803   MARSHALL        -> Marshall (Alaska)
```

Washoe County (a Nevada special district), the City of Jackson, Mississippi and
Clark County's Las Vegas district are not tribes. These are **bare place
names**: the recipient field holds the place and the organisation type lives
only in `recipient_type`. Matching them would have added $203.6M of false
attribution on 1,029 rows.

So the twelve non-`I` codes are excluded before matching. A narrow **secondary
pool** is admitted: a non-`I` row whose name self-identifies as Native
(`tribe`, `tribal`, `indian`, `native`, `pueblo`, `rancheria`, `nation`,
`band of`, `village council`, …) may be matched, but **only on an exact or
alias hit** — never containment. Every disaster above is a bare place name with
no Native token, so the gate excludes them all. The secondary pool contributes
771 transactions, matching things like `ALABAMA-QUASSARTE TRIBAL TOWN`,
`NATIVE VILLAGE OF EKUK` and `SELDOVIA VILLAGE TRIBE` — real tribal
governments miscoded `C` (city) or `D` (special district) by the filer.

## Method

**One resolver.** `resolve_entity` from `code/33_apply_party_rulings.py` is
imported, never re-implemented (standing rule 8). It carries the diacritic
fold, core-set equality, alias lookup, containment matching for the spine's
short names, the narrowed ANCSA corporate-form guard and the word-order
tie-break.

**Full official names.** The spine says "Sleetmute"; federal systems say
"Village of Sleetmute". The spine's `fr_official_name` column (91 FR 4102, on
519 of 1,310 entities) closes that gap. Rather than teach the resolver a second
name column — which would be re-implementing matching — the same resolver runs
twice: once against canonical names, once against a shadow spine whose
`canonical_name` is the Federal Register official name. **The two runs must
agree**; disagreement is refused, not arbitrated. This is what makes `HYDABURG
COOPERATIVE ASSN.`, `KLAWOCK COOPERATIVE ASSOCIATION`, `WRANGELL COOPERATIVE
ASSOCIATION` and `FOREST COUNTY POTAWATOMI COMMUNITY` resolvable at all.

**Match keys.** Each attributed row carries `faads_row_id`, the zero-based row
index into `data/clean/faads_transactions_all_agencies.csv` (2,769,748 rows as
scanned), plus `award_id_fain`, `action_date`, `agency`, `cfda_program` and the
signed `obligated_usd`. The row id is positional and valid for this file
version; the scanned row count is in the summary JSON so a mismatch is
detectable.

### The guards, in order

| # | guard | what it stops |
|---|---|---|
| 0 | documented false positives | `SALT RIVER PROJECT` (the $28.71M scar) and one hand-ruled ambiguous name |
| 1 | recipient-type narrowing | 1,954,336 rows of state governments, individuals, universities, cities |
| 3a | organisation-type bar, hard | cities, school districts, water/power/telephone utilities, conservation districts, local public safety, housing authorities |
| 4 | trap tokens | a name whose only identifying words are on the trap list |
| 5 | the resolver, run twice | everything with no confident spine match |
| 6a | government name on a non-government | `NATIVE VILLAGE OF ELIM` → Elim Native **Corporation**; `TIGUA INDIAN TRIBE` → Tigua Community Development Corporation |
| 6b | organisational-form mismatch | `YUKON KUSKOKWIM HEALTH CORPORATION` → The Kuskokwim Corporation |
| 6f | college ↔ college, both ways | `OGLALA LAKOTA COLLEGE` → the Oglala Sioux Tribe |
| 6g | school name → BIE School only | `FOND DU LAC OJIBWAY SCHOOL` → the Fond du Lac Band |
| 6d | consortium name on a single entity | `INTER-TRIBAL ENV COUNCIL - CHEROKEE` → Cherokee Nation |
| 6e | direction word dropped | `DELAWARE TRIBE OF WESTERN OKLA` → the wrong Delaware |
| 7 | generic one-word entity names | the Alaska village named **Council** absorbing every "council" |
| 9 | entity more specific than recipient | `CHEROKEE NATION OF OKLAHOMA` → United **Keetoowah** Band |
| 3b | organisation-type bar, soft | county/town/borough/cooperative/mining words, unless the entity's own official name carries them |
| 2 | **the state check** | `SAN JUAN PUEBLO` (NM) → San Juan Southern Paiute (AZ) |

**The soft bars are resolved by evidence, not by hunch.** `county`,
`township`, `town`, `borough` and `cooperative` each appear inside the official
name of a real Native government — Forest County Potawatomi Community,
Passamaquoddy Indian Township, Kialegee Tribal Town, and the Klawock, Hydaburg
and Wrangell **Cooperative Associations**, which is the standard IRA-era name
for an Alaska village government. A blanket bar deletes real tribes; an earlier
draft of this script barred Forest County Potawatomi as a "county government".
A soft bar is therefore lifted when the barred word appears in the matched
entity's own canonical or Federal Register name, or when the recipient name
carries an explicit Native token. Otherwise it stands, and it catches `KLAMATH
COUNTY` (OR) → Klamath (OR), which the state guard would not have caught
because both are in Oregon.

**The state guard is hard, and it earns its place.** `recipient_state` is 100%
populated. A name match whose state contradicts the spine's state is REFUSED,
never downgraded, and a spine row with no state cannot confirm anything so it is
refused too. What it caught, all real:

```
AROOSTOCK MICMAC COUNCIL, INC   (ME) -> Council Native Corporation (AK)
INTER TRIBAL COUNCIL OF AZ, INC (AZ) -> Council Native Corporation (AK)
NORTHERN CIRCLE INDIAN H/A      (CA) -> Circle (AK)
MARSHALL ISLANDS                (MH) -> Marshall (AK)
NO. CAROLINA / CHEROKEE NATION  (NC) -> Cherokee Nation (OK)
SEMINOLE NATION JTPA PROGRAMS   (OK) -> Seminole Tribe of Florida
MODOC LASSEN INDIAN HOUSING     (CA) -> Modoc Nation (OK)
UTE MT UTE TRIBE WEEMINUCHE ... (CO) -> Ute Indian Tribe (UT)
ONEIDA TRIBE OF INDIANS OF WI   (WI) -> Oneida (NY)
```

`AROOSTOCK MICMAC COUNCIL` and `INTER TRIBAL COUNCIL OF AZ` are the recorded
"Central Council" trap reproducing on new data, and the state guard is what
stopped them.

It costs real coverage, and that cost is deliberate: `QUECHAN INDIAN TRIBE`
(AZ; the Fort Yuma reservation straddles CA/AZ and the spine says CA),
`PUEBLO OF SAN JUAN` / `SAN JUAN PUEBLO` (NM; the spine's "San Juan" is the
Arizona San Juan Southern Paiute), and multi-state Navajo, Zuni and Standing
Rock rows filed under their non-spine state. 142 groups / 782 rows / $168.2M
net are refused this way, each itemised for a hand ruling.

### Rulings NOT imported, deliberately

`data/spine/federal_funding_rulings_from_dofile.csv` holds 881 exact-name and
92 name-prefix EXCLUDE rulings from `hci_analysis.do`. They were tested against
this pool and **not applied**. They are **scope** exclusions from a lower-48
federally-recognized-tribes-only study, not **ownership** exclusions: the list
drops the whole state of `AK`, the prefix `village of`, and by name Metlakatla,
Kenaitze, Hoonah, Kawerak, Seldovia, Kodiak Area Native Association, South
Puget Intertribal, GLITC, USET, MOWA Choctaw and Haliwa-Saponi — 161 groups /
1,093 rows here. All are real Native entities the Cedar spine deliberately
includes. Applying that list would have deleted "Village of Sleetmute", the
exact case this build exists to capture.

## Refusals

Refusals are a deliverable. `review/faads_attribution_refusals_2026-08-06.csv`
carries 3,669 records accounting for all 1,971,424 unattributed rows in the
window.

| reason | groups | rows | net USD |
|---|---:|---:|---:|
| `recipient_type_not_tribal_government` | 13 | 1,954,336 | $1,347,945,880,515 |
| `no_confident_name_match` | 2,087 | 9,734 | $2,231,885,864 |
| `secondary_pool_requires_exact_match` | 731 | 2,663 | $501,024,552 |
| `organisation_type_bar` | 476 | 1,983 | $616,567,777 |
| `state_mismatch` | 142 | 782 | $168,212,048 |
| `spine_state_unknown` | 63 | 547 | $185,420,693 |
| `trap_token_only` | 32 | 391 | $78,720,309 |
| `entity_more_specific_than_recipient` | 6 | 244 | $155,561,972 |
| `consortium_name_on_single_entity` | 15 | 201 | $24,964,621 |
| `organisational_form_mismatch` | 38 | 177 | $121,656,863 |
| `generic_entity_name_needs_exact_match` | 23 | 170 | $45,833,192 |
| `direction_word_dropped` | 11 | 82 | $4,721,228 |
| `government_name_on_corporation` | 17 | 67 | $5,747,375 |
| `college_entity_mismatch` | 10 | 24 | $3,018,748 |
| `school_name_on_non_school_entity` | 4 | 22 | $4,372,846 |
| `documented_false_positive` | 1 | 1 | $291,538 |

The two most valuable to rule on by hand:

1. **`spine_state_unknown`** — 63 groups / 547 rows / $185.4M. These are
   correct matches to intertribal organisations (Inter-Tribal Council of
   Nevada, ANTHC, Northwest Indian Fisheries Commission, CRITFC, USET, Great
   Lakes Inter-Tribal Council) refused **only** because all 55 `ITO-` spine
   rows have an empty `state`, so the state check cannot pass. Populating
   `state` on those spine rows would recover every one. The spine was not
   modified by this build.

2. **`entity_more_specific_than_recipient`** — the Cherokee family, 244 rows /
   $155.6M. `CHEROKEE NATION OF OKLAHOMA` (132 rows) and `UNITED KEETOOWAH
   BAND OF CHEROKEE` (51 rows) are both refused: with Keetoowah's five-word
   canonical in the spine, set logic genuinely cannot separate them. This is
   the brief's instruction that "cherokee" must never match alone, applied
   without exception. One hand ruling settles both.

`trap_token_only` refuses 32 groups whose entire identifying content is a trap
word, including `CHEROKEE NATION` (81 rows), `SHAWNEE TRIBE` and `CONFEDERATED
TRIBES`.

## Hand audit

**60 distinct (recipient name, state) → entity pairs**, drawn with
`random.seed(60806)` from the 2,295-pair match frame and checked one by one
against the spine's Federal Register official names.

**As found: 3 wrong in 60 — a 5.0% false-positive rate.**

| # | recipient | attributed to | verdict |
|---|---|---|---|
| 4 | `BLACKFEET COMMUNITYCOLLEGE LOCATION: 02` (MT) | Blackfeet (the tribe) | **wrong** — the college, run together as one word, so `\bcollege\b` never fired |
| 43 | `POJOAQUE HOUSING CORP` (NM) | Pueblo of Pojoaque | **wrong** — a housing entity, which this build treats as a separate legal person |
| 58 | `UPPER SIOUX COMMUNITY INDIAN HSG. A` (MN) | Upper Sioux | **wrong** — "HSG. A" is an abbreviated Indian Housing Authority |

The other 57 were correct, including the ones most likely not to be:
`FOREST COUNTY POTAWATOMI COMMUNITY` → Forest County (not a county
government), `COUNCIL OF ATHABASCAN TRIBAL` → the consortium rather than the
Alaska village named Council, `TABLE BLUFF RESERVATION - WIYOT TRIBE` → Wiyot,
`RAMONA BAND OF CAHUILLA` → Ramona, `KANSAS / KICKAPOO TRIBE` → Kickapoo Tribe
in Kansas (not the Oklahoma or Texas Kickapoo), `WINNEBAGO, VILLAGE OF` →
Winnebago, `PAUG-VIK., LTD` → Paug-Vik Incorporated, Ltd.

All three were traced to a mechanism and all three are now refused:

- #4 — the college-name test was anchored with `\bcollege\b`; the source runs
  words together, so the anchor was dropped.
- #43 and #58 — the housing-entity bar matched only `housing auth` / `hsg
  auth`. The source abbreviates and truncates, so the pattern now does too.

After the fixes, none of the three remains attributed, and the correct college
matches (`BLACKFEET COMMUNITY COLLEGE`, `NEBRASKA INDIAN COMMUNITY COLLEGE`)
are preserved.

**The 5.0% as-found figure is the honest headline.** Any post-fix rate measured
on the same 60 would be optimistic, because the fixes were derived from that
sample.

An earlier 60-pair audit, run against the 952-entity spine, found the same rate
— 3 in 60 — and produced guard 9 and the `contractors` form word. Its errors
were `CAHUILLA MISSION INDIANS RAMONA BAND` → Cahuilla (the record names two
tribes), `ILIAMNA LAKE CONTRACTORS` → Iliamna (a construction firm), and
`OKLAHOMA / CHEROKEE NATION` → United Keetoowah Band. All three are refused in
the shipped file.

### Errors found by auditing outside the random sample

Two strata were audited exhaustively rather than sampled, judged highest-risk
in advance: every match landing on an ANCSA corporation, and every match made
only via `fr_official_name`. That found and fixed:

```
NATIVE VILLAGE OF ELIM               -> Elim Native Corporation
NATIVE VILLAGE OF SHISHMAREF         -> Shishmaref Native Corporation
AGDAAQUX TRIBE OF KING COVE          -> King Cove Holdings, LLC
OLD HARBOR TRIBAL COUNCIL            -> Old Harbor Native Corporation
LEISNOI VILLAGE (AKA WOODY ISLAND)   -> Leisnoi, Inc.
COOK INLET TRIBAL COUNCIL, INC       -> Council Native Corporation
CENTRAL CNCL OF ILINGIT & HAIDA ...  -> Haida Corporation
ALASKA SEA OTTER AND STELLER
  SEA LION COMMIS...                 -> Sea Lion Corporation
BRISTOL BAY AREA HEALTH CORPORATION  -> Bristol Bay Native Corporation
SEALASKA HERITAGE FOUNDATION         -> Sealaska Corporation
LOWER KUSKOKWIM SCHOOL DISTRIC       -> The Kuskokwim Corporation
BERING STRAITS REGIONAL HA           -> Bering Straits Native Corporation
DELAWARE TRIBE HSG AUTHORITY         -> Delaware Tribe of Indians
CALIFORNIA / ROUND VALLEY IND HEALTH -> Round Valley
INTER-TRIBAL ENV COUNCIL - CHEROKEE  -> Cherokee Nation
CENTRAL TRIBES OF THE SHAWNEE AREAS  -> Shawnee Tribe
TIGUA INDIAN TRIBE                   -> Tigua Community Development Corp
S'KLALLAM TRIBE                      -> Jamestown S'Klallam Tribal Capital
```

`Sea Lion` and `Central Council` are both scars `AGENTS.md` records by name,
reproducing on new data. The mechanism is structural, not accidental:
**containment matching rewards the shortest spine name that fits, and in Alaska
the shortest name for a place is usually its ANCSA corporation** — the mirror
image of standing rules 2 and 3.

### A guard that was measured and removed

A rule refusing any match that discards a trap word looked obviously right and
lost on measurement: 4 real errors caught, 130 rows of correct matches
destroyed — `MILLE LACS BAND OF OJIBWE` and `LEECH LAKE BAND OF OJIBWE` (the
spine spells it Chippewa, the same people), `COLORADO / UTE MOUNTAIN TRIBE` (a
mangled state prefix on a Colorado tribe), `FORT MCDOWELL MOHAVE APACHE` (the
tribe's former name). Its true catches — `BEAVER CREEK BAND OF PEE DEE` (SC)
onto Beaver (AK), `KOOTENAI RIVER NETWORK` (MT) onto Kootenai (ID) — were every
one of them already refused by the state guard. It was removed; the reasoning
is preserved in the script so it is not re-added.

Guard 9 went the same way in its first form. Unrestricted, "the entity must not
be more specific than the recipient" cost 582 rows to save 190, because this
source truncates names at ~45 characters and `UNITED KEETOOWAH BAND OF
CHEROKEE`, `COLUMBIA RIVER INTER-TRIBAL FISH CO`, `ASSOCIATION OF VILLAGE
COUNCIL` and `KICKAPOO TRIBE OF KANSAS` are all correct matches to a longer
official name. It now fires only when a trap word is present *and* a
shorter-named rival exists.

## Known conservative refusals

Correct matches this build declines to make, each recoverable with a hand
ruling:

- **Tribally designated housing entities** (~200 rows) — chartered apart from
  the tribe under NAHASDA, and the category demonstrably misdirects: `BRISTOL
  BAY HOUSING AUTHORITY` resolves to Bristol Bay Native **Corporation**.
- **Multi-state tribes filed under a non-spine state** (782 rows).
- **Intertribal organisations** (547 rows) — blocked only by empty `state` on
  the `ITO-` spine rows.
- **`COLORADO RIVER INDIAN TRIBES`** and other names whose whole identifying
  content is a trap word.

Tribal colleges and BIE schools are **no longer** refused. They were, while the
spine had no entity for them; now that it holds 37 Tribal Colleges and 185 BIE
Schools, their awards go to the college or school itself — 618 and 301
transactions respectively — which is both more accurate and more useful than
either discarding them or folding them into the tribe.

Tribal executive departments are **not** refused either: `SYCUAN DEPARTMENT OF
PUBLIC SAFETY`, `NAVAJO DEPARTMENT OF LAW ENFORCEMENT` and `CHICKASAW NATION
DIVISION OF HSG` are organs of the tribal government, not separate legal
persons. The `department of` phrase-bar was tested and removed: every
state-agency form in this file (`DEPARTMENT OF NATURAL RESOURCES`, `MONTANA
DEPARTMENT OF NATURAL RESOURCES`, `COLORADO DIVISION OF WILDLIFE`, `GOVERNMENT
OF THE DISTRICT OF COLUMBIA`) already returns `no_spine_match`. The resolver is
the guard there, not the phrase.

## Files

| file | contents |
|---|---|
| `data/clean/faads_entity_attribution.csv` | 29,594 attributed transactions, one row per transaction key |
| `review/faads_attribution_refusals_2026-08-06.csv` | 3,669 refusal records with reason and detail |
| `data/clean/faads_attribution_audit_sample.csv` | 2,287 distinct matched pairs, the hand-audit frame |
| `data/clean/faads_attribution_summary.json` | machine-readable totals and spine provenance, consumed by `code/35_coverage_audit.py` |

## Standing constraints honoured

- **Tier B, never tier A.** A name is not an identifier. `confidence_tier` is
  `B` on all 29,594 rows and `tier_rationale` states why on every one.
- **One resolver** (rule 8) — `33_apply_party_rulings.resolve_entity`,
  imported, not re-implemented.
- **Different legal persons** (rules 2 and 3) — guard 6a is the
  government/corporation split; the corporate-form guard is not applied outside
  Alaska.
- **No DUNS published** (rule 6) — no identifier column is emitted.
- **Recomputed, not hand-edited** (rule 10) — every figure above comes from the
  summary JSON or a recount of the output files.
- `data/spine/`, `data/clean/cedar_*` and `review/cedar_*.html` were not
  modified. `code/00_run_all.py` was not run. No network request was made.
