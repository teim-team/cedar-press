# Deals Build Log — Entity Newsroom Sweep, 2026-08-05

Dataset 1 (Indian Country Deals). Channel: **entity newsrooms**, per AGENTS.md "Access
quirks" — the twelve corporations named there as UNSWEPT.

**Outputs**
- `data/clean/deals_2026_ytd_additions.csv` — **1 new row** (ND-2026-077)
- `data/clean/deals_historical_additions.csv` — **30 new rows** (2021–2025)
- `review/deals_skipped_leads_2026-08-05.csv` — **18 skipped leads**
- Log: `logs/22_deals_2026-08-05.log`

Nothing was written into `deals_2026_ytd.csv` or `deals_historical_2020_2025.csv`.
Both additions files were validated column-for-column against the live files, and
Deal_IDs were checked for collisions against both (none).

---

## The rule applied this session

Every dollar figure and every date below was re-read in retrieved page text before it
was written. Where a figure existed only in a search-engine summary, an aggregator, or a
directory, it was not written. Where a date existed only as a site posting stamp, the row
was skipped. Three separate value traps were caught and excluded — they are documented
under "Value traps" below because they are the kind of error that would have silently
entered the ledger.

---

## Per-entity results

### Doyon, Limited — SWEPT. 3 rows, 2 skips.
`doyon.com/news/` fetches fine but is a shareholder-notice feed (fuel costs, registry,
fire management); deal announcements live at unindexed slugs reached by search.

| Outcome | Item |
|---|---|
| ADDED | ND-2023-005 — acquires Fairweather, LLC (2023-05-01), undisclosed |
| ADDED | ND-2024-005 — **divestiture**: sells its Doyon Anvil JV interest to Anvil Corp (2024-01-02) |
| ADDED | ND-2022-004 — Na-Denaʼ JV with Huna Totem; JV takes 80% of Alaska Independent Coach Tours, closed 2022-02-01 |
| ADDED | ND-2025-019 — with The Aleut Corporation, US$5.0M into Graphite One (2025-10-06) |
| SKIPPED | Doyon Government Group — ten award posts incl. a $200M Army MATOC, all stamped 2026-06-09, no award dates (`no_date`) |
| SKIPPED | Fish Lake Final Conveyance — index headline only, not retrieved (`no_amount`) |

Note: ND-2025-019 is filed under Doyon but the row is co-principal with The Aleut
Corporation and the $5.0M is **combined** — the release gives no per-corporation split,
so none was invented.

### NANA Regional Corporation — BLOCKED (partial).
`nana.com/news/` and `nana.com/category/press-releases/` both return **HTTP 403** to
automated fetch. The pre-Drake NANA history AGENTS.md wanted remains uncaptured through
this channel. One row recovered via the Akima subsidiary domain, which does fetch.

| Outcome | Item |
|---|---|
| ADDED | ND-2023-004 — Akima, LLC definitive agreement to acquire Pinnacle Solutions (2023-04-10) |
| EXCLUDED (dup) | NANA/Drake Construction — already ND-2026-072 |

**Manual download needed: nana.com.** Attribution note — project records say Akima is
owned jointly by NANA and The Aleut Corporation, but both retrieved sources name only
NANA, so only NANA is asserted in the row.

### Ahtna, Incorporated — BLOCKED. 1 row, 4 skips.
`ahtna.com` returns **HTTP 403** on both `/news/` and the individual announcement slug
tried. Everything captured came from third-party press.

| Outcome | Item |
|---|---|
| ADDED | ND-2025-015 — reacquires 4,228 acres from the U.S. Air Force, transfer mid-May 2025, Confidence **Medium** |
| SKIPPED | Cavache, Inc. acquisition — 2019-11-19 (`out_of_window`) |
| SKIPPED | North Slope pad space from AIDEA — published 2020-01-03 but no transaction date; likely a 2019 close (`no_date`) |
| SKIPPED | AAA Valley Gravel — page 403s (`no_date`) |
| SKIPPED | Subsidiary federal contract actions — USAspending/HigherGov only (`aggregator_only`) |

**Manual download needed: ahtna.com.**

### Bristol Bay Native Corporation — SWEPT. 1 row, 1 exclusion.
`bbnc.net/news/` fetches but carries only shareholder notices (picnic, enrollment, tax
info). No primary deal releases found.

| Outcome | Item |
|---|---|
| ADDED | ND-2025-012 — majority ownership of Alaska Growth Capital (2025-01-08), Confidence **Medium** |
| EXCLUDED | Blue North Fisheries / Clipper Seafoods — effective **2019-09-30** (`out_of_window`) |

The Blue North exclusion matters: search summaries framed it as a "2025–2026"
acquisition. The retrieved article dates it to 2019. Had the summary been trusted, a
six-year-misdated row would have entered the 2025 file.

### Afognak Native Corporation / Alutiiq — SWEPT, ZERO YIELD.
`afognak.com/news/` is a stub ("News TEST" page) with two 2023 non-deal items. No
acquisition announcements located for 2020–2026. The only event surfaced was the December
2024 rename of Alutiiq Diversified Services to Afognak Diversified Services — a rename,
not a transaction; logged for the entity spine, not the ledger.

### Ukpeaġvik Iñupiat Corporation — SWEPT. 2 rows, 2 skips. Best-structured newsroom of the twelve.
`uicalaska.com/news/` fetches cleanly with dated, permalinked releases.

| Outcome | Item |
|---|---|
| ADDED | **ND-2026-077** — majority interest in Northbank Civil and Marine (2026-01-16) |
| ADDED | ND-2024-009 — majority interest in Delta Solutions & Strategies, **effective 2024-11-29** (UIC's largest to date) |
| SKIPPED | HC Contractors / Alaska Veterans Cemetery — the $16.7M is a VA grant to the State of Alaska, not UIC's contract value (`no_amount`) |
| EXCLUDED (dup) | Iḷisaġvik College land purchase — already ND-2026-053 |

Also confirms MA2020-001's open item is still open: no UIC/Johansen Construction release
surfaced in the 2020 archive.

### Poarch Band of Creek Indians / Wind Creek Hospitality — SWEPT. 2 rows.
`pci-nsn.gov` fetches fine.

| Outcome | Item |
|---|---|
| ADDED | ND-2023-003 — completes purchase of Magic City Casino, Miami, closed **2023-02-27**, **$96,000,000** recorded deed price |
| ADDED | ND-2025-014 — completes purchase of the Birmingham Racecourse (2025-04-02), undisclosed |

Magic City is the largest disclosed figure added this session and the one with the most
careful value handling — see "Value traps."

### Cherokee Nation Businesses / Cherokee Federal — SWEPT. 2 rows, 2 skips.
`cherokee-federal.com/all-news-insights` fetches but the index surfaces **only 2026
items** to automated fetch; 2025 releases were reached through the wire services.

| Outcome | Item |
|---|---|
| ADDED | ND-2025-018 — Sovereign Capital majority stake in MSI, LLC (2025-09-02) |
| ADDED | ND-2025-020 — acquires HigherEchelon's Salesforce practice, **effective 2025-11-01** |
| SKIPPED | NASA SEWP VI award — no ceiling stated (`no_amount`) |
| SKIPPED | GSA OCAS MSS sole-award BPA — no value stated (`no_amount`) |
| EXCLUDED (dup) | Front Line Power Construction — already ND-2026-010 |

Both skipped items are probably material. They are the highest-value follow-ups on the
list, resolvable through FPDS.

### Chickasaw Nation Industries — SWEPT. 6 rows. Richest single newsroom.
`chickasaw.com/about/news` returns a fully dated index of acquisitions *and* contract
awards going back to 2018. Each item below was retrieved individually, not taken from the
index.

| Outcome | Item |
|---|---|
| ADDED | ND-2021-007 — Chickasaw Health Consulting, $25M CDC contract (2021-08-02) |
| ADDED | ND-2021-008 — CNI Manufacturing, $6.2M FAA contract (2021-08-24) |
| ADDED | ND-2021-009 — acquires DIGITALiBiz, Inc. (2021-09-02) |
| ADDED | ND-2021-011 — Chickasaw Business Solutions, $24.4M USDA FSA contract (2021-10-29) |
| ADDED | ND-2022-005 — acquires IPKeys Technologies (2022-08-01) |
| ADDED | ND-2023-006 — acquires Washington Business Dynamics (2023-07-05) |
| EXCLUDED (dup) | 5 Bars Services — already MA2020-012 |

ND-2021-011: the headline rounds to "$24M"; the body says $24.4M over five years if all
options are exercised. The body figure was used and the option caveat disclosed.
ND-2022-005: State and Location left **blank** — the release names no target location and
none was inferred.

### Ho-Chunk, Inc. — SWEPT, ZERO YIELD. 1 skip.
`hochunkinc.com/news/` fetches but is a community/intern/gallery feed; no transaction
releases surfaced across 2023–2026.

| Outcome | Item |
|---|---|
| SKIPPED | Subsidiary buys $1.3M of farmland (231 acres) on the reservation — Lincoln Journal Star redirects to a TollBit paywall; body unreadable (`aggregator_only`) |

Do not confuse with **Ho-Chunk Nation of Wisconsin**, a different tribe, already in the
ledger at ND-2025-004 ($610M Beloit financing).

### Gun Lake Investments — PARTIAL. 2 rows, 2 skips.
`gunlakeinvestments.com/news/` returns **404**; the homepage does surface a dated headline
list, which is how the Hot 'n Now trail was picked up.

| Outcome | Item |
|---|---|
| ADDED | ND-2024-006 — CSM Services acquires Custodial Housekeeping Staffing (2024-02-23), Confidence **Medium** |
| ADDED | ND-2024-008 — acquires the Hot 'n Now brand with Jeff Konczak via HNN Holdings, **October 2024**, mid-month placeholder |
| ADDED (joint) | ND-2021-010 — with Waséyabek, Zip Xpress and Green Transportation (2021-10-26) |
| SKIPPED | Wayland mixed-use apartment complex / U.S. 131 corridor — no date, no value (`no_date`) |
| SKIPPED | Crain's Grand Rapids corroboration — HTTP 403 (`aggregator_only`) |

**ND-2024-008 is the strict-window case of this session.** It was announced 21–22 January
2025 and would naturally have landed in 2025. The transaction is reported as October 2024,
so the row is filed in **2024**. `Event_Date` 2024-10-15 is a **mid-month placeholder**,
disclosed in `Date_Basis` exactly as the convention requires. No day was invented.

### Waséyabek Development Company — SWEPT. 10 rows. Highest yield of the twelve.
`waseyabek.com/news/` returns a complete dated archive back to 2019 with clean permalinks
— the best-behaved newsroom encountered. Every item below was retrieved individually.

| Outcome | Item |
|---|---|
| ADDED | ND-2021-010 — Zip Xpress + Green Transportation, jointly with Gun Lake Investments (2021-10-26) |
| ADDED | ND-2021-012 — majority owner of Safari Circuits (2021-12-30) |
| ADDED | ND-2022-006 — buys the RSI of West Michigan building + adjacent lot, **closed 2022-09-12** |
| ADDED | ND-2023-007 — majority owner of BLDI, LLC (2023-09-18) |
| ADDED | ND-2023-008 — majority owner of VES, LLC (2023-12-01) |
| ADDED | ND-2024-007 — with Potawatomi Ventures, strategic investments in BAMF Health (2024-08-19), Confidence **Medium** |
| ADDED | ND-2025-013 — Great Lakes Warehousing + 156 acres, Holland MI (2025-02-04) |
| ADDED | ND-2025-016 — **$205M** NETL five-year contract (2025-06-24) |
| ADDED | ND-2025-017 — **$5M** into Michigan Capital Network (2025-07-29) |
| ADDED | ND-2025-021 — Safari Circuits acquires the former LaCroix Grand Rapids plant (2025-12-02) |
| SKIPPED | Original Nov 2021 BAMF Health investment — not retrieved, no amount, double-count risk against ND-2024-007 (`no_amount`) |
| EXCLUDED (dup) | McKay Tower JV (2020) — already ACQ2020-016; RSI operating company (2020) — already MA2020-007 |

ND-2022-006 is deliberately *not* a duplicate of MA2020-007: Waséyabek bought the
operating company in August 2020 and the **real estate** in September 2022, from a seller
who had retained the building. Two events, two rows, no double-count.

---

## Value traps caught and excluded

1. **Magic City Casino (ND-2023-003).** The recorded Miami-Dade deed price is $96M;
   Commercial Observer separately *estimates* full deal value near $600M including the
   gaming license. Only the $96M recorded price is in `Announced_Value_USD`. The $600M
   estimate appears in Notes as an estimate and is in **no** value field, including
   `Project_Total_Value_USD`.
2. **Safari Circuits / LaCroix plant (ND-2025-021).** The release's only dollar figure,
   $750,000, is planned **new equipment** spending, not the purchase price. Excluded from
   all value fields; noted.
3. **HC Contractors / Alaska Veterans Cemetery (skipped).** The $16.7M is a VA grant to
   the State of Alaska. Attributing it to UIC would have been a false attribution of a
   federal grant as a tribal contract award. Row skipped entirely.

## Date audit — one conflict resolved

The Graphite One / Doyon + Aleut release was rendered by an intermediary summary as
**October 6, 2024**. The PR Newswire dateline was re-read directly and reads
**"VANCOUVER, BC, Oct. 6, 2025."** The URL slug and syndication IDs agree with 2025. The
row is filed as **2025-10-06**. Recorded here because the same intermediary path is used
throughout this build and this is the one place it demonstrably got a year wrong.

## Newsrooms that block automated fetch — manual download queue

| Domain | Status | Why it matters |
|---|---|---|
| `nana.com` | HTTP 403 (both news paths) | Pre-Drake NANA history, the specific gap AGENTS.md flagged |
| `ahtna.com` | HTTP 403 (index + slugs) | Whole Ahtna deal history |
| `crainsgrandrapids.com` | HTTP 403 | Recurring source for Michigan tribal deals (Waséyabek, Gun Lake) |
| `journalstar.com` | TollBit paywall gateway | Ho-Chunk Inc. land purchases |
| `gunlakeinvestments.com/news/` | HTTP 404 | Homepage headline list is the workaround |
| `cherokee-federal.com/all-news-insights` | fetches, but indexes 2026 only | 2025 releases reachable via wires |

Consistent with the AGENTS.md note that uploaded files bypass all robots restrictions.

---

## Confidence distribution of added rows

| Confidence | Count | Which |
|---|---|---|
| High | 26 | Primary company release, or primary + independent |
| Medium | 5 | ND-2024-006, ND-2024-007, ND-2024-008, ND-2025-012, ND-2025-015 |

Every Medium row carries its reason in `Notes`: no primary release located, no amount
disclosed at all, month-level placeholder date, or a dollar figure whose scope is narrower
than the transaction.

## Ownership-change records emitted (per AGENTS.md "the subtle insight")

19 of the 31 added rows are acquisitions, divestitures or majority-stake changes and
should emit ownership-change records into the time-aware attribution ledger. The
divestiture — **ND-2024-005, Doyon Anvil exiting the Doyon family on/about 2024-01-02** —
is the highest-value one, since FPDS will not have updated retroactively.

## Follow-ups, ranked

1. Cherokee Federal's **GSA OCAS MSS sole-award BPA** and **NASA SEWP VI** — pull ceilings and award dates from FPDS.
2. **Doyon Government Group** — resolve award dates for the ten posts (a $200M MATOC among them); re-read each post individually, the index showed headline/body value mismatches.
3. Manual download of **nana.com** and **ahtna.com**.
4. Ho-Chunk Inc. **$1.3M farmland** purchase — manual retrieval of the Journal Star piece.
5. Waséyabek's **Nov 2021 BAMF Health** release — resolve the double-count question against ND-2024-007.
