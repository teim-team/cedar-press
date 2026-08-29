#!/usr/bin/env python3
"""
16c_copy_funding_inputs.py
Copy every input the Dataset-3 reconciliation relied on into
Cedar Press/data/raw/external/federal_funding/ and write _SOURCE_MANIFEST.csv.
Source trees are read-only; nothing under dissertation/ is modified.
"""
import csv, os, shutil, hashlib, datetime
from pathlib import Path

CEDAR = str(Path(__file__).resolve().parent.parent)
DISS  = r"C:\Users\esm247\Desktop\dissertation\data\tribal_federal_spending"
DEST  = os.path.join(CEDAR, "data", "raw", "external", "federal_funding")
LOG   = os.path.join(CEDAR, "logs", "16_federal_funding_recon_2026-08-05.log")
os.makedirs(DEST, exist_ok=True)
_lf = open(LOG, "a", encoding="utf-8")
def log(m):
    line = f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}][COPY] {m}"
    print(line, flush=True); _lf.write(line + "\n"); _lf.flush()

# (original_path, lineage, role, copy?)  -- lineage A already lives inside Cedar
# Press (Federal Spending/), so it is manifested in place rather than duplicated.
ITEMS = [
    (os.path.join(CEDAR, "Federal Spending", "raw",
     "Assistance_PrimeTransactions_2023-04-09_H19M53S53_1.csv"), "A",
     "raw USAspending assistance prime transactions (shared root of BOTH lineages)", False),
    (os.path.join(CEDAR, "Federal Spending", "clean",
     "fed_funding_data_clean_corrtd.dta"), "A", "hand-cleaned tribe-attributed panel (corrected)", False),
    (os.path.join(CEDAR, "Federal Spending", "clean",
     "fed_funding_data_clean.dta"), "A", "hand-cleaned tribe-attributed panel (original)", False),
    (os.path.join(CEDAR, "Federal Spending", "code",
     "fed_funding_do_file_corrtd.do"), "A", "identification do-file (corrected)", False),
    (os.path.join(CEDAR, "Federal Spending", "code",
     "fed_funding_do_file.do"), "A", "identification do-file (original)", False),
    (os.path.join(DISS, "clean", "award_level_panel_research_ready.csv"), "B",
     "pre-dedup award panel (needed to verify the $67B claim)", True),
    (os.path.join(DISS, "clean", "award_level_panel_research_ready_deduped.csv"), "B",
     "deduped award panel (lineage B canonical)", True),
    (os.path.join(DISS, "clean", "award_level_panel_research_ready_deduped_dropped_rows.csv"), "B",
     "dedup audit trail", True),
    (os.path.join(DISS, "clean", "tribe_year_research_ready_wide_deduped.csv"), "B",
     "tribe-year wide panel (lineage B shipped panel)", True),
    (os.path.join(DISS, "clean", "master_tribal_spending_panel.csv"), "B",
     "tribe/uei/fiscal-year panel (only lineage B file with true fiscal_year)", True),
    (os.path.join(DISS, "dedupe_award_panel.py"), "B", "dedup script", True),
    (os.path.join(DISS, "dedupe_award_panel.log"), "B", "dedup run log", True),
    (os.path.join(DISS, "build_research_ready_panel.py"), "B", "award panel build script", True),
    (os.path.join(DISS, "integrate_grants_to_panel.py"), "B",
     "script that folds the assistance CSV into lineage B", True),
    (os.path.join(DISS, "RESEARCH_READY_DATA_DICTIONARY.md"), "B", "data dictionary", True),
    (os.path.join(DISS, "DATA_GOVERNANCE_2026-04-29.md"), "B", "governance doc", True),
    (os.path.join(DISS, "CHANGELOG.md"), "B", "changelog (carries the $67B claim)", True),
]

def count_rows(p):
    if not p.lower().endswith(".csv"): return ""
    n = 0
    with open(p, encoding="utf-8", errors="replace", newline="") as f:
        rd = csv.reader(f)
        try: next(rd)
        except StopIteration: return 0
        for _ in rd: n += 1
    return n

def md5(p, cap=None):
    h = hashlib.md5()
    with open(p, "rb") as f:
        while True:
            b = f.read(1 << 22)
            if not b: break
            h.update(b)
    return h.hexdigest()

rows = []
today = datetime.date.today().isoformat()
for src, lin, role, docopy in ITEMS:
    if not os.path.exists(src):
        log(f"MISSING (not copied): {src}"); continue
    dst = os.path.join(DEST, os.path.basename(src)) if docopy else src
    if docopy:
        shutil.copy2(src, dst)
        log(f"copied -> {os.path.basename(dst)}  ({os.path.getsize(src)/1e6:.1f} MB)")
    else:
        log(f"in place (not duplicated): {src}")
    n = count_rows(src)
    rows.append({
        "file": os.path.basename(src), "lineage": lin, "role": role,
        "original_path": src,
        "cedar_path": dst,
        "copied_into_cedar": "yes" if docopy else "no (already inside Cedar Press)",
        "bytes": os.path.getsize(src), "rows_excl_header": n,
        "source_mtime": datetime.datetime.fromtimestamp(os.path.getmtime(src)).isoformat(timespec="seconds"),
        "md5": md5(src) if os.path.getsize(src) < 200_000_000 else "(skipped: >200MB)",
        "copied_date": today,
    })

man = os.path.join(DEST, "_SOURCE_MANIFEST_federal_funding.csv")
with open(man, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
log(f"wrote manifest {man} ({len(rows)} entries)")
