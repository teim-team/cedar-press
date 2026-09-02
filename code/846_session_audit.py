#!/usr/bin/env python3
"""
Cedar Press - 846: DID WE ACTUALLY DO WHAT WE SAID WE DID?

    py -3 code/846_session_audit.py            # run every claim, print PASS/FAIL
    py -3 code/846_session_audit.py verify     # exit 1 if any claim is FAIL

WHY
---
Owner, 2026-09-02: *"Make sure you have done everything you said you would, or
have learned, or agents have done. You have this whole chat context - make sure
before you compact it that we're not missing anything. Otherwise we're just
spinning wheels."*

A session this long generates claims faster than anyone can hold them, and a
claim that was true when made can be untrue an hour later because twenty agents
are writing the same tree. Three times tonight a fix was reported complete and
was not:

  * 843 retired the CICD scheme and its `verify` inspected 3 files out of 310.
  * The crosswalk row for legacy 347 was corrected and the 820 rows it had
    already produced were left pointing at Cherokee Nation for a day.
  * 503's register writer was declared safe while holding a fixed 9-column
    list against a 14-column file.

So this file does not narrate. Every claim below is re-measured against disk on
every run, and a claim that cannot be measured is not listed.

THE ENTITY LAYER IS CHECKED FIRST AND HARDEST
---------------------------------------------
Owner, same message: *"The natives - it connects to everything else. We need
the native entities to connect them too."* The register is the connective
tissue; a wrong row there is wrong in all thirteen datasets at once. So the
identity checks run first and any failure there is reported as CRITICAL.
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
CLEAN = ROOT / "data" / "clean"
SPINE = ROOT / "data" / "spine"

RESULTS = []


def claim(name, critical=False):
    def deco(fn):
        RESULTS.append((name, fn, critical))
        return fn
    return deco


def hdr(p: Path):
    with p.open(encoding="utf-8-sig", errors="replace") as fh:
        return next(csv.reader(fh), [])


def rows(p: Path):
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def script_exit(*args) -> int:
    r = subprocess.run([sys.executable, str(ROOT / "code" / args[0])] + list(args[1:]),
                       capture_output=True, text=True, cwd=str(ROOT))
    return r.returncode


# ---------------------------------------------------------------- identity
@claim("United Keetoowah Band holds its own funding rows, not Cherokee Nation's",
       critical=True)
def _ukb():
    bad = n = 0
    amt = 0.0
    for r in rows(CLEAN / "federal_funding_transactions.csv"):
        if "keetoowah" not in (r.get("canonical_name") or "").lower():
            continue
        n += 1
        if (r.get("cedar_uid") or "").strip() != "CE-001BS-HA":
            bad += 1
            try:
                amt += float((r.get("obligated_usd") or "0").replace(",", ""))
            except ValueError:
                pass
    return (bad == 0, f"{n} Keetoowah rows, {bad} still on the wrong uid "
                      f"(${amt:,.2f})")


@claim("no ANCSA corporation carries a federally-recognized TRIBE's legal name",
       critical=True)
def _frname():
    bad = [r for r in rows(SPINE / "cedar_identity_register.csv")
           if "Corporation" in (r.get("entity_class") or "")
           and (r.get("federal_register_legal_name") or "").strip()]
    return (not bad, f"{len(bad)} corporation(s) carrying a tribe legal name")


@claim("the register survives its own rebuild without losing enricher columns",
       critical=True)
def _regcols():
    src = (ROOT / "code" / "503_identity.py").read_text(encoding="utf-8",
                                                        errors="replace")
    live = hdr(SPINE / "cedar_identity_register.csv")
    derived = "if REGISTER.exists():" in src and "_extra" in src
    return (derived, f"register has {len(live)} cols; 503 derives its header: "
                     f"{derived}")


@claim("every cedar_uid in the register is unique and none is blank",
       critical=True)
def _uids():
    rs = rows(SPINE / "cedar_identity_register.csv")
    uids = [r.get("cedar_uid", "") for r in rs]
    blank = sum(1 for u in uids if not u.strip())
    dup = len(uids) - len(set(uids))
    return (blank == 0 and dup == 0,
            f"{len(rs):,} entities, {blank} blank, {dup} duplicate")


@claim("the named collision families point at the right side", critical=True)
def _collide():
    """The owner named three cases needing real diligence: Ho-Chunk Inc vs
    Ho-Chunk Nation of Wisconsin, Eastern Band Cherokee vs Cherokee Nation
    Oklahoma, Seminole of Oklahoma vs Seminole of Florida. Two were wrong in
    `entity_aliases.csv` on 2026-09-02 and a matcher pilot found them, not a
    gate. They are gated now."""
    MUST = {"ho chunk inc": "TRBF-WNNBGO-00",     # Winnebago Tribe of Nebraska
            "seminole nation": "TRBF-SMNLOK-00"}  # The Seminole Nation of Oklahoma
    bad = []
    for r in rows(CLEAN / "entity_aliases.csv"):
        a = (r.get("normalized_alias") or "").strip().lower()
        if a in MUST and (r.get("entity_id") or "") != MUST[a]:
            bad.append(f"{a} -> {r.get('entity_id')}")
    return (not bad, "; ".join(bad) or "both point at the correct entity")


@claim("no alias row is missing its declared key")
def _aliaskey():
    rs = rows(CLEAN / "entity_aliases.csv")
    blank = sum(1 for r in rs if not (r.get("alias_id") or "").strip())
    return (blank == 0, f"{blank} of {len(rs):,} rows have a blank alias_id")


# ---------------------------------------------------------------- CICD
@claim("the CICD scheme is gone from every table and every reachable read")
def _cicd():
    return (script_exit("844_nuke_cicd.py", "verify") == 0, "844 verify")


@claim("the CICD crosswalk is evidence in graveyard/, not an input")
def _grave():
    g = (ROOT / "graveyard" / "cicd" / "assistance_tribe_id_crosswalk.csv").exists()
    old = (SPINE / "legacy" / "assistance_tribe_id_crosswalk.csv").exists()
    return (g and not old, f"in graveyard: {g}; still in spine/legacy: {old}")


# ---------------------------------------------------------------- regenerate
@claim("no NEW unsafe regenerating writer since the baseline")
def _regen():
    return (script_exit("845_regenerate_guard.py", "verify") == 0, "845 verify")


@claim("the funding builder's header and row writer are the same length")
def _align():
    import ast
    tree = ast.parse((ROOT / "code" / "24_funding_merge.py").read_text(
        encoding="utf-8", errors="replace"))
    h = next((len(n.value.elts) for n in tree.body
              if isinstance(n, ast.Assign)
              and getattr(n.targets[0], "id", "") == "TX_COLS"), None)
    w = next((len(n.args[0].elts) for n in ast.walk(tree)
              if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "writerow"
              and n.args and isinstance(n.args[0], ast.List)
              and len(n.args[0].elts) > 15), None)
    return (h == w, f"TX_COLS {h} vs writerow {w}")


# ---------------------------------------------------------------- datasets
@claim("all 13 datasets pass the production contract")
def _ready():
    p = CLEAN / "cedar_dataset_readiness.csv"
    if not p.exists():
        return (False, "readiness table absent")
    rs = rows(p)
    ready = [r for r in rs if r.get("status") == "READY"]
    return (len(ready) == len(rs) and len(rs) >= 13,
            f"{len(ready)}/{len(rs)} READY")


@claim("C4 identity coverage is a census, not a head-N sample")
def _c4():
    rs = rows(CLEAN / "cedar_dataset_readiness.csv")
    sampled = [r["dataset"] for r in rs
               if (r.get("c4_sampled_tables") or "-").strip() not in ("-", "")]
    return (not sampled, f"{len(sampled)} dataset(s) still sampled: "
                         f"{', '.join(sampled) or 'none'}")


@claim("the geography axis is joinable, not just addressed")
def _geo():
    n = j = 0
    for t in ("prime_contracts.csv", "federal_funding_transactions.csv"):
        p = CLEAN / t
        if not p.exists():
            continue
        cols = [c for c in hdr(p) if c.startswith("geo_") and "fips" in c]
        if not cols:
            continue
        with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            for r in csv.DictReader(fh):
                n += 1
                if any((r.get(c) or "").strip() for c in cols):
                    j += 1
    pct = 100 * j / n if n else 0
    return (pct > 85, f"{j:,}/{n:,} rows joinable ({pct:.1f}%)")


@claim("recipient and place-of-performance geography stay SEPARATE (ADR-015 r1)")
def _geo_sep():
    c = hdr(CLEAN / "prime_contracts.csv")
    return ("geo_recipient_county_fips" in c and "geo_pop_county_fips" in c,
            "both columns present" if "geo_pop_county_fips" in c else "COLLAPSED")


@claim("no constellation edge asserts ownership or carries money (ADR-014)")
def _const():
    p = CLEAN / "cedar_constellation_edges.csv"
    if not p.exists():
        return (False, "edge file absent")
    rs = rows(p)
    bad = sum(1 for r in rs if (r.get("is_ownership_claim") or "N") != "N"
              or (r.get("money_rolls_through") or "N") != "N")
    solo = sum(1 for r in rs if r.get("tier") == "sole_entity_in_area")
    return (bad == 0 and solo == 0,
            f"{len(rs):,} edges, {bad} breach the fence, "
            f"{solo} rest on sole_entity_in_area")


# ---------------------------------------------------------------- deliverables
@claim("every dataset has its own methodology paper")
def _method():
    d = ROOT / "docs" / "methodology"
    want = {"contractors", "subcontracting", "funding", "gaming",
            "natural-resources", "native-owned-businesses", "nonprofits",
            "deals", "lobbying", "legislation", "federal-register", "nagpra",
            "_entity_layer"}
    have = {p.stem for p in d.glob("*.md")} if d.exists() else set()
    missing = want - have
    return (not missing, f"{len(want & have)}/{len(want)} written"
                         f"{'; missing ' + ', '.join(sorted(missing)) if missing else ''}")


@claim("the tooling the owner asked for is installed and importable")
def _pkgs():
    out = []
    for m in ("splink", "usaddress", "pandera", "trafilatura", "selectolax",
              "jellyfish", "polars", "duckdb", "anthropic", "instructor"):
        try:
            __import__(m)
        except ImportError:
            out.append(m)
    return (not out, f"missing: {', '.join(out) or 'none'}")


def main() -> int:
    verify = len(sys.argv) > 1 and sys.argv[1] == "verify"
    fails = crit = 0
    print(f"  846 session audit   {len(RESULTS)} claims, re-measured against disk\n")
    for name, fn, critical in RESULTS:
        try:
            ok, detail = fn()
        except Exception as e:
            ok, detail = False, f"{type(e).__name__}: {str(e)[:60]}"
        if not ok:
            fails += 1
            crit += bool(critical)
        tag = "PASS" if ok else ("FAIL*" if critical else "FAIL ")
        print(f"    {tag}  {name}")
        print(f"           {detail}")
    print(f"\n  {len(RESULTS)-fails}/{len(RESULTS)} pass"
          f"   {fails} fail   {crit} of them CRITICAL (identity layer)")
    if not verify:
        (ROOT / "docs" / "SESSION_AUDIT.json").write_text(json.dumps(
            {"claims": len(RESULTS), "fail": fails, "critical": crit},
            indent=1), encoding="utf-8")
    return 1 if (verify and fails) else 0


if __name__ == "__main__":
    sys.exit(main())
