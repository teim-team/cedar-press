# Resolution rules learned from the adjudication corpus

*Written 2026-09-01 (workstream I). Every number here is reproduced by
`py -3 code/522_mine_rulings.py all`; the assembled corpus is written to
`data/interim/ruling_corpus_mined.csv`. Read with
`docs/NATIVE_ENTITY_NUANCES.md`, which holds the domain knowledge these rules
operate on.*

The owner's ask was not for a summary of what was decided. It was for **the
discriminating features that decided it** — stated so they can be coded, each
bounded by the counter-example that stops it becoming a habit. A rule with no
counter-example in this file is a rule nobody has stress-tested yet, and it is
labelled as such.

---

## The corpus

**24,411 recorded adjudications** across **39 source files**, assembled from
`data/spine/`, `data/clean/` and `review/`. Three populations, which must not
be summed carelessly:

| ruler | n | what it is |
|---|---:|---|
| **OWNER** | **4,168** | Elijah Moreno, by hand. 3,789 of them are his own **pre-Cedar Stata linkage work**, read back out of `fed_funding_do_file.do` and its corrected twin — the largest and oldest body of judgement in the project. |
| RULESET | 4,656 | decisions produced by **two filter scripts the owner authored**. Two human acts. |
| AGENT / MIXED | 15,587 | agent research verdicts, unioned into `cedar_ruling_ledger_consolidated.csv`. |

**54% of the owner's recorded decisions are refusals** (2,242 REFUSE vs 1,926
CONFIRM). That ratio is the reason this file is organised around what makes him
say no.

Previously un-mined, as far as any document in the repo shows: the **3,789
do-file rows** (never referenced outside their own extract), the **752-row
`entity_crosswalk_bgov.csv`** (the owner's 2021 tribe→vendor linkage, cited
nowhere), and the **`my_guess`/`my_confidence` columns** on the reconciliation
cards — the only place in the repo where the machine and the human answered the
same question and both answers were kept.

---

# PART 1 — RULES IMPLEMENTED THIS PASS

## R1. A tribal token beside an administrative-geography word names a PLACE

**The rule.** On the loose token-subset path, if the filed name carries
`COUNTY, COUNTIES, PARISH, BOROUGH, MUNICIPALITY, MUNICIPAL, METROPOLITAN,
FALLS, HEIGHTS, JUNCTION, BEACH, DOWNTOWN, ESTATES, BLUFF, SUBDIVISION,
UNINCORPORATED` and the winning entity's **own canonical name does not carry
the same word**, refuse: `REFUSED_ADMIN_GEOGRAPHY`.

**The discriminating feature.** Not the tribal token — the *head*. American
counties, towns and falls are named for the nations that were removed from
them, so the token is evidence of history, not of the filer's identity. The
canonical-aware clause is what makes it a rule and not a blocklist: the test is
*does the entity's own legal name contain this geography word*, and only if it
does not is the word doing place-work.

**The evidence.**
- `503.resolve()` was returning a tribe for **2,458 of 5,197 names a human had
  already refused (47%)**. This guard accounts for **659** of the 1,404 now
  refused.
- The owner's own nonprofit filter is a hand-maintained list of **52 literal
  patterns** covering 1,711 exclusions. **33 of the 52 are this one rule in 33
  costumes** — `APACHE COUNTY`, `APACHE JUNCTION`, `CHEROKEE COUNTY`,
  `CHEROKEE TRAIL`, `CHIPPEWA COUNTY`, `CHIPPEWA FALLS`, `WICHITA FALLS`,
  `KLAMATH FALLS`, `ONONDAGA COUNTY`, `SEMINOLE COUNTY`, `PIMA COUNTY`, …
- Real cases the guard now stops: `COWLITZ COUNTY AUXILIARY COMMUNICATIONS
  SERVICE` → `TRBF-COWLTZ-00`; `OSAGE COUNTY ECONOMIC DEVELOPMENT CORPORATION`
  → `TRBF-OSAGEN-00`; `SANTA ROSA COUNTY FLORIDA` → `TRBF-SROSAR-00` (which the
  correction register already had to unwind across 299 rows in three tables).

**The counter-examples that bound it.**
- **Forest County Potawatomi Community** is a federally recognized tribe with
  COUNTY in its name. The canonical-aware clause saves it; a plain COUNTY
  blocklist would have destroyed it, along with **Cold Springs Rancheria** and
  the **Confederated Tribes of Warm Springs**.
- **TOWNSHIP, VILLAGE and CITY are deliberately absent.** `KAYENTA TOWNSHIP` is
  the Navajo Nation's own municipal government and `INDIAN TOWNSHIP TRIBAL
  GOVERNMENT` is a Passamaquoddy reservation government — both settled by owner
  rulings in `review/ruling_vs_table_contradictions_2026-08-26.csv`. A
  township can be a tribe. A county never is.

**Where it lives.** `code/503_identity.py` → `ADMIN_GEOGRAPHY` and
`loose_path_refusal()`. It also makes the hand-written `TUSCARAWAS METROPOLITAN
HOUSING` entry in `RESOLUTIONS` redundant: `522 fixtures` calls the guard
directly on that name and it reaches `REFUSED_ADMIN_GEOGRAPHY:METROPOLITAN`
from the shape alone. **The literal that `NATIVE_ENTITY_NUANCES.md` records as
a lesson is now a rule that would have caught it unaided.**

---

## R2. A civic organisation that borrowed a place name is not the nation

**The rule.** On the loose token-subset path, if the filed name carries a token
from `CIVIC_FORM` — congregations, sports clubs, service clubs, PTOs, arts and
heritage societies, sheriffs' and firefighters' associations, cemetery
associations — refuse: `REFUSED_CIVIC_FORM`.

**The discriminating feature.** The **head noun says what kind of thing it is**,
and the tribal token sits in the modifier slot doing the work of a postcode.
`ONONDAGA GOLF AND COUNTRY CLUB` is a golf club in Onondaga County.
`TUSCARORA SOCCER CLUB` is a soccer club. `RESTORATION CHURCH WICHITA` is a
church in Wichita, Kansas.

**The evidence.** 745 of the 1,404 new refusals. Token-level, over the
consolidated ruling ledger: `SOCIETY` 32 refusals / 0 confirmations,
`HISTORICAL` 22/0, `CLUB` 33/2, `CHURCH` 124 refusals in the sweep.

**How the vocabulary was chosen, and why that matters.** Every token had to
appear in **zero** of the 1,952 names a human ruled *to* an entity **and zero**
of the 1,536 spine canonical names. Selection on a measured criterion, not on
taste.

**The counter-examples that bound it — and one of them was caught by a
held-out control, not by me.** The vocabulary was then tested against the
owner's 2021 BGOV crosswalk, 751 vendor names never used in fitting. It
rejected three:

| name | why the token had to go |
|---|---|
| **Makah Museum** | MUSEUM removed. Tribes run museums. |
| **Southern Ute Cultural Center & Museum** | same |
| **Native Village of Port Lions** | LIONS removed. It is an Alaska Native village, not a service club. |

`HOSPITAL`, `FOUNDATION`, `ASSOCIATION`, `SCHOOL`, `CENTER`, `PARK` and
`MEMORIAL` were considered and **rejected before testing**: each occurs on real
spine entities (185 BIE Schools; NHO foundations) or on real owner-ruled Native
organisations. `SCHOOL` alone would have killed 160 spine rows.

**One survivor of the held-out test is not a false positive.** The vocabulary
still rejects **`Cherokee Boys Club Inc/The`**, which the 2021 crosswalk
carries as a Cherokee vendor. It is right to reject it: `EXCL-0003`, the
owner's own later ruling, reads *"non-profit not tribally owned parent_name ==
Cherokee Boys Club Inc"*, and `ruling_vs_table_contradictions_2026-08-26.csv`
records `THE CHEROKEE BOYS CLUB, INC.` sitting at tier A against a `BLOCKED:
nonprofit_not_tribally_owned` ruling. **The guard agrees with the owner's later
judgement against his own earlier one.**

**Where it lives.** `code/503_identity.py` → `CIVIC_FORM`.

---

## Blast radius of R1 + R2, measured before and after

| control population | before | after | verdict |
|---|---:|---:|---|
| names a human **REFUSED** that `resolve()` claimed | **2,458** | **1,055** | −1,403 (−57%) false resolutions; 1,404 names now carry an explicit `REFUSED_*` reason (745 CIVIC_FORM, 659 ADMIN_GEOGRAPHY) |
| names a human **RULED to an entity** that resolve | 1,117 | **1,117** | unchanged |
| **spine canonical names** that resolve | 1,532 / 1,536 | **1,532 / 1,536** | unchanged |
| **held-out** BGOV vendor names refused by a guard | — | **1** (Cherokee Boys Club, correctly) | — |
| `503 reconcile` legacy ids resolved | 359 / 361 | **358 / 361** | −1: `ONONDAGA COUNTY RESOURCE RECOVERY AGENCY INC`, $0 |

The only production change is one legacy id carrying **$0**, correctly refused.
`62_no_regression_check.py` exit 0. Both guards are proved by
`py -3 code/522_mine_rulings.py fixtures`: 11 must-catch cases (all real
refused names) and 8 must-not-catch near-misses.

**The residual is honest and is the next pass's work.** 1,055 refused names
still resolve, dominated by single-token entities whose token is a US city:
Wichita (232), Cherokee Nation (142), Klamath (77), Seminole (70), Seneca (70),
Taos (68), Laguna (60). `ST. AUGUSTINE DISTILLERY` still resolves to
`TRBF-AGSTNE-00`. See R7 for the rule that would close it and why it is not
implemented yet.

---

# PART 2 — RULES DOCUMENTED, NOT YET IMPLEMENTABLE HERE

## R3. Nearly half of tribal enterprises share no word with their owner

**The rule.** Name matching has a hard ceiling on tribal contracting
subsidiaries, and it is roughly half. Candidate generation that relies on the
tribe's name appearing in the vendor's name cannot find the other half, and no
amount of fuzzier matching changes that — the words are not there.

**The discriminating feature.** Measured over the owner's own 2021 BGOV
crosswalk, **347 of 750 tribe→vendor linkages (46.3%) share not one
non-generic token** between the vendor name and the tribe name.

**The evidence, and the three shapes inside it.**
- **In-language names.** Alabama-Quassarte Tribal Town → `Aquate Corp`;
  Chitimacha → `Tiya Services LLC`, `Wayti Services LLC`, `Keta Group LLC`;
  Comanche Nation → `Queni Engineering Services LLC`; Blackfeet →
  `Syieh Development Corp`; Burns Paiute → `WA DA Enterprise Corp`. This is the
  `Suh'dutsing` pattern in `NATIVE_ENTITY_NUANCES.md`, and the crosswalk shows
  it is not an exception but a **house style**.
- **Landmark names.** Blackfeet → `Chief Mountain Technologies Inc`.
- **Wholly opaque corporate names.** CSKT → `S&K Electronics`,
  `International Towers LLC`; Coeur d'Alene → `Echelon LLC`; Choctaw Nation →
  `AIP Enterprises LLC/OK`.

**The counter-example.** 403 of 750 (53.7%) *do* share a token, so name
matching is not useless — it is a **recall ceiling, not a precision problem**.
And the sharing can mislead: see R4.

**Where it belongs.** Candidate generation, not `503`. The only instruments
that cross this gap are ownership declarations —
`data/clean/fpds_uei_edges.csv` (2,901 parent/ultimate-parent edges) and the
CAGE hierarchy — both already documented in `NATIVE_ENTITY_NUANCES.md`.
`503.resolve()` should never be asked to bridge it, and a "no candidate" from
`503` on an opaque LLC is the correct answer, not a gap.

---

## R4. A tribal name inside an enterprise name is a BRAND, not an owner

**The rule.** When a firm's name contains a tribal token, that token identifies
the brand. It is not evidence of who owns the firm, and it is frequently the
name of a *different* nation from the owner.

**The discriminating feature.** Ownership evidence, or nothing. This is the
inverse of R3 and the more dangerous half: R3 loses you entities, R4 gives you
the wrong one at tier A.

**The evidence — every one an owner ruling against a table**
(`review/ruling_vs_table_contradictions_2026-08-26.csv`, 32 of 122 naming a
different entity):

| firm | the table said | the owner ruled |
|---|---|---|
| `MUSKOGEE METAL WORKS INC`, `MUSKOGEE TECHNOLOGY` | Lower Muscogee (`TRBS-LWRMSE-00`) | **Poarch Band of Creek Indians** |
| `ECHOTA DEFENSE SERVICES` | Echota Cherokee, state-recognized (`TRBS-ECHOTA-00`) | **Cherokee Nation** |
| `SEMINOLE NATION SERVICES, LLC` | Seminole Tribe of Florida | **Seminole Nation of Oklahoma** |
| `POTAWATOMI TRAINING LLC` | Citizen Potawatomi | **Forest County Potawatomi** |
| `RED CEDAR ENTERPRISES INC` | Paiute Indian Tribe of Utah (the *Cedar* Band) | **Modoc Nation** |
| `BLUE EARTH SERVICES & TECHNOLOGY LLC` | Blue Lake Rancheria | **Confederated Coos** |
| `FOUR TRIBES CONSTRUCTION SERVICES, LLC` (+3 siblings) | Te-Moak | **Susanville Indian Rancheria** |

**The corroboration across four years.** The owner's 2021 BGOV crosswalk
independently lists `Echota Defense Services` under **Cherokee Nation** — the
same call he made again in 2026 against a table that had guessed the
state-recognized Echota. Two adjudications, four years apart, same answer,
built from different sources.

**The counter-example.** `Cherokee General Corporation` (`RUL-0002`) proves the
rule's *other* edge: not merely the wrong nation, but **no** nation. It is
Doyon-owned; the Cherokee name predates the acquisition and carries no Cherokee
connection at all. The owner logged it as *"the classic Cherokee Inc. trap."*

**Where it belongs.** A lint class over the ledger: *tier A + a tribal token in
`legal_business_name` + `attribution_method` in the name-matching family* is a
defect signature. Not codeable in `503`, which sees a name and no method.

---

## R5. A scope exclusion is not an ownership exclusion

**The rule.** An exclusion register records *two different acts* in one column
— "this is not a Native entity" and "this is outside my analysis frame" — and
reading the second as the first destroys real entities.

**The discriminating feature.** The reason text, read literally. The owner made
this call himself, once, in `RUL-0004`:

> `EXCL-0116` in `hci_analysis.do` line 1029 reads `// ANC` — a SCOPE exclusion
> from a lower-48-tribes-only analysis, NOT an ownership exclusion. Doyon
> attribution stands; **$302.5M** in prime obligations retained.

**The evidence that it generalises far beyond that one row.** His do-file
exclusion block, mined here for the first time, drops by name:

| what was dropped | unique do-file exclusions | what the Cedar spine now carries |
|---|---:|---|
| schools, colleges, universities | 202 | **185 BIE Schools + 37 Tribal Colleges** |
| health centres, hospitals, clinics | 74 | self-governance consortia (`SGVF-*`), Urban Indian Organizations (43) |
| housing authorities | 195 | constituency and tribal-government entities |
| state-recognized tribes (`haliwa-saponi`, `lumbee`, `mowa choctaw`, `united houma`, `muscogee nation of florida`, `the chickamauga nation`) | 86 | **64 `TRBS` rows** |
| intertribal / intra-tribal | 20 | **56 Intertribal Organizations** |

Roughly **570 names the owner's earlier work excluded are entities the current
spine carries in their own class.** They do not contradict each other; they
answer different questions. His `federal_funding_rulings_from_dofile.csv`
already labels one batch honestly — *"the following tribe is federally
recognized but not serviced"* — which is a service-area statement, not an
identity statement.

**The counter-example.** The scope/ownership distinction is not a licence to
promote everything: `THE CHEROKEE BOYS CLUB, INC.` and the 26
`nonprofit_not_tribally_owned` exclusions are **genuine ownership refusals**
carrying the same file's formatting. The reason text is the only thing that
separates them, which is exactly why it must never be discarded.

**Where it belongs.** `NATIVE_ENTITY_NUANCES.md` (added), and a required
`exclusion_kind` column — `scope` vs `ownership` — on any future exclusion
register. Do not re-run the do-file exclusions against the current spine
without one.

---

## R6. Individual Native ownership is not entity ownership — in both directions

**The rule.** A firm owned by a Native person gets `CEDAR-ENT-` and
**deliberately no tribal link**. The presence of "Tribal", "Native" or
"American Indian" in a firm's name is not evidence of anything.

**The evidence.** 45 rulings in `individual_native_prior_rulings.csv` (40
`INDIVIDUAL_NATIVE`, 5 `INDIVIDUAL_NATIVE_NOT_TRIBAL`) and 31 in
`cedar_exclusion_rulings.csv`. Read the owner's own notes:

- *"Tribal Energy Alternatives"* → **individually Native-owned, not tribal.**
- *"Laguna Creek LLC — NOT Pueblo of Laguna. Individual ownership is not entity
  ownership."*
- *"FOUR CORNER PEST CONTROL LLC — Proposed Te-Moak — wrong."*
- `Native American Services Corp` and `Native Energy & Technology Inc` →
  **NOT_NATIVE** (`review/ruling_redirect_unresolved_2026-08-12.csv`).

**The base rate that makes this the dominant residual.** On the 99 high-dollar
reconciliation cards the owner ruled, **54% are `not_native` (33) or
`individual` (21)**. Only 46% are tribe, ANC or NHO.

**The counter-example.** The class is real and is being *under*-counted, not
over-counted: `docs/CICD_BENCHMARK.md` UNDERCOUNT-04 records 22 of 40 firms the
owner ruled individually Native-owned carrying **no** Native self-certification
on a single contract row — $212.5M. The person can see what the instrument
cannot. So the rule is "no tribal link", never "no entity".

**Where it belongs.** Already encoded as
`refuses_tribal_link_not_native_ownership`. The gap is in *candidate
generation*, which keeps proposing tribal owners for these firms.

---

## R7. Cedar's own prior fails in exactly one direction: over-attribution

**The rule (and the one place this file can score the machine against the
human).** `my_guess`/`my_confidence` on the reconciliation cards are Cedar's
algorithmic prior; `ruling` is the owner's answer. 99 cards where both exist.

| | |
|---|---:|
| prior **abstained** (`unsure`) | 73 (**74%**) |
| prior **committed** | 26 |
| … correct | 18 (69%) |
| … **wrong** | **8** |

**The discriminating feature — and it is the finding.** All 8 errors have the
same shape. The prior named an **institutional Native owner** where the truth
was something narrower:

```
anc -> individual   2    (Ames 1 LLC @60%, American Mechanical Inc @50%)
anc -> not_native   2    (Frawner Corp @50%, Global Constructors LLC @50%)
anc -> tribe        2    (T&H Services LLC @75%, Moss Cape LLC @75%)
nho -> individual   1    (Environet Inc. @65%)
nho -> anc          1    (Akimeka Technologies @60%)
```

**It has never once wrongly said `not_native`.** Every error is a false
positive for institutional Native ownership. Combined with the 46% base rate in
R6, a prior that guesses `anc` on an opaque LLC is wrong more often than right.

**The counter-example that keeps this from being "always abstain".** The two
`anc -> tribe` errors were *right that the firm is Native* and wrong only about
the class — `T&H Services` is Central Council Tlingit & Haida, `Moss Cape` is
Native Village of Eyak. Both are Alaska entities that a matcher reasonably read
as ANCs. Which is exactly the Eyak trap: one village name, two enterprise
families, two different owners (see `NATIVE_ENTITY_NUANCES.md`).

**Where it belongs.** The reconciliation tool's scoring. **Concrete proposal:
suppress any `anc` or `nho` prior below 80% confidence and emit `unsure`** —
on this sample that removes 8 of 8 errors and 6 of 18 correct guesses, trading
a 69% hit rate for a clean one. Not implemented: the tool is not this
workstream's file, and 99 cards is a thin sample for a threshold.

---

## R8. A place-name refusal must be recorded against the SHAPE, not the string

**The rule.** Recording an exclusion as a literal name guarantees you pay for
it again in the next spelling.

**The evidence.** From `cedar_correction_register.csv`, verbatim:

> *Coeur d'Alene Mining, the mining company — not the Coeur d'Alene Tribe.
> Script 65 bars the spelling 'MINES' and this is the same company spelled
> 'MINING': **a correction that covers one spelling and not its variant.***

And in the same register, one freight brokerage colliding with Robinson
Rancheria appears **four times** — *"spacing variant"*, *"no punctuation"*,
*"intermediary for the same freight brokerage"*. Four rulings, one company, one
shape.

**Where it belongs.** This pass acted on it: R1 and R2 replace 33 of the
owner's 52 hand-maintained literals with two shape rules.

---

## R9. `status` says the ruling was processed; `outcome` says what it decided

Not new — `docs/ANCSA_OWNERSHIP_RULING.md` records it — but it is the single
most expensive reading error in the corpus and belongs in a rules file. Script
191's first pass read `status = SETTLED` as a confirmation on a row whose
`outcome` was `HOLD_OVER_OWNER` and whose text read *"HOLD — RETRACTION
REQUIRED"*. **Only `outcome = ENTITY` is a settled attribution.** A `HOLD` is
the strongest possible signal that a human must look. In the corpus: 2,687
HOLDs, 2,514 `HOLD` + 521 `HOLD_OVER_OWNER` outcomes.

---

# PART 3 — REPEAT OFFENDERS: where the rule did not stick

**2,922 of 5,500 distinct subjects (53%) were adjudicated more than once, and
2,213 of those were asked again in a *different review batch*.** That is not a
knowledge gap. It means the queue builder did not read where the first answer
was written.

**The fix is structural, and it is one line of discipline:** every queue
builder must exclude subjects already present in
`cedar_ruling_ledger_consolidated.csv` before writing a row. The ledger exists
and unions 39 files; nothing consumes it as a suppression list. One file,
`review/individual_native_queue_withdrawn_already_ruled_2026-08-26.csv`, shows
somebody discovering this by hand.

**The sticky-wrong-id offenders.** A wrong id that attracts many *unrelated*
firms is one bad row propagated, not many bad matches:

| id | firms wrongly attributed to it | what it is |
|---|---:|---|
| `TRBF-UNTHOR-00` | 5 — Suh'dutsing ×3, Weeminuche Construction | the four Suh'dutsing rows sit at **tier A**, method `hand` |
| `TRBF-TEMOAK-00` | 5 — all four Four Tribes firms | ruled Susanville |
| `AKNF-INPTBW-00-ARCSLO` | 3 — Koman, A+ Government Solutions, Ati Government Solutions (+ Santa Fe Indian School, Berkeley-Charleston-Dorchester) | no plausible token overlap with any of them |

`AKNF-INPTBW-00-ARCSLO` is the one to investigate first: it is attached to
firms sharing *no token at all* with Barrow or Arctic Slope, alongside
`cluster_v3` rows keying **Pennsylvania State University** to Lower Sioux and
**George Mason University** to Pribilof Islands. Those are not name-match
failures. They are the signature of a **row misalignment** in whatever built
`cluster_v3`, and no name guard can reach them.

---

# PART 4 — CONTRADICTIONS. Not resolved here.

**Ruling versus ruling: none.** Measured — **0 of 5,500 subjects** carry two
rulings naming two different entities. The 312 divergent subjects are all
`HOLD → ENTITY`, which is evidence arriving, not disagreement.

**Ruling versus table: 122, of which 32 name a different entity.** Listed in
`review/ruling_vs_table_contradictions_2026-08-26.csv`. Most are R4.

**Three that need the owner, and are listed rather than resolved:**

1. **Suh'dutsing — three answers in three places, and the wrong one publishes.**
   - `cedar_identifier_ledger_final.csv`: four UEI rows, `attribution_method =
     hand`, **tier A** → `TRBF-UNTHOR-00` (Ute Indian Tribe of the Uintah &
     Ouray). Plainly wrong.
   - the same ledger, CAGE rows: `elijah_ruling_redirect`, tier B →
     `TRBF-PTTRUT-00` (Paiute Indian Tribe of Utah). The owner's ruling.
   - `503.RESOLUTIONS` and `NATIVE_ENTITY_NUANCES.md`: `CNSF-PTTRUT-CD`, the
     **Cedar Band** constituent.

   The withdrawal of `TRBF-UNTHOR-00` is unambiguous and two independent owner
   rulings refute it. **The repoint target is not**: parent (`PTTRUT-00`) or
   constituent (`PTTRUT-CD`) is a granularity question only the owner should
   settle, exactly as FA-01 handled Bristol Bay — withdraw now, queue the
   repoint. Not done here because the withdrawal requires new
   `cedar_correction_register.csv` rows and that table is not this
   workstream's.

2. **Tribal colleges: `TCU-*` or `TRBF-*`?** `CONFEDERATED SALISH & KOOTENAI
   TRIBES` is ruled `TCU-SLSHKT-00` against a table saying `TRBF-CSKTFR-00`;
   `KEWEENAW BAY INDIAN COMMUNITY` is ruled `TCU-KWNWB1-00` against
   `TRBF-KWNWBY-00`. The college and the government share a name and a UEI in
   the source. The corpus does not say which the money belongs to.

3. **`CAGE:4CS13`** is ruled `Native Village of Eyak` in one owner inbox and
   the bare class `NATIVE` in another. Same ruler, two batches, two
   granularities.

**One correction is declared and not propagated, and the fix is one command.**
`354_correction_register.py` reports `F-DELAWARE-ALIAS` — two distinct
federally recognized tribes conflated by a CAGE legal-name alias — applied to
`entity_aliases.csv` but still live in `cedar_identifier_ledger_final.csv` and
`cedar_identifier_ledger_tiered.csv` (1 row each). `py -3
code/354_correction_register.py --apply` closes it. It was attempted this pass
and blocked by the sandbox classifier, so it is named here rather than left
silent.

---

# PART 5 — THE LEARNING TARGET

Rulings needed per 100 **publishable** identifications. Publishable means tier
A in `cedar_identifier_ledger_final.csv` — a row that actually carries a Native
entity into a shipping table.

| | 2026-09-01 baseline |
|---|---:|
| tier A identifications | 2,286 |
| tier X (permanent refutations) | 468 |
| **owner adjudication events** | **2,210** |
| **OWNER rulings per 100 tier-A ids** | **96.7** |
| all adjudicated subjects (owner + agent) per 100 | 240.6 |

**96.7 is essentially one human decision per publishable identification.** That
is casework, and it does not scale to a universe of 1,536 spine entities and
20,577 ledger rows.

**The counter-example is in the same corpus, and it is the whole argument.**
Two filter scripts the owner authored produced 4,656 exclusions —
**2,328 decisions per human act**. The two guards implemented this pass are the
same trade in miniature: two rules, 1,403 false resolutions removed, zero
correct resolutions lost. Roughly 33 of the owner's 52 hand-maintained place
literals are now redundant.

**What the next pass should report:** this table again, with the ruling count
held flat and the tier-A count risen. If both rise together, the project is
doing casework, not learning.
