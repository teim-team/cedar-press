#!/usr/bin/env python3
"""
1096_navajo_unexclude_and_harvest.py -- Cedar Press, GAMING-DEEP.

APPLIES the TERMS-SCOPE ruling (docs/PUBLICATION_POLICY.md,
`<!-- BEGIN TERMS-SCOPE -->`, 2026-09-02) to the eight Navajo hosts that
`code/980_gaming_web_harvest.py` refused, and re-runs 980 against the seven the
ruling reopens.

WHAT WAS WRONG
--------------
One host, `navajoeconomy.org/business-regulatory/`, is recorded
TERMS_STATED_RESTRICTIVE. 980 turned that into a nation-wide exclusion three
different ways at once - a tribe id, a name token `"navajo"`, and eleven host
suffixes - and the eight Navajo targets in `data/staging/gaming_web_harvest/
targets.csv` were all written `terms_restricted = Y` and never requested:

    www.firerockcasino.com          Fire Rock Casino
    www.flowingwatercasino.com      Flowing Water Casino
    www.navajogaming.com            Navajo Nation Gaming Enterprise
    www.northernedgecasino.com      Northern Edge Casino
    www.navajo-nsn.gov              Navajo Nation government
    tax.navajo-nsn.gov              Navajo Tax Commission
    www.nnooc.org                   Navajo Nation Oil and Gas
    navajoeconomy.org               <- the one that actually stated terms

**A name token cannot express a host-scoped restriction.** `"navajo"` in
RESTRICTED_NAME_TOKENS matched the nation, so no host of theirs could ever be
reached whatever its own terms said. That is the mechanism, and it is the
reason the ruling calls over-exclusion a defect rather than caution.

WHAT THIS PASS DID, PER HOST, WITH ITS OWN EVIDENCE
----------------------------------------------------
Each of the seven was checked on its own before anything was reopened -
robots.txt with our own UA (a 403/404 is ALLOWED, per PULL_DISCIPLINE.md), and
the homepage read for restrictive language:

    firerockcasino.com          robots 200, 0 Disallow, no terms language  OPEN
    flowingwatercasino.com      robots 200, 0 Disallow, no terms language  OPEN
    navajogaming.com            robots 200, 0 Disallow, no terms language  OPEN
    northernedgecasino.com      robots 200, 0 Disallow, no terms language  OPEN
    nnooc.org                   robots 404 (= allowed), no terms language  OPEN
    www.navajo-nsn.gov          robots 200, 16 Disallow (all admin paths)  METHOD-RESTRICTED
    tax.navajo-nsn.gov          same robots, same Terms of Use            METHOD-RESTRICTED

**A THIRD STATE WAS NEEDED AND IS NOW RECORDED.** navajo-nsn.gov/Terms was
read, not assumed, and it says:

    "You may not obtain or attempt to obtain any materials or information
     through any means not intentionally made available or provided for
     through the Navajo Nation Web Sites."

That restricts the ROUTE, not the content. A homepage the site publishes is
intentionally made available; an unlinked `/wp-json/` index or a sitemap walk
is exactly what it describes. Cedar had only two states - excluded by every
route, or open - and having only two is what produced the over-exclusion in the
first place. `980.METHOD_RESTRICTED_HOSTS` is the middle state: the homepage is
fetched, the hidden-endpoint enumeration and the sitemap/WP-REST page walk are
refused, and the refusal is written into `host_probe.jsonl` as
`REFUSED_METHOD_RESTRICTED_BY_STATED_TERMS` carrying the verbatim clause.

`navajoeconomy.org` stays excluded and is not touched.

WHY THE STALE PROBE RECORDS HAVE TO GO FIRST
---------------------------------------------
980's resume logic builds `done` from `host_probe.jsonl`, and the seven hosts
each already carry a `(host, "ALL")` record whose status is
`EXCLUDED_TERMS_STATED_RESTRICTIVE`. A resume would treat that as work already
finished and skip the host silently - **a refusal cached as a completion**.
This script MOVES those records to a dated sidecar rather than deleting them:
the refusal happened, and the record of it is the evidence that the correction
was needed. Flag, never delete.

USAGE
    py -3 code/1096_navajo_unexclude_and_harvest.py plan
    py -3 code/1096_navajo_unexclude_and_harvest.py unblock   # constants + files
    py -3 code/1096_navajo_unexclude_and_harvest.py verify
Then, in order:
    py -3 code/980_gaming_web_harvest.py probe
    py -3 code/980_gaming_web_harvest.py pages
    py -3 code/980_gaming_web_harvest.py build
    py -3 code/980_gaming_web_harvest.py verify
    py -3 code/1094_merge_web_harvest_into_gaming_claims.py merge   # ENRICHER LAST
"""
import argparse
import csv
import io
import json
import shutil
import sys
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parents[1]
STG = CEDAR / "data" / "staging" / "gaming_web_harvest"
TARGETS = STG / "targets.csv"
PROBE = STG / "host_probe.jsonl"
LOGS = CEDAR / "logs"
TODAY = date.today().isoformat()
TAG = "pre_1096_navajo_unexclude_and_harvest"
SELF = "code/1096_navajo_unexclude_and_harvest.py"
REPORT = LOGS / "1096_navajo_unexclude_report.json"

sys.path.insert(0, str(CEDAR / "code"))

# The one host whose OWN terms were read and are restrictive. Never reopened.
STAYS_EXCLUDED = {"navajoeconomy.org"}

# The seven the ruling reopens, with the evidence recorded for each.
REOPEN = {
    "www.firerockcasino.com": "robots.txt 200, 0 Disallow directives; homepage carries no reproduction, republication or automated-access clause [checked 2026-09-02]",
    "www.flowingwatercasino.com": "robots.txt 200, 0 Disallow directives; homepage carries no reproduction, republication or automated-access clause [checked 2026-09-02]",
    "www.navajogaming.com": "robots.txt 200, 0 Disallow directives; homepage carries no reproduction, republication or automated-access clause [checked 2026-09-02]",
    "www.northernedgecasino.com": "robots.txt 200, 0 Disallow directives; homepage carries no reproduction, republication or automated-access clause [checked 2026-09-02]",
    "www.nnooc.org": "robots.txt 404 - and a 404 on robots is ALLOWED, not blocked (PULL_DISCIPLINE.md: 22 phantom blocks came from reading a non-200 as disallow_all); homepage carries no restrictive clause [checked 2026-09-02]",
    "www.navajo-nsn.gov": "METHOD-RESTRICTED. robots.txt 200, 16 Disallow directives, all admin/infrastructure paths. navajo-nsn.gov/Terms restricts the ROUTE: \"You may not obtain or attempt to obtain any materials or information through any means not intentionally made available or provided for through the Navajo Nation Web Sites.\" Homepage only [read 2026-09-02]",
    "tax.navajo-nsn.gov": "METHOD-RESTRICTED. Same robots.txt and the same Navajo Nation Terms of Use as the apex. Homepage only [read 2026-09-02]",
}
METHOD_ONLY = {"www.navajo-nsn.gov", "tax.navajo-nsn.gov"}


def load_980():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "m980", CEDAR / "code" / "980_gaming_web_harvest.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def check_constants(m):
    """The constants must ALREADY be corrected. This script does not edit code;
    it refuses to unblock the data files against a code state that would just
    re-refuse the host on the next run."""
    bad = []
    if "TRBF-NAVAJO-00" in m.RESTRICTED_TRIBE_IDS:
        bad.append("RESTRICTED_TRIBE_IDS still holds TRBF-NAVAJO-00")
    if "navajo" in m.RESTRICTED_NAME_TOKENS:
        bad.append("RESTRICTED_NAME_TOKENS still holds 'navajo' - a NAME token "
                   "cannot express a host-scoped restriction")
    for h in REOPEN:
        if m.is_restricted_host(h):
            bad.append(f"{h} is still matched by RESTRICTED_HOST_SUFFIXES")
    for h in STAYS_EXCLUDED:
        if not m.is_restricted_host(h):
            bad.append(f"{h} is NO LONGER excluded and it must be - its own "
                       f"terms are restrictive")
    for h in METHOD_ONLY:
        if not m.method_restriction(h):
            bad.append(f"{h} carries no METHOD_RESTRICTED_HOSTS clause")
    for h in REOPEN:
        if h not in METHOD_ONLY and m.method_restriction(h):
            bad.append(f"{h} is method-restricted and should not be")
    return bad


def unblock(dry):
    m = load_980()
    bad = check_constants(m)
    if bad:
        raise RuntimeError("980's constants are not in the post-ruling state:\n  "
                           + "\n  ".join(bad))

    # ---- targets.csv: terms_restricted Y -> N on the seven -----------------
    with open(TARGETS, encoding="utf-8-sig", newline="") as fh:
        rdr = csv.DictReader(fh)
        rows = [dict(r) for r in rdr]
        fields = list(rdr.fieldnames)
    n_before = len(rows)
    flipped = []
    for r in rows:
        if r["host"] in REOPEN and r["terms_restricted"] == "Y":
            r["terms_restricted"] = "N"
            flipped.append(r["host"])
    still = [r["host"] for r in rows
             if r["host"] in STAYS_EXCLUDED and r["terms_restricted"] == "Y"]
    if len(rows) != n_before:
        raise RuntimeError("row conservation failed on targets.csv")

    # ---- host_probe.jsonl: MOVE the cached refusals to a sidecar -----------
    kept, moved = [], []
    for line in io.open(PROBE, encoding="utf-8"):
        try:
            rec = json.loads(line)
        except ValueError:
            kept.append(line)
            continue
        if (rec.get("host") in REOPEN
                and str(rec.get("http_status", "")).startswith("EXCLUDED_TERMS")):
            rec["_retired_by"] = SELF
            rec["_retired_date"] = TODAY
            rec["_retired_reason"] = (
                "the exclusion was inherited from navajoeconomy.org and the "
                "TERMS-SCOPE ruling voids it. The refusal is kept here because "
                "it is the evidence the correction was needed.")
            moved.append(rec)
        else:
            kept.append(line)
    if len(kept) + len(moved) != sum(1 for _ in io.open(PROBE, encoding="utf-8")):
        raise RuntimeError("line conservation failed on host_probe.jsonl")

    if not dry:
        b = TARGETS.with_name(f"{TARGETS.name}.bak_{TODAY}_{TAG}")
        if not b.exists():
            shutil.copy2(TARGETS, b)
        tmp = TARGETS.with_suffix(".csv.part")
        with open(tmp, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        tmp.replace(TARGETS)

        pb = PROBE.with_name(f"{PROBE.name}.bak_{TODAY}_{TAG}")
        if not pb.exists():
            shutil.copy2(PROBE, pb)
        side = STG / f"host_probe_retired_navajo_exclusions_{TODAY}.jsonl"
        with io.open(side, "w", encoding="utf-8", newline="") as fh:
            for rec in moved:
                fh.write(json.dumps(rec) + "\n")
        tmp = PROBE.with_suffix(".jsonl.part")
        with io.open(tmp, "w", encoding="utf-8", newline="") as fh:
            fh.writelines(kept)
        tmp.replace(PROBE)

    rep = {
        "built_by": SELF, "built_date": TODAY, "dry_run": dry,
        "ruling": "docs/PUBLICATION_POLICY.md <!-- BEGIN TERMS-SCOPE --> 2026-09-02",
        "hosts_reopened": len(flipped), "hosts_reopened_list": sorted(flipped),
        "hosts_still_excluded": sorted(still),
        "method_restricted": sorted(METHOD_ONLY),
        "per_host_evidence": REOPEN,
        "targets_rows": n_before,
        "cached_refusals_retired": len(moved),
        "probe_lines_kept": len(kept),
        "why_the_refusals_had_to_move": (
            "980 builds its resume set from host_probe.jsonl. A cached "
            "EXCLUDED_TERMS_STATED_RESTRICTIVE record reads as work already "
            "finished, so a re-run would skip the host and print nothing. A "
            "refusal cached as a completion is invisible."),
    }
    if not dry:
        LOGS.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    return rep


def verify():
    fails = []
    m = load_980()
    fails += check_constants(m)

    t = {r["host"]: r for r in csv.DictReader(
        io.open(TARGETS, encoding="utf-8-sig"))}
    for h in REOPEN:
        if h not in t:
            fails.append(f"V1 {h} is not in targets.csv")
        elif t[h]["terms_restricted"] != "N":
            fails.append(f"V1 {h} is still terms_restricted=Y in targets.csv")
    for h in STAYS_EXCLUDED:
        if h in t and t[h]["terms_restricted"] != "Y":
            fails.append(f"V2 {h} MUST stay terms_restricted=Y - its own terms "
                         f"are restrictive and the ruling does not reopen it")

    stale = 0
    for line in io.open(PROBE, encoding="utf-8"):
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if (rec.get("host") in REOPEN
                and str(rec.get("http_status", "")).startswith("EXCLUDED_TERMS")):
            stale += 1
    if stale:
        fails.append(f"V3 {stale} cached EXCLUDED_TERMS probe records remain "
                     f"for reopened hosts - a resume will skip them silently")

    # V4 -- the eight hard-listed sources are untouched by this pass.
    for h in ("colvilletribes.com", "yakama.com", "ctuir.org", "chickasaw.net",
              "nana.com", "southernute-nsn.gov", "fcpotawatomi.com",
              "stillaguamish.com", "navajoeconomy.org"):
        if not m.is_restricted_host(h):
            fails.append(f"V4 hard-listed source {h} is no longer excluded")

    print(f"  reopened: {len(REOPEN)}   still excluded: {len(STAYS_EXCLUDED)}   "
          f"method-restricted: {len(METHOD_ONLY)}")
    if fails:
        print("\n  VERIFY FAILED")
        for f in fails:
            print("   -", f)
        return 1
    print("  VERIFY OK - 4 invariants")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["plan", "unblock", "verify"])
    a = ap.parse_args()
    if a.stage in ("plan", "unblock"):
        print(json.dumps(unblock(dry=(a.stage == "plan")), indent=2))
        return 0
    return verify()


if __name__ == "__main__":
    sys.exit(main())
