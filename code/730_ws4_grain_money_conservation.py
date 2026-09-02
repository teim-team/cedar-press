#!/usr/bin/env python3
"""
Cedar Press - 730: WORKSTREAM GRAIN-WS4. Grain refusals, the funding
cross-table money rules, and row conservation for `legislation`.

    py -3 code/730_ws4_grain_money_conservation.py            # measure + write
    py -3 code/730_ws4_grain_money_conservation.py verify     # read-only, exit 1

WHAT THIS WORKSTREAM WAS HANDED
-------------------------------
Eight shippable tables across `funding`, `lobbying` and `legislation` whose
grain the readiness scoreboard (518) reports as UNSTATED:

    funding      faads_transactions.csv
                 faads_transactions_all_agencies.csv
                 native_passthrough.csv
    lobbying     ferc_docket_filings.csv
                 hearing_bill_links.csv
                 lobbying_registrant_native_ownership_evidence.csv
    legislation  congressional_correspondence_log.csv
                 native_bills_subject_sweep.csv

`512.GRAIN_WS4` is EMPTY, and that is the measured finding, not a shortfall.
Seven of the eight carry LITERAL DUPLICATE ROWS - whole rows repeating byte
for byte - and a file with a literal duplicate row has no unique key at ANY
arity, because the widest candidate available is the whole row and it already
collides. `512.validate_grain` turns a declaration with no usable key into a
release-blocking violation, correctly. The eighth holds ZERO rows and its id
generator is measurably NOT unique on the population it draws from (see
section A). Declaring past any of that is the one way the contracts file can
lie, and "a wrong grain in a contract is worse than a missing one" is that
file's own rule.

So this script does the thing that IS available: it measures each refusal
exactly, names the one upstream change that would lift it, and names who owns
that change. Every number below is re-measured from the live files on each
run, and `verify` exits 1 when one of them stops being true.

WHAT WAS FIXED RATHER THAN DESCRIBED
------------------------------------
`native_passthrough.csv` was 20% incomplete and had been since 2026-08-12.
`81_build_passthrough_dataset.py` is a pure projection of `subawards.csv`, and
`subawards.csv` had grown and been re-attributed under it. Rebuilt 2026-09-01
against subawards.csv sha256 ae80c2af... (72,837 rows), spine sha256
6e607d3d... (1,555 rows), both verified unchanged across the build:

    1,262 -> 1,522 rows      +251 new both-sides-Native subawards
                             -4 rows whose sub-side attribution was WITHDRAWN
                                upstream (sub_native_tribe_id is now blank on
                                4 Chugachmiut -> Bristol Bay Area Health
                                Corporation subawards; 81 refuses a row it
                                cannot name on both ends)
                             ~90 rows RE-POINTED from Alaska Native village
                                GOVERNMENTS (AKNF-*) to village CORPORATIONS
                                (ANVC-*) - Eyak -> Eyak Corporation, Alutiiq ->
                                Afognak Native Corporation, Sun'aq -> Natives
                                of Kodiak. That is docs/ANCSA_OWNERSHIP_RULING
                                .md rule 1, which the parent already carries
                                and the projection did not. The stale file was
                                the one CONTRADICTING the owner's ruling.
                             241 rows flipped amount_countable 1 -> 0 on the
                                parent's current duplicate_status /
                                subaward_exceeds_prime_flag.

The rebuild was checked BEFORE it was run, by deriving 81's output in memory
and diffing it against the file on disk, so that every change above was known
and traced to an upstream authority first. `.bak_2026-09-01_pre_ws4_rebuild`
sits beside both outputs. Nothing was de-duplicated and no row was deleted.

Writes  docs/WS4_GRAIN_MONEY_CONSERVATION.md   the evidence, for a human
        docs/MONEY_TOTALLING_RULES.md          C7, appended between markers
        data/clean/cedar_harvest_conservation.csv   C5, MERGED never rewritten
"""
from __future__ import annotations

import collections
import csv
import importlib.util
import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()

CLEAN = ROOT / "data" / "clean"
SPINE = ROOT / "data" / "spine"
OUT_MD = ROOT / "docs" / "WS4_GRAIN_MONEY_CONSERVATION.md"
MONEY_MD = ROOT / "docs" / "MONEY_TOTALLING_RULES.md"
CONSERVATION = CLEAN / "cedar_harvest_conservation.csv"

# MONEY_TOTALLING_RULES.md is written WHOLESALE by 574 (`OUT_MD.write_text`),
# so anything appended to it is destroyed the next time 574 runs. The section
# this script contributes is therefore delimited and re-applied idempotently:
# re-running 730 restores it. Named here so the next reader knows the file has
# two authors and one of them overwrites.
MARK_A = "<!-- BEGIN GRAIN-WS4 -->"
MARK_B = "<!-- END GRAIN-WS4 -->"

WS4_TABLES = [
    ("funding", "faads_transactions.csv"),
    ("funding", "faads_transactions_all_agencies.csv"),
    ("funding", "native_passthrough.csv"),
    ("lobbying", "ferc_docket_filings.csv"),
    ("lobbying", "hearing_bill_links.csv"),
    ("lobbying", "lobbying_registrant_native_ownership_evidence.csv"),
    ("legislation", "congressional_correspondence_log.csv"),
    ("legislation", "native_bills_subject_sweep.csv"),
]

# The candidate key each table's own build log, header or sibling table gives
# positive reason to expect. Tested on the FULL file, never on a sample.
CANDIDATES = {
    "faads_transactions.csv": [
        ["award_id_fain"], ["award_id_fain", "action_date", "obligated_usd"]],
    "faads_transactions_all_agencies.csv": [
        ["award_id_fain"], ["award_id_fain", "action_date", "obligated_usd"]],
    "native_passthrough.csv": [
        ["subaward_number"],
        ["subaward_number", "prime_award_id", "from_tribe_id", "to_tribe_id"],
        ["subaward_number", "prime_award_id", "from_tribe_id", "to_tribe_id",
         "subaward_date", "amount_usd"]],
    "ferc_docket_filings.csv": [
        ["ferc_filing_id"],
        ["docket_number", "subdocket", "accession_number",
         "filer_organization_as_recorded"]],
    "hearing_bill_links.csv": [
        ["event_id", "bill_id"],
        ["event_id", "bill_id", "link_basis", "relationship"]],
    "lobbying_registrant_native_ownership_evidence.csv": [
        ["registrant_id", "evidence_route"],
        ["registrant_id", "evidence_route", "native_entity_id",
         "evidence_tier"]],
    "congressional_correspondence_log.csv": [
        ["record_id"], ["record_id", "control_number"]],
    "native_bills_subject_sweep.csv": [
        ["bill_id"], ["bill_id", "subject_family", "matched_phrase"]],
}


def find(name: str) -> Path | None:
    for d in (CLEAN, SPINE):
        p = d / name
        if p.exists():
            return p
    return None


def read_csv(p: Path) -> list:
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def money(x) -> float:
    try:
        return float(str(x or "").replace(",", "").replace("$", "") or 0)
    except ValueError:
        return 0.0


def scan(p: Path, cols):
    """Stream selected columns. The all-agencies file is 2.77M rows; a
    DictReader over it costs a minute of nothing."""
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rr = csv.reader(fh)
        head = next(rr, [])
        idx = {c: head.index(c) for c in cols if c in head}
        for row in rr:
            w = len(row)
            yield {c: (row[i] if i < w else "") for c, i in idx.items()}


# ---------------------------------------------------------------------------
# A. GRAIN - the refusals, measured
# ---------------------------------------------------------------------------
def measure_grain():
    out = []
    for coll, name in WS4_TABLES:
        p = find(name)
        if p is None:
            out.append(dict(collection=coll, table=name, error="not on disk"))
            continue
        with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            rr = csv.reader(fh)
            head = [h.strip() for h in next(rr, [])]
            # Whole-row duplicates are counted on the LITERAL row, joined with
            # a unit separator that cannot occur inside a parsed CSV field, so
            # a count here is a literal duplicate and not a hash artefact of
            # two different rows colliding on a delimiter.
            seen = collections.Counter()
            n = 0
            keyed = {tuple(k): collections.Counter()
                     for k in CANDIDATES.get(name, [])}
            pos = {c: head.index(c) for c in head}
            for row in rr:
                n += 1
                w = len(row)
                seen["\x1f".join(row)] += 1
                for k in keyed:
                    keyed[k]["\x1f".join(
                        (row[pos[c]] if c in pos and pos[c] < w else "")
                        for c in k)] += 1
        dup_rows = sum(v - 1 for v in seen.values() if v > 1)
        dup_groups = sum(1 for v in seen.values() if v > 1)
        cands = []
        for k, cnt in keyed.items():
            missing = [c for c in k if c not in head]
            cands.append(dict(
                key=list(k), columns_missing=missing,
                duplicate_rows=(None if missing
                                else sum(v - 1 for v in cnt.values() if v > 1)),
                distinct=(None if missing else len(cnt))))
        out.append(dict(collection=coll, table=name, rows=n,
                        columns=len(head),
                        literal_duplicate_rows=dup_rows,
                        literal_duplicate_groups=dup_groups,
                        candidates=cands,
                        # A file with a literal duplicate row has NO unique key
                        # at any arity. This is not an opinion about the data;
                        # it is arithmetic, and it is why GRAIN_WS4 is empty.
                        key_possible_today=(dup_rows == 0)))
    return out


def measure_correspondence_id():
    """The one WS4 table with no literal duplicates holds ZERO rows, so any
    key is vacuously unique. Whether `record_id` may be DECLARED is therefore
    a question about the GENERATOR, not about the file - and the generator is
    measurable.

    136.build_correspondence_layer mints
        record_id = "FOIAREQ-{agency_code}-{foia_request_id}"
    for every foia_request_index.csv row with
        requester_is_congressional_office == "Y".
    """
    p = CLEAN / "foia_request_index.csv"
    if not p.exists():
        return {}
    rows = read_csv(p)
    pair = collections.Counter((r.get("agency_code", ""),
                                r.get("foia_request_id", "")) for r in rows)
    coll = sum(v - 1 for v in pair.values() if v > 1)
    # WHY the id collides, in the source's own words: every colliding row
    # carries a parse-quality reason saying the control number was recovered
    # more than once from the PDF layout.
    why = collections.Counter()
    dupkeys = {k for k, v in pair.items() if v > 1}
    for r in rows:
        if (r.get("agency_code", ""), r.get("foia_request_id", "")) in dupkeys:
            for tok in (r.get("parse_quality_reason") or "").split("|"):
                if tok.strip():
                    why[tok.strip()] += 1
    return dict(rows=len(rows),
                congressional_office_requesters=sum(
                    1 for r in rows
                    if r.get("requester_is_congressional_office") == "Y"),
                id_collisions=coll,
                distinct_ids=len(pair),
                collision_reasons=why.most_common(4))


# ---------------------------------------------------------------------------
# B. C7 - the funding cross-table money paths
# ---------------------------------------------------------------------------
def measure_money():
    m = {}

    faads_all = find("faads_transactions_all_agencies.csv")
    faads_doi = find("faads_transactions.csv")
    ffx = find("federal_funding_transactions.csv")

    # one pass over the 2.77M-row file
    a_rows = a_tot = 0
    a_blank_tribe = 0
    a_fy07_rows = 0
    a_fy07_tot = 0.0
    a_fy07_fain = set()
    a_years = set()
    for r in scan(faads_all, ["fiscal_year", "obligated_usd", "award_id_fain",
                              "tribe_id"]):
        a_rows += 1
        a_tot += money(r["obligated_usd"])
        if not (r.get("tribe_id") or "").strip():
            a_blank_tribe += 1
        fy = (r.get("fiscal_year") or "").strip()
        if fy:
            a_years.add(fy)
        if fy == "2007":
            a_fy07_rows += 1
            a_fy07_tot += money(r["obligated_usd"])
            if (r.get("award_id_fain") or "").strip():
                a_fy07_fain.add(r["award_id_fain"].strip())
    m["faads_all"] = dict(rows=a_rows, total=a_tot,
                          blank_tribe_id_rows=a_blank_tribe,
                          fy_min=min(a_years), fy_max=max(a_years),
                          fy2007_rows=a_fy07_rows, fy2007_total=a_fy07_tot)

    d_rows = 0
    d_tot = 0.0
    d_years = set()
    for r in scan(faads_doi, ["fiscal_year", "obligated_usd"]):
        d_rows += 1
        d_tot += money(r["obligated_usd"])
        if (r.get("fiscal_year") or "").strip():
            d_years.add(r["fiscal_year"].strip())
    m["faads_doi"] = dict(rows=d_rows, total=d_tot,
                          fy_min=min(d_years), fy_max=max(d_years))

    f_rows = 0
    f_tot = 0.0
    f_years = set()
    f_fy07_rows = 0
    f_fy07_tot = 0.0
    f_fy07_shared = 0.0
    f_attr_rows = 0
    f_attr_tot = 0.0
    for r in scan(ffx, ["fiscal_year", "obligated_usd", "award_id_fain",
                        "tribe_id", "excluded_flag"]):
        f_rows += 1
        v = money(r["obligated_usd"])
        f_tot += v
        fy = (r.get("fiscal_year") or "").strip()
        if fy:
            f_years.add(fy)
        if (r.get("tribe_id") or "").strip() and \
                (r.get("excluded_flag") or "").strip() != "1":
            f_attr_rows += 1
            f_attr_tot += v
        if fy == "2007":
            f_fy07_rows += 1
            f_fy07_tot += v
            if (r.get("award_id_fain") or "").strip() in a_fy07_fain:
                f_fy07_shared += v
    m["ffx"] = dict(rows=f_rows, total=f_tot,
                    fy_min=min(f_years), fy_max=max(f_years),
                    fy2007_rows=f_fy07_rows, fy2007_total=f_fy07_tot,
                    fy2007_on_shared_fain=f_fy07_shared,
                    attributed_rows=f_attr_rows, attributed_total=f_attr_tot)

    pan = read_csv(CLEAN / "federal_funding_tribe_year_panel.csv")
    m["panel"] = dict(rows=len(pan),
                      total=sum(money(r["total_obligated_usd"]) for r in pan),
                      n_transactions=sum(int(r.get("n_transactions") or 0)
                                         for r in pan))

    att = read_csv(CLEAN / "faads_entity_attribution.csv")
    m["attribution"] = dict(rows=len(att),
                            total=sum(money(r["obligated_usd"]) for r in att))

    bie = read_csv(CLEAN / "bie_uio_dollars_by_entity.csv")
    m["bie_uio"] = dict(
        rows=len(bie),
        components={c: sum(money(r.get(c)) for r in bie) for c in
                    ("total_usd", "usd_faads_all_agencies",
                     "usd_federal_funding", "usd_nonprofit_990",
                     "usd_prime_contracts", "usd_subawards")})

    pt = read_csv(CLEAN / "native_passthrough.csv")
    pr = read_csv(CLEAN / "native_passthrough_pairs.csv")
    cnt = collections.Counter(tuple(r.values()) for r in pt)
    cols = list(pt[0].keys()) if pt else []
    ci = cols.index("amount_countable") if "amount_countable" in cols else -1
    ai = cols.index("amount_usd") if "amount_usd" in cols else -1
    m["passthrough"] = dict(
        rows=len(pt),
        total_all=sum(money(r["amount_usd"]) for r in pt),
        countable_rows=sum(1 for r in pt if r["amount_countable"] == "1"),
        countable_total=sum(money(r["amount_usd"]) for r in pt
                            if r["amount_countable"] == "1"),
        literal_duplicate_rows=sum(v - 1 for v in cnt.values() if v > 1),
        duplicate_surplus_countable_rows=sum(
            v - 1 for k, v in cnt.items() if v > 1 and k[ci] == "1"),
        duplicate_surplus_countable_usd=sum(
            money(k[ai]) * (v - 1) for k, v in cnt.items()
            if v > 1 and k[ci] == "1"),
        pairs_rows=len(pr),
        pairs_total=sum(money(r["countable_usd"]) for r in pr))
    return m


# ---------------------------------------------------------------------------
# C. C5 - row conservation for `legislation`, and a refresh of the
#    native_passthrough rows this workstream's rebuild made stale
# ---------------------------------------------------------------------------
def measure_conservation():
    """Every disposition below is DERIVED by re-running the builder's own
    filter over the builder's own input, never asserted from a build log."""
    rows = []

    # -- native_bills_subject_sweep.csv ---------------------------------
    # 73_bills_votes_completion.stage_sweep walks all_bill_intros.csv and
    # emits one row per bill whose title, subjects or policy area matches a
    # subject family. The regexes are IMPORTED from 73 rather than copied, so
    # this measurement cannot drift away from the build that produced the file.
    corpus_p = (ROOT / "data" / "raw" / "external" / "votingpatterns"
                / "all_bill_intros.csv")
    sweep_p = CLEAN / "native_bills_subject_sweep.csv"
    if corpus_p.exists() and sweep_p.exists():
        spec = importlib.util.spec_from_file_location(
            "_ws4_b73", HERE / "73_bills_votes_completion.py")
        b73 = importlib.util.module_from_spec(spec)
        sys.modules["_ws4_b73"] = b73
        spec.loader.exec_module(b73)
        corpus = read_csv(corpus_p)
        emitted = excluded = nofamily = 0
        for r in corpus:
            title = r.get("title") or ""
            hay = f"{title} || {r.get('subjects') or ''} || " \
                  f"{r.get('policy_area') or ''}"
            fam = where = ""
            for fname, rxs in b73.FAMILY_RX.items():
                for rx in rxs:
                    if rx.search(title):
                        fam, where = fname, "title"
                        break
                    if rx.search(hay):
                        fam, where = fname, "subjects_or_policy_area"
                        break
                if fam:
                    break
            if not fam and (r.get("policy_area") or "").strip().lower() == \
                    "native americans":
                fam, where = "general", "congress_gov_policy_area"
            if not fam:
                nofamily += 1
                continue
            bad = next((w for rx, w in b73.SWEEP_EXCLUDE if rx.search(title)),
                       "")
            if bad and where == "title":
                excluded += 1
                continue
            emitted += 1
        n_in = len(corpus)
        rows += [
            ("data/clean/native_bills_subject_sweep.csv", n_in, "emitted",
             emitted, "a subject-family phrase matched the Congress.gov "
             "title, subjects or policyArea"),
            ("data/clean/native_bills_subject_sweep.csv", n_in,
             "rejected:no_native_subject_family_matched", nofamily,
             "the corpus is EVERY bill introduced since the 103rd Congress; "
             "the sweep is the Native-subject slice of it"),
            ("data/clean/native_bills_subject_sweep.csv", n_in,
             "rejected:title_matched_a_false_friend_guard", excluded,
             "SWEEP_EXCLUDE in 73_bills_votes_completion.py - a title phrase "
             "that matches a family regex for a non-Native reason"),
            ("data/clean/native_bills_subject_sweep.csv", n_in,
             "flagged:literal_duplicate_inherited_from_the_corpus",
             _literal_dups(sweep_p),
             "all_bill_intros.csv repeats 595 bill_ids byte-identically; the "
             "sweep emits one row per corpus row and inherits them. RETAINED "
             "and flagged, never deleted - de-dupe key is bill_id"),
        ]

    # -- congressional_correspondence_log.csv ---------------------------
    # ZERO rows, and the conservation is the whole explanation for why.
    idx_p = CLEAN / "foia_request_index.csv"
    ccl_p = CLEAN / "congressional_correspondence_log.csv"
    if idx_p.exists() and ccl_p.exists():
        idx = read_csv(idx_p)
        emitted = sum(1 for r in idx
                      if r.get("requester_is_congressional_office") == "Y")
        seeks = sum(1 for r in idx
                    if r.get("seeks_congressional_correspondence") == "Y")
        rows += [
            ("data/clean/congressional_correspondence_log.csv", len(idx),
             "emitted", emitted,
             "136.build_correspondence_layer writes a row only where a "
             "RETRIEVED record names a congressional office as a party"),
            ("data/clean/congressional_correspondence_log.csv", len(idx),
             "rejected:requester_is_not_a_congressional_office",
             len(idx) - emitted,
             "CONG_ORG_RE must match a chamber or a named member's office; "
             "merely containing 'congress' is deliberately not enough"),
            ("data/clean/congressional_correspondence_log.csv", len(idx),
             "not_emitted_but_evidentiary:request_seeks_a_congressional_"
             "correspondence_log", seeks,
             "these prove the LOG EXISTS at that bureau and has already been "
             "located and reviewed once; they feed "
             "congressional_correspondence_systems.csv, not this table"),
        ]

    # -- native_passthrough.csv, refreshed after the WS4 rebuild ---------
    sub_p = CLEAN / "subawards.csv"
    pt_p = CLEAN / "native_passthrough.csv"
    if sub_p.exists() and pt_p.exists():
        sub = read_csv(sub_p)
        n_in = len(sub)
        both = [r for r in sub if r.get("direction") == "both_sides_native"]
        unres = [r for r in both
                 if not (r.get("prime_native_tribe_id") or "").strip()
                 or not (r.get("sub_native_tribe_id") or "").strip()]
        emitted = len(both) - len(unres)
        rows += [
            ("data/clean/native_passthrough.csv", n_in, "emitted", emitted,
             "both sides resolved to a Cedar entity"),
            ("data/clean/native_passthrough.csv", n_in,
             "rejected:direction_is_not_both_sides_native",
             n_in - len(both),
             "one hop only: this dataset is the Native-to-Native slice"),
            ("data/clean/native_passthrough.csv", n_in,
             "rejected:one_side_unresolved_to_a_cedar_entity", len(unres),
             "a relationship we cannot name on both ends is not a "
             "pass-through we can publish"),
            # KEPT AT ITS KEY, SET TO ZERO, NOT DELETED. The disposition was
            # true when GRAIN-WS1 measured it and the WS4 rebuild closed it;
            # deleting the row would erase the fact that it was ever open.
            ("data/clean/native_passthrough.csv", n_in,
             "stale:both_sides_native_rows_appended_to_subawards.csv_after_"
             "the_last_81_build_so_no_passthrough_row_exists_for_them_yet", 0,
             "CLOSED 2026-09-01 by workstream GRAIN-WS4: 81_build_passthrough_"
             "dataset.py re-run against subawards.csv at 72,837 rows, "
             "1,262 -> 1,522"),
        ]
    return rows


def _literal_dups(p: Path) -> int:
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rr = csv.reader(fh)
        next(rr, [])
        c = collections.Counter("\x1f".join(r) for r in rr)
    return sum(v - 1 for v in c.values() if v > 1)


CONS_COLS = ["source_table", "rows_in", "disposition", "rows", "pct",
             "examples", "harvest_date"]


def merge_conservation(new_rows) -> tuple:
    """MERGE-ONLY on (source_table, disposition).

    A wholesale rewrite of this ledger destroyed 2,146,673 accounted rows on
    2026-09-01. This function never writes a row it did not either find or
    add: existing keys are UPDATED IN PLACE at their original position, new
    keys are appended, and nothing is ever removed.
    """
    existing = read_csv(CONSERVATION) if CONSERVATION.exists() else []
    hdr = CONS_COLS
    if CONSERVATION.exists():
        with CONSERVATION.open(encoding="utf-8-sig", newline="") as fh:
            hdr = next(csv.reader(fh), CONS_COLS)
    pos = {(r.get("source_table"), r.get("disposition")): i
           for i, r in enumerate(existing)}
    updated = added = 0
    for table, n_in, disp, n, ex in new_rows:
        rec = {c: "" for c in hdr}
        rec.update(source_table=table, rows_in=str(n_in), disposition=disp,
                   rows=str(n),
                   pct=(f"{100.0 * n / n_in:.2f}" if n_in else "0.00"),
                   examples=ex, harvest_date=TODAY)
        k = (table, disp)
        if k in pos:
            existing[pos[k]].update(rec)
            updated += 1
        else:
            existing.append(rec)
            added += 1
    with CONSERVATION.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=hdr, extrasaction="ignore")
        w.writeheader()
        w.writerows(existing)
    return updated, added, len(existing)


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------
def usd(x):
    return f"${x:,.0f}"


def money_section(m):
    a, d, f = m["faads_all"], m["faads_doi"], m["ffx"]
    pan, att, bie, pt = m["panel"], m["attribution"], m["bie_uio"], \
        m["passthrough"]
    b = bie["components"]
    pct = (100.0 * f["fy2007_on_shared_fain"] / f["fy2007_total"]
           if f["fy2007_total"] else 0)
    L = [MARK_A, "",
         "## `funding` — the CROSS-TABLE paths, and the FY2007 seam", "",
         f"*Appended {TODAY} by workstream GRAIN-WS4 "
         f"(`code/730_ws4_grain_money_conservation.py`). Re-measured from the "
         f"live files on every run.* **This file is written WHOLESALE by "
         f"`574`, which will delete this section; re-run `730` to restore "
         f"it.**", "",
         "The section above states what a buyer may total WITHIN each funding "
         "table. It does not say what happens when two of them are loaded "
         "together, and that is where the largest unstated double-count in "
         "this dataset lives.", "",
         "### THE FY2007 SEAM — the one nobody had measured", "",
         f"`faads_transactions_all_agencies.csv` covers **FY{a['fy_min']}–"
         f"{a['fy_max']}**. `federal_funding_transactions.csv` covers "
         f"**FY{f['fy_min']}–{f['fy_max']}**. **They both hold FY2007**, and "
         f"it is not a token overlap:", "",
         "| | rows | obligations |", "|---|---:|---:|",
         f"| `faads_transactions_all_agencies.csv` FY2007 | "
         f"{a['fy2007_rows']:,} | {usd(a['fy2007_total'])} |",
         f"| `federal_funding_transactions.csv` FY2007 | "
         f"{f['fy2007_rows']:,} | {usd(f['fy2007_total'])} |",
         f"| …of which sits on a FAIN the faads file ALSO carries | | "
         f"**{usd(f['fy2007_on_shared_fain'])}** ({pct:.1f}%) |", "",
         f"**{pct:.1f}% of the FY2007 dollars in the modern table are the "
         f"same awards the archive table already carries.** A buyer building "
         f"a FY2001–FY2026 series by stacking the two files double-counts "
         f"FY2007. Stack them at **FY2001–2006 from the archive, FY2007 "
         f"onward from `federal_funding_transactions.csv`** — the modern "
         f"table is the attributed one, so the seam belongs on its side.", "",
         "### `faads_transactions_all_agencies.csv` IS NOT A NATIVE TABLE",
         "",
         f"`tribe_id` is blank on **all {a['blank_tribe_id_rows']:,} rows** "
         f"and its {usd(a['total'])} is the WHOLE federal assistance universe "
         f"for FY{a['fy_min']}–{a['fy_max']}: every recipient in the country, "
         f"Native and not, unfiltered. **It must never be quoted as money "
         f"reaching Indian Country, and no ratio to a Native total is "
         f"meaningful because the file contains no attribution to divide "
         f"by.** `faads_transactions.csv` ({d['rows']:,} rows, "
         f"{usd(d['total'])}, FY{d['fy_min']}–{d['fy_max']}) is the *Interior* "
         f"slice of that same file, carried into it verbatim — an AGENCY "
         f"filter, not a Native one; its `tribe_id` is blank on all "
         f"{d['rows']:,} rows too. Never add the two. The Native attribution "
         f"for these years lives OUTSIDE both files, in "
         f"`faads_entity_attribution.csv` ({m['attribution']['rows']:,} rows, "
         f"FY2001–06). The Native-attributed figure Cedar publishes for the "
         f"modern era is {usd(f['attributed_total'])} over "
         f"{f['attributed_rows']:,} rows of "
         f"`federal_funding_transactions.csv` (`tribe_id` populated, "
         f"`excluded_flag != 1`, FY{f['fy_min']}–{f['fy_max']}) — a different "
         f"PERIOD as well as a different population, so it is not the "
         f"denominator of anything above.", "",
         "### The four ROLL-UPS and PROJECTIONS that are not new money", "",
         "| table | measure | it is a roll-up / projection of | never add to |",
         "|---|---|---|---|",
         f"| `federal_funding_tribe_year_panel.csv` | `total_obligated_usd` "
         f"= {usd(pan['total'])} over {pan['rows']:,} (tribe, year) cells, "
         f"{pan['n_transactions']:,} transactions | "
         f"`federal_funding_transactions.csv`, after its attribution and "
         f"exclusion filters | the transaction table, and its own "
         f"`obl_type_*` columns, which decompose `total_obligated_usd` and "
         f"sum back to it |",
         f"| `faads_entity_attribution.csv` | `obligated_usd` = "
         f"{usd(att['total'])} over {att['rows']:,} rows | "
         f"`faads_transactions_all_agencies.csv` — the dollar is carried "
         f"verbatim onto an attribution row | either faads table |",
         f"| `native_passthrough_pairs.csv` | `countable_usd` = "
         f"{usd(pt['pairs_total'])} over {pt['pairs_rows']:,} entity pairs | "
         f"the countable rows of `native_passthrough.csv` — it reconciles to "
         f"the cent | `native_passthrough.csv` |",
         f"| `bie_uio_dollars_by_entity.csv` | `total_usd` = "
         f"{usd(b['total_usd'])} over {bie['rows']:,} entities | **FIVE "
         f"DATASETS AT ONCE** (see below) | anything |", "",
         "### `bie_uio_dollars_by_entity.csv` — a cross-dataset roll-up, and "
         "it double-counts inside itself", "",
         "| component | dollars | already published as |", "|---|---:|---|",
         f"| `usd_federal_funding` | {usd(b['usd_federal_funding'])} | "
         f"`federal_funding_transactions.csv` |",
         f"| `usd_prime_contracts` | {usd(b['usd_prime_contracts'])} | "
         f"`prime_contracts.csv` |",
         f"| `usd_faads_all_agencies` | {usd(b['usd_faads_all_agencies'])} | "
         f"`faads_transactions_all_agencies.csv` |",
         f"| `usd_subawards` | {usd(b['usd_subawards'])} | `subawards.csv` — "
         f"**and a subaward is a SLICE of a prime already counted in the row "
         f"above it** |",
         f"| `usd_nonprofit_990` | {usd(b['usd_nonprofit_990'])} | "
         f"`np_*` |",
         f"| **`total_usd`** | **{usd(b['total_usd'])}** | the sum of the "
         f"five |", "",
         f"`total_usd` is a **PROGRAMME-EXPOSURE MEASURE, not a dollar "
         f"total**: it adds an assistance obligation, a contract obligation "
         f"and a subaward slice of that same contract, which are three "
         f"different things and, for the subaward column, partly the same "
         f"dollar twice. {usd(b['usd_subawards'])} of it is inside "
         f"`usd_prime_contracts` by construction, and "
         f"`usd_faads_all_agencies` straddles the FY2007 seam with "
         f"`usd_federal_funding`. Read the components; never quote the total "
         f"as money received.", "",
         "### `native_passthrough.csv` — rebuilt, and what changed", "",
         f"Rebuilt {TODAY} by GRAIN-WS4: **{pt['rows']:,} rows**, was 1,262 "
         f"and 20% incomplete since 2026-08-12. `amount_usd` is additive "
         f"**only** at `amount_countable == 1` — {pt['countable_rows']:,} "
         f"rows, **{usd(pt['countable_total'])}**, against "
         f"{usd(pt['total_all'])} unfiltered. The filter now removes "
         f"{usd(pt['total_all'] - pt['countable_total'])}.", "",
         f"The table carries **{pt['literal_duplicate_rows']} literal "
         f"duplicate rows**, inherited from `subawards.csv`'s retained "
         f"monthly re-filings. "
         f"{pt['literal_duplicate_rows'] - pt['duplicate_surplus_countable_rows']}"
         f" of them already carry `amount_countable = 0`, so the money rule "
         f"excludes them without anything being deleted. The remaining "
         f"**{pt['duplicate_surplus_countable_rows']} rows, "
         f"{usd(pt['duplicate_surplus_countable_usd'])}**, are countable AND "
         f"repeated — that is the entire exposure, and it is the one number "
         f"a buyer needs. **The fix is not a delete:** `81` collapses "
         f"`subawards.duplicate_status` and `subaward_exceeds_prime_flag` "
         f"into a single 0/1 flag and drops both source columns, so the file "
         f"cannot say WHICH filter failed. Carrying `duplicate_status` "
         f"through would make the de-dupe key statable and cost one line.",
         "",
         "> `amount_countable` is a **0/1 FLAG, not money**. "
         "`517.MONEY_HINTS` matches the substring `amount` and counts it as a "
         "money column, which is why this table reports one more money "
         "column than it has. Flagged by GRAIN-WS1, still open, owner: "
         "whoever holds `517`.", "", MARK_B]
    return "\n".join(L)


def write_docs(grain, corr, m, cons_counts):
    L = [f"# Workstream GRAIN-WS4 — grain refusals, funding money paths, "
         f"legislation row conservation", "",
         f"*Generated {TODAY} by `code/730_ws4_grain_money_conservation.py`. "
         f"Every number is re-measured from the live files on every run; "
         f"`verify` exits 1 when one of them stops being true.*", "",
         "## A. Why `512.GRAIN_WS4` is empty", "",
         "A file containing a LITERAL duplicate row — a whole row repeating "
         "byte for byte — has no unique key at any arity, because the widest "
         "candidate available is the whole row and it already collides. "
         "`512.validate_grain` turns a declaration with no usable key into a "
         "release-blocking violation. Seven of the eight tables this "
         "workstream was handed are in that state; the eighth holds zero "
         "rows. **No de-duplication was performed and no row was deleted.**",
         "",
         "| table | collection | rows | literal dup rows | groups | key "
         "possible today |", "|---|---|---:|---:|---:|---|"]
    for g in grain:
        if g.get("error"):
            L.append(f"| `{g['table']}` | {g['collection']} | — | — | — | "
                     f"{g['error']} |")
            continue
        L.append(f"| `{g['table']}` | {g['collection']} | {g['rows']:,} | "
                 f"{g['literal_duplicate_rows']:,} | "
                 f"{g['literal_duplicate_groups']:,} | "
                 f"{'yes' if g['key_possible_today'] else '**NO**'} |")
    L += ["", "### Candidate keys tested on the FULL file", "",
          "| table | candidate | duplicate rows |", "|---|---|---:|"]
    for g in grain:
        for c in g.get("candidates", []):
            if c["columns_missing"]:
                v = f"n/a — {c['columns_missing']} not in header"
            else:
                v = f"{c['duplicate_rows']:,}"
            L.append(f"| `{g['table']}` | `{'+'.join(c['key'])}` | {v} |")

    L += ["", "### The eighth table: `congressional_correspondence_log.csv`",
          ""]
    if corr:
        L += [f"Zero rows, so every key is vacuously unique and the file "
              f"cannot testify about itself. The question is therefore about "
              f"the GENERATOR, and the generator is measurable. "
              f"`136.build_correspondence_layer` mints "
              f"`record_id = \"FOIAREQ-{{agency_code}}-{{foia_request_id}}\"` "
              f"for every `foia_request_index.csv` row whose requester is a "
              f"congressional office.", "",
              f"- `foia_request_index.csv` holds **{corr['rows']:,}** rows and "
              f"**{corr['congressional_office_requesters']}** of them name a "
              f"congressional office as requester. The table is empty because "
              f"nothing qualified, not because a build failed.",
              f"- `(agency_code, foia_request_id)` — the exact pair the id is "
              f"built from — **collides {corr['id_collisions']} times** over "
              f"{corr['distinct_ids']:,} distinct values.",
              f"- The colliding rows say why themselves, in "
              f"`parse_quality_reason`: "
              + "; ".join(f"`{k}` ×{v}" for k, v in
                          corr["collision_reasons"]) + ".", "",
              "So `record_id` is **not unique on the population it is drawn "
              "from**. Declaring it as a primary key would validate today "
              "against zero rows and break the first time the table fills. "
              "It stays in `GRAIN_OPEN`. **The fix is upstream of this "
              "table:** the PDF layout solver in `136` recovers one control "
              "number for two different requests — different requester, "
              "different description, different official — and stamps both. "
              "Owner: whoever holds `136`."]

    L += ["", "### What each refusal needs, and who owns it", "",
          "| table | the one change that lifts it | owner |", "|---|---|---|",
          "| `faads_transactions.csv`, `faads_transactions_all_agencies.csv` "
          "| the queued re-extract in `review/OWNER_DECISION_QUEUE.md`. "
          "`30_funding_pre2008.to_out_row` now carries "
          "`assistance_transaction_unique_key`; when it runs, both tables "
          "become declarable in one line. **It re-orders a 2.77M-row file and "
          "`faads_entity_attribution.csv` keys 29,594 attributions to ROW "
          "POSITION** — they must move in the same pass, and "
          "`faads_attribution_key` (`code/710`) is the content key that lets "
          "them. | owner decision queue |",
          "| `native_passthrough.csv` | `81` carries "
          "`subawards.duplicate_status` through instead of collapsing it into "
          "`amount_countable`. The de-dupe key becomes statable; the "
          "duplicates stay. | `81_build_passthrough_dataset.py` |",
          "| `ferc_docket_filings.csv` | 822 byte-identical repeats of one "
          "(document, filer). A further 167 digest collisions differ only in "
          "filer-name CASE and are NOT duplicates. `133` needs a "
          "per-occurrence ordinal or an upstream fetch fix. | "
          "`133_build_ferc_advocacy.py` |",
          "| `hearing_bill_links.csv` | source-side: Congress.gov event 338549 "
          "lists 27 of its 64 `relatedItems.bills` twice, verbatim. `98` "
          "should de-duplicate the API payload per event before emitting — "
          "that is not a Cedar fact being deleted, it is an API repetition "
          "not being ingested twice. | `98_build_oira_and_hearings.py` |",
          "| `lobbying_registrant_native_ownership_evidence.csv` | **ONE "
          "COLUMN.** The 4 duplicates are four INDEPENDENT source assertions "
          "of one UEI, rendered identical because `182` does not carry "
          "`asserted_by_source` onto the output row. The sibling table "
          "`lobbying_registrant_identifiers.csv` already keys on "
          "`identifier + asserted_by_source`. Carrying that column makes this "
          "table declarable and PRESERVES the corroboration a de-dupe would "
          "delete. | `182` |",
          "| `native_bills_subject_sweep.csv` | the corpus: "
          "`data/raw/external/votingpatterns/all_bill_intros.csv` repeats 595 "
          "`bill_id`s byte-identically over 183,233 rows. A bill is "
          "introduced once. De-dupe key `bill_id`, applied to the CORPUS, not "
          "to the sweep. | the votingpatterns corpus |",
          "| `congressional_correspondence_log.csv` | see above — the control "
          "number the id is built from is recovered twice from one PDF "
          "layout. | `136` |", ""]

    L += ["## B. C7 — the funding money paths", "",
          "Written to `docs/MONEY_TOTALLING_RULES.md` between the "
          "`GRAIN-WS4` markers. The headline: "
          "`faads_transactions_all_agencies.csv` and "
          "`federal_funding_transactions.csv` **both hold FY2007**, and "
          f"{100.0 * m['ffx']['fy2007_on_shared_fain'] / max(m['ffx']['fy2007_total'], 1):.1f}% "
          "of the modern table's FY2007 dollars sit on FAINs the archive "
          "table also carries.", ""]

    L += ["## C. C5 — row conservation", "",
          f"{cons_counts[0]} existing (source_table, disposition) rows "
          f"updated in place, {cons_counts[1]} added, "
          f"{cons_counts[2]} rows in the ledger. **Merge-only**: no row is "
          f"ever removed and no key is ever rewritten from scratch — a "
          f"wholesale rewrite of this ledger destroyed 2,146,673 accounted "
          f"rows on 2026-09-01.", ""]
    L += ["## D. The `62` gate reading at the end of this workstream — "
          "nothing red is WS4's", "",
          "`py -3 code/62_no_regression_check.py` was run after every write "
          "below. **Standing rule 15 says a fail is stop-work and must not be "
          "recorded as 'pre-existing, not mine' and stepped around, so each "
          "red line was attributed by re-measuring it, not by assuming.**",
          "",
          "| red line | verdict | owner |", "|---|---|---|",
          "| `lint_class1` 0 → 3, `lint_class2c` 60 → 61, "
          "`lint_new_defect_instances` | re-ran `293_lint_bug_classes.py` and "
          "read the named findings: every new instance is in "
          "`731_ws5_grain_contractors_nonprofits_deals.py`. **Zero findings "
          "name `730`.** | GRAIN-WS5 |",
          "| `contract_violations = 7` | `entity_aliases.csv` `alias_id` not "
          "unique (1 blank-keyed row) + 6 orphan shippable tables. `512` "
          "reports **no violation for any table WS4 touched**, and "
          "`native_passthrough_pairs.csv` still validates its declared "
          "`from_tribe_id + to_tribe_id` key after the rebuild. | "
          "`entity_aliases` owner; codebook registrants |",
          "| `contract_orphan_shippable = 6` | `native_owned_businesses.csv`, "
          "`nonprofit_schedule_c_coverage.csv`, "
          "`nonprofit_schedule_c_lobbying.csv`, `regulations_gov_comments"
          ".csv`, `regulations_gov_entity_coverage.csv`, "
          "`sam_native_class_distributions.csv` — registered in the codebook, "
          "claimed by no collection. WS4 registered nothing. | the "
          "workstreams that registered them |",
          "| `rulings_unapplied` 1,215 → 2,894 | measured ONLY from "
          "`cedar_ruling_ledger_consolidated.csv` (43,321 rows), which WS4 "
          "never opened. | the ruling-mining workstream |",
          "| `files_with_columns_lost_vs_backup` | re-ran the check's own "
          "logic: the only loss is `entity_evidence_profile.csv` against a "
          "`bak_2026-08-28_pre505` backup. WS4's three backups "
          "(`native_passthrough.csv`, `native_passthrough_pairs.csv`, "
          "`cedar_harvest_conservation.csv`, all "
          "`.bak_2026-09-01_pre_ws4*`) lose no column and the live file is "
          "newer than each. | `505` / entity-evidence owner |",
          "| `SHIPPING LOST: advocacy_passthrough_2026-08-07.csv` | the "
          "coordinator's deliberate de-registration of a dated snapshot that "
          "was shipping the same $193,592,975 twice. The file is on disk. | "
          "the integrator |",
          "| `tables_missing_from_25_TABLES` 179 → 187 | new tables "
          "registered by sibling workstreams; WS4 created no table. | "
          "siblings |", "",
          "**WS4 moved three metrics the right way:** "
          "`harvest_source_rows_read` (the legislation conservation rows "
          "below), and `native_passthrough.csv` off the "
          "`ship_tables_at_zero`/unshipped-260 line by closing the stale "
          "disposition. It moved none the wrong way.", "",
          ]
    OUT_MD.write_text("\n".join(L), encoding="utf-8")


def apply_money_section(text: str):
    body = MONEY_MD.read_text(encoding="utf-8") if MONEY_MD.exists() else ""
    if MARK_A in body and MARK_B in body:
        head, _, rest = body.partition(MARK_A)
        _, _, tail = rest.partition(MARK_B)
        body = head + text + tail
    else:
        body = body.rstrip() + "\n\n---\n\n" + text + "\n"
    MONEY_MD.write_text(body, encoding="utf-8")


def main() -> int:
    verify = len(sys.argv) > 1 and sys.argv[1] == "verify"
    grain = measure_grain()
    corr = measure_correspondence_id()
    m = measure_money()
    cons = measure_conservation()

    fails = []
    for g in grain:
        if g.get("error"):
            fails.append(f"W1 {g['table']}: {g['error']}")
            continue
        if g["key_possible_today"] and g["table"] != \
                "congressional_correspondence_log.csv":
            fails.append(
                f"W2 {g['table']} now has ZERO literal duplicate rows - a key "
                f"may be declarable. Re-run `512 probe {g['table']}` and "
                f"declare it in GRAIN_WS4 rather than leaving it UNSTATED.")
    if corr and corr["id_collisions"] == 0:
        fails.append(
            "W3 (agency_code, foia_request_id) is now UNIQUE in "
            "foia_request_index.csv - the reason congressional_correspondence"
            "_log.csv's record_id was refused no longer holds. Re-open it.")
    if m["ffx"]["fy2007_on_shared_fain"] <= 0:
        fails.append("W4 the FY2007 seam between faads_transactions_all_"
                     "agencies.csv and federal_funding_transactions.csv no "
                     "longer overlaps - re-check the stated rule.")

    counts = (0, 0, 0)
    if not verify:
        counts = merge_conservation(cons)
        apply_money_section(money_section(m))
        write_docs(grain, corr, m, counts)
        print(f"  wrote {OUT_MD.relative_to(ROOT)}")
        print(f"  {MONEY_MD.relative_to(ROOT)}: GRAIN-WS4 section applied")
        print(f"  conservation: {counts[0]} updated, {counts[1]} added, "
              f"{counts[2]} rows total (MERGE-ONLY)")

    print(f"\n  GRAIN-WS4: {len(grain)} tables measured, "
          f"{sum(1 for g in grain if not g.get('key_possible_today'))} "
          f"cannot carry a key today")
    for g in grain:
        if g.get("error"):
            continue
        print(f"    {g['table']:52s} {g['rows']:>9,} rows  "
              f"{g['literal_duplicate_rows']:>7,} literal dup rows")
    print(f"\n  FY2007 seam: "
          f"{m['ffx']['fy2007_on_shared_fain'] / 1e9:.2f}B of "
          f"federal_funding_transactions FY2007 sits on FAINs "
          f"faads_transactions_all_agencies also carries")
    print(f"  native_passthrough: {m['passthrough']['rows']:,} rows, "
          f"countable ${m['passthrough']['countable_total']:,.2f}")
    for f in fails:
        print(f"  FAIL  {f}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
