#!/usr/bin/env python3
# lint-ok: class6 - an IN-PLACE ENRICHER by design. It reads
# prime_contracts.csv and rewrites it with two added columns; it never
# rebuilds. Declared ordering: it runs AFTER 131 and 207 and after any rebuild
# of prime_contracts.csv, and it must be re-run after every such rebuild.
"""
Cedar Press - 429: carry the temporal as-of OWNERSHIP verdict onto the
customer-facing prime contracting tables.

THE DEFECT
----------
`code/515_temporal.py asof` resolves, for every (firm UEI, fiscal year) Cedar
has evidence about, who owned that firm DURING that year, and records whether
the answer agrees with the owner Cedar currently ships. It produces
`review/temporal_asof_ownership.csv`.

**Nothing in the publication layer consumed a single row of it.**
`code/517_export_safety.py` counts the statuses into a Markdown table and
stops. Every customer-facing table went on presenting the CURRENT owner as
though it were the historical one, on transactions dated up to twenty-six
years earlier, with no column anywhere saying otherwise.

THE RULE, EXACTLY AS THE EXTERNAL REVIEWER STATED IT
----------------------------------------------------
    "Unknown ownership can remain unknown. Contradicted ownership must never
     silently become definite."

So: an UNKNOWN may ship, AS UNKNOWN. A CONTRADICTED owner may never ship as a
definite historical owner. And an unknown is NEVER filled from current
ownership - that is the defect, not the repair.

WHAT THIS ADDS, AND WHAT IT DELIBERATELY DOES NOT TOUCH
-------------------------------------------------------
Two columns on `prime_contracts.csv`:

  `owner_attribution_status`            the as-of verdict for this row's
                                        (awardee_uei, fiscal_year)
  `owner_as_of_transaction_cedar_uid`   the entity the temporal layer
                                        CONFIRMS held this firm in this year,
                                        or the literal `UNKNOWN`

`tribe_id`, `canonical_name` and `cedar_uid` are NOT changed, and that is
deliberate. They are Cedar's CURRENT attribution and they remain exactly that.
What was missing was never the current answer; it was any statement of whether
the current answer is also the historical one. Blanking them would destroy a
real, useful, correctly-labelled fact in order to fix a labelling problem.
`owner_as_of_transaction_cedar_uid` is the historical answer, and it says
UNKNOWN wherever the evidence does not support one.

THE SEVEN STATUSES, AND WHY `RESOLVED` IS NOT ONE OF THEM
---------------------------------------------------------
`517_export_safety.py` treats `asof_status == RESOLVED` as definite. It is
not, and the file says so in its own columns. Of 10,983 RESOLVED cells:

    agrees_with_shipped = 1     3,669   the layer CONFIRMS the shipped owner
    agrees_with_shipped = 0       410   the layer CONTRADICTS it
    agrees_with_shipped = ''    6,899   a parent UEI resolved, but Cedar holds
                                        no entity for that UEI, so the shipped
                                        owner is neither confirmed nor denied

Only the first is a confirmation. Folding the other 7,309 cells into
"RESOLVED" is how $86.1B of prime obligations came to be counted as safe. This
script splits them:

    CONFIRMED_AS_OF               definite, and the only status that may carry
                                  a historical owner
    CONTRADICTED_AS_OF            the layer says someone ELSE held the firm
    RESOLVED_OWNER_NOT_IN_CEDAR   a parent resolved; Cedar cannot name it
    UNKNOWN_OUTSIDE_EVIDENCE      \\
    AMBIGUOUS_OVERLAP              |  the resolver's own verdicts, carried
    NO_FACT_ON_SUBJECT             |  through unchanged
    NO_COVERING_FACT               |
    AMBIGUOUS_GRANULARITY         /
    NOT_EVALUATED                 the temporal layer holds no cell for this
                                  (awardee_uei, fiscal_year) at all

MEASURED EXPOSURE, on 888,862 attributed prime rows carrying $244.766B:

    CONFIRMED_AS_OF               151,851 rows   $ 45.629B   18.6%
    RESOLVED_OWNER_NOT_IN_CEDAR   310,421 rows   $ 86.086B   35.2%
    NOT_EVALUATED                 306,626 rows   $ 78.830B   32.2%
    UNKNOWN_OUTSIDE_EVIDENCE       58,847 rows   $ 18.603B    7.6%
    AMBIGUOUS_OVERLAP              41,716 rows   $ 10.215B    4.2%
    NO_FACT_ON_SUBJECT              9,459 rows   $  2.931B    1.2%
    CONTRADICTED_AS_OF              9,259 rows   $  2.074B    0.8%
    NO_COVERING_FACT                  608 rows   $  0.333B    0.1%
    AMBIGUOUS_GRANULARITY              75 rows   $  0.066B    0.0%

**$199.137B of prime obligations - 81.4% - shipped a definite-looking owner
the temporal layer does not confirm, and $2.074B of it the layer actively
contradicts.** After this pass those rows say so in a column, and the
historical-owner column on every one of them reads UNKNOWN.

    py -3 code/429_apply_asof_ownership_status.py --check    # measure only
    py -3 code/429_apply_asof_ownership_status.py --apply    # write it
    py -3 code/429_apply_asof_ownership_status.py --verify   # exit 1 on a
                                                             # violation

Reads  review/temporal_asof_ownership.csv
       data/clean/prime_contracts.csv
Writes data/clean/prime_contracts.csv            (in place, .part + replace)
       review/prime_owner_asof_exposure.csv      (the dollars, by status)
       data/clean/codebook/02_prime_contracting.csv   (APPEND ONLY)
       data/clean/codebook_master.csv                 (APPEND ONLY)

Re-run `py -3 code/62_no_regression_check.py` after.
"""

import argparse
import csv
import os
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))

CLEAN = ROOT / "data" / "clean"
REVIEW = ROOT / "review"
PRIME = CLEAN / "prime_contracts.csv"
ASOF = REVIEW / "temporal_asof_ownership.csv"
EXPOSURE = REVIEW / "prime_owner_asof_exposure.csv"
TODAY = date.today().isoformat()

csv.field_size_limit(10 ** 9)

STATUS_COL = "owner_attribution_status"
ASOF_OWNER_COL = "owner_as_of_transaction_cedar_uid"

#: The ONE status that may carry a historical owner. Everything else ships
#: UNKNOWN. This is a set of one on purpose: it is the shape of the rule, and
#: adding a second member is a decision someone has to make explicitly.
DEFINITE = {"CONFIRMED_AS_OF"}

#: What a not-definite row publishes as its historical owner. A literal, not a
#: blank: a blank reads as "no data collected", and this is a measured verdict
#: of "we looked and cannot say".
UNKNOWN = "UNKNOWN"


def classify(cell):
    """One as-of row -> (status, the cedar_uid it may publish or UNKNOWN)."""
    if cell is None:
        return "NOT_EVALUATED", UNKNOWN
    status = (cell.get("asof_status") or "").strip()
    if status != "RESOLVED":
        return status or "NOT_EVALUATED", UNKNOWN
    agrees = (cell.get("agrees_with_shipped") or "").strip()
    if agrees == "1":
        uid = (cell.get("resolved_owner_cedar_uid") or "").strip()
        # Belt and braces: a CONFIRMED cell with no uid to publish is not a
        # confirmation of anything, and must not become one by default.
        return ("CONFIRMED_AS_OF", uid) if uid else \
            ("RESOLVED_OWNER_NOT_IN_CEDAR", UNKNOWN)
    if agrees == "0":
        return "CONTRADICTED_AS_OF", UNKNOWN
    return "RESOLVED_OWNER_NOT_IN_CEDAR", UNKNOWN


def load_asof():
    if not ASOF.exists():
        raise SystemExit(
            f"REFUSING: {ASOF.relative_to(ROOT)} is absent. Run "
            f"`py -3 code/515_temporal.py asof --apply` first. Stamping a "
            f"status column from a file that is not there would mark every "
            f"row NOT_EVALUATED and look like a completed pass.")
    out = {}
    with open(ASOF, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            k = ((r.get("subject_uei") or "").strip().upper(),
                 (r.get("fiscal_year") or "").strip())
            out[k] = r
    return out


def scan(asof, header_only=False):
    """Walk prime_contracts and tally rows/dollars by status. No writes."""
    by_status = defaultdict(lambda: [0, 0.0])
    with open(PRIME, encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        fields = rd.fieldnames or []
        if header_only:
            return fields, by_status
        for r in rd:
            if (r.get("attributed_flag") or "") != "1":
                continue
            k = ((r.get("awardee_uei") or "").strip().upper(),
                 (r.get("fiscal_year") or "").strip())
            status, _uid = classify(asof.get(k))
            e = by_status[status]
            e[0] += 1
            e[1] += float(r.get("total_obligations") or 0)
    return fields, by_status


def report(by_status):
    tot = sum(v[1] for v in by_status.values())
    rows = sum(v[0] for v in by_status.values())
    print(f"{'status':32} {'rows':>10} {'obligations':>20}   share")
    definite_usd = 0.0
    for s, (n, v) in sorted(by_status.items(), key=lambda kv: -kv[1][1]):
        mark = "  definite" if s in DEFINITE else ""
        if s in DEFINITE:
            definite_usd += v
        print(f"  {s:30} {n:>10,} ${v:>19,.2f}  "
              f"{100 * v / tot if tot else 0:5.1f}%{mark}")
    print(f"  {'TOTAL':30} {rows:>10,} ${tot:>19,.2f}")
    print(f"\n  MAY ship a definite historical owner: ${definite_usd:,.2f} "
          f"({100 * definite_usd / tot if tot else 0:.1f}%)")
    print(f"  MUST ship as UNKNOWN:                 "
          f"${tot - definite_usd:,.2f} "
          f"({100 * (tot - definite_usd) / tot if tot else 0:.1f}%)")
    contra = by_status.get("CONTRADICTED_AS_OF", [0, 0.0])
    print(f"  of which ACTIVELY CONTRADICTED:       ${contra[1]:,.2f} "
          f"over {contra[0]:,} rows - the sharpest bucket, and the one the "
          f"rule names")
    return tot, definite_usd


def write_exposure(by_status):
    EXPOSURE.parent.mkdir(parents=True, exist_ok=True)
    part = EXPOSURE.with_suffix(EXPOSURE.suffix + ".part")
    tot = sum(v[1] for v in by_status.values())
    with open(part, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["owner_attribution_status", "may_ship_definite_owner",
                    "n_prime_rows", "obligations_usd", "share_of_total_pct",
                    "built_date"])
        for s, (n, v) in sorted(by_status.items(), key=lambda kv: -kv[1][1]):
            w.writerow([s, int(s in DEFINITE), n, round(v, 2),
                        round(100 * v / tot, 4) if tot else 0, TODAY])
    os.replace(part, EXPOSURE)
    print(f"wrote {EXPOSURE.relative_to(ROOT)}")


def apply_status(asof):
    fields, _ = scan(asof, header_only=True)
    new_fields = list(fields)
    for c in (STATUS_COL, ASOF_OWNER_COL):
        if c not in new_fields:
            new_fields.append(c)

    by_status = defaultdict(lambda: [0, 0.0])
    unattributed = 0
    part = PRIME.with_suffix(PRIME.suffix + ".part")
    with open(PRIME, encoding="utf-8-sig", newline="") as fh, \
            open(part, "w", encoding="utf-8", newline="") as out:
        rd = csv.DictReader(fh)
        w = csv.DictWriter(out, fieldnames=new_fields)
        w.writeheader()
        for r in rd:
            if (r.get("attributed_flag") or "") != "1":
                # An unattributed row names no owner at all, so there is no
                # owner to qualify. It says so rather than being left blank.
                r[STATUS_COL] = "NO_OWNER_ATTRIBUTED"
                r[ASOF_OWNER_COL] = UNKNOWN
                unattributed += 1
                w.writerow(r)
                continue
            k = ((r.get("awardee_uei") or "").strip().upper(),
                 (r.get("fiscal_year") or "").strip())
            status, uid = classify(asof.get(k))
            r[STATUS_COL] = status
            r[ASOF_OWNER_COL] = uid if status in DEFINITE else UNKNOWN
            e = by_status[status]
            e[0] += 1
            e[1] += float(r.get("total_obligations") or 0)
            w.writerow(r)
    os.replace(part, PRIME)
    print(f"wrote {PRIME.relative_to(ROOT)} with {STATUS_COL} and "
          f"{ASOF_OWNER_COL}")
    print(f"  {unattributed:,} unattributed row(s) marked "
          f"NO_OWNER_ATTRIBUTED - they name no owner, so there is none to "
          f"qualify")
    return by_status


def verify():
    """Exit 1 if any row presents a definite historical owner it may not.

    This is the check the rule reduces to, and it is run against the FILE, not
    against the code that wrote it.
    """
    bad = defaultdict(lambda: [0, 0.0])
    missing_col = False
    seen = 0
    with open(PRIME, encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        if STATUS_COL not in (rd.fieldnames or []) \
                or ASOF_OWNER_COL not in (rd.fieldnames or []):
            missing_col = True
        else:
            for r in rd:
                seen += 1
                status = (r.get(STATUS_COL) or "").strip()
                owner = (r.get(ASOF_OWNER_COL) or "").strip()
                if status in DEFINITE:
                    if not owner or owner == UNKNOWN:
                        e = bad["DEFINITE_STATUS_WITH_NO_OWNER"]
                        e[0] += 1
                        e[1] += float(r.get("total_obligations") or 0)
                    continue
                if owner and owner != UNKNOWN:
                    e = bad[f"NOT_DEFINITE_BUT_NAMES_AN_OWNER:{status}"]
                    e[0] += 1
                    e[1] += float(r.get("total_obligations") or 0)
    if missing_col:
        print(f"FAIL: prime_contracts.csv carries an owner attribution for "
              f"dated transactions and does NOT carry {STATUS_COL}/"
              f"{ASOF_OWNER_COL}. A buyer cannot tell a confirmed historical "
              f"owner from a current one. Run --apply.")
        return 1
    if bad:
        print(f"FAIL: {sum(v[0] for v in bad.values()):,} row(s) violate the "
              f"as-of ownership rule:")
        for reason, (n, v) in sorted(bad.items(), key=lambda kv: -kv[1][1]):
            print(f"  {reason:60} {n:>9,} rows  ${v:,.2f}")
        print("  'Contradicted ownership must never silently become "
              "definite.' A row whose status is not in "
              f"{sorted(DEFINITE)} may publish only {UNKNOWN!r} as its "
              f"historical owner.")
        return 1
    print(f"OK: {seen:,} rows checked; every row that names a historical "
          f"owner has a status in {sorted(DEFINITE)}, and every row that does "
          f"not says {UNKNOWN!r}.")
    return 0


# --------------------------------------------------------------------------
# codebook - the same reason as 428: the codebook decides what ships, so a
# column change that is not registered can unship the dataset silently.
# --------------------------------------------------------------------------
CB_DATASET = "02_prime_contracting"
CB_FRAG = ROOT / "data" / "clean" / "codebook" / (CB_DATASET + ".csv")
CB_MASTER = CLEAN / "codebook_master.csv"

NEW_VARIABLES = {
    STATUS_COL: ("text", "category",
        "Whether Cedar's owner attribution on this row is CONFIRMED for the "
        "transaction's own fiscal year by the temporal layer "
        "(`code/515_temporal.py asof`). One of: CONFIRMED_AS_OF (the layer "
        "confirms this owner held the firm that year - the ONLY status that "
        "may carry a historical owner); CONTRADICTED_AS_OF (the layer says "
        "someone else held it); RESOLVED_OWNER_NOT_IN_CEDAR (a parent UEI "
        "resolved but Cedar holds no entity for it, so the shipped owner is "
        "neither confirmed nor denied); UNKNOWN_OUTSIDE_EVIDENCE, "
        "AMBIGUOUS_OVERLAP, NO_FACT_ON_SUBJECT, NO_COVERING_FACT, "
        "AMBIGUOUS_GRANULARITY (the resolver's own verdicts); NOT_EVALUATED "
        "(no as-of cell exists for this awardee_uei and fiscal year); "
        "NO_OWNER_ATTRIBUTED (the row is not attributed to a Native entity at "
        "all). `tribe_id` and `cedar_uid` are Cedar's CURRENT attribution and "
        "are unaffected by this column."),
    ASOF_OWNER_COL: ("text", "code",
        "The entity the temporal layer CONFIRMS owned this firm during this "
        "transaction's fiscal year, or the literal `UNKNOWN`. Unknown "
        "ownership ships as unknown; contradicted ownership never ships as a "
        "definite historical owner, and is never filled in from current "
        "ownership. Non-UNKNOWN on 18.6% of attributed prime obligations. Use "
        "`cedar_uid` for the current owner and this column for the "
        "as-of-transaction owner - they are different questions and Cedar "
        "answers them separately."),
}


def register_codebook(n_rows, filled):
    for path, label in ((CB_FRAG, "fragment"), (CB_MASTER, "master")):
        with open(path, encoding="utf-8-sig", newline="") as fh:
            rd = csv.DictReader(fh)
            fields = rd.fieldnames or []
            rows = list(rd)
        have = {r["variable"] for r in rows if r.get("dataset") == CB_DATASET}
        add = []
        for v, (typ, units, desc) in NEW_VARIABLES.items():
            if v in have:
                continue
            add.append({
                "dataset": CB_DATASET, "variable": v, "type": typ,
                "units": units,
                "pct_filled": "%.1f" % (100.0 * filled.get(v, 0) / n_rows),
                "n_rows": str(n_rows), "published": "1",
                "access_tier": "public", "description": desc,
                "generated": TODAY,
            })
        if not add:
            print(f"  codebook {label}: already registered, no change")
            continue
        bak = path.with_suffix(path.suffix + ".bak_%s_pre429_codebook" % TODAY)
        if not bak.exists():
            bak.write_bytes(path.read_bytes())
        part = path.with_suffix(path.suffix + ".part")
        with open(part, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
            w.writeheader()
            w.writerows(rows + add)
        os.replace(part, path)
        print(f"  codebook {label}: +{len(add)} variable(s)")

    import cedar_codebook as CB
    import importlib
    importlib.reload(CB)
    grp, score = CB.match_group(CB.header_of(PRIME), CB.dataset_groups())
    print(f"  codebook match for prime_contracts.csv: {grp} at {score:.3f} "
          f"(threshold {CB.MATCH_THRESHOLD})")
    if score < CB.MATCH_THRESHOLD:
        raise SystemExit(
            "REFUSING to leave prime_contracts.csv undocumented - an "
            "unregistered column change unships the dataset.")


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--apply", action="store_true")
    g.add_argument("--verify", action="store_true")
    args = ap.parse_args()

    if args.verify:
        return verify()

    print("=== Cedar Press 429: as-of ownership status on prime contracts ===")
    print(f"    the rule: unknown ownership may ship AS UNKNOWN; "
          f"contradicted ownership may never ship as a definite historical "
          f"owner\n")
    asof = load_asof()
    print(f"as-of layer: {len(asof):,} (uei, fiscal_year) cells from "
          f"{ASOF.relative_to(ROOT)}\n")

    if args.check:
        _fields, by_status = scan(asof)
        report(by_status)
        print("\nCHECK ONLY. Nothing was written.")
        return 0

    by_status = apply_status(asof)
    print()
    report(by_status)
    write_exposure(by_status)
    n_rows = sum(v[0] for v in by_status.values())
    definite = sum(v[0] for s, v in by_status.items() if s in DEFINITE)
    register_codebook(n_rows, {STATUS_COL: n_rows, ASOF_OWNER_COL: definite})
    print()
    rc = verify()
    print("\nNOW RUN: py -3 code/62_no_regression_check.py")
    return rc


if __name__ == "__main__":
    sys.exit(main())
