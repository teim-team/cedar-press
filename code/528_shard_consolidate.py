#!/usr/bin/env python3
"""
Cedar Press - 528: SHARD CONSOLIDATION. Nine shards in, one map out.

    py -3 code/528_shard_consolidate.py            # merge + report
    py -3 code/528_shard_consolidate.py verify     # exit 1 if a shard file is malformed

WHY
---
Owner, 2026-09-01, checking: *"these shards, like, you're having them not
just see what's out there. You're having them start scraping and downloading
and consolidating too. Right?"*

Scraping and downloading: yes, each shard writes harvest jsonl. Consolidating:
NO - and that was the honest answer. Nine shards were writing nine separate
staging files and nothing merged them. Eight busy agents whose output never
reaches a customer table is the exact failure mode this project keeps
producing documents about, so the merge became a script instead of an
intention.

WHAT THIS IS NOT
----------------
This does NOT write to the spine. Whether a harvested website becomes
`entity_website` on the identity register is an assertion, and assertions go
through 510 with a source and a confidence - not through a merge utility.
This produces the consolidated map and the coverage ledger; promotion is a
separate, deliberate step with a human in it.

THE COVERAGE LEDGER IS THE POINT
--------------------------------
Owner's standing worry is that *"certain native entities might never get
updated"* - silently, forever, because nothing counts them. So the second
output is per-CLASS coverage against all 1,555 register entities: how many
have a website, how many were attempted and found to have none, and how many
no shard has touched at all. The third number is the one that matters. An
entity nobody attempted looks identical to an entity with no web presence
unless you keep them apart, and only one of those is a gap in our effort.

SAFE TO RUN MID-FLIGHT. Shards are long-running and land at different times.
A missing shard file is reported as NOT_STARTED, never an error.
"""
from __future__ import annotations

import csv
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()

REGISTER = ROOT / "data" / "spine" / "cedar_identity_register.csv"
MAP_DIR = ROOT / "data" / "staging" / "tribe_web_map"
OUT_MAP = ROOT / "data" / "staging" / "cedar_web_map.csv"
OUT_DOC = ROOT / "docs" / "SHARD_COVERAGE.md"

# Which shard owns which slice. Keeps "who was supposed to do this" answerable.
SHARDS = {
    "shard_a": "tribal governments, gaming slice 1",
    "shard_b": "tribal governments, gaming slice 2",
    "shard_c": "tribal governments, gaming slice 3",
    "shard_d": "tribal governments, gaming slice 4 + non-gaming",
    "shard_e": "Alaska Native corporations (regional, group, village)",
    "shard_f": "intertribal, urban Indian, consortia, constituency",
    "shard_g": "BIE schools, tribal colleges, CDFIs, financial institutions",
    "shard_h": "Native Hawaiian orgs, state-recognized tribes, individuals",
    "shard_i": "Native nonprofits (np_orgs, not in register)",
    # A SECOND WAVE WAS LAUNCHED AFTER THIS DICT WAS WRITTEN, AND THE DICT IS
    # THE ONLY THING THAT MAKES A SHARD VISIBLE.
    #
    # Shard K finished 228/228 Alaska Native Villages - the largest untouched
    # block in Cedar, 225 of them never touched by anyone - and wrote 1,237
    # rows with `cedar_uid` populated on every one. The coverage ledger went on
    # reporting "225 untouched" afterwards, because a hard-coded roster of nine
    # cannot see a tenth.
    #
    # That is this project's own recurring defect turned on its own scoreboard:
    # a check that silently measures a subset and reports it as the whole. Same
    # family as the export gate reading a key nothing writes, and the robots
    # parser calling an open site closed. The lesson each time is the same -
    # derive the set, do not enumerate it - so `collect()` now unions this dict
    # with whatever `shard_*.csv` files are actually on disk, and an unlisted
    # shard is reported rather than ignored.
    "shard_k": "Alaska Native Village governments",
    "shard_l": "vendor lists, unsurveyed federally recognized tribes, 1st half",
    "shard_m": "vendor lists, unsurveyed federally recognized tribes, 2nd half",
}

MAP_COLS = ["cedar_uid", "canonical_name", "entity_class", "url_type", "url",
            "http_status", "checked_date", "evidence", "shard"]


def read_csv(p: Path) -> list:
    if not p.exists():
        return []
    try:
        with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            return list(csv.DictReader(fh))
    except OSError:
        return []


def register():
    """cedar_uid -> row, plus the class histogram we score coverage against."""
    rows = read_csv(REGISTER)
    by_uid = {r["cedar_uid"]: r for r in rows if r.get("cedar_uid")}
    return by_uid, Counter(r.get("entity_class", "") for r in rows)


def collect():
    """Merge every shard map. Dedupe on (uid, url_type, url) - two shards
    finding the same URL is agreement, not duplication, and must not
    double-count in the coverage numbers."""
    seen = set()
    merged = []
    status = {}
    problems = []

    # Derive the set, do not enumerate it. Any shard_*.csv on disk is read even
    # if nobody added it to SHARDS - see the note in SHARDS above for why this
    # matters. An unlisted one is reported so the roster gets fixed too.
    found = sorted(p.stem for p in MAP_DIR.glob("shard_*.csv"))
    unlisted = [s for s in found if s not in SHARDS]
    for s in unlisted:
        problems.append(s + ".csv is on disk but not named in SHARDS - it was "
                        "still read; add it so its slice is described")
    order = list(SHARDS) + unlisted

    for shard in order:
        p = MAP_DIR / (shard + ".csv")
        if not p.exists():
            status[shard] = {"state": "NOT_STARTED", "rows": 0, "uids": 0}
            continue
        rows = read_csv(p)
        if rows and "url" not in rows[0]:
            problems.append(shard + ".csv has no `url` column - cols were "
                            + str(list(rows[0])[:8]))
            status[shard] = {"state": "MALFORMED", "rows": len(rows), "uids": 0}
            continue
        uids = set()
        kept = 0
        for r in rows:
            uid = (r.get("cedar_uid") or "").strip()
            key = (uid, (r.get("url_type") or "").strip(),
                   (r.get("url") or "").strip().rstrip("/").lower())
            if key in seen:
                continue
            seen.add(key)
            r["shard"] = shard
            merged.append(r)
            kept += 1
            if uid:
                uids.add(uid)
        status[shard] = {"state": "RUNNING_OR_DONE", "rows": kept,
                         "uids": len(uids)}
    return merged, status, problems


def main() -> int:
    verify = len(sys.argv) > 1 and sys.argv[1] == "verify"
    by_uid, class_total = register()
    merged, status, problems = collect()

    # ---- coverage per class: has a url / attempted-and-none / untouched ----
    touched = defaultdict(set)      # class -> uids any shard wrote a row for
    with_url = defaultdict(set)     # class -> uids with at least one live url
    for r in merged:
        uid = (r.get("cedar_uid") or "").strip()
        if not uid:
            continue
        cls = (by_uid.get(uid, {}).get("entity_class")
               or r.get("entity_class") or "UNKNOWN")
        touched[cls].add(uid)
        url = (r.get("url") or "").strip()
        st = str(r.get("http_status") or "").strip()
        if url and (st.startswith("2") or st == ""):
            with_url[cls].add(uid)

    if not verify:
        MAP_DIR.mkdir(parents=True, exist_ok=True)
        with OUT_MAP.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=MAP_COLS, extrasaction="ignore")
            w.writeheader()
            for r in merged:
                w.writerow(r)

        L = ["# Shard coverage - the master list, and who has touched it", "",
             "*Generated " + TODAY + " by `code/528_shard_consolidate.py`. "
             "Merged map: `data/staging/cedar_web_map.csv`. This file does "
             "NOT write to the spine - promoting a harvested website to "
             "`entity_website` is an assertion and goes through 510.*", "",
             "## Shard status", "",
             "| shard | slice | state | map rows | entities touched |",
             "|---|---|---|---:|---:|"]
        # `status` is keyed by every shard collect() considered, listed or not.
        for s in status:
            desc = SHARDS.get(s, "(not in roster - see problems)")
            st = status[s]
            L.append("| `%s` | %s | %s | %s | %s |"
                     % (s, desc, st["state"], format(st["rows"], ","),
                        format(st["uids"], ",")))

        L += ["", "## Coverage by entity class", "",
              "*`untouched` is the number that matters. An entity nobody "
              "attempted looks the same as an entity with no web presence "
              "unless you keep them apart - and only one of those is a gap "
              "in our effort.*", "",
              "| entity class | in register | with a URL | touched, none "
              "found | untouched |", "|---|---:|---:|---:|---:|"]
        tot_reg = tot_url = tot_touch = 0
        for cls, n in class_total.most_common():
            t, u = len(touched.get(cls, ())), len(with_url.get(cls, ()))
            L.append("| %s | %s | %s | %s | %s |"
                     % (cls, format(n, ","), format(u, ","),
                        format(t - u, ","), format(n - t, ",")))
            tot_reg += n
            tot_url += u
            tot_touch += t
        L.append("| **total** | **%s** | **%s** | **%s** | **%s** |"
                 % (format(tot_reg, ","), format(tot_url, ","),
                    format(tot_touch - tot_url, ","),
                    format(tot_reg - tot_touch, ",")))

        L += ["", "## URL types harvested", "", "| type | n |", "|---|---:|"]
        for k, v in Counter((r.get("url_type") or "?")
                            for r in merged).most_common():
            L.append("| %s | %s |" % (k, format(v, ",")))

        if problems:
            L += ["", "## Malformed shard output", ""]
            L += ["- " + p for p in problems]

        OUT_DOC.write_text("\n".join(L) + "\n", encoding="utf-8")

    done = sum(1 for s in status.values() if s["state"] != "NOT_STARTED")
    print("  shard consolidate  %d/%d shards reporting   %s map rows   "
          "%s entities with a URL   %d malformed"
          % (done, len(SHARDS), format(len(merged), ","),
             format(sum(len(v) for v in with_url.values()), ","),
             len(problems)))
    for p in problems:
        print("    MALFORMED  " + p)
    return 1 if (verify and problems) else 0


if __name__ == "__main__":
    sys.exit(main())
