#!/usr/bin/env python3
"""
Cedar Press - 900: NATURAL RESOURCES -> THE HUB. The C4 join, not a resolution.

    py -3 code/900_nr_hub_join.py                 # apply, in place, with backups
    py -3 code/900_nr_hub_join.py verify          # read-only, exit 1 on breach
    py -3 code/900_nr_hub_join.py verify --selftest
                                                  # prove verify fires, on a
                                                  # synthetic violation, then
                                                  # restore. Exits 1 if the
                                                  # guard did NOT fire.

WHAT THIS IS, AND WHAT IT DELIBERATELY IS NOT
---------------------------------------------
`natural-resources` was BLOCKED on C4: "only 25% of entity-bearing rows carry a
Cedar id". Three different things were hiding under that one number and only
one of them was work:

  1. 9,791 of 11,305 revenue rows are `national_aggregate`. Interior publishes
     Native American revenue ONLY in aggregate, by law. There is no entity on
     the row to carry an id. Scoring those as unkeyed measures the statute.
     That is `901_nr_record_scope.py`'s job (ADR-010), not this script's.
  2. Rows that DO carry a resolved entity in a ROLE-PREFIXED column
     (`recipient_entity_id`, `beneficiary_entity_id`, ...) that the C4 scanner
     could not see. That was a scanner blind spot; fixed in 518.
  3. **Rows that name a Cedar entity by its spine HANDLE and carry no
     `cedar_uid`.** That is a HUB JOIN and it is this script.

So: nothing here decides WHO an entity is. Every id written is an exact lookup
of an identifier the row already holds, in
`data/spine/cedar_identity_register.csv`, restricted to `register_status =
active`. Where a lookup is not exact and unambiguous the row keeps its blank
and the reason is written to `review/nr_hub_join_unresolved_<date>.csv`.
**Flag, never delete** - and never guess.

THE ONE PLACE THIS DOES MORE THAN LOOK UP AN ID
-----------------------------------------------
`anc_ceiling_roster.csv` and `ancsa_filings_index.csv` key entities in a
SOURCE-LOCAL scheme (`anc_id = ANC-<16 hex>`) that the hub has never adopted -
the exact ADR-009 defect: a spoke re-deriving identity locally. 19,465 rows,
invisible to the old C4 scanner because neither table has a column the scanner
recognised. Joining them needs a NAME match, so it is fenced:

  * candidates are restricted to `ANRC` / `ANVC` handles ONLY. A roster row is
    an ANCSA CORPORATION by construction (`parent_entity_class = ANC`), so a
    federally recognized village TRIBE (`AKNF`) is never a candidate. This is
    the village-tribe-vs-village-corp trap named in
    docs/NATIVE_ENTITY_NUANCES.md, and it is real here: 22 of 196 roster names
    match an AKNF handle and an ANVC handle both. Restricting the candidate
    set is what makes those 22 safe rather than a coin flip.
  * the comparison is on a normalised name, and the ONLY normalisations are
    typographic (curly apostrophe -> ASCII, diacritic folding, corporate-suffix
    and punctuation stripping). No token containment, no fuzzy distance, no
    "closest match". AGENTS.md forbids a containment matcher from keying a
    dollar and these rows are one join away from money.
  * a match must be EXACTLY ONE candidate. Zero -> unresolved. Two -> refused.

MONEY AND ROWS
--------------
This script writes identifier columns and nothing else. Row counts are
unchanged and every money column is unchanged to the cent; both are asserted,
per table, on every run and again by `verify` against
`docs/schema/nr_hub_join_census.json`.

ORDERING
--------
`900` writes ids. `901_nr_record_scope.py` writes `record_scope`. They touch
disjoint columns, but run 900 first: 901's `entity` / `unresolved` split reads
the ids this script writes.

Backs up every file it modifies as `<name>.bak_<date>_pre900`.
"""
from __future__ import annotations

import csv
import json
import re
import shutil
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()

CLEAN = ROOT / "data" / "clean"
REGISTER = ROOT / "data" / "spine" / "cedar_identity_register.csv"
CENSUS = ROOT / "docs" / "schema" / "nr_hub_join_census.json"
REVIEW = ROOT / "review" / f"nr_hub_join_unresolved_{TODAY}.csv"

BASIS_STEM = ("exact lookup in data/spine/cedar_identity_register.csv "
              "(register_status=active) by ")

# money columns asserted unchanged, per table
MONEY = {
    "resource_revenue.csv": ["amount_usd", "amount_usd_real2025"],
    "resource_assets.csv": [],
    "resource_parties.csv": [],
    "anc_ceiling_roster.csv": [],
    "ancsa_filings_index.csv": ["bytes"],
}

TYPO = str.maketrans({
    "’": "'", "‘": "'", "′": "'", "´": "'", "`": "'",
    "–": "-", "—": "-", "‐": "-", "‑": "-", " ": " ",
})
_SUFFIX = re.compile(r"\b(inc|incorporated|corp|corporation|company|co|the|ltd|llc)\b")


def norm_name(s: str) -> str:
    """Typographic normalisation only. Never semantic."""
    s = (s or "").translate(TYPO)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = s.lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = _SUFFIX.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def name_forms(n: str):
    """The three renderings a roster/issuer name is allowed to be tried as."""
    out = [("as_recorded", n)]
    m = re.search(r"\(([^)]*)\)", n or "")
    if m:
        out.append(("parenthetical_stripped", re.sub(r"\([^)]*\)", " ", n)))
        out.append(("parenthetical_content", m.group(1)))
    return out


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


def money_sum(rows, cols):
    out = {}
    for c in cols:
        t = Decimal(0)
        for r in rows:
            v = (r.get(c) or "").strip().replace(",", "").replace("$", "")
            if not v:
                continue
            try:
                t += Decimal(v)
            except Exception:
                pass
        out[c] = str(t)
    return out


def nz(r, c):
    return (r.get(c) or "").strip()


# ---------------------------------------------------------------- register
def load_register():
    reg, _ = read_csv(REGISTER)
    by_handle, by_uid, corp_name = {}, {}, defaultdict(set)
    for r in reg:
        if r.get("register_status") != "active":
            continue
        h, u = r["handle"].strip(), r["cedar_uid"].strip()
        if h:
            by_handle[h] = u
        if u:
            by_uid[u] = r
        if h.split("-")[0] in ("ANRC", "ANVC"):
            corp_name[norm_name(r.get("canonical_name"))].add(u)
    return by_handle, by_uid, corp_name


# ---------------------------------------------------------------- the joins
def plan(by_handle, by_uid, corp_name):
    """Return {table: (rows, cols_before, cols_after, stats, unresolved)}."""
    out = {}
    unresolved = []

    # -- 1/2. resource_revenue + resource_parties + nothing-else: handle -> uid
    for table, src_cols in (
        ("resource_revenue.csv", ["recipient_entity_id", "beneficiary_entity_id"]),
        ("resource_parties.csv", ["entity_id"]),
    ):
        p = CLEAN / table
        rows, before = read_csv(p)
        after = list(before)
        if "cedar_uid" not in after:
            after.append("cedar_uid")
        if "cedar_uid_basis" not in after:
            after.insert(after.index("cedar_uid") + 1, "cedar_uid_basis")
        st = Counter()
        for r in rows:
            r.setdefault("cedar_uid_basis", r.get("cedar_uid_basis") or "")
            if nz(r, "cedar_uid"):
                st["already_keyed"] += 1
                continue
            for c in src_cols:
                v = nz(r, c)
                if not v:
                    continue
                u = by_handle.get(v)
                if u:
                    r["cedar_uid"] = u
                    r["cedar_uid_basis"] = f"{BASIS_STEM}{c}={v}"
                    st["joined"] += 1
                    break
                # a value that is NOT a spine handle is not a Cedar entity.
                # PAYER-US-BIA / PAYER-STATE-ND are federal and state payer
                # stubs; they are correctly not in the hub and must never be
                # counted as entity attachment.
                st[f"not_a_spine_handle:{v.split('-')[0]}"] += 1
                unresolved.append(dict(
                    table=table, row_key=nz(r, "resource_revenue_event_id")
                    or nz(r, "party_link_id"), column=c, value=v,
                    reason="value is not an active handle in the identity "
                           "register; not a Cedar entity"))
            else:
                if not any(nz(r, c) for c in src_cols):
                    st["no_entity_named"] += 1
        out[table] = (rows, before, after, st)

    # -- 3. anc_ceiling_roster: local anc_id scheme -> hub, by fenced name match
    p = CLEAN / "anc_ceiling_roster.csv"
    ros, before = read_csv(p)
    after = list(before)
    for c in ("cedar_uid", "cedar_uid_basis", "entity_resolution_status"):
        if c not in after:
            after.append(c)
    st = Counter()
    anc_uid = {}
    for r in ros:
        got = None
        for basis, form in name_forms(r.get("corporation_name")):
            k = norm_name(form)
            if not k:
                continue
            c = corp_name.get(k)
            if c and len(c) == 1:
                got = (basis, next(iter(c)))
                break
            if c and len(c) > 1:
                got = ("AMBIGUOUS", sorted(c))
                break
        if got and got[0] != "AMBIGUOUS":
            r["cedar_uid"] = got[1]
            r["cedar_uid_basis"] = (
                f"{BASIS_STEM}corporation_name ({got[0]}), candidate set "
                f"restricted to ANRC/ANVC handles because parent_entity_class="
                f"{r.get('parent_entity_class','')} makes this row an ANCSA "
                f"corporation and never a village tribe")
            r["entity_resolution_status"] = "resolved"
            anc_uid[r["anc_id"]] = got[1]
            st[f"resolved:{got[0]}"] += 1
        else:
            r["cedar_uid"] = ""
            reason = ("two or more active ANRC/ANVC candidates - refused"
                      if got else
                      "no active ANRC/ANVC handle carries this name")
            r["cedar_uid_basis"] = ""
            r["entity_resolution_status"] = (
                "refused_ambiguous" if got else "unresolved")
            st["unresolved"] += 1
            unresolved.append(dict(
                table="anc_ceiling_roster.csv", row_key=r["anc_id"],
                column="corporation_name", value=r.get("corporation_name", ""),
                reason=reason))
    out["anc_ceiling_roster.csv"] = (ros, before, after, st)

    # -- 4. ancsa_filings_index: anc_id -> the roster's uid
    p = CLEAN / "ancsa_filings_index.csv"
    fi, before = read_csv(p)
    after = list(before)
    for c in ("cedar_uid", "cedar_uid_basis"):
        if c not in after:
            after.append(c)
    st = Counter()
    for r in fi:
        u = anc_uid.get(nz(r, "anc_id"))
        if u:
            r["cedar_uid"] = u
            r["cedar_uid_basis"] = (
                f"anc_id={r['anc_id']} resolved through "
                f"anc_ceiling_roster.csv, which 900 joined to the identity "
                f"register")
            st["joined"] += 1
        else:
            r["cedar_uid"] = ""
            r["cedar_uid_basis"] = ""
            st["unresolved"] += 1
    out["ancsa_filings_index.csv"] = (fi, before, after, st)

    # -- 5. resource_assets: through the PARTY TABLE, which is where
    #       attribution lives. One unambiguous `owner` party, or nothing.
    parties, _ = read_csv(CLEAN / "resource_parties.csv")
    owners = defaultdict(set)
    # `relationship`, not `party_role`, is the column that says "this Native
    # entity stands behind the object". `parent_native_entity` covers owner,
    # lessor and reserved_mineral_estate_holder; it deliberately excludes
    # `serves_native_entities` (a beneficiary among others is not an owner -
    # the Utah revitalization-fund ruling in docs/RESOURCE_LEDGER_BUILD_LOG.md
    # is explicit that writing a parent there would invent an ownership fact)
    # and `counterparty` (the lessee).
    for pr in parties:
        if (pr.get("object_type") != "asset"
                or pr.get("relationship") != "parent_native_entity"):
            continue
        u = by_handle.get(nz(pr, "entity_id")) or nz(pr, "cedar_uid")
        if u:
            owners[nz(pr, "object_id")].add(u)
    p = CLEAN / "resource_assets.csv"
    ra, before = read_csv(p)
    after = list(before)
    if "cedar_uid_basis" not in after:
        after.insert(after.index("cedar_uid") + 1
                     if "cedar_uid" in after else len(after), "cedar_uid_basis")
    st = Counter()
    for r in ra:
        if nz(r, "cedar_uid"):
            st["already_keyed"] += 1
            continue
        c = owners.get(nz(r, "resource_asset_id"), set())
        if len(c) == 1:
            r["cedar_uid"] = next(iter(c))
            r["cedar_uid_basis"] = (
                "single `owner` party for this asset in "
                "resource_parties.csv, hub-joined on its entity_id")
            st["joined_via_party_table"] += 1
        else:
            r["cedar_uid_basis"] = ""
            st["unresolved" if not c else "refused_multiple_parents"] += 1
            unresolved.append(dict(
                table="resource_assets.csv", row_key=nz(r, "resource_asset_id"),
                column="resource_parties.relationship=parent_native_entity",
                value="|".join(sorted(c)),
                reason="no single parent_native_entity party" if not c
                       else "more than one parent_native_entity party - refused"))
    out["resource_assets.csv"] = (ra, before, after, st)

    return out, unresolved


# ---------------------------------------------------------------- run
def main() -> int:
    args = sys.argv[1:]
    verify = bool(args) and args[0] == "verify"
    selftest = "--selftest" in args

    if selftest:
        return run_selftest()

    by_handle, by_uid, corp_name = load_register()
    print(f"  register: {len(by_handle):,} active handles, "
          f"{len(corp_name):,} distinct ANRC/ANVC normalised names")

    pre = {}
    for t in MONEY:
        rows, cols = read_csv(CLEAN / t)
        pre[t] = dict(rows=len(rows), cols=cols, money=money_sum(rows, MONEY[t]))

    built, unresolved = plan(by_handle, by_uid, corp_name)

    breaches = []
    census = {"generated": TODAY, "tables": {}}
    print()
    for t, (rows, before, after, st) in built.items():
        # --- conservation, proven per table -------------------------------
        if len(rows) != pre[t]["rows"]:
            breaches.append(f"{t}: ROW COUNT {pre[t]['rows']} -> {len(rows)}")
        m_after = money_sum(rows, MONEY[t])
        for c, v in pre[t]["money"].items():
            if m_after[c] != v:
                breaches.append(f"{t}: MONEY {c} {v} -> {m_after[c]}")
        lost = [c for c in before if c not in after]
        gained = [c for c in after if c not in before]
        if lost:
            breaches.append(f"{t}: COLUMNS LOST {lost}")

        keyed = sum(1 for r in rows if nz(r, "cedar_uid"))
        # --- every uid written must be an ACTIVE register uid -------------
        bad = {nz(r, "cedar_uid") for r in rows
               if nz(r, "cedar_uid") and nz(r, "cedar_uid") not in by_uid}
        if bad:
            breaches.append(f"{t}: {len(bad)} cedar_uid not active in the "
                            f"register: {sorted(bad)[:4]}")

        print(f"  {t:30s} rows {len(rows):6,}  cedar_uid {keyed:6,} "
              f"({100.0*keyed/len(rows) if rows else 0:5.1f}%)")
        print(f"  {'':30s} + {gained}  - {lost or 'none'}")
        for k, v in sorted(st.items()):
            print(f"  {'':32s}{k:36s} {v:7,}")
        census["tables"][t] = dict(rows=len(rows), cedar_uid=keyed,
                                   money=m_after, columns=after)

    if breaches:
        print("\n  !! INVARIANT BREACH")
        for b in breaches:
            print("     " + b)
        return 1

    if verify:
        if not CENSUS.exists():
            print(f"\n  no census at {CENSUS} - run without `verify` first")
            return 1
        old = json.loads(CENSUS.read_text(encoding="utf-8"))
        drift = []
        for t, c in old["tables"].items():
            live, _ = read_csv(CLEAN / t)
            n = len(live)
            k = sum(1 for r in live if nz(r, "cedar_uid"))
            if n != c["rows"]:
                drift.append(f"{t}: rows {c['rows']} -> {n}")
            if k < c["cedar_uid"]:
                drift.append(f"{t}: cedar_uid REGRESSED {c['cedar_uid']} -> {k}")
            m = money_sum(live, MONEY[t])
            for col, v in c["money"].items():
                if m.get(col) != v:
                    drift.append(f"{t}: money {col} {v} -> {m.get(col)}")
        if drift:
            print("\n  !! VERIFY FAILED")
            for d in drift:
                print("     " + d)
            return 1
        print("\n  verify OK - rows, money and hub coverage all hold")
        return 0

    # --- write --------------------------------------------------------
    for t, (rows, before, after, st) in built.items():
        p = CLEAN / t
        bak = p.with_name(p.name + f".bak_{TODAY}_pre900")
        if not bak.exists():          # never clobber the PRE state on a re-run
            shutil.copy2(p, bak)
        write_csv(p, rows, after)
    REVIEW.parent.mkdir(parents=True, exist_ok=True)
    with REVIEW.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["table", "row_key", "column",
                                           "value", "reason"])
        w.writeheader()
        w.writerows(unresolved)
    CENSUS.parent.mkdir(parents=True, exist_ok=True)
    CENSUS.write_text(json.dumps(census, indent=1), encoding="utf-8")
    print(f"\n  wrote 5 tables + {REVIEW.relative_to(ROOT)} "
          f"({len(unresolved):,} refusals, each with a reason)")
    print(f"  census -> {CENSUS.relative_to(ROOT)}")
    return 0


def run_selftest() -> int:
    """Prove `verify` fires. Corrupt one row, verify, restore, verify."""
    t = "resource_revenue.csv"
    p = CLEAN / t
    if not CENSUS.exists():
        print("  run 900 without `verify` first, then --selftest")
        return 1
    keep = p.read_bytes()
    try:
        rows, cols = read_csv(p)
        # violation 1: blank a cedar_uid the census counted
        hit = next((r for r in rows if nz(r, "cedar_uid")), None)
        if hit is None:
            print("  no keyed row to corrupt")
            return 1
        hit["cedar_uid"] = ""
        write_csv(p, rows, cols)
        rc = _verify_only()
        print(f"  synthetic violation A (one cedar_uid blanked): "
              f"verify exit={rc}  -> {'FIRED' if rc else 'DID NOT FIRE'}")
        if rc == 0:
            return 1
        # violation 2: change a money cell by one cent
        p.write_bytes(keep)
        rows, cols = read_csv(p)
        hit = next(r for r in rows if nz(r, "amount_usd"))
        hit["amount_usd"] = str(Decimal(hit["amount_usd"]) + Decimal("0.01"))
        write_csv(p, rows, cols)
        rc2 = _verify_only()
        print(f"  synthetic violation B (one cent added to amount_usd): "
              f"verify exit={rc2}  -> {'FIRED' if rc2 else 'DID NOT FIRE'}")
        if rc2 == 0:
            return 1
    finally:
        p.write_bytes(keep)
    rc3 = _verify_only()
    print(f"  restored: verify exit={rc3}  -> "
          f"{'clean' if rc3 == 0 else 'STILL FAILING'}")
    return 0 if rc3 == 0 else 1


def _verify_only() -> int:
    old = json.loads(CENSUS.read_text(encoding="utf-8"))
    for t, c in old["tables"].items():
        live, _ = read_csv(CLEAN / t)
        if len(live) != c["rows"]:
            return 1
        if sum(1 for r in live if nz(r, "cedar_uid")) < c["cedar_uid"]:
            return 1
        m = money_sum(live, MONEY[t])
        for col, v in c["money"].items():
            if m.get(col) != v:
                return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
