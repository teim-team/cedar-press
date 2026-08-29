#!/usr/bin/env python3
"""
Cedar Press - 32: Build the deals-party review queue.

Dataset 5 joined 0 of 203 deal rows because the deals schema carries NO entity
identifier - `Native_Party` is free text. That single gap keeps the dated
ownership-event ledger, the asset the linked file was built around, sitting
BESIDE the panel rather than inside it.

The fix is small: rule the distinct party strings once, then every deal row
inherits a tribe_id. This script proposes matches conservatively and sends
everything uncertain to Elijah.

Matching discipline (each rule was paid for):
  * Never match on a single generic token. "Cherokee" alone must not reach
    Cherokee Nation; "Creek" alone must not reach Berry Creek.
  * Never collapse a qualified name. Absentee Shawnee Tribe of Oklahoma is
    NOT the Shawnee Tribe.
  * Two plausible entities means UNMATCHED, not a coin flip. Oneida NY and
    Oneida WI are different entities and $716M was once mis-split between them.

Outputs
-------
data/clean/deals_party_matches.csv     high-confidence proposals
review/deals_party_queue_<date>.csv    everything needing a ruling
"""

import sys as _sys_cd
from pathlib import Path as _Path_cd
_sys_cd.path.insert(0, str(_Path_cd(__file__).resolve().parent))
import cedar_domain as DOM   # noqa: E402  - DEALS_TRUTH, PROMOTED_TABLES

import csv
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
EXT = CEDAR / "data" / "raw" / "external"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()

NOISE = {"inc", "incorporated", "llc", "l l c", "corp", "corporation", "co",
         "company", "ltd", "limited", "lp", "llp", "the", "of", "and",
         "enterprises", "enterprise", "holdings", "group", "development",
         "industries", "services", "systems", "solutions", "gaming",
         "authority", "management", "partners", "ventures"}

# Words that describe the FORM of a tribal government rather than which one.
# "Navajo Nation" and "Navajo" are the same entity; stripping these lets an
# exact core comparison succeed where token-subset matching picked a worse
# candidate (Ramah Navajo Chapter) purely on an alias collision.
STRUCTURAL = {"nation", "nations", "tribe", "tribes", "tribal", "band", "bands",
              "pueblo", "community", "communities", "rancheria", "village",
              "colony", "indians", "indian", "native", "peoples", "people",
              "reservation", "confederated", "of"}

# Tokens that are tribe names AND common place/word names. A match resting on
# one of these alone is never enough.
GENERIC = {"cherokee", "creek", "seneca", "cayuga", "mohawk", "chippewa",
           "ottawa", "miami", "peoria", "shawnee", "sioux", "yavapai",
           "umatilla", "klamath", "modoc", "ponca", "kiowa", "comanche",
           "osage", "caddo", "oneida", "onondaga", "huron", "kickapoo",
           "winnebago", "menominee", "houma", "santee", "catawba", "lumbee",
           "apache", "navajo", "pueblo", "tribe", "tribal", "nation", "band",
           "native", "indian", "village", "community", "rancheria"}


def read_csv(p):
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(p, rows, fields):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {p.relative_to(CEDAR)}  ({len(rows):,} rows)")


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("\u02bb", "").replace("\u2018", "").replace("'", "")
    s = re.sub(r"[^a-z0-9 ]+", " ", s.lower())
    return [t for t in s.split() if t and t not in NOISE]


def core(s):
    """Identity tokens only: government-form words stripped as well as noise.

    'Navajo Nation', 'Navajo' and 'Navajo Tribe' all reduce to {'navajo'}.
    'Eastern Shawnee Tribe' reduces to {'eastern','shawnee'} and so still
    stays distinct from 'Shawnee Tribe' -> {'shawnee'}, which is the
    distinction three federally recognized governments were once collapsed on.
    """
    return frozenset(t for t in norm(s) if t not in STRUCTURAL)


def main():
    print("=== Cedar Press: deals-party review queue ===\n")

    # ---- every distinct party string across every deals file ------------
    parties = Counter()
    where = defaultdict(set)
    # THE TRUTH: data/clean/deals_classified.csv (cedar_domain.DEALS_TRUTH).
    #
    # This read the two root ledgers plus `deals_*_additions.csv`. That was
    # NOT the additions-only defect - the ledgers were here - but it is still
    # the wrong input, for two reasons measured 2026-08-26:
    #   * the parts union to 936 distinct Deal_IDs and the promoted table
    #     holds 935, because the parts do NOT honour
    #     `review/deals_withdrawn_duplicates.csv` (MA2020-008, withdrawn as a
    #     duplicate of ANCSA2-2020-004). Script 54 deliberately leaves a
    #     withdrawn row in its source file, so every consumer that assembles
    #     the universe itself must re-implement the withdrawal - and this one
    #     did not, so the queue offered a withdrawn row's party for ruling.
    #   * a hand-assembled union goes stale the day a tenth part is written.
    # Read the promoted table. See `cedar_domain.PROMOTED_TABLES`.
    files = [CEDAR / DOM.DEALS_TRUTH]
    for f in files:
        rows = read_csv(f)
        if not rows:
            continue
        col = "Native_Party" if "Native_Party" in rows[0] else None
        if not col:
            continue
        for r in rows:
            v = (r.get(col) or "").strip()
            if v:
                parties[v] += 1
                where[v].add(f.name)
        print(f"  {f.name:<44} {len(rows):>4} rows")
    print(f"\n  distinct Native_Party strings: {len(parties):,}")

    # ---- alias corpus from the spine ------------------------------------
    aliases = defaultdict(set)          # entity_id -> {alias token tuples}
    names = {}
    for r in read_csv(SPINE / "cedar_entity_spine.csv"):
        eid = r.get("tribe_id", "").strip()
        if not eid:
            continue
        names[eid] = r.get("canonical_name", "")
        cands = [r.get("canonical_name", "")] + \
                [a for a in (r.get("aliases") or "").split("|")]
        for a in cands:
            t = tuple(norm(a))
            if t:
                aliases[eid].add(t)
    for r in read_csv(EXT / "canonical_tribe_table.csv"):
        eid = r.get("tribe_id", "").strip()
        if not eid:
            continue
        names.setdefault(eid, r.get("canonical_name", ""))
        for k in ("canonical_name", "entity_namefull", "fedreg_nameaka",
                  "fedreg_nameprev", "biatld_nameshort"):
            t = tuple(norm(r.get(k, "")))
            if t:
                aliases[eid].add(t)
    print(f"  spine entities with aliases  : {len(aliases):,}")

    # ---- match -----------------------------------------------------------
    exact_index = defaultdict(set)
    for eid, alts in aliases.items():
        for t in alts:
            exact_index[t].add(eid)

    # Canonical-name index, kept separate from aliases. An alias collision
    # ("Navajo" is both the Navajo Nation's short form AND an alias fragment of
    # Ramah Navajo Chapter) must not outrank an exact canonical hit.
    canon_index = defaultdict(set)
    canon_core = {}
    for r in read_csv(SPINE / "cedar_entity_spine.csv"):
        eid = r.get("tribe_id", "").strip()
        cname = r.get("canonical_name", "")
        t = tuple(norm(cname))
        if eid and t:
            canon_index[t].add(eid)
            canon_core[eid] = core(cname)

    # The ANC roster is NOT in the 687-entity NEID spine, so before this no
    # Alaska Native corporation could ever match. That produced a real error:
    # "Ukpeagvik Inupiat Corporation" resolved to the federally recognized
    # VILLAGE named Inupiat. Under ANCSA a village government and a village
    # corporation are distinct entities, and merging them would attribute a
    # corporation's contracts to a tribal government.
    anc_ids = set()
    for r in read_csv(CLEAN / "anc_ceiling_roster.csv"):
        aid = (r.get("anc_id") or "").strip()
        cname = (r.get("corporation_name") or "").strip()
        t = tuple(norm(cname))
        if aid and t:
            canon_index[t].add(aid)
            canon_core[aid] = core(cname)
            names[aid] = cname
            anc_ids.add(aid)

    matched, queue = [], []
    for party, n in parties.most_common():
        pt = tuple(norm(party))
        if not pt:
            continue
        pset = set(pt)

        # SCORE, do not collect. The old code unioned every candidate, so one
        # alias collision turned an obvious match into a review item.
        scored = {}

        def offer(eid, score, how):
            if score > scored.get(eid, (0, ""))[0]:
                scored[eid] = (score, how)

        # 1. Exact canonical name - the strongest signal available.
        for eid in canon_index.get(pt, set()):
            offer(eid, 100, "exact_canonical")

        # 1b. Exact CORE match: identical once government-form words are
        #     stripped. "Navajo Nation" == "Navajo". This must outrank alias
        #     containment, which previously handed Navajo Nation to Ramah
        #     Navajo Chapter on a shared alias fragment.
        pcore = core(party)
        if pcore:
            for eid, ecore in canon_core.items():
                if ecore and ecore == pcore:
                    offer(eid, 95, "exact_core")

        # 2. Exact alias.
        for eid in exact_index.get(pt, set()):
            offer(eid, 80, "exact_alias")

        # 3. PARENT NAME INSIDE A SUBSIDIARY NAME. This is the case that was
        #    missing entirely, and it is the common one: Chickasaw Nation
        #    Industries, Seneca Gaming Corporation, Jamul Indian Village
        #    Development Corporation all name their parent outright.
        #    Score by how much of the party string the entity name accounts
        #    for, so the LONGER entity name wins - "Navajo Nation" prefers
        #    Navajo over Ramah Navajo Chapter.
        for t, eids in canon_index.items():
            distinctive = [x for x in t if x not in GENERIC]
            if not distinctive:
                continue
            if set(t).issubset(pset):
                # Full entity name present inside the party string.
                score = 60 + len(t) * 3 + len(distinctive) * 2
                for eid in eids:
                    offer(eid, score, "parent_name_in_subsidiary")

        # 4. Alias containment, weakest, still requires two distinctive tokens.
        if not scored:
            for t, eids in exact_index.items():
                distinctive = [x for x in t if x not in GENERIC]
                if len(distinctive) < 2:
                    continue
                if set(t).issubset(pset) or pset.issubset(set(t)):
                    for eid in eids:
                        offer(eid, 30 + len(distinctive), "alias_containment")

        # A party string that names a CORPORATION must prefer a corporation.
        # Without this, the village government outranks its own village
        # corporation whenever both carry the same core tokens.
        is_corp = bool(re.search(r"\b(corporation|corp|inc|incorporated|company|llc)\b",
                                 party, re.IGNORECASE))
        if is_corp:
            for eid in list(scored):
                s, how = scored[eid]
                if eid in anc_ids:
                    scored[eid] = (s + 10, how + "+corp_form")
                elif str(eid).startswith(("AKNF", "TRBF", "TRBS")):
                    # A government entity matched by a corporate name string.
                    scored[eid] = (s - 15, how + "-govt_for_corp_name")

        if scored:
            best = max(s for s, _ in scored.values())
            # A clear winner wins. A genuine tie goes to Elijah.
            top = [e for e, (s, _) in scored.items() if s == best]
            hits = set(top)
            method = scored[top[0]][1] if len(top) == 1 else "tied"
        else:
            hits, method = set(), ""

        row = {
            "native_party": party, "n_deals": n,
            "source_files": " | ".join(sorted(where[party])),
            "n_candidates": len(hits),
            "candidate_ids": " | ".join(sorted(hits)),
            "candidate_names": " | ".join(sorted(names.get(e, "") for e in hits)),
            "match_method": method,
        }
        if len(hits) == 1:
            row["proposed_tribe_id"] = next(iter(hits))
            row["proposed_name"] = names.get(row["proposed_tribe_id"], "")
            matched.append(row)
        else:
            row["question"] = (
                f"Which entity is '{party}'?" if len(hits) > 1
                else f"'{party}' matched no spine entity. Which is it, or is it non-Native?")
            row["YOUR_RULING"] = ""
            queue.append(row)

    write_csv(CLEAN / "deals_party_matches.csv", matched,
              ["native_party", "proposed_tribe_id", "proposed_name", "n_deals",
               "match_method", "source_files"])
    queue.sort(key=lambda r: -r["n_deals"])
    write_csv(REVIEW / f"deals_party_queue_{TODAY}.csv", queue,
              ["native_party", "n_deals", "n_candidates", "candidate_ids",
               "candidate_names", "source_files", "question", "YOUR_RULING"])

    amb = sum(1 for r in queue if r["n_candidates"] > 1)
    print("\n=== SUMMARY ===")
    print(f"  parties auto-matched (1 candidate) : {len(matched):,}")
    print(f"  ambiguous (2+ candidates)          : {amb:,}")
    print(f"  no match at all                    : {len(queue)-amb:,}")
    print(f"  deals covered by auto-matches      : "
          f"{sum(r['n_deals'] for r in matched):,} of {sum(parties.values()):,}")
    print("\n  Ruling these unlocks the ownership-event ledger into the entity-year panel.")


if __name__ == "__main__":
    main()
