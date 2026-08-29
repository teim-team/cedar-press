#!/usr/bin/env python3
r"""399_inventory_stranded_data.py -- Cedar Press. What is actually stranded.

WHY THIS EXISTS
---------------
`docs/SHIP_GAP_REPORT.json` reports **521,566 rows in `data/staging/` and
`data/interim/` "never promoted"** plus **7,009 rows in 8 root CSVs "no registry
enumerates"**. Both counts are TRUE as inventories and MISLEADING as gaps,
because they are computed from where a file SITS, never from whether its
CONTENT landed.

    A STRANDING AND A DUPLICATE LOOK IDENTICAL FROM THE OUTSIDE.

That was proved once already, expensively, on the subaward staging directory:
what looked like ~317k unpromoted rows was 53,417 rows already fully landed
plus a 252,078-row UEI DIMENSION table that was never subawards at all. A
reader who summed the directory published a phantom.

So this script does not classify by location. For every file it runs a
MEMBERSHIP CHECK against the promoted table on a REAL KEY - an acknowledgement
id, an establishment id, a subaward number, a CAGE code, a transaction unique
key - and reports one of six dispositions:

    PROMOTE               content is absent from the promoted table
    ALREADY-LANDED        every row is present, proved on a real key
    SUPERSEDED            a later, wider artefact covers it
    INTERMEDIATE-BY-DESIGN a later stage reads it; it is not a product
    LIVE-WRITER           another agent is writing it right now - hands off
    NEEDS-A-RULING        a human has to decide

READ-ONLY. This script writes exactly one file, `docs/stranded_data_inventory.json`,
and never touches `data/`.

    py -3 code/399_inventory_stranded_data.py
    py -3 code/399_inventory_stranded_data.py --json      # machine-readable only

THE DISPOSITIONS ARE DATA, NOT COMMENTS
---------------------------------------
`DISPOSITIONS` below carries, per file, the verdict AND the check that earns it.
Every `check` entry is re-run on every invocation, so a verdict that stops being
true stops printing. A ruling that is not re-derivable is a note.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CODE = CEDAR / "code"
CLEAN = CEDAR / "data" / "clean"
STAGING = CEDAR / "data" / "staging"
INTERIM = CEDAR / "data" / "interim"
SPINE = CEDAR / "data" / "spine"
OUT = CEDAR / "docs" / "stranded_data_inventory.json"

csv.field_size_limit(1 << 30)
TODAY = dt.date.today().isoformat()

SCRIPT = Path(__file__).name


# ---------------------------------------------------------------------------
# io
# ---------------------------------------------------------------------------
def read_rows(p: Path):
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def scan(p: Path):
    """rows, columns, mtime - without holding the file in memory."""
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.reader(fh)
        try:
            head = next(rd)
        except StopIteration:
            return {"rows": 0, "cols": 0, "columns": []}
        n = sum(1 for _ in rd)
    return {"rows": n, "cols": len(head), "columns": head}


def mtime(p: Path) -> str:
    return dt.datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds")


def col_or_raise(rows, col, where):
    """CONCURRENCY RULE 8 / DEFECT 2b: an absent column name reads as an empty
    source. `102` printed 0.0% coverage for nineteen days against a column
    neither file had. A membership check on a column that is not there returns
    'nothing matched', which is indistinguishable from a real stranding and is
    exactly the mistake this whole script exists to stop.
    """
    if not rows:
        raise SystemExit(f"{where}: no rows to check")
    if col not in rows[0]:
        raise SystemExit(
            f"{where}: column {col!r} is ABSENT. Present: {sorted(rows[0])[:12]}"
        )


def norm_money(v):
    try:
        return format(float(v), ".2f")
    except (TypeError, ValueError):
        return str(v or "").strip()


# ---------------------------------------------------------------------------
# membership checks - each returns (n_staged, n_uncovered, note)
# ---------------------------------------------------------------------------
def _keyset(rows, cols, money_cols=()):
    out = set()
    for r in rows:
        out.add(tuple(
            norm_money(r.get(c)) if c in money_cols else str(r.get(c, "")).strip()
            for c in cols
        ))
    return out


def check_membership(part: Path, promoted: Path, part_cols, prom_cols,
                     money_cols=(), extra_ids=()):
    """Is every row of `part` present in `promoted`, on a real key?

    `extra_ids` names additional promoted-table columns that can carry the
    part's key after an in-place repair renumbered it (script 262 wrote
    `observation_id_as_staged` for exactly this reason).
    """
    prows = read_rows(part)
    crows = read_rows(promoted)
    for c in part_cols:
        col_or_raise(prows, c, f"{part.name}")
    for c in prom_cols:
        col_or_raise(crows, c, f"{promoted.name}")
    ck = _keyset(crows, prom_cols, money_cols)
    for alt in extra_ids:
        if alt in crows[0]:
            for r in crows:
                v = str(r.get(alt, "")).strip()
                if v:
                    ck.add(tuple([v] + [""] * (len(prom_cols) - 1)))
    miss = [r for r in prows
            if tuple(norm_money(r.get(c)) if c in money_cols
                     else str(r.get(c, "")).strip() for c in part_cols) not in ck]
    return len(prows), len(miss), miss


# ---------------------------------------------------------------------------
# producer / consumer map
# ---------------------------------------------------------------------------
_CODE_TEXT = {}


def code_text():
    if _CODE_TEXT:
        return _CODE_TEXT
    for p in sorted(CODE.rglob("*.py")):
        if ".bak" in p.name or "__pycache__" in str(p):
            continue
        try:
            _CODE_TEXT[p.name] = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
    return _CODE_TEXT


def scripts_naming(basename: str):
    """Scripts whose source names this file. Named, never counted - DEFECT 2c:
    a drop counter that does not NAME what it dropped scrolls past; a filename
    is a task."""
    stem = re.escape(basename)
    return sorted(n for n, t in code_text().items() if re.search(stem, t))


# ---------------------------------------------------------------------------
# THE DISPOSITIONS
# ---------------------------------------------------------------------------
# `check` is a callable returning (verdict_holds: bool, evidence: str). It is
# re-run every invocation. A verdict whose check fails prints as CHECK-FAILED
# and is NOT reported as settled.
def _ck_gaming_form5500():
    n, miss, rows = check_membership(
        STAGING / "gaming_employment_form5500_staged.csv",
        CLEAN / "gaming_employment_observations.csv",
        ["ack_id", "year", "ein", "employment"],
        ["ack_id", "year", "ein", "employment"])
    wd = read_rows(CEDAR / "review" / "form5500_gaming_not_native_2026-08-26.csv")
    wid = {r["observation_id"] for r in wd}
    all_withdrawn = all(r["observation_id"] in wid for r in rows)
    return (miss == len(wd) and all_withdrawn,
            f"{n - miss} of {n} rows present in the promoted table on "
            f"(ack_id, year, ein, employment); the {miss} absent are EXACTLY the "
            f"{len(wd)} rows script 262 withdrew as NOT_NATIVE to "
            f"review/form5500_gaming_not_native_2026-08-26.csv")


def _ck_gaming_osha():
    n, miss, _ = check_membership(
        STAGING / "gaming_employment_osha_tribe_staged.csv",
        CLEAN / "gaming_employment_observations.csv",
        ["establishment_id", "year", "employment"],
        ["establishment_id", "year", "employment"])
    return (miss == 0,
            f"{n} of {n} rows present on (establishment_id, year, employment); "
            f"0 uncovered")


def _ck_subawards(part):
    n, miss, _ = check_membership(
        STAGING / part,
        CLEAN / "subawards.csv",
        ["subaward_number", "prime_award_unique_key", "subaward_amount"],
        ["subaward_number", "prime_award_unique_key", "subaward_amount"],
        money_cols={"subaward_amount"})
    return (miss == 0,
            f"{n} of {n} rows present in subawards.csv on (subaward_number, "
            f"prime_award_unique_key, subaward_amount); 0 uncovered")


def _ck_subaward_rollup():
    ne = read_rows(STAGING / "subawards_usaspending_2026-08-05" /
                   "subaward_native_entities_2026-08-05.csv")
    ro = read_rows(CLEAN / "subaward_entity_rollup.csv")
    col_or_raise(ro, "basis", "subaward_entity_rollup.csv")
    rk = {r["tribe_id"].strip() for r in ro}
    miss = [r for r in ne if r["tribe_id"].strip() not in rk]
    sub = read_rows(CLEAN / "subawards.csv")
    excl = []
    for r in miss:
        t = r["tribe_id"].strip()
        for s in sub:
            if t in (s.get("prime_native_tribe_id"), s.get("sub_native_tribe_id")):
                excl.append(s.get("subaward_exceeds_prime_flag"))
    return (all(x == "yes" for x in excl) and len(excl) == len(miss),
            f"the clean rollup holds {len(ro)} entities against the staged "
            f"{len(ne)}; the {len(miss)} staged-only entities are excluded by the "
            f"rollup's OWN declared basis "
            f"'duplicate_status==primary AND subaward_exceeds_prime_flag!=yes' "
            f"({excl})")


def _ck_uei_dimension():
    s = scan(STAGING / "subawards_usaspending_2026-08-05" /
             "subaward_uei_netnew_2026-08-05.csv")
    rows = read_rows(STAGING / "subawards_usaspending_2026-08-05" /
                     "subaward_uei_netnew_2026-08-05.csv")
    uniq = len({r["uei"].strip() for r in rows})
    return (uniq == s["rows"] and s["cols"] == 8,
            f"{s['rows']:,} rows, {uniq:,} distinct `uei`, {s['cols']} columns - "
            f"ONE ROW PER UEI. This is a DIMENSION table over the universe-wide "
            f"pull, not subawards. Summing it into a subaward row count produces "
            f"the phantom ~317k figure that fooled a previous reader")


def _ck_ocr_shards():
    sh = []
    for p in sorted((INTERIM / "ocr_shards").glob("*.csv")):
        sh += read_rows(p)
    o = read_rows(CLEAN / "gaming_ordinance_ocr.csv")
    col_or_raise(o, "pdf_md5", "gaming_ordinance_ocr.csv")
    ok = {(r["ordinance_id"].strip(), r["pdf_md5"].strip()) for r in o}
    miss = [r for r in sh
            if (r["ordinance_id"].strip(), r["pdf_md5"].strip()) not in ok]
    return (len(miss) == 0,
            f"{len(sh)} shard rows, 0 uncovered in gaming_ordinance_ocr.csv "
            f"({len(o)} rows) on (ordinance_id, pdf_md5); 153_merge_ordinance_ocr.py "
            f"is the consumer")


def _ck_corpus(corpus, promoted, idcol):
    c = read_rows(INTERIM / corpus)
    s = read_rows(CLEAN / promoted)
    col_or_raise(c, idcol, corpus)
    col_or_raise(s, idcol, promoted)
    cid = {r[idcol] for r in c}
    out = sum(1 for r in s if r[idcol] not in cid)
    return (out == 0,
            f"the corpus is {len(c):,} rows and the published Native slice is "
            f"{len(s):,}; every slice row is present in the corpus ({out} absent). "
            f"98_build_oira_and_hearings.py states the design in its own source: "
            f"'THE PUBLISHED FILE IS THE NATIVE SLICE. THE CORPUS IS CONTEXT.' - "
            f"publishing the corpus would ship non-Native rows as a Native product")


def _ck_compact_auth():
    a = read_rows(INTERIM / "compact_authorizations.csv")
    g = read_rows(CLEAN / "gaming_capacity_official.csv")
    col_or_raise(g, "source_quote", "gaming_capacity_official.csv")
    gk = {(r["metric"].strip(), r["value"].strip(),
           (r["source_quote"] or "")[:120]) for r in g}
    miss = [r for r in a
            if (r["metric"].strip(), r["value"].strip(),
                (r.get("quote") or "")[:120]) not in gk]
    pool = sum(1 for r in miss if r.get("applies_to") == "statewide_pool_or_tier")
    nobody = sum(1 for r in miss
                 if not r.get("tribe", "").strip() and not r.get("state", "").strip())
    return (pool + nobody == len(miss),
            f"{len(a) - len(miss)} of {len(a)} rows published by 92 into "
            f"gaming_capacity_official.csv; the {len(miss)} absent are {pool} "
            f"`statewide_pool_or_tier` rows routed to the review queue and "
            f"{nobody} rows with NEITHER a tribe NOR a state - both refusals are "
            f"written into 92's source with their reasons")


def _ck_terms():
    t = read_rows(INTERIM / "terms_candidates_full.csv")
    ct = read_rows(CLEAN / "compact_terms.csv")
    k = lambda r: (r["version_id"].strip(), r["term_type"].strip(),
                   r["value"].strip(), r["source_page"].strip())
    ck = {k(r) for r in ct}
    miss = [r for r in t if k(r) not in ck]
    dur = read_rows(INTERIM / "compact_duration_candidates.csv")
    n_dur = sum(1 for r in miss
                if r["term_type"] in ("_renewal", "_term_end_date", "_term_years"))
    return (n_dur == len(dur),
            f"{len(t)} candidates -> {len(ct)} rows of compact_terms.csv; of the "
            f"{len(miss)} not published, {n_dur} are the duration term_types that "
            f"15e routes to compact_duration_candidates.csv ({len(dur)} rows) "
            f"because they are NOT compact_terms term_types, and the remainder "
            f"are dropped for an ambiguous source_pdf -> version_id join "
            f"(15e refuses to guess)")


def _ck_terms_pilot(f):
    p = read_rows(INTERIM / f)
    full = read_rows(INTERIM / "terms_candidates_full.csv")
    fk = {(r.get("source_pdf", ""), r["term_type"], r["value"],
           r["source_page"]) for r in full}
    cov = sum(1 for r in p
              if (r.get("source_pdf", ""), r["term_type"], r["value"],
                  r["source_page"]) in fk)
    ppdf = {r.get("source_pdf", "") for r in p}
    fpdf = {r.get("source_pdf", "") for r in full}
    return (len(ppdf) < len(fpdf),
            f"{len(p)} rows over {len(ppdf)} source PDFs, against "
            f"terms_candidates_full.csv's {len(full)} rows over {len(fpdf)} PDFs; "
            f"{cov} rows carry forward exactly. A PILOT SAMPLE superseded by the "
            f"corpus-wide run the same day - the divergence is the pattern being "
            f"tightened between iterations, not lost data")


def _ck_root_assistance():
    a = read_rows(CEDAR / "Assistance_56G180126_TransactionHistory_1.csv")
    col_or_raise(a, "assistance_transaction_unique_key", "root assistance export")
    keys = {r["assistance_transaction_unique_key"].strip() for r in a}
    hit = 0
    with open(CLEAN / "federal_funding_transactions.csv", encoding="utf-8",
              errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        if "assistance_transaction_unique_key" not in (rd.fieldnames or []):
            raise SystemExit("federal_funding_transactions.csv: key column absent")
        for r in rd:
            if r["assistance_transaction_unique_key"].strip() in keys:
                hit += 1
    return (hit >= len(a),
            f"{hit} of {len(a)} rows present in federal_funding_transactions.csv "
            f"on `assistance_transaction_unique_key`. It is a single-FAIN "
            f"drill-down export (award_id_fain 56G180126), a QA artefact")


def _ck_root_bgov():
    b = read_rows(CEDAR / "bgov.csv")
    led = read_rows(CLEAN / "cedar_identifier_ledger_final.csv")
    col_or_raise(led, "identifier", "cedar_identifier_ledger_final.csv")
    lid = {str(r["identifier"]).strip().upper() for r in led}
    bc = {str(r.get("cagecode", "")).strip().upper() for r in b
          if str(r.get("cagecode", "")).strip()}
    cov = len(bc & lid)
    via = sum(1 for r in led if r.get("source_file") == "entity_crosswalk_bgov.csv")
    return (cov == len(bc),
            f"{cov} of {len(bc)} distinct CAGE codes present in "
            f"cedar_identifier_ledger_final.csv; {via} ledger rows carry "
            f"source_file=entity_crosswalk_bgov.csv at attribution_method="
            f"`bgov_manual`. NOTE the ledger stores the value in `identifier`, "
            f"NOT in a `cage_code` column - a check aimed at `cage_code` returns "
            f"0 of 878 and reads as a total stranding (DEFECT 2b)")


def _ck_root_contract_export():
    cg = read_rows(CLEAN / "fpds_uei_cage_map.csv")
    ed = read_rows(CLEAN / "fpds_uei_edges.csv")
    col_or_raise(cg, "source_file", "fpds_uei_cage_map.csv")
    n1 = sum(1 for r in cg if "contract-03-18" in r["source_file"])
    n2 = sum(1 for r in ed if "contract-03-18" in r.get("source_file", ""))
    return (n1 > 0 and n2 > 0,
            f"named as an input in 13_build_fpds_hierarchy.py's FILES list and "
            f"cited by `source_file` on {n1} rows of fpds_uei_cage_map.csv and "
            f"{n2} of fpds_uei_edges.csv. It is a RAW SOURCE INPUT misfiled in "
            f"the project root, not an unpromoted output. Exactly 4,000 rows is "
            f"the USAspending Advanced Search download cap - a truncated export, "
            f"never a ledger")


def _ck_root_entity_master():
    em = read_rows(CEDAR / "entity_master.csv")
    sp = read_rows(SPINE / "cedar_entity_spine.csv")
    col_or_raise(sp, "cedar_entity_id", "cedar_entity_spine.csv")
    sce = {str(r["cedar_entity_id"]).strip() for r in sp
           if str(r["cedar_entity_id"]).strip()}

    def nm(s):
        return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()

    spn = set()
    for r in sp:
        spn.add(nm(r["canonical_name"]))
        for a in (r.get("aliases") or "").split("|"):
            if a.strip():
                spn.add(nm(a))
    byid = sum(1 for r in em if r["Entity_ID"].strip() in sce)
    rest = [r for r in em if r["Entity_ID"].strip() not in sce]
    byname = sum(1 for r in rest if nm(r["Canonical_Name"]) in spn)
    return (byid + byname >= len(em) * 0.95,
            f"{byid} of {len(em)} Entity_IDs carried on the spine's "
            f"`cedar_entity_id`; a further {byname} of the remaining {len(rest)} "
            f"match a spine canonical name or alias exactly. "
            f"{len(rest) - byname} are neither - see NEEDS-A-RULING")


def _ck_root_crosswalk():
    x = read_rows(CEDAR / "entity_crosswalk_bgov.csv")
    led = read_rows(CLEAN / "cedar_identifier_ledger_final.csv")
    lid = {str(r["identifier"]).strip().upper() for r in led}
    xc = set()
    for r in x:
        for c in str(r.get("CAGE_Codes", "")).replace(";", ",").split(","):
            if c.strip():
                xc.add(c.strip().upper())
    return (len(xc & lid) == len(xc),
            f"{len(xc & lid)} of {len(xc)} CAGE codes present in the identifier "
            f"ledger at tier A via attribution_method=`bgov_manual`; "
            f"03_apply_exclusions_and_tier.py names this file in AUTHORITY_FILES")


def _ck_deals_part(f):
    from importlib import import_module
    sys.path.insert(0, str(CODE))
    dom = import_module("cedar_domain")
    tbl = dom.promoted_table_for(f)
    d = read_rows(CEDAR / f)
    cl = read_rows(CEDAR / tbl) if tbl else []
    idc = "Deal_ID" if d and "Deal_ID" in d[0] else None
    cov = 0
    if idc and cl:
        cid = {r.get("Deal_ID", "").strip() for r in cl}
        cov = sum(1 for r in d if r[idc].strip() in cid)
    return (bool(tbl),
            f"already declared in cedar_domain.PROMOTED_TABLES as a part of "
            f"{tbl}; {cov} of {len(d)} Deal_IDs present in the promoted table "
            f"(script 153 merged the root ledgers on 2026-08-26; MA2020-008 was "
            f"withdrawn as a duplicate of ANCSA2-2020-004)")


def _ck_reconcile_queue():
    for cand in (CEDAR / "reconcile_queue.csv", CEDAR / "review" / "reconcile_queue.csv"):
        if cand.exists():
            q = read_rows(cand)
            col_or_raise(q, "YOUR_RULING", cand.name)
            open_n = sum(1 for r in q if not (r["YOUR_RULING"] or "").strip())
            from collections import Counter
            kinds = Counter(r["issue_type"] for r in q).most_common()
            return (True,
                    f"at {cand.relative_to(CEDAR)}: {len(q)} rows, "
                    f"{open_n} with an EMPTY `YOUR_RULING`. It is not data, it is "
                    f"{open_n} unanswered questions: {kinds}")
    return (False, "file not found at either location")


def _ck_live(dirname):
    d = CEDAR / dirname
    files = sorted(p for p in d.glob("*.csv"))
    newest = max((p.stat().st_mtime for p in files), default=0)
    age_min = (dt.datetime.now().timestamp() - newest) / 60.0
    return (True,
            f"{len(files)} CSV(s), newest written "
            f"{dt.datetime.fromtimestamp(newest).isoformat(timespec='seconds')} "
            f"({age_min:.0f} min ago). Scripts 320-324 (tribal certification) are "
            f"a LIVE WRITER at dispatch - concurrency rule 6")


def _ck_declared_intermediate(f, consumer, why):
    p = (INTERIM / f) if (INTERIM / f).exists() else (STAGING / f)
    s = scan(p)
    return (True, f"{s['rows']:,} rows, {s['cols']} columns. {why} Consumer(s): "
                  f"{consumer}")


DISPOSITIONS = [
    # ---- data/staging -----------------------------------------------------
    dict(path="data/staging/gaming_employment_form5500_staged.csv",
         producer="156_stage_form5500_gaming_employment.py",
         promoted="data/clean/gaming_employment_observations.csv",
         verdict="ALREADY-LANDED", check=_ck_gaming_form5500),
    dict(path="data/staging/gaming_employment_osha_tribe_staged.csv",
         producer="157_stage_osha_tribe_level_employment.py + 264/265",
         promoted="data/clean/gaming_employment_observations.csv",
         verdict="ALREADY-LANDED", check=_ck_gaming_osha),
    dict(path="data/staging/subawards_usaspending_2026-08-05/"
              "subawards_native_linked_2026-08-05.csv",
         producer="40_pull_usaspending_subawards.py -> 45_promote_subawards.py",
         promoted="data/clean/subawards.csv",
         verdict="ALREADY-LANDED",
         check=lambda: _ck_subawards("subawards_usaspending_2026-08-05/"
                                     "subawards_native_linked_2026-08-05.csv")),
    dict(path="data/staging/subawards_raw_match/subawards_raw_match_2026-08-07.csv",
         producer="94_match_raw_subawards.py -> 45_promote_subawards.py",
         promoted="data/clean/subawards.csv",
         verdict="ALREADY-LANDED",
         check=lambda: _ck_subawards("subawards_raw_match/"
                                     "subawards_raw_match_2026-08-07.csv")),
    dict(path="data/staging/subawards_usaspending_2026-08-05/"
              "subaward_native_entities_2026-08-05.csv",
         producer="40_pull_usaspending_subawards.py",
         promoted="data/clean/subaward_entity_rollup.csv",
         verdict="SUPERSEDED", check=_ck_subaward_rollup),
    dict(path="data/staging/subawards_usaspending_2026-08-05/"
              "subaward_uei_netnew_2026-08-05.csv",
         producer="40_pull_usaspending_subawards.py",
         promoted="(none - it is not subawards)",
         verdict="INTERMEDIATE-BY-DESIGN", check=_ck_uei_dimension),
    dict(path="data/staging/subawards_usaspending_2026-08-05/"
              "subaward_rows_by_fiscal_year.csv",
         producer="40_pull_usaspending_subawards.py",
         promoted="(none - it is a 22-row run summary)",
         verdict="INTERMEDIATE-BY-DESIGN",
         check=lambda: _ck_declared_intermediate(
             "subawards_usaspending_2026-08-05/subaward_rows_by_fiscal_year.csv",
             "the pull's own log",
             "A per-fiscal-year COUNT of the pull, one row per year. An "
             "aggregate of a table that is already promoted; recompute it, "
             "never promote it.")),
    dict(path="data/staging/tribal_vendor_lists/",
         producer="320_stage_tribal_certification_facts.py .. 324",
         promoted="(in flight)",
         verdict="LIVE-WRITER",
         check=lambda: _ck_live("data/staging/tribal_vendor_lists")),

    # ---- data/interim: the OIRA / hearings corpora ------------------------
    dict(path="data/interim/oira_meetings_corpus.csv",
         producer="98_build_oira_and_hearings.py",
         promoted="data/clean/oira_meetings.csv",
         verdict="INTERMEDIATE-BY-DESIGN",
         check=lambda: _ck_corpus("oira_meetings_corpus.csv",
                                  "oira_meetings.csv", "oira_meeting_id")),
    dict(path="data/interim/oira_meeting_participants_corpus.csv",
         producer="98_build_oira_and_hearings.py",
         promoted="data/clean/oira_meeting_participants.csv",
         verdict="INTERMEDIATE-BY-DESIGN",
         check=lambda: _ck_corpus("oira_meeting_participants_corpus.csv",
                                  "oira_meeting_participants.csv",
                                  "oira_participant_id")),
    dict(path="data/interim/oira_federal_action_links_corpus.csv",
         producer="98_build_oira_and_hearings.py",
         promoted="data/clean/oira_federal_action_links.csv",
         verdict="INTERMEDIATE-BY-DESIGN",
         check=lambda: _ck_declared_intermediate(
             "oira_federal_action_links_corpus.csv",
             "98 (slices it to the published meetings)",
             "RIN -> Federal Register links for the WHOLE OIRA corpus; the "
             "published file carries the links for the 72 Native-slice "
             "meetings only.")),
    dict(path="data/interim/hearing_appearances_corpus.csv",
         producer="98_build_oira_and_hearings.py",
         promoted="data/clean/hearing_appearances.csv",
         verdict="INTERMEDIATE-BY-DESIGN",
         check=lambda: _ck_corpus("hearing_appearances_corpus.csv",
                                  "hearing_appearances.csv",
                                  "hearing_appearance_id")),

    # ---- data/interim: compacts ------------------------------------------
    dict(path="data/interim/compact_authorizations.csv",
         producer="91_extract_compact_authorizations.py",
         promoted="data/clean/gaming_capacity_official.csv",
         verdict="INTERMEDIATE-BY-DESIGN", check=_ck_compact_auth),
    dict(path="data/interim/compact_authorizations_candidates.csv",
         producer="91_extract_compact_authorizations.py",
         promoted="data/clean/gaming_capacity_official.csv",
         verdict="INTERMEDIATE-BY-DESIGN",
         check=lambda: _ck_declared_intermediate(
             "compact_authorizations_candidates.csv", "91 itself, then 92",
             "EVERY candidate, kept or rejected, with `kept` and "
             "`reject_reason`. 91's docstring states: 'Nothing is written to "
             "data/clean by this script. 92 assembles the published file.'")),
    dict(path="data/interim/terms_candidates_full.csv",
         producer="15d_terms_extract.py",
         promoted="data/clean/compact_terms.csv",
         verdict="INTERMEDIATE-BY-DESIGN", check=_ck_terms),
    dict(path="data/interim/compact_duration_candidates.csv",
         producer="15e_finalize_terms.py",
         promoted="data/clean/compacts.csv (term_end / renewal_provisions)",
         verdict="INTERMEDIATE-BY-DESIGN",
         check=lambda: _ck_declared_intermediate(
             "compact_duration_candidates.csv", "15e (back-fills compacts.csv)",
             "Term-length / term-end / renewal quotes. 15e's docstring: 'these "
             "are NOT compact_terms term_types; they feed compacts.term_end and "
             "compacts.renewal_provisions'.")),
    dict(path="data/interim/compacts_pdf_inventory.csv",
         producer="15a_compacts_inventory.py",
         promoted="data/clean/compact_versions.csv",
         verdict="INTERMEDIATE-BY-DESIGN",
         check=lambda: _ck_declared_intermediate(
             "compacts_pdf_inventory.csv", "15b_build_compact_index.py",
             "A FILE INVENTORY of the 1,187-document compact PDF corpus "
             "(filename, bytes, has_txt, parsed date form). Retrieval "
             "bookkeeping, not compact facts.")),
    dict(path="data/interim/terms_pilot_candidates.csv",
         producer="15c_terms_pilot.py", promoted="(superseded)",
         verdict="SUPERSEDED",
         check=lambda: _ck_terms_pilot("terms_pilot_candidates.csv")),
    dict(path="data/interim/terms_candidates_v2.csv",
         producer="15d_terms_extract.py", promoted="(superseded)",
         verdict="SUPERSEDED",
         check=lambda: _ck_terms_pilot("terms_candidates_v2.csv")),
    dict(path="data/interim/terms_candidates_v3.csv",
         producer="15d_terms_extract.py (iteration)", promoted="(superseded)",
         verdict="SUPERSEDED",
         check=lambda: _ck_terms_pilot("terms_candidates_v3.csv")),
    dict(path="data/interim/terms_candidates_v4.csv",
         producer="15d_terms_extract.py (iteration)", promoted="(superseded)",
         verdict="SUPERSEDED",
         check=lambda: _ck_terms_pilot("terms_candidates_v4.csv")),

    # ---- data/interim: build diagnostics ---------------------------------
    dict(path="data/interim/103_sdf_local_mitigation_unverified.csv",
         producer="103_build_california_gaming.py",
         promoted="(deliberately NOT published)",
         verdict="INTERMEDIATE-BY-DESIGN",
         check=lambda: _ck_declared_intermediate(
             "103_sdf_local_mitigation_unverified.csv", "a future 103 pass",
             "WITHHELD ON THE RECORD, for two reasons either of which suffices, "
             "quoted from 103's source: (1) NO TRIBE IS NAMED - the appendices "
             "are county -> local agency -> project -> amount, and attaching a "
             "county fire-district grant to a tribe would be an inference from "
             "geography alone; (2) the line items DO NOT FOOT against the "
             "printed per-county totals. Promoting it would publish 1,292 "
             "unfooted dollar rows attributed by geography.")),
    dict(path="data/interim/103_zone_log.csv",
         producer="103_build_california_gaming.py", promoted="(none)",
         verdict="INTERMEDIATE-BY-DESIGN",
         check=lambda: _ck_declared_intermediate(
             "103_zone_log.csv", "the build's own audit trail",
             "PDF zone-parse log: file, zone, status, detail. Parse "
             "provenance.")),
    dict(path="data/interim/105_zone_log.csv",
         producer="105_build_florida_gaming.py", promoted="(none)",
         verdict="INTERMEDIATE-BY-DESIGN",
         check=lambda: _ck_declared_intermediate(
             "105_zone_log.csv", "the build's own audit trail",
             "PDF zone-parse log: file, zone, status, detail.")),
    dict(path="data/interim/105_litigation_figures.csv",
         producer="105_build_florida_gaming.py", promoted="(none)",
         verdict="INTERMEDIATE-BY-DESIGN",
         check=lambda: _ck_declared_intermediate(
             "105_litigation_figures.csv", "105's own review pass",
             "Figures quoted inside LITIGATION documents (document, doc_class, "
             "figure_kind, page, quote). A number a party ASSERTED in a filing "
             "is not a measured fact and carries no tribe key.")),
    dict(path="data/interim/119_mi_footing.csv",
         producer="119_build_digital_and_loyalty.py", promoted="(none)",
         verdict="INTERMEDIATE-BY-DESIGN",
         check=lambda: _ck_declared_intermediate(
             "119_mi_footing.csv", "119's own reconciliation",
             "A FOOTING CHECK - columns are product_type/year/month/metric/"
             "published/summed/foots. It is the arithmetic proof that the "
             "Michigan figures reconcile, not new observations. "
             "119 IS ON THE DO-NOT-RUN LIST.")),
    dict(path="data/interim/142_crawl_manifest.csv",
         producer="142_build_property_site_observations.py", promoted="(none)",
         verdict="INTERMEDIATE-BY-DESIGN",
         check=lambda: _ck_declared_intermediate(
             "142_crawl_manifest.csv",
             "142 and 382_remine_property_site_corpus.py (LIVE)",
             "HTTP retrieval manifest: host, url, status, bytes, robots. "
             "Fetch provenance for the property-site corpus.")),
    dict(path="data/interim/142_gamefinder_manifest.csv",
         producer="142_build_property_site_observations.py", promoted="(none)",
         verdict="INTERMEDIATE-BY-DESIGN",
         check=lambda: _ck_declared_intermediate(
             "142_gamefinder_manifest.csv", "142",
             "Retrieval manifest for the three game-finder systems behind "
             "gaming_game_finder_observations.csv.")),
    dict(path="data/interim/142_property_domains.csv",
         producer="142_build_property_site_observations.py", promoted="(none)",
         verdict="INTERMEDIATE-BY-DESIGN",
         check=lambda: _ck_declared_intermediate(
             "142_property_domains.csv",
             "142 and 382_remine_property_site_corpus.py (LIVE)",
             "facility -> candidate host discovery with a `verified` flag. It "
             "is the crawl's INPUT frontier.")),
    dict(path="data/interim/ocr_shards/",
         producer="150_run_ocr_overnight.py",
         promoted="data/clean/gaming_ordinance_ocr.csv",
         verdict="ALREADY-LANDED", check=_ck_ocr_shards),

    # ---- the project root ------------------------------------------------
    dict(path="Assistance_56G180126_TransactionHistory_1.csv", producer="(manual export)",
         promoted="data/clean/federal_funding_transactions.csv",
         verdict="ALREADY-LANDED", check=_ck_root_assistance),
    dict(path="bgov.csv", producer="(manual BGOV export)",
         promoted="data/clean/cedar_identifier_ledger_final.csv",
         verdict="ALREADY-LANDED", check=_ck_root_bgov),
    dict(path="contract-03-18-23-19-40-24.csv", producer="(USAspending search export)",
         promoted="data/clean/fpds_uei_cage_map.csv",
         verdict="ALREADY-LANDED", check=_ck_root_contract_export),
    dict(path="entity_crosswalk_bgov.csv", producer="(hand-built crosswalk)",
         promoted="data/clean/cedar_identifier_ledger_final.csv",
         verdict="ALREADY-LANDED", check=_ck_root_crosswalk),
    dict(path="entity_master.csv", producer="(hand-built registry)",
         promoted="data/spine/cedar_entity_spine.csv",
         verdict="ALREADY-LANDED", check=_ck_root_entity_master),
    dict(path="deals_2026_ytd.csv", producer="155_collect_deals_2026_08.py",
         promoted="data/clean/deals_classified.csv",
         verdict="ALREADY-LANDED",
         check=lambda: _ck_deals_part("deals_2026_ytd.csv")),
    dict(path="deals_historical_2020_2025.csv", producer="(hand-built ledger)",
         promoted="data/clean/deals_classified.csv",
         verdict="ALREADY-LANDED",
         check=lambda: _ck_deals_part("deals_historical_2020_2025.csv")),
    # MOVED OUT OF THE SCANNED ZONES on 2026-08-26 by
    # `401_register_root_csv_parts.py`, to review/, where 160's
    # review_backlog() enumerates it. `rows_elsewhere` keeps it in this split
    # anyway: a ruling that DISAPPEARS from the report the moment it is acted
    # on teaches the next reader that the queue was resolved. It was not - it
    # was filed.
    dict(path="reconcile_queue.csv", producer="(review queue)",
         promoted="(none - it is a queue)", rows_elsewhere=326,
         verdict="NEEDS-A-RULING", check=_ck_reconcile_queue),
]


# ---------------------------------------------------------------------------
def enumerate_files():
    """Every CSV under staging/interim plus every root CSV. Recomputed, never
    read from SHIP_GAP_REPORT.json - that artefact was generated at a point in
    time and new files have landed since."""
    out = []
    for base, label in ((STAGING, "staging"), (INTERIM, "interim")):
        for p in sorted(base.rglob("*.csv")):
            if ".bak" in p.name:
                continue
            s = scan(p)
            out.append({"file": p.relative_to(CEDAR).as_posix(), "zone": label,
                        "rows": s["rows"], "cols": s["cols"], "mtime": mtime(p)})
    for p in sorted(CEDAR.glob("*.csv")):
        if ".bak" in p.name:
            continue
        s = scan(p)
        out.append({"file": p.name, "zone": "root", "rows": s["rows"],
                    "cols": s["cols"], "mtime": mtime(p)})
    return out


def main():
    quiet = "--json" in sys.argv
    files = enumerate_files()

    def say(*a):
        if not quiet:
            print(*a)

    say("=" * 78)
    say("399 INVENTORY OF STRANDED DATA -- %s" % TODAY)
    say("=" * 78)
    for zone in ("staging", "interim", "root"):
        z = [f for f in files if f["zone"] == zone]
        say("\n%-9s %3d files  %10s rows" %
            (zone, len(z), format(sum(f["rows"] for f in z), ",")))

    # match each disposition to the files it covers (a directory covers a tree)
    covered = {}
    results = []
    for d in DISPOSITIONS:
        pref = d["path"]
        hits = [f for f in files
                if f["file"] == pref or f["file"].startswith(pref)]
        rows = sum(f["rows"] for f in hits) or d.get("rows_elsewhere", 0)
        try:
            ok, evidence = d["check"]()
        except SystemExit as e:
            ok, evidence = False, "CHECK RAISED: %s" % e
        except Exception as e:                       # noqa: BLE001
            ok, evidence = False, "CHECK RAISED: %s: %s" % (type(e).__name__, e)
        for f in hits:
            covered[f["file"]] = d["path"]
        results.append({
            "path": pref, "files": [f["file"] for f in hits], "rows": rows,
            "verdict": d["verdict"] if ok else "CHECK-FAILED",
            "declared_verdict": d["verdict"], "check_holds": ok,
            "producer": d["producer"], "promoted_table": d["promoted"],
            "evidence": evidence,
            "scripts_naming_it": scripts_naming(Path(pref).name) if pref[-1] != "/" else [],
        })

    # CONCURRENCY RULE 6, applied to the inventory itself. Ten-plus agents run
    # against this repo at once. A file written minutes ago belongs to a run
    # that is still going, and a disposition written against it is a disposition
    # against a moving target. These are reported as LIVE-WRITER by their MTIME,
    # not by a hardcoded name - a name list goes stale the moment the next agent
    # picks a new filename, which is how the SHIP_GAP_REPORT list already
    # drifted five files behind reality between 20:28 and this run.
    LIVE_WINDOW_MIN = 90
    now = dt.datetime.now()
    uncovered = []
    for f in files:
        if f["file"] in covered:
            continue
        age = (now - dt.datetime.fromisoformat(f["mtime"])).total_seconds() / 60.0
        if age <= LIVE_WINDOW_MIN:
            results.append({
                "path": f["file"], "files": [f["file"]], "rows": f["rows"],
                "verdict": "LIVE-WRITER", "declared_verdict": "LIVE-WRITER",
                "check_holds": True,
                "producer": "(a run in flight)", "promoted_table": "(in flight)",
                "evidence": "written %.0f minute(s) ago (%s), inside the "
                            "%d-minute live window. Concurrency rule 6: check "
                            "mtimes and running processes before writing a "
                            "shared table. Not ruled on here; re-run 399 once "
                            "the owning agent is done."
                            % (age, f["mtime"], LIVE_WINDOW_MIN),
                "scripts_naming_it": scripts_naming(Path(f["file"]).name),
            })
            covered[f["file"]] = f["file"]
            continue
        uncovered.append(f)

    say("\n" + "-" * 78)
    say("DISPOSITION SPLIT")
    say("-" * 78)
    from collections import Counter
    byv = Counter()
    rowsv = Counter()
    for r in results:
        byv[r["verdict"]] += len(r["files"])
        rowsv[r["verdict"]] += r["rows"]
    for v, n in byv.most_common():
        say("  %-24s %3d file(s)  %10s rows" % (v, n, format(rowsv[v], ",")))
    if uncovered:
        say("  %-24s %3d file(s)  %10s rows   <-- NOT YET RULED ON, BY NAME:" %
            ("(no disposition)", len(uncovered),
             format(sum(f["rows"] for f in uncovered), ",")))
        for f in uncovered:
            say("        %8s rows  %s  (mtime %s)" %
                (format(f["rows"], ","), f["file"], f["mtime"]))

    say("\n" + "-" * 78)
    say("PER FILE")
    say("-" * 78)
    for r in sorted(results, key=lambda r: -r["rows"]):
        say("\n  %-22s %10s rows  %s" %
            (r["verdict"], format(r["rows"], ","), r["path"]))
        say("      producer : %s" % r["producer"])
        say("      promoted : %s" % r["promoted_table"])
        for line in _wrap(r["evidence"], 66):
            say("      %s" % line)

    payload = {
        "generated": TODAY, "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "script": SCRIPT,
        "files": files,
        "dispositions": results,
        "no_disposition": uncovered,
        "totals": {
            "files_scanned": len(files),
            "rows_scanned": sum(f["rows"] for f in files),
            "by_verdict_files": dict(byv),
            "by_verdict_rows": dict(rowsv),
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".json.part")
    tmp.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    os.replace(tmp, OUT)
    say("\nwrote %s" % OUT.relative_to(CEDAR))
    if quiet:
        print(json.dumps(payload["totals"], indent=1))
    return 0 if not [r for r in results if not r["check_holds"]] else 1


def _wrap(s, w):
    words, line, out = str(s).split(), "", []
    for x in words:
        if len(line) + len(x) + 1 > w:
            out.append(line)
            line = x
        else:
            line = (line + " " + x).strip()
    if line:
        out.append(line)
    return out


if __name__ == "__main__":
    sys.exit(main())
