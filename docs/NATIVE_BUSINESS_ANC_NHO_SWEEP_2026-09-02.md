# ANC / NHO / Alaska Native Village business-directory sweep — build log

*Written 2026-09-02 by the NBOA-EXPAND workstream. Every figure below was
re-counted from the live staging files with `csv.reader` on the date written;
where a figure comes from another document it says so.*

**Scripts:** `code/1070_anc_nho_business_sweep.py` (the web sweep) and
`code/1073_ancsa_consolidation_subsidiaries.py` (the offline ANCSA mine).
Both carry `verify` and `selftest`; both `selftest`s pass with **every** invariant
firing on an injected violation — eight in `1070` (V1-V8), six in `1073`
(W1-W6) — and both `verify`s report **0 violations** on the final outputs.

**Nothing here was committed and nothing was written to `data/clean/`.**

---

## 1. Why this pass exists

The owner:

> *"I wanna make sure for gaming and the business dataset that you're scraping
> like every tribal website and ANC and NHO that could have stuff. The native
> business dataset should be the easiest to do, to be honest."*

`docs/methodology/native-owned-businesses.md` §B6 measured the gap he was
pointing at:

```
NHOs 0 of 210 · village corporations 0 of 173 · BIE schools 0 of 185
```

`code/701_enterprise_and_business_list_sweep.py` swept 279 hosts and swept
**one class** — the 349 federally recognised tribes of
`review/tribal_vendor_list_registry_2026-08-26.csv`. Shard E reached 22 ANC
parents through ANCSA filings and shard H reached 30 NHOs through a single
Wayback capture of the NHOA member page. **Nobody had ever opened an Alaska
Native Village Corporation's own website, a Native Hawaiian Organization's own
website, or an Alaska Native Village government's own website looking for a
business list.**

## 2. The population, and why it is a population and not a sample

`spine_entity_class` on the 1,555-row spine, joined to
`data/staging/cedar_web_map.csv` for a host. There is no register of "Native
entities that publish a business list" to filter on, so the identifier leg IS
the population.

| workstream class | spine classes | entities | with a host |
|---|---|---:|---:|
| `anc` | ANC Regional (12) · ANC Village Corp (173) · ANCSA Group Corp (6) | 191 | 191 |
| `nho` | Native Hawaiian Organization | 210 | 126 |
| `tribal_government` | Fed. rec. Alaska Native Village (225) · Fed. rec. tribe not probed by 701 (76) · State-recognised tribe (64) | 365 | 328 |
| `intertribal` | Intertribal Organization | 56 | 48 |
| **total** | | **822** | **693** |

`web.archive.org`, Facebook, X, LinkedIn, YouTube and Google Docs are dropped
as candidate hosts. The web map records them as an entity's "organization"
URL; probing them would run the terms check, the robots check and the name
check against **the platform**, whose terms are not the nation's. The Wayback
route is a legitimate later rung when an origin is gone; it is not the origin.

## 3. What was run per entity, in order

Imported from `701` so there is exactly one definition — `excluded_hosts()`,
`is_excluded()`, `fetch()`, `robots_ok()`, `reach()` and the terms patterns.
Shard M re-probed a restricted host four hours after refusing it because its
`--deep` path read a hard-coded constant instead of the verdict the same
script had written. **A refusal recorded in one code path is enforced from one
place every other path reads.**

1. `robots.txt` fetched with **our** UA and handed to `RobotFileParser.parse()`
2. the ladder: https/http × apex/www × our UA / browser headers / relaxed TLS
3. **the served page must NAME the entity**
4. terms, **before** any enumeration
5. `/wp-json/wp/v2/types` — custom post types
6. `/wp-json/wp/v2/search` — class vocabulary
7. `/wp-json/wp/v2/media?per_page=100`, paginated, unfiltered by MIME
8. `sitemap_index.xml` / `sitemap.xml` / `wp-sitemap.xml`
9. **nav-link fallback** where neither a sitemap nor the REST API answered

### Four things this pass had to add, each because the old rule was measured wrong

**A name check that survives an ʻokina.** 701 tokenises on `[^a-z]`.
`Kaʻala Farm` and `Hawaiʻi Maoli` shatter into fragments and **every NHO would
have been recorded as "the served page does not name the entity"** — a false
negative that silently deletes 210 entities from the study. Unicode is folded
on both sides and the corporate stopwords (Incorporated, Corporation,
Foundation, Association) are dropped the way 701 drops Tribe/Band/Nation.

**Class vocabulary.** 701's vocabulary is a tribal government's. An ANC says
*operating companies*, *family of companies*, *lines of business*, *8(a)
subsidiaries*; an NHO says *member directory*, *affiliates*. This is the same
defect `docs/HIDDEN_DATA_TECHNIQUES.md` records for TERO terms one level up:
searching a corporation with a nation's nouns measures the nouns.

**A collection noun standing alone is a list.** CIRI publishes its operating
companies at `/enterprise/` and ASRC Federal at `/companies/`. Both scored
WEAK in the canary because 701's `LIST_SHAPED` wants a list *word* beside the
noun ("enterprise directory") and a corporation does not write that.

**A repeating first path segment is a collection.** Bristol Bay publishes 200+
sitemap URLs under `/affiliate/<company>/` and scored `MENTION_ONLY`, because
every other rule judges one URL at a time and each individual company page's
slug is a sentence. The sitemap is telling us the shape of the data. Judge the
set, not the member — and read each member's name from **that page's `<h1>`**,
never from the URL slug: `bristol-bay-construction-holdings-llc` title-cases
to "Llc".

## 4. Result — 822 entities, every one with a verdict

`data/staging/native_business_sweep_1070/verdicts.csv`

| verdict | anc | intertribal | nho | tribal gov | total |
|---|---:|---:|---:|---:|---:|
| LIST_FOUND | 21 | 3 | 4 | 2 | **30** |
| MENTION_ONLY | 12 | 12 | 16 | 24 | 64 |
| NO_LIST_FOUND | 18 | 26 | 53 | 50 | 147 |
| NOT_SEARCHED_MACHINE_READABLE | 6 | 1 | 12 | 12 | 31 |
| DOMAIN_NOT_THE_ENTITY | 19 | 2 | 21 | 86 | 128 |
| HIJACKED_OR_WRONG_DOMAIN | 4 | 0 | 2 | 0 | 6 |
| UNREACHABLE | 105 | 1 | 26 | 135 | 267 |
| NO_HOST_KNOWN | 0 | 8 | 73 | 37 | 118 |
| TERMS_STATED_RESTRICTIVE | 2 | 3 | 3 | 7 | 15 |
| EXCLUDED_TERMS (refused before contact) | 1 | 0 | 0 | 10 | 11 |
| ROBOTS_DISALLOW | 3 | 0 | 0 | 2 | 5 |
| **total** | **191** | **56** | **210** | **365** | **822** |

Rolled up:

| class | published a list | answered, none published | refused by terms/robots | no usable site |
|---|---:|---:|---:|---:|
| anc | 21 | 36 | 6 | 128 |
| intertribal | 3 | 39 | 3 | 11 |
| nho | 4 | 81 | 3 | 122 |
| tribal_government | 2 | 86 | 19 | 258 |
| **total** | **30** | **242** | **31** | **519** |

**Hit rate among entities whose site actually answered: 30 of 272 = 11.0%.**

Two findings in that table matter more than the hit rate.

**`no_usable_site` is 519 of 822 and it is not this sweep's failure.** 105 of
191 ANCs are unreachable by every rung of the ladder — village corporations
overwhelmingly do not run a website. 128 entities served a page that does not
name them, 86 of them Alaska Native Village governments whose web-map URL
points at a borough, a regional consortium or an ArcGIS service. **That is a
finding about `cedar_web_map.csv`, and it is handed back rather than
absorbed**: those URLs are not the entity's own site and the map records them
as though they were.

**`EXCLUDED_TERMS` = 11 means eleven publishers were refused before a single
request left this machine.** They are named in
`docs/PUBLICATION_POLICY.md` and in 701's `EXCLUDED`, and they stay refused by
every route including Wayback and the media API.

## 5. The second route, which needed no network at all

`code/1073_ancsa_consolidation_subsidiaries.py`. The mandate names it:

> *"ANCSA audited filings under Alaska Statute 45.55.139 are a separate,
> richer route"*

**The filings were already on this machine** — `docs/AGENT_FIELD_GUIDE.md` §5,
`ON_DISK_NOT_PROMOTED`. `code/1031` had fetched 358 audited annual reports
covering 41 **village** corporations, 2016–2026, and extracted 50 of them.
Shard E mined `ancsa_txt/` and `ancsa_txt_v2/`; **it never saw
`ancsa_txt_v3`.** Extraction of the remaining 308 was restarted and the
"Principles of Consolidation" note mined:

> The consolidated financial statements include the accounts of Azachorok,
> Incorporated and its wholly owned subsidiary **Azachorok Contract Services,
> LLC** (collectively, the Corporation).

That is a parent asserting ownership of a named company in a document an
independent auditor signed and the State of Alaska holds.

**Final run over the complete corpus: 358 documents, 41 village
corporations.** 225 documents named subsidiaries, 48 carried a note that
named none, 85 had no consolidation note in the text layer. **34 of the 41
corporations yielded at least one named subsidiary; 265 distinct children;
1,094 (parent, child, edition-year) rows.** By stated relation:
`wholly_owned` 961 · `equity_or_jv` 102 · `majority_owned` 22 ·
`subsidiary_unspecified` 9.

**Four outcomes per document, and the third is a real result:**

| outcome | meaning |
|---|---|
| `NAMES_EXTRACTED` | the note names the subsidiaries |
| `NOTE_PRESENT_NAMES_NOT_STATED` | Afognak: *"its majority-owned subsidiaries (collectively, the Corporation), most of which are limited liability companies."* The corporation **has** subsidiaries and the audited statement declines to name them. Recording that as "no subsidiaries" would be a false negative. |
| `NO_CONSOLIDATION_NOTE_IN_TEXT` | no such note in the text layer — often an image-only scan whose OCR is thin |
| — | every document has a row in `ancsa_document_log.csv` either way |

### The extraction rule, and the four ways the first version was wrong

A company name is **a run of capitalised tokens ending in a corporate
suffix**. The first version split the note on `;` / `and` / `,` and kept any
fragment ending in a suffix. Measured on the real corpus that produced:

```
"majority-owned subsidiaries , most of which are limited"
"as well as one mineral development company"
"2016 (3) Acquisitions On April 18, 2017, the Company"
"o Bethel Builders LLC"          <- an OCR'd bullet
```

Every one of those ends in a word that **is** a corporate suffix, which is
exactly why a suffix test at the end of a fragment does not work. The
structural fact that separates a name from a sentence is that **the word
before the suffix is capitalised** — "Contract Services, LLC" but "are
limited". Four further guards, each from a measured false positive:

- six tokens maximum — an un-punctuated OCR run merged three Ouzinkie
  subsidiaries into one 8-token name
- a two-word name whose head is a generic business noun is a fragment
  ("Certified Company", "Development, Inc")
- `X is a subsidiary of Y` — **Y must be this document's own filer.**
  Gwitchyaa Zhee's report discusses Doyon, and the first version filed Doyon
  as Gwitchyaa Zhee's subsidiary
- the stored quote is **windowed on the name**, not truncated to the first 400
  characters. A consolidation note runs to 1,600 characters and the tenth
  subsidiary it lists sits past any head-truncation; ten rows shipped a quote
  that did not contain the name it was evidence for, and invariant W2 caught
  it

Shard E's 482 hand-adjudicated edges are loaded and **those pairs are never
re-emitted**. A duplicate that looks like corroboration is the worst kind.

## 6. What is staged, and the two tiers

`data/staging/native_business_sweep_1070/staged_native_owned_businesses_2026-09-02.csv`
— the **58-column `native_owned_businesses.csv` schema exactly**, so it is a
merge candidate and not a new table. `data/clean/native_owned_businesses.csv`
was never opened for writing.

De-duplicated against three things: the live clean file on
(authority, normalised name); shard E's ANC edges; and itself.

**Two tiers, and the second is kept rather than deleted.** Measured over the
harvest: the WordPress custom-post-type route, the HTML `<table>` route and
the sitemap-member route were clean; the HTML heading/anchor scrape returned
real subsidiaries mixed with "NAICS Code: Healthcare", "Press Release",
"Fairbanks" and "Shareholder Portal". A row stages if its route is structured,
**or** its name carries a corporate signal, **or** it came off a page whose
own path says *directory* and which yielded eight or more names — flagged
`HEADING_SCRAPE_ON_A_DIRECTORY_INDEX`. Everything else goes to
`candidates_for_review_2026-09-02.csv` with its URL and the reason.

That third tier exists because of one page. **USET's Tribal Enterprise
Directory returned 471 names** — Akwesasne Farmers Market, Choctaw Fresh
Produce, Passamaquoddy Maple Syrup, Penobscot Indian Nation Fish and Game —
and 425 of them carry no LLC/Inc/Services token. The corporate-signal rule
would have thrown away the single richest directory in the sweep on the
grounds that a farmers market is not spelled like a defence contractor.

### Final counts

**1,106 rows staged from 54 certifying authorities, 1,086 distinct firms,
0 verify violations.**

| authority class | rows | authorities |
|---|---:|---:|
| Alaska Native Village Corporation | 385 | 44 |
| Alaska Native Regional Corporation | 198 | 7 |
| Intertribal Organization | 523 | 3 |

Dropped on the way in: 952 within-run duplicates (the ANCSA corpus repeats a
parent-child pair once per filing year — every edition survives in the
JSONL), **156 that duplicate shard E's hand-adjudicated ANC edges**, 11 that
duplicate the live clean file, 6 from an authority whose site was never
established as its own, and 370 held for review.

### The gradient was not flattened

`identity_scope` per source, never invented:

| scope | what the source actually said |
|---|---|
| `parent_asserted_subsidiary` | an ANC's operating-company page, or an audited consolidation note |
| `tribally_owned_entity` | a nation's own enterprise register |
| `shareholder_descendant_or_spouse` | an ANC's **shareholder** business directory |
| `association_member` | **new value.** An NHO or intertribal association's member list is a list of organisations that joined it — not an ownership claim of any strength, and none of the 14 existing scopes says it |
| `tribally_owned_entity_of_a_member_nation` | **new value, and the one that matters most.** USET's directory lists Choctaw Fresh Produce and Passamaquoddy Maple Syrup. Those **are** tribally owned — by the Mississippi Band of Choctaw and the Passamaquoddy Tribe, **not by USET**, which is the keyed authority on the row. Writing `tribally_owned_entity` there would assert an ownership the source never asserted, which is the one thing the affiliation rule exists to prevent. `assertion_class` is `RELATIONSHIP` on these 468 rows for the same reason, and **a consumer that sums OWNERSHIP and RELATIONSHIP has added two different facts.** |

Final distribution:

```
parent_asserted_subsidiary                  513
tribally_owned_entity_of_a_member_nation    468
shareholder_descendant_or_spouse             61
association_member                           55
tribally_owned_entity                         9
```

`assertion_class`: OWNERSHIP 583 · RELATIONSHIP 523.

Two column decisions a merge must know about:

- **`certification_tier` is deliberately left empty.** In the live file it
  holds a TERO preference priority ("Priority 1", 693 rows). An ANCSA
  ownership relation is a different fact in the same shape, and putting it
  there would give one column two vocabularies — the `extent_competed`
  defect. The relation rides in `verification_basis` and in
  `validation_flags` as `RELATION=wholly_owned|majority_owned|equity_or_jv|
  subsidiary_unspecified`, and **the merge should give it a column.**
- **`inclusion_basis` gains a second value.** All 2,393 live rows read
  `program_authority`. A directory row is that. An ANCSA row is not — it is
  `audited_filing_as_45_55_139`.

### Privacy

No `owner_name_raw`, email, phone or street-address column is written.
`identity_claim_text` is a verbatim quote and is **redacted** for
address- and contact-shaped spans before it is staged: two ANCSA quotes
carried "2201 Buena Vista Drive" and "925 Park Avenue", the addresses of
hotels a corporation owns. Almost certainly not a person's home; the cost of
dropping them is nil and the policy line is that a street address does not
ship from this table. The unredacted quote survives in the staging JSONL.
A **firm's** name always publishes, person-shaped or not — the 521-row
over-withholding the owner reversed is not repeated; `business_name_raw`
is written verbatim and `business_name_is_person_name` is left undecided
(`-1`) rather than guessed at.

## 7. What the numbers say about the remaining coverage

- **The ANC class is now done on both routes.** 191 of 191 websites probed;
  21 published a list; 105 have no reachable site at all. All 358 AS 45.55.139
  filings are extracted and mined. Where a village corporation has no website
  — the common case — **the audited filing is the only route, and it worked**:
  44 village corporations now certify rows, against 0 before this pass.
- **The NHO class answered and published almost nothing.** 210 probed, 4
  `LIST_FOUND`, and every one of those four yielded only navigation furniture
  once fetched. **Zero real NHO business rows came off NHO websites.** The
  NHO business record lives in the SBA 8(a) register and in the NHOA member
  directory shard H already read — not on the members' own sites. Treating
  "NHOs 0 of 210" as a scraping backlog is the wrong model; it is
  `SOURCE_DOES_NOT_PUBLISH` for most of the class.
- **Alaska Native Village governments are a web-map problem before they are a
  harvest problem.** 86 of 225 served a page that does not name them.
- **The best remaining web target is the intertribal class**: 3 of 42 that
  answered published a list, and one of those three (USET) was worth 468
  staged rows on its own. Regional intertribal councils, tribal chambers of
  commerce and gaming associations aggregate what the individual nations do
  not publish. There are 56 in the spine and 8 have no host recorded.

## 8. Files written

```
code/1070_anc_nho_business_sweep.py
code/1073_ancsa_consolidation_subsidiaries.py
data/staging/native_business_sweep_1070/host_log.jsonl
data/staging/native_business_sweep_1070/verdicts.csv
data/staging/native_business_sweep_1070/business_rows.jsonl
data/staging/native_business_sweep_1070/business_rows_ancsa.jsonl
data/staging/native_business_sweep_1070/ancsa_document_log.csv
data/staging/native_business_sweep_1070/staged_native_owned_businesses_2026-09-02.csv
data/staging/native_business_sweep_1070/candidates_for_review_2026-09-02.csv
data/staging/native_business_sweep_1070/raw/          (every body that produced a row)
docs/NATIVE_BUSINESS_ANC_NHO_SWEEP_2026-09-02.md      (this file)
logs/1070_sweep_2026-09-02.log · logs/1070_sweep_b.log · logs/1070_harvest_b.log
logs/1031_extract_2026-09-02.log
```

`code/1031 ... extract` ran to completion during this pass (358 of 358) and
`code/1073 ... mine` was re-run over the full corpus; both verifies are clean.
If the corpus grows again, invariant **W5** fails until every extracted
document has a log row — which is how you know it grew under you.

## 9. Handed to other workstreams, not absorbed

- **CAGE/UEI harvest (1000–1009):** the staged rows carry
  `federal_identifier_match_status = NOT_ATTEMPTED`. Identifiers seen on ANC
  operating-company pages were not collected here.
- **`cedar_web_map.csv` owner:** 128 entities whose recorded URL serves a page
  that does not name them, and 6 whose domain is hijacked or parked. Named
  per entity in `verdicts.csv` with the route that was tried.
- **The integrator:** `review/tribal_vendor_list_registry_2026-08-26.csv` was
  **not** appended to. 701 owns that file and its 359 rows are federally
  recognised tribes; these 822 entities are a different population.
  `verdicts.csv` is the record and should be merged deliberately, not by an
  agent writing into another workstream's shared file.
