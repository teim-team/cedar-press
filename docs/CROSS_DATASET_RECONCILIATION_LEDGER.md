# Cross-dataset reconciliation ledger

*Written 2026-09-02 by the cross-dataset agent. Every number is re-measured from
the live files by two scripts, and both refuse to agree with a stale figure:*

```
py -3 code/1010_ownership_change_from_contracting.py measure | verify | selftest
py -3 code/1011_cross_dataset_reconciliation.py            measure | verify | selftest
```

`verify` exits 1 when a recorded invariant stops being true; both were proved to
fire on a tampered invariant and on a synthetic violation before this file was
written. **Neither script repairs another dataset's table.** Where a finding
belongs to somebody else it is written down with the identifier and the count so
that owner can act.

**A reproducibility note.** `prime_contracts.csv` was rewritten during this
session by `871_promote_geo_keys_contracts` — 56 columns to 70, 1.20 GB to
1.43 GB, row count unchanged at 1,217,768. Every figure below was re-measured
against the 70-column vintage and both `verify` runs pass on it. If the file
moves again, re-run `measure`; a stale figure will fail `verify` rather than
survive into prose.

This file answers two questions the owner asked as one:

> *"If we see a deal that's published, we should see the federal contracting
> company change owners. Or if we see the federal contracting company change
> owners, that's not something publicly available — it's a deal we can report."*

---

## Part 1 — ownership changes visible only in contracting

### What was scanned

`prime_contracts.csv`, 1,217,768 rows, 12,491 distinct awardee UEIs, FY2000–2026.
For every UEI, the DECLARED PARENT in each fiscal year; a year counts as
declaring one parent only when that parent holds ≥80% of the year's rows over
≥2 rows. A UEI qualifies as a transition only when its parent runs are
**strictly time-ordered and disjoint** — if parent A reappears after parent B the
declaration is oscillating, which is FPDS inconsistency and not an event.

That leaves **780 parent transitions**. Then the discipline.

### 682 of 780 were REJECTED as relabelling, and that is the headline

The owner's warning was explicit — *"a company changes from, like, All Native
Group to Ho-Chunk Inc, but it's still the same Native entity"* — and it is what
most of this signal is:

| refusal | n | worked example |
|---|---:|---|
| `INTRA_FAMILY_SAME_HUB` | 416 | `AGVIQ LLC`: Tikigaq Corporation → AGVIQ LLC. Both resolve to `ANVC-TIKIGA-00` |
| `SAME_NAME_REREGISTRATION` | 211 | `AFFIGENT, LLC`: `NANA REGIONAL CORPORATION INC` → `NANA REGIONAL CORPORATION INC.` → `NANA REGIONAL CORPORATION, INC` — three SAM registrations of one company, three UEIs, no transaction |
| `INTRA_FAMILY_SHARED_BRAND` | 29 | `ALEUT CONSTRUCTION LLC`: The Aleut Corporation → Aleut Information Technology, on the token `aleut` |
| `INTRA_FAMILY_ACRONYM` | 24 | `BOWHEAD BUSINESS AND TECHNOLOGY SOLUTIONS`: UIC Government Services → Ukpeaġvik Iñupiat Corporation. `UIC` is a recorded acronym alias of `ANVC-KPVKPT-00` |
| `NAN_SENTINEL` | 2 | `Petro Star Inc` → `NATIVE VILLAGE OF TYONEK`, joined through the literal string `NAN` in `parent_uei` |

**Why the two token-level refusals are legitimate here and would not be as
matchers.** `ENTITY_MATCH_RULES` rule 7: *"a bare token may never AWARD a match,
but it may always BLOCK one."* SHARED_BRAND and ACRONYM only ever suppress a
report. A wrong refusal costs a missed story; a wrong report invents a
transaction.

The self-test proves the refusal fires on exactly the case the owner named: a
synthetic `All Native Group → Ho-Chunk, Inc.` transition is rejected on
`TRBF-WNNBGO-00`, and a genuine `Corvid Holdings → Chickasaw Nation` transition
is not.

### 98 survived. 97 are not in Cedar's deal ledger

Of the 98, **72 have a Native side** and **71 of those are unrecorded**. The
single match is `ENVIRONMENTAL QUALITY MANAGEMENT, INC` → `ANCSA-2019-004`.

Matching against the deal ledger is deliberately strict: only rows whose
category is itself an ownership change (217 of 935 in `deals_classified.csv`,
plus all 98 rows of `ownership_events.csv`), and the deal row must
contain the company's whole distinctive name as a **contiguous token run**. A
set-intersection version matched `Rnb Technologies → Oasis Systems` to an
unrelated ANCSA acquisition on the token `systems`. The window is ±5 years
because the declaration lags the transaction — `North Wind Group acquires LBYD
Engineers` is dated 2020 and LBYD's FPDS parent did not become Cook Inlet Region
until FY2025.

### The leads, ranked by prime obligations on the firm

Full file: `review/1010_ownership_change_candidates.csv`. These are the
unannounced ones with a Native side and no mis-filing caution. **A candidate is
a LEAD, not a finding** — rungs 2–5 of `ENTITY_MATCH_RULES` rule 13 (the website,
the address, the news article) are a human's job.

| child UEI | firm | declared parent, through | declared parent, from | direction | firm prime obligations |
|---|---|---|---|---|---:|
| `FGELS2KFR825` | AMEE BAY, LLC | itself, FY2015 | OLD HARBOR NATIVE CORPORATION `K3N7G5L6GRY6`, FY2016 | acquired into a parent | $245,043,291 |
| `RXF9DDWVMGF5` | SEVEN GENERATIONS ARCHITECTURE & ENGINEERING | MNO-BMADSEN `LDNUFQ3NZN94`, FY2023 | itself, FY2024 | spun out | $240,299,784 |
| `ULBJLGWUNXK1` | CREATIVE APPAREL ASSOCIATES, LLC | itself, FY2013 | INDIAN TOWNSHIP HEALTH CENTRE `E199HJW7RFF8`, FY2014 | acquired into a parent | $216,560,956 |
| `K7MPSQUS6XC3` | EAGLE HEALTH, LLC | itself, FY2023 | CAPE FOX CORPORATION `NHLYBKJK2GP3`, FY2025 | acquired into a parent | $180,710,169 |
| `GMHWR9QF3AJ6` | Gsi Pacific Inc. | itself, FY2015 | NATIVE HAWAIIAN COMMUNITY DEVELOPMENT CORP `F8VLWK5HJGJ5`, FY2016 | acquired into a parent | $158,172,309 |
| `Y1JWKAY431U5` | AQUATE CORPORATION | ALABAMA-QUASSARTE ECONOMIC DEVELOPMENT AUTHORITY FOUNDATION `JYN3U8N9V517`, FY2012 | itself, FY2013 | spun out | $157,243,009 |
| `EHM2NWLJHSJ7` | GSI NORTH AMERICA INC | NATIVE HAWAIIAN COMMUNITY DEVELOPMENT CORP `F8VLWK5HJGJ5`, FY2023 | itself, FY2025 | spun out | $134,295,731 |
| `WNUXNEJ347B7` | Dawson Federal, Inc. | itself, FY2015 | Hawaiian Native Corporation `VCT5JU1AYDQ9`, FY2016 | acquired into a parent | $133,822,155 |
| `NM8KVK8HGZY6` | Nisga'A Data Systems Llc | itself, FY2013 | GOLDBELT, INCORPORATED `P9QQX7RT8E98`, FY2015 | acquired into a parent | $132,425,608 |
| `KQNYKJCTWEC8` | BSET, LLC | TANADGUSIX CORPORATION `JTT1TMUBS2N5`, FY2023 | itself, FY2025 | spun out | $122,481,108 |
| `HE6SK5L289W4` | SAXMAN ONE, LLC | itself, FY2023 | CAPE FOX CORPORATION `NHLYBKJK2GP3`, FY2024 | acquired into a parent | $95,087,613 |
| `LVQCMPXYEG79` | MIAMI WIIPICA, LLC | MIAMI NATION ENTERPRISES `QCRWNAD3L6A8`, FY2023 | itself, FY2024 | spun out | $87,104,762 |
| `QSH2MX6G3YM3` | SMI INTERNATIONAL, LLC | NANA REGIONAL CORPORATION `KW9NCQ8W64S4`, FY2010 | THE ALEUT CORPORATION `M5H7HESFYJL5`, FY2014 | moved between Native families | $86,883,043 |
| `WSTJJH9KLGS3` | Dawson Technical Llc | itself, FY2015 | Hawaiian Native Corporation `VCT5JU1AYDQ9`, FY2016 | acquired into a parent | $75,836,069 |
| `RNREKG196UC3` | ECHOTA TECHNOLOGIES CORPORATION | itself, FY2012 | OSAGE, LLC `LPXYYU21LJS3`, FY2014 | acquired into a parent | $60,958,434 |
| `GLWHK5VNPT63` | YUKON MANAGEMENT, LLC | itself, FY2024 | GANA-A' YOO, LIMITED `K3KWSY8WY8L5`, FY2026 | acquired into a parent | $55,971,065 |
| `JE6LL9BHJBB4` | LIFESOURCE BIOMEDICAL, LLC | itself, FY2014 | GOLDBELT, INCORPORATED `P9QQX7RT8E98`, FY2015 | acquired into a parent | $54,465,346 |
| `FE4QVTUAN3R5` | B & H Contracting Company Inc | itself, FY2019 | Hawaiian Native Corporation `VCT5JU1AYDQ9`, FY2020 | acquired into a parent | $53,990,589 |
| `VBZBJQQNKT96` | SECURITY ALLIANCE LLC | itself, FY2022 | SEALASKA CORPORATION `XMKLMV8GCWJ5`, FY2023 | acquired into a parent | $53,164,079 |
| `FEX9L6Z5RXX5` | Ntvi Enterprises, Llc | itself, FY2013 | Northern Taiga Ventures Inc. `LELBHQ88UMK9`, FY2015 | acquired into a parent | $42,956,648 |

Two more that are worth a look and sit lower on dollars:

- `DD7KTEMDG6A5` **CORVID TECHNOLOGIES, LLC** — Corvid Technologies `VUBTVT9ADBD1` FY2023–24 → **CHICKASAW NATION** `KS8HLVMJEMW9` FY2025–26. The
  deal ledger's only Chickasaw/Corvid row is `ND-2019-001`, a different
  transaction (Rocus Networks).
- `R3GMNTDL7356` **S & T SERVICES, LLC** — Tikigaq Corporation FY2005–2010 →
  **CEDAR BAND OF PAIUTES** FY2011–2023. An Alaska village corporation's firm
  appearing under a Utah band, and it stuck for thirteen years.

Two divestitures **out** of Native ownership, neither in the ledger:

- `PTJATEQ7Q873` **WHPACIFIC, INC.** — NANA Regional Corporation FY2008–2019 →
  **NV5 GLOBAL, INC.** `HK7JHMM3TG85` FY2020–2024.
- `F2BEQJNKFY83` **CLARUS FLUID INTELLIGENCE, LLC** — Koniag, Inc. FY2008–2017 →
  CHESTNUT PARK FY2019–20 → RELADYNE, INC. FY2021–24.

### 22 candidates carry an explicit caution, and one class is not a deal at all

Where the CHILD's own name shares a distinctive token with only ONE of the two
parents, the other declaration is as likely a mis-filing as an ownership fact.
Four firms — `ALEUT FACILITIES SUPPORT SERVICES, LLC` `Q5VGLSJYBGQ8`,
`ALEUT GLOBAL SOLUTIONS, LLC` `Y7KZVN5B74Q7`, `ALEUT TECHNOLOGIES, LLC`
`ECHJVVDGGDL6` and `ALEUT VENTURES LLC` `N3T3ZMGMJ143` — all declare **NANA
Regional Corporation** through FY2010 and **The Aleut Corporation** from FY2011
or FY2012, $692,701,356 between them. Four Aleut-named companies do not move
from NANA to Aleut in the same year; the likelier reading is that the earlier
filings were wrong. Each such row carries `interpretation_caution` naming the
shared token, and 42 of the 98 candidates carry a caution of some kind.

### The reverse direction: does a published deal show up in contracting?

`review/1010_announced_deals_vs_contracting.csv`. Of the 217 ownership-type rows
in `deals_classified.csv` and `ownership_events.csv`:

| verdict | n | reading |
|---|---:|---|
| `TARGET_NOT_A_FEDERAL_PRIME` | 159 | expected — most of this ledger is casinos, hotels, land and broadband |
| `TARGET_NOT_NAMED_IN_TITLE` | 29 | the title has no transaction verb, so no target could be isolated |
| `NO_PARENT_CHANGE_IN_FPDS` | 21 | the target IS a prime, kept filing, and never changed its declared parent |
| `CONFIRMED_BY_CONTRACTING` | 8 | both datasets agree |

**8 of 29 testable announced deals leave a trace in FPDS.** That is the
empirical answer to the owner's first sentence, and it cuts in Cedar's favour:
FPDS does not update retroactively, so for 21 published acquisitions —
`Chickasaw Nation Industries acquires Washington Business Dynamics`, `Bristol Bay
Native Corporation acquires Central Environmental`, `Akima, LLC agrees to
acquire Pinnacle Solutions` — **the deal ledger is the only ownership record
that exists.** That is the moat AGENTS.md describes, measured.

---

## Part 2 — where the datasets disagree

Full findings: `review/1011_cross_dataset_findings.csv` (12) with 1,509 instance
rows in `review/1011_cross_dataset_finding_rows.csv`. Ranked by embarrassment
first and dollars second, because a $0 finding that makes a published claim
false outranks a large one that is merely incomplete.

**No figure below may be added to any other figure.** Every dollar is a REACH
measure — how much already-published money sits behind a defect — and the prime
obligations quoted are the same dollars `prime_contracts.csv` already publishes.

### CDR-11 · HIGHEST · $38,191,057,346 — three quarantined methods are still load-bearing

`docs/CROSS_DATASET_LEARNING.md` states the rule: *"a discredited method taints
its output wherever it landed. Quarantined: cluster_v3, need_v6,
sam_namematch_2026_05_06."*

**2,142 UEI rows of `cedar_identifier_ledger_final.csv` still carry one of those
three as `attribution_method`, and 0 of them carry an `exclusion_id`.** They key
172,338 rows of `prime_contracts.csv` worth $38.19B. Two risk slices inside it:

- **183 firm/hub pairs, $7,668,984,930**, share **no** distinctive token with the
  hub they are keyed to;
- **189 pairs, $5,065,062,423**, share only a token that is already on
  `cedar_domain.NAME_TRAPS`.

The worst individually:

| firm | UEI | keyed to | tier | prime obligations |
|---|---|---|---|---:|
| GENERAL DYNAMICS INFORMATION TECHNOLOGY, INC. | `L2RLDSEQJ5M1` | Barrow `AKNF-INPTBW-00-ARCSLO` | B | $3,533,754,913 |
| BLUE TECH INC. | `MDC5LDZKQAM4` | Blue Lake `TRBF-BLULKE-00` | B | $3,505,660,429 |
| PERATON GOVERNMENT COMMUNICATIONS INC. | `KLQZPHMGKK23` | Barrow | B | $1,686,751,008 |
| IDS INTERNATIONAL, LLC | `C4CPAY4AL545` | Barrow | B | $1,080,762,008 |
| EAGLE HARBOR, LLC | `KYNNE53LWS99` | Eagle `AKNF-VEAGLE-00-…` on the trap token `eagle` | B | $634,718,125 |
| AMERICAN EAGLE PROTECTIVE SERVICES CORP | `TT6AZ3TPBVW3` | Eagle, on `eagle` | B | $445,552,368 |

The ledger row for the first one reads, verbatim:

```
UEI,L2RLDSEQJ5M1,AKNF-INPTBW-00-ARCSLO,Barrow,Computer Sciences Corporation,
Federally recognized Alaska Native Village,cluster_v3,B,
"Algorithmic name clustering, unreviewed"
```

**And the quarantine is invisible downstream.**
`prime_contracts.attribution_method` reads `uei_exact` on every one of these
rows, because that column records **how the identifier joined**, not **how the
identifier was ruled**. A row keyed through "algorithmic name clustering,
unreviewed" is indistinguishable in the contracting table from a row keyed
through an Elijah ruling. Carrying the ledger's own `attribution_method` and
`confidence_tier` through the join would make the quarantine visible and costs
two columns.

> Owner: contracting + identity layer. **Not repaired here.** The instances are
> listed in `review/1011_cross_dataset_finding_rows.csv` under `CDR-11`.

### CDR-12 · HIGHEST · $575,844,567 — one corporate family, four nations, and Cedar settles it itself

`North Wind` / `LBYD` in `prime_contracts.csv`:

| hub | rows | UEIs | obligations | how those UEIs were keyed |
|---|---:|---:|---:|---|
| Cook Inlet Region `ANRC-CKINLT-00` | 7,149 | 24 | $2,220,343,149 | `agent_research_two_leg` |
| **Eastern Shoshone `TRBF-ESWNDR-00`** | **1,242** | **16** | **$537,610,729** | **`cluster_v3`, all of them** |
| **Lumbee `TRBF-LUMBEE-00`** | **32** | **6** | **$38,228,967** | **not in the identifier ledger at all** |
| Nelson Lagoon `AKNF-NLSONL-00-…` | 1 | 1 | $4,871 | `cluster_v3` |

`NORTH WIND CONSTRUCTION SERVICES, LLC` appears on **both** sides under
different UEIs. The Eastern Shoshone reading rests on the token `wind`, which is
on `cedar_domain.NAME_TRAPS`, and Cedar's own deal ledger contradicts it twice:

- `ANCSA2-2017-003` — *"CIRI through its subsidiary North Wind purchased Portage
  and its subsidiaries"*
- `MA2020-004` — *"North Wind Group acquires LBYD Engineers"*

Note what is **not** claimed: `WIND RIVER CONSTRUCTION LLC` ($14,592,180) is
excluded from the figure above and may genuinely be Eastern Shoshone — Wind
River is their reservation, which is precisely why the token is a trap.

> Owner: identity layer. The fix is a ruling on 16 UEIs, not a rebuild.

### CDR-06 · HIGHEST · $87,626,820,925 — a repair that is recorded as done and is 65% undone

`prime_contracts.csv` — re-measured on the 70-column vintage written by
`871_promote_geo_keys_contracts` — still holds the literal three-character
string `nan` in **617,097 cells**:

| column | cells | share of rows |
|---|---:|---:|
| `cage_code` | 398,840 | 32.75% |
| `place_of_perform_city` | 88,269 | 7.25% |
| `place_of_perform_state` | 87,068 | 7.15% |
| `funding_agency` | 33,263 | 2.73% |
| `extent_competed` | 9,411 | 0.77% |
| `recipient_state_code` | 202 | 0.02% |
| `parent_uei` | 22 | 0.00% |
| `recipient_city_name` | 22 | 0.00% |

`code/772_strip_nan_sentinels.py` documents 953,785 such cells across twelve
columns and a backup named **`prime_contracts.bak_2026-09-02_011205_pre772.csv`**
sits beside the live file — so the repair reads as applied. It was applied to
one column. `parent_contract_number`, which `772`'s own docstring measures at
262,773 sentinel cells, now measures **0**. Every other column `772` names still
measures at or near the figure in that docstring. `award_type` (71,134) and
`naics_code` (2,773) are also clear; the 617,097 above is what is left.

Why this is the worst one on the list: `ENTITY_MATCH_RULES` rule 4 already warns
that this exact sentinel in `fpds_uei_cage_map.csv` (2,196 rows, 2,193 UEIs)
will *"fuse 2,193 unrelated entities"* on a CAGE join. In `prime_contracts.csv`
the same sentinel now sits on **2,015 distinct awardee UEIs across 411 Cedar
hubs carrying $87.63B**. And the two `parent_uei` sentinels already fuse
`Petro Star Inc` (ASRC) with `NATIVE VILLAGE OF TYONEK`.

> Owner: whoever holds `772`. Running `write` on the remaining columns is the
> whole fix. **Not run here** — `772`'s own docstring records that a whole-file
> rewrite firing while another builder holds the file is how a run gets lost.

### CDR-02 · HIGH · $175,604,584,174 — the ranked contractors are strangers to the entity layer

**1,343 of 1,379** operating companies in `contractor_ranking.csv` that are
distinct from their owner are named nowhere in `entity_relationships.csv` or
`cedar_constellation_edges.csv`. Top of the list: `Tkc Integration Services Llc`
($4.12B, NANA), `Petro Star, Inc.` ($3.60B, ASRC), `DEFENSE SYSTEMS AND
SOLUTIONS` ($3.27B, Calista), `Tribalco, Llc` ($2.48B, Houlton Band of
Maliseet).

`contractor_ranking.csv` is a published product. Its firm column is exactly the
thing the relationship graph cannot corroborate.

### CDR-01 · HIGH · $0 — the typed ownership graph has no joinable subject

`entity_relationships.csv` is named in AGENTS.md as *"the source of truth"* for
ownership, replacing `entity_hierarchy.csv`. Measured:

| relationship_type | rows | source blank | target blank |
|---|---:|---|---|
| `owned_by` | 1,462 | **all 1,462** | — |
| `brand_of` | 106 | **all 106** | — |
| `affiliated_with` | 148 | 7 | **all 148** |
| `operated_by` | 56 | — | **all 56** |
| `associated_with_region` | 391 | — | — |
| `village_corporation_for` | 77 | — | — |
| `chartered_by` | 30 | — | — |
| `constituent_band_of` | 22 | — | — |

**1,772 of 2,292 edges (77.3%) have a blank endpoint.** On `owned_by` the owned
firm exists only inside the free-text `notes` column — *"firm 'Tkc Integration
Services Llc,' (UEI M46UYYHVH4B1) is owned by this Native entity directly"*.
**996 of the 1,462 recover a UEI from that prose; 466 recover nothing.**

A buyer cannot answer *"which firms does NANA own"* from this file without
parsing English. Promoting the prose UEI into `source_entity_id` closes 68% of
it immediately.

### CDR-03 · HIGH · $84,515,855,455 — the ledger cannot resolve the parents FPDS names

**287 of 847** non-self `parent_uei` values in `prime_contracts.csv` sit above at
least one Cedar-attributed child and have **no row** in
`cedar_identifier_ledger_final.csv`. They are not obscure:

| parent UEI | name | children | obligations on those children |
|---|---|---:|---:|
| `KW9NCQ8W64S4` | NANA REGIONAL CORPORATION INC | 65 | $14,923,276,084 |
| `L2YMLW7SK3K8` | CHUGACH ALASKA CORPORATION | 22 | $10,777,675,004 |
| `RQ13XQQKKQ67` | AFOGNAK NATIVE CORP | 60 | $8,774,818,346 |
| `ZHEGXL9HYV43` | THE CHENEGA CORPORATION | 52 | $8,598,427,650 |
| `PQUEL5MZFDJ3` | BRISTOL BAY NATIVE CORPORATION | 49 | $4,002,462,062 |
| `DRDKNY4L1T33` | KONIAG, INC. | 24 | $3,325,477,705 |
| `S2SVA1GNRVK5` | COOK INLET REGION INC | 33 | $2,313,721,635 |

The ledger holds dozens of *other* UEIs for each of these corporations. What it
does not hold is the registration FPDS itself points at, which is the one a
consumer following the parent link will land on.

### CDR-04 · HIGH · $39,099,757 — lobbying clients the spine already names

**57 of 515** rows in `lobbying_unmatched_clients.csv` resolve to **exactly one**
spine entity on an exact whole-name match against `canonical_name`,
`fr_official_name` or a recorded alias. No containment, no token match. The
commonest recorded reason for the miss is `no_alias_hit`.

| client | spend | filings | resolves to |
|---|---:|---:|---|
| NATIONAL INDIAN GAMING ASSOCIATION | $10,764,000 | 303 | `ITO-GAMING-00` |
| NATIONAL AMERICAN INDIAN HOUSING COUNCIL | $5,337,219 | 185 | `ITO-HOUSIN-00` |
| UTE INDIAN TRIBE | $4,704,475 | 118 | `TRBF-UNTHOR-00` |
| KAMEHAMEHA SCHOOLS | $2,586,500 | 67 | `NHO-KMHMHS-00` |
| SOUTHERN CALIFORNIA TRIBAL CHAIRMEN'S ASSOCIATION | $2,200,000 | 64 | `ITO-STHRNC-00` |
| ALASKA NATIVE TRIBAL HEALTH CONSORTIUM | $1,676,250 | 160 | `ITO-LSKHLT-00` |
| ALASKA FEDERATION OF NATIVES | $1,490,000 | 97 | `ITO-LSKFDR-00` |

All 57 are in `review/1011_cross_dataset_finding_rows.csv` under `CDR-04`.

> Owner: influence. These are alias-layer additions, not new rulings.

### CDR-05 · MEDIUM · $7,947,217,326 — 41 hubs appear in contracting and nowhere else

Of 499 hubs with attributed prime contracting, 41 appear in **none** of funding,
gaming, lobbying, nonprofits, deals, subawards or the FAADS attribution.
**34 of the 41 are Alaska Native Village Corporations**, for which this is the
expected shape — a village corporation holds no compact, files no tribal 990 and
lobbies through its region. The finding is not that they are wrong; it is that
each is a single-source attribution with no second dataset able to corroborate
it. Largest: Tyonek $2.69B, Ouzinkie $2.15B, K'oyitl'ots'ina $0.99B.

One non-ANC case was checked by hand and **cleared**:
`TRBS-CRNHKA-00 Cheroenhaka (Nottoway) Indian Tribe`, a Virginia
state-recognized tribe, carries $137,521,237 on a single UEI `HPHVSDPH1K93`
whose legal name is `CHEROENHAKA NOTTOWAY ENTERPRISES, LLC` — an exact-name
enterprise of that tribe, keyed `uei_exact`. Not a misattribution; a scope
question about state-recognized tribes, which is the owner's to answer.

### CDR-07 · MEDIUM · $0 — 291 gaming keys rest on a method the rules refuse alone

`gaming_facilities.csv` `entity_match_method`: containment 291, core 247, alias
154, exact 85, unanimous_city_operator 7, corrected_by_regulator_roster 1,
blank 2. `ENTITY_MATCH_RULES` rule 9 is unambiguous — *"Containment never accepts
alone"* — and names it as the class that produced 41 wrong links onto `Council
Native Corporation`. No wrong key is demonstrated here. What is demonstrated is
that **37% of the gaming register's keys rest on a method the project's own
rules will not accept without a second signal.**

### CDR-08 · NONE · tested, no disagreement found

For all 787 facilities, the operator string the source publishes (`tribe`) was
resolved independently against the spine by exact whole-name match and compared
with the `tribe_id` Cedar ships. **Disagreements: 0.** Recorded so nobody spends
a day re-deriving it.

### CDR-09 · MEDIUM · 17 nonprofits whose own registered name IS a spine entity

Unkeyed rows of `np_orgs.csv` whose `org_name` matches exactly one spine entity
on a whole-name match, and **0 of the 17 appear in `np_ein_entity_hub.csv`**.
They are Indian Health Service programmes, tribal colleges and BIE schools:
`CHAPA-DE INDIAN HEALTH PROGRAM INC` → `SGVF-CHAPAD-00`, `FEATHER RIVER TRIBAL
HEALTH INC` → `SGVF-FTHRRV-00`, `DENVER INDIAN HEALTH AND FAMILY SERVICES INC` →
`UIO-DNVRHL-00`, `KICKAPOO NATION SCHOOL` → `BIE-KCKPNT-00`, and so on.

**Two carry a prior EXCLUSION ruling** (`NAVAJO PREPARATORY SCHOOL INC`,
`CHOCTAW HOME FINANCE CORPORATION`). An exclusion is a decision, not an
omission; those two need the ruling re-read, not a link.

> **Reported, not written.** The `serves` / hub edge belongs to the constellation
> agent and to the nonprofit owner. The 17 rows with their EINs are in
> `review/1011_cross_dataset_finding_rows.csv` under `CDR-09`.

### CDR-10 · four duplicate allegations tested; all four phantom

Whole-row duplicate scan, measured with `csv.reader` over eleven identity and
cross-dataset tables — `ownership_events`, `contractor_ranking`,
`entity_relationships`, `deals_classified`, `gaming_facilities`,
`np_ein_entity_hub`, `lobbying_registrant_client_relationships`,
`fpds_uei_edges`, `cedar_identifier_ledger_final`, `entity_aliases`,
`cedar_constellation_edges`: **surplus duplicate rows = 0 in every one.**

Four semantic allegations tested:

1. **`entity_aliases` — 73 groups share `(entity_id, normalized_alias)`. PHANTOM.**
   72 of them are an original alias **plus** the deliberate ASCII-folded variant
   written by `97_build_aliases_and_relationships.py:ascii_fold` — an em-dash
   spelling and a hyphen spelling of the same name. A de-dupe on
   `normalized_alias` deletes the fold, which exists precisely so a source that
   types a hyphen still matches. The 73rd is `Dena Nena Henash` /
   `Dena' Nena' Henash` — the apostrophe orthography `ENTITY_MATCH_RULES` rule 14
   calls a positive identifying signal.
2. **`deals_*_additions.csv` against `deals_classified.csv` — 790 of 790 shared.
   PHANTOM, and the documented figure re-verifies exactly.** They are the same
   rows staged twice by design: never sum them together, and never delete them
   either, since they record which pass found which deal.
3. **`ownership_events.csv` against `deals_classified.csv` — 97 of 98 rows carry
   a `source_deal_id` in the deal ledger. PHANTOM.** Its
   $5,345,966,000 of `announced_value_usd` is the same money as the deals it
   projects. Never add the two.
4. **`cedar_identifier_ledger_final.csv` — 13,507 UEI rows, 13,507 distinct
   identifiers.** No collision.

**One real defect found while testing the phantoms:** `entity_aliases.csv`
carries a **blank `alias_id`** — the table's declared key — on 2 of 6,298 rows,
both `org_self_statement` rows for Tanana Chiefs Conference. No non-blank
`alias_id` repeats.

---

## What this agent did not do

- Did not sum across datasets. Every dollar here is a reach measure over money
  another table already publishes.
- Did not collapse a duplicate. Four allegations tested, four phantom, zero rows
  removed.
- Did not repair another dataset's table in place. `772` was not run; the
  `serves` edges were not written; no ledger row was repointed; no candidate
  deal was written to `deals_classified.csv`.
- Did not treat a name match as identity. Every award-side match in both scripts
  is an exact whole-name or contiguous-token-run test with ≥2 distinctive
  tokens; token-level tests appear only where they REFUSE.

## Files written

| file | what |
|---|---|
| `code/1010_ownership_change_from_contracting.py` | detector; `measure` / `verify` / `selftest` |
| `code/1011_cross_dataset_reconciliation.py` | twelve checks; `measure` / `verify` / `selftest` |
| `review/1010_ownership_change_candidates.csv` | 98 leads, ranked |
| `review/1010_ownership_change_rejections.csv` | 682 intra-family refusals with the shared evidence |
| `review/1010_announced_deals_vs_contracting.csv` | 217 announced deals against FPDS |
| `review/1011_cross_dataset_findings.csv` | 12 findings |
| `review/1011_cross_dataset_finding_rows.csv` | 1,509 instance rows |
| `docs/schema/ownership_change_invariants.json` | what `1010 verify` enforces |
| `docs/schema/cross_dataset_reconciliation_invariants.json` | what `1011 verify` enforces |
| `docs/CROSS_DATASET_RECONCILIATION_LEDGER.md` | this file |
