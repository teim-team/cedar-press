# The corroboration layer — how many INDEPENDENT observers stand behind a fact

*Built 2026-09-02. Code: `code/1118_corroboration_layer.py`. Read with
`docs/ASSERTION_LAYER.md` (which owns entity-grade facts and the resolution
rules) and `docs/ENTITY_MATCH_RULES.md` (which owns whether two names are one
entity — untouched here).*

```
py -3 code/1118_corroboration_layer.py build
py -3 code/1118_corroboration_layer.py verify     # exits 1 on breach
py -3 code/1118_corroboration_layer.py selftest   # proves every C fires
```

**Read-only against every dataset. No table was edited in place. Nothing was
committed.** What should merge is in *Merge proposals* at the bottom.

---

## The headline number

**320 of 4,432 facts (7.2%) reach two or more independent evidence families.**

| independent families | facts | |
|---:|---:|---|
| **0** | 1,399 | 31.6% — supported only by Cedar agreeing with itself, or by an unattributed row |
| **1** | 2,713 | 61.2% |
| **2** | 315 | 7.1% |
| **3** | 5 | 0.1% |

Read the zero row before the two row. **A third of the facts examined have no
voting evidence family at all** — not one weak source, *none*. That is not a
new defect this pass created; it is what was always there, and the layer's
main contribution is that it is now a number instead of a feeling.

**This is NOT the assertion layer's 8,975 moving.** `code/510_assertions.py`
owns entity-grade facts and its own count is unchanged — re-measured today
from `data/clean/cedar_resolved_facts.csv`: **9,204 single-valued facts, 5,445
at zero families, 3,757 at one, 2 at two**. This layer measures a different
universe one level out — the shipping datasets — and the two must not be
added together. See *Merge proposals*.

---

## The definition everything turns on

An **evidence family** is a class of OBSERVER, not a file, a row or a URL.

| family | what it is | votes |
|---|---|:-:|
| `federal_transactional` | FPDS / FSRS / USAspending: the government recording that a transaction happened, with the identifiers used on it | ✔ |
| `federal_registry` | SAM, the Federal Register tribal list, NIGC, IRS BMF, BIE, IHS, SBA | ✔ |
| `audited_filing` | ANCSA AS 45.55.139 report, Form 990 return, Single Audit, SEC filing | ✔ |
| `entity_self_published` | the entity's own site, capability statement, company list, newsletter, release | ✔ |
| `state_registry` | a state regulator's own record | ✔ |
| `court_record` | IBIA / IBLA / a docket | ✔ |
| `human_ruling` | an owner ruling with a recorded reason | ✔ |
| **`third_party_press`** | **an eighth family this pass had to add** — see below | ✔ |
| `cedar_inference` | a name match, a containment link, `cluster_v3`, a resolver output | ✘ |
| `compiled_directory` | Casino City Press, legacy CICD, a vendor property list | ✘ |
| `unattributed` | no provenance was ever recorded | ✘ |

### Three arguments with the taxonomy, and how each was settled

**1. The seven families had nowhere honest to put a trade journal.** 59 deals
cite `Trade press`, and both available homes were lies: `entity_self_published`
claims a reporter is the entity, and dropping it claims a reporter is nobody.
`third_party_press` is added, and it **votes** — a reporter is a real
independent observer. What it may never do is corroborate a press release it
is reprinting, and R-A catches that automatically whenever the two citations
resolve to one URL.

**2. Casino City Press does not vote.** `gaming_facilities.csv` is built on
`casino_city_press | tribal_property_list | votingpatterns_canonical` — vendor
directories, compiled, provenance unknown, and licence-constrained (they may
be read for QA and never published). `data/spine/cedar_source_registry.csv`
already carries `independence_is_unverified = 1` on `LR_CICD` for exactly this
reason. Applying the same ruling to the gaming directories is consistency, not
a new judgement. **Consequence: 681 of 786 gaming facilities have zero voting
families for their tribal affiliation.**

**3. A member association's directory is the member speaking.** `shard-H` in
NEST is `nhoassociation.org/members.html`. It is folded into
`entity_self_published` rather than given a family, because a members list
reports what members submitted about themselves.

---

## The three rules that stop an echo counting as a second source

**R-A — one upstream document is one observation.** Every observation carries
an `upstream_key`; two sharing one collapse before families are counted. The
key is normalised, so `web.archive.org/web/<stamp>/<url>` has the same
upstream as the live `<url>`, because it **is** that page.

> Measured cost of not doing this: **220 of 651 two-source deals cite the same
> URL twice.**

**R-B — one publisher is one observer** unless the two documents are of
different kinds. Two paths on one host are one observer.

> **362 further deals are two paths on one host**, and 16 more are two
> different hosts in one family. After R-A, R-B and R-C, of the 651 deals
> carrying two citations, **53 reach two different observers.**

**R-C — a family pair that shares an upstream FOR THIS PREDICATE collapses.**
Predicate-scoped, because independence is not a property of two sources in
general — it is a property of two sources *about one thing*.

- `federal_registry` + `federal_transactional` are **one** family for a legal
  NAME: USAspending copies recipient identity from the SAM registration
  (`LR_USASPENDING derives_from LR_SAM`).
- The same two are **two** families for an identifier BINDING: a CAGE is
  issued by DLA, a UEI by SAM.gov, and FPDS records the binding actually used
  on an award. Three parties, not one registrant talking to itself.
- `federal_registry` + `cedar_inference` are **one** for Native status:
  np_orgs' determination *is* a name match over an IRS BMF row, and the IRS
  never asserts that an organisation is Native.

---

## What each pair tested, and what it found

| pair | dataset | facts | 0 fam | 1 fam | **≥2 fam** |
|---|---|---:|---:|---:|---:|
| P1 NEST identifier — parent's own CAGE × FPDS | nest | 107 | 0 | 31 | **76** |
| P2 NEST ownership — audited filing × own site × FPDS-declared parent | nest | 1,615 | 0 | 1,474 | **141** |
| P3 deals — `Source_1` × `Source_2` | deals | 1,073 | 2 | 1,022 | **49** |
| P4 nonprofit Native status — Cedar's inference × the org's own 990 words | nonprofits | 784 | 716 | 68 | **0** |
| P5 gaming affiliation — CGCC × the property's own site | gaming | 786 | 681 | 100 | **5** |
| P7 self-published identifier × federally held identifier | `_entity_layer` + nonprofits | 67 | 0 | 18 | **49** |

### P1 — the cheapest real corroboration in the project

107 NEST rows carry a CAGE **published by the parent on its own site**
(`identifier_basis`). **76 of those 107 CAGEs appear in
`fpds_uei_cage_map.csv`** — the parent says it, and a federal award record
independently shows the same code in use. Two families, 76 facts, zero
network calls, and the data was already on disk.

The other 31 are as interesting: **a CAGE a parent publishes that has never
appeared on a federal award.** Not a defect — a firm can hold a CAGE and not
win work — but it is the honest boundary of the corroboration.

### P2 — NEST's own multi-source column is not a multi-family column

`nest_enterprises.n_distinct_sources` reports **438 rows with more than one
source**. At observation grain, in
`data/staging/nest/ownership_edges_staged.jsonl` (3,796 rows), the same
population reaches **two evidence families on 40 groups.** The gap is almost
entirely one filer's AS 45.55.139 report across several fiscal years: three
documents, one observer.

Adding the FPDS declared-parent family (87 corroborations, built by
`code/1102`) brings the total to **141 of 1,615**.

**This is the single most important correction in this document, because 438
is a number a buyer could reasonably read as corroboration and it is not one.**

### P3 — the deals dataset claims more verification than it cites

`Verification_Status` against the measured family count:

| label | rows | 1 family | 2 families |
|---|---:|---:|---:|
| `Primary verified` | 553 | 545 | 8 |
| `Verified` | 331 | 309 | 22 |
| `Primary + independent verified` | 18 | **4** | 14 |
| `Independent secondary corroborated` | 5 | **5** | 0 |
| `Secondary corroborated` | 2 | 0 | 2 |

**13 rows carry a label that unambiguously claims independent corroboration
and reach one evidence family.** They are written to the disagreement table
individually. `Verified` and `Primary verified` are *not* flagged — those
labels do not say what the row was verified against, so calling them
overstatements would be its own unmeasured claim. They are reported here as
context.

### P4 — the nonprofit result is the sharpest, and it is a zero

**784 Native-status claims in `np_orgs.csv` reach at most ONE voting evidence
family, and 716 of them reach NONE.**

The reason is structural, not an oversight. `disposition = NATIVE_VERIFIED_STRICT`
is a **name match over an IRS BMF row**. The IRS does not assert that an
organisation is Native; it lists a name, an address and an NTEE code. So the
determination is `cedar_inference`, which does not vote, and `n_coders_agree`
— which reads like five sources — is four coders reading one BMF row plus one
USAspending signal that derives from SAM.

The organisation's **own Form 990 narrative** is a genuine second family, and
4,296 np_orgs EINs have one on disk
(`data/staging/np_mission/inclusion_basis.jsonl`, built by `code/541`). Of the
784 Native claims: **68 corroborate**, 226 are **silent**, 23 unmeasurable,
467 have no local return.

**Silence is not refutation, and this document will not let it be read as
one.** *Tongass Tlingit Cultural Heritage Institute* scores `placename_only`
and is plainly Native — the miner scored the place name, not the mission. The
subset worth a human is the one where the organisation's own words are silent
**and** Cedar's link crosses a state line. There are 29, and they are listed
below.

### P5 — gaming affiliation is state-vs-site, and the pair barely overlaps

Only two families independently state which nation a gaming property belongs
to: the **CGCC's own published lists** (`ca_gaming_facilities_official.csv`,
178 rows with a facility id) and the **property's own site**
(`gaming_property_self_published_assertions.csv`, 241 ownership/management
rows with a facility id). They overlap on **5 facilities**.

**`gaming_nigc_roster_link.csv` was read and REFUSED for this predicate**, and
the refusal is the point. It looks like 453 rows of federal corroboration; the
NIGC location map carries a facility name, an address and a contact person and
**no tribe**. The `tribe_id` on those rows is Cedar's own. It corroborates that
a property exists at an address on IGRA lands — which is worth having, and is
a different fact.

### P7 — the mandate's headline pair, and how thin it is

Every UEI, CAGE and EIN Cedar holds arrived from the federal side. An entity's
own statement of the same identifier is an independent family. **49 facts now
carry two, from four routes:**

| route | on disk | corroborated |
|---|---:|---:|
| firm capability statements via `native_business_identifier_crosswalk.csv` | 12 | 4 |
| `code/1114`'s harvest (`data/staging/capability_1114/`) — **live snapshot** | 16 | 8 |
| JSON-LD identifier blocks in `data/staging/cedar_web_map.csv` | 2 entities | 4 |
| a nonprofit's own page stating its own EIN (`data/staging/np_harvest/raw/pages/`) | 1,434 pages | **33** |

`code/1114_capability_statement_harvest.py` is another workstream's live
harvest and had reached one entity when this ran. **Its row count is written
into `cedar_corroboration_conservation.csv` so this number is re-derivable
rather than trusted, and it will grow when 1114 does.**

---

## The disagreements — 306 rows, 254 distinct facts, none reconciled

Every one carries both sides with a quote or a URL (invariant **C5**), and
`resolution` reads `REFUSED - recorded, not reconciled` on all of them.

| verdict | rows | distinct facts |
|---|---:|---:|
| `OWN_990_SILENT_ON_NATIVE_IDENTITY` | 197 | 197 |
| `SELF_PUBLISHED_OWNER_NAMES_A_DIFFERENT_NATION` | 52 | 2 |
| `OWN_990_SILENT_AND_THE_LINK_CROSSES_A_STATE_LINE` | 29 | 29 |
| `VERIFICATION_CLAIM_RESTS_ON_ONE_EVIDENCE_FAMILY` | 13 | 13 |
| `DECLARED_PARENT_IS_A_DIFFERENT_ENTITY` | 8 | 8 |
| `SELF_PUBLISHED_EIN_DIFFERS_FROM_THE_IRS_SIDE_EIN` | 6 | 6 |
| `SAME_CAGE_DIFFERENT_LEGAL_NAME` | 1 | 1 |

### The 29 that need a human first

`np_orgs.disposition = NATIVE_VERIFIED_STRICT`, the organisation's own Form
990 narrative silent on Native identity, **and** Cedar's link crossing a state
line. Fourteen of the twenty-nine, with the organisation's own words:

| organisation | its own 990 says |
|---|---|
| KANSAS HUMANE SOCIETY OF WICHITA INC | *"YOUTH EDUCATION IS A KEY BUILDING BLOCK TO REACHING OUR VISION AND REDUCING OUR COMMUNITY'S DISTRE…"* |
| WAMPANOAG COUNTRY CLUB INC | *"…IS A PRIVATE MEMBERSHIP CLUB THAT WAS FOUNDED IN 1924…"* |
| UNITED HABESHA COMMUNITY OF WICHITA UHCW INC | *"HELP COMMUNITY IN NEED"* |
| RANCHO LA LAGUNA INC | *"TO PROMOTE AND PRESERVE THE CULTURE OF CHARRERIA"* |
| CALIFORNIA CLUB OF LAGUNA WOODS VILLAGE | *"…social recreational entertainment members club located inside an over 55 year aged retirem…"* |
| PASADENA ROSEBUD ACADEMY CHARTER SCHOOL | *"THE ORGANIZATION OPERATED A CHARTER SCHOOL…"* |
| RED ROSEBUD FOUNDATION | *"PotatoAllergy.com and its groundbreaking books…"* |
| CHICKASAW CIVIC THEATRE (AL) | *"TO PRESENT SEVERAL COMMUNITY THEATRE PRESENTATIONS EACH YEAR…"* |
| CHICKASAW DEVELOPMENT CORPORATION (AL) | *"PROVIDE HOUSING FOR PERSONS OF LOW INCOME, ELDERLY OR DISABLED"* |
| CHICKASAW ATHLETIC BOOSTER CLUB (IA) | *"…THE ATHLETIC DEPARTMENT AT NEW HAMPTON C…"* |
| CHICKASAW WELLNESS COMPLEX INC (IA) | *"TO PROVIDE COMMUNITY WITH A PLACE FOR HEALTHY RECREATION"* |
| ZUNI HILLS ELEMENTARY PARENT TEACHER STUDENT ORG (AZ) | *"Support Zuni Hills Elementary School activities"* |
| NORTH LAGUNA CREEK VALLEY HI COMMUNITY ASSOCIATION | *"…NORTH LAGUNA CREEK AND VALLEY HI COMMUNITY…"* |
| SANTA ROSA BAND OF LOWER MUSCOGEE INC | *"…preserve the history and heritag…"* (a state-level band; the link is to a different nation) |

**Chickasaw, Alabama is a city.** Zuni Hills is a Phoenix subdivision. Laguna
is a place in California and *Habesha* names the Ethiopian and Eritrean
diaspora. This is the `ENTITY_MATCH_RULES` place-name defect, arriving with
Cedar's *strongest* nonprofit Native label attached — and the organisations'
own filings say so in their own words. `NATIVE_VERIFIED_STRICT` is 697 rows;
293 of them have a local Form 990, and **214 of those 293 give no Native
signal in the organisation's own words**.

**None of these rows were changed.** `np_orgs.csv` is not this layer's to edit.

### The 8 NEST ownership contradictions

The firm's declared FPDS parent resolves to a Cedar entity other than the
owner NEST publishes. `ENTITY_MATCH_RULES` rule 12 says suspect the parent row
first, and `code/1102` already adjudicated seven of these in NEST's favour —
they are carried here so the conflict stays visible rather than closed:

| firm | NEST says | FPDS declared parent resolves to |
|---|---|---|
| Bowhead Manufacturing / Professional Solutions / Transportation, Rockford Corporation, UMIAQ Environmental *(5)* | Ukpeaġvik Iñupiat Corporation | `AKNF-INPTAS-00-ARCSLO` (the **village government**) |
| Nisga'a Tek LLC | Tlingit & Haida | `ANVC-GLDBLT-00` |
| Goldbelt Eagle, LLC | Goldbelt, Incorporated | `AKNF-VEAGLE-00-DOYONL-TNNACH` |
| Broadleaf, Inc | The Hawai'i Pacific Foundation | `ANRC-ARCSLO-00` |

### The one CAGE conflict

| | value | source |
|---|---|---|
| A `entity_self_published` | **ASRC Federal DNC** | the parent's own company page, CAGE published there |
| B `federal_transactional` | **DATA NETWORKS, INC.** | `fpds_uei_cage_map.csv`, same CAGE |

Both may be true across time — a CAGE survives an acquisition and a rename —
which is precisely why the layer records it instead of choosing.

### The 6 EIN conflicts

A page harvested under one EIN states a different labelled EIN. Two are a
foundation stating its parent charity's number
(*LUTHERAN SOCIAL SERVICES OF SOUTH DAKOTA FOUNDATION* → `46-0224731`;
*FOUNDATION FOR THE INDIAN TRAILS PUBLIC LIBRARY* → `27-2783518`); the rest
are unexplained.

---

## Two defects this layer found in ITSELF, and how

Both are the repo's signature failure — *the number was produced, it was
plausible, and it was about something else* — and both were caught by
invariants written before they happened.

**1. The EIN detector matched a Facebook tracking pixel.** v1 accepted `TIN`
without a word boundary and a bare nine digits without a strong label. It
reported **81 disagreements**, of which the most common single value was
`314192535` — `facebookAppId`. v2 requires a labelled occurrence, and for the
bare nine-digit form a strong label. **81 → 6.** The 75 that vanished were
fabricated conflicts about real organisations. The dead regex is kept in the
source with this account beside it.

**2. The 90-UEI cardinality bug, repeated.** `docs/ASSERTION_LAYER.md` records
R00: one entity holds 90 UEIs, all real, and the first resolver read them as 90
competing answers. The first version of this layer keyed a fact as
`(subject, predicate)` and reported **Nakupuna Foundation CONTESTED** because
it publishes eight CAGE codes on one page. `MULTI_VALUED_CLASSES` now puts the
value in the key for an identifier binding.

A third, caught by **C3** on its first run: `Moody's Investors Service rating
action (public press release, retrieved via Internet Archive)` was typed
`RETRIEVAL_METHOD` because the Internet Archive test ran before the
rating-agency test. The parenthetical names how the page was fetched; the
string names an observer. **The retrieval test now runs last.**

And a fourth, in the reverse direction: **five fabricated gaming conflicts.**
The CGCC publishes *"Campo Band of Diegueno Mission Indians of the Campo
Indian Reservation"*; the property's own site says *"Campo Kumeyaay Nation"*.
Folding only corporate suffixes made those two different answers. Agreement
for an affiliation is now distinctive-token overlap after stripping tribal
descriptors, with a third outcome — `NOT_COMPARABLE` — for the case where one
side's whole name is descriptors (*"the Confederated Tribes"*), because
returning AGREE there would print an absence of evidence as evidence of
agreement.

---

## Verification

`verify` runs eight invariants and exits 1 on any breach. `selftest` injects
each violation, asserts exit 1 **and that the named invariant is what fired**,
restores, and asserts exit 0. All nine fixtures pass.

| | |
|---|---|
| **C1** | every evidence family is declared |
| **C2** | no fact claims more independent families than its observations support, recomputed through R-A/R-B/R-C |
| **C3** | one upstream document wears one family, everywhere in the store. *Not C2 restated* — C2 checks the count, C3 checks the typing, and R-A hides a typing bug from C2 by collapsing the pair. It found three real bugs on its first run |
| **C4** | a non-voting family never contributes to a count |
| **C5** | every disagreement quotes or links BOTH sides |
| **C6** | source-row conservation — `rows_in == sum(named dispositions)`, and `other`/`unknown`/`misc`/`n/a` are refused by name |
| **C7** | `CORROBORATED` requires ≥2 families **and** agreement under the predicate's own agreement test |
| **C8** | the census names all fourteen shipping datasets, each with a non-blank reason |

**Source-row conservation: 31,186 rows read across 13 inputs, 0 unaccounted,
every rejection named.** It immediately surfaced the P4 denominator —
`native_claim_no_local_990_return` 467 — which no coverage document held.

---

## The census: which datasets are still wholly single-sourced

| dataset | status | facts examined | ≥2 families | wholly single-sourced |
|---|---|---:|---:|:-:|
| `_entity_layer` | MEASURED (identifier bindings only) | 34 | 16 | N |
| `nest` | MEASURED | 1,722 | 217 | N |
| `deals` | MEASURED | 1,073 | 49 | N |
| `nonprofits` | MEASURED | 817 | 33 | N |
| `gaming` | MEASURED | 786 | 5 | N |
| `contractors` | SINGLE_FAMILY_BY_CONSTRUCTION | 0 | 0 | **Y** |
| `federal-register` | SINGLE_FAMILY_BY_CONSTRUCTION | 0 | 0 | **Y** |
| `funding` | SINGLE_FAMILY_BY_CONSTRUCTION | 0 | 0 | **Y** |
| `nagpra` | SINGLE_FAMILY_BY_CONSTRUCTION | 0 | 0 | **Y** |
| `subcontracting` | SINGLE_FAMILY_BY_CONSTRUCTION | 0 | 0 | **Y** |
| `legislation` | NOT_REACHED_BY_THIS_PASS | 0 | 0 | **Y** |
| `lobbying` | NOT_REACHED_BY_THIS_PASS | 0 | 0 | **Y** |
| `native-owned-businesses` | NOT_REACHED_BY_THIS_PASS | 0 | 0 | **Y** |
| `natural-resources` | NOT_REACHED_BY_THIS_PASS | 0 | 0 | **Y** |

**Nine of fourteen shipping datasets are wholly single-sourced**, and the
census distinguishes the two reasons rather than blurring them.
`SINGLE_FAMILY_BY_CONSTRUCTION` means the source *is* the fact — a NAGPRA
notice is the Federal Register record, and a republication of it is the same
family; `510` proved this by harvesting the FR roster and moving the
corroborated count by zero. `NOT_REACHED_BY_THIS_PASS` means a real pair
exists and nobody has built it. **Only the second kind is a task.**

---

## The highest-value unbuilt pair, and it is already on disk

**`lobbying`: LDA registrant filings × Form 990 Schedule C.** An organisation
reports its lobbying spend to the Senate/House LDA registry *and*, separately,
to the IRS on Schedule C, under different definitions and different penalties.
Two families, same fact, and Cedar holds both:
`data/staging/np_mission/schedule_c_lobbying.csv` — 860 returns with a
Schedule C, 466 with an amount, **553 of them already in `np_orgs`**, against
`native_entity_lobbying_disclosures.csv`.

The two figures will not match, and that is the value: the reconciliation is
the story, and the residual is a measurement of what LDA does not capture.

Ranked next:

1. **`natural-resources`** — a state severance filing and an ONRR
   disbursement for one production stream are two families for one fact.
   Currently the tables cover *different* streams, so they were not tested.
2. **`native-owned-businesses`** — a tribal certification register is the
   independent family; 26 rows are staged in
   `data/staging/tribal_vendor_lists/`, 22 carrying `THIRD_PARTY_TRIBAL_GOVT`.
3. **`gaming` beyond California** — CGCC is the only state list on disk with
   real per-facility grain. WA, MN, OK and CT publish equivalents.
4. **Finish `code/1114`.** 937 entities queued, one processed, and 3,175
   located-but-unextracted surfaces in `surfaces_found.csv`. Each capability
   statement that yields a UEI is a second family for a binding Cedar already
   holds.

---

## Merge proposals — what belongs in another owner's table, and why not here

Nothing below was applied. Each names the owner.

1. **`510_assertions.py` should adopt `third_party_press`, `compiled_directory`
   and the predicate-scoped `SHARED_UPSTREAM` table.** The source registry's
   `derives_from` tree is a *global* statement about two sources; it cannot
   express that SAM and FPDS are one family for a name and two for an
   identifier binding. That distinction is what earns P1's 76 corroborations,
   and the assertion layer cannot currently make it.
2. **`nest_enterprises.csv` should carry `n_independent_families` beside
   `n_distinct_sources`.** 438 and 141 are both true and only one of them is
   corroboration. Owner: the NEST workstream.
3. **`deals_classified.csv` should carry the measured family count beside
   `Verification_Status`.** 13 rows claim independent corroboration and cite
   one family. Owner: the deals workstream. *Do not rewrite the labels* —
   record the measurement next to them.
4. **`np_orgs.csv` needs a `native_status_evidence_families` column, and it
   would read 0 on 716 of 784 Native claims.** Owner: the nonprofits
   workstream. The 29 state-conflict rows above should reach
   `review/OWNER_DECISION_QUEUE.md` before any of them publishes.
5. **`gaming_facilities.csv` should not present `operating_entity_cedar_uids`
   as an operator statement.** It equals `cedar_uid` on 786 of 787 rows — the
   tribe restated, not an independent operator. Owner: the gaming workstream.
   *(**787 is the ROW count and is correct here**, because this is a per-row
   statement about a column. It is NOT the facility denominator — note added
   2026-09-02 by the ruling-propagation pass, which is gating that number:)*

> **GAMING-DENOMINATOR-2026-09-02 — the gaming denominator, re-derived from the live files.**
> **`gaming_facilities.csv` holds 787 ROWS, and a row is not a facility.** The ladder, owned and gated by `code/846_session_audit.py::_denom`:
> 
> ```
> 787   rows in gaming_facilities.csv
> -16   whose NAME says no casino - 7 exactly "No casino", plus 9 more like
>       "Grand Canyon West - no casino", "Tribal admin only - no casino"
> =771   facility rows
> -57   extra rows across the same-tribe duplicate groups
> =714   distinct properties
> ```
> 
> **FIVE denominators circulated on 2026-09-02 and all five were quoted as settled: 787, 780, 734, 727, 714.** Each came from a different definition of "facility" and none said which. 787 is raw rows; 780 removes only the 7 EXACT placeholders and misses the 9 that say it in a longer name; 734 is 787 minus duplicates with every placeholder left in; 727 is 780 minus a duplicate count of 53. **None of them is wrong about the piece it measured, and four of them are wrong as a denominator.** No verdict is applied in the table itself - `duplicate_of_facility_id` is populated on 10 rows, not 57 - so 714 is a measurement, not a state of the file. Note also that the duplicate register carries `DIFFERENT_TRIBES_CHECK_BOTH` groups that are **not** duplicates: Stables Casino pairs the Miami Tribe with Modoc Nation, which is a joint operation. Dividing by 787 inflates the denominator by 10.2% and understates every gaming coverage percentage by about 9.3%.
>
> Authority: `code/846_session_audit.py::_denom`, which gates this ladder.
> Re-derive rather than quote: `py -3 code/1116_ruling_propagation_2026_09_02.py derive`.
> `py -3 code/1116_ruling_propagation_2026_09_02.py verify` exits 1 while any
> document in `docs/` or `review/` still states a superseded figure unmarked.


---

## Where this is honestly weak

- **Four of fourteen datasets carry all the measured facts.** `contractors`,
  `funding`, `subcontracting`, `federal-register`, `nagpra`, `legislation`,
  `lobbying`, `natural-resources` and `native-owned-businesses` contributed
  nothing, and for five of them that is a real finding while for four it is
  simply undone work. The census says which is which; do not read the row
  count as coverage.
- **`P7`'s 1114 block is a snapshot of a live harvest.** It will change under
  this layer without this layer changing. The conservation table records the
  input row count so the drift is visible.
- **The 197 `OWN_990_SILENT` rows are not refutations** and the disagreement
  table says so on every row. They are a queue, and the miner that produced
  them has known false negatives — it scored *Tongass Tlingit Cultural
  Heritage Institute* as `placename_only`.
- **`SHARED_UPSTREAM` has an entry that never fires.** The
  `(federal_registry, cedar_inference, native_status)` rule is declarative: it
  records *why* np_orgs' name match gets `cedar_inference` and not a federal
  vote. That is the `I7` dead-authority shape, kept deliberately, and named
  here so the next reader does not report it as a bug.
- **`third_party_press` votes, and that is arguable.** A trade journal
  reprinting a press release verbatim is not an independent observer, and R-A
  only catches it when both citations resolve to one URL. Thirty deals reach
  two families via `entity_self_published,third_party_press`; if the press
  vote were withdrawn, the project total falls from 320 to about 290.

---

## Tables

| path | rows | what it is |
|---|---:|---|
| `data/clean/cedar_corroboration_observations.csv` | 5,588 | one row per observation, with its family, upstream key and quote |
| `data/clean/cedar_fact_corroboration.csv` | 4,432 | one row per fact, with `n_independent_families` and the collapse notes |
| `data/clean/cedar_corroboration_disagreements.csv` | 306 | both sides, both quoted, `REFUSED - recorded, not reconciled` |
| `data/clean/cedar_corroboration_census.csv` | 14 | per shipping dataset, with a reason on every row |
| `data/clean/cedar_corroboration_conservation.csv` | 13 | rows in = sum of named dispositions |

All five are **internal**: they are a measurement of Cedar's evidence base,
not a product, and `cedar_corroboration_disagreements.csv` names organisations
against claims that have not been adjudicated.
