#!/usr/bin/env python3
"""
Cedar Press - 941: REFRESH ONE COLLECTION'S CODEBOOK FRAGMENT FROM THE DATA.

    py -3 code/941_refresh_codebook_fragment.py list
    py -3 code/941_refresh_codebook_fragment.py drift            # measure only
    py -3 code/941_refresh_codebook_fragment.py <collection> --apply
    py -3 code/941_refresh_codebook_fragment.py verify           # exit 1 on a
                                                                 # RETIRED name

WHY THIS EXISTS AND WHY IT IS NOT SCRIPT 41
-------------------------------------------
`41_build_codebooks.py` measures a codebook from the file it documents, which
is the right rule, and it is on `cedar_pipeline.NEVER_RUN` because it writes
`codebook_master.csv` in 'w' mode from a hardcoded DATASETS dict and DELETES
21 of the 43 blocks registered since. So the correct behaviour and the safe
behaviour live in the same file and cannot both be had by running it.

This does what `cedar_register_codebook.py` did for the four orphaned gaming
codebooks: it writes ONE FRAGMENT, from the live header, and never touches the
master. 41's `access_tier` and `DESCRIPTIONS` are IMPORTED, not copied - a
second copy of the DUNS rule is a second place for it to go stale.

WHAT WENT STALE, MEASURED 2026-09-02
------------------------------------
15 of 41's 17 collections have drifted from the files they document. The one
that is not merely incomplete but WRONG is `03_federal_funding`:

    documented, and gone from the data ..... tribe_id_scheme
    live, and documented nowhere ........... 25 columns, including
                                             attribution_status,
                                             attribution_basis and cedar_uid

`tribe_id` and `tribe_id_scheme` were retired on 2026-09-01 by
`code/843_retire_cicd_scheme.py`, and `tribe_id_scheme_resolved` /
`_resolved_basis` were renamed to `attribution_status` / `attribution_basis`.
A codebook that still lists a column a buyer cannot find in the file is worse
than one that is merely short.

MEASURED BY STREAMING
---------------------
`cedar_register_codebook.profile()` reads the whole table into memory. The
assistance table is 659 MB and the prime table is larger; this streams with
`csv.reader` and holds one row at a time, so it works on the big collections
that most need it.
"""
from __future__ import annotations

import ast
import csv
import importlib.util
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))
CLEAN = ROOT / "data" / "clean"
FRAG = CLEAN / "codebook"
DOCS = ROOT / "docs" / "codebooks"
TODAY = date.today().isoformat()
csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))

FIELDS = ["dataset", "variable", "type", "units", "pct_filled", "n_rows",
          "published", "access_tier", "description", "generated"]

# Names retired on 2026-09-01. A codebook that still lists one of these is
# documenting a column the buyer will not find. `verify` fails on it.
RETIRED = {"tribe_id_scheme", "same_as_legacy_cicd",
           "tribe_id_scheme_resolved", "tribe_id_scheme_resolved_basis"}
# ...but only where the retirement actually applies. `tribe_id` is alive and
# correct in a dozen other tables; it was removed from exactly two files.
RETIRED_IN = {"federal_funding_transactions.csv",
              "federal_funding_tribe_year_panel.csv"}
RETIRED_SCOPED = {"tribe_id"}


def load41():
    spec = importlib.util.spec_from_file_location(
        "cedar41", ROOT / "code" / "41_build_codebooks.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def datasets_map():
    """41's DATASETS dict, read by AST so nothing in 41 is executed at import
    time by accident. 41 is NEVER_RUN; reading its data is not running it."""
    src = (ROOT / "code" / "41_build_codebooks.py").read_text(
        encoding="utf-8", errors="replace")
    for n in ast.parse(src).body:
        if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "DATASETS":
            return ast.literal_eval(n.value)
    raise SystemExit("FATAL: DATASETS not found in 41_build_codebooks.py")


def resolve(f: str) -> Path:
    return (CLEAN / f).resolve()


def stream_profile(paths):
    """(ordered columns, {col: {type, pct_filled}}, n_rows) - one row at a time."""
    cols, seen = [], set()
    filled, numeric, nonint, n = {}, {}, {}, 0
    for p in paths:
        if not p.exists():
            continue
        with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            rd = csv.reader(fh)
            hdr = next(rd, [])
            for c in hdr:
                if c not in seen:
                    seen.add(c)
                    cols.append(c)
                    filled[c] = numeric[c] = nonint[c] = 0
            for row in rd:
                n += 1
                for i, c in enumerate(hdr):
                    if i >= len(row):
                        continue
                    v = row[i].strip()
                    if not v:
                        continue
                    filled[c] += 1
                    try:
                        x = float(v.replace(",", "").replace("$", ""))
                        numeric[c] += 1
                        if not float(x).is_integer():
                            nonint[c] += 1
                    except ValueError:
                        pass
    prof = {}
    for c in cols:
        f = filled[c]
        if not f:
            t = "empty"
        elif numeric[c] == f:
            t = "integer" if not nonint[c] else "numeric"
        else:
            t = "text"
        prof[c] = {"type": t,
                   "pct_filled": round(100.0 * f / n, 1) if n else 0.0}
    return cols, prof, n


def parse_doc(path: Path) -> dict:
    """Existing prose, so a refresh keeps every hand-written description."""
    out = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or not cells[0].startswith("`"):
            continue
        names = re.findall(r"`([A-Za-z0-9_]+)`", cells[0])
        desc = cells[-1].strip()
        if not names or not desc or desc.lower() in ("definition", "description"):
            continue
        for nm in names:
            out.setdefault(nm, desc)
    return out


def frag_vars(ds: str) -> dict:
    p = FRAG / f"{ds}.csv"
    if not p.exists():
        return {}
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        return {r["variable"]: r for r in csv.DictReader(fh)}


def live_header(paths):
    cols, seen = [], set()
    for p in paths:
        if not p.exists():
            continue
        with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            for c in next(csv.reader(fh), []):
                if c not in seen:
                    seen.add(c)
                    cols.append(c)
    return cols


def drift_report(DS):
    """Every collection, ghost columns and undocumented columns. Header only -
    no full read, so this is cheap enough to run before deciding anything."""
    rows = []
    for ds, files in DS.items():
        paths = [resolve(f) for f in files]
        missing = [f for f, p in zip(files, paths) if not p.exists()]
        live = live_header(paths)
        doc = set(frag_vars(ds)) or set(parse_doc(DOCS / f"{ds}.md"))
        ghost = [c for c in sorted(doc) if c not in live]
        undoc = [c for c in live if c not in doc]
        bad = [c for c in ghost if c in RETIRED] + [
            c for c in ghost
            if c in RETIRED_SCOPED and any(f in RETIRED_IN for f in files)]
        rows.append({"dataset": ds, "files": files, "missing": missing,
                     "ghost": ghost, "undoc": undoc, "retired": sorted(set(bad))})
    return rows


def refresh(ds: str, DS, m41, apply: bool) -> int:
    files = DS[ds]
    paths = [resolve(f) for f in files]
    for f, p in zip(files, paths):
        if not p.exists():
            print(f"  WARNING file absent, skipped: {f}")
    before = frag_vars(ds)
    prose = parse_doc(DOCS / f"{ds}.md")
    cols, prof, n = stream_profile(paths)

    rows = []
    for c in cols:
        t = prof[c]["type"]
        # PRIOR FRAGMENT -> HAND-WRITTEN PROSE -> 41's DESCRIPTIONS table.
        # Never invented. A blank is left blank. 41's `describe` returns
        # (description, units), and its units are authored rather than guessed,
        # so they win over the suffix heuristic below.
        d41, u41 = m41.describe(c, ds)
        desc = (before.get(c, {}).get("description", "").strip()
                or prose.get(c, "").strip()
                or (d41 or "").strip())
        tier = m41.access_tier(c)
        rows.append({
            "dataset": ds, "variable": c, "type": t,
            "units": (u41 or units_for(c, t)),
            "pct_filled": prof[c]["pct_filled"],
            "n_rows": n, "published": 0 if tier == "internal" else 1,
            "access_tier": tier, "description": desc, "generated": TODAY})

    gained = [c for c in cols if c not in before]
    lost = [c for c in before if c not in cols]
    print(f"  {ds}: {len(before)} -> {len(rows)} variables over "
          f"{n:,} rows in {len(files)} file(s)")
    print(f"    gained ({len(gained)}): {', '.join(gained) or '-'}")
    print(f"    lost   ({len(lost)}): {', '.join(lost) or '-'}"
          f"   <- these columns are NOT in the data any more")
    undescribed = [r["variable"] for r in rows if not r["description"]]
    if undescribed:
        print(f"    NO DESCRIPTION YET ({len(undescribed)}): "
              f"{', '.join(undescribed[:12])}")
        print("    a blank description is honest; an invented one is not. "
              "Write them by hand into the .md and re-run.")
    if not apply:
        print("\n  nothing written. re-run with `--apply`.")
        return 0

    import cedar_codebook as CB                                  # noqa: E402
    p = FRAG / f"{ds}.csv"
    if p.exists():
        bak = p.with_suffix(p.suffix + f".bak_{TODAY}_pre941")
        if not bak.exists():
            bak.write_bytes(p.read_bytes())
    CB.write_fragment(ds, rows, FIELDS)
    print(f"  wrote {p.relative_to(ROOT)}")

    md = DOCS / f"{ds}.md"
    if md.exists():
        bak = md.with_suffix(md.suffix + f".bak_{TODAY}_pre941")
        if not bak.exists():
            bak.write_bytes(md.read_bytes())
    title = ds.split("_", 1)[-1].replace("_", " ").title()
    L = [f"# Codebook — {title}", "",
         f"*{n:,} rows across {len(files)} file(s). Regenerated {TODAY} by "
         f"`code/941_refresh_codebook_fragment.py` from the live headers of "
         f"{', '.join('`' + f + '`' for f in files)}.*", "",
         "Variables marked **internal** are retained for auditing and are not "
         "included in published extracts.", "",
         "| Variable | Type | Units / format | Filled | Description |",
         "|---|---|---|---:|---|"]
    for r in rows:
        mark = (" *(internal)*" if r["access_tier"] == "internal"
                else " *(subscriber)*" if r["access_tier"] == "subscriber"
                else "")
        L.append(f"| `{r['variable']}`{mark} | {r['type']} | {r['units']} | "
                 f"{r['pct_filled']:.0f}% | {r['description']} |")
    md.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"  wrote {md.relative_to(ROOT)}")
    print("\n  the master is NOT rebuilt here. Run "
          "`py -3 code/cedar_codebook.py build` when no other agent owns it.")
    return 0


def units_for(col, t):
    c = col.lower()
    if c.endswith("_id") or c.endswith("_code") or c.endswith("_uid"):
        return "code"
    if "usd" in c or c.endswith("_amount") or c.endswith("_value"):
        return "USD"
    if c.endswith("_date") or c in ("year", "fiscal_year"):
        return "date"
    if t in ("integer", "numeric"):
        return "count"
    return ""


# ---------------------------------------------------------------------------
# THE MINIMAL CORRECTION
# ---------------------------------------------------------------------------
# A full regeneration of 03_federal_funding would add 38 live columns, 22 of
# them public-tier with NO description anybody has written yet - and
# `codebook_undocumented_public` is MUST_BE_ZERO in 62. Shipping 22 blanks to
# make the codebook "current" would trade a stale claim for a broken gate, and
# inventing 22 descriptions would be fabrication. Neither is acceptable.
#
# So `retire-names` does only the part that is unambiguously WRONG rather than
# merely incomplete: the two columns that no longer exist, and the two whose
# fill rates the codebook states falsely. Everything measured with csv.reader
# over the live files on 2026-09-02:
#
#   tribe_id         DROPPED from federal_funding_transactions and the panel by
#                    843. Still documented at "integer, 11%".
#   tribe_id_scheme  DROPPED by 843. Still documented at 77% with the value set
#                    `lineageA_dofile_integer`.
#   tribe_id_neid    documented as type `empty`, 0.0% filled. It is Cedar's own
#                    handle and it is filled on 552,602 rows, 15.9%.
#   canonical_name   documented at 76.9%. Measured 16.0%.
#
# The 38 undocumented columns are reported, not written. That work is owed and
# it belongs to whoever authored the columns.
RETIRE_ROWS = {
    ("03_federal_funding", "tribe_id"): None,
    ("03_federal_funding", "tribe_id_scheme"): None,
}
REPLACE_ROWS = [
    dict(dataset="03_federal_funding", variable="attribution_status",
         type="text", units="category", pct_filled="20.2", published="1",
         access_tier="public",
         description="Whether this row is attributed to a Native entity, "
                     "unattributed, or explicitly ruled not Native. One of: "
                     "`cedar_neid`, `unattributed`, `excluded_not_native`, "
                     "`unresolved_native`. Renamed 2026-09-01 from "
                     "`tribe_id_scheme_resolved` when the CICD id scheme was "
                     "retired; the field is unchanged."),
    dict(dataset="03_federal_funding", variable="cedar_uid",
         type="text", units="code", pct_filled="16.1", published="1",
         access_tier="public",
         description="Cedar Press permanent identifier for the Native entity. "
                     "Stable across releases and across renames; use this to "
                     "join datasets."),
]
FIX_FILL = {
    ("03_federal_funding", "tribe_id_neid"): (
        "text", "15.9",
        "Cedar Press entity handle (NEID form) for the Native entity this row "
        "is attributed to. Blank where the row is unattributed."),
    ("03_federal_funding", "canonical_name"): ("text", "16.0", None),
}


def retire_names(apply: bool) -> int:
    targets = [CLEAN / "codebook_master.csv", FRAG / "03_federal_funding.csv"]
    n_rows_now = "3477199"
    for t in targets:
        if not t.exists():
            print(f"  absent, skipped: {t}")
            continue
        with t.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            rd = csv.DictReader(fh)
            fields = list(rd.fieldnames or [])
            rows = list(rd)
        out, dropped, fixed = [], [], []
        have = {(r["dataset"], r["variable"]) for r in rows}
        for r in rows:
            k = (r.get("dataset"), r.get("variable"))
            if k in RETIRE_ROWS:
                dropped.append(r["variable"])
                continue
            if k in FIX_FILL:
                ty, pct, desc = FIX_FILL[k]
                fixed.append(f"{r['variable']} {r['pct_filled']}%->{pct}%"
                             f" type {r['type']}->{ty}")
                r["type"], r["pct_filled"] = ty, pct
                if desc:
                    r["description"] = desc
            if r.get("dataset") == "03_federal_funding":
                r["n_rows"] = n_rows_now
            out.append(r)
        added = []
        for spec in REPLACE_ROWS:
            k = (spec["dataset"], spec["variable"])
            if k in have:
                continue
            row = {f: "" for f in fields}
            row.update({f: v for f, v in spec.items() if f in fields})
            row["n_rows"] = n_rows_now
            row["generated"] = TODAY
            out.append(row)
            added.append(spec["variable"])
        print(f"  {t.name}: {len(rows)} -> {len(out)} rows")
        print(f"    dropped (retired by 843): {', '.join(dropped) or '-'}")
        print(f"    added:                    {', '.join(added) or '-'}")
        print(f"    fill/type corrected:      {'; '.join(fixed) or '-'}")
        if apply:
            bak = t.with_suffix(t.suffix + f".bak_{TODAY}_pre941")
            if not bak.exists():
                bak.write_bytes(t.read_bytes())
            tmp = t.with_suffix(t.suffix + ".tmp941")
            with tmp.open("w", encoding="utf-8", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
                w.writeheader()
                w.writerows(out)
            tmp.replace(t)
            print(f"    wrote {t.relative_to(ROOT)} (backup {bak.name})")
    if not apply:
        print(chr(10) + "  nothing written. re-run with `--apply`.")
    return 0


def main() -> int:
    argv = sys.argv[1:]
    mode = argv[0] if argv else "drift"
    DS = datasets_map()

    if mode == "retire-names":
        return retire_names("--apply" in argv)

    if mode == "list":
        for ds, files in DS.items():
            print(f"  {ds:<34} {', '.join(files)}")
        return 0

    if mode in ("drift", "verify"):
        rows = drift_report(DS)
        bad = []
        n_ghost = n_undoc = 0
        for r in rows:
            n_ghost += len(r["ghost"])
            n_undoc += len(r["undoc"])
            if r["retired"]:
                bad.append(f"{r['dataset']} still documents RETIRED "
                           f"{', '.join(r['retired'])}")
            if r["missing"]:
                bad.append(f"{r['dataset']} names a file that is not on disk: "
                           f"{', '.join(r['missing'])}")
        if mode == "drift":
            for r in sorted(rows, key=lambda x: -(len(x["ghost"]) * 10
                                                  + len(x["undoc"]))):
                if not (r["ghost"] or r["undoc"] or r["missing"]):
                    continue
                print(f"\n  {r['dataset']}")
                if r["missing"]:
                    print(f"    FILE ABSENT   {', '.join(r['missing'])}")
                if r["ghost"]:
                    print(f"    DOCUMENTED BUT GONE ({len(r['ghost'])})  "
                          f"{', '.join(r['ghost'])}")
                if r["undoc"]:
                    print(f"    LIVE BUT UNDOCUMENTED ({len(r['undoc'])})  "
                          f"{', '.join(r['undoc'][:10])}"
                          f"{' ...' if len(r['undoc']) > 10 else ''}")
            print(f"\n  {sum(1 for r in rows if r['ghost'] or r['undoc'])}"
                  f"/{len(rows)} collections have drifted   "
                  f"{n_ghost} ghost column(s)   {n_undoc} undocumented")
        for b in bad:
            print("  FAIL " + b)
        print(f"  941 verify   {'FAIL' if bad else 'ok'}   {len(bad)} "
              f"codebook(s) documenting a retired column")
        return 1 if (mode == "verify" and bad) else 0

    if mode not in DS:
        print(f"unknown collection {mode!r}. `list` shows them all.")
        return 2
    return refresh(mode, DS, load41(), "--apply" in argv)


if __name__ == "__main__":
    sys.exit(main())
