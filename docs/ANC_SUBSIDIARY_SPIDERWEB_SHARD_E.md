# The ANC subsidiary spiderweb — shard E, 2026-09-01

*Ownership edges asserted by the parent corporation itself, for the 191 ANCSA
entities in `data/spine/cedar_identity_register.csv`: 12 Alaska Native Regional
Corporations, 6 ANCSA Group Corporations, 173 Alaska Native Village
Corporations.*

**Nothing here was written to the spine, to `503`, `510`, `512` or any ledger.
No entity was minted. No attribution was made.** The outputs are staged
candidates with quotes.

---

## Why this shard exists, in the owner's terms

> *"It is impossible to establish a correct corporate hierarchy outside of tribes
> doing it for you."* — the owner, 2026-08-29, `docs/NATIVE_ENTITY_NUANCES.md`

The federal spiderweb terminates one hop short of the truth: SAM's declared
highest-level owner is the highest *incorporated* owner — Ho-Chunk, Inc., not the
Winnebago Tribe — because the government need not hold a CAGE in the chain.

**ANCs solve this from the other direction.** They publish their own subsidiary
lists, and the strongest form of that publication is not a marketing page: it is
the **audited "Principles of Consolidation" note** in the annual report each ANCSA
corporation with 500+ shareholders must file with the Alaska Division of Banking
and Securities under **AS 45.55.139**. That note enumerates the wholly- and
majority-owned subsidiaries **by legal name**, signed off by an auditor. It is
ownership asserted by the parent, about itself, under a statutory filing
obligation — the strongest evidence class available to Cedar for this family, and
better than anything derivable from SAM.

---

## What it produced

| | |
|---|---:|
| entities in the slice | **191** |
| **parent→child ownership edges** | **482** |
| — depth 1 (named by the parent itself) | 404 |
| — depth 2 (named by a subsidiary about ITS children) | 78 |
| distinct asserting parents | 37, under **21 ANC roots** |
| edges carrying a stated ownership % | 13 |
| edges carrying a published CAGE code | 32 |
| from an audited annual report | 355 |
| from a corporate site | 127 (2 of them from JSON-LD only) |
| children with ≥1 candidate match into Cedar | 142 of 482 |
| — **exact CAGE identifier matches** | **27** |
| — published CAGE that Cedar's index does NOT hold | 5 |
| — name-exact / name-normalised proposals | 90 / 36 |
| entities with a live page of their own | 50 of 191 |
| entities with **no site found** (recorded) | 141 |
| shareholder-communication channel records | 302 |
| PDFs indexed through `wp-json` media, in 29 requests | **2,270** |

Edges by ANC root: Bristol Bay 151, Ahtna 64, Calista 40, ASRC 39, Goldbelt 37,
UIC 29, Huna Totem 23, Chugach 17, Tikigaq 16, Sealaska 11, Koniag 8, Doyon 7,
Aleut 7, Tatitlek 7, CIRI 6, Sitnasuak 5, Kuukpik 5, Bering Straits 4, Olgoonik 2,
Tyonek 2, Emmonak 2.

---

## Outputs

| file | what it is |
|---|---|
| `data/staging/anc_subsidiaries/shard_e.jsonl` | **the deliverable** — one parent→child ownership assertion per line, with the sentence that asserts it |
| `data/staging/anc_subsidiaries/shard_e_match_candidates.csv` | candidate matches to Cedar entities / UEIs / CAGE codes, with confidence. **Proposals only** |
| `data/staging/anc_subsidiaries/shard_e_dropped.json` | every name the extractor refused, with the reason |
| `data/staging/tribe_web_map/shard_e.csv` | the web map, absences included |
| `data/staging/tribe_harvest/shard_e/newsletters.jsonl` | shareholder-communication channels and whether they carry deal content |
| `data/staging/tribe_harvest/shard_e/_report_passages.jsonl` | the indexed source passages the edges were adjudicated from |
| `data/staging/tribe_harvest/shard_e/_coverage_*.json` | per-probe-stage coverage: attempted vs total, and an explicit `complete` boolean |

Code: `531` (index local report passages) → `532` (web probe) → `533` (build
edges) → `534` (web map) → `535` (match candidates) → `536` (newsletters).
`533` is spec-driven: `code/533_shard_e_spec.json` (report sources) and
`code/533_shard_e_spec_web.json` (corporate-site sources).

---

## The two guards, enforced in code

**1. Anti-fabrication.** Every `child_name_raw` must appear **verbatim** in the
source document text (diacritic- and punctuation-folded). A name that does not is
dropped to `shard_e_dropped.json` and counted. Nothing is inferred from a shared
name, a shared word or a shared address — name-based inference is exactly the
defect the owner says makes existing hierarchies wrong.

**2. No association edges.** `docs/ANCSA_OWNERSHIP_RULING.md` rules 4 and 5: the
village-corporation ↔ village-government link and the regional ↔ village link are
**shareholding and ancestry, never ownership**. This file contains neither, and
the spec may not add one. For the same reason **`tribe_id` is blank on every row
of `shard_e.csv`** — putting a tribe_id on an ANC row would assert the edge the
ruling forbids.

**3. No natural persons.** ASRC Federal's directory is parsed off its
`General Manager:` line, which is used as a *structural anchor only*. The person's
name is never read into a field.

---

## The single best find: ASRC Federal publishes its own CAGE codes

`https://www.asrcfederal.com/companies/` lists each operating company with its
**CAGE code**. A CAGE is an identifier, not a name, so those rows join to Cedar's
own `fpds_uei_cage_map.csv` / `cedar_cage_backfill.csv` with **no name matching at
all** — the one route in this shard that is not subject to the 46.3% name-recall
ceiling. Those matches carry confidence `exact_identifier`; a published CAGE that
Cedar's index does not hold is recorded as `exact_identifier_unmatched`, which is
itself a finding about coverage.

**27 of the 32 published CAGE codes hit Cedar's own index exactly**, and the
legal names they return are the argument for the whole method — these are
registrants a name matcher would never have connected to ASRC:

| ASRC Federal calls it | CAGE | the legal name on file | UEI |
|---|---|---|---|
| ASRC Federal Broadleaf | 5RWC4 | **BROADLEAF, INC** | DGA4AQ4DJYY9 |
| ASRC Federal DNC | 03EV6 | **DATA NETWORKS, INC** | GNXNRGLSNML9 |
| ASRC Federal InuTeq | 5NTT4 | **INUTEQ, LLC** | NBEWZB8LQ8Z5 |
| ASRC Federal Primus | 3GQG0 | **PRIMUS SOLUTIONS INCORPORATED** | YYZXLJD6NTZ9 |
| ASRC Federal Vistronix | 1CXP0 | **VISTRONIX INC** | XPRKVQ956WB4 |
| ASRC Federal NetCentric | 1R5E0 | **NETCENTRIC TECHNOLOGY, LLC** | T65LCYKJCW58 |
| ASRC Federal Analytical Services | 0Z229 | **ANALYTICAL SERVICES INCORPORATED** | K5Y3MDHD2MB5 |
| ASRC Federal Mission Solutions | 5LG96 | **MISSION SOLUTIONS LLC** | VVQ8NPGU36B7 |
| Agile Decision Sciences | 7VVF6 | AGILE DECISION SCIENCES, LLC | C6EMRJ67V4M3 |
| Space Coast Aerospace Services | 7PSV4 | SPACE COAST AEROSPACE SERVICES LLC | VNWUMZ22BNP6 |

Not one of the bolded rows shares a token with "Arctic Slope", "ASRC" or any
Alaska Native name. They are reachable **only** because the parent published the
CAGE next to its own branding.

The same shape runs through Calista — *Brice*, *Tunista*, *Yulista*, *STG*,
*Troy7*, *DSOFT Technology*, *StraitSys*, *Delta EMI*, *Terra Foundations*,
*Y-Tech Services* — and Bristol Bay, whose 150-company consolidation note is
dominated by *CCI*, *SES*, *SpecPro*, *Vista*, *Eagle*, *STS*, *Glacier*,
*Cannon*, *PetroCard* and *John Burns Construction*.

---

## The recovery ladder, and which rung worked

`docs/PULL_DISCIPLINE.md` governs every request. One poller, 3.0s per-host floor,
robots.txt honoured per host, no retry loops, a 2h run deadline, and a global stop
if the first twelve probes all refuse.

| obstacle | rung that worked |
|---|---|
| `asrc.com` returns **HTTP 307 behind a Sucuri CloudProxy JS challenge** | **Not defeated — and deliberately not.** A JS cookie challenge is a stated access control. Recorded as a refusal, and ASRC's depth-1 subsidiaries were taken instead from its own **audited annual report**, which is a better source anyway. ASRC Federal and ASRC Industrial are reachable on their own domains. |
| `www.beringstraits.com` does not resolve | the apex `beringstraits.com` does — `/subsidiaries/` served the family-of-companies page |
| `www.ahtna.com/our-companies/` 404 | the real page is `/doing-business-with-ahtna/family-of-companies/`, found from the homepage nav |
| `nana.com`, `ciri.com`, `doyon.com`, `sealaska.com` serve their company lists from JS | the **annual report** carried the assertion instead; CIRI's segment note names CDC dba North Wind Group, OSC Global, CLDC and CIRI Energy in prose |
| 173 village corporations, most with no obvious domain | generated one candidate domain per name and **recorded every miss as an absence** |

**A 404 on a guessed path is not a refusal by the host.** The first probe run
tripped its own circuit breaker after three guessed 404s on `ahtna.com` and
skipped the real pages behind them. The breaker now counts only 0/403/429/5xx.
That bug is recorded here because it is the kind that silently converts a live
site into a "no site found" row.

---

## What the page sends but does not show

`docs/HIDDEN_DATA_TECHNIQUES.md` was applied to every page this shard had already
fetched, at a cost of **zero additional requests** (`code/537_shard_e_hidden_data.py`
reads the stored bytes). Per-site results are in
`data/staging/tribe_harvest/shard_e/_hidden_data.jsonl`, and the technique that
fired is carried into the `evidence` column of `shard_e.csv`.

**The find that justifies the checklist: Emmonak Corporation publishes its own
identifiers in `application/ld+json` and shows none of them on the page.**

```
"identifier": [ {"propertyID": "SAM UEI",   "value": "NQE6F46KTGM6"},
                {"propertyID": "CAGE Code", "value": "3MKH9"},
                {"propertyID": "TIN/EIN",   "value": "92-0045979"},
                {"propertyID": "DUNS",      "value": "010200236"},
                {"propertyID": "SAM UEI",   "value": "MUMNCL2GXVW9"},
                {"propertyID": "CAGE Code", "value": "8X0S4"} ],
"subOrganization": [ "Field Calibrations, Inc.", "Qiilituliq, LLC" ]
```

A village corporation handing over its UEI, CAGE, EIN and DUNS **and naming two
subsidiaries** — in structured form, asserted by itself. Nothing in the rendered
page carries any of it, and the rendered page is so thin that the corroboration
check first mistook the site for a parked domain. That bug is fixed: corroboration
now falls back to the served HTML.

Also recorded: 78 of the shard's sites advertise `wp-json`, which makes
`/wp-json/wp/v2/media` the cheap route to their annual-report and newsletter PDFs
— **one request instead of crawling an archive**, which is gentler on a small
corporate server as well as better data.

### A guessed domain that answers is not the right site

`englishbay.com` is a Vancouver photography blog. `nima.com`, `kwik.com`,
`bayview.com`, `farwest.com` are other people's businesses. **A false "website
found" is worse than an honest absence**, so any URL generated from a corporation
name must corroborate — a distinctive token of the name AND an ANCSA / Alaska
Native signal on the page — or it is recorded as `UNRELATED_DOMAIN` with the
reason, and the entity still counts as having no site found.

---

## Coverage is asserted, never assumed

`532` writes `_coverage_<stage>.json` on every exit with `candidates_total`,
`candidates_attempted`, an explicit `complete` boolean, `deadline_truncated`, and
**the URLs it did not attempt, by name**. A deadline-truncated crawl of a
corporate tree must never be readable as the whole tree: half a subsidiary list is
a wrong answer, not a small one.

---

## What is NOT here, and why

- **Depth beyond 2 is mostly unwalked.** ASRC alone reports *"more than 110
  operating companies"* and AIS *"over 35"*; this pass reaches ASRC Federal's own
  card list and three ASRC Industrial acquisitions. BBNC's 150 are flat in the
  filing, so their internal tiers are not modelled.
- **Kuukpik was written off as unparseable and then recovered.** The `pdftotext`
  extract in `data/interim/ancsa_txt_v2/` returns page furniture and drops the
  notes entirely, so this shard first recorded "notes did not survive
  extraction". On the natural-resources workstream's MMS finding — *a source two
  passes had called unusable read clean by pdfplumber coordinate, 315 rows and
  $4.09B recovered* — it was retried with **pdfplumber**, which returns Kuukpik's
  `2. SUBSIDIARIES` note intact: Nanuq, Inc.; Kuukpik Drilling, LLC; Kuukpik
  Transportation, LLC; Kuukpik Kuayaat, LLC; Kuukpik Oil Field Services, LLC.
  **Five edges that a whole-corpus text layer had silently lost.** `533` now has
  a `pdf_path` source route for exactly this. Any other ANC report recorded as
  unreadable deserves the same one retry before it is believed.
- **The Alaska state corporate registry rung was not needed** and was not used.
- **No shareholder-level anything.** The ANCSA §7(h) share-transfer question in
  `ANCSA_OWNERSHIP_RULING.md` does not bear on any edge here, and no measure in
  this shard depends on it.

---

## Interlock with the §7(i)/§7(j) resource work

The natural-resources workstream owns `data/clean/resource_revenue.csv` and the
ANCSA §7(i)/§7(j) extraction, and this shard did not touch it. The interlock is
real and should be worked next: **§7(j) is the receiving side for this slice.**
A regional corporation's filed report states what it redistributed to which
village corporations — parent-asserted, filed and dated, the same evidence class
this shard chased on corporate sites, already structured.

Two checks that produce findings either way:

* a village corporation **named in a §7(j) filing but with no site found here**
  is corroborated as an operating entity, and its absence from the web is then a
  disclosure fact rather than a doubt about the entity;
* a village corporation **live on the web but absent from every §7(j) filing** is
  a discrepancy worth recording, not smoothing over.

`shard_e.csv` carries all 191 with their status, so the join is one merge on
`cedar_uid`.

---

## Handoff

The next pass should walk depth 3 from the holding companies this file already
names — `Bristol Bay Construction Holdings`, `Bristol Bay Government Services
Group`, `Chugach Government Solutions`, `Ahtna Federal Holdings`, `HunaTek
Holding`, `UIC Government Services` — each of which has its own site. And
`shard_e_match_candidates.csv` should go to `503`/`510` as candidates, never as
resolutions: **the 27 CAGE matches are the ones worth adjudicating first**,
because they are the only ones that do not rest on a name.
