# Dataset & validation-source discovery — round 1, 2026-08-27

Standing directive: keep identifying new datasets to add and sources for
validation. This round swept four frames in parallel — federal/procurement,
state certification programs, Native business orgs/awards, and validation
infrastructure. Raw per-candidate evidence (96 candidates + 4 frame summaries,
honest negatives included) is in `dataset_discovery_2026-08-27.jsonl`.
Evidence grade: search-only (fetch egress-blocked); every claim rests on
titles/URLs/snippets that literally appeared in results. Nothing here enters
`sources.jsonl` until it passes the Phase 3 bounded protocol with page-level
verification. A daily discovery routine continues from here, one frame per
round, appending only new findings.

## Top additions (new record-bearing datasets)

1. **IAC "Made/Produced by American Indians" trademark producer directory**
   (indianagfoods.org/producers) — a true certification-mark dataset: 500+
   licensed producers, eligibility requires tribal membership or 51% Native
   control, browsable state pages. Strongest new Indigenous-specific source
   found; food/ag sector.
2. **SBA DSBS bulk file via FOIA** — DSBS's own data-mining page routes bulk
   users to the FOIA frequently-requested-records copy of the full database;
   business types include tribally-owned/ANC/NHO (self-certified flags;
   8(a) status itself is SBA-verified). Needs a human FOIA request.
3. **Buy Indian awardees via FPDS/USAspending set-aside codes (IEE/ISBEE)** —
   enumerates actual Buy Indian Act award recipients in bulk downloads;
   $1.4B FY23 per BIA. Self-representation caveat travels; excellent event
   stream (awards are events, not entities).
4. **Alaska UCP DBE directory XLS** — daily-updated download that per results
   explicitly flags **ANC-Owned** firms certified under 49 CFR 26.63(c)(2);
   the only DBE feed found with an entity-owned flag.
5. **Texas HUB / CMBL download files** — published data files plus a distinct
   `AI = Native American` ethnicity code (vs a generic minority bucket).
6. **Oregon COBID** — ethnicity-filterable certified-vendor directory with
   download-all-to-Excel, updated daily (MBE general category; ethnicity
   field in export needs hands-on confirmation).
7. **SC Commission for Minority Affairs Native American Business Directory**
   — a wholly Indigenous-specific state-published list (2019 PDF; currency
   check needed). Fills a Southeast gap.
8. **New Mexico's statutory Native American resident business certificate**
   (NMSA 13-1-22, 51% tribally-connected ownership, TRD-issued) — the highest
   category specificity of any state found, but access is a per-certificate
   validation tool; the list itself likely needs a records request.

Watch list: NCAIED 40 Under 40 annual classes (named honorees with tribal
affiliations — event stream), NAFOA leadership awards, Native CDFI Network
member list (+ BIA/NWAF PDF snapshots), NativeAmerica.travel listings,
NNASC (new Native-founded certifier — no public roster yet), NY/NJ MSDC
Native-owned page, NACC-Illinois directory + its meta-list of Native chambers.
NEED (already TBD-065) re-confirmed as the top tribal-enterprise dataset;
whether business-level data is releasable is a needs-human question for the
Minneapolis Fed.

## The validation stack (sources for validating, never for asserting ownership)

Core: **SAM.gov Entity Management Public V2 extract** (monthly full + daily
deltas, layout docs located; UEI/CAGE liveness) · **Wayback CDX API** (free,
documented; proves what a directory asserted on a past date — fits the
source-versioning design directly) · **IRS EO BMF** monthly CSVs (Native
nonprofits/CDFIs; keys on EIN which Cedar excludes — match on name+address) ·
**CDFI Fund certified list** (Excel; 64 Native CDFIs as of Sept 2024).

Free state feeds, best first: **Oregon** Socrata Active-Businesses (best-in-
class), **Alaska** DCCED business-license CSV, **Minnesota** SOS weekly bulk
(free for non-commercial/press — Cedar likely qualifies), **WA DOR** Business
Lookup API + **WA L&I** contractor-license Socrata files, **CSLB** contractor
lists (CA). Cheap paid tiers: WI DFI ($5/mo new-entity feed), OK SOS monthly
master, NC/SD/ND subscriptions. Search-only states (NM, MI, AZ) are the gap
**OpenCorporates** could fill via its public-benefit API grant (application
needed; ODbL share-alike licensing question for legal review).

Statistical context only (never records): Census ABS AIAN-owned tables
(2022: 47,519 AIAN-owned employer firms, $78.5B receipts) and SUSB
denominators. ABS microdata confirmed FSRDC-restricted — question closed.

## Closed questions (don't re-search)

HUD Section 3 registry dead (phased out 2023-09-01, no replacement) · VA
CVE/VetBiz exposes no Native ownership · DOD Indian Incentive Program has no
public eligible-firm database · DOI OSDBU publishes no IEE vendor list (use
FPDS ex post) · no IACB registrant list beyond the Source Directory · NIBA
dormant · no SD/NE Native chamber found (Great Plains AICC barely evidenced)
· AZ, MI, NV, ID, UT, AK, CO have no state Indigenous-specific certification
data · WA SOS bulk extract discontinued (CCFS per-query export remains) ·
PowWows.com Shop Native is noise-level (includes non-Native-made "for
Natives" products).

## Systemic caveats

- **Oct 2025 USDOT DBE interim final rule**: state UCP directories are in
  reevaluation (ADOT states listed firms "not certified per the IFR"; CUCP
  froze counting 2026-03-02). Any DBE-derived record needs an
  as-of-reevaluation flag.
- Federal identity flags (SAM business types, DSBS tribal/ANC/NHO, IEE/ISBEE)
  are **self-attested** — cross-reference only, `do_not_infer` binding, and
  no tribal affiliation is ever named.
- Every "bulk export contains the ethnicity field" claim is snippet-level
  until fetched.

## Needs human

1. MN SOS non-commercial bulk-data request; 2. OpenCorporates public-benefit
application (+ ODbL legal review); 3. paid-tier decisions (WI $5/mo, OK SOS,
NC/SD/ND); 4. SC CMA — ask whether a post-2019 directory edition exists;
5. NNASC — ask whether a certified-supplier roster will be public; 6. NM TRD
certificate-list request (a state records request, not FOIA — needs owner
sign-off given the no-FOIA direction below).

## Owner decisions (2026-08-27, post-round-1)

- **NEED: access refused.** The owner reports the Minneapolis Fed will not
  grant access to NEED business-level data. NEED (TBD-065) is therefore
  aggregate/statistical context only; drop the access inquiry and never
  treat NEED-derived figures as record-level evidence.
- **No FOIA requests.** The SBA DSBS FOIA bulk route (and any similar FOIA
  path) is dropped per owner direction. DSBS remains a searchable-only
  cross-reference; Buy Indian awardees stay reachable through the ordinary
  FPDS/USAspending public downloads, which involve no FOIA.
- **Outreach emails to tribes whose rosters are stated available on request
  are approved** — worked through `outreach/requests.md`, starting with the
  documented on-request offices (Lummi, Coeur d'Alene, Sisseton, LTBB,
  Northern Cheyenne).
