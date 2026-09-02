#!/usr/bin/env python3
"""
206_profile_prime_vocabulary_seams.py — READ-ONLY.

WHY THIS EXISTS
---------------
`docs/CICD_BENCHMARK.md` finding INTERNAL-05 (severity HIGH) recorded that
`prime_contracts.extent_competed` holds TWO VOCABULARIES in one column:
raw FPDS single-letter codes on BGOV-era rows and rendered description tags on
archive-era rows. A filter on either vocabulary therefore selects an ERA, not a
competition status — the same failure shape as the set-aside definition change
that AGENTS.md records as nearly corrupting the flagship statistic.

The obvious next question is *"where else?"*. This script answers it by
measuring, for every categorical column on `prime_contracts.csv`, whether the
two eras speak the same vocabulary. It writes NOTHING to `data/clean` and makes
NO network requests.

WHAT AN ERA IS HERE
-------------------
`source_file` is the seam marker and it survives the 2026-08-12 merge by design
(`AGENTS.md`: "source_file is not rewritten on any row, so the seam stays
visible in the data"). `master prime file.dta` is the BGOV era; every
`FY####_All_Contracts_Full_########.zip` is the USAspending award-archive era.

WHAT IT REPORTS
---------------
Per column, per era: cardinality, the value set, and — the number that matters —
the share of each era's rows carrying a value the OTHER era never uses. A column
where both eras use the same words is CLEAN and is reported by name; this
project counts what it drops, by name.

    py -3 code/206_profile_prime_vocabulary_seams.py

Outputs `review/prime_vocabulary_seam_profile_<date>.json` and a printed table.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIME = ROOT / "data" / "clean" / "prime_contracts.csv"
OUT = ROOT / "review" / f"prime_vocabulary_seam_profile_{date.today().isoformat()}.json"

csv.field_size_limit(10 ** 7)

BGOV_SOURCE = "master prime file.dta"

# Every column that carries a VOCABULARY rather than a number, an identifier or
# free text. Identifiers (contract_number, uei, cage) and names (awardee_name)
# are excluded because they are not drawn from a controlled list, so "the two
# eras use different values" is expected and meaningless there.
CATEGORICAL = [
    "setaside",
    "reported_8a",
    "reported_buy_indian",
    "reported_indian_business",
    "reported_native_preference",
    "setaside_reported",
    "extent_competed",
    "funding_agency",
    "sector",
    "supersector",
    "defense",
    "recipient_state_code",
    "place_of_perform_state",
    "inflation_base_year",
    "pre_2000_flag",
    "attribution_method",
    "confidence_tier",
    "attributed_flag",
    "source_authority",
    "ruling_status",
]

# Columns whose cardinality is legitimately large; report the seam metric but
# only the head of the value list.
HIGH_CARD = {"funding_agency", "sector", "recipient_state_code",
             "place_of_perform_state", "attribution_method"}


def shape_of(v: str) -> str:
    """Classify an extent_competed token WITHOUT assigning it a meaning."""
    s = (v or "").strip()
    if not s:
        return "blank"
    if len(s) == 1 and s.isalpha():
        return "single_letter_code"
    if s.isalpha() and len(s) <= 3 and s.isupper() and " " not in s:
        return "short_alpha_code"
    return "rendered_label"


def main() -> int:
    if not PRIME.exists():
        print(f"MISSING: {PRIME}", file=sys.stderr)
        return 2

    st = PRIME.stat()
    print(f"reading {PRIME}")
    print(f"  bytes {st.st_size:,}  mtime "
          f"{datetime.fromtimestamp(st.st_mtime).isoformat(timespec='seconds')}")

    # per column -> per era -> Counter(value)
    vocab: dict[str, dict[str, Counter]] = {
        c: defaultdict(Counter) for c in CATEGORICAL}
    era_rows: Counter = Counter()
    era_dollars: dict[str, float] = defaultdict(float)
    ec_shape: dict[str, Counter] = defaultdict(Counter)
    ec_by_source: dict[str, Counter] = defaultdict(Counter)
    ec_shape_dollars: dict[tuple, float] = defaultdict(float)
    source_files: Counter = Counter()
    missing_cols: list[str] = []

    with PRIME.open(newline="", encoding="utf-8") as fh:
        rdr = csv.DictReader(fh)
        header = rdr.fieldnames or []
        for c in CATEGORICAL:
            if c not in header:
                missing_cols.append(c)
        # STANDING RULE 8 (AGENTS.md): a computation aimed at a column that is
        # not there must RAISE, never print a zero.
        if missing_cols:
            print(f"FATAL: columns absent from {PRIME.name}: {missing_cols}",
                  file=sys.stderr)
            return 3
        cols = [c for c in CATEGORICAL]

        for row in rdr:
            sf = row.get("source_file", "")
            source_files[sf] += 1
            era = "BGOV" if sf == BGOV_SOURCE else "ARCHIVE"
            era_rows[era] += 1
            try:
                era_dollars[era] += float(row.get("total_obligations") or 0)
            except ValueError:
                pass
            for c in cols:
                vocab[c][era][(row.get(c) or "").strip()] += 1
            sh = shape_of(row.get("extent_competed", ""))
            ec_shape[era][sh] += 1
            ec_by_source[sf][sh] += 1
            try:
                ec_shape_dollars[(era, sh)] += float(
                    row.get("total_obligations") or 0)
            except ValueError:
                pass

    total = sum(era_rows.values())
    print(f"\nrows {total:,}   BGOV {era_rows['BGOV']:,}   "
          f"ARCHIVE {era_rows['ARCHIVE']:,}")

    report = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "file": str(PRIME.relative_to(ROOT)).replace("\\", "/"),
        "file_bytes": st.st_size,
        "file_mtime": datetime.fromtimestamp(st.st_mtime).isoformat(
            timespec="seconds"),
        "rows_total": total,
        "era_definition": {
            "BGOV": f"source_file == '{BGOV_SOURCE}'",
            "ARCHIVE": "every other source_file (USAspending award archive)",
        },
        "era_rows": dict(era_rows),
        "era_dollars_total_obligations": {k: round(v, 2)
                                          for k, v in era_dollars.items()},
        "source_files": dict(source_files.most_common()),
        "extent_competed_token_shape": {
            era: dict(cnt) for era, cnt in ec_shape.items()},
        "extent_competed_token_shape_by_source_file": {
            k: dict(v) for k, v in sorted(ec_by_source.items())},
        "extent_competed_token_shape_dollars": {
            f"{e}|{s}": round(v, 2) for (e, s), v in ec_shape_dollars.items()},
        "columns": {},
    }

    print(f"\n{'column':<32} {'BGOV n':>7} {'ARCH n':>7} {'shared':>7} "
          f"{'BGOV-only rows':>15} {'ARCH-only rows':>15}  verdict")
    print("-" * 116)

    for c in CATEGORICAL:
        b = vocab[c]["BGOV"]
        a = vocab[c]["ARCHIVE"]
        # blanks are absence, not a vocabulary choice; count them separately
        bset = {k for k in b if k != ""}
        aset = {k for k in a if k != ""}
        shared = bset & aset
        b_only = bset - aset
        a_only = aset - bset
        b_only_rows = sum(b[k] for k in b_only)
        a_only_rows = sum(a[k] for k in a_only)
        b_nonblank = sum(v for k, v in b.items() if k != "")
        a_nonblank = sum(v for k, v in a.items() if k != "")

        if not bset or not aset:
            verdict = "ONE_ERA_ONLY"
        elif not shared:
            verdict = "DISJOINT — TWO VOCABULARIES"
        elif b_only_rows == 0 and a_only_rows == 0:
            verdict = "CLEAN"
        else:
            pb = 100.0 * b_only_rows / b_nonblank if b_nonblank else 0.0
            pa = 100.0 * a_only_rows / a_nonblank if a_nonblank else 0.0
            verdict = f"PARTIAL ({pb:.1f}% / {pa:.1f}% era-only)"

        print(f"{c:<32} {len(bset):>7,} {len(aset):>7,} {len(shared):>7,} "
              f"{b_only_rows:>15,} {a_only_rows:>15,}  {verdict}")

        entry = {
            "verdict": verdict,
            "bgov_distinct": len(bset),
            "archive_distinct": len(aset),
            "shared_distinct": len(shared),
            "bgov_rows_with_era_only_value": b_only_rows,
            "archive_rows_with_era_only_value": a_only_rows,
            "bgov_blank_rows": b.get("", 0),
            "archive_blank_rows": a.get("", 0),
        }
        if c in HIGH_CARD:
            entry["bgov_only_values_head"] = sorted(b_only)[:25]
            entry["archive_only_values_head"] = sorted(a_only)[:25]
            entry["shared_values_head"] = sorted(shared)[:25]
        else:
            entry["bgov_values"] = dict(b.most_common())
            entry["archive_values"] = dict(a.most_common())
        report["columns"][c] = entry

    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".json.part")
    tmp.write_text(json.dumps(report, indent=2), encoding="utf-8")
    os.replace(tmp, OUT)
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
