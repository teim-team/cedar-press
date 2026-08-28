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
