#!/usr/bin/env python3
"""
288 - COLLECTION DESCRIPTORS, computed from the files. Never hand-typed.

    py -3 code/288_build_collection_descriptors.py

THE TARGET, AS THE PRODUCT REPO ACTUALLY DEFINES IT
---------------------------------------------------
`server/cedar_press/collections.py` in `github.com/teim-team/cedar-press`
declares `CollectionDataset`, a frozen dataclass:

    id · name · short_name · origin · level · tracks · rows_label ·
    downloads · vintage · version · updated · sources · method

The JS mirror is `src/features/grove/collection.js`; shelf assignment lives in
`pressCatalog.js`; release entries in `pressReleases.js`. Its own docstring
says the file is demonstration data - *"plausible values for the demo
workspace, never real published figures. The real pilot datasets arrive as
manifest + data files"* - so generating over it is the intended path.

**"Version and vintage are load-bearing, not garnish."** Its words. And the
citation string is BUILT FROM THE DESCRIPTOR:

    Lumecon, "{name}" ({version}, vintage {vintage}), Cedar Press
    collection, cedarpress.ai. Accessed {date}.

So a wrong `vintage` does not sit quietly in a config file - it propagates
into every citation anyone writes of this data. That is the reason this is
computed and not typed.

THREE MEASURED REASONS NOT TO HAND-TYPE ANY OF IT
-------------------------------------------------
1. The demo descriptor declares `deals` at `rows_label="1,248 rows"`. The file
   holds **935**.
2. It declares `vintage="2026 Q2"` and `tracks="...2010 to current"`. Deals
   actually span **2000-2026** and collection stopped mid-quarter, so "2026
   Q2" is a period the data does not cover and "from 2010" understates the
   series by a decade.
3. `docs/ASSUMPTIONS_AND_LIMITATIONS.md:1484` states the merged employment
   table is **3,300 rows**. That was the PLANNED figure, written before the
   merge was measured. The file holds **3,246** - 54 rows were removed as
   misattributed. **A generator that read the prose would emit the planned
   number.** This one reads the file.

THE VINTAGE RULE, WHICH IS THE WHOLE POINT
------------------------------------------
FY2026 closes 2026-09-30. Prime data stops **2026-07-03** and assistance
**2026-06-30**. So **FY2025 is the last COMPLETE fiscal year and every
calendar-2026 figure is year-to-date.** A descriptor may not name a period
the data does not cover. If the maximum observed date falls inside a period,
the vintage says so in words a citation can carry - `2026-07-03 (YTD)` - and
`vintage_is_ytd` is true. `refusals` records every period label that was
considered and declined, so the honesty is auditable rather than asserted.

Writes to `dist/collections/`. Reads `data/clean` and nothing else; makes no
network call and touches no dataset.

Claimed 2026-08-26 with script numbers 284-292.
"""

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cedar_codebook as CB           # noqa: E402
import cedar_keys as CK               # noqa: E402
import cedar_schema as CS             # noqa: E402

try:
    import cedar_domain as CD         # noqa: E402
except Exception:                     # pragma: no cover
    CD = None

#: The CANONICAL table of a collection, where the repo already declares one.
#: `cedar_domain.PROMOTED_TABLES` names the promoted table and the parts it
#: was built from, and `DEALS_TRUTH` says outright: *"The single truth for
#: the deals universe. Import this; do not glob."*
#:
#: This matters for `rows_label`. Summing every member of the `01_deals`
#: block gives 1,725 - the promoted table PLUS its own parts, counted twice.
#: The demo descriptor says 1,248 and the truth is 935; a generator that
#: emitted 1,725 would be wrong in a new and more confident way.
_PROMOTED = {Path(k).name for k in
             getattr(CD, "PROMOTED_TABLES", {})} if CD else set()

csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
DOCS = CEDAR / "docs"
SCHEMA_DIR = DOCS / "schema"
OUT_DIR = CEDAR / "dist" / "collections"
STATE = OUT_DIR / "_version_state.json"
TODAY = date.today().isoformat()

SOURCE_SCAN_ROWS = 60_000

#: FY end for the US federal fiscal year.
FY_END_MONTH, FY_END_DAY = 9, 30

_DATEISH = re.compile(r"(date|_at|_on|day|period|signed|filed|posted|"
                      r"awarded|effective)", re.I)

#: BUILD METADATA, NOT DATA. `built_date` and `fetched_date` carry the date
#: THIS BUILD RAN, so a vintage computed over them always reads "today" and
#: is always wrong. The first run of this script emitted
#: `vintage = 2026-08-26 (YTD)` for 38 collections for exactly that reason -
#: every one of them would have gone into a citation as the as-of date of the
#: DATA. Excluded by name, before anything is measured.
_BUILD_META = re.compile(
    r"^(built_date|build_date|fetched_date|fetched_at|generated|generated_at|"
    r"retrieved_at|run_date|_?ingested_at|last_updated|updated_at|"
    r"snapshot_date|extracted_at|indexed_at|scraped_at|as_of_date|as_of)$",
    re.I)
#: PROCESSING dates: when CEDAR did something to the row, not when the thing
#: happened at the source. `prime_contracts.ruling_applied_date` is a single
#: constant - 2026-08-26 - and it set `prime-contracting`'s vintage to today
#: on the second run of this script, which would have put "vintage 2026-08-26"
#: into every citation of a series that actually stops 2026-07-03.
_PROCESSING_DATE = re.compile(
    r"(applied|verified|reviewed|linked|resolved|checked|matched|classified|"
    r"promoted|imported|ruled|attributed|geocoded|normalis|normaliz|"
    r"harvested|staged|merged|keyed|observed|collected|seen|added|created|"
    r"entered|logged)", re.I)

_YEARISH = re.compile(r"(^|_)(fy|fiscal_year|year|grant_year|award_year)(_|$)",
                      re.I)

#: A date column with almost no distinct values is a STAMP, not a series.
#: Name lists go stale; this one is a property of the data, so it catches the
#: processing column nobody thought to name.
MIN_DISTINCT_FOR_A_DATE_SERIES = 3
MIN_ROWS_TO_APPLY_THAT_TEST = 100
_URLISH = re.compile(r"(source_url|url|source_link|document_url|link)$", re.I)
_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")

#: The absence vocabulary a concurrent agent is defining for the product.
#: Carried into every descriptor so a reader can always tell a genuine source
#: absence from our failure to look.
#:
#: NOT merged with `cedar_domain.ABSENCE_VALUES`, which is a DIFFERENT and
#: narrower set scoped to individual-Native ownership evidence
#: (NO_CLAIM_FOUND / NO_SITE_FOUND / SITE_UNREACHABLE / NOT_CHECKED /
#: UNDETERMINED). `NOT_CHECKED` is the only member of both. Collapsing them
#: would let "we did not sweep this firm's website" be read as "the source
#: reported nothing", which is exactly the distinction the owner asked for.
ABSENCE_VOCABULARY = {
    "NOT_IN_SOURCE":
        "the source was consulted and does not carry this fact",
    "BELOW_REPORTING_THRESHOLD":
        "the source withholds it because it falls under a stated threshold",
    "OUT_OF_SCOPE_BY_CONSTRUCTION":
        "the row cannot have this value; the question does not apply",
    "SUPPRESSED":
        "Cedar Press withheld it - small cell, licence, or privacy",
    "REPORTED_EMPTY":
        "the source returned an explicit empty value",
    "NOT_CHECKED":
        "nobody looked. Never a finding about the world.",
}


# ---------------------------------------------------------------------------

def fy_of(iso):
    y, m, _ = int(iso[:4]), int(iso[5:7]), int(iso[8:10])
    return y + 1 if (m, ) > (FY_END_MONTH, ) else y


def last_complete_fy(max_iso):
    """The last fiscal year the data covers END TO END."""
    fy = fy_of(max_iso)
    fy_end = f"{fy - 1 if FY_END_MONTH < 12 else fy}-" \
             f"{FY_END_MONTH:02d}-{FY_END_DAY:02d}"
    fy_end = f"{fy}-{FY_END_MONTH:02d}-{FY_END_DAY:02d}" \
        if fy_of(f"{fy}-{FY_END_MONTH:02d}-{FY_END_DAY:02d}") == fy else fy_end
    return fy if max_iso >= fy_end else fy - 1


def scan_dates_and_sources(path, header, columns):
    """min/max date, min/max year, and the source hosts. One pass, FULL.

    FULL and not sampled, deliberately. A sampled maximum date is a vintage
    that is too early, and a vintage that is too early goes into a citation.
    Cheap anyway: only the date, year and url columns are touched.
    """
    n_rows_hint = max((c["n_filled"] for c in columns), default=0)
    idx_d, excluded = [], []
    for c in columns:
        nm = c["name"].strip()
        if not _DATEISH.search(nm) or                 c["observed_type"] not in ("date", "timestamp", "text"):
            continue
        if _BUILD_META.match(nm):
            excluded.append((nm, "build metadata: records when this build "
                                 "ran, not when the event happened"))
            continue
        if _PROCESSING_DATE.search(nm):
            excluded.append((nm, "processing date: records when Cedar acted "
                                 "on the row, not when the event happened"))
            continue
        nd = c.get("n_distinct")
        if (n_rows_hint >= MIN_ROWS_TO_APPLY_THAT_TEST
                and nd is not None
                and nd < MIN_DISTINCT_FOR_A_DATE_SERIES):
            excluded.append((nm, f"only {nd} distinct value(s) over "
                                 f"{n_rows_hint:,} rows - a stamp, not a "
                                 f"series"))
            continue
        idx_d.append(c["position"])
    idx_y = [c["position"] for c in columns
             if _YEARISH.search(c["name"])
             and not _BUILD_META.match(c["name"].strip())]
    idx_u = [c["position"] for c in columns if _URLISH.search(c["name"])]
    if not (idx_d or idx_y or idx_u):
        return {}
    dmin = dmax = None
    fmax = fcol = None          # the furthest FUTURE date, tracked separately
    ymin = ymax = None
    dcol = ycol = None
    hosts = Counter()
    n = 0
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.reader(fh)
        next(rd, None)
        for row in rd:
            n += 1
            for i in idx_d:
                if i >= len(row):
                    continue
                m = _ISO.match(row[i].strip())
                if not m:
                    continue
                v = m.group(0)
                if not (1776 <= int(v[:4]) <= 2100):
                    continue
                # A FUTURE date is a fact the data records, never the
                # data's as-of date. A gaming compact expiring in 2060 made
                # the first run emit `vintage 2060-12-31`. Tracked, and kept
                # out of the vintage.
                if v > TODAY:
                    if fmax is None or v > fmax:
                        fmax, fcol = v, header[i]
                    continue
                if dmax is None or v > dmax:
                    dmax, dcol = v, header[i]
                if dmin is None or v < dmin:
                    dmin = v
            for i in idx_y:
                if i >= len(row):
                    continue
                s = row[i].strip()
                if len(s) == 4 and s.isdigit() and 1776 <= int(s) <= 2100:
                    y = int(s)
                    if y > int(TODAY[:4]):
                        continue
                    if ymax is None or y > ymax:
                        ymax, ycol = y, header[i]
                    if ymin is None or y < ymin:
                        ymin = y
            if n <= SOURCE_SCAN_ROWS:
                for i in idx_u:
                    if i < len(row) and row[i].startswith("http"):
                        h = urlparse(row[i].strip()).netloc.lower()
                        if h:
                            hosts[h] += 1
    return {"date_min": dmin, "date_max": dmax, "date_column": dcol,
            "future_date_max": fmax, "future_date_column": fcol,
            "date_columns_excluded": excluded,
            "year_min": ymin, "year_max": ymax, "year_column": ycol,
            "hosts": hosts.most_common(8), "rows": n,
            "hosts_basis": f"netloc of {', '.join(header[i] for i in idx_u)} "
                           f"over the first {min(n, SOURCE_SCAN_ROWS):,} rows"
                           if idx_u else None}


def compute_vintage(span):
    """(vintage, is_ytd, complete_through, refusals). Honest by construction."""
    refusals = []
    dmax = span.get("date_max")
    ymax = span.get("year_max")
    if not dmax and ymax:
        # A year column and nothing else. `prime_contracts.csv` is exactly
        # this: `fiscal_year` plus two build stamps, and no transaction date
        # at all. So the series CANNOT support a dated vintage, and saying so
        # IS the finding - not a gap to paper over with today's date.
        fy_end = f"{ymax}-{FY_END_MONTH:02d}-{FY_END_DAY:02d}"
        refusals.append(
            f"declined to emit a dated vintage: this collection carries no "
            f"event-date column, only a year. Most recent year: {ymax}.")
        if TODAY < fy_end:
            refusals.append(
                f"declined to emit vintage 'FY{ymax}': FY{ymax} ends "
                f"{fy_end} and today is {TODAY}, so FY{ymax - 1} is the "
                f"last COMPLETE fiscal year and every FY{ymax} figure is "
                f"year-to-date.")
            return (f"FY{ymax} (YTD; FY{ymax - 1} is the last complete "
                    f"fiscal year)"), True, ymax - 1, refusals
        return f"FY{ymax}", False, ymax, refusals
    if not dmax:
        refusals.append("no date or year column: no vintage can be computed")
        return None, None, None, refusals

    y, m, d = int(dmax[:4]), int(dmax[5:7]), int(dmax[8:10])
    cal_complete = (m, d) == (12, 31)
    fy = fy_of(dmax)
    fy_end = f"{fy}-{FY_END_MONTH:02d}-{FY_END_DAY:02d}"
    fy_complete = dmax >= fy_end
    q = (m - 1) // 3 + 1
    q_end = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}[q]
    q_complete = (m, d) >= q_end

    if fy_complete and cal_complete:
        return dmax, False, fy, refusals
    if not fy_complete:
        refusals.append(
            f"declined to emit vintage 'FY{fy}': FY{fy} ends {fy_end} and "
            f"the data stops {dmax}. FY{fy - 1} is the last COMPLETE fiscal "
            f"year and every FY{fy} figure is year-to-date.")
    if not q_complete:
        refusals.append(
            f"declined to emit vintage '{y} Q{q}': that quarter ends "
            f"{y}-{q_end[0]:02d}-{q_end[1]:02d} and the data stops {dmax}.")
    if not cal_complete:
        refusals.append(
            f"declined to emit vintage '{y}': the calendar year is not "
            f"complete in this data (stops {dmax}), so every {y} figure "
            f"is year-to-date.")
    return f"{dmax} (YTD)", True, fy - 1 if not fy_complete else fy, refusals


def rows_label(n, stem, level):
    """What ONE ROW IS, in words. Display copy - not a count the code trusts,
    but it must not contradict the file either."""
    unit = re.sub(r"^(cedar|gaming|np|fac|fr|nigc)_", "", stem)
    unit = unit.replace("_", " ").strip()
    unit = re.sub(r"\b(clean|final|published|classified|all|table)\b", "",
                  unit).strip() or "records"
    if not unit.endswith("s"):
        unit += "s"
    return f"{n:,} {unit}"


def slug(block):
    return re.sub(r"^\d+[a-z]?_", "", block).replace("_", "-")


def title(block):
    s = re.sub(r"^\d+[a-z]?_", "", block).replace("_", " ")
    return s.title().replace("Np ", "Nonprofit ").replace("Fr ", "Federal Register ")


def main():
    started = datetime.now()
    print("=" * 78)
    print("288  COLLECTION DESCRIPTORS - computed, not typed")
    print("=" * 78)

    schema_index = {}
    p = SCHEMA_DIR / "schema_index.json"
    if p.exists():
        schema_index = json.loads(p.read_text(encoding="utf-8"))["tables"]
    keys = {}
    p = SCHEMA_DIR / "keys.json"
    if p.exists():
        keys = json.loads(p.read_text(encoding="utf-8"))["tables"]

    groups = CB.dataset_groups()
    shippable, licensed, undocumented = CB.registered_tables(groups=groups)
    profiles, _, _ = CS.load_profiles()
    print(f"\n  {len(shippable)} shippable tables in "
          f"{len({g for _, g, _ in shippable})} codebook blocks")
    print(f"  {len(licensed)} vendor-licensed tables excluded outright")
    print(f"  {len(undocumented)} undocumented tables have no collection")

    by_block = defaultdict(list)
    for path, g, score in shippable:
        by_block[g].append((path, score))

    print(f"\n  scanning dates and sources (full pass, date/year/url columns "
          f"only)...")
    descriptors, all_refusals = {}, []
    prev = {}
    if STATE.exists():
        prev = json.loads(STATE.read_text(encoding="utf-8"))

    for block in sorted(by_block):
        members = sorted(by_block[block], key=lambda ps: -ps[0].stat().st_size)
        spans, rows_total, hosts = [], 0, Counter()
        excluded_cols = []
        downloads, blocked_members = [], []
        for path, score in members:
            pr = profiles.get(path.name, {})
            cols = pr.get("columns", [])
            hdr = pr.get("header_order", [])
            try:
                sp = scan_dates_and_sources(path, hdr, cols)
            except Exception as e:                  # noqa: BLE001
                sp = {"error": f"{type(e).__name__}: {e}"}
            n = sp.get("rows", pr.get("rows_scanned", 0))
            rows_total += n
            if sp.get("date_max") or sp.get("year_max"):
                spans.append(sp)
            for nm, why in sp.get("date_columns_excluded", []):
                excluded_cols.append((path.name, nm, why))
            for h, c in sp.get("hosts", []):
                hosts[h] += c
            st = schema_index.get(path.name, {})
            k = (keys.get(path.name, {}) or {}).get("primary_key", {})
            entry = {
                "file": path.name,
                "rows": n,
                "columns": st.get("columns"),
                "ingest_status": st.get("status", "UNKNOWN"),
                "primary_key_kind": k.get("kind"),
                "primary_key": k.get("columns"),
                "licensed_columns_withheld":
                    st.get("licensed_columns_dropped", []),
            }
            downloads.append(entry)
            if str(st.get("status", "")).startswith("BLOCKED"):
                blocked_members.append(path.name)

        merged = {
            "date_min": min((s["date_min"] for s in spans
                             if s.get("date_min")), default=None),
            "date_max": max((s["date_max"] for s in spans
                             if s.get("date_max")), default=None),
            "year_min": min((s["year_min"] for s in spans
                             if s.get("year_min")), default=None),
            "year_max": max((s["year_max"] for s in spans
                             if s.get("year_max")), default=None),
        }
        vintage, is_ytd, complete_through, refusals = compute_vintage(merged)
        for r in refusals:
            all_refusals.append((block, r))

        lo = merged["year_min"] or (merged["date_min"] or "")[:4] or None
        hi = merged["year_max"] or (merged["date_max"] or "")[:4] or None
        tracks = (f"{lo} to {hi}" if lo and hi and str(lo) != str(hi)
                  else (str(lo) if lo else "span not computable from this "
                                            "table's columns"))
        # Forward-looking dates are a FACT the data records - a compact that
        # expires in 2060 - and they belong in `tracks`, never in `vintage`.
        fut = max((s.get("future_date_max") for s in spans
                   if s.get("future_date_max")), default=None)
        if fut:
            tracks += f" (terms recorded out to {fut[:4]})"

        # The canonical member: the promoted table if the domain declares
        # one, otherwise the largest. Never the sum.
        promoted = [pth for pth, _ in members if pth.name in _PROMOTED]
        main_file = promoted[0] if promoted else members[0][0]
        main_rows = next((d["rows"] for d in downloads
                          if d["file"] == main_file.name), rows_total)
        cid = slug(block)
        prev_entry = prev.get(cid, {})
        content_digest = CK.stable_digest(
            [str(sorted((d["file"], d["rows"]) for d in downloads)),
             str(vintage), tracks])
        changed = prev_entry.get("content_digest") != content_digest
        version = prev_entry.get("version", "v0.1")
        if changed and prev_entry:
            maj, minr = version.lstrip("v").split(".")
            version = f"v{maj}.{int(minr) + 1}"
        updated = TODAY if changed or not prev_entry \
            else prev_entry.get("updated", TODAY)

        sources = [{"host": h, "n_rows_citing": c}
                   for h, c in hosts.most_common(8)]
        producing = sorted({s for s in (
            schema_index.get(d["file"], {}).get("producing_script")
            for d in downloads) if s})

        descriptors[cid] = {
            # --- the product's CollectionDataset fields --------------------
            "id": cid,
            "name": title(block),
            "short_name": title(block).split()[-1],
            "origin": "federal_administrative_record",
            "level": "entity_records",
            "tracks": tracks,
            "rows_label": rows_label(main_rows, main_file.stem,
                                     "entity_records"),
            "downloads": downloads,
            "vintage": vintage,
            "version": version,
            "updated": updated,
            "sources": sources,
            "method": (
                f"Assembled by Cedar Press from {len(downloads)} table(s) "
                f"documented in codebook block `{block}`. "
                f"{'Primary keys: ' + ', '.join(sorted({d['primary_key_kind'] for d in downloads if d['primary_key_kind']})) + '. ' if downloads else ''}"
                f"Every figure is recomputed from `data/clean` at build "
                f"time; none is transcribed from a document."),
            # --- everything below is Cedar-side provenance, not the -------
            # --- product contract. Kept separate on purpose.  -------------
            "_cedar": {
                "codebook_block": block,
                "vintage_is_ytd": is_ytd,
                "last_complete_fiscal_year": complete_through,
                "vintage_refusals": refusals,
                "date_min": merged["date_min"],
                "date_max": merged["date_max"],
                "furthest_forward_date": fut,
                "date_columns_excluded_from_vintage": [
                    {"file": f, "column": c, "why": w}
                    for f, c, w in excluded_cols],
                "vintage_column": next(
                    (sp.get("date_column") for sp in spans
                     if sp.get("date_max") == merged["date_max"]), None),
                "rows_in_canonical_table": main_rows,
                "canonical_table": main_file.name,
                "content_digest": content_digest,
                "content_changed_since_last_build": changed,
                "rows_total": rows_total,
                "members_blocked_for_ingest": blocked_members,
                "shelf": None,
                "shelf_note": "The shelf (standard / pro / grove) is a "
                              "CATALOG decision on the app side, not a "
                              "property of the file. Never emitted here.",
                "origin_level_note":
                    "`origin` and `level` must use the app's evidence "
                    "registry vocabulary (SOURCE_ORIGIN, "
                    "SOURCE_AVAILABILITY). The values above are Cedar's "
                    "best reading and MUST be validated against that "
                    "registry before a PR - this repo has no copy of it, "
                    "and inventing a vocabulary member is how two systems "
                    "silently disagree.",
                "absence_vocabulary": ABSENCE_VOCABULARY,
                "sources_basis":
                    "distinct netloc of the table's source_url column over "
                    f"the first {SOURCE_SCAN_ROWS:,} rows. A frequency "
                    "ranking of hosts, NOT a licence-cleared citation list.",
                "producing_scripts": producing,
                "citation_preview":
                    f'Lumecon, "{title(block)}" ({version}, vintage '
                    f'{vintage}), Cedar Press collection, cedarpress.ai.',
            },
        }

    # --- report -------------------------------------------------------------
    print(f"\n  {len(descriptors)} collection descriptor(s)\n")
    print(f"  {'id':28s} {'rows':>9}  {'vintage':26s} tracks")
    for cid, d in sorted(descriptors.items()):
        print(f"  {cid:28s} {d['_cedar']['rows_total']:>9,}  "
              f"{str(d['vintage'])[:26]:26s} {d['tracks']}")

    ytd = [c for c, d in descriptors.items() if d["_cedar"]["vintage_is_ytd"]]
    print(f"\n  VINTAGE HONESTY: {len(ytd)} of {len(descriptors)} collections "
          f"are YTD and say so.")
    print(f"  {len(all_refusals)} period label(s) were considered and "
          f"REFUSED:")
    for block, r in all_refusals[:14]:
        print(f"    {block}: {r}")
    if len(all_refusals) > 14:
        print(f"    ... and {len(all_refusals) - 14} more, in each "
              f"descriptor's `_cedar.vintage_refusals`")

    blocked = {c: d["_cedar"]["members_blocked_for_ingest"]
               for c, d in descriptors.items()
               if d["_cedar"]["members_blocked_for_ingest"]}
    print(f"\n  COLLECTIONS WITH A MEMBER BLOCKED FOR INGEST "
          f"({len(blocked)}) - these cannot ship whole:")
    for c, files in sorted(blocked.items()):
        print(f"    {c:26s} {', '.join(files)}")

    # --- the three fixtures the coordinator named --------------------------
    print("\n  FIXTURES - a hand-typed descriptor vs the file")
    dl = descriptors.get("deals", {})
    if dl:
        print(f"    deals  demo says rows_label='1,248 rows'   -> computed "
              f"'{dl['rows_label']}'")
        print(f"    deals  demo says vintage='2026 Q2'         -> computed "
              f"'{dl['vintage']}'")
        print(f"    deals  demo says tracks='2010 to current'  -> computed "
              f"'{dl['tracks']}'")
    GROUND_TRUTH = {
        "federal-funding": ("2026-06-30", "assistance data stops 2026-06-30"),
    }
    for cid, (want, why) in GROUND_TRUTH.items():
        got = str(descriptors.get(cid, {}).get("vintage") or "")
        ok = got.startswith(want)
        print(f"    {cid}: vintage {'MATCHES' if ok else 'DOES NOT MATCH'} "
              f"the recorded ground truth ({why}) - computed '{got}'")
    pc = descriptors.get("prime-contracting", {})
    if pc:
        print(f"    prime-contracting: '{pc['vintage']}'")
        print(f"      prime_contracts.csv carries NO transaction-date "
              f"column - only fiscal_year, built_date and "
              f"ruling_applied_date.")
        print(f"      START_HERE.md records that prime data stops "
              f"2026-07-03; that date is NOT in this table, so it cannot "
              f"be asserted here.")

    emp = CLEAN / "gaming_employment_observations.csv"
    if emp.exists():
        n = profiles.get(emp.name, {}).get("rows_scanned", 0)
        print(f"    gaming_employment_observations.csv: "
              f"ASSUMPTIONS_AND_LIMITATIONS.md:1484 says 3,300 rows; "
              f"the file holds {n:,}")

    # --- write --------------------------------------------------------------
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for cid, d in descriptors.items():
        p = OUT_DIR / f"{cid}.json"
        tmp = p.with_suffix(".json.part")
        tmp.write_text(json.dumps(d, indent=1, sort_keys=True, default=str),
                       encoding="utf-8")
        tmp.replace(p)
    index = {"generated": TODAY,
             "generated_at": started.isoformat(timespec="seconds"),
             "produced_by": "288_build_collection_descriptors.py",
             "target": "github.com/teim-team/cedar-press "
                       "server/cedar_press/collections.py CollectionDataset",
             "contract_fields": ["id", "name", "short_name", "origin",
                                 "level", "tracks", "rows_label",
                                 "downloads", "vintage", "version",
                                 "updated", "sources", "method"],
             "absence_vocabulary": ABSENCE_VOCABULARY,
             "vintage_rule": "FY2026 closes 2026-09-30; prime data stops "
                             "2026-07-03 and assistance 2026-06-30, so "
                             "FY2025 is the last complete fiscal year and "
                             "every calendar-2026 figure is YTD. A "
                             "descriptor may not name a period the data "
                             "does not cover.",
             "collections": {c: {k: v for k, v in d.items() if k != "_cedar"}
                             for c, d in descriptors.items()}}
    tmp = (OUT_DIR / "index.json").with_suffix(".json.part")
    tmp.write_text(json.dumps(index, indent=1, sort_keys=True, default=str),
                   encoding="utf-8")
    tmp.replace(OUT_DIR / "index.json")
    state = {c: {"version": d["version"], "updated": d["updated"],
                 "content_digest": d["_cedar"]["content_digest"]}
             for c, d in descriptors.items()}
    tmp = STATE.with_suffix(".json.part")
    tmp.write_text(json.dumps(state, indent=1, sort_keys=True),
                   encoding="utf-8")
    tmp.replace(STATE)
    json.loads((OUT_DIR / "index.json").read_text(encoding="utf-8"))

    print(f"\n  wrote dist/collections/*.json ({len(descriptors)} files) "
          f"+ index.json + _version_state.json, re-read OK")
    print(f"\n  {(datetime.now() - started).total_seconds():.1f}s")
    print("  NOTHING IN data/clean WAS WRITTEN. No network call was made.")
    print("  NOTHING WAS PUSHED - the PR is the coordinator's to open.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
