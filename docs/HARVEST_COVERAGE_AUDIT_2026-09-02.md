# Harvest coverage audit — what was actually looked for, per entity, per thing

*Built 2026-09-02 by `code/1112_harvest_coverage_matrix.py`. This is an **audit**, not a
harvest. No network calls. Every number below is re-derived from artefacts on disk; no
coverage document was taken at its word, including `docs/SHARD_COVERAGE.md`.*

**Deliverable:** `data/clean/cedar_harvest_coverage_matrix.csv` — 1,555 entities × 5
harvest types = **7,775 rows**, each naming the artefact that proves its outcome.
Companion: `data/clean/cedar_harvest_coverage_evidence.csv` — **24,297** distinct
evidence records, one per (entity, type, outcome, artefact).

```
py -3 code/1112_harvest_coverage_matrix.py build
py -3 code/1112_harvest_coverage_matrix.py verify     # 8 invariants, exits 1 on breach
py -3 code/1112_harvest_coverage_matrix.py selftest   # PASSES: poisoned copy exits 1,
                                                      # clean copy exits 0, and the
                                                      # robots fixture fires correctly
```

---

## The outcome vocabulary, and why it has six values

The three the owner asked to keep apart — **harvested something**, **checked and it does
not exist**, **never checked** — plus the fourth he named, **refused on terms or robots**.
Two more were forced by the evidence, and collapsing either of them would have inflated
a number:

| outcome | means |
|---|---|
| `HARVESTED` | content rows for this entity and this thing exist in a table on disk |
| `REFUSED` | robots.txt bans the whole site, or the publisher states restrictive terms. **Narrowed 2026-09-02:** for a Native entity's own site the terms half no longer refuses (`PUBLICATION_POLICY.md`, `TERMS-OWNER-RULING-2026-09-02`), so the `REFUSED` counts in the headline table below are an **over-count** of what is still off limits and an **under-count** of the worklist. Re-run `code/1112` to re-derive them; do not hand-edit the numbers |
| `FOUND_NOT_EXTRACTED` | the surface was located and reached; nothing was pulled into a table |
| `CHECKED_ABSENT` | looked for, positively determined not published |
| `ATTEMPTED_INCONCLUSIVE` | an attempt is on record and it could not decide — host unreachable, no host known, or the page does not name the entity |
| `NEVER_CHECKED` | no artefact anywhere records an attempt |

`FOUND_NOT_EXTRACTED` exists because a TERO page that answers 200 is not a vendor list in
a table, and calling it "harvested" is how a coverage number stops meaning anything.
`ATTEMPTED_INCONCLUSIVE` exists because **266 unreachable hosts and 127 wrong domains are
not evidence that a list does not exist** — they are evidence that we could not tell.

`REFUSED` outranks `FOUND_NOT_EXTRACTED` deliberately. A surface located on a host that
has refused us is not a surface we may act on.

---

## THE HEADLINE — how many of the 1,555 have genuinely never been looked at

| thing | HARVESTED | REFUSED | FOUND_NOT_EXTRACTED | CHECKED_ABSENT | ATTEMPTED_INCONCLUSIVE | **NEVER_CHECKED** |
|---|---:|---:|---:|---:|---:|---:|
| enterprises / subsidiaries | 144 | 35 | 6 | 411 | 504 | **455 (29.3%)** |
| **CAGE / UEI / DUNS** | 85 | 11 | 17 | 3 | 0 | **1,439 (92.5%)** |
| individual Native business directories | 58 | 54 | 216 | 276 | 501 | **450 (28.9%)** |
| gaming | 255 | 9 | 33 | 0 | 1 | **1,257 (80.8%)** |
| newsletters / press | 694 | 8 | 8 | 472 | 0 | **373 (24.0%)** |

**Read the gaming row against the right denominator.** 1,257 "never checked" is not a
gap: only **284 of the 1,555 operate a known gaming facility**
(`gaming_facilities.csv`, `cedar_uid` + `operating_entity_cedar_uids`), and among those
284 the split is **255 HARVESTED · 28 FOUND_NOT_EXTRACTED · 1 inconclusive · 0 never
checked**. Gaming is the one dimension that is genuinely finished.

**No such excuse exists for CAGE / UEI / DUNS.** Every entity is in scope, and 92.5% of
them have never had a capability statement or government-contracting page looked for.
The 85 `HARVESTED` come almost entirely from `native_business_identifier_crosswalk.csv`
and `nest_enterprises.csv`, i.e. from businesses *under* an entity, not from the entity's
own published statement.

### 189 entities have never been looked at for **any** of the five

- **185 BIE Schools** — every one of the 185, on all five things. 182 of them have a live
  website in `cedar_web_map.csv`. No shard ever ran a content harvest over them; shard_g
  mapped their URLs and stopped.
- **4 Native CDFIs.**

### NEVER_CHECKED by entity class

| class | enterprises | identifiers | indiv. business | gaming | newsletter | n |
|---|---:|---:|---:|---:|---:|---:|
| Federally recognized tribe | 0 | 307 | 0 | 67 | 8 | 349 |
| Federally recognized Alaska Native Village | 0 | 228 | 0 | 225 | 45 | 228 |
| Native Hawaiian Organization | 0 | 185 | 0 | 210 | 97 | 210 |
| BIE School | **185** | **185** | **185** | **185** | **185** | 185 |
| Alaska Native Village Corporation | 0 | 173 | 0 | 173 | 0 | 173 |
| Native CDFI | 63 | 64 | 64 | 64 | 4 | 64 |
| State-recognized tribe | 0 | 63 | 0 | 64 | 2 | 64 |
| Intertribal Organization | 0 | 56 | 0 | 51 | 3 | 56 |
| Individually Native-owned business | 45 | 0 | 45 | 45 | 29 | 45 |
| Urban Indian Organization | 43 | 43 | 43 | 43 | 0 | 43 |
| Tribal College or University | 37 | 37 | 37 | 37 | 0 | 37 |
| Native Financial Institution | 29 | 29 | 29 | 29 | 0 | 29 |
| Federal-level self-governance consortium | 29 | 29 | 28 | 29 | 0 | 29 |
| Federal-level constituency entity | 21 | 22 | 16 | 14 | 0 | 22 |
| Alaska Native Regional Corporation | 0 | 9 | 0 | 12 | 0 | 12 |
| ANCSA Group Corporation | 0 | 6 | 0 | 6 | 0 | 6 |
| State-level constituency entity | 3 | 3 | 3 | 3 | 0 | 3 |

The zeros are real and they are the good news. **Every federally recognized tribe, every
Alaska Native Village, every ANC and every NHO has had enterprises and individual-business
directories genuinely looked for** — by `native_business_sweep_1070`,
`tribal_enterprises`, shard_l, shard_m and the 359-tribe
`review/tribal_vendor_list_registry_2026-08-26.csv`. The institution classes — schools,
colleges, urban Indian orgs, CDFIs, financial institutions, consortia — are where nobody
went.

---

## Where the reported numbers were wrong

| claim | re-derived |
|---|---|
| `docs/SHARD_COVERAGE.md`: **untouched = 0** for every class | **True, and it measures site discovery, not harvest.** All 1,555 entities do appear in `data/staging/cedar_web_map.csv`. That is the only thing it establishes. Per *thing*, untouched runs from 373 to 1,439 |
| `docs/SHARD_COVERAGE.md`: shard_l and shard_m **NOT_STARTED**, 0 map rows, 0 entities | **Both ran.** shard_l holds 152 entity verdicts across `_verdicts.jsonl` + `_verdicts_auto.jsonl` and 13 probe logs; shard_m holds a 148-entity deep probe and a 149-entity host log. They wrote no rows into the web map, so a shard table keyed on map rows reports them as never started |
| `docs/SHARD_COVERAGE.md`: **1,254 with a URL** | **1,275** entities have ≥1 2xx URL of a non-dead type; 1,484 have any non-blank URL string. Neither is 1,254 |
| gaming web harvest = **1,166** observations | file holds **1,175** |
| newsletter corpus = **1,195** | file holds **1,889** — 1,394 `publication_channel` + **481 `probe_absence`** + 13 flagged + 1 contact-point. The absence rows are the most valuable part of that table and quoting 1,195 hides them |
| `native_owned_businesses.csv` 2,916 · `nest_enterprises.csv` 1,610 | **confirmed exactly** |
| 127 entities point at a site that does not name them | **confirmed exactly** — 127 `DOMAIN_NOT_THE_ENTITY`, plus 6 `HIJACKED_OR_WRONG_DOMAIN`, so 133 entities carry the flag |
| 14 spine entities have an all-stopword name | **7 re-derived** with the stopword list in `code/1112` (`Council`, `Eek`, `Koi`, `Ute`, `Council Native Corporation`, `Alaska Native Village Corporation Association`, `Hawaiian Native Corporation`). The 14 is not reproducible from any list on disk; the four named in `docs/NATIVE_BUSINESS_ANC_NHO_SWEEP_2026-09-02.md` are all in the 7 |

### One defect this audit created and caught in itself

The first cut of the refusal detector tested `"Disallow" in robots_note`. It fired on
`no Disallow directives` (34 hosts) and on `Disallow: /wp-admin/` (24 more), and reported
**106 individual-business refusals where the honest number is 54** — the repo's signature
defect, inside a detector written to find that defect. Replaced with
`robots_bans_whole_site()`, which fires only on a bare `/` or on an agent named by name,
and is proven by a **9-case fixture asserted in `selftest`**. `/wp-admin/` is not a
refusal of a TERO page.

### Contamination: cells that are right about the artefact and may be wrong about the world

| flag | cells | entities |
|---|---:|---:|
| `SITE_DOES_NOT_NAME_ENTITY` | 665 | 133 |
| `SOURCE_REFUSES_THIS_AGENT_OR_STATES_RESTRICTIVE_TERMS` | 47 | 11 | *(the `STATES_RESTRICTIVE_TERMS` half of this flag stopped gating on 2026-09-02 - `PUBLICATION_POLICY.md`, `TERMS-OWNER-RULING-2026-09-02`. Keep the flag; it now records the publisher's stated preference rather than a refusal Cedar honours.)* |
| `NAME_IS_ALL_STOPWORDS_identity_not_checkable_from_page_text` | 35 | 7 |

**89 of those cells claim `HARVESTED` or `FOUND_NOT_EXTRACTED`** and are the ones to
re-check first. The flags are carried in the matrix's `contamination_flags` column, each
naming the artefact it came from.

---

## THE HIGHEST-YIELD GAP

### 1. CAGE / UEI / DUNS from the entity's own published pages — 556 entities, one route

**Which entities.** The 1,439 `identifiers` rows at `NEVER_CHECKED`, narrowed to those
that can actually be worked: **556 entities** that (a) have a live 2xx site of a non-dead
url_type, (b) already carry a UEI, CAGE or EIN in
`cedar_identifier_ledger_final.csv`, so a capability statement almost certainly exists,
and (c) carry no contamination flag. **269 of the 556 already have a machine-readable
surface mapped** (`api_endpoint` / `wp_types` / `wp_media_pdf` / `sitemap` /
`machine_readable_surface` rows in `cedar_web_map.csv`), so the route is already known
host by host.

By class: 290 federally recognized tribes · 141 Alaska Native Villages · 35
state-recognized tribes · 29 ANC village corporations · 19 tribal colleges · 13 Native
CDFIs.

**Which route.** The machinery exists and does not need to be written: `shard_m`'s
`deep_probe.jsonl` already runs `/wp-json/wp/v2/media` (unfiltered, paginated) +
`wp/v2/search` + `wp/v2/types` + sitemap against 148 hosts. Point it at
capability-statement vocabulary — *capability statement, capabilities, CAGE, UEI, DUNS,
SAM registration, GSA schedule, 8(a), small business* — over the media index rather than
the TERO vocabulary. `docs/HIDDEN_DATA_TECHNIQUES.md` §3 and §11: a capability statement
is a PDF in `wp-content/uploads`, and its **PDF metadata carries the `as_of_date` the
document never prints**.

**Why it is worth more than the row count.** `docs/ASSERTION_LAYER.md` measured that
**every fact in Cedar rests on exactly one source; 0 of 8,975 single-valued facts have a
second**. Cedar's UEIs and CAGEs all come from the federal side — FPDS, SAM, the award
archive. An entity's own capability statement is a **genuinely independent evidence
family** for the same identifier, which is the highest-value harvest in the project by
the standing item 0 in `START_HERE.md`, and it is the one field where a second source is
both cheap and decisive.

### 2. 634 directory rows already on disk and never promoted — a join, not a fetch

**16 of 36 `TBD-*` files in `data/staging/business_registry/` have zero rows in
`data/clean/native_owned_businesses.csv`.** 634 rows, 15 entities that are not currently
certifying authorities in the clean table at all:

Puyallup (88) · Hoopa (136) · Wampanoag/Aquinnah (101) · Pyramid Lake (73) ·
Sisseton-Wahpeton (45) · Bad River (39) · Little Traverse (35) · Citizen Potawatomi (27) ·
Spokane (23) · Kalispel (12) · Chehalis (10) · Shoshone-Bannock (10) · Chitimacha (7) ·
Delaware Tribe (4) · California Valley Miwok (3).

The registry is honest about this — it labels them `HARVESTED_STAGING_ONLY` — but the
coverage number quoted from `native_owned_businesses.csv` does not see them, and
`individual_business` `HARVESTED` reads 58 entities instead of 73. This is
`ON_DISK_NOT_PROMOTED` in the `docs/AGENT_FIELD_GUIDE.md` §5 sense.

**Two things must not be done blind.**
- **`TBD-C01` is a byte-equal duplicate of `TBD-079`** (Muscogee Creek CESO vendor list,
  337 rows, identical name sets) and `TBD-079` is already promoted. Promoting the glob
  would add 337 phantom rows. It is excluded above.
- **All 16 are `publishable = N`.** Promotion buys internal coverage and the ability to
  say honestly what we hold; it buys **zero** publishable rows until consent and terms
  are settled per source.

### 3. 216 entities where an individual-business surface was located and never extracted

`individual_business` `FOUND_NOT_EXTRACTED` = 216, of which **211 carry no contamination
flag**. Only ~57 of these are a registry `LIST_FOUND_*`; the rest are TERO *programme*
pages, ordinances and application forms rather than rosters — `LIST_FOUND_TERO_FREE_VOCAB`
paired with `harvest_status = NO_LIST_TO_HARVEST` is the shape, and it means the
machinery is published and the register is not. Lower yield than it looks, and worth
saying so rather than counting it.

---

## A TERMS FINDING THAT NEEDED AN OWNER RULING - AND GOT ONE THE SAME DAY

> **RULED 2026-09-02.** `docs/PUBLICATION_POLICY.md`,
> `TERMS-OWNER-RULING-2026-09-02`: *"So tribal websites, I actually don't care
> if they say it does scrape. Because if it's publicly available and you can
> scrape it, scrape it."* Southern Ute's terms language **does not block the
> harvest**. The proposed disposition at the foot of this section - move
> `TBD-D01` to `graveyard/` and never promote it - is therefore **withdrawn as
> to the business rows**, and the finding resolves as:
>
> * **The 21 business rows may be harvested and kept.** The exclusion that
>   `TBD-055` records is now an observation of what southernute-nsn.gov states,
>   not a gate.
> * **`owner_name_raw`, `email`, `phone` and `address_raw` may not be
>   published.** This is the privacy carve-out the ruling states explicitly and
>   it is the *only* live bar on this file. It is not a licensing question and
>   it did not move with the ruling.
> * **The process defect this section found is untouched and is the durable
>   part.** `TBD-D01` had no row in the vendor-list registry, so nothing
>   connected the harvest back to the ruling that governed it. A ruling that
>   lives in one artefact while the harvester reads another will be re-litigated
>   every pass. Write the decision onto the row that asked for it.
>
> The section below is kept verbatim as the record of what was found.



**`data/staging/business_registry/TBD-D01_southern_ute_indian_owned_business_list.jsonl`
holds 21 rows extracted from a source the vendor-list registry had already ruled
restricted.**

`review/tribal_vendor_list_registry_2026-08-26.csv` records Southern Ute as
`harvest_status = EXCLUDED_TERMS_STATED_RESTRICTIVE`, `source_terms_status =
TERMS_STATED_RESTRICTIVE`, quoting southernute-nsn.gov: *"under this license you may not:
modify or copy the materials; use the materials for any commercial purpose, or for any
public display."* The `list_url` in that exclusion is
`.../2026/03/2026-Indian-Own-Business-List.pdf`.

`TBD-D01` was written on **2026-09-01** by `run-2026-09-01-shardd` from
**that exact PDF**, with `ingestion_method = pdf` and a cached snapshot at
`raw/TRBF-STHUTE-00_tero_b05678af.pdf`. It carries named natural persons
(`owner_name_raw`), street addresses, phones and emails. It has **no row in the
vendor-list registry**, so nothing connected it back to the exclusion.

This is the same shape as the 42 2xx rows on 13 hosts that refuse this agent by name: a
later pass re-harvested what an earlier pass had ruled off limits, because the exclusion
lived in one artefact and the harvester read another. Terms restrictions attach to
host+path and to the restricted entity's own publications — this is the restricted
entity's own publication.

**Proposed disposition:** move `TBD-D01_*.jsonl` and
`raw/TRBF-STHUTE-00_tero_b05678af.pdf` to `graveyard/`, record the exclusion against
`TBD-D01` as well as `TBD-055`, and never promote it. Filed as an owner item.
