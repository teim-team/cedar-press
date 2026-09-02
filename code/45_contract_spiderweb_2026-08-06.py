#!/usr/bin/env python3
"""
Cedar Press - 45: contract spiderweb candidates, 2026-08-06.

Finds UEIs that share a corporate parent with a ledger-confirmed Native UEI.
These are CANDIDATES for review. Nothing here is an attribution.

Why this rebuild supersedes review/contract_spiderweb_candidates_2026-08-05.csv
------------------------------------------------------------------------------
That file has 7 rows because only `contracts_w1.zip` had been collected when it
ran. `contracts_w2.zip` and `contracts_w3.zip` were collected later the same
evening and cover 2024-07-01 through 2026-08-05. This run reads all three plus
`idvs_all.zip`, and adds the FY2000-2022 parent graph from
`data/clean/prime_contracts.csv` (11,449 distinct parent UEIs), which the
earlier run did not use at all.

Two relationship shapes, kept distinct because they carry different weight
--------------------------------------------------------------------------
  parent_is_ledger_native  - the candidate's own parent UEI is ledger-confirmed.
                             Strong: this is a direct ownership edge.
  sibling_of_ledger_native - the candidate shares a parent with a DIFFERENT UEI
                             that is ledger-confirmed. Weaker: siblings under a
                             large non-Native holding company are not Native.
                             ASRC Federal subsidiaries sitting under Science
                             Applications International are the worked example -
                             SAIC is the parent of record, and its other
                             children are emphatically not Native.

NEVER classify by name alone. AGENTS.md: subsidiaries often carry generic or
numbered names, DBAs invert the signal, and individual Native ownership is not
tribal/ANC/NHO ownership. Resolve via the hierarchy, then have Elijah rule.

Only tier-A ledger UEIs seed the web. Tier B is algorithmic and unruled -
seeding from B would compound one unreviewed guess into another.

Reads  data/raw/contracts/usaspending_gapfill_2026-08-05/*.zip
       data/clean/prime_contracts.csv
       data/clean/cedar_identifier_ledger_final.csv
Writes review/contract_spiderweb_candidates_2026-08-06.csv
       review/contract_new_ueis_fy2023_2026.csv
"""

import csv
import io
import json
import zipfile
from collections import defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
GAPFILL = CEDAR / "data" / "raw" / "contracts" / "usaspending_gapfill_2026-08-05"
TODAY = date.today().isoformat()


def load_ledger():
    tier, meta = {}, {}
    with open(CLEAN / "cedar_identifier_ledger_final.csv",
              encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            if (r.get("identifier_type") or "").strip().upper() != "UEI":
                continue
            u = (r.get("identifier") or "").strip().upper()
            if len(u) != 12:
                continue
            t = (r.get("confidence_tier") or "").strip()
            if u not in tier or "ABCX".find(t) < "ABCX".find(tier[u]):
                tier[u] = t
                meta[u] = (r.get("tribe_id", ""), r.get("canonical_name", ""),
                           r.get("entity_class", ""))
    return tier, meta


def iter_gapfill_rows():
    """Prime award-summary rows from every collected gapfill zip."""
    for z in sorted(GAPFILL.glob("*.zip")):
        if z.name.startswith("_schema_probe"):
            continue
        with zipfile.ZipFile(z) as zf:
            for m in zf.namelist():
                if not m.lower().endswith(".csv") or "Subawards" in m:
                    continue
                with zf.open(m) as fh:
                    for r in csv.DictReader(io.TextIOWrapper(fh, "utf-8-sig")):
                        yield z.name, r


def main():
    print("=== Cedar Press 45: contract spiderweb 2026-08-06 ===\n")
    tier, meta = load_ledger()
    native_A = {u for u, t in tier.items() if t == "A"}
    print(f"ledger: {len(tier):,} UEIs, {len(native_A):,} at tier A (seeds)")

    # ---- observations: uei -> parent, with rollups ----------------------
    # `parent` is a SET, not a scalar. 528 of 4,023 recipients (13.1%) in the
    # gapfill carry MORE THAN ONE recipient_parent_uei, for two distinct
    # reasons that must be handled differently:
    #   - self-parent (parent == recipient): a placeholder meaning "no parent
    #     of record", not an ownership fact. Dropped.
    #   - genuinely different parents: real ownership change. FPDS does not
    #     update retroactively (AGENTS.md), so both edges are true, at
    #     different times. ASRC Federal Facilities Logistics appears under both
    #     Arctic Slope (CY16XXPHX213) and SAIC (RE7WMNV9L719).
    # Taking last-seen would pick one arbitrarily by zip iteration order. Every
    # edge is kept and the conflict is disclosed on the row.
    obs = defaultdict(lambda: {"name": "", "cage": "", "parents": {},
                               "n": 0, "usd": 0.0,
                               "first": "", "last": "", "flags": set(),
                               "src": set()})
    FLAGCOLS = ["alaskan_native_corporation_owned_firm",
                "american_indian_owned_business", "tribally_owned_firm",
                "native_hawaiian_organization_owned_firm",
                "indian_tribe_federally_recognized"]

    n_rows = 0
    for zname, r in iter_gapfill_rows():
        u = (r.get("recipient_uei") or "").strip().upper()
        if len(u) != 12:
            continue
        n_rows += 1
        o = obs[u]
        o["name"] = o["name"] or (r.get("recipient_name") or "").strip()
        o["cage"] = o["cage"] or (r.get("cage_code") or "").strip()
        p = (r.get("recipient_parent_uei") or "").strip().upper()
        if len(p) == 12 and p != u:              # self-parent is a placeholder
            o["parents"].setdefault(
                p, (r.get("recipient_parent_name") or "").strip())
        o["n"] += 1
        try:
            o["usd"] += float(r.get("total_obligated_amount") or 0)
        except ValueError:
            pass
        for k in ("award_base_action_date", "award_latest_action_date"):
            d = (r.get(k) or "").strip()[:10]
            if d:
                o["first"] = min(o["first"] or d, d)
                o["last"] = max(o["last"], d)
        for f in FLAGCOLS:
            if (r.get(f) or "").strip().lower() in ("t", "true", "1", "y"):
                o["flags"].add(f)
        o["src"].add("gapfill_award_summaries_2023_2026")
    print(f"gapfill: {n_rows:,} prime award summaries, "
          f"{len(obs):,} distinct recipient UEIs")

    # ---- FY2000-2022 parent graph from the spine ------------------------
    spine_parent, spine_meta, spine_ueis = {}, {}, set()
    with open(CLEAN / "prime_contracts.csv", encoding="utf-8-sig",
              newline="") as fh:
        for r in csv.DictReader(fh):
            u = (r.get("awardee_uei") or "").strip().upper()
            if len(u) != 12:
                continue
            spine_ueis.add(u)
            p = (r.get("parent_uei") or "").strip().upper()
            if len(p) == 12 and p != u:
                spine_parent.setdefault(u, {})[p] = \
                    (r.get("parent_name") or "").strip()
            spine_meta.setdefault(u, ((r.get("awardee_name") or "").strip(),
                                      "",
                                      (r.get("cage_code") or "").strip()))
    print(f"spine: {len(spine_ueis):,} awardee UEIs, "
          f"{len({p for d in spine_parent.values() for p in d}):,} "
          "distinct parents")

    # ---- unified parent graph (multi-edge) -------------------------------
    edges = defaultdict(dict)          # uei -> {parent_uei: parent_name}
    for u, o in obs.items():
        for p, pn in o["parents"].items():
            edges[u].setdefault(p, pn)
    for u, d in spine_parent.items():
        for p, pn in d.items():
            edges[u].setdefault(p, pn)
    children = defaultdict(set)
    for u, d in edges.items():
        for p in d:
            children[p].add(u)
    n_conflict = sum(1 for d in edges.values() if len(d) > 1)
    print(f"parent graph: {len(edges):,} UEIs with >=1 parent edge, "
          f"{n_conflict:,} ({100*n_conflict/max(len(edges),1):.1f}%) have "
          "MORE THAN ONE parent - kept as separate edges, not collapsed")

    # parents that are themselves ledger-confirmed Native
    native_parents = {p for p in children if p in native_A}
    # parents with at least one ledger-confirmed Native child
    parents_with_native_child = {p for p, kids in children.items()
                                 if kids & native_A}
    print(f"parents that ARE tier-A Native UEIs: {len(native_parents):,}")
    print(f"parents with >=1 tier-A Native child: "
          f"{len(parents_with_native_child):,}")

    # ---- candidates ------------------------------------------------------
    rows = []
    seen = set()
    for p in native_parents | parents_with_native_child:
        pname = (obs.get(p, {}).get("name")
                 or spine_meta.get(p, ("", "", ""))[0]
                 or next((edges[k][p] for k in children[p] if edges[k].get(p)),
                         ""))
        for u in sorted(children[p]):
            if u in native_A or u == p:
                continue                       # already confirmed, not a lead
            if tier.get(u) == "X":
                continue                       # ruled out; never a candidate
            if (u, p) in seen:                 # one row per EDGE, not per UEI
                continue
            seen.add((u, p))
            other_parents = sorted(set(edges[u]) - {p})
            o = obs.get(u)
            sm = spine_meta.get(u, ("", "", ""))
            rel = ("parent_is_ledger_native" if p in native_A
                   else "sibling_of_ledger_native")
            sibs = sorted((children[p] & native_A) - {u})
            rows.append({
                "candidate_uei": u,
                "candidate_name": (o["name"] if o else "") or sm[0],
                "candidate_cage": (o["cage"] if o else "") or sm[2],
                "relationship": rel,
                "shared_parent_uei": p,
                "shared_parent_name": pname,
                "parent_ledger_tier": tier.get(p, ""),
                "parent_ledger_tribe_id": meta.get(p, ("", "", ""))[0],
                "parent_ledger_canonical_name": meta.get(p, ("", "", ""))[1],
                "parent_ledger_entity_class": meta.get(p, ("", "", ""))[2],
                "ledger_confirmed_siblings": ";".join(sibs[:5]),
                "n_ledger_confirmed_siblings": len(sibs),
                "candidate_other_parent_ueis": ";".join(other_parents),
                "parent_conflict": "YES" if other_parents else "NO",
                "candidate_current_ledger_tier": tier.get(u, "not_in_ledger"),
                "in_spine_fy2000_2022": "YES" if u in spine_ueis else "NO",
                "n_award_summaries_2023_2026": o["n"] if o else 0,
                # CUMULATIVE over each award's whole life, NOT an FY total.
                # Award-summary total_obligated_amount double-counts if summed
                # across years. Use it to TRIAGE which candidates matter, never
                # as a published dollar figure.
                "award_summary_obligated_usd_cumulative":
                    round(o["usd"], 2) if o else 0,
                "first_action_date": o["first"] if o else "",
                "last_action_date": o["last"] if o else "",
                "native_flags_on_award": ";".join(sorted(o["flags"])) if o else "",
                "evidence": (
                    "Shares recipient_parent_uei with a tier-A ledger-confirmed "
                    "Native UEI. Parent edge observed on USAspending prime award "
                    "summaries 2023-2026 and/or parent_uei in "
                    "prime_contracts.csv (FY2000-2022)."),
                "attribution_status": "CANDIDATE_ONLY_NOT_ATTRIBUTED",
                "caution": ((
                    "Sibling relationships under a large non-Native holding "
                    "company are NOT evidence of Native ownership. Verify the "
                    "parent is the Native entity before ruling."
                    if rel == "sibling_of_ledger_native" else
                    "Direct ownership edge; still requires a source before "
                    "attribution.")
                    + (" AMBIGUOUS OWNERSHIP: this UEI also reports a "
                       "different parent. FPDS does not update retroactively, "
                       "so the edges may be true at different times - date the "
                       "ownership change before attributing any dollar."
                       if other_parents else "")),
                "built_date": TODAY,
                "YOUR_RULING": "",
            })

    rows.sort(key=lambda r: (-r["award_summary_obligated_usd_cumulative"],
                             r["candidate_uei"]))
    out = REVIEW / "contract_spiderweb_candidates_2026-08-06.csv"
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {out.name}: {len(rows):,} candidates")
    for rel in ("parent_is_ledger_native", "sibling_of_ledger_native"):
        s = [r for r in rows if r["relationship"] == rel]
        print(f"   {rel}: {len(s):,}  "
              f"(${sum(r['award_summary_obligated_usd_cumulative'] for r in s)/1e6:,.1f}M cumulative)")

    # ---- new UEIs --------------------------------------------------------
    new = [u for u in obs
           if u not in spine_ueis and u not in tier]
    nrows = sorted(({"uei": u, "name": obs[u]["name"], "cage": obs[u]["cage"],
                     "parent_ueis": ";".join(sorted(obs[u]["parents"])),
                     "parent_names": ";".join(sorted(set(obs[u]["parents"].values()))),
                     "n_awards": obs[u]["n"],
                     "award_summary_obligated_usd_cumulative": round(obs[u]["usd"], 2),
                     "first_action_date": obs[u]["first"],
                     "last_action_date": obs[u]["last"],
                     "native_flags_on_award": ";".join(sorted(obs[u]["flags"])),
                     "note": ("Appears in FY2023-2026 award summaries; absent "
                              "from both prime_contracts.csv and the ledger. "
                              "Flag presence is NOT attribution."),
                     "built_date": TODAY}
                    for u in new),
                   key=lambda r: -r["award_summary_obligated_usd_cumulative"])
    out2 = REVIEW / "contract_new_ueis_fy2023_2026.csv"
    with open(out2, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(nrows[0].keys()))
        w.writeheader()
        w.writerows(nrows)
    print(f"wrote {out2.name}: {len(nrows):,} UEIs new since FY2022")

    print(json.dumps({
        "gapfill_recipient_ueis": len(obs),
        "already_in_spine": len(set(obs) & spine_ueis),
        "already_in_ledger": len(set(obs) & set(tier)),
        "new_ueis": len(new),
        "candidates": len(rows),
    }, indent=2))


if __name__ == "__main__":
    main()
