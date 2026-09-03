# Tribal newsletter & tribal media survey — 2026-08-27

Reconnaissance of tribal newsletters/newspapers as an additional evidence
channel: could their content become a dataset, and do they carry lists of
tribal businesses, awards to them, or certification coverage? Raw per-outlet
evidence (42 outlets, honest negatives included) is in
`newsletter_survey_2026-08-27.jsonl`.

**Evidence grade:** search-only, same as the Wave 5.1 sweep — page fetches are
blocked by the build environment, so every claim rests on titles/URLs/snippets
that literally appeared in search results. Nothing here enters `sources.jsonl`
until it passes the Phase 3 bounded protocol with page-level verification.

## What newsletters actually yield (three recurring record types)

1. **Business spotlight columns** naming a business + owner + tribal
   citizenship ("Tulalip tribal member," "Diné entrepreneur," "Oglala"). Best
   evidenced: Tulalip News/syəcəb (dated 2026 articles), Navajo Times `/biz`,
   Lakota Times, Osage News (already TBD-139), Hownikan, Char-Koosta News.
   → In Cedar's model these are **Tribal Secondary source records at best**:
   journalism, not certification. `verification_basis` would be `title_only`
   (or a new `press_reported` value for taxonomy v2 to decide); a spotlight
   can corroborate an existing entity or propose a candidate, never create or
   upgrade an ownership assertion on its own.

2. **Award and certification coverage** — the standout: **Cherokee Phoenix**
   covers the Cherokee Nation TERO awards banquet across years (2015, 2021,
   2024 in results) naming category winners, plus TERO-certified expo
   coverage citing 733–802 certified firms; Red Lake Nation News ran "10
   Indian-Owned Businesses Receive TERO Awards" (2015); Lakota Times covers
   entrepreneur awards ("40 Under 40") with person + tribe + business; BBNC's
   Path to Prosperity competition names winning shareholder businesses.
   → These are **events** (unit-of-analysis rule): award/certification
   coverage attaches `certification_event_status`-style evidence to records
   and entities; it never spawns entities. Multi-year archives make this a
   genuine longitudinal event stream — e.g. answering "was this firm being
   honored as TERO-certified in 2021?"

3. **ANC shareholder-business channels** — newsletters point at the
   structured directories the registry already tracks: Calista's Storyknife
   explicitly republishes businesses from the Calivika directory (TBD-130);
   Chugach directory + Shareholder Business Assistance Program grantees
   (TBD-127); Koniag directory (TBD-129); BBNC directory + competition
   winners (TBD-125). The newsletter layer adds an **event stream on top of
   existing rows**, not new sources. Sealaska/Ahtna/Doyon newsletters yield
   little business content (consistent with wave-5 exclusions).

Negative space is real and useful: most tribal-government newsletters
(Hocak Worak, Anishinaabeg Today, DeBahJiMon, Odawa Trails, Traveling Times,
Tribal Observer, Nugguam, Squol Quol, Inaajimowin…) have deep, minable PDF
archives but showed **no** member-business content in search — they should not
be scraped on spec.

## Dataset assessment

- Distribution across 42 outlets: 9 high / 9 medium / 21 low / 3 none.
- The highest-value near-term dataset is **not** the newsletters themselves
  but what the cross-outlet search surfaced alongside them: **dated, versioned
  TERO certified-vendor PDF lists** (Poarch `TERO_Certified_Business_List_01.20.2026.pdf`,
  EBCI April–May 2026 vendor list) — already registry rows (TBD-037, TBD-043);
  the survey adds fresh dated-edition evidence consistent with their wave-5
  cadence findings.
- A newsletter-derived dataset is viable as a **second check** in exactly the
  user-intended sense: spotlights corroborate existence/identity framing of
  businesses found in primary lists; award coverage adds dated events;
  archives (Char-Koosta 1956–2014 searchable; Umatilla Journal OCR'd on
  archive.org; Seminole Tribune PDFs to 2000) support historical validation.

## Candidates for the Phase 3 protocol (new source rows, pending fetch verification)

| Candidate | Nation (crosswalk id) | Would-be class | Record types |
|---|---|---|---|
| Cherokee Phoenix TERO awards/expo coverage | bia:cherokee-nation | Tribal Secondary | business_awards, certification events |
| Tulalip News / syəcəb business features | bia:tulalip-tribes | Tribal Secondary | spotlight_column |
| Navajo Times `/biz` section | bia:navajo-nation | Tribal Secondary | spotlight_column |
| Lakota Times business/awards coverage | bia:oglala-sioux (+ bia:rosebud-sioux) | Tribal Secondary | spotlight_column, business_awards |
| Char-Koosta News (incl. member-business "virtual mall" nonprofit it covered) | bia:salish-kootenai | Tribal Secondary | spotlight_column |
| Red Lake Nation News business section | bia:red-lake | Tribal Secondary | business_awards, certification events |
| Hownikan member-venture features | bia:citizen-potawatomi | Tribal Secondary | spotlight_column |
| Seminole Tribune archive | (Seminole Tribe of Florida — not yet in crosswalk; wave-5 excluded the tribe's procurement channel, not its press) | Tribal Secondary | spotlight_column |
| Sault Tribe Member Business Directory page (saulttribe.com/newsroom/2055-stmbd) | bia:sault-ste-marie | Tribal Primary or Secondary (verify who registers/verifies) | directory_list — distinct from TBD-016 Sault Tribe Thrive |
| Confederated Umatilla Journal (OCR archive) / Spilyay Tymoo business category | bia:umatilla / bia:warm-springs | Tribal Secondary | spotlight_column (historical) |
| BBNC Path to Prosperity winners; Chugach SBAP grantees; Doyon Shareholder Spotlight | — (ANC; attach to TBD-125/127; Doyon was wave-5 excluded — spotlight is individual-focused, low yield) | Cross-Reference event streams | business_awards |

Enumeration frames found for later: goia.wa.gov's directory of Washington
tribal newspapers; the Adam Matthew "Indigenous Newspapers in North America"
licensed corpus (1970–2016) for historical mining (licensed access = needs
human).

## Guardrails that bind any newsletter ingestion

- Newsletters are **non-certifying**: `identity_mix` is effectively always
  "Yes", the caveat travels with every record, and a spotlight or award
  never creates or upgrades an ownership assertion (matching rules 2/4).
- **Publication boundary / personal-vs-business:** spotlights are stories
  about people. Only the business form of names/contacts is ingestible;
  personal detail in profiles is not, however public the article. This
  channel makes FIELD_CLASSIFICATION.md (pre-Phase-5 gate) more important,
  not less.
- Awards and certification coverage are **events** attached to records and
  entities — they never spawn entities (unit-of-analysis rule).
- Respectful acquisition applies to tribal press like any tribal site;
  licensed archives (Newspapers.com, Adam Matthew) and membership-gated
  papers (Turtle Mountain Times) are needs-human, never scraped around.

## Not done here

No `sources.jsonl` rows were added, no statuses changed, and no
verification-log entries were written: this is reconnaissance research, not
source-evidence alteration. Each candidate above still needs the Phase 3
sequence (official-site check → fetch verification → new TBD id in house
style) once egress allows.
