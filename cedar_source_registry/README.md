# Cedar Press — U.S. Tribal & Native Business Source Registry (Wave 5)

Machine-readable source registry, originally exported 2026-08-27 from
`cedar_press_tribal_business_source_registry_us_wave5.xlsx`. **Authority:** the
xlsx is the frozen wave-5 snapshot; from wave 5.1 onward these versioned files
are canonical and the xlsx is not updated. For wave-5 content only, a
disagreement means the export was unfaithful — resolve against the xlsx and log
the correction.

## Files

| File | Records | One line per |
|---|---|---|
| `sources.jsonl` | 161 | source program (the master registry; 148 wave-5 + TBD-166..178 from the 2026-08 expansion rounds) |
| `scrape_queue.jsonl` | 92 | live source ranked for immediate ingestion |
| `partnership_leads.jsonl` | 57 | confirmed-but-unpublished roster to request directly |
| `negative_findings.jsonl` | 290 | Phase 3 formal negatives: tribes checked with no public registry found, with recheck dates |
| `cross_reference.jsonl` | 40 | secondary directory with `do_not_infer` guardrails |
| `verification_log.jsonl` | 141 | append-only fact-check log: 31 wave-5 lines (18 verified, 5 researched-and-excluded, 4 URL corrections, 2 edits reverted) + 97 wave-5.1 search-only re-checks (`channel: web_search_only`) + 13 expansion-round additions |
| `nations.jsonl` | 406 | nation crosswalk stub (Phase 0) — see "Nation crosswalk" below |
| `outreach/requests.md` | — | outreach queue for request-only sources (roster generated from partnership_leads.jsonl) |
| `PHASE_REPORT.md` | — | phase close-out: what was verified, changed, excluded, and the needs-human list |
| `research/newsletter_survey_2026-08-27.{md,jsonl}` | 42 outlets | tribal newsletter/media reconnaissance: dataset potential, business lists/awards coverage, Phase-3 candidates |
| `pipeline.py` + `PIPELINE.md` | — | the one-file dataset pipeline exemplar: registry-driven, staleness-aware, SQLite mock of the production database |
| `taxonomy.json` | — | identity taxonomy and grading rubric definitions |
| `record_schema.json` | — | recommended schema for *business* records ingested from these sources |
| `summary.json` | — | counts (computed from `sources.jsonl`, not transcribed) + matching rules |
| `HARMONIZED_SCHEMA.md` | — | two-layer harmonized dataset design: assertion layer + entity layer |
| `schema/source_record.schema.json` | — | JSON Schema (2020-12) for Layer-1 records; formalizes the workbook's Recommended Schema sheet |
| `schema/harmonized_entity.schema.json` | — | JSON Schema for Layer-2 resolved entities (identity as assertions, field provenance, persistent conflicts) |
| `templates/source_record.example.jsonl` | 2 | worked Layer-1 examples: a real Tulalip NAOB record + a clearly-marked illustrative cross-reference |
| `templates/harmonized_entity.example.json` | 1 | worked Layer-2 entity merging those two, validated against the schema |
| `templates/source_record.header.csv` | — | empty CSV header for Layer-1 exports |

Keys are snake_cased from the xlsx headers (`Nation / Source` → `nation_source`,
`Directory URL` → `directory_url`). `source_id` (`TBD-NNN`) is the join key across
every file. ID gaps (59–62, 84–94, 110–111) are intentional — removed non-U.S.
entries from earlier waves — not corruption.

## Nation crosswalk (Phase 0 stub)

`nations.jsonl` gives every nation the registry references one stable id, and
every `sources.jsonl` row carries `nation_ids: []` plus
`nation_scope: single_nation | multi_nation | regional | national | unknown`.
Regenerate with `tools/phase0_build_nations.py`; `tools/check_integrity.py`
enforces id resolution and name-variant uniqueness.

- `bia:<slug>` ids are entities on the BIA list of federally recognized tribes
  (2026-01-30 Federal Register notice, 575 entities). `bia_name` values are
  flagged `name_verified_against_list: false` until the list itself can be
  fetched and diffed (network egress is blocked in the build environment); the
  full-list import of unreferenced entities is pending for the same reason.
- `bia:minnesota-chippewa-tribe--<band>` rows key the six MCT component
  reservations separately (sources cite bands; the BIA list has one entity);
  `parent_nation_id` points at the parent.
- `nonbia:<slug>` marks referenced nations not on the BIA list (Patawomeck —
  Virginia state-recognized; Chappaquiddick Wampanoag — unrecognized), with
  `recognition` saying which.
- ANCSA corporations are not nations: ANC sources map to `nation_ids: []`,
  `nation_scope: regional`.
- `nation_ids` on a source row means "the nation(s) this source program is
  scoped to" — never an ownership assertion about any listed business.

## Evidence hierarchy (never flatten this)

`source_priority_class` encodes what a record from that source can *assert*:

1. **Tribal Primary** (45) — official tribal certification/member lists. Controls over everything.
2. **Tribal Secondary** (11) — tribal or tribe-linked, but mixed or non-certifying. May add records/fields; caveat travels with the data.
3. **Tribal Partnership** (52) — roster confirmed to exist, not public. Request directly; do not scrape thin evidence pages as if they were the roster.
4. **Cross-Reference** (32) — state/chamber/ANC/nonprofit directories. May propose matches and affiliations only; can never create a tribal-ownership assertion. Each row carries a `do_not_infer` field in `cross_reference.jsonl` — treat it as binding.
5. **Discovery Only** (2) / **Coverage Frame** (6) — candidate generation and TERO-universe enumeration only.

Conflicts persist as parallel source assertions; nothing silently overwrites a
tribal assertion. Chamber membership, state certification, or ANC shareholder
status is never evidence of citizenship in a particular tribe.

## Field semantics worth knowing

- `status_group`: `Live` (scrapeable now) / `Stale` / `Historical` / `Lead`
  (partnership evidence only) / `Complementary` (cross-reference).
- `scrape_grade` (A+–D) and `automation_score` (5–1) grade the *acquisition*, not
  the evidentiary weight — a D-grade Tribal Partnership lead still outranks an
  A+ chamber directory as evidence.
- `identity_mix: "Yes"` means the source can contain non-target-identity records;
  never bulk-label such a source's rows.
- `minimum_ownership_membership_rule` is quoted/paraphrased from the source at the
  level the source states it. Absence of a numeric threshold is recorded as such —
  do not backfill 51% by analogy.
- `last_checked`: only rows touched in a wave get that wave's date. A 2026-08-26
  date means "not re-verified in Wave 5," not "dead."

## Wave 5 delta (what changed vs Wave 4)

- **Verified against the live web (18 sources, all exist):** Tulalip TBD-030, Muscogee TBD-079, Grand Ronde TBD-032, CTUIR TBD-033, Poarch TBD-037, Navajo TBD-041, Cherokee TBD-042, EBCI TBD-043, Chickasaw TBD-018, Choctaw OK TBD-078, MS Choctaw TBD-080, Pawnee TBD-081, Minnesota OSP TBD-145, Koniag TBD-129, BBNC TBD-125, Lummi TBD-031, Coeur d'Alene TBD-044, Sisseton TBD-077.
- **Net URL corrections (4):** TBD-079 (CESO under Department of Commerce), TBD-145 (MN OSP `/about-us/state-government/`), and two Alaska regionals whose entries pointed at announcement/initiative pages instead of the actual directories: TBD-129 Koniag → **koniagbizdirectory.com** and TBD-125 BBNC → **BBNCShareholderBiz.com**. Two other same-day edits (TBD-032, TBD-033) were made and then **reverted** after page inspection showed the original paths canonical.
- **ANC scope caveats that matter for assertions:** Koniag admits businesses owned **or operated** by Shareholders/Descendants; BBNC admits **spouse**-owned businesses. Neither listing is, by itself, a Native-ownership assertion — preserve the relationship field on every record. The four other ANC entries (Chugach, Afognak, Bering Straits, Calista, plus the Ahtna lead) have directory-shaped URLs and were not re-inspected; check them during ingestion setup.
- **Stale-source conversion paths:** Lummi's TERO states a current NAOB registry is available on request (2022 PDF is just the last public artifact; Title 25 Ch. 25.07, 51% ownership/management/control, annual recertification). Coeur d'Alene and Sisseton both run active certification programs with no published roster — all three are one-email conversions from Stale to current coverage.
- **Page-inspection findings (acquisition detail invisible in search snippets):**
  - Tulalip `/TEROReports` renders the full ~45-record registry inline with CSV/TXT export controls and a small-business filter; nightly build stamp. `tulalip_owned_%` measures *Tulalip-member* ownership only — other-tribe certified businesses show 0%/N-A.
  - Grand Ronde's canonical `/government/tero/` page renders all ~82 IOBs inline (51 construction, 31 non-construction); certification requires proof of ≥51% Tribal-member-or-Indian ownership.
  - CTUIR's directory is one dated DOCX artifact (updated 2026-04-20) plus a separate ODOT Certified Contractors sub-list.
  - Navajo's NBOA Source List updates monthly (CAP-37-02) as dated PDFs under `/wp-content/uploads/`, with §204(A) priority tiers and expiration dates. Tier rule: P1 = 100% Navajo-owned; P2 = 51–99% Navajo, 51–100% other-Indian, or 100% Nation enterprises.
  - EBCI (bimonthly) and Poarch (dated) both publish list PDFs at predictable `/wp-content/uploads/` paths that bypass 403 landing pages.
  - Minnesota OSP exposes `vmpvendors.csv` plus added/removed-since-Jan-2023 delta files; category `I` = Indigenous American.
- **Added (TBD-157…163):** Gila River TERO, Pascua Yaqui TERO, Turtle Mountain TERO (certification runs through external ND offices — see caveat), Osage Nation Tax Commission vendor channel, AICC of California (site is mostly placeholders — outreach lead only), Washington OMWBE (monthly XLSX delta files, filter to Native owner categories), Council for Tribal Employment Rights (fourth coverage frame; national TERO umbrella).
- **Researched and excluded** (in `verification_log.jsonl`): Seminole Tribe of Florida (DemandStar), Sealaska (login-gated), Doyon (no public directory), White Mountain Apache (no public list located). The six ANC directories already in the registry appear to be the regionals that actually publish.

## Quick recipes

```bash
# Live tribal-primary scrape targets, best first
jq -s 'map(select(.source_priority_class=="Tribal Primary" and .status_group=="Live"))
       | sort_by(-.automation_score) | .[] | {source_id, nation_source, directory_url, scrape_grade}' sources.jsonl

# Everything for one state
jq 'select(.st_prov=="MN")' sources.jsonl

# Partnership outreach list with next steps
jq '{source_id, nation_source, recommended_next_step, source_url}' partnership_leads.jsonl

# What Wave 5 actually verified
jq '{source_id, source, result}' verification_log.jsonl
```

## Do not

- Do not treat `directory_url` liveness as re-verified unless `last_checked` says 2026-08-27.
- Do not promote a Lead to coverage without obtaining the roster.
- Do not merge records across sources on name alone; `schema/source_record.schema.json` is the binding contract for
  the per-source assertion layer (one row per business *appearance in one source*),
  and `schema/harmonized_entity.schema.json` for the entity layer — read
  `HARMONIZED_SCHEMA.md` before writing any merge code. Identity is never a boolean;
  spouse/operated_by never map to ownership; conflicts persist rather than overwrite.
