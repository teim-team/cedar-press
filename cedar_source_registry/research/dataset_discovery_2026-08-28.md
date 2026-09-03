# Dataset discovery — 2026-08-28 round: state DBE/UCP directories

Daily discovery round, frame: state DOT Unified Certification Program (UCP)
DBE directories with Native American identifiability. 16 new sources in
`dataset_discovery_2026-08-28.jsonl` (search-only evidence grade). None
previously recorded; MN OSP, WA OMWBE, OK Commerce, MT Native American Made
were already registered and are excluded.

## Why this frame matters

Every state DOT runs a federally mandated UCP with a searchable certified-DBE
directory; DBE = >=51% owned AND controlled by socially/economically
disadvantaged individuals, with Native Americans a presumed group (per USDOT).
These are validation/cross-reference gold: state-certified with annual
renewal. A DBE flag is NEVER tribal citizenship — cross-reference use only.

## TIME-SENSITIVE: the October 2025 IFR

USDOT's Interim Final Rule (effective 2025-10-03) removed race/sex
presumptions and forced re-evaluation of ALL DBE certifications; several
states (OK, AZ, MI, NY, NV) mark listed certifications as in re-evaluation,
and ethnicity tagging may be frozen or removed going forward. **Snapshot the
export-capable directories soon** — the pre-IFR ethnicity-tagged rosters may
not be reconstructible later. This is a needs-human/priority-ingestion item.

## Registration-ready standouts (bulk export exists today)

- **New York** — the NYSUCP DBE directory is an OPEN DATASET on data.ny.gov
  (CSV/API via Socrata). Best-in-class bulk access; verify the ethnicity
  column on the dataset page.
- **North Dakota** — B2GNow "Download Entire Directory to Excel" confirmed.
- **Wisconsin** — WisDOT publishes the full UCP directory as an Excel file.
- **Alaska** — daily-updated PDFs that explicitly tag **ANC-Owned** firms
  (49 CFR 26.63(c)(2)) — the clearest Native-identity semantics of any state
  directory (corporate ANC criterion, not individual citizenship).
- **Oregon COBID** — one directory spans DBE + state MBE/WBE/ESB with
  full-directory Excel export documented.

Also captured: OK, NM, AZ (UTRACS), MT (MDT app), CA (CUCP query system),
NV, MI (MUCP), TX (TUCP), NC (EBS Vendor Directory, ethnicity-searchable,
spans DBE+MBE+HUB). Platform note: most are the same B2GNow
`SearchCertifiedDirectory.asp` engine under different domains — one adapter
covers many states.

## Adjacent finds

- **NC Commission of Indian Affairs American Indian Business Directory**
  (doa.nc.gov) — Native-specific by construction, state-maintained; verify
  inclusion criteria (likely NC-recognized tribes) before use.
- **CPUC Supplier Clearinghouse (GO 156)** — CA utility supplier diversity;
  MBE explicitly includes Native American at 51%; unaffected by the DBE IFR.
- Meta-index: USDOT's state-by-state DBE program page list
  (transportation.gov/civil-rights/...state-dot-and-dbe-program-websites).

## Next step (owner call or next round)

Promote the five bulk-export standouts to Cross-Reference rows with
do_not_infer guardrails, and prioritize snapshotting them when fetch access
opens, given the IFR clock.
