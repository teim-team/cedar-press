# Annual-Report Organisation Discovery

*Mining ANC and NHO annual reports for Native organisations. Run 2026-08-06.*

Output: `review/agent_native_org_candidates_annualreports_2026-08-06.csv` — 107 candidates.

---

## Why this run exists

Elijah: *"ANCs annual reports prob list this and a lot of NHOs have annual reports
on their websites and give to native causes too as another source."*

The ANC corpus was **already on disk**. A prior pass downloaded 246 annual reports
from the Alaska DBS ANCSA portal and extracted their text layers for DEAL
extraction, then never read them for organisations. This run does that, and adds a
first pass over NHO websites.

**Nothing in Task 1 required the network.** The whole ANC half is local.

---

## Corpus

`data/interim/ancsa_txt/` (166 files, 22.6 MB) + `data/interim/ancsa_txt_v2/`
(80 files, 6.8 MB) = **246 files, 19 corporations, FY2016–FY2026**.

| Files | Corporation | | Files | Corporation |
|---|---|---|---|---|
| 25 | NANA Regional | | 11 | Arctic Slope Regional |
| 18 | Doyon, Limited | | 11 | Bristol Bay Native |
| 18 | Sitnasuak Native | | 11 | Calista |
| 17 | Bering Straits Native | | 11 | Goldbelt |
| 17 | Ukpeagvik Iñupiat | | 11 | Olgoonik |
| 15 | Sealaska | | 10 | Ahtna |
| 15 | Huna Totem | | 10 | Aleut |
| 13 | Cook Inlet Region | | 6 | Tikigaq |
| 13 | Koniag | | 2 | Kuukpik |
| 12 | Chugach Alaska | | | |

---

## Method

**1. Keyword windows.** Scan every file for `foundation | scholarship | donat |
charitab | sponsor | philanthrop | contribut | giving | nonprofit | 501(c)(3) |
shareholder benefit | in-kind`, take ±350 characters, and pull capitalised name
phrases ending in an organisational suffix (Foundation, Institute, Fund,
Association, Council, Center, Society, Museum, Authority, Consortium…).
**1,285 distinct name strings.** That is a lead list, not a finding list.

**2. Find the structured rosters.** Search for list headers —
`supported the following organizations`, `donations and contributions`,
`community donations`, `grant recipients`. **75 blocks across 45 files.** These are
what actually matter: published, alphabetised, year-stamped recipient lists.

**3. Quote extraction is mechanical.** `scratchpad/mkq.py` locates each needle in
the source text and returns the surrounding characters plus the enclosing
`<<<PAGE n>>>` marker. **If the needle is not found the row is dropped and
reported.** On the first build 44 of 84 rows failed this check because the PDF
text layer wraps sentences mid-line and my needles were whitespace-normalised.
Not one hand-typed quote reached the CSV. The same guard runs against the fetched
HTML for the NHO half.

That guard also produced a substantive correction. **Alaska Native Tourism
Network** was staged as a candidate Native nonprofit; forcing the quote out of the
source showed it is Huna Totem Corporation's own tourism initiative — *"our
initiative to develop ports, transportation, lodging, and tour products"*. It is
now a `NOT_NATIVE` row explaining the trap rather than a fabricated organisation.

**4. Dedup before proposing.** Every candidate normalised through `norm()`
imported from `code/33_apply_party_rulings.py` (never re-implemented, per standing
rule 8) and matched against `data/spine/cedar_entity_spine.csv` (953 rows),
`data/clean/np_orgs.csv` (12,764) and `data/clean/nho_register.csv` (218).

The substring fallback in that matcher **over-fired exactly as the project's own
traps predict** and is reported here rather than quietly dropped:

- `Institute of the North` and `First Alaskans Institute` → `TRBF-UNTHOR-00` (**Ute**, inside the word "Instit**ute**")
- `Cook Inlet Tribal Council` and `Regional Elders Council` → `AKNF-COUNCL-00` (the Alaska village of **Council**)
- `Tanana Chiefs Conference` → `ANRC-NANARC-00` (NANA)

All refused. Only exact normalised matches were treated as hits.

---

## Which reports were productive

**Bering Straits Native Corporation is the richest source in the corpus, by a
wide margin.** It publishes two alphabetised recipient rosters every year — one
corporate, one employee-giving — in FY2016, 2017, 2018, 2019, 2023, 2024, 2025
and 2026. Nothing else in the corpus is this systematic. It is also the only
corporation whose lists name **other corporations' foundations** (Gana-A'Yoo
Foundation, Sealaska Heritage, The CIRI Foundation, Calista Education and
Culture), which is how several cross-region links were found.

| Corporation | What it yields |
|---|---|
| **Bering Straits Native** | 8 years of full named recipient rosters. The single best source. |
| **Cook Inlet Region** | A standing "family of nonprofit organizations" page with a description and URL for each — the highest evidentiary quality per line in the corpus. |
| **Koniag** | A `DONATIONS AND CONTRIBUTIONS` note naming donees *and dollar amounts* inside the audited MD&A. |
| **Chugach Alaska** | Names and dates its own nonprofits, including two established c.2023. |
| **Huna Totem** | The clearest for-profit/nonprofit split in the corpus (Alaska Native Voices vs the Educational Institute). |
| **Bristol Bay Native** | Documents its foundation's 2023 rename in both the before and after reports. |
| **Calista** | A full four-name merger lineage for CECI, dated. |
| **Sealaska** | Named nonprofits as line items in the audited shareholder-benefit table — stronger than any giving list. |
| **Doyon** | Aggregate community-donation dollars every year, but names only a handful of recipients. |
| **NANA** | Aqqaluk Trust dollar flows in detail; recipient names mostly in the shareholder newsletter, not the report. |
| **Olgoonik, UIC, Goldbelt, Ahtna, Aleut** | Small named-donee lists, several unique finds each. |
| **ASRC, Sitnasuak, Tikigaq, Kuukpik** | Nothing usable. Financial statements and proxy materials, no giving disclosure. |

**Class finding.** Every regional ANC and most village corporations fund an
affiliated foundation, and the reports are consistent about the relationship:
Huna Totem's word is *"non-profit affiliate"*, UIC's is *"another UIC **related**
company"*, Koniag books its foundation as an external **donee** with a dollar
amount. That is the accounting proof of separate legal personality, and it
matches Elijah's standing rule — `parent_native_entity` stays **EMPTY**, the
relationship goes in `serves_native_entities`.

Ahtna's report goes further and prints the disclaimer itself: **"*AITRC is not
owned by Ahtna"**. A primary source ruling out the ownership inference is worth
more than any heuristic.

---

## Unusable, and why

**`2025_Bering_Straits_Annual_Report` and `2026_..._Annual_Report` — broken text
layer, recovered by re-OCR.** The FY2025 PDF's embedded font uses a subsetted
encoding offset by a uniform **+29 codepoints**; the extracted text reads
`$ODVND1DWLYH+HULWDJH&HQWHU`, where `\x03` is the space. Decoding is
deterministic (`chr(ord(c)+29)` recovers `AlaskaNativeHeritageCenter`) — but word
boundaries are destroyed, and a decoded string is a reconstruction, not a
transcription. **Re-OCR was used instead**: pages rendered at 300 dpi with PyMuPDF
and read with `tesseract --psm 4` (`C:\Users\esm247\AppData\Local\Programs\Tesseract-OCR\tesseract.exe`,
not on PATH). That recovered the FY2025 roster cleanly, including
*Native Village of Koyuk*, *Native Village of Teller* and *Village of Solomon*.
The FY2026 file's text layer is intact and needed no OCR.

**`2022_2021_Calista_Annual_Report` — bad OCR, confirmed and avoided.** The
known defects are present (`Acquishions`, `!Z42,69:[l` both verified in the file).
No candidate in this queue is sourced from it.

**`2019 Tikigaq Proxy Materials`, settlement-trust financial statements, NANA
meeting notices** — under 600 bytes of text each, no content. Not defects; those
documents simply carry no organisational information.

---

## The Task 2 pass: NHO websites

Single sequential pass, declared User-Agent with a contact address, one fetch per
URL, cached to disk, 1.5 s spacing. **No poller was started and no host lock was
taken** — nothing here needed one. `api.usaspending.gov` was not touched.

**10 NHO domains attempted, 9 reachable.** All nine returned HTTP 200, seven of
them in under half a second; `manaonui.com` took 3–9 s. The only failure was
`www.makuagroup.com` (`URLError`, 0.09 s — instant, so an edge-level refusal
rather than a slow server, per `PULL_DISCIPLINE.md` rule 4). It was not retried
and no poller was left behind; Wayback CDX enumeration is the documented next
move for that one host. The general reachability concern in the brief did not
materialise.

**`nakupunafoundation.org` is the NHO equivalent of the BSNC roster** and the most
valuable single page found in this run. It publishes a *2025 Annual Giveback
Report*, an *Our Reports* index, `$21,263,247 in community giving from 2015–2025`
broken out by category, and an *Our Partners* page giving a **paragraph of
description plus a "supporting since" year for every grantee**. Description plus
date is materially better evidence than a name on a list.

**Domain-split hazard worth recording:** the NHO is at `nakupunafoundation.org`
while the for-profit family is at `nakupuna.com`, and `nho_register.csv` points at
the `.com`. Same failure class the register already flags for `nhldef.org`.

Also productive: `naoiwikane.org` (a dated 2001–2020 funding timeline naming every
grantee) and `manaonui.com/grants/` (a described grant-recipient list).
`kekumuulu.org` and `hoopalefoundation.org` describe themselves well but **name no
grantees** — recorded as negative results so they are not re-swept.

**Incidental finding for the deals ledger, not this queue.**
`alakainafoundation.com` now states that the Alaka'ina Foundation's nine for-profit
firms *"were wholly acquired in June 2026 by BSNC"* and *"operate today as
Bering-Alaka'ina Holdings"*. That names acquirer, month and resulting holding
company for a transaction already carried in the 2026 ledger, and it is an
ownership-change record: nine UEIs move from NHO to ANC ownership on one date.
Routed to whoever owns the ledger.

---

## Results

| Ruling | Rows |
|---|---|
| `NATIVE_ORG` | 76 |
| `NOT_NATIVE` | 19 |
| `UNCERTAIN` (held) | 7 |
| `ALREADY_IN_SPINE` | 5 |
| **Total** | **107** |

Of the 76 `NATIVE_ORG` rows, **63 are Alaska Native** (from the local ANC corpus)
and **13 are Native Hawaiian** (from NHO websites). Three of the 76 are flagged in
their notes as a **programme or facility rather than a legal person** — Nuuciq
Spirit Camp, Ahtna Cultural Center, Ke Kama Pono Safehouse — so that no later pass
mints an entity for them.

`NATIVE_ORG` notes always state **which** — Native-CONTROLLED, Native-SERVING, or
both. Ownership and service are never collapsed. Where the source establishes
service but not control (Arctic Slope Community Foundation, Mt. Edgecumbe Alumni
Association, Partners in Development Foundation) the note says so and asks for a
second source.

### Coverage gaps this run exposed

- **Kawerak, Inc.** — `KAWRAK` is already baked into Cedar spine IDs as the
  consortium suffix on every Bering Straits village row
  (`AKNF-UNLKLT-00-BERSTR-KAWRAK`), yet Kawerak has no row of its own.
- **Native Hawaiian Organizations Association** — `nho_register.csv` cites the
  NHOA member directory as its primary evidence series, yet NHOA has no entity row.
  The same shape of gap.
- **Southcentral Foundation** — absent from both the spine and `np_orgs.csv`,
  despite being one of the largest Alaska Native health organisations in the country.
- **Tanana Chiefs Conference, Kodiak Area Native Association, Southeast Alaska
  Regional Health Consortium, Norton Sound Health Corporation** — peer consortia
  are already in the spine as `SGVF-` rows (Maniilaq, Copper River, Bristol Bay
  Native Association), so these are like-for-like gaps, not a new class.
- **No ANC-affiliated foundation is in `np_orgs.csv`** except The Aleut Foundation.
  Doyon Foundation, Sealaska Heritage Institute, The CIRI Foundation, Koniag
  Education Foundation and the rest are all absent — because `np_orgs` is a
  *name-match* funnel and none of those names carries a Native token a matcher
  would fire on. That is a structural blind spot in the nonprofit layer, and this
  corpus is the fix for it.

### One defect found in existing data

`np_orgs.csv` keys **Cook Inlet Tribal Council** (EIN 92-0094184) to
**`ANVC-COUNCI-00`** — the ANCSA village corporation for the village of *Council*
in the Bering Straits region. Cook Inlet Tribal Council is an Anchorage-region
nonprofit with no relation to it. The bare token "Council" did this. Flagged in
the CSV as `ALREADY_IN_SPINE` with the correction; **not** fixed here, because
`data/clean/` is out of scope for this run.

---

## Traps honoured

- **A place name is not evidence** (the 282 withdrawn rows). Barrow Whaling
  Captains Association, Diomede Dance Group and Utqiaġvik Presbyterian Church all
  name a place that matches a spine row; each note says so explicitly and refuses
  the merge.
- **`funnel_stage = verified_strict` is a NAME match, not a Native-status
  verification.** The Aleut Foundation and Ahtna Intertribal Resource Commission
  both sit at `verified_strict` and `UNRULED`; this corpus supplies what the name
  match never did.
- **Hawaiian orthography.** Every Hawaiian name in the output carries a fold
  warning covering **both** ʻokina and kahakō. `Mālama Loko Ea` and
  `Nā Aikane O Puʻukoholā Heiau` are the exposed cases.
- **Alaska orthography is the same problem.** `Iñupiaq Language Commission` splits
  into `i upiaq` without the fold — the identical failure documented for
  `Ukpeaġvik`.
- **Refuse-alone name traps** (creek, cherokee, colorado, ojibwe, shawnee, oneida,
  apache, central, eagle, river, mountain, santa): none appeared as a sole basis
  for any candidate here.
- **Concurrent classes untouched.** No `TCU-`, `CDFI-`, `BIE-` or `UIO-` rows
  proposed. Ilisaġvik College (a TCU, named in Olgoonik's reports) and Spruce Root
  (a Native CDFI, a line item in Sealaska's audited table) were **found but routed**
  to the agents who own those classes rather than duplicated. Spruce Root is in the
  CSV carrying that routing note; Ilisaġvik is not proposed at all.

---

## Not done, and what it would take

- **Only the FY2025 BSNC report was re-OCR'd.** A full-corpus OCR pass would find
  giving lists in reports whose text layers are partly degraded. Roughly a
  page-render plus tesseract call per page; the tooling used here is reusable.
- **11 of 19 corporations still have unmined report sections.** This run followed
  giving/scholarship/foundation keywords; board-biography and community-programme
  sections carry more organisation names and were not systematically read.
- **Only 9 of 33 NHO websites were read.** The register holds 33 contracting
  NHOs; the nine reachable ones produced 23 candidates, so the remaining 24 are
  the highest-yield unfinished work in this queue. `www.makuagroup.com` needs a
  Wayback CDX pass.

## Regression check

`py -3 code/62_no_regression_check.py` **FAILS at the time of writing, on two
metrics that are not this run's** — `codebook_undocumented_public = 5` (must be 0)
and `tier_A` fallen 2,149 → 2,148. This run wrote exactly two files, both outside
everything the guard measures: this log and
`review/agent_native_org_candidates_annualreports_2026-08-06.csv`. `data/spine/`,
`data/clean/cedar_*` and `review/cedar_*.html` were not touched. File timestamps
place the cause elsewhere: `data/clean/codebook_master.csv` was rewritten at 16:57
and `cedar_identifier_ledger_final.csv` at 16:24, both by concurrent agents, while
this run's first write was 16:59. Reported rather than fixed — repairing another
agent's in-flight artefact mid-run is how the silent revert documented in script 62
happened in the first place.
- **No EIN resolution.** Every new candidate carries `review_id = NAME:<name>`.
  ProPublica Nonprofit Explorer would attach EINs, but
  `projects.propublica.org` **already holds a host lock**
  (`logs/_HOSTLOCK_projects.propublica.org.json`) — under rule 9, one poller per
  host, so that work belongs appended to the existing lock's queue, not started here.
