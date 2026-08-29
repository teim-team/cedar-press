#!/usr/bin/env python3
"""
23c_copy_directory_core_sources.py -- Cedar Press Gaming dataset, Phase 1 Step C.

Stages the directory-core inputs into data/raw/external/gaming/directory_core/
so the gaming build is self-contained (Cedar Press rule: nothing reads outside
the folder at runtime).

votingpatterns/ and dissertation/ are READ-ONLY. This script copies OUT of them
and never writes into them.

Each copied file gets a manifest row recording its origin path, mtime, size,
sha256, and -- critically -- a `value_class` note stating whether the numbers it
carries are REPORTED, PAYMENTS-DERIVED, REVERSE-ENGINEERED or MODELLED. That
assessment is written from the source projects' own READMEs and audit reports,
which are copied alongside the data so the claim is checkable.
"""
import os, csv, io, shutil, hashlib, datetime

BASE = r"C:\Users\esm247\Desktop\Cedar Press"
DEST = os.path.join(BASE, "data", "raw", "external", "gaming", "directory_core")
MAN  = os.path.join(BASE, "data", "raw", "external", "gaming", "_SOURCE_MANIFEST.csv")
os.makedirs(DEST, exist_ok=True)

VP = r"C:\Users\esm247\Desktop\votingpatterns\data\processed"
DI = r"C:\Users\esm247\Desktop\dissertation\data\indiangaming"
COPIED = datetime.date(2026, 8, 5).isoformat()

buf = io.StringIO()
def log(*a):
    s = " ".join(str(x) for x in a); print(s); buf.write(s + "\n")

# (src, description, value_class)
SOURCES = [
 (os.path.join(VP, "canonical_casino_addresses_FINAL.csv"),
  "Casino identity + address + coordinates, 411 records, hand-curated in votingpatterns",
  "REPORTED (operator websites / state commissions). No capacity or revenue fields. "
  "zip and county_fips stored as integers -- leading zeros already destroyed at source."),
 (os.path.join(VP, "canonical_casino_addresses_supplement.csv"),
  "Same 411 records plus per-record `source` URL and `notes`",
  "REPORTED. ~93% of address/coordinate provenance is the casino's own marketing website; "
  "no regulator source. Self-collected and unaudited."),
 (os.path.join(VP, "bia_compact_properties_geocoded_v2.csv"),
  "Property/address strings extracted from BIA compact PDFs, geocoded, 766 rows",
  "REPORTED text extraction; geocoding is DERIVED and mostly absent -- "
  "geocoder_match_quality=No_Match on 590 of 766 rows, and pairing_uncertain=1 on 231."),
 (os.path.join(VP, "per_property_gaming_revenue_FINAL_v3_audited.csv"),
  "Per-property implied gaming revenue panel, 512 rows, 1994-2026",
  "MIXED AND MOSTLY NOT REPORTED. Only the 63 ct_slot_win_annual rows are a published "
  "revenue figure. ~410 rows are a compact-rate inversion of a payment (OK x20, CT x4, "
  "MI x50, OR x16.67, NY x4, WA/WI per-compact). 22 rows are IMPLAN model output. "
  "data_quality_tier_audited='tier2A_agent_verified_real' certifies the PAYMENT was "
  "verified, NOT that revenue was reported -- do not read it as reported GGR."),
 (os.path.join(VP, "per_property_gaming_revenue_FINAL_v3_README.md"),
  "README for the per-property revenue panel (states the rate inversions)", "documentation"),
 (os.path.join(VP, "per_property_gaming_revenue_FINAL_v2_README.md"),
  "README for the v2 vintage -- states the inversion rates verbatim", "documentation"),
 (os.path.join(VP, "published_tribal_gaming_revenue_v3_audited.csv"),
  "State-published tribal gaming payments/fees, 530 rows",
  "value_usd_millions is a PAYMENT OR FEE, not gaming revenue, except ct_slot_win_annual. "
  "verification_status: agent_verified 442 (source PDF/CSV archived), "
  "hand_written_estimate 83 (data_archived_at='not_archived'), agent_state_aggregate 5."),
 (os.path.join(VP, "published_revenue_audit_REPORT.md"),
  "Audit report for the published-revenue file; documents removal of 19 fabricated AZ "
  "per-tribe rows and enumerates the unverified hand-written estimates", "documentation"),
 (os.path.join(VP, "per_tribe_gaming_revenue_reverse_engineered.csv"),
  "Per-tribe payments with AIANNH crosswalk, 611 rows",
  "value_millions is the published PAYMENT. implied_GGR_millions is filled on only "
  "17 of 611 rows (method='rate_inverse'). `method` conflates derivation with a join "
  "failure: 'no_aiannh_match' (239 rows) is a crosswalk miss, not a value basis."),
 (os.path.join(DI, "Indian Gaming Dataset.xlsx"),
  "Casino opening/closing event history, hand-coded with per-event source URLs",
  "REPORTED. Every opening/closing date carries its own source URL column and a "
  "'last reviewed' date. Best-documented date provenance of any input here."),
 (os.path.join(DI, "tribal_casino_panel.dta"),
  "Casino City Press gaming-property panel, 13,198 obs x 75 vars, 43 waves 2001-2023",
  "REPORTED capacity (slots, casino sq ft, table games, rooms, employees, parking) as "
  "published by Casino City Press. Integer 0 stands in for missing -- 0 must be read as "
  "unknown, never as 'zero slots'. Contains NO revenue column."),
 (os.path.join(DI, "Tribal Property List.xlsx"),
  "Casino City property roster, 612 rows, with Casino City ID and open/close dates",
  "REPORTED. Supplies the Casino City ID join key. No capacity, no revenue."),
]

rows = []
for src, desc, vclass in SOURCES:
    name = os.path.basename(src)
    dst = os.path.join(DEST, name)
    if not os.path.exists(src):
        log(f"MISSING  {src}")
        rows.append(dict(local_file="directory_core/" + name, source_url=src,
                         description=desc, http_status="MISSING", bytes=0, sha256="",
                         fetched_date=COPIED, note="source file not found"))
        continue
    shutil.copy2(src, dst)
    b = open(dst, "rb").read()
    log(f"COPIED   {name:<52} {len(b):>12,} bytes")
    rows.append(dict(local_file="directory_core/" + name, source_url=src,
                     description=desc, http_status="COPIED", bytes=len(b),
                     sha256=hashlib.sha256(b).hexdigest(), fetched_date=COPIED,
                     note=vclass))

fields = ["local_file", "source_url", "description", "http_status", "bytes",
          "sha256", "fetched_date", "note"]
keep = []
if os.path.exists(MAN):
    have = {r["local_file"] for r in rows}
    keep = [r for r in csv.DictReader(open(MAN, encoding="utf-8"))
            if r.get("local_file") not in have]
with open(MAN, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    for r in keep + rows: w.writerow(r)
log(f"\nmanifest rows: {len(keep) + len(rows)}  ->  {MAN}")

with open(os.path.join(BASE, "logs", "23_gaming_2026-08-05.log"), "a",
          encoding="utf-8") as fh:
    fh.write("\n\n" + "=" * 78 + "\n23c_copy_directory_core_sources.py\n"
             + "=" * 78 + "\n" + buf.getvalue())
