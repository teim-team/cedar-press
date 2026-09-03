# The nonprofit place-name collision, measured - `code/1155`, 2026-09-02

*Every figure below was produced by a named command on the live files that day.
Where a figure is a hand judgement it says so, names the sample, the seed and
the size, and the labels are on disk. Revised the same day after an independent
hand-check found a false refusal; what changed and why is section 10.*

**Commands**

```
py -3 code/1155_np_placename_precision.py sample     # seeded population sample
py -3 code/1155_np_placename_precision.py report     # every number in this doc
py -3 code/1155_np_placename_precision.py apply      # the demotion (reversible)
py -3 code/1155_np_placename_precision.py audit      # sample the APPLIED set
py -3 code/1155_np_placename_precision.py codebook   # register the new columns
py -3 code/1155_np_placename_precision.py verify     # 10 invariants, exit 1 on breach
py -3 code/1155_np_placename_precision.py selftest   # each one injected, RED asserted
```

`verify` was run BEFORE `apply` and returned exit 1 on I1a, I1b and I2 - it
fails when the work has not landed, which is the only thing that makes its green
run afterwards mean anything. `selftest` re-proves I1a/I1b/I2/I5b, I6 and I7 by
injecting each violation into the live files, asserting RED and the invariant
naming itself, restoring, and asserting GREEN.

---

## 1. The headline, and it is bad

**Of the 1,423 `np_orgs.csv` rows carrying both a `tribe_id` and a `cedar_uid`
- the LINKED numerator behind the published 11.15% - a stratum-weighted 78.8%
name the wrong entity.**

Measured on a seeded random sample of 210 of those 1,423, hand-classified from
the record alone (IRS BMF name, city, state, NTEE, and the keyed spine entity's
own name and state). Seed `20260902`; sample
`review/np_placename_precision_sample_2026-09-02.csv`; labels and per-row
reasons `review/np_placename_precision_labels_2026-09-02.csv`; the stratum sizes
as drawn `review/np_placename_precision_strata_2026-09-02.json`.

| stratum | population | sampled | TRUE | FALSE | UNKNOWN | strict precision | upper bound |
|---|---:|---:|---:|---:|---:|---:|---:|
| `key_review_disposition = SUPPORTED` - **these ship a key** | 888 | 150 | 38 | 105 | 7 | **25.3%** | 30.0% |
| everything already masked | 535 | 60 | 3 | 56 | 1 | 5.0% | 6.7% |
| **weighted over all 1,423** | 1,423 | 210 | | | | **17.7% TRUE, 78.8% FALSE, 3.5% UNKNOWN** | |

**Strict precision** counts only rows the record positively settles as the keyed
nation or one of its organs. **Upper bound** hands every UNKNOWN to the
attribution. The honest reading of the shipped keys is *between 25% and 30%
correct*.

The weighting is against the stratum sizes **as drawn**, not as they stand now.
`apply` moves rows between strata, and re-weighting against today's sizes turns
17.7% into 13.5% while answering a different question - see section 11.

### The rubric, stated so the next pass can disagree with it

- **TRUE** - the keyed Cedar entity is the right Native entity: the organisation
  IS that nation, or is plainly an organ, enterprise, program, congregation or
  citizens' body OF that nation, sited in that nation's own community.
- **FALSE** - the shared word is doing other work in this record: a county, a
  town, a lake or river, a landform, a surname, the South-Asian or Caribbean
  sense of *Indian*, or a **different Native entity** from the one keyed.
- **UNKNOWN** - the record genuinely does not settle it.

**21 of the 161 FALSE rows are Native organisations keyed to the wrong entity**
(`native_wrong_entity = 1` in the labels file) - `NATIVE HAWAIIAN EDUCATION
ASSOCIATION` to *Hawaiian Native Corporation*, `LAS VEGAS INDIAN CENTER` to the
Las Vegas Paiute Tribe, `ST AUGUSTINE INDIAN MISSION` (Winnebago NE) to the
**Augustine** Band of Cahuilla Indians, California, on the token `AUGUSTINE`.
A refusal on those rows withdraws a key and asserts nothing about Native status.

---

## 2. Why the existing guard could not reach it: state agreement argues the wrong way

`docs/ENTITY_MATCH_RULES.md` already warns that state agreement is a strong
corroborator and a poor gate. On this failure mode it is worse than poor.

**A town named after a nation is almost always in that nation's own state.** So
the collision passes the state test by construction, and `code/1101`'s
`HELD_STATE_DISAGREES` - which caught 461 rows and was the right rule for a
different family - cannot see it. Every one of these reads
`keyed_state_agreement = Y`, `key_review_disposition = SUPPORTED`, and most read
`disposition = NATIVE_VERIFIED_STRICT`, the highest-confidence bucket:

```
COQUILLE CHESS CLUB                Coquille  OR   Coquille Indian Tribe    NATIVE_VERIFIED_STRICT
CHEHALIS BALLET CENTER             Chehalis  WA   Chehalis Tribe           NATIVE_VERIFIED_STRICT
COWLITZ OFF LEASH ASSOCIATION      Kelso     WA   Cowlitz Tribe            NATIVE_VERIFIED_STRICT
PENOBSCOT FLY FISHERS              Brewer    ME   Penobscot Nation         NATIVE_VERIFIED_STRICT
SENECA ZOOLOGICAL SOCIETY          Rochester NY   Seneca Nation            SUPPORTED
SHAKOPEE BAND BOOSTERS             Shakopee  MN   Shakopee Mdewakanton     SUPPORTED
MILLE LACS COUNTY SEARCH & RESCUE  Milaca    MN   Mille Lacs Band          SUPPORTED
```

`SHAKOPEE BAND BOOSTERS` is the whole problem in three words: a high-school
concert band, keyed to a Sioux community, because a nation is a *band*.

The exposure is concentrated. Six entities carry a third of the 1,423: Seneca
121, Crow 97, Fond du Lac 87, Pueblo of Laguna 72, Rosebud 50, Shakopee 46.

---

## 3. The discriminator

Not a denylist of tribe names - a test of what the shared token is **doing in
this particular record**, computed from data Cedar already holds.

**P1 - the matched token is this filer's own postal place.** The nation's
distinctive token(s) appear in the organisation's IRS BMF `city`. If the word
that matched is the name of the town the filer sits in, the word is an address
in that record. **349 rows.**

**P2 - the matched token is qualified as geography in the name itself.** The
token is immediately followed by a US geographic-form noun - `COUNTY`, `FALLS`,
`LAKE`, `VALLEY`, `BEACH`, `RIVER`, 50 in all - **that the keyed entity's own
official name does not itself carry**. `SENECA COUNTY` is a county;
`TURTLE MOUNTAIN` is a nation. That last clause is not decoration: without it P2
refused `TURTLE MOUNTAIN RECOVERY CENTER` in Belcourt ND, the band's own seat.
**168 rows.**

### Three vetoes, because a refusal is a claim too

Blocking on weak evidence is safe in a way awarding on it is not - and the
reverse has to be true as well. A refusal is refused where:

1. **The organisation's own name carries Native-purpose language.** Rule 7: the
   record's own words outrank geography.
2. **An INDEPENDENT evidence family names this EIN** - a Single Audit filed
   under `entity_type = tribal`, an EIN-UEI federal-assistance bridge row, a
   Schedule I grant relationship. **`np_ein_entity_hub` is deliberately not
   used**: it names 1,416 of the 1,423 keyed EINs, so it is the same name
   matcher seen a second time, not a second witness. The genuinely independent
   families are thin - `fac_tribal_single_audits` reaches 50 of the 1,423,
   Schedule I 149 + 69, the UEI bridge 19, `grantmaker_funding_flows` **0**.
3. **The town is the nation's own seat** - section 4.

### Scored against the hand labels

On the 202 labelled rows that are not UNKNOWN:

| | count |
|---|---:|
| caught a hand-FALSE | 80 |
| **hit a hand-TRUE (the cost)** | **0** |
| missed a hand-FALSE | 81 |
| correctly left a TRUE alone | 41 |

**Scored-set precision: 0 errors in 80. By the rule of three that is >= 96.2% at
95% confidence** - and it is a floor, not 100%; zero observed errors in 80 rows
does not mean zero errors. **Recall over hand-FALSE 49.7%.**

The vetoes bought that precision: before them the same predicate scored 83
caught / **4 wrong** (95.4%). Trading four catches for four errors is the right
trade, because a wrong refusal destroys a correct claim and this project's house
rule is that a wrong attribution is not expandable.

**Recall is deliberately half.** The 81 it misses are three other families, each
needing its own predicate rather than a loosening of this one: surnames
(`CROW LUNA FOUNDATION`, `POARCH FAMILY FOUNDATION`), the wrong-Native-entity
family (section 1), and place names with no geographic-form word and no city
match (`SEMINOLE COON HUNTERS CLUB`, Roseland VA).

---

## 4. The seat veto, and the blind spot that a hand-check found

Zuni NM, Siletz OR, Crow Agency MT and Kasaan AK are towns named after a nation
**because the nation is there**. P1 must not fire in a nation's own community.

**The veto gates P1 only.** P1 is a geographic inference and a seat is
geographic evidence against it; P2 reads the organisation's OWN NAME, and rule 7
says the record's own words outrank geography in both directions. Measured:
gating P2 as well preserved `COWLITZ VALLEY LODGE 530`, a fraternal lodge whose
own name says Cowlitz *Valley*, purely because the tribe's BIA address is in the
same town - and it suppressed six other correct catches
(`SHINNECOCK HILLS GOLF CLUB`, three `MILLE LACS LAKE` organisations,
`COQUILLE VALLEY GARDEN CLUB`, `HOPE HOUSE OF CHEROKEE COUNTY`).

### Where the seat comes from

| route | what it is |
|---|---|
| `fac_tribal_single_audits` | where a nation's own government files its Single Audit |
| `fac_native_nontribal_single_audits` | bodies too small for the tribal-audit table |
| `gaming_facilities` | its casinos |
| BIA Tribal Leaders Directory | the address BIA publishes for every federally recognized tribe |
| the entity CLASS | a village government sits at the village it names |

The first three take a **dominance test**: a city is the seat only if it holds
at least half that entity's anchored observations. Two stray 2021-22 Chehalis
Tribal Housing Authority filings that print `CHEHALIS` where fifteen other years
print `OAKVILLE` would otherwise have vetoed 22 correct refusals.

The BIA directory carries no Cedar key, so it is joined by **exact normalised
name** against the spine's own published names and used only on a **unique**
match: **540 of 583 unique, 42 ambiguous, 1 unmatched** - all discarded but the
540. A name join may do this because it only ever BLOCKS a refusal.

`cedar_entity_spine.city` cannot serve at all: it is blank on **all 238** keyed
entities.

### The blind spot, and the class rule that closes it

All four evidential routes are **filings or a directory**, and a village of
sixty people files no Single Audit, runs no casino, and gives BIA a P.O. box in
the nearest town. The BIA directory's address for the Organized Village of
Kasaan is **Ketchikan** - 30 miles and a ferry away.

So the fifth route is structural rather than evidential: **an entity class that
IS a place.** A `Federally recognized Alaska Native Village` sits at the village
it is named for; that is what the class means, and no filing is needed to
establish it.

**Guarded by state agreement**, without which `EAGLE BUTTE LAKOTA CHAPEL` in
Eagle Butte, South Dakota reads as sitting in the Native Village of Eagle,
**Alaska**, and a plainly wrong key would be preserved.

**Deliberately NOT extended to `Federally recognized tribe`.** Measured: that
would veto **114 of the refusals**, because Coquille OR, Chehalis WA, Shakopee
MN, Flandreau SD, Lummi Island WA, Quinault WA, Seneca Falls NY and West Seneca
NY all bear a nation's name and none is that nation's seat. **The class
distinction is load-bearing**, and it is the reason the fix had to be scoped
rather than generalised.

---

## 5. What was written

**517 of 1,423 live keys fire the predicate (36.3%).** 349 on P1, 168 on P2.
297 read `SUPPORTED` before this pass - keys that ship - and 220 already carried
another pass's verdict.

Flag and never delete. No row was removed; no `cedar_uid` was minted, reused or
erased; `np_orgs.csv` is 12,764 rows before and after, and a column-by-column
diff against the backup shows **only `key_review_disposition` and
`key_review_basis` changed**, plus three new columns.

| column | on how many | what it says |
|---|---:|---|
| `placename_refusal_rung` | 517 | `P1_TOKEN_IS_THE_FILERS_OWN_CITY` or `P2_TOKEN_QUALIFIED_AS_GEOGRAPHY_IN_THE_NAME` |
| `placename_refusal_basis` | 517 | the token, the evidence, and that this is not a Native-status finding |
| `placename_refusal_date` | 517 | `2026-09-02` |
| `key_review_disposition` | **297** | demoted to `REFUSED_PLACE_NAME_IS_THE_ADDRESS` |

**A verdict another pass already recorded is evidence and was left standing.**
The 220 rows already reading `HELD_STATE_DISAGREES` keep `code/1101`'s finding -
it is true and it already MASKs - and carry the refusal in its own columns
instead. Only `SUPPORTED` was overwritten.

**`apply` is reversible.** When the predicate is tightened, a row it no longer
refuses LOSES the refusal and returns to `SUPPORTED`; invariant I7 fails if any
refusal outlives the rule behind it. That path is not theoretical - it is how
the two false refusals in section 10 were undone.

### The cross-lane dependency, stated loudly

`code/cedar_publication.py` is **deny-by-default**: a `key_review_disposition`
value its vocabulary has never seen **WITHHOLDS the whole row**. So one line was
added to `BLOCKED_STATES["key_review_disposition"]`:

```python
"REFUSED_PLACE_NAME_IS_THE_ADDRESS": MASK,
```

MASK is what the other three refusal values already do - the IRS record is real
and ships, the contested key does not, and `MASK_COLS` already blanks
`cedar_uid`, `tribe_id`, `tribe_canonical_name`, `cedar_spine_entity_id`,
`cedar_spine_canonical_name` and `cedar_link_key` for this column.

**If that line is dropped, 297 real IRS filings vanish from the export instead
of their keys being masked.** Invariant **I6** reads `cedar_publication.py` and
fails if the entry is gone; `selftest` proves I6 fires by deleting it. That is
the only edit this pass made outside the nonprofits lane.

---

## 6. The after-number, and it FALLS

**Published attributions on the nonprofits flagship: 851 -> 555. 6.71% -> 4.37%
of the 12,689 shipped rows.**

Measured by reproducing `cedar_publication`'s gate against
`data/clean/np_orgs.csv` - the pre-apply simulation returned 851, exactly the
`cedar_uid` fill of the live `dist/customer/nonprofits.csv`, which is why the
after-figure can be trusted. The export itself is rebuilt by `code/1137`, not
here.

**This is the correct outcome and it is not an improvement in any number.** 296
attributions were withdrawn because they were wrong. Nothing was gained; false
claims were removed.

### The ratchet does not move, and that is a defect in the ratchet

`docs/LINKAGE_COVERAGE.md` defines LINKED as
`tribe_id <> '' AND cedar_uid <> ''` on `data/clean/np_orgs.csv`, and
`code/62_no_regression_check.py` ratchets it. **Both key columns are untouched
by this pass - flag, never delete - so LINKED stays at 1,423 / 11.15% while the
shipped attribution rate falls to 4.37%.** Confirmed against
`1139_linkage_coverage.metrics()`: `linkage_nonprofits_bp 1115`,
`linkage_nonprofits_rows 1423`, unmoved.

So the standing measurement **cannot see a withdrawn claim**. It reports 11.15%
for a table that shipped 6.71% and now ships 4.37%. Three readings of one
dataset, and the ratcheted one is the least true. This is not a request to
re-baseline anything - the raw metric is stable and no floor was breached. It is
a request to **add the publication mask to the LINKED predicate**:

```
LINKED := tribe_id <> '' AND cedar_uid <> ''
          AND key_review_disposition IN ('SUPPORTED', '')
          AND disposition NOT IN ('NATIVE_PROPOSED_AWAITING_OWNER_RULING',
                                  'CONFLICT_EXCLUDED_AND_RULED_NATIVE')
```

`1139_linkage_coverage.py` and `62` are not this pass's to edit. The measurement
is here; the decision is the integrator's.

---

## 7. What in the brief did not reproduce

- **"the organisation's own 990 language."** There is none on disk for these
  EINs. A header sweep of every non-backup CSV in `data/clean` and `data/spine`
  for `mission` / `activity` / `purpose` / `description` / `narrative` found no
  990 mission or program-service text for `np_orgs` filers. `np_financials.csv`
  is financial fields only. The discriminator uses the BMF **name**, **city**,
  **state** and **NTEE** instead, and NTEE proved far weaker than the name -
  `A6E0` on `CHEHALIS BALLET CENTER` is diagnostic, but 3,000 rows carry no NTEE.
- **`grantmaker_funding_flows` as a corroborator.** It names **0** of the 1,423
  keyed EINs.
- **`np_ein_entity_hub` as a corroborator.** It names **1,416 of 1,423** -
  99.5%. It is the same matcher, not a witness; using it would veto everything.

---

## 8. Gate state after the pass, stated in full

- **`1155 verify` - PASS**, 10 invariants (I1a I1b I2 I3 I4a I4b I5a I5b I6 I7).
  Run BEFORE `apply` it exits 1 on I1a, I1b and I2.
- **`selftest` - PASS.** Four violations injected into the live files, each went
  RED and named itself, each restored, GREEN reasserted.
- **`py -3 code/293_lint_bug_classes.py` - `code/1155` contributes ZERO findings**
  across all seven classes. The repo total rose 148 to 164 in the same window;
  every new finding names another script (`1060`, `1077`, `1085`, `1086`, `846`,
  `852`, `873`, `1030`, `1031`, `1111`, `980`, `992`, `1011`, `30`, `518`, `870`,
  `99`). Not this pass's, and named here rather than stepped around.
- **`1136_control_byte_gate verify` - PASS**, 1,020 files, 0 control bytes. The
  script is pure ASCII.
- **`cedar_publication verify` - PASS**, 0 problems.
- **`846_session_audit` - 29/30.** The one FAIL is `1137 verify rc=1`: four
  datasets are stale against `data/clean`, and three are not this pass's -
  `federal-register`, `nagpra`, `nest`, plus `nonprofits`. `dist/` and
  `code/1137` are outside this lane, so the export was not rebuilt. Remediation
  for the nonprofits quarter is
  `py -3 code/1137_customer_dataset_combine.py build nonprofits`; until it runs,
  the delivered spreadsheet still carries the 851.
- **`62_no_regression_check`** exit 0; the linkage metrics are unmoved and no
  floor was breached. It reports many unrelated regressions from other lanes.

---

## 9. Applied-set precision, which is NOT the scored-set precision

A reviewer will ask for both, and the distinction is the difference between a
measurement and an extrapolation.

- **Scored-set** - the 80 refusals that fall inside the original 210-row
  population sample. A fair random subsample of the POPULATION. **0 errors in
  80, >= 96.2% at 95% confidence.**
- **Applied-set** - the 297 rows whose claim this pass actually WITHDREW. These
  are the ones where a wrong refusal costs something; the other 220 were masked
  either way. This set gets its **own** random sample: seed `202609022`, 60 of
  297, in `review/np_placename_precision_applied_audit_2026-09-02.csv` with
  labels and per-row reasons beside it. **0 wrong in 60, >= 95.0% at 95%
  confidence.**

Neither figure is 100%. Zero observed errors in n rows bounds the error rate at
about 3/n; both numbers above are floors and are printed by `report` as floors.

**The extrapolation the coordinator flagged was real and it has now been
closed.** The scored figure was measured on 80 rows and quoted about 293;
`KASAAN HAIDA HERITAGE FOUNDATION` sat outside those 80. The applied set now has
its own sample rather than borrowing one.

---

## 10. The false refusal, what it pointed at, and what the fix cost

An independent hand-check of four of the 293 found one wrong:

```
KASAAN HAIDA HERITAGE FOUNDATION   city KASAAN  state AK   keyed Kasaan
  refused P1_TOKEN_IS_THE_FILERS_OWN_CITY
```

Kasaan, Alaska is the seat of the Organized Village of Kasaan. The diagnosis was
right and it was about a class, not a row: **the seat veto's evidence was
federal filings, and small Alaska Native villages file none.**

Two things were changed, and both were measured across the whole 1,423 before
adoption rather than patched at the row:

| change | rows it moved | verdict |
|---|---:|---|
| BIA Tribal Leaders Directory added as a seat source | **1** refusal withdrawn: `WHITE EARTH REDISCOVERY CENTER`, White Earth MN - the nation's own seat | a second false refusal nobody had found |
| village-class seat rule, state-guarded | **1** refusal withdrawn: `KASAAN HAIDA HERITAGE FOUNDATION` | the reported row |
| seat veto restricted to P1 | **6** new correct catches | `SHINNECOCK HILLS GOLF CLUB`, three `MILLE LACS LAKE` bodies, `COQUILLE VALLEY GARDEN CLUB`, `HOPE HOUSE OF CHEROKEE COUNTY` |

Net: 513 refusals to 517; 293 demotions to 297. **The measured exposure of the
class the hand-check identified is 1 of 293** - the mechanism is real, the
population is small, because only 45 of the 1,423 live keys are village
governments at all and only 5 of those sit in their own named village.

### The name-level veto was measured and REJECTED

The second suggestion - veto where the organisation's own name carries an
unambiguous Native identifier such as `HAIDA`, distinct from a place word - was
built and measured, and it does not pay.

The diagnosis was exactly right about the cause: `NATIVE_PURPOSE_RE` looks for
**purpose** words (`TRIBE`, `NATION`, `BAND`, `NATIVE`, `INDIAN`) and `HAIDA` is
a **people** name, so it was never going to fire.

Building the people vocabulary structurally: take every distinctive token any
Cedar entity publishes about itself (1,759), subtract every token appearing in
any US place name in `geo_place_county_crosswalk.csv` (42,650 places), leaving
1,045 candidates. **Applied to the 293, that vetoes 48 - and 47 of the 48 are
wrong**, because Cedar's register contains organisations, so `EDUCATION`,
`FRIENDS`, `SENIOR`, `WELLNESS`, `AGRICULTURAL` and `UNITED` all qualify as
"tokens a Native entity publishes that are not US place names".

Tightening with a frequency threshold against a corpus of 26,974 distinct
ordinary American organisation names
(`np_schedule_i_grants.recipient_name_as_filed`) does not separate them either:

```
HAIDA 19   TLINGIT 19   WAMPANOAG 7   OJIBWE 6   ALEUT 5   INUPIAT 2   IROQUOIS 1
DUCK  7    SWIM    5    ORDER     4   SUSTAIN 3
```

Any threshold admitting `HAIDA` at 19 also admits `DUCK`, `SWIM`, `ORDER` and
`SUSTAIN`, which would wrongly save `SENECA LAKE DUCK HUNTERS ASSOCIATION`,
`SHAKOPEE SWIM BOOSTERS`, `COLVILLE VALLEY SWIM CLUB`,
`SENECA LAKE ORDER OF BREWERS` and `SUSTAIN FOND DU LAC`. **Net: gains 1, loses
5.**

A tighter variant - the extra token must belong to the keyed entity's own
declared family - catches Kasaan (`HAIDA` from the Central Council of the
Tlingit and Haida Indian Tribes) but only via a loose handle-chain expansion
that also pulls in `CRAIG`, `DOUGLAS`, `CENTRAL` and `ISLAND`, and it wrongly
saves `MILLE LACS LAKE HISTORICAL SOCIETY` on the token `LAKE`.

**So the name veto is not adopted.** The seat route saves the same row at zero
measured cost, and shipping a vocabulary that trades one save for five losses to
reach it would be the denylist mistake `docs/ENTITY_MATCH_RULES.md` exists to
prevent. Recorded here so the next pass does not rebuild it.

---

## 11. Three things this pass got wrong first

Recorded because they are this repo's own bug class.

**The weighted precision drifted 17.7% to 13.5% on a re-run.** `report` was
re-weighting the sample against *today's* stratum sizes, and `apply` had just
moved 293 rows out of SUPPORTED. A number that was produced, was plausible, and
was about something else - `docs/AGENT_FIELD_GUIDE.md` section 3 exactly. The
draw-time populations are now persisted by `sample` and `report` prints
UNMEASURED rather than a number if that file is absent.

**The first predicate refused four correct rows**, all in a nation's own town -
`ZUNI CHRISTIAN REFORMED CHURCH`, `SILETZ GOSPEL TABERNACLE`,
`CROW LUTHERAN CHURCH`, `TURTLE MOUNTAIN RECOVERY CENTER`. Found by scoring the
predicate against the hand labels, which is the only reason they were found.

**The seat veto then missed two more**, in Kasaan AK and White Earth MN, and the
scored sample could not see either. Found by an independent hand-check and by
widening the evidence and re-measuring. **A precision measured on 80 rows and
quoted about 293 is an extrapolation**, and the fix is not a better
extrapolation but a second sample drawn from the set the claim is about.

### The caveat that remains, and it is not small

**The same judgement drew the rule and the labels.** Both samples were
hand-classified by the agent that wrote the predicate, so the two are not
independent, and an error in how I read a record shows up identically in the
rule and in its score. The coordinator's four-row independent check is worth
more per row than either sample: it found the one thing both of mine missed.
**Treat >= 96.2% and >= 95.0% as this pass's own estimate of its own work.**

---

## 12. Left open

- **~604 wrong keys this predicate does not reach.** 78.8% of 1,423 is ~1,121
  estimated wrong; 517 are refused. Three families, section 3.
- **The 220 rows carrying two refusal reasons.** Masked either way; both
  `placename_refusal_rung` and `key_review_disposition` are on the row if a
  later pass wants one verdict.
- **`disposition = NATIVE_VERIFIED_STRICT` on 139 refused rows.** The
  Native/not-Native question and the which-entity question are different columns
  and this pass answered only the second. But that bucket contains
  `COQUILLE CHESS CLUB` at one edge and, until today, refused
  `KASAAN HAIDA HERITAGE FOUNDATION` at the other - a label that is wrong in
  both directions at once is worth the owner re-reading.
