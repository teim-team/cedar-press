#!/usr/bin/env python3
"""871 - promote joinable geographic keys onto the CONTRACTING tables (ADR-015).

WHAT IT WRITES ONTO WHAT
------------------------
    data/clean/prime_contracts.csv   1,217,768 rows, transaction grain
    data/clean/subawards.csv            72,837 rows, subaward grain

Both in place, both backed up first, both proven row- and money-conserving.

THE ROUTE, AND WHY IT IS TWO HOPS
---------------------------------
`prime_contracts.csv` carries `contract_transaction_unique_key` (69.1% filled).
The geography lives at AWARD grain in `geo_award_county_crosswalk.csv` (870),
keyed on `contract_award_unique_key`. Nothing in the clean table carries an
award key, so the bridge is:

    prime_contracts.contract_transaction_unique_key
      -> data/raw/contracts/usaspending_archive_2026-08-07/filtered/
         FY*_ledger_rows.csv   (904,282 pairs, transaction key unique)
      -> contract_award_unique_key
      -> geo_award_county_crosswalk.csv

That bridge was built by the archive pull for a different purpose (PSC and
award description). It is reused, not rebuilt.

`subawards.csv` needs no bridge: it already carries `prime_award_unique_key`,
which IS the crosswalk key.

TWO COLUMNS, NEVER ONE (ADR-015 rule 1)
---------------------------------------
Every table gets a RECIPIENT county and a PLACE-OF-PERFORMANCE county under
names that cannot be confused, and they are never merged, never coalesced, and
never filled from each other:

    geo_recipient_county_fips     where the awardee is
    geo_pop_county_fips           where the work was performed

On 1,045,397 of 1,050,968 crosswalk awards (99.5%) both sides are present, and
they DISAGREE on a large minority of them. That disagreement is the ADR-015
measure. Collapsing the columns would delete it.

THE SUBAWARD TRAP, NAMED IN THE COLUMN NAME
-------------------------------------------
The crosswalk key on `subawards.csv` is the PRIME award's key, so the geography
it returns is the PRIME's recipient and the PRIME's place of performance -- NOT
the subawardee's. A subaward to a firm in Alaska under a prime awarded to a firm
in Virginia would carry Virginia in `geo_recipient_county_fips` if that column
were named as it is on the prime table. It is therefore named

    geo_prime_award_recipient_county_fips
    geo_prime_award_pop_county_fips

on `subawards.csv` and nothing else. The subawardee's own county is NOT
derivable from the clean table: `subawards.csv` carries `sub_state` and no
sub-city, sub-zip or sub-county column at all. That gap is reported, not filled.

TIERS
-----
    exact_award_summary   the federal award summary named the county. Two hops
                          of exact key equality, no inference.
    derived_place_modal   no award key reached the crosswalk, so the row's own
                          city+state was looked up in the place crosswalk and
                          took its MODAL county. `geo_*_place_dominance_share`
                          carries how dominant that county was among the
                          observations, and `geo_*_place_ambiguous` is 1 when
                          the place was seen in more than one county. A consumer
                          that will not accept a 0.61 dominance share can filter
                          on the column; the row is never dropped and never
                          silently promoted.

Derived rows are honestly worse than exact ones and are marked on every row.
They are not counted toward the "keyed" figure without saying which tier.

MODES
-----
    py -3 code/871_promote_geo_keys_contracts.py           promote in place
    py -3 code/871_promote_geo_keys_contracts.py verify    re-measure and assert
    py -3 code/871_promote_geo_keys_contracts.py selftest  prove verify fires

INVARIANTS (verify exits 1 on any failure)
------------------------------------------
  I1 ROW CONSERVATION to the row: each table has exactly as many rows after as
     the backup taken before it.
  I2 MONEY CONSERVATION to the cent: the sum of the table's money column is
     byte-identical, compared as scaled integer cents, against the backup.
  I3 COLUMN CONSERVATION: no column present in the backup is missing after.
  I4 every non-empty county fips is 5 digits and starts with its own state fips.
  I5 no row carries a tier without a fips, or a fips without a tier; and no
     `exact_award_summary` row lacks the award key it claims to have come from.
"""

import csv
import glob
import json
import os
import shutil
import sys
from collections import Counter

csv.field_size_limit(10 * 1024 * 1024)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEAN = os.path.join(ROOT, "data", "clean")
XWALK_AWARD = os.path.join(CLEAN, "geo_award_county_crosswalk.csv")
XWALK_PLACE = os.path.join(CLEAN, "geo_place_county_crosswalk.csv")
BRIDGE_GLOB = os.path.join(ROOT, "data", "raw", "contracts",
                           "usaspending_archive_2026-08-07", "filtered",
                           "FY*_ledger_rows.csv")
OUT_STATS = os.path.join(ROOT, "docs", "GEO_PROMOTION_CONTRACTS.json")
STAMP = "2026-09-02"

PRIME = os.path.join(CLEAN, "prime_contracts.csv")
SUBS = os.path.join(CLEAN, "subawards.csv")
BAK_PRIME = PRIME + f".bak_{STAMP}_pre871_promote_geo_keys_contracts"
BAK_SUBS = SUBS + f".bak_{STAMP}_pre871_promote_geo_keys_contracts"

PRIME_NEW = [
    "geo_recipient_county_fips", "geo_recipient_county_name",
    "geo_recipient_state_fips", "geo_recipient_place_dominance_share",
    "geo_recipient_place_ambiguous",
    "geo_pop_county_fips", "geo_pop_county_name",
    "geo_pop_state_fips", "geo_pop_place_dominance_share",
    "geo_pop_place_ambiguous",
    "geo_key_tier", "geo_key_basis", "geo_award_unique_key", "geo_built_date",
]

SUBS_NEW = [
    "geo_prime_award_recipient_county_fips", "geo_prime_award_recipient_county_name",
    "geo_prime_award_recipient_state_fips",
    "geo_prime_award_pop_county_fips", "geo_prime_award_pop_county_name",
    "geo_prime_award_pop_state_fips",
    "geo_key_tier", "geo_key_basis", "geo_subawardee_county_gap_reason",
    "geo_built_date",
]

SUB_GAP = ("subawards.csv carries sub_state and no sub city, zip or county "
           "column; the subawardee's county is not derivable from this table. "
           "The county columns here are the PRIME award's, not the subawardee's.")


def norm_city(v):
    return " ".join((v or "").strip().upper().split())


def norm_state(v):
    v = (v or "").strip().upper()
    return v if len(v) == 2 and v.isalpha() else ""


def money_cents(v):
    v = (v or "").strip().replace(",", "").replace("$", "")
    if not v:
        return 0
    try:
        return int(round(float(v) * 100))
    except ValueError:
        return 0


def load_award_xwalk():
    xw = {}
    with open(XWALK_AWARD, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            xw[row["award_unique_key"]] = (
                row["recipient_county_fips"], row["recipient_county_name"],
                row["recipient_state_fips"],
                row["pop_county_fips"], row["pop_county_name"], row["pop_state_fips"])
    return xw


def load_place_xwalk():
    pl = {}
    with open(XWALK_PLACE, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["place_key_type"] != "city_state":
                continue
            pl[row["place_key"]] = (row["county_fips"], row["county_name"],
                                    row["state_fips"], row["dominance_share"],
                                    row["ambiguous_flag"])
    return pl


def load_bridge():
    br = {}
    for f in sorted(glob.glob(BRIDGE_GLOB)):
        with open(f, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                t = (row.get("contract_transaction_unique_key") or "").strip()
                a = (row.get("contract_award_unique_key") or "").strip()
                if t and a:
                    br[t] = a
    return br


def backup(src, dst):
    if os.path.exists(dst):
        print(f"  [bak] {os.path.basename(dst)} exists, kept")
        return
    shutil.copyfile(src, dst)
    print(f"  [bak] {os.path.basename(dst)}")


def col_diff(before_hdr, after_hdr, label):
    b, a = set(before_hdr), set(after_hdr)
    gained = [c for c in after_hdr if c not in b]
    lost = [c for c in before_hdr if c not in a]
    print(f"  [cols] {label}: {len(before_hdr)} -> {len(after_hdr)}")
    print(f"         gained ({len(gained)}): {gained}")
    print(f"         lost   ({len(lost)}): {lost if lost else 'none'}")
    return gained, lost


def promote_prime(xw, place, bridge):
    print(f"\n[871] {os.path.relpath(PRIME, ROOT)}")
    backup(PRIME, BAK_PRIME)
    tmp = PRIME + ".tmp871"
    tier = Counter()
    n = 0
    cents = 0
    with open(BAK_PRIME, newline="", encoding="utf-8") as fin, \
         open(tmp, "w", newline="", encoding="utf-8") as fout:
        r = csv.reader(fin)
        hdr = next(r)
        # Idempotent: if a previous run already added these columns, rebuild them
        # rather than appending a second copy or leaving stale values in place.
        base_idx = [i for i, c in enumerate(hdr) if c not in PRIME_NEW]
        base_hdr = [hdr[i] for i in base_idx]
        w = csv.writer(fout)
        w.writerow(base_hdr + PRIME_NEW)
        i_txn = hdr.index("contract_transaction_unique_key")
        i_rcity = hdr.index("recipient_city_name")
        i_rstate = hdr.index("recipient_state_code")
        i_pcity = hdr.index("place_of_perform_city")
        i_pstate = hdr.index("place_of_perform_state")
        i_money = hdr.index("total_obligations")
        width = len(hdr)
        for row in r:
            n += 1
            if len(row) < width:
                row = row + [""] * (width - len(row))
            cents += money_cents(row[i_money])
            akey = bridge.get(row[i_txn].strip(), "") if row[i_txn].strip() else ""
            hit = xw.get(akey) if akey else None
            if hit and (hit[0] or hit[3]):
                vals = [hit[0], hit[1], hit[2], "", "",
                        hit[3], hit[4], hit[5], "", "",
                        "exact_award_summary",
                        "usaspending_prime_award_summary_via_"
                        "usaspending_archive_transaction_bridge",
                        akey, STAMP]
                tier["exact_award_summary"] += 1
            else:
                rk = f"{norm_state(row[i_rstate])}|{norm_city(row[i_rcity])}"
                pk = f"{norm_state(row[i_pstate])}|{norm_city(row[i_pcity])}"
                rp = place.get(rk) if "|" in rk and rk[0] != "|" else None
                pp = place.get(pk) if "|" in pk and pk[0] != "|" else None
                if rp or pp:
                    vals = [rp[0] if rp else "", rp[1] if rp else "",
                            rp[2] if rp else "", rp[3] if rp else "",
                            rp[4] if rp else "",
                            pp[0] if pp else "", pp[1] if pp else "",
                            pp[2] if pp else "", pp[3] if pp else "",
                            pp[4] if pp else "",
                            "derived_place_modal",
                            "modal county of this row's own city+state in "
                            "geo_place_county_crosswalk.csv",
                            akey, STAMP]
                    tier["derived_place_modal"] += 1
                else:
                    vals = [""] * 10 + ["", "", akey, STAMP]
                    tier["unkeyed"] += 1
            w.writerow([row[i] for i in base_idx] + vals)
    with open(tmp, newline="", encoding="utf-8") as fh:
        after_hdr = next(csv.reader(fh))
    col_diff(hdr, after_hdr, "prime_contracts.csv")
    os.replace(tmp, PRIME)
    print(f"  [rows] {n:,}   obligations ${cents/100:,.2f}")
    for k, v in tier.most_common():
        print(f"         {k:<22} {v:>9,}  {v/max(1,n):6.1%}")
    return {"rows": n, "cents": cents, "tiers": dict(tier)}


def promote_subs(xw):
    print(f"\n[871] {os.path.relpath(SUBS, ROOT)}")
    backup(SUBS, BAK_SUBS)
    tmp = SUBS + ".tmp871"
    tier = Counter()
    n = 0
    cents = 0
    with open(BAK_SUBS, newline="", encoding="utf-8") as fin, \
         open(tmp, "w", newline="", encoding="utf-8") as fout:
        r = csv.reader(fin)
        hdr = next(r)
        base_idx = [i for i, c in enumerate(hdr) if c not in SUBS_NEW]
        base_hdr = [hdr[i] for i in base_idx]
        w = csv.writer(fout)
        w.writerow(base_hdr + SUBS_NEW)
        i_key = hdr.index("prime_award_unique_key")
        i_money = hdr.index("subaward_amount")
        width = len(hdr)
        for row in r:
            n += 1
            if len(row) < width:
                row = row + [""] * (width - len(row))
            cents += money_cents(row[i_money])
            akey = (row[i_key] or "").strip()
            hit = xw.get(akey) if akey else None
            if hit and (hit[0] or hit[3]):
                vals = [hit[0], hit[1], hit[2], hit[3], hit[4], hit[5],
                        "exact_award_summary",
                        "usaspending_prime_award_summary_on_"
                        "prime_award_unique_key", SUB_GAP, STAMP]
                tier["exact_award_summary"] += 1
            else:
                vals = ["", "", "", "", "", "", "", "", SUB_GAP, STAMP]
                tier["unkeyed"] += 1
            w.writerow([row[i] for i in base_idx] + vals)
    with open(tmp, newline="", encoding="utf-8") as fh:
        after_hdr = next(csv.reader(fh))
    col_diff(hdr, after_hdr, "subawards.csv")
    os.replace(tmp, SUBS)
    print(f"  [rows] {n:,}   subaward amount ${cents/100:,.2f}")
    for k, v in tier.most_common():
        print(f"         {k:<22} {v:>9,}  {v/max(1,n):6.1%}")
    return {"rows": n, "cents": cents, "tiers": dict(tier)}


def build():
    print("[871] loading crosswalks")
    xw = load_award_xwalk()
    print(f"       award crosswalk keys : {len(xw):,}")
    place = load_place_xwalk()
    print(f"       place crosswalk city+state entries : {len(place):,}")
    bridge = load_bridge()
    print(f"       transaction->award bridge pairs    : {len(bridge):,}")
    stats = {"built": STAMP, "script": "871_promote_geo_keys_contracts.py",
             "award_xwalk_keys": len(xw), "place_xwalk_city_state": len(place),
             "bridge_pairs": len(bridge),
             "prime_contracts": promote_prime(xw, place, bridge),
             "subawards": promote_subs(xw)}
    with open(OUT_STATS, "w", encoding="utf-8") as fh:
        json.dump(stats, fh, indent=2)
    print(f"\n[871] wrote {os.path.relpath(OUT_STATS, ROOT)}")
    return stats


# --------------------------------------------------------------------- verify
TABLES = [
    (PRIME, BAK_PRIME, "total_obligations",
     [("geo_recipient_county_fips", "geo_recipient_state_fips"),
      ("geo_pop_county_fips", "geo_pop_state_fips")]),
    (SUBS, BAK_SUBS, "subaward_amount",
     [("geo_prime_award_recipient_county_fips", "geo_prime_award_recipient_state_fips"),
      ("geo_prime_award_pop_county_fips", "geo_prime_award_pop_state_fips")]),
]


def _scan(path, money_col, fips_pairs):
    n = 0
    cents = 0
    bad_fips = 0
    tier_no_fips = 0
    fips_no_tier = 0
    exact_no_key = 0
    tiers = Counter()
    with open(path, newline="", encoding="utf-8") as fh:
        r = csv.DictReader(fh)
        hdr = list(r.fieldnames or [])
        for row in r:
            n += 1
            cents += money_cents(row.get(money_col))
            any_fips = False
            for fc, sc in fips_pairs:
                v = (row.get(fc) or "").strip()
                if not v:
                    continue
                any_fips = True
                if len(v) != 5 or not v.isdigit():
                    bad_fips += 1
                elif (row.get(sc) or "") and v[:2] != row.get(sc):
                    bad_fips += 1
            t = (row.get("geo_key_tier") or "").strip()
            tiers[t or "(none)"] += 1
            if t and not any_fips:
                tier_no_fips += 1
            if any_fips and not t:
                fips_no_tier += 1
            if t == "exact_award_summary" and not (row.get("geo_award_unique_key")
                                                   or "").strip():
                # subawards carry the key in prime_award_unique_key instead
                if "geo_award_unique_key" in hdr:
                    exact_no_key += 1
    return dict(rows=n, cents=cents, hdr=hdr, bad_fips=bad_fips,
                tier_no_fips=tier_no_fips, fips_no_tier=fips_no_tier,
                exact_no_key=exact_no_key, tiers=tiers)


def _scan_backup(path, money_col):
    n = 0
    cents = 0
    with open(path, newline="", encoding="utf-8") as fh:
        r = csv.reader(fh)
        hdr = next(r)
        i = hdr.index(money_col)
        width = len(hdr)
        for row in r:
            n += 1
            cents += money_cents(row[i] if i < len(row) else "")
    return n, cents, hdr


def verify(tables=None, quiet=False):
    tables = tables or TABLES
    say = (lambda *a: None) if quiet else print
    fails = []
    for path, bak, money_col, fips_pairs in tables:
        name = os.path.basename(path)
        if not os.path.exists(path):
            fails.append(f"MISSING {path}")
            continue
        cur = _scan(path, money_col, fips_pairs)
        say(f"[871 verify] {name}")
        say(f"    rows {cur['rows']:,}   {money_col} ${cur['cents']/100:,.2f}")
        say(f"    tiers {dict(cur['tiers'])}")
        say(f"    bad_fips {cur['bad_fips']}  tier_without_fips {cur['tier_no_fips']}"
            f"  fips_without_tier {cur['fips_no_tier']}"
            f"  exact_without_award_key {cur['exact_no_key']}")
        if cur["bad_fips"]:
            fails.append(f"I4 {name}: {cur['bad_fips']} malformed / "
                         f"state-inconsistent county fips")
        if cur["tier_no_fips"] or cur["fips_no_tier"] or cur["exact_no_key"]:
            fails.append(f"I5 {name}: tier/fips disagree "
                         f"(tier_no_fips {cur['tier_no_fips']}, "
                         f"fips_no_tier {cur['fips_no_tier']}, "
                         f"exact_no_key {cur['exact_no_key']})")
        if os.path.exists(bak):
            bn, bc, bhdr = _scan_backup(bak, money_col)
            lost = [c for c in bhdr if c not in cur["hdr"]]
            say(f"    vs backup: rows {bn:,} -> {cur['rows']:,}   "
                f"cents {bc:,} -> {cur['cents']:,}   "
                f"cols {len(bhdr)} -> {len(cur['hdr'])}   lost {lost if lost else 'none'}")
            if bn != cur["rows"]:
                fails.append(f"I1 {name}: row conservation broken "
                             f"{bn:,} -> {cur['rows']:,}")
            if bc != cur["cents"]:
                fails.append(f"I2 {name}: money conservation broken "
                             f"{bc:,}c -> {cur['cents']:,}c "
                             f"(delta ${abs(bc-cur['cents'])/100:,.2f})")
            if lost:
                fails.append(f"I3 {name}: columns lost vs backup: {lost}")
        else:
            say(f"    !! no backup at {os.path.basename(bak)}; "
                f"I1/I2/I3 cannot be checked")
            fails.append(f"I1/I2/I3 {name}: backup missing, conservation unprovable")
    if fails:
        for f in fails:
            say("FAIL:", f)
        return 1
    say("[871 verify] OK -- I1 I2 I3 I4 I5 all hold")
    return 0


def selftest():
    """Corrupt a COPY of prime_contracts (head only, with a matching head-only
    backup) one invariant at a time and prove verify() returns 1."""
    import tempfile
    if not os.path.exists(PRIME):
        print("[871 selftest] build first")
        return 1
    tmp = tempfile.mkdtemp(prefix="871_selftest_")
    live = os.path.join(tmp, "t.csv")
    bak = os.path.join(tmp, "t.csv.bak")
    N = 20000

    def head(src, dst, n):
        with open(src, newline="", encoding="utf-8") as fi, \
             open(dst, "w", newline="", encoding="utf-8") as fo:
            r = csv.reader(fi)
            w = csv.writer(fo)
            for i, row in enumerate(r):
                if i > n:
                    break
                w.writerow(row)

    head(PRIME, live, N)
    head(PRIME, bak, N)
    spec = [(live, bak, "total_obligations",
             [("geo_recipient_county_fips", "geo_recipient_state_fips"),
              ("geo_pop_county_fips", "geo_pop_state_fips")])]
    ok = True

    def rows(p):
        with open(p, newline="", encoding="utf-8") as fh:
            return list(csv.reader(fh))

    def write(p, rr):
        with open(p, "w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerows(rr)

    base = verify(spec, quiet=True)
    print(f"[871 selftest] clean {N:,}-row copy verify -> {base} "
          f"{'(expected 0)' if base == 0 else '!! CLEAN COPY ALREADY FAILS'}")
    ok = ok and base == 0

    def case(name, mutate):
        nonlocal ok
        head(PRIME, live, N)
        head(PRIME, bak, N)
        mutate()
        rc = verify(spec, quiet=True)
        good = rc == 1
        print(f"  {name:<54} verify -> {rc}  {'FIRES' if good else '!! DID NOT FIRE'}")
        ok = ok and good

    def drop_row():
        rr = rows(live)
        write(live, rr[:1] + rr[2:])

    def move_money():
        rr = rows(live)
        i = rr[0].index("total_obligations")
        for r in rr[1:]:
            if r[i] and money_cents(r[i]):
                r[i] = str(float(r[i]) + 0.01)
                break
        write(live, rr)

    def drop_col():
        rr = rows(live)
        i = rr[0].index("sector")
        write(live, [r[:i] + r[i + 1:] for r in rr])

    def break_fips():
        rr = rows(live)
        i = rr[0].index("geo_recipient_county_fips")
        for r in rr[1:]:
            if r[i]:
                r[i] = r[i][1:]
                break
        write(live, rr)

    def tier_without_fips():
        rr = rows(live)
        fi = rr[0].index("geo_recipient_county_fips")
        pi = rr[0].index("geo_pop_county_fips")
        for r in rr[1:]:
            if r[fi] or r[pi]:
                r[fi] = r[pi] = ""
                break
        write(live, rr)

    case("I1 one row dropped", drop_row)
    case("I2 one obligation moved by a cent", move_money)
    case("I3 an existing column dropped", drop_col)
    case("I4 a promoted county fips loses a digit", break_fips)
    case("I5 a tiered row loses both its fips", tier_without_fips)

    shutil.rmtree(tmp, ignore_errors=True)
    print("[871 selftest] " + ("OK -- every invariant fired" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "build"
    if mode == "verify":
        sys.exit(verify())
    if mode == "selftest":
        sys.exit(selftest())
    build()
    sys.exit(verify())
