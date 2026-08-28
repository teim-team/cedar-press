# Phase 3 expansion sweep — round 1, 2026-08-27

Owner directive: look for more US tribes. 76 federally recognized tribes not
previously in the registry were checked across five regional batches
(Southwest, Oklahoma/Kansas, Pacific NW/Oregon, Great Lakes/Plains,
CA/NV/Southeast/Northeast). Search-only evidence grade (page fetch blocked in
the build environment); every claim rests on URLs that literally appeared in
results; raw per-tribe evidence with batch labels is in
`expansion_sweep_2026-08-27.jsonl`.

## Outcomes

- **7 new registry rows (TBD-166..172)**, each with a verification-log line
  and a search-only caveat:
  - **TBD-166 Siletz Tribal Business Directory** (stbcorp.net) — the best
    find: an official STBC directory of businesses with **any** CTSI-member
    ownership share (1–100%). The share must be preserved on every record —
    a listing is never a majority-ownership assertion. Tribal Secondary, Live.
  - **TBD-167 Nisqually NAOB Registry** — TERO orientation materials
    reference a maintained certified NAOB list that is not posted. Entered
    as Tribal Partnership Lead and added to the outreach roster (a
    Lummi-style one-request conversion).
  - **TBD-168 Pokagon Band Tribal Owned Business & Vendor Directory** —
    official PDF including citizen-owned small businesses; newest evidenced
    edition 2022, so entered Stale. Tribal Primary, identity-mixed (vendors).
  - **TBD-169/170/171 Pueblo enterprise pages** (Jemez, Pojoaque, San
    Felipe) — official pages naming tribally owned enterprises; entered as
    Tribal Secondary pilot rows with `tribal_government` identity scope.
    Whether enterprise pages belong in the registry as a class is a Phase 4
    taxonomy question; these three are the test cases.
  - **TBD-172 Chehalis Approved Vendors** — tribe-published business-license
    list updated monthly, named vendors visible; includes non-Native firms,
    so Discovery Only (the Swinomish TBD-108 pattern).
- **69 rows in `negative_findings.jsonl`** (the formal table the mission
  brief mandates): 62 `no_public_registry_found`, 2 `procurement_platform_only`
  (San Manuel vendor onboarding; Reno-Sparks bids), 5 `unresolved` with
  6-month rechecks — the interesting unresolveds being **Taos Pueblo's
  ARTISTS page**, **Santee Sioux "Local Business Page"**, and **Ohkay
  Owingeh's Tsay Corporation page** (enterprise records in prose). Others
  recheck after ~12 months so the same tribes aren't re-researched forever.
- **73 new crosswalk rows** in `nations.jsonl` (109 → 182) — every checked
  tribe now has a stable id whether the finding was positive or negative.
  One naming note: search results show San Manuel now styled "Yuhaaviatam of
  San Manuel Nation"; recorded with the former name as a variant, flagged
  unverified like all crosswalk names.

## Patterns worth keeping

- **TERO ≠ published roster.** Many checked tribes demonstrably run TERO or
  Indian-preference programs (Acoma, Jicarilla, Hannahville, Lac du Flambeau,
  Yankton, Seneca, Mohegan, Tunica-Biloxi, Absentee Shawnee, Suquamish,
  Makah, Lower Brule…) with no public certified list — these are future
  outreach candidates, recorded in the negatives' notes.
- **Oklahoma beyond the big nations is enterprise-page country**: the
  smaller OK tribes publish tribally-owned enterprise pages, not member
  registries; 15 of 15 checked came back negative.
- **Seneca has a worker skill bank, not a business list** — a useful
  reminder that TERO artifacts vary in unit of analysis.
- Adjacent finds logged in evidence: Neah Bay Chamber member directory
  (non-tribal, Makah-adjacent), Cow Creek's UIDC "BUY LOCAL" directory
  trademark with no live page yet.

## Round 2 (same day)

77 more tribes checked across five batches (remaining NM pueblos + Arizona,
Great Basin/Rockies, Southern/Central California, Northeast + Plains, PNW
leftovers + Alaska tribal governments — kept distinct from ANCSA corps). Raw
evidence appended to the same JSONL with batch labels.

- **3 new rows (TBD-173..175):** Fort Belknap **Program and Enterprise
  Directory** (a recurring dated-PDF series — 2017-18 edition on legmt.gov,
  2023 edition on the tribe's CDN; entered Stale); Houlton Band of Maliseet
  **Directory with an "Our Businesses" section** (weakest positive of the
  round — flagged for early inspection); Duck Valley **Community Directory**
  (community-wide incl. local businesses; Discovery Only).
- **The round's defining pattern: enterprise pages everywhere.** ~25 tribes
  publish official pages naming their tribally owned enterprises (Turning
  Stone/Oneida NY, Cayuga, Onondaga, Santa Ana, Ysleta del Sur, Ak-Chin,
  Fort McDowell, Viejas, Pala, Rincon/REDCO, Soboba, Chemehuevi, Tule
  River/TREDC, Table Mountain, Redding/RREDCO, Susanville/SIRCO, Iowa
  KS-NE/Grey Snow, Flandreau, Goshute/GFC, Kalispel, Shoalwater Bay/WBE,
  Sitka, Ketchikan/KTBC, Craig, Seldovia, Nambe, Picuris, Cocopah). Per the
  round-1 decision these are **held as an inventory** (URLs preserved in the
  negatives' notes and the raw JSONL) rather than registered — whether
  enterprise pages become a registry class is the Phase 4 taxonomy call,
  with the three Pueblo pilots (TBD-169..171) as test cases. If Phase 4
  says yes, this inventory converts to ~25 rows mechanically.
- **New unresolveds (6-month recheck):** San Ildefonso's official **Artists
  page** (the Taos pattern) and Metlakatla's community **Directory** (people
  AND organizations — flagged with a publication-boundary warning: person
  entries are never ingestible).
- **TERO-without-roster candidates for future outreach:** Torres Martinez
  (offices on both domains), Fort Mojave, Quechan (application PDF), Walker
  River, Kootenai of Idaho (ITD-listed director), Crow Creek (director on
  LinkedIn), Round Valley (TERO organizing — first public meeting).
- Wrong-tribe traps caught and excluded: oneida-nsn.gov (WI ≠ Oneida Indian
  Nation NY), crow-nsn.gov (MT ≠ Crow Creek SD), kickapootexas.org (TX ≠
  KS), metlakatla.ca (BC, Canada ≠ Annette Island).

## Round 3 (2026-08-28)

67 more tribes (Southern CA + Eastern Sierra, Northern CA Pomo country,
Central CA + NV/UT/AZ stragglers, Southeast/Southcentral Alaska tribal
governments) plus an org-level survey of the Alaska regional nonprofit
consortia (`research/ak_consortia_survey_2026-08-28.jsonl`).

- **2 new rows (TBD-176/177):** **Kawerak's Bering Strait Business
  Directory** (beringstrait.biz — browsable regional directory with
  individual business pages; covers local businesses generally, so
  discovery/corroboration grade, never an ownership assertion) and the
  **Hoonah Indian Association Business Directory List** (official-site
  directory page; scope unknown, early inspection flagged).
- **Fast-recheck unresolveds (2026-11-28):** Campo Kumeyaay — search
  summaries twice referenced a "Campo Business Directory" on campo-nsn.gov
  but no literal URL surfaced; Chilkat Indian Village (Klukwan) — site
  snippets twice state a list of Klukwan weavers exists in an "Artist
  Gallery" but the artist-list page never surfaced. Both likely exist.
- **Enterprise-page inventory grew by ~10** (La Jolla's five named
  enterprises, Sun'aq, Ione, Tuolumne/TEDA properties map, Mooretown,
  Middletown, Robinson, Scotts Valley, Habematolel/Habemco, Coyote
  Valley/CEDCO) — same hold-for-Phase-4 treatment.
- **Alaska consortia as enumeration frames:** TCC (42 members; the FY23-28
  477 Plan PDF enumerates villages), AVCP (56 tribes; CEDS PDF), APIA
  (tribes page names all 13), BBNA (31; Regional Reference Guide PDF),
  KANA (10), Chugachmiut (7), CRNA (6) — these are the practical frames
  for sweeping Alaska's ~200 villages in future rounds; promoting the
  strongest to Coverage Frame rows is a cheap follow-up if wanted. AFN's
  convention Customary Art Fair (~170-180 Native artist vendors) has no
  public roster (app-only per results); CITC's Indigenous Set Up Shop is a
  Native-exclusive entrepreneur program with no published cohort. Maniilaq:
  clean negative.
- Small-band pattern held: most CA rancherias and SE Alaska villages have
  government/service sites with no business registry — 62 more clean
  negatives with recheck dates, including a caught false-positive trap
  (a "TERO CERTIFIED BUSINESSES" PDF at pci-nsn.gov is Poarch, not
  Pinoleville).

## Round 4 (2026-08-28)

80 more entities across five batches — the first systematic Alaska-village
sweep using the consortia enumeration frames from round 3 (North Slope/NW
Arctic, Y-K Delta, Interior/TCC region, Bristol Bay/Aleutians/Kodiak) plus
the Oklahoma small-tribe and north-coast-California stragglers. Raw evidence
appended to the same JSONL with `r4-*` batch labels.

- **Zero new source rows — and that is the round's finding.** All 64 Alaska
  villages came back negative: village tribal governments publish
  council/program/contact pages, not business registries. The practical
  Alaska acquisition paths remain the regional layer already in the
  registry (ANC shareholder directories, Kawerak's beringstrait.biz
  TBD-176) plus **TCC's consortium-level TERO**, which per the Tanana check
  maintains an Indian-owned vendor listing region-wide for all 42 member
  villages (tananachiefs.org/services/job-training/tero/) — promoted
  same-day as **TBD-178** (Tribal Partnership, Lead): one request to TCC
  TERO covers 42 villages that individually publish nothing.
- **Enterprise-page inventory grew by 7** (Kaw KNBS, Ottawa OK, Modoc
  Nation, Seneca-Cayuga, Delaware Tribe of Indians/Bartlesville — kept
  distinct from Delaware Nation/Anadarko already in the registry — Bear
  River Rohnerville (page lives on the casino domain), Blue Lake Rancheria
  Economy page). Same hold-for-Phase-4 treatment; URLs preserved in the
  negatives' notes.
- **Fast-recheck unresolveds (2026-11-28):** McGrath Native Village —
  search summaries twice claimed a business directory on mcgrathnvc.com
  but no literal URL surfaced (and the *City* of McGrath's municipal
  directory is a nearby trap); Wiyot Tribe — wiyot.us runs a CivicEngage
  `BusinessDirectoryII` module titled "Resource Directory" whose category
  scope (tribal businesses vs. community resources) was not visible.
- **Single-enterprise-in-prose pattern:** several villages evidence exactly
  one tribally owned enterprise with no listing page (Igiugig's Iliamna
  Lake Contractors 8(a), Nulato Hills Enterprises LLC, Port Lions Farm,
  Elk Valley Tribal Fuel Mart) — recorded in the negatives' notes, not
  registrable as directories.
- **ANCSA-corp separations held:** Ouzinkie Native Corporation's
  business directory (ouzinkie.com/business-directory), Old Harbor Native
  Corp, Iliamna Natives Ltd, Gwichyaa Zhee Corp, Deloy Ges, and Mendas
  Cha-ag were all surfaced and excluded from tribal-government findings
  per scope (noted for the separate corporation track).
- Wrong-tribe traps caught: fortsillapache-nsn.gov enterprises page ≠
  Apache Tribe of Oklahoma; Canadian Odawa results ≠ Ottawa Tribe of OK;
  Oregon Modoc history pages ≠ Modoc Nation (Miami, OK).
- Ledger after integration: **405 of ~575 BIA entities checked** (117 with
  source rows, 288 negatives-only), ~178 unchecked — mostly Chugach-region
  and remaining small villages, small CA/NV bands, and misc stragglers.

## Follow-ups

1. Fetch-verify the 7 new rows at page level (egress unblock or local run).
2. Add Nisqually to the outreach queue send-list once a contact email is
   verified (none surfaced this pass).
3. Recheck the three 6-month unresolveds (2027-02-27).
4. Next expansion rounds: remaining ~340 unchecked federally recognized
   tribes — next candidates include the rest of the Eight Northern Pueblos,
   NV/UT/ID small tribes, remaining CA rancherias, and Alaska villages
   (coordinate with ANVCA frame). The daily discovery routine can take these
   a region at a time.
