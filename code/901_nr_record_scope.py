#!/usr/bin/env python3
"""
Cedar Press - 901: ADR-010 `record_scope` for `resource_revenue.csv`.

    py -3 code/901_nr_record_scope.py               # apply, in place, backup
    py -3 code/901_nr_record_scope.py verify        # read-only, exit 1 on breach
    py -3 code/901_nr_record_scope.py verify --selftest
                                                    # prove verify fires

WHY THIS EXISTS
---------------
`natural-resources` was BLOCKED on C4 at "25% of entity-bearing rows carry a
Cedar id". 9,791 of the 11,305 revenue rows are `national_aggregate` because
**Interior publishes Native American resource revenue only in aggregate, by
law**. The publisher says so in its own words:

  "For all Native American land, the federal government only releases natural
   resource extraction and revenue information in aggregate. Specific data on
   Native American revenues are confidential and proprietary. Treaties, laws,
   and regulations dictate what data the government can release."
   -- https://revenuedata.doi.gov/how-revenue-works/native-american-revenue/

Measured on the file: `State`, `County`, `FIPS Code` and `Offshore Region` are
blank on 100% of Native American rows against 99.8% populated on the Federal
rows in the same extract (docs/RESOURCE_LEDGER_BUILD_LOG.md). There is no
entity on the row to carry an id, and counting those rows as "unkeyed" scores
the statute rather than the data.

ADR-010 already decided this and says so in as many words: *"Coverage is
measured against the resolvable denominator, not the row count."* What was
missing was the per-row column that makes the resolvable denominator
derivable. 518's own comment says the same - *"the honest denominator is not
yet derivable per row. Deriving it is the work ADR-010 sets up."* This is that
work, for this table.

THE MAPPING, AND ITS EVIDENCE
-----------------------------
Scope is a deterministic function of `aggregation_level` + `source_system`.
Nothing here is judged row by row.

  national_aggregate      -> indian_country  Interior aggregates by law (above)
  entity_specific         -> entity          a Native entity is named, either
                                             in a role column or in the
                                             resource_parties bridge
  per_headright_rate      -> entity          the subject is the Osage mineral
                                             estate - ONE Native entity, on the
                                             bridge as mineral_estate_owner at
                                             100%. The RECIPIENT is a class of
                                             individual headright holders and
                                             is never published as individuals;
                                             that is publication policy, not an
                                             unresolved link. The Council's
                                             2,228.97393 divisor is a CHECK and
                                             never a multiplier.
  entity_specific_component -> unresolved    the Osage Minerals Council
                                             newsletter names the estate and
                                             no bridge row has been written.
                                             THE ONLY DEFECT SCOPE - 60 rows,
                                             and they stay in the denominator.
  state_aggregate / UT    -> native_serving  Utah Code 63N-24-703(4): the fund
                                             "consists of state severance tax
                                             money to be spent at the
                                             discretion of the state" and
                                             "does not constitute a trust
                                             fund". The build ruled that
                                             writing a tribe as recipient
                                             would invent an ownership fact;
                                             the tribe appears in
                                             resource_parties as
                                             `serves_native_entities`.
  state_aggregate / MT    -> geographic      the quarterly distribution letter
                                             carries a tribal line and NAMES NO
                                             TRIBE - recorded verbatim in
                                             `beneficiary_note` on all 49 rows.
                                             The record is scoped to Montana.

THE ANTI-GAMING INVARIANT
-------------------------
A scope column can be used to make a bad number look good by scoping attached
rows out of the denominator. So this script asserts, and `verify` re-asserts:

  **no row scoped `indian_country`, `geographic` or `native_serving` may carry
  a `cedar_uid`, or a `parent_native_entity` party in resource_parties.csv.**

A row only leaves the C4 denominator when nothing in Cedar stands behind it.
The Utah rows pass because their bridge relationship is
`serves_native_entities`, which ADR-010 defines as deliberately unkeyed on the
actor side - not because they were quietly excused.

Runs AFTER `900_nr_hub_join.py`. Backs up as `.bak_<date>_pre901`.
"""
from __future__ import annotations

import csv
import json
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()

TABLE = ROOT / "data" / "clean" / "resource_revenue.csv"
PARTIES = ROOT / "data" / "clean" / "resource_parties.csv"
CENSUS = ROOT / "docs" / "schema" / "nr_record_scope_census.json"

MONEY = ["amount_usd", "amount_usd_real2025"]

# ADR-010 vocabulary. Only `unresolved` is a defect; only these three leave
# the C4 denominator.
NON_ENTITY = {"indian_country", "geographic", "native_serving"}
VOCAB = {"entity", "multi_entity", "unresolved"} | NON_ENTITY

DOI_QUOTE = ('Interior releases Native American resource revenue ONLY in '
             'aggregate: "For all Native American land, the federal government '
             'only releases natural resource extraction and revenue '
             'information in aggregate. Specific data on Native American '
             'revenues are confidential and proprietary." '
             'https://revenuedata.doi.gov/how-revenue-works/native-american-revenue/ '
             '- measured: State/County/FIPS/Offshore Region blank on 100% of '
             'Native American rows vs 99.8% populated on Federal rows in the '
             'same extract. No entity exists on the row to carry an id.')


def nz(r, c):
    return (r.get(c) or "").strip()


def read_csv(p: Path):
    with p.open(encoding="utf-8-sig", newline="") as fh:
        rdr = csv.DictReader(fh)
        return list(rdr), list(rdr.fieldnames or [])


def write_csv(p: Path, rows, cols):
    tmp = p.with_suffix(p.suffix + ".part")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    tmp.replace(p)


def money_sum(rows):
    out = {}
    for c in MONEY:
        t = Decimal(0)
        for r in rows:
            v = nz(r, c).replace(",", "").replace("$", "")
            if v:
                try:
                    t += Decimal(v)
                except Exception:
                    pass
        out[c] = str(t)
    return out


def parent_parties():
    """revenue_event -> True when a Native entity STANDS BEHIND the row."""
    pr, _ = read_csv(PARTIES)
    out = defaultdict(bool)
    for p in pr:
        if p.get("object_type") != "revenue_event":
            continue
        if p.get("relationship") != "parent_native_entity":
            continue
        if nz(p, "entity_id") or nz(p, "cedar_uid"):
            out[nz(p, "object_id")] = True
    return out


def classify(r):
    lvl = nz(r, "aggregation_level")
    src = nz(r, "source_system")
    if lvl == "national_aggregate":
        return "indian_country", DOI_QUOTE
    if lvl == "per_headright_rate":
        return "entity", (
            "the subject is the Osage mineral estate - one Native entity, "
            "carried in resource_parties.csv as mineral_estate_owner "
            "(relationship=parent_native_entity, interest_share_pct=100). The "
            "recipient is a class of individual headright holders and is "
            "never published as individuals; the Council's 2,228.97393 "
            "headright divisor is a check, never a multiplier.")
    if lvl == "state_aggregate":
        if src == "UT_COBI_fund_financials":
            return "native_serving", (
                'Utah Code 63N-24-703(4): the fund "consists of state '
                'severance tax money to be spent at the discretion of the '
                'state" and "does not constitute a trust fund". No tribe is '
                "recipient or beneficiary; the tribe is carried in "
                "resource_parties.csv as serves_native_entities. Writing a "
                "parent here would invent an ownership fact "
                "(docs/RESOURCE_LEDGER_BUILD_LOG.md section 3).")
        return "geographic", (
            "Montana DOR quarterly county oil and gas distribution letter. "
            "The letter carries a tribal distribution line and NAMES NO "
            "TRIBE and no county - recorded verbatim in beneficiary_note and "
            "geography_note on the row. The record is scoped to the State of "
            "Montana, not to an entity.")
    if lvl == "entity_specific_component":
        return "unresolved", (
            "Osage Minerals Council quarterly newsletter line item. The "
            "estate is nameable and no resource_parties bridge row has been "
            "written for these events. THIS IS THE WORK QUEUE - the rows stay "
            "in the C4 denominator and count as misses.")
    if lvl == "entity_specific":
        return "entity", (
            "a Native entity is named on the row in a role-prefixed id "
            "column, or stands behind it in resource_parties.csv with "
            "relationship=parent_native_entity")
    return "unresolved", f"no scope rule for aggregation_level={lvl!r}"


def build():
    rows, before = read_csv(TABLE)
    after = list(before)
    for c in ("record_scope", "record_scope_basis"):
        if c not in after:
            after.append(c)
    parents = parent_parties()
    st, breaches = Counter(), []
    for r in rows:
        scope, basis = classify(r)
        if scope not in VOCAB:
            breaches.append(f"scope {scope!r} outside the ADR-010 vocabulary")
        r["record_scope"], r["record_scope_basis"] = scope, basis
        st[scope] += 1
        attached = bool(nz(r, "cedar_uid")) or parents.get(
            nz(r, "resource_revenue_event_id"), False)
        if attached:
            st[f"{scope}:attached"] += 1
        # ---- the anti-gaming invariant --------------------------------
        if scope in NON_ENTITY and attached:
            breaches.append(
                f"{nz(r,'resource_revenue_event_id')}: scoped {scope} (out of "
                f"the C4 denominator) but a Cedar entity stands behind it")
    return rows, before, after, st, breaches


def main() -> int:
    args = sys.argv[1:]
    verify = bool(args) and args[0] == "verify"
    if "--selftest" in args:
        return selftest()

    pre_rows, _ = read_csv(TABLE)
    pre = dict(rows=len(pre_rows), money=money_sum(pre_rows))

    rows, before, after, st, breaches = build()

    if len(rows) != pre["rows"]:
        breaches.append(f"ROW COUNT {pre['rows']} -> {len(rows)}")
    m = money_sum(rows)
    for c, v in pre["money"].items():
        if m[c] != v:
            breaches.append(f"MONEY {c} {v} -> {m[c]}")
    lost = [c for c in before if c not in after]
    if lost:
        breaches.append(f"COLUMNS LOST {lost}")

    denom = sum(v for k, v in st.items()
                if ":" not in k and k not in NON_ENTITY)
    att = sum(v for k, v in st.items()
              if k.endswith(":attached")
              and k.split(":")[0] not in NON_ENTITY)
    print(f"\n  resource_revenue.csv   {len(rows):,} rows"
          f"   + {[c for c in after if c not in before] or 'none'}"
          f"   - {lost or 'none'}")
    print(f"  money unchanged: " +
          "  ".join(f"{c}={v}" for c, v in m.items()))
    print("\n  ADR-010 record_scope")
    for k in sorted(x for x in st if ":" not in x):
        mark = "  (out of the C4 denominator)" if k in NON_ENTITY else ""
        print(f"    {k:18s} {st[k]:7,}   attached {st.get(k+':attached',0):6,}{mark}")
    print(f"\n  C4 on the resolvable denominator: {att:,} / {denom:,} = "
          f"{100.0*att/denom if denom else 0:.1f}%"
          f"   (raw row-count denominator would say "
          f"{100.0*sum(st.get(k+':attached',0) for k in VOCAB)/len(rows):.1f}%)")

    if breaches:
        print("\n  !! INVARIANT BREACH")
        for b in breaches[:20]:
            print("     " + b)
        return 1

    if verify:
        if not CENSUS.exists():
            print(f"\n  no census at {CENSUS} - run without `verify` first")
            return 1
        old = json.loads(CENSUS.read_text(encoding="utf-8"))
        live, _ = read_csv(TABLE)
        drift = []
        if len(live) != old["rows"]:
            drift.append(f"rows {old['rows']} -> {len(live)}")
        lm = money_sum(live)
        for c, v in old["money"].items():
            if lm.get(c) != v:
                drift.append(f"money {c} {v} -> {lm.get(c)}")
        lc = Counter(nz(r, "record_scope") for r in live)
        for k, v in old["scopes"].items():
            if lc.get(k, 0) != v:
                drift.append(f"scope {k} {v} -> {lc.get(k,0)}")
        if "" in lc:
            drift.append(f"{lc['']} rows carry NO record_scope")
        if drift:
            print("\n  !! VERIFY FAILED")
            for d in drift:
                print("     " + d)
            return 1
        print("\n  verify OK")
        return 0

    bak = TABLE.with_name(TABLE.name + f".bak_{TODAY}_pre901")
    if not bak.exists():
        shutil.copy2(TABLE, bak)
    write_csv(TABLE, rows, after)
    CENSUS.write_text(json.dumps(dict(
        generated=TODAY, rows=len(rows), money=m,
        scopes={k: st[k] for k in st if ":" not in k},
        attached={k: st[k] for k in st if k.endswith(":attached")},
        resolvable_denominator=denom, attached_in_denominator=att),
        indent=1), encoding="utf-8")
    print(f"\n  wrote {TABLE.name} + census {CENSUS.relative_to(ROOT)}")
    return 0


def selftest() -> int:
    """Corrupt the file three ways; each must make `verify` exit 1."""
    if not CENSUS.exists():
        print("  run 901 without `verify` first")
        return 1
    keep = TABLE.read_bytes()
    ok = True
    try:
        for label, mutate in (
            ("one record_scope blanked",
             lambda rows: rows[0].__setitem__("record_scope", "")),
            ("a national_aggregate row re-scoped to `entity` "
             "(inflates the denominator)",
             lambda rows: next(r for r in rows
                               if r["record_scope"] == "indian_country")
             .__setitem__("record_scope", "entity")),
            ("an ATTACHED row scoped out to `indian_country` "
             "(the anti-gaming guard)",
             lambda rows: next(r for r in rows
                               if (r.get("cedar_uid") or "").strip())
             .__setitem__("record_scope", "indian_country")),
        ):
            TABLE.write_bytes(keep)
            rows, cols = read_csv(TABLE)
            mutate(rows)
            write_csv(TABLE, rows, cols)
            rc = _verify_only()
            print(f"  synthetic violation: {label}\n"
                  f"      verify exit={rc} -> "
                  f"{'FIRED' if rc else 'DID NOT FIRE'}")
            ok = ok and rc == 1
    finally:
        TABLE.write_bytes(keep)
    rc = _verify_only()
    print(f"  restored: verify exit={rc} -> {'clean' if rc == 0 else 'FAILING'}")
    return 0 if ok and rc == 0 else 1


def _verify_only() -> int:
    old = json.loads(CENSUS.read_text(encoding="utf-8"))
    live, _ = read_csv(TABLE)
    if len(live) != old["rows"]:
        return 1
    lm = money_sum(live)
    for c, v in old["money"].items():
        if lm.get(c) != v:
            return 1
    lc = Counter(nz(r, "record_scope") for r in live)
    if "" in lc:
        return 1
    for k, v in old["scopes"].items():
        if lc.get(k, 0) != v:
            return 1
    parents = parent_parties()
    for r in live:
        if (nz(r, "record_scope") in NON_ENTITY
                and (nz(r, "cedar_uid")
                     or parents.get(nz(r, "resource_revenue_event_id"), False))):
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
