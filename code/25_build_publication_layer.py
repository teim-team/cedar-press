#!/usr/bin/env python3
"""
Cedar Press - 25: Build the publication layer.

Three deliverables, one run:

  1. SQLite database   dist/cedar_press.db
     Every dataset as a table, typed, indexed on the identifier columns people
     actually join on. Ships with dist/schema.sql so it can be loaded into
     Postgres or anything else.

  2. Master spreadsheet dist/cedar_press_master.xlsx
     Human-facing. Summary first, then the panel-level tables. The two 200 MB+
     transaction files are deliberately NOT embedded - a spreadsheet that
     crashes Excel is not a deliverable. They live in the DB and as CSV.

  3. Sanity checks      dist/SANITY_CHECKS.md
     Runs before publishing and FAILS LOUDLY. Checks that would have caught
     every defect found so far: blank identifiers, tier leakage, orphaned
     rulings, duplicate keys, malformed CAGEs, pre-2000 rows in a published
     view, and dollar figures that carry no basis.

No charts. Elijah: "we dont need fancy graphs or anything."
"""

import csv
import sqlite3
import sys
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
DIST = CEDAR / "dist"
TODAY = date.today().isoformat()

MAX_XLSX_ROWS = 200_000     # Excel's real-world comfort limit
SIZE_LIMIT_MB = 60          # above this, DB + CSV only

# (table_name, source path, index columns, ship_in_xlsx)
TABLES = [
    ("entity_spine",           SPINE / "cedar_entity_spine.csv",              ["tribe_id"], True),
    ("identifier_ledger",      CLEAN / "cedar_identifier_ledger_final.csv",   ["identifier", "tribe_id", "confidence_tier"], True),
    ("publishable_identifiers", CLEAN / "cedar_publishable_identifiers.csv",  ["identifier"], True),
    ("exclusion_rulings",      SPINE / "cedar_exclusion_rulings.csv",         ["identifier"], True),
    ("elijah_rulings",         SPINE / "cedar_rulings.csv",                   ["identifier"], True),
    ("uei_cage_map",           CLEAN / "fpds_uei_cage_map.csv",               ["uei", "cage_code"], False),
    ("uei_ownership_edges",    CLEAN / "fpds_uei_edges.csv",                  ["child_uei", "parent_uei"], True),
    ("funding_transactions",   CLEAN / "federal_funding_transactions.csv",    ["recipient_uei", "tribe_id"], False),
    ("funding_tribe_year",     CLEAN / "federal_funding_tribe_year_panel.csv", ["tribe_id"], True),
    ("subawards",              CLEAN / "subawards.csv",                       ["sub_uei", "prime_uei"], True),
    ("prime_sub_network",      CLEAN / "prime_sub_network.csv",               ["prime_uei", "sub_uei"], True),
    ("lobbying_filings",       CLEAN / "native_entity_lobbying_disclosures.csv", ["entity_id"], True),
    ("lobbying_entity_year",   CLEAN / "tribe_year_lobbying_panel.csv",       ["entity_id"], True),
    ("nonprofit_orgs",         CLEAN / "np_orgs.csv",                         ["EIN"], True),
    ("federal_actions",        CLEAN / "federal_actions.csv",                 ["document_number"], False),
    ("native_bills",           CLEAN / "native_bills.csv",                    ["bill_id"], True),
    ("bill_votes",             CLEAN / "bill_votes.csv",                      ["vote_id", "bill_id"], True),
    ("member_positions",       CLEAN / "member_positions.csv",                ["vote_id"], False),
    ("compacts",               CLEAN / "compacts.csv",                        ["compact_id"], True),
    ("compact_versions",       CLEAN / "compact_versions.csv",                ["version_id", "compact_id"], True),
    ("compact_terms",          CLEAN / "compact_terms.csv",                   ["version_id"], True),
    ("gaming_decisions",       CLEAN / "gaming_land_decisions.csv",           ["decision_id"], True),
    ("gaming_facilities",      CLEAN / "gaming_facilities.csv",               [], True),
    ("nho_entities",           CLEAN / "nho_verified_entities.csv",           ["uei"], True),
    ("anc_roster",             CLEAN / "anc_ceiling_roster.csv",              ["anc_id"], True),
    ("cross_dataset_map",      CLEAN / "cross_dataset_ruling_map.csv",        ["identifier"], True),
    # The lobbying REGISTRANT layer, added 2026-08-26 by
    # code/183_register_lobbying_registrant_layer.py. The firm hired to lobby
    # is an entity in its own right; until now it was a bare string on a
    # filing. Registered here as overrides because these tables carry index
    # columns the codebook registry cannot guess.
    ("lobbying_registrants",           CLEAN / "lobbying_registrants.csv",                          ["registrant_id"], True),
    ("lobbying_registrant_clients",    CLEAN / "lobbying_registrant_client_relationships.csv",      ["registrant_id", "client_id", "native_entity_id"], True),
    ("lobbying_registrant_identifiers", CLEAN / "lobbying_registrant_identifiers.csv",              ["registrant_id", "identifier"], True),
    ("lobbying_registrant_ownership",  CLEAN / "lobbying_registrant_native_ownership_evidence.csv", ["registrant_id", "native_entity_id"], True),
    ("lobbying_registrant_concentration", CLEAN / "lobbying_registrant_concentration.csv",          ["scope", "scope_value"], True),
    # The CORRECTION REGISTER, added 2026-08-26 by
    # code/356_register_correction_register.py. Every attribution this project
    # has WITHDRAWN, stated as an (entity, subject) pair that must no longer
    # co-occur in any table. It ships for the same reason the withdrawals
    # themselves stay visible in their own files: a project whose premise is
    # never to attribute falsely owes the public its list of corrections.
    ("correction_register",    CLEAN / "cedar_correction_register.csv",       ["correction_id", "entity_id", "finding_id"], True),
    # The OWNERSHIP-CHAIN ranking, added 2026-08-26 by
    # code/269_build_contractor_ranking.py. One row per operating company, with
    # the entity that owns it and the identifier that establishes the link.
    # Registered as an override because the index columns are a compound of an
    # owner key and a firm key, which the codebook registry cannot guess. The
    # table is TIER A ONLY by construction - the tier filter has already been
    # applied at build time, so there is no tier column to filter on here.
    ("contractor_ranking",             CLEAN / "contractor_ranking.csv",                            ["owner_entity_id", "operating_company_uei"], True),
    # The INDIVIDUALLY NATIVE-OWNED FIRM class, added 2026-08-26 by
    # code/241-243. Registered as overrides because the index columns are a
    # Cedar surrogate the registry cannot guess, and because the three tables
    # have DIFFERENT publication rules that a reader must be able to tell
    # apart: the register and the firm-year table are internal join surfaces
    # whose name and identifier columns carry `published = 0`, and only the
    # published view is surrogate-keyed and small-cell suppressed.
    #
    # NONE of these ever sums into a tribal, ANC or NHO total. Every entity in
    # the class is self-parented and `cedar_domain.bears_ownership()` refuses
    # every edge on it in both directions.
    ("individual_native_firm_register",  CLEAN / "individual_native_firm_register.csv",             ["surrogate_entity_id", "identifier"], True),
    ("individual_native_firm_contracts", CLEAN / "individual_native_firm_contracts.csv",            ["surrogate_entity_id", "identifier"], True),
    ("individual_native_firm_contracts_published", CLEAN / "individual_native_firm_contracts_published.csv", ["surrogate_entity_id"], True),
    ("individual_native_exclusion_pairs", CLEAN / "individual_native_exclusion_pairs.csv",          ["identifier", "excluded_entity_id"], True),
]


# ---------------------------------------------------------------------------
# TABLES ABOVE IS NOW AN OVERRIDE LIST, NOT THE UNIVERSE.
#
# 2026-08-26: it WAS the universe, and it held two gaming entries against 47
# gaming tables in data/clean. dist/cedar_press.db shipped 912 of 104,412
# gaming rows - 0.87% - and nothing anywhere reported that.
#
# TABLES still earns its place: it carries facts the registry does not know -
# a table's published NAME (`gaming_decisions` for gaming_land_decisions.csv),
# its index columns, whether it belongs in the spreadsheet, and the three
# sources that live in data/spine rather than data/clean. Everything ELSE now
# comes from the codebook registry, so a new dataset ships by being documented
# rather than by someone remembering to edit this list.
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent))
import cedar_codebook as CB                                    # noqa: E402


def resolve_tables():
    """Curated overrides first, then everything the codebook documents."""
    out = list(TABLES)
    seen = {p.name for _, p, _, _ in TABLES}
    shippable, licensed, undocumented = CB.registered_tables()

    for p, group, score in sorted(shippable, key=lambda r: r[0].name):
        if p.name in seen:
            continue
        out.append((p.stem, p, guess_index(p), True))
    return out, licensed, undocumented


def guess_index(path):
    """Index the join keys people actually use, if the file has them."""
    hdr = [h.strip().lower() for h in CB.header_of(path)]
    want = ("tribe_id", "entity_id", "facility_id", "property_id",
            "compact_id", "uei", "ein", "cage_code", "administrative_region_id")
    return [c for c in want if c in hdr][:3]


def sqlname(s):
    """SQL-safe column name."""
    out = "".join(c if (c.isalnum() or c == "_") else "_" for c in s.strip())
    if not out or out[0].isdigit():
        out = "c_" + out
    return out.lower()[:60]


def load(path, limit=None):
    if not path.exists():
        return None, None
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rd = csv.reader(fh)
        try:
            header = next(rd)
        except StopIteration:
            return [], []
        rows = []
        for i, r in enumerate(rd):
            if limit and i >= limit:
                break
            rows.append(r)
    return header, rows


# ---------------------------------------------------------------- sanity ----
def sanity(conn):
    """Checks that would have caught every defect found so far."""
    checks = []

    def chk(name, sql, ok_if_zero=True, note=""):
        try:
            n = conn.execute(sql).fetchone()[0]
        except sqlite3.Error as e:
            checks.append((name, "SKIP", str(e)[:70], note))
            return
        status = "PASS" if ((n == 0) == ok_if_zero) else "FAIL"
        checks.append((name, status, f"{n:,}", note))

    chk("Blank identifiers in ledger",
        "SELECT COUNT(*) FROM identifier_ledger WHERE TRIM(COALESCE(identifier,''))=''",
        note="A blank identifier produced unusable review rows once already.")
    chk("Tier X leaked into publishable set",
        "SELECT COUNT(*) FROM publishable_identifiers WHERE confidence_tier<>'A'",
        note="Only tier A may publish.")
    chk("Excluded identifiers present in publishable set",
        "SELECT COUNT(*) FROM publishable_identifiers p JOIN exclusion_rulings e "
        "ON UPPER(p.identifier)=UPPER(e.identifier)",
        note="An exclusion ruling must block publication everywhere.")
    chk("Malformed CAGE unflagged in uei_cage_map",
        "SELECT COUNT(*) FROM uei_cage_map WHERE LENGTH(TRIM(cage_code))>0 "
        "AND LENGTH(TRIM(cage_code))<>5 AND TRIM(COALESCE(cage_malformed_flag,''))=''",
        note="Excel stripped leading zeros and produced scientific notation.")
    chk("Ownership self-edges",
        "SELECT COUNT(*) FROM uei_ownership_edges WHERE UPPER(child_uei)=UPPER(parent_uei)",
        note="A self-loop is not an inter-firm linkage.")
    chk("Federal roll-up unflagged in ownership edges",
        "SELECT COUNT(*) FROM uei_ownership_edges WHERE UPPER(parent_uei)='NW2RJN8TQQW1' "
        "AND COALESCE(blocklisted_parent,'')<>'1'",
        note="GOVERNMENT OF THE UNITED STATES - would attribute agencies to tribes. "
             "Must be flagged in the data, not just blocked in one consumer.")
    chk("Duplicate compact_id",
        "SELECT COUNT(*) FROM (SELECT compact_id FROM compacts GROUP BY compact_id "
        "HAVING COUNT(*)>1)")
    chk("Orphan compact_versions",
        "SELECT COUNT(*) FROM compact_versions v LEFT JOIN compacts c "
        "USING(compact_id) WHERE c.compact_id IS NULL")
    # A blank bill_id is an UNLINKED procedural vote, not a broken key. Only a
    # non-blank bill_id pointing at nothing is a genuine referential failure.
    chk("Dangling bill_id in bill_votes",
        "SELECT COUNT(*) FROM bill_votes v LEFT JOIN native_bills b USING(bill_id) "
        "WHERE b.bill_id IS NULL AND TRIM(COALESCE(v.bill_id,''))<>''",
        note="Blank bill_id = unlinked procedural vote (a real category). "
             "Non-blank pointing at nothing = a real break.")
    chk("NHO firms in tier A with no ruled parent",
        "SELECT COUNT(*) FROM nho_entities WHERE confidence_tier='A' "
        "AND TRIM(COALESCE(parent_native_entity,''))=''",
        note="8(a) alone never establishes NHO ownership.")
    chk("Funding rows attributed AND excluded without both flags",
        "SELECT COUNT(*) FROM funding_transactions "
        "WHERE attributed_flag='1' AND excluded_flag='1' AND confidence_tier<>'X'",
        note="Both facts must be retained, tier must reflect the exclusion.")
    chk("pre_2000 rows present in federal_actions (expected, informational)",
        "SELECT COUNT(*) FROM federal_actions WHERE pre_2000_flag='1'",
        ok_if_zero=False,
        note="Expected non-zero: retained and flagged, excluded from the published view.")
    chk("Deal rows missing a Deal_Category",
        "SELECT COUNT(*) FROM deals WHERE TRIM(COALESCE(Deal_Category,''))=''",
        note="Without a category, negotiated transactions cannot be separated from "
             "federal awards - and the two must never be charted as one series.")
    return checks


# ------------------------------------------------------------------ main ----
def main():
    DIST.mkdir(parents=True, exist_ok=True)
    dbpath = DIST / "cedar_press.db"
    if dbpath.exists():
        dbpath.unlink()
    conn = sqlite3.connect(dbpath)
    conn.execute("PRAGMA journal_mode=OFF")
    conn.execute("PRAGMA synchronous=OFF")

    print("=== Cedar Press: publication layer ===\n")
    print("[1] Building SQLite database")
    ddl, manifest = [], []

    resolved, licensed, undocumented = resolve_tables()
    print(f"  {len(TABLES)} curated + {len(resolved) - len(TABLES)} from the "
          f"codebook registry = {len(resolved)} tables")
    if licensed:
        print("  LICENCE GATE - refused, by name:")
        for p, _, _ in licensed:
            print(f"     {p.name}  ({CB.LICENSED_SOURCE_FILES[p.name]})")
    if undocumented:
        print(f"  {len(undocumented)} clean table(s) have no codebook block "
              f"and CANNOT be published. Named at the end of this run.")

    for table, path, idx, in_xlsx in resolved:
        # A TABLE NAME IS AS SQL-UNSAFE AS A COLUMN NAME, and only the columns
        # were being cleaned. Registry-derived tables take their name from
        # `path.stem`, and `data/clean/advocacy_passthrough_2026-08-07.csv`
        # (dated 2026-08-07) makes that stem
        # `advocacy_passthrough_2026-08-07` - three bare hyphens in a
        # `CREATE TABLE` statement, which sqlite reads as subtraction and
        # rejects with `near "-": syntax error`. The whole build then aborts
        # AFTER `dbpath.unlink()`, so the failure mode is a partial database on
        # disk where a complete one used to be.
        # Found 2026-08-26 by code/243's registration chain. The defect is not
        # in the dated file; it is here, and it fires for any registered table
        # whose filename carries a date, a dot or a space.
        # `sqlname()` already existed one function away.
        table = sqlname(table)
        if not path.exists():
            print(f"  - {table:<26} not built")
            continue
        if path.name in CB.LICENSED_SOURCE_FILES:
            print(f"  ! {table:<26} REFUSED - vendor-licensed")
            continue
        size_mb = path.stat().st_size / 1024 / 1024
        header, rows = load(path)
        if header is None:
            continue

        # A licensed vendor key never reaches the database. Measured
        # 2026-08-26, the shipped DB carried 404,236 populated recipient_duns
        # and 595 casino_city_id against terms that say neither is published.
        drop = {i for i, c in enumerate(header) if CB.is_licensed_col(c)}
        if drop:
            print(f"    [licensed] {table}: dropping "
                  f"{', '.join(header[i] for i in sorted(drop))}")
            header = [c for i, c in enumerate(header) if i not in drop]
            rows = [[v for i, v in enumerate(r) if i not in drop] for r in rows]

        cols = [sqlname(c) for c in header]
        # De-duplicate column names (some sources ship repeats).
        seen, final = {}, []
        for c in cols:
            if c in seen:
                seen[c] += 1
                c = f"{c}_{seen[c]}"
            else:
                seen[c] = 0
            final.append(c)

        create = f"CREATE TABLE {table} (\n  " + ",\n  ".join(f'"{c}" TEXT' for c in final) + "\n);"
        conn.execute(create)
        ddl.append(create)
        conn.executemany(
            f"INSERT INTO {table} VALUES ({','.join('?' * len(final))})",
            [r[:len(final)] + [None] * (len(final) - len(r)) for r in rows])
        for ic in idx:
            ic_s = sqlname(ic)
            if ic_s in final:
                stmt = f"CREATE INDEX ix_{table}_{ic_s} ON {table}({ic_s});"
                conn.execute(stmt)
                ddl.append(stmt)
        conn.commit()
        manifest.append({"table": table, "rows": len(rows), "columns": len(final),
                         "source": path.name, "size_mb": f"{size_mb:.1f}",
                         "in_spreadsheet": "yes" if (in_xlsx and len(rows) <= MAX_XLSX_ROWS
                                                     and size_mb <= SIZE_LIMIT_MB) else "no"})
        print(f"  - {table:<26} {len(rows):>9,} rows  {size_mb:>7.1f} MB")

    (DIST / "schema.sql").write_text("\n".join(ddl), encoding="utf-8")
    print(f"\n  wrote dist/cedar_press.db and dist/schema.sql")

    # NAME WHAT DID NOT SHIP. A count with no filenames is how a 0.87% ship
    # rate survived twenty days and roughly twenty builds.
    if undocumented:
        shipped = sum(m["rows"] for m in manifest)
        missed = 0
        print(f"\n  NOT PUBLISHED - {len(undocumented)} clean table(s) with no "
              f"codebook block at >={CB.MATCH_THRESHOLD:.2f}:")
        for p, g, s in sorted(undocumented, key=lambda r: -r[2]):
            try:
                with open(p, encoding="utf-8-sig", errors="replace",
                          newline="") as fh:
                    n = sum(1 for _ in csv.reader(fh)) - 1
            except OSError:
                n = 0
            missed += max(n, 0)
            print(f"     {s:4.2f}  {p.name:46s} {n:>8,} rows   "
                  f"best block: {g}")
        tot = shipped + missed
        print(f"\n  SHIP RATE: {shipped:,} of {tot:,} rows "
              f"({(shipped / tot * 100) if tot else 0:.1f}%) reached the "
              f"database.")

    # ---- sanity ----------------------------------------------------------
    print("\n[2] Sanity checks")
    checks = sanity(conn)
    fails = [c for c in checks if c[1] == "FAIL"]
    for name, status, val, note in checks:
        mark = {"PASS": "ok  ", "FAIL": "FAIL", "SKIP": "skip"}[status]
        print(f"  {mark}  {name:<52} {val}")

    lines = [f"# Cedar Press — Sanity Checks", "", f"*Run {TODAY}.*", "",
             f"**{len(checks) - len(fails)} of {len(checks)} passed.**", "",
             "| Check | Result | Count | Why it matters |", "|---|---|---:|---|"]
    for name, status, val, note in checks:
        lines.append(f"| {name} | **{status}** | {val} | {note} |")
    lines += ["", "## Table manifest", "",
              "| Table | Rows | Cols | Source | Size | In spreadsheet |",
              "|---|---:|---:|---|---:|---|"]
    for m in manifest:
        lines.append(f"| `{m['table']}` | {m['rows']:,} | {m['columns']} | "
                     f"{m['source']} | {m['size_mb']} MB | {m['in_spreadsheet']} |")
    lines += ["", "## Notes", "",
              "- Tables marked *no* under **In spreadsheet** are too large for Excel. They "
              "ship in `cedar_press.db` and as CSV under `data/clean/`.",
              "- The published view excludes `pre_2000_flag = 1` and anything not tier A.",
              "- `schema.sql` loads into Postgres or DuckDB unchanged; all columns are TEXT "
              "so no source value is coerced or lost. Cast at query time."]
    (DIST / "SANITY_CHECKS.md").write_text("\n".join(lines), encoding="utf-8")

    # ---- spreadsheet -----------------------------------------------------
    print("\n[3] Master spreadsheet")
    try:
        import xlsxwriter
    except ImportError:
        print("  xlsxwriter missing - skipping")
        conn.close()
        return 1

    xl = DIST / "cedar_press_master.xlsx"
    wb = xlsxwriter.Workbook(str(xl), {"constant_memory": True})
    hdr = wb.add_format({"bold": True, "bg_color": "#1F3B5C", "font_color": "white",
                         "border": 1, "text_wrap": True, "valign": "top"})
    title = wb.add_format({"bold": True, "font_size": 14})
    warn = wb.add_format({"font_color": "#8C2A2A", "bold": True})

    ws = wb.add_worksheet("README")
    ws.set_column(0, 0, 30)
    ws.set_column(1, 1, 96)
    r = 0
    ws.write(r, 0, "Cedar Press — Master Data", title); r += 2
    for k, v in [
        ("Generated", TODAY),
        ("Database", "cedar_press.db (SQLite) — every table, including the large ones"),
        ("Schema", "schema.sql — loads into Postgres / DuckDB unchanged"),
        ("Sanity checks", f"SANITY_CHECKS.md — {len(checks)-len(fails)}/{len(checks)} passed"),
        ("Published view", "confidence_tier = 'A' AND pre_2000_flag <> '1'"),
        ("Temporal floor", "2000. Pre-2000 rows retained and flagged, not deleted."),
        ("Attribution rule", "Only tier A publishes. Rulings are the only promotion path."),
        ("Not included here", "Transaction-level tables >60 MB — see the database"),
    ]:
        ws.write(r, 0, k, hdr); ws.write(r, 1, v); r += 1
    r += 1
    ws.write(r, 0, "Sheet", hdr); ws.write(r, 1, "Rows", hdr); r += 1
    sheet_index = r

    written = 0
    # EXCEL TRUNCATES A SHEET NAME TO 31 CHARACTERS, so two tables that agree
    # on their first 31 characters collide and xlsxwriter raises
    # DuplicateWorksheetName - AFTER the database has been written, aborting
    # the run at its last step. The DB columns are already de-duplicated a few
    # hundred lines above; the sheet names were not, and the same idea is
    # needed here. Found 2026-08-26 on
    # `individual_native_firm_contracts` vs
    # `individual_native_firm_contracts_published`, which share their first 32.
    # Names are NOT shortened to dodge this: a table name is a published fact
    # and the citation string in the product repo is generated from the
    # descriptor, so it must stay honest rather than convenient.
    sheet_used = {"readme"}

    def sheet_name(table):
        base = table[:31]
        if base.lower() not in sheet_used:
            sheet_used.add(base.lower())
            return base
        for i in range(2, 100):
            suffix = f"~{i}"
            alt = table[:31 - len(suffix)] + suffix
            if alt.lower() not in sheet_used:
                sheet_used.add(alt.lower())
                print(f"    [sheet] {table} -> {alt} (31-char collision)")
                return alt
        raise SystemExit(f"cannot name a worksheet for {table}")

    for m in manifest:
        if m["in_spreadsheet"] != "yes":
            continue
        table = m["table"]
        cur = conn.execute(f"SELECT * FROM {table}")
        cols = [d[0] for d in cur.description]
        sh = wb.add_worksheet(sheet_name(table))
        for c, name in enumerate(cols):
            sh.write(0, c, name, hdr)
        sh.freeze_panes(1, 0)
        sh.autofilter(0, 0, 0, len(cols) - 1)
        n = 0
        for i, row in enumerate(cur, start=1):
            for c, v in enumerate(row):
                if v is not None and v != "":
                    sh.write_string(i, c, str(v)[:1000])
            n = i
        ws.write(sheet_index, 0, table); ws.write(sheet_index, 1, n)
        sheet_index += 1
        written += 1
        print(f"  - {table:<26} {n:>9,} rows")

    if fails:
        ws.write(sheet_index + 1, 0, "SANITY FAILURES", warn)
        for f in fails:
            sheet_index += 1
            ws.write(sheet_index + 1, 1, f"{f[0]} — {f[2]}", warn)

    wb.close()
    conn.close()
    mb = xl.stat().st_size / 1024 / 1024
    print(f"\n  wrote dist/cedar_press_master.xlsx  ({written} sheets, {mb:.1f} MB)")

    print("\n=== SUMMARY ===")
    print(f"  tables in database : {len(manifest)}")
    print(f"  sheets in workbook : {written}")
    print(f"  sanity             : {len(checks)-len(fails)}/{len(checks)} passed")
    if fails:
        print("\n  FAILURES:")
        for f in fails:
            print(f"    - {f[0]}: {f[2]}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
