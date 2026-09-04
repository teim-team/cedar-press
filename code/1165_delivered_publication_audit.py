#!/usr/bin/env python3
"""
Cedar Press - 1165: do the publication rules hold in the DELIVERED files?

    py -3 code/1165_delivered_publication_audit.py            # audit, print
    py -3 code/1165_delivered_publication_audit.py json       # + write JSON
    py -3 code/1165_delivered_publication_audit.py <dataset>  # one dataset

WHY THIS EXISTS
---------------
`cedar_publication` is where the rules live and `1137` is where they are
applied. Every existing check reads one of those two - the policy module, or
the builder's own manifest. Nothing reads the FILE THE CUSTOMER RECEIVES.

That is the gap this project's field guide calls its signature defect: a check
that measures something adjacent to its own name. `1137 verify` compares the
delivered row count against `MANIFEST.csv`, which `1137` wrote; agreement there
says the writer was self-consistent, not that the policy landed. Masking and
column-dropping happen AT EXPORT, so `data/clean` is the wrong place to look
and the manifest is the writer grading its own homework.

So this reads `dist/customer/*.csv` and nothing else, streaming, UNCAPPED, and
reports per dataset:

  A. COLUMNS. No `NEVER` (personal data), no `DROP_COLS` (licensed proprietary
     identifiers), no build-lineage column may survive as a header in a
     delivered CSV. Tested on the delivered header, case-insensitively for
     DROP_COLS, and with the join prefix stripped for lineage - a joined column
     arrives as `<table>__<name>`.

  B. WITHHOLD STATES. A value that `BLOCKED_STATES` disposes as WITHHOLD may
     not appear at all. A value the vocabulary does not enumerate is also a
     WITHHOLD by the deny-by-default rule, so it may not appear either; those
     are reported by name because an unenumerated value is upstream drift.

  C. MASK STATES. A MASK row SHIPS - what must be gone is the Cedar
     attribution on it. So for every MASK row this counts the `MASK_COLS` cells
     that are still populated and every `attributed_flag` that is not "0".
     A non-zero count here is CP-017 back again.

  D. THE QUARANTINE CONJUNCTION. `identifier_ruling_quarantined == Y` AND
     `identifier_ruling_tier != A` is `BLOCKED_COMBINATIONS`, and its
     disposition is MASK, NOT withhold - the award is a real federal record.
     So the population is expected to be non-zero and the LEAK count is what
     must be zero. Both are printed, because reporting only the second invites
     the next reader to think the rows are gone.

  E. THE SUBAWARD FENCE. `duplicate_status == 'primary'` is a ROW gate - the
     two other values are WITHHOLD, so nothing else may ship.
     `subaward_exceeds_prime_flag != 'yes'` is a MONEY fence, not a row gate:
     those rows are real filings and DO ship, flagged. Conflating the two
     would report the fence broken every time it works. Both legs are counted
     separately, in rows and in dollars.

Nothing here is sampled and nothing is inferred. Every figure is a full pass
over the delivered file.

READS   dist/customer/*.csv  (only)
WRITES  review/1165_delivered_publication_audit_<date>.json  (mode `json`)
EXIT    1 if any violation is measured, 0 otherwise.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cedar_publication import (
    BLOCKED_STATES,
    DROP_COLS,
    MASK,
    MASK_COLS,
    MASK_FLAGS,
    NEID_COLS,
    NEVER,
    PROPOSED_COLS,
    SUBAWARD_FILE,
    WITHHOLD,
    adjudication,
    is_lineage_column,
)

csv.field_size_limit(10_000_000)
OUT = ROOT / "dist" / "customer"
# Local calendar date, as every other script in `code/` stamps its
# artefacts. A timezone-aware clock would name a different day than the
# build log written beside it, which is worse than the lint it silences.
TODAY = date.today().isoformat()  # noqa: DTZ011
REVIEW = ROOT / "review" / f"1165_delivered_publication_audit_{TODAY}.json"


# RETIRED NEID IDENTIFIERS, BY VALUE AND NOT ONLY BY NAME
# ------------------------------------------------------------------------
# Owner ruling 2026-09-03: the CICD/NEID identifiers are retired and Cedar's
# own key is the identity. `publishable_columns()` drops them BY NAME, which
# is the right gate and is not a sufficient one - the first retirement
# (`code/843`) enumerated three files and missed 77, and a name gate cannot
# see the same identifier arriving in a column called something else. So this
# tests the VALUES.
#
# A SHAPE REGEX WAS TRIED FIRST AND IT WAS THE DEFECT THIS REPO IS NAMED FOR.
# `^(?!CE-)[A-Z]{2,6}-[A-Z0-9]{4,8}-[0-9]{2}$` looks decisive and, measured
# against the delivered files on 2026-09-03, it was wrong in both directions
# at once:
#
#   * 568 FALSE POSITIVES. `contractors.award_base_description` holds
#     `DPW-00229-01` - a phrase inside a contract description - and
#     `subcontracting.subaward_number` holds `SR-2012-11`, which is a subaward
#     number. Neither identifies anything Cedar resolves.
#   * 2,173 MISSES, because 298 of the 1,562 real NEIDs are the extended
#     Alaska form and carry four or five parts:
#     `AKNF-ACSRMT-00-CALSTA-ASVCPR`.
#
# So the test is MEMBERSHIP in the real vocabulary, harvested from the columns
# that hold NEIDs in `data/clean` and `data/spine`, and the shape regex is
# demoted to a SCREEN: a value with the shape that is NOT in the vocabulary is
# reported separately and is NOT counted as a violation, because
# `SR-2012-11` is not one.
#
# LIST-VALUED CELLS ARE SPLIT. `nagpra_notices` has no single-id column at
# all - six pipe-delimited role columns, because one notice names many
# parties (AGENT_FIELD_GUIDE rule 18). A whole-cell membership test reads
# every multi-party cell as clean, which is how a 90.83%-linked dataset once
# scanned as 0%.
NEID_SHAPE = re.compile(r"^(?!CE-)[A-Z]{2,6}-[A-Z0-9]{4,8}-[0-9]{2}$")
# Cedar's OWN key, matched anywhere in a cell so a pipe-delimited entity list
# counts. Used only to answer "can this file name a Cedar entity", never to
# validate one - `1167` owns uid correctness.
_UID_SHAPE = re.compile("CE-[0-9A-Z]{5}-[0-9A-Z]{2}")
NEID_VOCAB_CACHE = ROOT / "review" / "1165_neid_vocabulary.json"
# The delimiters these tables use for a multi-party cell.
_SPLIT = ("|", ";")
# Only tables small enough to be a register are scanned for the vocabulary; a
# NEID is an ENTITY identifier, so every distinct value appears in one of
# them, and parsing 1.5 GB of transactions to re-derive 1,562 strings would
# make this audit unrunnable.
VOCAB_MAX_BYTES = 15_000_000
VOCAB_COLS = ("tribe_id", "neid", "tribe_id_neid")


def neid_vocabulary(refresh: bool = False) -> set:
    """Every NEID value Cedar holds, harvested once and cached.

    The cache records how many files were scanned and how many values were
    found, so a reader can tell an empty vocabulary - which would make every
    membership test pass, vacuously - from a real one. An empty harvest RAISES
    rather than return a clean result: rule 4, an absence of evidence must
    never print as evidence of absence.
    """
    if NEID_VOCAB_CACHE.exists() and not refresh:
        d = json.loads(NEID_VOCAB_CACHE.read_text(encoding="utf-8"))
        if d.get("values"):
            return set(d["values"])
    vals, files = set(), 0
    for d in (ROOT / "data" / "clean", ROOT / "data" / "spine"):
        for q in sorted(d.glob("*.csv")):
            if q.stat().st_size > VOCAB_MAX_BYTES:
                continue
            try:
                with q.open(encoding="utf-8-sig", errors="replace",
                            newline="") as fh:
                    rd = csv.DictReader(fh)
                    cols = [c for c in (rd.fieldnames or [])
                            if c.lower() in VOCAB_COLS]
                    if not cols:
                        continue
                    files += 1
                    for r in rd:
                        for c in cols:
                            v = (r.get(c) or "").strip()
                            if v and "-" in v:
                                vals.add(v)
            except OSError:
                continue
    if not vals:
        raise SystemExit(
            "  1165: harvested an EMPTY NEID vocabulary from "
            f"{files} file(s). Every membership test would pass for that "
            "reason alone, so the audit refuses to run rather than report a "
            "clean result it did not measure.")
    NEID_VOCAB_CACHE.parent.mkdir(parents=True, exist_ok=True)
    NEID_VOCAB_CACHE.write_text(json.dumps(
        {"harvested": TODAY, "files_scanned": files,
         "columns": list(VOCAB_COLS), "max_bytes": VOCAB_MAX_BYTES,
         "n": len(vals), "values": sorted(vals)}, indent=1), encoding="utf-8")
    return vals


def _money(v):
    try:
        return float(str(v).replace(",", "").replace("$", "").strip())
    except (TypeError, ValueError):
        return None


def audit_one(path: Path, vocab: set | None = None) -> dict:
    """One streaming pass. Returns everything measured about this file.

    `vocab` is the retired-NEID value set. It is harvested on demand so a
    caller - and the selftest - can hand in a fixture vocabulary instead.
    """
    vocab = neid_vocabulary() if vocab is None else vocab
    res = {
        "dataset": path.stem,
        "bytes": path.stat().st_size,
        "rows": 0,
        "columns": 0,
        "header": [],
        # A
        "never_columns_present": [],
        "drop_columns_present": [],
        "lineage_columns_present": [],
        "neid_columns_present": [],
        "neid_value_cells": defaultdict(int),
        "cedar_uid_value_cells": defaultdict(int),
        "neid_value_tokens": defaultdict(int),
        "neid_value_examples": {},
        "neid_shaped_unknown": defaultdict(int),
        "neid_shaped_unknown_examples": {},
        "identity_columns_present": [],
        # B/C
        # Per-column fill, measured on the DELIVERED file. `1137` computes a
        # sparse-column list in memory during the build and records it in
        # MANIFEST.csv; that is the writer's account of its own work. A
        # reviewer needs the same fact read back off the file that shipped.
        "filled": defaultdict(int),
        "state_columns_present": [],
        "value_counts": defaultdict(lambda: defaultdict(int)),
        "withheld_states_present": {},
        "unenumerated_states_present": {},
        # Row-level, one row one disposition, from the policy function.
        # The old report summed per-COLUMN value tallies and called the
        # result rows; a contractors row carries four state columns, so
        # that number counted many rows four times.
        "disposition_rows": defaultdict(int),
        "mask_rows": 0,
        "mask_attribution_leaks": defaultdict(int),
        # D
        "quarantine_population": 0,
        "quarantine_tier_A": 0,
        "quarantine_leaks": defaultdict(int),
        # E
        "duplicate_status_counts": defaultdict(int),
        "exceeds_prime_counts": defaultdict(int),
        "subaward_unfiltered_usd": 0.0,
        "subaward_countable_usd": 0.0,
        "subaward_rows_countable": 0,
    }
    lower_drop = {c.lower() for c in DROP_COLS}
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        hdr = rd.fieldnames or []
        res["header"] = hdr
        res["columns"] = len(hdr)
        res["never_columns_present"] = [c for c in hdr if c in NEVER]
        res["drop_columns_present"] = [c for c in hdr if c.lower() in lower_drop]
        res["lineage_columns_present"] = [c for c in hdr if is_lineage_column(c)]
        lower_neid = {c.lower() for c in NEID_COLS} | {
            c.lower() for c in PROPOSED_COLS}
        res["neid_columns_present"] = [c for c in hdr
                                       if c.lower() in lower_neid]
        # A dataset that loses its NEID column must still be able to name an
        # entity. Cedar's own key, under every spelling the delivered files
        # use - the subcontracting file carries one per side of the award.
        #
        # TESTED BY VALUE AS WELL AS BY NAME, and the name half alone was
        # wrong. When the NEID retirement moved from dropping columns to
        # TRANSLATING their values (`cedar_publication.translate_neid_values`,
        # 2026-09-03), `nagpra` went from 47,252 retired identifiers to 47,114
        # Cedar uids - carried in `consulted_entity_ids`,
        # `affiliated_entity_ids` and four more. It can name an entity on every
        # resolved row. A name-only test still called it identity-less and
        # reported a blocker that had just been fixed, because none of those
        # columns is SPELLED `cedar_uid`.
        #
        # So the question is not "is there a column called cedar_uid" but "can
        # this file name a Cedar entity at all".
        named = {c.lower() for c in ("cedar_uid", "prime_cedar_uid",
                                     "sub_cedar_uid", "entity_cedar_uids",
                                     "cedar_entity_id", "cedar_spine_entity_id")}
        res["identity_columns_present"] = [c for c in hdr if c.lower() in named]
        # `identity_value_columns` CANNOT be computed here - the row scan that
        # fills `cedar_uid_value_cells` has not run yet, and reading the dict
        # now returns empty for every dataset. It is set after the scan.
        state_cols = [c for c in BLOCKED_STATES if c in hdr]
        res["state_columns_present"] = state_cols
        # `MASK_COLS` is keyed by state column AND by combination reason, so
        # only the attribution columns that actually exist in this header can
        # leak. Resolve once rather than per row.
        mask_targets = {k: [c for c in cols if c in hdr]
                        for k, cols in MASK_COLS.items()}
        flags_here = [c for c in MASK_FLAGS if c in hdr]
        has_quar = ("identifier_ruling_quarantined" in hdr)
        is_sub = (path.name == SUBAWARD_FILE)

        filled = res["filled"]
        for r in rd:
            res["rows"] += 1
            for c, v in r.items():
                if v is None:
                    continue
                v = str(v).strip()
                if not v:
                    continue
                filled[c] += 1
                # Count Cedar's OWN key wherever it appears, not only in a
                # column named for it. This is what makes the identity check
                # below true after the 2026-09-03 value translation: nagpra's
                # entity columns hold uids under names like
                # `consulted_entity_ids`, and a name-only test called that
                # dataset identity-less.
                if "CE-" in v and _UID_SHAPE.search(v):
                    res["cedar_uid_value_cells"][c] += 1
                # Cheap pre-filter first: every NEID is hyphenated, and this
                # one test skips most of ~100M cells before any set lookup.
                if "-" in v:
                    if v in vocab:
                        res["neid_value_cells"][c] += 1
                        res["neid_value_tokens"][c] += 1
                        res["neid_value_examples"].setdefault(c, v)
                    elif any(d in v for d in _SPLIT):
                        toks = [t.strip() for t in
                                v.replace(";", "|").split("|")]
                        hit = [t for t in toks if t in vocab]
                        if hit:
                            res["neid_value_cells"][c] += 1
                            res["neid_value_tokens"][c] += len(hit)
                            res["neid_value_examples"].setdefault(c, hit[0])
                    elif NEID_SHAPE.match(v):
                        # Shaped, unknown to the vocabulary. Reported, never
                        # counted as a violation - `SR-2012-11` is a subaward
                        # number.
                        res["neid_shaped_unknown"][c] += 1
                        res["neid_shaped_unknown_examples"].setdefault(c, v)
            for col in state_cols:
                res["value_counts"][col][(r.get(col) or "").strip()
                                         or "(blank)"] += 1
            # THE DISPOSITION COMES FROM `cedar_publication.adjudication()`,
            # NOT FROM A COPY OF IT HERE. The first draft of this file walked
            # `BLOCKED_STATES` and `BLOCKED_COMBINATIONS` itself, which is the
            # field guide's "two detectors for one class drift" defect: this
            # audit would have gone on agreeing with the policy it was written
            # against long after the policy moved, and agreeing with a stale
            # copy of the rules is the one failure a publication audit cannot
            # survive. `1137` calls `is_publication_eligible`, which calls
            # this; the audit now asks the same function the same question.
            disp, why = adjudication(r)
            res["disposition_rows"][disp] += 1
            if disp == WITHHOLD:
                # `adjudication` reports `<column>=<value>` for a known
                # WITHHOLD and `unknown_state:<column>=<value>` for a value the
                # vocabulary has never seen. Both are violations; they are
                # counted apart because the second is upstream drift and needs
                # a different fix.
                if why.startswith("unknown_state:"):
                    k = why.split(":", 1)[1]
                    res["unenumerated_states_present"][k] = (
                        res["unenumerated_states_present"].get(k, 0) + 1)
                else:
                    res["withheld_states_present"][why] = (
                        res["withheld_states_present"].get(why, 0) + 1)
            # D - the conjunction, reported as a population in its own right.
            # `adjudication` already folds it into `disp`; counting the rows
            # lets the report say how many SHIP under it, which a leak count of
            # zero would otherwise leave a reader to assume is none.
            if has_quar:
                q = (r.get("identifier_ruling_quarantined") or "").strip()
                t = (r.get("identifier_ruling_tier") or "").strip()
                if q == "Y":
                    if t == "A":
                        res["quarantine_tier_A"] += 1
                    else:
                        res["quarantine_population"] += 1
                        for c in mask_targets.get(
                                "quarantined_method_not_ruled_tier_A", []):
                            if (r.get(c) or "").strip():
                                res["quarantine_leaks"][c] += 1
                        for c in flags_here:
                            if (r.get(c) or "").strip() not in ("", "0"):
                                res["quarantine_leaks"][c] += 1
            # C - a MASK row must carry no Cedar attribution.
            if disp == MASK:
                res["mask_rows"] += 1
                # A single-column reason is `<column>=<value>`; a conjunction
                # reason is a bare name. `MASK_COLS` is keyed by both, exactly
                # as `mask_attribution` splits it.
                for c in mask_targets.get(why.split("=", 1)[0], []):
                    if (r.get(c) or "").strip():
                        res["mask_attribution_leaks"][f"{why}:{c}"] += 1
                for c in flags_here:
                    if (r.get(c) or "").strip() not in ("", "0"):
                        res["mask_attribution_leaks"][f"{why}:{c}"] += 1
            # E - the two legs of the subaward fence, kept apart.
            if is_sub:
                ds = (r.get("duplicate_status") or "").strip() or "(blank)"
                ex = (r.get("subaward_exceeds_prime_flag") or "").strip() \
                    or "(blank)"
                res["duplicate_status_counts"][ds] += 1
                res["exceeds_prime_counts"][ex] += 1
                v = _money(r.get("subaward_amount"))
                if v is not None:
                    res["subaward_unfiltered_usd"] += v
                    if ds == "primary" and ex != "yes":
                        res["subaward_countable_usd"] += v
                        res["subaward_rows_countable"] += 1
    # `csv.DictReader` puts overflow cells under the key `None` when a row has
    # more fields than the header. That is a malformed row, not a column, and
    # it must be reported rather than silently counted as one.
    res["ragged_rows"] = res["filled"].pop(None, 0)
    res["empty_columns"] = [c for c in res["header"] if not res["filled"].get(c)]
    # defaultdicts do not serialise usefully; freeze them.
    res["filled"] = {c: res["filled"].get(c, 0) for c in res["header"]}
    res["value_counts"] = {k: dict(v) for k, v in res["value_counts"].items()}
    res["cedar_uid_value_cells"] = dict(res["cedar_uid_value_cells"])
    res["identity_value_columns"] = sorted(
        c for c, n in res["cedar_uid_value_cells"].items() if n)
    res["neid_value_cells"] = dict(res["neid_value_cells"])
    res["neid_value_tokens"] = dict(res["neid_value_tokens"])
    res["neid_shaped_unknown"] = dict(res["neid_shaped_unknown"])
    res["disposition_rows"] = dict(res["disposition_rows"])
    res["mask_attribution_leaks"] = dict(res["mask_attribution_leaks"])
    res["quarantine_leaks"] = dict(res["quarantine_leaks"])
    res["duplicate_status_counts"] = dict(res["duplicate_status_counts"])
    res["exceeds_prime_counts"] = dict(res["exceeds_prime_counts"])
    return res


def selftest() -> int:
    """Prove every detector FIRES, on a fixture, before anyone trusts a green.

    Field guide rule 1: *a check does not count until a fixture proves it
    fires.* This audit reported zero violations across all thirteen delivered
    files on its first run, and zero is the strongest thing it can say - which
    is exactly the shape of the twenty-four checks in
    `docs/AGENT_FIELD_GUIDE.md` that were measuring something else. So each
    class is injected into a throwaway CSV, `audit_one` is asked about it, and
    the NAMED invariant must be the one that fires. A clean fixture must come
    back clean, or the detectors are firing on everything.

    Writes nothing outside a temporary directory and touches no delivered file.
    """
    import tempfile
    fails = []
    # A FIXTURE VOCABULARY, not the live one. The selftest must prove
    # the detector fires, not that this machine happens to hold a
    # particular register - and harvesting 67 files to check a two-row
    # CSV is what makes a selftest stop being run.
    VOC = {"ANRC-AHTNAI-00", "TRBF-CADDON-00", "TRBF-ZUNINM-00",
           "AKNF-ACSRMT-00-CALSTA-ASVCPR"}

    def check(label, condition, detail=""):
        print(f"    {'ok  ' if condition else 'FAIL'}  {label}"
              + (f"   {detail}" if detail else ""))
        if not condition:
            fails.append(label)

    with tempfile.TemporaryDirectory() as td:
        d = Path(td)

        # 1. A clean file must be clean. Without this the rest proves nothing:
        #    a detector that fires on everything also fires on the fixture.
        clean = d / "clean_fixture.csv"
        clean.write_text(
            "cedar_uid,tribe_id,canonical_name,ruling_status,attributed_flag\n"
            "CEDAR-1,T1,Example Nation,RULED_ATTRIBUTED,1\n",
            encoding="utf-8")
        r = audit_one(clean, VOC)
        check("clean fixture is clean",
              not (r["never_columns_present"] or r["drop_columns_present"]
                   or r["lineage_columns_present"]
                   or r["withheld_states_present"]
                   or r["unenumerated_states_present"]
                   or r["mask_attribution_leaks"] or r["ragged_rows"]),
              f"{r['rows']} row, {r['columns']} cols")

        # 2. Column classes.
        cols = d / "cols_fixture.csv"
        cols.write_text("phone,DUNS,ruling_source_file,ok_col\n"
                        "555,123,review/x.csv,v\n", encoding="utf-8")
        r = audit_one(cols, VOC)
        check("NEVER column detected", r["never_columns_present"] == ["phone"],
              str(r["never_columns_present"]))
        check("DROP_COLS detected case-insensitively",
              r["drop_columns_present"] == ["DUNS"],
              str(r["drop_columns_present"]))
        check("lineage column detected",
              r["lineage_columns_present"] == ["ruling_source_file"],
              str(r["lineage_columns_present"]))

        # 3. A WITHHOLD state, and a value the vocabulary has never seen.
        st = d / "state_fixture.csv"
        st.write_text("duplicate_status\nexact_repeat_within_source\n"
                      "a_state_nobody_enumerated\n", encoding="utf-8")
        r = audit_one(st, VOC)
        check("WITHHOLD state detected",
              r["withheld_states_present"].get(
                  "duplicate_status=exact_repeat_within_source") == 1,
              str(r["withheld_states_present"]))
        check("unenumerated state detected (deny-by-default)",
              r["unenumerated_states_present"].get(
                  "duplicate_status=a_state_nobody_enumerated") == 1,
              str(r["unenumerated_states_present"]))

        # 4. A MASK row that kept its attribution - CP-017's exact shape.
        mk = d / "mask_fixture.csv"
        mk.write_text(
            "cedar_uid,tribe_id,canonical_name,ruling_status,attributed_flag\n"
            "CEDAR-9,T9,Held Nation,RULED_HOLD,1\n"
            ",,,RULED_HOLD,0\n", encoding="utf-8")
        r = audit_one(mk, VOC)
        check("MASK row counted", r["mask_rows"] == 2, str(r["mask_rows"]))
        check("row-level disposition counter agrees with the row count",
              sum(r["disposition_rows"].values()) == r["rows"] == 2,
              str(r["disposition_rows"]))
        # The leak key carries the WHOLE adjudication reason, value included -
        # `ruling_status=RULED_HOLD:cedar_uid`, not `ruling_status:cedar_uid`.
        # A reviewer needs to know WHICH state let the attribution through.
        check("MASK attribution leak detected on cedar_uid",
              r["mask_attribution_leaks"].get(
                  "ruling_status=RULED_HOLD:cedar_uid") == 1,
              str(r["mask_attribution_leaks"]))
        check("MASK leak detected on attributed_flag",
              r["mask_attribution_leaks"].get(
                  "ruling_status=RULED_HOLD:attributed_flag") == 1)

        # 5. The quarantine conjunction, both sides of the `unless`.
        q = d / "quarantine_fixture.csv"
        q.write_text(
            "cedar_uid,identifier_ruling_quarantined,identifier_ruling_tier\n"
            "CEDAR-2,Y,B\n"
            "CEDAR-3,Y,A\n"
            ",Y,B\n", encoding="utf-8")
        r = audit_one(q, VOC)
        check("quarantine population counted",
              r["quarantine_population"] == 2, str(r["quarantine_population"]))
        check("tier A is EXCLUDED from the quarantine rule",
              r["quarantine_tier_A"] == 1, str(r["quarantine_tier_A"]))
        check("quarantine leak detected",
              r["quarantine_leaks"].get("cedar_uid") == 1,
              str(r["quarantine_leaks"]))

        # 6. A ragged row - more fields than the header.
        rg = d / "ragged_fixture.csv"
        rg.write_text("a,b\n1,2\n1,2,3\n", encoding="utf-8")
        r = audit_one(rg, VOC)
        check("ragged row detected", r["ragged_rows"] == 1,
              str(r["ragged_rows"]))

        # 7a. The NEID retirement, owner ruling 2026-09-03 - by NAME, by
        #     VALUE, inside a list cell, and the screen that must NOT fire.
        nd = d / "neid_fixture.csv"
        nd.write_text(
            "cedar_uid,tribe_id,some_other_col,parties,award_desc\n"
            "CE-0000D-E5,ANRC-AHTNAI-00,TRBF-CADDON-00,CE-0001F-Z7|TRBF-ZUNINM-00|AKNF-ACSRMT-00-CALSTA-ASVCPR,DPW-00229-01\n"
            "CE-0002B-12,,plain text,,SR-2012-11\n", encoding="utf-8")
        r = audit_one(nd, VOC)
        check("retired NEID column detected by name",
              r["neid_columns_present"] == ["tribe_id"],
              str(r["neid_columns_present"]))
        check("retired NEID VALUE detected in an innocently named column",
              r["neid_value_cells"].get("some_other_col") == 1,
              str(r["neid_value_cells"]))
        check("a LIST cell is split, and both NEIDs in it are counted",
              r["neid_value_cells"].get("parties") == 1
              and r["neid_value_tokens"].get("parties") == 2,
              f"cells={r['neid_value_cells'].get('parties')} "
              f"tokens={r['neid_value_tokens'].get('parties')}")
        check("cedar_uid is NOT mistaken for a NEID",
              "cedar_uid" not in r["neid_value_cells"],
              str(r["neid_value_cells"]))
        check("a NEID-SHAPED non-NEID is screened, not counted as a "
              "violation",
              r["neid_value_cells"].get("award_desc") is None
              and r["neid_shaped_unknown"].get("award_desc") == 2,
              f"violations={r['neid_value_cells'].get('award_desc')} "
              f"screened={r['neid_shaped_unknown'].get('award_desc')}")
        check("identity column found",
              r["identity_columns_present"] == ["cedar_uid"],
              str(r["identity_columns_present"]))

        # 7b. A file with no Cedar key at all must say so.
        ni = d / "no_identity_fixture.csv"
        ni.write_text("a,b\n1,2\n", encoding="utf-8")
        r = audit_one(ni, VOC)
        check("a delivered file with no identity column is detected",
              r["identity_columns_present"] == [],
              str(r["identity_columns_present"]))

        # 7. Empty-column detection, which the report quotes per dataset.
        ec = d / "empty_fixture.csv"
        ec.write_text("a,b\n1,\n2,   \n", encoding="utf-8")
        r = audit_one(ec, VOC)
        check("all-blank column detected", r["empty_columns"] == ["b"],
              str(r["empty_columns"]))

        # 8. The subaward fence, on a file named as the delivered one - the
        #    two legs must be counted apart, and only the row gate is a
        #    violation.
        sub = d / SUBAWARD_FILE
        sub.write_text(
            "duplicate_status,subaward_exceeds_prime_flag,subaward_amount\n"
            "primary,,100\n"
            "primary,yes,900\n"
            "exact_repeat_within_source,,50\n", encoding="utf-8")
        r = audit_one(sub, VOC)
        check("subaward row gate: non-primary counted",
              r["duplicate_status_counts"].get(
                  "exact_repeat_within_source") == 1,
              str(r["duplicate_status_counts"]))
        check("subaward money fence: exceeds-prime row SHIPS, uncounted",
              r["exceeds_prime_counts"].get("yes") == 1
              and r["subaward_countable_usd"] == 100.0
              and r["subaward_unfiltered_usd"] == 1050.0,
              f"countable ${r['subaward_countable_usd']:,.2f} / "
              f"unfiltered ${r['subaward_unfiltered_usd']:,.2f}")

    print(f"\n  1165 selftest   {'FAIL' if fails else 'ok'}   "
          f"{len(fails)} detector(s) did not fire as named")
    return 1 if fails else 0


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if "selftest" in args:
        return selftest()
    mode = "json" if "json" in args else "print"
    only = {a for a in args if a != "json"}
    files = sorted(p for p in OUT.glob("*.csv") if p.name != "MANIFEST.csv")
    if only:
        files = [p for p in files if p.stem in only]
        if not files:
            print(f"  no delivered file matches {', '.join(sorted(only))}",
                  file=sys.stderr)
            return 2
    out, violations = [], []
    # Harvested ONCE, before the pass, so the size of the vocabulary is
    # printed beside the finding. A vocabulary of zero would make every
    # membership test pass for that reason alone; `neid_vocabulary` raises
    # rather than let that happen, and printing the count is how a reader
    # sees that it did not.
    vocab = neid_vocabulary(refresh=("refresh-vocab" in args))
    print(f"  1165 delivered publication audit   {len(files)} file(s), "
          f"full scan, no cap")
    print(f"    retired-NEID vocabulary: {len(vocab):,} value(s) "
          f"({NEID_VOCAB_CACHE.name})\n")
    for p in files:
        r = audit_one(p, vocab)
        out.append(r)
        bad = []
        for label, key in (("NEVER column", "never_columns_present"),
                           ("DROP_COLS column", "drop_columns_present"),
                           ("lineage column", "lineage_columns_present"),
                           ("retired NEID/proposed column",
                            "neid_columns_present")):
            for c in r[key]:
                bad.append(f"{label} `{c}` survives in the delivered header")
        for k, n in sorted(r["withheld_states_present"].items()):
            bad.append(f"WITHHOLD state {k} on {n:,} delivered rows")
        for k, n in sorted(r["unenumerated_states_present"].items()):
            bad.append(f"unenumerated state {k} on {n:,} delivered rows "
                       f"(deny-by-default says WITHHOLD)")
        for k, n in sorted(r["mask_attribution_leaks"].items()):
            bad.append(f"MASK leak {k} populated on {n:,} rows")
        for k, n in sorted(r["quarantine_leaks"].items()):
            bad.append(f"quarantine leak `{k}` populated on {n:,} rows")
        if p.name == SUBAWARD_FILE:
            for k, n in sorted(r["duplicate_status_counts"].items()):
                if k != "primary":
                    bad.append(f"duplicate_status={k} on {n:,} delivered rows")
        # A row with more fields than the header is a malformed CSV, and it is
        # the one defect that makes every other figure in this file suspect -
        # a reader parsing it column-by-position gets shifted values from that
        # row on. `DictReader` hides it under the key `None`.
        for c, n in sorted(r["neid_value_cells"].items()):
            bad.append(f"retired NEID value in `{c}` on {n:,} delivered rows "
                       f"({r['neid_value_tokens'].get(c, 0):,} value(s); "
                       f"e.g. `{r['neid_value_examples'].get(c, '')}`)")
        # A dataset that had an identity column and now has none is the ONE
        # outcome the NEID retirement must not produce, and it is invisible to
        # every other check here: dropping a column never fails a row count.
        if not r["identity_columns_present"] and not r.get("identity_value_columns"):
            bad.append("NO Cedar identity column survives in the delivered "
                       "header - the dataset can no longer name an entity")
        if r["ragged_rows"]:
            bad.append(f"{r['ragged_rows']:,} row(s) carry more fields than "
                       f"the header - malformed CSV")
        violations.extend(f"{r['dataset']}: {b}" for b in bad)
        print(f"    {r['dataset']:<26} {r['rows']:>9,} rows x "
              f"{r['columns']:>3} cols  {r['bytes']/1e6:>9,.1f} MB   "
              f"{len(r['empty_columns'])} empty col(s)   "
              f"{len(bad)} violation(s)")
        if r["quarantine_population"] or r["quarantine_tier_A"]:
            print(f"      quarantined Y & tier != A : "
                  f"{r['quarantine_population']:,} rows SHIP (policy is MASK, "
                  f"not withhold); tier A inside quarantine: "
                  f"{r['quarantine_tier_A']:,}")
        if r["mask_rows"]:
            print(f"      rows adjudicated MASK     : {r['mask_rows']:,}")
        if p.name == SUBAWARD_FILE:
            print("      duplicate_status          : "
                  + "; ".join(f"{k}={v:,}" for k, v in
                              sorted(r["duplicate_status_counts"].items())))
            print("      subaward_exceeds_prime    : "
                  + "; ".join(f"{k}={v:,}" for k, v in
                              sorted(r["exceeds_prime_counts"].items())))
            print(f"      subaward_amount           : "
                  f"${r['subaward_unfiltered_usd']:,.2f} unfiltered / "
                  f"${r['subaward_countable_usd']:,.2f} countable over "
                  f"{r['subaward_rows_countable']:,} fenced rows")
        for b in bad[:6]:
            print(f"      !! {b}")
    print()
    for v in violations[:40]:
        print("  FAIL " + v)
    print(f"\n  1165 audit   {'FAIL' if violations else 'ok'}   "
          f"{len(violations)} violation(s) across {len(files)} delivered file(s)")
    if mode == "json":
        REVIEW.parent.mkdir(parents=True, exist_ok=True)
        REVIEW.write_text(json.dumps(
            {"generated": TODAY, "files": out, "violations": violations},
            indent=2), encoding="utf-8")
        print(f"  json -> {REVIEW.relative_to(ROOT)}")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
