#!/usr/bin/env python3
r"""Cedar Press 88 — how many independent federal traces does each property leave?

Elijah, 2026-08-06:
    "if we cant link them to federal actions in registra and compact they are
     probably quirky properties like a gas station or something."

Elijah, 2026-08-06 (the correction that changed the schema):
    "the class ii and iii are tricky cuz at any time a tribe can change their
     status by swapping out their machines so its a necessary but not
     sufficient condition."

================================================================================
THE THREE RULES THIS SCRIPT IS BUILT AROUND
================================================================================

1. A COMPACT IS NECESSARY-BUT-NOT-SUFFICIENT IN BOTH DIRECTIONS.
   - Its PRESENCE does not prove the property operates Class III. A compact
     authorises; it does not observe. It is signed by a tribe and a state and
     says nothing about which building has which machines on which day.
   - Its ABSENCE does not prove the property is not gaming. **Class II gaming
     requires no tribal-state compact at all.** A bingo hall or card room
     running Class II only will legitimately have no compact and no Class III
     Federal Register approval and is still a real gaming operation.
   Therefore a compact trace may only ever RAISE a count. It can never lower
   one and it can never on its own move a row toward NOT_A_GAMING_PROPERTY.

2. GAMING CLASS IS NOT A PROPERTY ATTRIBUTE. It is a time-varying operational
   state. A tribe converts between Class II and Class III by changing what is
   on the floor; Class II bingo-based machines and Class III slots look alike to
   a visitor and can be swapped with no federal record generated. Oklahoma
   tribes have run Class II fleets specifically to stay outside compact
   revenue-sharing. **So no gaming class is assigned to any property here.**
   What is recorded instead is DATED OBSERVATIONS with sources:
       compact_in_force_as_of · nigc_listed_as_of · land_decision_date
   (This is also a further reason Cedar Press publishes no property-level
   revenue: Class II and Class III have materially different revenue profiles,
   the mix is unobservable per property, and it can change without notice.
   Anyone modelling property GGR off machine counts is assuming a class mix
   they cannot know.)

3. A TRIBE-LEVEL TRACE CANNOT CONFIRM A PROPERTY.
   A compact, a Federal Register compact approval and a BIA gaming-land
   decision are all keyed to a TRIBE. A tribe operating six casinos generates
   one compact. Joining that compact to all six rows says nothing about any of
   them, and joining it to a golf course owned by the same tribe says nothing
   either. `docs/GAMING_TEMPORAL_BUILD_LOG.md` §3 already measured this: of
   thirteen facilities that matched a BIA land decision on (tribe, state),
   TWELVE were rejected, including one whose bound would have asserted that
   Muckleshoot Casino could not have opened before 2008 when it had operated
   since the 1990s.
   So `federal_trace_count` counts PROPERTY-LEVEL traces only.
   Tribe-level traces are carried in their own columns and their own count,
   are never summed into `federal_trace_count`, and are labelled on every row.

   THE VALIDATION TEST FOR THIS DESIGN is the 16 rows literally named
   `No casino`, `No casino currently`, `Tribal admin only - no casino`. Several
   of those tribes DO hold compacts — Las Vegas Paiute and Pyramid Lake Paiute
   both appear in Federal Register compact notices. If a compact counted as a
   property trace, a row that says in its own name that there is no casino
   would score two. It scores zero, and the tribe-level columns show why.

================================================================================

Reads   data/clean/gaming_facilities.csv                (774, never modified)
        review/nigc_roster_diff_2026-08-06.csv          property<->NIGC marker
        data/raw/external/nigc/locations/nigc_gaming_locations_map6_2026-08-06.json
        data/clean/federal_actions.csv                  FR compact approvals
        data/clean/gaming_land_decisions.csv            BIA / IGRA s.20
        data/clean/compacts.csv, compact_events.csv
        data/clean/nigc_region_assignments.csv
        data/spine/cedar_entity_spine.csv
        code/33_apply_party_rulings.py                  resolve_entity — THE ONE
                                                        RESOLVER. No new matcher
                                                        is written anywhere here.

Writes  data/clean/gaming_property_federal_traces.csv   774 rows
        review/gaming_property_triage_<date>.csv        evidence per row
        review/gaming_series_breaks_<date>.csv          comparability note
"""

import csv
import importlib.util
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
RAW = CEDAR / "data" / "raw" / "external" / "nigc" / "locations"
TODAY = date.today().isoformat()

csv.field_size_limit(2 ** 31 - 1)

NIGC_MAP_URL = "https://www.nigc.gov/map/"
BIA_GLD_URL = "https://www.bia.gov/as-ia/oig/gaming-land-decisions"
FR_DOC_URL = "https://www.federalregister.gov/documents/{}"


# ------------------------------------------------------------------ the resolver
# AGENTS.md: "code/33_apply_party_rulings.py holds the ONE resolver. Import
# resolve_entity; never write another name matcher."
_spec = importlib.util.spec_from_file_location(
    "m33", str(CEDAR / "code" / "33_apply_party_rulings.py"))
M33 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M33)
resolve_entity = M33.resolve_entity


def read_csv(p):
    p = Path(p)
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


# =============================================================== FR compact trace
#
# The Federal Register compact-approval notice is a genuinely independent
# federal trace from the BIA compact index in `compacts.csv`: the index is a
# BIA web table, the notice is the statutory publication IGRA s.11(d)(8)(D)
# requires. They agree often, which is a verification, and where only one fires
# that is recorded too.
#
# The tribe is named IN THE DOCUMENT, so feeding that name to resolve_entity is
# the sanctioned use of the containment tier under AGENTS.md: "containment may
# be used only to resolve an owner ALREADY NAMED IN EVIDENCE — never to detect a
# match, and never to key a dollar." Nothing here keys a dollar.

COMPACT_DOC_RE = re.compile(
    r"tribal[- ]state (?:class iii )?(?:gaming )?compact"
    r"|class iii gaming compact"
    r"|approved tribal-state compact", re.I)

# Ordered. The first that yields a plausible name wins; nothing is guessed.
TRIBE_PATS = [
    re.compile(r"\bBetween\s+(?:the\s+)?(.{4,90}?)\s+and the State of\b", re.I),
    re.compile(r"\bapproved\s+(?:the\s+)?(.{4,90}?)\s+and the State of\b", re.I),
    re.compile(r"\(\s*(.{4,90}?)\s+and the State of\b", re.I),
    re.compile(r"^Indian Gaming[;,]\s*(.{4,80}?)\s*(?:,\s*[A-Z]{2})?\s*(?:;|$)"),
]

BOILER_LEAD = re.compile(
    r"^(?:Tribal-State (?:Class III )?(?:Gaming )?Compact(?:s)?"
    r"(?: Amendment[s]?)?(?: for Regulation of Class III Gaming)?\s*"
    r"|Amendment [IVXLC0-9]+ to the\s*"
    r"|an? \s*)", re.I)

# A candidate that is boilerplate, or that names more than one tribe, is
# REFUSED rather than resolved to whichever tribe happens to match. A notice
# covering "three Tribes in California" names no tribe this script may use.
REFUSE_CAND = re.compile(
    r"taking effect|following|tribes in |^\s*two |^\s*three |^\s*notice"
    r"|pueblos of|, the |^\s*and\b", re.I)


def fr_compact_traces(spine):
    """(tribe_id) -> list of FR compact-approval documents naming that tribe."""
    by_tribe = defaultdict(list)
    scanned = named = resolved = 0
    unresolved = Counter()
    refused = Counter()
    for row in read_csv(CLEAN / "federal_actions.csv"):
        title = (row.get("title") or "").strip()
        abstract = (row.get("abstract") or "").strip()
        if not COMPACT_DOC_RE.search(title + " " + abstract):
            continue
        scanned += 1
        cand = None
        for pat in TRIBE_PATS:
            m = pat.search(title) or pat.search(abstract)
            if not m:
                continue
            c = BOILER_LEAD.sub("", m.group(1).strip().strip(".,")).strip()
            if 3 < len(c) < 90:
                cand = c
                break
        if not cand:
            continue
        if REFUSE_CAND.search(cand):
            refused[cand] += 1
            continue
        named += 1
        tid, canon, how = resolve_entity(cand, spine)
        if not tid:
            unresolved[f"{cand} :: {how}"] += 1
            continue
        resolved += 1
        by_tribe[tid].append({
            "document_number": row.get("document_number", ""),
            "publication_date": row.get("publication_date", ""),
            "effective_on": row.get("effective_on", ""),
            "title": title,
            "url": row.get("html_url") or FR_DOC_URL.format(
                row.get("document_number", "")),
            "tribe_string_in_document": cand,
            "resolve_how": how,
        })
    print(f"  FR compact-approval documents scanned      : {scanned:,}")
    print(f"  ... a tribe name extractable from the text : {named:,}")
    print(f"  ... resolved to a spine entity             : {resolved:,}")
    print(f"  ... refused as multi-tribe or boilerplate  : {sum(refused.values()):,}")
    print(f"  ... named but unresolved (held, not guessed): {sum(unresolved.values()):,}")
    return by_tribe, unresolved, refused


# ================================================================== main build

# IGRA s.20 (25 U.S.C. 2719) exception vocabulary, as BIA's Office of Indian
# Gaming prints it in its own index. EVERY row of gaming_land_decisions.csv is a
# s.20 determination — that index IS the s.20 index. So an "IGRA s.20
# determination" is NOT an independent trace from a "BIA gaming land decision";
# they are one record read two ways, and counting both would double-count a
# single federal action. The exception is recorded on the same record instead.
S20_EXCEPTION = {
    "Two-Part Secretarial Determination": "25 USC 2719(b)(1)(A)",
    "Settlement of a Land Claim": "25 USC 2719(b)(1)(B)(i)",
    "Initial Reservation": "25 USC 2719(b)(1)(B)(ii)",
    "Restored Lands": "25 USC 2719(b)(1)(B)(iii)",
    "Within or Contiguous to Reservation Boundaries": "25 USC 2719(a)(1)",
    "Oklahoma - Within Former Reservation Boundaries": "25 USC 2719(a)(2)(A)(i)",
    "Within Last Recognized Reservation": "25 USC 2719(a)(2)(A)(ii)",
}

# Narrow, evidence-backed disqualifiers. NOT a name rule for "travel plaza",
# "smoke shop" or "trading post" — GAMING_TEMPORAL_BUILD_LOG.md sect.3 and
# AGENTS.md both record that Choctaw Travel Plaza Casino Too, Wewoka Trading
# Post Casino and Watonga Bingo and Smoke Shop demonstrably DO host gaming, and
# sect.9.5 records three rulings withdrawn for exactly this over-reach. Golf is
# the one name class ruled non-gaming one row at a time (Lake of Isles, Peoria
# Ridge, Singing Hills, Pala Mesa) and it is the only one used here.
DENIES_CASINO_RE = re.compile(r"\bno casino\b|\bno gaming\b|tribal admin only", re.I)
GOLF_RE = re.compile(r"\bgolf\b|\blinks\b", re.I)
STUB_RE = re.compile(r"\bsee\s+\w|actual\s+(?:nd|ia|ca|ok)\b", re.I)

CAPACITY_COLS = ["gaming_machines", "table_games", "poker_tables", "bingo_seats"]


NIGC_ADDR_RE = re.compile(r",\s*([^,]+?)\s+([A-Z]{2})\s+\d{5}(?:-\d{4})?\s*$")


def nigc_city_state(addr):
    """Read city and state out of an NIGC marker address.

    NIGC prints "street, City ST ZIP". This parses that shape and nothing else;
    an address that does not have it yields ("", "") rather than a guess.
    """
    m = NIGC_ADDR_RE.search((addr or "").strip())
    if not m:
        return "", ""
    return m.group(1).strip().lower(), m.group(2).strip().upper()


def num(v):
    try:
        return float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return 0.0


def main():
    print("=== Cedar Press 88: gaming property federal traces ===\n")

    spine = read_csv(SPINE / "cedar_entity_spine.csv")
    fac = read_csv(CLEAN / "gaming_facilities.csv")
    print(f"spine entities : {len(spine):,}")
    print(f"facilities     : {len(fac):,}  (read-only; not one row is modified)\n")

    # --- property-level: the NIGC gaming location map -----------------------
    diff = read_csv(REVIEW / "nigc_roster_diff_2026-08-06.csv")
    nigc_by_fac = {}
    for d in diff:
        if d["outcome"] == "MATCHED" and d["facility_id"]:
            nigc_by_fac[d["facility_id"]] = d
    print(f"NIGC map matches (property-level): {len(nigc_by_fac):,}")

    # the marker JSON supplies the marker's own address/region, so the trace
    # carries NIGC's record and not our restatement of it
    import json
    markers = {}
    mj = RAW / "nigc_gaming_locations_map6_2026-08-06.json"
    if mj.exists():
        for m in json.load(open(mj, encoding="utf-8")):
            markers[str(m.get("id"))] = m
    print(f"NIGC marker JSON: {len(markers):,} locations\n")

    # nigc_listed_as_of — the date the marker set was retrieved. NIGC's map
    # carries no per-marker date, so the only honest as-of is the pull date.
    nigc_fetched = ""
    for d in diff:
        if d.get("fetched_date"):
            nigc_fetched = d["fetched_date"]
            break

    # ------------------------------------------------------------------------
    # THE CEILING ON `trace_nigc_gaming_location_map = 0`
    # ------------------------------------------------------------------------
    # The roster match is DETERMINISTIC AND ONE-TO-ONE (nearest-first greedy on
    # coordinates within 1.2 km in the same state, then identical normalised
    # name in the same state). That produces false zeros two ways, and both were
    # found by inspecting the output rather than by reasoning about it:
    #
    #   (a) EXCLUSIVITY. Where Cedar holds two rows for one property, only one
    #       can claim the marker. `CCP-544900 Casino Del Sol` matched; its twin
    #       `VP-0041 Casino Del Sol Resort` could not, and scored zero.
    #   (b) MATCH MISS. `Barona Resort & Casino` (CCP-41700) scored ZERO federal
    #       traces of any kind — yet NIGC maps `Barona Valley Ranch Resort and
    #       Casino` at 1932 Wildcat Canyon Road, Lakeside CA. Same property.
    #       The names do not normalise equal and the coordinates did not come
    #       within 1.2 km. `Apache Gold Casino Resort` (CCP-86600) is the same
    #       failure against NIGC's `Apache Gold Casino`.
    #
    # So a zero here means "this row did not win a marker", NOT "this property
    # leaves no federal trace". A LEAD column records where an unmatched NIGC
    # marker sits in this row's own city and state. That key is exact string
    # equality on city and state — deterministic, not fuzzy, and NOT a name
    # matcher. It is a lead for a human, never a match: it is excluded from
    # federal_trace_count and never changes a classification.
    # NIGC's marker addresses are structured "street, City ST ZIP", so the city
    # comes out by parsing the field's own shape. That is reading a structured
    # field, not matching a name.
    unmatched_by_place = defaultdict(list)
    parsed = 0
    for d in diff:
        if d["outcome"] != "IN_NIGC_NOT_IN_CEDAR":
            continue
        city, st = nigc_city_state(d.get("nigc_address", ""))
        st = st or (d.get("state") or "").strip().upper()
        if city and st:
            parsed += 1
            unmatched_by_place[(city, st)].append(d)
    print(f"unmatched NIGC markers with a parseable (city,state): "
          f"{parsed:,} of {sum(1 for d in diff if d['outcome']=='IN_NIGC_NOT_IN_CEDAR'):,}")

    # ------------------------------------------------------------------------
    # PROPERTY-LEVEL, NON-FEDERAL: dated gaming-equipment observations
    # ------------------------------------------------------------------------
    # `gaming_facility_metrics.csv` carries 12,416 gaming_machines, 5,356
    # table_games, 2,988 poker_tables and 2,530 bingo_seats observations, each
    # keyed to a facility_id and each carrying its own as_of_date. A dated
    # observation of slot machines AT a property is direct evidence that the
    # property gambles — stronger property-level evidence than any tribe-level
    # federal record, and it is why this column exists separately rather than
    # being folded into the federal count. It is a VENDOR observation (Casino
    # City), not a federal record, and is labelled so on every row.
    #
    # NOTE ON WHAT IS DELIBERATELY NOT READ: the same file carries
    # `implied_gaming_revenue`, `ok_exclusivity_fee_annual`,
    # `ct_slot_contribution_annual` and similar. NO DOLLAR IS READ FROM THIS
    # FILE. Cedar Press publishes no property-level revenue; NIGC publishes GGR
    # at region level only.
    EQUIP = {"gaming_machines", "table_games", "poker_tables", "bingo_seats"}
    equip = defaultdict(list)
    for m in read_csv(CLEAN / "gaming_facility_metrics.csv"):
        if m.get("metric") not in EQUIP or not m.get("facility_id"):
            continue
        try:
            v = float(str(m.get("value", "")).replace(",", "").strip())
        except (TypeError, ValueError):
            continue
        if v > 0:
            equip[m["facility_id"]].append(m)
    print(f"facilities with >=1 dated gaming-equipment observation: {len(equip):,}\n")

    # --- tribe-level: Federal Register compact approvals --------------------
    fr_by_tribe, fr_unresolved, fr_refused = fr_compact_traces(spine)
    print()

    # --- tribe-level: BIA gaming land decisions (= IGRA s.20) ---------------
    gld_by_tribe = defaultdict(list)
    for g in read_csv(CLEAN / "gaming_land_decisions.csv"):
        if g.get("tribe_id"):
            gld_by_tribe[g["tribe_id"]].append(g)

    # --- tribe-level: the BIA compact index ---------------------------------
    cmp_by_tribe = defaultdict(list)
    for c in read_csv(CLEAN / "compacts.csv"):
        if c.get("tribe_id"):
            cmp_by_tribe[c["tribe_id"]].append(c)
    cev_by_tribe = defaultdict(list)
    for c in read_csv(CLEAN / "compact_events.csv"):
        if c.get("tribe_id"):
            cev_by_tribe[c["tribe_id"]].append(c)

    # --- coverage status already established by the NIGC region build -------
    cov = {}
    for a in read_csv(CLEAN / "nigc_region_assignments.csv"):
        cov.setdefault(a["facility_id"], a)

    out, triage = [], []
    for f in fac:
        fid = f["facility_id"]
        tid = f.get("tribe_id") or ""
        name = f.get("facility_name") or ""

        # ---------- PROPERTY-LEVEL TRACE 1: the NIGC gaming location map ----
        d = nigc_by_fac.get(fid)
        mk = markers.get((d or {}).get("nigc_marker_id", "")) or {}
        t_nigc = 1 if d else 0

        # ---------- TRIBE-LEVEL TRACE: FR Class III compact approval --------
        frs = sorted(fr_by_tribe.get(tid, []),
                     key=lambda x: x["publication_date"] or "")
        t_fr = 1 if frs else 0

        # ---------- TRIBE-LEVEL TRACE: BIA gaming land / IGRA s.20 ----------
        glds = sorted(gld_by_tribe.get(tid, []),
                      key=lambda x: x.get("decision_date") or "")
        # An approved decision is the one that makes land gaming-eligible; a
        # Disapproved or Pending decision is a federal trace of an APPLICATION
        # and is recorded as such rather than as an eligibility.
        gld_ok = [g for g in glds if (g.get("decision_status") or "").lower() == "approved"]
        t_gld = 1 if glds else 0

        # ---------- TRIBE-LEVEL TRACE: the BIA compact index ----------------
        cps = sorted(cmp_by_tribe.get(tid, []),
                     key=lambda x: x.get("original_effective_date") or "")
        cevs = cev_by_tribe.get(tid, [])
        t_cmp = 1 if cps else 0

        # ---------- NIGC management contract approval -----------------------
        # Not held by this project. NIGC publishes approved management
        # contracts, but no retrieved file exists in data/raw/ and this session
        # could not add one (see the build log). Recorded as NOT SEARCHED
        # rather than as absent, because absence under a filter is a property
        # of the filter (AGENTS.md).
        t_mgmt = 0
        mgmt_status = "not_held_by_cedar_press_this_session"

        prop_traces = t_nigc
        tribe_traces = t_fr + t_gld + t_cmp

        # ---------- non-federal corroborator, clearly labelled --------------
        cap = {c: num(f.get(c)) for c in CAPACITY_COLS}
        obs = equip.get(fid, [])
        obs_dates = sorted(x.get("as_of_date", "") for x in obs if x.get("as_of_date"))
        obs_metrics = sorted({x["metric"] for x in obs})
        reports_capacity = 1 if (any(v > 0 for v in cap.values()) or obs) else 0

        # ---------- the NIGC match ceiling, as a lead only ------------------
        leads = [] if t_nigc else unmatched_by_place.get(
            ((f.get("city") or "").strip().lower(),
             (f.get("state") or "").strip().upper()), [])

        # ---------- classification ------------------------------------------
        absent_reason = (f.get("open_date_absent_reason") or "")
        dup_of = f.get("duplicate_of_facility_id") or ""
        denies = bool(DENIES_CASINO_RE.search(name))
        is_stub = bool(STUB_RE.search(name)) or "cross-reference stub" in absent_reason
        is_golf = bool(GOLF_RE.search(name))

        if denies or absent_reason.startswith("not a gaming facility"):
            cls = "PLACEHOLDER_ROW" if denies else "NOT_A_GAMING_PROPERTY"
            basis = ("The row's own facility_name asserts that the tribe operates "
                     "no casino. It is a roster placeholder, not a property."
                     if denies else
                     "Ruled `not a gaming facility` in the temporal build "
                     "(open_date_absent_reason), one row at a time against the "
                     "operator's own description.")
        elif dup_of or is_stub or "duplicate row" in absent_reason:
            cls = "DUPLICATE"
            basis = (f"Duplicate of {dup_of}. " if dup_of else "") + \
                    "A cross-reference stub or ruled duplicate; the property is " \
                    "held on another row. Retained, never deleted."
        elif "not a distinct gaming property" in absent_reason:
            cls = "DUPLICATE"
            basis = "Ruled not a distinct property in the temporal build."
        elif prop_traces >= 1:
            cls = "CONFIRMED_GAMING"
            basis = ("On NIGC's published gaming location map, matched "
                     f"{d.get('match_basis','')}. NIGC's universe covers Class II "
                     "AND Class III, so this confirms a gaming operation without "
                     "asserting any class.")
        elif is_golf and prop_traces == 0 and not reports_capacity:
            cls = "NOT_A_GAMING_PROPERTY"
            basis = ("A golf property with zero property-level federal traces and "
                     "no reported gaming capacity. Ruled by name only for golf, "
                     "which is the single name class this project has ruled "
                     "non-gaming one row at a time (Lake of Isles, Peoria Ridge, "
                     "Singing Hills, Pala Mesa).")
        elif reports_capacity:
            cls = "CONFIRMED_GAMING"
            what = ", ".join(f"{k}={int(v)}" for k, v in cap.items() if v > 0) \
                or ", ".join(obs_metrics)
            span = (f" observed {obs_dates[0]} to {obs_dates[-1]} across "
                    f"{len(obs)} dated observations") if obs_dates else ""
            basis = ("No property-level FEDERAL trace, but gaming equipment is "
                     f"observed AT this property: {what}{span}. That is a VENDOR "
                     "observation (Casino City), not a federal record, and is "
                     "counted in reports_gaming_capacity_non_federal rather than "
                     "in federal_trace_count. Absence from NIGC's map is not "
                     "evidence of no gaming: NIGC's universe is Class II and "
                     "Class III gaming ON INDIAN LANDS, so a tribally owned "
                     "property outside IGRA never appears there.")
        else:
            cls = "INSUFFICIENT_TRACE_REVIEW"
            basis = ("Zero property-level federal traces and no dated gaming-"
                     "equipment observation. NOT a finding that the property "
                     "does not gamble — a Class II hall needs no compact and no "
                     "Class III Federal Register approval, and NIGC's map omits "
                     "tribally owned properties operating outside IGRA. Needs a "
                     "human ruling.")
            if leads:
                cls = "INSUFFICIENT_TRACE_REVIEW"
                basis += (f" LEAD: {len(leads)} NIGC marker(s) that matched no "
                          f"Cedar row sit in this row's own city and state "
                          f"({'; '.join(x['nigc_location_name'] for x in leads)[:200]}). "
                          "The roster match is one-to-one and deterministic, so "
                          "this row may be the same property under a different "
                          "name. A lead for a human, NOT a match, and it changes "
                          "no count here.")

        if tribe_traces and cls in ("PLACEHOLDER_ROW", "NOT_A_GAMING_PROPERTY"):
            basis += (f" NOTE: {tribe_traces} TRIBE-level federal trace(s) fire on "
                      "this row's tribe. They are not evidence about this "
                      "property and are deliberately excluded from "
                      "federal_trace_count.")

        excluded = 1 if cls in ("PLACEHOLDER_ROW", "NOT_A_GAMING_PROPERTY",
                                "DUPLICATE") else 0

        first_fr = frs[0] if frs else {}
        first_gld = (gld_ok or glds or [{}])[0]
        first_cmp = cps[0] if cps else {}

        rec = {
            "facility_id": fid,
            "facility_name": name,
            "tribe": f.get("tribe", ""),
            "tribe_id": tid,
            "tribe_canonical_name": f.get("tribe_canonical_name", ""),
            "city": f.get("city", ""),
            "state": f.get("state", ""),
            "property_status": f.get("property_status", ""),
            "close_date": f.get("close_date", ""),
            "duplicate_of_facility_id": dup_of,

            # ---- PROPERTY-LEVEL ----
            "trace_nigc_gaming_location_map": t_nigc,
            "nigc_marker_id": (d or {}).get("nigc_marker_id", ""),
            "nigc_location_name": (d or {}).get("nigc_location_name", ""),
            "nigc_marker_address": mk.get("address", ""),
            "nigc_region_name": (d or {}).get("nigc_region_name", ""),
            "nigc_match_basis": (d or {}).get("match_basis", ""),
            "nigc_match_distance_m": (d or {}).get("match_distance_m", ""),
            "nigc_listed_as_of": nigc_fetched if t_nigc else "",
            "nigc_map_url": NIGC_MAP_URL if t_nigc else "",

            # ---- TRIBE-LEVEL ----
            "trace_fr_class_iii_compact_approval": t_fr,
            "fr_document_number": first_fr.get("document_number", ""),
            "fr_publication_date": first_fr.get("publication_date", ""),
            "fr_document_title": first_fr.get("title", ""),
            "fr_tribe_string_in_document": first_fr.get("tribe_string_in_document", ""),
            "fr_resolve_how": first_fr.get("resolve_how", ""),
            "fr_document_url": first_fr.get("url", ""),
            "fr_n_documents": len(frs),
            "fr_all_document_numbers": "|".join(
                x["document_number"] for x in frs)[:900],

            "trace_bia_gaming_land_decision": t_gld,
            "bia_decision_id": first_gld.get("decision_id", ""),
            "bia_decision_title": first_gld.get("decision_title", ""),
            "bia_decision_status": first_gld.get("decision_status", ""),
            "land_decision_date": first_gld.get("decision_date", ""),
            "igra_section20_exception": S20_EXCEPTION.get(
                first_gld.get("legal_theory", ""), first_gld.get("legal_theory", "")),
            "igra_section20_citation": S20_EXCEPTION.get(
                first_gld.get("legal_theory", ""), ""),
            "bia_decision_url": (first_gld.get("federal_register_url")
                                 or first_gld.get("source_url")
                                 or (BIA_GLD_URL if first_gld else "")),
            "bia_n_decisions": len(glds),

            "trace_tribal_state_compact": t_cmp,
            "compact_id": first_cmp.get("compact_id", ""),
            "compact_in_force_as_of": first_cmp.get("original_effective_date", ""),
            "compact_status": first_cmp.get("status", ""),
            "compact_url": (first_cmp.get("FR_notice_url")
                            or first_cmp.get("source_url", "")),
            "compact_n": len(cps),
            "compact_n_events": len(cevs),

            "trace_nigc_management_contract": t_mgmt,
            "nigc_management_contract_status": mgmt_status,

            # ---- counts ----
            "federal_trace_count": prop_traces,
            "federal_trace_level": "property",
            "tribe_level_trace_count": tribe_traces,
            "tribe_level_traces": "|".join(
                n for n, v in (("FR_CLASS_III_COMPACT_APPROVAL", t_fr),
                               ("BIA_GAMING_LAND_DECISION_IGRA_S20", t_gld),
                               ("TRIBAL_STATE_COMPACT_INDEX", t_cmp)) if v),
            "reports_gaming_capacity_non_federal": reports_capacity,
            "gaming_capacity_reported": "; ".join(
                f"{k}={int(v)}" for k, v in cap.items() if v > 0),
            "gaming_equipment_metrics_observed": "|".join(obs_metrics),
            "gaming_equipment_n_observations": len(obs),
            "gaming_equipment_observed_first": obs_dates[0] if obs_dates else "",
            "gaming_equipment_observed_last": obs_dates[-1] if obs_dates else "",
            "gaming_equipment_source": ("Casino City capacity panel via "
                                        "gaming_facility_metrics.csv — VENDOR "
                                        "observation, not a federal record"
                                        if obs else ""),

            "nigc_unmatched_marker_in_same_city_state": len(leads),
            "nigc_unmatched_marker_names": "|".join(
                x["nigc_location_name"] for x in leads)[:400],
            "nigc_match_ceiling_note": (
                "The NIGC roster match is deterministic and ONE-TO-ONE. A zero "
                "in trace_nigc_gaming_location_map means this row won no "
                "marker, not that the property is unlisted: a second Cedar row "
                "for the same property cannot claim a marker already taken, and "
                "a name variant beyond exact normalised equality plus a "
                "coordinate gap over 1.2 km misses outright (measured cases: "
                "Barona Resort & Casino, Apache Gold Casino Resort)."),

            "property_likelihood": cls,
            "property_likelihood_basis": basis,
            "excluded_from_gaming_property_count": excluded,
            "gaming_class_recorded": "NOT_RECORDED_BY_DESIGN",
            "gaming_class_note": (
                "Gaming class is a time-varying operational state, not a "
                "property attribute: a tribe changes class by swapping machines "
                "and no federal record is generated. Cedar Press records dated "
                "authorisations and dated listings, never a class."),
            "igra_coverage_status": cov.get(fid, {}).get("igra_coverage_status", ""),
            "built_date": TODAY,
        }
        out.append(rec)

        triage.append({
            "facility_id": fid, "facility_name": name, "tribe": f.get("tribe", ""),
            "city": f.get("city", ""), "state": f.get("state", ""),
            "property_likelihood": cls,
            "federal_trace_count": prop_traces,
            "tribe_level_trace_count": tribe_traces,
            "reports_gaming_capacity_non_federal": reports_capacity,
            "on_nigc_map": t_nigc, "nigc_marker_id": rec["nigc_marker_id"],
            "nigc_unmatched_marker_in_same_city_state": len(leads),
            "nigc_unmatched_marker_names": rec["nigc_unmatched_marker_names"],
            "gaming_equipment_n_observations": len(obs),
            "gaming_equipment_observed_last": rec["gaming_equipment_observed_last"],
            "has_tribe_id": 1 if tid else 0,
            "fr_compact_doc": rec["fr_document_number"],
            "fr_document_url": rec["fr_document_url"],
            "bia_decision_id": rec["bia_decision_id"],
            "compact_id": rec["compact_id"],
            "compact_in_force_as_of": rec["compact_in_force_as_of"],
            "excluded_from_gaming_property_count": excluded,
            "evidence": basis,
            "existing_absent_reason": absent_reason[:300],
            "YOUR_RULING": "",
            "built_date": TODAY,
        })

    fields = list(out[0].keys())
    write_csv(CLEAN / "gaming_property_federal_traces.csv", out, fields)
    write_csv(REVIEW / f"gaming_property_triage_{TODAY}.csv", triage,
              list(triage[0].keys()))

    # ------------------------------------------------------------- the report
    print("\n--- trace distribution (PROPERTY-level) ---")
    for k, v in sorted(Counter(r["federal_trace_count"] for r in out).items()):
        print(f"  {k} trace(s): {v:,}")
    print("\n--- tribe-level trace distribution (NOT property evidence) ---")
    for k, v in sorted(Counter(r["tribe_level_trace_count"] for r in out).items()):
        print(f"  {k} trace(s): {v:,}")
    print("\n--- property_likelihood ---")
    for k, v in Counter(r["property_likelihood"] for r in out).most_common():
        print(f"  {k:32s} {v:,}")

    # ------------------------------------------------- THE VALIDATION TEST
    print("\n=== VALIDATION: the 16 rows whose own name denies a casino ===")
    ph = [r for r in out if DENIES_CASINO_RE.search(r["facility_name"])]
    bad = [r for r in ph if r["federal_trace_count"] != 0]
    print(f"  rows found: {len(ph)}   scoring ZERO property-level traces: "
          f"{len(ph) - len(bad)}")
    if bad:
        print("  *** FAILED — trace logic is wrong before it is applied to "
              "anything uncertain: ***")
        for r in bad:
            print(f"      {r['facility_id']} {r['facility_name']} "
                  f"count={r['federal_trace_count']}")
    else:
        print("  PASSED. All 16 score zero on federal_trace_count.")
    withtribe = [r for r in ph if r["tribe_level_trace_count"] > 0]
    print(f"  ... and {len(withtribe)} of them DO carry tribe-level traces:")
    for r in withtribe:
        print(f"      {r['facility_id']:9s} {r['facility_name'][:40]:40s} "
              f"tribe-level={r['tribe_level_trace_count']} "
              f"[{r['tribe_level_traces']}]")
    print("  That is the point: a tribe-level federal record cannot confirm a "
          "property.\n     If compacts counted as property traces, a row named "
          "'No casino' would score two.")

    # --------------------------------------------------- the honest ceilings
    print("\n--- what a zero does and does not mean ---")
    z = [r for r in out if r["federal_trace_count"] == 0]
    print(f"  rows with 0 property-level federal traces          : {len(z):,}")
    print(f"  ... of which carry a dated gaming-equipment obs    : "
          f"{sum(1 for r in z if r['reports_gaming_capacity_non_federal']):,}")
    print(f"  ... of which have an unmatched NIGC marker in their")
    print(f"      own city and state (a LEAD, not a match)       : "
          f"{sum(1 for r in z if r['nigc_unmatched_marker_in_same_city_state']):,}")
    print(f"  ... of which carry NO tribe_id, so no tribe-level")
    print(f"      trace could reach them at all                  : "
          f"{sum(1 for r in z if not r['tribe_id']):,}")
    zz = [r for r in out if r["federal_trace_count"] == 0
          and not r["reports_gaming_capacity_non_federal"]
          and not r["tribe_level_trace_count"]]
    print(f"  rows with NO trace of ANY kind, federal or vendor,")
    print(f"      at property or tribe level                     : {len(zz):,}")
    for r in zz[:25]:
        print(f"      {r['facility_id']:11s} {r['facility_name'][:44]:44s} "
              f"{r['state']:3s} {r['property_likelihood']}")

    # ---------------------------------------------- unresolved FR, for review
    if fr_unresolved:
        rows = [{"tribe_string_in_document": k.split(" :: ")[0],
                 "resolve_reason": k.split(" :: ")[-1], "n_documents": v,
                 "note": "Named in a Federal Register Class III compact notice "
                         "but not resolvable to a spine entity. HELD, not "
                         "guessed.", "YOUR_RULING": "", "built_date": TODAY}
                for k, v in fr_unresolved.most_common()]
        write_csv(REVIEW / f"gaming_fr_compact_unresolved_tribes_{TODAY}.csv",
                  rows, list(rows[0].keys()))

    # ------------------------------------------------- the comparability note
    breaks = [{
        "dataset": "gaming_property_federal_traces",
        "break_id": f"GAMING_CLASS_NOT_A_PROPERTY_ATTRIBUTE_{TODAY}",
        "break_type": "definitional_comparability",
        "effective_from": "", "effective_to": "",
        "what_changed":
            "A property's gaming class (Class II vs Class III under IGRA) is a "
            "time-varying OPERATIONAL state, not a property attribute. A tribe "
            "changes class by swapping the machines on its floor. Class II "
            "electronic bingo-based machines and Class III slots are visually "
            "indistinguishable and can be exchanged without generating any "
            "federal record.",
        "why_it_matters":
            "A property's compact status changing between years is a change in "
            "LEGAL AUTHORISATION, not necessarily a change in operations — and "
            "the reverse is equally true: a property can change what it "
            "operates with no change in any federal record. A compact is "
            "NECESSARY BUT NOT SUFFICIENT in both directions. Its presence does "
            "not prove Class III operation; its absence does not prove the "
            "property is not gaming, because Class II requires no compact at "
            "all. Do not chart 'Class III properties by year' off compact "
            "presence; it measures authorisation, not activity.",
        "consequence_for_revenue":
            "This is a further reason Cedar Press publishes NO property-level "
            "revenue. Class II and Class III carry materially different revenue "
            "profiles, the mix is unobservable per property, and it can change "
            "without notice. Modelling property GGR from machine counts "
            "implicitly assumes a class mix that cannot be known. NIGC "
            "publishes GGR at REGION level only.",
        "how_this_dataset_handles_it":
            "No gaming class is assigned to any property. Only dated "
            "observations are recorded: compact_in_force_as_of, "
            "nigc_listed_as_of, land_decision_date. The column "
            "gaming_class_recorded reads NOT_RECORDED_BY_DESIGN on all 774 rows.",
        "source_url": "https://www.nigc.gov/general-counsel/indian-gaming-regulatory-act",
        "authority": "IGRA, 25 U.S.C. 2703(7)-(8) (class II / class III "
                     "definitions) and 2710(d)(1)(C) (class III requires a "
                     "compact); Elijah Moreno ruling 2026-08-06",
        "owner_note": "data/clean/series_breaks.csv is owned by another process "
                      "(script 86). This row is staged here for its owner to "
                      "merge; series_breaks.csv was NOT edited.",
        "built_date": TODAY,
    }, {
        "dataset": "gaming_property_federal_traces",
        "break_id": f"BIA_GAMING_LAND_INDEX_IS_THE_IGRA_S20_INDEX_{TODAY}",
        "break_type": "source_scope",
        "effective_from": "", "effective_to": "",
        "what_changed":
            "An 'IGRA Section 20 determination' and a 'BIA gaming land "
            "decision' are the SAME record, not two independent federal "
            "traces. BIA's Office of Indian Gaming index is the Section 20 "
            "index: every one of its 138 rows carries a legal_theory that is a "
            "25 U.S.C. 2719 exception.",
        "why_it_matters":
            "Counting both would double-count one federal action and inflate "
            "every triangulation score by one on 138 tribes' properties.",
        "consequence_for_revenue": "",
        "how_this_dataset_handles_it":
            "One trace column, trace_bia_gaming_land_decision, with the "
            "Section 20 exception and its U.S. Code citation recorded on the "
            "same record in igra_section20_exception / igra_section20_citation.",
        "source_url": BIA_GLD_URL,
        "authority": "25 U.S.C. 2719",
        "owner_note": "Staged for the owner of series_breaks.csv.",
        "built_date": TODAY,
    }]
    write_csv(REVIEW / f"gaming_series_breaks_{TODAY}.csv", breaks,
              list(breaks[0].keys()))


if __name__ == "__main__":
    main()
