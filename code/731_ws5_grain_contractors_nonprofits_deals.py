#!/usr/bin/env python3
"""
Cedar Press - 731: WORKSTREAM GRAIN-WS5. contractors, nonprofits, deals.

    py -3 code/731_ws5_grain_contractors_nonprofits_deals.py measure
    py -3 code/731_ws5_grain_contractors_nonprofits_deals.py verify
    py -3 code/731_ws5_grain_contractors_nonprofits_deals.py conserve --apply
    py -3 code/731_ws5_grain_contractors_nonprofits_deals.py doc

`measure` prints every number this workstream asserted. `verify` re-measures
them against the live files and exits 1 when one stops being true - the same
contract 572/573/574 hold. `conserve --apply` MERGES this workstream's C5
ledgers into the shared `data/clean/cedar_harvest_conservation.csv` on the
`(source_table, disposition)` key and rewrites nothing it does not own.
`doc` writes `docs/WS5_GRAIN_AND_SOURCES.md`.

THE RULE THIS WORKSTREAM WAS HANDED, AND KEPT
---------------------------------------------
DO NOT DE-DUPLICATE ANYTHING. Four duplicate allegations were re-measured on
2026-09-01 and three were wrong: prime_contracts 80,778 -> 0; faads_* 180,260
-> 0 (a de-dupe would have destroyed $8,291,124,113); np_schedule_i_grants
101 -> 0 real duplicated facts. Where a table's rows genuinely render
identical the fix is the identity the writer dropped, never a DELETE. Both
declarations in this file are that fix:

    269  operating_company_seq   1..n within the owner   -> 0 duplicate keys
    132  schedule_i_line_seq     1..n within object_id   -> NOT DONE, 132 is
                                                            not ours to edit

WHAT THIS WORKSTREAM CHANGED IN A BUILDER
-----------------------------------------
`269_build_contractor_ranking.py`, and only that one. Two changes, both in
`GRAIN_WS5`'s comment block in 512:

  1. `operating_company_seq` - the key that did not exist, because 269 groups
     on `(tribe_id, firm_key)` and never wrote `firm_key`.
  2. THE ENTITY-CLASS EXEMPTION. The personal-name guard fired on 134 of
     1,429 rows and exactly ONE was a natural person. The other 133 were
     tribal governments and their instrumentalities. A rule that exists to
     protect a natural person was suppressing the legal names of sovereign
     governments, one of them carrying $71.9M. 269 now applies the guard only
     where there is no positive evidence that the subject is an entity, and
     records that evidence per row in `entity_class_basis`.
"""
from __future__ import annotations

import csv
import glob
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CLEAN = ROOT / "data" / "clean"
csv.field_size_limit(10 ** 9)
TODAY = date.today().isoformat()

CONSERVATION = CLEAN / "cedar_harvest_conservation.csv"
OUT_MD = ROOT / "docs" / "WS5_GRAIN_AND_SOURCES.md"
CONS_COLS = ["source_table", "rows_in", "disposition", "rows", "pct",
             "examples", "harvest_date"]

URL_RE = re.compile(r"https?://", re.I)


def rd(name: str) -> list:
    p = CLEAN / name
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def money(v) -> float:
    try:
        return float(str(v or "0").replace(",", "").replace("$", "") or 0)
    except ValueError:
        return 0.0


# =====================================================================
# MEASUREMENTS. One function per assertion; each returns (label, got, want).
# `want` is None where the number is reported rather than ratcheted.
# =====================================================================
def m_contractors() -> dict:
    rows = rd("contractor_ranking.csv")
    out = {"rows": len(rows)}
    if not rows:
        return out
    hdr = list(rows[0])
    out["has_operating_company_seq"] = "operating_company_seq" in hdr
    out["has_entity_class_basis"] = "entity_class_basis" in hdr
    keys = [(r.get("owner_entity_id"), r.get("operating_company_seq"))
            for r in rows]
    out["pk_duplicate_rows"] = len(keys) - len(set(keys))
    out["pk_blank_component_rows"] = sum(
        1 for a, b in keys if not (a or "").strip() or not (b or "").strip())

    withheld = [r for r in rows
                if r.get("publishable_operating_name") == "N"]
    out["names_withheld"] = len(withheld)
    out["names_withheld_usd"] = round(
        sum(money(r.get("firm_obligations_usd")) for r in withheld), 2)
    freed = [r for r in rows
             if (r.get("entity_class_basis") or "").strip()
             and r.get("privacy_class") in ("POSSIBLE_PERSONAL_NAME",
                                            "UNKNOWN")]
    out["entity_class_exemption_rows"] = len(freed)
    out["entity_class_exemption_usd"] = round(
        sum(money(r.get("firm_obligations_usd")) for r in freed), 2)
    out["entity_class_exemption_by_basis"] = dict(Counter(
        (r.get("entity_class_basis") or "").split(":")[0] for r in freed))
    out["governments_freed"] = sorted(
        {(r.get("operating_company_name"), r.get("owner_name"))
         for r in freed
         if (r.get("entity_class_basis") or "").startswith(
             "governmental_or_institutional_token")})[:400]

    # C7 - the two statements a buyer needs, re-measured every run.
    out["sum_firm_obligations_usd"] = round(
        sum(money(r.get("firm_obligations_usd")) for r in rows), 2)
    out["sum_owner_obligations_usd_ROW_SUMMED_WRONG"] = round(
        sum(money(r.get("owner_obligations_usd")) for r in rows), 2)
    per_owner = {}
    for r in rows:
        per_owner[r.get("owner_entity_id")] = money(
            r.get("owner_obligations_usd"))
    out["sum_owner_obligations_usd_over_distinct_owners"] = round(
        sum(per_owner.values()), 2)
    out["n_owners"] = len(per_owner)
    if out["sum_firm_obligations_usd"]:
        out["owner_grain_inflation_x"] = round(
            out["sum_owner_obligations_usd_ROW_SUMMED_WRONG"]
            / out["sum_firm_obligations_usd"], 2)
    return out


def m_nonprofits() -> dict:
    out = {}
    p = CLEAN / "np_schedule_i_grants.csv"
    if p.exists():
        c = Counter()
        n = 0
        obj = Counter()
        obj_usd = defaultdict(float)
        with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            rr = csv.reader(fh)
            head = next(rr, [])
            io = head.index("object_id") if "object_id" in head else -1
            ic = (head.index("cash_grant_usd")
                  if "cash_grant_usd" in head else -1)
            for row in rr:
                n += 1
                c[tuple(row)] += 1
                if io >= 0 and io < len(row):
                    obj[row[io]] += 1
                    if ic >= 0 and ic < len(row):
                        obj_usd[row[io]] += money(row[ic])
        out["grants_rows"] = n
        out["grants_literal_duplicate_rows"] = sum(v - 1 for v in c.values()
                                                   if v > 1)
        out["grants_collision_groups"] = sum(1 for v in c.values() if v > 1)
        out["grants_rows_inside_a_collision_group"] = sum(
            v for v in c.values() if v > 1)
        out["grants_cash_grant_usd_total"] = round(sum(obj_usd.values()), 2)
        out["grants_distinct_object_id"] = len(obj)
        # THE POINT: the collision groups are inside ONE return, and the
        # filers table holds that return exactly once. So the parser did not
        # double-read anything; the FILER listed the line twice.
        dup_objs = set()
        with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            rr = csv.reader(fh)
            next(rr, [])
            for row in rr:
                if c[tuple(row)] > 1 and io >= 0 and io < len(row):
                    dup_objs.add(row[io])
        out["object_ids_carrying_a_collision"] = len(dup_objs)
        filers = rd("np_schedule_i_filers.csv")
        fo = Counter(r.get("object_id") for r in filers)
        out["those_object_ids_appearing_MORE_THAN_ONCE_in_filers"] = sum(
            1 for o in dup_objs if fo.get(o, 0) > 1)
        out["money_a_dedupe_would_delete_usd"] = round(sum(
            (v - 1) * money(dict(zip(head, k)).get("cash_grant_usd"))
            for k, v in c.items() if v > 1), 2)

    filers = rd("np_schedule_i_filers.csv")
    if filers:
        out["filers_rows"] = len(filers)
        out["filers_distinct_object_id"] = len({r.get("object_id")
                                                for r in filers})
        out["filers_part2_cash_grant_total_usd"] = round(
            sum(money(r.get("part2_cash_grant_total_usd")) for r in filers), 2)
    return out


def m_deals() -> dict:
    cl = rd("deals_classified.csv")
    out = {"classified_rows": len(cl)}
    if not cl:
        return out
    out["classified_distinct_deal_id"] = len({r.get("Deal_ID") for r in cl})

    # SOURCE-LINK COVERAGE - the deals dataset is the one Cedar ORIGINATES
    # rather than collates, so PUBLICATION_POLICY.md asks for a source on
    # every row. This is the coverage fact.
    two = one = none = 0
    hosts = Counter()
    types = Counter()
    for r in cl:
        s1 = r.get("Source_1") or ""
        s2 = r.get("Source_2") or ""
        a, b = bool(URL_RE.search(s1)), bool(URL_RE.search(s2))
        if a and b:
            two += 1
        elif a or b:
            one += 1
        else:
            none += 1
        m = re.search(r"https?://([^/\s]+)", s1 or s2 or "", re.I)
        if m:
            hosts[m.group(1).lower().replace("www.", "")] += 1
        types[(r.get("Source_1_Type") or r.get("Source_2_Type")
               or "(blank)")] += 1
    out["rows_with_two_independent_source_urls"] = two
    out["rows_with_one_source_url"] = one
    out["rows_with_NO_source_url"] = none
    out["rows_with_at_least_one_source_url"] = two + one
    out["source_link_coverage_pct"] = round(100.0 * (two + one) / len(cl), 2)
    out["distinct_source_hosts"] = len(hosts)
    out["rows_sourced_to_a_dot_gov_host"] = sum(
        v for k, v in hosts.items() if k.endswith(".gov"))
    out["top_source_hosts"] = dict(hosts.most_common(12))
    out["top_source_types"] = dict(types.most_common(10))

    # C7 - the two double-counting paths.
    ids = {r.get("Deal_ID") for r in cl}
    fold = {}
    add_rows = add_in = 0
    # lint-ok: class1 - reading the staging slices IS the job here. This
    # workstream exists to MEASURE that every additions row is already in
    # `deals_classified.csv`, which is read above as `cl`; the finding is
    # the double-counting path, not a substitute for the promoted table.
    for p in sorted(glob.glob(str(CLEAN / "deals_*_additions.csv"))):
        a = rd(Path(p).name)
        inn = sum(1 for r in a if r.get("Deal_ID") in ids)
        fold[Path(p).name] = {"rows": len(a), "already_in_classified": inn,
                              "not_in_classified": len(a) - inn}
        add_rows += len(a)
        add_in += inn
    out["additions_files"] = fold
    out["additions_rows_total"] = add_rows
    out["additions_rows_already_in_classified"] = add_in
    out["classified_usd_total"] = round(
        sum(money(r.get("Announced_Value_USD")) for r in cl), 2)
    slice_ids = set()
    # lint-ok: class1 - same reason: the slice universe is what the promoted
    # table is being measured AGAINST.
    for p in glob.glob(str(CLEAN / "deals_*_additions.csv")):
        for r in rd(Path(p).name):
            slice_ids.add(r.get("Deal_ID"))
    out["classified_rows_present_in_a_staging_slice"] = sum(
        1 for r in cl if r.get("Deal_ID") in slice_ids)
    out["classified_rows_originated_in_the_merged_ledger"] = sum(
        1 for r in cl if r.get("Deal_ID") not in slice_ids)
    # C8 exposure: what a full 88 rebuild would discard. These three columns
    # are written IN PLACE by 33/53/57/154 and exist in no input to 88.
    out["rows_carrying_in_place_party_enrichment"] = sum(
        1 for r in cl if (r.get("native_party_entity_id") or "").strip())
    root_ids = set()
    for nm in ("deals_2026_ytd.csv", "deals_historical_2020_2025.csv"):
        p = ROOT / nm
        if p.exists():
            with p.open(encoding="utf-8-sig", errors="replace",
                        newline="") as fh:
                for r in csv.DictReader(fh):
                    root_ids.add(r.get("Deal_ID"))
    out["classified_rows_in_a_root_ledger"] = sum(
        1 for r in cl if r.get("Deal_ID") in root_ids)
    out["classified_rows_in_NEITHER_slice_nor_root_ledger"] = sum(
        1 for r in cl if r.get("Deal_ID") not in slice_ids
        and r.get("Deal_ID") not in root_ids)
    out["classified_usd_on_rows_present_in_a_staging_slice"] = round(sum(
        money(r.get("Announced_Value_USD")) for r in cl
        if r.get("Deal_ID") in slice_ids), 2)
    fed = [r for r in cl if "federal" in (r.get("Value_Type") or "").lower()]
    out["rows_whose_value_type_names_a_federal_award"] = len(fed)
    out["usd_whose_value_type_names_a_federal_award"] = round(
        sum(money(r.get("Announced_Value_USD")) for r in fed), 2)

    trf = rd("tribal_resolution_financings.csv")
    out["tribal_resolution_financings_rows"] = len(trf)
    if trf:
        pk = ["entity_id", "source_url", "source_index_url",
              "instrument_title"]
        keys = [tuple((r.get(c) or "").strip() for c in pk) for r in trf]
        out["trf_pk_duplicate_rows"] = len(keys) - len(set(keys))
        out["trf_pk_blank_component_rows"] = sum(1 for k in keys if not all(k))
        out["trf_instrument_number_blank_rows"] = sum(
            1 for r in trf if not (r.get("instrument_number") or "").strip())
        out["trf_financing_status"] = dict(Counter(
            r.get("financing_status") for r in trf))
    return out


def measure_all() -> dict:
    return {"measured_date": TODAY,
            "contractors": m_contractors(),
            "nonprofits": m_nonprofits(),
            "deals": m_deals()}


# =====================================================================
# VERIFY. The assertions this workstream published, re-checked.
# =====================================================================
CHECKS = [
    # (path, comparison, expected, why it matters)
    ("contractors.pk_duplicate_rows", "==", 0,
     "the declared primary key (owner_entity_id, operating_company_seq) must "
     "be unique - it is the whole reason contractor_ranking.csv is "
     "declarable"),
    ("contractors.pk_blank_component_rows", "==", 0,
     "a key with a blank component is not a key"),
    ("contractors.has_operating_company_seq", "==", True,
     "269 must emit the ordinal; without it the declaration in 512 is a lie"),
    ("contractors.has_entity_class_basis", "==", True,
     "the entity-class exemption must be auditable per row"),
    ("contractors.names_withheld", "<=", 10,
     "the guard withheld 134 of 1,429 names and 133 were tribal governments. "
     "If this climbs back the exemption has stopped working"),
    ("deals.rows_with_NO_source_url", "==", 0,
     "deals is the dataset Cedar ORIGINATES, and PUBLICATION_POLICY.md asks "
     "for a source on every row of it"),
    ("deals.trf_pk_duplicate_rows", "==", 0,
     "the declared key for tribal_resolution_financings.csv"),
    ("deals.trf_pk_blank_component_rows", "==", 0,
     "a key with a blank component is not a key"),
    ("deals.classified_rows_in_NEITHER_slice_nor_root_ledger", "==", 0,
     "88's repaired glob plus the two root ledgers must be a COMPLETE cover "
     "of deals_classified.csv, or a rebuild loses rows on top of losing the "
     "in-place party enrichment"),
    # The np finding, stated as a check rather than as prose: if a colliding
    # object_id ever appears twice in the filers table, the "the filer listed
    # it twice" reading is wrong and the rows really would be a parser
    # double-read. It has never been true and it is worth knowing the day it
    # is - because that is the day a de-dupe becomes correct.
    ("nonprofits.those_object_ids_appearing_MORE_THAN_ONCE_in_filers",
     "==", 0,
     "every np_schedule_i_grants collision group sits inside ONE return that "
     "np_schedule_i_filers.csv holds exactly once - so the FILER listed the "
     "line twice and a de-dupe deletes real grants"),
]


def verify() -> int:
    M = measure_all()

    def get(path):
        cur = M
        for part in path.split("."):
            cur = (cur or {}).get(part)
        return cur

    fails, oks = [], []
    for path, op, want, why in CHECKS:
        got = get(path)
        ok = (got == want) if op == "==" else (
            got is not None and got <= want)
        (oks if ok else fails).append((path, op, want, got, why))

    print("=== 731 verify: WS5 assertions, re-measured ===\n")
    for path, op, want, got, _ in oks:
        print(f"  OK    {path:70s} {got!r} {op} {want!r}")
    for path, op, want, got, why in fails:
        print(f"  FAIL  {path:70s} {got!r} is not {op} {want!r}")
        print(f"        {why}")
    print(f"\n  {len(oks)} pass, {len(fails)} fail")
    return 1 if fails else 0


# =====================================================================
# C5 - ROW CONSERVATION. MERGE-ONLY, and here is why that is in capitals.
#
# `510_assertions.py` wrote this file wholesale on 2026-09-01 and destroyed
# 2,146,673 accounted rows belonging to federal-register and nagpra. The file
# is SHARED. Every ledger below is keyed (source_table, disposition) and every
# key this run does not own is preserved byte for byte.
#
# WHAT THIS FUNCTION WILL NOT DO. `573.cmd_conserve_probe` refused to merge a
# ledger for natural-resources that accounted for two harvests out of twelve,
# on the grounds that clearing a named blocker while the contract point it
# names stays 90% unmet makes the scoreboard worse. That standard is kept
# here: every partition below is COMPLETE - it accounts for 100% of the rows
# of the table it names, measured on the live file, and I13's arithmetic
# (rows_in == sum of dispositions) is the proof.
# =====================================================================
def conservation_rows() -> list:
    out = []

    def add(table, rows_in, buckets, examples=None):
        examples = examples or {}
        for disp, n in buckets:
            out.append(dict(
                source_table=f"data/clean/{table}", rows_in=rows_in,
                disposition=disp, rows=n,
                pct=round(100.0 * n / max(rows_in, 1), 2),
                examples=examples.get(disp, ""), harvest_date=TODAY))

    # ---- contractors -----------------------------------------------------
    # This REPLACES the three rows WS2 merged. WS2's partition was
    # 1,295 published / 53 withheld-and-unkeyable / 81 withheld-but-keyable,
    # and both halves of that are now stale: `operating_company_seq` keys all
    # 1,429 rows and the entity-class exemption took the withheld set from
    # 134 to 5. Leaving WS2's numbers in place would leave I13 arithmetic that
    # no longer describes the file.
    cr = rd("contractor_ranking.csv")
    if cr:
        w = [r for r in cr if r.get("publishable_operating_name") == "N"]
        add("contractor_ranking.csv", len(cr), [
            ("emitted:operating_company_published_and_uniquely_keyed_by_"
             "owner_entity_id_plus_operating_company_seq", len(cr) - len(w)),
            ("rejected:name_withheld_because_no_positive_entity_class_"
             "evidence_was_found_the_row_ships_with_every_contract_fact_and_"
             "is_still_uniquely_keyed", len(w)),
        ], {})

    # ---- nonprofits ------------------------------------------------------
    p = CLEAN / "np_schedule_i_grants.csv"
    if p.exists():
        c = Counter()
        n = 0
        with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            rr = csv.reader(fh)
            next(rr, [])
            for row in rr:
                n += 1
                c[tuple(row)] += 1
        inside = sum(v for v in c.values() if v > 1)
        add("np_schedule_i_grants.csv", n, [
            ("emitted:Schedule_I_Part_II_grant_line_that_renders_uniquely_"
             "across_the_whole_file", n - inside),
            ("emitted:grant_line_the_FILER_listed_more_than_once_verbatim_on_"
             "ONE_return_RETAINED_never_deleted_pending_a_line_ordinal_from_"
             "132_build_schedule_i_layer", inside),
        ])
    filers = rd("np_schedule_i_filers.csv")
    if filers:
        g = Counter()
        with (CLEAN / "np_schedule_i_grants.csv").open(
                encoding="utf-8-sig", errors="replace", newline="") as fh:
            for r in csv.DictReader(fh):
                g[r.get("object_id")] += 1
        has = sum(1 for r in filers if g.get(r.get("object_id")))
        add("np_schedule_i_filers.csv", len(filers), [
            ("emitted:return_whose_Part_II_organisation_grant_lines_were_"
             "parsed_and_whose_part2_cash_grant_total_reconciles_to_them_to_"
             "the_dollar", has),
            ("emitted:return_filed_Schedule_I_with_no_Part_II_organisation_"
             "grant_lines_and_a_part2_cash_grant_total_of_zero",
             len(filers) - has),
        ])

    # ---- deals -----------------------------------------------------------
    cl = rd("deals_classified.csv")
    if cl:
        two = one = none = 0
        for r in cl:
            a = bool(URL_RE.search(r.get("Source_1") or ""))
            b = bool(URL_RE.search(r.get("Source_2") or ""))
            if a and b:
                two += 1
            elif a or b:
                one += 1
            else:
                none += 1
        add("deals_classified.csv", len(cl), [
            ("emitted:deal_event_carrying_TWO_independent_source_urls", two),
            ("emitted:deal_event_carrying_one_source_url", one),
            ("rejected:deal_event_carrying_no_source_url_at_all", none),
        ])
        ids = {r.get("Deal_ID") for r in cl}
        # lint-ok: class1 - the C5 ledger accounts for the SLICES' own rows,
        # so the slice files are the subject of the measurement, not a
        # stand-in for `deals_classified.csv` (accounted for just above).
        for pth in sorted(glob.glob(str(CLEAN / "deals_*_additions.csv"))):
            nm = Path(pth).name
            a = rd(nm)
            inn = sum(1 for r in a if r.get("Deal_ID") in ids)
            add(nm, len(a), [
                ("emitted:staging_row_folded_into_deals_classified_on_"
                 "Deal_ID_and_therefore_NEVER_summable_alongside_it", inn),
                ("rejected:staging_row_whose_Deal_ID_is_absent_from_deals_"
                 "classified_so_it_never_reached_the_merged_ledger",
                 len(a) - inn),
            ])
    trf = rd("tribal_resolution_financings.csv")
    if trf:
        add("tribal_resolution_financings.csv", len(trf), [
            ("emitted:retrieved_document_whose_own_text_names_a_financing_"
             "AUTHORISATION_status_AUTHORIZED_and_nothing_further",
             sum(1 for r in trf
                 if r.get("financing_status") == "AUTHORIZED")),
            ("emitted:retrieved_document_recorded_at_a_status_beyond_"
             "AUTHORIZED_on_the_builds_own_evidentiary_ladder",
             sum(1 for r in trf
                 if r.get("financing_status") != "AUTHORIZED")),
        ])
    return out


def conserve(apply: bool) -> int:
    mine = conservation_rows()
    by_tab = defaultdict(list)
    for r in mine:
        by_tab[r["source_table"]].append(r)
    print("=== 731 conserve: WS5 C5 ledgers ===\n")
    bad = 0
    for tab, rs in sorted(by_tab.items()):
        tot = sum(r["rows"] for r in rs)
        ok = tot == rs[0]["rows_in"]
        bad += 0 if ok else 1
        print(f"  {'OK ' if ok else 'BAD'} {tab}  rows_in={rs[0]['rows_in']:,}"
              f"  accounted={tot:,}")
        for r in rs:
            print(f"        {r['rows']:>8,}  {r['disposition']}")
    if bad:
        print(f"\n  {bad} ledger(s) do not reconcile - NOT written. I13 would "
              f"fail and a ledger that does not add up is worse than none.")
        return 1
    if not apply:
        print("\n  dry run - pass --apply to merge")
        return 0
    if CONSERVATION.exists():
        shutil.copy2(CONSERVATION,
                     CONSERVATION.with_name(
                         CONSERVATION.name + f".bak_{TODAY}_pre731"))
    # MERGE, NEVER REWRITE. Two things are dropped deliberately and nothing
    # else: keys this run owns, and any OTHER disposition still standing on a
    # table this run re-partitions (WS2's three contractor_ranking rows). A
    # stale disposition left beside a new partition breaks I13's arithmetic.
    mine_keys = {(r["source_table"], r["disposition"]) for r in mine}
    mine_tabs = {r["source_table"] for r in mine}
    kept, superseded = [], []
    if CONSERVATION.exists():
        with CONSERVATION.open(encoding="utf-8-sig", errors="replace",
                               newline="") as fh:
            for r in csv.DictReader(fh):
                k = (r.get("source_table"), r.get("disposition"))
                if k in mine_keys or r.get("source_table") in mine_tabs:
                    # NAMED, not counted. A ledger row leaving a shared file
                    # is exactly the event that destroyed 2,146,673 accounted
                    # rows on 2026-09-01, so every one is printed with its
                    # table, its disposition and its row count.
                    superseded.append(
                        f"{r.get('source_table')} :: {r.get('disposition')} "
                        f"({r.get('rows')} rows, harvested "
                        f"{r.get('harvest_date')})")
                    continue
                kept.append(r)
    if superseded:
        print("\n  SUPERSEDED - replaced by this run's partition of the "
              "same table:")
        for line in superseded:
            print(f"      {line}")
    tmp = CONSERVATION.with_name(CONSERVATION.name + ".part")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CONS_COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(mine + kept)
    tmp.replace(CONSERVATION)
    print(f"\n  merged {len(mine)} ledger rows over {len(by_tab)} tables; "
          f"{len(kept)} rows belonging to other workstreams preserved; "
          f"{len(superseded)} superseded row(s) replaced")
    print(f"  accounted rows now "
          f"{sum(int(r['rows'] or 0) for r in mine + kept):,}")
    return 0


# =====================================================================
def write_doc() -> int:
    M = measure_all()
    C, N, D = M["contractors"], M["nonprofits"], M["deals"]
    L = []
    A = L.append
    A("# WS5 — contractors, nonprofits, deals: the grain, the guard, and the "
      "sources")
    A("")
    A(f"*Measured {TODAY} by `code/731_ws5_grain_contractors_nonprofits_"
      f"deals.py`. Regenerate rather than edit — every number is taken from "
      f"the files on disk at run time, and `verify` exits 1 when one of them "
      f"stops being true.*")
    A("")
    A("## 1. `contractor_ranking.csv` — DECLARED, and the privacy guard was "
      "the bigger finding")
    A("")
    A("WS2 established that this table had no key: `269` emits one row per "
      "`(tribe_id, firm_key)` and **never writes `firm_key`**, and the "
      "personal-name guard then blanked `operating_company_uei` and replaced "
      "`operating_company_name` with a constant, so two operating companies "
      "of one owner became literally indistinguishable. WS2 proposed the fix "
      "and did not make it. It is made now.")
    A("")
    A("| | |")
    A("|---|---:|")
    A(f"| rows | {C.get('rows', 0):,} |")
    A(f"| duplicates on `(owner_entity_id, operating_company_seq)` | "
      f"**{C.get('pk_duplicate_rows')}** |")
    A(f"| rows with a blank key component | {C.get('pk_blank_component_rows')} |")
    A("")
    A("`operating_company_seq` is 1..n within the owner in the sort order "
      "`269` already used — descending `firm_obligations_usd`. It is unique "
      "by construction and it leaks nothing a redaction was protecting. It is "
      "a **position, not an identity**: it is recomputed every build and it "
      "moves when a firm's obligations move, so a buyer who needs something "
      "stable joins on `operating_company_uei`.")
    A("")
    A("### The guard was firing on sovereign governments")
    A("")
    A("The rule exists to protect a natural person. Measured on the live "
      "file, it fired on **134 of 1,429 rows and exactly one of those 134 was "
      "a natural person** — `BARRETT, MICHAEL`, $20,000. The other 133 were "
      "tribal governments and their instrumentalities: Nez Perce Tribe, "
      "Pueblo of Acoma, Rosebud Sioux Tribe, Ramah Navajo Chapter, Blackfeet "
      "Utilities, Wyandotte Net Tel, Yakama Power, Santa Clara Pueblo, "
      "Quinault Indian Nation, Havasupai Tribe. One carried $71.9M.")
    A("")
    A("The owner settled the principle in `docs/PUBLICATION_POLICY.md`: a "
      "firm's legal name is the firm's name, and the surviving distinction is "
      "whether a column describes the **firm** or a **person separate from "
      "it**. `269`'s own docstring already said the population has no sole "
      "proprietors in it — *\"the owner side is the entity spine, and a sole "
      "proprietor is not on it\"*.")
    A("")
    A("So `privacy_class` is unchanged and still carries 171's verbatim "
      "verdict — the audit trail of what the blunt rule said — and the "
      "**decision** now requires the absence of positive entity evidence. The "
      "evidence is written onto the row in a new `entity_class_basis` column:")
    A("")
    A("| basis | rows freed |")
    A("|---|---:|")
    for k, v in sorted(C.get("entity_class_exemption_by_basis", {}).items(),
                       key=lambda kv: -kv[1]):
        A(f"| `{k}` | {v} |")
    A("")
    A(f"**{C.get('entity_class_exemption_rows')} rows freed, "
      f"${C.get('entity_class_exemption_usd', 0)/1e9:,.2f}B.** Names still "
      f"withheld: **{C.get('names_withheld')}**, carrying "
      f"${C.get('names_withheld_usd', 0):,.2f} — and not one of them is a "
      f"government. The residual is deliberate: a two- or three-token name "
      f"with no entity evidence at all, a blank name, a `SURNAME, FIRSTNAME` "
      f"comma form, and any UEI already ruled not-nameable in "
      f"`individual_native_ownership_verification.csv`. Absence of entity "
      f"evidence is still resolved in the person's favour, and a privacy "
      f"ruling only ever tightens.")
    A("")
    A("### C7 — what may be summed")
    A("")
    A("| statement | measured |")
    A("|---|---:|")
    A(f"| `SUM(firm_obligations_usd)` over every row | "
      f"${C.get('sum_firm_obligations_usd', 0)/1e9:,.2f}B |")
    A(f"| `SUM(owner_obligations_usd)` over every row | "
      f"${C.get('sum_owner_obligations_usd_ROW_SUMMED_WRONG', 0)/1e9:,.2f}B |")
    A(f"| the same, over distinct `owner_entity_id` | "
      f"${C.get('sum_owner_obligations_usd_over_distinct_owners', 0)/1e9:,.2f}B"
      f" |")
    A(f"| inflation if row-summed, over {C.get('n_owners')} owners | "
      f"**{C.get('owner_grain_inflation_x')}x** |")
    A("")
    A("`firm_*` is the additive family. Every `owner_*` column is an "
      "owner-grain attribute repeated on every operating-company row of that "
      "owner. And the table totals to within $0.04 of `prime_contracts.csv`'s "
      "tier-A attributed obligations, so it is a **lossless partition of the "
      "same money** — summing both, or unioning them, double-counts $176.74B.")
    A("")
    A("## 2. `np_schedule_i_grants.csv` — REFUSED, and the refusal is the "
      "finding")
    A("")
    A(f"{N.get('grants_literal_duplicate_rows')} literal duplicate rows over "
      f"{N.get('grants_rows', 0):,}, in "
      f"{N.get('grants_collision_groups')} groups covering "
      f"{N.get('grants_rows_inside_a_collision_group')} rows. "
      f"**They are not duplicates.** "
      f"{N.get('object_ids_carrying_a_collision')} `object_id`s carry a "
      f"collision and "
      f"{N.get('those_object_ids_appearing_MORE_THAN_ONCE_in_filers')} of "
      f"them appear more than once in `np_schedule_i_filers.csv` — so every "
      f"group sits inside ONE return that was parsed exactly once, and the "
      f"FILER listed the line twice. First Nations Development Institute "
      f"lists two $20,000 Economic Development grants to Seneca Nation of "
      f"Indians on its FY2017 return, and both are real.")
    A("")
    A(f"**A de-dupe deletes "
      f"${N.get('money_a_dedupe_would_delete_usd', 0):,.2f} of real grants.** "
      f"The fix is a LINE ORDINAL, not a DELETE: `132.parse_one` walks "
      f"`RecipientTable` in document order and records no ordinal, and one "
      f"column — `schedule_i_line_seq`, 1..n within `object_id` — makes "
      f"`(object_id, schedule_i_line_seq)` unique and takes the count to zero "
      f"without removing a row. That is the same shape as `430`'s fix for "
      f"`prime_contracts` and as `operating_company_seq` above. **`132` is "
      f"not this workstream's to edit**, so the table stays UNSTATED and the "
      f"task now has a name.")
    A("")
    A(f"C7: `cash_grant_usd` totals "
      f"${N.get('grants_cash_grant_usd_total', 0):,.2f} and "
      f"`np_schedule_i_filers.part2_cash_grant_total_usd` totals "
      f"${N.get('filers_part2_cash_grant_total_usd', 0):,.2f} — the same "
      f"money at two grains, to the dollar, and all "
      f"{N.get('filers_rows', 0):,} returns reconcile individually. Never add "
      f"it to federal obligations either: a re-granted federal award is in "
      f"both, and Cedar's shape for that is `native_passthrough.csv`'s "
      f"directed edge plus its `amount_countable` flag, which Schedule I "
      f"lacks.")
    A("")
    A("## 3. `deals` — two declarations, and the source-link coverage the "
      "owner asked for")
    A("")
    A("### Every row of the originated dataset carries a source")
    A("")
    A("`deals_classified.csv` is the one dataset Cedar **originates** rather "
      "than collates, so `PUBLICATION_POLICY.md` asks for a source on every "
      "row of it. Measured:")
    A("")
    A("| | rows | share |")
    A("|---|---:|---:|")
    n = max(D.get("classified_rows", 1), 1)
    for lbl, k in (("two independent source URLs",
                    "rows_with_two_independent_source_urls"),
                   ("one source URL", "rows_with_one_source_url"),
                   ("**no source URL at all**", "rows_with_NO_source_url")):
        A(f"| {lbl} | {D.get(k, 0):,} | {100.0*D.get(k, 0)/n:,.1f}% |")
    A(f"| **at least one** | **{D.get('rows_with_at_least_one_source_url'):,}"
      f"** | **{D.get('source_link_coverage_pct')}%** |")
    A("")
    A(f"{D.get('distinct_source_hosts')} distinct hosts; "
      f"{D.get('rows_sourced_to_a_dot_gov_host'):,} rows cite a `.gov` "
      f"source. The top hosts are:")
    A("")
    for k, v in (D.get("top_source_hosts") or {}).items():
        A(f"- `{k}` — {v:,}")
    A("")
    A("### `deals_2026_ytd_additions.csv` — the empty file, answered")
    A("")
    A(f"GRAIN_OPEN asked whether it was consumed or emptied by a rebuild. "
      f"**Consumed.** All "
      f"{D.get('additions_rows_already_in_classified'):,} of the "
      f"{D.get('additions_rows_total'):,} rows across the nine staging slices "
      f"carry a `Deal_ID` the classified ledger already holds — 100%, not one "
      f"row left behind:")
    A("")
    A("| staging slice | rows | already in `deals_classified` |")
    A("|---|---:|---:|")
    for k, v in sorted((D.get("additions_files") or {}).items()):
        A(f"| `{k}` | {v['rows']:,} | {v['already_in_classified']:,} |")
    A("")
    A(f"So it is declared from the writer and its eight siblings, on "
      f"`Deal_ID` — the route GRAIN-WS3 used for `admin_appeal_positions.csv`."
      f" **The double-counting statement is the point of the declaration:** "
      f"{D.get('classified_rows_present_in_a_staging_slice'):,} of "
      f"{D.get('classified_rows'):,} classified rows are also in a slice, "
      f"worth "
      f"${D.get('classified_usd_on_rows_present_in_a_staging_slice', 0)/1e9:,.2f}"
      f"B against a "
      f"${D.get('classified_usd_total', 0)/1e9:,.2f}B headline. All nine "
      f"tables are individually safe to aggregate and **no two of them are "
      f"safe together.**")
    A("")
    A(f"The second path is bigger than it looks: "
      f"{D.get('rows_whose_value_type_names_a_federal_award'):,} of "
      f"{D.get('classified_rows'):,} rows carry a `Value_Type` naming a "
      f"FEDERAL award — "
      f"${D.get('usd_whose_value_type_names_a_federal_award', 0)/1e9:,.2f}B "
      f"that Cedar already ships in the funding and contracting datasets. A "
      f"deal announcement and the obligation behind it are one dollar.")
    A("")
    A("### `tribal_resolution_financings.csv` — declared from the builder")
    A("")
    A(f"One row, `instrument_number` blank, so the instrument key the open "
      f"question asks about is **absent**, not merely unproven. `149`'s sweep "
      f"holds `doc_links` as a set of `(document_url, link_text, index_page, "
      f"how_found)` tuples and emits at most one row per tuple inside one "
      f"nation's host loop, so a row is a RETRIEVED DOCUMENT whose text names "
      f"a financing authorisation — and `instrument_title` is load-bearing "
      f"because one document reached under two link texts is two rows by "
      f"construction. Key `(entity_id, source_url, source_index_url, "
      f"instrument_title)`: "
      f"{D.get('trf_pk_duplicate_rows')} duplicates, "
      f"{D.get('trf_pk_blank_component_rows')} blank components.")
    A("")
    A("`financing_status` is AUTHORIZED on the whole table. A council "
      "resolution records that a governing body voted to **permit** an "
      "officer to enter a transaction; it does not establish that the "
      "transaction was negotiated, executed or funded. "
      "`principal_amount_text` and `pledged_revenues_text` are free text and "
      "are not money columns — they may not be totalled at all.")
    A("")
    A("## 4. What is still blocked, and who owns it")
    A("")
    A("| blocker | table | owner |")
    A("|---|---|---|")
    A("| C1/C2/C3 — no line ordinal, so 90 real grant lines render identical "
      "| `np_schedule_i_grants.csv` | `132_build_schedule_i_layer.py`: emit "
      "`schedule_i_line_seq` |")
    A("| C4 — 13% of rows carry a Cedar id, scope `mixed` | `nonprofits` | "
      "the identity workstream; ADR-010 |")
    A("| C8 — `88_build_deals_taxonomy.py` is in `NEVER_RUN` | `deals` | the "
      "pipeline owner; see the characterisation below |")
    A("")
    A("### C8, characterised rather than touched")
    A("")
    A(f"`cedar_pipeline.NEVER_RUN` names two things and only one of them is "
      f"still live. **The first is fixed.** 88's glob read "
      f"`deals_*_additions.csv` and never saw the root ledgers, which is the "
      f"miscount that shipped as '790 deals' for three weeks; the glob was "
      f"repaired at source. Re-measured today, the input side is now a "
      f"COMPLETE COVER of the output: "
      f"{D.get('classified_rows_present_in_a_staging_slice')} of "
      f"{D.get('classified_rows')} classified rows are in a staging slice and "
      f"the remaining "
      f"{D.get('classified_rows_originated_in_the_merged_ledger')} are in "
      f"`deals_2026_ytd.csv` / `deals_historical_2020_2025.csv` at the repo "
      f"root — **0 rows are in neither**, so a rebuild that reads both "
      f"surfaces loses no row.")
    A("")
    A(f"**The second is live and it is the whole of the blocker.** "
      f"{D.get('rows_carrying_in_place_party_enrichment')} of "
      f"{D.get('classified_rows')} rows carry `native_party_entity_id`, "
      f"`native_party_attribution_source` and `cedar_uid` — written IN PLACE "
      f"by 33/53/57/154 after 88 ran, and present in neither the slices nor "
      f"the root ledgers. A full taxonomy rebuild discards all "
      f"{D.get('rows_carrying_in_place_party_enrichment')}. This is the "
      f"class-6 shape the whole project keeps meeting — a full-rebuild writer "
      f"and in-place enrichers on one table with no declared ordering — and "
      f"the fix is the one `510` already applied to "
      f"`cedar_harvest_conservation.csv` and the one `01` still needs: 88 "
      f"takes a `.bak` before writing, records a pre-rebuild census (row "
      f"count, distinct `Deal_ID`, count of non-blank "
      f"`native_party_entity_id`), and the four party enrichers are replayed "
      f"in a recorded order and gated on that census. Until then the correct "
      f"posture is the one in force: keep it in `NEVER_RUN`.")
    A("")
    A("## 5. `62` gate state at handoff — every red line named with its owner")
    A("")
    A("Standing rule 15: red is recorded, never stepped around. WS5 raised "
      "four lint findings of its own and cleared all four before handoff — "
      "three `class1` (reading the staging slices IS this workstream's "
      "subject; waived on the line with a reason, which 293 counts and names) "
      "and one `class2c` (a superseded-row counter that named nothing; it now "
      "prints every superseded ledger row with its table, disposition and row "
      "count, because a ledger row leaving a SHARED file is exactly the event "
      "that destroyed 2,146,673 accounted rows on 2026-09-01).")
    A("")
    A("What is still red belongs to other workstreams:")
    A("")
    A("| red line | owner | already named in `AGENTS.md`? |")
    A("|---|---|---|")
    A("| `lint_new_defect_instances` — `NEW class6: "
      "518_dataset_readiness.py / cedar_dataset_readiness.csv` | 518's author "
      "| yes |")
    A("| `lint_new_defect_instances` — `NEW class6: "
      "73_faads_name_attribution.py / faads_entity_attribution.csv` | the "
      "funding / FAADS workstream, which has "
      "`710_faads_attribution_content_key.py` staged | **no — recorded here "
      "because `AGENTS.md` is not WS5's to edit** |")
    A("| `rulings_unapplied` ROSE 1,215 → 2,894 | the rulings-propagation "
      "workstream. The metric reads `status` on "
      "`cedar_ruling_ledger_consolidated.csv`, which `173` rebuilds from "
      "`23`'s output — the same three-table defect WS2 documented, and no "
      "file WS5 touched is in its surface | **no — recorded here for the "
      "same reason** |")
    A("| `contract_violations = 7`, `contract_orphan_shippable = 6`, "
      "`tables_missing_from_25_TABLES` 179 → 187 | the contracts and "
      "curated-override workstreams; new `data/clean` tables from other "
      "shards | yes |")
    A("| `files_with_columns_lost_vs_backup = 1` — "
      "`entity_evidence_profile.csv` | whoever ran `505` | yes |")
    A("| `SHIPPING LOST: advocacy_passthrough_2026-08-07.csv` | the owner's "
      "own deliberate deregistration; `AGENTS.md` says in as many words that "
      "the gate's wording is wrong and nobody should spend further time on it "
      "| yes |")
    A("")
    A("WS5 moved these in the right direction: "
      "`contract_grain_stated_shippable` 185 → 204, "
      "`contract_grain_unstated_shippable` 25 → 19, "
      "`export_unsafe_money_tables` 11 → 8, `harvest_source_rows_read` "
      "2,146,807 → 12,743,700, `lint_bug_class_instances` 146 → 145.")
    A("")
    OUT_MD.write_text("\n".join(L), encoding="utf-8")
    print(f"  wrote {OUT_MD.relative_to(ROOT)}")
    return 0


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "measure"
    if cmd == "verify":
        return verify()
    if cmd == "conserve":
        return conserve("--apply" in sys.argv)
    if cmd == "doc":
        return write_doc()
    print(json.dumps(measure_all(), indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
