# Dataset 9 — Federal Actions Affecting Tribal Nations — Build Log

**Date:** 2026-08-05
**Scripts:** `code/10_pull_federal_register.py`, `code/11_classify_federal_actions.py`
**Logs:** `logs/10_federal_register_2026-08-05.log`, `logs/11_classify_federal_actions_2026-08-05.log`
**Source:** Federal Register API v1, `https://www.federalregister.gov/api/v1/documents.json` (free, no key, GET)
**Harvest runtime:** 1,132 s (18.9 min), 462 shards, 0 failed
**Outputs:**

| Path | Rows | Size |
|---|---:|---:|
| `data/clean/federal_actions_raw.csv` | 156,452 | 235 MB |
| `data/clean/federal_actions.csv` | 156,452 | 240 MB |
| `data/raw/federal_register/*.jsonl.gz` | 451 files | 112 MB |
| `data/raw/federal_register/_shard_manifest.csv` | 462 | — |

**Date range achieved: 1994-01-03 → 2026-08-05.** The API's own coverage floor is
1994, so the plan's caveat 1 (pre-1994 lives in scanned GovInfo volumes) is
confirmed, not worked around.

**Zero fabrication.** Every cell is a value returned in an API response body.
Absent fields are blank, never filled. Raw responses are retained gzipped per
shard so any row traces back to the bytes it came from. Six randomly drawn
classified rows were re-fetched individually from the live API after the build:
**6/6 matched exactly** on title, publication date, and document type.

---

## 1. Nets, and what each one caught

Both nets ran over 1994-01-01 → 2026-08-05, sharded by publication year.

| Net | Query | Records returned (pre-dedup) |
|---|---|---:|
| keyword | `conditions[term]=tribal` | 113,110 |
| keyword | `conditions[term]=Indian` | 82,339 |
| keyword | `conditions[term]=tribe` | 64,346 |
| keyword | `conditions[term]=reservation` | 25,694 |
| keyword | `conditions[term]="Native American"` | 19,504 |
| keyword | `conditions[term]="Native Hawaiian"` | 6,680 |
| keyword | `conditions[term]="Alaska Native"` | 6,245 |
| agency | `conditions[agencies][]=indian-affairs-bureau` | 3,309 |
| keyword | `conditions[term]=ANCSA` | 555 |
| keyword | `conditions[term]="tribal-state compact"` | 469 |
| keyword | `conditions[term]="federal acknowledgment"` | 221 |
| keyword | `conditions[term]="fee-to-trust"` | 194 |
| keyword | `conditions[term]="land into trust"` | 169 |
| keyword | `conditions[term]="liquor ordinance"` | 129 |

After dedup on `document_number`: **156,452 unique documents.**

| `net_caught` | Rows | Meaning |
|---|---:|---|
| `keyword` | 153,143 | matched a term, not a BIA-authored document |
| `both` | 3,297 | BIA document that also matched a term |
| `agency` | 12 | BIA document **no keyword net found** |

The agency net is almost entirely a subset of the keyword net — but not
entirely, and the 12 exceptions justify running both. Two of them are
substantive tribal land actions the keyword net missed outright:

- `2001-02-20` Acquisition of Title to Land in Trust; Delay of Effective Date; Correction
- `2001-06-13` Acquisition of Title to Land in Trust; Delay of Effective Date

Both are now classified `land_into_trust`. A keyword-only build would have
dropped them.

---

## 2. Rows by publication year

| Year | Rows | Year | Rows | Year | Rows |
|---|---:|---|---:|---|---:|
| 1994 | 2,926 | 2005 | 4,829 | 2016 | 5,273 |
| 1995 | 3,209 | 2006 | 4,852 | 2017 | 4,151 |
| 1996 | 3,624 | 2007 | 4,685 | 2018 | 4,588 |
| 1997 | 3,612 | 2008 | 5,266 | 2019 | 4,692 |
| 1998 | 4,025 | 2009 | 4,535 | 2020 | 4,855 |
| 1999 | 4,610 | 2010 | 5,056 | 2021 | 4,848 |
| 2000 | 4,585 | 2011 | 5,317 | 2022 | 5,167 |
| 2001 | 4,951 | 2012 | 5,064 | 2023 | 6,295 |
| 2002 | 5,090 | 2013 | 4,904 | 2024 | 7,068 |
| 2003 | 5,053 | 2014 | 4,870 | 2025 | 5,283 |
| 2004 | 4,840 | 2015 | 4,875 | 2026 | 3,454 (through 08-05) |

No year is missing and no year is anomalously thin. 2026 is a partial year.

---

## 3. Rows by `action_type`

Assigned only from explicit text in the document's own title, abstract, or FR
`type` field. Every classified row carries `action_type_rule`,
`action_type_signal` (the literal substring that fired), and
`action_type_source_field`, so any label is checkable without re-reading the API.

| action_type | Rows | On-face relevant |
|---|---:|---:|
| reservation_proclamation | 121 | 100% |
| land_into_trust | 305 | 82% |
| ancsa_conveyance | 768 | 100% |
| gaming_land_decision | 101 | 96% |
| tribal_state_compact | 687 | 100% |
| liquor_ordinance | 258 | 90% |
| federal_acknowledgment | 187 | 100% |
| recognition_list_update | 35 | 100% |
| consultation | 235 | 100% |
| rulemaking | 63,248 | 4% |
| irrigation_rates | 97 | 95% |
| grant_solicitation | 3,396 | 25% |
| other | 87,014 | 18% |
| **Total** | **156,452** | |

"On-face relevant" is the `title_abstract_term_hit` column: the share of rows in
which a harvest term actually appears in that document's **own title or
abstract**, computed locally from returned text. Overall only **22,169 of
156,452 rows (14.2%)** are on-face; the rest matched on body text alone.

### Read the two tiers differently

- **The ten named tribal buckets (2,794 rows) are high precision** — 82–100%
  on-face, and they are exactly the recurring self-labelling BIA categories the
  plan wanted first: proclamations, ANCSA selections, compacts, liquor
  ordinances, acknowledgment, irrigation rates, recognition-list updates.
- **`rulemaking` (63,248) and `other` (87,014) are the recall tier.** They are
  dominated by documents that merely mention "Indian", "tribal", or
  "reservation" somewhere in the body — an EPA air rule listing tribal lands, an
  FAA notice using "reservation" in its ordinary sense. `rulemaking` is 4%
  on-face. **Do not present 63,248 as a count of tribal rulemakings.** It is the
  count of Rules and Proposed Rules inside the tribal keyword net.
- `grant_solicitation` (25% on-face) has the same caveat: it is every funding
  notice caught by the net, e.g. "Cooperative Agreements To Prevent Lyme
  Disease", not a list of tribal grant programs.

For a defensible high-precision working set, filter
`title_abstract_term_hit == 1`, or filter to the ten named buckets.

---

## 4. What the API would not return

Probed at runtime and recorded in the harvest log — none of this is assumed.

| Attempt | Result |
|---|---|
| `conditions[agencies][]=bureau-of-indian-affairs` | **HTTP 400** `{"errors":{"agencies":"invalid value"}}` — this slug does not exist. The correct slug is `indian-affairs-bureau` (agency id 234, raw name "Bureau of Indian Affairs"). Also checked: no `bureau-of-indian-affairs` entry anywhere in `/api/v1/agencies.json`. |
| `conditions[title]=tribal` | **HTTP 400** `{"errors":{"title":"is not a valid field"}}` — there is **no title-scoped or abstract-scoped search**. `conditions[term]` is full text only. This is the single most consequential API limit here: it is why the corpus is 156k rows instead of ~20k, and why `title_abstract_term_hit` had to be computed client-side. |
| `conditions[bogus]=x` | HTTP 400 — unknown conditions **error rather than being silently ignored**. A 200 therefore proves the filter was really applied. |
| Any query returning ≥ 10,000 | `count` and retrievable results are **capped at 10,000**. A capped query is silently truncated, so every net was sharded by year and would have been re-fetched by month, then day, on reaching 9,500. |
| Pre-1994 documents | Not available. API coverage begins 1994. |

Other API behavior worth recording:

- Multi-word terms must be sent as **quoted phrases**. Unquoted, matching
  loosens badly (`"Native American"` unquoted returned 878 hits for 2010 vs 598
  quoted; `land into trust` unquoted would match any document containing
  "trust"). All multi-word terms in this build were quoted.
- The API **503s on bursts**. At 3 concurrent workers it returned a stream of
  503s; at 2 workers with a 0.6 s pause it returned 7 across the whole run, all
  absorbed by retry. Zero shards were lost to it.

---

## 5. Completeness checks

- **462 of 462 shards succeeded, 0 failed.** 451 wrote records; 11 were
  genuinely empty (a term with no hits in a given year).
- **0 count mismatches.** Every shard returned exactly the number of records its
  own `count` promised. Pagination lost nothing.
- **No shard ever reached the 9,500 cap guard**, so no month/day subdivision was
  needed and no result set was truncated. The largest single shard was
  `tribal` 2024 at 5,541 records, well under the 9,500 guard.
- 156,452 rows, 156,452 distinct `document_number` — **0 duplicates**, 0 blank
  titles, 0 blank publication dates.

### Field population

| Field | Non-blank | Share |
|---|---:|---:|
| `html_url`, `json_url` | 156,452 | 100.0% |
| `agency_names` | 155,514 | 99.4% |
| `pdf_url` | 153,526 | 98.1% |
| `abstract` | 130,181 | 83.2% |
| `action` | 129,301 | 82.6% |
| `dates` | 126,279 | 80.7% |
| `docket_ids` | 104,938 | 67.1% |
| `cfr_references` | 64,412 | 41.2% |
| `effective_on` | 43,811 | 28.0% |
| `regulation_id_numbers` | 40,162 | 25.7% |
| `comment_url` | 1,039 | 0.7% |

`comment_url` is effectively unpopulated — comment routing lives in the `dates`
text and on regulations.gov, not in this field. Do not build a comment-deadline
product on it; parse `dates` instead.

---

## 6. Gaps and cautions

1. **1994 has no usable document type.** 2,838 of 2,926 1994 rows are typed
   `Uncategorized Document`; from 1995 the API types documents normally
   (Notice / Rule / Proposed Rule). Consequence: `rulemaking` shows 39 rows in
   1994 against 1,287 in 1995 — **that is a metadata artifact, not a policy
   shift.** 1994 rules are sitting in `other`. Any time series involving
   `rulemaking` should start at 1995 or backfill 1994 stage from the document
   text.
2. **Pre-1994 is absent entirely** — the plan's acknowledged seam. Acknowledgment
   petition timelines and early ANCSA conveyances are truncated at the left edge.
3. **Full-text-only matching drives corpus size.** 85.8% of rows do not mention
   any harvest term in their own title or abstract. This is recall, not
   relevance; `title_abstract_term_hit` is the filter.
4. **`other` is 55.6% of rows and is not homogeneous.** Identifiable recurring
   clusters inside it, none of which fit the specified bucket list:

   | Cluster (measured by title match, within `other`) | Rows |
   |---|---:|
   | Information-collection / Paperwork Reduction Act notices | 27,981 |
   | NAGPRA inventory-completion / repatriation notices | 5,634 |
   | HEARTH Act tribal leasing-ordinance approvals | 123 |

   Information-collection notices alone are 32% of `other` and 18% of the whole
   corpus — they are procedural OMB paperwork that happens to name a tribal
   program, and they are the single largest source of bulk in this build.

   NAGPRA notices and HEARTH Act leasing approvals are both genuine federal
   actions affecting tribal nations and both are self-labelling in the title.
   They are in `other` only because they are not on the bucket list. **These are
   the two strongest candidates for new buckets** — flagged, not added.
5. **`consultation` is assigned from the title only.** Agencies routinely recite
   in an abstract that tribal consultation was conducted before issuing a rule;
   that sentence is evidence consultation happened, not evidence the document
   *is* a consultation notice. Observed on real 2024 rows: "Tribal General
   Welfare Benefits" (a Rule) and an Alaska subsistence rule were both pulled
   into `consultation` by such a recital before this restriction was applied.
   Consequence: consultation is **undercounted** — consultations announced only
   in a rule's preamble are not captured.
6. **The corpus is not BIA-centric.** EPA (25,724 documents) nearly matches
   Interior (26,838), because environmental rules mention Indian country
   constantly. That is a true property of the keyword net, but it means agency
   composition describes *who mentions tribes*, not *who acts on tribal matters*.
7. **FR ≠ the complete universe** (plan caveat 2, unchanged): land can enter
   trust without a proclamation, and not every federal-tribal interaction
   produces a notice.
8. **No entity linking was attempted.** `tribe_or_native_entity` is present and
   **empty on all 156,452 rows**, by instruction. Resolving notice names to the
   spine needs alias history and reconcile-queue rulings; string-matching tribe
   names out of titles is the "Cherokee Inc." trap AGENTS.md forbids.
9. **`related_action_id` / proceedings assembly is not built** — that is phase 2.
   The raw material is present: `regulation_id_numbers` (25.7%) and `docket_ids`
   (67.1%) are the chain keys.

---

## 7. Schema notes

`federal_actions.csv` = `federal_actions_raw.csv` plus six columns:
`action_type`, `action_type_rule`, `action_type_signal`,
`action_type_source_field`, `tribe_or_native_entity` (empty),
`classified_date`.

Harvest-side columns beyond the requested API fields:

| Column | Meaning |
|---|---|
| `net_caught` | `agency` / `keyword` / `both` — derived from which harvest returned the document |
| `keyword_terms_matched` | which term queries returned it |
| `title_abstract_term_hit` | 1 if a term appears in this document's own title/abstract |
| `title_abstract_terms` | which terms those were |
| `source_url` | the document's `html_url` (its public FR page) |
| `api_endpoint` | the API endpoint the row came from |
| `fetched_date` | 2026-08-05 |

`agencies` is flattened to three parallel columns (`agency_names`,
`agency_raw_names`, `agency_slugs`, `; `-joined, order preserved) rather than
buried as JSON. `cfr_references` is rendered `"{title} CFR {part}"`.

Nothing under `data/spine/`, `data/clean/cedar_*`, or `review/` was read or
modified.

---

## REFRESH 2026-08-26 — incremental, and `11` WAS NOT RUN

**156,452 → 156,772 rows (+320). `publication_date` now reaches 2026-08-26,
which is the newest date the source itself carries (probed HTTP 200 the same
run).** Full write-up, with the before/after measurement from script 301:
**`docs/REFRESH_CADENCE.md` PART 5.** The numbers live there; this note exists
so a reader of this log does not quote 156,452 as current.

Script: `code/342_pull_federal_register_incremental.py`. Window 2026-08-06 ..
2026-08-26, 14 nets, one shard each, `records_retrieved ==
source_reported_total` on all 14, zero documents already held.

**Two warnings this refresh earns, both about the scripts named at the top of
this log.**

1. **`11_classify_federal_actions.py` IS A FULL REBUILD and must not be run to
   refresh this dataset.** `federal_actions.csv` carries `pre_2000_flag` and
   `floor_basis_field`, written IN PLACE by `22_apply_temporal_floor.py`. A
   rebuild reverts both — the 133-vs-168 shape (AGENTS.md concurrency rule 5).
   342 imports 11's own `classify()` and 22's own `year_of()` and appends.
2. **`10_pull_federal_register.py` cannot be used incrementally.** Its shard
   cache is keyed `net__key__d0__d1`, so moving `END_DATE` renames the current
   year's shard and refetches the whole year across all 14 nets.

**The completeness contract.** The next incremental run derives its start date
from `max(publication_date)` in the file, so merging a partial window would
advance that maximum past documents never retrieved and the gap would be
permanent and invisible. 342 merges only when every net returned and every
shard matched its source-reported count; otherwise it records `INCOMPLETE`,
leaves the CSVs untouched, and the cached shards let a later run resume free.

**Downstream tables derived from this corpus are now one refresh behind it** —
`fr_content_classification.csv` (156,452), and the builds owned by `130`, `76`,
`98`, `133`, `136`. Named, not run: see PART 5 §5.4 for why `78` in particular
must wait for a quiet lobbying build.
