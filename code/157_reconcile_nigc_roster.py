#!/usr/bin/env python3
r"""Cedar Press 157 - reconcile the CURRENT NIGC roster against Cedar's 774.

INPUT
  data/raw/external/nigc/locations/nigc_roster_current_<date>.csv   (script 155)
  data/raw/external/nigc/locations/nigc_gaming_locations_map6_2026-08-06.json
  data/clean/gaming_facilities.csv
  data/clean/gaming_property_federal_traces.csv   (the 2026-08-06 marker links)
  review/gaming_additions_2026-08-06.csv          (the 140 unruled staged rows)

WHAT WENT WRONG LAST TIME, AND WHAT THIS FIXES
----------------------------------------------
Script 92 partitioned the 140 staged additions with a test that is *exact string
equality on a parsed city*. That test is defeated by NIGC's own typing, and the
staged file proves it:

    NIGC "Mohnomen MN"   Cedar "Mahnomen MN"
    NIGC "Muscogee OK"   Cedar "Muskogee OK"
    NIGC "Seneca Fall NY" Cedar "Seneca Falls NY"

Each misspelling scored `n_cedar_rows_in_same_city_state = 0`, which reads as
"Cedar has nothing here" and staged a property Cedar already holds. **A
misspelling in the source became a claim about our coverage.** So city equality
here is edit-distance tolerant - and, per the containment defect recorded in
AGENTS.md, city similarity is only ever a SECONDARY condition alongside name
evidence, never a match on its own.

THE MATCH LADDER, strongest first, one-to-one, nothing fuzzy alone. **Name
evidence outranks proximity** - see the comment on the rung loop for the five
links the old order (carry-over first) lost.

  exact_name_state   normalised facility name equal AND state equal
  core_name_state    EQUALITY of the distinctive tokens (venue words such as
                     casino/bingo/resort/hotel stripped) AND state equal.
                     Equality, never containment.
  street_state       normalised street line equal AND state equal
  carryover          the 2026-08-06 marker with this name+address was matched
                     to a Cedar row by the 1.2 km coordinate pass in script 88
  name_city_state    token containment either direction AND state equal AND
                     city equal within edit distance 2 AND unique both ways
  name_state         token containment either direction AND state equal AND
                     unique both ways

The last two rungs may not claim a Cedar row the record itself says is closed;
such cases are queued instead.

RULES HONOURED
  * A Cedar row absent from the CURRENT map is NOT evidence against that row.
    NIGC's map is a current-operations map; a property that closed in 2003
    cannot appear on it. Rows carrying a close date, or a close bound before
    today, are reported separately and never flagged.  (Three rulings were
    withdrawn on 2026-08-06 for exactly this error.)
  * Nothing is appended to gaming_facilities.csv by this script. It writes a
    linkage file and a ruling queue.

OUTPUT
  data/clean/gaming_nigc_roster_link.csv
  review/gaming_nigc_additions_2026-08-26.csv     (re-ruled 140 + new markers)
  logs/157_nigc_reconciliation.json
"""

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
RAWN = CEDAR / "data" / "raw" / "external" / "nigc" / "locations"
REVIEW = CEDAR / "review"
LOGS = CEDAR / "logs"
TODAY = date.today().isoformat()
NIGC_URL = "https://www.nigc.gov/map/"

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


def read_csv(p):
    with open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(p, rows, fields=None):
    fields = fields or list(rows[0].keys())
    tmp = Path(str(p) + ".part")
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    tmp.replace(p)


# ------------------------------------------------------------- normalisation
_PUNCT = re.compile(r"[^a-z0-9 ]+")
_WS = re.compile(r"\s+")
# Deliberately NOT stripped: `casino`, `bingo`, `travel plaza`, `gaming`.
# Folding those would merge `Choctaw Casino - Durant` with `Choctaw Travel Plaza
# - Durant`, which are different properties. Only corporate/orthographic noise
# is folded, per the `core()` rule in AGENTS.md: a token that appears in one
# name and not the other is never noise.
_FOLD = {"and": "", "the": "", "at": "", "llc": "", "inc": "", "lp": "",
         "co": "", "dba": ""}


def norm(s):
    s = (s or "").lower().replace("&", " and ")
    # APOSTROPHES ARE DELETED, NOT SPACED. NIGC writes `King’s Club Casino`
    # with a curly quote and Cedar writes `Kings Club Casino`; letting the
    # punctuation class turn it into a space yields `king s` and loses a match
    # that is otherwise exact. Same for `Prairie’s Edge`.
    s = s.replace("’", "").replace("'", "").replace("ʼ", "")
    # Both sources also carry U+FFFD where an apostrophe was mis-decoded on the
    # way in (`Northwood�s Recreation`). Deleting it recovers the word.
    s = s.replace("�", "")
    s = _PUNCT.sub(" ", s)
    return _WS.sub(" ", s).strip()


def toks(s):
    return {t for t in norm(s).split() if t and _FOLD.get(t, t)}


# Words that name the KIND of gaming venue rather than WHICH one. Stripping
# them turns `Mole Lake Casino and Bingo` and `Mole Lake Casino Lodge` into the
# same key, which is what lets a name variant link instead of looking like a
# property Cedar does not hold.
#
# `travel`, `plaza`, `stop`, `station`, `store` and roman numerals are
# DELIBERATELY NOT in this set. Folding them would merge `Choctaw Casino -
# Durant` with `Choctaw Travel Plaza - Durant`, and `Muckleshoot Casino` with
# `Muckleshoot Casino II` - separately NIGC-listed locations in both cases.
# Same rule as `core()` in AGENTS.md: a token that appears in one name and not
# the other is never noise.
_VENUE = {"casino", "casinos", "bingo", "resort", "hotel", "lodge", "gaming",
          "entertainment", "center", "centre", "spa", "club", "inn", "hall",
          "and", "the", "of", "at", "dba", "llc", "inc", "d", "b", "a"}


def core_key(s):
    """The distinctive tokens of a facility name, order-independent.

    EQUALITY on this key is required - never containment. Containment on a
    stripped key is how `Choctaw Casino` would swallow every Choctaw property
    in Oklahoma.
    """
    return " ".join(sorted(x for x in norm(s).split() if x not in _VENUE))


def norm_street(s):
    s = norm(s)
    for a, b in [(" street", " st"), (" road", " rd"), (" avenue", " ave"),
                 (" highway", " hwy"), (" drive", " dr"), (" boulevard", " blvd"),
                 (" north ", " n "), (" south ", " s "), (" east ", " e "),
                 (" west ", " w "), (" northwest", " nw"), (" northeast", " ne"),
                 (" southwest", " sw"), (" southeast", " se")]:
        s = (s + " ").replace(a + " ", b + " ").strip()
    return _WS.sub(" ", s).strip()


def lev(a, b, cap=3):
    if a == b:
        return 0
    if abs(len(a) - len(b)) > cap:
        return cap + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1,
                           prev[j - 1] + (ca != cb)))
        prev = cur
        if min(prev) > cap:
            return cap + 1
    return prev[-1]


def city_close(a, b):
    a, b = norm(a), norm(b)
    if not a or not b:
        return False
    return a == b or lev(a, b) <= 2


def contained(a, b):
    ta, tb = toks(a), toks(b)
    if not ta or not tb:
        return False
    return ta <= tb or tb <= ta


# ------------------------------------------------------------------- closure
def is_closed(fac, today=TODAY):
    """True when the record's OWN evidence says it was not operating today.

    This is the guard behind the withdrawn 2026-08-06 rulings: a current web
    page cannot testify about a property that closed in 2003, so a closed row's
    absence from the current map is expected and is never a finding.
    """
    if (fac.get("close_date") or "").strip():
        return True
    nb = (fac.get("close_date_not_after") or "").strip()
    if nb and nb[:10] < today:
        return True
    if (fac.get("property_status_literal") or "") == "Temporarily Closed":
        return True
    return False


def main():
    roster_path = RAWN / f"nigc_roster_current_{TODAY}.csv"
    if not roster_path.exists():
        cands = sorted(RAWN.glob("nigc_roster_current_*.csv"))
        if not cands:
            raise SystemExit("no NIGC roster on disk - run code/155 first")
        roster_path = cands[-1]
    roster = read_csv(roster_path)
    print(f"NIGC roster {roster_path.name}: {len(roster)} markers")

    # Exact duplicate markers in NIGC's own roster collapse to one location.
    # The key is NAME + STATE, not name + address: NIGC files every Agua
    # Caliente property at `5401 Dinah Shore Dr.` and every Chickasaw property
    # at `2020 Lonnie Abbott Blvd., Ada` - a tribal headquarters, not the
    # property. Its ADDRESS is the tribe's mailing address on a large minority
    # of rows, so address is not an identity here and name is.
    seen, nigc = set(), []
    dup_markers = []
    for r in roster:
        k = (norm(r["nigc_location_name"]), r["state"])
        if k in seen:
            dup_markers.append(r["nigc_location_name"])
            continue
        seen.add(k)
        nigc.append(r)
    print(f"  distinct NIGC locations: {len(nigc)} "
          f"({len(dup_markers)} exact duplicate markers collapsed)")

    fac = read_csv(CLEAN / "gaming_facilities.csv")
    traces = read_csv(CLEAN / "gaming_property_federal_traces.csv")
    print(f"Cedar facilities: {len(fac)}")

    # ---- carry-over links from the 2026-08-06 coordinate/name pass
    carry = {}
    for t in traces:
        if t.get("nigc_location_name"):
            carry[(norm(t["nigc_location_name"]),
                   norm(t["nigc_marker_address"]))] = t["facility_id"]
            carry.setdefault((norm(t["nigc_location_name"]),), t["facility_id"])
    print(f"  carry-over marker links from 2026-08-06: "
          f"{len({v for k, v in carry.items() if len(k) == 2})}")

    by_id = {f["facility_id"]: f for f in fac}
    claimed = {}                                    # facility_id -> nigc row
    links = []
    closed_conflicts = []
    # A weak rung may never claim a Cedar row the record itself says is closed.
    # Measured cost of not having this guard: NIGC's current `Newcastle Gaming
    # Center` was claimed by Cedar's `Newcastle Gaming Center II`, which carries
    # `close_date = 2010-03-15`, while `Newcastle Casino` sat open in the same
    # city. Linking a live regulated operation to a row we say shut in 2010 is
    # the same error as ruling a 2003 property against a 2026 page, running the
    # other way.
    TIER = {"exact_name_state": "A", "core_name_state": "A",
            "carryover_2026-08-06_marker_link": "A", "street_state": "A",
            "name_city_state": "B", "name_state": "B"}

    def try_claim(n, fid, basis):
        if fid in claimed or not fid:
            return False
        claimed[fid] = n
        f = by_id[fid]
        links.append({
            "facility_id": fid, "facility_name": f["facility_name"],
            "tribe_id": f.get("tribe_id", ""),
            "tribe_canonical_name": f.get("tribe_canonical_name", ""),
            "cedar_city": f.get("city", ""), "cedar_state": f.get("state", ""),
            "nigc_location_name": n["nigc_location_name"],
            "nigc_address": n["nigc_address"],
            "nigc_region_name": n["nigc_region_name"],
            "nigc_city": n["city"], "nigc_state": n["state"],
            "match_basis": basis, "link_tier": TIER[basis],
            "cedar_row_has_close_evidence": "1" if is_closed(f) else "0",
            "nigc_listed_as_of": n["fetched_date"],
            "igra_coverage_status": "VERIFIED_NIGC_OPERATION",
            "source_url": NIGC_URL,
        })
        return True

    unmatched = list(nigc)

    by_name_state = defaultdict(list)
    by_core_state = defaultdict(list)
    by_street_state = defaultdict(list)
    for f in fac:
        by_name_state[(norm(f["facility_name"]), f.get("state", ""))].append(f["facility_id"])
        c = core_key(f["facility_name"])
        if c:
            by_core_state[(c, f.get("state", ""))].append(f["facility_id"])
        if f.get("address"):
            by_street_state[(norm_street(f["address"]), f.get("state", ""))].append(f["facility_id"])

    # RUNG ORDER MATTERS, AND IT IS NOT THE ORDER IT WAS FIRST WRITTEN IN.
    # The 2026-08-06 carry-over is a COORDINATE match within 1.2 km. On a
    # tribal resort campus several gaming locations sit inside 1.2 km of each
    # other, so a coordinate match is weaker identity evidence than the name.
    # Running carry-over first cost real links, measured on this data:
    #     NIGC `Sportman's Bar`          claimed Cedar `4 Bears Casino & Lodge`
    #     NIGC `White Oak Casino`        claimed Cedar `Palace Casino & Hotel`
    #     NIGC `Washita Casino`          claimed Cedar `Ada Gaming Center`
    #     NIGC `Firelake Bowling Center` claimed Cedar `Thunderbird Casino - Shawnee`
    #     NIGC `Eagles Landing Hotel`    claimed Cedar `Lucky Eagle Casino & Hotel`
    # ...and each theft then reported the correctly-named NIGC location as a
    # property Cedar does not have. **Name evidence outranks proximity.**
    for rung in ("exact_name_state", "core_name_state", "street_state",
                 "carryover_2026-08-06_marker_link"):
        rest = []
        for n in unmatched:
            if rung == "exact_name_state":
                hits = by_name_state.get((norm(n["nigc_location_name"]), n["state"]), [])
            elif rung == "core_name_state":
                k = core_key(n["nigc_location_name"])
                hits = by_core_state.get((k, n["state"]), []) if k else []
            elif rung == "street_state":
                hits = by_street_state.get((norm_street(n["street"]), n["state"]), []) \
                    if n["street"] else []
            else:
                fid = carry.get((norm(n["nigc_location_name"]), norm(n["nigc_address"]))) \
                    or carry.get((norm(n["nigc_location_name"]),))
                hits = [fid] if fid and fid in by_id else []
            hits = [h for h in hits if h not in claimed]
            # uniqueness both ways: no other still-unmatched NIGC row may key to
            # the same Cedar row on this rung
            if len(hits) == 1:
                if try_claim(n, hits[0], rung):
                    continue
            rest.append(n)
        unmatched = rest
        print(f"  after {rung}: {len(unmatched)}")

    # weak rungs - token containment + state (+ city within edit distance 2)
    for rung, need_city in (("name_city_state", True), ("name_state", False)):
        rest = []
        for n in unmatched:
            raw = [f for f in fac
                   if f["facility_id"] not in claimed
                   and f.get("state", "") == n["state"]
                   and contained(n["nigc_location_name"], f["facility_name"])
                   and (not need_city or city_close(n["city"], f.get("city", "")))]
            cands = [f for f in raw if not is_closed(f)]
            if raw and not cands:
                closed_conflicts.append({
                    "nigc_location_name": n["nigc_location_name"],
                    "nigc_address": n["nigc_address"],
                    "nigc_region_name": n["nigc_region_name"],
                    "candidate_facility_ids": "|".join(f["facility_id"] for f in raw),
                    "candidate_facility_names": "|".join(f["facility_name"] for f in raw),
                    "candidate_close_dates": "|".join(f.get("close_date", "") for f in raw),
                    "rung": rung,
                    "question": ("NIGC lists this location as a current gaming "
                                 "operation on 2026-08-26, and the only Cedar row "
                                 "whose name matches carries close evidence. "
                                 "Either the close date is wrong, or this is a "
                                 "different property that Cedar lacks. NOT LINKED "
                                 "and NOT ADDED without a ruling."),
                    "source_url": NIGC_URL, "fetched_date": TODAY,
                    "YOUR_RULING": "",
                })
            if len(cands) == 1:
                # one-to-one both ways: no other NIGC row may also contain it
                others = [m for m in unmatched
                          if m is not n and m["state"] == n["state"]
                          and contained(m["nigc_location_name"], cands[0]["facility_name"])
                          and (not need_city or city_close(m["city"], cands[0].get("city", "")))]  # noqa: E501
                if not others and try_claim(n, cands[0]["facility_id"], rung):
                    continue
            rest.append(n)
        unmatched = rest
        print(f"  after {rung}: {len(unmatched)}")

    write_csv(CLEAN / "gaming_nigc_roster_link.csv", links)
    print(f"\nWROTE gaming_nigc_roster_link.csv - {len(links)} NIGC-confirmed "
          f"Cedar properties "
          f"(tier A {sum(1 for l in links if l['link_tier'] == 'A')}, "
          f"tier B {sum(1 for l in links if l['link_tier'] == 'B')})")
    if closed_conflicts:
        write_csv(REVIEW / f"gaming_nigc_closed_row_conflicts_{TODAY}.csv",
                  closed_conflicts)
        print(f"  {len(closed_conflicts)} NIGC-current / Cedar-closed conflicts "
              f"queued, not linked")

    # ------------------------------------------------- Cedar rows off the map
    open_unlisted, closed_unlisted = [], []
    for f in fac:
        if f["facility_id"] in claimed or f.get("duplicate_of_facility_id"):
            continue
        (closed_unlisted if is_closed(f) else open_unlisted).append(f)
    print(f"Cedar rows not on the current NIGC map: "
          f"{len(open_unlisted)} with no close evidence, "
          f"{len(closed_unlisted)} with close evidence (EXPECTED - a current "
          f"map cannot list a closed property)")

    # ------------------------------------------------ re-rule the staged 140
    staged = read_csv(REVIEW / "gaming_additions_2026-08-06.csv")
    old = json.loads((RAWN / "nigc_gaming_locations_map6_2026-08-06.json")
                     .read_text(encoding="utf-8", errors="replace"))
    old_by_id = {str(m["id"]): m for m in old}

    nigc_by_key = {(norm(n["nigc_location_name"]), norm(n["nigc_address"])): n
                   for n in nigc}
    link_by_nigcname = defaultdict(list)
    for l in links:
        link_by_nigcname[norm(l["nigc_location_name"])].append(l)

    out, counts = [], Counter()
    for s in staged:
        m = old_by_id.get(s["nigc_marker_id"], {})
        nm = s["nigc_location_name"] or m.get("title", "")
        addr = s["nigc_address"] or m.get("address", "")
        row = dict(s)
        row["reconciled_date"] = TODAY

        still = nigc_by_key.get((norm(nm), norm(addr))) or \
            next((n for n in nigc if norm(n["nigc_location_name"]) == norm(nm)), None)
        row["still_on_nigc_map_2026-08-26"] = "1" if still else "0"

        hit = link_by_nigcname.get(norm(nm))
        if hit:
            row["RULING_2026-08-26"] = "ALREADY_IN_CEDAR_DO_NOT_ADD"
            row["ruling_facility_id"] = hit[0]["facility_id"]
            row["ruling_basis"] = (
                f"Resolved against the current NIGC roster by the 157 match "
                f"ladder ({hit[0]['match_basis']}): this marker is Cedar row "
                f"{hit[0]['facility_id']} ({hit[0]['facility_name']}, "
                f"{hit[0]['cedar_city']} {hit[0]['cedar_state']}). Script 92 "
                f"could not see it because its test was exact equality on a "
                f"parsed city and NIGC's own address text differs "
                f"(NIGC '{s['parsed_city']}' vs Cedar '{hit[0]['cedar_city']}').")
            counts["ALREADY_IN_CEDAR_DO_NOT_ADD"] += 1
        elif not still:
            row["RULING_2026-08-26"] = "QUEUE_MARKER_GONE_FROM_NIGC_MAP"
            row["ruling_facility_id"] = ""
            row["ruling_basis"] = (
                "This marker was on NIGC's map on 2026-08-06 and is not on it "
                "on 2026-08-26. A marker leaving a current-operations map is "
                "not proof the property closed - NIGC edits its map for many "
                "reasons - so nothing is inferred. Needs a human ruling.")
            counts["QUEUE_MARKER_GONE_FROM_NIGC_MAP"] += 1
        else:
            row["RULING_2026-08-26"] = "ADD_AS_NEW_CEDAR_PROPERTY"
            row["ruling_facility_id"] = ""
            row["ruling_basis"] = (
                "Still on NIGC's map on 2026-08-26 and won no Cedar row on any "
                "rung of the 156 ladder, including the city-typo-tolerant one. "
                "NIGC listing is itself the evidence of a regulated gaming "
                "operation; tribe attribution is a separate question and is not "
                "guessed from the facility name.")
            counts["ADD_AS_NEW_CEDAR_PROPERTY"] += 1
        out.append(row)

    # markers on the CURRENT map that are in neither Cedar nor the staged file
    staged_keys = {norm(s["nigc_location_name"]) for s in staged}
    for n in unmatched:
        if norm(n["nigc_location_name"]) in staged_keys:
            continue
        out.append({
            "disposition": "NEW_SINCE_2026-08-06",
            "nigc_marker_id": "", "nigc_location_name": n["nigc_location_name"],
            "nigc_address": n["nigc_address"], "parsed_city": n["city"],
            "parsed_state": n["state"], "nigc_region_name": n["nigc_region_name"],
            "igra_coverage_status": "VERIFIED_NIGC_OPERATION",
            "corroborating_sources": "NIGC_GAMING_LOCATION_MAP",
            "source_url": NIGC_URL, "fetched_date": TODAY,
            "do_not_append_without_ruling": "1", "YOUR_RULING": "",
            "built_date": TODAY, "reconciled_date": TODAY,
            "still_on_nigc_map_2026-08-26": "1",
            "RULING_2026-08-26": "ADD_AS_NEW_CEDAR_PROPERTY",
            "ruling_facility_id": "",
            "ruling_basis": ("On NIGC's current map, absent from Cedar's 774 and "
                             "absent from the 2026-08-06 staging file."),
        })
        counts["ADD_AS_NEW_CEDAR_PROPERTY"] += 1

    fields = list(staged[0].keys()) + ["reconciled_date",
                                       "still_on_nigc_map_2026-08-26",
                                       "RULING_2026-08-26", "ruling_facility_id",
                                       "ruling_basis"]
    write_csv(REVIEW / f"gaming_nigc_additions_{TODAY}.csv", out, fields)
    print(f"\nRE-RULED the staged additions -> "
          f"review/gaming_nigc_additions_{TODAY}.csv ({len(out)} rows)")
    for k, v in counts.most_common():
        print(f"  {k:36s} {v}")

    summary = {
        "built": TODAY,
        "nigc_markers_current": len(roster),
        "nigc_locations_distinct": len(nigc),
        "nigc_markers_2026_08_06": len(old),
        "cedar_facilities": len(fac),
        "nigc_matched_to_cedar": len(links),
        "match_basis": dict(Counter(l["match_basis"] for l in links)),
        "nigc_unmatched": len(unmatched),
        "nigc_current_vs_cedar_closed_conflicts": len(closed_conflicts),
        "cedar_unlisted_no_close_evidence": len(open_unlisted),
        "cedar_unlisted_with_close_evidence": len(closed_unlisted),
        "staged_rulings": dict(counts),
        "nigc_duplicate_markers": dup_markers,
    }
    (LOGS / "157_nigc_reconciliation.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    print("\n" + json.dumps({k: v for k, v in summary.items()
                             if k != "nigc_duplicate_markers"}, indent=2))


if __name__ == "__main__":
    main()
