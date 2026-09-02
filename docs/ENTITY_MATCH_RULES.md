# Entity match rules — what counts as evidence that two names are one entity

*Written 2026-09-01. Live doc. Enforced by `code/503_identity.py` and
`code/610_repair_generic_containment_links.py`. Read before writing any matcher.*

## The rule

> **An entity whose entire distinctive token set is generic may not win a match
> that rests only on the name.**

Three independent defects on 2026-09-01 were the same defect:

| where | what matched | why it fired |
|---|---|---|
| `entity_aliases.csv` | 104 `alias_type='brand'` rows, **every one a single token** — `cultural` → Southern Ute, `indigenous` → Delaware Nation, `colorado`, `broadband`, `advantage` | the alias was a fragment of a company name, not a name |
| `503_identity.py` loose path | `UMATILLA ELECTRIC COOPERATIVE` → Umatilla Tribe; `SENECA HOSE CO NO 1` → Seneca Nation; `TAOS VOLUNTEER FIRE DEPARTMENT` → Pueblo of Taos | the tribe's distinctive token is a place name every local body carries |
| `np_ein_entity_hub.csv` | **53 containment links**, incl. 41 onto `Council Native Corporation` and 5 onto `Council` (a real Alaska Native Village) | the entity's whole name is generic words |

## Why a denylist is not the fix

`cedar_domain.NAME_TRAPS` holds 51 words — `modoc`, `oneida`, `colorado`,
`advantage` — and did not hold `council`, `health` or `native`.

A denylist only refuses a word somebody already listed. It catches
`FOND DU LAC YACHT CLUB` and never `ENVISION GREATER FOND DU LAC`, because no
word in the second is on any list. Shard J measured this directly: the
`ADMIN_GEOGRAPHY` and `CIVIC_FORM` guards are word denylists and could not
reach the case that motivated them.

**Write the structural predicate, then use a denylist only for named exceptions.**

## Why state agreement is not the fix either

Tested on the `np_ein_entity_hub` case and it fails half of it:

- it kills all five `Council` links — Philadelphia, Brooklyn, none in Alaska ✓
- it kills **none** of the `Native Health` links — Winslow AZ and Fort Defiance
  AZ are both in Arizona, and so is Native Health ✗

Geography is a strong corroborator and a poor gate.

## FLAGGING IS NOT A CLAIM THAT THE ORGANISATION IS NOT NATIVE

This matters and it is easy to get wrong. Among the 53 refused links are
**Cook Inlet Tribal Council**, **International Indian Treaty Council**,
**National Indian Council on Aging**, **Indian Action Council of Northwestern
California**, **Northern California Indian Development Council** and
**Inter-Tribal Council of Louisiana**. Every one is a genuine Native
organisation.

The refusal says only: **this is not THAT entity.** It removes a wrong
attribution; it does not assert the organisation is non-Native, and it must
never be read that way downstream. Those organisations are now correctly
unkeyed, which is an honest state — `record_scope = unresolved` (ADR-010) — and
several of them plainly deserve a spine row of their own.

That is why the repair **flags and never deletes**. A deleted row asserts
nothing; a flagged row says what was refused and why, and can be reversed.

## "INDIAN" IS AMBIGUOUS AND CEDAR IS ONLY EVER ABOUT ONE MEANING

Caught in the same 53:

- `COUNCIL OF INDIAN ORTHODOX CHURCHES INC` — the Malankara Orthodox Church
- `NATIONAL COUNCIL OF ASIAN INDIAN ASSOCIATIONS INC` — the Indian diaspora
- `COUNCIL FOR WEST INDIAN PLANNING & DEVELOPMENT` — the Caribbean
- `INDIAN RIVER ESTATE PLANNING COUNCIL`, `CULTURAL COUNCIL OF INDIAN RIVER
  COUNTY` — a Florida county
- `INDIAN ORCHARD CITIZENS COUNCIL` — a Massachusetts neighbourhood

A matcher that treats `INDIAN` as a Native signal will key South Asian
diaspora organisations, Caribbean development bodies and Florida estate
planners into Indian Country. Treat the token as **no signal at all** unless
something else in the record carries the meaning.


## Rule 7 — where the record has an address, geography is a LADDER, not a gate

*Added 2026-09-01 by workstream INT-1, after ruling 711 held OSHA ITA
establishments (`review/employment_osha_711_ruled_2026-09-01.csv`). It is the
route that reliably settled them, and it is cheap to re-run.*

The 711 were all held on one reason: *"shares a distinctive token with a Cedar
property but no exact name+state match."* Pearl River Resort, 3,233 employees,
held on the token `pearl`. **Holding was right** — a shared token is the
Umatilla defect and rule 1 already refuses it. But the corroboration the hold
was waiting for was sitting unused in the same file: the OSHA 300A carries a
**street address and ZIP on 100% of rows** and an **EIN on 69%**, and the
2026-08-07 pass used none of the three.

So where a source record carries an address, rank the evidence and take the
highest rung that fires:

1. **An identifier.** EIN / UEI / CAGE against `cedar_identifier_ledger.csv`.
   Rule 4 already says this; it stands alone.
2. **Street address AND ZIP** both matching one row in the domain's own
   facility/property table. Two independent geographic signals agreeing on one
   site. This rung is strong enough to carry a **facility-level** key, not just
   an entity-level one — 54 of the 115 filings promoted came this way.
3. **The record's own words naming the entity** — every distinctive token of a
   spine name present, plus a governmental word, plus state agreement, plus
   uniqueness in that state.
4. **A brand match against the domain's curated table**, equal-token or the
   record's tokens as a strict SUPERSET of the facility's (the filer prints the
   brand plus a qualifier: `HARRAH'S SOUTHERN CALIFORNIA RINCON` against
   Cedar's `Harrah's Resort Southern California`). Require ≥2 distinctive
   tokens so a one-word brand can never win this way.
5. **ZIP + city** pointing at a facility of exactly one entity — the weakest
   rung, and it needs the veto below.

### The two things this rule exists to stop

**A ZIP is a strong corroborator and a poor gate.** Run ZIP-first and it
attributed `HARRAH'S SOUTHERN CALIFORNIA (RINCON)`, 1,400 employees, to **San
Pasqual** — ZIP 92082, Valley Center CA, holds Rincon's Harrah's *and* San
Pasqual's Valley View — and `Twenty Nine Palms Band of Mission Indians`, 720
employees, to **Augustine**, because ZIP 92236 holds both Coachella casinos. In
each case the establishment name PRINTS the right owner. Hence:

> **VETO: the record's own words outrank geography. If the text names or brands
> any entity other than the one the ZIP points at, the ZIP match is refused,
> not reconciled.**

The veto has to look for a *mention* without requiring a governmental word — a
bare token may never AWARD a match, but it may always BLOCK one. Blocking on
weak evidence is safe in a way awarding on it is not.

### An entity class that cannot hold the thing cannot win the match

Derive the allowed classes from the data, not from a list: the classes that
actually own a row in `gaming_facilities.csv` are `Federally recognized tribe`,
`Federal-level constituency entity` and `Federally recognized Alaska Native
Village`. Without that gate a token-subset test hands *Yakama Nation Legends
Casino Hotel* to the Yakama Nation **tribal school** and *Harrah's Cherokee* to
an individually Native-owned business called *Cherokee Enterprises Inc* —
because each beats the real tribe on uniqueness, the real tribe's spine name
carrying a token (*Confederated* Yakama, *Eastern* Cherokee) the filing does not
print. The codebook already called `entity_class` load-bearing as a guard; this
is what that means in practice.

### What it yielded, so the next pass can judge the cost

Of 711 establishments: **66 had already been promoted** by later passes, **344
were already ruled `blocked_commercial`**, and only **301 were genuinely open**
— the headline backlog was 58% stale. Of the 720 filings behind those 301,
**115 promoted** (54 on address+ZIP, 40 on brand, 12 on the filing naming the
government, 9 on ZIP+city) and **605 stayed `unresolved`**, which ADR-010 makes
an honest outcome. **Unresolved is the expected majority result** here, because
NAICS 7132/721120 is the gambling industry and most of it is not tribal.

## The checklist for any new matcher

1. **Compute the distinctive token set** — the name minus generic and
   organisational words. If it is empty, the name cannot support a name-only
   match. Stop.
2. **Say which evidence class the match rests on.** Exact normalized name and
   alias are strong; core-name is moderate; containment and token-subset are
   weak and need corroboration.
3. **Corroborate a weak match** with a second, independent signal: an
   identifier (UEI, CAGE, EIN), state agreement, or the organisation's own
   statement of affiliation.
4. **An identifier beats every name method.** Shard E linked seven ASRC
   subsidiaries — $5.43B, none sharing a token with "Arctic Slope" — through
   published CAGE codes. Prefer that route wherever it exists. But note
   `fpds_uei_cage_map.csv` carries the literal string `NAN` in `cage_code` on
   2,196 rows across 2,193 UEIs; join without excluding it and you fuse 2,193
   unrelated entities.
5. **Record the method and the evidence on the row**, so a later pass can
   re-judge without re-deriving.
6. **Unkeyed is an honest outcome.** ADR-010 makes `unresolved` a legitimate
   record scope. A wrong key is worse than no key, and the house rule stands:
   missing coverage is expandable, a wrong attribution is not.


---

# Rules 7–12 — added 2026-09-01 by `int-3-review`

*Derived while deciding the `review/` backlog (`docs/REVIEW_BACKLOG_RULINGS.md`,
`code/603_*`, `code/604_*`). Each one is here because it settled a class, not a
row.*

## 7. An entity's own official name is the arbiter of its own boundary

When a filed name and a Cedar entity are being compared, the question is not
"do they share tokens" but **"is every distinctive word in the filed name
accounted for by that entity's own official name?"** Take the union of
`canonical_name`, `fr_official_name` and `aliases` from the spine and subtract
it from the filed name's distinctive tokens. What is left is the **residue**,
and the residue decides:

| residue | meaning | disposition |
|---|---|---|
| empty | the same entity | ACCEPT |
| place or spelling variant — `PINE, RIDGE`; `LOUSIANA`; `RESERVATI` | still the entity | ACCEPT |
| an institution form — `SCHOOL`, `AUTHORITY`, `COLLEGE`, `UTILITY`, `HOUSING` | a body the nation created | HOLD |
| four or more distinctive words | a different name | HOLD |

**Why this and not set equality.** Cedar's canonical names are deliberately
short (`Rosebud` for the Rosebud Sioux Tribe), so requiring equality holds 280
correct rows worth $23.4B. **Why this and not containment.** Containment in the
other direction accepts `TURTLE MOUNTAIN COMMUNITY COLLEGE` as the Turtle
Mountain Band, `MENOMINEE INDIAN SCHOOL DISTRICT` as the Menominee Tribe and
`NAVAJO TRIBAL UTILITY AUTHORITY` as the Navajo Nation. A tribal college, a
school district and a utility are real entities and they are not the nation.

**The residue cap is empirical, not chosen.** Over 281 accepts, the largest
residue on a correct one is three (`NAMBE PUEBLO GOVERNOR'S OFFICE`), and
exactly one wrong accept carried no institution-form word at all:
`LEECH LAKE BAND OF OJIBWE NATURAL WILD RICE` → the Band, residue
`NATURAL, OJIBWE, RICE, WILD`. No denylist could have caught it — `RICE` is not
an organisational form — and the structural fact that it adds four distinctive
words is what separates it.

## 8. A ruled METHOD is not a positive ruling, and an agent ruling may not mint tier A

Already true of `attribution_method` (START_HERE 1b: all 317 `elijah_ruling`
EIN rows are tier X, NEGATIVE). Extended here to propagation:
`propagated_from_agent_ruling` may not carry a row to tier A. Tier A is an
**identifier** grade. Measured: of 1,223 rows queued for tier B → tier A
promotion, **not one carries an identifier**, so the correct number of
promotions is zero.

## 9. Containment never accepts alone

Containment and token-subset are WEAK classes (checklist step 2) and need a
second independent signal. With no corroborator, containment is REFUSED where a
link would be created and HELD where one already exists at tier B. This is the
class that produced 41 wrong links onto `Council Native Corporation`.

## 10. An alias needs three independent observations

One Federal Register notice spelling a name a particular way is a typesetter.
Two is often the same notice reissued. **Three or more independent notices is
corroboration.** Calibration: the earlier recognition-alias pass rejected
**76 of 228** proposals on review — a 33% error rate, far too high to
auto-apply at n=1. Applied to 1,049 NAGPRA proposals: 211 accept, 168 hold,
670 refuse.

## 11. A DECLARED PARENT UEI outranks a name, and 20 observations is the floor

`fpds_uei_edges.csv` carries parent/child UEI relationships **the registrant
filed about itself**. That is the identifier evidence rule 4 asks for and it is
already on disk — no browser needed. Two thresholds make it usable:

- **An edge observed 20+ times is ownership.** Below that it is a **joint
  venture or a co-award**, and a JV genuinely has two parents. Measured: all 72
  ledger rows whose declared parent disagrees on a sub-20 edge are JVs
  (`WHH Nisqually Federal Services` declares TDX Quality exactly **once**),
  while every real ownership case is observed 100+ times.
- **The parent's tier does not transfer.** A link resolved through a tier-A
  parent is proposed at **tier B**: the parent's tier describes the parent's
  own link. A tier is inherited from the source row, never assigned by the
  consumer.

## 12. When a declared parent contradicts an attribution, suspect the PARENT row first

The most valuable rule here, and the least obvious. Sweeping every tier A/B UEI
in the ledger against its declared parent produced **129 contradictions on
$2.82B** — a number that reads like 129 wrong attributions and is not:

- **54 rows, $2.39B — the PARENT row is the defect.** Every Bowhead subsidiary
  is correctly keyed to `ANVC-KPVKPT-00`, Ukpeaġvik Iñupiat Corporation, while
  **the corporation's own UEI is keyed to `AKNF-INPTAS-00-ARCSLO`, the Native
  Village**. `ANCSA_OWNERSHIP_RULING` RULE 2 and
  `cedar_domain.village_government_owns_an_anc()` (always `False`) say that
  link cannot exist. One bad parent row makes 54 good child rows look wrong.
  Same shape at Olgoonik/Wainwright and St. George Tanaq/Pribilof. This is the
  known `ALASKA_VILLAGE_GOVERNMENT_VS_VILLAGE_CORPORATION` family (334 defects,
  $24.52B) reached by an independent route.
- **72 rows, $0.40B — rule 11's JV floor.** Ledger stands.
- **3 rows, $0.03B — genuine.** The only non-ANCSA one:
  `Tikigaq Technology Services` keyed to **Paiute of Utah**
  (`TRBF-PTTRUT-00`) while declaring **TIKIGAQ CORPORATION** (Point Hope,
  Alaska) as its parent **258 times**.

**So a contradiction sweep must classify before it acts.** Acting on the raw
129 would have repointed 126 correct rows to chase 3 wrong ones.
