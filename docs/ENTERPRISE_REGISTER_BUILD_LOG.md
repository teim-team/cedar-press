# The tribal enterprise register, and the corrected business-list hit rate

*Written 2026-09-01 by WORKSTREAM ENTERPRISE. Script:
`code/701_enterprise_and_business_list_sweep.py`. Every figure below is
recomputable from `data/staging/tribal_enterprises/` and the files it names.*

---

## THE HEADLINE

**On the 297 tribes shards L and M swept, the hit rate with TERO-free
business-list vocabulary is 10.7%, against their 3.4%.**

| slice | rows | probed | LIST_FOUND | rate |
|---|---:|---:|---:|---:|
| **the 297 shard L+M tribes** | 286 | **234** | **25** | **10.7%** |
| the original 62-tribe registry | 62 | 45 | 3 | 6.7% |
| **all 348 registry hosts** | 348 | **279** | **28** | **10.0%** |

Shards L and M both returned **3.4%** independently, which read as
corroboration and was in fact two runs of the same instrument. The rate is
**3.1× higher** once the vocabulary stops assuming a TERO office. Shard L's own
broader count of 7.4% was the closest anyone got, and even that was an accident
— it came from two WordPress custom post types that happened to be named
`enterprise` and `tribalbusiness`.

**19 registry verdicts were corrected**: 16 rows that said `NO_LIST_FOUND` and
3 that said `LIST_REFERENCED_NOT_PUBLISHED` publish a business or enterprise
list. `review/tribal_vendor_list_registry_2026-08-26.csv` now carries
`verdict = LIST_FOUND_TERO_FREE_VOCAB` on those rows, with the prior verdict
preserved verbatim in the new `tero_free_sweep_2026-09-01` column.

### The two clearest false negatives, and why they happened

**Nez Perce.** Shard M enumerated **all 290** media files on `nezperce.org`,
read `X-WP-Total` correctly, ran custom post types, REST search and sitemap,
and recorded `NO_LIST_FOUND`. Sitting in that index it had already downloaded:

```
NPTCertifiedIndianBusinessList9617.pdf          media date 2018-01-28
```

The TERO pattern required `certified` adjacent to `business`. The file name
puts **`Indian`** between them. One token of separation, and a certified
Indian-owned business list disappeared from a survey that had the file in hand.
**It was recovered at zero network cost**, by re-reading
`data/staging/tribe_harvest/shard_m/media_inventory.csv` — 31,393 rows this
project already owned.

**Shakopee.** Shard M recorded `custom_post_types=True` for
`shakopeedakota.org` and returned `NO_LIST_FOUND`. The CPT list it captured
contains a post type literally named **`enterprise`**, holding **13** SMSC
businesses. The list was fetched, written to disk, and never read for business
vocabulary. Same for **Tlingit & Haida**, which shard L had ruled
`LIST_REFERENCED_NOT_PUBLISHED` on the strength of two empty sitemap pages
while a populated `enterprise` CPT and a rendered
`/about-us/tribal-enterprises/` index were both being served.

> **The lesson generalises past this workstream.** Three of the largest finds
> were already inside files a sibling shard had downloaded. The expensive part
> of a sweep is the fetching; the cheap part is asking a second question of
> what came back. `PULL_DISCIPLINE.md` tier 1 says re-read what you own before
> you pull, and it paid three times here.

---

## THE ENTERPRISE REGISTER

`data/staging/tribal_enterprises/enterprise_register.jsonl` — **293 subsidiary
rows across 24 nations**, of which **210 are `review_status = accepted`**.

A nation listing its own subsidiaries is **parent-asserted ownership**, the
evidence class shard E used for 482 ANC edges. It feeds the **hub / sub-hub
crosswalk** in `docs/IDENTIFIER_STANDARD.md`, not the vendor dataset.

| ruling on the candidate pages | n |
|---|---:|
| `ENTERPRISE_REGISTER` — harvested | 20 |
| `ALREADY_HARVESTED_SHARD_L` — re-found, cross-check on the method | 3 |
| `MEMBER_BUSINESS_LIST` — belongs to the vendor dataset, not here | 1 |
| `NOT_A_LIST` — carries the vocabulary, lists nothing | 7 |

Rulings are recorded per page in
`data/staging/tribal_enterprises/enterprise_pages.csv`, each with the evidence.

### Which technique produced them

| technique | rows |
|---|---:|
| shard L's registers, restated in this schema | 85 |
| `wp/v2/types` → a custom post type collection | 62 |
| `wp/v2/types` + REST search | 15 |
| `wp/v2/search` for `enterprise` | 20 |
| `sitemap.xml` (incl. one non-WordPress host, Crow) | 23 |
| offline re-read of files already on disk | 5 |

**Custom post types are the highest-yield single signal**, exactly as
`HIDDEN_DATA_TECHNIQUES.md` #3 says — and every CPT find is a register no
page-by-page crawl reaches, because the CMS renders it as individual pages with
no index.

### The new registers

Seneca (`enterprises` CPT, 8) · Calista (`subsidiary` CPT, 41) ·
Shakopee (`enterprise` CPT, 13) · Tlingit & Haida (`enterprise` CPT + index, 15)
· Cow Creek (12) · Crow (10) · Paskenta (5) · Cahuilla (5) ·
Pueblo of San Felipe (4) · Mescalero Apache (3) · Tunica-Biloxi (3) ·
Kickapoo of Texas (3) · Table Mountain (2) · Yurok (1) · plus St. Croix,
Wilton, Fort Sill Apache, Ponca of Nebraska and Mesa Grande, whose pages were
ruled registers but whose rendered markup yielded no clean firm names.

### Staleness is on every row

`source_edition_date` is populated on **94 of 210** accepted rows, from JSON-LD
`dateModified`, the WordPress `modified` field, or the media record's date.

```
2026  13     2025  51     2024   7
2023  12     2022   1     2021  10
```

Two dated finds are old enough to matter and are flagged as such:
**Nez Perce's Certified Indian Business List** encodes an edition of **9/6/17**
in its own filename, and **Shoshone-Bannock's TERO directory is
September 2022** — three years stale, which shard L had already recorded and
which this pass confirms is still the current edition on the site.

---

## THE CONTRADICTION — a hub is never its peer's subsidiary

**Doyon, Limited's own operating-companies page names `Huna Totem Corporation`
and `Klawock Heenya Corporation`.** Cedar keys both as Alaska Native **village**
corporations in their own right — `ANVC-HUNATO-00` and `ANVC-KLWCKH-00`.

`ANCSA_OWNERSHIP_RULING` does not let a regional corporation own a village
corporation, and Cedar is right. Doyon is telling the truth about a
*relationship*: these are its Alaska tourism **joint-venture partners**, and
`ENTITY_MATCH_RULES` rule 11 says a JV genuinely has two parents. Reading the
page at face value would have converted two independent ANCSA corporations into
subsidiaries of a third — the
`ALASKA_VILLAGE_GOVERNMENT_VS_VILLAGE_CORPORATION` family of defect (334
defects, $24.52B) reached from a new direction.

Both rows are held at `review_status = held_contradicts_cedar` with
`relationship` downgraded to `joint_venture`, and the rule that catches them is
general, not a patch for two rows: **where a named firm resolves to a Cedar hub
that is not the publisher, the row is held.**

Two implementation notes, because each nearly hid the finding:

- The match must check **every** candidate id, not the alphabetically first.
  Huna Totem matched both `A-0018` (a `native_owned_businesses` row) and
  `ANVC-HUNATO-00`. Sorting put the non-hub first.
- Shard L's Doyon extraction is a **prose scrape** and swept up page furniture
  alongside the firms — `"Enjoy lunch at Kantishna Roadhouse"`,
  `"KRH Earns Best Wilderness Lodge"`, `", Klawock Island Ventures, and"`. Those
  are held as `held_nav_furniture`. The underlying source
  (`TBD-059_doyon_operating_companies.jsonl`) has the same defect and is worth
  a re-extraction.

### Entity matching, honestly

Of 210 accepted rows, **3 carry a keyed Cedar candidate** (`Seneca Holdings` →
`SENECA HOLDINGS LLC`; `Tunista, Inc.` and `Brice, Inc.` → Calista;
`Tunica-Biloxi Holdings, Inc.` → its own nation) and **24 name a firm Cedar has
seen but never keyed** — chiefly the ASRC Federal family, present in
`native_owned_businesses.csv` with a null `business_entity_id`. That second
group is the more useful one: it is an adjudication backlog with a
parent-asserted ownership statement now attached to each name.

Nothing was minted, nothing was resolved, nothing was written to the spine or
to `data/clean`.

---

## THE FIVE FALSE-POSITIVE CLASSES, AND THE PREDICATE THAT KILLS EACH

Broadening the vocabulary broadens the noise. The first adjudication returned
**37.3%**, which was wrong. Each correction is a structural predicate, not a
word denylist — a denylist only refuses a word somebody already listed.

**1. The query echoed back.** REST-search hits carried the search term in the
title I had built (`[subsidiaries] Terms of Service`), so every result for
`subsidiaries` scored on its own query. *Fix: strip the prefix, judge the path.*

**2. A news story is not a register.**
`coquilletribe.org/tribal-enterprise-partners-with-forest-service/` matches the
vocabulary perfectly and is a press release. *Fix: a LIST lives at a short
slug; a STORY lives at a sentence. Five tokens is the empirical cut — the
longest correct slug observed is `/ponca-economic-development-corporation/` at
four; the false positives run to six and twelve.*

**3. A shared CMS template manufactures a fake cluster.**
`/BusinessDirectoryii.aspx` surfaced on **four** tribes at once — Quinault,
Northern Arapaho, Quapaw, Reno-Sparks. Four nations do not adopt the same URL.
It is the CivicPlus *Resource Directory* module. Read from a cached copy of
Northern Arapaho's at zero network cost, its 32 listings are *"Batterers
Intervention (BIP)"*, *"Community Health Representatives"*, *"Diabetes
Program"*, *"Ethete Child Care"* — government **programmes**, mixed with two
enterprises. Shard M had already ruled Quinault's copy this way; the ruling now
generalises to the template. **A lead for a later pass:** that page's own
Category `<select>` offers a *Tribal Business* filter, and
`HIDDEN_DATA_TECHNIQUES` #5 says a select IS the taxonomy. The filtered subset
may be a real list.

**4. A trademark notice is not a data-reuse restriction.**
`choctawnation.com/copyright-and-trademarks/` triggered the terms filter on
*"Unauthorized use ... may be trademark infringement"* — about its **logo**.
Refusing Choctaw on that would have been a false exclusion. The registry
already carries `TERMS_STATED_COPYRIGHT_ONLY` as a distinct non-excluding
verdict; this reproduces that distinction. **A publisher that means content
says so in content words** — copy, reproduce, redistribute, extract, scrape,
data mining — and those still bind.

**5. Site furniture in a heading scrape.** No amount of tuning removes the
last of it, so every HTML-derived row carries a `review_status` and only
`accepted` rows are counted: 75 held as navigation, 6 as a single generic word.

There is a sixth, caught in the smoke test before it did damage: an unbounded
`judi` in the hijacked-domain pattern matched **"Judicial Branch"** and flagged
`cherokee.org`, `cskt.org` and `gilariver.org` as hijacked. A false hijack
deletes a real nation from the sweep as silently as the robots false-block in
`PULL_DISCIPLINE.md`. Every token in that pattern is now word-bounded.

And a seventh, in this pass's own matcher: the single word **`Cultural`**,
scraped from Cahuilla's department nav, matched **Southern Ute** through a
one-token `brand` alias — the *exact* defect `ENTITY_MATCH_RULES` rule 1 was
written from, reproduced by a new script hours later. Rule 1 is now enforced
here: a name whose whole distinctive token set is generic may not win a
name-only match.

---

## THE IDENTITY_SCOPE GRADIENT WAS NOT FLATTENED

Copied from `data/clean/native_owned_businesses.csv`:

| what the source is | `identity_scope` |
|---|---|
| a nation's register of its own companies | `tribally_owned_entity` |
| an ANC parent's subsidiary list | `parent_asserted_subsidiary` |
| a member/citizen-owned business directory | `any_native` |
| a business **licence** register | `unknown` |
| a TERO or procurement **vendor** list | `vendor_relationship` |

Two rulings turn on this and both were made against the pattern's own verdict:

- **Nez Perce's Certified Indian Business List** is `MEMBER_BUSINESS_LIST`, not
  an enterprise register. These are firms the Tribe *certifies*, not firms it
  *owns*, and the row belongs in the vendor dataset.
- **Lower Elwha** hosts a PDF for the **Port Angeles** Chamber of Commerce — a
  non-tribal municipal chamber. Counting it would have converted a town's
  business association into Native-owned firms, which is precisely the Bad
  River two-table error (31 tribally owned + 8 area businesses) at a different
  address.

---

## TERMS AND EXCLUSIONS — one definition, in one place

`excluded_hosts()` is the **only** definition of what is off limits, and every
route calls `is_excluded()` — including `fetch()` itself, so no route can reach
a refused host even by mistake. It is built from the registry's **own**
`source_terms_status` / `consent_status` verdicts, unioned with the named list
in `docs/PUBLICATION_POLICY.md`, and it covers subdomains of a refused apex.

This is deliberate. Shard M's `--deep` mode re-probed a restricted host because
its check read a hard-coded constant instead of the verdict the same script had
written. **A verdict written by any pass now binds this one**, and the named
policy list is a floor rather than the source of truth, so a registry row
losing its verdict cannot silently re-open a refused publisher.

20 hosts excluded. Terms were read **before** enumeration on every host, and a
`TERMS_STATED_RESTRICTIVE` reading stops the host with nothing further
requested.

`robots.txt` is fetched with **our declared UA** and handed to
`RobotFileParser.parse()`. `.read()` fetches with `Python-urllib` and reads a
403 on the robots file as `disallow_all` — 22 hosts were lost to that in one
shard today. A 404 or an empty file means allowed; only a real `Disallow` is a
refusal, and two hosts (Ely Shoshone, Penobscot) genuinely are.

---

## WHAT WAS NOT REACHED, so the gap stays visible

Of 348 registry hosts, **279 were probed**. The other 69:

| reason | n |
|---|---:|
| unreachable by every rung of the ladder | 26 |
| the served page never names the entity, on any rung | 24 |
| `TERMS_STATED_RESTRICTIVE` / policy exclusion | 11 |
| `robots.txt` Disallow on `/` | 3 |
| other | 5 |

**The 42 are the honest weak point of this pass.** A domain that answers is not
the right domain — six hijacked or lapsed tribal domains were found on
2026-09-01 serving a Thai casino, Indonesian slots, adult video, an electronics
blog, a link farm and a porn redirect — so the name check has to stay. But a
check that fails closed for the wrong reason costs real work, and one such bug
was found and fixed mid-run: the first version re-fetched the homepage to run
the check and, where the second fetch behaved differently from the rung that
had worked, read an empty string and recorded *"does not name the entity"*.
Thirteen live tribal sites — Red Lake, Menominee, San Carlos, Standing Rock
among them — were deleted from the sweep by a check that never saw the page.
It now judges the bytes that actually answered, and also matches a name printed
with the spaces closed up (`RedLakeNation`).

**Those hosts were re-run twice**, and the two retries recovered **8 tribes and
one more enterprise register** (Spokane, `/government/tribal-enterprises/`).
Diagnosis of the residue, by hand:

- `redlakenation.org` serves a **689-byte IIS7 placeholder** at the apex; the
  site is on `www`. The ladder now keeps going.
- `menominee-nsn.gov` is 321 KB titled *"MITW - Home Page"* and the word
  *Menominee* first appears past the old 200,000-character scan window. **A
  truncated read that reports "absent" rather than "truncated"** is the same
  defect `PULL_DISCIPLINE.md` records for cut-off PDFs. The window is now the
  whole document.
- `chitimacha.gov` returns **HTTP 307 into a Sucuri JavaScript challenge**
  (*"Javascript is required"*). Genuinely unreachable to an automated client;
  shard M recorded the same 307. Not a false negative.

The 24 that still never name their entity are a real residue and are recorded
as such, not as absences of a list.

---

## SELECTION DECLARATION

Leg used: **KNOWN_IDENTIFIER only** — the 359 rows of the vendor-list registry,
which is the spine's federally-recognized tribe roster plus the original
62-tribe survey. There is no TYPE_FILTER for *"tribe that publishes a business
list"*: no registry of such lists exists to filter on, so the identifier leg
here **is** the population, not a sample of one. `population_basis` on every
row emitted is `spine_federally_recognized_tribe`.

Cost: **6,637 requests** across 348 hosts plus two retries, ~19 per host, one poller, 1.2s
between requests to the same host, no host blocked, no deadline truncation.
An API call returning 100 media rows is gentler than 100 page fetches, which is
part of why `HIDDEN_DATA_TECHNIQUES.md` exists.

## Files

```
data/staging/tribal_enterprises/
  enterprise_register.jsonl        293 rows, 24 nations, 210 accepted
  enterprise_pages.csv             the per-page rulings and their evidence
  verdicts.csv                     348 tribes, per-tribe verdict + routes run
  business_list_candidates.jsonl   the zero-network offline re-read
  host_log.jsonl                   per host: robots, terms, routes, hits
  raw/                             every CPT collection and page harvested
  _state.json                      run state, selection leg, request count
review/tribal_vendor_list_registry_2026-08-26.csv
  + tero_free_sweep_2026-09-01     new column, all 348 rows annotated
  backup: .bak_2026-09-01_pre701
code/701_enterprise_and_business_list_sweep.py
```

---

## GATE AND HANDOFF

`py -3 code/62_no_regression_check.py` → **exit 1**, on lines that were already
red and are already attributed to their owners in the
`## GATE ATTRIBUTION 2026-09-01` entry at the end of `AGENTS.md`:
`contract_orphan_shippable`, `contract_violations`,
`files_with_columns_lost_vs_backup` (= `entity_evidence_profile.csv`),
`lint_new_defect_instances` (= `518_dataset_readiness.py` and
`73_faads_name_attribution.py`, the only two findings new against the lint
baseline), `rulings_unapplied`, the three codebook/`25_TABLES` lines, and
`SHIPPING LOST: advocacy_passthrough_2026-08-07.csv` (deregistered, still on
disk, fifth workstream to stop on it).

**This workstream contributes nothing to any of them, and that is checked, not
asserted.** `docs/lint_bug_classes.json` carries **zero** findings in
`701_*`; the diff against `lint_bug_classes_baseline.json` on the baseline's
own `class|file|evidence` key returns exactly the two class6 rows named above;
and nothing under `data/clean/`, `dist/`, or the spine was written. The one
shared file touched is `review/tribal_vendor_list_registry_2026-08-26.csv`,
which **gained** a column and lost none, with a backup at
`.bak_2026-09-01_pre701`.

Handoff **HAND-FCC0FF3895**, recorded `--by "enterprise"`, UNVERIFIED — a
different session must run the verify.

## WHAT THE NEXT PASS SHOULD DO, in order of cheapness

1. **The 24 hosts whose served page never names its entity.** Some are real
   WAF challenges (`chitimacha.gov`, Sucuri 307) and some are apex placeholders
   the ladder has not yet outflanked. Each is a tribe currently absent from the
   rate's denominator.
2. **The CivicPlus `Tribal Business` category filter.** Four tribes serve the
   Resource Directory module and its Category `<select>` names a *Tribal
   Business* subset. `HIDDEN_DATA_TECHNIQUES` #5: a select IS the taxonomy.
3. **Re-extract `TBD-059_doyon_operating_companies.jsonl`.** It is a prose
   scrape carrying page furniture and two joint-venture partners recorded as
   operating companies.
4. **Work the 24 `name_present_in_cedar_but_unkeyed` rows**, chiefly the ASRC
   Federal family. Each now has a parent-asserted ownership statement attached
   to a name Cedar holds with a null `business_entity_id`.
5. **Ask.** Nine publishers are excluded on their own stated terms and the
   Navajo NBOA source list — the strongest lower-48 find in the whole survey —
   is one of them. `PUBLICATION_POLICY.md`: *asking is the route back in; a
   cleverer scrape is not.*
