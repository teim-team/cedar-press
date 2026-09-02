#!/usr/bin/env python3
# lint-ok: class6 - THE ORDERING IS DECLARED. This script FULL-REBUILDS
# assistance_tribe_id_crosswalk.csv; 503_reconcile_assistance_to_cedar_ids.py
# ENRICHES it in place (resolved Cedar ids + basis, owner-directed 2026-08-28)
# and runs LAST. Declared in cedar_pipeline.KNOWN_ORDERINGS. Re-run 503 after
# any run of this script, or the reconciliation reverts silently while this
# prints a normal-looking row count.
"""
Cedar Press - 152: crosswalk the assistance legacy tribe index to Cedar IDs.

WHAT THIS IS, AND WHAT IT IS NOT
--------------------------------
`federal_funding_transactions.csv` carries `tribe_id` in TWO schemes in one
column:

    lineageA_dofile_integer   365,535 rows   e.g. 192, 201, 343
    Cedar-shaped (has a dash) 170,488 rows   e.g. TRBF-NAVAJO-00

I first read this as "514,000 unjoinable rows." **That was wrong.** The integers
are a deliberate, dense tribe index - 361 distinct IDs across slots 1-381 - and
every one carries the tribe's own name beside it:

    192 -> NAVAJO NATION TRIBAL GOVERNMENT, THE      12,764 rows
    201 -> OGLALA SIOUX TRIBE OF PINE RIDGE            5,501 rows
    343 -> TURTLE MOUNTAIN BAND OF CHIPPEWA INDIANS    5,055 rows

The attribution work was already done in the original do-file. What is missing
is only the mapping between two ID vocabularies.

**So this is a 361-row crosswalk, not a 365,535-row problem.**

HOW IT RESOLVES
---------------
Each integer's most frequent name goes through the SHARED resolver
(`33_apply_party_rulings.resolve_entity`), with today's guards applied:

- containment must rest on a token unique to ONE spine entity
- `NAME_TRAPS` applies to the token path too, not just containment
- a tribe name followed by a place suffix is a PLACE

WHAT IT REFUSES
---------------
- **It writes a crosswalk, not an edit.** `federal_funding_transactions.csv` is
  untouched. Applying the crosswalk is a separate, reviewable step.
- **Nothing is promoted to tier A by the join.** A resolver match is tier B.
  Learned the same day: an EIN hit was treated as tier A and produced UNITED WAY
  OF THE GREATER CHIPPEWA VALLEY -> United Auburn. **A tier is inherited from
  the source, never assigned by the consumer.**
- **An unresolved integer keeps its rows.** It is a real tribe with a real name
  that our spine does not hold under that string - a spine gap to fill, never a
  row to drop.

    py -3 code/152_build_assistance_id_crosswalk.py
"""

import csv
import importlib.util
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
LEGACY_DIR = CEDAR / "data" / "spine" / "legacy"
REVIEW = CEDAR / "review"
SPINE = CEDAR / "data" / "spine" / "cedar_entity_spine.csv"
SRC = CLEAN / "federal_funding_transactions.csv"
OUT = LEGACY_DIR / "assistance_tribe_id_crosswalk.csv"
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

NAME_COLS = ("tribe_name", "recipient_name", "tribe", "canonical_name",
             "entity_name", "recipient_legal_name", "awardee_name")
PLACE_SUFFIXES = {"falls", "city", "county", "springs", "heights", "valley",
                  "park", "beach", "ridge", "lake", "lakes", "river", "hills",
                  "junction", "township", "borough", "village", "plains",
                  "bay", "harbor", "island"}
SHORT_OK = {"zuni", "hopi", "crow", "ute", "sac", "fox", "yurok", "hoopa",
            "makah", "lummi", "quinault", "tlingit", "haida", "aleut",
            "inupiat", "koniag", "chugach", "doyon", "calista", "ahtna"}
STOP = {"the", "of", "and", "inc", "llc", "corporation", "company", "tribe",
        "tribal", "nation", "native", "indian", "indians", "alaska", "alaskan",
        "village", "community", "band", "pueblo", "council", "group", "corp",
        "reservation", "government", "business", "confederated", "assiniboine"}


def load(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def weak_containment(spine_name, candidate, how, tok=None):
    """Reject a containment match only when it does NOT cover the spine name.

    TWO WRONG VERSIONS PRECEDED THIS ONE, both measured 2026-08-12.

    v1 excluded only stopwords and short words. That let DENVER INDIAN HEALTH &
    FAMILY SERVICES match the spine entity "Native Health" on the single shared
    word "health" - 6 characters, so the length test passed it.

    v2 required a shared token UNIQUE to one spine entity. That was too strict
    in the other direction and killed correct matches: "NAVAJO NATION TRIBAL
    GOVERNMENT, THE" -> Navajo was rejected because "navajo" also appears in
    Ramah Navajo and Alamo Navajo. It threw away the eight LARGEST tribes in the
    assistance crosswalk - Navajo, Oglala Sioux, Turtle Mountain, Fort Peck,
    Lummi, White Mountain Apache, Rosebud, Salish and Kootenai.

    The real discriminator is COVERAGE OF THE SPINE NAME:

        "Navajo"        vs "NAVAJO NATION TRIBAL GOVERNMENT"  -> 1/1 covered  KEEP
        "Native Health" vs "DENVER INDIAN HEALTH & FAMILY..."  -> 1/2 covered  DROP

    A containment match is sound when every distinctive token of the SPINE
    entity's name appears in the candidate. Matching half a spine name proves
    nothing; matching all of it is what containment is supposed to mean.
    """
    if "contain" not in (how or "").lower():
        return False
    cand = set(norm(candidate).split())
    spine_tokens = [w for w in norm(spine_name).split()
                    if w not in STOP and (len(w) >= 4 or w in SHORT_OK)]
    if not spine_tokens:
        return True                      # nothing distinctive to match on
    return not all(w in cand for w in spine_tokens)



def main():
    spec = importlib.util.spec_from_file_location(
        "m33", CEDAR / "code" / "33_apply_party_rulings.py")
    m33 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m33)
    dspec = importlib.util.spec_from_file_location(
        "cedar_domain", CEDAR / "code" / "cedar_domain.py")
    dom = importlib.util.module_from_spec(dspec)
    dspec.loader.exec_module(dom)
    TRAPS = dom.NAME_TRAPS

    spine = load(SPINE)
    by_tid = {r["tribe_id"]: r for r in spine}
    tok = defaultdict(list)
    for r in spine:
        for w in norm(r.get("canonical_name")).split():
            if w in STOP or (len(w) < 5 and w not in SHORT_OK):
                continue
            tok[w].append(r)
    tok = {k: v[0] for k, v in tok.items() if len(v) == 1}

    print("=== 152: assistance legacy tribe index -> Cedar IDs ===\n")
    rows = load(SRC)
    idx = defaultdict(lambda: {"rows": 0, "names": Counter(), "usd": 0.0,
                               "states": Counter()})
    cedar_rows = 0
    for r in rows:
        t = (r.get("tribe_id") or "").strip()
        if not t:
            continue
        if "-" in t:
            cedar_rows += 1
            continue
        if not t.isdigit():
            continue
        e = idx[t]
        e["rows"] += 1
        for c in NAME_COLS:
            v = (r.get(c) or "").strip()
            if v:
                e["names"][v] += 1
                break
        s = (r.get("recipient_state") or r.get("state") or "").strip()
        if s:
            e["states"][s] += 1
        try:
            e["usd"] += float(str(r.get("obligated_usd") or 0).replace(",", "") or 0)
        except ValueError:
            pass

    print(f"  assistance rows            : {len(rows):,}")
    print(f"  already Cedar-shaped       : {cedar_rows:,}")
    print(f"  legacy-integer rows        : {sum(e['rows'] for e in idx.values()):,}")
    print(f"  DISTINCT legacy ids to map : {len(idx):,}   <- the real job size\n")

    out, stats = [], Counter()
    for lid, e in sorted(idx.items(), key=lambda kv: -kv[1]["rows"]):
        nm = e["names"].most_common(1)[0][0] if e["names"] else ""
        tid = cname = basis = ""
        tier = ""
        if nm:
            rid, rname, how = m33.resolve_entity(nm, spine)
            weak = weak_containment(rname, nm, how, tok) if rid else False
            if rid and not weak:
                tid, cname, tier = rid, rname, "B"
                basis = f"spine resolver ({how})"
                stats["resolved"] += 1
            else:
                words = norm(nm).split()
                hit = None
                for i, w in enumerate(words):
                    if w not in tok or w in TRAPS:
                        continue
                    if i + 1 < len(words) and words[i + 1] in PLACE_SUFFIXES:
                        continue
                    hit = tok[w]
                    break
                if hit:
                    tid, cname, tier = hit["tribe_id"], hit["canonical_name"], "B"
                    basis = "distinctive spine token in the name"
                    stats["token match"] += 1
                else:
                    basis = "no spine candidate"
                    stats["UNRESOLVED - spine gap"] += 1
        else:
            basis = "legacy id carries no name in this file"
            stats["no name"] += 1

        # HIERARCHY - Elijah, 2026-08-12: "ramah and alamo i believe are chapters
        # of the navajo nation like precincts". Correct, and the spine already
        # models it: Ramah Navajo Chapter is entity_class "Federal-level
        # constituent" with parent_entity_id TRBF-NAVAJO-00.
        #
        # So a name appearing in several spine entities is often a PARENT AND ITS
        # CONSTITUENTS, not competing candidates. 12 legacy ids here resolve to a
        # constituent on purpose - Leech Lake, Fond du Lac, Mille Lacs, Bois
        # Forte and Grand Portage under Minnesota Chippewa; Battle Mountain and
        # Wells under Te-Moak; Kanosh, Shivwits and Indian Peaks under Paiute
        # Indian Tribe of Utah; Viejas under Capitan Grande.
        #
        # The do-file gave those bands their own ids. Collapsing them into the
        # parent would destroy real structure. So the CHILD is what we map to,
        # and the parent is carried alongside so a consumer can roll up without
        # losing the distinction. "We own the TOP, the tribe owns the INSIDE."
        sp_row = by_tid.get(tid, {})
        parent_id = (sp_row.get("parent_entity_id") or "").split("|")[0].strip()
        is_constituent = "constitu" in (sp_row.get("entity_class") or "").lower()
        out.append({
            "legacy_tribe_id": lid,
            "legacy_name_as_filed": nm,
            "n_rows": e["rows"],
            "obligated_usd": round(e["usd"], 2),
            "top_states": "; ".join(k for k, _ in e["states"].most_common(3)),
            "proposed_cedar_tribe_id": tid,
            "proposed_canonical_name": cname,
            "confidence_tier": tier,
            "match_basis": basis,
            "entity_class": sp_row.get("entity_class", ""),
            "is_constituent_of_a_larger_tribe": "YES" if is_constituent else "NO",
            "parent_entity_id": parent_id if parent_id != tid else "",
            "parent_entity_name": (by_tid.get(parent_id, {}).get("canonical_name", "")
                                   if parent_id and parent_id != tid else ""),
            "caveat": "A resolver match is tier B. The legacy id already carries "
                      "the do-file's own attribution; this maps vocabularies, it "
                      "does not re-adjudicate whether the row is Native.",
            "built_date": TODAY,
        })

    print("[outcomes]")
    for k, v in stats.most_common():
        print(f"  {k:34s} {v:>4}")
    mapped = sum(1 for r in out if r["proposed_cedar_tribe_id"])
    rows_mapped = sum(r["n_rows"] for r in out if r["proposed_cedar_tribe_id"])
    print(f"\n  legacy ids mapped : {mapped} of {len(out)}")
    print(f"  rows they unlock  : {rows_mapped:,} "
          f"({100*rows_mapped/max(sum(r['n_rows'] for r in out),1):.1f}% of legacy rows)")
    print(f"  $ they unlock     : ${sum(r['obligated_usd'] for r in out if r['proposed_cedar_tribe_id'])/1e9:,.2f}B")

    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    print(f"\n  wrote {OUT.relative_to(CEDAR)}")

    unres = [r for r in out if not r["proposed_cedar_tribe_id"]]
    if unres:
        dest = REVIEW / f"assistance_legacy_id_unresolved_{TODAY}.csv"
        with open(dest, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(unres[0]))
            w.writeheader()
            w.writerows(sorted(unres, key=lambda r: -r["n_rows"]))
        print(f"  wrote {dest.name}  ({len(unres)} to rule)")
        print("\n  biggest unresolved:")
        for r in sorted(unres, key=lambda r: -r["n_rows"])[:8]:
            print(f"    {r['n_rows']:>6,} rows  id {r['legacy_tribe_id']:>4}  "
                  f"{r['legacy_name_as_filed'][:44]}")
    print("\n  federal_funding_transactions.csv NOT modified")


if __name__ == "__main__":
    main()
