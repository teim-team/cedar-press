#!/usr/bin/env python3
"""
Cedar Press - 1179: an identifier that is KEYED in one table and UNKEYED in
another is a rule that exists and was not applied. Measure it, emit the
adjudicated subset as a ruling file 173 can consume, and GUARD it so it cannot
silently come back.

    py -3 code/1179_cross_table_key_consistency.py measure
    py -3 code/1179_cross_table_key_consistency.py emit
    py -3 code/1179_cross_table_key_consistency.py verify
    py -3 code/1179_cross_table_key_consistency.py selftest

WHY THIS EXISTS
---------------
Measured 2026-09-04 on the 2025-2026 federal funding window (`action_date`
calendar years 2025 and 2026): 2,315 distinct recipients, **1,255 carrying no
`cedar_uid` at all** - 45.8% of recipients keyed - while 227 of the unkeyed
carry over $1M each, $4,205,699,483 together. The owner's instruction that day
was *"everything should have a cedar id anyway"*.

`cedar_identifier_ledger_final.csv` already holds a settled identifier ->
`cedar_uid` ruling for a large share of them. **`173_consolidate_rulings_ledger.py`
cannot see those rulings**: the ledger is on its `PROPOSAL_ONLY` list
("the ledger IS a source table, not a ruling file"), so it is never a *subject*
discoverer - even though 173 already trusts the same ledger row as a **tier**
authority (its rung 3). A ruling that no consolidator can see is a ruling no
applier can apply. That asymmetry is the mechanism of the gap.

THE THING THIS SCRIPT REFUSES TO DO, AND WHY IT IS THE POINT
------------------------------------------------------------
**Not every unkeyed row is a gap. In the largest bucket the UNKEYED table is
right and the LEDGER is wrong.** Measured, funding side:

    cross_dataset_propagation:funding   50 ids   9,746 rows   $7,013,581,245

Every one of those ledger rows was *propagated out of the funding dataset
itself* ("Established in the funding dataset ... Propagated, not researched").
Feeding them back into funding is an instrument reading its own output -
`AGENT_FIELD_GUIDE.md` rule 10 - and the top of that bucket is the
place-name-coincidence defect verbatim:

    DTNMMPBN5715  SANTA CLARA CNTY HOUSING AUTH -> "Pueblo of Santa Clara"
                  20 rows keyed, 1,336 rows unkeyed, $4,528,275,378
    KZE9G2M4GRX9  SANTA ANA, CITY OF            -> "Pueblo of Santa Ana"
    MDWQNJL9HFJ8  BOISE CITY ADA HOUSING AUTH   -> "Bois Forte"
    NHZZNNWMW5G3  WINNEBAGO COUNTY HOUSING AUTH -> "Winnebago"
    ZKM3EN3P2173  MANCHESTER HOUSING AND REDEV  -> "Manchester"
    XFT7HSDNMFQ7  PEORIA HOUSING AUTH           -> "Peoria Tribe of Indians"

That is the same shape as the OMAHA HOUSING AUTHORITY denial the owner settled
on 2026-09-04, which cost $1,135,664,503 to withdraw. Mass-applying this bucket
would have re-created it six times over. So the gate here is the **method that
recorded the ruling**, not the existence of a key:

    ADJUDICATED  elijah_ruling, elijah_ruling_redirect, hand, bgov_manual,
                 web_verified, agent_research_two_leg, ladder_1117,
                 ladder_1122, fpds_uei_cage_bridge      -> emitted for 173
    PROPAGATED   cross_dataset_propagation:*            -> REFUSED, circular
    MACHINE      cluster_v3, sam_namematch_*, need_v6,
                 institution_exact_name, unmatched,
                 agent_research_one_leg                 -> REFUSED, proposal only

Nothing is deleted and nothing is hidden: every refused identifier is written
to the review CSV with the reason in `disposition`.

THE TIER IS INHERITED. `emit` copies `confidence_tier` off the ledger row and
names that row in `source_file` / `tier_rationale`. It never assigns one, and a
ledger row at tier C or X is not a positive ruling and is never emitted.

WHAT COUNTS AS "UNKEYED"
------------------------
Four row states, kept apart because they mean different things and only one of
them is a gap:

    KEYED_AGREES          the table's uid == the ledger's uid
    KEYED_DISAGREES       both present and DIFFERENT - a finding, never a fix
    UNKEYED_PLAIN         no uid, no exclusion, not out of scope  <-- the gap
    UNKEYED_BUT_EXCLUDED  excluded_flag=1 or tier X - a DECISION, not an absence
    UNKEYED_NOT_EVALUATED attribution_method starts `not_evaluated` - out of scope

UNMEASURED RATHER THAN CLEAN
----------------------------
`verify` raises rather than return a number it cannot measure: a missing
ledger, a ledger with zero tier-A/B rulings, or a missing consumer table all
exit 2 with UNMEASURED. An absence of evidence never prints as evidence of
absence (`AGENT_FIELD_GUIDE.md` rule 4).

SNAPSHOT. Concurrent rebuilds write `data/clean/` continuously; every figure
this script prints is a snapshot at its own run time and it prints that time.
"""

import csv
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

LEDGER_NAME = "cedar_identifier_ledger_final.csv"

# The named invariant this script's guard exists to defend. `verify` prints
# this literal when it fires; `selftest` asserts on this literal, so a rename
# of the check cannot silently pass the selftest.
INVARIANT = "IDENTIFIER_KEYED_IN_ONE_TABLE_AND_UNKEYED_IN_ANOTHER"

# ---------------------------------------------------------------------------
# Ruling-method authority. A tier is inherited; a METHOD decides whether the
# ruling may be applied at all.
# ---------------------------------------------------------------------------
ADJUDICATED = {
    "elijah_ruling", "elijah_ruling_redirect", "hand", "bgov_manual",
    "web_verified", "agent_research_two_leg", "ladder_1117", "ladder_1122",
    "fpds_uei_cage_bridge",
}
REFUSE_REASON = {
    "cross_dataset_propagation": (
        "CIRCULAR - this ledger row was propagated out of a Cedar dataset, not "
        "researched; applying it back is an instrument reading its own output"),
    "cluster_v3": "MACHINE CLUSTER - a name-cluster proposal, never a ruling",
    "sam_namematch": "MACHINE NAME MATCH - a name match is not a ruling",
    "need_v6": "need_v6 - 6.5% accurate, never publishes alone (START_HERE trap 1)",
    "institution_exact_name": "EXACT NAME MATCH - the exactness of the key says "
                              "nothing about the correctness of the link",
    "unmatched": "UNMATCHED - the ledger row records no link",
    "agent_research_one_leg": "ONE LEG - a single-leg agent finding; two legs or a "
                              "human before it moves a dollar",
}

# (table, id column, id kind, uid column, tier column, exclusion column,
#  amount column, display-name column)
CONSUMERS = [
    ("federal_funding_transactions.csv", "recipient_uei", "UEI", "cedar_uid",
     "confidence_tier", "excluded_flag", "obligated_usd", "recipient_name"),
    ("prime_contracts.csv", "awardee_uei", "UEI", "cedar_uid",
     "confidence_tier", None, "total_obligations", "awardee_name"),
    ("prime_contracts.csv", "cage_code", "CAGE", "cedar_uid",
     "confidence_tier", None, "total_obligations", "awardee_name"),
    ("subawards.csv", "sub_uei", "UEI", "sub_cedar_uid", "sub_native_tier",
     None, "subaward_amount", "sub_name"),
    ("faads_transactions_all_agencies.csv", "recipient_uei", "UEI", "cedar_uid",
     None, None, "obligated_usd", "recipient_name"),
    ("faads_transactions.csv", "recipient_uei", "UEI", "cedar_uid",
     None, None, "obligated_usd", "recipient_name"),
    ("fac_tribal_single_audits.csv", "auditee_uei", "UEI", "cedar_uid",
     "confidence_tier", None, None, "auditee_name"),
    ("np_orgs.csv", "EIN", "EIN", "cedar_uid", None, None, None, "name"),
    ("nonprofit_schedule_c_lobbying.csv", "ein", "EIN", "cedar_uid",
     None, None, None, None),
    ("gaming_employment_observations.csv", "ein", "EIN", "cedar_uid",
     None, None, None, None),
]

STATES = ("KEYED_AGREES", "KEYED_DISAGREES", "UNKEYED_PLAIN",
          "UNKEYED_BUT_EXCLUDED", "UNKEYED_NOT_EVALUATED")


def clean_dir(root):
    return Path(root) / "data" / "clean"


def review_dir(root):
    return Path(root) / "review"


def norm_id(kind, v):
    v = (v or "").strip().upper()
    if not v:
        return ""
    if kind == "EIN":
        v = v.replace("-", "").zfill(9)
        return v if v.isdigit() and len(v) == 9 and v != "0" * 9 else ""
    if kind == "UEI":
        return v if len(v) == 12 and v.isalnum() else ""
    if kind == "CAGE":
        return v if len(v) == 5 and v.isalnum() else ""
    return v


def method_disposition(method):
    """APPLY / REFUSE with a NAMED reason. Never `other`, never `unknown`."""
    m = (method or "").strip()
    if m in ADJUDICATED:
        return "APPLY_ADJUDICATED", "ruling recorded by an adjudicated method"
    for pref, why in REFUSE_REASON.items():
        if m.startswith(pref):
            return "REFUSED_" + pref.upper(), why
    return "REFUSED_METHOD_NOT_RECOGNISED", (
        "method %r is on no list here; a method this script has never seen may "
        "not carry a positive attribution by default" % m)


def load_rulings(root):
    """identifier -> the ledger's positive ruling. Raises if unmeasurable."""
    p = clean_dir(root) / LEDGER_NAME
    if not p.exists():
        raise RuntimeError("UNMEASURED: %s is absent" % p)
    rule, conflict, seen = {}, {}, 0
    with open(p, newline="", encoding="utf-8-sig", errors="replace") as f:
        rdr = csv.DictReader(f)
        need = ("identifier_type", "identifier", "confidence_tier",
                "cedar_uid", "attribution_method")
        missing = [c for c in need if c not in (rdr.fieldnames or [])]
        if missing:
            raise RuntimeError("UNMEASURED: %s has no %s column(s)" % (p.name, missing))
        for d in rdr:
            it = (d["identifier_type"] or "").strip().upper()
            if it not in ("UEI", "CAGE", "EIN"):
                continue
            iv = norm_id(it, d["identifier"])
            if not iv:
                continue
            seen += 1
            tier = (d["confidence_tier"] or "").strip().upper()
            uid = (d["cedar_uid"] or "").strip()
            if tier not in ("A", "B") or not uid:
                continue
            k = (it, iv)
            if k in rule and rule[k]["uid"] != uid:
                conflict[k] = sorted({rule[k]["uid"], uid})
            rule[k] = {
                "uid": uid,
                "tribe_id": (d.get("tribe_id") or "").strip(),
                "tier": tier,
                "method": (d["attribution_method"] or "").strip(),
                "name": (d.get("canonical_name") or "").strip(),
                "legal_name": (d.get("legal_business_name") or "").strip(),
                "entity_class": (d.get("entity_class") or "").strip(),
                "rationale": (d.get("tier_rationale") or "").strip(),
                "ledger_source": (d.get("source_file") or "").strip(),
                "exclusion_id": (d.get("exclusion_id") or "").strip(),
            }
    for k in conflict:
        rule.pop(k, None)          # two uids for one identifier apply NEITHER
    if not seen:
        raise RuntimeError("UNMEASURED: %s carries no UEI/CAGE/EIN rows" % p.name)
    if not rule:
        raise RuntimeError("UNMEASURED: %s carries no tier-A/B ruling with a "
                           "cedar_uid - the ruling set is empty, so a clean "
                           "result here would mean nothing" % p.name)
    return rule, conflict


def scan(root, rule, only=None):
    """consumer key -> {identifier -> {state: [rows, dollars]}}"""
    out, names, missing = {}, {}, []
    for (tbl, idc, kind, uidc, tierc, exclc, amtc, namec) in CONSUMERS:
        ckey = "%s|%s" % (tbl, idc)
        if only and ckey not in only:
            continue
        p = clean_dir(root) / tbl
        if not p.exists():
            missing.append(tbl)
            continue
        per = defaultdict(lambda: defaultdict(lambda: [0, 0.0]))
        with open(p, newline="", encoding="utf-8", errors="replace") as f:
            rdr = csv.DictReader(f)
            hdr = rdr.fieldnames or []
            if idc not in hdr or uidc not in hdr:
                missing.append("%s (no %s/%s column)" % (tbl, idc, uidc))
                continue
            tc = tierc if tierc in hdr else None
            ec = exclc if exclc in hdr else None
            ac = amtc if amtc in hdr else None
            nc = namec if namec in hdr else None
            for d in rdr:
                iv = norm_id(kind, d.get(idc))
                if not iv:
                    continue
                k = (kind, iv)
                r = rule.get(k)
                if r is None:
                    continue
                uid = (d.get(uidc) or "").strip()
                if uid:
                    st = "KEYED_AGREES" if uid == r["uid"] else "KEYED_DISAGREES"
                else:
                    tier = (d.get(tc) or "").strip().upper() if tc else ""
                    ex = (d.get(ec) or "").strip() if ec else ""
                    if ex == "1" or tier == "X":
                        st = "UNKEYED_BUT_EXCLUDED"
                    elif (d.get("attribution_method") or "").startswith("not_evaluated"):
                        st = "UNKEYED_NOT_EVALUATED"
                    else:
                        st = "UNKEYED_PLAIN"
                amt = 0.0
                if ac:
                    try:
                        amt = float(d.get(ac) or 0)
                    except ValueError:
                        amt = 0.0
                per[k][st][0] += 1
                per[k][st][1] += amt
                if nc and k not in names:
                    v = (d.get(nc) or "").strip()
                    if v:
                        names[k] = v
        out[ckey] = per
    return out, names, missing


# ---------------------------------------------------------------------------
# measure
# ---------------------------------------------------------------------------

def measure(root, write=True):
    stamp = datetime.now().isoformat(timespec="seconds")
    rule, conflict = load_rulings(root)
    print("SNAPSHOT %s - data/clean is written by concurrent rebuilds; every "
          "figure below is a single run." % stamp)
    print("ledger rulings at tier A/B carrying a cedar_uid : %d" % len(rule))
    print("identifiers dropped for two uids in the ledger  : %d  (apply NEITHER)"
          % len(conflict))
    for k, v in sorted(conflict.items())[:10]:
        print("    %s|%s -> %s" % (k[0], k[1], " vs ".join(v)))

    per_tbl, names, missing = scan(root, rule)
    if missing:
        print("  tables absent or without the expected columns: %s" % missing)

    recs = []
    grand = Counter()
    for ckey, per in per_tbl.items():
        agg_n, agg_d, agg_i = Counter(), Counter(), defaultdict(set)
        for k, st in per.items():
            for s, (n, a) in st.items():
                agg_n[s] += n
                agg_d[s] += a
                agg_i[s].add(k)
        print("\n[%s]" % ckey)
        for s in STATES:
            if agg_n[s]:
                print("   %-22s %9d rows  $%17.0f  %5d identifiers"
                      % (s, agg_n[s], agg_d[s], len(agg_i[s])))
        # per-identifier disposition rows for the gap and the contradictions
        for k, st in per.items():
            gap_n, gap_d = st.get("UNKEYED_PLAIN", [0, 0.0])
            dis_n, dis_d = st.get("KEYED_DISAGREES", [0, 0.0])
            if not gap_n and not dis_n:
                continue
            r = rule[k]
            disp, why = method_disposition(r["method"])
            if dis_n and not gap_n:
                disp, why = "CONTRADICTION_KEYED_DISAGREES", (
                    "the table's uid and the ledger's uid are both present and "
                    "DIFFERENT - neither side is overwritten here")
            recs.append({
                "consumer": ckey,
                "identifier_type": k[0],
                "identifier": k[1],
                "table_name": names.get(k, ""),
                "ledger_cedar_uid": r["uid"],
                "ledger_tribe_id": r["tribe_id"],
                "ledger_canonical_name": r["name"],
                "ledger_entity_class": r["entity_class"],
                "ledger_confidence_tier": r["tier"],
                "ledger_attribution_method": r["method"],
                "ledger_source_file": r["ledger_source"],
                "ledger_exclusion_id": r["exclusion_id"],
                "rows_unkeyed_plain": gap_n,
                "usd_unkeyed_plain": round(gap_d, 2),
                "rows_keyed_agrees": st.get("KEYED_AGREES", [0, 0.0])[0],
                "rows_keyed_disagrees": dis_n,
                "usd_keyed_disagrees": round(dis_d, 2),
                "rows_unkeyed_but_excluded": st.get("UNKEYED_BUT_EXCLUDED", [0, 0.0])[0],
                "rows_unkeyed_not_evaluated": st.get("UNKEYED_NOT_EVALUATED", [0, 0.0])[0],
                "disposition": disp,
                "disposition_reason": why,
                "ledger_tier_rationale": r["rationale"][:300],
                "measured_at": stamp,
            })
            grand[disp] += 1
            grand[disp + "|rows"] += gap_n
            grand[disp + "|usd"] += gap_d

    print("\n--- the gap, by disposition (identifiers / rows / dollars) ---")
    for d in sorted({k for k in grand if "|" not in k}):
        print("  %-34s %5d ids  %8d rows  $%17.0f"
              % (d, grand[d], grand[d + "|rows"], grand[d + "|usd"]))
    print("\n  ONE WORKED ROW, so the number can be checked by hand:")
    apply_recs = [r for r in recs if r["disposition"] == "APPLY_ADJUDICATED"]
    for r in sorted(apply_recs, key=lambda r: -r["usd_unkeyed_plain"])[:1]:
        for kk in ("consumer", "identifier", "table_name", "ledger_cedar_uid",
                   "ledger_canonical_name", "ledger_confidence_tier",
                   "ledger_attribution_method", "rows_unkeyed_plain",
                   "usd_unkeyed_plain", "rows_keyed_agrees"):
            print("    %-28s %s" % (kk, r[kk]))

    if write and recs:
        dest = review_dir(root) / ("1179_cross_table_key_gap_%s.csv" % TODAY)
        dest.parent.mkdir(parents=True, exist_ok=True)
        recs.sort(key=lambda r: (-r["usd_unkeyed_plain"], r["consumer"]))
        with open(str(dest) + ".part", "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(recs[0]))
            w.writeheader()
            w.writerows(recs)
        os.replace(str(dest) + ".part", dest)
        print("\n  wrote %s (%d rows)" % (dest.name, len(recs)))
    return recs


# ---------------------------------------------------------------------------
# emit - a ruling file 173 discovers, carrying the INHERITED tier
# ---------------------------------------------------------------------------

def emit(root):
    recs = measure(root, write=True)
    keep = [r for r in recs if r["disposition"] == "APPLY_ADJUDICATED"
            and r["rows_unkeyed_plain"] > 0]
    by_id = {}
    for r in keep:
        k = (r["identifier_type"], r["identifier"])
        e = by_id.setdefault(k, dict(r, consumers=[], rows_total=0, usd_total=0.0))
        e["consumers"].append(r["consumer"])
        e["rows_total"] += r["rows_unkeyed_plain"]
        e["usd_total"] += r["usd_unkeyed_plain"]
    # 173 resolves an ENTITY verdict by TRIBE_ID_RE literal first and only then
    # by name, so a spine-shaped tribe_id is written in front of the name:
    # `tribe_id_literal` is exact where the name resolver is a match. A
    # `CEDAR-ENT-*` id is NOT spine-shaped and is deliberately left as a bare
    # name - those 62 subjects are the ledger's "individually Native-owned"
    # rulings, which state in their own tier_rationale that they carry no
    # ownership edge to any tribe, ANC or NHO.
    import re as _re
    SPINE_ID = _re.compile(r"^(TRBF|TRBS|AKNF|ANRC|ANVC|CNSF|CNSS|SGVF|NHO|TCU|"
                           r"CDFI|BIE|UIO|ITO|NP|NAFI|UNK)[-_][A-Z0-9]+", _re.I)
    out = []
    for (it, iv), e in sorted(by_id.items(), key=lambda kv: -kv[1]["usd_total"]):
        tid = e["ledger_tribe_id"]
        nm = e["ledger_canonical_name"] or e["ledger_cedar_uid"]
        ruling = ("%s %s" % (tid, nm)).strip() if SPINE_ID.match(tid or "") else nm
        out.append({
            # columns 173's `subject_of` and `discover` read
            "identifier_type": it,
            "identifier": iv,
            "ruling": ruling,
            "tribe_id": e["ledger_tribe_id"],
            "canonical_name": e["ledger_canonical_name"],
            "cedar_uid": e["ledger_cedar_uid"],
            # THE TIER IS INHERITED - copied off the ledger row, never assigned
            "confidence_tier": e["ledger_confidence_tier"],
            "tier": e["ledger_confidence_tier"],
            "attribution_method": e["ledger_attribution_method"],
            "ruled_date": TODAY,
            "source_file": "%s :: %s row for %s %s" % (
                LEDGER_NAME, e["ledger_attribution_method"], it, iv),
            "tier_rationale": e["ledger_tier_rationale"],
            "entity_class": e["ledger_entity_class"],
            "unapplied_in": " | ".join(sorted(set(e["consumers"]))),
            "unapplied_rows": e["rows_total"],
            "unapplied_usd": round(e["usd_total"], 2),
            "emitted_by": "code/1179_cross_table_key_consistency.py emit",
        })
    dest = review_dir(root) / ("cedar_ledger_key_rulings_%s.csv" % TODAY)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not out:
        print("\nemit: nothing in the ADJUDICATED class - no file written")
        return []
    with open(str(dest) + ".part", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    os.replace(str(dest) + ".part", dest)
    print("\nemit: wrote %s" % dest.name)
    print("  identifiers          : %d" % len(out))
    print("  rows they would key  : %d" % sum(r["unapplied_rows"] for r in out))
    print("  dollars behind them  : $%.0f" % sum(r["unapplied_usd"] for r in out))
    print("  tiers, INHERITED     : %s"
          % dict(Counter(r["confidence_tier"] for r in out)))
    print("  methods              : %s"
          % dict(Counter(r["attribution_method"] for r in out)))
    print("\n  next: py -3 code/173_consolidate_rulings_ledger.py --check")
    print("        py -3 code/174_apply_rulings_to_source_tables.py --check")
    return out


# ---------------------------------------------------------------------------
# verify - the guard
# ---------------------------------------------------------------------------

BASELINE = "_1179_cross_table_key_baseline.json"


def verify(root, record=False, only=None, quiet=False):
    """Exit 1 while an identifier is keyed in one table and unkeyed in another.

    Counts ONLY the class this repo has agreed is a defect: an adjudicated
    ledger ruling at tier A/B with a cedar_uid, against a row in a consumer
    table that carries no uid, no exclusion and no out-of-scope marker.
    """
    stamp = datetime.now().isoformat(timespec="seconds")
    rule, _ = load_rulings(root)
    per_tbl, names, missing = scan(root, rule, only=only)
    if missing:
        raise RuntimeError("UNMEASURED: consumer table(s) absent or reshaped: %s"
                           % missing)
    if not per_tbl:
        raise RuntimeError("UNMEASURED: no consumer table was scanned")

    viol = []
    for ckey, per in per_tbl.items():
        for k, st in per.items():
            n, a = st.get("UNKEYED_PLAIN", [0, 0.0])
            if not n:
                continue
            disp, _why = method_disposition(rule[k]["method"])
            if disp != "APPLY_ADJUDICATED":
                continue
            viol.append((ckey, k, n, a, rule[k], names.get(k, "")))
    viol.sort(key=lambda v: -v[3])

    ids = len({v[1] for v in viol})
    rows = sum(v[2] for v in viol)
    usd = sum(v[3] for v in viol)
    if not quiet:
        print("SNAPSHOT %s" % stamp)
        print("%s" % INVARIANT)
        print("  ruling set (tier A/B + cedar_uid, adjudicated method) : %d"
              % sum(1 for k in rule
                    if method_disposition(rule[k]["method"])[0] == "APPLY_ADJUDICATED"))
        print("  identifiers in breach : %d" % ids)
        print("  rows in breach        : %d" % rows)
        print("  dollars behind them   : $%.0f" % usd)
        for ckey, k, n, a, r, nm in viol[:15]:
            print("    %-46s %s|%s %-34s %6d rows $%15.0f -> %s (%s, tier %s)"
                  % (ckey, k[0], k[1], nm[:34], n, a, r["uid"], r["method"], r["tier"]))
        if len(viol) > 15:
            print("    ... %d more" % (len(viol) - 15))

    bl_path = clean_dir(root) / BASELINE
    if record:
        bl_path.write_text(json.dumps(
            {"invariant": INVARIANT, "identifiers": ids, "rows": rows,
             "usd": round(usd, 2), "recorded_at": stamp}, indent=1),
            encoding="utf-8")
        print("  recorded baseline -> %s" % bl_path.name)
        return 0

    if viol:
        if not quiet:
            print("\nFAIL %s : %d identifiers / %d rows / $%.0f are settled in "
                  "%s and unkeyed in a table that reads them."
                  % (INVARIANT, ids, rows, usd, LEDGER_NAME))
        return 1
    if not quiet:
        print("\nPASS %s : no adjudicated ledger ruling is unapplied in a "
              "consumer table." % INVARIANT)
    return 0


# ---------------------------------------------------------------------------
# selftest - plant the violation, prove the NAMED detector fires
# ---------------------------------------------------------------------------

def _fixture(tmp, planted):
    """A minimal tree: one ledger ruling, one consumer table."""
    cd = clean_dir(tmp)
    cd.mkdir(parents=True, exist_ok=True)
    (Path(tmp) / "review").mkdir(parents=True, exist_ok=True)
    with open(cd / LEDGER_NAME, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "identifier_type", "identifier", "tribe_id", "canonical_name",
            "legal_business_name", "entity_class", "attribution_method",
            "confidence_tier", "tier_rationale", "is_authority", "exclusion_id",
            "source_file", "cedar_uid"])
        w.writeheader()
        # an ADJUDICATED ruling - the class the guard defends
        w.writerow({"identifier_type": "UEI", "identifier": "AAAAAAAAAAAA",
                    "tribe_id": "TRBF-TEST01-00", "canonical_name": "Fixture Nation",
                    "legal_business_name": "FIXTURE NATION", "entity_class": "Federally recognized tribe",
                    "attribution_method": "elijah_ruling", "confidence_tier": "A",
                    "tier_rationale": "fixture", "is_authority": "YES",
                    "exclusion_id": "", "source_file": "fixture", "cedar_uid": "CE-FIXT1-AA"})
        # a PROPAGATED ruling - must NEVER be counted as a breach
        w.writerow({"identifier_type": "UEI", "identifier": "BBBBBBBBBBBB",
                    "tribe_id": "TRBF-TEST02-00", "canonical_name": "Propagated Pueblo",
                    "legal_business_name": "SOMEWHERE COUNTY HOUSING AUTH", "entity_class": "",
                    "attribution_method": "cross_dataset_propagation:funding",
                    "confidence_tier": "B", "tier_rationale": "propagated",
                    "is_authority": "", "exclusion_id": "", "source_file": "funding",
                    "cedar_uid": "CE-FIXT2-BB"})
        # tier C - not a positive ruling, must never enter the ruling set
        w.writerow({"identifier_type": "UEI", "identifier": "CCCCCCCCCCCC",
                    "tribe_id": "", "canonical_name": "", "legal_business_name": "",
                    "entity_class": "", "attribution_method": "elijah_ruling",
                    "confidence_tier": "C", "tier_rationale": "", "is_authority": "",
                    "exclusion_id": "", "source_file": "fixture", "cedar_uid": ""})

    hdr = ["recipient_uei", "recipient_name", "obligated_usd", "cedar_uid",
           "confidence_tier", "excluded_flag", "attribution_method", "action_date"]
    rows = [
        # the ADJUDICATED subject, KEYED - never a breach
        dict(recipient_uei="AAAAAAAAAAAA", recipient_name="FIXTURE NATION",
             obligated_usd="100", cedar_uid="CE-FIXT1-AA", confidence_tier="A",
             excluded_flag="0", attribution_method="ruling_applied", action_date="2025-01-01"),
        # the ADJUDICATED subject, EXCLUDED - a DECISION, never a breach
        dict(recipient_uei="AAAAAAAAAAAA", recipient_name="FIXTURE NATION",
             obligated_usd="200", cedar_uid="", confidence_tier="X",
             excluded_flag="1", attribution_method="ledger_exclusion", action_date="2025-01-02"),
        # the ADJUDICATED subject, OUT OF SCOPE - never a breach
        dict(recipient_uei="AAAAAAAAAAAA", recipient_name="FIXTURE NATION",
             obligated_usd="300", cedar_uid="", confidence_tier="C",
             excluded_flag="0", attribution_method="not_evaluated:fixture",
             action_date="2025-01-03"),
        # the PROPAGATED subject, unkeyed and plain - REFUSED, never a breach
        dict(recipient_uei="BBBBBBBBBBBB", recipient_name="SOMEWHERE COUNTY HOUSING AUTH",
             obligated_usd="9999999", cedar_uid="", confidence_tier="",
             excluded_flag="0", attribution_method="", action_date="2025-01-04"),
        # the tier-C subject, unkeyed and plain - not a ruling, never a breach
        dict(recipient_uei="CCCCCCCCCCCC", recipient_name="TIER C CO",
             obligated_usd="500", cedar_uid="", confidence_tier="",
             excluded_flag="0", attribution_method="", action_date="2025-01-05"),
    ]
    if planted:
        # THE VIOLATION: adjudicated tier-A ruling, row unkeyed, unexcluded,
        # in scope. This and only this must make the named detector fire.
        rows.append(dict(recipient_uei="AAAAAAAAAAAA", recipient_name="FIXTURE NATION",
                         obligated_usd="4242.42", cedar_uid="", confidence_tier="",
                         excluded_flag="0", attribution_method="", action_date="2025-01-06"))
    with open(cd / "federal_funding_transactions.csv", "w", encoding="utf-8",
              newline="") as f:
        w = csv.DictWriter(f, fieldnames=hdr)
        w.writeheader()
        w.writerows(rows)
    return "federal_funding_transactions.csv|recipient_uei"


def selftest():
    import io
    import tempfile
    import contextlib
    ok = True
    only = None

    def run(tmp, planted):
        nonlocal only
        only = {_fixture(tmp, planted)}
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = verify(tmp, only=only)
        return rc, buf.getvalue()

    with tempfile.TemporaryDirectory() as tmp:
        rc, out = run(tmp, planted=False)
        print("1. clean fixture (keyed / excluded / out-of-scope / propagated / "
              "tier C only)")
        print("     exit %d, expected 0" % rc)
        if rc != 0:
            ok = False
            print("     FAIL - the guard fires on rows that are NOT the defect")
            print(out)
        if "PASS %s" % INVARIANT not in out:
            ok = False
            print("     FAIL - the PASS line does not name %s" % INVARIANT)

    with tempfile.TemporaryDirectory() as tmp:
        rc, out = run(tmp, planted=True)
        print("2. one planted violation: UEI AAAAAAAAAAAA, tier A elijah_ruling, "
              "cedar_uid CE-FIXT1-AA, one funding row unkeyed / unexcluded / in "
              "scope, $4,242.42")
        print("     exit %d, expected 1" % rc)
        if rc != 1:
            ok = False
            print("     FAIL - the guard did NOT fire on the planted violation")
            print(out)
        if "FAIL %s" % INVARIANT not in out:
            ok = False
            print("     FAIL - it went red without naming %s" % INVARIANT)
        if "AAAAAAAAAAAA" not in out:
            ok = False
            print("     FAIL - it did not name the identifier it fired on")
        if "4242" not in out.replace(",", ""):
            ok = False
            print("     FAIL - it did not carry the planted dollars ($4,242.42); "
                  "a detector that fires without the amount cannot be checked")
        if "identifiers in breach : 1" not in out:
            ok = False
            print("     FAIL - it did not count exactly ONE identifier in breach; "
                  "the propagated and tier-C subjects must not be counted")
        if "BBBBBBBBBBBB" in out or "CCCCCCCCCCCC" in out:
            ok = False
            print("     FAIL - a REFUSED-method or tier-C subject was counted as "
                  "a breach")

    # UNMEASURED rather than clean
    with tempfile.TemporaryDirectory() as tmp:
        clean_dir(tmp).mkdir(parents=True, exist_ok=True)
        print("3. absent ledger")
        try:
            verify(tmp, only={"federal_funding_transactions.csv|recipient_uei"})
            ok = False
            print("     FAIL - returned a number with no ledger to measure against")
        except RuntimeError as e:
            print("     raised UNMEASURED: %s" % str(e)[:70])

    with tempfile.TemporaryDirectory() as tmp:
        _fixture(tmp, planted=True)
        (clean_dir(tmp) / "federal_funding_transactions.csv").unlink()
        print("4. absent consumer table")
        try:
            verify(tmp, only={"federal_funding_transactions.csv|recipient_uei"})
            ok = False
            print("     FAIL - a missing table read as CLEAN")
        except RuntimeError as e:
            print("     raised UNMEASURED: %s" % str(e)[:70])

    print("\nselftest %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "measure"
    if cmd == "measure":
        measure(CEDAR)
        return 0
    if cmd == "emit":
        emit(CEDAR)
        return 0
    if cmd == "verify":
        return verify(CEDAR, record="--baseline" in sys.argv)
    if cmd == "selftest":
        return selftest()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
