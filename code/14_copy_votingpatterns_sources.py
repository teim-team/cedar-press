"""
14_copy_votingpatterns_sources.py
Cedar Press Dataset 10 (Native Bills & Congressional Votes) -- STAGE 0.

Copies every source file this build depends on OUT of C:\\Users\\esm247\\Desktop\\votingpatterns
(read-only) INTO Cedar Press\\data\\raw\\external\\votingpatterns\\ and writes a source manifest
(original path, bytes, sha256-short, row count, copied date).

All downstream Cedar Press build steps read ONLY from the local copies.

PRIMARY SOURCES (upstream provenance, not paths):
  - Voteview (Lewis, Poole, Rosenthal, et al.), voteview.com/data: HSall_rollcalls, HSall_votes,
    HSall_members. Congresses 1-119.
  - Congress.gov API v3 (Library of Congress): bill metadata, Congresses 103-119.
"""
import csv
import hashlib
import os
import shutil
import sys
from datetime import date
from pathlib import Path

SRC = Path(r"C:\Users\esm247\Desktop\votingpatterns")
DEST_ROOT = Path(__file__).resolve().parent.parent
DEST = DEST_ROOT / "data" / "raw" / "external" / "votingpatterns"
DEST.mkdir(parents=True, exist_ok=True)

FILES = [
    # (relative source path, primary source label)
    ("data/processed/rollcalls_tribal.csv", "Voteview HSall/Hall rollcalls, House, keyword+landmark classified"),
    ("data/processed/rollcalls_all_tribal_classified.csv", "Voteview House rollcalls, pro-tribal + procedural-opposition"),
    ("data/processed/rollcalls_senate_tribal.csv", "Voteview HSall rollcalls, Senate, keyword classified"),
    ("data/processed/rollcalls_anti_tribal.csv", "Voteview House rollcalls, anti-tribal classified"),
    ("data/processed/anti_tribal_votes_expanded.csv", "Voteview House rollcalls, anti-tribal 8-strategy expansion"),
    ("data/processed/tribal_votes_adjudicated.csv", "Two-coder adjudicated vote direction"),
    ("data/processed/tribal_votes_coder_A.csv", "Coder A independent direction coding"),
    ("data/processed/tribal_votes_coder_B.csv", "Coder B independent direction coding"),
    ("data/processed/anti_tribal_votes_adjudicated.csv", "Two-coder adjudicated anti-tribal set"),
    ("data/processed/member_tribal_scores_v2.csv", "House member x congress tribal scores"),
    ("data/processed/member_tribal_scores_by_votetype.csv", "House member scores split by vote type"),
    ("data/processed/senate_member_tribal_scores.csv", "Senate member x congress tribal scores"),
    ("data/processed/tribal_bill_intros.csv", "Congress.gov API v3 bill metadata, tribal-classified subset"),
    ("data/processed/all_bill_intros.csv", "Congress.gov API v3 bill metadata, full hr/s/hjres/sjres universe 103-119"),
    ("data/processed/member_bill_intros_panel.csv", "Member x congress sponsorship counts"),
    ("data/processed/intercoder_report.txt", "Intercoder reliability report, pro-tribal direction"),
    ("data/processed/intercoder_report_anti_tribal.txt", "Intercoder reliability report, anti-tribal set"),
    ("data/processed/intercoder_expanded_report.txt", "Anti-tribal expansion methodology report"),
    ("data/raw/voteview/HSall_rollcalls.csv", "Voteview, voteview.com/data, all rollcalls both chambers"),
    ("data/raw/voteview/HSall_members.csv", "Voteview, voteview.com/data, member roster w/ bioguide_id"),
    ("data/raw/voteview/HSall_votes.csv", "Voteview, voteview.com/data, member-level cast codes"),
]


def sha256_short(p: Path, nbytes=None) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            b = f.read(1 << 22)
            if not b:
                break
            h.update(b)
    return h.hexdigest()[:16]


def count_rows(p: Path) -> str:
    if p.suffix.lower() != ".csv":
        return ""
    n = 0
    with open(p, "r", encoding="utf-8", errors="replace", newline="") as f:
        for _ in f:
            n += 1
    return str(max(n - 1, 0))


def main():
    today = date.today().isoformat()
    rows = []
    for rel, label in FILES:
        s = SRC / rel
        if not s.exists():
            print(f"  MISSING (skipped): {s}")
            rows.append({
                "dest_file": "", "original_path": str(s), "primary_source": label,
                "bytes": "", "sha256_16": "", "row_count": "", "copied_date": today,
                "status": "MISSING_AT_SOURCE",
            })
            continue
        d = DEST / s.name
        if d.exists() and d.stat().st_size == s.stat().st_size:
            print(f"  already present, size match: {s.name}")
        else:
            print(f"  copying {s.name} ({s.stat().st_size/1e6:.1f} MB) ...", flush=True)
            shutil.copy2(s, d)
        rows.append({
            "dest_file": d.name,
            "original_path": str(s),
            "primary_source": label,
            "bytes": d.stat().st_size,
            "sha256_16": sha256_short(d),
            "row_count": count_rows(d),
            "copied_date": today,
            "status": "OK",
        })
        print(f"    -> {d.name} rows={rows[-1]['row_count']} sha={rows[-1]['sha256_16']}")

    man = DEST / "SOURCE_MANIFEST.csv"
    with open(man, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\nManifest written: {man}  ({len(rows)} entries)")


if __name__ == "__main__":
    main()
