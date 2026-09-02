# Congressional correspondence logs + FOIA logs as a discovery index

*Built 2026-08-12 by `code/136_build_congressional_correspondence_and_foia_index.py`.
Every number on this page is recomputed from the CSVs by the `report`
stage; none is typed by hand.*

## Part A - the correspondence systems

Congress does not centrally report its contacts with agencies. The
agency on the receiving end does, because controlled correspondence is
how an agency proves it answered a member. So the systems were looked
for by NAME, in the agencies' own Privacy Act notices, not by hunting
for a portal - most of these systems have no public face at all.

**8 correspondence systems confirmed to exist**, each from the agency's
own Federal Register System of Records Notice, quoted verbatim with its
document number:

| agency | system | number | citation |
|---|---|---|---|
| DOI | Secretarial Controlled Correspondence File--Interior, OS--20. | - | 1999-04-23 FR document 99-10215 |
| DOT | This Notice updates the system name to DOT/FAA 852 ``Complaint Investi | FAA 852 | 2022-10-07 FR document 2022-21927 |
| DOT | Department of Transportation (DOT)/Federal Aviation Administration (FA | - | 2022-10-12 FR document 2022-22126 |
| EPA | Quill, EPA-22. | EPA-22 | 2024-08-12 FR document 2024-16354 |
| HHS | Tracking Records and Case Files for FOIA and Privacy Act Requests and  | - | 2016-03-29 FR document 2016-07060 |
| HUD | Correspondence Tracking System (CTS), HUD/ADM-09. | ADM-09 | 2024-08-05 FR document 2024-17181 |
| HUD | Correspondence Tracking System (CTS), HUD/ADM-09. | ADM-09 | 2026-01-27 FR document 2026-01558 |
| USDA | USDA/FNS-13, | FNS-13 | 2023-09-18 FR document 2023-19829 |

A SORN says the system EXISTS. It does not say any log is public, and
`log_publicly_posted` is `NOT_FOUND` on every one of them.

**249 further rows are FOIA-log evidence**: a third party asked a bureau
for its log of letters from members of Congress, and the bureau opened a
case and disposed of it. That establishes the log exists AND has already
been located and reviewed once - which is the expensive half.

`congressional_correspondence_log.csv` holds **0** rows. Nothing was
invented to fill it: no agency in scope publishes the log itself, and a
row is only written where a retrieved record names a congressional
office as a party. That absence is the finding, and it is what the
systems registry exists to make actionable.

> ### RULED OUT OF SCOPE 2026-09-02 — and the reason above is no longer the reason
>
> *Workstream GRAIN-LEGISLATION. This paragraph is kept exactly as written
> because it was true when written; what follows supersedes it.*
>
> `congressional_correspondence_log.csv` was the last C1/C2 blocker on the
> `legislation` dataset in `docs/DATASET_READINESS.md` — grain UNSTATED, no
> validated primary key, on a table with zero rows. A 0-row table cannot be
> waved through, so it was tested rather than declared, and **the test came
> back different from what this log says.**
>
> **The population changed.** Re-measured with `csv.reader` on 2026-09-02, not
> read off this page:
>
> | | when this log was written | 2026-09-02 |
> |---|---:|---:|
> | `foia_request_index.csv` rows | 9,481 | **20,102** |
> | …with `requester_is_congressional_office = Y` | 0 | **4** |
>
> So "empty by construction" is dead. `136.build_correspondence_layer` would
> emit four rows today. **The four rows are why the table is still not
> shipped.** All four are HHS Office of the Secretary FOIA-log rows carrying
> `native_related = N` and `native_basis = no_native_signal_in_this_row`:
>
> | control number | requester | subject |
> |---|---|---|
> | `2017 00237 FOIA OS` | Murray, Patty — United States Senate | correspondence from or regarding Tom Price |
> | `2018-00358-FOIA-OS` | Murray, Patty — United States Senate | communications to and from Mr. Azar as HHS General Counsel |
> | `2021-01759-FOIA-OS` | Barker, Kendal — Sen. Tuberville | abuse reports, Unaccompanied Alien Children |
> | `2022-01226-FOIA-OS` | Paul, Rand — U.S. Senate | records pertaining to FOIA request 2021-00251-FOIA-OS |
>
> HHS is swept at all only because IHS sits under it. Shipping four rows of
> non-Native noise inside an Indian-affairs collection is **worse than
> shipping nothing** — a buyer reasonably reads their presence as a claim that
> these are Indian-affairs records. And it would still not be declarable: WS4
> measured `record_id` (`FOIAREQ-{agency_code}-{foia_request_id}`) colliding
> **381 times over 9,100 distinct values** in its own source, because 136's
> PDF layout solver recovers one control number for two different requests.
>
> **RULING: out of scope, removed from the shippable table list.** Declared in
> `cedar_codebook.INTERNAL_TABLES` — the one registry
> `512_build_dataset_contracts.status_of()` reads — and ruled `INTERNAL` in
> `391_triage_unshipped_tables.VERDICTS` so the operational copy and the
> authority cannot drift. The reasoning is in
> `code/512_build_dataset_contracts.py` under `GRAIN_LEGISLATION`. Nothing was
> deleted: the file, its 24-column header and the `GRAIN_OPEN` question all
> stay where they are.
>
> **REVERSIBLE, and here is the trigger.** Delete one line from
> `INTERNAL_TABLES` the day a controlled-correspondence log is actually
> obtained — by FOIA, or by an agency posting one. Until then
> `log_publicly_posted` is `NOT_FOUND` or `NO_ONLY_RELEASED_ON_REQUEST` on all
> **257** rows of `congressional_correspondence_systems.csv`, which is the
> table that carries the finding and **does** ship.

## Part B - the FOIA index

> ⚠ **STALE COUNT, measured 2026-09-02: the file holds 20,102 rows, not
> 9,481.** Every figure in this section is the 2026-08-12 vintage and every
> one of them is now low. They are left in place — superseded numbers are
> never overwritten here — but do not quote one without re-counting the CSV.
> The per-agency and per-quality breakdowns below have not been re-derived;
> only the row total and `requester_is_congressional_office` were, for the
> scope ruling in Part A.

**9481 requests** parsed from **89 retrieved log objects**, 1993-2026.

| agency | bureau | requests |
|---|---|---:|
| DOI | Office of the Secretary | 5162 |
| BIA | Bureau of Indian Affairs | 1818 |
| IHS | Indian Health Service | 1435 |
| BIA | Assistant Secretary - Indian Affairs | 933 |
| BIA | Bureau of Indian Education | 133 |

- **196** requests seek congressional correspondence or logs of it.
- **667** seek calendars, visitor records, meeting invitations or
  Questions for the Record. Those are `EventClass.ACCESS` if they are
  ever built, and the domain model refuses to promote them.
- **453** requests name an entity that resolves to the spine, across **123**
  distinct entities.
- **3885** rows come from spreadsheet logs and **5596** from PDF logs.
  A spreadsheet has real cells, so the row boundary is GIVEN. A PDF
  log has no ruling lines and the boundary is SOLVED from geometry.
  Filter `source_format = XLSX` for rows with no geometry anywhere
  in their provenance: **52** of those seek congressional
  correspondence and **70** name a spine entity.
- **6023** rows are `parse_quality = CLEAN`; **3458** are
  `SUSPECT_BOUNDARY` - a PDF row whose description begins mid-sentence,
  which is the signature of a cell boundary that slipped and carried
  the tail of the request above it. The text is verbatim either way;
  what is not established is that the leading fragment belongs to
  this control number. Filter on CLEAN before quoting.
- **4563** rows carry `native_related = Y`; 4319 of those on bureau remit
  alone (AS-IA, BIA, BIE and IHS logs are Native by construction).

## Coverage - and what NOT_CHECKED means here

| agency | PUBLISHES | NOT_FOUND | NOT_CHECKED |
|---|---:|---:|---:|
| BIA | 35 | 9 | 0 |
| DOE | 0 | 3 | 0 |
| DOI | 28 | 17 | 0 |
| DOT | 0 | 0 | 3 |
| EPA | 0 | 3 | 0 |
| HHS | 0 | 0 | 3 |
| HUD | 1 | 1 | 1 |
| IHS | 9 | 1 | 0 |
| USDA | 0 | 0 | 2 |

`NOT_CHECKED` is not a gap in the source. HHS, USDA and DOT answer
**HTTP 403** to a full browser header set on every path tried, so those
agencies were never swept; recording them as NOT_FOUND would have
manufactured a coverage claim out of a block. HUD's index page returns
200 and LISTS its quarterly logs, and the log objects themselves refuse
the connection - the logs are published, we were refused.

## What was refused, and why

**21 retrieved objects were REFUSED rather than parsed.** A FOIA log is
a table with no ruling lines; when the geometry cannot be solved, a
mis-read row would attach one requester's words to another requester's
control number. That is fabrication, so the file is kept, named, and
left unparsed.

Two named causes:

- **Image-only scans.** Interior's Office of the Secretary monthly logs
  from January 2026 are 14 pages with one image per page and ZERO
  characters. Both pdfplumber and PyMuPDF return the empty string. A
  near-empty extraction is a scan, not an empty document. OCR is queued.
- **Scrambled or unmapped glyphs.** Some months emit their text in a
  jumbled order or in a font with no ToUnicode map, so the row content
  cannot be assembled by line at all.

## Files

- `data/clean/congressional_correspondence_systems.csv` - 257 rows
- `data/clean/congressional_correspondence_log.csv` - 0 rows
- `data/clean/foia_request_index.csv` - 9481 rows
- `data/clean/foia_discovery_targets.csv` - 122 rows
- `data/clean/correspondence_foia_source_coverage.csv` - 124 rows

Raw objects and the per-URL fetch manifest with an HTTP status on every
row: `data/raw/external/correspondence/`.

