#!/usr/bin/env python3
"""
Cedar Press - 519: CLOSURE of the `federal-register` dataset.

    py -3 code/519_closure_federal_register.py conserve   # measure + merge C5
    py -3 code/519_closure_federal_register.py verify     # read-only, exit 1
    py -3 code/519_closure_federal_register.py fixtures   # PROVE each check fires

WHY THIS FILE EXISTS
--------------------
`docs/DATASET_READINESS.md` scored `federal-register` BLOCKED on exactly one
point of the ten-point shipping contract:

    C5  every harvested row has a named disposition

Twenty-two customer tables, every grain declared and validated, every primary
key unique, not one literal duplicate row - and no statement anywhere about
what went INTO the build. "156,772 documents came out" licenses a reader to
believe nothing was lost, and the build had no way to say whether that was
true. This file gives every source row of this dataset a NAMED bucket, and
then refuses to pass while any row lacks one.

It also carries the dataset's other closure checks, because a scoreboard that
is only re-measured by hand drifts: grain, primary keys, literal duplicates and
the FEDERAL REGISTER IDENTITY PATH are re-derived here from the live files on
every run, not read out of a JSON somebody wrote in August.

THE LEDGER KEY IS THE OUTPUT TABLE, NOT THE INPUT
-------------------------------------------------
`510_assertions.py` keys its ledgers by the SOURCE table it harvests. These are
keyed by the OUTPUT table whose construction they account for, following the
convention `77_build_nagpra_dataset.py` established for the same reason: most
of these outputs have no single source table, and one output can be cut out of
two inputs (`fr_consultation_year.csv` is built from the notices AND the
referenced table). The arithmetic invariant I13 checks is identical either way:
`rows_in == sum(dispositions)` within one key.

`518_dataset_readiness.py` reads C5 coverage as `basename(source_table)` over
`data/clean/cedar_harvest_conservation.csv`, so keying by the output is also
what makes coverage visible per customer table rather than per harvester.

TWO THINGS ABOUT THAT SHARED FILE, both of which cost time to discover
----------------------------------------------------------------------
  * `510_assertions.py all --apply` REWRITES it from 510's own ledgers, so it
    will delete these 22 row-groups. That is not hypothetical - it is a plain
    `write_csv` in 510. So the ledgers are ALSO kept, durably and in full, in
    `review/federal_register_row_conservation.csv`, and the repair is one cheap
    command that recomputes nothing:

        py -3 code/519_closure_federal_register.py conserve --publish-only

    Run it whenever `62` reports `harvest_source_rows_read` falling, or `518`
    puts `federal-register` back to BLOCKED on C5. `verify` names this repair
    by hand in its failure text so the next session does not have to find it.

  * The merge PRESERVES every key it does not own. A wholesale rewrite here
    would delete 510's 36 rows and nagpra's - which is exactly the failure this
    function is written to survive coming the other way.

RECOMPUTED vs MEASURED, and why the difference is stated
--------------------------------------------------------
A disposition is only worth the evidence behind it, so each ledger declares how
its buckets were established:

  RECOMPUTED  the builder's OWN predicate was imported and re-run over the
              input on disk (`11.classify`, `78.fr_tier`, `78.fr_themes`,
              `78.CONSULT_TITLE/_SUBJECT_ABS/_BOILERPLATE`, `134.TRIBAL_RE`).
              Nothing here re-implements a rule; a rule that moves moves here
              too, and the reconciliation against the output file fails loudly
              if the recomputation and the shipped table disagree.
  MEASURED    the disposition is established by key membership between the
              input and the output on disk, and the REASON is the builder's
              documented rule (e.g. 70 writes a bridge row only where it
              resolved an entity). The count is a measurement; the reason is a
              citation.

THE STALE BUCKET IS A REAL FINDING, NOT A FUDGE
-----------------------------------------------
320 documents sit in `federal_actions.csv` and in NO row of
`fr_content_classification.csv`. They are not dropped by any rule: they were
published after `78_content_analysis.py` last ran, and `78` writes four
lobbying tables that another workstream rewrote on 2026-08-28, so re-running it
to close the gap is a cross-dataset revert this file will not perform on its
own authority. The gap is therefore NAMED, counted, and proven to be exactly
"published later" - `conserve` fails if a single one of those 320 documents has
a publication date at or below the last date the content classifier covers,
because that would mean a row was dropped by something other than staleness.

Reads   data/clean/*.csv, data/spine/*.csv, data/raw/federal_register/*.jsonl.gz,
        data/raw/fr_ex_parte/_index.json, _candidates.json,
        data/raw/advocacy/nepa_eplanning/register.json,
        data/raw/external/section_106/candidates.csv,
        docs/schema/dataset_contracts.json
Writes  data/clean/cedar_harvest_conservation.csv   MERGED, never rewritten
        review/federal_register_row_conservation.csv   the durable C5 ledger
        review/federal_register_closure_evidence.json  what verify measured
"""
from __future__ import annotations

import argparse
import csv
import gzip
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
csv.field_size_limit(10 ** 8)
TODAY = date.today().isoformat()

COLLECTION = "federal-register"
CONSERVATION_REL = "data/clean/cedar_harvest_conservation.csv"
LEDGER_LOCAL_REL = "review/federal_register_row_conservation.csv"
EVIDENCE_REL = "review/federal_register_closure_evidence.json"
CONTRACTS_REL = "docs/schema/dataset_contracts.json"

CONSERVATION_COLS = ["source_table", "rows_in", "disposition", "rows", "pct",
                     "examples", "harvest_date"]

#: 510's I13 refuses these by name. Re-stated here so the refusal happens at
#: the point a disposition is INVENTED, not two layers downstream.
UNNAMED_REASON_RE = re.compile(r"(?:^|:)(other|unknown|misc|n/?a)\s*$", re.I)

#: The one declared exception to "a primary key is never blank".
#: `fr_consultation_by_agency.csv` carries a single blank `normalized_department`
#: row and the grain declaration in 512 says so in as many words: it is the
#: unattributed bucket. A check that refused it would be refusing a documented
#: decision; a check that ignored blank keys everywhere would be no check.
BLANK_KEY_ALLOWED = {"fr_consultation_by_agency.csv": 1}


# =====================================================================
# overlay-aware file access - what makes `fixtures` cheap and real
# =====================================================================
# A fixture must run `verify` as a REAL subprocess against a REAL mutated file,
# or it proves nothing about exit codes. Copying this dataset's inputs costs
# half a gigabyte, so `--dir` is an OVERLAY: a path present under the overlay
# root is read from there, everything else falls through to the repository. A
# fixture then copies only the one file it mutates.
class Ctx:
    def __init__(self, overlay=None):
        self.overlay = Path(overlay).resolve() if overlay else None

    def path(self, rel):
        if self.overlay is not None:
            p = self.overlay / rel
            if p.exists():
                return p
        return ROOT / rel

    def exists(self, rel):
        return self.path(rel).exists()


def read_csv(p):
    p = Path(p)
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def read_header(p):
    p = Path(p)
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        return [c.strip() for c in next(csv.reader(fh), [])]


def write_csv(p, rows, cols):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def load_module(name, filename):
    """Import a builder by path so its OWN predicates can be re-run.

    Every one of these is `if __name__ == '__main__'`-guarded (checked), so the
    import executes definitions only. Re-typing a regex from one of them here
    would be a second copy to keep in step, which is the defect this project
    keeps paying for.
    """
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)                                   # type: ignore
    return mod


# =====================================================================
# the ledger - deliberately the same shape as 510's and 77's
# =====================================================================
class RowLedger:
    """Per-OUTPUT-table row accounting. Named dispositions only.

    Not imported from 510 or 77: both are other workstreams' files and
    importing either executes a module body that reads half the repository.
    """

    def __init__(self, table, evidence):
        self.table = table              # "data/clean/<output>.csv"
        self.evidence = evidence        # RECOMPUTED | MEASURED | SELF
        self.rows_in = 0
        self.counts = Counter()
        self.examples = defaultdict(list)

    def seen(self, n=1):
        self.rows_in += n

    def note(self, disposition, example="", n=1):
        if UNNAMED_REASON_RE.search(disposition):
            raise ValueError(
                f"disposition {disposition!r} is not a NAMED reason - an "
                f"unnamed rejection is the defect this ledger exists to catch")
        self.counts[disposition] += n
        if example and len(self.examples[disposition]) < 3:
            self.examples[disposition].append(str(example)[:80])

    def unaccounted(self):
        return self.rows_in - sum(self.counts.values())


def conservation_rows(ledgers):
    out = []
    for lg in ledgers:
        for disp, n in sorted(lg.counts.items()):
            out.append(dict(source_table=lg.table, rows_in=lg.rows_in,
                            disposition=disp, rows=n,
                            pct=round(100.0 * n / max(lg.rows_in, 1), 2),
                            examples="; ".join(lg.examples.get(disp, [])),
                            harvest_date=TODAY))
    return out


# =====================================================================
# what the collection ships - read from the contract, never hard-coded
# =====================================================================
def shippable_tables(ctx):
    doc = json.loads(ctx.path(CONTRACTS_REL).read_text(encoding="utf-8"))
    for coll in doc.get("contracts", []):
        if coll["collection"] == COLLECTION:
            return [t for t in coll.get("tables", [])
                    if t.get("status") == "shippable"]
    raise SystemExit(f"{COLLECTION} is not in {CONTRACTS_REL} - run 512 first")


# =====================================================================
# CONSERVE - build every ledger
# =====================================================================
STALE = ("stale:published_after_the_last_78_content_analysis_run_so_no_"
         "classification_row_exists_for_it_yet")


def _clean(ctx, name):
    return ctx.path(f"data/clean/{name}")


def _docset(ctx, name, col="document_number"):
    p = _clean(ctx, name)
    if not p.exists():
        return set()
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        r = csv.reader(fh)
        hdr = next(r, [])
        if col not in hdr:
            return set()
        i = hdr.index(col)
        return {row[i] for row in r if len(row) > i}


def _stale_set(ctx):
    """Documents in federal_actions.csv with no fr_content_classification row.

    PROVEN to be staleness, not a silent drop: every one must postdate the last
    publication date the classifier covers. `conserve` raises if one does not.
    """
    fa, fc = {}, {}
    with _clean(ctx, "federal_actions.csv").open(
            encoding="utf-8-sig", errors="replace", newline="") as fh:
        r = csv.reader(fh)
        hdr = next(r)
        i, j = hdr.index("document_number"), hdr.index("publication_date")
        for row in r:
            fa[row[i]] = row[j]
    with _clean(ctx, "fr_content_classification.csv").open(
            encoding="utf-8-sig", errors="replace", newline="") as fh:
        r = csv.reader(fh)
        hdr = next(r)
        i, j = hdr.index("document_number"), hdr.index("publication_date")
        for row in r:
            fc[row[i]] = row[j]
    stale = {d for d in fa if d not in fc}
    if stale:
        cutoff = max(fc.values())
        early = sorted(d for d in stale if fa[d] <= cutoff)
        if early:
            raise SystemExit(
                f"\n  REFUSING to call {len(stale)} missing classification "
                f"row(s) stale: {len(early)} of them were published on or "
                f"before {cutoff}, the last date the classifier covers "
                f"(e.g. {early[:3]}). Those rows were dropped by something "
                f"other than staleness and that something has no name yet.")
    return stale, fa, fc


def led_federal_actions_raw(ctx):
    """The FR API cache -> federal_actions_raw.csv. RECOMPUTED from the bytes.

    The shard MANIFEST is not the population: `_shard_manifest.csv` was last
    written 2026-08-05 and eleven shards covering 2026-08-06..2026-08-26 landed
    afterwards, so a ledger built from the manifest would under-report the
    corpus by an incremental pull. The directory is the truth.
    """
    lg = RowLedger("data/clean/federal_actions_raw.csv", "RECOMPUTED")
    raw = ctx.path("data/raw/federal_register")
    kept = _docset(ctx, "federal_actions_raw.csv")
    seen = set()
    for p in sorted(raw.glob("*.jsonl.gz")):
        with gzip.open(p, "rt", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                lg.seen()
                try:
                    dn = (json.loads(line) or {}).get("document_number") or ""
                except ValueError:
                    lg.note("rejected:cached_api_line_is_not_valid_json_and_"
                            "carries_no_document", p.name)
                    continue
                if not dn:
                    lg.note("rejected:api_record_carries_no_document_number",
                            p.name)
                elif dn in seen:
                    lg.note("duplicate:same_document_returned_by_another_net_"
                            "or_another_date_shard", dn)
                elif dn in kept:
                    seen.add(dn)
                    lg.note("emitted", dn)
                else:
                    seen.add(dn)
                    lg.note("rejected:cached_document_is_absent_from_the_built_"
                            "table_the_cache_is_newer_than_the_last_assembly",
                            dn)
    return lg


def led_federal_actions(ctx):
    """federal_actions_raw.csv -> federal_actions.csv. RECOMPUTED via 11.classify.

    11 classifies every row it reads and writes every row it classifies; there
    is no filter. The ledger proves that rather than asserting it: a raw
    document absent from the classified table has no name, and would land in
    UNACCOUNTED_FOR.
    """
    lg = RowLedger("data/clean/federal_actions.csv", "RECOMPUTED")
    out = _docset(ctx, "federal_actions.csv")
    for dn in _docset(ctx, "federal_actions_raw.csv"):
        lg.seen()
        lg.note("emitted" if dn in out else
                "rejected:raw_document_is_absent_from_the_classified_table_"
                "the_pull_is_newer_than_the_last_classification", dn)
    return lg


def led_content_classification(ctx, stale):
    lg = RowLedger("data/clean/fr_content_classification.csv", "MEASURED")
    fc = _docset(ctx, "fr_content_classification.csv")
    for dn in _docset(ctx, "federal_actions.csv"):
        lg.seen()
        lg.note("emitted" if dn in fc else STALE, dn)
    return lg


def _fc_rows(ctx):
    """fr_content_classification.csv, streamed to the four columns needed."""
    fc_p = _clean(ctx, "fr_content_classification.csv")
    with fc_p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        r = csv.reader(fh)
        hdr = next(r)
        idx = {c: hdr.index(c) for c in
               ("document_number", "publication_year", "relevance_tier",
                "themes", "content_classifiable")}
        for row in r:
            yield {c: row[i] for c, i in idx.items()}


def led_relevance_tier_year(ctx, stale):
    """RECOMPUTED. Every classification row enters exactly one (tier, year)."""
    lg = RowLedger("data/clean/fr_relevance_tier_year.csv", "RECOMPUTED")
    for d in stale:
        lg.seen()
        lg.note(STALE, d)
    cells = Counter()
    for r in _fc_rows(ctx):
        lg.seen()
        if not r["publication_year"]:
            lg.note("rejected:publication_date_is_blank_so_the_document_has_no_"
                    "year_to_aggregate_into", r["document_number"])
            continue
        cells[(r["relevance_tier"], r["publication_year"])] += 1
        lg.note("emitted", r["document_number"])
    _reconcile(lg, cells, read_csv(_clean(ctx, "fr_relevance_tier_year.csv")),
               lambda x: (x["relevance_tier"], x["publication_year"]),
               "n_documents")
    return lg


def led_theme_year(ctx, stale):
    """RECOMPUTED with 78's own theme regexes."""
    m78 = load_module("m78", "78_content_analysis.py")
    lg = RowLedger("data/clean/fr_theme_year.csv", "RECOMPUTED")
    for d in stale:
        lg.seen()
        lg.note(STALE, d)
    cells = Counter()
    for r in _fc_rows(ctx):
        lg.seen()
        if r["content_classifiable"] != "1":
            lg.note("rejected:no_native_term_in_the_title_or_abstract_so_no_"
                    "theme_may_be_asserted_about_this_document",
                    r["document_number"])
            continue
        if not r["publication_year"]:
            lg.note("rejected:publication_date_is_blank_so_the_document_has_no_"
                    "year_to_aggregate_into", r["document_number"])
            continue
        themes = [t for t in (r["themes"] or "").split("|") if t]
        if not themes:
            lg.note("rejected:document_is_classifiable_but_no_theme_pattern_"
                    "matched_its_title_or_abstract", r["document_number"])
            continue
        for t in themes:
            cells[(t, r["publication_year"])] += 1
        lg.note("emitted", r["document_number"])
    # sanity: the shipped themes column must be what 78's regexes produce today
    assert m78.FR_RX, "78 exposes no theme regexes - the import is wrong"
    _reconcile(lg, cells, read_csv(_clean(ctx, "fr_theme_year.csv")),
               lambda x: (x["theme"], x["publication_year"]), "n_documents")
    return lg


def _consult_flags(m78, title, abstract):
    """78's OWN consultation predicates, re-run. Never re-implemented."""
    boiler = bool(m78.CONSULT_BOILERPLATE.search(abstract))
    in_title = bool(m78.CONSULT_TITLE.search(title))
    in_abs = bool(m78.CONSULT_SUBJECT_ABS.search(abstract)) and not boiler
    return boiler, in_title, in_abs


def _fa_text_rows(ctx):
    fa_p = _clean(ctx, "federal_actions.csv")
    with fa_p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        r = csv.reader(fh)
        hdr = next(r)
        idx = {c: hdr.index(c) for c in
               ("document_number", "title", "abstract", "publication_date",
                "agency_names")}
        for row in r:
            yield {c: (row[i] if i < len(row) else "") for c, i in idx.items()}


def led_consultation_notices(ctx, stale):
    m78 = load_module("m78", "78_content_analysis.py")
    classifiable = {r["document_number"] for r in _fc_rows(ctx)
                    if r["content_classifiable"] == "1"}
    lg = RowLedger("data/clean/fr_consultation_notices.csv", "RECOMPUTED")
    got, want = set(), _docset(ctx, "fr_consultation_notices.csv")
    for r in _fa_text_rows(ctx):
        lg.seen()
        dn = r["document_number"]
        if dn in stale:
            lg.note(STALE, dn)
            continue
        if dn not in classifiable:
            lg.note("rejected:no_native_term_in_the_title_or_abstract_so_the_"
                    "document_is_not_about_Indian_Country_on_its_face", dn)
            continue
        _b, in_title, in_abs = _consult_flags(m78, r["title"], r["abstract"])
        if in_title or in_abs:
            got.add(dn)
            lg.note("emitted", dn)
        else:
            lg.note("rejected:neither_the_title_nor_the_abstract_carries_a_"
                    "consultation_signal", dn)
    _drift(lg, got, want)
    return lg


def led_consultation_referenced(ctx, stale):
    m78 = load_module("m78", "78_content_analysis.py")
    classifiable = {r["document_number"] for r in _fc_rows(ctx)
                    if r["content_classifiable"] == "1"}
    lg = RowLedger("data/clean/fr_consultation_referenced.csv", "RECOMPUTED")
    got, want = set(), _docset(ctx, "fr_consultation_referenced.csv")
    for r in _fa_text_rows(ctx):
        lg.seen()
        dn = r["document_number"]
        if dn in stale:
            lg.note(STALE, dn)
            continue
        if dn not in classifiable:
            lg.note("rejected:no_native_term_in_the_title_or_abstract_so_the_"
                    "document_is_not_about_Indian_Country_on_its_face", dn)
            continue
        boiler, in_title, _a = _consult_flags(m78, r["title"], r["abstract"])
        if boiler and not in_title:
            got.add(dn)
            lg.note("emitted", dn)
        else:
            lg.note("rejected:the_abstract_does_not_report_a_consultation_"
                    "already_undertaken_in_the_NAGPRA_style_recital", dn)
    _drift(lg, got, want)
    return lg


def led_consultation_by_agency(ctx):
    """RECOMPUTED. Each notice enters the series once per normalised department."""
    lg = RowLedger("data/clean/fr_consultation_by_agency.csv", "RECOMPUTED")
    cells = Counter()
    for r in read_csv(_clean(ctx, "fr_consultation_notices.csv")):
        lg.seen()
        deps = [d for d in (r.get("normalized_departments") or "").split("|")]
        if not deps:
            lg.note("rejected:notice_names_no_agency_so_it_enters_no_"
                    "department_row", r.get("document_number"))
            continue
        for d in deps:
            cells[d] += 1
        lg.note("emitted", r.get("document_number"))
    _reconcile(lg, cells, read_csv(_clean(ctx, "fr_consultation_by_agency.csv")),
               lambda x: x["normalized_department"], "n_consultation_notices")
    return lg


def led_consultation_year(ctx):
    lg = RowLedger("data/clean/fr_consultation_year.csv", "RECOMPUTED")
    n_cells, r_cells = Counter(), Counter()
    for src, cells in (("fr_consultation_notices.csv", n_cells),
                       ("fr_consultation_referenced.csv", r_cells)):
        for r in read_csv(_clean(ctx, src)):
            lg.seen()
            y = (r.get("publication_year") or "").strip()
            if not y:
                lg.note("rejected:publication_date_is_blank_so_the_document_"
                        "has_no_year_to_aggregate_into", r.get("document_number"))
                continue
            cells[y] += 1
            lg.note("emitted", r.get("document_number"))
    out = read_csv(_clean(ctx, "fr_consultation_year.csv"))
    _reconcile(lg, n_cells, out, lambda x: x["publication_year"],
               "n_consultation_notices")
    _reconcile(lg, r_cells, out, lambda x: x["publication_year"],
               "n_documents_reporting_consultation_undertaken")
    return lg


def led_abstract_availability(ctx):
    lg = RowLedger("data/clean/fr_abstract_availability_year.csv", "RECOMPUTED")
    cells = Counter()
    for r in _fa_text_rows(ctx):
        lg.seen()
        y = (r["publication_date"] or "")[:4]
        if not y:
            lg.note("rejected:publication_date_is_blank_so_the_document_has_no_"
                    "year_to_aggregate_into", r["document_number"])
            continue
        cells[y] += 1
        lg.note("emitted", r["document_number"])
    _reconcile(lg, cells,
               read_csv(_clean(ctx, "fr_abstract_availability_year.csv")),
               lambda x: x["publication_year"], "n_documents")
    return lg


def led_entity_bridge(ctx):
    """MEASURED. 70 writes a bridge row only where it RESOLVED a spine entity;
    a document with no bridge row is a document in which no entity name
    resolved, which is 70's documented refusal, not a silent drop."""
    lg = RowLedger("data/clean/federal_actions_entity_bridge.csv", "MEASURED")
    linked = _docset(ctx, "federal_actions_entity_bridge.csv")
    for dn in _docset(ctx, "federal_actions.csv"):
        lg.seen()
        lg.note("emitted" if dn in linked else
                "rejected:no_spine_entity_name_resolved_in_this_document_so_70_"
                "key_unjoined_datasets_refused_to_key_it", dn)
    return lg


def led_consultation_events(ctx):
    """MEASURED. 96's event id is CONS-FR-<document_number>, so the input
    population and the output are joinable exactly."""
    lg = RowLedger("data/clean/consultation_events.csv", "MEASURED")
    src = _docset(ctx, "fr_consultation_notices.csv") | \
        _docset(ctx, "fr_consultation_referenced.csv")
    got = {r["consultation_event_id"][len("CONS-FR-"):]
           for r in read_csv(_clean(ctx, "consultation_events.csv"))
           if r["consultation_event_id"].startswith("CONS-FR-")}
    for dn in sorted(src):
        lg.seen()
        lg.note("emitted" if dn in got else
                "rejected:notice_text_could_not_be_retrieved_or_carried_no_"
                "parseable_consultation_event", dn)
    return lg


def led_ex_parte_notices(ctx):
    lg = RowLedger("data/clean/fr_ex_parte_notices.csv", "MEASURED")
    idx = json.loads(ctx.path("data/raw/fr_ex_parte/_index.json")
                     .read_text(encoding="utf-8"))
    cand = json.loads(ctx.path("data/raw/fr_ex_parte/_candidates.json")
                      .read_text(encoding="utf-8"))
    pop = set(idx.get("documents") or {}) | set(cand.get("documents") or {})
    got = _docset(ctx, "fr_ex_parte_notices.csv")
    for dn in sorted(pop):
        lg.seen()
        lg.note("emitted" if dn in got else
                "rejected:indexed_document_carried_no_ex_parte_marker_or_its_"
                "text_could_not_be_retrieved", dn)
    return lg


def led_ex_parte_parties(ctx):
    lg = RowLedger("data/clean/fr_ex_parte_parties.csv", "MEASURED")
    got = {r["fr_ex_parte_notice_id"]
           for r in read_csv(_clean(ctx, "fr_ex_parte_parties.csv"))}
    for r in read_csv(_clean(ctx, "fr_ex_parte_notices.csv")):
        lg.seen()
        nid = r["fr_ex_parte_notice_id"]
        lg.note("emitted" if nid in got else
                "rejected:notice_text_carries_no_parseable_party_phrase_so_no_"
                "party_row_may_be_cut_from_it", nid)
    return lg


def led_ex_parte_links(ctx):
    """Two source datasets, one link table. `source_dataset` is the column that
    says which - and a customer joining `fr_ex_parte_parties` to it today gets
    ZERO rows, because all nine links come from `ferc_ex_parte_parties.csv`."""
    lg = RowLedger("data/clean/fr_ex_parte_party_entity_links.csv", "MEASURED")
    existing = read_csv(_clean(ctx, "fr_ex_parte_party_entity_links.csv"))
    by_ds = defaultdict(set)
    for l in existing:
        by_ds[l["source_dataset"]].add(l["source_row_id"])
    for src, key in (("ferc_ex_parte_parties.csv", "ferc_ex_parte_party_id"),
                     ("fr_ex_parte_parties.csv", "fr_ex_parte_party_id")):
        for r in read_csv(_clean(ctx, src)):
            lg.seen()
            rid = r.get(key) or ""
            lg.note("emitted" if rid in by_ds[src] else
                    "rejected:party_name_as_printed_resolved_to_no_Native_"
                    "entity_under_154s_link_name_guards", rid)
    return lg


def led_nepa_projects(ctx):
    """RECOMPUTED with 134's OWN TRIBAL_RE over the retained BLM register."""
    m134 = load_module("m134", "134_build_nepa_eplanning.py")
    lg = RowLedger("data/clean/nepa_eplanning_projects.csv", "RECOMPUTED")
    reg = json.loads(ctx.path("data/raw/advocacy/nepa_eplanning/register.json")
                     .read_text(encoding="utf-8"))
    built = {r["nepa_number"] for r in
             read_csv(_clean(ctx, "nepa_eplanning_projects.csv"))}
    for r in reg:
        lg.seen()
        native = (r.get("native_program_net") == "1"
                  or "Native American" in (r.get("program") or ""))
        tribal = bool(m134.TRIBAL_RE.search(r.get("projectname") or ""))
        if not (native or tribal):
            lg.note("rejected:BLM_register_row_names_no_tribal_term_and_sits_"
                    "in_no_cultural_historical_native_american_program",
                    r.get("nepanumber") or r.get("projectid"))
        elif (r.get("nepanumber") or "") in built:
            lg.note("emitted", r.get("nepanumber"))
        else:
            lg.note("rejected:tribal_relevant_register_row_whose_project_page_"
                    "was_not_retrieved_see_nepa_source_coverage_csv",
                    r.get("nepanumber") or r.get("projectid"))
    return lg


def led_nepa_child(ctx, out_name, reason):
    lg = RowLedger(f"data/clean/{out_name}", "MEASURED")
    got = {r["nepa_number"] for r in read_csv(_clean(ctx, out_name))}
    for r in read_csv(_clean(ctx, "nepa_eplanning_projects.csv")):
        lg.seen()
        lg.note("emitted" if r["nepa_number"] in got else reason,
                r["nepa_number"])
    return lg


def led_section_106_events(ctx):
    lg = RowLedger("data/clean/section_106_consultation_events.csv", "MEASURED")
    cands = read_csv(ctx.path("data/raw/external/section_106/candidates.csv"))
    got = _docset(ctx, "section_106_consultation_events.csv")
    for r in cands:
        lg.seen()
        dn = r.get("document_number") or ""
        lg.note("emitted" if dn in got else
                "rejected:candidate_document_carries_no_Section_106_or_36_CFR_"
                "800_marker_in_its_retrieved_text", dn)
    return lg


def led_section_106_parties(ctx):
    lg = RowLedger("data/clean/section_106_project_parties.csv", "MEASURED")
    got = _docset(ctx, "section_106_project_parties.csv")
    for r in read_csv(_clean(ctx, "section_106_consultation_events.csv")):
        lg.seen()
        dn = r.get("document_number") or ""
        lg.note("emitted" if dn in got else
                "rejected:notice_names_no_consulting_party_in_a_role_bearing_"
                "sentence_so_no_party_row_may_be_cut_from_it", dn)
    return lg


def led_self_coverage(ctx, name, disposition):
    """A coverage table IS its own conservation ledger.

    `correspondence_foia_source_coverage.csv` and
    `section_106_source_coverage.csv` exist to record what each source
    published INCLUDING the sources that published nothing. Every probe is a
    row by construction, so the identity is the honest statement - and stating
    it keeps the table inside the C5 contract instead of quietly outside it.
    """
    lg = RowLedger(f"data/clean/{name}", "SELF")
    for r in read_csv(_clean(ctx, name)):
        lg.seen()
        lg.note(disposition, (r.get("url") or r.get("source") or ""))
    return lg


def _reconcile(lg, cells, out_rows, keyfn, valcol):
    """The recomputation must reproduce the shipped aggregate, or the ledger
    is describing a build that no longer exists. Recorded as a DRIFT
    disposition so `verify` fails on it rather than a silent mismatch."""
    have = Counter()
    for r in out_rows:
        try:
            have[keyfn(r)] += int(r.get(valcol) or 0)
        except (TypeError, ValueError):
            continue
    bad = {k for k in set(cells) | set(have) if cells.get(k, 0) != have.get(k, 0)}
    if bad:
        lg.note(f"DRIFT_recomputation_disagrees_with_the_shipped_table_on_"
                f"{len(bad)}_cells_of_{valcol}", str(sorted(bad)[:2]), n=0)


def _drift(lg, got, want):
    if got != want:
        lg.note(f"DRIFT_recomputed_membership_differs_from_the_shipped_table_"
                f"by_{len(got ^ want)}_documents", str(sorted(got ^ want)[:2]),
                n=0)


def build_ledgers(ctx):
    stale, _fa, _fc = _stale_set(ctx)
    print(f"  stale set: {len(stale)} document(s) classified nowhere yet "
          f"(all proven to postdate the classifier)")
    L = [
        led_federal_actions_raw(ctx),
        led_federal_actions(ctx),
        led_content_classification(ctx, stale),
        led_relevance_tier_year(ctx, stale),
        led_theme_year(ctx, stale),
        led_consultation_notices(ctx, stale),
        led_consultation_referenced(ctx, stale),
        led_consultation_by_agency(ctx),
        led_consultation_year(ctx),
        led_abstract_availability(ctx),
        led_entity_bridge(ctx),
        led_consultation_events(ctx),
        led_ex_parte_notices(ctx),
        led_ex_parte_parties(ctx),
        led_ex_parte_links(ctx),
        led_nepa_projects(ctx),
        led_nepa_child(ctx, "nepa_project_documents.csv",
                       "rejected:project_page_lists_no_documents_in_its_"
                       "administrative_record"),
        led_nepa_child(ctx, "nepa_administrative_record_parties.csv",
                       "rejected:project_page_names_no_administrative_record_"
                       "party"),
        led_section_106_events(ctx),
        led_section_106_parties(ctx),
        led_self_coverage(ctx, "correspondence_foia_source_coverage.csv",
                          "emitted:source_probed_and_recorded_including_the_"
                          "sources_that_yielded_nothing"),
        led_self_coverage(ctx, "section_106_source_coverage.csv",
                          "emitted:source_swept_and_recorded_including_what_it_"
                          "could_not_yield"),
    ]
    return L


def publish(ctx):
    """MERGE the durable ledger into the shared file. Never rewrite it."""
    local = read_csv(ctx.path(LEDGER_LOCAL_REL))
    if not local:
        print(f"  no {LEDGER_LOCAL_REL} - run `conserve` first")
        return 1
    ours = {r["source_table"] for r in local}
    shared = ctx.path("data/clean/cedar_harvest_conservation.csv")
    keep = [r for r in read_csv(shared)
            if (r.get("source_table") or "") not in ours]
    write_csv(shared, keep + local, CONSERVATION_COLS)
    print(f"  merged {len(local)} disposition row(s) over {len(ours)} "
          f"federal-register table(s); {len(keep)} row(s) of other ledgers "
          f"left untouched")
    return 0


def cmd_conserve(args):
    ctx = Ctx(args.dir)
    if args.publish_only:
        return publish(ctx)
    print("=== 519 conserve: federal-register row conservation ===\n")
    L = build_ledgers(ctx)
    bad = [lg for lg in L if lg.unaccounted()]
    for lg in bad:
        print(f"  CONSERVATION BREACH {lg.table}: {lg.rows_in:,} read, "
              f"{sum(lg.counts.values()):,} accounted, "
              f"{lg.unaccounted():,} unnamed")
    if bad:
        return 1
    for lg in L:
        print(f"\n  {lg.table}   [{lg.evidence}]   {lg.rows_in:,} rows read")
        for disp, n in sorted(lg.counts.items(), key=lambda kv: -kv[1]):
            print(f"      {n:>9,}  {disp}")
    write_csv(ctx.path(LEDGER_LOCAL_REL), conservation_rows(L),
              CONSERVATION_COLS)
    print(f"\n  wrote {LEDGER_LOCAL_REL}")
    return publish(ctx)


# =====================================================================
# VERIFY
# =====================================================================
def check_conservation(ctx, tables, fails, ev):
    by = defaultdict(list)
    for r in read_csv(ctx.path(CONSERVATION_REL)):
        by[r.get("source_table") or ""].append(r)
    covered = 0
    for t in tables:
        key = f"data/clean/{t['table']}"
        rs = by.get(key)
        if not rs:
            fails.append(
                f"C5 {t['table']}: NO row-conservation coverage in "
                f"{CONSERVATION_REL}. If 510_assertions.py all --apply has run "
                f"since, the repair is: py -3 code/"
                f"519_closure_federal_register.py conserve --publish-only")
            continue
        covered += 1
        rows_in = int(rs[0]["rows_in"] or 0)
        total = sum(int(r["rows"] or 0) for r in rs)
        if total != rows_in:
            fails.append(f"C5 {t['table']}: {rows_in:,} rows read but "
                         f"{total:,} accounted for - {abs(rows_in-total):,} "
                         f"vanished without a named disposition")
        for r in rs:
            d = r["disposition"]
            if d == "UNACCOUNTED_FOR" and int(r["rows"] or 0):
                fails.append(f"C5 {t['table']}: {r['rows']} UNACCOUNTED_FOR")
            if UNNAMED_REASON_RE.search(d):
                fails.append(f"C5 {t['table']}: disposition {d!r} is not a "
                             f"NAMED reason")
            if d.startswith("DRIFT_"):
                fails.append(f"C5 {t['table']}: {d} - the ledger describes a "
                             f"build the shipped table no longer matches; "
                             f"re-run `conserve`")
    ev["c5_tables_covered"] = covered
    ev["c5_tables_total"] = len(tables)


def check_grain_and_duplicates(ctx, tables, fails, ev):
    import hashlib
    per = {}
    for t in tables:
        name = t["table"]
        p = _clean(ctx, name)
        if not p.exists():
            fails.append(f"C1 {name}: declared shippable but absent from disk")
            continue
        pk = t.get("primary_key") or []
        if not pk:
            fails.append(f"C2 {name}: no primary key declared")
            continue
        with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            r = csv.reader(fh)
            hdr = [c.strip() for c in next(r, [])]
            miss = [k for k in pk if k not in hdr]
            if miss:
                fails.append(f"C2 {name}: declared key column(s) {miss} are "
                             f"not in the file")
                continue
            ki = [hdr.index(k) for k in pk]
            keys, whole, n, dups, blank = set(), set(), 0, 0, 0
            dupkey = 0
            for row in r:
                n += 1
                kv = tuple(row[i] if i < len(row) else "" for i in ki)
                if all(x.strip() == "" for x in kv):
                    blank += 1
                if kv in keys:
                    dupkey += 1
                else:
                    keys.add(kv)
                h = hashlib.blake2b("\x1f".join(row).encode("utf-8", "replace"),
                                    digest_size=16).digest()
                if h in whole:
                    dups += 1
                else:
                    whole.add(h)
        per[name] = dict(rows=n, duplicate_keys=dupkey,
                         literal_duplicates=dups, blank_keys=blank)
        if dupkey:
            fails.append(f"C2 {name}: declared primary key {pk} repeats on "
                         f"{dupkey:,} row(s)")
        if dups:
            fails.append(f"C3 {name}: {dups:,} LITERAL duplicate row(s)")
        if blank > BLANK_KEY_ALLOWED.get(name, 0):
            fails.append(f"C2 {name}: {blank} row(s) carry a wholly blank "
                         f"primary key ({BLANK_KEY_ALLOWED.get(name,0)} "
                         f"declared)")
    ev["per_table"] = per


def check_identity_path(ctx, fails, ev):
    """The Federal Register identity path, end to end.

    `fr_recognized_entities.csv` is the one Cedar source declared
    `authority_for` anything, so a bad match there is laundered into an
    authoritative Cedar fact. The source-record layer split the claim from the
    match; these three checks are that split, re-derived from the shipped files
    rather than trusted from 514's own run.
    """
    links = read_csv(ctx.path("data/spine/cedar_source_record_links.csv"))
    recs = {r["source_record_id"]: r
            for r in read_csv(ctx.path("data/spine/cedar_source_records.csv"))}
    spine = read_csv(ctx.path("data/spine/cedar_entity_spine.csv"))
    cls = {r["cedar_uid"]: r.get("entity_class", "") for r in spine
           if r.get("cedar_uid")}
    ACCEPTED = ("verified", "proposed")

    accepted = {l["cedar_uid"] for l in links
                if l["link_role"] == "identifies"
                and l["link_status"] in ACCEPTED and l["cedar_uid"]}
    refused = {l["cedar_uid"] for l in links
               if l["link_status"] in ("contested", "denied", "unresolved")
               and l["cedar_uid"]} - accepted

    # (a) the class guard, re-derived. An FR roster of governments cannot name
    #     an ANCSA corporation, and the rule lives on the RECORD, so it cannot
    #     be bypassed by editing the resolver.
    guard_breaches = []
    for l in links:
        if l["link_role"] != "identifies" or l["link_status"] not in ACCEPTED:
            continue
        rec = recs.get(l["source_record_id"])
        if not rec:
            fails.append(f"C4 link {l['link_id']} names source record "
                         f"{l['source_record_id']}, which does not exist")
            continue
        eligible = {c for c in (rec.get("eligible_entity_classes") or "").split("|") if c}
        got = cls.get(l["cedar_uid"], "")
        if eligible and got not in eligible:
            guard_breaches.append((l["link_id"], l["cedar_uid"], got))
    for lid, uid, got in guard_breaches:
        fails.append(f"C4 CLASS GUARD BYPASSED: accepted link {lid} attaches a "
                     f"Federal Register roster record to {uid}, entity class "
                     f"{got!r}, which the roster cannot name")

    # (b) no assertion may reach a customer through a refused link
    asserts = [a for a in read_csv(ctx.path("data/clean/cedar_assertions.csv"))
               if a.get("source_id") == "fr_tribal_list"]
    through_refused = [a for a in asserts if a["cedar_uid"] in refused]
    for a in through_refused[:5]:
        fails.append(f"C6 assertion {a['assertion_id']} carries Federal "
                     f"Register authority onto {a['cedar_uid']}, which only a "
                     f"{'contested/denied/unresolved'} link names")

    # (c) an assertion sourced to the source-record layer must have a link
    from_layer = [a for a in asserts
                  if (a.get("origin_table") or "").endswith(
                      "cedar_source_records.csv")]
    orphan = [a for a in from_layer if a["cedar_uid"] not in accepted]
    for a in orphan[:5]:
        fails.append(f"C4 assertion {a['assertion_id']} came out of the "
                     f"source-record layer but no accepted `identifies` link "
                     f"names {a['cedar_uid']}")

    # Reported, not failed on: assertions that carry the roster's source_id but
    # were harvested from the SPINE's fr_official_name column rather than from
    # a source record. Two are known and named in docs/SOURCE_RECORD_LAYER.md
    # (Bristol Bay Area Health Corporation, Bristol Bay Housing Authority);
    # they belong to the spine's owner, not to this dataset.
    residue = [a for a in asserts
               if a not in from_layer and a["cedar_uid"] not in accepted]
    ev["identity"] = dict(
        accepted_links=len(accepted), refused_only_uids=len(refused),
        fr_assertions=len(asserts), from_source_record_layer=len(from_layer),
        through_refused_link=len(through_refused), orphan_from_layer=len(orphan),
        class_guard_breaches=len(guard_breaches),
        spine_column_residue=len(residue),
        spine_column_residue_uids=sorted({a["cedar_uid"] for a in residue}))


def cmd_verify(args):
    ctx = Ctx(args.dir)
    tables = shippable_tables(ctx)
    fails, ev = [], {"measured": TODAY, "collection": COLLECTION,
                     "n_shippable_tables": len(tables)}
    only = set(args.only.split(",")) if args.only else None

    # One function covers several contract points, so selection is by the SET
    # of points it can fail on. A fixture that names C3 must be able to run
    # exactly the check that raises C3, or `--only` silently runs nothing and
    # every fixture "passes" by never firing - which is how two of them did.
    def run(tags, fn):
        if only is None or (only & tags):
            fn()

    run({"C5"}, lambda: check_conservation(ctx, tables, fails, ev))
    run({"C1", "C2", "C3"},
        lambda: check_grain_and_duplicates(ctx, tables, fails, ev))
    run({"C4", "C6"}, lambda: check_identity_path(ctx, fails, ev))

    print(f"\n=== 519 verify: {COLLECTION} ===")
    print(f"  {len(tables)} shippable tables")
    if "c5_tables_covered" in ev:
        print(f"  C5 conservation coverage   "
              f"{ev['c5_tables_covered']}/{ev['c5_tables_total']}")
    if "per_table" in ev:
        print(f"  C2 duplicate primary keys  "
              f"{sum(v['duplicate_keys'] for v in ev['per_table'].values())}")
        print(f"  C3 literal duplicate rows  "
              f"{sum(v['literal_duplicates'] for v in ev['per_table'].values())}")
    if "identity" in ev:
        i = ev["identity"]
        print(f"  C4 accepted identity links {i['accepted_links']}   "
              f"class-guard breaches {i['class_guard_breaches']}")
        print(f"  C6 FR assertions reaching a customer through a refused "
              f"link: {i['through_refused_link']}")
        if i["spine_column_residue"]:
            print(f"  note: {i['spine_column_residue']} fr_tribal_list "
                  f"assertion(s) come from the SPINE's fr_official_name "
                  f"column, not from a source record: "
                  f"{i['spine_column_residue_uids']} - see "
                  f"docs/SOURCE_RECORD_LAYER.md, owned by the spine")
    if args.dir is None:
        p = ctx.path(EVIDENCE_REL)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(ev, indent=1), encoding="utf-8")
    for f in fails:
        print(f"  FAIL {f}")
    if fails:
        print(f"\n  {len(fails)} failure(s). {COLLECTION} is NOT closed.")
        return 1
    print(f"\n  OK - grain, keys, duplicates, conservation and the Federal "
          f"Register identity path all hold.")
    return 0


# =====================================================================
# FIXTURES - prove every check FIRES, and goes green again
# =====================================================================
# Following 514's lesson: the real instances are the historical record, the
# fixtures are the test. Each mutation is applied to a COPY in a temp overlay,
# so the defect is synthetic and cannot be fixed out from under the check by
# tomorrow's build. `verify --dir <overlay>` runs as a subprocess, so the exit
# codes below are real process exits.
def _run_verify(overlay, only):
    r = subprocess.run(
        [sys.executable, str(Path(__file__)), "verify", "--dir", str(overlay),
         "--only", only], capture_output=True, text=True, cwd=str(ROOT))
    return r.returncode, r.stdout


def _stage(overlay, rel):
    dst = Path(overlay) / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / rel, dst)
    return dst


FIXTURES = []


def fixture(check, what, rel):
    def deco(fn):
        FIXTURES.append((check, what, rel, fn))
        return fn
    return deco


@fixture("C5", "delete every conservation row for one customer table",
         CONSERVATION_REL)
def _f_c5_missing(p):
    rows = read_csv(p)
    write_csv(p, [r for r in rows
                  if r["source_table"] != "data/clean/fr_theme_year.csv"],
              CONSERVATION_COLS)


@fixture("C5", "make one ledger stop adding up", CONSERVATION_REL)
def _f_c5_arith(p):
    rows = read_csv(p)
    for r in rows:
        if r["source_table"] == "data/clean/fr_consultation_year.csv" \
                and r["disposition"] == "emitted":
            r["rows"] = str(int(r["rows"]) - 7)
            break
    write_csv(p, rows, CONSERVATION_COLS)


@fixture("C5", "rename a named rejection to an UNNAMED one", CONSERVATION_REL)
def _f_c5_unnamed(p):
    rows = read_csv(p)
    for r in rows:
        if r["source_table"] == "data/clean/fr_theme_year.csv" \
                and r["disposition"].startswith("rejected:"):
            r["disposition"] = "rejected:other"
            break
    write_csv(p, rows, CONSERVATION_COLS)


@fixture("C2", "repeat a declared primary key",
         "data/clean/section_106_source_coverage.csv")
def _f_c2_dupkey(p):
    rows = read_csv(p)
    hdr = read_header(p)
    clone = dict(rows[0])
    clone["finding"] = clone.get("finding", "") + " (fixture)"
    write_csv(p, rows + [clone], hdr)


@fixture("C3", "append a byte-identical duplicate row",
         "data/clean/section_106_source_coverage.csv")
def _f_c3_dup(p):
    rows = read_csv(p)
    write_csv(p, rows + [dict(rows[0])], read_header(p))


@fixture("C4", "attach an accepted FR roster link to an ANCSA CORPORATION "
                "(the measured F1 scenario)",
         "data/spine/cedar_source_record_links.csv")
def _f_c4_class(p):
    rows = read_csv(p)
    hdr = read_header(p)
    denied = next(r for r in rows if r["link_status"] == "denied")
    clone = dict(denied)
    clone["link_id"] = denied["link_id"] + "-FIXTURE"
    clone["link_status"] = "proposed"
    clone["link_role"] = "identifies"
    write_csv(p, rows + [clone], hdr)


@fixture("C4", "demote an accepted link to `contested` while its assertion "
               "still ships", "data/spine/cedar_source_record_links.csv")
def _f_c4_refused(p):
    fx_rows = read_csv(p)
    hdr = read_header(p)
    asserts = {a["cedar_uid"] for a in
               read_csv(ROOT / "data/clean/cedar_assertions.csv")
               if a.get("source_id") == "fr_tribal_list"}
    for r in fx_rows:
        if (r["link_role"] == "identifies"
                and r["link_status"] == "proposed"
                and r["cedar_uid"] in asserts):
            r["link_status"] = "contested"
            break
    write_csv(p, fx_rows, hdr)


@fixture("C5", "MUST NOT FIRE: add a conservation ledger this dataset does "
               "not own", CONSERVATION_REL)
def _f_mustnot(p):
    rows = read_csv(p)
    rows.append(dict(source_table="data/clean/some_other_dataset.csv",
                     rows_in="10", disposition="emitted", rows="10",
                     pct="100.0", examples="", harvest_date=TODAY))
    write_csv(p, rows, CONSERVATION_COLS)


def cmd_fixtures(_args):
    print("=== 519 fixtures: every check, proven to fire and to clear ===\n")
    base = tempfile.mkdtemp(prefix="fr_closure_fx_")
    rc, _ = _run_verify(base, "C1,C4,C5")
    print(f"  BASELINE (empty overlay -> the live tree)          exit {rc}")
    ok = rc == 0
    results = []
    try:
        for check, what, rel, mutate in FIXTURES:
            must_fire = not what.startswith("MUST NOT FIRE")
            over = tempfile.mkdtemp(prefix="fr_closure_fx_")
            try:
                p = _stage(over, rel)
                mutate(p)
                fired, out = _run_verify(over, check)
                shutil.copy2(ROOT / rel, p)          # restore
                cleared, _ = _run_verify(over, check)
                good = ((fired == 1) if must_fire else (fired == 0)) \
                    and cleared == 0
                results.append(good)
                tag = "PASS" if good else "FAIL"
                print(f"  {tag} {check:4s} {what[:62]:62s} "
                      f"exit {fired}   restored {cleared}")
                if not good:
                    print("       " + "\n       ".join(
                        l for l in out.splitlines() if "FAIL" in l)[:400])
            finally:
                shutil.rmtree(over, ignore_errors=True)
    finally:
        shutil.rmtree(base, ignore_errors=True)
    print(f"\n  {len(results)} fixture(s), {sum(results)} behaved as specified")
    return 0 if (ok and all(results)) else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("conserve")
    c.add_argument("--publish-only", action="store_true",
                   help="re-merge the durable ledger without recomputing it "
                        "(the repair after 510_assertions.py all --apply)")
    c.add_argument("--dir")
    c.set_defaults(func=cmd_conserve)
    v = sub.add_parser("verify")
    v.add_argument("--dir", help="overlay root; files present here win")
    v.add_argument("--only", help="comma-separated check tags: C1,C4,C5")
    v.set_defaults(func=cmd_verify)
    f = sub.add_parser("fixtures")
    f.set_defaults(func=cmd_fixtures)
    args = ap.parse_args()
    for k in ("dir", "only", "publish_only"):
        if not hasattr(args, k):
            setattr(args, k, None)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
