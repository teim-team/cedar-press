"""SHARD-E: propose CANDIDATE matches from the ANC subsidiary edges to entities
Cedar already knows, and to identifiers in data/clean/fpds_uei_edges.csv.

THIS SCRIPT RESOLVES NOTHING. It writes candidates with a confidence and the
reason, into data/staging/anc_subsidiaries/shard_e_match_candidates.csv.
Identity resolution belongs to 503/510; nothing here touches the spine, mints an
entity, or writes a ledger row. A named-but-unmatched subsidiary is a valuable
row exactly as it stands.

Two match routes, and they are NOT the same strength:

  * CAGE  - exact. ASRC Federal publishes the CAGE code of every operating
            company on its own site; a CAGE is an identifier, not a name, so an
            exact hit is evidence of the same registrant with no name inference
            at all. Confidence `exact_identifier`.
  * name  - a proposal only. docs/NATIVE_ENTITY_NUANCES.md measures the ceiling:
            over the owner's 2021 BGOV crosswalk, 46.3% of confirmed tribe->vendor
            linkages share NOT ONE non-generic token with the owner's name, and no
            fuzzier matcher raises that. So a name hit is `name_exact` or
            `name_normalised` and never better, and a MISS is not evidence of
            anything.

NO NETWORK.
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STAGE = ROOT / "data" / "staging" / "anc_subsidiaries"
EDGES = STAGE / "shard_e.jsonl"
OUT = STAGE / "shard_e_match_candidates.csv"
csv.field_size_limit(10_000_000)

SUFFIX = re.compile(
    r"\b(llc|l\.l\.c|inc|incorporated|corp|corporation|co|company|ltd|limited|"
    r"lp|llp|plc|group|holdings|holding)\b")


def fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s.lower())


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = SUFFIX.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def main():
    edges = [json.loads(ln) for ln in EDGES.open(encoding="utf-8")]

    # --- Cedar entities (whole register, not just shard E's slice)
    reg = list(csv.DictReader(
        (ROOT / "data/spine/cedar_identity_register.csv").open(encoding="utf-8-sig")))
    by_fold, by_norm = {}, {}
    for r in reg:
        by_fold.setdefault(fold(r["canonical_name"]), r)
        by_norm.setdefault(norm(r["canonical_name"]), r)

    # --- identifier graph: names, UEIs and CAGE codes already on file
    uei_rows = list(csv.DictReader(
        (ROOT / "data/clean/fpds_uei_edges.csv").open(encoding="utf-8-sig")))
    name_to_uei, name_to_uei_n = {}, {}
    for r in uei_rows:
        for nm, ui in ((r.get("child_name"), r.get("child_uei")),
                       (r.get("parent_name"), r.get("parent_uei"))):
            if nm and ui:
                name_to_uei.setdefault(fold(nm), (nm, ui))
                name_to_uei_n.setdefault(norm(nm), (nm, ui))

    cage_to = {}
    cage_files = [ROOT / "data/clean/fpds_uei_cage_map.csv",
                  ROOT / "data/clean/cedar_cage_backfill.csv"]
    ct = [p.name for p in cage_files if p.exists()]
    for p in cage_files:
        if not p.exists():
            continue
        for r in csv.DictReader(p.open(encoding="utf-8-sig")):
            cg = (r.get("cage_code") or "").strip().upper()
            if cg:
                cage_to.setdefault(cg, {"uei": r.get("uei", ""),
                                        "legal_business_name": r.get("legal_business_name", ""),
                                        "cage_source_file": p.name})
    cage_cols = ["uei", "cage_code", "legal_business_name"]

    rows = []
    for e in edges:
        child = e["child_name_raw"]
        f, n = fold(child), norm(child)
        hits = []
        cg = (e.get("child_cage_code") or "").strip().upper()
        if cg and cg in cage_to:
            r = cage_to[cg]
            hits.append(("cedar_identifier_graph", "exact_identifier",
                         "CAGE " + cg,
                         json.dumps({k: r[k] for k in list(r)[:6]}, ensure_ascii=False)[:300]))
        elif cg:
            hits.append(("published_cage_no_match", "exact_identifier_unmatched",
                         "CAGE " + cg,
                         "the parent publishes this CAGE; it is not in Cedar's cage index"))
        if f in by_fold:
            r = by_fold[f]
            hits.append(("cedar_register", "name_exact", r["canonical_name"],
                         r["cedar_uid"] + " | " + r["entity_class"]))
        elif n and n in by_norm:
            r = by_norm[n]
            hits.append(("cedar_register", "name_normalised", r["canonical_name"],
                         r["cedar_uid"] + " | " + r["entity_class"]))
        if f in name_to_uei:
            nm, ui = name_to_uei[f]
            hits.append(("fpds_uei_edges", "name_exact", nm, "UEI " + ui))
        elif n and n in name_to_uei_n:
            nm, ui = name_to_uei_n[n]
            hits.append(("fpds_uei_edges", "name_normalised", nm, "UEI " + ui))

        if not hits:
            hits = [("", "no_candidate", "",
                     "named by its parent, unmatched in Cedar. This is a finding, "
                     "not a gap: 46.3% of confirmed tribal subsidiaries share no "
                     "non-generic token with the owner (NATIVE_ENTITY_NUANCES.md).")]
        for src, conf, cand, detail in hits:
            rows.append({
                "parent_cedar_uid": e["parent_cedar_uid"],
                "parent_name": e["parent_name"],
                "anc_root_name": e.get("anc_root_name", ""),
                "child_name_raw": child,
                "child_cage_code": e.get("child_cage_code", ""),
                "depth": e["depth"],
                "candidate_source": src,
                "candidate_confidence": conf,
                "candidate_name": cand,
                "candidate_detail": detail,
                "source_url": e["source_url"],
                "source_type": e["source_type"],
            })

    with OUT.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    import collections
    c = collections.Counter(r["candidate_confidence"] for r in rows)
    matched = len({r["child_name_raw"] for r in rows
                   if r["candidate_confidence"] != "no_candidate"})
    print("edges", len(edges), "| candidate rows", len(rows),
          "| distinct children with >=1 candidate", matched)
    for k, v in c.most_common():
        print("   %-30s %d" % (k, v))
    print("cage index", len(cage_to), "codes from", ct,
          "cols", cage_cols[:8])
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main())
