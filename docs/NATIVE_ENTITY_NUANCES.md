# Native entity nuances — the working knowledge that resolves names

*Written 2026-08-28, after this knowledge took the assistance reconciliation
from 78% to 100% of dollars. Read with `docs/IDENTIFIER_STANDARD.md`. This is
domain knowledge, not policy — every claim here was verified against the spine
and the FR list during the reconciliation, and each pattern names the case that
proved it.*

## The entity types are not interchangeable

| type | what it is | id prefix | trap |
|---|---|---|---|
| Federally recognized tribe | sovereign government on the FR list | `TRBF` | the FR name is often not the name on a filing (renames, below) |
| AK Native **Village** (tribe) | a federally recognized government | `AKNF` | shares its name with a corporation that is NOT it |
| AK **Village Corporation** | an ANCSA business corporation | `ANVC` | "Native Village of Elim" (government) vs "Elim Native Corporation" (company). The Elim defect: a matcher preferring the shorter name picks the corporation. **Gov-class restriction kills this structurally.** |
| AK **Regional Corporation** | one of 12 ANCSA regionals | `ANRC` | shareholder/spouse-admitting directories are not ownership assertions |
| State-recognized tribe | recognized by a state, not the FR | `TRBS` | never promote to TRBF by name similarity |
| Constituency entity | a band/sub-government under one recognized tribe | `CNSF`/`CNSS` | **receives money in its own name** — excluding these classes left $1.5B "unmatched" |
| NHO | Native Hawaiian Organization | `NHO` | no authoritative federal roster exists; the universe is open |
| Individually Native-owned business | owned by a person, incl. person-named firms | `CEDAR-ENT-` | deliberately NO tribal link — `refuses_tribal_link_not_native_ownership` |

## The Federal Register parenthetical pattern

Some FR entries are ONE recognized tribe whose parenthetical names constituent
bands. The spine models both levels; money can arrive addressed to either.

- **Te-Moak Tribe of Western Shoshone** → four bands: Battle Mountain, Elko,
  South Fork, Wells (`CNSF-TEMOAK-BT/EK/SF/WL`). Filings arrive as
  "ELKO BAND COUNCIL" with no mention of Te-Moak.
- **Paiute Indian Tribe of Utah** → five bands: Cedar, Indian Peaks, Kanosh,
  Koosharem, Shivwits (`CNSF-PTTRUT-*`). "SHIVWITS BAND OF PAIUTES" is the
  Shivwits constituent, not a separate tribe.
- **Capitan Grande** is a combined listing → Barona Group and Viejas Group
  (`CNSF-CPTNGR-BA/VJ`). "BARONA BAND OF MISSION INDIANS" is the Barona Group.
- **Passamaquoddy** is the inverse quirk: ONE recognized tribe whose joint
  council is composed of two reservation governments that are NOT separately
  FR-listed — Indian Township and Pleasant Point/Sipayik
  (`CNSF-PSMQDY-IT/PP`). "PLEASANT POINT INDIAN RESERVATION" is Sipayik.
- **Shoshone-Bannock Tribes of the Fort Hall Reservation of Idaho** is ONE
  joint tribe (`TRBF-FTHALL-00`); money addressed to "the Tribes" goes to the
  joint government, not a band. (A matcher preferring "more specific"
  candidates wrongly dropped the parent here — the FR entry decides.)

## Renames the filings predate

Old federal filings carry names tribes no longer use. The spine holds the
current name; the filing needs an equivalence, not a new entity:

| filed as | is | id |
|---|---|---|
| San Manuel Band of Mission Indians | **Yuhaaviatam of San Manuel Nation** | `TRBF-YHVTSM-00` |
| Cortina Band of Wintun Indians | **Kletsel Dehe Wintun Nation** | `TRBF-KLTSLD-00` |
| Stewarts Point Rancheria | **Kashia Band of Pomo Indians** | `TRBF-KASHIA-00` |
| Aroostook Micmac Council | **Mi'kmaq Nation** | `TRBF-MIKMAQ-00` |
| Fort Sill Apache Tribe | **Fort Sill-Chiricahua-Warm Springs Apache** | `TRBF-FSCWSA-00` |
| Colusa Indian Community Council | **Cachil DeHe Band of Wintun Indians** | `TRBF-CACHLD-00` |

**Rule: a spine "gap" is usually an alias gap.** All 24 "missing" tribes in the
assistance reconciliation were in the spine under current names. Probe by
fragment and by history before minting anything.

## Same-name tribes are split by geography, and the money knows

Oneida Nation (NY) and Oneida Nation (WI) are different sovereigns.
Undecidable from the name; decided by `recipient_state_code` on the rows
themselves — 2,208 of 2,210 rows and $890M of $890M were WI. **When a name is
ambiguous, ask where the money went.** Same for Seminole (OK vs FL) — which is
why state tokens are never stripped in matching.

## Tribally-owned enterprises attribute to their ultimate owner

"SUH'DUTSING TECHNOLOGIES, LLC" looks like a random company; *suh'dutsing* is
Paiute for cedar, and it is the Cedar Band of Paiutes' enterprise →
`CNSF-PTTRUT-CD` under the hub model's ultimate-owner semantics (we assert the
owner, never the intermediate chain). Enterprise names are often in-language;
an unrecognizable LLC on a tribal contract deserves a language/ownership check
before an exclusion.

## Historical and synonym names are load-bearing

Filings, IRS records and old directories use the name a nation had when the
document was written. The alias layer must carry the history, and today it does
not fully:

| current (spine) | also known as / formerly | status 2026-08-28 |
|---|---|---|
| Yuhaaviatam of San Manuel Nation | San Manuel Band of Mission Indians | resolved in 503 |
| **Ohkay Owingeh** (`TRBF-OKYOWG-00`) | **San Juan Pueblo** (pre-2005) | **MISSING — and dangerous: "SAN JUAN PUEBLO" loose-matches the San Juan SOUTHERN PAIUTE (`TRBF-SNJUAN-00`), a different nation.** |
| **Three Affiliated Tribes** (`TRBF-MHATAT-00`) | **MHA Nation; Mandan, Hidatsa & Arikara Nation** | **MISSING from aliases** despite the id stem being MHA-TAT and the owner's own rule ("Three Affiliated is also MHA is also Mandan, Hidatsa and Arikara") |
| Kletsel Dehe Wintun Nation | Cortina Band of Wintun Indians | resolved in 503 |
| Kashia Band of Pomo | Stewarts Point Rancheria | resolved in 503 |
| Mi'kmaq Nation | Aroostook Band of Micmacs | resolved in 503 |

**Backfill these through the alias layer (418's pattern), not a script's dict**
— a resolution buried in one script's RESOLUTIONS helps one table; an alias
helps every matcher in the project.

## Unique characters: ʻokina, kahakō, and Alaska orthographies

- The **ʻokina is a consonant**, not punctuation: prefer **U+02BB** (ʻ) in
  canonical names. Measured 2026-08-28: the NHO register uses **U+2018**
  (typographic quote) throughout — clean UTF-8, wrong character. A console
  rendering it as `?` is NOT mojibake; check codepoints before "fixing" data.
- **Kahakō vowels** (ā ē ī ō ū) and Alaska Native orthographies (Yupʼik,
  Gwichʼin apostrophes; Iñupiaq ñ) appear in legal names.
- **Matching is already safe**: the resolvers normalize BOTH sides identically
  (diacritics and marks strip to the same key), so ʻOhana matches Ohana.
  **Display and canonical storage are where it matters** — never "normalize" a
  stored canonical name; store the correct marks and match on the folded key.
- The same word appears as ʻokina, right-quote, straight apostrophe, or nothing
  across sources (Suhʼdutsing / Suh'dutsing / Suhdutsing). Treat all as one key.

## Not everything Native-sounding is Native

"TUSCARAWAS METROPOLITAN HOUSING" is an Ohio county housing authority — the
county carries a Delaware-origin place name. A place named FOR a Native nation
is not a Native entity ("a place suffix makes a tribe name a place" — the
Wichita Falls rule, and its inverse). Record the exclusion so it never
re-surfaces as a candidate.

## Non-recognized ≠ non-existent

State-recognized (`TRBS`) and unrecognized communities are real organizations
that appear in filings and directories. They get spine rows in their own class
— never a TRBF row, and never silently dropped.

## Verifying ownership: the CAGE spiderweb, and why it cannot finish the job

*Added 2026-08-29 from an owner note, the same day it resolved FA-01.*

**The tool.** [cage.dla.mil](https://cage.dla.mil/Home/UsageAgree) — enter a UEI
or CAGE code, get the corporate hierarchy links up to the **highest-level
owner**. If the chain leaves ownership unclear, the company's own website
(about page, plus the address) makes the final call. Nearly every company that
contracts ends up in this database; it is rare to hold a CAGE or UEI and not be
there. The search sits behind a usage-agreement session cookie, so it is a
**manual** verification step, not a scraper target — which also keeps the
methodology human-replicable.

**Where the data comes from, so it is not double-counted.** The hierarchy is
the registrant's own FAR 4.18 / 52.204-17 ownership declaration filed through
SAM — self-certified, with DLA verifying only that the declared owner's CAGE
exists. In the assertion layer's terms it is the **LR_SAM evidence family**,
not an independent one. But it is a far stronger *kind* of claim than an
address: a legal ownership declaration, which is exactly what ultimate-owner
attribution needs.

**The caveat that makes the spine necessary (owner's words, 2026-08-29).** The
declared highest-level owner is often the highest *incorporated* owner — **Ho-Chunk,
Inc., not the Winnebago Tribe of Nebraska** — because the tribe itself need not
hold a CAGE in the chain. So the federal spiderweb can terminate one hop short
of the truth, and *it is impossible to establish a correct corporate hierarchy
outside of tribes doing it for you*. That last hop — holding company → tribe —
is Cedar's proprietary edge, and the reason the spine's ultimate-owner
knowledge cannot be replaced by any federal database.

**The spiderweb we already hold.** `data/clean/fpds_uei_edges.csv` carries
2,290 parent/ultimate-parent edges over 1,844 registrants, straight from FPDS
contract actions — no SAM API calls, no scraping. Measured 2026-08-29 it is
sometimes *better* than the worst case above: Ho-Chunk, Inc.'s declared parent
in FPDS **is** WINNEBAGO TRIBE OF NEBRASKA (90 observations). And it displays
the adjacent trap in its own rows: `HO-CHUNK NATION → HO-CHUNK NATION` sits
beside it — Wisconsin's Ho-Chunk Nation is a **different sovereign** from
Nebraska's Winnebago Tribe, one careless name-match away from a false merge
(the spine's `TRBF-WNNBGO`/phantom-id history in `71` is that exact lesson).

**Worked case: FA-01, Bristol Bay.** `cluster_v3` keyed UEI `NL5HNWNUFMK4`
(legal name BRISTOL BAY AREA HEALTH CORPORATION) to `ANRC-BRBYCO-00`, the ANCSA
regional corporation — "Bristol Bay" matched, the wrong Bristol Bay won. The
spine already held the health consortium as its own entity, `SGVF-BRSTLB-00`.
The withdrawal was propagated to all 10 stale tables (742 rows) by
`354_correction_register.py --apply`; the ledgers record it as **tier X**, so
the assertion layer now carries the permanent refutation. The **repoint** of
those rows to `SGVF-BRSTLB-00` keys dollars, so it is queued for an owner
ruling in `review/rulings_inbox_2026-08-29_agent.csv`, with the CAGE check
above as its verification protocol.
