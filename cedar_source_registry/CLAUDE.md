# Cedar Press — U.S. Tribal & Native Business Source Registry (Wave 5)

Machine-readable source registry, originally exported 2026-08-27 from
`cedar_press_tribal_business_source_registry_us_wave5.xlsx`. **Authority:** the
xlsx is the frozen wave-5 snapshot; from wave 5.1 onward these versioned files
are canonical and the xlsx is not updated. For wave-5 content only, a
disagreement means the export was unfaithful — resolve against the xlsx and log
the correction.

## Files

Counts as of 2026-08-28 (wave 5.1 + expansion rounds; README.md's table is the
authoritative current copy):

| File | Records | One line per |
|---|---|---|
| `sources.jsonl` | 174 | source program (148 wave-5 + TBD-166..191, incl. Native Hawaiian block TBD-184..191) |
| `scrape_queue.jsonl` | 105 | live source ranked for immediate ingestion |
| `partnership_leads.jsonl` | 57 | confirmed-but-unpublished roster to request directly |
| `negative_findings.jsonl` | 484 | Phase 3 formal negatives with recheck dates — with sources.jsonl this covers every entity on the 2026 BIA list |
| `cross_reference.jsonl` | 48 | secondary directory with `do_not_infer` guardrails |
| `verification_log.jsonl` | 164 | append-only fact-check log |
| `nations.jsonl` | 584 | nation crosswalk — every `bia_name` verified against the FR 2026-01-30 list (`research/bia_list_2026-01-30/`) |
| `summary.json` | — | counts computed from sources.jsonl (never transcribed) + coverage ledger |
| `pipeline.py` + `PIPELINE.md` | — | one-file dataset pipeline exemplar |
| `outreach/requests.md` | — | outreach tracker (waves 1-2 sent 2026-08-28 from the owner's Cornell address) |

Regenerate: `tools/phase0_build_nations.py` (crosswalk, verifies against the
official list and fails on mismatch), `tools/build_summary.py`,
`tools/build_outreach.py`; gate everything with `tools/check_integrity.py`.

Keys are snake_cased from the xlsx headers (`Nation / Source` → `nation_source`,
`Directory URL` → `directory_url`). `source_id` (`TBD-NNN`) is the join key across
every file. ID gaps (59–62, 84–94, 110–111) are intentional — removed non-U.S.
entries from earlier waves — not corruption.

Phase 0 (post-wave-5): `nations.jsonl` is the nation crosswalk stub and every
`sources.jsonl` row carries `nation_ids` + `nation_scope` — see README "Nation
crosswalk". Use `nation_id`s, never free-text nation names, in new work.

## Evidence hierarchy (never flatten this)

`source_priority_class` encodes what a record from that source can *assert*:

1. **Tribal Primary** (47) — official tribal certification/member lists. Controls over everything.
2. **Tribal Secondary** (21) — tribal or tribe-linked, but mixed or non-certifying. May add records/fields; caveat travels with the data.
3. **Tribal Partnership** (54) — roster confirmed to exist, not public. Request directly; do not scrape thin evidence pages as if they were the roster.
4. **Cross-Reference** (40) — state/chamber/ANC/nonprofit directories. May propose matches and affiliations only; can never create a tribal-ownership assertion. Each row carries a `do_not_infer` field in `cross_reference.jsonl` — treat it as binding.
5. **Discovery Only** (6) / **Coverage Frame** (6) — candidate generation and TERO-universe enumeration only.

Conflicts persist as parallel source assertions; nothing silently overwrites a
tribal assertion. Chamber membership, state certification, or ANC shareholder
status is never evidence of citizenship in a particular tribe.

## Field semantics worth knowing

- `status_group`: `Live` (scrapeable now) / `Stale` / `Historical` / `Lead`
  (partnership evidence only) / `Complementary` (cross-reference) / `Obtained`
  (roster in hand but **not** published at a pollable URL — supplied by the
  Nation or by the owner, so it refreshes by re-asking, never by crawling).
  `Obtained` is deliberately not `Live`: conflating them would put a scraper on
  a URL that does not serve the roster.
- **Publication rights are separate from possession.** Holding a roster does not
  license republishing it. An `Obtained` source stays unpublished until the
  Nation confirms; the `caveats` field carries that state.
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

## Cross-platform: always declare an encoding

This repo is written on Linux runners (UTF-8 default) and also run on the
owner's Windows machine (cp1252 default). **Every text-mode file operation must
name its encoding**, including `subprocess.run(..., text=True)`, which decodes
with the locale unless told otherwise.

Fixed 2026-08-28 (30 call sites + one subprocess): before that, on Windows,
`check_integrity.py` reported 10 false join failures — it read `—` (the
deliberate "not tied to one source" marker in `verification_log.jsonl`) as
`â€"` — and the append-only guard could **never** pass, because the working file
was read as UTF-8 while the git baseline came back as cp1252. Both are safety
properties that were silently off on one host and on on the other. Worse, three
tools *wrote* without an encoding, so the mangling was persisted into the data
(see the `â€"` still embedded in a Lumbee row).

**A check that fails for an environmental reason trains people to ignore the
gate.** Ten permanent FAILs are indistinguishable from noise.

## Do not

- Do not treat `directory_url` liveness as re-verified unless `last_checked` says 2026-08-27.
- Do not project a Counter onto a hardcoded display vocabulary with
  `{k: c[k] for k in ORDER if c[k]}` — that silently drops any new value.
  `build_summary.ordered()` appends unknown keys instead. Vocabulary drift must
  surface as a new key, never as a missing count.
- Do not promote a Lead to coverage without obtaining the roster.
- Do not merge records across sources on name alone; `schema/source_record.schema.json` is the binding contract for
  the per-source assertion layer (one row per business *appearance in one source*),
  and `schema/harmonized_entity.schema.json` for the entity layer — read
  `HARMONIZED_SCHEMA.md` before writing any merge code. Identity is never a boolean;
  spouse/operated_by never map to ownership; conflicts persist rather than overwrite.
