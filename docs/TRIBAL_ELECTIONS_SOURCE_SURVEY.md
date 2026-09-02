# Tribal elections and council composition — the source survey

*Generated 2026-09-02 by `code/1106_tribal_election_survey.py survey`. Every number is read out of the staged files at write time.*

**This is a survey, not a dataset.** Owner ruling: *"The election one, I think it's interesting. If the data seems easy, then yeah, make it. But that's not a dataset we'll offer — we can add it later, because it pairs well with the voting election data."* Low priority, internal, and only if it comes easily. Nothing here is registered in the codebook or the collection map; the staged table lives in `data/staging/tribal_governance/`.

## The short answer

**One leader per nation, with an election date, is cheap and is now staged. A council, and turnover over time, is not.**

## Route 1 — the tribal press. MEASURED, and it does not work today

The brief expected this route: election results and council swearing-in are staple tribal-press content, and `992`/`993` had already fetched 1,077 issue documents and read 1,172 WordPress articles. Measured 2026-09-02:

| what is on disk | what it holds |
|---|---|
| `data/staging/deals_from_newsletters/_documents.jsonl` (1,077 rows) | url, host, md5, byte count, char count, candidate COUNT. **No body text.** |
| `deal_candidates*.csv` (650 screened) | only the sentences that matched a DEAL pattern |
| `data/staging/np_harvest/raw/newsletters/` (124 files, 34 MB) | nonprofit newsletter INDEX pages, not issues |

So the text an election extractor would read was never retained. Running it means re-fetching every document, OCR for the PDFs, and then a per-document human read — and the newsletter corpus's own standing policy is that back issues are not downloaded in bulk. That is the definition of the thing the brief said to time-box and stop.

There is a second reason to be slow here. A tribal newspaper's election coverage sits on the same page as its obituaries and its health notices. An election result names a person in a public role and is fine; a bulk text harvest of the pages around it is how the other thing gets in by accident.

## Route 2 — the BIA Tribal Leaders Directory. Cheap, national, and half of it was already on this machine

Indian Affairs publishes the Tribal Leaders Directory as an ArcGIS FeatureServer layer. **Shard K had already pulled the Alaska slice** (227 records, `data/staging/tribe_harvest/shard_k/bia_tld_alaska_leaders.jsonl`) — one HTTP request per record — to read village addresses, and nobody had noticed the layer also carries `dateelected` and `nextelection`. This is the `ON_DISK_NOT_PROMOTED` state in `docs/AGENT_FIELD_GUIDE.md` §5, in its least visible form: not a file nobody found, but a COLUMN nobody read in a file that was already here.

| | |
|---|---:|
| records in the national layer | 602 |
| resolved to the Cedar spine by exact normalised name | 587 (98%) |
| carrying `date_elected` | 487 (81%) |
| carrying `next_election` | 468 (78%) |
| rows flagged with an upstream BIA date defect | 1 |
| HTTP requests the whole national pull cost | 2 |

### What it is, stated precisely

One row per **Leader / Authorized Representative** — the single officer the BIA recognises as able to sign for the nation. `LARtype`: Land Area Representation 321; Alaska Native Village 228; Tribal Statistical Area 34; Federally Recognized Tribal Entity 19.

Titles, which are themselves a governance finding — the office a nation puts at its head is not uniform:

| title | nations |
|---|---:|
| President | 189 |
| Chairman | 175 |
| Chairperson | 55 |
| Chairwoman | 40 |
| Chief | 34 |
| First Chief | 31 |
| Governor | 24 |
| 1st Chief | 7 |
| Principal Chief | 6 |
| Tribal Chief | 4 |
| Tribal President | 2 |
| Vice-President | 2 |

### Term starts, by year

| year elected | leaders |
|---|---:|
| 2018 | 12 |
| 2019 | 8 |
| 2020 | 23 |
| 2021 | 41 |
| 2022 | 51 |
| 2023 | 93 |
| 2024 | 115 |
| 2025 | 74 |
| 2026 | 28 |
| 9/20 | 1 |
| July | 1 |
| June | 1 |

### Next election due, by year

| year | nations |
|---|---:|
| 2028 | 52 |
| 2029 | 15 |
| 2030 | 5 |
| 3/20 | 1 |
| 9/20 | 1 |
| July | 1 |
| June | 1 |
| TBD | 1 |

### Entity classes it reaches

| entity class | rows |
|---|---:|
| Federally recognized tribe | 345 |
| Federally recognized Alaska Native Village | 217 |
| Federal-level constituency entity | 22 |
| Alaska Native Village Corporation | 3 |

## The three things this source CANNOT do, and what each would cost

**1. It is one leader, not a council.** The layer holds the LAR and no other seat. A council-composition dataset needs a second source per nation. The cheapest existing one on this machine is `data/staging/tribe_harvest/shard_k/bbna_tribal_councils.jsonl` — **31 Bristol Bay councils, 235 named officers with roles, already parsed** from one regional association's contact page. That is the shape of the work: it is per-consortium page scraping, roughly 200 sources for national coverage, and each one is a different HTML layout. Alaska is over-represented because shard K went there; the lower 48 has no equivalent aggregator.

**2. It is a snapshot, not a history.** The BIA overwrites this layer in place. `date_elected` gives the CURRENT term's start and nothing before it, so turnover — the thing that actually pairs with the owner's voting-patterns research — is not in it. Two ways to get it, and they are very different prices:

  * **Snapshot it forward.** Re-run `pull` quarterly and diff. Costs two HTTP requests a quarter and produces a real turnover series — starting from zero history, today.
  * **Mine Wayback captures of the layer backwards.** The ArcGIS query endpoint is a URL, so captures may exist. Unverified; the honest expectation is that a JSON API endpoint is captured rarely and unevenly, which would give an irregular panel rather than a series.

**3. It is federal recognition of a signatory, not an election record.** `date_elected` is what the nation reported to its BIA agency. It is not a certified result, there is no vote count, no candidate list and no turnout. For anything resembling an election RESULT the sources are the nations' own election ordinances and their published certifications — of which exactly **two** are on this machine (`2026-Election-Ordinance.pdf`, `Revised-DN-Election-Ordinance.pdf`, both under `data/staging/tribe_harvest/shard_a/raw/_documents/`), because nothing has ever gone looking for them.

## What it would take to make this a dataset

| deliverable | route | honest cost |
|---|---|---|
| current leader + term dates, national | done — `pull` + `resolve` | **2 HTTP requests.** Staged today |
| turnover series | quarterly re-pull + diff | 2 requests/quarter, series starts empty |
| council composition | ~200 consortium and nation pages | weeks; every page a different layout; no national aggregator exists |
| certified election results | nation election ordinances and certifications | per-nation document hunt, then per-document reading. Not machine extractable |

## Recommendation

Keep the staged leader table internal, and **start the quarterly snapshot now** — it is two requests and it is the only way the turnover series ever exists, since every quarter not captured is a quarter permanently lost. Do not attempt council composition or election results until someone asks for them by name: both are per-document human work, which is precisely the boundary the brief drew.

## Rebuild

```
py -3 code/1106_tribal_election_survey.py pull
py -3 code/1106_tribal_election_survey.py resolve
py -3 code/1106_tribal_election_survey.py survey
py -3 code/1106_tribal_election_survey.py verify --selftest
```

