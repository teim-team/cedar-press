# The owner's ladder, run at scale — 2026-09-02

*Scripts: `code/1117_ladder_adjudication.py` (the splink queue) and
`code/1122_ladder_repoints.py` (three named families). Both applied. Both
`verify` green; both `selftest` proves `verify` exits 1 on an injected
violation and 0 on restore. Registers:
`review/ladder_adjudication_2026-09-02.csv` (252 rows) and
`review/ladder_repoints_2026-09-02.csv` (36 rows). Conservation proofs:
`docs/LADDER_ADJUDICATION_1117.json`, `docs/LADDER_REPOINTS_1122.json`.*

The owner: *"All I gotta do is look up its codes, its address, its website,
see if the website literally says 'wholly owned by blah blah blah', or if the
address matches any other company."* The ladder, in his order:
**address → website → search the address for other owned entities → CAGE /
declared parent as a pointer → news → STOP.**

## The numbers

| | identifiers | prime rows | obligations |
|---|---:|---:|---:|
| **1117** keyed (84 ACCEPT + 12 REPOINT) | 96 | 1,210 | **$696,817,828.01** |
| **1117** declined (140 REFUSE + 16 UNRESOLVED) | 156 | — | **$261,232,503.02** |
| **1122** repointed | 27 | 3,771 | **$1,432,559,402.63** |
| **1122** withdrawn | 8 | 1,757 | **$450,452,958.06** |
| **1122** confirmed where it stood | 1 | 113 | $2,041,005.56 |

**85 distinct Cedar entities** gained rows in `prime_contracts`; distinct
`cedar_uid` in that table goes **449 → 526**.

Conservation, measured independently in duckdb against the pre-pass backups:

```
rows            1,217,768  ->  1,217,768
columns                75  ->         75
total_obligations   $310,005,258,660.75  ->  $310,005,258,660.75   (to the cent)
attributed rows       790,003 -> 791,213 (1117) -> 789,456 (1122)
attributed dollars    $229,464,705,356.85
                   -> $230,161,523,184.86   (+$696,817,828.01, exactly 1117)
                   -> $229,711,070,226.81   (-$450,452,958.05, exactly 1122)
```

> **`START_HERE.md` still says prime is `$244.77B (79.0%) · 498 entities ·
> 888,803 rows`. It is not.** Measured on the live file 2026-09-02:
> **$229,711,070,226.81 (74.1%) · 526 entities · 789,456 rows.** Most of that
> drift is `code/1079`'s quarantine withdrawals earlier the same day, not this
> pass; this pass is +$696.8M and −$450.5M against it. The row is stale in the
> way §6 of the field guide describes and should be re-measured, not re-typed.

## The rung that settled the most, and it is not on the owner's list

**A UEI THAT CARRIES TWO NAMES IS A RENAME, RECORDED IN THE FEDERAL FILE.**
He never needed this rung because he was looking at one firm at a time.
`prime_contracts` stores the awardee name **as filed**, and a registrant that
renames keeps its UEI, so the answer is often already inside the table:

```
HJ3MK5334WS6  "INDIAN WALK IN CENTER"  +  "URBAN INDIAN CENTER OF SALT LAKE"
DT3GJW3JNMN5  "THE ABERDEEN AREA TRIBAL CHAIRMENS HEALTH BOARD"
              +  "GREAT PLAINS TRIBAL CHAIRMEN'S HEALTH BOARD"
MQGXUX1QMZL8  "NATIVE AMERICAN COMMUNITY HEALTH CENTER, INC."  +  "NATIVE HEALTH"
KMA9EB4NSB87  "NATIVE AMERICAN REHABILITATION ASSOCIATION INC"  +  "NARA NW, INC."
C471YH1GMPX7  "NORTHWEST INDIAN FISHERIES COMM"  +  "... COMMISSION"
```

The Salt Lake one, $33.2M, had already defeated three web rungs: `uicsl.org`
states no former name, `indianwalkincenter.org` is a parked GoDaddy page, and
UIHI's Salt Lake City programme profile names only the current organisation.
**Query the identifier before you open a browser.**

Two more on-disk rungs earned their place and cost nothing:

* **`nest_enterprises.csv`** settled `ASRC Federal Mission Services`
  (uei `WTJEFSM3P945`, $480.3M), `Neeser Paug-Vik JV` (uei `KVXHALMXN7J5`),
  `Hui Huliau Technology Services` (uei `KW1DMENKNVU4`, $38.7M) and
  `Colorado Professional Resources` (uei `M5RSKDDD9KJ7`) — **by UEI**, from
  parent-declared subsidiary lists.
* **`fpds_uei_edges.csv`** settled `Cherokee Chainlink & Construct` ($2.92M):
  it declares `CHEROKEE CHAINLINK AND CONSTRUCTION` as parent **28 times**,
  over rule 11's floor of 20, and that parent is already tier A in the ledger.

## What the web rungs actually returned

Verbatim, and each one ended an enquiry:

* `texasnativehealth.org/mission-history` — *"Texas Native Health, formerly
  known as Dallas Inter-Tribal Center and Urban Inter-Tribal Center of Texas,
  was created to fulfill the immediate needs of those living in the DFW
  Metroplex as a result of Public Law 959."* ($42.25M)
* `senecanationgroup.com/companies/great-hill-solutions/`, reached because
  **`greathillsolutions.com` 301-redirects to it** — *"Great Hill Solutions,
  LLC (Great Hill) is a wholly owned subsidiary of Seneca Nation Group (SNG),
  the federal contracting arm of Seneca Holdings."* ($549.81M)
* `huihuliau.com` — *"Hui Huliau, A Native Hawaiian Organization"*, with Hui
  Huliau Technology Services under "Our Companies", at Waianae HI, the
  contractor's own city. ($38.70M)
* `ganaayoo.com/subsidiaries` — names *"Gana-A'Yoo Construction Services JV"*
  and states *"Gana-A'Yoo, Limited (Gana-A'Yoo) is an Alaska Native Village
  Corporation (ANC), headquartered in Anchorage, and owned by its Koyukon
  Athabascan shareholders and their descendants."* ($18.14M)
* `capefoxcorp.com` — *"CFC is the Alaska Native Corporation for the Village
  of Saxman, Alaska"*, and its Federal Contracting Group page names *"Cape Fox
  Federal Integrators, LLC"*.
* `asrcfederal.com` — *"ASRC Federal is a wholly-owned subsidiary of Arctic
  Slope Regional Corporation (ASRC), an Alaska Native corporation owned by
  over 14,000 Iñupiaq shareholders."*
* **IRS BMF is a genuinely independent evidence family** (`ASSERTION_LAYER`'s
  test: not a republication of anything Cedar holds) and its `sub_name` field
  is a doing-business-as line. It settled *"Central Oklahoma American Indian
  Health Council Inc"* → **Oklahoma City Indian Clinic** ($53.24M) and gave the
  address that settled **Heart of America Indian Center** → Kansas City Indian
  Center (`600 W 39TH ST`, the address `kcindiancenter.org` publishes for
  itself).

**A redirect is evidence.** Two of the largest answers in this pass —
Great Hill → Seneca, and Alaka'ina → Bering-Alaka'ina — arrived as HTTP 301s
from the firm's own historic domain to its new owner's site. Follow them.

## The refusals are the product

**166 of 252 splink rows and 8 of 36 identifiers were declined, $711.7M of
prime obligations left or taken off the attributed total.** Named families:

* **18 pest-control companies keyed to `FOUR CORNER PEST CONTROL LLC`** on the
  token `PEST CONTROL` — Qualla Termite, No Ka Oi Termite (Guam), Gonzalez,
  Warners, Badland's, Dakota, Mohave, Ridley, 1-Stop (twice), Brunelle's, Five
  Star, Shahan, Solutions Weed & Pest, APC, Bugs Bee Gone, and a firm actually
  called `Pest Control, Llc`. One Native-owned pest-control company had
  absorbed an industry.
* **`SIERRA NEVADA CORPORATION` → Te-Moak Tribe of Western Shoshone.** A large
  privately held aerospace company, on the token `Nevada`.
* **`Indian Health Service (8670)` and `Indian Health Service (0878)`** keyed
  to two urban Indian organisations. That is the federal agency.
* **`AMERICAN EAGLE PROTECTIVE SERVICES CORP`, $450.45M, withdrawn.** A Texas
  security firm on `eagle`, which is already on `cedar_domain.NAME_TRAPS`.
  Rungs 1, 2 and 4 all ran; rung 6 answered.
* Nine organisations refused only because **Cedar has no row for them**:
  National Indian Child Welfare Association, Intertribal Buffalo Council
  (formerly Intertribal Bison Cooperative — one organisation appearing twice in
  the queue under both names), Toiyabe Indian Health Project, Alaska Native
  Health Board, Edith K. Kanaka'ole Foundation, Native American Fish & Wildlife
  Society, AIANTA, Baltimore American Indian Center, American Indian Center of
  Chicago. `ENTITY_MATCH_RULES` is explicit: **a refusal is not a finding that
  the organisation is non-Native.** These are spine gaps and are listed as
  such.

## Two things that would have gone wrong, and what caught them

**1. An exact name match on a SHARED UEI is not an entity match.**
The mechanical half of `1117` matches a filed name to exactly one spine name
with state agreement — 49 rows, and it is right 49 times. It was also about to
key **`HASKELL INDIAN NATIONS UNIVERSITY`** ($286,328) to the register's
Haskell entity. UEI `PW9NHUE1KUY4` carries a second awardee name in
`prime_contracts`: **`DOI BUREAU OF INDIAN AFFAIRS`**. It is the Bureau's
registration, and keying it would have put federal-agency awards on a tribal
college. The guard is now `MECH_EXCLUDE`, and the general rule is *check what
else the identifier carries before you trust a name match on it*.

**2. A detector's proposal can be the error.** `OWNER_DECISION_QUEUE` EL-1's
second-largest row, UEI `H1ZEEZK2D6B3` *"San Juan Pueblo Tribal Council"*,
$2,041,005.56, is keyed to **Ohkay Owingeh and that is correct** — Ohkay
Owingeh *is* the renamed San Juan Pueblo and 113 of 113 awards are in New
Mexico. The proposal, `TRBF-SNJUAN-00`, is the San Juan **Southern Paiute**
Tribe of **Arizona**. It reads as a collision only because the spine does not
carry `San Juan Pueblo` in Ohkay Owingeh's aliases, so a FORMER name looks
foreign. **Confirmed, not moved**, and the reason is written onto the ledger row
so the detector can learn the exception.

## Two entities in one community, checked before keying either

* **Old Harbor.** The queue proposed the Native **Village** of Old Harbor
  (`CE-0000D-E5`). UEI `K3N7G5L6GRY6`'s awardee name is `OLD HARBOR NATIVE
  CORPORATION` — the ANCSA village corporation, `CE-000A9-81`. Keyed to the
  corporation. **Consequence flagged, not applied:** `code/1075` left 292 Sage
  Systems rows ($66.4M) unattributed *because this corporation's UEI had no
  entity row*; giving it one means `40_build_prime_contracts.py`'s `parent_uei`
  fallback will reach them on the next rebuild. Nobody has ruled on that.
* **Seneca.** `senecanationgroup.com/about`: *"The Seneca Nation is a sovereign
  Nation rooted in its ancestral homelands in Western New York."* Seneca Nation
  of Indians (NY, `CE-001AC-YN`), not the Seneca-Cayuga Nation (OK,
  `CE-001AB-RW`).
* **Sea Lion — and here Cedar contradicts ITSELF.** The register holds `Sea
  Lion Corporation` as a village corporation `CE-000BV-SK`;
  `nest_enterprises.csv` holds a `Sea Lion Corporation` as an enterprise of
  **Choggiung, Ltd.** `CE-00088-R8`. Two Cedar records, two owners, one name.
  `Sea Lion Security & Control Systems` and `Sea Lion International` ($6.08M)
  are left **UNRESOLVED** rather than keyed to a name Cedar cannot resolve
  internally. Queued as **LAD-1d**.

## The Eastern Shawnee family — $47.83M on a Virginia tribe

Found by pulling one thread in `review/native_business_link_holds_2026-09-02.csv`.
The hold reads `state_conflict:directory=OK;federal=KS`. Behind it: **twelve
CAGE codes whose registered name contains `EASTERN SHAWNEE`, all keyed to
`CE-00130-KS`, the Chickahominy Indians-Eastern Division of VIRGINIA**, tier B
by `need_v6` — the method START_HERE puts at 6.5% accurate. The token is
`EASTERN`, the same token that put the Order of the Eastern Star on a Virginia
tribe.

**The owner had already ruled on this family, twice, and the ruling never
reached its siblings.** `CAGE 09J30 ERG - EASTERN SHAWNEE JV, LLC` and
`CAGE 12DZ6 EASTERN SHAWNEE - VERACITY JV LLC` are keyed to the Eastern Shawnee
Tribe of Oklahoma at **tier A by `elijah_ruling`**. All 82 prime rows on the
Virginia tribe were Eastern Shawnee firms in KS and MO; it now has **zero**,
which is the honest state.

**The directory does not make it Muscogee.** The listing that surfaced it is a
Muscogee (Creek) Nation vendor directory, and `PUBLICATION_POLICY` is explicit
that *"a firm on a TERO vendor list may have no ownership relationship at
all."* The firm's own legal name names its nation; the directory names its
customer.

Seven more identifiers on the same Virginia tribe were **withdrawn** on
`EASTERN` or `DIVISION` alone — including a Rhode Island Pequot tribe, a South
Carolina Cherokee group, an Alabama foundation, and **two North Dakota
sports/gun clubs**. `CHICKAHOMINY INDIAN TRIBE - EASTERN DIVISION` stays
exactly where it is.

## A deal nobody has reported

`alakainafoundation.com` 301-redirects to `beringalakaina.com`, which names
nine companies — Ke'aki Technologies, Laulima Government Solutions, Kūpono
Government Services, Kāpili Services, Po'okela Solutions, Kīkaha Solutions,
Pololei Solutions, Alaka'ina Professional Services, Alaka'ina Technical
Services — records that the **Alaka'ina Foundation**, a Native Hawaiian
Organization certified in 2004, established and ran them from 2005, and states
they *"were wholly acquired in June 2026 by BSNC"*.

That **answers `OWNER_DECISION_QUEUE` EL-2**, which asks why `Laulima
Government Solutions, LLC` has two declared owners: it is not a joint venture,
the owners are **sequential**. And it is a nine-company NHO family acquired by
an Alaska Native regional corporation, which is precisely the class
`PUBLICATION_POLICY` calls *"a deal Cedar can report"*.

## What stopped, and what was tried at each rung

Rung 6 — *"sometimes you just can't find it"* — was used **16 times in the
splink queue and once more for `Kaiva Services`**, and each row records the
rung it died on. The largest:

| firm | $ | rung 1 | rung 2 | rung 3/4 |
|---|---:|---|---|---|
| `Hui O Ka Koa, Llc` | $64.30M | Honolulu; the proposal rests on the word `koa` | `huiokakoa.com` does not resolve | generic Honolulu co-location |
| `Friend Contractors - White Mountain Jv` | $19.48M | **Kodiak AK**, ~1,000 km from White Mountain; neighbours are an Alutiiq cluster | none | — |
| `Ascg Incorporated Of New Mexico` | $16.57M | Albuquerque only | `ascg.com` does not resolve | — |
| `Gtb Health Solutions, Llc` | $2.75M | Traverse City MI — the initialism and the city both point at the Grand Traverse Band, which is NOT what was proposed | `gtbindians.org` names only "Grand Traverse Economic Development" | — |
| `Indian Health Board Of Billings` | $3.15M | Billings MT, one UIO in town | site gives the legal name as BUIHWC and names no former name | IRS holds both names, separately |
| `Kaiva Services` | $9.26M | directory Tulsa **OK** against federal Ivins **UT** | `kaivaservices.com` blank | declares itself as its own parent; no FPDS edge |

An initialism is not an ownership statement, and one UIO per town is not proof
of a rename.

## Tier, and what an agent may not do

**Every link written by both scripts is tier B**, method `ladder_1117` /
`ladder_1122`. `ENTITY_MATCH_RULES` rule 8: an agent ruling may not mint tier A.
Neither method is in the RULED set in `62_no_regression_check.py`, so
`tier_A_ruled` cannot be inflated by this pass — and where `1122` corrected a
tier-A row it **fell** by seven, itemised in `docs/KNOWN_ISSUES.md` under
`LADDER-1117-1122`, and was not re-baselined.

Nothing was minted, retired or reused. Every destination `cedar_uid` was
verified present in `data/spine/cedar_identity_register.csv` before any write
(invariant I5). Withdrawals write `confidence_tier = X` and **no**
`exclusion_id`: `data/spine/cedar_exclusion_rulings.csv` is the owner's
register.

## What was deliberately not written

* **`subawards.csv`** carries 954 rows on a keyed prime UEI and 1,238 on a
  keyed sub UEI. Subaward attribution has its own grain and its own money rules
  (`MONEY_TOTALLING_RULES.md`); the counts are reported so the next pass
  propagates deliberately rather than by accident.
* **`prime_contracts_archive_backfill.csv`** — 0 of these UEIs appear in it.
* **The spine and the register.** Adding `San Juan Pueblo` to Ohkay Owingeh's
  aliases is the right fix for EL-1's false positive and it is a spine edit;
  it is asked in `OWNER_DECISION_QUEUE` LAD-1b, not taken.
* **`code/62_no_regression_check.py`.** It does not run — `NameError: ROOT`,
  from commit `f274b01`. The integrator owns it. See `KNOWN_ISSUES`.
