#!/usr/bin/env python3
"""
Cedar Press 107b - backfill `source_url` into the state_gaming raw manifest.

WHY THIS IS A SEPARATE STEP
---------------------------
`code/107_pull_remaining_states.py` retrieved some files itself and knows their
URLs in code. The rest of the raw tree was retrieved by reconnaissance agents,
and their URLs live only in their transcripts. A raw tree whose provenance
depends on a transcript is not reproducible, so the URLs are transcribed here,
once, into a file that `write_manifest()` then carries forward on every run.

THE RULE THIS FILE ENFORCES
---------------------------
**`UNKNOWN` is a legitimate value and a guess is not.** A plausible-looking
wrong URL is worse than a blank, because it will be believed and re-fetched, and
whatever comes back will be treated as the same document. Anything not
reconstructible is written `UNKNOWN` and reported as such.

Input:  data/raw/external/state_gaming/_retriever_urls.csv
        (relative_path, source_url, fetched_date, note)
Output: source_url merged into _SOURCE_MANIFEST.csv, and a coverage report.
"""

import csv, sys
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
RAW = CEDAR / "data" / "raw" / "external" / "state_gaming"
URLS = RAW / "_retriever_urls.csv"
MAN = RAW / "_SOURCE_MANIFEST.csv"


def read_csv(p):
    if not Path(p).exists():
        return []
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def main():
    if not URLS.exists():
        sys.exit(f"missing {URLS.relative_to(CEDAR)} - nothing to merge")
    supplied = {r["relative_path"].strip().replace("\\", "/"): r
                for r in read_csv(URLS) if r.get("relative_path")}
    man = read_csv(MAN)
    if not man:
        sys.exit("run code/107_pull_remaining_states.py first")

    filled = kept = unknown = missing = 0
    for row in man:
        rel = row["relative_path"]
        s = supplied.get(rel)
        if s:
            u = (s.get("source_url") or "").strip()
            if u and u.upper() != "UNKNOWN":
                if not row.get("source_url"):
                    filled += 1
                row["source_url"] = u
                if s.get("fetched_date"):
                    row["fetched_date"] = s["fetched_date"].strip()
                if s.get("note"):
                    row["retrieved_by"] = (row.get("retrieved_by", "") +
                                           f" ({s['note'].strip()})").strip()
                continue
            # An explicit UNKNOWN is recorded AS "UNKNOWN", not left blank -
            # blank reads as "nobody has looked yet", which is false here.
            row["source_url"] = "UNKNOWN"
            unknown += 1
            continue
        if row.get("source_url"):
            kept += 1
        else:
            missing += 1

    flds = list(man[0].keys())
    with open(MAN, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=flds, extrasaction="ignore")
        w.writeheader()
        w.writerows(man)

    on_disk = {p.relative_to(RAW).as_posix() for p in RAW.rglob("*")
               if p.is_file() and not p.name.startswith("_")}
    orphan = sorted(set(supplied) - on_disk)

    print(f"  {MAN.relative_to(CEDAR)}: {len(man)} files")
    print(f"    {filled:>5} source_url filled from the retriever list")
    print(f"    {kept:>5} already had one (retrieved by script 107 itself)")
    print(f"    {unknown:>5} explicitly UNKNOWN - reconstructible by nobody")
    print(f"    {missing:>5} still blank - NOT COVERED by the retriever list")
    if orphan:
        print(f"    {len(orphan)} listed URLs have no file on disk: "
              f"{', '.join(orphan[:5])}")
    if missing:
        print("\n  Files still blank:")
        for r in man:
            if not r.get("source_url"):
                print(f"    {r['relative_path']}")


if __name__ == "__main__":
    main()
