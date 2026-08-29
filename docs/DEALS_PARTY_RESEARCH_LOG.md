# Deals Party Research Log — Dataset 1 (Indian Country Deals)

*Agent run 2026-08-05. Output: `review/rulings_inbox_2026-08-05_agent_deals.csv` (549 rulings).*
*Zero fabrication: every row in the output carries a URL that was actually retrieved on 2026-08-05
and a quoted sentence from it. No row was written without evidence.*

---

## What was in front of me

| | Count |
|---|---:|
| Deal rows across the seven ledgers | 875 |
| Distinct `Native_Party` strings | 607 |
| Already settled by Elijah (`data/clean/deals_party_attribution.csv`) — untouched | 33 |
| Unruled at start | 574 parties / 801 deal rows |
| **Ruled this run** | **549 parties / 776 deal rows** |
| Left UNRESOLVED | 25 parties / 25 deal rows |

Ledgers read: `data/clean/deals_{2000_2019,2026_ytd,anc_reports,ancsa_portal,federal_awards,historical,sec_2010_2017}_additions.csv`
plus the two root files `deals_historical_2020_2025.csv` and `deals_2026_ytd.csv` (the review queue counts
those two, so omitting them would have undercounted every party).

## Result by category

| Ruling class | Parties | Deal rows |
|---|---:|---:|
| `ENTITY_OWNED` — a named Native entity | 501 | 723 |
| `NATIVE_ORGANIZATION` — Native, no single owner | 35 | 40 |
| `NOT_NATIVE` | 4 | 4 |
| `MULTI-ENTITY` — enumerate before attributing | 9 | 9 |
| `UNRESOLVED` | 25 | 25 |

Identifiers recovered: **242 UEIs, 90 CAGE codes**, all by *exact* legal-name match (no fuzzy matching)
against `data/clean/funding_identifier_harvest.csv` (USAspending recipient records) and
`data/clean/fpds_uei_cage_map.csv` (FPDS legal business names).

---

## Method

### 1. The Federal Register recognized-tribes notice as a quotable census
The single highest-leverage retrieval of the run. The current BIA list —
**91 FR 4102, 2026-01-30, FR Doc. 2026-01899, 575 Tribal entities** —
<https://www.federalregister.gov/documents/2026/01/30/2026-01899/indian-entities-recognized-by-and-eligible-to-receive-services-from-the-united-states-bureau-of>
was pulled as plain text via `federalregister.gov/documents/full_text/text/2026/01/30/2026-01899.txt`
and used as an *index*, not a search: each party string was normalised (diacritics stripped,
punctuation collapsed) and looked up inside the notice.

- **241 parties matched the notice verbatim.** Each ruling quotes the exact BIA entry.
- **91 more were resolved as documented name variants** (`Taos Pueblo` → `Pueblo of Taos, New Mexico`;
  `Fallon Paiute Shoshone Tribe` → `Paiute-Shoshone Tribe of the Fallon Reservation and Colony, Nevada`).
  Every variant target was itself verified to appear in the notice before the ruling was written.

The notice's parentheticals turned out to be evidence in their own right — the "previously listed as"
forms date renames directly: `Mi'kmaq Nation (previously listed as Aroostook Band of Micmacs)`,
`Louden Tribe (previously listed as Galena Village (aka Louden Village))`,
`Pulikla Tribe of Yurok People (previously listed as Resighini Rancheria)`,
`Yuhaaviatam of San Manuel Nation (previously listed as San Manuel Band of Mission Indians)`.

**A parse caution worth keeping.** The FR text is hard-wrapped at ~70 columns and entries wrap without
indentation, so a naive line-based parse produced 561 or 613 entries against a stated 575. I stopped
parsing into entries and matched against the whitespace-collapsed *whole section* instead, then
audited every match that was not the prefix of a cleanly parsed entry (34 of them). That audit is
what caught the Mattaponi trap below.

### 2. The About-page method for everything else
For each non-tribe party: read the deal row's own `Source_1`, then go to the firm's own
About / Our Corporation / Ownership page and look for the plain-language ownership sentence.
This produced the strongest evidence in the run, e.g.

- `North Wind Group` → *"The company is a wholly owned subsidiary of Cook Inlet Region, Inc. (CIRI)"*
- `Kituwah, LLC` → *"Kituwah LLC is wholly owned by the Eastern Band of Cherokee Indians."*
- `Osni Ponca, LLC` → *"wholly owned by the Ponca Tribe of Nebraska"*
- `Choggiung Limited` → *"a village corporation formed under the Alaska Native Claims Settlement Act (ANCSA)"*
- `Saddleback Communications` → *"created by the Salt River Pima-Maricopa Indian Community (SRPMIC)"*

### 3. The deal row's own source article, read for ownership
Several parties were settled from the document the deal was already sourced to:

- **Mohegan Tribal Gaming Authority** (13 rows) — the row's own SEC Form S-4, financial-statement
  Note 1: *"The Mohegan Tribal Gaming Authority ... is an instrumentality of the Mohegan Tribe of
  Indians of Connecticut."*
- **Arctic Slope Regional Corporation** (26 rows) — the row's own 2001 annual report on Wayback:
  *"The Arctic Slope Regional Corporation was created pursuant to the Act."* (asrc.com renders
  client-side and returns nothing to a fetcher; the annual report is the durable source.)
- **Chickasaw Strategic Pointe / Health Consulting / Business Solutions** — each row's own
  chickasaw.com press release names CNI as the parent, and CNI's About page states
  *"Chickasaw Nation Industries, Inc. (CNI) is a federally chartered corporation wholly owned by the
  Chickasaw Nation."* Three-level chains, fully documented.

### 4. Housing authorities: a statutory basis, not a name guess
87 unruled parties came from HUD ONAP award lists. All six PDFs were downloaded and converted, and
**67 parties carry the verbatim award-list line** in their note. The ownership link rests on
NAHASDA, 25 U.S.C. 4103(22), retrieved from uscode.house.gov: a tribally designated housing entity is
one the tribe *"authorizes ... to receive grant amounts ... established by exercise of the power of
self-government of one or more Indian tribes."* The same subsection expressly contemplates
*"regional housing authorities"* — which is exactly why the six regional authorities below were ruled
`NATIVE_ORGANIZATION` rather than assigned an owner. This follows Elijah's own settled rulings on the
Colville, Comanche Nation, Yakama Nation, San Ildefonso and Fort Peck housing authorities.

### 5. Access notes (add to `docs/ACCESS_TECHNIQUES.md`)
- **Web search was unavailable** (session budget exhausted; DuckDuckGo's HTML endpoint returns a bot
  challenge to curl). Everything below was reached by constructing URLs directly. This is workable —
  About pages live at predictable paths — but it costs 2–3 attempts per firm.
- **`nana.com` is no longer blocked.** It has been on the manual-download queue for the whole project
  for a standing 403; a normal browser User-Agent returns 200 and the About page states ownership outright.
- **`ahtna.com` serves HTML fine** to a normal User-Agent, and its homepage carries the ownership
  sentence. The hard block in ACCESS_TECHNIQUES applies to its archived PDFs, not the live site.
- **`sec.gov` needs a User-Agent with contact details**, not just a browser string — a plain
  Chrome UA returned a 4.8 KB stub; `-A "CedarPress Research <email>"` returned the full 595 KB S-4.
- **JS-only sites return nothing**: asrc.com, waseyabek.com/about-us, bbnc.net/our-corporation,
  mohawknetworks.com, sanmanuel-nsn.gov, 500sails.org/about. For these, fall back to the deal's own
  source, to a subsidiary's site, or to Wayback.

---

## Traps hit — the ones that would have produced false attributions

1. **`Mattaponi Tribe` is not `Upper Mattaponi Tribe`.** The string matched the FR notice only because
   it is a *substring* of the federally recognized Upper Mattaponi Tribe. The Mattaponi Tribe (Mattaponi
   Indian Reservation, King William VA) is **state-recognized and not on the BIA list**, and
   `Upper Mattaponi Indian Tribe` appears in this same deals file as a *separate* party. Left UNRESOLVED.
   This is the single most dangerous auto-match in the file.

2. **`The Aleut Corporation` → the matcher proposed `Aleut Community of St. Paul Island`.**
   Corporation vs. tribal government. Ruled to the ANCSA regional corporation (NEID ANRC-ALEUTC-00)
   on its own words: *"one of 12 Alaska Native regional corporations established under the Alaska
   Native Claims Settlement Act."*

3. **`Chenega Corporation` → the matcher proposed `Native Village of Chenega`** (AKNF-CHNEGA-00).
   Village corporation vs. tribal government — and the Native Village of Chenega is *also* its own
   party in this file. Same error class for **`Afognak Native Corporation` → `Native Village of Afognak`**.

4. **`Salamatof Native Association Inc` vs `Salamatof Tribe`.** Both appear in this deals file.
   The Association is the ANCSA village corporation (*"a Native Corporation formed under the Alaska
   Native Claims Settlement Act of 1971 (ANCSA), with corporate offices ... in Kenai"*); the Tribe is on
   the BIA Alaska list. Two legal persons, two money flows.

5. **`Sitnasuak Native Corporation`** (village corp for Nome) is not the **Nome Eskimo Community**;
   **`Cape Fox Corporation`** (Saxman) is not the **Organized Village of Saxman**;
   **`Huna Totem Corporation`** (Hoonah) is not the **Hoonah Indian Association** — which is also in this file.

6. **`Department of Hawaiian Home Lands` / `Department of Hawaiian Homelands`** — a **State of Hawaii
   executive department**, constitutionally funded by the Hawai'i Legislature. It *serves* Native Hawaiian
   beneficiaries but is not an NHO and must never roll up as a Native entity.

7. **`Northwest Arctic Borough`** — an Alaska **home-rule municipality** (*"NAB was incorporated as a
   First Class Borough in 1986 and became a Home Rule Borough in 1987"*), 85.8% Alaska Native population
   but not a tribe, ANC or NHO.

8. **`Southwest Alaska Municipal Conference`** — a 501(c)(4) **municipal-membership** economic
   development body, not a Native organization.

9. **Component reservations of the Minnesota Chippewa Tribe.** `Leech Lake Band of Ojibwe`,
   `Mille Lacs Band of Ojibwe`, `White Earth Band of Chippewa Indians` and `Bois Forte Band of Chippewa
   Indians` appear on the BIA list only inside the MCT entry's parenthetical
   (*"Minnesota Chippewa Tribe, Minnesota (Six component reservations: Bois Forte Band (Nett Lake);
   Fond du Lac Band; Grand Portage Band; Leech Lake Band; Mille Lacs Band; White Earth Band)"*).
   Each is ruled to its band, with the MCT relationship recorded — do not silently collapse them into MCT
   or treat them as free-standing listings.

10. **`Shivwits Band of Paiutes`, `South Fork Band Council`, `Te-Moak Battle Mountain Band`** — constituent
    bands named inside a parent tribe's FR entry (Paiute Indian Tribe of Utah; Te-Moak Tribe of Western
    Shoshone Indians of Nevada). Ruled to the parent, band recorded.

11. **Joint ventures flagged partial, per the ARCTEC precedent**: `Arctic Inupiat Offshore LLC`
    (ASRC + six village corporations), `Doyon, Limited / Huna Totem Corporation (Na-Dena')`,
    `Doyon, Limited / The Aleut Corporation`, `Alaska Village Electric Cooperative / Stebbins Native
    Corporation`, `AVEC / Bethel Native Corporation`, `Southern Ute Growth Fund / Kava Equity Partners`,
    `Maniilaq Association / Tribal Development Partners`, and every
    `Waséyabek + Gun Lake Investments` / `Waséyabek + Potawatomi Ventures` row (two different tribes).
    Also `NANA Regional Corporation, Inc. (buyer); Arctic Slope Regional Corporation (seller)` — a
    two-sided row where ASRC must not be booked as an acquirer.

---

## Spine gap: ANCSA village corporations

The Cedar Press spine carries **zero** village corporations. **14 parties in this ledger are village
corporations** and therefore have no spine target. They are ruled `NATIVE ORGANIZATION - ANCSA village
corporation (<village>); spine gap` rather than forced onto the similarly named tribal government:

Ukpeaġvik Iñupiat Corporation (Utqiaġvik) · Chenega Corporation (+2 subsidiary strings) ·
Cape Fox Corporation (Saxman) · Bethel Native Corporation (+1 JV string) · Choggiung Limited (Dillingham) ·
Salamatof Native Association Inc · Sitnasuak Native Corporation (Nome) · Afognak Native Corporation ·
Old Harbor Native Corporation · Huna Totem Corporation (Hoonah) · Olgoonik Development LLC (Wainwright).

Additional village corporations appear *inside* the Arctic Inupiat Offshore joint-venture party string
and are not separately ruled: Atqasuk Corporation, Kaktovik Inupiat Corporation, Nunamiut Corporation,
Olgoonik Corporation, Tikigaq Corporation, Ukpeagvik Inupiat Corporation.

**Recommendation:** the ANCSA universe ceiling in `STATE_OF_BUILD.md` already names 196 ANCs including
173 village/urban corps in `Entity_Master`. Bringing those 173 into `data/spine/cedar_entity_spine.csv`
with an `A-` village-corp class would convert all 14 of these from organization-level records into
attributable entities — and would do the same for the ANCSA-portal deal rows.

---

## The 25 parties I could NOT resolve, and what I tried

| Party | Rows | What I tried | Why it failed |
|---|---:|---|---|
| Huna Totem Corporation | 2 | hunatotem.com `/`, `/about/`, `/about-us`, `/our-story/`, `/corporate/`, `/shareholders/`; NTIA awardee page | Site is JS-rendered and all About paths 404 into the homepage. *Ruled* on a secondary source (Wikipedia, quoted) and flagged for primary-source confirmation — counted as resolved-with-caveat, not clean. |
| Mattaponi Tribe | 1 | FR notice full-text; HUD FY23 ICDBG award list (line retrieved) | Matches the FR text only as a substring of **Upper Mattaponi Tribe**. The Mattaponi Tribe is state-recognized. Cannot tell whether HUD's line is shorthand for Upper Mattaponi or a genuinely different recipient. **Needs Elijah.** |
| Washoe HA | 1 | HUD FY24 IHBG-COMP list (line retrieved); FR notice | "HA" is almost certainly Housing Authority and the Washoe Tribe of Nevada & California is on the BIA list — but the abbreviation is not documented anywhere I retrieved. Withheld rather than guessed. |
| Tamaya Housing, Inc | 1 | HUD FY2018-19 list (line retrieved); santaana-nsn.gov; tamayaenterprises.com | "Tamaya" is the Keres name for Santa Ana Pueblo, but no retrieved page states the corporate relationship. Naming inference alone is exactly the "Cherokee Inc. trap." |
| Toiyabe Indian Health Project, Inc, for the Bridgeport Indian Colony, | 1 | HUD FY2024 ICDBG list (line retrieved) | A multi-tribe Native health nonprofit acting *for* a named tribe — needs a governance page to decide organization vs. entity-owned. |
| Tohono O'odham Utility Authority, Inc. | 1 | toua.net `/`, `/about`, `/about-us`, `/about-toua`, `/history`; NTIA awardee page | Site serves no ownership sentence. Almost certainly a Tohono O'odham Nation enterprise; not documented. |
| Mohawk Networks, LLC | 1 | mohawknetworks.com `/`, `/about`, `/about-us`; NTIA awardee page | Domain returns zero bytes. Elijah's Akwesasne→Saint Regis Mohawk alias makes this likely, but the ownership link is undocumented. |
| Yurok Telecommunications Corp. | 1 | yuroktelecom.com/about; yuroktribe.org | No ownership statement retrieved. |
| Aha Macav Power Service | 1 | mojaveindiantribe.com, fortmojave.com, critonline.com | No ownership statement retrieved. |
| Kootznoowoo Incorporated | 1 | kootznoowoo.com `/`, `/about`, `/about-us/`, `/history/`, `/corporation/` | Shareholder notices only; no self-description as a village corporation. |
| Benhti Economic Development Corporation | 1 | benhtiedc.com, benhti.com | Domains dead. |
| Alaska Tribal Spectrum | 1 | alaskatribalspectrum.com/.org | Domains dead. |
| Yukon-Kuskokwim Delta Tribal Broadband | 1 | NTIA awardee page only | No corporate site located without search. |
| Atautchikun, LLC | 1 | NTIA awardee page only | No corporate site located without search. |
| Ahtna Intertribal Resource Commission | 1 | ahtnatribal.org `/`, `/about/` | Pages return text but no governance/ownership sentence. Likely an intertribal org of the eight Ahtna tribes — undocumented. |
| Santa Fe Indian School | 1 | sfis.k12.nm.us `/`, `/about`, `/about-us`, `/history` | No governance sentence retrieved. Believed operated by the 19 Pueblos of New Mexico — undocumented. |
| Nebraska Indian Community College | 1 | thenicc.edu `/`, `/about`, `/about-us`, `/history` | Pages are near-empty to a fetcher. |
| California Rural Indian Health Board | 1 | crihb.org `/about/`, `/about-crihb/`, `/who-we-are/` | No governance sentence retrieved. |
| Riverside San Bernardino County Indian Health Inc | 1 | rsbcihi.org `/`, `/about-us` | No governance sentence retrieved. |
| Inter-Tribal Council Inc. (OK) | 1 | NTIA awardee page | Name too generic to resolve safely without a site. |
| United Urban Indian Council Inc. | 1 | NTIA awardee page | Urban Native nonprofit by name; no site located. |
| Haudenosaunee Environmental Task Force | 1 | NTIA awardee page | No site located. |
| Hiipaka LLC | 1 | waimeavalley.net `/about`, `/about-us/`; oha.org/waimea | Believed an Office of Hawaiian Affairs entity (Waimea Valley) — a genuine NHO question; not documented. |
| 500 Sails | 1 | 500sails.org `/`, `/about/`, `/our-story/`, `/mission/`, `/about-us/` | JS-only. A CNMI (Northern Marianas) Chamorro/Carolinian canoe nonprofit — probably outside the AIAN/ANC/NHO universe entirely, which is itself a scope decision for Elijah. |
| Native American Development Corp. | 1 | nadc-nabn.org `/about` | Page describes the Native American Manufacturing Network, not NADC's own ownership. A Native CDFI by the deal file's own typing. |
| Laguna Creek LLC | 1 | pr.com press release; tribalbusinessnews article | The deals file types it "Native-owned business." Under Elijah's Tallsalt Advisors / Tribal Energy Alternatives rulings, an individually Native-owned firm is **not** an entity-owned firm — so this must not be attributed without evidence of entity ownership. |

Every one of these is a *documented* dead end, not a skipped row. Nine of them would fall out
immediately if web search were available for one session.

---

## Notes for the next run

1. **`Gun Lake Investments` never appears as a standalone party string** — only inside combined
   Waséyabek/GLI rows. If the ledger is ever normalised into one-party-per-row, it becomes its own party.
2. **Party strings carry deal geography, not entity geography.** `Bristol Bay Native Corporation` is
   recorded with `State=AL`; `Chumash Capital Investments, LLC` with `State=FL`; `North Wind Group` with
   `State="AL / AK"`. Do not derive entity state from these columns.
3. **`Walker River Paiute Trib`** (truncated) and **`Warm Springs Housing Authority (WSHA),`** (trailing
   comma) are transcription artifacts in the deals files worth cleaning at source.
4. **`Seminole Tribe of Florida, Inc.`** is a distinct corporate entity from the Seminole Tribe of Florida
   government. It is attributed to the tribe here with the distinction recorded in the note; if Dataset 5
   ever separates governmental from corporate flows, this row needs re-examination.
5. The two aggregate IHBG rows and the two "~600 recipients" rows are portfolio records by the ledger's own
   convention (AGENTS.md: formula rounds = one portfolio row). They are ruled `MULTI-ENTITY` so they never
   attach to a single entity in Dataset 5.
