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

**CORRECTION 2026-09-01 — this entry is not what the tables say, and one of
the three answers is wrong.** Measured in
`cedar_identifier_ledger_final.csv`: four Suh'dutsing UEI rows sit at **tier
A**, method `hand`, pointing at **`TRBF-UNTHOR-00` (Ute Indian Tribe of the
Uintah & Ouray)** — a different nation, and the tier that publishes. The CAGE
rows for the same firms carry the owner's own later ruling,
`elijah_ruling_redirect` → **`TRBF-PTTRUT-00`**, at tier B. This file and
`503.RESOLUTIONS` say `CNSF-PTTRUT-CD`. The **withdrawal of `TRBF-UNTHOR-00` is
unambiguous** — two independent owner rulings refute it — but the choice
between the parent (`PTTRUT-00`) and the Cedar Band constituent
(`PTTRUT-CD`) is a granularity question for the owner, exactly as FA-01 handled
Bristol Bay. Filed in `docs/RESOLUTION_RULES_LEARNED.md` Part 4; **do not treat
the `CNSF-PTTRUT-CD` above as settled until it is.**

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

**Updated 2026-09-01: the Wichita Falls rule is now code, not a literal.**
`503.resolve()` was returning a tribe for **2,458 of the 5,197 names a human
had already refused (47%)**, almost all through its loose distinctive-token
subset path — because for the ~400 spine entities whose distinctive set is ONE
token that is also an American place name, that test is satisfied by every
organisation in the county. Two guards now sit on that path
(`ADMIN_GEOGRAPHY`, `CIVIC_FORM` in `503`), removing **1,403 false resolutions
with zero loss** on 1,952 owner-ruled entity names and 1,536 spine canonical
names. They also make the hand-written TUSCARAWAS entry in `RESOLUTIONS`
redundant — the shape rule reaches the same answer unaided. Full derivation,
counter-examples and blast radius: `docs/RESOLUTION_RULES_LEARNED.md` R1–R2.
Two carve-outs worth remembering here: **a county is never a tribe, but a
township can be** (Kayenta Township is Navajo, Indian Township is
Passamaquoddy), and **tribes run museums** (Makah Museum, Southern Ute
Cultural Center & Museum).

### A nation's whole name can be an ordinary English word

`TRBF-ENTPRS-00`'s canonical name is **Enterprise** (Enterprise Rancheria), so
its token matches any organisation carrying the word — 14 withdrawn keys in
`cedar_correction_register.csv`. The same defect runs through the owner's own
hand exclusions, where the collided word is a **surname**: "Old Crow Rudy",
"Creek Ronald", "Kills Crow Chad A", "Wells Timothy Michael", "Zunigha Curtis",
and the Robinson Rancheria / freight-brokerage collision that had to be ruled
**four separate times** for four spellings of one company. And a watercourse is
a Creek: "Marsh Creek", "Muddy Creek Oil & Gas".

**The rule: before a single-token entity may win a match, ask whether the token
is a word.** A distinctive-token set of size one on a common noun or a common
surname is not distinctive.

### Indigenous is not the same as American Indian / Alaska Native

Three separate refusals, three different reasons, all of which look identical
to a matcher:

- **Nisga'a** is a British Columbia **First Nation** — withdrawn 2026-08-06
  from a Tlingit & Haida attribution. Canadian First Nations are Indigenous and
  are not in the US federal universe.
- **"Arte Maya Tz'Utuhil"** (`EXCL-0044`) is Guatemalan Maya. Latin American
  Indigenous organisations are outside the frame.
- **"Indian" often means India.** `ST GEORGE INDIAN ORTHODOX CENTER OF STATEN
  ISLAND` was attributed to **St. George Tanaq Corporation**, Alaska. The same
  collision runs through the nonprofit exclusions: Hindu Temple of Greater
  Wichita, Peoria Area Punjabi/Telugu/Malayali associations, Gujarati Samaj of
  Peoria.

And the geographic form: **Indiana / Indianapolis / Indian Creek / Indian River
/ Indian Trail** are places. This one bites the gaming dataset specifically —
`Aztar Indiana Gaming Company` and `Caesars Southern Indiana` are commercial
casinos, not tribal gaming.

### A tribal name inside an enterprise name is a BRAND, not an owner

The most expensive false-positive shape in the corpus, because it produces a
*plausible* wrong answer at tier A rather than an obvious one. Every row below
is an owner ruling overturning a table
(`review/ruling_vs_table_contradictions_2026-08-26.csv`):

| the firm | the table said | the owner ruled |
|---|---|---|
| MUSKOGEE METAL WORKS / MUSKOGEE TECHNOLOGY | Lower Muscogee | **Poarch Band of Creek Indians** |
| ECHOTA DEFENSE SERVICES | Echota Cherokee (state-recognized) | **Cherokee Nation** |
| SEMINOLE NATION SERVICES, LLC | Seminole Tribe of Florida | **Seminole Nation of Oklahoma** |
| POTAWATOMI TRAINING LLC | Citizen Potawatomi | **Forest County Potawatomi** |
| RED CEDAR ENTERPRISES INC | Paiute Indian Tribe of Utah | **Modoc Nation** |
| FOUR TRIBES CONSTRUCTION SERVICES (+3 siblings) | Te-Moak | **Susanville Indian Rancheria** |

And the limiting case, `RUL-0002`: **Cherokee General Corporation is
Doyon-owned** — the Cherokee name predates the acquisition and carries no
Cherokee connection at all. The owner filed it as *"the classic Cherokee Inc.
trap."*

The inverse is just as true and is quantified: measured over the owner's own
2021 BGOV crosswalk, **347 of 750 confirmed tribe→vendor linkages (46.3%)
share not one non-generic token with the owning tribe's name** — Alabama-
Quassarte's `Aquate Corp`, Chitimacha's `Tiya`/`Wayti`/`Keta`, Comanche's
`Queni Engineering`, Blackfeet's `Syieh Development`. **Name matching has a
recall ceiling of roughly half on tribal subsidiaries, and no fuzzier matcher
raises it — the words are not there.** Only an ownership declaration crosses
that gap.

### One village name, two enterprise families, two different owners

`Eyak`, from `docs/ANCSA_OWNERSHIP_RULING.md`:

| enterprise family | owner |
|---|---|
| Copper River Family of Companies | **Native Village of Eyak** — the tribe |
| EyakTek / Eyak Services / Northtide / Solutions71 / Cordova Central | **Eyak Corporation** — the ANC |

A matcher keying on "Eyak" is wrong half the time whichever way it leans. This
is why an ANCSA village-government attribution must be evidenced **per
identifier and never per name** — and note that a ruling naming a *brand
family* is not a ruling about any one identifier.

Related, and easy to get loosely wrong — the owner's own correction,
2026-08-26: **"A shareholder is not necessarily enrolled in the tribe. A
shareholder necessarily has ancestry."** ANCSA shares descend by inheritance
and gift while village enrollment has been closed for a long time, so the
shareholder roll and the enrollment roll are two overlapping populations, not
two views of one list. Never infer either from the other, and never write the
village-corporation ↔ village-government relationship as an ownership edge.

## An exclusion register holds TWO different acts, and only the reason text separates them

**Added 2026-09-01. This is the most consequential thing mined out of the
owner's pre-Cedar work.**

An exclusion can mean *"this is not a Native entity"* or it can mean *"this is
outside the frame of the analysis I was running"*. They look identical in a
CSV. Reading the second as the first deletes real entities. The owner made the
call himself, once, in `RUL-0004`:

> `EXCL-0116` in `hci_analysis.do` reads `// ANC` — a SCOPE exclusion from a
> lower-48-tribes-only analysis, NOT an ownership exclusion. Doyon attribution
> stands; **$302.5M** in prime obligations retained.

It generalises much further than that one row. His `fed_funding_do_file.do`
exclusion block — 1,895 unique rulings, mined for the first time this pass —
drops by name:

| dropped in the do-file | n | what the Cedar spine now carries |
|---|---:|---|
| schools, colleges, universities | 202 | **185 BIE Schools + 37 Tribal Colleges** |
| health centres, hospitals, clinics | 74 | self-governance consortia, 43 Urban Indian Organizations |
| housing authorities | 195 | constituency and tribal-government entities |
| state-recognized tribes (Haliwa-Saponi, Lumbee, MOWA Choctaw, United Houma, Muscogee Nation of Florida, Chickamauga) | 86 | **64 `TRBS` rows** |
| inter-tribal / intra-tribal | 20 | **56 Intertribal Organizations** |

Roughly **570 names his earlier work excluded are entities the current spine
carries in their own class.** The two bodies of work do not contradict each
other — they answer different questions, and one batch even labels itself
honestly: *"the following tribe is federally recognized but not serviced."*

**Never re-run a legacy exclusion list against the current spine without an
`exclusion_kind` column — `scope` or `ownership`.** And do not over-correct:
the 26 `nonprofit_not_tribally_owned` rows in the same corpus are genuine
ownership refusals wearing the same formatting. The reason text is the only
discriminator, which is why it must never be dropped.

*(Related and already settled elsewhere: an intertribal organisation has
**members, not owners** — 30 lobbying rulings say so, and the do-file's
`inter-tribal` prefix drop agrees. There is no single-entity attribution to
make.)*

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

**The API route (checked 2026-08-29, MEASURED 2026-08-30).** cage.dla.mil has
no public API. The [SAM Entity Management API](https://open.gsa.gov/api/entity-api/)
(`api.sam.gov/entity-information/v3/entities?ueiSAM=<UEI>`, key via
`set_sam_key.ps1`) serves registration facts — name, CAGE, structure, state of
incorporation, address, website — and is the right tool **at adjudication time,
for a handful of lookups**. Measured limits, hit empirically:

- **our key is the 10-calls/day tier** (personal key, no role; 429 on call ~9);
- **`entityHierarchyInformation` is hidden at that tier** — 62 registrations
  pulled, zero carried it, including known subsidiaries that certainly declare
  parents. *An absent section therefore proves nothing about ownership* — an
  inference this file briefly recorded and retracts;
- the `ultimateParentUEISAM` search filter is untested (the 429 landed first);
- response pages cap at 10 records, whatever the batch size.

**The systematic route is public and unmetered: the parent-UEI columns on
FPDS/USAspending transaction files we already hold.** On 2026-08-30 the
assistance extract (602 MB, `recipient_parent_uei`, never previously harvested)
was added to `13_build_fpds_hierarchy.py`: **2,290 → 2,901 edges** and
**24,977 → 29,981 cage triples**, zero API calls. That file also settled BBAHC:
across 191 transactions its declared parent is **itself** — its own
highest-level owner, not BBNC. `511_sam_entity_hierarchy.py` (the API sweep)
is parked with its worklist saved; its shippable product was this harvest.
