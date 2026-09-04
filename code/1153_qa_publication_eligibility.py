#!/usr/bin/env python3
"""
Cedar Press - 1153: the CP-002 / CP-022 publication-eligibility audit.

    py -3 code/1153_qa_publication_eligibility.py            # report
    py -3 code/1153_qa_publication_eligibility.py build      # write the ledgers
    py -3 code/1153_qa_publication_eligibility.py verify     # FAIL if unlanded

WHY THIS EXISTS
---------------
The 2026-09-02 QA review logged 151 findings and `1152` reconciled them. Two
CONFIRMED classes were the same underlying defect - *the export publishes rows
the pipeline already knows are unsafe* - and this file is their fix's evidence.

  CP-002  blocked adjudication states reaching customers.
  CP-022/031/033  build lineage - the script or local file that MADE the row -
          shipped in the customer file as if it were provenance.

The RULES live in `code/cedar_publication.py`, beside `row_ok()` and
`publishable_columns()`, which is what CP-002 asked for: one shared,
deny-by-default policy applied before export rather than each builder deciding
for itself. This file MEASURES them - what the policy withholds, what it masks,
what it drops as a column, and what it deliberately leaves alone.

THREE THINGS THIS FILE ASSERTS, AND WHY EACH IS NOT THE OBVIOUS ANSWER
-----------------------------------------------------------------------
1. **A blocked state is not one thing and does not get one answer.** A
   superseded LDA filing was really filed and is real history; a subaward filed
   to SAM 93 times is one subaward; an unadjudicated Native/not-Native call is
   not a finding yet. So the policy has four dispositions - PUBLISH, FLAG,
   MASK, WITHHOLD - and `docs/PUBLICATION_ELIGIBILITY.md` carries the judgement
   for every value of every state column, with its live count.

2. **A contract whose ownership ruling was withdrawn is still a real federal
   award.** Dropping it would delete public record to hide a Cedar mistake.
   MASK keeps the row and blanks the attribution, and leaves the state column
   in place so the file SAYS why the owner is absent.

3. **`_basis` is not a lineage suffix and a value scan is the wrong detector.**
   `natural-resources.record_scope_basis` quotes Interior's aggregate-release
   rule verbatim with the URL beside it; `contractors.geo_key_basis` names the
   crosswalk the county came from. Both contain a filename. Both are the best
   provenance in the product. So the column drop is BY NAME, enumerated, and
   this file's second ledger is the list of columns that MIX evidence and
   plumbing in one value - reported as a data problem, never dropped.

THE ONE NUMBER THE RECONCILIATION GOT WRONG, AND A SECOND ONE
--------------------------------------------------------------
`1152` reported the export as "43-311 columns" against the review's "29-81" and
read that as narrowing. It is not: `gaming` ships 311 columns and only the
100-row previews in `dist/preview/` are narrow. Corrected in this run.

And `1152.check_blocked_states()` reads `cap=5000` rows per file, so every
blocked-state count it printed is a count of the first 5,000 rows. Measured
here on the whole file, `lobbying.is_superseded = 1` is 1,064 rows, not 211;
`subcontracting.duplicate_status = superseded_by_primary_source` is 846, not
38; `contractors.owner_attribution_status = CONTRADICTED_AS_OF` is 9,223, not
8. Same defect class as the width claim: a partial scan reported as a
population.
"""
from __future__ import annotations

import csv
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))
csv.field_size_limit(10_000_000)

from cedar_publication import (          # noqa: E402
    BLOCKED_STATES, BLOCKED_COMBINATIONS,
    MASK_COLS, MASK_FLAGS, LINEAGE_COLS, LINEAGE_SUFFIXES,
    PUBLISH, FLAG, MASK, WITHHOLD,
    is_lineage_column, is_publication_eligible, lobbying_warning,
)

TODAY = date.today().isoformat()
CUST = ROOT / "dist" / "customer"
PREVIEW = ROOT / "dist" / "preview"
OUT_STATES = ROOT / "review" / f"1153_adjudication_states_{TODAY}.csv"
OUT_MIXED = ROOT / "review" / f"1153_mixed_provenance_columns_{TODAY}.csv"
DOC = ROOT / "docs" / "PUBLICATION_ELIGIBILITY.md"

# A value that names a script or a local file. Used ONLY to report, never to
# drop - see the module docstring, point 3. `https://.../edgar/data/...` is
# stripped before the local-path test because `data/` inside a URL is not a
# local path, and that false positive is what made an earlier value scan
# report `deals.Source_1` as leaking when it holds SEC filing URLs.
_B = chr(92)
SCRIPT_RE = re.compile(r"\b(?:code[/" + _B + _B + r"])?\d{2,4}_[A-Za-z0-9_]+\.py\b"
                       r"|\.py\b", re.I)
URL_RE = re.compile(r"https?://\S+", re.I)
LOCAL_RE = re.compile(r"\b(?:data|review|dist|graveyard)[/" + _B + _B + r"]"
                      r"|[A-Za-z]:" + _B + _B +
                      r"|[/~]Desktop[/" + _B + _B + r"]"
                      r"|\.zip\b|\.dta\b", re.I)


def files():
    return [p for p in sorted(CUST.glob("*.csv")) if p.name != "MANIFEST.csv"]


def scan(cap=None):
    """One pass per delivered file. Returns everything the report needs."""
    out = {}
    for p in files():
        stem = p.name[:-4]
        # csv.reader + column indices, not DictReader: `contractors.csv` is
        # 1.6 GB and building an 82-key dict per row costs minutes to answer a
        # question about two columns.
        with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            rd = csv.reader(fh)
            hdr = next(rd, [])
            state_cols = [c for c in hdr if c in BLOCKED_STATES]
            lineage = [c for c in hdr if is_lineage_column(c)]
            # candidate provenance columns - anything that could plausibly
            # carry a source claim, so the mixed-value report is not limited
            # to names someone already suspected
            prov = [c for c in hdr
                    if any(k in c.lower() for k in
                           ("basis", "source", "reason", "note", "evidence",
                            "method", "document", "detail"))]
            si = [(hdr.index(c), c) for c in state_cols]
            pi = [(hdr.index(c), c) for c in prov]
            # A MASK that fired must have left NOTHING behind. This is the
            # check that the mask ran, as opposed to being defined: for every
            # state value dispositioned MASK, no attribution cell on the row
            # may still be filled.
            # Conjunction rules: countable and leak-checkable the same way.
            # A rule applies to this file only if every column it names is
            # present, so a table that does not carry the quarantine columns is
            # not silently reported as clean against a rule it cannot trip.
            ci = []
            for rule in BLOCKED_COMBINATIONS:
                cols = list(rule["when"]) + list(rule.get("unless", {}))
                if not all(c in hdr for c in rule["when"]):
                    continue
                tgt = [(hdr.index(x), x) for x in
                       tuple(MASK_COLS.get(rule["reason"], ())) + MASK_FLAGS
                       if x in hdr]
                ci.append((rule,
                           [(hdr.index(c), c) for c in cols if c in hdr],
                           tgt))
            combos = Counter()
            mi = {}
            for c in state_cols:
                if not any(d == MASK for d in BLOCKED_STATES[c].values()):
                    continue
                tgt = [(hdr.index(x), x) for x in
                       tuple(MASK_COLS.get(c, ())) + MASK_FLAGS if x in hdr]
                if tgt:
                    mi[c] = (hdr.index(c), tgt)
            states = {c: Counter() for c in state_cols}
            kinds = {c: Counter() for c in prov}
            leak = Counter()
            n = 0
            for row in rd:
                n += 1
                if cap and n > cap:
                    break
                w = len(row)
                for i, c in si:
                    states[c][row[i].strip() if i < w else ""] += 1
                for i, c in pi:
                    v = row[i].strip() if i < w else ""
                    if not v:
                        continue
                    k = []
                    if SCRIPT_RE.search(v):
                        k.append("script")
                    if URL_RE.search(v):
                        k.append("url")
                    if LOCAL_RE.search(URL_RE.sub("", v)):
                        k.append("localpath")
                    kinds[c]["+".join(k) if k else "prose"] += 1
                for c, (idx, tgt) in mi.items():
                    v = row[idx].strip() if idx < w else ""
                    if not v or BLOCKED_STATES[c].get(v) != MASK:
                        continue
                    for i, x in tgt:
                        cell = row[i].strip() if i < w else ""
                        if cell and not (x in MASK_FLAGS and cell == "0"):
                            leak[f"{c}={v} left {x}"] += 1
                for rule, cols, tgt in ci:
                    vals = {c: (row[i].strip() if i < w else "")
                            for i, c in cols}
                    if not all(vals.get(c) in s
                               for c, s in rule["when"].items()):
                        continue
                    if any(vals.get(c) in s
                           for c, s in rule.get("unless", {}).items()):
                        continue
                    combos[rule["reason"]] += 1
                    if rule["disposition"] != MASK:
                        continue
                    for i, x in tgt:
                        cell = row[i].strip() if i < w else ""
                        if cell and not (x in MASK_FLAGS and cell == "0"):
                            leak[f"{rule['reason']} left {x}"] += 1
        out[stem] = {"rows": n, "cols": len(hdr), "header": hdr,
                     "states": states, "lineage": lineage, "kinds": kinds,
                     "mask_leak": leak, "combos": combos}
    return out


def dispositions(states):
    """(disposition, count) per (dataset, column, value), through THE policy."""
    rows = []
    for stem, d in states.items():
        for col, ctr in d["states"].items():
            for val, n in sorted(ctr.items(), key=lambda kv: -kv[1]):
                if not val:
                    disp = PUBLISH
                else:
                    disp = BLOCKED_STATES[col].get(val)
                    if disp is None:
                        disp = next((x for k, x in BLOCKED_STATES[col].items()
                                     if k.lower() == val.lower()), None)
                    if disp is None:
                        disp = WITHHOLD      # deny-by-default
                rows.append({"dataset": stem, "state_column": col,
                             "value": val or "(blank)", "rows": n,
                             "disposition": disp,
                             "masks": "; ".join(MASK_COLS.get(col, ()))
                                      if disp == MASK else ""})
    return rows


def mixed(states):
    """Columns whose VALUES mix real evidence with build plumbing.

    Not a drop list. A column here is a DATA problem - the value should not
    have had the code path written into it in the first place - and the fix is
    upstream in whatever wrote it, not in the export.
    """
    rows = []
    for stem, d in states.items():
        for col, ctr in d["kinds"].items():
            tot = sum(ctr.values())
            if not tot:
                continue
            plumb = sum(v for k, v in ctr.items()
                        if "script" in k or "localpath" in k)
            if not plumb:
                continue
            clean = tot - plumb
            rows.append({
                "dataset": stem, "column": col, "filled": tot,
                "values_naming_a_script_or_local_file": plumb,
                "values_that_do_not": clean,
                "pct_plumbing": round(100.0 * plumb / tot, 1),
                # NOT a severity. `EVERY_VALUE` means every filled value
                # names a script or a local file SOMEWHERE in it - which for
                # `legislation.entity_link_basis` ("no spine name matched this
                # bill's title or text; code/1140 from ...") is one sentence of
                # real evidence with a build note welded on. The fix is
                # upstream in whatever wrote the value, never a column drop.
                "kind": ("EVERY_VALUE" if clean == 0 else "SOME_VALUES"),
                "breakdown": "; ".join(f"{k}={v}" for k, v in ctr.most_common()),
            })
    rows.sort(key=lambda r: -r["values_naming_a_script_or_local_file"])
    return rows


def widths():
    cw, pw = {}, {}
    for p in files():
        with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            cw[p.name[:-4]] = len(next(csv.reader(fh), []))
    if PREVIEW.exists():
        for p in sorted(PREVIEW.glob("*.csv")):
            if p.name == "MANIFEST.csv":
                continue
            with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
                pw[p.name[:-4]] = len(next(csv.reader(fh), []))
    return cw, pw


def report(st):
    disp = dispositions(st)
    mx = mixed(st)
    cw, pw = widths()

    print(f"  1153 publication eligibility   {len(st)} delivered files\n")

    print("  CP-002 - adjudication states now under ONE deny-by-default policy")
    tally = Counter(r["disposition"] for r in disp)
    for k in (WITHHOLD, MASK, FLAG, PUBLISH):
        n = sum(r["rows"] for r in disp if r["disposition"] == k)
        print(f"    {k:<9} {tally[k]:>3} state value(s)  {n:>10,} rows")
    print()
    for k, lab in ((WITHHOLD, "WITHHELD  (row does not ship)"),
                   (MASK, "MASKED    (row ships, Cedar attribution withheld)")):
        print(f"    {lab}")
        for r in sorted((r for r in disp if r["disposition"] == k),
                        key=lambda r: -r["rows"]):
            print(f"      {r['dataset']:<26}{r['state_column']:<28}"
                  f"{r['value'][:40]:<41}{r['rows']:>9,}")
        print()

    combos = {s: d["combos"] for s, d in st.items() if d.get("combos")}
    if combos:
        print("    CONJUNCTIONS (BLOCKED_COMBINATIONS - no single column "
              "carries the fact)")
        for s, ctr in combos.items():
            for why, n in ctr.most_common():
                rule = next(r for r in BLOCKED_COMBINATIONS
                            if r["reason"] == why)
                print(f"      {s:<26}{why[:44]:<45}{rule['disposition']:<9}"
                      f"{n:>9,}")
        print()

    leaks = {s: d["mask_leak"] for s, d in st.items() if d.get("mask_leak")}
    if leaks:
        print("    MASK LEAKS - the mask is defined and did not fire")
        for s, ctr in leaks.items():
            for what, n in ctr.most_common(6):
                print(f"      {s:<26}{what[:60]:<62}{n:>9,}")
        print()

    print("  CP-022/031/033 - build-lineage columns dropped by name")
    any_lin = False
    for stem, d in st.items():
        if d["lineage"]:
            any_lin = True
            print(f"    {stem:<26} {', '.join(d['lineage'])}")
    if not any_lin:
        print("    none in the delivered files - the rule has landed")
    print()

    print("  columns whose VALUES mix evidence and plumbing (reported, NOT dropped)")
    for r in mx[:14]:
        print(f"    {r['kind']:<14}{r['dataset']:<24}{r['column'][:44]:<45}"
              f"{r['values_naming_a_script_or_local_file']:>8,}/"
              f"{r['filled']:<9,}{r['pct_plumbing']:>6}%")
    if len(mx) > 14:
        print(f"    ... {len(mx) - 14} more, all in the ledger")
    print()

    print("  export width - the correction to 1152")
    if cw:
        print(f"    dist/customer : {min(cw.values())}-{max(cw.values())} cols "
              f"(widest: {max(cw, key=cw.get)} at {max(cw.values())})")
    if pw:
        print(f"    dist/preview  : {min(pw.values())}-{max(pw.values())} cols")
    else:
        print("    dist/preview  : absent - rebuild with 1151")
    print(f"    the review saw 29-81 on the ten-row sample; the delivered "
          f"export is WIDER, not narrower")
    print()
    print("  " + lobbying_warning())
    return disp, mx


def write(disp, mx, st):
    combos = {s: d["combos"] for s, d in st.items() if d.get("combos")}
    OUT_STATES.parent.mkdir(parents=True, exist_ok=True)
    with OUT_STATES.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(disp[0]))
        w.writeheader()
        w.writerows(disp)
    with OUT_MIXED.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(mx[0]))
        w.writeheader()
        w.writerows(mx)
    print(f"    -> {OUT_STATES.relative_to(ROOT)}")
    print(f"    -> {OUT_MIXED.relative_to(ROOT)}")

    cw, pw = widths()
    L = [f"# Publication eligibility - the CP-002 policy and its evidence",
         "",
         f"*Generated by `code/1153_qa_publication_eligibility.py build` on "
         f"{TODAY}. Never hand-edit; re-run the script.*", "",
         "The rules are in `code/cedar_publication.py`: `BLOCKED_STATES`, "
         "`MASK_COLS`, `LINEAGE_COLS`, `is_publication_eligible()`. This "
         "document is what they DO, measured against `dist/customer/`.", "",
         "## The four dispositions", "",
         "| disposition | meaning |", "|---|---|",
         "| PUBLISH | the state is not a blocker |",
         "| FLAG | the row ships and the state column ships with it - the "
         "buyer needs to SEE this, not to have it hidden |",
         "| MASK | the row ships; the Cedar attribution on it does not. The "
         "state column stays, so the file says why the owner is absent |",
         "| WITHHOLD | the row does not ship. It is not deleted - it stays in "
         "`data/clean` with its status, and the count appears in "
         "`MANIFEST.csv` under `rows_withheld` |", "",
         "An adjudication value this policy has never seen WITHHOLDS and names "
         "itself in the reason. That is what deny-by-default means here.", "",
         "## Every state value, its live count and its judgement", "",
         "| dataset | state column | value | rows | disposition |",
         "|---|---|---|---:|---|"]
    for r in sorted(disp, key=lambda r: (r["dataset"], r["state_column"],
                                         -r["rows"])):
        L.append(f"| {r['dataset']} | `{r['state_column']}` | "
                 f"`{r['value']}` | {r['rows']:,} | {r['disposition']} |")
    L += ["", "## Conjunctions - where no single column carries the fact", "",
          "`BLOCKED_COMBINATIONS` in `cedar_publication`. CP-016 needed one: "
          "the defect is a quarantined METHOD, and the misleading "
          "`ruling_status` label is on only a fraction of the rows it "
          "produced.", "",
          "| dataset | rule | disposition | rows |", "|---|---|---|---:|"]
    for s, ctr in sorted(combos.items()):
        for why, n in ctr.most_common():
            rule = next(r for r in BLOCKED_COMBINATIONS if r["reason"] == why)
            L.append(f"| {s} | `{why}` | {rule['disposition']} | {n:,} |")
    L += ["", "## Build-lineage columns dropped by name", "",
          "`LINEAGE_COLS` + `LINEAGE_SUFFIXES` in `cedar_publication`. "
          "**`_basis` is deliberately NOT a lineage suffix** - it carries the "
          "best provenance in the product.", ""]
    lin = {s: d["lineage"] for s, d in st.items() if d["lineage"]}
    if lin:
        L += ["| dataset | columns still present (the rule has NOT landed) |",
              "|---|---|"]
        L += [f"| {s} | {', '.join(c)} |" for s, c in sorted(lin.items())]
    else:
        L.append("No delivered file carries a lineage column. The rule has "
                 "landed.")
    L += ["", "## Columns that MIX evidence and plumbing", "",
          "Reported, never dropped. A column here is an upstream DATA problem: "
          "the value should not have had a code path written into it. The "
          "column stays because the rest of the value is evidence.", "",
          "| dataset | column | plumbing / filled | % | kind |",
          "|---|---|---:|---:|---|"]
    for r in mx:
        L.append(f"| {r['dataset']} | `{r['column']}` | "
                 f"{r['values_naming_a_script_or_local_file']:,} / "
                 f"{r['filled']:,} | {r['pct_plumbing']} | {r['kind']} |")
    L += ["", "## Export width", "",
          f"`dist/customer` is **{min(cw.values())}-{max(cw.values())} "
          f"columns**, widest `{max(cw, key=cw.get)}`. The ten-row review saw "
          f"29-81. **The export is wider than the review found, not "
          f"narrower** - only the 100-row previews in `dist/preview` are "
          f"narrow"
          + (f" ({min(pw.values())}-{max(pw.values())})." if pw else "."), "",
          "## Still open, and why they are not decided here", "",
          "- **QA-CP016 is RESOLVED, not open.** It was logged here as "
          "needing an owner because 3,469 quarantined rows read "
          "`ruling_status = RULED_ATTRIBUTED` and a positive human ruling "
          "should not be discarded by a batch-level quarantine. **The premise "
          "was false.** Those rows are `cluster_v3` (3,330) and `need_v6` "
          "(139), and **no row anywhere in the quarantine is tier A** - "
          "227,540 of 227,540 are tier B on `identifier_ruling_tier` and on "
          "`confidence_tier`, while `ENTITY_MATCH_RULES` rule 8 reserves tier "
          "A for an owner ruling. They are the quarantined method’s own "
          "output wearing an adjudication-shaped name. Masked by "
          "`BLOCKED_COMBINATIONS`, keyed on the method and the tier rather "
          "than on the status label - which matters, because the label is on "
          "1,405 of the still-attributed rows and the unlabelled "
          "`cluster_v3` rows beside them carried $16.00B.", "",
          "- **QA-NEST-SOURCEDOC** `nest.source_document` is a real "
          "source-document column on 825 rows and the owner's own research "
          "dataset, named by its path on this machine, on 3,189. It is kept "
          "because dropping it would delete the 825; the fix is upstream.", "",
          "- **QA-GEOREASON** `subcontracting.geo_subawardee_county_gap_reason` "
          "opens every one of its 85,858 filled values with `closed "
          "2026-09-02 by code/1109_subawardee_geo_promote:` and then states a "
          "real method. The sentence is evidence with a build note welded to "
          "the front of it; the fix is to stop writing the prefix.", ""]
    DOC.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"    -> {DOC.relative_to(ROOT)}")


def verify(st) -> int:
    """FAIL when the work did not land."""
    bad = []
    if not files():
        bad.append("dist/customer is empty - nothing to verify")
    for stem, d in st.items():
        for c in d["lineage"]:
            bad.append(f"{stem}.csv still ships lineage column `{c}` - "
                       f"publishable_columns() did not drop it, so the export "
                       f"was not rebuilt after the rule changed")
        for col, ctr in d["states"].items():
            for val, n in ctr.items():
                if not val:
                    continue
                disp = BLOCKED_STATES[col].get(val) or next(
                    (x for k, x in BLOCKED_STATES[col].items()
                     if k.lower() == val.lower()), None)
                if disp is None:
                    bad.append(f"{stem}.{col} = {val!r} ({n:,} rows) is not in "
                               f"the policy vocabulary; deny-by-default should "
                               f"have withheld it")
                elif disp == WITHHOLD:
                    bad.append(f"{stem}.{col} = {val!r} is WITHHOLD and "
                               f"{n:,} row(s) shipped anyway")
        for what, n in sorted(d.get("mask_leak", {}).items(), key=lambda kv: -kv[1]):
            bad.append(f"{stem}: MASK not applied - {what} filled on "
                       f"{n:,} row(s)")
    for b in bad:
        print("  FAIL " + b)
    print(f"  1153 verify   {'FAIL' if bad else 'ok'}   {len(bad)} problem(s)")
    return 1 if bad else 0


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "report"
    if not CUST.exists():
        print(f"  {CUST.relative_to(ROOT)} does not exist - run 1137 build")
        return 1
    st = scan()
    if mode == "verify":
        return verify(st)
    disp, mx = report(st)
    if mode == "build":
        write(disp, mx, st)
    else:
        print("\n  nothing written. re-run with `build`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
