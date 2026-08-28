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

## Round 5 (2026-08-28, second batch)

80 more entities across five batches; 77 integrated (three — Mi'kmaq
Nation, Kickapoo in Kansas, Sac and Fox of Missouri — turned out to be
round-1 re-checks caused by a candidate-filter bug that only compared
`bia_name`, not `names` variants; their fresh evidence stayed in the
research JSONL, the duplicate negative rows were dropped, and the filter
lesson is recorded here so future rounds compare all name variants).
Raw evidence appended with `r5-*` batch labels.

- **Alaska village pattern held at scale.** Bering Strait (16), Y-K Delta
  second sweep (16), Chugach/Cook Inlet/Kodiak (16), and
  Aleutians/Pribilofs/Peninsula (18) produced zero registries. Most
  villages' entire web presence is a BIA/NARF/consortium profile page;
  the ANCSA-corp-vs-tribe trap recurred constantly (afognak.org tribe vs
  afognak.com corp — whose *Shareholder Businesses* directory is
  corp-track material; tatitlek.com, chenega.com, salamatof.com all
  corps, not tribes).
- **Enterprise-page inventory grew by 5:** Kongiganak (official Google
  Sites with pages for Puvurnaq Power Co. and village businesses — the
  round's most interesting weak-form positive), **Aleut Community of St.
  Paul Island** (aleut.com/enterprise, ~5 enterprises incl. Awalix LLC),
  **Port Heiden** (four named Meshik/Aniakchak enterprise pages on the
  tribal site), **Upper Mattaponi** (umitribe.org/business-enterprises/),
  and **Sac and Fox of Missouri** (sacandfoxks.com /entities/ child
  pages). Same hold-for-Phase-4 treatment; URLs in the negatives' notes.
- **Fast-recheck unresolved (2026-11-28):** Colusa Indian Community —
  colusa-nsn.gov/government/economic-development/ ("CICC Operations")
  literally exists but search could not confirm it enumerates the
  tribe's enterprises (casino, energy, utility authority).
- **Virginia's 2018 cohort is nearly all negative** (Rappahannock,
  Chickahominy ×2, Nansemond, Monacan) — Upper Mattaponi is the
  exception via its enterprise page.
- Single-enterprise-in-prose leads for the corroboration file: Kipnuk
  Light Plant (DOE-documented tribally owned utility), Tununak Native
  Store, Karluk's Mary's Creek Cabin, Larsen Bay's tribally owned farm,
  Gambell/Savoonga Native Stores (ANCSA opt-outs, no corp trap).
- Ledger after integration: **482 of ~575 BIA entities checked** (117
  with source rows, 365 negatives-only), ~101 unchecked — the remainder
  is mostly middle-Kuskokwim/upper-Yukon villages (Georgetown, Stony
  River, Lime Village, Portage Creek, Tuluksak, the Kalskags, Aniak
  corridor…), the rest of the NANA/North Slope stragglers, and scattered
  small lower-48 bands.

## Round 6 (2026-08-28, third batch)

69 entities across five batches — the Alaska closeout (Arctic Slope regional
tribe + Seward Peninsula + lower-Yukon "paper villages", middle Kuskokwim,
Yukon-Koyukuk/upper Tanana, Copper River/SE/Bristol Bay leftovers) plus the
lower-48 finals the fixed candidate filter surfaced (Crow, Fort Peck,
Shakopee, Upper/Lower Sioux had genuinely never been checked). Raw evidence
appended with `r6-*` batch labels.

- **The round's two real conversions are wave-5 Leads coming true:**
  - **Fort Peck (TBD-096)** — the public roster the Lead said was "not
    located" exists: a literal page *TERO Certified Indian Owned Business
    M-R* on fortpecktero.org surfaced, evidencing an alphabet-paginated
    public certified list. Logged as conversion evidence (Lead retained per
    the no-upgrade-from-snippets rule); top page-level inspection target.
  - **Tlingit & Haida (TBD-122)** — the anticipated Native-owned business
    directory now has a literal public page
    (thbusinessresourcecenter.com/browse-businesses/). Caveat: results
    describe it as covering "indigenous AND minority owned businesses," so
    a listing alone is never a Native-ownership assertion. Same
    log-don't-upgrade treatment.
- **One new row: TBD-179, the Tlingit & Haida Certified Tribal Artist
  Program** (Tribal Primary, Live) — tribal-enrollment-gated artist
  certification (2014 Tribal Assembly resolution) with a public artists
  page on shoptlingithaida.com. Person-adjacent records: publication
  boundary review required before anything ships.
- **Crow (TBD-117) re-check:** still no public list — TERO office page
  under construction, regulations PDF public, FEMA solicitations reference
  "TERO approved contractors." Outreach remains the path.
- **The 62 Alaska checks were uniformly negative**, completing the pattern
  from rounds 4-5: village governments publish council/program pages, not
  registries. Notables in the negatives' notes: ICAS's new economic arm
  "Iñupiat Tribal Business Solutions" (CEDS 2025-30; watch for a page),
  King Island unresolved (claimed business-directory reference, no literal
  URL — fast recheck 2026-11-28; ivory-carver community makes an artist
  list plausible), Red Devil's council only recently reestablished after a
  decade dormant, and Cheesh-Na's Chistochina Enterprises (single Section
  17 corp — enterprise-page hold along with Upper Sioux and Shakopee).
- **Process note:** two more duplicate-check near-misses (Crow, Fort Peck)
  slipped past even the fixed name-variant filter because agent name forms
  ("Crow Nation") differ from BIA list forms ("Crow Tribe of Montana");
  both were caught by the integrity checker's crosswalk-uniqueness gates
  before anything landed, and folded into their existing rows. The
  integrity gate, not the filter, is the real guard.
- Ledger after integration: **548 of ~575 BIA entities checked** (117 with
  source rows, 431 negatives-only), **~35 unchecked** — at this point the
  remainder can't be reliably enumerated from memory; finishing requires
  fetching the actual BIA list and diffing against the crosswalk (the
  standing needs-human egress item).

## BIA list verified (2026-08-28)

The owner supplied the FR 2026-01-30 notice as a PDF (now the immutable raw
artifact in `research/bia_list_2026-01-30/` with a parsed `entities.json`),
closing the biggest needs-human item without waiting for egress. Outcomes:

- **Every crosswalk `bia_name` is now the official printed string and
  `name_verified_against_list: true`** — enforced by a bijection check in
  `tools/phase0_build_nations.py` that fails the build unless every BIA row
  maps to exactly one printed entry and every printed entry is represented.
  ~17 name-form fixes landed (e.g. "Pueblo of Nambe" not "Nambe Pueblo";
  "Chickahominy Indian Tribe—Eastern Division"; "Iqugmiut" not "Iqurmiut";
  official former names from 16 "previously listed as" annotations captured
  as variants).
- **575 confirmed from the primary source**; the "587" search-snippet figure
  is dead. 577 printed name-entries reconcile to 575 via the Venetie and
  Pribilof combined listings (their "(See ...)" pointers and groupings are
  documented in entities.json's count_note). The Capitan Grande combined
  entry covers both the Barona and Viejas rows.
- **Lumbee Tribe of North Carolina is on the list** (recognized by Pub. L.
  119-60, Dec 2025, with service-eligibility conditions noted in the FR
  text) — already crosswalked via a wave-5 source reference.
- **Corrections:** Valdez Native Tribe is not on the list → reclassified
  `nonbia:` (its round-5 negative row remapped); the round-5
  `bia:sac-and-fox-nation-oklahoma` row was a duplicate of the existing
  Sac & Fox Nation row (filter miss) → removed, negative row remapped.
  Seminole Tribe of Florida and White Mountain Apache — researched and
  excluded in wave 5 but never crosswalked — got rows plus formal negative
  rows citing the wave-5 log evidence.
- **The full list is imported**, so the unchecked remainder is no longer an
  estimate: **35 entities have never been checked** (excluding the MCT
  umbrella entity, which is represented by its six band rows) — 21 small CA
  rancherias/bands, Kickapoo TX, Meskwaki (IA), Saginaw Chippewa and Little
  River Ottawa (MI), Samish and Sauk-Suiattle (WA), and 7 AK villages
  (Ivanof Bay, Kaguyak, Napaimute, New Koliganek, Pedro Bay, Pitka's Point,
  Yupiit of Andreafski). These are the round-7 target list.

## Round 7 (2026-08-28) — sweep complete

The final 34 entities from the verified-list remainder. **With this round,
every entity on the 2026 BIA list has been checked** (the sole "unchecked"
crosswalk row is the Minnesota Chippewa Tribe umbrella entity, represented
by its six band rows): 117 nations carry source rows, 466 carry only
dated negatives with recheck dates.

- **Enterprise-page inventory grew by 11** — the biggest single-round haul,
  confirming that mid-size gaming tribes publish enterprise pages, not
  member registries: Saginaw Chippewa (sagchip.org/business/ — plus a
  Nov-2025 TERO ordinance stating TERO maintains an Indian-owned business
  listing: a top outreach candidate), Meskwaki Inc. "Our Companies",
  Yocha Dehe (/enterprises/ per-property pages), Paskenta, Tachi Yokut,
  Kickapoo Traditional Tribe of Texas, Northfork (which also runs a
  vendor Business Registration form — worth inspecting), Big Sandy,
  Augustine, Samish, and California Valley Miwok (MIWOK Global — caveat:
  CVMT has a long-running leadership dispute with rival web presences;
  verify the publishing faction before any registry use).
- **TERO-office-without-published-list outreach candidates:** Pit River
  (office page + director, no list) and Saginaw Chippewa (ordinance-backed
  listing, no list URL); Crow remains from round 6.
- **Fast-recheck unresolveds (2026-11-28):** Picayune (chukchansi-nsn.gov
  economic-development page — URL literally exists, content never surfaced;
  note the misspelled path 'economicdevlopment' is verbatim) and Santa
  Rosa Band of Cahuilla (economic-development page + TERO Commission on
  the boards page).
- Cedarville's agent-reported positive was demoted at integration (single
  enterprise in site text, no listing page — the Igiugig pattern).
  Napaimute is the most web-active of the final AK villages (Napaimute
  Enterprises LLC news posts, no listing page); Kaguyak, New Koliganek,
  Pitka's Point, and Yupiit of Andreafski have no web presence at all.

## Deep-dives + Native Hawaiian expansion (2026-08-28, owner-directed)

Maximum-depth passes on 20 maybe-public pages plus an NH discovery sweep
(raw evidence: `research/deepdive_nh_2026-08-28.jsonl`).

- **Three tribal promotions:** Pyramid Lake's public Business Directory
  (TBD-181 — enterprises AND a tribal-member-owned section), San Ildefonso's
  artist pages (TBD-182 — named individuals; publication boundary), and
  Metlakatla's community directory (TBD-183 — Discovery Only; people AND
  organizations).
- **A trap defused:** the unattributed "Certified Contractors List for
  TERO" belongs to Warm Springs (official copy at Oregon DOT) — and its
  visible contractors include large non-Native firms, so TBD-034 is a TERO
  COMPLIANCE list, never an ownership assertion (identity_mix flipped).
- **Resolutions:** Wiyot's module is a social-services directory; Colusa's
  CICC page is a utilities narrative; Lumbee's spotlights are nomination
  forms; King Island, Santee, Kwinhagak, Algaaciq, Asa'carsarmiut resolve
  clean-negative. Enterprise-page holds grew: Colusa Indian Energy, Santa
  Rosa Pit Stop/Toro Peak, Tsay subsidiaries (tsayfcg.net), Campo's Muht
  Hei. Still open with rechecks: Penobscot (form visible, listings
  unconfirmed), Taos, Campo directory, Chilkat gallery, McGrath, Picayune
  (better candidate found: chukchansi-nsn.gov/cse/).
- **Native Hawaiian block (TBD-184..191), owner-directed scope add** —
  individually owned AND NHO-entity, labeled: KEDA's certified NHBD (the
  only stated rule: >=50% NH owned/controlled, ancestry verified),
  Kuhikuhi, OHA's borrower showcase, Pop-Up Makeke (+The Makeke),
  both NH chambers, DOI/SBA 8(a) NHO list, NHOA members. All Cross-
  Reference with do_not_infer rows pending the Phase-4 NH-class decision.
  Adjacent notes kept in the research file: Mana Up cohorts (NH flagged
  ad hoc), DOI's NHOL (different NHO definition — consultation, not
  commerce), editorial one-off lists for cross-validation.

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
