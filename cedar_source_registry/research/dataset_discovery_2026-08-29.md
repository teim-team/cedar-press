# Dataset discovery — 2026-08-29 round: federal procurement identifiability

Daily discovery round, frame: where Native-owned businesses are identifiable
in federal procurement data. 10 sources in
`dataset_discovery_2026-08-29.jsonl` (search-only evidence grade).

## The architecture, in one paragraph

Everything flows from **SAM.gov self-representation**: entities self-report
socio-economic status (American Indian Owned; Tribally Owned Firm; ANC Owned;
NHO Owned) at registration, those flags propagate to FPDS contract actions,
and surface in USAspending, DSBS, and the IHS/BIA Buy Indian dashboards.
Only 8(a)/HUBZone/WOSB/VOSB status is SBA-VERIFIED — every Native ownership
flag in this layer is self-certified (GAO-15-588: self-certify + challenge).
Identity discipline: these flags are cross-reference evidence, never
verification of Native ownership, and never tribal citizenship.

## Best acquisition paths

- **USAspending API/bulk** — `recipient_type_names` separately filters
  'American Indian Owned Business', 'Tribally Owned Firm', 'Alaskan Native
  Corporation Owned Firm', 'Native Hawaiian Organization Owned Firm':
  full award-level enumeration by category, bulk CSV, no auth. The single
  strongest federal path, and the natural empirical base for the owner's
  Buy Indian Act research.
- **SAM Entity Management Public Extracts** — monthly full file + daily
  deltas incl. Reps & Certs; the upstream registry itself. Verify which
  socio-economic fields survive the public extract tier (layout PDF at
  open.gsa.gov).
- **DSBS** — Tribally/ANC/NHO/Other-Native ownership filters crossable with
  the SBA-verified 8(a) flag = the practical entity-owned-8(a) enumeration
  (the GAO-12-84 methodology); search-only, no official export.
- **IHS + BIA Buy Indian pages** — SAM-derived Native-vendor dashboards,
  IEE self-certification Representation forms (IEE = 51%+ Indian-owned),
  BISAM set-aside announcements. Dashboards are views, not adjudicated
  IEE rosters — no verified IEE roster exists anywhere (GAO-15-588).

## Honest negatives

No standalone public 8(a) roster splitting entity-owned vs individual
(CRS R48190 documents the rules; DSBS crossing is the workaround). DOD
Indian Incentive Program has no public subcontractor list (rebates flow
privately prime -> contracting officer).

## Next step (owner call or later round)

Promote USAspending + SAM extracts + DSBS as Cross-Reference rows with
self-certification do_not_infer guardrails; they also power the "federal
policy -> entrepreneurship" article angle directly.
