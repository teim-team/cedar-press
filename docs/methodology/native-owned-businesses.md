# Methodology — Native-Owned Businesses

**`native-owned-businesses`. Two unrelated strands under one collection name:
`native_owned_businesses.csv` (2,393 firms from 18 tribal certifying
authorities) and the `individual_native_*` family (45 individually
Native-owned firms carrying $2,340,066,582 in federal prime obligations).**
[measured 2026-09-02]

*Written 2026-09-02. This is the methodology record: what was pulled and from
where, how the rows were made, how entities were attributed, what was decided
and why, what the known limits are, and how often it has to be re-pulled. It is
not the product copy (`docs/datasets/_descriptors.json`) and not the codebook
(`docs/codebooks/`).*

**A note on the figures.** `[measured]` means the figure was re-counted from
the live file with `csv.reader` on 2026-09-02. `[from the record]` means it
came from a build log or docstring without independent measurement. Where a doc
and the data disagreed, the measurement won; the disagreements are listed at
the end.

**Readiness: READY.** [measured — `docs/DATASET_READINESS.md`, regenerated
2026-09-02: 6 tables, 6/6 grain, 6/6 keys, duplicates clean, rebuild declared]

---

## The structural fact to grasp first

**This collection holds two things that share a name and share nothing else.**

- **Strand A — individually Native-owned firms.** Firms owned by *people*, not
  nations. Seven tables (`individual_native_*`), keyed on Cedar-minted
  surrogates, sourced from `prime_contracts.csv` plus the owner's own rulings
  plus a web verification pass. **They roll up to nothing and appear in no
  tribal total.**
- **Strand B — tribal certification registries.**
  `native_owned_businesses.csv`, 2,393 firms harvested from 18 tribal TERO
  offices, Indian-preference registers, business-licensing departments and
  enterprise registers, normalised to one schema.

> **A live registration defect worth recording:**
> `code/500_build_architecture_map.py`'s `COLLECTIONS` entry for this
> collection matches `^(individual_native|tribal_certification)` and its
> `dirs` list omits `02m_native_owned_businesses` — so
> **`native_owned_businesses.csv`, a 2,393-row shipping table, is claimed by no
> collection at all**, and `docs/DATASET_CONTRACTS.md` lists 7 tables for the
> collection without it. The strand that carries the collection's name is
> invisible to the map that describes it.

---

# STRAND B — tribal certification registries

## B1. Sources

**18 certifying authorities** [measured — 18 distinct `source_id`], harvested
by `code/330_build_native_owned_businesses.py harvest` from snapshots in
`data/staging/business_registry/raw/`, with **no network calls at build time**.

Largest first: Cherokee Nation 836 · Navajo Nation 346 · Muscogee (Creek) 337 ·
Lummi 140 · MHA Nation 133 · CSKT 116 · Calista 98 · Grand Ronde 81 · EBCI 68 ·
Pokagon 68 · Tulalip 49 · Oneida (WI) 34 · Blackfeet 25 · ASRC Federal 20 ·
Tohono O'odham 17 · Poarch 13 · Doyon 8 · Menominee 4.

### What was deliberately not used

**Six certifying authorities are EXCLUDED on their own stated terms and stay
excluded by every route — the publisher's page, its WordPress media API, the
Wayback Machine, sitemap enumeration, browser-header retries, relaxed TLS, and
any harmonised derivative.** Each is recorded with the verbatim quote and URL
that justifies it, in `code/330`'s `EXCLUDED` constant:

| authority | the term, quoted |
|---|---|
| **Confederated Colville** | *"All rights reserved, Colville Tribes. Copyright (c)"* |
| **CTUIR / Umatilla** | *"Copyright (c) CTUIR 2020"* |
| **Forest County Potawatomi** | *"…personal, non-commercial transitory viewing only… you may not: Modify or copy the materials; Use the materials for any commercial purpose…"* |
| **NANA Regional / Akima** | *"…no Content or Marks may be copied, reproduced, aggregated, republished… for any commercial purpose whatsoever, without our express prior written permission… any automated use… data mining, scraping…"* |
| **Southern Ute** | *"…personal, non-commercial transitory viewing only… you may not: modify or copy the materials; use the materials for any commercial purpose…"* |
| **The Chickasaw Nation** | *"…may not be copied or redistributed and is provided 'AS IS'…"* |

**Four of the six were found only on 2026-09-01, because nobody had opened the
terms page** that an earlier survey had recorded as `SILENT`. That is the
process lesson: a survey that does not read the terms page has not established
that terms are absent.

**What the exclusions cost, ranked so a future opt-in request knows where to
start:**

- **Colville is the richest schema in the whole study** — an explicit numeric
  *"Indian % Owned"* column plus a four-level preference tier. It is also the
  source that proves a TERO listing is not itself an ownership claim: **firms at
  0% Indian ownership still carry "Certified Title 10 = Yes."**
- **NANA is the single highest-value request** — about 55 operating companies
  each publishing **CAGE, UEI, DUNS, primary NAICS and 8(a) status**, joinable
  to federal award data with no name matching at all. A sitemap enumeration was
  **stopped mid-run** when the terms were read.
- **Chickasaw** is roughly 622 businesses, the largest lower-48 directory after
  Cherokee. **Southern Ute**'s 27 firms answer the growth-fund question
  directly (Red Willow and Red Cedar appear on the TERO Indian-owned list
  beside small local contractors). **CTUIR** has 14 very clean entries; **FCP**
  18.

**Two more names commonly listed with those six, correctly distinguished:**

- **Yakama is not a terms exclusion.** It is `NO_LIST_FOUND`: the TERO exists
  and operates and publishes its ordinance plus six blank forms, **but never a
  roster**. The Indian Preference Application proves a list exists internally.
  Yakama is separately one of four tribes — with Standing Rock, Oglala and
  Seneca — **whose own ordinance requires publication and who do not publish.**
- **Stillaguamish** came from a different harvest. Shard M read
  `stillaguamish.com/terms-of-use` **before** enumerating, found *"prior
  written permission… Any unauthorized use… may violate copyright"*, and
  dropped the host. **Four hours later its own `--deep` mode re-probed the same
  host and pulled 1,506 media-index entries**, because that mode consulted a
  hard-coded constant and never read the verdict the same script had written to
  its own log. Quarantined, dropped from the outputs, nothing harvested.
  **Standing rule earned: a refusal recorded in one code path must be enforced
  from a single place every other path reads.**
  The mirror-image defect, same shard: the terms matcher fired on **inline
  CSS** at `nhbp-nsn.gov/legal/` and recorded Nottawaseppi Potawatomi as
  restrictive — that page states no restriction. **A false restrictive is not
  the safe direction; it silently deletes a tribe from the study.**

**Other access decisions, recorded as facts rather than as friction.** No
login, paywall or access control was bypassed: Oneida's WP REST route answered
401 and was not worked around; NANAtkut, mySealaska, Eklutna `/members` and
Beacon Bid were not probed. **`elyshoshonetribe.com` names `ClaudeBot` and
`anthropic-ai` under an explicit Disallow** — crawling stopped, and the host is
marked `wayback_priority = EXCLUDED`, because **an origin's stated refusal of
this agent is not routed around by fetching the same content from an archive.**
`colvilletribes.com` also names both agents, but under `User-agent: *` with no
blanket disallow and permitted TERO paths — recorded as a reason to **ask
before publishing**, not as a licence. CSKT's `Crawl-delay: 10` and Choctaw
Nation's `Disallow: /pdfs/` were honoured; Turtle Mountain is
`ROBOTS_DISALLOW_ALL`; Choctaw Nation is `BEHIND_LOGIN_OUT_OF_SCOPE`, and
**Wayback is not a route around a login.**
`kotzebueira.org`, `nana.com` and `olgoonik.com` answer HTTP 403 on **every
path including `robots.txt`** — a WAF — so their terms status is
**`NOT_CHECKED`, never `SILENT`**: an unreadable term is not an absent one, and
they are never recorded as negatives.

> **Two different terms bars are in force and nobody has picked one.** Navajo,
> Colville and CTUIR were marked restrictive on a **bare copyright footer**;
> Chickasaw, FCP, Southern Ute and NANA on an **actual terms page**. On the
> first bar essentially every tribal website is restricted. The 2026-09-01 pass
> applied the second bar to its own findings and **did not reverse the first
> bar's verdicts** — so Navajo stays *inside* `native_owned_businesses.csv`
> with the restrictive flag and `publishable = N`, while Colville and CTUIR
> stay out entirely. **This is left visible rather than resolved unilaterally**,
> and it is the single most consequential open question in the dataset.

## B2. How the rows were made

`code/316_build_tribal_vendor_list_roster.py` … `code/324` (the survey) →
`code/330_build_native_owned_businesses.py` (`harvest|promote|registry|codebook|docs`)
→ `code/321_gate_tribal_source_restriction.py` (the gate) →
`code/615_set_publishable_native_owned_businesses.py --apply` (the publishing
decision) → `code/771_normalize_nboa_certification_dates.py`. Verdicts are
loaded by `code/319_load_tribal_vendor_list_verdicts.py`; the sweeps are
`code/570` (shard L) and `code/690` (shard M).

Ingestion is not uniform and is recorded per row: Blackfeet is **OCR from a
scan** (`ingestion_method = ocr_rapidocr_220dpi`, with per-row mean confidence
and `OCR_RECOVERED` kept distinguishable); Menominee's DevExpress grid pager
refused three argument formats and yielded 4 of 23 rows; Tohono O'odham yielded
17 of 19 certification stamps; CSKT 116 of 118, with 5 rows flagged
`BUSINESS_NAME_MAY_BE_AN_ADDRESS_LINE`.

## B3. How entities were attributed, and the loose path that was refused

Each business is offered to `503_identity.resolve()` and **only an exact
normalized name or alias hit is accepted.** The loose gov-class token path was
refused by design, because it produced:

```
Navajo Engineering & Construction     -> Navajo
Osage Electrical Contractors          -> The Osage Nation
Arctic Information Technology         -> Arctic Village
```

**78 rows matched that way and every one would have been wrong.** An unresolved
business keeps its row: `record_scope = unresolved` on **2,389 of 2,393**,
`entity` on 4. [measured]

**The certifying AUTHORITY is keyed; the BUSINESS is not.** That asymmetry is
the collection's largest commercial limitation and is stated in §B6.

## B4. Decisions that shaped the data

### The inclusion basis IS the product

`identity_claim_text` is quoted verbatim from each authority and **is not
uniform, because the authorities do not mean the same thing.**
`identity_scope` [measured]:

```
any_native                                 1,567
citizen                                      385
mixed                                        164
shareholder_descendant_or_spouse              98   <- the weakest
enrolled_member_cskt                          91
parent_asserted_subsidiary                    28
enrolled_member_other_federally_recognized    25
any_native_oodham_and_local                   15
enrolled_member_100pct                         6
enrolled_member_51pct                          4
vendor_relationship                            4
tribally_owned_entity                          3
other_indian_preference_certified              2
unknown                                        1
```

**A firm certified at 100% enrolled-member ownership, one on an any-Native
list, one qualifying through a shareholder's spouse or descendant, and a vendor
with no ownership relation at all are four different claims.** Flattening them
into "tribally owned" would erase a gradient the sources went to the trouble of
stating — and a spouse-owned firm is not a Native-owned firm, while the source
cannot tell you which of the 98 is which.

`assertion_class` splits the same way: **OWNERSHIP 2,389 / RELATIONSHIP 4**
(Menominee). [measured] **A consumer that sums the two has added two different
facts.**

### Affiliation, not ownership, is the published relation

The owner's call, and it follows from the gradient above: **the relation Cedar
publishes is `affiliated_with` a named nation, with `identity_scope` beside it
saying what the affiliation actually is.** The strong claim stays available to
anyone who filters for it; the dataset does not assert it on rows that never
supported it.

### Privacy: the clean table carries the certification, not the front door

Withheld from `data/clean` and kept in staging, named per row in
`withheld_fields`: `owner_name_raw`, `email`, `phone`, `address_raw`,
`postal_code`, `website`, `dba_name`, `description_raw`. Counted rather than
named: `owner_name_present`, `n_owners_named`. **No digest surrogate is minted
for a personal name** — a digest of an enumerable value is not a privacy
control, and the protection is that the column does not ship.

`business_name_is_person_name` [measured]: 0 on 1,786, 1 on 280, **−1
(undecidable) on 327**.

### An over-withholding the owner reversed

The first version of `code/615` withheld 521 rows because
`business_name_is_person_name` was 1 or undecidable — treating *"Jane Doe
Construction"* as publishing Jane Doe. The owner reversed it:

> *"If a site is publicly accessible, it is part of the public domain and
> therefore we can incorporate it… It's not PII, it's not Social Security
> numbers. But the firm is named after the owner — it's the name of the firm,
> and of course we're going to include that."*

**A firm's legal name is the firm's name.** A business listed on a tribe's
public vendor directory has been published by that tribe *as a business*, by a
certifying authority that chose to list it. Suppressing the name would make the
row useless while protecting nobody.

**The distinction that survives is not name-shaped-ness. It is: does the column
describe the FIRM or a PERSON separate from the firm?** Firm — legal name, DBA,
city, state, NAICS, certification number, licence number, identity scope —
publishes. Person — a home address, personal email or phone, a date of birth,
an SSN — never, and **none of it is in this table anyway**: the clean file was
verified to carry no `owner_name_raw`, email, phone or street-address column
before `615` ran, so the privacy gate was retired rather than loosened.

**`business_name_is_person_name` is KEPT as a column.** It is no longer a
suppression trigger, but it is a real property of the row.

### Two gates, computed separately, and only one of them moved

`code/615` runs **permission** (a property of the source) and **privacy** as
independent gates. Result [measured]: **`publishable = Y` on 2,047 rows, `N` on
346** — the 346 being Navajo NBOA's `TERMS_STATED_RESTRICTIVE` rows.

**`consent_status` is `UNRESOLVED` on all 2,393 rows and stays that way.**
`publishable` records *Cedar's* decision under a stated policy;
`consent_status` records *the source's*. Overwriting the second with the first
would record a permission nobody gave. The gate's governing line:
**"SILENCE IS UNRESOLVED, NEVER PERMISSION."**

`code/321_gate_tribal_source_restriction.py` enforces it with five failing
checks: required columns present (**a gate that cannot evaluate a file must
FAIL, never pass it**), declared vocabulary only, `publishable = Y` requires
`consent_status = OPT_IN`, `OPT_OUT` implies `publishable = N`, and no
restricted file may have leaked into `data/clean/` or `dist/`.

### Muscogee, recorded rather than averaged

A concurrent workstream typed the same Muscogee (Creek) Nation CESO
spreadsheet as `TBD-C01`, `vendor_list` / `unspecified`, because the file
states no ownership threshold. This build kept `TBD-079` as OWNERSHIP, because
**NCA 18-199 §9-105(I) requires 51%+ Native ownership to be on it.** Both
readings are defensible and they are **337 rows apart**. `TBD-C01` is refused
as a duplicate rather than merged, and the disagreement is left visible.

## B5. What a buyer may total

There is no money column. The countable things are firms and authorities, and
the two `assertion_class` values must not be pooled.

## B6. Known limits

- **Coverage is 62 of 1,555 spine entities (4.0%)** — among federally
  recognised tribes, 52 of 349 (14.9%). **297 tribes have never been looked
  at.** NHOs 0 of 210, BIE schools 0 of 185, village corporations 0 of 173.
  **An entity absent from the registry is `NEVER_CHECKED`, which is a different
  fact from `NO_LIST_FOUND`.** The remaining 297 tribes are roughly 20
  agent-days at the measured rate, and the 2026-08-26 hit rate (22 of 62 = 35%)
  predicts about 100 further lists.
- **No `cedar_uid` column at all**, and `business_entity_id` is filled on **4
  of 2,393 rows**. **This dataset cannot be joined to Cedar's contracting,
  funding or subcontracting record** — and "this TERO-certified firm also holds
  $X in federal primes" is the whole commercial value of the collection.
- **No indication of what most of these firms do.** `naics` is filled on **34
  of 2,393 rows (1.4%)**, which is why the shipped sample requested it and then
  dropped it as all-blank. `service_category_raw` is filled on **2,043 rows
  (85%)** and was never requested.
- **Certification dates are unusable as shipped.** 623 populated
  `certification_expiration` values in **six distinct formats** —
  `####-##-##` (346), `##/##/####` (144), `#/##/####` (86), `#/#/####` (33),
  `##/#/####` (13), `#/##/##` (1) — and the ISO plurality belongs to the 346
  rows that are `publishable = N` and never ship, so **every date that reaches
  a customer is in an un-normalised US format.** `certification_start` is on
  **72 of 2,393**, so a buyer cannot tell a new certification from a decade-old
  one. `source_last_updated` is on 1,127 (47%) and is not shown — for a list of
  certifications that expire, that is the difference between a live register
  and a rumour.
- **`certifying_authority_name` is blank on all 2,393 rows** [measured] while
  `source_id` and `certifying_authority_entity_id` are populated — an
  always-empty column of the kind ADR-011's C11 exists to catch.
- **Two authorities are names only.** ASRC and Doyon carry no UEI and no CAGE —
  exactly the fields that would make them joinable.
- **Re-pull notes that will otherwise cost time.** Lummi's `robots.txt`
  disallows `/apps` and the tribe's own page links
  `/apps/BusLicenses/LummiOwnedBusinesses.php`; **the identical report is at
  `/widgets/`, which is not disallowed — any re-run must use it.**
  `cherokeetero.com`'s recorded 403 was a **User-Agent gate, not a block**:
  `robots.txt` reads `Disallow:` (empty) and a browser UA gets 200.
- **A hidden-route sweep found nothing, and that is recorded.** The 2026-09-01
  pass (robots.txt → `/wp-json/wp/v2/types` → `/media?search=` → `/search` →
  `sitemap.xml`) against the eleven referenced-but-unreachable rows returned no
  new material.

## B7. Refresh

**`publish_cadence` = NONE. There is no publication schedule, and inventing one
would be a lie.** A list changes when a tribal office remembers to update it.
Cedar holds through 2026-09-01. Route: `code/570` / `code/588` — **read
`robots.txt` and the terms page FIRST.**

**What breaks if it is not re-pulled: every list not captured this quarter is
gone.** No publisher in the harvest is known to archive superseded lists, so
**Cedar's own successive harvests are the only longitudinal record of Native
business certification that will exist.** Vintage retention is a build rule
here, not housekeeping.

---

# STRAND A — individually Native-owned firms

## A1. Sources

- **The owner's own 45 rulings**, gathered from **five files in three
  vocabularies**: `data/spine/cedar_exclusion_rulings.csv` from
  `hci_analysis.do` (31 rows, `exclusion_reason = individually_native_owned`,
  note *"owned by individual Cherokees"*), plus four `review/rulings_inbox_*`
  files using `YOUR_RULING = INDIVIDUAL_NATIVE`, `YOUR_RULING = OWNER_NAMED`,
  and free-text *"Not a Native entity — individually Native-owned firm."*
  [measured — 45 rows, 45 distinct identifiers, `ruled_by = Elijah Moreno` on
  all]
- **`prime_contracts.csv`, read-only** — the candidate universe.
- **A 12-batch web verification pass**,
  `data/raw/web/individual_native_verification_2026-08-26/`, about 300 distinct
  company websites, one request at a time. **`api.sam.gov`, NIGC and the state
  gaming regulators were off limits and were not contacted.**
- **SAM FY2000–2007**, for the finer distinction between
  `flag_american_indian_owned` (a **person**) and `flag_tribally_owned_firm` (an
  **entity**) — which reaches only 4 of 334 candidates today. [measured]

## A2. How the rows were made

`code/170_build_individual_native_candidates.py` →
`code/171_build_individual_native_verification.py` (the four-evidence table and
`compute_tier()`) → `code/172_write_individual_native_codebook_fragment.py` →
`code/173_refresh_individual_native_results_section.py` (regenerates §9 of the
build log **from the table**) →
`code/241_promote_individual_native_firms_in_place.py` (creates the class,
mints `CEDAR-ENT-nnnnnn` via `cedar_ids.allocate()` under the file lock,
promotes the 45 rulings in place) →
`code/242_build_individual_native_firm_contracts.py` (the class-scoped rollup
and the published cell table) → `code/243` / `code/244` →
`code/575_closure_native_owned_businesses.py conserve` (the row-conservation
ledger) → `code/358_measure_sam_individual_native_class_delta.py`.

| table | rows | one row = |
|---|---:|---|
| `individual_native_firm_register.csv` | **45** | one firm ruled into the class |
| `individual_native_firm_contracts.csv` | 324 | one (firm, fiscal year) |
| `individual_native_firm_contracts_published.csv` | 613 | one published aggregate **cell** |
| `individual_native_ownership_verification.csv` | 335 | one verification candidate, with four independent evidence fields |
| `individual_native_verification_candidates.csv` | 335 | one candidate UEI staged |
| `individual_native_prior_rulings.csv` | 45 | one prior ruling and its propagation |
| `individual_native_exclusion_pairs.csv` | 5 | one (identifier, excluded entity) ruling |

[measured]

## A3. How entities were attributed

**The class keys on the FIRM, never on the person**, on a Cedar-minted
surrogate `CEDAR-ENT-nnnnnn`. `parent_native_entity` is permanently NULL,
`ultimate_parent_entity_id` is the entity's own id, and `ownership_basis` reads
`INDIVIDUAL_NATIVE_OWNER_NOT_A_TRIBAL_ENTITY`. **It rolls up to nothing and
appears in no tribal total.**

Register [measured]: `evidence_tier = A` on all 45; `evidence_grade =
elijah_ruling` on all 45; `ruling_class` INDIVIDUAL_NATIVE 40 /
**INDIVIDUAL_NATIVE_NOT_TRIBAL 5**; `ruling_outcome` AFFIRM 40 /
**REFUSE_TRIBAL_LINK_AFFIRM 5**; `identifier_type` UEI 40 / NAME 3 / CAGE 2;
`temporal_caveat` populated on **100%**; `consent_status = NOT_ASKED` on all
45; `publish_name` 1 on 34 / 0 on 11.

Verification table [measured]: **335 candidates carrying $36,313,241,503.80 of
contract rows**; `evidence_tier` **A 18 · B 160 · C 156 · X 1**;
`evidence_independence` FEDERAL_SELF_CERT_ONLY 156 · SELF_ASSERTION_ONLY 147 ·
INDEPENDENT_CORROBORATION 31 · INDEPENDENT_CONTRADICTION 1; `ownership_class`
UNDETERMINED 146 · INDIVIDUAL_NATIVE 74 · NATIVE_UNSPECIFIED 47 ·
**ALASKA_NATIVE_CORPORATION 31 · NATIVE_HAWAIIAN_ORGANIZATION 30 ·
TRIBAL_ENTITY 6** · NON_NATIVE_OWNER_NAMED 1; `name_trap_warning` fires on
**41** rows (cherokee 30, river 2, creek 2, indian 3, united 2, pacific 1,
alliance 1, frontier 1).

### The tier rule is a pure function of INDEPENDENCE, not of weight

**A SAM flag and the firm's own website are the same party speaking in two
venues.**

| tier | requires |
|---|---|
| **A** | at least one leg that is **not the firm**, plus a second agreeing leg |
| **B** | exactly one non-SAM leg |
| **C** | federal self-certification only |
| **X** | a source names a **non-Native** owner against the flag — a *finding*, sent to review with its evidence, never a deletion |

A CAGE registry lookup, a GAO decision or an OpenCorporates filing lifts a
ruling to an independent leg. **A company website does not.**

**Not every "third party" is a third party, and applying that cost 21 tier-A
rows.** Directory hits (govtribe, highergov, govconinabox, opengovus) are
**SAM-derived**; PRNewswire and PRLog print what the company pays for. Applying
`third_party_independence` moved **tier A from 39 to 18**, and every demotion
surfaced in the review queue with its URL.

## A4. Decisions that shaped the data

### Seeded from 45 rulings, not from 305 candidates

*A ruling is evidence. A candidate is a question.*

### A ruling is NOT tier A because its method is "ruled"

`elijah_ruling` is in the RULED set whether the owner said yes or no.
`148_resolve_schedule_i_recipients.py` wrote `tier = "A" if method in RULED`
and **published 317 of the owner's tier-X EXCLUSIONS as tier-A attributions.**
So `241` branches on the ruling's **OUTCOME** through an exhaustive
`RULING_OUTCOME` map, and **an unrecognised outcome aborts the run.**
`tier_source` records which path fired on every row.

### The five rulings that look like refusals and are not

*"Not a Native entity — individually Native-owned firm"* refuses the **tribal
link**, not Native ownership. Read as "not Native", it inverts the owner's
meaning and deletes five firms. They are carried as
`INDIVIDUAL_NATIVE_NOT_TRIBAL` with
`refuses_tribal_link_not_native_ownership = 1`, so the **direction** of the
refusal stays visible.

### `owner_tribal_affiliation_named` stays free text forever

It is an attribute of a **person**, never an edge of the firm, and it is never
keyed to an entity. **31 of the 45 rulings read "owned by individual
Cherokees"** — the Cherokee Nation does not own those firms, and "Cherokee"
does not resolve to one entity anyway (three federally recognised Cherokee
tribes plus a long tail). If a relationship row is ever wanted it must use
`owner_self_identifies_with`, which is in `cedar_domain.NEVER_OWNERSHIP` and
**carries no money, ever.** ($27.59B was once booked wrong on exactly this
confusion.)

### A mnemonic slug was rejected as a primary key

`INDV-GANJEROB-00`, built from a person's name, **is** the disclosure — minted
into every downstream join. The measurement forced it: **2,594 of the 9,258 SAM
firms carry a legal name that reads as a person's name** (740 of 2,912 in the
individual class, 25.4%; 1,854 of 6,346 in the entity class, 29.2%), against
the 8 the privacy section had originally been written from.

### The UEI carve-out

SAM's public entity search resolves a UEI to a legal name **and a street
address**, so for a firm whose legal name is a person's name **the UEI
publishes the name by one hop.** It is withheld wherever
`firm_legal_name_is_person` is 1 or UNKNOWN. There is deliberately **no
surrogate-keyed per-firm publishable view**: a digest of a UEI is reversible by
enumerating SAM's entity space.

### Small-cell suppression, reported rather than dropped

`individual_native_firm_contracts_published.csv`: 613 cells, **375 suppressed /
238 published**, rule = *"Fewer than 3 firms resolve to this cell. A one- or
two-firm cell in a class of privately owned firms is a person's name."*
[measured] **The 613 rows overlap — summing them gives $17,074,665,885.33
against a true class total of $2.34B.**

### The two classes are NEVER summed, and the reason is directional

From the first 15 rulings: tribally and ANC-owned **7,329 rows / $2.76B**;
individually Native-owned **14,029 rows / $0.98B** — *larger by row count,
smaller by dollars*. **Summing moves both numbers in opposite directions from
the truth.** `242` writes a separate table rather than a column on
`prime_contracts.csv`, precisely so the $244.77B attributed total is untouched.

### A positional id fabricated an attribution, and a re-run caught it

`verification_id` was `INV-nnnn`, assigned in descending obligation order, and
the web pass was dispatched keyed on it. **At 17:57 on 2026-08-26 a concurrent
agent rewrote `prime_contracts.csv`, Iyabak Construction crossed into the top
400, the set went 334 → 335, and every id below the insertion point shifted by
one.** Result: `INV-0307 Cherokee Construction, Inc.` carrying **Frontier
Electronic Systems' sentence and URL**, complete with a fetch date. **Nothing
errored.**

Fix: re-key on **UEI → CAGE → normalised name** [measured —
`web_pass_matched_on` is UEI on 334 of 334], keep `web_pass_verification_id` as
the id held at pass time, and report loudly on either side of a non-match.
**Standing rule earned: never join two artefacts on a rank, an index or a row
number when both derive from a file another agent can write.**

### The federal flag is a discovery channel with a measured blind spot, never a definition

**22 of the 40 prior-ruled firms carry ZERO Native self-certification on any
contract row.** The largest is **Frontier Electronic Systems Corp — 998 rows,
$204,225,019, not one Native flag** — ruled `INDIVIDUAL_NATIVE` from the
company's own site. Also Cherokee Energy Management & Construction, Cherokee
Holdings, Cherokee Veterans Construction, Cherokee Controls, Bank of Cherokee
County.

**A flag-defined candidate set drops 29 of the 45 rulings on the floor**, which
is why `candidate_basis = PRIOR_OWNER_RULING` exists as a second entry route.
The caution is recorded with it: this is a **Cherokee-heavy sample** (31 of 45
from one do-file pass), so the *direction* is established and the *magnitude*
across Indian Country is not.

### 69% of the class's SAM dollars are not the class's money

Of 2,912 candidate firms carrying **$22,789,700,023** in the two individual SAM
variants: 17 are already in the class ($242M); **606 are already bound to a
tribe, ANC or NHO in the ledger — $15,721,934,154**; and 2,289 are new to both
register and ledger, $6,825,571,535 across 45,456 rows, every one
`UNRULED_CANDIDATE` at tier C. **The obvious reading — "$22.79B" — is wrong by
a factor of three, in the direction that discredits the dataset.**

### `soleProprietorship` was rejected as a classifier and kept as a tripwire

Four rows carry `YES` on the TRIBAL extract and **all four are tribally
owned** — including **CNI ADMINISTRATION SERVICES LLC, ultimate parent the
Chickasaw Nation.** It errs in both directions. It is used only to set
`firm_legal_name_is_person = UNKNOWN` and force the name through the privacy
gate.

### Absence is never disproof

The vocabulary is `NO_CLAIM_FOUND`, never `NOT_NATIVE`, and `SITE_UNREACHABLE`
is separate again — **only 404 and 403 are facts about an object; a 500 or a
TLS failure is a fact about the moment.** Wording is preserved rather than
tidied: *"founded" is not "owned"* (Arrow Indian Contractors); a badge is not a
sentence (Gearhart); *heritage is not ownership* (Firelake's "inspiration for
our company name"); *descent is not enrollment*; an NHO is not a tribe; and one
Mohawk affiliation is Canadian.

### Ownership changed inside the award window, repeatedly, with dates

At least nine firms: Aeromet (L-3, ~$20M, May 2003), ICRC (VSE, 2007-06-04),
Akimeka (VSE, 2010), TeraThink (CGI, 2020-03-31), Meyer Contracting (ESOP,
2024), Lakota Solutions (Shee Atiká), Arrowhead Contracting (Kava Equity /
Southern Ute Growth Fund), Sayres (Broadtree), **DAWSON → LAUKOA rebrand
2026-06-29 with UEI and CAGE unchanged** — invisible to every identifier-keyed
join — and Indian Eyes. **No single ownership answer is correct for the whole
span of any of those rows.**

### The temporal caveat is structural, and it bounds what anyone should look for

`temporal_caveat` is populated on **100%** of register rows, and the reason is
in the parent table: **all 209,478 FY2023–FY2026 rows in `prime_contracts.csv`
carry `attributed_flag = 1`**, because the archive backfill was seeded from
known Native identifiers. So **`attributed_flag = 0` selects the BGOV era
exclusively**, and every candidate's contract activity ends FY2022 or earlier.
A 2026 page is always testifying about a record at least four years old, and on
some rows twenty-six.

**Nobody should go looking for new individually-Native firms in FY2023+: the
absence there is a property of the pull, not of Indian Country.** Three gaming
rulings were withdrawn on 2026-08-06 for exactly this error.

### The by-product may be worth more than the product

Every candidate carries `attributed_flag = 0`, so firms whose own sites declare
a **tribal, ANC or NHO** owner are **missing tier-A entity attributions at the
dollar figure already in the row.** They are queued as `MISSING ENTITY
ATTRIBUTION` — **67 of the 164 review rows** — and the queue deliberately does
**not** propose an entity.

## A5. Known limits

- **Strand A is 45 firms**, against a candidate population of **2,289 new SAM
  firms / $6.83B** (51× larger by firm count) and a further **2,550
  unattributed awardees in `prime_contracts.csv` carrying a Native flag,
  holding $19.52B**. The top-400 cut is a priority order, not a universe.
- **156 of 335 candidates (46.6%) rest on federal self-certification alone.**
  Only **18 reach tier A**, only **34 carry any third-party source**, and only
  **31 name a specific tribe** — an unnamed "Native American owned" cannot be
  checked against a roll and cannot be joined to the spine.
- **Web-pass coverage**: CLAIM_FOUND 141 (42.2%) · NO_CLAIM_FOUND 50 (15.0%) ·
  SITE_UNREACHABLE 37 (11.1%) · **NO_SITE_FOUND 106 (31.7%)** · NOT_CHECKED 1.
  150 of 335 carry a verbatim website sentence, covering $19,749,769,004.
- **The web pass's largest known bias, named:** **every one of the twelve
  batches exhausted its search budget**, most partway through and one before
  its first query. **The 106 `NO_SITE_FOUND` rows are a ceiling on absence, not
  a measurement of it.** And `web.archive.org` was blocked for this
  environment's fetch tool — for a candidate set whose activity ends FY2022 and
  reaches back to FY2000, **the archive IS the route to award-period ownership
  language**, and it was shut.
- **Nine of the 45 register rows have
  `native_ownership_evidence_n_legs = 0`.** [measured]
- **No spine roll-up exists and none should be built.** Every tribal, ANC and
  NHO figure Cedar has published is unchanged by `241` and `242`.

## A6. Refresh

Strand A **has no cadence** — it is a ruling-driven register. Re-run `171` when
the two SAM individual-owned variants are joined; the join needs no change, but
**it is a sharper reading of one voice, never a second leg, and cannot move a
row to tier A.** `SITE_UNREACHABLE` rows should be retried through a real
browser, since several are TLS or connection failures the fetch tool handles
poorly.

---

## Stale claims found while writing this

1. **`docs/datasets/native-owned-businesses.md` says "NOTHING HERE PUBLISHES —
   every row carries `consent_status = UNRESOLVED`, `publishable = N."`**
   Measured: **`publishable = Y` on 2,047 of 2,393 rows**; only the 346 Navajo
   rows are N. `code/615` flipped them on 2026-09-01 under an explicit owner
   ruling. **`docs/REFRESH_CADENCE.md` repeats the same dead sentence** in this
   collection's `breaks_on_refresh` cell. **This is the most consequential
   stale line in the collection — it says nothing ships when 85% does.**
2. **`code/500_build_architecture_map.py`'s `COLLECTIONS` entry for this
   collection is stale**, and its regex and `dirs` list leave
   `native_owned_businesses.csv` claimed by no collection.
   `docs/DATASET_CONTRACTS.md` lists 7 tables for the collection and omits it
   too. The same entry's inline note about promoting the
   `tribal_certification_*` files from staging is still unactioned — 26 / 15 /
   62 / 60 / 14 rows remain in `data/staging/tribal_vendor_lists/`, all
   `publishable = N`.
3. **`docs/DATASET_READINESS.md` regenerated 2026-09-02 rates this collection
   READY** on 6 tables. Earlier generations of the per-dataset doc report it as
   one blocker short of the line. The scoreboard is the current statement.
4. **The Navajo/Colville/CTUIR terms verdicts rest on a different bar from the
   Chickasaw/FCP/Southern Ute/NANA ones** — a bare copyright footer against an
   actual terms page — and the two have never been reconciled. It is recorded
   here as an open decision rather than a defect, because resolving it
   unilaterally in either direction would either delete or expose real data.
