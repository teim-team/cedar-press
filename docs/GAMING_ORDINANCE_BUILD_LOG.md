# Tribal gaming ordinances — build log

> ## ⚠ SUPERSEDED ON EVERY PROVISION COUNT by `docs/GAMING_ORDINANCE_OCR_MERGE_LOG.md`
> *Flagged 2026-08-26.*
>
> The OCR merge log states that it *"supersedes this document on every count it restates."*
> That was the right thing to write — but a banner on the **new** document only helps
> readers who find the new document, and **this is the file people open**, because it is
> named after the dataset.
>
> | measure | this log says | after OCR merge |
> |---|---:|---:|
> | `tribal_gaming_agency_named` rows | 741 (:149) | **973** |
> | …tribes | 284 of 321 (:149, :225 as 296 of 321) | **307** |
> | …distinct agency names | 397 (:149) | **469** |
> | `licensing_provisions` rows | 728 | **932** |
> | …tribes | 296 (:225) | **317** |
>
> **`docs/GAMING_SPEC_RECONCILIATION.md:196` carries the same superseded figures and is not
> named as a companion by either log**, so nobody following the pointer will find it.
>
> **Also: "321 tribes" is wrong, and this document already says so.** Lines 269–270 state
> plainly *"So NIGC's 321 rows are not 321 distinct tribes"*, and :327 gives 305 of 321
> resolving. Measured against `data/clean/gaming_ordinances.csv` on 2026-08-26:
> **299 distinct `tribe_id`, 55 rows carrying none, 314 distinct `tribe_name`.** So 321 is
> wrong **and 305 is also wrong.** The row arithmetic (321 `ORIGINAL_ORDINANCE` + 834
> `AMENDMENT` = 1,155) is correct everywhere it appears; only the tribe count is bad. It has
> propagated into `START_HERE.md` and `GAMING_SPEC_RECONCILIATION.md:155` as "321 tribes"
> and is corrected there.

Code: `code/118_build_gaming_ordinances.py` (`fetch` / `parse` / `reconcile` /
`codebook`).
Source: NIGC Office of General Counsel, *Gaming Ordinances*,
<https://www.nigc.gov/office-of-general-counsel/gaming-ordinances/>,
retrieved 2026-08-12.
Raw: `data/raw/external/nigc_ordinances/` — index HTML + CSV, 1,151 PDFs
(3.12 GiB), `_SOURCE_MANIFEST.csv` with md5 and HTTP status on every file.
Writes: `data/clean/gaming_ordinances.csv`,
`data/clean/codebook/07f_gaming_ordinances.csv`,
`review/ordinance_compact_diff_2026-08-12.csv`,
`review/ordinance_unresolved_2026-08-12.csv`,
`data/interim/118_run_summary.txt`.

Nothing else was written. `compacts.csv`, `compact_structured_terms.csv`,
`gaming_facilities.csv`, `gaming_capacity_official.csv`, `nigc_*`,
`gaming_device_observations.csv`, `ca_gaming_*`, `wa_*`, `fl_*`,
`tribal_tax_bases.csv`, `prime_contracts.csv`, `federal_funding_transactions.csv`,
`subawards.csv`, `entity_*`, the identifier ledger, the spine and
`codebook_master.csv` were **read only or untouched**.
`code/62_no_regression_check.py` passed before and after.

Numbers here are reproduced from `data/interim/118_run_summary.txt`, which the
script writes on every run. Re-run the script rather than editing a figure.

> **SUPERSEDED IN PART, 2026-08-26 — read
> `docs/GAMING_ORDINANCE_OCR_MERGE_LOG.md` alongside this file.** The 264
> image-only scans this log records as an OCR backlog (§2, §8.5) have been OCR'd
> and integrated by `code/153_merge_ordinance_ocr.py`. **Every extraction count
> in §3 and §6 below is now a floor, not the current figure** — class II rows
> 530 → 670, tribal gaming agency rows 741 → 973, `PER_CAPITA_PLAN_ASSERTED`
> tribes 15 → 22, and tribes with no class determinable 32 → 10. The figures
> below are left exactly as `118` computed them, because they are that run's
> output and a hand-edited number is a claim, not a fact (standing rule 10). The
> current figures are in the merge log and in
> `data/interim/153_run_summary.txt`.

---

## 1. Why this is a distinct universe, not a duplicate of the compacts

Under IGRA the two instruments cover different populations:

- **Class III gaming requires a tribal-state COMPACT.** We hold 707, reaching
  276 tribes.
- **Class II gaming requires an NIGC-approved tribal gaming ORDINANCE and no
  compact at all** (25 U.S.C. 2710(b)).

Every tribe conducting regulated gaming has an ordinance; only the class III
tribes have a compact. So the ordinance universe is strictly **wider**, and the
part it adds is exactly the class II population the compact work cannot see.

Elijah, 2026-08-07: *"what about gaming ordinances, which are all available I
believe and distinct from compacts — maybe they will provide some additional
information."*

---

## 2. What was retrieved

| | n |
|---|---:|
| Tribes on NIGC's index | **321** |
| Original ordinances | **321** |
| Amendments | **834** |
| **Instrument rows** | **1,155** |
| Approval-date range | **1985-12-02 – 2026-02-12** |
| PDFs retrieved (HTTP 200) | 1,151 |
| Distinct md5s | 1,148 |
| Bytes | 3,355,311,519 (3.12 GiB) |
| Fetch failures | 1 (NIGC's own link is not a URL — §4) |
| Amendment counts | 1 instrument 67 tribes · 2 → 71 · 3 → 54 · 4 → 39 · 5 → 32 · 6 → 26 · 7+ → 32. Most amended: **Bay Mills Indian Community, 23 instruments** |

Every instrument is a row. **Amendments are stored historically and nothing is
overwritten** — an ordinance amended four times is five rows, each carrying
`effective_range_start`, `effective_range_end`, `in_force_status`,
`supersedes_ordinance_id` and `superseded_by_ordinance_id`. Two rows carry
`supersedes_basis = stated_in_document_date_matched` because the approval letter
names the superseded instrument and its date (*"supersedes Ordinance No. 15
Concerning Gaming, approved by the NIGC Chair on November 15, 1993"*); the rest
are `chronological_prior_instrument`.

**An amendment amends; it does not necessarily replace.** NIGC's own 2008 letter
to the Absentee Shawnee Tribe says the amendment *"replaces the introductory
sections and Title I of the Tribe's gaming ordinance, leaving Titles II-V in
place."* `supersedes_ordinance_id` therefore means *the instrument this one
follows*, not *the instrument this one voids*.

### Text layer

| `text_layer_status` | rows |
|---|---:|
| `TEXT_LAYER_PRESENT` | 886 |
| `IMAGE_ONLY_SCAN_NO_TEXT_LAYER` | 264 |
| `NO_DOCUMENT_LINKED_ON_INDEX` / `NOT_RETRIEVED` | 4 |
| document belongs to another tribe (§4) | 1 |

**23% of the archive is an image-only scan with no text layer.** A near-empty
extraction is a scan, not an empty document, and is recorded as such rather than
read as "nothing in it". Those rows still carry a verbatim `source_quote` from
NIGC's own index cell and a `source_url`, so the zero-fabrication contract holds
on all 1,155 rows — the assertion is in the code.

---

## 3. What was extracted, and what each field can carry

### 3.1 Classes authorised — the core product

| | rows | tribes |
|---|---:|---:|
| Class II authorised | 530 | **266** |
| Class III authorised | 502 | **249** |
| Both | — | 229 |
| **Class II only** | — | **37** |
| No class determinable from any instrument | — | 35 |

`classes_basis` records how each was established, highest precision first:

| basis | rows |
|---|---:|
| `authorisation_section_heading` | 392 |
| `authorising_verb_window` | 134 |
| `authorisation_word_near_class_token` | 58 |
| `ordinance_scope_statement` | 47 |
| `instrument_title_names_class` | 22 |
| `no_authorising_language_found` | 233 |

The 233 with no authorising language are overwhelmingly **amendment approval
letters that contain no ordinance text** — a two-page letter approving a change
to a licensing section says nothing about classes. That is why the class
question is answered at tribe level, across all of a tribe's instruments, and
not per row.

**A class NAMED in a definitions section has not been AUTHORISED.** The compact
build refused 1,296 rows for exactly that confusion and the same guard runs
here: a bare class token never yields a row.

**Authorisation is not operation.** Every row carries
`authorisation_measurement_type = LEGAL_AUTHORISATION_NOT_A_COUNT`, and the
build asserts at startup that
`cedar_domain.may_promote(AUTHORIZED_MAXIMUM, ACTIVE_FLOOR_COUNT)` is `False`.
A floor can be swapped between classes with no federal record, so the class
actually operated is **unobservable here** and this file does not claim it.

### 3.2 The tribal gaming agency register

**284 of 321 tribes name a tribal regulatory body**, 741 rows, **397 distinct
names**, of which **363 carry the tribe's own distinctive tokens**
(`tribal_gaming_agency_basis = tribe_specific_name`); 206 rows name a generic
body ("the Tribal Gaming Commission").

This answers a question the compact parse raised and could not close. That build
found **674 reporting obligations running to a *Tribal* Gaming Agency** rather
than a state one, and named none of them. These are the bodies: Sycuan Gaming
Commission, Muckleshoot Gaming Commission, Pueblo of Santa Ana Gaming Board,
Cheyenne River Sioux Tribe Gaming Board, Puyallup Tribe Gaming Regulatory
Office, Tonto Apache Gaming Office, Kickapoo Traditional Tribe of Texas Gaming
Regulatory Authority, Alabama-Coushatta Tribal Gaming Regulatory Authority, and
so on. Nobody has assembled this list, and it is a direct measure of tribal
regulatory capacity.

Two guards, both earned on this corpus:

- **The National Indian Gaming Commission is the federal regulator, not a
  tribe's own agency.** Filing it as one inverts the fact the column exists to
  record. OCR spells it wrong and it slips a plain string filter — *"NeHonel
  Indian Gaming Commission"* was written as Ysleta del Sur's gaming agency
  before `NIGC_LOOKALIKE` refused any `... Indian Gaming Commission` sharing no
  distinctive token with the tribe.
- **Lowercase connectors must be inside the name.** Without `of`, the
  capitalised run breaks and the body is truncated to its tail: *Jena Band of
  Choctaw Indians Gaming Commission* became "Choctaw Indians Gaming
  Commission", and *Kickapoo Traditional Tribe of Texas Gaming Regulatory
  Authority* became **"Texas Gaming Regulatory Authority"** — which reads as a
  state agency.

### 3.3 Revenue Allocation Plans and per capita — the finding that contradicts the brief

**343 rows / 196 tribes reference a revenue allocation plan.** But the
per-capita split is the point:

| `per_capita_referenced` | rows | tribes (strongest value across the tribe's instruments) |
|---|---:|---:|
| `PER_CAPITA_CONDITIONAL_RECITATION` | 300 | 160 |
| `PER_CAPITA_REFERENCED_UNQUALIFIED` | 111 | 42 |
| `PER_CAPITA_PROHIBITED` | 33 | 20 |
| `PER_CAPITA_PLAN_ASSERTED` | 19 | 14 |
| `PER_CAPITA_TABLE_OF_CONTENTS_ONLY` | 3 | 1 |
| `NOT_REFERENCED` | 420 | 84 |

The brief for this build assumed *"an ordinance referencing [a RAP] tells you
per-capita distribution exists."* **Measured on the corpus, that is not true.**
The overwhelming majority of per-capita language is the conditional statutory
recitation of 25 U.S.C. 2710(b)(3):

> "If the Tribe elects to make per capita payments to tribal members, it shall
> authorize such payments only upon approval by the Secretary of the Interior
> under 25 U.S.C. § 2710(b)(3) and 25 C.F.R. §§ 522.4(b)(2)(ii) and 522.6(b)."
> — Alabama-Coushatta Tribe of Texas gaming ordinance

That sentence proves the ordinance **contemplates** per capita. It does not
prove a plan exists or that a dollar was ever distributed. Reading it as
evidence of distribution is the same class of error as reading a compact's
authorised device cap as an operating floor count.

**The 15 tribes with at least one instrument at `PER_CAPITA_PLAN_ASSERTED` are
the real lead** — the ordinance states in the indicative that the tribe *has
elected* to make per capita payments or that a plan *has been approved*. They
are Cheyenne and Arapaho Tribes of Oklahoma, Chitimacha Tribe of Louisiana,
Confederated Tribes of the Siletz Reservation, Crow Creek Sioux Tribe, Dry Creek
Rancheria of Pomo Indians, Eastern Band of Cherokee Indians, Lac du Flambeau
Band of Lake Superior Chippewa Indians, Oneida Nation, Pokagon Band of
Potawatomi Indians of Michigan, Ponca Tribe of Indians of Oklahoma, Prairie
Island Indian Community, Quapaw Tribe of Indians, Tohono O'odham Nation,
Tunica-Biloxi Tribe of Louisiana and Ute Mountain Ute Tribe. Those are the ones
worth chasing to an Interior-approved Revenue Allocation Plan.

**20 tribes prohibit per capita outright**, which is an equally real economic
fact and one nobody records.

### 3.4 Licensing and internal controls

**296 of 321 tribes** carry licensing provisions; the enumerated features are
`KEY_EMPLOYEE_LICENSE`, `PRIMARY_MANAGEMENT_OFFICIAL_LICENSE`,
`FACILITY_LICENSE`, `BACKGROUND_INVESTIGATION`, `VENDOR_LICENSE`,
`SUSPENSION_REVOCATION`, `GAMING_EMPLOYEE_LICENSE`,
`ELIGIBILITY_DETERMINATION`.

**254 rows / 149 tribes** carry an internal-control reference (MICS, TICS,
25 C.F.R. Part 542/543).

### 3.5 Signatory and dates

**395 rows carry a signatory, 69 distinct** — Anthony J. Hope, Ada E. Deer
(Acting Chair), Tracie Stevens, Jonodev Chaudhuri, E. Sequoyah Simermeyer,
Sharon M. Avery (Acting Chairwoman) and others. The rest are lost to OCR of the
signature block.

`effective_date` is populated on only **26 rows** — an ordinance's own effective
date is rarely stated, and it is **never inferred from the approval date**.

---

## 4. Defects in NIGC's own index, found and recorded rather than smoothed

`index_anomaly` carries these on the affected rows.

**(a) One link, two dates.** `wpdmdl=3252&ind=3246` is printed in the Absentee
Shawnee row as **both** the 1995-01-10 original ordinance and the 2008-03-25
amendment, and the file served is the 2008 amendment. So the 1995 original is
listed but not reachable. `INDEX_LINK_PRINTED_UNDER_MORE_THAN_ONE_DATE`.

**(b) The same PDF served for a DIFFERENT tribe.** Kialegee Tribal Town's
2022-06-02 amendment link (`wpdmdl=10058`) and the Kalispel Tribe's
(`wpdmdl=10013`) are different links returning a **byte-identical** file —
Kalispel's, and the resolved object is literally named
`20220602_Kalispel_Ord_Amend_Apprl-1.pdf`. Trusting the index would have written
Kalispel's ordinance under Kialegee's name. **Only md5s catch this**: the byte
lengths, the dates and the links all look right. That row is refused
(`confidence = document_served_belongs_to_another_tribe`) and carries no
extracted content.

**(c) A duplicate tribe listing.** NIGC lists Santa Ysabel twice — once as
*Iipay Nation of Santa Ysabel (Formally …)* and once as *Santa Ysabel Band of
Diegueno Mission Indians* — with two different `wpdmdl` ids serving the same
PDF. That is a duplicate listing, not a mislink, and is labelled
`SAME_PDF_UNDER_TWO_INDEX_NAMES_SAME_TRIBE`. **So NIGC's 321 rows are not 321
distinct tribes.**

**(d) An href that is not a URL.** The Cahto Indian Tribe of the Laytonville
Rancheria 1996-11-26 row carries
`href="http://Cahto Indian Tribe of the Laytonville Rancheria"` — the tribe's
name pasted into the link. It is the single fetch failure.
`INDEX_LINK_IS_NOT_A_URL`.

**(e) An approval date three years before IGRA.** The Muscogee (Creek) Nation
row prints an amendment date of **1985-12-02**. IGRA was enacted 17 October
1988, so that cannot be an NIGC approval date.
`INDEX_DATE_PRECEDES_IGRA_ENACTMENT`. The date is kept as printed and flagged.

### The download trap, re-confirmed and defeated

`docs/NIGC_REGION_BUILD_LOG.md` §15 records that every `nigc.gov/download/<slug>/`
page carries a sidebar WPDM link with the same `wpdmdl=`, so matching the first
`wpdmdl=` returns the identical PDF 24 times and looks like success. **On this
page the trap presents differently and worse** — the links are per-instrument
and correct-looking, and the collisions are in NIGC's data rather than in the
scraper. The three guards that held: take links only from inside
`<table id="tablepress-1">`, md5 every file and record a duplicate as a
collision rather than accepting it, and re-read the approval date from the
letter.

### Date agreement

| `date_agreement` | rows |
|---|---:|
| `LETTER_DATE_NOT_FOUND` | 552 |
| `AGREE` | 316 |
| `NO_TEXT` | 264 |
| `DISAGREE_DOCUMENT_IS_ANOTHER_INSTRUMENT` | 9 |
| `AGREE_WITHIN_45_DAYS` | 5 |
| `LIKELY_OCR_YEAR_MISREAD` | 4 |
| `NO_DOCUMENT` / `NO_USABLE_DOCUMENT` | 5 |

A first pass produced **117 false disagreements**, every one of which would have
looked like an index defect. The cause: the NIGC letterhead date is usually a
scanned date **stamp** (`NOV 1 5 1993`, `WAR 2 7 2000`, `APR 13 2C05`) that OCR
cannot parse, so the first parseable date on the page was the **tribe's
submission date** — *"This letter responds to your letter of January 10, 2000"*.
The extractor now reads only the region **before the salutation**, rejects dates
led by *letter of / dated / submitted on / adopted on / received on*, and accepts
a spaced-digit stamp. **A date the OCR destroyed is a miss, not a licence to
take the nearest parseable number**, so 552 rows carry
`LETTER_DATE_NOT_FOUND` and the index date stands unchallenged.

`LIKELY_OCR_YEAR_MISREAD` exists because four disagreements share month and day
and differ by one to three years on a scanned letterhead. Calling those an index
defect would be the stronger claim on the weaker evidence.

---

## 5. Entity keying — 305 of 321, and the four guards that got there

The one resolver (`33_apply_party_rulings.resolve_entity`) was imported, never
re-implemented. **305 of 321 NIGC tribe names resolve; 16 go to review at Tier
B.** 165 names reach `entity_tier = A`; the rest are B.

**Guard 0 — the spine VIEW is restricted to ordinance-eligible classes.** An
IGRA gaming ordinance is approved for a federally recognised tribe or Alaska
Native village. A tribal college, a BIE school, a CDFI or an ANCSA corporation
can never hold one, so they are not candidates. This is a domain restriction on
the candidate pool, not a new matcher, and it is the guard AGENTS.md records as
one that works. Measured: it is what stops **`Keweenaw Bay Indian Community`
resolving to Keweenaw Bay Ojibwa Community *College*** — containment scores the
college higher because it shares two tokens with the record while the tribe's
short canonical name `Keweenaw` shares one. 577 of 1,310 spine entities are
eligible.

**Guard 1 — state disagreement refuses.** States are parsed from the tribe's own
name as a **set**, because three traps each produced a wrong state on the first
pass: the *leading* token is the tribe's name and not a state
(`Alabama-Coushatta Tribe of Texas`, `Delaware Nation, Oklahoma`, `Iowa Tribe of
Kansas and Nebraska`, `Colorado River Indian Tribes`), some names carry **two**
states (`Washoe Tribe of Nevada and California`), and token-sequence matching is
required so `Otoe-Missouria` does not read as Missouri.

**Guard 2 — the record must be at least as specific as the entity.** Containment
rewards the shortest spine name; that is how `NATIVE VILLAGE OF ELIM` once
landed on *Elim Native Corporation*.

**Guard 3 — a trap-token-only containment match does not link on its own, but
does with state corroboration.** `Oneida Nation of New York` shares only the
trap token `oneida` with the spine's `Oneida`, and that **is** the New York
nation. Refusing it outright was measured and cost a correct match, so the state
is allowed to be the second leg. This is the failure mode AGENTS.md records for
over-eager guards, avoided by measuring rather than assuming.

**Guard 4 — the Federal Register official name as a verification leg.** Measured
on all 321 names: it **agrees** with the resolver 242 times, and **conflicts
once** — `Flandreau Santee Sioux Tribe`, which max-overlap containment sent to
**Santee Sioux (Nebraska)** because that shares two tokens while the correct
entity's short canonical name `Flandreau` (South Dakota) shares one. That row is
refused and queued. Before the guard, Flandreau's five instruments were booked
to the wrong nation and Flandreau itself appeared as "compact but no ordinance".

**It is never used to RESOLVE a name the resolver refused.** Measured on the 16
refusals it would have produced 7 answers of which **at least 3 are wrong** —
`Cherokee Nation, Oklahoma` to the *United Keetoowah Band*, `Shawnee Tribe of
Oklahoma` to the *Eastern* Shawnee Tribe. That is the shape of guard AGENTS.md
records as measured-and-removed, so it was not built.

Tier A requires two independent legs: an exact/core/alias name match **plus**
either state agreement or official-name agreement. **Containment never reaches
A** whatever corroborates it.

`review/ordinance_unresolved_2026-08-12.csv` holds one row per unresolved tribe
name — not per instrument — with the resolver's reason, the question, a
`YOUR_RULING` column, and a verbatim source quote.

---

## 6. The reconciliation — three populations

`review/ordinance_compact_diff_2026-08-12.csv`, 339 rows.

| Population | Tribes |
|---|---:|
| Ordinance (keyed to the spine) | **298** |
| Ordinance (name-only, unresolved) | 16 |
| Compact | 276 |
| On the NIGC gaming location map | 213 (110 mapped locations carry no keyed tribe) |

| `population_class` | tribes |
|---|---:|
| `ORD+CMP+MAP` | 188 |
| `ORD+CMP+---` | 70 |
| `ORD+---+---` | 45 |
| `ORD+---+MAP` | 11 |
| `---+CMP+---` | 11 |
| `---+---+MAP` | 7 |
| `---+CMP+MAP` | 7 |

### 6.1 THE HEADLINE — ordinance but no compact: 40 tribes

These are **class II operators by statute**: they hold an NIGC-approved gaming
ordinance and no tribal-state class III compact.

Alabama-Coushatta · Alabama-Quassarte Tribal Town · Bridgeport · California
Valley · Cayuga Nation of New York · Cloverdale · Delaware Tribe of Indians ·
Eklutna · Ely Shoshone · Fort McDermitt · Greenville · Grindstone · Guidiville ·
Jena · Kake · Kashia · Kickapoo of Texas · Klawock · Koi · Lytton · Metlakatla ·
Miccosukee · Paiute-Shoshone · Passamaquoddy · Poarch · Quartz Valley · Redwood
Valley · Resighini · Round Valley · Santa Rosa of Cahuilla · Santee Sioux ·
Santo Domingo · Scotts Valley · Shinnecock · Shoshone-Bannock · Te-Moak · The
Seminole Nation of Oklahoma · Tlingit & Haida · Wampanoag · Ysleta del Sur.

**29 of the 40 carry class II authorisation in the text of an instrument.**
Eleven have an NIGC-mapped location; **29 do not** — authorised, not observed
operating.

**16 unresolved names are EXCLUDED from that count and reported separately.**
Joining them on a missing key would score every one of them as "no compact", and
several of them (Viejas, Santa Ysabel, Mille Lacs, Cherokee Nation, St. Regis)
certainly do hold class III compacts. Counting them would have inflated the
headline by 40% with tribes that contradict it.

### 6.2 Ordinance but no NIGC mapped location: 115 tribes

Authorised, not observed operating. **An ordinance is an authorisation, not an
operation**; a tribe may hold an approved ordinance and run nothing, and this
build never infers a facility from one. The other reading is equally live: NIGC's
map holds 490 locations against 545 FY2025 audited-financial-statement
operations, so absence from the map is also a property of the map.

### 6.3 Compact but no ordinance on the NIGC index: 18 tribes, 15 unexplained

Three are the mirror of the unresolved index names above (Flandreau, Viejas,
Shoshone-Paiute). The remaining fifteen — Cherokee Nation, Fond du Lac, Fort
Sill-Chiricahua-Warm Springs-Apache, Havasupai, Hoh, Hopi, Little River,
Northern Arapaho, Ramona, Saint Regis, San Juan, Shawnee Tribe, United Keetoowah
Band, Walker River, Zuni — are unexplained.

**IGRA requires an approved ordinance for class III as well as class II.** So an
unexplained row here is a **gap in NIGC's published index**, not a tribe
operating without an ordinance. It is a lead for a hand pass, and the honest
reading of the index's completeness.

The two `name_level_*_candidate` columns are **leads for a human, never joins**.
A loose version of that test proposed `Cherokee Nation, Oklahoma` → *United
Keetoowah Band*, `Shawnee Tribe of Oklahoma` → *Absentee*-Shawnee and `Fond du
Lac` → *Mille Lacs*, so the test now requires every distinctive token of the
candidate to appear in the other name, excludes trap tokens **and state names**
(`Apache Tribe of Oklahoma` reduced to `{oklahoma}` and matched `Cherokee
Nation, Oklahoma`), and prints **all** qualifying candidates rather than picking
one.

---

## 7. Tiering

Every row is `tier = B`. These are algorithmic extractions with receipts, not
human rulings, and spec 10.1 lands automated results at B pending review.
**Nothing here publishes without a review pass.** `entity_tier` is carried
separately: 662 rows at A, 493 at B.

`confidence` is the evidentiary basis, not a probability:
`document_parsed` 886 · `document_no_text_layer` 264 · `index_only` 4 ·
`document_served_belongs_to_another_tribe` 1.

The codebook fragment is `data/clean/codebook/07f_gaming_ordinances.csv`, written
through `cedar_codebook.write_fragment`. **`codebook_master.csv` was not
touched** — it is a derived concatenation with a dozen writers.

---

## 8. What this archive structurally cannot tell us

1. **Which class is actually operated.** An ordinance authorises; a floor can be
   swapped between class II and class III with no federal record. 229 tribes are
   authorised for both, and for those the authorisation says nothing about the
   mix on any given day.
2. **Whether anything is operating at all.** No facility, device count, revenue
   figure or opening date can be inferred from an ordinance, and none is written
   here.
3. **Whether a Revenue Allocation Plan exists.** 160 tribes recite the statutory
   condition; only **15** assert a plan or an election. The Interior-approved
   RAPs themselves are a separate document series this build does not reach.
4. **Anything about gaming outside IGRA.** NIGC's ordinance jurisdiction is class
   II and class III **on Indian lands**. A tribally owned casino under a
   commercial licence off Indian lands never appears — the same ceiling
   `docs/NIGC_REGION_BUILD_LOG.md` §10 records for the location map.
5. ~~**The 264 image-only scans.**~~ **CLOSED 2026-08-26.** 263 of the 264 were
   OCR'd (the 264th is the Kialegee row serving Kalispel's file, still refused)
   and integrated by `code/153_merge_ordinance_ocr.py`; they now carry
   `text_layer_status = OCR_RECOVERED` and their provisions are read. Mean OCR
   confidence 0.8710, none below 0.70, no blank document. See
   `docs/GAMING_ORDINANCE_OCR_MERGE_LOG.md`. What remains is narrower and is
   **not** an OCR backlog: ten keyed tribes still have no class determinable
   because every instrument NIGC posts for them is an amendment approval letter
   containing no ordinance text.
6. **Recall is deliberately below precision throughout.** Every guard in §3 and
   §5 removes true positives along with false ones; each one's reason is recorded
   in the code beside it.
7. **NIGC's index is the only source.** A tribe with an approved ordinance that
   NIGC has not posted is invisible here — and §6.3 shows fifteen tribes with
   compacts and no posted ordinance, which is direct evidence that the index is
   incomplete.

---

## 9. Pull discipline

One poller, one host. `logs/_HOSTLOCK_www.nigc.gov.json` was claimed before the
first request and released on completion; no concurrent poller against
`nigc.gov` was found. Requests were sequential with a 2 s floor gap; **1,151 of
1,152 objects returned HTTP 200**, no throttling and no retries. The run was
interrupted once by an external process kill and **resumed from the manifest
checkpoint without re-fetching a single file**. `files.usaspending.gov`,
`api.usaspending.gov`, `apps.nd.gov` and `www.treasurer.nd.gov` were not
touched. No process was killed by image name; `Win32_Process` was used to
enumerate.
