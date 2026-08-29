#!/usr/bin/env python3
"""
Cedar Press - the prime contracting ENTITY-YEAR panel, in one place.

WHY THIS MODULE EXISTS
----------------------
`prime_contracts_entity_year.csv` had THREE independent copies of its
aggregation logic - in `40_build_prime_contracts.py`, in
`131_merge_archive_backfill.py`, and (as an append path) in
`114_pull_prime_archive.py`. All three keyed the panel on

    (tribe_id, canonical_name, fiscal_year, confidence_tier)

which is not what the file is NAMED, is not what a buyer assumes, and is not
what the contract declared. One entity-year therefore held up to 3 rows.
Fixing that in one of three copies would have left the other two to put it
back on the next run, so the aggregation now lives here and the three scripts
call it.


THE GRAIN, AND THE EVIDENCE FOR CHOOSING IT
-------------------------------------------
Measured on data/clean/prime_contracts.csv, 2026-08-29, 888,862 attributed
rows carrying $244,765,639,853.97:

    key                                                  rows        sum
    (tribe_id, canonical_name, fiscal_year, tier)       8,477   $244.765639B
    (tribe_id, fiscal_year)                             6,715   $244.765639B

**The two sums are identical to the cent.** Every source row lands in exactly
one bucket under either key, so the name/tier rows PARTITION the entity-year -
they never restate the same dollars. Collapsing them therefore cannot lose a
dollar, and that is what makes the entity-year grain the honest one.

The two extra dimensions were also asymmetric in worth:

  * `canonical_name` is NOISE. 56 of 498 entities carried more than one, and
    every case measured was the same entity under a longer or shorter label
    off the identifier ledger - `Mille Lacs` vs `Mille Lacs Band of Ojibwe`,
    `Catawba` vs `Catawba Indian Nation of South Carolina`. The entity spine
    already holds exactly one canonical name per `tribe_id`, and that is the
    one this panel publishes. The variants are still reported, as a COLUMN,
    so no observation is destroyed.

  * `confidence_tier` is REAL. 1,487 of 6,715 entity-years mix tier A and
    tier B attributions, and $68.0B of the $244.8B total is tier B. A buyer
    who wants tier-A-only dollars must still be able to get them. So the tier
    survives as `obligations_usd_tier_a` / `obligations_usd_tier_b` COLUMNS
    rather than as extra rows - the distinction is kept, the fan-out is not.

`confidence_tier` is DELIBERATELY NOT CARRIED FORWARD UNDER ITS OLD NAME.
A column called `confidence_tier` holding "A", "B" or "A+B" would let
`df[df.confidence_tier == "A"]` return a partial, plausible, wrong number -
only the entity-years that happen to be pure tier A. A KeyError is loud; a
silently truncated filter is not. The tier now reads out of named money
columns and out of `confidence_tiers`, which is a SET rendered as `A+B`.


WHAT THE OLD GRAIN ACTUALLY COST A BUYER
----------------------------------------
Not, as first supposed, an inflated `groupby(["tribe_id","fiscal_year"]).sum()`
- that returned the right total, because the rows partition. The damage was on
the JOIN. Any entity-year table joined to this one on (tribe_id, fiscal_year)
FANNED OUT up to 3x, multiplying the OTHER table's money by the number of name
and tier variants Cedar happened to hold for that entity. The file is named
entity-year and declared `tribe_id` as a key column, so nothing warned the
buyer; the merge simply returned more rows than it started with and every
figure downstream of it was wrong.

Reads  data/clean/prime_contracts.csv        (the row-level source of truth)
       data/spine/cedar_entity_spine.csv     (the ONE canonical name per entity)
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"

#: The published column order. `confidence_tier` is absent by design - see the
#: module docstring. `cedar_uid` is stamped by `503_identity.py` and is carried
#: through here rather than dropped, because a rebuild that drops it ships a
#: dataset a customer cannot join.
PANEL_FIELDS = [
    "tribe_id",
    "cedar_uid",
    "canonical_name",
    "fiscal_year",
    "obligations_usd",
    "n_contracts",
    "obligations_usd_tier_a",
    "n_contracts_tier_a",
    "obligations_usd_tier_b",
    "n_contracts_tier_b",
    "confidence_tiers",
    "attribution_name_variants_n",
    "attribution_names",
    # THE AS-OF OWNERSHIP SPLIT. See `code/429_apply_asof_ownership_status.py`.
    # `obligations_usd` attributes on Cedar's CURRENT ownership. These two say
    # how much of it the temporal layer confirms was owned by this entity in
    # THIS fiscal year, and how much it does not. Unknown ownership ships as
    # unknown; it is never filled in from the current owner.
    "obligations_usd_owner_asof_confirmed",
    "obligations_usd_owner_asof_not_confirmed",
    "owner_attribution_statuses",
    "built_date",
]

#: The declared primary key. Validated on every build by `assert_grain`, and
#: declared to the contract layer in `512_build_dataset_contracts.py`.
PANEL_PRIMARY_KEY = ["tribe_id", "fiscal_year"]

#: The one as-of status that may carry a definite historical owner. Kept in
#: step with `429_apply_asof_ownership_status.DEFINITE`; a second member is a
#: decision, not a default.
ASOF_DEFINITE = {"CONFIRMED_AS_OF"}

PRIME = CLEAN / "prime_contracts.csv"


class PanelGrainError(Exception):
    """The panel about to be written is not one row per (entity, year)."""


class PanelConservationError(Exception):
    """The panel does not carry the same dollars as the rows it aggregates."""


def spine_canonical_names():
    """tribe_id -> the ONE canonical name the entity spine holds for it.

    The spine is the authority on an entity's name. The identifier ledger
    holds whatever label a registration was filed under, and those labels are
    what produced the name-variant rows this module exists to collapse.
    """
    out = {}
    with open(SPINE / "cedar_entity_spine.csv",
              encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            out[(r.get("tribe_id") or "").strip()] = \
                (r.get("canonical_name") or "").strip()
    return out


def existing_uids(panel_path):
    """tribe_id -> cedar_uid, read off the panel already on disk.

    `503_identity.py stamp` materialises `cedar_uid` onto this table from
    `tribe_id`, so the mapping is a pure function of tribe_id and carrying it
    forward reproduces exactly what a re-stamp would write. A tribe_id the
    file does not carry a uid for is returned as "" and COUNTED by the caller,
    never quietly filled from somewhere else.
    """
    p = Path(panel_path)
    if not p.exists():
        return {}
    out = {}
    with open(p, encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        if "cedar_uid" not in (rd.fieldnames or []):
            return {}
        for r in rd:
            t = (r.get("tribe_id") or "").strip()
            u = (r.get("cedar_uid") or "").strip()
            if t and u:
                out.setdefault(t, u)
    return out


def aggregate(rows, today, spine_names=None, uid_of=None):
    """Row-level prime contracts -> the entity-year panel.

    `rows` is any iterable of dicts carrying at least `attributed_flag`,
    `tribe_id`, `fiscal_year`, `confidence_tier`, `canonical_name` and
    `total_obligations`. Unattributed rows enter no entity total and are
    skipped here exactly as they were skipped by the three copies this
    replaces.

    Returns (panel_rows, stats). `stats` names every category the function
    dropped or could not fill - a skip counter that does not say what it
    skipped is how this project has lost rows before.
    """
    spine_names = spine_names if spine_names is not None else {}
    uid_of = uid_of if uid_of is not None else {}

    acc = defaultdict(lambda: {
        "obl": 0.0, "n": 0,
        "obl_a": 0.0, "n_a": 0,
        "obl_b": 0.0, "n_b": 0,
        "obl_asof_ok": 0.0, "obl_asof_no": 0.0,
        "tiers": set(), "names": set(), "asof": set(),
    })
    # EVERY EXCLUSION IS NAMED, NOT COUNTED.
    #
    # This function used to keep bare `rows_unattributed_skipped += 1` tallies.
    # A number that says 328,906 rows did not enter any entity total, and
    # cannot say WHICH, is defect class 2c - "the 87 defect": the count goes in
    # the log, the identity does not, and nobody can act on it. So each
    # exclusion accumulates into a keyed bucket carrying the vendor, the
    # identifier, the year, the row count and the dollars, and the caller
    # writes those buckets to `review/prime_entity_year_excluded_rows.csv`.
    # The counts are then DERIVED from the buckets rather than tracked beside
    # them, so a count and its bucket cannot drift apart.
    excluded = defaultdict(lambda: [0, 0.0])
    stats = {
        "rows_read": 0,
        "rows_aggregated": 0,
        "excluded": excluded,
        "tier_other_than_A_or_B": defaultdict(int),
        "entities_missing_from_spine": set(),
        "entities_missing_cedar_uid": set(),
    }

    for r in rows:
        stats["rows_read"] += 1
        v_raw = float(r.get("total_obligations") or 0)
        who = (str(r.get("awardee_uei") or "").strip().upper(),
               str(r.get("awardee_name") or "").strip(),
               str(r.get("fiscal_year") or "").strip())
        # CSV gives strings, `40_build_prime_contracts.py` hands us the dicts
        # it is about to write and those carry ints. Coerce rather than assume:
        # `1 != "1"` silently skipped EVERY row the first time this module was
        # called from 40, and an empty panel would have looked like a clean run.
        if str(r.get("attributed_flag") or "").strip() != "1":
            e = excluded[who + ("NOT_ATTRIBUTED_TO_A_NATIVE_ENTITY",)]
            e[0] += 1
            e[1] += v_raw
            continue
        tid = str(r.get("tribe_id") or "").strip()
        fy = str(r.get("fiscal_year") or "").strip()
        if not tid:
            e = excluded[who + ("ATTRIBUTED_FLAG_1_BUT_NO_TRIBE_ID",)]
            e[0] += 1
            e[1] += v_raw
            continue
        if not fy:
            e = excluded[who + ("ATTRIBUTED_BUT_NO_FISCAL_YEAR",)]
            e[0] += 1
            e[1] += v_raw
            continue
        tier = str(r.get("confidence_tier") or "").strip()
        v = v_raw

        a = acc[(tid, fy)]
        a["obl"] += v
        a["n"] += 1
        if tier == "A":
            a["obl_a"] += v
            a["n_a"] += 1
        elif tier == "B":
            a["obl_b"] += v
            a["n_b"] += 1
        else:
            # Not silently folded into the total-only columns: the builder
            # only ever attributes on tiers A and B, so anything else is a
            # finding and is named on stdout by the caller.
            stats["tier_other_than_A_or_B"][tier or "(blank)"] += 1
        # AS-OF OWNERSHIP. `429` stamps the row; a file that has not been
        # through 429 yet has no column, and the rollup says NOT_STAMPED
        # rather than quietly counting those dollars as confirmed.
        asof = str(r.get("owner_attribution_status") or "").strip() \
            or "NOT_STAMPED"
        a["asof"].add(asof)
        if asof in ASOF_DEFINITE:
            a["obl_asof_ok"] += v
        else:
            a["obl_asof_no"] += v
        if tier:
            a["tiers"].add(tier)
        nm = str(r.get("canonical_name") or "").strip()
        if nm:
            a["names"].add(nm)
        stats["rows_aggregated"] += 1

    out = []
    for (tid, fy), a in sorted(acc.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        canon = spine_names.get(tid, "")
        if not canon:
            stats["entities_missing_from_spine"].add(tid)
            # Fall back to the ledger label rather than shipping a blank name,
            # and say so in the stats. Never invent one.
            canon = sorted(a["names"])[0] if a["names"] else ""
        uid = uid_of.get(tid, "")
        if not uid:
            stats["entities_missing_cedar_uid"].add(tid)
        out.append({
            "tribe_id": tid,
            "cedar_uid": uid,
            "canonical_name": canon,
            "fiscal_year": fy,
            "obligations_usd": round(a["obl"], 2),
            "n_contracts": a["n"],
            "obligations_usd_tier_a": round(a["obl_a"], 2),
            "n_contracts_tier_a": a["n_a"],
            "obligations_usd_tier_b": round(a["obl_b"], 2),
            "n_contracts_tier_b": a["n_b"],
            "confidence_tiers": "+".join(sorted(a["tiers"])),
            "attribution_name_variants_n": len(a["names"]),
            "attribution_names": " | ".join(sorted(a["names"])),
            "obligations_usd_owner_asof_confirmed": round(a["obl_asof_ok"], 2),
            "obligations_usd_owner_asof_not_confirmed":
                round(a["obl_asof_no"], 2),
            "owner_attribution_statuses": "+".join(sorted(a["asof"])),
            "built_date": today,
        })
    return out, stats


def assert_grain(panel_rows):
    """REFUSE to write a panel that is not one row per (tribe_id, fiscal_year).

    This is the check the declared grain rests on, and it runs INSIDE the
    builder rather than only in the contract layer, so a defective panel is
    never written to disk in the first place.
    """
    seen = defaultdict(int)
    for r in panel_rows:
        seen[tuple(r[k] for k in PANEL_PRIMARY_KEY)] += 1
    dupes = {k: n for k, n in seen.items() if n > 1}
    if dupes:
        worst = sorted(dupes.items(), key=lambda kv: -kv[1])[:5]
        raise PanelGrainError(
            f"{len(dupes):,} (tribe_id, fiscal_year) key(s) appear more than "
            f"once across {len(panel_rows):,} rows. The declared primary key "
            f"{PANEL_PRIMARY_KEY} would be a lie and any buyer joining on it "
            f"would fan out. Worst: "
            + "; ".join(f"{k} x{n}" for k, n in worst))
    return True


def rounding_bound(n_rows):
    """The largest difference ROUNDING alone can produce over `n_rows` cells.

    Every published figure is rounded to the cent, so each row can differ from
    its unrounded value by at most half a cent. The bound is therefore
    `0.005 * n_rows`, plus a cent of float slop on the summation itself. It is
    DERIVED rather than picked, because a hand-picked tolerance is how a real
    loss gets waved through as 'rounding'.
    """
    return 0.005 * n_rows + 0.01


def assert_conservation(panel_rows, source_total, tol=None):
    """REFUSE to write a panel whose dollars differ from the rows it sums.

    `tol` defaults to `rounding_bound(len(panel_rows))` - the arithmetic
    maximum that cent-rounding can account for. Anything larger is a lost or
    duplicated transaction, not arithmetic.
    """
    if tol is None:
        tol = rounding_bound(len(panel_rows))
    panel_total = sum(float(r["obligations_usd"]) for r in panel_rows)
    if abs(panel_total - source_total) > tol:
        raise PanelConservationError(
            f"panel totals ${panel_total:,.2f} but the attributed rows it "
            f"aggregates total ${source_total:,.2f} - a difference of "
            f"${panel_total - source_total:,.2f}, which exceeds the "
            f"${tol:,.4f} that cent-rounding over {len(panel_rows):,} rows "
            f"can account for. An aggregate that does not conserve its "
            f"source is not an aggregate.")
    asof_total = sum(float(r["obligations_usd_owner_asof_confirmed"])
                     + float(r["obligations_usd_owner_asof_not_confirmed"])
                     for r in panel_rows)
    if abs(asof_total - panel_total) > tol:
        raise PanelConservationError(
            f"the as-of ownership split totals ${asof_total:,.2f} but "
            f"obligations_usd totals ${panel_total:,.2f}. Every dollar is "
            f"either confirmed as-of or it is not; a third bucket means "
            f"dollars would vanish from whichever half a buyer takes.")
    # The tier columns must also add back to the total, or a buyer splitting
    # by tier gets a different answer than one who does not.
    tier_total = sum(float(r["obligations_usd_tier_a"])
                     + float(r["obligations_usd_tier_b"]) for r in panel_rows)
    if abs(tier_total - panel_total) > tol:
        raise PanelConservationError(
            f"tier A + tier B totals ${tier_total:,.2f} but obligations_usd "
            f"totals ${panel_total:,.2f} (tolerance ${tol:,.4f}). Some "
            f"dollars carry a confidence_tier that is neither A nor B and "
            f"would vanish from a tier split.")
    return True


def build_from_prime(prime_path=None, panel_path=None, today=None):
    """The whole job: read prime_contracts.csv, return (panel_rows, stats).

    Does not write. The caller writes, so that a script which wants to build
    the panel into a temporary file for a diff can do so without touching the
    shipped one.
    """
    from datetime import date
    csv.field_size_limit(10 ** 9)
    prime_path = Path(prime_path or PRIME)
    panel_path = Path(panel_path or (CLEAN / "prime_contracts_entity_year.csv"))
    today = today or date.today().isoformat()

    names = spine_canonical_names()
    uids = existing_uids(panel_path)

    source_total = 0.0
    with open(prime_path, encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        missing = [c for c in ("attributed_flag", "tribe_id", "fiscal_year",
                               "confidence_tier", "canonical_name",
                               "total_obligations")
                   if c not in (rd.fieldnames or [])]
        if missing:
            raise PanelGrainError(
                f"{prime_path.name} is missing column(s) {missing}; refusing "
                f"to aggregate a table whose shape has changed underneath "
                f"this module rather than report a wrong zero.")

        def _rows():
            nonlocal source_total
            for r in rd:
                if (r.get("attributed_flag") or "") == "1" \
                        and (r.get("tribe_id") or "").strip() \
                        and (r.get("fiscal_year") or "").strip():
                    source_total += float(r.get("total_obligations") or 0)
                yield r

        panel, stats = aggregate(_rows(), today, spine_names=names,
                                 uid_of=uids)

    assert_grain(panel)
    assert_conservation(panel, source_total)
    stats["source_attributed_obligations_usd"] = round(source_total, 2)
    return panel, stats


def write_panel(panel_rows, panel_path):
    """Atomic write through a `.part` file, PANEL_FIELDS order."""
    import os
    p = Path(panel_path)
    part = p.with_suffix(p.suffix + ".part")
    with open(part, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=PANEL_FIELDS)
        w.writeheader()
        w.writerows(panel_rows)
    os.replace(part, p)
    return p


EXCLUDED_ROWS_FILE = CEDAR / "review" / "prime_entity_year_excluded_rows.csv"
EXCLUDED_FIELDS = ["awardee_uei", "awardee_name", "fiscal_year",
                   "exclusion_reason", "n_rows", "obligations_usd",
                   "built_date"]


def excluded_by_reason(stats):
    """reason -> (n_rows, obligations_usd), derived from the bucket."""
    out = defaultdict(lambda: [0, 0.0])
    for (_uei, _nm, _fy, reason), (n, v) in stats["excluded"].items():
        out[reason][0] += n
        out[reason][1] += v
    return {k: (v[0], round(v[1], 2)) for k, v in out.items()}


def write_excluded(stats, today, path=None):
    """Write every excluded (vendor, identifier, year) - not a sample."""
    import os
    path = Path(path or EXCLUDED_ROWS_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(path.suffix + ".part")
    rows = sorted(stats["excluded"].items(), key=lambda kv: (-kv[1][1], kv[0]))
    with open(part, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=EXCLUDED_FIELDS)
        w.writeheader()
        for (uei, nm, fy, reason), (n, v) in rows:
            w.writerow({"awardee_uei": uei, "awardee_name": nm,
                        "fiscal_year": fy, "exclusion_reason": reason,
                        "n_rows": n, "obligations_usd": round(v, 2),
                        "built_date": today})
    os.replace(part, path)
    return path, len(rows)


def print_stats(stats):
    """Name everything that was excluded. A silent counter is the bug."""
    print(f"  rows read                    {stats['rows_read']:>12,}")
    print(f"  aggregated                   {stats['rows_aggregated']:>12,}")
    for reason, (n, v) in sorted(excluded_by_reason(stats).items()):
        print(f"  excluded {reason:38} {n:>10,} rows  ${v:>18,.2f}")
    print(f"  every excluded (awardee_uei, awardee_name, fiscal_year, reason) "
          f"is written to {EXCLUDED_ROWS_FILE.name} - the identity, not just "
          f"the count")
    if stats["tier_other_than_A_or_B"]:
        for t, n in sorted(stats["tier_other_than_A_or_B"].items()):
            print(f"  !! confidence_tier {t!r}: {n:,} attributed row(s) - "
                  f"counted in obligations_usd but in NEITHER tier column")
    if stats["entities_missing_from_spine"]:
        miss = sorted(stats["entities_missing_from_spine"])
        print(f"  !! {len(miss):,} tribe_id(s) absent from the entity spine, "
              f"named: {', '.join(miss[:10])}"
              + (" ..." if len(miss) > 10 else ""))
    if stats["entities_missing_cedar_uid"]:
        miss = sorted(stats["entities_missing_cedar_uid"])
        print(f"  !! {len(miss):,} tribe_id(s) with NO cedar_uid, named: "
              f"{', '.join(miss[:10])}" + (" ..." if len(miss) > 10 else "")
              + "  -> re-run `py -3 code/503_identity.py stamp --apply`")
