# Codebook — CMS NPPES, the second independent source

*Two tables, 35,202 rows. Acquired 2026-09-02 by
`code/1121_acquire_nppes_corroboration.py` from
`npiregistry.cms.hhs.gov/api/?version=2.1`. No key. 680 requests, one per
spine entity plus paging.*

**`robots.txt` on this host serves the registry's Angular single-page-app HTML,
not a robots file.** A soft-404 page is not a robots file, so it reads as NOT
SERVED and therefore ALLOWED — the union check over nine agent tokens agrees.
Reading that HTML as `disallow_all` is the error that lost 22 open hosts in
one shard.

## Why Cedar holds it

`docs/ASSERTION_LAYER.md` and `START_HERE.md` item 0: across **8,975
single-valued facts, 0 have a second source, 0 disagree, and 2 have more than
one independent evidence family.** The arbitration machinery works and has
nothing to arbitrate.

NPPES is a **third evidence family**. The Federal Register roster is
Interior's list of sovereigns; the IRS BMF is Treasury's list of exempt
organisations (and `KNOWN_ISSUES` A3 records that 258 Native Hawaiian entities
return no IRS organisation at all); NPPES is HHS's list of enumerated health
care providers, populated by a separate application under a separate
authority.

> ## ⚠ THE QUERY PASSES THE NAME AND NOTHING ELSE
> The NPPES API accepts `state=` and `city=`. **Neither was sent, on purpose,
> and it cost match rate.**
>
> A search seeded with Cedar's own `state` can only return records that agree
> with Cedar's `state`. The "corroboration" would be Cedar reading its own
> value back out of a remote host — the evidence-lineage trap
> `ASSERTION_LAYER` names, wearing a query parameter instead of a table.
>
> Because the query is name-only, **`state_agrees = DISAGREE` is a reachable
> value**, and `1121 verify` **exits 1 if the file contains none**. A
> corroboration source that can only ever agree is measuring itself.

> ## ⚠ NOTHING HERE IS ATTRIBUTED
> **Every row of the candidate table is `confidence_tier = C`**, and `verify`
> fails if one is not. `START_HERE.md` standing rule 1: a tier is inherited
> from the source row, never assigned by the consumer, and the exactness of a
> key says nothing about the correctness of a link.
>
> `code/1118_corroboration_layer.py` is the consumer. This script hands it
> evidence and adjudicates nothing.

---

# `nppes_org_registrations.csv` — 16,981 rows

**One row per NPI-2 (organisation) record retrieved**, deduplicated on `npi`
across every query — one NPI can answer several spine names and is written
once.

**A registration is not an entity.** An organisation with three enumerated
subparts holds three NPIs, and `organizational_subpart = YES` is how CMS says
so. Do not count NPIs as organisations.

| Variable | Type | Description |
|---|---|---|
| `npi` | text | Primary key. 16,981 distinct = row count, asserted by `verify`. |
| `legal_name` | text | `basic.organization_name` — the name as filed with CMS. |
| `other_names` | text | Pipe-joined `other_names[].organization_name`, mostly `Doing Business As`. **A genuine alias source Cedar has not had for health organisations.** |
| `status` | text | `A` = active. |
| `organizational_subpart` | text | `YES`/`NO`. See above. |
| `enumeration_date` · `certification_date` · `last_updated` | date | **Dated public facts**, from a source with no relationship to Interior. Relevant to the 545-entity stale tail. |
| `mailing_address_1` · `mailing_city` · `mailing_state` · `mailing_postal_code` | text | The `MAILING`-purpose address. |
| `location_address_1` · `location_city` · `location_state` · `location_postal_code` | text | The `LOCATION`-purpose (practice) address. **This is the one the comparison uses**, falling back to mailing where absent. Mailing and location genuinely differ — a billing office is not a clinic — and conflating them would manufacture disagreements. |
| `location_telephone` | text | The **organisation's** line. Published. |
| `primary_taxonomy_code` · `primary_taxonomy_desc` | text | The provider taxonomy flagged `primary`, or the first if none is. ⚠ **NPPES serves `desc: null` on some taxonomy entries** — a key that exists with a null value, which is not the same as an absent key; the build coerces it to blank. |
| `all_taxonomy_desc` | text | Pipe-joined, all taxonomies. **No taxonomy code means "tribal"** — there is no Native flag anywhere in NPPES, which is why this pull has no type-filter leg. |
| `inclusion_basis` · `inclusion_basis_detail` | text | ADR-013 C12 `term_match`. The NPPES record carries no Native flag; the row is here because a **name** query seeded from a spine entity returned it. That is evidence about a name, not about identity. |
| `inclusion_basis_terms_matched` | text | **The queries that returned this NPI**, semicolon-joined (up to 20). C12 requires the matched terms, not just the fact of matching. |
| `retrieved_by_n_spine_queries` | integer | How many distinct spine names returned this NPI. **>1 is a warning**: a record that answers several nations' names is a name collision, not a shared identity. |
| `source_url` · `retrieved_at` · `source_id` · `population_basis` | text | Provenance. `source_id = cms_nppes`; `population_basis = KNOWN_IDENTIFIER`. |

**NOT WRITTEN AT ALL:** the `authorized_official_*` block — a named natural
person, their credential, job title and **direct telephone number**. Cedar
needs the organisation, not the person, and `verify` asserts no column
containing `authorized_official` reaches the file.

---

# `nppes_spine_name_candidates.csv` — 18,221 rows

**One row per (cedar_uid, npi) candidate pair — 17,072 — plus one row per
spine entity that was queried and matched nothing — 1,149.**

Negatives are rows. *Attempted and found nothing* must be distinguishable from
*never attempted*; this is the same grain rule `entity_dated_public_facts.csv`
follows. `verify` asserts **all 1,555 spine entities appear**.

| Variable | Description |
|---|---|
| `cedar_uid` · `spine_canonical_name` · `spine_entity_class` · `spine_state` · `spine_city` | The spine side, as it stood at build time. |
| `nppes_query` | The exact query string sent — the normalised canonical name, truncated to 60 characters on a word boundary, plus `*`. Reproducible. |
| `match_method` | `NAME_TOKEN_MATCH` (17,072) or `NOT_MATCHED` (1,149). |
| `npi` · `nppes_legal_name` | The NPPES side. Blank on `NOT_MATCHED` rows, which is why `match_method` is part of the primary key. |
| `name_token_jaccard` | Token-set Jaccard of the spine name against the NPPES legal name, after a **deliberately short** stoplist. **This is the column that separates signal from noise — see the bands below.** |
| `nppes_state` · `spine_state` · `state_agrees` | `AGREE` · `DISAGREE` · `NO_SPINE_VALUE` · `NO_NPPES_VALUE`. Exactly four values; `verify` asserts no fifth. |
| `nppes_city` · `spine_city` · `city_agrees` | Same vocabulary. **`NO_SPINE_VALUE` on 16,883 of 17,072** — the spine carries a city on only 229 of 1,555 entities. That is Cedar having nothing to compare, **never** the two agreeing. Where Cedar did have one: **118 AGREE, 71 DISAGREE.** |
| `nppes_enumeration_date` · `nppes_last_updated` · `nppes_primary_taxonomy_desc` | Carried through for the arbiter. |
| `hits_for_this_query` · `query_truncated` | How many NPIs the query returned, and whether it hit the 5-page (1,000-record) ceiling. **A truncated query is a partial answer and says so** rather than looking complete. |
| `confidence_tier` | **`C` on every row.** |
| `attribution_method` | `nppes_name_query_candidate` or `nppes_name_query_no_hit`. |
| `inclusion_basis` · `inclusion_basis_terms_matched` | `term_match`, and the query string. |

## ⚠ READ THE JACCARD BAND BEFORE YOU READ THE AGREEMENT RATE

Measured on the full file:

| band | pairs | spine entities | AGREE | DISAGREE | agreement |
|---|---:|---:|---:|---:|---:|
| all pairs | 17,072 | 406 | 3,994 | 13,057 | **23.4%** |
| jaccard ≥ 0.5 | 3,284 | 282 | 1,455 | 1,808 | 44.6% |
| **jaccard ≥ 0.8** | **644** | **76** | **603** | **20** | **96.8%** |
| jaccard = 1.0 | 635 | 75 | 594 | 20 | 96.7% |

**The 23.4% headline is not a quality figure and must never be quoted as
one.** A trailing-wildcard query on `CHEROKEE NATION*` returns 33
organisations, most of which are somebody else; the raw pool is *supposed* to
be wide, because the arbiter needs to see what was rejected as well as what
was kept. **At a real name match the source agrees with Cedar 96.8% of the
time.**

## ⚠ AND THE 20 THAT DISAGREE AT AN EXACT NAME MATCH ARE THE MOST VALUABLE ROWS IN THE FILE

They are almost all **place-name collisions on single-word Alaska village
names**, and the state comparison is what catches them:

| spine entity | spine state | NPPES legal name | NPPES state |
|---|---|---|---|
| Circle | AK | `CIRCLE INC` | NC |
| Pilot Point | AK | `PILOT POINT LLC` | TX |
| Platinum | AK | `PLATINUM INC.` | CA |
| Solomon | AK | `SOLOMON LLC` | MN |
| Hoh | WA | `HOH, LLC` | OR |
| Pine Ridge School | SD | `PINE RIDGE SCHOOL, INC.` | VT |

**A pure name matcher would have booked every one of these as a match.** The
state column turns them into refutations. This is the standing lesson in a new
place: *"a place suffix makes a tribe name a place"*, and
`START_HERE.md` standing rule 1 — the exactness of the key says nothing about
the correctness of the link.

**For `code/1118_corroboration_layer.py`:** `state_agrees = DISAGREE` at high
`name_token_jaccard` should be read as a **REFUTATION signal**, not as a
missing corroboration. It is the only column in Cedar that can currently tell
a name match from a name collision without a human.

---

## What this closes, honestly

* It is the **input** that lets the corroborated-fact count move off zero. The
  move itself is 1118's, and this script deliberately does not make it.
* At jaccard ≥ 0.8, **76 spine entities** have a second, independent
  observation of their state — mostly tribal health boards, clinics and
  Urban Indian Organizations, which is exactly the population an HHS
  enumeration can see.
* **1,149 of 1,555 spine entities matched nothing, and that is correct.** An
  Alaska Native village corporation, an ANCSA group corporation or a BIE
  school has no reason to hold an NPI. The negatives are recorded so nobody
  re-runs the query expecting a different answer.

## Reproducing

```
py -3 code/1121_acquire_nppes_corroboration.py probe
py -3 code/1121_acquire_nppes_corroboration.py pull      # ~35 min, resumable
py -3 code/1121_acquire_nppes_corroboration.py build     # zero network
py -3 code/1121_acquire_nppes_corroboration.py verify    # exits 1 on breach
py -3 code/1121_acquire_nppes_corroboration.py selftest  # proves verify FIRES
```

`pull` checkpoints `_state.json` every 25 entities and resumes from it. It
had to: the first run died at 875 of 1,555 on a `UnicodeEncodeError` printing
a spine name containing `ū` on a cp1252 console. Nothing was lost, and every
user-facing string now goes through an encode-safe writer — **a progress line
must not be able to end a network job.**
